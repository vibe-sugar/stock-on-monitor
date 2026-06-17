from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QSpinBox, QCheckBox, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from core.config import save_config

STYLE = """
QDialog        { background: #1a1a1a; }
QGroupBox      {
    background: #1a1a1a; color: #888888;
    border: 1px solid #2a2a2a; border-radius: 6px;
    margin-top: 8px; padding-top: 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; }
QLabel         { color: #aaaaaa; background: transparent; }
QCheckBox      { color: #aaaaaa; background: transparent; spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    background: #2a2a2a; border: 1px solid #444; border-radius: 3px;
}
QCheckBox::indicator:checked { background: #555555; border: 1px solid #888; }
QSlider::groove:horizontal {
    background: #2a2a2a; height: 4px; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #666666; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}
QSpinBox {
    background: #2a2a2a; color: #aaaaaa;
    border: 1px solid #333; border-radius: 4px; padding: 2px 6px;
}
QPushButton {
    background: #2a2a2a; color: #aaaaaa;
    border: 1px solid #333; border-radius: 4px; padding: 5px 14px;
}
QPushButton:hover { background: #3a3a3a; color: #cccccc; }
"""

# 12개 프리셋 색상
PRESET_COLORS = [
    "#FF5C5C",  # 빨강
    "#FF8C42",  # 주황
    "#FFD700",  # 노랑
    "#90EE90",  # 연두
    "#4FC3F7",  # 파랑
    "#9C27B0",  # 보라
    "#FFFFFF",  # 흰색
    "#CCCCCC",  # 밝은 회색
    "#AAAAAA",  # 중간 회색
    "#888888",  # 어두운 회색
    "#666666",  # 더 어두운 회색
    "#444444",  # 검은색에 가까운 회색
]


class ColorButton(QPushButton):
    """프리셋 색상 선택 버튼"""
    color_changed = pyqtSignal(str)

    def __init__(self, color="#aaaaaa"):
        super().__init__()
        self.setFixedSize(60, 24)
        self._color = color
        self.set_color(color)
        self.clicked.connect(self._pick)

    def set_color(self, hex_color):
        self._color = hex_color
        self.setStyleSheet(
            f"background:{hex_color}; border:1px solid #555; border-radius:4px;"
        )

    def get_color(self):
        return self._color

    def _pick(self):
        """프리셋 색상 선택 다이얼로그"""
        dlg = ColorPickerDialog(self._color, self)
        if dlg.exec_():
            color = dlg.get_selected_color()
            self.set_color(color)
            self.color_changed.emit(color)


