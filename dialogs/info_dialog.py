"""프로그램 정보 다이얼로그 — 블루 포인트 테마"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

from core.constants import APP_NAME, APP_VERSION, APP_AUTHOR, APP_WEBSITE, APP_GITHUB

BLUE_ACCENT = "#29b6f6"
BLUE_BORDER = "#1e3a4a"
BG_MAIN     = "#0f1a22"
BG_INPUT    = "#162030"
FG_MAIN     = "#b0b0b0"
FG_DIM      = "#666666"

STYLE = f"""
QDialog {{
    background: {BG_MAIN};
}}
QLabel {{
    color: {FG_MAIN};
    background: transparent;
}}
QPushButton {{
    background: {BG_INPUT};
    color: {FG_MAIN};
    border: 1px solid {BLUE_BORDER};
    border-radius: 4px;
    padding: 5px 14px;
}}
QPushButton:hover {{
    background: #1a3a4a;
    color: {BLUE_ACCENT};
    border-color: {BLUE_ACCENT};
}}
"""


class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("프로그램 정보")
        self.setFixedSize(320, 220)
        self.setStyleSheet(STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(30, 24, 30, 20)

        # 앱 이름 (파란 포인트)
        title = QLabel(f"◆  {APP_NAME}")
        title.setFont(QFont("Malgun Gothic", 15, QFont.Bold))
        title.setStyleSheet(f"color: {BLUE_ACCENT};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(4)

        for text in [f"Version  {APP_VERSION}", APP_AUTHOR]:
            lbl = QLabel(text)
            lbl.setFont(QFont("Malgun Gothic", 9))
            lbl.setStyleSheet(f"color: {FG_DIM};")
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl)

        layout.addSpacing(10)

        # 링크 버튼
        row = QHBoxLayout()
        btn_web = QPushButton("🌐 웹사이트")
        btn_git = QPushButton("🐙 GitHub")
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(APP_WEBSITE)))
        btn_git.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(APP_GITHUB)))
        row.addWidget(btn_web)
        row.addWidget(btn_git)
        layout.addLayout(row)

        layout.addStretch()

        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignCenter)

        self.setLayout(layout)
