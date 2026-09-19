"""
ابزارهای امنیتی - هش کردن رمز عبور با PBKDF2-HMAC-SHA256
"""

import hashlib
import hmac
import secrets
from datetime import timedelta
from enum import Enum

from utils.logger import get_logger
from utils.time_utils import utc_now

logger = get_logger(__name__)


class UserRole(Enum):
    """
    نقش‌های کاربری سیستم

    ===== اصلاح مهم =====
    این تعریف با `enums.UserRole` موازی بود ولی یک نقش نداشت:
    VICE_EDUCATION (معاون آموزشی).

    نتیجه: کاربری با نقش «معاون آموزشی» که در settings_page ساخته
    می‌شد، در ROLE_PERMISSIONS هیچ کلیدی نداشت و مجوزهایش به لیست
    خالی تبدیل می‌شد. همین‌طور برای SYSTEM.

    بهترین راه این است که فقط از `enums.UserRole` استفاده شود و این
    کپی حذف شود. اما چون فایل‌های زیادی این کلاس را import کرده‌اند،
    فعلاً نقش گمشده اضافه می‌شود و ROLE_PERMISSIONS کامل می‌شود تا
    چیزی نشکند.
    """
    MANAGER = "manager"           # مدیر - دسترسی کامل
    VICE_PRINCIPAL = "vice_principal"  # معاون پرورشی
    VICE_EDUCATION = "vice_education"  # معاون آموزشی
    TEACHER = "teacher"           # معلم
    COUNSELOR = "counselor"       # مشاور
    SYSTEM = "system"             # سیستم (داخلی)
    VIEWER = "viewer"             # مشاهده‌گر (فقط خواندنی)
    # ===== افزودن (بازرسی هفتم) =====
    # این سه نقش در models/enums.py::StaffRole وجود داشتند و در
    # جدول staff ذخیره می‌شوند، ولی در این enum نبودند.
    SPORT_COACH = "sport_coach"   # مربی ورزش
    QURAN_COACH = "quran_coach"   # مربی قرآن
    ART_COACH = "art_coach"       # مربی هنر
    OTHER = "other"               # سایر کادر


class Permission(Enum):
    """مجوزهای دسترسی"""
    # مدیریت کاربران
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    
    # مدیریت دانش‌آموزان
    VIEW_STUDENTS = "view_students"
    CREATE_STUDENT = "create_student"
    EDIT_STUDENT = "edit_student"
    DELETE_STUDENT = "delete_student"
    
    # مدیریت مشاهدات
    VIEW_OBSERVATIONS = "view_observations"
    CREATE_OBSERVATION = "create_observation"
    EDIT_OBSERVATION = "edit_observation"
    DELETE_OBSERVATION = "delete_observation"
    
    # مدیریت مداخلات
    VIEW_INTERVENTIONS = "view_interventions"
    CREATE_INTERVENTION = "create_intervention"
    EDIT_INTERVENTION = "edit_intervention"
    DELETE_INTERVENTION = "delete_intervention"
    
    # مدیریت پیگیری‌ها
    VIEW_FOLLOWUPS = "view_followups"
    CREATE_FOLLOWUP = "create_followup"
    EDIT_FOLLOWUP = "edit_followup"
    DELETE_FOLLOWUP = "delete_followup"
    
    # مدیریت گزارش‌ها
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"
    
    # مدیریت تنظیمات
    VIEW_SETTINGS = "view_settings"
    EDIT_SETTINGS = "edit_settings"
    
    # مدیریت پشتیبان‌گیری
    CREATE_BACKUP = "create_backup"
    RESTORE_BACKUP = "restore_backup"
    DELETE_BACKUP = "delete_backup"
    
    # مدیریت سال تحصیلی
    MANAGE_ACADEMIC_YEARS = "manage_academic_years"


