"""
صفحه داشبورد تحلیلی برای مدیر و معاون پرورشی
نمایش شاخص‌های تحلیلی، الگوهای رفتاری و دانش‌آموزان نیازمند توجه
بدون مقایسه و رتبه‌بندی
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QGridLayout, QScrollArea, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QSizePolicy, QTabWidget, QGroupBox, QTextEdit,
    QProgressBar, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont

from services.dashboard_service import DashboardService
from dal.academic_year_dal import AcademicYearDAL
from dal.staff_dal import StaffDAL
from utils.chart_helper import ChartHelper
from utils.logger import get_logger

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np


class AnalyticsDashboardPage(QWidget):
    """
    صفحه داشبورد تحلیلی - بدون مقایسه و رتبه‌بندی
    
    نمایش:
    - توزیع مشاهدات (مثبت/منفی/خنثی)
    - توزیع دانش‌آموزان بر اساس پایه
    - شایستگی‌های پرکاربرد
    - وضعیت مداخلات و پیگیری‌ها
    - دانش‌آموزان نیازمند توجه
    - روند تغییرات
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.dashboard_service = DashboardService()
        self.academic_year_dal = AcademicYearDAL()
        self.staff_dal = StaffDAL()
        self.logger = get_logger(self.__class__.__name__)
        
        self.current_teacher_id = None
        self.current_year_id = None
        self.dashboard_data = None
        
        self.setup_ui()
        self.load_academic_years()
        self.load_teachers()
        self.load_dashboard_data()
        
        # تایمر به‌روزرسانی خودکار هر ۵ دقیقه
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_dashboard_data)
        self.timer.start(300000)
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # ===== اسکرول اصلی =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #08223A;
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
        container.setStyleSheet("background-color: #08223A;")
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setSpacing(14)
        self.content_layout.setContentsMargins(18, 16, 18, 20)
        
        # ===== ۱. هدر و نوار ابزار =====
        self._build_header()
        
        # ===== ۲. ردیف کارت‌های کلیدی =====
        self._build_kpi_cards()
        
        # ===== ۳. بخش نمودارها (Grid 2x2) =====
        self._build_charts_section()
        
        # ===== ۴. بخش دانش‌آموزان نیازمند توجه =====
        self._build_students_section()
        
        # ===== ۵. بخش روند =====
        self._build_trend_section()
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
    
    def _build_header(self):
        """ساخت هدر و نوار ابزار"""
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
        
        title_label = QLabel("📊 داشبورد تحلیلی")
        title_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #F4C542;")
        
        subtitle_label = QLabel("نمایش شاخص‌های تحلیلی، الگوهای رفتاری و دانش‌آموزان نیازمند توجه")
        subtitle_label.setStyleSheet("font-size: 11px; color: #D9C36A;")
        
        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)
        layout.addLayout(title_box)
        
        layout.addStretch()
        
        # انتخاب معلم
        layout.addWidget(QLabel("معلم:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.setMinimumWidth(150)
        self.teacher_combo.setFixedHeight(36)
        self.teacher_combo.addItem("همه معلمان", None)
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
        
        # انتخاب سال تحصیلی
        layout.addWidget(QLabel("سال:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(120)
        self.year_combo.setFixedHeight(36)
        self.year_combo.addItem("همه سال‌ها", None)
        self.year_combo.currentIndexChanged.connect(self.on_year_changed)
        self.year_combo.setStyleSheet("""
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
        layout.addWidget(self.year_combo)
        
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
        """ساخت کارت‌های آماری کلیدی"""
        cards_grid = QGridLayout()
        cards_grid.setSpacing(12)
        
        self.kpi_cards = {}
        
        cards_config = [
            ("مشاهدات", "کل مشاهدات", "📝", "#0B2E4F", "#0B2E4F", "رفتارهای ثبت‌شده"),
            ("مثبت", "مشاهدات مثبت", "✅", "#16A34A", "#66BB6A", "رفتارهای سازنده"),
            ("منفی", "مشاهدات منفی", "❌", "#DC2626", "#F4D35E", "رفتارهای نامطلوب"),
            ("در انتظار", "پیگیری‌های باز", "🔔", "#D97706", "#FFFBEB", "نیازمند اقدام"),
        ]
        
        for i, (key, title, icon, accent_color, bg_light, subtext) in enumerate(cards_config):
            card = self._create_kpi_card(key, title, icon, "0", accent_color, bg_light, subtext)
            row = i // 2
            col = i % 2
            cards_grid.addWidget(card, row, col)
            self.kpi_cards[key] = card
        
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
    
    def _build_charts_section(self):
        """ساخت بخش نمودارها (Grid 2x2)"""
        charts_grid = QGridLayout()
        charts_grid.setSpacing(14)
        
        # ===== نمودار ۱: توزیع مشاهدات =====
        chart1_card = self._create_chart_card("🍩 توزیع مشاهدات", "positive")
        charts_grid.addWidget(chart1_card, 0, 0)
        
        # ===== نمودار ۲: توزیع پایه‌ها =====
        chart2_card = self._create_chart_card("📊 توزیع دانش‌آموزان بر اساس پایه", "grade")
        charts_grid.addWidget(chart2_card, 0, 1)
        
        # ===== نمودار ۳: وضعیت مداخلات =====
        chart3_card = self._create_chart_card("🛠️ وضعیت مداخلات", "intervention")
        charts_grid.addWidget(chart3_card, 1, 0)
        
        # ===== نمودار ۴: وضعیت پیگیری‌ها =====
        chart4_card = self._create_chart_card("🔔 وضعیت پیگیری‌ها", "followup")
        charts_grid.addWidget(chart4_card, 1, 1)
        
        self.content_layout.addLayout(charts_grid)
    
    def _create_chart_card(self, title, chart_key):
        """ایجاد کارت نمودار"""
        card = QFrame()
        card.setObjectName(f"ChartCard_{chart_key}")
        card.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        
        # هدر
        header_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #F4C542;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # بوم نمودار
        chart_container = QWidget()
        chart_container.setMinimumHeight(200)
        chart_container.setStyleSheet("background-color: #FAFAFA; border-radius: 8px;")
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        # ذخیره مرجع به container برای اضافه کردن نمودار بعداً
        setattr(self, f"chart_{chart_key}_container", chart_container)
        setattr(self, f"chart_{chart_key}_layout", chart_layout)
        
        layout.addWidget(chart_container)
        
        return card
    
    def _build_students_section(self):
        """ساخت بخش دانش‌آموزان نیازمند توجه"""
        students_card = QFrame()
        students_card.setObjectName("StudentsCard")
        students_card.setStyleSheet("""
            QFrame#StudentsCard {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(students_card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        
        # هدر
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        
        title_label = QLabel("👤 دانش‌آموزان نیازمند توجه")
        title_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #F4C542;")
        
        sub_label = QLabel("دانش‌آموزانی که هیچ مشاهده‌ای ندارند یا نیاز به پیگیری ویژه دارند")
        sub_label.setStyleSheet("font-size: 11px; color: #D9C36A;")
        
        title_box.addWidget(title_label)
        title_box.addWidget(sub_label)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        self.students_count_label = QLabel("تعداد: ۰")
        self.students_count_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #DC2626;
            background-color: #F4D35E;
            padding: 3px 12px;
            border-radius: 12px;
            border: 1px solid #C62828;
        """)
        header_layout.addWidget(self.students_count_label)
        
        layout.addLayout(header_layout)
        
        # جدول دانش‌آموزان
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(4)
        self.students_table.setHorizontalHeaderLabels(["نام دانش‌آموز", "پایه", "کلاس", "وضعیت"])
        self.students_table.setShowGrid(False)
        self.students_table.setAlternatingRowColors(True)
        self.students_table.setMinimumHeight(100)
        self.students_table.setStyleSheet("""
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
        """)
        
        header = self.students_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.students_table.verticalHeader().setVisible(False)
        self.students_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.students_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.students_table.itemDoubleClicked.connect(self.on_student_double_clicked)
        
        layout.addWidget(self.students_table)
        
        self.content_layout.addWidget(students_card)
    
    def _build_trend_section(self):
        """ساخت بخش روند تغییرات"""
        trend_card = QFrame()
        trend_card.setObjectName("TrendCard")
        trend_card.setStyleSheet("""
            QFrame#TrendCard {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(trend_card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        
        # هدر
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        
        title_label = QLabel("📈 روند تغییرات")
        title_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #F4C542;")
        
        sub_label = QLabel("روند ثبت مشاهدات در ۶ ماه اخیر")
        sub_label.setStyleSheet("font-size: 11px; color: #D9C36A;")
        
        title_box.addWidget(title_label)
        title_box.addWidget(sub_label)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # بوم نمودار روند
        self.trend_container = QWidget()
        self.trend_container.setMinimumHeight(220)
        self.trend_container.setStyleSheet("background-color: #FAFAFA; border-radius: 8px;")
        self.trend_layout = QVBoxLayout(self.trend_container)
        self.trend_layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(self.trend_container)
        
        self.content_layout.addWidget(trend_card)
    
    def load_academic_years(self):
        """بارگذاری سال‌های تحصیلی"""
        try:
            years = self.academic_year_dal.get_all(include_archived=True)
            self.year_combo.clear()
            self.year_combo.addItem("همه سال‌ها", None)
            for year in years:
                display_text = f"{year.title} {'📦' if year.is_archived == 1 else ''}"
                self.year_combo.addItem(display_text, year.id)
            
            active_year = self.academic_year_dal.get_active()
            if active_year:
                for i in range(self.year_combo.count()):
                    if self.year_combo.itemData(i) == active_year.id:
                        self.year_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری سال‌های تحصیلی: {e}")
    
    def load_teachers(self):
        """بارگذاری معلمان"""
        try:
            all_staff = self.staff_dal.get_all()
            teachers = [s for s in all_staff if s.role == "teacher"]
            self.teacher_combo.clear()
            self.teacher_combo.addItem("همه معلمان", None)
            for teacher in teachers:
                self.teacher_combo.addItem(f"{teacher.full_name}", teacher.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری معلمان: {e}")
    
    def on_teacher_changed(self, index):
        """وقتی معلم تغییر می‌کند"""
        self.current_teacher_id = self.teacher_combo.currentData()
        self.load_dashboard_data()
    
    def on_year_changed(self, index):
        """وقتی سال تحصیلی تغییر می‌کند"""
        self.current_year_id = self.year_combo.currentData()
        self.load_dashboard_data()
    
    def load_dashboard_data(self):
        """بارگذاری داده‌های داشبورد"""
        try:
            self.dashboard_data = self.dashboard_service.get_dashboard_data(
                teacher_id=self.current_teacher_id,
                year_id=self.current_year_id
            )
            
            if not self.dashboard_data:
                return
            
            # به‌روزرسانی کارت‌ها
            self._update_kpi_cards()
            
            # به‌روزرسانی نمودارها
            self._update_charts()
            
            # به‌روزرسانی جدول دانش‌آموزان
            self._update_students_table()
            
            # به‌روزرسانی نمودار روند
            self._update_trend_chart()
            
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری داده‌های داشبورد: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری داده‌ها:\n{str(e)}")
    
    def _update_kpi_cards(self):
        """به‌روزرسانی کارت‌های آماری"""
        stats = self.dashboard_data.get('general_stats', {})
        analytics = self.dashboard_data.get('analytics', {})
        
        self.kpi_cards["مشاهدات"].value_label.setText(str(stats.get('observations_count', 0)))
        self.kpi_cards["مثبت"].value_label.setText(str(stats.get('positive_count', 0)))
        self.kpi_cards["منفی"].value_label.setText(str(stats.get('negative_count', 0)))
        self.kpi_cards["در انتظار"].value_label.setText(str(stats.get('pending_followups', 0)))
    
    def _update_charts(self):
        """به‌روزرسانی نمودارها"""
        analytics = self.dashboard_data.get('analytics', {})
        
        # ===== نمودار ۱: توزیع مشاهدات =====
        obs_dist = analytics.get('observation_distribution', {})
        if obs_dist.get('total', 0) > 0:
            labels = ['مثبت', 'منفی', 'خنثی']
            values = [obs_dist.get('positive', 0), obs_dist.get('negative', 0), obs_dist.get('neutral', 0)]
            colors = ['#8BC34A', '#C62828', '#F4D35E']
            canvas = ChartHelper.create_pie_chart(labels, values, colors, "توزیع مشاهدات")
        else:
            canvas = ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        self._add_chart_to_container('positive', canvas)
        
        # ===== نمودار ۲: توزیع پایه‌ها =====
        grade_dist = analytics.get('grade_distribution', [])
        if grade_dist:
            canvas = ChartHelper.create_grade_distribution_chart(grade_dist, "توزیع دانش‌آموزان بر اساس پایه")
        else:
            canvas = ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        self._add_chart_to_container('grade', canvas)
        
        # ===== نمودار ۳: وضعیت مداخلات =====
        inter_status = analytics.get('intervention_status', {})
        if inter_status.get('total', 0) > 0:
            status_map = {
                'planned': 'برنامه‌ریزی شده',
                'in_progress': 'در حال اجرا',
                'completed': 'تکمیل شده',
                'cancelled': 'لغو شده'
            }
            labels = [status_map.get(k, k) for k in inter_status.keys() if k != 'total']
            values = [v for k, v in inter_status.items() if k != 'total']
            canvas = ChartHelper.create_pie_chart(labels, values, None, "وضعیت مداخلات")
        else:
            canvas = ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        self._add_chart_to_container('intervention', canvas)
        
        # ===== نمودار ۴: وضعیت پیگیری‌ها =====
        follow_status = analytics.get('followup_status', {})
        if follow_status.get('total', 0) > 0:
            status_map = {
                'pending': 'در انتظار',
                'done': 'انجام شده',
                'continued': 'نیازمند ادامه',
                'closed': 'مختومه',
                'cancelled': 'لغو شده'
            }
            labels = [status_map.get(k, k) for k in follow_status.keys() if k != 'total']
            values = [v for k, v in follow_status.items() if k != 'total']
            canvas = ChartHelper.create_pie_chart(labels, values, None, "وضعیت پیگیری‌ها")
        else:
            canvas = ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        self._add_chart_to_container('followup', canvas)
    
    def _add_chart_to_container(self, chart_key, canvas):
        """اضافه کردن نمودار به container مربوطه"""
        container = getattr(self, f"chart_{chart_key}_container", None)
        if not container:
            return
        
        # پاک کردن layout قبلی
        layout = getattr(self, f"chart_{chart_key}_layout", None)
        if layout:
            # حذف ویجت‌های قبلی
            for i in reversed(range(layout.count())):
                widget = layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            layout.addWidget(canvas)
    
    def _update_students_table(self):
        """به‌روزرسانی جدول دانش‌آموزان نیازمند توجه"""
        analytics = self.dashboard_data.get('analytics', {})
        students_list = analytics.get('students_without_observation_list', [])
        
        count = analytics.get('students_without_observation', 0)
        self.students_count_label.setText(f"تعداد: {count}")
        
        self.students_table.setRowCount(len(students_list))
        
        for row, student in enumerate(students_list):
            self.students_table.setItem(row, 0, QTableWidgetItem(student.get('full_name', 'نامشخص')))
            self.students_table.setItem(row, 1, QTableWidgetItem(
                f"پایه {student.get('grade', '?')}" if student.get('grade') else 'نامشخص'
            ))
            self.students_table.setItem(row, 2, QTableWidgetItem(student.get('class_name', '-')))
            self.students_table.setItem(row, 3, QTableWidgetItem("⚠️ بدون مشاهده"))
            
            # رنگ‌بندی ردیف
            for col in range(4):
                item = self.students_table.item(row, col)
                if item:
                    item.setForeground(QColor(220, 38, 38))
        
        # اگر ردیفی وجود ندارد
        if len(students_list) == 0:
            self.students_table.setRowCount(1)
            item = QTableWidgetItem("✅ همه دانش‌آموزان دارای مشاهده هستند")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor(22, 163, 74))
            self.students_table.setItem(0, 0, item)
            self.students_table.setSpan(0, 0, 1, 4)
            self.students_table.setRowHeight(0, 40)
    
    def _update_trend_chart(self):
        from utils.chart_helper import ChartHelper

        # دریافت داده‌های روند از داشبورد
        trend_data = self.dashboard_data.get('trend_data', {})
        
        # اگر داده وجود دارد و مجموع مشاهدات > 0 است
        if trend_data and trend_data.get('total', 0) > 0:
            # استخراج برچسب‌ها و مقادیر
            labels = trend_data.get('labels', [])
            positive = trend_data.get('positive', [])
            negative = trend_data.get('negative', [])
            neutral = trend_data.get('neutral', [])
            
            if labels and any(positive + negative + neutral):
                # ساخت لیست داده‌های روند برای ChartHelper
                trend_items = []
                for i, label in enumerate(labels):
                    trend_items.append({
                        'label': label,
                        'positive': positive[i] if i < len(positive) else 0,
                        'negative': negative[i] if i < len(negative) else 0,
                        'neutral': neutral[i] if i < len(neutral) else 0
                    })
                
                # ✅ ایجاد یک دیکشنری به جای کلاس Wrapper
                chart_data = {
                    'success': True,
                    'trend_data': trend_items
                }
                canvas = ChartHelper.create_trend_chart(chart_data, "روند مشاهدات در ۶ ماه اخیر")
            else:
                canvas = ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        else:
            canvas = ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        # پاک کردن layout قبلی و اضافه کردن نمودار جدید
        for i in reversed(range(self.trend_layout.count())):
            widget = self.trend_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        self.trend_layout.addWidget(canvas)

    def on_student_double_clicked(self, item):
        """باز کردن پرونده دانش‌آموز با دابل‌کلیک"""
        row = item.row()
        if row >= 0:
            # دریافت student_id از جدول
            # در این نسخه ساده، فقط یک پیام نمایش می‌دهیم
            student_name = self.students_table.item(row, 0).text()
            QMessageBox.information(
                self,
                "پرونده دانش‌آموز",
                f"پرونده دانش‌آموز {student_name}\n\nاین قابلیت در نسخه بعدی کامل می‌شود."
            )
