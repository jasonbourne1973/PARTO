"""
راستی‌آزمایی دور بیست‌وچهارم — فاز ۵ (DEF-05): اثباتِ end-to-end مسیرِ
ایمپورت/خروجیِ اکسل، طبق تصمیمِ صریحِ کاربر: رفتارِ فعلیِ commitِ
جزئی/ردیف‌به‌ردیف («keep_partial_as_is») دقیقاً همان‌طور که هست حفظ
می‌شود — DEF-05 در این دور به‌معنیِ «رفعِ اشکال» نیست، به‌معنیِ اثباتِ
end-to-end همان قرارداد است.

مبنا: docs/tech_audit_20_fa.md (بخش ۵، فاز ۵).

پوششِ این فایل (نکاتی که در verify_fixes4/16/17/19.py و
tests/test_import_export_edges.py و tests/test_permission_boundary.py
به‌صورتِ جداگانه اثبات شده بودند، ولی این ترکیبِ دقیق تا این دور آزموده
نشده بود):

  • بخش A — سفرِ واقعیِ کاربر از «دکمه تا دکمه»: کلیکِ «دانلود نمونه»
    (StudentsPage.download_sample_excel) → همان فایلِ واقعیِ تولیدشده،
    بدونِ هیچ دست‌کاری، به «ایمپورت از اکسل»
    (StudentsPage.import_from_excel) داده می‌شود → باید هر دو ردیفِ
    نمونه با موفقیتِ کامل (صفر خطا) وارد شوند و فهرستِ صفحه (بعد از
    بازخوانیِ خودکار) آن‌ها را نشان دهد. پیش از این، هر نیمه جدا آزموده
    شده بود (round23: create_sample_excel→import_students_from_excel
    مستقیم؛ round17 D5/D6: import_from_excel با فایل‌های دستی) ولی نه
    این دو دکمهٔ واقعیِ UI روی یک فایل.
  • بخش B — قراردادِ «commit جزئی» (تصمیمِ صریحِ کاربر در همین فاز):
    یک فایل با ردیف‌های معتبر + نامعتبر (کدملی تکراری در همان فایل و
    تاریخ نامعتبر) → ردیف‌های معتبر باید در دیتابیس بمانند، ردیف‌های
    نامعتبر رد شوند، و موفقیتِ ردیف‌های پیشین با شکستِ ردیف‌های بعدی
    rollback نشود. این آزمون صراحتاً مستندسازِ تصمیمِ
    «keep_partial_as_is» است (نه یک باگ).
  • بخش C — مرزِ مجوز از مسیرِ واقعیِ صفحه (نه صدا زدنِ مستقیمِ
    ExcelImporter): کاربرِ بدونِ CREATE_STUDENT روی
    StudentsPage.import_from_excel کلیک می‌کند → باید دیالوگِ خطا
    (critical) ببیند، نه موفقیت، و هیچ دانش‌آموزی نباید ساخته شود.
    (tests/test_permission_boundary.py مستقیماً ExcelImporter را صدا
    می‌زند؛ اینجا دقیقاً همان متدِ صفحه که کاربر کلیک می‌کند آزموده
    می‌شود.)
  • بخش D — همهٔ ستون‌های اختیاریِ فایلِ نمونه (نام پدر/نام
    ولی/تلفنِ ولی/آدرس/پایه/کلاس) باید دقیقاً به فیلدهای متناظرشان در
    دیتابیس برسند (نه فقط نام/نام‌خانوادگی/کدملی).

نکتهٔ محیط: این فایل به Qt واقعی نیاز دارد (StudentsPage یک QWidget
است):

    LD_LIBRARY_PATH=/home/user/qtstub/lib QT_QPA_PLATFORM=offscreen \\
        python3 verify_fixes24.py

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


TMP = tempfile.mkdtemp(prefix="round24_verify_")
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

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

app = QApplication.instance() or QApplication(sys.argv)

from utils.security import AccessControl

AccessControl.logout()

from dal.academic_year_dal import AcademicYearDAL
from dal.staff_dal import StaffDAL
from dal.student_dal import StudentDAL
from dal.user_dal import UserDAL
from models.academic_year import AcademicYear
from models.staff import Staff
from models.user import User
from views.pages.students_page import StudentsPage

student_dal = StudentDAL()

# --- فیکسچر: یک سال تحصیلیِ فعال (لازم برای دیالوگِ انتخابِ سال در ایمپورت)
year = AcademicYear()
year.title = "1403-1404"
year.start_date = "1403/07/01"
year.end_date = "1404/06/30"
year.is_active = 0
year.is_archived = 0
with contextlib.redirect_stdout(io.StringIO()):
    year = AcademicYearDAL().create(year)
    AcademicYearDAL().set_active(year.id)


def _make_staff_and_user(role, username):
    """ساخت staff + user با نقش دلخواه؛ خروجی: (users_id, staff_id)"""
    saved = AccessControl.current_staff_id()
    AccessControl.logout()
    try:
        staff = Staff()
        staff.full_name = f"آزمون {role}"
        staff.role = "other"
        with contextlib.redirect_stdout(io.StringIO()):
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


# --- استاب‌های Qt: دیالوگ‌های پیام و انتخابِ سال هرگز نباید واقعاً باز
# شوند (offscreen قفل می‌کند)؛ QFileDialog با مسیرِ فایلِ موردنظر پاسخ
# می‌دهد.
message_log = []
real_info = QMessageBox.information
real_crit = QMessageBox.critical
real_warn = QMessageBox.warning
real_get_open = QFileDialog.getOpenFileName
real_get_save = QFileDialog.getSaveFileName
real_dialog_exec = QDialog.exec

QMessageBox.information = staticmethod(
    lambda *a, **k: message_log.append(("info", str(a[2]))) or QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(
    lambda *a, **k: message_log.append(("crit", str(a[2]))) or QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(
    lambda *a, **k: message_log.append(("warn", str(a[2]))) or QMessageBox.StandardButton.Ok)


def _accept_year_dialog():
    """دیالوگِ انتخابِ سالِ تحصیلی را با «تأیید» (سالِ اولِ فعال) می‌بندد"""
    QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Accepted


def _restore_dialog_exec():
    QDialog.exec = real_dialog_exec


with contextlib.redirect_stdout(io.StringIO()):
    spage = StudentsPage()

# ============================================================
# بخش A: سفرِ واقعیِ کاربر — دانلودِ نمونه (UI) → ایمپورتِ همان فایل (UI)
# ============================================================
print("=" * 76)
print("بخش A: DEF-05 — سفرِ کاملِ «دانلودِ نمونه» → «ایمپورتِ همان فایل» از مسیرِ واقعیِ UI")
print("=" * 76)

sample_path = os.path.join(TMP, "نمونه_دانش‌آموزان.xlsx")
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (sample_path, ""))
n_msgs_before = len(message_log)
with contextlib.redirect_stdout(io.StringIO()):
    spage.download_sample_excel()
QFileDialog.getSaveFileName = real_get_save
download_msgs = message_log[n_msgs_before:]

check("A", "A1: کلیکِ «دانلودِ نمونه» فایلِ واقعی می‌سازد و پیامِ موفقیت می‌دهد",
      os.path.exists(sample_path) and os.path.getsize(sample_path) > 0
      and download_msgs and download_msgs[-1][0] == "info",
      f"exists={os.path.exists(sample_path)} msgs={download_msgs}")

students_before = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
n_msgs_before = len(message_log)
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (sample_path, "xlsx"))
_accept_year_dialog()
try:
    with contextlib.redirect_stdout(io.StringIO()):
        spage.import_from_excel()
finally:
    QFileDialog.getOpenFileName = real_get_open
    _restore_dialog_exec()
app.processEvents()
import_msgs = message_log[n_msgs_before:]
students_after = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]

a2_ok = (
    students_after == students_before + 2
    and import_msgs and import_msgs[-1][0] == "info"
    and "خطا" not in import_msgs[-1][1].split("\n\n")[0]
)
check("A", "A2 (هستهٔ DEF-05): همان فایلِ واقعیِ «نمونه» بدونِ هیچ دست‌کاری، از مسیرِ واقعیِ «ایمپورت از اکسل» هر دو ردیف را بدونِ خطا وارد می‌کند",
      a2_ok, f"students {students_before}->{students_after} last_msg={import_msgs[-1] if import_msgs else None}")

check("A", "A3: بعد از ایمپورتِ موفق، صفحه خودش را بازخوانی می‌کند و دانش‌آموزهای تازه در فهرست/COUNT دیده می‌شوند",
      spage.total_count == students_after
      and any(s.first_name == "علی" and s.last_name == "محمدی" for s in spage.students)
      and any(s.first_name == "سارا" and s.last_name == "احمدی" for s in spage.students),
      f"total_count={spage.total_count} names={[(s.first_name, s.last_name) for s in spage.students]}")

# ============================================================
# بخش B: قراردادِ commit جزئی (تصمیمِ صریحِ کاربر: keep_partial_as_is)
# ============================================================
print("=" * 76)
print("بخش B: DEF-05 — قراردادِ «commit جزئی» صراحتاً اثبات/مستند می‌شود (نه یک باگ)")
print("=" * 76)

import openpyxl

mixed_path = os.path.join(TMP, "mixed_round24.xlsx")
wb = openpyxl.Workbook()
ws = wb.active
ws.append(["نام", "نام خانوادگی", "کد ملی", "تاریخ تولد"])
ws.append(["معتبر۱", "ردیف", "6611111111", "1395/01/01"])       # معتبر
ws.append(["معتبر۲", "ردیف", "6622222222", "1395/01/01"])       # معتبر
ws.append(["نامعتبر", "کدملیِ‌تکراری", "6611111111", "1395/01/01"])  # تکراریِ ردیفِ اول همین فایل
ws.append(["نامعتبر", "تاریخِ‌غلط", "6633333333", "1395/13/45"])  # تاریخِ نامعتبر
wb.save(mixed_path)

from utils.excel_importer import ExcelImporter

importer = ExcelImporter()
with contextlib.redirect_stdout(io.StringIO()):
    b_success, b_message, b_imported, b_errors = importer.import_students_from_excel(
        mixed_path, year.id)

b1_ok = b_success and b_imported == 2 and len(b_errors) == 2
check("B", "B1: از ۴ ردیف (۲ معتبر، ۱ کدملیِ تکراریِ داخلِ همان فایل، ۱ تاریخِ نامعتبر) → دقیقاً ۲ ایمپورتِ موفق و ۲ خطا",
      b1_ok, f"success={b_success} imported={b_imported} errors={b_errors}")

valid1 = student_dal.get_by_national_code("6611111111")
valid2 = student_dal.get_by_national_code("6622222222")
invalid_dup = [s for s in (student_dal.get_all() or []) if getattr(s, "last_name", "") == "کدملیِ‌تکراری"]
invalid_date = [s for s in (student_dal.get_all() or []) if getattr(s, "last_name", "") == "تاریخِ‌غلط"]

check("B", "B2 (قراردادِ keep_partial_as_is): ردیف‌های معتبر واقعاً در دیتابیس commit شده‌اند و ردیف‌های ردشده هیچ اثری در دیتابیس ندارند — موفقیتِ ردیف‌های پیشین با شکستِ ردیف‌های بعدی rollback نمی‌شود",
      valid1 is not None and valid2 is not None and not invalid_dup and not invalid_date,
      f"valid1={valid1} valid2={valid2} dup_leftover={invalid_dup} date_leftover={invalid_date}")

# ============================================================
# بخش C: مرزِ مجوز از مسیرِ واقعیِ StudentsPage.import_from_excel
# (نه صدا زدنِ مستقیمِ ExcelImporter، بلکه دقیقاً همان متدی که با
# کلیکِ دکمه اجرا می‌شود)
# ============================================================
print("=" * 76)
print("بخش C: DEF-05 — مرزِ مجوز از مسیرِ واقعیِ صفحه (کلیکِ دکمهٔ «ایمپورت»)")
print("=" * 76)

viewer_staff_id = _make_staff_and_user("viewer", "viewer_round24")
students_before_c = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]

no_perm_path = os.path.join(TMP, "no_perm_round24.xlsx")
wb2 = openpyxl.Workbook()
ws2 = wb2.active
ws2.append(["نام", "نام خانوادگی", "کد ملی"])
ws2.append(["بدونِ‌مجوز", "کاربر", "6644444444"])
wb2.save(no_perm_path)

AccessControl.login(viewer_staff_id, None)
n_msgs_before = len(message_log)
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (no_perm_path, "xlsx"))
_accept_year_dialog()
try:
    with contextlib.redirect_stdout(io.StringIO()):
        spage.import_from_excel()
finally:
    QFileDialog.getOpenFileName = real_get_open
    _restore_dialog_exec()
    AccessControl.logout()
c_msgs = message_log[n_msgs_before:]
students_after_c = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]

check("C", "C1: کاربرِ «viewer» (بدونِ CREATE_STUDENT) با کلیکِ واقعیِ «ایمپورت از اکسل» فقط دیالوگِ خطا می‌بیند، نه موفقیت، و هیچ دانش‌آموزی ساخته نمی‌شود",
      bool(c_msgs) and c_msgs[-1][0] == "crit"
      and students_after_c == students_before_c
      and student_dal.get_by_national_code("6644444444") is None,
      f"msgs={c_msgs} students {students_before_c}->{students_after_c}")

# ============================================================
# بخش D: همهٔ ستون‌های اختیاریِ فایلِ نمونه به فیلدهای درست می‌رسند
# ============================================================
print("=" * 76)
print("بخش D: DEF-05 — ستون‌های اختیاریِ فایلِ نمونه (پدر/ولی/تلفن/آدرس/پایه/کلاس) به‌درستی ذخیره می‌شوند")
print("=" * 76)

ali = student_dal.get_by_national_code("1234567890")
sara = student_dal.get_by_national_code("0987654321")

d_ok = (
    ali is not None and sara is not None
    and ali.father_name == "رضا" and ali.guardian_name == "رضا محمدی"
    and ali.guardian_phone == "09123456789" and ali.address == "تهران"
    and sara.father_name == "حسن" and sara.guardian_name == "حسن احمدی"
    and sara.guardian_phone == "09123456788" and sara.address == "تهران"
)
check("D", "D1: ستون‌های اختیاریِ نام‌پدر/نام‌ولی/تلفنِ‌ولی/آدرس از فایلِ نمونه (بخشِ A) دقیقاً روی فیلدهای متناظرِ Student ذخیره شده‌اند",
      d_ok, f"ali={ali.__dict__ if ali else None} sara={sara.__dict__ if sara else None}")

profile_dal = None
with contextlib.suppress(Exception):
    from dal.student_academic_profile_dal import StudentAcademicProfileDAL
    profile_dal = StudentAcademicProfileDAL()

ali_profiles = [p for p in (profile_dal.get_all() if profile_dal else []) if p.student_id == ali.id] if ali else []
sara_profiles = [p for p in (profile_dal.get_all() if profile_dal else []) if p.student_id == sara.id] if sara else []

check("D", "D2: پایه و کلاسِ فایلِ نمونه (پایهٔ ۳/کلاسِ الف برای علی، پایهٔ ۲/کلاسِ ب برای سارا) در پروندهٔ سالانه ذخیره شده",
      len(ali_profiles) == 1 and ali_profiles[0].grade == 3 and ali_profiles[0].class_name == "الف"
      and len(sara_profiles) == 1 and sara_profiles[0].grade == 2 and sara_profiles[0].class_name == "ب",
      f"ali_profiles={[(p.grade, p.class_name) for p in ali_profiles]} "
      f"sara_profiles={[(p.grade, p.class_name) for p in sara_profiles]}")

# --- پاک‌سازی استاب‌ها
QMessageBox.information = real_info
QMessageBox.critical = real_crit
QMessageBox.warning = real_warn
AccessControl.logout()

print("=" * 76)
print(f"نتیجهٔ دور بیست‌وچهارم (فاز ۵ — DEF-05):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
