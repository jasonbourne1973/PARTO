"""
انواع داده‌ای ثابت (Enumها) برای استانداردسازی Statusها در سراسر پروژه
نسخه کامل - ۱۴۰۵
"""

from enum import Enum


class ObservationStatus(str, Enum):
    """وضعیت‌های مشاهده"""
    POSITIVE = "مثبت"
    NEGATIVE = "منفی"
    NEUTRAL = "خنثی"
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.POSITIVE: "✅ مثبت",
            cls.NEGATIVE: "❌ منفی",
            cls.NEUTRAL: "⬜ خنثی",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [(cls.POSITIVE, "مثبت"), (cls.NEGATIVE, "منفی"), (cls.NEUTRAL, "خنثی")]


class InterventionStatus(str, Enum):
    """وضعیت‌های مداخله"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.PLANNED: "🟡 برنامه‌ریزی شده",
            cls.IN_PROGRESS: "🔄 در حال اجرا",
            cls.DONE: "✅ انجام شده",
            cls.COMPLETED: "🟢 تکمیل شده",
            cls.CANCELLED: "❌ لغو شده",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def get_icon(cls, value):
        """دریافت آیکون وضعیت"""
        icon_map = {
            cls.PLANNED: "🟡",
            cls.IN_PROGRESS: "🔄",
            cls.DONE: "✅",
            cls.COMPLETED: "🟢",
            cls.CANCELLED: "❌",
        }
        return icon_map.get(value, "📌")
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.PLANNED, "برنامه‌ریزی شده"),
            (cls.IN_PROGRESS, "در حال اجرا"),
            (cls.DONE, "انجام شده"),
            (cls.COMPLETED, "تکمیل شده"),
            (cls.CANCELLED, "لغو شده"),
        ]
    
    @classmethod
    def is_active(cls, value):
        """آیا مداخله فعال است؟"""
        active_statuses = [cls.PLANNED, cls.IN_PROGRESS]
        return value in active_statuses
    
    @classmethod
    def is_completed(cls, value):
        """آیا مداخله تکمیل شده است؟"""
        completed_statuses = [cls.COMPLETED, cls.DONE]
        return value in completed_statuses


class FollowUpStatus(str, Enum):
    """وضعیت‌های پیگیری"""
    PENDING = "pending"
    DONE = "done"
    CONTINUED = "continued"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.PENDING: "🟡 در انتظار",
            cls.DONE: "✅ انجام شده",
            cls.CONTINUED: "🔄 نیازمند ادامه",
            cls.CLOSED: "🔒 مختومه",
            cls.CANCELLED: "❌ لغو شده",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def get_icon(cls, value):
        """دریافت آیکون وضعیت"""
        icon_map = {
            cls.PENDING: "🟡",
            cls.DONE: "✅",
            cls.CONTINUED: "🔄",
            cls.CLOSED: "🔒",
            cls.CANCELLED: "❌",
        }
        return icon_map.get(value, "📌")
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.PENDING, "در انتظار"),
            (cls.DONE, "انجام شده"),
            (cls.CONTINUED, "نیازمند ادامه"),
            (cls.CLOSED, "مختومه"),
            (cls.CANCELLED, "لغو شده"),
        ]
    
    @classmethod
    def is_pending(cls, value):
        """آیا پیگیری در انتظار است؟"""
        return value == cls.PENDING
    
    @classmethod
    def is_done(cls, value):
        """آیا پیگیری انجام شده است؟"""
        return value == cls.DONE


class FollowUpResultType(str, Enum):
    """نوع نتیجه پیگیری"""
    IMPROVED = "improved"
    NO_CHANGE = "no_change"
    CONTINUED = "continued"
    NEW_STATUS = "new_status"
    INSUFFICIENT = "insufficient"
    NEEDS_MORE = "needs_more"
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.IMPROVED: "✅ بهبود مشاهده شد",
            cls.NO_CHANGE: "➖ بدون تغییر قابل مشاهده",
            cls.CONTINUED: "🔄 تداوم وضعیت",
            cls.NEW_STATUS: "🆕 وضعیت جدید",
            cls.INSUFFICIENT: "❓ اطلاعات ناکافی",
            cls.NEEDS_MORE: "🔔 نیازمند پیگیری بیشتر",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.IMPROVED, "بهبود مشاهده شد"),
            (cls.NO_CHANGE, "بدون تغییر قابل مشاهده"),
            (cls.CONTINUED, "تداوم وضعیت"),
            (cls.NEW_STATUS, "وضعیت جدید"),
            (cls.INSUFFICIENT, "اطلاعات ناکافی"),
            (cls.NEEDS_MORE, "نیازمند پیگیری بیشتر"),
        ]


class StudentProfileStatus(str, Enum):
    """وضعیت‌های پرونده سالانه دانش‌آموز"""
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    ARCHIVED = "archived"
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.ACTIVE: "🟢 فعال",
            cls.IN_PROGRESS: "🟡 در حال پیگیری",
            cls.CLOSED: "🔒 مختومه",
            cls.ARCHIVED: "📦 بایگانی شده",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.ACTIVE, "فعال"),
            (cls.IN_PROGRESS, "در حال پیگیری"),
            (cls.CLOSED, "مختومه"),
            (cls.ARCHIVED, "بایگانی شده"),
        ]
    
    @classmethod
    def is_active_profile(cls, value):
        """آیا پرونده فعال است؟"""
        active_statuses = [cls.ACTIVE, cls.IN_PROGRESS]
        return value in active_statuses


class AcademicYearStatus(str, Enum):
    """وضعیت‌های سال تحصیلی"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.ACTIVE: "🟢 فعال",
            cls.INACTIVE: "⚪ غیرفعال",
            cls.ARCHIVED: "📦 بایگانی شده",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.ACTIVE, "فعال"),
            (cls.INACTIVE, "غیرفعال"),
            (cls.ARCHIVED, "بایگانی شده"),
        ]


