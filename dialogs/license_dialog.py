"""오픈소스 라이선스 다이얼로그"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame,
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

# ── 디자인 토큰 ────────────────────────────────────────────────────────────────
ACCENT       = "#5D87F6"
BG_MAIN      = "#1A1B1C"
BG_SURFACE   = "#242526"
BG_CARD      = "#202122"
BORDER       = "#3A3B3C"
BTN_BG       = "#1E2A4A"
BTN_FG       = "#7DA4F8"
FG_PRIMARY   = "#E0E0E0"
FG_SECONDARY = "#909090"
FG_MUTED     = "#555555"

STYLE = f"""
QDialog  {{ background: {BG_MAIN}; }}
QLabel   {{ color: {FG_PRIMARY}; background: transparent; }}
QFrame#divider {{ background: {BORDER}; border: none; }}
QPushButton {{
    background: {BTN_BG};
    color: {BTN_FG};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 6px 20px;
    font-size: 9pt;
}}
QPushButton:hover {{
    background: #263A6A;
    color: {ACCENT};
    border-color: {ACCENT};
}}
QPushButton:pressed {{ background: #141E38; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {BG_MAIN};
    width: 5px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 2px;
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

_BADGE = {
    "GPL"       : ("#2A1520", "#F06292"),
    "Apache"    : ("#1A2038", "#5D87F6"),
    "BSD"       : ("#182420", "#34D399"),
    "PSF"       : ("#222324", "#909090"),
    "Commercial": ("#1E1A28", "#A78BFA"),
}

def _badge(lic: str):
    for k, v in _BADGE.items():
        if k in lic:
            return v
    return ("#222324", "#909090")


class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("오픈소스 라이선스")
        self.setFixedSize(520, 460)
        self.setStyleSheet(STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 헤더
        header = QWidget()
        header.setStyleSheet(f"background: {BG_SURFACE};")
        h_lay = QVBoxLayout()
        h_lay.setContentsMargins(18, 12, 18, 10)
        h_lay.setSpacing(0)
        hdr_lbl = QLabel("이 프로그램은 아래 오픈소스 라이브러리를 사용합니다.")
        hdr_lbl.setFont(QFont("Malgun Gothic", 9))
        hdr_lbl.setStyleSheet(f"color: {FG_SECONDARY}; background: transparent;")
        h_lay.addWidget(hdr_lbl)
        header.setLayout(h_lay)
        layout.addWidget(header)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        layout.addWidget(div)

        # 스크롤
        body = QWidget()
        body.setStyleSheet(f"background: {BG_MAIN};")
        b_lay = QVBoxLayout()
        b_lay.setContentsMargins(0, 0, 0, 0)
        b_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setObjectName("lic_cont")
        container.setStyleSheet(f"QWidget#lic_cont {{ background: {BG_MAIN}; }}")
        vbox = QVBoxLayout()
        vbox.setContentsMargins(16, 12, 16, 8)
        vbox.setSpacing(6)

        for i, lib in enumerate(LICENSES):
            card = QWidget()
            card.setObjectName(f"lc_{i}")
            card.setStyleSheet(f"""
                QWidget#lc_{i} {{
                    background: {BG_CARD};
                    border: none;
                    border-left: 3px solid {ACCENT};
                    border-radius: 5px;
                }}
            """)
            cl = QVBoxLayout()
            cl.setContentsMargins(14, 9, 14, 9)
            cl.setSpacing(3)

            # 이름 행
            top = QHBoxLayout()
            top.setSpacing(7)

            lbl_name = QLabel(lib["name"])
            lbl_name.setFont(QFont("Malgun Gothic", 10, QFont.Bold))
            lbl_name.setStyleSheet(f"color: {FG_PRIMARY}; background: transparent;")

            lbl_ver = QLabel(f"v{lib['version']}")
            lbl_ver.setFont(QFont("Malgun Gothic", 8))
            lbl_ver.setStyleSheet(f"color: {FG_MUTED}; background: transparent;")

            bg_c, fg_c = _badge(lib["license"])
            lbl_lic = QLabel(lib["license"])
            lbl_lic.setFont(QFont("Malgun Gothic", 8))
            lbl_lic.setStyleSheet(
                f"color:{fg_c}; background:{bg_c}; border-radius:3px; padding:1px 7px;"
            )

            top.addWidget(lbl_name)
            top.addWidget(lbl_ver)
            top.addStretch()
            top.addWidget(lbl_lic)
            cl.addLayout(top)

            lbl_desc = QLabel(lib["desc"])
            lbl_desc.setFont(QFont("Malgun Gothic", 8))
            lbl_desc.setStyleSheet(f"color: {FG_SECONDARY}; background: transparent;")
            lbl_desc.setWordWrap(True)
            cl.addWidget(lbl_desc)

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

        b_lay.addWidget(scroll)
        body.setLayout(b_lay)
        layout.addWidget(body)

        # 닫기 버튼
        footer = QWidget()
        footer.setStyleSheet(f"background: {BG_MAIN};")
        f_lay = QHBoxLayout()
        f_lay.setContentsMargins(18, 8, 18, 14)
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        f_lay.addStretch()
        f_lay.addWidget(btn_close)
        f_lay.addStretch()
        footer.setLayout(f_lay)
        layout.addWidget(footer)

        self.setLayout(layout)
