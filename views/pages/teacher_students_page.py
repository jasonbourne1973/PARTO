"""
صفحه مشاهده دانش‌آموزان یک معلم - نسخه کامل
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
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
from utils.logger import get_logger

logger = get_logger(__name__)


class TeacherStudentsPage(QWidget):
    """صفحه مشاهده دانش‌آموزان یک معلم"""
    
    student_selected = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.student_dal = StudentDAL()
        self.staff_dal = StaffDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.competency_dal = CompetencyDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        
        self.current_teacher_id = None
        self.current_year_id = None
        self.current_students = []
        self.selected_student_id = None
        
        self.setup_ui()
        self.load_teachers()
        self.load_academic_years()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # ===== عنوان =====
        title_label = QLabel("👨‍🏫 دانش‌آموزان معلم")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        main_layout.addWidget(title_label)
        
        # ===== نوار انتخاب معلم و سال =====
        toolbar = QHBoxLayout()
        
        toolbar.addWidget(QLabel("انتخاب معلم:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.setMinimumWidth(200)
        self.teacher_combo.setPlaceholderText("انتخاب معلم...")
        self.teacher_combo.currentIndexChanged.connect(self.load_teacher_students)
        toolbar.addWidget(self.teacher_combo)
        
        toolbar.addSpacing(20)
        
        toolbar.addWidget(QLabel("سال تحصیلی:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(150)
        self.year_combo.currentIndexChanged.connect(self.load_teacher_students)
        toolbar.addWidget(self.year_combo)
        
        toolbar.addStretch()
        
        # دکمه به‌روزرسانی
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedWidth(40)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover { background-color: #08223A; }
        """)
        self.refresh_btn.clicked.connect(self.load_teacher_students)
        toolbar.addWidget(self.refresh_btn)
        
        main_layout.addLayout(toolbar)
        
        # ===== بخش اصلی: Splitter =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ===== سمت چپ: لیست دانش‌آموزان =====
        left_frame = QFrame()
        left_frame.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 5px;
            }
        """)
        left_layout = QVBoxLayout()
        left_frame.setLayout(left_layout)
        
        # عنوان لیست
        list_title = QLabel("📋 لیست دانش‌آموزان")
        list_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F4C542; padding: 5px;")
        left_layout.addWidget(list_title)
        
        # جدول دانش‌آموزان
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(5)
        self.students_table.setHorizontalHeaderLabels([
            "ردیف", "نام و نام خانوادگی", "پایه", "کلاس", "وضعیت"
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
            QTableWidget::item:selected { background-color: #66BB6A; color: #F4C542; }
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
        
        self.students_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.students_table.itemClicked.connect(self.on_student_selected)
        self.students_table.itemDoubleClicked.connect(self.on_student_double_clicked)
        
        left_layout.addWidget(self.students_table)
        
        splitter.addWidget(left_frame)
        
        # ===== سمت راست: جزئیات دانش‌آموز =====
        right_frame = QFrame()
        right_frame.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 5px;
            }
        """)
        right_layout = QVBoxLayout()
        right_frame.setLayout(right_layout)
        
        # عنوان جزئیات
        details_title = QLabel("📋 جزئیات دانش‌آموز")
        details_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F4C542; padding: 5px;")
        right_layout.addWidget(details_title)
        
        # تب‌های جزئیات
        self.details_tabs = QTabWidget()
        self.details_tabs.setStyleSheet("""
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
                padding: 8px 15px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
    border-color: #F4C542;
                background-color: #8BC34A;
                color: #111111;
            }
        """)
        
        # تب اطلاعات
        self.info_tab = self.create_info_tab()
        self.details_tabs.addTab(self.info_tab, "📊 اطلاعات")
        
        # تب مشاهدات
        self.obs_tab = self.create_observations_tab()
        self.details_tabs.addTab(self.obs_tab, "📝 مشاهدات")
        
        # تب مداخلات
        self.inter_tab = self.create_interventions_tab()
        self.details_tabs.addTab(self.inter_tab, "🛠️ مداخلات")
        
        # تب پیگیری‌ها
        self.follow_tab = self.create_followups_tab()
        self.details_tabs.addTab(self.follow_tab, "🔔 پیگیری‌ها")
        
        right_layout.addWidget(self.details_tabs)
        
        splitter.addWidget(right_frame)
        splitter.setSizes([450, 550])
        
        main_layout.addWidget(splitter)
        
        # ===== دکمه‌های پایین =====
        bottom_layout = QHBoxLayout()
        
        self.view_profile_btn = QPushButton("👤 مشاهده پرونده کامل")
        self.view_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7d3c98; }
        """)
        self.view_profile_btn.clicked.connect(self.view_full_profile)
        bottom_layout.addWidget(self.view_profile_btn)
        
        bottom_layout.addStretch()
        
        self.edit_teacher_btn = QPushButton("✏️ ویرایش معلم")
        self.edit_teacher_btn.setStyleSheet("""
            QPushButton {
                background-color: #F4D35E;
                color: #F4C542;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #F28C28; }
        """)
        self.edit_teacher_btn.clicked.connect(self.edit_teacher_assignment)
        bottom_layout.addWidget(self.edit_teacher_btn)
        
        main_layout.addLayout(bottom_layout)
    
    def create_info_tab(self):
        """ایجاد تب اطلاعات دانش‌آموز"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                border: 1px solid #8BC34A;
                padding: 10px;
                font-size: 13px;
                background-color: #08223A;
                line-height: 1.8;
            }
        """)
        self.info_text.setPlaceholderText("برای مشاهده اطلاعات، یک دانش‌آموز را انتخاب کنید...")
        layout.addWidget(self.info_text)
        
        return tab
    
    def create_observations_tab(self):
        """ایجاد تب مشاهدات"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.obs_table = QTableWidget()
        self.obs_table.setColumnCount(5)
        self.obs_table.setHorizontalHeaderLabels(["تاریخ", "محیط", "نوع", "شدت", "شرح"])
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
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        self.obs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.obs_table)
        
        return tab
    
    def create_interventions_tab(self):
        """ایجاد تب مداخلات"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.inter_table = QTableWidget()
        self.inter_table.setColumnCount(5)
        self.inter_table.setHorizontalHeaderLabels(["تاریخ", "نوع", "مسئول", "وضعیت", "نتیجه"])
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
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        self.inter_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.inter_table)
        
        return tab
    
    def create_followups_tab(self):
        """ایجاد تب پیگیری‌ها"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.follow_table = QTableWidget()
        self.follow_table.setColumnCount(4)
        self.follow_table.setHorizontalHeaderLabels(["تاریخ", "وضعیت", "نوع نتیجه", "نتیجه"])
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
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        self.follow_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.follow_table)
        
        return tab
    
    def load_teachers(self):
        """بارگذاری معلمان در کامبوباکس"""
        try:
            all_staff = self.staff_dal.get_all()
            teachers = [s for s in all_staff if s.role == "teacher"]
            self.teacher_combo.clear()
            self.teacher_combo.addItem("انتخاب معلم...", None)
            for teacher in teachers:
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
    
    def load_teacher_students(self):
        """بارگذاری دانش‌آموزان معلم انتخاب شده"""
        teacher_id = self.teacher_combo.currentData()
        year_id = self.year_combo.currentData()
        
        if not teacher_id:
            self.students_table.setRowCount(0)
            self.clear_details()
            return
        
        self.current_teacher_id = teacher_id
        self.current_year_id = year_id
        
        try:
            # دریافت انتساب‌های معلم
            if year_id:
                assignments = self.assignment_dal.get_by_teacher(teacher_id, year_id)
            else:
                assignments = self.assignment_dal.get_by_teacher(teacher_id, include_inactive=True)
            
            self.current_students = []
            self.students_table.setRowCount(len(assignments))
            
            for row, assignment in enumerate(assignments):
                self.current_students.append(assignment)
                
                self.students_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.students_table.setItem(row, 1, QTableWidgetItem(assignment.student_name or "نامشخص"))
                self.students_table.setItem(row, 2, QTableWidgetItem(str(assignment.grade) if assignment.grade else "-"))
                self.students_table.setItem(row, 3, QTableWidgetItem(assignment.class_name or "-"))
                
                status_item = QTableWidgetItem("🟢 فعال" if assignment.is_active == 1 else "🔴 غیرفعال")
                if assignment.is_active == 1:
                    status_item.setBackground(QColor(200, 255, 200))
                else:
                    status_item.setBackground(QColor(255, 200, 200))
                self.students_table.setItem(row, 4, status_item)
                self.students_table.setRowHeight(row, 35)
            
            # انتخاب اولین دانش‌آموز به صورت خودکار
            if assignments:
                self.students_table.selectRow(0)
                self.on_student_selected(self.students_table.item(0, 0))
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری دانش‌آموزان:\n{e!s}")
    
    def on_student_selected(self, item):
        """وقتی دانش‌آموز انتخاب می‌شود"""
        row = item.row()
        if row < len(self.current_students):
            assignment = self.current_students[row]
            self.selected_student_id = assignment.student_id
            self.show_student_details(assignment)
    
    def on_student_double_clicked(self, item):
        """وقتی دانش‌آموز دابل‌کلیک می‌شود"""
        self.view_full_profile()
    
    def show_student_details(self, assignment):
        """نمایش جزئیات دانش‌آموز"""
        try:
            student = self.student_dal.get_by_id(assignment.student_id)
            if not student:
                return
            
            # ===== اطلاعات =====
            # دریافت اطلاعات پرونده
            profile = self.profile_dal.get_active_by_student(student.id) if hasattr(self, 'profile_dal') else None
            grade_text = profile.grade_display if profile else "-"
            class_name = profile.class_name if profile else "-"
            
            info_text = f"""
📊 **اطلاعات دانش‌آموز**

👤 **نام:** {student.full_name}
📚 **پایه:** {grade_text}
🏫 **کلاس:** {class_name}
🆔 **کد ملی:** {student.national_code or 'ندارد'}
📅 **تاریخ تولد:** {student.birth_date or 'ندارد'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👨‍🏫 **اطلاعات اختصاص معلم**

👤 **معلم:** {assignment.teacher_name or 'نامشخص'}
📅 **تاریخ انتصاب:** {assignment.assigned_date or 'نامشخص'}
📌 **وضعیت:** {assignment.status_display}
"""
            
            self.info_text.setText(info_text)
            
            # ===== مشاهدات =====
            self.load_student_observations(student.id)
            
            # ===== مداخلات =====
            self.load_student_interventions(student.id)
            
            # ===== پیگیری‌ها =====
            self.load_student_followups(student.id)
            
        except Exception as e:
            logger.error(f"خطا در نمایش جزئیات: {e}")
    
    def load_student_observations(self, student_id):
        """بارگذاری مشاهدات دانش‌آموز"""
        try:
            # دریافت پرونده فعال
            profile = self.profile_dal.get_active_by_student(student_id) if hasattr(self, 'profile_dal') else None
            if not profile:
                self.obs_table.setRowCount(0)
                return
            
            observations = self.observation_dal.get_by_student_profile(profile.id, limit=20)
            self.obs_table.setRowCount(len(observations))
            
            for row, obs in enumerate(observations):
                self.obs_table.setItem(row, 0, QTableWidgetItem(obs.observation_date or ""))
                self.obs_table.setItem(row, 1, QTableWidgetItem(obs.location or ""))
                
                type_item = QTableWidgetItem(obs.behavior_type or "خنثی")
                if obs.behavior_type == "مثبت":
                    type_item.setBackground(QColor(200, 255, 200))
                elif obs.behavior_type == "منفی":
                    type_item.setBackground(QColor(255, 200, 200))
                self.obs_table.setItem(row, 2, type_item)
                
                self.obs_table.setItem(row, 3, QTableWidgetItem("⭐" * obs.severity))
                
                desc_text = obs.description[:40] + "..." if obs.description and len(obs.description) > 40 else obs.description or ""
                self.obs_table.setItem(row, 4, QTableWidgetItem(desc_text))
                self.obs_table.setRowHeight(row, 30)
                
        except Exception as e:
            logger.error(f"خطا در بارگذاری مشاهدات: {e}")
    
    def load_student_interventions(self, student_id):
        """بارگذاری مداخلات دانش‌آموز"""
        try:
            profile = self.profile_dal.get_active_by_student(student_id) if hasattr(self, 'profile_dal') else None
            if not profile:
                self.inter_table.setRowCount(0)
                return
            
            interventions = self.intervention_dal.get_by_student_profile(profile.id, limit=10)
            self.inter_table.setRowCount(len(interventions))
            # نام کادر یک‌جا خوانده می‌شود (رفع N+1)
            staff_names = self.staff_dal.get_names_by_ids(i.staff_id for i in interventions)
            
            for row, inter in enumerate(interventions):
                self.inter_table.setItem(row, 0, QTableWidgetItem(inter.date or ""))
                self.inter_table.setItem(row, 1, QTableWidgetItem(inter.type_display))
                
                staff_name = staff_names.get(inter.staff_id) or "نامشخص"
                self.inter_table.setItem(row, 2, QTableWidgetItem(staff_name))
                
                self.inter_table.setItem(row, 3, QTableWidgetItem(inter.status_display))
                self.inter_table.setItem(row, 4, QTableWidgetItem(inter.result or "نامشخص"))
                self.inter_table.setRowHeight(row, 30)
                
        except Exception as e:
            logger.error(f"خطا در بارگذاری مداخلات: {e}")
    
    def load_student_followups(self, student_id):
        """بارگذاری پیگیری‌های دانش‌آموز"""
        try:
            profile = self.profile_dal.get_active_by_student(student_id) if hasattr(self, 'profile_dal') else None
            if not profile:
                self.follow_table.setRowCount(0)
                return
            
            followups = self.followup_dal.get_by_student_profile(profile.id)
            self.follow_table.setRowCount(len(followups))
            
            for row, follow in enumerate(followups):
                self.follow_table.setItem(row, 0, QTableWidgetItem(follow.date or ""))
                self.follow_table.setItem(row, 1, QTableWidgetItem(follow.status_display))
                self.follow_table.setItem(row, 2, QTableWidgetItem(follow.result_type_display))
                self.follow_table.setItem(row, 3, QTableWidgetItem(follow.result_description or "نامشخص"))
                self.follow_table.setRowHeight(row, 30)
                
        except Exception as e:
            logger.error(f"خطا در بارگذاری پیگیری‌ها: {e}")
    
    def clear_details(self):
        """پاک کردن جزئیات"""
        self.info_text.clear()
        self.obs_table.setRowCount(0)
        self.inter_table.setRowCount(0)
        self.follow_table.setRowCount(0)
        self.selected_student_id = None
    
    def view_full_profile(self):
        """مشاهده پرونده کامل دانش‌آموز"""
        if self.selected_student_id:
            self.student_selected.emit(self.selected_student_id)
        else:
            QMessageBox.warning(self, "توجه", "لطفاً یک دانش‌آموز را انتخاب کنید.")
    
    def edit_teacher_assignment(self):
        """ویرایش اختصاص معلم"""
        if not self.selected_student_id:
            QMessageBox.warning(self, "توجه", "لطفاً یک دانش‌آموز را انتخاب کنید.")
            return
        
        # پیدا کردن انتساب فعلی
        for assignment in self.current_students:
            if assignment.student_id == self.selected_student_id:
                from views.dialogs.assign_teacher_dialog import AssignTeacherDialog
                dialog = AssignTeacherDialog(assignment_id=assignment.id, parent=self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.load_teacher_students()
                    QMessageBox.information(self, "موفقیت", "اطلاعات معلم با موفقیت ویرایش شد.")
                return