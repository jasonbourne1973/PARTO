"""
تست‌های مدل‌ها - PARTOW
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from models.student import Student
from models.student_academic_profile import StudentAcademicProfile
from models.observation import Observation
from models.intervention import Intervention
from models.followup import FollowUp
from models.academic_year import AcademicYear


class TestStudent(unittest.TestCase):
    """تست‌های مدل Student"""
    
    def test_create_student(self):
        student = Student()
        student.first_name = "علی"
        student.last_name = "محمدی"
        student.national_code = "1234567890"
        
        self.assertEqual(student.full_name, "علی محمدی")
        self.assertEqual(student.national_code, "1234567890")
    
    def test_validate_student(self):
        student = Student()
        errors = student.validate()
        self.assertTrue(len(errors) > 0)  # باید خطا داشته باشد
        
        student.first_name = "علی"
        student.last_name = "محمدی"
        errors = student.validate()
        self.assertEqual(len(errors), 0)  # بدون خطا


class TestAcademicYear(unittest.TestCase):
    """تست‌های مدل AcademicYear"""
    
    def test_create_academic_year(self):
        year = AcademicYear()
        year.title = "1406-1407"
        year.is_active = 1
        
        self.assertEqual(year.title, "1406-1407")
        self.assertEqual(year.status_display, "🟢 فعال")
        self.assertEqual(year.display_name, "1406-1407")
    
    def test_validate_academic_year(self):
        year = AcademicYear()
        errors = year.validate()
        self.assertTrue(len(errors) > 0)
        
        year.title = "1406-1407"
        errors = year.validate()
        self.assertEqual(len(errors), 0)


class TestObservation(unittest.TestCase):
    """تست‌های مدل Observation با ABC"""
    
    def test_create_observation(self):
        obs = Observation()
        obs.student_profile_id = 1
        obs.staff_id = 2
        obs.observation_date = "1406/07/15"
        obs.description = "دانش‌آموز در فعالیت گروهی همکاری خوبی داشت."
        obs.antecedent = "معلم از دانش‌آموزان خواست گروهی کار کنند."
        obs.behavior = "دانش‌آموز با اعضای گروه همکاری کرد."
        obs.consequence = "کار گروهی به موقع انجام شد."
        obs.behavior_type = "مثبت"
        obs.severity = 4
        
        self.assertEqual(obs.behavior_type, "مثبت")
        self.assertEqual(obs.severity_display, "⭐⭐⭐⭐")
        self.assertTrue("زمینه" in obs.abc_summary)
    
    def test_validate_observation(self):
        obs = Observation()
        errors = obs.validate()
        self.assertTrue(len(errors) > 0)
        
        obs.student_profile_id = 1
        obs.staff_id = 2
        obs.observation_date = "1406/07/15"
        obs.description = "تست"
        # ===== اصلاح (بازرسی ششم) =====
        # مدل از نسخهٔ سه‌لایه به بعد «رفتار مشاهده‌شده» را هم
        # الزامی می‌داند (AB؛ مدل Observation.validate در
        # models/observation.py)، ولی این تست قدیمی بود و آن را
        # پر نمی‌کرد؛ به همین دلیل شکست می‌خورد.
        obs.behavior = "رفتار تست"
        errors = obs.validate()
        self.assertEqual(len(errors), 0)
    
    def test_behavior_types(self):
        obs = Observation()
        obs.behavior_type = "مثبت"
        self.assertEqual(obs.behavior_type_display, "✅ مثبت")
        
        obs.behavior_type = "منفی"
        self.assertEqual(obs.behavior_type_display, "❌ منفی")


class TestIntervention(unittest.TestCase):
    """تست‌های مدل Intervention"""
    
    def test_create_intervention(self):
        inter = Intervention()
        inter.type = "individual_talk"
        inter.status = "planned"
        
        self.assertEqual(inter.type_display, "گفتگوی فردی")
        self.assertEqual(inter.status_display, "برنامه‌ریزی شده")
        self.assertTrue(inter.is_active_intervention)
    
    def test_validate_intervention(self):
        inter = Intervention()
        errors = inter.validate()
        self.assertTrue(len(errors) > 0)
        
        inter.student_profile_id = 1
        inter.staff_id = 2
        inter.type = "individual_talk"
        inter.description = "تست"
        inter.date = "1406/07/20"
        errors = inter.validate()
        self.assertEqual(len(errors), 0)


class TestFollowUp(unittest.TestCase):
    """تست‌های مدل FollowUp"""
    
    def test_create_followup(self):
        follow = FollowUp()
        follow.status = "pending"
        follow.result_type = "improved"
        
        self.assertEqual(follow.status_display, "در انتظار")
        self.assertEqual(follow.result_type_display, "بهبود مشاهده شد")  # بدون Emoji (سیاست پروژه)
        self.assertTrue(follow.is_pending)
    
    def test_validate_followup(self):
        follow = FollowUp()
        errors = follow.validate()
        self.assertTrue(len(errors) > 0)
        
        follow.intervention_id = 1
        follow.staff_id = 2
        follow.date = "1406/07/25"
        errors = follow.validate()
        self.assertEqual(len(errors), 0)


if __name__ == '__main__':
    unittest.main()