"""
مدل شاخص - سطح دوم از ساختار شایستگی
"""

from models.base import BaseModel


class Indicator(BaseModel):
    """
    مدل شاخص (Indicator)
    
    ساختار سلسله‌مراتبی:
    Competency (شایستگی) → Indicator (شاخص) → ObservableBehavior (رفتار قابل مشاهده)
    
    شاخص‌ها معیارهای دقیق‌تری برای ارزیابی یک شایستگی هستند.
    """
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.competency_id = None     # ارجاع به Competency
        
        # ===== اطلاعات اصلی =====
        self.title = None             # عنوان شاخص
        self.description = None       # توضیحات شاخص
        self.sort_order = 0           # ترتیب نمایش
        
        # ===== فیلدهای کمکی =====
        self.competency_title = None  # برای نمایش
    
    @property
    def full_title(self):
        """عنوان کامل با شماره"""
        return f"{self.sort_order}. {self.title}" if self.sort_order else self.title
    
    def validate(self):
        errors = []
        if not self.competency_id:
            errors.append("شایستگی باید انتخاب شود")
        if not self.title or len(self.title.strip()) < 2:
            errors.append("عنوان شاخص باید حداقل ۲ کاراکتر باشد")
        return errors