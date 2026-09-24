"""
آزمون‌های مرز مجوز backend — دور هجدهم، مرحلهٔ ۱ (BUG-NAV-03)

پوشش مأموریت:
  • بند ۹ — «فراخوانی مستقیم بدون مجوز باید رد شود، نه فقط پنهان‌کردن دکمه»:
    کاربر واردشده با نقش کم‌مجوز، متدهای حساس DAL/سرویس را مستقیم صدا
    می‌زند و باید PermissionDeniedError بگیرد.
  • فقط سیاست‌های «اعلام‌شده» در Permission/ROLE_PERMISSIONS اعمال شده‌اند
    (هیچ مجوز جدیدی ابداع نشده — DD-1 در docs/design_decisions_fa.md).
  • DD-4 — بافت بدون نشست (اسکریپت/سیستم) مجاز است؛ نشستِ نقشِ بی‌مجوز رد
    می‌شود؛ غیرفعال‌سازی حساب همان لحظه دسترسی را می‌بندد.
  • تغییر نقش (MANAGE_ROLES) از ویرایش عادی کاربر (MANAGE_USERS) جدا است.
  • تغییر رمز «خود» بدون MANAGE_USERS مجاز است؛ رمز «دیگری» نه.
  • رد مجوز در Audit Log ثبت می‌شود (action='permission_denied').

هر تست روی دیتابیس موقت تازه اجرا می‌شود و نشست بین تست‌ها پاک می‌شود.
"""

import contextlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.connection as _dbc
from config import settings as _settings


class PermissionBoundaryTestBase(unittest.TestCase):
    """پایهٔ مشترک: دیتابیس موقت تازه + پاک‌سازی نشست"""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="partow_perm_")
        self._saved = (_settings.DB_PATH, _dbc.DB_PATH)
        _settings.DB_PATH = os.path.join(self._tmpdir, "partow.db")
        _dbc.DB_PATH = _settings.DB_PATH
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False

        from utils.security import AccessControl
        AccessControl.logout()
        self.ac = AccessControl

        # seed → کاربر admin/manager + staff «سیستم» موجود است
        self.db = _dbc.DatabaseConnection()
        self._users = self._manager_user_ids()

    def tearDown(self):
        from utils.security import AccessControl
        AccessControl.logout()
        with contextlib.suppress(Exception):
            _dbc.DatabaseConnection().close_all()
        _settings.DB_PATH, _dbc.DB_PATH = self._saved
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False

    # ---------------- کمکی ----------------

    def _manager_user_ids(self):
        """شناسهٔ users.id و staff_id کاربر manager پیش‌فرض (seed)"""
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT id, staff_id FROM users "
            "WHERE role = 'manager' AND is_deleted = 0 LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(row, "کاربر manager پیش‌فرض (seed) باید وجود داشته باشد")
        return {"users_id": row["id"], "staff_id": row["staff_id"]}

    def _make_staff_and_user(self, role, username):
        """
        ساخت staff + user با نقش دلخواه؛ خروجی: (users_id, staff_id)

        ساخت fixture در «بافت سیستمی» (بدون نشست) انجام می‌شود تا گارد
        مجوز روی UserDAL.create با سناریوی خود آزمون قاطی نشود؛ سپس
        نشست قبلی (اگر بود) برمی‌گردد.
        """
        from dal.staff_dal import StaffDAL
        from dal.user_dal import UserDAL
        from models.staff import Staff
        from models.user import User

        saved = self.ac.current_staff_id()
        self.ac.logout()
        try:
            staff = Staff()
            staff.full_name = f"آزمون {role}"
            staff.role = "other"  # نقش staff جدا از نقش کاربری است
            staff_id = StaffDAL().create(staff).id

            user = User()
            user.staff_id = staff_id
            user.username = username
            user.role = role
            user.is_active = 1
            users_id = UserDAL().create(user, raw_password="Passw0rd!123").id
        finally:
            if saved is not None:
                self.ac.login(saved, None)
        return users_id, staff_id

    def _login_staff(self, staff_id):
        """ورود به نشست backend با staff_id"""
        self.ac.login(staff_id, None)


class TestNoSessionSystemContext(PermissionBoundaryTestBase):
    """DD-4: بدون نشست = بافت سیستمی/اسکریپتی → عملیات مجاز (قرارداد)"""

    def test_guarded_ops_allowed_without_session(self):
        from dal.academic_year_dal import AcademicYearDAL
        from models.academic_year import AcademicYear

        self.assertFalse(self.ac.has_session())
        year = AcademicYear()
        year.title = "۱۴۰۳-۱۴۰۴"
        year.start_date = "1403/07/01"
        year.end_date = "1404/06/30"
        created = AcademicYearDAL().create(year)          # بدون نشست → مجاز
        AcademicYearDAL().set_active(created.id)          # بدون نشست → مجاز
        self.assertTrue(self.ac.has_permission("manage_users"))


