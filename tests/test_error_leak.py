"""
آزمون‌های رفع نشت Exception خام — دور نوزدهم، مرحلهٔ ۵ (ERR-01, ERR-LEAK-01)

پوشش مأموریت:
  • ممیزی سراسری الگوی `ServiceError(f"...{e!s}")` در services/*.py و
    `base_service.execute_in_transaction`: شبیه‌سازی خطای DB/فایل باید
    پیام کاربر را «امن و عمومی» بدهد، نه متن خامِ exception (بدون
    sqlite/Traceback/مسیر فایل/RuntimeError واقعی).
  • `DatabaseError.user_visible=False` و `DataIntegrityError.user_visible=False`
    باید همیشه برقرار باشند (نه فقط جایی که قبلاً تست شده).
  • رفعِ نشت نباید پیام‌های عمدیِ امن (ValidationError/«یافت نشد»/
    «به حداکثر رسیده») را که از قبل برای کاربر نوشته شده‌اند نابود کند —
    این‌ها باید دست‌نخورده (با همان متن مفید) به کاربر برسند، فقط دیگر
    با متن خامِ سیستمی قاطی نشوند.

هر تست روی دیتابیس/پوشهٔ پیوست موقت تازه اجرا می‌شود.
"""

import contextlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.connection as _dbc
from config import settings as _settings


