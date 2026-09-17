"""
سرویس پایه با پشتیبانی از Transaction و مدیریت خطا
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import DatabaseConnection
from utils.logger import get_logger
from utils.error_handler import ErrorHandler, ServiceError


class BaseService:
    """
    سرویس پایه برای تمام سرویس‌ها
    
    ویژگی‌ها:
    - مدیریت Transaction
    - مدیریت خطا
    - Logging یکپارچه
    - Audit Log
    """
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler()
        self._in_transaction = False
    
    # ============================================================
    # Transaction واقعی
    # ============================================================
    #
    # ===== اصلاح مهم =====
    # نسخه قبلی begin_transaction() فقط `self._in_transaction = True`
    # ست می‌کرد. هیچ BEGIN به sqlite فرستاده نمی‌شد و DALها همچنان
    # بعد از هر دستور commit می‌زدند. نتیجه:
    #
    #     execute_in_transaction(...)  → خطا → rollback
    #     → داده‌ای که نوشته شده بود سر جایش می‌ماند
    #
    # تست انجام‌شده روی کد قبلی: بعد از rollback، تعداد دانش‌آموز
    # یتیم در دیتابیس = ۱ (باید ۰ باشد).
    #
    # حالا کار به DatabaseConnection سپرده می‌شود که عمق تراکنش را
    # نگه می‌دارد و commit()های میانی را بی‌اثر می‌کند. تراکنش‌های
    # تودرتو هم پشتیبانی می‌شوند.

    def begin_transaction(self):
        """شروع یک Transaction جدید (تودرتو مجاز است)"""
        self.db.begin_transaction()
        self._in_transaction = True
        self.logger.debug("Transaction شروع شد.")

    def commit_transaction(self):
        """تأیید Transaction"""
        try:
            self.db.commit_transaction()
            self._in_transaction = self.db.in_transaction
            self.logger.debug("Transaction با موفقیت تأیید شد.")
        except Exception as e:
            self.logger.error(f"خطا در تأیید Transaction: {e}")
            self.rollback_transaction()
            raise ServiceError(f"خطا در ذخیره‌سازی: {str(e)}")

    def rollback_transaction(self):
        """بازگشت Transaction (همه لایه‌های تودرتو)"""
        try:
            self.db.rollback_transaction()
            self._in_transaction = False
            self.logger.debug("Transaction بازگشت داده شد.")
        except Exception as e:
            self.logger.error(f"خطا در بازگشت Transaction: {e}")

    def execute_in_transaction(self, func, *args, **kwargs):
        """
        اجرای یک تابع در داخل Transaction

        Args:
            func: تابعی که باید اجرا شود
            *args, **kwargs: آرگومان‌های تابع

        Returns:
            نتیجه تابع

        Raises:
            ServiceError: در صورت بروز خطا
        """
        self.begin_transaction()
        try:
            result = func(*args, **kwargs)
            self.commit_transaction()
            return result
        except Exception as e:
            self.rollback_transaction()
            self.logger.error(f"خطا در اجرای Transaction: {e}")
            # ===== اصلاح =====
            # نسخه قبلی نوع خطای اصلی را دور می‌انداخت و همه‌چیز را
            # به ServiceError تبدیل می‌کرد. حالا اگر خطا از قبل یک
            # ServiceError بود (مثلاً خطای اعتبارسنجی با پیام فارسی)،
            # همان پیام به کاربر می‌رسد نه «خطا در عملیات: ...».
            if isinstance(e, ServiceError):
                raise
            raise ServiceError(f"خطا در عملیات: {str(e)}") from e

    def transaction(self):
        """
        استفاده به شکل with (روش پیشنهادی برای کد جدید)

            with self.transaction():
                self.student_dal.create(student)
                self.profile_dal.create(profile)
        """
        return _TransactionContext(self)


class _TransactionContext:
    """مدیر زمینه برای with self.transaction()"""

    def __init__(self, service):
        self._service = service

    def __enter__(self):
        self._service.begin_transaction()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._service.commit_transaction()
        else:
            self._service.rollback_transaction()
        # خطا را بلعیده نمی‌کنیم؛ به بالادست propagate می‌شود
        return False
    
    def log_audit(self, user_id, action, entity_type, entity_id=None,
                  old_value=None, new_value=None, ip_address=None):
        """ثبت Audit Log"""
        try:
            from utils.security import AuditLogger
            audit_logger = AuditLogger(self.db)
            return audit_logger.log(user_id, action, entity_type, entity_id,
                                   old_value, new_value, ip_address)
        except Exception as e:
            self.logger.warning(f"خطا در ثبت Audit Log: {e}")
            return False
    
    def handle_error(self, error, user_message=None, log_level='error'):
        """
        مدیریت یک خطا
        
        Args:
            error: شیء خطا
            user_message: پیام نمایشی به کاربر
            log_level: سطح لاگ ('error', 'warning', 'info')
        """
        return self.error_handler.handle(error, user_message, log_level)
    
    def validate_model(self, model):
        """
        اعتبارسنجی یک مدل
        
        Args:
            model: مدل مورد نظر
            
        Returns:
            bool: آیا مدل معتبر است؟
            
        Raises:
            ServiceError: در صورت عدم اعتبار
        """
        errors = model.validate()
        if errors:
            error_msg = "\n".join(errors)
            self.logger.warning(f"خطای اعتبارسنجی: {error_msg}")
            raise ServiceError(f"خطا در اعتبارسنجی:\n{error_msg}")
        return True