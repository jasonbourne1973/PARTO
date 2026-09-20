"""
بررسی‌های دور چهاردهم: داوری فنی مدیر پروژه (۱۵ مورد)

مرحلهٔ ۱ — اولویت قرمز:
  A) اتصال SQLite و تراکنش در چند نخ (موارد ۱، ۳، ۴) ................ ۹ بررسی
  B) هویت کاربر/سیستم در Audit بین نخ‌ها (مورد ۲) ..................... ۶ بررسی
  C) پشتیبان امن، بازیابی امن و Path Traversal (موارد ۵، ۶، ۱۳) ...... ۱۰ بررسی
  D) یکپارچگی Migration (مورد ۱۱) ...................................... ۳ بررسی

مرحلهٔ ۲ — اولویت نارنجی/زرد:
  E) رفع N+1 با خوانش دسته‌ای و همان معناشناسی (مورد ۱۵) ............. ۸ بررسی
  F) پوشش تریگرهای Audit و old/new معنادار (موارد ۷، ۸) .............. ۶ بررسی
  G) یادآوری بدون تکرار با جست‌وجوی موجودیت (مورد ۹) .................. ۲ بررسی
  H) یک مسیر واحد برای DAL تفسیر حرفه‌ای (مورد ۱۰) ..................... ۲ بررسی
  I) وابستگی‌ها فقط از requirements.txt (مورد ۱۲) ...................... ۲ بررسی
  J) پاکسازی اعلان‌ها واقعاً هر ۲۴ ساعت (مورد ۱۴) ...................... ۲ بررسی

جمع: ۵۰ بررسی

هر بررسی روی یک دیتابیس موقت اجرا می‌شود و به داده‌های کاربر دست نمی‌زند.
بخش‌های B و E به PySide6 نیاز دارند (کارگرهای واقعی QThread و صفحهٔ واقعی
پروندهٔ دانش‌آموز)؛ با QT_QPA_PLATFORM=offscreen اجرا می‌شود.
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
migrate_body = conn_src.split("def _migrate_database")[1].split("def _create_all_tables")[0]
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
print("بخش E: رفع N+1 — خوانش دسته‌ای با همان معناشناسی (مورد ۱۵)")
print("=" * 76)

import ast  # noqa: E402
import re  # noqa: E402

from dal.academic_year_dal import AcademicYearDAL  # noqa: E402
from dal.competency_dal import CompetencyDAL  # noqa: E402
from dal.intervention_dal import InterventionDAL  # noqa: E402
from dal.observation_dal import ObservationDAL  # noqa: E402
from dal.staff_dal import StaffDAL  # noqa: E402
from dal.student_academic_profile_dal import StudentAcademicProfileDAL  # noqa: E402
from dal.student_dal import StudentDAL  # noqa: E402
from dal.teacher_assignment_dal import TeacherAssignmentDAL  # noqa: E402
from models.observation import Observation  # noqa: E402
from models.student import Student  # noqa: E402
from models.student_academic_profile import StudentAcademicProfile  # noqa: E402
from models.teacher_assignment import TeacherAssignment  # noqa: E402

student_dal = StudentDAL()
profile_dal = StudentAcademicProfileDAL()
competency_dal = CompetencyDAL()
intervention_dal = InterventionDAL()
staff_dal = StaffDAL()
observation_dal = ObservationDAL()
active_year = AcademicYearDAL().get_active()

# --- داده‌های آزمایشی: ۱۵ دانش‌آموز با پروندهٔ فعال + ۱ حذف‌شده + ۱ فقط فارغ‌التحصیل
e_ids = []
with quiet():
    for i in range(17):
        st = Student()
        st.first_name = f"دسته{i}"
        st.last_name = "چهاردهم"
        st.national_code = f"14{i:08d}"
        st.is_active = 1
        sid = student_dal.create(st).id
        e_ids.append(sid)
        prof = StudentAcademicProfile()
        prof.student_id = sid
        prof.academic_year_id = active_year.id
        prof.grade = (i % 6) + 1
        prof.class_name = "الف"
        if i == 16:
            prof.status = "graduated"
        profile_dal.create(prof)
        if i < 15:
            ta = TeacherAssignment()
            ta.student_id = sid
            ta.staff_id = 1
            ta.academic_year_id = active_year.id
            ta.grade = prof.grade
            ta.is_active = 1
            TeacherAssignmentDAL().create(ta)
    student_dal.delete(e_ids[15])
    e_comps = competency_dal.get_all()[:3]
    e_profile = profile_dal.get_active_by_student(e_ids[0])
    for k in range(12):
        o = Observation()
        o.student_profile_id = e_profile.id
        o.staff_id = 1
        o.competency_id = e_comps[k % 3].id
        o.observation_date = f"1405/07/{(k % 28) + 1:02d}"
        o.description = "شرح آزمایشی"
        o.behavior = "رفتار ثبت‌شدهٔ آزمایشی"
        o.behavior_type = "مثبت" if k % 2 == 0 else "منفی"
        o.severity = 2
        observation_dal.create(o)

QUERY_LOG = []


def _trace(statement):
    QUERY_LOG.append(statement)


def _count(pattern):
    rx = re.compile(pattern, re.IGNORECASE)
    return sum(1 for q in QUERY_LOG if rx.search(q))


def _reset():
    del QUERY_LOG[:]


conn.set_trace_callback(_trace)

# --- E1: StudentDAL.get_by_ids ≡ get_by_id (حذف‌شده‌ها بیرون، ناموجود بیرون) و «یک» کوئری
_reset()
single_students = {sid: student_dal.get_by_id(sid) for sid in e_ids}
n_single = _count(r"FROM students\b")
_reset()
batch_students = student_dal.get_by_ids(e_ids + [None, 987654])
n_batch = _count(r"FROM students\b")
same_students = all(
    (single_students[sid] is None) == (sid not in batch_students)
    and (single_students[sid] is None
         or single_students[sid].full_name == batch_students[sid].full_name)
    for sid in e_ids)
check("E", "StudentDAL.get_by_ids همان نتیجهٔ get_by_id را برای ۱۷ شناسه می‌دهد (حذف‌شده/ناموجود بیرون) با ۱ کوئری به‌جای ۱۷",
      same_students and n_single == 17 and n_batch == 1
      and e_ids[15] not in batch_students
      and e_ids[15] in student_dal.get_by_ids([e_ids[15]], include_deleted=True),
      f"single={n_single} batch={n_batch} same={same_students}")

# --- E2: پروندهٔ فعال دسته‌ای ≡ get_active_by_student (سال فعال، وضعیت غیرپایانی)
_reset()
single_profiles = {sid: profile_dal.get_active_by_student(sid) for sid in e_ids}
n_single = _count(r"FROM student_academic_profiles\b")
_reset()
batch_profiles = profile_dal.get_active_by_students(e_ids)
n_batch = _count(r"FROM student_academic_profiles\b")
same_profiles = all(
    (single_profiles[sid] is None) == (sid not in batch_profiles)
    and (single_profiles[sid] is None
         or single_profiles[sid].id == batch_profiles[sid].id)
    for sid in e_ids)
check("E", "get_active_by_students همان پروندهٔ فعالِ get_active_by_student را می‌دهد (فارغ‌التحصیل بیرون) با ۱ کوئری به‌جای ۱۷",
      same_profiles and n_single == 17 and n_batch == 1
      and e_ids[16] not in batch_profiles and len(batch_profiles) == 16,
      f"single={n_single} batch={n_batch} same={same_profiles} n={len(batch_profiles)}")

# --- E3: سایر خوانش‌های دسته‌ای: پرونده/شایستگی/مداخله/کادر + تکه‌تکه‌شدن IN
pids = [pr.id for pr in batch_profiles.values()]
_reset()
by_pid = profile_dal.get_by_ids(pids + [None])
n_p = _count(r"FROM student_academic_profiles\b")
_reset()
comp_objs = competency_dal.get_by_ids([c.id for c in e_comps] * 4)
comp_titles = competency_dal.get_titles_by_ids([c.id for c in e_comps])
n_c = _count(r"FROM competencies\b")
_reset()
inter_map = intervention_dal.get_by_ids([1, 2, 3, 999999])
n_i = _count(r"FROM interventions\b")
_reset()
staff_names = staff_dal.get_names_by_ids([1, None, 999999])
n_s = _count(r"full_name FROM staff\b")
_reset()
big = student_dal.get_by_ids(list(range(1, 1201)))
n_big = _count(r"FROM students\b")
_reset()
empty_calls = (student_dal.get_by_ids([]), profile_dal.get_active_by_students([None]),
               competency_dal.get_titles_by_ids(None))
n_empty = len(QUERY_LOG)
check("E", "پرونده/شایستگی/مداخله/کادر هم دسته‌ای خوانده می‌شوند؛ ۱۲۰۰ شناسه در ۳ تکهٔ IN؛ ورودی خالی → صفر کوئری",
      set(by_pid) == set(pids) and n_p == 1
      and {c.id for c in e_comps} == set(comp_objs)
      and all(comp_objs[c.id].title == c.title == comp_titles[c.id] for c in e_comps)
      and n_c == 2 and n_i == 1 and isinstance(inter_map, dict)
      and staff_names.get(1) and n_s == 1
      and n_big == 3 and len(big) >= 17
      and empty_calls == ({}, {}, {}) and n_empty == 0,
      f"p={n_p} c={n_c} i={n_i} s={n_s} big={n_big} empty={n_empty}")

# --- E4: سرویس‌های تحلیلی: آمار شایستگی از روی ۱۲ مشاهده با ۱ کوئری شایستگی (قبلاً ۱۲)
from services.teacher_performance_service import TeacherPerformanceService  # noqa: E402
from services.trend_analysis_service import TrendAnalysisService  # noqa: E402

obs_list = observation_dal.get_by_student_profile(e_profile.id)
_reset()
comp_stats = TeacherPerformanceService()._calculate_competency_stats(obs_list)
n_perf = _count(r"FROM competencies\b")
_reset()
trend_stats = TrendAnalysisService()._competency_stats(obs_list) \
    if hasattr(TrendAnalysisService(), "_competency_stats") else None
n_trend = _count(r"FROM competencies\b")
expected_titles = {c.title for c in e_comps}
check("E", "TeacherPerformanceService: آمار ۱۲ مشاهده روی ۳ شایستگی با ۱ کوئری شایستگی و همان شمارش‌ها",
      set(comp_stats) == expected_titles and n_perf == 1
      and sum(v["count"] for v in comp_stats.values()) == 12
      and sum(v["positive"] for v in comp_stats.values()) == 6
      and n_trend <= 1,
      f"titles={sorted(comp_stats)} perf={n_perf} trend={n_trend}")

# --- E5: داشبورد معلم با فیلتر سال: ۱۵ دانش‌آموز → تعداد کوئری مستقل از N
from services.dashboard_service import DashboardService  # noqa: E402

_reset()
with quiet():
    teacher_stats = DashboardService()._get_teacher_stats(1, active_year.id)
n_students_q = _count(r"FROM students\b")
n_profiles_q = _count(r"FROM student_academic_profiles\b")
check("E", "DashboardService._get_teacher_stats با ۱۵ دانش‌آموز و فیلتر سال: ۱ کوئری دانش‌آموز و ≤۲ کوئری پرونده (قبلاً یکی به ازای هر رکورد)",
      teacher_stats is not None and teacher_stats["students_count"] == 15
      and teacher_stats["observations_count"] >= 12
      and n_students_q == 1 and n_profiles_q <= 2,
      f"stats={teacher_stats} students_q={n_students_q} profiles_q={n_profiles_q}")

# --- E6: صفحهٔ پروندهٔ دانش‌آموز (رابط واقعی): لیست دانش‌آموزان با ۱ کوئری پرونده
page_error = None
combo_count = -1
n_page_profiles = -1
n_page_students = -1
try:
    from views.pages.student_profile_page import StudentProfilePage

    with quiet():
        page = StudentProfilePage()
    _reset()
    with quiet():
        page.load_student_list()
    n_page_profiles = _count(r"FROM student_academic_profiles\b")
    n_page_students = _count(r"FROM students\b")
    combo_count = page.student_select_combo.count()
except Exception as e:  # pragma: no cover
    page_error = str(e)
all_students_count = len(student_dal.get_all())
check("E", "StudentProfilePage.load_student_list: همهٔ دانش‌آموزان با پایه نمایش داده می‌شوند ولی فقط ۱ کوئری پرونده زده می‌شود (نه یکی برای هر دانش‌آموز)",
      page_error is None and combo_count == all_students_count + 1
      and n_page_profiles == 1 and n_page_students == 1,
      f"error={page_error} combo={combo_count} students={all_students_count} "
      f"profile_q={n_page_profiles} student_q={n_page_students}")

conn.set_trace_callback(None)


# --- E7: بازرسی ایستا: هیچ حلقه‌ای در سرویس‌ها/صفحه‌ها برای هر رکورد get_by_id/get_active_by_student نمی‌زند
def _n_plus_one_sites():
    sites = []
    roots = [os.path.join("services"), os.path.join("views", "pages")]
    for root in roots:
        for name in sorted(os.listdir(root)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            tree = ast.parse(read(path))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.For, ast.ListComp, ast.GeneratorExp)):
                    continue
                for sub in ast.walk(node):
                    if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                            and sub.func.attr in ("get_by_id", "get_active_by_student")
                            and isinstance(sub.func.value, ast.Attribute)
                            and sub.func.value.attr in (
                                "student_dal", "profile_dal", "competency_dal",
                                "staff_dal", "intervention_dal")):
                        sites.append(f"{path}:{sub.lineno}")
    return sorted(set(sites))


residual = _n_plus_one_sites()
# تنها استثنا: حلقهٔ «ارتقاء» که برای هر دانش‌آموز پرونده را می‌خواند و «می‌نویسد»
# (مسیر نوشتن تراکنشی، نه نمایش)؛ عمداً دست نخورده است.
allowed = {site for site in residual if site.startswith(os.path.join("views", "pages", "promotion_page.py"))}
check("E", "بازرسی ایستا: در سرویس‌ها و صفحه‌ها هیچ حلقهٔ نمایشی «برای هر رکورد یک get_by_id/get_active_by_student» باقی نمانده",
      set(residual) == allowed and len(allowed) <= 1,
      f"residual={residual}")

# --- E8: دو خرابیِ واقعی که همین بازرسی در مسیر معلم پیدا کرد (رگرسیون‌گیر)
#   ۱) TeacherAssignmentDAL._row_to_assignment از row.get استفاده می‌کرد؛ sqlite3.Row
#      متد get ندارد → هر خوانش انتسابِ معلم AttributeError می‌داد.
#   ۲) TeacherReportPage.generate_recommendations سه‌تایی‌های «شایستگی برتر» را
#      دوتایی باز می‌کرد → ValueError و شکست کل گزارش معلم.
teacher_assignments = TeacherAssignmentDAL().get_by_teacher(1, active_year.id)
assignment_ok = (len(teacher_assignments) >= 15
                 and all(a.student_name for a in teacher_assignments)
                 and all(a.teacher_name for a in teacher_assignments))
report_error = None
strength_line = ""
try:
    from views.pages.teacher_report_page import TeacherReportPage

    with quiet():
        # سه رفتار مثبت دیگر روی شایستگی اول → الگوی «توانمندی» (۵ مثبت از ۷)
        for k in range(3):
            o = Observation()
            o.student_profile_id = e_profile.id
            o.staff_id = 1
            o.competency_id = e_comps[0].id
            o.observation_date = f"1405/08/{k + 1:02d}"
            o.description = "شرح آزمایشی"
            o.behavior = "رفتار مثبت ثبت‌شده"
            o.behavior_type = "مثبت"
            o.severity = 1
            observation_dal.create(o)
        report_page = TeacherReportPage()
        report_data = report_page.collect_report_data(
            teacher_assignments, "1405/01/01", "1405/12/29")
        recs = report_page.generate_recommendations(report_data)
    strength_line = next((line for line in recs["teacher"] if "شایستگی‌های برتر" in line), "")
except Exception as e:  # pragma: no cover
    report_error = f"{type(e).__name__}: {e}"
check("E", "مسیر معلم سالم است: انتساب‌های معلم بدون AttributeError خوانده می‌شوند و گزارش معلم با الگوی «توانمندی» بدون ValueError ساخته می‌شود (متن رفتارمحور، نه شدت‌محور)",
      assignment_ok and report_error is None
      and e_comps[0].title in strength_line and "رفتار مثبت از" in strength_line
      and "میانگین شدت" not in strength_line
      and report_data["total_observations"] >= 15,
      f"assignments={len(teacher_assignments)} ok={assignment_ok} error={report_error} line={strength_line[:80]!r}")

# ============================================================================
print("=" * 76)
print("بخش F: پوشش تریگرهای Audit و ثبت معنادار قبل/بعد (موارد ۷ و ۸)")
print("=" * 76)

PM_AUDIT_TABLES = (
    "students", "observations", "interventions", "followups",
    "student_academic_profiles", "staff", "competencies",
    "family_contexts", "parent_interviews", "counseling_sessions",
    "screenings", "screening_results", "professional_interpretations",
    "individual_goals", "extracurricular_activities", "recommendations",
    "users", "attachments",
)
trigger_rows = conn.execute(
    "SELECT tbl_name, sql FROM sqlite_master WHERE type = 'trigger'").fetchall()
triggers_by_table = {}
for row in trigger_rows:
    triggers_by_table.setdefault(row[0], []).append((row[1] or "").upper())
missing_cov = []
trigger_names = {row[0] for row in conn.execute(
    "SELECT name FROM sqlite_master WHERE type = 'trigger'").fetchall()}
for table in PM_AUDIT_TABLES:
    sqls = triggers_by_table.get(table, [])
    kinds = {kind for kind in ("INSERT", "UPDATE", "DELETE")
             if any(re.search(rf"AFTER\s+{kind}\s+ON", sql) for sql in sqls)}
    names_ok = all(f"trg_{table}_{suffix}_audit" in trigger_names
                   for suffix in ("insert", "update", "soft_delete", "restore", "hard_delete"))
    if kinds != {"INSERT", "UPDATE", "DELETE"} or not names_ok:
        missing_cov.append((table, sorted(kinds), names_ok))
# (دور ۱۵) notifications هم به فهرست مدیریت‌شده اضافه شد؛ پس «همهٔ ۱۸
# جدول مدیر پروژه زیرمجموعهٔ فهرست» بررسی می‌شود، نه برابری دقیق.
check("F", "هر ۱۸ جدول فهرست مدیر پروژه (۷ جدول قبلی + ۱۱ جدول جدید) پنج تریگر insert/update/soft_delete/restore/hard_delete دارند",
      not missing_cov and set(PM_AUDIT_TABLES) <= set(dbc.DatabaseConnection._AUDIT_TABLES),
      f"missing={missing_cov}")

# --- F2: ویرایش زمینهٔ خانوادگی → old/new کامل و تفاوت واقعی قابل دیدن
from dal.family_context_dal import FamilyContextDAL  # noqa: E402
from models.family_context import FamilyContext  # noqa: E402

with quiet():
    fc = FamilyContext()
    fc.student_profile_id = e_profile.id
    fc.parental_support = "low"
    fc.guardian_status = "both_parents"
    fc.recorded_by = 1
    fc = FamilyContextDAL().create(fc)
    fc.parental_support = "high"
    FamilyContextDAL().update(fc)
fc_audit = conn.execute(
    "SELECT action, old_value, new_value, user_id FROM audit_logs "
    "WHERE entity_type = 'family_contexts' AND entity_id = ? ORDER BY id",
    (fc.id,)).fetchall()
fc_actions = [r[0] for r in fc_audit]
edit_row = next((r for r in fc_audit if r[0] == "edit"), None)
try:
    fc_old = json.loads(edit_row[1]) if edit_row else {}
    fc_new = json.loads(edit_row[2]) if edit_row else {}
except (TypeError, ValueError):
    fc_old, fc_new = {}, {}
check("F", "ویرایش family_contexts: Audit با old/new کاملِ JSON (نه فقط id) و تغییر parental_support از low به high قابل دیدن است",
      fc_actions[:2] == ["create", "edit"]
      and fc_old.get("parental_support") == "low" and fc_new.get("parental_support") == "high"
      and len(fc_old) > 5 and fc_old.get("id") == fc.id,
      f"actions={fc_actions} old_keys={len(fc_old)} old={fc_old.get('parental_support')} new={fc_new.get('parental_support')}")

# --- F3: users: تغییر رمز ثبت می‌شود ولی password_hash هرگز در Audit نمی‌آید
from dal.user_dal import UserDAL  # noqa: E402

admin_row = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
with quiet():
    UserDAL().update_password(admin_row[0], "Round14!Secure#pass", user_id_actor=1)
user_audit = conn.execute(
    "SELECT action, old_value, new_value FROM audit_logs "
    "WHERE entity_type = 'users' AND entity_id = ? ORDER BY id DESC LIMIT 1",
    (admin_row[0],)).fetchone()
leak = any(
    (val and "password_hash" in val) for val in (user_audit[1], user_audit[2])) if user_audit else True
check("F", "users: ویرایش کاربر در Audit ثبت می‌شود اما ستون password_hash نه در old_value است و نه در new_value",
      user_audit is not None and user_audit[0] == "edit" and not leak
      and json.loads(user_audit[2]).get("id") == admin_row[0],
      f"row={user_audit and user_audit[0]} leak={leak}")

# --- F4: سرویس + تریگر → فقط «یک» ردیف Audit برای ایجاد (بدون تکرار BaseService)
from services.student_service import StudentService  # noqa: E402

with quiet():
    svc_student = StudentService().create_student(
        {"first_name": "سرویس", "last_name": "چهاردهم", "national_code": "1414141414",
         "grade": 2}, user_id=1)
svc_rows = conn.execute(
    "SELECT action, user_id FROM audit_logs WHERE entity_type = 'students' AND entity_id = ?",
    (svc_student.id,)).fetchall()
check("F", "ایجاد دانش‌آموز از مسیر سرویس: دقیقاً یک ردیف Audit «create» با user_id واقعی (تریگر + BaseService تکرار نمی‌کنند)",
      len(svc_rows) == 1 and svc_rows[0][0] == "create" and svc_rows[0][1] == 1,
      f"rows={svc_rows}")

# --- F5: حذف نرم و بازیابی هم با مقدار قبل/بعد معنادار ثبت می‌شوند
with quiet():
    student_dal.delete(svc_student.id)
    student_dal.restore(svc_student.id)
sd_rows = conn.execute(
    "SELECT action, old_value, new_value FROM audit_logs "
    "WHERE entity_type = 'students' AND entity_id = ? ORDER BY id",
    (svc_student.id,)).fetchall()
sd_actions = [r[0] for r in sd_rows]
soft = next((r for r in sd_rows if r[0] == "delete_soft"), None)
rest = next((r for r in sd_rows if r[0] == "restore"), None)
soft_ok = (soft and soft[1] and json.loads(soft[1]).get("is_deleted") == 0
           and json.loads(soft[1]).get("first_name") == "سرویس")
rest_ok = (rest and rest[2] and json.loads(rest[2]).get("is_deleted") == 0
           and json.loads(rest[2]).get("id") == svc_student.id)
check("F", "حذف نرم و بازیابی: delete_soft تصویر کامل ردیف قبل از حذف و restore تصویر کامل بعد از بازیابی را ثبت می‌کنند",
      sd_actions == ["create", "delete_soft", "restore"] and bool(soft_ok) and bool(rest_ok),
      f"actions={sd_actions} soft_ok={bool(soft_ok)} rest_ok={bool(rest_ok)}")

# --- F6: حذف فیزیکی (permanent_delete) هم بدون رد نمی‌ماند
with quiet():
    hard_obs = Observation()
    hard_obs.student_profile_id = e_profile.id
    hard_obs.staff_id = 1
    hard_obs.competency_id = e_comps[0].id
    hard_obs.observation_date = "1405/07/20"
    hard_obs.description = "مشاهدهٔ حذف فیزیکی"
    hard_obs.behavior = "رفتار آزمایشی"
    hard_obs.behavior_type = "خنثی"
    hard_obs.severity = 1
    hard_obs = observation_dal.create(hard_obs)
    observation_dal.permanent_delete(hard_obs.id)
hard_rows = conn.execute(
    "SELECT action, old_value, new_value, user_id FROM audit_logs "
    "WHERE entity_type = 'observations' AND entity_id = ? ORDER BY id", (hard_obs.id,)).fetchall()
hard_actions = [r[0] for r in hard_rows]
hard = next((r for r in hard_rows if r[0] == "delete"), None)
hard_old = json.loads(hard[1]) if hard and hard[1] else {}
still_there = conn.execute("SELECT COUNT(*) FROM observations WHERE id = ?", (hard_obs.id,)).fetchone()[0]
check("F", "حذف فیزیکی (permanent_delete): تریگر AFTER DELETE یک ردیف «delete» با تصویر کامل ردیف حذف‌شده و کاربر واقعی ثبت می‌کند",
      hard_actions == ["create", "delete"] and hard_old.get("description") == "مشاهدهٔ حذف فیزیکی"
      and hard_old.get("id") == hard_obs.id and hard[3] == 1 and still_there == 0,
      f"actions={hard_actions} old_keys={len(hard_old)}")

# ============================================================================
print("=" * 76)
print("بخش G: جلوگیری از یادآوری تکراری با جست‌وجوی موجودیت (مورد ۹)")
print("=" * 76)

import jdatetime  # noqa: E402

from dal.followup_dal import FollowUpDAL  # noqa: E402
from dal.notification_dal import NotificationDAL  # noqa: E402
from models.followup import FollowUp  # noqa: E402
from models.intervention import Intervention  # noqa: E402
from models.notification import Notification  # noqa: E402
from services.notification_service import NotificationService  # noqa: E402

yesterday = jdatetime.date.today() - jdatetime.timedelta(days=1)
with quiet():
    inter = Intervention()
    inter.student_profile_id = e_profile.id
    inter.staff_id = 1
    inter.type = "counseling"
    inter.date = "1405/07/01"
    inter.description = "مداخلهٔ آزمایشی چهاردهم"
    inter = intervention_dal.create(inter)
    fu = FollowUp()
    fu.intervention_id = inter.id
    fu.staff_id = 1
    fu.date = "1405/07/02"
    fu.method = "phone"
    fu.description = "پیگیری آزمایشی"
    fu.status = "pending"
    fu.next_action_date = f"{yesterday.year}/{yesterday.month:02d}/{yesterday.day:02d}"
    fu = FollowUpDAL().create(fu)

notif_service = NotificationService()
notif_dal = NotificationDAL()


def _overdue_count():
    return conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE entity_type = 'followup' AND entity_id = ? "
        "AND type = ? AND is_deleted = 0", (fu.id, Notification.TYPE_OVERDUE)).fetchone()[0]


with quiet():
    first_run = notif_service.check_and_create_reminders()
after_first = _overdue_count()
# ۱۲ اعلان جدیدتر برای همان کاربر → اعلان پیگیری دیگر جزو «۱۰ اعلان آخر» نیست
# (اعلان پیگیری به سه روز قبل برده می‌شود تا ترتیب created_at قطعی باشد)
with quiet():
    conn.execute(
        "UPDATE notifications SET created_at = datetime('now', '-3 days') "
        "WHERE entity_type = 'followup' AND entity_id = ?", (fu.id,))
    conn.commit()
    for k in range(12):
        notif_service.create_notification(
            user_id=1, notification_type=Notification.TYPE_SYSTEM
            if hasattr(Notification, "TYPE_SYSTEM") else "system",
            title=f"اعلان پرکننده {k}", message="برای جابه‌جا کردن اعلان پیگیری از ۱۰ مورد آخر")
    second_run = notif_service.check_and_create_reminders()
after_second = _overdue_count()
recent_ids = [n.entity_id for n in notif_dal.get_by_user(1, limit=10)]
check("G", "پیگیری معوق: اجرای اول یک اعلان می‌سازد؛ بعد از ۱۲ اعلان جدیدتر (خارج از ۱۰ مورد آخر) اجرای دوم اعلان تکراری نمی‌سازد",
      after_first == 1 and after_second == 1 and fu.id not in recent_ids
      and second_run["total"] == 0,
      f"first={after_first} second={after_second} in_recent={fu.id in recent_ids} run2={second_run}")

# --- G2: معنای «فعال» حفظ شده: اعلان خوانده‌شده مانع اعلان جدید نیست؛ پرس‌وجو بر اساس موجودیت است
exists_before = notif_service._check_existing_notification(fu.id, 1, Notification.TYPE_OVERDUE)
other_user = notif_service._check_existing_notification(fu.id, 2, Notification.TYPE_OVERDUE)
other_type = notif_service._check_existing_notification(fu.id, 1, Notification.TYPE_REMINDER)
notif_id = conn.execute(
    "SELECT id FROM notifications WHERE entity_type = 'followup' AND entity_id = ? AND type = ?",
    (fu.id, Notification.TYPE_OVERDUE)).fetchone()[0]
with quiet():
    notif_dal.mark_as_read(notif_id)
exists_after = notif_service._check_existing_notification(fu.id, 1, Notification.TYPE_OVERDUE)
notif_src = read("services/notification_service.py")
check_body = notif_src.split("def _check_existing_notification")[1].split("def _enrich_notification")[0]
check("G", "جست‌وجو دقیقاً بر اساس (کاربر، نوع اعلان، نوع/شناسهٔ موجودیت) است؛ کاربر/نوع دیگر → نه؛ اعلان خوانده‌شده → فعال نیست؛ بدون get_by_user(limit=10)",
      exists_before is True and other_user is False and other_type is False
      and exists_after is False and "exists_for_entity" in check_body
      and "get_by_user" not in check_body,
      f"before={exists_before} other_user={other_user} other_type={other_type} after={exists_after}")

# ============================================================================
print("=" * 76)
print("بخش H: یک مسیر واحد برای DAL تفسیر حرفه‌ای (مورد ۱۰)")
print("=" * 76)

import importlib.util  # noqa: E402

from dal.professional_interpretation_dal import ProfessionalInterpretationDAL  # noqa: E402
from models.professional_interpretation import ProfessionalInterpretation  # noqa: E402

shim_gone = importlib.util.find_spec("dal.interpretation_dal") is None \
    and not os.path.exists(os.path.join("dal", "interpretation_dal.py"))
shim_refs = []
for root in ("dal", "services", "views", "utils", "models", "database", "tests"):
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith(".py") and "interpretation_dal import" in read(os.path.join(dirpath, name)) \
                    and "professional_interpretation_dal import" not in read(os.path.join(dirpath, name)):
                shim_refs.append(os.path.join(dirpath, name))
main_src = read("main.py")
check("H", "فایل تکراری dal/interpretation_dal.py حذف شده و هیچ ماژولی (dal/services/views/utils/models/database/tests/main) آن را import نمی‌کند",
      shim_gone and not shim_refs and "interpretation_dal import InterpretationDAL" not in main_src,
      f"gone={shim_gone} refs={shim_refs}")

with quiet():
    interp = ProfessionalInterpretation()
    interp.student_profile_id = e_profile.id
    interp.staff_id = 1
    interp.level = "normal"
    interp.title = "تفسیر آزمایشی ۱۴"
    interp.detailed_text = "متن تفسیری آزمایشی برای بررسی دور چهاردهم"
    interp.status = "draft"
    interp = ProfessionalInterpretationDAL().create(interp)
fetched_interp = ProfessionalInterpretationDAL().get_by_id(interp.id)
interp_users = [path for path in ("services/report_generator.py",)
                if "ProfessionalInterpretationDAL()" in read(path)]
check("H", "مسیر واحد ProfessionalInterpretationDAL کار می‌کند (create/get) و گزارش‌ساز از همین مسیر استفاده می‌کند",
      fetched_interp is not None and fetched_interp.title == "تفسیر آزمایشی ۱۴" and interp_users,
      f"fetched={fetched_interp and fetched_interp.title}")

# ============================================================================
print("=" * 76)
print("بخش I: اجرای تست‌ها در محیط تمیز فقط با requirements.txt (مورد ۱۲)")
print("=" * 76)

REQ_IMPORT_NAMES = {
    "pyside6": {"PySide6", "shiboken6"}, "matplotlib": {"matplotlib"},
    "openpyxl": {"openpyxl"}, "jdatetime": {"jdatetime"}, "pillow": {"PIL"},
    "reportlab": {"reportlab"}, "arabic-reshaper": {"arabic_reshaper"},
    "python-bidi": {"bidi"}, "numpy": {"numpy"}, "pytest": {"pytest"},
}
req_lines = [line.split("#")[0].strip() for line in read("requirements.txt").splitlines()]
req_names = {re.split(r"[<>=!~\[]", line)[0].strip().lower() for line in req_lines if line}
allowed_imports = set()
for name in req_names:
    allowed_imports |= REQ_IMPORT_NAMES.get(name, {name})
stdlib_names = set(getattr(sys, "stdlib_module_names", set()))
local_names = {n for n in os.listdir(".") if os.path.isdir(n)} | {
    n[:-3] for n in os.listdir(".") if n.endswith(".py")}
OPTIONAL_GUARDED = {"magic"}


def _third_party_imports(paths):
    found = {}
    for path in paths:
        tree = ast.parse(read(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".")[0]]
            for n in names:
                if n in stdlib_names or n in local_names or n in allowed_imports:
                    continue
                found.setdefault(n, set()).add(path)
    return found


all_py = []
for root in ("dal", "services", "views", "utils", "models", "database", "tests", "config"):
    for dirpath, _dirs, files in os.walk(root):
        all_py += [os.path.join(dirpath, f) for f in files if f.endswith(".py")]
all_py += [n for n in os.listdir(".") if n.endswith(".py")]
unknown = _third_party_imports(all_py)
validator_src = read("utils/file_validator.py")
magic_guarded = "try:" in validator_src.rsplit("import magic", 1)[0][-200:]
check("I", "همهٔ importهای غیر-استاندارد پروژه (کد، تست‌ها و اسکریپت‌های verify) در requirements.txt هستند؛ تنها استثنا python-magic اختیاری با try/except",
      set(unknown) <= OPTIONAL_GUARDED and magic_guarded and "pytest" in req_names
      and "jdatetime" in req_names and "numpy" in req_names,
      f"unknown={ {k: sorted(v)[:3] for k, v in unknown.items()} } req={sorted(req_names)}")

test_files = [os.path.join("tests", f) for f in os.listdir("tests") if f.endswith(".py")]
tests_unknown = _third_party_imports(test_files)
tests_import_ok = all(
    "pytest" in read(path) or "unittest" in read(path) for path in test_files)
check("I", "پوشهٔ tests/ فقط به کتابخانه‌های requirements و ماژول‌های پروژه وابسته است (بدون وابستگی پنهان)؛ pytest در requirements است",
      not tests_unknown and tests_import_ok and len(test_files) >= 3,
      f"unknown={tests_unknown} files={len(test_files)}")

# ============================================================================
print("=" * 76)
print("بخش J: پاکسازی اعلان‌ها واقعاً هر ۲۴ ساعت (مورد ۱۴)")
print("=" * 76)

from datetime import timedelta  # noqa: E402

from utils.notification_scheduler import NotificationScheduler  # noqa: E402
from utils.time_utils import utc_now  # noqa: E402

scheduler = NotificationScheduler()
scheduler._last_cleanup_time = None
first_none = scheduler._should_cleanup()
scheduler._last_cleanup_time = utc_now()
just_now = scheduler._should_cleanup()
scheduler._last_cleanup_time = utc_now() - timedelta(hours=23, minutes=50)
almost = scheduler._should_cleanup()
scheduler._last_cleanup_time = utc_now() - timedelta(hours=25)
stale = scheduler._should_cleanup()
check("J", "_should_cleanup: بدون سابقه → بله؛ همین الان → خیر؛ ۲۳ ساعت و ۵۰ دقیقه → خیر؛ ۲۵ ساعت → بله",
      first_none is True and just_now is False and almost is False and stale is True
      and NotificationScheduler._CLEANUP_INTERVAL_HOURS == 24,
      f"none={first_none} now={just_now} 23h50={almost} 25h={stale}")


class _FakeNotificationService:
    def __init__(self):
        self.cleanups = 0
        self.checks = 0

    def check_and_create_reminders(self):
        self.checks += 1
        return {"created_count": 0, "overdue_count": 0, "total": 0}

    def cleanup_old_notifications(self):
        self.cleanups += 1
        return 0


fake = _FakeNotificationService()
real_service = scheduler.notification_service
scheduler.notification_service = fake
scheduler._last_cleanup_time = None
try:
    with quiet():
        scheduler._run_scheduled_tasks()
        scheduler._run_scheduled_tasks()
        scheduler._run_scheduled_tasks()
        stamp_after_runs = scheduler._last_cleanup_time
        scheduler._last_cleanup_time = utc_now() - timedelta(hours=24, minutes=1)
        scheduler._run_scheduled_tasks()
finally:
    scheduler.notification_service = real_service
check("J", "سه اجرای پیاپیِ وظایف ساعتی فقط یک پاکسازی انجام می‌دهند؛ بعد از گذشت ۲۴ ساعت پاکسازی دوم انجام می‌شود (یادآوری‌ها هر بار بررسی می‌شوند)",
      fake.checks == 4 and fake.cleanups == 2 and stamp_after_runs is not None,
      f"checks={fake.checks} cleanups={fake.cleanups}")

# ============================================================================
print("=" * 76)
print(f"نتیجهٔ دور چهاردهم (مرحله‌های ۱ و ۲):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("موارد ناموفق:")
    for item in FAILURES:
        print(f"  - {item}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های دور چهاردهم سبز است (نخ‌ایمنی، هویت Audit، پشتیبان/بازیابی امن، Migration، "
      "N+1، پوشش Audit، اعلان بدون تکرار، DAL واحد، محیط تمیز، پاکسازی ۲۴ساعته).")
