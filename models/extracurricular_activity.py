"""
مدل فعالیت فوق‌برنامه
ثبت مشارکت دانش‌آموزان در فعالیت‌های فرهنگی، هنری، ورزشی و مذهبی
"""

from typing import ClassVar

from models.base import BaseModel


class ExtracurricularActivity(BaseModel):
    """
    مدل فعالیت فوق‌برنامه
    
    ویژگی‌ها:
    - ثبت فعالیت‌های فرهنگی، هنری، ورزشی و مذهبی
    - ثبت تاریخ و مدت زمان فعالیت
    - ثبت سطح مشارکت و نتیجه
    - ثبت نقش دانش‌آموز در فعالیت
    """
    
    # نوع فعالیت
    TYPE_CULTURAL = "cultural"          # فرهنگی
    TYPE_ART = "art"                    # هنری
    TYPE_SPORT = "sport"                # ورزشی
    TYPE_RELIGIOUS = "religious"        # مذهبی
    TYPE_SCIENTIFIC = "scientific"      # علمی
    TYPE_SOCIAL = "social"              # اجتماعی
    TYPE_VOLUNTEER = "volunteer"        # داوطلبانه
    TYPE_OTHER = "other"                # سایر
    
    TYPE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (TYPE_CULTURAL, "فرهنگی"),
        (TYPE_ART, "هنری"),
        (TYPE_SPORT, "ورزشی"),
        (TYPE_RELIGIOUS, "مذهبی"),
        (TYPE_SCIENTIFIC, "علمی"),
        (TYPE_SOCIAL, "اجتماعی"),
        (TYPE_VOLUNTEER, "داوطلبانه"),
        (TYPE_OTHER, "سایر"),
    ]
    
    # سطح مشارکت
    LEVEL_PARTICIPANT = "participant"   # شرکت‌کننده
    LEVEL_ACTIVE = "active"             # فعال
    LEVEL_LEADER = "leader"             # رهبر/مسئول
    LEVEL_ORGANIZER = "organizer"       # سازمان‌دهنده
    
    LEVEL_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (LEVEL_PARTICIPANT, "شرکت‌کننده"),
        (LEVEL_ACTIVE, "فعال"),
        (LEVEL_LEADER, "رهبر/مسئول"),
        (LEVEL_ORGANIZER, "سازمان‌دهنده"),
    ]
    
    # وضعیت فعالیت
    STATUS_PLANNED = "planned"          # برنامه‌ریزی شده
    STATUS_IN_PROGRESS = "in_progress"  # در حال اجرا
    STATUS_COMPLETED = "completed"      # انجام شده
    STATUS_CANCELLED = "cancelled"      # لغو شده
    
    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (STATUS_PLANNED, "برنامه‌ریزی شده"),
        (STATUS_IN_PROGRESS, "در حال اجرا"),
        (STATUS_COMPLETED, "انجام شده"),
        (STATUS_CANCELLED, "لغو شده"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.student_profile_id = None   # ارجاع به StudentAcademicProfile
        self.teacher_id = None           # ارجاع به Staff (معلم مسئول)
        
        # ===== اطلاعات فعالیت =====
        self.title = None                # عنوان فعالیت
        self.type = None                 # نوع فعالیت
        self.description = None          # توضیحات فعالیت
        
        # ===== تاریخ و زمان =====
        self.start_date = None           # تاریخ شروع (شمسی)
        self.end_date = None             # تاریخ پایان (شمسی)
        self.duration_hours = None       # مدت زمان (ساعت)
        
        # ===== مکان =====
        self.location = None             # مکان برگزاری
        
        # ===== مشارکت =====
        self.participation_level = None  # سطح مشارکت
        self.role = None                 # نقش دانش‌آموز
        self.team_name = None            # نام تیم/گروه
        
        # ===== نتیجه =====
        self.result = None               # نتیجه فعالیت
        self.achievements = None         # دستاوردها (JSON)
        self.feedback = None             # بازخورد
        
        # ===== وضعیت =====
        self.status = self.STATUS_PLANNED
        
        # ===== فیلدهای کمکی =====
        self.student_name = None
        self.teacher_name = None
    
    @property
    def type_display(self):
        """نمایش فارسی نوع فعالیت"""
        type_map = {
            self.TYPE_CULTURAL: "فرهنگی",
            self.TYPE_ART: "هنری",
            self.TYPE_SPORT: "ورزشی",
            self.TYPE_RELIGIOUS: "مذهبی",
            self.TYPE_SCIENTIFIC: "علمی",
            self.TYPE_SOCIAL: "اجتماعی",
            self.TYPE_VOLUNTEER: "داوطلبانه",
            self.TYPE_OTHER: "سایر",
        }
        return type_map.get(self.type, self.type)
    
    @property
    def status_display(self):
        """نمایش فارسی وضعیت فعالیت"""
        status_map = {
            self.STATUS_PLANNED: "برنامه‌ریزی شده",
            self.STATUS_IN_PROGRESS: "در حال اجرا",
            self.STATUS_COMPLETED: "انجام شده",
            self.STATUS_CANCELLED: "لغو شده",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def level_display(self):
        """نمایش فارسی سطح مشارکت"""
        level_map = {
            self.LEVEL_PARTICIPANT: "شرکت‌کننده",
            self.LEVEL_ACTIVE: "فعال",
            self.LEVEL_LEADER: "رهبر/مسئول",
            self.LEVEL_ORGANIZER: "سازمان‌دهنده",
        }
        return level_map.get(self.participation_level, self.participation_level)
    
    @property
    def is_completed(self):
        """آیا فعالیت انجام شده است؟"""
        return self.status == self.STATUS_COMPLETED
    
    @property
    def is_active(self):
        """آیا فعالیت فعال است؟"""
        return self.status in [self.STATUS_PLANNED, self.STATUS_IN_PROGRESS]
    
    @property
    def icon(self):
        """دریافت آیکون مناسب برای نوع فعالیت"""
        icon_map = {
            self.TYPE_CULTURAL: "🎭",
            self.TYPE_ART: "🎨",
            self.TYPE_SPORT: "⚽",
            self.TYPE_RELIGIOUS: "🕌",
            self.TYPE_SCIENTIFIC: "🔬",
            self.TYPE_SOCIAL: "🤝",
            self.TYPE_VOLUNTEER: "❤️",
            self.TYPE_OTHER: "📌",
        }
        return icon_map.get(self.type, "📌")
    
    def complete(self, result=None, achievements=None):
        """تکمیل فعالیت"""
        self.status = self.STATUS_COMPLETED
        if result:
            self.result = result
        if achievements:
            self.achievements = achievements
    
    def cancel(self, reason=None):
        """لغو فعالیت"""
        self.status = self.STATUS_CANCELLED
        if reason:
            self.feedback = reason
    
    def validate(self):
        errors = []
        if not self.student_profile_id:
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        if not self.title or len(self.title.strip()) < 2:
            errors.append("عنوان فعالیت باید حداقل ۲ کاراکتر باشد")
        if not self.type:
            errors.append("نوع فعالیت باید انتخاب شود")
        if self.type and self.type not in [t[0] for t in self.TYPE_CHOICES]:
            errors.append("نوع فعالیت نامعتبر است")
        if self.participation_level and self.participation_level not in [l[0] for l in self.LEVEL_CHOICES]:
            errors.append("سطح مشارکت نامعتبر است")
        if self.status and self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت فعالیت نامعتبر است")
        if not self.start_date:
            errors.append("تاریخ شروع نمی‌تواند خالی باشد")
        return errors