"""
بررسی‌های دور شانزدهم — عیب‌یابی فنی کامل (مأموریت ۳۸ بندی)

هر بخش، آزمون «کارکردی با پیش/پس‌شرط» است: نه فقط «استثنا نداد»، بلکه وضعیت
دیتابیس/فایل قبل و بعد از عمل مقایسه می‌شود.

مرحلهٔ ۱ — Migration، تست‌های قدیمی، نسخهٔ پایتون (بندهای ۴، ۵، ۶، ۱۵، ۲۲-migration):
  A) کشف پویا از فایل‌سیستم، شکست بلند بارگذاری، ترتیب Downgrade، تراکنش هر گام،
     logging با traceback، مسیر خطای main.py، makeSuite، نسخهٔ پایتون ........ ۱۵ بررسی

مرحلهٔ ۲ — Backup/Restore و file handling (بندهای ۱۱، ۱۲، ۲۵):
  B) نام امن، نوشتن اتمیک، پاکسازی در شکست، وضعیت واقعی فهرست، حذف امن با sidecar،
     بازیابی با پیش/پس‌شرط، جابه‌جایی امن پیوست‌ها، انتقال پوشهٔ قدیمی، توقف واقعی
     زمان‌بند، صفحهٔ پشتیبان‌گیری offscreen .......................................... ۱۲ بررسی

جمع فعلی: ۲۷ بررسی
"""

import contextlib
import io
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import types

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


TMP = tempfile.mkdtemp(prefix="round16_verify_")

# ============================================================
print("=" * 76)
print("بخش A: Migration — کشف پویا، شکست بلند، ترتیب Downgrade، تراکنش هر گام، لاگ")
print("=" * 76)

import database.migrations.manager as mm  # noqa: E402

# خروجی کنسولِ لاگر برنامه در این اسکریپت خاموش می‌شود (فایل لاگ و
# هندلر گیرندهٔ آزمون همچنان همه‌چیز را می‌گیرند) تا tracebackهای عمدی
# سناریوهای شکست، خروجی بررسی را شلوغ نکنند.
for _h in list(mm.logger.handlers):
    if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
        _h.setLevel(logging.CRITICAL)


class _CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


def _write(dirname, filename, body):
    with open(os.path.join(dirname, filename), "w", encoding="utf-8") as fh:
        fh.write(body)


# --- A1: کشف پویا از فایل‌سیستم، بدون سقف شماره
disc_dir = tempfile.mkdtemp(prefix="r16_disc_", dir=TMP)
for ver in (1, 2, 7, 100):
    _write(disc_dir, f"migration_v{ver}.py",
           f"VERSION = {ver}\n\ndef upgrade(connection):\n    pass\n\ndef downgrade(connection):\n    pass\n")
_write(disc_dir, "notes.py", "x = 1\n")
_write(disc_dir, "migration_vX.py", "def upgrade(connection):\n    pass\n")
_write(disc_dir, "migration_v3.txt", "not python\n")
found_dyn = mm._discover_migrations(directory=disc_dir)
manager_src = read("database/migrations/manager.py")
check("A", "کشف migration از روی نام فایل (migration_vN.py) بدون سقف ثابت: نسخهٔ ۱۰۰ هم پیدا می‌شود و فایل‌های نامربوط رد می‌شوند",
      sorted(found_dyn) == [1, 2, 7, 100]
      and all(getattr(found_dyn[v], "VERSION", None) == v for v in found_dyn)
      and "range(1, 100)" not in manager_src,
      f"found={sorted(found_dyn)}")

# --- A2: فایلِ موجود با import داخلی شکست‌خورده → MigrationLoadError (نه «وجود ندارد»)
broken_dir = tempfile.mkdtemp(prefix="r16_broken_", dir=TMP)
_write(broken_dir, "migration_v1.py", "def upgrade(connection):\n    pass\n")
_write(broken_dir, "migration_v2.py",
       "import dependency_missing_for_parto_r16_test\n\ndef upgrade(connection):\n    pass\n")
capture = _CaptureHandler()
mm.logger.addHandler(capture)
load_error = None
try:
    mm._discover_migrations(directory=broken_dir)
except mm.MigrationLoadError as e:
    load_error = e
finally:
    mm.logger.removeHandler(capture)
err_records = [r for r in capture.records if r.levelno == logging.ERROR and "migration_v2" in r.getMessage()]
check("A", "شکست import داخلی یک migration موجود → MigrationLoadError با علت اصلی (__cause__) و ثبت ERROR همراه traceback؛ به‌عنوان «نسخهٔ گمشده» جا زده نمی‌شود",
      isinstance(load_error, mm.MigrationLoadError)
      and load_error.filename == "migration_v2.py"
      and isinstance(load_error.__cause__, ImportError)
      and len(err_records) == 1 and err_records[0].exc_info is not None,
      f"error={load_error!r}")

