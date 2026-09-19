"""
PARTOW - ورودی اصلی برنامه - نسخه دیباگ
"""

import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from views.main_window import MainWindow
from database.connection import DatabaseConnection
from utils.logger import get_logger, log_error, log_info


def main():
    """نقطه ورود اصلی برنامه - نسخه دیباگ"""
    
    print("🔵 مرحله 1: شروع برنامه...")
    
    try:
        # تست دیتابیس
        print("🔵 مرحله 2: تست دیتابیس...")
        db = DatabaseConnection()
        conn = db.get_connection()
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
        try:
            from config.settings import LOGO_ICON_PATH
            if os.path.exists(LOGO_ICON_PATH):
                window.setWindowIcon(QIcon(LOGO_ICON_PATH))
        except Exception:
            pass
        
        print("🔵 مرحله 6: نمایش پنجره...")
        window.show()
        
        print("✅ برنامه با موفقیت اجرا شد.")
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        traceback.print_exc()
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("خطا")
        msg.setText(f"خطا در اجرای برنامه:\n{str(e)}")
        msg.exec()
        sys.exit(1)


if __name__ == "__main__":
    main()