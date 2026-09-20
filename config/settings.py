"""
تنظیمات مرکزی پروژه - نسخه اصلاح شده
"""

import os

# مسیر ریشه پروژه
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# مسیر دیتابیس
DB_PATH = os.path.join(BASE_DIR, "database", "partow.db")
DB_VERSION = 9  # نسخه ۹: یکدست‌سازی تاریخ‌های شمسی موجود (بازرسی نهم)
                # نسخه ۸: ایندکس‌گذاری ۳۵ ستون کلید خارجی (بازرسی هشتم)
                # نسخه ۷: جدول‌های recommendations، saved_filters، backups
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
APP_VERSION = "27.2.4"
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
#
# ===== نکته مهم (بازرسی هشتم) =====
# این بلوک «Re-export» است: هیچ‌کدام از این نام‌ها داخل همین فایل
# استفاده نمی‌شوند، ولی ۲۰+ ماژول دیگر (مثلاً views/main_window.py و
# views/pages/students_page.py) آن‌ها را این‌طور وارد می‌کنند:
#       from config.settings import GRADES, STAFF_ROLES
# پس حذف‌شدنشان به‌عنوان «import بی‌استفاده» برنامه را می‌شکند.
# پاک‌سازی خودکار ruff دقیقاً همین کار را کرد و سه فایل را شکست؛
# به‌همین‌دلیل نام‌ها با شکل صریح «X as X» نوشته می‌شوند که هم برای
# انسان و هم برای lint روشن است: «این‌ها عمداً صادر می‌شوند».
from config.constants import (
    COMPETENCY_CATEGORIES as COMPETENCY_CATEGORIES,
)
from config.constants import (
    FOLLOWUP_TYPES as FOLLOWUP_TYPES,
)
from config.constants import (
    GRADE_NAMES as GRADE_NAMES,
)
from config.constants import (
    GRADES as GRADES,
)
from config.constants import (
    INTERVENTION_TYPES as INTERVENTION_TYPES,
)
from config.constants import (
    LIVING_STATUSES as LIVING_STATUSES,
)
from config.constants import (
    OBSERVATION_LOCATIONS as OBSERVATION_LOCATIONS,
)
from config.constants import (
    OBSERVATION_TYPES as OBSERVATION_TYPES,
)
from config.constants import (
    STAFF_ROLES as STAFF_ROLES,
)

# ===== نام‌های قدیمی برای سازگاری با کدهای موجود =====
OBSERVATION_ENVIRONMENTS = OBSERVATION_LOCATIONS