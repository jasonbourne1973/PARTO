"""
مدیریت استاندارد خطا در سراسر برنامه

===== چه چیزی اصلاح شد =====
۱. کلاس `PermissionError` هم‌نام با کلاس داخلی پایتون بود. هر فایلی
   که این ماژول را import می‌کرد و بعد `except PermissionError` می‌نوشت،
   خطای واقعی سیستم‌عامل (مثلاً `os.remove` روی فایل قفل‌شده در
   ویندوز) را نمی‌گرفت. نام به `AuthorizationError` تغییر کرد.
   یک alias با هشدار برای سازگاری موقت نگه داشته شده.

۲. دکوراتور `handle_exceptions` به جای raise کردن، dict برمی‌گرداند.
   یعنی تابعی که `Student` برمی‌گرداند، در حالت خطا `dict` برمی‌گرداند
   و فراخوان با `AttributeError` کرش می‌کرد. حالا پیش‌فرض raise است.

۳. منطق نمایش پیام با `code < 500` تصمیم می‌گرفت. ولی `ServiceError`
   و `DatabaseError` هر دو code=500 دارند، پس پیام‌های مفید مثل
   «این کد ملی قبلاً ثبت شده» با «خطای داخلی سیستم» جایگزین می‌شد.
   حالا معیار این است که آیا خطا از جنس `AppError` است یا نه.

۴. `ServiceError` حالا `user_visible=True` دارد چون پیام‌هایش برای
   کاربر نوشته شده‌اند، نه برای لاگ.
"""

import sys
import traceback
import warnings
from datetime import datetime

from utils.logger import get_logger, log_error


class AppError(Exception):
    """
    خطای پایه برنامه

    Attributes:
        message: پیام خطا
        code: کد خطا (مشابه HTTP برای دسته‌بندی)
        details: جزئیات اضافی
        user_visible: آیا این پیام برای نشان دادن به کاربر مناسب است؟
                      اگر False باشد، پیام عمومی نمایش داده می‌شود.
    """

    def __init__(self, message, code=None, details=None, user_visible=True):
        self.message = message
        self.code = code or 500
        self.details = details or {}
        self.user_visible = user_visible
        super().__init__(message)


class ValidationError(AppError):
    """خطای اعتبارسنجی - پیام همیشه برای کاربر مناسب است"""

    def __init__(self, message, details=None):
        super().__init__(message, code=400, details=details,
                         user_visible=True)


class NotFoundError(AppError):
    """خطای پیدا نشدن رکورد"""

    def __init__(self, message, details=None):
        super().__init__(message, code=404, details=details,
                         user_visible=True)


class AuthorizationError(AppError):
    """
    خطای دسترسی غیرمجاز

    این کلاس قبلاً `PermissionError` نام داشت که با کلاس داخلی پایتون
    تداخل می‌کرد. نام تغییر کرد.
    """

    def __init__(self, message, details=None):
        super().__init__(message, code=403, details=details,
                         user_visible=True)


class ServiceError(AppError):
    """
    خطای سرویس

    پیام‌های ServiceError معمولاً برای کاربر نوشته شده‌اند
    («دانش‌آموز با این کد ملی قبلاً ثبت شده است») پس user_visible=True.
    """

    def __init__(self, message, details=None, user_visible=True):
        super().__init__(message, code=500, details=details,
                         user_visible=user_visible)


class DatabaseError(AppError):
    """خطای دیتابیس - پیام فنی است و به کاربر نشان داده نمی‌شود"""

    def __init__(self, message, details=None):
        super().__init__(message, code=500, details=details,
                         user_visible=False)


class DataIntegrityError(AppError):
    """
    خطای یکپارچگی داده

    مثلاً وقتی یک عملیات چندمرحله‌ای نصفه‌کاره می‌ماند.
    """

    def __init__(self, message, details=None):
        super().__init__(message, code=500, details=details,
                         user_visible=False)


# ------------------------------------------------------------------
# سازگاری با کد قبلی
# ------------------------------------------------------------------
# کد قدیمی ممکن است `from utils.error_handler import PermissionError`
# داشته باشد. این alias فعلاً نگه داشته شده تا چیزی نشکند، ولی
# یک DeprecationWarning می‌دهد. در نسخه بعدی حذف می‌شود.

