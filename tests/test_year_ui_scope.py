"""
آزمون‌های مرحلهٔ ۳ دور هجدهم — سال و UI (بندهای ۶، ۷، ۲۶، ۳۱)

پوشش مأموریت:
  • BUG-GUI-13 — تغییر سال در شاخص‌ها/تحلیل باید «فهرست + پنل نتایج» را
    با همان سال تازه کند (نمایش کهنهٔ سال قبلی ممنوع).
  • BUG-GUI-07/08 — پایهٔ فهرست دانش‌آموزان شاخص‌ها/تحلیل باید از
    «سال انتخاب‌شده» بیاید نه پروندهٔ فعال؛ دانش‌آموز بدون پرونده در
    آن سال فهرست نمی‌شود (نه fallback به سال فعال).
  • BUG-NAV-07 — ایندکس ناوبری فقط از نگاشت مرکزی PAGE_INDEX.
  • BUG-GUI-01 — کنتراست نام/آیکون کاربر سایدبار (محاسباتی؛ §C
    verify_fixes18 برای هدر اصلی).

نکتهٔ ایزوله‌سازی: هر کلاس دیتابیس موقت خودش را می‌سازد؛ سال‌های
۱۴۰۳/۱۴۰۴ با داده‌های عمداً متفاوت و پروندهٔ فعال در سال دوم.
"""

import contextlib
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# صفحه‌های Qt (IndicatorsPage/AnalysisPage) به QApplication نیاز دارند؛
# این فایل فقط با همین دو متغیر محیطی اجرا می‌شود (مستند در سند دور ۱۸):
#   LD_LIBRARY_PATH=<qtstub> QT_QPA_PLATFORM=offscreen python -m pytest
from PySide6.QtWidgets import QApplication

import database.connection as _dbc
from config import settings as _settings

_QAPP = QApplication.instance() or QApplication(sys.argv)


def _reset_db(tmpdir):
    _settings.DB_PATH = os.path.join(tmpdir, "partow.db")
    _dbc.DB_PATH = _settings.DB_PATH
    _dbc.DatabaseConnection._instance = None
    _dbc.DatabaseConnection._connection = None
    _dbc.DatabaseConnection._initialized = False


class BaseYearIsolation(unittest.TestCase):
    """سال ۱۴۰۳ (پروندهٔ دانش‌آموز A) و ۱۴۰۴ (پروندهٔ دانش‌آموز B)"""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="partow_year_ui_")
        self._saved = (_settings.DB_PATH, _dbc.DB_PATH)
        _reset_db(self._tmpdir)
        with contextlib.redirect_stdout(io.StringIO()):
            _dbc.DatabaseConnection()
        self._seed_two_years()

    def tearDown(self):
        with contextlib.suppress(Exception):
            _dbc.DatabaseConnection().close_all()
        _settings.DB_PATH, _dbc.DB_PATH = self._saved
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False

    def _seed_two_years(self):
        from dal.academic_year_dal import AcademicYearDAL
        from dal.student_academic_profile_dal import StudentAcademicProfileDAL
        from dal.student_dal import StudentDAL
        from models.academic_year import AcademicYear
        from models.student_academic_profile import StudentAcademicProfile

        self.year_dal = AcademicYearDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()

        year_1403 = AcademicYear()
        year_1403.title = "۱۴۰۳-۱۴۰۴"
        year_1403.start_date = "1403/07/01"
        year_1403.end_date = "1404/06/30"
        self.year_1403 = self.year_dal.create(year_1403)

        year_1404 = AcademicYear()
        year_1404.title = "۱۴۰۴-۱۴۰۵"
        year_1404.start_date = "1404/07/01"
        year_1404.end_date = "1405/06/30"
        self.year_1404 = self.year_dal.create(year_1404)
        self.year_dal.set_active(self.year_1404.id)  # سال فعال = ۱۴۰۴

        # دانش‌آموز A فقط پروندهٔ ۱۴۰۳؛ دانش‌آموز B فقط ۱۴۰۴
        self.student_a = self.student_dal.create(self._student("علی", "الف", "1111111111"))
        self.student_b = self.student_dal.create(self._student("رضا", "ب", "2222222222"))

        profile_a = StudentAcademicProfile()
        profile_a.student_id = self.student_a.id
        profile_a.academic_year_id = self.year_1403.id
        profile_a.grade = 3
        profile_a.class_name = "سوم-الف"
        profile_a.status = "active"
        self.profile_a = self.profile_dal.create(profile_a)

        profile_b = StudentAcademicProfile()
        profile_b.student_id = self.student_b.id
        profile_b.academic_year_id = self.year_1404.id
        profile_b.grade = 1
        profile_b.class_name = "اول-ب"
        profile_b.status = "active"
        self.profile_b = self.profile_dal.create(profile_b)

    @staticmethod
    def _student(first, last, national_code):
        student = __import__(
            "models.student", fromlist=["Student"]).Student()
        student.first_name = first
        student.last_name = last
        student.national_code = national_code
        return student


