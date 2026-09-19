"""
اسکریپت راستی‌آزمایی اصلاحات PARTO — دور سوم (بازرسی مجدد برنچ)
================================================================
این فایل را در پوشه ریشه پروژه (کنار main.py) بگذارید و اجرا کنید:

    python verify_fixes3.py

همه آزمون‌ها روی **دیتابیس موقت** اجرا می‌شوند؛ یعنی به
database/partow.db واقعی شما و به داده‌هایتان هیچ آسیبی نمی‌رسد.

این اسکریپت مکمل verify_fixes.py (دور اول: ۱۷ آزمون) و
verify_fixes2.py (دور دوم: ۳۲ آزمون) است.

دور سوم این سه باگ را پوشش می‌دهد:

  🔴 باگ ۲۱ — StaffDAL.delete() حذف فیزیکی می‌کرد (تنها DELETE FROM در
     کل پروژه). چون PRAGMA foreign_keys = ON است و یازده جدول به
     staff.id کلید خارجی با ON DELETE CASCADE دارند، یک کلیک روی
     «حذف» در صفحهٔ تنظیمات، همهٔ مشاهده‌ها، مداخلات، پیگیری‌ها،
     جلسات مشاوره، مصاحبه‌های والدین، غربالگری‌ها، تفسیرها،
     انتساب‌ها و حساب کاربری آن فرد را **برای همیشه** نابود می‌کرد —
     بدون هیچ ردی در گزارش حسابرسی.

  🟠 باگ ۲۰ — StudentAcademicProfile.STATUS_ARCHIVED روی مدل تعریف
     نشده بود، ولی delete() و archive() پرونده هر دو به آن ارجاع
     می‌دادند ⇒ هر دو ۱۰۰٪ با AttributeError شکست می‌خوردند و
     restore() هم اصلاً وجود نداشت.

  🟠 باگ ۲۲ — تریگرهای حسابرسی، شناسهٔ کاربر جاری را در
     audit_logs.user_id می‌نویسند که به staff.id کلید خارجی دارد.
     اعتبارسنجیِ آن شناسه «بعد از» _initialize_database() انجام
     می‌شد، در حالی که INSERTهای seed «داخل» آن اجرا می‌شوند ⇒ با
     شناسهٔ ناموجود، ساخت دیتابیس و هر نوشتن دیگری با خطای
     گمراه‌کنندهٔ FOREIGN KEY constraint failed شکست می‌خورد.

به‌علاوه دو آزمون انباشته که کل دور سوم را جمع‌بندی می‌کنند:
  • نشتی حذف منطقی در همهٔ DALهای اصلی (رکورد حذف‌شده در خروجی نیاید)
  • استحکام روی دیتابیس کاملاً خالی (سناریوی نصب تازه در مدرسهٔ جدید)

خروجی مورد انتظار: همه موارد ✅ و در پایان «موفق: N  ناموفق: 0».
"""

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TMP = tempfile.mkdtemp(prefix="parto_verify3_")
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
    """اجرای یک آزمون و ثبت نتیجه (بدون توقف در صورت شکست)"""
    import contextlib
    import io
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            fn()
        RESULTS.append((title, True, ""))
        print(f"  ✅ {title}")
    except AssertionError as e:
        RESULTS.append((title, False, str(e)))
        print(f"  ❌ {title}\n      {e}")
    except Exception as e:
        import traceback
        tb = traceback.format_exc().strip().splitlines()
        RESULTS.append((title, False, f"{type(e).__name__}: {e}"))
        print(f"  ❌ {title}\n      {type(e).__name__}: {e}")
        if tb:
            print(f"      {tb[-2].strip()[:110]}")


def _fresh_connection(db_path=None):
    """ساختن اتصال تازه (singleton را ریست می‌کند)"""
    from database.connection import DatabaseConnection
    DatabaseConnection._instance = None
    DatabaseConnection._connection = None
    DatabaseConnection._initialized = False
    DatabaseConnection._current_user_id = None
    if db_path:
        dbc.DB_PATH = db_path
        settings.DB_PATH = db_path
    conn = DatabaseConnection().get_connection(user_id=1)
    return DatabaseConnection(), conn


DBCON, CONN = _fresh_connection(DB)


def _restore_main():
    """
    بعضی آزمون‌ها singleton را به یک دیتابیس موقت دیگر می‌برند.
    اگر بعد از آن‌ها اتصال اصلی برنگردد، آزمون‌های بعدی با DALهایی
    کار می‌کنند که به دیتابیس اشتباه وصل‌اند (و خطای FOREIGN KEY
    بی‌ربط می‌گیرند). این تابع اتصال اصلی را برمی‌گرداند.
    """
    global DBCON, CONN
    dbc.DB_PATH = DB
    settings.DB_PATH = DB
    DBCON, CONN = _fresh_connection(DB)


# ============================================================
# دادهٔ پایهٔ آزمون
# ============================================================
import jdatetime                                # noqa: E402
from models.staff import Staff                  # noqa: E402
from models.student import Student              # noqa: E402
from models.student_academic_profile import StudentAcademicProfile  # noqa: E402
from models.observation import Observation      # noqa: E402
from models.intervention import Intervention    # noqa: E402
from models.followup import FollowUp            # noqa: E402
from models.parent_interview import ParentInterview              # noqa: E402
from models.teacher_assignment import TeacherAssignment          # noqa: E402
from models.counseling_session import CounselingSession          # noqa: E402
from dal.staff_dal import StaffDAL              # noqa: E402
from dal.student_dal import StudentDAL          # noqa: E402
from dal.student_academic_profile_dal import StudentAcademicProfileDAL  # noqa: E402
from dal.observation_dal import ObservationDAL  # noqa: E402
from dal.intervention_dal import InterventionDAL      # noqa: E402
from dal.followup_dal import FollowUpDAL        # noqa: E402
from dal.parent_interview_dal import ParentInterviewDAL          # noqa: E402
from dal.teacher_assignment_dal import TeacherAssignmentDAL      # noqa: E402
from dal.counseling_session_dal import CounselingSessionDAL      # noqa: E402

CTX = {}
_TODAY = jdatetime.date.today().strftime("%Y/%m/%d")


def _seed():
    CTX["year"] = CONN.execute(
        "SELECT id FROM academic_years WHERE is_active = 1").fetchone()[0]
    CTX["comp"] = CONN.execute(
        "SELECT id FROM competencies LIMIT 1").fetchone()[0]

    t = Staff()
    t.full_name = "خانم محمدی"
    t.role = "teacher"
    t.is_active = 1
    CTX["teacher"] = StaffDAL().create(t).id

    coun = Staff()
    coun.full_name = "آقای رضایی"
    coun.role = "counselor"
    coun.is_active = 1
    CTX["counselor"] = StaffDAL().create(coun).id

    s = Student()
    s.first_name = "سارا"
    s.last_name = "کریمی"
    s.national_code = "0011111111"
    s.birth_date = "1395/02/02"
    s.father_name = "علی"
    s.is_active = 1
    CTX["student"] = StudentDAL().create(s).id

    p = StudentAcademicProfile()
    p.student_id = CTX["student"]
    p.academic_year_id = CTX["year"]
    p.grade = 4
    p.class_name = "ب"
    p.status = "active"
    CTX["profile"] = StudentAcademicProfileDAL().create(p).id

    obs_ids = []
    for k in range(5):
        o = Observation()
        o.student_profile_id = CTX["profile"]
        o.staff_id = CTX["teacher"]
        o.competency_id = CTX["comp"]
        o.observation_date = _TODAY
        o.location = "کلاس"
        o.description = f"مشاهدهٔ شمارهٔ {k + 1} سارا"
        o.antecedent = "زمینه"
        o.behavior = "رفتار"
        o.consequence = "پیامد"
        o.behavior_type = "مثبت"
        o.severity = 3
        obs_ids.append(ObservationDAL().create(o).id)
    CTX["obs"] = obs_ids

    i = Intervention()
    i.student_profile_id = CTX["profile"]
    i.staff_id = CTX["teacher"]
    i.observation_id = obs_ids[0]
    i.type = "آموزشی"
    i.date = _TODAY
    i.description = "مداخله برای سارا"
    i.goal = "هدف"
    i.status = "completed"
    CTX["intervention"] = InterventionDAL().create(i).id

    f = FollowUp()
    f.intervention_id = CTX["intervention"]
    f.staff_id = CTX["teacher"]
    f.date = _TODAY
    f.method = "حضوری"
    f.description = "پیگیری سارا"
    f.status = "done"
    CTX["followup"] = FollowUpDAL().create(f).id

    pi = ParentInterview()
    pi.student_profile_id = CTX["profile"]
    pi.staff_id = CTX["teacher"]
    pi.interview_date = _TODAY
    pi.interview_method = "حضوری"
    pi.interviewer_name = "خانم محمدی"
    pi.parent_name = "علی کریمی"
    pi.topic = "وضعیت سارا"
    pi.summary = "خلاصه"
    pi.status = "completed"
    CTX["interview"] = ParentInterviewDAL().create(pi).id

    ta = TeacherAssignment()
    ta.staff_id = CTX["teacher"]
    ta.student_id = CTX["student"]
    ta.academic_year_id = CTX["year"]
    ta.role = "teacher"
    CTX["assignment"] = TeacherAssignmentDAL().create(ta).id

    cs = CounselingSession()
    cs.student_profile_id = CTX["profile"]
    cs.counselor_id = CTX["counselor"]
    cs.session_date = _TODAY
    cs.session_time = "10:00"
    cs.duration_minutes = 30
    cs.type = "فردی"
    cs.method = "گفتگو"
    cs.topic = "اضطراب"
    cs.summary = "خلاصه"
    cs.status = "completed"
    CTX["session"] = CounselingSessionDAL().create(cs).id