class ErrorLeakTestBase(unittest.TestCase):
    """پایهٔ مشترک: دیتابیس موقت + پوشهٔ پیوست موقت + یک دانش‌آموز/پروندهٔ نمونه"""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="partow_errleak_")
        self._saved = (
            _settings.DB_PATH, _dbc.DB_PATH,
            getattr(_settings, 'ATTACHMENTS_DIR', None),
        )
        _settings.DB_PATH = os.path.join(self._tmpdir, "partow.db")
        _dbc.DB_PATH = _settings.DB_PATH
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False

        att_dir = os.path.join(self._tmpdir, "attachments")
        _settings.ATTACHMENTS_DIR = att_dir
        import config.settings as _cfg
        _cfg.ATTACHMENTS_DIR = att_dir
        import dal.attachment_dal as _ad
        _ad.ATTACHMENTS_DIR = att_dir
        self.att_dir = att_dir

        self.db = _dbc.DatabaseConnection()  # seed (admin/manager + سال پیش‌فرض)

        from utils.security import AccessControl
        AccessControl.logout()

        # یک دانش‌آموز و پروندهٔ سالانهٔ نمونه برای تست‌هایی که به آن نیاز دارند
        from dal.student_academic_profile_dal import StudentAcademicProfileDAL
        from dal.student_dal import StudentDAL
        from models.student import Student
        from models.student_academic_profile import StudentAcademicProfile

        year_row = self.db.get_connection().execute(
            "SELECT id FROM academic_years WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        self.year_id = year_row["id"] if year_row else None

        student = Student()
        student.first_name = "علی"
        student.last_name = "احمدی"
        student.national_code = "1234567890"
        self.student = StudentDAL().create(student)

        profile = StudentAcademicProfile()
        profile.student_id = self.student.id
        profile.academic_year_id = self.year_id
        profile.grade = 1
        profile.status = StudentAcademicProfile.STATUS_ACTIVE
        self.profile = StudentAcademicProfileDAL().create(profile)

    def tearDown(self):
        from utils.security import AccessControl
        AccessControl.logout()
        with contextlib.suppress(Exception):
            _dbc.DatabaseConnection().close_all()
        db_path, dbc_path, att_dir = self._saved
        _settings.DB_PATH, _dbc.DB_PATH = db_path, dbc_path
        if att_dir is not None:
            _settings.ATTACHMENTS_DIR = att_dir
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False


# ============================================================
# بخش A: نامرئی‌بودن متن خام در پیام‌های کاربر (نمونه‌ای از services/*.py)
# ============================================================

class TestNoRawExceptionLeak(ErrorLeakTestBase):
    """شبیه‌سازی خطای DB/فایل → پیام کاربر نباید متن خام داشته باشد"""

    RAW_MARKER = "SECRET_RAW_TEXT_/home/user/partow.db_traceback_line_99"

    def test_observation_service_get_by_id_raw_db_error_hidden(self):
        from services.observation_service import ObservationService
        svc = ObservationService()
        original = svc.observation_dal.get_by_id

        def _boom(*a, **k):
            raise RuntimeError(self.RAW_MARKER)
        svc.observation_dal.get_by_id = _boom
        try:
            with self.assertRaises(Exception) as ctx:
                svc.get_observation(1)
        finally:
            svc.observation_dal.get_by_id = original
        self.assertNotIn(self.RAW_MARKER, str(ctx.exception))
        self.assertFalse(getattr(ctx.exception, "user_visible", True))

    def test_intervention_service_search_raw_db_error_hidden(self):
        from services.intervention_service import InterventionService
        svc = InterventionService()
        original = svc.intervention_dal.search

        def _boom(*a, **k):
            raise RuntimeError(self.RAW_MARKER)
        svc.intervention_dal.search = _boom
        try:
            with self.assertRaises(Exception) as ctx:
                svc.search_interventions("x")
        finally:
            svc.intervention_dal.search = original
        self.assertNotIn(self.RAW_MARKER, str(ctx.exception))

    def test_followup_service_get_all_raw_db_error_hidden(self):
        from services.followup_service import FollowUpService
        svc = FollowUpService()
        original = svc.followup_dal.get_all

        def _boom(*a, **k):
            raise RuntimeError(self.RAW_MARKER)
        svc.followup_dal.get_all = _boom
        try:
            with self.assertRaises(Exception) as ctx:
                svc.get_all_followups()
        finally:
            svc.followup_dal.get_all = original
        self.assertNotIn(self.RAW_MARKER, str(ctx.exception))

    def test_student_service_search_raw_db_error_hidden(self):
        from services.student_service import StudentService
        svc = StudentService()
        original = svc.student_dal.search

        def _boom(*a, **k):
            raise RuntimeError(self.RAW_MARKER)
        svc.student_dal.search = _boom
        try:
            with self.assertRaises(Exception) as ctx:
                svc.search_students("x")
        finally:
            svc.student_dal.search = original
        self.assertNotIn(self.RAW_MARKER, str(ctx.exception))

    def test_attachment_service_get_attachment_raw_db_error_hidden(self):
        from services.attachment_service import AttachmentService
        svc = AttachmentService()
        original = svc.attachment_dal.get_by_id

        def _boom(*a, **k):
            raise RuntimeError(self.RAW_MARKER)
        svc.attachment_dal.get_by_id = _boom
        try:
            with self.assertRaises(Exception) as ctx:
                svc.get_attachment(1)
        finally:
            svc.attachment_dal.get_by_id = original
        self.assertNotIn(self.RAW_MARKER, str(ctx.exception))

    def test_base_service_execute_in_transaction_raw_error_hidden(self):
        from services.student_service import StudentService
        svc = StudentService()

        def _boom():
            raise RuntimeError(self.RAW_MARKER)
        with self.assertRaises(Exception) as ctx:
            svc.execute_in_transaction(_boom)
        self.assertNotIn(self.RAW_MARKER, str(ctx.exception))
        self.assertFalse(getattr(ctx.exception, "user_visible", True))

    def test_base_service_commit_transaction_raw_error_hidden(self):
        from services.student_service import StudentService
        svc = StudentService()
        svc.begin_transaction()
        original = svc.db.commit_transaction

        def _boom():
            raise RuntimeError(self.RAW_MARKER)
        svc.db.commit_transaction = _boom
        try:
            with self.assertRaises(Exception) as ctx:
                svc.commit_transaction()
        finally:
            svc.db.commit_transaction = original
            with contextlib.suppress(Exception):
                svc.rollback_transaction()
        self.assertNotIn(self.RAW_MARKER, str(ctx.exception))

    def test_report_generator_export_pdf_raw_error_hidden(self):
        from services.report_generator import ReportGenerator
        svc = ReportGenerator()
        # هر متد تولید داده که برای PDF لازم است را خراب می‌کنیم تا export_to_pdf
        # وارد مسیر except شود؛ ساده‌ترین راه: مستقیماً profile_dal.get_by_id بترکد.
        original_get = svc.profile_dal.get_by_id if hasattr(svc, "profile_dal") else None
        if original_get is None:
            self.skipTest("ReportGenerator بدون profile_dal مستقیم است")
        def _boom(*a, **k):
            raise RuntimeError(self.RAW_MARKER)
        svc.profile_dal.get_by_id = _boom
        try:
            ok, message = svc.export_to_pdf(self.profile.id, os.path.join(self._tmpdir, "out.pdf"))
        finally:
            svc.profile_dal.get_by_id = original_get
        self.assertFalse(ok)
        self.assertNotIn(self.RAW_MARKER, message)


# ============================================================
# بخش B: کلاس‌های AppError — نامرئی‌بودن به‌طور طراحی
# ============================================================

class TestAppErrorVisibilityInvariants(unittest.TestCase):
    """DatabaseError/DataIntegrityError باید همیشه user_visible=False باشند"""

    def test_database_error_always_user_invisible(self):
        from utils.error_handler import DatabaseError
        err = DatabaseError("هر پیامی حتی فنی")
        self.assertFalse(err.user_visible)
        self.assertEqual(err.code, 500)

    def test_data_integrity_error_always_user_invisible(self):
        from utils.error_handler import DataIntegrityError
        err = DataIntegrityError("هر پیامی حتی فنی")
        self.assertFalse(err.user_visible)
        self.assertEqual(err.code, 500)

    def test_service_error_default_still_user_visible(self):
        """قرارداد قبلی نباید بشکند: ServiceError بدون آرگومان صریح، پیش‌فرضش True است"""
        from utils.error_handler import ServiceError
        err = ServiceError("پیام امن")
        self.assertTrue(err.user_visible)

    def test_service_error_can_be_marked_invisible(self):
        from utils.error_handler import ServiceError
        err = ServiceError("جزئیات فنی", user_visible=False)
        self.assertFalse(err.user_visible)

    def test_error_handler_build_response_hides_invisible_message(self):
        """مسیر ErrorHandler: user_visible=False → پیام عمومی، نه پیام واقعی"""
        from utils.error_handler import ErrorHandler, ServiceError
        handler = ErrorHandler()
        err = ServiceError("متن فنی که نباید دیده شود", user_visible=False)
        response = handler.handle(err, log_level='info')
        self.assertNotIn("متن فنی که نباید دیده شود", response['error']['message'])
        self.assertEqual(response['error']['message'], ErrorHandler.GENERIC_MESSAGE)

    def test_error_handler_build_response_shows_visible_message(self):
        from utils.error_handler import ErrorHandler, ServiceError
        handler = ErrorHandler()
        err = ServiceError("این کد ملی قبلاً ثبت شده است.", user_visible=True)
        response = handler.handle(err, log_level='info')
        self.assertEqual(response['error']['message'], "این کد ملی قبلاً ثبت شده است.")


# ============================================================
# بخش C: عدم نابودیِ پیام‌های عمدی/امنِ از پیش نوشته‌شده
# ============================================================

class TestSafeMessagesPreserved(ErrorLeakTestBase):
    """
    رفعِ نشت نباید پیام‌های عمدیِ کاربرمحور (ValidationError/«یافت نشد»/
    محدودیت‌های کسب‌وکاری) را که *داخل همان try* پیش از رسیدن به except
    عمومی raise شده‌اند نابود کند.
    """

    def test_attachment_limit_message_survives_generic_except(self):
        """
        این دقیقاً همان سناریوی tests/test_attachment_restore.py است: سقف
        ۲۰ پیوست با ValidationError raise می‌شود و باید پیامش («حداکثر»)
        از execute_in_transaction دست‌نخورده عبور کند، نه با پیام عمومی
        جایگزین شود.
        """
        from services.attachment_service import AttachmentService
        svc = AttachmentService()
        entity = ("observation", 1)
        for i in range(20):
            svc.upload_attachment(
                entity[0], entity[1], f"content-{i}".encode(), f"f{i}.txt",
                created_by=None, user_id=None)
        with self.assertRaises(Exception) as ctx:
            svc.upload_attachment(
                entity[0], entity[1], b"over limit", "the21st.txt",
                created_by=None, user_id=None)
        self.assertIn("حداکثر", str(ctx.exception))

    def test_intervention_not_found_message_survives_generic_except(self):
        """
        InterventionService.get_intervention: بلوکِ «یافت نشد» داخل همان
        try با except Exception عمومی پوشش داده شده؛ رفعِ نشت نباید این
        پیامِ امنِ مفید را با یک پیام عمومیِ کم‌فایده جایگزین کند.
        """
        from services.intervention_service import InterventionService
        svc = InterventionService()
        with self.assertRaises(Exception) as ctx:
            svc.get_intervention(999999)
        self.assertIn("یافت نشد", str(ctx.exception))

    def test_recommendation_accept_not_found_message_survives(self):
        from services.recommendation_service import RecommendationService
        svc = RecommendationService()
        with self.assertRaises(Exception) as ctx:
            svc.accept_recommendation(999999)
        self.assertIn("یافت نشد", str(ctx.exception))

    def test_recommendation_save_failure_reports_title_and_reason(self):
        """
        بازآزمونِ سناریوی verify_fixes6 §F3: اگر ذخیرهٔ پیشنهاد شکست
        بخورد، خطای بالارفته باید همچنان گویا باشد (شامل واژهٔ «ذخیره»)،
        نه یک پیام عمومیِ بی‌ربط.
        """
        import contextlib as _c
        import io as _io

        from services.recommendation_service import RecommendationService
        svc = RecommendationService()

        def _boom(rec):
            raise RuntimeError("شبیه‌سازی خرابی دیتابیس")
        original_create = svc.recommendation_dal.create
        svc.recommendation_dal.create = _boom
        try:
            with _c.redirect_stdout(_io.StringIO()), self.assertRaises(Exception) as ctx:
                svc.generate_recommendations(self.profile.id)
        finally:
            svc.recommendation_dal.create = original_create
        self.assertIn("ذخیره", str(ctx.exception))
        # و همچنان امن: متن خامِ RuntimeError نباید دیده شود
        self.assertNotIn("شبیه‌سازی خرابی دیتابیس", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
