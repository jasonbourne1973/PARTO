#!/usr/bin/env python3
"""
راستی‌آزمایی دور یازدهم — تحلیل رشد‌محور و رفتارمحور

بخش‌ها:
  A) قوت/ضعف بر پایهٔ «نوع رفتار» (۵ بررسی)
  B) روند بر پایهٔ ترکیب رفتارها، نه تعداد مشاهدات (۴ بررسی)
  C) تفکیک مشاهده / غربالگری / تفسیر حرفه‌ای (۳ بررسی)
  D) زمینهٔ خانوادگی به‌عنوان اطلاعات زمینه‌ای (۲ بررسی)
  E) گزارش رشدمحور و اثربخشی مداخلات (۴ بررسی)
  F) لحن محتاطانه و ردیابی‌پذیری پیشنهادها (۳ بررسی)
  G) لایهٔ داده و روایت چندساله (۳ بررسی)
  H) نگهبان‌های ساختاری (۲ بررسی)

اجرا:  python verify_fixes11.py
"""

import os
import re
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

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
    return open(os.path.join(ROOT, path), encoding='utf-8').read()


TMP = tempfile.mkdtemp(prefix='round11_verify_')

# ============================================================
# آماده‌سازی یک پروندهٔ آزمایشی با رفتارهای هدف‌دار
# ============================================================
import database.connection as dbc  # noqa: E402
from config import settings as cfg  # noqa: E402

cfg.DB_PATH = os.path.join(TMP, 'partow.db')
dbc.DB_PATH = cfg.DB_PATH
dbc.DatabaseConnection._instance = None
dbc.DatabaseConnection._connection = None
dbc.DatabaseConnection._initialized = False

conn = dbc.DatabaseConnection().get_connection()
cur = conn.cursor()
cur.execute("INSERT INTO academic_years (title, start_date, end_date, is_active) "
            "VALUES ('1404-1405', '1404/06/01', '1405/03/31', 1)")
cur.execute("INSERT INTO students (first_name, last_name, national_code) "
            "VALUES ('آزمون', 'رشد', '0000000001')")
student_id = cur.lastrowid
cur.execute("INSERT INTO staff (full_name, role) VALUES ('کارشناس آزمون', 'counselor')")
staff_id = cur.lastrowid
cur.execute("INSERT INTO student_academic_profiles (student_id, academic_year_id, grade, class_name) "
            "VALUES (?, 1, 3, 'الف')", (student_id,))
profile_id = cur.lastrowid
for title in ('شایستگی الف', 'شایستگی ب', 'شایستگی ج', 'شایستگی د'):
    cur.execute("INSERT INTO competencies (title, is_active) VALUES (?, 1)", (title,))
conn.commit()

comp_ids = [row[0] for row in cur.execute(
    "SELECT id FROM competencies WHERE title LIKE 'شایستگی %' ORDER BY id").fetchall()]

# الگوها:
#  الف) ۳ رفتار منفی با شدت ۵ → باید «نیازمند توجه» باشد (نه قوت)
#  ب) ۳ رفتار مثبت با شدت ۱ → باید «توانمندی» باشد (نه ضعف)
#  ج) یک رفتار منفی با شدت ۵ + یک مثبت با شدت ۱ → نه قوت، نه ضعف
#  د) دو رفتار خنثی → نه قوت، نه ضعف
obs_rows = [
    (comp_ids[0], '1404/06/05', 'منفی', 5, 'بی‌توجهی به تکلیف', 'ثبت اول'),
    (comp_ids[0], '1404/06/12', 'منفی', 5, 'بی‌توجهی به تکلیف', 'ثبت دوم'),
    (comp_ids[0], '1404/06/19', 'منفی', 5, 'بی‌توجهی به تکلیف', 'ثبت سوم'),
    (comp_ids[1], '1404/06/06', 'مثبت', 1, 'کمک به هم‌کلاسی', 'ثبت اول'),
    (comp_ids[1], '1404/06/13', 'مثبت', 1, 'کمک به هم‌کلاسی', 'ثبت دوم'),
    (comp_ids[1], '1404/06/20', 'مثبت', 1, 'کمک به هم‌کلاسی', 'ثبت سوم'),
    (comp_ids[2], '1404/06/07', 'منفی', 5, 'رفتار موردی', 'تک‌مورد منفی'),
    (comp_ids[2], '1404/06/14', 'مثبت', 1, 'رفتار موردی مثبت', 'تک‌مورد مثبت'),
    (comp_ids[3], '1404/06/08', 'خنثی', 2, 'رفتار خنثی', 'ثبت اول'),
    (comp_ids[3], '1404/06/15', 'خنثی', 2, 'رفتار خنثی', 'ثبت دوم'),
]
for comp_id, date, btype, severity, behavior, description in obs_rows:
    cur.execute(
        "INSERT INTO observations (student_profile_id, staff_id, competency_id, "
        "observation_date, location, description, behavior, behavior_type, severity) "
        "VALUES (?, ?, ?, ?, 'کلاس', ?, ?, ?, ?)",
        (profile_id, staff_id, comp_id, date, description, behavior, btype, severity))