class TestIndicatorListingYearScope(BaseYearIsolation):
    """BUG-GUI-07: پایهٔ فهرست شاخص‌ها از سال انتخاب‌شده"""

    def _make_page(self):
        with contextlib.redirect_stdout(io.StringIO()):
            from views.pages.indicators_page import IndicatorsPage
            return IndicatorsPage()

    def test_year_1403_lists_only_a_with_its_grade(self):
        page = self._make_page()
        self._select_year(page, self.year_1403.id)
        page.load_students_for_teacher()

        data = self._combo_students(page)
        self.assertIn(self.student_a.id, data, "A باید در فهرست ۱۴۰۳ باشد")
        self.assertNotIn(self.student_b.id, data, "B نباید در فهرست ۱۴۰۳ باشد")

        # پایهٔ نمایش‌داده‌شده باید پایهٔ پروندهٔ ۱۴۰۳ باشد (نه فعال)
        row = self._row_of(page, self.student_a.id)
        self.assertIn("سوم", row,
                      "پایهٔ نمایشی باید از پروندهٔ ۱۴۰۳ بیاید (پایهٔ فعال A دیگر نیست)")

    def test_year_1404_lists_only_b_with_its_grade(self):
        page = self._make_page()
        self._select_year(page, self.year_1404.id)
        page.load_students_for_teacher()

        data = self._combo_students(page)
        self.assertIn(self.student_b.id, data)
        self.assertNotIn(self.student_a.id, data)

        row = self._row_of(page, self.student_b.id)
        self.assertIn("اول", row)

    def test_all_years_keeps_current_behaviour_without_grade_leak(self):
        """
        حالت «همه سال‌ها»: رفتار فعلی حفظ می‌شود (همهٔ دانش‌آموزان
        فهرست می‌شوند)؛ مهم این است که پایهٔ نمایشیِ دانش‌آموزِ
        بی‌پروندهٔ فعال از پروندهٔ تاریخی سال دیگر «نشت» نکند.
        """
        page = self._make_page()
        self._select_year(page, None)
        page.load_students_for_teacher()
        data = self._combo_students(page)
        self.assertIn(self.student_b.id, data)
        # پایهٔ B باید پایهٔ فعال (۱۴۰۴) باشد
        self.assertIn("اول", self._row_of(page, self.student_b.id))
        # اگر A فهرست شد، پایه‌اش نباید «سوم» (پروندهٔ ۱۴۰۳) باشد؛
        # پایهٔ فعال A وجود ندارد → «نامشخص»
        if self.student_a.id in data:
            self.assertNotIn(
                "سوم", self._row_of(page, self.student_a.id),
                "پایهٔ پروندهٔ تاریخی ۱۴۰۳ نباید در فهرست «همه سال‌ها» بیاید")

    def test_no_fallback_to_active_year_when_listing_1403(self):
        """هیچ‌وقت نباید پایهٔ ۱۴۰۴ (سال فعال DB) به فهرست ۱۴۰۳ نشت کند"""
        page = self._make_page()
        self._select_year(page, self.year_1403.id)
        page.load_students_for_teacher()
        data = self._combo_students(page)
        self.assertNotIn(
            self.student_b.id, data,
            "B با پروندهٔ سال فعال (۱۴۰۴) نباید در فهرست ۱۴۰۳ باشد")

    # ---------- کمکی ----------

    @staticmethod
    def _select_year(page, year_id):
        for i in range(page.year_combo.count()):
            if page.year_combo.itemData(i) == year_id:
                page.year_combo.blockSignals(True)
                page.year_combo.setCurrentIndex(i)
                page.year_combo.blockSignals(False)
                return
        raise AssertionError(f"سال {year_id} در کامبو نیست")

    @staticmethod
    def _combo_students(page):
        return [page.student_combo.itemData(i)
                for i in range(page.student_combo.count())]

    @staticmethod
    def _row_of(page, student_id):
        for i in range(page.student_combo.count()):
            if page.student_combo.itemData(i) == student_id:
                return page.student_combo.itemText(i)
        raise AssertionError("دانش‌آموز در کامبو نیست")


