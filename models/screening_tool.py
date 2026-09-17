"""
مدل ابزار غربالگری (Screening Tool)
"""

from models.base import BaseModel


class ScreeningTool(BaseModel):
    """
    مدل ابزار غربالگری - ثبت اطلاعات ابزارهای معتبر
    
    این مدل صرفاً اطلاعات ابزارهای غربالگری را ثبت می‌کند
    و هیچ تفسیر یا تشخیص خودکاری تولید نمی‌کند.
    
    ویژگی‌ها:
    - ثبت نام و نسخه ابزار
    - ثبت حوزه‌های ارزیابی
    - ثبت مقیاس‌های امتیازدهی
    - بدون تولید تفسیر خودکار
    """
    
    # وضعیت‌های ابزار
    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_DEPRECATED = "deprecated"
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "فعال"),
        (STATUS_INACTIVE, "غیرفعال"),
        (STATUS_DEPRECATED, "منسوخ شده"),
    ]
    
    # نوع ابزار
    TYPE_QUESTIONNAIRE = "questionnaire"
    TYPE_CHECKLIST = "checklist"
    TYPE_SCALE = "scale"
    TYPE_INTERVIEW = "interview"
    TYPE_OBSERVATION = "observation"
    
    TYPE_CHOICES = [
        (TYPE_QUESTIONNAIRE, "پرسشنامه"),
        (TYPE_CHECKLIST, "چک‌لیست"),
        (TYPE_SCALE, "مقیاس"),
        (TYPE_INTERVIEW, "مصاحبه ساختاریافته"),
        (TYPE_OBSERVATION, "چک‌لیست مشاهده"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== اطلاعات پایه =====
        self.name = None                    # نام ابزار
        self.version = None                 # نسخه ابزار
        self.type = None                    # نوع ابزار (از TYPE_CHOICES)
        
        # ===== اطلاعات تخصصی =====
        self.description = None             # توضیحات ابزار
        self.reference = None               # مرجع/منبع ابزار
        self.target_age_group = None        # گروه سنی هدف
        self.target_grade_range = None      # محدوده پایه تحصیلی
        
        # ===== حوزه‌ها =====
        self.domains = None                 # حوزه‌های ارزیابی (JSON)
        self.sub_domains = None             # زیرحوزه‌ها (JSON)
        
        # ===== مقیاس‌ها =====
        self.scoring_scale = None           # مقیاس امتیازدهی (JSON)
        self.min_score = None               # حداقل امتیاز
        self.max_score = None               # حداکثر امتیاز
        self.cutoff_scores = None           # امتیازهای برش (JSON)
        
        # ===== وضعیت =====
        self.status = self.STATUS_ACTIVE
        self.is_standard = False            # آیا ابزار استاندارد است؟
        
        # ===== فیلدهای کمکی =====
        self.administration_time = None     # زمان اجرا (دقیقه)
        self.required_training = None       # آیا نیاز به آموزش دارد؟
    
    @property
    def status_display(self):
        """نمایش فارسی وضعیت"""
        status_map = {
            self.STATUS_ACTIVE: "فعال",
            self.STATUS_INACTIVE: "غیرفعال",
            self.STATUS_DEPRECATED: "منسوخ شده",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def type_display(self):
        """نمایش فارسی نوع ابزار"""
        type_map = {
            self.TYPE_QUESTIONNAIRE: "پرسشنامه",
            self.TYPE_CHECKLIST: "چک‌لیست",
            self.TYPE_SCALE: "مقیاس",
            self.TYPE_INTERVIEW: "مصاحبه ساختاریافته",
            self.TYPE_OBSERVATION: "چک‌لیست مشاهده",
        }
        return type_map.get(self.type, self.type or "ثبت نشده")
    
    @property
    def domain_list(self):
        """دریافت لیست حوزه‌ها"""
        if self.domains:
            if isinstance(self.domains, list):
                return self.domains
            elif isinstance(self.domains, str):
                try:
                    import json
                    return json.loads(self.domains)
                except:
                    return [self.domains]
        return []
    
    def validate(self):
        errors = []
        if not self.name or len(self.name.strip()) < 2:
            errors.append("نام ابزار باید حداقل ۲ کاراکتر باشد")
        if self.type not in [t[0] for t in self.TYPE_CHOICES]:
            errors.append("نوع ابزار نامعتبر است")
        if self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت ابزار نامعتبر است")
        return errors