"""
종목 설정 다이얼로그
- 한국 주식 / 한국 ETF / 미국 주식·ETF 모두 지원
- 저장 시 강제 종료 버그 수정: try/except 감쌈, signal emit 후 accept()
- 디자인: 어두운 그레이 배경, 파랑은 포인트만
- 드래그로 행 순서 변경 지원
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from core.config import save_stocks
from core.fetcher import search_stocks
import core.logger as logger

# ── 디자인 토큰 ────────────────────────────────────────────────────────────────
ACCENT       = "#5D87F6"
BG_MAIN      = "#1A1B1C"
BG_SURFACE   = "#242526"
BG_INPUT     = "#2C2D2E"
BG_TABLE     = "#222324"
BORDER       = "#3A3B3C"
BTN_BG       = "#1E2A4A"
BTN_FG       = "#7DA4F8"
FG_PRIMARY   = "#E0E0E0"
FG_SECONDARY = "#909090"
FG_MUTED     = "#555555"
ETF_COLOR    = "#A78BFA"   # ETF 강조 — 보라
RED_SOFT     = "#F06292"

STYLE = f"""
QDialog  {{ background: {BG_MAIN}; }}
QWidget  {{ background: {BG_MAIN}; }}
QLabel   {{ color: {FG_PRIMARY}; background: transparent; font-size: 9pt; }}
QLineEdit, QComboBox {{
    background: {BG_INPUT};
    color: {FG_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 9px;
    font-size: 9pt;
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; padding-right: 6px; }}
QComboBox QAbstractItemView {{
    background: {BG_INPUT};
    color: {FG_PRIMARY};
    border: 1px solid {BORDER};
    selection-background-color: {BTN_BG};
    selection-color: {ACCENT};
    outline: none;
}}
QPushButton {{
    background: {BTN_BG};
    color: {BTN_FG};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 12px;
    font-size: 9pt;
}}
QPushButton:hover {{
    background: #263A6A;
    color: {ACCENT};
    border-color: {ACCENT};
}}
QPushButton:pressed {{ background: #141E38; }}
QPushButton#btn_save {{
    background: {ACCENT};
    color: #FFFFFF;
    border: 1px solid {ACCENT};
    font-weight: bold;
    padding: 6px 20px;
}}
QPushButton#btn_save:hover {{ background: #4A74E8; border-color: #4A74E8; }}
QPushButton#btn_del {{
    background: #2A1520;
    color: {RED_SOFT};
    border: 1px solid #4A2030;
}}
QPushButton#btn_del:hover {{
    background: #381828;
    color: #FF80AB;
    border-color: {RED_SOFT};
}}
QPushButton#btn_del:disabled {{
    background: {BG_SURFACE};
    color: {FG_MUTED};
    border-color: {BORDER};
}}
QTableWidget {{
    background: {BG_TABLE};
    color: {FG_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 5px;
    gridline-color: #2E2F30;
    font-size: 9pt;
}}
QTableWidget::item {{
    background: {BG_TABLE};
    color: {FG_PRIMARY};
    padding: 3px 6px;
    border: none;
}}
QTableWidget::item:selected {{
    background: {BTN_BG};
    color: {ACCENT};
}}
QTableWidget::item:hover {{
    background: #282930;
}}
QHeaderView::section {{
    background: {BG_SURFACE};
    color: {ACCENT};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    padding: 5px 6px;
    font-weight: bold;
    font-size: 9pt;
}}
QTableCornerButton::section {{
    background: {BG_SURFACE};
    border: none;
}}
QScrollBar:vertical {{
    background: {BG_MAIN};
    width: 5px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 2px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {FG_MUTED}; }}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; }}
