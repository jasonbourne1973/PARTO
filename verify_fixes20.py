"""
راستی‌آزمایی دور بیستم — «دستورالعمل تکمیلی اصلاح نواقص باقی‌مانده پس از
Master Audit» (مبنا: commit 8c69b3f، شاخهٔ arena/01a0ddf1-parto)

این فایل به‌مرور، همراه با اجرای هر فاز از docs/tech_audit_20_fa.md،
تکمیل می‌شود (دقیقاً هم‌الگو با verify_fixes19.py برای دور قبل).

بخش‌ها:
  A) DEF-01 — StudentAcademicProfileDAL.update() اکنون Permission
     (EDIT_STUDENT) و Scope (DD-6) بی‌قیدوشرط دارد (هم رکورد موجود، هم
     دانش‌آموزِ مقصد اگر جابه‌جا شود). create() عمداً بدون تغییر ماند
     (دلیل کامل در docstring خودِ متد و در tests/test_def01_profile_scope.py)؛
     به‌جایش services/observation_service.py و
     services/intervention_service.py (_get_or_create_profile) اکنون
     Scope را زودهنگام (fail-fast) بررسی می‌کنند و مسیر «معلم دانش‌آموز
     تازه می‌سازد» (بدون Scope، چون انتسابی نمی‌تواند وجود داشته باشد)
     دست‌نخورده باقی مانده است.

نکتهٔ محیط: این فایل به Qt واقعی نیاز ندارد؛ اما اگر بعداً بخش‌های GUI
اضافه شد، با:

    LD_LIBRARY_PATH=/home/user/qtstub/lib QT_QPA_PLATFORM=offscreen \\
        python3 verify_fixes20.py

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


TMP = tempfile.mkdtemp(prefix="round20_verify_")
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


def make_staff_and_user(role, username):
    """ساخت staff+user با نقش دلخواه در «بافت سیستمی» (بدون نشست جاری)"""
    from dal.staff_dal import StaffDAL
    from dal.user_dal import UserDAL
    from models.staff import Staff
    from models.user import User

    saved = AccessControl.current_staff_id()
    AccessControl.logout()
    try:
        staff = Staff()
        staff.full_name = f"آزمون {role}"
        staff.role = "other"
        staff_id = StaffDAL().create(staff).id

        user = User()
        user.staff_id = staff_id
        user.username = username
        user.role = role
        user.is_active = 1
        UserDAL().create(user, raw_password="Passw0rd!123")
    finally:
        if saved is not None:
            AccessControl.login(saved, None)
    return staff_id


def login(staff_id):
    AccessControl.login(staff_id, None)


def assign_teacher(student_id, staff_id, academic_year_id, is_active=1, is_deleted=0):
    conn.execute(
        """
        INSERT INTO teacher_assignments
            (student_id, staff_id, academic_year_id, is_active, is_deleted)
        VALUES (?, ?, ?, ?, ?)
        """,
        (student_id, staff_id, academic_year_id, is_active, is_deleted),
    )
    conn.commit()


year_row = conn.execute(
    "SELECT id FROM academic_years WHERE is_active = 1 LIMIT 1").fetchone()
YEAR_ID = year_row["id"]

from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.student import Student
from models.student_academic_profile import StudentAcademicProfile

student_dal = StudentDAL()
profile_dal = StudentAcademicProfileDAL()


def new_student(last_name, national_code):
    s = Student()
    s.first_name = "آزمون۲۰"
    s.last_name = last_name
    s.national_code = national_code
    return student_dal.create(s)


def new_profile(student_id, academic_year_id=None):
    p = StudentAcademicProfile()
    p.student_id = student_id
    p.academic_year_id = academic_year_id or YEAR_ID
    p.grade = 1
    p.class_name = "اول-الف"
    return profile_dal.create(p)


# ============================================================
# بخش A: DEF-01 — StudentAcademicProfileDAL.update() Permission+Scope
# ============================================================
print("=" * 76)
print("بخش A: DEF-01 — StudentAcademicProfileDAL.update() اکنون "
      "Permission (EDIT_STUDENT) + Scope (DD-6) بی‌قیدوشرط دارد")
print("=" * 76)

# A1: بدون مجوز → رد
viewer_id = make_staff_and_user("viewer", "v20_1")
s1 = new_student("الف۲۰", "9600000001")
p1 = new_profile(s1.id)
login(viewer_id)
a1_blocked = False
try:
    p1.grade = 2
    profile_dal.update(p1)
except PermissionDeniedError:
    a1_blocked = True
AccessControl.logout()
check("A", "A1: VIEWER بدون EDIT_STUDENT از update() رد می‌شود", a1_blocked)

# A2: معلم خارج از Scope → رد
teacher_id = make_staff_and_user("teacher", "t20_1")
s2 = new_student("ب۲۰", "9600000002")
p2 = new_profile(s2.id)
login(teacher_id)
a2_blocked = False
try:
    p2.grade = 2
    profile_dal.update(p2)
except PermissionDeniedError:
    a2_blocked = True
AccessControl.logout()
check("A", "A2: TEACHER خارج از Scope از update() رد می‌شود", a2_blocked)

# A3: معلم داخل Scope → موفق
teacher_id2 = make_staff_and_user("teacher", "t20_2")
s3 = new_student("ج۲۰", "9600000003")
p3 = new_profile(s3.id)
assign_teacher(s3.id, teacher_id2, YEAR_ID)
login(teacher_id2)
p3.grade = 4
saved3 = profile_dal.update(p3)
AccessControl.logout()
check("A", "A3: TEACHER داخل Scope می‌تواند update() کند", saved3 is not None and saved3.grade == 4)

# A4: مدیر بدون محدودیت Scope
s4 = new_student("د۲۰", "9600000004")
p4 = new_profile(s4.id)
p4.grade = 5
saved4 = profile_dal.update(p4)
check("A", "A4: MANAGER (بدون نشست/سیستمی) از update() رد نمی‌شود", saved4 is not None)

# A5: انتقال متقاطع دانش‌آموز — رد
teacher_id3 = make_staff_and_user("teacher", "t20_3")
s5a = new_student("ه۲۰-الف", "9600000005")
s5b = new_student("ه۲۰-ب", "9600000006")
p5 = new_profile(s5a.id)
assign_teacher(s5a.id, teacher_id3, YEAR_ID)
login(teacher_id3)
a5_blocked = False
try:
    p5.student_id = s5b.id
    profile_dal.update(p5)
except PermissionDeniedError:
    a5_blocked = True
AccessControl.logout()
check("A", "A5: انتقال پرونده به دانش‌آموزِ خارج از Scope (cross-student) رد می‌شود", a5_blocked)

# A6: create() عمداً بدون Scope — مسیر «دانش‌آموز تازه» نباید بشکند
teacher_id4 = make_staff_and_user("teacher", "t20_4")
login(teacher_id4)
from services.student_service import StudentService

a6_ok = True
try:
    new_stu = StudentService().create_student({
        "first_name": "دانش‌آموز",
        "last_name": "تازهٔ۲۰",
        "national_code": "9600000007",
        "grade": 1,
        "class_name": "اول-ب",
    })
    a6_ok = bool(new_stu and new_stu.id)
except PermissionDeniedError:
    a6_ok = False
AccessControl.logout()
prof_count = conn.execute(
    "SELECT COUNT(*) c FROM student_academic_profiles WHERE student_id = ?",
    (new_stu.id if a6_ok else -1,)).fetchone()["c"] if a6_ok else 0
check("A", "A6: TEACHER هنوز می‌تواند دانش‌آموز تازه + پروندهٔ خودکارش را بسازد "
      "(create() عمداً بدون Scope مانده — رگرسیون‌سنج)",
      a6_ok and prof_count == 1)

# A7: ایجاد خودکار پروندهٔ سالانه در جریان ثبت مشاهده — fail-fast Scope
from services.observation_service import ObservationService

teacher_id5 = make_staff_and_user("teacher", "t20_5")
s7 = new_student("و۲۰", "9600000008")
login(teacher_id5)
a7_blocked = False
try:
    ObservationService().create_observation({
        "student_id": s7.id,
        "staff_id": teacher_id5,
        "observation_date": "1404/01/01",
        "behavior": "رفتار آزمون ۲۰",
        "description": "توضیح آزمون ۲۰",
        "behavior_type": "خنثی",
    })
except PermissionDeniedError:
    a7_blocked = True
AccessControl.logout()
leaked_profile = conn.execute(
    "SELECT COUNT(*) c FROM student_academic_profiles WHERE student_id = ?",
    (s7.id,)).fetchone()["c"]
check("A", "A7: ثبت مشاهده برای معلمِ خارج از Scope رد می‌شود و اثر جانبیِ "
      "«ساختِ پروندهٔ سالانه» هم rollback می‌شود (نه فقط خودِ مشاهده)",
      a7_blocked and leaked_profile == 0)

# A8: همان حالت با انتساب صحیح → موفق
teacher_id6 = make_staff_and_user("teacher", "t20_6")
s8 = new_student("ز۲۰", "9600000009")
assign_teacher(s8.id, teacher_id6, YEAR_ID)
login(teacher_id6)
obs8 = ObservationService().create_observation({
    "student_id": s8.id,
    "staff_id": teacher_id6,
    "observation_date": "1404/01/01",
    "behavior": "رفتار آزمون ۲۰-ب",
    "description": "توضیح آزمون ۲۰-ب",
    "behavior_type": "خنثی",
})
AccessControl.logout()
check("A", "A8: ثبت مشاهده برای معلمِ داخل Scope با موفقیت انجام می‌شود "
      "(پرونده + مشاهده هر دو ساخته می‌شوند)",
      obs8 is not None and obs8.id is not None)

AccessControl.logout()

# ============================================================
print("=" * 76)
print(f"نتیجهٔ دور بیستم (فاز ۱ — DEF-01):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
if FAILURES:
    print("موارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
print("=" * 76)

with contextlib.suppress(Exception):
    dbc.DatabaseConnection().close_all()

sys.exit(1 if FAIL else 0)
