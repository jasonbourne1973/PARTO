"""
مدل جلسه مشاوره تخصصی
ثبت و پیگیری جلسات مشاوره با دانش‌آموزان
"""

from typing import ClassVar

from models.base import BaseModel


class CounselingSession(BaseModel):
    """
    مدل جلسه مشاوره تخصصی
    
    ویژگی‌ها:
    - ثبت جلسات مشاوره فردی
    - پیگیری وضعیت جلسات
    - ثبت موضوعات و نتایج
    - برنامه‌ریزی جلسات آینده
    """
    
    # وضعیت‌های جلسه
    STATUS_SCHEDULED = "scheduled"      # برنامه‌ریزی شده
    STATUS_IN_PROGRESS = "in_progress"  # در حال انجام
    STATUS_COMPLETED = "completed"      # انجام شده
    STATUS_CANCELLED = "cancelled"      # لغو شده
    STATUS_NO_SHOW = "no_show"          # حضور نیافت
    
    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (STATUS_SCHEDULED, "برنامه‌ریزی شده"),
        (STATUS_IN_PROGRESS, "در حال انجام"),
        (STATUS_COMPLETED, "انجام شده"),
        (STATUS_CANCELLED, "لغو شده"),
        (STATUS_NO_SHOW, "حضور نیافت"),
    ]
    
    # نوع جلسه
    TYPE_INDIVIDUAL = "individual"      # فردی
    TYPE_GROUP = "group"                # گروهی
    TYPE_FAMILY = "family"              # خانوادگی
    TYPE_ASSESSMENT = "assessment"      # ارزیابی
    TYPE_FOLLOWUP = "followup"          # پیگیری
    
    TYPE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (TYPE_INDIVIDUAL, "فردی"),
        (TYPE_GROUP, "گروهی"),
        (TYPE_FAMILY, "خانوادگی"),
        (TYPE_ASSESSMENT, "ارزیابی"),
        (TYPE_FOLLOWUP, "پیگیری"),
    ]
    
    # روش جلسه
    METHOD_IN_PERSON = "in_person"      # حضوری
    METHOD_PHONE = "phone"              # تلفنی
    METHOD_VIDEO = "video"              # تصویری
    METHOD_OTHER = "other"              # سایر
    
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
        self.counselor_id = None         # ارجاع به Staff (مشاور)
        self.referred_by = None          # ارجاع به Staff (معرف‌کننده)
        
        # ===== اطلاعات جلسه =====
        self.session_date = None         # تاریخ جلسه (شمسی)
        self.session_time = None         # زمان جلسه
        self.duration_minutes = None     # مدت زمان (دقیقه)
        self.type = None                 # نوع جلسه
        self.method = None               # روش جلسه
        self.location = None             # مکان جلسه
        
        # ===== موضوع و محتوا =====
        self.topic = None                # موضوع جلسه
        self.goals = None                # اهداف جلسه (JSON)
        self.summary = None              # خلاصه جلسه
        self.details = None              # جزئیات کامل
        
        # ===== مداخلات و توصیه‌ها =====
        self.interventions_discussed = None  # مداخلات مطرح‌شده (JSON)
        self.recommendations = None      # توصیه‌ها (JSON)
        self.homework = None             # تکالیف (JSON)
        
        # ===== نتیجه =====
        self.outcome = None              # نتیجه جلسه
        self.follow_up_needed = False    # آیا نیاز به پیگیری دارد؟
        self.next_session_date = None    # تاریخ جلسه بعدی
        self.next_session_notes = None   # یادداشت جلسه بعدی
        
        # ===== وضعیت =====
        self.status = self.STATUS_SCHEDULED
        
        # ===== فیلدهای کمکی =====
        self.student_name = None
        self.counselor_name = None
        self.referred_by_name = None
    
    @property
    def status_display(self):
        """نمایش فارسی وضعیت جلسه"""
        status_map = {
            self.STATUS_SCHEDULED: "برنامه‌ریزی شده",
            self.STATUS_IN_PROGRESS: "در حال انجام",
            self.STATUS_COMPLETED: "انجام شده",
            self.STATUS_CANCELLED: "لغو شده",
            self.STATUS_NO_SHOW: "حضور نیافت",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def type_display(self):
        """نمایش فارسی نوع جلسه"""
        type_map = {
            self.TYPE_INDIVIDUAL: "فردی",
            self.TYPE_GROUP: "گروهی",
            self.TYPE_FAMILY: "خانوادگی",
            self.TYPE_ASSESSMENT: "ارزیابی",
            self.TYPE_FOLLOWUP: "پیگیری",
        }
        return type_map.get(self.type, self.type)
    
    @property
    def method_display(self):
        """نمایش فارسی روش جلسه"""
        method_map = {
            self.METHOD_IN_PERSON: "حضوری",
            self.METHOD_PHONE: "تلفنی",
            self.METHOD_VIDEO: "تصویری",
            self.METHOD_OTHER: "سایر",
        }
        return method_map.get(self.method, self.method)
    
    @property
    def is_completed(self):
        """آیا جلسه انجام شده است؟"""
        return self.status == self.STATUS_COMPLETED
    
    @property
    def is_scheduled(self):
        """آیا جلسه برنامه‌ریزی شده است؟"""
        return self.status == self.STATUS_SCHEDULED
    
    @property
    def is_cancelled(self):
        """آیا جلسه لغو شده است؟"""
        return self.status == self.STATUS_CANCELLED
    
    def complete(self, outcome=None):
        """تکمیل جلسه"""
        self.status = self.STATUS_COMPLETED
        if outcome:
            self.outcome = outcome
    
    def cancel(self, reason=None):
        """لغو جلسه"""
        self.status = self.STATUS_CANCELLED
        if reason:
            self.details = f"{self.details or ''}\n\nدلیل لغو: {reason}"
    
    def mark_no_show(self):
        """ثبت عدم حضور"""
        self.status = self.STATUS_NO_SHOW
    
    def validate(self):
        errors = []
        if not self.student_profile_id:
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        if not self.counselor_id:
            errors.append("مشاور باید انتخاب شود")
        if not self.session_date:
            errors.append("تاریخ جلسه نمی‌تواند خالی باشد")
        if self.type not in [t[0] for t in self.TYPE_CHOICES]:
            errors.append("نوع جلسه نامعتبر است")
        if self.method and self.method not in [m[0] for m in self.METHOD_CHOICES]:
            errors.append("روش جلسه نامعتبر است")
        if self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت جلسه نامعتبر است")
        return errors