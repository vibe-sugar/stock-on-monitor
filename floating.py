"""
FloatingWidget  —  주식 정보 플로팅 위젯

드래그 처리 방식:
  - 위젯 전체(카드, 테이블 포함)에서 마우스 프레스/무브 이벤트를 eventFilter 로 잡아
    어느 위치를 클릭해도 창을 이동할 수 있도록 했습니다.
  - QTableWidget 은 itemClicked 등 자체 이벤트를 소비하므로
    eventFilter 에서 mousePress / mouseMove 이벤트를 직접 처리합니다.

블루 포인트 테마:
  - 배경: 거의 검정 (#0d0d0d)
  - 포인트: 밝은 파랑 (#29b6f6, #4fc3f7)
  - 일반 글자: 밝은 회색 (#b0b0b0)
  - 상승: #29b6f6 (파랑) / 하락: #ef5350 (빨강)  — invert 설정으로 반전 가능
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QMenu,
    QTableWidget, QTableWidgetItem,
)
from PyQt5.QtCore import Qt, QPoint, QTimer, QEvent
from PyQt5.QtGui import QFont, QColor, QBrush

from core.fetcher import fetch_price
from core.constants import APP_NAME
import core.logger as logger


# ── 색상 팔레트 ──────────────────────────────────────────────────────────────
BLUE_ACCENT   = "#29b6f6"   # 밝은 파란색 포인트
BLUE_LIGHT    = "#4fc3f7"   # 더 밝은 파랑 (상승 색)
RED_SOFT      = "#ef5350"   # 부드러운 빨강 (하락 색)
FG_DEFAULT    = "#b0b0b0"   # 기본 글자색
FG_DIM        = "#666666"   # 흐릿한 글자색
BG_CARD       = "#0d0d0d"   # 카드 배경
BORDER_COLOR  = "#1e3a4a"   # 파란 계열 테두리

MENU_STYLE = f"""
QMenu {{
    background: #0f1f2a;
    color: {FG_DEFAULT};
    border: 1px solid {BORDER_COLOR};
    padding: 4px;
    border-radius: 4px;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: 3px;
}}
QMenu::item:selected {{
    background: #1a3a4a;
    color: {BLUE_ACCENT};
}}
QMenu::separator {{
    background: {BORDER_COLOR};
    height: 1px;
    margin: 3px 4px;
}}
"""


class FloatingWidget(QWidget):
    """메인 플로팅 위젯"""

    def __init__(self, data_dir: str, cfg: dict, stocks: list):
        super().__init__()
        self.data_dir = data_dir
        self.cfg      = cfg
        self.stocks   = [s for s in stocks if s.get("active", True)]

        # 드래그 상태
        self._drag_pos    = QPoint()
        self._is_dragging = False

        # UI 내부 참조
        self.card      = None
        self.table     = None
        self.row_items = []   # list[dict[str, QTableWidgetItem]]
        self.col_map   = {}   # {"name": 0, "price": 1, ...}
        self.summary_row = -1
        self.sum_current_item  = None
        self.sum_profit_item   = None

        logger.info(f"FloatingWidget init: {len(self.stocks)} stocks")
        self._build_ui()
        self._setup_flags()

        # 가격 갱신 타이머
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_prices)
        interval = max(3000, self.cfg.get("interval_ms", 10000))
        self.timer.start(interval)
        self.update_prices()

    # ── 초기화 ──────────────────────────────────────────────────────────────

    def _setup_flags(self):
        """윈도우 플래그 및 항상 위 설정"""
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.show()
        logger.debug(f"window flags set: always_on_top={self.cfg.get('always_on_top', True)}")

    def _build_ui(self):
        """최상위 레이아웃 구성 (card 래퍼)"""
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
        """카드 배경 스타일 (파란색 테두리 포인트)"""
        bg    = self.cfg.get("bg_color", BG_CARD)
        alpha = self.cfg.get("bg_alpha", 220)
        c     = QColor(bg)
        self.card.setStyleSheet(f"""
            QWidget#card {{
                background-color: rgba({c.red()},{c.green()},{c.blue()},{alpha});
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
            }}
        """)

    # ── 테이블 재구성 ────────────────────────────────────────────────────────

    def _rebuild_table(self):
        """테이블 위젯 전체 재생성"""
        # 기존 위젯 제거
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.table          = None
        self.row_items      = []
        self.col_map        = {}
        self.summary_row    = -1
        self.sum_current_item = None
        self.sum_profit_item  = None

        fs = self.cfg.get("font_size", 9)
        fc = self.cfg.get("font_color", FG_DEFAULT)

        # 종목 없을 때 안내 레이블
        if not self.stocks:
            lbl = QLabel("우클릭하여 종목을 설정해주세요.")
            lbl.setFont(QFont("Malgun Gothic", fs))
            lbl.setStyleSheet(f"color:{BLUE_ACCENT}; background:transparent; padding:12px 4px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.card_layout.addWidget(lbl)
            return

        # ── 열 구성 계산 ────────────────────────────────────────────────────
        col_map: dict[str, int] = {}
        idx = 0

        if self.cfg.get("show_name"):
            col_map["name"] = idx; idx += 1
        if self.cfg.get("show_code"):
            col_map["code"] = idx; idx += 1

        col_map["price"] = idx; idx += 1

        # 변동액 vs 변동률 (둘 다 체크돼 있어도 변동액 우선)
        if self.cfg.get("show_change_amt"):
            col_map["change_amt"] = idx; idx += 1
        elif self.cfg.get("show_change_pct"):
            col_map["change_pct"] = idx; idx += 1

        # 손익액 vs 손익률
        if self.cfg.get("show_profit_amt"):
            col_map["profit_amt"] = idx; idx += 1
        elif self.cfg.get("show_profit_pct"):
            col_map["profit_pct"] = idx; idx += 1

        if self.cfg.get("show_total"):
            col_map["total"] = idx; idx += 1

        self.col_map = col_map
        col_count    = idx
        logger.debug(f"col_map: {col_map}")

        # ── 행 개수 계산 ─────────────────────────────────────────────────────
        row_count = len(self.stocks)
        if self.cfg.get("show_summary"):
            self.summary_row = row_count
            row_count += 1

        # ── QTableWidget 생성 ─────────────────────────────────────────────────
        tbl = QTableWidget(row_count, col_count)
        tbl.setStyleSheet(f"""
            QTableWidget {{
                background: transparent;
                border: none;
                gridline-color: rgba(41,182,246,8);
            }}
            QTableWidget::item {{
                padding: 1px 3px;
                border: none;
                background: transparent;
            }}
            QHeaderView::section {{
                background: transparent;
                border: none;
                padding: 0;
            }}
            QScrollBar {{ width:0; height:0; }}
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

        # ── 데이터 행 초기화 ─────────────────────────────────────────────────
        for row, stock in enumerate(self.stocks):
            rd: dict[str, QTableWidgetItem] = {}

            if "name" in col_map:
                it = self._make_item(stock.get("name", ""), fs - 1, Qt.AlignLeft | Qt.AlignVCenter, fc)
                tbl.setItem(row, col_map["name"], it)
                rd["name"] = it

            if "code" in col_map:
                it = self._make_item(stock.get("code", ""), fs - 1, Qt.AlignLeft | Qt.AlignVCenter, FG_DIM)
                tbl.setItem(row, col_map["code"], it)
                rd["code"] = it

            it = self._make_item("--", fs, Qt.AlignRight | Qt.AlignVCenter, fc, bold=True)
            tbl.setItem(row, col_map["price"], it)
            rd["price"] = it

            for key in ("change_amt", "change_pct", "profit_amt", "profit_pct", "total"):
                if key in col_map:
                    it = self._make_item("--", fs - 1, Qt.AlignRight | Qt.AlignVCenter, fc)
                    tbl.setItem(row, col_map[key], it)
                    rd[key] = it

            self.row_items.append(rd)

        # ── 요약 행 초기화 ───────────────────────────────────────────────────
        if self.summary_row >= 0:
            sr = self.summary_row
            # 빈 셀로 채우기
            for c in range(col_count):
                tbl.setItem(sr, c, QTableWidgetItem(""))

            self.sum_current_item = self._make_item(
                "--", fs - 1, Qt.AlignLeft | Qt.AlignVCenter, BLUE_ACCENT
            )
            tbl.setItem(sr, 0, self.sum_current_item)

            self.sum_profit_item = self._make_item(
                "--", fs - 1, Qt.AlignRight | Qt.AlignVCenter, BLUE_ACCENT
            )
            tbl.setItem(sr, col_count - 1, self.sum_profit_item)

        tbl.resizeColumnsToContents()
        tbl.setSizeAdjustPolicy(QTableWidget.AdjustToContents)

        # ── 드래그를 위한 이벤트 필터 등록 ──────────────────────────────────
        # 테이블 자체 + viewport 모두 필터 설치
        tbl.installEventFilter(self)
        tbl.viewport().installEventFilter(self)

        self.card_layout.addWidget(tbl)
        self.table = tbl
        logger.debug(f"table rebuilt: {row_count} rows x {col_count} cols")

    # ── 아이템 생성 헬퍼 ────────────────────────────────────────────────────

    @staticmethod
    def _make_item(
        text: str,
        font_size: int,
        align: int,
        color: str,
        bold: bool = False,
    ) -> QTableWidgetItem:
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
        """타이머 또는 직접 호출 시 모든 종목 가격 갱신"""
        if not self.stocks or self.table is None:
            self._resize_to_content()
            return

        fc          = self.cfg.get("font_color", FG_DEFAULT)
        total_buy   = 0.0
        total_cur   = 0.0

        for i, stock in enumerate(self.stocks):
            if i >= len(self.row_items):
                break
            rd   = self.row_items[i]
            data = fetch_price(stock["market"], stock["code"])

            if data is None:
                rd["price"].setText("ERR")
                rd["price"].setForeground(QBrush(QColor("#ff4444")))
                continue

            cur        = data["current"]
            chg        = data["change"]
            chg_pct    = data["change_pct"]
            buy        = float(stock.get("buy_price", 0))
            qty        = int(stock.get("quantity", 0))
            pft_amt    = (cur - buy) * qty
            pft_pct    = (cur - buy) / buy * 100 if buy != 0 else 0.0
            total      = cur * qty

            total_buy += buy * qty
            total_cur += total

            arrow  = "▲" if chg > 0 else ("▼" if chg < 0 else "─")
            c_col  = self._change_color(chg)
            p_col  = self._change_color(pft_amt)

            # 종목명
            if "name" in rd:
                rd["name"].setText(stock.get("name", ""))
                rd["name"].setForeground(QBrush(QColor(fc)))

            # 종목코드
            if "code" in rd:
                rd["code"].setText(stock.get("code", ""))
                rd["code"].setForeground(QBrush(QColor(FG_DIM)))

            # 현재가
            price_color = c_col if self.cfg.get("use_change_color") else fc
            rd["price"].setText(f"{int(cur):,}")
            rd["price"].setForeground(QBrush(QColor(price_color)))

            # 변동액
            if "change_amt" in rd:
                rd["change_amt"].setText(f"{arrow}{chg:+,.0f}")
                rd["change_amt"].setForeground(QBrush(QColor(c_col)))
            # 변동률
            elif "change_pct" in rd:
                rd["change_pct"].setText(f"{arrow}{chg_pct:+.2f}%")
                rd["change_pct"].setForeground(QBrush(QColor(c_col)))

            # 손익액
            if "profit_amt" in rd:
                sign = "+" if pft_amt >= 0 else ""
                rd["profit_amt"].setText(f"{sign}{int(pft_amt):,}")
                rd["profit_amt"].setForeground(QBrush(QColor(p_col)))
            # 손익률
            elif "profit_pct" in rd:
                rd["profit_pct"].setText(f"{pft_pct:+.2f}%")
                rd["profit_pct"].setForeground(QBrush(QColor(p_col)))

            # 총평가액
            if "total" in rd:
                rd["total"].setText(f"{int(total):,}")
                rd["total"].setForeground(QBrush(QColor(fc)))

        # 열 너비 자동 조정
        if self.table:
            self.table.resizeColumnsToContents()

        # 요약 행
        if self.summary_row >= 0 and self.sum_current_item and self.sum_profit_item:
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

        self._resize_to_content()

    def _resize_to_content(self):
        """카드 크기를 내용에 맞게 조정"""
        if self.card:
            self.card.adjustSize()
            self.resize(self.card.sizeHint())

    def _change_color(self, value: float) -> str:
        """값 부호에 따른 색상 반환"""
        if not self.cfg.get("use_change_color", True):
            return self.cfg.get("font_color", FG_DEFAULT)
        invert = self.cfg.get("invert_color", False)
        if value > 0:
            return RED_SOFT  if invert else BLUE_LIGHT
        elif value < 0:
            return BLUE_LIGHT if invert else RED_SOFT
        return "#777777"

    # ── 외부에서 설정 / 종목 반영 ────────────────────────────────────────────

    def apply_settings(self, cfg: dict):
        """설정 다이얼로그에서 저장 후 호출"""
        logger.info("apply_settings called")
        self.cfg = cfg
        self._apply_card_style()
        # always_on_top 변경 반영
        flags = Qt.FramelessWindowHint | Qt.Tool
        if cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 타이머 주기 갱신
        interval = max(3000, cfg.get("interval_ms", 10000))
        self.timer.start(interval)

        self._rebuild_table()
        self.show()
        self.update_prices()

    def apply_stocks(self, stocks: list):
        """종목 다이얼로그에서 저장 후 호출"""
        logger.info(f"apply_stocks called: {len(stocks)} items")
        self.stocks = [s for s in stocks if s.get("active", True)]
        self._rebuild_table()
        self.update_prices()

    # ── 드래그 이동 (이벤트 필터) ────────────────────────────────────────────

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
        """
        테이블 및 viewport 위의 마우스 이벤트를 가로채어 창 이동에 사용.
        QEvent 타입 상수를 직접 비교 (import 불필요).
        """
        et = event.type()

        # MouseButtonPress (2)
        if et == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self._drag_pos    = event.globalPos() - self.frameGeometry().topLeft()
                self._is_dragging = True
            # 컨텍스트 메뉴 표시를 위해 RightButton 은 통과
            return False   # 이벤트 소비 안 함 (테이블 자체 처리 허용)

        # MouseMove (5)
        elif et == QEvent.MouseMove:
            if self._is_dragging and event.buttons() == Qt.LeftButton:
                self.move(event.globalPos() - self._drag_pos)
                return True   # 이동 처리 → 테이블 셀 선택 방지

        # MouseButtonRelease (3)
        elif et == QEvent.MouseButtonRelease:
            self._is_dragging = False

        return super().eventFilter(obj, event)

    # ── 우클릭 컨텍스트 메뉴 ────────────────────────────────────────────────

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.addAction("ℹ  정보",            self._open_info)
        menu.addAction("📖  사용법",          self._open_usage)
        menu.addAction("📜  오픈소스 라이선스", self._open_license)
        menu.addSeparator()
        menu.addAction("📈  종목 수정",        self._open_stocks)
        menu.addAction("⚙  환경설정",         self._open_settings)
        menu.addSeparator()
        menu.addAction("✕  종료하기",          QApplication.quit)
        menu.exec_(e.globalPos())

    # ── 다이얼로그 열기 ──────────────────────────────────────────────────────

    def _open_info(self):
        from dialogs.info_dialog import InfoDialog
        dlg = InfoDialog(self)
        dlg.exec_()

    def _open_usage(self):
        from dialogs.usage_dialog import UsageDialog
        dlg = UsageDialog(self)
        dlg.exec_()

    def _open_license(self):
        from dialogs.license_dialog import LicenseDialog
        dlg = LicenseDialog(self)
        dlg.exec_()

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
