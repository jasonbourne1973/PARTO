"""
بررسی‌های دور دوازدهم: روند گام‌به‌گام، روایت چندسالهٔ منسجم و پایداری فنی

  A) روند جهت رشد با درنظرگرفتن بازه‌های میانی ............. ۵ بررسی
  B) گزارش چندساله از «فهرست سال‌ها» به «روایت منسجم» ...... ۵ بررسی
  C) نخ‌ایمنی اتصال/تراکنش/کاربر جاری ..................... ۵ بررسی
  D) پشتیبان امن (نسخه، Zip-Slip، شکست بلند) ................ ۴ بررسی
  E) حسابرسی یکپارچه با مقدار واقعی تغییرات ................. ۷ بررسی
  F) جلوگیری از اعلان تکراری ............................... ۲ بررسی
  G) یک مسیر واحد برای DAL تفسیر حرفه‌ای ................... ۲ بررسی
  H) شکست بلند Migration ناقص .............................. ۲ بررسی
  I) زمان‌بند پاکسازی و وابستگی‌های تست .................... ۳ بررسی
  J) رفع N+1 در پرونده و گزارش‌ها .......................... ۴ بررسی
  K) نگهبان‌های بدون پس‌روندگی (محتوای دور ۱۱) ............. ۴ بررسی

جمع: ۴۳ بررسی
"""

import contextlib
import io
import os
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = 0
FAIL = 0
FAILURES = []


