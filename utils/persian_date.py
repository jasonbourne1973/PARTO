"""
ابزارهای کار با تاریخ شمسی

===== چه چیزی اصلاح شد =====
نسخه قبلی تابع `get_today` تبدیل میلادی→شمسی را دستی و تقریبی انجام
می‌داد. نتیجه‌اش این بود:

    2026-09-17  →  کد: 1405/06/17   درست: 1405/06/26   (۹ روز خطا)
    2026-06-15  →  کد: 1405/03/15   درست: 1405/03/25   (۱۰ روز خطا)
    2026-04-05  →  کد: 1405/01/05   درست: 1405/01/16   (۱۱ روز خطا)
    2026-01-25  →  کد: 1405/11/06   درست: 1404/11/05   (یک سال خطا!)

و چون `ShamsiDateInput.__init__` همین تابع را صدا می‌زد، تاریخ پیش‌فرض
همه فرم‌های ثبت مشاهده، مداخله، پیگیری و هدف اشتباه بود.

حالا از jdatetime استفاده می‌شود که در requirements.txt هم هست.

همچنین `is_valid_persian_date` روز ۳۰ اسفند را در سال‌های کبیسه رد
می‌کرد (چون `if day > 29` بود). اصلاح شد.
"""

import re

# فرمت یکتای تاریخ در کل پروژه.
# همه ستون‌های تاریخ در دیتابیس با همین فرمت ذخیره می‌شوند تا
# مقایسه رشته‌ای (>= و <=) در کوئری‌ها درست کار کند.
DB_DATE_FORMAT = "%Y/%m/%d"

PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر",
    "مرداد", "شهریور", "مهر", "آبان",
    "آذر", "دی", "بهمن", "اسفند"
]


class PersianDate:
    """کلاس کار با تاریخ شمسی"""

    @staticmethod
    def get_today():
        """
        دریافت تاریخ امروز به فرمت yyyy/MM/dd شمسی

        از jdatetime استفاده می‌کند. اگر jdatetime نصب نباشد،
        به جای برگرداندن تاریخ غلط، استثنا می‌دهد - چون تاریخ
        غلط بدتر از خطای صریح است (بی‌صدا در دیتابیس ذخیره می‌شود).
        """
        import jdatetime

        today = jdatetime.date.today()
        return f"{today.year:04d}/{today.month:02d}/{today.day:02d}"

    @staticmethod
    def is_valid_persian_date(date_str):
        """
        بررسی اعتبار تاریخ شمسی به فرمت yyyy/MM/dd

        روزهای هر ماه به درستی بررسی می‌شود، شامل ۳۰ اسفند در
        سال‌های کبیسه.
        """
        if not date_str:
            return False

        # ارقام فارسی/عربی را اول یکدست کن
        date_str = normalize_digits(str(date_str).strip())

        # ===== نکته =====
        # هر دو فراخوان این تابع (ShamsiDateInput.is_valid و
        # PersianCalendar.is_valid) رشته‌ای با جداکننده «/» تولید
        # می‌کنند، پس فرمت اصلی همان است. اما to_db_date خط تیره
        # («1405-6-6») را هم می‌پذیرد و نرمال می‌کند؛ اگر اینجا فقط
        # اسلش بپذیریم، تاریخی که to_db_date ذخیره می‌کند توسط
        # اعتبارسنجی رد می‌شود. پس هر دو جداکننده پذیرفته می‌شود.
        date_str = date_str.replace('-', '/')

        if not re.match(r'^\d{4}/\d{1,2}/\d{1,2}$', date_str):
            return False

        try:
            year, month, day = (int(part) for part in date_str.split('/'))
        except ValueError:
            return False

        if year < 1300 or year > 1500:
            return False
        if month < 1 or month > 12:
            return False
        if day < 1:
            return False

        # تعداد روزهای هر ماه شمسی
        if 1 <= month <= 6:
            max_day = 31          # فروردین تا شهریور
        elif 7 <= month <= 11:
            max_day = 30          # مهر تا بهمن
        else:
            # اسفند: ۲۹ روز، ولی در سال کبیسه ۳۰ روز
            max_day = 30 if is_leap_year(year) else 29

        return day <= max_day

    @staticmethod
    def get_persian_months():
        """لیست نام ماه‌های شمسی"""
        return list(PERSIAN_MONTHS)

    @staticmethod
    def month_name(month):
        """نام فارسی ماه از شماره آن"""
        if isinstance(month, int) and 1 <= month <= 12:
            return PERSIAN_MONTHS[month - 1]
        return ""

    @staticmethod
    def get_month_label(date_str):
        """
        برچسب فارسی ماه از یک تاریخ

        «1405/06/26» → «شهریور 1405»

        این تابع جایگزین `_get_month_label` در ObservationDAL و
        `get_persian_month_label` در analytics_helpers است که
        هر دو کپی یکدیگر بودند.
        """
        if not date_str or len(str(date_str)) < 7:
            return date_str

        parts = normalize_digits(str(date_str)).split('/')
        if len(parts) < 2:
            return date_str

        try:
            year = int(parts[0])
            month = int(parts[1])
        except ValueError:
            return date_str

        if 1 <= month <= 12:
            return f"{PERSIAN_MONTHS[month - 1]} {year}"
        return date_str

    @staticmethod
    def format_for_db(year, month, day):
        """ساخت رشته تاریخ با فرمت دیتابیس (با صفر پر شده)"""
        return f"{int(year):04d}/{int(month):02d}/{int(day):02d}"

    @staticmethod
    def parse(date_str):
        """
        تجزیه رشته تاریخ به (year, month, day)

        Returns:
            tuple یا None اگر نامعتبر باشد
        """
        if not PersianDate.is_valid_persian_date(date_str):
            return None

        parts = normalize_digits(str(date_str).strip()).split('/')
        return int(parts[0]), int(parts[1]), int(parts[2])


