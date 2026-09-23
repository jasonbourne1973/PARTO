"""
صفحه مدیریت ساختار آموزشی - یکپارچه‌سازی مدیریت کلاس‌ها، اختصاص معلم و دانش‌آموزان معلم
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
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dal.academic_year_dal import AcademicYearDAL
from dal.class_dal import ClassDAL
from dal.competency_dal import CompetencyDAL
from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from models.class_model import ClassModel
from utils.logger import get_logger
from views.dialogs.assign_teacher_dialog import AssignTeacherDialog
from views.pages.promotion_page import PromotionPage
from views.pages.year_sync import YearAwarePage


class AcademicStructurePage(YearAwarePage, QWidget):
    """
    صفحه یکپارچه مدیریت ساختار آموزشی شامل سه بخش:
    1. مدیریت کلاس‌ها
    2. اختصاص معلم به دانش‌آموزان
    3. مشاهده دانش‌آموزان معلم
    """
    
    student_selected = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)    
        
        # ===== DALها =====
        self.student_dal = StudentDAL()
        self.staff_dal = StaffDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.class_dal = ClassDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.competency_dal = CompetencyDAL()
        self.class_year_combo = None
        
        self.logger = get_logger(self.__class__.__name__)
        
        # ===== متغیرهای وضعیت =====
        self.current_teacher_id = None
        self.current_year_id = None
        self.current_students = []
        self.selected_student_ids = []
        self.selected_student_id = None
        
        # ===== کامبوباکس‌های مورد نیاز =====
        self.class_year_combo = None  # تعریف شده برای استفاده در load_academic_years
        
        self.setup_ui()
        self.load_initial_data()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # ===== عنوان =====
        title_label = QLabel("🏫 مدیریت ساختار آموزشی")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #F4C542;
                padding: 5px 0;
            }
        """)
        main_layout.addWidget(title_label)
        
        # ===== نوار انتخاب سال تحصیلی (مشترک) =====
        toolbar = QHBoxLayout()
        
        toolbar.addWidget(QLabel("📅 سال تحصیلی:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(150)
        self.year_combo.currentIndexChanged.connect(self.on_year_changed)
        self.year_combo.setStyleSheet("""
            QComboBox {
    color: #F4C542;
                padding: 5px 10px;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                background-color: #08223A;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #0B2E4F;
            }
        """)
        toolbar.addWidget(self.year_combo)
        
        toolbar.addStretch()
        
        # دکمه به‌روزرسانی
        self.refresh_btn = QPushButton("🔄 به‌روزرسانی")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 6px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #08223A;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_all)
        toolbar.addWidget(self.refresh_btn)
        
        main_layout.addLayout(toolbar)
        
        # ===== تب‌ها =====
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
                font-size: 13px;
            }
            QTabBar::tab:selected {
    border-color: #F4C542;
                background-color: #8BC34A;
                color: #111111;
            }
        """)
        
        # تب 1: مدیریت کلاس‌ها
        self.class_tab = self.create_class_tab()
        self.tabs.addTab(self.class_tab, "🏫 مدیریت کلاس‌ها")
        
        # تب 2: اختصاص معلم
        self.assign_tab = self.create_assign_tab()
        self.tabs.addTab(self.assign_tab, "👨‍🏫 اختصاص معلم")
        
        # تب 3: دانش‌آموزان معلم
        self.teacher_students_tab = self.create_teacher_students_tab()
        self.tabs.addTab(self.teacher_students_tab, "📋 دانش‌آموزان معلم")
        
        # تب 4: ارتقاء پایه
        self.promotion_page = PromotionPage(embedded=True)
        self.tabs.addTab(self.promotion_page, "📈 ارتقاء پایه")
        
        main_layout.addWidget(self.tabs)
    
    # ============================================================
    # تب 1: مدیریت کلاس‌ها
    # ============================================================
    
    def create_class_tab(self):
        """ایجاد تب مدیریت کلاس‌ها"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #D9C36A;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #D9C36A;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        container = QWidget()
        container_layout = QVBoxLayout()
        container.setLayout(container_layout)
        
        # ===== فرم افزودن کلاس =====
        form_group = QGroupBox("➕ افزودن کلاس جدید")
        form_group.setStyleSheet("""
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
        form_layout = QGridLayout()
        form_group.setLayout(form_layout)
        
        # نام کلاس
        form_layout.addWidget(QLabel("نام کلاس:"), 0, 0)
        self.class_name_input = QLineEdit()
        self.class_name_input.setPlaceholderText("مثال: الف، ب، ج، ...")
        self.class_name_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                padding: 6px 10px;
                border: 1px solid #8BC34A;
                border-radius: 4px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F;
                border: 2px solid #F4C542;
            }
        """)
        form_layout.addWidget(self.class_name_input, 0, 1)
        
        # پایه
        form_layout.addWidget(QLabel("پایه:"), 1, 0)
        self.class_grade_combo = QComboBox()
        grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}
        for grade in range(1, 7):
            self.class_grade_combo.addItem(f"پایه {grade_names[grade]}", grade)
        self.class_grade_combo.setStyleSheet("""
            QComboBox {
    color: #F4C542;
                padding: 6px 10px;
                border: 1px solid #8BC34A;
                border-radius: 4px;
                background-color: #08223A;
            }
            QComboBox:hover {
                border-color: #F28C28;
            }
        """)
        form_layout.addWidget(self.class_grade_combo, 1, 1)
        
        # معلم
        form_layout.addWidget(QLabel("معلم اصلی:"), 2, 0)
        self.class_teacher_combo = QComboBox()
        self.class_teacher_combo.addItem("بدون معلم", None)
        self.class_teacher_combo.setStyleSheet("""
            QComboBox {
    color: #F4C542;
                padding: 6px 10px;
                border: 1px solid #8BC34A;
                border-radius: 4px;
                background-color: #08223A;
            }
            QComboBox:hover {
                border-color: #F28C28;
            }
        """)
        form_layout.addWidget(self.class_teacher_combo, 2, 1)
        
        # ظرفیت
        form_layout.addWidget(QLabel("ظرفیت:"), 3, 0)
        self.class_capacity_spin = QSpinBox()
        self.class_capacity_spin.setRange(0, 100)
        self.class_capacity_spin.setValue(30)
        self.class_capacity_spin.setStyleSheet("""
            QSpinBox {
    color: #F4C542;
    background-color: #08223A;
                padding: 6px 10px;
                border: 1px solid #8BC34A;
                border-radius: 4px;
            }
            QSpinBox:focus {
    color: #FFE8A3;
    background-color: #0B2E4F;
                border: 2px solid #F4C542;
            }
        """)
        form_layout.addWidget(self.class_capacity_spin, 3, 1)
        
        # دکمه افزودن
        self.add_class_btn = QPushButton("➕ افزودن کلاس")
        self.add_class_btn.setStyleSheet("""
            QPushButton {
                background-color: #F28C28;
                color: #111111;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        self.add_class_btn.clicked.connect(self.add_class)
        form_layout.addWidget(self.add_class_btn, 4, 0, 1, 2)

        # (بازرسی شانزدهم) حالت ویرایش با همین فرم
        self._editing_class_id = None
        self.cancel_edit_class_btn = QPushButton("✖ انصراف از ویرایش")
        self.cancel_edit_class_btn.setStyleSheet(
            "QPushButton { background-color: #08223A; color: #F4C542; padding: 8px 20px; "
            "border: 1px solid #D9C36A; border-radius: 5px; }")
        self.cancel_edit_class_btn.clicked.connect(self.cancel_edit_class)
        self.cancel_edit_class_btn.setVisible(False)
        form_layout.addWidget(self.cancel_edit_class_btn, 5, 0, 1, 2)
        
        container_layout.addWidget(form_group)
        
        # ===== جدول کلاس‌ها =====
        table_label = QLabel("📋 لیست کلاس‌ها")
        table_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #F4C542; padding: 5px 0;")
        container_layout.addWidget(table_label)
        
        self.class_table = QTableWidget()
        self.class_table.setColumnCount(6)
        self.class_table.setHorizontalHeaderLabels(["شناسه", "نام کلاس", "پایه", "معلم", "تعداد دانش‌آموز", "عملیات"])
        self.class_table.setAlternatingRowColors(True)
        self.class_table.setStyleSheet("""
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
    background-color: #0B2E4F;
                padding: 8px;
            }
            QTableWidget::item:hover {
    color: #FFE8A3;
                background-color: #174F78;
            }
            QHeaderView::section {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px;
                border: 1px solid #D9C36A;
                font-weight: bold;
            }
        """)
        
        header = self.class_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.class_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        container_layout.addWidget(self.class_table)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        return tab
    
    # ============================================================
    # تب 2: اختصاص معلم
    # ============================================================
    
    def create_assign_tab(self):
        """ایجاد تب اختصاص معلم"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # ===== نوار انتخاب معلم =====
        assign_toolbar = QHBoxLayout()
        
        assign_toolbar.addWidget(QLabel("👨‍🏫 انتخاب معلم:"))
        self.assign_teacher_combo = QComboBox()
        self.assign_teacher_combo.setMinimumWidth(200)
        self.assign_teacher_combo.setPlaceholderText("انتخاب معلم...")
        self.assign_teacher_combo.currentIndexChanged.connect(self.load_assign_students)
        self.assign_teacher_combo.setStyleSheet("""
            QComboBox {
    color: #F4C542;
                padding: 5px 10px;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                background-color: #08223A;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #66BB6A;
            }
        """)
        assign_toolbar.addWidget(self.assign_teacher_combo)
        
        assign_toolbar.addStretch()
        
        # دکمه اختصاص جدید
        self.assign_new_btn = QPushButton("➕ اختصاص معلم جدید")
        self.assign_new_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 6px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        self.assign_new_btn.clicked.connect(self.open_assign_dialog)
        assign_toolbar.addWidget(self.assign_new_btn)
        
        layout.addLayout(assign_toolbar)
        
        # ===== جدول انتساب‌ها =====
        self.assign_table = QTableWidget()
        self.assign_table.setColumnCount(6)
        self.assign_table.setHorizontalHeaderLabels([
            "ردیف", "دانش‌آموز", "پایه", "کلاس", "وضعیت", "عملیات"
        ])
        self.assign_table.setAlternatingRowColors(True)
        self.assign_table.setStyleSheet("""
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
    background-color: #0B2E4F;
                padding: 8px;
            }
            QTableWidget::item:hover {
    color: #FFE8A3;
                background-color: #174F78;
            }
            QHeaderView::section {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px;
                border: 1px solid #D9C36A;
                font-weight: bold;
            }
        """)
        
        header = self.assign_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.assign_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.assign_table)
        
        return tab
    
    # ============================================================
    # تب 3: دانش‌آموزان معلم
    # ============================================================
    
    def create_teacher_students_tab(self):
        """ایجاد تب دانش‌آموزان معلم"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # ===== نوار انتخاب معلم =====
        ts_toolbar = QHBoxLayout()
        
        ts_toolbar.addWidget(QLabel("👨‍🏫 انتخاب معلم:"))
        self.ts_teacher_combo = QComboBox()
        self.ts_teacher_combo.setMinimumWidth(200)
        self.ts_teacher_combo.setPlaceholderText("انتخاب معلم...")
        self.ts_teacher_combo.currentIndexChanged.connect(self.load_teacher_students)
        self.ts_teacher_combo.setStyleSheet("""
            QComboBox {
    color: #F4C542;
                padding: 5px 10px;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                background-color: #08223A;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #08223A;
            }
        """)
        ts_toolbar.addWidget(self.ts_teacher_combo)
        
        ts_toolbar.addStretch()
        
        # تعداد دانش‌آموزان
        self.ts_count_label = QLabel("تعداد: 0 دانش‌آموز")
        self.ts_count_label.setStyleSheet("font-size: 13px; color: #D9C36A; font-weight: bold;")
        ts_toolbar.addWidget(self.ts_count_label)
        
        layout.addLayout(ts_toolbar)
        
        # ===== بخش اصلی (Splitter) =====
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
        
        list_title = QLabel("📋 لیست دانش‌آموزان")
        list_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #F4C542; padding: 5px;")
        left_layout.addWidget(list_title)
        
        self.ts_students_table = QTableWidget()
        self.ts_students_table.setColumnCount(5)
        self.ts_students_table.setHorizontalHeaderLabels([
            "ردیف", "نام و نام خانوادگی", "پایه", "کلاس", "وضعیت"
        ])
        self.ts_students_table.setAlternatingRowColors(True)
        self.ts_students_table.setStyleSheet("""
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
    background-color: #0B2E4F;
                padding: 8px;
            }
            QTableWidget::item:hover {
    color: #FFE8A3;
                background-color: #174F78;
            }
            QTableWidget::item:selected {
                background-color: #66BB6A;
                color: #111111;
            }
            QHeaderView::section {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px;
                border: 1px solid #D9C36A;
                font-weight: bold;
            }
        """)
        
        header = self.ts_students_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.ts_students_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ts_students_table.itemDoubleClicked.connect(self.on_ts_student_double_clicked)
        left_layout.addWidget(self.ts_students_table)
        
        splitter.addWidget(left_frame)
        
        # ===== سمت راست: جزئیات =====
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
        
        details_title = QLabel("📋 جزئیات دانش‌آموز")
        details_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #F4C542; padding: 5px;")
        right_layout.addWidget(details_title)
        
        self.ts_details_text = QTextEdit()
        self.ts_details_text.setReadOnly(True)
        self.ts_details_text.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                border: 1px solid #8BC34A;
                padding: 10px;
                font-size: 13px;
                background-color: #08223A;
                line-height: 1.8;
            }
        """)
        self.ts_details_text.setPlaceholderText("برای مشاهده جزئیات، روی یک دانش‌آموز کلیک کنید...")
        right_layout.addWidget(self.ts_details_text)
        
        # دکمه مشاهده پرونده
        view_profile_btn = QPushButton("👤 مشاهده پرونده کامل")
        view_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7d3c98;
            }
        """)
        view_profile_btn.clicked.connect(self.view_full_profile)
        right_layout.addWidget(view_profile_btn)
        
        splitter.addWidget(right_frame)
        splitter.setSizes([450, 550])
        
        layout.addWidget(splitter)
        
        return tab
    
    # ============================================================
    # متدهای بارگذاری داده
    # ============================================================
    
    def reload_for_year(self, year_id):
        """
        بارگذاری دوبارهٔ ساختار آموزشی و تب ارتقاء پایه

        کامبوی سال این صفحه پیش از این متد هماهنگ شده است؛ فهرست
        سال‌ها هم تازه می‌شود تا نشان «سال فعال» درست بماند.
        """
        self.load_academic_years()
        promotion = getattr(self, "promotion_page", None)
        setter = getattr(promotion, "set_active_year", None)
        if callable(setter):
            setter(year_id)
        return True

    def load_initial_data(self):
        """بارگذاری داده‌های اولیه"""
        self.load_academic_years()
        self.load_teachers()
        self.load_classes()
        self.load_assign_students()
        self.load_teacher_students()

    def load_academic_years(self):
        try:
            years = self.academic_year_dal.get_all(include_archived=True)
            
            # بارگذاری در year_combo
            self.year_combo.blockSignals(True)
            self.year_combo.clear()
            self.year_combo.addItem("همه سال‌ها", None)
            for year in years:
                display_text = f"{year.title} {'📦' if year.is_archived == 1 else ''}"
                self.year_combo.addItem(display_text, year.id)
            self.year_combo.blockSignals(False)
            
            # ✅ بررسی وجود class_year_combo قبل از استفاده
            if self.class_year_combo:
                self.class_year_combo.blockSignals(True)
                self.class_year_combo.clear()
                self.class_year_combo.addItem("همه سال‌ها", None)
                for year in years:
                    display_text = f"{year.title} {'📦' if year.is_archived == 1 else ''}"
                    self.class_year_combo.addItem(display_text, year.id)
                self.class_year_combo.blockSignals(False)
            
            # انتخاب سال فعال
            active_year = self.academic_year_dal.get_active()
            if active_year:
                for i in range(self.year_combo.count()):
                    if self.year_combo.itemData(i) == active_year.id:
                        self.year_combo.setCurrentIndex(i)
                        break
                
                if self.class_year_combo:
                    for i in range(self.class_year_combo.count()):
                        if self.class_year_combo.itemData(i) == active_year.id:
                            self.class_year_combo.setCurrentIndex(i)
                            break
           
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری سال‌های تحصیلی: {e}")
    
    def load_teachers(self):
        """بارگذاری معلمان در کامبوباکس‌ها"""
        try:
            all_staff = self.staff_dal.get_all()
            teachers = [s for s in all_staff if s.role == "teacher"]
            
            # بارگذاری در class_teacher_combo
            self.class_teacher_combo.blockSignals(True)
            self.class_teacher_combo.clear()
            self.class_teacher_combo.addItem("بدون معلم", None)
            for teacher in teachers:
                self.class_teacher_combo.addItem(f"{teacher.full_name}", teacher.id)
            self.class_teacher_combo.blockSignals(False)
            
            # بارگذاری در assign_teacher_combo
            self.assign_teacher_combo.blockSignals(True)
            self.assign_teacher_combo.clear()
            self.assign_teacher_combo.addItem("انتخاب معلم...", None)
            for teacher in teachers:
                self.assign_teacher_combo.addItem(f"{teacher.full_name}", teacher.id)
            self.assign_teacher_combo.blockSignals(False)
            
            # بارگذاری در ts_teacher_combo
            self.ts_teacher_combo.blockSignals(True)
            self.ts_teacher_combo.clear()
            self.ts_teacher_combo.addItem("انتخاب معلم...", None)
            for teacher in teachers:
                self.ts_teacher_combo.addItem(f"{teacher.full_name}", teacher.id)
            self.ts_teacher_combo.blockSignals(False)
                
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری معلمان: {e}")
    
    def on_year_changed(self, index):
        """وقتی سال تحصیلی تغییر می‌کند"""
        self.current_year_id = self.year_combo.currentData()
        self.load_classes()
        self.load_assign_students()
        self.load_teacher_students()
    
    def refresh_all(self):
        """به‌روزرسانی همه داده‌ها"""
        self.load_academic_years()
        self.load_teachers()
        self.load_classes()
        self.load_assign_students()
        self.load_teacher_students()
        QMessageBox.information(self, "موفقیت", "✅ همه داده‌ها با موفقیت به‌روزرسانی شدند.")
    
    # ============================================================
    # متدهای تب کلاس‌ها
    # ============================================================
    
    def load_classes(self):
        """بارگذاری کلاس‌ها در جدول"""
        try:
            year_id = self.year_combo.currentData()
            classes = self.class_dal.get_classes_with_stats(year_id)
            self.class_table.setRowCount(len(classes))
            
            grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}
            
            # نام معلم‌ها یک‌جا خوانده می‌شود (رفع N+1)
            teacher_names = self.staff_dal.get_names_by_ids(
                it['class'].teacher_id for it in classes)
            for row, item in enumerate(classes):
                class_obj = item['class']
                
                self.class_table.setItem(row, 0, QTableWidgetItem(str(class_obj.id)))
                self.class_table.setItem(row, 1, QTableWidgetItem(class_obj.name or ""))
                self.class_table.setItem(row, 2, QTableWidgetItem(grade_names.get(class_obj.grade, str(class_obj.grade)) if class_obj.grade else "-"))
                
                teacher_name = teacher_names.get(class_obj.teacher_id) or "بدون معلم"
                self.class_table.setItem(row, 3, QTableWidgetItem(teacher_name))
                
                self.class_table.setItem(row, 4, QTableWidgetItem(str(item['student_count'])))
                
                # دکمه‌های عملیات
                btn_widget = QWidget()
                btn_layout = QHBoxLayout()
                btn_layout.setContentsMargins(2, 2, 2, 2)
                btn_layout.setSpacing(2)
                
                edit_btn = QPushButton("✏️")
                edit_btn.setFixedSize(30, 30)
                edit_btn.setStyleSheet("background-color: #F4D35E; color: #111111; border: none; border-radius: 4px;")
                edit_btn.clicked.connect(lambda checked, c=class_obj: self.edit_class(c))
                btn_layout.addWidget(edit_btn)
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 30)
                delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 4px;")
                delete_btn.clicked.connect(lambda checked, c=class_obj: self.delete_class(c))
                btn_layout.addWidget(delete_btn)
                
                btn_widget.setLayout(btn_layout)
                self.class_table.setCellWidget(row, 5, btn_widget)
                self.class_table.setRowHeight(row, 35)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری کلاس‌ها:\n{e!s}")
    
    def add_class(self):
        """افزودن کلاس جدید"""
        name = self.class_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "خطا", "لطفاً نام کلاس را وارد کنید.")
            return
        
        grade = self.class_grade_combo.currentData()
        teacher_id = self.class_teacher_combo.currentData()
        capacity = self.class_capacity_spin.value()
        
        # دریافت سال تحصیلی
        year_id = self.year_combo.currentData()
        if not year_id:
            QMessageBox.warning(self, "خطا", "لطفاً یک سال تحصیلی را انتخاب کنید.")
            return
        
        try:
            if self._editing_class_id:
                # ===== حالت ویرایش (بازرسی شانزدهم) =====
                class_obj = self.class_dal.get_by_id(self._editing_class_id)
                if class_obj is None:
                    raise ValueError("کلاس موردنظر دیگر وجود ندارد.")
                class_obj.name = name
                class_obj.grade = grade
                class_obj.teacher_id = teacher_id
                class_obj.capacity = capacity
                self.class_dal.update(class_obj)
                saved = self.class_dal.get_by_id(class_obj.id)
                if saved is None or saved.name != name or saved.grade != grade:
                    raise ValueError("تغییرات در دیتابیس ثبت نشد.")
                self.cancel_edit_class()
                self.load_classes()
                QMessageBox.information(self, "موفقیت", f"✅ کلاس {name} ویرایش شد.")
                return

            class_obj = ClassModel()
            class_obj.name = name
            class_obj.grade = grade
            class_obj.teacher_id = teacher_id
            class_obj.academic_year_id = year_id
            class_obj.capacity = capacity
            class_obj.is_active = 1
            
            self.class_dal.create(class_obj)
            
            self.class_name_input.clear()
            self.class_capacity_spin.setValue(30)
            self.load_classes()
            
            QMessageBox.information(self, "موفقیت", f"✅ کلاس {name} با موفقیت اضافه شد.")
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در ذخیرهٔ کلاس:\n{e!s}")
    
    def edit_class(self, class_obj):
        """
        ویرایش کلاس با همان فرم افزودن (بازرسی شانزدهم)

        قبلاً فقط پیام «در نسخهٔ بعدی» داده می‌شد، در حالی که
        ClassDAL.update وجود داشت. سال تحصیلی کلاس در ویرایش تغییر نمی‌کند.
        """
        self._editing_class_id = class_obj.id
        self.class_name_input.setText(class_obj.name or "")
        idx = self.class_grade_combo.findData(class_obj.grade)
        if idx >= 0:
            self.class_grade_combo.setCurrentIndex(idx)
        idx = self.class_teacher_combo.findData(class_obj.teacher_id)
        self.class_teacher_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.class_capacity_spin.setValue(int(class_obj.capacity or 0))
        self.add_class_btn.setText(f"💾 ذخیرهٔ تغییرات کلاس {class_obj.display_name}")
        self.cancel_edit_class_btn.setVisible(True)
        self.class_name_input.setFocus()

    def cancel_edit_class(self):
        """خروج از حالت ویرایش"""
        self._editing_class_id = None
        self.class_name_input.clear()
        self.class_capacity_spin.setValue(30)
        self.class_teacher_combo.setCurrentIndex(0)
        self.add_class_btn.setText("➕ افزودن کلاس")
        self.cancel_edit_class_btn.setVisible(False)
    
    def delete_class(self, class_obj):
        """حذف کلاس"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف کلاس {class_obj.display_name} اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.class_dal.delete(class_obj.id)
                self.load_classes()
                QMessageBox.information(self, "موفقیت", "✅ کلاس با موفقیت حذف شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{e!s}")
    
    # ============================================================
    # متدهای تب اختصاص معلم
    # ============================================================
    
    def load_assign_students(self):
        """بارگذاری انتساب‌های معلم انتخاب شده"""
        teacher_id = self.assign_teacher_combo.currentData()
        year_id = self.year_combo.currentData()
        
        if not teacher_id:
            self.assign_table.setRowCount(0)
            return
        
        try:
            if year_id:
                assignments = self.assignment_dal.get_by_teacher(teacher_id, year_id)
            else:
                assignments = self.assignment_dal.get_by_teacher(teacher_id, include_inactive=True)
            
            self.assign_table.setRowCount(len(assignments))
            
            for row, assignment in enumerate(assignments):
                self.assign_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.assign_table.setItem(row, 1, QTableWidgetItem(assignment.student_name or "نامشخص"))
                self.assign_table.setItem(row, 2, QTableWidgetItem(str(assignment.grade) if assignment.grade else "-"))
                self.assign_table.setItem(row, 3, QTableWidgetItem(assignment.class_name or "-"))
                
                status_item = QTableWidgetItem("🟢 فعال" if assignment.is_active == 1 else "🔴 غیرفعال")
                if assignment.is_active == 1:
                    status_item.setBackground(QColor(200, 255, 200))
                else:
                    status_item.setBackground(QColor(255, 200, 200))
                self.assign_table.setItem(row, 4, status_item)
                
                # دکمه‌ها
                btn_widget = QWidget()
                btn_layout = QHBoxLayout()
                btn_layout.setContentsMargins(2, 2, 2, 2)
                
                edit_btn = QPushButton("✏️")
                edit_btn.setFixedSize(30, 30)
                edit_btn.setStyleSheet("background-color: #F4D35E; color: #111111; border: none; border-radius: 4px;")
                edit_btn.clicked.connect(lambda checked, a=assignment: self.edit_assignment(a))
                btn_layout.addWidget(edit_btn)
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 30)
                delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 4px;")
                delete_btn.clicked.connect(lambda checked, a=assignment: self.delete_assignment(a))
                btn_layout.addWidget(delete_btn)
                
                btn_widget.setLayout(btn_layout)
                self.assign_table.setCellWidget(row, 5, btn_widget)
                self.assign_table.setRowHeight(row, 40)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری انتساب‌ها:\n{e!s}")
    
    def open_assign_dialog(self):
        """باز کردن دیالوگ اختصاص معلم"""
        dialog = AssignTeacherDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_assign_students()
            self.load_teacher_students()
            QMessageBox.information(self, "موفقیت", "✅ معلم با موفقیت اختصاص داده شد.")
    
    def edit_assignment(self, assignment):
        """ویرایش انتساب"""
        dialog = AssignTeacherDialog(assignment_id=assignment.id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_assign_students()
            self.load_teacher_students()
            QMessageBox.information(self, "موفقیت", "✅ اطلاعات معلم با موفقیت ویرایش شد.")
    
    def delete_assignment(self, assignment):
        """حذف انتساب"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف اختصاص معلم {assignment.teacher_name} از دانش‌آموز {assignment.student_name} اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.assignment_dal.delete(assignment.id)
                self.load_assign_students()
                self.load_teacher_students()
                QMessageBox.information(self, "موفقیت", "✅ اختصاص معلم با موفقیت حذف شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{e!s}")
    
    # ============================================================
    # متدهای تب دانش‌آموزان معلم
    # ============================================================
    
    def load_teacher_students(self):
        """بارگذاری دانش‌آموزان معلم انتخاب شده"""
        teacher_id = self.ts_teacher_combo.currentData()
        year_id = self.year_combo.currentData()
        
        if not teacher_id:
            self.ts_students_table.setRowCount(0)
            self.ts_count_label.setText("تعداد: 0 دانش‌آموز")
            self.ts_details_text.clear()
            return
        
        try:
            if year_id:
                assignments = self.assignment_dal.get_by_teacher(teacher_id, year_id)
            else:
                assignments = self.assignment_dal.get_by_teacher(teacher_id, include_inactive=True)
            
            self.ts_students_table.setRowCount(len(assignments))
            self.ts_count_label.setText(f"تعداد: {len(assignments)} دانش‌آموز")
            
            for row, assignment in enumerate(assignments):
                self.ts_students_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.ts_students_table.setItem(row, 1, QTableWidgetItem(assignment.student_name or "نامشخص"))
                self.ts_students_table.setItem(row, 2, QTableWidgetItem(str(assignment.grade) if assignment.grade else "-"))
                self.ts_students_table.setItem(row, 3, QTableWidgetItem(assignment.class_name or "-"))
                
                status_item = QTableWidgetItem("🟢 فعال" if assignment.is_active == 1 else "🔴 غیرفعال")
                if assignment.is_active == 1:
                    status_item.setBackground(QColor(200, 255, 200))
                else:
                    status_item.setBackground(QColor(255, 200, 200))
                self.ts_students_table.setItem(row, 4, status_item)
                self.ts_students_table.setRowHeight(row, 35)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری دانش‌آموزان:\n{e!s}")
    
    def on_ts_student_double_clicked(self, item):
        """وقتی دانش‌آموز دابل‌کلیک می‌شود"""
        self.view_full_profile()
    
    def view_full_profile(self):
        """مشاهده پرونده کامل دانش‌آموز"""
        row = self.ts_students_table.currentRow()
        if row >= 0:
            # دریافت student_id از جدول
            item = self.ts_students_table.item(row, 1)
            if item:
                # پیدا کردن دانش‌آموز از لیست
                teacher_id = self.ts_teacher_combo.currentData()
                year_id = self.year_combo.currentData()
                if teacher_id:
                    if year_id:
                        assignments = self.assignment_dal.get_by_teacher(teacher_id, year_id)
                    else:
                        assignments = self.assignment_dal.get_by_teacher(teacher_id, include_inactive=True)
                    
                    if row < len(assignments):
                        student_id = assignments[row].student_id
                        self.student_selected.emit(student_id)
                        return
        
        QMessageBox.warning(self, "توجه", "لطفاً یک دانش‌آموز را انتخاب کنید.")