conn.commit()

from dal.observation_dal import ObservationDAL  # noqa: E402
from dal.followup_dal import FollowUpDAL  # noqa: E402
from dal.intervention_dal import InterventionDAL  # noqa: E402
from models.followup import FollowUp  # noqa: E402
from models.intervention import Intervention  # noqa: E402
from services.report_generator import ReportGenerator  # noqa: E402
from services.trend_analysis_service import TrendAnalysisService  # noqa: E402
from utils.behavior_analysis import (  # noqa: E402
    DOMINANCE_RATIO,
    MIN_PATTERN_COUNT,
    classify_pattern,
    count_behaviors,
    growth_direction,
)

observation_dal = ObservationDAL()
report_gen = ReportGenerator()
trend_service = TrendAnalysisService()

observations = observation_dal.get_by_student_profile(profile_id)

# ============================================================
print("=" * 76)
print("بخش A: قوت/ضعف بر پایهٔ «نوع رفتار» (نه شدت)")
print("=" * 76)

report = report_gen.generate_student_report(profile_id)
check("A", "تولید گزارش پرونده بدون خطا انجام شد", bool(report))

strength_names = [s['competency'] for s in report['strengths']]
weakness_names = [w['competency'] for w in report['weaknesses']]

check("A", "رفتار منفی با شدت بالا «نقطه قوت» شمرده نمی‌شود",
      'شایستگی الف' not in strength_names and 'شایستگی الف' in weakness_names,
      f"strengths={strength_names} weaknesses={weakness_names}")
check("A", "رفتار مثبت با شدت پایین «نقطه ضعف» شمرده نمی‌شود",
      'شایستگی ب' in strength_names and 'شایستگی ب' not in weakness_names,
      f"strengths={strength_names} weaknesses={weakness_names}")
check("A", "مشاهدهٔ منفرد (منفی یا مثبت) نتیجه‌گیری نمی‌سازد",
      'شایستگی ج' not in strength_names and 'شایستگی ج' not in weakness_names,
      f"ج در strengths={strength_names} / weaknesses={weakness_names}")
check("A", "رفتارهای خنثی به‌تنهایی قوت/ضعف شمرده نمی‌شوند",
      'شایستگی د' not in strength_names and 'شایستگی د' not in weakness_names)
check("A", "شدت فقط به‌عنوان «اطلاعات تکمیلی» همراه خروجی است",
      all(s.get('severity_is_auxiliary') for s in report['strengths'] + report['weaknesses'])
      and all('avg_severity' in s for s in report['strengths'] + report['weaknesses']))

# ============================================================
print()
print("=" * 76)
print("بخش B: روند = ترکیب رفتارها، نه تعداد مشاهدات")
print("=" * 76)


def _period(label, positive, negative, neutral=0):
    return {'label': label, 'positive': positive, 'negative': negative,
            'neutral': neutral, 'total': positive + negative + neutral}


# کاهش شدید تعداد مشاهدات، ولی ترکیب (نسبت) ثابت
stable = growth_direction([_period('ماه ۱', 6, 4), _period('ماه ۲', 3, 2)])
check("B", "کاهش تعداد مشاهدات به‌تنهایی «بهبود» تفسیر نمی‌شود",
      stable['status'] == 'stable', stable['status'])

improving = growth_direction([_period('ماه ۱', 2, 8), _period('ماه ۲', 8, 2)])
check("B", "افزایش سهم رفتار مثبت «بهبود» شناسایی می‌شود",
      improving['status'] == 'improving', improving['status'])

declining = growth_direction([_period('ماه ۱', 8, 2), _period('ماه ۲', 2, 8)])
check("B", "افزایش سهم رفتار منفی «نیاز به توجه» شناسایی می‌شود",
      declining['status'] == 'declining', declining['status'])

note = stable['volume_note'] + improving['volume_note']
check("B", "یادداشت «حجم ثبت ≠ شاخص رشد» در خروجی روند هست",
      ('شاخص رشد نیست' in note or 'بهبود رفتار نیست' in note or
       'شاخص پیشرفت یا پسرفت نیست' in note), note[:120])

