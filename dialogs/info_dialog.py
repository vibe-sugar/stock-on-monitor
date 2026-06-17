from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QDesktopServices
from PyQt5.QtCore import QUrl
from core.constants import APP_NAME, APP_VERSION, APP_AUTHOR, APP_WEBSITE, APP_GITHUB

STYLE = """
QDialog { background: #1a1a2e; }
QLabel  { color: #cccccc; background: transparent; }
QPushButton {
    background: #3a3a5e; color: #cccccc;
    border: none; border-radius: 4px; padding: 5px 14px;
}
QPushButton:hover { background: #5a5aae; color: white; }
"""

class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("프로그램 정보")
        self.setFixedSize(320, 240)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(30, 24, 30, 20)

        title = QLabel(f"✦  {APP_NAME}")
        title.setFont(QFont("Malgun Gothic", 16, QFont.Bold))
        title.setStyleSheet("color: #9090ee;")
        title.setAlignment(Qt.AlignCenter)

        for text in [
            f"Version  {APP_VERSION}",
            APP_AUTHOR,
        ]:
            l = QLabel(text)
            l.setFont(QFont("Malgun Gothic", 9))
            l.setStyleSheet("color: #888;")
            l.setAlignment(Qt.AlignCenter)
            layout.addWidget(l) if layout.count() > 0 else None

        layout.addWidget(title)
        layout.addSpacing(4)

        for text in [f"Version  {APP_VERSION}", APP_AUTHOR]:
            l = QLabel(text)
            l.setFont(QFont("Malgun Gothic", 9))
            l.setStyleSheet("color: #888;")
            l.setAlignment(Qt.AlignCenter)
            layout.addWidget(l)

        layout.addSpacing(8)

        # 링크 버튼
        btn_row = QHBoxLayout()
        btn_web = QPushButton("🌐 웹사이트")
        btn_git = QPushButton("🐙 GitHub")
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(APP_WEBSITE)))
        btn_git.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(APP_GITHUB)))
        btn_row.addWidget(btn_web)
        btn_row.addWidget(btn_git)
        layout.addLayout(btn_row)

        layout.addStretch()
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignCenter)

        self.setLayout(layout)
