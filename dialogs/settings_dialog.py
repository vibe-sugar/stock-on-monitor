"""
환경설정 다이얼로그
디자인 시스템:
  ACCENT      #5D87F6  — 밝은 파랑 (포인트, 활성 상태, 링크)
  ACCENT_DARK #111726  — 아주 어두운 네이비 (그룹박스 배경, 인풋 배경)
  BTN_BG      #132859  — 버튼 배경 (짙은 네이비)
  BTN_FG      #577CF7  — 버튼 글씨 (중간 파랑)
  BG_MAIN     #1A1F2E  — 다이얼로그/화면 배경 (다크 그레이-블루)
  BG_SURFACE  #222840  — 카드/그룹 배경
  BORDER      #2D3A5C  — 구분선/테두리 (절제된 블루-그레이)
  FG_PRIMARY  #D8DEF0  — 주요 텍스트 (밝은 블루-화이트)
  FG_SECONDARY #7A8AB0 — 보조 텍스트 (중간 블루-그레이)
  FG_MUTED    #4A5578  — 희미한 텍스트
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QSpinBox, QCheckBox, QGroupBox, QGridLayout,
    QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from core.config import save_config
import core.logger as logger

# ── 디자인 토큰 ────────────────────────────────────────────────────────────────
ACCENT       = "#5D87F6"   # 밝은 파랑 — 포인트
ACCENT_DARK  = "#111726"   # 아주 어두운 네이비
BTN_BG       = "#132859"   # 버튼 배경
BTN_FG       = "#577CF7"   # 버튼 글씨
BG_MAIN      = "#1A1F2E"   # 다이얼로그 배경
BG_SURFACE   = "#222840"   # 그룹박스 배경
BORDER       = "#2D3A5C"   # 테두리
FG_PRIMARY   = "#D8DEF0"   # 주요 텍스트
FG_SECONDARY = "#7A8AB0"   # 보조 텍스트
FG_MUTED     = "#4A5578"   # 희미한 텍스트
RED_SOFT     = "#F06292"   # 위험/삭제 액션

# 프리셋 색상 (ACCENT 중심 12개)
PRESET_COLORS = [
    "#5D87F6",  # ACCENT 파랑
    "#7B9FFF",  # 연한 파랑
    "#577CF7",  # BTN_FG 파랑
    "#3D6FE0",  # 진한 파랑
    "#A78BFA",  # 보라
    "#67E8F9",  # 시안
    "#34D399",  # 민트 초록
    "#F0A3A3",  # 연한 빨강
    "#F06292",  # 분홍
    "#FFD700",  # 골드
    "#D8DEF0",  # FG_PRIMARY 흰색
    "#7A8AB0",  # FG_SECONDARY 회색
]

STYLE = f"""
QDialog {{
    background: {BG_MAIN};
}}
QGroupBox {{
    background: {BG_SURFACE};
    color: {ACCENT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    font-size: 9pt;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: {ACCENT};
}}
QLabel {{
    color: {FG_PRIMARY};
    background: transparent;
    font-size: 9pt;
}}
QCheckBox {{
    color: {FG_PRIMARY};
    background: transparent;
    spacing: 8px;
    font-size: 9pt;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    background: {ACCENT_DARK};
    border: 1px solid {BORDER};
    border-radius: 4px;
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    image: none;
}}
QCheckBox::indicator:disabled {{
    background: {BG_SURFACE};
    border: 1px solid {FG_MUTED};
}}
QSlider::groove:horizontal {{
    background: {ACCENT_DARK};
    height: 5px;
    border-radius: 3px;
    border: 1px solid {BORDER};
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 15px;
    height: 15px;
    margin: -5px 0;
    border-radius: 8px;
    border: 2px solid {BG_MAIN};
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 3px;
}}
QSpinBox {{
    background: {ACCENT_DARK};
    color: {FG_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 9pt;
    min-width: 56px;
}}
QSpinBox:focus {{
    border-color: {ACCENT};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {ACCENT_DARK};
    border: none;
    width: 16px;
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
QPushButton#btn_save {{
    background: {ACCENT};
    color: #FFFFFF;
    border: 1px solid {ACCENT};
    font-weight: bold;
    padding: 7px 22px;
    font-size: 9pt;
}}
QPushButton#btn_save:hover {{
    background: #4A74E8;
    border-color: #4A74E8;
}}
QPushButton#btn_cancel {{
    background: {BG_SURFACE};
    color: {FG_SECONDARY};
    border: 1px solid {BORDER};
}}
QPushButton#btn_cancel:hover {{
    color: {FG_PRIMARY};
    border-color: {FG_SECONDARY};
}}
"""


class ColorButton(QPushButton):
    """색상 선택 버튼"""
    color_changed = pyqtSignal(str)

    def __init__(self, color: str = "#7A8AB0"):
        super().__init__()
        self.setFixedSize(64, 26)
        self._color = color
        self._apply()
        self.clicked.connect(self._pick)

    def _apply(self):
        # 버튼 배경색에 따라 텍스트 명도 자동 결정
        c = QColor(self._color)
        luminance = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        text_col = "#111726" if luminance > 128 else "#D8DEF0"
        self.setStyleSheet(
            f"background: {self._color};"
            f"color: {text_col};"
            f"border: 1px solid {BORDER};"
            f"border-radius: 6px;"
            f"font-size: 8pt;"
        )
        self.setText(self._color.upper())

    def set_color(self, hex_color: str):
        self._color = hex_color
        self._apply()

    def get_color(self) -> str:
        return self._color

    def _pick(self):
        dlg = ColorPickerDialog(self._color, self)
        if dlg.exec_() == QDialog.Accepted:
            color = dlg.get_color()
            self.set_color(color)
            self.color_changed.emit(color)


class ColorPickerDialog(QDialog):
    """12개 프리셋 색상 선택"""

    def __init__(self, current: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("색상 선택")
        self.setFixedSize(320, 140)
        self.setStyleSheet(f"""
            QDialog  {{ background: {BG_MAIN}; }}
            QLabel   {{ color: {FG_PRIMARY}; background: transparent; }}
            QPushButton {{
                background: {BTN_BG}; color: {BTN_FG};
                border: 1px solid {BORDER}; border-radius: 5px; padding: 4px 12px;
            }}
            QPushButton:hover {{ background: #1C3A7A; color: {ACCENT}; border-color: {ACCENT}; }}
        """)
        self._color = current
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(5)
        for i, color in enumerate(PRESET_COLORS):
            btn = QPushButton()
            btn.setFixedSize(38, 38)
            is_sel = (color.lower() == self._color.lower())
            border_col = ACCENT if is_sel else BORDER
            border_w   = "3px" if is_sel else "1px"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    border: {border_w} solid {border_col};
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    border: 2px solid {ACCENT};
                }}
            """)
            btn.clicked.connect(lambda _, c=color: self._pick(c))
            grid.addWidget(btn, i // 6, i % 6)
        layout.addLayout(grid)

        row = QHBoxLayout()
        btn_ok = QPushButton("확인")
        btn_cancel = QPushButton("취소")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        row.addStretch()
        row.addWidget(btn_ok)
        row.addWidget(btn_cancel)
        layout.addLayout(row)
        self.setLayout(layout)

    def _pick(self, color: str):
        self._color = color
        self.accept()

    def get_color(self) -> str:
        return self._color


class SettingsDialog(QDialog):
    settings_updated = pyqtSignal(dict)

    def __init__(self, data_dir: str, cfg: dict, parent=None):
        super().__init__(parent)
        self.data_dir = data_dir
        self.cfg      = cfg.copy()

        self.setWindowTitle("환경 설정")
        self.setFixedSize(440, 660)
        self.setStyleSheet(STYLE)
        self._build_ui()
        logger.debug("SettingsDialog opened")

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        # ── 외관 ──────────────────────────────────────────────────────────────
        grp_ap = QGroupBox("  외관")
        g1 = QGridLayout()
        g1.setSpacing(9)
        g1.setColumnStretch(1, 1)
        g1.setContentsMargins(14, 8, 14, 12)

        g1.addWidget(self._lbl("배경색"), 0, 0)
        self.btn_bg = ColorButton(self.cfg.get("bg_color", "#0d0d0d"))
        g1.addWidget(self.btn_bg, 0, 1, Qt.AlignLeft)

        g1.addWidget(self._lbl("배경 투명도"), 1, 0)
        self.sld_alpha = QSlider(Qt.Horizontal)
        self.sld_alpha.setRange(0, 11)
        alpha_step = round((self.cfg.get("bg_alpha", 220) - 30) / 225 * 11)
        self.sld_alpha.setValue(max(0, min(11, alpha_step)))
        self.lbl_alpha = QLabel(str(self._step_to_alpha(self.sld_alpha.value())))
        self.lbl_alpha.setFixedWidth(32)
        self.lbl_alpha.setStyleSheet(f"color: {FG_SECONDARY}; background: transparent;")
        self.sld_alpha.valueChanged.connect(
            lambda v: self.lbl_alpha.setText(str(self._step_to_alpha(v)))
        )
        row_a = QHBoxLayout()
        row_a.setSpacing(8)
        row_a.addWidget(self.sld_alpha)
        row_a.addWidget(self.lbl_alpha)
        g1.addLayout(row_a, 1, 1)

        g1.addWidget(self._lbl("글자 크기"), 2, 0)
        self.spn_font = QSpinBox()
        self.spn_font.setRange(6, 20)
        self.spn_font.setValue(self.cfg.get("font_size", 9))
        g1.addWidget(self.spn_font, 2, 1, Qt.AlignLeft)

        g1.addWidget(self._lbl("글자 색상"), 3, 0)
        self.btn_font_color = ColorButton(self.cfg.get("font_color", "#b0b0b0"))
        g1.addWidget(self.btn_font_color, 3, 1, Qt.AlignLeft)

        grp_ap.setLayout(g1)
        layout.addWidget(grp_ap)

        # ── 테두리 ────────────────────────────────────────────────────────────
        grp_border = QGroupBox("  테두리")
        g_bd = QGridLayout()
        g_bd.setSpacing(9)
        g_bd.setColumnStretch(1, 1)
        g_bd.setContentsMargins(14, 8, 14, 12)

        g_bd.addWidget(self._lbl("두께  (0 = 없음)"), 0, 0)
        self.spn_border_width = QSpinBox()
        self.spn_border_width.setRange(0, 5)
        self.spn_border_width.setValue(int(self.cfg.get("border_width", 0)))
        g_bd.addWidget(self.spn_border_width, 0, 1, Qt.AlignLeft)

        g_bd.addWidget(self._lbl("테두리 색상"), 1, 0)
        self.btn_border_color = ColorButton(self.cfg.get("border_color", "#2D3A5C"))
        g_bd.addWidget(self.btn_border_color, 1, 1, Qt.AlignLeft)

        grp_border.setLayout(g_bd)
        layout.addWidget(grp_border)

        # ── 동작 ──────────────────────────────────────────────────────────────
        grp_act = QGroupBox("  동작")
        g_act = QVBoxLayout()
        g_act.setSpacing(8)
        g_act.setContentsMargins(14, 8, 14, 12)

        self.chk_always_on_top = QCheckBox("항상 위에 표시")
        self.chk_always_on_top.setChecked(self.cfg.get("always_on_top", True))
        g_act.addWidget(self.chk_always_on_top)

        row_iv = QHBoxLayout()
        row_iv.addWidget(self._lbl("갱신 주기 (초)"))
        row_iv.addSpacing(8)
        self.spn_interval = QSpinBox()
        self.spn_interval.setRange(3, 300)
        self.spn_interval.setValue(max(3, self.cfg.get("interval_ms", 10000) // 1000))
        row_iv.addWidget(self.spn_interval)
        row_iv.addStretch()
        g_act.addLayout(row_iv)

        grp_act.setLayout(g_act)
        layout.addWidget(grp_act)

        # ── 증감 색상 ─────────────────────────────────────────────────────────
        grp_clr = QGroupBox("  증감 색상")
        g2 = QVBoxLayout()
        g2.setSpacing(8)
        g2.setContentsMargins(14, 8, 14, 12)
        self.chk_use_color = QCheckBox("증감 색상 사용  (상승 파랑 / 하락 빨강)")
        self.chk_use_color.setChecked(self.cfg.get("use_change_color", True))
        self.chk_invert = QCheckBox("색상 반전  (상승 빨강 / 하락 파랑)")
        self.chk_invert.setChecked(self.cfg.get("invert_color", False))
        g2.addWidget(self.chk_use_color)
        g2.addWidget(self.chk_invert)
        grp_clr.setLayout(g2)
        layout.addWidget(grp_clr)

        # ── 표시 항목 ─────────────────────────────────────────────────────────
        grp_show = QGroupBox("  표시 항목")
        g3 = QGridLayout()
        g3.setSpacing(7)
        g3.setContentsMargins(14, 8, 14, 12)

        checks = [
            ("show_name",       "종목명"),
            ("show_code",       "종목코드"),
            ("show_change_amt", "금일 변동액"),
            ("show_change_pct", "금일 변동 %"),
            ("show_profit_amt", "손익액"),
            ("show_profit_pct", "손익률 %"),
            ("show_total",      "총평가액"),
            ("show_summary",    "합산 요약"),
        ]
        self.chk_map: dict[str, QCheckBox] = {}
        for i, (key, label) in enumerate(checks):
            c = QCheckBox(label)
            c.setChecked(self.cfg.get(key, False))
            self.chk_map[key] = c
            g3.addWidget(c, i // 2, i % 2)

        grp_show.setLayout(g3)
        layout.addWidget(grp_show)

        # ── 하단 버튼 ─────────────────────────────────────────────────────────
        layout.addSpacing(4)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_save   = QPushButton("저장하기")
        btn_save.setObjectName("btn_save")
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton("취소")
        btn_cancel.setObjectName("btn_cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    @staticmethod
    def _lbl(text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(f"color: {FG_PRIMARY}; background: transparent; font-size: 9pt;")
        return l

    @staticmethod
    def _step_to_alpha(step: int) -> int:
        return int(30 + step / 11 * 225)

    def _save(self):
        """설정 저장 — 강제 종료 방지를 위해 완전히 try/except 로 감쌈"""
        try:
            self.cfg["bg_color"]         = self.btn_bg.get_color()
            self.cfg["bg_alpha"]         = self._step_to_alpha(self.sld_alpha.value())
            self.cfg["font_size"]        = self.spn_font.value()
            self.cfg["font_color"]       = self.btn_font_color.get_color()
            self.cfg["always_on_top"]    = self.chk_always_on_top.isChecked()
            self.cfg["interval_ms"]      = self.spn_interval.value() * 1000
            self.cfg["use_change_color"] = self.chk_use_color.isChecked()
            self.cfg["invert_color"]     = self.chk_invert.isChecked()
            self.cfg["border_width"]     = self.spn_border_width.value()
            self.cfg["border_color"]     = self.btn_border_color.get_color()
            for key, chk in self.chk_map.items():
                self.cfg[key] = chk.isChecked()

            save_config(self.data_dir, self.cfg)
            logger.info("Settings saved successfully")

            self.settings_updated.emit(self.cfg.copy())
            self.accept()

        except Exception as e:
            logger.exception(f"Settings save error: {e}")
            QMessageBox.critical(
                self, "저장 오류",
                f"설정을 저장하는 중 오류가 발생했습니다.\n{e}"
            )
