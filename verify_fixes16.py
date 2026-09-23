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

مرحلهٔ ۳-الف — Inventory صفحات (بندهای ۲، ۳، ۱۰، ۱۸، ۱۹، ۳۶ برای views/pages + main_window):
  C) اجرای واقعی handlerهای همهٔ صفحه‌ها و پنجرهٔ اصلی (offscreen)، چهار زنجیرهٔ تزئینی
     تکمیل‌شده با پیش/پس‌شرط، Inventory ایستا، کنتراست کل views/، ممیزی سیگنال‌ها ... ۹ بررسی

مرحلهٔ ۳-ب — دیالوگ‌ها و ویجت‌ها (بندهای ۲، ۳، ۱۴، ۱۸، ۱۹، ۳۶ برای views/dialogs + views/widgets):
  D) ۸ فرم ثبت/ویرایش با پیش/پس‌شرط DB، درخت شایستگی، ورود، تغییر رمز، جست‌وجوی پیشرفته،
     خروجی AI در ۶ قالب، زنگولهٔ اعلان، اعتبارسنجی مشاهده، کد بدون مصرف‌کننده ......... ۱۶ بررسی

مرحلهٔ ۴ — پیوست‌ها، نخ‌ها/کارگرها، Race، وضعیت Screening/Recommendation (بندهای ۷، ۸، ۲۰، ۲۱، ۳۲):
  E) زنجیرهٔ کامل پیوست (صف آپلود، یکتایی نام فایل، رد نوع غیرمجاز، پاکسازی در شکست DB،
     جست‌وجو/پیش‌نمایش/دانلود/حذف، Race و بستن امن)، نگهبان ثبت دوباره در ۸ فرم، بهداشت نخ‌ها ... ۱۲ بررسی

مرحلهٔ ۵ — تراکنش/ایمپورت/نتیجه/استثنا/SQL/Constraints/خروجی/سازگاری (بندهای ۱۶، ۱۷، ۲۲، ۲۳، ۲۴، ۲۶، ۳۰، ۳۱):
  F) اتمیک‌بودن واقعی تراکنش سرویس، ایمپورت اکسل (نمونهٔ برنامه + سناریوهای خراب)، قرارداد نتیجهٔ حذف،
     اسکن except بی‌صدا، اسکن SQL، Constraints، خروجی‌های واقعی صفحه‌ها، سازگاری جدول/DB ......... ۹ بررسی

مرحلهٔ ۶ — کد مرده، وابستگی‌ها، لایهٔ سرویس (بندهای ۲۷، ۲۸، ۲۹):
  G) حذف کد مردهٔ تأییدشده بدون ارجاع باقی‌مانده، جهت وابستگی لایه‌ها، سیگنال‌های هرگز-emit-نشده،
     سرویس‌های wrapper ...................................................................... ۴ بررسی

تکمیلی — تصمیم‌های باز (BUG-023 و BUG-027):
  H) کامبوی سال تحصیلی هدر (فعال‌سازی با تأیید، برگشت، بایگانی) و نقطهٔ ورودی پیوست‌ها ... ۲ بررسی

تکمیلی — باقی‌مانده‌ها:
  I) تب پیشنهادها، خروجی گزارش کلاس/معلم/عملکرد، ویرایش اختصاص معلم، CHECK دیتابیس تازه،
     مخزن بدون دیتابیس واقعی، خروج خودکار بدون تأیید .................................. ۶ بررسی

داوری سوم مدیر پروژه — مرحلهٔ ۱:
  J) رد/تکمیل پیشنهاد با QInputDialog (BUG-NEW-01)، کنتراست «اقدام پیشنهادی» و نشان‌های داشبورد (BUG-NEW-03) ... ۲ بررسی

داوری سوم — مرحلهٔ ۲:
  K) Migrationهای واقعاً اتمیک: بدون commit داخلی، فایل واقعی با شکست وسط کار، زنجیرهٔ واقعی ۵→۹ و ۹→۸→۹،
     مسیر ترمیم با تراکنش صریح (BUG-NEW-02) ...................................................... ۴ بررسی

داوری سوم — مرحلهٔ ۳:
  L) ثبت مداخله از روی پیشنهاد: پیش‌پرکردن نوع/شرح/هدف، پیوند پیشنهاد ↔ مداخله، شکست پیوند صریح (BUG-NEW-04) ... ۲ بررسی

جمع: ۹۳ بررسی
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
check("B", "اگر کپی پیوست‌ها شکست بخورد: دیتابیس بازیابی شده، پوشهٔ پیوست‌های قبلی دست‌نخورده برگشته (نه پاک‌شده)، نتیجه صریحاً attachments_restored=False با ⚠️، نام پشتیبان pre_restore در پیام، بدون فایل/پوشهٔ ایمنی و موقت",
      res_partial["success"] and count_partial == count_before
      and res_partial.get("attachments_restored") is False
      and "copy interrupted" in str(res_partial.get("attachments_error"))
      and res_partial["message"].startswith("⚠️")
      and os.path.basename(str(res_partial.get("pre_restore_file") or "?")) in res_partial["message"]
      and os.path.exists(os.path.join(ATT_DIR, "current_only.txt"))
      and not os.path.exists(ATT_DIR + ".restore_safety")
      and not os.path.exists(TEST_DB + ".restore_safety")
      and not os.path.exists(os.path.join(BK_DIR, "temp_restore")),
      f"count={count_partial} msg={str(res_partial.get('message'))[:90]} "
      f"safety={os.path.exists(TEST_DB + '.restore_safety')}")

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
print("بخش C: Inventory صفحات — اجرای واقعی handlerها، زنجیره‌های تکمیل‌شده، کنتراست، سیگنال‌ها")
print("=" * 76)

import importlib  # noqa: E402
import inspect  # noqa: E402

from tools import ui_inventory as inv  # noqa: E402

from PySide6.QtCore import QSettings, Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QListWidget,
    QMessageBox,
    QTableWidget,
    QTreeWidget,
    QWidget,
)

app = QApplication.instance() or QApplication(sys.argv)
QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, os.path.join(TMP, "qsettings"))
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, os.path.join(TMP, "qsettings"))

# دادهٔ آزمایشی برای صفحه‌ها (دانش‌آموز در سال فعال با مشاهده/مداخله/پیگیری)
from dal.academic_year_dal import AcademicYearDAL  # noqa: E402
from dal.class_dal import ClassDAL  # noqa: E402
from dal.competency_dal import CompetencyDAL  # noqa: E402
from dal.followup_dal import FollowUpDAL  # noqa: E402
from dal.intervention_dal import InterventionDAL  # noqa: E402
from dal.observation_dal import ObservationDAL  # noqa: E402
from dal.student_academic_profile_dal import StudentAcademicProfileDAL  # noqa: E402
from models.class_model import ClassModel  # noqa: E402
from models.followup import FollowUp  # noqa: E402
from models.intervention import Intervention  # noqa: E402
from models.observation import Observation  # noqa: E402
from models.student_academic_profile import StudentAcademicProfile  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    conn = db.get_connection(user_id=1)
    smoke_student = _new_student("اسموک", "صفحه‌ها", "1616161616")
    active_year = AcademicYearDAL().get_active()
    prof = StudentAcademicProfile()
    prof.student_id, prof.academic_year_id, prof.grade, prof.class_name = smoke_student.id, active_year.id, 2, "الف"
    smoke_pid = StudentAcademicProfileDAL().create(prof).id
    comps = CompetencyDAL().get_all()
    obs_ids = []
    for i, (bt, d) in enumerate([("منفی", "1405/07/05"), ("منفی", "1405/07/15"), ("مثبت", "1405/08/05"),
                                 ("مثبت", "1405/08/20"), ("خنثی", "1405/09/01")]):
        o = Observation()
        o.student_profile_id, o.staff_id, o.competency_id = smoke_pid, 1, comps[i % 3].id
        o.observation_date, o.description, o.behavior, o.behavior_type, o.severity = d, "شرح", "رفتار", bt, 2
        obs_ids.append(ObservationDAL().create(o).id)
    it = Intervention()
    it.student_profile_id, it.staff_id, it.observation_id, it.type = smoke_pid, 1, obs_ids[0], "individual_talk"
    it.date, it.description, it.goal, it.status = "1405/07/20", "شرح", "هدف", "done"
    smoke_iid = InterventionDAL().create(it).id
    fu = FollowUp()
    fu.intervention_id, fu.staff_id, fu.date, fu.method, fu.status = smoke_iid, 1, "1405/08/01", "گفتگو", "pending"
    fu.result_type, fu.result_description, fu.description = "improved", "ن", "پ"
    FollowUpDAL().create(fu)
    cls_obj = ClassModel()
    cls_obj.name, cls_obj.grade, cls_obj.academic_year_id, cls_obj.capacity, cls_obj.is_active = "آزمون‌ویرایش", 2, active_year.id, 25, 1
    smoke_class_id = ClassDAL().create(cls_obj).id

# دیالوگ‌ها و پیام‌ها بدون تعامل کاربر
ui_msgs = []
QMessageBox.information = staticmethod(lambda *a, **k: ui_msgs.append(("info", str(a[2])[:100])) or QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: ui_msgs.append(("warn", str(a[2])[:100])) or QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: ui_msgs.append(("crit", str(a[2])[:160])) or QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
QMessageBox.about = staticmethod(lambda *a, **k: None)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected
QDialog.exec_ = QDialog.exec
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ""))
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: "")
QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", False))
QInputDialog.getInt = staticmethod(lambda *a, **k: (0, False))

SMOKE_SKIP = {'create_backup', 'restore_from_file', 'logout', 'start_auto_backup', 'stop_auto_backup',
              'close', 'auto_logout'}
PAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "views", "pages")


def _select_first_rows(page):
    for val in list(vars(page).values()):
        try:
            if isinstance(val, QTableWidget) and val.rowCount() > 0:
                val.selectRow(0)
                val.setCurrentCell(0, 0)
            elif isinstance(val, QListWidget) and val.count() > 0:
                val.setCurrentRow(0)
            elif isinstance(val, QTreeWidget) and val.topLevelItemCount() > 0:
                val.setCurrentItem(val.topLevelItem(0))
        except Exception:
            pass


def _pick_argument(page, name, pname, model_lists):
    if inv.LOAD_METHOD_RE.match(name) or name.startswith(('display_', 'render_', 'populate_', 'fill_', 'set_',
                                                          'build_', 'draw_', 'format_')):
        return None
    if pname in ('index', 'checked', 'text', 'value', 'state', 'event', 'pos', 'position', 'data', 'idx'):
        return None
    if pname == 'item':
        for val in vars(page).values():
            if isinstance(val, QTableWidget) and val.rowCount() > 0 and val.item(0, 0) is not None:
                return val.item(0, 0)
            if isinstance(val, QListWidget) and val.count() > 0:
                return val.item(0)
        return None
    stem = pname.rstrip('s').lower()
    for attr, lst in model_lists.items():
        tname = type(lst[0]).__name__.lower()
        if stem and (stem in tname or tname in stem or stem in attr.lower()):
            return lst[0]
    for lst in model_lists.values():
        if type(lst[0]).__name__.lower()[:5] in name.lower():
            return lst[0]
    return None


def smoke_pages():
    """هر صفحه ساخته می‌شود و هر handler متصل (بدون آرگومان، یا با شیء ردیف/آیتم) اجرا می‌شود."""
    summary = {'classes': 0, 'handlers': 0, 'problems': []}
    for fname in sorted(os.listdir(PAGES_DIR)):
        if not fname.endswith('.py') or fname == '__init__.py':
            continue
        modname = 'views.pages.' + fname[:-3]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                mod = importlib.import_module(modname)
        except Exception as e:
            summary['problems'].append((fname, 'IMPORT', f"{type(e).__name__}: {e}"))
            continue
        for cinfo in inv.analyze_file(os.path.join(PAGES_DIR, fname)):
            cls = getattr(mod, cinfo.name, None)
            if cls is None or not inspect.isclass(cls) or not issubclass(cls, QWidget) or cls.__name__.endswith('Worker'):
                continue
            summary['classes'] += 1
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    page = cls()
            except Exception as e:
                summary['problems'].append((f"{fname}:{cinfo.name}", 'INIT', f"{type(e).__name__}: {e}"))
                continue
            _select_first_rows(page)
            model_lists = {a: v for a, v in vars(page).items()
                           if isinstance(v, list) and v and hasattr(v[0], '__dict__') and not hasattr(v[0], 'metaObject')}
            targets = set()
            for b in cinfo.buttons:
                t = b['connected_to']
                if t and t.startswith('self.'):
                    targets.add(t[5:].split('(')[0])
            for c in cinfo.connects:
                if c['target'].startswith('self.'):
                    targets.add(c['target'][5:].split('(')[0])
            targets.update(n for n in cinfo.methods if inv.LOAD_METHOD_RE.match(n))
            for name in sorted(targets):
                if name in SMOKE_SKIP:
                    continue
                fn = getattr(page, name, None)
                if not callable(fn):
                    continue
                try:
                    required = [p for p in inspect.signature(fn).parameters.values()
                                if p.default is inspect._empty and p.kind == p.POSITIONAL_OR_KEYWORD]
                except (TypeError, ValueError):
                    continue
                args = []
                if required:
                    if len(required) != 1:
                        continue
                    arg = _pick_argument(page, name, required[0].name, model_lists)
                    if arg is None:
                        continue
                    args = [arg]
                before = len(ui_msgs)
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        fn(*args)
                        app.processEvents()
                    summary['handlers'] += 1
                    crit = [m for m in ui_msgs[before:] if m[0] == 'crit']
                    if crit:
                        summary['problems'].append((f"{fname}:{cinfo.name}", name, f"CRIT_MSG: {crit[0][1]}"))
                except Exception as e:
                    summary['handlers'] += 1
                    summary['problems'].append((f"{fname}:{cinfo.name}", name, f"{type(e).__name__}: {e}"))
            page.deleteLater()
            app.processEvents()
    return summary


smoke = smoke_pages()
check("C", "همهٔ کلاس‌های صفحه (views/pages) ساخته می‌شوند و همهٔ handlerهای متصل (بدون آرگومان، با ردیف انتخاب‌شده، یا با شیء ردیف/آیتم) بدون استثنا و بدون پیام «خطا» اجرا می‌شوند",
      smoke['classes'] >= 20 and smoke['handlers'] >= 140 and not smoke['problems'],
      f"classes={smoke['classes']} handlers={smoke['handlers']} problems={smoke['problems'][:5]}")

# --- پنجرهٔ اصلی با ورود شبیه‌سازی‌شده
import views.dialogs.login_dialog as login_dialog_mod  # noqa: E402


def _fake_login_exec(self, *a, **k):
    self.login_successful.emit(1, 'admin', 'admin')
    return QDialog.DialogCode.Accepted


login_dialog_mod.LoginDialog.exec = _fake_login_exec
import views.main_window as main_window_mod  # noqa: E402

main_problems = []
try:
    with contextlib.redirect_stdout(io.StringIO()):
        win = main_window_mod.MainWindow()
    pages_count = win.stacked_widget.count()
    for i in range(pages_count):
        win.stacked_widget.setCurrentIndex(i)
        app.processEvents()
    with contextlib.redirect_stdout(io.StringIO()):
        win.load_academic_years()
        win.update_notification_badge()
        win.toggle_notifications()
        win.toggle_notifications()
        win.open_student_profile(smoke_student.id)
    profile_ok = win.stacked_widget.currentWidget() is win.students_page and \
        win.students_page.profile_page.student_id == smoke_student.id
except Exception as e:
    main_problems.append(f"{type(e).__name__}: {e}")
    pages_count, profile_ok = 0, False
check("C", "پنجرهٔ اصلی با ورود شبیه‌سازی‌شده ساخته می‌شود؛ ناوبری به همهٔ صفحه‌ها، اعلان‌ها و بازکردن پروندهٔ دانش‌آموز بدون استثنا",
      not main_problems and pages_count >= 14 and profile_ok,
      f"pages={pages_count} profile_ok={profile_ok} problems={main_problems}")

# --- «گزارش پرونده» در پروندهٔ دانش‌آموز → صفحهٔ گزارش‌ها با همان دانش‌آموز
with contextlib.redirect_stdout(io.StringIO()):
    win.students_page.profile_page.generate_report()
    app.processEvents()
check("C", "دکمهٔ «📄 گزارش پرونده»: صفحهٔ گزارش‌ها باز و همان دانش‌آموز در کامبو انتخاب و گزارشش بارگذاری می‌شود (قبلاً فقط پیام «به بخش گزارش‌ها بروید»)",
      win.stacked_widget.currentWidget() is win.reports_page
      and win.reports_page.student_combo.currentData() == smoke_student.id
      and getattr(win.reports_page, 'current_report', None) is not None,
      f"current={type(win.stacked_widget.currentWidget()).__name__} combo={win.reports_page.student_combo.currentData()}")

# --- دابل‌کلیک در داشبورد تحلیلی → سیگنال با شناسهٔ دانش‌آموز → پروندهٔ همان دانش‌آموز
analytics = win.dashboard_page.analytics_dashboard_page
from PySide6.QtWidgets import QTableWidgetItem  # noqa: E402

analytics.students_table.setRowCount(1)
probe_item = QTableWidgetItem("دانش‌آموز آزمایشی")
probe_item.setData(Qt.ItemDataRole.UserRole, smoke_student.id)
analytics.students_table.setItem(0, 0, probe_item)
received = []
analytics.student_selected.connect(lambda sid: received.append(sid))
with contextlib.redirect_stdout(io.StringIO()):
    win.stacked_widget.setCurrentIndex(0)
    analytics.on_student_double_clicked(probe_item)
    app.processEvents()
check("C", "دابل‌کلیک روی دانش‌آموزِ «بدون مشاهده» در داشبورد تحلیلی: سیگنال student_selected با شناسه → پنجرهٔ اصلی پروندهٔ همان دانش‌آموز را باز می‌کند (قبلاً پیام «در نسخهٔ بعدی»)",
      received == [smoke_student.id]
      and win.stacked_widget.currentWidget() is win.students_page
      and win.students_page.profile_page.student_id == smoke_student.id,
      f"received={received}")

