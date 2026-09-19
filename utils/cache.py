"""
ابزار کش کردن داده‌ها برای افزایش سرعت

===== چه چیزی اصلاح شد =====
۱. نسخه قبلی با `if result is not None` تصمیم می‌گشت. چون `get()`
   برای «نبود» هم `None` برمی‌گرداند، هر تابعی که `{}` یا `[]` یا
   `0` یا `False` برمی‌گرداند هرگز کش نمی‌شد. در کوئری‌های آماری
   این خیلی رایج است.

۲. «منقضی شده» و «وجود ندارد» هر دو `None` بودند و قابل تفکیک نبودند.

۳. هیچ سقف حافظه‌ای وجود نداشت ⇒ رشد بی‌حد.

۴. کلید کش شامل `str(self)` بود که برای متدها `<object at 0x7f...>`
   تولید می‌کند.

۵. کش هیچ‌وقت بعد از نوشتن در دیتابیس پاک نمی‌شد. حالا `invalidate`
   بر اساس پیشوند اضافه شده تا بعد از هر create/update/delete
   کش‌های مرتبط دور ریخته شوند.
"""

import threading
import time
from collections import OrderedDict
from functools import wraps

# علامتی که «مقدار کش‌شده واقعاً None بود» را از «کش وجود ندارد»
# جدا می‌کند.
_MISSING = object()


class Cache:
    """مدیریت کش داده‌ها - thread-safe با سقف حافظه"""

    _instance = None
    _lock = threading.RLock()

    # حداکثر تعداد کلید در کش
    MAX_ENTRIES = 512

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._cache = OrderedDict()
                cls._instance._expiry = {}
                cls._instance._hits = 0
                cls._instance._misses = 0
            return cls._instance

    def get(self, key, default=None):
        """
        دریافت مقدار از کش

        Returns:
            مقدار کش‌شده، یا `default` اگر نبود/منقضی شده بود.
            چون default پیش‌فرض None است ولی می‌توانید هر چیز دیگری
            بدهید، مقدار کش‌شده‌ی None هم درست تشخیص داده می‌شود.
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default

            expiry = self._expiry.get(key)
            if expiry is not None and time.time() > expiry:
                self._evict(key)
                self._misses += 1
                return default

            # دسترسی اخیر را به آخر OrderedDict ببر (برای LRU)
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]

    def set(self, key, value, ttl=300):
        """
        ذخیره مقدار در کش

        Args:
            ttl: زمان انقضا به ثانیه. None یعنی بدون انقضا.
        """
        with self._lock:
            self._cache[key] = value
            self._cache.move_to_end(key)
            self._expiry[key] = (time.time() + ttl) if ttl else None

            # اگر از سقف گذشتیم، قدیمی‌ترین را دور بریز
            while len(self._cache) > self.MAX_ENTRIES:
                oldest_key, _ = self._cache.popitem(last=False)
                self._expiry.pop(oldest_key, None)

        return value

    def has(self, key):
        """آیا کلید در کش هست و منقضی نشده؟"""
        with self._lock:
            if key not in self._cache:
                return False
            expiry = self._expiry.get(key)
            return expiry is None or time.time() <= expiry

    def clear(self, key=None):
        """پاک کردن یک کلید یا کل کش"""
        with self._lock:
            if key is None:
                self._cache.clear()
                self._expiry.clear()
                return
            self._evict(key)

    def invalidate(self, prefix):
        """
        پاک کردن همه کلیدهایی که با این پیشوند شروع می‌شوند

        بعد از نوشتن در دیتابیس صدا زده شود تا کش کهنه خوانده نشود.

        مثال:
            cache.invalidate('get_dashboard_data')
        """
        with self._lock:
            doomed = [k for k in self._cache if str(k).startswith(prefix)]
            for key in doomed:
                self._evict(key)
            return len(doomed)

    def stats(self):
        """آمار کش - برای صفحه تنظیمات/دیباگ"""
        with self._lock:
            total = self._hits + self._misses
            return {
                'entries': len(self._cache),
                'max_entries': self.MAX_ENTRIES,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(self._hits / total * 100, 1) if total else 0.0,
            }

    def _evict(self, key):
        self._cache.pop(key, None)
        self._expiry.pop(key, None)

    # سازگاری با کد قبلی
    def is_valid(self, key):
        return self.has(key)


def cached(ttl=300, key_prefix=None):
    """
    دکوراتور کش کردن نتایج توابع

    Args:
        ttl: زمان انقضا به ثانیه
        key_prefix: پیشوند کلید. اگر ندهید، نام ماژول + نام تابع است.

    نکته مهم درباره کلیدها:
    برای متدها، `self` از آرگومان‌ها حذف می‌شود و به جایش نام کلاس
    می‌آید. این کار از دو مشکل جلوگیری می‌کند:
      ۱. `str(self)` آدرس حافظه تولید می‌کند که کلید را بی‌فایده می‌کرد
      ۲. کلید کوتاه‌تر و قابل خواندن می‌شود

    نکته درباره آرگومان‌های غیرقابل هش:
    dict و list به رشته خوانا تبدیل می‌شوند. اگر آرگومانی دارید که
    str() پایداری ندارد، `cached` را روی آن تابع نگذارید.
    """
    def decorator(func):
        prefix = key_prefix or f"{func.__module__}.{func.__qualname__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = Cache()
            key = _build_key(prefix, func, args, kwargs)

            cached_value = cache.get(key, default=_MISSING)
            if cached_value is not _MISSING:
                return cached_value

            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        # اجازه پاک کردن دستی کش این تابع
        wrapper.invalidate_cache = lambda: Cache().invalidate(prefix)
        wrapper.cache_prefix = prefix
        return wrapper

    return decorator


def _build_key(prefix, func, args, kwargs):
    """ساخت کلید پایدار و خوانا"""
    call_args = args

    # برای متدها، self را حذف کن و نام کلاس را جایگزین کن
    if args and _is_method(func, args[0]):
        call_args = (f"<{type(args[0]).__name__}>", *args[1:])

    arg_parts = [_stable_repr(value) for value in call_args]
    kwarg_parts = [
        f"{name}={_stable_repr(value)}"
        for name, value in sorted(kwargs.items())
    ]

    return f"{prefix}({','.join(arg_parts + kwarg_parts)})"


def _is_method(func, first_arg):
    """آیا اولین آرگومان یک self است؟"""
    if first_arg is None or isinstance(first_arg, (str, int, float, bool)):
        return False
    return hasattr(first_arg, '__class__') and hasattr(first_arg, '__dict__')


def _stable_repr(value):
    """نمایش پایدار برای استفاده در کلید کش"""
    if value is None:
        return "None"
    if isinstance(value, (str, int, float, bool)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_stable_repr(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            f"{_stable_repr(k)}:{_stable_repr(v)}"
            for k, v in sorted(value.items(), key=lambda kv: repr(kv[0]))
        ) + "}"
    if isinstance(value, (set, frozenset)):
        return "{" + ",".join(sorted(_stable_repr(v) for v in value)) + "}"
    # برای اشیاء سفارشی: نام کلاس + id
    return f"<{type(value).__name__}:{id(value)}>"