"""

MARKET_OPTIONS = [
    ("한국 주식  (KR)",    "KR"),
    ("한국 ETF  (KR_ETF)", "KR_ETF"),
    ("미국  (US)",         "US"),
]

MARKET_LABEL = {"KR": "KR", "KR_ETF": "ETF", "US": "US"}


class DraggableTable(QTableWidget):
    row_moved = pyqtSignal(int, int)

    def __init__(self, rows: int, cols: int):
        super().__init__(rows, cols)
        self._drag_src: int | None = None
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    def mousePressEvent(self, e):
        it = self.itemAt(e.pos())
        self._drag_src = it.row() if it else None
        super().mousePressEvent(e)

    def dropEvent(self, e):
        it = self.itemAt(e.pos())
        dst = it.row() if it else None
        if self._drag_src is not None and dst is not None and self._drag_src != dst:
            self.row_moved.emit(self._drag_src, dst)
        self._drag_src = None
        e.ignore()


class SearchThread(QThread):
    result = pyqtSignal(list)

    def __init__(self, market: str, query: str):
        super().__init__()
        self.market = market
        self.query  = query

    def run(self):
        try:
            results = search_stocks(self.query, self.market)
            self.result.emit(results)
        except Exception as e:
            logger.error(f"SearchThread error: {e}")
            self.result.emit([])


class StockDialog(QDialog):
    stocks_updated = pyqtSignal(list)

    def __init__(self, data_dir: str, stocks: list, parent=None):
        super().__init__(parent)
        self.data_dir       = data_dir
        self.stocks         = [s.copy() for s in stocks]
        self._sel_result    = None
        self._search_thread = None
        self._old_threads   = []

        self.setWindowTitle("종목 설정")
        self.setMinimumSize(680, 580)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._refresh_table()
        logger.debug("StockDialog opened")

    def _build_ui(self):
        main = QVBoxLayout()
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(10)

        main.addWidget(self._section_label("종목 · ETF 검색 및 추가"))

        row_search = QHBoxLayout()
        row_search.setSpacing(7)

        self.cmb_market = QComboBox()
        for label, _ in MARKET_OPTIONS:
            self.cmb_market.addItem(label)
        self.cmb_market.setFixedWidth(166)
        self.cmb_market.setToolTip(
            "한국 주식 : 코스피·코스닥\n"
            "한국 ETF  : KODEX·TIGER·KBSTAR 등 KR ETF 1140종\n"
            "미국      : NYSE·NASDAQ 주식 및 ETF"
        )

        self.edit_query = QLineEdit()
        self.edit_query.setPlaceholderText(
            "코드 또는 종목명   예) 005930  삼성전자  069500  AAPL  SPY"
        )
        self.edit_query.returnPressed.connect(self._search)

        btn_search = QPushButton("조회")
        btn_search.setFixedWidth(64)
        btn_search.clicked.connect(self._search)

        row_search.addWidget(self.cmb_market)
        row_search.addWidget(self.edit_query)
        row_search.addWidget(btn_search)
        main.addLayout(row_search)

        self.tbl_search = QTableWidget(0, 3)
        self.tbl_search.setHorizontalHeaderLabels(["코드", "종목명 / ETF명", "현재가"])
        self.tbl_search.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_search.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_search.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_search.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_search.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_search.setFixedHeight(126)
        self.tbl_search.itemClicked.connect(self._on_search_clicked)
        main.addWidget(self.tbl_search)

        row_input = QHBoxLayout()
        row_input.setSpacing(7)
        lbl_buy = QLabel("매수단가")
        lbl_buy.setStyleSheet(f"color: {FG_SECONDARY}; background: transparent; font-size: 9pt;")
        self.edit_buy = QLineEdit()
        self.edit_buy.setPlaceholderText("매수단가")
        self.edit_buy.returnPressed.connect(self._add_stock)
        lbl_qty = QLabel("수량")
        lbl_qty.setStyleSheet(f"color: {FG_SECONDARY}; background: transparent; font-size: 9pt;")
        self.edit_qty = QLineEdit()
        self.edit_qty.setPlaceholderText("보유수량")
        self.edit_qty.returnPressed.connect(self._add_stock)
        btn_add = QPushButton("추가")
        btn_add.setFixedWidth(64)
        btn_add.clicked.connect(self._add_stock)
        row_input.addWidget(lbl_buy)
        row_input.addWidget(self.edit_buy)
        row_input.addSpacing(4)
        row_input.addWidget(lbl_qty)
        row_input.addWidget(self.edit_qty)
        row_input.addWidget(btn_add)
        main.addLayout(row_input)

        main.addWidget(self._section_label("저장된 종목  —  행 드래그로 순서 변경"))

        self.tbl_stocks = DraggableTable(0, 5)
        self.tbl_stocks.setHorizontalHeaderLabels(["시장", "코드", "종목명", "매수단가", "수량"])
        self.tbl_stocks.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_stocks.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_stocks.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_stocks.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_stocks.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_stocks.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_stocks.itemDoubleClicked.connect(self._on_double_click)
        self.tbl_stocks.row_moved.connect(self._on_row_moved)
        main.addWidget(self.tbl_stocks)

        row_btn = QHBoxLayout()
        row_btn.setSpacing(8)
        self.btn_del = QPushButton("선택 삭제")
        self.btn_del.setObjectName("btn_del")
        self.btn_del.clicked.connect(self._delete_selected)
        btn_save  = QPushButton("저장하기")
        btn_save.setObjectName("btn_save")
        btn_save.clicked.connect(self._save)
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.reject)
        row_btn.addWidget(self.btn_del)
        row_btn.addStretch()
        row_btn.addWidget(btn_close)
        row_btn.addWidget(btn_save)
        main.addLayout(row_btn)

        self.setLayout(main)
        self._update_del_btn()

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(f"  {text}")
        lbl.setFont(QFont("Malgun Gothic", 9, QFont.Bold))
        lbl.setFixedHeight(26)
        lbl.setStyleSheet(
            f"color: {FG_PRIMARY};"
            f"background: {BG_SURFACE};"
            f"border-left: 3px solid {ACCENT};"
            f"padding-left: 8px;"
        )
        return lbl

    def _get_selected_market(self) -> str:
        idx = self.cmb_market.currentIndex()
        if 0 <= idx < len(MARKET_OPTIONS):
            return MARKET_OPTIONS[idx][1]
        return "KR"

    def _search(self):
        query = self.edit_query.text().strip()
        if not query:
            return
        market = self._get_selected_market()
        logger.info(f"StockDialog search: market={market}, query={query!r}")

        if self._search_thread and self._search_thread.isRunning():
            self._old_threads.append(self._search_thread)

        self.tbl_search.clearContents()
        self.tbl_search.setRowCount(1)
        self.tbl_search.setSpan(0, 0, 1, 3)
        it = QTableWidgetItem("  조회 중...")
        it.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        it.setForeground(QColor(FG_MUTED))
        it.setBackground(QColor(BG_TABLE))
        self.tbl_search.setItem(0, 0, it)

        th = SearchThread(market, query)
        th.result.connect(self._on_search_result)
        th.finished.connect(self._cleanup_thread)
        th.finished.connect(th.deleteLater)
        self._search_thread = th
        th.start()

    def _on_search_result(self, results: list):
        if self.sender() is not self._search_thread:
            return

        self.tbl_search.setSpan(0, 0, 1, 1)
        self.tbl_search.clearContents()

        if not results:
            self.tbl_search.setRowCount(1)
            self.tbl_search.setSpan(0, 0, 1, 3)
            it = QTableWidgetItem("  검색 결과가 없습니다.  코드·종목명을 다시 확인하거나 시장을 변경해보세요.")
            it.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            it.setForeground(QColor(FG_MUTED))
            it.setBackground(QColor(BG_TABLE))
            self.tbl_search.setItem(0, 0, it)
            self._sel_result = None
            return

        self.tbl_search.setRowCount(len(results))
        for i, r in enumerate(results):
            market    = r["market"]
            price     = r["price"]
            price_str = f"{price:,.2f}" if market == "US" else f"{price:,.0f}"
            fg = ETF_COLOR if market == "KR_ETF" else FG_PRIMARY
            for col, val in enumerate([r["code"], r["name"], price_str]):
                it = QTableWidgetItem(val)
                it.setBackground(QColor(BG_TABLE))
                it.setForeground(QColor(fg))
                it.setFont(QFont("Malgun Gothic", 9))
                self.tbl_search.setItem(i, col, it)

        if len(results) == 1:
            self._sel_result = results[0]
            self.tbl_search.selectRow(0)

    def _cleanup_thread(self):
        sender = self.sender()
        if sender is self._search_thread:
            self._search_thread = None
        elif sender in self._old_threads:
            self._old_threads.remove(sender)

    def _on_search_clicked(self, item):
        row = item.row()
        if self.tbl_search.columnSpan(row, 0) > 1:
            return
        code_it  = self.tbl_search.item(row, 0)
        name_it  = self.tbl_search.item(row, 1)
        price_it = self.tbl_search.item(row, 2)
        if not code_it:
            return
        market = self._get_selected_market()
        try:
            price = float(price_it.text().replace(",", ""))
        except Exception:
            price = 0.0
        self._sel_result = {
            "code"  : code_it.text(),
            "name"  : name_it.text() if name_it else "",
            "market": market,
            "price" : price,
        }

    def _add_stock(self):
        if not self._sel_result:
            QMessageBox.warning(self, "알림", "먼저 종목 / ETF를 조회하고 선택하세요.")
            return
        try:
            buy = float(self.edit_buy.text().replace(",", ""))
            qty = int(self.edit_qty.text().replace(",", ""))
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "매수단가와 수량을 올바르게 입력하세요.")
            return
        if buy <= 0 or qty <= 0:
            QMessageBox.warning(self, "입력 오류", "매수단가와 수량은 0보다 커야 합니다.")
            return

        self.stocks.append({
            "market"   : self._sel_result["market"],
            "code"     : self._sel_result["code"],
            "name"     : self._sel_result["name"],
            "buy_price": buy,
            "quantity" : qty,
            "active"   : True,
        })
        self._sel_result = None
        self.edit_buy.clear()
        self.edit_qty.clear()
        self._refresh_table()
        self._update_del_btn()

    def _delete_selected(self):
        rows = sorted({i.row() for i in self.tbl_stocks.selectedItems()}, reverse=True)
        if not rows:
            QMessageBox.warning(self, "알림", "삭제할 종목을 선택하세요.")
            return
        if len(self.stocks) - len(rows) < 1:
            QMessageBox.warning(self, "삭제 불가", "최소 1개 종목은 유지해야 합니다.")
            return
        for r in rows:
            if r < len(self.stocks):
                del self.stocks[r]
        self._refresh_table()
        self._update_del_btn()

    def _on_row_moved(self, src: int, dst: int):
        if 0 <= src < len(self.stocks) and 0 <= dst < len(self.stocks):
            s = self.stocks.pop(src)
            self.stocks.insert(dst, s)
            self._refresh_table()

    def _update_del_btn(self):
        self.btn_del.setEnabled(len(self.stocks) > 1)

    def _refresh_table(self):
        self.tbl_stocks.setRowCount(len(self.stocks))
        for i, s in enumerate(self.stocks):
            market = s.get("market", "KR")
            vals = [
                MARKET_LABEL.get(market, market),
                s.get("code", ""),
                s.get("name", ""),
                f"{s.get('buy_price', 0):,.0f}",
                str(s.get("quantity", 0)),
            ]
            for col, val in enumerate(vals):
                it = QTableWidgetItem(val)
                it.setFont(QFont("Malgun Gothic", 9))
                it.setBackground(QColor(BG_TABLE))
                it.setForeground(QColor(ETF_COLOR if market == "KR_ETF" and col == 0 else FG_PRIMARY))
                it.setFlags(
                    (it.flags() | Qt.ItemIsEditable)
                    if col in (2, 3, 4)
                    else (it.flags() & ~Qt.ItemIsEditable)
                )
                self.tbl_stocks.setItem(i, col, it)

    def _on_double_click(self, item):
        if item.column() in (2, 3, 4):
            self.tbl_stocks.editItem(item)

    def _save(self):
        try:
            for i in range(self.tbl_stocks.rowCount()):
                if i >= len(self.stocks):
                    break
                name_it = self.tbl_stocks.item(i, 2)
                buy_it  = self.tbl_stocks.item(i, 3)
                qty_it  = self.tbl_stocks.item(i, 4)
                if name_it:
                    self.stocks[i]["name"] = name_it.text().strip()
                if buy_it:
                    try:
                        self.stocks[i]["buy_price"] = float(buy_it.text().replace(",", ""))
                    except ValueError:
                        pass
                if qty_it:
                    try:
                        self.stocks[i]["quantity"] = int(qty_it.text().replace(",", ""))
                    except ValueError:
                        pass

            save_stocks(self.data_dir, self.stocks)
            logger.info(f"stocks saved: {len(self.stocks)} items")

            self.stocks_updated.emit([s.copy() for s in self.stocks])
            self.accept()

        except Exception as e:
            logger.exception(f"StockDialog save error: {e}")
            QMessageBox.critical(self, "저장 오류",
                f"종목 정보를 저장하는 중 오류가 발생했습니다.\n{e}")