# --- A3: فایل بدون upgrade → MigrationLoadError
noup_dir = tempfile.mkdtemp(prefix="r16_noup_", dir=TMP)
_write(noup_dir, "migration_v1.py", "def something_else(connection):\n    pass\n")
noup_error = None
try:
    with contextlib.redirect_stdout(io.StringIO()):
        mm._discover_migrations(directory=noup_dir)
except mm.MigrationLoadError as e:
    noup_error = e
check("A", "فایل migration بدون تابع upgrade → MigrationLoadError (نه نادیده‌گرفتن خاموش)",
      isinstance(noup_error, mm.MigrationLoadError) and "upgrade" in str(noup_error),
      str(noup_error))

# --- A4: نسخهٔ گمشده در بازه همچنان MigrationMissingError است (تمایز از LoadError)
gap_db = os.path.join(TMP, "gap.db")
gap_conn = sqlite3.connect(gap_db)
mm.MigrationManager.set_version(gap_conn, 1)
real_discover = mm._discover_migrations
mm._discover_migrations = lambda: dict(found_dyn)  # {1, 2, 7, 100}
gap_error = None
try:
    mm.MigrationManager.migrate(gap_conn, 7)
except mm.MigrationMissingError as e:
    gap_error = e
finally:
    mm._discover_migrations = real_discover
gap_version = mm.MigrationManager.get_current_version(gap_conn)
gap_conn.close()
check("A", "نسخهٔ واقعاً گمشده در بازه (۳..۶) → MigrationMissingError پیش از اجرای هر گام؛ نسخه دست‌نخورده",
      isinstance(gap_error, mm.MigrationMissingError)
      and gap_error.missing == [3, 4, 5, 6] and gap_version == 1,
      f"error={gap_error} version={gap_version}")


# --- ماژول‌های ساختگی برای سناریوهای ارتقاء/بازگشت (ترتیب فراخوانی‌ها زمانی و مشترک)
CALL_LOG = []


def _fake_module(version, upgrade_fail=False, downgrade_fail=False, no_downgrade=False):
    mod = types.ModuleType(f"fake_migration_v{version}")
    calls = CALL_LOG

    def upgrade(connection):
        calls.append(("upgrade", version))
        connection.execute(f"CREATE TABLE t{version} (id INTEGER PRIMARY KEY)")
        if upgrade_fail:
            raise RuntimeError(f"upgrade v{version} intentionally failed")

    def downgrade(connection):
        calls.append(("downgrade", version))
        connection.execute(f"DROP TABLE IF EXISTS t{version}")
        connection.execute(f"CREATE TABLE downgrade_probe_{version} (id INTEGER PRIMARY KEY)")
        if downgrade_fail:
            raise RuntimeError(f"downgrade v{version} intentionally failed")
        connection.execute(f"DROP TABLE downgrade_probe_{version}")

    mod.upgrade = upgrade
    if not no_downgrade:
        mod.downgrade = downgrade
    mod.calls = calls
    return mod