class TestUnauthorizedDirectCallRejected(PermissionBoundaryTestBase):
    """بند ۹: فراخوانی مستقیم توسط کاربر بی‌مجوز → PermissionDeniedError"""

    def _login_teacher(self):
        users_id, staff_id = self._make_staff_and_user("teacher", "teacher_perm")
        self._login_staff(staff_id)
        return users_id, staff_id

    def test_teacher_cannot_manage_users(self):
        from dal.user_dal import UserDAL
        from utils.security import PermissionDeniedError

        self._login_teacher()
        victim, _ = self._make_staff_and_user("viewer", "victim_x")

        with self.assertRaises(PermissionDeniedError):
            UserDAL().delete(victim)
        # حذف انجام نشده باشد (نتیجهٔ واقعی بررسی شود، نه فقط استثنا)
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT is_deleted FROM users WHERE id = ?", (victim,)).fetchone()
        self.assertEqual(row["is_deleted"], 0)

    def test_teacher_cannot_change_academic_year(self):
        from dal.academic_year_dal import AcademicYearDAL
        from models.academic_year import AcademicYear
        from utils.security import PermissionDeniedError

        # ساخت سال در بافت سیستمی؛ سپس سناریو با نشست معلم
        year = AcademicYear()
        year.title = "۱۴۰۴-۱۴۰۵"
        year.start_date = "1404/07/01"
        year.end_date = "1405/06/30"
        created = AcademicYearDAL().create(year)
        self._login_teacher()
        with self.assertRaises(PermissionDeniedError):
            AcademicYearDAL().set_active(created.id)
        # سال فعال همان سال پیش‌فرض بماند
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT title FROM academic_years WHERE is_active = 1 "
            "AND is_deleted = 0").fetchone()
        self.assertNotEqual(row["title"], "۱۴۰۴-۱۴۰۵")

    def test_teacher_cannot_delete_student(self):
        from dal.student_dal import StudentDAL
        from models.student import Student
        from utils.security import PermissionDeniedError

        student = Student()
        student.first_name = "سینا"
        student.last_name = "آزمونی"
        student.national_code = "3333333333"
        sid = StudentDAL().create(student).id  # create دانش‌آموز محافظت نیست
        self._login_teacher()
        with self.assertRaises(PermissionDeniedError):
            StudentDAL().delete(sid)
        row = self.db.get_connection().execute(
            "SELECT is_deleted FROM students WHERE id = ?", (sid,)).fetchone()
        self.assertEqual(row["is_deleted"], 0)

    def test_teacher_cannot_restore_backup(self):
        from utils.security import PermissionDeniedError

        self._login_teacher()
        from utils.backup import BackupManager
        manager = BackupManager(
            db_path=os.path.join(self._tmpdir, "partow.db"),
            attachments_dir=os.path.join(self._tmpdir, "att"),
            backup_dir=os.path.join(self._tmpdir, "bk"),
        )
        with self.assertRaises(PermissionDeniedError):
            manager.restore_backup("any.partobak")

    def test_teacher_can_create_observation_context_but_no_delete(self):
        """CREATE_OBSERVATION دارد؛ DELETE_OBSERVATION ندارد (سیاست فعلی)"""
        from dal.observation_dal import ObservationDAL
        from utils.security import PermissionDeniedError

        self._login_teacher()
        self.assertTrue(self.ac.has_permission("create_observation"))
        self.assertFalse(self.ac.has_permission("delete_observation"))
        # حتی حذفِ «رکورد ناموجود» هم پیش از هرچیز به مرز مجوز می‌خورد
        with self.assertRaises(PermissionDeniedError):
            ObservationDAL().delete(999999)

    def test_denial_is_audited(self):
        """رد مجوز در audit_logs با action='permission_denied' ثبت می‌شود"""
        from dal.user_dal import UserDAL
        from utils.security import PermissionDeniedError

        _, staff_id = self._login_teacher()
        victim, _ = self._make_staff_and_user("viewer", "victim_y")
        with self.assertRaises(PermissionDeniedError):
            UserDAL().delete(victim)

        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT user_id, action FROM audit_logs "
            "WHERE action = 'permission_denied' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(row, "رد مجوز باید در Audit Log بیاید")
        self.assertEqual(row["user_id"], staff_id)


