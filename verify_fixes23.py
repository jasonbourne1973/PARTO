"""
راستی‌آزمایی دور بیست‌وسوم — فاز ۴ (DEF-04): اثباتِ کاملِ قراردادِ
Pagination/COUNT به‌صورت end-to-end برای هر «فهرست».

مبنا: docs/tech_audit_20_fa.md (بخش ۴، فاز ۴) — ادامهٔ راستی‌آزمایی‌های
verify_fixes17/19/20/21/22.py.

دامنهٔ بررسی‌شده (شرح کامل در گزارش فاز ۴):
  • بازبینیِ ایستایِ همهٔ جفت‌های get_all()/count_all() (و
    search()/count_search()) در ObservationDAL، InterventionDAL،
    FollowUpDAL، ExtracurricularDAL، StudentDAL — تأییدِ اینکه
    WHERE/JOIN دو عضوِ هر جفت دقیقاً یکسان است (بدون رگرسیون از فازهای
    قبل). این بخش صرفاً بازبینیِ کد بود، نه آزمونِ خودکارِ تازه (چون
    verify_fixes17 §D1/D2 و verify_fixes21 §B از قبل این قرارداد را
    برای مقادیرِ واقعی می‌سنجند).
  • هستهٔ فاز ۴ — نقصِ واقعیِ کشف‌شده و رفع‌شده: در
    `views/pages/students_page.py`، دکمه‌های «صفحهٔ بعد/قبل»، تغییرِ
    «تعداد در صفحه» و چک‌باکسِ «نمایشِ حذف‌شده‌ها» همیشه بی‌قیدوشرط
    `load_students()` (فهرستِ کاملِ بدونِ فیلتر) را صدا می‌زدند — یعنی
    اگر کاربر عبارتی جست‌وجو می‌کرد که به چند صفحه می‌رسید (دکمهٔ
    «بعدی» فعال می‌شد)، کلیک روی «صفحهٔ بعد» عبارتِ جست‌وجو را نادیده
    می‌گرفت و فهرستِ کاملِ نامرتبط را (با اندیسِ صفحهٔ اشتباه) نشان
    می‌داد — نقضِ آشکارِ قراردادِ COUNT/Pagination برای «فهرستِ
    جست‌وجوشده». رفع شد با یک مسیرِ مشترکِ `_reload_current_page` که
    فیلترِ جست‌وجویِ فعال را تشخیص می‌دهد و مسیرِ درست
    (`_run_search`/`load_students`) را صدا می‌زند.

نکتهٔ محیط: این فایل به Qt واقعی نیاز دارد (StudentsPage یک QWidget
است):

    LD_LIBRARY_PATH=/home/user/qtstub/lib QT_QPA_PLATFORM=offscreen \\
        python3 verify_fixes23.py

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


TMP = tempfile.mkdtemp(prefix="round23_verify_")
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

from dal.student_dal import StudentDAL
from models.student import Student
from views.pages.students_page import StudentsPage

student_dal = StudentDAL()


def new_student(first_name, last_name, national_code):
    s = Student()
    s.first_name = first_name
    s.last_name = last_name
    s.national_code = national_code
    with contextlib.redirect_stdout(io.StringIO()):
        return student_dal.create(s)


# ============================================================
# بخش D: DEF-04 — قراردادِ Pagination/COUNT هنگامِ ناوبری/تغییرِ
# اندازهٔ صفحه/تغییرِ حالتِ حذف‌شده در حینِ جست‌وجوی فعال
# ============================================================
print("=" * 76)
print("بخش D: DEF-04 — قراردادِ Pagination/COUNT در تعاملِ جست‌وجو + ناوبری")
print("=" * 76)

# فیکسچر: ۱۵ دانش‌آموزِ منطبق با عبارتِ جست‌وجو («جستجو۲۳») + ۵ دانش‌آموزِ
# نامرتبط (که فقط باید در فهرستِ کامل/بدون‌فیلتر دیده شوند).
matching = [new_student("جستجو۲۳", f"ردیف{i:02d}", f"{5100000000 + i}")
            for i in range(15)]
unrelated = [new_student("نامرتبط۲۳", f"ردیف{i:02d}", f"{5200000000 + i}")
             for i in range(5)]
matching_ids = {s.id for s in matching}
unrelated_ids = {s.id for s in unrelated}

with contextlib.redirect_stdout(io.StringIO()):
    spage = StudentsPage()

spage.page_size_combo.setCurrentText("10")
spage.search_input.setText("جستجو۲۳")   # textChanged → search_students() (صفحهٔ ۰)

d1_ok = (
    spage.total_count == 15
    and spage.total_pages == 2
    and len(spage.students) == 10
    and {s.id for s in spage.students} <= matching_ids
    and spage.next_page_btn.isEnabled()
)
check("D", "D1: جست‌وجوی «۱۵ نتیجه» با اندازهٔ صفحهٔ ۱۰ → صفحهٔ اول ۱۰ ردیف، ۲ صفحه، «بعدی» فعال",
      d1_ok, f"total={spage.total_count} pages={spage.total_pages} n={len(spage.students)}")

page1_ids = {s.id for s in spage.students}
spage.next_page()  # هستهٔ رفع نقص: قبلاً اینجا load_students (فهرست کامل) صدا زده می‌شد

d2_ok = (
    spage.current_page == 1
    and spage.total_count == 15          # نه شمارشِ کاملِ ۲۰تایی
    and len(spage.students) == 5         # ۵ ردیفِ باقی‌ماندهٔ همان جست‌وجو
    and {s.id for s in spage.students} <= matching_ids
    and {s.id for s in spage.students}.isdisjoint(unrelated_ids)
    and {s.id for s in spage.students}.isdisjoint(page1_ids)
)
check("D", "D2 (هستهٔ رفع DEF-04): کلیک «صفحهٔ بعد» حینِ جست‌وجو، همان جست‌وجو را ادامه می‌دهد (نه فهرستِ کاملِ نامرتبط)",
      d2_ok,
      f"page={spage.current_page} total={spage.total_count} n={len(spage.students)} "
      f"ids={sorted({s.id for s in spage.students})}")

spage.prev_page()
d3_ok = (
    spage.current_page == 0
    and {s.id for s in spage.students} == page1_ids
)
check("D", "D3: «صفحهٔ قبل» از صفحهٔ دومِ جست‌وجو، دقیقاً همان ۱۰ ردیفِ صفحهٔ اولِ جست‌وجو را برمی‌گرداند",
      d3_ok, f"ids={sorted({s.id for s in spage.students})} expected={sorted(page1_ids)}")

# D4: تغییرِ «تعداد در صفحه» حینِ جست‌وجوی فعال باید همان جست‌وجو را با
# اندازهٔ تازه دوباره اجرا کند، نه فهرستِ کامل را.
spage.page_size_combo.setCurrentText("20")
d4_ok = (
    spage.total_count == 15
    and len(spage.students) == 15
    and {s.id for s in spage.students} == matching_ids
)
check("D", "D4: تغییرِ اندازهٔ صفحه (۱۰→۲۰) حینِ جست‌وجوی فعال، همان ۱۵ نتیجهٔ جست‌وجو را در یک صفحه نشان می‌دهد",
      d4_ok, f"total={spage.total_count} n={len(spage.students)}")

# D5: خاموش کردنِ جست‌وجو → ناوبری باید به رفتارِ فهرستِ کاملِ قبلی برگردد
spage.search_input.clear()  # textChanged → load_students() چون عبارت خالی است
d5_ok = spage.total_count == 20 and {s.id for s in spage.students} <= (matching_ids | unrelated_ids)
check("D", "D5 (بدون رگرسیون): پاک‌کردنِ عبارتِ جست‌وجو، به فهرستِ کاملِ ۲۰تایی برمی‌گردد",
      d5_ok, f"total={spage.total_count}")

spage.page_size_combo.setCurrentText("10")
spage.current_page = 0
spage.load_students()
before_np_ids = {s.id for s in spage.students}
spage.next_page()
d6_ok = (
    spage.current_page == 1
    and spage.total_count == 20
    and {s.id for s in spage.students}.isdisjoint(before_np_ids)
)
check("D", "D6 (بدون رگرسیون): «صفحهٔ بعد» بدونِ جست‌وجوی فعال هنوز رفتارِ قبلیِ فهرستِ کامل را دارد",
      d6_ok, f"page={spage.current_page} total={spage.total_count}")

# D7: چک‌باکسِ «نمایشِ حذف‌شده‌ها» حینِ جست‌وجوی فعال باید همان جست‌وجو را
# روی فهرستِ حذف‌شده (نه فهرستِ کاملِ فعال) اجرا کند.
from services.student_service import StudentService

student_service = StudentService()
with contextlib.redirect_stdout(io.StringIO()):
    for s in matching[:3]:
        student_service.delete_student(s.id, user_id=1)
deleted_matching_ids = {s.id for s in matching[:3]}

spage.search_input.setText("جستجو۲۳")   # جست‌وجوی فعال روی فهرستِ فعال (۱۲ تای باقی‌مانده)
d7a_ok = spage.total_count == 12 and {s.id for s in spage.students}.isdisjoint(deleted_matching_ids)
spage.on_show_deleted_toggled(True)     # تغییرِ حالت، با جست‌وجوی فعال
d7b_ok = (
    spage.total_count == 3
    and {s.id for s in spage.students} == deleted_matching_ids
)
spage.on_show_deleted_toggled(False)
spage.search_input.clear()
check("D", "D7: تغییرِ «نمایشِ حذف‌شده‌ها» حینِ جست‌وجوی فعال، همان عبارت را روی فهرستِ درست (فعال→۱۲، حذف‌شده→۳) اجرا می‌کند",
      d7a_ok and d7b_ok,
      f"active_total={spage.total_count if d7a_ok else 'N/A'} deleted_ids={sorted({s.id for s in spage.students}) if not d7a_ok else 'skipped'}")

AccessControl.logout()

print("=" * 76)
print(f"نتیجهٔ دور بیست‌وسوم (فاز ۴ — DEF-04):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
