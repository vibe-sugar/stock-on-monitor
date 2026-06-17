from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

STYLE = """
QDialog  { background: #1a1a1a; }
QWidget  { background: #1a1a1a; }
QLabel   { color: #aaaaaa; background: transparent; }
QPushButton {
    background: #2a2a2a; color: #aaaaaa;
    border: 1px solid #333; border-radius: 4px; padding: 5px 14px;
}
QPushButton:hover { background: #3a3a3a; color: #cccccc; }
QScrollArea { border: none; background: #1a1a1a; }
"""

LICENSES = [
    {
        "name"   : "PyQt5",
        "version": "5.15.x",
        "license": "GPL v3 / Commercial",
        "url"    : "https://www.riverbankcomputing.com/software/pyqt/",
        "desc"   : "Qt 프레임워크 Python 바인딩. GUI 구성에 사용.",
    },
    {
        "name"   : "yfinance",
        "version": "0.2.x",
        "license": "Apache 2.0",
        "url"    : "https://github.com/ranaroussi/yfinance",
        "desc"   : "Yahoo Finance API 래퍼. 주식 실시간 가격 조회에 사용.",
    },
    {
        "name"   : "FinanceDataReader",
        "version": "0.9.x",
        "license": "Apache 2.0",
        "url"    : "https://github.com/FinanceData/FinanceDataReader",
        "desc"   : "한국 주식 종목 목록(KRX) 조회에 사용.",
    },
    {
        "name"   : "pandas",
        "version": "2.x",
        "license": "BSD 3-Clause",
        "url"    : "https://pandas.pydata.org/",
        "desc"   : "데이터 처리 라이브러리. 종목 목록 필터링에 사용.",
    },
    {
        "name"   : "pywin32",
        "version": "310",
        "license": "PSF License",
        "url"    : "https://github.com/mhammond/pywin32",
        "desc"   : "Windows 바로가기(.lnk) 생성에 사용.",
    },
    {
        "name"   : "PyInstaller",
        "version": "6.x",
        "license": "GPL v2 + exception",
        "url"    : "https://pyinstaller.org/",
        "desc"   : "Python 스크립트를 단일 exe로 패키징하는데 사용.",
    },
]


class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("오픈소스 라이선스")
        self.setFixedSize(500, 420)
        self.setStyleSheet(STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(8)

        title = QLabel("이 프로그램은 아래 오픈소스 라이브러리를 사용합니다.")
        title.setFont(QFont("Malgun Gothic", 9))
        title.setStyleSheet("color: #666666;")
        layout.addWidget(title)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        container.setStyleSheet("background: #1a1a1a;")
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 8, 0)
        vbox.setSpacing(6)

        for lib in LICENSES:
            card = QWidget()
            card.setStyleSheet("""
                QWidget {
                    background: #222222;
                    border: 1px solid #2a2a2a;
                    border-radius: 6px;
                }
            """)
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(12, 8, 12, 8)
            card_layout.setSpacing(3)

            # 이름 + 라이선스
            row = QHBoxLayout()
            lbl_name = QLabel(f"{lib['name']}  <span style='color:#555;font-size:8pt;'>v{lib['version']}</span>")
            lbl_name.setFont(QFont("Malgun Gothic", 10, QFont.Bold))
            lbl_name.setStyleSheet("color: #cccccc; background: transparent;")
            lbl_name.setTextFormat(Qt.RichText)

            lbl_lic = QLabel(lib["license"])
            lbl_lic.setFont(QFont("Malgun Gothic", 8))
            lbl_lic.setStyleSheet("color: #666666; background: transparent;")
            lbl_lic.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            row.addWidget(lbl_name)
            row.addStretch()
            row.addWidget(lbl_lic)
            card_layout.addLayout(row)

            # 설명
            lbl_desc = QLabel(lib["desc"])
            lbl_desc.setFont(QFont("Malgun Gothic", 8))
            lbl_desc.setStyleSheet("color: #888888; background: transparent;")
            lbl_desc.setWordWrap(True)
            card_layout.addWidget(lbl_desc)

            # URL 링크
            lbl_url = QLabel(f"<a href='{lib['url']}' style='color:#555555;'>{lib['url']}</a>")
            lbl_url.setFont(QFont("Malgun Gothic", 8))
            lbl_url.setStyleSheet("background: transparent;")
            lbl_url.setOpenExternalLinks(True)
            card_layout.addWidget(lbl_url)

            card.setLayout(card_layout)
            vbox.addWidget(card)

        vbox.addStretch()
        container.setLayout(vbox)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignCenter)

        self.setLayout(layout)
