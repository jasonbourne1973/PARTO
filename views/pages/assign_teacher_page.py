"""
صفحه مدیریت اختصاص معلم به دانش‌آموزان - نسخه کامل
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
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
from dal.staff_dal import StaffDAL

# ===== اصلاح =====
# در جدول «دانش‌آموزان بدون معلم» از `self.profile_dal` استفاده می‌شد
# ولی این ویژگی هیچ‌جا در __init__ ساخته نمی‌شد. نتیجه: hasattr همیشه
# False بود و ستون‌های «پایه» و «کلاس» برای همه دانش‌آموزان به ترتیب
# «نامشخص» و خالی نمایش داده می‌شدند.
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from utils.logger import get_logger
from views.dialogs.assign_teacher_dialog import AssignTeacherDialog

logger = get_logger(__name__)


class AssignTeacherPage(QWidget):
    """صفحه مدیریت اختصاص معلم به دانش‌آموزان"""
    
    assignment_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.student_dal = StudentDAL()
        self.staff_dal = StaffDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        # ===== اصلاح =====
        # بدون این خط ستون پایه/کلاس در جدول دانش‌آموزان بدون معلم خالی می‌ماند.
        self.profile_dal = StudentAcademicProfileDAL()
        
        self.students = []
        self.all_teachers = []
        self.selected_student_ids = []
        self.current_assignments = []
        
        self.setup_ui()
        self.load_teachers()
        self.load_academic_years()
        self.load_students()
        self.load_assignments()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== عنوان =====
        title_label = QLabel("👨‍🏫 مدیریت اختصاص معلم به دانش‌آموزان")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        layout.addWidget(title_label)
        
        # ===== نوار انتخاب معلم و سال =====
        toolbar = QHBoxLayout()
        
        toolbar.addWidget(QLabel("انتخاب معلم:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.setMinimumWidth(200)
        self.teacher_combo.setPlaceholderText("انتخاب معلم...")
        self.teacher_combo.currentIndexChanged.connect(self.on_teacher_changed)
        toolbar.addWidget(self.teacher_combo)
        
        toolbar.addSpacing(20)
        
        toolbar.addWidget(QLabel("سال تحصیلی:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(150)
        self.year_combo.currentIndexChanged.connect(self.load_assignments)
        toolbar.addWidget(self.year_combo)
        
        toolbar.addStretch()
        
        # دکمه‌ها
        self.assign_btn = QPushButton("➕ اختصاص معلم به دانش‌آموزان")
        self.assign_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #66BB6A; }
        """)
        self.assign_btn.clicked.connect(self.open_assign_dialog)
        toolbar.addWidget(self.assign_btn)
        
        layout.addLayout(toolbar)
        
        # ===== بخش جستجو =====
        search_layout = QHBoxLayout()
        
        search_label = QLabel("🔍 جستجو:")
        search_label.setStyleSheet("font-weight: bold;")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("نام، نام خانوادگی یا کد ملی...")
        self.search_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                padding: 5px 10px;
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
        search_layout.addWidget(self.search_input)
        
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
        search_layout.addWidget(self.clear_search_btn)
        
        layout.addLayout(search_layout)
        
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
            }
            QTabBar::tab:selected {
    border-color: #F4C542;
                background-color: #8BC34A;
                color: #111111;
            }
        """)
        
        # تب 1: دانش‌آموزان بدون معلم
        self.tab_no_teacher = self.create_no_teacher_tab()
        self.tabs.addTab(self.tab_no_teacher, "📋 دانش‌آموزان بدون معلم")
        
        # تب 2: دانش‌آموزان دارای معلم
        self.tab_with_teacher = self.create_with_teacher_tab()
        self.tabs.addTab(self.tab_with_teacher, "👨‍🏫 دانش‌آموزان دارای معلم")
        
        layout.addWidget(self.tabs)
    
    def create_no_teacher_tab(self):
        """ایجاد تب دانش‌آموزان بدون معلم"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.no_teacher_table = QTableWidget()
        self.no_teacher_table.setColumnCount(6)
        self.no_teacher_table.setHorizontalHeaderLabels([
            "✅", "ردیف", "نام و نام خانوادگی", "پایه", "کلاس", "کد ملی"
        ])
        
        self.no_teacher_table.setAlternatingRowColors(True)
        self.no_teacher_table.setStyleSheet("""
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
        
        header = self.no_teacher_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.no_teacher_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.no_teacher_table.itemClicked.connect(self.on_item_clicked)
        
        layout.addWidget(self.no_teacher_table)
        
        # دکمه‌های عملیات برای تب بدون معلم
        btn_layout = QHBoxLayout()
        
        self.assign_selected_btn = QPushButton("📌 اختصاص معلم به انتخاب‌شده")
        self.assign_selected_btn.setStyleSheet("""
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
        self.assign_selected_btn.clicked.connect(self.assign_selected_students)
        btn_layout.addWidget(self.assign_selected_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return tab
    
    def create_with_teacher_tab(self):
        """ایجاد تب دانش‌آموزان دارای معلم"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.with_teacher_table = QTableWidget()
        self.with_teacher_table.setColumnCount(7)
        self.with_teacher_table.setHorizontalHeaderLabels([
            "ردیف", "نام و نام خانوادگی", "پایه", "کلاس", "معلم", "وضعیت", "عملیات"
        ])
        
        self.with_teacher_table.setAlternatingRowColors(True)
        self.with_teacher_table.setStyleSheet("""
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
        
        header = self.with_teacher_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        self.with_teacher_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.with_teacher_table)
        
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
    
    def load_students(self):
        """بارگذاری دانش‌آموزان"""
        try:
            self.students = self.student_dal.get_all()
            self.display_no_teacher_students()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری دانش‌آموزان:\n{str(e)}")
    
    def load_assignments(self):
        """بارگذاری انتساب‌های معلم"""
        try:
            teacher_id = self.teacher_combo.currentData()
            year_id = self.year_combo.currentData()
            
            if teacher_id and year_id:
                self.current_assignments = self.assignment_dal.get_by_teacher(teacher_id, year_id)
            else:
                self.current_assignments = []
            
            self.display_with_teacher_students()
            self.display_no_teacher_students()
            
        except Exception as e:
            logger.error(f"خطا در بارگذاری انتساب‌ها: {e}")
    
    def on_teacher_changed(self, index):
        """وقتی معلم تغییر می‌کند"""
        self.load_assignments()
    
    def display_no_teacher_students(self):
        """نمایش دانش‌آموزان بدون معلم"""
        teacher_id = self.teacher_combo.currentData()
        year_id = self.year_combo.currentData()
        
        if not teacher_id or not year_id:
            self.no_teacher_table.setRowCount(0)
            return
        
        # دریافت شناسه دانش‌آموزانی که معلم دارند
        assigned_student_ids = [a.student_id for a in self.current_assignments]
        
        # فیلتر دانش‌آموزانی که معلم ندارند
        no_teacher_students = [s for s in self.students if s.id not in assigned_student_ids]
        
        self.no_teacher_table.setRowCount(len(no_teacher_students))
        
        for row, student in enumerate(no_teacher_students):
            # دریافت اطلاعات پرونده
            profile = self.profile_dal.get_active_by_student(student.id) if hasattr(self, 'profile_dal') else None
            grade_text = profile.grade_display if profile else "نامشخص"
            class_name = profile.class_name if profile else ""
            
            check_item = QTableWidgetItem("☐")
            check_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            check_item.setData(Qt.ItemDataRole.UserRole, student.id)
            self.no_teacher_table.setItem(row, 0, check_item)
            
            self.no_teacher_table.setItem(row, 1, QTableWidgetItem(str(row + 1)))
            self.no_teacher_table.setItem(row, 2, QTableWidgetItem(student.full_name))
            self.no_teacher_table.setItem(row, 3, QTableWidgetItem(grade_text))
            self.no_teacher_table.setItem(row, 4, QTableWidgetItem(class_name))
            self.no_teacher_table.setItem(row, 5, QTableWidgetItem(student.national_code or ""))
            self.no_teacher_table.setRowHeight(row, 35)
    
    def display_with_teacher_students(self):
        """نمایش دانش‌آموزانی که معلم دارند"""
        self.with_teacher_table.setRowCount(len(self.current_assignments))
        
        for row, assignment in enumerate(self.current_assignments):
            self.with_teacher_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.with_teacher_table.setItem(row, 1, QTableWidgetItem(assignment.student_name or "نامشخص"))
            self.with_teacher_table.setItem(row, 2, QTableWidgetItem(str(assignment.grade) if assignment.grade else "-"))
            self.with_teacher_table.setItem(row, 3, QTableWidgetItem(assignment.class_name or "-"))
            self.with_teacher_table.setItem(row, 4, QTableWidgetItem(assignment.teacher_name or "نامشخص"))
            
            status_item = QTableWidgetItem("🟢 فعال" if assignment.is_active == 1 else "🔴 غیرفعال")
            if assignment.is_active == 1:
                status_item.setBackground(QColor(200, 255, 200))
            else:
                status_item.setBackground(QColor(255, 200, 200))
            self.with_teacher_table.setItem(row, 5, status_item)
            
            # دکمه‌های عملیات
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setStyleSheet("background-color: #F4D35E; color: #F4C542; border: none; border-radius: 4px;")
            edit_btn.clicked.connect(lambda checked, a=assignment: self.edit_assignment(a))
            btn_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 4px;")
            delete_btn.clicked.connect(lambda checked, a=assignment: self.delete_assignment(a))
            btn_layout.addWidget(delete_btn)
            
            btn_widget.setLayout(btn_layout)
            self.with_teacher_table.setCellWidget(row, 6, btn_widget)
            self.with_teacher_table.setRowHeight(row, 40)
    
    def on_item_clicked(self, item):
        """انتخاب/لغو انتخاب دانش‌آموز"""
        row = item.row()
        check_item = self.no_teacher_table.item(row, 0)
        
        if check_item.text() == "☐":
            check_item.setText("☑")
            student_id = check_item.data(Qt.ItemDataRole.UserRole)
            if student_id not in self.selected_student_ids:
                self.selected_student_ids.append(student_id)
        else:
            check_item.setText("☐")
            student_id = check_item.data(Qt.ItemDataRole.UserRole)
            if student_id in self.selected_student_ids:
                self.selected_student_ids.remove(student_id)
    
    def search_students(self):
        """جستجوی دانش‌آموزان"""
        search_term = self.search_input.text().strip()
        
        if not search_term:
            self.load_students()
            return
        
        try:
            results = self.student_dal.search(search_term)
            # فیلتر کردن نتایج برای نمایش در تب بدون معلم
            teacher_id = self.teacher_combo.currentData()
            year_id = self.year_combo.currentData()
            
            if teacher_id and year_id:
                assigned_student_ids = [a.student_id for a in self.current_assignments]
                no_teacher_results = [s for s in results if s.id not in assigned_student_ids]
            else:
                no_teacher_results = results
            
            # نمایش نتایج در جدول بدون معلم
            self.no_teacher_table.setRowCount(len(no_teacher_results))
            
            for row, student in enumerate(no_teacher_results):
                check_item = QTableWidgetItem("☐")
                check_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                check_item.setData(Qt.ItemDataRole.UserRole, student.id)
                self.no_teacher_table.setItem(row, 0, check_item)
                
                self.no_teacher_table.setItem(row, 1, QTableWidgetItem(str(row + 1)))
                self.no_teacher_table.setItem(row, 2, QTableWidgetItem(student.full_name))
                self.no_teacher_table.setItem(row, 3, QTableWidgetItem("نامشخص"))
                self.no_teacher_table.setItem(row, 4, QTableWidgetItem(""))
                self.no_teacher_table.setItem(row, 5, QTableWidgetItem(student.national_code or ""))
                self.no_teacher_table.setRowHeight(row, 35)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در جستجو:\n{str(e)}")
    
    def clear_search(self):
        """پاک کردن جستجو"""
        self.search_input.clear()
        self.load_students()
    
    def assign_selected_students(self):
        """اختصاص معلم به دانش‌آموزان انتخاب شده"""
        if not self.selected_student_ids:
            QMessageBox.warning(self, "توجه", "لطفاً حداقل یک دانش‌آموز را انتخاب کنید.")
            return
        
        teacher_id = self.teacher_combo.currentData()
        if not teacher_id:
            QMessageBox.warning(self, "توجه", "لطفاً یک معلم را انتخاب کنید.")
            return
        
        year_id = self.year_combo.currentData()
        if not year_id:
            QMessageBox.warning(self, "توجه", "لطفاً یک سال تحصیلی را انتخاب کنید.")
            return
        
        # باز کردن دیالوگ اختصاص معلم
        dialog = AssignTeacherDialog(
            student_ids=self.selected_student_ids,
            teacher_id=teacher_id,
            year_id=year_id,
            parent=self
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_student_ids = []
            self.load_assignments()
            self.load_students()
            QMessageBox.information(self, "موفقیت", "معلم با موفقیت به دانش‌آموزان اختصاص داده شد.")
    
    def open_assign_dialog(self):
        """باز کردن دیالوگ اختصاص معلم"""
        dialog = AssignTeacherDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_assignments()
            self.load_students()
    
    def edit_assignment(self, assignment):
        """ویرایش انتساب معلم"""
        dialog = AssignTeacherDialog(
            assignment_id=assignment.id,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_assignments()
            self.load_students()
            QMessageBox.information(self, "موفقیت", "اطلاعات معلم با موفقیت ویرایش شد.")
    
    def delete_assignment(self, assignment):
        """حذف انتساب معلم"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف اختصاص معلم {assignment.teacher_name} از دانش‌آموز {assignment.student_name} اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.assignment_dal.delete(assignment.id)
                self.load_assignments()
                self.load_students()
                QMessageBox.information(self, "موفقیت", "اختصاص معلم با موفقیت حذف شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{str(e)}")