def _tables(connection):
    return {r[0] for r in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")}


def _run_with(modules, connection, target):
    mm._discover_migrations = lambda: modules
    error = None
    try:
        mm.MigrationManager.migrate(connection, target)
    except Exception as e:
        error = e
    finally:
        mm._discover_migrations = real_discover
    return error


# --- A5: Downgrade موفق: اول downgrade، بعد کاهش نسخه
dg_db = os.path.join(TMP, "downgrade_ok.db")
dg_conn = sqlite3.connect(dg_db)
mods = {1: _fake_module(1), 2: _fake_module(2), 3: _fake_module(3)}
CALL_LOG.clear()
err_up = _run_with(mods, dg_conn, 3)
tables_after_up = _tables(dg_conn)
err_dg = _run_with(mods, dg_conn, 1)
tables_after_dg = _tables(dg_conn)
order = list(CALL_LOG)
check("A", "Downgrade موفق: ۳→۱ با ترتیب v3 سپس v2، جدول‌های همان نسخه‌ها حذف و نسخهٔ ثبت‌شده ۱ می‌شود",
      err_up is None and err_dg is None
      and {"t1", "t2", "t3"} <= tables_after_up
      and "t1" in tables_after_dg and not {"t2", "t3"} & tables_after_dg
      and mm.MigrationManager.get_current_version(dg_conn) == 1
      and order == [("upgrade", 1), ("upgrade", 2), ("upgrade", 3), ("downgrade", 3), ("downgrade", 2)],
      f"up={err_up} dg={err_dg} tables={sorted(tables_after_dg)} order={order}")
dg_conn.close()

# --- A6: Downgrade شکست‌خورده: نسخه قبلی حفظ، اسکیما سازگار (rollback)
dgf_db = os.path.join(TMP, "downgrade_fail.db")
dgf_conn = sqlite3.connect(dgf_db)
mods_f = {1: _fake_module(1), 2: _fake_module(2), 3: _fake_module(3, downgrade_fail=True)}
capture = _CaptureHandler()
mm.logger.addHandler(capture)
try:
    err_up = _run_with(mods_f, dgf_conn, 3)
    CALL_LOG.clear()
    err_dgf = _run_with(mods_f, dgf_conn, 1)
finally:
    mm.logger.removeHandler(capture)
tables_f = _tables(dgf_conn)
step_errors = [r for r in capture.records if r.levelno == logging.ERROR and r.exc_info is not None]
check("A", "Downgrade شکست‌خورده (v3): نسخه ۳ می‌ماند، جدول t3 سر جایش است، جدول نیمه‌کارهٔ downgrade با rollback نیست، v2 اصلاً اجرا نمی‌شود، تراکنش باز نمانده",
      err_up is None and isinstance(err_dgf, mm.MigrationStepError)
      and err_dgf.version == 3 and err_dgf.direction == "downgrade"
      and mm.MigrationManager.get_current_version(dgf_conn) == 3
      and "t3" in tables_f and "downgrade_probe_3" not in tables_f
      and CALL_LOG == [("downgrade", 3)]
      and not dgf_conn.in_transaction,
      f"err={err_dgf!r} version={mm.MigrationManager.get_current_version(dgf_conn)} tables={sorted(tables_f)}")
check("A", "شکست گام با exc_info (traceback) در لاگ برنامه ثبت می‌شود",
      len(step_errors) >= 1 and "نسخه 3" in step_errors[0].getMessage(),
      f"{len(step_errors)} records")
dgf_conn.close()

# --- A7: Upgrade شکست‌خورده وسط زنجیره: گام‌های قبلی معتبر، گام خراب rollback، نسخه = آخرین گام موفق
upf_db = os.path.join(TMP, "upgrade_fail.db")
upf_conn = sqlite3.connect(upf_db)
mm.MigrationManager.set_version(upf_conn, 1)
mods_u = {1: _fake_module(1), 2: _fake_module(2), 3: _fake_module(3, upgrade_fail=True)}
err_upf = _run_with(mods_u, upf_conn, 3)
tables_u = _tables(upf_conn)
check("A", "Upgrade شکست‌خورده در v3: v2 اعمال و نسخه ۲ ثبت شده؛ جدول t3 (DDL داخل تراکنش) با rollback نیست؛ نسخه هرگز ۳ نمی‌شود",
      isinstance(err_upf, mm.MigrationStepError) and err_upf.version == 3
      and err_upf.direction == "upgrade"
      and mm.MigrationManager.get_current_version(upf_conn) == 2
      and "t2" in tables_u and "t3" not in tables_u and not upf_conn.in_transaction,
      f"err={err_upf!r} version={mm.MigrationManager.get_current_version(upf_conn)} tables={sorted(tables_u)}")
upf_conn.close()

# --- A8: Downgrade بدون تابع downgrade → توقف با خطای روشن و نسخهٔ دست‌نخورده
nd_db = os.path.join(TMP, "no_downgrade.db")
nd_conn = sqlite3.connect(nd_db)
mods_nd = {1: _fake_module(1), 2: _fake_module(2, no_downgrade=True)}
err_nd_up = _run_with(mods_nd, nd_conn, 2)
err_nd = _run_with(mods_nd, nd_conn, 1)
check("A", "Downgrade از نسخه‌ای که تابع downgrade ندارد → MigrationLoadError با پیام روشن؛ نسخه ۲ می‌ماند (قبلاً بی‌سروصدا نسخه کم می‌شد)",
      err_nd_up is None and isinstance(err_nd, mm.MigrationLoadError)
      and "downgrade" in str(err_nd)
      and mm.MigrationManager.get_current_version(nd_conn) == 2,
      f"err={err_nd!r}")
nd_conn.close()

# --- A9: بستهٔ واقعی: کشف = فایل‌های روی دیسک
real_files = sorted(int(m.group(1)) for m in
                    (re.match(r"^migration_v(\d+)\.py$", f)
                     for f in os.listdir("database/migrations")) if m)
real_found = sorted(mm._discover_migrations())
check("A", "کشف در بستهٔ واقعی دقیقاً همان فایل‌های migration_vN.py روی دیسک است",
      real_found == real_files and real_found[-1] >= 9,
      f"files={real_files} found={real_found}")

# --- A10: logging به‌جای print؛ اجرای موفق رکورد INFO می‌سازد
migrate_src = manager_src.split("class MigrationManager")[1].split("def run_migration")[0]
discover_src = manager_src.split("def _discover_migrations")[1].split("def _begin_transaction")[0]
capture = _CaptureHandler()
mm.logger.addHandler(capture)
info_db = os.path.join(TMP, "info.db")
info_conn = sqlite3.connect(info_db)
stdout_buf = io.StringIO()
try:
    with contextlib.redirect_stdout(stdout_buf):
        err_info = _run_with({1: _fake_module(1)}, info_conn, 1)
finally:
    mm.logger.removeHandler(capture)
info_conn.close()
info_records = [r for r in capture.records if r.levelno == logging.INFO]
check("A", "در MigrationManager و کشف migration هیچ print نیست (فقط CLI run_migration چاپ می‌کند)؛ اجرای موفق در لاگ INFO ثبت می‌شود و چیزی چاپ نمی‌شود",
      "print(" not in migrate_src and "print(" not in discover_src
      and "exc_info=True" in migrate_src and "exc_info=True" in discover_src
      and err_info is None and len(info_records) >= 2 and stdout_buf.getvalue() == "",
      f"info={len(info_records)} stdout={stdout_buf.getvalue()[:60]!r}")

# --- A11: main.py — نگهبان نسخهٔ پایتون پیش از import کتابخانه‌ها؛ مسیر خطا بدون QApplication نمی‌میرد
main_src = read("main.py")
except_block = main_src.split("    except Exception as e:\n        print(f\"❌ خطا: {e}\")")[1]
check("A", "main.py: نگهبان MIN_PYTHON پیش از import PySide6؛ مسیر خطای راه‌اندازی اول QApplication را تضمین می‌کند بعد QMessageBox می‌سازد و خطا را با traceback لاگ می‌کند",
      "MIN_PYTHON = (3, 9)" in main_src
      and main_src.index("MIN_PYTHON") < main_src.index("from PySide6")
      and "QApplication.instance() is None" in except_block
      and except_block.index("QApplication.instance() is None") < except_block.index("QMessageBox()")
      and "exc_info=True" in except_block,
      "")

# --- A12: سازوکار باگ مسیر خطا (QWidget بدون QApplication برنامه را می‌کُشد) — اثبات با زیرفرایند
env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
crash = subprocess.run([sys.executable, "-c",
                        "from PySide6.QtWidgets import QMessageBox\nQMessageBox()\nprint('ALIVE')"],
                       capture_output=True, text=True, env=env, timeout=120)
alive = subprocess.run([sys.executable, "-c",
                        "import sys\nfrom PySide6.QtWidgets import QApplication, QMessageBox\n"
                        "app = QApplication.instance() or QApplication(sys.argv)\nQMessageBox()\nprint('ALIVE')"],
                       capture_output=True, text=True, env=env, timeout=120)
check("A", "اثبات سازوکار: QMessageBox بدون QApplication فرایند را می‌کُشد (پیام خطا هرگز دیده نمی‌شد)؛ با تضمین QApplication زنده می‌ماند",
      "ALIVE" not in crash.stdout and crash.returncode != 0
      and "ALIVE" in alive.stdout and alive.returncode == 0,
      f"crash rc={crash.returncode} alive rc={alive.returncode}")

# --- A13: تست‌های قدیمی: بدون makeSuite؛ unittest discover و اجرای مستقیم فایل‌ها سبز
tests_src = "".join(read(os.path.join("tests", f)) for f in os.listdir("tests") if f.endswith(".py"))
discover_run = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                              capture_output=True, text=True, env=env, timeout=600)
direct_runs = [subprocess.run([sys.executable, os.path.join("tests", f)],
                              capture_output=True, text=True, env=env, timeout=600)
               for f in ("test_dal.py", "test_services.py")]
