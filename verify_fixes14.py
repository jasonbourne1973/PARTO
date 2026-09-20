"""
بررسی‌های دور چهاردهم: داوری فنی مدیر پروژه (۱۵ مورد) — مرحلهٔ ۱: اولویت قرمز

  A) اتصال SQLite و تراکنش در چند نخ (موارد ۱، ۳، ۴) ................ ۹ بررسی
  B) هویت کاربر/سیستم در Audit بین نخ‌ها (مورد ۲) ..................... ۶ بررسی
  C) پشتیبان امن، بازیابی امن و Path Traversal (موارد ۵، ۶، ۱۳) ...... ۱۰ بررسی
  D) یکپارچگی Migration (مورد ۱۱) ...................................... ۳ بررسی

جمع مرحلهٔ ۱: ۲۸ بررسی  (مرحلهٔ ۲ — موارد نارنجی/زرد — در ادامهٔ همین فایل
اضافه می‌شود)

هر بررسی روی یک دیتابیس موقت اجرا می‌شود و به داده‌های کاربر دست نمی‌زند.
بخش B به PySide6 نیاز دارد (کارگرهای واقعی QThread)؛ با QT_QPA_PLATFORM=offscreen
اجرا می‌شود.
"""

import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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


def quiet():
    return contextlib.redirect_stdout(io.StringIO())


TMP = tempfile.mkdtemp(prefix="round14_verify_")
TEST_DB = os.path.join(TMP, "partow.db")
ATT_DIR = os.path.join(TMP, "attachments")

import config.settings as settings
import database.connection as dbc

settings.DB_PATH = TEST_DB
dbc.DB_PATH = TEST_DB
dbc.DatabaseConnection._instance = None
dbc.DatabaseConnection._connection = None
dbc.DatabaseConnection._initialized = False
dbc.DatabaseConnection._current_user_id = None

import services.attachment_service as attachment_service_module

attachment_service_module.ATTACHMENTS_DIR = ATT_DIR

with quiet():
    db = dbc.DatabaseConnection()
    conn = db.get_connection(user_id=1)

from dal.audit_log_dal import AuditLogDAL
from utils.backup import BackupManager

conn_src = read("database/connection.py")
backup_src = read("utils/backup.py")
scheduler_src = read("utils/notification_scheduler.py")
attachment_dialog_src = read("views/dialogs/attachment_dialog.py")
backup_page_src = read("views/pages/backup_page.py")
manager_src = read("database/migrations/manager.py")


def count_students(c=None):
    c = c or conn
    return c.execute("SELECT COUNT(*) FROM students").fetchone()[0]


# ============================================================================
print("=" * 76)
print("بخش A: اتصال SQLite و تراکنش در چند نخ (موارد ۱، ۳، ۴)")
print("=" * 76)

# --- A1: هر نخ اتصال خودش را دارد و اتصال نخ اصلی به اشتراک گذاشته نمی‌شود
thread_conns = {}
thread_errors = []


def _grab(tag):
    try:
        thread_conns[tag] = dbc.DatabaseConnection().get_connection()
    except Exception as e:  # pragma: no cover
        thread_errors.append(f"{tag}: {e}")


threads = [threading.Thread(target=_grab, args=(f"t{i}",)) for i in range(3)]
for t in threads:
    t.start()
for t in threads:
    t.join()
distinct = {id(c) for c in thread_conns.values()}
check("A", "هر نخ اتصال SQLite جداگانه می‌گیرد و اتصال نخ اصلی مشترک نیست",
      not thread_errors and len(distinct) == 3
      and all(c is not conn for c in thread_conns.values())
      and db.get_connection() is conn,
      f"errors={thread_errors}")

# --- A2: تراکنش نخ A زیر پای نخ B نیست (عمق، commit و rollback مستقل)
# نخ A تراکنش نوشتنی باز می‌کند و کمی نگه می‌دارد؛ نخ B در همان فاصله
# تراکنش خودش را شروع می‌کند: باید «منتظر بماند» (busy_timeout) نه این‌که
# خطا بدهد یا عمق/کار نخ A را دستکاری کند. rollback نخ A فقط کار A را لغو
# می‌کند و commit نخ B فقط کار B را ذخیره.
tx_log = {}
gate_a_started = threading.Event()


