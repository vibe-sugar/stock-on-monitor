import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMenu, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QFont, QColor, QBrush

from core.fetcher import fetch_price
from core.constants import APP_NAME


class FloatingWidget(QWidget):
    def __init__(self, data_dir, cfg, stocks):
        super().__init__()
        self.data_dir = data_dir
        self.cfg = cfg
        self.stocks = [s for s in stocks if s.get("active", True)]
        self._drag_pos = QPoint()
        
        # UI 컴포넌트 초기화
        self.table = None
        self.row_widgets = []
        self.col_map = {}
        self.summary_row_idx = -1
        self.lbl_sum_current = None
        self.lbl_sum_profit = None

        self._build_ui()
        self._apply_always_on_top()

        # 타이머 설정
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_prices)
        self.timer.start(self.cfg.get("interval_ms", 10000))
        self.update_prices()

    def _apply_always_on_top(self):
        """항상 위 설정 적용"""
        always_on_top = self.cfg.get("always_on_top", True)
        flags = Qt.FramelessWindowHint | Qt.Tool
        if always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.show()

    def _build_ui(self):
        """UI 구성"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.card = QWidget(self)
        self.card.setObjectName("card")
        self._apply_card_style()

        self.stock_layout = QVBoxLayout()
        self.stock_layout.setContentsMargins(12, 8, 12, 8)
        self.stock_layout.setSpacing(4)

        self._rebuild_rows()

        self.card.setLayout(self.stock_layout)
        outer.addWidget(self.card)
        self.setLayout(outer)

    def _apply_card_style(self):
        """카드 스타일 적용"""
        bg = self.cfg.get("bg_color", "#111111")
        alpha = self.cfg.get("bg_alpha", 210)
        c = QColor(bg)
        self.card.setStyleSheet(f"""
            QWidget#card {{
                background-color: rgba({c.red()},{c.green()},{c.blue()},{alpha});
                border-radius: 8px;
            }}
        """)

    def _rebuild_rows(self):
        """테이블 재구성"""
        # 기존 레이아웃 정리
        while self.stock_layout.count():
            item = self.stock_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.row_widgets = []
        self.table = None
        self.summary_row_idx = -1
        self.lbl_sum_current = None
        self.lbl_sum_profit = None

        # 종목이 없는 경우
        if not self.stocks:
            empty_widget = QWidget()
            empty_widget.setStyleSheet("background: transparent;")
            empty_layout = QVBoxLayout()
            empty_layout.setContentsMargins(12, 20, 12, 20)
            empty_layout.setSpacing(0)

            lbl_guide = QLabel("우클릭하여 종목을 설정해주세요.")
            lbl_guide.setFont(QFont("Malgun Gothic", self.cfg.get("font_size", 9)))
            lbl_guide.setStyleSheet(f"color:{self.cfg.get('font_color', '#aaaaaa')}; background:transparent;")
            lbl_guide.setAlignment(Qt.AlignCenter)

            empty_layout.addWidget(lbl_guide)
            empty_widget.setLayout(empty_layout)
            self.stock_layout.addWidget(empty_widget)
            return

        # 열 구성 계산
        fs = self.cfg.get("font_size", 9)
        fc = self.cfg.get("font_color", "#aaaaaa")
        
        col_count = 0
        col_map = {}
        
        if self.cfg.get("show_name"):
            col_map["name"] = col_count
            col_count += 1
        if self.cfg.get("show_code"):
            col_map["code"] = col_count
            col_count += 1
        
        col_map["price"] = col_count
        col_count += 1
        
        if self.cfg.get("show_change_amt"):
            col_map["change_amt"] = col_count
            col_count += 1
        elif self.cfg.get("show_change_pct"):
            col_map["change_pct"] = col_count
            col_count += 1
        
        if self.cfg.get("show_profit_amt"):
            col_map["profit_amt"] = col_count
            col_count += 1
        elif self.cfg.get("show_profit_pct"):
            col_map["profit_pct"] = col_count
            col_count += 1
        
        if self.cfg.get("show_total"):
            col_map["total"] = col_count
            col_count += 1
        
        self.col_map = col_map

        # 테이블 행 개수 (요약 행 포함 여부)
        row_count = len(self.stocks)
        if self.cfg.get("show_summary"):
            self.summary_row_idx = row_count
            row_count += 1

        # 테이블 생성
        table = QTableWidget(row_count, col_count)
        table.setStyleSheet(f"""
            QTableWidget {{
                background: transparent;
                border: none;
                gridline-color: rgba(255,255,255,15);
            }}
            QTableWidget::item {{
                padding: 2px;
                border: none;
            }}
            QHeaderView::section {{
                background: transparent;
                border: none;
                padding: 0px;
            }}
            QScrollBar {{
                width: 0px;
                height: 0px;
            }}
        """)
        table.horizontalHeader().setVisible(False)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 행 높이 설정
        for row in range(row_count):
            table.setRowHeight(row, fs + 6)

        # 데이터 행 채우기
        for row, stock in enumerate(self.stocks):
            row_data = {}

            if "name" in col_map:
                item = QTableWidgetItem(stock.get("name", ""))
                item.setFont(QFont("Malgun Gothic", fs - 1))
                item.setForeground(QBrush(QColor(fc)))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(row, col_map["name"], item)
                row_data["name"] = item

            if "code" in col_map:
                item = QTableWidgetItem(stock.get("code", ""))
                item.setFont(QFont("Malgun Gothic", fs - 1))
                item.setForeground(QBrush(QColor("#666666")))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(row, col_map["code"], item)
                row_data["code"] = item

            # 가격
            item = QTableWidgetItem("--")
            item.setFont(QFont("Malgun Gothic", fs, QFont.Bold))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, col_map["price"], item)
            row_data["price"] = item

            # 변동액/변동률
            if "change_amt" in col_map:
                item = QTableWidgetItem("--")
                item.setFont(QFont("Malgun Gothic", fs - 1))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row, col_map["change_amt"], item)
                row_data["change_amt"] = item
            elif "change_pct" in col_map:
                item = QTableWidgetItem("--")
                item.setFont(QFont("Malgun Gothic", fs - 1))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row, col_map["change_pct"], item)
                row_data["change_pct"] = item

            # 손익액/손익률
            if "profit_amt" in col_map:
                item = QTableWidgetItem("--")
                item.setFont(QFont("Malgun Gothic", fs - 1))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row, col_map["profit_amt"], item)
                row_data["profit_amt"] = item
            elif "profit_pct" in col_map:
                item = QTableWidgetItem("--")
                item.setFont(QFont("Malgun Gothic", fs - 1))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row, col_map["profit_pct"], item)
                row_data["profit_pct"] = item

            # 총액
            if "total" in col_map:
                item = QTableWidgetItem("--")
                item.setFont(QFont("Malgun Gothic", fs - 1))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row, col_map["total"], item)
                row_data["total"] = item

            self.row_widgets.append(row_data)

        # 요약 행 설정
        if self.cfg.get("show_summary") and self.summary_row_idx >= 0:
            summary_row = self.summary_row_idx
            
            # 모든 셀 초기화
            for col in range(col_count):
                item = QTableWidgetItem("")
                item.setBackground(QColor("transparent"))
                table.setItem(summary_row, col, item)

            # 첫 번째 셀에 총 자산 표시
            summary_item = QTableWidgetItem("--")
            summary_item.setFont(QFont("Malgun Gothic", fs - 1))
            summary_item.setForeground(QBrush(QColor(fc)))
            summary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(summary_row, 0, summary_item)
            self.lbl_sum_current = summary_item

            # 마지막 셀에 총 손익 표시
            profit_item = QTableWidgetItem("--")
            profit_item.setFont(QFont("Malgun Gothic", fs - 1))
            profit_item.setForeground(QBrush(QColor(fc)))
            profit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(summary_row, col_count - 1, profit_item)
            self.lbl_sum_profit = profit_item

        # 테이블 설정 완료
        table.resizeColumnsToContents()
        table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        table.installEventFilter(self)

        self.stock_layout.addWidget(table)
        self.table = table

    def update_prices(self):
        """가격 갱신"""
        if not self.stocks or self.table is None:
            if self.card:
                self.card.adjustSize()
                self.resize(self.card.sizeHint())
            return

        total_buy = 0
        total_current = 0
        fc = self.cfg.get("font_color", "#aaaaaa")

        # 각 종목 데이터 갱신
        for i, stock in enumerate(self.stocks):
            if i >= len(self.row_widgets):
                break

            row_data = self.row_widgets[i]
            data = fetch_price(stock["market"], stock["code"])

            if data is None:
                row_data["price"].setText("ERR")
                continue

            current = data["current"]
            change = data["change"]
            change_pct = data["change_pct"]
            buy_price = stock["buy_price"]
            quantity = stock["quantity"]
            profit_amt = (current - buy_price) * quantity
            profit_pct = (current - buy_price) / buy_price * 100 if buy_price != 0 else 0
            total = current * quantity

            total_buy += buy_price * quantity
            total_current += current * quantity

            arrow = "▲" if change > 0 else ("▼" if change < 0 else "─")
            c_col = self._change_color(change)
            p_col = self._change_color(profit_amt)

            # 종목명
            if "name" in row_data:
                row_data["name"].setText(stock.get("name", ""))
                row_data["name"].setForeground(QBrush(QColor(fc)))

            # 종목코드
            if "code" in row_data:
                row_data["code"].setText(stock.get("code", ""))
                row_data["code"].setForeground(QBrush(QColor("#666666")))

            # 가격
            row_data["price"].setText(f"{int(current):,}")
            color = c_col if self.cfg.get("use_change_color") else fc
            row_data["price"].setForeground(QBrush(QColor(color)))

            # 변동액/변동률
            if "change_amt" in row_data:
                change_text = f"{arrow} {change:+,.0f}"
                row_data["change_amt"].setText(change_text)
                row_data["change_amt"].setForeground(QBrush(QColor(c_col)))
            elif "change_pct" in row_data:
                row_data["change_pct"].setText(f"{arrow} {change_pct:+.2f}%")
                row_data["change_pct"].setForeground(QBrush(QColor(c_col)))

            # 손익액/손익률
            if "profit_amt" in row_data:
                profit_text = f"{'+' if profit_amt >= 0 else ''}{int(profit_amt):,}원"
                row_data["profit_amt"].setText(profit_text)
                row_data["profit_amt"].setForeground(QBrush(QColor(p_col)))
            elif "profit_pct" in row_data:
                row_data["profit_pct"].setText(f"{profit_pct:+.2f}%")
                row_data["profit_pct"].setForeground(QBrush(QColor(p_col)))

            # 총액
            if "total" in row_data:
                row_data["total"].setText(f"{int(total):,}원")
                row_data["total"].setForeground(QBrush(QColor(fc)))

        # 테이블 크기 조정
        if self.table:
            self.table.resizeColumnsToContents()

        # 요약 행 갱신
        if self.cfg.get("show_summary") and self.lbl_sum_current and self.lbl_sum_profit:
            total_profit = total_current - total_buy
            p_col = self._change_color(total_profit)
            profit_pct = (total_profit / total_buy * 100) if total_buy > 0 else 0

            self.lbl_sum_current.setText(f"총 자산 {int(total_current):,}")
            color = p_col if self.cfg.get("use_change_color") else fc
            self.lbl_sum_current.setForeground(QBrush(QColor(color)))

            self.lbl_sum_profit.setText(
                f"총 손익 {('+' if total_profit >= 0 else '')}{int(total_profit):,}  ({profit_pct:+.2f}%)"
            )
            self.lbl_sum_profit.setForeground(QBrush(QColor(p_col)))

        # 윈도우 크기 조정
        self.card.adjustSize()
        self.resize(self.card.sizeHint())

    def _change_color(self, value) -> str:
        """변동에 따른 색상 반환"""
        if not self.cfg.get("use_change_color", True):
            return self.cfg.get("font_color", "#aaaaaa")
        invert = self.cfg.get("invert_color", False)
        if value > 0:
            return "#4FC3F7" if invert else "#FF5C5C"
        elif value < 0:
            return "#FF5C5C" if invert else "#4FC3F7"
        return "#777777"

    def apply_settings(self, cfg):
        """설정 적용"""
        self.cfg = cfg
        self._apply_card_style()
        self._apply_always_on_top()
        self._rebuild_rows()
        self.update_prices()

    def apply_stocks(self, stocks):
        """종목 적용"""
        self.stocks = [s for s in stocks if s.get("active", True)]
        self._rebuild_rows()
        self.update_prices()

    def mousePressEvent(self, e):
        """마우스 누름"""
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        """마우스 이동"""
        if e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)
            e.accept()

    def eventFilter(self, obj, event):
        """이벤트 필터"""
        if self.table and obj is self.table:
            if event.type() == 2:  # QEvent.MouseButtonPress
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                return True
            elif event.type() == 5:  # QEvent.MouseMove
                if event.buttons() == Qt.LeftButton:
                    self.move(event.globalPos() - self._drag_pos)
                    return True
        return super().eventFilter(obj, event)

    def contextMenuEvent(self, e):
        """우클릭 메뉴"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #1a1a1a; color: #aaaaaa;
                border: 1px solid #333; padding: 4px;
            }
            QMenu::item { padding: 6px 20px; border-radius: 3px; }
            QMenu::item:selected { background: #2a2a2a; color: #cccccc; }
            QMenu::separator { background: #333; height: 1px; margin: 3px 0; }
        """)
        menu.addAction("ℹ  정보", self._open_info)
        menu.addAction("📖  사용법", self._open_usage)
        menu.addAction("📜  오픈소스 라이선스", self._open_license)
        menu.addSeparator()
        menu.addAction("📈  종목설정", self._open_stocks)
        menu.addAction("⚙  환경설정", self._open_settings)
        menu.addSeparator()
        menu.addAction("✕  종료하기", QApplication.quit)
        menu.exec_(e.globalPos())

    def _open_license(self):
        from dialogs.license_dialog import LicenseDialog
        LicenseDialog(self).exec_()

    def _open_info(self):
        from dialogs.info_dialog import InfoDialog
        InfoDialog(self).exec_()

    def _open_usage(self):
        from dialogs.usage_dialog import UsageDialog
        UsageDialog(self).exec_()

    def _open_stocks(self):
        from dialogs.stock_dialog import StockDialog
        dlg = StockDialog(self.data_dir, self.stocks, self)
        dlg.stocks_updated.connect(self.apply_stocks)
        dlg.exec_()

    def _open_settings(self):
        from dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.data_dir, self.cfg, self)
        dlg.settings_updated.connect(self.apply_settings)
        dlg.exec_()
