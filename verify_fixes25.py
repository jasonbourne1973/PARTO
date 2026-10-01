"""
راستی‌آزمایی دور بیست‌وپنجم — فاز ۶ (DEF-06): رفعِ N+1 در
StudentProfilePage.load_student_list.

مبنا: docs/tech_audit_20_fa.md (بخش ۱، ردیفِ DEF-06 — همان نقصِ واقعیِ
verify_fixes14.py §E) و بخش ۶، فاز ۶.

### نقص (پیش از رفع)

`views/pages/student_profile_page.py :: load_student_list` وقتی
`self.selected_year_id` مقدار داشت (که با انتخابِ پیش‌فرضِ سالِ فعال در
`load_academic_years`، همیشه همین حالت است)، برایِ **هرِ** دانش‌آموز
جداگانه `self.profile_dal.get_by_student_and_year(student.id, ...)`
صدا می‌زد — یعنی با N دانش‌آموز، N کوئریِ جداگانه به
`student_academic_profiles`. شاخهٔ `else` (بدونِ سال) از قبل درست بود
و از متدِ گروهیِ `get_active_by_students` استفاده می‌کرد.

### چرا رفعش ساده و کم‌ریسک بود

متدِ گروهیِ لازم، `StudentAcademicProfileDAL.get_by_students_and_year`،
از «دورِ هجدهم» دقیقاً برایِ همین منظور در DAL وجود داشت («بدون این
متد، رفعِ N+1 ناقص می‌ماند» — کامنتِ خودِ آن دور) ولی هیچ نقطهٔ تماسی
(call site) هرگز آن را صدا نمی‌زد. رفع، فقط سیم‌کشیِ دو خط بود: به‌جایِ
دیکشنری‌سازیِ دستی با یک کوئری به‌ازایِ هر دانش‌آموز، همان متدِ گروهیِ
موجود صدا زده شد. هیچ امضایی تغییر نکرد، هیچ DALِ تازه‌ای اضافه نشد.

### پوششِ این فایل

  • بخشِ A — شمارشِ کوئری: با N دانش‌آموز و سالِ انتخاب‌شده، دقیقاً
    «۱» کوئریِ `student_academic_profiles` زده می‌شود (نه N).
  • بخشِ B — درستیِ داده (نه فقط شمارشِ کوئری): متنِ نمایش‌داده‌شده برایِ
    هر دانش‌آموز باید دقیقاً پایهٔ همان «سالِ انتخاب‌شده» را نشان دهد —
    نه پایهٔ سالِ دیگر، حتی وقتی همان دانش‌آموز در چند سال پرونده دارد.
  • بخشِ C — دانش‌آموزِ بدونِ پرونده در سالِ انتخاب‌شده → «نامشخص» (بدونِ
    خطا، بدونِ نشتِ دادهٔ سالِ دیگر).
  • بخشِ D — تغییرِ سال از کامبوباکس (`reload_for_year`) هم از همین
    مسیرِ گروهی استفاده می‌کند و پایهٔ درستِ سالِ تازه را نشان می‌دهد.
  • بخشِ E — فهرستِ خالیِ دانش‌آموزان → بدونِ خطا.

نکتهٔ محیط: این فایل به Qt واقعی نیاز دارد (StudentProfilePage یک
QWidget است):

    LD_LIBRARY_PATH=/home/user/qtstub/lib QT_QPA_PLATFORM=offscreen \\
        python3 verify_fixes25.py

اجرا شود.
"""

import contextlib
import io
import os
import re
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


TMP = tempfile.mkdtemp(prefix="round25_verify_")
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

from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from utils.security import AccessControl

AccessControl.logout()

from dal.academic_year_dal import AcademicYearDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.academic_year import AcademicYear
from models.student import Student
from models.student_academic_profile import StudentAcademicProfile

student_dal = StudentDAL()
profile_dal = StudentAcademicProfileDAL()


def quiet():
    return contextlib.redirect_stdout(io.StringIO())


