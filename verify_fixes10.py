#!/usr/bin/env python3
"""
راستی‌آزمایی دور دهم بازرسی — پاکی کامل lint، صحت معنایی ClassVar،
سیاست «مرز خطا» و نگهبان‌های نهایی

بخش‌ها:
  A) پاکی کامل lint (۸ بررسی)
  B) صحت معنایی ClassVar و نحو مدرن (۷ بررسی)
  C) زمان/تاریخ و نسخهٔ پایگاه‌داده (۵ بررسی)
  D) بهداشت مخزن (۵ بررسی)
  E) نگهبان‌های رگرسیون (۵ بررسی)

اجرا:  python verify_fixes10.py
"""

import ast
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

APP_DIRS = ('dal', 'services', 'views', 'models', 'utils', 'database', 'config')
SCOPE = APP_DIRS + ('main.py', 'tests')

# چند بررسی (مقایسه با HEAD و فایل‌های ردیابی‌شده) نیاز به مخزن git دارند؛
# در یک کپی ساده (tar بدون .git) به‌جای «شکست»، رد می‌شوند.
HAS_GIT = os.path.isdir(os.path.join(ROOT, '.git'))

RUFF = os.path.join(os.path.dirname(sys.executable), 'ruff')
if not os.path.exists(RUFF):
    RUFF = 'ruff'


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


def ruff(*args):
    return subprocess.run([RUFF, *list(args)], capture_output=True, text=True, cwd=ROOT)


def findings(stdout):
    """فقط خطوطِ یافته‌ها (نه پیام خلاصه/راهنما) را می‌شمارد."""
    return [ln for ln in stdout.splitlines() if re.match(r'^[^ ]+\.py:\d+:\d+:', ln)]


TMP = tempfile.mkdtemp(prefix="round10_verify_")

# ================================================================
print("=" * 76)
print("بخش A: پاکی کامل lint")
print("=" * 76)

r = ruff('check', '.')
check("A", "`ruff check .` روی کل درخت پاک است", r.returncode == 0,
      str(findings(r.stdout)[:3]))

for rule, label in (
    ("RUF012", "ثابت‌های کلاس دیگر default متغیر نیستند"),
    ("UP006,UP035", "نحو قدیمی typing (List/Dict/Tuple) پاک شد"),
    ("F", "خطاهای واقعی پایتون صفر است"),
    ("S110", "try/except/pass بی‌توضیح صفر است"),
):
    r = ruff('check', '--select', rule, *SCOPE)
    check("A", label, r.returncode == 0, str(findings(r.stdout)[:3]))

# توجه: `--select` روی CLI فهرست ignore فایل تنظیمات را نادیده می‌گیرد،
# پس اینجا صریحاً همان قواعد «بدهیِ سابق» را می‌شماریم (نه RUF001… که
# عمداً برای متن فارسی خاموش است).
DEBT = ("SIM102,SIM105,SIM108,SIM110,SIM113,SIM118,SIM401,RUF005,RUF012,"
        "RUF013,RUF059,C401,C416,C420,PIE810,UP006,UP035")
r = ruff('check', '--select', DEBT, *SCOPE)
check("A", "همهٔ قواعد بدهیِ سابق (SIM/RUF/C4/PIE/UP) صفر شدند",
      r.returncode == 0, str(findings(r.stdout)[:3]))

r = ruff('check', '--select', 'BLE001', 'dal')
check("A", "dal از سیاست مرز خطا بیرون است (BLE001 = 0)",
      r.returncode == 0, str(findings(r.stdout)[:3]))

cfg = read(os.path.join(ROOT, 'ruff.toml'))
policy_ok = all(f'"{p}" = ["BLE001"]' in cfg for p in
                ('services/**', 'views/**', 'database/**', 'utils/**', 'models/**', 'main.py'))
check("A", "ruff.toml سیاست «مرز خطا» را مستند کرده", policy_ok)
check("A", "ابزارهای راستی‌آزمایی از lint بیرون‌اند",
      'extend-exclude' in cfg and 'verify_fixes*.py' in cfg)

# ================================================================
print()
print("=" * 76)
print("بخش B: صحت معنایی ClassVar و نحو مدرن")
print("=" * 76)


def class_literals(src):
    """ثابت‌های سطح‌کلاس با مقدار literal → {'Class.NAME': value}"""
    out = {}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                targets = []
                if isinstance(item, ast.Assign):
                    targets, val = item.targets, item.value
                elif isinstance(item, ast.AnnAssign) and item.value is not None:
                    targets, val = [item.target], item.value
                else:
                    continue
                try:
                    literal = ast.literal_eval(val)
                except Exception:
                    continue
                for t in targets:
                    if isinstance(t, ast.Name):
                        out[f"{node.name}.{t.id}"] = literal
    return out


