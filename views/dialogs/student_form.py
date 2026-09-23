"""
فرم ثبت و ویرایش دانش‌آموز - نسخه با پشتیبانی از سیستم راهنما
"""


import jdatetime
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config.settings import GRADES, LIVING_STATUSES
from dal.academic_year_dal import AcademicYearDAL
from dal.family_context_dal import FamilyContextDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.academic_year import AcademicYear
from models.family_context import FamilyContext
from models.student import Student
from utils.logger import get_logger
from utils.time_utils import utc_now
from utils.tooltip_manager import TooltipManager
from utils.ui_guards import single_submit

logger = get_logger(__name__)


class StudentForm(QDialog):
    """فرم ثبت/ویرایش دانش‌آموز با پشتیبانی از سیستم راهنما"""

    def __init__(self, student=None, parent=None):
        super().__init__(parent)

        self.student = student or Student()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.year_dal = AcademicYearDAL()
        self.family_dal = FamilyContextDAL()
        self.is_edit_mode = student is not None

        self.existing_profile = None
        if self.is_edit_mode and self.student.id:
            self.existing_profile = self.profile_dal.get_active_by_student(self.student.id)

        # در حالت ویرایش، اطلاعات خانوادگی از دیتابیس خوانده می‌شود
        # (رفع BUG-GUI-02: قبلاً از فیلدهای سایه‌ای مدل Student خوانده
        # می‌شد که هیچ‌وقت در دیتابیس ذخیره نمی‌شدند).
        self.existing_family = None
        if self.existing_profile:
            try:
                self.existing_family = self.family_dal.get_by_student_profile(
                    self.existing_profile.id)
            except Exception as e:
                logger.error(f"خطا در خواندن زمینهٔ خانوادگی دانش‌آموز: {e}")
                self.existing_family = None

        self.setWindowTitle("ویرایش دانش‌آموز" if self.is_edit_mode else "ثبت دانش‌آموز جدید")
        self.setModal(True)
        self.setFixedSize(600, 700)

        self.setup_ui()

        if self.is_edit_mode:
            self.load_student_data()

    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        form_layout = QFormLayout()
        container.setLayout(form_layout)

        # ===== فیلدهای فرم =====

        # نام
        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("نام دانش‌آموز")
        form_layout.addRow("نام:", self.first_name_input)

        # نام خانوادگی
        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("نام خانوادگی")
        form_layout.addRow("نام خانوادگی:", self.last_name_input)

        # نام پدر
        self.father_name_input = QLineEdit()
        self.father_name_input.setPlaceholderText("نام پدر")
        form_layout.addRow("نام پدر:", self.father_name_input)

        # کد ملی
        self.national_code_input = QLineEdit()
        self.national_code_input.setPlaceholderText("کد ملی ۱۰ رقمی")
        self.national_code_input.setMaxLength(10)
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.national_code_input, 'national_code')
        form_layout.addRow("کد ملی:", self.national_code_input)

        # تاریخ تولد
        self.birth_date_input = QLineEdit()
        self.birth_date_input.setPlaceholderText("مثال: 1390/05/15")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.birth_date_input, 'birth_date')
        form_layout.addRow("تاریخ تولد:", self.birth_date_input)

        # ===== اطلاعات سالانه =====
        form_layout.addRow(QLabel("--- اطلاعات سال تحصیلی ---"))

        # پایه
        self.grade_combo = QComboBox()
        grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}
        for grade in GRADES:
            self.grade_combo.addItem(f"پایه {grade_names[grade]}", grade)
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.grade_combo, 'grade')
        form_layout.addRow("پایه:", self.grade_combo)

        # کلاس
        self.class_input = QLineEdit()
        self.class_input.setPlaceholderText("مثال: الف، ب، ...")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.class_input, 'class')
        form_layout.addRow("کلاس:", self.class_input)

        # سال تحصیلی
        self.academic_year_input = QLineEdit()
        self.academic_year_input.setReadOnly(True)
        self.academic_year_input.setStyleSheet("background-color: #f0f0f0;")

        self._ensure_active_year()
        form_layout.addRow("سال تحصیلی:", self.academic_year_input)

        # نام ولی
        self.guardian_name_input = QLineEdit()
        self.guardian_name_input.setPlaceholderText("نام پدر یا ولی")
        form_layout.addRow("نام ولی:", self.guardian_name_input)

        # شماره تماس ولی
        self.guardian_phone_input = QLineEdit()
        self.guardian_phone_input.setPlaceholderText("شماره تماس")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.guardian_phone_input, 'phone')
        form_layout.addRow("شماره تماس ولی:", self.guardian_phone_input)

        # تعداد برادران
        self.brothers_spin = QSpinBox()
        self.brothers_spin.setRange(0, 20)
        self.brothers_spin.setValue(0)
        form_layout.addRow("تعداد برادران:", self.brothers_spin)

        # تعداد خواهران
        self.sisters_spin = QSpinBox()
        self.sisters_spin.setRange(0, 20)
        self.sisters_spin.setValue(0)
        form_layout.addRow("تعداد خواهران:", self.sisters_spin)

        # وضعیت زندگی با والدین
        self.living_status_combo = QComboBox()
        for status in LIVING_STATUSES:
            self.living_status_combo.addItem(status)
        form_layout.addRow("وضعیت زندگی:", self.living_status_combo)

        # آدرس
        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(80)
        form_layout.addRow("آدرس:", self.address_input)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # ===== دکمه‌ها =====
        button_layout = QHBoxLayout()

        self.save_btn = QPushButton("💾 ذخیره")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.save_btn.clicked.connect(self.save_student)

        self.cancel_btn = QPushButton("❌ انصراف")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #D94B4B; }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def _ensure_active_year(self):
        """اطمینان از وجود سال تحصیلی فعال"""
        active_year = self.year_dal.get_active()
        if active_year and active_year.id:
            self.academic_year_input.setText(active_year.title)
            self._active_year = active_year
            return

        try:
            now = jdatetime.datetime.now()
            current_year = now.year
        except Exception:
            current_year = utc_now().year - 621

        new_year = AcademicYear()
        new_year.title = f"{current_year}-{current_year+1}"
        new_year.start_date = f"{current_year}/07/01"
        new_year.end_date = f"{current_year+1}/06/30"
        new_year.is_active = 1
        new_year.is_archived = 0

        created_year = self.year_dal.create(new_year)
        if not created_year or not created_year.id:
            raise Exception("ایجاد سال تحصیلی فعال ناموفق بود")

        self.academic_year_input.setText(created_year.title)
        self._active_year = created_year
        logger.debug(f"✅ سال تحصیلی جدید در فرم ایجاد شد: {created_year.title} (ID={created_year.id})")
    
    def load_student_data(self):
        """بارگذاری اطلاعات دانش‌آموز برای ویرایش"""
        self.first_name_input.setText(self.student.first_name or "")
        self.last_name_input.setText(self.student.last_name or "")
        self.father_name_input.setText(self.student.father_name or "")
        self.national_code_input.setText(self.student.national_code or "")
        self.birth_date_input.setText(self.student.birth_date or "")
        
        # بارگذاری اطلاعات پرونده (اگر وجود داشته باشد)
        if self.existing_profile:
            index = self.grade_combo.findData(self.existing_profile.grade)
            if index >= 0:
                self.grade_combo.setCurrentIndex(index)
            self.class_input.setText(self.existing_profile.class_name or "")
        else:
            # اگر پرونده فعال نبود، یک پایه پیش‌فرض انتخاب کن
            self.grade_combo.setCurrentIndex(0)
        
        self.guardian_name_input.setText(self.student.guardian_name or "")
        self.guardian_phone_input.setText(self.student.guardian_phone or "")

        # اطلاعات خانوادگی از family_contexts خوانده می‌شود؛ اگر پروندهٔ فعالی
        # نباشد، یک ردیف FamilyContext خالی برای پیش‌فرض نمایش استفاده می‌شود
        # (بدون نوشتن در دیتابیس در مرحلهٔ بارگذاری).
        family = self.existing_family or FamilyContext()
        self.brothers_spin.setValue(int(family.siblings_brothers or 0))
        self.sisters_spin.setValue(int(family.siblings_sisters or 0))

        living_status = family.living_status
        if living_status:
            index = self.living_status_combo.findText(living_status)
            if index >= 0:
                self.living_status_combo.setCurrentIndex(index)
            else:
                # مقدار ثبت‌شده در لیست استاندارد نیست (دادهٔ قدیمی/دستی)؛
                # نباید بی‌صدا به گزینهٔ اول تغییر کند.
                self.living_status_combo.addItem(living_status)
                self.living_status_combo.setCurrentIndex(
                    self.living_status_combo.count() - 1)

        self.address_input.setText(self.student.address or "")
    
    @single_submit()
    def save_student(self):
        """ذخیره دانش‌آموز در دیتابیس"""
        self.student.first_name = self.first_name_input.text().strip()
        self.student.last_name = self.last_name_input.text().strip()
        self.student.father_name = self.father_name_input.text().strip()
        self.student.national_code = self.national_code_input.text().strip()
        self.student.birth_date = self.birth_date_input.text().strip()
        self.student.guardian_name = self.guardian_name_input.text().strip()
        self.student.guardian_phone = self.guardian_phone_input.text().strip()
        self.student.address = self.address_input.toPlainText().strip()
        self.student.is_active = 1

        # اطلاعات خانوادگی دیگر روی مدل Student (که ستون دیتابیس ندارد)
        # گذاشته نمی‌شود؛ مقادیر فرم مستقیم به family_contexts می‌روند.
        family_inputs = {
            'living_status': self.living_status_combo.currentText(),
            'siblings_brothers': self.brothers_spin.value(),
            'siblings_sisters': self.sisters_spin.value(),
        }

        errors = self.student.validate()
        if errors:
            QMessageBox.warning(self, "خطا در اعتبارسنجی", "\n".join(errors))
            return

        try:
            self._ensure_active_year()
            active_year = getattr(self, "_active_year", None)

            logger.debug(f"سال فعال هنگام ذخیرهٔ دانش‌آموز: {active_year.id if active_year else None}")

            if not active_year or not active_year.id:
                QMessageBox.critical(self, "خطا", "سال تحصیلی فعالی وجود ندارد.")
                return

            # 1) ذخیره دانش‌آموز
            if self.is_edit_mode:
                self.student_dal.update(self.student)
                message = "دانش‌آموز با موفقیت ویرایش شد"
            else:
                saved_student = self.student_dal.create(self.student)
                if not saved_student or not saved_student.id:
                    raise Exception("شناسه دانش‌آموز پس از ذخیره برنگشت")
                self.student = saved_student
                message = "دانش‌آموز با موفقیت ثبت شد"

            if not self.student.id:
                raise Exception("student.id نامعتبر است")

            # 2) ذخیره پرونده سالانه
            grade = self.grade_combo.currentData()
            class_name = self.class_input.text().strip()

            existing_profile = self.profile_dal.get_by_student_and_year(
                self.student.id,
                active_year.id
            )

            if existing_profile:
                existing_profile.grade = grade
                existing_profile.class_name = class_name
                existing_profile.status = "active"
                self.profile_dal.update(existing_profile)
                profile_id = existing_profile.id
            else:
                from models.student_academic_profile import StudentAcademicProfile

                new_profile = StudentAcademicProfile()
                new_profile.student_id = self.student.id
                new_profile.academic_year_id = active_year.id
                new_profile.grade = grade
                new_profile.class_name = class_name
                new_profile.status = "active"

                logger.debug(f"DEBUG profile -> student_id={new_profile.student_id}, academic_year_id={new_profile.academic_year_id}")

                saved_profile = self.profile_dal.create(new_profile)
                profile_id = getattr(saved_profile, 'id', None) or new_profile.id

            if not profile_id:
                raise Exception("شناسهٔ پروندهٔ سالانه پس از ذخیره برنگشت")

            # 3) ذخیرهٔ اطلاعات خانوادگی در جای قانونی‌اش (family_contexts)
            #    upsert تک‌ردیفی + بررسی rowcount + بازخوانی از دیتابیس.
            saved_family = self.family_dal.upsert_family_facts(
                profile_id,
                living_status=family_inputs['living_status'],
                siblings_brothers=family_inputs['siblings_brothers'],
                siblings_sisters=family_inputs['siblings_sisters'],
            )
            self.existing_family = saved_family

            QMessageBox.information(self, "موفقیت", message)
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در ذخیره اطلاعات:\n{e!s}")