# --- اطلاعات مدرسه: ذخیرهٔ واقعی و بازخوانی در نمونهٔ جدید
settings_page = win.settings_page if hasattr(win, 'settings_page') else None
if settings_page is None:
    import views.pages.settings_page as settings_page_mod
    with contextlib.redirect_stdout(io.StringIO()):
        settings_page = settings_page_mod.SettingsPage()
settings_page.school_name.setText("دبستان آزمون")
settings_page.school_code.setText("98765")
settings_page.school_address.setText("خیابان آزمون")
settings_page.school_phone.setText("021-0000000")
settings_page.school_principal.setText("مدیر آزمون")
n_before = len(ui_msgs)
settings_page.save_school_info()
saved_msgs = ui_msgs[n_before:]
import views.pages.settings_page as settings_page_mod  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    fresh_settings = settings_page_mod.SettingsPage()
check("C", "«💾 ذخیره اطلاعات» مدرسه: مقادیر واقعاً ذخیره می‌شوند و در نمونهٔ تازهٔ صفحه بازخوانی می‌شوند (قبلاً فقط پیام موفقیت + دادهٔ ساختگی «مدرسه نمونه»)",
      saved_msgs and saved_msgs[-1][0] == "info"
      and fresh_settings.school_name.text() == "دبستان آزمون"
      and fresh_settings.school_code.text() == "98765"
      and fresh_settings.school_principal.text() == "مدیر آزمون"
      and "مدرسه نمونه" not in read("views/pages/settings_page.py"),
      f"msgs={saved_msgs} name={fresh_settings.school_name.text()!r}")

# --- ویرایش کلاس (هر دو صفحه): فرم پر می‌شود، ذخیره → دیتابیس تغییر می‌کند، فرم به حالت افزودن برمی‌گردد
class_dal = ClassDAL()


def _edit_class_roundtrip(page, new_name):
    target = class_dal.get_by_id(smoke_class_id)
    page.edit_class(target)
    filled = (page.class_name_input.text() == target.name and page._editing_class_id == smoke_class_id
              and page.cancel_edit_class_btn.isVisible() or not page.isVisible())
    page.class_name_input.setText(new_name)
    page.class_capacity_spin.setValue(31)
    before = len(ui_msgs)
    with contextlib.redirect_stdout(io.StringIO()):
        page.add_class()
    msgs_after = ui_msgs[before:]
    saved = class_dal.get_by_id(smoke_class_id)
    return (filled and saved is not None and saved.name == new_name and saved.capacity == 31
            and page._editing_class_id is None and page.add_class_btn.text().startswith("➕")
            and msgs_after and msgs_after[-1][0] == "info"), (saved.name if saved else None, msgs_after)


ok_settings, det_settings = _edit_class_roundtrip(fresh_settings, "ویرایش‌شده‌۱")
import views.pages.academic_structure_page as acad_mod  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    acad_page = acad_mod.AcademicStructurePage()
ok_acad, det_acad = _edit_class_roundtrip(acad_page, "ویرایش‌شده‌۲")
check("C", "دکمهٔ «✏️» ویرایش کلاس در تنظیمات و ساختار آموزشی: فرم با مقادیر کلاس پر می‌شود، ذخیره → ردیف classes در دیتابیس تغییر می‌کند و فرم به حالت افزودن برمی‌گردد (قبلاً پیام «در نسخهٔ بعدی»)",
      ok_settings and ok_acad and "نسخه بعدی" not in read("views/pages/settings_page.py")
      and "نسخه بعدی" not in read("views/pages/academic_structure_page.py")
      and "نسخه بعدی" not in read("views/pages/analytics_dashboard.py"),
      f"settings={det_settings} academic={det_acad}")

# --- Inventory ایستا: بدون دکمهٔ بی‌اتصال/stub؛ دکمه‌های تزئینی قبلی دیگر MSG_ONLY نیستند
with contextlib.redirect_stdout(io.StringIO()):
    inventory = inv.build_report(write=False)
flagged_kinds = {(f[0], f[2]): f[5] for f in inventory['flagged']}
decorative_before = {("views/pages/settings_page.py", "save_btn"),
                     ("views/pages/settings_page.py", "edit_btn"),
                     ("views/pages/academic_structure_page.py", "edit_btn"),
                     ("views/pages/student_profile_page.py", "self.btn_report")}
check("C", "Inventory ایستا (tools/ui_inventory.py): هیچ دکمه‌ای بدون اتصال یا با handler خالی نیست؛ چهار دکمهٔ تزئینی قبلی (ذخیرهٔ اطلاعات مدرسه، ✏️ کلاس ×۲، گزارش پرونده) دیگر «فقط پیام» نیستند",
      inventory['totals'].get('NO_CONNECT', 0) == 0 and inventory['totals'].get('STUB', 0) == 0
      and not any(k.startswith('MISSING') for k in inventory['totals'])
      and not (decorative_before & set(flagged_kinds)),
      f"totals={inventory['totals']} still_flagged={sorted(decorative_before & set(flagged_kinds))}")


# --- کنتراست رنگ در کل views/
def _lum(hexv):
    h = hexv.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]

    def f(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


low_contrast = []
for sub in ('views', 'views/pages', 'views/dialogs', 'views/widgets'):
    for fname in sorted(os.listdir(sub)):
        if not fname.endswith('.py'):
            continue
        src = read(os.path.join(sub, fname))
        blocks = [m.group(1) for m in re.finditer(r'\{([^{}]*)\}', src)]
        blocks += [m.group(2) for m in re.finditer(r'setStyleSheet\(\s*(["\'])([^"\'{}]*?)\1\s*\)', src)]
        # (تکمیلی) استایل‌های چندخطی بدون selector — «color/background-color» مستقیم داخل رشته
        for m in re.finditer(r'setStyleSheet\(\s*(f?)("""|\'\'\')(.*?)\2\s*\)', src, re.S):
            body = re.sub(r'\{[^{}]*\}', '', m.group(3)) if m.group(1) else m.group(3)
            if '{' not in body:
                blocks.append(body)
        for body in blocks:
            fg = re.search(r'(?<![\w-])color\s*:\s*(#[0-9a-fA-F]{6})\b', body)
            bg = re.search(r'background(?:-color)?\s*:\s*(#[0-9a-fA-F]{6})\b', body)
            if fg and bg and _contrast(fg.group(1), bg.group(1)) < 3.0:
                low_contrast.append((os.path.join(sub, fname), fg.group(1), bg.group(1)))
rec_src = read("views/widgets/recommendation_widget.py")
rec_btn_block = rec_src.split("self.generate_btn.setStyleSheet(")[1].split(")")[0]
check("C", "کنتراست: در کل views/ هیچ بلوک استایلی (با selector یا بدون آن) با نسبت کنتراست متن/زمینه کمتر از ۳:۱ نمانده (قبلاً ۱۰۴ + ۵ مورد، از جمله متن هم‌رنگ زمینه در دکمهٔ Generate، «اقدام پیشنهادی»، نشان‌های داشبورد و برچسب‌های «داده ناکافی»)",
      not low_contrast and "color: #0B2E4F;" not in rec_btn_block.split("background-color: #0B2E4F;")[1].split("}")[0],
      f"remaining={low_contrast[:5]}")

# --- سیگنال‌های سفارشی بدون گیرنده: فقط فهرست شناخته‌شده (گزارش‌شده در سند)
KNOWN_RECEIVERLESS = {
    ('views/dialogs/assign_teacher_dialog.py', 'assignment_saved'),
    ('views/dialogs/attachment_dialog.py', 'attachment_added'),
    ('views/dialogs/attachment_dialog.py', 'attachment_deleted'),
    ('views/dialogs/change_password_dialog.py', 'password_changed'),
    ('views/main_window.py', 'academic_year_changed'),
    ('views/widgets/competency_tree_widget.py', 'behavior_selected'),
    ('views/widgets/competency_tree_widget.py', 'competency_selected'),
    ('views/widgets/competency_tree_widget.py', 'indicator_selected'),
    ('views/widgets/help_widget.py', 'help_requested'),
    ('views/widgets/recommendation_widget.py', 'intervention_requested'),
    ('views/widgets/recommendation_widget.py', 'recommendation_updated'),
}
receiverless = {(r, sig) for r, c, sig, ln, e, recv in inventory['signals'] if not recv}
new_receiverless = receiverless - KNOWN_RECEIVERLESS
newly_wired = {('views/pages/student_profile_page.py', 'report_requested'),
               ('views/pages/analytics_dashboard.py', 'student_selected')}
check("C", "ممیزی Signal/Slot: سیگنال‌های جدید (report_requested، student_selected داشبورد تحلیلی) گیرنده دارند؛ سیگنال‌های بدون گیرنده فقط همان فهرست مستندشده‌اند (نه مورد تازه)",
      not new_receiverless and not (newly_wired & receiverless),
      f"new_receiverless={sorted(new_receiverless)}")

# ============================================================
print()
print("=" * 76)
print("بخش D: دیالوگ‌ها و ویجت‌ها — ثبت/ویرایش واقعی با پیش/پس‌شرط دیتابیس، ورود، جست‌وجو، خروجی AI")
print("=" * 76)

import csv  # noqa: E402
import json  # noqa: E402
import zipfile  # noqa: E402

from dal.staff_dal import StaffDAL  # noqa: E402
from dal.user_dal import UserDAL  # noqa: E402
from models.staff import Staff  # noqa: E402

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
with contextlib.redirect_stdout(io.StringIO()):
    _t = Staff()
    _t.full_name, _t.role = "معلم آزمون", "teacher"
    teacher_id = StaffDAL().create(_t).id
    _c = Staff()
    _c.full_name, _c.role = "مشاور آزمون", "counselor"
    counselor_id = StaffDAL().create(_c).id
form_student = smoke_student
form_pid = smoke_pid


def _count(table):
    return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE is_deleted = 0").fetchone()[0]


def _last_id(table):
    return conn.execute(f"SELECT MAX(id) FROM {table}").fetchone()[0]


def _combo_pick(combo, data=None):
    if data is not None:
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)
            return data
    for i in range(combo.count()):
        if combo.itemData(i) not in (None, 0, ''):
            combo.setCurrentIndex(i)
            return combo.itemData(i)
    return None


def _form_roundtrip(label, table, text_col, make_form, fill, save_name, edit_form, edit_widget, signal_name, expected_fk=None):
    """ایجاد → شمارش +۱ و مقدار ستون؛ ویرایش → بارگذاری مقدار قبلی و ذخیرهٔ مقدار جدید در DB"""
    detail = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            form = make_form()
            fill(form)
            emitted = []
            getattr(form, signal_name).connect(lambda *a: emitted.append(1))
            before = _count(table)
            n_msgs = len(ui_msgs)
            getattr(form, save_name)()
            after = _count(table)
        new_id = _last_id(table)
        row = conn.execute(f"SELECT {text_col}{', ' + expected_fk[0] if expected_fk else ''} FROM {table} WHERE id = ?", (new_id,)).fetchone()
        detail.update(before=before, after=after, row=tuple(row) if row else None,
                      msgs=[m for m in ui_msgs[n_msgs:] if m[0] != 'info'])
        created_ok = (after == before + 1 and emitted and form.result() == QDialog.DialogCode.Accepted
                      and row is not None and row[0] == f"{label} اولیه"
                      and (expected_fk is None or row[1] == expected_fk[1]))
        with contextlib.redirect_stdout(io.StringIO()):
            form2 = edit_form(new_id)
            widget = getattr(form2, edit_widget)
            loaded = widget.text() if hasattr(widget, 'text') and not hasattr(widget, 'toPlainText') else widget.toPlainText()
            if hasattr(widget, 'toPlainText'):
                widget.setPlainText(f"{label} ویرایش‌شده")
            else:
                widget.setText(f"{label} ویرایش‌شده")
            n_msgs2 = len(ui_msgs)
            getattr(form2, save_name)()
        now = conn.execute(f"SELECT {text_col} FROM {table} WHERE id = ?", (new_id,)).fetchone()[0]
        detail.update(loaded=loaded, now=now, edit_msgs=[m for m in ui_msgs[n_msgs2:] if m[0] != 'info'])
        edited_ok = loaded == f"{label} اولیه" and now == f"{label} ویرایش‌شده" and form2.result() == QDialog.DialogCode.Accepted
        return bool(created_ok and edited_ok), detail
    except Exception as e:
        detail['exception'] = f"{type(e).__name__}: {e}"
        return False, detail


from views.dialogs.activity_form import ActivityForm  # noqa: E402
from views.dialogs.counseling_session_form import CounselingSessionForm  # noqa: E402
from views.dialogs.followup_form import FollowUpForm  # noqa: E402
from views.dialogs.goal_form import GoalForm  # noqa: E402
from views.dialogs.intervention_form import InterventionForm  # noqa: E402
from views.dialogs.observation_form import ObservationForm  # noqa: E402
from views.dialogs.student_form import StudentForm  # noqa: E402

# --- D1: مشاهده (بدون «توضیحات تکمیلی» اختیاری — قبلاً با خطای «توضیحات باید حداقل ۳ کاراکتر» شکست می‌خورد)


def _fill_obs(f):
    _combo_pick(f.student_combo, form_student.id)
    _combo_pick(f.observer_combo)
    f.behavior_input.setPlainText("مشاهده اولیه")
    f.selected_competency_id = comps[1].id


ok, det = _form_roundtrip("مشاهده", "observations", "behavior", lambda: ObservationForm(student_id=form_student.id),
                          _fill_obs, "save_observation", lambda i: ObservationForm(observation_id=i),
                          "behavior_input", "observation_saved", ("student_profile_id", form_pid))
obs_desc = conn.execute("SELECT description FROM observations WHERE id = ?", (_last_id("observations"),)).fetchone()[0]
check("D", "ObservationForm: ثبت با فیلدهای الزامیِ نمایان (بدون «توضیحات تکمیلی») → ردیف جدید با پروندهٔ درست؛ ویرایش → مقدار جدید در DB؛ ستون description (NOT NULL) خالی نمی‌ماند",
      ok and obs_desc in ("مشاهده اولیه", "مشاهده ویرایش‌شده"), f"{det} desc={obs_desc!r}")


# --- D2: مداخله
def _fill_int(f):
    _combo_pick(f.student_combo, form_student.id)
    _combo_pick(f.observer_combo)
    f.description_input.setPlainText("مداخله اولیه")
    f.goal_input.setPlainText("هدف")


ok, det = _form_roundtrip("مداخله", "interventions", "description", lambda: InterventionForm(student_id=form_student.id),
                          _fill_int, "save_intervention", lambda i: InterventionForm(intervention_id=i),
                          "description_input", "intervention_saved", ("student_profile_id", form_pid))
check("D", "InterventionForm: ثبت → ردیف جدید با پروندهٔ درست؛ ویرایش → مقدار جدید در DB", ok, str(det))

# --- D3: پیگیری (ویرایش قبلاً غیرممکن بود: «لطفاً یک مداخله انتخاب کنید»)
followup_iid = _last_id("interventions")


def _fill_fu(f):
    _combo_pick(f.student_combo, form_student.id)
    _combo_pick(f.intervention_combo, followup_iid)
    _combo_pick(f.staff_combo)
    f.description_input.setPlainText("پیگیری اولیه")
    f.result_description_input.setPlainText("نتیجه")


ok, det = _form_roundtrip("پیگیری", "followups", "description", lambda: FollowUpForm(intervention_id=followup_iid),
                          _fill_fu, "save_followup", lambda i: FollowUpForm(followup_id=i),
                          "description_input", "followup_saved", ("intervention_id", followup_iid))
with contextlib.redirect_stdout(io.StringIO()):
    fu_edit_form = FollowUpForm(followup_id=_last_id("followups"))
check("D", "FollowUpForm: ثبت → ردیف جدید روی همان مداخله؛ ویرایش → مقدار جدید در DB (قبلاً فرم ویرایش دانش‌آموز/مداخلهٔ خودش را نداشت و ذخیره همیشه رد می‌شد)",
      ok and fu_edit_form.intervention_combo.currentData() == followup_iid
      and fu_edit_form.student_combo.currentData() == form_student.id,
      f"{det} edit_combo={fu_edit_form.intervention_combo.currentData()} student={fu_edit_form.student_combo.currentData()}")


# --- D4: دانش‌آموز
def _fill_student(f):
    f.first_name_input.setText("دانش‌آموز اولیه")
    f.last_name_input.setText("فرم")
    f.national_code_input.setText("1818181818")
    f.birth_date_input.setText("1396/02/03")
    if hasattr(f, 'academic_year_input'):
        f.academic_year_input.setText(active_year.title)


ok, det = _form_roundtrip("دانش‌آموز", "students", "first_name", StudentForm, _fill_student, "save_student",
                          lambda i: StudentForm(student=StudentDAL().get_by_id(i)), "first_name_input", "accepted")
check("D", "StudentForm: ثبت → ردیف جدید؛ ویرایش → نام جدید در DB", ok, str(det))


# --- D5: هدف فردی
def _fill_goal(f):
    _combo_pick(f.student_combo, form_student.id)
    _combo_pick(f.assignee_combo)
    f.title_input.setText("هدف اولیه")
    f.description_input.setPlainText("شرح هدف")


ok, det = _form_roundtrip("هدف", "individual_goals", "title", lambda: GoalForm(profile_id=form_pid), _fill_goal, "save_goal",
                          lambda i: GoalForm(goal_id=i), "title_input", "goal_saved", ("student_profile_id", form_pid))
check("D", "GoalForm: ثبت → ردیف جدید با پروندهٔ درست؛ ویرایش → عنوان جدید در DB", ok, str(det))


# --- D6: فعالیت فوق‌برنامه
def _fill_act(f):
    _combo_pick(f.student_combo, form_student.id)
    _combo_pick(f.teacher_combo)
    f.title_input.setText("فعالیت اولیه")
    f.description_input.setPlainText("شرح فعالیت")


