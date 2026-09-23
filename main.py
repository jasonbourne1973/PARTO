"""
PARTOW - ورودی اصلی برنامه - نسخه دیباگ
"""

import contextlib
import os
import sys
import traceback

# نسخهٔ پشتیبانی‌شدهٔ پایتون (بازرسی شانزدهم): حداقل ۳.۹ — پیش از import
# کتابخانه‌ها بررسی می‌شود تا به‌جای SyntaxError/ImportError مبهم، پیام روشن
# داده شود. (README: بخش پیش‌نیازها)
MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    sys.stderr.write(
        f"PARTO به Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} یا بالاتر نیاز دارد؛ "
        f"نسخهٔ فعلی: {sys.version.split()[0]}\n")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from database.connection import DatabaseConnection
from views.main_window import MainWindow


def main():
    """نقطه ورود اصلی برنامه - نسخه دیباگ"""
    
    print("🔵 مرحله 1: شروع برنامه...")
    
    try:
        # تست دیتابیس
        print("🔵 مرحله 2: تست دیتابیس...")
        db = DatabaseConnection()
        db.get_connection()  # فقط برای اطمینان از برقراری اتصال
        print("✅ دیتابیس متصل شد.")
        
        # ایجاد اپلیکیشن
        print("🔵 مرحله 3: ایجاد اپلیکیشن...")
        app = QApplication(sys.argv)
        app.setApplicationName("PARTOW")
        
        # ===== تنظیم آیکون برنامه =====
        try:
            from config.settings import LOGO_ICON_PATH, LOGO_PATH
            icon_path = LOGO_ICON_PATH if os.path.exists(LOGO_ICON_PATH) else LOGO_PATH
            if os.path.exists(icon_path):
                app.setWindowIcon(QIcon(icon_path))
                print(f"✅ آیکون برنامه از {icon_path} بارگذاری شد")
            else:
                print("⚠️ فایل آیکون پیدا نشد")
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری آیکون: {e}")
        
        # ایجاد پنجره اصلی
        print("🔵 مرحله 4: ایجاد پنجره اصلی...")
        window = MainWindow()
        
        # بررسی وضعیت لاگین
        print(f"🔵 مرحله 5: وضعیت لاگین = {window.is_logged_in}")
        
        if not window.is_logged_in:
            print("❌ لاگین ناموفق بود، برنامه بسته می‌شود.")
            sys.exit(0)
        
        # ===== تنظیم آیکون پنجره اصلی =====
        # نبود/خرابی فایل آیکون نباید بالا آمدن برنامه را متوقف کند
        with contextlib.suppress(Exception):
            from config.settings import LOGO_ICON_PATH
            if os.path.exists(LOGO_ICON_PATH):
                window.setWindowIcon(QIcon(LOGO_ICON_PATH))
        
        print("🔵 مرحله 6: نمایش پنجره...")
        window.show()
        
        print("✅ برنامه با موفقیت اجرا شد.")
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        traceback.print_exc()

        # (بازرسی شانزدهم) خطای راه‌اندازی باید در لاگ برنامه هم بماند
        # (مثلاً شکست Migration)، نه فقط در کنسولی که در اجرای پنجره‌ای
        # دیده نمی‌شود. شکستِ خودِ لاگ‌گیری نباید پیام اصلی را پنهان کند.
        with contextlib.suppress(Exception):
            from utils.logger import get_logger
            get_logger('main').error(f"خطا در راه‌اندازی برنامه: {e}", exc_info=True)

        # اگر خطا پیش از ساخت QApplication رخ داده باشد (مثل شکست اتصال/
        # Migration دیتابیس در مرحلهٔ ۲)، ساختن QMessageBox بدون
        # QApplication خودِ برنامه را با
        # «QWidget: Must construct a QApplication before a QWidget» می‌کُشت و
        # کاربر هیچ پیامی نمی‌دید.
        if QApplication.instance() is None:
            QApplication(sys.argv)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("خطا")
        msg.setText(f"خطا در اجرای برنامه:\n{e!s}")
        msg.exec()
        sys.exit(1)


if __name__ == "__main__":
    main()