"""
آزمون‌های مرحلهٔ ۸ — دور نوزدهم (SEC-HARD-DELETE-01 / RESTORE-EDGE-01)

پوشش مأموریت:
  • SEC-HARD-DELETE-01 — قبل از این مرحله، permanent_delete در
    StudentDAL/ObservationDAL/InterventionDAL/FollowUpDAL/UserDAL هیچ
    بررسیِ Permission نداشت (کاربر بی‌مجوز هم می‌توانست مستقیم صدا بزند)
    و در StudentDAL/InterventionDAL هیچ بررسیِ وابستگی نداشت — با اینکه
    این دو جدول با ON DELETE CASCADE به فرزندانشان وصل‌اند و حذف دائم
    عملاً کل تاریخچهٔ وابسته را بدون Audit Trail نابود می‌کرد.
    StaffDAL.permanent_delete از قبل گاردِ وابستگی داشت ولی Permission
    نداشت. این‌ها اکنون همه اصلاح شده‌اند (بدون افزودن Permission تازه —
    از همان مجوزِ delete()/restore() موجود استفاده شده).
  • RESTORE-EDGE-01 — قبل از این مرحله، restore() در
    ObservationDAL/InterventionDAL/FollowUpDAL/StudentAcademicProfileDAL
    فقط Scope موجودیت را بررسی می‌کرد، نه اینکه موجودیت والد (پروندهٔ
    سالانه/مداخله/دانش‌آموز) خودش هنوز موجود و حذف‌نشده باشد. حالا هر
    چهار متد این بررسی را دارند و AttachmentService.restore_attachment
    هم همین بررسی را برای موجودیت والدِ پیوست اضافه کرده.

هر تست روی دیتابیس موقت تازه اجرا می‌شود.
"""

import contextlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.connection as _dbc
from config import settings as _settings


