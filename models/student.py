"""
مدل دانش‌آموز (اطلاعات دائمی)
"""

from models.base import BaseModel


class Student(BaseModel):
    """مدل دانش‌آموز با پشتیبانی از Soft Delete"""

    def __init__(self):
        super().__init__()
        self.first_name = None
        self.last_name = None
        self.national_code = None
        self.birth_date = None
        self.father_name = None
        self.guardian_name = None
        self.guardian_phone = None
        self.address = None
        self._is_active = 1  # استفاده از متغیر خصوصی
        
        # این فیلدها در دیتابیس وجود ندارند - برای نمایش استفاده می‌شوند
        self.siblings_brothers = 0
        self.siblings_sisters = 0
        self.living_status = None

    # ------------------------------------------------------------------
    # پراپرتی is_active با getter و setter
    # ------------------------------------------------------------------
    @property
    def is_active(self):
        """دریافت وضعیت فعال بودن"""
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        """تنظیم وضعیت فعال بودن (هر مقدار truthy → 1 و غیر آن → 0)"""
        self._is_active = 1 if value else 0

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def full_name_with_code(self):
        """نام کامل به همراه کد ملی"""
        if self.national_code:
            return f"{self.full_name} ({self.national_code})"
        return self.full_name
    
    def soft_delete(self, user_id=None):
        """حذف منطقی دانش‌آموز"""
        super().soft_delete(user_id)
        self.is_active = 0  # غیرفعال کردن همزمان
    
    def restore(self):
        """بازیابی دانش‌آموز از حذف منطقی"""
        super().restore()
        self.is_active = 1  # فعال کردن همزمان

    def validate(self):
        """اعتبارسنجی اطلاعات دانش‌آموز برای فرم و سرویس."""
        errors = []

        if not self.first_name or not self.first_name.strip():
            errors.append("نام نمی‌تواند خالی باشد")
        elif len(self.first_name.strip()) < 2:
            errors.append("نام باید حداقل ۲ کاراکتر باشد")

        if not self.last_name or not self.last_name.strip():
            errors.append("نام خانوادگی نمی‌تواند خالی باشد")
        elif len(self.last_name.strip()) < 2:
            errors.append("نام خانوادگی باید حداقل ۲ کاراکتر باشد")

        # کد ملی اختیاری است، اما اگر وارد شود باید دقیقاً ده رقم باشد.
        if self.national_code:
            national_code = str(self.national_code).strip()
            if not national_code.isdigit() or len(national_code) != 10:
                errors.append("کد ملی باید دقیقاً ۱۰ رقم باشد")

        # شماره سرپرست اختیاری است، اما مقدار واردشده باید یازده رقم باشد.
        if self.guardian_phone:
            guardian_phone = str(self.guardian_phone).strip()
            if not guardian_phone.isdigit() or len(guardian_phone) != 11:
                errors.append("شماره تماس سرپرست باید ۱۱ رقم باشد")

        return errors
