"""
Migration نسخه ۹ — یکدست‌سازی تاریخ‌های شمسیِ موجود در دیتابیس

===== چرا این migration لازم است؟ =====
از بازرسی هشتم، همهٔ مسیرهای *نوشتن* تاریخ را یکدست کردیم
(«1405-6-6» → «1405/06/06»، ارقام فارسی → لاتین، صفر ابتدایی).
اما دیتابیس‌هایی که از قبل وجود دارند، ردیف‌های قدیمی با قالب‌های
مخلوط دارند:

    '1405-6-6'   '۱۴۰۵/۰۶/۰۶'   '1405/6/6'   '1405/06/06'

SQLite مقایسه و ORDER BY را رشته‌ای انجام می‌دهد، پس این مخلوط باعث
می‌شود:
  • بازه‌های تاریخی («از ۱۴۰۵/۰۶/۰۱ تا ۱۴۰۵/۰۶/۳۱») بعضی ردیف‌ها را
    از قلم بیندازند،
  • روندها و نمودارهای ماهانه/هفتگی نادرست گروه‌بندی شوند.

===== چه کاری انجام می‌شود؟ =====
۲۰ ستون تاریخ‌دار در جدول‌های مختلف پیمایش می‌شود؛ هر مقدار با همان
تابع مشترک `to_db_date` نرمال می‌شود و فقط اگر تفاوت داشت، UPDATE
می‌شود. مقادیری که تاریخ شمسی نیستند (متن آزاد، NULL) دست‌نخورده
می‌مانند و فقط شمارش می‌شوند.

===== بی‌خطر بودن =====
  • فقط مقادیری که «سالم و شمسی» تشخیص داده شوند بازنویسی می‌شوند
    (بازهٔ سال ۱۳۰۰ تا ۱۵۰۰).
  • اجرای دوبارهٔ آن هیچ تغییری ایجاد نمی‌کند (idempotent).
  • هر جدول/ستون داخل try/except است تا روی ساختارهای قدیمیِ ناقص
    هم بالا آمدن برنامه متوقف نشود.
"""

import re

# ستون‌های تاریخ‌دار (جدول، ستون)
DATE_COLUMNS = [
    ("academic_years", "start_date"),
    ("academic_years", "end_date"),
    ("students", "birth_date"),
    ("parent_interviews", "interview_date"),
    ("parent_interviews", "next_action_date"),
    ("observations", "observation_date"),
    ("screenings", "execution_date"),
    ("screening_results", "execution_date"),
    ("interventions", "date"),
    ("followups", "date"),
    ("followups", "next_action_date"),
    ("teacher_assignments", "assigned_date"),
    ("counseling_sessions", "session_date"),
    ("counseling_sessions", "next_session_date"),
    ("extracurricular_activities", "start_date"),
    ("extracurricular_activities", "end_date"),
    ("individual_goals", "target_date"),
    ("individual_goals", "start_date"),
    ("individual_goals", "end_date"),
    ("individual_goals", "achievement_date"),
]

# بازهٔ قابل‌قبول سال شمسی (برای اینکه تاریخ میلادی یا متن آزاد
# اشتباهی «نرمال» نشود)
MIN_YEAR = 1300
MAX_YEAR = 1500

CANONICAL_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")


def _table_exists(cursor, table_name):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def _normalize(value):
    """
    یک مقدار تاریخ شمسی را به قالب کانونیکال yyyy/MM/dd تبدیل می‌کند

    Returns:
        str | None: مقدار نرمال‌شده، یا None اگر مقدار تاریخ شمسی نباشد
    """
    from utils.persian_date import to_db_date

    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    normalized = to_db_date(text)
    if not normalized:
        return None

    if not CANONICAL_RE.match(normalized):
        return None

    try:
        year = int(normalized[:4])
        month = int(normalized[5:7])
        day = int(normalized[8:10])
    except ValueError:
        return None

    # فقط سال شمسی منطقی و ماه/روز معتبر
    if not (MIN_YEAR <= year <= MAX_YEAR):
        return None
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None

    return normalized


def upgrade(connection):
    """نرمال‌سازی تاریخ‌های شمسیِ ردیف‌های موجود"""
    cursor = connection.cursor()

    print("🔄 Migration نسخه ۹: یکدست‌سازی تاریخ‌های شمسی در دیتابیس")

    total_updated = 0
    total_skipped = 0

    for table, column in DATE_COLUMNS:
        if not _table_exists(cursor, table) or not _column_exists(cursor, table, column):
            continue

        try:
            cursor.execute(
                f"SELECT id, {column} FROM {table} "
                f"WHERE {column} IS NOT NULL AND TRIM({column}) <> ''"
            )
            rows = cursor.fetchall()
        except Exception as e:
            print(f"  ⚠️ خواندن {table}.{column} ممکن نشد: {e}")
            continue

        updated = 0
        for row_id, value in rows:
            normalized = _normalize(value)
            if normalized is None:
                total_skipped += 1
                continue
            if normalized != value:
                cursor.execute(
                    f"UPDATE {table} SET {column} = ? WHERE id = ?",
                    (normalized, row_id),
                )
                updated += 1

        if updated:
            total_updated += updated
            print(f"  ✅ {table}.{column}: {updated} مقدار نرمال شد")

    # (بازرسی شانزدهم — BUG-NEW-02) commit این‌جا حذف شد: تراکنش را فقط
    # MigrationManager._run_step (یا _heal_schema) باز و commit/rollback می‌کند.
    print(
        f"  📊 جمع: {total_updated} مقدار اصلاح شد"
        f"{f'، {total_skipped} مقدار غیرتاریخی رد شد' if total_skipped else ''}."
    )


def downgrade(connection):
    """
    بازگشت — عمداً کاری انجام نمی‌شود

    نرمال‌سازی داده تخریب‌پذیر نیست؛ قالب اصلیِ هر ردیف در دیتابیس
    نگه داشته نمی‌شود، پس بازگرداندن آن ممکن نیست. دست‌نخورده گذاشتن
    دادهٔ نرمال‌شده بی‌خطر است (همهٔ کدها این قالب را می‌فهمند).
    """
    print("ℹ️ بازگشت از نسخه ۹ لازم نیست: تاریخ‌ها فقط یکدست شده‌اند.")
