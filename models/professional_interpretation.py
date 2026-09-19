"""
مدل تفسیر تخصصی (Professional Interpretation)
"""

from typing import ClassVar

from models.base import BaseModel


class ProfessionalInterpretation(BaseModel):
    """
    مدل تفسیر تخصصی - تفسیر مشاور یا فرد دارای صلاحیت
    
    این مدل برای ثبت تفسیرهای تخصصی است که توسط افراد دارای صلاحیت
    (مشاور، روانشناس، ...) انجام می‌شود.
    
    نکته مهم:
    - سیستم هیچ‌گونه تفسیر خودکاری تولید نمی‌کند
    - تمام تفسیرها باید توسط فرد متخصص ثبت شوند
    - این مدل می‌تواند به Observation یا Screening متصل شود
    """
    
    # سطوح تفسیر
    LEVEL_OBSERVATION = "observation"
    LEVEL_SCREENING = "screening"
    LEVEL_COMPREHENSIVE = "comprehensive"
    
    LEVEL_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (LEVEL_OBSERVATION, "تفسیر مشاهده"),
        (LEVEL_SCREENING, "تفسیر غربالگری"),
        (LEVEL_COMPREHENSIVE, "تفسیر جامع"),
    ]
    
    # وضعیت‌های تفسیر
    STATUS_DRAFT = "draft"
    STATUS_FINAL = "final"
    STATUS_ARCHIVED = "archived"
    
    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (STATUS_DRAFT, "پیش‌نویس"),
        (STATUS_FINAL, "نهایی"),
        (STATUS_ARCHIVED, "بایگانی شده"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.student_profile_id = None       # ارجاع به StudentAcademicProfile
        self.staff_id = None                 # ارجاع به Staff (تفسیرکننده)
        
        # ===== ارجاع به داده منبع =====
        self.observation_id = None           # ارجاع به Observation (اختیاری)
        self.screening_id = None             # ارجاع به Screening (اختیاری)
        
        # ===== سطوح =====
        self.level = self.LEVEL_OBSERVATION  # سطح تفسیر
        self.domain = None                   # حوزه تفسیر
        
        # ===== محتوای تفسیر =====
        self.title = None                    # عنوان تفسیر
        self.summary = None                  # خلاصه تفسیر
        self.detailed_text = None            # متن کامل تفسیر
        
        # ===== توصیه‌ها =====
        self.recommendations = None          # توصیه‌ها (JSON)
        self.next_steps = None               # اقدامات بعدی (JSON)
        
        # ===== وضعیت =====
        self.status = self.STATUS_DRAFT
        
        # ===== فیلدهای کمکی =====
        self.student_name = None
        self.staff_name = None
    
    @property
    def status_display(self):
        """نمایش وضعیت به فارسی"""
        status_map = {
            self.STATUS_DRAFT: "پیش‌نویس",
            self.STATUS_FINAL: "نهایی",
            self.STATUS_ARCHIVED: "بایگانی شده",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def level_display(self):
        """نمایش سطح تفسیر به فارسی"""
        level_map = {
            self.LEVEL_OBSERVATION: "تفسیر مشاهده",
            self.LEVEL_SCREENING: "تفسیر غربالگری",
            self.LEVEL_COMPREHENSIVE: "تفسیر جامع",
        }
        return level_map.get(self.level, self.level)
    
    @property
    def is_final(self):
        """آیا تفسیر نهایی است؟"""
        return self.status == self.STATUS_FINAL
    
    @property
    def is_draft(self):
        """آیا تفسیر پیش‌نویس است؟"""
        return self.status == self.STATUS_DRAFT
    
    def validate(self):
        errors = []
        if not self.student_profile_id:
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        if not self.staff_id:
            errors.append("تفسیرکننده باید انتخاب شود")
        if not self.title or len(self.title.strip()) < 3:
            errors.append("عنوان تفسیر باید حداقل ۳ کاراکتر باشد")
        if not self.detailed_text or len(self.detailed_text.strip()) < 10:
            errors.append("متن تفسیر باید حداقل ۱۰ کاراکتر باشد")
        if self.level not in [l[0] for l in self.LEVEL_CHOICES]:
            errors.append("سطح تفسیر نامعتبر است")
        if self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت تفسیر نامعتبر است")
        return errors