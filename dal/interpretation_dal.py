"""
لایه دسترسی به داده تفسیر تخصصی (ProfessionalInterpretation)

===== بازرسی دوازدهم: حذف دوگانگی DAL =====
قبلاً دو فایل تقریباً یکسان برای یک مفهوم وجود داشت:

    dal/interpretation_dal.py  (کلاس InterpretationDAL)
    dal/professional_interpretation_dal.py  (کلاس ProfessionalInterpretationDAL)

که بدنه‌شان موبه‌مو یکی بود. دوگانگی یعنی خطر واگرایی در آینده
(یکی اصلاح شود و دیگری نه). حالا مرجع اصلی پروژه
ProfessionalInterpretationDAL است و این فایل فقط یک نام سازگار
نگه می‌دارد تا هیچ import قدیمی نشکند؛ هیچ منطق مستقلی این‌جا
نیست و هر دو نام به «یک» مسیر کد می‌رسند.
"""

from dal.professional_interpretation_dal import ProfessionalInterpretationDAL

# نام قدیمی برای سازگاری با importهای موجود
InterpretationDAL = ProfessionalInterpretationDAL

__all__ = ["InterpretationDAL", "ProfessionalInterpretationDAL"]
