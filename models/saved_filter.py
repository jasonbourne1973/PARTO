"""
مدل فیلتر ذخیره‌شده - ذخیره و مدیریت فیلترهای جستجو
"""

from models.base import BaseModel


class SavedFilter(BaseModel):
    """
    مدل فیلتر ذخیره‌شده
    
    ویژگی‌ها:
    - ذخیره فیلترهای پرکاربرد برای استفاده مجدد
    - اشتراک‌گذاری فیلترها بین کاربران
    - دسته‌بندی فیلترها
    - ذخیره پارامترهای جستجو به صورت JSON
    """
    
    # سطح دسترسی
    VISIBILITY_PRIVATE = "private"      # فقط خود کاربر
    VISIBILITY_SHARED = "shared"        # اشتراک‌گذاری شده با همه
    VISIBILITY_TEAM = "team"            # فقط تیم/گروه خاص
    
    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, "خصوصی"),
        (VISIBILITY_SHARED, "اشتراکی"),
        (VISIBILITY_TEAM, "تیمی"),
    ]
    
    # نوع فیلتر
    TYPE_STUDENT = "student"            # فیلتر دانش‌آموزان
    TYPE_OBSERVATION = "observation"    # فیلتر مشاهدات
    TYPE_INTERVENTION = "intervention"  # فیلتر مداخلات
    TYPE_FOLLOWUP = "followup"          # فیلتر پیگیری‌ها
    TYPE_REPORT = "report"              # فیلتر گزارش‌ها
    
    TYPE_CHOICES = [
        (TYPE_STUDENT, "دانش‌آموزان"),
        (TYPE_OBSERVATION, "مشاهدات"),
        (TYPE_INTERVENTION, "مداخلات"),
        (TYPE_FOLLOWUP, "پیگیری‌ها"),
        (TYPE_REPORT, "گزارش‌ها"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== اطلاعات پایه =====
        self.name = None                 # نام فیلتر
        self.description = None          # توضیحات فیلتر
        self.filter_type = None          # نوع فیلتر
        self.visibility = self.VISIBILITY_PRIVATE  # سطح دسترسی
        
        # ===== کاربر =====
        self.user_id = None              # شناسه کاربر ایجادکننده
        
        # ===== پارامترهای فیلتر =====
        self.filter_params = None        # پارامترهای فیلتر (JSON)
        
        # ===== آمار استفاده =====
        self.use_count = 0               # تعداد دفعات استفاده
        
        # ===== فیلدهای کمکی =====
        self.user_name = None
        self.is_owner = False
    
    @property
    def visibility_display(self):
        """نمایش فارسی سطح دسترسی"""
        visibility_map = {
            self.VISIBILITY_PRIVATE: "🔒 خصوصی",
            self.VISIBILITY_SHARED: "🌐 اشتراکی",
            self.VISIBILITY_TEAM: "👥 تیمی",
        }
        return visibility_map.get(self.visibility, self.visibility)
    
    @property
    def type_display(self):
        """نمایش فارسی نوع فیلتر"""
        type_map = {
            self.TYPE_STUDENT: "دانش‌آموزان",
            self.TYPE_OBSERVATION: "مشاهدات",
            self.TYPE_INTERVENTION: "مداخلات",
            self.TYPE_FOLLOWUP: "پیگیری‌ها",
            self.TYPE_REPORT: "گزارش‌ها",
        }
        return type_map.get(self.filter_type, self.filter_type)
    
    @property
    def is_shared(self):
        """آیا فیلتر به اشتراک گذاشته شده است؟"""
        return self.visibility in [self.VISIBILITY_SHARED, self.VISIBILITY_TEAM]
    
    def increment_use(self):
        """افزایش تعداد استفاده از فیلتر"""
        self.use_count += 1
    
    def validate(self):
        errors = []
        if not self.name or len(self.name.strip()) < 2:
            errors.append("نام فیلتر باید حداقل ۲ کاراکتر باشد")
        if not self.filter_type:
            errors.append("نوع فیلتر باید انتخاب شود")
        if self.filter_type and self.filter_type not in [t[0] for t in self.TYPE_CHOICES]:
            errors.append("نوع فیلتر نامعتبر است")
        if self.visibility and self.visibility not in [v[0] for v in self.VISIBILITY_CHOICES]:
            errors.append("سطح دسترسی نامعتبر است")
        if not self.user_id:
            errors.append("کاربر باید مشخص شود")
        if not self.filter_params:
            errors.append("پارامترهای فیلتر نمی‌تواند خالی باشد")
        return errors