class StaffRole(str, Enum):
    """نقش‌های کادر مدرسه"""
    MANAGER = "manager"
    VICE_PRINCIPAL = "vice_principal"
    VICE_EDUCATION = "vice_education"
    TEACHER = "teacher"
    SPORT_COACH = "sport_coach"
    QURAN_COACH = "quran_coach"
    ART_COACH = "art_coach"
    COUNSELOR = "counselor"
    SYSTEM = "system"
    OTHER = "other"
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.MANAGER: "مدیر",
            cls.VICE_PRINCIPAL: "معاون پرورشی",
            cls.VICE_EDUCATION: "معاون آموزشی",
            cls.TEACHER: "معلم",
            cls.SPORT_COACH: "مربی ورزش",
            cls.QURAN_COACH: "مربی قرآن",
            cls.ART_COACH: "مربی هنر",
            cls.COUNSELOR: "مشاور",
            cls.SYSTEM: "سیستم",
            cls.OTHER: "سایر",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.MANAGER, "مدیر"),
            (cls.VICE_PRINCIPAL, "معاون پرورشی"),
            (cls.VICE_EDUCATION, "معاون آموزشی"),
            (cls.TEACHER, "معلم"),
            (cls.SPORT_COACH, "مربی ورزش"),
            (cls.QURAN_COACH, "مربی قرآن"),
            (cls.ART_COACH, "مربی هنر"),
            (cls.COUNSELOR, "مشاور"),
            (cls.SYSTEM, "سیستم"),
            (cls.OTHER, "سایر"),
        ]
    
    @classmethod
    def is_teacher(cls, value):
        """آیا نقش معلم است؟"""
        return value == cls.TEACHER
    
    @classmethod
    def is_manager(cls, value):
        """آیا نقش مدیریتی است؟"""
        managerial_roles = [cls.MANAGER, cls.VICE_PRINCIPAL, cls.VICE_EDUCATION]
        return value in managerial_roles


