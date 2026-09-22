"""
ثابت‌های پروژه - نسخه بازطراحی شده با Enumها
"""

from models.enums import (
    AcademicYearStatus,
    ActionType,
    CompetencyCategory,
    EntityType,
    FollowUpResultType,
    FollowUpStatus,
    Grade,
    InterventionStatus,
    ObservationStatus,
    StaffRole,
    StudentProfileStatus,
    UserRole,
)

# ============================================================
# نقش‌های کادر مدرسه (برای سازگاری با کدهای موجود)
# ============================================================
STAFF_ROLES = StaffRole.choices()

# ============================================================
# محیط‌های مشاهده
# ============================================================
OBSERVATION_LOCATIONS = [
    "کلاس",
    "حیاط",
    "نمازخانه",
    "زنگ ورزش",
    "اردو",
    "مراسم",
    "زنگ تفریح",
    "سرویس",
    "سالن اجتماعات",
    "سایر"
]

# ============================================================
# انواع مشاهده (برای سازگاری با کدهای موجود)
# ============================================================
OBSERVATION_TYPES = ObservationStatus.choices()
OBSERVATION_TYPES_VALUES = [obs_type.value for obs_type in ObservationStatus]

# ============================================================
# انواع مداخله (برای سازگاری با کدهای موجود)
# ============================================================
INTERVENTION_TYPES = [
    ("individual_talk", "گفتگوی فردی"),
    ("group_talk", "گفتگوی گروهی"),
    ("parent_call", "تماس با والدین"),
    ("parent_meeting", "جلسه با والدین"),
    ("responsibility", "سپردن مسئولیت"),
    ("encouragement", "تشویق"),
    ("group_activity", "فعالیت گروهی"),
    ("educational_game", "بازی تربیتی"),
    ("referral", "ارجاع به مشاور"),
    ("counseling", "مشاوره"),
    ("seat_change", "تغییر جای نشستن"),
    ("peer_helper", "همیار دانش‌آموز"),
    ("warning", "تذکر شفاهی"),
    ("other", "سایر")
]

# ============================================================
# انواع پیگیری (برای سازگاری با کدهای موجود)
# ============================================================
FOLLOWUP_TYPES = FollowUpStatus.choices()
FOLLOWUP_STATUS_VALUES = [status.value for status in FollowUpStatus]

# ============================================================
# انواع نتیجه پیگیری
# ============================================================
FOLLOWUP_RESULT_TYPES = FollowUpResultType.choices()
FOLLOWUP_RESULT_VALUES = [result.value for result in FollowUpResultType]

# ============================================================
# پایه‌های تحصیلی (برای سازگاری با کدهای موجود)
# ============================================================
GRADES = [grade.value for grade in Grade]
GRADE_NAMES = {grade.value: grade.get_display(grade.value) for grade in Grade}

# ============================================================
# وضعیت‌های زندگی با والدین (برای سازگاری با کدهای موجود)
# ============================================================
# ✅ اصلاح: تبدیل به لیستی از رشته‌ها به جای tuple
LIVING_STATUSES = [
    "با هر دو والدین",
    "فقط با مادر",
    "فقط با پدر",
    "با پدربزرگ و مادربزرگ",
    "سایر"
]

# ============================================================
# دسته‌بندی شایستگی‌ها (برای سازگاری با کدهای موجود)
# ============================================================
COMPETENCY_CATEGORIES = CompetencyCategory.choices()

# ============================================================
# وضعیت‌های پرونده دانش‌آموز
# ============================================================
PROFILE_STATUSES = StudentProfileStatus.choices()
PROFILE_STATUS_VALUES = [status.value for status in StudentProfileStatus]

# ============================================================
# وضعیت‌های سال تحصیلی
# ============================================================
ACADEMIC_YEAR_STATUSES = AcademicYearStatus.choices()
ACADEMIC_YEAR_STATUS_VALUES = [status.value for status in AcademicYearStatus]

# ============================================================
# وضعیت‌های مداخله
# ============================================================
INTERVENTION_STATUSES = InterventionStatus.choices()
INTERVENTION_STATUS_VALUES = [status.value for status in InterventionStatus]

# ============================================================
# وضعیت‌های پیگیری
# ============================================================
FOLLOWUP_STATUSES = FollowUpStatus.choices()
FOLLOWUP_STATUS_VALUES = [status.value for status in FollowUpStatus]

# ============================================================
# نقش‌های کاربری
# ============================================================
USER_ROLES = UserRole.choices()
USER_ROLE_VALUES = [role.value for role in UserRole]

# ============================================================
# نوع عملیات‌ها (برای Audit Log)
# ============================================================
ACTION_TYPES = ActionType.choices()
ACTION_TYPE_VALUES = [action.value for action in ActionType]

# ============================================================
# نوع موجودیت‌ها (برای Audit Log)
# ============================================================
ENTITY_TYPES = EntityType.choices()
ENTITY_TYPE_VALUES = [entity.value for entity in EntityType]

# ============================================================
# توابع کمکی برای دریافت وضعیت‌ها
# ============================================================

# ============================================================
# نگاشت‌های سریع برای استفاده در Viewها
# ============================================================

# نگاشت وضعیت‌های مداخله به آیکون
INTERVENTION_STATUS_ICON = {
    status.value: status.get_icon(status.value) for status in InterventionStatus
}

# نگاشت وضعیت‌های پیگیری به آیکون
FOLLOWUP_STATUS_ICON = {
    status.value: status.get_icon(status.value) for status in FollowUpStatus
}

# نگاشت پایه‌ها به نمایش فارسی
GRADE_DISPLAY_MAP = {grade.value: grade.get_display(grade.value) for grade in Grade}

# نگاشت نقش‌های کادر به نمایش فارسی
STAFF_ROLE_DISPLAY_MAP = {role.value: role.get_display(role.value) for role in StaffRole}

# ============================================================
# نام‌های قدیمی برای سازگاری با کدهای موجود
# ============================================================
OBSERVATION_ENVIRONMENTS = OBSERVATION_LOCATIONS