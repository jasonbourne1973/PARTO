"""
اسکریپت راستی‌آزمایی اصلاحات PARTO — دور دوم (بازرسی مجدد برنچ)
================================================================
این فایل را در پوشه ریشه پروژه (کنار main.py) بگذارید و اجرا کنید:

    python verify_fixes2.py

همه آزمون‌ها روی یک **دیتابیس موقت** اجرا می‌شوند؛ یعنی به
database/partow.db واقعی شما و به داده‌هایتان هیچ آسیبی نمی‌رسد.

این اسکریپت مکمل verify_fixes.py است (دور اول: ۱۷ آزمون).
دور دوم این ۸ مورد را پوشش می‌دهد:

  ۱. متدهای جست‌وجوی مفقود در ObservationDAL / InterventionDAL / FollowUpDAL
     (کادر جست‌وجوی سه صفحه مشاهدات، مداخلات و پیگیری‌ها کار نمی‌کرد)
  ۲. AdvancedSearchService.profile_dal که هرگز ساخته نمی‌شد
  ۳. CounselingService.get_session_stats (صفت ناموجود روی مدل پرونده)
  ۴. views/pages/promotion_page.py: متدهای ناموجود DAL + گاردهای
     «except AttributeError: pass» که منطق ایمنی را بی‌صدا از کار
     می‌انداختند (ارتقاء تکراری / خطای کاذب «پایه یافت نشد»)
  ۵. utils/persian_pdf.py: استفاده از cm در مقدار پیش‌فرض آرگومان، که
     باعث می‌شد بدون reportlab کل برنامه بالا نیاید
  ۶. services/teacher_report_service.py: import بدون گارد openpyxl
  ۷. days=None در دو متد DAL (TypeError در timedelta)
  ۸. کاراکترهای عربی «ك» و «ي» در متن گزارش‌های چاپی

خروجی مورد انتظار: همه موارد ✅ و در پایان «موفق: N  ناموفق: 0».
"""

import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TMP = tempfile.mkdtemp(prefix="parto_verify2_")
DB_DIR = os.path.join(TMP, "database")
os.makedirs(DB_DIR, exist_ok=True)
DB = os.path.join(DB_DIR, "partow.db")

import config.settings as settings

settings.DB_PATH = DB
settings.ATTACHMENTS_DIR = os.path.join(TMP, "attachments")

import database.connection as dbc

dbc.DB_PATH = DB

RESULTS = []


def check(title, fn):
    try:
        fn()
        RESULTS.append((title, True, ""))
        print(f"  [OK]   {title}")
    except Exception as e:
        RESULTS.append((title, False, f"{type(e).__name__}: {e}"))
        print(f"  [FAIL] {title}\n         -> {type(e).__name__}: {str(e)[:220]}")


def _code_only(relpath):
    """متن فایل بدون خطوط کامنت.

    نمونه‌های «قبل از اصلاح» داخل کامنت‌ها نقل می‌شوند؛ اگر کامنت‌ها هم
    شمرده شوند، آزمون به‌خاطر متن کامنت شکست کاذب می‌خورد.
    """
    path = os.path.join(ROOT, *relpath.split("/"))
    kept = []
    for line in open(path, encoding="utf-8").read().split("\n"):
        if line.lstrip().startswith("#"):
            continue
        kept.append(line)
    return "\n".join(kept)


print("=" * 74)
print("۰) ساخت دیتابیس موقت و داده آزمون")
print("=" * 74)
with contextlib.redirect_stdout(io.StringIO()):
    conn = dbc.DatabaseConnection().get_connection()

from dal.academic_year_dal import AcademicYearDAL
from dal.counseling_session_dal import CounselingSessionDAL
from dal.observation_dal import ObservationDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import (
    StudentAcademicProfileDAL,
)
from models.academic_year import AcademicYear
from models.counseling_session import CounselingSession
from models.student_academic_profile import (
    StudentAcademicProfile,
)
from services.advanced_search_service import (
    AdvancedSearchService,
)
from services.counseling_service import CounselingService
from services.followup_service import FollowUpService
from services.intervention_service import InterventionService
from services.observation_service import ObservationService
from services.student_service import StudentService
from services.teacher_performance_service import (
    TeacherPerformanceService,
)
from services.teacher_report_service import TeacherReportService

