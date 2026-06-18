"""
FloatingWidget  —  주식 정보 플로팅 위젯

버그 수정:
  - _PriceFetcher: quit()+wait(2000ms) 로 안전 종료, deleteLater 미사용
    → "Destroyed while thread is still running" 완전 해결
  - 로딩 UI: setFixedHeight 제거, 카드 여백 정상화, 텍스트 항상 표시
  - 데이터 불러오는 중: _fetching 중이면 캐시 유무 무관하게 문구 표시
드래그: table + viewport 양쪽에 eventFilter 설치
즉시갱신: 설정/종목 저장 후 캐시로 즉시 표시, 비동기 새로고침
컬럼 합산: change / profit 단일 컬럼 (▲500(5.00%) 형식)
증감 색상: 현재가·변동·손익·총평가에만 적용 (종목명·합산행 제외)
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMenu,
    QTableWidget, QTableWidgetItem, QSizePolicy,
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

        # 드래그
        self._drag_pos    = QPoint()
        self._is_dragging = False

        # 가격 캐시 (code → dict)
        self._price_cache: dict[str, dict] = {}

        # UI 내부 참조
        self.card             = None
        self.table            = None
        self.row_items        = []
        self.col_map          = {}
        self.summary_row      = -1
        self.sum_current_item = None
        self.sum_profit_item  = None

        # ── 비동기 fetcher ── deleteLater 절대 사용 금지
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

        # card_layout 여백은 항상 (10, 6, 10, 6) 으로 고정
        # _show_loading_ui 에서 절대 변경하지 않음
        self.card_layout = QVBoxLayout()
        self.card_layout.setContentsMargins(10, 6, 10, 6)
        self.card_layout.setSpacing(2)

        self._rebuild_table()

        self.card.setLayout(self.card_layout)
        outer.addWidget(self.card)
        self.setLayout(outer)

    def _apply_card_style(self):
        """배경 + 테두리 스타일"""
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

    # ── 로딩 UI ─────────────────────────────────────────────────────────────

    def _show_loading_ui(self, fs: int, text: str):
        """
        로딩/fetching 중 표시하는 가로형 라벨.
        ★ setFixedHeight 사용 안 함 — 텍스트 크기에 맞게 자동 조정
        ★ card_layout 여백 변경 안 함 — 항상 (10,6,10,6) 유지
        """
        lbl = QLabel(f"● {text}")
        lbl.setFont(QFont("Malgun Gothic", fs))
        lbl.setStyleSheet(
            f"color: {FG_DEFAULT}; background: transparent;"
            f" padding: 0px;"
        )
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # ● 은 ACCENT 색으로 강조하고 싶지만 QLabel 단색 제한상
        # 대신 색상 있는 dot 별도 라벨로 분리
        # → QLabel 하나로 통합하면 텍스트 클리핑 문제 없음

        # dot + text 를 HBox 로
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(5)

        dot = QLabel("●")
        dot.setFont(QFont("Malgun Gothic", fs))
        dot.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        dot.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        msg = QLabel(text)
        msg.setFont(QFont("Malgun Gothic", fs))
        msg.setStyleSheet(f"color: {FG_DEFAULT}; background: transparent;")
        msg.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        hbox.addWidget(dot)
        hbox.addWidget(msg)
        hbox.addStretch()
        container.setLayout(hbox)

        self.card_layout.addWidget(container)
        self._resize_to_content()

    # ── 테이블 재구성 ────────────────────────────────────────────────────────

    def _rebuild_table(self):
        """테이블 위젯 전체 재생성"""
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

        # ── 분기 1: 최초 로딩 중 (캐시 없음) ───────────────────────────────
        if self._loading and not self._price_cache:
            self._show_loading_ui(fs, "프로그램 준비중...")
            return

        # ── 분기 2: 설정/종목 저장 후 재조회 중 (캐시 없음) ────────────────
        # _fetching=True + 캐시 없음 → 데이터 불러오는 중 표시
        if self._fetching and not self._price_cache:
            self._show_loading_ui(fs, "데이터 불러오는 중")
            return

        # ── 분기 3: 종목 없음 ────────────────────────────────────────────────
        if not self.stocks:
            lbl = QLabel("우클릭하여 종목을 설정해주세요.")
            lbl.setFont(QFont("Malgun Gothic", fs))
            lbl.setStyleSheet(f"color:{ACCENT}; background:transparent; padding:4px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.card_layout.addWidget(lbl)
            self._resize_to_content()
            return

        # ── 분기 4: 정상 테이블 ─────────────────────────────────────────────
        self._build_table(fs)

    def _build_table(self, fs: int):
        """정상 테이블 빌드"""
        fc = self.cfg.get("font_color", FG_DEFAULT)

        # ── 열 구성 ─────────────────────────────────────────────────────────
        # change: show_change_amt 또는 show_change_pct 중 하나 이상이면 단일 컬럼
        # profit: show_profit_amt 또는 show_profit_pct 중 하나 이상이면 단일 컬럼
        col_map: dict[str, int] = {}
        idx = 0

        if self.cfg.get("show_name"):   col_map["name"]   = idx; idx += 1
        if self.cfg.get("show_code"):   col_map["code"]   = idx; idx += 1

        col_map["price"] = idx; idx += 1

        if self.cfg.get("show_change_amt") or self.cfg.get("show_change_pct"):
            col_map["change"] = idx; idx += 1

        if self.cfg.get("show_profit_amt") or self.cfg.get("show_profit_pct"):
            col_map["profit"] = idx; idx += 1

        if self.cfg.get("show_total"):  col_map["total"]  = idx; idx += 1

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

        # 캐시된 가격으로 즉시 채우기
        if self._price_cache:
            self._apply_prices_from_cache()

        self._resize_to_content()
        logger.debug(f"table built: {row_count}r x {col_count}c")

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

    # ── 캐시 즉시 반영 ───────────────────────────────────────────────────────

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

    # ── 가격 갱신 ────────────────────────────────────────────────────────────

    def update_prices(self):
        """비동기로 가격 조회 시작."""
        if not self.stocks:
            self._loading  = False
            self._fetching = False
            self._resize_to_content()
            return

        # ── 이전 fetcher 안전 종료 ──────────────────────────────────────────
        # ★ 핵심: quit() 후 wait(2000ms)로 완전 종료 확인 후 참조 해제
        # wait() 없이 None 처리 시 GC 가 QThread 파괴 → 크래시
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

        self._fetching = True

        fetcher = _PriceFetcher(self.stocks)
        fetcher.done.connect(self._on_prices_fetched)
        fetcher.finished.connect(self._on_fetcher_finished)
        self._fetcher = fetcher
        fetcher.start()

    def _on_fetcher_finished(self):
        """스레드 종료 시 포인터만 정리"""
        self._fetcher = None

    def _on_prices_fetched(self, results: list):
        """백그라운드 조회 완료 → UI 갱신"""
        was_loading  = self._loading
        was_fetching = self._fetching
        self._loading  = False
        self._fetching = False

        # 로딩 화면 → 실제 테이블로 교체가 필요한 경우
        if was_loading or (was_fetching and self.table is None):
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
        self._resize_to_content()

    # ── 행 데이터 채우기 ─────────────────────────────────────────────────────

    def _fill_row(self, i: int, stock: dict, data: dict, fc: str):
        """하나의 행에 데이터를 채움.

        색상 규칙:
          - 종목명(name): 항상 fc (증감 색상 미적용)
          - 종목코드(code): 항상 FG_DIM
          - 현재가(price): use_change_color 시 등락 색상, 아니면 fc
          - 변동(change): 항상 등락 색상 (use_change_color 무관)
          - 손익(profit):  항상 등락 색상 (use_change_color 무관)
          - 총평가(total): 항상 fc
          - 합산행(summary): 항상 ACCENT (별도 _fill_summary)
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

        arrow   = "▲" if chg > 0 else ("▼" if chg < 0 else "─")
        c_col   = self._change_color(chg)
        p_col   = self._change_color(pft_amt)
        use_clr = self.cfg.get("use_change_color", True)

        # ── 종목명: 항상 fc (증감 색상 미적용) ─────────────────────────────
        if "name" in rd:
            rd["name"].setText(stock.get("name", ""))
            rd["name"].setForeground(QBrush(QColor(fc)))

        # ── 종목코드: 항상 FG_DIM ───────────────────────────────────────────
        if "code" in rd:
            rd["code"].setText(stock.get("code", ""))
            rd["code"].setForeground(QBrush(QColor(FG_DIM)))

        # ── 현재가: use_change_color 시 등락색, 아니면 fc ──────────────────
        price_col = c_col if use_clr else fc
        rd["price"].setText(f"{int(cur):,}" if cur == int(cur) else f"{cur:,.2f}")
        rd["price"].setForeground(QBrush(QColor(price_col)))

        # ── 변동 컬럼: amt+pct 합산 ────────────────────────────────────────
        if "change" in rd:
            show_amt = self.cfg.get("show_change_amt", False)
            show_pct = self.cfg.get("show_change_pct", False)
            if show_amt and show_pct:
                txt = f"{arrow}{chg:+,.0f}({chg_pct:+.2f}%)"
            elif show_amt:
                txt = f"{arrow}{chg:+,.0f}"
            else:
                txt = f"{arrow}{chg_pct:+.2f}%"
            rd["change"].setText(txt)
            rd["change"].setForeground(QBrush(QColor(c_col)))

        # ── 손익 컬럼: amt+pct 합산 ────────────────────────────────────────
        if "profit" in rd:
            show_amt = self.cfg.get("show_profit_amt", False)
            show_pct = self.cfg.get("show_profit_pct", False)
            p_arrow  = "▲" if pft_amt > 0 else ("▼" if pft_amt < 0 else "─")
            abs_amt  = abs(pft_amt)
            abs_pct  = abs(pft_pct)
            if show_amt and show_pct:
                a = f"{int(abs_amt):,}" if abs_amt == int(abs_amt) else f"{abs_amt:,.2f}"
                txt = f"{p_arrow}{a}({abs_pct:.2f}%)"
            elif show_amt:
                a = f"{int(abs_amt):,}" if abs_amt == int(abs_amt) else f"{abs_amt:,.2f}"
                txt = f"{p_arrow}{a}"
            else:
                txt = f"{p_arrow}{abs_pct:.2f}%"
            rd["profit"].setText(txt)
            rd["profit"].setForeground(QBrush(QColor(p_col)))

        # ── 총평가: 항상 fc ────────────────────────────────────────────────
        if "total" in rd:
            rd["total"].setText(
                f"{int(total):,}" if total == int(total) else f"{total:,.2f}"
            )
            rd["total"].setForeground(QBrush(QColor(fc)))

    def _fill_summary(self, total_buy: float, total_cur: float, fc: str):
        """요약 행 갱신 — 항상 ACCENT 색상 (증감 색상 미적용)"""
        if self.summary_row < 0 or not self.sum_current_item or not self.sum_profit_item:
            return
        total_pft     = total_cur - total_buy
        total_pft_pct = (total_pft / total_buy * 100) if total_buy > 0 else 0.0
        sign          = "+" if total_pft >= 0 else ""

        self.sum_current_item.setText(f"총{int(total_cur):,}")
        self.sum_current_item.setForeground(QBrush(QColor(ACCENT)))
        self.sum_profit_item.setText(
            f"{sign}{int(total_pft):,} ({total_pft_pct:+.2f}%)"
        )
        # 합산 행은 ACCENT 고정 (증감 색상 미적용)
        self.sum_profit_item.setForeground(QBrush(QColor(ACCENT)))

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

        # 캐시가 없을 경우 _fetching=True 로 로딩 문구 표시
        # 캐시가 있을 경우 즉시 캐시로 테이블 그린 뒤 백그라운드 갱신
        self._fetching = not bool(self._price_cache)
        self._rebuild_table()
        self.update_prices()

    def apply_stocks(self, stocks: list):
        """종목 저장 후 즉시 반영"""
        logger.info(f"apply_stocks called: {len(stocks)} items")
        self.stocks = [s for s in stocks if s.get("active", True)]

        # 종목이 바뀌었으므로 캐시 초기화 (다른 종목 캐시가 잘못 표시되는 것 방지)
        self._price_cache = {}
        self._fetching = True   # 빈 캐시 → 로딩 문구 표시
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
