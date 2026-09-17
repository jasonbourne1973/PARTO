"""
فرم ثبت و ویرایش فعالیت فوق‌برنامه - نسخه با پشتیبانی از سیستم راهنما
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QTextEdit, QSpinBox, QMessageBox, QWidget,
    QScrollArea, QGroupBox, QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from services.extracurricular_service import ExtracurricularService
from dal.student_dal import StudentDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.staff_dal import StaffDAL
from models.extracurricular_activity import ExtracurricularActivity
from utils.shamsi_date_input import ShamsiDateInput
from utils.error_handler import ValidationError
from utils.logger import get_logger
from utils.tooltip_manager import TooltipManager
from views.widgets.help_widget import HelpWidget


class ActivityForm(QDialog):
    """فرم ثبت و ویرایش فعالیت فوق‌برنامه با پشتیبانی از سیستم راهنما"""

    activity_saved = Signal()

    def __init__(self, activity_id=None, profile_id=None, parent=None):
        super().__init__(parent)

        self.extracurricular_service = ExtracurricularService()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.logger = get_logger(self.__class__.__name__)

        self.activity_id = activity_id
        self.profile_id = profile_id
        self.existing_activity = None
        self.is_edit_mode = activity_id is not None

        self.setWindowTitle("ویرایش فعالیت" if self.is_edit_mode else "ثبت فعالیت جدید")
        self.setModal(True)
        self.resize(650, 700)

        self.setup_ui()
        self.load_students()
        self.load_teachers()

        if self.is_edit_mode:
            self.load_activity_data()
        elif self.profile_id:
            self.select_profile(profile_id)

    def setup_ui(self):
        """راه‌اندازی رابط کاربری با Tooltip و راهنما"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #0B2E4F; }")

        container = QWidget()
        container.setMinimumWidth(0)
        container.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred
        )
        container.setStyleSheet("background-color: #0B2E4F;")
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # ===== ویجت راهنمای سریع =====
        self.help_widget = HelpWidget(
            "راهنمای ثبت فعالیت",
            "فعالیت‌های فوق‌برنامه شامل فعالیت‌های فرهنگی، هنری، ورزشی و مذهبی است.",
            self
        )
        layout.addWidget(self.help_widget)

        # ===== گروه اطلاعات پایه =====
        info_group = QGroupBox("📋 اطلاعات فعالیت")
        info_group.setStyleSheet("""
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
        form_layout = QFormLayout(info_group)
        form_layout.setSpacing(8)

        # دانش‌آموز
        self.student_combo = QComboBox()
        self.student_combo.setEditable(True)
        self.student_combo.setPlaceholderText("جستجو و انتخاب دانش‌آموز...")
        self.student_combo.setMinimumHeight(32)
        TooltipManager.set_field_tooltip(self.student_combo, 'student')
        form_layout.addRow("👤 دانش‌آموز:", self.student_combo)

        # معلم مسئول
        self.teacher_combo = QComboBox()
        self.teacher_combo.addItem("بدون معلم", None)
        self.teacher_combo.setPlaceholderText("انتخاب معلم مسئول...")
        self.teacher_combo.setMinimumHeight(32)
        TooltipManager.set_field_tooltip(self.teacher_combo, 'observer')
        form_layout.addRow("👨‍🏫 معلم مسئول:", self.teacher_combo)

        # عنوان
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("عنوان فعالیت...")
        self.title_input.setMinimumHeight(32)
        form_layout.addRow("📝 عنوان:", self.title_input)

        # نوع فعالیت
        self.type_combo = QComboBox()
        for value, display in ExtracurricularActivity.TYPE_CHOICES:
            self.type_combo.addItem(display, value)
        self.type_combo.setMinimumHeight(32)
        form_layout.addRow("🏷️ نوع فعالیت:", self.type_combo)

        # تاریخ
        date_layout = QVBoxLayout()

        start_widget = QWidget()
        start_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        start_layout = QVBoxLayout(start_widget)
        start_layout.setContentsMargins(0, 0, 0, 0)
        start_layout.addWidget(QLabel("تاریخ شروع:"))
        self.start_date_input = ShamsiDateInput()
        TooltipManager.set_field_tooltip(self.start_date_input, 'date')
        start_layout.addWidget(self.start_date_input)
        date_layout.addWidget(start_widget)

        end_widget = QWidget()
        end_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        end_layout = QVBoxLayout(end_widget)
        end_layout.setContentsMargins(0, 0, 0, 0)
        end_layout.addWidget(QLabel("تاریخ پایان:"))
        self.end_date_input = ShamsiDateInput()
        end_layout.addWidget(self.end_date_input)
        date_layout.addWidget(end_widget)

        duration_widget = QWidget()
        duration_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        duration_layout = QVBoxLayout(duration_widget)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.addWidget(QLabel("مدت (ساعت):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 100)
        self.duration_spin.setValue(0)
        self.duration_spin.setMinimumHeight(32)
        duration_layout.addWidget(self.duration_spin)
        date_layout.addWidget(duration_widget)

        date_layout.addStretch()
        form_layout.addRow("📅 تاریخ:", date_layout)

        # مکان
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("مکان برگزاری...")
        self.location_input.setMinimumHeight(32)
        form_layout.addRow("📍 مکان:", self.location_input)

        layout.addWidget(info_group)

        # ===== گروه مشارکت =====
        participation_group = QGroupBox("🎯 مشارکت")
        participation_group.setStyleSheet("""
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
        part_layout = QFormLayout(participation_group)
        part_layout.setSpacing(8)

        # سطح مشارکت
        self.level_combo = QComboBox()
        for value, display in ExtracurricularActivity.LEVEL_CHOICES:
            self.level_combo.addItem(display, value)
        self.level_combo.setMinimumHeight(32)
        form_layout.addRow("📊 سطح مشارکت:", self.level_combo)

        # نقش
        self.role_input = QLineEdit()
        self.role_input.setPlaceholderText("نقش دانش‌آموز در فعالیت...")
        self.role_input.setMinimumHeight(32)
        form_layout.addRow("🎭 نقش:", self.role_input)

        # نام تیم
        self.team_input = QLineEdit()
        self.team_input.setPlaceholderText("نام تیم/گروه...")
        self.team_input.setMinimumHeight(32)
        form_layout.addRow("🏆 تیم/گروه:", self.team_input)

        layout.addWidget(participation_group)

        # ===== گروه توضیحات و نتیجه =====
        desc_group = QGroupBox("📄 توضیحات و نتیجه")
        desc_group.setStyleSheet("""
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
        desc_layout = QFormLayout(desc_group)
        desc_layout.setSpacing(8)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("توضیحات کامل فعالیت...")
        self.description_input.setMaximumHeight(80)
        self.description_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        TooltipManager.set_field_tooltip(self.description_input, 'description')
        desc_layout.addRow("📝 توضیحات:", self.description_input)

        self.result_input = QTextEdit()
        self.result_input.setPlaceholderText("نتیجه فعالیت...")
        self.result_input.setMaximumHeight(60)
        self.result_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        TooltipManager.set_field_tooltip(self.result_input, 'result')
        desc_layout.addRow("📊 نتیجه:", self.result_input)

        self.achievements_input = QTextEdit()
        self.achievements_input.setPlaceholderText("دستاوردها (هر مورد در یک خط)...")
        self.achievements_input.setMaximumHeight(60)
        self.achievements_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        desc_layout.addRow("🏅 دستاوردها:", self.achievements_input)

        self.feedback_input = QTextEdit()
        self.feedback_input.setPlaceholderText("بازخورد...")
        self.feedback_input.setMaximumHeight(60)
        self.feedback_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        desc_layout.addRow("💬 بازخورد:", self.feedback_input)

        layout.addWidget(desc_group)

        # ===== گروه وضعیت =====
        status_group = QGroupBox("📌 وضعیت")
        status_group.setStyleSheet("""
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
        status_layout = QFormLayout(status_group)
        status_layout.setSpacing(8)

        self.status_combo = QComboBox()
        for value, display in ExtracurricularActivity.STATUS_CHOICES:
            self.status_combo.addItem(display, value)
        self.status_combo.setMinimumHeight(32)
        status_layout.addRow("وضعیت:", self.status_combo)

        layout.addWidget(status_group)

        # ===== دکمه‌ها =====
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("💾 ذخیره فعالیت")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 10px 30px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.save_btn.clicked.connect(self.save_activity)
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("❌ انصراف")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #D94B4B; }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def load_students(self):
        try:
            students = self.student_dal.get_all()
            self.student_combo.clear()
            for student in students:
                self.student_combo.addItem(student.full_name, student.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری دانش‌آموزان: {e}")

    def load_teachers(self):
        try:
            staff_list = self.staff_dal.get_all()
            teachers = [s for s in staff_list if s.role == "teacher"]
            self.teacher_combo.clear()
            self.teacher_combo.addItem("بدون معلم", None)
            for teacher in teachers:
                self.teacher_combo.addItem(f"{teacher.full_name}", teacher.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری معلمان: {e}")
    
    def select_profile(self, profile_id):
        """انتخاب دانش‌آموز بر اساس پرونده"""
        try:
            profile = self.profile_dal.get_by_id(profile_id)
            if profile:
                for i in range(self.student_combo.count()):
                    if self.student_combo.itemData(i) == profile.student_id:
                        self.student_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            self.logger.error(f"خطا در انتخاب دانش‌آموز: {e}")
    
    def load_activity_data(self):
        """بارگذاری اطلاعات فعالیت برای ویرایش"""
        try:
            self.existing_activity = self.extracurricular_service.get_activity(self.activity_id)
            if not self.existing_activity:
                QMessageBox.critical(self, "خطا", "فعالیت مورد نظر یافت نشد")
                self.reject()
                return
            
            activity = self.existing_activity
            
            # دانش‌آموز
            profile = self.profile_dal.get_by_id(activity.student_profile_id)
            if profile:
                for i in range(self.student_combo.count()):
                    if self.student_combo.itemData(i) == profile.student_id:
                        self.student_combo.setCurrentIndex(i)
                        break
            
            # معلم
            if activity.teacher_id:
                for i in range(self.teacher_combo.count()):
                    if self.teacher_combo.itemData(i) == activity.teacher_id:
                        self.teacher_combo.setCurrentIndex(i)
                        break
            
            self.title_input.setText(activity.title or "")
            
            type_index = self.type_combo.findData(activity.type)
            if type_index >= 0:
                self.type_combo.setCurrentIndex(type_index)
            
            self.start_date_input.set_date(activity.start_date or "")
            self.end_date_input.set_date(activity.end_date or "")
            self.duration_spin.setValue(activity.duration_hours or 0)
            self.location_input.setText(activity.location or "")
            
            level_index = self.level_combo.findData(activity.participation_level)
            if level_index >= 0:
                self.level_combo.setCurrentIndex(level_index)
            
            self.role_input.setText(activity.role or "")
            self.team_input.setText(activity.team_name or "")
            
            self.description_input.setText(activity.description or "")
            self.result_input.setText(activity.result or "")
            
            if activity.achievements:
                self.achievements_input.setText("\n".join(activity.achievements))
            
            self.feedback_input.setText(activity.feedback or "")
            
            status_index = self.status_combo.findData(activity.status)
            if status_index >= 0:
                self.status_combo.setCurrentIndex(status_index)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری اطلاعات:\n{str(e)}")
    
    def save_activity(self):
        """ذخیره فعالیت"""
        # اعتبارسنجی
        student_index = self.student_combo.currentIndex()
        if student_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک دانش‌آموز انتخاب کنید")
            return
        
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "خطا", "لطفاً عنوان فعالیت را وارد کنید")
            return
        
        if not self.start_date_input.is_valid():
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ شروع را به صورت صحیح وارد کنید")
            return
        
        # دریافت پرونده دانش‌آموز
        student_id = self.student_combo.itemData(student_index)
        profile = self.profile_dal.get_active_by_student(student_id)
        if not profile:
            QMessageBox.warning(self, "خطا", "دانش‌آموز پرونده فعالی ندارد")
            return
        
        # ساخت داده‌ها
        achievements_text = self.achievements_input.toPlainText().strip()
        achievements = [line.strip() for line in achievements_text.split('\n') if line.strip()] if achievements_text else None
        
        data = {
            'student_profile_id': profile.id,
            'teacher_id': self.teacher_combo.currentData(),
            'title': self.title_input.text().strip(),
            'type': self.type_combo.currentData(),
            'description': self.description_input.toPlainText().strip(),
            'start_date': self.start_date_input.get_date_string(),
            'end_date': self.end_date_input.get_date_string(),
            'duration_hours': self.duration_spin.value(),
            'location': self.location_input.text().strip(),
            'participation_level': self.level_combo.currentData(),
            'role': self.role_input.text().strip(),
            'team_name': self.team_input.text().strip(),
            'result': self.result_input.toPlainText().strip(),
            'achievements': achievements,
            'feedback': self.feedback_input.toPlainText().strip(),
            'status': self.status_combo.currentData()
        }
        
        try:
            if self.is_edit_mode:
                self.extracurricular_service.update_activity(self.activity_id, data)
                msg = "✅ فعالیت با موفقیت ویرایش شد"
            else:
                self.extracurricular_service.create_activity(data)
                msg = "✅ فعالیت با موفقیت ثبت شد"
            
            QMessageBox.information(self, "موفقیت", msg)
            self.activity_saved.emit()
            self.accept()
            
        except ValidationError as e:
            QMessageBox.warning(self, "خطا در اعتبارسنجی", str(e))
        except Exception as e:
            self.logger.error(f"خطا در ذخیره فعالیت: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در ذخیره:\n{str(e)}")