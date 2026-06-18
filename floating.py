"""
FloatingWidget  —  주식 정보 플로팅 위젯

버그 수정:
  - _PriceFetcher: quit()+wait() 로 안전 종료, deleteLater 미사용
    → "Destroyed while thread is still running" 완전 해결
  - 가격 조회 중 로딩 UI 표시 (_loading / _fetching 플래그)
드래그: table + viewport 양쪽에 eventFilter 설치
즉시갱신: 설정/종목 저장 후 캐시로 즉시 표시, 비동기 새로고침
컬럼 합산: change_amt+change_pct → change 단일 컬럼 (▲500(5.00%) 형식)
증감 색상: use_change_color 일 때 해당 행 전체(종목명 포함) 색상 적용
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMenu,
    QTableWidget, QTableWidgetItem,
)
from PyQt5.QtCore import Qt, QPoint, QTimer, QEvent, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush

from core.fetcher import fetch_price
import core.logger as logger


# ── 디자인 토큰 ──────────────────────────────────────────────────────────────
ACCENT     = "#5D87F6"   # 파랑 포인트
RISE_COLOR = "#7DA4F8"   # 상승 (밝은 파랑)
FALL_COLOR = "#F06292"   # 하락 (분홍)
FG_DEFAULT = "#E0E0E0"   # 주요 텍스트
FG_DIM     = "#606060"   # 희미한 텍스트
BG_CARD    = "#1A1B1C"   # 플로팅 카드 기본 배경

# 하위 호환성 alias
BLUE_ACCENT = ACCENT
BLUE_LIGHT  = RISE_COLOR
RED_SOFT    = FALL_COLOR

MENU_STYLE = f"""
QMenu {{
    background: #242526;
    color: {FG_DEFAULT};
    border: 1px solid #3A3B3C;
    padding: 4px;
    border-radius: 6px;
}}
QMenu::item {{ padding: 7px 22px; border-radius: 4px; font-size: 9pt; }}
QMenu::item:selected {{ background: #1E2A4A; color: {ACCENT}; }}
QMenu::separator {{ background: #3A3B3C; height: 1px; margin: 3px 6px; }}
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
        self.card             = None
        self.table            = None
        self.row_items        = []
        self.col_map          = {}
        self.summary_row      = -1
        self.sum_current_item = None
        self.sum_profit_item  = None

        # ── 비동기 fetcher 관리 ──────────────────────────────────────────────
        # ★ 절대 deleteLater 사용 금지 ★
        # finished 시그널로 포인터만 None 처리, 수명은 self 가 관리
        # 이전 fetcher 교체 시 wait() 로 완전 종료 확인 후 참조 해제
        self._fetcher: _PriceFetcher | None = None

        # 로딩 상태 플래그
        self._loading  = True    # 프로그램 최초 시작 중
        self._fetching = False   # 비동기 fetch 진행 중 여부

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

        bw = int(self.cfg.get("border_width", 0))
        bc = self.cfg.get("border_color", "#3A3B3C")

        border_css = f"border: {bw}px solid {bc};" if bw > 0 else "border: none;"

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

        # ── 로딩 중 또는 fetch 진행 중 표시 ────────────────────────────────
        # ★ _fetching 중이면 캐시 유무와 무관하게 항상 로딩 문구 표시 ★
        if self._loading and not self._price_cache:
            self._show_loading_ui(fs, "프로그램 준비중...")
            return

        if self._fetching and not self._price_cache:
            self._show_loading_ui(fs, "데이터 불러오는 중")
            return

        # ── 종목 없을 때 안내 ────────────────────────────────────────────────
        if not self.stocks:
            lbl = QLabel("우클릭하여 종목을 설정해주세요.")
            lbl.setFont(QFont("Malgun Gothic", fs))
            lbl.setStyleSheet(
                f"color:{ACCENT}; background:transparent; padding:12px 4px;"
            )
            lbl.setAlignment(Qt.AlignCenter)
            self.card_layout.addWidget(lbl)
            self._resize_to_content()
            return

        # ── 열 구성 ─────────────────────────────────────────────────────────
        # change_amt / change_pct 를 하나의 "change" 컬럼으로 합산
        # show_change_amt=True  → ▲500
        # show_change_pct=True  → ▲5.00%
        # 둘 다 True            → ▲500(5.00%)
        col_map: dict[str, int] = {}
        idx = 0

        if self.cfg.get("show_name"):    col_map["name"]  = idx; idx += 1
        if self.cfg.get("show_code"):    col_map["code"]  = idx; idx += 1

        col_map["price"] = idx; idx += 1

        # change: amt와 pct 중 하나 이상 켜져 있으면 단일 컬럼
        if self.cfg.get("show_change_amt") or self.cfg.get("show_change_pct"):
            col_map["change"] = idx; idx += 1

        # profit: amt와 pct 중 하나 이상 켜져 있으면 단일 컬럼
        if self.cfg.get("show_profit_amt") or self.cfg.get("show_profit_pct"):
            col_map["profit"] = idx; idx += 1

        if self.cfg.get("show_total"):   col_map["total"] = idx; idx += 1

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
                gridline-color: rgba(90,90,90,15);
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

        # ── 데이터 행 초기화 ────────────────────────────────────────────────
        for row, stock in enumerate(self.stocks):
            rd: dict[str, QTableWidgetItem] = {}

            if "name" in col_map:
                it = self._make_item(stock.get("name", ""), fs - 1,
                                     Qt.AlignLeft | Qt.AlignVCenter, fc)
                tbl.setItem(row, col_map["name"], it)
                rd["name"] = it

            if "code" in col_map:
                it = self._make_item(stock.get("code", ""), fs - 1,
                                     Qt.AlignLeft | Qt.AlignVCenter, FG_DIM)
                tbl.setItem(row, col_map["code"], it)
                rd["code"] = it

            it = self._make_item("--", fs, Qt.AlignRight | Qt.AlignVCenter, fc, bold=True)
            tbl.setItem(row, col_map["price"], it)
            rd["price"] = it

            for key in ("change", "profit", "total"):
                if key in col_map:
                    it = self._make_item("--", fs - 1,
                                         Qt.AlignRight | Qt.AlignVCenter, fc)
                    tbl.setItem(row, col_map[key], it)
                    rd[key] = it

            self.row_items.append(rd)

        # ── 요약 행 ─────────────────────────────────────────────────────────
        if self.summary_row >= 0:
            sr = self.summary_row
            for c in range(col_count):
                tbl.setItem(sr, c, QTableWidgetItem(""))
            self.sum_current_item = self._make_item(
                "--", fs - 1, Qt.AlignLeft | Qt.AlignVCenter, ACCENT)
            tbl.setItem(sr, 0, self.sum_current_item)
            self.sum_profit_item = self._make_item(
                "--", fs - 1, Qt.AlignRight | Qt.AlignVCenter, ACCENT)
            tbl.setItem(sr, col_count - 1, self.sum_profit_item)

        tbl.resizeColumnsToContents()
        tbl.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        tbl.installEventFilter(self)
        tbl.viewport().installEventFilter(self)

        self.card_layout.addWidget(tbl)
        self.table = tbl

        # 캐시된 가격으로 즉시 채우기 (빈 화면 방지)
        if self._price_cache:
            self._apply_prices_from_cache()

        self._resize_to_content()
        logger.debug(f"table rebuilt: {row_count}r x {col_count}c")

    def _show_loading_ui(self, fs: int, text: str = "프로그램 준비중..."):
        """가격 조회 중 가로형 로딩 UI — 문구만 보이는 얇은 바"""
        row = QHBoxLayout()
        row.setContentsMargins(10, 2, 10, 2)   # 위/아래 최소 여백
        row.setSpacing(5)

        dot = QLabel("●")
        dot.setFont(QFont("Malgun Gothic", max(6, fs - 2)))
        dot.setStyleSheet(f"color: {ACCENT}; background: transparent;")

        lbl = QLabel(text)
        lbl.setFont(QFont("Malgun Gothic", fs))
        lbl.setStyleSheet(f"color: {FG_DEFAULT}; background: transparent;")

        row.addWidget(dot)
        row.addWidget(lbl)
        row.addStretch()

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wrapper.setLayout(row)
        wrapper.setMinimumWidth(160)
        # 높이 = 폰트 크기 + 위아래 여백(4) + 약간의 여유(4)
        wrapper.setFixedHeight(fs + 12)

        self.card_layout.setContentsMargins(10, 4, 10, 4)  # 카드 자체 여백도 최소화
        self.card_layout.addWidget(wrapper)
        self._resize_to_content()

    def _apply_prices_from_cache(self):
        """캐시에 있는 가격을 현재 테이블에 즉시 반영"""
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
        """비동기로 가격 조회 시작."""
        if not self.stocks:
            self._loading  = False
            self._fetching = False
            self._resize_to_content()
            return

        # ── 이전 fetcher 안전 종료 ──────────────────────────────────────────
        # ★ 핵심: quit() 후 wait()로 스레드가 완전히 끝날 때까지 대기 ★
        # wait() 없이 _fetcher = None 을 하면 Python GC 가 QThread 객체를
        # 파괴할 때 스레드가 아직 실행 중 → "Destroyed while thread is still running"
        if self._fetcher is not None:
            try:
                if self._fetcher.isRunning():
                    # done 시그널 연결 끊기 (중복 _on_prices_fetched 방지)
                    try:
                        self._fetcher.done.disconnect(self._on_prices_fetched)
                    except (TypeError, RuntimeError):
                        pass
                    # finished 시그널 연결 끊기
                    try:
                        self._fetcher.finished.disconnect(self._on_fetcher_finished)
                    except (TypeError, RuntimeError):
                        pass
                    self._fetcher.quit()
                    # 최대 2초 대기 — 네트워크 요청이 있으므로 여유 있게
                    if not self._fetcher.wait(2000):
                        # 2초 후에도 종료 안 되면 강제 종료 (최후 수단)
                        self._fetcher.terminate()
                        self._fetcher.wait(1000)
            except RuntimeError:
                pass   # C++ 객체 이미 파괴된 경우 무시
            self._fetcher = None

        self._fetching = True   # fetch 시작 → 로딩 표시 활성화

        fetcher = _PriceFetcher(self.stocks)
        fetcher.done.connect(self._on_prices_fetched)
        fetcher.finished.connect(self._on_fetcher_finished)
        self._fetcher = fetcher
        fetcher.start()

    def _on_fetcher_finished(self):
        """스레드 종료 시 포인터만 정리 (객체 파괴 X — deleteLater 절대 사용 안 함)"""
        self._fetcher = None

    def _on_prices_fetched(self, results: list):
        """백그라운드 조회 완료 → UI 갱신"""
        was_loading  = self._loading
        was_fetching = self._fetching
        self._loading  = False   # 첫 조회 완료 → 로딩 플래그 해제
        self._fetching = False   # fetch 완료 → fetching 플래그 해제

        if was_loading or (was_fetching and self.table is None):
            # 로딩/fetching 화면을 실제 테이블로 교체
            self._rebuild_table()
            if self.table is None:
                return

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
                rd["price"].setForeground(QBrush(QColor("#FF5555")))
                continue

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

        arrow = "▲" if chg > 0 else ("▼" if chg < 0 else "─")
        c_col = self._change_color(chg)
        p_col = self._change_color(pft_amt)

        # 행 전체에 적용할 기본 글자색
        # use_change_color 가 켜져 있으면 행 전체를 등락 색상으로 통일
        use_color = self.cfg.get("use_change_color", True)
        row_col   = c_col if use_color else fc  # 종목명·가격 등 모든 셀에 적용

        # ── 종목명 ─────────────────────────────────────────────────────────
        if "name" in rd:
            rd["name"].setText(stock.get("name", ""))
            rd["name"].setForeground(QBrush(QColor(row_col)))

        # ── 종목코드 ───────────────────────────────────────────────────────
        if "code" in rd:
            rd["code"].setText(stock.get("code", ""))
            # 코드는 색상을 약간 dim하게 (row_col 에서 알파 조정 대신 FG_DIM 유지)
            rd["code"].setForeground(QBrush(QColor(FG_DIM)))

        # ── 현재가 ─────────────────────────────────────────────────────────
        if cur == int(cur):
            rd["price"].setText(f"{int(cur):,}")
        else:
            rd["price"].setText(f"{cur:,.2f}")
        rd["price"].setForeground(QBrush(QColor(row_col)))

        # ── 변동 (change) — amt + pct 합산 컬럼 ──────────────────────────
        if "change" in rd:
            show_amt = self.cfg.get("show_change_amt", False)
            show_pct = self.cfg.get("show_change_pct", False)

            if show_amt and show_pct:
                # ▲500(5.00%) 형식
                rd["change"].setText(f"{arrow}{chg:+,.0f}({chg_pct:+.2f}%)")
            elif show_amt:
                # ▲500 형식
                rd["change"].setText(f"{arrow}{chg:+,.0f}")
            elif show_pct:
                # ▲5.00% 형식
                rd["change"].setText(f"{arrow}{chg_pct:+.2f}%")
            else:
                rd["change"].setText("")
            rd["change"].setForeground(QBrush(QColor(c_col)))

        # ── 손익 (profit) — amt + pct 합산 컬럼 ──────────────────────────
        if "profit" in rd:
            show_amt = self.cfg.get("show_profit_amt", False)
            show_pct = self.cfg.get("show_profit_pct", False)
            p_arrow  = "▲" if pft_amt > 0 else ("▼" if pft_amt < 0 else "─")

            if show_amt and show_pct:
                # ▲49,000(49.00%) 형식
                amt_str = (f"{int(pft_amt):+,}" if pft_amt == int(pft_amt)
                           else f"{pft_amt:+,.2f}")
                rd["profit"].setText(f"{p_arrow}{amt_str[1:]}({pft_pct:+.2f}%)")
            elif show_amt:
                amt_str = (f"{int(pft_amt):+,}" if pft_amt == int(pft_amt)
                           else f"{pft_amt:+,.2f}")
                rd["profit"].setText(f"{p_arrow}{amt_str[1:]}")
            elif show_pct:
                rd["profit"].setText(f"{p_arrow}{abs(pft_pct):.2f}%")
            else:
                rd["profit"].setText("")
            rd["profit"].setForeground(QBrush(QColor(p_col)))

        # ── 총평가액 ───────────────────────────────────────────────────────
        if "total" in rd:
            rd["total"].setText(
                f"{int(total):,}" if total == int(total) else f"{total:,.2f}"
            )
            rd["total"].setForeground(QBrush(QColor(row_col)))

    def _fill_summary(self, total_buy: float, total_cur: float, fc: str):
        """요약 행 갱신"""
        if self.summary_row < 0 or not self.sum_current_item or not self.sum_profit_item:
            return
        total_pft     = total_cur - total_buy
        total_pft_pct = (total_pft / total_buy * 100) if total_buy > 0 else 0.0
        p_col         = self._change_color(total_pft)
        sign          = "+" if total_pft >= 0 else ""

        self.sum_current_item.setText(f"총{int(total_cur):,}")
        self.sum_current_item.setForeground(QBrush(QColor(ACCENT)))
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
        if value > 0:   return FALL_COLOR if invert else RISE_COLOR
        elif value < 0: return RISE_COLOR if invert else FALL_COLOR
        return "#707070"

    # ── 설정 / 종목 반영 ─────────────────────────────────────────────────────

    def apply_settings(self, cfg: dict):
        """설정 저장 후 즉시 반영"""
        logger.info("apply_settings called")
        self.cfg = cfg
        self._apply_card_style()

        pos   = self.pos()
        flags = Qt.FramelessWindowHint | Qt.Tool
        if cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.move(pos)
        self.show()

        self.timer.start(max(3000, cfg.get("interval_ms", 10000)))
        self._fetching = True   # 저장 직후 데이터 재조회 중 표시
        self._rebuild_table()
        self.update_prices()

    def apply_stocks(self, stocks: list):
        """종목 저장 후 즉시 반영"""
        logger.info(f"apply_stocks called: {len(stocks)} items")
        self.stocks    = [s for s in stocks if s.get("active", True)]
        self._fetching = True   # 저장 직후 데이터 재조회 중 표시
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