def _thread_a():
    d = dbc.DatabaseConnection()
    try:
        d.begin_transaction()
        c = d.get_connection()
        c.execute("INSERT INTO students (first_name, last_name) VALUES ('نخA', 'ناتمام')")
        tx_log['a_depth_inside'] = d._transaction_depth
        gate_a_started.set()
        time.sleep(0.7)
        tx_log['a_depth_before_rollback'] = d._transaction_depth   # هنوز ۱
        d.rollback_transaction()          # کل کار نخ A لغو می‌شود
        tx_log['a_depth_end'] = d._transaction_depth
    except Exception as e:  # pragma: no cover
        tx_log['a_error'] = str(e)
        gate_a_started.set()


def _thread_b():
    d = dbc.DatabaseConnection()
    gate_a_started.wait(10)
    try:
        tx_log['b_depth_seen'] = d._transaction_depth      # باید ۰ باشد
        started = time.monotonic()
        d.begin_transaction()                              # منتظر نخ A می‌ماند
        tx_log['b_wait'] = round(time.monotonic() - started, 2)
        d.begin_transaction()                              # تودرتو
        c = d.get_connection()
        c.execute("INSERT INTO students (first_name, last_name) VALUES ('نخB', 'کامل')")
        tx_log['b_depth_inside'] = d._transaction_depth
        d.commit_transaction()
        d.commit_transaction()
        tx_log['b_depth_end'] = d._transaction_depth
    except Exception as e:  # pragma: no cover
        tx_log['b_error'] = str(e)


ta = threading.Thread(target=_thread_a)
tb = threading.Thread(target=_thread_b)
ta.start()
tb.start()
ta.join(15)
tb.join(15)
a_rows = conn.execute("SELECT COUNT(*) FROM students WHERE first_name = 'نخA'").fetchone()[0]
b_rows = conn.execute("SELECT COUNT(*) FROM students WHERE first_name = 'نخB'").fetchone()[0]
check("A", "تراکنش دو نخ مستقل است: نخ B منتظر می‌ماند (نه خطا)، عمق‌ها جدا، rollback نخ A و commit نخ B فقط روی کار خودشان",
      'a_error' not in tx_log and 'b_error' not in tx_log
      and tx_log.get('a_depth_inside') == 1 and tx_log.get('b_depth_seen') == 0
      and tx_log.get('a_depth_before_rollback') == 1
      and tx_log.get('b_wait', 0) >= 0.3
      and tx_log.get('b_depth_inside') == 2
      and tx_log.get('a_depth_end') == 0 and tx_log.get('b_depth_end') == 0
      and a_rows == 0 and b_rows == 1,
      f"log={tx_log} a_rows={a_rows} b_rows={b_rows}")

# --- A3: نوشتن هم‌زمان چند نخ بدون خطای SQLite و بدون گم‌شدن رکورد
write_errors = []


def _writer(tag, count):
    try:
        d = dbc.DatabaseConnection()
        for i in range(count):
            d.begin_transaction()
            d.get_connection().execute(
                "INSERT INTO students (first_name, last_name) VALUES (?, ?)",
                (f"همزمان{tag}", str(i)))
            d.commit_transaction()
    except Exception as e:  # pragma: no cover
        write_errors.append(f"{tag}: {e}")


writers = [threading.Thread(target=_writer, args=(tag, 20)) for tag in "XYZ"]
for t in writers:
    t.start()
# نخ اصلی هم هم‌زمان می‌نویسد (شبیه رابط کاربری + زمان‌بند)
_writer("M", 20)
for t in writers:
    t.join(30)
total_concurrent = conn.execute(
    "SELECT COUNT(*) FROM students WHERE first_name LIKE 'همزمان%'").fetchone()[0]
check("A", "رابط کاربری + سه نخ پس‌زمینه هم‌زمان می‌نویسند: بدون خطا و بدون گم‌شدن رکورد (۸۰/۸۰)",
      not write_errors and total_concurrent == 80,
      f"errors={write_errors} total={total_concurrent}")

