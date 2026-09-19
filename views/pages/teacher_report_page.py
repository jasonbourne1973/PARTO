"""
صفحه گزارش معلم - نسخه کامل با خروجی Excel و PDF
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import matplotlib
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dal.academic_year_dal import AcademicYearDAL
from dal.competency_dal import CompetencyDAL
from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.staff_dal import StaffDAL

# ===== اصلاح =====
# در متد گزارش‌گیری از `self.profile_dal` استفاده می‌شد ولی این ویژگی
# هیچ‌جا در __init__ ساخته نمی‌شد؛ بنابراین hasattr همیشه False بود و
# `profile` همیشه None می‌ماند ⇒ بلوک `if profile:` هرگز اجرا نمی‌شد و
# گزارش معلم برای همه دانش‌آموزان «صفر مشاهده/مداخله/پیگیری» نشان
# می‌داد (بدون هیچ پیام خطایی).
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from services.teacher_report_service import TeacherReportService
from utils.shamsi_date_input import ShamsiDateInput

matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from utils.behavior_analysis import classify_pattern, pattern_label
from utils.logger import get_logger

logger = get_logger(__name__)


class TeacherReportPage(QWidget):
    """صفحه گزارش معلم"""
    
    def __init__(self, parent=None, embedded=False):
        super().__init__(parent)
        self.embedded = embedded
        
        self.student_dal = StudentDAL()
        self.staff_dal = StaffDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.competency_dal = CompetencyDAL()
        # ===== اصلاح =====
        # بدون این خط، `hasattr(self, 'profile_dal')` در متد گزارش‌گیری
        # همیشه False بود و گزارش معلم خالی برمی‌گشت.
        self.profile_dal = StudentAcademicProfileDAL()
        self.report_service = TeacherReportService()
        
        self.current_teacher_id = None
        self.current_report = None
        self.all_teachers = []
        
        self.setup_ui()
        self.load_teachers()
        self.load_academic_years()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        if not self.embedded:
            title_label = QLabel("📊 گزارش عملکرد معلم")
            title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
            layout.addWidget(title_label)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        toolbar.addWidget(QLabel("معلم:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.setMinimumWidth(200)
        self.teacher_combo.setPlaceholderText("انتخاب معلم...")
        self.teacher_combo.currentIndexChanged.connect(self.on_teacher_changed)
        toolbar.addWidget(self.teacher_combo)
        
        toolbar.addSpacing(15)
        
        toolbar.addWidget(QLabel("سال تحصیلی:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(150)
        self.year_combo.currentIndexChanged.connect(self.on_year_changed)
        toolbar.addWidget(self.year_combo)
        
        toolbar.addSpacing(15)
        
        toolbar.addWidget(QLabel("از تاریخ:"))
        self.start_date = ShamsiDateInput()
        toolbar.addWidget(self.start_date)
        
        toolbar.addWidget(QLabel("تا تاریخ:"))
        self.end_date = ShamsiDateInput()
        toolbar.addWidget(self.end_date)
        
        toolbar.addSpacing(10)
        
        self.generate_btn = QPushButton("📊 تولید گزارش")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.generate_btn.clicked.connect(self.generate_report)
        toolbar.addWidget(self.generate_btn)
        
        toolbar.addStretch()
        
        # دکمه‌های خروجی
        self.excel_btn = QPushButton("📊 Excel")
        self.excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 6px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.excel_btn.clicked.connect(self.export_excel)
        toolbar.addWidget(self.excel_btn)
        
        self.pdf_btn = QPushButton("📄 PDF")
        self.pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 6px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #D94B4B; }
        """)
        self.pdf_btn.clicked.connect(self.export_pdf)
        toolbar.addWidget(self.pdf_btn)
        
        layout.addLayout(toolbar)
        
        # ===== پیام "داده ناکافی" =====
        self.insufficient_data_label = QLabel("")
        self.insufficient_data_label.setStyleSheet("""
            QLabel {
                background-color: #C62828;
                color: #C62828;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                border: 1px solid #F4C542;
            }
        """)
        self.insufficient_data_label.setVisible(False)
        layout.addWidget(self.insufficient_data_label)
        
        # ===== نوار پیشرفت =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #D9C36A;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0B2E4F;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # ===== تب‌های گزارش =====
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
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
                padding: 10px 20px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
    border-color: #F4C542;
                background-color: #8BC34A;
                color: #111111;
            }
        """)
        
        self.tabs.addTab(self.create_summary_tab(), "📊 خلاصه")
        self.tabs.addTab(self.create_competency_tab(), "⭐ شایستگی‌ها")
        self.tabs.addTab(self.create_students_tab(), "📋 دانش‌آموزان")
        self.tabs.addTab(self.create_chart_tab(), "📈 نمودار")
        self.tabs.addTab(self.create_recommendations_tab(), "💡 پیشنهادات")
        
        layout.addWidget(self.tabs)
    
    def create_summary_tab(self):
        """ایجاد تب خلاصه"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                padding: 15px;
                font-size: 13px;
                line-height: 1.8;
            }
        """)
        self.summary_text.setPlaceholderText("پس از انتخاب معلم و کلیک روی تولید گزارش، خلاصه اینجا نمایش داده می‌شود...")
        scroll.setWidget(self.summary_text)
        layout.addWidget(scroll)
        
        return tab
    
    def create_competency_tab(self):
        """ایجاد تب شایستگی‌ها"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.competency_table = QTableWidget()
        self.competency_table.setColumnCount(4)
        self.competency_table.setHorizontalHeaderLabels(["شایستگی", "میانگین شدت", "تعداد", "وضعیت"])
        self.competency_table.setAlternatingRowColors(True)
        self.competency_table.setStyleSheet("""
            QTableWidget {
    color: #F4C542;
                background-color: #0B2E4F;
                alternate-background-color: #0B2E4F;
                gridline-color: #D9C36A;
                border: 1px solid #D9C36A;
                border-radius: 5px;
            }
            QTableWidget::item {
    color: #F4C542;
    border-bottom: 1px solid #D9C36A;
    background-color: #0B2E4F; padding: 8px; }
            QHeaderView::section {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px;
                border: 1px solid #D9C36A;
                font-weight: bold;
            }
        """)
        
        header = self.competency_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.competency_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.competency_table)
        
        return tab
    
    def create_students_tab(self):
        """ایجاد تب دانش‌آموزان"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(6)
        self.students_table.setHorizontalHeaderLabels([
            "ردیف", "دانش‌آموز", "پایه", "کلاس", "مشاهدات", "وضعیت کلی"
        ])
        self.students_table.setAlternatingRowColors(True)
        self.students_table.setStyleSheet("""
            QTableWidget {
    color: #F4C542;
                background-color: #0B2E4F;
                alternate-background-color: #0B2E4F;
                gridline-color: #D9C36A;
                border: 1px solid #D9C36A;
                border-radius: 5px;
            }
            QTableWidget::item {
    color: #F4C542;
    border-bottom: 1px solid #D9C36A;
    background-color: #0B2E4F; padding: 8px; }
            QTableWidget::item:hover {
    color: #FFE8A3; background-color: #174F78; }
            QHeaderView::section {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px;
                border: 1px solid #D9C36A;
                font-weight: bold;
            }
        """)
        
        header = self.students_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.students_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.students_table.itemDoubleClicked.connect(self.on_student_double_clicked)
        layout.addWidget(self.students_table)
        
        return tab
    
    def create_chart_tab(self):
        """ایجاد تب نمودار"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #0B2E4F; border: 1px solid #D9C36A; border-radius: 5px;")
        layout.addWidget(self.canvas)
        
        return tab
    
    def create_recommendations_tab(self):
        """ایجاد تب پیشنهادات"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        self.recommendations_text.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                padding: 15px;
                font-size: 13px;
                line-height: 1.8;
            }
        """)
        self.recommendations_text.setPlaceholderText("پیشنهادات پس از تولید گزارش نمایش داده می‌شود...")
        scroll.setWidget(self.recommendations_text)
        layout.addWidget(scroll)
        
        return tab
    
    def load_teachers(self):
        """بارگذاری معلمان در کامبوباکس"""
        try:
            all_staff = self.staff_dal.get_all()
            self.all_teachers = [s for s in all_staff if s.role == "teacher"]
            self.teacher_combo.clear()
            self.teacher_combo.addItem("انتخاب معلم...", None)
            for teacher in self.all_teachers:
                self.teacher_combo.addItem(f"{teacher.full_name}", teacher.id)
        except Exception as e:
            logger.error(f"خطا در بارگذاری معلمان: {e}")
    
    def load_academic_years(self):
        """بارگذاری سال‌های تحصیلی در کامبوباکس"""
        try:
            years = self.academic_year_dal.get_all(include_archived=True)
            self.year_combo.clear()
            self.year_combo.addItem("همه سال‌ها", None)
            for year in years:
                display_text = f"{year.title} {'📦' if year.is_archived == 1 else ''}"
                self.year_combo.addItem(display_text, year.id)
            
            # انتخاب سال فعال
            active_year = self.academic_year_dal.get_active()
            if active_year:
                for i in range(self.year_combo.count()):
                    if self.year_combo.itemData(i) == active_year.id:
                        self.year_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            logger.error(f"خطا در بارگذاری سال‌های تحصیلی: {e}")
    
    def on_teacher_changed(self, index):
        """وقتی معلم تغییر می‌کند"""
        if index >= 0:
            self.current_teacher_id = self.teacher_combo.itemData(index)
            # اگر معلم انتخاب شد، به‌روزرسانی تاریخ‌ها
            if self.current_teacher_id:
                self.update_date_ranges()
    
    def on_year_changed(self, index):
        """وقتی سال تحصیلی تغییر می‌کند"""
        self.update_date_ranges()
    
    def update_date_ranges(self):
        """به‌روزرسانی محدوده تاریخ‌ها بر اساس سال تحصیلی"""
        year_id = self.year_combo.currentData()
        if year_id:
            year = self.academic_year_dal.get_by_id(year_id)
            if year:
                if year.start_date:
                    self.start_date.set_date(year.start_date)
                if year.end_date:
                    self.end_date.set_date(year.end_date)
    
    def generate_report(self):
        """تولید گزارش معلم"""
        teacher_id = self.teacher_combo.currentData()
        if not teacher_id:
            QMessageBox.warning(self, "توجه", "لطفاً یک معلم را انتخاب کنید.")
            return
        
        start_date = self.start_date.get_date_string()
        end_date = self.end_date.get_date_string()
        
        if not start_date or not end_date:
            QMessageBox.warning(self, "توجه", "لطفاً تاریخ شروع و پایان را وارد کنید.")
            return
        
        # دریافت نام معلم
        teacher_name = self.get_teacher_name(teacher_id)
        
        # نمایش نوار پیشرفت
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.set_buttons_enabled(False)
        
        try:
            # تولید گزارش
            self.progress_bar.setValue(20)
            
            # دریافت دانش‌آموزان معلم
            year_id = self.year_combo.currentData()
            assignments = self.assignment_dal.get_by_teacher(teacher_id, year_id)
            
            if not assignments:
                self.progress_bar.setVisible(False)
                self.set_buttons_enabled(True)
                QMessageBox.information(self, "توجه", "هیچ دانش‌آموزی به این معلم اختصاص داده نشده است.")
                return
            
            self.progress_bar.setValue(40)
            
            # دریافت داده‌های هر دانش‌آموز
            report_data = self.collect_report_data(assignments, start_date, end_date)
            
            self.progress_bar.setValue(80)
            
            # ذخیره گزارش
            self.current_report = report_data
            self.current_report['teacher_name'] = teacher_name
            self.current_report['teacher_id'] = teacher_id
            self.current_report['start_date'] = start_date
            self.current_report['end_date'] = end_date
            self.current_report['year_title'] = self.get_year_title(year_id)
            
            # نمایش گزارش
            self.display_report(report_data)
            
            self.progress_bar.setValue(100)
            
            # بررسی داده ناکافی
            if len(assignments) < 2:
                self.insufficient_data_label.setVisible(True)
                self.insufficient_data_label.setText(
                    f"⚠️ داده کافی برای تحلیل کامل وجود ندارد. "
                    f"تعداد دانش‌آموزان: {len(assignments)} (حداقل ۲ مورد نیاز است)"
                )
            else:
                self.insufficient_data_label.setVisible(False)
            
            QMessageBox.information(self, "موفقیت", "گزارش با موفقیت تولید شد.")
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در تولید گزارش:\n{e!s}")
        
        finally:
            self.progress_bar.setVisible(False)
            self.set_buttons_enabled(True)
    
    def collect_report_data(self, assignments, start_date, end_date):
        """جمع‌آوری داده‌های گزارش"""
        data = {
            'total_students': len(assignments),
            'students_data': [],
            'total_observations': 0,
            'positive_observations': 0,
            'negative_observations': 0,
            'neutral_observations': 0,
            'total_interventions': 0,
            'total_followups': 0,
            'pending_followups': 0,
            'competency_stats': {},
            'semester_stats': {'first': {'count': 0, 'positive': 0}, 
                              'second': {'count': 0, 'positive': 0}},
            'trend_data': [],
            'recommendations': {'teacher': [], 'counselor': []}
        }
        
        for assignment in assignments:
            student_id = assignment.student_id
            student = self.student_dal.get_by_id(student_id)
            if not student:
                continue
            
            # دریافت پرونده فعال دانش‌آموز
            profile = self.profile_dal.get_active_by_student(student_id) if hasattr(self, 'profile_dal') else None
            
            if profile:
                # دریافت مشاهدات
                observations = self.observation_dal.get_by_date_range(profile.id, start_date, end_date)
                
                # آمار مشاهدات
                positive = sum(1 for o in observations if o.behavior_type == "مثبت")
                negative = sum(1 for o in observations if o.behavior_type == "منفی")
                neutral = len(observations) - positive - negative
                
                # محاسبه درصد مثبت
                positive_percent = (positive / len(observations) * 100) if observations else 0
                
                # تعیین وضعیت کلی
                if positive_percent >= 70:
                    status = "🟢 خوب"
                elif positive_percent >= 40:
                    status = "🟡 متوسط"
                else:
                    status = "🔴 نیازمند توجه"
                
                student_data = {
                    'student': student,
                    'assignment': assignment,
                    'observations_count': len(observations),
                    'positive': positive,
                    'negative': negative,
                    'neutral': neutral,
                    'positive_percent': positive_percent,
                    'status': status,
                    'observations': observations,
                    'interventions': self.intervention_dal.get_by_student_profile(profile.id) if hasattr(self, 'intervention_dal') else [],
                    'followups': self.followup_dal.get_by_student_profile(profile.id) if hasattr(self, 'followup_dal') else []
                }
                
                data['students_data'].append(student_data)
                
                # جمع‌آوری آمار کلی
                data['total_observations'] += len(observations)
                data['positive_observations'] += positive
                data['negative_observations'] += negative
                data['neutral_observations'] += neutral
                
                # آمار شایستگی‌ها
                for obs in observations:
                    if obs.competency_id:
                        competency = self.competency_dal.get_by_id(obs.competency_id)
                        if competency:
                            key = competency.title
                            if key not in data['competency_stats']:
                                data['competency_stats'][key] = {
                                    'count': 0,
                                    'total_severity': 0,
                                    'positive': 0,
                                    'negative': 0
                                }
                            data['competency_stats'][key]['count'] += 1
                            data['competency_stats'][key]['total_severity'] += obs.severity or 1
                            if obs.behavior_type == "مثبت":
                                data['competency_stats'][key]['positive'] += 1
                            elif obs.behavior_type == "منفی":
                                data['competency_stats'][key]['negative'] += 1
        
        # محاسبه میانگین شایستگی‌ها
        for key in data['competency_stats']:
            if data['competency_stats'][key]['count'] > 0:
                data['competency_stats'][key]['avg_severity'] = round(
                    data['competency_stats'][key]['total_severity'] / 
                    data['competency_stats'][key]['count'], 1
                )
        
        # تولید پیشنهادات
        data['recommendations'] = self.generate_recommendations(data)
        
        return data
    
    def generate_recommendations(self, data):
        """تولید پیشنهادات بر اساس داده‌ها"""
        recommendations = {'teacher': [], 'counselor': []}
        
        # تحلیل شایستگی‌ها
        weak_competencies = []
        strong_competencies = []
        
        # بازرسی یازدهم: قوت/ضعف بر پایهٔ نوع رفتار ثبت‌شده، نه میانگین شدت
        for key, stats in data['competency_stats'].items():
            kind = classify_pattern(
                stats.get('positive', 0), stats.get('negative', 0),
                max(stats.get('count', 0) - stats.get('positive', 0)
                    - stats.get('negative', 0), 0),
                stats.get('count', 0))
            if kind == 'needs_attention':
                weak_competencies.append((key, stats.get('negative', 0), stats.get('count', 0)))
            elif kind == 'strength':
                strong_competencies.append((key, stats.get('positive', 0), stats.get('count', 0)))
        
        # مرتب‌سازی بر پایهٔ تعداد رفتار جهت‌دار
        weak_competencies.sort(key=lambda x: (x[1], x[2]), reverse=True)
        strong_competencies.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        # پیشنهادات برای معلم
        if weak_competencies:
            recommendations['teacher'].append(
                "🔴 زمینه‌های با الگوی تکرارشوندهٔ رفتار منفی در کلاس شما:\n" +
                "\n".join([f"   • {name} ({neg} رفتار منفی از {cnt} مشاهده)"
                          for name, neg, cnt in weak_competencies[:3]]) +
                "\n   پیشنهاد: بررسی این الگوها و طراحی فعالیت‌های هدفمند."
            )
        else:
            recommendations['teacher'].append("✅ وضعیت شایستگی‌های دانش‌آموزان شما خوب است. به روند فعلی ادامه دهید.")
        
        if strong_competencies:
            recommendations['teacher'].append(
                "⭐ شایستگی‌های برتر در کلاس شما:\n" +
                "\n".join([f"   • {name} (میانگین شدت: {avg})" for name, avg in strong_competencies[:3]])
            )
        
        # تحلیل عمومی
        positive_percent = (data['positive_observations'] / data['total_observations'] * 100) if data['total_observations'] > 0 else 0
        
        if positive_percent >= 60:
            recommendations['teacher'].append(
                f"✅ {positive_percent:.0f}% مشاهدات شما مثبت است. این نشان‌دهنده فضای آموزشی مناسب است."
            )
        elif positive_percent >= 40:
            recommendations['teacher'].append(
                f"🟡 {positive_percent:.0f}% مشاهدات شما مثبت است. با تقویت رفتارهای مثبت می‌توانید این عدد را افزایش دهید."
            )
        else:
            recommendations['teacher'].append(
                f"🔴 {positive_percent:.0f}% مشاهدات شما مثبت است. بررسی علل و تغییر رویکرد آموزشی توصیه می‌شود."
            )
        
        # پیشنهادات برای مشاور
        if data['total_students'] >= 5 and data['total_observations'] >= 20:
            recommendations['counselor'].append(
                f"📊 این معلم {data['total_students']} دانش‌آموز دارد و {data['total_observations']} مشاهده ثبت شده است. "
                f"بررسی الگوهای رفتاری کلاس می‌تواند مفید باشد."
            )
        
        if data['pending_followups'] > 0:
            recommendations['counselor'].append(
                f"🔔 {data['pending_followups']} پیگیری باز وجود دارد. هماهنگی با معلم برای پیگیری‌های معوق توصیه می‌شود."
            )
        
        return recommendations
    
    def display_report(self, data):
        """نمایش گزارش"""
        # خلاصه
        self.display_summary(data)
        
        # شایستگی‌ها
        self.display_competencies(data)
        
        # دانش‌آموزان
        self.display_students(data)
        
        # نمودار
        self.draw_chart(data)
        
        # پیشنهادات
        self.display_recommendations(data)
    
    def display_summary(self, data):
        """نمایش خلاصه گزارش"""
        total = data['total_observations']
        positive = data['positive_observations']
        negative = data['negative_observations']
        neutral = data['neutral_observations']
        positive_percent = (positive / total * 100) if total > 0 else 0
        
        summary = f"""
📊 **گزارش عملکرد معلم**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **اطلاعات معلم**
• نام: {self.current_report.get('teacher_name', 'نامشخص')}
• تعداد دانش‌آموزان: {data['total_students']} نفر
• بازه زمانی: {self.current_report.get('start_date', '')} تا {self.current_report.get('end_date', '')}
• سال تحصیلی: {self.current_report.get('year_title', 'همه سال‌ها')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **آمار کلی**
• کل مشاهدات: {total}
• مشاهدات مثبت: {positive} ({positive_percent:.1f}%)
• مشاهدات منفی: {negative} ({negative/total*100 if total > 0 else 0:.1f}%)
• مشاهدات خنثی: {neutral} ({neutral/total*100 if total > 0 else 0:.1f}%)
• مداخلات ثبت‌شده: {data['total_interventions']}
• پیگیری‌های باز: {data['pending_followups']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **تحلیل وضعیت کلاس**
"""
        if positive_percent >= 60:
            summary += "✅ وضعیت کلاس مطلوب است. فضای آموزشی مثبت و سازنده حاکم است."
        elif positive_percent >= 40:
            summary += "🟡 وضعیت کلاس متوسط است. با تلاش بیشتر می‌توان به بهبود کمک کرد."
        else:
            summary += "🔴 وضعیت کلاس نیازمند توجه ویژه است. بررسی و تغییر رویکرد توصیه می‌شود."
        
        self.summary_text.setText(summary)
    
    def display_competencies(self, data):
        """نمایش شایستگی‌ها"""
        stats = data['competency_stats']
        self.competency_table.setRowCount(len(stats))
        
        for row, (name, stat) in enumerate(stats.items()):
            self.competency_table.setItem(row, 0, QTableWidgetItem(name))
            self.competency_table.setItem(row, 1, QTableWidgetItem(str(stat.get('avg_severity', 0))))
            self.competency_table.setItem(row, 2, QTableWidgetItem(str(stat['count'])))
            
            # بازرسی یازدهم: وضعیت بر پایهٔ الگوی رفتار ثبت‌شده، نه شدت
            kind = classify_pattern(
                stat.get('positive', 0), stat.get('negative', 0),
                max(stat.get('count', 0) - stat.get('positive', 0)
                    - stat.get('negative', 0), 0),
                stat.get('count', 0))
            if kind == 'strength':
                status = "✅ " + pattern_label(kind)
                color = QColor(0, 128, 0)
            elif kind == 'needs_attention':
                status = "🔴 " + pattern_label(kind)
                color = QColor(255, 0, 0)
            elif kind == 'mixed':
                status = "🟠 " + pattern_label(kind)
                color = QColor(255, 140, 0)
            else:
                status = "⬜ " + pattern_label(kind)
                color = QColor(158, 158, 158)
            
            item = QTableWidgetItem(status)
            item.setForeground(color)
            self.competency_table.setItem(row, 3, item)
            self.competency_table.setRowHeight(row, 30)
    
    def display_students(self, data):
        """نمایش لیست دانش‌آموزان"""
        students = data['students_data']
        self.students_table.setRowCount(len(students))
        
        for row, s in enumerate(students):
            self.students_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.students_table.setItem(row, 1, QTableWidgetItem(s['student'].full_name))
            self.students_table.setItem(row, 2, QTableWidgetItem(str(s['assignment'].grade) if s['assignment'].grade else "-"))
            self.students_table.setItem(row, 3, QTableWidgetItem(s['assignment'].class_name or "-"))
            self.students_table.setItem(row, 4, QTableWidgetItem(str(s['observations_count'])))
            
            status_item = QTableWidgetItem(s['status'])
            if "خوب" in s['status']:
                status_item.setBackground(QColor(200, 255, 200))
            elif "متوسط" in s['status']:
                status_item.setBackground(QColor(255, 255, 200))
            else:
                status_item.setBackground(QColor(255, 200, 200))
            self.students_table.setItem(row, 5, status_item)
            self.students_table.setRowHeight(row, 30)
    
    def draw_chart(self, data):
        """رسم نمودارها"""
        self.figure.clear()
        
        stats = data['competency_stats']
        if not stats:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'هیچ داده‌ای برای نمایش وجود ندارد',
                   ha='center', va='center', fontsize=14)
            ax.set_xticks([])
            ax.set_yticks([])
            self.canvas.draw()
            return
        
        # نمودار میله‌ای ترکیب رفتارها (بازرسی یازدهم: به‌جای میانگین شدت)
        items = sorted(
            stats.items(),
            key=lambda x: (x[1].get('positive', 0) + x[1].get('negative', 0),
                           x[1].get('count', 0)),
            reverse=True)[:10]
        
        names = [item[0][:15] for item in items]
        positions = range(len(names))
        positive_values = [item[1].get('positive', 0) for item in items]
        negative_values = [item[1].get('negative', 0) for item in items]
        
        ax = self.figure.add_subplot(111)
        ax.bar([p - 0.2 for p in positions], positive_values, width=0.4,
               color='#66BB6A', label='رفتار مثبت')
        ax.bar([p + 0.2 for p in positions], negative_values, width=0.4,
               color='#C62828', label='رفتار منفی')
        ax.set_xticks(list(positions))
        ax.set_xticklabels(names)
        ax.set_ylabel('تعداد رفتار ثبت‌شده', fontsize=12)
        ax.set_xlabel('زمینه (شایستگی)', fontsize=12)
        ax.set_title('ترکیب رفتارهای ثبت‌شده در کلاس (بدون رتبه‌بندی دانش‌آموزان)',
                     fontsize=13, fontweight='bold')
        ax.legend(fontsize=8)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def display_recommendations(self, data):
        """نمایش پیشنهادات"""
        recs = data['recommendations']
        
        text = """
💡 **پیشنهادات بر اساس داده‌های موجود**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**👨‍🏫 پیشنهادات برای معلم:**
"""
        for rec in recs.get('teacher', []):
            text += f"\n{rec}\n"
        
        text += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🫂 پیشنهادات برای مشاور:**
