"""
تست‌های یکپارچگی نوشتن دانش‌آموز (دور هفدهم — مرحلهٔ ۲)

مبنا: بندهای ۱۲ و ۱۳ مأموریت MASTER FIX

  • CREATE/EDIT باید اتمیک باشد: شکست در هر مرحله (دانش‌آموز، پروندهٔ
    سالانه، زمینهٔ خانوادگی) نباید رکورد نیمه‌ساخته («دانش‌آموز یتیم»)
    باقی بگذارد.
  • نتیجهٔ UPDATE باید واقعاً بررسی شود: به‌روزرسانی رکورد ناموجود یا
    حذف‌شده نباید «موفقیت» تلقی شود.

تست‌ها روی دیتابیس موقت اجرا می‌شوند؛ به دادهٔ کاربر دست نمی‌زنند و به
اتصال سراسری برنامه هم وابسته نیستند.
"""

import contextlib
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.connection as _dbc
from config import settings as _settings

_TMP_DB_DIR = tempfile.mkdtemp(prefix='partow_atomic_test_')
_settings.DB_PATH = os.path.join(_TMP_DB_DIR, 'partow.db')
_dbc.DB_PATH = _settings.DB_PATH
_dbc.DatabaseConnection._instance = None
_dbc.DatabaseConnection._connection = None
_dbc.DatabaseConnection._initialized = False

from dal.family_context_dal import FamilyContextDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.student import Student
from models.student_academic_profile import StudentAcademicProfile


def _make_student(first_name='آزمون', last_name='اتمیک', national_code='1701111111'):
    student = Student()
    student.first_name = first_name
    student.last_name = last_name
    student.national_code = national_code
    student.is_active = 1
    return student


class TestStudentWriteAtomicity(unittest.TestCase):
    """اتمیک‌بودن مسیر نوشتن: دانش‌آموز + پرونده + زمینهٔ خانوادگی"""

    def setUp(self):
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.family_dal = FamilyContextDAL()
        self.db = self.student_dal.db
        self.conn = self.db.get_connection(user_id=1)
        with contextlib.redirect_stdout(io.StringIO()):
            active = self.db.execute_query(
                "SELECT id, title FROM academic_years WHERE is_active = 1 "
                "ORDER BY id LIMIT 1").fetchone()
        if active is None:
            self.db.execute_query(
                "INSERT INTO academic_years (title, start_date, end_date, "
                "is_active, is_archived) VALUES ('1404-1405', '1404/07/01', "
                "'1405/06/30', 1, 0)")
            self.db.commit()
            active = self.db.execute_query(
                "SELECT id, title FROM academic_years WHERE is_active = 1 "
                "ORDER BY id LIMIT 1").fetchone()
        self.year_id = active[0]

    def _counts(self, national_code):
        row = self.conn.execute(
            "SELECT id FROM students WHERE national_code = ?",
            (national_code,)).fetchone()
        if row is None:
            return None, 0, 0
        profiles = self.conn.execute(
            "SELECT COUNT(*) FROM student_academic_profiles WHERE student_id = ?",
            (row[0],)).fetchone()[0]
        family = self.conn.execute(
            "SELECT COUNT(*) FROM family_contexts f JOIN student_academic_profiles p "
            "ON p.id = f.student_profile_id WHERE p.student_id = ?",
            (row[0],)).fetchone()[0]
        return row[0], profiles, family

    def test_rollback_removes_all_three_writes(self):
        """شکست مرحلهٔ سوم → دانش‌آموز، پرونده و زمینهٔ خانوادگی همه برمی‌گردند"""
        code = '1701111112'
        student = _make_student(national_code=code)

        self.db.begin_transaction()
        created = self.student_dal.create(student)
        profile = StudentAcademicProfile()
        profile.student_id = created.id
        profile.academic_year_id = self.year_id
        profile.grade = 1
        profile.status = StudentAcademicProfile.STATUS_ACTIVE
        saved_profile = self.profile_dal.create(profile)
        saved_family = self.family_dal.upsert_family_facts(
            saved_profile.id, living_status='با هر دو والدین',
            siblings_brothers=1, siblings_sisters=1)
        self.assertIsNotNone(saved_family)

        # پیش از rollback هر سه نوشته در همان تراکنش دیده می‌شوند
        before = self._counts(code)
        self.assertIsNotNone(before[0])

        self.db.rollback_transaction()

        after = self._counts(code)
        self.assertIsNone(after[0], 'دانش‌آموز پس از rollback باقی مانده است')
        self.assertEqual(after[1], 0)
        self.assertEqual(after[2], 0)

    def test_commit_keeps_all_three_writes(self):
        """مسیر موفق: هر سه نوشته با یک commit ثبت می‌شوند"""
        code = '1701111113'
        student = _make_student(national_code=code)

        self.db.begin_transaction()
        created = self.student_dal.create(student)
        profile = StudentAcademicProfile()
        profile.student_id = created.id
        profile.academic_year_id = self.year_id
        profile.grade = 2
        profile.status = StudentAcademicProfile.STATUS_ACTIVE
        saved_profile = self.profile_dal.create(profile)
        self.family_dal.upsert_family_facts(
            saved_profile.id, living_status='فقط با مادر',
            siblings_brothers=2, siblings_sisters=3)
        self.db.commit_transaction()

        student_id, profiles, family = self._counts(code)
        self.assertIsNotNone(student_id)
        self.assertEqual(profiles, 1)
        self.assertEqual(family, 1)

        stored = self.conn.execute(
            "SELECT guardian_status, siblings_brothers, siblings_sisters, is_deleted "
            "FROM family_contexts WHERE student_profile_id = ?",
            (saved_profile.id,)).fetchone()
        self.assertEqual(stored['siblings_brothers'], 2)
        self.assertEqual(stored['siblings_sisters'], 3)
        # «فقط با مادر» باید به کد کانونیکال guardian_status نگاشت شده باشد
        from models.family_context import FamilyContext
        self.assertEqual(stored['guardian_status'], FamilyContext.GUARDIAN_MOTHER)


