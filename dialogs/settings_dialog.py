"""
환경설정 다이얼로그
- 저장 시 강제 종료 버그 수정: try/except 로 감싸고 signal 은 close() 이후가 아닌 close() 전에 emit
- 블루 포인트 테마 적용
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

# ── 블루 포인트 스타일시트 ───────────────────────────────────────────────────
BLUE_ACCENT  = "#29b6f6"
BLUE_BORDER  = "#1e3a4a"
BG_MAIN      = "#0f1a22"
BG_GROUP     = "#111e28"
BG_INPUT     = "#162030"
FG_MAIN      = "#b0b0b0"
FG_DIM       = "#666666"
FG_TITLE     = "#29b6f6"

STYLE = f"""
QDialog {{
    background: {BG_MAIN};
}}
QGroupBox {{
    background: {BG_GROUP};
    color: {FG_TITLE};
    border: 1px solid {BLUE_BORDER};
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    color: {BLUE_ACCENT};
}}
QLabel {{
    color: {FG_MAIN};
    background: transparent;
}}
QCheckBox {{
    color: {FG_MAIN};
    background: transparent;
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    background: {BG_INPUT};
    border: 1px solid {BLUE_BORDER};
    border-radius: 3px;
}}
QCheckBox::indicator:checked {{
    background: {BLUE_ACCENT};
    border: 1px solid {BLUE_ACCENT};
}}
QCheckBox::indicator:disabled {{
    background: #1a2a3a;
    border: 1px solid #1e3a4a;
}}
QSlider::groove:horizontal {{
    background: {BG_INPUT};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {BLUE_ACCENT};
    width: 14px; height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {BLUE_ACCENT};
    border-radius: 2px;
}}
QSpinBox {{
    background: {BG_INPUT};
    color: {FG_MAIN};
    border: 1px solid {BLUE_BORDER};
    border-radius: 4px;
    padding: 2px 6px;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {BG_INPUT};
    border: none;
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
QPushButton#btn_save {{
    background: #0e2a3a;
    color: {BLUE_ACCENT};
    border: 1px solid {BLUE_ACCENT};
    font-weight: bold;
}}
QPushButton#btn_save:hover {{
    background: #1a3a4a;
}}
"""

# 프리셋 색상 (블루 중심)
PRESET_COLORS = [
    "#29b6f6",  # 밝은 파랑
    "#4fc3f7",  # 연한 파랑
    "#0288d1",  # 진한 파랑
    "#ef5350",  # 빨강
    "#ff8a65",  # 주황
    "#ffd54f",  # 노랑
    "#81c784",  # 녹색
    "#ffffff",  # 흰색
    "#cccccc",  # 밝은 회색
    "#aaaaaa",  # 중간 회색
    "#666666",  # 어두운 회색
    "#333333",  # 매우 어두운 회색
]


class ColorButton(QPushButton):
    """색상 선택 버튼"""
    color_changed = pyqtSignal(str)

    def __init__(self, color: str = "#aaaaaa"):
        super().__init__()
        self.setFixedSize(60, 24)
        self._color = color
        self._apply()
        self.clicked.connect(self._pick)

    def _apply(self):
        self.setStyleSheet(
            f"background:{self._color}; border:1px solid {BLUE_BORDER}; border-radius:4px;"
        )

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
        self.setFixedSize(296, 130)
        self.setStyleSheet(STYLE)
        self._color = current
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(4)
        for i, color in enumerate(PRESET_COLORS):
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    border: 2px solid #1e3a4a;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid {BLUE_ACCENT};
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
        self.setFixedSize(430, 580)
        self.setStyleSheet(STYLE)
        self._build_ui()
        logger.debug("SettingsDialog opened")

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # ── 외관 ──────────────────────────────────────────────────────────
        grp_ap = QGroupBox("외관")
        g1 = QGridLayout()
        g1.setSpacing(8)
        g1.setColumnStretch(1, 1)

        g1.addWidget(QLabel("배경색"), 0, 0)
        self.btn_bg = ColorButton(self.cfg.get("bg_color", "#0d0d0d"))
        g1.addWidget(self.btn_bg, 0, 1, Qt.AlignLeft)

        g1.addWidget(QLabel("배경 투명도"), 1, 0)
        self.sld_alpha = QSlider(Qt.Horizontal)
        self.sld_alpha.setRange(0, 11)
        alpha_step = round((self.cfg.get("bg_alpha", 220) - 30) / 225 * 11)
        self.sld_alpha.setValue(max(0, min(11, alpha_step)))
        self.lbl_alpha = QLabel(str(self._step_to_alpha(self.sld_alpha.value())))
        self.lbl_alpha.setFixedWidth(30)
        self.sld_alpha.valueChanged.connect(
            lambda v: self.lbl_alpha.setText(str(self._step_to_alpha(v)))
        )
        row_a = QHBoxLayout()
        row_a.addWidget(self.sld_alpha)
        row_a.addWidget(self.lbl_alpha)
        g1.addLayout(row_a, 1, 1)

        g1.addWidget(QLabel("글자 크기"), 2, 0)
        self.spn_font = QSpinBox()
        self.spn_font.setRange(6, 20)
        self.spn_font.setValue(self.cfg.get("font_size", 9))
        g1.addWidget(self.spn_font, 2, 1, Qt.AlignLeft)

        g1.addWidget(QLabel("글자 색상"), 3, 0)
        self.btn_font_color = ColorButton(self.cfg.get("font_color", "#b0b0b0"))
        g1.addWidget(self.btn_font_color, 3, 1, Qt.AlignLeft)

        grp_ap.setLayout(g1)
        layout.addWidget(grp_ap)

        # ── 동작 ──────────────────────────────────────────────────────────
        grp_act = QGroupBox("동작")
        g_act = QVBoxLayout()

        self.chk_always_on_top = QCheckBox("항상 위에 표시")
        self.chk_always_on_top.setChecked(self.cfg.get("always_on_top", True))
        g_act.addWidget(self.chk_always_on_top)

        g_act.addWidget(QLabel("갱신 주기 (초)"))
        self.spn_interval = QSpinBox()
        self.spn_interval.setRange(3, 300)
        self.spn_interval.setValue(max(3, self.cfg.get("interval_ms", 10000) // 1000))
        g_act.addWidget(self.spn_interval)

        grp_act.setLayout(g_act)
        layout.addWidget(grp_act)

        # ── 증감 색상 ──────────────────────────────────────────────────────
        grp_clr = QGroupBox("증감 색상")
        g2 = QVBoxLayout()
        self.chk_use_color = QCheckBox("증감 색상 사용")
        self.chk_use_color.setChecked(self.cfg.get("use_change_color", True))
        self.chk_invert = QCheckBox("색상 반전  (상승=빨강, 하락=파랑)")
        self.chk_invert.setChecked(self.cfg.get("invert_color", False))
        g2.addWidget(self.chk_use_color)
        g2.addWidget(self.chk_invert)
        grp_clr.setLayout(g2)
        layout.addWidget(grp_clr)

        # ── 표시 항목 ──────────────────────────────────────────────────────
        grp_show = QGroupBox("플로팅 표시 항목")
        g3 = QGridLayout()
        g3.setSpacing(6)

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

        # ── 하단 버튼 ──────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_save  = QPushButton("저장하기")
        btn_save.setObjectName("btn_save")
        btn_save.clicked.connect(self._save)
        btn_close = QPushButton("취소")
        btn_close.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self.setLayout(layout)

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
            for key, chk in self.chk_map.items():
                self.cfg[key] = chk.isChecked()

            save_config(self.data_dir, self.cfg)
            logger.info("Settings saved successfully")

            # 먼저 signal emit → 그 다음 닫기
            self.settings_updated.emit(self.cfg.copy())
            self.accept()

        except Exception as e:
            logger.exception(f"Settings save error: {e}")
            QMessageBox.critical(
                self, "저장 오류",
                f"설정을 저장하는 중 오류가 발생했습니다.\n{e}"
            )
