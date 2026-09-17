"""
مدل انتساب معلم به دانش‌آموز
"""

from models.base import BaseModel


class TeacherAssignment(BaseModel):
    """
    مدل انتساب معلم به دانش‌آموز
    
    این مدل ارتباط بین معلمان و دانش‌آموزان را مدیریت می‌کند.
    هر دانش‌آموز می‌تواند چند معلم داشته باشد (مثلاً معلم اصلی، معلم ورزش، ...)
    و هر معلم می‌تواند چند دانش‌آموز داشته باشد.
    """
    
    def __init__(self):
        super().__init__()
        self.student_id = None          # ارجاع به Student
        self.staff_id = None            # ارجاع به Staff (که نقش teacher دارد)
        self.academic_year_id = None    # ارجاع به AcademicYear
        self.grade = None               # پایه (برای اطلاعات بیشتر)
        self.class_name = None          # کلاس (برای اطلاعات بیشتر)
        self.is_active = 1              # 0=غیرفعال, 1=فعال
        self.assigned_date = None       # تاریخ انتساب (شمسی)
        self.updated_at = None          # تاریخ آخرین تغییر
        
        # فیلدهای کمکی برای نمایش
        self.student_name = None
        self.teacher_name = None
        self.academic_year_title = None
    
    @property
    def status_display(self):
        """نمایش وضعیت به فارسی"""
        if self.is_active == 1:
            return "🟢 فعال"
        else:
            return "🔴 غیرفعال"
    
    def validate(self):
        errors = []
        if not self.student_id:
            errors.append("دانش‌آموز باید انتخاب شود")
        if not self.staff_id:
            errors.append("معلم باید انتخاب شود")
        if not self.academic_year_id:
            errors.append("سال تحصیلی باید انتخاب شود")
        return errors