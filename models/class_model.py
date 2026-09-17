"""
مدل کلاس - برای مدیریت کلاس‌های مدرسه
"""

from models.base import BaseModel


class ClassModel(BaseModel):
    """مدل کلاس مدرسه"""
    
    def __init__(self):
        super().__init__()
        self.name = None           # نام کلاس (الف، ب، ج، ...)
        self.grade = None          # پایه (1 تا 6)
        self.teacher_id = None     # شناسه معلم اصلی کلاس
        self.academic_year_id = None  # شناسه سال تحصیلی
        self.capacity = 0          # ظرفیت کلاس
        self.is_active = 1         # 0=غیرفعال, 1=فعال
        self.description = None    # توضیحات
    
    @property
    def display_name(self):
        """نمایش نام کلاس به همراه پایه"""
        grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}
        grade_text = grade_names.get(self.grade, str(self.grade)) if self.grade else ""
        if grade_text and self.name:
            return f"پایه {grade_text} - کلاس {self.name}"
        return self.name or "کلاس نامشخص"
    
    def validate(self):
        errors = []
        if not self.name or len(self.name.strip()) < 1:
            errors.append("نام کلاس نمی‌تواند خالی باشد")
        if self.grade and self.grade not in range(1, 7):
            errors.append("پایه باید بین 1 تا 6 باشد")
        if self.capacity and self.capacity < 0:
            errors.append("ظرفیت کلاس نمی‌تواند منفی باشد")
        return errors