CTX = {}


def _mk_staff(name, role):
    s = StaffDAL()
    from models.staff import Staff
    st = Staff()
    st.full_name = name
    st.role = role
    st.is_active = 1
    st.description = "داده آزمون"
    return s.create(st)


def setup():
    CTX["teacher1"] = _mk_staff("معلم اول", "teacher")
    CTX["teacher2"] = _mk_staff("معلم دوم", "teacher")
    CTX["counselor"] = _mk_staff("مشاور مدرسه", "counselor")

    CTX["student"] = StudentService().create_student({
        "first_name": "علی", "last_name": "محمدی", "national_code": "0012345678",
        "birth_date": "1390-05-10", "grade": 4, "class_name": "4/1",
    }, user_id=CTX["teacher1"].id)
    CTX["student2"] = StudentService().create_student({
        "first_name": "مریم", "last_name": "احمدی", "national_code": "0012345679",
        "birth_date": "1390-06-10", "grade": 4, "class_name": "4/1",
    }, user_id=CTX["teacher1"].id)

    pdal = StudentAcademicProfileDAL()
    CTX["profile"] = pdal.get_active_by_student(CTX["student"].id)
    CTX["profile2"] = pdal.get_active_by_student(CTX["student2"].id)
    assert CTX["profile"] and CTX["profile2"], "پرونده سالانه ساخته نشد"

    osvc = ObservationService()
    # ۳ مشاهده برای دانش‌آموز اول توسط معلم اول، ۱ مشاهده برای دومی
    for i, (prof, staff, text) in enumerate([
        (CTX["profile"], CTX["teacher1"], "دانش‌آموز در گروه همکاری کرد"),
        (CTX["profile"], CTX["teacher1"], "پاسخ درست به پرسش کلاس"),
        (CTX["profile"], CTX["teacher1"], "بی‌قراری در زنگ ورزش"),
        (CTX["profile2"], CTX["teacher2"], "یادداشت‌برداری دقیق از درس"),
    ]):
        osvc.create_observation({
            "student_id": prof.student_id, "staff_id": staff.id,
            "observation_date": f"1404/06/{10 + i:02d}",
            "description": text, "behavior": text, "location": "کلاس درس",
            "behavior_type": ["مثبت", "مثبت", "منفی", "خنثی"][i],
            "severity": 2 + (i % 3), "tags": "آزمون,دور دوم",
        }, user_id=staff.id)

    isvc = InterventionService()
    r = isvc.create_intervention({
        "student_id": CTX["student"].id, "staff_id": CTX["teacher1"].id,
        "title": "مداخله آزمون", "description": "برنامه تقویت مشارکت کلاسی",
        "goal": "بهبود مشارکت", "date": "1404/06/12",
        "type": "individual", "status": "planned",
    }, user_id=CTX["teacher1"].id)
    CTX["intervention"] = getattr(r, "id", None)

    FollowUpService().create_followup({
        "intervention_id": CTX["intervention"], "student_id": CTX["student"].id,
        "staff_id": CTX["teacher1"].id, "date": "1404/06/20",
        "title": "پیگیری آزمون", "description": "بررسی روند مشارکت دانش‌آموز",
        "status": "pending", "next_action_date": "1404/07/01",
    }, user_id=CTX["teacher1"].id)


with contextlib.redirect_stdout(io.StringIO()):
    setup()
print(f"  داده آماده شد: {len(CTX)} موجودیت")


# ============================================================
print()
print("=" * 74)
print("۱) جست‌وجوی متن آزاد (متدهای مفقود در سه DAL)")
print("=" * 74)


def search_observations_works():
    r = ObservationService().search_observations("کلاس")
    assert len(r) >= 3, f"انتظار حداقل ۳ نتیجه بود، {len(r)} برگشت"


check("ObservationService.search_observations نتیجه می‌دهد", search_observations_works)


