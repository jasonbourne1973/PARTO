"""
مدل اطلاعات زمینه‌ای خانواده (Family Context)
"""

from typing import ClassVar

from models.base import BaseModel


class FamilyContext(BaseModel):
    """
    مدل اطلاعات زمینه‌ای خانواده دانش‌آموز
    
    این مدل اطلاعات لازم برای حمایت آموزشی و تربیتی را ثبت می‌کند.
    اطلاعات باید در حد نیاز مدرسه باشد و از جمع‌آوری اطلاعات غیرضروری خودداری شود.
    """
    
    # وضعیت‌های سرپرستی
    GUARDIAN_BOTH = "both"
    GUARDIAN_MOTHER = "mother"
    GUARDIAN_FATHER = "father"
    GUARDIAN_GRANDPARENTS = "grandparents"
    GUARDIAN_OTHER = "other"
    
    GUARDIAN_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (GUARDIAN_BOTH, "هر دو والدین"),
        (GUARDIAN_MOTHER, "فقط مادر"),
        (GUARDIAN_FATHER, "فقط پدر"),
        (GUARDIAN_GRANDPARENTS, "پدربزرگ و مادربزرگ"),
        (GUARDIAN_OTHER, "سایر"),
    ]

    # ===== نگاشت «وضعیت زندگی» فرم دانش‌آموز به همان ستون guardian_status =====
    # (بازبینی نهایی — رفع BUG-GUI-02)
    # فرم ثبت/ویرایش دانش‌آموز فیلد «وضعیت زندگی» را با متن‌های
    # config.constants.LIVING_STATUSES نشان می‌دهد. همان مفهوم با کدهای
    # GUARDIAN_CHOICES در family_contexts.guardian_status ذخیره می‌شود؛
    # پس هیچ ستون/جدول تازه‌ای لازم نیست و دادهٔ خانواده در جای
    # قانونی خودش (زمینهٔ خانوادگی هر پرونده) می‌ماند.
    LIVING_STATUS_MAP: ClassVar[dict] = {
        "با هر دو والدین": GUARDIAN_BOTH,
        "فقط با مادر": GUARDIAN_MOTHER,
        "فقط با پدر": GUARDIAN_FATHER,
        "با پدربزرگ و مادربزرگ": GUARDIAN_GRANDPARENTS,
        "سایر": GUARDIAN_OTHER,
    }
    GUARDIAN_TO_LIVING_STATUS: ClassVar[dict] = {
        code: label for label, code in LIVING_STATUS_MAP.items()
    }
    
    # وضعیت‌های ارتباط با مدرسه
    CONTACT_GOOD = "good"
    CONTACT_MODERATE = "moderate"
    CONTACT_POOR = "poor"
    CONTACT_IRREGULAR = "irregular"
    
    CONTACT_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (CONTACT_GOOD, "خوب و مستمر"),
        (CONTACT_MODERATE, "متوسط"),
        (CONTACT_POOR, "ضعیف"),
        (CONTACT_IRREGULAR, "نامنظم"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.student_profile_id = None   # ارجاع به StudentAcademicProfile
        
        # ===== وضعیت سرپرستی =====
        self.guardian_status = None      # از GUARDIAN_CHOICES
        self.guardian_notes = None       # توضیحات تکمیلی سرپرستی
        
        # ===== ترکیب خانواده =====
        self.siblings_brothers = 0       # تعداد برادران
        self.siblings_sisters = 0        # تعداد خواهران
        self.family_members = 0          # تعداد کل اعضای خانواده (اختیاری)
        
        # ===== وضعیت ارتباط با مدرسه =====
        self.school_contact = None       # از CONTACT_CHOICES
        self.contact_details = None      # جزئیات ارتباط
        
        # ===== شرایط آموزشی منزل =====
        self.has_study_space = False     # آیا فضای مطالعه دارد؟
        self.has_desk = False            # آیا میز تحریر دارد؟
        self.parental_support = None     # سطح حمایت والدین (low/medium/high)
        self.educational_notes = None    # یادداشت‌های آموزشی
        
        # ===== عوامل مؤثر بر وضعیت آموزشی/تربیتی =====
        self.economic_status = None      # وضعیت اقتصادی (low/medium/high)
        self.economic_notes = None       # توضیحات اقتصادی
        self.family_stress = None        # استرس‌های خانوادگی
        self.health_issues = None        # مسائل سلامتی در خانواده
        self.other_factors = None        # سایر عوامل
        
        # ===== یادداشت‌های مرتبط =====
        self.notes = None                # یادداشت‌های عمومی
        
        # ===== تاریخ ثبت =====
        self.recorded_by = None          # شناسه ثبت‌کننده
        self.recorded_by_name = None     # نام ثبت‌کننده (برای نمایش)
    
    @property
    def guardian_status_display(self):
        """نمایش فارسی وضعیت سرپرستی"""
        status_map = {
            self.GUARDIAN_BOTH: "هر دو والدین",
            self.GUARDIAN_MOTHER: "فقط مادر",
            self.GUARDIAN_FATHER: "فقط پدر",
            self.GUARDIAN_GRANDPARENTS: "پدربزرگ و مادربزرگ",
            self.GUARDIAN_OTHER: "سایر",
        }
        return status_map.get(self.guardian_status, self.guardian_status or "ثبت نشده")
    
    @property
    def school_contact_display(self):
        """نمایش فارسی وضعیت ارتباط با مدرسه"""
        contact_map = {
            self.CONTACT_GOOD: "خوب و مستمر",
            self.CONTACT_MODERATE: "متوسط",
            self.CONTACT_POOR: "ضعیف",
            self.CONTACT_IRREGULAR: "نامنظم",
        }
        return contact_map.get(self.school_contact, self.school_contact or "ثبت نشده")
    
    @property
    def siblings_count(self):
        """تعداد کل خواهر و برادر"""
        return (self.siblings_brothers or 0) + (self.siblings_sisters or 0)

    @property
    def living_status(self):
        """
        «وضعیت زندگی با والدین» به‌صورت متنِ فرم (LIVING_STATUSES)

        همان مقدار guardian_status است که برای نمایش در فرم دانش‌آموز به
        متن فارسی برگردانده می‌شود. اگر دادهٔ قدیمی متن باشد، خودش
        برگردانده می‌شود تا چیزی «ناشناخته» نشود.
        """
        if not self.guardian_status:
            return None
        if self.guardian_status in self.GUARDIAN_TO_LIVING_STATUS:
            return self.GUARDIAN_TO_LIVING_STATUS[self.guardian_status]
        return self.guardian_status

    @living_status.setter
    def living_status(self, value):
        """
        تنظیم «وضعیت زندگی» با متن فرم

        مقدار خالی/ناموجود → دست‌نخورده ماندن مقدار فعلی (هیچ داده‌ای پاک
        نمی‌شود). اگر متن ناشناخته باشد، همان‌طور ذخیره می‌شود تا کاربر
        داده‌اش را از دست ندهد، ولی نگاشت معکوس فقط برای کدهای شناخته‌شده
        انجام می‌شود.
        """
        if value is None or str(value).strip() == "":
            return
        text = str(value).strip()
        self.guardian_status = self.LIVING_STATUS_MAP.get(text, text)
    
    def to_dict(self):
        """تبدیل به دیکشنری برای نمایش"""
        return {
            'guardian_status': self.guardian_status_display,
            'guardian_notes': self.guardian_notes,
            'siblings_brothers': self.siblings_brothers,
            'siblings_sisters': self.siblings_sisters,
            'siblings_count': self.siblings_count,
            'school_contact': self.school_contact_display,
            'contact_details': self.contact_details,
            'has_study_space': "بله" if self.has_study_space else "خیر",
            'has_desk': "بله" if self.has_desk else "خیر",
            'parental_support': self.parental_support,
            'educational_notes': self.educational_notes,
            'economic_status': self.economic_status,
            'family_stress': self.family_stress,
            'health_issues': self.health_issues,
            'other_factors': self.other_factors,
            'notes': self.notes,
        }
    
    def validate(self):
        errors = []
        if not self.student_profile_id:
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        if self.guardian_status and self.guardian_status not in [g[0] for g in self.GUARDIAN_CHOICES]:
            errors.append("وضعیت سرپرستی نامعتبر است")
        if self.school_contact and self.school_contact not in [c[0] for c in self.CONTACT_CHOICES]:
            errors.append("وضعیت ارتباط با مدرسه نامعتبر است")
        if self.siblings_brothers and self.siblings_brothers < 0:
            errors.append("تعداد برادران نمی‌تواند منفی باشد")
        if self.siblings_sisters and self.siblings_sisters < 0:
            errors.append("تعداد خواهران نمی‌تواند منفی باشد")
        return errors