check("A", "tests/: هیچ unittest.makeSuite (حذف‌شده در Python 3.13) نمانده؛ «unittest discover» و اجرای مستقیم فایل‌ها با TestLoader سبز است",
      "makeSuite" not in tests_src
      and discover_run.returncode == 0 and "OK" in discover_run.stderr
      and all(r.returncode == 0 and "OK" in r.stderr for r in direct_runs),
      f"discover rc={discover_run.returncode} direct={[r.returncode for r in direct_runs]}")

# --- A14: نسخهٔ پایتون صریح و یکدست
readme = read("README.md")
ruff_toml = read("ruff.toml")
check("A", "نسخهٔ پشتیبانی‌شدهٔ Python صریح و یکدست است: README (۳.۹ تا ۳.۱۳)، ruff target py39، نگهبان main.py",
      "3.9 تا 3.13" in readme and 'target-version = "py39"' in ruff_toml
      and "sys.version_info < MIN_PYTHON" in main_src,
      "")

# ============================================================
print()
print("=" * 76)
print("بخش B: Backup/Restore و file handling — حذف امن، نوشتن اتمیک، وضعیت واقعی، توقف واقعی")
print("=" * 76)

import hashlib  # noqa: E402
import time  # noqa: E402
import zipfile  # noqa: E402

# --- دیتابیس موقت برنامه (برای سناریوهای بازیابی واقعی)
TEST_DB = os.path.join(TMP, "partow.db")
import config.settings as settings  # noqa: E402
import database.connection as dbc  # noqa: E402

settings.DB_PATH = TEST_DB
dbc.DB_PATH = TEST_DB
dbc.DatabaseConnection._instance = None
with contextlib.redirect_stdout(io.StringIO()):
    db = dbc.DatabaseConnection()
    conn = db.get_connection(user_id=1)

import utils.backup as backup_mod  # noqa: E402
from utils.backup import BackupManager  # noqa: E402

for _h in list(backup_mod.logger.handlers):
    if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
        _h.setLevel(logging.CRITICAL)

