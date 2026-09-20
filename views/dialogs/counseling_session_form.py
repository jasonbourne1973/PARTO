"""
فرم ثبت و ویرایش جلسه مشاوره - نسخه با پشتیبانی از سیستم راهنما
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
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

from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.counseling_session import CounselingSession
from services.counseling_service import CounselingService
from utils.error_handler import ValidationError
from utils.logger import get_logger
from utils.shamsi_date_input import ShamsiDateInput
from utils.tooltip_manager import TooltipManager
from views.widgets.help_widget import HelpWidget


class CounselingSessionForm(QDialog):
    """فرم ثبت و ویرایش جلسه مشاوره با پشتیبانی از سیستم راهنما"""

    session_saved = Signal()

    def __init__(self, session_id=None, profile_id=None, parent=None):
        super().__init__(parent)

        self.counseling_service = CounselingService()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.logger = get_logger(self.__class__.__name__)

        self.session_id = session_id
        self.profile_id = profile_id
        self.existing_session = None
        self.is_edit_mode = session_id is not None

        self.setWindowTitle("ویرایش جلسه مشاوره" if self.is_edit_mode else "ثبت جلسه مشاوره جدید")
        self.setModal(True)
        self.resize(700, 750)

        self.setup_ui()
        self.load_students()
        self.load_counselors()
        self.load_staff()

        if self.is_edit_mode:
            self.load_session_data()
        elif self.profile_id:
            self.select_profile(profile_id)

    def setup_ui(self):
        """راه‌اندازی رابط کاربری با Tooltip و راهنما"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #0B2E4F; }")

        container = QWidget()
        container.setStyleSheet("background-color: #0B2E4F;")
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # ===== ویجت راهنمای سریع =====
        self.help_widget = HelpWidget(
            "راهنمای ثبت جلسه مشاوره",
            "جلسات مشاوره برای بررسی و حمایت از وضعیت روانی و اجتماعی دانش‌آموزان برگزار می‌شود.",
            self
        )
        layout.addWidget(self.help_widget)

        # ===== گروه اطلاعات پایه =====
        info_group = QGroupBox("📋 اطلاعات پایه")
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

        # مشاور
        self.counselor_combo = QComboBox()
        self.counselor_combo.setPlaceholderText("انتخاب مشاور...")
        self.counselor_combo.setMinimumHeight(32)
        form_layout.addRow("🧑‍⚕️ مشاور:", self.counselor_combo)

        # معرف
        self.referred_by_combo = QComboBox()
        self.referred_by_combo.addItem("بدون معرف", None)
        self.referred_by_combo.setMinimumHeight(32)
        form_layout.addRow("📋 معرف:", self.referred_by_combo)

        # تاریخ و زمان
        date_time_layout = QHBoxLayout()

        date_widget = QWidget()
        date_layout = QVBoxLayout(date_widget)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.addWidget(QLabel("تاریخ جلسه:"))
        self.date_input = ShamsiDateInput()
        TooltipManager.set_field_tooltip(self.date_input, 'date')
        date_layout.addWidget(self.date_input)
        date_time_layout.addWidget(date_widget)

        time_widget = QWidget()
        time_layout = QVBoxLayout(time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.addWidget(QLabel("زمان:"))
        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("مثال: 14:30")
        self.time_input.setMinimumHeight(32)
        time_layout.addWidget(self.time_input)
        date_time_layout.addWidget(time_widget)

        duration_widget = QWidget()
        duration_layout = QVBoxLayout(duration_widget)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.addWidget(QLabel("مدت (دقیقه):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(10, 120)
        self.duration_spin.setValue(30)
        self.duration_spin.setMinimumHeight(32)
        duration_layout.addWidget(self.duration_spin)
        date_time_layout.addWidget(duration_widget)

        date_time_layout.addStretch()
        form_layout.addRow("📅 تاریخ و زمان:", date_time_layout)

        # نوع و روش
        type_method_layout = QHBoxLayout()

        type_widget = QWidget()
        type_layout = QVBoxLayout(type_widget)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.addWidget(QLabel("نوع جلسه:"))
        self.type_combo = QComboBox()
        for value, display in CounselingSession.TYPE_CHOICES:
            self.type_combo.addItem(display, value)
        self.type_combo.setMinimumHeight(32)
        type_layout.addWidget(self.type_combo)
        type_method_layout.addWidget(type_widget)

        method_widget = QWidget()
        method_layout = QVBoxLayout(method_widget)
        method_layout.setContentsMargins(0, 0, 0, 0)
        method_layout.addWidget(QLabel("روش:"))
        self.method_combo = QComboBox()
        for value, display in CounselingSession.METHOD_CHOICES:
            self.method_combo.addItem(display, value)
        self.method_combo.setMinimumHeight(32)
        method_layout.addWidget(self.method_combo)
        type_method_layout.addWidget(method_widget)

        location_widget = QWidget()
        location_layout = QVBoxLayout(location_widget)
        location_layout.setContentsMargins(0, 0, 0, 0)
        location_layout.addWidget(QLabel("مکان:"))
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("مکان جلسه...")
        self.location_input.setMinimumHeight(32)
        location_layout.addWidget(self.location_input)
        type_method_layout.addWidget(location_widget)

        type_method_layout.addStretch()
        form_layout.addRow("📍 نوع و مکان:", type_method_layout)

        layout.addWidget(info_group)

        # ===== گروه موضوع و اهداف =====
        topic_group = QGroupBox("🎯 موضوع و اهداف")
        topic_group.setStyleSheet("""
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
        topic_layout = QFormLayout(topic_group)
        topic_layout.setSpacing(8)

        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("موضوع اصلی جلسه...")
        self.topic_input.setMinimumHeight(32)
        topic_layout.addRow("📝 موضوع:", self.topic_input)

        self.goals_input = QTextEdit()
        self.goals_input.setPlaceholderText("اهداف جلسه (هر هدف در یک خط)...")
        self.goals_input.setMaximumHeight(60)
        self.goals_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        topic_layout.addRow("🎯 اهداف:", self.goals_input)

        layout.addWidget(topic_group)

        # ===== گروه محتوا =====
        content_group = QGroupBox("📄 محتوای جلسه")
        content_group.setStyleSheet("""
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
        content_layout = QFormLayout(content_group)
        content_layout.setSpacing(8)

        self.summary_input = QTextEdit()
        self.summary_input.setPlaceholderText("خلاصه جلسه...")
        self.summary_input.setMaximumHeight(80)
        self.summary_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        content_layout.addRow("📊 خلاصه:", self.summary_input)

        self.details_input = QTextEdit()
        self.details_input.setPlaceholderText("جزئیات کامل جلسه...")
        self.details_input.setMaximumHeight(120)
        self.details_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        content_layout.addRow("📝 جزئیات:", self.details_input)

        layout.addWidget(content_group)

        # ===== گروه مداخلات و توصیه‌ها =====
        rec_group = QGroupBox("💡 مداخلات و توصیه‌ها")
        rec_group.setStyleSheet("""
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
        rec_layout = QFormLayout(rec_group)
        rec_layout.setSpacing(8)

        self.interventions_input = QTextEdit()
        self.interventions_input.setPlaceholderText("مداخلات مطرح‌شده (هر مورد در یک خط)...")
        self.interventions_input.setMaximumHeight(60)
        self.interventions_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        rec_layout.addRow("🛠️ مداخلات:", self.interventions_input)

        self.recommendations_input = QTextEdit()
        self.recommendations_input.setPlaceholderText("توصیه‌ها (هر مورد در یک خط)...")
        self.recommendations_input.setMaximumHeight(60)
        self.recommendations_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        rec_layout.addRow("📋 توصیه‌ها:", self.recommendations_input)

        self.homework_input = QTextEdit()
        self.homework_input.setPlaceholderText("تکالیف (هر مورد در یک خط)...")
        self.homework_input.setMaximumHeight(60)
        self.homework_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        rec_layout.addRow("📚 تکالیف:", self.homework_input)

        layout.addWidget(rec_group)

        # ===== گروه نتیجه و پیگیری =====
        follow_group = QGroupBox("🔔 نتیجه و پیگیری")
        follow_group.setStyleSheet("""
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
        follow_layout = QFormLayout(follow_group)
        follow_layout.setSpacing(8)

        self.outcome_input = QTextEdit()
        self.outcome_input.setPlaceholderText("نتیجه جلسه...")
        self.outcome_input.setMaximumHeight(60)
        self.outcome_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        follow_layout.addRow("📊 نتیجه:", self.outcome_input)

        self.follow_up_check = QCheckBox("نیاز به پیگیری دارد")
        self.follow_up_check.setStyleSheet("font-weight: bold; color: #F4C542;")
        follow_layout.addRow("", self.follow_up_check)

        next_date_layout = QHBoxLayout()
        next_date_layout.addWidget(QLabel("تاریخ جلسه بعدی:"))
        self.next_date_input = ShamsiDateInput()
        next_date_layout.addWidget(self.next_date_input)
        follow_layout.addRow("📅 جلسه بعدی:", next_date_layout)

        self.next_notes_input = QTextEdit()
        self.next_notes_input.setPlaceholderText("یادداشت جلسه بعدی...")
        self.next_notes_input.setMaximumHeight(40)
        self.next_notes_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        follow_layout.addRow("📝 یادداشت:", self.next_notes_input)

        self.status_combo = QComboBox()
        for value, display in CounselingSession.STATUS_CHOICES:
            self.status_combo.addItem(display, value)
        self.status_combo.setMinimumHeight(32)
        follow_layout.addRow("📌 وضعیت:", self.status_combo)

        layout.addWidget(follow_group)

        # ===== دکمه‌ها =====
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("💾 ذخیره جلسه")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 10px 30px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.save_btn.clicked.connect(self.save_session)
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

        self.follow_up_check.toggled.connect(self.on_follow_up_toggled)

    def on_follow_up_toggled(self, checked):
        self.next_date_input.setEnabled(checked)
        self.next_notes_input.setEnabled(checked)

    
    def load_students(self):
        """بارگذاری دانش‌آموزان"""
        try:
            students = self.student_dal.get_all()
            self.student_combo.clear()
            for student in students:
                self.student_combo.addItem(student.full_name, student.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری دانش‌آموزان: {e}")
    
    def load_counselors(self):
        """بارگذاری مشاوران"""
        try:
            staff_list = self.staff_dal.get_all()
            counselors = [s for s in staff_list if s.role == "counselor"]
            self.counselor_combo.clear()
            for counselor in counselors:
                self.counselor_combo.addItem(f"{counselor.full_name}", counselor.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری مشاوران: {e}")
    
    def load_staff(self):
        """بارگذاری اعضای کادر برای معرف"""
        try:
            staff_list = self.staff_dal.get_all()
            self.referred_by_combo.clear()
            self.referred_by_combo.addItem("بدون معرف", None)
            for staff in staff_list:
                self.referred_by_combo.addItem(f"{staff.full_name}", staff.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری اعضای کادر: {e}")
    
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
    
    def load_session_data(self):
        """بارگذاری اطلاعات جلسه برای ویرایش"""
        try:
            self.existing_session = self.counseling_service.get_session(self.session_id)
            if not self.existing_session:
                QMessageBox.critical(self, "خطا", "جلسه مورد نظر یافت نشد")
                self.reject()
                return
            
            session = self.existing_session
            
            # دانش‌آموز
            profile = self.profile_dal.get_by_id(session.student_profile_id)
            if profile:
                for i in range(self.student_combo.count()):
                    if self.student_combo.itemData(i) == profile.student_id:
                        self.student_combo.setCurrentIndex(i)
                        break
            
            # مشاور
            for i in range(self.counselor_combo.count()):
                if self.counselor_combo.itemData(i) == session.counselor_id:
                    self.counselor_combo.setCurrentIndex(i)
                    break
            
            # معرف
            if session.referred_by:
                for i in range(self.referred_by_combo.count()):
                    if self.referred_by_combo.itemData(i) == session.referred_by:
                        self.referred_by_combo.setCurrentIndex(i)
                        break
            
            # تاریخ و زمان
            self.date_input.set_date(session.session_date or "")
            self.time_input.setText(session.session_time or "")
            self.duration_spin.setValue(session.duration_minutes or 30)
            
            # نوع و روش
            type_index = self.type_combo.findData(session.type)
            if type_index >= 0:
                self.type_combo.setCurrentIndex(type_index)
            
            method_index = self.method_combo.findData(session.method)
            if method_index >= 0:
                self.method_combo.setCurrentIndex(method_index)
            
            self.location_input.setText(session.location or "")
            
            # موضوع و اهداف
            self.topic_input.setText(session.topic or "")
            if session.goals:
                self.goals_input.setText("\n".join(session.goals))
            
            # محتوا
            self.summary_input.setText(session.summary or "")
            self.details_input.setText(session.details or "")
            
            # مداخلات و توصیه‌ها
            if session.interventions_discussed:
                self.interventions_input.setText("\n".join(session.interventions_discussed))
            if session.recommendations:
                self.recommendations_input.setText("\n".join(session.recommendations))
            if session.homework:
                self.homework_input.setText("\n".join(session.homework))
            
            # نتیجه و پیگیری
            self.outcome_input.setText(session.outcome or "")
            self.follow_up_check.setChecked(session.follow_up_needed)
            self.next_date_input.set_date(session.next_session_date or "")
            self.next_notes_input.setText(session.next_session_notes or "")
            
            # وضعیت
            status_index = self.status_combo.findData(session.status)
            if status_index >= 0:
                self.status_combo.setCurrentIndex(status_index)
            
            self.on_follow_up_toggled(session.follow_up_needed)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری اطلاعات:\n{e!s}")
    
    def save_session(self):
        """ذخیره جلسه مشاوره"""
        # اعتبارسنجی
        student_index = self.student_combo.currentIndex()
        if student_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک دانش‌آموز انتخاب کنید")
            return
        
        counselor_index = self.counselor_combo.currentIndex()
        if counselor_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک مشاور انتخاب کنید")
            return
        
        if not self.date_input.is_valid():
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ را به صورت صحیح وارد کنید")
            return
        
        # دریافت پرونده دانش‌آموز
        student_id = self.student_combo.itemData(student_index)
        profile = self.profile_dal.get_active_by_student(student_id)
        if not profile:
            QMessageBox.warning(self, "خطا", "دانش‌آموز پرونده فعالی ندارد")
            return
        
        # ساخت داده‌ها
        goals_text = self.goals_input.toPlainText().strip()
        goals = [line.strip() for line in goals_text.split('\n') if line.strip()] if goals_text else None
        
        interventions_text = self.interventions_input.toPlainText().strip()
        interventions = [line.strip() for line in interventions_text.split('\n') if line.strip()] if interventions_text else None
        
        recommendations_text = self.recommendations_input.toPlainText().strip()
        recommendations = [line.strip() for line in recommendations_text.split('\n') if line.strip()] if recommendations_text else None
        
        homework_text = self.homework_input.toPlainText().strip()
        homework = [line.strip() for line in homework_text.split('\n') if line.strip()] if homework_text else None
        
        data = {
            'student_profile_id': profile.id,
            'counselor_id': self.counselor_combo.currentData(),
            'referred_by': self.referred_by_combo.currentData(),
            'session_date': self.date_input.get_date_string(),
            'session_time': self.time_input.text().strip(),
            'duration_minutes': self.duration_spin.value(),
            'type': self.type_combo.currentData(),
            'method': self.method_combo.currentData(),
            'location': self.location_input.text().strip(),
            'topic': self.topic_input.text().strip(),
            'goals': goals,
            'summary': self.summary_input.toPlainText().strip(),
            'details': self.details_input.toPlainText().strip(),
            'interventions_discussed': interventions,
            'recommendations': recommendations,
            'homework': homework,
            'outcome': self.outcome_input.toPlainText().strip(),
            'follow_up_needed': self.follow_up_check.isChecked(),
            'next_session_date': self.next_date_input.get_date_string() if self.follow_up_check.isChecked() else None,
            'next_session_notes': self.next_notes_input.toPlainText().strip() if self.follow_up_check.isChecked() else None,
            'status': self.status_combo.currentData()
        }
        
        try:
            if self.is_edit_mode:
                self.counseling_service.update_session(self.session_id, data)
                msg = "✅ جلسه مشاوره با موفقیت ویرایش شد"
            else:
                self.counseling_service.create_session(data)
                msg = "✅ جلسه مشاوره با موفقیت ثبت شد"
            
            QMessageBox.information(self, "موفقیت", msg)
            self.session_saved.emit()
            self.accept()
            
        except ValidationError as e:
            QMessageBox.warning(self, "خطا در اعتبارسنجی", str(e))
        except Exception as e:
            self.logger.error(f"خطا در ذخیره جلسه: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در ذخیره:\n{e!s}")