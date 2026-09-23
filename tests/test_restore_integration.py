"""
آزمون‌های یکپارچهٔ «حذف → بازیابی → تغییر سال → ویرایش» (دور هفدهم — مرحلهٔ ۳)

پوشش بندهای مأموریت:

  • §۳۸ / IT-RESTORE-YEAR-01 — حذف دانش‌آموز، بازیابی، تغییر سال فعال و
    ویرایش: پروندهٔ تاریخی نه جابه‌جا می‌شود و نه تغییر می‌کند.
  • §۳۹ / IT-YEAR-CRUD-01 — دو دانش‌آموز در دو سال (۱۴۰۳/۱۴۰۴)، سپس
    حذف/بازیابی/ویرایش و بررسی جدایی کامل دادهٔ سال‌ها.
  • §۳ / BUG-RESTORE-01/05/06/07 — قرارداد واقعی سرویس‌های بازیابی:
    «فقط رکورد حذف‌شده»، «بررسی اثر واقعی روی دیتابیس»، «خطای صریح برای
    رکورد ناموجود»، «حفظ پروندهٔ سالانه»، و «فهرست حذف‌شده‌ها = همان
    چیزهایی که در DB حذف‌شده‌اند».

نکتهٔ جداسازی: هر تست روی یک دیتابیس موقت تازه اجرا می‌شود و در پایان،
مسیر و اتصال قبلی برگردانده می‌شود؛ نه دیتابیس واقعی، نه دیتابیس سایر
تست‌ها دست نمی‌خورَد. (همان درسِ آزمون حساب‌داری پشتیبان در مرحلهٔ ۱.)

این فایل Qt لازم ندارد (اجرای واقعی فرم/صفحه‌ها در `verify_fixes17.py §C`
با QApplication آفلاین انجام می‌شود).
"""

import contextlib
import io
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.connection as _dbc
from config import settings as _settings
from dal.academic_year_dal import AcademicYearDAL
from dal.counseling_session_dal import CounselingSessionDAL
from dal.extracurricular_dal import ExtracurricularDAL
from dal.family_context_dal import FamilyContextDAL
from dal.goal_dal import GoalDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.academic_year import AcademicYear
from models.staff import Staff
from models.student_academic_profile import StudentAcademicProfile
from services.counseling_service import CounselingService
from services.extracurricular_service import ExtracurricularService
from services.goal_service import GoalService
from services.student_service import StudentService
from utils.error_handler import ServiceError

_NATIONAL_BASE = random.randint(10000000, 89999999)


