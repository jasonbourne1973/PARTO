"""
صفحه تولید و نمایش گزارش‌ها - نسخه نهایی با قابلیت ردیابی و انتخاب سال تحصیلی و معلم
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
    QLineEdit,
    QMessageBox,
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
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from services.case_timeline_service import CaseTimelineService
from services.report_generator import ReportGenerator
from views.pages.class_report_page import ClassReportPage
from views.pages.teacher_performance_page import TeacherPerformancePage
from views.pages.teacher_report_page import TeacherReportPage

matplotlib.use('QtAgg')
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from utils.logger import get_logger

logger = get_logger(__name__)


class ReportsPage(QWidget):
    """صفحه تولید گزارش‌ها با قابلیت ردیابی و انتخاب سال تحصیلی و معلم"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.competency_dal = CompetencyDAL()
        self.staff_dal = StaffDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        self.report_generator = ReportGenerator()
        self.timeline_service = CaseTimelineService()
        
        self.current_student_id = None
        self.current_profile_id = None
        self.current_report = None
        self.all_students = []
        self.all_academic_years = []
        self.all_teachers = []
        self.selected_teacher_id = None
        
        self.setup_ui()
        self.load_students()
        self.load_academic_years()
        self.load_teachers()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        title_label = QLabel("📄 گزارش‌ها")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        toolbar.addWidget(title_label)
        toolbar.addStretch()
        
        # ===== انتخاب معلم =====
        toolbar.addWidget(QLabel("معلم:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.setMinimumWidth(150)
        self.teacher_combo.addItem("همه معلمان", None)
        self.teacher_combo.currentIndexChanged.connect(self.on_teacher_changed)
        toolbar.addWidget(self.teacher_combo)
        
        # ===== انتخاب دانش‌آموز =====
        toolbar.addWidget(QLabel("دانش‌آموز:"))
        self.student_combo = QComboBox()
        self.student_combo.setMinimumWidth(200)
        self.student_combo.addItem("انتخاب دانش‌آموز...", None)
        self.student_combo.currentIndexChanged.connect(self.load_report)
        toolbar.addWidget(self.student_combo)
        
        # ===== جستجوی دانش‌آموز =====
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
        
        # ===== انتخاب سال تحصیلی =====
        toolbar.addWidget(QLabel("سال تحصیلی:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(150)
        self.year_combo.addItem("همه سال‌ها", None)
        self.year_combo.currentIndexChanged.connect(self.load_report)
        toolbar.addWidget(self.year_combo)
        
        # ===== دکمه‌ها =====
        self.parent_btn = QPushButton("👨‍👩‍👦 گزارش والدین")
        self.parent_btn.setStyleSheet("""
            QPushButton {
                background-color: #F4D35E;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #F28C28; }
        """)
        self.parent_btn.clicked.connect(self.show_parent_report)
        toolbar.addWidget(self.parent_btn)
        
        self.excel_btn = QPushButton("📊 خروجی Excel")
        self.excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.excel_btn.clicked.connect(self.export_excel)
        toolbar.addWidget(self.excel_btn)
        
        layout.addLayout(toolbar)

        self.pdf_btn = QPushButton("📄 خروجی PDF")
        self.pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #9E1B1B; }
        """)
        self.pdf_btn.clicked.connect(self.export_pdf)
        toolbar.addWidget(self.pdf_btn)

        # دکمه خروجی برای هوش مصنوعی
        self.ai_export_btn = QPushButton("🤖 خروجی برای هوش مصنوعی")
        self.ai_export_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7d3c98; }
        """)
        self.ai_export_btn.clicked.connect(self.export_for_ai)
        toolbar.addWidget(self.ai_export_btn)

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
        self.tabs.addTab(self.create_traceability_tab(), "🔗 ردیابی")
        self.tabs.addTab(self.create_observations_tab(), "📝 مشاهدات")
        self.tabs.addTab(self.create_interventions_tab(), "🛠️ مداخلات")
        self.tabs.addTab(self.create_followups_tab(), "🔔 پیگیری‌ها")
        self.tabs.addTab(self.create_chart_tab(), "📈 نمودار")
        
        self.teacher_report_page = TeacherReportPage(embedded=True)
        self.tabs.addTab(self.teacher_report_page, "📊 گزارش معلم")

        # گزارش‌های مدیریتی به‌صورت تب داخلی همین صفحه نمایش داده می‌شوند؛
        # بنابراین منوی اصلی فقط یک گزینه «گزارش‌ها» دارد.
        self.class_report_page = ClassReportPage(self)
        self.tabs.addTab(self.class_report_page, "📊 گزارش کلاس")

        self.teacher_performance_page = TeacherPerformancePage(self)
        self.tabs.addTab(self.teacher_performance_page, "📈 عملکرد معلم")

        layout.addWidget(self.tabs)
    
    # ===== بارگذاری معلمان =====
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
                # همه دانش‌آموزان
                self.all_students = self.student_dal.get_all()
                for student in self.all_students:
                    display_text = f"{student.full_name}"
                    self.student_combo.addItem(display_text, student.id)
        except Exception as e:
            logger.error(f"خطا در بارگذاری دانش‌آموزان معلم: {e}")
    
    def load_academic_years(self):
        """بارگذاری سال‌های تحصیلی در کامبوباکس"""
        try:
            self.all_academic_years = self.academic_year_dal.get_all(include_archived=True)
            self.year_combo.clear()
            self.year_combo.addItem("همه سال‌ها", None)
            for year in self.all_academic_years:
                display_text = f"{year.title} {'(بایگانی)' if year.is_archived == 1 else ''}"
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
    
    def load_students(self):
        """بارگذاری دانش‌آموزان در کامبوباکس"""
        try:
            self.all_students = self.student_dal.get_all()
            self.student_combo.clear()
            self.student_combo.addItem("انتخاب دانش‌آموز...", None)
            for student in self.all_students:
                display_text = f"{student.full_name}"
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
    
    def get_student_name(self):
        """دریافت نام دانش‌آموز فعلی"""
        if not self.current_student_id:
            return "نامشخص"
        try:
            student = self.student_dal.get_by_id(self.current_student_id)
            return student.full_name if student else "نامشخص"
        except Exception:
            return "نامشخص"
    
    def load_report(self):
        """بارگذاری گزارش برای دانش‌آموز انتخاب شده با فیلتر سال"""
        student_id = self.student_combo.currentData()
        year_id = self.year_combo.currentData()
        
        if student_id is None:
            self.clear_report()
            return
        
        self.current_student_id = student_id
        
        try:
            if year_id:
                profile = self.profile_dal.get_by_student_and_year(student_id, year_id)
                if not profile:
                    self.clear_report()
                    self.summary_text.setText("⚠️ دانش‌آموز در سال تحصیلی انتخاب شده پرونده‌ای ندارد.")
                    self.insufficient_data_label.setVisible(True)
                    self.insufficient_data_label.setText("⚠️ پرونده‌ای برای سال تحصیلی انتخاب شده وجود ندارد.")
                    return
            else:
                profile = self.profile_dal.get_active_by_student(student_id)
                if not profile:
                    self.clear_report()
                    self.summary_text.setText("⚠️ هیچ پرونده فعالی برای این دانش‌آموز وجود ندارد.")
                    self.insufficient_data_label.setVisible(True)
                    self.insufficient_data_label.setText("⚠️ پرونده فعالی برای این دانش‌آموز وجود ندارد.")
                    return
            
            self.current_profile_id = profile.id
            
            report = self.report_generator.generate_student_report(profile.id)
            if not report:
                self.clear_report()
                self.summary_text.setText("⚠️ امکان تولید گزارش وجود ندارد.")
                return
            
            self.current_report = report
            self.display_report(report)
            
            if report['observations_count'] < 3:
                self.insufficient_data_label.setVisible(True)
                self.insufficient_data_label.setText(
                    f"⚠️ داده کافی برای تحلیل روند وجود ندارد. "
                    f"تعداد مشاهدات ثبت‌شده: {report['observations_count']} (حداقل ۳ مورد نیاز است)"
                )
            else:
                self.insufficient_data_label.setVisible(False)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در تولید گزارش:\n{e!s}")
    
    def clear_report(self):
        """پاک کردن گزارش"""
        self.summary_text.setText("⚠️ لطفاً یک دانش‌آموز را انتخاب کنید.")
        self.obs_table.setRowCount(0)
        self.inter_table.setRowCount(0)
        self.follow_table.setRowCount(0)
        self.traceability_table.setRowCount(0)
        self.figure.clear()
        self.canvas.draw()
        self.current_report = None
        self.insufficient_data_label.setVisible(False)
    
    def display_report(self, report):
        """نمایش گزارش"""
        student = report['student']
        profile = report['profile']
        academic_year = report['academic_year']
        
        summary_text = self.generate_summary_text(report, student, profile, academic_year)
        self.summary_text.setText(summary_text)
        
        self.display_observations(report['observations'])
        self.display_interventions(report['interventions'])
        self.display_followups(report['followups'])
        self.display_traceability(report)
        self.draw_chart(report)
    
    # ===== تب خلاصه =====
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
        self.summary_text.setPlaceholderText("پس از انتخاب دانش‌آموز، خلاصه گزارش اینجا نمایش داده می‌شود...")
        scroll.setWidget(self.summary_text)
        layout.addWidget(scroll)
        
        return tab
    
    def generate_summary_text(self, report, student, profile, academic_year):
        """تولید متن خلاصه گزارش"""
        text = f"""
📋 **گزارش پرونده سالانه دانش‌آموز**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**👤 اطلاعات دانش‌آموز**
• نام: {student.full_name}
• پایه: {profile.grade_display}
• کلاس: {profile.class_name or '-'}
• سال تحصیلی: {academic_year.title if academic_year else '-'}
• شناسه پرونده: {profile.id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📊 خلاصه آماری**
• تعداد مشاهدات: {report['observations_count']}
• تعداد مداخلات: {report['interventions_count']}
• تعداد پیگیری‌ها: {report['followups_count']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**⭐ توانمندی‌ها (الگوی تکرارشوندهٔ رفتار مثبت)**
"""
        # بازرسی یازدهم: معیار قوت/ضعف «نوع رفتار ثبت‌شده» است، نه شدت.
        if report['strengths']:
            for strength in report['strengths']:
                text += (f"• {strength['competency']} — "
                         f"{strength['positive']} رفتار مثبت از "
                         f"{strength['count']} مشاهدهٔ ثبت‌شده\n")
        else:
            text += "• الگوی تکرارشوندهٔ رفتار مثبت ثبت نشده است.\n"
        
        text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🔴 زمینه‌های نیازمند توجه (الگوی تکرارشوندهٔ رفتار منفی)**
"""
        if report['weaknesses']:
            for weakness in report['weaknesses']:
                text += (f"• {weakness['competency']} — "
                         f"{weakness['negative']} رفتار منفی از "
                         f"{weakness['count']} مشاهدهٔ ثبت‌شده\n")
        else:
            text += "• الگوی تکرارشوندهٔ رفتار منفی ثبت نشده است.\n"
        text += ("• توجه: این فهرست بر پایهٔ رفتارهای ثبت‌شده است و "
                 "به‌معنای تشخیص یا برچسب نیست.\n")
        
        text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**💡 پیشنهادات**

**👨‍🏫 به معلم:**
"""
        for rec in report['recommendations']['teacher']:
            text += f"• {rec}\n"
        
        text += """
**👨‍👩‍👦 به والدین:**
"""
        for rec in report['recommendations']['parents']:
            text += f"• {rec}\n"
        
        text += """
**🫂 به مشاور:**
"""
        for rec in report['recommendations']['counselor']:
            text += f"• {rec}\n"
        
        if report['trend_data']:
            direction = self.report_generator.calculate_trend_direction(report['trend_data'])
            text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📈 روند تغییر رفتار (بر پایهٔ ترکیب رفتارها)**
"""
            for item in report['trend_data']:
                text += (f"• {item['month']}: {item['positive']} مثبت، "
                         f"{item['negative']} منفی، {item['neutral']} خنثی "
                         f"(سهم مثبت {item['positive_share']}٪) — "
                         f"حجم ثبت: {item['count']} مشاهده\n")
            text += f"• جهت تغییر: {direction['label']} — {direction['message']}\n"
            # بازرسی سیزدهم: مسیر بین بازه‌ها هم نشان داده می‌شود تا روشن
            # باشد نتیجه فقط از مقایسهٔ اولین و آخرین بازه گرفته نشده است.
            if direction.get('path_text'):
                text += f"• مسیر تغییر بین بازه‌ها: {direction['path_text']}\n"
            for caution in direction.get('caution_notes') or []:
                text += f"• ⚠️ {caution}\n"
            text += f"• {direction['volume_note']}\n"
        else:
            text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📈 روند تغییر رفتار**
⚠️ داده کافی برای تحلیل روند وجود ندارد (حداقل ۳ مشاهده در بازه‌های مختلف مورد نیاز است).
"""
        
        if report['semester_stats']:
            stats = report['semester_stats']
            text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📊 مقایسه نیمسال‌ها (بر پایهٔ ترکیب رفتارها)**
• نیمسال اول: {stats['first']['positive']} مثبت، {stats['first']['negative']} منفی از {stats['first']['count']} مشاهده (سهم مثبت {stats['first'].get('positive_share', 0)}٪)
• نیمسال دوم: {stats['second']['positive']} مثبت، {stats['second']['negative']} منفی از {stats['second']['count']} مشاهده (سهم مثبت {stats['second'].get('positive_share', 0)}٪)
• جهت تغییر رفتار: {stats.get('trend', '-')}
• {stats.get('volume_note', '')}
"""
        
        # ===== اثربخشی مداخلات (اقدام ← پیگیری ← نتیجه) =====
        effectiveness = report.get('intervention_effectiveness') or {}
        if effectiveness.get('items'):
            text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🔗 اثربخشی مداخلات (اقدام ← پیگیری ← نتیجه)**
"""
            for item in effectiveness['items'][:10]:
                text += f"• {item['type']} ({item['date'] or '-'}): {item['outcome']}\n"
                if item.get('goal'):
                    text += f"   هدف: {item['goal']}\n"
                for follow in item['followups'][:2]:
                    text += (f"   پیگیری {follow['date'] or ''} "
                             f"({follow['method']}): {follow['result_label']}\n")
            text += f"• {effectiveness['summary']}\n"

        # ===== زمینهٔ خانوادگی (اطلاعات زمینه‌ای، نه قضاوت) =====
        family = report.get('family_background') or {}
        if family.get('contexts') or family.get('interviews'):
            text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**👨‍👩‍👦 زمینهٔ خانوادگی (اطلاعات زمینه‌ای)
"""
            text += f"• {family.get('note', '')}\n"
            for ctx in family['contexts'][:2]:
                text += (f"• وضعیت سرپرست: {ctx['guardian_status']} | "
                         f"حمایت والدین: {ctx['parental_support']} | "
                         f"فضای مطالعه: {ctx['study_space']}\n")
            for iv in family['interviews'][:3]:
                text += (f"• گفت‌وگو {iv['date'] or ''} ({iv['method']}) — "
                         f"{iv['topic'] or 'بدون موضوع'} | وضعیت: {iv['status']}\n")

        # ===== لایه‌های اطلاعاتی (تفکیک مشاهده/غربالگری/تفسیر) =====
        layers = report.get('information_layers') or {}
        if layers:
            text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🧭 لایه‌های اطلاعاتی (مشاهده / غربالگری / تفسیر حرفه‌ای)**
"""
            text += f"• {layers.get('chain_note', '')}\n"
            obs_layer = layers.get('observation', {})
            text += f"• {obs_layer.get('title', '')}: {obs_layer.get('note', '')}\n"
            scr = layers.get('screening', {})
            if scr.get('items'):
                for item in scr['items'][:3]:
                    text += (f"• غربالگری: {item['tool']} — {item['date'] or ''} | "
                             f"وضعیت: {item['status']} | {item['note']}\n")
            else:
                text += "• غربالگری: نتیجه‌ای ثبت نشده است.\n"
            text += f"  {scr.get('note', '')}\n"
            interp = layers.get('interpretation', {})
            if interp.get('items'):
                for item in interp['items'][:3]:
                    text += (f"• تفسیر حرفه‌ای [{item['level']}]: {item['title']} "
                             f"— {item['status']}\n")
            else:
                text += "• تفسیر حرفه‌ای: ثبت نشده است.\n"
            text += f"  {interp.get('note', '')}\n"
        
        # ===== سابقهٔ رشد چندساله (بازرسی دوازدهم → تکمیل سیزدهم) =====
        # گزارش معمول برنامه همان روایت منسجم PDF/Excel را با رندر مشترک
        # نشان می‌دهد: مسیر سال‌به‌سال، الگوهای ادامه‌دار، زمینه‌های
        # تغییریافته (با جهت)، مداخلات مؤثرتر بر اساس پیگیری و جمع‌بندی.
        growth = report.get('growth_narrative') or {}
        if growth.get('has_data'):
            text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🌱 سابقهٔ رشد و مسیر طی‌شده (چندساله — مقایسهٔ دانش‌آموز با خودش)**
"""
            for kind, line in self.report_generator.growth_narrative_lines(growth):
                if kind == 'heading':
                    text += f"\n**{line}**\n"
                elif kind == 'bullet':
                    text += f"• {line}\n"
                else:
                    text += f"{line}\n"

        text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📝 جمع‌بندی سالانهٔ رشد**
{report['summary']}
"""

        return text
    
    # ===== تب ردیابی =====
    def create_traceability_tab(self):
        """ایجاد تب ردیابی"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        info_label = QLabel("🔗 قابلیت ردیابی - کلیک روی هر شناسه، رکورد اصلی را نمایش می‌دهد")
        info_label.setStyleSheet("font-size: 13px; color: #D9C36A; padding: 5px;")
        layout.addWidget(info_label)
        
        self.traceability_table = QTableWidget()
        self.traceability_table.setColumnCount(4)
        self.traceability_table.setHorizontalHeaderLabels(["نوع", "شناسه", "تاریخ", "توضیح"])
        self.traceability_table.setAlternatingRowColors(True)
        self.traceability_table.setStyleSheet("""
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
        
        header = self.traceability_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        self.traceability_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.traceability_table)
        
        return tab
    
    def display_traceability(self, report):
        """نمایش داده‌های ردیابی"""
        records = []
        
        for obs in report.get('observations', []):
            records.append({
                'type': 'مشاهده',
                'id': obs.id,
                'date': obs.observation_date,
                'description': obs.description[:50] + '...' if obs.description and len(obs.description) > 50 else obs.description or ''
            })
        
        for inter in report.get('interventions', []):
            records.append({
                'type': 'مداخله',
                'id': inter.id,
                'date': inter.date,
                'description': inter.description[:50] + '...' if inter.description and len(inter.description) > 50 else inter.description or ''
            })
        
        for follow in report.get('followups', []):
            records.append({
                'type': 'پیگیری',
                'id': follow.id,
                'date': follow.date,
                'description': follow.result_description[:50] + '...' if follow.result_description and len(follow.result_description) > 50 else follow.result_description or ''
            })
        
        records.sort(key=lambda x: x['date'] or '')
        
        self.traceability_table.setRowCount(len(records))
        
        for row, record in enumerate(records):
            type_item = QTableWidgetItem(record['type'])
            if record['type'] == 'مشاهده':
                type_item.setBackground(QColor(200, 230, 255))
            elif record['type'] == 'مداخله':
                type_item.setBackground(QColor(255, 220, 200))
            else:
                type_item.setBackground(QColor(220, 200, 255))
            self.traceability_table.setItem(row, 0, type_item)
            
            id_item = QTableWidgetItem(str(record['id']))
            id_item.setForeground(QColor(52, 152, 219))
            id_item.setToolTip("برای مشاهده جزئیات، دابل‌کلیک کنید")
            self.traceability_table.setItem(row, 1, id_item)
            
            self.traceability_table.setItem(row, 2, QTableWidgetItem(record['date'] or 'نامشخص'))
            self.traceability_table.setItem(row, 3, QTableWidgetItem(record['description']))
    
    # ===== تب مشاهدات =====
    def create_observations_tab(self):
        """ایجاد تب مشاهدات"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.obs_table = QTableWidget()
        self.obs_table.setColumnCount(7)
        self.obs_table.setHorizontalHeaderLabels(["شناسه", "تاریخ", "محیط", "شایستگی", "نوع", "شدت", "شرح"])
        self.obs_table.setAlternatingRowColors(True)
        self.obs_table.setStyleSheet("""
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
        
        header = self.obs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        
        self.obs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.obs_table.itemDoubleClicked.connect(self.on_traceability_clicked)
        layout.addWidget(self.obs_table)
        
        return tab
    
    def display_observations(self, observations):
        """نمایش مشاهدات در جدول با شناسه"""
        self.obs_table.setRowCount(len(observations))
        
        # عنوان شایستگی‌ها یک‌جا خوانده می‌شود (رفع N+1)
        comp_titles = self.competency_dal.get_titles_by_ids(
            o.competency_id for o in observations)
        for row, obs in enumerate(observations):
            id_item = QTableWidgetItem(str(obs.id))
            id_item.setForeground(QColor(52, 152, 219))
            id_item.setToolTip("برای مشاهده جزئیات، دابل‌کلیک کنید")
            self.obs_table.setItem(row, 0, id_item)
            
            self.obs_table.setItem(row, 1, QTableWidgetItem(obs.observation_date or ""))
            self.obs_table.setItem(row, 2, QTableWidgetItem(obs.location or ""))
            
            comp_name = comp_titles.get(obs.competency_id) or "نامشخص"
            self.obs_table.setItem(row, 3, QTableWidgetItem(comp_name))
            
            type_item = QTableWidgetItem(obs.behavior_type or "خنثی")
            if obs.behavior_type == "مثبت":
                type_item.setBackground(QColor(200, 255, 200))
            elif obs.behavior_type == "منفی":
                type_item.setBackground(QColor(255, 200, 200))
            self.obs_table.setItem(row, 4, type_item)
            
            self.obs_table.setItem(row, 5, QTableWidgetItem("⭐" * obs.severity))
            
            desc_text = obs.description[:60] + "..." if obs.description and len(obs.description) > 60 else obs.description or ""
            self.obs_table.setItem(row, 6, QTableWidgetItem(desc_text))
    
    # ===== تب مداخلات =====
    def create_interventions_tab(self):
        """ایجاد تب مداخلات"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.inter_table = QTableWidget()
        self.inter_table.setColumnCount(6)
        self.inter_table.setHorizontalHeaderLabels(["شناسه", "تاریخ", "نوع", "مسئول", "وضعیت", "نتیجه"])
        self.inter_table.setAlternatingRowColors(True)
        self.inter_table.setStyleSheet("""
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
        
        header = self.inter_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        
        self.inter_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.inter_table.itemDoubleClicked.connect(self.on_traceability_clicked)
        layout.addWidget(self.inter_table)
        
        return tab
    
    def display_interventions(self, interventions):
        """نمایش مداخلات در جدول با شناسه"""
        self.inter_table.setRowCount(len(interventions))
        
        # نام کادر یک‌جا خوانده می‌شود (رفع N+1)
        staff_names = self.staff_dal.get_names_by_ids(
            x.staff_id for x in interventions)
        for row, inter in enumerate(interventions):
            id_item = QTableWidgetItem(str(inter.id))
            id_item.setForeground(QColor(230, 126, 34))
            id_item.setToolTip("برای مشاهده جزئیات، دابل‌کلیک کنید")
            self.inter_table.setItem(row, 0, id_item)
            
            self.inter_table.setItem(row, 1, QTableWidgetItem(inter.date or ""))
            self.inter_table.setItem(row, 2, QTableWidgetItem(inter.type_display))
            
            staff_name = staff_names.get(inter.staff_id) or "نامشخص"
            self.inter_table.setItem(row, 3, QTableWidgetItem(staff_name))
            
            self.inter_table.setItem(row, 4, QTableWidgetItem(inter.status_display))
            self.inter_table.setItem(row, 5, QTableWidgetItem(inter.result or "نامشخص"))
    
    # ===== تب پیگیری‌ها =====
    def create_followups_tab(self):
        """ایجاد تب پیگیری‌ها"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.follow_table = QTableWidget()
        self.follow_table.setColumnCount(6)
        self.follow_table.setHorizontalHeaderLabels(["شناسه", "تاریخ", "مسئول", "وضعیت", "نوع نتیجه", "نتیجه"])
        self.follow_table.setAlternatingRowColors(True)
        self.follow_table.setStyleSheet("""
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
        
        header = self.follow_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        
        self.follow_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.follow_table.itemDoubleClicked.connect(self.on_traceability_clicked)
        layout.addWidget(self.follow_table)
        
        return tab
    
    def display_followups(self, followups):
        """نمایش پیگیری‌ها در جدول با شناسه"""
        self.follow_table.setRowCount(len(followups))
        
        # نام کادر یک‌جا خوانده می‌شود (رفع N+1)
        staff_names = self.staff_dal.get_names_by_ids(
            x.staff_id for x in followups)
        for row, follow in enumerate(followups):
            id_item = QTableWidgetItem(str(follow.id))
            id_item.setForeground(QColor(142, 68, 173))
            id_item.setToolTip("برای مشاهده جزئیات، دابل‌کلیک کنید")
            self.follow_table.setItem(row, 0, id_item)
            
            self.follow_table.setItem(row, 1, QTableWidgetItem(follow.date or ""))
            
            staff_name = staff_names.get(follow.staff_id) or "نامشخص"
            self.follow_table.setItem(row, 2, QTableWidgetItem(staff_name))
            
            self.follow_table.setItem(row, 3, QTableWidgetItem(follow.status_display))
            self.follow_table.setItem(row, 4, QTableWidgetItem(follow.result_type_display))
            self.follow_table.setItem(row, 5, QTableWidgetItem(follow.result_description or "نامشخص"))
    
    # ===== تب نمودار =====
    def create_chart_tab(self):
        """ایجاد تب نمودار"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #0B2E4F; border: 1px solid #D9C36A; border-radius: 5px;")
        layout.addWidget(self.canvas)
        
        return tab
    
    def draw_chart(self, report):
        """رسم نمودار"""
        self.figure.clear()
        
        if not report['competency_stats']:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'هیچ داده‌ای برای نمایش وجود ندارد',
                   ha='center', va='center', fontsize=14)
            ax.set_xticks([])
            ax.set_yticks([])
            self.canvas.draw()
            return
        
        # ===== اصلاح (بازرسی یازدهم) =====
        # پیش از این، نمودار بر پایهٔ «میانگین شدت» کشیده می‌شد؛ اکنون
        # ترکیب رفتارهای مثبت/منفی هر زمینه نمایش داده می‌شود. شدت در
        # تحلیل نقش تصمیم‌گیر ندارد.
        stats = report['competency_stats']
        items = sorted(stats.items(),
                       key=lambda x: ((x[1].get('positive', 0) + x[1].get('negative', 0)),
                                      x[1].get('count', 0)),
                       reverse=True)[:8]
        
        names = [item[0][:12] for item in items]
        positive_values = [item[1].get('positive', 0) for item in items]
        negative_values = [item[1].get('negative', 0) for item in items]
        
        if len(names) < 3:
            ax = self.figure.add_subplot(111)
            positions = range(len(names))
            ax.bar([p - 0.2 for p in positions], positive_values, width=0.4,
                   color='#66BB6A', label='رفتار مثبت')
            ax.bar([p + 0.2 for p in positions], negative_values, width=0.4,
                   color='#C62828', label='رفتار منفی')
            ax.set_xticks(list(positions))
            ax.set_xticklabels(names)
            ax.set_ylabel('تعداد رفتار ثبت‌شده')
            ax.set_title('ترکیب رفتارهای ثبت‌شده به تفکیک زمینه', fontsize=13,
                         fontweight='bold')
            ax.legend()
            self.figure.tight_layout()
            self.canvas.draw()
            return
        
        N = len(names)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        positive_plot = positive_values + positive_values[:1]
        negative_plot = negative_values + negative_values[:1]
        
        ax = self.figure.add_subplot(111, projection='polar')
        ax.plot(angles, positive_plot, 'o-', linewidth=2, color='#2E7D32',
                label='رفتار مثبت')
        ax.fill(angles, positive_plot, alpha=0.20, color='#2E7D32')
        ax.plot(angles, negative_plot, 'o-', linewidth=2, color='#C62828',
                label='رفتار منفی')
        ax.fill(angles, negative_plot, alpha=0.20, color='#C62828')
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(names, size=8)
        max_value = max(positive_values + negative_values + [1])
        ax.set_ylim(0, max_value * 1.15)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.15), fontsize=8)
        ax.set_title('ترکیب رفتارهای ثبت‌شده به تفکیک زمینه (بدون رتبه‌بندی)',
                     size=12, fontweight='bold', pad=20)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    # ===== رویدادهای ردیابی =====
    def on_traceability_clicked(self, item):
        """مدیریت کلیک روی آیتم‌های ردیابی"""
        row = item.row()
        table = item.tableWidget()
        
        id_item = table.item(row, 0)
        if not id_item:
            return
        
        try:
            record_id = int(id_item.text())
        except ValueError:
            return
        
        if table == self.traceability_table:
            type_item = table.item(row, 0)
            if not type_item:
                return
            record_type = type_item.text()
        else:
            if table == self.obs_table:
                record_type = 'مشاهده'
            elif table == self.inter_table:
                record_type = 'مداخله'
            elif table == self.follow_table:
                record_type = 'پیگیری'
            else:
                return
        
        self.show_record_details(record_type, record_id)
    
    def show_record_details(self, record_type, record_id):
        """نمایش جزئیات یک رکورد با شناسه"""
        if record_type == 'مشاهده':
            obs = self.observation_dal.get_by_id(record_id)
            if obs:
                details = f"""
📝 **جزئیات مشاهده**
شناسه: {obs.id}
تاریخ: {obs.observation_date}
محیط: {obs.location}
شایستگی: {self._get_competency_name(obs.competency_id)}
نوع: {obs.behavior_type}
شدت: {obs.severity_display}

━━━━━━━━━━ مدل ABC ━━━━━━━━━━
🔴 A - زمینه: {obs.antecedent or 'ثبت نشده'}
🟡 B - رفتار: {obs.behavior or 'ثبت نشده'}
🟢 C - پیامد: {obs.consequence or 'ثبت نشده'}

📝 شرح: {obs.description}
🏷️ برچسب‌ها: {obs.tags or 'ندارد'}
"""
                QMessageBox.information(self, "جزئیات مشاهده", details)
                
        elif record_type == 'مداخله':
            inter = self.intervention_dal.get_by_id(record_id)
            if inter:
                staff_name = self._get_staff_name(inter.staff_id)
                details = f"""
🛠️ **جزئیات مداخله**
شناسه: {inter.id}
تاریخ: {inter.date}
نوع: {inter.type_display}
مسئول: {staff_name}
وضعیت: {inter.status_display}
هدف: {inter.goal or 'ثبت نشده'}
نتیجه: {inter.result or 'ثبت نشده'}

📝 شرح: {inter.description}
"""
                QMessageBox.information(self, "جزئیات مداخله", details)
                
        elif record_type == 'پیگیری':
            follow = self.followup_dal.get_by_id(record_id)
            if follow:
                staff_name = self._get_staff_name(follow.staff_id)
                details = f"""
🔔 **جزئیات پیگیری**
شناسه: {follow.id}
تاریخ: {follow.date}
مسئول: {staff_name}
وضعیت: {follow.status_display}
نوع نتیجه: {follow.result_type_display}
شرح نتیجه: {follow.result_description or 'ثبت نشده'}
اقدام بعدی: {follow.next_action_date or 'تعیین نشده'}

📝 شرح: {follow.description or 'ثبت نشده'}
"""
                QMessageBox.information(self, "جزئیات پیگیری", details)
    
    def _get_competency_name(self, competency_id):
        """دریافت نام شایستگی"""
        if not competency_id:
            return "نامشخص"
        try:
            comp = self.competency_dal.get_by_id(competency_id)
            return comp.title if comp else "نامشخص"
        except Exception:
            return "نامشخص"
    
    def _get_staff_name(self, staff_id):
        """دریافت نام مسئول"""
        if not staff_id:
            return "نامشخص"
        try:
            staff = self.staff_dal.get_by_id(staff_id)
            return staff.full_name if staff else "نامشخص"
        except Exception:
            return "نامشخص"
    
    # ===== گزارش والدین =====
    def show_parent_report(self):
        """نمایش گزارش والدین"""
        if not self.current_profile_id:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا یک دانش‌آموز را انتخاب کنید.")
            return
        
        try:
            parent_report = self.report_generator.generate_parent_report(self.current_profile_id)
            if not parent_report:
                QMessageBox.warning(self, "توجه", "امکان تولید گزارش والدین وجود ندارد.")
                return
            
            text = f"""
👨‍👩‍👦 **گزارش والدین**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**👤 دانش‌آموز:** {parent_report['student_name']}
**پایه:** {parent_report['grade']}
**کلاس:** {parent_report['class']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📊 خلاصه**
{parent_report['summary']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**⭐ نقاط قوت**
"""
            if parent_report['strengths']:
                for strength in parent_report['strengths']:
                    text += (f"• {strength['competency']} — "
                             f"{strength.get('positive', 0)} رفتار مثبت از "
                             f"{strength.get('count', 0)} مشاهده\n")
            else:
                text += "• الگوی تکرارشوندهٔ رفتار مثبت ثبت نشده است.\n"
            
            text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🔴 زمینه‌های نیازمند حمایت**
"""
            if parent_report['weaknesses']:
                for weakness in parent_report['weaknesses']:
                    text += (f"• {weakness['competency']} — "
                             f"{weakness.get('negative', 0)} رفتار منفی از "
                             f"{weakness.get('count', 0)} مشاهده\n")
            else:
                text += "• الگوی تکرارشوندهٔ رفتار منفی ثبت نشده است.\n"
            
            text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**💡 پیشنهاد برای والدین**
"""
            for rec in parent_report['recommendations']['parents']:
                text += f"• {rec}\n"
            
            if parent_report['trend']:
                text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📈 روند کلی**
• تعداد مشاهدات ثبت‌شده: {parent_report['observations_count']}
• تعداد مداخلات: {parent_report['interventions_count']}
"""
            
            QMessageBox.information(self, "گزارش والدین", text)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در تولید گزارش والدین:\n{e!s}")
    
    # ===== خروجی Excel =====
    def export_excel(self):
        """خروجی Excel کامل"""
        if not self.current_profile_id:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا یک دانش‌آموز را انتخاب کنید.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل Excel",
            f"گزارش_{self.get_student_name()}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            success, message = self.report_generator.export_to_excel(
                self.current_profile_id,
                file_path
            )
            
            if success:
                QMessageBox.information(self, "موفقیت", message)
            else:
                QMessageBox.critical(self, "خطا", message)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در خروجی Excel:\n{e!s}")

    def export_pdf(self):
        """خروجی PDF کامل"""
        if not self.current_profile_id:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا یک دانش‌آموز را انتخاب کنید.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل PDF",
            f"گزارش_{self.get_student_name()}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return
        
        try:
            success, message = self.report_generator.export_to_pdf(
                self.current_profile_id,
                file_path
            )
            
            if success:
                QMessageBox.information(self, "موفقیت", message)
            else:
                QMessageBox.critical(self, "خطا", message)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در خروجی PDF:\n{e!s}")

    def export_for_ai(self):
        """خروجی داده برای هوش مصنوعی"""
        if not self.current_profile_id:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا یک دانش‌آموز را انتخاب کنید.")
            return
        
        from views.dialogs.export_ai_dialog import ExportAIDialog
        dialog = ExportAIDialog(
            profile_id=self.current_profile_id,
            parent=self
        )
        dialog.exec() 