# --- A4: close() وضعیت تراکنش همان نخ را صفر می‌کند و اتصال بعدی تمیز است
db.begin_transaction()
db.get_connection().execute(
    "INSERT INTO students (first_name, last_name) VALUES ('بسته', 'ناتمام')")
depth_before_close = db._transaction_depth
db.close()
depth_after_close = db._transaction_depth
with quiet():
    fresh = db.get_connection()
closed_row = fresh.execute(
    "SELECT COUNT(*) FROM students WHERE first_name = 'بسته'").fetchone()[0]
try:
    db.begin_transaction()
    db.commit_transaction()
    clean_begin = True
except Exception as e:  # pragma: no cover
    clean_begin = False
    print("   ", e)
check("A", "close() عمق تراکنش را صفر می‌کند؛ کار ناتمام rollback و اتصال تازه با وضعیت تمیز شروع می‌شود",
      depth_before_close == 1 and depth_after_close == 0 and closed_row == 0
      and clean_begin and fresh is not conn,
      f"before={depth_before_close} after={depth_after_close} row={closed_row}")
conn = fresh

# --- A5: close_all همهٔ نخ‌ها را می‌بندد و نخ‌ها بعداً اتصال تازه می‌گیرند
other_conn_holder = {}
other_gate = threading.Event()
other_release = threading.Event()


def _long_lived():
    d = dbc.DatabaseConnection()
    other_conn_holder['first'] = d.get_connection()
    other_gate.set()
    other_release.wait(10)
    try:
        # بعد از close_all: اتصال قدیمی نباید دوباره استفاده شود
        other_conn_holder['second'] = d.get_connection()
        other_conn_holder['depth'] = d._transaction_depth
        other_conn_holder['ok'] = other_conn_holder['second'].execute(
            "SELECT 1").fetchone()[0] == 1
    except Exception as e:  # pragma: no cover
        other_conn_holder['error'] = str(e)


tl = threading.Thread(target=_long_lived)
tl.start()
other_gate.wait(10)
with quiet():
    db.close_all()
other_release.set()
tl.join(15)
with quiet():
    conn = db.get_connection()
check("A", "close_all اتصال همهٔ نخ‌ها را می‌بندد؛ هر نخ بعداً اتصال تازه با تراکنش صفر می‌گیرد",
      'error' not in other_conn_holder
      and other_conn_holder.get('ok') is True
      and other_conn_holder.get('first') is not other_conn_holder.get('second')
      and other_conn_holder.get('depth') == 0,
      f"{ {k: v for k, v in other_conn_holder.items() if k in ('error', 'ok', 'depth')} }")

# --- A6: اتصال نخ‌های تمام‌شده یتیم نمی‌ماند (هرس رجیستری)
live_gate = threading.Event()
live_release = threading.Event()


def _short_lived():
    dbc.DatabaseConnection().get_connection()
    live_gate.set()
    live_release.wait(10)


shorts = [threading.Thread(target=_short_lived) for _ in range(5)]
for t in shorts:
    t.start()
time.sleep(0.3)
with_live = len(dbc.DatabaseConnection._open_connections)
live_release.set()
for t in shorts:
    t.join(10)
after_dead = dbc.DatabaseConnection.open_connection_count()
check("A", "اتصال نخ‌های کارگرِ تمام‌شده بسته و از رجیستری حذف می‌شود (بدون اتصال یتیم)",
      with_live >= 6 and after_dead == 1,
      f"with_live={with_live} after_dead={after_dead}")

# --- A7: حالت‌های نخ‌محلی هنوز از طریق نام‌های قدیمی هم قابل دسترس‌اند (سازگاری)
check("A", "نام‌های قدیمی (_connection/_transaction_depth/_current_user_id) به وضعیت نخ جاری اشاره می‌کنند",
      dbc.DatabaseConnection._connection is conn
      and dbc.DatabaseConnection._transaction_depth == 0
      and dbc.DatabaseConnection._current_user_id == 1
      and db._connection is conn)

# --- A9: آماده‌سازی اسکیما (Migration/ترمیم/DDL تریگرها) برای هر نخ تازه تکرار نمی‌شود
schema_out = io.StringIO()
schema_errors = []