_seed()


def _count(table):
    return CONN.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _src(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def _code_only(text):
    """حذف خط‌های توضیح تا جست‌وجو در متن کد دچار خطای مثبت نشود"""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        out.append(line)
    return "\n".join(out)


# ============================================================
print("=" * 74)
print("بخش ۱ — باگ ۲۰: STATUS_ARCHIVED و حذف/بایگانی/بازگردانی پرونده")
print("=" * 74)


def model_has_archived():
    assert hasattr(StudentAcademicProfile, "STATUS_ARCHIVED"), \
        "STATUS_ARCHIVED روی مدل تعریف نشده"
    assert StudentAcademicProfile.STATUS_ARCHIVED == "archived", \
        "مقدار STATUS_ARCHIVED درست نیست"


check("مدل StudentAcademicProfile ثابت STATUS_ARCHIVED دارد", model_has_archived)


def archived_in_choices():
    values = [v for v, _ in StudentAcademicProfile.STATUS_CHOICES]
    assert "archived" in values, f"'archived' در STATUS_CHOICES نیست: {values}"
    labels = dict(StudentAcademicProfile.STATUS_CHOICES)
    assert labels["archived"], "برچسب فارسی «بایگانی‌شده» خالی است"


check("«بایگانی‌شده» در STATUS_CHOICES و برچسب فارسی دارد", archived_in_choices)


def status_display_archived():
    p = StudentAcademicProfile()
    p.status = "archived"
    assert p.status_display == "بایگانی‌شده", \
        f"status_display اشتباه است: {p.status_display!r}"


check("status_display برای پروندهٔ بایگانی‌شده «بایگانی‌شده» می‌دهد",
      status_display_archived)


def validate_accepts_archived():
    p = StudentAcademicProfile()
    p.student_id = CTX["student"]
    p.academic_year_id = CTX["year"]
    p.grade = 4
    p.status = "archived"
    errs = p.validate()
    assert not errs, f"validate() وضعیت archived را رد کرد: {errs}"


check("validate() وضعیت «بایگانی‌شده» را می‌پذیرد", validate_accepts_archived)


def profile_delete_works():
    """قبل از اصلاح: AttributeError: ... has no attribute 'STATUS_ARCHIVED'"""
    pdal = StudentAcademicProfileDAL()
    s2 = Student()
    s2.first_name = "رضا"
    s2.last_name = "حذفی"
    s2.national_code = "0022222222"
    s2.birth_date = "1395/03/03"
    s2.father_name = "پدر"
    s2.is_active = 1
    sid = StudentDAL().create(s2).id
    p = StudentAcademicProfile()
    p.student_id = sid
    p.academic_year_id = CTX["year"]
    p.grade = 3
    p.class_name = "ج"
    p.status = "active"
    pid = pdal.create(p).id
    CTX["del_profile"] = pid

    assert pdal.delete(pid, user_id=1) is True, "delete() مقدار True نداد"
    row = CONN.execute(
        "SELECT is_deleted, deleted_by, status FROM student_academic_profiles "
        "WHERE id = ?", (pid,)).fetchone()
    assert row is not None, "رکورد پرونده کاملاً از بین رفت (حذف فیزیکی!)"
    assert row[0] == 1, f"is_deleted=1 نشد: {row[0]}"
    assert row[1] == 1, f"deleted_by ثبت نشد: {row[1]}"
    assert row[2] == "archived", f"status به archived نرفت: {row[2]!r}"


check("delete() پرونده کار می‌کند و حذف منطقی می‌کند (نه AttributeError)",
      profile_delete_works)


def profile_delete_keeps_records():
    pid = CTX["del_profile"]
    row = CONN.execute(
        "SELECT status_history FROM student_academic_profiles WHERE id = ?",
        (pid,)).fetchone()
    import json
    hist = json.loads(row[0] or "[]")
    assert hist, "تاریخچهٔ وضعیت ثبت نشده"
    assert hist[-1]["to"] == "archived", \
        f"آخرین رویداد تاریخچه archived نیست: {hist[-1]}"


check("حذف پرونده در تاریخچهٔ وضعیت ثبت می‌شود", profile_delete_keeps_records)


def profile_get_by_id_hides_deleted():
    assert StudentAcademicProfileDAL().get_by_id(CTX["del_profile"]) is None, \
        "get_by_id پروندهٔ حذف‌شده را برگرداند"


check("get_by_id پروندهٔ حذف‌شده را برنمی‌گرداند", profile_get_by_id_hides_deleted)


def profile_archive_works():
    """archive() فقط وضعیت را عوض می‌کند؛ is_deleted دست نمی‌خورد"""
    pdal = StudentAcademicProfileDAL()
    s3 = Student()
    s3.first_name = "مینا"
    s3.last_name = "بایگانی"
    s3.national_code = "0033333333"
    s3.birth_date = "1395/04/04"
    s3.father_name = "پدر"
    s3.is_active = 1
    sid = StudentDAL().create(s3).id
    p = StudentAcademicProfile()
    p.student_id = sid
    p.academic_year_id = CTX["year"]
    p.grade = 2
    p.class_name = "د"
    p.status = "active"
    pid = pdal.create(p).id
    CTX["arch_profile"] = pid
    CTX["arch_student"] = sid

    assert pdal.archive(pid) is True, "archive() مقدار True نداد"
    row = CONN.execute(
        "SELECT is_deleted, status FROM student_academic_profiles WHERE id = ?",
        (pid,)).fetchone()
    assert row[0] == 0, f"archive() نباید is_deleted را ۱ کند: {row[0]}"
    assert row[1] == "archived", f"status به archived نرفت: {row[1]!r}"


check("archive() پرونده کار می‌کند و is_deleted را دست نمی‌زند",
      profile_archive_works)


def archived_not_active_profile():
    """پروندهٔ بایگانی‌شده نباید «پروندهٔ فعال» شمرده شود"""
    got = StudentAcademicProfileDAL().get_active_by_student(CTX["arch_student"])
    assert got is None or got.id != CTX["arch_profile"], \
        "get_active_by_student پروندهٔ بایگانی‌شده را برگرداند"


check("get_active_by_student پروندهٔ «بایگانی‌شده» را برنمی‌گرداند",
      archived_not_active_profile)


def archived_visible_in_lists():
    """بایگانی ≠ حذف: رکورد باید در فهرست تاریخی دیده شود"""
    assert StudentAcademicProfileDAL().get_by_id(CTX["arch_profile"]) is not None, \
        "پروندهٔ بایگانی‌شده (نه حذف‌شده) از get_by_id ناپدید شد"


check("پروندهٔ بایگانی‌شده (حذف‌نشده) همچنان خواندنی است",
      archived_visible_in_lists)


def profile_restore_works():
    pdal = StudentAcademicProfileDAL()
    assert hasattr(pdal, "restore"), "restore() روی پرونده اصلاً وجود ندارد"
    pid = CTX["del_profile"]
    assert pdal.restore(pid) is True, "restore() مقدار True نداد"
    row = CONN.execute(
        "SELECT is_deleted, deleted_at, deleted_by, status "
        "FROM student_academic_profiles WHERE id = ?", (pid,)).fetchone()
    assert row[0] == 0, f"is_deleted به ۰ برنگشت: {row[0]}"
    assert row[1] is None, "deleted_at پاک نشد"
    assert row[2] is None, "deleted_by پاک نشد"
    assert row[3] == "inactive", \
        f"بازگردانی باید وضعیت را inactive بگذارد (نه active): {row[3]!r}"


check("restore() پرونده وجود دارد و درست کار می‌کند", profile_restore_works)


def update_status_rejects_unknown():
    """ریشهٔ «واژگان مرده»: وضعیت ناشناخته باید رد شود"""
    pdal = StudentAcademicProfileDAL()
    try:
        pdal.update_status(CTX["profile"], "closed")
    except ValueError as e:
        assert "closed" in str(e), f"پیام خطا وضعیت بد را نگفت: {e}"
        return
    raise AssertionError("update_status وضعیت نامعتبر 'closed' را پذیرفت")


check("update_status وضعیت نامعتبر ('closed') را با ValueError رد می‌کند",
      update_status_rejects_unknown)


def update_status_accepts_all_valid():
    pdal = StudentAcademicProfileDAL()
    for value, _label in StudentAcademicProfile.STATUS_CHOICES:
        pdal.update_status(CTX["profile"], value, "آزمون")
    pdal.update_status(CTX["profile"], "active", "بازگشت به فعال")
    row = CONN.execute(
        "SELECT status FROM student_academic_profiles WHERE id = ?",
        (CTX["profile"],)).fetchone()
    assert row[0] == "active", f"وضعیت نهایی active نیست: {row[0]!r}"


check("update_status همهٔ وضعیت‌های معتبر مدل را می‌پذیرد",
      update_status_accepts_all_valid)


def promotion_guard_includes_archived():
    code = _code_only(_src("views/pages/promotion_page.py"))
    m = re.search(r"terminal\s*=\s*\(([^)]*)\)", code, re.S)
    assert m, "گارد وضعیت‌های پایانی در promotion_page پیدا نشد"
    body = m.group(1)
    for name in ("STATUS_GRADUATED", "STATUS_DROPPED",
                 "STATUS_TRANSFERRED", "STATUS_ARCHIVED"):
        assert name in body, f"{name} در گارد وضعیت‌های پایانی نیست"


check("گارد صفحهٔ ارتقاء «بایگانی‌شده» را هم وضعیت پایانی می‌داند",
      promotion_guard_includes_archived)


def no_broken_class_constant_refs():
    """اسکن ایستا: هیچ ارجاعی به ثابت کلاسیِ ناموجود نمانده باشد"""
    import ast
    import importlib
    pat = re.compile(r"^(STATUS_|TYPE_|ROLE_|PRIORITY_|LEVEL_|DOMAIN_|METHOD_)")
    class_module = {}
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in
                   ("__pycache__", ".git", "full_test_artifacts", "reports")]
        for f in files:
            if not f.endswith(".py") or f.startswith("verify_fixes"):
                continue
            p = os.path.join(root, f)
            mod = os.path.relpath(p, ROOT)[:-3].replace(os.sep, ".")
            try:
                tree = ast.parse(open(p, encoding="utf-8").read())
            except Exception:
                continue
            for n in tree.body:
                if isinstance(n, ast.ClassDef):
                    class_module.setdefault(n.name, mod)
    bad = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in
                   ("__pycache__", ".git", "full_test_artifacts", "reports")]
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            try:
                tree = ast.parse(open(p, encoding="utf-8").read())
            except Exception:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute) or not pat.match(node.attr):
                    continue
                if not isinstance(node.value, ast.Name):
                    continue
                cname = node.value.id
                if cname not in class_module:
                    continue
                try:
                    cls = getattr(importlib.import_module(class_module[cname]), cname)
                except Exception:
                    continue
                if hasattr(cls, node.attr):
                    continue
                if any(hasattr(b, node.attr) for b in getattr(cls, "__mro__", [])):
                    continue
                bad.append(f"{cname}.{node.attr} در {os.path.relpath(p, ROOT)}:{node.lineno}")
    assert not bad, "ارجاع به ثابت کلاسی ناموجود: " + "; ".join(bad)


