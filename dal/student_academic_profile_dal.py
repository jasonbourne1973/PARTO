"""
لایه دسترسی به داده پرونده‌های سالانه دانش‌آموز
با متدهای چندساله برای گزارش روند
"""

import json
import sqlite3

from database.connection import DatabaseConnection
from models.student_academic_profile import StudentAcademicProfile
from utils.logger import get_logger
from utils.time_utils import utc_now_iso

logger = get_logger(__name__)


class StudentAcademicProfileDAL:
    """عملیات CRUD برای پرونده‌های سالانه دانش‌آموز"""

    def __init__(self):
        self.db = DatabaseConnection()

    def create(self, profile):
        """ایجاد پرونده سالانه جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        errors = profile.validate()
        if errors:
            raise ValueError("\n".join(errors))

        # بررسی وجود student
        cursor.execute(
            "SELECT id FROM students WHERE id = ? AND is_deleted = 0",
            (profile.student_id,)
        )
        if not cursor.fetchone():
            raise ValueError(f"student_id={profile.student_id} در جدول students وجود ندارد")

        # بررسی وجود academic_year
        cursor.execute(
            "SELECT id FROM academic_years WHERE id = ? AND is_deleted = 0",
            (profile.academic_year_id,)
        )
        if not cursor.fetchone():
            raise ValueError(f"academic_year_id={profile.academic_year_id} در جدول academic_years وجود ندارد")

        try:
            logger.debug("📝 ایجاد پرونده سالانه:")
            logger.debug(f"   student_id: {profile.student_id}")
            logger.debug(f"   academic_year_id: {profile.academic_year_id}")
            logger.debug(f"   grade: {profile.grade}")
            logger.debug(f"   class_name: {profile.class_name}")
            logger.debug(f"   status: {profile.status}")

            cursor.execute("""
                INSERT INTO student_academic_profiles (
                    student_id, academic_year_id, grade, class_name, status, status_history
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                profile.student_id,
                profile.academic_year_id,
                profile.grade,
                profile.class_name,
                profile.status,
                profile.status_history or "[]"
            ))

            conn.commit()
            profile.id = cursor.lastrowid

            logger.debug(f"✅ پرونده سالانه با ID {profile.id} ایجاد شد.")
            return profile

        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise Exception(f"خطای دیتابیس هنگام ایجاد پرونده سالانه: {e}")

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError):
            conn.rollback()
            raise

    def get_by_id(self, profile_id):
        """دریافت پرونده با شناسه"""
        cursor = self.db.execute_query(
            "SELECT * FROM student_academic_profiles WHERE id = ? AND is_deleted = 0",
            (profile_id,)
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_profile(row)
        return None

    def get_by_student_and_year(self, student_id, academic_year_id):
        """دریافت پرونده یک دانش‌آموز در یک سال خاص"""
        cursor = self.db.execute_query(
            """SELECT * FROM student_academic_profiles
               WHERE student_id = ? AND academic_year_id = ? AND is_deleted = 0""",
            (student_id, academic_year_id)
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_profile(row)
        return None

    def get_active_by_student(self, student_id):
        """دریافت پرونده فعال یک دانش‌آموز (سال جاری)"""
        # ===== اصلاح (بازرسی دوم) =====
        # فیلتر وضعیت با واژگانی نوشته شده بود که در برنامه وجود ندارند:
        #
        #     AND sap.status NOT IN ('archived', 'closed')
        #
        # مقدارهای واقعیِ مدل StudentAcademicProfile عبارت‌اند از:
        #     active / inactive / graduated / transferred / dropped
        # و هیچ کجای پروژه 'archived' یا 'closed' روی پرونده ست نمی‌شود
        # (grep: صفر نتیجه). یعنی این شرط «هیچ رکوردی را فیلتر نمی‌کرد».
        #
        # نتیجه عملی: دانش‌آموز فارغ‌التحصیل یا انصرافی/انتقالی هم
        # «پرونده فعال» داشت و در داشبورد، گزارش کلاس و لیست ارتقاء
        # مانند دانش‌آموز فعال رفتار می‌کرد.
        #
        # دو نکته برای ایمنی:
        #   ۱) COALESCE: اگر در دیتابیس قدیمی status مقدار NULL یا ''
        #      داشته باشد، رکورد «حذف» نشود (NOT IN روی NULL همیشه
        #      NULL می‌دهد و رکورد بی‌صدا از نتیجه بیرون می‌افتاد).
        #   ۲) 'inactive' عمداً در لیست سیاه نیست: صفحه ارتقاء پرونده
        #      سال قبل را inactive می‌کند و همان پرونده باید برای
        #      خواندن سابقه/گزارش سال قبل پیدا شود. فیلتر «سال فعال»
        #      (ay.is_active = 1) همان کار را درست انجام می‌دهد.
        #   ۳) ORDER BY: LIMIT 1 بدون ORDER BY نامعین بود. اگر برای یک
        #      دانش‌آموز در یک سال دو پرونده وجود داشته باشد (داده‌های
        #      قدیمی)، اولین پرونده — که تاریخچه و مشاهده‌ها به آن وصل
        #      است — برگردانده می‌شود تا نتیجه پایدار بماند.
        #
        # ===== افزوده (بازرسی سوم) =====
        # 'archived' به لیست سیاه اضافه شد. دلیلش این است که در همین دور
        # متدهای delete()/archive() پرونده اصلاح شدند و حالا واقعاً
        # STATUS_ARCHIVED را ست می‌کنند (قبلاً به خاطر نبودِ این ثابت روی
        # مدل، هر دو با AttributeError شکست می‌خوردند و هیچ پرونده‌ای
        # هیچ‌وقت 'archived' نمی‌شد). پس از این به بعد این وضعیت واقعاً
        # در دیتابیس وجود دارد و پروندهٔ بایگانی‌شده نباید «فعال» شمرده
        # شود.
        cursor = self.db.execute_query("""
            SELECT sap.* FROM student_academic_profiles sap
            JOIN academic_years ay ON sap.academic_year_id = ay.id
            WHERE sap.student_id = ?
              AND ay.is_active = 1
              AND ay.is_deleted = 0
              AND ay.is_archived = 0
              AND sap.is_deleted = 0
              AND COALESCE(sap.status, 'active')
                  NOT IN ('graduated', 'dropped', 'transferred', 'archived')
            ORDER BY sap.id ASC
            LIMIT 1
        """, (student_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_profile(row)
        return None

    def get_by_status(self, status):
        """دریافت پرونده‌ها بر اساس وضعیت"""
        cursor = self.db.execute_query(
            """SELECT * FROM student_academic_profiles
               WHERE status = ? AND is_deleted = 0
               ORDER BY id DESC""",
            (status,)
        )
        rows = cursor.fetchall()
        return [self._row_to_profile(row) for row in rows]

    def get_all(self, limit=None):
        """دریافت همه پرونده‌ها"""
        if limit is not None:
            cursor = self.db.execute_query(
                """SELECT * FROM student_academic_profiles
                   WHERE is_deleted = 0
                   ORDER BY id DESC
                   LIMIT ?""",
                (limit,)
            )
        else:
            cursor = self.db.execute_query(
                """SELECT * FROM student_academic_profiles
                   WHERE is_deleted = 0
                   ORDER BY id DESC"""
            )

        rows = cursor.fetchall()
        return [self._row_to_profile(row) for row in rows]

    def update(self, profile):
        """به‌روزرسانی پرونده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE student_academic_profiles SET
                    student_id = ?, academic_year_id = ?, grade = ?,
                    class_name = ?, status = ?, status_history = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 0
            """, (
                profile.student_id,
                profile.academic_year_id,
                profile.grade,
                profile.class_name,
                profile.status,
                profile.status_history,
                profile.id
            ))

            conn.commit()
            return profile

        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"خطا در به‌روزرسانی پرونده سالانه: {e}")

    def update_status(self, profile_id, new_status, history_note=None):
        """به‌روزرسانی وضعیت پرونده با ثبت تاریخچه"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # ===== اصلاح (بازرسی سوم) — جلوگیری از «واژگان مرده» =====
        # این متد هیچ اعتبارسنجی‌ای نداشت؛ هر رشته‌ای به عنوان وضعیت
        # پذیرفته و در دیتابیس نوشته می‌شد. ریشهٔ دو باگ قبلی همین بود:
        #   • promotion_page وضعیت "closed" می‌گذاشت که در STATUS_CHOICES
        #     مدل نیست ⇒ validate() ردش می‌کرد.
        #   • get_active_by_student با 'archived'/'closed' فیلتر می‌کرد که
        #     هیچ‌وقت ست نمی‌شدند ⇒ شرط هیچ رکوردی را فیلتر نمی‌کرد.
        # حالا هر وضعیت ناشناخته بلافاصله و با پیام روشن رد می‌شود،
        # به‌جای اینکه بی‌صدا در دیتابیس بنشیند و سال‌ها بعد باعث
        # آمار غلط شود.
        valid = [s[0] for s in StudentAcademicProfile.STATUS_CHOICES]
        if new_status not in valid:
            raise ValueError(
                f"وضعیت نامعتبر برای پروندهٔ تحصیلی: {new_status!r}. "
                f"مقدارهای مجاز: {', '.join(valid)}"
            )

        try:
            cursor.execute("""
                SELECT status, status_history
                FROM student_academic_profiles
                WHERE id = ? AND is_deleted = 0
            """, (profile_id,))
            row = cursor.fetchone()
            if not row:
                return None

            old_status = row['status']
            old_history = row['status_history'] or "[]"

            try:
                history = json.loads(old_history)
            except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError):
                history = []

            history.append({
                'from': old_status,
                'to': new_status,
                'date': utc_now_iso(),
                'note': history_note or ''
            })
            new_history = json.dumps(history, ensure_ascii=False)

            cursor.execute("""
                UPDATE student_academic_profiles SET
                    status = ?, status_history = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, new_history, profile_id))

            conn.commit()
            return True

        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"خطا در تغییر وضعیت پرونده: {e}")

    def delete(self, profile_id, user_id=None):
        """
        حذف منطقی پروندهٔ تحصیلی

        ===== 🔴 اصلاح (بازرسی سوم) =====
        نسخهٔ قبلی فقط این بود:

            return self.update_status(
                profile_id, StudentAcademicProfile.STATUS_ARCHIVED, ...)

        دو مشکل داشت:
          ۱) STATUS_ARCHIVED روی مدل تعریف نشده بود ⇒ همیشه
             AttributeError ⇒ «حذف پرونده» از روز اول کار نمی‌کرد.
          ۲) حتی اگر کار می‌کرد، فقط وضعیت را عوض می‌کرد و is_deleted را
             دست نمی‌زد. یعنی برخلاف بقیهٔ موجودیت‌های برنامه:
               • get_by_id/get_all که `is_deleted = 0` فیلتر می‌کنند
                 همچنان رکورد «حذف‌شده» را برمی‌گرداندند
               • تریگر trg_student_academic_profiles_soft_delete_audit
                 هرگز اجرا نمی‌شد ⇒ حذف در گزارش حسابرسی ثبت نمی‌شد
               • deleted_at و deleted_by خالی می‌ماندند

        حالا هم is_deleted=1 می‌شود (مثل بقیهٔ DALها، با ثبت زمان و
        کاربر و اجرای تریگر حسابرسی) و هم وضعیت به 'archived' می‌رود و
        در تاریخچهٔ وضعیت ثبت می‌شود.
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT status, status_history
                FROM student_academic_profiles
                WHERE id = ? AND is_deleted = 0
            """, (profile_id,))
            row = cursor.fetchone()
            if not row:
                return False

            old_status = row['status']
            try:
                history = json.loads(row['status_history'] or "[]")
            except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError):
                history = []
            history.append({
                'from': old_status,
                'to': StudentAcademicProfile.STATUS_ARCHIVED,
                'date': utc_now_iso(),
                'note': "حذف منطقی توسط کاربر"
            })

            now = utc_now_iso()
            cursor.execute("""
                UPDATE student_academic_profiles SET
                    is_deleted = 1,
                    deleted_at = ?,
                    deleted_by = ?,
                    status = ?,
                    status_history = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 0
            """, (
                now,
                user_id,
                StudentAcademicProfile.STATUS_ARCHIVED,
                json.dumps(history, ensure_ascii=False),
                profile_id
            ))

            affected = cursor.rowcount
            conn.commit()
            return affected > 0

        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"خطا در حذف پرونده تحصیلی: {e}")

    def restore(self, profile_id, user_id=None):
        """
        بازگرداندن پروندهٔ حذف‌شده (تا پیش از این وجود نداشت)

        وضعیت به 'inactive' برمی‌گردد و نه 'active': بازگرداندن یک
        پرونده به معنی فعال‌کردن دوبارهٔ دانش‌آموز در سال جاری نیست و
        باید آگاهانه و جداگانه انجام شود (وگرنه یک پروندهٔ حذف‌شده
        می‌توانست ناگهان در داشبورد و لیست ارتقاء ظاهر شود).
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT status, status_history
                FROM student_academic_profiles
                WHERE id = ? AND is_deleted = 1
            """, (profile_id,))
            row = cursor.fetchone()
            if not row:
                return False

            try:
                history = json.loads(row['status_history'] or "[]")
            except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError):
                history = []
            history.append({
                'from': row['status'],
                'to': StudentAcademicProfile.STATUS_INACTIVE,
                'date': utc_now_iso(),
                'note': "بازگردانی از حذف منطقی"
            })

            cursor.execute("""
                UPDATE student_academic_profiles SET
                    is_deleted = 0,
                    deleted_at = NULL,
                    deleted_by = NULL,
                    status = ?,
                    status_history = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 1
            """, (
                StudentAcademicProfile.STATUS_INACTIVE,
                json.dumps(history, ensure_ascii=False),
                profile_id
            ))

            affected = cursor.rowcount
            conn.commit()
            return affected > 0

        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"خطا در بازگردانی پرونده تحصیلی: {e}")

    def archive(self, profile_id):
        """
        بایگانی کردن پرونده (بدون حذف منطقی)

        تفاوتش با delete(): اینجا is_deleted دست نمی‌خورد، پس پرونده
        همچنان در فهرست‌ها و گزارش‌های تاریخی دیده می‌شود و فقط
        «پروندهٔ فعال» محسوب نمی‌شود. مناسب پایان سال تحصیلی.
        """
        return self.update_status(
            profile_id,
            StudentAcademicProfile.STATUS_ARCHIVED,
            "بایگانی شد"
        )

    # ============================================================
    # متدهای چندساله برای گزارش روند
    # ============================================================

    def get_all_profiles_for_student(self, student_id):
        """
        دریافت تمام پرونده‌های یک دانش‌آموز در طول سال‌های مختلف

        Args:
            student_id: شناسه دانش‌آموز

        Returns:
            list: لیست پرونده‌ها به ترتیب سال
        """
        cursor = self.db.execute_query("""
            SELECT sap.*, ay.title as academic_year_title, ay.start_date, ay.end_date
            FROM student_academic_profiles sap
            JOIN academic_years ay ON sap.academic_year_id = ay.id
            WHERE sap.student_id = ? AND sap.is_deleted = 0
            ORDER BY ay.start_date ASC
        """, (student_id,))
        rows = cursor.fetchall()

        profiles = []
        for row in rows:
            profile = self._row_to_profile(row)
            profile.academic_year_title = row['academic_year_title']
            profile.academic_year_start = row['start_date']
            profile.academic_year_end = row['end_date']
            profiles.append(profile)

        return profiles

    def get_multi_year_stats(self, student_id):
        """
        دریافت آمار چندساله یک دانش‌آموز

        Args:
            student_id: شناسه دانش‌آموز

        Returns:
            dict: {
                'total_years': int,
                'years': list,
                'grade_progression': list,
                'has_data': bool
            }
        """
        profiles = self.get_all_profiles_for_student(student_id)

        if not profiles:
            return {
                'total_years': 0,
                'years': [],
                'grade_progression': [],
                'has_data': False
            }

        years = []
        grade_progression = []

        for profile in profiles:
            years.append({
                'year_id': profile.academic_year_id,
                'title': getattr(profile, 'academic_year_title', 'نامشخص'),
                'grade': profile.grade,
                'grade_display': profile.grade_display,
                'class_name': profile.class_name,
                'status': profile.status,
                'status_display': profile.status_display
            })

            grade_progression.append({
                'year': getattr(profile, 'academic_year_title', 'نامشخص'),
                'grade': profile.grade,
                'grade_display': profile.grade_display
            })

        return {
            'total_years': len(profiles),
            'years': years,
            'grade_progression': grade_progression,
            'has_data': len(profiles) > 0
        }

    def get_student_years_range(self, student_id):
        """
        دریافت محدوده سال‌های تحصیلی یک دانش‌آموز

        Args:
            student_id: شناسه دانش‌آموز

        Returns:
            dict: {
                'first_year': str,
                'last_year': str,
                'total_years': int
            }
        """
        profiles = self.get_all_profiles_for_student(student_id)

        if not profiles:
            return {
                'first_year': None,
                'last_year': None,
                'total_years': 0
            }

        return {
            'first_year': getattr(profiles[0], 'academic_year_title', None),
            'last_year': getattr(profiles[-1], 'academic_year_title', None),
            'total_years': len(profiles)
        }

    def _row_to_profile(self, row):
        """تبدیل ردیف دیتابیس به مدل StudentAcademicProfile"""
        profile = StudentAcademicProfile()
        profile.id = row['id']
        profile.student_id = row['student_id']
        profile.academic_year_id = row['academic_year_id']
        profile.grade = row['grade']
        profile.class_name = row['class_name']
        profile.status = row['status']
        profile.status_history = row['status_history']
        profile.created_at = row['created_at']
        profile.updated_at = row['updated_at']
        profile.is_deleted = row['is_deleted']
        profile.deleted_at = row['deleted_at']
        profile.deleted_by = row['deleted_by']
        return profile