ATT_DIR = os.path.join(TMP, "attachments")
BK_DIR = os.path.join(TMP, "backups")
os.makedirs(ATT_DIR, exist_ok=True)
with open(os.path.join(ATT_DIR, "keep_me.txt"), "w", encoding="utf-8") as fh:
    fh.write("attachment content")
bm = BackupManager(TEST_DB, ATT_DIR, BK_DIR)
for _h in list(bm.logger.handlers):
    if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
        _h.setLevel(logging.CRITICAL)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def _dir_files(d):
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


# --- B1: نام با پیمایش مسیر → فایل فقط داخل پوشهٔ پشتیبان
res_evil = bm.create_backup("../../evil_name", user_id=1, user_name="آزمون")
outside_candidates = [os.path.join(TMP, "evil_name.partobak"),
                      os.path.join(os.path.dirname(TMP), "evil_name.partobak")]
check("B", "نام پشتیبان امن‌سازی می‌شود: «../../evil_name» فقط evil_name.partobak داخل پوشهٔ پشتیبان می‌سازد و هیچ فایلی بیرون پوشه ساخته نمی‌شود",
      res_evil["success"] and res_evil["name"] == "evil_name"
      and os.path.realpath(res_evil["file"]) == os.path.join(os.path.realpath(BK_DIR), "evil_name.partobak")
      and not any(os.path.exists(c) for c in outside_candidates),
      str(res_evil.get("message"))[:100])

# --- B2: نوشتن اتمیک + checksum واقعاً SHA-256
res_ok = bm.create_backup("good_one", user_id=1, user_name="آزمون")
good_file = res_ok.get("file")
sidecar = good_file + ".sha256"
leftovers = [f for f in _dir_files(BK_DIR) if f.endswith((".tmp", ".db.tmp", "-wal", "-shm", "-journal"))]
check("B", "پشتیبان موفق: بدون فایل موقت باقی‌مانده (قبلاً کنار هر پشتیبان .db.tmp-wal/-shm جا می‌ماند)؛ فایل .sha256 کنار آن واقعاً SHA-256 همان فایل است (قبلاً MD5 با پسوند sha256)",
      res_ok["success"] and os.path.exists(good_file) and os.path.exists(sidecar)
      and not leftovers and res_ok.get("checksum_saved") is True
      and open(sidecar, encoding="utf-8").read().strip() == _sha256(good_file) == res_ok["checksum"]
      and len(res_ok["checksum"]) == 64,
      f"leftovers={leftovers}")

# --- B3: شکست وسط ساخت → هیچ .partobak نیمه‌کاره/موقت باقی نمی‌ماند
before_fail = _dir_files(BK_DIR)
real_count = BackupManager._count_attachments


def _boom(self):
    raise OSError("disk exploded during metadata")


BackupManager._count_attachments = _boom
try:
    res_fail = bm.create_backup("half_written", user_id=1, user_name="آزمون")
finally:
    BackupManager._count_attachments = real_count
after_fail = _dir_files(BK_DIR)
check("B", "شکست وسط ساخت پشتیبان: success=False با پیام، و هیچ فایل نیمه‌کاره (.partobak/.tmp/.db.tmp) در پوشه نمی‌ماند",
      res_fail["success"] is False and "disk exploded" in res_fail["message"]
      and after_fail == before_fail,
      f"diff={sorted(set(after_fail) ^ set(before_fail))}")

# --- B4: وضعیت واقعی فایل‌ها در فهرست
tampered = os.path.join(BK_DIR, "tampered.partobak")
shutil.copy2(good_file, tampered)
shutil.copy2(sidecar, tampered + ".sha256")
with open(tampered, "ab") as fh:
    fh.write(b"garbage appended after archive")
corrupt = os.path.join(BK_DIR, "corrupt.partobak")
with open(corrupt, "wb") as fh:
    fh.write(b"this is not a zip file at all")
nochk = os.path.join(BK_DIR, "nochecksum.partobak")
shutil.copy2(good_file, nochk)
statuses = {b["file"]: b["status"] for b in bm.list_backups()}
check("B", "list_backups وضعیت واقعی می‌دهد: سالم=ok، دستکاری‌شده=mismatch، غیر-ZIP=corrupt، بدون فایل کناری=no_checksum (قبلاً همه «✅ سالم»)",
      statuses.get("good_one.partobak") == "ok"
      and statuses.get("tampered.partobak") == "mismatch"
      and statuses.get("corrupt.partobak") == "corrupt"
      and statuses.get("nochecksum.partobak") == "no_checksum",
      str(statuses))

# --- B5: delete_backup — فقط داخل پوشه، فقط .partobak، بدون پیوند نمادین؛ sidecar هم حذف می‌شود
outside_file = os.path.join(TMP, "outside.partobak")
with open(outside_file, "wb") as fh:
    fh.write(b"x")
wrong_ext = os.path.join(BK_DIR, "notes.txt")
with open(wrong_ext, "w", encoding="utf-8") as fh:
    fh.write("x")
