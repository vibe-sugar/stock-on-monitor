"""
종목 설정 다이얼로그
- 한국 주식 / 한국 ETF / 미국 주식·ETF 모두 지원
- 저장 시 강제 종료 버그 수정: try/except 감쌈, signal emit 후 accept()
- 블루 포인트 테마 적용
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

# ── 블루 포인트 스타일시트 ────────────────────────────────────────────────────
BLUE_ACCENT = "#2841E8"
BLUE_BORDER = "#1e3a4a"
BG_MAIN     = "#0f1a22"
BG_INPUT    = "#162030"
BG_TABLE    = "#111e28"
FG_MAIN     = "#b0b0b0"
FG_DIM      = "#666666"

STYLE = f"""
QDialog  {{ background: {BG_MAIN}; }}
QWidget  {{ background: {BG_MAIN}; }}
QLabel   {{ color: {FG_MAIN}; background: transparent; }}
QLineEdit, QComboBox {{
    background: {BG_INPUT};
    color: {FG_MAIN};
    border: 1px solid {BLUE_BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {BLUE_ACCENT};
}}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background: {BG_INPUT};
    color: {FG_MAIN};
    border: 1px solid {BLUE_BORDER};
    selection-background-color: #1a3a4a;
    selection-color: {BLUE_ACCENT};
}}
QPushButton {{
    background: {BG_INPUT};
    color: {FG_MAIN};
    border: 1px solid {BLUE_BORDER};
    border-radius: 4px;
    padding: 5px 12px;
}}
QPushButton:hover {{
    background: #1a3a4a;
    color: {BLUE_ACCENT};
    border-color: {BLUE_ACCENT};
}}
QPushButton#btn_save {{
    background: #0e2a3a;
    color: {BLUE_ACCENT};
    border: 1px solid {BLUE_ACCENT};
    font-weight: bold;
}}
QPushButton#btn_save:hover {{
    background: #1a3a4a;
}}
QPushButton#btn_del {{
    background: #1a1010;
    border-color: #3a2020;
    color: #cc5555;
}}
QPushButton#btn_del:hover {{
    background: #2a1a1a;
    color: #ff6666;
    border-color: #aa3333;
}}
QPushButton#btn_del:disabled {{
    background: {BG_MAIN};
    color: #333333;
    border-color: #1a2a3a;
}}
QTableWidget {{
    background: {BG_TABLE};
    color: {FG_MAIN};
    border: 1px solid {BLUE_BORDER};
    gridline-color: #1a2a3a;
}}
QTableWidget::item {{
    background: {BG_TABLE};
    color: {FG_MAIN};
    padding: 2px 4px;
}}
QTableWidget::item:selected {{
    background: #1a3a4a;
    color: {BLUE_ACCENT};
}}
QHeaderView::section {{
    background: {BG_INPUT};
    color: {BLUE_ACCENT};
    border: none;
    border-right: 1px solid {BLUE_BORDER};
    border-bottom: 1px solid {BLUE_BORDER};
    padding: 4px;
    font-weight: bold;
}}
QTableCornerButton::section {{
    background: {BG_INPUT};
    border: none;
}}
QScrollBar:vertical {{
    background: {BG_MAIN};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #1e3a4a;
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; }}
"""

# ── 시장 목록 정의 ────────────────────────────────────────────────────────────
MARKET_OPTIONS = [
    ("한국 주식  (KR)",    "KR"),
    ("한국 ETF  (KR_ETF)", "KR_ETF"),
    ("미국  (US)",         "US"),
]

# 시장 코드 → 표시 이름
MARKET_LABEL = {
    "KR"     : "KR",
    "KR_ETF" : "ETF",
    "US"     : "US",
}


class DraggableTable(QTableWidget):
    """드래그로 행 순서를 변경하는 테이블"""
    row_moved = pyqtSignal(int, int)   # from_row, to_row

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
        e.ignore()   # 직접 처리하므로 Qt 기본 동작 무시


class SearchThread(QThread):
    """별도 스레드에서 종목/ETF 검색"""
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
        self._sel_result    = None   # 검색에서 선택된 종목
        self._search_thread = None
        self._old_threads   = []

        self.setWindowTitle("종목 설정")
        self.setMinimumSize(660, 560)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._refresh_table()
        logger.debug("StockDialog opened")

    # ── UI 구성 ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        main = QVBoxLayout()
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(10)

        # ── 종목 검색 영역 ────────────────────────────────────────────────
        main.addWidget(self._section("▸ 종목 / ETF 검색 및 추가"))

        row_search = QHBoxLayout()

        # 시장 선택 콤보
        self.cmb_market = QComboBox()
        for label, _ in MARKET_OPTIONS:
            self.cmb_market.addItem(label)
        self.cmb_market.setFixedWidth(160)
        self.cmb_market.setToolTip(
            "한국 주식 : 코스피·코스닥\n"
            "한국 ETF  : KODEX·TIGER·KBSTAR 등 KR ETF 1140종\n"
            "미국      : NYSE·NASDAQ 주식 및 ETF"
        )

        self.edit_query = QLineEdit()
        self.edit_query.setPlaceholderText(
            "코드 또는 종목명  예) 005930  삼성전자  069500  KODEX 200  AAPL  SPY"
        )
        self.edit_query.returnPressed.connect(self._search)

        btn_search = QPushButton("조회")
        btn_search.setFixedWidth(64)
        btn_search.clicked.connect(self._search)

        row_search.addWidget(self.cmb_market)
        row_search.addWidget(self.edit_query)
        row_search.addWidget(btn_search)
        main.addLayout(row_search)

        # ── 검색 결과 테이블 ──────────────────────────────────────────────
        self.tbl_search = QTableWidget(0, 3)
        self.tbl_search.setHorizontalHeaderLabels(["코드", "종목명 / ETF명", "현재가"])
        self.tbl_search.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_search.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_search.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_search.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_search.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_search.setFixedHeight(120)
        self.tbl_search.itemClicked.connect(self._on_search_clicked)
        main.addWidget(self.tbl_search)

        # ── 매수 정보 입력 ────────────────────────────────────────────────
        row_input = QHBoxLayout()
        self.edit_buy = QLineEdit()
        self.edit_buy.setPlaceholderText("매수단가")
        self.edit_buy.returnPressed.connect(self._add_stock)
        self.edit_qty = QLineEdit()
        self.edit_qty.setPlaceholderText("보유수량")
        self.edit_qty.returnPressed.connect(self._add_stock)
        btn_add = QPushButton("추가")
        btn_add.setFixedWidth(64)
        btn_add.clicked.connect(self._add_stock)

        row_input.addWidget(QLabel("매수단가"))
        row_input.addWidget(self.edit_buy)
        row_input.addWidget(QLabel("수량"))
        row_input.addWidget(self.edit_qty)
        row_input.addWidget(btn_add)
        main.addLayout(row_input)

        # ── 저장된 종목 테이블 ────────────────────────────────────────────
        main.addWidget(self._section("▸ 저장된 종목  (행 드래그로 순서 변경 가능)"))

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

        # ── 하단 버튼 ─────────────────────────────────────────────────────
        row_btn = QHBoxLayout()
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
        row_btn.addWidget(btn_save)
        row_btn.addWidget(btn_close)
        main.addLayout(row_btn)

        self.setLayout(main)
        self._update_del_btn()

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Malgun Gothic", 9, QFont.Bold))
        lbl.setStyleSheet(f"color: {BLUE_ACCENT}; background: transparent;")
        return lbl

    def _get_selected_market(self) -> str:
        """콤보박스 현재 선택 → market 코드 반환"""
        idx = self.cmb_market.currentIndex()
        if 0 <= idx < len(MARKET_OPTIONS):
            return MARKET_OPTIONS[idx][1]
        return "KR"

    # ── 검색 ─────────────────────────────────────────────────────────────────

    def _search(self):
        query = self.edit_query.text().strip()
        if not query:
            return
        market = self._get_selected_market()
        logger.info(f"StockDialog search: market={market}, query={query!r}")

        # 이전 스레드 보관
        if self._search_thread and self._search_thread.isRunning():
            self._old_threads.append(self._search_thread)

        # "조회 중..." 표시
        self.tbl_search.clearContents()
        self.tbl_search.setRowCount(1)
        self.tbl_search.setSpan(0, 0, 1, 3)
        it = QTableWidgetItem("조회 중...")
        it.setTextAlignment(Qt.AlignCenter)
        it.setForeground(QColor(FG_DIM))
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
            return   # 이전 스레드 결과는 무시

        self.tbl_search.setSpan(0, 0, 1, 1)
        self.tbl_search.clearContents()

        if not results:
            self.tbl_search.setRowCount(1)
            self.tbl_search.setSpan(0, 0, 1, 3)
            it = QTableWidgetItem(
                "검색 결과가 없습니다.  코드·종목명을 다시 확인하거나 시장을 변경해보세요."
            )
            it.setTextAlignment(Qt.AlignCenter)
            it.setForeground(QColor(FG_DIM))
            it.setBackground(QColor(BG_TABLE))
            self.tbl_search.setItem(0, 0, it)
            self._sel_result = None
            return

        self.tbl_search.setRowCount(len(results))
        for i, r in enumerate(results):
            market = r["market"]
            price  = r["price"]
            # 원화는 정수, 달러는 소수 2자리
            price_str = f"{price:,.2f}" if market == "US" else f"{price:,.0f}"
            vals = [r["code"], r["name"], price_str]
            for col, val in enumerate(vals):
                it = QTableWidgetItem(val)
                it.setBackground(QColor(BG_TABLE))
                # ETF 이름은 파란색으로 구분
                fg = BLUE_ACCENT if market == "KR_ETF" else FG_MAIN
                it.setForeground(QColor(fg))
                self.tbl_search.setItem(i, col, it)

        # 결과 1건이면 자동 선택
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
            return   # "조회 중" / "없음" 행
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
        logger.debug(f"search selected: {self._sel_result['code']} ({self._sel_result['market']})")

    # ── 종목 추가 ─────────────────────────────────────────────────────────────

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

        new_stock = {
            "market"   : self._sel_result["market"],
            "code"     : self._sel_result["code"],
            "name"     : self._sel_result["name"],
            "buy_price": buy,
            "quantity" : qty,
            "active"   : True,
        }
        self.stocks.append(new_stock)
        logger.info(
            f"stock added: {new_stock['code']} ({new_stock['market']}) "
            f"buy={buy} qty={qty}"
        )
        self._sel_result = None
        self.edit_buy.clear()
        self.edit_qty.clear()
        self._refresh_table()
        self._update_del_btn()

    # ── 종목 삭제 ─────────────────────────────────────────────────────────────

    def _delete_selected(self):
        rows = sorted(
            {i.row() for i in self.tbl_stocks.selectedItems()}, reverse=True
        )
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

    # ── 행 이동 ───────────────────────────────────────────────────────────────

    def _on_row_moved(self, src: int, dst: int):
        if 0 <= src < len(self.stocks) and 0 <= dst < len(self.stocks):
            s = self.stocks.pop(src)
            self.stocks.insert(dst, s)
            self._refresh_table()
            logger.debug(f"row moved: {src} → {dst}")

    def _update_del_btn(self):
        self.btn_del.setEnabled(len(self.stocks) > 1)

    # ── 테이블 갱신 ───────────────────────────────────────────────────────────

    def _refresh_table(self):
        self.tbl_stocks.setRowCount(len(self.stocks))
        for i, s in enumerate(self.stocks):
            market = s.get("market", "KR")
            vals = [
                MARKET_LABEL.get(market, market),   # 시장 표시명
                s.get("code", ""),
                s.get("name", ""),
                f"{s.get('buy_price', 0):,.0f}",
                str(s.get("quantity", 0)),
            ]
            for col, val in enumerate(vals):
                it = QTableWidgetItem(val)
                it.setBackground(QColor(BG_TABLE))
                # ETF 행은 파랑으로 강조
                if market == "KR_ETF":
                    fg = BLUE_ACCENT if col == 0 else FG_MAIN
                else:
                    fg = FG_MAIN
                it.setForeground(QColor(fg))
                # 종목명(2), 매수단가(3), 수량(4) 편집 가능
                if col in (2, 3, 4):
                    it.setFlags(it.flags() | Qt.ItemIsEditable)
                else:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.tbl_stocks.setItem(i, col, it)

    def _on_double_click(self, item):
        if item.column() in (2, 3, 4):
            self.tbl_stocks.editItem(item)

    # ── 저장 ─────────────────────────────────────────────────────────────────

    def _save(self):
        """저장 — 강제 종료 방지를 위해 완전히 try/except 로 감쌈"""
        try:
            # 테이블 편집 내용을 self.stocks 에 반영
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

            # signal 먼저 emit → 그 다음 닫기
            self.stocks_updated.emit([s.copy() for s in self.stocks])
            self.accept()

        except Exception as e:
            logger.exception(f"StockDialog save error: {e}")
            QMessageBox.critical(
                self, "저장 오류",
                f"종목 정보를 저장하는 중 오류가 발생했습니다.\n{e}"
            )