def _plain_open():
    try:
        dbc.DatabaseConnection().get_connection().execute("SELECT 1").fetchone()
    except Exception as e:  # pragma: no cover
        schema_errors.append(str(e))


with contextlib.redirect_stdout(schema_out):
    openers = [threading.Thread(target=_plain_open) for _ in range(4)]
    for t in openers:
        t.start()
    for t in openers:
        t.join(10)
schema_text = schema_out.getvalue()
check("A", "نخ‌های تازه فقط اتصال می‌گیرند؛ DDL تریگرها/ترمیم اسکیما برای هر نخ تکرار نمی‌شود (یک‌بار در هر نسل)",
      not schema_errors and "تریگرهای Audit Log" not in schema_text
      and "Migration" not in schema_text,
      f"errors={schema_errors} out={schema_text[:80]!r}")

# --- A8: منبع: اتصال در هر نخ جدا ساخته می‌شود و رجیستری نخ را ضعیف نگه می‌دارد
check("A", "منبع: اتصال نخ‌محلی + هرس رجیستری + worker_context برای نخ‌های کارگر",
      "threading.local()" in conn_src
      and "_prune_dead_thread_connections" in conn_src
      and "weakref.ref(threading.current_thread())" in conn_src
      and "def worker_context" in conn_src)

# ============================================================================
print("=" * 76)
print("بخش B: هویت کاربر/سیستم در Audit بین نخ‌ها (مورد ۲)")
print("=" * 76)

# --- B1: کارگر واقعی آپلود پیوست (QThread) به نام کاربر واردشده ثبت می‌کند
qt_error = None
try:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    from services.attachment_service import AttachmentService
    from views.dialogs.attachment_dialog import AttachmentUploadWorker

    sample_file = os.path.join(TMP, "sample.txt")
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write("نمونه")
    with quiet():
        worker = AttachmentUploadWorker(
            service=AttachmentService(), entity_type="student", entity_id=1,
            file_path=sample_file, created_by=None)
        worker.start()
        worker.wait(15000)
except Exception as e:  # pragma: no cover
    qt_error = str(e)

audit_row = conn.execute(
    "SELECT user_id, action FROM audit_logs WHERE entity_type = 'attachments' "
    "ORDER BY id DESC LIMIT 1").fetchone()
att_row = conn.execute(
    "SELECT created_by FROM attachments ORDER BY id DESC LIMIT 1").fetchone()
check("B", "آپلود پیوست در نخ کارگر واقعی (QThread) در Audit به نام کاربر واردشده ثبت می‌شود، نه «سیستم»",
      qt_error is None and audit_row is not None
      and audit_row[0] == 1 and audit_row[1] == 'create',
      f"qt_error={qt_error} audit={tuple(audit_row) if audit_row else None}")
check("B", "created_by پیوست هم کاربر واقعی است (قبلاً همیشه None/نامشخص بود)",
      att_row is not None and att_row[0] == 1,
      f"created_by={att_row[0] if att_row else None}")

# --- B3: نخ خودکار سیستم (زمان‌بند) با هویت صریح None می‌نویسد → Audit «سیستم»
sys_result = {}


def _system_job():
    d = dbc.DatabaseConnection()
    try:
        with d.worker_context(None):
            sys_result['user_inside'] = d.get_current_user()
            c = d.get_connection()
            c.execute("INSERT INTO students (first_name, last_name) VALUES ('خودکار', 'سیستم')")
            c.commit()
            sys_result['sid'] = c.execute(
                "SELECT id FROM students WHERE first_name = 'خودکار'").fetchone()[0]
        sys_result['user_after'] = d.get_current_user()
    except Exception as e:  # pragma: no cover
        sys_result['error'] = str(e)


tsys = threading.Thread(target=_system_job)
tsys.start()
tsys.join(15)
sys_audit = conn.execute(
    "SELECT user_id FROM audit_logs WHERE entity_type = 'students' AND entity_id = ? "
    "AND action = 'create'", (sys_result.get('sid'),)).fetchone()
sys_view = [r for r in AuditLogDAL().get_logs(limit=200, entity_type='students')
            if r.get('entity_id') == sys_result.get('sid')]
