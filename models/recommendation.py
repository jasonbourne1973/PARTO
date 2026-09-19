"""
مدل پیشنهادات - ذخیره پیشنهادات تولیدشده در دیتابیس
"""

from utils.time_utils import utc_now_iso

from models.base import BaseModel


class Recommendation(BaseModel):
    """
    مدل پیشنهادات - ذخیره‌سازی پیشنهادات تولیدشده
    
    ویژگی‌ها:
    - ذخیره پیشنهادات برای هر دانش‌آموز
    - ثبت وضعیت اجرا
    - ثبت بازخورد
    - تاریخچه پیشنهادات
    """
    
    # وضعیت‌های پیشنهاد
    STATUS_PENDING = "pending"          # در انتظار بررسی
    STATUS_ACCEPTED = "accepted"        # پذیرفته شده
    STATUS_REJECTED = "rejected"        # رد شده
    STATUS_IMPLEMENTED = "implemented"  # اجرا شده
    STATUS_COMPLETED = "completed"      # تکمیل شده
    STATUS_ARCHIVED = "archived"        # بایگانی شده
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "در انتظار بررسی"),
        (STATUS_ACCEPTED, "پذیرفته شده"),
        (STATUS_REJECTED, "رد شده"),
        (STATUS_IMPLEMENTED, "اجرا شده"),
        (STATUS_COMPLETED, "تکمیل شده"),
        (STATUS_ARCHIVED, "بایگانی شده"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.student_profile_id = None   # ارجاع به StudentAcademicProfile
        self.staff_id = None             # ارجاع به Staff (تولیدکننده یا مسئول)
        
        # ===== اطلاعات پیشنهاد =====
        self.rule_id = None              # شناسه قانون اعمال‌شده
        self.category = None             # دسته‌بندی پیشنهاد
        self.priority = None             # اولویت (critical/high/medium/low)
        self.title = None                # عنوان پیشنهاد
        self.description = None          # توضیحات پیشنهاد
        self.suggested_action = None     # اقدام پیشنهادی
        self.suggested_intervention_type = None  # نوع مداخله پیشنهادی
        
        # ===== اطلاعات مرتبط =====
        self.related_competency_id = None    # شناسه شایستگی مرتبط
        self.related_observation_ids = None  # شناسه مشاهدات مرتبط (JSON)
        self.score = 0                       # امتیاز اهمیت (0-100)
        self.metadata = None                 # اطلاعات اضافی (JSON)
        
        # ===== وضعیت =====
        self.status = self.STATUS_PENDING
        self.implemented_at = None       # تاریخ اجرا
        self.completed_at = None         # تاریخ تکمیل
        self.feedback = None             # بازخورد
        self.feedback_notes = None       # یادداشت بازخورد
        
        # ===== فیلدهای کمکی =====
        self.student_name = None
        self.staff_name = None
        self.competency_name = None
    
    @property
    def status_display(self):
        """نمایش فارسی وضعیت"""
        status_map = {
            self.STATUS_PENDING: "در انتظار بررسی",
            self.STATUS_ACCEPTED: "پذیرفته شده",
            self.STATUS_REJECTED: "رد شده",
            self.STATUS_IMPLEMENTED: "اجرا شده",
            self.STATUS_COMPLETED: "تکمیل شده",
            self.STATUS_ARCHIVED: "بایگانی شده",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def priority_display(self):
        """نمایش فارسی اولویت"""
        priority_map = {
            "critical": "🔴 بحرانی",
            "high": "🟠 بالا",
            "medium": "🟡 متوسط",
            "low": "🟢 پایین"
        }
        return priority_map.get(self.priority, self.priority)
    
    @property
    def category_display(self):
        """نمایش فارسی دسته‌بندی"""
        category_map = {
            "intervention": "🛠️ مداخله",
            "encouragement": "⭐ تشویق",
            "followup": "🔔 پیگیری",
            "support": "🫂 حمایت",
            "referral": "📋 ارجاع",
            "observation": "📝 مشاهده"
        }
        return category_map.get(self.category, self.category)
    
    @property
    def is_pending(self):
        """آیا پیشنهاد در انتظار است؟"""
        return self.status == self.STATUS_PENDING
    
    @property
    def is_implemented(self):
        """آیا پیشنهاد اجرا شده است؟"""
        return self.status in [self.STATUS_IMPLEMENTED, self.STATUS_COMPLETED]
    
    def accept(self):
        """پذیرش پیشنهاد"""
        self.status = self.STATUS_ACCEPTED
    
    def reject(self, notes=None):
        """رد پیشنهاد"""
        self.status = self.STATUS_REJECTED
        if notes:
            self.feedback_notes = notes
    
    def implement(self):
        """اجرای پیشنهاد"""
        self.status = self.STATUS_IMPLEMENTED
        self.implemented_at = utc_now_iso()
    
    def complete(self, feedback=None):
        """تکمیل پیشنهاد"""
        self.status = self.STATUS_COMPLETED
        self.completed_at = utc_now_iso()
        if feedback:
            self.feedback = feedback
    
    def validate(self):
        errors = []
        if not self.student_profile_id:
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        if not self.rule_id:
            errors.append("شناسه قانون باید مشخص شود")
        if not self.title or len(self.title.strip()) < 3:
            errors.append("عنوان پیشنهاد باید حداقل ۳ کاراکتر باشد")
        if not self.description or len(self.description.strip()) < 5:
            errors.append("توضیحات پیشنهاد باید حداقل ۵ کاراکتر باشد")
        if self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت پیشنهاد نامعتبر است")
        return errors