changed = []
if HAS_GIT:
    changed = subprocess.run(['git', 'diff', '--name-only', 'HEAD', '--', '*.py'],
                             capture_output=True, text=True, cwd=ROOT).stdout.split()
compared, mismatch = 0, []
for rel in changed:
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        continue
    old = subprocess.run(['git', 'show', f'HEAD:{rel}'], capture_output=True,
                         text=True, cwd=ROOT).stdout
    before, after = class_literals(old), class_literals(read(path))
    compared += 1
    for key, val in before.items():
        if key in after and after[key] != val:
            mismatch.append(f"{rel}:{key}")
if HAS_GIT:
    check("B", f"مقدار ثابت‌های کلاس در {compared} فایل تغییریافته دست‌نخورده است",
          not mismatch, str(mismatch[:3]))
else:
    print("  ⏭️ [B] مقایسه با HEAD رد شد (بدون مخزن git)")

# ClassVar نباید به فیلد dataclass تبدیل شود
import dataclasses
import importlib
problem = []
for path in app_py_files('models'):
    src = read(path)
    if '@dataclass' not in src or 'ClassVar' not in src:
        continue
    problem.append(os.path.relpath(path, ROOT))
check("B", "هیچ فیلد dataclass به ClassVar تبدیل نشده", not problem, str(problem))

dc_fields = []
for mod in ('models.analytics_models', 'models.recommendation_rules'):
    m = importlib.import_module(mod)
    for name in dir(m):
        obj = getattr(m, name)
        if isinstance(obj, type) and dataclasses.is_dataclass(obj):
            dc_fields.append((name, len(dataclasses.fields(obj))))
check("B", "dataclassها فیلدهای خود را از دست نداده‌اند",
      dc_fields and all(n > 0 for _, n in dc_fields), str(dc_fields))

from models.counseling_session import CounselingSession  # noqa: E402
from models.observation import Observation  # noqa: E402
from utils.file_validator import FileValidator  # noqa: E402
from utils.theme_manager import ThemeManager  # noqa: E402

check("B", "CounselingSession.STATUS_CHOICES سالم است (۵ گزینه)",
      len(CounselingSession.STATUS_CHOICES) == 5)
check("B", "FileValidator.ALLOWED_EXTENSIONS سالم است (۶ مورد)",
      len(FileValidator.ALLOWED_EXTENSIONS) == 6)
check("B", "ThemeManager.THEMES سالم است (۴ تم)", len(ThemeManager.THEMES) == 4)
# (دور ۱۶) مدل Notification همراه زیرسیستم اعلان‌ها حذف شد؛ همان بررسی روی مدل‌های زنده
check("B", "ثابت‌های کلاس در زمان اجرا خوانده می‌شوند",
      CounselingSession.STATUS_CHOICES and Observation.BEHAVIOR_POSITIVE == 'مثبت'
      and FileValidator.ALLOWED_EXTENSIONS)

# نگهبان NameError: متدهایی که دور دهم به utc_now/utc_now_iso مهاجرت
# کردند باید واقعاً اجرا شوند (خطای import جاافتاده فوراً لو می‌رود).
runtime_errors = []
from models.base import BaseModel  # noqa: E402
from models.individual_goal import IndividualGoal  # noqa: E402
from models.recommendation import Recommendation  # noqa: E402
# (دور ۱۶) مدل Notification حذف شد؛ همان نگهبان روی مدل‌های زندهٔ زمان‌دار
for obj, meth in ((BaseModel(), 'get_current_time'),
                  (Recommendation(), 'implement'),
                  (IndividualGoal(), 'achieve')):
    try:
        getattr(obj, meth)()
    except Exception as exc:
        runtime_errors.append(f"{type(obj).__name__}.{meth}: {type(exc).__name__}")
check("B", "متدهای زمان‌دار مدل‌ها بدون NameError اجرا می‌شوند",
      not runtime_errors, str(runtime_errors))

import pkgutil  # noqa: E402
import warnings  # noqa: E402
warnings.filterwarnings('ignore')
mods = []
for pkg in APP_DIRS:
    try:
        p = importlib.import_module(pkg)
    except Exception as exc:  # pragma: no cover
        check("B", f"import بستهٔ {pkg}", False, str(exc))
        continue
    mods.append(pkg)
    mods += [m.name for m in pkgutil.walk_packages(p.__path__, pkg + '.')]
