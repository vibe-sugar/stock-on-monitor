"""
AdPopup  —  프로그램 시작 시 1회 표시되는 광고 배너 팝업

레이아웃:
  ┌─────────────────────────────────┐  ← 카드 (300 × ~284 px)
  │  [QWebEngineView  300 × 250]    │  ← 광고 iframe 영역
  ├─────────────────────────────────┤
  │  ⓘ stock on monitor에서 표시…  [닫기]│
  └─────────────────────────────────┘

설계:
  - FramelessWindowHint | WindowStaysOnTopHint  (Tool 제외 — 일부 OS에서 show 억제)
  - WA_TranslucentBackground 미사용 (QWebEngineView 와 충돌)
  - 화면 우측 하단 고정 배치 (마진 16px)
  - 닫기 버튼 클릭 → self.close()
  - 광고 URL 은 AD_URL 상수에서 교체
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QApplication, QFrame,
)
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
except ImportError as _web_err:
    import sys, subprocess
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "PyQtWebEngine"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings  # type: ignore
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QFont, QFontMetrics

# ── 광고 URL ──────────────────────────────────────────────────────────────────
AD_URL = "https://www.naver.com"

# ── 디자인 토큰 (floating.py 와 동일 팔레트) ─────────────────────────────────
BG_CARD     = "#1A1B1C"
BG_FOOTER   = "#111213"
BORDER      = "#3A3B3C"
FG_PRIMARY  = "#E0E0E0"
FG_DIM      = "#888888"
BTN_BG      = "#2A2B2C"
BTN_HOVER   = "#3A3B3C"
BTN_PRESS   = "#4A4B4C"
ACCENT      = "#5D87F6"

# 배너 고정 크기 (IAB Medium Rectangle)
AD_W = 300
AD_H = 250


class AdPopup(QWidget):
    """광고 배너 팝업 — 프로그램 시작 시 1회 표시."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        # ── 윈도우 플래그 ──────────────────────────────────────────────────
        # Tool 플래그 제거: 일부 환경에서 Tool 창이 show() 되지 않는 문제 방지
        # WA_TranslucentBackground 미사용: QWebEngineView 와 충돌하여 렌더링 깨짐
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_DeleteOnClose)

        # 카드 전체를 스타일로 그리므로 배경은 단색으로 고정
        self.setStyleSheet(f"QWidget#adRoot {{ background: {BG_CARD}; }}")
        self.setObjectName("adRoot")

        self._build_ui()

        # showEvent 이후 위치 확정
        QTimer.singleShot(0, self._place_bottom_right)

    # ── UI 빌드 ────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 외곽 카드 컨테이너 ──
        self.card = QWidget(self)
        self.card.setObjectName("adCard")
        self.card.setStyleSheet(f"""
            QWidget#adCard {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
            }}
        """)
        self.card.setFixedWidth(AD_W)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ── 웹뷰 ──────────────────────────────────────────────────────────
        self._web = QWebEngineView(self.card)
        self._web.setFixedSize(AD_W, AD_H)
        s = self._web.settings()
        s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        s.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, False)
        self._web.load(QUrl(AD_URL))
        card_layout.addWidget(self._web)

        # ── 구분선 ────────────────────────────────────────────────────────
        sep = QFrame(self.card)
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Plain)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {BORDER}; border: none;")
        card_layout.addWidget(sep)

        # ── 하단 정보바 ───────────────────────────────────────────────────
        footer = QWidget(self.card)
        footer.setObjectName("adFooter")
        footer.setStyleSheet(f"QWidget#adFooter {{ background: {BG_FOOTER}; }}")

        foot_layout = QHBoxLayout(footer)
        foot_layout.setContentsMargins(8, 4, 6, 4)
        foot_layout.setSpacing(4)

        # ⓘ 아이콘
        lbl_icon = QLabel("ⓘ", footer)
        lbl_icon.setStyleSheet(
            f"color: {FG_DIM}; background: transparent; font-size: 9pt;"
        )
        lbl_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # 광고 안내 문구
        font_small = QFont()
        font_small.setPointSize(8)
        lbl_text = QLabel("stock on monitor에서 표시하는 광고", footer)
        lbl_text.setFont(font_small)
        lbl_text.setStyleSheet(f"color: {FG_DIM}; background: transparent;")
        lbl_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # 닫기 버튼
        btn_close = QPushButton("닫기", footer)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFocusPolicy(Qt.NoFocus)
        btn_close.setFont(font_small)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                color: {FG_DIM};
                background: {BTN_BG};
                border: 1px solid {BORDER};
                border-radius: 3px;
                padding: 2px 8px;
            }}
            QPushButton:hover {{
                background: {BTN_HOVER};
                color: {FG_PRIMARY};
                border-color: {ACCENT};
            }}
            QPushButton:pressed {{
                background: {BTN_PRESS};
            }}
        """)
        btn_close.clicked.connect(self.close)

        foot_layout.addWidget(lbl_icon)
        foot_layout.addWidget(lbl_text)
        foot_layout.addWidget(btn_close)

        # 푸터 높이: 폰트 높이 + 상하 패딩 8px
        fm_h = QFontMetrics(font_small).height()
        footer.setFixedHeight(fm_h + 16)

        card_layout.addWidget(footer)

        root.addWidget(self.card)

        # 위젯 전체 크기 고정
        total_h = AD_H + 1 + (fm_h + 16)  # 웹뷰 + 구분선 + 푸터
        self.setFixedSize(AD_W, total_h)

    # ── 화면 우측 하단 배치 ────────────────────────────────────────────────

    def _place_bottom_right(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.move(100, 100)
            return
        geo = screen.availableGeometry()
        margin = 16
        x = geo.right()  - self.width()  - margin
        y = geo.bottom() - self.height() - margin
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        self._place_bottom_right()