link_path = os.path.join(BK_DIR, "link.partobak")
link_ok = True
try:
    os.symlink(outside_file, link_path)
except (OSError, NotImplementedError):
    link_ok = False
r_out = bm.delete_backup(outside_file)
r_ext = bm.delete_backup(wrong_ext)
r_link = bm.delete_backup(link_path) if link_ok else (False, "symlink unsupported")
r_traversal = bm.delete_backup(os.path.join(BK_DIR, "..", "outside.partobak"))
r_dir = bm.delete_backup(BK_DIR)
r_good = bm.delete_backup(tampered, user_id=1, user_name="آزمون")
r_again = bm.delete_backup(tampered)
check("B", "delete_backup: مسیر بیرون پوشه، پیمایش «..»، پسوند غیر .partobak، پیوند نمادین و خود پوشه رد می‌شوند و چیزی حذف نمی‌شود؛ فایل معتبر با .sha256 کنارش حذف می‌شود؛ حذف دوباره «وجود ندارد»",
      r_out[0] is False and os.path.exists(outside_file)
      and r_ext[0] is False and os.path.exists(wrong_ext)
      and r_link[0] is False and os.path.exists(outside_file)
      and r_traversal[0] is False and os.path.exists(outside_file)
      and r_dir[0] is False and os.path.isdir(BK_DIR)
      and r_good[0] is True and not os.path.exists(tampered) and not os.path.exists(tampered + ".sha256")
      and r_again[0] is False and "وجود ندارد" in r_again[1],
      f"out={r_out[1][:40]} ext={r_ext[1][:40]} link={r_link[1][:40]} good={r_good[1][:40]} again={r_again[1][:40]}")
if link_ok and os.path.lexists(link_path):
    os.remove(link_path)

# --- B6: شکست حذف sidecar → نتیجهٔ صریح (نه موفقیت ظاهری)
victim = os.path.join(BK_DIR, "victim.partobak")
shutil.copy2(good_file, victim)
shutil.copy2(sidecar, victim + ".sha256")
real_remove = os.remove


def _remove_but_not_sidecar(path):
    if str(path).endswith("victim.partobak.sha256"):
        raise PermissionError("sidecar locked")
    return real_remove(path)


os.remove = _remove_but_not_sidecar
try:
    r_partial = bm.delete_backup(victim)
finally:
    os.remove = real_remove
check("B", "اگر حذف فایل .sha256 شکست بخورد: فایل اصلی حذف شده ولی نتیجه False با پیام صریح دربارهٔ sidecar است",
      r_partial[0] is False and "checksum" in r_partial[1] and "sidecar locked" in r_partial[1]
      and not os.path.exists(victim) and os.path.exists(victim + ".sha256"),
      str(r_partial))
os.remove(victim + ".sha256")

# --- B7: بازیابی واقعی با پیش/پس‌شرط روی دیتابیس و پیوست‌ها
from dal.student_dal import StudentDAL  # noqa: E402
from models.student import Student  # noqa: E402

student_dal = StudentDAL()


def _new_student(first, last, code):
    st = Student()
    st.first_name, st.last_name, st.national_code = first, last, code
    st.birth_date = "1395/01/01"
    st.gender = "male"
    return student_dal.create(st)


for i in range(3):
    _new_student("دانش‌آموز", f"شمارهٔ {i}", f"00000000{i}1")
count_before = conn.execute("SELECT COUNT(*) FROM students WHERE is_deleted = 0").fetchone()[0]
snap = bm.create_backup("snapshot_for_restore", user_id=1, user_name="آزمون")
# تغییر وضعیت پس از پشتیبان: یک دانش‌آموز جدید + حذف فایل پیوست
_new_student("بعد", "از پشتیبان", "0000000099")
os.remove(os.path.join(ATT_DIR, "keep_me.txt"))
count_changed = conn.execute("SELECT COUNT(*) FROM students WHERE is_deleted = 0").fetchone()[0]
with contextlib.redirect_stdout(io.StringIO()):
    res_restore = bm.restore_backup(snap["file"], user_id=1, user_name="آزمون")
    conn = db.get_connection(user_id=1)
count_after = conn.execute("SELECT COUNT(*) FROM students WHERE is_deleted = 0").fetchone()[0]
check("B", "بازیابی واقعی: تعداد دانش‌آموزان به مقدار زمان پشتیبان برمی‌گردد، پیوست حذف‌شده برمی‌گردد، پوشهٔ موقت و پوشهٔ ایمنی باقی نمی‌مانند",
      snap["success"] and count_changed == count_before + 1
      and res_restore["success"] and count_after == count_before
      and res_restore.get("attachments_restored") is True
      and os.path.exists(os.path.join(ATT_DIR, "keep_me.txt"))
      and not os.path.exists(os.path.join(BK_DIR, "temp_restore"))
      and not os.path.exists(ATT_DIR + ".restore_safety")
      and not os.path.exists(TEST_DB + ".restore_safety"),
      f"before={count_before} changed={count_changed} after={count_after} msg={str(res_restore.get('message'))[:80]}")

