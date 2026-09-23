"""
تست‌های لایه دسترسی به داده - نسخه کامل
"""

import os
import sys
import unittest

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
from dal.observation_dal import ObservationDAL
from dal.student_dal import StudentDAL
from models.observation import Observation
from models.student import Student


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


def run_tests():
    """اجرای همه تست‌ها"""
    # (بازرسی شانزدهم) بارگذاری با TestLoader؛ API قدیمی ساخت suite در Python 3.13 حذف شده است.
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTest(loader.loadTestsFromTestCase(TestStudentDAL))
    suite.addTest(loader.loadTestsFromTestCase(TestObservationDAL))
    suite.addTest(loader.loadTestsFromTestCase(TestAcademicYearDAL))
    
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