def __getattr__(name):
    """
    پشتیبانی از `from utils.error_handler import PermissionError`

    این ماژول‌سطح __getattr__ است (PEP 562، پایتون ۳.۷ به بعد).
    """
    if name == 'PermissionError':
        warnings.warn(
            "utils.error_handler.PermissionError منسوخ شده است. "
            "این نام با کلاس داخلی پایتون تداخل می‌کرد. "
            "به جایش از AuthorizationError استفاده کنید.",
            DeprecationWarning,
            stacklevel=2
        )
        return AuthorizationError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class ErrorHandler:
    """مدیریت استاندارد خطاها"""

    # پیام عمومی برای خطاهایی که نباید جزئیات فنی‌شان نشان داده شود
    GENERIC_MESSAGE = (
        "خطای غیرمنتظره‌ای رخ داد.\n"
        "جزئیات در فایل لاگ ثبت شده است."
    )

    def __init__(self):
        self.logger = get_logger('ErrorHandler')

    def handle(self, error, user_message=None, log_level='error',
               reraise=False):
        """
        مدیریت یک خطا

        Args:
            error: شیء خطا
            user_message: پیام نمایشی دلخواه (اختیاری)
            log_level: سطح لاگ ('error', 'warning', 'info')
            reraise: اگر True، بعد از ثبت و لاگ، خطا دوباره raise می‌شود.
                     این حالت برای زمانی است که می‌خواهید هم لاگ شود
                     هم فراخوان بداند عملیات شکست خورده.

        Returns:
            dict: پاسخ استاندارد خطا

        Raises:
            همان error اگر reraise=True باشد
        """
        error_info = self._extract_error_info(error)
        self._log_error(error_info, log_level)
        response = self._build_response(error_info, user_message)

        if reraise:
            raise error

        return response

    def _extract_error_info(self, error):
        """استخراج اطلاعات از خطا"""
        return {
            'type': type(error).__name__,
            'message': str(error),
            'code': getattr(error, 'code', 500),
            'details': getattr(error, 'details', {}),
            'user_visible': getattr(error, 'user_visible', False),
            'is_app_error': isinstance(error, AppError),
            'traceback': (
                None if isinstance(error, AppError)
                else traceback.format_exc()
            ),
        }

    def _log_error(self, error_info, log_level):
        """ثبت خطا در لاگ"""
        log_message = f"[{error_info['type']}] {error_info['message']}"

        if log_level == 'error':
            log_error('ErrorHandler', log_message, extra={
                'code': error_info['code'],
                'details': error_info['details'],
                'traceback': error_info['traceback']
            })
        elif log_level == 'warning':
            self.logger.warning(log_message, extra={
                'code': error_info['code'],
                'details': error_info['details']
            })
        else:
            self.logger.info(log_message, extra={
                'code': error_info['code'],
                'details': error_info['details']
            })

    def _build_response(self, error_info, user_message):
        """
        ساخت پاسخ استاندارد برای کاربر

        منطق نمایش پیام:
        - اگر کاربر پیام دلخواه داده → همان
        - اگر خطا از جنس AppError است و user_visible=True → پیام خود خطا
        - در غیر این صورت → پیام عمومی

        نسخه قبلی با `code < 500` تصمیم می‌گرفت. چون ServiceError
        کد ۵۰۰ دارد، پیام‌های مفیدش هرگز به کاربر نمی‌رسید.
        """
        if user_message:
            display_message = user_message
        elif error_info['user_visible']:
            display_message = error_info['message']
        else:
            display_message = self.GENERIC_MESSAGE

        return {
            'success': False,
            'error': {
                'code': error_info['code'],
                'type': error_info['type'],
                'message': display_message,
                # جزئیات فنی فقط وقتی که پیام برای کاربر مناسب است
                'details': (
                    error_info['details']
                    if error_info['user_visible'] else None
                ),
            }
        }

    @staticmethod
    def handle_exceptions(func=None, *, reraise=True, log_level='error'):
        """
        دکوراتور مدیریت خطا

        Args:
            reraise: اگر True (پیش‌فرض)، خطا بعد از لاگ دوباره raise
                     می‌شود. این رفتار درست است چون فراخوان باید بداند
                     عملیات شکست خورده.
                     اگر False باشد، dict خطا برگردانده می‌شود - فقط
                     برای توابعی که واقعاً خروجی dict دارند مناسب است.
            log_level: سطح لاگ

        استفاده:
            @ErrorHandler.handle_exceptions
            def create_student(...):
                ...

            # یا با تنظیمات:
            @ErrorHandler.handle_exceptions(reraise=False)
            def get_stats(...):
                ...
        """
        def decorator(fn):
            def wrapper(*args, **kwargs):
                handler = ErrorHandler()
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    return handler.handle(
                        e, log_level=log_level, reraise=reraise
                    )
            wrapper.__name__ = fn.__name__
            wrapper.__doc__ = fn.__doc__
            return wrapper

        # پشتیبانی از هر دو شکل: با و بدون پرانتز
        if func is not None:
            return decorator(func)
        return decorator
