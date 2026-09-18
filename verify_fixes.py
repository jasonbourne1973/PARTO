"""
اسکریپت راستی‌آزمایی اصلاحات PARTO
====================================
این فایل را در پوشه ریشه پروژه (کنار main.py) بگذارید و اجرا کنید:

    python verify_fixes.py

همه آزمون‌ها روی یک **دیتابیس موقت** اجرا می‌شوند؛ یعنی به
database/partow.db واقعی شما و به داده‌هایتان هیچ آسیبی نمی‌رسد.

خروجی مورد انتظار: همه موارد ✅ و در پایان «موفق: N  ناموفق: 0».
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TMP = tempfile.mkdtemp(prefix="parto_verify_")
DB_DIR = os.path.join(TMP, "database")
os.makedirs(DB_DIR, exist_ok=True)
DB = os.path.join(DB_DIR, "partow.db")

import config.settings as settings          # noqa: E402
settings.DB_PATH = DB
settings.ATTACHMENTS_DIR = os.path.join(TMP, "attachments")

import database.connection as dbc           # noqa: E402
dbc.DB_PATH = DB

RESULTS = []


def check(title, fn):
    try:
        fn()
        RESULTS.append((title, True, ""))
        print(f"  [OK]   {title}")
    except Exception as e:
        RESULTS.append((title, False, f"{type(e).__name__}: {e}"))
        print(f"  [FAIL] {title}\n         -> {type(e).__name__}: {str(e)[:200]}")


print("=" * 72)
print("۱) ساخت دیتابیس تازه (شبیه‌سازی نصب جدید)")
print("=" * 72)
with contextlib.redirect_stdout(io.StringIO()):
    conn = dbc.DatabaseConnection().get_connection()


def tables_and_columns():
    tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing_t = {"recommendations", "saved_filters", "backups"} - tabs
    assert not missing_t, f"جدول‌های مفقود: {sorted(missing_t)}"
    for t, c in (("attachments", "updated_at"),
                 ("observations", "indicator_id"),
                 ("observations", "observable_behavior_id")):
        cols = {x[1] for x in conn.execute(f"PRAGMA table_info({t})")}
        assert c in cols, f"ستون {t}.{c} وجود ندارد"


def seeds_present():
    for t, minimum in (("indicators", 1), ("observable_behaviors", 1), ("screening_tools", 1)):
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        assert n >= minimum, f"جدول {t} خالی است (تعداد={n})"


check("جدول‌های recommendations / saved_filters / backups ساخته شده‌اند", tables_and_columns)
check("ستون‌های attachments.updated_at و observations.indicator_id وجود دارند", tables_and_columns)
check("indicators / observable_behaviors / screening_tools seed شده‌اند", seeds_present)

print()
print("=" * 72)
print("۲) لایه سرویس: عملیات اصلی ثبت داده")
print("=" * 72)
with contextlib.redirect_stdout(io.StringIO()):
    from dal.staff_dal import StaffDAL
    from dal.student_dal import StudentDAL
    from models.staff import Staff
    from models.student import Student
    from services.advanced_search_service import AdvancedSearchService
    from services.dashboard_service import DashboardService
    from services.followup_service import FollowUpService
    from services.intervention_service import InterventionService
    from services.observation_service import ObservationService
    from services.recommendation_service import RecommendationService
    from services.student_service import StudentService

CTX = {}

_staff = Staff()
_staff.full_name = "کاربر راستی‌آزمایی"
_staff.role = "counselor"
_staff.is_active = 1
UID = StaffDAL().create(_staff).id


def _sid():
    assert CTX.get("student"), "دانش‌آموز ساخته نشد"
    return CTX["student"].id


def mk_student():
    CTX["student"] = StudentService().create_student({
        "first_name": "علی", "last_name": "محمدی", "national_code": "0012345678",
        "birth_date": "1390-05-10", "grade": 5, "class_name": "5/1",
    }, user_id=UID)


def mk_obs():
    CTX["observation"] = ObservationService().create_observation({
        "student_id": _sid(), "staff_id": UID, "observation_date": "1404/06/01",
        "description": "مشاهده راستی‌آزمایی", "behavior": "رفتار مثبت",
        "behavior_type": "مثبت", "severity": 2,
        "indicator_id": conn.execute("SELECT id FROM indicators LIMIT 1").fetchone()[0],
        "observable_behavior_id": conn.execute(
            "SELECT id FROM observable_behaviors LIMIT 1").fetchone()[0],
    }, user_id=UID)


def mk_intervention():
    r = InterventionService().create_intervention({
        "student_id": _sid(), "staff_id": UID, "title": "مداخله راستی‌آزمایی",
        "description": "توضیح مداخله", "date": "1404/06/01",
        "type": "individual", "status": "planned",
    }, user_id=UID)
    CTX["intervention"] = r.id if r else None


def mk_followup():
    assert CTX.get("intervention"), "مداخله ساخته نشد"
    FollowUpService().create_followup({
        "intervention_id": CTX["intervention"], "student_id": _sid(), "staff_id": UID,
        "date": "1404/06/10", "title": "پیگیری راستی‌آزمایی",
        "description": "توضیح پیگیری", "status": "pending",
    }, user_id=UID)


def three_layer_saved():
    row = conn.execute(
        "SELECT indicator_id, observable_behavior_id FROM observations WHERE id=?",
        (CTX["observation"].id,)).fetchone()
    assert row[0] is not None, "indicator_id در دیتابیس NULL است"
    assert row[1] is not None, "observable_behavior_id در دیتابیس NULL است"


def recommendation_saved():
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        RecommendationService().generate_recommendations(_sid())
    out = log.getvalue()
    assert "no such table" not in out, f"خطای جدول مفقود: {out[:200]}"


def saved_filter_works():
    r = AdvancedSearchService().save_filter(
        name="فیلتر راستی‌آزمایی", filter_type="student",
        filter_params={"grade": 5}, user_id=UID)
    assert r, "ذخیره فیلتر ناموفق بود"


check("ثبت دانش‌آموز (StudentService.create_student)", mk_student)
check("ثبت مشاهده (ObservationService.create_observation)", mk_obs)
check("ذخیره شاخص و رفتار قابل مشاهده روی مشاهده (ساختار سه‌لایه)", three_layer_saved)
check("ثبت مداخله (InterventionService.create_intervention)", mk_intervention)
check("ثبت پیگیری (FollowUpService.create_followup)", mk_followup)
check("تولید پیشنهاد بدون خطای «no such table: recommendations»", recommendation_saved)
check("ذخیره فیلتر جست‌وجو (جدول saved_filters)", saved_filter_works)
check("داشبورد (DashboardService.get_dashboard_data)",
      lambda: DashboardService().get_dashboard_data())

print()
print("=" * 72)
print("۳) پیوست‌ها و پشتیبان‌گیری")
print("=" * 72)
with contextlib.redirect_stdout(io.StringIO()):
    from dal.attachment_dal import AttachmentDAL
    from models.attachment import Attachment
    from utils.backup import BackupManager


def attachment_update():
    dal = AttachmentDAL()
    a = Attachment()
    a.entity_type = "student"
    a.entity_id = _sid()
    a.file_name = "a.png"
    a.file_path = os.path.join(TMP, "a.png")
    a.file_size = 10
    a.file_type = "image/png"
    with open(a.file_path, "w", encoding="utf-8") as f:
        f.write("x")
    created = dal.create(a)
    assert created and created.id, "پیوست ساخته نشد"
    created.file_name = "b.png"
    assert dal.update(created) is not False, "به‌روزرسانی پیوست ناموفق بود"
    assert dal.get_by_id(created.id).file_name == "b.png", "نام فایل جدید ذخیره نشد"


def backup_create():
    bdir = os.path.join(TMP, "backups")
    bm = BackupManager(DB, settings.ATTACHMENTS_DIR, bdir)
    assert hasattr(bm, "logger"), "BackupManager.logger ساخته نشد"
    out = bm.create_backup(name="verify_backup", user_id=UID, user_name="راستی‌آزمایی")
    assert isinstance(out, dict) and out.get("success"), f"پشتیبان‌گیری ناموفق: {out}"
    assert any(f.endswith(".partobak") for f in os.listdir(bdir)), "فایل پشتیبان ساخته نشد"


def backup_tampered_rejected():
    bdir = os.path.join(TMP, "backups")
    bf = os.path.join(bdir, "verify_backup.partobak")
    sha = bf + ".sha256"
    if os.path.exists(sha):
        with open(sha, "w", encoding="utf-8") as f:
            f.write("0" * 64)
    bm = BackupManager(DB, settings.ATTACHMENTS_DIR, bdir)
    out = bm.restore_backup(bf)
    assert isinstance(out, dict), "خروجی restore_backup نامعتبر"
    assert out.get("success") is False, "بازیابی با checksum دستکاری‌شده باید رد می‌شد"


check("ایجاد و به‌روزرسانی پیوست (ستون updated_at)", attachment_update)
check("پشتیبان‌گیری + ساخت checksum + وجود logger", backup_create)
check("رد شدن بازیابی وقتی checksum دستکاری شده باشد", backup_tampered_rejected)

print()
print("=" * 72)
print("۴) لایه‌بندی: لایه داده نباید به Qt وابسته باشد")
print("=" * 72)


def no_qt_in_data_layer():
    """فقط import های واقعی Qt را می‌شمارد (نه اشاره در کامنت‌ها)."""
    bad = []
    for pkg in ("dal", "services", "models", "database", "config", "data"):
        d = os.path.join(ROOT, pkg)
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames[:] = [x for x in dirnames if x != "__pycache__"]
            for f in filenames:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(dirpath, f)
                for line in open(path, encoding="utf-8", errors="ignore"):
                    code = line.split("#", 1)[0].strip()
                    if code.startswith(("import PySide6", "from PySide6")):
                        bad.append(os.path.relpath(path, ROOT))
                        break
    assert not bad, f"وابستگی Qt در لایه داده: {bad}"


def analytics_queries():
    """کوئری‌های آماری که قبلاً با «parameters are of unsupported type» می‌ترکیدند."""
    from dal.competency_dal import CompetencyDAL
    from dal.observation_dal import ObservationDAL
    from dal.recommendation_dal import RecommendationDAL
    from dal.student_dal import StudentDAL

    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        dist = ObservationDAL().get_observations_distribution_by_type()
        ObservationDAL().get_observations_distribution_by_location()
        ObservationDAL().get_observations_by_time_period()
        grades = StudentDAL().get_student_distribution_by_grade()
        StudentDAL().get_student_count_by_status()
        without = StudentDAL().get_students_without_observations()
        RecommendationDAL().get_recommendation_stats()
        CompetencyDAL().get_competency_avg_severity()
    out = log.getvalue()
    assert "unsupported type" not in out, f"کوئری آماری شکست خورد:\n{out[:400]}"
    assert isinstance(dist, dict) and dist.get("total") is not None, f"توزیع مشاهدات نامعتبر: {dist}"
    assert isinstance(grades, (list, dict)), "توزیع پایه‌ها نامعتبر"
    assert isinstance(without, list), "دانش‌آموزان بدون مشاهده باید لیست باشد"
    return dist


check("هیچ‌کدام از لایه‌های dal/services/models/database به PySide6 وابسته نیستند",
      no_qt_in_data_layer)

print()
print("=" * 72)
print("۵) کوئری‌های آماری داشبورد (قبلاً بی‌صدا شکست می‌خوردند)")
print("=" * 72)
check("توزیع مشاهدات / پایه‌ها / وضعیت / آمار پیشنهادات بدون خطا", analytics_queries)


def dashboard_analytics_filled():
    data = DashboardService().get_dashboard_data()
    an = data.get("analytics") or {}
    dist = an.get("observation_distribution") or {}
    assert dist, f"توزیع مشاهدات در داشبورد خالی است: {an}"
    assert dist.get("total", 0) >= 1, f"تعداد مشاهدات در داشبورد صفر است: {dist}"


check("داشبورد توزیع مشاهدات را واقعاً پر می‌کند", dashboard_analytics_filled)

print()
print("=" * 72)
ok = sum(1 for _, s, _ in RESULTS if s)
fail = len(RESULTS) - ok
print(f"نتیجه نهایی:  موفق: {ok}   ناموفق: {fail}")
print("=" * 72)
for title, success, err in RESULTS:
    if not success:
        print(f"  ✗ {title}\n      {err}")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if fail == 0 else 1)