def search_observations_limit():
    r = ObservationService().search_observations("کلاس", 2)
    assert len(r) == 2, f"limit رعایت نشد: {len(r)} نتیجه"


check("search_observations پارامتر limit را رعایت می‌کند", search_observations_limit)


def search_obs_by_student_scoped():
    r = ObservationService().search_observations_by_student(CTX["student"].id, "کلاس")
    profs = {o.student_profile_id for o in r}
    assert r, "هیچ نتیجه‌ای برنگشت"
    assert profs == {CTX["profile"].id}, f"نتایج به دانش‌آموز دیگر نشت کرد: {profs}"


check("search_observations_by_student فقط همان دانش‌آموز را برمی‌گرداند",
      search_obs_by_student_scoped)


def search_obs_by_teacher_scoped():
    r = ObservationService().search_observations_by_teacher(CTX["teacher1"].id, "کلاس")
    assert r, "هیچ نتیجه‌ای برنگشت"
    staffs = {o.staff_id for o in r}
    assert staffs == {CTX["teacher1"].id}, f"نتایج به معلم دیگر نشت کرد: {staffs}"


check("search_observations_by_teacher فقط همان معلم را برمی‌گرداند",
      search_obs_by_teacher_scoped)


def search_interventions_works():
    svc = InterventionService()
    assert svc.search_interventions("مشارکت"), "جست‌وجوی مداخلات خالی بود"
    assert svc.search_interventions_by_student(CTX["student"].id, "مشارکت")
    assert svc.search_interventions_by_teacher(CTX["teacher1"].id, "مشارکت")


check("هر سه متد جست‌وجوی مداخلات کار می‌کنند", search_interventions_works)


def search_followups_works():
    svc = FollowUpService()
    assert svc.search_followups("مشارکت"), "جست‌وجوی پیگیری‌ها خالی بود"
    assert svc.search_followups_by_student(CTX["student"].id, "مشارکت")
    assert svc.search_followups_by_teacher(CTX["teacher1"].id, "مشارکت")


check("هر سه متد جست‌وجوی پیگیری‌ها کار می‌کنند (با JOIN روی مداخله)",
      search_followups_works)


def search_no_result_is_empty_not_error():
    r = ObservationService().search_observations("عبارتی‌که‌اصلاً‌وجود‌ندارد")
    assert r == [], f"باید لیست خالی برگرداند نه خطا: {r}"


check("جست‌وجوی عبارت ناموجود → لیست خالی (بدون استثنا)",
      search_no_result_is_empty_not_error)


def like_wildcards_escaped():
    svc = ObservationService()
    n_all = len(svc.search_observations("کلاس"))
    assert n_all > 0
    # اگر «٪» به‌عنوان wildcard تفسیر شود، همه رکوردها برمی‌گردند
    n_pct = len(svc.search_observations("٪"))
    n_us = len(svc.search_observations("_"))
    assert n_pct == 0, f"٪ به‌عنوان wildcard نشت کرد ({n_pct} نتیجه)"
    assert n_us == 0, f"_ به‌عنوان wildcard نشت کرد ({n_us} نتیجه)"


check("کاراکترهای ویژه LIKE فرار داده می‌شوند (٪ و _ wildcard نمی‌شوند)",
      like_wildcards_escaped)


def soft_deleted_hidden_from_search():
    svc = ObservationService()
    before = len(svc.search_observations("کلاس"))
    assert before > 0
    conn.execute("UPDATE observations SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP")
    conn.commit()
    try:
        after = len(svc.search_observations("کلاس"))
        assert after == 0, f"رکوردهای حذف منطقی‌شده برگشتند: {after}"
        with_deleted = len(ObservationDAL().search("کلاس", include_deleted=True))
        assert with_deleted == before, (
            f"include_deleted=True باید {before} می‌داد، {with_deleted} داد")
    finally:
        conn.execute("UPDATE observations SET is_deleted = 0, deleted_at = NULL")
        conn.commit()


check("حذف منطقی از نتایج جست‌وجو پنهان می‌شود (و با include_deleted برمی‌گردد)",
      soft_deleted_hidden_from_search)


