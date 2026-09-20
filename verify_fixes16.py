"""
بررسی‌های دور شانزدهم — عیب‌یابی فنی کامل (مأموریت ۳۸ بندی)

هر بخش، آزمون «کارکردی با پیش/پس‌شرط» است: نه فقط «استثنا نداد»، بلکه وضعیت
دیتابیس/فایل قبل و بعد از عمل مقایسه می‌شود.

مرحلهٔ ۱ — Migration، تست‌های قدیمی، نسخهٔ پایتون (بندهای ۴، ۵، ۶، ۱۵، ۲۲-migration):
  A) کشف پویا از فایل‌سیستم، شکست بلند بارگذاری، ترتیب Downgrade، تراکنش هر گام،
     logging با traceback، مسیر خطای main.py، makeSuite، نسخهٔ پایتون ........ ۱۵ بررسی

جمع فعلی: ۱۵ بررسی
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
print(f"نتیجهٔ دور شانزدهم (مرحلهٔ ۱):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
if FAILURES:
    print("موارد ناموفق:")
    for f in FAILURES:
        print("   -", f)
print("=" * 76)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