class _IsolatedStackTest(unittest.TestCase):
    """پایهٔ مشترک: دیتابیس موقت تازه برای هر تست + بازگردانی وضعیت قبلی"""

    def setUp(self):
        self._saved = (
            _settings.DB_PATH,
            _dbc.DB_PATH,
            _dbc.DatabaseConnection._instance,
            _dbc.DatabaseConnection._connection,
            _dbc.DatabaseConnection._initialized,
            getattr(_dbc.DatabaseConnection, "_current_user_id", None),
        )
        self._tmpdir = tempfile.mkdtemp(prefix="partow_restore_it_")
        _settings.DB_PATH = os.path.join(self._tmpdir, "partow.db")
        _dbc.DB_PATH = _settings.DB_PATH
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False
        with contextlib.redirect_stdout(io.StringIO()):
            _dbc.DatabaseConnection().get_connection(user_id=1)

        self.year_dal = AcademicYearDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.family_dal = FamilyContextDAL()
        self.staff_dal = StaffDAL()
        self.student_service = StudentService()
        self._national_seed = 0

    def tearDown(self):
        (_settings.DB_PATH, _dbc.DB_PATH, _dbc.DatabaseConnection._instance,
         _dbc.DatabaseConnection._connection, _dbc.DatabaseConnection._initialized,
         _current) = self._saved
        if _current is not None:
            _dbc.DatabaseConnection._current_user_id = _current

    # ------------------------------------------------------------------
    # ابزارهای ساخت داده
    # ------------------------------------------------------------------

    def _national_code(self):
        """کد ملی یکتا و ۱۰رقمی برای هر آزمون (بدون دست‌زدن به داده واقعی)"""
        self._national_seed += 1
        return f"{_NATIONAL_BASE}{self._national_seed:02d}"

    def _make_year(self, title, start_date, end_date, active=False):
        year = AcademicYear()
        year.title = title
        year.start_date = start_date
        year.end_date = end_date
        year.is_active = 1 if active else 0
        created = self.year_dal.create(year)
        if active:
            self.year_dal.set_active(created.id)
        return created

    def _add_student(self, first_name, last_name, grade=1, class_name=""):
        """
        دانش‌آموز از مسیر واقعی سرویس (StudentService.create_student)

        این مسیر خودش پروندهٔ سالانهٔ «سال فعال» را با همان پایه/کلاس می‌سازد؛
        همان چیزی که فرم ثبت‌نام انجام می‌دهد.
        """
        with contextlib.redirect_stdout(io.StringIO()):
            created = self.student_service.create_student({
                "first_name": first_name,
                "last_name": last_name,
                "national_code": self._national_code(),
                "grade": grade,
                "class_name": class_name,
            }, user_id=1)
        return created

    def _profile_in_year(self, student_id, year_id):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.profile_dal.get_by_student_and_year(student_id, year_id)

    def _add_profile(self, student_id, year_id, grade, class_name):
        profile = StudentAcademicProfile()
        profile.student_id = student_id
        profile.academic_year_id = year_id
        profile.grade = grade
        profile.class_name = class_name
        profile.status = StudentAcademicProfile.STATUS_ACTIVE
        with contextlib.redirect_stdout(io.StringIO()):
            return self.profile_dal.create(profile)

    def _profiles(self, student_id):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.profile_dal.get_all_profiles_for_student(
                student_id, include_deleted=True)

    def _form_like_edit(self, student, active_year, grade, class_name):
        """
        همان کاری که `StudentForm.save_student` برای پروندهٔ سالانه می‌کند:
        اگر پروندهٔ «سال فعال» هست به‌روزش می‌کند، وگرنه پروندهٔ تازه می‌سازد.
        اجرای واقعی خودِ فرم در `verify_fixes17.py §C` انجام می‌شود؛ اینجا
        فقط همان قرارداد بدون Qt تکرار می‌شود.
        """
        with contextlib.redirect_stdout(io.StringIO()):
            profile = self.profile_dal.get_by_student_and_year(
                student.id, active_year.id)
            if profile:
                profile.grade = grade
                profile.class_name = class_name
                profile.status = StudentAcademicProfile.STATUS_ACTIVE
                saved = self.profile_dal.update(profile)
            else:
                saved = self._add_profile(
                    student.id, active_year.id, grade, class_name)
        return saved

    def _audit_rows(self, table, entity_id):
        """
        ردیف‌های Audit یک رکورد

        نکته: تریگرهای دیتابیس نام «جدول» را در entity_type می‌نویسند
        (مثل «students») و همان ردیف تریگر، ثبت دستیِ سرویس را بی‌نیاز
        می‌کند؛ پس شاهدِ حسابرسیِ بازیابی هم همان ردیف است.
        """
        fresh = _dbc.DatabaseConnection().get_connection(user_id=1)
        rows = fresh.execute(
            "SELECT action, user_id FROM audit_logs WHERE entity_type = ? "
            "AND entity_id = ?", (table, entity_id)).fetchall()
        return [{"action": r[0], "user_id": r[1]} for r in rows]