# --- B8: شکست بازیابی پیوست‌ها → دیتابیس بازیابی شده، پیوست‌های قبلی حفظ، نتیجهٔ صریح
_new_student("دوباره", "بعد از پشتیبان", "0000000098")
with open(os.path.join(ATT_DIR, "current_only.txt"), "w", encoding="utf-8") as fh:
    fh.write("exists only now")
real_copytree = shutil.copytree


def _copytree_fail(src, dst, *a, **k):
    raise OSError("copy interrupted")


shutil.copytree = _copytree_fail
try:
    with contextlib.redirect_stdout(io.StringIO()):
        res_partial = bm.restore_backup(snap["file"], user_id=1, user_name="آزمون")
        conn = db.get_connection(user_id=1)
finally:
    shutil.copytree = real_copytree
count_partial = conn.execute("SELECT COUNT(*) FROM students WHERE is_deleted = 0").fetchone()[0]
check("B", "اگر کپی پیوست‌ها شکست بخورد: دیتابیس بازیابی شده، پوشهٔ پیوست‌های قبلی دست‌نخورده برگشته (نه پاک‌شده)، نتیجه صریحاً attachments_restored=False با ⚠️، بدون پوشهٔ ایمنی/موقت",
      res_partial["success"] and count_partial == count_before
      and res_partial.get("attachments_restored") is False
      and "copy interrupted" in str(res_partial.get("attachments_error"))
      and res_partial["message"].startswith("⚠️")
      and os.path.exists(os.path.join(ATT_DIR, "current_only.txt"))
      and not os.path.exists(ATT_DIR + ".restore_safety")
      and not os.path.exists(os.path.join(BK_DIR, "temp_restore")),
      f"count={count_partial} msg={str(res_partial.get('message'))[:90]}")

# --- B9: انتقال پشتیبان‌های پوشهٔ قدیمی (views/backups) بدون بازنویسی
legacy_dir = os.path.join(TMP, "views", "backups")
os.makedirs(legacy_dir, exist_ok=True)
shutil.copy2(good_file, os.path.join(legacy_dir, "old_one.partobak"))
shutil.copy2(sidecar, os.path.join(legacy_dir, "old_one.partobak.sha256"))
shutil.copy2(good_file, os.path.join(legacy_dir, "good_one.partobak"))  # هم‌نام با موجود
with open(os.path.join(legacy_dir, "backup_log.txt"), "w", encoding="utf-8") as fh:
    fh.write("legacy log\n")
moved = bm.adopt_legacy_backups(legacy_dir)
merged_log = read(os.path.join(BK_DIR, "backup_log.txt"))
check("B", "پشتیبان‌های پوشهٔ قدیمی داخل درخت کد به پوشهٔ استاندارد منتقل می‌شوند (فایل، sidecar؛ لاگ قدیمی به لاگ فعلی افزوده می‌شود)؛ فایل هم‌نام موجود بازنویسی نمی‌شود",
      sorted(moved) == ["backup_log.txt", "old_one.partobak", "old_one.partobak.sha256"]
      and os.path.exists(os.path.join(BK_DIR, "old_one.partobak"))
      and not os.path.exists(os.path.join(legacy_dir, "backup_log.txt"))
      and "legacy log" in merged_log and "create" in merged_log
      and os.path.exists(os.path.join(legacy_dir, "good_one.partobak"))
      and _sha256(good_file) == _sha256(os.path.join(BK_DIR, "good_one.partobak")),
      str(moved))

# --- B10: زمان‌بند خودکار واقعاً متوقف می‌شود
auto_before = [f for f in _dir_files(BK_DIR) if f.startswith("auto_backup_")]
handle = bm.schedule_auto_backup(interval_hours=0.0003, user_id=None, user_name="سیستم")  # ≈۱٫۱ ثانیه
deadline = time.time() + 8
while time.time() < deadline and not [f for f in _dir_files(BK_DIR) if f.startswith("auto_backup_") and f.endswith(".partobak")]:
    time.sleep(0.2)
auto_created = [f for f in _dir_files(BK_DIR) if f.startswith("auto_backup_") and f.endswith(".partobak")]
stopped = handle.stop(timeout=10)
count_at_stop = len([f for f in _dir_files(BK_DIR) if f.startswith("auto_backup_") and f.endswith(".partobak")])
time.sleep(2.5)
count_later = len([f for f in _dir_files(BK_DIR) if f.startswith("auto_backup_") and f.endswith(".partobak")])
check("B", "پشتیبان‌گیری خودکار: پس از فاصلهٔ زمانی یک پشتیبان auto_backup_* ساخته می‌شود؛ stop() نخ را واقعاً تمام می‌کند و بعد از آن پشتیبان جدیدی ساخته نمی‌شود (قبلاً «توقف» فقط مرجع را None می‌کرد)",
      not auto_before and len(auto_created) >= 1 and stopped is True
      and not handle.is_running() and count_later == count_at_stop,
      f"created={auto_created} stopped={stopped} at_stop={count_at_stop} later={count_later}")