class Grade(int, Enum):
    """پایه‌های تحصیلی"""
    FIRST = 1
    SECOND = 2
    THIRD = 3
    FOURTH = 4
    FIFTH = 5
    SIXTH = 6
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.FIRST: "اول",
            cls.SECOND: "دوم",
            cls.THIRD: "سوم",
            cls.FOURTH: "چهارم",
            cls.FIFTH: "پنجم",
            cls.SIXTH: "ششم",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.FIRST, "اول"),
            (cls.SECOND, "دوم"),
            (cls.THIRD, "سوم"),
            (cls.FOURTH, "چهارم"),
            (cls.FIFTH, "پنجم"),
            (cls.SIXTH, "ششم"),
        ]
    
    @classmethod
    def is_graduating(cls, value):
        """آیا پایه ششم است (فارغ‌التحصیل)؟"""
        return value == cls.SIXTH
    
    @classmethod
    def get_next_grade(cls, value):
        """دریافت پایه بعدی"""
        if value < cls.SIXTH:
            return value + 1
        return None


class UserRole(str, Enum):
    """نقش‌های کاربری سیستم"""
    MANAGER = "manager"
    VICE_PRINCIPAL = "vice_principal"
    VICE_EDUCATION = "vice_education"
    TEACHER = "teacher"
    COUNSELOR = "counselor"
    SYSTEM = "system"
    VIEWER = "viewer"
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.MANAGER: "مدیر",
            cls.VICE_PRINCIPAL: "معاون پرورشی",
            cls.VICE_EDUCATION: "معاون آموزشی",
            cls.TEACHER: "معلم",
            cls.COUNSELOR: "مشاور",
            cls.SYSTEM: "سیستم",
            cls.VIEWER: "مشاهده‌گر",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.MANAGER, "مدیر"),
            (cls.VICE_PRINCIPAL, "معاون پرورشی"),
            (cls.VICE_EDUCATION, "معاون آموزشی"),
            (cls.TEACHER, "معلم"),
            (cls.COUNSELOR, "مشاور"),
            (cls.SYSTEM, "سیستم"),
            (cls.VIEWER, "مشاهده‌گر"),
        ]


class LivingStatus(str, Enum):
    """وضعیت زندگی با والدین"""
    BOTH = "با هر دو والدین"
    MOTHER_ONLY = "فقط با مادر"
    FATHER_ONLY = "فقط با پدر"
    GRANDPARENTS = "با پدربزرگ و مادربزرگ"
    OTHER = "سایر"
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.BOTH, "با هر دو والدین"),
            (cls.MOTHER_ONLY, "فقط با مادر"),
            (cls.FATHER_ONLY, "فقط با پدر"),
            (cls.GRANDPARENTS, "با پدربزرگ و مادربزرگ"),
            (cls.OTHER, "سایر"),
        ]


class CompetencyCategory(str, Enum):
    """دسته‌بندی شایستگی‌ها"""
    SOCIAL = "social"
    MORAL = "moral"
    BEHAVIORAL = "behavioral"
    EMOTIONAL = "emotional"
    EDUCATIONAL = "educational"
    COGNITIVE = "cognitive"
    SELF_MANAGEMENT = "self_management"
    PARTICIPATION = "participation"
    OTHER = "other"
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.SOCIAL: "اجتماعی",
            cls.MORAL: "اخلاقی",
            cls.BEHAVIORAL: "رفتاری",
            cls.EMOTIONAL: "عاطفی-هیجانی",
            cls.EDUCATIONAL: "آموزشی",
            cls.COGNITIVE: "شناختی",
            cls.SELF_MANAGEMENT: "خودمدیریتی",
            cls.PARTICIPATION: "مشارکت",
            cls.OTHER: "سایر",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.SOCIAL, "اجتماعی"),
            (cls.MORAL, "اخلاقی"),
            (cls.BEHAVIORAL, "رفتاری"),
            (cls.EMOTIONAL, "عاطفی-هیجانی"),
            (cls.EDUCATIONAL, "آموزشی"),
            (cls.COGNITIVE, "شناختی"),
            (cls.SELF_MANAGEMENT, "خودمدیریتی"),
            (cls.PARTICIPATION, "مشارکت"),
            (cls.OTHER, "سایر"),
        ]


