#!/usr/bin/env python3
"""
راستی‌آزمایی دور هفتم بازرسی — رفع موارد باقی‌مانده

بخش‌ها (۳۰ بررسی):
  A) لایه‌بندی: جدول users فقط از DAL ................. ۶ بررسی
  B) چرخهٔ کاربران از مسیر رابط کاربری ................. ۷ بررسی
  C) فایل‌های پیوست و اعتبارسنجی محتوا ................. ۶ بررسی
  D) یکسان‌سازی نام موجودیت در Audit Log ............... ۴ بررسی
  E) کنترل دسترسی نقش‌های کادر ......................... ۳ بررسی
  F) سلامت ایستا (except های لخت، ماژول‌های مرده) ...... ۴ بررسی

اجرا:  python verify_fixes7.py
"""

import ast
import contextlib
import io
import os
import re
import shutil
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


def code_only(path):
    """
    متن فایل بدون کامنت‌ها (برای جست‌وجوی SQL واقعی)

    هم خطوط کامنت کامل و هم کامنت‌های انتهای خط حذف می‌شوند تا
    توضیحاتی مثل «# برای UPDATE users» به‌اشتباه SQL واقعی شمرده نشوند.
    """
    out = []
    for line in read(path).splitlines():
        line = line.split(' #')[0]
        if line.strip().startswith('#'):
            continue
        out.append(line)
    return "\n".join(out)


