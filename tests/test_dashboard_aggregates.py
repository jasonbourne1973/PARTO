"""
آزمون‌های اصلاح Dashboard/Performance با Aggregate — دور نوزدهم، مرحلهٔ ۷
(PERF-01/08/09)

پوشش مأموریت:
  • dal/observation_dal.py::get_dashboard_stats/get_monthly_trend — کوئری
    Aggregate جدید (COUNT/SUM/GROUP BY) که جایگزین حلقهٔ پایتونیِ قدیمیِ
    dashboard_service شد؛ باید همان اعداد را (با همان فیلترهای
    staff_id/academic_year_id که get_all/count_all دارند) برگرداند.
  • dal/followup_dal.py::get_dashboard_stats — همان‌طور برای پیگیری‌ها.
  • رفع باگِ جانبیِ کشف‌شده حین این مرحله: فیلتر academic_year_id در
    get_all/count_all سه DAL (Observation/Intervention/FollowUp) قبلاً
    پروندهٔ حذف‌شده (student_academic_profiles.is_deleted=1) را هم می‌شمرد
    — چون JOIN با student_academic_profiles شرط sap.is_deleted=0 نداشت؛
    در حالی‌که همه‌جای دیگرِ کد (profile_dal.get_by_ids و منطق پایتونیِ
    قدیمیِ dashboard_service که از همان متد استفاده می‌کرد) پروندهٔ
    حذف‌شده را از فیلتر سال مستثنا می‌کردند. این تست‌ها صریحاً این مورد
    را regression می‌کنند.
  • services/dashboard_service.py::_get_general_stats/_get_observation_trend/
    _get_teacher_stats — آزمون سرتاسری (End-to-End) با دیتاست ثابت، برای
    اطمینان از این‌که خروجی نهاییِ Dashboard بعد از این تعویضِ داخلی همان
    اعداد قبلی را دارد (بدون تغییر UI/خروجی قابل‌مشاهده).

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


class DashboardAggregateTestBase(unittest.TestCase):
    """پایهٔ مشترک: دیتابیس موقت + فیکسچرهای دانش‌آموز/سال تحصیلی/پرونده"""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="partow_dashboard_agg_")
        self._saved = (_settings.DB_PATH, _dbc.DB_PATH)
        _settings.DB_PATH = os.path.join(self._tmpdir, "partow.db")
        _dbc.DB_PATH = _settings.DB_PATH
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False

        self.db = _dbc.DatabaseConnection()  # seed اولیه

        from utils.security import AccessControl
        AccessControl.logout()

        from dal.academic_year_dal import AcademicYearDAL
        from dal.followup_dal import FollowUpDAL
        from dal.intervention_dal import InterventionDAL
        from dal.observation_dal import ObservationDAL
        from dal.student_academic_profile_dal import StudentAcademicProfileDAL
        from dal.student_dal import StudentDAL

        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()

        row = self.db.get_connection().execute(
            "SELECT id FROM academic_years WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        self.year_a_id = row["id"]

        from models.academic_year import AcademicYear
        year_b = AcademicYear()
        year_b.title = "سال دوم آزمون"
        year_b.start_date = "1404/07/01"
        year_b.end_date = "1405/03/31"
        year_b.is_active = 0
        self.year_b_id = AcademicYearDAL().create(year_b).id

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

    def _new_staff(self, full_name):
        """
        ایجاد یک عضو کادر با درج مستقیم SQL (نه AccessControl/Service):
        مأموریتِ Stage 6/سایر بخش‌ها نشان داد make_staff_and_user برای
        نقش‌های غیرمعلم شکست می‌خورد؛ برای این آزمون فقط یک ردیف معتبر در
        جدول staff لازم است (کلید خارجیِ observations.staff_id/interventions.
        staff_id/followups.staff_id باید یک ردیف واقعی را نشانه بگیرد).
        """
        cur = self.db.get_connection().execute(
            "INSERT INTO staff (full_name, role, is_active) VALUES (?, 'teacher', 1)",
            (full_name,))
        self.db.commit()
        return cur.lastrowid

    def _new_student(self, last_name, national_code):
        from models.student import Student
        s = Student()
        s.first_name = "آزمون"
        s.last_name = last_name
        s.national_code = national_code
        return self.student_dal.create(s)

    def _new_profile(self, student_id, academic_year_id):
        from models.student_academic_profile import StudentAcademicProfile
        p = StudentAcademicProfile()
        p.student_id = student_id
        p.academic_year_id = academic_year_id
        p.grade = 1
        p.class_name = "اول-الف"
        return self.profile_dal.create(p)

    def _new_observation(self, profile_id, staff_id, behavior_type, date="1404/01/01"):
        from models.observation import Observation
        o = Observation()
        o.student_profile_id = profile_id
        o.staff_id = staff_id
        o.observation_date = date
        o.description = "مشاهدهٔ آزمون Aggregate"
        o.behavior_type = behavior_type
        return self.observation_dal.create(o)

    def _new_intervention(self, profile_id, staff_id, date="1404/01/01"):
        from models.intervention import Intervention
        i = Intervention()
        i.student_profile_id = profile_id
        i.staff_id = staff_id
        i.type = "گفتگوی فردی"
        i.date = date
        i.description = "مداخلهٔ آزمون Aggregate"
        return self.intervention_dal.create(i)

    def _new_followup(self, intervention_id, staff_id, status="pending", date="1404/01/01"):
        from models.followup import FollowUp
        f = FollowUp()
        f.intervention_id = intervention_id
        f.staff_id = staff_id
        f.date = date
        f.status = status
        f.description = "پیگیری آزمون Aggregate"
        return self.followup_dal.create(f)


class TestObservationDashboardStats(DashboardAggregateTestBase):
    """ObservationDAL.get_dashboard_stats — شمارش/تفکیک با یک کوئری Aggregate"""

    def setUp(self):
        super().setUp()
        self.teacher10 = self._new_staff("معلم آزمون ۱۰")
        self.teacher20 = self._new_staff("معلم آزمون ۲۰")
        student1 = self._new_student("آگ‌دان۱", "8100000001")
        student2 = self._new_student("آگ‌دان۲", "8100000002")
        self.profile1 = self._new_profile(student1.id, self.year_a_id)
        self.profile2 = self._new_profile(student2.id, self.year_b_id)

        # معلم ۱۰: ۳ مثبت، ۲ منفی، ۱ خنثی روی سال A
        self._new_observation(self.profile1.id, self.teacher10, "مثبت")
        self._new_observation(self.profile1.id, self.teacher10, "مثبت")
        self._new_observation(self.profile1.id, self.teacher10, "مثبت")
        self._new_observation(self.profile1.id, self.teacher10, "منفی")
        self._new_observation(self.profile1.id, self.teacher10, "منفی")
        self._new_observation(self.profile1.id, self.teacher10, "خنثی")

        # معلم ۲۰: ۱ مثبت روی سال B
        self._new_observation(self.profile2.id, self.teacher20, "مثبت")

    def test_total_without_filter_counts_everything(self):
        stats = self.observation_dal.get_dashboard_stats()
        self.assertEqual(stats['total'], 7)
        self.assertEqual(stats['positive'], 4)
        self.assertEqual(stats['negative'], 2)
        self.assertEqual(stats['neutral'], 1)

    def test_filter_by_staff_id(self):
        stats = self.observation_dal.get_dashboard_stats(staff_id=self.teacher10)
        self.assertEqual(stats['total'], 6)
        self.assertEqual(stats['positive'], 3)
        self.assertEqual(stats['negative'], 2)
        self.assertEqual(stats['neutral'], 1)

    def test_filter_by_academic_year(self):
        stats_a = self.observation_dal.get_dashboard_stats(academic_year_id=self.year_a_id)
        self.assertEqual(stats_a['total'], 6)
        stats_b = self.observation_dal.get_dashboard_stats(academic_year_id=self.year_b_id)
        self.assertEqual(stats_b['total'], 1)

    def test_filter_by_staff_and_year_combined(self):
        stats = self.observation_dal.get_dashboard_stats(
            staff_id=self.teacher10, academic_year_id=self.year_a_id)
        self.assertEqual(stats['total'], 6)
        stats_none = self.observation_dal.get_dashboard_stats(
            staff_id=self.teacher10, academic_year_id=self.year_b_id)
        self.assertEqual(stats_none['total'], 0)

    def test_soft_deleted_observation_excluded(self):
        obs = self._new_observation(self.profile1.id, self.teacher10, "مثبت")
        before = self.observation_dal.get_dashboard_stats()['total']
        self.observation_dal.delete(obs.id, 1)
        after = self.observation_dal.get_dashboard_stats()['total']
        self.assertEqual(after, before - 1)

    def test_soft_deleted_profile_excluded_from_year_filter(self):
        """رگرسیون باگ: پروندهٔ حذف‌شده نباید در فیلتر سال شمرده شود"""
        before = self.observation_dal.get_dashboard_stats(academic_year_id=self.year_a_id)
        self.assertEqual(before['total'], 6)
        self.profile_dal.delete(self.profile1.id, 1)
        after = self.observation_dal.get_dashboard_stats(academic_year_id=self.year_a_id)
        self.assertEqual(after['total'], 0)
        # ولی بدون فیلتر سال، خودِ مشاهدات هنوز موجودند (فقط پروندهٔ سالانه حذف شده)
        unfiltered = self.observation_dal.get_dashboard_stats()
        self.assertEqual(unfiltered['total'], 7)


class TestObservationMonthlyTrend(DashboardAggregateTestBase):
    """ObservationDAL.get_monthly_trend — گروه‌بندی GROUP BY ماه"""

    def setUp(self):
        super().setUp()
        self.teacher30 = self._new_staff("معلم آزمون ۳۰")
        self.teacher99 = self._new_staff("معلم آزمون ۹۹")
        student = self._new_student("آگ‌روند", "8100000010")
        self.profile = self._new_profile(student.id, self.year_a_id)
        # فروردین: ۲ مثبت، ۱ منفی
        self._new_observation(self.profile.id, self.teacher30, "مثبت", date="1404/01/05")
        self._new_observation(self.profile.id, self.teacher30, "مثبت", date="1404/01/20")
        self._new_observation(self.profile.id, self.teacher30, "منفی", date="1404/01/28")
        # اردیبهشت: ۱ خنثی
        self._new_observation(self.profile.id, self.teacher30, "خنثی", date="1404/02/10")

    def test_monthly_buckets(self):
        trend = self.observation_dal.get_monthly_trend()
        self.assertEqual(trend["1404/01"]["count"], 3)
        self.assertEqual(trend["1404/01"]["positive"], 2)
        self.assertEqual(trend["1404/01"]["negative"], 1)
        self.assertEqual(trend["1404/01"]["neutral"], 0)
        self.assertEqual(trend["1404/02"]["count"], 1)
        self.assertEqual(trend["1404/02"]["neutral"], 1)

    def test_monthly_buckets_filtered_by_staff(self):
        self._new_observation(self.profile.id, self.teacher99, "مثبت", date="1404/01/15")
        trend_30 = self.observation_dal.get_monthly_trend(staff_id=self.teacher30)
        self.assertEqual(trend_30["1404/01"]["count"], 3)
        trend_99 = self.observation_dal.get_monthly_trend(staff_id=self.teacher99)
        self.assertEqual(trend_99["1404/01"]["count"], 1)

    def test_missing_month_has_no_key(self):
        trend = self.observation_dal.get_monthly_trend()
        self.assertNotIn("1404/03", trend)


class TestFollowUpDashboardStats(DashboardAggregateTestBase):
    """FollowUpDAL.get_dashboard_stats — شمارش کل/در-انتظار با یک کوئری"""

    def setUp(self):
        super().setUp()
        self.teacher40 = self._new_staff("معلم آزمون ۴۰")
        student1 = self._new_student("آگ‌پیگ۱", "8100000020")
        student2 = self._new_student("آگ‌پیگ۲", "8100000021")
        self.profile1 = self._new_profile(student1.id, self.year_a_id)
        self.profile2 = self._new_profile(student2.id, self.year_b_id)
        self.intervention1 = self._new_intervention(self.profile1.id, self.teacher40)
        self.intervention2 = self._new_intervention(self.profile2.id, self.teacher40)

        self._new_followup(self.intervention1.id, self.teacher40, status="pending")
        self._new_followup(self.intervention1.id, self.teacher40, status="pending")
        self._new_followup(self.intervention1.id, self.teacher40, status="done")
        self._new_followup(self.intervention2.id, self.teacher40, status="pending")

    def test_total_and_pending(self):
        stats = self.followup_dal.get_dashboard_stats()
        self.assertEqual(stats['total'], 4)
        self.assertEqual(stats['pending'], 3)

    def test_filter_by_academic_year_via_intervention_profile_chain(self):
        stats_a = self.followup_dal.get_dashboard_stats(academic_year_id=self.year_a_id)
        self.assertEqual(stats_a['total'], 3)
        self.assertEqual(stats_a['pending'], 2)
        stats_b = self.followup_dal.get_dashboard_stats(academic_year_id=self.year_b_id)
        self.assertEqual(stats_b['total'], 1)

    def test_soft_deleted_profile_excluded_from_year_filter(self):
        """رگرسیون باگ: پروندهٔ حذف‌شده نباید در فیلتر سال پیگیری‌ها شمرده شود"""
        self.profile_dal.delete(self.profile1.id, 1)
        stats_a = self.followup_dal.get_dashboard_stats(academic_year_id=self.year_a_id)
        self.assertEqual(stats_a['total'], 0)
        unfiltered = self.followup_dal.get_dashboard_stats()
        self.assertEqual(unfiltered['total'], 4)


class TestInterventionCountAllYearFilterBugfix(DashboardAggregateTestBase):
    """رگرسیون: InterventionDAL.count_all(academic_year_id=) نباید پروندهٔ حذف‌شده را بشمارد"""

    def test_soft_deleted_profile_excluded(self):
        teacher50 = self._new_staff("معلم آزمون ۵۰")
        student = self._new_student("آگ‌مدا", "8100000030")
        profile = self._new_profile(student.id, self.year_a_id)
        self._new_intervention(profile.id, teacher50)
        self._new_intervention(profile.id, teacher50)

        before = self.intervention_dal.count_all(academic_year_id=self.year_a_id)
        self.assertEqual(before, 2)

        self.profile_dal.delete(profile.id, 1)
        after = self.intervention_dal.count_all(academic_year_id=self.year_a_id)
        self.assertEqual(after, 0)
        # بدون فیلتر سال، خودِ مداخلات هنوز موجودند
        self.assertEqual(self.intervention_dal.count_all(), 2)


class TestDashboardServiceEndToEnd(DashboardAggregateTestBase):
    """
    services/dashboard_service.py — آزمون سرتاسری با دیتاست ثابت

    اطمینان از این‌که بعد از تعویضِ get_all()←Aggregate SQL، اعداد نهاییِ
    _get_general_stats/_get_observation_trend/_get_teacher_stats با
    محاسبهٔ دستیِ روی همان فیکسچر یکی است.
    """

    def setUp(self):
        super().setUp()
        self.teacher60 = self._new_staff("معلم آزمون ۶۰")
        self.teacher70 = self._new_staff("معلم آزمون ۷۰")
        student1 = self._new_student("سرتاسری۱", "8100000040")
        student2 = self._new_student("سرتاسری۲", "8100000041")
        self.profile1 = self._new_profile(student1.id, self.year_a_id)
        self.profile2 = self._new_profile(student2.id, self.year_a_id)

        # معلم ۶۰: ۲ مشاهدهٔ مثبت + ۱ منفی، ۱ مداخله، ۲ پیگیری (۱ pending)
        self._new_observation(self.profile1.id, self.teacher60, "مثبت")
        self._new_observation(self.profile1.id, self.teacher60, "مثبت")
        self._new_observation(self.profile1.id, self.teacher60, "منفی")
        inter60 = self._new_intervention(self.profile1.id, self.teacher60)
        self._new_followup(inter60.id, self.teacher60, status="pending")
        self._new_followup(inter60.id, self.teacher60, status="done")

        # معلم ۷۰: ۱ مشاهدهٔ مثبت، ۱ مداخله، ۱ پیگیری pending
        self._new_observation(self.profile2.id, self.teacher70, "مثبت")
        inter70 = self._new_intervention(self.profile2.id, self.teacher70)
        self._new_followup(inter70.id, self.teacher70, status="pending")

        from services.dashboard_service import DashboardService
        self.service = DashboardService()

    def test_general_stats_school_wide(self):
        stats = self.service._get_general_stats(teacher_id=None, year_id=self.year_a_id)
        self.assertEqual(stats['observations_count'], 4)
        self.assertEqual(stats['positive_count'], 3)
        self.assertEqual(stats['negative_count'], 1)
        self.assertEqual(stats['neutral_count'], 0)
        self.assertEqual(stats['interventions_count'], 2)
        self.assertEqual(stats['followups_count'], 3)
        self.assertEqual(stats['pending_followups'], 2)
        self.assertTrue(stats['has_data'])

    def test_general_stats_filtered_by_teacher(self):
        stats = self.service._get_general_stats(teacher_id=self.teacher60, year_id=self.year_a_id)
        self.assertEqual(stats['observations_count'], 3)
        self.assertEqual(stats['positive_count'], 2)
        self.assertEqual(stats['negative_count'], 1)
        self.assertEqual(stats['interventions_count'], 1)
        self.assertEqual(stats['followups_count'], 2)
        self.assertEqual(stats['pending_followups'], 1)

    def test_teacher_stats(self):
        stats = self.service._get_teacher_stats(self.teacher60, year_id=self.year_a_id)
        self.assertEqual(stats['observations_count'], 3)
        self.assertAlmostEqual(stats['positive_percent'], 66.7, places=1)
        self.assertEqual(stats['interventions_count'], 1)
        # نکتهٔ رفتار قدیمیِ حفظ‌شده: followups در _get_teacher_stats بدون فیلتر سال
        self.assertEqual(stats['followups_count'], 2)
        self.assertEqual(stats['pending_followups'], 1)

    def test_observation_trend_current_month_bucket(self):
        import jdatetime
        today_key = jdatetime.date.today().strftime("%Y/%m")
        # فیکسچر با تاریخ پیش‌فرض 1404/01/01 ثبت شده بود؛ برای این‌که روند
        # قابل‌پیش‌بینی باشد، یک مشاهدهٔ تازه با تاریخ «امروز» اضافه می‌کنیم
        self._new_observation(self.profile1.id, self.teacher60, "مثبت",
                               date=jdatetime.date.today().strftime("%Y/%m/%d"))
        trend = self.service._get_observation_trend(teacher_id=self.teacher60, year_id=self.year_a_id)
        self.assertIn(today_key, trend['months'])
        idx = trend['months'].index(today_key)
        self.assertGreaterEqual(trend['counts'][idx], 1)
        self.assertEqual(trend['total'], sum(trend['counts']))


if __name__ == "__main__":
    unittest.main()