check("اسکن کل پروژه: هیچ ارجاعی به ثابت کلاسیِ ناموجود نمانده",
      no_broken_class_constant_refs)


# ============================================================
print()
print("=" * 74)
print("بخش ۲ — باگ ۲۱: حذف عضو کادر باید منطقی باشد، نه آبشاریِ ویرانگر")
print("=" * 74)


def _real_sql_strings(path):
    """
    رشته‌های SQL واقعیِ یک فایل — بدون docstringها.

    چرا لازم است: docstring متد delete() در staff_dal.py کدِ قدیمی و
    خراب را به عنوان توضیح نقل می‌کند («نسخهٔ قبلی این بود:
    DELETE FROM staff …»). یک اسکن متنی ساده همان نقل‌قول را به عنوان
    باگ گزارش می‌کرد.
    """
    import ast
    src = _src(path)
    tree = ast.parse(src)
    docstrings = set()
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef,
                           ast.ClassDef, ast.Module)):
            ds = ast.get_docstring(fn, clean=False)
            if ds:
                docstrings.add(ds.strip())
    out = []
    for node in ast.walk(tree):
        text = None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
        elif isinstance(node, ast.JoinedStr):
            text = "".join(
                "X" if isinstance(v, ast.FormattedValue)
                else str(getattr(v, "value", "")) for v in node.values)
        if not text or text.strip() in docstrings:
            continue
        owner = "?"
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if fn.lineno <= node.lineno <= getattr(fn, "end_lineno", node.lineno):
                    owner = fn.name
        out.append((node.lineno, owner, " ".join(text.split())))
    return out


def no_hard_delete_in_staff_delete():
    """delete() عادی باید منطقی باشد؛ permanent_delete() صریح مجاز است"""
    bad = [f"{owner}() خط {ln}" for ln, owner, text
           in _real_sql_strings("dal/staff_dal.py")
           if re.search(r"DELETE\s+FROM\s+staff", text, re.I)
           and owner != "permanent_delete"]
    assert not bad, f"حذف فیزیکی بیرون از permanent_delete: {'; '.join(bad)}"


check("delete() عضو کادر حذف فیزیکی نمی‌کند (فقط permanent_delete() مجاز است)",
      no_hard_delete_in_staff_delete)


def no_hard_delete_anywhere():
    """هیچ DAL: متد delete() عادی نباید DELETE FROM بزند"""
    bad = []
    for f in sorted(os.listdir(os.path.join(ROOT, "dal"))):
        if not f.endswith(".py") or f == "__init__.py":
            continue
        for ln, owner, text in _real_sql_strings(os.path.join("dal", f)):
            if not re.search(r"DELETE\s+FROM\s+[a-z_]+", text, re.I):
                continue
            if owner.startswith("permanent_delete") or owner.startswith("purge"):
                continue                      # حذف دائمیِ صریح و عمدی
            bad.append(f"{f}:{ln} در {owner}()")
    assert not bad, "حذف فیزیکی در متد غیرصریح: " + "; ".join(bad)


check("در هیچ DAL، delete() عادی حذف فیزیکی نمی‌کند",
      no_hard_delete_anywhere)


def permanent_delete_guarded():
    """حذف دائمی عضو کادرِ دارای سابقه باید رد شود"""
    tid = CTX["teacher"]
    n_obs = CONN.execute(
        "SELECT COUNT(*) FROM observations WHERE staff_id = ?", (tid,)).fetchone()[0]
    assert n_obs > 0, "پیش‌نیاز آزمون: معلم باید سابقه داشته باشد"
    try:
        StaffDAL().permanent_delete(tid)
    except ValueError as e:
        assert "سابقه" in str(e), f"پیام خطا واضح نیست: {e}"
        assert CONN.execute("SELECT COUNT(*) FROM staff WHERE id = ?",
                            (tid,)).fetchone()[0] == 1, \
            "رکورد با وجود ردشدن، حذف شد"
        assert _count("observations") == n_obs, \
            "مشاهده‌ها با وجود ردشدنِ حذف دائمی، کم شدند"
        return
    raise AssertionError("🔴 permanent_delete معلمِ دارای سابقه انجام شد")


check("permanent_delete عضو کادرِ دارای سابقه رد می‌شود و داده‌ها سالم می‌مانند",
      permanent_delete_guarded)


def permanent_delete_works_when_clean():
    """ولی برای رکورد اشتباهیِ بدون سابقه باید کار کند"""
    s = Staff()
    s.full_name = "رکورد اشتباهی"
    s.role = "other"
    s.is_active = 0
    sid = StaffDAL().create(s).id
    assert StaffDAL().permanent_delete(sid) is True, \
        "permanent_delete برای رکورد بدون سابقه کار نکرد"
    assert CONN.execute("SELECT COUNT(*) FROM staff WHERE id = ?",
                        (sid,)).fetchone()[0] == 0, "رکورد پاک نشد"


check("permanent_delete برای رکورد اشتباهیِ بدون سابقه کار می‌کند",
      permanent_delete_works_when_clean)


def staff_delete_is_soft():
    before = {t: _count(t) for t in
              ("observations", "interventions", "followups",
               "parent_interviews", "teacher_assignments", "staff")}
    CTX["before_delete"] = before
    CTX["audit_before"] = _count("audit_logs")

    tid = CTX["teacher"]
    assert StaffDAL().delete(tid, user_id=tid) is True, "delete() مقدار True نداد"

    row = CONN.execute(
        "SELECT is_deleted, is_active, deleted_at, deleted_by FROM staff WHERE id = ?",
        (tid,)).fetchone()
    assert row is not None, "🔴 ردیف staff کاملاً حذف شد (حذف فیزیکی!)"
    assert row[0] == 1, f"is_deleted=1 نشد: {row[0]}"
    assert row[1] == 0, f"is_active=0 نشد (ورود کاربر باید بسته شود): {row[1]}"
    assert row[2], "deleted_at ثبت نشد"
    assert row[3] == tid, f"deleted_by ثبت نشد: {row[3]}"


check("delete() عضو کادر حذف منطقی می‌کند (is_deleted/is_active/deleted_at/deleted_by)",
      staff_delete_is_soft)


def cascade_preserved():
    """مهم‌ترین آزمون دور سوم: سابقهٔ دانش‌آموز باید دست‌نخورده بماند"""
    before = CTX["before_delete"]
    lost = {}
    for table, n in before.items():
        now = _count(table)
        if now < n:
            lost[table] = (n, now)
    assert not lost, (
        "🔴 رکوردها با حذف معلم نابود شدند (ON DELETE CASCADE): " +
        ", ".join(f"{t}: {a}→{b}" for t, (a, b) in lost.items()))


check("با حذف معلم هیچ رکوردی نابود نمی‌شود (مشاهده/مداخله/پیگیری/مصاحبه/انتساب)",
      cascade_preserved)


def student_history_intact():
    n = CONN.execute(
        "SELECT COUNT(*) FROM observations WHERE student_profile_id = ?",
        (CTX["profile"],)).fetchone()[0]
    assert n == len(CTX["obs"]), \
        f"🔴 مشاهدات دانش‌آموز از {len(CTX['obs'])} به {n} کاهش یافت"


check("همهٔ ۵ مشاهدهٔ دانش‌آموز بعد از حذف معلمش باقی است",
      student_history_intact)


def audit_log_records_soft_delete():
    row = CONN.execute(
        "SELECT action, entity_type, entity_id FROM audit_logs "
        "WHERE entity_type = 'staff' AND entity_id = ? "
        "ORDER BY id DESC LIMIT 1", (CTX["teacher"],)).fetchone()
    assert row is not None, "🔴 حذف عضو کادر در گزارش حسابرسی ثبت نشد"
    assert row[0] in ("delete_soft", "delete", "soft_delete"), \
        f"اکشن حسابرسی حذف درست نیست: {row[0]!r}"
    assert _count("audit_logs") > CTX["audit_before"], \
        "تعداد رکوردهای حسابرسی زیاد نشد"


check("حذف منطقی عضو کادر در audit_logs ثبت می‌شود (تریگر اجرا شد)",
      audit_log_records_soft_delete)


