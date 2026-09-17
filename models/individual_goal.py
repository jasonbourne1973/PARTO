"""
مدل هدف فردی دانش‌آموز
تعیین و پیگیری اهداف تربیتی و آموزشی برای هر دانش‌آموز
"""

from models.base import BaseModel


class IndividualGoal(BaseModel):
    """
    مدل هدف فردی دانش‌آموز
    
    ویژگی‌ها:
    - تعیین اهداف شخصی‌سازی‌شده برای هر دانش‌آموز
    - تعیین بازه زمانی برای هر هدف
    - پیگیری پیشرفت و وضعیت اهداف
    - ارتباط با شایستگی‌ها و مداخلات
    """
    
    # وضعیت‌های هدف
    STATUS_DRAFT = "draft"              # پیش‌نویس
    STATUS_ACTIVE = "active"            # فعال
    STATUS_IN_PROGRESS = "in_progress"  # در حال پیشرفت
    STATUS_COMPLETED = "completed"      # تکمیل شده
    STATUS_ACHIEVED = "achieved"        # محقق شده
    STATUS_ABANDONED = "abandoned"      # رها شده
    STATUS_REVIEW = "review"            # نیاز به بازبینی
    
    STATUS_CHOICES = [
        (STATUS_DRAFT, "پیش‌نویس"),
        (STATUS_ACTIVE, "فعال"),
        (STATUS_IN_PROGRESS, "در حال پیشرفت"),
        (STATUS_COMPLETED, "تکمیل شده"),
        (STATUS_ACHIEVED, "محقق شده"),
        (STATUS_ABANDONED, "رها شده"),
        (STATUS_REVIEW, "نیاز به بازبینی"),
    ]
    
    # اولویت هدف
    PRIORITY_HIGH = "high"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_LOW = "low"
    
    PRIORITY_CHOICES = [
        (PRIORITY_HIGH, "بالا"),
        (PRIORITY_MEDIUM, "متوسط"),
        (PRIORITY_LOW, "پایین"),
    ]
    
    # حوزه هدف
    DOMAIN_EDUCATIONAL = "educational"      # آموزشی
    DOMAIN_BEHAVIORAL = "behavioral"        # رفتاری
    DOMAIN_SOCIAL = "social"                # اجتماعی
    DOMAIN_EMOTIONAL = "emotional"          # عاطفی-هیجانی
    DOMAIN_MORAL = "moral"                  # اخلاقی
    DOMAIN_SKILL = "skill"                  # مهارتی
    DOMAIN_OTHER = "other"                  # سایر
    
    DOMAIN_CHOICES = [
        (DOMAIN_EDUCATIONAL, "آموزشی"),
        (DOMAIN_BEHAVIORAL, "رفتاری"),
        (DOMAIN_SOCIAL, "اجتماعی"),
        (DOMAIN_EMOTIONAL, "عاطفی-هیجانی"),
        (DOMAIN_MORAL, "اخلاقی"),
        (DOMAIN_SKILL, "مهارتی"),
        (DOMAIN_OTHER, "سایر"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.student_profile_id = None   # ارجاع به StudentAcademicProfile
        self.created_by = None           # ارجاع به Staff (ایجادکننده)
        self.assigned_to = None          # ارجاع به Staff (مسئول پیگیری)
        self.related_competency_id = None # ارجاع به Competency
        self.related_intervention_id = None # ارجاع به Intervention
        
        # ===== اطلاعات هدف =====
        self.title = None                # عنوان هدف
        self.description = None          # توضیحات هدف
        self.domain = None               # حوزه هدف
        self.priority = None             # اولویت
        
        # ===== معیارهای موفقیت =====
        self.success_criteria = None     # معیارهای موفقیت (JSON)
        self.target_date = None          # تاریخ هدف (شمسی)
        self.start_date = None           # تاریخ شروع (شمسی)
        self.end_date = None             # تاریخ پایان (شمسی)
        
        # ===== پیشرفت =====
        self.progress_percent = 0        # درصد پیشرفت (0-100)
        self.progress_notes = None       # یادداشت‌های پیشرفت
        
        # ===== وضعیت =====
        self.status = self.STATUS_DRAFT
        
        # ===== نتیجه =====
        self.result = None               # نتیجه نهایی
        self.achievement_date = None     # تاریخ دستیابی
        
        # ===== فیلدهای کمکی =====
        self.student_name = None
        self.created_by_name = None
        self.assigned_to_name = None
        self.competency_name = None
    
    @property
    def status_display(self):
        """نمایش فارسی وضعیت هدف"""
        status_map = {
            self.STATUS_DRAFT: "پیش‌نویس",
            self.STATUS_ACTIVE: "فعال",
            self.STATUS_IN_PROGRESS: "در حال پیشرفت",
            self.STATUS_COMPLETED: "تکمیل شده",
            self.STATUS_ACHIEVED: "محقق شده",
            self.STATUS_ABANDONED: "رها شده",
            self.STATUS_REVIEW: "نیاز به بازبینی",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def priority_display(self):
        """نمایش فارسی اولویت هدف"""
        priority_map = {
            self.PRIORITY_HIGH: "🔴 بالا",
            self.PRIORITY_MEDIUM: "🟡 متوسط",
            self.PRIORITY_LOW: "🟢 پایین",
        }
        return priority_map.get(self.priority, self.priority)
    
    @property
    def priority_color(self):
        """رنگ اولویت"""
        colors = {
            self.PRIORITY_HIGH: "#DC2626",
            self.PRIORITY_MEDIUM: "#F59E0B",
            self.PRIORITY_LOW: "#22C55E",
        }
        return colors.get(self.priority, "#F59E0B")
    
    @property
    def domain_display(self):
        """نمایش فارسی حوزه هدف"""
        domain_map = {
            self.DOMAIN_EDUCATIONAL: "آموزشی",
            self.DOMAIN_BEHAVIORAL: "رفتاری",
            self.DOMAIN_SOCIAL: "اجتماعی",
            self.DOMAIN_EMOTIONAL: "عاطفی-هیجانی",
            self.DOMAIN_MORAL: "اخلاقی",
            self.DOMAIN_SKILL: "مهارتی",
            self.DOMAIN_OTHER: "سایر",
        }
        return domain_map.get(self.domain, self.domain)
    
    @property
    def is_active_goal(self):
        """آیا هدف فعال است؟"""
        return self.status in [self.STATUS_ACTIVE, self.STATUS_IN_PROGRESS]
    
    @property
    def is_achieved(self):
        """آیا هدف محقق شده است؟"""
        return self.status in [self.STATUS_ACHIEVED, self.STATUS_COMPLETED]
    
    @property
    def progress_status(self):
        """وضعیت پیشرفت"""
        if self.progress_percent == 0:
            return "شروع نشده"
        elif self.progress_percent < 30:
            return "شروع شده"
        elif self.progress_percent < 70:
            return "در حال پیشرفت"
        elif self.progress_percent < 100:
            return "نزدیک به اتمام"
        else:
            return "تکمیل شده"
    
    def update_progress(self, percent, notes=None):
        """به‌روزرسانی پیشرفت"""
        self.progress_percent = max(0, min(100, percent))
        if notes:
            self.progress_notes = notes
        
        # به‌روزرسانی وضعیت بر اساس پیشرفت
        if self.progress_percent >= 100:
            self.status = self.STATUS_COMPLETED
        elif self.progress_percent > 0 and self.status == self.STATUS_ACTIVE:
            self.status = self.STATUS_IN_PROGRESS
    
    def achieve(self, result=None):
        """ثبت دستیابی به هدف"""
        self.status = self.STATUS_ACHIEVED
        self.progress_percent = 100
        if result:
            self.result = result
        from datetime import datetime
        self.achievement_date = datetime.now().isoformat()
    
    def validate(self):
        errors = []
        if not self.student_profile_id:
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        if not self.title or len(self.title.strip()) < 2:
            errors.append("عنوان هدف باید حداقل ۲ کاراکتر باشد")
        if self.priority and self.priority not in [p[0] for p in self.PRIORITY_CHOICES]:
            errors.append("اولویت هدف نامعتبر است")
        if self.domain and self.domain not in [d[0] for d in self.DOMAIN_CHOICES]:
            errors.append("حوزه هدف نامعتبر است")
        if self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت هدف نامعتبر است")
        if self.progress_percent and (self.progress_percent < 0 or self.progress_percent > 100):
            errors.append("درصد پیشرفت باید بین 0 تا 100 باشد")
        return errors