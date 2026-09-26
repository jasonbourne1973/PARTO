"""
راستی‌آزمایی دور نوزدهم — مرحلهٔ ۱: مرز مجوز create/update برای
Student/Observation/Intervention/Followup/Attachment + ایمپورت Excel
(سند مدیر پروژه، بخش‌های ۹/۱۰ — گسترش دامنه به «همهٔ create/update»
طبق تصمیم کاربر expand_all_create) + مرحلهٔ ۲: زیرساخت مشترک Scope/IDOR
+ مرحلهٔ ۳: سیم‌کشی IDOR/Scope در سطح Object روی InterventionDAL و
FollowUpDAL (خواندن مستقیم با ID، ساخت، و Cross-resource)
+ مرحلهٔ ۴: همان الگو برای ObservationDAL؛ Scope مستقل روی
AttachmentService برای هر ۷ نوع entity_type؛ و — طبق تصمیم صریح مدیر
پروژه dd1_scope=add_scope_only — افزودن *فقط* Scope (بدون اختراع
Permission) به CounselingSessionDAL/ExtracurricularDAL/GoalDAL که طبق
DD-1 هنوز هیچ Permission‌ای در enum ندارند.
+ مرحلهٔ ۵: رفع نشت Exception خام (ERR-01/ERR-LEAK-01) — الگوی
`ServiceError(f"...{e!s}")` در سراسر services/*.py و
base_service.execute_in_transaction حذف شد؛ کمکی مشترک
`BaseService._safe_service_error` جایگزینِ امنِ آن است که پیام‌های
عمدیِ از پیش امن (ValidationError/«یافت نشد») را دست‌نخورده نگه می‌دارد
ولی متن خامِ Exception سیستمی/DB/فایل را با پیام عمومیِ user_visible=False
جایگزین می‌کند.

پیش از این دور، AccessControl.require_permission فقط روی delete/restore
و چند عملیات مدیریتی اعمال شده بود؛ create/update چهار موجودیت اصلی و
تمام عملیات پیوست (Attachment) بدون هیچ کنترل مجوزی بودند — یعنی نقش
VIEWER (که فقط باید VIEW_* داشته باشد) می‌توانست مستقیماً دانش‌آموز/
مشاهده/مداخله/پیگیری بسازد یا فایل پیوست کند/حذف کند.

بخش‌ها:
  A) DAL-level: create/update چهار DAL اصلی برای VIEWER رد می‌شود؛
     برای نقش دارای مجوز (مثلاً TEACHER برای Student) انجام می‌شود.
  B) Service-level: execute_in_transaction دیگر PermissionDeniedError
     را در یک ServiceError عمومی پنهان نمی‌کند (نوع دقیق استثنا حفظ
     می‌شود) — رگرسیون روی base_service.py.
  C) ایمپورت Excel: بررسی مجوز CREATE_STUDENT *پیش از* بررسی نصب‌بودن
     openpyxl/وجود فایل انجام می‌شود (مرز امنیتی نباید به وضعیت محیط
     وابسته باشد)؛ کاربر بی‌مجوز با یک پیام روشن رد می‌شود، نه با
     شکست تک‌تک ردیف‌ها.
  D) Attachment: عملیات آپلود/دریافت/حذف/بازیابی از ENTITY_PERMISSION_MAP
     (سیاست DD-6: «همان مجوز موجودیت والد») استفاده می‌کنند؛ VIEWER
     برای entity_type='student' رد می‌شود، MANAGER مجاز است.
  E) UI: دکمه‌های افزودن/ایمپورت/ویرایش صفحه‌های دانش‌آموزان، مشاهدات،
     مداخلات و پیگیری‌ها برای نقش بی‌مجوز غیرفعال‌اند (هماهنگی UI↔backend
     طبق الگوی موجود دکمهٔ 🗑️، DD-5).
  F) مرحلهٔ ۲ — زیرساخت مشترک Scope: AccessControl.has_student_scope /
     require_student_scope دقیقاً طبق DD-6 عمل می‌کنند: فقط TEACHER با
     انتساب فعال محدود است؛ نقش‌های دیگر (و بافت بدون نشست) بدون
     محدودیت‌اند. (تست‌های کامل‌تر و مستقل در tests/test_scope_boundary.py)
  G) مرحلهٔ ۳ — IDOR/Scope در سطح Object: InterventionDAL.get_by_id/
     create و FollowUpDAL.get_by_id/create اکنون زنجیرهٔ
     FollowUp→Intervention→Profile→Student→Scope را بررسی می‌کنند؛
     TEACHER نمی‌تواند با ID مستقیم رکورد دانش‌آموز خارج از Scope خود
     را بخواند، و نمی‌تواند پیگیری را به مداخلهٔ خارج از Scope وصل کند
     (Cross-resource). (تست‌های کامل‌تر و مستقل، شامل update/delete/
     restore، در tests/test_intervention_followup_scope.py)
  H) مرحلهٔ ۴ — ObservationDAL.get_by_id همان زنجیرهٔ Scope را دارد؛
     CounselingSessionDAL/ExtracurricularDAL/GoalDAL که طبق DD-1
     Permission ندارند، حالا Scope مستقل می‌گیرند (dd1_scope=
     add_scope_only)؛ AttachmentService._require_entity_scope روی هر
     ۷ نوع entity_type (فراتر از ۴ تای ENTITY_PERMISSION_MAP) اعمال
     می‌شود. (تست‌های کامل‌تر در tests/test_stage4_scope.py)
  I) مرحلهٔ ۵ — رفع نشت Exception خام: کلاس‌های AppError (Database/
     DataIntegrityError همیشه user_visible=False)؛ ErrorHandler پیامِ
     user_visible=False را با پیام عمومی جایگزین می‌کند؛ شبیه‌سازی
     RuntimeError خام در ObservationService/execute_in_transaction
     دیگر متن خام را نشان نمی‌دهد؛ پیام‌های عمدیِ امن («یافت نشد»،
     شکستِ گویای ذخیرهٔ پیشنهاد) دست‌نخورده می‌مانند. (تست‌های کامل‌تر
     در tests/test_error_leak.py)
  J) مرحلهٔ ۶ — رفع باگ‌های Query/Pagination (سند بخش‌های ۲/۳/۲۵/۳۵):
     یک اعتبارسنج مشترک utils.pagination.normalize_limit_offset اضافه
     شد (limit=None بدون تغییر می‌ماند، مقادیر منفی کلمپ می‌شوند، سقف
     بالا اعمال می‌شود)؛ StudentsPage.load_students/search_students
     دیگر کل دیتاست را در self.all_students نمی‌ریزند و روی آن Python
     slice نمی‌زنند — به LIMIT/OFFSET واقعیِ SQL + کوئری COUNT جداگانه
     برای total_count تبدیل شدند (رفتار UI/خروجی Excel بدون تغییر)؛
     ObservationDAL/InterventionDAL/FollowUpDAL/ExtracurricularDAL هم
     طبق تصمیم صریح کاربر (scope=backend_infra_only) یک count_all()
     و پارامتر offset به‌عنوان زیرساختِ آماده گرفتند، بدون افزودن هیچ
     کنترل صفحه‌بندی تازه‌ای به UI صفحه‌های مشاهدات/مداخلات/پیگیری‌ها
     (که امروز چنین کنترلی ندارند و افزودنش قابلیت تازه بود، نه رفع
     باگ). (تست‌های کامل‌تر و مستقل در tests/test_pagination.py)
  K) مرحلهٔ ۷ — Dashboard/Performance با Aggregate (PERF-01/08/09):
     observation_dal.get_all()/intervention_dal.get_all()/followup_dal.get_all()
     در dashboard_service._get_general_stats/_get_observation_trend/
     _get_teacher_stats با کوئری‌های Aggregate جدید (get_dashboard_stats/
     get_monthly_trend/count_all) جایگزین شدند؛ اعداد خروجیِ Dashboard
     دقیقاً همان قبلی است. حین این جایگزینی یک باگِ جانبی هم کشف و رفع شد:
     JOIN فیلتر academic_year_id در هر سه DAL، پروندهٔ حذف‌شدهٔ
     (student_academic_profiles.is_deleted=1) را هم می‌شمرد؛ حالا مثل
     همه‌جای دیگرِ کد (profile_dal.get_by_ids) مستثنا می‌شود. (تست‌های
     کامل‌تر و مستقل در tests/test_dashboard_aggregates.py)
  L) مرحلهٔ ۸ — SEC-HARD-DELETE-01 / RESTORE-EDGE-01:
     permanent_delete در Student/Observation/Intervention/FollowUp/User
     DAL هیچ بررسیِ Permission نداشت (StaffDAL هم گاردِ وابستگی داشت ولی
     Permission نه)؛ حالا همگی همان Permission موجودِ delete()/restore()
     را می‌خواهند (بدون اختراع Permission تازه). StudentDAL/InterventionDAL
     که با ON DELETE CASCADE به فرزندانشان وصل‌اند، گاردِ وابستگیِ تازه هم
     گرفتند (اگر پروندهٔ سالانه/پیگیریِ وابسته وجود داشته باشد، حذف دائم
     رد می‌شود — دقیقاً مثل الگوی از قبل موجودِ staff_dal). علاوه بر این،
     restore() در Observation/Intervention/FollowUp/StudentAcademicProfile
     DAL و AttachmentService.restore_attachment اکنون بررسی می‌کنند که
     موجودیت والد (پروندهٔ سالانه/مداخله/دانش‌آموز/موجودیتِ اصلیِ پیوست)
     خودش وجود دارد و حذف نشده — وگرنه رکورد «فعالِ روی والدِ حذف‌شده»
     ساخته می‌شد. (تست‌های کامل‌تر و مستقل در
     tests/test_hard_delete_restore_edge.py)
  M) تکمیلِ یافتهٔ جانبیِ مرحلهٔ ۸: کلِ `StudentAcademicProfileDAL` هیچ
     Permission/Scope‌ای نداشت (از قلمِ مراحل قبلی جا مانده بود).
     `create`/`update` عمداً دست‌نخورده ماندند (چند مسیر فعال دارند —
     از جمله ایجاد خودکار پرونده هنگام ثبت مشاهده/مداخله — که گیت‌کردنشان
     با یک Permission غلط می‌تواند بی‌سروصدا TEACHER را از ثبت مشاهده
     محروم کند؛ نیازمند تحلیل جداگانه است، نه حدس). `delete`/`restore`
     چون **صفر مصرف‌کنندهٔ فعال** داشتند (نه در Service، نه در UI)،
     بدون ریسک با همان `DELETE_STUDENT`/Scope دانش‌آموز گیت شدند.

نکتهٔ محیط: بخش E به Qt واقعی نیاز دارد؛ با کتابخانه‌های جانشین
(qtstub) و QT_QPA_PLATFORM=offscreen اجرا می‌شود:

  LD_LIBRARY_PATH=/home/user/qtstub/lib QT_QPA_PLATFORM=offscreen \\
      python3 verify_fixes19.py
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


TMP = tempfile.mkdtemp(prefix="round19_verify_")
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


# ============================================================
# بخش A: DAL-level create/update
# ============================================================
print("=" * 76)
print("بخش A: مرز مجوز create/update در DAL (Student/Observation/Intervention/Followup)")
print("=" * 76)

viewer_staff = make_staff_and_user("viewer", "viewer_r19")
teacher_staff = make_staff_and_user("teacher", "teacher_r19")

from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.student_dal import StudentDAL
from models.followup import FollowUp
from models.intervention import Intervention
from models.observation import Observation
from models.student import Student

# --- ساخت پیش‌نیاز (دانش‌آموز/مداخله) در بافت سیستمی ---
AccessControl.logout()
base_student = Student()
base_student.first_name = "علی"
base_student.last_name = "پایه"
base_student.national_code = "1111111111"
base_student = StudentDAL().create(base_student)

import jdatetime

from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from models.student_academic_profile import StudentAcademicProfile

_today = jdatetime.date.today().strftime("%Y/%m/%d")

_year_row = conn.execute(
    "SELECT id FROM academic_years WHERE is_active = 1 AND is_deleted = 0 LIMIT 1"
).fetchone()
_profile = StudentAcademicProfile()
_profile.student_id = base_student.id
_profile.academic_year_id = _year_row["id"]
_profile.grade = 1
_profile.class_name = "اول-الف"
base_profile = StudentAcademicProfileDAL().create(_profile)
BASE_PROFILE_ID = base_profile.id

base_intervention = Intervention()
base_intervention.student_profile_id = BASE_PROFILE_ID
base_intervention.staff_id = 1
base_intervention.type = "گفتگوی فردی"
base_intervention.date = _today
base_intervention.description = "پایه برای آزمون followup"
base_intervention = InterventionDAL().create(base_intervention)

login(viewer_staff)

with contextlib.suppress(Exception):
    s = Student()
    s.first_name = "ویو"
    s.last_name = "ممنوع"
    s.national_code = "2222222222"
    try:
        StudentDAL().create(s)
        check("A", "VIEWER نمی‌تواند دانش‌آموز بسازد", False, "استثنا داده نشد")
    except PermissionDeniedError:
        check("A", "VIEWER نمی‌تواند دانش‌آموز بسازد", True)

try:
    base_student.first_name = "تغییر-ویو"
    StudentDAL().update(base_student)
    check("A", "VIEWER نمی‌تواند دانش‌آموز را ویرایش کند", False, "استثنا داده نشد")
except PermissionDeniedError:
    check("A", "VIEWER نمی‌تواند دانش‌آموز را ویرایش کند", True)

try:
    o = Observation()
    o.student_profile_id = BASE_PROFILE_ID
    o.staff_id = 1
    o.observation_date = _today
    o.description = "مشاهده ویو"
    ObservationDAL().create(o)
    check("A", "VIEWER نمی‌تواند مشاهده بسازد", False, "استثنا داده نشد")
except PermissionDeniedError:
    check("A", "VIEWER نمی‌تواند مشاهده بسازد", True)

try:
    i = Intervention()
    i.student_profile_id = BASE_PROFILE_ID
    i.staff_id = 1
    i.type = "گفتگوی فردی"
    i.date = _today
    i.description = "مداخله ویو"
    InterventionDAL().create(i)
    check("A", "VIEWER نمی‌تواند مداخله بسازد", False, "استثنا داده نشد")
except PermissionDeniedError:
    check("A", "VIEWER نمی‌تواند مداخله بسازد", True)

try:
    f = FollowUp()
    f.intervention_id = base_intervention.id
    f.staff_id = 1
    f.date = _today
    FollowUpDAL().create(f)
    check("A", "VIEWER نمی‌تواند پیگیری بسازد", False, "استثنا داده نشد")
except PermissionDeniedError:
    check("A", "VIEWER نمی‌تواند پیگیری بسازد", True)

AccessControl.logout()
login(teacher_staff)
try:
    s2 = Student()
    s2.first_name = "معلم"
    s2.last_name = "مجاز"
    s2.national_code = "3333333333"
    created = StudentDAL().create(s2)
    check("A", "TEACHER می‌تواند دانش‌آموز بسازد (CREATE_STUDENT دارد)",
          created is not None and created.id is not None)
except PermissionDeniedError as e:
    check("A", "TEACHER می‌تواند دانش‌آموز بسازد (CREATE_STUDENT دارد)", False, str(e))

try:
    base_intervention.description = "ویرایش توسط معلم"
    InterventionDAL().update(base_intervention)
    check("A", "TEACHER نمی‌تواند مداخله را ویرایش کند (فقط CREATE دارد نه EDIT)",
          False, "استثنا داده نشد")
except PermissionDeniedError:
    check("A", "TEACHER نمی‌تواند مداخله را ویرایش کند (فقط CREATE دارد نه EDIT)", True)

AccessControl.logout()

# ============================================================
# بخش B: Service-level — نوع استثنا حفظ می‌شود (base_service.py)
# ============================================================
print("=" * 76)
print("بخش B: execute_in_transaction دیگر PermissionDeniedError را نمی‌بلعد")
print("=" * 76)

from services.student_service import StudentService
from utils.error_handler import ServiceError

login(viewer_staff)
svc = StudentService()
try:
    svc.create_student({"first_name": "سرویس", "last_name": "ویو"})
    check("B", "StudentService.create_student با VIEWER → PermissionDeniedError دقیق", False,
          "استثنا داده نشد")
except PermissionDeniedError:
    check("B", "StudentService.create_student با VIEWER → PermissionDeniedError دقیق", True)
except ServiceError as e:
    check("B", "StudentService.create_student با VIEWER → PermissionDeniedError دقیق", False,
          f"به‌جای آن ServiceError عمومی گرفته شد: {e}")
except Exception as e:
    check("B", "StudentService.create_student با VIEWER → PermissionDeniedError دقیق", False,
          f"نوع استثنای غیرمنتظره: {type(e).__name__}: {e}")

AccessControl.logout()

# ============================================================
# بخش C: ایمپورت Excel — مرز مجوز پیش از بررسی محیط
# ============================================================
print("=" * 76)
print("بخش C: ایمپورت Excel — CREATE_STUDENT پیش از بررسی openpyxl/فایل")
print("=" * 76)

from utils.excel_importer import ExcelImporter

login(viewer_staff)
success, message, imported, errors = ExcelImporter().import_students_from_excel(
    "/nonexistent/path/does-not-matter.xlsx")
check("C", "ایمپورت با VIEWER رد می‌شود (success=False)", success is False)
check("C", "ایمپورت با VIEWER: 0 رکورد وارد شد", imported == 0)
check("C", "پیام رد شامل واژهٔ «اجازه» است (نه خطای فایل/openpyxl)", "اجازه" in message,
      detail=message)
AccessControl.logout()

# مسیر مثبت: بدون نشست (بافت سیستمی، DD-4) باید از سد مجوز رد شود و به
# بررسی بعدی (وجود فایل) برسد — یعنی پیام دیگر دربارهٔ «اجازه» نیست.
success2, message2, imported2, errors2 = ExcelImporter().import_students_from_excel(
    "/nonexistent/path/does-not-matter.xlsx")
check("C", "بدون نشست (بافت سیستمی): از سد مجوز عبور می‌کند و به خطای فایل می‌رسد",
      "اجازه" not in message2, detail=message2)

# ============================================================
# بخش D: Attachment — سیاست «همان مجوز موجودیت والد» (DD-6)
# ============================================================
print("=" * 76)
print("بخش D: Attachment — ENTITY_PERMISSION_MAP بر اساس موجودیت والد")
print("=" * 76)

ATT_DIR = os.path.join(TMP, "attachments")
os.makedirs(ATT_DIR, exist_ok=True)
import dal.attachment_dal as attachment_dal_mod
import services.attachment_service as attachment_service_mod

attachment_dal_mod.ATTACHMENTS_DIR = ATT_DIR
attachment_service_mod.ATTACHMENTS_DIR = ATT_DIR
from services.attachment_service import AttachmentService

sample_bytes = "نمونهٔ آزمون پیوست دور نوزدهم".encode()

att_service = AttachmentService()

login(viewer_staff)
try:
    att_service.upload_attachment(
        entity_type="student", entity_id=base_student.id,
        file_data=sample_bytes, file_name="sample.txt", created_by=viewer_staff)
    check("D", "VIEWER نمی‌تواند به دانش‌آموز پیوست آپلود کند", False, "استثنا داده نشد")
except PermissionDeniedError:
    check("D", "VIEWER نمی‌تواند به دانش‌آموز پیوست آپلود کند", True)
AccessControl.logout()

manager_row = conn.execute(
    "SELECT staff_id FROM users WHERE role = 'manager' AND is_deleted = 0 LIMIT 1"
).fetchone()
manager_staff_id = manager_row["staff_id"]
login(manager_staff_id)
uploaded = None
try:
    uploaded = att_service.upload_attachment(
        entity_type="student", entity_id=base_student.id,
        file_data=sample_bytes, file_name="sample.txt", created_by=manager_staff_id)
    check("D", "MANAGER می‌تواند به دانش‌آموز پیوست آپلود کند (EDIT_STUDENT دارد)",
          uploaded is not None)
except PermissionDeniedError as e:
    check("D", "MANAGER می‌تواند به دانش‌آموز پیوست آپلود کند (EDIT_STUDENT دارد)", False, str(e))
AccessControl.logout()

if uploaded is not None:
    login(viewer_staff)
    try:
        att_service.delete_attachment(uploaded.id, user_id=viewer_staff)
        check("D", "VIEWER نمی‌تواند پیوست دانش‌آموز را حذف کند", False, "استثنا داده نشد")
    except PermissionDeniedError:
        check("D", "VIEWER نمی‌تواند پیوست دانش‌آموز را حذف کند", True)
    AccessControl.logout()

    # نکته: در پیکربندی فعلی ROLE_PERMISSIONS همهٔ نقش‌ها VIEW_STUDENTS
    # دارند (سطح «دیدن» عمداً باز است)، پس هیچ نقش واقعی‌ای نمی‌تواند
    # این سناریو را با VIEWER بازتولید کند. رفتار موردنظر (رد مجوز باید
    # آشکار بماند، نه به‌شکل «فهرست خالی») را با شبیه‌سازی مستقیم رد
    # مجوز می‌سنجیم (رگرسیون روی الگوی except Exception: return []).
    from unittest.mock import patch
    with patch.object(
        AccessControl, "require_permission",
        side_effect=PermissionDeniedError("student_view_permission", action="test")
    ):
        try:
            att_service.search_attachments("student", base_student.id, "sample")
            check("D", "search_attachments رد مجوز را پنهان نمی‌کند (نه فهرست خالی)",
                  False, "استثنا داده نشد؛ رد مجوز پنهان شده")
        except PermissionDeniedError:
            check("D", "search_attachments رد مجوز را پنهان نمی‌کند (نه فهرست خالی)", True)

    login(manager_staff_id)
    try:
        atts = att_service.get_attachments_by_entity("student", base_student.id)
        check("D", "MANAGER می‌تواند پیوست‌های دانش‌آموز را ببیند (VIEW_STUDENTS دارد)",
              len(atts) >= 1)
    except PermissionDeniedError as e:
        check("D", "MANAGER می‌تواند پیوست‌های دانش‌آموز را ببیند (VIEW_STUDENTS دارد)",
              False, str(e))
    AccessControl.logout()
else:
    check("D", "VIEWER نمی‌تواند پیوست دانش‌آموز را حذف کند", False, "آپلود پیش‌نیاز شکست خورد")
    check("D", "search_attachments رد مجوز را پنهان نمی‌کند (نه فهرست خالی)",
          False, "آپلود پیش‌نیاز شکست خورد")
    check("D", "MANAGER می‌تواند پیوست‌های دانش‌آموز را ببیند (VIEW_STUDENTS دارد)",
          False, "آپلود پیش‌نیاز شکست خورد")

# ============================================================
# بخش E: UI — گیت‌بندی دکمه‌های افزودن/ایمپورت/ویرایش
# ============================================================
print("=" * 76)
print("بخش E: UI — دکمه‌های صفحه‌ها برای نقش بی‌مجوز غیرفعال‌اند")
print("=" * 76)

try:
    from PySide6.QtWidgets import QApplication
    _qapp = QApplication.instance() or QApplication(sys.argv)
    QT_OK = True
except Exception as e:  # pragma: no cover - محیط بدون Qt واقعی
    QT_OK = False
    print(f"  ⚠️  Qt در دسترس نیست ({e}) — بخش E رد می‌شود (NOT_TESTED)")

if QT_OK:
    with contextlib.redirect_stdout(io.StringIO()):
        from views.pages.followups_page import FollowUpsPage
        from views.pages.interventions_page import InterventionsPage
        from views.pages.observations_page import ObservationsPage
        from views.pages.students_page import StudentsPage

    def _build(cls):
        """ساخت صفحه با سرکوب چاپ‌های سازنده، بدون بلعیدن استثنا"""
        with contextlib.redirect_stdout(io.StringIO()):
            return cls()

    login(viewer_staff)
    try:
        sp = _build(StudentsPage)
        check("E", "VIEWER: دکمهٔ افزودن دانش‌آموز غیرفعال است", not sp.add_btn.isEnabled())
        check("E", "VIEWER: دکمهٔ ایمپورت Excel غیرفعال است", not sp.import_btn.isEnabled())
    except Exception as e:
        check("E", "VIEWER: دکمهٔ افزودن/ایمپورت دانش‌آموز غیرفعال است", False, str(e))

    try:
        op = _build(ObservationsPage)
        check("E", "VIEWER: دکمهٔ ثبت مشاهده غیرفعال است", not op.add_btn.isEnabled())
    except Exception as e:
        check("E", "VIEWER: دکمهٔ ثبت مشاهده غیرفعال است", False, str(e))

    try:
        ip = _build(InterventionsPage)
        check("E", "VIEWER: دکمهٔ ثبت مداخله غیرفعال است", not ip.add_btn.isEnabled())
    except Exception as e:
        check("E", "VIEWER: دکمهٔ ثبت مداخله غیرفعال است", False, str(e))

    try:
        fp = _build(FollowUpsPage)
        check("E", "VIEWER: دکمهٔ ثبت پیگیری غیرفعال است", not fp.add_btn.isEnabled())
    except Exception as e:
        check("E", "VIEWER: دکمهٔ ثبت پیگیری غیرفعال است", False, str(e))
    AccessControl.logout()

    login(teacher_staff)
    try:
        sp2 = _build(StudentsPage)
        check("E", "TEACHER: دکمهٔ افزودن دانش‌آموز فعال است (CREATE_STUDENT دارد)",
              sp2.add_btn.isEnabled())
    except Exception as e:
        check("E", "TEACHER: دکمهٔ افزودن دانش‌آموز فعال است (CREATE_STUDENT دارد)", False, str(e))
    AccessControl.logout()

# ============================================================
# بخش F: مرحلهٔ ۲ — زیرساخت مشترک Scope (DD-6)
# ============================================================
print("=" * 76)
print("بخش F: زیرساخت Scope — AccessControl.has_student_scope/require_student_scope")
print("=" * 76)

scope_teacher_staff = make_staff_and_user("teacher", "teacher_scope_r19")
AccessControl.logout()

s_assigned = Student()
s_assigned.first_name = "منتسب"
s_assigned.last_name = "آزمون"
s_assigned.national_code = "4444444444"
s_assigned = StudentDAL().create(s_assigned)

s_other = Student()
s_other.first_name = "غیرمنتسب"
s_other.last_name = "آزمون"
s_other.national_code = "5555555555"
s_other = StudentDAL().create(s_other)

conn.execute(
    "INSERT INTO teacher_assignments (student_id, staff_id, academic_year_id, is_active) "
    "VALUES (?, ?, 1, 1)",
    (s_assigned.id, scope_teacher_staff),
)
conn.commit()

login(scope_teacher_staff)
check("F", "TEACHER به دانش‌آموز منتسب Scope دارد",
      AccessControl.has_student_scope(s_assigned.id))
check("F", "TEACHER به دانش‌آموز غیرمنتسب Scope ندارد",
      not AccessControl.has_student_scope(s_other.id))
try:
    AccessControl.require_student_scope(s_other.id, action="verify_fixes19")
    check("F", "require_student_scope برای دانش‌آموز غیرمنتسب رد می‌شود", False,
          "استثنا داده نشد")
except PermissionDeniedError:
    check("F", "require_student_scope برای دانش‌آموز غیرمنتسب رد می‌شود", True)
AccessControl.logout()

login(manager_staff_id)
check("F", "MANAGER بدون محدودیت Scope است (DD-6)",
      AccessControl.has_student_scope(s_other.id))
AccessControl.logout()

check("F", "بافت بدون نشست (سیستمی): بدون محدودیت Scope است",
      AccessControl.has_student_scope(s_other.id))

print("=" * 76)
print("بخش G: IDOR/Scope در سطح Object روی Intervention/FollowUp (مرحلهٔ ۳)")
print("=" * 76)


def _new_student(last_name, national_code):
    s = Student()
    s.first_name = "آزمون"
    s.last_name = last_name
    s.national_code = national_code
    return s


def _new_profile(student_id, academic_year_id):
    p = StudentAcademicProfile()
    p.student_id = student_id
    p.academic_year_id = academic_year_id
    p.grade = 1
    p.class_name = "اول-الف"
    return p


def _new_intervention(profile_id):
    i = Intervention()
    i.student_profile_id = profile_id
    i.staff_id = 1
    i.type = "گفتگوی فردی"
    i.date = _today
    i.description = "مداخلهٔ آزمون بخش G"
    return i


def _new_followup(intervention_id):
    f = FollowUp()
    f.intervention_id = intervention_id
    f.staff_id = 1
    f.date = _today
    f.description = "پیگیری آزمون بخش G"
    return f


g_teacher_staff = make_staff_and_user("teacher", "teacher_iof_r19")
AccessControl.logout()

g_student_a = StudentDAL().create(_new_student("جی-منتسب", "6666666601"))
g_student_b = StudentDAL().create(_new_student("جی-غیرمنتسب", "6666666602"))

conn.execute(
    "INSERT INTO teacher_assignments (student_id, staff_id, academic_year_id, is_active) "
    "VALUES (?, ?, 1, 1)",
    (g_student_a.id, g_teacher_staff),
)
conn.commit()

g_profile_a = StudentAcademicProfileDAL().create(_new_profile(g_student_a.id, _year_row["id"]))
g_profile_b = StudentAcademicProfileDAL().create(_new_profile(g_student_b.id, _year_row["id"]))

g_intervention_a = InterventionDAL().create(_new_intervention(g_profile_a.id))
g_intervention_b = InterventionDAL().create(_new_intervention(g_profile_b.id))

g_followup_a = FollowUpDAL().create(_new_followup(g_intervention_a.id))
g_followup_b = FollowUpDAL().create(_new_followup(g_intervention_b.id))

login(g_teacher_staff)

try:
    InterventionDAL().get_by_id(g_intervention_a.id)
    check("G", "TEACHER مداخلهٔ دانش‌آموز منتسب خودش را با ID می‌خواند", True)
except PermissionDeniedError as e:
    check("G", "TEACHER مداخلهٔ دانش‌آموز منتسب خودش را با ID می‌خواند", False, str(e))

try:
    InterventionDAL().get_by_id(g_intervention_b.id)
    check("G", "IDOR: TEACHER نمی‌تواند مداخلهٔ معلم دیگر را با ID مستقیم بخواند", False,
          "استثنا داده نشد")
except PermissionDeniedError:
    check("G", "IDOR: TEACHER نمی‌تواند مداخلهٔ معلم دیگر را با ID مستقیم بخواند", True)

try:
    FollowUpDAL().get_by_id(g_followup_a.id)
    check("G", "TEACHER پیگیری دانش‌آموز منتسب خودش را با ID می‌خواند", True)
except PermissionDeniedError as e:
    check("G", "TEACHER پیگیری دانش‌آموز منتسب خودش را با ID می‌خواند", False, str(e))

try:
    FollowUpDAL().get_by_id(g_followup_b.id)
    check("G", "IDOR: TEACHER نمی‌تواند پیگیری معلم دیگر را با ID مستقیم بخواند", False,
          "استثنا داده نشد")
except PermissionDeniedError:
    check("G", "IDOR: TEACHER نمی‌تواند پیگیری معلم دیگر را با ID مستقیم بخواند", True)

try:
    InterventionDAL().create(_new_intervention(g_profile_b.id))
    check("G", "TEACHER نمی‌تواند برای دانش‌آموز خارج از Scope مداخله بسازد", False,
          "استثنا داده نشد")
except PermissionDeniedError:
    check("G", "TEACHER نمی‌تواند برای دانش‌آموز خارج از Scope مداخله بسازد", True)

try:
    FollowUpDAL().create(_new_followup(g_intervention_b.id))
    check("G", "Cross-resource: TEACHER نمی‌تواند به مداخلهٔ خارج از Scope پیگیری وصل کند",
          False, "استثنا داده نشد")
except PermissionDeniedError:
    check("G", "Cross-resource: TEACHER نمی‌تواند به مداخلهٔ خارج از Scope پیگیری وصل کند",
          True)

AccessControl.logout()
login(manager_staff_id)
try:
    result = InterventionDAL().get_by_id(g_intervention_b.id)
    check("G", "MANAGER بدون محدودیت Scope مداخلهٔ هر دانش‌آموزی را می‌خواند (DD-6)",
          result is not None)
except PermissionDeniedError as e:
    check("G", "MANAGER بدون محدودیت Scope مداخلهٔ هر دانش‌آموزی را می‌خواند (DD-6)",
          False, str(e))
AccessControl.logout()

print("=" * 76)
print("بخش H: مرحلهٔ ۴ — IDOR/Scope روی Observation و موجودیت‌های فقط-Scope (DD-1)")
print("=" * 76)

from dal.counseling_session_dal import CounselingSessionDAL
from dal.extracurricular_dal import ExtracurricularDAL
from dal.goal_dal import GoalDAL
from models.counseling_session import CounselingSession
from models.extracurricular_activity import ExtracurricularActivity
from models.individual_goal import IndividualGoal

h_teacher_staff = make_staff_and_user("teacher", "teacher_stage4_r19")
AccessControl.logout()

h_student_a = StudentDAL().create(_new_student("اچ-منتسب", "7777777701"))
h_student_b = StudentDAL().create(_new_student("اچ-غیرمنتسب", "7777777702"))

conn.execute(
    "INSERT INTO teacher_assignments (student_id, staff_id, academic_year_id, is_active) "
    "VALUES (?, ?, 1, 1)",
    (h_student_a.id, h_teacher_staff),
)
conn.commit()

h_profile_a = StudentAcademicProfileDAL().create(_new_profile(h_student_a.id, _year_row["id"]))
h_profile_b = StudentAcademicProfileDAL().create(_new_profile(h_student_b.id, _year_row["id"]))


def _new_observation(profile_id):
    o = Observation()
    o.student_profile_id = profile_id
    o.staff_id = 1
    o.observation_date = _today
    o.description = "مشاهدهٔ آزمون بخش H"
    return o


h_observation_a = ObservationDAL().create(_new_observation(h_profile_a.id))
h_observation_b = ObservationDAL().create(_new_observation(h_profile_b.id))

_h_session = CounselingSession()
_h_session.student_profile_id = h_profile_b.id
_h_session.counselor_id = 1
_h_session.session_date = _today
_h_session.type = CounselingSession.TYPE_INDIVIDUAL
h_session_b = CounselingSessionDAL().create(_h_session)

_h_activity = ExtracurricularActivity()
_h_activity.student_profile_id = h_profile_b.id
_h_activity.title = "فعالیت H"
_h_activity.type = ExtracurricularActivity.TYPE_SPORT
_h_activity.start_date = _today
h_activity_b = ExtracurricularDAL().create(_h_activity)

_h_goal = IndividualGoal()
_h_goal.student_profile_id = h_profile_b.id
_h_goal.title = "هدف H"
h_goal_b = GoalDAL().create(_h_goal)

login(h_teacher_staff)

try:
    ObservationDAL().get_by_id(h_observation_b.id)
    check("H", "IDOR: TEACHER نمی‌تواند مشاهدهٔ معلم دیگر را با ID مستقیم بخواند", False,
          "استثنا داده نشد")
except PermissionDeniedError:
    check("H", "IDOR: TEACHER نمی‌تواند مشاهدهٔ معلم دیگر را با ID مستقیم بخواند", True)

try:
    ObservationDAL().get_by_id(h_observation_a.id)
    check("H", "TEACHER مشاهدهٔ دانش‌آموز منتسب خودش را می‌خواند", True)
except PermissionDeniedError as e:
    check("H", "TEACHER مشاهدهٔ دانش‌آموز منتسب خودش را می‌خواند", False, str(e))

for label, dal_call in [
    ("CounselingSessionDAL", lambda: CounselingSessionDAL().get_by_id(h_session_b.id)),
    ("ExtracurricularDAL", lambda: ExtracurricularDAL().get_by_id(h_activity_b.id)),
    ("GoalDAL", lambda: GoalDAL().get_by_id(h_goal_b.id)),
]:
    try:
        dal_call()
        check("H", f"{label}: طبق DD-1 هیچ Permission ندارد اما Scope رد می‌کند"
                    " (dd1_scope=add_scope_only)", False, "استثنا داده نشد")
    except PermissionDeniedError:
        check("H", f"{label}: طبق DD-1 هیچ Permission ندارد اما Scope رد می‌کند"
                    " (dd1_scope=add_scope_only)", True)

AccessControl.logout()

svc = AttachmentService()
login(h_teacher_staff)
try:
    svc.get_attachments_by_entity('observation', h_observation_b.id)
    check("H", "Attachment: Scope مستقل از Permission موجودیت والد (observation)", False,
          "استثنا داده نشد")
except PermissionDeniedError:
    check("H", "Attachment: Scope مستقل از Permission موجودیت والد (observation)", True)
AccessControl.logout()

# ============================================================
print("=" * 76)
print("بخش I: مرحلهٔ ۵ — رفع نشت Exception خام (ERR-01/ERR-LEAK-01)")
print("=" * 76)

from utils.error_handler import AppError, DatabaseError, DataIntegrityError

# --- I1: کلاس‌های AppError — نامرئی‌بودن به‌طور طراحی
_db_err = DatabaseError("جزئیات فنی sqlite")
_di_err = DataIntegrityError("جزئیات فنی نیمه‌کاره")
_se_default = ServiceError("پیام امن پیش‌فرض")
check("I1", "DatabaseError/DataIntegrityError همیشه user_visible=False دارند؛ "
            "ServiceError پیش‌فرضش (بدون تغییر) همچنان True است",
      _db_err.user_visible is False and _di_err.user_visible is False
      and _se_default.user_visible is True,
      f"db={_db_err.user_visible} di={_di_err.user_visible} se={_se_default.user_visible}")

# --- I2: ErrorHandler مسیر user_visible=False را عمومی می‌کند
from utils.error_handler import ErrorHandler

_handler = ErrorHandler()
_invisible = ServiceError("این متن فنی نباید دیده شود", user_visible=False)
_resp = _handler.handle(_invisible, log_level='info')
check("I2", "ErrorHandler: پیام user_visible=False با پیام عمومی جایگزین می‌شود",
      _resp['error']['message'] == ErrorHandler.GENERIC_MESSAGE
      and "این متن فنی نباید دیده شود" not in _resp['error']['message'],
      _resp['error']['message'])

# --- I3: شبیه‌سازی خطای DB خام در ObservationService.get_observation
from services.observation_service import ObservationService

_RAW = "RAW_MARKER_/var/lib/partow/db_internal_path_12345"
_obs_svc = ObservationService()
_orig_get = _obs_svc.observation_dal.get_by_id


def _obs_boom(*_a, **_k):
    raise RuntimeError(_RAW)


_obs_svc.observation_dal.get_by_id = _obs_boom
try:
    _obs_svc.get_observation(1)
    check("I3", "شبیه‌سازی خطای DB خام در ObservationService.get_observation: پیام کاربر متن خام ندارد",
          False, "استثنا داده نشد")
except Exception as e:
    check("I3", "شبیه‌سازی خطای DB خام در ObservationService.get_observation: پیام کاربر متن خام ندارد",
          _RAW not in str(e) and isinstance(e, AppError) and e.user_visible is False,
          f"type={type(e).__name__} msg={e}")
finally:
    _obs_svc.observation_dal.get_by_id = _orig_get

# --- I4: شبیه‌سازی خطای خام در base_service.execute_in_transaction
_stu_svc = StudentService()


def _tx_boom():
    raise RuntimeError(_RAW)


try:
    _stu_svc.execute_in_transaction(_tx_boom)
    check("I4", "execute_in_transaction: خطای Exception خام با پیام عمومی امن جایگزین می‌شود",
          False, "استثنا داده نشد")
except Exception as e:
    check("I4", "execute_in_transaction: خطای Exception خام با پیام عمومی امن جایگزین می‌شود",
          _RAW not in str(e) and isinstance(e, AppError) and e.user_visible is False,
          f"type={type(e).__name__} msg={e}")

# --- I5: پیام‌های عمدی/امن (ValidationError/«یافت نشد») نباید نابود شوند
# (این‌جا فقط «یافت نشد» را روی سرویس مداخله بررسی می‌کنیم؛ سناریوی کاملِ
#  سقفِ پیوست در tests/test_error_leak.py و tests/test_attachment_restore.py
#  با جزئیات بیشتر پوشش داده شده است.)
from services.intervention_service import InterventionService

_inter_svc = InterventionService()
try:
    _inter_svc.get_intervention(999999)
    check("I5", "پیام «یافت نشد» از except عمومی دست‌نخورده عبور می‌کند (نابود نمی‌شود)",
          False, "استثنا داده نشد")
except Exception as e:
    check("I5", "پیام «یافت نشد» از except عمومی دست‌نخورده عبور می‌کند (نابود نمی‌شود)",
          "یافت نشد" in str(e), str(e))

# --- I6: بازآزمونِ verify_fixes6 §F3 — شکستِ ذخیرهٔ پیشنهاد هنوز گویاست
# ولی دیگر متن خامِ RuntimeError شبیه‌سازی‌شده را نشان نمی‌دهد
from services.recommendation_service import RecommendationService

_i_student = StudentDAL().create(_new_student("رفع‌نشت", "5551112223"))
_i_profile = StudentAcademicProfileDAL().create(_new_profile(_i_student.id, _year_row["id"]))
_rec_svc = RecommendationService()


def _rec_boom(_rec):
    raise RuntimeError("RAW_RECOMMENDATION_DB_FAILURE")


_orig_rec_create = _rec_svc.recommendation_dal.create
_rec_svc.recommendation_dal.create = _rec_boom
try:
    with contextlib.redirect_stdout(io.StringIO()):
        _rec_svc.generate_recommendations(_i_profile.id)
    check("I6", "شکستِ ذخیرهٔ پیشنهاد گویا می‌ماند ولی دیگر متن خام ندارد", False,
          "استثنا داده نشد")
except Exception as e:
    check("I6", "شکستِ ذخیرهٔ پیشنهاد گویا می‌ماند ولی دیگر متن خام ندارد",
          "ذخیره" in str(e) and "RAW_RECOMMENDATION_DB_FAILURE" not in str(e),
          str(e))
finally:
    _rec_svc.recommendation_dal.create = _orig_rec_create

AccessControl.logout()

# ============================================================
print("=" * 76)
print("بخش J: مرحلهٔ ۶ — اصلاح Query/Pagination (بخش‌های ۲، ۳، ۲۵، ۳۵)")
print("=" * 76)

from dal.extracurricular_dal import ExtracurricularDAL as _J_ExtracurricularDAL
from dal.followup_dal import FollowUpDAL as _J_FollowUpDAL
from dal.intervention_dal import InterventionDAL as _J_InterventionDAL
from dal.observation_dal import ObservationDAL as _J_ObservationDAL
from dal.student_dal import StudentDAL as _J_StudentDAL
from utils.pagination import normalize_limit_offset as _j_norm

# --- J1: utils/pagination.py — قراردادِ حیاتی limit=None یعنی «بدون سقف»
_j_limit, _j_offset = _j_norm(None, None)
_j_limit2, _j_offset2 = _j_norm(None, 50)
_j_limit3, _j_offset3 = _j_norm(-5, -10)
_j_limit4, _ = _j_norm(999999, 0)
check("J", "J1: normalize_limit_offset — limit=None دست‌نخورده می‌ماند (حتی با offset)؛ "
      "مقادیر منفی به صفر/۱ کلمپ می‌شوند؛ سقف بالا اعمال می‌شود",
      _j_limit is None and _j_offset is None
      and _j_limit2 is None and _j_offset2 is None
      and _j_limit3 == 1 and _j_offset3 == 0
      and _j_limit4 <= 200,
      f"{(_j_limit, _j_offset, _j_limit2, _j_offset2, _j_limit3, _j_offset3, _j_limit4)}")

# --- J2: StudentDAL.get_all/search اکنون LIMIT/OFFSET واقعی SQL دارند
#     و count_all/count_search دقیقاً همان WHERE را می‌شمارند
with contextlib.redirect_stdout(io.StringIO()):
    _j_dal = _J_StudentDAL()
    for _i in range(23):
        StudentDAL().create(_new_student(f"صفحه‌بندی{_i:02d}", f"6{_i:09d}"))

# (توجه: تا این نقطهٔ فایل، دانش‌آموزان بخش‌های قبلی هم در دیتابیس‌اند؛
#  بنابراین «total» فقط باید با طول get_all() بدون سقف برابر باشد — نه
#  عددی ثابت — و صفحات LIMIT/OFFSET باید همه‌شان را بدون هم‌پوشانی/جا
#  انداختن بپوشانند.)
_j_total = _j_dal.count_all()
_j_unbounded = _j_dal.get_all()
_j_all_paged_ids = []
_j_offset_cursor = 0
while _j_offset_cursor < _j_total:
    _j_chunk = _j_dal.get_all(limit=10, offset=_j_offset_cursor)
    _j_all_paged_ids.extend(s.id for s in _j_chunk)
    _j_offset_cursor += 10
_j_page1 = _j_dal.get_all(limit=10, offset=0)
_j_page2 = _j_dal.get_all(limit=10, offset=10)
check("J", "J2: StudentDAL — count_all دقیقاً با len(get_all()) برابر است؛ صفحاتِ "
      "LIMIT/OFFاست (ده‌تایی) بدون هم‌پوشانی/جا انداختن دقیقاً همان مجموعه را می‌پوشانند",
      _j_total == len(_j_unbounded)
      and len(_j_page1) == 10 and len(_j_page2) == 10
      and sorted(_j_all_paged_ids) == sorted(s.id for s in _j_unbounded)
      and len({s.id for s in _j_page1} & {s.id for s in _j_page2}) == 0,
      f"total={_j_total} p1={len(_j_page1)} p2={len(_j_page2)} paged={len(_j_all_paged_ids)}")

# --- J3: StudentDAL.search اکنون limit/offset می‌گیرد؛ count_search با آن هم‌خوان است
_j_search_all = _j_dal.search("صفحه‌بندی")
_j_search_p1 = _j_dal.search("صفحه‌بندی", limit=10, offset=0)
_j_count_search = _j_dal.count_search("صفحه‌بندی")
check("J", "J3: StudentDAL.search اکنون limit/offset می‌پذیرد (سازگار با گذشته چون پیش‌فرض "
      "None است) و count_search دقیقاً با طول جست‌وجوی بدون سقف برابر است",
      len(_j_search_all) == 23 and len(_j_search_p1) == 10
      and _j_count_search == 23,
      f"all={len(_j_search_all)} p1={len(_j_search_p1)} count={_j_count_search}")

# --- J4: جست‌وجوی only_deleted=True در حالت «نمایش حذف‌شده‌ها» دیگر با
#     حلقهٔ پایتونی روی کل فهرست انجام نمی‌شود؛ در خود SQL و ایزوله از فعال‌هاست
_j_victim = _j_search_all[0]
with contextlib.redirect_stdout(io.StringIO()):
    StudentDAL().delete(_j_victim.id, 1)
_j_only_deleted = _j_dal.search("صفحه‌بندی", only_deleted=True)
_j_active_after = _j_dal.search("صفحه‌بندی")
check("J", "J4: جست‌وجوی only_deleted=True فقط رکورد حذف‌شده را می‌دهد و از نتایج فعال "
      "جدا می‌ماند؛ count_search هم با only_deleted سازگار است",
      [s.id for s in _j_only_deleted] == [_j_victim.id]
      and _j_victim.id not in [s.id for s in _j_active_after]
      and _j_dal.count_search("صفحه‌بندی", only_deleted=True) == 1,
      f"only_deleted={[s.id for s in _j_only_deleted]} victim={_j_victim.id}")

# --- J5: StudentsPage — قرارداد قدیمیِ total_pages (بدون max(1,...) در فیلد
#     خام) و صفحه‌بندی واقعی SQL (نه دیگر Python slice روی کل فهرست) حفظ شده
from views.pages.students_page import StudentsPage as _J_StudentsPage

with contextlib.redirect_stdout(io.StringIO()):
    _j_page_obj = _J_StudentsPage()
    _j_page_obj.page_size_combo.setCurrentText("10")
    _j_page_obj.current_page = 0
    _j_page_obj.load_students()
_j_first_page_rows = len(_j_page_obj.students)
_j_total_count = _j_page_obj.total_count
check("J", "J5: StudentsPage.load_students از total_count (کوئری COUNT) برای صفحه‌بندی "
      "استفاده می‌کند و self.students فقط ردیف‌های همان صفحه (نه کل دیتاست) را دارد",
      _j_total_count == _j_dal.count_all()
      and _j_first_page_rows == min(10, _j_total_count),
      f"total_count={_j_total_count} rows={_j_first_page_rows}")

# --- J6: export_to_excel هنوز کل دیتاستِ فیلترشده را (نه فقط صفحهٔ جاری) صادر
#     می‌کند — واکشیِ کامل حالا فقط در لحظهٔ کلیک خروجی انجام می‌شود
import openpyxl
from PySide6.QtWidgets import QFileDialog, QMessageBox

_j_export_path = os.path.join(TMP, "j6_export_all.xlsx")
real_save_dialog_j = QFileDialog.getSaveFileName
# نکته: export_to_excel در پایان یک QMessageBox.information واقعی نمایش می‌دهد
# که exec() آن در محیط offscreen (بدون کاربر برای بستنش) برای همیشه بلاک
# می‌شود — باید موقتاً بی‌اثر شود (همانند information/warning/critical).
real_msgbox_info_j = QMessageBox.information
real_msgbox_warn_j = QMessageBox.warning
real_msgbox_crit_j = QMessageBox.critical
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (_j_export_path, "xlsx"))
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
QMessageBox.critical = staticmethod(lambda *a, **k: None)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        _j_page_obj.export_to_excel()
finally:
    QFileDialog.getSaveFileName = real_save_dialog_j
    QMessageBox.information = real_msgbox_info_j
    QMessageBox.warning = real_msgbox_warn_j
    QMessageBox.critical = real_msgbox_crit_j
_j_exported_sheet = openpyxl.load_workbook(_j_export_path).active
_j_exported_rows = [row for row in _j_exported_sheet.iter_rows(values_only=True)
                    if row and isinstance(row[0], int)]
check("J", "J6: خروجی Excel پس از تغییر داخلی load_students (که دیگر all_students را "
      "در هر بارگذاری پر نمی‌کند) هنوز کل دیتاست فیلترشده را می‌نویسد، نه فقط صفحهٔ ۱۰تایی",
      _j_first_page_rows == 10 and len(_j_exported_rows) == _j_total_count,
      f"page_rows={_j_first_page_rows} exported={len(_j_exported_rows)} total={_j_total_count}")

# --- J7: ObservationDAL/InterventionDAL/FollowUpDAL/ExtracurricularDAL —
#     offset سازگار با گذشته (پیش‌فرض None) + count_all جدید؛ هیچ UI
#     صفحه‌بندی تازه‌ای اضافه نشده (طبق تصمیم backend_infra_only)
with contextlib.redirect_stdout(io.StringIO()):
    _j_student2 = StudentDAL().create(_new_student("زیرساخت‌کوئری", "6999990001"))
    _j_profile2 = StudentAcademicProfileDAL().create(_new_profile(_j_student2.id, _year_row["id"]))
    _j_obs_dal = _J_ObservationDAL()
    for _i in range(6):
        _obs = Observation()
        _obs.student_profile_id = _j_profile2.id
        _obs.staff_id = 1
        _obs.observation_date = _today
        _obs.description = f"مشاهدهٔ زیرساخت {_i}"
        _obs.behavior_type = "خنثی"
        _j_obs_dal.create(_obs)
    _j_int_dal = _J_InterventionDAL()
    _j_intervention2 = _j_int_dal.create(_new_intervention(_j_profile2.id))
    for _i in range(4):
        _j_int_dal.create(_new_intervention(_j_profile2.id))
    _j_follow_dal = _J_FollowUpDAL()
    for _i in range(3):
        _j_follow_dal.create(_new_followup(_j_intervention2.id))
    _j_extra_dal = _J_ExtracurricularDAL()
    _j_activity = ExtracurricularActivity()
    _j_activity.student_profile_id = _j_profile2.id
    _j_activity.teacher_id = 1
    _j_activity.type = ExtracurricularActivity.TYPE_SPORT
    _j_activity.title = "فعالیت زیرساخت"
    _j_activity.start_date = _today
    _j_extra_dal.create(_j_activity)

_j_obs_count = _j_obs_dal.count_all()
_j_obs_page = _j_obs_dal.get_all(limit=3, offset=3)
_j_int_count = _j_int_dal.count_all()
_j_int_page = _j_int_dal.get_all(limit=2, offset=2)
_j_follow_count = _j_follow_dal.count_all()
_j_extra_count = _j_extra_dal.count_all()
_j_extra_unbounded = _j_extra_dal.get_all()
# (توجه: بخش H پیش‌تر یک ExtracurricularActivity دیگر ساخته، پس extra_count
#  می‌تواند از ۱ بیشتر باشد — فقط باید با get_all() بدون سقف برابر و حداقل ۱ باشد.)
check("J", "J7: چهار DAL دیگر (Observation/Intervention/FollowUp/Extracurricular) اکنون "
      "count_all + offset دارند؛ limit=None هنوز بدون سقف است (سازگار با گذشته)",
      _j_obs_count >= 6 and len(_j_obs_page) == 3
      and _j_int_count >= 5 and len(_j_int_page) == 2
      and _j_follow_count >= 3
      and _j_extra_count >= 1 and _j_extra_count == len(_j_extra_unbounded),
      f"obs={_j_obs_count} int={_j_int_count} follow={_j_follow_count} extra={_j_extra_count}")

# --- J8: صفحه‌های مشاهدات/مداخلات/پیگیری‌ها هیچ کنترل صفحه‌بندی تازه‌ای
#     نگرفته‌اند (طبق تصمیم صریح کاربر backend_infra_only در مرحلهٔ ۶)
import inspect as _j_inspect

from views.pages.followups_page import FollowUpsPage as _J_FollowUpsPage
from views.pages.interventions_page import InterventionsPage as _J_InterventionsPage
from views.pages.observations_page import ObservationsPage as _J_ObservationsPage

_j_pagination_markers = ("page_size_combo", "current_page", "next_page_btn", "prev_page_btn")
_j_no_new_ui = []
for _cls in (_J_ObservationsPage, _J_InterventionsPage, _J_FollowUpsPage):
    _src = _j_inspect.getsource(_cls)
    _j_no_new_ui.append(not any(marker in _src for marker in _j_pagination_markers))
check("J", "J8: صفحه‌های مشاهدات/مداخلات/پیگیری‌ها هنوز هیچ ابزار صفحه‌بندی‌ای در UI "
      "ندارند — طبق scope=backend_infra_only، افزودن آن یک قابلیت تازه بود، نه رفع باگ",
      all(_j_no_new_ui), f"{_j_no_new_ui}")

with contextlib.suppress(Exception):
    _j_page_obj.close()
AccessControl.logout()

print("=" * 76)
print("بخش K: مرحلهٔ ۷ — Dashboard/Performance با Aggregate (PERF-01/08/09)")
print("=" * 76)

# --- فیکسچر مشترک بخش K
from dal.academic_year_dal import AcademicYearDAL
from services.dashboard_service import DashboardService

with contextlib.redirect_stdout(io.StringIO()):
    from models.academic_year import AcademicYear
    _k_year_b_obj = AcademicYear()
    _k_year_b_obj.title = "سال K-19"
    _k_year_b_obj.start_date = "1404/07/01"
    _k_year_b_obj.end_date = "1405/03/31"
    _k_year_b_obj.is_active = 0
    _k_year_b_id = AcademicYearDAL().create(_k_year_b_obj).id

    _k_teacher_x = make_staff_and_user("teacher", "dash_k_teacher_x_r19")
    _k_teacher_y = make_staff_and_user("teacher", "dash_k_teacher_y_r19")

    _k_student_x = StudentDAL().create(_new_student("کی-ایکس", "9100000001"))
    _k_student_y = StudentDAL().create(_new_student("کی-ایگرگ", "9100000002"))
    _k_profile_x = StudentAcademicProfileDAL().create(_new_profile(_k_student_x.id, _year_row["id"]))
    _k_profile_y = StudentAcademicProfileDAL().create(_new_profile(_k_student_y.id, _k_year_b_id))

    _k_obs_dal = ObservationDAL()
    _k_int_dal = InterventionDAL()
    _k_follow_dal = FollowUpDAL()

    def _k_obs(profile_id, staff_id, behavior_type, date="1404/01/01"):
        o = Observation()
        o.student_profile_id = profile_id
        o.staff_id = staff_id
        o.observation_date = date
        o.description = "مشاهدهٔ بخش K"
        o.behavior_type = behavior_type
        return _k_obs_dal.create(o)

    def _k_intervention(profile_id, staff_id):
        i = Intervention()
        i.student_profile_id = profile_id
        i.staff_id = staff_id
        i.type = "گفتگوی فردی"
        i.date = _today
        i.description = "مداخلهٔ بخش K"
        return _k_int_dal.create(i)

    def _k_followup(intervention_id, staff_id, status="pending"):
        f = FollowUp()
        f.intervention_id = intervention_id
        f.staff_id = staff_id
        f.date = _today
        f.status = status
        f.description = "پیگیری بخش K"
        return _k_follow_dal.create(f)

    # معلم X روی سال A: ۲ مثبت، ۱ منفی، ۱ خنثی
    _k_obs(_k_profile_x.id, _k_teacher_x, "مثبت")
    _k_obs(_k_profile_x.id, _k_teacher_x, "مثبت")
    _k_obs(_k_profile_x.id, _k_teacher_x, "منفی")
    _k_obs(_k_profile_x.id, _k_teacher_x, "خنثی")
    # معلم Y روی سال B: ۱ مثبت
    _k_obs(_k_profile_y.id, _k_teacher_y, "مثبت")

    _k_inter_x = _k_intervention(_k_profile_x.id, _k_teacher_x)
    _k_intervention(_k_profile_y.id, _k_teacher_y)

    _k_followup(_k_inter_x.id, _k_teacher_x, status="pending")
    _k_followup(_k_inter_x.id, _k_teacher_x, status="pending")

# --- K1: ObservationDAL.get_dashboard_stats — Aggregate یک‌کوئری‌ای
_k_stats_all = _k_obs_dal.get_dashboard_stats()
_k_stats_x = _k_obs_dal.get_dashboard_stats(staff_id=_k_teacher_x)
_k_stats_year_a = _k_obs_dal.get_dashboard_stats(academic_year_id=_year_row["id"])
check("K", "K1: ObservationDAL.get_dashboard_stats — شمارش/تفکیک نوع رفتار با یک "
      "کوئری Aggregate (نه get_all()+حلقهٔ پایتونی)",
      _k_stats_x['total'] == 4 and _k_stats_x['positive'] == 2
      and _k_stats_x['negative'] == 1 and _k_stats_x['neutral'] == 1
      and _k_stats_year_a['total'] >= 4 and _k_stats_all['total'] >= 5,
      f"all={_k_stats_all} x={_k_stats_x} year_a={_k_stats_year_a}")

# --- K2: ObservationDAL.get_monthly_trend — GROUP BY ماه
_k_trend = _k_obs_dal.get_monthly_trend(staff_id=_k_teacher_x)
check("K", "K2: ObservationDAL.get_monthly_trend — گروه‌بندی ماهانه با GROUP BY "
      "(جایگزین حلقهٔ پایتونیِ قدیمیِ dashboard_service)",
      "1404/01" in _k_trend and _k_trend["1404/01"]['count'] == 4
      and _k_trend["1404/01"]['positive'] == 2,
      f"{_k_trend}")

# --- K3: FollowUpDAL.get_dashboard_stats — کل/در-انتظار با یک کوئری
_k_follow_stats = _k_follow_dal.get_dashboard_stats(staff_id=_k_teacher_x)
check("K", "K3: FollowUpDAL.get_dashboard_stats — شمارش کل/pending با یک کوئری Aggregate",
      _k_follow_stats['total'] == 2 and _k_follow_stats['pending'] == 2,
      f"{_k_follow_stats}")

# --- K4: رگرسیونِ باگِ کشف‌شده — پروندهٔ حذف‌شده در فیلتر academic_year_id
#     نباید در Observation/Intervention/FollowUp شمرده شود (قبل از این
#     مرحله JOIN با student_academic_profiles شرط is_deleted نداشت)
with contextlib.redirect_stdout(io.StringIO()):
    # توجه: تا این نقطه از اسکریپت، بخش‌های A تا J هم روی همین سال (_year_row)
    # داده ساخته‌اند؛ پس «بعد از حذف» صفر نمی‌شود — فقط باید دقیقاً به‌اندازهٔ
    # ۴ مشاهده/۱ مداخله/۲ پیگیریِ متعلق به profile_x کم شود.
    _k_before_obs = _k_obs_dal.get_dashboard_stats(academic_year_id=_year_row["id"])['total']
    _k_before_int = _k_int_dal.count_all(academic_year_id=_year_row["id"])
    _k_before_follow = _k_follow_dal.get_dashboard_stats(academic_year_id=_year_row["id"])['total']
    StudentAcademicProfileDAL().delete(_k_profile_x.id, 1)
    _k_after_obs = _k_obs_dal.get_dashboard_stats(academic_year_id=_year_row["id"])['total']
    _k_after_int = _k_int_dal.count_all(academic_year_id=_year_row["id"])
    _k_after_follow = _k_follow_dal.get_dashboard_stats(academic_year_id=_year_row["id"])['total']
check("K", "K4: رگرسیون باگ — پروندهٔ حذف‌شده (StudentAcademicProfile.is_deleted=1) "
      "دیگر در فیلتر سالِ Observation/Intervention/FollowUp شمرده نمی‌شود",
      _k_before_obs - _k_after_obs == 4
      and _k_before_int - _k_after_int == 1
      and _k_before_follow - _k_after_follow == 2,
      f"obs {_k_before_obs}→{_k_after_obs}, int {_k_before_int}→{_k_after_int}, "
      f"follow {_k_before_follow}→{_k_after_follow}")

# --- K5: DashboardService._get_general_stats — سرتاسری با دیتاست تازه (بدون تداخل با K4)
with contextlib.redirect_stdout(io.StringIO()):
    _k_teacher_z = make_staff_and_user("teacher", "dash_k_teacher_z_r19")
    _k_student_z = StudentDAL().create(_new_student("کی-زد", "9100000003"))
    _k_profile_z = StudentAcademicProfileDAL().create(_new_profile(_k_student_z.id, _year_row["id"]))
    _k_obs(_k_profile_z.id, _k_teacher_z, "مثبت")
    _k_obs(_k_profile_z.id, _k_teacher_z, "مثبت")
    _k_obs(_k_profile_z.id, _k_teacher_z, "منفی")
    _k_dashboard = DashboardService()
    _k_general = _k_dashboard._get_general_stats(teacher_id=_k_teacher_z, year_id=_year_row["id"])
check("K", "K5: DashboardService._get_general_stats — خروجیِ سرتاسری بعد از تعویضِ "
      "get_all()←Aggregate SQL با محاسبهٔ دستی یکی است",
      _k_general['observations_count'] == 3 and _k_general['positive_count'] == 2
      and _k_general['negative_count'] == 1 and _k_general['has_data'] is True,
      f"{_k_general}")

# --- K6: DashboardService._get_teacher_stats — همان الگو برای آمار یک معلم
_k_teacher_stats = _k_dashboard._get_teacher_stats(_k_teacher_z, year_id=_year_row["id"])
check("K", "K6: DashboardService._get_teacher_stats — نسبت مثبت/تعداد صحیح از Aggregate",
      _k_teacher_stats is not None and _k_teacher_stats['observations_count'] == 3
      and abs(_k_teacher_stats['positive_percent'] - 66.7) < 0.5,
      f"{_k_teacher_stats}")

# --- K7: DashboardService._get_observation_trend — سطل ماه جاری از GROUP BY تازه
_k_trend_result = _k_dashboard._get_observation_trend(teacher_id=_k_teacher_x, year_id=None)
check("K", "K7: DashboardService._get_observation_trend — روند ۶ ماههٔ اخیر از "
      "get_monthly_trend می‌آید و total با جمع شمارش‌ها برابر است",
      _k_trend_result['total'] == sum(_k_trend_result['counts'])
      and len(_k_trend_result['months']) == 6,
      f"{_k_trend_result}")

# --- K8: ضمانتِ عدم بازگشتِ الگوی قدیمی — سه متد اصلاح‌شده دیگر get_all()
#     خام صدا نمی‌زنند (فقط متدهای Aggregate جدید)
_k_src_general = _j_inspect.getsource(DashboardService._get_general_stats)
_k_src_trend = _j_inspect.getsource(DashboardService._get_observation_trend)
_k_src_teacher = _j_inspect.getsource(DashboardService._get_teacher_stats)
# نکته: student_dal.get_all() عمداً دست‌نخورده ماند (خارج از حیطهٔ
# PERF-01/08/09 که فقط observation/intervention/followup را نشانه رفته
# بود)؛ فقط سه فراخوانیِ get_all() این سه DAL باید حذف شده باشند.
_k_banned_calls = (
    "observation_dal.get_all()", "intervention_dal.get_all()", "followup_dal.get_all()")
_k_offenders = [
    call for call in _k_banned_calls
    if call in _k_src_general or call in _k_src_trend or call in _k_src_teacher
]
check("K", "K8: _get_general_stats/_get_observation_trend/_get_teacher_stats دیگر "
      "observation_dal.get_all()/intervention_dal.get_all()/followup_dal.get_all() "
      "خام صدا نمی‌زنند (جایگزین با get_dashboard_stats/count_all/get_monthly_trend)",
      len(_k_offenders) == 0,
      f"موارد یافت‌شده: {_k_offenders}" if _k_offenders else "ok")

AccessControl.logout()

print("=" * 76)
print("بخش L: مرحلهٔ ۸ — SEC-HARD-DELETE-01 / RESTORE-EDGE-01")
print("=" * 76)

from dal.staff_dal import StaffDAL
from dal.user_dal import UserDAL

# --- L1: StudentDAL.permanent_delete — Permission + گاردِ وابستگی تازه
with contextlib.redirect_stdout(io.StringIO()):
    _l_viewer = make_staff_and_user("viewer", "l_viewer_r19")
    _l_student1 = StudentDAL().create(_new_student("ال-یک", "9300000001"))
    _l_profile1 = StudentAcademicProfileDAL().create(_new_profile(_l_student1.id, _year_row["id"]))
login(_l_viewer)
_l1_denied = False
try:
    StudentDAL().permanent_delete(_l_student1.id)
except PermissionDeniedError:
    _l1_denied = True
AccessControl.logout()
_l1_blocked = False
try:
    StudentDAL().permanent_delete(_l_student1.id)
except ValueError:
    _l1_blocked = True
check("L", "L1: StudentDAL.permanent_delete — VIEWER رد می‌شود؛ حتی با مجوز، "
      "وجود پروندهٔ سالانه مانع حذف دائم می‌شود (بدون این مرحله، هیچ‌کدام "
      "بررسی نمی‌شد و CASCADE کل تاریخچه را پاک می‌کرد)",
      _l1_denied and _l1_blocked)

# --- L2: InterventionDAL.permanent_delete — گاردِ وابستگی روی followups (CASCADE واقعی)
with contextlib.redirect_stdout(io.StringIO()):
    _l_student2 = StudentDAL().create(_new_student("ال-دو", "9300000002"))
    _l_profile2 = StudentAcademicProfileDAL().create(_new_profile(_l_student2.id, _year_row["id"]))
    _l_inter2 = InterventionDAL().create(_new_intervention(_l_profile2.id))
    FollowUpDAL().create(_new_followup(_l_inter2.id))
_l2_blocked = False
try:
    InterventionDAL().permanent_delete(_l_inter2.id)
except ValueError:
    _l2_blocked = True
check("L", "L2: InterventionDAL.permanent_delete — با پیگیریِ وابسته رد می‌شود "
      "(followups.intervention_id با ON DELETE CASCADE وصل است)",
      _l2_blocked)

# --- L3: ObservationDAL/FollowUpDAL/UserDAL.permanent_delete — Permission تازه
with contextlib.redirect_stdout(io.StringIO()):
    _l_obs3 = ObservationDAL().create(_new_observation(_l_profile2.id))
    _l_follow3 = FollowUpDAL().create(_new_followup(_l_inter2.id))
    _l_victim_staff = make_staff_and_user("viewer", "l_victim_r19")
    _l_victim_user_row = conn.execute(
        "SELECT id FROM users WHERE staff_id = ?", (_l_victim_staff,)).fetchone()
login(_l_viewer)
_l3_obs_denied = _l3_follow_denied = _l3_user_denied = False
try:
    ObservationDAL().permanent_delete(_l_obs3.id)
except PermissionDeniedError:
    _l3_obs_denied = True
try:
    FollowUpDAL().permanent_delete(_l_follow3.id)
except PermissionDeniedError:
    _l3_follow_denied = True
try:
    UserDAL().permanent_delete(_l_victim_user_row["id"])
except PermissionDeniedError:
    _l3_user_denied = True
AccessControl.logout()
check("L", "L3: ObservationDAL/FollowUpDAL/UserDAL.permanent_delete اکنون همگی "
      "Permission می‌خواهند (قبلاً هیچ‌کدام بررسی نمی‌کردند)",
      _l3_obs_denied and _l3_follow_denied and _l3_user_denied)

# --- L4: StaffDAL.permanent_delete — گاردِ وابستگیِ قبلی دست‌نخورده + Permission تازه
login(_l_viewer)
_l4_denied = False
try:
    StaffDAL().permanent_delete(_l_victim_staff)
except PermissionDeniedError:
    _l4_denied = True
AccessControl.logout()
check("L", "L4: StaffDAL.permanent_delete — قبل از این مرحله فقط گاردِ وابستگی "
      "داشت (سند تأیید کرده بود) ولی Permission نداشت؛ حالا VIEWER رد می‌شود",
      _l4_denied)

# --- L5: ObservationDAL.restore — RESTORE-EDGE-01 (پروندهٔ والد حذف‌شده)
with contextlib.redirect_stdout(io.StringIO()):
    ObservationDAL().delete(_l_obs3.id, 1)
    StudentAcademicProfileDAL().delete(_l_profile2.id, 1)
_l5_blocked = False
try:
    ObservationDAL().restore(_l_obs3.id)
except ValueError:
    _l5_blocked = True
check("L", "L5: ObservationDAL.restore رد می‌شود وقتی پروندهٔ سالانهٔ والد "
      "خودش حذف‌شده است (نه فقط بررسی Scope)", _l5_blocked)

# --- L6: InterventionDAL.restore — همان الگو
with contextlib.redirect_stdout(io.StringIO()):
    InterventionDAL().delete(_l_inter2.id, 1)
_l6_blocked = False
try:
    InterventionDAL().restore(_l_inter2.id)
except ValueError:
    _l6_blocked = True
check("L", "L6: InterventionDAL.restore رد می‌شود وقتی پروندهٔ سالانهٔ والد "
      "حذف‌شده است", _l6_blocked)

# --- L7: FollowUpDAL.restore — والد = مداخلهٔ حذف‌شده
with contextlib.redirect_stdout(io.StringIO()):
    FollowUpDAL().delete(_l_follow3.id, 1)
_l7_blocked = False
try:
    FollowUpDAL().restore(_l_follow3.id)
except ValueError:
    _l7_blocked = True
check("L", "L7: FollowUpDAL.restore رد می‌شود وقتی مداخلهٔ والد حذف‌شده است",
      _l7_blocked)

# --- L8: StudentAcademicProfileDAL.restore — والد = دانش‌آموزِ حذف‌شده
with contextlib.redirect_stdout(io.StringIO()):
    StudentDAL().delete(_l_student2.id, 1)
_l8_blocked = False
try:
    StudentAcademicProfileDAL().restore(_l_profile2.id)
except ValueError:
    _l8_blocked = True
check("L", "L8: StudentAcademicProfileDAL.restore رد می‌شود وقتی دانش‌آموزِ "
      "والد حذف‌شده است", _l8_blocked)

# --- L9: AttachmentService.restore_attachment — والد = مشاهدهٔ حذف‌شده
with contextlib.redirect_stdout(io.StringIO()):
    _l_student9 = StudentDAL().create(_new_student("ال-نه", "9300000009"))
    _l_profile9 = StudentAcademicProfileDAL().create(_new_profile(_l_student9.id, _year_row["id"]))
    _l_obs9 = ObservationDAL().create(_new_observation(_l_profile9.id))
    from services.attachment_service import AttachmentService as _L_AttachmentService
    _l_att_service = _L_AttachmentService()
    _l_att = _l_att_service.upload_attachment(
        "observation", _l_obs9.id, b"content", "l9.txt",
        created_by=None, user_id=None)
    _l_att_service.delete_attachment(_l_att.id)
    ObservationDAL().delete(_l_obs9.id, 1)
from utils.error_handler import ServiceError as _L_ServiceError

_l9_blocked = False
try:
    _l_att_service.restore_attachment(_l_att.id)
except _L_ServiceError as _l9_exc:
    _l9_blocked = "والد" in str(_l9_exc)
check("L", "L9: AttachmentService.restore_attachment رد می‌شود وقتی موجودیت "
      "والدِ پیوست (همان مشاهده) حذف‌شده است", _l9_blocked)

AccessControl.logout()

print("=" * 76)
print("بخش M: تکمیلِ یافتهٔ جانبیِ مرحلهٔ ۸ — StudentAcademicProfileDAL.delete/restore")
print("=" * 76)

# --- M1: delete/restore پروندهٔ سالانه اکنون Permission می‌خواهند (قبلاً هیچ)
with contextlib.redirect_stdout(io.StringIO()):
    _m_viewer = make_staff_and_user("viewer", "m_viewer_r19")
    _m_student1 = StudentDAL().create(_new_student("ام-یک", "9500000001"))
    _m_profile1 = StudentAcademicProfileDAL().create(_new_profile(_m_student1.id, _year_row["id"]))
login(_m_viewer)
_m1_delete_denied = False
try:
    StudentAcademicProfileDAL().delete(_m_profile1.id, _m_viewer)
except PermissionDeniedError:
    _m1_delete_denied = True
AccessControl.logout()
with contextlib.redirect_stdout(io.StringIO()):
    StudentAcademicProfileDAL().delete(_m_profile1.id, 1)
login(_m_viewer)
_m1_restore_denied = False
try:
    StudentAcademicProfileDAL().restore(_m_profile1.id)
except PermissionDeniedError:
    _m1_restore_denied = True
AccessControl.logout()
check("M", "M1: StudentAcademicProfileDAL.delete/restore اکنون همان مجوز "
      "DELETE_STUDENT را می‌خواهند (قبلاً کلِ این DAL هیچ Permission‌ای نداشت)",
      _m1_delete_denied and _m1_restore_denied)

# --- M2: Scope هم اعمال می‌شود (معلمِ بدون انتساب رد می‌شود)
with contextlib.redirect_stdout(io.StringIO()):
    _m_teacher = make_staff_and_user("teacher", "m_teacher_r19")
    _m_student2 = StudentDAL().create(_new_student("ام-دو", "9500000002"))
    _m_profile2 = StudentAcademicProfileDAL().create(_new_profile(_m_student2.id, _year_row["id"]))
login(_m_teacher)
_m2_blocked = False
try:
    StudentAcademicProfileDAL().delete(_m_profile2.id, _m_teacher)
except PermissionDeniedError:
    # TEACHER اصلاً DELETE_STUDENT ندارد؛ این خودش تأیید می‌کند که مرز
    # فعال است (Permission زودتر از Scope رد می‌کند)
    _m2_blocked = True
AccessControl.logout()
check("M", "M2: StudentAcademicProfileDAL.delete برای TEACHER رد می‌شود "
      "(نه Permission دارد، نه در این مرحله Scope موضوعیت پیدا می‌کند)",
      _m2_blocked)

AccessControl.logout()

# ============================================================
print("=" * 76)
print(f"نتیجهٔ دور نوزدهم (مرحله‌های ۱ تا ۸ + تکمیلِ یافتهٔ جانبی):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
if FAILURES:
    print("موارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
print("=" * 76)

with contextlib.suppress(Exception):
    dbc.DatabaseConnection().close_all()

sys.exit(1 if FAIL else 0)