check("B", "عملیات خودکار در نخ پس‌زمینه با user_id=NULL ثبت می‌شود و در تاریخچه «سیستم» نمایش داده می‌شود",
      'error' not in sys_result and sys_result.get('user_inside') is None
      and sys_audit is not None and sys_audit[0] is None
      and sys_view and sys_view[0].get('user_name') == 'سیستم',
      f"{sys_result} audit={tuple(sys_audit) if sys_audit else None} "
      f"view={sys_view[0].get('user_name') if sys_view else None}")

# --- B4: هویت نخ اصلی پس از کار نخ‌های دیگر دست‌نخورده است (نه بازنویسی، نه به‌ارث‌رفتن)
check("B", "کاربر جاری نخ اصلی بعد از کار نخ‌های کارگر/سیستم همچنان همان کاربر واردشده است",
      db.get_current_user() == 1 and sys_result.get('user_after') is None)

# --- B5: نخ کارگر با هویت نامعتبر (کاربر حذف‌شده) به NULL می‌افتد، نه به کاربر نخ اصلی
inv_result = {}


def _invalid_user_job():
    d = dbc.DatabaseConnection()
    try:
        with quiet(), d.worker_context(987654):
            c = d.get_connection()
            inv_result['user'] = d.get_current_user()
            c.execute("INSERT INTO students (first_name, last_name) VALUES ('نامعتبر', 'کاربر')")
            c.commit()
    except Exception as e:  # pragma: no cover
        inv_result['error'] = str(e)


tinv = threading.Thread(target=_invalid_user_job)
tinv.start()
tinv.join(15)
check("B", "هویت نامعتبر در نخ کارگر → NULL (بدون خطای FK و بدون انتساب به کاربر نخ اصلی)",
      'error' not in inv_result and inv_result.get('user') is None
      and conn.execute("SELECT COUNT(*) FROM students WHERE first_name = 'نامعتبر'").fetchone()[0] == 1,
      f"{inv_result}")

# --- B6: منبع: زمان‌بند صریحاً «سیستم» است و کارگرهای UI هویت را صریح تحویل می‌گیرند
check("B", "منبع: زمان‌بند با worker_context(None) و کارگرهای آپلود/پشتیبان با هویت کاربر واقعی اجرا می‌شوند",
      "worker_context(None)" in scheduler_src
      and "worker_context(self.user_context)" in attachment_dialog_src
      and "created_by=DatabaseConnection().get_current_user()" in attachment_dialog_src
      and "worker_context(self.user_id)" in backup_page_src
      and "user_id=self.user_id, user_name=self.user_name" in backup_page_src)

# ============================================================================
print("=" * 76)
print("بخش C: پشتیبان امن، بازیابی امن و Path Traversal (موارد ۵، ۶، ۱۳)")
print("=" * 76)

BK_DIR = os.path.join(TMP, "backups")
manager = BackupManager(TEST_DB, ATT_DIR, BK_DIR)

# --- C1: هیچ مسیر «کپی مستقیم فایل فعال» در ساخت پشتیبان نیست
create_body = backup_src.split("def create_backup")[1].split("def _quiesce_database")[0]
check("C", "create_backup هیچ fallback «کپی مستقیم فایل فعال» ندارد (فقط online backup یا شکست روشن)",
      "shutil.copy2(self.db_path" not in create_body
      and "src.backup(dst)" in create_body
      and "_verify_sqlite_file(tmp_db_snapshot)" in create_body)

# --- C2: اگر فایل دیتابیس نباشد، پشتیبان «ظاهراً موفق» ساخته نمی‌شود
missing_manager = BackupManager(os.path.join(TMP, "missing.db"), ATT_DIR,
                                os.path.join(TMP, "bk_missing"))
missing_result = missing_manager.create_backup("x")
check("C", "نبودِ فایل دیتابیس → شکست روشن، نه ZIP بدون دیتابیس با success=True",
      missing_result.get('success') is False
      and 'یافت نشد' in missing_result.get('message', '')
      and not os.path.exists(os.path.join(TMP, "bk_missing", "x.partobak")),
      f"{missing_result.get('message', '')[:80]}")

