"""
FloatingWidget  —  주식 정보 플로팅 위젯

드래그: table + viewport 양쪽에 eventFilter 설치 → 어디서든 드래그 이동
즉시갱신: 설정/종목 저장 후 _rebuild_table() + 즉시 update_prices()
         update_prices()는 QThread 로 비동기 처리 → UI 블로킹 없음
테두리: cfg 의 border_width(0=없음) / border_color 로 동적 적용
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QMenu,
    QTableWidget, QTableWidgetItem,
)
from PyQt5.QtCore import Qt, QPoint, QTimer, QEvent, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush

from core.fetcher import fetch_price
import core.logger as logger


# ── 색상 팔레트 ──────────────────────────────────────────────────────────────
BLUE_ACCENT  = "#29b6f6"
BLUE_LIGHT   = "#4fc3f7"
RED_SOFT     = "#ef5350"
FG_DEFAULT   = "#b0b0b0"
FG_DIM       = "#666666"
BG_CARD      = "#0d0d0d"

MENU_STYLE = f"""
QMenu {{
    background: #0f1f2a;
    color: {FG_DEFAULT};
    border: 1px solid #1e3a4a;
    padding: 4px;
    border-radius: 4px;
}}
QMenu::item {{ padding: 6px 20px; border-radius: 3px; }}
QMenu::item:selected {{ background: #1a3a4a; color: {BLUE_ACCENT}; }}
QMenu::separator {{ background: #1e3a4a; height: 1px; margin: 3px 4px; }}
"""


# ── 비동기 가격 갱신 스레드 ───────────────────────────────────────────────────
class _PriceFetcher(QThread):
    """모든 종목 가격을 백그라운드에서 한 번에 조회해 결과를 signal 로 반환"""
    done = pyqtSignal(list)   # list[dict | None]  — stocks 순서와 동일

    def __init__(self, stocks: list):
        super().__init__()
        self._stocks = stocks

    def run(self):
        results = []
        for s in self._stocks:
            try:
                results.append(fetch_price(s["market"], s["code"]))
            except Exception as e:
                logger.error(f"_PriceFetcher error {s.get('code')}: {e}")
                results.append(None)
        self.done.emit(results)


class FloatingWidget(QWidget):
    """메인 플로팅 위젯"""

    def __init__(self, data_dir: str, cfg: dict, stocks: list):
        super().__init__()
        self.data_dir = data_dir
        self.cfg      = cfg
        self.stocks   = [s for s in stocks if s.get("active", True)]

        # 드래그
        self._drag_pos    = QPoint()
        self._is_dragging = False

        # 가격 캐시 (code → dict)  — 재빌드 후 즉시 표시에 사용
        self._price_cache: dict[str, dict] = {}

        # UI 내부 참조
        self.card      = None
        self.table     = None
        self.row_items = []   # list[dict[str, QTableWidgetItem]]
        self.col_map   = {}
        self.summary_row     = -1
        self.sum_current_item = None
        self.sum_profit_item  = None

        # 비동기 fetcher
        self._fetcher: _PriceFetcher | None = None

        logger.info(f"FloatingWidget init: {len(self.stocks)} stocks")
        self._build_ui()
        self._setup_flags()

        # 정기 갱신 타이머
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_prices)
        self.timer.start(max(3000, self.cfg.get("interval_ms", 10000)))

        # 초기 가격 즉시 조회
        self.update_prices()

    # ── 초기화 ──────────────────────────────────────────────────────────────

    def _setup_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.show()

    def _build_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.card = QWidget(self)
        self.card.setObjectName("card")
        self._apply_card_style()

        self.card_layout = QVBoxLayout()
        self.card_layout.setContentsMargins(10, 6, 10, 6)
        self.card_layout.setSpacing(2)

        self._rebuild_table()

        self.card.setLayout(self.card_layout)
        outer.addWidget(self.card)
        self.setLayout(outer)

    def _apply_card_style(self):
        """배경 + 테두리 스타일 (border_width=0 이면 테두리 없음)"""
        bg    = self.cfg.get("bg_color", BG_CARD)
        alpha = self.cfg.get("bg_alpha", 220)
        c     = QColor(bg)

        bw    = int(self.cfg.get("border_width", 0))
        bc    = self.cfg.get("border_color", "#1e3a4a")

        if bw > 0:
            border_css = f"border: {bw}px solid {bc};"
        else:
            border_css = "border: none;"

        self.card.setStyleSheet(f"""
            QWidget#card {{
                background-color: rgba({c.red()},{c.green()},{c.blue()},{alpha});
                {border_css}
                border-radius: 8px;
            }}
        """)

    # ── 테이블 재구성 ────────────────────────────────────────────────────────

    def _rebuild_table(self):
        """테이블 위젯 전체 재생성 후 캐시 가격으로 즉시 채우기"""
        # 기존 위젯 제거
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.table            = None
        self.row_items        = []
        self.col_map          = {}
        self.summary_row      = -1
        self.sum_current_item = None
        self.sum_profit_item  = None

        fs = self.cfg.get("font_size", 9)
        fc = self.cfg.get("font_color", FG_DEFAULT)

        # 종목 없을 때 안내
        if not self.stocks:
            lbl = QLabel("우클릭하여 종목을 설정해주세요.")
            lbl.setFont(QFont("Malgun Gothic", fs))
            lbl.setStyleSheet(
                f"color:{BLUE_ACCENT}; background:transparent; padding:12px 4px;"
            )
            lbl.setAlignment(Qt.AlignCenter)
            self.card_layout.addWidget(lbl)
            self._resize_to_content()
            return

        # ── 열 구성 ─────────────────────────────────────────────────────────
        col_map: dict[str, int] = {}
        idx = 0

        if self.cfg.get("show_name"):    col_map["name"]       = idx; idx += 1
        if self.cfg.get("show_code"):    col_map["code"]       = idx; idx += 1

        col_map["price"] = idx; idx += 1

        if self.cfg.get("show_change_amt"):
            col_map["change_amt"] = idx; idx += 1
        elif self.cfg.get("show_change_pct"):
            col_map["change_pct"] = idx; idx += 1

        if self.cfg.get("show_profit_amt"):
            col_map["profit_amt"] = idx; idx += 1
        elif self.cfg.get("show_profit_pct"):
            col_map["profit_pct"] = idx; idx += 1

        if self.cfg.get("show_total"):   col_map["total"]      = idx; idx += 1

        self.col_map = col_map
        col_count    = idx

        # ── 행 개수 ─────────────────────────────────────────────────────────
        row_count = len(self.stocks)
        if self.cfg.get("show_summary"):
            self.summary_row = row_count
            row_count += 1

        # ── QTableWidget ─────────────────────────────────────────────────────
        tbl = QTableWidget(row_count, col_count)
        tbl.setStyleSheet("""
            QTableWidget {
                background: transparent; border: none;
                gridline-color: rgba(41,182,246,8);
            }
            QTableWidget::item {
                padding: 1px 3px; border: none; background: transparent;
            }
            QHeaderView::section { background: transparent; border: none; padding: 0; }
            QScrollBar { width:0; height:0; }
        """)
        tbl.horizontalHeader().setVisible(False)
        tbl.verticalHeader().setVisible(False)
        tbl.setShowGrid(False)
        tbl.setSelectionMode(QTableWidget.NoSelection)
        tbl.setFocusPolicy(Qt.NoFocus)
        tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tbl.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)

        row_h = fs + 7
        for r in range(row_count):
            tbl.setRowHeight(r, row_h)

        # ── 데이터 행 초기화 ──────────────────────────────────────────────────
        for row, stock in enumerate(self.stocks):
            rd: dict[str, QTableWidgetItem] = {}
            code = stock.get("code", "")

            if "name" in col_map:
                it = self._make_item(stock.get("name", ""), fs - 1,
                                     Qt.AlignLeft | Qt.AlignVCenter, fc)
                tbl.setItem(row, col_map["name"], it)
                rd["name"] = it

            if "code" in col_map:
                it = self._make_item(code, fs - 1,
                                     Qt.AlignLeft | Qt.AlignVCenter, FG_DIM)
                tbl.setItem(row, col_map["code"], it)
                rd["code"] = it

            it = self._make_item("--", fs, Qt.AlignRight | Qt.AlignVCenter, fc, bold=True)
            tbl.setItem(row, col_map["price"], it)
            rd["price"] = it

            for key in ("change_amt", "change_pct", "profit_amt", "profit_pct", "total"):
                if key in col_map:
                    it = self._make_item("--", fs - 1,
                                         Qt.AlignRight | Qt.AlignVCenter, fc)
                    tbl.setItem(row, col_map[key], it)
                    rd[key] = it

            self.row_items.append(rd)

        # ── 요약 행 ──────────────────────────────────────────────────────────
        if self.summary_row >= 0:
            sr = self.summary_row
            for c in range(col_count):
                tbl.setItem(sr, c, QTableWidgetItem(""))
            self.sum_current_item = self._make_item(
                "--", fs - 1, Qt.AlignLeft | Qt.AlignVCenter, BLUE_ACCENT)
            tbl.setItem(sr, 0, self.sum_current_item)
            self.sum_profit_item = self._make_item(
                "--", fs - 1, Qt.AlignRight | Qt.AlignVCenter, BLUE_ACCENT)
            tbl.setItem(sr, col_count - 1, self.sum_profit_item)

        tbl.resizeColumnsToContents()
        tbl.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        tbl.installEventFilter(self)
        tbl.viewport().installEventFilter(self)

        self.card_layout.addWidget(tbl)
        self.table = tbl

        # ── 캐시된 가격으로 즉시 채우기 (빈 화면 방지) ───────────────────────
        if self._price_cache:
            self._apply_prices_from_cache()

        self._resize_to_content()
        logger.debug(f"table rebuilt: {row_count}r x {col_count}c")

    def _apply_prices_from_cache(self):
        """캐시에 있는 가격을 현재 테이블에 즉시 반영 (API 호출 없음)"""
        if not self.table:
            return
        fc        = self.cfg.get("font_color", FG_DEFAULT)
        total_buy = 0.0
        total_cur = 0.0

        for i, stock in enumerate(self.stocks):
            if i >= len(self.row_items):
                break
            data = self._price_cache.get(stock.get("code", ""))
            if data is None:
                continue
            self._fill_row(i, stock, data, fc)
            buy = float(stock.get("buy_price", 0))
            qty = int(stock.get("quantity", 0))
            total_buy += buy * qty
            total_cur += data["current"] * qty

        if self.table:
            self.table.resizeColumnsToContents()

        self._fill_summary(total_buy, total_cur, fc)
        self._resize_to_content()

    # ── 아이템 생성 헬퍼 ────────────────────────────────────────────────────

    @staticmethod
    def _make_item(text, font_size, align, color, bold=False) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        f  = QFont("Malgun Gothic", font_size)
        if bold:
            f.setWeight(QFont.Bold)
        it.setFont(f)
        it.setForeground(QBrush(QColor(color)))
        it.setTextAlignment(align)
        return it

    # ── 가격 갱신 ────────────────────────────────────────────────────────────

    def update_prices(self):
        """비동기로 가격 조회 시작. 이전 fetcher 가 살아있으면 재시작만."""
        if not self.stocks:
            self._resize_to_content()
            return

        # 이전 fetcher 가 아직 실행 중이면 중단하고 새로 시작
        if self._fetcher and self._fetcher.isRunning():
            self._fetcher.done.disconnect()
            self._fetcher.quit()
            self._fetcher = None

        fetcher = _PriceFetcher(self.stocks)
        fetcher.done.connect(self._on_prices_fetched)
        fetcher.finished.connect(fetcher.deleteLater)
        self._fetcher = fetcher
        fetcher.start()

    def _on_prices_fetched(self, results: list):
        """백그라운드 조회 완료 → UI 갱신"""
        if self.table is None:
            return

        fc        = self.cfg.get("font_color", FG_DEFAULT)
        total_buy = 0.0
        total_cur = 0.0

        for i, (stock, data) in enumerate(zip(self.stocks, results)):
            if i >= len(self.row_items):
                break

            code = stock.get("code", "")

            if data is None:
                rd = self.row_items[i]
                rd["price"].setText("ERR")
                rd["price"].setForeground(QBrush(QColor("#ff4444")))
                continue

            # 캐시 업데이트
            self._price_cache[code] = data

            self._fill_row(i, stock, data, fc)
            buy = float(stock.get("buy_price", 0))
            qty = int(stock.get("quantity", 0))
            total_buy += buy * qty
            total_cur += data["current"] * qty

        if self.table:
            self.table.resizeColumnsToContents()

        self._fill_summary(total_buy, total_cur, fc)
        self._resize_to_content()

    def _fill_row(self, i: int, stock: dict, data: dict, fc: str):
        """하나의 행에 데이터를 채움"""
        rd      = self.row_items[i]
        cur     = data["current"]
        chg     = data["change"]
        chg_pct = data["change_pct"]
        buy     = float(stock.get("buy_price", 0))
        qty     = int(stock.get("quantity", 0))
        pft_amt = (cur - buy) * qty
        pft_pct = (cur - buy) / buy * 100 if buy != 0 else 0.0
        total   = cur * qty

        arrow  = "▲" if chg > 0 else ("▼" if chg < 0 else "─")
        c_col  = self._change_color(chg)
        p_col  = self._change_color(pft_amt)

        if "name" in rd:
            rd["name"].setText(stock.get("name", ""))
            rd["name"].setForeground(QBrush(QColor(fc)))

        if "code" in rd:
            rd["code"].setText(stock.get("code", ""))
            rd["code"].setForeground(QBrush(QColor(FG_DIM)))

        price_col = c_col if self.cfg.get("use_change_color") else fc
        if cur == int(cur):
            rd["price"].setText(f"{int(cur):,}")
        else:
            rd["price"].setText(f"{cur:,.2f}")
        rd["price"].setForeground(QBrush(QColor(price_col)))

        if "change_amt" in rd:
            rd["change_amt"].setText(f"{arrow}{chg:+,.0f}")
            rd["change_amt"].setForeground(QBrush(QColor(c_col)))
        elif "change_pct" in rd:
            rd["change_pct"].setText(f"{arrow}{chg_pct:+.2f}%")
            rd["change_pct"].setForeground(QBrush(QColor(c_col)))

        if "profit_amt" in rd:
            sign = "+" if pft_amt >= 0 else ""
            rd["profit_amt"].setText(
                f"{sign}{int(pft_amt):,}" if pft_amt == int(pft_amt)
                else f"{sign}{pft_amt:,.2f}"
            )
            rd["profit_amt"].setForeground(QBrush(QColor(p_col)))
        elif "profit_pct" in rd:
            rd["profit_pct"].setText(f"{pft_pct:+.2f}%")
            rd["profit_pct"].setForeground(QBrush(QColor(p_col)))

        if "total" in rd:
            rd["total"].setText(
                f"{int(total):,}" if total == int(total) else f"{total:,.2f}"
            )
            rd["total"].setForeground(QBrush(QColor(fc)))

    def _fill_summary(self, total_buy: float, total_cur: float, fc: str):
        """요약 행 갱신"""
        if self.summary_row < 0 or not self.sum_current_item or not self.sum_profit_item:
            return
        total_pft     = total_cur - total_buy
        total_pft_pct = (total_pft / total_buy * 100) if total_buy > 0 else 0.0
        p_col         = self._change_color(total_pft)
        sign          = "+" if total_pft >= 0 else ""

        self.sum_current_item.setText(f"총{int(total_cur):,}")
        self.sum_current_item.setForeground(QBrush(QColor(BLUE_ACCENT)))
        self.sum_profit_item.setText(
            f"{sign}{int(total_pft):,} ({total_pft_pct:+.2f}%)"
        )
        self.sum_profit_item.setForeground(QBrush(QColor(p_col)))

    def _resize_to_content(self):
        if self.card:
            self.card.adjustSize()
            self.resize(self.card.sizeHint())

    def _change_color(self, value: float) -> str:
        if not self.cfg.get("use_change_color", True):
            return self.cfg.get("font_color", FG_DEFAULT)
        invert = self.cfg.get("invert_color", False)
        if value > 0:   return RED_SOFT   if invert else BLUE_LIGHT
        elif value < 0: return BLUE_LIGHT if invert else RED_SOFT
        return "#777777"

    # ── 설정 / 종목 반영 ─────────────────────────────────────────────────────

    def apply_settings(self, cfg: dict):
        """설정 저장 후 즉시 반영"""
        logger.info("apply_settings called")
        self.cfg = cfg
        self._apply_card_style()

        # always_on_top 변경: 현재 위치 보존 후 재표시
        pos   = self.pos()
        flags = Qt.FramelessWindowHint | Qt.Tool
        if cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.move(pos)
        self.show()

        # 타이머 주기 갱신
        self.timer.start(max(3000, cfg.get("interval_ms", 10000)))

        # 테이블 재구성 → 캐시로 즉시 채우기 → 비동기 갱신
        self._rebuild_table()
        self.update_prices()

    def apply_stocks(self, stocks: list):
        """종목 저장 후 즉시 반영"""
        logger.info(f"apply_stocks called: {len(stocks)} items")
        self.stocks = [s for s in stocks if s.get("active", True)]
        self._rebuild_table()
        self.update_prices()

    # ── 드래그 ───────────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos    = e.globalPos() - self.frameGeometry().topLeft()
            self._is_dragging = True
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._is_dragging and e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._is_dragging = False
        super().mouseReleaseEvent(e)

    def eventFilter(self, obj, event):
        et = event.type()
        if et == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self._drag_pos    = event.globalPos() - self.frameGeometry().topLeft()
                self._is_dragging = True
            return False
        elif et == QEvent.MouseMove:
            if self._is_dragging and event.buttons() == Qt.LeftButton:
                self.move(event.globalPos() - self._drag_pos)
                return True
        elif et == QEvent.MouseButtonRelease:
            self._is_dragging = False
        return super().eventFilter(obj, event)

    # ── 우클릭 메뉴 ──────────────────────────────────────────────────────────

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.addAction("ℹ  정보",             self._open_info)
        menu.addAction("📖  사용법",           self._open_usage)
        menu.addAction("📜  오픈소스 라이선스",  self._open_license)
        menu.addSeparator()
        menu.addAction("📈  종목 수정",         self._open_stocks)
        menu.addAction("⚙  환경설정",          self._open_settings)
        menu.addSeparator()
        menu.addAction("✕  종료하기",           QApplication.quit)
        menu.exec_(e.globalPos())

    # ── 다이얼로그 ───────────────────────────────────────────────────────────

    def _open_info(self):
        from dialogs.info_dialog import InfoDialog
        InfoDialog(self).exec_()

    def _open_usage(self):
        from dialogs.usage_dialog import UsageDialog
        UsageDialog(self).exec_()

    def _open_license(self):
        from dialogs.license_dialog import LicenseDialog
        LicenseDialog(self).exec_()

    def _open_stocks(self):
        from dialogs.stock_dialog import StockDialog
        dlg = StockDialog(self.data_dir, self.stocks, self)
        dlg.stocks_updated.connect(self.apply_stocks)
        dlg.exec_()

    def _open_settings(self):
        from dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.data_dir, self.cfg, self)
        dlg.settings_updated.connect(self.apply_settings)
        dlg.exec_()