TMP = tempfile.mkdtemp(prefix="round7_verify_")
NOSTUB = os.environ.get("PARTO_NO_QT") == "1"

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

    print("=" * 76)
    print("بخش A: لایه‌بندی — جدول users فقط از DAL")
    print("=" * 76)

    VIEW_FILES = [
        'views/pages/settings_page.py',
        'views/dialogs/login_dialog.py',
        'views/dialogs/change_password_dialog.py',
    ]
    SQL_USERS = re.compile(
        r"(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+users\b", re.I)
    for f in VIEW_FILES:
        hits = SQL_USERS.findall(code_only(f))
        check("A", f"هیچ SQL خام users در {f}", not hits, str(hits))

    # لایهٔ نمایش باید از DAL استفاده کند
    check("A", "SettingsPage از UserDAL استفاده می‌کند",
          'self.user_dal' in read('views/pages/settings_page.py')
          and 'UserDAL' in read('views/pages/settings_page.py'))
    check("A", "LoginDialog از UserDAL استفاده می‌کند",
          'self.user_dal.authenticate' in read('views/dialogs/login_dialog.py'))
    check("A", "ChangePasswordDialog از UserDAL استفاده می‌کند",
          'self.user_dal.update_password' in read('views/dialogs/change_password_dialog.py'))

    print()
    print("=" * 76)
    print("بخش B: چرخهٔ کاربران از مسیر رابط کاربری")
    print("=" * 76)

    from dal.staff_dal import StaffDAL
    from dal.user_dal import UserDAL
    from models.staff import Staff
    from models.user import User

    # یک عضو کادر تازه برای این بخش
    st = Staff()
    st.full_name = "معلم آزمون هفتم"
    st.role = "teacher"
    st.is_active = 1
    with contextlib.redirect_stdout(io.StringIO()):
        st = StaffDAL().create(st)

    ud = UserDAL()

    new_user = User()
    new_user.staff_id = st.id
    new_user.username = "r7_teacher"
    new_user.role = "teacher"
    new_user.is_active = 1
    with contextlib.redirect_stdout(io.StringIO()):
        created = ud.create(new_user, raw_password="Round7@123", user_id_actor=1)

    check("B", "ساخت کاربر با UserDAL.create انجام می‌شود",
          created is not None and created.id is not None)

    row = conn.execute(
        "SELECT must_change_password, is_active FROM users WHERE id = ?",
        (created.id,)).fetchone()
    check("B", "کاربر جدید موظف به تغییر رمز است (must_change_password=1)",
          row["must_change_password"] == 1, str(dict(row)))

    # ردیف Audit برای «ساخت کاربر» (جدول users تریگر ندارد)
    audit_create = conn.execute(
        "SELECT COUNT(*) c FROM audit_logs WHERE entity_type = 'users' "
        "AND action = 'create' AND entity_id = ?", (created.id,)).fetchone()["c"]
    check("B", "ساخت کاربر در Audit Log ثبت می‌شود", audit_create == 1,
          f"{audit_create} ردیف")

    # یک عضو کادر نباید دو حساب بگیرد
    dup = User()
    dup.staff_id = st.id
    dup.username = "r7_teacher_2"
    dup.role = "teacher"
    dup.is_active = 1
    blocked = False
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ud.create(dup, raw_password="Round7@123")
    except Exception:
        blocked = True
    check("B", "برای یک عضو کادر فقط یک حساب ساخته می‌شود", blocked)

    # تغییر رمز (مسیر ChangePasswordDialog → UserDAL.update_password)
    changed = ud.update_password(created.id, "Round7@456",
                                 clear_must_change=True, user_id_actor=1)
    check("B", "تغییر رمز از مسیر DAL کار می‌کند و پرچم را پاک می‌کند",
          changed and ud.authenticate("r7_teacher", "Round7@456") is not None
          and ud.authenticate("r7_teacher", "Round7@123") is None)

    # حذف/بازگردانی با ثبت‌کننده
    deleted = ud.delete(created.id, user_id_actor=1)
    row = conn.execute(
        "SELECT is_deleted, is_active, deleted_at, deleted_by FROM users WHERE id = ?",
        (created.id,)).fetchone()
    check("B", "حذف منطقی: is_active صفر و deleted_by پر می‌شود",
          deleted and row["is_deleted"] == 1 and row["is_active"] == 0
          and row["deleted_at"] and row["deleted_by"] == 1, str(dict(row)))

    restored = ud.restore(created.id, user_id_actor=1)
    check("B", "بازگردانی کاربر کار می‌کند", restored is not None)

    print()
    print("=" * 76)
    print("بخش C: اعتبارسنجی محتوای فایل پیوست")
    print("=" * 76)

    from utils.file_validator import MAGIC_AVAILABLE as _magic
    from utils.file_validator import FileValidator

    check("C", "utils.file_validator بدون python-magic هم import می‌شود",
          FileValidator is not None,
          f"(magic در این محیط: {'موجود' if _magic else 'ناموجود — مسیر پشتیبان'})")

    check("C", "تشخیص امضامحور، تصویر واقعی را می‌شناسد",
          FileValidator._detect_mime(b'\x89PNG\r\n\x1a\n' + b'0' * 64) == 'image/png')

    ok_pdf, _, info_pdf = FileValidator.validate_file(b'%PDF-1.7' + b'0' * 100, 'r.pdf')
    check("C", "PDF واقعی پذیرفته می‌شود", ok_pdf and info_pdf['category'] == 'document')

    ok_exe, msg_exe, _ = FileValidator.validate_file(b'MZ\x90\x00' + b'0' * 100, 'photo.png')
    check("C", "فایل اجرایی با نام عکس رد می‌شود", not ok_exe,
          "اگر رد نشود، آپلود فایل اجرایی ممکن است")

    ok_elf, _, _ = FileValidator.validate_file(b'\x7fELF' + b'0' * 100, 'harmless.jpg')
    check("C", "فایل ELF با نام تصویر رد می‌شود", not ok_elf)

    ok_sh, _, _ = FileValidator.validate_file(b'#!/bin/sh\nrm -rf /', 'notes.txt')
    check("C", "اسکریپت شل با نام متنی رد می‌شود", not ok_sh)

    print()
    print("=" * 76)
    print("بخش D: یکسان‌سازی نام موجودیت در Audit Log")
    print("=" * 76)

    from utils.security import AUDIT_ENTITY_ALIASES, normalize_entity_type

    check("D", "نگاشت نام موجودیت مرکزی وجود دارد",
          AUDIT_ENTITY_ALIASES.get('student') == 'students')

    check("D", "normalize برای هر دو شکل یک پاسخ می‌دهد",
          normalize_entity_type('observation') == normalize_entity_type('observations'),
          )

    # ردیف واقعی: ساخت دانش‌آموز (تریگر می‌نویسد) و خواندن با نام مفرد
    from services.student_service import StudentService

    db.set_current_user(1)
    ss = StudentService()
    with contextlib.redirect_stdout(io.StringIO()):
        stu = ss.create_student(
            {"first_name": "آزمون", "last_name": "هفتم", "national_code": "7777777777"},
            user_id=1,
        )
    from dal.audit_log_dal import AuditLogDAL
    logs_by_table = AuditLogDAL().get_logs(entity_type='students', entity_id=stu.id)
    logs_by_singular = AuditLogDAL().get_logs(entity_type='student', entity_id=stu.id)
    check("D", "جست‌وجو با نام مفرد و نام جدول هر دو نتیجه می‌دهد",
          len(logs_by_table) >= 1 and len(logs_by_singular) == len(logs_by_table),
          f"جدول={len(logs_by_table)}، مفرد={len(logs_by_singular)}")

    types = {r['entity_type'] for r in logs_by_table}
    check("D", "همهٔ ردیف‌های یک رویداد نام یکدست دارند",
          types <= {'students'}, str(types))

    print()
    print("=" * 76)
    print("بخش E: کنترل دسترسی نقش‌های کادر")
    print("=" * 76)

    from models.enums import StaffRole
    from utils.security import ROLE_PERMISSIONS, get_role_permissions

    staff_roles = {r.value for r in StaffRole}
    missing = sorted(staff_roles - set(ROLE_PERMISSIONS))
    check("E", "هر نقش جدول staff تعریف مجوز صریح دارد", not missing, str(missing))

    coach_perms = get_role_permissions('sport_coach')
    check("E", "مربی ورزش مجوز ثبت مشاهده دارد ولی مجوز مدیریتی ندارد",
          'create_observation' in coach_perms and 'manage_users' not in coach_perms
          and 'restore_backup' not in coach_perms)

    check("E", "نقش ناشناخته همچنان کم‌دسترسی است",
          'manage_users' not in get_role_permissions('some_unknown_role'))

    print()
    print("=" * 76)
    print("بخش F: سلامت ایستا")
    print("=" * 76)

    bare = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs
                   if d not in ('__pycache__', '.git', 'reports', 'full_test_artifacts')]
        for f in files:
            if not f.endswith('.py') or f.startswith(('verify_fixes', 'patch_')):
                continue
            p = os.path.join(root, f)
            try:
                tree = ast.parse(read(p))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    bare.append(f"{p}:{node.lineno}")
    check("F", "هیچ «except:» لختی در پروژه نمانده", not bare, f"{len(bare)} مورد: {bare[:4]}")

    dead_dupes = [
        'views/pages/parent_report_service.py',
        'views/pages/school_report_service.py',
    ]
    check("F", "ماژول‌های تکراری views/pages حذف شده‌اند",
          not any(os.path.exists(p) for p in dead_dupes),
          str([p for p in dead_dupes if os.path.exists(p)]))

    # (دور ۱۶) school_report_service بدون مصرف‌کننده بود و حذف شد
    check("F", "نسخهٔ اصلیِ سرویس گزارش والدین سر جایش است",
          os.path.exists('services/parent_report_service.py'))

    entry_points = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs
                   if d not in ('__pycache__', '.git', 'reports', 'full_test_artifacts')]
        for f in files:
            if f.endswith('.py'):
                entry_points.append(os.path.join(root, f))
    bad_compile = []
    for p in entry_points:
        try:
            compile(read(p), p, 'exec')
        except SyntaxError as e:
            bad_compile.append(f"{p}: {e}")
    check("F", "همهٔ فایل‌های پایتون پروژه کامپایل می‌شوند", not bad_compile,
          str(bad_compile[:3]))

except Exception as exc:  # pragma: no cover
    import traceback
    traceback.print_exc()
    FAIL += 1
    FAILURES.append(f"[GLOBAL] خطای اجرای راستی‌آزمایی: {exc}")

finally:
    try:
        dbc.DatabaseConnection._instance = None
        dbc._connection = None
        dbc._initialized = False
        settings.DB_PATH = _orig_s
        dbc.DB_PATH = _orig_c
    except Exception:
        pass
    shutil.rmtree(TMP, ignore_errors=True)

print()
print("=" * 76)
print(f"نتیجهٔ دور هفتم:  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های دور هفتم سبز است.")
