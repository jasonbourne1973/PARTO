"""
فرم ثبت و ویرایش مداخله - نسخه با پشتیبانی از سیستم راهنما
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dal.staff_dal import StaffDAL
from dal.student_dal import StudentDAL
from services.intervention_service import InterventionService
from utils.error_handler import ServiceError, ValidationError
from utils.logger import get_logger
from utils.shamsi_date_input import ShamsiDateInput
from utils.tooltip_manager import TooltipManager
from views.widgets.help_widget import HelpWidget


class InterventionForm(QDialog):
    """فرم ثبت و ویرایش مداخله با پشتیبانی از سیستم راهنما"""

    intervention_saved = Signal()

    def __init__(self, intervention_id=None, student_id=None, parent=None):
        super().__init__(parent)

        self.intervention_service = InterventionService()
        self.student_dal = StudentDAL()
        self.staff_dal = StaffDAL()
        self.logger = get_logger(self.__class__.__name__)

        self.intervention_id = intervention_id
        self.existing_intervention = None
        self.selected_student_id = student_id
        self.is_edit_mode = intervention_id is not None

        self.setWindowTitle("ویرایش مداخله" if self.is_edit_mode else "ثبت مداخله جدید")
        self.setModal(True)
        self.resize(700, 750)

        self.setup_ui()
        self.load_students()
        self.load_staff()
        self.load_observations()

        if self.is_edit_mode:
            self.load_intervention_data()

        if self.selected_student_id and not self.is_edit_mode:
            for i in range(self.student_combo.count()):
                if self.student_combo.itemData(i) == self.selected_student_id:
                    self.student_combo.setCurrentIndex(i)
                    break

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

        # ===== ویجت راهنمای سریع =====
        self.help_widget = HelpWidget.create_for_intervention_form(self)
        layout.addWidget(self.help_widget)

        info_group = QGroupBox("📋 اطلاعات پایه")
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
        form_layout.setSpacing(8)

        self.student_combo = QComboBox()
        self.student_combo.setEditable(True)
        self.student_combo.setPlaceholderText("جستجو و انتخاب دانش‌آموز...")
        self.student_combo.currentIndexChanged.connect(self.on_student_changed)
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.student_combo, 'student')
        form_layout.addRow("👤 دانش‌آموز:", self.student_combo)

        self.observer_combo = QComboBox()
        self.observer_combo.setPlaceholderText("انتخاب مسئول مداخله...")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.observer_combo, 'observer')
        form_layout.addRow("👤 مسئول:", self.observer_combo)

        self.observation_combo = QComboBox()
        self.observation_combo.setPlaceholderText("انتخاب مشاهده مرتبط (اختیاری)...")
        form_layout.addRow("📋 مشاهده مرتبط:", self.observation_combo)

        self.date_input = ShamsiDateInput()
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.date_input, 'date')
        form_layout.addRow("📅 تاریخ مداخله:", self.date_input)

        layout.addWidget(info_group)

        type_group = QGroupBox("🎯 نوع مداخله")
        type_group.setStyleSheet("""
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
        type_layout = QFormLayout(type_group)

        self.type_combo = QComboBox()
        intervention_types = [
            ("individual_talk", "گفتگوی فردی"),
            ("group_talk", "گفتگوی گروهی"),
            ("parent_call", "تماس با والدین"),
            ("parent_meeting", "جلسه با والدین"),
            ("responsibility", "سپردن مسئولیت"),
            ("encouragement", "تشویق"),
            ("group_activity", "فعالیت گروهی"),
            ("educational_game", "بازی تربیتی"),
            ("referral", "ارجاع به مشاور"),
            ("counseling", "مشاوره"),
            ("seat_change", "تغییر جای نشستن"),
            ("peer_helper", "همیار دانش‌آموز"),
            ("warning", "تذکر شفاهی"),
            ("other", "سایر")
        ]
        for value, display in intervention_types:
            self.type_combo.addItem(display, value)
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.type_combo, 'intervention_type')
        type_layout.addRow("نوع مداخله:", self.type_combo)

        layout.addWidget(type_group)

        desc_group = QGroupBox("📝 توضیحات مداخله")
        desc_group.setStyleSheet("""
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
        desc_layout = QFormLayout(desc_group)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("شرح کامل مداخله انجام‌شده...")
        self.description_input.setMaximumHeight(100)
        self.description_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 5px;")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.description_input, 'description')
        desc_layout.addRow("توضیحات:", self.description_input)

        self.goal_input = QTextEdit()
        self.goal_input.setPlaceholderText("هدف از مداخله (اختیاری)...")
        self.goal_input.setMaximumHeight(60)
        self.goal_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 5px;")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.goal_input, 'goal')
        desc_layout.addRow("🎯 هدف:", self.goal_input)

        self.result_input = QTextEdit()
        self.result_input.setPlaceholderText("نتیجه مداخله (در صورت مشخص بودن)...")
        self.result_input.setMaximumHeight(60)
        self.result_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 5px;")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.result_input, 'result')
        desc_layout.addRow("📊 نتیجه:", self.result_input)

        layout.addWidget(desc_group)

        status_group = QGroupBox("📌 وضعیت")
        status_group.setStyleSheet("""
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
        status_layout = QFormLayout(status_group)

        self.status_combo = QComboBox()
        self.status_combo.addItem("🟡 برنامه‌ریزی شده", "planned")
        self.status_combo.addItem("🔄 در حال اجرا", "in_progress")
        self.status_combo.addItem("✅ انجام شده", "done")
        self.status_combo.addItem("🟢 تکمیل شده", "completed")
        self.status_combo.addItem("❌ لغو شده", "cancelled")
        status_layout.addRow("وضعیت:", self.status_combo)

        layout.addWidget(status_group)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("💾 ذخیره مداخله")
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
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.save_btn.clicked.connect(self.save_intervention)

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

        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        layout.addSpacing(10)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def load_students(self):
        try:
            students = self.student_dal.get_all()
            self.student_combo.clear()
            for student in students:
                self.student_combo.addItem(student.full_name, student.id)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری دانش‌آموزان:\n{str(e)}")

    def load_staff(self):
        try:
            staff_list = self.staff_dal.get_all()
            self.observer_combo.clear()
            for staff in staff_list:
                self.observer_combo.addItem(f"{staff.full_name} ({staff.role_display})", staff.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری مسئولان: {e}")

    def on_student_changed(self, index):
        if index >= 0:
            student_id = self.student_combo.itemData(index)
            if student_id:
                self.load_observations_for_student(student_id)

    def load_observations(self):
        try:
            self.observation_combo.clear()
            self.observation_combo.addItem("بدون مشاهده مرتبط", None)
            student_index = self.student_combo.currentIndex()
            if student_index >= 0:
                student_id = self.student_combo.itemData(student_index)
                if student_id:
                    self.load_observations_for_student(student_id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری مشاهدات: {e}")

    def load_observations_for_student(self, student_id):
        try:
            observations = self.intervention_service.get_available_observations_for_intervention(student_id)
            self.observation_combo.clear()
            self.observation_combo.addItem("بدون مشاهده مرتبط", None)
            for obs in observations:
                display_text = f"{obs.observation_date} - {obs.description[:30]}..."
                self.observation_combo.addItem(display_text, obs.id)
            self.logger.info(f"✅ {len(observations)} مشاهده بدون مداخله یافت شد.")
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری مشاهدات: {e}")
            self.observation_combo.clear()
            self.observation_combo.addItem("بدون مشاهده مرتبط", None)
    
    def load_intervention_data(self):
        """بارگذاری اطلاعات مداخله برای ویرایش با استفاده از سرویس"""
        try:
            self.existing_intervention = self.intervention_service.get_intervention(self.intervention_id)
            if not self.existing_intervention:
                QMessageBox.critical(self, "خطا", "مداخله مورد نظر یافت نشد")
                self.reject()
                return
            
            inter = self.existing_intervention
            
            # انتخاب دانش‌آموز
            student_id = getattr(inter, 'student_id', None)
            if student_id:
                for i in range(self.student_combo.count()):
                    if self.student_combo.itemData(i) == student_id:
                        self.student_combo.setCurrentIndex(i)
                        break
                # بارگذاری مشاهدات بدون مداخله برای این دانش‌آموز
                self.load_observations_for_student(student_id)
            
            # انتخاب مسئول
            for i in range(self.observer_combo.count()):
                if self.observer_combo.itemData(i) == inter.staff_id:
                    self.observer_combo.setCurrentIndex(i)
                    break
            
            # انتخاب مشاهده مرتبط
            if inter.observation_id:
                # ابتدا مطمئن شویم که مشاهده در لیست وجود دارد
                for i in range(self.observation_combo.count()):
                    if self.observation_combo.itemData(i) == inter.observation_id:
                        self.observation_combo.setCurrentIndex(i)
                        break
                else:
                    # اگر مشاهده در لیست نبود، آن را اضافه کنیم
                    from dal.observation_dal import ObservationDAL
                    obs_dal = ObservationDAL()
                    obs = obs_dal.get_by_id(inter.observation_id)
                    if obs:
                        display_text = f"{obs.observation_date} - {obs.description[:30]}..."
                        self.observation_combo.addItem(display_text, obs.id)
                        self.observation_combo.setCurrentIndex(self.observation_combo.count() - 1)
            
            self.date_input.set_date(inter.date or "")
            
            # انتخاب نوع
            type_index = self.type_combo.findData(inter.type)
            if type_index >= 0:
                self.type_combo.setCurrentIndex(type_index)
            
            self.description_input.setText(inter.description or "")
            self.goal_input.setText(inter.goal or "")
            self.result_input.setText(inter.result or "")
            
            # انتخاب وضعیت
            status_index = self.status_combo.findData(inter.status)
            if status_index >= 0:
                self.status_combo.setCurrentIndex(status_index)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری اطلاعات:\n{str(e)}")
    
    def save_intervention(self):
        """ذخیره مداخله با استفاده از سرویس"""
        # ===== جمع‌آوری داده‌ها =====
        student_index = self.student_combo.currentIndex()
        if student_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک دانش‌آموز انتخاب کنید")
            return
        
        observer_index = self.observer_combo.currentIndex()
        if observer_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک مسئول انتخاب کنید")
            return
        
        if not self.date_input.is_valid():
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ را به صورت صحیح وارد کنید")
            return
        
        # ===== ساخت دیکشنری داده‌ها =====
        data = {
            'student_id': self.student_combo.itemData(student_index),
            'staff_id': self.observer_combo.itemData(observer_index),
            'observation_id': self.observation_combo.currentData(),
            'type': self.type_combo.currentData(),
            'date': self.date_input.get_date_string(),
            'description': self.description_input.toPlainText().strip(),
            'goal': self.goal_input.toPlainText().strip(),
            'status': self.status_combo.currentData(),
            'result': self.result_input.toPlainText().strip()
        }
        
        # ===== اعتبارسنجی با سرویس =====
        is_valid, errors = self.intervention_service.validate_intervention(data)
        if not is_valid:
            QMessageBox.warning(self, "خطا در اعتبارسنجی", "\n".join(errors))
            return
        
        # ===== ذخیره با سرویس =====
        try:
            if self.is_edit_mode:
                self.intervention_service.update_intervention(self.intervention_id, data)
                msg = "✅ مداخله با موفقیت ویرایش شد"
            else:
                self.intervention_service.create_intervention(data)
                msg = "✅ مداخله با موفقیت ثبت شد"
            
            QMessageBox.information(self, "موفقیت", msg)
            self.intervention_saved.emit()
            self.accept()
        except ValidationError as e:
            QMessageBox.warning(self, "خطا در اعتبارسنجی", str(e))
        except ServiceError as e:
            QMessageBox.critical(self, "خطا", str(e))
        except Exception as e:
            self.logger.error(f"خطا در ذخیره مداخله: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در ذخیره:\n{str(e)}")