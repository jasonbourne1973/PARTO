"""
مدل پایه برای تمام موجودیت‌ها - با پشتیبانی از Soft Delete یکپارچه

===== چه چیزی اصلاح شد =====
نسخه قبلی `to_dict` این بود:

    return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

مشکل: `is_active` و `is_deleted` هر دو property هستند، پس در
`__dict__` نیستند. و فیلدهای پشتیبان `_is_active` / `_is_deleted`
با فیلتر `_` حذف می‌شدند.

نتیجه: خروجی to_dict این بود:
    {'id': None, 'created_at': None, 'updated_at': None,
     'deleted_at': None, 'deleted_by': None, 'first_name': 'علی'}
یعنی نه is_active داشت نه is_deleted. هر خروجی JSON، Excel یا
Audit Log که از to_dict استفاده می‌کرد، وضعیت فعال/حذف‌شده را
از دست می‌داد.

حالا propertyهای خواندنی هم به خروجی اضافه می‌شوند.
"""

from datetime import datetime


class BaseModel:
    """مدل پایه با فیلدهای مشترک و Soft Delete یکپارچه"""

    # نام propertyهایی که باید در to_dict ظاهر شوند.
    # کلاس‌های فرزند می‌توانند این را گسترش دهند.
    _EXPOSED_PROPERTIES = (
        'is_deleted',
        'is_active',
        'is_soft_deleted',
    )

    def __init__(self):
        self.id = None
        self.created_at = None
        self.updated_at = None

        # ===== فیلدهای Soft Delete (یکسان در تمام مدل‌ها) =====
        self._is_deleted = 0          # استفاده از متغیر خصوصی
        self.deleted_at = None
        self.deleted_by = None

    @property
    def is_deleted(self):
        """دریافت وضعیت حذف شده"""
        return self._is_deleted

    @is_deleted.setter
    def is_deleted(self, value):
        """تنظیم وضعیت حذف شده"""
        self._is_deleted = 1 if value else 0

    def to_dict(self, include_properties=True):
        """
        تبدیل به دیکشنری

        Args:
            include_properties: اگر True، propertyهای خواندنیِ لیست‌شده
                                در `_EXPOSED_PROPERTIES` هم اضافه می‌شوند.
                                این شامل is_active و is_deleted است که
                                در نسخه قبلی بی‌صدا حذف می‌شدند.

        Returns:
            dict
        """
        result = {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_')
        }

        if include_properties:
            for name in self._EXPOSED_PROPERTIES:
                # فقط propertyهایی که واقعاً روی این کلاس تعریف شده‌اند
                attr = getattr(type(self), name, None)
                if isinstance(attr, property) and name not in result:
                    try:
                        result[name] = getattr(self, name)
                    except AttributeError:
                        # کلاس فرزند property را تعریف نکرده
                        continue

        return result

    @staticmethod
    def get_current_time():
        """دریافت زمان فعلی به فرمت ISO"""
        return datetime.now().isoformat()

    def soft_delete(self, user_id=None):
        """
        حذف منطقی - فقط علامت‌گذاری به عنوان حذف شده

        این متد رکورد را واقعاً از دیتابیس پاک نمی‌کند
        فقط is_deleted را به ۱ تغییر می‌دهد
        """
        self.is_deleted = 1
        self.deleted_at = self.get_current_time()
        self.deleted_by = user_id

    def restore(self):
        """
        بازیابی از حذف منطقی

        این متد رکورد را از حالت حذف شده خارج می‌کند
        """
        self.is_deleted = 0
        self.deleted_at = None
        self.deleted_by = None

    @property
    def is_soft_deleted(self):
        """آیا رکورد حذف شده است؟"""
        return self._is_deleted == 1

    @property
    def is_active(self):
        """
        آیا رکورد فعال است؟

        دو حالت:
        ۱. کلاس فرزند ستون واقعی `is_active` در دیتابیس دارد و
           `_is_active` را ست کرده (مثل Student، Staff، AcademicYear،
           Competency، StudentFile و...) → همان مقدار برگردانده می‌شود.
        ۲. کلاس فرزند چنین ستونی ندارد (مثل Observation، FollowUp،
           Screening و...) → «فعال» یعنی «حذف منطقی نشده».

        این رفتار دقیقاً همان چیزی است که نسخه قبلی هم می‌داد،
        فقط حالا در to_dict هم ظاهر می‌شود.
        """
        own_value = self.__dict__.get('_is_active')
        if own_value is not None:
            return own_value
        return 1 if self._is_deleted == 0 else 0

    @is_active.setter
    def is_active(self, value):
        """
        تنظیم وضعیت فعال

        ===== نکته مهم =====
        این setter حذف‌شدنی نیست. بررسی روی مدل‌ها نشان می‌دهد هر دو
        شکل استفاده می‌شود:

            student.py خط ۵۵:   self.is_active = 0
            student.py خط ۶۰:   self.is_active = 1
            student.py خط ۲۱:   self._is_active = 1

        اگر is_active فقط getter داشته باشد، هر نسبت‌دهی‌ای با
        AttributeError می‌شکند. پس مقدار همیشه در `_is_active`
        نوشته می‌شود تا getter همان را برگرداند.
        """
        self._is_active = 1 if value else 0

    def validate(self):
        """
        اعتبارسنجی مدل - باید در کلاس‌های فرزند پیاده‌سازی شود

        Returns:
            list: لیست خطاها
        """
        return []