def staff_hidden_from_lists():
    names = [s.full_name for s in StaffDAL().get_all()]
    assert "خانم محمدی" not in names, \
        f"عضو حذف‌شده همچنان در get_all() است: {names}"
    names_role = [s.full_name for s in StaffDAL().get_by_role("teacher")]
    assert "خانم محمدی" not in names_role, \
        f"عضو حذف‌شده همچنان در get_by_role() است: {names_role}"


check("عضو حذف‌شده از فهرست‌ها و انتخاب معلم پنهان می‌شود",
      staff_hidden_from_lists)


def staff_include_deleted_shows_them():
    names = [s.full_name for s in StaffDAL().get_all(include_deleted=True)]
    assert "خانم محمدی" in names, \
        f"include_deleted=True عضو حذف‌شده را برنگرداند: {names}"


check("get_all(include_deleted=True) عضو حذف‌شده را برمی‌گرداند (برای بازگردانی)",
      staff_include_deleted_shows_them)


def deleted_staff_name_still_resolvable():
    """گزارش‌های تاریخی باید نام فرد را نشان دهند، نه «نامشخص»"""
    s = StaffDAL().get_by_id(CTX["teacher"])
    assert s is not None, \
        "get_by_id عضو حذف‌شده را برنگرداند؛ نام در گزارش‌ها «نامشخص» می‌افتد"
    assert s.full_name == "خانم محمدی", f"نام اشتباه: {s.full_name!r}"
    assert StaffDAL().get_by_id(CTX["teacher"], include_deleted=False) is None, \
        "include_deleted=False باید None برگرداند"


check("نام عضو حذف‌شده برای سوابق تاریخی قابل بازیابی است",
      deleted_staff_name_still_resolvable)


def observation_still_shows_teacher_name():
    obs = ObservationDAL().get_by_id(CTX["obs"][0])
    assert obs is not None, "مشاهده از بین رفت"
    st = StaffDAL().get_by_id(obs.staff_id)
    assert st is not None and st.full_name == "خانم محمدی", \
        "نام معلمِ مشاهدهٔ ثبت‌شده قابل بازیابی نیست"


check("مشاهدهٔ ثبت‌شده هنوز نام معلمش را دارد",
      observation_still_shows_teacher_name)


def login_blocked_for_deleted_staff():
    """
    عضو کادر حذف‌شده/غیرفعال نباید بتواند وارد شود

    ===== به‌روزرسانی (بازرسی هفتم) =====
    این آزمون قبلاً وجود رشتهٔ «staff_active» در فایل
    views/dialogs/login_dialog.py را بررسی می‌کرد. در بازرسی هفتم
    SQL خام لاگین به `UserDAL.authenticate` منتقل شد (اولویت ۱)، پس
    آن رشته دیگر در دیالوگ نیست — ولی خودِ بررسی حذف نشده و حتی
    کامل‌تر است:
        • کاربر is_deleted=1 رد می‌شود
        • کاربر is_active=0 رد می‌شود
        • عضو کادر حذف‌شده (staff_deleted) رد می‌شود
        • عضو کادر غیرفعال (staff_active != 1) رد می‌شود
    پس آزمون حالا «محل قرارگیری کد» را نمی‌سنجد، بلکه رفتار واقعی
    ورود را می‌سنجد — که هدف اصلی این بررسی بود.
    """
    row = CONN.execute(
        "SELECT is_active FROM staff WHERE id = ?", (CTX["teacher"],)).fetchone()
    assert row[0] != 1, \
        "عضو حذف‌شده هنوز is_active=1 دارد ⇒ می‌تواند وارد برنامه شود"

    # ۱) منطق بررسی باید در لایهٔ دادهٔ احراز هویت باشد
    code = _src("dal/user_dal.py")
    for needle in ("staff_active", "staff_deleted"):
        assert needle in code, \
            f"بررسی «{needle}» عضو کادر در مسیر احراز هویت پیدا نشد"

    # ۲) آزمون رفتاری — با یک عضو کادر مستقل تا رکوردهای
    #    مشترک آزمون‌های دیگر دست‌نخورده بمانند
    from dal.user_dal import UserDAL
    from dal.staff_dal import StaffDAL
    from models.staff import Staff
    from models.user import User

    probe = Staff()
    probe.full_name = "عضو آزمون ورود"
    probe.role = "teacher"
    probe.is_active = 1
    probe_id = StaffDAL().create(probe).id

    ud = UserDAL()
    ghost = User()
    ghost.staff_id = probe_id
    ghost.username = "ghost_teacher"
    ghost.role = "teacher"
    ghost.is_active = 1
    ud.create(ghost, raw_password="Ghost@12345")

    # الف) وقتی همه‌چیز سالم است، ورود باید کار کند
    assert ud.authenticate("ghost_teacher", "Ghost@12345") is not None, \
        "ورود کاربرِ سالم کار نمی‌کند (پیش‌نیاز آزمون برقرار نیست)"

    # ب) عضو کادر غیرفعال → ورود ممنوع
    CONN.execute("UPDATE staff SET is_active = 0 WHERE id = ?", (probe_id,))
    assert ud.authenticate("ghost_teacher", "Ghost@12345") is None, \
        "کاربرِ عضو کادرِ غیرفعال توانست وارد شود!"

    # ج) برگشت به حالت فعال → ورود باید دوباره کار کند
    CONN.execute("UPDATE staff SET is_active = 1 WHERE id = ?", (probe_id,))
    assert ud.authenticate("ghost_teacher", "Ghost@12345") is not None, \
        "پس از فعال‌سازی دوباره، ورود کاربر کار نمی‌کند"

    # د) عضو کادر حذف‌شده (منطقی) → ورود ممنوع
    CONN.execute("UPDATE staff SET is_deleted = 1 WHERE id = ?", (probe_id,))
    assert ud.authenticate("ghost_teacher", "Ghost@12345") is None, \
        "کاربرِ عضو کادرِ حذف‌شده توانست وارد شود!"

    # پاک‌سازی اثر آزمون (کاربر و عضو آزمایشی)
    CONN.execute("UPDATE users SET is_deleted = 1 WHERE username = 'ghost_teacher'")
    CONN.execute("UPDATE staff SET is_deleted = 1 WHERE id = ?", (probe_id,))


check("ورود عضو کادر حذف‌شده به برنامه بسته می‌شود",
      login_blocked_for_deleted_staff)


def staff_restore_works():
    assert hasattr(StaffDAL(), "restore"), \
        "restore() روی عضو کادر اصلاً وجود ندارد"
    tid = CTX["teacher"]
    assert StaffDAL().restore(tid, user_id=1) is True, "restore() مقدار True نداد"
    row = CONN.execute(
        "SELECT is_deleted, is_active, deleted_at, deleted_by FROM staff WHERE id = ?",
        (tid,)).fetchone()
    assert row[0] == 0, f"is_deleted به ۰ برنگشت: {row[0]}"
    assert row[1] == 0, \
        f"بازگردانی نباید خودکار فعال کند (is_active={row[1]})"
    assert row[2] is None and row[3] is None, "deleted_at/deleted_by پاک نشدند"
    names = [s.full_name for s in StaffDAL().get_all(include_inactive=True)]
    assert "خانم محمدی" in names, "بعد از بازگردانی در فهرست نیست"


check("restore() عضو کادر وجود دارد و رکورد را برمی‌گرداند (بدون فعال‌سازی خودکار)",
      staff_restore_works)


def system_account_protected():
    row = CONN.execute(
        "SELECT id FROM staff WHERE role = 'system' LIMIT 1").fetchone()
    assert row is not None, "عضو کادر «سیستم» در دیتابیس نیست"
    try:
        StaffDAL().delete(row[0])
    except ValueError as e:
        assert "سیستم" in str(e), f"پیام خطا واضح نیست: {e}"
        return
    raise AssertionError("🔴 حساب «سیستم» حذف شد؛ حساب admin از دست می‌رود")


check("حساب «سیستم» (که حساب admin به آن وصل است) حذف‌شدنی نیست",
      system_account_protected)


def delete_idempotent_and_missing_id():
    assert StaffDAL().delete(999999) is False, \
        "حذف شناسهٔ ناموجود باید False بدهد، نه True"
    tid = CTX["teacher"]
    StaffDAL().delete(tid)
    assert StaffDAL().delete(tid) is False, \
        "حذف دوبارهٔ همان رکورد باید False بدهد"
    StaffDAL().restore(tid)


check("delete() در برابر شناسهٔ ناموجود و حذف دوباره False می‌دهد (نه True کاذب)",
      delete_idempotent_and_missing_id)


# ============================================================
print()
print("=" * 74)
print("بخش ۳ — باگ ۲۲: شناسهٔ کاربر جاری ناموجود نباید نوشتن را بشکند")
print("=" * 74)


def fresh_db_with_bad_user_id():
    """دیتابیس کاملاً تازه + user_id ناموجود ⇒ قبلاً FOREIGN KEY constraint failed"""
    db2 = os.path.join(TMP, "fresh_baduser.db")
    for ext in ("", "-wal", "-shm"):
        if os.path.exists(db2 + ext):
            os.remove(db2 + ext)
    try:
        conn2 = _fresh_connection(db2)[1]
        assert conn2 is not None, "اتصال ساخته نشد"
        n = conn2.execute("SELECT COUNT(*) FROM staff").fetchone()[0]
        assert n >= 1, f"seed انجام نشد (staff={n})"
    finally:
        _restore_main()


check("ساخت دیتابیس تازه با user_id ناموجود شکست نمی‌خورد (FOREIGN KEY)",
      fresh_db_with_bad_user_id)


