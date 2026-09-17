"""
مدل پرونده سالانه دانش‌آموز
"""

from models.base import BaseModel


class StudentFile(BaseModel):
    """مدل پرونده سالانه دانش‌آموز"""
    
    def __init__(self):
        super().__init__()
        self.student_id = None
        self.academic_year_id = None
        self.class_name = None
        self.grade = None
        # فیلد پشتیبان برای property تا setter واقعی داشته باشیم.
        self._is_active = 1
        self.is_archived = 0
    
    @property
    def is_active(self):
        """وضعیت فعال بودن پرونده."""
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        """تنظیم وضعیت فعال بودن پرونده."""
        self._is_active = 1 if value else 0

    @property
    def grade_display(self):
        """نمایش پایه به صورت فارسی"""
        grade_map = {
            1: "اول", 2: "دوم", 3: "سوم",
            4: "چهارم", 5: "پنجم", 6: "ششم"
        }
        return grade_map.get(self.grade, str(self.grade))
    
    @property
    def class_display(self):
        return self.class_name or "تعیین نشده"
    
    @property
    def status_display(self):
        """نمایش وضعیت پرونده"""
        if self.is_archived == 1:
            return "📦 بایگانی شده"
        elif self.is_active == 1:
            return "🟢 فعال"
        else:
            return "🔴 غیرفعال"
    
    def validate(self):
        """اعتبارسنجی اطلاعات پرونده سالانه"""
        errors = []
        
        if not self.student_id:
            errors.append("دانش‌آموز باید انتخاب شود")
        if not self.academic_year_id:
            errors.append("سال تحصیلی باید انتخاب شود")
        if self.grade and self.grade not in range(1, 7):
            errors.append("پایه باید بین 1 تا 6 باشد")
        
        return errors