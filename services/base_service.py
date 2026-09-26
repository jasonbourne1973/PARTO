"""
سرویس پایه با پشتیبانی از Transaction و مدیریت خطا
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import DatabaseConnection
from utils.error_handler import AppError, ErrorHandler, ServiceError
from utils.logger import get_logger
from utils.security import PermissionDeniedError


class BaseService:
    """
    سرویس پایه برای تمام سرویس‌ها
    
    ویژگی‌ها:
    - مدیریت Transaction
    - مدیریت خطا
    - Logging یکپارچه
    - Audit Log
    """
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler()
        self._in_transaction = False

    # ============================================================
    # کمکی مشترک برای رفع نشت Exception خام (دور نوزدهم، مرحلهٔ ۵ —
    # ERR-01/ERR-LEAK-01)
    # ============================================================
    #
    # الگوی رایج در سراسر لایهٔ سرویس این بود:
    #
    #     try:
    #         ...
    #         if not found:
    #             raise ServiceError("... یافت نشد.")   # پیام امن/عمدی
    #         ...
    #     except Exception as e:
    #         self.logger.error(...)
    #         raise ServiceError(f"خطای عمومی: {e!s}")   # نشت raw
    #
    # چون بلوک `except Exception` هم Exceptionِ خامِ سیستمی (sqlite/OS)
    # و هم ServiceError/ValidationError عمدیِ *داخل همان try* (مثل «یافت
    # نشد» یا «به حداکثر رسیده») را یکسان می‌گرفت، رفعِ ساده‌لوحانهٔ نشت
    # (فقط حذف `{e!s}`) پیام‌های عمدی و امن را هم با یک پیام عمومیِ کم‌فایده
    # جایگزین می‌کرد — خودش یک باگِ تازه بود. `_safe_service_error` این
    # دو حالت را تفکیک می‌کند: اگر e از قبل AppError با user_visible=True
    # است (پیامش عمداً و امن برای کاربر نوشته شده)، همان پیام حفظ می‌شود؛
    # در غیر این صورت (Exception خام/سیستمی یا AppError با
    # user_visible=False مثل DatabaseError) با پیام عمومی امنِ داده‌شده
    # جایگزین می‌شود.
    def _safe_service_error(self, e, generic_message):
        """
        ساخت ServiceError امن از یک exception گرفته‌شده در except عمومی

        Args:
            e: exception گرفته‌شده (ممکن است AppError عمدی یا Exception خام باشد)
            generic_message: پیام عمومیِ امن برای حالتی که e خام/سیستمی است

        Returns:
            ServiceError: باید با `raise ... from e` پرتاب شود
        """
        if isinstance(e, AppError) and e.user_visible:
            return ServiceError(e.message, user_visible=True)
        if isinstance(e, PermissionDeniedError):
            # (یادداشت) این‌جا فقط پیامِ امنِ PermissionDeniedError حفظ
            # می‌شود؛ خودِ نوعِ استثنا هنوز به ServiceError بدل می‌شود —
            # همان رفتار قبل از مرحلهٔ ۵ (یک نقص جداگانه و از قبل موجود،
            # نه چیزی که مرحلهٔ ۵ ایجاد کرده باشد؛ رفعش نیازمند افزودن
            # `except PermissionDeniedError: raise` در محل‌های پرشمار
            # فراخوانی است و خارج از حیطهٔ ERR-01/ERR-LEAK-01 است).
            return ServiceError(str(e), user_visible=True)
        return ServiceError(generic_message, user_visible=False)

    # ============================================================
    # Transaction واقعی
    # ============================================================
    #
    # ===== اصلاح مهم =====
    # نسخه قبلی begin_transaction() فقط `self._in_transaction = True`
    # ست می‌کرد. هیچ BEGIN به sqlite فرستاده نمی‌شد و DALها همچنان
    # بعد از هر دستور commit می‌زدند. نتیجه:
    #
    #     execute_in_transaction(...)  → خطا → rollback
    #     → داده‌ای که نوشته شده بود سر جایش می‌ماند
    #
    # تست انجام‌شده روی کد قبلی: بعد از rollback، تعداد دانش‌آموز
    # یتیم در دیتابیس = ۱ (باید ۰ باشد).
    #
    # حالا کار به DatabaseConnection سپرده می‌شود که عمق تراکنش را
    # نگه می‌دارد و commit()های میانی را بی‌اثر می‌کند. تراکنش‌های
    # تودرتو هم پشتیبانی می‌شوند.

    def begin_transaction(self):
        """شروع یک Transaction جدید (تودرتو مجاز است)"""
        self.db.begin_transaction()
        self._in_transaction = True
        self.logger.debug("Transaction شروع شد.")

    def commit_transaction(self):
        """تأیید Transaction"""
        try:
            self.db.commit_transaction()
            self._in_transaction = self.db.in_transaction
            self.logger.debug("Transaction با موفقیت تأیید شد.")
        except Exception as e:
            self.logger.error(f"خطا در تأیید Transaction: {e}")
            self.rollback_transaction()
            raise self._safe_service_error(e, "خطا در ذخیره‌سازی.") from e

    def rollback_transaction(self):
        """بازگشت Transaction (همه لایه‌های تودرتو)"""
        try:
            self.db.rollback_transaction()
            self._in_transaction = False
            self.logger.debug("Transaction بازگشت داده شد.")
        except Exception as e:
            self.logger.error(f"خطا در بازگشت Transaction: {e}")

    def execute_in_transaction(self, func, *args, **kwargs):
        """
        اجرای یک تابع در داخل Transaction

        Args:
            func: تابعی که باید اجرا شود
            *args, **kwargs: آرگومان‌های تابع

        Returns:
            نتیجه تابع

        Raises:
            ServiceError: در صورت بروز خطا
        """
        self.begin_transaction()
        try:
            result = func(*args, **kwargs)
            self.commit_transaction()
            return result
        except Exception as e:
            self.rollback_transaction()
            self.logger.error(f"خطا در اجرای Transaction: {e}")
            # ===== اصلاح =====
            # نسخه قبلی نوع خطای اصلی را دور می‌انداخت و همه‌چیز را
            # به ServiceError تبدیل می‌کرد. حالا اگر خطا از قبل یک
            # ServiceError بود (مثلاً خطای اعتبارسنجی با پیام فارسی)،
            # همان پیام به کاربر می‌رسد نه «خطا در عملیات: ...».
            #
            # (دور نوزدهم، مرحلهٔ ۵ — ERR-01/ERR-LEAK-01) این شرط قبلاً
            # فقط ServiceError/PermissionDeniedError را دست‌نخورده رد
            # می‌کرد. اما ValidationError/NotFoundError/AuthorizationError
            # هم دقیقاً همین‌طور «پیام از پیش امن و برای کاربر نوشته‌شده»
            # هستند (user_visible=True در تعریف کلاس‌شان) — مثلاً «تعداد
            # پیوست‌ها به حداکثر رسیده است» که از AttachmentService.upload
            # به‌عنوان ValidationError raise می‌شود. قبلاً چون این کلاس‌ها
            # در isinstance نبودند، پیام مفیدشان با «خطا در عملیات» عمومی
            # جایگزین می‌شد (و تنها به این دلیل که پیام قدیمی خام {e!s} را
            # داخل خودش embed می‌کرد، به‌طور تصادفی همچنان دیده می‌شد —
            # قرارداد قدیمی/تست‌شدهٔ پروژه این بود که این نوع خطاها به
            # ServiceError تبدیل شوند ولی پیامشان حفظ شود؛ رفع نشتِ
            # Exception خام نباید این قرارداد را بشکند، پس همان تبدیل با
            # پیام دست‌نخورده و بدون افزودن جزئیات فنی/raw ادامه دارد).
            if isinstance(e, (ServiceError, PermissionDeniedError)):
                raise
            if isinstance(e, AppError) and e.user_visible:
                # پیام خودِ AppError (ValidationError/NotFoundError/
                # AuthorizationError) از قبل امن و برای کاربر نوشته شده؛
                # صرفاً نوعش به ServiceError تبدیل می‌شود (قرارداد قبلی)
                # بدون افزودن هیچ متن خام دیگری.
                raise ServiceError(e.message, user_visible=True) from e
            raise ServiceError("خطا در عملیات.", user_visible=False) from e

    # ============================================================
    # Audit Log / مدیریت خطا / اعتبارسنجی
    # ============================================================
    #
    # ===== اصلاح بحرانی =====
    # این سه متد (log_audit، handle_error، validate_model) با تورفتگی
    # اشتباه **داخل کلاس _TransactionContext** تعریف شده بودند، در
    # حالی که بدنه‌شان از self.db و self.logger و self.error_handler
    # استفاده می‌کند؛ یعنی فقط روی BaseService معنا دارند.
    #
    # نتیجه در زمان اجرا:
    #     AttributeError: 'StudentService' object has no attribute 'validate_model'
    #     AttributeError: 'ObservationService' object has no attribute 'log_audit'
    #
    # چون این فراخوان‌ها داخل execute_in_transaction بودند، خطا به
    # ServiceError تبدیل می‌شد و تراکنش rollback می‌کرد. یعنی عملاً
    # «ثبت دانش‌آموز»، «ثبت مشاهده»، «ثبت مداخله»، «ثبت پیگیری» و
    # «ثبت پیوست» همه شکست می‌خوردند و هیچ داده‌ای ذخیره نمی‌شد.
    #
    # تست روی کد قبلی:
    #     hasattr(BaseService, "log_audit")      → False
    #     hasattr(BaseService, "validate_model") → False
    # حالا هر سه متد به BaseService برگردانده شده‌اند.

    # ============================================================
    # جلوگیری از Audit تکراری (باگ بازرسی ششم)
    # ============================================================
    #
    # دیتابیس برنامه برای هر جدول حساس (۱۸ جدول از بازرسی دوازدهم)
    # تریگر حسابرسی دارد:
    #     trg_<table>_{insert,update,soft_delete,restore,hard_delete}_audit
    # (ابتدا ۷ جدول students, observations, interventions, followups,
    # student_academic_profiles, staff, competencies بود.)
    #
    # این تریگرها خودشان بعد از هر نوشتن یک ردیف در audit_logs
    # می‌سازند. اما سرویس‌ها هم صریحاً log_audit صدا می‌زنند؛
    # نتیجه، دو ردیف برای «یک» تغییر بود:
    #
    #     id 163 | user_id NULL | create | students | 6
    #     id 165 | user_id 1    | create | student  | 6
    #
    # یعنی هم شمارش گزارش‌های حسابرسی دوبرابر می‌شد و هم
    # entity_type دو واژه‌نامهٔ متفاوت داشت ('students' تریگر و
    # 'student' سرویس)، پس فیلترکردن لاگ‌ها هم قابل‌اعتماد نبود.
    #
    # تصمیم: تریگرها می‌مانند (چون تغییراتِ staff، competencies و
    # پروندهٔ سالانه هم از همان مسیر ثبت می‌شوند و کوتاه‌کردن آن‌ها
    # یعنی از دست دادن بخشی از تاریخچه)، و ثبتِ صریح سرویس وقتی
    # تریگرِ همان جدول و همان action وجود دارد، تکرار نمی‌شود.
    #
    # نام کاربر در ردیف تریگر از get_current_user_id() می‌آید که
    # در ورودِ کاربر (set_current_user) مقدار می‌گیرد؛ تست شد که
    # user_id درست ثبت می‌شود.
    # ===== نگاشت نام موجودیت → نام جدول (بازرسی هفتم) =====
    # این نگاشت به utils.security.AUDIT_ENTITY_ALIASES منتقل شد تا
    # سرویس‌ها، AuditLogger و DAL همگی از «یک» منبع بخوانند؛ سه
    # نسخهٔ جدا از هم دقیقاً همان چیزی است که باعث ناهمخوانی
    # 'student' در برابر 'students' شده بود.
    @staticmethod
    def _entity_table_map():
        try:
            from utils.security import AUDIT_ENTITY_ALIASES
            return AUDIT_ENTITY_ALIASES
        except Exception:  # pragma: no cover - مسیر پشتیبان
            # آینهٔ AUDIT_ENTITY_ALIASES (بازرسی دوازدهم: پوشش ۱۸ جدول)
            return {
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
                'notification': 'notifications',
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
                'notifications': 'notifications',
            }
    _AUDIT_ACTIONS = ('create', 'edit', 'delete_soft', 'restore', 'delete')
    _TRIGGER_CACHE = None

    def _trigger_audit_tables(self):
        """
        جدول‌هایی که تریگر حسابرسی فعال دارند (یک‌بار خوانده می‌شود)

        Returns:
            set: نام جدول‌هایی که تریگر دارند
        """
        if BaseService._TRIGGER_CACHE is not None:
            return BaseService._TRIGGER_CACHE

        tables = set()
        try:
            conn = self.db.get_connection()
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                "AND name LIKE 'trg_%_audit'"
            )
            for (name,) in cursor.fetchall():
                # trg_<table>_insert_audit / ..._update_audit / ...
                rest = name[len('trg_'):-len('_audit')]
                for suffix in ('_insert', '_update', '_soft_delete', '_restore',
                               '_hard_delete'):
                    if rest.endswith(suffix):
                        tables.add(rest[:-len(suffix)])
                        break
        except Exception as e:
            self.logger.debug(f"خواندن تریگرهای حسابرسی ممکن نشد: {e}")

        BaseService._TRIGGER_CACHE = tables
        return tables

    def _audit_handled_by_trigger(self, entity_type, action):
        """آیا تریگرِ دیتابیس همین تغییر را ثبت می‌کند؟"""
        if action not in self._AUDIT_ACTIONS:
            return False
        table = self._entity_table_map().get(
            str(entity_type).strip().lower() if entity_type else None)
        if not table:
            return False
        return table in self._trigger_audit_tables()

    def log_audit(self, user_id, action, entity_type, entity_id=None,
                  old_value=None, new_value=None, ip_address=None):
        """
        ثبت Audit Log (بدون تکرارِ ردیف‌های تریگر)

        ===== اصلاح (بازرسی هفتم) =====
        نام موجودیت با `normalize_entity_type` یکدست می‌شود (مفرد →
        نام جدول) تا با ردیف‌هایی که تریگرهای دیتابیس می‌نویسند
        یکی باشد. قبلاً یک رویداد واحد با دو نام («student» و
        «students») ثبت می‌شد و جست‌وجوی تاریخچه ناقص می‌ماند.
        """
        if self._audit_handled_by_trigger(entity_type, action):
            self.logger.debug(
                f"Audit تکراری ثبت نشد؛ تریگر {entity_type}/{action} "
                f"خودش ردیف را نوشت (entity_id={entity_id})."
            )
            return True

        try:
            from utils.security import AuditLogger
            audit_logger = AuditLogger(self.db)
            return audit_logger.log(user_id, action, entity_type, entity_id,
                                   old_value, new_value, ip_address)
        except Exception as e:
            self.logger.warning(f"خطا در ثبت Audit Log: {e}")
            return False

    # ============================================================
    # کمک‌تابع‌های اعتبارسنجی (بازرسی ششم)
    # ============================================================
    #
    # الگوی پرتکرارِ کل پروژه این بود:
    #     value = data.get('result_type', '').strip()
    # اگر کلید در دیکشنری وجود داشت ولی مقدارش None بود،
    # data.get پيش‌فرض را برنمی‌گرداند و None برمی‌گردد؛ نتیجه:
    #     AttributeError: 'NoneType' object has no attribute 'strip'
    #
    # این خطا در create_followup باعث می‌شد ثبت پیگیری با پیام
    # مبهمِ زیر کامل شکست بخورد، در حالی که فراخوان فقط
    # result_type=None داده بود:
    #     ServiceError: خطا در عملیات: 'NoneType' object has no
    #     attribute 'strip'
    #
    # تست عملی روی کد قبلی:
    #     FollowUpService.create_followup({..., 'result_type': None})
    #         → ServiceError (ذخیره نمی‌شد)
    @staticmethod
    def coerce_id(value, default=None):
        """
        شناسه (کلید خارجی) را به عدد صحیح تبدیل می‌کند

        ورودی‌های قابل قبول: 5، "5"، None
        هر چیز دیگری (لیست، دیکشنری، متن غیرعددی) → default

        چرا؟ الگوی رایج کد این بود که شناسه را بدون بررسی به
        پارامتر SQL می‌داد؛ اگر اشتباهاً لیست پاس داده می‌شد،
        خطای مبهمِ زیر بالا می‌آمد و در بعضی مسیرها هم بی‌صدا
        خورده می‌شد:
            sqlite3.ProgrammingError: Error binding parameter 2:
            type 'list' is not supported
        """
        if value is None or value == '':
            return default
        if isinstance(value, bool):
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            text = value.strip()
            if text.lstrip('-').isdigit():
                return int(text)
            return default
        return default

    @staticmethod
    def clean_text(value, default=''):
        """
        متنِ ورودی را امن می‌کند

        Args:
            value: مقدار ورودی (ممکن است None باشد)
            default: مقدار جانشین وقتی ورودی None است

        Returns:
            str یا default: متن بدون فاصله‌های ابتدا/انتها
        """
        if value is None:
            return default
        return str(value).strip()

    @staticmethod
    def clean_date(value, default=None):
        """
        تاریخ (شمسی) را برای ذخیره یکدست می‌کند

        ورودی‌های پذیرفته‌شده: «1405/06/26»، «1405-6-6»، None
        خروجی همیشه «yyyy/MM/dd» با صفرِ ابتدایی است تا مقایسه و
        مرتب‌سازی رشته‌ای تاریخ‌ها در کوئری‌ها درست بماند.
        مقدار نامعتبر/خالی → default
        """
        if value is None or value == '':
            return default
        try:
            from utils.persian_date import to_db_date
            normalized = to_db_date(value)
        except Exception as _exc:
            get_logger(__name__).debug(f"خطای مدیریت‌شده در clean_date (مسیر جایگزین): {_exc}")
            normalized = None
        if not normalized:
            return default
        return normalized

    def check_date(self, value, label='تاریخ', required=False):
        """
        بررسی یک تاریخ شمسیِ ورودی و برگرداندن شکل کانونیکال آن

        قاعده:
            «1405-6-6»   → «1405/06/06» و معتبر
            «1405/13/45» → معتبر نیست (ماه/روز خارج از تقویم)
            «» / None    → اگر required باشد خطا، وگرنه None

        Args:
            value: مقدار ورودی
            label: نام فیلد برای پیام خطا (مثلاً «تاریخ جلسه»)
            required: آیا خالی‌بودن خطاست؟

        Returns:
            tuple: (normalized_value_or_None, error_message_or_None)
        """
        raw = self.clean_text(value)
        if not raw:
            if required:
                return None, f"{label} نمی‌تواند خالی باشد"
            return None, None

        normalized = self.clean_date(raw)
        if not normalized or not self.is_valid_jalali_date(normalized):
            return None, f"{label} معتبر نیست (قالب: yyyy/MM/dd)"

        return normalized, None

    @staticmethod
    def is_valid_jalali_date(value):
        """
        اعتبارسنجی واقعی تاریخ شمسی (نه فقط شکل ظاهری)

        قبلاً سرویس‌ها با یک regex ساده فقط شکل «yyyy/MM/dd» را
        بررسی می‌کردند؛ نتیجه: تاریخ‌هایی مثل «1405/13/45» معتبر
        شمرده می‌شدند و در دیتابیس ذخیره می‌شدند (ماه ۱۳ و روز ۴۵).
        تست عملی روی کد قبلی:
            ObservationService.validate_observation({...,
                'observation_date': '1405/13/45'})
                → (True, [])
        """
        if not value:
            return False

        text = str(value).strip()
        # جداکننده باید «/» باشد؛ to_db_date فرمت‌های دیگر را
        # نرمال می‌کند، ولی ورودیِ فرم/سرویس باید یکدست باشد.
        import re
        if not re.match(r'^\d{4}/\d{1,2}/\d{1,2}$', text):
            return False

        try:
            from utils.persian_date import PersianDate
            return PersianDate.is_valid_persian_date(text)
        except Exception as _exc:
            get_logger(__name__).debug(f"خطای مدیریت‌شده در is_valid_jalali_date (مسیر جایگزین): {_exc}")
            return False

    def handle_error(self, error, user_message=None, log_level='error'):
        """
        مدیریت یک خطا

        Args:
            error: شیء خطا
            user_message: پیام نمایشی به کاربر
            log_level: سطح لاگ ('error', 'warning', 'info')
        """
        return self.error_handler.handle(error, user_message, log_level)

    def validate_model(self, model):
        """
        اعتبارسنجی یک مدل

        Args:
            model: مدل مورد نظر

        Returns:
            bool: آیا مدل معتبر است؟

        Raises:
            ServiceError: در صورت عدم اعتبار
        """
        errors = model.validate()
        if errors:
            error_msg = "\n".join(errors)
            self.logger.warning(f"خطای اعتبارسنجی: {error_msg}")
            raise ServiceError(f"خطا در اعتبارسنجی:\n{error_msg}")
        return True

    def transaction(self):
        """
        استفاده به شکل with (روش پیشنهادی برای کد جدید)

            with self.transaction():
                self.student_dal.create(student)
                self.profile_dal.create(profile)
        """
        return _TransactionContext(self)


class _TransactionContext:
    """مدیر زمینه برای with self.transaction()"""

    def __init__(self, service):
        self._service = service

    def __enter__(self):
        self._service.begin_transaction()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._service.commit_transaction()
        else:
            self._service.rollback_transaction()
        # خطا را بلعیده نمی‌کنیم؛ به بالادست propagate می‌شود
        return False