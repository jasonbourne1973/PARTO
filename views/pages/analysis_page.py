"""
صفحه تحلیل روند رشد - نسخه کامل با نمودارهای متعدد و جستجو
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import matplotlib
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dal.academic_year_dal import AcademicYearDAL
from dal.observation_dal import ObservationDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from database.connection import DatabaseConnection
from utils.shamsi_date_input import ShamsiDateInput

matplotlib.use('QtAgg')
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisPage(QWidget):
    """صفحه تحلیل روند رشد با نمودارهای متعدد"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.observation_dal = ObservationDAL()
        self.staff_dal = StaffDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        self.db = DatabaseConnection()
        self.current_student_id = None
        self.all_students = []
        self.all_teachers = []
        self.selected_teacher_id = None
        
        self.setup_ui()
        self.load_students()
        self.load_teachers()
        self.load_academic_years()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        title_label = QLabel("📈 تحلیل روند رشد")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        toolbar.addWidget(title_label)
        toolbar.addStretch()
        
        # انتخاب معلم
        toolbar.addWidget(QLabel("معلم:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.setMinimumWidth(150)
        self.teacher_combo.addItem("همه معلمان", None)
        self.teacher_combo.currentIndexChanged.connect(self.on_teacher_changed)
        toolbar.addWidget(self.teacher_combo)
        
        toolbar.addWidget(QLabel("دانش‌آموز:"))
        self.student_combo = QComboBox()
        self.student_combo.setMinimumWidth(200)
        self.student_combo.addItem("انتخاب دانش‌آموز...", None)
        self.student_combo.currentIndexChanged.connect(self.load_analysis)
        toolbar.addWidget(self.student_combo)
        
        # جستجو
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجوی نام یا کد ملی...")
        self.search_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                padding: 5px 10px;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                font-size: 13px;
                min-width: 150px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F;
                border: 2px solid #F4C542;
            }
        """)
        toolbar.addWidget(self.search_input)
        
        self.search_btn = QPushButton("🔍 جستجو")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 5px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #08223A; }
        """)
        self.search_btn.clicked.connect(self.search_student)
        toolbar.addWidget(self.search_btn)
        
        self.clear_search_btn = QPushButton("✖")
        self.clear_search_btn.setFixedSize(30, 30)
        self.clear_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #9E1B1B; }
        """)
        self.clear_search_btn.clicked.connect(self.clear_search)
        toolbar.addWidget(self.clear_search_btn)
        
        # انتخاب سال تحصیلی
        toolbar.addWidget(QLabel("سال:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(120)
        self.year_combo.addItem("همه سال‌ها", None)
        self.year_combo.currentIndexChanged.connect(self.load_analysis)
        toolbar.addWidget(self.year_combo)
        
        layout.addLayout(toolbar)
        
        # ===== تنظیمات بازه زمانی =====
        date_group = QGroupBox("📅 بازه زمانی تحلیل (شمسی)")
        date_group.setStyleSheet("""
            QGroupBox {
    color: #111111;
                font-weight: bold;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #66BB6A;
            }
            QGroupBox::title {
    background-color: #8BC34A;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #111111;
            }
        """)
        
        date_form_layout = QFormLayout()
        date_form_layout.setSpacing(8)
        
        self.start_date = ShamsiDateInput()
        self.start_date.setFixedHeight(35)
        date_form_layout.addRow("📅 از تاریخ:", self.start_date)
        
        self.end_date = ShamsiDateInput()
        self.end_date.setFixedHeight(35)
        date_form_layout.addRow("📅 تا تاریخ:", self.end_date)
        
        self.analyze_btn = QPushButton("📊 تحلیل")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 10px 30px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
                min-height: 40px;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.analyze_btn.clicked.connect(self.load_analysis)
        date_form_layout.addRow("", self.analyze_btn)
        
        date_group.setLayout(date_form_layout)
        layout.addWidget(date_group)
        
        # ===== تب‌های نمودار =====
        self.chart_tabs = QTabWidget()
        self.chart_tabs.setStyleSheet("""
            QTabWidget::pane {
    color: #111111;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                background-color: #66BB6A;
            }
            QTabBar::tab {
    color: #111111;
    border: 1px solid #8BC34A;
    background-color: #66BB6A;
                padding: 8px 16px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
    border-color: #F4C542;
                background-color: #8BC34A;
                color: #111111;
            }
        """)
        
        # تب 1: روند تغییرات
        self.trend_tab = QWidget()
        trend_layout = QVBoxLayout()
        self.trend_tab.setLayout(trend_layout)
        self.trend_figure = Figure(figsize=(10, 4), dpi=100)
        self.trend_canvas = FigureCanvas(self.trend_figure)
        self.trend_canvas.setStyleSheet("background-color: #0B2E4F; border: 1px solid #D9C36A; border-radius: 5px;")
        trend_layout.addWidget(self.trend_canvas)
        self.chart_tabs.addTab(self.trend_tab, "📈 روند شدت")
        
        # تب 2: توزیع مشاهدات (دایره‌ای)
        self.pie_tab = QWidget()
        pie_layout = QVBoxLayout()
        self.pie_tab.setLayout(pie_layout)
        self.pie_figure = Figure(figsize=(6, 4), dpi=100)
        self.pie_canvas = FigureCanvas(self.pie_figure)
        self.pie_canvas.setStyleSheet("background-color: #0B2E4F; border: 1px solid #D9C36A; border-radius: 5px;")
        pie_layout.addWidget(self.pie_canvas)
        self.chart_tabs.addTab(self.pie_tab, "🍩 توزیع مشاهدات")
        
        # تب 3: نمودار شایستگی‌ها (میله‌ای)
        self.competency_tab = QWidget()
        competency_layout = QVBoxLayout()
        self.competency_tab.setLayout(competency_layout)
        self.competency_figure = Figure(figsize=(8, 4), dpi=100)
        self.competency_canvas = FigureCanvas(self.competency_figure)
        self.competency_canvas.setStyleSheet("background-color: #0B2E4F; border: 1px solid #D9C36A; border-radius: 5px;")
        competency_layout.addWidget(self.competency_canvas)
        self.chart_tabs.addTab(self.competency_tab, "📊 شایستگی‌ها")
        
        # تب 4: نمودار محیط‌ها (میله‌ای)
        self.location_tab = QWidget()
        location_layout = QVBoxLayout()
        self.location_tab.setLayout(location_layout)
        self.location_figure = Figure(figsize=(8, 4), dpi=100)
        self.location_canvas = FigureCanvas(self.location_figure)
        self.location_canvas.setStyleSheet("background-color: #0B2E4F; border: 1px solid #D9C36A; border-radius: 5px;")
        location_layout.addWidget(self.location_canvas)
        self.chart_tabs.addTab(self.location_tab, "📍 محیط‌ها")
        
        layout.addWidget(self.chart_tabs)
        
        # ===== تحلیل توصیفی =====
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setMaximumHeight(150)
        self.analysis_text.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                padding: 10px;
                font-size: 13px;
            }
        """)
        self.analysis_text.setPlaceholderText("پس از انتخاب دانش‌آموز و کلیک روی تحلیل، نتایج اینجا نمایش داده می‌شود...")
        layout.addWidget(self.analysis_text)
        
        self._set_default_dates()
    
    def _set_default_dates(self):
        """تنظیم تاریخ‌های پیش‌فرض"""
        try:
            import jdatetime
            today = jdatetime.date.today()
            self.end_date.set_date(f"{today.year:04d}/{today.month:02d}/{today.day:02d}")
            start_month = today.month - 3
            start_year = today.year
            if start_month <= 0:
                start_month += 12
                start_year -= 1
            self.start_date.set_date(f"{start_year:04d}/{start_month:02d}/{today.day:02d}")
        except (ImportError, ValueError, AttributeError, TypeError) as e:
            # نبود jdatetime یا تاریخ نامعتبر: صفحه بدون تاریخ پیش‌فرض
            # بالا می‌آید و کاربر خودش تاریخ را وارد می‌کند.
            logger.debug(f"تاریخ‌های پیش‌فرض تنظیم نشد: {e}")
    
    def load_teachers(self):
        """بارگذاری معلمان در کامبوباکس"""
        try:
            all_staff = self.staff_dal.get_all()
            self.all_teachers = [s for s in all_staff if s.role == "teacher"]
            self.teacher_combo.clear()
            self.teacher_combo.addItem("همه معلمان", None)
            for teacher in self.all_teachers:
                self.teacher_combo.addItem(f"{teacher.full_name}", teacher.id)
        except Exception as e:
            logger.error(f"خطا در بارگذاری معلمان: {e}")
    
    def on_teacher_changed(self, index):
        """وقتی معلم تغییر می‌کند، لیست دانش‌آموزان را به‌روز کن"""
        self.selected_teacher_id = self.teacher_combo.currentData()
        self.load_students_for_teacher()
    
    def load_students_for_teacher(self):
        """بارگذاری دانش‌آموزان یک معلم خاص"""
        try:
            self.student_combo.clear()
            self.student_combo.addItem("انتخاب دانش‌آموز...", None)
            
            if self.selected_teacher_id:
                year_id = self.year_combo.currentData()
                assignments = self.assignment_dal.get_by_teacher(self.selected_teacher_id, year_id)
                
                for assignment in assignments:
                    student = self.student_dal.get_by_id(assignment.student_id)
                    if student:
                        profile = self.profile_dal.get_active_by_student(student.id)
                        grade_text = profile.grade_display if profile else "نامشخص"
                        display_text = f"{student.full_name} - پایه {grade_text}"
                        self.student_combo.addItem(display_text, student.id)
            else:
                self.all_students = self.student_dal.get_all()
                for student in self.all_students:
                    profile = self.profile_dal.get_active_by_student(student.id)
                    grade_text = profile.grade_display if profile else "نامشخص"
                    display_text = f"{student.full_name} - پایه {grade_text}"
                    self.student_combo.addItem(display_text, student.id)
        except Exception as e:
            logger.error(f"خطا در بارگذاری دانش‌آموزان معلم: {e}")
    
    def load_academic_years(self):
        """بارگذاری سال‌های تحصیلی در کامبوباکس"""
        try:
            years = self.academic_year_dal.get_all(include_archived=True)
            self.year_combo.clear()
            self.year_combo.addItem("همه سال‌ها", None)
            for year in years:
                display_text = f"{year.title} {'(بایگانی)' if year.is_archived == 1 else ''}"
                self.year_combo.addItem(display_text, year.id)
            
            active_year = self.academic_year_dal.get_active()
            if active_year:
                for i in range(self.year_combo.count()):
                    if self.year_combo.itemData(i) == active_year.id:
                        self.year_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            logger.error(f"خطا در بارگذاری سال‌های تحصیلی: {e}")
    
    def load_students(self):
        """بارگذاری دانش‌آموزان در کامبوباکس"""
        try:
            self.all_students = self.student_dal.get_all()
            self.student_combo.clear()
            self.student_combo.addItem("انتخاب دانش‌آموز...", None)
            for student in self.all_students:
                profile = self.profile_dal.get_active_by_student(student.id)
                grade_text = profile.grade_display if profile else "نامشخص"
                display_text = f"{student.full_name} - پایه {grade_text}"
                self.student_combo.addItem(display_text, student.id)
        except Exception as e:
            logger.error(f"خطا در بارگذاری دانش‌آموزان: {e}")
    
    def search_student(self):
        """جستجوی دانش‌آموز و انتخاب در کامبوباکس"""
        search_term = self.search_input.text().strip()
        if not search_term:
            QMessageBox.warning(self, "توجه", "لطفاً عبارت جستجو را وارد کنید.")
            return
        
        try:
            results = self.student_dal.search(search_term)
            if not results:
                QMessageBox.information(self, "نتیجه", "هیچ دانش‌آموزی یافت نشد.")
                return
            
            if len(results) == 1:
                student = results[0]
                for i in range(self.student_combo.count()):
                    if self.student_combo.itemData(i) == student.id:
                        self.student_combo.setCurrentIndex(i)
                        break
            else:
                names = "\n".join([f"• {s.full_name} (کد: {s.national_code or 'ندارد'})" for s in results[:10]])
                msg = f"{len(results)} دانش‌آموز پیدا شد:\n\n{names}\n\nلطفاً از لیست کشویی انتخاب کنید."
                QMessageBox.information(self, "نتیجه جستجو", msg)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در جستجو:\n{e!s}")
    
    def clear_search(self):
        """پاک کردن جستجو و نمایش همه"""
        self.search_input.clear()
        self.student_combo.setCurrentIndex(0)
    
    def load_analysis(self):
        """بارگذاری تحلیل برای دانش‌آموز انتخاب شده"""
        student_id = self.student_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        year_id = self.year_combo.currentData()
        
        if student_id is None:
            self.clear_charts()
            self.analysis_text.setText("⚠️ لطفاً یک دانش‌آموز را انتخاب کنید.")
            return
        
        self.current_student_id = student_id
        
        start_date = self.start_date.get_date_string()
        end_date = self.end_date.get_date_string()
        
        if not start_date or not end_date:
            self.analysis_text.setText("⚠️ لطفاً تاریخ شروع و پایان را وارد کنید.")
            return
        
        if year_id:
            profile = self.profile_dal.get_by_student_and_year(student_id, year_id)
        else:
            profile = self.profile_dal.get_active_by_student(student_id)
        
        if not profile:
            self.clear_charts()
            self.analysis_text.setText("⚠️ هیچ پرونده‌ای برای این دانش‌آموز در سال انتخاب شده وجود ندارد.")
            return
        
        observations = self.observation_dal.get_by_date_range(
            profile.id, start_date, end_date
        )
        
        if teacher_id:
            observations = [obs for obs in observations if obs.staff_id == teacher_id]
        
        if not observations:
            self.clear_charts()
            self.analysis_text.setText("⚠️ هیچ مشاهده‌ای در بازه زمانی انتخاب شده وجود ندارد.")
            return
        
        # رسم تمام نمودارها
        self.draw_trend_chart(observations)
        self.draw_pie_chart(observations)
        self.draw_competency_chart(observations)
        self.draw_location_chart(observations)
        self.show_analysis_text(observations, start_date, end_date)
    
    def clear_charts(self):
        """پاک کردن تمام نمودارها"""
        for figure in [self.trend_figure, self.pie_figure, self.competency_figure, self.location_figure]:
            figure.clear()
            canvas = figure.canvas
            if canvas:
                canvas.draw()
    
    def draw_trend_chart(self, observations):
        """رسم نمودار روند تغییرات"""
        self.trend_figure.clear()
        ax = self.trend_figure.add_subplot(111)
        
        dates = {}
        for obs in observations:
            if obs.observation_date not in dates:
                dates[obs.observation_date] = []
            dates[obs.observation_date].append(obs.severity)
        
        sorted_dates = sorted(dates.keys())
        avg_severities = [sum(dates[d]) / len(dates[d]) for d in sorted_dates]
        max_severities = [max(dates[d]) for d in sorted_dates]
        min_severities = [min(dates[d]) for d in sorted_dates]
        
        ax.plot(sorted_dates, avg_severities, 'o-', linewidth=2, color='#0B2E4F', label='میانگین')
        ax.fill_between(sorted_dates, min_severities, max_severities, alpha=0.2, color='#0B2E4F')
        
        ax.set_xlabel('تاریخ (شمسی)', fontsize=11)
        ax.set_ylabel('شدت', fontsize=11)
        ax.set_title('روند تغییرات شدت مشاهدات', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # چرخش برچسب‌ها
        ax.tick_params(axis='x', rotation=45)
        
        self.trend_figure.tight_layout()
        self.trend_canvas.draw()
    
    def draw_pie_chart(self, observations):
        """رسم نمودار دایره‌ای توزیع مشاهدات"""
        self.pie_figure.clear()
        ax = self.pie_figure.add_subplot(111)
        
        positive = sum(1 for o in observations if o.behavior_type == "مثبت")
        negative = sum(1 for o in observations if o.behavior_type == "منفی")
        neutral = len(observations) - positive - negative
        
        labels = ['مثبت', 'منفی', 'خنثی']
        sizes = [positive, negative, neutral]
        colors = ['#8BC34A', '#C62828', '#F4D35E']
        explode = (0.05, 0.05, 0.05)
        
        if sum(sizes) > 0:
            ax.pie(sizes, explode=explode, labels=labels, colors=colors,
                   autopct='%1.1f%%', shadow=True, startangle=90)
            ax.set_title('توزیع نوع مشاهدات', fontsize=13, fontweight='bold')
        
        self.pie_figure.tight_layout()
        self.pie_canvas.draw()
    
    def draw_competency_chart(self, observations):
        """رسم نمودار میله‌ای شایستگی‌ها"""
        self.competency_figure.clear()
        ax = self.competency_figure.add_subplot(111)
        
        # گروه‌بندی بر اساس شایستگی
        competency_stats = {}
        for obs in observations:
            if obs.competency_id:
                comp_name = obs.competency_title or self._get_competency_name(obs.competency_id)
                if comp_name not in competency_stats:
                    competency_stats[comp_name] = {'count': 0, 'total_severity': 0}
                competency_stats[comp_name]['count'] += 1
                competency_stats[comp_name]['total_severity'] += obs.severity or 1
        
        if competency_stats:
            # مرتب‌سازی و انتخاب ۱۰ مورد اول
            items = sorted(competency_stats.items(), 
                          key=lambda x: x[1]['total_severity'] / x[1]['count'], 
                          reverse=True)[:10]
            
            names = [item[0][:15] for item in items]
            values = [item[1]['total_severity'] / item[1]['count'] for item in items]
            
            bars = ax.bar(names, values, color='#66BB6A', edgecolor='#F4C542')
            
            # رنگ‌بندی بر اساس مقدار
            for bar, val in zip(bars, values):
                if val >= 4:
                    bar.set_color('#66BB6A')
                elif val >= 3:
                    bar.set_color('#0B2E4F')
                elif val >= 2:
                    bar.set_color('#F4D35E')
                else:
                    bar.set_color('#C62828')
            
            ax.set_ylabel('میانگین شدت', fontsize=11)
            ax.set_xlabel('شایستگی', fontsize=11)
            ax.set_title('وضعیت شایستگی‌ها', fontsize=13, fontweight='bold')
            ax.set_ylim(0, 5)
            ax.grid(True, alpha=0.2, axis='y')
            
            # چرخش برچسب‌ها
            ax.tick_params(axis='x', rotation=30)
        
        self.competency_figure.tight_layout()
        self.competency_canvas.draw()
    
    def draw_location_chart(self, observations):
        """رسم نمودار میله‌ای محیط‌های مشاهده"""
        self.location_figure.clear()
        ax = self.location_figure.add_subplot(111)
        
        # گروه‌بندی بر اساس محیط
        location_stats = {}
        for obs in observations:
            loc = obs.location or 'نامشخص'
            if loc not in location_stats:
                location_stats[loc] = 0
            location_stats[loc] += 1
        
        if location_stats:
            items = sorted(location_stats.items(), key=lambda x: x[1], reverse=True)[:8]
            
            names = [item[0] for item in items]
            values = [item[1] for item in items]
            
            bars = ax.bar(names, values, color='#0B2E4F', edgecolor='#F4C542')
            
            # نمایش اعداد روی میله‌ها
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                       str(val), ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            ax.set_ylabel('تعداد مشاهدات', fontsize=11)
            ax.set_xlabel('محیط', fontsize=11)
            ax.set_title('توزیع مشاهدات بر اساس محیط', fontsize=13, fontweight='bold')
            ax.grid(True, alpha=0.2, axis='y')
            
            # چرخش برچسب‌ها
            ax.tick_params(axis='x', rotation=30)
        
        self.location_figure.tight_layout()
        self.location_canvas.draw()
    
    def _get_competency_name(self, competency_id):
        """دریافت نام شایستگی از شناسه"""
        try:
            from dal.competency_dal import CompetencyDAL
            comp_dal = CompetencyDAL()
            comp = comp_dal.get_by_id(competency_id)
            return comp.title if comp else "نامشخص"
        except Exception:
            return "نامشخص"
    
    def show_analysis_text(self, observations, start_date, end_date):
        """نمایش تحلیل توصیفی"""
        if not observations:
            self.analysis_text.setText("⚠️ داده‌ای برای تحلیل وجود ندارد.")
            return
        
        severities = [obs.severity for obs in observations]
        avg_severity = sum(severities) / len(severities)
        max_severity = max(severities)
        min_severity = min(severities)
        
        positive = sum(1 for obs in observations if obs.behavior_type == "مثبت")
        negative = sum(1 for obs in observations if obs.behavior_type == "منفی")
        neutral = len(observations) - positive - negative
        
        # تحلیل روند
        if len(observations) >= 3:
            first_third = severities[:len(severities)//3]
            last_third = severities[2*len(severities)//3:]
            
            if len(first_third) > 0 and len(last_third) > 0:
                avg_first = sum(first_third) / len(first_third)
                avg_last = sum(last_third) / len(last_third)
                
                if avg_last > avg_first * 1.1:
                    trend = "📈 افزایش قابل توجه"
                elif avg_last > avg_first:
                    trend = "📈 افزایش ملایم"
                elif avg_last < avg_first * 0.9:
                    trend = "📉 کاهش قابل توجه"
                elif avg_last < avg_first:
                    trend = "📉 کاهش ملایم"
                else:
                    trend = "➡️ تقریباً ثابت"
            else:
                trend = "⚠️ داده کافی نیست"
        else:
            trend = "⚠️ حداقل به ۳ مشاهده نیاز است"
        
        student_name = self.get_student_name()
        
        analysis = f"""
📊 **تحلیل جامع روند رشد**

📌 **دانش‌آموز:** {student_name}
📅 **بازه زمانی:** {start_date} تا {end_date}
📝 **تعداد مشاهدات:** {len(observations)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **روند کلی:** {trend}

📊 **آمار توصیفی:**
• میانگین شدت: {avg_severity:.2f}
• بیشترین شدت: {max_severity}
• کمترین شدت: {min_severity}
• انحراف معیار: {np.std(severities):.2f}

🏷️ **توزیع نوع مشاهدات:**
• ✅ مثبت: {positive} مورد ({positive/len(observations)*100:.1f}%)
• ❌ منفی: {negative} مورد ({negative/len(observations)*100:.1f}%)
• ⬜ خنثی: {neutral} مورد ({neutral/len(observations)*100:.1f}%)

💡 **توصیه‌ها:**
{self.get_recommendation(avg_severity, trend, positive/len(observations) if observations else 0)}
"""
        self.analysis_text.setText(analysis)
    
    def get_student_name(self):
        try:
            student = self.student_dal.get_by_id(self.current_student_id)
            return student.full_name if student else "نامشخص"
        except Exception:
            return "نامشخص"
    
    def get_recommendation(self, avg_severity, trend, positive_ratio):
        recommendations = []
        
        if avg_severity >= 4:
            recommendations.append("✅ وضعیت کلی بسیار مطلوب است. به نظارت و ثبت مشاهدات ادامه دهید.")
        elif avg_severity >= 3:
            if "افزایش" in trend:
                recommendations.append("🟡 روند رو به بهبود است. به حمایت و تمرین ادامه دهید.")
            else:
                recommendations.append("🟡 وضعیت متوسط است. با تمرین‌های هدفمند می‌توان بهبود یافت.")
        elif avg_severity >= 2:
            if "کاهش" in trend:
                recommendations.append("🟠 روند کاهشی است. نیاز به بررسی و حمایت ویژه دارد.")
            else:
                recommendations.append("🟠 وضعیت نیازمند توجه است. با مشاور مدرسه هماهنگ کنید.")
        else:
            recommendations.append("🔴 وضعیت نیازمند حمایت فوری است. لطفاً با مشاور مدرسه تماس بگیرید.")
        
        if positive_ratio >= 0.6:
            recommendations.append("✅ درصد مشاهدات مثبت بالا است. فضای آموزشی مناسب می‌باشد.")
        elif positive_ratio >= 0.4:
            recommendations.append("🟡 درصد مشاهدات مثبت متوسط است. می‌توان با تقویت رفتارهای مثبت بهبود یافت.")
        else:
            recommendations.append("🔴 درصد مشاهدات مثبت پایین است. بررسی علل و تغییر رویکرد توصیه می‌شود.")
        
        return "\n".join(recommendations)