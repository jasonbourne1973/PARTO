"""
صفحه مدیریت دانش‌آموزان - نسخه با جستجوی سریع و پیشرفته و Pagination
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from dal.academic_year_dal import AcademicYearDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from services.student_service import StudentService
from utils.logger import get_logger
from utils.security import AccessControl, Permission
from utils.time_utils import utc_now
from views.dialogs.student_form import StudentForm
from views.pages.student_profile_page import StudentProfilePage
from views.pages.year_sync import YearAwarePage
from views.widgets.deleted_records import (
    ask_restore_confirmation,
    current_user_id,
    deleted_label,
    make_restore_button,
    make_show_deleted_checkbox,
    report_restore_failure,
)

logger = get_logger(__name__)


class StudentsPage(YearAwarePage, QWidget):
    """صفحه مدیریت دانش‌آموزان با جستجوی سریع و پیشرفته و Pagination"""
    
    student_double_clicked = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.academic_year_dal = AcademicYearDAL()
        # مسیر بازیابی باید از لایهٔ سرویس بگذرد (بررسی نتیجهٔ واقعی + Audit)
        self.student_service = StudentService()
        
        self.students = []
        # (دور نوزدهم، مرحلهٔ ۶) all_students دیگر «کل فهرست فیلترشده» را در
        # هر بارگذاری/جست‌وجو نگه نمی‌دارد (آن الگو یعنی لود کامل جدول در
        # هر تغییر صفحه/کاراکتر جست‌وجو). این فهرست فقط هنگام خروجی Excel
        # (export_to_excel) به‌صورت جداگانه و کامل واکشی می‌شود؛ صفحه‌بندی
        # نمایش از total_count + LIMIT/OFFSET واقعی SQL استفاده می‌کند.
        self.all_students = []
        self.total_count = 0
        self.showing_deleted = False
        self.current_page = 0
        self.page_size = 20
        self.total_pages = 1
        
        self.setup_ui()
        self.load_students()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        title_label = QLabel("📋 دانش‌آموزان")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #F4C542;
            }
        """)
        main_layout.addWidget(title_label)
        
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
        
        list_tab = QWidget()
        layout = QVBoxLayout()
        list_tab.setLayout(layout)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        toolbar.addStretch()
        
        # ===== جعبه جستجو =====
        search_label = QLabel("🔍 جستجو:")
        search_label.setStyleSheet("font-weight: bold;")
        toolbar.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("نام، نام خانوادگی، کد ملی...")
        self.search_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                padding: 8px;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                font-size: 13px;
                min-width: 200px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F;
                border: 2px solid #F4C542;
            }
        """)
        self.search_input.textChanged.connect(self.search_students)
        toolbar.addWidget(self.search_input)
        
        # دکمه جستجوی پیشرفته
        self.advanced_search_btn = QPushButton("🔍 پیشرفته")
        self.advanced_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #66BB6A; }
        """)
        self.advanced_search_btn.clicked.connect(self.open_advanced_search)
        toolbar.addWidget(self.advanced_search_btn)
        
        self.add_btn = QPushButton("➕ افزودن دانش‌آموز")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #08223A;
            }
        """)
        self.add_btn.clicked.connect(self.add_student)
        # (دور نوزدهم) دکمهٔ افزودن هم مثل دکمهٔ حذف با همان مرز backend
        # هماهنگ می‌شود (DD-5) — بدون CREATE_STUDENT، UI و backend هر دو
        # اجازهٔ ساخت دانش‌آموز جدید نمی‌دهند.
        self.add_btn.setEnabled(
            AccessControl.has_permission(Permission.CREATE_STUDENT.value))
        toolbar.addWidget(self.add_btn)
        
        # ===== دکمه‌های ایمپورت و اکسل (جدید) =====
        self.import_btn = QPushButton("📥 ایمپورت از Excel")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8BC34A;
            }
        """)
        self.import_btn.clicked.connect(self.import_from_excel)
        # (دور نوزدهم) ایمپورت هم CREATE_STUDENT لازم دارد؛ همان مرز UI↔backend
        self.import_btn.setEnabled(
            AccessControl.has_permission(Permission.CREATE_STUDENT.value))
        toolbar.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("📤 خروجی Excel")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #08223A;
            }
        """)
        self.export_btn.clicked.connect(self.export_to_excel)
        toolbar.addWidget(self.export_btn)
        
        self.sample_btn = QPushButton("📄 دریافت نمونه")
        self.sample_btn.setStyleSheet("""
            QPushButton {
                background-color: #F4D35E;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F28C28;
            }
        """)
        self.sample_btn.clicked.connect(self.download_sample_excel)
        toolbar.addWidget(self.sample_btn)

        # (دور هفدهم — BUG-RESTORE-01) مسیر واقعی بازیابی دانش‌آموز:
        # DAL.restore وجود داشت ولی هیچ راهی در UI به آن نمی‌رسید.
        self.show_deleted_check = make_show_deleted_checkbox(
            self, "on_show_deleted_toggled",
            "دانش‌آموزان حذف‌شده را نشان می‌دهد تا با ↩️ بازیابی شوند.")
        toolbar.addWidget(self.show_deleted_check)

        layout.addLayout(toolbar)
        
        # ===== جدول =====
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ردیف", "نام", "نام خانوادگی", "پایه", "کلاس",
            "کد ملی", "عملیات"
        ])
        
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
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
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.table)
        
        # ===== بخش Pagination =====
        pagination_layout = QHBoxLayout()
        
        self.page_label = QLabel("صفحه 1 از 1")
        self.page_label.setStyleSheet("font-size: 13px; color: #D9C36A;")
        pagination_layout.addWidget(self.page_label)
        
        pagination_layout.addStretch()
        
        self.prev_page_btn = QPushButton("◀ قبلی")
        self.prev_page_btn.setFixedWidth(80)
        self.prev_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 5px 10px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #08223A; }
            QPushButton:disabled { background-color: #D9C36A; }
        """)
        self.prev_page_btn.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_page_btn)
        
        self.next_page_btn = QPushButton("بعدی ▶")
        self.next_page_btn.setFixedWidth(80)
        self.next_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 5px 10px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #08223A; }
            QPushButton:disabled { background-color: #D9C36A; }
        """)
        self.next_page_btn.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_page_btn)
        
        pagination_layout.addWidget(QLabel("تعداد در صفحه:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "20", "50", "100"])
        self.page_size_combo.setCurrentText("20")
        self.page_size_combo.currentTextChanged.connect(self.load_students)
        pagination_layout.addWidget(self.page_size_combo)
        
        layout.addLayout(pagination_layout)
        
        self.tabs.addTab(list_tab, "📋 لیست دانش‌آموزان")
        
        self.profile_page = StudentProfilePage()
        self.tabs.addTab(self.profile_page, "👤 پرونده دانش‌آموز")
        
        main_layout.addWidget(self.tabs)
    
    def open_profile_tab(self, student_id):
        """باز کردن تب پرونده دانش‌آموز"""
        self.profile_page.set_student_id(student_id)
        self.tabs.setCurrentIndex(1)
    
    def on_show_deleted_toggled(self, checked):
        """تغییر حالت نمایش حذف‌شده‌ها → بازگشت به صفحهٔ اول و بارگذاری دوباره"""
        self.showing_deleted = bool(checked)
        self.current_page = 0
        self.load_students()

    def load_students(self):
        """
        بارگذاری لیست دانش‌آموزان با Pagination واقعی (یا فهرست حذف‌شده‌ها)

        (دور نوزدهم، مرحلهٔ ۶ — اصلاح Query/Pagination) قبلاً این متد کل
        دانش‌آموزان فیلترشده را از دیتابیس می‌خواند و بعد در پایتون
        صفحه‌بندی (slice) می‌کرد؛ حالا شمارش کل با COUNT و ردیف‌های همان
        صفحه با LIMIT/OFFSET واقعی گرفته می‌شوند.
        """
        try:
            self.page_size = int(self.page_size_combo.currentText())
            if self.showing_deleted:
                # مسیر بازیابی: فقط رکوردهای حذف‌شده، از لایهٔ سرویس
                self.total_count = self.student_service.count_deleted_students()
            else:
                self.total_count = self.student_dal.count_all()

            # (بدون max(1, ...) عمداً؛ فرمول دقیقاً همان قدیمی است — فهرست
            # خالی باید total_pages=0 بدهد، برچسب صفحه در
            # update_pagination_controls جداگانه با max(1, ...) نمایش داده
            # می‌شود؛ همان قراردادی که verify_fixes17 §D2 آزمون می‌کند.)
            self.total_pages = (self.total_count + self.page_size - 1) // self.page_size
            self.current_page = min(self.current_page, self.total_pages - 1)
            if self.current_page < 0:
                self.current_page = 0

            offset = self.current_page * self.page_size
            if self.showing_deleted:
                self.students = self.student_service.get_deleted_students(
                    self.page_size, offset)
            else:
                self.students = self.student_dal.get_all(self.page_size, offset)

            self.display_students(self.students)
            self.update_pagination_controls()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری دانش‌آموزان:\n{e!s}")
    
    def reload_for_year(self, year_id):
        """
        بارگذاری دوبارهٔ فهرست دانش‌آموزان برای سال اعلام‌شده

        ستون «پایه/کلاس» از پروندهٔ سالانهٔ هر دانش‌آموز می‌آید؛ با تغییر
        سال، همان پرونده‌های سال جدید خوانده می‌شوند. صفحهٔ «پرونده
        دانش‌آموز» که داخل همین صفحه است هم انتخاب سال را می‌گیرد.
        """
        self.current_page = 0
        self.load_students()
        profile_page = getattr(self, "profile_page", None)
        setter = getattr(profile_page, "set_active_year", None)
        if callable(setter):
            setter(year_id)
        return True

    def update_pagination_controls(self):
        """به‌روزرسانی کنترل‌های Pagination"""
        self.page_label.setText(f"صفحه {self.current_page + 1} از {max(1, self.total_pages)}")
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)
    
    def prev_page(self):
        """رفتن به صفحه قبل"""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_students()
    
    def next_page(self):
        """رفتن به صفحه بعد"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.load_students()
    
    def get_student_info(self, student_id):
        """دریافت اطلاعات پرونده فعال دانش‌آموز"""
        try:
            profile = self.profile_dal.get_active_by_student(student_id)
            if profile:
                return {
                    'grade': profile.grade_display,
                    'class': profile.class_name or ''
                }
        except Exception as e:
            # نبود پروندهٔ فعال برای این سال → ستون‌های پایه/کلاس خالی
            logger.debug(f"پروندهٔ سالانهٔ دانش‌آموز {student_id} خوانده نشد: {e}")
        return {'grade': '-', 'class': '-'}
    
    def display_students(self, students):
        """نمایش دانش‌آموزان در جدول (حالت حذف‌شده: فقط بازیابی)"""
        self.table.setRowCount(len(students))
        
        for row, student in enumerate(students):
            info = self.get_student_info(student.id) if not self.showing_deleted else None
            
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(student.first_name or ""))
            last_name = student.last_name or ""
            if self.showing_deleted:
                last_name = deleted_label(last_name)
            self.table.setItem(row, 2, QTableWidgetItem(last_name))
            self.table.setItem(row, 3, QTableWidgetItem(info['grade'] if info else '-'))
            self.table.setItem(row, 4, QTableWidgetItem(info['class'] if info else '-'))
            self.table.setItem(row, 5, QTableWidgetItem(student.national_code or ""))
            
            # دکمه‌های عملیات
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(2)

            if self.showing_deleted:
                # رکورد حذف‌شده فقط یک کار منطقی دارد: بازیابی؛ ولی فقط
                # برای کسی که مجوز حذف/بازیابی دارد (UI↔backend هماهنگ)
                if AccessControl.has_permission(Permission.DELETE_STUDENT.value):
                    btn_layout.addWidget(
                        make_restore_button(student, self.restore_student))
                btn_widget.setLayout(btn_layout)
                self.table.setCellWidget(row, 6, btn_widget)
                self.table.setRowHeight(row, 40)
                continue

            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F4D35E;
                    color: #111111;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #F28C28;
                }
            """)
            edit_btn.clicked.connect(lambda checked, s=student: self.edit_student(s))
            # (دور نوزدهم) هماهنگ با EDIT_STUDENT در DAL — UI↔backend یک مرز
            edit_btn.setEnabled(
                AccessControl.has_permission(Permission.EDIT_STUDENT.value))
            btn_layout.addWidget(edit_btn)
            
            if AccessControl.has_permission(Permission.DELETE_STUDENT.value):
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 30)
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #C62828;
                        color: #F4C542;
                        border: none;
                        border-radius: 4px;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #9E1B1B;
                    }
                """)
                delete_btn.clicked.connect(
                    lambda checked, s=student: self.delete_student(s))
                btn_layout.addWidget(delete_btn)
            
            profile_btn = QPushButton("👤")
            profile_btn.setFixedSize(30, 30)
            profile_btn.setStyleSheet("""
                QPushButton {
                    background-color: #66BB6A;
                    color: #111111;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #7d3c98;
                }
            """)
            profile_btn.clicked.connect(lambda checked, s=student: self.open_profile(s))
            btn_layout.addWidget(profile_btn)
            
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 6, btn_widget)
            self.table.setRowHeight(row, 40)
    
    def search_students(self):
        """
        جستجوی دانش‌آموزان با Pagination واقعی

        (دور نوزدهم، مرحلهٔ ۶) مانند load_students، شمارش کل با COUNT
        (در SQL) و ردیف‌های صفحهٔ جاری با LIMIT/OFFSET گرفته می‌شوند؛
        دیگر فهرست کامل در پایتون فیلتر/برش زده نمی‌شود. جست‌وجو در حالت
        «نمایش حذف‌شده‌ها» هم اکنون در همان SQL (نه حلقهٔ پایتونی) روی
        فقط رکوردهای حذف‌شده انجام می‌شود.
        """
        search_term = self.search_input.text().strip()
        
        if not search_term:
            self.load_students()
            return
        
        try:
            self.current_page = 0
            if self.showing_deleted:
                # در حالت نمایش حذف‌شده‌ها، جست‌وجو روی همان فهرست حذف‌شده
                # انجام می‌شود (وگرنه فهرستِ فعال جای حالت بازیابی را می‌گرفت).
                self.total_count = self.student_service.count_search_deleted_students(
                    search_term)
            else:
                self.total_count = self.student_dal.count_search(search_term)

            # (همان توضیح load_students: بدون max(1, ...) عمداً)
            self.total_pages = (self.total_count + self.page_size - 1) // self.page_size

            offset = self.current_page * self.page_size
            if self.showing_deleted:
                self.students = self.student_service.search_deleted_students(
                    search_term, self.page_size, offset)
            else:
                self.students = self.student_dal.search(
                    search_term, limit=self.page_size, offset=offset)
            
            self.display_students(self.students)
            self.update_pagination_controls()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در جستجو:\n{e!s}")
    
    def open_advanced_search(self):
        """باز کردن دیالوگ جستجوی پیشرفته"""
        from views.dialogs.advanced_search_dialog import AdvancedSearchDialog
        dialog = AdvancedSearchDialog(self)
        dialog.student_selected.connect(self.open_profile_by_id)
        dialog.exec()
    
    def open_profile_by_id(self, student_id):
        """باز کردن پرونده دانش‌آموز با شناسه"""
        self.student_double_clicked.emit(student_id)
    
    def on_item_double_clicked(self, item):
        """باز کردن پرونده دانش‌آموز با دابل‌کلیک"""
        row = item.row()
        if row < len(self.students):
            student = self.students[row]
            self.open_profile(student)
    
    def open_profile(self, student):
        """باز کردن پرونده دانش‌آموز"""
        self.student_double_clicked.emit(student.id)
    
    def add_student(self):
        """
        افزودن دانش‌آموز جدید - باز کردن فرم ثبت

        (دور هفدهم — بند ۱۳ مأموریت) پیام موفقیت فقط در «یک» لایه نمایش
        داده می‌شود: خودِ فرم پس از ذخیرهٔ موفق پیام می‌دهد. قبلاً همین
        پیام این‌جا هم دوباره نشان داده می‌شد و کاربر برای یک ذخیره دو
        پیام می‌دید. این‌جا فقط فهرست یک‌بار تازه می‌شود.
        """
        try:
            form = StudentForm(parent=self)
            result = form.exec()
            if result == QDialog.DialogCode.Accepted:
                self.load_students()
        except Exception as e:
            logger.error(f"خطا در باز کردن فرم دانش‌آموز: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"مشکل در باز کردن فرم:\n{e!s}")
    
    def edit_student(self, student):
        """
        ویرایش دانش‌آموز

        مثل «افزودن»، پیام موفقیت فقط از سمت فرم می‌آید و این‌جا تنها
        فهرست یک‌بار تازه می‌شود (بدون پیام تکراری).
        """
        form = StudentForm(student=student, parent=self)
        if form.exec() == QDialog.DialogCode.Accepted:
            self.load_students()
    
    def delete_student(self, student):
        """حذف دانش‌آموز"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف دانش‌آموز '{student.full_name}' اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted = self.student_dal.delete(student.id)
                self.load_students()
                if deleted:
                    QMessageBox.information(
                        self, "موفقیت", "دانش‌آموز با موفقیت حذف شد"
                    )
                else:
                    QMessageBox.warning(
                        self, "خطا", "دانش‌آموز مورد نظر حذف نشد."
                    )
            except Exception as e:
                # خطای حذف نباید بی‌صدا بماند: پیام کاربر + traceback در لاگ
                logger.error(f"خطا در حذف دانش‌آموز {student.id}: {e}", exc_info=True)
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{e!s}")
    
    def restore_student(self, student):
        """
        بازیابی دانش‌آموز حذف‌شده (دور هفدهم — BUG-RESTORE-01)

        مسیر کامل: UI → StudentService.restore_student → StudentDAL.restore
        موفقیت فقط بعد از نتیجهٔ واقعی سرویس اعلام می‌شود؛ پروندهٔ سالانه و
        سال تحصیلی رکورد دست‌نخورده می‌ماند.
        """
        full_name = f"{student.first_name or ''} {student.last_name or ''}".strip()
        if not ask_restore_confirmation(
                self, f"آیا دانش‌آموز «{full_name}» بازیابی شود؟"):
            return

        try:
            restored = self.student_service.restore_student(
                student.id, user_id=current_user_id())
        except Exception as e:
            report_restore_failure(self, e)
            return

        self.load_students()
        if restored is not None:
            QMessageBox.information(
                self, "موفقیت",
                f"دانش‌آموز «{full_name}» بازیابی شد. برای دیدنش تیک "
                "«نمایش حذف‌شده‌ها» را بردارید.")
        else:  # pragma: no cover - سرویس در نبود اثر خطا می‌دهد
            QMessageBox.warning(self, "توجه", "بازیابی انجام نشد.")

    # ===== متدهای جدید برای Excel =====
    
    def export_to_excel(self):
        """
        خروجی Excel از دانش‌آموزان

        (دور نوزدهم، مرحلهٔ ۶) از این پس load_students/search_students
        فقط ردیف‌های همان صفحه را نگه می‌دارند؛ خروجی Excel باید تمام
        دانش‌آموزانِ منطبق با فیلتر جاری (نه فقط صفحهٔ نمایشی) باشد،
        بنابراین اینجا — و فقط اینجا، در لحظهٔ کلیک خروجی — یک واکشیِ
        کامل (بدون LIMIT) با همان فیلتر جاری (حذف‌شده/فعال + متن جست‌وجو)
        انجام می‌شود؛ رفتار قابل‌مشاهده با قبل از این تغییر یکسان است.
        """
        search_term = self.search_input.text().strip()
        try:
            if self.showing_deleted:
                if search_term:
                    self.all_students = self.student_service.search_deleted_students(
                        search_term)
                else:
                    self.all_students = self.student_service.get_deleted_students()
            elif search_term:
                self.all_students = self.student_dal.search(search_term)
            else:
                self.all_students = self.student_dal.get_all()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در خروجی:\n{e!s}")
            return

        export_students = self.all_students or self.students
        if not export_students:
            QMessageBox.warning(
                self, "توجه", "هیچ دانش‌آموزی برای خروجی وجود ندارد."
            )
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل Excel",
            f"دانش‌آموزان_{utc_now().strftime('%Y%m%d')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            from utils.excel_importer import ExcelImporter
            importer = ExcelImporter()
            
            active_year = self.academic_year_dal.get_active()
            # (دور هفدهم — بند ۱۵) اگر صفحه در حالت «نمایش حذف‌شده‌ها»
            # باشد، فایل باید خودش بگوید داده‌های حذف‌شده‌اند؛ وگرنه فایلی
            # با عنوان «لیست دانش‌آموزان» می‌سازیم که خواننده‌اش نمی‌فهمد
            # این ردیف‌ها در فهرست فعال نیستند.
            success, message = importer.export_students_to_excel(
                export_students, file_path, active_year,
                deleted_view=self.showing_deleted,
            )
            
            if success:
                QMessageBox.information(self, "موفقیت", message)
            else:
                QMessageBox.critical(self, "خطا", message)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در خروجی:\n{e!s}")
    
    def import_from_excel(self):
        """ایمپورت دانش‌آموزان از Excel"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب فایل Excel",
            "",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        # انتخاب سال تحصیلی
        years = self.academic_year_dal.get_all()
        if not years:
            QMessageBox.warning(self, "توجه", "هیچ سال تحصیلی فعالی وجود ندارد. لطفاً ابتدا یک سال ایجاد کنید.")
            return
        
        # دیالوگ ساده برای انتخاب سال
        dialog = QDialog(self)
        dialog.setWindowTitle("انتخاب سال تحصیلی")
        dialog.setModal(True)
        dialog_layout = QVBoxLayout()
        
        dialog_layout.addWidget(QLabel("لطفاً سال تحصیلی را انتخاب کنید:"))
        year_combo = QComboBox()
        for year in years:
            year_combo.addItem(year.title, year.id)
        dialog_layout.addWidget(year_combo)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        dialog_layout.addWidget(button_box)
        
        dialog.setLayout(dialog_layout)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        year_id = year_combo.currentData()
        
        try:
            from utils.excel_importer import ExcelImporter
            importer = ExcelImporter()
            
            # ایمپورت
            # imported_count داخل message گزارش می‌شود
            success, message, _imported_count, errors = importer.import_students_from_excel(
                file_path, year_id
            )
            
            # (دور هفدهم — بند ۱۴) جزئیات خطاها در «هر دو» مسیر نمایش داده
            # می‌شود. قبلاً فقط مسیر موفقیت خطاها را نشان می‌داد؛ یعنی وقتی
            # همهٔ ردیف‌ها رد می‌شدند کاربر فقط تعداد خطا را می‌دید و دلیل
            # هیچ ردیفی را نمی‌فهمید.
            msg = message
            if errors:
                # نمایش ۱۰ خطای اول
                error_text = "\n".join(errors[:10])
                if len(errors) > 10:
                    error_text += f"\n... و {len(errors)-10} خطای دیگر"
                msg += f"\n\nخطاها:\n{error_text}"

            if success:
                self.load_students()
                QMessageBox.information(self, "نتیجه ایمپورت", msg)
            else:
                QMessageBox.critical(self, "خطای ایمپورت", msg)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در ایمپورت:\n{e!s}")
    
    def download_sample_excel(self):
        """دانلود فایل نمونه Excel"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل نمونه",
            "نمونه_دانش‌آموزان.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            from utils.excel_importer import ExcelImporter
            importer = ExcelImporter()
            success, message = importer.create_sample_excel(file_path)
            
            if success:
                QMessageBox.information(self, "موفقیت", message)
            else:
                QMessageBox.critical(self, "خطا", message)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در ایجاد فایل نمونه:\n{e!s}")