# ============================================================
print()
print("=" * 74)
print("۲) AdvancedSearchService.profile_dal")
print("=" * 74)


def advanced_search_by_student():
    svc = AdvancedSearchService()
    assert hasattr(svc, "profile_dal"), "صفت profile_dal در __init__ ساخته نمی‌شود"
    r = svc.search_observations({"student_id": CTX["student"].id})
    assert r, "جست‌وجوی مشاهدات با فیلتر دانش‌آموز خالی بود"
    assert {o.student_profile_id for o in r} == {CTX["profile"].id}


check("search_observations با student_id دیگر AttributeError نمی‌دهد",
      advanced_search_by_student)


def advanced_search_student_status():
    svc = AdvancedSearchService()
    st = svc._get_student_status(CTX["student"].id)
    assert st == StudentAcademicProfile.STATUS_ACTIVE, f"وضعیت اشتباه: {st}"


check("_get_student_status از self.profile_dal استفاده می‌کند و درست کار می‌کند",
      advanced_search_student_status)


# ============================================================
print()
print("=" * 74)
print("۳) CounselingService.get_session_stats")
print("=" * 74)


def session_stats_has_student_name():
    cs = CounselingService()
    cs.create_session({
        "student_profile_id": CTX["profile"].id,
        "counselor_id": CTX["counselor"].id,
        "session_date": "1404/06/15", "session_time": "10:00",
        "duration_minutes": 45, "type": CounselingSession.TYPE_INDIVIDUAL,
        "method": CounselingSession.METHOD_IN_PERSON,
        "topic": "بررسی وضعیت تحصیلی", "summary": "خلاصه آزمون",
        "status": CounselingSession.STATUS_SCHEDULED,
    }, user_id=CTX["counselor"].id)
    stats = cs.get_session_stats(CTX["profile"].id)
    assert isinstance(stats, dict), f"خروجی dict نیست: {type(stats)}"
    assert stats.get("student_name") == "علی محمدی", (
        f"نام دانش‌آموز اشتباه است: {stats.get('student_name')!r}")


check("get_session_stats نام دانش‌آموز را از Student می‌گیرد (نه از پرونده)",
      session_stats_has_student_name)


def session_stats_unknown_profile():
    stats = CounselingService().get_session_stats(999999)
    assert isinstance(stats, dict), "برای پرونده ناموجود باید dict خالی برگرداند"
    assert "student_name" not in stats or not stats["student_name"]


check("get_session_stats برای پرونده ناموجود نمی‌شکند", session_stats_unknown_profile)


# ============================================================
print()
print("=" * 74)
print("۴) مسیر ارتقاء دانش‌آموزان (promotion_page + DALها)")
print("=" * 74)


def academic_year_get_by_title_exists():
    dal = AcademicYearDAL()
    assert hasattr(dal, "get_by_title"), "متد get_by_title اضافه نشده است"
    y = AcademicYear()
    y.title = "1409-1410"
    y.start_date = "1409/07/01"
    y.end_date = "1410/06/31"
    y.is_active = 0
    y.is_archived = 0
    created = dal.create(y)
    assert created and created.id, "ساخت سال تحصیلی ناموفق"
    found = dal.get_by_title("1409-1410")
    assert found and found.id == created.id, "get_by_title سال را پیدا نکرد"
    CTX["year"] = created


check("AcademicYearDAL.get_by_title سال موجود را پیدا می‌کند",
      academic_year_get_by_title_exists)


def get_by_title_finds_archived():
    dal = AcademicYearDAL()
    dal.archive(CTX["year"].id)
    assert dal.get_by_title("1409-1410"), (
        "سال بایگانی‌شده پیدا نشد ⇒ ارتقاء یک سال تکراری می‌ساخت")
    assert dal.get_by_title("1409-1410", include_archived=False) is None, (
        "با include_archived=False نباید برگردد")
    assert dal.get_by_title("عنوانی‌که‌وجود‌ندارد") is None
    assert dal.get_by_title("") is None and dal.get_by_title(None) is None