# ===== نقش‌ها و مجوزهای آنها =====
ROLE_PERMISSIONS = {
    UserRole.MANAGER.value: [
        # دسترسی کامل به همه چیز
        p.value for p in Permission
    ],
    UserRole.VICE_PRINCIPAL.value: [
        Permission.VIEW_STUDENTS.value,
        Permission.CREATE_STUDENT.value,
        Permission.EDIT_STUDENT.value,
        Permission.VIEW_OBSERVATIONS.value,
        Permission.CREATE_OBSERVATION.value,
        Permission.EDIT_OBSERVATION.value,
        Permission.VIEW_INTERVENTIONS.value,
        Permission.CREATE_INTERVENTION.value,
        Permission.EDIT_INTERVENTION.value,
        Permission.VIEW_FOLLOWUPS.value,
        Permission.CREATE_FOLLOWUP.value,
        Permission.EDIT_FOLLOWUP.value,
        Permission.VIEW_REPORTS.value,
        Permission.EXPORT_REPORTS.value,
        Permission.VIEW_SETTINGS.value,
        Permission.CREATE_BACKUP.value,
        Permission.RESTORE_BACKUP.value,
        Permission.MANAGE_ACADEMIC_YEARS.value,
    ],
    UserRole.TEACHER.value: [
        Permission.VIEW_STUDENTS.value,
        Permission.CREATE_STUDENT.value,
        Permission.EDIT_STUDENT.value,
        Permission.VIEW_OBSERVATIONS.value,
        Permission.CREATE_OBSERVATION.value,
        Permission.EDIT_OBSERVATION.value,
        Permission.VIEW_INTERVENTIONS.value,
        Permission.CREATE_INTERVENTION.value,
        Permission.VIEW_FOLLOWUPS.value,
        Permission.CREATE_FOLLOWUP.value,
        Permission.VIEW_REPORTS.value,
    ],
    UserRole.COUNSELOR.value: [
        Permission.VIEW_STUDENTS.value,
        Permission.VIEW_OBSERVATIONS.value,
        Permission.CREATE_OBSERVATION.value,
        Permission.VIEW_INTERVENTIONS.value,
        Permission.CREATE_INTERVENTION.value,
        Permission.EDIT_INTERVENTION.value,
        Permission.VIEW_FOLLOWUPS.value,
        Permission.CREATE_FOLLOWUP.value,
        Permission.EDIT_FOLLOWUP.value,
        Permission.VIEW_REPORTS.value,
        Permission.EXPORT_REPORTS.value,
    ],
    # ===== اصلاح: نقش‌هایی که قبلاً هیچ مجوزی نداشتند =====
    UserRole.VICE_EDUCATION.value: [
        # معاون آموزشی: مشابه معاون پرورشی، بدون دسترسی به پشتیبان‌گیری
        Permission.VIEW_STUDENTS.value,
        Permission.CREATE_STUDENT.value,
        Permission.EDIT_STUDENT.value,
        Permission.VIEW_OBSERVATIONS.value,
        Permission.CREATE_OBSERVATION.value,
        Permission.EDIT_OBSERVATION.value,
        Permission.VIEW_INTERVENTIONS.value,
        Permission.CREATE_INTERVENTION.value,
        Permission.EDIT_INTERVENTION.value,
        Permission.VIEW_FOLLOWUPS.value,
        Permission.CREATE_FOLLOWUP.value,
        Permission.EDIT_FOLLOWUP.value,
        Permission.VIEW_REPORTS.value,
        Permission.EXPORT_REPORTS.value,
        Permission.VIEW_SETTINGS.value,
        Permission.MANAGE_ACADEMIC_YEARS.value,
    ],
    UserRole.SYSTEM.value: [
        # نقش داخلی: دسترسی کامل، چون کارهای سیستمی
        # (زمان‌بند اعلان‌ها، پشتیبان‌گیری خودکار) را انجام می‌دهد
        p.value for p in Permission
    ],
    UserRole.VIEWER.value: [
        Permission.VIEW_STUDENTS.value,
        Permission.VIEW_OBSERVATIONS.value,
        Permission.VIEW_INTERVENTIONS.value,
        Permission.VIEW_FOLLOWUPS.value,
        Permission.VIEW_REPORTS.value,
    ],

    # ===== افزودن (بازرسی هفتم — اولویت ۵) =====
    # این نقش‌ها در جدول staff وجود دارند (models/enums.py::StaffRole)
    # و می‌توانند برای کاربران ساخته شوند، ولی قبلاً در هیچ کلیدی از
    # ROLE_PERMISSIONS نبودند؛ مجوزشان به «پیش‌فرض» می‌افتاد و
    # مدیر نمی‌توانست رفتارشان را تعیین کند.
    #
    # سیاست پیشنهادی: مربیان مثل معلم هستند ولی اجازهٔ *ثبت* مشاهده
    # را هم دارند (چون در فعالیت‌های فوق‌برنامه با دانش‌آموز کار
    # می‌کنند)؛ گرچه الزاماً نباید بتوانند پروندهٔ دانش‌آموز را
    # تغییر دهند. اگر سیاست مدرسه چیز دیگری است، فقط همین لیست‌ها
    # را ویرایش کنید — نقطهٔ واحدی برای تصمیم وجود دارد.
    UserRole.SPORT_COACH.value: [
        Permission.VIEW_STUDENTS.value,
        Permission.VIEW_OBSERVATIONS.value,
        Permission.CREATE_OBSERVATION.value,
        Permission.VIEW_INTERVENTIONS.value,
        Permission.VIEW_FOLLOWUPS.value,
        Permission.VIEW_REPORTS.value,
    ],
    UserRole.QURAN_COACH.value: [
        Permission.VIEW_STUDENTS.value,
        Permission.VIEW_OBSERVATIONS.value,
        Permission.CREATE_OBSERVATION.value,
        Permission.VIEW_INTERVENTIONS.value,
        Permission.VIEW_FOLLOWUPS.value,
        Permission.VIEW_REPORTS.value,
    ],
    UserRole.ART_COACH.value: [
        Permission.VIEW_STUDENTS.value,
        Permission.VIEW_OBSERVATIONS.value,
        Permission.CREATE_OBSERVATION.value,
        Permission.VIEW_INTERVENTIONS.value,
        Permission.VIEW_FOLLOWUPS.value,
        Permission.VIEW_REPORTS.value,
    ],
    UserRole.OTHER.value: [
        # «سایر»: فقط مشاهده — تصمیم دقیق با مدیر مدرسه است
        Permission.VIEW_STUDENTS.value,
        Permission.VIEW_OBSERVATIONS.value,
        Permission.VIEW_INTERVENTIONS.value,
        Permission.VIEW_FOLLOWUPS.value,
        Permission.VIEW_REPORTS.value,
    ],
}


