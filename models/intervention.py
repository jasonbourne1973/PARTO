"""
مدل مداخله - با Soft Delete یکپارچه
"""

from typing import ClassVar

from models.base import BaseModel


class Intervention(BaseModel):
    """
    مدل مداخله تربیتی با Soft Delete یکپارچه
    
    چرخه: Observation → Intervention → FollowUp → Outcome
    """
    
    # وضعیت‌های مداخله
    STATUS_PLANNED = "planned"      # برنامه‌ریزی شده
    STATUS_IN_PROGRESS = "in_progress"  # در حال اجرا
    STATUS_DONE = "done"            # انجام شده
    STATUS_COMPLETED = "completed"  # تکمیل شده
    STATUS_CANCELLED = "cancelled"  # لغو شده
    
    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (STATUS_PLANNED, "برنامه‌ریزی شده"),
        (STATUS_IN_PROGRESS, "در حال اجرا"),
        (STATUS_DONE, "انجام شده"),
        (STATUS_COMPLETED, "تکمیل شده"),
        (STATUS_CANCELLED, "لغو شده"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.student_profile_id = None   # ارجاع به StudentAcademicProfile
        self.staff_id = None             # ارجاع به Staff (مسئول مداخله)
        self.observation_id = None       # ارجاع به Observation (اختیاری)
        
        # ===== اطلاعات اصلی =====
        self.type = None                 # نوع مداخله (از constants)
        self.date = None                 # تاریخ مداخله (شمسی)
        self.description = None          # شرح کامل مداخله
        self.goal = None                 # هدف مداخله
        
        # ===== وضعیت و نتیجه =====
        self.status = self.STATUS_PLANNED  # وضعیت مداخله
        self.result = None               # نتیجه مداخله
        
        # ===== فیلدهای کمکی برای نمایش =====
        self.student_name = None
        self.staff_name = None
        self.observation_date = None
    
    @property
    def type_display(self):
        """نمایش نوع مداخله به فارسی"""
        type_map = {
            "individual_talk": "گفتگوی فردی",
            "group_talk": "گفتگوی گروهی",
            "parent_call": "تماس با والدین",
            "parent_meeting": "جلسه با والدین",
            "responsibility": "سپردن مسئولیت",
            "encouragement": "تشویق",
            "group_activity": "فعالیت گروهی",
            "educational_game": "بازی تربیتی",
            "referral": "ارجاع به مشاور",
            "counseling": "مشاوره",
            "seat_change": "تغییر جای نشستن",
            "peer_helper": "همیار دانش‌آموز",
            "warning": "تذکر شفاهی",
            "other": "سایر"
        }
        return type_map.get(self.type, self.type or "نامشخص")
    
    @property
    def status_display(self):
        """نمایش وضعیت به فارسی (بدون Emoji)"""
        status_map = {
            self.STATUS_PLANNED: "برنامه‌ریزی شده",
            self.STATUS_IN_PROGRESS: "در حال اجرا",
            self.STATUS_DONE: "انجام شده",
            self.STATUS_COMPLETED: "تکمیل شده",
            self.STATUS_CANCELLED: "لغو شده",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def is_active_intervention(self):
        """آیا مداخله فعال است؟"""
        return self.status in [self.STATUS_PLANNED, self.STATUS_IN_PROGRESS]
    
    @property
    def is_completed(self):
        """آیا مداخله تکمیل شده است؟"""
        return self.status in [self.STATUS_COMPLETED, self.STATUS_DONE]
    
    def soft_delete(self, user_id=None):
        """حذف منطقی مداخله"""
        super().soft_delete(user_id)
    
    def restore(self):
        """بازیابی مداخله از حذف منطقی"""
        super().restore()
    
    def validate(self):
        errors = []
        if not self.student_profile_id:
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        if not self.staff_id:
            errors.append("مسئول مداخله باید انتخاب شود")
        if not self.type:
            errors.append("نوع مداخله باید انتخاب شود")
        if not self.description or len(self.description.strip()) < 3:
            errors.append("توضیحات باید حداقل ۳ کاراکتر باشد")
        if not self.date:
            errors.append("تاریخ مداخله نمی‌تواند خالی باشد")
        if self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت مداخله نامعتبر است")
        return errors