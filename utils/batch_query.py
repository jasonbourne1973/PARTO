"""
کمک‌تابع‌های خوانش دسته‌ای (بازرسی چهاردهم — رفع N+1)

الگوی «برای هر رکورد یک get_by_id» با بزرگ‌شدن دیتابیس، پروندهٔ
دانش‌آموز، گزارش‌ها و داشبورد را کند می‌کند. DALها با این کمک‌تابع‌ها
چند شناسه را با «یک» کوئری IN (...) می‌خوانند. برای احترام به سقف
پارامترهای SQLite (در نسخه‌های قدیمی ۹۹۹)، شناسه‌ها تکه‌تکه می‌شوند.
"""

IN_CHUNK_SIZE = 500


def unique_ids(values):
    """شناسه‌های یکتا و غیر-None، با ترتیب پایدار (مرتب‌شده)."""
    return sorted({value for value in (values or []) if value is not None})


def id_chunks(values, size=IN_CHUNK_SIZE):
    """تقسیم شناسه‌های یکتا به تکه‌های اندازهٔ size برای عبارت IN."""
    ids = unique_ids(values)
    for start in range(0, len(ids), size):
        yield ids[start:start + size]


def placeholders(count):
    """رشتهٔ «?, ?, ...» برای عبارت IN با count پارامتر."""
    return ", ".join("?" * count)