"""
        for rec in recs.get('counselor', []):
            text += f"\n{rec}\n"
        
        if not recs.get('counselor'):
            text += "\n✅ وضعیت عمومی مطلوب است. نیاز به مداخله خاصی نیست."
        
        self.recommendations_text.setText(text)
    
    def on_student_double_clicked(self, item):
        """وقتی دانش‌آموز دابل‌کلیک می‌شود"""
        row = item.row()
        if row < len(self.current_report['students_data']):
            student_data = self.current_report['students_data'][row]
            student = student_data['student']
            QMessageBox.information(
                self,
                f"اطلاعات {student.full_name}",
                f"""
👤 **دانش‌آموز:** {student.full_name}
📚 **پایه:** {student_data['assignment'].grade or 'نامشخص'}
🏫 **کلاس:** {student_data['assignment'].class_name or 'نامشخص'}
📊 **تعداد مشاهدات:** {student_data['observations_count']}
✅ **مثبت:** {student_data['positive']}
❌ **منفی:** {student_data['negative']}
📈 **درصد مثبت:** {student_data['positive_percent']:.1f}%
📌 **وضعیت کلی:** {student_data['status']}
"""
            )
    
    def get_teacher_name(self, teacher_id):
        """دریافت نام معلم"""
        try:
            teacher = self.staff_dal.get_by_id(teacher_id)
            return teacher.full_name if teacher else "نامشخص"
        except Exception:
            return "نامشخص"
    
    def get_year_title(self, year_id):
        """دریافت عنوان سال تحصیلی"""
        if not year_id:
            return "همه سال‌ها"
        try:
            year = self.academic_year_dal.get_by_id(year_id)
            return year.title if year else "نامشخص"
        except Exception:
            return "نامشخص"
    
    def set_buttons_enabled(self, enabled):
        """فعال/غیرفعال کردن دکمه‌ها"""
        self.generate_btn.setEnabled(enabled)
        self.excel_btn.setEnabled(enabled)
        self.pdf_btn.setEnabled(enabled)
    
    def export_excel(self):
        """خروجی Excel"""
        if not self.current_report:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا یک گزارش تولید کنید.")
            return
        
        teacher_name = self.current_report.get('teacher_name', 'نامشخص')
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل Excel",
            f"گزارش_معلم_{teacher_name}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            self.report_service.export_to_excel(self.current_report, file_path)
            QMessageBox.information(self, "موفقیت", f"فایل Excel با موفقیت در {file_path} ذخیره شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در خروجی Excel:\n{e!s}")
    
    def export_pdf(self):
        """خروجی PDF گزارش معلم"""
        if not self.current_report:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا یک گزارش تولید کنید.")
            return
        
        teacher_name = self.current_report.get('teacher_name', 'نامشخص')
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل PDF",
            f"گزارش_معلم_{teacher_name}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return
        
        try:
            # استفاده از سرویس به روز شده
            self.report_service.export_to_pdf(self.current_report, file_path)
            QMessageBox.information(self, "موفقیت", f"فایل PDF با موفقیت در {file_path} ذخیره شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در خروجی PDF:\n{e!s}")