# ===== نگاشت نقش‌های مترادف/قدیمی (بازرسی ششم) =====
# ممکن است در دیتابیسِ به‌روزنشده مقدارهایی مثل admin یا
# vice_principle (با غلط املایی) مانده باشد. بدون این نگاشت، این
# نقش‌ها «ناشناخته» می‌شدند و مجوزهایشان به لیست پیش‌فرض می‌رسید.
ROLE_ALIASES = {
    'admin': 'manager',
    'administrator': 'manager',
    'modir': 'manager',
    'principal': 'manager',
    'vice_principle': 'vice_principal',
    'deputy': 'vice_principal',
}

# مجوزهای پیش‌فرض برای نقشِ ناشناخته.
# سیاست: «کم‌ترین دسترسیِ محتمل» — منوهای خواندنی باز می‌مانند
# ولی کارهای مدیریتی (کاربران، پشتیبان‌گیری، ساختار آموزشی) بسته
# است. قبلاً نقش ناشناخته عملاً همه‌چیز داشت، چون هیچ‌جا بررسی
# نمی‌شد.
FALLBACK_ROLE_PERMISSIONS = list(ROLE_PERMISSIONS[UserRole.VIEWER.value])


def get_role_permissions(role):
    """
    مجوزهای یک نقش را برمی‌گرداند (تنها مرجع مورد اعتماد)

    این تابع همان منبعی است که هم SessionManager.has_permission و
    هم رابط کاربری از آن استفاده می‌کنند تا تعریف مجوزها دو تایی
    (و ناهمخوان) نشود.

    Args:
        role: رشتهٔ نقش (مثلاً 'manager'، 'teacher'، 'counselor')

    Returns:
        list[str]: لیست مجوزها. برای نقشِ ناشناخته، لیست پیش‌فرضِ
        FALLBACK_ROLE_PERMISSIONS برمی‌گردد (نه لیست خالی؛ چون لیست
        خالی در UI یعنی «کاربر هیچ صفحه‌ای نمی‌بیند»).
    """
    key = (role or '').strip().lower()
    key = ROLE_ALIASES.get(key, key)
    if key in ROLE_PERMISSIONS:
        return list(ROLE_PERMISSIONS[key])
    return list(FALLBACK_ROLE_PERMISSIONS)


