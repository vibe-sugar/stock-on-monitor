"""
환경설정 다이얼로그
디자인: 어두운 그레이 배경 (#1A1B1C), 파랑은 포인트만 (#5D87F6)
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QSpinBox, QCheckBox, QGroupBox, QGridLayout,
    QMessageBox, QColorDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from core.config import save_config
import core.logger as logger

# ── 디자인 토큰 ────────────────────────────────────────────────────────────────
ACCENT       = "#5D87F6"   # 파랑 포인트
BG_MAIN      = "#1A1B1C"   # 메인 배경
BG_SURFACE   = "#242526"   # 그룹박스 배경
BG_INPUT     = "#2C2D2E"   # 인풋/스핀박스 배경
BORDER       = "#3A3B3C"   # 테두리
BTN_BG       = "#1E2A4A"   # 버튼 배경 (어두운 네이비)
BTN_FG       = "#7DA4F8"   # 버튼 글씨
FG_PRIMARY   = "#E0E0E0"   # 주요 텍스트
FG_SECONDARY = "#909090"   # 보조 텍스트
FG_MUTED     = "#555555"   # 희미한 텍스트


STYLE = f"""
QDialog {{
    background: {BG_MAIN};
}}
QGroupBox {{
    background: {BG_SURFACE};
    color: {FG_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    font-size: 9pt;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {ACCENT};
    font-weight: bold;
}}
QLabel {{
    color: {FG_PRIMARY};
    background: transparent;
    font-size: 9pt;
}}
QCheckBox {{
    color: {FG_PRIMARY};
    background: transparent;
    spacing: 7px;
    font-size: 9pt;
}}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 3px;
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
}}
QCheckBox::indicator:disabled {{
    background: {BG_SURFACE};
    border: 1px solid {BORDER};
}}
QSlider::groove:horizontal {{
    background: {BG_INPUT};
    height: 4px;
    border-radius: 2px;
    border: 1px solid {BORDER};
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 14px; height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QSpinBox {{
    background: {BG_INPUT};
    color: {FG_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 9pt;
    min-width: 52px;
}}
QSpinBox:focus {{
    border-color: {ACCENT};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {BG_INPUT};
    border: none;
    width: 14px;
}}
QPushButton {{
    background: {BTN_BG};
    color: {BTN_FG};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 14px;
    font-size: 9pt;
}}
QPushButton:hover {{
    background: #263A6A;
    color: {ACCENT};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background: #141E38;
}}
QPushButton#btn_save {{
    background: {ACCENT};
    color: #FFFFFF;
    border: 1px solid {ACCENT};
    font-weight: bold;
    padding: 6px 20px;
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
    background: #2E2F30;
}}
"""


class ColorButton(QPushButton):
    """색상 선택 버튼 — 선택된 색상을 배경 스와치로만 표시 (텍스트 없음)"""
    color_changed = pyqtSignal(str)

    def __init__(self, color: str = "#909090"):
        super().__init__()
        self.setFixedSize(44, 26)
        self._color = color
        self._apply()
        self.clicked.connect(self._pick)

    def _apply(self):
        self.setStyleSheet(
            f"background: {self._color};"
            f"border: 1px solid {BORDER}; border-radius: 5px;"
        )
        self.setText("")  # 텍스트 없음 — 색상 스와치만 표시

    def set_color(self, hex_color: str):
        self._color = hex_color
        self._apply()

    def get_color(self) -> str:
        return self._color

    def _pick(self):
        # QColorDialog — 그림판 수준의 풀 HSV 컬러 휠/스펙트럼 선택
        initial = QColor(self._color)
        color = QColorDialog.getColor(
            initial, self,
            "색상 선택",
            QColorDialog.ShowAlphaChannel,
        )
        if color.isValid():
            hex_color = color.name()  # '#rrggbb'
            self.set_color(hex_color)
            self.color_changed.emit(hex_color)


# ColorPickerDialog 는 더 이상 사용하지 않음.
# ColorButton._pick() 에서 QColorDialog.getColor() 를 직접 호출함.


class SettingsDialog(QDialog):
    settings_updated = pyqtSignal(dict)

    def __init__(self, data_dir: str, cfg: dict, parent=None):
        super().__init__(parent)
        self.data_dir = data_dir
        self.cfg      = cfg.copy()

        self.setWindowTitle("환경 설정")
        self.setFixedSize(430, 640)
        self.setStyleSheet(STYLE)
        self._build_ui()
        logger.debug("SettingsDialog opened")

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # ── 외관 ──────────────────────────────────────────────────────────────
        grp_ap = QGroupBox("외관")
        g1 = QGridLayout()
        g1.setSpacing(8)
        g1.setColumnStretch(1, 1)
        g1.setContentsMargins(12, 6, 12, 10)

        g1.addWidget(self._lbl("배경색"), 0, 0)
        self.btn_bg = ColorButton(self.cfg.get("bg_color", "#1A1B1C"))
        g1.addWidget(self.btn_bg, 0, 1, Qt.AlignLeft)

        g1.addWidget(self._lbl("배경 투명도"), 1, 0)
        self.sld_alpha = QSlider(Qt.Horizontal)
        self.sld_alpha.setRange(0, 11)
        alpha_step = round((self.cfg.get("bg_alpha", 220) - 30) / 225 * 11)
        self.sld_alpha.setValue(max(0, min(11, alpha_step)))
        self.lbl_alpha = QLabel(str(self.sld_alpha.value() + 1))  # 1~12 단계 표시
        self.lbl_alpha.setFixedWidth(24)
        self.lbl_alpha.setStyleSheet(f"color: {FG_SECONDARY}; background: transparent;")
        self.sld_alpha.valueChanged.connect(
            lambda v: self.lbl_alpha.setText(str(v + 1))  # 0→"1", 11→"12"
        )
        row_a = QHBoxLayout()
        row_a.setSpacing(6)
        row_a.addWidget(self.sld_alpha)
        row_a.addWidget(self.lbl_alpha)
        g1.addLayout(row_a, 1, 1)

        g1.addWidget(self._lbl("글자 크기"), 2, 0)
        self.spn_font = QSpinBox()
        self.spn_font.setRange(6, 20)
        self.spn_font.setValue(self.cfg.get("font_size", 9))
        g1.addWidget(self.spn_font, 2, 1, Qt.AlignLeft)

        g1.addWidget(self._lbl("글자 색상"), 3, 0)
        self.btn_font_color = ColorButton(self.cfg.get("font_color", "#E0E0E0"))
        g1.addWidget(self.btn_font_color, 3, 1, Qt.AlignLeft)

        grp_ap.setLayout(g1)
        layout.addWidget(grp_ap)

        # ── 테두리 ────────────────────────────────────────────────────────────
        grp_border = QGroupBox("테두리")
        g_bd = QGridLayout()
        g_bd.setSpacing(8)
        g_bd.setColumnStretch(1, 1)
        g_bd.setContentsMargins(12, 6, 12, 10)

        g_bd.addWidget(self._lbl("두께  (0 = 없음)"), 0, 0)
        self.spn_border_width = QSpinBox()
        self.spn_border_width.setRange(0, 5)
        self.spn_border_width.setValue(int(self.cfg.get("border_width", 0)))
        g_bd.addWidget(self.spn_border_width, 0, 1, Qt.AlignLeft)

        g_bd.addWidget(self._lbl("테두리 색상"), 1, 0)
        self.btn_border_color = ColorButton(self.cfg.get("border_color", "#3A3B3C"))
        g_bd.addWidget(self.btn_border_color, 1, 1, Qt.AlignLeft)

        grp_border.setLayout(g_bd)
        layout.addWidget(grp_border)

        # ── 동작 ──────────────────────────────────────────────────────────────
        grp_act = QGroupBox("동작")
        g_act = QVBoxLayout()
        g_act.setSpacing(7)
        g_act.setContentsMargins(12, 6, 12, 10)

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
        grp_clr = QGroupBox("증감 색상")
        g2 = QVBoxLayout()
        g2.setSpacing(7)
        g2.setContentsMargins(12, 6, 12, 10)
        self.chk_use_color = QCheckBox("증감 색상 사용  (상승 파랑 / 하락 분홍)")
        self.chk_use_color.setChecked(self.cfg.get("use_change_color", True))
        self.chk_invert = QCheckBox("색상 반전  (상승 분홍 / 하락 파랑)")
        self.chk_invert.setChecked(self.cfg.get("invert_color", False))
        g2.addWidget(self.chk_use_color)
        g2.addWidget(self.chk_invert)
        grp_clr.setLayout(g2)
        layout.addWidget(grp_clr)

        # ── 표시 항목 ─────────────────────────────────────────────────────────
        grp_show = QGroupBox("표시 항목")
        g3 = QGridLayout()
        g3.setSpacing(6)
        g3.setContentsMargins(12, 6, 12, 10)

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
        layout.addSpacing(2)
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
