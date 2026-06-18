"""오픈소스 라이선스 다이얼로그 — 통일 디자인 시스템"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QDesktopServices
from PyQt5.QtCore import QUrl

# ── 디자인 토큰 ────────────────────────────────────────────────────────────────
ACCENT       = "#5D87F6"
ACCENT_DARK  = "#111726"
BTN_BG       = "#132859"
BTN_FG       = "#577CF7"
BG_MAIN      = "#1A1F2E"
BG_SURFACE   = "#222840"
BG_CARD      = "#1E2438"
BORDER       = "#2D3A5C"
FG_PRIMARY   = "#D8DEF0"
FG_SECONDARY = "#7A8AB0"
FG_MUTED     = "#4A5578"

STYLE = f"""
QDialog {{ background: {BG_MAIN}; }}
QLabel  {{ color: {FG_PRIMARY}; background: transparent; }}
QPushButton {{
    background: {BTN_BG};
    color: {BTN_FG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 20px;
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
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {BG_MAIN};
    width: 5px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; }}
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

# 라이선스 유형별 배지 색상
_LICENSE_BADGE = {
    "GPL"       : ("#2A1525", "#F06292"),
    "Apache"    : ("#122030", "#5D87F6"),
    "BSD"       : ("#122820", "#34D399"),
    "PSF"       : ("#1A2030", "#7A8AB0"),
    "Commercial": ("#201520", "#A78BFA"),
}

def _badge_colors(license_str: str):
    for key, colors in _LICENSE_BADGE.items():
        if key in license_str:
            return colors
    return ("#1A2030", "#7A8AB0")


class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("오픈소스 라이선스")
        self.setFixedSize(520, 460)
        self.setStyleSheet(STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(10)

        # 헤더
        hdr = QLabel("이 프로그램은 아래 오픈소스 라이브러리를 사용합니다.")
        hdr.setFont(QFont("Malgun Gothic", 9))
        hdr.setStyleSheet(f"color: {FG_SECONDARY}; background: transparent;")
        layout.addWidget(hdr)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setObjectName("lic_container")
        container.setStyleSheet(f"QWidget#lic_container {{ background: {BG_MAIN}; }}")
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 8, 0)
        vbox.setSpacing(8)

        for i, lib in enumerate(LICENSES):
            card = QWidget()
            card.setObjectName(f"lic_card_{i}")
            card.setStyleSheet(f"""
                QWidget#lic_card_{i} {{
                    background: {BG_CARD};
                    border: none;
                    border-left: 3px solid {ACCENT};
                    border-radius: 6px;
                }}
            """)
            cl = QVBoxLayout()
            cl.setContentsMargins(14, 10, 14, 10)
            cl.setSpacing(4)

            # 이름 행
            row_top = QHBoxLayout()
            row_top.setSpacing(8)

            lbl_name = QLabel(lib["name"])
            lbl_name.setFont(QFont("Malgun Gothic", 10, QFont.Bold))
            lbl_name.setStyleSheet(f"color: {FG_PRIMARY}; background: transparent;")

            lbl_ver = QLabel(f"v{lib['version']}")
            lbl_ver.setFont(QFont("Malgun Gothic", 8))
            lbl_ver.setStyleSheet(f"color: {FG_MUTED}; background: transparent;")

            # 라이선스 배지
            bg_c, fg_c = _badge_colors(lib["license"])
            lbl_lic = QLabel(lib["license"])
            lbl_lic.setFont(QFont("Malgun Gothic", 8))
            lbl_lic.setStyleSheet(
                f"color: {fg_c};"
                f"background: {bg_c};"
                f"border-radius: 4px;"
                f"padding: 1px 8px;"
            )
            lbl_lic.setAlignment(Qt.AlignVCenter)

            row_top.addWidget(lbl_name)
            row_top.addWidget(lbl_ver)
            row_top.addStretch()
            row_top.addWidget(lbl_lic)
            cl.addLayout(row_top)

            # 설명
            lbl_desc = QLabel(lib["desc"])
            lbl_desc.setFont(QFont("Malgun Gothic", 8))
            lbl_desc.setStyleSheet(f"color: {FG_SECONDARY}; background: transparent;")
            lbl_desc.setWordWrap(True)
            cl.addWidget(lbl_desc)

            # URL
            lbl_url = QLabel(
                f"<a href='{lib['url']}' style='color:{ACCENT}; text-decoration:none;'>"
                f"↗ {lib['url']}</a>"
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

        # 닫기 버튼
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignCenter)

        self.setLayout(layout)