# --- C3: اسنپ‌شات خراب → پشتیبان تحویل نمی‌شود
corrupt_path = os.path.join(TMP, "corrupt.db")
with open(corrupt_path, "wb") as f:
    f.write(b"SQLite format 3\x00" + b"\xff" * 4000)
corrupt_manager = BackupManager(corrupt_path, ATT_DIR, os.path.join(TMP, "bk_corrupt"))
corrupt_result = corrupt_manager.create_backup("c")
check("C", "دیتابیس خراب → online backup/اعتبارسنجی اسنپ‌شات شکست می‌خورد و هیچ فایل پشتیبانی تحویل نمی‌شود",
      corrupt_result.get('success') is False
      and not os.path.exists(os.path.join(TMP, "bk_corrupt", "c.partobak"))
      and not os.path.exists(os.path.join(TMP, "bk_corrupt", "c.db.tmp")),
      f"{corrupt_result.get('message', '')[:80]}")

# --- C4: پشتیبان سالم: اسنپ‌شات معتبر + نسخهٔ واقعی برنامه در فراداده
with quiet():
    good = manager.create_backup("good", user_id=1, user_name="آزمون")
good_ok = good.get('success') is True
meta = {}
members = []
if good_ok:
    with zipfile.ZipFile(good['file']) as z:
        members = z.namelist()
        meta = json.loads(z.read("metadata.json"))
        z.extract("database/partow.db", os.path.join(TMP, "peek"))
    snap_ok, snap_detail = BackupManager._verify_sqlite_file(
        os.path.join(TMP, "peek", "database", "partow.db"))
else:
    snap_ok, snap_detail = False, good.get('message')
check("C", "پشتیبان سالم از اسنپ‌شات معتبر SQLite ساخته می‌شود و نسخهٔ فراداده = APP_VERSION",
      good_ok and "database/partow.db" in members and snap_ok
      and meta.get('version') == settings.APP_VERSION
      and meta.get('created_by') == 1,
      f"ok={good_ok} snap={snap_detail} version={meta.get('version')}")

# --- C5: بازیابی با عضو database خراب → دیتابیس فعال دست‌نخورده می‌ماند
bad_file = os.path.join(BK_DIR, "bad.partobak")
with zipfile.ZipFile(bad_file, "w") as z:
    z.writestr("database/partow.db", b"not a sqlite database at all" * 200)
    z.writestr("metadata.json", json.dumps({"name": "bad"}))
students_before = count_students()
with quiet():
    bad_result = manager.restore_backup(bad_file)
try:
    probe = sqlite3.connect(TEST_DB)
    students_after = probe.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    probe.close()
except sqlite3.Error as e:  # pragma: no cover
    students_after = f"broken: {e}"
check("C", "بازیابی از پشتیبانی که دیتابیسش خراب است رد می‌شود و دیتابیس فعال دست‌نخورده می‌ماند",
      bad_result.get('success') is False and students_after == students_before
      and 'دست‌نخورده' in bad_result.get('message', ''),
      f"before={students_before} after={students_after} msg={bad_result.get('message', '')[:60]}")

# --- C6: Zip-Slip: اعضای مخرب رد می‌شوند و هیچ فایلی بیرون پوشهٔ بازیابی نوشته نمی‌شود
evil_names = ["../../evil.txt", "/abs/evil.txt", "database/../../evil2.txt",
              "attachments\\..\\evil3.txt", "database/C:evil4.txt"]
slip_results = {}
for i, evil in enumerate(evil_names):
    evil_zip = os.path.join(BK_DIR, f"evil{i}.partobak")
    with zipfile.ZipFile(evil_zip, "w") as z:
        z.writestr(evil, b"pwned")
        z.writestr("database/partow.db", b"x")
    with quiet():
        r = manager.restore_backup(evil_zip)
    slip_results[evil] = r.get('success')
escaped = [p for p in (os.path.join(TMP, "evil.txt"), os.path.join(BK_DIR, "evil2.txt"),
                       os.path.join(BK_DIR, "evil3.txt"), "/abs/evil.txt")
           if os.path.exists(p)]
check("C", "Zip-Slip: اعضای `..`، مسیر مطلق، `\\\\` و `:` رد می‌شوند و فایلی بیرون پوشهٔ بازیابی ساخته نمی‌شود",
      all(v is False for v in slip_results.values()) and not escaped
      and count_students() == students_before,
      f"{slip_results} escaped={escaped}")

