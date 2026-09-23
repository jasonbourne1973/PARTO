"""
فرم ثبت و ویرایش مشاهده - نسخه با پشتیبانی از سیستم راهنما
"""

import jdatetime
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
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

from config.settings import OBSERVATION_LOCATIONS
from dal.competency_dal import CompetencyDAL
from dal.staff_dal import StaffDAL
from dal.student_dal import StudentDAL
from services.observation_service import ObservationService
from utils.constants import DEFAULT_SEVERITY, SUGGESTED_TAGS
from utils.error_handler import ServiceError, ValidationError
from utils.logger import get_logger
from utils.shamsi_date_input import ShamsiDateInput
from utils.tooltip_manager import TooltipManager
from utils.ui_guards import single_submit
from views.widgets.competency_tree_widget import CompetencyTreeWidget
from views.widgets.help_widget import HelpWidget


class ObservationForm(QDialog):
    """
    فرم ثبت و ویرایش مشاهده - با پشتیبانی از سیستم راهنما
    """

    observation_saved = Signal()

    def __init__(self, observation_id=None, student_id=None, parent=None):
        super().__init__(parent)

        self.observation_service = ObservationService()
        self.student_dal = StudentDAL()
        self.staff_dal = StaffDAL()
        self.competency_dal = CompetencyDAL()
        self.logger = get_logger(self.__class__.__name__)

        self.observation_id = observation_id
        self.existing_observation = None
        self.selected_student_id = student_id
        self.selected_competency_id = None
        self.selected_indicator_id = None
        self.selected_behavior_id = None

        self.is_edit_mode = observation_id is not None

        self.setWindowTitle("ویرایش مشاهده" if self.is_edit_mode else "ثبت مشاهده جدید")
        self.setModal(True)
        self.resize(800, 850)

        self.setup_ui()
        self.load_students()
        self.load_staff()
        self.set_default_date()

        if self.is_edit_mode:
            self.load_observation_data()

        if self.selected_student_id and not self.is_edit_mode:
            for i in range(self.student_combo.count()):
                if self.student_combo.itemData(i) == self.selected_student_id:
                    self.student_combo.setCurrentIndex(i)
                    break

        QTimer.singleShot(100, self.behavior_input.setFocus)

    def setup_ui(self):
        """راه‌اندازی رابط کاربری با Tooltip و راهنما"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)
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
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # ===== هدر =====
        header_layout = QHBoxLayout()

        title_label = QLabel("📝 ثبت مشاهده" if not self.is_edit_mode else "✏️ ویرایش مشاهده")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #F4C542;
            }
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.guide_btn = QPushButton("❓ راهنما")
        self.guide_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #08223A; }
        """)
        self.guide_btn.clicked.connect(self.show_guide)
        header_layout.addWidget(self.guide_btn)

        layout.addLayout(header_layout)

        # ===== ویجت راهنمای سریع =====
        self.help_widget = HelpWidget.create_for_observation_form(self)
        layout.addWidget(self.help_widget)

        # ===== گروه اطلاعات اصلی =====
        main_group = QGroupBox("اطلاعات مشاهده")
        main_group.setStyleSheet("""
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
        form_layout = QFormLayout(main_group)
        form_layout.setSpacing(6)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # ===== ردیف ۱: دانش‌آموز و تاریخ =====
        row1_layout = QVBoxLayout()
        row1_layout.setSpacing(15)

        # دانش‌آموز
        student_widget = QWidget()
        student_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        student_layout = QVBoxLayout(student_widget)
        student_layout.setContentsMargins(0, 0, 0, 0)
        student_label = QLabel("دانش‌آموز:")
        student_label.setStyleSheet("font-weight: bold; color: #F4C542;")
        student_layout.addWidget(student_label)

        self.student_combo = QComboBox()
        self.student_combo.setEditable(True)
        self.student_combo.setPlaceholderText("جستجو و انتخاب...")
        self.student_combo.setMinimumHeight(32)
        self.student_combo.setStyleSheet("""
            QComboBox {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                min-width: 180px;
            }
            QComboBox:focus {
    color: #FFE8A3;
    background-color: #0B2E4F; border: 2px solid #F4C542; }
            QComboBox::drop-down { border: none; }
        """)
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.student_combo, 'student')
        student_layout.addWidget(self.student_combo)
        row1_layout.addWidget(student_widget, 2)

        # تاریخ
        date_widget = QWidget()
        date_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        date_layout = QVBoxLayout(date_widget)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_label = QLabel("تاریخ:")
        date_label.setStyleSheet("font-weight: bold; color: #F4C542;")
        date_layout.addWidget(date_label)

        self.date_input = ShamsiDateInput()
        self.date_input.setMinimumHeight(32)
        self.date_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                min-width: 120px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F; border: 2px solid #F4C542; }
        """)
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.date_input, 'date')
        date_layout.addWidget(self.date_input)
        row1_layout.addWidget(date_widget, 1)

        form_layout.addRow(row1_layout)

        # ===== ردیف ۲: مشاهده‌گر و محیط =====
        row2_layout = QVBoxLayout()
        row2_layout.setSpacing(15)

        # مشاهده‌گر
        observer_widget = QWidget()
        observer_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        observer_layout = QVBoxLayout(observer_widget)
        observer_layout.setContentsMargins(0, 0, 0, 0)
        observer_label = QLabel("مشاهده‌گر:")
        observer_label.setStyleSheet("font-weight: bold; color: #F4C542;")
        observer_layout.addWidget(observer_label)

        self.observer_combo = QComboBox()
        self.observer_combo.setPlaceholderText("انتخاب مشاهده‌گر...")
        self.observer_combo.setMinimumHeight(32)
        self.observer_combo.setStyleSheet("""
            QComboBox {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                min-width: 150px;
            }
            QComboBox:focus {
    color: #FFE8A3;
    background-color: #0B2E4F; border: 2px solid #F4C542; }
        """)
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.observer_combo, 'observer')
        observer_layout.addWidget(self.observer_combo)
        row2_layout.addWidget(observer_widget, 2)

        # محیط
        location_widget = QWidget()
        location_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        location_layout = QVBoxLayout(location_widget)
        location_layout.setContentsMargins(0, 0, 0, 0)
        location_label = QLabel("محیط:")
        location_label.setStyleSheet("font-weight: bold; color: #F4C542;")
        location_layout.addWidget(location_label)

        self.location_combo = QComboBox()
        for loc in OBSERVATION_LOCATIONS:
            self.location_combo.addItem(loc)
        self.location_combo.setMinimumHeight(32)
        self.location_combo.setStyleSheet("""
            QComboBox {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                min-width: 120px;
            }
            QComboBox:focus {
    color: #FFE8A3;
    background-color: #0B2E4F; border: 2px solid #F4C542; }
        """)
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.location_combo, 'location')
        location_layout.addWidget(self.location_combo)
        row2_layout.addWidget(location_widget, 1)

        form_layout.addRow(row2_layout)

        layout.addWidget(main_group)

        # ===== گروه رفتار =====
        behavior_group = QGroupBox("رفتار مشاهده‌شده")
        behavior_group.setStyleSheet("""
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
        behavior_layout = QVBoxLayout(behavior_group)

        quick_guide = QLabel("✏️ رفتار قابل مشاهده را ثبت کنید (مثال: در زنگ تفریح، همکلاسی را هل داد)")
        quick_guide.setStyleSheet("""
            QLabel {
                background-color: #C62828;
                padding: 5px 10px;
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 12px;
                border: 1px solid #F4C542;
            }
        """)
        quick_guide.setWordWrap(True)
        behavior_layout.addWidget(quick_guide)

        self.behavior_input = QTextEdit()
        self.behavior_input.setPlaceholderText("رفتار مشاهده‌شده را به طور مختصر و عینی ثبت کنید...")
        self.behavior_input.setMinimumHeight(60)
        self.behavior_input.setMaximumHeight(100)
        self.behavior_input.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                border: 1px solid #8BC34A;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                background-color: #08223A;
            }
            QTextEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F; border: 2px solid #F4C542; }
        """)
        behavior_layout.addWidget(self.behavior_input)

        self.show_more_btn = QPushButton("🔽 نمایش فیلدهای بیشتر (اختیاری)")
        self.show_more_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #D9C36A;
                border: none;
                font-size: 12px;
                text-align: right;
                padding: 2px;
            }
            QPushButton:hover { color: #F4C542; }
        """)
        self.show_more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_more_btn.clicked.connect(self.toggle_more_fields)
        behavior_layout.addWidget(self.show_more_btn)

        # ===== فیلدهای بیشتر =====
        self.more_widget = QWidget()
        more_layout = QFormLayout(self.more_widget)
        more_layout.setSpacing(6)
        more_layout.setContentsMargins(0, 5, 0, 5)

        # Antecedent
        self.antecedent_input = QTextEdit()
        self.antecedent_input.setPlaceholderText("قبل از رفتار چه اتفاقی افتاد؟ (اختیاری)")
        self.antecedent_input.setMaximumHeight(40)
        self.antecedent_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px; font-size: 12px;")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.antecedent_input, 'antecedent')
        more_layout.addRow("🔴 زمینه:", self.antecedent_input)

        # Consequence
        self.consequence_input = QTextEdit()
        self.consequence_input.setPlaceholderText("پس از رفتار چه اتفاقی افتاد؟ (اختیاری)")
        self.consequence_input.setMaximumHeight(40)
        self.consequence_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px; font-size: 12px;")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.consequence_input, 'consequence')
        more_layout.addRow("🟢 پیامد:", self.consequence_input)

        # توضیحات
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("توضیحات تکمیلی (اختیاری)...")
        self.description_input.setMaximumHeight(40)
        self.description_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px; font-size: 12px;")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.description_input, 'description')
        more_layout.addRow("📝 توضیحات:", self.description_input)

        # برچسب‌ها
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("ورزشی, آموزشی, رفتاری, ... (اختیاری)")
        self.tags_input.setStyleSheet("border: 1px solid #D9C36A; border-radius: 4px; padding: 4px; font-size: 12px;")
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.tags_input, 'tags')
        more_layout.addRow("🏷️ برچسب‌ها:", self.tags_input)

        self.more_widget.setVisible(False)
        behavior_layout.addWidget(self.more_widget)

        layout.addWidget(behavior_group)

        # ===== گروه شایستگی =====
        competency_group = QGroupBox("📊 شایستگی مرتبط (اختیاری)")
        competency_group.setStyleSheet("""
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
        competency_layout = QVBoxLayout(competency_group)

        comp_guide = QLabel("💡 می‌توانید شایستگی، شاخص یا رفتار قابل مشاهده مرتبط را انتخاب کنید")
        comp_guide.setStyleSheet("""
            QLabel {
                background-color: #66BB6A;
                padding: 5px 10px;
                border-radius: 4px;
                color: #111111;
                font-size: 12px;
                border: 1px solid #8BC34A;
            }
        """)
        comp_guide.setWordWrap(True)
        competency_layout.addWidget(comp_guide)

        self.competency_tree = CompetencyTreeWidget(show_select_buttons=False)
        self.competency_tree.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        self.competency_tree.setMinimumWidth(0)
        self.competency_tree.setMinimumHeight(200)
        self.competency_tree.setMaximumHeight(300)
        self.competency_tree.full_path_selected.connect(self.on_competency_selected)
        competency_layout.addWidget(self.competency_tree)

        self.selected_path_label = QLabel("هیچ شایستگی‌ای انتخاب نشده است")
        self.selected_path_label.setStyleSheet("""
            QLabel {
                color: #D9C36A;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #0B2E4F;
                border-radius: 4px;
                border: 1px solid #08223A;
                font-weight: bold;
            }
        """)
        self.selected_path_label.setWordWrap(True)
        competency_layout.addWidget(self.selected_path_label)

        clear_comp_btn = QPushButton("🗑️ پاک کردن انتخاب شایستگی")
        clear_comp_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 4px 15px;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #D94B4B; }
        """)
        clear_comp_btn.clicked.connect(self.clear_competency_selection)
        competency_layout.addWidget(clear_comp_btn)

        layout.addWidget(competency_group)

        # ===== ردیف نوع و شدت =====
        type_severity_layout = QHBoxLayout()
        type_severity_layout.setSpacing(20)

        # نوع رفتار
        type_widget = QWidget()
        type_layout = QVBoxLayout(type_widget)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_label = QLabel("نوع رفتار:")
        type_label.setStyleSheet("font-weight: bold; color: #F4C542;")
        type_layout.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["مثبت", "منفی", "خنثی"])
        self.type_combo.setMinimumHeight(30)
        self.type_combo.setStyleSheet("""
            QComboBox {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                min-width: 100px;
            }
        """)
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.type_combo, 'behavior_type')
        type_layout.addWidget(self.type_combo)
        type_severity_layout.addWidget(type_widget)

        # شدت
        severity_widget = QWidget()
        severity_layout = QVBoxLayout(severity_widget)
        severity_layout.setContentsMargins(0, 0, 0, 0)
        severity_label = QLabel("شدت:")
        severity_label.setStyleSheet("font-weight: bold; color: #F4C542;")
        severity_layout.addWidget(severity_label)

        severity_row = QHBoxLayout()
        severity_row.setSpacing(5)

        self.severity_spin = QSpinBox()
        self.severity_spin.setRange(1, 5)
        self.severity_spin.setValue(DEFAULT_SEVERITY)
        self.severity_spin.setMinimumHeight(30)
        self.severity_spin.setStyleSheet("""
            QSpinBox {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 4px;
                padding: 4px;
                font-size: 13px;
                min-width: 60px;
            }
        """)
        # تنظیم Tooltip
        TooltipManager.set_field_tooltip(self.severity_spin, 'severity')
        severity_row.addWidget(self.severity_spin)

        self.severity_label = QLabel("⭐" * 3)
        self.severity_label.setStyleSheet("font-size: 14px; color: #F4D35E;")
        severity_row.addWidget(self.severity_label)

        severity_layout.addLayout(severity_row)
        type_severity_layout.addWidget(severity_widget)

        type_severity_layout.addStretch()
        layout.addLayout(type_severity_layout)

        # ===== دکمه‌ها =====
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.save_btn = QPushButton("💾 ذخیره مشاهده")
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
        self.save_btn.clicked.connect(self.save_observation)
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("انصراف")
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

        layout.addSpacing(5)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.severity_spin.valueChanged.connect(self.update_severity_display)

    def setup_tag_completer(self):
        """تنظیم تکمیل خودکار برای برچسب‌ها"""
        completer = QCompleter(SUGGESTED_TAGS)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.tags_input.setCompleter(completer)

    # بقیه متدها مانند نسخه قبلی
    def set_default_date(self):
        try:
            today = jdatetime.date.today()
            date_str = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
            self.date_input.set_date(date_str)
        except Exception as _exc:
            self.logger.debug(
                f"خطای غیرمنتظره در {self.__class__.__name__}: {_exc}"
            )

    def update_severity_display(self, value):
        self.severity_label.setText("⭐" * value)

    def toggle_more_fields(self):
        visible = self.more_widget.isVisible()
        self.more_widget.setVisible(not visible)
        self.show_more_btn.setText("🔼 مخفی کردن فیلدهای بیشتر" if not visible else "🔽 نمایش فیلدهای بیشتر (اختیاری)")

    def show_guide(self):
        from config.help_messages import OBSERVATION_GUIDE
        QMessageBox.information(
            self,
            "راهنمای ثبت مشاهده",
            OBSERVATION_GUIDE,
            QMessageBox.StandardButton.Ok
        )

    def load_students(self):
        try:
            students = self.student_dal.get_all()
            self.student_combo.clear()
            for student in students:
                self.student_combo.addItem(student.full_name, student.id)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری دانش‌آموزان:\n{e!s}")

    def load_staff(self):
        try:
            staff_list = self.staff_dal.get_all()
            self.observer_combo.clear()
            for staff in staff_list:
                self.observer_combo.addItem(staff.full_name, staff.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری مشاهده‌گرها: {e}")

    def on_competency_selected(self, selection):
        self.selected_competency_id = selection.get('competency_id')
        self.selected_indicator_id = selection.get('indicator_id')
        self.selected_behavior_id = selection.get('behavior_id')

        full_path = selection.get('full_path', '')
        if full_path and full_path != "ثبت نشده":
            self.selected_path_label.setText(f"✅ انتخاب‌شده: {full_path}")
            self.selected_path_label.setStyleSheet("""
                QLabel {
                    color: #111111;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #eafaf1;
                    border-radius: 4px;
                    border: 1px solid #a9dfbf;
                    font-weight: bold;
                }
            """)
        else:
            self.selected_path_label.setText("هیچ شایستگی‌ای انتخاب نشده است")
            self.selected_path_label.setStyleSheet("""
                QLabel {
                    color: #D9C36A;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #0B2E4F;
                    border-radius: 4px;
                    border: 1px solid #08223A;
                    font-weight: bold;
                }
            """)

    def clear_competency_selection(self):
        self.selected_competency_id = None
        self.selected_indicator_id = None
        self.selected_behavior_id = None
        self.selected_path_label.setText("هیچ شایستگی‌ای انتخاب نشده است")
        self.selected_path_label.setStyleSheet("""
            QLabel {
                color: #D9C36A;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #0B2E4F;
                border-radius: 4px;
                border: 1px solid #08223A;
                font-weight: bold;
            }
        """)
        self.competency_tree.clear_selection()
    
    def load_observation_data(self):
        """بارگذاری اطلاعات مشاهده برای ویرایش"""
        try:
            self.existing_observation = self.observation_service.get_observation(self.observation_id)
            if not self.existing_observation:
                QMessageBox.critical(self, "خطا", "مشاهده مورد نظر یافت نشد")
                self.reject()
                return
            
            obs = self.existing_observation
            
            # دانش‌آموز
            student_id = getattr(obs, 'student_id', None)
            if student_id:
                for i in range(self.student_combo.count()):
                    if self.student_combo.itemData(i) == student_id:
                        self.student_combo.setCurrentIndex(i)
                        break
            
            # مشاهده‌گر
            for i in range(self.observer_combo.count()):
                if self.observer_combo.itemData(i) == obs.staff_id:
                    self.observer_combo.setCurrentIndex(i)
                    break
            
            # تاریخ
            self.date_input.set_date(obs.observation_date or "")
            
            # محیط
            loc_index = self.location_combo.findText(obs.location or "")
            if loc_index >= 0:
                self.location_combo.setCurrentIndex(loc_index)
            
            # رفتار
            self.behavior_input.setText(obs.behavior or "")
            
            # زمینه و پیامد
            self.antecedent_input.setText(obs.antecedent or "")
            self.consequence_input.setText(obs.consequence or "")
            
            # نوع و شدت
            type_index = self.type_combo.findText(obs.behavior_type or "")
            if type_index >= 0:
                self.type_combo.setCurrentIndex(type_index)
            self.severity_spin.setValue(obs.severity or DEFAULT_SEVERITY)
            
            # برچسب‌ها و توضیحات
            self.tags_input.setText(obs.tags or "")
            self.description_input.setText(obs.description or "")
            
            # ===== بارگذاری شایستگی انتخاب‌شده =====
            if obs.competency_id or obs.indicator_id or obs.observable_behavior_id:
                # تنظیم انتخاب در درخت
                self.competency_tree.set_selection_by_ids(
                    competency_id=obs.competency_id,
                    indicator_id=obs.indicator_id,
                    behavior_id=obs.observable_behavior_id
                )
                
                # به‌روزرسانی لیبل مسیر
                path_parts = []
                if obs.competency_title:
                    path_parts.append(obs.competency_title)
                if obs.indicator_title:
                    path_parts.append(obs.indicator_title)
                if obs.observable_behavior_text:
                    path_parts.append(obs.observable_behavior_text)
                
                if path_parts:
                    full_path = " → ".join(path_parts)
                    self.selected_path_label.setText(f"✅ انتخاب‌شده: {full_path}")
                    self.selected_path_label.setStyleSheet("""
                        QLabel {
                            color: #111111;
                            font-size: 12px;
                            padding: 4px 8px;
                            background-color: #eafaf1;
                            border-radius: 4px;
                            border: 1px solid #a9dfbf;
                            font-weight: bold;
                        }
                    """)
                    
                    self.selected_competency_id = obs.competency_id
                    self.selected_indicator_id = obs.indicator_id
                    self.selected_behavior_id = obs.observable_behavior_id
                    self.selected_competency_name = obs.competency_title
                    self.selected_indicator_name = obs.indicator_title
                    self.selected_behavior_text = obs.observable_behavior_text
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری اطلاعات:\n{e!s}")
    
    def get_behavior_text(self):
        """دریافت متن رفتار با حذف فاصله‌های اضافی"""
        text = self.behavior_input.toPlainText().strip()
        return text
    
    @single_submit()
    def save_observation(self):
        """ذخیره مشاهده - با پشتیبانی از ساختار سه‌لایه"""
        
        # ===== اعتبارسنجی سریع =====
        student_index = self.student_combo.currentIndex()
        if student_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک دانش‌آموز انتخاب کنید")
            self.student_combo.setFocus()
            return
        
        behavior_text = self.get_behavior_text()
        if not behavior_text:
            QMessageBox.warning(self, "خطا", "لطفاً رفتار مشاهده‌شده را ثبت کنید")
            self.behavior_input.setFocus()
            return
        
        if len(behavior_text) < 3:
            QMessageBox.warning(self, "خطا", "توضیحات رفتار باید حداقل ۳ کاراکتر باشد")
            self.behavior_input.setFocus()
            return
        
        if len(behavior_text) > 500:
            QMessageBox.warning(self, "خطا", "توضیحات رفتار نباید بیشتر از ۵۰۰ کاراکتر باشد")
            self.behavior_input.setFocus()
            return
        
        observer_index = self.observer_combo.currentIndex()
        if observer_index < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک مشاهده‌گر انتخاب کنید")
            return
        
        if not self.date_input.is_valid():
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ را به صورت صحیح وارد کنید")
            self.date_input.setFocus()
            return
        
        # ===== ساخت داده‌ها =====
        data = {
            'student_id': self.student_combo.itemData(student_index),
            'staff_id': self.observer_combo.itemData(observer_index),
            'competency_id': self.selected_competency_id,
            'indicator_id': self.selected_indicator_id,
            'observable_behavior_id': self.selected_behavior_id,
            'observation_date': self.date_input.get_date_string(),
            'location': self.location_combo.currentText(),
            'behavior': behavior_text,
            'antecedent': self.antecedent_input.toPlainText().strip(),
            'consequence': self.consequence_input.toPlainText().strip(),
            'description': self.description_input.toPlainText().strip(),
            'behavior_type': self.type_combo.currentText(),
            'severity': self.severity_spin.value(),
            'tags': self.tags_input.text().strip()
        }
        
        # ===== ذخیره =====
        try:
            if self.is_edit_mode:
                self.observation_service.update_observation(self.observation_id, data)
                msg = "✅ مشاهده با موفقیت ویرایش شد"
            else:
                self.observation_service.create_observation(data)
                msg = "✅ مشاهده با موفقیت ثبت شد"
            
            QMessageBox.information(self, "موفقیت", msg)
            self.observation_saved.emit()
            self.accept()
            
        except ValidationError as e:
            QMessageBox.warning(self, "خطا در اعتبارسنجی", str(e))
        except ServiceError as e:
            QMessageBox.critical(self, "خطا", str(e))
        except Exception as e:
            self.logger.error(f"خطا در ذخیره مشاهده: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در ذخیره:\n{e!s}")
    
    def keyPressEvent(self, event):
        """مدیریت کلیدهای میانبر"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.save_observation()
        super().keyPressEvent(event)