"""
مدل غربالگری (Screening) - یکپارچه با ابزارها و نتایج
"""

from models.base import BaseModel


class Screening(BaseModel):
    """
    مدل غربالگری - یکپارچه‌سازی ابزار و نتیجه
    
    این مدل صرفاً داده‌های خام از ابزار غربالگری را ثبت می‌کند
    و هیچ تفسیر خودکاری تولید نمی‌کند.
    
    تفاوت با Observation:
    - Observation: ثبت یک رفتار یا رویداد مشاهده‌شده
    - Screening: نتیجه یک ابزار استاندارد یا پرسشنامه
    """
    
    # وضعیت‌های غربالگری
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_CANCELLED = "cancelled"
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "در انتظار"),
        (STATUS_COMPLETED, "تکمیل شده"),
        (STATUS_IN_PROGRESS, "در حال اجرا"),
        (STATUS_CANCELLED, "لغو شده"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.student_profile_id = None   # ارجاع به StudentAcademicProfile
        self.staff_id = None             # ارجاع به Staff (اجراکننده)
        self.tool_id = None              # ارجاع به ScreeningTool
        self.result_id = None            # ارجاع به ScreeningResult (اختیاری)
        
        # ===== اطلاعات ابزار =====
        self.tool_name = None            # نام ابزار غربالگری (برای نمایش سریع)
        self.tool_version = None         # نسخه ابزار
        
        # ===== اطلاعات اجرا =====
        self.execution_date = None       # تاریخ اجرا (شمسی)
        self.execution_context = None    # زمینه اجرا
        
        # ===== داده‌های خام =====
        self.domain_scores = None        # امتیازات حوزه‌ها (JSON)
        self.total_score = None          # امتیاز کل
        
        # ===== حوزه‌ها =====
        self.domain = None               # حوزه اصلی
        self.sub_domain = None           # زیرحوزه
        
        # ===== وضعیت =====
        self.status = self.STATUS_PENDING
        
        # ===== فیلدهای کمکی =====
        self.student_name = None
        self.staff_name = None
        self.tool_display_name = None
    
    @property
    def status_display(self):
        """نمایش وضعیت به فارسی"""
        status_map = {
            self.STATUS_PENDING: "در انتظار",
            self.STATUS_COMPLETED: "تکمیل شده",
            self.STATUS_IN_PROGRESS: "در حال اجرا",
            self.STATUS_CANCELLED: "لغو شده",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def is_completed(self):
        """آیا غربالگری تکمیل شده است؟"""
        return self.status == self.STATUS_COMPLETED
    
    @property
    def has_interpretation(self):
        """آیا تفسیر تخصصی برای این غربالگری وجود دارد؟"""
        return hasattr(self, 'interpretations') and len(self.interpretations) > 0
    
    @property
    def domain_score_dict(self):
        """دریافت دیکشنری امتیازات حوزه‌ها"""
        if self.domain_scores:
            if isinstance(self.domain_scores, dict):
                return self.domain_scores
            elif isinstance(self.domain_scores, str):
                try:
                    import json
                    return json.loads(self.domain_scores)
                except:
                    return {}
        return {}
    
    def get_domain_score(self, domain_name):
        """دریافت امتیاز یک حوزه خاص"""
        scores = self.domain_score_dict
        return scores.get(domain_name, 0)
    
    def add_interpretation(self, interpretation):
        """افزودن تفسیر تخصصی به غربالگری"""
        if not hasattr(self, 'interpretations'):
            self.interpretations = []
        if interpretation not in self.interpretations:
            self.interpretations.append(interpretation)
            interpretation.screening_id = self.id
            interpretation.student_profile_id = self.student_profile_id
    
    def validate(self):
        errors = []
        if not self.student_profile_id:
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        if not self.staff_id:
            errors.append("اجراکننده باید انتخاب شود")
        if not self.tool_name:
            errors.append("نام ابزار غربالگری نمی‌تواند خالی باشد")
        if not self.execution_date:
            errors.append("تاریخ اجرا نمی‌تواند خالی باشد")
        if self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت غربالگری نامعتبر است")
        return errors