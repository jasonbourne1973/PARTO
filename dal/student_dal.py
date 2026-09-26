"""
لایه دسترسی به داده دانش‌آموزان (اطلاعات دائمی) - با Soft Delete یکپارچه
با متدهای تحلیلی برای داشبورد
"""

import sqlite3

from database.connection import DatabaseConnection
from models.student import Student
from utils.batch_query import id_chunks, placeholders
from utils.logger import get_logger
from utils.pagination import normalize_limit_offset
from utils.security import AccessControl, Permission
from utils.time_utils import utc_now_iso

logger = get_logger(__name__)


class StudentDAL:
    """عملیات CRUD برای دانش‌آموزان با Soft Delete یکپارچه"""

    def __init__(self):
        self.db = DatabaseConnection()

    def create(self, student):
        """ایجاد دانش‌آموز جدید"""
        # مرز مجوز backend (دور نوزدهم — سند ممیزی مدیر پروژه، بخش ۹):
        # create فقط با نمایش/مخفی‌کردن دکمه در UI محافظت نمی‌شد؛ هر
        # کاربر واردشده (حتی «مشاهده‌گر») می‌توانست مستقیم این متد را
        # صدا بزند. الگو یکسان با delete/restore (BUG-NAV-03) است.
        AccessControl.require_permission(
            Permission.CREATE_STUDENT.value, action="StudentDAL.create")
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            national_code = student.national_code.strip() if student.national_code else None
            if national_code == "":
                national_code = None

            cursor.execute("""
                INSERT INTO students (
                    first_name, last_name, national_code, birth_date,
                    father_name, guardian_name, guardian_phone, address,
                    is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                student.first_name,
                student.last_name,
                national_code,
                student.birth_date,
                student.father_name,
                student.guardian_name,
                student.guardian_phone,
                student.address,
                student.is_active
            ))

            self.db.commit()
            student.id = cursor.lastrowid
            student.national_code = national_code
            return student

        except sqlite3.IntegrityError as e:
            self.db.rollback()
            raise Exception(f"خطا در ثبت دانش‌آموز: {e}")

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError):
            self.db.rollback()
            raise

    def get_by_id(self, student_id, include_deleted=False):
        """دریافت دانش‌آموز با شناسه"""
        query = "SELECT * FROM students WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"

        cursor = self.db.execute_query(query, (student_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_student(row)
        return None

    def get_by_ids(self, student_ids, include_deleted=False):
        """
        دریافت چند دانش‌آموز با «یک» کوئری (بازرسی چهاردهم: رفع N+1)

        معناشناسی دقیقاً مثل get_by_id است (پیش‌فرض: حذف‌شده‌ها
        برنمی‌گردند؛ شناسهٔ ناموجود در خروجی نیست).

        Returns:
            dict: {student_id: Student}
        """
        result = {}
        for chunk in id_chunks(student_ids):
            query = f"SELECT * FROM students WHERE id IN ({placeholders(len(chunk))})"
            if not include_deleted:
                query += " AND is_deleted = 0"
            cursor = self.db.execute_query(query, tuple(chunk))
            for row in cursor.fetchall():
                student = self._row_to_student(row)
                result[student.id] = student
        return result

    def get_all(self, limit=None, offset=None, include_deleted=False):
        """دریافت همه دانش‌آموزان - فقط رکوردهای موجود"""
        # (دور نوزدهم، مرحلهٔ ۶ — Pagination مرکزی) اعتبارسنجی/Clamp
        # limit/offset از یک محل مشترک؛ limit=None دست‌نخورده می‌ماند
        # (یعنی «بدون سقف» — قرارداد موجود صادرات کامل نمی‌شکند).
        limit, offset = normalize_limit_offset(limit, offset)

        query = "SELECT * FROM students WHERE 1=1"
        params = []

        if not include_deleted:
            query += " AND is_deleted = 0"

        query += " ORDER BY last_name, first_name"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

        cursor = self.db.execute_query(query, tuple(params) if params else None)
        rows = cursor.fetchall()
        return [self._row_to_student(row) for row in rows]

    def count_all(self, include_deleted=False):
        """
        شمارش کل دانش‌آموزان با همان WHERE متد get_all (بدون LIMIT/OFFSET)

        برای Pagination واقعی لازم است `total` دقیقاً همان فیلتری را
        داشته باشد که صفحه‌بندی رویش اعمال می‌شود (دور نوزدهم، مرحلهٔ ۶).
        """
        query = "SELECT COUNT(*) as cnt FROM students WHERE 1=1"
        if not include_deleted:
            query += " AND is_deleted = 0"
        cursor = self.db.execute_query(query)
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    def search(self, search_term, include_deleted=False, only_deleted=False,
               limit=None, offset=None):
        """
        جستجوی دانش‌آموزان

        Args:
            only_deleted: اگر True باشد، فقط رکوردهای حذف‌شده جست‌وجو
                می‌شوند (برای جست‌وجوی متنی در حالت «نمایش حذف‌شده‌ها»؛
                قبلاً این فیلتر با یک حلقهٔ پایتونی روی کل فهرست حذف‌شده
                انجام می‌شد). با include_deleted ناسازگار است؛ only_deleted
                اولویت دارد.
        """
        limit, offset = normalize_limit_offset(limit, offset)

        query = """
            SELECT * FROM students
            WHERE (first_name LIKE ? OR last_name LIKE ? OR national_code LIKE ?)
        """
        params = [f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"]
        if only_deleted:
            query += " AND is_deleted = 1"
        elif not include_deleted:
            query += " AND is_deleted = 0"

        query += " ORDER BY last_name, first_name"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

        cursor = self.db.execute_query(query, tuple(params))

        rows = cursor.fetchall()
        return [self._row_to_student(row) for row in rows]

    def count_search(self, search_term, include_deleted=False, only_deleted=False):
        """شمارش نتایج جستجو با همان WHERE متد search (بدون LIMIT/OFFSET)"""
        query = """
            SELECT COUNT(*) as cnt FROM students
            WHERE (first_name LIKE ? OR last_name LIKE ? OR national_code LIKE ?)
        """
        params = [f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"]
        if only_deleted:
            query += " AND is_deleted = 1"
        elif not include_deleted:
            query += " AND is_deleted = 0"
        cursor = self.db.execute_query(query, tuple(params))
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    def update(self, student):
        """
        به‌روزرسانی دانش‌آموز - فقط رکوردهای موجود

        (دور هفدهم — بند ۱۳ مأموریت) نتیجهٔ UPDATE واقعاً بررسی می‌شود:
        پیش از این، اگر رکورد وجود نداشت یا حذف‌شده بود، این متد مثل
        «موفقیت» رفتار می‌کرد و مدل را برمی‌گرداند (هیچ ردیفی تغییر نکرده
        بود). حالا در آن حالت `None` برمی‌گردد و در لاگ هم هشدار ثبت
        می‌شود تا لایهٔ بالا بتواند نبودِ اثر را تشخیص دهد.
        """
        # مرز مجوز backend (دور نوزدهم) — همان الگوی create/delete
        AccessControl.require_permission(
            Permission.EDIT_STUDENT.value, action="StudentDAL.update")
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            national_code = student.national_code.strip() if student.national_code else None
            if national_code == "":
                national_code = None

            cursor.execute("""
                UPDATE students SET
                    first_name = ?, last_name = ?, national_code = ?,
                    birth_date = ?, father_name = ?, guardian_name = ?,
                    guardian_phone = ?, address = ?, is_active = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 0
            """, (
                student.first_name,
                student.last_name,
                national_code,
                student.birth_date,
                student.father_name,
                student.guardian_name,
                student.guardian_phone,
                student.address,
                student.is_active,
                student.id
            ))

            affected = cursor.rowcount
            self.db.commit()
            if affected == 0:
                logger.warning(
                    f"به‌روزرسانی دانش‌آموز {student.id} روی دیتابیس اثر نکرد "
                    "(رکورد وجود ندارد یا حذف‌شده است)."
                )
                return None
            student.national_code = national_code
            return student

        except sqlite3.IntegrityError as e:
            self.db.rollback()
            raise Exception(f"خطا در ویرایش دانش‌آموز: {e}")

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError):
            self.db.rollback()
            raise

    def delete(self, student_id, user_id=None):
        """حذف منطقی دانش‌آموز - فقط رکوردهای موجود"""
        # مرز مجوز backend (BUG-NAV-03): حذف دانش‌آموز = DELETE_STUDENT
        # (نگاشت «بازیابی» هم به همین مجوز؛ مستند در docs/design_decisions_fa.md)
        AccessControl.require_permission(
            Permission.DELETE_STUDENT.value, action="StudentDAL.delete")
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM students WHERE id = ? AND is_deleted = 0",
            (student_id,)
        )
        if not cursor.fetchone():
            return False

        now = utc_now_iso()
        cursor.execute("""
            UPDATE students SET
                is_deleted = 1,
                is_active = 0,
                deleted_at = ?,
                deleted_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (now, user_id, student_id))

        self.db.commit()
        return True

    def restore(self, student_id, user_id=None):
        """بازیابی دانش‌آموز حذف شده - فقط رکوردهای حذف شده"""
        # مرز مجوز backend (BUG-NAV-03): بازیابی = همان مجوز حذف
        AccessControl.require_permission(
            Permission.DELETE_STUDENT.value, action="StudentDAL.restore")
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM students WHERE id = ? AND is_deleted = 1",
            (student_id,)
        )
        if not cursor.fetchone():
            return False

        cursor.execute("""
            UPDATE students SET
                is_deleted = 0,
                is_active = 1,
                deleted_at = NULL,
                deleted_by = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 1
        """, (student_id,))

        self.db.commit()
        return True

    def get_deleted(self, limit=None, offset=None):
        """دریافت لیست رکوردهای حذف شده"""
        limit, offset = normalize_limit_offset(limit, offset)

        query = "SELECT * FROM students WHERE is_deleted = 1 ORDER BY deleted_at DESC"
        params = []

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

        cursor = self.db.execute_query(query, tuple(params) if params else None)
        rows = cursor.fetchall()
        return [self._row_to_student(row) for row in rows]

    def count_deleted(self):
        """شمارش رکوردهای حذف‌شده (بدون LIMIT/OFFSET) — برای Pagination"""
        cursor = self.db.execute_query(
            "SELECT COUNT(*) as cnt FROM students WHERE is_deleted = 1")
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    def get_by_national_code(self, national_code, include_deleted=False):
        """دریافت دانش‌آموز با کد ملی"""
        query = "SELECT * FROM students WHERE national_code = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"

        cursor = self.db.execute_query(query, (national_code,))
        row = cursor.fetchone()
        if row:
            return self._row_to_student(row)
        return None

    def advanced_search(self, name=None, national_code=None, grade=None,
                        class_name=None, birth_date=None, include_deleted=False):
        """جستجوی پیشرفته دانش‌آموزان بر اساس معیارهای متعدد"""
        query = """
            SELECT DISTINCT s.*
            FROM students s
            LEFT JOIN student_academic_profiles sap ON s.id = sap.student_id
            WHERE 1=1
        """
        params = []

        if not include_deleted:
            query += " AND s.is_deleted = 0"

        if name and name.strip():
            query += " AND (s.first_name LIKE ? OR s.last_name LIKE ?)"
            params.append(f"%{name.strip()}%")
            params.append(f"%{name.strip()}%")

        if national_code and national_code.strip():
            query += " AND s.national_code LIKE ?"
            params.append(f"%{national_code.strip()}%")

        if grade is not None:
            query += " AND sap.grade = ?"
            params.append(grade)

        if class_name and class_name.strip():
            query += " AND sap.class_name LIKE ?"
            params.append(f"%{class_name.strip()}%")

        if birth_date and birth_date.strip():
            query += " AND s.birth_date = ?"
            params.append(birth_date.strip())

        query += " ORDER BY s.last_name, s.first_name"

        try:
            cursor = self.db.execute_query(query, tuple(params) if params else None)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                student = self._row_to_student(row)
                if student:
                    results.append(student)
            return results
        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در جستجوی پیشرفته: {e}")
            return []

    def permanent_delete(self, student_id):
        """
        حذف فیزیکی دانش‌آموز - فقط برای موارد خاص استفاده شود

        (دور نوزدهم، مرحلهٔ ۸ — SEC-HARD-DELETE-01) این متد قبلاً بدون
        هیچ بررسیِ Permission یا وابستگی، ردیف را مستقیماً DELETE
        می‌کرد. چون `student_academic_profiles.student_id` با
        `ON DELETE CASCADE` به students.id وصل است، این کار عملاً
        هر پرونده/مشاهده/مداخله/پیگیری/غربالگری/... متعلق به آن
        دانش‌آموز را هم برای همیشه پاک می‌کرد — بدون Audit Trail (بر
        خلاف delete() منطقی که سابقه را با is_deleted=1 حفظ می‌کند).
        حالا مثل staff_dal.permanent_delete: هم Permission بررسی
        می‌شود، هم وابستگی (وجود پروندهٔ سالانه) قبل از حذف.
        """
        # مرز مجوز backend: حذف دائم = همان مجوز حذف منطقی (بدون اختراع
        # Permission تازه)
        AccessControl.require_permission(
            Permission.DELETE_STUDENT.value, action="StudentDAL.permanent_delete")

        conn = self.db.get_connection()
        cursor = conn.cursor()

        row = cursor.execute(
            "SELECT first_name, last_name FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()
        if row is None:
            return False

        profile_count = cursor.execute(
            "SELECT COUNT(*) FROM student_academic_profiles WHERE student_id = ?",
            (student_id,)
        ).fetchone()[0]
        if profile_count:
            raise ValueError(
                f"«{row['first_name']} {row['last_name']}» دارای "
                f"{profile_count} پروندهٔ سالانه (و هر سابقهٔ مشاهده/"
                "مداخله/پیگیری/غربالگری وابسته به آن‌ها) است؛ حذف دائم "
                "همهٔ این تاریخچه را برای همیشه نابود می‌کند. به‌جای آن "
                "از حذف عادی استفاده کنید تا رکورد غیرفعال و از "
                "فهرست‌ها پنهان شود ولی سوابق حفظ بمانند."
            )

        cursor.execute(
            "DELETE FROM students WHERE id = ?",
            (student_id,)
        )
        affected = cursor.rowcount
        self.db.commit()
        return affected > 0

    # ============================================================
    # متدهای تحلیلی برای داشبورد
    # ============================================================

    def get_student_distribution_by_grade(self, academic_year_id=None, staff_id=None):
        """
        دریافت توزیع دانش‌آموزان بر اساس پایه

        Args:
            academic_year_id: شناسه سال تحصیلی (اختیاری)
            staff_id: اگر داده شود، فقط دانش‌آموزانِ نسبت‌داده‌شده به همین
                معلم (از طریق teacher_assignments) شمرده می‌شوند - فیلتر
                انتخاب معلم در داشبورد.

        Returns:
            list: [
                {
                    'grade': int,
                    'grade_display': str,
                    'count': int,
                    'percentage': float
                }
            ]
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT sap.grade, COUNT(DISTINCT s.id) as count
                FROM students s
                JOIN student_academic_profiles sap ON s.id = sap.student_id
                WHERE s.is_deleted = 0
                AND s.is_active = 1
                AND sap.is_deleted = 0
                AND sap.status = 'active'
            """
            params = []

            if academic_year_id:
                query += " AND sap.academic_year_id = ?"
                params.append(academic_year_id)

            if staff_id:
                query += """
                AND EXISTS (
                    SELECT 1 FROM teacher_assignments ta
                    WHERE ta.student_id = s.id
                    AND ta.staff_id = ?
                    AND ta.is_deleted = 0
                    AND ta.is_active = 1
                )
                """
                params.append(staff_id)

            query += " GROUP BY sap.grade ORDER BY sap.grade"

            cursor.execute(query, tuple(params))  # اصلاح: None می‌داد «parameters are of unsupported type»
            rows = cursor.fetchall()

            total = sum(row['count'] for row in rows) if rows else 0

            grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}

            result = []
            for row in rows:
                grade = row['grade']
                count = row['count']
                result.append({
                    'grade': grade,
                    'grade_display': grade_names.get(grade, str(grade)),
                    'count': count,
                    'percentage': round((count / total * 100), 1) if total > 0 else 0
                })

            return result

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت توزیع دانش‌آموزان: {e}")
            return []

    def get_student_count_by_status(self, academic_year_id=None):
        """
        دریافت تعداد دانش‌آموزان بر اساس وضعیت پرونده

        Args:
            academic_year_id: شناسه سال تحصیلی (اختیاری)

        Returns:
            dict: {
                'active': int,
                'inactive': int,
                'graduated': int,
                'transferred': int,
                'dropped': int,
                'total': int
            }
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT sap.status, COUNT(DISTINCT s.id) as count
                FROM students s
                JOIN student_academic_profiles sap ON s.id = sap.student_id
                WHERE s.is_deleted = 0
                AND s.is_active = 1
                AND sap.is_deleted = 0
            """
            params = []

            if academic_year_id:
                query += " AND sap.academic_year_id = ?"
                params.append(academic_year_id)

            query += " GROUP BY sap.status"

            cursor.execute(query, tuple(params))  # اصلاح: None می‌داد «parameters are of unsupported type»
            rows = cursor.fetchall()

            result = {
                'active': 0,
                'inactive': 0,
                'graduated': 0,
                'transferred': 0,
                'dropped': 0,
                'total': 0
            }

            total = 0
            for row in rows:
                status = row['status']
                count = row['count']
                if status == 'active':
                    result['active'] = count
                elif status == 'inactive':
                    result['inactive'] = count
                elif status == 'graduated':
                    result['graduated'] = count
                elif status == 'transferred':
                    result['transferred'] = count
                elif status == 'dropped':
                    result['dropped'] = count
                total += count

            result['total'] = total
            return result

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت تعداد دانش‌آموزان بر اساس وضعیت: {e}")
            return {'active': 0, 'inactive': 0, 'graduated': 0, 'transferred': 0, 'dropped': 0, 'total': 0}

    def get_students_without_observations(self, academic_year_id=None, staff_id=None):
        """
        دریافت دانش‌آموزانی که هیچ مشاهده‌ای ندارند

        Args:
            academic_year_id: شناسه سال تحصیلی (اختیاری)
            staff_id: اگر داده شود، فقط دانش‌آموزانی که «به همین معلم
                نسبت داده شده‌اند» (از طریق teacher_assignments) و هنوز
                مشاهده‌ای ندارند برمی‌گردند - فیلتر انتخاب معلم در داشبورد.

        Returns:
            list: لیست دانش‌آموزان بدون مشاهده
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # ===== اصلاح مهم =====
            # زیرکوئری NOT EXISTS روی sap2 هیچ فیلتر سال تحصیلی نداشت:
            #     WHERE sap2.student_id = s.id AND o.is_deleted = 0
            #
            # یعنی «دانش‌آموزی که در هیچ سالی مشاهده ندارد». ولی کار
            # این گزارش «دانش‌آموزان بدون مشاهده در سال جاری» است.
            #
            # نتیجه: دانش‌آموزی که پارسال چند مشاهده داشته ولی امسال
            # هیچ‌کدام ندارد، از لیست حذف می‌شد — دقیقاً همان کسی که
            # مشاور باید پیدایش کند. لیست عملاً همیشه خالی می‌آمد.
            #
            # حالا وقتی سال تحصیلی داده شده، زیرکوئری هم به همان سال
            # محدود می‌شود.
            year_filter_sub = ""
            params = []
            if academic_year_id:
                year_filter_sub = "AND sap2.academic_year_id = ?"
                params.append(academic_year_id)

            query = f"""
                SELECT s.id, s.first_name, s.last_name, sap.grade, sap.class_name
                FROM students s
                JOIN student_academic_profiles sap ON s.id = sap.student_id
                WHERE s.is_deleted = 0
                AND s.is_active = 1
                AND sap.is_deleted = 0
                AND sap.status = 'active'
                AND NOT EXISTS (
                    SELECT 1 FROM observations o
                    JOIN student_academic_profiles sap2 ON o.student_profile_id = sap2.id
                    WHERE sap2.student_id = s.id
                    AND o.is_deleted = 0
                    {year_filter_sub}
                )
            """

            if academic_year_id:
                query += " AND sap.academic_year_id = ?"
                params.append(academic_year_id)

            if staff_id:
                # فقط دانش‌آموزانی که در سال جاری به این معلم نسبت داده شده‌اند
                query += """
                AND EXISTS (
                    SELECT 1 FROM teacher_assignments ta
                    WHERE ta.student_id = s.id
                    AND ta.staff_id = ?
                    AND ta.is_deleted = 0
                    AND ta.is_active = 1
                )
                """
                params.append(staff_id)

            query += " ORDER BY s.last_name, s.first_name"

            cursor.execute(query, tuple(params))  # اصلاح: None می‌داد «parameters are of unsupported type»
            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    'id': row['id'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'full_name': f"{row['first_name']} {row['last_name']}",
                    'grade': row['grade'],
                    'class_name': row['class_name']
                })

            return result

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت دانش‌آموزان بدون مشاهده: {e}")
            return []

    def get_student_activity_summary(self, student_id, start_date=None, end_date=None):
        """
        دریافت خلاصه فعالیت‌های یک دانش‌آموز

        Args:
            student_id: شناسه دانش‌آموز
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)

        Returns:
            dict: {
                'observations_count': int,
                'interventions_count': int,
                'followups_count': int,
                'positive_count': int,
                'negative_count': int,
                'avg_severity': float,
                'last_observation_date': str
            }
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # دریافت پرونده فعال
            profile_query = """
                SELECT id FROM student_academic_profiles
                WHERE student_id = ? AND is_deleted = 0 AND status = 'active'
                LIMIT 1
            """
            cursor.execute(profile_query, (student_id,))
            profile = cursor.fetchone()

            if not profile:
                return {
                    'observations_count': 0,
                    'interventions_count': 0,
                    'followups_count': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'avg_severity': 0,
                    'last_observation_date': None
                }

            profile_id = profile['id']

            # دریافت مشاهدات
            obs_query = """
                SELECT COUNT(*) as count, 
                       SUM(CASE WHEN behavior_type = 'مثبت' THEN 1 ELSE 0 END) as positive,
                       SUM(CASE WHEN behavior_type = 'منفی' THEN 1 ELSE 0 END) as negative,
                       AVG(severity) as avg_severity,
                       MAX(observation_date) as last_date
                FROM observations
                WHERE student_profile_id = ? AND is_deleted = 0
            """
            obs_params = [profile_id]

            if start_date:
                obs_query += " AND observation_date >= ?"
                obs_params.append(start_date)
            if end_date:
                obs_query += " AND observation_date <= ?"
                obs_params.append(end_date)

            cursor.execute(obs_query, obs_params)
            obs_row = cursor.fetchone()

            # دریافت مداخلات
            inter_query = """
                SELECT COUNT(*) as count
                FROM interventions
                WHERE student_profile_id = ? AND is_deleted = 0
            """
            inter_params = [profile_id]

            if start_date:
                inter_query += " AND date >= ?"
                inter_params.append(start_date)
            if end_date:
                inter_query += " AND date <= ?"
                inter_params.append(end_date)

            cursor.execute(inter_query, inter_params)
            inter_row = cursor.fetchone()

            # دریافت پیگیری‌ها
            follow_query = """
                SELECT COUNT(*) as count
                FROM followups f
                JOIN interventions i ON f.intervention_id = i.id
                WHERE i.student_profile_id = ? AND f.is_deleted = 0
            """
            follow_params = [profile_id]

            if start_date:
                follow_query += " AND f.date >= ?"
                follow_params.append(start_date)
            if end_date:
                follow_query += " AND f.date <= ?"
                follow_params.append(end_date)

            cursor.execute(follow_query, follow_params)
            follow_row = cursor.fetchone()

            return {
                'observations_count': obs_row['count'] if obs_row else 0,
                'interventions_count': inter_row['count'] if inter_row else 0,
                'followups_count': follow_row['count'] if follow_row else 0,
                'positive_count': obs_row['positive'] if obs_row else 0,
                'negative_count': obs_row['negative'] if obs_row else 0,
                'avg_severity': round(obs_row['avg_severity'], 1) if obs_row and obs_row['avg_severity'] else 0,
                'last_observation_date': obs_row['last_date'] if obs_row else None
            }

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت خلاصه فعالیت‌های دانش‌آموز: {e}")
            return {
                'observations_count': 0,
                'interventions_count': 0,
                'followups_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'avg_severity': 0,
                'last_observation_date': None
            }

    def _row_to_student(self, row):
        """تبدیل ردیف دیتابیس به مدل Student"""
        if row is None:
            return None

        student = Student()
        student.id = row['id']
        student.first_name = row['first_name']
        student.last_name = row['last_name']
        student.national_code = row['national_code']
        student.birth_date = row['birth_date']
        student.father_name = row['father_name']
        student.guardian_name = row['guardian_name']
        student.guardian_phone = row['guardian_phone']
        student.address = row['address']
        student.is_active = row['is_active']
        student.created_at = row['created_at']
        student.updated_at = row['updated_at']

        # فیلدهای Soft Delete
        student.is_deleted = row['is_deleted']
        student.deleted_at = row['deleted_at']
        student.deleted_by = row['deleted_by']

        return student