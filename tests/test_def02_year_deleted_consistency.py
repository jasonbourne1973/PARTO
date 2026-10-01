"""
آزمون‌های DEF-02 (ممیزی تکمیلی، دور بیستم — فاز ۲)

پوشش: «پروندهٔ سالانهٔ حذف‌شده نباید در فیلترِ سالِ تحصیلی شمرده شود».

پیش از این فاز، این قاعده فقط در ObservationDAL.get_all/count_all و
InterventionDAL.get_all/count_all و FollowUpDAL._base_filters رعایت
می‌شد (دور نوزدهم، مرحلهٔ ۷). این فاز همان قاعده را به محل‌های زیر که
عقب افتاده بودند تعمیم داد:

  • ObservationDAL.get_by_student() / _search_where()  (منبعِ صریحِ DEF-02)
  • InterventionDAL.get_by_student() / _search_where()  (منبعِ صریحِ DEF-02)
  • FollowUpDAL._search_where()
  • ObservationDAL.get_trend_by_class()  — یافتهٔ جانبی: پارامتر
    academic_year_id اصلاً در کوئری استفاده نمی‌شد (نه فقط یک ناسازگاریِ
    is_deleted، بلکه یک فیلترِ کاملاً بی‌اثر — گزارش کلاس همیشه روند
    همهٔ سال‌ها را نشان می‌داد).
  • services/class_report_service.py — _get_class_intervention_stats /
    _get_class_followup_stats

توجه (یافتهٔ منفی، ثبت‌شده برای شفافیت): دو محل دیگر که در ابتدا مشکوک
به همین الگو به نظر می‌رسیدند بررسی و رد شدند، چون به‌خاطر
UNIQUE(student_id, academic_year_id) در سطح جدول student_academic_profiles
(بدون فیلتر is_deleted)، سناریوی «دو ردیف پروندهٔ هم‌سال برای یک
دانش‌آموز — یکی حذف‌شده یکی فعال» ساختاراً غیرممکن است؛ پس افزودنِ
sap.is_deleted=0 در آن دو محل هیچ‌وقت نتیجه را تغییر نمی‌دهد (کد مرده):
  • dal/class_dal.py: get_class_observations_stats /
    get_class_competency_stats / get_class_student_stats (کوئریِ دومِ
    هرکدام که obs_query نام دارد)
  • dal/student_dal.py: get_students_without_observations (زیرکوئریِ
    NOT EXISTS با sap2) — بدون تغییر کد ماند؛ دلیل در کامنتِ کنار همان
    خط مستند شده.

هر تست روی دیتابیس موقت تازه اجرا می‌شود (از HardDeleteRestoreTestBase در
tests/test_hard_delete_restore_edge.py استفاده می‌شود).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_hard_delete_restore_edge import HardDeleteRestoreTestBase


class Def02TestBase(HardDeleteRestoreTestBase):
    """پایهٔ مشترک: یک دانش‌آموز با پروندهٔ سالِ جاری + مشاهده/مداخله روی آن"""

    def _make_student_with_profile(self, national_code, class_name="اول-الف"):
        student = self._new_student("آزمونDEF02", national_code)
        profile = self._new_profile(student.id)
        profile.class_name = class_name
        self.profile_dal.update(profile)
        return student, profile


# ================================================================
# ObservationDAL.get_by_student(student_id, academic_year_id)
# ================================================================

class TestObservationGetByStudentYearDeletedProfile(Def02TestBase):
    def test_included_while_profile_active(self):
        student, profile = self._make_student_with_profile("9600000101")
        self._new_observation(profile.id)
        result = self.observation_dal.get_by_student(student.id, academic_year_id=self.year_id)
        self.assertEqual(len(result), 1)

    def test_excluded_after_profile_soft_deleted(self):
        """(DEF-02) پروندهٔ حذف‌شده نباید در فیلتر سال شمرده شود"""
        student, profile = self._make_student_with_profile("9600000102")
        self._new_observation(profile.id)
        self.profile_dal.delete(profile.id, 1)

        result = self.observation_dal.get_by_student(student.id, academic_year_id=self.year_id)
        self.assertEqual(result, [])

        # سازگاری با get_all/count_all که از قبل همین قاعده را داشتند
        all_result = self.observation_dal.get_all(academic_year_id=self.year_id)
        self.assertEqual(
            [o for o in all_result if o.student_profile_id == profile.id], []
        )

    def test_without_year_filter_unaffected(self):
        """بدون فیلتر سال، رفتار قبلی حفظ می‌شود (خارج از دامنهٔ DEF-02)"""
        student, profile = self._make_student_with_profile("9600000103")
        self._new_observation(profile.id)
        result = self.observation_dal.get_by_student(student.id)
        self.assertEqual(len(result), 1)


# ================================================================
# InterventionDAL.get_by_student(student_id, academic_year_id)
# ================================================================

class TestInterventionGetByStudentYearDeletedProfile(Def02TestBase):
    def test_included_while_profile_active(self):
        student, profile = self._make_student_with_profile("9600000201")
        self._new_intervention(profile.id)
        result = self.intervention_dal.get_by_student(student.id, academic_year_id=self.year_id)
        self.assertEqual(len(result), 1)

    def test_excluded_after_profile_soft_deleted(self):
        student, profile = self._make_student_with_profile("9600000202")
        self._new_intervention(profile.id)
        self.profile_dal.delete(profile.id, 1)

        result = self.intervention_dal.get_by_student(student.id, academic_year_id=self.year_id)
        self.assertEqual(result, [])

        all_result = self.intervention_dal.get_all(academic_year_id=self.year_id)
        self.assertEqual(
            [i for i in all_result if i.student_profile_id == profile.id], []
        )


# ================================================================
# _search_where — Observation / Intervention / FollowUp
# ================================================================

class TestSearchYearDeletedProfile(Def02TestBase):
    def test_observation_search_excludes_deleted_profile_year(self):
        _student, profile = self._make_student_with_profile("9600000301")
        obs = self._new_observation(profile.id)
        obs.description = "واژهٔ-یکتای-آزمون-الف"
        self.observation_dal.update(obs)

        found = self.observation_dal.search(
            "واژهٔ-یکتای-آزمون-الف", academic_year_id=self.year_id)
        self.assertEqual(len(found), 1)

        self.profile_dal.delete(profile.id, 1)
        found_after = self.observation_dal.search(
            "واژهٔ-یکتای-آزمون-الف", academic_year_id=self.year_id)
        self.assertEqual(found_after, [])

    def test_intervention_search_excludes_deleted_profile_year(self):
        _student, profile = self._make_student_with_profile("9600000302")
        inter = self._new_intervention(profile.id)
        inter.description = "واژهٔ-یکتای-آزمون-ب"
        self.intervention_dal.update(inter)

        found = self.intervention_dal.search(
            "واژهٔ-یکتای-آزمون-ب", academic_year_id=self.year_id)
        self.assertEqual(len(found), 1)

        self.profile_dal.delete(profile.id, 1)
        found_after = self.intervention_dal.search(
            "واژهٔ-یکتای-آزمون-ب", academic_year_id=self.year_id)
        self.assertEqual(found_after, [])

    def test_followup_search_excludes_deleted_profile_year(self):
        _student, profile = self._make_student_with_profile("9600000303")
        inter = self._new_intervention(profile.id)
        follow = self._new_followup(inter.id)
        follow.description = "واژهٔ-یکتای-آزمون-ج"
        self.followup_dal.update(follow)

        found = self.followup_dal.search(
            "واژهٔ-یکتای-آزمون-ج", academic_year_id=self.year_id)
        self.assertEqual(len(found), 1)

        self.profile_dal.delete(profile.id, 1)
        found_after = self.followup_dal.search(
            "واژهٔ-یکتای-آزمون-ج", academic_year_id=self.year_id)
        self.assertEqual(found_after, [])


# ================================================================
# ObservationDAL.get_trend_by_class — یافتهٔ جانبی: academic_year_id
# قبلاً کاملاً بی‌اثر بود (نه فقط ناسازگاریِ is_deleted)
# ================================================================

class TestObservationTrendByClassYearFilter(Def02TestBase):
    def test_year_filter_now_actually_applied(self):
        """
        قبل از این فاز، academic_year_id در امضای متد وجود داشت ولی هرگز
        در کوئری استفاده نمی‌شد؛ یعنی روند همیشه شامل «همهٔ سال‌ها» بود.
        این تست ثابت می‌کند از این پس فیلتر واقعاً اثر دارد: مشاهدهٔ
        متعلق به سال دیگر نباید در روند سالِ درخواستی شمرده شود.
        """
        from dal.academic_year_dal import AcademicYearDAL
        from models.academic_year import AcademicYear

        other_year = AcademicYear()
        other_year.title = "سال آزمون دیگر ۱۴۰۳-۱۴۰۴"
        other_year.start_date = "1403/07/01"
        other_year.end_date = "1404/03/31"
        other_year.is_active = 0
        other_year_id = AcademicYearDAL().create(other_year).id

        student, profile_y1 = self._make_student_with_profile(
            "9600000401", class_name="روند-کلاس")
        obs1 = self._new_observation(profile_y1.id)
        obs1.observation_date = "1404/01/01"
        self.observation_dal.update(obs1)

        profile_y2 = self._new_profile(student.id, academic_year_id=other_year_id)
        profile_y2.class_name = "روند-کلاس"
        self.profile_dal.update(profile_y2)
        obs2 = self._new_observation(profile_y2.id)
        obs2.observation_date = "1403/07/10"
        self.observation_dal.update(obs2)

        # بدون فیلتر سال: هر دو مشاهده باید در روند دیده شوند (رفتار قبلی).
        trend_all = self.observation_dal.get_trend_by_class("روند-کلاس")
        total_all = sum(p["total"] for p in trend_all)
        self.assertEqual(total_all, 2)

        # با فیلتر سال جاری: فقط مشاهدهٔ همان سال باید شمرده شود.
        trend_y1 = self.observation_dal.get_trend_by_class(
            "روند-کلاس", academic_year_id=self.year_id)
        total_y1 = sum(p["total"] for p in trend_y1)
        self.assertEqual(total_y1, 1)

        # با فیلتر سالِ دیگر: فقط مشاهدهٔ آن سال.
        trend_y2 = self.observation_dal.get_trend_by_class(
            "روند-کلاس", academic_year_id=other_year_id)
        total_y2 = sum(p["total"] for p in trend_y2)
        self.assertEqual(total_y2, 1)

    def test_deleted_profile_excluded_from_year_filtered_trend(self):
        _student, profile = self._make_student_with_profile(
            "9600000402", class_name="روند-کلاس-۲")
        obs = self._new_observation(profile.id)
        obs.observation_date = "1404/01/01"
        self.observation_dal.update(obs)

        trend_before = self.observation_dal.get_trend_by_class(
            "روند-کلاس-۲", academic_year_id=self.year_id)
        self.assertEqual(sum(p["total"] for p in trend_before), 1)

        self.profile_dal.delete(profile.id, 1)
        trend_after = self.observation_dal.get_trend_by_class(
            "روند-کلاس-۲", academic_year_id=self.year_id)
        self.assertEqual(sum(p["total"] for p in trend_after), 0)


# ================================================================
# services/class_report_service.py — آمار مداخلات/پیگیریِ کلاس
# ================================================================

class TestClassReportServiceYearDeletedProfile(Def02TestBase):
    def setUp(self):
        super().setUp()
        from services.class_report_service import ClassReportService
        self.report_service = ClassReportService()

    def test_intervention_stats_excludes_deleted_profile_year(self):
        _student, profile = self._make_student_with_profile(
            "9600000601", class_name="کلاس-گزارش-۱")
        self._new_intervention(profile.id)

        stats_before = self.report_service._get_class_intervention_stats(
            "کلاس-گزارش-۱", self.year_id)
        self.assertEqual(stats_before["total"], 1)

        self.profile_dal.delete(profile.id, 1)
        stats_after = self.report_service._get_class_intervention_stats(
            "کلاس-گزارش-۱", self.year_id)
        self.assertEqual(stats_after["total"], 0)

    def test_followup_stats_excludes_deleted_profile_year(self):
        _student, profile = self._make_student_with_profile(
            "9600000602", class_name="کلاس-گزارش-۲")
        inter = self._new_intervention(profile.id)
        self._new_followup(inter.id)

        stats_before = self.report_service._get_class_followup_stats(
            "کلاس-گزارش-۲", self.year_id)
        self.assertEqual(stats_before["total"], 1)

        self.profile_dal.delete(profile.id, 1)
        stats_after = self.report_service._get_class_followup_stats(
            "کلاس-گزارش-۲", self.year_id)
        self.assertEqual(stats_after["total"], 0)

    def test_followup_stats_excludes_deleted_parent_intervention(self):
        """یافتهٔ جانبی: پیگیریِ زیرِ مداخلهٔ حذف‌شده هم نباید شمرده شود
        (هم‌راستا با FollowUpDAL که همه‌جا i.is_deleted=0 را هم چک می‌کند)"""
        _student, profile = self._make_student_with_profile(
            "9600000603", class_name="کلاس-گزارش-۳")
        inter = self._new_intervention(profile.id)
        self._new_followup(inter.id)

        self.intervention_dal.delete(inter.id, 1)
        stats_after = self.report_service._get_class_followup_stats(
            "کلاس-گزارش-۳", self.year_id)
        self.assertEqual(stats_after["total"], 0)


if __name__ == "__main__":
    unittest.main()
