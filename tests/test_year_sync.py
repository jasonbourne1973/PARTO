"""
تست‌های همگام‌سازی «سال تحصیلی فعال» (بازبینی نهایی — BUG-GUI-12 / NAV-04/05/06)

این تست‌ها قرارداد جدید را قفل می‌کنند:

  • `MainWindow.set_active_year(year_id)` تنها مسیر تغییر سال فعال است و
    صفحه‌های وابسته به سال با متد صریح `set_active_year` همگام می‌شوند
    (نه با اسکن بازتابی نام متدهای `load_*`).
  • صفحه‌های وابسته، «سال اعلام‌شده» را می‌خوانند و اگر سال فعال دیتابیس
    چیز دیگری باشد، همان انتخاب صریح معتبر است (بدون حدس زدن).
  • ساختار کد در `views/pages/year_sync.py` مشترک است: انتخاب سال در کامبو
    بدون فرستادن سیگنال (تا حلقهٔ بازگشتی و بارگذاری چندباره رخ ندهد).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.academic_year_dal import AcademicYearDAL
from models.academic_year import AcademicYear
from views.pages.year_sync import YearAwarePage, select_year_in_combo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FakeCombo:
    """کمبوی سبک با همان قرارداد QComboBox (بدون نیاز به Qt)"""

    def __init__(self, items):
        self._items = list(items)
        self._index = 0 if self._items else -1
        self.signals_blocked = 0
        self.blocked_during_set = False

    def blockSignals(self, flag):
        self.signals_blocked = 1 if flag else 0

    def count(self):
        return len(self._items)

    def itemData(self, index):
        return self._items[index][1]

    def currentIndex(self):
        return self._index

    def setCurrentIndex(self, index):
        # انتخاب سال باید «بدون سیگنال» باشد؛ اینجا فقط ثبت می‌شود که
        # در لحظهٔ انتخاب، سیگنال‌ها قفل بوده‌اند.
        self.blocked_during_set = bool(self.signals_blocked)
        self._index = index

    def addItem(self, text, data):
        self._items.append((text, data))
        if self._index < 0:
            self._index = 0

    def currentData(self):
        if 0 <= self._index < len(self._items):
            return self._items[self._index][1]
        return None


class FakeYearDAL:
    """DAL سبک سال تحصیلی با سال فعال قابل تنظیم"""

    def __init__(self, active_id):
        self.active_id = active_id
        self.lookups = []

    def get_by_id(self, year_id):
        self.lookups.append(year_id)
        if year_id is None:
            return None
        year = AcademicYear()
        year.id = year_id
        year.title = f"سال {year_id}"
        return year

    def get_active(self):
        if self.active_id is None:
            return None
        return self.get_by_id(self.active_id)


class ProbePage(YearAwarePage):
    """صفحهٔ ساختگی: فقط بارگذاری‌ها و کامبوی سال را می‌شمارد"""

    def __init__(self, active_id=1, combo_years=None):
        self.academic_year_dal = FakeYearDAL(active_id)
        self.year_combo = FakeCombo([(f"سال {y}", y) for y in (combo_years or [1])])
        self.reloads = []
        self.year_list_loads = 0

    def load_academic_years(self):
        self.year_list_loads += 1
        known = {data for _, data in self.year_combo._items}
        for year in (1, 2, 3):
            if year not in known:
                self.year_combo.addItem(f"سال {year}", year)

    def reload_for_year(self, year_id):
        self.reloads.append(year_id)
        return True


class TestYearSyncHelpers(unittest.TestCase):
    """کمک‌تابع‌های مشترک همگام‌سازی سال"""

    def test_select_year_in_combo_selects_without_signal(self):
        combo = FakeCombo([("a", 1), ("b", 2)])
        self.assertTrue(select_year_in_combo(combo, 2))
        self.assertEqual(combo.currentData(), 2)
        self.assertTrue(combo.blocked_during_set)      # انتخاب بدون سیگنال
        self.assertEqual(combo.signals_blocked, 0)     # قفل پس از پایان برداشته می‌شود

    def test_select_year_in_combo_reports_missing_year(self):
        combo = FakeCombo([("a", 1)])
        self.assertFalse(select_year_in_combo(combo, 99))
        self.assertEqual(combo.currentData(), 1)  # انتخاب قبلی دست‌نخورده

    def test_select_year_in_combo_handles_none(self):
        combo = FakeCombo([("همه سال‌ها", None), ("a", 1)])
        combo.setCurrentIndex(1)
        self.assertTrue(select_year_in_combo(combo, None))
        self.assertIsNone(combo.currentData())


class TestYearAwarePage(unittest.TestCase):
    """رفتار مشترک صفحه‌های وابسته به سال"""

    def test_set_active_year_syncs_combo_and_reloads(self):
        page = ProbePage(active_id=1, combo_years=[1, 2])
        self.assertTrue(page.set_active_year(2))
        self.assertEqual(page.active_year_id, 2)
        self.assertEqual(page.year_combo.currentData(), 2)
        self.assertEqual(page.reloads, [2])

    def test_missing_year_is_refreshed_then_selected(self):
        """سالی که پس از ساخت صفحه اضافه شده، ابتدا از DB خوانده می‌شود"""
        page = ProbePage(active_id=1, combo_years=[1])
        self.assertTrue(page.set_active_year(3))
        self.assertTrue(page.year_list_loads >= 1)
        self.assertEqual(page.year_combo.currentData(), 3)
        self.assertEqual(page.reloads, [3])

    def test_effective_year_prefers_explicit_selection(self):
        page = ProbePage(active_id=1)
        page.set_active_year(2)
        self.assertEqual(page.effective_year().id, 2)

    def test_effective_year_falls_back_to_db_active(self):
        page = ProbePage(active_id=1)
        self.assertEqual(page.effective_year().id, 1)
        self.assertEqual(page.year_combo.currentData(), 1)

    def test_effective_year_without_dal_is_none(self):
        class NoDal(YearAwarePage):
            def reload_for_year(self, year_id):
                return True

        page = NoDal()
        page.active_year_id = 3
        self.assertIsNone(page.effective_year())


class TestYearSyncWiring(unittest.TestCase):
    """سیم‌کشی تک‌منبع حقیقت در کد (بدون ساخت پنجره)"""

    def _read(self, rel_path):
        with open(os.path.join(ROOT, rel_path), encoding="utf-8") as handle:
            return handle.read()

    def test_main_window_has_no_reflection_reload(self):
        src = self._read("views/main_window.py")
        self.assertNotIn("import inspect", src)
        self.assertIn("def set_active_year", src)
        self.assertIn("academic_year_changed.connect(self._sync_pages_for_year)", src)

    def test_all_year_pages_are_year_aware(self):
        pages = (
            "dashboard_page", "students_page", "observations_page",
            "interventions_page", "followups_page", "indicators_page",
            "analysis_page", "reports_page", "academic_structure_page",
            "counseling_page", "activities_page", "goals_page", "settings_page",
        )
        missing = []
        for name in pages:
            src = self._read(f"views/pages/{name}.py")
            if "YearAwarePage" not in src or "def reload_for_year" not in src:
                missing.append(name)
        self.assertEqual(missing, [])

    def test_year_aware_page_list_is_explicit(self):
        src = self._read("views/main_window.py")
        block = src[src.index("def _year_aware_pages"):src.index("def _sync_pages_for_year")]
        for name in ("dashboard_page", "students_page", "indicators_page",
                     "reports_page", "settings_page"):
            self.assertIn(f'"{name}"', block)
        # اسکن بازتابی نام متدها نباید برگردد
        self.assertNotIn("dir(page)", block)
        self.assertNotIn("signature(", block)

    def test_pages_do_not_guess_active_year_for_free_pages(self):
        """صفحه‌های وابسته، سال مؤثر را از effective_year می‌گیرند"""
        for name in ("observations_page", "interventions_page", "followups_page",
                     "activities_page", "counseling_page", "goals_page"):
            src = self._read(f"views/pages/{name}.py")
            self.assertNotIn("self.academic_year_dal.get_active()", src)
            self.assertIn("self.effective_year()", src)

    def test_no_new_guess_in_selected_year_when_missing(self):
        """در صفحهٔ پرونده، انتخاب سال صریح است و از سال دیگر جایگزین نمی‌شود"""
        src = self._read("views/pages/student_profile_page.py")
        self.assertIn("def reload_for_year", src)
        self.assertIn("self.selected_year_id = year_id", src)
        self.assertIn("self.profile_dal.get_by_student_and_year(", src)
        block = src[src.index("def load_student_data"):src.index("def load_timeline")]
        self.assertIn("if self.selected_year_id:", block)
        self.assertIn("سال دیگری نباید به‌عنوان جایگزین", block)
        # در انتخاب صریح سال، هیچ فراخوانی get_active_by_student در بدنهٔ
        # همان شاخه نباید وجود داشته باشد (فقط شاخهٔ «بدون انتخاب»).
        selected_branch = block[block.index("if self.selected_year_id:"):block.index("else:")]
        self.assertNotIn("get_active_by_student", selected_branch)


class TestYearSyncAgainstDatabase(unittest.TestCase):
    """همگام‌سازی با دیتابیس واقعی (موقت) — بدون Qt"""

    def setUp(self):
        self.dal = AcademicYearDAL()
        self.active = self.dal.get_active()
        if self.active is None:
            self.skipTest("سال تحصیلی فعالی وجود ندارد")

    def test_explicit_selection_wins_over_db_active(self):
        year = AcademicYear()
        year.title = "1999-2000"
        year.start_date = "1999/07/01"
        year.end_date = "2000/06/30"
        year.is_active = 0
        year.is_archived = 0
        created = self.dal.create(year)
        try:
            page = ProbePage(active_id=self.active.id)
            page.academic_year_dal = self.dal
            page.set_active_year(created.id)
            self.assertEqual(page.effective_year().id, created.id)
            # سال فعال دیتابیس دست‌نخورده است: همگام‌سازی صفحه‌ها به‌تنهایی
            # حق تغییر سال فعال را ندارد.
            self.assertEqual(self.dal.get_active().id, self.active.id)
        finally:
            self.dal.delete(created.id)


def run_tests():
    """اجرای همهٔ تست‌های این فایل"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for case in (TestYearSyncHelpers, TestYearAwarePage, TestYearSyncWiring,
                 TestYearSyncAgainstDatabase):
        suite.addTest(loader.loadTestsFromTestCase(case))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 50)
    print("📊 خلاصه تست‌های همگام‌سازی سال:")
    print(f"  • اجرا شده: {result.testsRun}")
    print(f"  • موفق: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  • ناموفق: {len(result.failures)}")
    print(f"  • خطا: {len(result.errors)}")
    print("=" * 50)

    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_tests() else 1)