# ============================================================
print()
print("=" * 76)
print("بخش C: تفکیک مشاهده / غربالگری / تفسیر حرفه‌ای")
print("=" * 76)

layers = report.get('information_layers') or {}
check("C", "سه لایهٔ اطلاعاتی جدا از هم در گزارش وجود دارد",
      all(k in layers for k in ('observation', 'screening', 'interpretation'))
      and 'زنجیره' in layers.get('chain_note', '') or
      ('مشاهدهٔ رفتاری' in layers.get('chain_note', '') and
       'غربالگری' in layers.get('chain_note', '') and
       'تفسیر حرفه‌ای' in layers.get('chain_note', '')),
      str(list(layers.keys())))
scr_note = (layers.get('screening', {}).get('note', '') or '')
check("C", "یادداشت لایهٔ غربالگری صریحاً می‌گوید «تشخیص نیست»",
      'تشخیص' in scr_note and ('نیست' in scr_note))
interp_note = (layers.get('interpretation', {}).get('note', '') or '')
check("C", "یادداشت تفسیر حرفه‌ای جای تشخیص بالینی را رد می‌کند",
      'تشخیص' in interp_note)

# ============================================================
print()
print("=" * 76)
print("بخش D: زمینهٔ خانوادگی = اطلاعات زمینه‌ای")
print("=" * 76)

family = report.get('family_background') or {}
check("D", "یادداشت «زمینه‌ای، نه قضاوت» در گزارش خانواده هست",
      'زمینه' in family.get('note', '') and 'قضاوت' in family.get('note', ''))
check("D", "ساختار زمینهٔ خانوادگی و گفت‌وگوها آماده است",
      isinstance(family.get('contexts'), list)
      and isinstance(family.get('interviews'), list))

# ============================================================
print()
print("=" * 76)
print("بخش E: گزارش رشدمحور و اثربخشی مداخلات")
print("=" * 76)

summary = report['summary']
check("E", "جمع‌بندی سالانه هر پنج بخش را دارد و تشخیص را رد می‌کند",
      all(k in summary for k in ('۱) توانمندی', '۲) زمینه‌های نیازمند توجه',
                                 '۳) ترکیب رفتارهای ثبت‌شده', '۴) اقدامات و نتایج',
                                 '۵) روند تغییر رفتار'))
      and 'تشخیص روان‌شناختی' in summary
      and 'مقایسه فقط با خود دانش‌آموز' in summary, summary[:80])
check("E", "گزارش هم توانمندی و هم زمینهٔ نیازمند توجه دارد (تعادل)",
      bool(report['strengths']) and bool(report['weaknesses']),
      f"{len(report['strengths'])}/{len(report['weaknesses'])}")

# مداخلهٔ بدون پیگیری
intervention_dal = InterventionDAL()
followup_dal = FollowUpDAL()
inter = Intervention()
inter.student_profile_id = profile_id
inter.staff_id = staff_id
inter.type = 'individual_talk'
inter.date = '1404/07/01'
inter.description = 'گفت‌وگوی هدفمند دربارهٔ تکالیف'
inter.goal = 'افزایش پیگیری تکالیف'
inter.status = Intervention.STATUS_DONE
created_inter = intervention_dal.create(inter)

inter2 = Intervention()
inter2.student_profile_id = profile_id
inter2.staff_id = staff_id
inter2.type = 'encouragement'
inter2.date = '1404/07/02'
inter2.description = 'تشویق رفتار مثبت'
inter2.goal = 'تقویت رفتار مثبت'
inter2.status = Intervention.STATUS_DONE
created_inter2 = intervention_dal.create(inter2)

follow = FollowUp()
follow.intervention_id = created_inter2.id
follow.staff_id = staff_id
follow.date = '1404/07/20'
follow.method = 'مشاهده در کلاس'
follow.status = FollowUp.STATUS_DONE if hasattr(FollowUp, 'STATUS_DONE') else 'done'
follow.result_type = FollowUp.RESULT_IMPROVED
follow.result_description = 'رفتار مثبت تکرار شد'
followup_dal.create(follow)

report2 = report_gen.generate_student_report(profile_id)
eff = report2.get('intervention_effectiveness') or {}
items = {item['intervention_id']: item for item in eff.get('items', [])}
check("E", "مداخلهٔ بدون پیگیری «قابل ارزیابی نیست» علامت می‌خورد",
      created_inter.id in items and items[created_inter.id]['outcome_known'] is False
      and 'ثبت نشده' in items[created_inter.id]['outcome'],
      str(items.get(created_inter.id, {}).get('outcome')))