def check(section, name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ [{section}] {name}")
    else:
        FAIL += 1
        FAILURES.append(f"[{section}] {name} {detail}")
        print(f"  ❌ [{section}] {name}  {detail}")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ============================================================
# آماده‌سازی دیتابیس موقت
# ============================================================
TMP = tempfile.mkdtemp(prefix="round12_verify_")
TEST_DB = os.path.join(TMP, "partow.db")

import config.settings as settings  # noqa: E402
import database.connection as dbc  # noqa: E402

_orig_s, _orig_c = settings.DB_PATH, dbc.DB_PATH
settings.DB_PATH = TEST_DB
dbc.DB_PATH = TEST_DB
dbc.DatabaseConnection._instance = None
dbc.DatabaseConnection._connection = None
dbc.DatabaseConnection._initialized = False
dbc.DatabaseConnection._current_user_id = None

with contextlib.redirect_stdout(io.StringIO()):
    db = dbc.DatabaseConnection()
    conn = db.get_connection(user_id=1)

from dal.competency_dal import CompetencyDAL  # noqa: E402
from dal.notification_dal import NotificationDAL  # noqa: E402
from dal.observation_dal import ObservationDAL  # noqa: E402
from dal.staff_dal import StaffDAL  # noqa: E402
from dal.student_academic_profile_dal import StudentAcademicProfileDAL  # noqa: E402
from dal.student_dal import StudentDAL  # noqa: E402
from dal.user_dal import UserDAL  # noqa: E402
from models.notification import Notification  # noqa: E402
from models.observation import Observation  # noqa: E402
from models.staff import Staff  # noqa: E402
from models.student import Student  # noqa: E402
from models.student_academic_profile import StudentAcademicProfile  # noqa: E402
from models.user import User  # noqa: E402
from services.notification_service import NotificationService  # noqa: E402
from services.report_generator import ReportGenerator  # noqa: E402
from utils.behavior_analysis import (  # noqa: E402
    DOMINANCE_RATIO,
    MIN_PATTERN_COUNT,
    classify_pattern,
    growth_direction,
)

report_gen = ReportGenerator()
notif_service = NotificationService()


def _period(label, positive, negative, neutral=0):
    return {'label': label, 'positive': positive, 'negative': negative,
            'neutral': neutral, 'total': positive + negative + neutral}


# ============================================================
print("=" * 76)
print("بخش A: روند گام‌به‌گام (بازه‌های میانی نادیده گرفته نمی‌شوند)")
print("=" * 76)

# رفتار دوبازه‌ای دقیقاً مثل قبل
stable = growth_direction([_period('ماه ۱', 6, 4), _period('ماه ۲', 3, 2)])
improving = growth_direction([_period('ماه ۱', 2, 8), _period('ماه ۲', 8, 2)])
declining = growth_direction([_period('ماه ۱', 8, 2), _period('ماه ۲', 2, 8)])
check("A", "رفتار دوبازه‌ای حفظ شده (ثبات/بهبود/افت)",
      stable['status'] == 'stable' and improving['status'] == 'improving'
      and declining['status'] == 'declining',
      f"{stable['status']}/{improving['status']}/{declining['status']}")

# جهش میانی: بهبود سپس افت → روند غیرقطعی (نه برآیند ابتدا/انتها)
spike = growth_direction([_period('مهر', 2, 8), _period('آبان', 6, 4),
                          _period('آذر', 1, 9)])
check("A", "تغییر جهت در بازهٔ میانی «تغییر ترکیبی» می‌شود (نه ابتدا/انتها)",
      spike['status'] == 'mixed' and spike['unanimous'] is False
      and [s['status'] for s in spike['steps']] == ['improving', 'declining'],
      f"{spike['status']} steps={[s['status'] for s in spike['steps']]}")

# سه بازهٔ یک‌جهت → همان جهت
up3 = growth_direction([_period('۱', 1, 9), _period('۲', 5, 5),
                        _period('۳', 9, 1)])
check("A", "سه بازهٔ یک‌جهتِ بهبود، «بهبود» گزارش می‌شود",
      up3['status'] == 'improving' and up3['unanimous'] is True
      and len(up3['steps']) == 2, up3['status'])

# تعداد مشاهدات همچنان شاخص رشد نیست
same_share = growth_direction([_period('۱', 6, 4), _period('۲', 60, 40),
                               _period('۳', 3, 2)])
check("A", "تعداد مشاهدات در تصمیم روند نقشی ندارد (سهم ثابت → ثبات)",
      same_share['status'] == 'stable'
      and ('شاخص رشد نیست' in same_share['volume_note']
           or 'بهبود رفتار نیست' in same_share['volume_note']
           or 'شاخص پیشرفت یا پسرفت نیست' in same_share['volume_note']),
      f"{same_share['status']} | {same_share['volume_note'][:60]}")

few = growth_direction([_period('۱', 5, 5)])
check("A", "کمتر از دو بازه → دادهٔ ناکافی",
      few['status'] == 'insufficient' and few['steps'] == [], few['status'])

# ============================================================
print()
print("=" * 76)
print("بخش B: روایت چندسالهٔ منسجم (تداوم، تغییر، اثربخشی)")
print("=" * 76)

with contextlib.redirect_stdout(io.StringIO()):
    st = Student()
    st.first_name = "روایت"
    st.last_name = "دوازدهم"
    st.national_code = "1212121212"
    st.is_active = 1
    student_id = StudentDAL().create(st).id

    y1 = conn.execute(
        "SELECT id, title FROM academic_years WHERE is_deleted = 0 ORDER BY id"
    ).fetchone()
    conn.execute(
        "INSERT INTO academic_years (title, is_active) VALUES ('1404-1405', 0)")
    conn.commit()
    y2id = conn.execute(
        "SELECT id FROM academic_years WHERE title = '1404-1405'").fetchone()[0]

    comps = CompetencyDAL().get_all()
    c_need, c_strength, c_changed = comps[0].id, comps[1].id, comps[2].id

    profile_ids = []
    for yid, grade in ((y1['id'], 1), (y2id, 2)):
        p = StudentAcademicProfile()
        p.student_id = student_id
        p.academic_year_id = yid
        p.grade = grade
        p.class_name = "الف"
        profile_ids.append(StudentAcademicProfileDAL().create(p).id)

    obs_dal = ObservationDAL()

    def _add_obs(pid, comp_id, btype, date):
        o = Observation()
        o.student_profile_id = pid
        o.staff_id = 1
        o.competency_id = comp_id
        o.observation_date = date
        o.description = "شرح آزمایشی"
        o.behavior = "رفتار ثبت‌شدهٔ آزمایشی"
        o.behavior_type = btype
        o.severity = 2
        return obs_dal.create(o).id

    # سال ۱: نیاز ماندگار (منفی×۲) + توانمندی ماندگار (مثبت×۲) + تغییریافته (مثبت×۲)
    _add_obs(profile_ids[0], c_need, "منفی", "1403/08/01")
    _add_obs(profile_ids[0], c_need, "منفی", "1403/09/01")
    _add_obs(profile_ids[0], c_strength, "مثبت", "1403/08/02")
    _add_obs(profile_ids[0], c_strength, "مثبت", "1403/09/02")
    _add_obs(profile_ids[0], c_changed, "مثبت", "1403/08/03")
    _add_obs(profile_ids[0], c_changed, "مثبت", "1403/09/03")
    # سال ۲: همان نیاز و توانمندی تکرار می‌شوند؛ سومی منفی می‌شود (تغییر الگو)
    _add_obs(profile_ids[1], c_need, "منفی", "1404/08/01")
    _add_obs(profile_ids[1], c_need, "منفی", "1404/09/01")
    _add_obs(profile_ids[1], c_strength, "مثبت", "1404/08/02")
    _add_obs(profile_ids[1], c_strength, "مثبت", "1404/09/02")
    _add_obs(profile_ids[1], c_changed, "منفی", "1404/08/03")
    _add_obs(profile_ids[1], c_changed, "منفی", "1404/09/03")

narrative = report_gen.generate_growth_narrative(student_id)
synth = narrative.get('synthesis') or {}

check("B", "جمع‌بندی مسیر رشد با کلیدهای ساخت‌یافته ساخته می‌شود",
      all(k in synth for k in ('text', 'persistent_strengths',
                               'persistent_needs', 'changed_areas',
                               'effective_years', 'totals')),
      str(sorted(synth.keys())))

need_names = [p['competency'] for p in synth.get('persistent_needs', [])]
strength_names = [p['competency'] for p in synth.get('persistent_strengths', [])]
c_need_title = CompetencyDAL().get_by_id(c_need).title
c_strength_title = CompetencyDAL().get_by_id(c_strength).title
check("B", "الگوهای ماندگار چندساله شناسایی می‌شوند",
      c_need_title in need_names and c_strength_title in strength_names,
      f"needs={need_names} strengths={strength_names}")

changed_names = [c['competency'] for c in synth.get('changed_areas', [])]
c_changed_title = CompetencyDAL().get_by_id(c_changed).title
check("B", "زمینهٔ تغییریافته (مثبت→منفی بین سال‌ها) شناسایی می‌شود",
      c_changed_title in changed_names, str(changed_names))

full_report = report_gen.generate_student_report(profile_ids[0])
check("B", "گزارش معمول برنامه هم روایت چندساله را دارد",
      (full_report.get('growth_narrative') or {}).get('has_data') is True
      and bool((full_report.get('growth_narrative') or {}).get('synthesis')),
      str(list(full_report.keys()))[:100])

check("B", "جمع‌بندی غیرتشخیصی و فقط با مقایسهٔ با خود است",
      'تشخیص' in narrative.get('narrative', '')
      and 'مقایسه با دانش‌آموزان دیگر' in narrative.get('narrative', '')
      and 'مسیر کلی رشد' in synth.get('text', ''),
      synth.get('text', '')[:80])

# ============================================================
print()
print("=" * 76)
print("بخش C: نخ‌ایمنی اتصال، تراکنش و کاربر جاری")
print("=" * 76)

main_conn = db.get_connection()
conns = {}
conn_errors = []


def _grab(name):
    try:
        conns[name] = dbc.DatabaseConnection().get_connection()
    except Exception as e:  # pragma: no cover
        conn_errors.append(f"{name}: {e}")


t1 = threading.Thread(target=_grab, args=("t1",))
t2 = threading.Thread(target=_grab, args=("t2",))
t1.start()
t2.start()
t1.join()
t2.join()
check("C", "هر نخ اتصال خودش را می‌گیرد (نه اتصال مشترک)",
      not conn_errors and conns.get("t1") is not None
      and conns.get("t2") is not None
      and conns["t1"] is not conns["t2"]
      and conns["t1"] is not main_conn
      and db.get_connection() is main_conn,
      f"errors={conn_errors}")

write_errors = []


def _writer(tag, count):
    try:
        d = dbc.DatabaseConnection()
        c = d.get_connection()
        for i in range(count):
            c.execute(
                "INSERT INTO students (first_name, last_name) VALUES (?, ?)",
                (f"نخ{tag}", f"{i}"))
        c.commit()
    except Exception as e:  # pragma: no cover
        write_errors.append(f"{tag}: {e}")


wt1 = threading.Thread(target=_writer, args=("A", 25))
wt2 = threading.Thread(target=_writer, args=("B", 25))
wt1.start()
wt2.start()
wt1.join()
wt2.join()
both = conn.execute(
    "SELECT COUNT(*) FROM students WHERE first_name IN ('نخA', 'نخB')"
).fetchone()[0]
check("C", "نوشتن هم‌زمان دو نخ بدون خطا و بدون گم‌شدن رکورد",
      not write_errors and both == 50, f"errors={write_errors} count={both}")

anon_errors = []


def _anon_write():
    try:
        d = dbc.DatabaseConnection()
        assert d.get_current_user() is None, "کاربر نخ اصلی به ارث رسید!"
        c = d.get_connection()
        c.execute("INSERT INTO students (first_name, last_name) "
                  "VALUES ('ناشناس12', 'x')")
        c.commit()
    except Exception as e:  # pragma: no cover
        anon_errors.append(str(e)[:150])


db.set_current_user(1)
ta = threading.Thread(target=_anon_write)
ta.start()
ta.join()
anon_row = conn.execute(
    "SELECT user_id FROM audit_logs WHERE entity_type = 'students' "
    "AND new_value LIKE '%ناشناس12%' ORDER BY id DESC LIMIT 1").fetchone()
check("C", "عملیات نخ بدون کاربر به نام کاربر نخ اصلی ثبت نمی‌شود",
      not anon_errors and anon_row is not None and anon_row[0] is None,
      f"errors={anon_errors} row={dict(anon_row) if anon_row else None}")

tx_info = {}


def _tx_holder():
    d = dbc.DatabaseConnection()
    d.begin_transaction()
    tx_info['holder_depth'] = dbc.DatabaseConnection._transaction_depth
    c = d.get_connection()
    c.execute("INSERT INTO students (first_name, last_name) "
              "VALUES ('تراکنش12', 'x')")
    import time
    time.sleep(0.6)
    d.rollback_transaction()
    tx_info['holder_after'] = dbc.DatabaseConnection._transaction_depth


th = threading.Thread(target=_tx_holder)
th.start()
import time as _time
_time.sleep(0.2)
tx_info['main_during'] = dbc.DatabaseConnection._transaction_depth
main_conn.execute("INSERT INTO students (first_name, last_name) "
                  "VALUES ('خارج12', 'x')")
main_conn.commit()
th.join()
tx_left = conn.execute(
    "SELECT COUNT(*) FROM students WHERE first_name = 'تراکنش12'").fetchone()[0]
tx_main = conn.execute(
    "SELECT COUNT(*) FROM students WHERE first_name = 'خارج12'").fetchone()[0]
check("C", "عمق تراکنش نخ‌محلی است و rollback یک نخ به دیگری آسیب نمی‌زند",
      tx_info.get('holder_depth') == 1 and tx_info.get('main_during') == 0
      and tx_info.get('holder_after') == 0 and tx_left == 0 and tx_main == 1,
      str(tx_info))

db.begin_transaction()
db.begin_transaction()
db.close()
check("C", "بعد از close عمق تراکنش صفر و اتصال بعدی تمیز است",
      dbc.DatabaseConnection._transaction_depth == 0
      and db.get_connection() is not None
      and dbc.DatabaseConnection._transaction_depth == 0
      and not db.in_transaction)

# ============================================================
print()
print("=" * 76)
print("بخش D: پشتیبان امن (نسخه، Zip-Slip، شکست بلند)")
print("=" * 76)

from config.settings import APP_VERSION  # noqa: E402
from utils.backup import BackupManager  # noqa: E402

att_dir = os.path.join(TMP, "att")
bk_dir = os.path.join(TMP, "bk")
os.makedirs(att_dir, exist_ok=True)
os.makedirs(bk_dir, exist_ok=True)
bm = BackupManager(TEST_DB, att_dir, bk_dir)
res = bm.create_backup(name="r12test", user_id=1, user_name="admin")
check("D", "پشتیبان‌گیری موفق است و نسخهٔ واقعی برنامه را ثبت می‌کند",
      res.get('success') is True, str(res.get('message'))[:80])

import zipfile  # noqa: E402

meta_version = None
if res.get('success'):
    with zipfile.ZipFile(res['file']) as zf:
        import json as _json
        meta_version = _json.loads(zf.read('metadata.json').decode('utf-8')).get('version')
check("D", "نسخهٔ متادیتای پشتیبان همان APP_VERSION است",
      meta_version == APP_VERSION, f"{meta_version} != {APP_VERSION}")

evil_path = os.path.join(TMP, "evil_r12.txt")
if os.path.exists(evil_path):
    os.remove(evil_path)
malicious = os.path.join(bk_dir, "malicious.partobak")
with zipfile.ZipFile(malicious, "w") as zf:
    zf.writestr("../../evil_r12.txt", "pwned")
    zf.writestr("database/partow.db", b"fake")
out = bm.restore_backup(malicious, user_id=1, user_name="admin")
check("D", "بازیابی ZIP مخرب (Path Traversal) شکست امن می‌خورد",
      out.get('success') is False and not os.path.exists(evil_path),
      f"success={out.get('success')} evil_exists={os.path.exists(evil_path)}")

import sqlite3 as _sqlite3  # noqa: E402

_orig_connect = _sqlite3.connect


def _always_fail(*a, **k):
    raise _sqlite3.OperationalError("simulated online-backup failure")


_sqlite3.connect = _always_fail
try:
    fail_res = bm.create_backup(name="r12fail", user_id=1, user_name="admin")
finally:
    _sqlite3.connect = _orig_connect
check("D", "شکست online backup با خطای روشن گزارش می‌شود (نه کپی ناسالم)",
      fail_res.get('success') is False
      and ('مجاز نیست' in fail_res.get('message', '')
           or 'آنلاین' in fail_res.get('message', ''))
      and not os.path.exists(os.path.join(bk_dir, "r12fail.partobak")),
      str(fail_res.get('message'))[:100])

# بازیابی، اتصال نخ را بسته است؛ اتصال تازه بگیر
conn = db.get_connection()

# ============================================================
print()
print("=" * 76)
print("بخش E: حسابرسی یکپارچه با مقدار واقعی تغییرات")
print("=" * 76)

expected_tables = ['students', 'observations', 'interventions', 'followups',
                   'student_academic_profiles', 'staff', 'competencies',
                   'family_contexts', 'parent_interviews', 'counseling_sessions',
                   'screenings', 'screening_results',
                   'professional_interpretations', 'individual_goals',
                   'extracurricular_activities', 'recommendations', 'users',
                   'attachments']
missing_triggers = []
for table in expected_tables:
    n = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'trigger' "
        "AND name GLOB ?", (f'trg_{table}_*_audit',)).fetchone()[0]
    if n < 4:
        missing_triggers.append(f"{table}({n})")
