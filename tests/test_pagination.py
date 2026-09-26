"""
آزمون‌های اصلاح Query/Pagination — دور نوزدهم، مرحلهٔ ۶ (بخش‌های ۲، ۳، ۲۵، ۳۵)

پوشش مأموریت:
  • utils/pagination.py: اعتبارسنجی/Clamp مرکزی limit/offset و page/page_size
    (شامل قراردادِ حیاتیِ limit=None یعنی «بدون سقف» که خروجی Excel به آن
    وابسته است).
  • dal/student_dal.py: get_all/search/get_deleted واقعاً LIMIT/OFFSET دارند
    و count_all/count_search/count_deleted دقیقاً همان WHERE را (بدون
    LIMIT/OFFSET) می‌شمارند.
  • dal/observation_dal.py، dal/intervention_dal.py، dal/followup_dal.py،
    dal/extracurricular_dal.py: افزودن offset (سازگار با گذشته، پیش‌فرض
    None) + متدهای count_* جدید — به‌عنوان قابلیت آمادهٔ بک‌اند، بدون هیچ
    UI صفحه‌بندی تازه.
  • قرارداد قدیمی حفظ شده: limit=None هنوز یعنی «بدون سقف» (برای مصرف‌کننده‌هایی
    مثل خروجی Excel که کل دیتاست را می‌خواهند).

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
from utils.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    clamp_page_to_total,
    normalize_limit_offset,
    normalize_page,
)


class TestPaginationHelpers(unittest.TestCase):
    """آزمون‌های خالص utils/pagination.py (بدون دیتابیس)"""

    def test_limit_none_stays_unbounded(self):
        """limit=None باید دست‌نخورده بماند (قراردادِ «بدون سقف» صادرات Excel)"""
        limit, offset = normalize_limit_offset(None, None)
        self.assertIsNone(limit)
        self.assertIsNone(offset)

    def test_limit_none_ignores_offset(self):
        """اگر limit=None باشد، offset هم بی‌معنی است و None برمی‌گردد"""
        limit, offset = normalize_limit_offset(None, 50)
        self.assertIsNone(limit)
        self.assertIsNone(offset)

    def test_negative_limit_clamped_to_default(self):
        limit, _ = normalize_limit_offset(-5, 0)
        self.assertGreater(limit, 0)

    def test_limit_over_max_is_clamped(self):
        limit, _ = normalize_limit_offset(999999, 0)
        self.assertLessEqual(limit, MAX_PAGE_SIZE)

    def test_negative_offset_clamped_to_zero(self):
        _, offset = normalize_limit_offset(20, -10)
        self.assertEqual(offset, 0)

    def test_normalize_page_defaults(self):
        page, page_size, offset = normalize_page()
        self.assertEqual(page, 1)
        self.assertEqual(page_size, DEFAULT_PAGE_SIZE)
        self.assertEqual(offset, 0)

    def test_normalize_page_computes_offset(self):
        page, page_size, offset = normalize_page(page=3, page_size=20)
        self.assertEqual(page, 3)
        self.assertEqual(page_size, 20)
        self.assertEqual(offset, 40)

    def test_normalize_page_rejects_page_below_one(self):
        page, _, offset = normalize_page(page=0, page_size=20)
        self.assertEqual(page, 1)
        self.assertEqual(offset, 0)

    def test_clamp_page_to_total_within_range(self):
        page, total_pages = clamp_page_to_total(page=2, page_size=20, total=100)
        self.assertEqual(total_pages, 5)
        self.assertEqual(page, 2)

    def test_clamp_page_to_total_clamps_out_of_range(self):
        page, total_pages = clamp_page_to_total(page=999, page_size=20, total=45)
        self.assertEqual(total_pages, 3)
        self.assertEqual(page, 3)

    def test_clamp_page_to_total_empty_dataset(self):
        # قراردادِ صفحه‌بندیِ ۱-پایهٔ این ماژول: دیتاست خالی هم «صفحهٔ ۱ از
        # ۱» است (سازگار با متن نمایشیِ خالی، نه total_pages=0)
        page, total_pages = clamp_page_to_total(page=5, page_size=20, total=0)
        self.assertEqual(total_pages, 1)
        self.assertEqual(page, 1)


class PaginationDALTestBase(unittest.TestCase):
    """پایهٔ مشترک: دیتابیس موقت + فیکسچر دانش‌آموزان/سال تحصیلی"""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="partow_pagination_")
        self._saved = (_settings.DB_PATH, _dbc.DB_PATH)
        _settings.DB_PATH = os.path.join(self._tmpdir, "partow.db")
        _dbc.DB_PATH = _settings.DB_PATH
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False

        self.db = _dbc.DatabaseConnection()  # seed اولیه

        from utils.security import AccessControl
        AccessControl.logout()

    def tearDown(self):
        from utils.security import AccessControl
        AccessControl.logout()
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

    def _new_student(self, last_name, national_code):
        from dal.student_dal import StudentDAL
        from models.student import Student
        s = Student()
        s.first_name = "آزمون"
        s.last_name = last_name
        s.national_code = national_code
        return StudentDAL().create(s)


class TestStudentDALPagination(PaginationDALTestBase):
    """dal/student_dal.py — get_all/search/get_deleted + count_* (مرحلهٔ ۶)"""

    def setUp(self):
        super().setUp()
        from dal.student_dal import StudentDAL
        self.dal = StudentDAL()
        for i in range(25):
            self._new_student(f"صفحه{i:02d}", f"{5000000000 + i}")

    def test_count_all_matches_get_all_unbounded_length(self):
        self.assertEqual(self.dal.count_all(), 25)
        self.assertEqual(len(self.dal.get_all()), 25)

    def test_get_all_limit_offset_real_sql_pagination(self):
        page1 = self.dal.get_all(limit=10, offset=0)
        page2 = self.dal.get_all(limit=10, offset=10)
        page3 = self.dal.get_all(limit=10, offset=20)
        self.assertEqual(len(page1), 10)
        self.assertEqual(len(page2), 10)
        self.assertEqual(len(page3), 5)
        # سه صفحه باید مجموعاً همان ۲۵ دانش‌آموز را بدون تکرار پوشش دهند
        ids = {s.id for s in page1} | {s.id for s in page2} | {s.id for s in page3}
        self.assertEqual(len(ids), 25)

    def test_get_all_limit_none_is_unbounded(self):
        """قراردادِ حیاتی: limit=None یعنی همهٔ رکوردها (برای خروجی Excel)"""
        self.assertEqual(len(self.dal.get_all(limit=None)), 25)
        self.assertEqual(len(self.dal.get_all(limit=None, offset=5)), 25)

    def test_search_limit_offset(self):
        results_all = self.dal.search("صفحه")
        self.assertEqual(len(results_all), 25)
        page1 = self.dal.search("صفحه", limit=10, offset=0)
        page2 = self.dal.search("صفحه", limit=10, offset=10)
        self.assertEqual(len(page1), 10)
        self.assertEqual(len(page2), 10)

    def test_count_search_matches_unbounded_search_length(self):
        self.assertEqual(self.dal.count_search("صفحه"), 25)
        self.assertEqual(len(self.dal.search("صفحه")), 25)

    def test_get_deleted_pagination_and_count(self):
        students = self.dal.get_all()
        for s in students[:7]:
            self.dal.delete(s.id, 1)
        self.assertEqual(self.dal.count_deleted(), 7)
        page1 = self.dal.get_deleted(limit=5, offset=0)
        page2 = self.dal.get_deleted(limit=5, offset=5)
        self.assertEqual(len(page1), 5)
        self.assertEqual(len(page2), 2)

    def test_search_only_deleted_isolates_from_active(self):
        """جست‌وجوی only_deleted=True فقط حذف‌شده‌ها را می‌دهد، نه فعال‌ها"""
        students = self.dal.get_all()
        victim = next(s for s in students if s.last_name == "صفحه03")
        self.dal.delete(victim.id, 1)

        only_deleted = self.dal.search("صفحه", only_deleted=True)
        self.assertEqual([s.id for s in only_deleted], [victim.id])

        # پیش‌فرض (بدون only_deleted) باید حذف‌شده را نشان ندهد
        active_search = self.dal.search("صفحه")
        self.assertNotIn(victim.id, [s.id for s in active_search])

        self.assertEqual(self.dal.count_search("صفحه", only_deleted=True), 1)

    def test_invalid_limit_offset_are_clamped_not_crashing(self):
        """limit/offset نامعتبر (منفی/خیلی بزرگ) نباید کرش کند"""
        rows = self.dal.get_all(limit=-5, offset=-100)
        self.assertIsInstance(rows, list)
        rows2 = self.dal.get_all(limit=999999999, offset=0)
        self.assertLessEqual(len(rows2), 25)


class TestObservationDALPagination(PaginationDALTestBase):
    """dal/observation_dal.py — افزودن offset + count_all/count_search (زیرساخت بک‌اند)"""

    def setUp(self):
        super().setUp()
        from dal.observation_dal import ObservationDAL
        from dal.student_academic_profile_dal import StudentAcademicProfileDAL
        from models.observation import Observation
        from models.student_academic_profile import StudentAcademicProfile

        year_row = self.db.get_connection().execute(
            "SELECT id FROM academic_years WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        self.year_id = year_row["id"]

        student = self._new_student("رصدی", "5100000001")
        profile = StudentAcademicProfile()
        profile.student_id = student.id
        profile.academic_year_id = self.year_id
        profile.grade = 1
        profile.status = StudentAcademicProfile.STATUS_ACTIVE
        self.profile = StudentAcademicProfileDAL().create(profile)

        self.dal = ObservationDAL()
        for i in range(12):
            obs = Observation()
            obs.student_profile_id = self.profile.id
            obs.staff_id = 1
            obs.observation_date = "1403-01-01"
            obs.description = f"مشاهدهٔ آزمایشی شمارهٔ {i}"
            obs.behavior_type = "مثبت"
            self.dal.create(obs)

    def test_count_all_matches_unbounded_get_all(self):
        self.assertEqual(self.dal.count_all(), 12)
        self.assertEqual(len(self.dal.get_all()), 12)

    def test_get_all_offset_is_backward_compatible_and_real(self):
        page1 = self.dal.get_all(limit=5, offset=0)
        page2 = self.dal.get_all(limit=5, offset=5)
        self.assertEqual(len(page1), 5)
        self.assertEqual(len(page2), 5)
        self.assertNotEqual({o.id for o in page1}, {o.id for o in page2})

    def test_get_all_limit_none_still_unbounded(self):
        self.assertEqual(len(self.dal.get_all(limit=None)), 12)

    def test_count_search_matches_search_length(self):
        self.assertEqual(self.dal.count_search("آزمایشی"), 12)
        page = self.dal.search("آزمایشی", limit=4, offset=4)
        self.assertEqual(len(page), 4)


class TestInterventionDALPagination(PaginationDALTestBase):
    """dal/intervention_dal.py — افزودن offset + count_all/count_search"""

    def setUp(self):
        super().setUp()
        from dal.intervention_dal import InterventionDAL
        from dal.student_academic_profile_dal import StudentAcademicProfileDAL
        from models.intervention import Intervention
        from models.student_academic_profile import StudentAcademicProfile

        year_row = self.db.get_connection().execute(
            "SELECT id FROM academic_years WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        student = self._new_student("مداخله‌ای", "5200000001")
        profile = StudentAcademicProfile()
        profile.student_id = student.id
        profile.academic_year_id = year_row["id"]
        profile.grade = 1
        profile.status = StudentAcademicProfile.STATUS_ACTIVE
        self.profile = StudentAcademicProfileDAL().create(profile)

        self.dal = InterventionDAL()
        for i in range(9):
            it = Intervention()
            it.student_profile_id = self.profile.id
            it.staff_id = 1
            it.date = "1403-01-01"
            it.type = "individual"
            it.description = f"مداخلهٔ آزمایشی {i}"
            it.status = "planned"
            self.dal.create(it)

    def test_count_all_matches_unbounded_get_all(self):
        self.assertEqual(self.dal.count_all(), 9)
        self.assertEqual(len(self.dal.get_all()), 9)

    def test_get_all_offset_pagination(self):
        page1 = self.dal.get_all(limit=4, offset=0)
        page2 = self.dal.get_all(limit=4, offset=4)
        page3 = self.dal.get_all(limit=4, offset=8)
        self.assertEqual((len(page1), len(page2), len(page3)), (4, 4, 1))

    def test_count_search_matches_search_length(self):
        self.assertEqual(self.dal.count_search("آزمایشی"), 9)


class TestFollowUpDALPagination(PaginationDALTestBase):
    """dal/followup_dal.py — افزودن offset + count_all/count_search"""

    def setUp(self):
        super().setUp()
        from dal.followup_dal import FollowUpDAL
        from dal.intervention_dal import InterventionDAL
        from dal.student_academic_profile_dal import StudentAcademicProfileDAL
        from models.followup import FollowUp
        from models.intervention import Intervention
        from models.student_academic_profile import StudentAcademicProfile

        year_row = self.db.get_connection().execute(
            "SELECT id FROM academic_years WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        student = self._new_student("پیگیری‌ای", "5300000001")
        profile = StudentAcademicProfile()
        profile.student_id = student.id
        profile.academic_year_id = year_row["id"]
        profile.grade = 1
        profile.status = StudentAcademicProfile.STATUS_ACTIVE
        profile = StudentAcademicProfileDAL().create(profile)

        it = Intervention()
        it.student_profile_id = profile.id
        it.staff_id = 1
        it.date = "1403-01-01"
        it.type = "individual"
        it.description = "مداخلهٔ پایه برای پیگیری"
        it.status = "in_progress"
        self.intervention = InterventionDAL().create(it)

        self.dal = FollowUpDAL()
        for i in range(7):
            f = FollowUp()
            f.intervention_id = self.intervention.id
            f.staff_id = 1
            f.date = "1403-01-05"
            f.method = "in_person"
            f.description = f"پیگیری آزمایشی {i}"
            f.status = "done"
            self.dal.create(f)

    def test_count_all_matches_unbounded_get_all(self):
        self.assertEqual(self.dal.count_all(), 7)
        self.assertEqual(len(self.dal.get_all()), 7)

    def test_get_all_offset_pagination(self):
        page1 = self.dal.get_all(limit=3, offset=0)
        page2 = self.dal.get_all(limit=3, offset=3)
        page3 = self.dal.get_all(limit=3, offset=6)
        self.assertEqual((len(page1), len(page2), len(page3)), (3, 3, 1))

    def test_count_search_matches_search_length(self):
        self.assertEqual(self.dal.count_search("آزمایشی"), 7)


class TestExtracurricularDALPagination(PaginationDALTestBase):
    """dal/extracurricular_dal.py — افزودن offset + count_all"""

    def setUp(self):
        super().setUp()
        from dal.extracurricular_dal import ExtracurricularDAL
        from dal.student_academic_profile_dal import StudentAcademicProfileDAL
        from models.extracurricular_activity import ExtracurricularActivity
        from models.student_academic_profile import StudentAcademicProfile

        year_row = self.db.get_connection().execute(
            "SELECT id FROM academic_years WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        student = self._new_student("فعالیتی", "5400000001")
        profile = StudentAcademicProfile()
        profile.student_id = student.id
        profile.academic_year_id = year_row["id"]
        profile.grade = 1
        profile.status = StudentAcademicProfile.STATUS_ACTIVE
        self.profile = StudentAcademicProfileDAL().create(profile)

        self.dal = ExtracurricularDAL()
        for i in range(6):
            act = ExtracurricularActivity()
            act.student_profile_id = self.profile.id
            act.teacher_id = 1
            act.type = "sport"
            act.title = f"فعالیت آزمایشی {i}"
            act.start_date = "1403-02-01"
            self.dal.create(act)

    def test_count_all_matches_unbounded_get_all(self):
        self.assertEqual(self.dal.count_all(), 6)
        self.assertEqual(len(self.dal.get_all()), 6)

    def test_get_all_offset_pagination(self):
        page1 = self.dal.get_all(limit=4, offset=0)
        page2 = self.dal.get_all(limit=4, offset=4)
        self.assertEqual((len(page1), len(page2)), (4, 2))

    def test_limit_none_still_unbounded_with_offset_ignored(self):
        self.assertEqual(len(self.dal.get_all(limit=None, offset=3)), 6)


if __name__ == "__main__":
    unittest.main()