class TestRestoreYearIntegration(_IsolatedStackTest):
    """§۳۸ — IT-RESTORE-YEAR-01: حذف → بازیابی → تغییر سال → ویرایش"""

    def test_it_restore_year_01(self):
        year_1403 = self._make_year("1403-1404", "1403/07/01", "1404/03/31",
                                    active=True)
        year_1404 = self._make_year("1404-1405", "1404/07/01", "1405/03/31")

        student = self._add_student("زهرا", "بازیابی", grade=3, class_name="سوم-الف")
        profile_1403 = self._profile_in_year(student.id, year_1403.id)
        self.assertIsNotNone(profile_1403)
        self.assertEqual(profile_1403.academic_year_id, year_1403.id)
        self.assertEqual(profile_1403.grade, 3)

        # ۱) حذف منطقی
        with contextlib.redirect_stdout(io.StringIO()):
            deleted = self.student_service.delete_student(student.id, user_id=1)
        self.assertTrue(deleted)
        self.assertIsNone(self.student_dal.get_by_id(student.id))
        deleted_ids = [s.id for s in self.student_service.get_deleted_students()]
        self.assertIn(student.id, deleted_ids)

        # ۲) بازیابی — پروندهٔ ۱۴۰۳ باید دست‌نخورده بماند
        with contextlib.redirect_stdout(io.StringIO()):
            restored = self.student_service.restore_student(student.id, user_id=1)
        self.assertEqual(restored.id, student.id)
        self.assertFalse(getattr(restored, "is_deleted", 0))
        self.assertNotIn(student.id,
                         [s.id for s in self.student_service.get_deleted_students()])
        profiles_after_restore = self._profiles(student.id)
        self.assertEqual([p.id for p in profiles_after_restore], [profile_1403.id])
        self.assertEqual(profiles_after_restore[0].academic_year_id, year_1403.id)
        self.assertEqual(profiles_after_restore[0].grade, 3)
        self.assertEqual(profiles_after_restore[0].class_name, "سوم-الف")

        # ۳) تغییر سال فعال
        self.year_dal.set_active(year_1404.id)
        self.assertEqual(self.year_dal.get_active().id, year_1404.id)

        # ۴) ویرایش در سال جدید: پروندهٔ ۱۴۰۴ ساخته می‌شود، ۱۴۰۳ جابه‌جا نمی‌شود
        self._form_like_edit(student, year_1404, 4, "چهارم-ب")
        profiles = {p.academic_year_id: p for p in self._profiles(student.id)}
        self.assertEqual(set(profiles), {year_1403.id, year_1404.id})
        self.assertEqual(profiles[year_1403.id].id, profile_1403.id)
        self.assertEqual(profiles[year_1403.id].grade, 3)
        self.assertEqual(profiles[year_1403.id].class_name, "سوم-الف")
        self.assertEqual(profiles[year_1404.id].grade, 4)
        self.assertEqual(profiles[year_1404.id].class_name, "چهارم-ب")

        # ۵) ویرایش دوبارهٔ همان دانش‌آموز در سال ۱۴۰۴ → فقط همان پرونده
        self._form_like_edit(student, year_1404, 4, "چهارم-ج")
        profiles = {p.academic_year_id: p for p in self._profiles(student.id)}
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[year_1404.id].class_name, "چهارم-ج")
        self.assertEqual(profiles[year_1403.id].class_name, "سوم-الف")


class TestYearCrudIntegration(_IsolatedStackTest):
    """§۳۹ — IT-YEAR-CRUD-01: دو دانش‌آموز در دو سال + حذف/بازیابی/ویرایش"""

    def test_it_year_crud_01(self):
        year_1403 = self._make_year("1403-1404", "1403/07/01", "1404/03/31",
                                    active=True)
        student_a = self._add_student("الف", "سال‌اول", grade=1, class_name="اول-الف")
        profile_a_1403 = self._profile_in_year(student_a.id, year_1403.id)

        year_1404 = self._make_year("1404-1405", "1404/07/01", "1405/03/31",
                                    active=True)
        self.assertEqual(self.year_dal.get_active().id, year_1404.id)
        student_b = self._add_student("بهرام", "سال‌دوم", grade=2, class_name="دوم-ب")
        profile_b_1404 = self._profile_in_year(student_b.id, year_1404.id)

        # ویرایش «ب» در سال ۱۴۰۴ نباید به پروندهٔ «الف» در ۱۴۰۳ دست بزند
        self._form_like_edit(student_b, year_1404, 2, "دوم-ج")
        self.assertEqual(self._profiles(student_a.id)[0].id, profile_a_1403.id)
        self.assertEqual(self._profiles(student_a.id)[0].grade, 1)
        self.assertEqual(self._profiles(student_b.id)[0].id, profile_b_1404.id)
        self.assertEqual(self._profiles(student_b.id)[0].class_name, "دوم-ج")

        # حذف/بازیابی «الف» در حالی که سال فعال ۱۴۰۴ است
        with contextlib.redirect_stdout(io.StringIO()):
            self.student_service.delete_student(student_a.id, user_id=1)
            restored = self.student_service.restore_student(student_a.id, user_id=1)
        self.assertEqual(restored.id, student_a.id)

        profiles_a = self._profiles(student_a.id)
        self.assertEqual([p.id for p in profiles_a], [profile_a_1403.id])
        self.assertEqual(profiles_a[0].academic_year_id, year_1403.id)
        self.assertEqual(profiles_a[0].class_name, "اول-الف")
        # بازیابی نباید پروندهٔ تازه در سال فعال بسازد
        self.assertIsNone(self.profile_dal.get_by_student_and_year(
            student_a.id, year_1404.id))
        # و دادهٔ «ب» هم دست‌نخورده می‌ماند
        self.assertEqual(self._profiles(student_b.id)[0].class_name, "دوم-ج")

        # ویرایش «الف» در سال فعال ۱۴۰۴ → پروندهٔ ۱۴۰۴ افزوده می‌شود، ۱۴۰۳ حفظ
        self._form_like_edit(student_a, year_1404, 2, "دوم-الف")
        profiles_a = {p.academic_year_id: p for p in self._profiles(student_a.id)}
        self.assertEqual(set(profiles_a), {year_1403.id, year_1404.id})
        self.assertEqual(profiles_a[year_1403.id].grade, 1)
        self.assertEqual(profiles_a[year_1403.id].class_name, "اول-الف")
        self.assertEqual(profiles_a[year_1404.id].class_name, "دوم-الف")


