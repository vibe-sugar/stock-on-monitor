from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QDesktopServices
from PyQt5.QtCore import QUrl
from core.constants import APP_WEBSITE

STYLE = """
QDialog { background: #1a1a2e; }
QLabel  { color: #cccccc; background: transparent; }
QPushButton {
    background: #3a3a5e; color: #cccccc;
    border: none; border-radius: 4px; padding: 5px 14px;
}
QPushButton:hover { background: #5a5aae; color: white; }
"""

class UsageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("사용법")
        self.setFixedSize(300, 200)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 24, 30, 20)
        layout.setSpacing(10)

        lbl = QLabel("자세한 사용법은 웹사이트를 참고해주세요.")
        lbl.setFont(QFont("Malgun Gothic", 9))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)

        btn_web = QPushButton("🌐 사용법 페이지 열기")
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(APP_WEBSITE)))

        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.close)

        layout.addStretch()
        layout.addWidget(lbl)
        layout.addSpacing(10)
        layout.addWidget(btn_web)
        layout.addSpacing(6)
        layout.addWidget(btn_close)
        layout.addStretch()
        self.setLayout(layout)
