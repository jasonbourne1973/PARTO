"""
ماژول ابزارهای کمکی

===== چه چیزی اصلاح شد =====
نسخه قبلی این فایل دو import فوری (eager) داشت:

    from utils.persian_date import PersianDate
    from utils.shamsi_date_input import ShamsiDateInput

`ShamsiDateInput` یک ویجت Qt است و PySide6 را import می‌کند. چون هر
`from utils.xxx import ...` اول `utils/__init__.py` را اجرا می‌کند،
عملاً **لایه داده به لایه رابط کاربری وابسته شده بود**:

    database/connection.py::_seed_default_data
        → from utils.security import Security
        → utils/__init__.py
        → utils.shamsi_date_input
        → PySide6.QtWidgets   ❌

نتیجه‌اش این بود که هر استفاده بدون رابط گرافیکی از دیتابیس
(اسکریپت‌ها، تست‌ها، پشتیبان‌گیری خودکار، تولید گزارش از خط فرمان،
سرور بدون نمایشگر) با خطای import Qt شکست می‌خورد.

حالا import به صورت تنبل (PEP 562 - module __getattr__) انجام می‌شود:
`from utils import PersianDate` و `from utils import ShamsiDateInput`
دقیقاً مثل قبل کار می‌کنند، اما Qt فقط زمانی بارگذاری می‌شود که واقعاً
به آن نیاز باشد.
"""

import importlib

__all__ = ["PersianDate", "ShamsiDateEdit", "ShamsiDateInput"]

_LAZY = {
    "PersianDate": "utils.persian_date",
    "ShamsiDateInput": "utils.shamsi_date_input",
    "ShamsiDateEdit": "utils.shamsi_date_edit",
}


def __getattr__(name):
    """بارگذاری تنبل نام‌های عمومی ماژول (PEP 562)"""
    module_name = _LAZY.get(name)
    if module_name is None:
        raise AttributeError(f"module 'utils' has no attribute '{name}'")
    module = importlib.import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value  # کش کردن تا دفعه بعد سریع باشد
    return value


def __dir__():
    return sorted(list(globals().keys()) + __all__)
