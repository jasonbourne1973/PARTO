"""
دیالوگ تغییر رمز عبور - نسخه با پشتیبانی از راهنما
"""

import os
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dal.user_dal import UserDAL
from database.connection import DatabaseConnection
from utils.logger import get_logger
from utils.security import Security
from utils.tooltip_manager import TooltipManager


class ChangePasswordDialog(QDialog):
    """دیالوگ تغییر رمز عبور با پشتیبانی از راهنما"""

    password_changed = Signal()

    def __init__(self, username=None, parent=None, user_id=None, is_first_login=False):
        super().__init__(parent)

        self.username = username
        self.user_id = user_id
        self.is_first_login = is_first_login
        self.db = DatabaseConnection()
        self.user_dal = UserDAL()
        self.logger = get_logger(self.__class__.__name__)

        if is_first_login:
            self.setWindowTitle("تغییر رمز عبور (ورود اولیه)")
        else:
            self.setWindowTitle("تغییر رمز عبور")

        self.setModal(True)
        self.setFixedSize(420, 400)

        self.setup_ui()
        self.setup_connections()

        if username:
            self.username_input.setText(username)
            self.username_input.setReadOnly(True)

        if is_first_login:
            self.current_password_label.hide()
            self.current_password_input.hide()
            self.setFixedSize(420, 340)

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(25, 20, 25, 20)
        self.setLayout(main_layout)

        # ===== عنوان =====
        if self.is_first_login:
            title_text = "تغییر رمز عبور (ورود اولیه)"
            subtitle_text = "برای اولین بار وارد سیستم شده‌اید. لطفاً رمز عبور خود را تغییر دهید."
        else:
            title_text = "تغییر رمز عبور"
            subtitle_text = "رمز عبور خود را با دقت وارد کنید."

        title_label = QLabel(title_text)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #F4C542;
                padding: 10px 0;
            }
        """)
        main_layout.addWidget(title_label)

        subtitle_label = QLabel(subtitle_text)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #D9C36A;
                padding: 0 0 10px 0;
            }
        """)
        main_layout.addWidget(subtitle_label)

        # ===== فرم =====
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("نام کاربری")
        self.username_input.setMinimumHeight(36)
        self.username_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F; border: 2px solid #F4C542; }
        """)
        form_layout.addRow("نام کاربری:", self.username_input)

        self.current_password_label = QLabel("رمز فعلی:")
        self.current_password_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #F4C542;")

        self.current_password_input = QLineEdit()
        self.current_password_input.setPlaceholderText("رمز عبور فعلی را وارد کنید")
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_password_input.setMinimumHeight(36)
        self.current_password_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F; border: 2px solid #F4C542; }
        """)
        TooltipManager.set_tooltip(self.current_password_input, "رمز عبور فعلی خود را وارد کنید.")
        form_layout.addRow(self.current_password_label, self.current_password_input)

        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("رمز عبور جدید (حداقل ۸ کاراکتر)")
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setMinimumHeight(36)
        self.new_password_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F; border: 2px solid #F4C542; }
        """)
        TooltipManager.set_tooltip(self.new_password_input, "رمز عبور جدید باید حداقل ۸ کاراکتر باشد و شامل حروف بزرگ، کوچک، اعداد و یک نویسهٔ خاص (!@#$%^&*) باشد.")
        form_layout.addRow("رمز جدید:", self.new_password_input)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("رمز عبور جدید را دوباره وارد کنید")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setMinimumHeight(36)
        self.confirm_password_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F; border: 2px solid #F4C542; }
        """)
        TooltipManager.set_tooltip(self.confirm_password_input, "رمز عبور جدید را دوباره وارد کنید تا مطابقت آن تأیید شود.")
        form_layout.addRow("تکرار رمز جدید:", self.confirm_password_input)

        main_layout.addLayout(form_layout)

        # ===== نمایش رمز عبور =====
        show_pass_layout = QHBoxLayout()
        show_pass_layout.addStretch()

        self.show_password_check = QCheckBox("نمایش رمز عبور")
        self.show_password_check.setStyleSheet("""
            QCheckBox {
                font-size: 12px;
                color: #D9C36A;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        self.show_password_check.toggled.connect(self.toggle_password_visibility)
        show_pass_layout.addWidget(self.show_password_check)

        main_layout.addLayout(show_pass_layout)

        # ===== دکمه‌ها =====
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        save_text = "تغییر رمز و ورود" if self.is_first_login else "تغییر رمز عبور"

        self.save_btn = QPushButton(save_text)
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.save_btn.clicked.connect(self.change_password)
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("انصراف")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #D94B4B; }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(button_layout)

        # ===== پیام خطا =====
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #C62828;
                font-size: 12px;
                min-height: 20px;
            }
        """)
        main_layout.addWidget(self.error_label)

    def setup_connections(self):
        if not self.is_first_login:
            self.current_password_input.returnPressed.connect(self.change_password)
        self.new_password_input.returnPressed.connect(self.change_password)
        self.confirm_password_input.returnPressed.connect(self.change_password)

    def toggle_password_visibility(self, checked):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        if not self.is_first_login:
            self.current_password_input.setEchoMode(mode)
        self.new_password_input.setEchoMode(mode)
        self.confirm_password_input.setEchoMode(mode)
    
    def change_password(self):
        """تغییر رمز عبور"""
        username = self.username_input.text().strip()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        # اعتبارسنجی
        if not username:
            self.show_error("❌ نام کاربری نمی‌تواند خالی باشد.")
            return
        
        if not self.is_first_login:
            current_password = self.current_password_input.text()
            if not current_password:
                self.show_error("❌ لطفاً رمز عبور فعلی را وارد کنید.")
                self.current_password_input.setFocus()
                return
        
        if not new_password:
            self.show_error("❌ لطفاً رمز عبور جدید را وارد کنید.")
            self.new_password_input.setFocus()
            return
        
        # ===== اصلاح =====
        # عدد ۶ اینجا هاردکد بود، در حالی که Security.is_password_strong
        # حداقل ۶ و جاهای دیگر ۸ می‌خواستند. حالا همه از یک ثابت
        # مشترک (Security.MIN_PASSWORD_LENGTH = 8) می‌آیند.
        if len(new_password) < Security.MIN_PASSWORD_LENGTH:
            self.show_error(
                f"❌ رمز عبور جدید باید حداقل "
                f"{Security.MIN_PASSWORD_LENGTH} کاراکتر باشد."
            )
            self.new_password_input.setFocus()
            return
        
        if new_password != confirm_password:
            self.show_error("❌ رمز عبور جدید و تکرار آن مطابقت ندارند.")
            self.confirm_password_input.setFocus()
            return
        
        # بررسی قدرت رمز عبور
        # ===== اصلاح امنیتی =====
        # نسخه قبلی یک پرسش Yes/No می‌گرفت: «آیا با این رمز عبور
        # ادامه می‌دهید؟». یعنی کل سیاست رمز قوی با یک کلیک روی
        # «بله» دور زده می‌شد. برای سامانه‌ای که اطلاعات کودکان را
        # نگه می‌دارد این پذیرفتنی نیست.
        # حالا رمز ضعیف رد می‌شود و دلیلش به کاربر گفته می‌شود.
        strong, msg = Security.is_password_strong(new_password)
        if not strong:
            QMessageBox.warning(
                self,
                "رمز عبور ضعیف",
                f"{msg}\n\nلطفاً رمز قوی‌تری انتخاب کنید."
            )
            self.new_password_input.clear()
            self.confirm_password_input.clear()
            self.new_password_input.setFocus()
            return
        
        try:
            # ===== اصلاح (بازرسی هفتم — اولویت ۱) =====
            # نسخه قبلی سه کوئری خام روی جدول users می‌زد (خواندن
            # کاربر، بررسی رمز، نوشتن رمز جدید) — در حالی که
            # `UserDAL.get_password_hash` و `UserDAL.update_password`
            # از قبل وجود داشتند و حتی نسخهٔ DAL سخت‌گیرتر است:
            # تغییر رمز را روی کاربران حذف‌شده/غیرفعال انجام نمی‌دهد
            # و ردیف Audit هم می‌نویسد.
            #
            # نکتهٔ مهمی که باید حفظ شود: users.id هرگز با staff.id
            # قاطی نشود. main_window مقدار `user_id` را از LoginDialog
            # می‌گیرد که staff.id است؛ پس users.id همیشه از روی
            # username (که یکتاست) استخراج می‌شود — همان کاری که
            # `UserDAL.get_by_username` انجام می‌دهد.
            user = self.user_dal.get_by_username(username)
            if not user or user.is_deleted or not user.is_active:
                self.show_error("❌ کاربر مورد نظر یافت نشد.")
                return

            user_id = user.id              # users.id → برای UPDATE
            staff_id = user.staff_id       # staff.id → برای Audit Log

            # بررسی رمز فعلی (اگر ورود اولیه نباشد)
            if not self.is_first_login:
                current_password = self.current_password_input.text()
                current_password_hash = self.user_dal.get_password_hash(user_id=user_id)
                if not Security.verify_password(current_password, current_password_hash):
                    self.show_error("❌ رمز عبور فعلی اشتباه است.")
                    self.current_password_input.clear()
                    self.current_password_input.setFocus()
                    return

            # هش‌کردن و ذخیره (DAL خودش هش می‌کند، می‌کند و
            # must_change_password را پاک می‌کند)
            self.user_dal.update_password(
                user_id,
                new_password,
                clear_must_change=True,
                user_id_actor=staff_id,
            )

            self.logger.info(f"✅ رمز عبور کاربر {username} با موفقیت تغییر کرد.")

            self.password_changed.emit()
            self.accept()

        except Exception as e:
            self.logger.error(f"خطا در تغییر رمز عبور: {e}")
            self.show_error(f"❌ خطا در تغییر رمز عبور:\n{e!s}")
    
    def show_error(self, message):
        """نمایش پیام خطا"""
        self.error_label.setText(message)
    
    def keyPressEvent(self, event):
        """مدیریت کلیدهای صفحه‌کلید"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        super().keyPressEvent(event)