"""
AdPopup  —  프로그램 시작 시 1회 표시되는 광고 배너 팝업

레이아웃:
  ┌─────────────────────────────────┐  ← 카드 (300 × ~276 px)
  │  [QWebEngineView  300 × 250]    │  ← 광고 iframe 영역
  ├─────────────────────────────────┤
  │  ⓘ stock on monitor에서 표시…  [✕]│  ← 정보 + 닫기 행
  └─────────────────────────────────┘

설계:
  - FramelessWindowHint | Tool | WindowStaysOnTopHint
  - WA_TranslucentBackground + 8px 라운드 카드
  - 화면 우측 하단 고정 배치 (마진 16px)
  - 닫기 버튼 클릭 → self.close() 로 완전 종료
  - 광고 URL 은 AD_URL 상수에서 교체
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QApplication,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import Qt, QUrl, QSize
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QFont, QFontMetrics

# ── 광고 URL ──────────────────────────────────────────────────────────────────
AD_URL = "https://www.google.com"   # ← 실제 광고 배너 URL 로 교체

# ── 디자인 토큰 (floating.py 와 동일 팔레트) ─────────────────────────────────
ACCENT      = "#5D87F6"
BG_CARD     = "#1A1B1C"
BG_FOOTER   = "#111213"      # 하단 정보바 배경 (조금 더 어둠)
BORDER      = "#2A2B2C"
FG_PRIMARY  = "#E0E0E0"
FG_DIM      = "#808080"
CLOSE_HOVER = "#3A3B3C"
CLOSE_PRESS = "#4A4B4C"

# 배너 고정 크기
AD_W = 300
AD_H = 250

# 하단 정보바 높이 — 폰트 기준으로 계산 (런타임에 갱신)
FOOTER_H = 28   # fallback 기본값


class AdPopup(QWidget):
    """광고 배너 팝업 — 프로그램 시작 시 1회 표시."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        # 창 플래그: 프레임 없음, 상시 최상위, 투명 배경
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._build_ui()
        self._place_bottom_right()

    # ── UI 빌드 ────────────────────────────────────────────────────────────

    def _build_ui(self):
        """카드 컨테이너 + 웹뷰 + 하단 정보바를 조립."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 카드 ──
        self.card = QWidget(self)
        self.card.setObjectName("adCard")
        self.card.setStyleSheet(f"""
            QWidget#adCard {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)
        self.card.setFixedWidth(AD_W)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ── 웹뷰 (광고 iframe 역할) ──
        self._web = QWebEngineView(self.card)
        self._web.setFixedSize(AD_W, AD_H)
        # 스크롤바 숨김, JS 허용
        settings = self._web.settings()
        settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, False)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        self._web.load(QUrl(AD_URL))
        self._web.setStyleSheet("border-radius: 8px 8px 0 0;")
        card_layout.addWidget(self._web)

        # ── 구분선 ──
        sep = QWidget(self.card)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {BORDER};")
        card_layout.addWidget(sep)

        # ── 하단 정보바 ──
        footer = QWidget(self.card)
        footer.setObjectName("adFooter")
        footer.setStyleSheet(f"""
            QWidget#adFooter {{
                background: {BG_FOOTER};
                border-radius: 0 0 8px 8px;
            }}
        """)

        foot_layout = QHBoxLayout(footer)
        foot_layout.setContentsMargins(8, 0, 4, 0)
        foot_layout.setSpacing(4)

        # ⓘ 아이콘 + 문구
        lbl_icon = QLabel("ⓘ", footer)
        lbl_icon.setStyleSheet(
            f"color: {FG_DIM}; background: transparent; font-size: 10pt;"
        )
        lbl_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        lbl_text = QLabel("stock on monitor에서 표시하는 광고", footer)
        font = QFont()
        font.setPointSize(8)
        lbl_text.setFont(font)
        lbl_text.setStyleSheet(
            f"color: {FG_DIM}; background: transparent;"
        )
        lbl_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # ✕ 닫기 버튼
        btn_close = QPushButton("✕", footer)
        btn_close.setFixedSize(22, 22)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFocusPolicy(Qt.NoFocus)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                color: {FG_DIM};
                background: transparent;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: {CLOSE_HOVER};
                color: {FG_PRIMARY};
            }}
            QPushButton:pressed {{
                background: {CLOSE_PRESS};
            }}
        """)
        btn_close.clicked.connect(self.close)

        foot_layout.addWidget(lbl_icon)
        foot_layout.addWidget(lbl_text)
        foot_layout.addWidget(btn_close)

        # 하단 바 높이: 폰트 높이 + 상하 패딩
        fm_h = QFontMetrics(lbl_text.font()).height()
        footer_h = fm_h + 12   # 상하 6px 여유
        footer.setFixedHeight(footer_h)

        card_layout.addWidget(footer)

        root.addWidget(self.card)

    # ── 화면 배치 ──────────────────────────────────────────────────────────

    def _place_bottom_right(self):
        """화면 우측 하단에 16px 마진으로 배치."""
        screen = QApplication.primaryScreen()
        if screen is None:
            self.move(100, 100)
            return

        geo = screen.availableGeometry()   # 작업표시줄 제외 영역
        w = self.sizeHint().width()
        h = self.sizeHint().height()

        # card 실제 크기로 계산 (sizeHint 가 0 일 수 있으므로 보정)
        if w <= 0:
            w = AD_W + 2        # border 포함
        if h <= 0:
            h = AD_H + 30 + 2  # 웹뷰 + 푸터 + border

        margin = 16
        x = geo.right()  - w - margin
        y = geo.bottom() - h - margin
        self.move(x, y)

    # ── 페인트: 카드 그림자 효과 (선택) ──────────────────────────────────────
    # 간단하게 card 자체 border 로 처리하므로 paintEvent 오버라이드 불필요.
    # 단, WA_TranslucentBackground 가 활성이므로 기본 배경은 투명.

    def showEvent(self, event):
        """show() 직후 위치를 재조정 (크기 확정 후)."""
        super().showEvent(event)
        self._place_bottom_right()
