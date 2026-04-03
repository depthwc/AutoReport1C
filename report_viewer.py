import sys
import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QDateTime, QPointF
from PySide6.QtGui import QCursor, QPainter, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QFrame,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QSpinBox, QMessageBox, QComboBox, QToolTip
)
from PySide6.QtCharts import (
        QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis, QCategoryAxis,
        QLineSeries, QDateTimeAxis, QScatterSeries
)

class NumericTableItem(QTableWidgetItem):
    def __init__(self, val_str, val_raw=None):
        super().__init__(val_str)
        try:
            clean_str = str(val_raw).replace(' ', '').replace(',', '')
            self.val_num = float(clean_str)
        except (ValueError, TypeError):
            self.val_num = val_raw

    def __lt__(self, other):
        if isinstance(other, NumericTableItem):
            if isinstance(self.val_num, (int, float)) and isinstance(other.val_num, (int, float)):
                return self.val_num < other.val_num
            return str(self.val_num) < str(other.val_num)
        return super().__lt__(other)

import report_fun

STYLESHEET = """
QMainWindow {
    background: #f2f5f7;
}
QFrame#Card {
    background: #ffffff;
    border: 1px solid #dde5ec;
    border-radius: 14px;
}
QLabel#Title {
    color: #000000;
    font-size: 20px;
    font-weight: 800;
}
QLabel#Section {
    color: #000000;
    font-size: 16px;
    font-weight: 800;
}
QLabel {
    color: #000000;
    font-weight: 500;
    font-size: 14px;
}
QLabel#SummaryData {
    color: #0f8b8d;
    font-weight: bold;
    font-size: 15px;
}
QToolTip {
    background-color: #1f3b4d;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 8px;
    border: 1px solid #ffffff;
    border-radius: 6px;
}
QLineEdit, QListWidget, QTableWidget, QSpinBox, QComboBox {
    background: #fcfdff;
    border: 1px solid #cbd6e2;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 14px;
    color: #000000;
    selection-background-color: #0f8b8d;
    selection-color: #ffffff;
    min-height: 24px;
}
QComboBox::drop-down {
    border: none;
    width: 25px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #000000;
    selection-background-color: #0f8b8d;
    selection-color: #ffffff;
    border: 1px solid #cbd6e2;
}
QSpinBox {
    min-width: 60px;
}
QTabBar::tab {
    background: #e7eef3;
    color: #000000;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0f8b8d;
}
QPushButton {
    border: none;
    border-radius: 10px;
    padding: 9px 14px;
    font-size: 14px;
    font-weight: 700;
}
QPushButton#Primary {
    background: #0f8b8d;
    color: #ffffff;
}
QPushButton#Secondary {
    background: #e7eef3;
    color: #000000;
}
QTableWidget::item {
    padding: 5px;
}
"""

from ai_agent import AIChatWorker

class ReportViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoReport1C Viewer")
        self.resize(1400, 900)
        self.setStyleSheet(STYLESHEET)
        
        self.ai_messages = [
            {"role": "system", "content": "You are AI assistant for application called AutoReport. You will give informations about data. You will use tools when needed. You will keep things short and accuret. You use Uzbek language, but if user messages in other language you will switch to that language"}
        ]
        
        self.bar_labels = []
        self.bar_full_names = []
        self.bar_quantities = []
        self.bar_sales = []

        self.line_dates_str = []
        self.line_sales = []
        self.line_quants = []
        
        self._build_ui()
        self._load_files()
        self._load_history_chart()

    def _card(self) -> QFrame:
        c = QFrame()
        c.setObjectName("Card")
        return c

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ================= LEFT: AI CHAT =================
        left_panel = self._card()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        ai_title = QLabel("AI Agent Yordamchisi")
        ai_title.setObjectName("Section")
        
        self.chat_list = QListWidget()
        self.chat_list.setWordWrap(True)
        
        chat_input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Savolingizni yozing...")
        self.chat_input.returnPressed.connect(self.send_to_ai)
        self.send_btn = QPushButton("Yuborish")
        self.send_btn.setObjectName("Primary")
        self.send_btn.clicked.connect(self.send_to_ai)
        
        chat_input_layout.addWidget(self.chat_input)
        chat_input_layout.addWidget(self.send_btn)
        
        left_layout.addWidget(ai_title)
        left_layout.addWidget(self.chat_list)
        left_layout.addLayout(chat_input_layout)

        # ================= MIDDLE: DASHBOARD =================
        middle_panel = QVBoxLayout()
        middle_panel.setSpacing(10)
        
        # --- Summary Card ---
        self.summary_card = self._card()
        self.summary_card.setVisible(False)
        self.summary_layout = QHBoxLayout(self.summary_card)
        self.summary_layout.setContentsMargins(15, 10, 15, 10)
        
        self.sum_cashier_lbl = QLabel()
        self.sum_cashier_lbl.setObjectName("SummaryData")
        self.sum_humo_lbl = QLabel()
        self.sum_humo_lbl.setObjectName("SummaryData")
        self.sum_uzcard_lbl = QLabel()
        self.sum_uzcard_lbl.setObjectName("SummaryData")
        self.sum_naqd_lbl = QLabel()
        self.sum_naqd_lbl.setObjectName("SummaryData")
        self.sum_total_sales_lbl = QLabel()
        self.sum_total_sales_lbl.setObjectName("SummaryData")
        self.sum_total_qty_lbl = QLabel()
        self.sum_total_qty_lbl.setObjectName("SummaryData")

        self.summary_layout.addWidget(QLabel("Kassir: "))
        self.summary_layout.addWidget(self.sum_cashier_lbl)
        self.summary_layout.addStretch()
        self.summary_layout.addWidget(QLabel("HUMO: "))
        self.summary_layout.addWidget(self.sum_humo_lbl)
        self.summary_layout.addStretch()
        self.summary_layout.addWidget(QLabel("UZCARD: "))
        self.summary_layout.addWidget(self.sum_uzcard_lbl)
        self.summary_layout.addStretch()
        self.summary_layout.addWidget(QLabel("NAQD: "))
        self.summary_layout.addWidget(self.sum_naqd_lbl)
        self.summary_layout.addStretch()
        self.summary_layout.addWidget(QLabel("1C Qty: "))
        self.summary_layout.addWidget(self.sum_total_qty_lbl)
        self.summary_layout.addStretch()
        self.summary_layout.addWidget(QLabel("1C Total: "))
        self.summary_layout.addWidget(self.sum_total_sales_lbl)
        
        middle_panel.addWidget(self.summary_card)

        # --- Controls ---
        ctrl_card = self._card()
        ctrl_card.setMaximumHeight(70)
        ctrl_layout = QHBoxLayout(ctrl_card)
        ctrl_layout.addWidget(QLabel("Chart Sorting:"))
        self.chart_sort_combo = QComboBox()
        self.chart_sort_combo.addItems(["Sotuv (Sales)", "Miqdor (Quantity)"])
        self.chart_sort_combo.currentTextChanged.connect(self._update_bar_chart)
        ctrl_layout.addWidget(self.chart_sort_combo)
        
        ctrl_layout.addWidget(QLabel("Top N:"))
        
        self.btn_minus = QPushButton("-")
        self.btn_minus.setObjectName("Secondary")
        self.btn_minus.setFixedWidth(32)
        
        self.chart_limit_spin = QSpinBox()
        self.chart_limit_spin.setRange(1, 100)
        self.chart_limit_spin.setValue(10)
        self.chart_limit_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.chart_limit_spin.setAlignment(Qt.AlignCenter)
        self.chart_limit_spin.setFixedWidth(60)
        self.chart_limit_spin.valueChanged.connect(self._update_bar_chart)
        
        self.btn_plus = QPushButton("+")
        self.btn_plus.setObjectName("Secondary")
        self.btn_plus.setFixedWidth(32)
        
        self.btn_minus.clicked.connect(lambda: self.chart_limit_spin.setValue(self.chart_limit_spin.value() - 1))
        self.btn_plus.clicked.connect(lambda: self.chart_limit_spin.setValue(self.chart_limit_spin.value() + 1))
        
        ctrl_layout.addWidget(self.btn_minus)
        ctrl_layout.addWidget(self.chart_limit_spin)
        ctrl_layout.addWidget(self.btn_plus)
        ctrl_layout.addStretch()
        
        middle_panel.addWidget(ctrl_card)

        # CHARTS Card (placing charts side-by-side)
        charts_card = self._card()
        charts_layout = QVBoxLayout(charts_card)
        charts_layout.setContentsMargins(15, 10, 15, 15)
        
        charts_row = QHBoxLayout()
        
        # Left side - Native Qt Bar Chart
        bar_vbox = QVBoxLayout()
        self.bar_head_lbl = QLabel("Top Mahsulotlar")
        self.bar_head_lbl.setObjectName("Section")
        self.bar_head_lbl.setAlignment(Qt.AlignCenter)
        bar_vbox.addWidget(self.bar_head_lbl)
        
        self.bar_chart_view = QChartView()
        self.bar_chart_view.setRenderHint(QPainter.Antialiasing)
        self.bar_scroll = QScrollArea()
        self.bar_scroll.setWidgetResizable(True)
        self.bar_scroll.setWidget(self.bar_chart_view)
        
        # Forward horizontal scroll
        self.bar_scroll.wheelEvent = lambda event: self._custom_scroll(event, self.bar_scroll)
        bar_vbox.addWidget(self.bar_scroll)
        charts_row.addLayout(bar_vbox, 1)
        
        # Right side - Native Qt Line Chart
        line_vbox = QVBoxLayout()
        self.line_head_lbl = QLabel("Oylik Kassa Sotuvlari (1C_Total_Sales)")
        self.line_head_lbl.setObjectName("Section")
        self.line_head_lbl.setAlignment(Qt.AlignCenter)
        line_vbox.addWidget(self.line_head_lbl)
        
        self.line_chart_view = QChartView()
        self.line_chart_view.setRenderHint(QPainter.Antialiasing)
        self.line_scroll = QScrollArea()
        self.line_scroll.setWidgetResizable(True)
        self.line_scroll.setWidget(self.line_chart_view)
        
        self.line_scroll.wheelEvent = lambda event: self._custom_scroll(event, self.line_scroll)
        line_vbox.addWidget(self.line_scroll)
        charts_row.addLayout(line_vbox, 1)
        
        charts_layout.addLayout(charts_row)
        middle_panel.addWidget(charts_card, 5)
        
        # --- TABLE ---
        table_card = self._card()
        table_layout = QVBoxLayout(table_card)
        table_title = QLabel("Batafsil ma'lumot (Jadval)")
        table_title.setObjectName("Section")
        self.table_widget = QTableWidget()
        self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        table_layout.addWidget(table_title)
        table_layout.addWidget(self.table_widget)
        
        middle_panel.addWidget(table_card, 3)

        # ================= RIGHT: FILE NAVIGATOR =================
        right_panel = self._card()
        right_panel.setFixedWidth(250)
        right_layout = QVBoxLayout(right_panel)
        
        files_title = QLabel("Ma'lumotlar ombori")
        files_title.setObjectName("Section")
        
        self.tabs = QTabWidget()
        self.day_list = QListWidget()
        self.month_list = QListWidget()
        self.year_list = QListWidget()
        
        self.day_list.itemClicked.connect(lambda it: self.load_data("day", it.text()))
        self.month_list.itemClicked.connect(lambda it: self.load_data("month", it.text()))
        self.year_list.itemClicked.connect(lambda it: self.load_data("year", it.text()))
        
        self.tabs.addTab(self.day_list, "Kunlik")
        self.tabs.addTab(self.month_list, "Oylik")
        self.tabs.addTab(self.year_list, "Yillik")
        
        refresh_btn = QPushButton("Yangilash")
        refresh_btn.setObjectName("Secondary")
        refresh_btn.clicked.connect(self._load_files)
        
        right_layout.addWidget(files_title)
        right_layout.addWidget(self.tabs)
        right_layout.addWidget(refresh_btn)

        main_layout.addWidget(left_panel)
        main_layout.addLayout(middle_panel)
        main_layout.addWidget(right_panel)

    def _load_files(self):
        self.day_list.clear()
        self.month_list.clear()
        self.year_list.clear()
        base = Path("clean_data")
        if (base / "day").exists():
            for f in sorted((base / "day").glob("*.xlsx"), reverse=True):
                self.day_list.addItem(f.name)
        if (base / "month").exists():
            for f in sorted((base / "month").glob("*.xlsx"), reverse=True):
                self.month_list.addItem(f.name)
        if (base / "year").exists():
            for f in sorted((base / "year").glob("*.xlsx"), reverse=True):
                self.year_list.addItem(f.name)

    def _custom_scroll(self, event, scroll_area):
        hbar = scroll_area.horizontalScrollBar()
        delta = event.angleDelta().y()
        if delta != 0:
            hbar.setValue(hbar.value() - delta)

    def _format_money(self, val):
        try:
            return f"{float(val):,.0f}".replace(",", " ")
        except:
            return str(val)

    def _fetch_daily_summary(self, filename):
        date_str = filename.replace(".xlsx", "")
        try:
            dt_obj = datetime.strptime(date_str, "%d.%m.%Y")
            dash_date = dt_obj.strftime("%Y-%m-%d")
        except ValueError:
            dash_date = date_str

        historical_path = Path("cash_register/daily_info.xlsx")
        found = False
        if historical_path.exists():
            try:
                hist_df = pd.read_excel(historical_path)
                match = hist_df[hist_df['Date and Time'].astype(str).str.contains(dash_date, na=False)]
                if not match.empty:
                    row = match.iloc[-1]
                    self.sum_cashier_lbl.setText(str(row.get("Cashier", "N/A")))
                    self.sum_humo_lbl.setText(self._format_money(row.get("HUMO", 0)))
                    self.sum_uzcard_lbl.setText(self._format_money(row.get("UZCARD", 0)))
                    self.sum_naqd_lbl.setText(self._format_money(row.get("NAQD", 0)))
                    self.sum_total_sales_lbl.setText(self._format_money(row.get("1C_Total_Sales", 0)))
                    self.sum_total_qty_lbl.setText(self._format_money(row.get("1C_Quantity_Sold", 0)))
                    found = True
            except Exception as e:
                print(f"Error fetching daily summary: {e}")
        self.summary_card.setVisible(found)

    def load_data(self, period, filename):
        """
        Loads an Excel file corresponding to a selected period ('day', 'month', 'year')
        and filename. Once loaded, it updates the visual charts and table to reflect
        the newly loaded document.
        """
        path = f"clean_data/{period}/{filename}"
        if not os.path.exists(path): return
        try:
            self.current_df = pd.read_excel(path)
            if period == 'day':
                self._fetch_daily_summary(filename)
            else:
                self.summary_card.setVisible(False)
            self._update_bar_chart()
            self._update_table()
        except Exception as e:
            QMessageBox.warning(self, "Xatolik", f"Faylni o'qishda xatolik: {e}")

    # ===== QtCharts: BAR CHART =====
    def _update_bar_chart(self):
        """
        Builds and displays a bar chart for the Top N products.
        It reads the current dropdown selection to decide whether to sort by Sales or Quantity.
        """
        if self.current_df is None or self.current_df.empty:
            return
            
        sort_by = "sales" if "Sales" in self.chart_sort_combo.currentText() else "quantity"
        limit = self.chart_limit_spin.value()
        
        self.bar_head_lbl.setText(f"Top {limit} Mahsulot ({self.chart_sort_combo.currentText()})")
        
        top_df = report_fun.get_top_products(self.current_df, sort_by=sort_by, head=limit, ascending=False)
        
        if top_df.empty:
            self.bar_chart_view.setChart(QChart())
            return
            
        self.bar_labels = top_df['code'].astype(str).tolist()
        self.bar_full_names = top_df['product_name'].astype(str).tolist()
        self.bar_quantities = top_df['quantity'].tolist() if 'quantity' in top_df.columns else []
        self.bar_sales = top_df['sales'].tolist() if 'sales' in top_df.columns else []
        

        values = top_df[sort_by].tolist()
        
        series = QBarSeries()
        bar_set = QBarSet("Value")
        bar_set.setColor("#0f8b8d")        # Fill color
        bar_set.setBorderColor("#105f59")  # Outline color
        
        for val in values:
            bar_set.append(val)
            
        series.append(bar_set)
        
        bar_set.hovered.connect(self._on_bar_hovered)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.SeriesAnimations) 
        chart.legend().hide()
        
        axis_x = QBarCategoryAxis()
        axis_x.append(self.bar_labels)
        
        labels_font = QFont()
        labels_font.setPointSize(8)
        axis_x.setLabelsFont(labels_font)
        axis_x.setLabelsAngle(-45)
        
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QCategoryAxis()
        axis_y.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
        nice_max = 10
        if values:
            m = max(values)
            if m > 0:
                mag = 10 ** max(0, len(str(int(m))) - 1)
                nice_max = ((int(m) // mag) + 1) * mag
        
        step = nice_max / 4.0
        for i in range(5):
            val = round(i * step)
            label = self._format_money(val) + (" " * i)
            axis_y.append(label, val)
            
        axis_y.setMin(0)
        axis_y.setMax(nice_max)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        
        chart.setBackgroundRoundness(0)
        self.bar_chart_view.setChart(chart)
        
        # Enable horizontal scrolling if many items
        min_width_px = max(600, len(self.bar_labels) * 80)
        self.bar_chart_view.setMinimumWidth(min_width_px)

    def _on_bar_hovered(self, status, index):
        if status:
            if index >= 0 and index < len(self.bar_labels):
                lbl = self.bar_labels[index]
                full_name = self.bar_full_names[index]
                q = self.bar_quantities[index] if index < len(self.bar_quantities) else 0
                s = self.bar_sales[index] if index < len(self.bar_sales) else 0
                text = f"Mahsulot: {full_name}\nKOD: {lbl}\nSotuv: {self._format_money(s)} so'm\nMiqdor: {self._format_money(q)} dona"
                QToolTip.showText(QCursor.pos(), text)
        else:
            QToolTip.hideText()

    # ===== QtCharts: LINE CHART =====
    def _load_history_chart(self):
        """
        Reads the historical summary excel file (daily_info.xlsx) and plots a line chart 
        showing the overall sales trend over multiple days/months.
        """
        historical_path = Path("cash_register/daily_info.xlsx")
        
        chart = QChart()
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().hide()
        
        if not historical_path.exists():
            self.line_chart_view.setChart(chart)
            return
            
        try:
            hist_df = pd.read_excel(historical_path)
            
            if 'Date and Time' in hist_df.columns and '1C_Total_Sales' in hist_df.columns:
                self.line_dates_str = pd.to_datetime(hist_df['Date and Time']).dt.strftime('%Y-%m-%d').tolist()
                
                self.line_sales = hist_df['1C_Total_Sales'].fillna(0).tolist()
                self.line_quants = hist_df['1C_Quantity_Sold'].fillna(0).tolist() if '1C_Quantity_Sold' in hist_df.columns else []
                
                if len(self.line_dates_str) > 0:
                    series = QLineSeries() 
                    
                    scatter = QScatterSeries()
                    scatter.setColor("#c44536")
                    scatter.setMarkerSize(8)
                    series.setColor("#c44536")
                    
                    min_val, max_val = float('inf'), float('-inf')
                    
                    for i, (date_str, sale) in enumerate(zip(self.line_dates_str, self.line_sales)):
                        if pd.isna(sale): sale = 0

                        min_val = min(min_val, sale)
                        max_val = max(max_val, sale)
                        
                        dt = QDateTime.fromString(date_str, "yyyy-MM-dd")
                        msecs = dt.toMSecsSinceEpoch()
                        
                        series.append(msecs, sale)
                        scatter.append(msecs, sale)
                    
                    chart.addSeries(series)
                    chart.addSeries(scatter)
                    
                    scatter.hovered.connect(self._on_line_hovered)
                    
                    axis_x = QDateTimeAxis()
                    axis_x.setFormat("yyyy-MM-dd")
                    labels_font = QFont()
                    labels_font.setPointSize(8)
                    axis_x.setLabelsFont(labels_font)
                    axis_x.setLabelsAngle(-45)
                    min_dt = QDateTime.fromString(self.line_dates_str[0], "yyyy-MM-dd")
                    max_dt = QDateTime.fromString(self.line_dates_str[-1], "yyyy-MM-dd")
                    axis_x.setMin(min_dt.addDays(-1))
                    axis_x.setMax(max_dt.addDays(1))
                    if len(self.line_dates_str) > 20:
                        axis_x.setTickCount(20)
                    else:
                        axis_x.setTickCount(len(self.line_dates_str))
                    
                    chart.addAxis(axis_x, Qt.AlignBottom)
                    series.attachAxis(axis_x)
                    scatter.attachAxis(axis_x)
                    
                    axis_y = QCategoryAxis()
                    axis_y.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
                    if min_val != float('inf'):
                        import math
                        range_val = max(1, max_val - min_val)
                        magnitude = 10 ** math.floor(math.log10(range_val / 4.0)) if range_val > 0 else 1
                        fraction = (range_val / 4.0) / magnitude
                        if fraction >= 5: step = 5 * magnitude
                        elif fraction >= 2: step = 2 * magnitude
                        else: step = magnitude
                        
                        lower_bound = math.floor((min_val * 0.95) / step) * step
                        lower_bound = max(0, lower_bound)
                        upper_bound = math.ceil((max_val * 1.05) / step) * step
                        
                        axis_y.setMin(lower_bound)
                        axis_y.setMax(upper_bound)
                        
                        ticks = int((upper_bound - lower_bound) / step) + 1
                        for i in range(ticks):
                            val = lower_bound + i * step
                            label = self._format_money(val) + (" " * i)
                            axis_y.append(label, val)
                            
                    chart.addAxis(axis_y, Qt.AlignLeft)
                    series.attachAxis(axis_y)
                    scatter.attachAxis(axis_y)
                    
                    chart.setBackgroundRoundness(0)
                    
                    min_width_px = max(600, len(self.line_dates_str) * 45)
                    self.line_chart_view.setMinimumWidth(min_width_px)
        except Exception as e:
            print(f"Error loading history chart: {e}")
            
        self.line_chart_view.setChart(chart)

    def _on_line_hovered(self, point, state):
        if state:
            closest_i = 0
            closest_dist = float('inf')
            target_ms = point.x()
            
            for i, date_str in enumerate(self.line_dates_str):
                dt = QDateTime.fromString(date_str, "yyyy-MM-dd")
                ms = dt.toMSecsSinceEpoch()
                dist = abs(ms - target_ms)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_i = i
            
            s = self.line_sales[closest_i] if closest_i < len(self.line_sales) else 0
            q = self.line_quants[closest_i] if closest_i < len(self.line_quants) else 0
            date_label = self.line_dates_str[closest_i]
            
            text = f"Sana: {date_label}\nSotuv: {self._format_money(s)} so'm\nMiqdor: {self._format_money(q)} dona"
            QToolTip.showText(QCursor.pos(), text)
        else:
            QToolTip.hideText()

    def _update_table(self):
        if self.current_df is None or self.current_df.empty:
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            return
            
        table_df = report_fun.get_table_info(self.current_df)
        
        self.table_widget.setSortingEnabled(False)
        self.table_widget.setRowCount(table_df.shape[0])
        self.table_widget.setColumnCount(table_df.shape[1])
        self.table_widget.setHorizontalHeaderLabels(table_df.columns)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        for row in range(table_df.shape[0]):
            for col in range(table_df.shape[1]):
                val = table_df.iat[row, col]
                if isinstance(val, (int, float)):
                    val_str = self._format_money(val)
                    item = NumericTableItem(val_str, float(val))
                else:
                    val_str = str(val)
                    item = NumericTableItem(val_str, val_str)
                self.table_widget.setItem(row, col, item)
        self.table_widget.setSortingEnabled(True)

    def send_to_ai(self):
        text = self.chat_input.text().strip()
        if not text:
            return
            
        self.ai_messages.append({"role": "user", "content": text})
        self.chat_list.addItem(f"👤 Siz: {text}")
        self.chat_input.clear()
        self.send_btn.setEnabled(False)
        self.chat_list.addItem("🤖 AI: (O'ylamoqda...)")
        self.chat_list.scrollToBottom()
        
        #self.ai_messages[0]["content"] = """"""
        
        self.worker = AIChatWorker(self.ai_messages)
        self.worker.response_ready.connect(self._ai_response)
        self.worker.error_occurred.connect(self._ai_error)
        self.worker.start()

    def _ai_response(self, text):
        self.ai_messages.append({"role": "assistant", "content": text})
        self.chat_list.takeItem(self.chat_list.count()-1)
        self.chat_list.addItem(f"🤖 AI: {text}")
        self.chat_list.scrollToBottom()
        self.send_btn.setEnabled(True)

    def _ai_error(self, err_msg):
        self.chat_list.takeItem(self.chat_list.count()-1)
        self.chat_list.addItem(f"❌ Xato: {err_msg}")
        self.chat_list.scrollToBottom()
        self.send_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = ReportViewer()
    viewer.showMaximized()
    sys.exit(app.exec())