# --- C7: بازیابی سالم واقعاً اثر می‌کند (در حالی که نخ دیگری اتصال باز دارد)
bg_gate = threading.Event()
bg_release = threading.Event()
bg_result = {}


def _bg_reader():
    d = dbc.DatabaseConnection()
    try:
        d.get_connection().execute("SELECT COUNT(*) FROM students").fetchone()
        bg_gate.set()
        bg_release.wait(20)
        # بعد از بازیابی، این نخ باید بدون خطا اتصال تازه بگیرد
        bg_result['count'] = d.get_connection().execute(
            "SELECT COUNT(*) FROM students").fetchone()[0]
    except Exception as e:  # pragma: no cover
        bg_result['error'] = str(e)
        bg_gate.set()


bg = threading.Thread(target=_bg_reader)
bg.start()
bg_gate.wait(10)
conn.execute("DELETE FROM students")
conn.commit()
deleted_count = count_students()
with quiet():
    restore_result = manager.restore_backup(good['file'], user_id=1, user_name="آزمون")
bg_release.set()
bg.join(20)
with quiet():
    conn = db.get_connection()
restored_count = count_students()
check("C", "بازیابی سالم اثر می‌کند (رکوردهای حذف‌شده برمی‌گردند) حتی وقتی نخ دیگری اتصال باز داشت",
      restore_result.get('success') is True and deleted_count == 0
      and restored_count == students_before
      and 'error' not in bg_result and bg_result.get('count') == students_before
      and not os.path.exists(TEST_DB + '.restore_safety'),
      f"deleted={deleted_count} restored={restored_count} bg={bg_result} "
      f"msg={restore_result.get('message', '')[:60]}")

# --- C8: اگر راستی‌آزمایی پس از جایگزینی شکست بخورد، دیتابیس قبلی سر جایش برمی‌گردد
orig_verify = manager._verify_restored_database
manager._verify_restored_database = lambda: (False, "شبیه‌سازی شکست پس از جایگزینی")
marker_id = conn.execute(
    "INSERT INTO students (first_name, last_name) VALUES ('نشانه', 'قبل از بازیابی')").lastrowid
conn.commit()
with quiet():
    failed_after_copy = manager.restore_backup(good['file'])
manager._verify_restored_database = orig_verify
with quiet():
    conn = db.get_connection()
marker_alive = conn.execute(
    "SELECT COUNT(*) FROM students WHERE id = ?", (marker_id,)).fetchone()[0]
check("C", "شکست راستی‌آزمایی پس از جایگزینی → دیتابیس قبلی (با آخرین رکوردها) برگردانده می‌شود",
      failed_after_copy.get('success') is False and marker_alive == 1
      and 'برگردانده شد' in failed_after_copy.get('message', '')
      and not os.path.exists(TEST_DB + '.restore_safety'),
      f"success={failed_after_copy.get('success')} marker={marker_alive}")

# --- C9: پشتیبان‌گیری هم‌زمان با نوشتن نخ دیگر، پشتیبان سالم می‌دهد
busy_stop = threading.Event()
busy_errors = []


def _busy_writer():
    d = dbc.DatabaseConnection()
    try:
        i = 0
        while not busy_stop.is_set() and i < 400:
            c = d.get_connection()
            c.execute("INSERT INTO students (first_name, last_name) VALUES ('مشغول', ?)", (str(i),))
            c.commit()
            i += 1
    except Exception as e:  # pragma: no cover
        busy_errors.append(str(e))


busy = threading.Thread(target=_busy_writer)
busy.start()
time.sleep(0.05)
with quiet():
    live = manager.create_backup("live", user_id=1)
busy_stop.set()
busy.join(20)
live_ok = live.get('success') is True
if live_ok:
    with zipfile.ZipFile(live['file']) as z:
        z.extract("database/partow.db", os.path.join(TMP, "peek_live"))
    live_snap_ok, live_detail = BackupManager._verify_sqlite_file(
        os.path.join(TMP, "peek_live", "database", "partow.db"))
else:
    live_snap_ok, live_detail = False, live.get('message')