class ActionType(str, Enum):
    """نوع عملیات برای Audit Log"""
    CREATE = "create"
    EDIT = "edit"
    DELETE_SOFT = "delete_soft"
    RESTORE = "restore"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    EXPORT = "export"
    STATUS_CHANGE = "status_change"
    ROLE_CHANGE = "role_change"
    YEAR_CHANGE = "year_change"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"
    BACKUP_DELETE = "backup_delete"
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.CREATE: "➕ ایجاد",
            cls.EDIT: "✏️ ویرایش",
            cls.DELETE_SOFT: "🗑️ حذف",
            cls.RESTORE: "↩️ بازیابی",
            cls.LOGIN_SUCCESS: "🔓 ورود موفق",
            cls.LOGIN_FAILED: "🔒 ورود ناموفق",
            cls.LOGOUT: "🚪 خروج",
            cls.EXPORT: "📤 خروجی",
            cls.STATUS_CHANGE: "📌 تغییر وضعیت",
            cls.ROLE_CHANGE: "👤 تغییر نقش",
            cls.YEAR_CHANGE: "📅 تغییر سال تحصیلی",
            cls.BACKUP_CREATE: "💾 ایجاد پشتیبان",
            cls.BACKUP_RESTORE: "🔄 بازیابی پشتیبان",
            cls.BACKUP_DELETE: "🗑️ حذف پشتیبان",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.CREATE, "ایجاد"),
            (cls.EDIT, "ویرایش"),
            (cls.DELETE_SOFT, "حذف"),
            (cls.RESTORE, "بازیابی"),
            (cls.LOGIN_SUCCESS, "ورود موفق"),
            (cls.LOGIN_FAILED, "ورود ناموفق"),
            (cls.LOGOUT, "خروج"),
            (cls.EXPORT, "خروجی"),
            (cls.STATUS_CHANGE, "تغییر وضعیت"),
            (cls.ROLE_CHANGE, "تغییر نقش"),
            (cls.YEAR_CHANGE, "تغییر سال تحصیلی"),
            (cls.BACKUP_CREATE, "ایجاد پشتیبان"),
            (cls.BACKUP_RESTORE, "بازیابی پشتیبان"),
            (cls.BACKUP_DELETE, "حذف پشتیبان"),
        ]


class EntityType(str, Enum):
    """نوع موجودیت برای Audit Log"""
    STUDENT = "student"
    OBSERVATION = "observation"
    INTERVENTION = "intervention"
    FOLLOWUP = "followup"
    STAFF = "staff"
    COMPETENCY = "competency"
    ACADEMIC_YEAR = "academic_year"
    PROFILE = "student_academic_profile"
    ASSIGNMENT = "teacher_assignment"
    AUTH = "auth"
    BACKUP = "backup"
    USER = "user"
    
    @classmethod
    def get_display(cls, value):
        """دریافت نمایش فارسی"""
        display_map = {
            cls.STUDENT: "دانش‌آموز",
            cls.OBSERVATION: "مشاهده",
            cls.INTERVENTION: "مداخله",
            cls.FOLLOWUP: "پیگیری",
            cls.STAFF: "کادر مدرسه",
            cls.COMPETENCY: "شایستگی",
            cls.ACADEMIC_YEAR: "سال تحصیلی",
            cls.PROFILE: "پرونده سالانه",
            cls.ASSIGNMENT: "اختصاص معلم",
            cls.AUTH: "احراز هویت",
            cls.BACKUP: "پشتیبان‌گیری",
            cls.USER: "کاربر",
        }
        return display_map.get(value, str(value))
    
    @classmethod
    def choices(cls):
        """لیست انتخاب‌ها برای کامبوباکس"""
        return [
            (cls.STUDENT, "دانش‌آموز"),
            (cls.OBSERVATION, "مشاهده"),
            (cls.INTERVENTION, "مداخله"),
            (cls.FOLLOWUP, "پیگیری"),
            (cls.STAFF, "کادر مدرسه"),
            (cls.COMPETENCY, "شایستگی"),
            (cls.ACADEMIC_YEAR, "سال تحصیلی"),
            (cls.PROFILE, "پرونده سالانه"),
            (cls.ASSIGNMENT, "اختصاص معلم"),
            (cls.AUTH, "احراز هویت"),
            (cls.BACKUP, "پشتیبان‌گیری"),
            (cls.USER, "کاربر"),
        ]