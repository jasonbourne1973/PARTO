"""
تست‌های لایه دسترسی به داده - نسخه کامل
"""

import os
import sys
import unittest
import uuid as _uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# جداسازی تست‌ها از دیتابیس واقعی (بازرسی ششم)
# ============================================================
# نسخه قبلی تست‌ها مستقیماً به database/partow.db واقعی وصل
# می‌شدند؛ یعنی اجرای تست‌ها می‌توانست داده در دیتابیس کاربر
# بنویسد (test_create_student یک دانش‌آموز با کد ملی جعلی
# «1234567890» ثبت می‌کرد). حالا هر اجرا روی یک دیتابیس موقت
# انجام می‌شود و به دیتابیس واقعی دست نمی‌زند.
import tempfile as _tempfile

import database.connection as _dbc
from config import settings as _settings

_TMP_DB_DIR = _tempfile.mkdtemp(prefix='partow_test_')
_settings.DB_PATH = os.path.join(_TMP_DB_DIR, 'partow.db')
_dbc.DB_PATH = _settings.DB_PATH
_dbc.DatabaseConnection._instance = None
_dbc.DatabaseConnection._connection = None
_dbc.DatabaseConnection._initialized = False

from dal.academic_year_dal import AcademicYearDAL
from dal.family_context_dal import FamilyContextDAL
from dal.observation_dal import ObservationDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.family_context import FamilyContext
from models.observation import Observation
from models.student import Student
from models.student_academic_profile import StudentAcademicProfile


class TestStudentDAL(unittest.TestCase):
    """تست‌های DAL دانش‌آموز"""
    
    def setUp(self):
        """تنظیمات اولیه قبل از هر تست"""
        self.dal = StudentDAL()
        self.test_student = Student()
        self.test_student.first_name = 'تست'
        self.test_student.last_name = 'دانش‌آموز'
        self.test_student.national_code = '1234567890'
        self.test_student.is_active = 1
    
    def test_create_student(self):
        """تست ایجاد دانش‌آموز"""
        # بازرسی دهم: این تست قبلاً کل بدنه را در try/except pass گذاشته
        # بود؛ یعنی حتی اگر assert ها شکست بخورند، تست سبز می‌شد. حالا
        # واقعاً بررسی می‌کند (دیتابیس موقت در setUp ساخته می‌شود).
        student = self.dal.create(self.test_student)
        self.assertIsNotNone(student.id)
        self.assertEqual(student.first_name, 'تست')
        self.assertEqual(student.last_name, 'دانش‌آموز')
    
    def test_validate_student(self):
        """تست اعتبارسنجی دانش‌آموز"""
        student = Student()
        student.first_name = ''
        student.last_name = 'محمدی'
        errors = student.validate()
        self.assertTrue(any('نام' in e for e in errors))
        
        student.first_name = 'علی'
        errors = student.validate()
        self.assertEqual(len(errors), 0)


class TestObservationDAL(unittest.TestCase):
    """تست‌های DAL مشاهده"""
    
    def setUp(self):
        """تنظیمات اولیه قبل از هر تست"""
        self.dal = ObservationDAL()
        self.test_observation = Observation()
        self.test_observation.student_profile_id = 1
        self.test_observation.staff_id = 1
        self.test_observation.observation_date = '1405/08/15'
        self.test_observation.location = 'کلاس'
        self.test_observation.description = 'تست مشاهده'
        self.test_observation.behavior_type = 'مثبت'
        self.test_observation.severity = 3
    
    def test_validate_observation(self):
        """تست اعتبارسنجی مشاهده"""
        obs = Observation()
        obs.student_profile_id = None
        obs.staff_id = 1
        obs.observation_date = '1405/08/15'
        obs.description = 'تست'
        errors = obs.validate()
        self.assertTrue(any('پرونده' in e for e in errors))
        
        obs.student_profile_id = 1
        # ===== اصلاح (بازرسی ششم) — «رفتار مشاهده‌شده» الزامی است =====
        obs.behavior = "رفتار تست"
        errors = obs.validate()
        self.assertEqual(len(errors), 0)


class TestAcademicYearDAL(unittest.TestCase):
    """تست‌های DAL سال تحصیلی"""
    
    def setUp(self):
        """تنظیمات اولیه قبل از هر تست"""
        self.dal = AcademicYearDAL()
    
    def test_get_active(self):
        """تست دریافت سال فعال"""
        # بازرسی دهم: بدون try/except پوشاننده تا تست واقعاً بسنجد
        year = self.dal.get_active()
        self.assertTrue(year is None or hasattr(year, 'id'))


def _unique_national_code():
    """کد ملی ۱۰ رقمی یکتا برای تست‌ها (students.national_code یکتاست)"""
    return str(9000000000 + _uuid.uuid4().int % 999999999)


