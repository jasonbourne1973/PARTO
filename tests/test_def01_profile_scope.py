"""
آزمون‌های DEF-01 (ممیزی تکمیلی پس از دور نوزدهم)

پوشش:
  • StudentAcademicProfileDAL.update() اکنون Permission (EDIT_STUDENT) و
    Scope (DD-6) بی‌قیدوشرط دارد — هم روی رکورد موجود، هم روی دانش‌آموزِ
    مقصد اگر با تغییرِ student_id جابه‌جا شده باشد.
  • StudentAcademicProfileDAL.create() عمداً بدون Permission/Scope مانده
    (چون هم برای «دانش‌آموز تازه‌ساخته‌شده» و هم برای «ایجاد خودکار حین
    ثبت مشاهده/مداخله برای دانش‌آموز موجود» صدا زده می‌شود و فقط
    فراخوان‌کننده می‌داند کدام حالت است) — به‌جایش:
      - services/student_service.py (create_student) و
        views/dialogs/student_form.py (حالت ایجاد) بدون تغییر رفتار
        (بدون Scope) — چون دانش‌آموز تازه است و انتسابی وجود ندارد.
      - services/observation_service.py و services/intervention_service.py
        (_get_or_create_profile) اکنون Scope را زودهنگام (fail-fast)
        بررسی می‌کنند؛ نتیجهٔ نهایی (DENY/ALLOW) از قبل هم همین بود چون
        ObservationDAL.create/InterventionDAL.create در همان تراکنش
        اتمیک همین Scope را روی همان پروفایل بررسی می‌کردند.

هر تست روی دیتابیس موقت تازه اجرا می‌شود (از HardDeleteRestoreTestBase در
tests/test_hard_delete_restore_edge.py استفاده می‌شود تا فیکسچرهای مشترک
دوباره‌نویسی نشوند).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_hard_delete_restore_edge import HardDeleteRestoreTestBase


class Def01TestBase(HardDeleteRestoreTestBase):
    """پایهٔ مشترک + کمکیِ انتساب معلم (از TestProfilePermissionAndScope کپی نشده،
    بلکه دوباره تعریف شده تا این فایل مستقل از آن کلاس باشد)."""

    def _assign_teacher(self, student_id, staff_id, is_active=1, is_deleted=0):
        self.db.get_connection().execute(
            """
            INSERT INTO teacher_assignments
                (student_id, staff_id, academic_year_id, is_active, is_deleted)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, staff_id, self.year_id, is_active, is_deleted),
        )
        self.db.get_connection().commit()


# ================================================================
# StudentAcademicProfileDAL.update() — Permission + Scope
# ================================================================

