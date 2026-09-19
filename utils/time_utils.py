"""
ابزارهای زمان — تنها مرجع نوشتن مهر زمانی در دیتابیس

===== سیاست زمانی این پروژه (بازرسی هشتم) =====
۱. همهٔ مهرهای زمانیِ ذخیره‌شده در دیتابیس **UTC** هستند.
   دلیل: ستون‌های `TEXT DEFAULT CURRENT_TIMESTAMP` در SQLite همیشه UTC
   می‌نویسند (۲۶ جدول). اگر پایتون زمان محلی بنویسد، دو فرمت و دو
   منطقهٔ زمانی در یک ستون قاطی می‌شود و مقایسه‌های رشته‌ای خراب می‌شوند.

۲. خروجی این ماژول همیشه آفست صریح دارد:
       «2026-09-19T10:46:17.123456+00:00»
   پس هیچ ابهامی دربارهٔ منطقهٔ زمانی باقی نمی‌ماند.

۳. نمایش برای کاربر، در `utils.persian_date.format_timestamp` و به
   زمان محلیِ همان رایانه تبدیل می‌شود — یعنی کاربر ساعت درست را
   می‌بیند، بدون اینکه داده‌ها دچار ابهام شوند.

۴. برای مقایسه با ستون‌هایی که خودِ SQLite پر می‌کند
   (created_at/updated_at)، از `utc_now_sql()` استفاده کنید که همان
   قالب SQLite را دارد:  «2026-09-19 10:46:17»
"""

from datetime import datetime, timedelta, timezone

UTC = timezone.utc


def utc_now():
    """زمان کنونی به وقت جهانی، با آفست (aware)"""
    return datetime.now(UTC)


def utc_now_iso():
    """
    مهر زمانی ISO با آفست صریح UTC — برای نوشتن در ستون‌های TEXT

    Returns:
        str: مثلاً «2026-09-19T10:46:17.123456+00:00»
    """
    return utc_now().isoformat()


def utc_now_sql():
    """
    مهر زمانی در همان قالبِ SQLite (`CURRENT_TIMESTAMP`)

    برای مقایسه با ستون‌هایی که خودِ دیتابیس پر می‌کند لازم است،
    چون آن‌ها با فاصله و بدون آفست ذخیره می‌شوند:
        «2026-09-19 10:46:17»
    """
    return utc_now().strftime('%Y-%m-%d %H:%M:%S')


def utc_shift_iso(**kwargs):
    """
    مهر زمانی UTC با جابه‌جایی (برای بازه‌های زمانی)

    مثال:
        utc_shift_iso(days=-30)   # سی روز پیش، به وقت جهانی

    Args:
        **kwargs: همان آرگومان‌های timedelta (days, hours, minutes, …)

    Returns:
        str: مهر ISO با آفست UTC
    """
    return (utc_now() + timedelta(**kwargs)).isoformat()


def utc_shift_sql(**kwargs):
    """مهر زمانی UTC در قالب SQLite، با جابه‌جایی"""
    return (utc_now() + timedelta(**kwargs)).strftime('%Y-%m-%d %H:%M:%S')


def parse_timestamp(value):
    """
    تبدیل هر شکلِ مهر زمانی ذخیره‌شده به datetime آگاه از منطقهٔ زمانی

    ورودی‌های پشتیبانی‌شده:
        • «2026-09-19T10:46:17.123456+00:00»  → همان (آفست صریح)
        • «2026-09-19T13:46:17.123456»        → local (نوشتهٔ نسخه‌های قدیمی)
        • «2026-09-19 10:46:17»               → UTC (قالب SQLite)

    Args:
        value: رشته یا datetime یا None

    Returns:
        datetime | None: مقدار آگاه از منطقهٔ زمانی، یا None اگر
        قابل تبدیل نبود. توابع فراخوان باید None را مدیریت کنند.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None

    if dt.tzinfo is not None:
        return dt

    # بدون آفست: اگر جداکنندهٔ «T» باشد از پایتون آمده (نسخه‌های
    # قدیمی، محلی)؛ وگرنه از SQLite آمده و UTC است.
    if isinstance(value, datetime) or 'T' in str(value):
        return dt.astimezone()
    return dt.replace(tzinfo=UTC)


def age_days(value, now=None):
    """
    سن یک مهر زمانی بر حسب روز

    Args:
        value: مهر زمانی ذخیره‌شده
        now: مبنای محاسبه (پیش‌فرض: همین حالا)

    Returns:
        float | None: تعداد روز، یا None اگر مقدار قابل تبدیل نبود
    """
    parsed = parse_timestamp(value)
    if parsed is None:
        return None
    reference = now or utc_now()
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    return (reference - parsed).total_seconds() / 86400.0


def is_older_than(value, **kwargs):
    """آیا مهر زمانی از یک بازهٔ مشخص قدیمی‌تر است؟"""
    days = age_days(value)
    if days is None:
        return False
    return days > (timedelta(**kwargs).total_seconds() / 86400.0)
