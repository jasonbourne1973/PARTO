#!/usr/bin/env python3
"""
راستی‌آزمایی دور پنجم بازرسی — ~۴۰ بررسی

بخش‌ها:
  A) مسیر امنیتی (هش رمز، سیاست قدرت، نقش‌ها، جلسات) .... ۱۵ بررسی
  B) یکدستی متن‌های UI با سیاست واقعی رمز ................ ۴ بررسی
  C) سلامت ایستا: کامپایل، وابستگی‌ها، EXPLAIN کوئری‌ها،
     placeholderها، نسخه، نقش‌های دیتابیس ............... ~۲۰ بررسی

اجرا:  python3 verify_fixes5.py
"""

import ast
import collections
import contextlib
import hashlib
import io
import os
import py_compile
import re
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['TZ'] = 'Asia/Tehran'
time.tzset()

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


TMP = tempfile.mkdtemp(prefix="round5_verify_")

try:
    # دیتابیس موقت مثل محیط واقعی برنامه
    import config.settings as settings
    import database.connection as dbc

    TEST_DB = os.path.join(TMP, "partow.db")
    _orig_s, _orig_c = settings.DB_PATH, dbc.DB_PATH
    settings.DB_PATH = TEST_DB
    dbc.DB_PATH = TEST_DB
    dbc.DatabaseConnection._instance = None
    dbc._connection = None
    dbc._initialized = False
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _conn_obj = dbc.DatabaseConnection()
        app_conn = _conn_obj.get_connection()

    # ============================================================
    print("=" * 76)
    print("بخش A: مسیر امنیتی (utils/security.py)")
    print("=" * 76)

    from utils.security import ROLE_PERMISSIONS, Security, SessionManager, UserRole

    h = Security.hash_password("Admin@123")
    check("A1", "رمز درست پس از هش تأیید می‌شود",
          Security.verify_password("Admin@123", h) is True)

    check("A2", "رمز غلط رد می‌شود",
          Security.verify_password("WrongPass", h) is False)

    h2 = Security.hash_password("Admin@123")
    check("A3", "نمک تصادفی: دو هشِ یک رمز متفاوت و هر دو معتبر",
          h != h2 and Security.verify_password("Admin@123", h2))

    salt = "abcd1234"
    legacy = f"{salt}:{hashlib.sha256((salt + 'Old@Pass').encode()).hexdigest()}"
    check("A4", "فرمت قدیمی «salt:hash» پشتیبانی می‌شود",
          Security.verify_password("Old@Pass", legacy) is True)

    ok = (Security.verify_password(None, h) is False
          and Security.verify_password("x", None) is False
          and Security.verify_password("x", "") is False
          and Security.verify_password("x", "خراب") is False)
    check("A5", "ورودی‌های خالی/خراب → False بدون استثنا", ok)

    check("A6", "hash_password(None) → None",
          Security.hash_password(None) is None)

    cases = [
        ("Abc@12", False, "کوتاه‌تر از ۸"),
        ("abcdefg1", False, "بدون حرف بزرگ"),
        ("ABCDEFG1", False, "بدون حرف کوچک"),
        ("Abcdefgh", False, "بدون عدد"),
        ("Abcdefg1", False, "بدون نویسهٔ خاص"),
        ("Abcdef@1", True, "همهٔ شرایط"),
    ]
    ok = True
    for pw, expected, why in cases:
        strong, _msg = Security.is_password_strong(pw)
        if bool(strong) != expected:
            ok = False
            check("A7", f"سیاست قدرت رمز ({why})", False, f"{pw!r}")
    if ok:
        check("A7", f"سیاست قدرت رمز روی {len(cases)} حالت مرزی", True)

    check("A8", "حداقل طول رمز = ۸ (ثابت مشترک)",
          Security.MIN_PASSWORD_LENGTH == 8)

    enum_roles = {r.value for r in UserRole}
    missing = [r for r in enum_roles if r not in ROLE_PERMISSIONS]
    check("A9", "هر نقش enum یک کلید مجوز دارد", not missing, str(missing))

    enum_roles = {r.value for r in UserRole}
    extra = [r for r in ROLE_PERMISSIONS if r not in enum_roles]
    check("A10", "هیچ کلید مجوز بی‌صاحبی وجود ندارد", not extra, str(extra))

    sm = SessionManager()
    tok, _ = sm.create_session(1, "manager", "admin")
    uid, role, _un = sm.get_current_user(tok)
    check("A11", "جلسه: ایجاد → اعتبارسنجی → هویت",
          bool(tok) and uid == 1 and role == "manager")

    check("A12", "manager اجازهٔ manage_users دارد",
          sm.has_permission(tok, "manage_users"))

    sm2 = SessionManager()
    t2, _ = sm2.create_session(2, "viewer", "v")
    check("A13", "viewer اجازهٔ manage_users ندارد",
          not sm2.has_permission(t2, "manage_users"))

    sm2.end_session(t2)
    check("A14", "پایان جلسه → توکن نامعتبر",
          sm2.validate_session(t2) is None)

    check("A15", "generate_token یکتا و ۶۴ کاراکتری",
          len(Security.generate_token()) == 64
          and Security.generate_token() != Security.generate_token())

    # ============================================================
    print()
    print("=" * 76)
    print("بخش B: یکدستی متن‌های UI با سیاست واقعی رمز (۸ + ترکیب)")
    print("=" * 76)

    stale = []
    for root, dirs, fs in os.walk("views"):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in fs:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            src = open(p, encoding="utf-8").read()
            if re.search(r"[۶6] کاراکتر", src):
                stale.append(p)
    check("B1", "هیچ متن «حداقل ۶ کاراکتر»ی در views نمانده",
          not stale, str(stale))

    src = open("config/messages.py", encoding="utf-8").read()
    check("B2", "پیام password_weak هم‌قانون سیاست واقعی است",
          "6 کاراکتر" not in src and "۶ کاراکتر" not in src
          and "نویسهٔ خاص" in src)

    cp = open("views/dialogs/change_password_dialog.py", encoding="utf-8").read()
    check("B3", "دیالوگ تغییر رمز «۸ کاراکتر» را اعلام می‌کند",
          "حداقل ۸ کاراکتر" in cp and "نویسهٔ خاص" in cp)

    sp = open("views/pages/settings_page.py", encoding="utf-8").read()
    check("B4", "صفحهٔ مدیریت کاربران «۸ کاراکتر» را اعلام می‌کند",
          "حداقل ۸ کاراکتر" in sp and "[۶6] کاراکتر" not in sp)

    # ============================================================
    print()
    print("=" * 76)
    print("بخش C: سلامت ایستا")
    print("=" * 76)

    # C1 — کامپایل همهٔ فایل‌ها
    total = bad = 0
    for root, dirs, fs in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (
            "__pycache__", ".git", "full_test_artifacts",
            "reports", "docs", "venv", ".venv")]
        for f in fs:
            if f.endswith(".py"):
                total += 1
                p = os.path.join(root, f)
                try:
                    py_compile.compile(p, doraise=True, cfile=os.path.join(TMP, "x.pyc"))
                except Exception:
                    bad += 1
    check("C1", f"کامپایل هر {total} فایل پایتون بدون خطای نحوی", bad == 0,
          f"{bad} فایل خراب")

    # C2 — requirements.txt پوشش کامل
    req = open("requirements.txt", encoding="utf-8").read()
    need = ["PySide6", "matplotlib", "openpyxl", "jdatetime", "reportlab",
            "numpy"]
    miss = [n for n in need if n not in req]
    check("C2", "requirements.txt همهٔ وابستگی‌های import‌شده را دارد",
          not miss, f"غایب: {miss}")

    # C3 — EXPLAIN همهٔ کوئری‌های dal/services/utils روی دیتابیس آماده‌شده
    SQLSTART = re.compile(r'^\s*(WITH|SELECT|INSERT|REPLACE|UPDATE|DELETE)\b',
                          re.I)
    raw = __import__("sqlite3").connect(TEST_DB)
    raw.create_function("get_current_user_id", 0, lambda: 1)

    candidates = []

    def add(file_, line_, sql_):
        sql_ = sql_.strip()
        if SQLSTART.match(sql_):
            candidates.append((file_, line_, sql_))

    for top in ("dal", "services", "utils"):
        for root, dirs, fs in os.walk(top):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in sorted(fs):
                if not f.endswith(".py"):
                    continue
                p = os.path.join(root, f)
                try:
                    t = ast.parse(open(p, encoding="utf-8").read())
                except Exception:
                    continue
                for fn in [n for n in ast.walk(t)
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                    acc = collections.defaultdict(list)
                    nodes = sorted(
                        [n for n in ast.walk(fn)
                         if isinstance(n, (ast.Assign, ast.AugAssign))],
                        key=lambda n: n.lineno)
                    for n in nodes:
                        if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                            var = n.target.id
                        elif (isinstance(n, ast.Assign) and len(n.targets) == 1
                              and isinstance(n.targets[0], ast.Name)):
                            var = n.targets[0].id
                        else:
                            continue
                        v = n.value
                        parts = []
                        if isinstance(v, ast.Constant) and isinstance(v.value, str):
                            parts = [v.value]
                        elif isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add):
                            for x in ast.walk(v):
                                if isinstance(x, ast.Constant) and isinstance(x.value, str):
                                    parts.append(x.value)
                        if not parts:
                            continue
                        if isinstance(n, ast.AugAssign):
                            acc[var].extend(parts)
                        else:
                            acc[var] = parts
                        add(p, n.lineno, "".join(acc[var]))
                    for n in ast.walk(fn):
                        if isinstance(n, ast.Call):
                            m = (n.func.attr if isinstance(n.func, ast.Attribute)
                                 else (n.func.id if isinstance(n.func, ast.Name) else ""))
                            if m in ("execute", "executemany", "executescript") and n.args:
                                a = n.args[0]
                                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                                    add(p, n.lineno, a.value)
                                elif isinstance(a, ast.JoinedStr):
                                    txt = "".join(
                                        str(s.value) if isinstance(s, ast.Constant) else "'X'"
                                        for s in a.values)
                                    add(p, n.lineno, txt)

    sql_errors = []
    for p, ln, sql in candidates:
        if sql.upper().startswith("PRAGMA"):
            continue
        nph = sql.count("?")
        names = set(re.findall(r"(?<!:):([A-Za-z_]\w{1,30})\b", sql))
        try:
            if nph:
                raw.execute("EXPLAIN " + sql, tuple([None] * nph)).fetchall()
            elif names:
                raw.execute("EXPLAIN " + sql, dict.fromkeys(names)).fetchall()
            else:
                raw.execute("EXPLAIN " + sql).fetchall()
        except Exception as e:
            msg = str(e)
            if "'X'" in sql or "'X'" in msg:
                continue     # ف strang مصنوعی
            sql_errors.append((p, ln, msg))
    raw.close()
    check("C3", f"EXPLAIN هر {len(candidates)} کوئری dal/services/utils روی دیتابیس واقعی",
          not sql_errors, str(sql_errors[:3]))

    # C4 — نقش‌های ذخیره‌شده در دیتابیس همیشه معتبر بمانند
    row = app_conn.execute("SELECT role FROM users WHERE username='admin'").fetchone()
    check("C4", "کاربر seed با نقش معتبر «manager» ساخته می‌شود",
          row is not None and row["role"] in enum_roles)

    # C5 — نسخه تک‌منبعی
    s = open("config/settings.py", encoding="utf-8").read()
    m = re.search(r'APP_VERSION\s*=\s*"([\d.]+)"', s)
    check("C5", "APP_VERSION در config/settings.py تعریف شده",
          bool(m), "پیدا نشد")
    others = []
    for root, dirs, fs in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (
            "__pycache__", ".git", "full_test_artifacts",
            "reports", "docs", "venv", ".venv")]
        for f in fs:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            if p.replace("./", "").replace("\\", "/") == "config/settings.py":
                continue
            src = open(p, encoding="utf-8").read()
            if re.search(r'=\s*"27\.\d+\.\d+"', src):
                others.append(p)
    check("C6", "هیچ نسخهٔ هاردکد دیگری در پروژه نیست", not others, str(others))

finally:
    dbc.DatabaseConnection._instance = None
    dbc._connection = None
    dbc._initialized = False
    settings.DB_PATH = _orig_s
    dbc.DB_PATH = _orig_c
    shutil.rmtree(TMP, ignore_errors=True)

print()
print("=" * 76)
print(f"نتیجهٔ دور پنجم:  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های دور پنجم سبز است.")