class TestFamilyContextDAL(unittest.TestCase):
    """
    رگرسیون BUG-GUI-02 — پایداری اطلاعات خانوادگی

    این تست‌ها «قبل از اصلاح» شکست می‌خوردند: فرم دانش‌آموز سه ورودی
    خانوادگی را روی مدل Student می‌گذاشت و هیچ‌یک از آن‌ها در دیتابیس
    ذخیره نمی‌شد (students چنین ستون‌هایی ندارد).
    """

    def setUp(self):
        self.family_dal = FamilyContextDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.year_dal = AcademicYearDAL()

        self.student = Student()
        self.student.first_name = "خانواده"
        self.student.last_name = "تست"
        # کد ملی یکتا برای هر اجرا (جدول students روی کد ملی UNIQUE است و
        # دیتابیس تست بین تست‌ها مشترک است)
        self.student.national_code = _unique_national_code()
        self.student = self.student_dal.create(self.student)

        year = self.year_dal.get_active()
        if year is None:
            self.skipTest("سال تحصیلی فعالی برای ساخت پرونده وجود ندارد")
        self.year = year

        profile = StudentAcademicProfile()
        profile.student_id = self.student.id
        profile.academic_year_id = year.id
        profile.grade = 3
        profile.class_name = "ج"
        profile.status = "active"
        self.profile = self.profile_dal.create(profile)

    def test_family_facts_persist_and_are_read_back(self):
        """ثبت → بازخوانی از دیتابیس با همان مقادیر (و فقط یک ردیف)"""
        saved = self.family_dal.upsert_family_facts(
            self.profile.id,
            living_status="فقط با مادر",
            siblings_brothers=2,
            siblings_sisters=1,
        )
        self.assertEqual(saved.siblings_brothers, 2)
        self.assertEqual(saved.siblings_sisters, 1)
        self.assertEqual(saved.guardian_status, FamilyContext.GUARDIAN_MOTHER)
        self.assertEqual(saved.living_status, "فقط با مادر")

        again = self.family_dal.get_by_student_profile(self.profile.id)
        self.assertIsNotNone(again)
        self.assertEqual(again.id, saved.id)
        self.assertEqual(self.family_dal.count_for_profile(self.profile.id), 1)

    def test_second_save_updates_the_same_row(self):
        """ذخیرهٔ دوباره ردیف تکراری نمی‌سازد و مقدار را به‌روز می‌کند"""
        first = self.family_dal.upsert_family_facts(
            self.profile.id, living_status="با هر دو والدین",
            siblings_brothers=1, siblings_sisters=1)
        second = self.family_dal.upsert_family_facts(
            self.profile.id, living_status="با پدربزرگ و مادربزرگ",
            siblings_brothers=0, siblings_sisters=4)

        self.assertEqual(first.id, second.id)
        self.assertEqual(self.family_dal.count_for_profile(self.profile.id), 1)
        check = self.family_dal.get_by_student_profile(self.profile.id)
        self.assertEqual(check.siblings_sisters, 4)
        self.assertEqual(check.siblings_brothers, 0)
        self.assertEqual(check.guardian_status, FamilyContext.GUARDIAN_GRANDPARENTS)

    def test_unknown_living_status_is_not_silently_replaced(self):
        """مقدار ناشناخته (متن آزاد) ذخیره و بازخوانی می‌شود، نه پاک"""
        self.family_dal.upsert_family_facts(self.profile.id, living_status="با عمه")
        check = self.family_dal.get_by_student_profile(self.profile.id)
        self.assertEqual(check.guardian_status, "با عمه")
        self.assertEqual(check.living_status, "با عمه")

    def test_student_model_has_no_shadow_family_fields(self):
        """مدل Student نباید نسخهٔ سایه‌ای فیلدهای خانوادگی داشته باشد"""
        self.assertFalse(hasattr(self.student, "siblings_brothers"))
        self.assertFalse(hasattr(self.student, "siblings_sisters"))
        self.assertFalse(hasattr(self.student, "living_status"))

    def test_family_facts_are_per_profile(self):
        """هر پرونده (سال) زمینهٔ خانوادگی مستقل خودش را دارد"""
        other_student = Student()
        other_student.first_name = "دیگر"
        other_student.last_name = "دانش‌آموز"
        other_student.national_code = _unique_national_code()
        other_student = self.student_dal.create(other_student)

        other_profile = StudentAcademicProfile()
        other_profile.student_id = other_student.id
        other_profile.academic_year_id = self.year.id
        other_profile.grade = 4
        other_profile.status = "active"
        other_profile = self.profile_dal.create(other_profile)

        self.family_dal.upsert_family_facts(
            self.profile.id, living_status="فقط با پدر", siblings_brothers=3)
        self.family_dal.upsert_family_facts(
            other_profile.id, living_status="فقط با مادر", siblings_sisters=2)

        first = self.family_dal.get_by_student_profile(self.profile.id)
        second = self.family_dal.get_by_student_profile(other_profile.id)
        self.assertEqual(first.siblings_brothers, 3)
        self.assertEqual(first.guardian_status, FamilyContext.GUARDIAN_FATHER)
        self.assertEqual(second.siblings_sisters, 2)
        self.assertEqual(second.guardian_status, FamilyContext.GUARDIAN_MOTHER)

    def test_upsert_requires_profile_id(self):
        """بدون شناسهٔ پرونده، ثبت باید با خطای روشن رد شود"""
        with self.assertRaises(ValueError):
            self.family_dal.upsert_family_facts(None, siblings_brothers=1)


def run_tests():
    """اجرای همه تست‌ها"""
    # (بازرسی شانزدهم) بارگذاری با TestLoader؛ API قدیمی ساخت suite در Python 3.13 حذف شده است.
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTest(loader.loadTestsFromTestCase(TestStudentDAL))
    suite.addTest(loader.loadTestsFromTestCase(TestObservationDAL))
    suite.addTest(loader.loadTestsFromTestCase(TestAcademicYearDAL))
    suite.addTest(loader.loadTestsFromTestCase(TestFamilyContextDAL))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    print("📊 خلاصه تست‌های DAL:")
    print(f"  • اجرا شده: {result.testsRun}")
    print(f"  • موفق: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  • ناموفق: {len(result.failures)}")
    print(f"  • خطا: {len(result.errors)}")
    print("=" * 50)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)