"""
تنظیمات مرکزی پروژه - نسخه اصلاح شده
"""

import os
import sys

# مسیر ریشه پروژه
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# مسیر دیتابیس
DB_PATH = os.path.join(BASE_DIR, "database", "partow.db")
DB_VERSION = 7  # نسخه ۷: جدول‌های recommendations، saved_filters، backups
                # + ستون attachments.updated_at
                # + ستون‌های سه‌لایه روی observations
DB_VERSION_FILE = os.path.join(BASE_DIR, "database", "db_version.txt")

# مسیر فایل‌های استایل
STYLE_PATH = os.path.join(BASE_DIR, "assets", "styles", "main_style.qss")

# مسیر ذخیره پیوست‌ها
ATTACHMENTS_DIR = os.path.join(BASE_DIR, "attachments")

# ============================================================
# مسیر لوگو و آیکون
# ============================================================

# مسیر لوگوی اصلی (برای صفحه خوش‌آمدگویی و هدر)
LOGO_PATH = os.path.join(BASE_DIR, "assets", "images", "logo.png")

# مسیر آیکون برنامه (برای فایل اجرایی)
LOGO_ICON_PATH = os.path.join(BASE_DIR, "assets", "images", "logo.ico")

# اگر فایل ICO ندارید، از PNG استفاده کنید
if not os.path.exists(LOGO_ICON_PATH):
    LOGO_ICON_PATH = LOGO_PATH

# ============================================================
# تنظیمات برنامه و اطلاعات مالکیت
# ============================================================

APP_NAME = "PARTO"  # اصلاح: PARTOW -> PARTO
APP_FULL_NAME = "پرتو"
APP_VERSION = "27.2.3"
APP_AUTHOR = "سید محسن رسول زاده اصل بیرجند"
APP_EMAIL = "jaadougaroz1960@gmail.com"
APP_WEBSITE = "www.jaadougaroz1960.com"
APP_COPYRIGHT = """© این برنامه توسط جناب آقای سید محسن رسول زاده اصل بیرجند 
در سال 1405 طراحی و تولید شده و تمامی حق و حقوق این برنامه و ایده‌ها 
و طراحی برنامه تماماً و انحصاراً متعلق به صاحب برنامه 
که آقای سید محسن رسول زاده اصل بیرجند می‌باشد و در صورت هرگونه کپی‌برداری 
به هر شکل بدون اجازه کتبی و رسمی پیگرد قانونی در پی خواهد داشت"""

# ============================================================
# تنظیمات دیتابیس و نمایش
# ============================================================

DB_CONNECTION_TIMEOUT = 10
DATE_FORMAT = "%Y-%m-%d"
PERSIAN_DATE_FORMAT = "%Y/%m/%d"

# ===== وارد کردن تنظیمات از فایل constants =====
from config.constants import (
    STAFF_ROLES,
    OBSERVATION_LOCATIONS,
    OBSERVATION_TYPES,
    INTERVENTION_TYPES,
    FOLLOWUP_TYPES,
    GRADES,
    GRADE_NAMES,
    LIVING_STATUSES,
    COMPETENCY_CATEGORIES
)

# ===== نام‌های قدیمی برای سازگاری با کدهای موجود =====
OBSERVATION_ENVIRONMENTS = OBSERVATION_LOCATIONS