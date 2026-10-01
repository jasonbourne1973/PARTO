"""
آزمون‌های IDOR/Scope در سطح Object — دور نوزدهم، مرحلهٔ ۴

پوشش مأموریت:
  • Observation: همان الگوی مرحلهٔ ۳ (create/get_by_id/update/delete/
    restore با AccessControl.require_profile_scope).
  • Attachment: مرز Scope مستقل از مرز Permission موجود
    (ENTITY_PERMISSION_MAP) روی همهٔ ۷ نوع entity_type شناخته‌شده —
    شامل سه‌ موجودیتی که طبق DD-1 هنوز Permission ندارند.
  • CounselingSession/ExtracurricularActivity/IndividualGoal: طبق
    تصمیم صریح مدیر پروژه (dd1_scope=add_scope_only)، فقط لایهٔ Scope
    اضافه شده — بدون اختراع Permission جدید (DD-1 دست‌نخورده می‌ماند؛
    یعنی نقش‌های بدون Permission خاص هم می‌توانند این موجودیت‌ها را
    بسازند، اما TEACHER محدود به دانش‌آموزهای منتسب خودش است).
  • رد Scope همیشه PermissionDeniedError صریح است، نه NotFound.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jdatetime

from dal.counseling_session_dal import CounselingSessionDAL
from dal.extracurricular_dal import ExtracurricularDAL
from dal.followup_dal import FollowUpDAL
from dal.goal_dal import GoalDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from models.counseling_session import CounselingSession
from models.extracurricular_activity import ExtracurricularActivity
from models.followup import FollowUp
from models.individual_goal import IndividualGoal
from models.intervention import Intervention
from models.observation import Observation
from models.student_academic_profile import StudentAcademicProfile
from services.attachment_service import AttachmentService
from tests.test_scope_boundary import ScopeBoundaryTestBase
from utils.security import (
    ROLE_PERMISSIONS,
    AccessControl,
    Permission,
    PermissionDeniedError,
    UserRole,
)

TODAY = jdatetime.date.today().strftime("%Y/%m/%d")


class Stage4TestBase(ScopeBoundaryTestBase):
    """پایهٔ مشترک: دو پروندهٔ سالانه (منتسب/غیرمنتسب) + رکورد نمونه از هر موجودیت"""

    def setUp(self):
        super().setUp()
        AccessControl.logout()

        year_row = self.db.get_connection().execute(
            "SELECT id FROM academic_years WHERE is_active = 1 AND is_deleted = 0 LIMIT 1"
        ).fetchone()
        self.academic_year_id = year_row["id"]

        self.assigned_profile_id = self._make_profile(self.assigned_student_id)
        self.unassigned_profile_id = self._make_profile(self.unassigned_student_id)

        AccessControl.logout()

    def _make_profile(self, student_id):
        p = StudentAcademicProfile()
        p.student_id = student_id
        p.academic_year_id = self.academic_year_id
        p.grade = 1
        p.class_name = "اول-الف"
        return StudentAcademicProfileDAL().create(p).id

    def _login_teacher_with_assignment(self, username="t_stage4"):
        staff_id = self._login_role("teacher", username)
        self._assign_teacher(staff_id, self.assigned_student_id)
        return staff_id


class TestObservationDALObjectScope(Stage4TestBase):
    """همان الگوی IDOR مرحلهٔ ۳، برای Observation"""

    def _new_observation(self, profile_id):
        o = Observation()
        o.student_profile_id = profile_id
        o.staff_id = 1
        o.observation_date = TODAY
        o.description = "مشاهدهٔ آزمون Scope"
        return o

    def setUp(self):
        super().setUp()
        AccessControl.logout()
        self.assigned_observation = ObservationDAL().create(
            self._new_observation(self.assigned_profile_id))
        self.unassigned_observation = ObservationDAL().create(
            self._new_observation(self.unassigned_profile_id))
        AccessControl.logout()

    def test_teacher_can_create_for_assigned_student(self):
        self._login_teacher_with_assignment()
        created = ObservationDAL().create(self._new_observation(self.assigned_profile_id))
        self.assertIsNotNone(created.id)

    def test_teacher_cannot_create_for_unassigned_student(self):
        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            ObservationDAL().create(self._new_observation(self.unassigned_profile_id))

    def test_teacher_can_read_own_scope_by_id(self):
        self._login_teacher_with_assignment()
        result = ObservationDAL().get_by_id(self.assigned_observation.id)
        self.assertIsNotNone(result)

    def test_teacher_cannot_read_other_scope_by_id_idor(self):
        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            ObservationDAL().get_by_id(self.unassigned_observation.id)

    def test_teacher_can_update_own_scope(self):
        """TEACHER واقعاً EDIT_OBSERVATION دارد؛ این تست با مجوز واقعی اجرا می‌شود."""
        self._login_teacher_with_assignment()
        obs = self.assigned_observation
        obs.description = "ویرایش مجاز"
        ObservationDAL().update(obs)

    def test_teacher_cannot_update_other_scope(self):
        self._login_teacher_with_assignment()
        obs = self.unassigned_observation
        obs.description = "ویرایش غیرمجاز"
        with self.assertRaises(PermissionDeniedError):
            ObservationDAL().update(obs)

    def test_wiring_delete_restore_respect_scope(self):
        """TEACHER امروز DELETE_OBSERVATION ندارد؛ موقتاً برای این تست اعطا می‌شود."""
        original = list(ROLE_PERMISSIONS[UserRole.TEACHER.value])
        ROLE_PERMISSIONS[UserRole.TEACHER.value] = [
            *original, Permission.DELETE_OBSERVATION.value,
        ]
        try:
            teacher_staff_id = self._login_teacher_with_assignment()
            with self.assertRaises(PermissionDeniedError):
                ObservationDAL().delete(self.unassigned_observation.id)
            self.assertTrue(ObservationDAL().delete(self.assigned_observation.id))
            self.assertTrue(ObservationDAL().restore(self.assigned_observation.id))

            # حذف رکورد خارج از Scope در بافت سیستمی، تا در حالت «حذف‌شده»
            # قرار بگیرد و بشود رد Scope روی «بازیابی» را هم جدا سنجید
            # (خودِ حذف با نشست TEACHER بالا رد شد و رکورد دست‌نخورده ماند).
            AccessControl.logout()
            self.assertTrue(ObservationDAL().delete(self.unassigned_observation.id))
            AccessControl.login(teacher_staff_id, None)
            with self.assertRaises(PermissionDeniedError):
                ObservationDAL().restore(self.unassigned_observation.id)
        finally:
            ROLE_PERMISSIONS[UserRole.TEACHER.value] = original

    def test_manager_unrestricted(self):
        self._login_staff(self._users["staff_id"])
        result = ObservationDAL().get_by_id(self.unassigned_observation.id)
        self.assertIsNotNone(result)


class TestScopeOnlyEntities(Stage4TestBase):
    """
    CounselingSession/ExtracurricularActivity/IndividualGoal: طبق DD-1
    هیچ Permission‌ای ندارند (هر کاربر واردشده‌ای می‌تواند بسازد)؛ طبق
    تصمیم dd1_scope=add_scope_only، فقط Scope اعمال می‌شود.
    """

    def _new_session(self, profile_id):
        s = CounselingSession()
        s.student_profile_id = profile_id
        s.counselor_id = 1
        s.session_date = TODAY
        s.type = CounselingSession.TYPE_INDIVIDUAL
        return s

    def _new_activity(self, profile_id):
        a = ExtracurricularActivity()
        a.student_profile_id = profile_id
        a.title = "فعالیت آزمون"
        a.type = ExtracurricularActivity.TYPE_SPORT
        a.start_date = TODAY
        return a

    def _new_goal(self, profile_id):
        g = IndividualGoal()
        g.student_profile_id = profile_id
        g.title = "هدف آزمون"
        return g

    def setUp(self):
        super().setUp()
        AccessControl.logout()
        self.assigned_session = CounselingSessionDAL().create(
            self._new_session(self.assigned_profile_id))
        self.unassigned_session = CounselingSessionDAL().create(
            self._new_session(self.unassigned_profile_id))
        self.assigned_activity = ExtracurricularDAL().create(
            self._new_activity(self.assigned_profile_id))
        self.unassigned_activity = ExtracurricularDAL().create(
            self._new_activity(self.unassigned_profile_id))
        self.assigned_goal = GoalDAL().create(self._new_goal(self.assigned_profile_id))
        self.unassigned_goal = GoalDAL().create(self._new_goal(self.unassigned_profile_id))
        AccessControl.logout()

    def test_teacher_without_any_special_permission_can_touch_assigned(self):
        """نکتهٔ کلیدی DD-1: TEACHER هیچ Permission خاصی برای این سه ندارد، ولی رد نمی‌شود."""
        self._login_teacher_with_assignment()
        self.assertIsNotNone(
            CounselingSessionDAL().create(self._new_session(self.assigned_profile_id)))
        self.assertIsNotNone(
            ExtracurricularDAL().create(self._new_activity(self.assigned_profile_id)))
        self.assertIsNotNone(GoalDAL().create(self._new_goal(self.assigned_profile_id)))

    def test_teacher_cannot_create_for_unassigned_student(self):
        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            CounselingSessionDAL().create(self._new_session(self.unassigned_profile_id))
        with self.assertRaises(PermissionDeniedError):
            ExtracurricularDAL().create(self._new_activity(self.unassigned_profile_id))
        with self.assertRaises(PermissionDeniedError):
            GoalDAL().create(self._new_goal(self.unassigned_profile_id))

    def test_idor_get_by_id_blocked_for_all_three(self):
        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            CounselingSessionDAL().get_by_id(self.unassigned_session.id)
        with self.assertRaises(PermissionDeniedError):
            ExtracurricularDAL().get_by_id(self.unassigned_activity.id)
        with self.assertRaises(PermissionDeniedError):
            GoalDAL().get_by_id(self.unassigned_goal.id)

    def test_get_by_id_allowed_for_assigned(self):
        self._login_teacher_with_assignment()
        self.assertIsNotNone(CounselingSessionDAL().get_by_id(self.assigned_session.id))
        self.assertIsNotNone(ExtracurricularDAL().get_by_id(self.assigned_activity.id))
        self.assertIsNotNone(GoalDAL().get_by_id(self.assigned_goal.id))

    def test_update_delete_restore_respect_scope(self):
        teacher_staff_id = self._login_teacher_with_assignment()

        self.assigned_session.summary = "خلاصهٔ مجاز"
        CounselingSessionDAL().update(self.assigned_session)
        with self.assertRaises(PermissionDeniedError):
            self.unassigned_session.summary = "خلاصهٔ غیرمجاز"
            CounselingSessionDAL().update(self.unassigned_session)

        self.assertTrue(CounselingSessionDAL().delete(self.assigned_session.id))
        with self.assertRaises(PermissionDeniedError):
            CounselingSessionDAL().delete(self.unassigned_session.id)
        self.assertTrue(CounselingSessionDAL().restore(self.assigned_session.id))

        self.assertTrue(ExtracurricularDAL().delete(self.assigned_activity.id))
        with self.assertRaises(PermissionDeniedError):
            ExtracurricularDAL().delete(self.unassigned_activity.id)

        self.assertTrue(GoalDAL().delete(self.assigned_goal.id))
        with self.assertRaises(PermissionDeniedError):
            GoalDAL().delete(self.unassigned_goal.id)

        # حذف رکوردهای خارج از Scope در بافت سیستمی (چون تلاش TEACHER در
        # بالا رد شد و رکورد واقعاً حذف نشد) تا بشود رد Scope روی خودِ
        # «بازیابی» را هم جدا سنجید.
        AccessControl.logout()
        self.assertTrue(CounselingSessionDAL().delete(self.unassigned_session.id))
        AccessControl.login(teacher_staff_id, None)
        with self.assertRaises(PermissionDeniedError):
            CounselingSessionDAL().restore(self.unassigned_session.id)

    def test_manager_unrestricted_for_all_three(self):
        self._login_staff(self._users["staff_id"])
        self.assertIsNotNone(CounselingSessionDAL().get_by_id(self.unassigned_session.id))
        self.assertIsNotNone(ExtracurricularDAL().get_by_id(self.unassigned_activity.id))
        self.assertIsNotNone(GoalDAL().get_by_id(self.unassigned_goal.id))


class TestAttachmentServiceScope(Stage4TestBase):
    """مرز Scope مستقل روی Attachment، برای هر ۷ نوع entity_type"""

    def setUp(self):
        super().setUp()
        AccessControl.logout()

        # ایزوله‌سازی پوشهٔ پیوست‌ها (مثل TestAttachmentPermissionBoundary
        # در test_permission_boundary.py) — بدون این کار فایل واقعی روی
        # دیسک مخزن نوشته می‌شود.
        import dal.attachment_dal as _att_dal_mod
        import services.attachment_service as _att_svc_mod
        self._saved_att_dirs = (_att_dal_mod.ATTACHMENTS_DIR, _att_svc_mod.ATTACHMENTS_DIR)
        att_dir = os.path.join(self._tmpdir, "attachments")
        os.makedirs(att_dir, exist_ok=True)
        _att_dal_mod.ATTACHMENTS_DIR = att_dir
        _att_svc_mod.ATTACHMENTS_DIR = att_dir

        self.assigned_intervention = InterventionDAL().create(self._new_intervention(
            self.assigned_profile_id))
        self.unassigned_intervention = InterventionDAL().create(self._new_intervention(
            self.unassigned_profile_id))
        self.assigned_followup = FollowUpDAL().create(
            self._new_followup(self.assigned_intervention.id))
        self.unassigned_followup = FollowUpDAL().create(
            self._new_followup(self.unassigned_intervention.id))

        self.svc = AttachmentService()
        AccessControl.logout()

    def tearDown(self):
        import dal.attachment_dal as _att_dal_mod
        import services.attachment_service as _att_svc_mod
        _att_dal_mod.ATTACHMENTS_DIR, _att_svc_mod.ATTACHMENTS_DIR = self._saved_att_dirs
        super().tearDown()

    def _new_intervention(self, profile_id):
        i = Intervention()
        i.student_profile_id = profile_id
        i.staff_id = 1
        i.type = "گفتگوی فردی"
        i.date = TODAY
        i.description = "مداخلهٔ آزمون پیوست"
        return i

    def _new_followup(self, intervention_id):
        f = FollowUp()
        f.intervention_id = intervention_id
        f.staff_id = 1
        f.date = TODAY
        f.description = "پیگیری آزمون پیوست"
        return f

    def test_upload_to_own_scope_student_succeeds(self):
        self._login_teacher_with_assignment()
        att = self.svc.upload_attachment(
            'student', self.assigned_student_id, b'x', 'a.txt', created_by=1)
        self.assertIsNotNone(att.id)

    def test_upload_to_other_scope_student_blocked_idor(self):
        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            self.svc.upload_attachment(
                'student', self.unassigned_student_id, b'x', 'a.txt', created_by=1)

    def test_get_attachments_by_entity_blocked_for_out_of_scope_intervention(self):
        """
        TEACHER فقط VIEW_INTERVENTIONS دارد (نه EDIT) — پس مسیر 'view'
        در پیوست مداخله در دسترس است و برای بررسی Scope مناسب است.
        """
        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            self.svc.get_attachments_by_entity('intervention', self.unassigned_intervention.id)
        # ولی برای مداخلهٔ خودش مجاز است (لیست خالی برمی‌گردد، استثنا نه)
        result = self.svc.get_attachments_by_entity('intervention', self.assigned_intervention.id)
        self.assertEqual(result, [])

    def test_get_attachments_by_entity_blocked_for_out_of_scope_followup(self):
        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            self.svc.get_attachments_by_entity('followup', self.unassigned_followup.id)
        result = self.svc.get_attachments_by_entity('followup', self.assigned_followup.id)
        self.assertEqual(result, [])

    def test_get_attachments_by_entity_blocked_for_out_of_scope_observation(self):
        AccessControl.logout()
        obs_a = ObservationDAL().create(self._new_observation(self.assigned_profile_id))
        obs_b = ObservationDAL().create(self._new_observation(self.unassigned_profile_id))
        AccessControl.logout()

        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            self.svc.get_attachments_by_entity('observation', obs_b.id)
        result = self.svc.get_attachments_by_entity('observation', obs_a.id)
        self.assertEqual(result, [])

    def _new_observation(self, profile_id):
        o = Observation()
        o.student_profile_id = profile_id
        o.staff_id = 1
        o.observation_date = TODAY
        o.description = "مشاهدهٔ آزمون پیوست"
        return o

    def test_get_attachments_by_entity_scope_for_dd1_entities(self):
        """
        counseling_session/extracurricular_activity/individual_goal:
        طبق DD-1 مسیر 'view' اصلاً Permission‌ای ندارد (ENTITY_PERMISSION_MAP
        این‌ها را ندارد) — پس تنها گیت باقی‌مانده، Scope است.
        """
        AccessControl.logout()
        session_a = CounselingSessionDAL().create(self._new_session(self.assigned_profile_id))
        session_b = CounselingSessionDAL().create(self._new_session(self.unassigned_profile_id))
        activity_a = ExtracurricularDAL().create(self._new_activity(self.assigned_profile_id))
        activity_b = ExtracurricularDAL().create(self._new_activity(self.unassigned_profile_id))
        goal_a = GoalDAL().create(self._new_goal(self.assigned_profile_id))
        goal_b = GoalDAL().create(self._new_goal(self.unassigned_profile_id))
        AccessControl.logout()

        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            self.svc.get_attachments_by_entity('counseling_session', session_b.id)
        self.assertEqual(
            self.svc.get_attachments_by_entity('counseling_session', session_a.id), [])

        with self.assertRaises(PermissionDeniedError):
            self.svc.get_attachments_by_entity('extracurricular_activity', activity_b.id)
        self.assertEqual(
            self.svc.get_attachments_by_entity('extracurricular_activity', activity_a.id), [])

        with self.assertRaises(PermissionDeniedError):
            self.svc.get_attachments_by_entity('individual_goal', goal_b.id)
        self.assertEqual(
            self.svc.get_attachments_by_entity('individual_goal', goal_a.id), [])

    def _new_session(self, profile_id):
        s = CounselingSession()
        s.student_profile_id = profile_id
        s.counselor_id = 1
        s.session_date = TODAY
        s.type = CounselingSession.TYPE_INDIVIDUAL
        return s

    def _new_activity(self, profile_id):
        a = ExtracurricularActivity()
        a.student_profile_id = profile_id
        a.title = "فعالیت آزمون پیوست"
        a.type = ExtracurricularActivity.TYPE_SPORT
        a.start_date = TODAY
        return a

    def _new_goal(self, profile_id):
        g = IndividualGoal()
        g.student_profile_id = profile_id
        g.title = "هدف آزمون پیوست"
        return g

    def test_manager_unrestricted_for_attachment_scope(self):
        self._login_staff(self._users["staff_id"])
        result = self.svc.get_attachments_by_entity(
            'intervention', self.unassigned_intervention.id)
        self.assertEqual(result, [])

    def test_get_attachment_by_id_idor(self):
        """خواندن مستقیم یک پیوست با ID: هستهٔ IDOR در سطح Attachment."""
        AccessControl.logout()
        att = self.svc.upload_attachment(
            'intervention', self.unassigned_intervention.id, b'x', 'a.txt', created_by=1)
        AccessControl.logout()

        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            self.svc.get_attachment(att.id)


if __name__ == "__main__":
    unittest.main()
