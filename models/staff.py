"""
مدل کادر مدرسه (مشاهده‌گرها)
"""

from models.base import BaseModel


class Staff(BaseModel):
    """مدل کادر مدرسه"""
    
    def __init__(self):
        super().__init__()
        self.full_name = None
        self.role = None
        self.phone = None
        self.email = None
        self.is_active = 1
        self.description = None
    
    @property
    def role_display(self):
        role_map = {
            "manager": "مدیر",
            "vice_principal": "معاون پرورشی",
            "vice_education": "معاون آموزشی",
            "teacher": "معلم",
            "sport_coach": "مربی ورزش",
            "quran_coach": "مربی قرآن",
            "art_coach": "مربی هنر",
            "counselor": "مشاور",
            "system": "سیستم",
            "other": "سایر"
        }
        return role_map.get(self.role, self.role or "نامشخص")
    
    def validate(self):
        errors = []
        if not self.full_name or len(self.full_name.strip()) < 3:
            errors.append("نام کامل باید حداقل ۳ کاراکتر باشد")
        if not self.role:
            errors.append("سمت باید انتخاب شود")
        return errors

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value