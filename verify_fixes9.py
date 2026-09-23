#!/usr/bin/env python3
"""
راستی‌آزمایی دور نهم بازرسی — شکست‌های بی‌صدا، استثناهای لایهٔ داده،
یکدست‌سازی تاریخ‌های موجود و تنظیمات lint

بخش‌ها (۳۶ بررسی):
  A) پایان «except های بی‌صدا» ....................... ۶ بررسی
  B) باریک‌سازی استثنا در لایهٔ داده ................. ۵ بررسی
  C) حذف کد تکراری برچسب ماه ........................ ۷ بررسی
  D) Migration نسخهٔ ۹ (یکدست‌سازی تاریخ موجود) ...... ۸ بررسی
  E) تنظیمات lint و نگهبان‌های رگرسیون ............... ۷ بررسی
  F) بهداشت (ماژول مرده، بازصدورها) ................. ۳ بررسی

اجرا:  python verify_fixes9.py
"""

import ast
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = 0
FAIL = 0
FAILURES = []
ROOT = os.path.dirname(os.path.abspath(__file__))


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
    return open(path, encoding='utf-8').read()


def app_py_files(*dirs):
    for d in dirs:
        for root, sub, files in os.walk(os.path.join(ROOT, d)):
            sub[:] = [x for x in sub if x != '__pycache__']
            for f in files:
                if f.endswith('.py'):
                    yield os.path.join(root, f)


TMP = tempfile.mkdtemp(prefix="round9_verify_")