check("get_by_title سال بایگانی‌شده را هم پیدا می‌کند (جلوگیری از سال تکراری)",
      get_by_title_finds_archived)


def all_profiles_includes_history():
    pdal = StudentAcademicProfileDAL()
    # یک پرونده «فارغ‌التحصیل» در یک سال تحصیلی دیگر (غیرفعال)
    old = StudentAcademicProfile()
    old.student_id = CTX["student"].id
    old.academic_year_id = CTX["year"].id
    old.grade = 3
    old.class_name = "3/1"
    old.status = StudentAcademicProfile.STATUS_GRADUATED
    created = pdal.create(old)
    assert created and created.id, "ساخت پرونده سابقه ناموفق"

    allp = pdal.get_all_profiles_for_student(CTX["student"].id)
    ids = {p.id for p in allp}
    assert created.id in ids, (
        "get_all_profiles_for_student پرونده غیرفعال/سال دیگر را برنگرداند")
    assert CTX["profile"].id in ids, "پرونده سال جاری برنگشت"
    grades = [p.grade for p in allp if p.grade]
    assert max(grades) == 4, f"بیشترین پایه سابقه باید ۴ باشد، {max(grades)} شد"


def active_profile_excludes_terminal_status():
    pdal = StudentAcademicProfileDAL()
    pid = CTX["profile2"].id
    try:
        pdal.update_status(pid, StudentAcademicProfile.STATUS_GRADUATED, "آزمون")
        assert pdal.get_active_by_student(CTX["student2"].id) is None, (
            "پرونده «فارغ‌التحصیل» نباید به‌عنوان پرونده فعال برگردد")
        pdal.update_status(pid, StudentAcademicProfile.STATUS_DROPPED, "آزمون")
        assert pdal.get_active_by_student(CTX["student2"].id) is None, (
            "پرونده «انصرافی» نباید به‌عنوان پرونده فعال برگردد")
    finally:
        pdal.update_status(pid, StudentAcademicProfile.STATUS_ACTIVE, "برگشت به حالت اول")
    assert pdal.get_active_by_student(CTX["student2"].id) is not None, (
        "بعد از برگرداندن وضعیت به active باید دوباره پیدا شود")


def inactive_profile_still_readable():
    # 'inactive' عمداً حذف نمی‌شود: پرونده سال قبل باید برای سابقه/گزارش
    # قابل خواندن بماند.
    pdal = StudentAcademicProfileDAL()
    pid = CTX["profile2"].id
    try:
        pdal.update_status(pid, StudentAcademicProfile.STATUS_INACTIVE, "آزمون")
        assert pdal.get_active_by_student(CTX["student2"].id) is not None, (
            "پرونده inactive نباید ناپدید شود (سال تحصیلی هنوز فعال است)")
    finally:
        pdal.update_status(pid, StudentAcademicProfile.STATUS_ACTIVE, "برگشت")


def null_status_does_not_hide_student():
    # COALESCE: در داده‌های قدیمی ممکن است status خالی باشد؛ دانش‌آموز
    # نباید بی‌صدا ناپدید شود.
    pid = CTX["profile"].id
    conn.execute("UPDATE student_academic_profiles SET status = NULL WHERE id = ?",
                 (pid,))
    conn.commit()
    try:
        assert StudentAcademicProfileDAL().get_active_by_student(
            CTX["student"].id) is not None, (
            "status=NULL باعث گم شدن دانش‌آموز شد (COALESCE کار نمی‌کند)")
    finally:
        conn.execute(
            "UPDATE student_academic_profiles SET status = 'active' WHERE id = ?",
            (pid,))
        conn.commit()


def no_dead_status_vocabulary():
    src = _code_only("dal/student_academic_profile_dal.py")
    assert "NOT IN ('archived', 'closed')" not in src, (
        "هنوز واژگان مرده 'archived'/'closed' در کوئری هست")
    assert "'graduated'" in src and "'dropped'" in src and "'transferred'" in src, (
        "وضعیت‌های واقعی در فیلتر نیامده‌اند")


