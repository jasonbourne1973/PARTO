"""
مدل اعلان‌ها و یادآوری‌ها
"""

from typing import ClassVar

from models.base import BaseModel
from utils.time_utils import utc_now_iso


class Notification(BaseModel):
    """
    مدل اعلان‌ها و یادآوری‌ها
    
    ویژگی‌ها:
    - اعلان‌های سیستم
    - یادآوری‌های پیگیری
    - اعلان‌های معوق
    - وضعیت خوانده/نخوانده
    """
    
    # نوع‌های اعلان
    TYPE_REMINDER = "reminder"          # یادآوری پیگیری
    TYPE_OVERDUE = "overdue"            # معوق شده
    TYPE_SYSTEM = "system"              # اعلان سیستمی
    TYPE_INFO = "info"                  # اطلاع‌رسانی
    
    TYPE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (TYPE_REMINDER, "یادآوری"),
        (TYPE_OVERDUE, "معوق شده"),
        (TYPE_SYSTEM, "سیستمی"),
        (TYPE_INFO, "اطلاع‌رسانی"),
    ]
    
    # اولویت‌ها
    PRIORITY_HIGH = "high"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_LOW = "low"
    
    PRIORITY_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (PRIORITY_HIGH, "بالا"),
        (PRIORITY_MEDIUM, "متوسط"),
        (PRIORITY_LOW, "پایین"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== اطلاعات پایه =====
        self.user_id = None             # شناسه کاربر گیرنده (staff.id)
        self.type = None                # نوع اعلان
        self.priority = self.PRIORITY_MEDIUM  # اولویت
        self.title = None               # عنوان اعلان
        self.message = None             # پیام اعلان
        self.link = None                # لینک/مسیر مرتبط
        self.entity_type = None         # نوع موجودیت مرتبط
        self.entity_id = None           # شناسه موجودیت مرتبط
        
        # ===== وضعیت =====
        self.is_read = False            # خوانده شده؟
        self.read_at = None             # زمان خواندن
        self.is_dismissed = False       # رد شده؟
        self.dismissed_at = None        # زمان رد
        
        # ===== زمان‌بندی =====
        self.scheduled_at = None        # زمان برنامه‌ریزی‌شده
        self.expires_at = None          # زمان انقضا
        
        # ===== فیلدهای کمکی =====
        self.user_name = None           # نام کاربر (برای نمایش)
        self.related_data = None        # داده‌های مرتبط (JSON)
    
    @property
    def type_display(self):
        """نمایش فارسی نوع اعلان"""
        type_map = {
            self.TYPE_REMINDER: "یادآوری",
            self.TYPE_OVERDUE: "معوق شده",
            self.TYPE_SYSTEM: "سیستمی",
            self.TYPE_INFO: "اطلاع‌رسانی",
        }
        return type_map.get(self.type, self.type)
    
    @property
    def priority_display(self):
        """نمایش فارسی اولویت"""
        priority_map = {
            self.PRIORITY_HIGH: "🔴 بالا",
            self.PRIORITY_MEDIUM: "🟡 متوسط",
            self.PRIORITY_LOW: "🟢 پایین",
        }
        return priority_map.get(self.priority, self.priority)
    
    @property
    def status_display(self):
        """نمایش وضعیت اعلان"""
        if self.is_dismissed:
            return "رد شده"
        elif self.is_read:
            return "خوانده شده"
        else:
            return "خوانده نشده"
    
    @property
    def is_active(self):
        """آیا اعلان فعال است؟"""
        return not self.is_dismissed and not self.is_read
    
    def mark_as_read(self):
        """علامت‌گذاری به عنوان خوانده شده"""
        self.is_read = True
        self.read_at = utc_now_iso()
    
    def mark_as_dismissed(self):
        """علامت‌گذاری به عنوان رد شده"""
        self.is_dismissed = True
        self.dismissed_at = utc_now_iso()
    
    def validate(self):
        errors = []
        if not self.user_id:
            errors.append("کاربر گیرنده باید مشخص شود")
        if not self.type:
            errors.append("نوع اعلان باید مشخص شود")
        if self.type and self.type not in [t[0] for t in self.TYPE_CHOICES]:
            errors.append("نوع اعلان نامعتبر است")
        if self.priority and self.priority not in [p[0] for p in self.PRIORITY_CHOICES]:
            errors.append("اولویت اعلان نامعتبر است")
        if not self.title or len(self.title.strip()) < 2:
            errors.append("عنوان اعلان باید حداقل ۲ کاراکتر باشد")
        if not self.message or len(self.message.strip()) < 3:
            errors.append("پیام اعلان باید حداقل ۳ کاراکتر باشد")
        return errors