check("E", "نتیجهٔ پیگیری به مداخله متصل و گزارش می‌شود",
      created_inter2.id in items and items[created_inter2.id]['outcome_known']
      and items[created_inter2.id]['followups'][0]['result_type'] == FollowUp.RESULT_IMPROVED,
      str(items.get(created_inter2.id, {}).get('outcome')))

# ============================================================
print()
print("=" * 76)
print("بخش F: لحن محتاطانه و ردیابی‌پذیری پیشنهادها")
print("=" * 76)

recs = report2.get('recommendations', {})
all_recs = recs.get('teacher', []) + recs.get('parents', []) + recs.get('counselor', [])
joined = " ".join(all_recs)
check("F", "پیشنهادهای رفتارمحور به شناسهٔ مشاهدات ارجاع می‌دهند",
      'شناسهٔ مشاهدات' in joined)
forbidden = ('اختلال', 'تشخیص قطعی', 'برچسب‌گذاری', 'بیماری روان')
check("F", "لحن پیشنهادها تشخیصی/برچسب‌زننده نیست",
      not any(word in joined for word in forbidden),
      str([w for w in forbidden if w in joined]))
rules_src = read('models/recommendation_rules.py')
check("F", "عناوین قوانین به «الگوی تکرارشونده» تغییر کرده و ردیابی دارد",
      'الگوی تکرارشوندهٔ رفتار منفی' in rules_src
      and 'behavior_based' in rules_src
      and 'avg_severity' not in rules_src)

# ============================================================
print()
print("=" * 76)
print("بخش G: لایهٔ داده و روایت چندساله")
print("=" * 76)

strong = observation_dal.get_strong_competencies_for_student(profile_id)
weak = observation_dal.get_weak_competencies_for_student(profile_id)
check("G", "DAL توانمندی را از رفتار مثبت تکرارشونده می‌سازد",
      any(item['competency_id'] == comp_ids[1] for item in strong)
      and all(item['pattern'] == 'strength' for item in strong),
      str([(i['competency_id'], i['pattern']) for i in strong]))
check("G", "DAL زمینهٔ نیازمند توجه را از رفتار منفی تکرارشونده می‌سازد",
      any(item['competency_id'] == comp_ids[0] for item in weak)
      and all(item['pattern'] == 'needs_attention' for item in weak),
      str([(i['competency_id'], i['pattern']) for i in weak]))

trend = trend_service.analyze_student_trend(profile_id)
top = trend.get('top_competencies') or []
check("G", "زمینه‌های پرتکرار روند، برچسب الگو دارند (نه فقط تعداد)",
      bool(top) and all(len(item) >= 3 for item in top), str(top[:2]))

narrative = report_gen.generate_growth_narrative(student_id)
check("G", "روایت چندسالهٔ رشد ساخته می‌شود و غیرتشخیصی است",
      narrative.get('has_data') and 'تشخیص' in narrative.get('narrative', '')
      and 'مقایسه با دانش‌آموزان دیگر' in narrative.get('narrative', ''),
      narrative.get('narrative', '')[:100])

# ============================================================
print()
print("=" * 76)
print("بخش H: نگهبان‌های ساختاری")
print("=" * 76)

check("H", "آستانه‌های الگو (حداقل ۲ تکرار، غلبهٔ ۶۰٪) در یک ماژول مشترک است",
      MIN_PATTERN_COUNT == 2 and abs(DOMINANCE_RATIO - 0.6) < 1e-9)
check("H", "منطق قدیمی «قوت/ضعف بر پایهٔ میانگین شدت» باقی نمانده",
      'avg >= 3.5' not in read('services/report_generator.py')
      and 'avg <= 2.0' not in read('services/report_generator.py')
      and 'avg_severity >= 3.5' not in read('dal/observation_dal.py'))

counts = count_behaviors(observations)
check("H", "شمارش رفتارها با دادهٔ آزمایشی می‌خواند",
      counts == {'positive': 4, 'negative': 4, 'neutral': 2, 'total': 10},
      str(counts))
check("H", "رفتار خنثی هیچ‌گاه به‌تنهایی الگو نمی‌سازد",
      classify_pattern(0, 0, 2, 2) == 'insufficient')

# ============================================================
try:
    dbc.DatabaseConnection._instance = None
    dbc.DatabaseConnection._connection = None
except Exception:
    pass

print()
print("=" * 76)
print(f"نتیجهٔ دور یازدهم:  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های دور یازدهم سبز است (تحلیل رفتارمحور و رشدمحور).")