check("E", "هر ۱۸ جدول حساس ۴ تریگر حسابرسی دارند",
      not missing_triggers, str(missing_triggers))

conn.execute(
    "INSERT INTO parent_interviews (student_profile_id, staff_id, "
    "interview_date, parent_name, topic) VALUES (?, 1, '1404/01/01', "
    "'پدر', 'موضوع آزمایشی')", (profile_ids[0],))
conn.commit()
piid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
pi_rows = conn.execute(
    "SELECT COUNT(*) FROM audit_logs WHERE entity_type = 'parent_interviews' "
    "AND action = 'create' AND entity_id = ?", (piid,)).fetchone()[0]
check("E", "تغییر مصاحبهٔ والدین در Audit ثبت می‌شود (جدول تازه‌پوشش)",
      pi_rows == 1, f"{pi_rows} ردیف")

with contextlib.redirect_stdout(io.StringIO()):
    member = Staff()
    member.full_name = "کاربر حسابرسی ۱۲"
    member.role = "teacher"
    member.is_active = 1
    member_id = StaffDAL().create(member).id
    nu = User()
    nu.staff_id = member_id
    nu.username = "r12_audit_user"
    nu.role = "teacher"
    nu.is_active = 1
    created_user = UserDAL().create(nu, raw_password="R12audit@123",
                                    user_id_actor=1)