class TestYearChangeClearsStalePanel(BaseYearIsolation):
    """BUG-GUI-13: تغییر سال پنل نتایج سال قبلی را پاک می‌کند"""

    def _make_page(self):
        with contextlib.redirect_stdout(io.StringIO()):
            from views.pages.indicators_page import IndicatorsPage
            return IndicatorsPage()

    def test_year_switch_resets_selection_and_panel(self):
        page = self._make_page()
        # سال ۱۴۰۳ + انتخاب A
        self._select_year(page, self.year_1403.id)
        page.load_students_for_teacher()
        self._select_student(page, self.student_a.id)
        page.load_student_indicators()
        self.assertEqual(page.current_student_id, self.student_a.id)

        # تغییر سال به ۱۴۰۴ (مسیر واقعی سیگنال)
        self._select_year_signal(page, self.year_1404.id)

        # پنل نتایج باید پاک شده باشد — نه نتیجهٔ کهنهٔ ۱۴۰۳
        self.assertIsNone(
            page.current_student_id,
            "انتخاب دانش‌آموز سال قبلی نباید بی‌تازه‌سازی بماند")
        self.assertIsNone(page.current_profile_id)
        self.assertFalse(page.insufficient_data_label.isVisibleTo(page))
        self.assertIn(
            "دانش‌آموز", page.details_panel.toPlainText(),
            "پنل جزئیات باید پیام راهنما بدهد نه نتیجهٔ کهنه")

        # و A در فهرست ۱۴۰۴ نیست (نشتی ممنوع)
        data = self._combo_students(page)
        self.assertNotIn(self.student_a.id, data)

    def test_year_switch_keeps_selection_when_student_exists_in_new_year(self):
        """اگر همان دانش‌آموز در سال جدید پرونده داشت، انتخاب حفظ شود"""
        # B را هم در ۱۴۰۳ پرونده بدهیم تا «همان دانش‌آموز» در هر دو سال باشد
        from models.student_academic_profile import StudentAcademicProfile
        profile_b_1403 = StudentAcademicProfile()
        profile_b_1403.student_id = self.student_b.id
        profile_b_1403.academic_year_id = self.year_1403.id
        profile_b_1403.grade = 2
        profile_b_1403.class_name = "دوم-الف"
        profile_b_1403.status = "active"
        self.profile_dal.create(profile_b_1403)

        page = self._make_page()
        self._select_year(page, self.year_1404.id)
        page.load_students_for_teacher()
        self._select_student(page, self.student_b.id)
        page.load_student_indicators()
        self.assertEqual(page.current_student_id, self.student_b.id)

        # تغییر سال به ۱۴۰۳: انتخاب B حفظ و با پروندهٔ ۱۴۰۳ تازه می‌شود
        self._select_year_signal(page, self.year_1403.id)
        self.assertEqual(page.current_student_id, self.student_b.id)
        self.assertIsNotNone(page.current_profile_id)
        self.assertEqual(
            page.current_profile_id,
            self.profile_dal.get_by_student_and_year(
                self.student_b.id, self.year_1403.id).id,
            "پنل باید با پروندهٔ سال جدید (۱۴۰۳) خوانده شده باشد")

    def test_on_year_change_hides_insufficient_banner(self):
        page = self._make_page()
        page.insufficient_data_label.setVisible(True)
        self._select_year_signal(page, self.year_1403.id)
        self.assertFalse(page.insufficient_data_label.isVisibleTo(page))

    # ---------- کمکی ----------

    @staticmethod
    def _select_year(page, year_id):
        for i in range(page.year_combo.count()):
            if page.year_combo.itemData(i) == year_id:
                page.year_combo.blockSignals(True)
                page.year_combo.setCurrentIndex(i)
                page.year_combo.blockSignals(False)
                return
        raise AssertionError("سال در کامبو نیست")

    @staticmethod
    def _select_year_signal(page, year_id):
        """تغییر سال با سیگنال واقعی (مسیر on_year_changed)"""
        for i in range(page.year_combo.count()):
            if page.year_combo.itemData(i) == year_id:
                page.year_combo.setCurrentIndex(i)  # emit
                return
        raise AssertionError("سال در کامبو نیست")

    @staticmethod
    def _select_student(page, student_id):
        for i in range(page.student_combo.count()):
            if page.student_combo.itemData(i) == student_id:
                page.student_combo.blockSignals(True)
                page.student_combo.setCurrentIndex(i)
                page.student_combo.blockSignals(False)
                return
        raise AssertionError("دانش‌آموز در کامبو نیست")

    @staticmethod
    def _combo_students(page):
        return [page.student_combo.itemData(i)
                for i in range(page.student_combo.count())]

    @staticmethod
    def _row_of(page, student_id):
        for i in range(page.student_combo.count()):
            if page.student_combo.itemData(i) == student_id:
                return page.student_combo.itemText(i)
        raise AssertionError("دانش‌آموز در کامبو نیست")


