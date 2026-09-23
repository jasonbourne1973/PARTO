"""
مدل مصاحبه با والدین (Parent Interview)
"""

from typing import ClassVar

from models.base import BaseModel


class ParentInterview(BaseModel):
    """
    مدل مصاحبه با والدین
    
    ثبت ساختاریافته مصاحبه‌های انجام‌شده با والدین دانش‌آموز
    """
    
    # وضعیت‌های مصاحبه
    STATUS_SCHEDULED = "scheduled"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_NO_SHOW = "no_show"
    
    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (STATUS_SCHEDULED, "برنامه‌ریزی شده"),
        (STATUS_COMPLETED, "انجام شده"),
        (STATUS_CANCELLED, "لغو شده"),
        (STATUS_NO_SHOW, "حضور نیافت"),
    ]
    
    # روش‌های مصاحبه
    METHOD_IN_PERSON = "in_person"
    METHOD_PHONE = "phone"
    METHOD_VIDEO = "video"
    METHOD_OTHER = "other"
    
    METHOD_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (METHOD_IN_PERSON, "حضوری"),
        (METHOD_PHONE, "تلفنی"),
        (METHOD_VIDEO, "تصویری"),
        (METHOD_OTHER, "سایر"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.student_profile_id = None   # ارجاع به StudentAcademicProfile
        self.staff_id = None             # ارجاع به Staff (مصاحبه‌کننده)
        
        # ===== اطلاعات مصاحبه =====
        self.interview_date = None       # تاریخ مصاحبه (شمسی)
        self.interview_method = None     # از METHOD_CHOICES
        self.interviewer_name = None     # نام مصاحبه‌کننده
        
        # ===== اطلاعات والدین =====
        self.parent_name = None          # نام والد مصاحبه‌شونده
        self.parent_relation = None      # نسبت با دانش‌آموز (پدر، مادر، ...)
        self.parent_phone = None         # تلفن والد
        
        # ===== موضوع مصاحبه =====
        self.topic = None                # موضوع اصلی مصاحبه
        self.topic_category = None       # دسته‌بندی موضوع (آموزشی، رفتاری، ...)
        
        # ===== محتوای مصاحبه =====
        self.summary = None              # خلاصه گفت‌وگو
        self.details = None              # جزئیات کامل (اختیاری)
        self.key_points = None           # نکات کلیدی (JSON)
        
        # ===== نتیجه مصاحبه =====
        self.result = None               # نتیجه کلی
        self.outcome_notes = None        # یادداشت‌های نتیجه
        
        # ===== اقدام بعدی =====
        self.next_action = None          # اقدام بعدی
        self.next_action_date = None     # تاریخ اقدام بعدی
        self.next_action_by = None       # مسئول اقدام بعدی
        
        # ===== وضعیت =====
        self.status = self.STATUS_SCHEDULED
        
        # ===== فیلدهای کمکی =====
        self.student_name = None
        self.staff_name = None
    
    @property
    def status_display(self):
        """نمایش فارسی وضعیت مصاحبه"""
        status_map = {
            self.STATUS_SCHEDULED: "برنامه‌ریزی شده",
            self.STATUS_COMPLETED: "انجام شده",
            self.STATUS_CANCELLED: "لغو شده",
            self.STATUS_NO_SHOW: "حضور نیافت",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def method_display(self):
        """نمایش فارسی روش مصاحبه"""
        method_map = {
            self.METHOD_IN_PERSON: "حضوری",
            self.METHOD_PHONE: "تلفنی",
            self.METHOD_VIDEO: "تصویری",
            self.METHOD_OTHER: "سایر",
        }
        return method_map.get(self.interview_method, self.interview_method or "ثبت نشده")
    
    @property
    def is_completed(self):
        """آیا مصاحبه انجام شده است؟"""
        return self.status == self.STATUS_COMPLETED
    
    @property
    def is_scheduled(self):
        """آیا مصاحبه برنامه‌ریزی شده است؟"""
        return self.status == self.STATUS_SCHEDULED
    
    def to_dict(self):
        """تبدیل به دیکشنری برای نمایش"""
        return {
            'date': self.interview_date,
            'method': self.method_display,
            'parent_name': self.parent_name,
            'parent_relation': self.parent_relation,
            'topic': self.topic,
            'summary': self.summary,
            'result': self.result,
            'next_action': self.next_action,
            'next_action_date': self.next_action_date,
            'status': self.status_display,
        }
    
    def validate(self):
        errors = []
        if not self.student_profile_id:
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        if not self.staff_id:
            errors.append("مصاحبه‌کننده باید انتخاب شود")
        if not self.interview_date:
            errors.append("تاریخ مصاحبه نمی‌تواند خالی باشد")
        if not self.parent_name or len(self.parent_name.strip()) < 2:
            errors.append("نام والد باید حداقل ۲ کاراکتر باشد")
        if not self.topic or len(self.topic.strip()) < 3:
            errors.append("موضوع مصاحبه باید حداقل ۳ کاراکتر باشد")
        if self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت مصاحبه نامعتبر است")
        if self.interview_method and self.interview_method not in [m[0] for m in self.METHOD_CHOICES]:
            errors.append("روش مصاحبه نامعتبر است")
        return errors