ok, det = _form_roundtrip("فعالیت", "extracurricular_activities", "title", lambda: ActivityForm(profile_id=form_pid), _fill_act,
                          "save_activity", lambda i: ActivityForm(activity_id=i), "title_input", "activity_saved",
                          ("student_profile_id", form_pid))
check("D", "ActivityForm: ثبت → ردیف جدید با پروندهٔ درست؛ ویرایش → عنوان جدید در DB", ok, str(det))


# --- D7: جلسهٔ مشاوره
def _fill_cs(f):
    _combo_pick(f.student_combo, form_student.id)
    _combo_pick(f.counselor_combo, counselor_id)
    f.topic_input.setText("جلسه اولیه")
    f.summary_input.setPlainText("خلاصه")


ok, det = _form_roundtrip("جلسه", "counseling_sessions", "topic", lambda: CounselingSessionForm(profile_id=form_pid), _fill_cs,
                          "save_session", lambda i: CounselingSessionForm(session_id=i), "topic_input", "session_saved",
                          ("student_profile_id", form_pid))
check("D", "CounselingSessionForm: ثبت → ردیف جدید با پروندهٔ درست؛ ویرایش → موضوع جدید در DB", ok, str(det))

# --- D8: اختصاص معلم
from views.dialogs.assign_teacher_dialog import AssignTeacherDialog  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    at = AssignTeacherDialog(student_ids=[form_student.id])
    _combo_pick(at.teacher_combo, teacher_id)
    _combo_pick(at.year_combo, active_year.id)
    at_emitted = []
    at.assignment_saved.connect(lambda *a: at_emitted.append(1))
    at_before = _count("teacher_assignments")
    at.save_assignment()
at_after = _count("teacher_assignments")
at_row = conn.execute("SELECT staff_id, student_id FROM teacher_assignments WHERE id = ?", (_last_id("teacher_assignments"),)).fetchone()
check("D", "AssignTeacherDialog: اختصاص → ردیف teacher_assignments با معلم و دانش‌آموز درست + سیگنال assignment_saved",
      at_after == at_before + 1 and at_emitted and tuple(at_row) == (teacher_id, form_student.id),
      f"{at_before}->{at_after} row={tuple(at_row) if at_row else None}")

# --- D9: انتخاب شایستگی از درخت داخل فرم مشاهده (مسیر واقعی کاربر) → شناسه در DB
with contextlib.redirect_stdout(io.StringIO()):
    tree_form = ObservationForm(student_id=form_student.id)
    _combo_pick(tree_form.student_combo, form_student.id)
    _combo_pick(tree_form.observer_combo)
    tree_form.behavior_input.setPlainText("مشاهده از درخت")
    tree = tree_form.competency_tree.tree
    clicked_id = None
    # سطح اول درخت «دسته» است و شایستگی‌ها فرزند آن‌اند
    candidates = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    candidates += [c.child(j) for c in list(candidates) for j in range(c.childCount())]
    for item in candidates:
        if item.data(0, Qt.ItemDataRole.UserRole) == "competency":
            tree.setCurrentItem(item)
            tree_form.competency_tree.on_item_clicked(item, 0)
            clicked_id = item.data(1, Qt.ItemDataRole.UserRole)
            break
    tree_form.save_observation()
tree_row = conn.execute("SELECT competency_id FROM observations WHERE id = ?", (_last_id("observations"),)).fetchone()
check("D", "درخت شایستگی داخل فرم مشاهده: کلیک روی شایستگی → full_path_selected → شناسه در فرم → پس از ذخیره همان competency_id در DB",
      clicked_id is not None and tree_form.selected_competency_id == clicked_id and tree_row and tree_row[0] == clicked_id,
      f"clicked={clicked_id} form={tree_form.selected_competency_id} db={tree_row}")

# --- D10: ورود
from views.dialogs.login_dialog import LoginDialog  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    ld = LoginDialog()
    login_ok, need_pw = [], []
    ld.login_successful.connect(lambda *a: login_ok.append(a))
    ld.need_change_password.connect(lambda *a: need_pw.append(a))
    ld.username_input.setText("admin")
    ld.password_input.setText("wrong-password")
    ld.login()
    wrong_rejected = not login_ok and not need_pw and ld.result() != QDialog.DialogCode.Accepted
    ld.password_input.setText("Admin@123")
    ld.login()
check("D", "LoginDialog: رمز اشتباه → بدون سیگنال و بدون Accept؛ رمز درست ادمین پیش‌فرض → سیگنال (ورود یا الزام تغییر رمز) و Accept",
      wrong_rejected and (login_ok or need_pw) and ld.result() == QDialog.DialogCode.Accepted,
      f"ok={login_ok} need={need_pw}")

# --- D11: تغییر رمز
from views.dialogs.change_password_dialog import ChangePasswordDialog  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    cp = ChangePasswordDialog(username='admin', user_id=1)
    cp.current_password_input.setText("nope")
    cp.new_password_input.setText("Strong#Pass2026")
    cp.confirm_password_input.setText("Strong#Pass2026")
    cp.change_password()
    still_old = UserDAL().authenticate("admin", "Admin@123") is not None and UserDAL().authenticate("admin", "Strong#Pass2026") is None
    cp2 = ChangePasswordDialog(username='admin', user_id=1)
    pw_emitted = []
    cp2.password_changed.connect(lambda *a: pw_emitted.append(1))
    cp2.current_password_input.setText("Admin@123")
    cp2.new_password_input.setText("Strong#Pass2026")
    cp2.confirm_password_input.setText("Strong#Pass2026")
    cp2.change_password()
    new_works = UserDAL().authenticate("admin", "Strong#Pass2026") is not None and UserDAL().authenticate("admin", "Admin@123") is None
check("D", "ChangePasswordDialog: رمز فعلی اشتباه → هیچ تغییری در DB؛ رمز فعلی درست → رمز جدید کار می‌کند، قدیمی نه، سیگنال password_changed",
      still_old and new_works and pw_emitted and cp2.result() == QDialog.DialogCode.Accepted,
      f"still_old={still_old} new_works={new_works}")

# --- D12: جست‌وجوی پیشرفته (قبلاً تاریخ تولد = امروز به‌طور پیش‌فرض → همیشه صفر نتیجه)
from views.dialogs.advanced_search_dialog import AdvancedSearchDialog  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    asd = AdvancedSearchDialog()
    default_birth = asd.birth_date_input.get_date_string()
    picked = []
    asd.student_selected.connect(lambda sid: picked.append(sid))
    asd.name_input.setText("اسموک")
    asd.perform_search()
    rows = asd.result_table.rowCount()
    if rows:
        asd.on_result_double_clicked(asd.result_table.item(0, 0))
check("D", "AdvancedSearchDialog: فیلتر تاریخ تولد خالی شروع می‌شود (قبلاً «امروز» و هیچ نتیجه‌ای)؛ جست‌وجوی نام → نتیجه؛ دابل‌کلیک → student_selected با شناسهٔ درست و Accept",
      default_birth == "" and rows >= 1 and picked == [form_student.id] and asd.result() == QDialog.DialogCode.Accepted,
      f"default_birth={default_birth!r} rows={rows} picked={picked}")

# --- D13: خروجی هوش مصنوعی — هر ۶ قالب فایل واقعی و معتبر
from views.dialogs.export_ai_dialog import ExportAIDialog  # noqa: E402

ai_results = {}
with contextlib.redirect_stdout(io.StringIO()):
    ai = ExportAIDialog(student_id=form_student.id, profile_id=form_pid)
    for idx, ext in enumerate(["pdf", "xlsx", "csv", "json", "txt", "zip"]):
        out_path = os.path.join(TMP, f"ai_export.{ext}")
        QFileDialog.getSaveFileName = staticmethod(lambda *a, _p=out_path, **k: (_p, ""))
        btn = ai.format_group.button(idx)
        if btn is None:
            ai_results[ext] = "no-button"
            continue
        btn.setChecked(True)
        n_before = len(ui_msgs)
        ai.export_data()
        problems = [m for m in ui_msgs[n_before:] if m[0] in ('crit', 'warn')]
        try:
            if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
                valid = "missing"
            elif ext == "json":
                with open(out_path, encoding="utf-8") as fh:
                    valid = isinstance(json.load(fh), dict)
            elif ext == "zip":
                valid = zipfile.ZipFile(out_path).testzip() is None
            elif ext == "csv":
                with open(out_path, encoding="utf-8-sig") as fh:
                    valid = len(list(csv.reader(fh))) > 1
            elif ext == "pdf":
                with open(out_path, "rb") as fh:
                    valid = fh.read(5) == b"%PDF-"
            elif ext == "xlsx":
                import openpyxl
                valid = openpyxl.load_workbook(out_path).active.max_row > 1
            else:
                with open(out_path, encoding="utf-8") as fh:
                    valid = len(fh.read()) > 20
        except Exception as e:
            valid = f"invalid: {e}"
        ai_results[ext] = (valid, problems[:1])
    ai.copy_prompt()
    clip_len = len(QApplication.clipboard().text())
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
check("D", "ExportAIDialog: هر ۶ قالب (PDF/Excel/CSV/JSON/TXT/ZIP) فایل واقعی و معتبر می‌سازند؛ «کپی پرامپت» متن را در کلیپ‌بورد می‌گذارد",
      all(v[0] is True and not v[1] for v in ai_results.values()) and clip_len > 50,
      f"{ai_results} clip={clip_len}")

# --- D14: زنگولهٔ اعلان‌ها (منبع: پیگیری‌های در انتظار/معوق) → کلیک → سیگنال به پنجرهٔ اصلی
from views.widgets.notification_widget import NotificationItem, NotificationWidget  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    conn.execute("UPDATE followups SET status = 'pending', next_action_date = '1405/06/10' WHERE id = ?", (_last_id("followups"),))
    conn.commit()
    nw = NotificationWidget()
    nw.load_notifications()
    clicked_data = []
    nw.notification_clicked.connect(lambda d: clicked_data.append(d))
    n_items = [c for c in nw.findChildren(NotificationItem)]
    if n_items:
        n_items[0].clicked.emit(n_items[0].data)
check("D", "NotificationWidget (زنگوله): پیگیری‌های در انتظار/معوق بارگذاری می‌شوند، کلیک روی یک مورد notification_clicked با دادهٔ پیگیری می‌فرستد",
      len(n_items) >= 1 and clicked_data and clicked_data[0].get('student_name'),
      f"items={len(n_items)} label={nw.count_label.text()!r}")

# --- D15: اعتبارسنجی مشاهده: توضیحات اختیاری ولی اگر نوشته شد ≥۳ نویسه؛ رفتار همچنان الزامی
from services.observation_service import ObservationService  # noqa: E402
from utils.error_handler import ServiceError, ValidationError  # noqa: E402

obs_service = ObservationService()
base = {'student_id': form_student.id, 'staff_id': 1, 'competency_id': comps[0].id,
        'observation_date': '1405/07/22', 'behavior_type': 'مثبت', 'severity': 2}
with contextlib.redirect_stdout(io.StringIO()):
    created = obs_service.create_observation({**base, 'behavior': 'رفتار بدون توضیحات'})
    short_desc_error = None
    try:
        obs_service.create_observation({**base, 'behavior': 'رفتار', 'description': 'ab'})
    except (ValidationError, ServiceError) as e:
        short_desc_error = str(e)
    no_behavior_error = None
    try:
        obs_service.create_observation({**base, 'behavior': '', 'description': 'توضیحات کامل'})
    except (ValidationError, ServiceError) as e:
        no_behavior_error = str(e)
stored_desc = conn.execute("SELECT description FROM observations WHERE id = ?", (created.id,)).fetchone()[0]
check("D", "سرویس مشاهده: بدون توضیحات → ثبت می‌شود و description = متن رفتار (ستون NOT NULL)؛ توضیحات کوتاه‌تر از ۳ نویسه → خطا؛ رفتار خالی همچنان خطا",
      stored_desc == 'رفتار بدون توضیحات' and short_desc_error and 'توضیحات' in short_desc_error
      and no_behavior_error and 'رفتار' in no_behavior_error,
      f"desc={stored_desc!r} short={short_desc_error!r} nobeh={no_behavior_error!r}")

# --- D16: کد بدون مصرف‌کننده در رابط (فقط ثبت وضعیت — تصمیم با کاربر)
UNREACHABLE_UI = {
    'RecommendationWidget': {'views/widgets/recommendation_widget.py'},
}
consumers = {}
for cls_name, own_files in UNREACHABLE_UI.items():
    hits = []
    for sub in ('views', 'views/pages', 'views/dialogs', 'views/widgets', 'services', 'utils'):
        for fname in os.listdir(sub):
            path = os.path.join(sub, fname)
            if not fname.endswith('.py') or path in own_files:
                continue
            if re.search(rf'\b{cls_name}\b', read(path)):
                hits.append(path)
    if re.search(rf'\b{cls_name}\b', read('main.py')):
        hits.append('main.py')
    consumers[cls_name] = hits
check("D", "وضعیت: RecommendationWidget اکنون تب پروندهٔ دانش‌آموز است، AttachmentDialog از پروندهٔ دانش‌آموز باز می‌شود، زیرسیستم اعلان‌ها حذف شد — هیچ دیالوگ/ویجت بدون مصرف‌کننده‌ای نمانده",
      consumers.get('RecommendationWidget') == ['views/pages/student_profile_page.py'],
      str(consumers))

# ============================================================
print()
print("=" * 76)
print("بخش E: پیوست‌ها (زنجیرهٔ کامل)، نخ‌ها/کارگرها، ثبت دوباره (Race)، وضعیت Screening/Recommendation")
print("=" * 76)

import ast  # noqa: E402

import services.attachment_service as attachment_service_mod  # noqa: E402
from dal.attachment_dal import AttachmentDAL  # noqa: E402
from views.dialogs.attachment_dialog import AttachmentDialog, AttachmentUploadWorker  # noqa: E402

ATT_UPLOAD_DIR = os.path.join(TMP, "att_uploads")
attachment_service_mod.ATTACHMENTS_DIR = ATT_UPLOAD_DIR
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)