# --- B11: اتصال صفحه‌ها به پوشهٔ واحد، سیگنال کارگر، قفل هم‌زمانی، مخزن بدون فایل پشتیبان
page_src = read("views/pages/backup_page.py")
settings_page_src = read("views/pages/settings_page.py")
settings_src = read("config/settings.py")
gitignore = read(".gitignore")
tracked_backups = subprocess.run(["git", "ls-files", "*.partobak", "**/*.partobak"],
                                 capture_output=True, text=True).stdout.strip()
check("B", "هر دو صفحه از BACKUP_DIR واحد استفاده می‌کنند؛ کارگر سیگنال operation_finished دارد (نه بازتعریف finished)؛ هر ۴ عمل قفل هم‌زمانی دارند؛ جدول هنگام عملیات قفل می‌شود؛ backups/ در .gitignore و هیچ .partobak در مخزن نیست",
      "BACKUP_DIR = os.path.join(BASE_DIR, \"backups\")" in settings_src
      and "self.backup_dir = BACKUP_DIR" in page_src
      and "backup_dir = BACKUP_DIR" in settings_page_src
      and "operation_finished = Signal(bool, str)" in page_src
      and "finished = Signal(bool, str)\n" not in page_src.replace("operation_finished = Signal(bool, str)\n", "")
      and page_src.count("if self._operation_in_progress():") == 4
      and "self.table.setEnabled(enabled)" in page_src
      and "backups/" in gitignore and tracked_backups == "",
      f"tracked={tracked_backups!r}")

# --- B12: صفحهٔ پشتیبان‌گیری (offscreen): ایجاد و حذف از مسیر UI → کارگر → مدیر → فایل → تازه‌سازی جدول
gui_detail = ""
try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance() or QApplication(sys.argv)
    import views.pages.backup_page as backup_page_mod

    backup_page_mod.BACKUP_DIR = BK_DIR
    backup_page_mod.LEGACY_BACKUP_DIR = os.path.join(TMP, "no_legacy_here")
    shown = []
    QMessageBox.information = staticmethod(lambda *a, **k: shown.append(("info", a[2])))
    QMessageBox.critical = staticmethod(lambda *a, **k: shown.append(("crit", a[2])))
    QMessageBox.warning = staticmethod(lambda *a, **k: shown.append(("warn", a[2])))
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    with contextlib.redirect_stdout(io.StringIO()):
        page = backup_page_mod.BackupPage()

    def _wait_worker(p, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            app.processEvents()
            if p.worker is None or not p.worker.isRunning():
                app.processEvents()
                return True
            time.sleep(0.05)
        return False

    rows_before = page.table.rowCount()
    files_before = len([f for f in _dir_files(BK_DIR) if f.endswith(".partobak") and not f.startswith("pre_restore")])
    page.create_backup()
    finished_ok = _wait_worker(page)
    app.processEvents()
    rows_after_create = page.table.rowCount()
    files_after_create = len([f for f in _dir_files(BK_DIR) if f.endswith(".partobak") and not f.startswith("pre_restore")])
    # حذف از مسیر UI
    target = next(b for b in page.backup_manager.list_backups() if b["file"] == "nochecksum.partobak")
    page.delete_backup(target)
    finished_del = _wait_worker(page)
    app.processEvents()
    rows_after_delete = page.table.rowCount()
    gui_detail = (f"rows {rows_before}->{rows_after_create}->{rows_after_delete} files {files_before}->{files_after_create} "
                  f"shown={[k for k, _ in shown]} enabled={page.create_btn.isEnabled()}")
    check("B", "صفحهٔ پشتیبان‌گیری (offscreen): «ایجاد پشتیبان» → کارگر → فایل جدید روی دیسک → پیام موفقیت → جدول +۱؛ «حذف» ردیف → فایل حذف → جدول −۱؛ دکمه‌ها دوباره فعال",
          finished_ok and finished_del and rows_before == files_before
          and files_after_create == files_before + 1 and rows_after_create == rows_before + 1
          and rows_after_delete == rows_after_create - 1
          and not os.path.exists(os.path.join(BK_DIR, "nochecksum.partobak"))
          and shown and all(k == "info" for k, _ in shown)
          and page.create_btn.isEnabled() and page.table.isEnabled(),
          gui_detail)
except Exception as e:
    check("B", "صفحهٔ پشتیبان‌گیری (offscreen): زنجیرهٔ UI → کارگر → فایل → جدول", False,
          f"{type(e).__name__}: {e} {gui_detail}")

# ============================================================
print()
print("=" * 76)
print(f"نتیجهٔ دور شانزدهم (مرحله‌های ۱ و ۲):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
if FAILURES:
    print("موارد ناموفق:")
    for f in FAILURES:
        print("   -", f)
print("=" * 76)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