def writes_work_with_bad_user_id():
    db2 = os.path.join(TMP, "write_baduser.db")
    for ext in ("", "-wal", "-shm"):
        if os.path.exists(db2 + ext):
            os.remove(db2 + ext)
    try:
        dbcon2, conn2 = _fresh_connection(db2)
        dbcon2._current_user_id = 424242          # شناسه‌ای که وجود ندارد
        s = Student()
        s.first_name = "تست"
        s.last_name = "کاربرنامعتبر"
        s.national_code = "0044444444"
        s.birth_date = "1395/05/05"
        s.father_name = "پدر"
        s.is_active = 1
        sid = StudentDAL().create(s).id           # قبلاً: IntegrityError
        assert sid, "ثبت دانش‌آموز با کاربر جاری نامعتبر شکست خورد"
        row = conn2.execute(
            "SELECT user_id FROM audit_logs WHERE entity_type = 'students' "
            "AND entity_id = ? ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
        assert row is not None, "رکورد حسابرسی ساخته نشد"
        assert row[0] is None, \
            f"audit_logs.user_id باید NULL باشد (نه شناسهٔ ناموجود): {row[0]}"
    finally:
        _restore_main()


check("نوشتن رکورد با شناسهٔ کاربر جاری ناموفق کار می‌کند (audit با NULL)",
      writes_work_with_bad_user_id)


def validate_method_exists():
    assert hasattr(DBCON, "_validate_current_user"), \
        "_validate_current_user وجود ندارد"
    saved = DBCON._current_user_id
    try:
        DBCON._current_user_id = 987654
        state = DBCON._validate_current_user()
        assert DBCON._current_user_id is None, \
            "شناسهٔ ناموجود باید None شود"
        assert state == DBCON._USER_CHECK_CLEARED, \
            f"وضعیت برگشتی درست نیست: {state!r}"
    finally:
        DBCON._current_user_id = saved


check("_validate_current_user شناسهٔ ناموجود را پاک می‌کند",
      validate_method_exists)


def validation_happens_before_init():
    """ترتیب درست: اعتبارسنجی باید «قبل از» _initialize_database() باشد"""
    code = _src("database/connection.py")
    i_validate = code.find("self._validate_current_user()")
    i_init = code.find("self._initialize_database()")
    assert i_validate != -1, "_validate_current_user() صدا زده نمی‌شود"
    assert i_init != -1, "_initialize_database() پیدا نشد"
    assert i_validate < i_init, \
        "🔴 اعتبارسنجی کاربر جاری بعد از _initialize_database() است؛ " \
        "INSERTهای seed با FOREIGN KEY constraint failed می‌شکنند"


check("اعتبارسنجی کاربر جاری قبل از مقداردهی اولیهٔ دیتابیس انجام می‌شود",
      validation_happens_before_init)


def set_current_user_still_validates():
    DBCON.set_current_user(987654)
    assert DBCON._current_user_id is None, \
        "set_current_user شناسهٔ ناموجود را پذیرفت"
    DBCON.set_current_user(CTX["teacher"])
    assert DBCON._current_user_id == CTX["teacher"], \
        "set_current_user شناسهٔ معتبر را نگه نداشت"


check("set_current_user همچنان شناسهٔ نامعتبر را رد می‌کند",
      set_current_user_still_validates)


# ============================================================
print()
print("=" * 74)
print("بخش ۴ — آزمون انباشته: نشتی «حذف منطقی» در همهٔ DALهای اصلی")
print("=" * 74)


def soft_delete_leak_suite():
    """
    برای هر موجودیت: دو رکورد می‌سازیم، یکی را حذف منطقی می‌کنیم، بعد
    همهٔ متدهای خواندنی را با شناسه‌های رکورد حذف‌شده صدا می‌زنیم.
    رکورد حذف‌شده نباید در هیچ خروجی‌ای ظاهر شود.
    (اسکن ایستا نمی‌تواند این را بفهمد چون کوئری‌ها پویا ساخته می‌شوند.)
    """
    import inspect
    from dal.goal_dal import GoalDAL
    from dal.extracurricular_dal import ExtracurricularDAL
    from dal.screening_dal import ScreeningDAL
    from dal.family_context_dal import FamilyContextDAL
    from dal.professional_interpretation_dal import ProfessionalInterpretationDAL
    from models.individual_goal import IndividualGoal
    from models.extracurricular_activity import ExtracurricularActivity
    from models.screening import Screening
    from models.family_context import FamilyContext
    from models.professional_interpretation import ProfessionalInterpretation

    # یک دانش‌آموز و پروندهٔ تازه برای این بخش
    s = Student()
    s.first_name = "نیما"
    s.last_name = "نشتی"
    s.national_code = "0055555555"
    s.birth_date = "1395/06/06"
    s.father_name = "پدر"
    s.is_active = 1
    sid = StudentDAL().create(s).id
    p = StudentAcademicProfile()
    p.student_id = sid
    p.academic_year_id = CTX["year"]
    p.grade = 5
    p.class_name = "ه"
    p.status = "active"
    pid = StudentAcademicProfileDAL().create(p).id

    tid = CTX["teacher"]
    tool = CONN.execute("SELECT id FROM screening_tools LIMIT 1").fetchone()

    g = IndividualGoal()
    g.student_profile_id = pid
    g.created_by = tid
    g.assigned_to = tid
    g.title = "هدف آزمون نشتی"
    g.description = "ت"
    g.domain = "educational"
    g.priority = "high"
    g.success_criteria = "معیار"
    g.target_date = _TODAY
    g.start_date = _TODAY
    g.status = "active"
    g.progress_percent = 10
    gid = GoalDAL().create(g).id

    a = ExtracurricularActivity()
    a.student_profile_id = pid
    a.teacher_id = tid
    a.title = "فعالیت آزمون نشتی"
    a.type = "sport"
    a.description = "ت"
    a.start_date = _TODAY
    a.end_date = _TODAY
    a.duration_hours = 5
    a.participation_level = "فعال"
    a.status = "active"
    aid = ExtracurricularDAL().create(a).id

    sc = Screening()
    sc.student_profile_id = pid
    sc.staff_id = CTX["counselor"]
    sc.tool_id = tool[0] if tool else None
    sc.tool_name = "چک‌لیست مشاهده رفتار"
    sc.execution_date = _TODAY
    sc.domain = "emotional"
    sc.status = "completed"
    sc.total_score = 10
    scid = ScreeningDAL().create(sc).id

    fc = FamilyContext()
    fc.student_profile_id = pid
    fc.guardian_status = "همراه"
    fc.notes = "زمینهٔ آزمون نشتی"
    fc.recorded_by = tid
    fc.parental_support = "خوب"
    fcid = FamilyContextDAL().create(fc).id

    ip = ProfessionalInterpretation()
    ip.student_profile_id = pid
    ip.staff_id = CTX["counselor"]
    ip.level = "کلاس"
    ip.domain = "emotional"
    ip.title = "تفسیر آزمون نشتی"
    ip.summary = "خلاصه"
    ip.detailed_text = "متن"
    ip.status = "final"
    ipid = ProfessionalInterpretationDAL().create(ip).id

    o = Observation()
    o.student_profile_id = pid
    o.staff_id = tid
    o.competency_id = CTX["comp"]
    o.observation_date = _TODAY
    o.location = "کلاس"
    o.description = "مشاهدهٔ آزمون نشتی"
    o.antecedent = "ز"
    o.behavior = "ر"
    o.consequence = "پ"
    o.behavior_type = "مثبت"
    o.severity = 3
    oid = ObservationDAL().create(o).id

    i = Intervention()
    i.student_profile_id = pid
    i.staff_id = tid
    i.observation_id = oid
    i.type = "آموزشی"
    i.date = _TODAY
    i.description = "مداخلهٔ آزمون نشتی"
    i.goal = "هدف"
    i.status = "planned"
    iid = InterventionDAL().create(i).id

    fu = FollowUp()
    fu.intervention_id = iid
    fu.staff_id = tid
    fu.date = _TODAY
    fu.method = "حضوری"
    fu.description = "پیگیری آزمون نشتی"
    fu.status = "pending"
    fuid = FollowUpDAL().create(fu).id

    cs = CounselingSession()
    cs.student_profile_id = pid
    cs.counselor_id = CTX["counselor"]
    cs.session_date = _TODAY
    cs.session_time = "11:00"
    cs.duration_minutes = 30
    cs.type = "فردی"
    cs.method = "گفتگو"
    cs.topic = "موضوع آزمون نشتی"
    cs.summary = "خ"
    cs.status = "completed"
    csid = CounselingSessionDAL().create(cs).id

    pi = ParentInterview()
    pi.student_profile_id = pid
    pi.staff_id = tid
    pi.interview_date = _TODAY
    pi.interview_method = "حضوری"
    pi.interviewer_name = "معلم"
    pi.parent_name = "پدر"
    pi.topic = "مصاحبهٔ آزمون نشتی"
    pi.summary = "خ"
    pi.status = "completed"
    piid = ParentInterviewDAL().create(pi).id

    cases = [
        (ObservationDAL, "delete", oid, "مشاهده"),
        (InterventionDAL, "delete", iid, "مداخله"),
        (FollowUpDAL, "delete", fuid, "پیگیری"),
        (CounselingSessionDAL, "delete", csid, "جلسهٔ مشاوره"),
        (GoalDAL, "delete", gid, "هدف فردی"),
        (ExtracurricularDAL, "delete", aid, "فعالیت"),
        (ScreeningDAL, "delete", scid, "غربالگری"),
        (FamilyContextDAL, "delete", fcid, "زمینهٔ خانواده"),
        (ParentInterviewDAL, "delete", piid, "مصاحبهٔ والدین"),
        (ProfessionalInterpretationDAL, "delete", ipid, "تفسیر حرفه‌ای"),
    ]

    argmap = {
        "student_profile_id": pid, "profile_id": pid, "student_id": sid,
        "observation_id": oid, "intervention_id": iid, "followup_id": fuid,
        "session_id": csid, "counseling_session_id": csid, "goal_id": gid,
        "activity_id": aid, "screening_id": scid, "context_id": fcid,
        "family_context_id": fcid, "interview_id": piid,
        "parent_interview_id": piid, "interpretation_id": ipid,
        "competency_id": CTX["comp"], "staff_id": tid, "teacher_id": tid,
        "counselor_id": CTX["counselor"], "user_id": 1,
        "academic_year_id": CTX["year"], "year_id": CTX["year"],
        "class_name": "ه", "grade": 5,
        "start_date": "1400/01/01", "end_date": "1500/12/29",
        "date_from": "1400/01/01", "date_to": "1500/12/29", "date": _TODAY,
        "from_date": "1400/01/01", "to_date": "1500/12/29",
        "observation_date": _TODAY,
        "include_deleted": False, "limit": 500, "offset": 0,
        "per_page": 500, "page": 1,
        "status": None, "type": None, "domain": None, "behavior_type": None,
        "severity": None, "text": "", "query": "", "search_term": "",
        "keyword": "", "name": "", "title": "", "level": None,
        "priority": None, "method": None, "location": None, "tags": None,
        "days": 36500, "period": "monthly", "result_type": None,
        "category": None, "activity_type": None, "tool_name": None,
    }
    intentional = ("get_deleted", "list_deleted", "get_archived")

    def ids_of(obj, depth=0):
        out = set()
        if depth > 4 or obj is None:
            return out
        if isinstance(obj, (list, tuple, set)):
            for x in obj:
                out |= ids_of(x, depth + 1)
            return out
        if isinstance(obj, dict):
            if isinstance(obj.get("id"), int):
                out.add(obj["id"])
            return out
        v = getattr(obj, "id", None)
        if isinstance(v, int):
            out.add(v)
        return out

    leaks = []
    calls = 0
    for cls, method, rec_id, label in cases:
        obj = cls()
        getattr(obj, method)(rec_id)
        for mname in sorted(dir(obj)):
            if mname.startswith("_") or mname.startswith(intentional):
                continue
            fn = getattr(obj, mname)
            if not callable(fn):
                continue
            if not mname.startswith(("get_", "search", "list", "find",
                                     "count", "has_")):
                continue
            try:
                sig = inspect.signature(fn)
            except Exception:
                continue
            kwargs = {}
            miss = False
            for pname, param in sig.parameters.items():
                if pname == "self":
                    continue
                if pname in argmap:
                    kwargs[pname] = argmap[pname]
                elif param.default is inspect.Parameter.empty:
                    miss = True
            if miss:
                continue
            try:
                got = ids_of(fn(**kwargs))
            except Exception:
                continue
            calls += 1
            if rec_id in got:
                leaks.append(f"{cls.__name__}.{mname}() → {label} id={rec_id}")

    # در پایان، دانش‌آموز و پروندهٔ همین بخش را هم حذف و بررسی می‌کنیم
    CONN.execute("UPDATE students SET is_deleted = 1 WHERE id = ?", (sid,))
    CONN.execute(
        "UPDATE student_academic_profiles SET is_deleted = 1 WHERE id = ?", (pid,))
    CONN.commit()
    for cls, rec_id in ((StudentDAL, sid), (StudentAcademicProfileDAL, pid)):
        obj = cls()
        for mname in sorted(dir(obj)):
            if mname.startswith("_") or mname.startswith(intentional):
                continue
            fn = getattr(obj, mname)
            if not callable(fn) or not mname.startswith(
                    ("get_", "search", "list", "find", "count", "has_")):
                continue
            try:
                sig = inspect.signature(fn)
            except Exception:
                continue
            kwargs = {}
            miss = False
            for pname, param in sig.parameters.items():
                if pname == "self":
                    continue
                if pname in argmap:
                    kwargs[pname] = argmap[pname]
                elif param.default is inspect.Parameter.empty:
                    miss = True
            if miss:
                continue
            try:
                got = ids_of(fn(**kwargs))
            except Exception:
                continue
            calls += 1
            if rec_id in got:
                leaks.append(f"{cls.__name__}.{mname}() → id={rec_id}")

    assert calls > 80, f"تعداد فراخوانی‌ها کم است ({calls})؛ آزمون معتبر نیست"
    assert not leaks, (
        f"🔴 {len(leaks)} نشتی حذف منطقی در {calls} فراخوانی: " +
        "; ".join(leaks[:8]))
    CTX["leak_calls"] = calls


check("نشتی حذف منطقی: رکورد حذف‌شده در هیچ خروجی‌ای ظاهر نمی‌شود",
      soft_delete_leak_suite)


def leak_suite_coverage():
    n = CTX.get("leak_calls", 0)
    assert n >= 80, f"پوشش آزمون نشتی کم است: {n} فراخوانی"


check("آزمون نشتی پوشش کافی دارد (دست‌کم ۸۰ فراخوانی واقعی)",
      leak_suite_coverage)


# ============================================================
print()
print("=" * 74)
print("بخش ۵ — آزمون انباشته: استحکام روی دیتابیس کاملاً خالی")
print("=" * 74)


def empty_database_robustness():
    """
    سناریوی نصب تازه در یک مدرسهٔ جدید: صفر دانش‌آموز، صفر مشاهده.
    داشبورد، تحلیل روند و سرویس‌های گزارش نباید استثنا بدهند
    (تقسیم بر صفر، ایندکس روی لیست خالی، کلید غایب در dict و…).
    """
    import inspect
    db2 = os.path.join(TMP, "empty_robust.db")
    for ext in ("", "-wal", "-shm"):
        if os.path.exists(db2 + ext):
            os.remove(db2 + ext)
    try:
        _fresh_connection(db2)
        from services.dashboard_service import DashboardService
        from services.trend_analysis_service import TrendAnalysisService
        from services.counseling_service import CounselingService
        from services.goal_service import GoalService
        from services.extracurricular_service import ExtracurricularService
        from services.advanced_search_service import AdvancedSearchService
        from services.observation_service import ObservationService
        from services.class_report_service import ClassReportService
        from services.teacher_report_service import TeacherReportService

        failures = []
        objs = []
        for cls in (DashboardService, TrendAnalysisService, CounselingService,
                    GoalService, ExtracurricularService, AdvancedSearchService,
                    ObservationService, ClassReportService,
                    TeacherReportService):
            try:
                objs.append(cls())
            except Exception as e:
                failures.append(f"{cls.__name__}(): {type(e).__name__}: {e}")

        for obj in objs:
            cname = type(obj).__name__
            for mname in sorted(dir(obj)):
                if mname.startswith("_"):
                    continue
                fn = getattr(obj, mname)
                if not callable(fn):
                    continue
                if not mname.startswith(("get_", "search", "list", "count",
                                         "analyze")):
                    continue
                try:
                    sig = inspect.signature(fn)
                except Exception:
                    continue
                required = [p for pn, p in sig.parameters.items()
                            if pn != "self" and p.default is inspect.Parameter.empty]
                if required:
                    continue
                try:
                    fn()
                except Exception as e:
                    failures.append(
                        f"{cname}.{mname}(): {type(e).__name__}: {e}")

        # چند فراخوانی با آرگومان که مسیرهای «دادهٔ خالی» را می‌سنجد
        ds = DashboardService()
        ts = TrendAnalysisService()
        for label, fn in (
            ("get_dashboard_data()", ds.get_dashboard_data),
            ("get_dashboard_data(year_id=1)",
             lambda: ds.get_dashboard_data(year_id=1)),
            ("get_dashboard_data(teacher_id=1)",
             lambda: ds.get_dashboard_data(teacher_id=1)),
            ("analyze_student_trend(1)", lambda: ts.analyze_student_trend(1)),
            ("get_student_timeline(1)", lambda: ts.get_student_timeline(1)),
            ("get_trend_chart_data(1)", lambda: ts.get_trend_chart_data(1)),
            ("get_student_progress_summary(1)",
             lambda: ts.get_student_progress_summary(1)),
            ("analyze_multi_year_trend(1)",
             lambda: ts.analyze_multi_year_trend(1)),
            ("get_multi_year_chart_data(1)",
             lambda: ts.get_multi_year_chart_data(1)),
        ):
            try:
                fn()
            except Exception as e:
                failures.append(f"{label}: {type(e).__name__}: {e}")

        assert not failures, (
            f"{len(failures)} استثنا روی دیتابیس خالی: " +
            "; ".join(failures[:6]))
        CTX["empty_calls"] = 9
    finally:
        _restore_main()


check("دیتابیس کاملاً خالی: داشبورد/روند/گزارش‌ها هیچ استثنا نمی‌دهند",
      empty_database_robustness)


def fresh_install_seeds_complete():
    """نصب تازه باید شایستگی‌ها، شاخص‌ها و ابزارهای غربالگری را seed کند"""
    db2 = os.path.join(TMP, "empty_robust.db")
    import sqlite3
    conn2 = sqlite3.connect(db2)
    try:
        n_comp = conn2.execute("SELECT COUNT(*) FROM competencies").fetchone()[0]
        n_ind = conn2.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
        n_beh = conn2.execute(
            "SELECT COUNT(*) FROM observable_behaviors").fetchone()[0]
        n_tool = conn2.execute("SELECT COUNT(*) FROM screening_tools").fetchone()[0]
        n_user = conn2.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn2.close()
    assert n_comp >= 28, f"شایستگی‌ها seed نشدند: {n_comp}"
    assert n_ind >= 84, f"شاخص‌ها seed نشدند: {n_ind}"
    assert n_beh >= 252, f"رفتارهای قابل مشاهده seed نشدند: {n_beh}"
    assert n_tool >= 3, f"ابزارهای غربالگری seed نشدند: {n_tool}"
    assert n_user >= 1, f"کاربر admin ساخته نشد: {n_user}"


check("نصب تازه: ۲۸ شایستگی / ۸۴ شاخص / ۲۵۲ رفتار / ۳ ابزار / کاربر admin",
      fresh_install_seeds_complete)


# ============================================================
print()
print("=" * 74)
print("بخش ۶ — باگ ۲۳: بازیابی پشتیبان واقعاً داده را برمی‌گرداند")
print("=" * 74)


def backup_restore_roundtrip():
    """
    چرخهٔ کامل: ثبت داده ← پشتیبان ← خراب‌کردن عمدی ← بازیابی ← مقایسه

    قبل از اصلاح، restore_backup() پیام «✅ بازیابی با موفقیت انجام شد»
    می‌داد ولی داده‌ها برنمی‌گشتند: فایل partow.db جایگزین می‌شد اما
    partow.db-wal و -shm دست‌نخورده می‌ماندند و SQLite، WAL قدیمی را
    (که همان حذف‌ها در آن بود) روی دیتابیس بازیابی‌شده بازپخش می‌کرد.
    """
    import sqlite3
    from utils.backup import BackupManager

    sub = os.path.join(TMP, "bk")
    for d in ("dbdir", "att", "bk"):
        os.makedirs(os.path.join(sub, d), exist_ok=True)
    db2 = os.path.join(sub, "dbdir", "partow.db")
    att = os.path.join(sub, "att")
    bkdir = os.path.join(sub, "bk")
    try:
        dbc.DB_PATH = db2
        settings.DB_PATH = db2
        settings.ATTACHMENTS_DIR = att
        _fresh_connection(db2)

        # --- دادهٔ واقعی ---
        s1 = Student()
        s1.first_name = "پویا"
        s1.last_name = "پشتیبانی"
        s1.national_code = "0077777771"
        s1.birth_date = "1395/07/07"
        s1.father_name = "پدر"
        s1.is_active = 1
        sid1 = StudentDAL().create(s1).id
        s2 = Student()
        s2.first_name = "پریا"
        s2.last_name = "پشتیبانی"
        s2.national_code = "0077777772"
        s2.birth_date = "1395/08/08"
        s2.father_name = "پدر"
        s2.is_active = 1
        StudentDAL().create(s2)

        p1 = StudentAcademicProfile()
        p1.student_id = sid1
        p1.academic_year_id = CTX["year"]
        p1.grade = 3
        p1.class_name = "الف"
        p1.status = "active"
        StudentAcademicProfileDAL().create(p1)

        with open(os.path.join(att, "نمونه.txt"), "w", encoding="utf-8") as fh:
            fh.write("محتوای پیوست فارسی")

        def snapshot():
            c = sqlite3.connect(db2)
            try:
                return {
                    "students": c.execute(
                        "SELECT COUNT(*) FROM students").fetchone()[0],
                    "profiles": c.execute(
                        "SELECT COUNT(*) FROM student_academic_profiles").fetchone()[0],
                    "names": [r[0] for r in c.execute(
                        "SELECT first_name FROM students ORDER BY id")],
                }
            finally:
                c.close()

        before = snapshot()
        assert before["students"] == 2, f"پیش‌نیاز: {before}"

        bm = BackupManager(db2, att, bkdir)
        res = bm.create_backup(name="آزمون", user_id=1, user_name="admin")
        assert res.get("success"), f"پشتیبان‌گیری شکست خورد: {res.get('message')}"
        bpath = res["file"]
        assert os.path.exists(bpath), "فایل پشتیبان ساخته نشد"
        assert os.path.exists(bpath + ".sha256"), \
            "فایل checksum کنار پشتیبان ساخته نشد"

        # --- خراب‌کردن عمدی ---
        c = sqlite3.connect(db2)
        c.execute("DELETE FROM students")
        c.commit()
        c.close()
        broken = snapshot()
        assert broken["students"] == 0, "پیش‌نیاز: داده خراب نشد"

        # --- بازیابی ---
        out = bm.restore_backup(bpath, user_id=1, user_name="admin")
        assert out.get("success"), f"بازیابی شکست خورد: {out.get('message')}"

        after = snapshot()
        assert after == before, (
            f"🔴 بازیابی داده را برنگرداند!\n"
            f"   قبل از خرابی: {before}\n"
            f"   بعد از بازیابی: {after}")

        # فایل‌های ژورنال باید پاک شده باشند
        for ext in ("-wal", "-shm"):
            assert not os.path.exists(db2 + ext), (
                f"🔴 {ext} بعد از بازیابی باقی مانده؛ WAL قدیمی روی "
                "دیتابیس بازیابی‌شده بازپخش می‌شود")

        # پیوست‌ها هم برگشته باشند
        assert os.path.exists(os.path.join(att, "نمونه.txt")), \
            "فایل پیوست بعد از بازیابی نیست"
    finally:
        settings.ATTACHMENTS_DIR = os.path.join(TMP, "attachments")
        _restore_main()


check("چرخهٔ پشتیبان‌گیری ← خرابی ← بازیابی: داده دقیقاً برمی‌گردد",
      backup_restore_roundtrip)


def restore_rejects_tampered_backup():
    """فایل پشتیبان دستکاری‌شده باید رد شود (نه اینکه دیتابیس را خراب کند)"""
    from utils.backup import BackupManager
    sub = os.path.join(TMP, "bk2")
    for d in ("dbdir", "att", "bk"):
        os.makedirs(os.path.join(sub, d), exist_ok=True)
    db2 = os.path.join(sub, "dbdir", "partow.db")
    try:
        dbc.DB_PATH = db2
        settings.DB_PATH = db2
        _fresh_connection(db2)
        bm = BackupManager(db2, os.path.join(sub, "att"), os.path.join(sub, "bk"))
        res = bm.create_backup(name="دستکاری", user_id=1, user_name="admin")
        assert res.get("success"), "پشتیبان‌گیری شکست خورد"
        bpath = res["file"]
        # یک بایت از ZIP را عوض کن تا checksum نخورد
        with open(bpath, "r+b") as fh:
            fh.seek(200)
            b = fh.read(1)
            fh.seek(200)
            fh.write(bytes([(b[0] + 1) % 256]))
        out = bm.restore_backup(bpath, user_id=1, user_name="admin")
        assert out.get("success") is False, \
            "🔴 پشتیبان دستکاری‌شده پذیرفته شد (checksum راستی‌آزمایی نمی‌شود)"
        assert "checksum" in out.get("message", "").lower() or "سالم نیست" in out.get("message", ""), \
            f"پیام خطا دربارهٔ checksum نیست: {out.get('message')}"
    finally:
        _restore_main()


check("پشتیبان دستکاری‌شده با پیام checksum رد می‌شود (راستی‌آزمایی دور اول)",
      restore_rejects_tampered_backup)


def restore_reports_missing_database():
    """پشتیبانی که دیتابیس ندارد نباید «موفق» گزارش شود"""
    import zipfile
    from utils.backup import BackupManager
    sub = os.path.join(TMP, "bk3")
    for d in ("dbdir", "att", "bk"):
        os.makedirs(os.path.join(sub, d), exist_ok=True)
    db2 = os.path.join(sub, "dbdir", "partow.db")
    try:
        dbc.DB_PATH = db2
        settings.DB_PATH = db2
        _fresh_connection(db2)
        bm = BackupManager(db2, os.path.join(sub, "att"), os.path.join(sub, "bk"))
        fake = os.path.join(sub, "bk", "خالی.partobak")
        with zipfile.ZipFile(fake, "w") as z:
            z.writestr("README.txt", "این پشتیبان دیتابیس ندارد")
        out = bm.restore_backup(fake, user_id=1, user_name="admin")
        assert out.get("success") is False, \
            "🔴 پشتیبانِ بدون دیتابیس، «موفق» گزارش شد"
    finally:
        _restore_main()


check("پشتیبانِ بدون فایل دیتابیس «موفق» گزارش نمی‌شود",
      restore_reports_missing_database)


# ============================================================
print()
print("=" * 74)
print("بخش ۷ — رفت‌وبرگشت update(): همهٔ فیلدها واقعاً ذخیره می‌شوند؟")
print("=" * 74)


def update_roundtrip():
    """
    برای هر موجودیت: ساخت ← تغییر «همه» فیلدهای قابل ویرایش ←
    update() ← خواندن مجدد با get_by_id ← مقایسه فیلد به فیلد.

    این الگو باگی را می‌گیرد که خیلی رایج و خیلی پنهان است: متد
    update() یکی از ستون‌ها را در SET نمی‌گذارد، پس کاربر فرم را
    ویرایش و ذخیره می‌کند، پیام «ذخیره شد» می‌گیرد، ولی آن فیلد
    به مقدار قبلی برمی‌گردد.
    """
    from models.family_context import FamilyContext
    from dal.family_context_dal import FamilyContextDAL

    # ستون‌هایی که در schema نوعشان TEXT است ولی مقدار شناسهٔ عددی
    # می‌گیرند؛ SQLite به خاطر TEXT affinity مقدار را به رشته تبدیل
    # می‌کند. این یک ویژگیِ schema است، نه باگِ update() — پس در
    # مقایسه با تبدیل نوع سنجیده می‌شود و جداگانه گزارش می‌شود.
    TEXT_ID_COLUMNS = {"next_action_by"}

    cases = []

    o = Observation()
    o.student_profile_id = CTX["profile"]
    o.staff_id = CTX["teacher"]
    o.competency_id = CTX["comp"]
    o.observation_date = _TODAY
    o.location = "کلاس"
    o.description = "توصیف اولیه"
    o.antecedent = "ز"
    o.behavior = "ر"
    o.consequence = "پ"
    o.behavior_type = "مثبت"
    o.severity = 3
    o.tags = "برچسب"
    cases.append(("Observation", ObservationDAL(), o, {
        "location": "حیاط", "description": "توصیف ویرایش‌شده",
        "antecedent": "ز۲", "behavior": "ر۲", "consequence": "پ۲",
        "behavior_type": "منفی", "severity": 5, "tags": "برچسب۲",
        "competency_id": CTX["comp"], "observation_date": _TODAY}))

    i = Intervention()
    i.student_profile_id = CTX["profile"]
    i.staff_id = CTX["teacher"]
    i.type = "آموزشی"
    i.date = _TODAY
    i.description = "مداخله اولیه"
    i.goal = "هدف اولیه"
    i.status = "planned"
    cases.append(("Intervention", InterventionDAL(), i, {
        "type": "رفتاری", "description": "مداخله ویرایش‌شده",
        "goal": "هدف ویرایش‌شده", "status": "in_progress"}))

    cs = CounselingSession()
    cs.student_profile_id = CTX["profile"]
    cs.counselor_id = CTX["counselor"]
    cs.session_date = _TODAY
    cs.session_time = "09:00"
    cs.duration_minutes = 30
    cs.type = "individual"
    cs.method = "in_person"
    cs.location = "اتاق مشاوره"
    cs.topic = "موضوع اولیه"
    cs.goals = "اهداف"
    cs.summary = "خلاصه اولیه"
    cs.details = "جزئیات"
    cs.recommendations = "توصیه"
    cs.homework = "تکلیف"
    cs.outcome = "نتیجه"
    cs.status = "scheduled"
    cases.append(("CounselingSession", CounselingSessionDAL(), cs, {
        "session_time": "11:30", "duration_minutes": 45, "type": "group",
        "method": "phone", "location": "تلفنی", "topic": "موضوع ویرایش‌شده",
        "goals": "اهداف۲", "summary": "خلاصه۲", "details": "جزئیات۲",
        "recommendations": "توصیه۲", "homework": "تکلیف۲",
        "outcome": "نتیجه۲", "status": "completed"}))

    fc = FamilyContext()
    fc.student_profile_id = CTX["profile"]
    fc.guardian_status = "همراه"
    fc.guardian_notes = "یادداشت"
    fc.siblings_brothers = 1
    fc.siblings_sisters = 2
    fc.family_members = 4
    fc.has_study_space = 1
    fc.has_desk = 0
    fc.parental_support = "متوسط"
    fc.economic_status = "متوسط"
    fc.family_stress = "کم"
    fc.notes = "یادداشت کلی"
    fc.recorded_by = CTX["teacher"]
    cases.append(("FamilyContext", FamilyContextDAL(), fc, {
        "guardian_status": "تنها", "guardian_notes": "یادداشت۲",
        "siblings_brothers": 3, "siblings_sisters": 0, "family_members": 6,
        "has_study_space": 0, "has_desk": 1, "parental_support": "خوب",
        "economic_status": "ضعیف", "family_stress": "زیاد",
        "notes": "یادداشت کلی۲"}))

    pi = ParentInterview()
    pi.student_profile_id = CTX["profile"]
    pi.staff_id = CTX["teacher"]
    pi.interview_date = _TODAY
    pi.interview_method = "in_person"
    pi.interviewer_name = "معلم"
    pi.parent_name = "پدر"
    pi.parent_relation = "پدر"
    pi.topic = "موضوع اولیه"
    pi.summary = "خلاصه"
    pi.details = "جزئیات"
    pi.result = "نتیجه"
    pi.next_action = "اقدام"
    pi.next_action_date = _TODAY
    pi.status = "scheduled"
    cases.append(("ParentInterview", ParentInterviewDAL(), pi, {
        "interview_method": "phone", "interviewer_name": "معلم۲",
        "parent_name": "مادر", "parent_relation": "مادر",
        "topic": "موضوع ویرایش‌شده", "summary": "خلاصه۲", "details": "جزئیات۲",
        "result": "نتیجه۲", "next_action": "اقدام۲", "status": "completed"}))

    failures = []
    checked_fields = 0
    for name, dal, obj, edits in cases:
        created = dal.create(obj)
        rid = getattr(created, "id", None)
        assert rid, f"{name}: create شناسه برنگرداند"
        for k, v in edits.items():
            setattr(obj, k, v)
        dal.update(obj)
        got = dal.get_by_id(rid)
        assert got is not None, f"{name}: بعد از update، get_by_id خالی بود"
        for k, v in edits.items():
            actual = getattr(got, k, "<<MISSING>>")
            checked_fields += 1
            if k in TEXT_ID_COLUMNS:
                if str(actual) != str(v):
                    failures.append(f"{name}.{k}: انتظار {v!r} ← {actual!r}")
                continue
            if actual != v:
                failures.append(f"{name}.{k}: انتظار {v!r} ← {actual!r}")

    assert checked_fields > 40, f"پوشش کم است: {checked_fields} فیلد"
    assert not failures, (
        f"{len(failures)} فیلد در update() ذخیره نمی‌شود: " +
        "; ".join(failures[:8]))
    CTX["roundtrip_fields"] = checked_fields


check("update() در ۵ موجودیت همهٔ فیلدهای ویرایش‌شده را واقعاً ذخیره می‌کند",
      update_roundtrip)


def roundtrip_coverage():
    n = CTX.get("roundtrip_fields", 0)
    assert n >= 40, f"پوشش تست رفت‌وبرگشت کم است: {n} فیلد"


check("تست رفت‌وبرگشت دست‌کم ۴۰ فیلد را سنجیده است", roundtrip_coverage)


# ============================================================
print()
print("=" * 74)
print("بخش ۸ — نبودِ پسرفت در اصلاحات دور اول و دوم")
print("=" * 74)


def search_methods_still_present():
    """باگ A دور دوم: متدهای جست‌وجو باید سر جایشان باشند"""
    for path, needed in (
        ("dal/observation_dal.py", ("def search", "def search_by_student",
                                    "def search_by_teacher")),
        ("dal/intervention_dal.py", ("def search", "def search_by_student",
                                     "def search_by_teacher")),
        ("dal/followup_dal.py", ("def search", "def search_by_student")),
        ("dal/academic_year_dal.py", ("def get_by_title",)),
    ):
        code = _code_only(_src(path))
        for n in needed:
            assert n in code, f"{n} در {path} نیست (پسرفت اصلاحات دور دوم)"


check("متدهای جست‌وجوی اضافه‌شده در دور دوم سر جایشان هستند",
      search_methods_still_present)


def search_still_works_after_round3():
    """جست‌وجو باید همچنان واقعی کار کند (نه فقط وجود داشته باشد)"""
    odal = ObservationDAL()
    got = odal.search("سارا")
    assert isinstance(got, list), "search لیست برنگرداند"
    got2 = odal.search_by_student(CTX["student"], "سارا")
    assert isinstance(got2, list), "search_by_student لیست برنگرداند"
    got3 = odal.search_by_teacher(CTX["teacher"], "سارا")
    assert isinstance(got3, list), "search_by_teacher لیست برنگرداند"


check("جست‌وجوی مشاهدات بعد از اصلاحات دور سوم هم کار می‌کند",
      search_still_works_after_round3)


def profile_active_filter_still_correct():
    """دور دوم: وضعیت‌های پایانی نباید «فعال» شمرده شوند"""
    code = _src("dal/student_academic_profile_dal.py")
    m = re.search(r"NOT IN \(([^)]*)\)\s*\n\s*ORDER BY sap\.id", code)
    assert m, "فیلتر وضعیت‌های پایانی در get_active_by_student پیدا نشد"
    body = m.group(1)
    for value in ("graduated", "dropped", "transferred", "archived"):
        assert value in body, f"'{value}' در فیلتر نیست"
    assert "COALESCE" in code, "COALESCE برای دادهٔ قدیمی با status خالی نیست"


check("فیلتر «پروندهٔ فعال» هنوز درست است (COALESCE + ۴ وضعیت پایانی)",
      profile_active_filter_still_correct)


def optional_dependencies_guarded():
    """دور دوم: نبود reportlab/openpyxl نباید برنامه را از پا بیندازد"""
    pdf = _code_only(_src("utils/persian_pdf.py"))
    assert "REPORTLAB_MISSING_MSG" in pdf, \
        "گارد reportlab در persian_pdf.py نیست"
    trs = _code_only(_src("services/teacher_report_service.py"))
    assert "OPENPYXL_AVAILABLE" in trs, \
        "گارد openpyxl در teacher_report_service.py نیست"
    assert not re.search(r"^from openpyxl import", trs, re.M), \
        "import بدون گارد openpyxl برگشته است"


check("گارد وابستگی‌های اختیاری (reportlab/openpyxl) سر جایش است",
      optional_dependencies_guarded)


def no_arabic_chars_in_reports():
    """دور دوم: متن گزارش‌ها باید «ک» و «ی» فارسی باشد"""
    bad = []
    for path in ("services/teacher_report_service.py",
                 "services/report_generator.py",
                 "utils/report_template.py",
                 "dal/staff_dal.py",
                 "dal/student_academic_profile_dal.py",
                 "database/connection.py"):
        text = _src(path)
        for ch in ("\u0643", "\u064a"):        # ك  ي
            if ch in text:
                bad.append(f"{path}: {ch!r}")
    assert not bad, "کاراکتر عربی پیدا شد: " + "; ".join(bad)


check("هیچ کاراکتر عربی «ك»/«ي» در فایل‌های تغییریافته نیست",
      no_arabic_chars_in_reports)


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

# مسیر موقت پاک می‌شود؛ database/partow.db واقعی هرگز باز نشد
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if fail == 0 else 1)
