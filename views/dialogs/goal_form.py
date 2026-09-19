"""
فرم ثبت و ویرایش هدف فردی - نسخه با پشتیبانی از سیستم راهنما
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
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
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dal.competency_dal import CompetencyDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.individual_goal import IndividualGoal
from services.goal_service import GoalService
from utils.error_handler import ValidationError
from utils.logger import get_logger
from utils.shamsi_date_input import ShamsiDateInput
from utils.tooltip_manager import TooltipManager
from views.widgets.help_widget import HelpWidget


class GoalForm(QDialog):
    """فرم ثبت و ویرایش هدف فردی با پشتیبانی از سیستم راهنما"""

    goal_saved = Signal()

    def __init__(self, goal_id=None, profile_id=None, parent=None):
        super().__init__(parent)

        self.goal_service = GoalService()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.competency_dal = CompetencyDAL()
        self.logger = get_logger(self.__class__.__name__)

        self.goal_id = goal_id
        self.profile_id = profile_id
        self.existing_goal = None
        self.is_edit_mode = goal_id is not None

        self.setWindowTitle("ویرایش هدف" if self.is_edit_mode else "ثبت هدف جدید")
        self.setModal(True)
        self.resize(650, 700)

        self.setup_ui()
        self.load_students()
        self.load_staff()
        self.load_competencies()

        if self.is_edit_mode:
            self.load_goal_data()
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
            "راهنمای ثبت هدف",
            "اهداف فردی برای پیگیری و تقویت مهارت‌های خاص دانش‌آموز در حوزه‌های مختلف.",
            self
        )
        layout.addWidget(self.help_widget)

        # ===== گروه اطلاعات پایه =====
        info_group = QGroupBox("📋 اطلاعات هدف")
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

        # مسئول پیگیری
        self.assignee_combo = QComboBox()
        self.assignee_combo.addItem("بدون مسئول", None)
        self.assignee_combo.setPlaceholderText("انتخاب مسئول پیگیری...")
        self.assignee_combo.setMinimumHeight(32)
        TooltipManager.set_field_tooltip(self.assignee_combo, 'observer')
        form_layout.addRow("👨‍🏫 مسئول پیگیری:", self.assignee_combo)

        # عنوان
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("عنوان هدف...")
        self.title_input.setMinimumHeight(32)
        form_layout.addRow("📝 عنوان:", self.title_input)

        # حوزه و اولویت
        domain_priority_layout = QVBoxLayout()

        domain_widget = QWidget()
        domain_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        domain_layout = QVBoxLayout(domain_widget)
        domain_layout.setContentsMargins(0, 0, 0, 0)
        domain_layout.addWidget(QLabel("حوزه:"))
        self.domain_combo = QComboBox()
        for value, display in IndividualGoal.DOMAIN_CHOICES:
            self.domain_combo.addItem(display, value)
        self.domain_combo.setMinimumHeight(32)
        domain_layout.addWidget(self.domain_combo)
        domain_priority_layout.addWidget(domain_widget)

        priority_widget = QWidget()
        priority_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        priority_layout = QVBoxLayout(priority_widget)
        priority_layout.setContentsMargins(0, 0, 0, 0)
        priority_layout.addWidget(QLabel("اولویت:"))
        self.priority_combo = QComboBox()
        for value, display in IndividualGoal.PRIORITY_CHOICES:
            self.priority_combo.addItem(display, value)
        self.priority_combo.setMinimumHeight(32)
        priority_layout.addWidget(self.priority_combo)
        domain_priority_layout.addWidget(priority_widget)

        domain_priority_layout.addStretch()
        form_layout.addRow("🎯 حوزه و اولویت:", domain_priority_layout)

        # شایستگی مرتبط
        self.competency_combo = QComboBox()
        self.competency_combo.addItem("بدون شایستگی", None)
        self.competency_combo.setPlaceholderText("انتخاب شایستگی مرتبط...")
        self.competency_combo.setMinimumHeight(32)
        form_layout.addRow("📊 شایستگی مرتبط:", self.competency_combo)

        layout.addWidget(info_group)

        # ===== گروه تاریخ‌ها =====
        date_group = QGroupBox("📅 بازه زمانی")
        date_group.setStyleSheet("""
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
        date_layout = QVBoxLayout(date_group)
        date_layout.setSpacing(15)

        start_widget = QWidget()
        start_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        start_date_layout = QVBoxLayout(start_widget)
        start_date_layout.setContentsMargins(0, 0, 0, 0)
        start_date_layout.addWidget(QLabel("تاریخ شروع:"))
        self.start_date_input = ShamsiDateInput()
        TooltipManager.set_field_tooltip(self.start_date_input, 'date')
        start_date_layout.addWidget(self.start_date_input)
        date_layout.addWidget(start_widget)

        target_widget = QWidget()
        target_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        target_date_layout = QVBoxLayout(target_widget)
        target_date_layout.setContentsMargins(0, 0, 0, 0)
        target_date_layout.addWidget(QLabel("تاریخ هدف:"))
        self.target_date_input = ShamsiDateInput()
        target_date_layout.addWidget(self.target_date_input)
        date_layout.addWidget(target_widget)

        end_widget = QWidget()
        end_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        end_date_layout = QVBoxLayout(end_widget)
        end_date_layout.setContentsMargins(0, 0, 0, 0)
        end_date_layout.addWidget(QLabel("تاریخ پایان:"))
        self.end_date_input = ShamsiDateInput()
        end_date_layout.addWidget(self.end_date_input)
        date_layout.addWidget(end_widget)

        layout.addWidget(date_group)

        # ===== گروه توضیحات =====
        desc_group = QGroupBox("📄 توضیحات")
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
        self.description_input.setPlaceholderText("توضیحات کامل هدف...")
        self.description_input.setMaximumHeight(80)
        self.description_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        TooltipManager.set_field_tooltip(self.description_input, 'description')
        desc_layout.addRow("📝 توضیحات:", self.description_input)

        self.criteria_input = QTextEdit()
        self.criteria_input.setPlaceholderText("معیارهای موفقیت (هر مورد در یک خط)...")
        self.criteria_input.setMaximumHeight(60)
        self.criteria_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        desc_layout.addRow("✅ معیارهای موفقیت:", self.criteria_input)

        layout.addWidget(desc_group)

        # ===== گروه پیشرفت و وضعیت =====
        progress_group = QGroupBox("📊 پیشرفت و وضعیت")
        progress_group.setStyleSheet("""
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
        progress_layout = QFormLayout(progress_group)
        progress_layout.setSpacing(8)

        progress_row = QHBoxLayout()
        progress_row.addWidget(QLabel("درصد پیشرفت:"))
        self.progress_spin = QSpinBox()
        self.progress_spin.setRange(0, 100)
        self.progress_spin.setValue(0)
        self.progress_spin.setMinimumHeight(32)
        progress_row.addWidget(self.progress_spin)
        progress_row.addWidget(QLabel("%"))
        progress_row.addStretch()
        progress_layout.addRow(progress_row)

        self.progress_notes_input = QTextEdit()
        self.progress_notes_input.setPlaceholderText("یادداشت‌های پیشرفت...")
        self.progress_notes_input.setMaximumHeight(60)
        self.progress_notes_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        progress_layout.addRow("📝 یادداشت پیشرفت:", self.progress_notes_input)

        self.status_combo = QComboBox()
        for value, display in IndividualGoal.STATUS_CHOICES:
            self.status_combo.addItem(display, value)
        self.status_combo.setMinimumHeight(32)
        progress_layout.addRow("📌 وضعیت:", self.status_combo)

        self.result_input = QTextEdit()
        self.result_input.setPlaceholderText("نتیجه نهایی (در صورت تکمیل)...")
        self.result_input.setMaximumHeight(60)
        self.result_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px;")
        progress_layout.addRow("📊 نتیجه:", self.result_input)

        layout.addWidget(progress_group)

        # ===== دکمه‌ها =====
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("💾 ذخیره هدف")
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
        self.save_btn.clicked.connect(self.save_goal)
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
        """بارگذاری دانش‌آموزان"""
        try:
            students = self.student_dal.get_all()
            self.student_combo.clear()
            for student in students:
                self.student_combo.addItem(student.full_name, student.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری دانش‌آموزان: {e}")
    
    def load_staff(self):
        """بارگذاری اعضای کادر"""
        try:
            staff_list = self.staff_dal.get_all()
            self.assignee_combo.clear()
            self.assignee_combo.addItem("بدون مسئول", None)
            for staff in staff_list:
                self.assignee_combo.addItem(f"{staff.full_name}", staff.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری اعضای کادر: {e}")
    
    def load_competencies(self):
        """بارگذاری شایستگی‌ها"""
        try:
            competencies = self.competency_dal.get_all()
            self.competency_combo.clear()
            self.competency_combo.addItem("بدون شایستگی", None)
            for comp in competencies:
                self.competency_combo.addItem(comp.title, comp.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری شایستگی‌ها: {e}")
    
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
    
    def load_goal_data(self):
        """بارگذاری اطلاعات هدف برای ویرایش"""
        try:
            self.existing_goal = self.goal_service.get_goal(self.goal_id)
            if not self.existing_goal:
                QMessageBox.critical(self, "خطا", "هدف مورد نظر یافت نشد")
                self.reject()
                return
            
            goal = self.existing_goal
            
            # دانش‌آموز
            profile = self.profile_dal.get_by_id(goal.student_profile_id)
            if profile:
                for i in range(self.student_combo.count()):
                    if self.student_combo.itemData(i) == profile.student_id:
                        self.student_combo.setCurrentIndex(i)
                        break
            
            # مسئول
            if goal.assigned_to:
                for i in range(self.assignee_combo.count()):
                    if self.assignee_combo.itemData(i) == goal.assigned_to:
                        self.assignee_combo.setCurrentIndex(i)
                        break
            
            self.title_input.setText(goal.title or "")
            
            domain_index = self.domain_combo.findData(goal.domain)
            if domain_index >= 0:
                self.domain_combo.setCurrentIndex(domain_index)
            
            priority_index = self.priority_combo.findData(goal.priority)
            if priority_index >= 0:
                self.priority_combo.setCurrentIndex(priority_index)
            
            if goal.related_competency_id:
                for i in range(self.competency_combo.count()):
                    if self.competency_combo.itemData(i) == goal.related_competency_id:
                        self.competency_combo.setCurrentIndex(i)
                        break
            
            self.start_date_input.set_date(goal.start_date or "")
            self.target_date_input.set_date(goal.target_date or "")
            self.end_date_input.set_date(goal.end_date or "")
            
            self.description_input.setText(goal.description or "")
            if goal.success_criteria:
                self.criteria_input.setText("\n".join(goal.success_criteria))
            
            self.progress_spin.setValue(goal.progress_percent or 0)
            self.progress_notes_input.setText(goal.progress_notes or "")
            
            status_index = self.status_combo.findData(goal.status)
            if status_index >= 0:
                self.status_combo.setCurrentIndex(status_index)
            
            self.result_input.setText(goal.result or "")
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری اطلاعات:\n{str(e)}")
    
    def save_goal(self):
        """ذخیره هدف"""
        # اعتبارسنجی
        student_index = self.student_combo.currentIndex()
        if student_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک دانش‌آموز انتخاب کنید")
            return
        
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "خطا", "لطفاً عنوان هدف را وارد کنید")
            return
        
        # دریافت پرونده دانش‌آموز
        student_id = self.student_combo.itemData(student_index)
        profile = self.profile_dal.get_active_by_student(student_id)
        if not profile:
            QMessageBox.warning(self, "خطا", "دانش‌آموز پرونده فعالی ندارد")
            return
        
        # ساخت داده‌ها
        criteria_text = self.criteria_input.toPlainText().strip()
        criteria = [line.strip() for line in criteria_text.split('\n') if line.strip()] if criteria_text else None
        
        data = {
            'student_profile_id': profile.id,
            'assigned_to': self.assignee_combo.currentData(),
            'related_competency_id': self.competency_combo.currentData(),
            'title': self.title_input.text().strip(),
            'description': self.description_input.toPlainText().strip(),
            'domain': self.domain_combo.currentData(),
            'priority': self.priority_combo.currentData(),
            'success_criteria': criteria,
            'start_date': self.start_date_input.get_date_string(),
            'target_date': self.target_date_input.get_date_string(),
            'end_date': self.end_date_input.get_date_string(),
            'progress_percent': self.progress_spin.value(),
            'progress_notes': self.progress_notes_input.toPlainText().strip(),
            'status': self.status_combo.currentData(),
            'result': self.result_input.toPlainText().strip()
        }
        
        try:
            if self.is_edit_mode:
                self.goal_service.update_goal(self.goal_id, data)
                msg = "✅ هدف با موفقیت ویرایش شد"
            else:
                self.goal_service.create_goal(data)
                msg = "✅ هدف با موفقیت ثبت شد"
            
            QMessageBox.information(self, "موفقیت", msg)
            self.goal_saved.emit()
            self.accept()
            
        except ValidationError as e:
            QMessageBox.warning(self, "خطا در اعتبارسنجی", str(e))
        except Exception as e:
            self.logger.error(f"خطا در ذخیره هدف: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در ذخیره:\n{str(e)}")