u_rows = conn.execute(
    "SELECT COUNT(*) FROM audit_logs WHERE entity_type = 'users' "
    "AND action = 'create' AND entity_id = ?", (created_user.id,)).fetchone()[0]
check("E", "ساخت کاربر دقیقاً یک ردیف حسابرسی می‌گیرد (بدون تکرار دستی/تریگر)",
      u_rows == 1, f"{u_rows} ردیف")

conn.execute("UPDATE students SET first_name = 'قدیم۱۲' WHERE id = ?",
             (student_id,))
conn.commit()
conn.execute("UPDATE students SET first_name = 'جدید۱۲' WHERE id = ?",
             (student_id,))
conn.commit()
vals = conn.execute(
    "SELECT old_value, new_value FROM audit_logs WHERE entity_type = 'students' "
    "AND action = 'edit' AND entity_id = ? ORDER BY id DESC LIMIT 1",
    (student_id,)).fetchone()
check("E", "ویرایش، مقدار واقعی قبل/بعد را ثبت می‌کند (نه فقط id)",
      vals is not None and 'قدیم۱۲' in (vals[0] or '')
      and 'جدید۱۲' in (vals[1] or ''),
      f"old={str(vals[0])[:60] if vals else None}")

u_val = conn.execute(
    "SELECT new_value FROM audit_logs WHERE entity_type = 'users' "
    "AND entity_id = ? ORDER BY id DESC LIMIT 1",
    (created_user.id,)).fetchone()