check("get_all_profiles_for_student پرونده غیرفعال/سال‌های قبل را برمی‌گرداند",
      all_profiles_includes_history)
check("پرونده «فارغ‌التحصیل/انصرافی» دیگر پرونده فعال محسوب نمی‌شود",
      active_profile_excludes_terminal_status)
check("پرونده «inactive» همچنان خواندنی می‌ماند (سابقه سال قبل گم نمی‌شود)",
      inactive_profile_still_readable)
check("status=NULL باعث ناپدید شدن دانش‌آموز نمی‌شود (COALESCE)",
      null_status_does_not_hide_student)
check("واژگان مرده 'archived'/'closed' از کوئری حذف شده است",
      no_dead_status_vocabulary)


def duplicate_promotion_guard():
    pdal = StudentAcademicProfileDAL()
    target = CTX["year"]
    # پرونده‌ای که در سال مقصد ساخته شده (یعنی دانش‌آموز قبلاً ارتقاء یافته)
    dup = pdal.get_by_student_and_year(CTX["student"].id, target.id)
    assert dup is not None, "گارد «اجرای دوباره» پرونده موجود را پیدا نکرد"
    # و برای سالی که پرونده ندارد باید None بدهد
    assert pdal.get_by_student_and_year(CTX["student2"].id, target.id) is None, (
        "برای دانش‌آموزی که در آن سال پرونده ندارد باید None برگردد")


check("get_by_student_and_year گارد «ارتقاء تکراری» را ممکن می‌کند",
      duplicate_promotion_guard)


def promotion_page_has_no_phantom_dal_calls():
    src = _code_only("views/pages/promotion_page.py")
    assert not re.search(r"profile_dal\.get_by_student\(", src), (
        "هنوز متد ناموجود profile_dal.get_by_student صدا زده می‌شود")
    assert "STATUS_GRADUATED" in src and "ارتقاء داده نمی‌شود" in src, (
        "گارد «فارغ‌التحصیل دوباره ارتقاء نیابد» اضافه نشده است")
    assert "get_all_profiles_for_student(" in src, "متد جایگزین استفاده نشده است"
    assert "get_by_student_and_year(" in src, "گارد ارتقاء تکراری وصل نشده است"
    assert "except AttributeError" not in src, (
        "گارد پنهان‌کننده خطا (except AttributeError) هنوز باقی است")


check("promotion_page دیگر متد ناموجود را صدا نمی‌زند و گارد پنهان‌کننده ندارد",
      promotion_page_has_no_phantom_dal_calls)


# ============================================================
print()
print("=" * 74)
print("۵) وابستگی‌های اختیاری (reportlab و openpyxl)")
print("=" * 74)


def persian_pdf_units_always_defined():
    import utils.persian_pdf as pp
    assert hasattr(pp, "REPORTLAB_AVAILABLE")
    # چه reportlab باشد چه نباشد، این دو باید عدد باشند
    assert isinstance(pp.cm, float) and abs(pp.cm - 28.346456692913385) < 1e-6, pp.cm
    assert isinstance(pp.inch, float) and pp.inch == 72.0, pp.inch


check("utils.persian_pdf همیشه cm و inch عددی دارد (import نمی‌شکند)",
      persian_pdf_units_always_defined)


BLOCKER_SRC = '''
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = {root!r}
TMP = {tmp!r}
sys.path.insert(0, ROOT)

class Blocker:
    """reportlab را طوری مسدود می‌کند که انگار اصلاً نصب نیست."""
    def find_spec(self, name, path=None, target=None):
        if name == "reportlab" or name.startswith("reportlab."):
            raise ImportError("blocked for test")
        return None

sys.meta_path.insert(0, Blocker())

import config.settings as settings
settings.DB_PATH = os.path.join(TMP, "database", "blocked.db")
settings.ATTACHMENTS_DIR = os.path.join(TMP, "attachments")
import database.connection as dbc
dbc.DB_PATH = settings.DB_PATH

# قبل از اصلاح، همین import با NameError: name 'cm' is not defined می‌ترکید
import utils.persian_pdf as pp
assert pp.REPORTLAB_AVAILABLE is False
assert abs(pp.cm - 28.346456692913385) < 1e-9
import services.report_generator
import services.teacher_report_service
import services.parent_report_service
import services.school_report_service
import services.class_report_service
try:
    pp.PersianPDF(os.path.join(TMP, "x.pdf"))
    print("NO_ERROR")
except RuntimeError as e:
    print("RUNTIME_ERROR: " + str(e))
'''