class ColorPickerDialog(QDialog):
    """12개 프리셋 색상 선택 다이얼로그"""
    def __init__(self, current_color, parent=None):
        super().__init__(parent)
        self.setWindowTitle("색상 선택")
        self.setFixedSize(280, 180)
        self.setStyleSheet(STYLE)
        self._selected_color = current_color
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(6)

        for i, color in enumerate(PRESET_COLORS):
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    border: 2px solid #555;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #aaa;
                }}
            """)
            btn.clicked.connect(lambda checked, c=color: self._select_color(c))
            grid.addWidget(btn, i // 6, i % 6)

        layout.addLayout(grid)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("확인")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _select_color(self, color):
        self._selected_color = color
        self.accept()

    def get_selected_color(self):
        return self._selected_color


class SettingsDialog(QDialog):
    settings_updated = pyqtSignal(dict)

    def __init__(self, data_dir, cfg, parent=None):
        super().__init__(parent)
        self.data_dir = data_dir
        self.cfg      = cfg.copy()

        self.setWindowTitle("환경 설정")
        self.setFixedSize(420, 620)
        self.setStyleSheet(STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # ── 외관 ──────────────────────────────────────
        grp_ap = QGroupBox("외관")
        g1 = QGridLayout()
        g1.setSpacing(8)

        g1.addWidget(QLabel("배경색"), 0, 0)
        self.btn_bg = ColorButton(self.cfg.get("bg_color", "#111111"))
        g1.addWidget(self.btn_bg, 0, 1)

        g1.addWidget(QLabel("배경 투명도"), 1, 0)
        self.sld_alpha = QSlider(Qt.Horizontal)
        self.sld_alpha.setRange(0, 11)  # 12단계 (0~11)
        # 기존 값을 12단계로 변환
        current_alpha = self.cfg.get("bg_alpha", 210)
        alpha_step = round((current_alpha - 30) / (255 - 30) * 11)
        self.sld_alpha.setValue(max(0, min(11, alpha_step)))
        self.lbl_alpha = QLabel(self._alpha_to_label(self.sld_alpha.value()))
        self.sld_alpha.valueChanged.connect(lambda v: self.lbl_alpha.setText(self._alpha_to_label(v)))
        row_a = QHBoxLayout()
        row_a.addWidget(self.sld_alpha)
        row_a.addWidget(self.lbl_alpha)
        g1.addLayout(row_a, 1, 1)

        g1.addWidget(QLabel("글자 크기"), 2, 0)
        self.spn_font = QSpinBox()
        self.spn_font.setRange(6, 20)
        self.spn_font.setValue(self.cfg.get("font_size", 9))
        g1.addWidget(self.spn_font, 2, 1)

        g1.addWidget(QLabel("글자 색상"), 3, 0)
        self.btn_font_color = ColorButton(self.cfg.get("font_color", "#aaaaaa"))
        g1.addWidget(self.btn_font_color, 3, 1)

        grp_ap.setLayout(g1)
        layout.addWidget(grp_ap)

        # ── 동작 ──────────────────────────────────────
        grp_act = QGroupBox("동작")
        g_act = QVBoxLayout()
        self.chk_always_on_top = QCheckBox("항상 위에 표시")
        self.chk_always_on_top.setChecked(self.cfg.get("always_on_top", True))
        g_act.addWidget(self.chk_always_on_top)
        grp_act.setLayout(g_act)
        layout.addWidget(grp_act)

        # ── 증감 색상 ──────────────────────────────────
        grp_clr = QGroupBox("증감 색상")
        g2 = QVBoxLayout()
        self.chk_use_color = QCheckBox("증감 색상 사용")
        self.chk_use_color.setChecked(self.cfg.get("use_change_color", True))
        self.chk_invert    = QCheckBox("색상 반전 (상승=파랑, 하락=빨강)")
        self.chk_invert.setChecked(self.cfg.get("invert_color", False))
        g2.addWidget(self.chk_use_color)
        g2.addWidget(self.chk_invert)
        grp_clr.setLayout(g2)
        layout.addWidget(grp_clr)

        # ── 표시 항목 ──────────────────────────────────
        grp_show = QGroupBox("플로팅 표시 항목")
        g3 = QGridLayout()
        g3.setSpacing(6)

        checks = [
            ("show_current_price", "현재가", True),  # (key, label, disabled)
            ("show_code",       "종목코드", False),
            ("show_name",       "종목명", False),
            ("show_change_amt", "금일 변동액", False),
            ("show_change_pct", "금일 변동 %", False),
            ("show_profit_amt", "총액 변동", False),
            ("show_profit_pct", "총액 변동 %", False),
            ("show_total",      "총액", False),
        ]
        self.chk_map = {}
        for i, item in enumerate(checks):
            if len(item) == 3:
                key, label, disabled = item
            else:
                key, label = item
                disabled = False
            
            c = QCheckBox(label)
            c.setChecked(self.cfg.get(key, False))
            if disabled:
                c.setEnabled(False)
                c.setChecked(True)
            self.chk_map[key] = c
            g3.addWidget(c, i // 2, i % 2)

        grp_show.setLayout(g3)
        layout.addWidget(grp_show)

        # ── 합산 총 자산 ───────────────────────────────
        grp_sum = QGroupBox("합산 총 자산")
        g4 = QVBoxLayout()
        self.chk_summary = QCheckBox("총 자산 및 수익 표시")
        self.chk_summary.setChecked(self.cfg.get("show_summary", False))
        g4.addWidget(self.chk_summary)
        grp_sum.setLayout(g4)
        layout.addWidget(grp_sum)

        # ── 하단 버튼 ──────────────────────────────────
        btn_row = QHBoxLayout()
        btn_save  = QPushButton("저장 & 닫기")
        btn_save.clicked.connect(self._save_and_close)
        btn_close = QPushButton("취소")
        btn_close.clicked.connect(self.close)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _alpha_to_label(self, step):
        """12단계 슬라이더 값을 투명도 레이블로 변환"""
        alpha_value = 30 + (step / 11) * (255 - 30)
        return f"{int(alpha_value)}"

    def _alpha_to_value(self, step):
        """12단계 슬라이더 값을 실제 투명도 값으로 변환"""
        return int(30 + (step / 11) * (255 - 30))

    def _save_and_close(self):
        self.cfg["bg_color"]         = self.btn_bg.get_color()
        self.cfg["bg_alpha"]         = self._alpha_to_value(self.sld_alpha.value())
        self.cfg["font_size"]        = self.spn_font.value()
        self.cfg["font_color"]       = self.btn_font_color.get_color()
        self.cfg["always_on_top"]    = self.chk_always_on_top.isChecked()
        self.cfg["use_change_color"] = self.chk_use_color.isChecked()
        self.cfg["invert_color"]     = self.chk_invert.isChecked()
        self.cfg["show_summary"]     = self.chk_summary.isChecked()
        for key, chk in self.chk_map.items():
            self.cfg[key] = chk.isChecked()

        save_config(self.data_dir, self.cfg)
        self.settings_updated.emit(self.cfg)
        self.close()