check("E", "هش رمز در Audit کاربران ثبت نمی‌شود",
      u_val is not None and 'password_hash' not in (u_val[0] or ''),
      str(u_val[0])[:80] if u_val else "ردیفی نیست")

from services.base_service import BaseService  # noqa: E402

svc = BaseService()
before = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
svc.log_audit(user_id=1, action="create", entity_type="student",
              entity_id=student_id)
svc.log_audit(user_id=1, action="create", entity_type="attachment",
              entity_id=424242)
after = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
check("E", "ثبت دستی برای جدول دارای تریگر تکراری نمی‌سازد",
      after == before, f"{before} → {after}")

before2 = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
svc.log_audit(user_id=1, action="create", entity_type="backup",
              entity_id=424243)
after2 = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
check("E", "ثبت صریح برای موجودیت بدون تریگر همچنان کار می‌کند",
      after2 == before2 + 1, f"{before2} → {after2}")

# ============================================================
print()
print("=" * 76)
print("بخش F: جلوگیری از اعلان تکراری")
print("=" * 76)

from dal.notification_dal import NotificationDAL as _NDAL  # noqa: E402

ndal = _NDAL()

old_notif = Notification()
old_notif.user_id = 1
old_notif.type = Notification.TYPE_REMINDER
old_notif.title = "یادآوری قدیمی"
old_notif.message = "قدیمی"
old_notif.entity_type = "followup"
old_notif.entity_id = 777001
old_notif.scheduled_at = "2020-01-01T00:00:00+00:00"
old_id = ndal.create(old_notif).id
conn.execute("UPDATE notifications SET created_at = '2020-01-01 00:00:00' "
             "WHERE id = ?", (old_id,))
