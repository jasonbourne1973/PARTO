#!/usr/bin/env python3
"""
راستی‌آزمایی دور هشتم بازرسی — زمان UTC، اعتبارسنجی تاریخ، ایندکس‌ها و بهداشت مخزن

بخش‌ها (۳۶ بررسی):
  A) سیاست زمانی واحد (UTC) .......................... ۷ بررسی
  B) اعتبارسنجی و یکدست‌سازی تاریخ شمسی .............. ۹ بررسی
  C) ایندکس‌گذاری کلیدهای خارجی (migration v8) ....... ۶ بررسی
  D) بهداشت مخزن (فایل‌های ردیابی‌شده/مرده) ........... ۶ بررسی
  E) lint، بازصدورها و نگهبان‌های رگرسیون ............ ۸ بررسی

اجرا:  python verify_fixes8.py
"""

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


def shape(text):
    """متن بدون فاصله و بدون نیم‌فاصله، برای مقایسه‌های این‌فایلی"""
    return re.sub(r'[\s\u200c]+', '', text)


TMP = tempfile.mkdtemp(prefix="round8_verify_")

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
    print("بخش A: سیاست زمانی واحد (UTC)")
    print("=" * 76)

    TU = 'utils/time_utils.py'
    check("A", "utils/time_utils.py وجود دارد", os.path.exists(TU))
    tu = read(TU)
    for fn in ('utc_now', 'utc_now_iso', 'utc_now_sql', 'utc_shift_iso',
               'utc_shift_sql', 'parse_timestamp', 'age_days', 'is_older_than'):
        check("A", f"تابع {fn} در time_utils", f"def {fn}(" in tu)

    # ۱) هیچ datetime.now() بدون ناحیهٔ زمانی در کد برنامه نمانده باشد
    def real_code_lines(path):
        """خطوط فایل بدون کامنت‌ها و بدون رشته‌ها (با tokenize)"""
        import tokenize
        out = {}
        with open(path, 'rb') as fh:
            for tok in tokenize.tokenize(fh.readline):
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    continue
                out.setdefault(tok.start[0], []).append(tok.string)
        return {ln: ' '.join(parts) for ln, parts in out.items()}

    pat = re.compile(r'(?<![\w.])(datetime\.now\s*\(|datetime\.utcnow\s*\()')
    naive = []
    for d in ('dal', 'services', 'utils', 'database', 'views', 'models', 'config', 'tests'):
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x != '__pycache__']
            for f in files:
                if not f.endswith('.py'):
                    continue
                p = os.path.join(root, f)
                for ln, code in real_code_lines(p).items():
                    if pat.search(code) and 'jdatetime' not in code and 'now ( UTC )' not in code \
                            and 'now(UTC)' not in code.replace(' ', ''):
                        naive.append(f"{p}:{ln}")
    check("A", "هیچ زمان محلی naive باقی نمانده", not naive, str(naive[:4]))

    # ۲) رفتار واقعی توابع زمان
    from utils.time_utils import (
        age_days,
        is_older_than,
        parse_timestamp,
        utc_now_iso,
        utc_shift_iso,
    )
    iso = utc_now_iso()
    check("A", "utc_now_iso با +00:00 ذخیره می‌شود", iso.endswith('+00:00'), iso)
    check("A", "utc_shift_iso(days=-1) گذشته است",
          utc_shift_iso(days=-1) < iso)
    check("A", "utc_shift_iso(hours=1) آینده است",
          utc_shift_iso(hours=1) > iso)
    check("A", "parse_timestamp خروجی ISO را می‌فهمد",
          parse_timestamp(iso) is not None and
          parse_timestamp(iso).tzinfo is not None)
    check("A", "parse_timestamp ورودی بی‌ربط را None می‌کند",
          parse_timestamp('این یک تاریخ نیست') is None)
    check("A", "age_days روی زمان گذشته کار می‌کند",
          age_days(utc_shift_iso(days=-3)) >= 2.9)
    check("A", "is_older_than درست تصمیم می‌گیرد",
          is_older_than(utc_shift_iso(days=-10), days=7) is True and
          is_older_than(utc_shift_iso(days=-1), days=7) is False)

    # ۳) بررسی کاربردی: پاک‌سازی اعلان‌های قدیمی (باگ فرمت مخلوط)
    from dal.notification_dal import NotificationDAL
    from dal.staff_dal import StaffDAL
    from models.notification import Notification
    from models.staff import Staff

    st = Staff()
    st.full_name = "کاربر آزمون هشتم"
    st.role = "teacher"
    st.is_active = 1
    with contextlib.redirect_stdout(buf):
        st = StaffDAL().create(st)

    old = Notification()
    old.user_id, old.type, old.priority = st.id, 'info', 'low'
    old.title, old.message = "اعلان قدیمی", "متن"
    fresh = Notification()
    fresh.user_id, fresh.type, fresh.priority = st.id, 'info', 'low'
    fresh.title, fresh.message = "اعلان تازه", "متن"
    with contextlib.redirect_stdout(buf):
        nd = NotificationDAL()
        old = nd.create(old)
        fresh = nd.create(fresh)

    # created_at را خودکار SQLite پر می‌کند؛ برای آزمون، یکی را قدیمی می‌کنیم
    conn.execute("UPDATE notifications SET created_at = datetime('now', '-40 days') WHERE id = ?",
                 (old.id,))
    conn.commit()

    with contextlib.redirect_stdout(buf):
        nd.delete_old(days=30)

    ids = [r['id'] for r in conn.execute(
        "SELECT id FROM notifications WHERE user_id = ? AND is_deleted = 0", (st.id,)).fetchall()]
    check("A", "delete_old فقط اعلان قدیمی را حذف می‌کند",
          fresh.id in ids and old.id not in ids, f"ids={ids} old={old.id} fresh={fresh.id}")

    # ========================================================
    print()
    print("=" * 76)
    print("بخش B: اعتبارسنجی و یکدست‌سازی تاریخ شمسی")
    print("=" * 76)

    from utils.persian_date import PersianDate, to_db_date
    check("B", "to_db_date خط تیره را یکدست می‌کند",
          to_db_date('1405-6-6') == '1405/06/06', repr(to_db_date('1405-6-6')))
    check("B", "to_db_date ارقام فارسی را تبدیل می‌کند",
          to_db_date('۱۴۰۵/۰۶/۰۶') == '1405/06/06', repr(to_db_date('۱۴۰۵/۰۶/۰۶')))
    check("B", "تاریخ 1405/13/45 بی‌اعتبار است",
          PersianDate.is_valid_persian_date('1405/13/45') is False)
    check("B", "تاریخ 1404/12/30 (سال غیرکبیسه) بی‌اعتبار است",
          PersianDate.is_valid_persian_date('1404/12/30') is False)
    check("B", "تاریخ 1403/12/30 (سال کبیسه) معتبر است",
          PersianDate.is_valid_persian_date('1403/12/30') is True)

    from services.base_service import BaseService
    bs = BaseService.__new__(BaseService)
    norm, err = bs.check_date('1405-6-6', "تاریخ")
    check("B", "check_date خط تیره را می‌پذیرد و نرمال می‌کند",
          norm == '1405/06/06' and err is None, f"{norm} / {err}")
    norm, err = bs.check_date('1405/13/45', "تاریخ")
    check("B", "check_date تاریخ بی‌اعتبار را رد می‌کند",
          norm is None and err is not None, f"{norm} / {err}")
    norm, err = bs.check_date('', "تاریخ", required=True)
    check("B", "check_date فیلد اجباری خالی را رد می‌کند",
          norm is None and err is not None)
    norm, err = bs.check_date('', "تاریخ", required=False)
    check("B", "check_date فیلد اختیاری خالی را می‌پذیرد",
          norm is None and err is None)
    norm, err = bs.check_date(None, "تاریخ")
    check("B", "check_date مقدار None را کرش نمی‌کند", err is None and norm is None)

    # --- سرویس مشاهدات ---
    from services.observation_service import ObservationService
    db.set_current_user(st.id)
    stu = None
    from dal.student_dal import StudentDAL
    from models.student import Student
    s = Student()
    s.first_name, s.last_name = "دانش‌آموز", "آزمون هشتم"
    s.national_code = "1234567899"
    s.is_active = 1
    with contextlib.redirect_stdout(buf):
        stu = StudentDAL().create(s)
    from dal.student_academic_profile_dal import StudentAcademicProfileDAL
    from models.student_academic_profile import StudentAcademicProfile
    ay = conn.execute("SELECT id FROM academic_years WHERE is_active=1").fetchone()
    pr = StudentAcademicProfile()
    pr.student_id, pr.academic_year_id, pr.grade, pr.status = stu.id, ay['id'], 1, 'active'
    with contextlib.redirect_stdout(buf):
        pr = StudentAcademicProfileDAL().create(pr)
        obs = ObservationService().create_observation({
            'student_id': pr.id, 'staff_id': st.id, 'observation_date': '1405-6-6',
            'behavior': 'رفتار آزمون', 'description': 'توضیح', 'behavior_type': 'مثبت',
            'severity': 3}, user_id=st.id)
    stored = conn.execute("SELECT observation_date FROM observations WHERE id=?",
                          (obs.id,)).fetchone()['observation_date']
    check("B", "تاریخ مشاهده هنگام ذخیره نرمال می‌شود",
          stored == '1405/06/06', stored)
    ok, errs = ObservationService().validate_observation({
        'student_id': pr.id, 'staff_id': st.id, 'observation_date': '1405/13/45',
        'behavior': 'رفتار', 'description': 'توضیح', 'behavior_type': 'مثبت', 'severity': 3})
    check("B", "مشاهده با تاریخ بی‌اعتبار رد می‌شود", ok is False and errs, str(errs))

    # --- جلسهٔ مشاوره ---
    from services.counseling_service import CounselingService
    with contextlib.redirect_stdout(buf):
        ses = CounselingService().create_session({
            'student_profile_id': pr.id, 'counselor_id': st.id,
            'session_date': '1405-7-7', 'type': 'individual',
            'method': 'in_person', 'status': 'scheduled'}, user_id=st.id)
    sd = conn.execute("SELECT session_date FROM counseling_sessions WHERE id=?",
                      (ses.id,)).fetchone()['session_date']
    check("B", "تاریخ جلسه نرمال ذخیره می‌شود", sd == '1405/07/07', sd)
    try:
        with contextlib.redirect_stdout(buf):
            CounselingService()._validate_session_data({
                'student_profile_id': pr.id, 'counselor_id': st.id,
                'session_date': '1405/13/45'})
        check("B", "جلسه با تاریخ بی‌اعتبار رد می‌شود", False, "پذیرفته شد")
    except Exception as e:
        check("B", "جلسه با تاریخ بی‌اعتبار رد می‌شود",
              'معتبر نیست' in str(e), str(e)[:60])

    # --- فعالیت فوق‌برنامه و هدف ---
    from services.extracurricular_service import ExtracurricularService
    try:
        with contextlib.redirect_stdout(buf):
            ExtracurricularService()._validate_activity_data({
                'student_profile_id': pr.id, 'title': 'فعالیت', 'type': 'sport',
                'start_date': '1405/08/10', 'end_date': '1405/08/01'})
        check("B", "پایان قبل از شروع رد می‌شود", False, "پذیرفته شد")
    except Exception as e:
        check("B", "پایان قبل از شروع رد می‌شود",
              'قبل از تاریخ شروع' in str(e), str(e)[:60])
    try:
        with contextlib.redirect_stdout(buf):
            ExtracurricularService()._validate_activity_data({
                'student_profile_id': pr.id, 'title': None, 'type': 'sport',
                'start_date': '1405/08/10'})
        check("B", "عنوان None پیام گویا می‌دهد", False, "پذیرفته شد")
    except Exception as e:
        check("B", "عنوان None پیام گویا می‌دهد",
              'نمی‌تواند خالی باشد' in str(e), str(e)[:60])
    from services.goal_service import GoalService
    try:
        with contextlib.redirect_stdout(buf):
            GoalService()._validate_goal_data({
                'student_profile_id': pr.id, 'title': 'هدف',
                'target_date': '1405/00/10'})
        check("B", "هدف با تاریخ بی‌اعتبار رد می‌شود", False, "پذیرفته شد")
    except Exception as e:
        check("B", "هدف با تاریخ بی‌اعتبار رد می‌شود",
              'معتبر نیست' in str(e), str(e)[:60])

    # ========================================================
    print()
    print("=" * 76)
    print("بخش C: ایندکس‌گذاری کلیدهای خارجی (migration v8)")
    print("=" * 76)

    check("C", "DB_VERSION حداقل ۸ است (دور هشتم نسخه را به ۸ برد)",
          settings.DB_VERSION >= 8, str(settings.DB_VERSION))
    check("C", "migration_v8.py وجود دارد",
          os.path.exists('database/migrations/migration_v8.py'))
    check("C", "migration_v8 در فهرست ترمیمی ثبت شده",
          'migration_v8' in read('database/connection.py'))

    ver = conn.execute("SELECT version FROM db_version").fetchone()[0]
    check("C", "نسخهٔ دیتابیس ساخته‌شده با DB_VERSION هم‌خوان است",
          ver == settings.DB_VERSION, f"{ver} != {settings.DB_VERSION}")

    def fk_without_index(cx):
        indexed = {}
        for t, sql in cx.execute(
                "SELECT tbl_name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"):
            for m in re.findall(r'\(([^)]+)\)', sql or ''):
                for c in m.split(','):
                    indexed.setdefault(t, set()).add(c.strip())
        out = []
        for t, sql in cx.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
            for fk in re.findall(r'FOREIGN KEY\s*\(\s*(\w+)\s*\)', sql or ''):
                if fk not in indexed.get(t, set()):
                    out.append(f"{t}.{fk}")
        return out

    missing = fk_without_index(conn)
    check("C", "هیچ کلید خارجی بدون ایندکس نمانده", not missing, str(missing[:6]))
    n_idx = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    ).fetchone()[0]
    check("C", "ایندکس‌ها واقعاً ساخته شده‌اند", n_idx >= 100, str(n_idx))

    # idempotent بودن
    import importlib
    m8 = importlib.import_module('database.migrations.migration_v8')
    with contextlib.redirect_stdout(buf):
        m8.upgrade(conn)
    check("C", "اجرای دوبارهٔ migration بی‌خطاست",
          not fk_without_index(conn), str(fk_without_index(conn)[:5]))

    # downgrade روی یک کپی (دیتابیس اصلی دست‌نخورده بماند)
    copy_db = os.path.join(TMP, "downgrade.db")
    import sqlite3
    cx2 = sqlite3.connect(copy_db)
    conn.backup(cx2)          # کپی امن (دیتابیس در حالت WAL است)
    names = [e[0] for e in m8.FK_INDEXES]
    ph = ",".join("?" * len(names))
    before = cx2.execute(
        f"SELECT COUNT(*) FROM sqlite_master WHERE name IN ({ph})", names).fetchone()[0]
    with contextlib.redirect_stdout(buf):
        m8.downgrade(cx2)
    after = cx2.execute(
        f"SELECT COUNT(*) FROM sqlite_master WHERE name IN ({ph})", names).fetchone()[0]
    left = cx2.execute("SELECT COUNT(*) FROM sqlite_master WHERE name LIKE 'idx_%'").fetchone()[0]
    check("C", "downgrade فقط ایندکس‌های خودش را برمی‌دارد",
          before >= 40 and after == 0 and left > 0,
          f"before={before} after={after} left={left}")
    cx2.close()

    # ========================================================
    print()
    print("=" * 76)
    print("بخش D: بهداشت مخزن")
    print("=" * 76)

    def git_ls(pattern):
        out = subprocess.run(['git', 'ls-files'], capture_output=True, text=True,
                             cwd=os.path.dirname(os.path.abspath(__file__)))
        files = out.stdout.splitlines()
        return [f for f in files if re.search(pattern, f)]

    pyc = git_ls(r'__pycache__|\.pyc$')
    check("D", "هیچ .pyc/__pycache__ ردیابی نمی‌شود", not pyc, str(pyc[:3]))
    sidecar = git_ls(r'\.db-(wal|shm)$')
    check("D", "هیچ فایل جانبی SQLite ردیابی نمی‌شود", not sidecar, str(sidecar[:3]))

    gi = read('.gitignore')
    check("D", ".gitignore پوشش لازم را دارد",
          all(k in gi for k in ('__pycache__/', '*.py[cod]', '*.db-wal', '*.log')))

    # except های لخت در کد برنامه (نباید برگردند)
    bare = []
    for d in ('dal', 'services', 'utils', 'database', 'views', 'models'):
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x != '__pycache__']
            for f in files:
                if f.endswith('.py'):
                    p = os.path.join(root, f)
                    for i, line in enumerate(read(p).splitlines(), 1):
                        if re.match(r'\s*except\s*:\s*(#.*)?$', line):
                            bare.append(f"{p}:{i}")
    check("D", "هیچ except لختی نمانده", not bare, str(bare[:4]))

    patchers = [p for p in os.listdir('.')
                if re.match(r'patch_[p0-9].*\.py$', p)]
    check("D", "فایل‌های وصله‌ای موقت باقی نمانده‌اند", not patchers, str(patchers))

    # ماژول‌های مردهٔ حذف‌شده نباید برگردند
    dead = [p for p in ('views/pages/parent_report_service.py',
                        'views/pages/school_report_service.py') if os.path.exists(p)]
    check("D", "ماژول‌های مرده حذف شده‌اند", not dead, str(dead))

    # ========================================================
    print()
    print("=" * 76)
    print("بخش E: lint، بازصدور و نگهبان‌های رگرسیون")
    print("=" * 76)

    RUFF = os.path.join(os.path.dirname(sys.executable), 'ruff')
    if not os.path.exists(RUFF):
        RUFF = 'ruff'

    def ruff(*args):
        return subprocess.run([RUFF, *list(args)], capture_output=True, text=True,
                              cwd=os.path.dirname(os.path.abspath(__file__)))

    r = ruff('check', '--select', 'F', 'dal', 'services', 'views', 'models',
             'utils', 'database', 'config', 'main.py', 'tests')
    check("E", "ruff --select F پاک است", r.returncode == 0, r.stdout.strip()[-200:])

    r = ruff('check', 'dal', 'services', 'views', 'models', 'utils', 'database',
             'config', 'main.py', 'tests')
    total = len(re.findall(r'^[a-zA-Z0-9_/]+\.py:\d+:\d+:', r.stdout, re.M))
    check("E", "بدهیِ style کاهش یافته (زیر ۱۳۰۰)", total < 1300, str(total))

    star = [ln for ln, code in real_code_lines('models/__init__.py').items()
            if re.search(r'import\s*\*', code)]
    check("E", "هیچ star-import در models/__init__.py", not star, str(star))

    # بازصدورها: باید همچنان کار کنند
    try:
        from config.settings import GRADE_NAMES as G3
        from config.settings import GRADES as G1
        from config.settings import LIVING_STATUSES as G4
        from config.settings import STAFF_ROLES as G2
        ok_export = all([G1, G2, G3, G4])
    except Exception as e:
        ok_export = False
        print("     خطا:", e)
    check("E", "config.settings بازصدورهای constants را حفظ کرده", ok_export)
    try:
        from models import StaffRole as SR
        from models import UserRole as UR
        ok_models = UR is not None and SR is not None
    except Exception as e:
        ok_models = False
        print("     خطا:", e)
    check("E", "بستهٔ models enumها را بازصدور می‌کند", ok_models)

    # نگهبان: print های مدیریت خطا در DAL به logger تبدیل شده باشند
    dal_prints = []
    for root, dirs, files in os.walk('dal'):
        dirs[:] = [x for x in dirs if x != '__pycache__']
        for f in files:
            if f.endswith('.py'):
                p = os.path.join(root, f)
                for ln, code in real_code_lines(p).items():
                    if 'print(' in code:
                        dal_prints.append(f"{p}:{ln}")
    check("E", "هیچ print ای در لایهٔ داده نمانده", not dal_prints, str(dal_prints[:4]))

    # نگهبان: لایهٔ نمایش هم باید logger داشته باشد (۷۸ print حذف شد)
    view_prints = []
    for d in ('views', 'services', 'utils'):
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x != '__pycache__']
            for f in files:
                if f.endswith('.py'):
                    p = os.path.join(root, f)
                    for ln, code in real_code_lines(p).items():
                        if re.search(r'(?<![\w.])print\s*\(', code):
                            view_prints.append(f"{p}:{ln}")
    check("E", "هیچ print ای در views/services/utils نمانده",
          not view_prints, str(view_prints[:4]))

    # ماژول‌های مردهٔ دیگر نباید برگردند
    check("E", "صفحهٔ آزمایشی mena حذف شده",
          not os.path.exists('views/pages/test_promotion.py'))
    check("E", "ابزار وصله‌ای fix_ui_issues حذف شده",
          not os.path.exists('views/fix_ui_issues.py'))

    missing_logger = []
    for f in os.listdir('dal'):
        if not f.endswith('.py') or f.startswith('__'):
            continue
        src = read(os.path.join('dal', f))
        if re.search(r'logger\.(error|warning|debug)\(', src) and 'logger = get_logger' not in src:
            missing_logger.append(f)
    check("E", "هر DAL که لاگ می‌کند logger ماژولی دارد",
          not missing_logger, str(missing_logger))

    # نگهبان: UTC-aware بودن ستون‌های زمان در DAL تازه‌نوشته
    from dal.user_dal import UserDAL
    from models.user import User
    nu = User()
    nu.staff_id = st.id
    nu.username = "user_r8"
    nu.role = "teacher"
    with contextlib.redirect_stdout(buf):
        u = UserDAL().create(nu, raw_password='Aa12345678')
    check("E", "UserDAL.create کاربر را می‌سازد", u is not None and u.id is not None)

    # متدهای زمانی مدل‌ها نباید NameError بدهند (رگرسیون بازرسی هشتم)
    from datetime import datetime as _dt

    from models.analytics_models import AnalyticsDashboardData as AnalyticsSummary
    from models.base import BaseModel
    from models.individual_goal import IndividualGoal
    from models.notification import Notification
    from models.recommendation import Recommendation

    try:
        n = Notification()
        n.mark_as_read()
        n.mark_as_dismissed()
        rec = Recommendation()
        rec.implement()
        rec.complete(feedback='خوب')
        g = IndividualGoal()
        g.achieve(result='انجام شد')
        dash = AnalyticsSummary(observation_distribution=None, grade_distribution=[], competency_usage=[], intervention_stats=None, followup_stats=None, overdue_count=0, students_without_observation=0, observation_trend=[], intervention_trend=[], followup_trend=[])
        vals = [BaseModel.get_current_time(), n.read_at, n.dismissed_at,
                rec.implemented_at, rec.completed_at, g.achievement_date,
                dash.generated_at]
        aware = all(v and _dt.fromisoformat(v).tzinfo is not None for v in vals)
        check("E", "زمان مدل‌ها UTC-aware است (بدون NameError)", aware, str(vals[:3]))
    except Exception as e:
        check("E", "زمان مدل‌ها UTC-aware است (بدون NameError)", False,
              f"{type(e).__name__}: {e}")

    # ماژول وقت، تنها منبع زمان است
    check("E", "utils/time_utils تنها منبع زمان پروژه است",
          tu.count('def utc_now(') == 1 and 'from datetime import' in tu)

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
print(f"نتیجهٔ دور هشتم:  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های دور هشتم سبز است.")