def _wait_dialog_upload(dialog, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if not dialog.is_uploading() and not dialog._upload_queue:
            app.processEvents()
            return True
        time.sleep(0.02)
    return False


def _write_sample(name, data):
    path = os.path.join(TMP, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


sample_txt = _write_sample("note.txt", "متن نمونهٔ پیوست\n".encode("utf-8") * 20)
png_bytes = (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 64)
sample_png = _write_sample("photo.png", png_bytes)
entity_id = smoke_student.id

with contextlib.redirect_stdout(io.StringIO()):
    att_dialog = AttachmentDialog("student", entity_id)
    att_added = []
    att_dialog.attachment_added.connect(lambda: att_added.append(1))
    n_msgs = len(ui_msgs)
    att_dialog.upload_files([sample_txt, sample_png])
    finished = _wait_dialog_upload(att_dialog)
rows = conn.execute("SELECT id, file_name, file_path, created_by FROM attachments WHERE entity_type = 'student' "
                    "AND entity_id = ? AND is_deleted = 0 ORDER BY id", (entity_id,)).fetchall()
audit_rows = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE entity_type = 'attachments' AND action = 'create'").fetchone()[0]
batch_msgs = [m for m in ui_msgs[n_msgs:]]
check("E", "AttachmentDialog: آپلود دو فایل (txt + png) در صف ترتیبی → ۲ رکورد با created_by کاربر واردشده، ۲ فایل واقعی داخل پوشهٔ موجودیت، Audit، فهرست تازه‌سازی‌شده، یک پیام جمع‌بندی، دکمه‌ها دوباره فعال",
      finished and len(rows) == 2 and all(r[3] == 1 for r in rows)
      and all(os.path.isfile(r[2]) and r[2].startswith(os.path.join(ATT_UPLOAD_DIR, "student", str(entity_id))) for r in rows)
      and att_dialog.file_list.count() == 2 and att_added == [1]
      and audit_rows >= 2 and len(batch_msgs) == 1 and batch_msgs[0][0] == "info" and "2" in batch_msgs[0][1]
      and att_dialog.add_btn.isEnabled() and not att_dialog.is_uploading(),
      f"finished={finished} rows={[(r[1], r[3]) for r in rows]} list={att_dialog.file_list.count()} msgs={batch_msgs}")

# --- E2: دو فایل هم‌نام در یک ثانیه → دو فایل جدا (قبلاً نام فقط با timestamp ثانیه‌ای یکتا می‌شد)
dup_a = _write_sample("same_name.txt", b"first content ..........")
dup_dir = os.path.join(TMP, "dup2")
os.makedirs(dup_dir, exist_ok=True)
dup_b = os.path.join(dup_dir, "same_name.txt")
with open(dup_b, "wb") as fh:
    fh.write(b"second content .........")
with contextlib.redirect_stdout(io.StringIO()):
    att_dialog.upload_files([dup_a, dup_b])
    _wait_dialog_upload(att_dialog)
dup_rows = conn.execute("SELECT file_path FROM attachments WHERE entity_type = 'student' AND entity_id = ? "
                        "AND file_name = 'same_name.txt' AND is_deleted = 0", (entity_id,)).fetchall()
dup_contents = sorted(open(r[0], "rb").read() for r in dup_rows) if dup_rows else []
check("E", "دو آپلود هم‌نام پشت سر هم: دو مسیر فایل متفاوت با محتوای خودشان (قبلاً روی هم نوشته می‌شدند و دو رکورد به یک فایل اشاره می‌کردند)",
      len(dup_rows) == 2 and dup_rows[0][0] != dup_rows[1][0]
      and dup_contents == [b"first content ..........", b"second content ........."],
      f"paths={[os.path.basename(r[0]) for r in dup_rows]}")

# --- E3: نوع غیرمجاز → نه رکورد، نه فایل (نه حتی .part)
entity_folder = os.path.join(ATT_UPLOAD_DIR, "student", str(entity_id))
files_before = sorted(os.listdir(entity_folder))
count_before = conn.execute("SELECT COUNT(*) FROM attachments WHERE is_deleted = 0").fetchone()[0]
bad_file = _write_sample("payload.exe", b"MZ" + b"\x00" * 100)
with contextlib.redirect_stdout(io.StringIO()):
    n_msgs = len(ui_msgs)
    att_dialog.upload_files([bad_file])
    _wait_dialog_upload(att_dialog)
count_after = conn.execute("SELECT COUNT(*) FROM attachments WHERE is_deleted = 0").fetchone()[0]
files_after = sorted(os.listdir(entity_folder))
bad_msgs = ui_msgs[n_msgs:]
check("E", "فایل با پسوند/محتوای غیرمجاز (exe): آپلود با پیام خطا رد می‌شود؛ هیچ رکورد و هیچ فایلی (حتی .part) باقی نمی‌ماند",
      count_after == count_before and files_after == files_before
      and bad_msgs and bad_msgs[-1][0] == "crit",
      f"count {count_before}->{count_after} files_diff={sorted(set(files_after) ^ set(files_before))} msgs={bad_msgs[-1:]}")

# --- E4: شکست درج در دیتابیس → فایل یتیم روی دیسک نمی‌ماند
real_create = AttachmentDAL.create


def _create_fails(self, attachment):
    raise RuntimeError("db insert failed")


AttachmentDAL.create = _create_fails
try:
    with contextlib.redirect_stdout(io.StringIO()):
        n_msgs = len(ui_msgs)
        att_dialog.upload_files([sample_txt])
        _wait_dialog_upload(att_dialog)
finally:
    AttachmentDAL.create = real_create
files_after_dbfail = sorted(os.listdir(entity_folder))
check("E", "اگر درج رکورد در دیتابیس شکست بخورد: پیام خطا، رکوردی ثبت نمی‌شود و فایل نوشته‌شده روی دیسک پاک می‌شود (قبلاً فایل یتیم می‌ماند)",
      files_after_dbfail == files_before
      and conn.execute("SELECT COUNT(*) FROM attachments WHERE is_deleted = 0").fetchone()[0] == count_before
      and ui_msgs[n_msgs:] and ui_msgs[-1][0] == "crit" and "db insert failed" in ui_msgs[-1][1],
      f"files_diff={sorted(set(files_after_dbfail) ^ set(files_before))} msg={ui_msgs[-1:]}")

# --- E5: جست‌وجو / پاک‌کردن جست‌وجو / انتخاب و پیش‌نمایش / دانلود
with contextlib.redirect_stdout(io.StringIO()):
    att_dialog.search_input.setText("photo")
    att_dialog.search_attachments()
    search_count = att_dialog.file_list.count()
    att_dialog.clear_search()
    cleared_count = att_dialog.file_list.count()
    txt_item = next(att_dialog.file_list.item(i) for i in range(att_dialog.file_list.count())
                    if "note.txt" in att_dialog.file_list.item(i).text())
    att_dialog.on_file_selected(txt_item)
    preview_text = att_dialog.preview_label.text()
    info_text = att_dialog.info_text.toPlainText()
    download_target = os.path.join(TMP, "downloaded_note.txt")
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (download_target, ""))
    att_dialog.download_file()
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
check("E", "جست‌وجو (photo → ۱ مورد)، پاک‌کردن جست‌وجو (همه)، انتخاب فایل متنی → اطلاعات + پیش‌نمایش محتوا، دانلود → فایل با همان محتوا",
      search_count == 1 and cleared_count == 4
      and "note.txt" in info_text and "متن نمونهٔ پیوست" in preview_text
      and os.path.exists(download_target) and open(download_target, "rb").read() == open(sample_txt, "rb").read(),
      f"search={search_count} cleared={cleared_count} preview={preview_text[:30]!r}")

# --- E6: حذف → حذف منطقی در DB، فهرست −۱، سیگنال؛ فایل فیزیکی (به‌عمد) می‌ماند
with contextlib.redirect_stdout(io.StringIO()):
    att_deleted = []
    att_dialog.attachment_deleted.connect(lambda: att_deleted.append(1))
    deleted_id = att_dialog.current_attachment_id
    deleted_path = conn.execute("SELECT file_path FROM attachments WHERE id = ?", (deleted_id,)).fetchone()[0]
    att_dialog.delete_selected()
is_deleted_flag = conn.execute("SELECT is_deleted FROM attachments WHERE id = ?", (deleted_id,)).fetchone()[0]
check("E", "حذف پیوست انتخاب‌شده: is_deleted=1 در DB، فهرست −۱، سیگنال attachment_deleted؛ فایل فیزیکی برای امکان بازیابی می‌ماند (طراحی مستند)",
      is_deleted_flag == 1 and att_dialog.file_list.count() == 3 and att_deleted == [1] and os.path.exists(deleted_path),
      f"flag={is_deleted_flag} list={att_dialog.file_list.count()}")

# --- E7: Race در دیالوگ: شروع آپلود دوم وسط آپلود اول رد می‌شود؛ بستن وسط آپلود منتظر می‌ماند
big_file = _write_sample("big.txt", b"x" * (3 * 1024 * 1024))
with contextlib.redirect_stdout(io.StringIO()):
    n_msgs = len(ui_msgs)
    att_dialog.upload_files([big_file])
    first_worker = att_dialog.upload_worker
    was_running = att_dialog.is_uploading()
    att_dialog.upload_files([sample_txt])  # باید رد شود
    same_worker = att_dialog.upload_worker is first_worker
    att_dialog.close()                      # closeEvent منتظر پایان کارگر می‌ماند
    _wait_dialog_upload(att_dialog)
race_msgs = [m for m in ui_msgs[n_msgs:] if "آپلود قبلی" in m[1]]
check("E", "Race: درخواست آپلود دوم وسط آپلود اول با پیام رد می‌شود و کارگر جایگزین نمی‌شود؛ بستن دیالوگ وسط آپلود بدون کشتن نخ انجام می‌شود",
      was_running and same_worker and len(race_msgs) == 1 and not first_worker.isRunning(),
      f"running={was_running} same={same_worker} race_msgs={len(race_msgs)}")

# --- E8: نگهبان ثبت دوباره در فرم‌ها (کلیک دوم که وسط QMessageBox پردازش می‌شود)
reentry = {'count': 0}
real_info = QMessageBox.information


def _reentrant_info(*a, **k):
    ui_msgs.append(("info", str(a[2])[:100]))
    if reentry['count'] == 0:
        reentry['count'] += 1
        dbl_form.save_observation()      # شبیه‌سازی کلیک دوم در حلقهٔ رویداد تودرتو
    return QMessageBox.StandardButton.Ok


with contextlib.redirect_stdout(io.StringIO()):
    dbl_form = ObservationForm(student_id=form_student.id)
    _combo_pick(dbl_form.student_combo, form_student.id)
    _combo_pick(dbl_form.observer_combo)
    dbl_form.behavior_input.setPlainText("ثبت دوباره نباید بشود")
    dbl_form.selected_competency_id = comps[2].id
    obs_before = _count("observations")
    QMessageBox.information = staticmethod(_reentrant_info)
    try:
        dbl_form.save_observation()
    finally:
        QMessageBox.information = real_info
obs_after = _count("observations")
guard_src = read("utils/ui_guards.py")
guarded_forms = sum(1 for f in ("observation_form", "intervention_form", "followup_form", "student_form", "goal_form",
                                 "activity_form", "counseling_session_form", "assign_teacher_dialog")
                    if "@single_submit()" in read(f"views/dialogs/{f}.py"))
check("E", "نگهبان single_submit: ورود دوبارهٔ save_observation وسط پیام موفقیت فقط یک رکورد می‌سازد؛ پس از پایان، پرچم آزاد و دکمه فعال؛ هر ۸ فرم نگهبان دارند",
      obs_after == obs_before + 1 and reentry['count'] == 1 and not dbl_form._submit_in_progress
      and dbl_form.save_btn.isEnabled() and guarded_forms == 8 and "def single_submit" in guard_src,
      f"{obs_before}->{obs_after} guarded_forms={guarded_forms}")

# --- E9: نخ‌ها: بدنهٔ run کارگرها هیچ ویجتی را مستقیم لمس نمی‌کند؛ هیچ QThreadی سیگنال finished را بازتعریف نمی‌کند
WIDGET_HINTS = ('progress_bar', 'setText', 'setValue', 'QMessageBox', 'file_list', 'table', 'setEnabled', 'label')
thread_issues = []
for rel in ("views/dialogs/attachment_dialog.py", "views/pages/backup_page.py"):
    tree_ast = ast.parse(read(rel))
    for node in ast.walk(tree_ast):
        if isinstance(node, ast.ClassDef) and any(getattr(b, 'id', '') == 'QThread' for b in node.bases):
            for item in node.body:
                if isinstance(item, ast.Assign) and any(getattr(t, 'id', '') == 'finished' for t in item.targets):
                    thread_issues.append((rel, node.name, "finished redefined"))
                if isinstance(item, ast.FunctionDef) and item.name == 'run':
                    body_src = ast.unparse(item)
                    for hint in WIDGET_HINTS:
                        if hint in body_src:
                            thread_issues.append((rel, node.name, hint))
check("E", "نخ‌ها (بند ۲۰): AttachmentUploadWorker و BackupWorker در run فقط سیگنال می‌فرستند (بدون دسترسی مستقیم به ویجت)، و سیگنال داخلی finished را بازتعریف نمی‌کنند؛ اتصال DB داخل worker_context نخ‌محلی است",
      not thread_issues and "worker_context(self.user_context)" in read("views/dialogs/attachment_dialog.py"),
      str(thread_issues))

# --- E10: اتصال نخ کارگر پس از پایان آزاد می‌شود (رجیستری اتصال‌ها رشد نمی‌کند)
with contextlib.redirect_stdout(io.StringIO()):
    db.get_connection(user_id=1)
    registry_before = len(dbc.DatabaseConnection._open_connections)
    for _ in range(3):
        w = AttachmentUploadWorker(service=attachment_service_mod.AttachmentService(), entity_type="student",
                                   entity_id=entity_id, file_path=sample_txt, created_by=1)
        w.start()
        w.wait(30000)
    app.processEvents()
    db.get_connection(user_id=1)
    registry_after = len(dbc.DatabaseConnection._open_connections)
check("E", "سه آپلود پیاپی در نخ‌های کارگر: اتصال‌های نخ‌های تمام‌شده آزاد می‌شوند و رجیستری اتصال‌ها رشد نمی‌کند",
      registry_after <= registry_before + 1,
      f"registry {registry_before}->{registry_after}")

# --- E11: بازکردن فایل بدون shell
att_src = read("views/dialogs/attachment_dialog.py")
check("E", "«باز کردن فایل» با QDesktopServices.openUrl انجام می‌شود؛ هیچ os.system/shell با مسیر فایل در دیالوگ پیوست نیست (قبلاً تزریق فرمان از طریق نام فایل ممکن بود)",
      "os.system(" not in att_src and "QDesktopServices.openUrl(QUrl.fromLocalFile(" in att_src,
      "")

# --- E12: وضعیت Screening و Recommendation (فقط گزارش — طبق تصمیم کاربر)
screening_ui = [f for f in (os.path.join("views", d, n) for d in ("pages", "dialogs", "widgets") for n in os.listdir(os.path.join("views", d)) if n.endswith(".py"))
                if re.search(r"\b(ScreeningService|ScreeningDAL|ScreeningResultDAL|screening_form|ScreeningForm)\b", read(f))]
rec_widget_users = [f for f in (os.path.join("views", d, n) for d in ("pages", "dialogs", "widgets") for n in os.listdir(os.path.join("views", d)) if n.endswith(".py"))
                    if "RecommendationWidget" in read(f) and not f.endswith("recommendation_widget.py")]
check("E", "وضعیت ثبت‌شده: Screening هیچ UI ثبت/ویرایش ندارد (فقط نمایش لایه در گزارش — قابلیت جدید محسوب می‌شود و ساخته نشد)؛ RecommendationWidget اکنون در پروندهٔ دانش‌آموز مصرف می‌شود",
      not screening_ui and rec_widget_users == ['views/pages/student_profile_page.py'],
      f"screening_ui={screening_ui} rec_users={rec_widget_users}")

# ============================================================
print()
print("=" * 76)
print("بخش F: تراکنش، ایمپورت اکسل، قرارداد نتیجه، مدیریت استثنا، SQL، Constraints، خروجی‌ها، سازگاری داده")
print("=" * 76)

import sqlite3  # noqa: E402

import openpyxl  # noqa: E402

from services.base_service import BaseService  # noqa: E402
from utils.excel_importer import ExcelImporter  # noqa: E402

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)


# --- F1: تراکنش سرویس واقعاً اتمیک است (قبلاً conn.commit() در DALها تراکنش سرویس را می‌شکست)
class _ProbeService(BaseService):
    def __init__(self):
        super().__init__()
        self.student_dal = StudentDAL()


def _two_step_then_fail(service):
    st1 = Student()
    st1.first_name, st1.last_name = "تراکنش", "گام یک"
    service.student_dal.create(st1)
    st2 = Student()
    st2.first_name, st2.last_name = "تراکنش", "گام دو"
    service.student_dal.create(st2)
    raise RuntimeError("گام سوم شکست خورد")


probe_service = _ProbeService()
tx_before = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
tx_error = None
with contextlib.redirect_stdout(io.StringIO()):
    try:
        probe_service.execute_in_transaction(_two_step_then_fail, probe_service)
    except Exception as e:
        tx_error = e
tx_after = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
dal_raw_commits = sum(read(os.path.join("dal", f)).count("conn.commit()") for f in os.listdir("dal") if f.endswith(".py"))
check("F", "execute_in_transaction: دو درج DAL و سپس شکست → هیچ‌کدام باقی نمی‌ماند (قبلاً هر DAL با conn.commit() تراکنش سرویس را می‌شکست و داده نیمه‌کاره می‌ماند)؛ هیچ conn.commit() خامی در dal/ نمانده",
      tx_error is not None and tx_after == tx_before and dal_raw_commits == 0 and not conn.in_transaction,
      f"{tx_before}->{tx_after} raw_commits={dal_raw_commits} err={tx_error}")

# --- F2: ایمپورت اکسل با فایل نمونهٔ خودِ برنامه (قبلاً همیشه «ستون‌های ضروری یافت نشدند: last_name»)
importer = ExcelImporter()
sample_xlsx = os.path.join(TMP, "sample_students.xlsx")
with contextlib.redirect_stdout(io.StringIO()):
    sample_ok, _ = importer.create_sample_excel(sample_xlsx)
    st_before = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    prof_before = conn.execute("SELECT COUNT(*) FROM student_academic_profiles").fetchone()[0]
    ok_import, msg_import, n_import, errs_import = importer.import_students_from_excel(sample_xlsx)
st_after = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
prof_after = conn.execute("SELECT COUNT(*) FROM student_academic_profiles").fetchone()[0]
sample_rows = openpyxl.load_workbook(sample_xlsx).active.max_row - 1
imported_names = conn.execute("SELECT first_name, last_name, father_name FROM students ORDER BY id DESC LIMIT ?", (sample_rows,)).fetchall()
check("F", "ایمپورت اکسل با فایل نمونهٔ خودِ برنامه: همهٔ ردیف‌ها با پرونده وارد می‌شوند و ستون‌ها درست نگاشت می‌شوند (نام/نام خانوادگی/نام پدر جدا)",
      sample_ok and ok_import and n_import == sample_rows and not errs_import
      and st_after == st_before + sample_rows and prof_after == prof_before + sample_rows
      and all(r[0] and r[1] and r[0] != r[1] and r[2] != r[0] for r in imported_names),
      f"ok={ok_import} n={n_import} errs={errs_import} names={[tuple(r) for r in imported_names]}")

# --- F3: استواری ایمپورت: تکراری در فایل، پایهٔ غیرعددی، فایل خالی، فایل خراب، مسیر ناموجود، شکست پرونده بدون دانش‌آموز نیمه‌کاره
wb = openpyxl.load_workbook(sample_xlsx)
ws = wb.active
ws.append(["دوقلو", "اولی", "7777777777", "1395/01/01", "پدر", "ولی", "09121234567", "آدرس", 2, "ب"])
ws.append(["دوقلو", "دومی", "7777777777", "1395/01/01", "پدر", "ولی", "09121234567", "آدرس", 2, "ب"])   # کد ملی تکراری در همین فایل
ws.append(["پایه‌غلط", "جیم", "8888888888", "1395/01/01", "پدر", "ولی", "09121234567", "آدرس", "abc", "ب"])
ws.append(["", "بدون‌نام", "9999999999", "", "", "", "", "", 1, ""])
# ردیف‌های قبلی نمونه حالا تکراری‌اند (کد ملی‌شان در DB هست) → باید گزارش شوند نه دوباره وارد
robust_xlsx = os.path.join(TMP, "robust.xlsx")
wb.save(robust_xlsx)
with contextlib.redirect_stdout(io.StringIO()):
    before_robust = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    ok_r, msg_r, n_r, errs_r = importer.import_students_from_excel(robust_xlsx)
    after_robust = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    twins = conn.execute("SELECT COUNT(*) FROM students WHERE national_code = '7777777777'").fetchone()[0]
    empty_xlsx = os.path.join(TMP, "empty.xlsx")
    openpyxl.Workbook().save(empty_xlsx)
    ok_empty, msg_empty, n_empty, _ = importer.import_students_from_excel(empty_xlsx)
    corrupt_xlsx = os.path.join(TMP, "corrupt.xlsx")
    with open(corrupt_xlsx, "w", encoding="utf-8") as fh:
        fh.write("this is not an excel file")
    ok_corrupt, msg_corrupt, n_corrupt, _ = importer.import_students_from_excel(corrupt_xlsx)
    ok_missing, msg_missing, _, _ = importer.import_students_from_excel(os.path.join(TMP, "nope.xlsx"))
    # شکست ساخت پرونده → دانش‌آموزِ همان ردیف هم نباید بماند
    real_profile_create = StudentAcademicProfileDAL.create
    StudentAcademicProfileDAL.create = lambda self, p: (_ for _ in ()).throw(RuntimeError("profile failed"))
    single_xlsx = os.path.join(TMP, "single.xlsx")
    wb1 = openpyxl.Workbook()
    ws1 = wb1.active
    ws1.append(["نام", "نام خانوادگی", "کد ملی", "پایه", "کلاس"])
    ws1.append(["نیمه", "کاره", "1212121212", 3, "الف"])
    wb1.save(single_xlsx)
    try:
        before_partial = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        ok_partial, msg_partial, n_partial, errs_partial = importer.import_students_from_excel(single_xlsx)
    finally:
        StudentAcademicProfileDAL.create = real_profile_create
    after_partial = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