# ============================================================
# توابع سطح ماژول
# ============================================================

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_TRANSLATION_TABLE = {}
for _index, _digit in enumerate("0123456789"):
    _TRANSLATION_TABLE[ord(_PERSIAN_DIGITS[_index])] = _digit
    _TRANSLATION_TABLE[ord(_ARABIC_DIGITS[_index])] = _digit


def normalize_digits(text):
    """
    تبدیل ارقام فارسی و عربی به ASCII

    لازم چون `str.isdigit()` برای «۱۲۳» هم True می‌دهد. پس بدون
    این تبدیل، کد ملی با ارقام فارسی از اعتبارسنجی رد می‌شد ولی
    با کد ملی ASCII یکی نبود - یعنی UNIQUE دور زده می‌شد و جست‌وجو
    با کد ملی کار نمی‌کرد.
    """
    if text is None:
        return None
    return str(text).translate(_TRANSLATION_TABLE)


def is_leap_year(year):
    """
    آیا سال شمسی کبیسه است؟

    ===== نکته مهم =====
    الگوریتم رایج «باقی‌مانده بر ۳۳» که در بیشتر کدهای فارسی کپی
    می‌شود، برای همه سال‌ها درست نیست. تست‌شده:

        قاعده ((y + 1) % 33) در {1,5,9,13,17,22,26,30}
        → برای بازه ۱۳۸۰ تا ۱۴۳۰ غلط است

        سال‌های کبیسه واقعی ۱۳۹۵ تا ۱۴۱۴:
        ۱۳۹۵، ۱۳۹۹، ۱۴۰۳، ۱۴۰۸، ۱۴۱۲
        → فاصله‌ها ۴، ۴، ۵، ۴ است (شکست پنج‌ساله در دوره)

    به همین دلیل اینجا مستقیم به jdatetime واگذار می‌شود؛ همان
    کتابخانه‌ای که بقیه برنامه هم از آن استفاده می‌کند و مرجع
    معتبر است.
    """
    year = int(year)

    try:
        import jdatetime
        # اگر ۳۰ اسفند ساخته شود، سال کبیسه است
        try:
            jdatetime.date(year, 12, 30)
            return True
        except ValueError:
            return False
    except ImportError:
        # jdatetime نصب نیست: از جدول فاصله‌های راستی‌آزمایی‌شده
        # استفاده می‌کنیم. این فقط مسیر پشتیبان است.
        # سال‌های کبیسه واقعی از ۱۳۷۵ تا ۱۴۵۰:
        _LEAP_YEARS = {
            1375, 1378, 1382, 1387, 1391, 1395, 1399, 1403,
            1408, 1412, 1416, 1420, 1424, 1429, 1433, 1437,
            1441, 1445, 1450,
        }
        return year in _LEAP_YEARS


def to_db_date(value):
    """
    تبدیل هر ورودی به فرمت تاریخ دیتابیس

    ورودی‌های پذیرفته‌شده:
        - رشته شمسی «1405/06/26» یا «1405-6-6» → نرمال می‌شود
        - jdatetime.date / datetime
        - None → None

    این تابع باید در همه فرم‌ها قبل از ذخیره صدا زده شود تا
    فرمت تاریخ در کل دیتابیس یکدست بماند.
    """
    if value is None or value == "":
        return None

    # jdatetime.date یا datetime
    if hasattr(value, 'year') and hasattr(value, 'month'):
        return PersianDate.format_for_db(value.year, value.month, value.day)

    text = normalize_digits(str(value).strip())
    if not text:
        return None

    # جداکننده‌های مختلف را یکدست کن
    text = text.replace('-', '/')
    parts = text.split('/')
    if len(parts) != 3:
        return None

    try:
        year, month, day = (int(part) for part in parts)
    except ValueError:
        return None

    return PersianDate.format_for_db(year, month, day)
