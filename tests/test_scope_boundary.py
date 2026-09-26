"""
آزمون‌های زیرساخت مشترک Scope/IDOR — دور نوزدهم، مرحلهٔ ۲ (DD-6)

پوشش مأموریت:
  • مدل Scope دقیقاً طبق DD-6: فقط نقش TEACHER محدود به دانش‌آموزهایی
    است که در `teacher_assignments` با staff_id=او و is_active=1 و
    is_deleted=0 منتسب شده‌اند؛ همهٔ نقش‌های دیگر (MANAGER/COUNSELOR/
    VICE_PRINCIPAL/VICE_EDUCATION/SPORT_COACH/QURAN_COACH/ART_COACH/
    VIEWER/OTHER/SYSTEM) بدون محدودیت Scope هستند.
  • انتساب غیرفعال (is_active=0) یا حذف‌شده (is_deleted=1) هم‌ارز
    «بدون انتساب» است — نباید دسترسی بدهد.
  • رد Scope همیشه PermissionDeniedError صریح است (نه NotFound/فهرست
    خالی) و در Audit Log با action='permission_denied' ثبت می‌شود.
  • بافت بدون نشست (اسکریپت/سیستم، DD-4) و student_id=None هر دو مجاز
    باقی می‌مانند (سازگار با قرارداد has_permission).

این فایل فقط زیرساخت (`AccessControl.has_student_scope` /
`require_student_scope`) را می‌سنجد، مستقل از هر Entity خاص — نگاشت
Observation/Intervention/FollowUp/Attachment به student_id در مراحل
بعدی (۳ و ۴) با تست‌های اختصاصی خودشان می‌آید.
"""

import contextlib
import os
import sys
import unittest
from typing import ClassVar

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_permission_boundary import PermissionBoundaryTestBase
from utils.security import AccessControl, PermissionDeniedError, UserRole


class ScopeBoundaryTestBase(PermissionBoundaryTestBase):
    """پایهٔ مشترک: دو دانش‌آموز (منتسب/غیرمنتسب) برای هر تست"""

    def setUp(self):
        super().setUp()
        from dal.student_dal import StudentDAL
        from models.student import Student

        AccessControl.logout()
        s1 = Student()
        s1.first_name = "دانش‌آموز"
        s1.last_name = "منتسب"
        s1.national_code = "1111111101"
        self.assigned_student_id = StudentDAL().create(s1).id

        s2 = Student()
        s2.first_name = "دانش‌آموز"
        s2.last_name = "غیرمنتسب"
        s2.national_code = "1111111102"
        self.unassigned_student_id = StudentDAL().create(s2).id

    def _assign_teacher(self, staff_id, student_id, is_active=1, is_deleted=0):
        conn = self.db.get_connection()
        conn.execute(
            """
            INSERT INTO teacher_assignments
                (student_id, staff_id, academic_year_id, is_active, is_deleted)
            VALUES (?, ?, 1, ?, ?)
            """,
            (student_id, staff_id, is_active, is_deleted),
        )
        conn.commit()

    def _login_role(self, role, username):
        """
        ساخت staff+user با نقش دلخواه و ورود با آن

        نکته: برای نقش‌های مربی (sport_coach/quran_coach/art_coach) و
        «سایر» (other) از INSERT مستقیم SQL استفاده می‌شود، نه
        UserDAL().create()/models.User.validate(). چون
        `models/enums.py::UserRole` (که آن اعتبارسنجی از آن می‌خواند)
        این نقش‌ها را ندارد، در حالی‌که `utils/security.py::UserRole` و
        `ROLE_PERMISSIONS` آن‌ها را به‌عنوان نقش معتبر کاربر می‌شناسند
        (ناسازگاری پیش‌موجود و خارج از دامنهٔ مرحلهٔ ۲؛ در گزارش پایانی
        گزارش می‌شود). این تست فقط منطق AccessControl را می‌سنجد که
        مستقیماً از ستون `users.role` در دیتابیس می‌خواند، نه از مسیر
        اعتبارسنجی مدل.
        """
        from dal.staff_dal import StaffDAL
        from models.staff import Staff

        saved = self.ac.current_staff_id()
        self.ac.logout()
        try:
            staff = Staff()
            staff.full_name = f"آزمون {role}"
            staff.role = "other"
            staff_id = StaffDAL().create(staff).id

            conn = self.db.get_connection()
            conn.execute(
                """
                INSERT INTO users (staff_id, username, password_hash, role, is_active)
                VALUES (?, ?, 'x', ?, 1)
                """,
                (staff_id, username, role),
            )
            conn.commit()
        finally:
            if saved is not None:
                self.ac.login(saved, None)
        self.ac.login(staff_id, None)
        return staff_id


