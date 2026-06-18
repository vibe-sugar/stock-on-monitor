"""
FloatingWidget  —  주식 정보 플로팅 위젯

설계 원칙:
  - 로딩 UI: QLabel 하나를 card 안에 고정으로 심고 show/hide 전환
             (deleteLater 비동기 문제 완전 회피)
  - 상태 흐름:
      프로그램 시작     → _state="loading"   → "프로그램 준비중..." 표시
      fetcher 시작      → _state="fetching"  → "데이터 불러오는 중" 표시
      fetcher 완료      → _state="ready"     → 실제 테이블 표시
  - QThread 안전 종료: quit()+wait(2000ms), deleteLater 미사용
  - 증감 색상: 현재가·변동·손익에만 적용 (종목명·합산행 제외)
  - 변동/손익 합산 컬럼: ▲500(5.00%) 형식
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMenu,
    QTableWidget, QTableWidgetItem, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt, QPoint, QTimer, QEvent, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush

from core.fetcher import fetch_price
import core.logger as logger


# ── 디자인 토큰 ──────────────────────────────────────────────────────────────
ACCENT     = "#5D87F6"
RISE_COLOR = "#7DA4F8"
FALL_COLOR = "#F06292"
FG_DEFAULT = "#E0E0E0"
FG_DIM     = "#606060"
BG_CARD    = "#1A1B1C"

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

# 상태 상수
_ST_LOADING  = "loading"   # 최초 시작
_ST_FETCHING = "fetching"  # 데이터 조회 중
_ST_READY    = "ready"     # 정상 표시


# ── 비동기 가격 갱신 스레드 ───────────────────────────────────────────────────
class _PriceFetcher(QThread):
    done = pyqtSignal(list)

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

        self._drag_pos    = QPoint()
        self._is_dragging = False
        self._price_cache: dict[str, dict] = {}

        # UI 내부 참조
        self.card             = None
        self._lbl_loading     = None   # 로딩 전용 라벨 (항상 card 안에 존재)
        self.table            = None
        self.row_items        = []
        self.col_map          = {}
        self.summary_row      = -1
        self.sum_current_item = None
        self.sum_profit_item  = None

        # fetcher
        self._fetcher: _PriceFetcher | None = None

        # 상태: loading → fetching → ready
        self._state: str = _ST_LOADING

        logger.info(f"FloatingWidget init: {len(self.stocks)} stocks")
        self._build_ui()
        self._setup_flags()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_prices)
        self.timer.start(max(3000, self.cfg.get("interval_ms", 10000)))

        # 최초 조회 — 로딩 문구 표시하면서 시작
        self._start_fetch(show_loading=True)

    # ── 초기화 ──────────────────────────────────────────────────────────────

    def _setup_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.show()

    def _build_ui(self):
        """카드 + 로딩라벨 + (비어있는) 테이블 영역을 구성."""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.card = QWidget(self)
        self.card.setObjectName("card")
        self._apply_card_style()

        self.card_layout = QVBoxLayout()
        self.card_layout.setContentsMargins(10, 5, 10, 5)
        self.card_layout.setSpacing(0)

        # ── 로딩 전용 라벨 (항상 존재, show/hide 로 전환) ──────────────────
        self._lbl_loading = self._make_loading_label("프로그램 준비중...")
        self.card_layout.addWidget(self._lbl_loading)
        # 초기에는 loading 상태이므로 바로 보임

        self.card.setLayout(self.card_layout)
        outer.addWidget(self.card)
        self.setLayout(outer)

        self._resize_to_content()

    def _make_loading_label(self, text: str) -> QLabel:
        """로딩 문구 QLabel 생성 — padding 없음, 폰트 크기 기준으로만 높이 결정."""
        fs  = self.cfg.get("font_size", 9)
        lbl = QLabel(f"● {text}")
        lbl.setFont(QFont("Malgun Gothic", fs))
        # padding/margin 완전 제거, background transparent
        lbl.setStyleSheet(
            f"color: {FG_DEFAULT};"
            "background: transparent;"
            "padding: 0px; margin: 0px;"
        )
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # 높이를 폰트 메트릭 기준으로 정확히 고정
        fm_h = lbl.fontMetrics().height()
        lbl.setFixedHeight(fm_h + 4)   # 폰트 높이 + 2px 여유 (위아래 각 1px)
        lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        return lbl

    def _apply_card_style(self):
        bg    = self.cfg.get("bg_color", BG_CARD)
        alpha = self.cfg.get("bg_alpha", 220)
        c     = QColor(bg)
        bw    = int(self.cfg.get("border_width", 0))
        bc    = self.cfg.get("border_color", "#3A3B3C")
        border_css = f"border: {bw}px solid {bc};" if bw > 0 else "border: none;"
        self.card.setStyleSheet(f"""
            QWidget#card {{
                background-color: rgba({c.red()},{c.green()},{c.blue()},{alpha});
                {border_css}
                border-radius: 8px;
            }}
        """)

    # ── 상태 전환 ────────────────────────────────────────────────────────────

    def _set_state(self, state: str, msg: str = ""):
        """상태를 전환하고 UI를 즉시 업데이트."""
        old = self._state
        self._state = state
        logger.info(f"[FloatingWidget] state: {old} → {state}  msg={msg!r}")

        if state in (_ST_LOADING, _ST_FETCHING):
            # 테이블 숨기기
            if self.table:
                self.table.hide()
            # 로딩 라벨 텍스트 업데이트 후 표시
            fs  = self.cfg.get("font_size", 9)
            txt = msg or ("프로그램 준비중..." if state == _ST_LOADING else "데이터 불러오는 중")
            self._lbl_loading.setFont(QFont("Malgun Gothic", fs))
            self._lbl_loading.setText(f"● {txt}")
            fm_h = self._lbl_loading.fontMetrics().height()
            self._lbl_loading.setFixedHeight(fm_h + 4)
            self._lbl_loading.show()
        else:
            # ready: 로딩 라벨 숨기기, 테이블 표시
            self._lbl_loading.hide()
            if self.table:
                self.table.show()

        self._resize_to_content()

    # ── fetch 시작 ────────────────────────────────────────────────────────────

    def _start_fetch(self, show_loading: bool = False):
        """
        fetcher 를 시작.

        show_loading=True  : 로딩 문구 표시 후 fetch (초기·설정/종목 저장 시)
        show_loading=False : 백그라운드 자동 갱신 — 현재 테이블 그대로 유지,
                             문구 전환 없음 (타이머 주기 갱신)
        """
        if not self.stocks:
            self._state = _ST_READY
            self._lbl_loading.hide()
            self._ensure_table()
            return

        # 이전 fetcher 안전 종료
        if self._fetcher is not None:
            try:
                if self._fetcher.isRunning():
                    try:
                        self._fetcher.done.disconnect(self._on_prices_fetched)
                    except (TypeError, RuntimeError):
                        pass
                    try:
                        self._fetcher.finished.disconnect(self._on_fetcher_finished)
                    except (TypeError, RuntimeError):
                        pass
                    self._fetcher.quit()
                    if not self._fetcher.wait(2000):
                        self._fetcher.terminate()
                        self._fetcher.wait(1000)
            except RuntimeError:
                pass
            self._fetcher = None

        if show_loading:
            # 로딩 문구 표시 상태로 전환
            self._set_state(_ST_FETCHING, "데이터 불러오는 중")
        # show_loading=False 이면 _state 변경 없음 → UI 그대로 유지

        fetcher = _PriceFetcher(self.stocks)
        fetcher.done.connect(self._on_prices_fetched)
        fetcher.finished.connect(self._on_fetcher_finished)
        self._fetcher = fetcher
        fetcher.start()
        logger.info(f"[FloatingWidget] fetcher started (show_loading={show_loading})")

    def update_prices(self):
        """타이머 주기 갱신 — 로딩 문구 없이 백그라운드에서만 갱신."""
        self._start_fetch(show_loading=False)

    def _on_fetcher_finished(self):
        self._fetcher = None
        logger.info("[FloatingWidget] fetcher finished (thread ended)")

    def _on_prices_fetched(self, results: list):
        logger.info(f"[FloatingWidget] prices fetched: {len(results)} results")
        self._state = _ST_READY

        # 테이블이 없으면 (처음 또는 설정 변경) 새로 빌드
        if self.table is None:
            self._build_table()

        if self.table is None:
            # stocks 없음 등으로 테이블 빌드 안 된 경우
            self._lbl_loading.hide()
            self._resize_to_content()
            return

        # 데이터 반영
        fc        = self.cfg.get("font_color", FG_DEFAULT)
        total_buy = 0.0
        total_cur = 0.0

        for i, (stock, data) in enumerate(zip(self.stocks, results)):
            if i >= len(self.row_items):
                break
            if data is None:
                self.row_items[i]["price"].setText("ERR")
                self.row_items[i]["price"].setForeground(QBrush(QColor("#FF5555")))
                continue
            self._price_cache[stock.get("code", "")] = data
            self._fill_row(i, stock, data, fc)
            total_buy += float(stock.get("buy_price", 0)) * int(stock.get("quantity", 0))
            total_cur += data["current"] * int(stock.get("quantity", 0))

        if self.table:
            self.table.resizeColumnsToContents()
        self._fill_summary(total_buy, total_cur, fc)

        # 로딩 라벨 숨기고 테이블 표시
        self._lbl_loading.hide()
        self.table.show()
        self._resize_to_content()

    # ── 테이블 보장 ──────────────────────────────────────────────────────────

    def _ensure_table(self):
        """table 이 없고 stocks 가 있으면 빌드. 캐시 있으면 즉시 채움."""
        if self.table is None and self.stocks:
            self._build_table()
            if self._price_cache and self.table:
                self._apply_prices_from_cache()

    # ── 테이블 재구성 ────────────────────────────────────────────────────────

    def _destroy_table(self):
        """현재 테이블 위젯을 card_layout 에서 제거하고 참조 초기화."""
        if self.table is not None:
            self.card_layout.removeWidget(self.table)
            self.table.deleteLater()
            self.table            = None
            self.row_items        = []
            self.col_map          = {}
            self.summary_row      = -1
            self.sum_current_item = None
            self.sum_profit_item  = None

    def _build_table(self):
        """테이블 위젯 새로 생성 후 card_layout 에 추가."""
        self._destroy_table()

        fs = self.cfg.get("font_size", 9)
        fc = self.cfg.get("font_color", FG_DEFAULT)

        if not self.stocks:
            # 종목 없음: 안내 라벨로 표시 (로딩 라벨 재활용)
            self._lbl_loading.setText("● 우클릭하여 종목을 설정해주세요.")
            self._lbl_loading.setStyleSheet(
                f"color: {ACCENT}; background: transparent; padding: 0px; margin: 0px;"
            )
            fm_h = self._lbl_loading.fontMetrics().height()
            self._lbl_loading.setFixedHeight(fm_h + 4)
            self._lbl_loading.show()
            self._resize_to_content()
            return

        # 열 구성
        col_map: dict[str, int] = {}
        idx = 0
        if self.cfg.get("show_name"):  col_map["name"]   = idx; idx += 1
        if self.cfg.get("show_code"):  col_map["code"]   = idx; idx += 1
        col_map["price"] = idx; idx += 1
        if self.cfg.get("show_change_amt") or self.cfg.get("show_change_pct"):
            col_map["change"] = idx; idx += 1
        if self.cfg.get("show_profit_amt") or self.cfg.get("show_profit_pct"):
            col_map["profit"] = idx; idx += 1
        if self.cfg.get("show_total"): col_map["total"]  = idx; idx += 1

        self.col_map = col_map
        col_count    = idx

        row_count = len(self.stocks)
        if self.cfg.get("show_summary"):
            self.summary_row = row_count
            row_count += 1

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

        for row, stock in enumerate(self.stocks):
            rd: dict[str, QTableWidgetItem] = {}
            if "name" in col_map:
                it = self._make_item(stock.get("name", ""), fs - 1,
                                     Qt.AlignLeft | Qt.AlignVCenter, fc)
                tbl.setItem(row, col_map["name"], it); rd["name"] = it
            if "code" in col_map:
                it = self._make_item(stock.get("code", ""), fs - 1,
                                     Qt.AlignLeft | Qt.AlignVCenter, FG_DIM)
                tbl.setItem(row, col_map["code"], it); rd["code"] = it
            it = self._make_item("--", fs, Qt.AlignRight | Qt.AlignVCenter, fc, bold=True)
            tbl.setItem(row, col_map["price"], it); rd["price"] = it
            for key in ("change", "profit", "total"):
                if key in col_map:
                    it = self._make_item("--", fs - 1,
                                         Qt.AlignRight | Qt.AlignVCenter, fc)
                    tbl.setItem(row, col_map[key], it); rd[key] = it
            self.row_items.append(rd)

        if self.summary_row >= 0:
            sr = self.summary_row
            for c in range(col_count):
                tbl.setItem(sr, c, QTableWidgetItem(""))
            self.sum_current_item = self._make_item(
                "--", fs - 1, Qt.AlignLeft | Qt.AlignVCenter, fc)
            tbl.setItem(sr, 0, self.sum_current_item)
            self.sum_profit_item = self._make_item(
                "--", fs - 1, Qt.AlignRight | Qt.AlignVCenter, fc)
            tbl.setItem(sr, col_count - 1, self.sum_profit_item)

        tbl.resizeColumnsToContents()
        tbl.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        tbl.installEventFilter(self)
        tbl.viewport().installEventFilter(self)

        # 로딩 라벨 뒤에 삽입
        self.card_layout.addWidget(tbl)
        self.table = tbl

        # 상태에 따라 초기 표시 여부 결정
        if self._state == _ST_READY:
            self._lbl_loading.hide()
            tbl.show()
        else:
            tbl.hide()   # 아직 fetching 중 → 로딩 라벨만 표시

        logger.info(f"[FloatingWidget] table built: {row_count}r x {col_count}c, state={self._state}")

    def _apply_prices_from_cache(self):
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
            total_buy += float(stock.get("buy_price", 0)) * int(stock.get("quantity", 0))
            total_cur += data["current"] * int(stock.get("quantity", 0))
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

    # ── 행 데이터 채우기 ─────────────────────────────────────────────────────

    def _fill_row(self, i: int, stock: dict, data: dict, fc: str):
        """
        색상 규칙:
          종목명(name)  → 항상 fc
          종목코드(code) → 항상 FG_DIM
          현재가(price) → use_change_color 시 등락색, 아니면 fc
          변동(change)  → 등락색
          손익(profit)  → 등락색
          총평가(total) → 항상 fc
          합산행        → 항상 ACCENT (_fill_summary)
        """
        rd      = self.row_items[i]
        cur     = data["current"]
        chg     = data["change"]
        chg_pct = data["change_pct"]
        buy     = float(stock.get("buy_price", 0))
        qty     = int(stock.get("quantity", 0))
        pft_amt = (cur - buy) * qty
        pft_pct = (cur - buy) / buy * 100 if buy != 0 else 0.0
        total   = cur * qty

        arrow   = "▲" if chg > 0 else ("▼" if chg < 0 else "")
        c_col   = self._change_color(chg)
        p_col   = self._change_color(pft_amt)
        use_clr = self.cfg.get("use_change_color", True)

        if "name" in rd:
            rd["name"].setText(stock.get("name", ""))
            rd["name"].setForeground(QBrush(QColor(fc)))

        if "code" in rd:
            rd["code"].setText(stock.get("code", ""))
            rd["code"].setForeground(QBrush(QColor(FG_DIM)))

        price_col = c_col if use_clr else fc
        rd["price"].setText(f"{int(cur):,}" if cur == int(cur) else f"{cur:,.2f}")
        rd["price"].setForeground(QBrush(QColor(price_col)))

        if "change" in rd:
            show_amt = self.cfg.get("show_change_amt", False)
            show_pct = self.cfg.get("show_change_pct", False)
            if chg == 0:
                txt = "-"
            elif show_amt and show_pct:
                txt = f"{arrow}{abs(chg):,.0f}({chg_pct:+.2f}%)"
            elif show_amt:
                txt = f"{arrow}{abs(chg):,.0f}"
            else:
                txt = f"{arrow}{chg_pct:+.2f}%"
            rd["change"].setText(txt)
            rd["change"].setForeground(QBrush(QColor(c_col if use_clr else fc)))

        if "profit" in rd:
            show_amt = self.cfg.get("show_profit_amt", False)
            show_pct = self.cfg.get("show_profit_pct", False)
            p_arrow  = "▲" if pft_amt > 0 else ("▼" if pft_amt < 0 else "")
            abs_amt  = abs(pft_amt)
            abs_pct  = abs(pft_pct)
            if pft_amt == 0:
                txt = "-"
            elif show_amt and show_pct:
                a = f"{int(abs_amt):,}" if abs_amt == int(abs_amt) else f"{abs_amt:,.2f}"
                txt = f"{p_arrow}{a}({abs_pct:.2f}%)"
            elif show_amt:
                a = f"{int(abs_amt):,}" if abs_amt == int(abs_amt) else f"{abs_amt:,.2f}"
                txt = f"{p_arrow}{a}"
            else:
                txt = f"{p_arrow}{abs_pct:.2f}%"
            rd["profit"].setText(txt)
            rd["profit"].setForeground(QBrush(QColor(p_col if use_clr else fc)))

        if "total" in rd:
            rd["total"].setText(
                f"{int(total):,}" if total == int(total) else f"{total:,.2f}"
            )
            rd["total"].setForeground(QBrush(QColor(fc)))

    def _fill_summary(self, total_buy: float, total_cur: float, fc: str):
        """합산행 — 폰트 색상(fc) 고정, 증감 색상 미적용"""
        if self.summary_row < 0 or not self.sum_current_item or not self.sum_profit_item:
            return
        total_pft     = total_cur - total_buy
        total_pft_pct = (total_pft / total_buy * 100) if total_buy > 0 else 0.0
        sign          = "+" if total_pft >= 0 else ""
        self.sum_current_item.setText(f"총{int(total_cur):,}")
        self.sum_current_item.setForeground(QBrush(QColor(fc)))
        self.sum_profit_item.setText(f"{sign}{int(total_pft):,} ({total_pft_pct:+.2f}%)")
        self.sum_profit_item.setForeground(QBrush(QColor(fc)))

    def _resize_to_content(self):
        if self.card:
            self.card.adjustSize()
            self.resize(self.card.sizeHint())

    def _change_color(self, value: float) -> str:
        invert = self.cfg.get("invert_color", False)
        if value > 0:   return FALL_COLOR if invert else RISE_COLOR
        elif value < 0: return RISE_COLOR if invert else FALL_COLOR
        return "#707070"

    # ── 설정 / 종목 반영 ─────────────────────────────────────────────────────

    def apply_settings(self, cfg: dict):
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

        # 캐시가 있으면: 즉시 테이블 재빌드(캐시 데이터) → 백그라운드에서 조용히 갱신
        # 캐시가 없으면: 로딩 문구 표시 → fetch 완료 후 테이블 표시
        if self._price_cache:
            self._state = _ST_READY
            self._build_table()
            self._apply_prices_from_cache()
            self._lbl_loading.hide()
            if self.table:
                self.table.show()
            self._resize_to_content()
            self._start_fetch(show_loading=False)  # 로딩 문구 없이 백그라운드 갱신
        else:
            self._state = _ST_FETCHING
            self._lbl_loading.setText("● 데이터 불러오는 중")
            fm_h = self._lbl_loading.fontMetrics().height()
            self._lbl_loading.setFixedHeight(fm_h + 4)
            self._lbl_loading.show()
            self._destroy_table()
            self._resize_to_content()
            self._start_fetch(show_loading=True)   # 로딩 문구 유지하며 fetch

    def apply_stocks(self, stocks: list):
        logger.info(f"apply_stocks called: {len(stocks)} items")
        self.stocks       = [s for s in stocks if s.get("active", True)]
        self._price_cache = {}   # 종목 변경 → 캐시 초기화

        self._state = _ST_FETCHING
        self._lbl_loading.setText("● 데이터 불러오는 중")
        fm_h = self._lbl_loading.fontMetrics().height()
        self._lbl_loading.setFixedHeight(fm_h + 4)
        self._lbl_loading.show()
        self._destroy_table()
        self._resize_to_content()

        self._start_fetch(show_loading=True)

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