robust_expected_errors = sample_rows + 3   # نمونه‌های تکراری + کد ملی تکراری + پایهٔ غلط + نام خالی
check("F", "استواری ایمپورت: ردیف تکراری/پایهٔ غیرعددی/نام خالی گزارش می‌شوند و بقیه وارد می‌شوند؛ فایل خالی، فایل خراب و مسیر ناموجود بدون crash پیام روشن می‌دهند؛ شکست ساخت پرونده → دانش‌آموز نیمه‌کاره نمی‌ماند",
      ok_r and n_r == 1 and len(errs_r) == robust_expected_errors and after_robust == before_robust + 1 and twins == 1
      and ok_empty is False and msg_empty and n_empty == 0
      and ok_corrupt is False and msg_corrupt and n_corrupt == 0
      and ok_missing is False
      and n_partial == 0 and errs_partial and after_partial == before_partial and not conn.in_transaction,
      f"robust n={n_r} errs={len(errs_r)}/{robust_expected_errors} {errs_r[:6]} twins={twins} empty={ok_empty} corrupt={ok_corrupt} partial={before_partial}->{after_partial}")

# --- F4: قرارداد نتیجهٔ حذف در صفحه‌ها: حذف رکوردی که دیگر نیست → هشدار، نه «با موفقیت حذف شد»
import views.pages.goals_page as goals_page_mod  # noqa: E402
from dal.goal_dal import GoalDAL  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    gpage = goals_page_mod.GoalsPage()
    goal_obj = GoalDAL().get_by_id(_last_id("individual_goals"))
    n0 = len(ui_msgs)
    gpage.delete_goal(goal_obj)          # حذف واقعی
    first_msgs = ui_msgs[n0:]
    n1 = len(ui_msgs)
    gpage.delete_goal(goal_obj)          # همان شیء قدیمی؛ رکورد دیگر نیست
    second_msgs = ui_msgs[n1:]
check("F", "قرارداد نتیجه (بند ۱۷): حذف هدف موفق → پیام موفقیت؛ حذف دوبارهٔ همان رکورد (دیگر وجود ندارد) → هشدار «پیدا نشد» و نه موفقیت دروغین (همین اصلاح در فعالیت‌ها و جلسات مشاوره)",
      first_msgs and first_msgs[-1][0] == "info" and second_msgs and second_msgs[-1][0] == "warn"
      and "پیدا نشد" in second_msgs[-1][1]
      and all("deleted = self." in read(f"views/pages/{pg}.py") for pg in ("goals_page", "activities_page", "counseling_page")),
      f"first={first_msgs[-1:]} second={second_msgs[-1:]}")


# --- F5: مدیریت استثنا (بند ۱۶): هیچ except بی‌صدایی در services/ و dal/ نمانده
def _silent_handlers(paths):
    found = []
    for path in paths:
        src = read(path)
        lines = src.splitlines()
        for node in ast.walk(ast.parse(src)):
            if not isinstance(node, ast.ExceptHandler):
                continue
            body = ast.unparse(node)
            if re.search(r'logger\.|log_error|log_warning|logging\.|print\(|QMessageBox|raise\b|traceback|show_error|handle_error|ErrorHandler|get_logger\(', body):
                continue
            region = "\n".join(lines[node.lineno - 1: node.end_lineno])
            if '#' in region:      # مستندشده (عمدی)
                continue
            found.append((path, node.lineno))
    return found


silent_now = _silent_handlers([os.path.join(d, f) for d in ("services", "dal") for f in os.listdir(d) if f.endswith(".py")])
bare_excepts = [(d, f) for d in ("services", "dal", "utils", "views/pages", "views/dialogs", "views/widgets", "database")
                for f in os.listdir(d) if f.endswith(".py") and re.search(r"^\s*except\s*:\s*$", read(os.path.join(d, f)), re.M)]
check("F", "مدیریت استثنا: هیچ except بدون لاگ/raise/پیام (و بدون توضیح) در services/ و dal/ نمانده (۷۸ مورد لاگ‌دار شدند)؛ هیچ except خالی (bare) در پروژه نیست",
      not silent_now and not bare_excepts,
      f"silent={silent_now[:5]} bare={bare_excepts[:3]}")

# --- F6: SQL فقط پارامتری (بند ۳۰): هر رشتهٔ SQL درون‌یابی‌شده فقط placeholder/نام ثابت جدول/عبارت داخلی دارد
ALLOWED_SQL_INTERPOLATION = {"placeholders", "placeholders(len(chunk))", "table", "column", "new_values", "old_values",
                             "edit_when", "year_filter_sub", "joins", "' AND '.join(where)", "(joins, ' AND '.join(where))"}
sql_dynamic = []
for d in ("dal", "services", "database", "utils"):
    for fname in os.listdir(d):
        if not fname.endswith(".py"):
            continue
        for node in ast.walk(ast.parse(read(os.path.join(d, fname)))):
            if isinstance(node, ast.JoinedStr):
                text = "".join(v.value for v in node.values if isinstance(v, ast.Constant))
                if re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE TRIGGER)\b", text):
                    for v in node.values:
                        if isinstance(v, ast.FormattedValue) and ast.unparse(v.value) not in ALLOWED_SQL_INTERPOLATION:
                            sql_dynamic.append((os.path.join(d, fname), node.lineno, ast.unparse(v.value)))
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant) \
                    and isinstance(node.left.value, str) and re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", node.left.value):
                if ast.unparse(node.right) not in ALLOWED_SQL_INTERPOLATION:
                    sql_dynamic.append((os.path.join(d, fname), node.lineno, ast.unparse(node.right)))
check("F", "SQL (بند ۳۰): هیچ مقدار کاربر با رشته‌سازی وارد SQL نمی‌شود — تنها درون‌یابی‌ها placeholder، نام ثابت جدول/ستون داخلی و بخش‌های WHERE با «?» هستند",
      not sql_dynamic, str(sql_dynamic[:5]))

# --- F7: Constraints (بند ۳۱): FK فعال و اجرا می‌شود، UNIQUE کد ملی و پروندهٔ (دانش‌آموز، سال)، NOT NULL ستون‌های کلیدی
fk_on = conn.execute("PRAGMA foreign_keys").fetchone()[0]


def _integrity(sql, params=()):
    try:
        conn.execute(sql, params)
        conn.commit()
        return "accepted"
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return str(e)


fk_err = _integrity("INSERT INTO observations (student_profile_id, staff_id, competency_id, observation_date, description, behavior, behavior_type) "
                    "VALUES (999999, 1, 1, '1405/01/01', 'x', 'y', 'مثبت')")
uniq_err = _integrity("INSERT INTO students (first_name, last_name, national_code) VALUES ('تکراری', 'کد', ?)", (form_student.national_code,))
prof_err = _integrity("INSERT INTO student_academic_profiles (student_id, academic_year_id, grade) VALUES (?, ?, 2)",
                      (form_student.id, active_year.id))
notnull_err = _integrity("INSERT INTO students (first_name, last_name) VALUES (NULL, 'x')")
with contextlib.redirect_stdout(io.StringIO()):
    from services.student_service import StudentService
    dup_service_error = None
    try:
        StudentService().create_student({'first_name': 'تکراری', 'last_name': 'سرویس', 'national_code': form_student.national_code,
                                         'birth_date': '1395/01/01', 'gender': 'male'})
    except Exception as e:
        dup_service_error = str(e)
check("F", "Constraints (بند ۳۱): foreign_keys=ON و FK نقض‌شده رد می‌شود؛ UNIQUE کد ملی و UNIQUE پروندهٔ (دانش‌آموز، سال) و NOT NULL نام اجرا می‌شوند؛ سرویس هم کد ملی تکراری را با پیام رد می‌کند",
      fk_on == 1 and "FOREIGN KEY" in fk_err and "UNIQUE" in uniq_err and "UNIQUE" in prof_err and "NOT NULL" in notnull_err
      and dup_service_error and ("تکراری" in dup_service_error or "UNIQUE" in dup_service_error or "قبلاً" in dup_service_error),
      f"fk={fk_err[:40]} uniq={uniq_err[:40]} prof={prof_err[:40]} notnull={notnull_err[:30]} svc={dup_service_error!r}")

# --- F8: خروجی‌های واقعی از صفحه‌ها (بند ۲۴): PDF/Excel گزارش دانش‌آموز، Excel فهرست دانش‌آموزان + فایل نمونه
export_results = {}


def _export_via(page, method, target):
    QFileDialog.getSaveFileName = staticmethod(lambda *a, _t=target, **k: (_t, ""))
    n_before = len(ui_msgs)
    with contextlib.redirect_stdout(io.StringIO()):
        getattr(page, method)()
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
    msgs_after = ui_msgs[n_before:]
    ok_file = os.path.exists(target) and os.path.getsize(target) > 0
    if ok_file and target.endswith(".pdf"):
        with open(target, "rb") as fh:
            ok_file = fh.read(5) == b"%PDF-"
    elif ok_file and target.endswith(".xlsx"):
        ok_file = openpyxl.load_workbook(target).active.max_row >= 2
    return ok_file and bool(msgs_after) and msgs_after[-1][0] == "info", (ok_file, msgs_after[-1:])


with contextlib.redirect_stdout(io.StringIO()):
    win.reports_page.select_student(form_student.id)
export_results["report_pdf"] = _export_via(win.reports_page, "export_pdf", os.path.join(TMP, "student_report.pdf"))
export_results["report_xlsx"] = _export_via(win.reports_page, "export_excel", os.path.join(TMP, "student_report.xlsx"))
export_results["students_xlsx"] = _export_via(win.students_page, "export_to_excel", os.path.join(TMP, "students.xlsx"))
export_results["sample_xlsx"] = _export_via(win.students_page, "download_sample_excel", os.path.join(TMP, "sample_dl.xlsx"))
check("F", "خروجی‌ها از مسیر صفحه (بند ۲۴): PDF و Excel گزارش دانش‌آموز، Excel فهرست دانش‌آموزان و فایل نمونهٔ ایمپورت → فایل واقعی و معتبر + پیام موفقیت",
      all(v[0] for v in export_results.values()),
      str({k: v[1] for k, v in export_results.items() if not v[0]}))

# --- F9: سازگاری داده UI↔DB (بند ۲۳): صفحهٔ مشاهدات — تعداد ردیف جدول = DB؛ ثبت جدید → +۱؛ حذف از صفحه → DB و جدول
import views.pages.observations_page as obs_page_mod  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    opage = obs_page_mod.ObservationsPage()
    opage.load_observations()
    rows_initial = opage.table.rowCount()
    db_initial = len(ObservationDAL().get_all()) if hasattr(ObservationDAL(), "get_all") else rows_initial
    obs_service.create_observation({**base, 'behavior': 'سازگاری UI و DB'})
    opage.load_observations()
    rows_after_add = opage.table.rowCount()
    target_obs = next(o for o in opage.observations if o.behavior == 'سازگاری UI و DB')
    opage.delete_observation(target_obs)
    rows_after_delete = opage.table.rowCount()
deleted_flag = conn.execute("SELECT is_deleted FROM observations WHERE id = ?", (target_obs.id,)).fetchone()[0]
check("F", "سازگاری داده (بند ۲۳): جدول مشاهدات با DB برابر است؛ ثبت از سرویس + بارگذاری دوباره → +۱ ردیف؛ حذف از صفحه → is_deleted=1 در DB و −۱ ردیف در جدول",
      rows_initial == db_initial and rows_after_add == rows_initial + 1 and deleted_flag == 1
      and rows_after_delete == rows_after_add - 1,
      f"rows {rows_initial}->{rows_after_add}->{rows_after_delete} db_initial={db_initial} flag={deleted_flag}")

# ============================================================
print()
print("=" * 76)
print("بخش G: کد مرده، جهت وابستگی لایه‌ها، لایهٔ سرویس، سیگنال‌های بی‌استفاده")
print("=" * 76)

# --- G1: ماژول‌های مردهٔ حذف‌شده دیگر نیستند و هیچ ارجاعی به آن‌ها نمانده؛ ماژول‌های «منتظر تصمیم» هنوز هستند
REMOVED_DEAD = ["views/pages/assign_teacher_page.py", "views/pages/teacher_students_page.py",
                "utils/cache.py", "utils/competency_helper.py", "models/student_file.py",
                "views/widgets/filter_widget.py", "utils/notification_scheduler.py",
                "services/notification_service.py", "dal/notification_dal.py", "models/notification.py",
                "dal/saved_filter_dal.py", "models/saved_filter.py", "services/advanced_search_service.py",
                "dal/backup_dal.py", "services/school_report_service.py", "dal/screening_tool_dal.py",
                "utils/report_template.py", "models/analytics_models.py"]
# آنچه عمداً مانده: ویجت پیشنهادها (اکنون زنده)، زیرسیستم Screening (لایهٔ گزارش از آن می‌خواند)
PENDING_DECISION = ["views/widgets/recommendation_widget.py", "dal/screening_dal.py", "dal/screening_result_dal.py"]
app_dirs = ["main.py", "views", "views/pages", "views/dialogs", "views/widgets", "services", "dal", "utils", "database", "models", "config"]
app_sources = {}
for d in app_dirs:
    if d.endswith(".py"):
        app_sources[d] = read(d)
        continue
    for fname in os.listdir(d):
        if fname.endswith(".py"):
            app_sources[os.path.join(d, fname)] = read(os.path.join(d, fname))
stale_refs = []
for removed in REMOVED_DEAD:
    dotted = removed[:-3].replace("/", ".")            # مثلاً models.notification
    stem = os.path.basename(removed)[:-3]
    pattern = rf"\b{re.escape(dotted)}\b|\bimport\s+{re.escape(stem)}\b|from\s+\.\s*import\s+{re.escape(stem)}\b"
    for path, src in app_sources.items():
        if re.search(pattern, src):
            stale_refs.append((removed, path))
check("G", "کد مردهٔ تأییدشده (۱۸ ماژول: دو صفحهٔ هرگز-سوارنشده، زیرسیستم اعلان‌ها، فیلترهای ذخیره‌شده، BackupDAL، SchoolReportService، report_template، analytics_models، …) حذف شده و هیچ ارجاعی به آن‌ها در کد نمانده؛ ماژول‌های نگه‌داشته‌شده سر جایشان هستند",
      not any(os.path.exists(p) for p in REMOVED_DEAD) and not stale_refs
      and all(os.path.exists(p) for p in PENDING_DECISION),
      f"stale={stale_refs} missing_pending={[p for p in PENDING_DECISION if not os.path.exists(p)]}")

# --- G2: جهت وابستگی لایه‌ها (بند ۲۸)
FORBIDDEN = {"services": {"views"}, "dal": {"services", "views"}, "models": {"dal", "services", "views"},
             "database": {"services", "views", "dal"}, "config": {"views", "services", "dal", "utils", "database"}}
UTILS_DAL_EXCEPTIONS = {"utils/excel_importer.py", "utils/backup.py", "utils/security.py"}
layer_violations = []
for path, src in app_sources.items():
    layer = path.split("/")[0]
    if layer == "main.py":
        continue
    for node in ast.walk(ast.parse(src)):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods = [node.module]
        for m in mods:
            target = m.split(".")[0]
            if target in FORBIDDEN.get(layer, set()):
                layer_violations.append((path, m))
            if layer == "utils" and target in ("views", "services", "dal") and path not in UTILS_DAL_EXCEPTIONS:
                layer_violations.append((path, m))
raw_db_in_views = [(p, m.group(0)) for p, src in app_sources.items() if p.startswith("views")
                   for m in re.finditer(r"\.execute\(|execute_query\(|get_connection\(\)", src)]
qt_in_services = [p for p, src in app_sources.items() if p.startswith("services") and re.search(r"^\s*(from|import)\s+PySide6", src, re.M)]
check("G", "جهت وابستگی (بند ۲۸): services→views، dal→services/views، models→dal/services، database→services/dal ممنوع و رعایت شده؛ هیچ SQL/اتصال خام در views؛ هیچ import از Qt در services (استثناهای utils→dal مستند: excel_importer، backup، security)",
      not layer_violations and not raw_db_in_views and not qt_in_services,
      f"violations={layer_violations[:5]} raw={raw_db_in_views[:3]} qt={qt_in_services}")

# --- G3: سیگنال‌های سفارشی: هیچ سیگنالی نیست که تعریف شده ولی هرگز emit نشود (کد مرده)
with contextlib.redirect_stdout(io.StringIO()):
    inventory_g = inv.build_report(write=False)
never_emitted = [(r, c, sig) for r, c, sig, ln, e, recv in inventory_g['signals'] if e == 0]
check("G", "هیچ سیگنال سفارشی «تعریف‌شده ولی هرگز emit‌نشده» در views/ نمانده (student_changed و assignment_changed ×۲ حذف شدند؛ BackupWorker.progress اکنون emit می‌شود)",
      not never_emitted, str(never_emitted))

# --- G4: لایهٔ سرویس (بند ۲۹): سرویس‌های زنده منطق دارند؛ فقط NotificationService (زیرسیستم دست‌نیافتنی) اغلب wrapper است
wrapper_services = []
for fname in sorted(os.listdir("services")):
    if not fname.endswith(".py") or fname == "__init__.py":
        continue
    tree_s = ast.parse(read(os.path.join("services", fname)))
    for cls in [n for n in tree_s.body if isinstance(n, ast.ClassDef)]:
        methods = [m for m in cls.body if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")]
        wrappers = 0
        for m in methods:
            body = [st for st in m.body if not (isinstance(st, ast.Expr) and isinstance(getattr(st, "value", None), ast.Constant))]
            if len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.Call) \
                    and "_dal." in ast.unparse(body[0].value.func):
                wrappers += 1
        if methods and wrappers / len(methods) > 0.5:
            wrapper_services.append(cls.name)