class TestStudentRestoreContract(_IsolatedStackTest):
    """§۳ — قرارداد سرویس بازیابی دانش‌آموز"""

    def setUp(self):
        super().setUp()
        self.year = self._make_year("1403-1404", "1403/07/01", "1404/03/31",
                                    active=True)

    def test_restore_rejects_active_record_without_touching_db(self):
        student = self._add_student("سالم", "فعال")
        before = self._audit_rows("students", student.id)
        with self.assertRaises(ServiceError) as ctx:
            self.student_service.restore_student(student.id, user_id=1)
        self.assertIn("حذف نشده", str(ctx.exception))
        self.assertIsNotNone(self.student_dal.get_by_id(student.id))
        self.assertEqual(self._audit_rows("students", student.id), before)

    def test_restore_missing_record_is_explicit_error(self):
        before = len(self.student_dal.get_all())
        with self.assertRaises(ServiceError):
            self.student_service.restore_student(987654, user_id=1)
        self.assertEqual(len(self.student_dal.get_all()), before)

    def test_deleted_list_matches_db_and_shrinks_after_restore(self):
        students = [self._add_student(f"حذف‌شدنی{i}", "تست") for i in range(3)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.student_service.delete_student(students[0].id, user_id=1)
            self.student_service.delete_student(students[1].id, user_id=1)

        deleted_ids = {s.id for s in self.student_service.get_deleted_students()}
        self.assertEqual(deleted_ids, {students[0].id, students[1].id})

        with contextlib.redirect_stdout(io.StringIO()):
            self.student_service.restore_student(students[0].id, user_id=1)
        deleted_ids = {s.id for s in self.student_service.get_deleted_students()}
        self.assertEqual(deleted_ids, {students[1].id})

    def test_restore_keeps_all_historical_profiles_and_writes_audit(self):
        student = self._add_student("چندساله", "تست", grade=1, class_name="اول-الف")
        other_year = self._make_year("1404-1405", "1404/07/01", "1405/03/31")
        first = self._profile_in_year(student.id, self.year.id)
        second = self._add_profile(student.id, other_year.id, 2, "دوم-ب")
        before = {p.id: (p.academic_year_id, p.grade, p.class_name)
                  for p in self._profiles(student.id)}

        with contextlib.redirect_stdout(io.StringIO()):
            self.student_service.delete_student(student.id, user_id=1)
        with contextlib.redirect_stdout(io.StringIO()):
            self.student_service.restore_student(student.id, user_id=1)

        after = {p.id: (p.academic_year_id, p.grade, p.class_name)
                 for p in self._profiles(student.id)}
        self.assertEqual(after, before)
        self.assertEqual(set(after), {first.id, second.id})
        restore_rows = [r for r in self._audit_rows("students", student.id)
                        if r["action"] == "restore"]
        self.assertTrue(restore_rows)
        self.assertEqual({r["user_id"] for r in restore_rows}, {1})


class TestEntityRestoreContract(_IsolatedStackTest):
    """§۳ — قرارداد سرویس بازیابی فعالیت/هدف/مشاوره (RESTORE-05/06/07)"""

    def setUp(self):
        super().setUp()
        self.year = self._make_year("1403-1404", "1403/07/01", "1404/03/31",
                                    active=True)
        student = self._add_student("صاحب", "پرونده", grade=1, class_name="اول-الف")
        self.profile = self._profile_in_year(student.id, self.year.id)
        staff = Staff()
        staff.full_name = "مشاور آزمون"
        staff.role = "مشاور"
        with contextlib.redirect_stdout(io.StringIO()):
            self.staff = self.staff_dal.create(staff)

    def _check_contract(self, service, dal, create, delete, restore, get_deleted):
        """قرارداد مشترک چهار عملیات: ساخت → حذف → بازیابی → بررسی"""
        entity = create()
        self.assertFalse(getattr(entity, "is_deleted", 0))

        # رکورد فعال نباید بازیابی شود
        with self.assertRaises(ServiceError) as ctx:
            restore(entity.id)
        self.assertIn("حذف نشده", str(ctx.exception))
        self.assertFalse(getattr(dal.get_by_id(entity.id), "is_deleted", 0))

        # حذف منطقی → در فهرست حذف‌شده‌ها
        delete(entity.id)
        self.assertTrue(getattr(dal.get_by_id(entity.id, include_deleted=True),
                                "is_deleted", 0))
        self.assertIn(entity.id, [e.id for e in get_deleted()])

        # بازیابی واقعی
        restored = restore(entity.id)
        self.assertEqual(restored.id, entity.id)
        self.assertFalse(getattr(restored, "is_deleted", 0))
        self.assertEqual(restored.student_profile_id, self.profile.id)
        self.assertNotIn(entity.id, [e.id for e in get_deleted()])

        # رکورد ناموجود → خطای صریح
        with self.assertRaises(ServiceError):
            restore(999999)
        return restored

    def test_activity_restore_contract(self):
        service = ExtracurricularService()
        dal = ExtracurricularDAL()
        data = {
            "student_profile_id": self.profile.id,
            "title": "المپیاد ریاضی",
            "type": "scientific",
            "start_date": "1403/08/01",
            "status": "planned",
        }

        def _create():
            with contextlib.redirect_stdout(io.StringIO()):
                return service.create_activity(data, user_id=1)

        def _delete(activity_id):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(service.delete_activity(activity_id, user_id=1))

        restored = self._check_contract(
            service, dal, _create, _delete,
            lambda aid: service.restore_activity(aid, user_id=1),
            service.get_deleted_activities)
        self.assertEqual(restored.title, "المپیاد ریاضی")

    def test_goal_restore_contract(self):
        service = GoalService()
        dal = GoalDAL()
        data = {
            "student_profile_id": self.profile.id,
            "title": "بهبود تمرکز",
            "domain": "educational",
            "priority": "medium",
            "start_date": "1403/08/01",
        }

        def _create():
            with contextlib.redirect_stdout(io.StringIO()):
                return service.create_goal(data, user_id=1)

        def _delete(goal_id):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(service.delete_goal(goal_id, user_id=1))

        restored = self._check_contract(
            service, dal, _create, _delete,
            lambda gid: service.restore_goal(gid, user_id=1),
            service.get_deleted_goals)
        self.assertEqual(restored.title, "بهبود تمرکز")

    def test_counseling_restore_contract(self):
        service = CounselingService()
        dal = CounselingSessionDAL()
        data = {
            "student_profile_id": self.profile.id,
            "counselor_id": self.staff.id,
            "session_date": "1403/08/01",
            "type": "individual",
            "topic": "افت تحصیلی",
        }

        def _create():
            with contextlib.redirect_stdout(io.StringIO()):
                return service.create_session(data, user_id=1)

        def _delete(session_id):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(service.delete_session(session_id, user_id=1))

        restored = self._check_contract(
            service, dal, _create, _delete,
            lambda sid: service.restore_session(sid, user_id=1),
            service.get_deleted_sessions)
        self.assertEqual(restored.topic, "افت تحصیلی")


if __name__ == "__main__":
    unittest.main(verbosity=2)