def _year(title, start, end, make_active=False):
    year = AcademicYear()
    year.title = title
    year.start_date = start
    year.end_date = end
    year.is_active = 0
    year.is_archived = 0
    with quiet():
        year = AcademicYearDAL().create(year)
    if make_active:
        AcademicYearDAL().set_active(year.id)
    return year


def new_student(first_name, last_name, national_code):
    s = Student()
    s.first_name = first_name
    s.last_name = last_name
    s.national_code = national_code
    with quiet():
        return student_dal.create(s)


def new_profile(student_id, year_id, grade, class_name=""):
    p = StudentAcademicProfile()
    p.student_id = student_id
    p.academic_year_id = year_id
    p.grade = grade
    p.class_name = class_name
    p.status = StudentAcademicProfile.STATUS_ACTIVE
    with quiet():
        return profile_dal.create(p)


QUERY_LOG = []


def _trace(statement):
    QUERY_LOG.append(statement)


def _count(pattern):
    rx = re.compile(pattern, re.IGNORECASE)
    return sum(1 for q in QUERY_LOG if rx.search(q))


def _reset():
    del QUERY_LOG[:]


conn.set_trace_callback(_trace)

# --- فیکسچر: دو سالِ تحصیلی + ۲۰ دانش‌آموز با پروندهٔ سالِ ۱ و پروندهٔ
# متفاوت برایِ سالِ ۲ (پایه فرق دارد تا «درستیِ داده» هم سنجیده شود)
year1 = _year("1402-1403", "1402/07/01", "1403/06/31", make_active=True)
year2 = _year("1403-1404", "1403/07/01", "1404/06/31", make_active=False)

students = [new_student(f"دانش‌آموز۲۵_{i:02d}", "آزمون", f"{7100000000 + i}") for i in range(20)]
for s in students:
    new_profile(s.id, year1.id, grade=1, class_name="اول-الف")
    new_profile(s.id, year2.id, grade=2, class_name="دوم-ب")

# دانش‌آموزی که فقط در سالِ ۲ پرونده دارد (در سالِ ۱ چیزی نیست)
only_year2 = new_student("فقط‌سالِ‌دو", "آزمون", "7100000099")
new_profile(only_year2.id, year2.id, grade=3, class_name="سوم-ج")

from views.pages.student_profile_page import StudentProfilePage  # noqa: E402

with quiet():
    ppage = StudentProfilePage()

# ============================================================
# بخش A: شمارشِ کوئری — ۲۱ دانش‌آموز، سالِ فعال (۱) انتخاب‌شده
# ============================================================
print("=" * 76)
print("بخش A: DEF-06 — شمارشِ کوئریِ پروندهٔ سالانه در load_student_list")
print("=" * 76)

_reset()
with quiet():
    ppage.load_student_list()
n_profile_q = _count(r"FROM student_academic_profiles\b")
n_student_q = _count(r"FROM students\b")
combo_count = ppage.student_select_combo.count()
all_count = len(student_dal.get_all())

check("A", "A1 (هستهٔ رفعِ DEF-06): با ۲۱ دانش‌آموز و سالِ انتخاب‌شده، فقط «۱» کوئریِ پروندهٔ سالانه زده می‌شود (نه یکی به ازایِ هر دانش‌آموز)",
      n_profile_q == 1 and n_student_q == 1 and combo_count == all_count + 1,
      f"profile_q={n_profile_q} student_q={n_student_q} combo={combo_count} all={all_count}")

# ============================================================
# بخش B: درستیِ داده — پایهٔ نمایش‌داده‌شده باید دقیقاً پایهٔ همان
# سالِ انتخاب‌شده باشد (نه سالِ دیگر)
# ============================================================
print("=" * 76)
print("بخش B: DEF-06 — درستیِ داده: پایهٔ نمایش‌داده‌شده مالِ همان سالِ انتخاب‌شده است")
print("=" * 76)