class TestProfileUpdatePermissionAndScope(Def01TestBase):
    def test_update_requires_permission(self):
        from utils.security import PermissionDeniedError
        viewer_id = self._make_staff_and_user("viewer", "viewer_upd1")
        student = self._new_student("به‌روزرسانی۱", "9500000001")
        profile = self._new_profile(student.id)
        self._login(viewer_id)
        profile.grade = 2
        with self.assertRaises(PermissionDeniedError):
            self.profile_dal.update(profile)

    def test_update_blocked_for_teacher_outside_scope(self):
        from utils.security import PermissionDeniedError
        teacher_id = self._make_staff_and_user("teacher", "teacher_upd1")
        student = self._new_student("به‌روزرسانی۲", "9500000002")
        profile = self._new_profile(student.id)
        # عمداً منتسب نشده
        self._login(teacher_id)
        profile.grade = 2
        with self.assertRaises(PermissionDeniedError):
            self.profile_dal.update(profile)

    def test_update_succeeds_for_teacher_inside_scope(self):
        teacher_id = self._make_staff_and_user("teacher", "teacher_upd2")
        student = self._new_student("به‌روزرسانی۳", "9500000003")
        profile = self._new_profile(student.id)
        self._assign_teacher(student.id, teacher_id)
        self._login(teacher_id)
        profile.grade = 4
        profile.class_name = "چهارم-ب"
        saved = self.profile_dal.update(profile)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.grade, 4)

    def test_update_succeeds_for_manager(self):
        """مدیر بدون محدودیت Scope است (DD-6)"""
        student = self._new_student("به‌روزرسانی۴", "9500000004")
        profile = self._new_profile(student.id)
        profile.grade = 5
        saved = self.profile_dal.update(profile)
        self.assertIsNotNone(saved)

    def test_update_cross_student_denied_when_target_out_of_scope(self):
        """
        معلم به دانش‌آموز A منتسب است ولی نه به B؛ اگر بخواهد پروندهٔ A را
        با تغییرِ student_id به B منتقل کند، باید رد شود (نه فقط بررسیِ
        رکورد موجود، بلکه بررسیِ دانش‌آموزِ مقصد هم).
        """
        from utils.security import PermissionDeniedError
        teacher_id = self._make_staff_and_user("teacher", "teacher_upd3")
        student_a = self._new_student("متقاطع‌الف", "9500000005")
        student_b = self._new_student("متقاطع‌ب", "9500000006")
        profile = self._new_profile(student_a.id)
        self._assign_teacher(student_a.id, teacher_id)
        # عمداً به student_b منتسب نشده
        self._login(teacher_id)
        profile.student_id = student_b.id
        with self.assertRaises(PermissionDeniedError):
            self.profile_dal.update(profile)

    def test_update_returns_none_for_missing_profile_without_session(self):
        """رفتار قبلی (بدون نشست) باید دست‌نخورده بماند"""
        from models.student_academic_profile import StudentAcademicProfile
        ghost = StudentAcademicProfile()
        ghost.id = 999999
        ghost.student_id = 1
        ghost.academic_year_id = self.year_id
        ghost.grade = 1
        ghost.class_name = "x"
        ghost.status = "active"
        self.assertIsNone(self.profile_dal.update(ghost))


# ================================================================
# StudentAcademicProfileDAL.create() — عمداً بدون Scope در خودِ DAL،
# اما Scope در فراخوان‌کننده‌های «دانش‌آموز موجود» (observation/intervention)
# ================================================================

