"""
دیالوگ اختصاص و ویرایش معلم به دانش‌آموز - نسخه با Tooltip
"""

import jdatetime
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from dal.academic_year_dal import AcademicYearDAL
from dal.staff_dal import StaffDAL
from dal.student_dal import StudentDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from models.teacher_assignment import TeacherAssignment
from utils.logger import get_logger
from utils.shamsi_date_input import ShamsiDateInput
from utils.tooltip_manager import TooltipManager

logger = get_logger(__name__)


class AssignTeacherDialog(QDialog):
    """دیالوگ اختصاص و ویرایش معلم به دانش‌آموز با Tooltip"""

    assignment_saved = Signal()

    def __init__(self, student_ids=None, teacher_id=None, year_id=None,
                 assignment_id=None, parent=None):
        super().__init__(parent)

        self.student_dal = StudentDAL()
        self.staff_dal = StaffDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.assignment_dal = TeacherAssignmentDAL()

        self.student_ids = student_ids or []
        self.assignment_id = assignment_id
        self.is_edit_mode = assignment_id is not None
        self.existing_assignment = None

        self.setWindowTitle("ویرایش اختصاص معلم" if self.is_edit_mode else "اختصاص معلم به دانش‌آموزان")
        self.setModal(True)
        self.resize(550, 400)

        self.setup_ui()
        self.load_teachers()
        self.load_academic_years()
        self.load_students()

        if self.is_edit_mode:
            self.load_assignment_data()
        else:
            if teacher_id:
                for i in range(self.teacher_combo.count()):
                    if self.teacher_combo.itemData(i) == teacher_id:
                        self.teacher_combo.setCurrentIndex(i)
                        break

            if year_id:
                for i in range(self.year_combo.count()):
                    if self.year_combo.itemData(i) == year_id:
                        self.year_combo.setCurrentIndex(i)
                        break

            today = jdatetime.date.today()
            self.date_input.set_date(f"{today.year}/{today.month:02d}/{today.day:02d}")

    def setup_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #08223A; }")

        container = QWidget()
        container.setStyleSheet("background-color: #08223A;")
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        info_group = QGroupBox("📋 اطلاعات اختصاص معلم")
        info_group.setStyleSheet("""
            QGroupBox {
    color: #111111;
                font-weight: bold;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
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
        form_layout = QFormLayout(info_group)
        form_layout.setSpacing(10)

        self.teacher_combo = QComboBox()
        self.teacher_combo.setPlaceholderText("انتخاب معلم...")
        TooltipManager.set_tooltip(self.teacher_combo, "معلم مورد نظر را از لیست انتخاب کنید.")
        form_layout.addRow("👨‍🏫 معلم:", self.teacher_combo)

        self.year_combo = QComboBox()
        self.year_combo.setPlaceholderText("انتخاب سال تحصیلی...")
        TooltipManager.set_tooltip(self.year_combo, "سال تحصیلی مورد نظر را انتخاب کنید.")
        form_layout.addRow("📅 سال تحصیلی:", self.year_combo)

        if self.is_edit_mode:
            self.student_combo = QComboBox()
            self.student_combo.setPlaceholderText("انتخاب دانش‌آموز...")
            TooltipManager.set_tooltip(self.student_combo, "دانش‌آموز مورد نظر را انتخاب کنید.")
            form_layout.addRow("👤 دانش‌آموز:", self.student_combo)

        self.grade_input = QComboBox()
        for grade in range(1, 7):
            grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}
            self.grade_input.addItem(f"پایه {grade_names[grade]}", grade)
        TooltipManager.set_tooltip(self.grade_input, "پایه تحصیلی دانش‌آموز را انتخاب کنید.")
        form_layout.addRow("📚 پایه:", self.grade_input)

        self.class_input = QComboBox()
        for cls in ["الف", "ب", "ج", "د", "ه", "و"]:
            self.class_input.addItem(cls)
        self.class_input.setEditable(True)
        TooltipManager.set_tooltip(self.class_input, "کلاس دانش‌آموز را وارد کنید.")
        form_layout.addRow("🏫 کلاس:", self.class_input)

        self.date_input = ShamsiDateInput()
        TooltipManager.set_tooltip(self.date_input, "تاریخ انتصاب معلم را به شمسی وارد کنید.")
        form_layout.addRow("📅 تاریخ انتصاب:", self.date_input)

        if not self.is_edit_mode:
            self.student_count_label = QLabel(f"تعداد دانش‌آموزان انتخاب‌شده: {len(self.student_ids)}")
            self.student_count_label.setStyleSheet("color: #D9C36A; font-size: 13px;")
            form_layout.addRow("📊 تعداد:", self.student_count_label)

        layout.addWidget(info_group)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("💾 ذخیره" if self.is_edit_mode else "✅ اختصاص معلم")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 12px 40px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                min-height: 40px;
            }
            QPushButton:hover { background-color: #66BB6A; }
        """)
        self.save_btn.clicked.connect(self.save_assignment)
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("❌ انصراف")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 12px 40px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                min-height: 40px;
            }
            QPushButton:hover { background-color: #D94B4B; }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)
        layout.addSpacing(10)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)
    
    def load_teachers(self):
        """بارگذاری معلمان در کامبوباکس"""
        try:
            all_staff = self.staff_dal.get_all()
            teachers = [s for s in all_staff if s.role == "teacher"]
            self.teacher_combo.clear()
            for teacher in teachers:
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
        except Exception as e:
            logger.error(f"خطا در بارگذاری سال‌های تحصیلی: {e}")
    
    def load_students(self):
        """بارگذاری دانش‌آموزان در کامبوباکس (حالت ویرایش)"""
        if self.is_edit_mode:
            try:
                students = self.student_dal.get_all()
                self.student_combo.clear()
                for student in students:
                    self.student_combo.addItem(student.full_name, student.id)
            except Exception as e:
                logger.error(f"خطا در بارگذاری دانش‌آموزان: {e}")
    
    def load_assignment_data(self):
        """بارگذاری اطلاعات انتساب برای ویرایش"""
        try:
            self.existing_assignment = self.assignment_dal.get_by_id(self.assignment_id)
            if not self.existing_assignment:
                QMessageBox.critical(self, "خطا", "انتساب مورد نظر یافت نشد.")
                self.reject()
                return
            
            assignment = self.existing_assignment
            
            # انتخاب معلم
            for i in range(self.teacher_combo.count()):
                if self.teacher_combo.itemData(i) == assignment.staff_id:
                    self.teacher_combo.setCurrentIndex(i)
                    break
            
            # انتخاب سال تحصیلی
            for i in range(self.year_combo.count()):
                if self.year_combo.itemData(i) == assignment.academic_year_id:
                    self.year_combo.setCurrentIndex(i)
                    break
            
            # انتخاب دانش‌آموز
            for i in range(self.student_combo.count()):
                if self.student_combo.itemData(i) == assignment.student_id:
                    self.student_combo.setCurrentIndex(i)
                    break
            
            # انتخاب پایه
            grade_index = self.grade_input.findData(assignment.grade)
            if grade_index >= 0:
                self.grade_input.setCurrentIndex(grade_index)
            
            # انتخاب کلاس
            class_index = self.class_input.findText(assignment.class_name or "")
            if class_index >= 0:
                self.class_input.setCurrentIndex(class_index)
            elif assignment.class_name:
                self.class_input.setEditText(assignment.class_name)
            
            # تنظیم تاریخ
            if assignment.assigned_date:
                self.date_input.set_date(assignment.assigned_date)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری اطلاعات:\n{e!s}")
    
    def save_assignment(self):
        """ذخیره انتساب معلم"""
        # اعتبارسنجی
        teacher_index = self.teacher_combo.currentIndex()
        if teacher_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک معلم را انتخاب کنید.")
            return
        
        year_index = self.year_combo.currentIndex()
        if year_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک سال تحصیلی را انتخاب کنید.")
            return
        
        if not self.date_input.is_valid():
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ را به صورت صحیح وارد کنید.")
            return
        
        teacher_id = self.teacher_combo.currentData()
        year_id = self.year_combo.currentData()
        grade = self.grade_input.currentData()
        class_name = self.class_input.currentText().strip()
        assigned_date = self.date_input.get_date_string()
        
        try:
            if self.is_edit_mode:
                # ویرایش انتساب موجود
                assignment = self.existing_assignment
                assignment.staff_id = teacher_id
                assignment.academic_year_id = year_id
                assignment.grade = grade
                assignment.class_name = class_name
                assignment.assigned_date = assigned_date
                assignment.is_active = 1
                
                self.assignment_dal.update(assignment)
                msg = "اطلاعات معلم با موفقیت ویرایش شد."
            else:
                # ایجاد انتساب جدید برای هر دانش‌آموز
                if not self.student_ids:
                    QMessageBox.warning(self, "خطا", "هیچ دانش‌آموزی انتخاب نشده است.")
                    return
                
                for student_id in self.student_ids:
                    # بررسی وجود انتساب تکراری
                    existing = self.assignment_dal.get_by_student(student_id, year_id)
                    already_has_teacher = any(a.staff_id == teacher_id for a in existing)
                    
                    if already_has_teacher:
                        # اگر این معلم قبلاً به این دانش‌آموز اختصاص دارد، رد شدن
                        continue
                    
                    assignment = TeacherAssignment()
                    assignment.student_id = student_id
                    assignment.staff_id = teacher_id
                    assignment.academic_year_id = year_id
                    assignment.grade = grade
                    assignment.class_name = class_name
                    assignment.is_active = 1
                    assignment.assigned_date = assigned_date
                    
                    self.assignment_dal.create(assignment)
                
                msg = "معلم با موفقیت به دانش‌آموزان اختصاص داده شد."
            
            QMessageBox.information(self, "موفقیت", msg)
            self.assignment_saved.emit()
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در ذخیره:\n{e!s}")