class TestRoleIsolation(PermissionBoundaryTestBase):
    """جداسازی MANAGE_USERS از MANAGE_ROLES و نقش‌های مختلف"""

    def test_vice_principal_cannot_delete_user_but_can_restore_backup_perm(self):
        from utils.security import PermissionDeniedError

        _, staff_id = self._make_staff_and_user(
            "vice_principal", "vp_perm")
        self._login_staff(staff_id)
        # RESTORE_BACKUP دارد (سیاست فعلی ROLE_PERMISSIONS)
        self.assertTrue(self.ac.has_permission("restore_backup"))
        # MANAGE_USERS ندارد
        self.assertFalse(self.ac.has_permission("manage_users"))
        from dal.user_dal import UserDAL
        with self.assertRaises(PermissionDeniedError):
            UserDAL().set_active(self._users["users_id"], False)

    def test_role_change_requires_manage_roles(self):
        from dal.user_dal import UserDAL
        from models.user import User
        from utils.security import PermissionDeniedError

        target_id, _ = self._make_staff_and_user("viewer", "role_target")

        # manager: هم MANAGE_USERS دارد هم MANAGE_ROLES → تغییر نقش مجاز
        self._login_staff(self._users["staff_id"])
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (target_id,)).fetchone()
        user = User()
        user.id = row["id"]
        user.staff_id = row["staff_id"]
        user.username = row["username"]
        user.role = "teacher"
        user.password_hash = row["password_hash"]
        user.is_active = row["is_active"]
        user.must_change_password = row["must_change_password"]
        updated = UserDAL().update(user)
        self.assertEqual(updated.role, "teacher")

        # کاربر بدون MANAGE_ROLES (اینجا: نفسِ manager بودن را می‌گیریم
        # با نشستِ vice_education که MANAGE_USERS هم ندارد → رد در همان
        # گارد اولِ update)
        _, ve_staff = self._make_staff_and_user("vice_education", "ve_perm")
        self._login_staff(ve_staff)
        user.role = "viewer"
        with self.assertRaises(PermissionDeniedError):
            UserDAL().update(user)


class TestOwnPasswordChange(PermissionBoundaryTestBase):
    """DD-4: تغییر رمز «خود» بدون MANAGE_USERS مجاز؛ رمز «دیگری» نه"""

    def test_own_password_allowed_without_manage_users(self):
        from dal.user_dal import UserDAL

        users_id, staff_id = self._make_staff_and_user("teacher", "own_pw")
        self._login_staff(staff_id)
        ok = UserDAL().update_password(users_id, "NewPass!9876")
        self.assertTrue(ok)

    def test_others_password_requires_manage_users(self):
        from dal.user_dal import UserDAL
        from utils.security import PermissionDeniedError

        self._make_staff_and_user("teacher", "t1_pw")
        _other_id, other_staff = self._make_staff_and_user("teacher", "t2_pw")
        self._login_staff(other_staff)  # t2 می‌خواهد رمز t1 را عوض کند
        target_id, _ = self._make_staff_and_user("teacher", "t3_pw")
        with self.assertRaises(PermissionDeniedError):
            UserDAL().update_password(target_id, "Hacked!000")


class TestSessionRevocation(PermissionBoundaryTestBase):
    """غیرفعال‌سازی/حذف حساب → نشست همان لحظه بی‌اعتبار (خوانش تازهٔ نقش)"""

    def test_deactivated_account_loses_backend_access(self):
        from dal.user_dal import UserDAL

        # مدیر عامل سیستم؟ نه: ادمین وارد است و معلم را غیرفعال می‌کند
        self._login_staff(self._users["staff_id"])
        target_id, target_staff = self._make_staff_and_user(
            "teacher", "deact_me")
        self.assertTrue(UserDAL().set_active(target_id, False))

        # نشست معلم هنوز «باز» است، ولی حسابش غیرفعال شده → رد
        self._login_staff(target_staff)
        self.assertFalse(self.ac.has_permission("create_observation"))
        from dal.user_dal import UserDAL as _U
        with self.assertRaises(Exception):
            _U().reset_password(self._users["users_id"])


class TestUiHelperConsistency(PermissionBoundaryTestBase):
    """DD-5: کمکی UI همان پاسخ مرز backend را می‌دهد"""

    def test_teacher_has_no_delete_permission_flag(self):
        self._make_staff_and_user("teacher", "ui_teacher")
        # بدون نشست → True (بافت سیستمی)
        self.assertTrue(self.ac.has_permission("delete_student"))
        _, staff_id = self._make_staff_and_user("teacher", "ui_teacher2")
        self._login_staff(staff_id)
        self.assertFalse(self.ac.has_permission("delete_student"))
        self._login_staff(self._users["staff_id"])
        self.assertTrue(self.ac.has_permission("delete_student"))


if __name__ == "__main__":
    unittest.main()