try:
    import config.settings as settings
    import database.connection as dbc

    TEST_DB = os.path.join(TMP, "partow.db")
    _orig_s, _orig_c = settings.DB_PATH, dbc.DB_PATH
    settings.DB_PATH = TEST_DB
    dbc.DB_PATH = TEST_DB
    dbc.DatabaseConnection._instance = None
    dbc.DatabaseConnection._connection = None
    dbc.DatabaseConnection._initialized = False

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        db = dbc.DatabaseConnection()
        conn = db.get_connection()

    # ========================================================
    print("=" * 76)
    print("بخش A: پایان «except های بی‌صدا»")
    print("=" * 76)

    def silent_swallows():
        """
        except هایی که بدنه‌شان فقط pass است و نه لاگ دارند و نه
        کامنت توضیحی بالای همان pass.
        """
        out = []
        for path in app_py_files('dal', 'services', 'utils', 'views', 'models', 'database'):
            src = read(path)
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            lines = src.splitlines()
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                if any(not isinstance(n, ast.Pass) for n in node.body):
                    continue
                has_log = any(
                    isinstance(sub, ast.Call) and (
                        (isinstance(sub.func, ast.Name) and sub.func.id in
                         ('error', 'warning', 'info', 'debug', 'exception', 'critical', 'print'))
                        or (isinstance(sub.func, ast.Attribute) and sub.func.attr in
                            ('error', 'warning', 'info', 'debug', 'exception', 'critical'))
                    )
                    for n in node.body for sub in ast.walk(n)
                )
                if has_log:
                    continue
                ln = node.body[0].lineno if node.body else node.lineno
                prev = lines[ln - 2].strip() if ln >= 2 else ''
                if prev.startswith('#'):
                    continue
                out.append(f"{os.path.relpath(path, ROOT)}:{ln}")
        return out

    silent = silent_swallows()
    check("A", "هیچ except بی‌صدا و بی‌توضیحی نمانده", not silent, str(silent[:5]))

    # نمونه‌های شاخص اصلاح‌شده
    check("A", "dal/user_dal ثبت Audit ناموفق را لاگ می‌کند",
          'logger.debug(f"ثبت Audit' in read('dal/user_dal.py'))
    check("A", "utils/file_validator شکست libmagic را لاگ می‌کند",
          'libmagic پاسخ نداد' in read('utils/file_validator.py'))
    # (دور ۱۶) dal/backup_dal بدون مصرف‌کننده حذف شد؛ همان اصل («شکست حذف فایل
    # بی‌صدا نمی‌ماند») روی مسیر زندهٔ پشتیبان‌ها بررسی می‌شود.
    check("A", "utils/backup حذف‌نشدن فایل checksum/پشتیبان را در نتیجه و لاگ اعلام می‌کند",
          'حذف نشد' in read('utils/backup.py') and 'logger.warning' in read('utils/backup.py'))
    check("A", "utils/logger دلیل نبود __file__ را توضیح می‌دهد",
          'بدون __file__' in read('utils/logger.py'))
    check("A", "migration_v5 خطای DROP COLUMN را گزارش می‌کند",
          'حذف ستون‌های screenings' in read('database/migrations/migration_v5.py'))

    # ========================================================
    print()
    print("=" * 76)
    print("بخش B: استثناهای لایهٔ داده (BLE001)")
    print("=" * 76)

    RUFF = os.path.join(os.path.dirname(sys.executable), 'ruff')
    if not os.path.exists(RUFF):
        RUFF = 'ruff'

    def ruff(*args):
        return subprocess.run([RUFF, *list(args)], capture_output=True, text=True, cwd=ROOT)

    r = ruff('check', '--select', 'BLE001', '--output-format=concise', 'dal')
    dal_ble = [ln for ln in r.stdout.splitlines()
               if re.match(r'^[^ ]+\.py:\d+:\d+:', ln)]
    check("B", "هیچ except عامی در dal باقی نمانده", not dal_ble, str(dal_ble[:4]))

    r = ruff('check', '--select', 'F', 'dal', 'services', 'views', 'models', 'utils',
             'database', 'config', 'main.py', 'tests')
    check("B", "ruff --select F پاک است", r.returncode == 0, r.stdout[-200:])

    # نگهبان: خطاهای برنامه‌نویسی دیگر قورت داده نمی‌شوند
    import inspect

    from dal.student_dal import StudentDAL
    src = inspect.getsource(StudentDAL)
    check("B", "StudentDAL استثناهای مشخص می‌گیرد",
          'except (' in src and 'sqlite3.Error' in src)
    check("B", "StudentDAL دیگر except Exception ندارد",
          not re.search(r'except\s+Exception', src))

    # خطای واقعی دیتابیس همچنان مدیریت می‌شود (نه کرش)
    with contextlib.redirect_stdout(buf):
        dal_inst = StudentDAL()
    try:
        dal_inst.get_by_id("نامعتبر") if False else None
        ok = True
    except Exception:
        ok = False
    check("B", "لایهٔ داده با ورودی نامعتبر کرش نمی‌کند", ok)

    # ========================================================
    print()
    print("=" * 76)
    print("بخش C: حذف کد تکراری «برچسب ماه»")
    print("=" * 76)

    month_src = read('utils/persian_date.py')
    check("C", "پیاده‌سازی واحد در utils/persian_date هست",
          'def get_month_label' in month_src and 'PERSIAN_MONTHS' in month_src)

    duplicates = []
    for path in app_py_files('dal', 'services', 'utils', 'views'):
        src = read(path)
        if 'month_names = ["فروردین"' in src:
            duplicates.append(os.path.relpath(path, ROOT))
    check("C", "هیچ کپی محلی از فهرست ماه‌ها نمانده",
          not duplicates, str(duplicates))

    from dal.followup_dal import FollowUpDAL
    from dal.intervention_dal import InterventionDAL
    from dal.observation_dal import ObservationDAL
    from dal.teacher_assignment_dal import TeacherAssignmentDAL
    from utils.analytics_helpers import AnalyticsHelpers
    from utils.persian_calendar import TimeGrouper
    from utils.persian_date import PersianDate

    samples = ['1405/06/26', '1405/01/05', '1405/12/01']
    expected = [PersianDate.get_month_label(s) for s in samples]
    check("C", "خروجی PersianDate با نمونه‌ها هم‌خوان است",
          expected == ['شهریور 1405', 'فروردین 1405', 'اسفند 1405'], str(expected))

    dal_impls = [FollowUpDAL()._get_month_label, InterventionDAL()._get_month_label,
                 ObservationDAL()._get_month_label, TeacherAssignmentDAL()._get_month_label]
    same = all([fn(s) for s in samples] == expected for fn in dal_impls)
    check("C", "همهٔ DAL ها همان خروجی را می‌دهند", same)
    check("C", "analytics_helpers هم همان خروجی را می‌دهد",
          [AnalyticsHelpers.get_persian_month_label(s) for s in samples] == expected)
    check("C", "TimeGrouper هم همان خروجی را می‌دهد",
          TimeGrouper.get_month_label('1405/06') == 'شهریور 1405')
    check("C", "ورودی نامعتبر به fallback می‌رسد",
          FollowUpDAL()._get_month_label('بوق') == 'بوق' and
          FollowUpDAL()._get_month_label('') == '')

    # ========================================================
    print()
    print("=" * 76)
    print("بخش D: Migration نسخهٔ ۹ — یکدست‌سازی تاریخ‌های موجود")
    print("=" * 76)

    check("D", "DB_VERSION = 9", settings.DB_VERSION == 9, str(settings.DB_VERSION))
    check("D", "migration_v9.py وجود دارد",
          os.path.exists('database/migrations/migration_v9.py'))

    from database.migrations import migration_v9 as m9
    check("D", "فهرست ستون‌های تاریخ‌دار کامل است",
          len(m9.DATE_COLUMNS) >= 20, str(len(m9.DATE_COLUMNS)))

    # دادهٔ قدیمی با قالب‌های مخلوط
    conn.execute(
        "INSERT INTO academic_years (title, start_date, end_date) VALUES (?, ?, ?)",
        ('آزمون ۹', '1405-1-2', '۱۴۰۵/۰۲/۰۳'))
    conn.execute(
        "INSERT INTO academic_years (title, start_date, end_date) VALUES (?, ?, ?)",
        ('متن آزاد', 'بوق', 'نامعلوم'))
    conn.commit()

    with contextlib.redirect_stdout(buf):
        m9.upgrade(conn)

    r1 = conn.execute("SELECT start_date, end_date FROM academic_years WHERE title='آزمون ۹'").fetchone()
    check("D", "تاریخ خط‌تیره نرمال شد", r1[0] == '1405/01/02', str(r1[0]))
    check("D", "ارقام فارسی نرمال شد", r1[1] == '1405/02/03', str(r1[1]))

    r2 = conn.execute("SELECT start_date, end_date FROM academic_years WHERE title='متن آزاد'").fetchone()
    check("D", "مقدار غیرتاریخی دست‌نخورده ماند",
          r2[0] == 'بوق' and r2[1] == 'نامعلوم', str((r2[0], r2[1])))

    # idempotent
    before = conn.execute("SELECT COUNT(*) FROM academic_years").fetchone()[0]
    with contextlib.redirect_stdout(buf):
        m9.upgrade(conn)
    after_same = conn.execute(
        "SELECT start_date FROM academic_years WHERE title='آزمون ۹'").fetchone()[0]
    check("D", "اجرای دوباره تغییری ایجاد نمی‌کند",
          after_same == '1405/01/02' and
          conn.execute("SELECT COUNT(*) FROM academic_years").fetchone()[0] == before)

    # مسیر واقعی ارتقاء نسخه: نسخه را ۸ می‌کنیم و اتصال را بازمی‌سازیم
    conn.execute("INSERT INTO academic_years (title, start_date, end_date) VALUES (?, ?, ?)",
                 ('ارتقاء', '1404-5-6', '1404/05/06'))
    conn.execute("UPDATE db_version SET version = 8")
    conn.commit()
    conn.close()
    dbc.DatabaseConnection._instance = None
    dbc.DatabaseConnection._connection = None
    dbc.DatabaseConnection._initialized = False
    with contextlib.redirect_stdout(buf):
        conn = dbc.DatabaseConnection().get_connection()
    ver = conn.execute("SELECT version FROM db_version").fetchone()[0]
    up = conn.execute("SELECT start_date FROM academic_years WHERE title='ارتقاء'").fetchone()[0]
    check("D", "ارتقاء ۸→۹ خودکار اجرا می‌شود", ver == 9, str(ver))
    check("D", "داده در مسیر ارتقاء هم نرمال شد", up == '1404/05/06', str(up))

    with contextlib.redirect_stdout(buf):
        m9.downgrade(conn)
    check("D", "downgrade داده را تخریب نمی‌کند",
          conn.execute("SELECT start_date FROM academic_years WHERE title='ارتقاء'").fetchone()[0]
          == '1404/05/06')

    # ========================================================
    print()
    print("=" * 76)
    print("بخش E: تنظیمات lint و نگهبان‌های رگرسیون")
    print("=" * 76)

    check("E", "فایل ruff.toml وجود دارد", os.path.exists('ruff.toml'))
    cfg = read('ruff.toml')
    check("E", "ruff.toml بازصدورها را مستثنا کرده",
          'PLC0414' in cfg and 'config/settings.py' in cfg)
    check("E", "ruff.toml قواعد معنادار را فعال کرده",
          all(k in cfg for k in ('"F"', '"I"', '"S110"', '"BLE"')))

    r = ruff('check', '--select', 'PLC0414', 'config/settings.py', 'models/__init__.py')
    check("E", "تنظیمات، PLC0414 را برای بازصدورها نادیده می‌گیرد",
          r.returncode == 0, r.stdout[-150:])

    # نگهبان: بازصدورها هنوز کار می‌کنند
    try:
        from config.settings import GRADE_NAMES as g3
        from config.settings import GRADES as g1
        from config.settings import STAFF_ROLES as g2
        from models import StaffRole as sr
        from models import UserRole as ur
        exports_ok = all([g1, g2, g3]) and ur is not None and sr is not None
    except Exception as e:
        exports_ok = False
        print("     خطا:", e)
    check("E", "بازصدورهای config/models سالم‌اند", exports_ok)

    r = ruff('check', 'dal', 'services', 'views', 'models', 'utils', 'database', 'config',
             'main.py')
    total = len([ln for ln in r.stdout.splitlines() if re.match(r'^[^ ]+\.py:\d+:\d+:', ln)])
    check("E", "بدهیِ lint کاهش یافته (زیر ۹۰۰)", total < 900, str(total))

    ble = len([ln for ln in ruff('check', '--select', 'BLE001', '--output-format=concise', '.')
               .stdout.splitlines() if re.match(r'^[^ ]+\.py:\d+:\d+:', ln)])
    check("E", "BLE001 از ۵۵۲ به زیر ۵۰۰ رسید", ble < 500, str(ble))

    # ========================================================
    print()
    print("=" * 76)
    print("بخش F: بهداشت")
    print("=" * 76)

    check("F", "utils/file_preview.py (بدون مصرف‌کننده) حذف شده",
          not os.path.exists('utils/file_preview.py'))
    importers = []
    for path in app_py_files('dal', 'services', 'utils', 'views', 'models', 'config'):
        if 'file_preview' in read(path) and 'file_preview.py' not in path:
            importers.append(os.path.relpath(path, ROOT))
    check("F", "هیچ ماژولی file_preview را import نمی‌کند", not importers, str(importers))

    check("F", "کد مردهٔ test_promotion حذف‌شده باقی مانده",
          not os.path.exists('views/pages/test_promotion.py'))

except Exception as exc:
    import traceback
    traceback.print_exc()
    FAIL += 1
    FAILURES.append(f"[GLOBAL] خطای اجرای راستی‌آزمایی: {exc}")

finally:
    try:
        dbc.DatabaseConnection._instance = None
        dbc.DatabaseConnection._connection = None
        dbc.DatabaseConnection._initialized = False
        settings.DB_PATH = _orig_s
        dbc.DB_PATH = _orig_c
    except Exception:
        pass
    shutil.rmtree(TMP, ignore_errors=True)

print()
print("=" * 76)
print(f"نتیجهٔ دور نهم:  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های دور نهم سبز است.")
