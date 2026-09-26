"""
آزمون‌های IDOR/Scope در سطح Object برای Intervention و FollowUp
دور نوزدهم — مرحلهٔ ۳ (طبق docs/tech_audit_19_fa.md و DD-6)

پوشش مأموریت:
  • زنجیرهٔ Intervention→Profile→Student→Scope و
    FollowUp→Intervention→Profile→Student→Scope در
    utils.security.AccessControl (resolverهای _student_id_from_profile،
    _profile_id_from_intervention، _intervention_id_from_followup و
    has/require_profile_scope، has/require_intervention_scope،
    has/require_followup_scope) — به‌صورت مستقل از DAL.
  • سیم‌کشی واقعی در InterventionDAL.create/get_by_id و
    FollowUpDAL.create/get_by_id با نقش TEACHER واقعی (این دو DAL و دو
    عملیات، تنها مسیرهایی هستند که TEACHER امروز واقعاً مجوز آن‌ها را
    دارد؛ TEACHER به‌طور پیش‌فرض EDIT_INTERVENTION/DELETE_INTERVENTION/
    EDIT_FOLLOWUP/DELETE_FOLLOWUP را ندارد — این یک یافتهٔ پیش‌موجود
    است، نه محصول این مرحله؛ رجوع کنید به گزارش پایانی مرحلهٔ ۳).
  • سیم‌کشی update/delete/restore در هر دو DAL: چون امروز TEACHER این
    مجوزها را ندارد، این تست‌ها موقتاً (فقط در طول خودشان) این مجوزها
    را به TEACHER اعطا می‌کنند تا مشخص شود لایهٔ Scope --- جدا از لایهٔ
    Permission --- به‌درستی سیم‌کشی شده است (دفاع در عمق / آماده برای
    تغییر سیاست مجوز در آینده).
  • FollowUp نمی‌تواند به مداخلهٔ خارج از Scope وصل شود (Cross-resource).
  • رد Scope همیشه PermissionDeniedError صریح است، نه NotFound.
  • نقش‌های غیرمحدود (MANAGER و ...) طبق DD-6 هیچ محدودیتی ندارند.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jdatetime

from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from models.followup import FollowUp
from models.intervention import Intervention
from models.student_academic_profile import StudentAcademicProfile
from tests.test_scope_boundary import ScopeBoundaryTestBase
from utils.security import (
    ROLE_PERMISSIONS,
    AccessControl,
    Permission,
    PermissionDeniedError,
    UserRole,
)

TODAY = jdatetime.date.today().strftime("%Y/%m/%d")


class InterventionFollowUpScopeTestBase(ScopeBoundaryTestBase):
    """
    پایه: دو پروندهٔ سالانه (برای دانش‌آموز منتسب/غیرمنتسب) به‌همراه یک
    مداخله و پیگیریِ ازپیش‌ساخته روی هر کدام، در بافت سیستمی.
    """

    def setUp(self):
        super().setUp()
        AccessControl.logout()

        year_row = self.db.get_connection().execute(
            "SELECT id FROM academic_years WHERE is_active = 1 AND is_deleted = 0 LIMIT 1"
        ).fetchone()
        self.academic_year_id = year_row["id"]

        self.assigned_profile_id = self._make_profile(self.assigned_student_id)
        self.unassigned_profile_id = self._make_profile(self.unassigned_student_id)

        self.assigned_intervention = self._make_intervention(self.assigned_profile_id)
        self.unassigned_intervention = self._make_intervention(self.unassigned_profile_id)

        self.assigned_followup = self._make_followup(self.assigned_intervention.id)
        self.unassigned_followup = self._make_followup(self.unassigned_intervention.id)

        AccessControl.logout()

    def _make_profile(self, student_id):
        p = StudentAcademicProfile()
        p.student_id = student_id
        p.academic_year_id = self.academic_year_id
        p.grade = 1
        p.class_name = "اول-الف"
        return StudentAcademicProfileDAL().create(p).id

    def _make_intervention(self, profile_id):
        i = Intervention()
        i.student_profile_id = profile_id
        i.staff_id = 1
        i.type = "گفتگوی فردی"
        i.date = TODAY
        i.description = "مداخلهٔ آزمون Scope"
        return InterventionDAL().create(i)

    def _make_followup(self, intervention_id):
        f = FollowUp()
        f.intervention_id = intervention_id
        f.staff_id = 1
        f.date = TODAY
        f.description = "پیگیری آزمون Scope"
        return FollowUpDAL().create(f)

    def _login_teacher_with_assignment(self, username="t_iof"):
        staff_id = self._login_role("teacher", username)
        self._assign_teacher(staff_id, self.assigned_student_id)
        return staff_id


class TestResolverChain(InterventionFollowUpScopeTestBase):
    """resolverهای زنجیره، مستقل از DAL"""

    def test_profile_resolves_to_student(self):
        self.assertEqual(
            AccessControl._student_id_from_profile(self.assigned_profile_id),
            self.assigned_student_id,
        )

    def test_intervention_resolves_to_profile(self):
        self.assertEqual(
            AccessControl._profile_id_from_intervention(self.assigned_intervention.id),
            self.assigned_profile_id,
        )

    def test_followup_resolves_to_intervention(self):
        self.assertEqual(
            AccessControl._intervention_id_from_followup(self.assigned_followup.id),
            self.assigned_intervention.id,
        )

    def test_resolvers_return_none_for_missing_id(self):
        self.assertIsNone(AccessControl._student_id_from_profile(999999))
        self.assertIsNone(AccessControl._profile_id_from_intervention(999999))
        self.assertIsNone(AccessControl._intervention_id_from_followup(999999))

    def test_teacher_has_profile_scope_only_for_assigned(self):
        self._login_teacher_with_assignment()
        self.assertTrue(AccessControl.has_profile_scope(self.assigned_profile_id))
        self.assertFalse(AccessControl.has_profile_scope(self.unassigned_profile_id))

    def test_teacher_has_intervention_scope_only_for_assigned(self):
        self._login_teacher_with_assignment()
        self.assertTrue(
            AccessControl.has_intervention_scope(self.assigned_intervention.id))
        self.assertFalse(
            AccessControl.has_intervention_scope(self.unassigned_intervention.id))

    def test_teacher_has_followup_scope_only_for_assigned(self):
        self._login_teacher_with_assignment()
        self.assertTrue(AccessControl.has_followup_scope(self.assigned_followup.id))
        self.assertFalse(AccessControl.has_followup_scope(self.unassigned_followup.id))

    def test_require_intervention_scope_raises_for_unassigned(self):
        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            AccessControl.require_intervention_scope(self.unassigned_intervention.id)

    def test_require_followup_scope_raises_for_unassigned(self):
        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            AccessControl.require_followup_scope(self.unassigned_followup.id)

    def test_manager_unrestricted_for_profile_intervention_followup(self):
        """طبق DD-6: MANAGER هیچ محدودیت Scope‌ای ندارد."""
        self._login_staff(self._users["staff_id"])
        self.assertTrue(AccessControl.has_profile_scope(self.unassigned_profile_id))
        self.assertTrue(
            AccessControl.has_intervention_scope(self.unassigned_intervention.id))
        self.assertTrue(AccessControl.has_followup_scope(self.unassigned_followup.id))


class TestInterventionDALObjectScope(InterventionFollowUpScopeTestBase):
    """سیم‌کشی واقعی IDOR در InterventionDAL"""

    def test_teacher_can_create_intervention_for_assigned_student(self):
        self._login_teacher_with_assignment()
        i = Intervention()
        i.student_profile_id = self.assigned_profile_id
        i.staff_id = 1
        i.type = "گفتگوی فردی"
        i.date = TODAY
        i.description = "مداخلهٔ جدید در Scope"
        created = InterventionDAL().create(i)
        self.assertIsNotNone(created.id)

    def test_teacher_cannot_create_intervention_for_unassigned_student(self):
        self._login_teacher_with_assignment()
        i = Intervention()
        i.student_profile_id = self.unassigned_profile_id
        i.staff_id = 1
        i.type = "گفتگوی فردی"
        i.date = TODAY
        i.description = "مداخلهٔ خارج از Scope"
        with self.assertRaises(PermissionDeniedError):
            InterventionDAL().create(i)

    def test_teacher_can_read_own_scope_intervention_by_id(self):
        self._login_teacher_with_assignment()
        result = InterventionDAL().get_by_id(self.assigned_intervention.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.assigned_intervention.id)

    def test_teacher_cannot_read_other_scope_intervention_by_id_idor(self):
        """هستهٔ رفع IDOR: خواندن مستقیم با شناسهٔ خارج از Scope باید رد شود."""
        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            InterventionDAL().get_by_id(self.unassigned_intervention.id)

    def test_manager_can_read_any_intervention_by_id(self):
        self._login_staff(self._users["staff_id"])
        result = InterventionDAL().get_by_id(self.unassigned_intervention.id)
        self.assertIsNotNone(result)

    def test_no_session_bypasses_scope_on_get_by_id(self):
        """بافت بدون نشست (DD-4): مثلاً کارهای پس‌زمینه/سیستمی."""
        AccessControl.logout()
        result = InterventionDAL().get_by_id(self.unassigned_intervention.id)
        self.assertIsNotNone(result)

    def test_wiring_update_delete_restore_respect_scope(self):
        """
        بررسی صرفاً لایهٔ Scope در update/delete/restore.

        TEACHER امروز اصلاً EDIT_INTERVENTION/DELETE_INTERVENTION ندارد
        (یافتهٔ پیش‌موجود)، بنابراین این تست موقتاً این دو مجوز را به
        TEACHER اعطا می‌کند — فقط برای طول عمر همین تست — تا سیم‌کشی
        Scope در این سه متد (که ورای لایهٔ Permission است) راستی‌آزمایی
        شود.
        """
        original = list(ROLE_PERMISSIONS[UserRole.TEACHER.value])
        ROLE_PERMISSIONS[UserRole.TEACHER.value] = [
            *original,
            Permission.EDIT_INTERVENTION.value,
            Permission.DELETE_INTERVENTION.value,
        ]
        try:
            self._login_teacher_with_assignment()

            # ویرایش رکورد خارج از Scope باید رد شود
            with self.assertRaises(PermissionDeniedError):
                victim = self.unassigned_intervention
                victim.description = "دستکاری غیرمجاز"
                InterventionDAL().update(victim)

            # ویرایش رکورد داخل Scope باید موفق شود
            mine = self.assigned_intervention
            mine.description = "ویرایش مجاز"
            InterventionDAL().update(mine)

            # حذف رکورد خارج از Scope باید رد شود
            with self.assertRaises(PermissionDeniedError):
                InterventionDAL().delete(self.unassigned_intervention.id, user_id=None)

            # حذف رکورد داخل Scope باید موفق شود
            self.assertTrue(
                InterventionDAL().delete(self.assigned_intervention.id, user_id=None))

            # بازیابی رکورد داخل Scope که الان حذف شده، باید موفق شود
            self.assertTrue(
                InterventionDAL().restore(self.assigned_intervention.id))
        finally:
            ROLE_PERMISSIONS[UserRole.TEACHER.value] = original

    def test_wiring_restore_of_unassigned_record_rejected(self):
        """رکورد خارج از Scope حتی وقتی حذف شده هم قابل بازیابی توسط این معلم نیست."""
        original = list(ROLE_PERMISSIONS[UserRole.TEACHER.value])
        ROLE_PERMISSIONS[UserRole.TEACHER.value] = [
            *original,
            Permission.DELETE_INTERVENTION.value,
        ]
        try:
            # حذف رکورد خارج از Scope در بافت سیستمی (بدون نشست)
            AccessControl.logout()
            InterventionDAL().delete(self.unassigned_intervention.id, user_id=None)

            self._login_teacher_with_assignment()
            with self.assertRaises(PermissionDeniedError):
                InterventionDAL().restore(self.unassigned_intervention.id)
        finally:
            ROLE_PERMISSIONS[UserRole.TEACHER.value] = original


class TestFollowUpDALObjectScope(InterventionFollowUpScopeTestBase):
    """سیم‌کشی واقعی IDOR و Cross-resource در FollowUpDAL"""

    def test_teacher_can_create_followup_on_assigned_intervention(self):
        self._login_teacher_with_assignment()
        f = FollowUp()
        f.intervention_id = self.assigned_intervention.id
        f.staff_id = 1
        f.date = TODAY
        f.description = "پیگیری جدید در Scope"
        created = FollowUpDAL().create(f)
        self.assertIsNotNone(created.id)

    def test_teacher_cannot_create_followup_on_unassigned_intervention_cross_resource(self):
        """
        Cross-resource: نباید بشود روی مداخلهٔ خارج از Scope، با دانستن
        صرفِ intervention_id، پیگیری ساخت.
        """
        self._login_teacher_with_assignment()
        f = FollowUp()
        f.intervention_id = self.unassigned_intervention.id
        f.staff_id = 1
        f.date = TODAY
        f.description = "پیگیری غیرمجاز"
        with self.assertRaises(PermissionDeniedError):
            FollowUpDAL().create(f)

    def test_teacher_can_read_own_scope_followup_by_id(self):
        self._login_teacher_with_assignment()
        result = FollowUpDAL().get_by_id(self.assigned_followup.id)
        self.assertIsNotNone(result)

    def test_teacher_cannot_read_other_scope_followup_by_id_idor(self):
        self._login_teacher_with_assignment()
        with self.assertRaises(PermissionDeniedError):
            FollowUpDAL().get_by_id(self.unassigned_followup.id)

    def test_manager_can_read_any_followup_by_id(self):
        self._login_staff(self._users["staff_id"])
        result = FollowUpDAL().get_by_id(self.unassigned_followup.id)
        self.assertIsNotNone(result)

    def test_wiring_update_delete_restore_respect_scope(self):
        original = list(ROLE_PERMISSIONS[UserRole.TEACHER.value])
        ROLE_PERMISSIONS[UserRole.TEACHER.value] = [
            *original,
            Permission.EDIT_FOLLOWUP.value,
            Permission.DELETE_FOLLOWUP.value,
        ]
        try:
            self._login_teacher_with_assignment()

            with self.assertRaises(PermissionDeniedError):
                victim = self.unassigned_followup
                victim.description = "دستکاری غیرمجاز"
                FollowUpDAL().update(victim)

            mine = self.assigned_followup
            mine.description = "ویرایش مجاز"
            FollowUpDAL().update(mine)

            with self.assertRaises(PermissionDeniedError):
                FollowUpDAL().delete(self.unassigned_followup.id, user_id=None)

            self.assertTrue(FollowUpDAL().delete(self.assigned_followup.id, user_id=None))
            self.assertTrue(FollowUpDAL().restore(self.assigned_followup.id))
        finally:
            ROLE_PERMISSIONS[UserRole.TEACHER.value] = original


if __name__ == "__main__":
    unittest.main()