for i in range(15):
    n = Notification()
    n.user_id = 1
    n.type = Notification.TYPE_REMINDER
    n.title = f"یادآوری {i}"
    n.message = "جدید"
    n.entity_type = "followup"
    n.entity_id = 888000 + i
    ndal.create(n)
conn.commit()

check("F", "اعلان قدیمیِ buried زیر ۱۰ اعلان آخر هم پیدا می‌شود",
      notif_service._check_existing_notification(
          777001, 1, Notification.TYPE_REMINDER) is True)

check("F", "ترکیب متفاوت (نوع/موجودیت) تکراری شمرده نمی‌شود",
      notif_service._check_existing_notification(
          777001, 1, Notification.TYPE_OVERDUE) is False
      and notif_service._check_existing_notification(
          999999, 1, Notification.TYPE_REMINDER) is False)

# ============================================================
print()
print("=" * 76)
print("بخش G: یک مسیر واحد برای DAL تفسیر حرفه‌ای")
print("=" * 76)

from dal.interpretation_dal import InterpretationDAL  # noqa: E402
from dal.professional_interpretation_dal import (  # noqa: E402
    ProfessionalInterpretationDAL,
)

check("G", "نام قدیمی و مرجع به یک کلاس واحد می‌رسند",
      InterpretationDAL is ProfessionalInterpretationDAL)

