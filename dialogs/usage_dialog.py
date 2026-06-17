"""사용법 다이얼로그 — 블루 포인트 테마"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

from core.constants import APP_WEBSITE

BLUE_ACCENT = "#29b6f6"
BLUE_BORDER = "#1e3a4a"
BG_MAIN     = "#0f1a22"
BG_INPUT    = "#162030"
FG_MAIN     = "#b0b0b0"
FG_DIM      = "#888888"

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

USAGE_TEXT = """
  ▸  우클릭  → 메뉴 열기
  ▸  클릭+드래그  → 위치 이동
  ▸  종목 수정  → 종목 추가 / 삭제 / 순서 변경
  ▸  환경설정  → 색상, 글자 크기, 표시 항목 변경
  ▸  갱신 주기  → 기본 10초 (최소 3초)
""".strip()


class UsageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("사용법")
        self.setFixedSize(320, 240)
        self.setStyleSheet(STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("사용법")
        title.setFont(QFont("Malgun Gothic", 12, QFont.Bold))
        title.setStyleSheet(f"color: {BLUE_ACCENT};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        lbl = QLabel(USAGE_TEXT)
        lbl.setFont(QFont("Malgun Gothic", 9))
        lbl.setStyleSheet(f"color: {FG_DIM}; line-height: 180%;")
        lbl.setAlignment(Qt.AlignLeft)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        layout.addStretch()

        btn_web = QPushButton("🌐 웹사이트에서 더 보기")
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(APP_WEBSITE)))
        layout.addWidget(btn_web)

        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.setLayout(layout)
