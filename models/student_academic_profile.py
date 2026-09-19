"""
مدل پرونده سالانه دانش‌آموز - با ارتباط به FamilyContext و ParentInterview
"""

from typing import ClassVar

from models.base import BaseModel


class StudentAcademicProfile(BaseModel):
    """
    مدل پرونده سالانه دانش‌آموز
    
    هر دانش‌آموز در هر سال تحصیلی یک پرونده دارد.
    این پرونده شامل اطلاعات زمینه‌ای خانواده و مصاحبه‌های والدین است.
    """
    
    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_GRADUATED = "graduated"
    STATUS_TRANSFERRED = "transferred"
    STATUS_DROPPED = "dropped"
    # ===== اصلاح (بازرسی سوم) =====
    # StudentAcademicProfileDAL.delete() و .archive() هر دو به
    # StudentAcademicProfile.STATUS_ARCHIVED ارجاع می‌دادند ولی این ثابت
    # روی مدل تعریف نشده بود (و روی BaseModel هم نیست):
    #
    #   AttributeError: type object 'StudentAcademicProfile'
    #                   has no attribute 'STATUS_ARCHIVED'
    #
    # یعنی «حذف» و «بایگانی» پروندهٔ تحصیلی از روز اول ۱۰۰٪ شکست
    # می‌خورد. همین باعث شد هیچ پرونده‌ای هرگز وضعیت 'archived' نگیرد —
    # و در نتیجه فیلتر قدیمی get_active_by_student که
    # `NOT IN ('archived','closed')` بود عملاً هیچ رکوردی را فیلتر
    # نمی‌کرد (واژگان مرده). اسکن سیستماتیک همهٔ ارجاع‌های
    # «ثابت کلاسی» در پروژه: از ۱۲۷ ارجاع، فقط همین ۲ مورد خراب بودند.
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
        (STATUS_ACTIVE, "فعال"),
        (STATUS_INACTIVE, "غیرفعال"),
        (STATUS_GRADUATED, "فارغ‌التحصیل"),
        (STATUS_TRANSFERRED, "انتقالی"),
        (STATUS_DROPPED, "انصراف داده"),
        (STATUS_ARCHIVED, "بایگانی‌شده"),
    ]
    
    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.student_id = None          # ارجاع به Student
        self.academic_year_id = None    # ارجاع به AcademicYear
        
        # ===== اطلاعات پایه =====
        self.grade = None               # پایه تحصیلی (1-6)
        self.class_name = None          # نام کلاس
        self.status = self.STATUS_ACTIVE  # وضعیت پرونده
        self.status_history = None      # تاریخچه تغییرات وضعیت (JSON)
        
        # ===== اطلاعات زمینه‌ای خانواده =====
        # این فیلدها در دیتابیس نیستند - برای دسترسی سریع
        self.family_context = None      # شیء FamilyContext
        self.parent_interviews = []     # لیست مصاحبه‌های والدین
    
    @property
    def grade_display(self):
        """نمایش پایه به فارسی"""
        grade_map = {
            1: "اول",
            2: "دوم",
            3: "سوم",
            4: "چهارم",
            5: "پنجم",
            6: "ششم",
        }
        return grade_map.get(self.grade, str(self.grade))
    
    @property
    def status_display(self):
        """نمایش وضعیت به فارسی"""
        status_map = {
            self.STATUS_ACTIVE: "فعال",
            self.STATUS_INACTIVE: "غیرفعال",
            self.STATUS_GRADUATED: "فارغ‌التحصیل",
            self.STATUS_TRANSFERRED: "انتقالی",
            self.STATUS_DROPPED: "انصراف داده",
            self.STATUS_ARCHIVED: "بایگانی‌شده",
        }
        return status_map.get(self.status, self.status)
    
    @property
    def full_class_name(self):
        """نام کامل کلاس (پایه + کلاس)"""
        if self.grade and self.class_name:
            return f"{self.grade_display} - {self.class_name}"
        elif self.class_name:
            return self.class_name
        elif self.grade:
            return self.grade_display
        return "نامشخص"
    
    @property
    def has_family_context(self):
        """آیا اطلاعات زمینه‌ای خانواده ثبت شده است؟"""
        return self.family_context is not None
    
    @property
    def interview_count(self):
        """تعداد مصاحبه‌های والدین"""
        return len(self.parent_interviews)
    
    @property
    def last_interview_date(self):
        """تاریخ آخرین مصاحبه"""
        if self.parent_interviews:
            # مرتب‌سازی بر اساس تاریخ
            sorted_interviews = sorted(
                self.parent_interviews, 
                key=lambda x: x.interview_date or "", 
                reverse=True
            )
            return sorted_interviews[0].interview_date
        return None
    
    def add_family_context(self, family_context):
        """افزودن اطلاعات زمینه‌ای خانواده"""
        self.family_context = family_context
        family_context.student_profile_id = self.id
    
    def add_parent_interview(self, interview):
        """افزودن مصاحبه والدین"""
        if interview not in self.parent_interviews:
            self.parent_interviews.append(interview)
            interview.student_profile_id = self.id
    
    def get_completed_interviews(self):
        """دریافت مصاحبه‌های انجام شده"""
        return [i for i in self.parent_interviews if i.is_completed]
    
    def get_scheduled_interviews(self):
        """دریافت مصاحبه‌های برنامه‌ریزی شده"""
        return [i for i in self.parent_interviews if i.is_scheduled]
    
    def soft_delete(self, user_id=None):
        """حذف منطقی پرونده"""
        super().soft_delete(user_id)
    
    def restore(self):
        """بازیابی پرونده از حذف منطقی"""
        super().restore()
    
    def validate(self):
        errors = []
        if not self.student_id:
            errors.append("دانش‌آموز باید انتخاب شود")
        if not self.academic_year_id:
            errors.append("سال تحصیلی باید انتخاب شود")
        if self.grade and self.grade not in range(1, 7):
            errors.append("پایه باید بین 1 تا 6 باشد")
        if self.status not in [s[0] for s in self.STATUS_CHOICES]:
            errors.append("وضعیت پرونده نامعتبر است")
        return errors