class Security:
    """کلاس ابزارهای امنیتی - با PBKDF2-HMAC-SHA256 برای هش کردن رمز عبور"""
    
    # ثابت‌های PBKDF2
    PBKDF2_ITERATIONS = 100000  # تعداد تکرار
    PBKDF2_HASH_ALGORITHM = 'sha256'  # الگوریتم هش
    # حداقل طول رمز عبور — تنها مرجع معتبر در کل پروژه
    # (قبلاً ۶ در security و ۸ در change_password_dialog بود)
    MIN_PASSWORD_LENGTH = 8
    SALT_BYTES = 32  # طول Salt به بایت
    
    @staticmethod
    def hash_password(password):
        """
        هش کردن رمز عبور با استفاده از PBKDF2-HMAC-SHA256 + Salt
        
        فرمت خروجی: "salt:iterations:hash"
        salt: رمز تصادفی به صورت هگز
        iterations: تعداد تکرار
        hash: هش نهایی به صورت هگز
        
        Args:
            password: رمز عبور به صورت متن ساده
            
        Returns:
            str: هش رمز عبور شامل salt و iterations
        """
        if not password:
            return None
        
        # تولید Salt تصادفی
        salt = secrets.token_bytes(Security.SALT_BYTES)
        
        # هش کردن با PBKDF2
        key = hashlib.pbkdf2_hmac(
            Security.PBKDF2_HASH_ALGORITHM,
            password.encode('utf-8'),
            salt,
            Security.PBKDF2_ITERATIONS
        )
        
        # ذخیره Salt (به هگز) + تعداد تکرار + هش (به هگز)
        salt_hex = salt.hex()
        hash_hex = key.hex()
        
        return f"{salt_hex}:{Security.PBKDF2_ITERATIONS}:{hash_hex}"
    
    @staticmethod
    def verify_password(password, hashed_password):
        """
        بررسی رمز عبور با هش شده
        
        Args:
            password: رمز عبور وارد شده
            hashed_password: هش ذخیره شده در دیتابیس
            
        Returns:
            bool: آیا رمز عبور صحیح است؟
        """
        if not password or not hashed_password:
            return False
        
        try:
            # جداسازی اجزا
            parts = hashed_password.split(':')
            if len(parts) != 3:
                # پشتیبانی از فرمت قدیمی (salt:hash)
                if len(parts) == 2:
                    return Security._verify_legacy(password, hashed_password)
                return False
            
            salt_hex, iterations_str, stored_hash = parts
            iterations = int(iterations_str)
            
            # تبدیل Salt از هگز به بایت
            salt = bytes.fromhex(salt_hex)
            
            # محاسبه هش با همان پارامترها
            computed_key = hashlib.pbkdf2_hmac(
                Security.PBKDF2_HASH_ALGORITHM,
                password.encode('utf-8'),
                salt,
                iterations
            )
            computed_hash = computed_key.hex()
            
            # مقایسه با استفاده از compare_digest برای جلوگیری از timing attack
            return hmac.compare_digest(computed_hash, stored_hash)
            
        except Exception as e:
            logger.error(f"⚠️ خطا در بررسی رمز عبور: {e}")
            return False
    
    @staticmethod
    def _verify_legacy(password, legacy_hashed):
        """
        پشتیبانی از فرمت قدیمی SHA-256 برای سازگاری با نسخه‌های قبلی
        
        فرمت قدیمی: "salt:hash"
        """
        try:
            parts = legacy_hashed.split(':')
            if len(parts) != 2:
                return False
            
            salt, stored_hash = parts
            combined = salt + password
            computed_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
            
            return hmac.compare_digest(computed_hash, stored_hash)
        except Exception:
            return False
    
    @staticmethod
    def generate_token():
        """تولید توکن امن برای جلسات"""
        return secrets.token_hex(32)
    
    @staticmethod
    def is_password_strong(password):
        """بررسی قدرت رمز عبور"""
        # ===== اصلاح =====
        # نسخه قبلی حداقل ۶ کاراکتر می‌خواست، ولی
        # change_password_dialog حداقل ۸ کاراکتر می‌خواهد.
        # نتیجه: رمزی با ۶ یا ۷ کاراکتر در «تنظیمات ← مدیریت کاربران»
        # پذیرفته می‌شد ولی در «تغییر رمز عبور» رد می‌شد — دو قانون
        # متناقض برای یک چیز.
        # حالا هر دو روی یک عدد هستند و عدد از یک ثابت مشترک می‌آید.
        if len(password) < Security.MIN_PASSWORD_LENGTH:
            return False, f"رمز عبور باید حداقل {Security.MIN_PASSWORD_LENGTH} کاراکتر باشد."
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=<>?/" for c in password)
        
        if not (has_upper and has_lower and has_digit):
            return False, "رمز عبور باید شامل حروف بزرگ، کوچک و اعداد باشد."
        
        if not has_special:
            return False, "رمز عبور باید شامل حداقل یک کاراکتر خاص (!@#$%^&*) باشد."
        
        return True, "رمز عبور قوی است."
    
    @staticmethod
    def sanitize_filename(filename):
        """پاکسازی نام فایل برای جلوگیری از مسائل امنیتی"""
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    
    @staticmethod
    def get_file_extension(filename):
        """دریافت پسوند فایل"""
        if '.' in filename:
            return filename.rsplit('.', 1)[1].lower()
        return ''
    
    @staticmethod
    def is_allowed_file_type(filename, allowed_types):
        """بررسی نوع فایل مجاز"""
        ext = Security.get_file_extension(filename)
        return ext in allowed_types