class HardDeleteRestoreTestBase(unittest.TestCase):
    """پایهٔ مشترک: دیتابیس موقت + فیکسچرهای دانش‌آموز/پرونده/زنجیرهٔ کامل"""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="partow_hard_delete_")
        self._saved = (_settings.DB_PATH, _dbc.DB_PATH)
        _settings.DB_PATH = os.path.join(self._tmpdir, "partow.db")
        _dbc.DB_PATH = _settings.DB_PATH
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False

        self.db = _dbc.DatabaseConnection()  # seed اولیه

        from utils.security import AccessControl
        AccessControl.logout()
        self.ac = AccessControl

        from dal.followup_dal import FollowUpDAL
        from dal.intervention_dal import InterventionDAL
        from dal.observation_dal import ObservationDAL
        from dal.staff_dal import StaffDAL
        from dal.student_academic_profile_dal import StudentAcademicProfileDAL
        from dal.student_dal import StudentDAL
        from dal.user_dal import UserDAL

        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.staff_dal = StaffDAL()
        self.user_dal = UserDAL()

        row = self.db.get_connection().execute(
            "SELECT id FROM academic_years WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        self.year_id = row["id"]

    def tearDown(self):
        self.ac.logout()
        with contextlib.suppress(Exception):
            _dbc.DatabaseConnection().close_all()
        db_path, dbc_path = self._saved
        _settings.DB_PATH, _dbc.DB_PATH = db_path, dbc_path
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False
        with contextlib.suppress(Exception):
            import shutil
            shutil.rmtree(self._tmpdir, ignore_errors=True)

    # ---------------- کمکی ----------------

    def _new_student(self, last_name, national_code):
        from models.student import Student
        s = Student()
        s.first_name = "آزمون"
        s.last_name = last_name
        s.national_code = national_code
        return self.student_dal.create(s)

    def _new_profile(self, student_id, academic_year_id=None):
        from models.student_academic_profile import StudentAcademicProfile
        p = StudentAcademicProfile()
        p.student_id = student_id
        p.academic_year_id = academic_year_id or self.year_id
        p.grade = 1
        p.class_name = "اول-الف"
        return self.profile_dal.create(p)

    def _new_observation(self, profile_id, staff_id=1):
        from models.observation import Observation
        o = Observation()
        o.student_profile_id = profile_id
        o.staff_id = staff_id
        o.observation_date = "1404/01/01"
        o.description = "مشاهدهٔ آزمون مرحلهٔ ۸"
        o.behavior_type = "خنثی"
        return self.observation_dal.create(o)

    def _new_intervention(self, profile_id, staff_id=1):
        from models.intervention import Intervention
        i = Intervention()
        i.student_profile_id = profile_id
        i.staff_id = staff_id
        i.type = "گفتگوی فردی"
        i.date = "1404/01/01"
        i.description = "مداخلهٔ آزمون مرحلهٔ ۸"
        return self.intervention_dal.create(i)

    def _new_followup(self, intervention_id, staff_id=1):
        from models.followup import FollowUp
        f = FollowUp()
        f.intervention_id = intervention_id
        f.staff_id = staff_id
        f.date = "1404/01/01"
        f.description = "پیگیری آزمون مرحلهٔ ۸"
        return self.followup_dal.create(f)

    def _make_staff_and_user(self, role, username):
        """ساخت staff+user با نقش دلخواه در «بافت سیستمی» (بدون نشست جاری)"""
        from dal.user_dal import UserDAL
        from models.staff import Staff
        from models.user import User

        saved = self.ac.current_staff_id()
        self.ac.logout()
        try:
            staff = Staff()
            staff.full_name = f"آزمون {role}"
            staff.role = "other"
            staff_id = self.staff_dal.create(staff).id

            user = User()
            user.staff_id = staff_id
            user.username = username
            user.role = role
            user.is_active = 1
            UserDAL().create(user, raw_password="Passw0rd!123")
        finally:
            if saved is not None:
                self.ac.login(saved, None)
        return staff_id

    def _login(self, staff_id):
        self.ac.login(staff_id, None)


# ================================================================
# SEC-HARD-DELETE-01
# ================================================================

class TestStudentPermanentDeleteGuards(HardDeleteRestoreTestBase):
    def test_permission_required(self):
        from utils.security import PermissionDeniedError
        viewer_id = self._make_staff_and_user("viewer", "viewer_hd1")
        student = self._new_student("حذف‌دائم", "9200000001")
        self._login(viewer_id)
        with self.assertRaises(PermissionDeniedError):
            self.student_dal.permanent_delete(student.id)

    def test_blocked_when_profile_exists(self):
        student = self._new_student("حذف‌دائم۲", "9200000002")
        self._new_profile(student.id)
        with self.assertRaises(ValueError):
            self.student_dal.permanent_delete(student.id)
        # دانش‌آموز باید سرِ جایش باشد (رد شدنِ حذف واقعاً اثر کرده)
        row = self.db.get_connection().execute(
            "SELECT id FROM students WHERE id = ?", (student.id,)).fetchone()
        self.assertIsNotNone(row)

    def test_succeeds_when_no_profile(self):
        student = self._new_student("حذف‌دائم۳", "9200000003")
        self.assertTrue(self.student_dal.permanent_delete(student.id))
        row = self.db.get_connection().execute(
            "SELECT id FROM students WHERE id = ?", (student.id,)).fetchone()
        self.assertIsNone(row)

    def test_returns_false_for_nonexistent_student(self):
        self.assertFalse(self.student_dal.permanent_delete(999999))


class TestObservationPermanentDeleteGuards(HardDeleteRestoreTestBase):
    def test_permission_required(self):
        from utils.security import PermissionDeniedError
        viewer_id = self._make_staff_and_user("viewer", "viewer_hd2")
        student = self._new_student("مشاهده‌حذف", "9200000010")
        profile = self._new_profile(student.id)
        obs = self._new_observation(profile.id)
        self._login(viewer_id)
        with self.assertRaises(PermissionDeniedError):
            self.observation_dal.permanent_delete(obs.id)

    def test_succeeds_without_blocking_dependency(self):
        """FK به observations فقط SET NULL است — نباید مسدود شود"""
        student = self._new_student("مشاهده‌حذف۲", "9200000011")
        profile = self._new_profile(student.id)
        obs = self._new_observation(profile.id)
        self.assertTrue(self.observation_dal.permanent_delete(obs.id))
        row = self.db.get_connection().execute(
            "SELECT id FROM observations WHERE id = ?", (obs.id,)).fetchone()
        self.assertIsNone(row)


class TestInterventionPermanentDeleteGuards(HardDeleteRestoreTestBase):
    def test_permission_required(self):
        from utils.security import PermissionDeniedError
        viewer_id = self._make_staff_and_user("viewer", "viewer_hd3")
        student = self._new_student("مداخله‌حذف", "9200000020")
        profile = self._new_profile(student.id)
        inter = self._new_intervention(profile.id)
        self._login(viewer_id)
        with self.assertRaises(PermissionDeniedError):
            self.intervention_dal.permanent_delete(inter.id)

    def test_blocked_when_followup_exists(self):
        student = self._new_student("مداخله‌حذف۲", "9200000021")
        profile = self._new_profile(student.id)
        inter = self._new_intervention(profile.id)
        self._new_followup(inter.id)
        with self.assertRaises(ValueError):
            self.intervention_dal.permanent_delete(inter.id)
        row = self.db.get_connection().execute(
            "SELECT id FROM interventions WHERE id = ?", (inter.id,)).fetchone()
        self.assertIsNotNone(row)

    def test_succeeds_when_no_followup(self):
        student = self._new_student("مداخله‌حذف۳", "9200000022")
        profile = self._new_profile(student.id)
        inter = self._new_intervention(profile.id)
        self.assertTrue(self.intervention_dal.permanent_delete(inter.id))


class TestFollowUpPermanentDeleteGuards(HardDeleteRestoreTestBase):
    def test_permission_required(self):
        from utils.security import PermissionDeniedError
        viewer_id = self._make_staff_and_user("viewer", "viewer_hd4")
        student = self._new_student("پیگیری‌حذف", "9200000030")
        profile = self._new_profile(student.id)
        inter = self._new_intervention(profile.id)
        followup = self._new_followup(inter.id)
        self._login(viewer_id)
        with self.assertRaises(PermissionDeniedError):
            self.followup_dal.permanent_delete(followup.id)

    def test_succeeds_no_dependents(self):
        student = self._new_student("پیگیری‌حذف۲", "9200000031")
        profile = self._new_profile(student.id)
        inter = self._new_intervention(profile.id)
        followup = self._new_followup(inter.id)
        self.assertTrue(self.followup_dal.permanent_delete(followup.id))


class TestUserAndStaffPermanentDeleteGuards(HardDeleteRestoreTestBase):
    def test_user_permanent_delete_requires_permission(self):
        from utils.security import PermissionDeniedError
        viewer_id = self._make_staff_and_user("viewer", "viewer_hd5")
        victim_id = self._make_staff_and_user("viewer", "victim_hd5")
        from dal.user_dal import UserDAL
        victim_user_row = self.db.get_connection().execute(
            "SELECT id FROM users WHERE staff_id = ?", (victim_id,)).fetchone()
        self._login(viewer_id)
        with self.assertRaises(PermissionDeniedError):
            UserDAL().permanent_delete(victim_user_row["id"])

    def test_staff_permanent_delete_requires_permission(self):
        from utils.security import PermissionDeniedError
        viewer_id = self._make_staff_and_user("viewer", "viewer_hd6")
        clean_staff_id = self._make_staff_and_user("viewer", "clean_hd6")
        # حذفِ منطقی اکانتِ کاربریِ آن تا سابقه‌ای نداشته باشد؟ فقط permission را می‌سنجیم
        self._login(viewer_id)
        with self.assertRaises(PermissionDeniedError):
            self.staff_dal.permanent_delete(clean_staff_id)

    def test_staff_permanent_delete_still_blocks_on_dependency_with_permission(self):
        """گاردِ وابستگیِ قبلی دست‌نخورده مانده؛ فقط Permission اضافه شد"""
        student = self._new_student("کارمند‌سابقه", "9200000040")
        profile = self._new_profile(student.id)
        staff_with_history = self._make_staff_and_user("teacher", "teacher_hd6")
        self._new_observation(profile.id, staff_id=staff_with_history)
        # بافت سیستمی (بدون نشست) → مجاز طبق DD-4، ولی گاردِ وابستگی رد می‌کند
        with self.assertRaises(ValueError):
            self.staff_dal.permanent_delete(staff_with_history)


# ================================================================
# RESTORE-EDGE-01
# ================================================================

class TestObservationRestoreParentCheck(HardDeleteRestoreTestBase):
    def test_blocked_when_parent_profile_deleted(self):
        student = self._new_student("بازیابی‌مشاهده", "9200000050")
        profile = self._new_profile(student.id)
        obs = self._new_observation(profile.id)
        self.observation_dal.delete(obs.id, 1)
        self.profile_dal.delete(profile.id, 1)

        with self.assertRaises(ValueError) as ctx:
            self.observation_dal.restore(obs.id)
        self.assertIn("پرونده", str(ctx.exception))
        # وضعیت هنوز حذف‌شده باقی مانده (بازیابی نیمه‌کاره نشده)
        row = self.db.get_connection().execute(
            "SELECT is_deleted FROM observations WHERE id = ?", (obs.id,)).fetchone()
        self.assertEqual(row["is_deleted"], 1)

    def test_succeeds_when_parent_profile_active(self):
        student = self._new_student("بازیابی‌مشاهده۲", "9200000051")
        profile = self._new_profile(student.id)
        obs = self._new_observation(profile.id)
        self.observation_dal.delete(obs.id, 1)
        self.assertTrue(self.observation_dal.restore(obs.id))


class TestInterventionRestoreParentCheck(HardDeleteRestoreTestBase):
    def test_blocked_when_parent_profile_deleted(self):
        student = self._new_student("بازیابی‌مداخله", "9200000060")
        profile = self._new_profile(student.id)
        inter = self._new_intervention(profile.id)
        self.intervention_dal.delete(inter.id, 1)
        self.profile_dal.delete(profile.id, 1)

        with self.assertRaises(ValueError):
            self.intervention_dal.restore(inter.id)

    def test_succeeds_when_parent_profile_active(self):
        student = self._new_student("بازیابی‌مداخله۲", "9200000061")
        profile = self._new_profile(student.id)
        inter = self._new_intervention(profile.id)
        self.intervention_dal.delete(inter.id, 1)
        self.assertTrue(self.intervention_dal.restore(inter.id))


class TestFollowUpRestoreParentCheck(HardDeleteRestoreTestBase):
    def test_blocked_when_parent_intervention_deleted(self):
        student = self._new_student("بازیابی‌پیگیری", "9200000070")
        profile = self._new_profile(student.id)
        inter = self._new_intervention(profile.id)
        followup = self._new_followup(inter.id)
        self.followup_dal.delete(followup.id, 1)
        self.intervention_dal.delete(inter.id, 1)

        with self.assertRaises(ValueError) as ctx:
            self.followup_dal.restore(followup.id)
        self.assertIn("مداخله", str(ctx.exception))

    def test_succeeds_when_parent_intervention_active(self):
        student = self._new_student("بازیابی‌پیگیری۲", "9200000071")
        profile = self._new_profile(student.id)
        inter = self._new_intervention(profile.id)
        followup = self._new_followup(inter.id)
        self.followup_dal.delete(followup.id, 1)
        self.assertTrue(self.followup_dal.restore(followup.id))


class TestProfileRestoreParentCheck(HardDeleteRestoreTestBase):
    def test_blocked_when_parent_student_deleted(self):
        student = self._new_student("بازیابی‌پرونده", "9200000080")
        profile = self._new_profile(student.id)
        self.profile_dal.delete(profile.id, 1)
        self.student_dal.delete(student.id, 1)

        with self.assertRaises(ValueError) as ctx:
            self.profile_dal.restore(profile.id)
        self.assertIn("دانش‌آموز", str(ctx.exception))

    def test_succeeds_when_parent_student_active(self):
        student = self._new_student("بازیابی‌پرونده۲", "9200000081")
        profile = self._new_profile(student.id)
        self.profile_dal.delete(profile.id, 1)
        self.assertTrue(self.profile_dal.restore(profile.id))


class TestProfilePermissionAndScope(HardDeleteRestoreTestBase):
    """
    یافتهٔ جانبیِ تکمیل‌شده (مرحلهٔ ۸): StudentAcademicProfileDAL.delete/
    restore تا پیش از این هیچ Permission/Scope‌ای نداشتند (کلِ این DAL
    نداشت). چون هیچ Service/UI‌ای این دو متد را صدا نمی‌زد، بدون ریسکِ
    شکستنِ رفتار موجود، همان مجوز/Scope دانش‌آموزِ والد اضافه شد.
    """

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

    def test_delete_requires_permission(self):
        from utils.security import PermissionDeniedError
        viewer_id = self._make_staff_and_user("viewer", "viewer_prof1")
        student = self._new_student("پروندهٔ‌مجوز۱", "9400000001")
        profile = self._new_profile(student.id)
        self._login(viewer_id)
        with self.assertRaises(PermissionDeniedError):
            self.profile_dal.delete(profile.id, viewer_id)

    def test_restore_requires_permission(self):
        from utils.security import PermissionDeniedError
        viewer_id = self._make_staff_and_user("viewer", "viewer_prof2")
        student = self._new_student("پروندهٔ‌مجوز۲", "9400000002")
        profile = self._new_profile(student.id)
        self.profile_dal.delete(profile.id, 1)
        self._login(viewer_id)
        with self.assertRaises(PermissionDeniedError):
            self.profile_dal.restore(profile.id)

    def test_delete_blocked_for_teacher_outside_scope(self):
        from utils.security import PermissionDeniedError
        teacher_id = self._make_staff_and_user("teacher", "teacher_prof1")
        student = self._new_student("پروندهٔ‌اسکوپ۱", "9400000003")
        profile = self._new_profile(student.id)
        # عمداً منتسب نشده به این معلم
        self._login(teacher_id)
        with self.assertRaises(PermissionDeniedError):
            self.profile_dal.delete(profile.id, teacher_id)

    def test_delete_blocked_for_teacher_even_with_scope_assignment(self):
        """
        نکته: TEACHER اصلاً DELETE_STUDENT ندارد (سیاست از‌پیش‌موجودِ
        نقش‌ها، بازرسی BUG-NAV-03) — پس حتی با انتساب صحیح Scope هم رد
        می‌شود؛ Permission زودتر از Scope بررسی می‌شود.
        """
        from utils.security import PermissionDeniedError
        teacher_id = self._make_staff_and_user("teacher", "teacher_prof2")
        student = self._new_student("پروندهٔ‌اسکوپ۲", "9400000004")
        profile = self._new_profile(student.id)
        self._assign_teacher(student.id, teacher_id)
        self._login(teacher_id)
        with self.assertRaises(PermissionDeniedError):
            self.profile_dal.delete(profile.id, teacher_id)

    def test_delete_and_restore_succeed_for_manager(self):
        """مدیر بدون محدودیت Scope است (DD-6)"""
        student = self._new_student("پروندهٔ‌مدیر", "9400000005")
        profile = self._new_profile(student.id)
        self.assertTrue(self.profile_dal.delete(profile.id, 1))
        self.assertTrue(self.profile_dal.restore(profile.id))


class TestAttachmentRestoreParentCheck(HardDeleteRestoreTestBase):
    def setUp(self):
        super().setUp()
        self._tmp_att = tempfile.mkdtemp(prefix="partow_hd_att_")
        self._saved_att_dir = getattr(_settings, "ATTACHMENTS_DIR", None)
        _settings.ATTACHMENTS_DIR = self._tmp_att
        import config.settings as _cfg
        _cfg.ATTACHMENTS_DIR = self._tmp_att
        import dal.attachment_dal as _ad
        _ad.ATTACHMENTS_DIR = self._tmp_att

        from services.attachment_service import AttachmentService
        self.attachment_service = AttachmentService()

    def tearDown(self):
        if self._saved_att_dir is not None:
            _settings.ATTACHMENTS_DIR = self._saved_att_dir
        with contextlib.suppress(Exception):
            import shutil
            shutil.rmtree(self._tmp_att, ignore_errors=True)
        super().tearDown()

    def test_blocked_when_parent_observation_deleted(self):
        from utils.error_handler import ServiceError
        student = self._new_student("پیوست‌والد", "9200000090")
        profile = self._new_profile(student.id)
        obs = self._new_observation(profile.id)
        att = self.attachment_service.upload_attachment(
            "observation", obs.id, b"hello", "f.txt",
            created_by=None, user_id=None)
        self.attachment_service.delete_attachment(att.id)
        self.observation_dal.delete(obs.id, 1)

        with self.assertRaises(ServiceError) as ctx:
            self.attachment_service.restore_attachment(att.id)
        self.assertIn("والد", str(ctx.exception))
        # پیوست باید حذف‌شده بماند
        row = self.db.get_connection().execute(
            "SELECT is_deleted FROM attachments WHERE id = ?", (att.id,)).fetchone()
        self.assertEqual(row["is_deleted"], 1)

    def test_succeeds_when_parent_observation_active(self):
        student = self._new_student("پیوست‌والد۲", "9200000091")
        profile = self._new_profile(student.id)
        obs = self._new_observation(profile.id)
        att = self.attachment_service.upload_attachment(
            "observation", obs.id, b"hello", "f2.txt",
            created_by=None, user_id=None)
        self.attachment_service.delete_attachment(att.id)
        restored = self.attachment_service.restore_attachment(att.id)
        self.assertIsNotNone(restored)
        self.assertEqual(getattr(restored, "is_deleted", 0), 0)


if __name__ == "__main__":
    unittest.main()