class TestProfileCreateCallSiteScope(Def01TestBase):
    def _valid_obs_data(self, student_id, staff_id):
        return {
            "student_id": student_id,
            "staff_id": staff_id,
            "observation_date": "1404/01/01",
            "behavior": "رفتار آزمون",
            "description": "توضیح آزمون",
            "behavior_type": "خنثی",
        }

    def _valid_inter_data(self, student_id, staff_id):
        return {
            "student_id": student_id,
            "staff_id": staff_id,
            "type": "گفتگوی فردی",
            "date": "1404/01/01",
            "description": "مداخلهٔ آزمون",
        }

    def test_observation_create_denied_for_teacher_outside_scope_no_profile_leak(self):
        """
        معلمِ خارج از Scope نباید بتواند با ثبت مشاهده، پروندهٔ سالانهٔ
        دانش‌آموزِ خارج از Scope را هم (به‌عنوان اثر جانبی) بسازد. چون
        _get_or_create_profile و ObservationDAL.create هر دو در یک
        تراکنش اتمیک‌اند، رد Scope باید کل کار (از جمله ساختِ پرونده) را
        rollback کند.
        """
        from services.observation_service import ObservationService
        from utils.security import PermissionDeniedError

        teacher_id = self._make_staff_and_user("teacher", "teacher_obs1")
        student = self._new_student("مشاهدهٔ‌اسکوپ۱", "9500000010")
        # عمداً منتسب نشده

        self._login(teacher_id)
        with self.assertRaises(PermissionDeniedError):
            ObservationService().create_observation(
                self._valid_obs_data(student.id, teacher_id))

        # هیچ پروندهٔ سالانه‌ای نباید برای این دانش‌آموز ساخته شده باشد
        self.ac.logout()  # بافت سیستمی: بدون محدودیت Scope برای بررسی مستقیم
        profiles = self.profile_dal.get_all_profiles_for_student(
            student.id, include_deleted=True) if hasattr(
            self.profile_dal, "get_all_profiles_for_student") else None
        if profiles is None:
            row = self.db.get_connection().execute(
                "SELECT COUNT(*) c FROM student_academic_profiles WHERE student_id = ?",
                (student.id,)
            ).fetchone()
            self.assertEqual(row["c"], 0)
        else:
            self.assertEqual(len(profiles), 0)

    def test_observation_create_succeeds_for_teacher_inside_scope(self):
        from services.observation_service import ObservationService

        teacher_id = self._make_staff_and_user("teacher", "teacher_obs2")
        student = self._new_student("مشاهدهٔ‌اسکوپ۲", "9500000011")
        self._assign_teacher(student.id, teacher_id)

        self._login(teacher_id)
        obs = ObservationService().create_observation(
            self._valid_obs_data(student.id, teacher_id))
        self.assertIsNotNone(obs.id)

        self.ac.logout()
        row = self.db.get_connection().execute(
            "SELECT COUNT(*) c FROM student_academic_profiles WHERE student_id = ?",
            (student.id,)
        ).fetchone()
        self.assertEqual(row["c"], 1)

    def test_intervention_create_denied_for_teacher_outside_scope_no_profile_leak(self):
        from services.intervention_service import InterventionService
        from utils.security import PermissionDeniedError

        teacher_id = self._make_staff_and_user("teacher", "teacher_int1")
        student = self._new_student("مداخلهٔ‌اسکوپ۱", "9500000012")

        self._login(teacher_id)
        with self.assertRaises(PermissionDeniedError):
            InterventionService().create_intervention(
                self._valid_inter_data(student.id, teacher_id))

        self.ac.logout()
        row = self.db.get_connection().execute(
            "SELECT COUNT(*) c FROM student_academic_profiles WHERE student_id = ?",
            (student.id,)
        ).fetchone()
        self.assertEqual(row["c"], 0)

    def test_intervention_create_succeeds_for_teacher_inside_scope(self):
        from services.intervention_service import InterventionService

        teacher_id = self._make_staff_and_user("teacher", "teacher_int2")
        student = self._new_student("مداخلهٔ‌اسکوپ۲", "9500000013")
        self._assign_teacher(student.id, teacher_id)

        self._login(teacher_id)
        inter = InterventionService().create_intervention(
            self._valid_inter_data(student.id, teacher_id))
        self.assertIsNotNone(inter.id)

    def test_teacher_can_still_create_brand_new_student_with_auto_profile(self):
        """
        رگرسیونِ حیاتی: معلم باید همچنان بتواند دانش‌آموز تازه بسازد و
        پروندهٔ سالانهٔ خودکارش هم بدون خطای Scope ساخته شود — چون در
        این لحظه هیچ انتسابی برای دانش‌آموزِ تازه نمی‌تواند وجود داشته
        باشد؛ اگر create() بی‌قیدوشرط Scope می‌خواست، این مسیر می‌شکست.
        """
        from services.student_service import StudentService

        teacher_id = self._make_staff_and_user("teacher", "teacher_newstu1")
        self._login(teacher_id)
        student = StudentService().create_student({
            "first_name": "دانش‌آموز",
            "last_name": "تازهٔ‌معلم",
            "national_code": "9500000014",
            "grade": 1,
            "class_name": "اول-الف",
        })
        self.assertIsNotNone(student.id)

        self.ac.logout()
        row = self.db.get_connection().execute(
            "SELECT COUNT(*) c FROM student_academic_profiles WHERE student_id = ?",
            (student.id,)
        ).fetchone()
        self.assertEqual(row["c"], 1)


if __name__ == "__main__":
    unittest.main()