# ===== حذف encrypt_data و decrypt_data جعلی =====
# توابع encrypt_data و decrypt_data حذف شدند
# زیرا فقط Base64 Encoding بودند و رمزنگاری واقعی نبودند
# در صورت نیاز به رمزنگاری واقعی، از کتابخانه cryptography استفاده شود


class SessionManager:
    """مدیریت جلسات کاربران"""
    
    def __init__(self):
        self._sessions = {}
        self._session_timeout = 3600  # 1 ساعت
        self._max_sessions_per_user = 3  # حداکثر جلسه همزمان
    
    def create_session(self, user_id, user_role, username=None):
        """ایجاد جلسه جدید"""
        # بررسی تعداد جلسات فعال کاربر
        active_sessions = [s for s in self._sessions.values() if s.get('user_id') == user_id and not s.get('expired')]
        if len(active_sessions) >= self._max_sessions_per_user:
            return None, "تعداد جلسات همزمان برای این کاربر به حداکثر رسیده است."
        
        token = Security.generate_token()
        now = utc_now()
        
        self._sessions[token] = {
            'user_id': user_id,
            'user_role': user_role,
            'username': username or f"user_{user_id}",
            'created_at': now,
            'last_activity': now,
            'expires_at': now + timedelta(seconds=self._session_timeout),
            'expired': False,
            'ip_address': None,
        }
        
        return token, "جلسه با موفقیت ایجاد شد."
    
    def validate_session(self, token):
        """اعتبارسنجی جلسه"""
        if token not in self._sessions:
            return None
        
        session = self._sessions[token]
        
        # بررسی انقضا
        if session.get('expired', False):
            return None
        
        # بررسی timeout
        now = utc_now()
        if (now - session['last_activity']).seconds > self._session_timeout:
            self.end_session(token)
            return None
        
        # به‌روزرسانی زمان آخرین فعالیت
        session['last_activity'] = now
        session['expires_at'] = now + timedelta(seconds=self._session_timeout)
        
        return session
    
    def end_session(self, token):
        """پایان جلسه"""
        if token in self._sessions:
            self._sessions[token]['expired'] = True
            del self._sessions[token]
            return True
        return False
    
    def get_current_user(self, token):
        """دریافت کاربر فعلی از جلسه"""
        session = self.validate_session(token)
        if session:
            return session['user_id'], session['user_role'], session.get('username')
        return None, None, None
    
    def has_permission(self, token, permission):
        """بررسی دسترسی کاربر به یک مجوز خاص"""
        session = self.validate_session(token)
        if not session:
            return False
        
        user_role = session.get('user_role')
        # ===== اصلاح (بازرسی ششم) =====
        # قبلاً دو مسیر جدا برای مجوزها وجود داشت: این متد از
        # ROLE_PERMISSIONS می‌خواند و رابط کاربری از هیچ‌جا. حالا هر
        # دو از get_role_permissions استفاده می‌کنند و نقش‌های
        # مترادف/ناشناخته هم یک رفتار دارند.
        return permission in get_role_permissions(user_role)
    
    def has_any_permission(self, token, permissions):
        """بررسی دسترسی کاربر به حداقل یکی از مجوزها"""
        return any(self.has_permission(token, perm) for perm in permissions)
    
    def get_all_sessions(self):
        """دریافت لیست همه جلسات فعال"""
        sessions = []
        for token, session in self._sessions.items():
            if not session.get('expired', False):
                sessions.append({
                    'token': token[:8] + '...',  # فقط بخشی از توکن برای امنیت
                    'user_id': session['user_id'],
                    'username': session.get('username', 'نامشخص'),
                    'created_at': session['created_at'].isoformat(),
                    'last_activity': session['last_activity'].isoformat(),
                })
        return sessions