class TestUpdateResultIsChecked(unittest.TestCase):
    """نتیجهٔ واقعی UPDATE (بند ۱۳)"""

    def setUp(self):
        self.dal = StudentDAL()
        self.conn = self.dal.db.get_connection(user_id=1)

    def test_update_missing_row_returns_none(self):
        student = _make_student(national_code='1702222221')
        student.id = 987654
        self.assertIsNone(self.dal.update(student))

    def test_update_deleted_row_returns_none(self):
        student = _make_student(national_code='1702222222')
        saved = self.dal.create(student)
        self.dal.delete(saved.id)
        self.assertIsNone(self.dal.update(saved))

    def test_update_existing_row_returns_model(self):
        student = _make_student(national_code='1702222223')
        saved = self.dal.create(student)
        saved.first_name = 'ویرایش‌شده'
        result = self.dal.update(saved)
        self.assertIsNotNone(result)
        stored = self.conn.execute(
            "SELECT first_name FROM students WHERE id = ?", (saved.id,)).fetchone()
        self.assertEqual(stored[0], 'ویرایش‌شده')


class TestProfileUpdateResult(unittest.TestCase):
    """نتیجهٔ واقعی UPDATE برای پروندهٔ سالانه"""

    def setUp(self):
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.conn = self.student_dal.db.get_connection(user_id=1)

    def test_profile_update_missing_row_returns_none(self):
        profile = StudentAcademicProfile()
        profile.id = 987655
        profile.student_id = 1
        profile.academic_year_id = 1
        profile.grade = 1
        profile.status = StudentAcademicProfile.STATUS_ACTIVE
        self.assertIsNone(self.profile_dal.update(profile))


if __name__ == '__main__':
    unittest.main()
