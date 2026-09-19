"""
مدل پیگیری - با Soft Delete یکپارچه
"""

from typing import ClassVar

from models.base import BaseModel


class FollowUp(BaseModel):
    """
    مدل پیگیری با Soft Delete یکپارچه
    
    چرخه: Intervention → FollowUp → Outcome → Observation مجدد
    """
    
    # وضعیت‌های پیگیری
    STATUS_PENDING = "pending"       # در انتظار
    STATUS_DONE = "done"             # انجام شده
    STATUS_CONTINUED = "continued"   # نیازمند ادامه
    STATUS_CLOSED = "closed"         # مختومه
    STATUS_CANCELLED = "cancelled"   # لغو شده
    
    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (STATUS_PENDING, "در انتظار"),
        (STATUS_DONE, "انجام شده"),
        (STATUS_CONTINUED, "نیازمند ادامه"),
        (STATUS_CLOSED, "مختومه"),
        (STATUS_CANCELLED, "لغو شده"),
    ]
    
    # نوع نتیجه پیگیری
    RESULT_IMPROVED = "improved"           # بهبود مشاهده شد
    RESULT_NO_CHANGE = "no_change"         # بدون تغییر
    RESULT_CONTINUED = "continued"         # تداوم وضعیت
    RESULT_NEW_STATUS = "new_status"       # وضعیت جدید
    RESULT_INSUFFICIENT = "insufficient"   # اطلاعات ناکافی
    RESULT_NEEDS_MORE = "needs_more"       # نیازمند پیگیری بیشتر
    
    RESULT_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (RESULT_IMPROVED, "بهبود مشاهده شد"),
        (RESULT_NO_CHANGE, "بدون تغییر قابل مشاهده"),
        (RESULT_CONTINUED, "تداوم وضعیت"),
        (RESULT_NEW_STATUS, "وضعیت جدید"),
        (RESULT_INSUFFICIENT, "اطلاعات ناکافی"),
        (RESULT_NEEDS_MORE, "نیازمند پیگیری بیشتر"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.intervention_id = None   # ارجاع به Intervention
        self.staff_id = None          # ارجاع به Staff (مسئول پیگیری)
        
        # ===== اطلاعات اصلی =====
        self.date = None              # تاریخ پیگیری (شمسی)
        self.method = None            # روش پیگیری
        self.description = None       # شرح کامل پیگیری
        
        # ===== وضعیت =====
        self.status = self.STATUS_PENDING  # وضعیت پیگیری
        self.next_action_date = None       # تاریخ اقدام بعدی (شمسی)
        
        # ===== نتیجه =====
        self.result_type = None       # نوع نتیجه (از RESULT_CHOICES)
        self.result_description = None  # شرح نتیجه
        
        # ===== فیلدهای کمکی برای نمایش =====
        self.intervention_type = None
        self.staff_name = None
        self.student_name = None
    
    @property
    def status_display(self):
        """نمایش وضعیت به فارسی (بدون Emoji)"""
        status_map = {
            self.STATUS_PENDING: "در انتظار",
            self.STATUS_DONE: "انجام شده",
            self.STATUS_CONTINUED: "نیازمند ادامه",
            self.STATUS_CLOSED: "مختومه",
            self.STATUS_CANCELLED: "لغو شده",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def result_type_display(self):
        """نمایش نوع نتیجه به فارسی (بدون Emoji)"""
        result_map = {
            self.RESULT_IMPROVED: "بهبود مشاهده شد",
            self.RESULT_NO_CHANGE: "بدون تغییر قابل مشاهده",
            self.RESULT_CONTINUED: "تداوم وضعیت",
            self.RESULT_NEW_STATUS: "وضعیت جدید",
            self.RESULT_INSUFFICIENT: "اطلاعات ناکافی",
            self.RESULT_NEEDS_MORE: "نیازمند پیگیری بیشتر",
        }
        return result_map.get(self.result_type, self.result_type or "ثبت نشده")
    
    @property
    def is_pending(self):
        """آیا پیگیری در انتظار است؟"""
        return self.status == self.STATUS_PENDING
    
    @property
    def is_done(self):
        """آیا پیگیری انجام شده است؟"""
        return self.status == self.STATUS_DONE
    
    @property
    def is_closed(self):
        """آیا پیگیری مختومه است؟"""
        return self.status == self.STATUS_CLOSED
    
    def soft_delete(self, user_id=None):
        """حذف منطقی پیگیری"""
        super().soft_delete(user_id)
    
    def restore(self):
        """بازیابی پیگیری از حذف منطقی"""
        super().restore()
    
    def validate(self):
        errors = []
        if not self.intervention_id:
            errors.append("مداخله باید انتخاب شود")
        if not self.staff_id:
            errors.append("مسئول پیگیری باید انتخاب شود")
        if not self.date:
            errors.append("تاریخ پیگیری نمی‌تواند خالی باشد")
        if self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت پیگیری نامعتبر است")
        if self.result_type and self.result_type not in [r[0] for r in self.RESULT_CHOICES]:
            errors.append("نوع نتیجه نامعتبر است")
        return errors