check("G", "لایهٔ سرویس (بند ۲۹): هیچ سرویسی صرفاً wrapper ظاهری DAL نیست",
      not wrapper_services, str(wrapper_services))

# ============================================================
print()
print("=" * 76)
print("بخش H: تصمیم‌های باز — کامبوی سال تحصیلی هدر، نقطهٔ ورودی پیوست‌ها، حذف FilterWidget")
print("=" * 76)

from models.academic_year import AcademicYear  # noqa: E402

# --- H1: کامبوی سال تحصیلی هدر واقعاً سال فعال را عوض می‌کند (با تأیید)، رد → برگشت، بایگانی → هشدار
with contextlib.redirect_stdout(io.StringIO()):
    year_dal = AcademicYearDAL()
    active_before = year_dal.get_active()
    new_year = AcademicYear()
    new_year.title, new_year.start_date, new_year.end_date, new_year.is_active = "1406-1407", "1406/07/01", "1407/03/31", 0
    new_year_id = year_dal.create(new_year).id
    archived = AcademicYear()
    archived.title, archived.start_date, archived.end_date, archived.is_active = "1400-1401", "1400/07/01", "1401/03/31", 0
    archived_id = year_dal.create(archived).id
    year_dal.archive(archived_id)
    win.load_academic_years()

    def _combo_index_of(year_id):
        return next(i for i in range(win.year_combo.count()) if win.year_combo.itemData(i) == year_id)

    # ۱) انصراف → هیچ تغییری
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
    win.year_combo.setCurrentIndex(_combo_index_of(new_year_id))
    app.processEvents()
    after_no = year_dal.get_active().id
    combo_after_no = win.year_combo.currentData()
    # ۲) تأیید → سال فعال عوض می‌شود و صفحه‌ها بارگذاری می‌شوند
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    n_msgs = len(ui_msgs)
    win.year_combo.setCurrentIndex(_combo_index_of(new_year_id))
    app.processEvents()
    after_yes = year_dal.get_active().id
    label_after_yes = win.year_label.text()
    switch_msgs = ui_msgs[n_msgs:]
    # ۳) سال بایگانی‌شده → هشدار و برگشت به سال فعال
    n_msgs = len(ui_msgs)
    win.year_combo.setCurrentIndex(_combo_index_of(archived_id))
    app.processEvents()
    after_archived = year_dal.get_active().id
    archived_msgs = ui_msgs[n_msgs:]
    combo_after_archived = win.year_combo.currentData()
    # بازگرداندن سال فعال قبلی برای بقیهٔ بررسی‌ها
    win.year_combo.setCurrentIndex(_combo_index_of(active_before.id))
    app.processEvents()
    restored = year_dal.get_active().id
check("H", "BUG-023 کامبوی سال هدر: انصراف → بدون تغییر و برگشت کامبو؛ تأیید → سال فعال در DB عوض می‌شود، برچسب و صفحه‌ها به‌روز؛ سال بایگانی‌شده → هشدار و برگشت (قبلاً فقط برچسب عوض می‌شد)",
      after_no == active_before.id and combo_after_no == active_before.id
      and after_yes == new_year_id and "1406-1407" in label_after_yes and not [m for m in switch_msgs if m[0] == "crit"]
      and after_archived == new_year_id and archived_msgs and archived_msgs[-1][0] == "warn" and combo_after_archived == new_year_id
      and restored == active_before.id,
      f"no={after_no} yes={after_yes} label={label_after_yes!r} archived={after_archived} msgs={archived_msgs[-1:]} restored={restored}")

# --- H2: دکمهٔ «📎 پیوست‌ها» در پروندهٔ دانش‌آموز، دیالوگ پیوست را برای همان دانش‌آموز باز می‌کند
import views.dialogs.attachment_dialog as attachment_dialog_mod  # noqa: E402

opened = []


class _RecorderDialog:
    def __init__(self, entity_type, entity_id, parent=None):
        opened.append((entity_type, entity_id, type(parent).__name__))

    def exec(self):
        opened.append("exec")
        return 0


real_attachment_dialog = attachment_dialog_mod.AttachmentDialog
attachment_dialog_mod.AttachmentDialog = _RecorderDialog
try:
    with contextlib.redirect_stdout(io.StringIO()):
        profile_page = win.students_page.profile_page
        profile_page.set_student_id(form_student.id)
        profile_page.open_attachments()
        profile_page.student_id = None
        n_msgs = len(ui_msgs)
        profile_page.open_attachments()
        no_student_msgs = ui_msgs[n_msgs:]
        profile_page.set_student_id(form_student.id)
finally:
    attachment_dialog_mod.AttachmentDialog = real_attachment_dialog
check("H", "BUG-027 دکمهٔ «📎 پیوست‌ها» در پروندهٔ دانش‌آموز: AttachmentDialog('student', شناسهٔ همان دانش‌آموز) باز می‌شود؛ بدون دانش‌آموز → هشدار (قبلاً هیچ نقطهٔ ورودی نبود)",
      opened == [("student", form_student.id, "StudentProfilePage"), "exec"]
      and profile_page.btn_attachments.text().startswith("📎")
      and no_student_msgs and no_student_msgs[-1][0] == "warn",
      f"opened={opened}")

# ============================================================
print()
print("=" * 76)
print("بخش J: داوری سوم مدیر پروژه — مرحلهٔ ۱: رد/تکمیل پیشنهاد (BUG-NEW-01) و کنتراست «اقدام پیشنهادی» (BUG-NEW-03)")
print("=" * 76)

from PySide6.QtWidgets import QInputDialog as _QInputDialog  # noqa: E402

from services.recommendation_service import RecommendationService  # noqa: E402
from views.widgets.recommendation_widget import RecommendationWidget  # noqa: E402

rec_service = RecommendationService()
with contextlib.redirect_stdout(io.StringIO()):
    j_widget = RecommendationWidget()
    j_widget.set_profile_id(form_pid)
    j_recs = rec_service.generate_recommendations(form_pid) or []
    j_widget.load_recommendations()
    pending = [r for r in j_widget.recommendations if r.status == 'pending']
if len(pending) < 2:
    with contextlib.redirect_stdout(io.StringIO()):
        # پیشنهادهای بیشتر برای سناریوی رد/تکمیل
        j_recs = rec_service.generate_recommendations(form_pid) or []
        j_widget.load_recommendations()
        pending = [r for r in j_widget.recommendations if r.status == 'pending']


def _rec_status(rec_id):
    row = conn.execute("SELECT status, feedback_notes, feedback FROM recommendations WHERE id = ?", (rec_id,)).fetchone()
    return tuple(row) if row else None


rec_src = read("views/widgets/recommendation_widget.py")
if len(pending) >= 2:
    to_reject, to_complete = pending[0], pending[1]
    # ۱) انصراف از دیالوگ ورودی → بدون تغییر
    _QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
    with contextlib.redirect_stdout(io.StringIO()):
        j_widget.reject_recommendation(to_reject)
    unchanged = _rec_status(to_reject.id)
    # ۲) رد با دلیل → status = rejected و یادداشت ذخیره می‌شود
    _QInputDialog.getText = staticmethod(lambda *a, **k: ("دلیل آزمایشی رد", True))
    n_msgs = len(ui_msgs)
    with contextlib.redirect_stdout(io.StringIO()):
        j_widget.reject_recommendation(to_reject)
    rejected = _rec_status(to_reject.id)
    reject_msgs = ui_msgs[n_msgs:]
    # ۳) اجرا سپس تکمیل با بازخورد → status = completed
    _QInputDialog.getText = staticmethod(lambda *a, **k: ("بازخورد آزمایشی", True))
    n_msgs = len(ui_msgs)
    with contextlib.redirect_stdout(io.StringIO()):
        j_widget.accept_recommendation(to_complete)
        j_widget.implement_recommendation(to_complete)
        j_widget.complete_recommendation(to_complete)
    completed = _rec_status(to_complete.id)
    complete_msgs = ui_msgs[n_msgs:]
    check("J", "BUG-NEW-01: «رد پیشنهاد» و «تکمیل پیشنهاد» با QInputDialog.getText کار می‌کنند — انصراف → بدون تغییر؛ رد با دلیل → status=rejected + یادداشت؛ پذیرش→اجرا→تکمیل با بازخورد → status=completed (قبلاً هر دو با AttributeError می‌شکستند)",
          unchanged and unchanged[0] == 'pending'
          and rejected and rejected[0] == 'rejected' and rejected[1] == "دلیل آزمایشی رد"
          and completed and completed[0] == 'completed' and completed[2] == "بازخورد آزمایشی"
          and not [m for m in reject_msgs + complete_msgs if m[0] == 'crit']
          and "QMessageBox.getText" not in rec_src and "QInputDialog.getText" in rec_src,
          f"unchanged={unchanged} rejected={rejected} completed={completed} msgs={[m for m in reject_msgs + complete_msgs if m[0] != 'info']}")
else:
    check("J", "BUG-NEW-01: رد/تکمیل پیشنهاد (به اندازهٔ کافی پیشنهاد در انتظار تولید نشد)", False, f"pending={len(pending)} recs={len(j_recs)}")

action_block = rec_src.split('action_label.setStyleSheet("""')[1].split('""")')[0]
check("J", "BUG-NEW-03: برچسب «اقدام پیشنهادی» دیگر هم‌رنگ زمینه نیست (متن طلایی روی سرمه‌ای)؛ اسکن کنتراست اکنون استایل‌های چندخطی بدون selector را هم می‌بیند (۴ نشان نامرئی داشبورد هم اصلاح شد)",
      "color: #F4C542;" in action_block and "background-color: #0B2E4F;" in action_block
      and not re.search(r'color: #66BB6A;\n\s+background-color: #66BB6A;', read("views/pages/dashboard_page.py"))
      and not re.search(r'color: #0B2E4F;\n\s+background-color: #0B2E4F;', read("views/pages/dashboard_page.py")),
      "")

# ============================================================
print()
print("=" * 76)
print("بخش K: داوری سوم — مرحلهٔ ۲: Migrationهای واقعاً اتمیک (BUG-NEW-02)")
print("=" * 76)

import glob as _glob  # noqa: E402

# --- K1: هیچ migrationی خودش commit/rollback نمی‌کند
mig_files = sorted(_glob.glob("database/migrations/migration_v*.py"))
self_commit = [(f, i + 1) for f in mig_files for i, line in enumerate(read(f).splitlines())
               if re.match(r"^\s*connection\.(commit|rollback)\(\)", line)]
check("K", "BUG-NEW-02: هیچ‌یک از ۹ فایل migration خودش connection.commit()/rollback() ندارد؛ مالک تراکنش فقط MigrationManager است",
      mig_files and not self_commit and "def _begin_transaction" in read("database/migrations/manager.py"),
      f"files={len(mig_files)} self_commit={self_commit}")

# --- K2: اتمیک‌بودن با یک فایل migration واقعی (نه شیء ساختگی): چند DDL/DML و شکست وسط کار → هیچ‌چیز نمی‌ماند
atomic_dir = tempfile.mkdtemp(prefix="r16_atomic_", dir=TMP)
ATOMIC_MIGRATION_SRC = "\n".join([
    "def upgrade(connection):",
    "    cursor = connection.cursor()",
    "    cursor.execute(\"CREATE TABLE atomic_a (id INTEGER PRIMARY KEY, v TEXT)\")",
    "    cursor.execute(\"INSERT INTO atomic_a (v) VALUES ('x')\")",
    "    cursor.execute(\"CREATE INDEX idx_atomic_a_v ON atomic_a (v)\")",
    "    cursor.execute(\"CREATE TABLE atomic_b (id INTEGER PRIMARY KEY)\")",
    "    raise RuntimeError('failure injected after 4 statements')",
    "",
    "",
    "def downgrade(connection):",
    "    connection.execute(\"DROP TABLE IF EXISTS atomic_b\")",
    "    connection.execute(\"DROP TABLE IF EXISTS atomic_a\")",
    "",
])
_write(atomic_dir, "migration_v1.py", ATOMIC_MIGRATION_SRC)
atomic_db = os.path.join(TMP, "atomic.db")
atomic_conn = sqlite3.connect(atomic_db)
atomic_modules = mm._discover_migrations(directory=atomic_dir)
mm._discover_migrations = lambda: atomic_modules
atomic_error = None
try:
    mm.MigrationManager.migrate(atomic_conn, 1)
except Exception as e:
    atomic_error = e
finally:
    mm._discover_migrations = real_discover