def app_imports_without_reportlab():
    code = BLOCKER_SRC.format(root=ROOT, tmp=TMP)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, timeout=180, cwd=ROOT)
    out = (r.stdout or "") + (r.stderr or "")
    assert "name 'cm' is not defined" not in out, (
        f"هنوز بدون reportlab کل برنامه می‌شکند:\n{out[:400]}")
    assert r.returncode == 0, f"import ماژول‌های گزارش‌ساز شکست:\n{out[-500:]}"
    assert "RUNTIME_ERROR" in out and "reportlab" in out, (
        f"باید پیام خوانای «reportlab نصب نیست» بدهد:\n{out[-400:]}")


check("بدون reportlab، ماژول‌های گزارش‌ساز import می‌شوند و پیام خوانا می‌دهند",
      app_imports_without_reportlab)


def openpyxl_guarded():
    import services.teacher_report_service as trs
    assert hasattr(trs, "OPENPYXL_AVAILABLE"), "گارد openpyxl اضافه نشده است"
    src = open(os.path.join(ROOT, "services", "teacher_report_service.py"),
               encoding="utf-8").read()
    # import باید داخل try باشد، نه بی‌قید در سطح ماژول
    head = src.split("class TeacherReportService")[0]
    assert re.search(r"try:\s*\n\s*from openpyxl import Workbook", head), (
        "import openpyxl هنوز بدون گارد است")
    assert "if not OPENPYXL_AVAILABLE" in src, "پیام خطای خوانا اضافه نشده است"


check("services/teacher_report_service.py وابسته به openpyxl را گارد می‌کند",
      openpyxl_guarded)


# ============================================================
print()
print("=" * 74)
print("۶) آرگومان days=None (TypeError در timedelta)")
print("=" * 74)


def upcoming_sessions_days_none():
    r = CounselingSessionDAL().get_upcoming_sessions(days=None)
    assert isinstance(r, list), f"باید لیست برگرداند: {type(r)}"


check("CounselingSessionDAL.get_upcoming_sessions(days=None) نمی‌شکند",
      upcoming_sessions_days_none)


def daily_summary_days_none():
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        r = ObservationDAL().get_daily_observation_summary(days=None)
    out = log.getvalue()
    assert "NoneType" not in out, f"خطای timedelta هنوز چاپ می‌شود: {out[:200]}"
    assert isinstance(r, (list, dict)), f"خروجی نامعتبر: {type(r)}"


check("ObservationDAL.get_daily_observation_summary(days=None) خطا چاپ نمی‌کند",
      daily_summary_days_none)


# ============================================================
print()
print("=" * 74)
print("۷) متن گزارش‌ها: کاراکتر فارسی به‌جای عربی")
print("=" * 74)

ARABIC = re.compile("[\u0643\u064a\u0629]")   # ك  ي  ة


def no_arabic_chars_in_user_visible_text():
    bad = []
    files = ("services/teacher_report_service.py", "services/report_generator.py",
             "utils/report_template.py")
    for rel in files:
        p = os.path.join(ROOT, *rel.split("/"))
        if not os.path.exists(p):
            continue
        for i, line in enumerate(open(p, encoding="utf-8"), 1):
            if line.lstrip().startswith("#"):
                continue          # کامنت‌ها به کاربر نمایش داده نمی‌شوند
            if ARABIC.search(line):
                bad.append(f"{rel}:{i}")
    assert not bad, f"کاراکتر عربی در متن گزارش باقی مانده: {bad[:10]}"


check("در متن گزارش‌ها «ك»/«ي» عربی نمانده است", no_arabic_chars_in_user_visible_text)


