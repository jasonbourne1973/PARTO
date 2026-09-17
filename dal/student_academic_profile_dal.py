"""
لایه دسترسی به داده پرونده‌های سالانه دانش‌آموز
با متدهای چندساله برای گزارش روند
"""

import json
import sqlite3
from datetime import datetime

from database.connection import DatabaseConnection
from models.student_academic_profile import StudentAcademicProfile


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
            print("📝 ایجاد پرونده سالانه:")
            print(f"   student_id: {profile.student_id}")
            print(f"   academic_year_id: {profile.academic_year_id}")
            print(f"   grade: {profile.grade}")
            print(f"   class_name: {profile.class_name}")
            print(f"   status: {profile.status}")

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

            print(f"✅ پرونده سالانه با ID {profile.id} ایجاد شد.")
            return profile

        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise Exception(f"خطای دیتابیس هنگام ایجاد پرونده سالانه: {e}")

        except Exception:
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
        cursor = self.db.execute_query("""
            SELECT sap.* FROM student_academic_profiles sap
            JOIN academic_years ay ON sap.academic_year_id = ay.id
            WHERE sap.student_id = ?
              AND ay.is_active = 1
              AND ay.is_deleted = 0
              AND ay.is_archived = 0
              AND sap.is_deleted = 0
              AND sap.status NOT IN ('archived', 'closed')
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
            except Exception:
                history = []

            history.append({
                'from': old_status,
                'to': new_status,
                'date': datetime.now().isoformat(),
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

    def delete(self, profile_id):
        """حذف منطقی پرونده (بایگانی)"""
        return self.update_status(
            profile_id,
            StudentAcademicProfile.STATUS_ARCHIVED,
            "حذف منطقی توسط کاربر"
        )

    def archive(self, profile_id):
        """بایگانی کردن پرونده"""
        return self.update_status(profile_id, StudentAcademicProfile.STATUS_ARCHIVED, "بایگانی شد")

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