leftover = {r[0] for r in atomic_conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'atomic_%' OR name LIKE 'idx_atomic%'").fetchall()}
atomic_version = mm.MigrationManager.get_current_version(atomic_conn)
# همان فایل بدون شکست → همه‌چیز یک‌جا commit می‌شود (نام ماژول تازه تا کش import مزاحم نشود)
_write(atomic_dir, "migration_v1.py", ATOMIC_MIGRATION_SRC.replace(
    "    raise RuntimeError('failure injected after 4 statements')\n", ""))
atomic_modules = mm._discover_migrations(directory=atomic_dir)
mm._discover_migrations = lambda: atomic_modules
try:
    mm.MigrationManager.migrate(atomic_conn, 1)
finally:
    mm._discover_migrations = real_discover
after_fix = {r[0] for r in atomic_conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'atomic_%' OR name LIKE 'idx_atomic%'").fetchall()}
atomic_final_version = mm.MigrationManager.get_current_version(atomic_conn)
atomic_conn.close()
check("K", "فایل migration واقعی که پس از ۴ دستور DDL/DML شکست می‌خورد: هیچ جدول/ایندکس/ردیفی نمی‌ماند، نسخه ۰ می‌ماند، تراکنش باز نمی‌ماند؛ همان فایل بدون شکست → همه یک‌جا اعمال و نسخه ۱",
      isinstance(atomic_error, mm.MigrationStepError) and not leftover and atomic_version == 0
      and after_fix == {"atomic_a", "idx_atomic_a_v", "atomic_b"} and atomic_final_version == 1,
      f"error={atomic_error} leftover={leftover} version={atomic_version} after_fix={after_fix} final={atomic_final_version}")

# --- K3: زنجیرهٔ واقعی ۹ migration بدون commit داخلی: ۵→۹ در راه‌اندازی، ۹→۸→۹ با Manager
with contextlib.redirect_stdout(io.StringIO()):
    mm.MigrationManager.set_version(conn, 5)
    db.close_all()
    conn = db.get_connection(user_id=1)
    chain_version = db.get_db_version()
    raw_chain = sqlite3.connect(TEST_DB)
    mm.MigrationManager.migrate(raw_chain, 8)
    down_version = mm.MigrationManager.get_current_version(raw_chain)
    mm.MigrationManager.migrate(raw_chain, 9)
    up_version = mm.MigrationManager.get_current_version(raw_chain)
    raw_in_tx = raw_chain.in_transaction
    raw_chain.close()
    conn = db.get_connection(user_id=1)
check("K", "زنجیرهٔ واقعی migrationها بدون commit داخلی: دیتابیس اجبارشده به ۵ در راه‌اندازی → ۹؛ بازگشت ۹→۸ و ارتقای دوباره → ۹؛ هیچ تراکنشی باز نمی‌ماند",
      chain_version == 9 and down_version == 8 and up_version == 9 and not raw_in_tx and not conn.in_transaction,
      f"reopen={chain_version} down={down_version} up={up_version}")

# --- K4: مسیر ترمیم (_heal_schema) که migrationهای idempotent را مستقیم اجرا می‌کند: تراکنش صریح + commit/rollback
import database.migrations.migration_v7 as migration_v7  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    conn.execute("DROP TABLE IF EXISTS backups")
    conn.commit()
    real_v7_upgrade = migration_v7.upgrade

    def _v7_boom(connection):
        real_v7_upgrade(connection)                       # DDL واقعی (ساخت backups و …)
        connection.execute("CREATE TABLE heal_probe_tmp (id INTEGER)")
        raise RuntimeError("heal failure injected")

    migration_v7.upgrade = _v7_boom
    try:
        db.close_all()
        conn = db.get_connection(user_id=1)             # راه‌اندازی با ترمیم شکست‌خورده
    finally:
        migration_v7.upgrade = real_v7_upgrade
    tables_after_fail = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('backups', 'heal_probe_tmp')").fetchall()}
    in_tx_after_fail = conn.in_transaction
    db.close_all()
    conn = db.get_connection(user_id=1)                 # راه‌اندازی سالم → ترمیم commit می‌شود
    tables_after_ok = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('backups', 'heal_probe_tmp')").fetchall()}
check("K", "مسیر ترمیم ساختار (_heal_schema): شکست وسط migration_v7 → همهٔ DDL همان گام برمی‌گردد (نه backups نه جدول کمکی)، برنامه بالا می‌آید و تراکنش باز نمی‌ماند؛ راه‌اندازی بعدی → backups دوباره ساخته و commit می‌شود",
      tables_after_fail == set() and not in_tx_after_fail and tables_after_ok == {"backups"} and not conn.in_transaction,
      f"after_fail={tables_after_fail} in_tx={in_tx_after_fail} after_ok={tables_after_ok}")

# ============================================================
print()
print("=" * 76)
print("بخش L: داوری سوم — مرحلهٔ ۳: ثبت مداخله از روی پیشنهاد با پیش‌پرکردن و پیوند (BUG-NEW-04)")
print("=" * 76)

import views.dialogs.intervention_form as intervention_form_mod  # noqa: E402
import views.pages.student_profile_page as profile_mod  # noqa: E402

from services.recommendation_service import RecommendationService  # noqa: E402

rec_service = RecommendationService()
with contextlib.redirect_stdout(io.StringIO()):
    l_page = win.students_page.profile_page
    l_page.set_student_id(form_student.id)
    l_widget = l_page.recommendation_widget
    l_widget.load_recommendations()
    l_pending = [r for r in l_widget.recommendations if r.status in ('pending', 'accepted')]
    if not l_pending:
        rec_service.generate_recommendations(l_page.profile_id)
        l_widget.load_recommendations()
        l_pending = [r for r in l_widget.recommendations if r.status in ('pending', 'accepted')]

captured_forms = []
real_intervention_form = profile_mod.InterventionForm


class _PrefilledFormProbe(real_intervention_form):
    """همان فرم واقعی؛ فقط exec را با «پرکردن باقی فیلدها و ذخیره» شبیه‌سازی می‌کند"""

    def exec(self):
        captured_forms.append(self)
        _combo_pick(self.student_combo, form_student.id)
        _combo_pick(self.observer_combo)
        self.save_intervention()
        return self.result()


profile_mod.InterventionForm = _PrefilledFormProbe
try:
    if l_pending:
        l_rec = l_pending[0]
        int_before = _count("interventions")
        n_msgs = len(ui_msgs)
        with contextlib.redirect_stdout(io.StringIO()):
            l_widget.request_intervention(l_rec)
            app.processEvents()
        int_after = _count("interventions")
        form_used = captured_forms[0] if captured_forms else None
        new_iid = getattr(form_used, 'saved_intervention_id', None)
        int_row = conn.execute("SELECT type, description, goal, student_profile_id FROM interventions WHERE id = ?",
                               (new_iid,)).fetchone() if new_iid else None
        rec_row = conn.execute("SELECT status, metadata FROM recommendations WHERE id = ?", (l_rec.id,)).fetchone()
        rec_meta = json.loads(rec_row[1]) if rec_row and rec_row[1] else {}
        with contextlib.redirect_stdout(io.StringIO()):
            l_widget.load_recommendations()
        reloaded = next((r for r in l_widget.recommendations if r.id == l_rec.id), None)
        expected_type = l_rec.suggested_intervention_type
        l_msgs = [m for m in ui_msgs[n_msgs:] if m[0] != 'info']
        check("L", "BUG-NEW-04: «ثبت مداخله» از روی پیشنهاد → فرم مداخله با نوع/شرح/هدف پیشنهاد پیش‌پر می‌شود → پس از ذخیره، ردیف interventions با همان نوع ساخته می‌شود، پیشنهاد «اجراشده» و metadata.intervention_id به مداخله اشاره می‌کند، تب‌ها تازه می‌شوند",
              form_used is not None and form_used.recommendation_id == l_rec.id
              and form_used.prefill.get('type') == expected_type
              and int_after == int_before + 1 and int_row is not None
              and (expected_type is None or int_row[0] == expected_type)
              and int_row[3] == l_page.profile_id
              and (int_row[1] or '').strip() != '' and (int_row[2] or '').strip() != ''
              and rec_row and rec_row[0] == 'implemented' and rec_meta.get('intervention_id') == new_iid
              and reloaded is not None and reloaded.linked_intervention_id == new_iid
              and not l_msgs and form_used.recommendation_link_error is None
              and l_page.inter_table.rowCount() == conn.execute(
                  "SELECT COUNT(*) FROM interventions WHERE student_profile_id = ? AND is_deleted = 0",
                  (l_page.profile_id,)).fetchone()[0],
              f"prefill={getattr(form_used, 'prefill', None)} rec_id={getattr(form_used, 'recommendation_id', None)} "
              f"int {int_before}->{int_after} row={tuple(int_row) if int_row else None} rec={tuple(rec_row) if rec_row else None} "
              f"meta={rec_meta} msgs={l_msgs}")
    else:
        check("L", "BUG-NEW-04: ثبت مداخله از روی پیشنهاد (پیشنهادی در انتظار/پذیرفته وجود نداشت)", False, "")
finally:
    profile_mod.InterventionForm = real_intervention_form

# --- L2: شکست پیوند، ثبت مداخله را باطل نمی‌کند ولی صریح اعلام می‌شود
with contextlib.redirect_stdout(io.StringIO()):
    l_widget.load_recommendations()
    l_pending2 = [r for r in l_widget.recommendations if r.status in ('pending', 'accepted')]
    if not l_pending2:
        rec_service.generate_recommendations(l_page.profile_id)
        l_widget.load_recommendations()
        l_pending2 = [r for r in l_widget.recommendations if r.status in ('pending', 'accepted')]
    if not l_pending2:
        # پیشنهاد دستی برای سناریوی شکست پیوند
        from models.recommendation import Recommendation as _Rec
        _r = _Rec()
        _r.student_profile_id, _r.title, _r.description = l_page.profile_id, "پیشنهاد آزمون پیوند", "شرح"
        _r.category, _r.priority, _r.status = "behavioral", "medium", "pending"
        _r.suggested_intervention_type = "parent_call"
        rec_service.recommendation_dal.create(_r)
        l_widget.load_recommendations()
        l_pending2 = [r for r in l_widget.recommendations if r.status in ('pending', 'accepted')]
if l_pending2:
    real_implement = RecommendationService.implement_recommendation

    def _implement_fails(self, *a, **k):
        raise RuntimeError("link failure injected")

    RecommendationService.implement_recommendation = _implement_fails
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            l_form2 = intervention_form_mod.InterventionForm(
                student_id=form_student.id, prefill={'type': 'parent_call', 'description': 'شرح از پیشنهاد', 'goal': 'هدف'},
                recommendation_id=l_pending2[0].id)
            _combo_pick(l_form2.student_combo, form_student.id)
            _combo_pick(l_form2.observer_combo)
            n_msgs = len(ui_msgs)
            l_form2.save_intervention()
    finally:
        RecommendationService.implement_recommendation = real_implement
    saved2 = conn.execute("SELECT type, description FROM interventions WHERE id = ?", (l_form2.saved_intervention_id,)).fetchone() if l_form2.saved_intervention_id else None
    rec2 = conn.execute("SELECT status FROM recommendations WHERE id = ?", (l_pending2[0].id,)).fetchone()
    info_msg = next((m[1] for m in ui_msgs[n_msgs:] if m[0] == 'info'), '')
    check("L", "شکست پیوند پیشنهاد: مداخله ثبت می‌شود (نوع/شرح از پیشنهاد)، پیشنهاد دست‌نخورده می‌ماند و پیام صریحاً ⚠️ می‌گوید وضعیت پیشنهاد به‌روز نشد (نه موفقیت ظاهری)",
          saved2 is not None and saved2[0] == 'parent_call' and saved2[1] == 'شرح از پیشنهاد'
          and rec2 and rec2[0] in ('pending', 'accepted') and '⚠️' in info_msg
          and l_form2.recommendation_link_error == 'link failure injected' and l_form2.result() == QDialog.DialogCode.Accepted,
          f"saved={tuple(saved2) if saved2 else None} rec={tuple(rec2) if rec2 else None} msg={info_msg[:90]!r}")
else:
    check("L", "شکست پیوند پیشنهاد (پیشنهادی در انتظار وجود نداشت)", False, "")

# ============================================================
print()
print("=" * 76)
print("بخش I: تکمیل باقی‌مانده‌ها — تب پیشنهادها، خروجی گزارش کلاس/معلم، ویرایش اختصاص، CHECK، مخزن، خروج خودکار")
print("=" * 76)

import subprocess as _subprocess  # noqa: E402

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

# --- I1: تب «💡 پیشنهادها» در پروندهٔ دانش‌آموز: هم‌گام با پرونده، Generate → رکوردهای recommendations → نمایش/خلاصه
import views.pages.student_profile_page as profile_mod  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    prof_page = win.students_page.profile_page
    prof_page.set_student_id(form_student.id)
    rec_widget = prof_page.recommendation_widget
    tab_titles = [prof_page.tabs.tabText(i) for i in range(prof_page.tabs.count())]
    rec_before = conn.execute("SELECT COUNT(*) FROM recommendations WHERE student_profile_id = ? AND is_deleted = 0",
                              (prof_page.profile_id,)).fetchone()[0]
    n_msgs = len(ui_msgs)
    rec_widget.generate_recommendations()
    rec_after = conn.execute("SELECT COUNT(*) FROM recommendations WHERE student_profile_id = ? AND is_deleted = 0",
                             (prof_page.profile_id,)).fetchone()[0]
    # ویجت پس از تولید، پیشنهادهای «فعال» (در انتظار/پذیرفته‌شده) را نشان می‌دهد
    active_after = conn.execute("SELECT COUNT(*) FROM recommendations WHERE student_profile_id = ? AND is_deleted = 0 "
                                "AND status IN ('pending', 'accepted')", (prof_page.profile_id,)).fetchone()[0]
    displayed = len(rec_widget.recommendations)
    gen_msgs = ui_msgs[n_msgs:]
    # درخواست مداخله از روی پیشنهاد → فرم مداخلهٔ همین صفحه
    opened_forms = []
    real_form = profile_mod.InterventionForm

    class _FormRecorder:
        def __init__(self, *a, **k):
            opened_forms.append(k.get('student_id', a[1] if len(a) > 1 else None))

        def exec(self):
            return 0

        def __getattr__(self, name):
            return lambda *a, **k: None

    profile_mod.InterventionForm = _FormRecorder
    try:
        rec_widget.intervention_requested.emit({'title': 'x'})
        app.processEvents()
    finally:
        profile_mod.InterventionForm = real_form
check("I", "تب «💡 پیشنهادها» در پروندهٔ دانش‌آموز: ویجت با پروندهٔ جاری هم‌گام است؛ Generate → رکوردهای recommendations در DB و همان تعداد در نمایش؛ «ثبت مداخله» از روی پیشنهاد فرم مداخله را باز می‌کند (قبلاً ویجت هیچ‌جا سوار نبود)",
      any("پیشنهادها" in t for t in tab_titles) and rec_widget.profile_id == prof_page.profile_id
      and rec_after > rec_before and displayed == active_after and gen_msgs and gen_msgs[-1][0] == "info"
      and not [m for m in gen_msgs if m[0] == "crit"] and len(opened_forms) == 1,
      f"tabs={tab_titles[-2:]} rec {rec_before}->{rec_after} active={active_after} displayed={displayed} msgs={gen_msgs[-1:]} forms={opened_forms}")

# --- I2: خروجی PDF/Excel گزارش کلاس، گزارش معلم و عملکرد معلم از مسیر صفحه (فایل واقعی)
report_exports = {}
with contextlib.redirect_stdout(io.StringIO()):
    # کلاس: پروندهٔ دانش‌آموز آزمون در کلاس «الف» پایهٔ ۲ است؛ کلاس با همان نام/پایه در سال فعال
    active_year = AcademicYearDAL().get_active()
    cls_row = conn.execute("SELECT id FROM classes WHERE name = 'الف' AND grade = 2 AND academic_year_id = ? AND is_deleted = 0",
                           (active_year.id,)).fetchone()
    if cls_row is None:
        c = ClassModel()
        c.name, c.grade, c.academic_year_id, c.capacity, c.is_active = "الف", 2, active_year.id, 30, 1
        class_id_for_report = ClassDAL().create(c).id
    else:
        class_id_for_report = cls_row[0]
    crp = win.reports_page.class_report_page
    crp.load_classes()
    idx = crp.class_combo.findData(class_id_for_report)
    crp.class_combo.setCurrentIndex(idx)
    crp.on_class_changed(idx)
    crp.start_date.set_date("1405/01/01")
    crp.end_date.set_date("1405/12/29")
    crp.generate_report()
    class_report_ok = crp.current_report is not None
    report_exports["class_pdf"] = _export_via(crp, "export_pdf", os.path.join(TMP, "class_report.pdf"))
    report_exports["class_xlsx"] = _export_via(crp, "export_excel", os.path.join(TMP, "class_report.xlsx"))
    # معلم (اختصاص‌داده‌شده در §D)
    trp = win.reports_page.teacher_report_page
    trp.load_teachers()
    tidx = trp.teacher_combo.findData(teacher_id)
    trp.teacher_combo.setCurrentIndex(tidx)
    trp.start_date.set_date("1405/01/01")
    trp.end_date.set_date("1405/12/29")
    trp.generate_report()
    teacher_report_ok = trp.current_report is not None
    report_exports["teacher_pdf"] = _export_via(trp, "export_pdf", os.path.join(TMP, "teacher_report.pdf"))
    report_exports["teacher_xlsx"] = _export_via(trp, "export_excel", os.path.join(TMP, "teacher_report.xlsx"))
    # عملکرد معلم (نیاز به مشاهدهٔ ثبت‌شده توسط خودِ معلم در بازه دارد)
    obs_service.create_observation({'student_id': form_student.id, 'staff_id': teacher_id, 'competency_id': comps[0].id,
                                    'observation_date': '1405/07/15', 'behavior_type': 'مثبت', 'severity': 2,
                                    'behavior': 'مشاهدهٔ معلم برای گزارش عملکرد'})
    tpp = win.reports_page.teacher_performance_page
    tpp.load_teachers()
    pidx = tpp.teacher_combo.findData(teacher_id)
    tpp.teacher_combo.setCurrentIndex(pidx)
    tpp.on_teacher_changed(pidx)
    tpp.start_date.set_date("1405/01/01")
    tpp.end_date.set_date("1405/12/29")
    tpp.generate_report()
    perf_report_ok = tpp.current_report is not None
    report_exports["performance_pdf"] = _export_via(tpp, "export_pdf", os.path.join(TMP, "teacher_performance.pdf"))
check("I", "گزارش کلاس، گزارش معلم و عملکرد معلم از مسیر صفحه تولید می‌شوند و خروجی PDF/Excel آن‌ها فایل واقعی و معتبر است (قبلاً NOT_TESTED)",
      class_report_ok and teacher_report_ok and perf_report_ok and all(v[0] for v in report_exports.values()),
      f"class={class_report_ok} teacher={teacher_report_ok} perf={perf_report_ok} failed={ {k: v[1] for k, v in report_exports.items() if not v[0]} }")

# --- I3: حالت ویرایش AssignTeacherDialog: تغییر معلم → ردیف teacher_assignments به‌روز می‌شود
from dal.teacher_assignment_dal import TeacherAssignmentDAL  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    _t2 = Staff()
    _t2.full_name, _t2.role = "معلم دوم", "teacher"
    teacher2_id = StaffDAL().create(_t2).id
    assignment_id = conn.execute("SELECT id FROM teacher_assignments WHERE student_id = ? AND is_deleted = 0 ORDER BY id DESC LIMIT 1",
                                 (form_student.id,)).fetchone()[0]
    edit_dlg = AssignTeacherDialog(assignment_id=assignment_id)
    loaded_teacher = edit_dlg.teacher_combo.currentData()
    _combo_pick(edit_dlg.teacher_combo, teacher2_id)
    n_msgs = len(ui_msgs)
    edit_dlg.save_assignment()
saved_row = conn.execute("SELECT staff_id, student_id FROM teacher_assignments WHERE id = ?", (assignment_id,)).fetchone()
check("I", "AssignTeacherDialog در حالت ویرایش: معلم فعلی بارگذاری می‌شود، تغییر معلم → همان ردیف teacher_assignments به‌روز می‌شود (قبلاً NOT_TESTED)",
      loaded_teacher == teacher_id and tuple(saved_row) == (teacher2_id, form_student.id)
      and edit_dlg.result() == QDialog.DialogCode.Accepted and not [m for m in ui_msgs[n_msgs:] if m[0] == "crit"],
      f"loaded={loaded_teacher} row={tuple(saved_row) if saved_row else None} msgs={ui_msgs[n_msgs:][-1:]}")

# ============================================================
print()
print("=" * 76)
print("بخش M: بازبینی نهایی — پایداری اطلاعات خانوادگی دانش‌آموز (BUG-GUI-02)")
print("=" * 76)

# --- M1: جای قانونی داده: ستون‌های خانوادگی در students وجود ندارند و
#         مسیر رسمی، جدول family_contexts است
_students_cols = {row[1] for row in conn.execute("PRAGMA table_info(students)").fetchall()}
_family_cols = {row[1] for row in conn.execute("PRAGMA table_info(family_contexts)").fetchall()}
_shadow_in_students = {"siblings_brothers", "siblings_sisters", "living_status"} & _students_cols
_required_family_cols = {"student_profile_id", "siblings_brothers", "siblings_sisters", "guardian_status"}
check("M", "جای قانونی داده: جدول students هیچ ستون خانوادگی ندارد و family_contexts ستون‌های لازم (پرونده، برادر، خواهر، وضعیت سرپرستی/زندگی) را دارد",
      not _shadow_in_students and _required_family_cols <= _family_cols,
      f"shadow_in_students={sorted(_shadow_in_students)} family_missing={sorted(_required_family_cols - _family_cols)}")

# --- M2: مدل Student دیگر نسخهٔ سایه ندارد؛ مدل FamilyContext نگاشت
#         «وضعیت زندگی» فرم را به guardian_status دارد
from models.family_context import FamilyContext  # noqa: E402
from models.student import Student  # noqa: E402

_probe_student = Student()
_shadow_model_fields = [name for name in ("siblings_brothers", "siblings_sisters", "living_status")
                        if hasattr(_probe_student, name)]
_probe_family = FamilyContext()
_probe_family.living_status = "فقط با مادر"
_map_ok = (_probe_family.guardian_status == FamilyContext.GUARDIAN_MOTHER
           and _probe_family.living_status == "فقط با مادر")
_probe_family.living_status = "با عمه"          # مقدار ناشناخته نباید پاک شود
_unknown_ok = _probe_family.guardian_status == "با عمه" and _probe_family.living_status == "با عمه"
check("M", "مدل: Student هیچ فیلد سایه‌ای ندارد؛ FamilyContext «وضعیت زندگی» فرم را به guardian_status نگاشت می‌کند و مقدار ناشناخته را پاک نمی‌کند",
      not _shadow_model_fields and _map_ok and _unknown_ok,
      f"shadow={_shadow_model_fields} map={_map_ok} unknown_kept={_unknown_ok}")

# --- M3: مسیر واقعی فرم: ثبت → ذخیره در family_contexts → بازخوانی در فرم
#         → ویرایش → همان ردیف به‌روز می‌شود (بدون ردیف تکراری)
from views.dialogs.student_form import StudentForm  # noqa: E402

_form_student = Student()
_form_student.first_name = "خانوادگی"
_form_student.last_name = "فرم"
_form_student.national_code = "5555555555"
_form_student = StudentDAL().create(_form_student)

_family_profile = StudentAcademicProfile()
_family_profile.student_id = _form_student.id
_family_profile.academic_year_id = active_year.id
_family_profile.grade = 3
_family_profile.class_name = "ط"
_family_profile.status = "active"
_family_profile = StudentAcademicProfileDAL().create(_family_profile)

_family_detail = ""
try:
    with contextlib.redirect_stdout(io.StringIO()):
        create_form = StudentForm(student=StudentDAL().get_by_id(_form_student.id))
    create_form.brothers_spin.setValue(2)
    create_form.sisters_spin.setValue(1)
    create_form.living_status_combo.setCurrentText("فقط با مادر")
    _msgs_before = len(ui_msgs)
    with contextlib.redirect_stdout(io.StringIO()):
        create_form.save_student()

    _row = conn.execute(
        "SELECT id, student_profile_id, guardian_status, siblings_brothers, siblings_sisters "
        "FROM family_contexts WHERE student_profile_id = ?", (_family_profile.id,)).fetchone()
    _n_rows_after_create = conn.execute(
        "SELECT COUNT(*) FROM family_contexts WHERE student_profile_id = ?",
        (_family_profile.id,)).fetchone()[0]

    # بازخوانی در فرم (بدون هیچ کوئری دستی) — همان چیزی که کاربر می‌بیند
    with contextlib.redirect_stdout(io.StringIO()):
        reopen_form = StudentForm(student=StudentDAL().get_by_id(_form_student.id))
    _read_back = (reopen_form.brothers_spin.value(), reopen_form.sisters_spin.value(),
                  reopen_form.living_status_combo.currentText())

    # ویرایش مقادیر → همان ردیف به‌روز شود، نه ردیف تازه
    reopen_form.brothers_spin.setValue(0)
    reopen_form.sisters_spin.setValue(3)
    reopen_form.living_status_combo.setCurrentText("با پدربزرگ و مادربزرگ")
    with contextlib.redirect_stdout(io.StringIO()):
        reopen_form.save_student()
    _n_rows_after_edit = conn.execute(
        "SELECT COUNT(*) FROM family_contexts WHERE student_profile_id = ?",
        (_family_profile.id,)).fetchone()[0]
    _row_after_edit = conn.execute(
        "SELECT id, guardian_status, siblings_brothers, siblings_sisters "
        "FROM family_contexts WHERE student_profile_id = ?", (_family_profile.id,)).fetchone()

    # مدل Student نباید مقدار خانوادگی حمل کند (مسیر سایهٔ قبلی)
    _shadow_on_saved = [name for name in ("siblings_brothers", "siblings_sisters", "living_status")
                        if hasattr(create_form.student, name)]

    _family_detail = (f"row={tuple(_row) if _row else None} rows={_n_rows_after_create} "
                      f"read_back={_read_back} after_edit={tuple(_row_after_edit) if _row_after_edit else None} "
                      f"rows_edit={_n_rows_after_edit} shadow={_shadow_on_saved} "
                      f"msg={ui_msgs[_msgs_before:_msgs_before + 1]}")
    check("M", "فرم دانش‌آموز: ذخیره → ردیف family_contexts با همان مقدارها ساخته می‌شود؛ بازکردن دوبارهٔ فرم همان‌ها را از DB نشان می‌دهد؛ ویرایش فقط همان ردیف را به‌روز می‌کند (بدون ردیف تکراری و بدون فیلد سایه روی Student)",
          _row is not None and _row['guardian_status'] == FamilyContext.GUARDIAN_MOTHER
          and _row['siblings_brothers'] == 2 and _row['siblings_sisters'] == 1
          and _n_rows_after_create == 1
          and _read_back == (2, 1, "فقط با مادر")
          and _n_rows_after_edit == 1
          and _row_after_edit['id'] == _row['id']
          and _row_after_edit['guardian_status'] == FamilyContext.GUARDIAN_GRANDPARENTS
          and _row_after_edit['siblings_brothers'] == 0 and _row_after_edit['siblings_sisters'] == 3
          and not _shadow_on_saved
          and any(kind == "info" for kind, _ in ui_msgs[_msgs_before:]),
          _family_detail)
except Exception as _family_exc:
    check("M", "فرم دانش‌آموز: ذخیره/بازخوانی/ویرایش اطلاعات خانوادگی از مسیر واقعی فرم", False,
          f"{type(_family_exc).__name__}: {_family_exc} {_family_detail}")

# --- M4: پایداری پس از «راه‌اندازی دوباره»: اتصال بسته و دوباره باز می‌شود،
#         و داده با همین شناسه از DB خوانده می‌شود (بدون حافظهٔ درون‌برنامه‌ای)
_restart_ok = False
_restart_detail = ""
try:
    dbc.DatabaseConnection().close_all()
    # اتصال تازه (مثل بازکردن دوبارهٔ برنامه)؛ همان اتصال ماژول هم تازه می‌شود
    # تا بررسی‌های بعدی روی اتصال بسته اجرا نشوند.
    conn = dbc.DatabaseConnection().get_connection(user_id=1)
    _restart_row = conn.execute(
        "SELECT guardian_status, siblings_brothers, siblings_sisters FROM family_contexts "
        "WHERE student_profile_id = ?", (_family_profile.id,)).fetchone()
    _restart_ok = (_restart_row is not None
                   and _restart_row['siblings_sisters'] == 3
                   and _restart_row['guardian_status'] == FamilyContext.GUARDIAN_GRANDPARENTS)
    _restart_detail = f"row={tuple(_restart_row) if _restart_row else None}"
except Exception as _restart_exc:
    _restart_detail = f"{type(_restart_exc).__name__}: {_restart_exc}"
check("M", "پایداری پس از راه‌اندازی دوباره: با بستن کامل اتصال‌ها و اتصال تازه، همان مقدارها از دیتابیس خوانده می‌شوند (داده در حافظه نیست)",
      _restart_ok, _restart_detail)

# ============================================================
print()
print("=" * 76)
print("بخش N: بازبینی نهایی — همگام‌سازی «سال تحصیلی فعال» (BUG-GUI-12 / NAV-04/05/06)")
print("=" * 76)

# --- N1: ایستا — تک‌مسیر بودن تغییر سال در کد
_mw_src = read("views/main_window.py")
_ys_src = read("views/pages/year_sync.py")
_legacy_inspect = "import inspect" in _mw_src
_page_missing_reload = []
for _fname in ("dashboard_page", "students_page", "observations_page", "interventions_page",
               "followups_page", "indicators_page", "analysis_page", "reports_page",
               "academic_structure_page", "counseling_page", "activities_page", "goals_page",
               "settings_page"):
    _page_src = read(f"views/pages/{_fname}.py")
    if "YearAwarePage" not in _page_src or "def reload_for_year" not in _page_src:
        _page_missing_reload.append(_fname)
check("N", "ایستا: هیچ اسکن بازتابی (inspect) در main_window نمانده؛ همهٔ صفحه‌های وابسته به سال از YearAwarePage ارث می‌برند و reload_for_year دارند؛ فهرست صفحه‌ها صریح است",
      not _legacy_inspect
      and "def set_active_year" in _mw_src
      and "academic_year_changed.connect(self._sync_pages_for_year)" in _mw_src
      and "page_attrs = (" in _mw_src
      and "def effective_year" in _ys_src and "def select_year_in_combo" in _ys_src
      and not _page_missing_reload,
      f"inspect={_legacy_inspect} missing_reload={_page_missing_reload}")

# --- N2: تبدیل مسیر واقعی — سال دوم ساخته می‌شود و با set_active_year فعال می‌شود
_original_active = AcademicYearDAL().get_active()
_year2 = AcademicYear()
_year2.title = "1499-1500"
_year2.start_date = "1499/07/01"
_year2.end_date = "1500/06/30"
_year2.is_active = 0
_year2.is_archived = 0
_year2 = AcademicYearDAL().create(_year2)

_msgs_before_switch = len(ui_msgs)
_switch_ok = False
_switch_detail = ""
_synced, _skipped = [], []
_combo_state = {}
_active_state = {}
_nested_state = {}
try:
    with contextlib.redirect_stdout(io.StringIO()):
        _switch_ok, _switch_msg = win.set_active_year(_year2.id)
    win.last_year_sync = ([], [])
    # فهرست همگام‌شده باید از مسیر «سیگنال» پر شود؛ صفر ماندن یعنی سیگنال گیرنده ندارد
    win.academic_year_changed.emit(_year2.id)
    _synced_via_signal, _skipped_via_signal = win.last_year_sync
    _synced, _skipped = getattr(win, "last_year_sync", ([], []))

    _active_after = AcademicYearDAL().get_active()
    _combo_state = {name: getattr(getattr(win, name), "year_combo", None) for name in
                    ("indicators_page", "analysis_page", "reports_page", "academic_structure_page")}
    _combo_state = {name: (combo.currentData() if combo is not None else "no-combo")
                    for name, combo in _combo_state.items()}
    _active_state = {name: getattr(getattr(win, name), "active_year_id", None) for name in
                     ("dashboard_page", "students_page", "observations_page", "interventions_page",
                      "followups_page", "indicators_page", "analysis_page", "reports_page",
                      "academic_structure_page", "counseling_page", "activities_page", "goals_page",
                      "settings_page")}
    _nested_state = {
        "profile": win.students_page.profile_page.selected_year_id,
        "analytics": win.dashboard_page.analytics_dashboard_page.active_year_id,
        "class_report": win.reports_page.class_report_page.active_year_id,
        "teacher_report": win.reports_page.teacher_report_page.active_year_id,
        "promotion": win.academic_structure_page.promotion_page.active_year_id,
    }
    _switch_detail = (f"ok={_switch_ok} msg={_switch_msg!r} active={_active_after.id if _active_after else None} "
                      f"signal_synced={_synced_via_signal} combos={_combo_state} active_state={_active_state} nested={_nested_state} "
                      f"errors={[m for m in ui_msgs[_msgs_before_switch:] if m[0] != 'info'][:2]}")
    check("N", "تغییر سال با set_active_year: سال فعال دیتابیس عوض می‌شود، سیگنال academic_year_changed گیرندهٔ واقعی دارد و همهٔ ۱۳ صفحهٔ وابسته به سال (بدون استثنا و بدون پیام خطا) همگام می‌شوند",
          _switch_ok
          and _active_after is not None and _active_after.id == _year2.id
          and win.year_combo.currentData() == _year2.id
          and _year2.title in win.year_label.text()
          and _synced_via_signal and not _skipped_via_signal
          and len(_synced_via_signal) == 13
          and all(value == _year2.id for value in _active_state.values())
          and all(value == _year2.id for value in _combo_state.values())
          and all(value == _year2.id for value in _nested_state.values())
          and not [m for m in ui_msgs[_msgs_before_switch:] if m[0] != "info"],
          _switch_detail)
except Exception as _switch_exc:
    check("N", "تغییر سال با set_active_year و همگام‌سازی همهٔ صفحه‌ها", False,
          f"{type(_switch_exc).__name__}: {_switch_exc} {_switch_detail}")

# --- N3: «بدون حدس زدن سال فعال»: اگر سال فعال دیتابیس عوض شود ولی سامانه
#         انتخاب صریح داشته باشد، صفحه‌ها همان انتخاب صریح را می‌گیرند
_guess_ok = False
_guess_detail = ""
try:
    _dl_conn = dbc.DatabaseConnection().get_connection()
    _dl_conn.execute("UPDATE academic_years SET is_active = 0 WHERE id = ?", (_year2.id,))
    _dl_conn.execute("UPDATE academic_years SET is_active = 1 WHERE id = ?", (_original_active.id,))
    _dl_conn.commit()
    _explicit = win.observations_page.effective_year()
    _no_explicit_page = win.indicators_page.effective_year()
    _guess_ok = (_explicit is not None and _explicit.id == _year2.id
                 and _no_explicit_page is not None and _no_explicit_page.id == _year2.id)
    _guess_detail = (f"db_active={AcademicYearDAL().get_active().id} "
                     f"observations_effective={getattr(_explicit, 'id', None)} "
                     f"indicators_effective={getattr(_no_explicit_page, 'id', None)}")
except Exception as _guess_exc:
    _guess_detail = f"{type(_guess_exc).__name__}: {_guess_exc}"
check("N", "بدون حدس زدن: اگر سال فعال دیتابیس بیرون از برنامه عوض شود، صفحه‌های وابسته به سال همچنان سال اعلام‌شدهٔ سامانه را می‌خوانند (نه سال فعال دیتابیس)",
      _guess_ok, _guess_detail)

# --- N4: سال بایگانی‌شده فعال نمی‌شود و برگشت به سال قبلی بی‌خطا انجام می‌شود
_archive_ok = False
_archive_detail = ""
try:
    with contextlib.redirect_stdout(io.StringIO()):
        AcademicYearDAL().set_active(_year2.id)
    _mw_msgs = len(ui_msgs)
    with contextlib.redirect_stdout(io.StringIO()):
        _archived_ok, _archived_msg = win.set_active_year(
            next(y.id for y in AcademicYearDAL().get_all(include_archived=True)
                 if getattr(y, "is_archived", 0) == 1))
    _still = AcademicYearDAL().get_active()
    _archive_ok = (not _archived_ok and _still is not None and _still.id == _year2.id)
    _archive_detail = f"ok={_archived_ok} msg={_archived_msg!r} active={_still.id if _still else None}"
except Exception as _archive_exc:
    _archive_detail = f"{type(_archive_exc).__name__}: {_archive_exc}"
check("N", "سال بایگانی‌شده فعال نمی‌شود: set_active_year با False و پیام روشن برمی‌گردد و سال فعال دست‌نخورده می‌ماند",
      _archive_ok, _archive_detail)

# --- بازگرداندن وضعیت اولیه برای بررسی‌های بعدی (بدون اثر جانبی)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        win.set_active_year(_original_active.id)
        AcademicYearDAL().delete(_year2.id)
except Exception as _restore_exc:  # pragma: no cover
    print(f"   ⚠️ بازگردانی سال اولیه پس از بخش N ممکن نشد: {_restore_exc}")

# --- I4: قیدهای CHECK در دیتابیس تازه: شدت خارج از ۱..۵ و نوع رفتار ناشناخته در سطح دیتابیس رد می‌شوند
sev_err = _integrity("INSERT INTO observations (student_profile_id, staff_id, observation_date, description, behavior, behavior_type, severity) "
                     "VALUES (?, 1, '1405/01/01', 'x', 'y', 'مثبت', 9)", (form_pid,))
type_err = _integrity("INSERT INTO observations (student_profile_id, staff_id, observation_date, description, behavior, behavior_type, severity) "
                      "VALUES (?, 1, '1405/01/01', 'x', 'y', 'positive', 3)", (form_pid,))
ok_ins = _integrity("INSERT INTO observations (student_profile_id, staff_id, observation_date, description, behavior, behavior_type, severity) "
                    "VALUES (?, 1, '1405/01/01', 'x', 'y', 'خنثی', 3)", (form_pid,))
check("I", "CHECK در دیتابیس تازه (بند ۳۱): severity=9 و behavior_type ناشناخته در سطح دیتابیس رد می‌شوند؛ مقدار معتبر پذیرفته می‌شود (دیتابیس‌های موجود: اعتبارسنجی مدل/سرویس)",
      "CHECK" in sev_err and "CHECK" in type_err and ok_ins == "accepted",
      f"sev={sev_err[:40]} type={type_err[:40]} ok={ok_ins}")

# --- I5: مخزن: دیتابیس واقعی و پشتیبان‌ها ردیابی نمی‌شوند
tracked_db = _subprocess.run(["git", "ls-files", "database/partow.db"], capture_output=True, text=True).stdout.strip()
ignored_db = _subprocess.run(["git", "check-ignore", "-q", "database/partow.db"], capture_output=True).returncode == 0
check("I", "دیتابیس واقعی (database/partow.db) دیگر در مخزن git ردیابی نمی‌شود و در .gitignore است",
      tracked_db == "" and ignored_db, f"tracked={tracked_db!r} ignored={ignored_db}")

# --- I6: خروج خودکار پس از بی‌کاری واقعاً خودکار است (بدون دیالوگ تأیید) — آخرین بررسی، چون پنجره بسته می‌شود
asked = []
QMessageBox.question = staticmethod(lambda *a, **k: asked.append(a[1]) or QMessageBox.StandardButton.No)
popen_calls = []
real_popen = _subprocess.Popen
_subprocess.Popen = lambda *a, **k: popen_calls.append(a[0][:1]) or None


class _Exit(Exception):
    pass


real_exit = sys.exit
sys.exit = lambda code=0: (_ for _ in ()).throw(_Exit(str(code)))
logout_audit_before = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action = 'logout'").fetchone()[0]
exited = None
try:
    with contextlib.redirect_stdout(io.StringIO()):
        win.auto_logout()
except _Exit as e:
    exited = str(e)
finally:
    sys.exit = real_exit
    _subprocess.Popen = real_popen
logout_audit_after = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action = 'logout'").fetchone()[0]
check("I", "خروج خودکار (auto_logout): بدون دیالوگ تأیید انجام می‌شود، ثبت Audit خروج، اجرای دوبارهٔ برنامه و خروج فرایند (قبلاً منتظر کلیک «بله» می‌ماند)؛ خروج دستی همچنان تأیید می‌گیرد",
      not asked and exited == "0" and len(popen_calls) == 1 and logout_audit_after == logout_audit_before + 1
      and "lambda checked=False: self.logout(confirm=True)" in read("views/main_window.py"),
      f"asked={asked} exited={exited} popen={len(popen_calls)} audit {logout_audit_before}->{logout_audit_after}")

# ============================================================
print()
print("=" * 76)
print(f"نتیجهٔ دور شانزدهم (مرحله‌های ۱ تا ۶):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
if FAILURES:
    print("موارد ناموفق:")
    for f in FAILURES:
        print("   -", f)
print("=" * 76)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