class TestAnalysisListingYearScope(BaseYearIsolation):
    """BUG-GUI-08: پایهٔ فهرست تحلیل از سال انتخاب‌شده"""

    def _make_page(self):
        with contextlib.redirect_stdout(io.StringIO()):
            from views.pages.analysis_page import AnalysisPage
            return AnalysisPage()

    def test_year_1403_lists_only_a(self):
        page = self._make_page()
        self._select_year(page, self.year_1403.id)
        page.load_students_for_teacher()
        data = [page.student_combo.itemData(i)
                for i in range(page.student_combo.count())]
        self.assertIn(self.student_a.id, data)
        self.assertNotIn(self.student_b.id, data)

    def test_year_1404_lists_only_b(self):
        page = self._make_page()
        self._select_year(page, self.year_1404.id)
        page.load_students_for_teacher()
        data = [page.student_combo.itemData(i)
                for i in range(page.student_combo.count())]
        self.assertIn(self.student_b.id, data)
        self.assertNotIn(self.student_a.id, data)

    def test_year_switch_resets_analysis_panel(self):
        page = self._make_page()
        self._select_year(page, self.year_1403.id)
        page.load_students_for_teacher()
        # انتخاب A و اجرای تحلیل (بدون مشاهده: پیام خالی — کافی است انتخاب ثبت شود)
        for i in range(page.student_combo.count()):
            if page.student_combo.itemData(i) == self.student_a.id:
                page.student_combo.blockSignals(True)
                page.student_combo.setCurrentIndex(i)
                page.student_combo.blockSignals(False)
                page.load_analysis()
                break
        self.assertEqual(page.current_student_id, self.student_a.id)

        # تغییر سال به ۱۴۰۴ (سیگنال واقعی): پنل کهنه پاک شود
        for i in range(page.year_combo.count()):
            if page.year_combo.itemData(i) == self.year_1404.id:
                page.year_combo.setCurrentIndex(i)
                break
        self.assertNotEqual(
            page.current_student_id, self.student_a.id,
            "انتخاب سال قبلی نباید بدون تازه‌سازی باقی بماند")

    def _select_year(self, page, year_id):
        for i in range(page.year_combo.count()):
            if page.year_combo.itemData(i) == year_id:
                page.year_combo.blockSignals(True)
                page.year_combo.setCurrentIndex(i)
                page.year_combo.blockSignals(False)
                return
        raise AssertionError("سال در کامبو نیست")


class TestNavigationMapping(unittest.TestCase):
    """BUG-NAV-07: ایندکس ناوبری فقط از نگاشت مرکزی PAGE_INDEX"""

    @staticmethod
    def _main_window_source():
        import pathlib
        return pathlib.Path(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "views", "main_window.py")).read_text(encoding="utf-8")

    def test_source_has_no_hardcoded_stacked_index(self):
        """دسترسی setCurrentIndex فقط از داخل goto_page مجاز است"""
        src = self._main_window_source()
        self.assertIn("PAGE_INDEX", src, "نگاشت مرکزی باید موجود باشد")
        # هیچ setCurrentIndex خام روی stacked_widget به‌جز مسیرهای
        # مشتق از PAGE_INDEX نمانده باشد (comboهای دیگر بی‌ربط‌اند)
        import re
        allowed = {
            "setCurrentIndex(index)",   # داخل goto_page
            "setCurrentIndex(idx)",     # lambda منو (از PAGE_INDEX)
        }
        pattern = r"stacked_widget\.setCurrentIndex\(([^)]*)\)"
        for match in re.finditer(pattern, src):
            statement = f"setCurrentIndex({match.group(1).strip()})"
            self.assertIn(
                statement, allowed,
                f"«stacked_widget.{statement}» خام یافت شد — باید با "
                "goto_page/PAGE_INDEX جایگزین شود")

    def test_menu_items_use_page_names_not_numbers(self):
        src = self._main_window_source()
        self.assertIn('"dashboard", None', src)
        self.assertIn('"academic_structure", Permission.', src)
        # menu_items دیگر ایندکس عددی خام ندارد (الگوی قدیمی: , 1, / , 9,)

    def test_page_index_is_contiguous(self):
        from views.main_window import PAGE_INDEX
        values = sorted(PAGE_INDEX.values())
        self.assertEqual(
            values, list(range(len(values))),
            "ایندکس‌های PAGE_INDEX باید پیوسته 0..N باشند")
        self.assertEqual(PAGE_INDEX["students"], 2)
        self.assertEqual(PAGE_INDEX["followups"], 5)
        self.assertEqual(PAGE_INDEX["reports"], 8)


if __name__ == "__main__":
    unittest.main()