def report_titles_are_persian():
    src = open(os.path.join(ROOT, "services", "teacher_report_service.py"),
               encoding="utf-8").read()
    assert "گزارش عملکرد معلم" in src, "عنوان گزارش هنوز «عملكرد» است"
    assert "آمار کلی" in src
    assert "سال تحصیلی" in src


check("عنوان‌های گزارش معلم با «ک» و «ی» فارسی نوشته شده‌اند",
      report_titles_are_persian)


# ============================================================
print()
print("=" * 74)
print("۸) خروجی واقعی گزارش معلم (Excel و PDF)")
print("=" * 74)


def teacher_report_exports():
    tps = TeacherPerformanceService()
    data = tps.get_teacher_performance(CTX["teacher1"].id)
    assert data, "داده گزارش معلم خالی است"

    xlsx = os.path.join(TMP, "teacher.xlsx")
    pdf = os.path.join(TMP, "teacher.pdf")
    svc = TeacherReportService()
    svc.export_to_excel(data, xlsx)
    svc.export_to_pdf(data, pdf)

    assert os.path.getsize(xlsx) > 1000, f"فایل Excel خالی است: {os.path.getsize(xlsx)}"
    with open(xlsx, "rb") as f:
        assert f.read(2) == b"PK", "فایل Excel قالب درست ندارد"
    assert os.path.getsize(pdf) > 1000, f"فایل PDF خالی است: {os.path.getsize(pdf)}"
    with open(pdf, "rb") as f:
        assert f.read(4) == b"%PDF", "فایل PDF قالب درست ندارد"


check("گزارش معلم به Excel و PDF واقعی تبدیل می‌شود", teacher_report_exports)


def teacher_report_pdf_service():
    out = os.path.join(TMP, "teacher_perf.pdf")
    ok = TeacherPerformanceService().export_teacher_report_pdf(
        CTX["teacher1"].id, out)
    assert ok, f"خروجی ناموفق: {ok}"
    assert os.path.exists(out) and os.path.getsize(out) > 1000


check("export_teacher_report_pdf فایل تولید می‌کند", teacher_report_pdf_service)


# ============================================================
print()
print("=" * 74)
print("۹) سناریوی کامل کاربر (ثبت → جست‌وجو → گزارش)")
print("=" * 74)


def full_user_journey():
    # ۱) مشاهده تازه ثبت می‌شود
    obs = ObservationService().create_observation({
        "student_id": CTX["student2"].id, "staff_id": CTX["teacher2"].id,
        "observation_date": "1404/06/25",
        "description": "کمک به همکلاسی در حل تمرین", "behavior": "کمک به همکلاسی",
        "location": "کلاس درس", "behavior_type": "مثبت", "severity": 1,
    }, user_id=CTX["teacher2"].id)
    assert obs and obs.id, "ثبت مشاهده ناموفق"

    # ۲) بلافاصله با متنش پیدا می‌شود
    found = ObservationService().search_observations("همکلاسی")
    assert any(o.id == obs.id for o in found), "مشاهده تازه با جست‌وجو پیدا نشد"

    # ۳) در گزارش معلم هم می‌آید
    data = TeacherPerformanceService().get_teacher_performance(CTX["teacher2"].id)
    assert data.get("students") is not None, "گزارش معلم داده ندارد"

    # ۴) در جست‌وجوی پیشرفته با فیلتر دانش‌آموز هم می‌آید
    r = AdvancedSearchService().search_observations(
        {"student_id": CTX["student2"].id})
    assert any(o.id == obs.id for o in r), "در جست‌وجوی پیشرفته پیدا نشد"


check("چرخه کامل: ثبت مشاهده ← جست‌وجو ← گزارش معلم ← جست‌وجوی پیشرفته",
      full_user_journey)


# ============================================================
print()
print("=" * 74)
ok = sum(1 for _, s, _ in RESULTS if s)
fail = len(RESULTS) - ok
print(f"نتیجه نهایی:  موفق: {ok}   ناموفق: {fail}")
print("=" * 74)
for title, success, err in RESULTS:
    if not success:
        print(f"  ✗ {title}\n      {err}")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if fail == 0 else 1)
