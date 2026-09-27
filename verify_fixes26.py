"""
راستی‌آزمایی دور بیست‌وششم — فاز ۷ (DEF-07): گسترشِ پوششِ
Runtime/GUI Acceptance (offscreen) — پوششِ یک شکافِ واقعیِ باقی‌مانده.

مبنا: docs/tech_audit_20_fa.md (بخش ۱، DEF-07) و بخش ۷، فاز ۷. طبقِ
تصمیمِ کاربر (ask_user، «best_effort_gap_scan»): چون متنِ دقیقِ
سناریوهای «۹.۱ تا ۹.۸» از سندِ ورودیِ اصلی در مخزن نیست، این فاز به‌جایِ
حدس‌زدنِ آن فهرست، یک بررسیِ عملیِ پوشش انجام داد: برایِ هر کلاسِ صفحه
در `views/pages/*.py`، آیا حداقل یک آزمونِ Qt واقعیِ offscreen (نه فقط
بررسیِ ایستایِ متن کد) آن را واقعاً می‌سازد و متدهایِ اصلی‌اش را صدا
می‌زند؟

### نتیجهٔ پویش

اکثرِ صفحه‌ها (Students/Observations/Interventions/FollowUps/
Indicators/Analysis/Settings/Backup/AcademicStructure/Counseling/
Activities/Goals/ReportsPage با زیرصفحه‌هایِ ClassReport/TeacherReport/
TeacherPerformance/DashboardPage با AnalyticsDashboardPage) از دورهای
۱۴ تا ۲۵ به‌صورتِ عمیق و با دادهٔ واقعی آزموده شده‌اند — نه فقط ساختنِ
صفحه، بلکه فراخوانیِ متدهایِ واقعیِ دکمه‌ها، خروجیِ واقعیِ PDF/Excel،
تغییرِ ترکیب‌بندی‌ها، و اعتبارسنجیِ نتیجه رویِ دیتابیس.

**شکافِ واقعیِ پیداشده:** `views/pages/promotion_page.py`
(`PromotionPage`) از هیچ‌کدام از دورهای قبل — حتی به‌صورتِ ساختنِ صفحه
هم — به‌طور مستقیم آزموده نشده بود (فقط از طریقِ ساختِ `MainWindow`/
`AcademicStructurePage` می‌ساخته می‌شد که فقط `__init__`/`load_students`
اولیه را اجرا می‌کند). متدهایِ اصلیِ عملیاتیِ این صفحه —
`promote_all_students`, `promote_selected_students`,
`repeat_grade_students`, `_promote_one_student`,
`_get_or_create_target_year` — که مستقیماً پرونده‌هایِ سالانهٔ واقعی
می‌سازند/می‌بندند، در **هیچ** فایلِ `verify_fixes*.py` یا `tests/*.py`
حتی یک‌بار صدا زده نشده بودند. این دقیقاً همان نوعِ شکافی است که
DEF-07 به‌دنبالِ آن بود: منطقِ واقعیِ دکمه، نه فقط ساختنِ ویجت.

این فایل همان شکاف را می‌پوشاند.

### پوشش این فایل

  • بخش A — `promote_all_students`: با ۴ دانش‌آموز (پایهٔ ۲، پایهٔ ۵،
    پایهٔ ۶ [فارغ‌التحصیلی]، و یکی بدونِ پروندهٔ فعال ولی با سابقهٔ
    پایهٔ ۴) → نتیجهٔ دقیقِ هرکدام رویِ دیتابیس:
      - پایهٔ ۲/۵: پروندهٔ سالِ مبدأ INACTIVE می‌شود؛ پروندهٔ تازه در
        سالِ مقصد با پایهٔ ۳/۶ و STATUS_ACTIVE ساخته می‌شود.
      - پایهٔ ۶: پروندهٔ سالِ مبدأ GRADUATED می‌شود؛ هیچ پروندهٔ
        تازه‌ای در سالِ مقصد ساخته نمی‌شود.
      - بدونِ پروندهٔ فعال (سابقهٔ پایهٔ ۴): پروندهٔ تازه با پایهٔ ۵
        (۴+۱) در سالِ مقصد ساخته می‌شود.
  • بخش B — لغوِ دیالوگِ تأیید (No) → هیچ تغییری در دیتابیس.
  • بخش C — `promote_selected_students`: فقط زیرمجموعهٔ انتخاب‌شده
    ارتقاء می‌یابند؛ بقیه دست‌نخورده می‌مانند.
  • بخش D — گاردِ «اجرایِ دوباره»: صدا زدنِ دوبارهٔ ارتقاء با همان سالِ
    مقصد، پروندهٔ تکراری نمی‌سازد (0 پرونده تازه).
  • بخش E — `repeat_grade_students`: پروندهٔ تازه با **همان** پایه
    (نه پایه+۱) در سالِ مقصد ساخته می‌شود.

نکتهٔ محیط: این فایل به Qt واقعی نیاز دارد (PromotionPage یک QWidget
است):

    LD_LIBRARY_PATH=/home/user/qtstub/lib QT_QPA_PLATFORM=offscreen \\
        python3 verify_fixes26.py

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


TMP = tempfile.mkdtemp(prefix="round26_verify_")
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

from PySide6.QtWidgets import QApplication, QMessageBox

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


def new_profile(student_id, year_id, grade, status=StudentAcademicProfile.STATUS_ACTIVE):
    p = StudentAcademicProfile()
    p.student_id = student_id
    p.academic_year_id = year_id
    p.grade = grade
    p.class_name = ""
    p.status = status
    with quiet():
        return profile_dal.create(p)


real_question = QMessageBox.question
real_info = QMessageBox.information
real_crit = QMessageBox.critical
real_warn = QMessageBox.warning
message_log = []
QMessageBox.information = staticmethod(
    lambda *a, **k: message_log.append(("info", str(a[2]))) or QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(
    lambda *a, **k: message_log.append(("crit", str(a[2]))) or QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(
    lambda *a, **k: message_log.append(("warn", str(a[2]))) or QMessageBox.StandardButton.Ok)


def _answer_yes():
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)


def _answer_no():
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)


import jdatetime  # noqa: E402

from views.pages.promotion_page import PromotionPage  # noqa: E402


def _select_year_input(page, title):
    """
    انتخابِ عنوانِ سالِ مقصد در کامبویِ year_input

    این کامبو setEditable ندارد؛ setCurrentText رویِ متنی که در فهرست
    نیست هیچ اثری ندارد (رفتارِ استانداردِ Qt). به‌جایِ آن باید عنوان از
    میانِ آیتم‌هایِ از پیش ساخته‌شده (سالِ جاریِ شمسی−۲ تا +۴) انتخاب شود.
    """
    idx = page.year_input.findText(title)
    assert idx >= 0, f"عنوانِ «{title}» در کامبویِ year_input نیست"
    page.year_input.setCurrentIndex(idx)
    assert page.year_input.currentText() == title


# --- فیکسچر مشترک: سالِ مبدأ فعال با ۴ دانش‌آموزِ متنوع
# (سالِ مبدأ عمداً خیلی قدیمی/دور از بازهٔ کامبویِ year_input انتخاب شده
# تا هرگز با target_title/2/3 که از دلِ همان کامبو انتخاب می‌شوند تداخل
# نکند — کامبو فقط سالِ جاریِ شمسی−۲ تا +۴ را دارد.)
_cy = jdatetime.datetime.now().year
year_src = _year(f"{_cy - 20}-{_cy - 19}", f"{_cy - 20}/07/01", f"{_cy - 19}/06/31", make_active=True)
target_title = f"{_cy + 2}-{_cy + 3}"    # از کامبو (پیش‌فرض = +۱) انتخاب می‌شود
target_title2 = f"{_cy + 3}-{_cy + 4}"
target_title3 = f"{_cy + 4}-{_cy + 5}"

s_low = new_student("پایین‌رتبه", "ارتقاء", "8100000001")     # پایهٔ ۲
s_mid = new_student("میان‌رتبه", "ارتقاء", "8100000002")      # پایهٔ ۵
s_grad = new_student("فارغ‌التحصیل", "ارتقاء", "8100000003")  # پایهٔ ۶
s_hist = new_student("بدون‌پروندهٔ‌فعال", "ارتقاء", "8100000004")  # فقط سابقه

p_low = new_profile(s_low.id, year_src.id, grade=2)
p_mid = new_profile(s_mid.id, year_src.id, grade=5)
p_grad = new_profile(s_grad.id, year_src.id, grade=6)
# s_hist: پروندهٔ INACTIVE در سالی دیگر (نه سالِ فعال) → get_active_by_student چیزی برنمی‌گرداند
year_old = _year("1400-1401", "1400/07/01", "1401/06/31", make_active=False)
p_hist = new_profile(s_hist.id, year_old.id, grade=4, status=StudentAcademicProfile.STATUS_INACTIVE)

with quiet():
    ppage = PromotionPage()
_select_year_input(ppage, target_title)

# ============================================================
# بخش A: promote_all_students — نتیجهٔ دقیقِ هر مسیر
# ============================================================
print("=" * 76)
print("بخش A: DEF-07 — PromotionPage.promote_all_students با ۴ مسیرِ متفاوت")
print("=" * 76)

_answer_yes()
n_msgs_before = len(message_log)
with quiet():
    ppage.promote_all_students()
a_msgs = message_log[n_msgs_before:]

target_year = AcademicYearDAL().get_by_title(target_title)
check("A", "A0: سالِ مقصد با همین عنوان ساخته شد و پیامِ موفقیت نمایش داده شد",
      target_year is not None and a_msgs and a_msgs[-1][0] == "info",
      f"target_year={target_year} msgs={a_msgs}")

low_new = profile_dal.get_by_student_and_year(s_low.id, target_year.id) if target_year else None
mid_new = profile_dal.get_by_student_and_year(s_mid.id, target_year.id) if target_year else None
grad_new = profile_dal.get_by_student_and_year(s_grad.id, target_year.id) if target_year else None
hist_new = profile_dal.get_by_student_and_year(s_hist.id, target_year.id) if target_year else None

p_low_after = profile_dal.get_by_id(p_low.id)
p_mid_after = profile_dal.get_by_id(p_mid.id)
p_grad_after = profile_dal.get_by_id(p_grad.id)

check("A", "A1: دانش‌آموزِ پایهٔ ۲ → پروندهٔ سالِ مبدأ INACTIVE؛ پروندهٔ تازه در سالِ مقصد با پایهٔ ۳ و ACTIVE",
      p_low_after.status == StudentAcademicProfile.STATUS_INACTIVE
      and low_new is not None and low_new.grade == 3
      and low_new.status == StudentAcademicProfile.STATUS_ACTIVE,
      f"old_status={p_low_after.status} new={low_new.__dict__ if low_new else None}")

check("A", "A2: دانش‌آموزِ پایهٔ ۵ → پروندهٔ سالِ مبدأ INACTIVE؛ پروندهٔ تازه در سالِ مقصد با پایهٔ ۶ و ACTIVE",
      p_mid_after.status == StudentAcademicProfile.STATUS_INACTIVE
      and mid_new is not None and mid_new.grade == 6
      and mid_new.status == StudentAcademicProfile.STATUS_ACTIVE,
      f"old_status={p_mid_after.status} new={mid_new.__dict__ if mid_new else None}")

check("A", "A3 (فارغ‌التحصیلی): دانش‌آموزِ پایهٔ ۶ → پروندهٔ سالِ مبدأ GRADUATED؛ هیچ پروندهٔ تازه‌ای در سالِ مقصد ساخته نمی‌شود",
      p_grad_after.status == StudentAcademicProfile.STATUS_GRADUATED and grad_new is None,
      f"old_status={p_grad_after.status} new={grad_new}")

check("A", "A4 (بدونِ پروندهٔ فعال، از سابقه): دانش‌آموزی که پروندهٔ فعال ندارد ولی سابقهٔ پایهٔ ۴ دارد → پروندهٔ تازه با پایهٔ ۵ در سالِ مقصد",
      hist_new is not None and hist_new.grade == 5
      and hist_new.status == StudentAcademicProfile.STATUS_ACTIVE,
      f"new={hist_new.__dict__ if hist_new else None}")

# ============================================================
# بخش B: لغوِ دیالوگِ تأیید → هیچ تغییری
# ============================================================
print("=" * 76)
print("بخش B: DEF-07 — لغوِ دیالوگِ تأیید (پاسخِ «خیر») هیچ تغییری نمی‌دهد")
print("=" * 76)

s_cancel = new_student("لغوشده", "ارتقاء", "8100000005")
p_cancel = new_profile(s_cancel.id, year_src.id, grade=3)
with quiet():
    ppage.load_students()

_answer_no()
n_msgs_before = len(message_log)
with quiet():
    ppage.promote_all_students()
b_msgs = message_log[n_msgs_before:]

p_cancel_after = profile_dal.get_by_id(p_cancel.id)
cancel_new = profile_dal.get_by_student_and_year(s_cancel.id, target_year.id)
check("B", "B1: پاسخِ «خیر» به دیالوگِ تأیید → نه پیامی نشان داده می‌شود، نه پروندهٔ دانش‌آموز تغییر می‌کند",
      not b_msgs and p_cancel_after.status == StudentAcademicProfile.STATUS_ACTIVE
      and cancel_new is None,
      f"msgs={b_msgs} status={p_cancel_after.status} new={cancel_new}")

# ============================================================
# بخش C: promote_selected_students — فقط زیرمجموعهٔ انتخاب‌شده
# ============================================================
print("=" * 76)
print("بخش C: DEF-07 — PromotionPage.promote_selected_students فقط انتخاب‌شده‌ها را ارتقاء می‌دهد")
print("=" * 76)

_select_year_input(ppage, target_title2)

s_sel_a = new_student("انتخاب‌شده", "ارتقاء", "8100000006")
s_sel_b = new_student("انتخاب‌نشده", "ارتقاء", "8100000007")
p_sel_a = new_profile(s_sel_a.id, year_src.id, grade=1)
p_sel_b = new_profile(s_sel_b.id, year_src.id, grade=1)
with quiet():
    ppage.load_students()
ppage.selected_student_ids = [s_sel_a.id]

_answer_yes()
n_msgs_before = len(message_log)
with quiet():
    ppage.promote_selected_students()
c_msgs = message_log[n_msgs_before:]

target_year2 = AcademicYearDAL().get_by_title(target_title2)
sel_a_new = profile_dal.get_by_student_and_year(s_sel_a.id, target_year2.id) if target_year2 else None
sel_b_new = profile_dal.get_by_student_and_year(s_sel_b.id, target_year2.id) if target_year2 else None
p_sel_b_after = profile_dal.get_by_id(p_sel_b.id)

check("C", "C1: فقط دانش‌آموزِ انتخاب‌شده در سالِ مقصدِ تازه پروندهٔ جدید می‌گیرد؛ انتخاب‌نشده کاملاً دست‌نخورده می‌ماند",
      sel_a_new is not None and sel_a_new.grade == 2
      and sel_b_new is None
      and p_sel_b_after.status == StudentAcademicProfile.STATUS_ACTIVE
      and c_msgs and "1" in c_msgs[-1][1],
      f"sel_a_new={sel_a_new.__dict__ if sel_a_new else None} sel_b_new={sel_b_new} "
      f"b_status={p_sel_b_after.status} msg={c_msgs[-1:] if c_msgs else None}")

# ============================================================
# بخش D: گاردِ «اجرایِ دوباره» — بدونِ پروندهٔ تکراری
# ============================================================
print("=" * 76)
print("بخش D: DEF-07 — اجرایِ دوبارهٔ ارتقاء با همان سالِ مقصد، پروندهٔ تکراری نمی‌سازد")
print("=" * 76)

with quiet():
    ppage.load_students()
_answer_yes()
n_msgs_before = len(message_log)
with quiet():
    ppage.promote_all_students()   # همان سالِ مقصدِ target_title2؛ s_low/mid/grad/hist قبلاً به target_title رفته‌اند
d_msgs = message_log[n_msgs_before:]

# s_sel_a قبلاً به target_title2 رفته؛ دوباره اجرا نباید پروندهٔ دومی برایش بسازد
sel_a_profiles_in_target2 = [
    p for p in (profile_dal.get_all_profiles_for_student(s_sel_a.id) or [])
    if p.academic_year_id == target_year2.id
]
check("D", "D1: دانش‌آموزی که قبلاً به این سالِ مقصد ارتقاء یافته، با اجرایِ دوباره پروندهٔ تکراری نمی‌گیرد (فقط همان یک پرونده می‌ماند)",
      len(sel_a_profiles_in_target2) == 1 and bool(d_msgs),
      f"count={len(sel_a_profiles_in_target2)} msgs={d_msgs[-1:] if d_msgs else None}")

# ============================================================
# بخش E: repeat_grade_students — همان پایه، نه پایه+۱
# ============================================================
print("=" * 76)
print("بخش E: DEF-07 — PromotionPage.repeat_grade_students پایه را ثابت نگه می‌دارد")
print("=" * 76)

_select_year_input(ppage, target_title3)

# نکته: تا این‌جا سالِ فعال چند بار عوض شده (هر ارتقاءِ موفق، سالِ
# مقصدِ خودش را فعال می‌کند)؛ پروندهٔ این دانش‌آموز باید در همان سالِ
# «فعلاً فعال» ساخته شود تا get_active_by_student آن را پیدا کند.
current_active_before_e = AcademicYearDAL().get_active()
s_repeat = new_student("تکرارپایه", "ارتقاء", "8100000008")
p_repeat = new_profile(s_repeat.id, current_active_before_e.id, grade=4)
with quiet():
    ppage.load_students()
ppage.selected_student_ids = [s_repeat.id]

_answer_yes()
n_msgs_before = len(message_log)
with quiet():
    ppage.repeat_grade_students()
e_msgs = message_log[n_msgs_before:]

target_year3 = AcademicYearDAL().get_by_title(target_title3)
repeat_new = profile_dal.get_by_student_and_year(s_repeat.id, target_year3.id) if target_year3 else None
p_repeat_after = profile_dal.get_by_id(p_repeat.id)

check("E", "E1: تکرارِ پایه → پروندهٔ تازه در سالِ مقصد با **همان** پایهٔ ۴ (نه ۵) و ACTIVE؛ پروندهٔ قبلی INACTIVE",
      repeat_new is not None and repeat_new.grade == 4
      and repeat_new.status == StudentAcademicProfile.STATUS_ACTIVE
      and p_repeat_after.status == StudentAcademicProfile.STATUS_INACTIVE
      and bool(e_msgs),
      f"repeat_new={repeat_new.__dict__ if repeat_new else None} old_status={p_repeat_after.status}")

# --- پاک‌سازی استاب‌ها
QMessageBox.question = real_question
QMessageBox.information = real_info
QMessageBox.critical = real_crit
QMessageBox.warning = real_warn
AccessControl.logout()

print("=" * 76)
print(f"نتیجهٔ دور بیست‌وششم (فاز ۷ — DEF-07):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
