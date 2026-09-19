"""
فرم ثبت و ویرایش پیگیری - نسخه با پشتیبانی از سیستم راهنما
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
from services.followup_service import FollowUpService
from utils.error_handler import ServiceError, ValidationError
from utils.logger import get_logger
from utils.shamsi_date_input import ShamsiDateInput
from utils.tooltip_manager import TooltipManager
from views.widgets.help_widget import HelpWidget


class FollowUpForm(QDialog):
    """فرم ثبت و ویرایش پیگیری با پشتیبانی از سیستم راهنما"""

    followup_saved = Signal()

    def __init__(self, followup_id=None, intervention_id=None, parent=None):
        super().__init__(parent)

        self.followup_service = FollowUpService()
        self.student_dal = StudentDAL()
        self.staff_dal = StaffDAL()
        self.logger = get_logger(self.__class__.__name__)

        self.followup_id = followup_id
        self.existing_followup = None
        self.selected_intervention_id = intervention_id
        self.is_edit_mode = followup_id is not None

        self.setWindowTitle("ویرایش پیگیری" if self.is_edit_mode else "ثبت پیگیری جدید")
        self.setModal(True)
        self.resize(700, 750)

        self.setup_ui()
        self.load_students()
        self.load_staff()
        self.load_interventions()

        if self.is_edit_mode:
            self.load_followup_data()

        if self.selected_intervention_id and not self.is_edit_mode:
            for i in range(self.intervention_combo.count()):
                if self.intervention_combo.itemData(i) == self.selected_intervention_id:
                    self.intervention_combo.setCurrentIndex(i)
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
        self.help_widget = HelpWidget.create_for_followup_form(self)
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
        self.student_combo.setPlaceholderText("انتخاب دانش‌آموز...")
        self.student_combo.currentIndexChanged.connect(self.on_student_changed)
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.student_combo, 'student')
        form_layout.addRow("👤 دانش‌آموز:", self.student_combo)

        self.intervention_combo = QComboBox()
        self.intervention_combo.setPlaceholderText("انتخاب مداخله...")
        form_layout.addRow("🛠️ مداخله:", self.intervention_combo)

        self.staff_combo = QComboBox()
        self.staff_combo.setPlaceholderText("انتخاب مسئول پیگیری...")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.staff_combo, 'observer')
        form_layout.addRow("👤 مسئول پیگیری:", self.staff_combo)

        self.date_input = ShamsiDateInput()
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.date_input, 'date')
        form_layout.addRow("📅 تاریخ پیگیری:", self.date_input)

        self.next_date_input = ShamsiDateInput()
        form_layout.addRow("📅 تاریخ اقدام بعدی:", self.next_date_input)

        self.status_combo = QComboBox()
        self.status_combo.addItem("🟡 در انتظار", "pending")
        self.status_combo.addItem("✅ انجام شده", "done")
        self.status_combo.addItem("🔄 نیازمند ادامه", "continued")
        self.status_combo.addItem("🔒 مختومه", "closed")
        self.status_combo.addItem("❌ لغو شده", "cancelled")
        form_layout.addRow("📌 وضعیت:", self.status_combo)

        layout.addWidget(info_group)

        result_group = QGroupBox("📊 نتیجه پیگیری")
        result_group.setStyleSheet("""
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
        result_layout = QFormLayout(result_group)
        result_layout.setSpacing(8)

        self.result_type_combo = QComboBox()
        self.result_type_combo.addItem("انتخاب نوع نتیجه...", None)
        self.result_type_combo.addItem("بهبود مشاهده شد", "improved")
        self.result_type_combo.addItem("بدون تغییر قابل مشاهده", "no_change")
        self.result_type_combo.addItem("تداوم وضعیت", "continued")
        self.result_type_combo.addItem("وضعیت جدید", "new_status")
        self.result_type_combo.addItem("اطلاعات ناکافی", "insufficient")
        self.result_type_combo.addItem("نیازمند پیگیری بیشتر", "needs_more")
        result_layout.addRow("نوع نتیجه:", self.result_type_combo)

        self.result_description_input = QTextEdit()
        self.result_description_input.setPlaceholderText("شرح کامل نتیجه پیگیری...")
        self.result_description_input.setMaximumHeight(80)
        self.result_description_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 5px;")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.result_description_input, 'result')
        result_layout.addRow("شرح نتیجه:", self.result_description_input)

        layout.addWidget(result_group)

        desc_group = QGroupBox("📝 توضیحات پیگیری")
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
        self.description_input.setPlaceholderText("شرح کامل پیگیری انجام‌شده...")
        self.description_input.setMaximumHeight(100)
        self.description_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 5px;")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.description_input, 'description')
        desc_layout.addRow("توضیحات:", self.description_input)

        layout.addWidget(desc_group)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("💾 ذخیره پیگیری")
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
        self.save_btn.clicked.connect(self.save_followup)

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
            self.logger.error(f"خطا در بارگذاری دانش‌آموزان: {e}")

    def on_student_changed(self, index):
        if index >= 0:
            student_id = self.student_combo.itemData(index)
            if student_id:
                self.load_interventions_for_student(student_id)

    def load_interventions(self):
        try:
            student_index = self.student_combo.currentIndex()
            if student_index >= 0:
                student_id = self.student_combo.itemData(student_index)
                if student_id:
                    self.load_interventions_for_student(student_id)
                else:
                    self._clear_intervention_combo()
            else:
                self._clear_intervention_combo()
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری مداخلات: {e}")
            self._clear_intervention_combo()

    def load_interventions_for_student(self, student_id):
        try:
            interventions = self.followup_service.get_available_interventions_for_followup(student_id)
            self.intervention_combo.clear()
            for inter in interventions:
                display_text = f"{inter.type_display} - {inter.date}"
                self.intervention_combo.addItem(display_text, inter.id)
            self.logger.info(f"✅ {len(interventions)} مداخله بدون پیگیری یافت شد.")
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری مداخلات: {e}")
            self._clear_intervention_combo()

    def _clear_intervention_combo(self):
        self.intervention_combo.clear()
        self.intervention_combo.addItem("ابتدا دانش‌آموز را انتخاب کنید", None)

    def load_staff(self):
        try:
            staff_list = self.staff_dal.get_all()
            self.staff_combo.clear()
            for staff in staff_list:
                self.staff_combo.addItem(f"{staff.full_name} ({staff.role_display})", staff.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری مسئولان: {e}")
    
    def load_followup_data(self):
        """بارگذاری اطلاعات پیگیری برای ویرایش با استفاده از سرویس"""
        try:
            self.existing_followup = self.followup_service.get_followup(self.followup_id)
            if not self.existing_followup:
                QMessageBox.critical(self, "خطا", "پیگیری مورد نظر یافت نشد")
                self.reject()
                return
            
            follow = self.existing_followup
            
            # دریافت دانش‌آموز از مداخله
            student_id = getattr(follow, 'student_id', None)
            if student_id:
                for i in range(self.student_combo.count()):
                    if self.student_combo.itemData(i) == student_id:
                        self.student_combo.setCurrentIndex(i)
                        break
                # بارگذاری مداخلات برای این دانش‌آموز
                self.load_interventions_for_student(student_id)
            
            # انتخاب مداخله (در حالت ویرایش، مداخله خودش را نشان بده)
            for i in range(self.intervention_combo.count()):
                if self.intervention_combo.itemData(i) == follow.intervention_id:
                    self.intervention_combo.setCurrentIndex(i)
                    break
            
            # انتخاب مسئول
            for i in range(self.staff_combo.count()):
                if self.staff_combo.itemData(i) == follow.staff_id:
                    self.staff_combo.setCurrentIndex(i)
                    break
            
            self.date_input.set_date(follow.date or "")
            self.next_date_input.set_date(follow.next_action_date or "")
            
            # انتخاب وضعیت
            status_index = self.status_combo.findData(follow.status)
            if status_index >= 0:
                self.status_combo.setCurrentIndex(status_index)
            
            # انتخاب نوع نتیجه
            result_index = self.result_type_combo.findData(follow.result_type)
            if result_index >= 0:
                self.result_type_combo.setCurrentIndex(result_index)
            
            self.result_description_input.setText(follow.result_description or "")
            self.description_input.setText(follow.description or "")
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری اطلاعات:\n{str(e)}")
    
    def save_followup(self):
        """ذخیره پیگیری با استفاده از سرویس"""
        # ===== جمع‌آوری داده‌ها =====
        intervention_index = self.intervention_combo.currentIndex()
        if intervention_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک مداخله انتخاب کنید")
            return
        
        staff_index = self.staff_combo.currentIndex()
        if staff_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک مسئول پیگیری انتخاب کنید")
            return
        
        if not self.date_input.is_valid():
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ پیگیری را به صورت صحیح وارد کنید")
            return
        
        # ===== ساخت دیکشنری داده‌ها =====
        data = {
            'intervention_id': self.intervention_combo.itemData(intervention_index),
            'staff_id': self.staff_combo.itemData(staff_index),
            'date': self.date_input.get_date_string(),
            'next_action_date': self.next_date_input.get_date_string(),
            'status': self.status_combo.currentData(),
            'result_type': self.result_type_combo.currentData(),
            'result_description': self.result_description_input.toPlainText().strip(),
            'description': self.description_input.toPlainText().strip()
        }
        
        # ===== اعتبارسنجی با سرویس =====
        is_valid, errors = self.followup_service.validate_followup(data)
        if not is_valid:
            QMessageBox.warning(self, "خطا در اعتبارسنجی", "\n".join(errors))
            return
        
        # ===== ذخیره با سرویس =====
        try:
            if self.is_edit_mode:
                self.followup_service.update_followup(self.followup_id, data)
                msg = "✅ پیگیری با موفقیت ویرایش شد"
            else:
                self.followup_service.create_followup(data)
                msg = "✅ پیگیری با موفقیت ثبت شد"
            
            QMessageBox.information(self, "موفقیت", msg)
            self.followup_saved.emit()
            self.accept()
        except ValidationError as e:
            QMessageBox.warning(self, "خطا در اعتبارسنجی", str(e))
        except ServiceError as e:
            QMessageBox.critical(self, "خطا", str(e))
        except Exception as e:
            self.logger.error(f"خطا در ذخیره پیگیری: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در ذخیره:\n{str(e)}")