"""프로그램 정보 다이얼로그 — 통일 디자인 시스템"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

from core.constants import APP_NAME, APP_VERSION, APP_AUTHOR, APP_WEBSITE, APP_GITHUB

# ── 디자인 토큰 ────────────────────────────────────────────────────────────────
ACCENT       = "#5D87F6"
ACCENT_DARK  = "#111726"
BTN_BG       = "#132859"
BTN_FG       = "#577CF7"
BG_MAIN      = "#1A1F2E"
BG_SURFACE   = "#222840"
BORDER       = "#2D3A5C"
FG_PRIMARY   = "#D8DEF0"
FG_SECONDARY = "#7A8AB0"
FG_MUTED     = "#4A5578"

STYLE = f"""
QDialog {{
    background: {BG_MAIN};
}}
QLabel {{
    color: {FG_PRIMARY};
    background: transparent;
}}
QFrame#divider {{
    background: {BORDER};
}}
QPushButton {{
    background: {BTN_BG};
    color: {BTN_FG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 9pt;
}}
QPushButton:hover {{
    background: #1C3A7A;
    color: {ACCENT};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background: {ACCENT_DARK};
}}
QPushButton#btn_close {{
    background: {BG_SURFACE};
    color: {FG_SECONDARY};
    border: 1px solid {BORDER};
    padding: 5px 30px;
}}
QPushButton#btn_close:hover {{
    color: {FG_PRIMARY};
    border-color: {FG_SECONDARY};
}}
"""


class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("프로그램 정보")
        self.setFixedSize(340, 240)
        self.setStyleSheet(STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── 상단 헤더 영역 ────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(f"background: {BG_SURFACE}; border-radius: 0px;")
        h_layout = QVBoxLayout()
        h_layout.setContentsMargins(30, 22, 30, 18)
        h_layout.setSpacing(6)

        title = QLabel(APP_NAME)
        title.setFont(QFont("Malgun Gothic", 16, QFont.Bold))
        title.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        h_layout.addWidget(title)

        ver_lbl = QLabel(f"Version  {APP_VERSION}")
        ver_lbl.setFont(QFont("Malgun Gothic", 9))
        ver_lbl.setStyleSheet(f"color: {FG_MUTED}; background: transparent;")
        ver_lbl.setAlignment(Qt.AlignCenter)
        h_layout.addWidget(ver_lbl)

        header.setLayout(h_layout)
        layout.addWidget(header)

        # ── 구분선 ────────────────────────────────────────────────────────────
        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        layout.addWidget(div)

        # ── 하단 콘텐츠 ───────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background: {BG_MAIN};")
        b_layout = QVBoxLayout()
        b_layout.setContentsMargins(24, 16, 24, 16)
        b_layout.setSpacing(10)

        author_lbl = QLabel(APP_AUTHOR)
        author_lbl.setFont(QFont("Malgun Gothic", 9))
        author_lbl.setStyleSheet(f"color: {FG_SECONDARY}; background: transparent;")
        author_lbl.setAlignment(Qt.AlignCenter)
        b_layout.addWidget(author_lbl)

        # 링크 버튼 행
        row = QHBoxLayout()
        row.setSpacing(8)
        btn_web = QPushButton("🌐  웹사이트")
        btn_git = QPushButton("🐙  GitHub")
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(APP_WEBSITE)))
        btn_git.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(APP_GITHUB)))
        row.addWidget(btn_web)
        row.addWidget(btn_git)
        b_layout.addLayout(row)

        b_layout.addStretch()

        btn_close = QPushButton("닫기")
        btn_close.setObjectName("btn_close")
        btn_close.clicked.connect(self.accept)
        b_layout.addWidget(btn_close, alignment=Qt.AlignCenter)

        body.setLayout(b_layout)
        layout.addWidget(body)

        self.setLayout(layout)
