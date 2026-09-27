"""
راستی‌آزمایی دور بیست‌ودوم — فاز ۳ (DEF-03): برابریِ Scope بین
get_by_id و get_by_ids در DALهای دارای هر دو متد.

مبنا: docs/tech_audit_20_fa.md (بخش ۳، فاز ۳) — ادامهٔ راستی‌آزمایی‌های
verify_fixes19/20/21.py.

یافته‌ها (شرح کامل در گزارش فاز ۳):
  • InterventionDAL: get_by_id از قبل با require_profile_scope محافظت
    می‌شد (دور نوزدهم)، اما get_by_ids هیچ بررسی Scope‌ای نداشت — یعنی
    TEACHER می‌توانست با گذر شناسه از مسیر دسته‌ای، بند IDOR در
    get_by_id را دور بزند. رفع شد: get_by_ids اکنون هر آیتم را با
    require_profile_scope می‌سنجد و طبق «سیاست الف» موارد خارج از
    Scope را بی‌سروصدا از دیکشنری نتیجه حذف می‌کند (چون این متد صرفاً
    ابزار داخلیِ ساخت نگاشت/غنی‌سازی در همهٔ نقاط فراخوانی است، نه یک
    API با ورودی مستقیم کاربر؛ get_by_id تک‌آیتمی رفتار رد صریح خودش
    (PermissionDeniedError) را حفظ می‌کند).
  • CompetencyDAL: get_by_id/get_by_ids هر دو بدون Scope هستند (داده‌ی
    مرجع/کاتالوگ مشترک، نه داده‌ی وابسته به دانش‌آموز) — از قبل هم‌ارز؛
    نقص نیست.
  • StudentDAL: get_by_id/get_by_ids هر دو بدون Scope هستند و طبق DD-6
    (که فقط زنجیرهٔ Observation/Intervention/Activity/FollowUp/
    Attachment را نام می‌برد، نه رکورد پایهٔ Student) این هم از قبل
    هم‌ارز و خارج از دامنهٔ DEF-03 است.
  • StudentAcademicProfileDAL: get_by_id/get_by_ids هر دو بدون Scope
    هستند (خارج از دامنهٔ محدود DEF-03 که فقط ناهم‌ارزیِ batch/single
    را هدف می‌گیرد؛ چون این‌جا هر دو از قبل یکسان‌اند). این یک یافتهٔ
    جانبیِ عمیق‌تر (نبود Scope حتی روی خواندن تکی) است که در گزارش
    فاز ۳ به‌عنوان «تصمیم طراحی لازم» به کاربر گزارش می‌شود، نه اینجا
    بی‌اجازه رفع می‌گردد.

نکتهٔ محیط: این فایل به Qt واقعی نیاز ندارد؛ در صورت نیاز با:

    LD_LIBRARY_PATH=/home/user/qtstub/lib QT_QPA_PLATFORM=offscreen \\
        python3 verify_fixes22.py

اجرا شود.
"""

import contextlib
import io
import os
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


TMP = tempfile.mkdtemp(prefix="round22_verify_")
TEST_DB = os.path.join(TMP, "partow.db")

import config.settings as settings
import database.connection as dbc

settings.DB_PATH = TEST_DB
dbc.DB_PATH = TEST_DB
dbc.DatabaseConnection._instance = None
dbc.DatabaseConnection._connection = None
dbc.DatabaseConnection._initialized = False

with contextlib.redirect_stdout(io.StringIO()):
    db = dbc.DatabaseConnection()
    conn = db.get_connection(user_id=1)

from utils.security import AccessControl, PermissionDeniedError

AccessControl.logout()

year_row = conn.execute(
    "SELECT id FROM academic_years WHERE is_active = 1 LIMIT 1").fetchone()
YEAR_ID = year_row["id"]

from dal.intervention_dal import InterventionDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.intervention import Intervention
from models.staff import Staff
from models.student import Student
from models.student_academic_profile import StudentAcademicProfile

student_dal = StudentDAL()
profile_dal = StudentAcademicProfileDAL()
intervention_dal = InterventionDAL()


def new_student(last_name, national_code):
    s = Student()
    s.first_name = "آزمون۲۲"
    s.last_name = last_name
    s.national_code = national_code
    return student_dal.create(s)


def new_profile(student_id):
    p = StudentAcademicProfile()
    p.student_id = student_id
    p.academic_year_id = YEAR_ID
    p.grade = 1
    p.class_name = "اول-الف"
    return profile_dal.create(p)


def new_intervention(profile_id, description="مداخلهٔ آزمون۲۲"):
    i = Intervention()
    i.student_profile_id = profile_id
    i.staff_id = 1
    i.type = "گفتگوی فردی"
    i.date = "1404/01/01"
    i.description = description
    return intervention_dal.create(i)


def assign_teacher(staff_id, student_id, is_active=1, is_deleted=0):
    conn.execute(
        """
        INSERT INTO teacher_assignments
            (student_id, staff_id, academic_year_id, is_active, is_deleted)
        VALUES (?, ?, ?, ?, ?)
        """,
        (student_id, staff_id, YEAR_ID, is_active, is_deleted),
    )
    conn.commit()