# ===== یکسان‌سازی نام موجودیت در Audit Log (بازرسی هفتم) =====
# کلید = نام مفردی که سرویس‌ها استفاده می‌کنند، مقدار = نام جدول
# دیتابیس که تریگرها در entity_type می‌نویسند.
#
# (بازرسی دوازدهم) جدول‌هایی که تازه تریگر گرفته‌اند هم اضافه شدند
# (مفرد و جمع) تا BaseService._audit_handled_by_trigger آن‌ها را
# بشناسد و ثبت دستیِ تکراری انجام نشود. ورودی جمعِ جدول‌های قبلی هم
# صریحاً به خودشان نگاشت شد تا اگر سرویسی نام جدول را پاس داد، باز
# هم تکراری ثبت نشود (رفتار normalize برای این ورودی‌ها عوض نمی‌شود).
AUDIT_ENTITY_ALIASES = {
    'student': 'students',
    'observation': 'observations',
    'intervention': 'interventions',
    'followup': 'followups',
    'student_academic_profile': 'student_academic_profiles',
    'profile': 'student_academic_profiles',
    'staff': 'staff',
    'competency': 'competencies',
    'user': 'users',
    'attachment': 'attachments',
    'family_context': 'family_contexts',
    'parent_interview': 'parent_interviews',
    'counseling_session': 'counseling_sessions',
    'screening': 'screenings',
    'screening_result': 'screening_results',
    'professional_interpretation': 'professional_interpretations',
    'interpretation': 'professional_interpretations',
    'individual_goal': 'individual_goals',
    'extracurricular_activity': 'extracurricular_activities',
    'recommendation': 'recommendations',
    'students': 'students',
    'observations': 'observations',
    'interventions': 'interventions',
    'followups': 'followups',
    'student_academic_profiles': 'student_academic_profiles',
    'competencies': 'competencies',
    'users': 'users',
    'attachments': 'attachments',
    'family_contexts': 'family_contexts',
    'parent_interviews': 'parent_interviews',
    'counseling_sessions': 'counseling_sessions',
    'screenings': 'screenings',
    'screening_results': 'screening_results',
    'professional_interpretations': 'professional_interpretations',
    'individual_goals': 'individual_goals',
    'extracurricular_activities': 'extracurricular_activities',
    'recommendations': 'recommendations',
}


def normalize_entity_type(entity_type):
    """
    نام موجودیت را به شکل یکدست (نام جدول) برمی‌گرداند

    Args:
        entity_type: نام مفرد یا جمع؛ می‌تواند None باشد

    Returns:
        str | None: نام یکدست، یا همان مقدار ورودی اگر ناشناخته باشد
    """
    if not entity_type:
        return entity_type
    key = str(entity_type).strip().lower()
    return AUDIT_ENTITY_ALIASES.get(key, key)


