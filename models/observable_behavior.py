"""
مدل رفتار قابل مشاهده - سطح سوم از ساختار شایستگی
"""

from models.base import BaseModel


class ObservableBehavior(BaseModel):
    """
    مدل رفتار قابل مشاهده (Observable Behavior)
    
    ساختار سلسله‌مراتبی:
    Competency (شایستگی) → Indicator (شاخص) → ObservableBehavior (رفتار قابل مشاهده)
    
    رفتارهای قابل مشاهده، نمونه‌های عینی و قابل اندازه‌گیری از یک شاخص هستند.
    """
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.indicator_id = None      # ارجاع به Indicator
        self.competency_id = None     # ارجاع مستقیم به Competency (برای سرعت)
        
        # ===== اطلاعات اصلی =====
        self.text = None              # متن رفتار قابل مشاهده
        self.sort_order = 0           # ترتیب نمایش
        
        # ===== فیلدهای کمکی =====
        self.indicator_title = None   # برای نمایش
        self.competency_title = None  # برای نمایش
    
    @property
    def full_text(self):
        """متن کامل با شماره"""
        return f"{self.sort_order}. {self.text}" if self.sort_order else self.text
    
    def validate(self):
        errors = []
        if not self.indicator_id:
            errors.append("شاخص باید انتخاب شود")
        if not self.text or len(self.text.strip()) < 3:
            errors.append("متن رفتار قابل مشاهده باید حداقل ۳ کاراکتر باشد")
        return errors