def login_teacher(username):
    saved = AccessControl.current_staff_id()
    AccessControl.logout()
    staff = Staff()
    staff.full_name = f"معلم {username}"
    staff.role = "other"
    staff_id = StaffDAL().create(staff).id
    conn.execute(
        "INSERT INTO users (staff_id, username, password_hash, role, is_active) "
        "VALUES (?, ?, 'x', 'teacher', 1)",
        (staff_id, username),
    )
    conn.commit()
    if saved is not None:
        AccessControl.login(saved, None)
    AccessControl.login(staff_id, None)
    return staff_id


def login_manager(username):
    AccessControl.logout()
    staff = Staff()
    staff.full_name = f"مدیر {username}"
    staff.role = "other"
    staff_id = StaffDAL().create(staff).id
    conn.execute(
        "INSERT INTO users (staff_id, username, password_hash, role, is_active) "
        "VALUES (?, ?, 'x', 'manager', 1)",
        (staff_id, username),
    )
    conn.commit()
    AccessControl.login(staff_id, None)
    return staff_id


# ============================================================
# بخش C: DEF-03 — برابری Scope بین get_by_id و get_by_ids
# ============================================================
print("=" * 76)
print("بخش C: DEF-03 — برابری Scope بین get_by_id و get_by_ids")
print("=" * 76)

AccessControl.logout()
assigned_student = new_student("منتسب۲۲", "9800000001")
unassigned_student = new_student("غیرمنتسب۲۲", "9800000002")
assigned_profile = new_profile(assigned_student.id)
unassigned_profile = new_profile(unassigned_student.id)
assigned_intervention = new_intervention(assigned_profile.id, "مداخلهٔ منتسب")
unassigned_intervention = new_intervention(unassigned_profile.id, "مداخلهٔ غیرمنتسب")
AccessControl.logout()

# C1: پیش از رفع، get_by_id از قبل محافظت می‌شد (بازبینیِ عدم‌رگرسیون)
teacher_id = login_teacher("t_v22_1")
assign_teacher(teacher_id, assigned_student.id)

c1_ok = intervention_dal.get_by_id(assigned_intervention.id) is not None
c1_raised = False
try:
    intervention_dal.get_by_id(unassigned_intervention.id)
except PermissionDeniedError:
    c1_raised = True
check("C", "C1: get_by_id تک‌آیتمی هنوز رفتار رد صریح خودش را دارد (بدون رگرسیون)",
      c1_ok and c1_raised)

# C2: هستهٔ رفع — get_by_ids دیگر شناسهٔ خارج از Scope را برنمی‌گرداند
c2_map = intervention_dal.get_by_ids(
    [assigned_intervention.id, unassigned_intervention.id])
check("C", "C2: TEACHER با get_by_ids فقط مداخلهٔ منتسب را می‌بیند (IDOR بسته شد)",
      assigned_intervention.id in c2_map and unassigned_intervention.id not in c2_map)

# C3: وقتی همهٔ شناسه‌ها خارج از Scope‌اند، دیکشنری خالی برمی‌گردد نه استثنا
c3_raised = False
try:
    c3_map = intervention_dal.get_by_ids([unassigned_intervention.id])
except PermissionDeniedError:
    c3_raised = True
    c3_map = None
check("C", "C3: get_by_ids با ورودیِ کاملاً خارج از Scope استثنا بالا نمی‌برد (سیاست الف)",
      not c3_raised and c3_map == {})

# C4: نقش نامحدود (MANAGER) — هر دو مداخله را می‌بیند
login_manager("m_v22_1")
c4_map = intervention_dal.get_by_ids(
    [assigned_intervention.id, unassigned_intervention.id])
check("C", "C4: MANAGER با get_by_ids طبق DD-6 محدودیتی ندارد",
      assigned_intervention.id in c4_map and unassigned_intervention.id in c4_map)

# C5: بافت بدون نشست (DD-4) — سازگار با get_by_id
AccessControl.logout()
c5_map = intervention_dal.get_by_ids(
    [assigned_intervention.id, unassigned_intervention.id])
check("C", "C5: بافت بدون نشست (سیستمی/اسکریپت) در get_by_ids هم مثل get_by_id مجاز است",
      assigned_intervention.id in c5_map and unassigned_intervention.id in c5_map)

# C6: مصرف‌کنندهٔ واقعی — نگاشتِ چندشناسهٔ ترکیبی (منتسب + غیرموجود + خارج از Scope)
teacher_id2 = login_teacher("t_v22_2")
assign_teacher(teacher_id2, assigned_student.id)
mixed_ids = [assigned_intervention.id, unassigned_intervention.id, 987654321]
c6_map = intervention_dal.get_by_ids(mixed_ids)
check("C", "C6: ترکیب شناسهٔ منتسب/خارج‌از‌Scope/ناموجود → فقط منتسب برمی‌گردد",
      c6_map == {assigned_intervention.id: c6_map.get(assigned_intervention.id)})

AccessControl.logout()

print("=" * 76)
print(f"نتیجهٔ دور بیست‌ودوم (فاز ۳ — DEF-03):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