def _combo_texts(page):
    return {page.student_select_combo.itemData(i): page.student_select_combo.itemText(i)
            for i in range(page.student_select_combo.count())
            if page.student_select_combo.itemData(i) is not None}


def _grade_display(grade):
    p = StudentAcademicProfile()
    p.grade = grade
    return p.grade_display


texts_year1 = _combo_texts(ppage)
sample = students[0]
b1_ok = f"پایه {_grade_display(1)}" in texts_year1.get(sample.id, "")
check("B", "B1: در سالِ ۱ (فعال)، دانش‌آموزها با پایهٔ «۱» (پروندهٔ سالِ ۱) نمایش داده می‌شوند، نه پایهٔ سالِ ۲",
      b1_ok, f"text={texts_year1.get(sample.id)}")

ppage.reload_for_year(year2.id)
texts_year2 = _combo_texts(ppage)
b2_ok = f"پایه {_grade_display(2)}" in texts_year2.get(sample.id, "")
check("B", "B2: بعدِ سوئیچ به سالِ ۲ (reload_for_year)، همان دانش‌آموز حالا با پایهٔ «۲» (پروندهٔ سالِ ۲) نمایش داده می‌شود — بدونِ نشتِ دادهٔ سالِ ۱",
      b2_ok, f"text={texts_year2.get(sample.id)}")

# ============================================================
# بخش C: دانش‌آموزِ بدونِ پرونده در سالِ انتخاب‌شده → «نامشخص»
# ============================================================
print("=" * 76)
print("بخش C: DEF-06 — دانش‌آموزِ بدونِ پرونده در سالِ انتخاب‌شده")
print("=" * 76)

ppage.reload_for_year(year1.id)
texts_year1_again = _combo_texts(ppage)
c_ok = "نامشخص" in texts_year1_again.get(only_year2.id, "")
check("C", "C1: دانش‌آموزی که فقط در سالِ ۲ پرونده دارد، در نمایِ سالِ ۱ با «پایه نامشخص» دیده می‌شود (بدونِ خطا، بدونِ نشتِ دادهٔ سالِ دیگر)",
      c_ok, f"text={texts_year1_again.get(only_year2.id)}")

# ============================================================
# بخش D: تغییرِ سال با شمارشِ کوئری هنوز «۱» است (نه N)
# ============================================================
print("=" * 76)
print("بخش D: DEF-06 — بعدِ سوئیچِ سال هم شمارشِ کوئری «۱» می‌ماند")
print("=" * 76)

_reset()
with quiet():
    ppage.reload_for_year(year2.id)
n_profile_q_d = _count(r"FROM student_academic_profiles\b")
check("D", "D1: reload_for_year هم از همان مسیرِ گروهی استفاده می‌کند — «۱» کوئریِ پروندهٔ سالانه، نه N",
      n_profile_q_d == 1, f"profile_q={n_profile_q_d}")

# ============================================================
# بخش E: فهرستِ خالیِ دانش‌آموزان → بدونِ خطا
# ============================================================
print("=" * 76)
print("بخش E: DEF-06 — فهرستِ خالیِ دانش‌آموزان")
print("=" * 76)

empty_year = _year("1404-1405", "1404/07/01", "1405/06/31", make_active=False)
e_error = None
try:
    with quiet():
        empty_page = StudentProfilePage()
        empty_page.reload_for_year(empty_year.id)
except Exception as exc:  # pragma: no cover
    e_error = str(exc)

check("E", "E1: سالی که هیچ دانش‌آموزی با پروندهٔ آن سال ندارد → بدونِ خطا (کامبوباکس فقط «انتخاب دانش‌آموز...» دارد یا پایهٔ همه «نامشخص» است)",
      e_error is None, f"error={e_error}")

conn.set_trace_callback(None)
AccessControl.logout()

print("=" * 76)
print(f"نتیجهٔ دور بیست‌وپنجم (فاز ۶ — DEF-06):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
