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

from utils.behavior_analysis import (
    count_behaviors,
    growth_direction,
    shares,
)
from utils.logger import get_logger
from views.pages.year_sync import YearAwarePage

logger = get_logger(__name__)


class AnalysisPage(YearAwarePage, QWidget):
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
                color: #111111;
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
    
    def reload_for_year(self, year_id):
        """بارگذاری دوبارهٔ تحلیل‌ها با سال اعلام‌شده"""
        self.load_teachers()
        self.load_students_for_teacher()
        self.load_analysis()
        return True

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
                
                # خوانش دسته‌ای دانش‌آموزان و پروندهٔ فعال‌شان (رفع N+1؛
                # قبلاً برای هر تخصیص دو کوئری جدا زده می‌شد)
                student_map = self.student_dal.get_by_ids(
                    a.student_id for a in assignments)
                profile_map = self.profile_dal.get_active_by_students(student_map.keys())
                for assignment in assignments:
                    student = student_map.get(assignment.student_id)
                    if student:
                        profile = profile_map.get(student.id)
                        grade_text = profile.grade_display if profile else "نامشخص"
                        display_text = f"{student.full_name} - پایه {grade_text}"
                        self.student_combo.addItem(display_text, student.id)
            else:
                self.all_students = self.student_dal.get_all()
                # پروندهٔ فعال دانش‌آموزان یک‌جا خوانده می‌شود (رفع N+1)
                profile_map = self.profile_dal.get_active_by_students(
                    s.id for s in self.all_students)
                for student in self.all_students:
                    profile = profile_map.get(student.id)
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
            # پروندهٔ فعال دانش‌آموزان یک‌جا خوانده می‌شود (رفع N+1)
            profile_map = self.profile_dal.get_active_by_students(
                s.id for s in self.all_students)
            for student in self.all_students:
                profile = profile_map.get(student.id)
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
        """
        رسم نمودار روند **ترکیب رفتارها** (بازرسی یازدهم)

        پیش از این، نمودار «میانگین شدت» را نشان می‌داد؛ اکنون تعداد
        رفتارهای مثبت/منفی/خنثی در طول زمان رسم می‌شود، زیرا شاخص رشد
        «تغییر نوع رفتارهای ثبت‌شده» است و نه شدت یا حجم ثبت.
        """
        self.trend_figure.clear()
        ax = self.trend_figure.add_subplot(111)

        dates = {}
        for obs in observations:
            dates.setdefault(obs.observation_date, []).append(obs.behavior_type)

        sorted_dates = sorted(dates.keys())
        positives = [sum(1 for t in dates[d] if t == 'مثبت') for d in sorted_dates]
        negatives = [sum(1 for t in dates[d] if t == 'منفی') for d in sorted_dates]
        neutrals = [sum(1 for t in dates[d] if t not in ('مثبت', 'منفی')) for d in sorted_dates]

        ax.plot(sorted_dates, positives, 'o-', linewidth=2, color='#2E7D32',
                label='رفتار مثبت')
        ax.plot(sorted_dates, negatives, 'o-', linewidth=2, color='#C62828',
                label='رفتار منفی')
        ax.plot(sorted_dates, neutrals, 'o-', linewidth=1.5, color='#9E9E9E',
                label='خنثی')

        ax.set_xlabel('تاریخ (شمسی)', fontsize=11)
        ax.set_ylabel('تعداد رفتار ثبت‌شده', fontsize=11)
        ax.set_title('روند تغییر ترکیب رفتارها (تعداد = حجم ثبت، نه شاخص رشد)',
                     fontsize=12, fontweight='bold')
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
        
        # گروه‌بندی بر اساس شایستگی — با تفکیک نوع رفتار (نه شدت)
        competency_stats = {}
        for obs in observations:
            if obs.competency_id:
                comp_name = obs.competency_title or self._get_competency_name(obs.competency_id)
                entry = competency_stats.setdefault(
                    comp_name, {'positive': 0, 'negative': 0, 'neutral': 0, 'count': 0})
                entry['count'] += 1
                if obs.behavior_type == 'مثبت':
                    entry['positive'] += 1
                elif obs.behavior_type == 'منفی':
                    entry['negative'] += 1
                else:
                    entry['neutral'] += 1
        
        if competency_stats:
            # مرتب‌سازی بر پایهٔ تعداد رفتارهای جهت‌دار و انتخاب ۱۰ مورد اول
            items = sorted(
                competency_stats.items(),
                key=lambda x: (x[1]['positive'] + x[1]['negative'], x[1]['count']),
                reverse=True)[:10]
            
            names = [item[0][:15] for item in items]
            positions = range(len(names))
            positive_values = [item[1]['positive'] for item in items]
            negative_values = [item[1]['negative'] for item in items]
            
            ax.bar([p - 0.2 for p in positions], positive_values, width=0.4,
                   color='#66BB6A', edgecolor='#2E7D32', label='رفتار مثبت')
            ax.bar([p + 0.2 for p in positions], negative_values, width=0.4,
                   color='#C62828', edgecolor='#8E1B1B', label='رفتار منفی')
            ax.set_xticks(list(positions))
            ax.set_xticklabels(names)
            
            ax.set_ylabel('تعداد رفتار ثبت‌شده', fontsize=11)
            ax.set_xlabel('زمینه (شایستگی)', fontsize=11)
            ax.set_title('ترکیب رفتارهای ثبت‌شده به تفکیک زمینه (بدون رتبه‌بندی مقایسه‌ای)',
                         fontsize=12, fontweight='bold')
            ax.legend()
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
        
        # ===== اصلاح (بازرسی یازدهم) =====
        # تحلیل بر پایهٔ **ترکیب رفتارهای ثبت‌شده** ساخته می‌شود، نه
        # میانگین شدت و نه حجم مشاهدات. یک مشاهدهٔ منفرد نتیجه‌گیری
        # نمی‌سازد و متن هیچ تشخیصی ارائه نمی‌کند.
        counts = count_behaviors(observations)
        share = shares(counts)
        by_date = {}
        for obs in observations:
            by_date.setdefault(obs.observation_date or '-', []).append(obs)

        periods = []
        for date_key in sorted(by_date.keys()):
            period_counts = count_behaviors(by_date[date_key])
            periods.append({'label': date_key, 'positive': period_counts['positive'],
                            'negative': period_counts['negative'],
                            'neutral': period_counts['neutral'],
                            'total': period_counts['total']})

        direction = growth_direction(periods)
        student_name = self.get_student_name()
        
        analysis = f"""
📊 **تحلیل روند رشد (بر پایهٔ رفتارهای ثبت‌شده)**

📌 **دانش‌آموز:** {student_name}
📅 **بازه زمانی:** {start_date} تا {end_date}
📝 **حجم ثبت و پایش:** {counts['total']} مشاهده (این عدد به‌تنهایی شاخص رشد نیست)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **جهت تغییر رفتار:** {direction['label']}
{direction['message']}
{self._format_path_lines(direction)}🗒️ {direction['volume_note']}

🏷️ **ترکیب رفتارهای ثبت‌شده:**
• ✅ مثبت: {counts['positive']} مورد ({share['positive']}٪)
• ❌ منفی: {counts['negative']} مورد ({share['negative']}٪)
• ⬜ خنثی: {counts['neutral']} مورد
• میانگین شدت (اطلاعات تکمیلی): {np.mean([obs.severity or 1 for obs in observations]):.2f}

💡 **پیشنهادها (بر پایهٔ دادهٔ ثبت‌شده):**
{self.get_recommendation(share['positive'], direction['status'], counts)}

⚠️ این تحلیل «الگوی مشاهده‌شده» را توصیف می‌کند؛ تشخیص روان‌شناختی یا
برچسب نیست و مقایسه فقط با خود دانش‌آموز در طول زمان انجام می‌شود.
"""
        self.analysis_text.setText(analysis)
    
    @staticmethod
    def _format_path_lines(direction):
        """
        مسیر تغییر بین بازه‌ها (بازرسی سیزدهم)

        جهت روند فقط از مقایسهٔ اولین و آخرین بازه گرفته نمی‌شود؛ برای
        شفافیت، گام‌های میانی و یادداشت‌های احتیاطی هم نمایش داده می‌شوند.
        """
        lines = []
        path_text = (direction or {}).get('path_text') or ''
        if path_text:
            lines.append(f"🧭 مسیر تغییر بین بازه‌ها: {path_text}")
        for caution in (direction or {}).get('caution_notes') or []:
            lines.append(f"⚠️ {caution}")
        return ("\n".join(lines) + "\n") if lines else ""

    def get_student_name(self):
        try:
            student = self.student_dal.get_by_id(self.current_student_id)
            return student.full_name if student else "نامشخص"
        except Exception:
            return "نامشخص"
    
    def get_recommendation(self, positive_share, direction_status, counts):
        """
        پیشنهاد محتاطانه و قابل ردیابی — بر پایهٔ رفتارهای ثبت‌شده

        ساختار: دادهٔ ثبت‌شده ← الگوی مشاهده‌شده ← پیشنهاد بررسی/اقدام.
        شدت رفتار در این پیشنهادها نقشی ندارد و متن، تشخیص نیست.
        """
        recommendations = []

        # ۱) دادهٔ ثبت‌شده
        recommendations.append(
            f"دادهٔ ثبت‌شده: {counts['positive']} رفتار مثبت، "
            f"{counts['negative']} رفتار منفی و {counts['neutral']} رفتار خنثی "
            f"(سهم رفتار مثبت {positive_share}٪)."
        )

        # ۲) الگوی مشاهده‌شده
        if counts['total'] < 2:
            recommendations.append(
                "الگوی مشاهده‌شده: برای تحلیل الگو به ثبت مشاهدات بیشتری نیاز است؛ "
                "یک مشاهدهٔ منفرد مبنای نتیجه‌گیری نیست."
            )
        elif positive_share >= 60:
            recommendations.append(
                "الگوی مشاهده‌شده: سهم رفتارهای مثبت بیشتر است؛ تقویت همین مسیر پیشنهاد می‌شود."
            )
        elif positive_share >= 40:
            recommendations.append(
                "الگوی مشاهده‌شده: ترکیب رفتارها متعادل است؛ بررسی زمینه‌ها و "
                "تقویت رفتارهای مثبت پیشنهاد می‌شود."
            )
        else:
            recommendations.append(
                "الگوی مشاهده‌شده: در این زمینه الگوی نیازمند توجه مشاهده شده است؛ "
                "بررسی دقیق‌تر و در صورت تأیید، اقدام هدفمند پیشنهاد می‌شود."
            )

        # ۳) پیشنهاد بررسی/اقدام
        if direction_status == 'improving':
            recommendations.append(
                "پیشنهاد: با ثبت مستمر مشاهدات، روند را در بازهٔ بعدی هم بررسی کنید."
            )
        elif direction_status == 'declining':
            recommendations.append(
                "پیشنهاد: بررسی زمینه‌ها و هماهنگی با مشاور مدرسه پیشنهاد می‌شود."
            )
        elif direction_status == 'insufficient':
            recommendations.append(
                "پیشنهاد: ثبت مشاهده در بازه‌های زمانی مختلف، تحلیل روند را دقیق‌تر می‌کند."
            )
        else:
            recommendations.append(
                "پیشنهاد: ادامهٔ ثبت و پایش رفتارها و بررسی تغییرات در بازهٔ بعدی."
            )

        recommendations.append(
            "یادآوری: این متن «الگوی مشاهده‌شده» را گزارش می‌کند و به‌معنای "
            "تشخیص یا برچسب نیست."
        )
        return "\n".join(recommendations)