from models.professional_interpretation import (  # noqa: E402
    ProfessionalInterpretation,
)

interp = ProfessionalInterpretation()
interp.student_profile_id = profile_ids[0]
interp.staff_id = 1
interp.level = "normal"
interp.title = "تفسیر آزمایشی ۱۲"
interp.detailed_text = "متن تفسیری آزمایشی برای بررسی دور دوازدهم"
interp.status = "draft"
created_interp = InterpretationDAL().create(interp)
fetched = ProfessionalInterpretationDAL().get_by_id(created_interp.id)
check("G", "CRUD از مسیر واحد (نام قدیمی) کار می‌کند",
      fetched is not None and fetched.title == "تفسیر آزمایشی ۱۲")

# ============================================================
print()
print("=" * 76)
print("بخش H: شکست بلند Migration ناقص")
print("=" * 76)

import sqlite3  # noqa: E402

from database.migrations.manager import (  # noqa: E402
    MigrationManager,
    MigrationMissingError,
)

mig_db = os.path.join(TMP, "mig.db")
mconn = sqlite3.connect(mig_db)
mconn.execute("CREATE TABLE db_version (version INTEGER NOT NULL, "
              "updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
mconn.execute("INSERT INTO db_version (version) VALUES (9)")
mconn.commit()
raised = None
try:
    with contextlib.redirect_stdout(io.StringIO()):
        MigrationManager.migrate(mconn, 12)
except MigrationMissingError as e:
    raised = e
except Exception as e:  # pragma: no cover
    raised = RuntimeError(f"نوع خطای اشتباه: {type(e).__name__}: {e}")
kept = mconn.execute("SELECT version FROM db_version LIMIT 1").fetchone()[0]
mconn.close()
check("H", "نسخهٔ گمشده → MigrationMissingError و عدم مُهر نسخه",
      isinstance(raised, MigrationMissingError) and kept == 9
      and raised is not None and 10 in raised.missing,
      f"raised={type(raised).__name__ if raised else None} kept={kept}")

ok = False
try:
    with contextlib.redirect_stdout(io.StringIO()):
        MigrationManager.migrate(conn, settings.DB_VERSION)
    ok = True
except Exception as e:  # pragma: no cover
    ok = f"{type(e).__name__}: {e}"
check("H", "مسیر سالم Migration بدون خطا می‌ماند", ok is True, str(ok))

# ============================================================
print()
print("=" * 76)
print("بخش I: زمان‌بند پاکسازی و وابستگی‌های تست")
print("=" * 76)

from utils.notification_scheduler import NotificationScheduler  # noqa: E402
from utils.time_utils import utc_now  # noqa: E402
from datetime import timedelta as _td

sched = NotificationScheduler()
sched._last_cleanup_time = None
first = sched._should_cleanup()
sched._last_cleanup_time = utc_now()
second = sched._should_cleanup()
sched._last_cleanup_time = utc_now() - _td(hours=25)
third = sched._should_cleanup()
check("I", "پاکسازی فقط هر ۲۴ ساعت مجاز است (نه هر اجرا)",
      first is True and second is False and third is True,
      f"{first}/{second}/{third}")

req = read("requirements.txt")
check("I", "pytest در requirements ثبت شده (اجرای تست در محیط تمیز)",
      "pytest" in req, "pytest یافت نشد" if "pytest" not in req else "")

check("I", "نسخهٔ هاردکد پشتیبان حذف شده و از منبع اصلی می‌آید",
      "'2.0.0'" not in read("utils/backup.py")
      and '"2.0.0"' not in read("utils/backup.py")
      and "APP_VERSION" in read("utils/backup.py"))

# ============================================================
print()
print("=" * 76)
print("بخش J: رفع N+1 در پرونده و گزارش‌ها")
print("=" * 76)

comp_dal = CompetencyDAL()
staff_dal = StaffDAL()
all_comps = comp_dal.get_all()
ids = [c.id for c in all_comps[:5]] + [999999, None]
titles = comp_dal.get_titles_by_ids(ids)
expected = {}
for c in all_comps[:5]:
    expected[c.id] = c.title
check("J", "خواندن دسته‌ای عنوان شایستگی‌ها درست و کامل است",
      titles == expected and comp_dal.get_titles_by_ids([]) == {}
      and comp_dal.get_titles_by_ids(None) == {}, str(titles)[:80])

names = staff_dal.get_names_by_ids([1])
row1 = staff_dal.get_by_id(1)
check("J", "خواندن دسته‌ای نام کادر با get_by_id می‌خواند",
      names.get(1) == (row1.full_name if row1 else None)
      and staff_dal.get_names_by_ids([]) == {}, str(names))

import ast as _ast  # noqa: E402

page_src = read("views/pages/student_profile_page.py")
tree = _ast.parse(page_src)
bad_loops = []
for node in _ast.walk(tree):
    if isinstance(node, _ast.FunctionDef) and node.name in (
            'load_summary', 'load_observations', 'load_interventions',
            'load_followups'):
        for sub in _ast.walk(node):
            if isinstance(sub, _ast.Call) and isinstance(sub.func, _ast.Attribute) \
                    and sub.func.attr == 'get_by_id':
                bad_loops.append(node.name)
                break
check("J", "در حلقه‌های بارگذاری پرونده دیگر get_by_id تکی نیست",
      not bad_loops, str(bad_loops))

traced = []
trace_conn = db.get_connection()
trace_conn.set_trace_callback(traced.append)
try:
    comp_dal.get_titles_by_ids([c.id for c in all_comps[:6]])
finally:
    trace_conn.set_trace_callback(None)
comp_selects = [s for s in traced
                if 'competencies' in s and 'SELECT' in s.upper()]
check("J", "خواندن ۶ عنوان فقط یک SELECT روی competencies می‌زند",
      len(comp_selects) == 1, f"{len(comp_selects)} کوئری: {comp_selects[:1]}")

# ============================================================
print()
print("=" * 76)
print("بخش K: نگهبان‌های بدون پس‌روندگی (محتوای دور ۱۱)")
print("=" * 76)

check("K", "آستانه‌های الگو دست‌نخورده‌اند (۲ تکرار، غلبهٔ ۶۰٪)",
      MIN_PATTERN_COUNT == 2 and abs(DOMINANCE_RATIO - 0.6) < 1e-9)
check("K", "رفتار خنثی به‌تنهایی الگو نمی‌سازد و شدت تصمیم نمی‌گیرد",
      classify_pattern(0, 0, 2, 2) == 'insufficient'
      and classify_pattern(0, 3, 0, 3) == 'needs_attention'
      and 'avg_severity >= 3.5' not in read("dal/observation_dal.py"))
check("K", "لایه‌های مشاهده/غربالگری/تفسیر همچنان جدایند",
      all(k in (full_report.get('information_layers') or {})
          for k in ('observation', 'screening', 'interpretation')))
check("K", "نسخهٔ دیتابیس همچنان ۹ است (بدون bump)",
      int(settings.DB_VERSION) == 9, str(settings.DB_VERSION))

# ============================================================
try:
    dbc.DatabaseConnection._instance = None
    dbc.DatabaseConnection._connection = None
except Exception:
    pass
finally:
    settings.DB_PATH = _orig_s
    dbc.DB_PATH = _orig_c

print()
print("=" * 76)
print(f"نتیجهٔ دور دوازدهم:  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های دور دوازدهم سبز است.")