fails = []
for name in mods:
    try:
        importlib.import_module(name)
    except Exception as exc:
        fails.append(f"{name}: {type(exc).__name__}")
check("B", f"همهٔ {len(mods)} ماژول بدون خطا import می‌شوند", not fails, str(fails[:4]))

try:
    from config.settings import GRADE_NAMES, GRADES, STAFF_ROLES  # noqa: F401
    from models import StaffRole, UserRole  # noqa: F401
    exports_ok = bool(GRADES and STAFF_ROLES and GRADE_NAMES) and UserRole and StaffRole
except Exception as exc:
    exports_ok = False
    print("     خطا:", exc)
check("B", "بازصدورهای config.settings و models سالم‌اند", bool(exports_ok),
      "" if exports_ok else "import ناموفق")

check("B", "هیچ import قدیمی typing (List/Dict/Tuple) نمانده",
      not [p for p in app_py_files(*APP_DIRS)
           if re.search(r'^from typing import [^\n]*\b(List|Dict|Tuple|Set|FrozenSet)\b',
                        read(p), re.M)],
      "")

# ================================================================
print()
print("=" * 76)
print("بخش C: زمان، تاریخ و نسخهٔ پایگاه‌داده")
print("=" * 76)

from utils.time_utils import utc_now, utc_now_iso, utc_shift_iso  # noqa: E402
from utils.persian_date import to_db_date  # noqa: E402
from services.base_service import BaseService  # noqa: E402

iso = utc_now_iso()
check("C", "utc_now_iso خروجی UTC-aware می‌دهد",
      iso.endswith('+00:00') and utc_now().utcoffset().total_seconds() == 0)
check("C", "utc_shift_iso درست کار می‌کند",
      utc_shift_iso(days=-1) < iso < utc_shift_iso(days=1))

# DTZ005 = «datetime.now() بدون tz»؛ خودِ ruff منبعِ حقیقت است تا
# jdatetime.datetime.now() (عمدی، زمان محلی شمسی) و متن‌های راهنما
# اشتباهاً گرفته نشوند.
r = ruff('check', '--select', 'DTZ005', *APP_DIRS)
check("C", "هیچ datetime.now() بدون ناحیهٔ زمانی نمانده", r.returncode == 0,
      str(findings(r.stdout)[:4]))

check("C", "تاریخ '1405-6-6' به شکل استاندارد تبدیل می‌شود",
      to_db_date('1405-6-6') == '1405/06/06')
svc = BaseService()
clean, err = svc.check_date('1405-6-6', "تاریخ آزمایش")
bad, err2 = svc.check_date('1405/13/45', "تاریخ آزمایش")
check("C", "check_date تاریخ معتبر را می‌پذیرد و نامعتبر را رد می‌کند",
      clean == '1405/06/06' and bad is None and err is None and bool(err2),
      f"{clean!r} {bad!r} {err!r} {err2!r}")

from config import settings as cfg_settings  # noqa: E402
check("C", "DB_VERSION = ۹ است", int(cfg_settings.DB_VERSION) == 9, str(cfg_settings.DB_VERSION))

# ================================================================
print()
print("=" * 76)
print("بخش D: بهداشت مخزن")
print("=" * 76)

tracked = []
leftovers = [f for f in os.listdir(ROOT) if re.match(r'patch_.*\.py$', f)]
check("D", "هیچ اسکریپت وصلهٔ یک‌بارمصرفی نمانده", not leftovers, str(leftovers))
check("D", "پوشهٔ reports/temp (نسخهٔ تکراری) حذف شده",
      not os.path.exists(os.path.join(ROOT, 'reports')))

if HAS_GIT:
    tracked = subprocess.run(['git', 'ls-files'], capture_output=True, text=True,
                             cwd=ROOT).stdout.splitlines()
    junk = [f for f in tracked if f.endswith(('.pyc', '.pyo', '.db-wal', '.db-shm'))
            or '__pycache__' in f]
    check("D", "هیچ فایل موقت ردیابی‌شده‌ای وجود ندارد", not junk, str(junk[:4]))
else:
    tracked = []
    print("  ⏭️ [D] فهرست فایل‌های ردیابی‌شده رد شد (بدون مخزن git)")


