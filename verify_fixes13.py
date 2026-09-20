"""
بررسی‌های دور سیزدهم: دو ایراد محتوایی باقی‌مانده از داوری مدیر پروژه

  A) روند رشد با لحاظ بازه‌های میانی (نه فقط ابتدا/انتها) ...... ۱۰ بررسی
  B) همان منطق در سرویس روند و نمایش مسیر در صفحه‌ها ............ ۴ بررسی
  C) گزارش چندساله: از «فهرست سال‌ها» به «روایت منسجم مسیر رشد» .. ۱۴ بررسی
  D) نگهبان‌های بدون پس‌روندگی ................................... ۳ بررسی

جمع: ۳۲ بررسی

هر بررسی روی یک دیتابیس موقت اجرا می‌شود و به داده‌های کاربر دست نمی‌زند.
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


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ============================================================
# آماده‌سازی دیتابیس موقت
# ============================================================
TMP = tempfile.mkdtemp(prefix="round13_verify_")
TEST_DB = os.path.join(TMP, "partow.db")

import config.settings as settings  # noqa: E402
import database.connection as dbc  # noqa: E402

settings.DB_PATH = TEST_DB
dbc.DB_PATH = TEST_DB
dbc.DatabaseConnection._instance = None
dbc.DatabaseConnection._connection = None
dbc.DatabaseConnection._initialized = False
dbc.DatabaseConnection._current_user_id = None

with contextlib.redirect_stdout(io.StringIO()):
    db = dbc.DatabaseConnection()
    conn = db.get_connection(user_id=1)

from dal.competency_dal import CompetencyDAL  # noqa: E402
from dal.followup_dal import FollowUpDAL  # noqa: E402
from dal.intervention_dal import InterventionDAL  # noqa: E402
from dal.observation_dal import ObservationDAL  # noqa: E402
from dal.student_academic_profile_dal import StudentAcademicProfileDAL  # noqa: E402
from dal.student_dal import StudentDAL  # noqa: E402
from models.followup import FollowUp  # noqa: E402
from models.intervention import Intervention  # noqa: E402
from models.observation import Observation  # noqa: E402
from models.student import Student  # noqa: E402
from models.student_academic_profile import StudentAcademicProfile  # noqa: E402
from services.report_generator import ReportGenerator  # noqa: E402
from services.trend_analysis_service import TrendAnalysisService  # noqa: E402
from utils.behavior_analysis import (  # noqa: E402
    DOMINANCE_RATIO,
    MEANINGFUL_SHARE_CHANGE,
    MIN_PATTERN_COUNT,
    classify_pattern,
    growth_direction,
)

report_gen = ReportGenerator()
trend_service = TrendAnalysisService()


def _period(label, positive, negative, neutral=0):
    return {'label': label, 'positive': positive, 'negative': negative,
            'neutral': neutral, 'total': positive + negative + neutral}


# ============================================================
print("=" * 76)
print("بخش A: روند رشد با لحاظ بازه‌های میانی (نه فقط ابتدا/انتها)")
print("=" * 76)

# A1) رفتار دوبازه‌ای مثل قبل
stable2 = growth_direction([_period('ماه ۱', 6, 4), _period('ماه ۲', 3, 2)])
improving2 = growth_direction([_period('ماه ۱', 2, 8), _period('ماه ۲', 8, 2)])
declining2 = growth_direction([_period('ماه ۱', 8, 2), _period('ماه ۲', 2, 8)])
check("A", "رفتار دوبازه‌ای حفظ شده (ثبات/بهبود/افت)",
      stable2['status'] == 'stable' and improving2['status'] == 'improving'
      and declining2['status'] == 'declining',
      f"{stable2['status']}/{improving2['status']}/{declining2['status']}")

# A2) مثال مدیر پروژه: مهر ۲/۸ ← آبان ۶/۴ ← آذر ۱/۹
pm = growth_direction([_period('مهر', 2, 8), _period('آبان', 6, 4),
                       _period('آذر', 1, 9)])
check("A", "مثال مدیر پروژه (مهر/آبان/آذر): برگشت جهت در بازهٔ میانی → روند غیرقطعی",
      pm['status'] == 'mixed' and pm['reason'] == 'reversal'
      and pm['turning_points'] == ['آبان']
      and [s['status'] for s in pm['steps']] == ['improving', 'declining']
      and 'آبان' in pm['message'],
      f"{pm['status']}/{pm['reason']} turning={pm['turning_points']}")

# A3) بهبود تدریجی: هر گام زیر آستانه، ولی همه هم‌جهت → «بهبود» نه «ثابت»
gradual = growth_direction([_period('۱', 30, 70), _period('۲', 38, 62),
                            _period('۳', 46, 54), _period('۴', 54, 46),
                            _period('۵', 62, 38)])
check("A", "بهبود تدریجی (گام‌های کوچکِ هم‌جهت) دیگر «ثابت» گزارش نمی‌شود",
      gradual['status'] == 'improving' and 'تدریجی' in gradual['message'],
      f"{gradual['status']} | {gradual['message'][:70]}")

# A4) جهش میانی و بازگشت به وضعیت اولیه → غیرقطعی، نه «بهبود» و نه «ثابت»
returned = growth_direction([_period('۱', 30, 70), _period('۲', 45, 55),
                             _period('۳', 37, 63), _period('۴', 29, 71)])
check("A", "تغییر معنادار میانی که برگشته، «غیرقطعی» است (نه بهبود/ثابت)",
      returned['status'] == 'mixed' and returned['reason'] == 'returned'
      and returned['overall_status'] == 'stable',
      f"{returned['status']}/{returned['reason']} overall={returned['overall_status']}")

# A5) برآیند کلی بهبود، ولی یک گام معنادار مخالف در میانه → غیرقطعی
counter = growth_direction([_period('۱', 30, 70), _period('۲', 60, 40),
                            _period('۳', 48, 52)])
check("A", "برآیند بهبود + گام معنادار مخالف در میانه → غیرقطعی (نه برآیند ابتدا/انتها)",
      counter['status'] == 'mixed' and counter['overall_status'] == 'improving',
      f"{counter['status']} overall={counter['overall_status']}")

# A6) نوسان جزئی زیر آستانه، جهت را نمی‌شکند ولی گزارش می‌شود
wobble = growth_direction([_period('۱', 30, 70), _period('۲', 60, 40),
                           _period('۳', 54, 46)])
check("A", "نوسان جزئی (زیر آستانه) جهت را نمی‌شکند اما در پیام ذکر می‌شود",
      wobble['status'] == 'improving' and 'نوسان جزئی' in wobble['message'],
      f"{wobble['status']} | {wobble['message'][-90:]}")

# A7) تعداد مشاهدات هیچ نقشی در تصمیم ندارد (فقط حجم پایش)
same_share = growth_direction([_period('۱', 6, 4), _period('۲', 60, 40),
                               _period('۳', 3, 2)])
scaled = growth_direction([_period('مهر', 20, 80), _period('آبان', 6, 4),
                           _period('آذر', 100, 900)])
check("A", "تعداد مشاهدات در تصمیم روند نقشی ندارد (سهم ثابت → ثبات؛ مقیاس‌بندی → همان نتیجه)",
      same_share['status'] == 'stable' and scaled['status'] == pm['status']
      and ('شاخص رشد نیست' in same_share['volume_note']
           or 'بهبود رفتار نیست' in same_share['volume_note']
           or 'بهبود یا بدتر شدن رفتار' in same_share['volume_note']),
      f"{same_share['status']}/{scaled['status']}")

# A8) خروجی مسیر: همهٔ بازه‌ها (از جمله میانی) در path/path_text هستند
check("A", "مسیر گام‌به‌گام (path/path_text/steps/overall_status) در خروجی هست و بازهٔ میانی را دارد",
      [p['label'] for p in pm['path']] == ['مهر', 'آبان', 'آذر']
      and 'آبان' in pm['path_text'] and 'مهر' in pm['path_text'] and 'آذر' in pm['path_text']
      and 'overall_status' in pm and len(pm['steps']) == 2,
      pm['path_text'][:90])

# A9) یادداشت احتیاطی برای بازه‌های کم‌مشاهده، بدون اثر بر تصمیم
tiny = growth_direction([_period('۱', 1, 0), _period('۲', 0, 1), _period('۳', 1, 0)])
big = growth_direction([_period('۱', 10, 0), _period('۲', 0, 10), _period('۳', 10, 0)])
check("A", "بازهٔ کم‌مشاهده فقط یادداشت احتیاطی می‌گیرد؛ تصمیم عوض نمی‌شود",
      tiny['status'] == big['status'] and tiny['caution_notes']
      and not big['caution_notes'],
      f"{tiny['status']}/{big['status']} notes={len(tiny['caution_notes'])}")

# A10) کمتر از دو بازه → دادهٔ ناکافی
few = growth_direction([_period('۱', 5, 5)])
check("A", "کمتر از دو بازه → دادهٔ ناکافی (با کلیدهای کامل خروجی)",
      few['status'] == 'insufficient' and few['steps'] == [] and few['path'] == []
      and 'path_text' in few and 'overall_status' in few, few['status'])

# ============================================================
print()
print("=" * 76)
print("بخش B: همان منطق در سرویس روند و نمایش مسیر در صفحه‌ها")
print("=" * 76)

trend_src = read('services/trend_analysis_service.py')
_overall_body = trend_src.split('def _analyze_overall_trend')[1]
check("B", "سرویس روند دیگر فقط trend_data[0] را با trend_data[-1] مقایسه نمی‌کند",
      'first = trend_data[0]' not in trend_src and 'last = trend_data[-1]' not in trend_src
      and "positive_percent'] + 10" not in trend_src
      and 'growth_direction(' in _overall_body[:1500],
      "")

overall = trend_service._analyze_overall_trend([
    {'label': 'مهر', 'positive': 2, 'negative': 8, 'neutral': 0, 'total': 10,
     'positive_percent': 20.0},
    {'label': 'آبان', 'positive': 6, 'negative': 4, 'neutral': 0, 'total': 10,
     'positive_percent': 60.0},
    {'label': 'آذر', 'positive': 1, 'negative': 9, 'neutral': 0, 'total': 10,
     'positive_percent': 10.0},
])
check("B", "برچسب روند صفحهٔ پرونده با بازهٔ میانی «غیرقطعی» می‌شود (قبلاً «ثابت» بود)",
      overall['status'] == 'mixed' and 'آبان' in overall.get('path_text', '')
      and overall.get('direction', {}).get('reason') == 'reversal',
      f"{overall['status']} | {overall.get('path_text', '')[:60]}")

views_ok = (
    'path_text' in read('views/pages/student_profile_page.py')
    and 'path_text' in read('views/pages/analysis_page.py')
    and 'path_text' in read('views/pages/reports_page.py')
)
check("B", "صفحه‌های پرونده، تحلیل و گزارش‌ها مسیر تغییر بین بازه‌ها را نشان می‌دهند",
      views_ok, "")

rg_src = read('services/report_generator.py')
check("B", "PDF و جمع‌بندی سالانه هم «مسیر تغییر بین بازه‌ها» را دارند",
      rg_src.count('مسیر تغییر بین بازه‌ها') >= 2, str(rg_src.count('مسیر تغییر بین بازه‌ها')))

# ============================================================
print()
print("=" * 76)
print("بخش C: گزارش چندساله — از «فهرست سال‌ها» به «روایت منسجم مسیر رشد»")
print("=" * 76)

with contextlib.redirect_stdout(io.StringIO()):
    st = Student()
    st.first_name = "روایت"
    st.last_name = "سیزدهم"
    st.national_code = "1313131313"
    st.is_active = 1
    student_id = StudentDAL().create(st).id

    for title in ('1403-1404', '1404-1405'):
        conn.execute(
            "INSERT INTO academic_years (title, is_active, start_date) VALUES (?, 0, ?)",
            (title, title[:4] + '/07/01'))
    conn.commit()
    year_ids = [r[0] for r in conn.execute(
        "SELECT id FROM academic_years WHERE is_deleted = 0 ORDER BY start_date, id"
    ).fetchall()][:3]

    comps = CompetencyDAL().get_all()
    c_need, c_strength, c_flip, c_resolved, c_new = [c.id for c in comps[:5]]
    titles = {c.id: c.title for c in comps[:5]}

    profile_ids = []
    for yid, grade in zip(year_ids, (1, 2, 3)):
        p = StudentAcademicProfile()
        p.student_id = student_id
        p.academic_year_id = yid
        p.grade = grade
        p.class_name = "الف"
        profile_ids.append(StudentAcademicProfileDAL().create(p).id)

    obs_dal, int_dal, fu_dal = ObservationDAL(), InterventionDAL(), FollowUpDAL()

    def _add_obs(pid, comp_id, btype, date):
        o = Observation()
        o.student_profile_id = pid
        o.staff_id = 1
        o.competency_id = comp_id
        o.observation_date = date
        o.description = "شرح آزمایشی"
        o.behavior = "رفتار ثبت‌شدهٔ آزمایشی"
        o.behavior_type = btype
        o.severity = 2
        return obs_dal.create(o).id

    def _add_int(pid, obs_id, itype, date, result=None):
        i = Intervention()
        i.student_profile_id = pid
        i.staff_id = 1
        i.observation_id = obs_id
        i.type = itype
        i.date = date
        i.description = "مداخلهٔ آزمایشی"
        i.goal = "هدف آزمایشی"
        i.status = "done"
        iid = int_dal.create(i).id
        if result:
            f = FollowUp()
            f.intervention_id = iid
            f.staff_id = 1
            f.date = date
            f.method = "گفتگو"
            f.status = "done"
            f.result_type = result
            f.result_description = "نتیجهٔ آزمایشی"
            f.description = "پیگیری آزمایشی"
            fu_dal.create(f)
        return iid

    # سال ۱: نیاز ماندگار (منفی×۳)، توانمندی ماندگار (مثبت×۲)، flip=مثبت×۲، resolved=منفی×۲
    o1 = _add_obs(profile_ids[0], c_need, "منفی", "1403/08/01")
    _add_obs(profile_ids[0], c_need, "منفی", "1403/09/01")
    _add_obs(profile_ids[0], c_need, "منفی", "1403/10/01")
    _add_obs(profile_ids[0], c_strength, "مثبت", "1403/08/02")
    _add_obs(profile_ids[0], c_strength, "مثبت", "1403/09/02")
    _add_obs(profile_ids[0], c_flip, "مثبت", "1403/08/03")
    _add_obs(profile_ids[0], c_flip, "مثبت", "1403/09/03")
    o1r = _add_obs(profile_ids[0], c_resolved, "منفی", "1403/08/04")
    _add_obs(profile_ids[0], c_resolved, "منفی", "1403/09/04")
    _add_int(profile_ids[0], o1, "individual_talk", "1403/09/05", "no_change")
    _add_int(profile_ids[0], o1r, "parent_call", "1403/09/06", "improved")
    _add_int(profile_ids[0], o1, "warning", "1403/10/06")  # بدون پیگیری
    # سال ۲: نیاز و توانمندی ادامه دارند؛ flip ترکیبی؛ resolved فقط یک مثبت
    o2 = _add_obs(profile_ids[1], c_need, "منفی", "1404/08/01")
    _add_obs(profile_ids[1], c_need, "منفی", "1404/09/01")
    _add_obs(profile_ids[1], c_strength, "مثبت", "1404/08/02")
    _add_obs(profile_ids[1], c_strength, "مثبت", "1404/09/02")
    _add_obs(profile_ids[1], c_strength, "مثبت", "1404/10/02")
    _add_obs(profile_ids[1], c_flip, "مثبت", "1404/08/03")
    _add_obs(profile_ids[1], c_flip, "منفی", "1404/09/03")
    _add_obs(profile_ids[1], c_resolved, "مثبت", "1404/08/04")
    _add_int(profile_ids[1], o2, "individual_talk", "1404/09/05", "improved")
    _add_int(profile_ids[1], o2, "responsibility", "1404/10/05", "improved")
    # سال ۳: نیاز و توانمندی ادامه دارند؛ flip → منفی (افت)؛ new → منفی (تازه)
    o3 = _add_obs(profile_ids[2], c_need, "منفی", "1405/08/01")
    _add_obs(profile_ids[2], c_need, "منفی", "1405/09/01")
    _add_obs(profile_ids[2], c_strength, "مثبت", "1405/08/02")
    _add_obs(profile_ids[2], c_strength, "مثبت", "1405/09/02")
    _add_obs(profile_ids[2], c_strength, "مثبت", "1405/10/02")
    _add_obs(profile_ids[2], c_strength, "مثبت", "1405/11/02")
    _add_obs(profile_ids[2], c_flip, "منفی", "1405/08/03")
    _add_obs(profile_ids[2], c_flip, "منفی", "1405/09/03")
    _add_obs(profile_ids[2], c_new, "منفی", "1405/08/05")
    _add_obs(profile_ids[2], c_new, "منفی", "1405/09/05")
    _add_int(profile_ids[2], o3, "responsibility", "1405/09/05", "improved")
    _add_int(profile_ids[2], o3, "individual_talk", "1405/10/05", "needs_more")

narrative = report_gen.generate_growth_narrative(student_id)
synth = narrative.get('synthesis') or {}
section_keys = [s['key'] for s in synth.get('sections', [])]

check("C", "روایت در پنج بخش منسجم + یادداشت‌ها ساخته می‌شود (نه فقط فهرست سال‌ها)",
      section_keys == ['trajectory', 'persistent', 'changes', 'interventions',
                       'conclusion', 'caveats'],
      str(section_keys))

traj = synth.get('trajectory') or {}
per_year = traj.get('per_year') or []
check("C", "مسیر سال‌به‌سال با گام بین سال‌ها ساخته می‌شود و سال میانی نادیده گرفته نمی‌شود",
      len(per_year) == 3 and per_year[0]['step_label'] is None
      and per_year[1]['step_status'] == 'improving'
      and per_year[2]['step_status'] == 'declining'
      and traj.get('status') == 'mixed' and traj.get('turning_points') == ['1404-1405'],
      f"{[p['step_status'] for p in per_year]} status={traj.get('status')}")

needs = {p['competency']: p for p in synth.get('persistent_needs', [])}
strengths = {p['competency']: p for p in synth.get('persistent_strengths', [])}
check("C", "الگوهای ادامه‌دار با «آیا در آخرین سال هم هست؟» مشخص می‌شوند",
      titles[c_need] in needs and needs[titles[c_need]]['count'] == 3
      and needs[titles[c_need]]['still_present'] is True
      and titles[c_strength] in strengths
      and strengths[titles[c_strength]]['still_present'] is True,
      f"needs={list(needs)} strengths={list(strengths)}")

changes = {c['competency']: c['change'] for c in synth.get('changed_areas', [])}
check("C", "زمینه‌های تغییریافته با «جهت تغییر» دسته‌بندی می‌شوند (افت / دیگر الگو نیست / تازه‌پدیدآمده)",
      changes.get(titles[c_flip]) == 'strength_to_need'
      and changes.get(titles[c_resolved]) == 'need_resolved'
      and changes.get(titles[c_new]) == 'need_emerged'
      and all('change_label' in c and 'note' in c for c in synth['changed_areas']),
      str(changes))

resolved_entry = next((c for c in synth['changed_areas']
                       if c['competency'] == titles[c_resolved]), {})
check("C", "نبودِ الگو در سال آخر «رفع شدن» قطعی تلقی نمی‌شود (احتیاط + وضعیت ثبت در سال آخر)",
      'مشاهدهٔ بیشتر' in resolved_entry.get('note', '')
      and bool(resolved_entry.get('latest_status')),
      resolved_entry.get('latest_status', '')[:60])

eff = {b['type']: b for b in synth.get('effective_interventions', [])}
first_type = (synth.get('effective_interventions') or [{}])[0].get('type')
check("C", "اثربخشی مداخلات به تفکیک «نوع مداخله» در طول سال‌ها از پیگیری‌های واقعی ساخته می‌شود",
      first_type == 'سپردن مسئولیت'
      and eff['سپردن مسئولیت']['verdict'] == 'improved'
      and eff['سپردن مسئولیت']['improved'] == 2 and eff['سپردن مسئولیت']['with_followup'] == 2
      and sorted(eff['سپردن مسئولیت']['years']) == ['1404-1405', '1405-1406'],
      str({k: (v['verdict'], v['improved'], v['with_followup']) for k, v in eff.items()}))

check("C", "«۱ از ۳» مؤثرتر شمرده نمی‌شود (ترکیبی) و مداخلهٔ بدون پیگیری «قابل ارزیابی نیست»",
      eff['گفتگوی فردی']['verdict'] == 'partial' and eff['گفتگوی فردی']['with_followup'] == 3
      and eff['تذکر شفاهی']['verdict'] == 'not_evaluable'
      and eff['تذکر شفاهی']['no_followup'] == 1,
      f"{eff['گفتگوی فردی']['verdict']}/{eff['تذکر شفاهی']['verdict']}")

area = synth.get('area_interventions', {}).get(titles[c_need], {})
check("C", "مداخلات به «زمینهٔ» مشاهدهٔ مبنا پیوند می‌خورند (مداخله ← مشاهده ← شایستگی)",
      set(area) == {'گفتگوی فردی', 'سپردن مسئولیت', 'تذکر شفاهی'}
      and area['سپردن مسئولیت']['improved'] == 2
      and titles[c_need] in eff['سپردن مسئولیت']['competencies'],
      str(area))

pri_kinds = [p['kind'] for p in synth.get('priorities', [])]
pri_need = next((p for p in synth.get('priorities', []) if p['kind'] == 'persistent_need'), {})
check("C", "اولویت‌های ادامهٔ مسیر: نیاز ادامه‌دار + مداخلات مؤثر همان زمینه، نیاز تازه، افت، تکیه‌گاه‌ها",
      pri_kinds == ['persistent_need', 'reversed', 'new_need', 'build_on']
      and 'سپردن مسئولیت' in pri_need.get('text', ''),
      str(pri_kinds))

conclusion = next((s for s in synth['sections'] if s['key'] == 'conclusion'), {})
conclusion_text = " ".join(conclusion.get('lines', []))
check("C", "جمع‌بندی، مسیر کلی را به‌صورت روایت می‌گوید (بهبود/افت/ادامه‌دار) نه فهرست سال‌ها",
      'مسیر رشد از سال 1403-1404' in conclusion_text
      and 'نیازهای ادامه‌دار' in conclusion_text
      and 'یکنواخت نبوده' in conclusion_text
      and 'مسیر کلی رشد' in synth.get('text', ''),
      conclusion_text[:100])

lines = report_gen.growth_narrative_lines(narrative)
headings = [t for k, t in lines if k == 'heading']
check("C", "رندر مشترک روایت برای همهٔ خروجی‌ها (گزارش معمول، PDF، Excel) وجود دارد",
      len(headings) == 7 and 'growth_narrative_lines' in read('views/pages/reports_page.py')
      and rg_src.count('self.growth_narrative_lines(') >= 2,
      str(headings[:3]))

full_report = report_gen.generate_student_report(profile_ids[2])
growth = full_report.get('growth_narrative') or {}
check("C", "گزارش معمول برنامه همان روایت جامع (با همهٔ بخش‌ها) را دارد، نه فقط PDF",
      growth.get('has_data') is True
      and [s['key'] for s in growth.get('synthesis', {}).get('sections', [])] == section_keys,
      str(list(growth.keys()))[:80])

xlsx_path = os.path.join(TMP, "r13.xlsx")
pdf_path = os.path.join(TMP, "r13.pdf")
ok_xlsx, _ = report_gen.export_to_excel(profile_ids[2], xlsx_path)
ok_pdf, pdf_msg = report_gen.export_to_pdf(profile_ids[2], pdf_path)
sheet_ok = False
if ok_xlsx:
    from openpyxl import load_workbook
    wb = load_workbook(xlsx_path)
    if 'مسیر رشد چندساله' in wb.sheetnames:
        cells = [str(c.value) for row in wb['مسیر رشد چندساله'].iter_rows() for c in row if c.value]
        sheet_ok = any('۴) مداخلات' in v for v in cells) and any('۵) جمع‌بندی' in v for v in cells)
check("C", "خروجی Excel برگهٔ «مسیر رشد چندساله» و PDF بخش چندساله را با موفقیت می‌سازند",
      ok_xlsx and sheet_ok and ok_pdf and os.path.getsize(pdf_path) > 1000,
      f"xlsx={ok_xlsx} sheet={sheet_ok} pdf={ok_pdf} {pdf_msg[:40]}")

all_text = narrative.get('narrative', '') + " " + " ".join(
    t for _, t in lines)
check("C", "روایت غیرتشخیصی است و فقط دانش‌آموز را با خودش مقایسه می‌کند (بدون مقایسه با دیگران)",
      'تشخیص' in narrative.get('narrative', '')
      and 'مقایسه با دانش‌آموزان دیگر' in narrative.get('narrative', '')
      and 'میانگین کلاس' not in all_text and 'رتبه' not in all_text
      and any('دانش‌آموزان دیگر' in c for c in synth.get('caveats', [])),
      "")

# دانش‌آموز تک‌سال و دانش‌آموز بدون پرونده نباید بشکنند
with contextlib.redirect_stdout(io.StringIO()):
    st1 = Student()
    st1.first_name = "تک"
    st1.last_name = "سال"
    st1.national_code = "1313131314"
    st1.is_active = 1
    single_id = StudentDAL().create(st1).id
    p1 = StudentAcademicProfile()
    p1.student_id = single_id
    p1.academic_year_id = year_ids[-1]
    p1.grade = 1
    p1.class_name = "ب"
    single_pid = StudentAcademicProfileDAL().create(p1).id
    _add_obs(single_pid, c_need, "منفی", "1405/08/01")
    _add_obs(single_pid, c_need, "منفی", "1405/09/01")
    st0 = Student()
    st0.first_name = "بدون"
    st0.last_name = "پرونده"
    st0.national_code = "1313131315"
    st0.is_active = 1
    none_id = StudentDAL().create(st0).id

single = report_gen.generate_growth_narrative(single_id)
none_n = report_gen.generate_growth_narrative(none_id)
single_changes = next((s for s in single['synthesis']['sections'] if s['key'] == 'changes'), {})
check("C", "دانش‌آموز تک‌سال و بدون پرونده بدون خطا و با پیام صادقانه گزارش می‌شوند",
      single['has_data'] is True and single['direction']['status'] == 'insufficient'
      and any('دو سال' in ln for ln in single_changes.get('lines', []))
      and none_n['has_data'] is False and none_n['years'] == []
      and report_gen.growth_narrative_lines(none_n) == [],
      f"{single['direction']['status']} / {none_n.get('has_data')}")

# ============================================================
print()
print("=" * 76)
print("بخش D: نگهبان‌های بدون پس‌روندگی")
print("=" * 76)

check("D", "آستانه‌های الگو و معناداری دست‌نخورده‌اند (۲ تکرار، غلبهٔ ۶۰٪، تغییر ۱۰ واحد)",
      MIN_PATTERN_COUNT == 2 and abs(DOMINANCE_RATIO - 0.6) < 1e-9
      and abs(MEANINGFUL_SHARE_CHANGE - 10.0) < 1e-9)
check("D", "رفتار خنثی به‌تنهایی الگو نمی‌سازد و یک مشاهدهٔ منفرد قوت/ضعف نمی‌سازد",
      classify_pattern(0, 0, 2, 2) == 'insufficient'
      and classify_pattern(1, 0, 0, 1) not in ('strength', 'needs_attention')
      and classify_pattern(0, 1, 0, 1) not in ('strength', 'needs_attention')
      and classify_pattern(2, 0, 0, 2) == 'strength'
      and classify_pattern(0, 2, 0, 2) == 'needs_attention')
check("D", "نسخهٔ دیتابیس همچنان ۹ است (بدون قابلیت جدید و بدون migration)",
      settings.DB_VERSION == 9, str(settings.DB_VERSION))

# ============================================================
print()
print("=" * 76)
print(f"نتیجهٔ دور سیزدهم:  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("موارد ناموفق:")
    for item in FAILURES:
        print(f"  - {item}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های دور سیزدهم سبز است (روند با بازه‌های میانی + روایت منسجم چندساله).")
