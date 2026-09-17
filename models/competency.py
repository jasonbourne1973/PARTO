"""
مدل شایستگی - سطح اول از ساختار شایستگی
با ارتباط به Indicator و ObservableBehavior
"""

from models.base import BaseModel


class Competency(BaseModel):
    """
    مدل شایستگی تربیتی

    ساختار سلسله‌مراتبی:
    Competency (شایستگی) → Indicator (شاخص) → ObservableBehavior (رفتار قابل مشاهده)

    شایستگی‌ها توانایی‌های کلی هستند که از طریق شاخص‌ها و رفتارهای قابل مشاهده
    ارزیابی می‌شوند.
    """

    def __init__(self):
        super().__init__()
        self.title = None
        self.description = None
        self.category = None
        self._is_active = 1   # فیلد پشتیبان پراپرتی is_active
        self.sort_order = 0

        # فیلدهای Soft Delete
        self.is_deleted = 0
        self.deleted_at = None
        self.deleted_by = None

        # فیلدهای کمکی (برای بارگذاری سریع)
        self.indicators = []
        self.observable_behaviors = []

    # ------------------------------------------------------------------
    # پراپرتی is_active با getter و setter
    # ------------------------------------------------------------------
    @property
    def is_active(self):
        """دریافت وضعیت فعال بودن"""
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        """تنظیم وضعیت فعال بودن"""
        self._is_active = 1 if value else 0

    @property
    def category_display(self):
        """نمایش فارسی دسته‌بندی"""
        category_map = {
            "emotional": "عاطفی-هیجانی",
            "social": "اجتماعی",
            "educational": "آموزشی",
            "moral": "اخلاقی",
            "self_management": "خودمدیریتی",
            "participation": "مشارکت",
            "other": "سایر"
        }
        return category_map.get(self.category, self.category or "سایر")

    @property
    def indicators_count(self):
        """تعداد شاخص‌های مرتبط"""
        return len(self.indicators)

    @property
    def behaviors_count(self):
        """تعداد رفتارهای قابل مشاهده مرتبط"""
        return len(self.observable_behaviors)

    def add_indicator(self, indicator):
        """افزودن شاخص به شایستگی"""
        if indicator not in self.indicators:
            self.indicators.append(indicator)
            indicator.competency_id = self.id

    def add_observable_behavior(self, behavior):
        """افزودن رفتار قابل مشاهده به شایستگی"""
        if behavior not in self.observable_behaviors:
            self.observable_behaviors.append(behavior)
            behavior.competency_id = self.id

    def get_indicators_with_behaviors(self):
        """
        دریافت شاخص‌ها با رفتارهای قابل مشاهده آنها
        Returns: list of dict
        """
        result = []
        for indicator in sorted(self.indicators, key=lambda x: x.sort_order):
            behaviors = [b for b in self.observable_behaviors
                         if b.indicator_id == indicator.id]
            result.append({
                'indicator': indicator,
                'behaviors': sorted(behaviors, key=lambda x: x.sort_order)
            })
        return result

    def to_dict(self):
        """تبدیل به دیکشنری برای نمایش"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'category_display': self.category_display,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at,
            'deleted_by': self.deleted_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'indicators_count': self.indicators_count,
            'behaviors_count': self.behaviors_count,
        }

    def validate(self):
        errors = []
        if not self.title or len(self.title.strip()) < 2:
            errors.append("عنوان شایستگی باید حداقل ۲ کاراکتر باشد")
        if self.category and self.category not in [
            "emotional", "social", "educational", "moral",
            "self_management", "participation", "other"
        ]:
            errors.append("دسته‌بندی نامعتبر است")
        return errors
