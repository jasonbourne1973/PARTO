"""
راستی‌آزمایی دور بیست‌ویکم — فاز ۲ (DEF-02): یکسان‌سازیِ فیلترِ
سال-تحصیلی/پروندهٔ-حذف‌شده در محل‌هایی که عقب افتاده بودند.

مبنا: docs/tech_audit_20_fa.md (بخش ۲، فاز ۲) — ادامهٔ راستی‌آزمایی‌های
verify_fixes19/20.py.

بخش‌ها:
  B) DEF-02 — پروندهٔ حذف‌شده نباید در فیلتر سال شمرده شود:
     • ObservationDAL.get_by_student(student_id, academic_year_id)
     • InterventionDAL.get_by_student(student_id, academic_year_id)
     • ObservationDAL / InterventionDAL / FollowUpDAL — search با
       academic_year_id (از طریق _search_where مشترک)
     • ObservationDAL.get_trend_by_class — یافتهٔ جانبی: پارامتر
       academic_year_id قبلاً کاملاً بی‌اثر بود؛ اکنون واقعاً اعمال
       می‌شود.
     • services/class_report_service.py — _get_class_intervention_stats
       / _get_class_followup_stats

نکتهٔ محیط: این فایل به Qt واقعی نیاز ندارد؛ در صورت نیاز با:

    LD_LIBRARY_PATH=/home/user/qtstub/lib QT_QPA_PLATFORM=offscreen \\
        python3 verify_fixes21.py

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


TMP = tempfile.mkdtemp(prefix="round21_verify_")
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

from utils.security import AccessControl

AccessControl.logout()

year_row = conn.execute(
    "SELECT id FROM academic_years WHERE is_active = 1 LIMIT 1").fetchone()
YEAR_ID = year_row["id"]

from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.followup import FollowUp
from models.intervention import Intervention
from models.observation import Observation
from models.student import Student
from models.student_academic_profile import StudentAcademicProfile

student_dal = StudentDAL()
profile_dal = StudentAcademicProfileDAL()
observation_dal = ObservationDAL()
intervention_dal = InterventionDAL()
followup_dal = FollowUpDAL()


def new_student(last_name, national_code):
    s = Student()
    s.first_name = "آزمون۲۱"
    s.last_name = last_name
    s.national_code = national_code
    return student_dal.create(s)


def new_profile(student_id, academic_year_id=None, class_name="اول-الف"):
    p = StudentAcademicProfile()
    p.student_id = student_id
    p.academic_year_id = academic_year_id or YEAR_ID
    p.grade = 1
    p.class_name = class_name
    return profile_dal.create(p)


def new_observation(profile_id, description="مشاهدهٔ آزمون۲۱", date="1404/01/01"):
    o = Observation()
    o.student_profile_id = profile_id
    o.staff_id = 1
    o.observation_date = date
    o.description = description
    o.behavior_type = "خنثی"
    return observation_dal.create(o)


def new_intervention(profile_id, description="مداخلهٔ آزمون۲۱"):
    i = Intervention()
    i.student_profile_id = profile_id
    i.staff_id = 1
    i.type = "گفتگوی فردی"
    i.date = "1404/01/01"
    i.description = description
    return intervention_dal.create(i)


def new_followup(intervention_id, description="پیگیری آزمون۲۱"):
    f = FollowUp()
    f.intervention_id = intervention_id
    f.staff_id = 1
    f.date = "1404/01/01"
    f.description = description
    return followup_dal.create(f)


# ============================================================
# بخش B: DEF-02 — یکسان‌سازیِ فیلتر سال/پروندهٔ حذف‌شده
# ============================================================
print("=" * 76)
print("بخش B: DEF-02 — پروندهٔ حذف‌شده نباید در فیلتر سالِ تحصیلی شمرده شود")
print("=" * 76)

# B1: ObservationDAL.get_by_student — پیش از حذف پرونده
s1 = new_student("الف۲۱", "9700000001")
p1 = new_profile(s1.id)
new_observation(p1.id)
r1 = observation_dal.get_by_student(s1.id, academic_year_id=YEAR_ID)
check("B", "B1: ObservationDAL.get_by_student با سالِ معتبر، مشاهده را برمی‌گرداند",
      len(r1) == 1)

# B2: بعد از حذف پرونده → باید خالی شود (هم‌راستا با get_all)
profile_dal.delete(p1.id, 1)
r2 = observation_dal.get_by_student(s1.id, academic_year_id=YEAR_ID)
r2_all = observation_dal.get_all(academic_year_id=YEAR_ID)
check("B", "B2: بعد از حذفِ پرونده، ObservationDAL.get_by_student(سال) دیگر مشاهده را برنمی‌گرداند",
      r2 == [] and all(o.student_profile_id != p1.id for o in r2_all))

# B3: InterventionDAL.get_by_student — همان الگو
s3 = new_student("ب۲۱", "9700000002")
p3 = new_profile(s3.id)
new_intervention(p3.id)
r3_before = intervention_dal.get_by_student(s3.id, academic_year_id=YEAR_ID)
profile_dal.delete(p3.id, 1)
r3_after = intervention_dal.get_by_student(s3.id, academic_year_id=YEAR_ID)
check("B", "B3: InterventionDAL.get_by_student با فیلتر سال، بعد از حذفِ پرونده خالی می‌شود",
      len(r3_before) == 1 and r3_after == [])

# B4: ObservationDAL.search با academic_year_id — پروندهٔ حذف‌شده
s4 = new_student("ج۲۱", "9700000003")
p4 = new_profile(s4.id)
new_observation(p4.id, description="واژهٔ‌یکتای۲۱‌الف")
found_before = observation_dal.search("واژهٔ‌یکتای۲۱‌الف", academic_year_id=YEAR_ID)
profile_dal.delete(p4.id, 1)
found_after = observation_dal.search("واژهٔ‌یکتای۲۱‌الف", academic_year_id=YEAR_ID)
check("B", "B4: ObservationDAL.search با فیلتر سال، بعد از حذفِ پرونده نتیجه نمی‌دهد",
      len(found_before) == 1 and found_after == [])

# B5: InterventionDAL.search با academic_year_id
s5 = new_student("د۲۱", "9700000004")
p5 = new_profile(s5.id)
new_intervention(p5.id, description="واژهٔ‌یکتای۲۱‌ب")
found5_before = intervention_dal.search("واژهٔ‌یکتای۲۱‌ب", academic_year_id=YEAR_ID)
profile_dal.delete(p5.id, 1)
found5_after = intervention_dal.search("واژهٔ‌یکتای۲۱‌ب", academic_year_id=YEAR_ID)
check("B", "B5: InterventionDAL.search با فیلتر سال، بعد از حذفِ پرونده نتیجه نمی‌دهد",
      len(found5_before) == 1 and found5_after == [])

# B6: FollowUpDAL.search با academic_year_id (زنجیرهٔ Followup→Intervention→Profile)
s6 = new_student("ه۲۱", "9700000005")
p6 = new_profile(s6.id)
i6 = new_intervention(p6.id)
new_followup(i6.id, description="واژهٔ‌یکتای۲۱‌ج")
found6_before = followup_dal.search("واژهٔ‌یکتای۲۱‌ج", academic_year_id=YEAR_ID)
profile_dal.delete(p6.id, 1)
found6_after = followup_dal.search("واژهٔ‌یکتای۲۱‌ج", academic_year_id=YEAR_ID)
check("B", "B6: FollowUpDAL.search با فیلتر سال، بعد از حذفِ پروندهٔ زنجیره نتیجه نمی‌دهد",
      len(found6_before) == 1 and found6_after == [])

# B7: get_trend_by_class — یافتهٔ جانبی: پارامتر academic_year_id قبلاً بی‌اثر بود
s7 = new_student("و۲۱", "9700000006")
p7 = new_profile(s7.id, class_name="کلاس-روند۲۱")
new_observation(p7.id, date="1404/01/01")
trend_no_filter = observation_dal.get_trend_by_class("کلاس-روند۲۱")
trend_with_year = observation_dal.get_trend_by_class("کلاس-روند۲۱", academic_year_id=YEAR_ID)
profile_dal.delete(p7.id, 1)
trend_after_delete = observation_dal.get_trend_by_class("کلاس-روند۲۱", academic_year_id=YEAR_ID)
check("B", "B7: get_trend_by_class اکنون واقعاً با academic_year_id فیلتر می‌کند "
      "و بعد از حذفِ پرونده خالی می‌شود",
      sum(p["total"] for p in trend_no_filter) == 1
      and sum(p["total"] for p in trend_with_year) == 1
      and sum(p["total"] for p in trend_after_delete) == 0)

# B8/B9: class_report_service._get_class_intervention_stats / _get_class_followup_stats
from services.class_report_service import ClassReportService

report_service = ClassReportService()

s8 = new_student("ز۲۱", "9700000007")
p8 = new_profile(s8.id, class_name="کلاس-گزارش۲۱")
new_intervention(p8.id)
stats8_before = report_service._get_class_intervention_stats("کلاس-گزارش۲۱", YEAR_ID)
profile_dal.delete(p8.id, 1)
stats8_after = report_service._get_class_intervention_stats("کلاس-گزارش۲۱", YEAR_ID)
check("B", "B8: _get_class_intervention_stats بعد از حذفِ پرونده، مداخله را نمی‌شمارد",
      stats8_before["total"] == 1 and stats8_after["total"] == 0)

s9 = new_student("ح۲۱", "9700000008")
p9 = new_profile(s9.id, class_name="کلاس-گزارش۲۱-ب")
i9 = new_intervention(p9.id)
new_followup(i9.id)
stats9_before = report_service._get_class_followup_stats("کلاس-گزارش۲۱-ب", YEAR_ID)
profile_dal.delete(p9.id, 1)
stats9_after = report_service._get_class_followup_stats("کلاس-گزارش۲۱-ب", YEAR_ID)
check("B", "B9: _get_class_followup_stats بعد از حذفِ پرونده، پیگیری را نمی‌شمارد",
      stats9_before["total"] == 1 and stats9_after["total"] == 0)

# ============================================================
print("=" * 76)
print(f"نتیجهٔ دور بیست‌ویکم (فاز ۲ — DEF-02):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
if FAILURES:
    print("موارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
print("=" * 76)

with contextlib.suppress(Exception):
    dbc.DatabaseConnection().close_all()

sys.exit(1 if FAIL else 0)
