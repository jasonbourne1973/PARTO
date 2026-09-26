"""
اعتبارسنجی/نرمال‌سازی مرکزی پارامترهای Pagination

===== چرا این ماژول لازم شد (دور نوزدهم، مرحلهٔ ۶) =====
پیش از این، هر DAL/صفحه‌ای که Pagination داشت (یا می‌خواست داشته باشد)
منطق `page>=1` / `page_size<=MAX` / `offset>=0` را (اگر اصلاً چک می‌کرد)
خودش و جداگانه پیاده می‌کرد. `views/pages/students_page.py` هم کل
دیتاست را در حافظه لود می‌کرد و Slice پایتونی می‌زد (نه `LIMIT/OFFSET`
واقعی در SQL) — دقیقاً همان anti-pattern که سند مدیر پروژه در بخش‌های
۲، ۳، ۲۵، ۳۵ رد می‌کند.

این ماژول یک محل مشترک برای دو حالت رایج در این کدبیس فراهم می‌کند:

  ۱. `normalize_page(page, page_size, ...)` — برای مصرف‌کنندگانی که با
     شمارهٔ صفحه (۱-پایه) کار می‌کنند (مثلاً UI با دکمهٔ «صفحهٔ بعد»).
  ۲. `normalize_limit_offset(limit, offset, ...)` — برای DALهایی که با
     `limit`/`offset` خام کار می‌کنند (الگوی غالب در این کدبیس).

نکتهٔ مهم سازگاری: در بسیاری از فراخوانی‌های موجود، `limit=None` یعنی
عمداً «بدون سقف — همهٔ رکوردها» (مثلاً خروجی Excel که باید کل دیتاست
فیلترشده را بنویسد، نه فقط صفحهٔ جاری — رفتاری که در verify_fixes17
تثبیت شده). این ماژول هرگز `None` را به یک مقدار پیش‌فرض تبدیل نمی‌کند؛
فقط وقتی مقدار عددیِ واقعی داده شود، آن را در محدودهٔ معتبر Clamp می‌کند.
"""

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


def _to_int(value, default):
    """تبدیل امن به int؛ ورودی نامعتبر/غیرعددی → مقدار پیش‌فرض"""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_limit_offset(limit=None, offset=None, max_page_size=MAX_PAGE_SIZE):
    """
    اعتبارسنجی/Clamp پارامترهای limit/offset خام (الگوی DALهای این پروژه)

    Args:
        limit: تعداد رکورد درخواستی. `None` = بدون سقف (همهٔ رکوردها) —
            دست‌نخورده برمی‌گردد تا رفتار «صادرات کامل» نشکند.
        offset: نقطهٔ شروع. اگر limit مشخص نباشد نادیده گرفته می‌شود
            (OFFSET بدون LIMIT در SQLite معنای مفیدی برای این کدبیس ندارد).
        max_page_size: سقف بالای مجاز برای limit (پیش‌فرض ۲۰۰)

    Returns:
        tuple: (limit_نرمال‌شده یا None, offset_نرمال‌شده یا None)
    """
    if limit is None:
        return None, None

    norm_limit = _to_int(limit, DEFAULT_PAGE_SIZE)
    if norm_limit < 1:
        norm_limit = 1
    if norm_limit > max_page_size:
        norm_limit = max_page_size

    norm_offset = _to_int(offset, 0)
    if norm_offset < 0:
        norm_offset = 0

    return norm_limit, norm_offset


def normalize_page(page=1, page_size=DEFAULT_PAGE_SIZE, max_page_size=MAX_PAGE_SIZE):
    """
    اعتبارسنجی/Clamp پارامترهای page/page_size (۱-پایه) و محاسبهٔ offset

    Args:
        page: شمارهٔ صفحه (۱-پایه). کمتر از ۱ یا نامعتبر → ۱.
        page_size: تعداد ردیف در هر صفحه. کمتر از ۱ یا نامعتبر →
            DEFAULT_PAGE_SIZE؛ بیشتر از max_page_size → کلمپ می‌شود.
        max_page_size: سقف بالای مجاز برای page_size

    Returns:
        tuple: (page:int>=1, page_size:int در [1, max_page_size], offset:int>=0)
    """
    norm_page = _to_int(page, 1)
    if norm_page < 1:
        norm_page = 1

    norm_size = _to_int(page_size, DEFAULT_PAGE_SIZE)
    if norm_size < 1:
        norm_size = DEFAULT_PAGE_SIZE
    if norm_size > max_page_size:
        norm_size = max_page_size

    offset = (norm_page - 1) * norm_size
    return norm_page, norm_size, offset


def clamp_page_to_total(page, page_size, total):
    """
    اطمینان از اینکه صفحهٔ درخواستی بعد از دانستنِ `total` واقعی همچنان
    معتبر است (مثلاً کاربر در صفحهٔ ۵ بود، فیلتر عوض شد و حالا فقط ۲
    صفحه هست) — همان رفتاری که students_page.py از قبل با
    `min(current_page, total_pages - 1)` انجام می‌داد، اینجا متمرکز شد.

    Returns:
        tuple: (page کلمپ‌شده, total_pages)
    """
    total = max(0, _to_int(total, 0))
    page_size = max(1, _to_int(page_size, DEFAULT_PAGE_SIZE))
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1

    page = _to_int(page, 1)
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    return page, total_pages
