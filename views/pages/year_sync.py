"""
همگام‌سازی صفحه‌ها با «سال تحصیلی فعال» (بازبینی نهایی — BUG-GUI-12 / NAV-04/05/06)

طراحی قبلی: تنها مسیر اطلاع‌رسانی، بارگذاری دوبارهٔ صفحه‌ها با
`inspect` روی همهٔ متدهای `load_*` بود؛ یعنی هیچ صفحه‌ای «سال انتخاب‌شده»
را نمی‌گرفت و هر کدام جداگانه سال فعال دیتابیس را حدس می‌زد.

طراحی جدید: تک‌منبع حقیقت = `MainWindow.set_active_year(year_id)`.
هر صفحهٔ وابسته به سال یک متد صریح `set_active_year(year_id)` دارد که
انتخاب کاربر را می‌گیرد، کامبوی سال خودش (اگر دارد) را بدون سیگنال
هماهنگ می‌کند و داده را با همان سال دوباره می‌خواند. این ماژول فقط دو
کمک‌تابع مشترک دارد تا این همگام‌سازی در همهٔ صفحه‌ها یک‌شکل باشد.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


def select_year_in_combo(combo, year_id, *, add_if_missing=False):
    """
    انتخاب یک سال در کامبوی سال «بدون» فرستادن سیگنال تغییر

    Args:
        combo: کامبوی سال‌ها (itemData هر گزینه = شناسهٔ سال)
        year_id: شناسهٔ سال؛ None یعنی گزینهٔ «همه سال‌ها» (اگر وجود داشته باشد)
        add_if_missing: اگر سال در فهرست نبود، به‌عنوان گزینهٔ تازه افزوده شود

    Returns:
        bool: True اگر انتخاب انجام شد؛ False اگر سال در فهرست نبود
    """
    if combo is None:
        return False

    combo.blockSignals(True)
    try:
        for index in range(combo.count()):
            if combo.itemData(index) == year_id:
                combo.setCurrentIndex(index)
                return True
        if add_if_missing and year_id is not None:
            combo.addItem(str(year_id), year_id)
            combo.setCurrentIndex(combo.count() - 1)
            return True
        return False
    finally:
        combo.blockSignals(False)


class YearAwarePage:
    """
    رفتار مشترک صفحه‌های وابسته به سال

    صفحه‌ها این کلاس را به‌عنوان mixin ارث می‌برند و متد
    `reload_for_year()` خودشان را می‌نویسند (ترکیب صریح بارگذاری‌های
    همان صفحه). مزیت: هیچ فراخوانی بازتابی (reflection) و هیچ حدس‌زدنی
    از «سال فعال دیتابیس» باقی نمی‌ماند.
    """

    #: آخرین سالی که از بیرون (MainWindow) به این صفحه اعلام شده است
    active_year_id = None

    def set_active_year(self, year_id):
        """
        اعلام سال فعال سامانه به این صفحه

        Args:
            year_id: شناسهٔ سال تحصیلی فعال (یا None)

        Returns:
            bool: True اگر بارگذاری داده با همین سال انجام شد
        """
        self.active_year_id = year_id
        combo = getattr(self, "year_combo", None)
        if combo is not None and not select_year_in_combo(combo, year_id):
            # فهرست سال‌های صفحه ممکن است قدیمی باشد (سالی که پس از ساخت
            # صفحه اضافه شده است). یک بار تازه‌سازی و انتخاب دوباره؛ اگر
            # باز هم نبود، انتخاب صریح حفظ و گزارش می‌شود (بدون سکوت).
            loader = getattr(self, "load_academic_years", None)
            if callable(loader):
                try:
                    loader()
                except Exception as e:  # pragma: no cover - وابسته به دیتابیس
                    logger.error(
                        f"{type(self).__name__}: تازه‌سازی فهرست سال‌ها "
                        f"ناموفق بود: {e}"
                    )
            if not select_year_in_combo(combo, year_id):
                logger.warning(
                    f"{type(self).__name__}: سال {year_id} در فهرست سال‌های "
                    "این صفحه نیست؛ داده با همان انتخاب صریح بارگذاری می‌شود."
                )
        return self.reload_for_year(year_id)

    def reload_for_year(self, year_id):
        """بارگذاری دوبارهٔ داده‌های همین صفحه برای سال داده‌شده"""
        raise NotImplementedError

    def effective_year(self):
        """
        سال مؤثر این صفحه

        اگر سامانه سالی را صریح اعلام کرده باشد (`set_active_year`)،
        همان سال برمی‌گردد — حتی اگر سال فعال دیتابیس چیز دیگری باشد.
        فقط وقتی هیچ انتخابی نرسیده باشد، سال فعال دیتابیس خوانده
        می‌شود (رفتار مستقل صفحه در تست/اجرای تنها).
        """
        dal = getattr(self, "academic_year_dal", None)
        if dal is None:
            return None
        if self.active_year_id:
            try:
                year = dal.get_by_id(self.active_year_id)
            except Exception as e:  # pragma: no cover - وابسته به دیتابیس
                logger.error(
                    f"{type(self).__name__}: خواندن سال {self.active_year_id} "
                    f"ممکن نشد: {e}"
                )
                year = None
            if year is not None:
                return year
        return dal.get_active()