class AuditLogger:
    """ثبت رویدادهای امنیتی (Audit Log)"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def log(self, user_id, action, entity_type, entity_id=None, 
            old_value=None, new_value=None, ip_address=None):
        """
        ثبت یک رویداد در Audit Log
        
        Args:
            user_id: شناسه کاربر
            action: نوع اقدام (login, create, edit, delete, restore, export, ...)
            entity_type: نوع موجودیت (student, observation, intervention, followup, ...)
            entity_id: شناسه موجودیت (اختیاری)
            old_value: مقدار قبلی (برای تغییرات)
            new_value: مقدار جدید (برای تغییرات)
            ip_address: آدرس IP کاربر (اختیاری)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # ===== اصلاح (بازرسی هفتم) =====
            # نام موجودیت یکدست می‌شود تا ردیف‌های این کلاس با
            # ردیف‌های تریگرهای دیتابیس (که نام جدول را می‌نویسند)
            # قابل جست‌وجوی مشترک باشند.
            entity_type = normalize_entity_type(entity_type)

            # تبدیل دیکشنری به JSON برای ذخیره
            import json
            old_json = json.dumps(old_value, ensure_ascii=False) if old_value else None
            new_json = json.dumps(new_value, ensure_ascii=False) if new_value else None
            
            cursor.execute("""
                INSERT INTO audit_logs (
                    user_id, action, entity_type, entity_id,
                    old_value, new_value, ip_address
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                action,
                entity_type,
                entity_id,
                old_json,
                new_json,
                ip_address
            ))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"⚠️ خطا در ثبت Audit Log: {e}")
            return False
    
    def log_login(self, user_id, success=True, ip_address=None):
        """ثبت رویداد ورود"""
        action = "login_success" if success else "login_failed"
        return self.log(user_id, action, "auth", None, 
                        new_value={"success": success}, 
                        ip_address=ip_address)
    
    def log_logout(self, user_id, ip_address=None):
        """ثبت رویداد خروج"""
        return self.log(user_id, "logout", "auth", None, ip_address=ip_address)
    
    def log_create(self, user_id, entity_type, entity_id, data=None, ip_address=None):
        """ثبت رویداد ایجاد"""
        return self.log(user_id, "create", entity_type, entity_id, 
                        new_value=data, ip_address=ip_address)
    
    def log_edit(self, user_id, entity_type, entity_id, old_value, new_value, ip_address=None):
        """ثبت رویداد ویرایش"""
        return self.log(user_id, "edit", entity_type, entity_id, 
                        old_value, new_value, ip_address=ip_address)
    
    def log_delete(self, user_id, entity_type, entity_id, data=None, ip_address=None):
        """ثبت رویداد حذف (منطقی)"""
        return self.log(user_id, "delete_soft", entity_type, entity_id, 
                        old_value=data, ip_address=ip_address)
    
    def log_restore(self, user_id, entity_type, entity_id, data=None, ip_address=None):
        """ثبت رویداد بازیابی"""
        return self.log(user_id, "restore", entity_type, entity_id, 
                        new_value=data, ip_address=ip_address)
    
    def log_export(self, user_id, entity_type, entity_id=None, data=None, ip_address=None):
        """ثبت رویداد خروجی گرفتن"""
        return self.log(user_id, "export", entity_type, entity_id, 
                        new_value=data, ip_address=ip_address)
    
    def get_logs(self, limit=100, user_id=None, entity_type=None, action=None):
        """دریافت لاگ‌ها با فیلتر"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            if entity_type:
                # ===== اصلاح (بازرسی هفتم) =====
                # هم نام مفرد و هم نام جدول پذیرفته می‌شود؛ وگرنه
                # کسی که 'student' می‌داد ردیف‌های تریگر (students)
                # را از دست می‌داد و برعکس.
                query += " AND entity_type IN (?, ?)"
                norm = normalize_entity_type(entity_type)
                params.extend([entity_type, norm])
            if action:
                query += " AND action = ?"
                params.append(action)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                logs.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'action': row['action'],
                    'entity_type': row['entity_type'],
                    'entity_id': row['entity_id'],
                    'old_value': row['old_value'],
                    'new_value': row['new_value'],
                    'ip_address': row['ip_address'],
                    'created_at': row['created_at'],
                })
            
            return logs
        except Exception as e:
            logger.error(f"⚠️ خطا در دریافت Audit Log: {e}")
            return []