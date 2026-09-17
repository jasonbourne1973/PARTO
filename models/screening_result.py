"""
مدل نتیجه غربالگری (Screening Result)
"""

from models.base import BaseModel


class ScreeningResult(BaseModel):
    """
    مدل نتیجه غربالگری - ثبت داده‌های خام از اجرای ابزار
    
    این مدل صرفاً داده‌های خام از اجرای ابزار غربالگری را ثبت می‌کند.
    هیچ تفسیر خودکاری تولید نمی‌شود.
    
    داده‌های ثبت‌شده:
    - امتیازات خام در هر حوزه
    - امتیاز کل
    - پاسخ‌های ثبت‌شده
    - مشاهده‌های ثبت‌شده
    """
    
    # وضعیت‌های نتیجه
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_INVALID = "invalid"
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "در انتظار تکمیل"),
        (STATUS_COMPLETED, "تکمیل شده"),
        (STATUS_IN_PROGRESS, "در حال اجرا"),
        (STATUS_INVALID, "نامعتبر"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.student_profile_id = None     # ارجاع به StudentAcademicProfile
        self.staff_id = None               # ارجاع به Staff (اجراکننده)
        self.tool_id = None                # ارجاع به ScreeningTool
        
        # ===== اطلاعات اجرا =====
        self.execution_date = None         # تاریخ اجرا (شمسی)
        self.execution_context = None      # زمینه اجرا
        
        # ===== داده‌های خام =====
        self.raw_answers = None            # پاسخ‌های خام (JSON)
        self.raw_observations = None       # مشاهدات خام (JSON)
        self.domain_scores = None          # امتیازات حوزه‌ها (JSON)
        self.total_score = None            # امتیاز کل
        
        # ===== اطلاعات تکمیلی =====
        self.notes = None                  # یادداشت‌های اجرا
        self.duration_minutes = None       # مدت زمان اجرا (دقیقه)
        
        # ===== وضعیت =====
        self.status = self.STATUS_PENDING
        
        # ===== فیلدهای کمکی =====
        self.student_name = None
        self.staff_name = None
        self.tool_name = None
    
    @property
    def status_display(self):
        """نمایش فارسی وضعیت"""
        status_map = {
            self.STATUS_PENDING: "در انتظار تکمیل",
            self.STATUS_COMPLETED: "تکمیل شده",
            self.STATUS_IN_PROGRESS: "در حال اجرا",
            self.STATUS_INVALID: "نامعتبر",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def is_completed(self):
        """آیا نتیجه تکمیل شده است؟"""
        return self.status == self.STATUS_COMPLETED
    
    @property
    def is_valid(self):
        """آیا نتیجه معتبر است؟"""
        return self.status not in [self.STATUS_INVALID]
    
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
    
    def to_dict(self):
        """تبدیل به دیکشنری برای نمایش"""
        return {
            'tool_name': self.tool_name,
            'execution_date': self.execution_date,
            'total_score': self.total_score,
            'domain_scores': self.domain_score_dict,
            'status': self.status_display,
            'notes': self.notes,
        }
    
    def validate(self):
        errors = []
        if not self.student_profile_id:
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        if not self.staff_id:
            errors.append("اجراکننده باید انتخاب شود")
        if not self.tool_id:
            errors.append("ابزار غربالگری باید انتخاب شود")
        if not self.execution_date:
            errors.append("تاریخ اجرا نمی‌تواند خالی باشد")
        if self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت نتیجه نامعتبر است")
        return errors