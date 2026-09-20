"""
دیالوگ ورود به سیستم - نسخه با پشتیبانی از سیستم راهنما
"""

import os
import sys

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import APP_VERSION
from dal.user_dal import UserDAL
from database.connection import DatabaseConnection
from utils.logger import get_logger
from utils.tooltip_manager import TooltipManager

logger = get_logger(__name__)


class LoginDialog(QDialog):
    """دیالوگ ورود به سیستم با طراحی حرفه‌ای و پشتیبانی از راهنما"""

    login_successful = Signal(int, str, str)  # user_id, username, role
    need_change_password = Signal(int, str)   # user_id, username

    def __init__(self, parent=None):
        super().__init__(parent)

        self.db = DatabaseConnection()
        self.user_dal = UserDAL()
        self.logger = get_logger(self.__class__.__name__)
        self.current_user_id = None
        self.attempts = 0
        self.max_attempts = 5

        self.setWindowTitle("ورود به سامانه PARTO")
        self.setModal(True)
        self.setFixedSize(450, 550)

        self.setup_ui()
        self.setup_connections()

        self.username_input.setFocus()

    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(30, 25, 30, 25)
        self.setLayout(main_layout)

        # ===== لوگو و عنوان =====
        logo_layout = QVBoxLayout()
        logo_layout.setSpacing(5)

        title_label = QLabel("PARTO")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #F4C542;
                letter-spacing: 2px;
            }
        """)
        logo_layout.addWidget(title_label)

        subtitle_label = QLabel("سامانه پرونده ارزیابی و رشد توانمندی دانش‌آموز")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #D9C36A;
                font-weight: 500;
            }
        """)
        logo_layout.addWidget(subtitle_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #08223A; max-height: 1px; margin: 10px 0;")
        logo_layout.addWidget(separator)

        main_layout.addLayout(logo_layout)

        # ===== فرم ورود =====
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # نام کاربری
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("نام کاربری خود را وارد کنید")
        self.username_input.setMinimumHeight(38)
        self.username_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F; border: 2px solid #F4C542; }
        """)
        # تنظیم Tooltip
        TooltipManager.set_tooltip(self.username_input, "نام کاربری خود را وارد کنید. (مثال: admin)")
        form_layout.addRow("نام کاربری:", self.username_input)

        # رمز عبور
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("رمز عبور خود را وارد کنید")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(38)
        self.password_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F; border: 2px solid #F4C542; }
        """)
        # تنظیم Tooltip
        TooltipManager.set_tooltip(self.password_input, "رمز عبور خود را وارد کنید.")
        form_layout.addRow("رمز عبور:", self.password_input)

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

        # ===== دکمه ورود =====
        self.login_btn = QPushButton("ورود به سامانه")
        self.login_btn.setMinimumHeight(45)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover { background-color: #08223A; }
            QPushButton:disabled { background-color: #D9C36A; }
        """)
        self.login_btn.clicked.connect(self.login)
        main_layout.addWidget(self.login_btn)

        # ===== پیام خطا =====
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #C62828;
                font-size: 13px;
                font-weight: bold;
                padding: 5px;
                min-height: 25px;
            }
        """)
        main_layout.addWidget(self.error_label)

        # ===== دکمه‌های پایین =====
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(15)

        # دکمه تغییر رمز
        self.change_pass_btn = QPushButton("تغییر رمز عبور")
        self.change_pass_btn.setStyleSheet("""
            QPushButton {
                background-color: #F4D35E;
                color: #F4C542;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #F28C28; }
        """)
        self.change_pass_btn.clicked.connect(self.open_change_password)
        bottom_layout.addWidget(self.change_pass_btn)

        bottom_layout.addStretch()

        # دکمه خروج
        self.exit_btn = QPushButton("خروج")
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #9E1B1B; }
        """)
        self.exit_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.exit_btn)

        main_layout.addLayout(bottom_layout)

        # ===== نسخه برنامه =====
        # نسخه از یک منبع واحد خوانده می‌شود (config/settings.py)
        version_label = QLabel(f"نسخه {APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #D9C36A;
                margin-top: 8px;
            }
        """)
        main_layout.addWidget(version_label)

        # استایل کلی
        self.setStyleSheet("""
            QDialog {
                background-color: #0B2E4F;
                border-radius: 10px;
            }
            QFormLayout QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #F4C542;
            }
        """)

    def setup_connections(self):
        self.username_input.returnPressed.connect(self.login)
        self.password_input.returnPressed.connect(self.login)

    def toggle_password_visibility(self, checked):
        if checked:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def login(self):
        """ورود به سیستم"""
        logger.debug("🔵 تابع login اجرا شد")
        
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        # اعتبارسنجی ورودی
        if not username:
            self.show_error("لطفاً نام کاربری را وارد کنید.")
            self.username_input.setFocus()
            return
        
        if not password:
            self.show_error("لطفاً رمز عبور را وارد کنید.")
            self.password_input.setFocus()
            return
        
        # بررسی تعداد تلاش‌های ناموفق
        if self.attempts >= self.max_attempts:
            self.show_error(f"تعداد تلاش‌های ناموفق به {self.max_attempts} رسیده است.\nلطفاً برنامه را مجدداً اجرا کنید.")
            self.login_btn.setEnabled(False)
            return
        
        # غیرفعال کردن دکمه ورود
        self.login_btn.setEnabled(False)
        self.login_btn.setText("در حال بررسی...")
        
        try:
            # بررسی اعتبار کاربر
            user = self.authenticate_user(username, password)
            
            if user:
                logger.debug(f"✅ کاربر {username} احراز هویت شد")
                self.attempts = 0
                self.login_btn.setEnabled(True)
                self.login_btn.setText("ورود به سامانه")
                
                # ===== اصلاح: پنج مقدار، هر کدام برای کار خودش =====
                # staff_id → Audit Log و set_current_user
                # db_user_id → UPDATE روی جدول users
                # full_name عمداً استفاده نمی‌شود؛ نام نمایشی از خودِ
                # رکورد کادر (پنجرهٔ اصلی) خوانده می‌شود.
                staff_id, user_role, _full_name, must_change_password, db_user_id = user
                user_id = staff_id
                self.current_user_id = user_id

                # به‌روزرسانی زمان آخرین ورود (روی جدول users)
                self.update_last_login(db_user_id)

                # ثبت در Audit Log (نیاز به staff.id دارد)
                self.log_login_success(staff_id, username)
                
                # بررسی是否需要 تغییر رمز
                if must_change_password:
                    logger.debug(f"🔑 کاربر {username} باید رمز عبور خود را تغییر دهد")
                    # ارسال سیگنال برای تغییر رمز
                    self.need_change_password.emit(user_id, username)
                    # بستن دیالوگ
                    self.accept()
                    return
                
                # ارسال سیگنال
                logger.debug(f"🔵 ارسال سیگنال login_successful: {user_id}, {username}, {user_role}")
                self.login_successful.emit(user_id, username, user_role)
                
                # بستن دیالوگ
                logger.debug("🔵 بستن دیالوگ لاگین")
                self.accept()
            else:
                self.attempts += 1
                remaining = self.max_attempts - self.attempts
                if remaining > 0:
                    self.show_error(f"❌ نام کاربری یا رمز عبور اشتباه است.\nتعداد تلاش باقیمانده: {remaining}")
                else:
                    self.show_error("❌ تعداد تلاش‌های ناموفق به حد مجاز رسید.\nلطفاً برنامه را مجدداً اجرا کنید.")
                    self.login_btn.setEnabled(False)
                
                # ثبت ورود ناموفق
                self.log_login_failed(username)
                
                self.password_input.clear()
                self.password_input.setFocus()
                self.login_btn.setEnabled(True)
                self.login_btn.setText("ورود به سامانه")
                
        except Exception as e:
            logger.error(f"❌ خطا در ورود: {e}")
            import traceback
            traceback.print_exc()
            self.show_error("❌ خطا در ارتباط با دیتابیس.\nلطفاً مجدداً تلاش کنید.")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("ورود به سامانه")
    
    def authenticate_user(self, username, password):
        """
        احراز هویت کاربر

        ===== اصلاح (بازرسی هفتم — اولویت ۱) =====
        این متد قبلاً SQL خام جدول users را مستقیم در لایهٔ نمایش
        می‌زد. جدول `dal/user_dal.py::authenticate` از قبل وجود داشت
        (با همان ترتیب خروجی و همان منطق: بررسی is_active کاربر،
        فعال‌بودن عضو کادر، عدم حذف منطقی و احراز رمز)، اما کسی از
        آن استفاده نمی‌کرد. حالا فقط لایهٔ داده به این جدول دست
        می‌زند.

        خروجی این متد تغییر نکرده (۵ عنصر با همان ترتیب) تا کد
        فراخوان (btn_login / main_window) دست‌نخورده بماند.
        """
        try:
            logger.debug(f"🔵 احراز هویت کاربر: {username}")
            auth = self.user_dal.authenticate(username, password)

            if not auth:
                logger.debug(f"❌ احراز هویت {username} ناموفق بود")
                return None

            logger.debug(f"✅ احراز هویت {auth['username']} موفق بود")
            return (
                auth['staff_id'],                  # staff_id ← برای set_current_user و Audit
                auth['role'],                      # user_role
                auth['full_name'],                 # full_name
                auth['must_change_password'],      # must_change_password
                auth['user_id'],                   # users.id ← فقط برای UPDATE users
            )

        except Exception as e:
            logger.error(f"❌ خطا در احراز هویت: {e}")
            import traceback
            traceback.print_exc()
            return None

    def update_last_login(self, user_id):
        """
        به‌روزرسانی زمان آخرین ورود

        ===== اصلاح (بازرسی هفتم) =====
        SQL خام به UserDAL.update_last_login منتقل شد. امضای
        `update_last_login(self, user_id)` در DAL دقیقاً همین است.
        """
        try:
            self.user_dal.update_last_login(user_id)
            logger.debug(f"✅ زمان آخرین ورود برای کاربر {user_id} به‌روزرسانی شد")
        except Exception as e:
            logger.error(f"❌ خطا در به‌روزرسانی آخرین ورود: {e}")
    
    def log_login_success(self, user_id, username):
        """ثبت ورود موفق در Audit Log"""
        try:
            from utils.security import AuditLogger
            audit = AuditLogger(self.db)
            audit.log_login(user_id, success=True)
            self.logger.info(f"✅ ورود موفق: {username} (ID: {user_id})")
            logger.debug(f"✅ Audit Log: ورود موفق {username}")
        except Exception as e:
            logger.error(f"❌ خطا در ثبت Audit Log: {e}")
    
    def log_login_failed(self, username):
        """ثبت ورود ناموفق در Audit Log"""
        try:
            from utils.security import AuditLogger
            audit = AuditLogger(self.db)
            audit.log_login(None, success=False)
            self.logger.warning(f"⚠️ ورود ناموفق: {username}")
            logger.warning(f"⚠️ Audit Log: ورود ناموفق {username}")
        except Exception as e:
            logger.error(f"❌ خطا در ثبت Audit Log: {e}")
    
    def show_error(self, message):
        self.error_label.setText(message)
        QTimer.singleShot(5000, lambda: self.error_label.setText(""))

    def open_change_password(self):
        from views.dialogs.change_password_dialog import ChangePasswordDialog

        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا نام کاربری خود را وارد کنید.")
            return

        dialog = ChangePasswordDialog(username, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "موفقیت", "رمز عبور با موفقیت تغییر یافت.\nلطفاً با رمز جدید وارد شوید.")
            self.password_input.clear()
            self.password_input.setFocus()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        super().keyPressEvent(event)