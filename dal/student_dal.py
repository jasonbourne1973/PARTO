"""
لایه دسترسی به داده دانش‌آموزان (اطلاعات دائمی) - با Soft Delete یکپارچه
با متدهای تحلیلی برای داشبورد
"""

import sqlite3
from datetime import datetime

from database.connection import DatabaseConnection
from models.student import Student


class StudentDAL:
    """عملیات CRUD برای دانش‌آموزان با Soft Delete یکپارچه"""

    def __init__(self):
        self.db = DatabaseConnection()

    def create(self, student):
        """ایجاد دانش‌آموز جدید"""
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

            conn.commit()
            student.id = cursor.lastrowid
            student.national_code = national_code
            return student

        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise Exception(f"خطا در ثبت دانش‌آموز: {e}")

        except Exception:
            conn.rollback()
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

    def get_all(self, limit=None, offset=None, include_deleted=False):
        """دریافت همه دانش‌آموزان - فقط رکوردهای موجود"""
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

    def search(self, search_term, include_deleted=False):
        """جستجوی دانش‌آموزان - فقط رکوردهای موجود"""
        query = """
            SELECT * FROM students
            WHERE (first_name LIKE ? OR last_name LIKE ? OR national_code LIKE ?)
        """
        if not include_deleted:
            query += " AND is_deleted = 0"

        query += " ORDER BY last_name, first_name"

        cursor = self.db.execute_query(query, (
            f"%{search_term}%",
            f"%{search_term}%",
            f"%{search_term}%"
        ))

        rows = cursor.fetchall()
        return [self._row_to_student(row) for row in rows]

    def update(self, student):
        """به‌روزرسانی دانش‌آموز - فقط رکوردهای موجود"""
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

            conn.commit()
            student.national_code = national_code
            return student

        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise Exception(f"خطا در ویرایش دانش‌آموز: {e}")

        except Exception:
            conn.rollback()
            raise

    def delete(self, student_id, user_id=None):
        """حذف منطقی دانش‌آموز - فقط رکوردهای موجود"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM students WHERE id = ? AND is_deleted = 0",
            (student_id,)
        )
        if not cursor.fetchone():
            return False

        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE students SET
                is_deleted = 1,
                is_active = 0,
                deleted_at = ?,
                deleted_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (now, user_id, student_id))

        conn.commit()
        return True

    def restore(self, student_id, user_id=None):
        """بازیابی دانش‌آموز حذف شده - فقط رکوردهای حذف شده"""
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

        conn.commit()
        return True

    def get_deleted(self, limit=None):
        """دریافت لیست رکوردهای حذف شده"""
        query = "SELECT * FROM students WHERE is_deleted = 1 ORDER BY deleted_at DESC"
        params = []

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.db.execute_query(query, tuple(params) if params else None)
        rows = cursor.fetchall()
        return [self._row_to_student(row) for row in rows]

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
        except Exception as e:
            print(f"خطا در جستجوی پیشرفته: {e}")
            return []

    def permanent_delete(self, student_id):
        """حذف فیزیکی دانش‌آموز - فقط برای موارد خاص استفاده شود"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM students WHERE id = ?",
            (student_id,)
        )
        conn.commit()
        return True

    # ============================================================
    # متدهای تحلیلی برای داشبورد
    # ============================================================

    def get_student_distribution_by_grade(self, academic_year_id=None):
        """
        دریافت توزیع دانش‌آموزان بر اساس پایه

        Args:
            academic_year_id: شناسه سال تحصیلی (اختیاری)

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

            query += " GROUP BY sap.grade ORDER BY sap.grade"

            cursor.execute(query, params if params else None)
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

        except Exception as e:
            print(f"خطا در دریافت توزیع دانش‌آموزان: {e}")
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

            cursor.execute(query, params if params else None)
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

        except Exception as e:
            print(f"خطا در دریافت تعداد دانش‌آموزان بر اساس وضعیت: {e}")
            return {'active': 0, 'inactive': 0, 'graduated': 0, 'transferred': 0, 'dropped': 0, 'total': 0}

    def get_students_without_observations(self, academic_year_id=None):
        """
        دریافت دانش‌آموزانی که هیچ مشاهده‌ای ندارند

        Args:
            academic_year_id: شناسه سال تحصیلی (اختیاری)

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

            query += " ORDER BY s.last_name, s.first_name"

            cursor.execute(query, params if params else None)
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

        except Exception as e:
            print(f"خطا در دریافت دانش‌آموزان بدون مشاهده: {e}")
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

        except Exception as e:
            print(f"خطا در دریافت خلاصه فعالیت‌های دانش‌آموز: {e}")
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