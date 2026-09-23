"""
مدل مشاهده - با مدل ABC ساده شده
با ارتباط به ProfessionalInterpretation و پشتیبانی از ساختار سه‌لایه شایستگی
"""

from typing import ClassVar

from models.base import BaseModel


class Observation(BaseModel):
    """
    مدل مشاهده دانش‌آموز - ساده و کاربردی
    
    این مدل فقط رفتارهای قابل مشاهده را ثبت می‌کند.
    تفسیر تخصصی در مدل ProfessionalInterpretation جداگانه ثبت می‌شود.
    
    فیلدهای ضروری برای ثبت سریع مشاهده:
    - student_profile_id: پرونده دانش‌آموز
    - staff_id: مشاهده‌گر
    - observation_date: تاریخ مشاهده
    - location: محیط
    - behavior: رفتار مشاهده‌شده (فیلد اصلی)
    - description: توضیحات (الزامی در دیتابیس)
    
    فیلدهای اختیاری:
    - antecedent: زمینه
    - consequence: پیامد
    - behavior_type: نوع (مثبت/منفی/خنثی)
    - severity: شدت (1-5)
    - tags: برچسب‌ها
    - competency_id: شایستگی مرتبط (اختیاری)
    
    ===== فیلدهای جدید برای ساختار سه‌لایه =====
    - indicator_id: شاخص مرتبط (اختیاری)
    - observable_behavior_id: رفتار قابل مشاهده مرتبط (اختیاری)
    """
    
    # انواع رفتار
    BEHAVIOR_POSITIVE = "مثبت"
    BEHAVIOR_NEGATIVE = "منفی"
    BEHAVIOR_NEUTRAL = "خنثی"
    
    BEHAVIOR_TYPES: ClassVar[list] = [BEHAVIOR_POSITIVE, BEHAVIOR_NEGATIVE, BEHAVIOR_NEUTRAL]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.student_profile_id = None   # ارجاع به StudentAcademicProfile
        self.staff_id = None             # ارجاع به Staff (مشاهده‌گر)
        self.competency_id = None        # ارجاع به Competency (اختیاری)
        
        # ===== فیلدهای جدید ساختار سه‌لایه =====
        self.indicator_id = None         # ارجاع به Indicator (اختیاری)
        self.observable_behavior_id = None  # ارجاع به ObservableBehavior (اختیاری)
        
        # ===== اطلاعات پایه (ضروری) =====
        self.observation_date = None     # تاریخ مشاهده (شمسی)
        self.location = None             # محیط مشاهده
        self.behavior = None             # رفتار مشاهده‌شده (فیلد اصلی)
        self.description = None          # توضیحات کامل (الزامی در دیتابیس)
        
        # ===== اطلاعات تکمیلی (اختیاری) =====
        self.antecedent = None   # A: زمینه (اختیاری)
        self.consequence = None  # C: پیامد (اختیاری)
        
        # ===== اطلاعات اضافی =====
        self.behavior_type = None   # مثبت، منفی، خنثی
        self.severity = 3           # شدت (1 تا 5) - پیش‌فرض متوسط
        self.tags = None            # برچسب‌ها (برای دسته‌بندی)
        
        # ===== فیلدهای کمکی برای نمایش =====
        self.student_name = None
        self.staff_name = None
        self.competency_title = None
        self.indicator_title = None
        self.observable_behavior_text = None
        self.student_id = None  # برای نمایش سریع
        
        # ===== ارتباط با تفسیر تخصصی =====
        self.interpretations = []  # لیست تفسیرهای مرتبط
    
    @property
    def severity_display(self):
        """نمایش شدت به صورت علامت متنی"""
        return "⭐" * (self.severity or 0)
    
    @property
    def severity_text(self):
        """نمایش شدت به صورت متن"""
        severity_map = {
            1: "خیلی کم",
            2: "کم",
            3: "متوسط",
            4: "زیاد",
            5: "خیلی زیاد"
        }
        return severity_map.get(self.severity, str(self.severity))
    
    @property
    def behavior_type_display(self):
        """نمایش نوع رفتار به فارسی"""
        type_map = {
            self.BEHAVIOR_POSITIVE: "✅ مثبت",
            self.BEHAVIOR_NEGATIVE: "❌ منفی",
            self.BEHAVIOR_NEUTRAL: "⬜ خنثی",
        }
        return type_map.get(self.behavior_type, self.behavior_type or "نامشخص")
    
    @property
    def is_positive(self):
        """آیا مشاهده مثبت است؟"""
        return self.behavior_type == self.BEHAVIOR_POSITIVE
    
    @property
    def is_negative(self):
        """آیا مشاهده منفی است؟"""
        return self.behavior_type == self.BEHAVIOR_NEGATIVE
    
    @property
    def behavior_summary(self):
        """خلاصه رفتار برای نمایش"""
        if self.behavior:
            return self.behavior[:100] + "..." if len(self.behavior) > 100 else self.behavior
        return "بدون رفتار ثبت‌شده"
    
    @property
    def abc_summary(self):
        """خلاصه مدل ABC برای نمایش"""
        parts = []
        if self.antecedent:
            parts.append(f"زمینه: {self.antecedent[:50]}...")
        if self.behavior:
            parts.append(f"رفتار: {self.behavior[:50]}...")
        if self.consequence:
            parts.append(f"پیامد: {self.consequence[:50]}...")
        return " | ".join(parts) if parts else "ABC ثبت نشده"
    
    @property
    def has_interpretation(self):
        """آیا تفسیر تخصصی برای این مشاهده وجود دارد؟"""
        return len(self.interpretations) > 0
    
    @property
    def full_competency_path(self):
        """
        دریافت مسیر کامل ساختار سه‌لایه برای نمایش:
        شایستگی → شاخص → رفتار قابل مشاهده
        """
        path_parts = []
        if self.competency_title:
            path_parts.append(self.competency_title)
        if self.indicator_title:
            path_parts.append(self.indicator_title)
        if self.observable_behavior_text:
            path_parts.append(self.observable_behavior_text)
        return " → ".join(path_parts) if path_parts else "ثبت نشده"
    
    def add_interpretation(self, interpretation):
        """افزودن تفسیر تخصصی به مشاهده"""
        if interpretation not in self.interpretations:
            self.interpretations.append(interpretation)
            interpretation.observation_id = self.id
            interpretation.student_profile_id = self.student_profile_id
    
    def soft_delete(self, user_id=None):
        """حذف منطقی مشاهده"""
        super().soft_delete(user_id)
    
    def restore(self):
        """بازیابی مشاهده از حذف منطقی"""
        super().restore()
    
    def validate(self):
        """اعتبارسنجی - فیلدهای ضروری"""
        errors = []
        
        # فیلدهای ضروری
        if not self.student_profile_id:
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        if not self.staff_id:
            errors.append("مشاهده‌گر باید انتخاب شود")
        if not self.observation_date:
            errors.append("تاریخ مشاهده نمی‌تواند خالی باشد")
        if not self.behavior or len(self.behavior.strip()) < 3:
            errors.append("رفتار مشاهده‌شده باید حداقل ۳ کاراکتر باشد")
        # (بازرسی شانزدهم) «توضیحات تکمیلی» در فرم اختیاری و زیر «فیلدهای
        # بیشتر» پنهان است؛ اجباری‌بودنش این‌جا باعث می‌شد ثبت مشاهده با
        # فیلدهای الزامیِ نمایان، با پیام «توضیحات باید حداقل ۳ کاراکتر
        # باشد» شکست بخورد. سرویس در نبود توضیحات، متن رفتار را در ستون
        # description (NOT NULL) می‌گذارد؛ اگر کاربر چیزی نوشت، کوتاه‌تر از
        # ۳ نویسه نباشد.
        if self.description and len(self.description.strip()) < 3:
            errors.append("توضیحات (در صورت ثبت) باید حداقل ۳ کاراکتر باشد")
        
        # فیلدهای اختیاری با اعتبارسنجی
        if self.severity and self.severity not in range(1, 6):
            errors.append("شدت باید بین 1 تا 5 باشد")
        if self.behavior_type and self.behavior_type not in self.BEHAVIOR_TYPES:
            errors.append("نوع رفتار نامعتبر است")
        
        return errors