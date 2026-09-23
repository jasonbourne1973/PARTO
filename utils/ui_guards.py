"""
نگهبان‌های سادهٔ رابط کاربری (بازرسی شانزدهم — بند ۳۲)

single_submit: جلوگیری از اجرای دوبارهٔ یک عملیات ذخیره در اثر کلیک دوباره.

چرا لازم است؟ handler ذخیره در نخ رابط کاربری به‌صورت همزمان اجرا می‌شود،
ولی وسط آن `QMessageBox.information(...)` یک حلقهٔ رویداد تودرتو باز می‌کند؛
کلیک دومی که در صف بود همان‌جا پردازش می‌شود و `save_*` دوباره (تودرتو)
اجرا می‌شود → دو رکورد برای یک فرم. این نگهبان ورود دوباره را رد می‌کند و
دکمهٔ ذخیره را تا پایان عملیات غیرفعال نگه می‌دارد.
"""

import functools


def single_submit(button_attr='save_btn'):
    """
    دکوراتور برای متدهای ذخیرهٔ فرم‌ها

    Args:
        button_attr: نام صفتِ دکمهٔ ذخیره روی فرم (برای غیرفعال‌کردن موقت)
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            if getattr(self, '_submit_in_progress', False):
                return None
            self._submit_in_progress = True
            button = getattr(self, button_attr, None)
            if button is not None:
                button.setEnabled(False)
            try:
                return fn(self, *args, **kwargs)
            finally:
                self._submit_in_progress = False
                if button is not None:
                    button.setEnabled(True)
        return wrapper
    return decorator
