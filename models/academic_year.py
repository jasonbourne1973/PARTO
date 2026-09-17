"""
مدل سال تحصیلی - نسخه کامل
"""

from models.base import BaseModel


class AcademicYear(BaseModel):
    """مدل سال تحصیلی"""
    
    def __init__(self):
        super().__init__()
        self.title = None          # مثال: 1405-1406
        self.start_date = None     # تاریخ شروع (شمسی)
        self.end_date = None       # تاریخ پایان (شمسی)
        self.is_active = 0         # 0=غیرفعال, 1=فعال
        self.is_archived = 0       # 0=فعال, 1=بایگانی شده
    
    @property
    def status_display(self):
        if self.is_archived == 1:
            return "📦 بایگانی شده"
        elif self.is_active == 1:
            return "🟢 فعال"
        else:
            return "⚪ غیرفعال"
    
    @property
    def display_name(self):
        return self.title or "سال تحصیلی نامشخص"
    
    def validate(self):
        errors = []
        if not self.title or len(self.title.strip()) < 4:
            errors.append("عنوان سال تحصیلی باید حداقل ۴ کاراکتر باشد")
        return errors
    
    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value