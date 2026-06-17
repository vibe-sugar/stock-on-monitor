"""오픈소스 라이선스 다이얼로그 — 블루 포인트 테마"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QDesktopServices
from PyQt5.QtCore import QUrl

BLUE_ACCENT = "#2841E8"
BLUE_BORDER = "#1e3a4a"
BG_MAIN     = "#0f1a22"
BG_CARD     = "#111e28"
BG_INPUT    = "#162030"
FG_MAIN     = "#b0b0b0"
FG_DIM      = "#666666"
FG_TITLE    = "#cccccc"

STYLE = f"""
QDialog  {{ background: {BG_MAIN}; }}
QLabel   {{ color: {FG_MAIN}; background: transparent; }}
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
QScrollArea {{ border: none; background: {BG_MAIN}; }}
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
        title.setStyleSheet(f"color: {FG_DIM};")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; }}")

        container = QWidget()
        container.setObjectName("scroll_container")
        container.setStyleSheet(f"QWidget#scroll_container {{ background: {BG_MAIN}; }}")
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 6, 0)
        vbox.setSpacing(6)

        for i, lib in enumerate(LICENSES):
            card = QWidget()
            card.setObjectName(f"card_{i}")
            card.setStyleSheet(f"""
                QWidget#card_{i} {{
                    background: {BG_CARD};
                    border: none;
                    border-radius: 6px;
                }}
            """)
            cl = QVBoxLayout()
            cl.setContentsMargins(12, 8, 12, 8)
            cl.setSpacing(3)

            # 이름 + 버전 + 라이선스
            row = QHBoxLayout()
            lbl_name = QLabel(
                f"<span style='color:{FG_TITLE};font-weight:bold;'>{lib['name']}</span>"
                f"  <span style='color:{FG_DIM};font-size:8pt;'>v{lib['version']}</span>"
            )
            lbl_name.setFont(QFont("Malgun Gothic", 10))
            lbl_name.setTextFormat(Qt.RichText)
            lbl_name.setStyleSheet("background: transparent;")

            lbl_lic = QLabel(lib["license"])
            lbl_lic.setFont(QFont("Malgun Gothic", 8))
            lbl_lic.setStyleSheet(f"color: {FG_DIM}; background: transparent;")
            lbl_lic.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            row.addWidget(lbl_name)
            row.addStretch()
            row.addWidget(lbl_lic)
            cl.addLayout(row)

            lbl_desc = QLabel(lib["desc"])
            lbl_desc.setFont(QFont("Malgun Gothic", 8))
            lbl_desc.setStyleSheet(f"color: {FG_MAIN}; background: transparent;")
            lbl_desc.setWordWrap(True)
            cl.addWidget(lbl_desc)

            lbl_url = QLabel(
                f"<a href='{lib['url']}' style='color:{BLUE_ACCENT};'>{lib['url']}</a>"
            )
            lbl_url.setFont(QFont("Malgun Gothic", 8))
            lbl_url.setStyleSheet("background: transparent;")
            lbl_url.setOpenExternalLinks(True)
            cl.addWidget(lbl_url)

            card.setLayout(cl)
            vbox.addWidget(card)

        vbox.addStretch()
        container.setLayout(vbox)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignCenter)

        self.setLayout(layout)
