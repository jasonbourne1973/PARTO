"""
صفحه داشبورد مدیریتی - اصلاح شده بدون مقایسه و رتبه‌بندی
نمایش روند و وضعیت پرونده
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import matplotlib
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from dal.staff_dal import StaffDAL
from services.dashboard_service import DashboardService
from utils.chart_helper import ChartHelper
from utils.logger import get_logger
from utils.persian_date import format_timestamp
from views.pages.analytics_dashboard import AnalyticsDashboardPage

matplotlib.use('QtAgg')
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class DashboardPage(QWidget):
    """
    صفحه داشبورد مدیریتی - بدون مقایسه و رتبه‌بندی
    
    نمایش:
    - تعداد مشاهدات
    - روند مشاهدات
    - نقاط قوت مشاهده‌شده
    - زمینه‌های نیازمند حمایت
    - پیگیری‌های انجام‌شده
    - پیگیری‌های انجام‌نشده
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.dashboard_service = DashboardService()
        self.staff_dal = StaffDAL()
        self.logger = get_logger(self.__class__.__name__)

        self.all_teachers = []
        self.selected_teacher_id = None
        self.dashboard_data = None

        self.setup_ui()
        self.load_teachers()
        self.load_dashboard_data()

        # تایمر به‌روزرسانی خودکار هر ۵ دقیقه
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_dashboard_data)
        self.timer.start(300000)

    def setup_ui(self):
        """راه‌اندازی ساختار کامل رابط کاربری داشبورد"""
        font = QFont("Segoe UI", 10)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        self.setFont(font)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # محتوای داشبورد اصلی داخل تب اول قرار می‌گیرد تا داشبورد تحلیلی
        # نیز بدون شلوغ‌کردن منوی سمت چپ، تب دوم همین صفحه باشد.
        dashboard_main_container = QWidget()
        dashboard_main_layout = QVBoxLayout(dashboard_main_container)
        dashboard_main_layout.setSpacing(0)
        dashboard_main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #0B2E4F;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #08223A;
                width: 8px;
                border-radius: 4px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: #D9C36A;
                border-radius: 4px;
                min-height: 35px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #D9C36A;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        container = QWidget()
        container.setObjectName("MainContainer")
        container.setStyleSheet("QWidget#MainContainer { background-color: #0B2E4F; }")

        self.content_layout = QVBoxLayout(container)
        self.content_layout.setSpacing(14)
        self.content_layout.setContentsMargins(18, 16, 18, 20)

        # ۱. هدر اصلی و نوار ابزار
        self._build_header()

        # ۲. ردیف ۴ کارت کلیدی (بدون رتبه‌بندی)
        self._build_kpi_cards()

        # ۳. بخش میانی: نمودار روند
        self._build_chart_section()

        # ۴. بخش پایینی: پیگیری‌های معوق + آخرین فعالیت‌ها
        self._build_bottom_section()

        scroll.setWidget(container)
        dashboard_main_layout.addWidget(scroll)

        self.dashboard_tabs = QTabWidget()
        self.dashboard_tabs.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.dashboard_tabs.setStyleSheet("""
            QTabWidget::pane {
    color: #111111;
                border: 1px solid #8BC34A;
                border-radius: 8px;
                background-color: #66BB6A;
            }
            QTabBar::tab {
    border: 1px solid #8BC34A;
                background-color: #66BB6A;
                color: #111111;
                padding: 10px 22px;
                margin-left: 2px;
                font-size: 12px;
                font-weight: 700;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
            }
            QTabBar::tab:selected {
    border-color: #F4C542;
                background-color: #8BC34A;
                color: #111111;
            }
            QTabBar::tab:hover {
                background-color: #F4D35E;
                color: #111111;
            }
        """)
        self.dashboard_tabs.addTab(dashboard_main_container, "📊 داشبورد اصلی")

        self.analytics_dashboard_page = AnalyticsDashboardPage(self)
        self.dashboard_tabs.addTab(self.analytics_dashboard_page, "📈 داشبورد تحلیلی")

        main_layout.addWidget(self.dashboard_tabs)

    def _build_header(self):
        """ساخت نوار عنوان و کنترل‌های فیلتر"""
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_card.setStyleSheet("""
            QFrame#HeaderCard {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 12px;
            }
        """)

        layout = QHBoxLayout(header_card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # عنوان
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title_label = QLabel("📊 داشبورد مدیریت و پایش سلامت دانش‌آموزان")
        title_label.setStyleSheet("font-size: 16px; font-weight: 800; color: #F4C542;")

        subtitle_label = QLabel("نمای کلی از وضعیت توانمندی‌ها، مشاهدات و فعالیت‌های جاری مدرسه")
        subtitle_label.setStyleSheet("font-size: 11px; color: #D9C36A;")

        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)
        layout.addLayout(title_box)

        layout.addStretch()

        # فیلتر معلم
        self.teacher_combo = QComboBox()
        self.teacher_combo.setMinimumWidth(170)
        self.teacher_combo.setFixedHeight(36)
        self.teacher_combo.addItem("👨‍🏫 همه معلمان", None)
        self.teacher_combo.currentIndexChanged.connect(self.on_teacher_changed)
        self.teacher_combo.setStyleSheet("""
            QComboBox {
                padding: 4px 12px;
                border: 1px solid #8BC34A;
                border-radius: 8px;
                background-color: #08223A;
                color: #F4C542;
                font-size: 11.5px;
                font-weight: 600;
            }
            QComboBox:hover {
                border-color: #174F78;
                background-color: #0B2E4F;
            }
        """)
        layout.addWidget(self.teacher_combo)

        # دکمه به‌روزرسانی
        self.refresh_btn = QPushButton("🔄 به‌روزرسانی")
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #0B2E4F;
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 11.5px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #08223A;
            }
        """)
        self.refresh_btn.clicked.connect(self.load_dashboard_data)
        layout.addWidget(self.refresh_btn)

        self.content_layout.addWidget(header_card)

    def _build_kpi_cards(self):
        """ساخت ۴ کارت آماری (بدون رتبه‌بندی)"""
        cards_grid = QGridLayout()
        cards_grid.setSpacing(12)

        self.stats_cards = {}

        cards_config = [
            ("دانش‌آموزان", "کل دانش‌آموزان", "👨‍🎓", "#0B2E4F", "#0B2E4F", "پرونده‌های فعال سامانه"),
            ("مشاهدات", "مشاهدات ثبت‌شده", "📝", "#D97706", "#FFFBEB", "رفتاری و آموزشی"),
            ("مداخلات", "مداخلات انجام‌شده", "🛠️", "#7C3AED", "#66BB6A", "راهبردهای بهبود"),
            ("پیگیری باز", "پیگیری‌های باز", "🔔", "#DC2626", "#F4D35E", "نیازمند اقدام فوری"),
        ]

        for i, (key, title, icon, accent_color, bg_light, subtext) in enumerate(cards_config):
            card = self._create_kpi_card(key, title, icon, "0", accent_color, bg_light, subtext)
            row = i // 2
            col = i % 2
            cards_grid.addWidget(card, row, col)
            self.stats_cards[key] = card

        self.content_layout.addLayout(cards_grid)

    def _create_kpi_card(self, key, title, icon, default_value, accent_color, bg_light, subtext):
        """ایجاد کارت آماری"""
        card = QFrame()
        card_id = f"KpiCard_{abs(hash(key)) % 10000}"
        card.setObjectName(card_id)
        card.setStyleSheet(f"""
            QFrame#{card_id} {{
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-top: 3px solid {accent_color};
                border-radius: 12px;
            }}
        """)

        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        info_box = QVBoxLayout()
        info_box.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #F4C542;")

        sub_label = QLabel(subtext)
        sub_label.setStyleSheet("font-size: 10px; color: #D9C36A;")

        info_box.addWidget(title_label)
        info_box.addWidget(sub_label)
        top_row.addLayout(info_box)

        top_row.addStretch()

        icon_frame = QFrame()
        icon_fid = f"IconFrame_{abs(hash(key)) % 10000}"
        icon_frame.setObjectName(icon_fid)
        icon_frame.setFixedSize(40, 40)
        icon_frame.setStyleSheet(f"""
            QFrame#{icon_fid} {{
                background-color: {bg_light};
                border-radius: 10px;
                border: 1px solid {accent_color}30;
            }}
        """)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"font-size: 18px; color: {accent_color}; background: transparent; border: none;")
        icon_layout.addWidget(icon_lbl)

        top_row.addWidget(icon_frame)
        main_layout.addLayout(top_row)

        value_label = QLabel(default_value)
        value_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: 800;
            color: {accent_color};
            padding-top: 4px;
        """)
        main_layout.addWidget(value_label)

        card.value_label = value_label
        return card

    def _build_chart_section(self):
        """ساخت بخش نمودار روند (بدون مقایسه)"""
        chart_card = QFrame()
        chart_card.setObjectName("ChartCard")
        chart_card.setStyleSheet("""
            QFrame#ChartCard {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 12px;
            }
        """)
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(16, 14, 16, 14)
        chart_layout.setSpacing(8)

        # هدر نمودار
        chart_hdr = QHBoxLayout()
        c_title_box = QVBoxLayout()
        c_title_box.setSpacing(2)

        chart_title = QLabel("📈 تحلیل روند ماهانه ثبت مشاهدات")
        chart_title.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #F4C542;")

        chart_sub = QLabel("نمایش تغییرات بر اساس داده‌های ثبت‌شده - بدون مقایسه با دیگران")
        chart_sub.setStyleSheet("font-size: 11px; color: #D9C36A;")

        c_title_box.addWidget(chart_title)
        c_title_box.addWidget(chart_sub)
        chart_hdr.addLayout(c_title_box)
        chart_hdr.addStretch()

        legend_badge = QLabel("🔵 مشاهدات ماهانه")
        legend_badge.setStyleSheet("""
            font-size: 11px;
            font-weight: 600;
            color: #0B2E4F;
            background-color: #0B2E4F;
            padding: 3px 10px;
            border-radius: 12px;
            border: 1px solid #174F78;
        """)
        chart_hdr.addWidget(legend_badge)
        chart_layout.addLayout(chart_hdr)

        # بوم رسم Matplotlib
        self.chart_figure = Figure(figsize=(6, 3), dpi=100, facecolor='#0B2E4F')
        self.chart_canvas = FigureCanvas(self.chart_figure)
        self.chart_canvas.setMinimumHeight(200)
        self.chart_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.chart_canvas.setStyleSheet("background-color: transparent; border: none;")
        chart_layout.addWidget(self.chart_canvas)

        self.content_layout.addWidget(chart_card)

    def _build_bottom_section(self):
        """ساخت بخش پایینی شامل پیگیری‌های معوق و فعالیت‌ها"""
        bot_grid = QGridLayout()
        bot_grid.setSpacing(14)

        # ۱. جدول پیگیری‌های معوق
        reminders_card = QFrame()
        reminders_card.setObjectName("RemindersCard")
        reminders_card.setStyleSheet("""
            QFrame#RemindersCard {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 12px;
            }
        """)
        rem_layout = QVBoxLayout(reminders_card)
        rem_layout.setContentsMargins(16, 14, 16, 14)
        rem_layout.setSpacing(10)

        rem_hdr = QHBoxLayout()
        rem_t_box = QVBoxLayout()
        rem_t_box.setSpacing(2)

        rem_title = QLabel("🔔 پیگیری‌های در انتظار")
        rem_title.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #F4C542;")
        rem_sub = QLabel("مواردی که نیاز به اقدام دارند")
        rem_sub.setStyleSheet("font-size: 11px; color: #D9C36A;")
        rem_t_box.addWidget(rem_title)
        rem_t_box.addWidget(rem_sub)
        rem_hdr.addLayout(rem_t_box)
        rem_hdr.addStretch()

        self.reminder_summary_label = QLabel("✅ همه به موقع")
        self.reminder_summary_label.setStyleSheet("""
            font-size: 11px;
            font-weight: bold;
            color: #66BB6A;
            background-color: #66BB6A;
            padding: 3px 10px;
            border-radius: 12px;
            border: 1px solid #8BC34A;
        """)
        rem_hdr.addWidget(self.reminder_summary_label)
        rem_layout.addLayout(rem_hdr)

        self.reminder_table = QTableWidget()
        self.reminder_table.setColumnCount(4)
        self.reminder_table.setHorizontalHeaderLabels(["نام دانش‌آموز", "نوع مداخله", "تاریخ اقدام", "مسئول پیگیری"])
        self.reminder_table.setShowGrid(False)
        self.reminder_table.setAlternatingRowColors(True)
        self.reminder_table.setMinimumHeight(120)
        self.reminder_table.setStyleSheet(self._get_table_stylesheet())

        header = self.reminder_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.reminder_table.verticalHeader().setVisible(False)
        self.reminder_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.reminder_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        rem_layout.addWidget(self.reminder_table)

        bot_grid.addWidget(reminders_card, 0, 0)

        # ۲. جدول آخرین فعالیت‌ها
        activity_card = QFrame()
        activity_card.setObjectName("ActivityCard")
        activity_card.setStyleSheet("""
            QFrame#ActivityCard {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 12px;
            }
        """)
        act_layout = QVBoxLayout(activity_card)
        act_layout.setContentsMargins(16, 14, 16, 14)
        act_layout.setSpacing(10)

        act_hdr = QHBoxLayout()
        act_t_box = QVBoxLayout()
        act_t_box.setSpacing(2)

        act_title = QLabel("🔄 آخرین فعالیت‌های سامانه")
        act_title.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #F4C542;")
        act_sub = QLabel("گزارش تغییرات و رویدادهای اخیر")
        act_sub.setStyleSheet("font-size: 11px; color: #D9C36A;")
        act_t_box.addWidget(act_title)
        act_t_box.addWidget(act_sub)
        act_hdr.addLayout(act_t_box)
        act_hdr.addStretch()

        act_live = QLabel("🟢 فعال")
        act_live.setStyleSheet("""
            font-size: 11px;
            font-weight: 600;
            color: #66BB6A;
            background-color: #66BB6A;
            padding: 3px 10px;
            border-radius: 12px;
            border: 1px solid #8BC34A;
        """)
        act_hdr.addWidget(act_live)
        act_layout.addLayout(act_hdr)

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels(["زمان", "کاربر", "نوع عملیات", "بخش مرتبط"])
        self.activity_table.setShowGrid(False)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setMinimumHeight(120)
        self.activity_table.setStyleSheet(self._get_table_stylesheet())

        act_header = self.activity_table.horizontalHeader()
        act_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        act_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        act_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        act_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        act_header.setDefaultAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.activity_table.verticalHeader().setVisible(False)
        self.activity_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.activity_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        act_layout.addWidget(self.activity_table)

        bot_grid.addWidget(activity_card, 0, 1)

        self.content_layout.addLayout(bot_grid)

    def _get_table_stylesheet(self):
        """استایل جداول"""
        return """
            QTableWidget {
    gridline-color: #D9C36A;
                background-color: #0B2E4F;
                alternate-background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 8px;
                font-size: 11.5px;
                color: #F4C542;
                outline: 0;
            }
            QTableWidget::item {
    color: #F4C542;
    background-color: #0B2E4F;
                padding: 6px 10px;
                border-bottom: 1px solid #D9C36A;
            }
            QTableWidget::item:selected {
                background-color: #66BB6A;
                color: #F4C542;
            }
            QHeaderView::section {
                background-color: #66BB6A;
                color: #111111;
                padding: 6px 10px;
                border: 1px solid #D9C36A;
                border-bottom: 1px solid #D9C36A;
                font-weight: 700;
                font-size: 11px;
            }
        """

    def load_teachers(self):
        """بارگذاری لیست معلمان"""
        try:
            all_staff = self.staff_dal.get_all()
            self.all_teachers = [s for s in all_staff if s.role == "teacher"]
            self.teacher_combo.blockSignals(True)
            self.teacher_combo.clear()
            self.teacher_combo.addItem("👨‍🏫 همه معلمان", None)
            for teacher in self.all_teachers:
                self.teacher_combo.addItem(f"معلم: {teacher.full_name}", teacher.id)
            self.teacher_combo.blockSignals(False)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری معلمان: {e}")

    def on_teacher_changed(self, index):
        self.selected_teacher_id = self.teacher_combo.currentData()
        self.load_dashboard_data()

    def load_dashboard_data(self):
        """بارگذاری داده‌های داشبورد"""
        try:
            self.dashboard_data = self.dashboard_service.get_dashboard_data(
                teacher_id=self.selected_teacher_id
            )

            if not self.dashboard_data:
                return

            stats = self.dashboard_data.get('general_stats', {})

            # ۱. به‌روزرسانی کارت‌ها
            self.stats_cards["دانش‌آموزان"].value_label.setText(str(stats.get('students_count', 0)))
            self.stats_cards["مشاهدات"].value_label.setText(str(stats.get('observations_count', 0)))
            self.stats_cards["مداخلات"].value_label.setText(str(stats.get('interventions_count', 0)))
            self.stats_cards["پیگیری باز"].value_label.setText(str(stats.get('pending_followups', 0)))

            # ۲. رسم نمودار روند
            trend_data = self.dashboard_data.get('trend_data', {})
            self._draw_chart(trend_data)

            # ۳. به‌روزرسانی جدول یادآوری‌ها
            reminders = self.dashboard_data.get('reminders', {})
            self._load_reminders(reminders)

            # ۴. به‌روزرسانی جدول فعالیت‌ها
            activities = self.dashboard_data.get('recent_activities', [])
            self._load_recent_activities(activities)

        except Exception as e:
            self.logger.error(f"خطا در بارگذاری داده‌های داشبورد: {e}")

    def _draw_chart(self, trend_data):
        """رسم نمودار روند - بدون مقایسه"""
        self.chart_figure.clear()
        ax = self.chart_figure.add_subplot(111)

        self.chart_figure.patch.set_facecolor('#0B2E4F')
        ax.set_facecolor('#0B2E4F')

        labels = trend_data.get('labels', [])
        counts = trend_data.get('counts', [])
        positive = trend_data.get('positive', [])
        negative = trend_data.get('negative', [])

        if not labels or sum(counts) == 0:
            ax.text(0.5, 0.5, 'داده‌ای برای نمایش وجود ندارد',
                    ha='center', va='center', fontsize=11, color='#D9C36A')
            ax.axis('off')
            self.chart_canvas.draw()
            return

        x = np.arange(len(labels))
        width = 0.35

        # استفاده از ChartHelper برای نمایش فارسی
        labels_fa = [ChartHelper._farsi(str(label)) for label in labels]

        # رسم میله‌ها
        ax.bar(x - width/2, positive, width, label='مثبت', 
               color='#8BC34A', edgecolor='none', alpha=0.8)
        ax.bar(x + width/2, negative, width, label='منفی',
               color='#C62828', edgecolor='none', alpha=0.8)

        ax.set_xticks(x)
        ax.set_xticklabels(labels_fa, fontsize=9, color='#475569', fontweight='600')

        max_val = max(counts) if counts else 10
        ax.set_ylim(0, max_val * 1.3)
        ax.tick_params(axis='both', which='both', length=0, labelsize=9, colors='#D9C36A')

        ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#D9C36A', zorder=0)
        ax.xaxis.grid(False)

        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.legend(loc='upper right', fontsize=9, frameon=True,
                  facecolor='#0B2E4F', edgecolor='#D9C36A', framealpha=0.9)

        self.chart_figure.subplots_adjust(left=0.08, right=0.96, top=0.92, bottom=0.18)
        self.chart_canvas.draw()

    def _load_reminders(self, reminders):
        """بارگذاری جدول پیگیری‌ها"""
        try:
            if reminders.get('has_reminder', False):
                count = reminders.get('total_pending', 0)
                overdue = reminders.get('overdue_count', 0)
                txt = f"⚠️ {count} مورد در انتظار"
                if overdue > 0:
                    txt += f" | 🔴 {overdue} معوق"
                self.reminder_summary_label.setText(txt)
                self.reminder_summary_label.setStyleSheet("""
                    font-size: 11px;
                    font-weight: bold;
                    color: #DC2626;
                    background-color: #F4D35E;
                    padding: 3px 10px;
                    border-radius: 12px;
                    border: 1px solid #C62828;
                """)
            else:
                self.reminder_summary_label.setText("✅ همه به موقع")
                self.reminder_summary_label.setStyleSheet("""
                    font-size: 11px;
                    font-weight: bold;
                    color: #66BB6A;
                    background-color: #66BB6A;
                    padding: 3px 10px;
                    border-radius: 12px;
                    border: 1px solid #8BC34A;
                """)

            overdue_list = reminders.get('overdue_list', [])
            self.reminder_table.setRowCount(len(overdue_list) if overdue_list else 1)

            if overdue_list:
                for row, item in enumerate(overdue_list[:6]):
                    self.reminder_table.setItem(row, 0, QTableWidgetItem(f"👤 {item.get('student_name', 'نامشخص')}"))
                    self.reminder_table.setItem(row, 1, QTableWidgetItem(item.get('intervention_type', 'نامشخص')))
                    self.reminder_table.setItem(row, 2, QTableWidgetItem(f"📅 {item.get('next_action_date', '')}"))
                    self.reminder_table.setItem(row, 3, QTableWidgetItem(f"👨‍🏫 {item.get('staff_name', 'نامشخص')}"))
                    self.reminder_table.setRowHeight(row, 32)
            else:
                empty_item = QTableWidgetItem("🎉 هیچ پیگیری معوق یا نیازمند اقدامی وجود ندارد.")
                empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_item.setForeground(QColor("#66BB6A"))
                self.reminder_table.setItem(0, 0, empty_item)
                self.reminder_table.setSpan(0, 0, 1, 4)
                self.reminder_table.setRowHeight(0, 40)

        except Exception as e:
            self.logger.error(f"خطا در بارگذاری یادآوری‌ها: {e}")

    def _load_recent_activities(self, logs):
        """بارگذاری فعالیت‌های اخیر"""
        try:
            action_map = {
                'create': ('➕ ایجاد', '#66BB6A'),
                'edit': ('✏️ ویرایش', '#0B2E4F'),
                'delete_soft': ('🗑️ حذف', '#DC2626'),
                'delete': ('🗑️ حذف دائم', '#991B1B'),
                'restore': ('↩️ بازیابی', '#66BB6A'),
                'login_success': ('🔓 ورود', '#7C3AED'),
                'logout': ('🚪 خروج', '#D9C36A'),
                'export': ('📤 خروجی', '#D97706'),
            }

            entity_map = {
                'student': 'دانش‌آموز',
                'observation': 'مشاهده',
                'intervention': 'مداخله',
                'followup': 'پیگیری',
                'staff': 'کادر مدرسه',
                'academic_year': 'سال تحصیلی',
                'auth': 'امنیت و ورود',
                'user': 'کاربر سامانه',
                'notification': 'اعلان',
                'notifications': 'اعلان',
            }

            self.activity_table.setRowCount(min(len(logs), 6))

            for row, log in enumerate(logs[:6]):
                # created_at از «CURRENT_TIMESTAMP» می‌آید یعنی میلادی و UTC.
                # بدون تبدیل، کاربر در ایران ساعت را ۳ ساعت و ۳۰ دقیقه عقب‌تر
                # از زمان واقعی و تاریخ را میلادی می‌دید (و بین ۰۰:۰۰ تا ۰۳:۳۰
                # تهران، روز هم یک روز عقب‌تر بود). format_timestamp هر دو را
                # به شمسیِ زمان محلی می‌برد.
                self.activity_table.setItem(
                    row, 0,
                    QTableWidgetItem(format_timestamp(log.get('created_at')))
                )
                self.activity_table.setItem(row, 1, QTableWidgetItem(f"👤 {log.get('user_name', 'سیستم')}"))

                act_raw = log.get('action', '')
                act_label, act_color = action_map.get(act_raw, (act_raw, '#475569'))
                a_item = QTableWidgetItem(act_label)
                a_item.setForeground(QColor(act_color))
                self.activity_table.setItem(row, 2, a_item)

                ent_raw = log.get('entity_type', '')
                ent_label = entity_map.get(ent_raw, ent_raw)
                self.activity_table.setItem(row, 3, QTableWidgetItem(ent_label))
                self.activity_table.setRowHeight(row, 32)

        except Exception as e:
            self.logger.error(f"خطا در بارگذاری فعالیت‌های اخیر: {e}")