class TestTeacherScopeRestricted(ScopeBoundaryTestBase):
    """طبق DD-6: فقط TEACHER محدود به انتساب فعال است"""

    def test_teacher_has_scope_for_assigned_student(self):
        staff_id = self._login_role("teacher", "t_scope_1")
        self._assign_teacher(staff_id, self.assigned_student_id)
        self.assertTrue(self.ac.has_student_scope(self.assigned_student_id))

    def test_teacher_has_no_scope_for_unassigned_student(self):
        staff_id = self._login_role("teacher", "t_scope_2")
        self._assign_teacher(staff_id, self.assigned_student_id)
        self.assertFalse(self.ac.has_student_scope(self.unassigned_student_id))

    def test_require_student_scope_raises_for_unassigned(self):
        staff_id = self._login_role("teacher", "t_scope_3")
        self._assign_teacher(staff_id, self.assigned_student_id)
        with self.assertRaises(PermissionDeniedError):
            self.ac.require_student_scope(
                self.unassigned_student_id, action="test_case")

    def test_inactive_assignment_does_not_grant_scope(self):
        """انتساب با is_active=0 هم‌ارز «بدون انتساب» است"""
        staff_id = self._login_role("teacher", "t_scope_4")
        self._assign_teacher(staff_id, self.unassigned_student_id, is_active=0)
        self.assertFalse(self.ac.has_student_scope(self.unassigned_student_id))

    def test_deleted_assignment_does_not_grant_scope(self):
        """انتساب soft-delete شده هم‌ارز «بدون انتساب» است"""
        staff_id = self._login_role("teacher", "t_scope_5")
        self._assign_teacher(
            staff_id, self.unassigned_student_id, is_active=1, is_deleted=1)
        self.assertFalse(self.ac.has_student_scope(self.unassigned_student_id))

    def test_scope_denial_is_audited(self):
        staff_id = self._login_role("teacher", "t_scope_6")
        with contextlib.suppress(PermissionDeniedError):
            self.ac.require_student_scope(
                self.unassigned_student_id, action="audit_probe")
        conn = self.db.get_connection()
        row = conn.execute(
            """
            SELECT * FROM audit_logs
            WHERE user_id = ? AND action = 'permission_denied'
              AND entity_type = 'scope'
            ORDER BY id DESC LIMIT 1
            """,
            (staff_id,),
        ).fetchone()
        self.assertIsNotNone(row, "رد Scope باید در Audit Log ثبت شود")


class TestUnrestrictedRolesIgnoreScope(ScopeBoundaryTestBase):
    """طبق DD-6: این نقش‌ها بدون محدودیت Scope‌اند — انتساب اثری ندارد"""

    UNRESTRICTED_ROLES: ClassVar[list[str]] = [
        "manager", "vice_principal", "vice_education", "counselor",
        "sport_coach", "quran_coach", "art_coach", "viewer", "other",
    ]

    def test_unrestricted_roles_have_scope_for_unassigned_student(self):
        for i, role in enumerate(self.UNRESTRICTED_ROLES):
            with self.subTest(role=role):
                self._login_role(role, f"u_scope_{i}")
                self.assertTrue(
                    self.ac.has_student_scope(self.unassigned_student_id),
                    f"نقش «{role}» طبق DD-6 نباید محدود به Scope باشد",
                )
                self.ac.logout()

    def test_manager_require_student_scope_does_not_raise(self):
        self._login_role("manager", "u_scope_mgr")
        self.assertTrue(
            self.ac.require_student_scope(self.unassigned_student_id))


class TestScopeEdgeCases(ScopeBoundaryTestBase):
    """بافت بدون نشست و student_id=None — قرارداد هم‌سو با has_permission"""

    def test_no_session_system_context_has_scope(self):
        self.assertFalse(self.ac.has_session())
        self.assertTrue(self.ac.has_student_scope(self.unassigned_student_id))

    def test_none_student_id_has_scope(self):
        """داشتنِ Scope وقتی هنوز موجودیتی برای محدودکردن مشخص نیست"""
        self._login_role("teacher", "t_scope_none")
        self.assertTrue(self.ac.has_student_scope(None))

    def test_teacher_role_value_matches_enum(self):
        """اطمینان از اینکه بررسی روی UserRole.TEACHER.value انجام می‌شود"""
        self.assertEqual(UserRole.TEACHER.value, "teacher")


if __name__ == "__main__":
    unittest.main()