check("C", "پشتیبان‌گیری هم‌زمان با نوشتنِ نخ دیگر، بدون خطا و با اسنپ‌شات سالم انجام می‌شود",
      live_ok and live_snap_ok and not busy_errors,
      f"ok={live_ok} snap={live_detail} errors={busy_errors}")

# --- C10: منبع: نگهبان استخراج امن و راستی‌آزمایی قبل از جایگزینی
restore_body = backup_src.split("def restore_backup")[1].split("def _cleanup_pre_restore_files")[0]
code_lines_with_extractall = [
    line for line in backup_src.splitlines()
    if ".extractall(" in line and not line.strip().startswith(("#", "نسخهٔ", "می‌زد"))
    and "نسخهٔ قبلی" not in line]
check("C", "منبع: _safe_extract به‌جای extractall + اعتبارسنجی فایل استخراج‌شده قبل از جایگزینی + نسخهٔ APP_VERSION",
      not code_lines_with_extractall
      and "self._safe_extract(zipf, extract_dir)" in restore_body
      and restore_body.index("_verify_sqlite_file(") < restore_body.index("shutil.copy2(db_backup, self.db_path)")
      and "'version': APP_VERSION" in backup_src
      and "'version': '2.0.0'" not in backup_src,
      f"extractall_lines={code_lines_with_extractall}")

# ============================================================================
print("=" * 76)
print("بخش D: یکپارچگی Migration (مورد ۱۱)")
print("=" * 76)

from database.migrations import manager as migration_manager

# --- D1: نبودِ یک Migration در بازه → شکست بلند و مُهرنخوردن نسخه
gap_db = os.path.join(TMP, "gap.db")
gap_conn = sqlite3.connect(gap_db)
migration_manager.MigrationManager.set_version(gap_conn, 5)
real_discover = migration_manager._discover_migrations


def _discover_without_v7():
    found = dict(real_discover())
    found.pop(7, None)
    return found


migration_manager._discover_migrations = _discover_without_v7
gap_error = None
try:
    with quiet():
        migration_manager.MigrationManager.migrate(gap_conn, 9)
except migration_manager.MigrationMissingError as e:
    gap_error = e
except Exception as e:  # pragma: no cover
    gap_error = e
finally:
    migration_manager._discover_migrations = real_discover
gap_version = migration_manager.MigrationManager.get_current_version(gap_conn)
gap_conn.close()
check("D", "Migration گمشده (v7) → MigrationMissingError با نام نسخهٔ گمشده؛ نسخهٔ دیتابیس جلو نمی‌رود",
      isinstance(gap_error, migration_manager.MigrationMissingError)
      and gap_error.missing == [7] and gap_version == 5,
      f"error={type(gap_error).__name__} version={gap_version}")

# --- D2: در DatabaseConnection هم خطا بالا می‌آید و نسخه مُهر نمی‌خورد (بدون fallback خاموش)
migrate_body = conn_src.split("def _migrate_database")[1].split("def _migrate_to_v1")[0]
check("D", "_migrate_database بدون «مسیر جایگزین خاموش»: خطا بالا می‌آید و _set_db_version فقط بعد از موفقیت",
      "raise" in migrate_body
      and migrate_body.index("MigrationManager.migrate(") < migrate_body.index("self._set_db_version(to_version)")
      and "Migration برای نسخه" not in migrate_body)

# --- D3: مسیر سالم: دیتابیس تازه در نسخهٔ DB_VERSION است و بدون migration اضافی
check("D", "دیتابیس تازه دقیقاً در نسخهٔ DB_VERSION است و اجرای دوبارهٔ migrate کاری نمی‌کند",
      db.get_db_version() == settings.DB_VERSION and settings.DB_VERSION == 9
      and migration_manager.MigrationManager.get_current_version(conn) == 9)

# ============================================================================
print("=" * 76)
print(f"نتیجهٔ دور چهاردهم (مرحلهٔ ۱):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("موارد ناموفق:")
    for item in FAILURES:
        print(f"  - {item}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های مرحلهٔ ۱ دور چهاردهم سبز است (نخ‌ایمنی، هویت Audit، پشتیبان/بازیابی امن، Migration).")