def silent_swallows(path):
    """try/except که بدنه‌اش فقط pass یا ... است (بدون توضیح/لاگ)."""
    hits = []
    src = read(path)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return hits
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            body = [n for n in handler.body
                    if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                            and isinstance(n.value.value, str))]
            # بدنهٔ مؤثر: رشتهٔ تنها (docstring) حذف می‌شود
            if len(body) != 1:
                continue
            only = body[0]
            empty = isinstance(only, ast.Pass) or (
                isinstance(only, ast.Expr) and isinstance(only.value, ast.Constant)
                and only.value.value is Ellipsis)
            if not empty:
                continue
            # pass تنها فقط با «توضیح» پذیرفته است (کامنت در متن مبدأ)
            segment = ast.get_source_segment(src, handler) or ""
            if '#' not in segment:
                hits.append(f"{os.path.relpath(path, ROOT)}:{handler.lineno}")
    return hits


swallows = []
for path in app_py_files(*APP_DIRS):
    swallows += silent_swallows(path)
check("D", "هیچ except/pass بی‌توضیحی در کل درخت نمانده", not swallows, str(swallows[:4]))

# migration v9 idempotent
import sqlite3  # noqa: E402
db = os.path.join(TMP, 'idem.db')
conn = sqlite3.connect(db)
conn.executescript("CREATE TABLE academic_years (id INTEGER PRIMARY KEY, title TEXT, "
                   "start_date TEXT, end_date TEXT);")
conn.execute("INSERT INTO academic_years (id, title, start_date, end_date) "
             "VALUES (1, '۱۴۰۴-۱۴۰۵', '1404-6-1', '1405-3-31')")
conn.commit()
conn.close()
sys.path.insert(0, ROOT)
from database.migrations import migration_v9  # noqa: E402
conn = sqlite3.connect(db)
migration_v9.upgrade(conn)
first = conn.execute("SELECT start_date, end_date FROM academic_years").fetchone()
migration_v9.upgrade(conn)
second = conn.execute("SELECT start_date, end_date FROM academic_years").fetchone()
conn.close()
check("D", "migration_v9 یکدست‌سازی را درست و تکرارپذیر انجام می‌دهد",
      first == second == ('1404/06/01', '1405/03/31'), f"{first} {second}")

# ================================================================
print()
print("=" * 76)
print("بخش E: نگهبان‌های رگرسیون")
print("=" * 76)

suites = ['verify_fixes.py'] + [f"verify_fixes{i}.py" for i in range(2, 11)]
missing = [s for s in suites if not os.path.exists(os.path.join(ROOT, s))]
check("E", "همهٔ ۱۰ مجموعهٔ راستی‌آزمایی موجودند", not missing, str(missing))

env = dict(os.environ)
env.setdefault('QT_QPA_PLATFORM', 'offscreen')
py = sys.executable

r9 = subprocess.run([py, 'verify_fixes9.py'], capture_output=True, text=True,
                    cwd=ROOT, env=env, timeout=900)
tail9 = [ln for ln in r9.stdout.splitlines() if 'موفق' in ln]
check("E", "verify_fixes9 هنوز سبز است (۳۸/۰)",
      r9.returncode == 0 and tail9 and '38 موفق / 0' in tail9[-1], str(tail9[-1:]))

ru = subprocess.run([py, '-m', 'unittest', 'discover', '-s', 'tests'],
                    capture_output=True, text=True, cwd=ROOT, env=env, timeout=900)
check("E", "آزمون‌های واحد (۲۶) سبز است",
      ru.returncode == 0 and 'OK' in ru.stderr, ru.stderr.strip().splitlines()[-1:])

r6 = subprocess.run([py, 'verify_fixes6.py'], capture_output=True, text=True,
                    cwd=ROOT, env=env, timeout=900)
check("E", "verify_fixes6 (مرز خطای سرویس‌ها) سبز است", r6.returncode == 0,
      r6.stdout.strip().splitlines()[-1:])

r = ruff('check', '--select', 'I001', *SCOPE)
check("E", "ترتیب importها یکدست است", r.returncode == 0, str(findings(r.stdout)[:3]))

if HAS_GIT:
    check("E", "فایل‌های جانبی SQLite در مخزن ردیابی نمی‌شوند",
          'database/partow.db' in tracked
          and not [f for f in tracked if f.endswith('-wal')], "")
else:
    print("  ⏭️ [E] بررسی ردیابی SQLite رد شد (بدون مخزن git)")

# ================================================================
shutil.rmtree(TMP, ignore_errors=True)

print()
print("=" * 76)
print(f"نتیجهٔ دور دهم:  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های دور دهم سبز است؛ بدهی lint صفر شد.")
