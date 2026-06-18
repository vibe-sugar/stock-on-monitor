"""사용법 다이얼로그 — 통일 디자인 시스템"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget,
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

from core.constants import APP_WEBSITE

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
}}
QPushButton#btn_close:hover {{
    color: {FG_PRIMARY};
    border-color: {FG_SECONDARY};
}}
"""

# 각 항목: (아이콘, 제목, 설명)
USAGE_ITEMS = [
    ("🖱",  "우클릭",      "메뉴 열기"),
    ("✥",   "클릭+드래그", "위치 이동"),
    ("📈",  "종목 수정",   "종목 추가 / 삭제 / 순서 변경"),
    ("⚙",   "환경설정",    "색상, 글자 크기, 표시 항목 변경"),
    ("⏱",   "갱신 주기",   "기본 10초  (최소 3초)"),
]


class UsageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("사용법")
        self.setFixedSize(360, 320)
        self.setStyleSheet(STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 헤더 ─────────────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(f"background: {BG_SURFACE};")
        h_lay = QVBoxLayout()
        h_lay.setContentsMargins(24, 16, 24, 14)
        h_lay.setSpacing(0)
        title = QLabel("사용법")
        title.setFont(QFont("Malgun Gothic", 13, QFont.Bold))
        title.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        h_lay.addWidget(title)
        header.setLayout(h_lay)
        layout.addWidget(header)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        layout.addWidget(div)

        # ── 본문 ─────────────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background: {BG_MAIN};")
        b_lay = QVBoxLayout()
        b_lay.setContentsMargins(20, 16, 20, 16)
        b_lay.setSpacing(6)

        for icon, action, desc in USAGE_ITEMS:
            row_w = QWidget()
            row_w.setStyleSheet(
                f"background: {BG_SURFACE};"
                f"border-radius: 6px;"
            )
            row = QHBoxLayout()
            row.setContentsMargins(12, 7, 12, 7)
            row.setSpacing(10)

            lbl_icon = QLabel(icon)
            lbl_icon.setFixedWidth(22)
            lbl_icon.setFont(QFont("Segoe UI Emoji", 11))
            lbl_icon.setStyleSheet(f"color: {ACCENT}; background: transparent;")
            lbl_icon.setAlignment(Qt.AlignCenter)

            lbl_action = QLabel(action)
            lbl_action.setFixedWidth(88)
            lbl_action.setFont(QFont("Malgun Gothic", 9, QFont.Bold))
            lbl_action.setStyleSheet(f"color: {FG_PRIMARY}; background: transparent;")

            lbl_desc = QLabel(desc)
            lbl_desc.setFont(QFont("Malgun Gothic", 9))
            lbl_desc.setStyleSheet(f"color: {FG_SECONDARY}; background: transparent;")

            row.addWidget(lbl_icon)
            row.addWidget(lbl_action)
            row.addWidget(lbl_desc)
            row.addStretch()
            row_w.setLayout(row)
            b_lay.addWidget(row_w)

        b_lay.addStretch()

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_web = QPushButton("🌐  웹사이트에서 더 보기")
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(APP_WEBSITE)))
        btn_close = QPushButton("닫기")
        btn_close.setObjectName("btn_close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_web)
        btn_row.addWidget(btn_close)
        b_lay.addLayout(btn_row)

        body.setLayout(b_lay)
        layout.addWidget(body)

        self.setLayout(layout)
