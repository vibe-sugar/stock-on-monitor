"""
AdPopup  —  프로그램 시작 시 1회 표시되는 광고 배너 팝업

레이아웃:
  ┌─────────────────────────────────┐  ← 카드 (302 × ~284 px)
  │  [QWebEngineView  300 × 250]    │  ← 광고 iframe 영역
  ├─────────────────────────────────┤
  │  ⓘ stock on monitor에서 표시…  [닫기]│
  └─────────────────────────────────┘

주의사항:
  - Qt.Tool 미사용: Windows에서 Tool 창은 taskbar에 안 잡히며
    일부 환경에서 show() 자체가 억제되는 현상이 있음
  - WA_TranslucentBackground 미사용: QWebEngineView 렌더링 깨짐
  - setWindowFlag 후 반드시 show() 재호출 필요 없음 (생성자에서 처리)
"""

from __future__ import annotations

from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QApplication, QFrame,
)
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QFont, QFontMetrics

# ── 광고 URL ──────────────────────────────────────────────────────────────────
AD_URL = "http://127.0.0.1:5000"

# ── 디자인 토큰 ───────────────────────────────────────────────────────────────
BG_CARD    = "#1A1B1C"
BG_FOOTER  = "#111213"
BORDER     = "#3A3B3C"
FG_PRIMARY = "#E0E0E0"
FG_DIM     = "#888888"
BTN_BG     = "#2A2B2C"
BTN_HOVER  = "#3A3B3C"
BTN_PRESS  = "#4A4B4C"
ACCENT     = "#5D87F6"

AD_W = 300
AD_H = 250


class AdPopup(QWidget):
    """광고 배너 팝업 — 프로그램 시작 시 1회 표시."""

    def __init__(self):
        # parent=None : 독립 최상위 창으로 생성
        super().__init__(None)

        # ── 윈도우 플래그 ──────────────────────────────────────────────────
        # • FramelessWindowHint  : OS 타이틀바 제거
        # • WindowStaysOnTopHint : 항상 최상위
        # • Tool / WA_TranslucentBackground 제거 :
        #     Tool → Windows에서 show 억제 사례 있음
        #     TranslucentBackground → QWebEngineView 렌더링 깨짐
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)  # 포커스 빼앗지 않음

        self._build_ui()
        # 레이아웃 확정 후 위치 계산
        QTimer.singleShot(0, self._place_bottom_right)

    # ── UI 빌드 ────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)   # border 1px 공간
        root.setSpacing(0)

        # 외곽 배경 + 테두리 (widget 자체에 적용)
        self.setStyleSheet(f"""
            QWidget {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
            }}
        """)

        # ── 웹뷰 ──────────────────────────────────────────────────────────
        self._web = QWebEngineView(self)
        self._web.setFixedSize(AD_W, AD_H)
        s = self._web.settings()
        s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        s.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, False)
        self._web.load(QUrl(AD_URL))
        self._web.setStyleSheet("border: none;")
        root.addWidget(self._web)

        # ── 구분선 ────────────────────────────────────────────────────────
        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Plain)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {BORDER}; border: none; margin: 0;")
        root.addWidget(sep)

        # ── 하단 정보바 ───────────────────────────────────────────────────
        footer = QWidget(self)
        footer.setStyleSheet(f"background: {BG_FOOTER}; border: none;")

        foot_layout = QHBoxLayout(footer)
        foot_layout.setContentsMargins(8, 3, 6, 3)
        foot_layout.setSpacing(4)

        font_small = QFont()
        font_small.setPointSize(8)

        lbl_icon = QLabel("ⓘ", footer)
        lbl_icon.setStyleSheet(
            f"color: {FG_DIM}; background: transparent; font-size: 9pt; border: none;"
        )
        lbl_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        lbl_text = QLabel("stock on monitor에서 표시하는 광고", footer)
        lbl_text.setFont(font_small)
        lbl_text.setStyleSheet(f"color: {FG_DIM}; background: transparent; border: none;")
        lbl_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        btn_close = QPushButton("닫기", footer)
        btn_close.setFont(font_small)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFocusPolicy(Qt.NoFocus)
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

        fm_h = QFontMetrics(font_small).height()
        footer_h = fm_h + 14   # 상하 여유
        footer.setFixedHeight(footer_h)

        root.addWidget(footer)

        # 전체 크기 고정: 웹뷰 + 구분선(1) + 푸터 + 테두리(2)
        total_h = AD_H + 1 + footer_h + 2
        self.setFixedSize(AD_W + 2, total_h)

    # ── 우측 하단 배치 ─────────────────────────────────────────────────────

    def _place_bottom_right(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.move(200, 200)
            return
        geo = screen.availableGeometry()
        margin = 16
        x = geo.right()  - self.width()  - margin
        y = geo.bottom() - self.height() - margin
        self.move(x, y)
        self.raise_()   # 확실히 앞으로

    def showEvent(self, event):
        super().showEvent(event)
        self._place_bottom_right()
