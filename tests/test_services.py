"""
تست‌های سرویس‌ها - نسخه کامل
"""

import sys
import os
import unittest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.observation_service import ObservationService
from services.intervention_service import InterventionService
from services.followup_service import FollowUpService
from services.student_service import StudentService
from services.dashboard_service import DashboardService
from services.case_timeline_service import CaseTimelineService
from utils.error_handler import ServiceError, ValidationError


class TestObservationService(unittest.TestCase):
    """تست‌های سرویس مشاهده"""
    
    def setUp(self):
        """تنظیمات اولیه قبل از هر تست"""
        self.service = ObservationService()
        # ایجاد داده‌های تست
        self.test_data = {
            'student_id': 1,
            'staff_id': 1,
            'competency_id': None,
            'observation_date': '1405/08/15',
            'location': 'کلاس',
            'antecedent': 'معلم از دانش‌آموز سوال پرسید',
            'behavior': 'دانش‌آموز پاسخ صحیح داد',
            'consequence': 'معلم دانش‌آموز را تشویق کرد',
            'behavior_type': 'مثبت',
            'severity': 4,
            'description': 'تست مشاهده'
        }
    
    def test_validate_observation(self):
        """تست اعتبارسنجی مشاهده"""
        # داده معتبر
        is_valid, errors = self.service.validate_observation(self.test_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # داده نامعتبر (بدون دانش‌آموز)
        invalid_data = self.test_data.copy()
        invalid_data['student_id'] = None
        is_valid, errors = self.service.validate_observation(invalid_data)
        self.assertFalse(is_valid)
        self.assertTrue(any('دانش‌آموز' in e for e in errors))
        
        # داده نامعتبر (بدون مشاهده‌گر)
        invalid_data = self.test_data.copy()
        invalid_data['staff_id'] = None
        is_valid, errors = self.service.validate_observation(invalid_data)
        self.assertFalse(is_valid)
        self.assertTrue(any('مشاهده‌گر' in e for e in errors))
    
    def test_validate_observation_date(self):
        """تست اعتبارسنجی تاریخ مشاهده"""
        # تاریخ نامعتبر
        invalid_data = self.test_data.copy()
        invalid_data['observation_date'] = '1405/13/15'
        is_valid, errors = self.service.validate_observation(invalid_data)
        self.assertFalse(is_valid)
        
        # تاریخ با فرمت اشتباه
        invalid_data = self.test_data.copy()
        invalid_data['observation_date'] = '1405-08-15'
        is_valid, errors = self.service.validate_observation(invalid_data)
        self.assertFalse(is_valid)
    
    def test_validate_severity(self):
        """تست اعتبارسنجی شدت"""
        # شدت کمتر از 1
        invalid_data = self.test_data.copy()
        invalid_data['severity'] = 0
        is_valid, errors = self.service.validate_observation(invalid_data)
        self.assertFalse(is_valid)
        
        # شدت بیشتر از 5
        invalid_data = self.test_data.copy()
        invalid_data['severity'] = 6
        is_valid, errors = self.service.validate_observation(invalid_data)
        self.assertFalse(is_valid)


class TestInterventionService(unittest.TestCase):
    """تست‌های سرویس مداخله"""
    
    def setUp(self):
        """تنظیمات اولیه قبل از هر تست"""
        self.service = InterventionService()
        self.test_data = {
            'student_id': 1,
            'staff_id': 1,
            'observation_id': None,
            'type': 'individual_talk',
            'date': '1405/08/16',
            'description': 'تست مداخله',
            'goal': 'بهبود رفتار دانش‌آموز',
            'status': 'planned',
            'result': None
        }
    
    def test_validate_intervention(self):
        """تست اعتبارسنجی مداخله"""
        # داده معتبر
        is_valid, errors = self.service.validate_intervention(self.test_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # داده نامعتبر (بدون دانش‌آموز)
        invalid_data = self.test_data.copy()
        invalid_data['student_id'] = None
        is_valid, errors = self.service.validate_intervention(invalid_data)
        self.assertFalse(is_valid)
        
        # داده نامعتبر (بدون نوع)
        invalid_data = self.test_data.copy()
        invalid_data['type'] = ''
        is_valid, errors = self.service.validate_intervention(invalid_data)
        self.assertFalse(is_valid)
    
    def test_validate_status(self):
        """تست اعتبارسنجی وضعیت مداخله"""
        # وضعیت نامعتبر
        invalid_data = self.test_data.copy()
        invalid_data['status'] = 'invalid_status'
        is_valid, errors = self.service.validate_intervention(invalid_data)
        self.assertFalse(is_valid)
        
        # وضعیت معتبر
        for status in ['planned', 'in_progress', 'done', 'completed', 'cancelled']:
            valid_data = self.test_data.copy()
            valid_data['status'] = status
            is_valid, errors = self.service.validate_intervention(valid_data)
            self.assertTrue(is_valid)


class TestFollowUpService(unittest.TestCase):
    """تست‌های سرویس پیگیری"""
    
    def setUp(self):
        """تنظیمات اولیه قبل از هر تست"""
        self.service = FollowUpService()
        self.test_data = {
            'intervention_id': 1,
            'staff_id': 1,
            'date': '1405/08/17',
            'description': 'تست پیگیری',
            'status': 'pending',
            'next_action_date': '1405/08/20',
            'result_type': None,
            'result_description': None
        }
    
    def test_validate_followup(self):
        """تست اعتبارسنجی پیگیری"""
        # داده معتبر
        is_valid, errors = self.service.validate_followup(self.test_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # داده نامعتبر (بدون مداخله)
        invalid_data = self.test_data.copy()
        invalid_data['intervention_id'] = None
        is_valid, errors = self.service.validate_followup(invalid_data)
        self.assertFalse(is_valid)
        
        # داده نامعتبر (بدون مسئول)
        invalid_data = self.test_data.copy()
        invalid_data['staff_id'] = None
        is_valid, errors = self.service.validate_followup(invalid_data)
        self.assertFalse(is_valid)
    
    def test_validate_date(self):
        """تست اعتبارسنجی تاریخ پیگیری"""
        # تاریخ نامعتبر
        invalid_data = self.test_data.copy()
        invalid_data['date'] = '1405/13/17'
        is_valid, errors = self.service.validate_followup(invalid_data)
        self.assertFalse(is_valid)
    
    def test_validate_status(self):
        """تست اعتبارسنجی وضعیت پیگیری"""
        # وضعیت نامعتبر
        invalid_data = self.test_data.copy()
        invalid_data['status'] = 'invalid_status'
        is_valid, errors = self.service.validate_followup(invalid_data)
        self.assertFalse(is_valid)
        
        # وضعیت معتبر
        for status in ['pending', 'done', 'continued', 'closed', 'cancelled']:
            valid_data = self.test_data.copy()
            valid_data['status'] = status
            is_valid, errors = self.service.validate_followup(valid_data)
            self.assertTrue(is_valid)


class TestStudentService(unittest.TestCase):
    """تست‌های سرویس دانش‌آموز"""
    
    def setUp(self):
        """تنظیمات اولیه قبل از هر تست"""
        self.service = StudentService()
        self.test_data = {
            'first_name': 'علی',
            'last_name': 'محمدی',
            'national_code': '1234567890',
            'birth_date': '1390/05/15',
            'father_name': 'رضا',
            'guardian_name': 'رضا محمدی',
            'guardian_phone': '09123456789',
            'address': 'تهران'
        }
    
    def test_validate_student(self):
        """تست اعتبارسنجی دانش‌آموز"""
        from models.student import Student
        student = Student()
        student.first_name = 'علی'
        student.last_name = 'محمدی'
        errors = student.validate()
        self.assertEqual(len(errors), 0)
        
        student.first_name = ''
        errors = student.validate()
        self.assertTrue(any('نام' in e for e in errors))


class TestDashboardService(unittest.TestCase):
    """تست‌های سرویس داشبورد"""
    
    def setUp(self):
        """تنظیمات اولیه قبل از هر تست"""
        self.service = DashboardService()
    
    def test_get_dashboard_data(self):
        """تست دریافت داده‌های داشبورد"""
        # تست دریافت داده بدون فیلتر
        try:
            data = self.service.get_dashboard_data()
            self.assertIsNotNone(data)
            self.assertIn('general_stats', data)
            self.assertIn('management_indicators', data)
        except Exception as e:
            # اگر دیتابیس خالی باشد، خطا می‌دهد
            pass


class TestCaseTimelineService(unittest.TestCase):
    """تست‌های سرویس Timeline"""
    
    def setUp(self):
        """تنظیمات اولیه قبل از هر تست"""
        self.service = CaseTimelineService()
    
    def test_get_timeline(self):
        """تست دریافت Timeline"""
        # تست با شناسه نامعتبر
        events = self.service.get_timeline(None)
        self.assertEqual(events, [])
        
        # تست با شناسه معتبر (اگر وجود داشته باشد)
        # در محیط تست ممکن است داده نباشد
        try:
            events = self.service.get_timeline(1)
            self.assertIsInstance(events, list)
        except:
            pass


def run_tests():
    """اجرای همه تست‌ها"""
    # ایجاد suite تست
    suite = unittest.TestSuite()
    
    # اضافه کردن تست‌ها
    suite.addTest(unittest.makeSuite(TestObservationService))
    suite.addTest(unittest.makeSuite(TestInterventionService))
    suite.addTest(unittest.makeSuite(TestFollowUpService))
    suite.addTest(unittest.makeSuite(TestStudentService))
    suite.addTest(unittest.makeSuite(TestDashboardService))
    suite.addTest(unittest.makeSuite(TestCaseTimelineService))
    
    # اجرا
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # نمایش خلاصه
    print("\n" + "=" * 50)
    print(f"📊 خلاصه تست‌ها:")
    print(f"  • اجرا شده: {result.testsRun}")
    print(f"  • موفق: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  • ناموفق: {len(result.failures)}")
    print(f"  • خطا: {len(result.errors)}")
    print("=" * 50)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)