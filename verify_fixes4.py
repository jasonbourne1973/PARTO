#!/usr/bin/env python3
"""
راستی‌آزمایی دور چهارم بازرسی — ۳۶ بررسی

بخش‌ها:
  A) format_timestamp (مبدل شمسی مهر زمانی) ............. ۱۲ بررسی
  B) فیلتر معلم در ۹ کوئری تحلیلی داشبورد ............... ۱۶ بررسی
  C) اتصال سرتاسری سرویس داشبورد ........................ ۲ بررسی
  D) فوتر شمسیِ خروجی اکسل .............................. ۲ بررسی
  E) بدون پس‌روندگی (seed/تریگر/سلامت) .................. ۴ بررسی

اجرا:  python3 verify_fixes4.py
"""

import os
import re
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# منطقهٔ زمانی تهران تا نتیجهٔ تبدیل UTC قطعی باشد
os.environ['TZ'] = 'Asia/Tehran'
time.tzset()

import config.settings as settings
import database.connection as dbc

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


def _restore_main():
    """بازگرداندن مسیر دیتابیس اصلی و ریست تک‌نمونه‌ها"""
    dbc.DatabaseConnection._instance = None
    dbc._connection = None
    dbc._initialized = False


# ============================================================
# آماده‌سازی دیتابیس موقت
# ============================================================
TMP = tempfile.mkdtemp(prefix="round4_verify_")
TEST_DB = os.path.join(TMP, "partow.db")

_orig_settings_path = settings.DB_PATH
_orig_conn_path = dbc.DB_PATH
settings.DB_PATH = TEST_DB
dbc.DB_PATH = TEST_DB
_restore_main()

try:
    from dal.followup_dal import FollowUpDAL
    from dal.intervention_dal import InterventionDAL
    from dal.observation_dal import ObservationDAL
    from dal.staff_dal import StaffDAL
    from dal.student_dal import StudentDAL
    from utils.persian_date import format_timestamp

    conn_obj = dbc.DatabaseConnection()
    app_conn = conn_obj.get_connection()

    def q(sql, params=()):
        return app_conn.execute(sql, params).fetchall()

    def one(sql, params=()):
        return app_conn.execute(sql, params).fetchone()

    def insert_min(table, **kv):
        """درج با پرکردن خودکار ستون‌های NOT NULL بدون پیش‌فرض"""
        cols = {
            r[1]: r
            for r in app_conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, col in cols.items():
            if name in kv:
                continue
            notnull, dflt = col[3], col[4]
            if notnull and dflt is None and name != 'id':
                typ = (col[2] or '').upper()
                kv[name] = '' if 'TEXT' in typ or 'CHAR' in typ else 0
        keys = ', '.join(kv.keys())
        marks = ', '.join('?' for _ in kv)
        app_conn.execute(
            f"INSERT INTO {table} ({keys}) VALUES ({marks})", tuple(kv.values())
        )
        app_conn.commit()

    # ---------- دادهٔ آزمایشی ----------
    # سال تحصیلی فعال (در seed ساخته می‌شود)
    year_id = one("SELECT id FROM academic_years WHERE is_deleted=0")['id']

    insert_min('staff', full_name='معلم الف', role='teacher')
    insert_min('staff', full_name='معلم ب', role='teacher')
    staff_a = one("SELECT id FROM staff WHERE full_name='معلم الف'")['id']
    staff_b = one("SELECT id FROM staff WHERE full_name='معلم ب'")['id']

    def make_student(code):
        insert_min(
            'students', first_name='دانش', last_name=code,
            national_code=f'00{code}', is_active=1
        )
        sid = one("SELECT id FROM students WHERE last_name=?", (code,))['id']
        insert_min(
            'student_academic_profiles', student_id=sid,
            academic_year_id=year_id, grade=3, class_name='۳۱',
            status='active'
        )
        pid = one(
            "SELECT id FROM student_academic_profiles WHERE student_id=?", (sid,)
        )['id']
        return sid, pid

    s1, p1 = make_student('آ')   # متعلق به معلم الف، دارای مشاهده
    s2, p2 = make_student('ب')   # متعلق به معلم الف، بدون مشاهده
    s3, p3 = make_student('ج')   # متعلق به معلم ب،  بدون مشاهده

    for sid, st in ((s1, staff_a), (s2, staff_a), (s3, staff_b)):
        insert_min(
            'teacher_assignments', student_id=sid, staff_id=st,
            academic_year_id=year_id, grade=3, class_name='۳۱',
            is_active=1, assigned_date='1405/06/01'
        )

    comp_id = one("SELECT id FROM competencies LIMIT 1")['id']

    # ۳ مشاهده توسط الف، ۱ توسط ب
    for i, bt in enumerate(('مثبت', 'منفی', 'خنثی')):
        insert_min(
            'observations', student_profile_id=p1, staff_id=staff_a,
            competency_id=comp_id, behavior_type=bt, severity=2,
            observation_date='1405/06/2%d' % (i + 1), description='تست'
        )
    insert_min(
        'observations', student_profile_id=p1, staff_id=staff_b,
        competency_id=comp_id, behavior_type='مثبت', severity=1,
        observation_date='1405/06/25', description='تست'
    )

    # ۲ مداخلهٔ الف (یک انجام‌شده، یک برنامه‌ریزی)، ۱ لغوشدهٔ ب
    insert_min(
        'interventions', student_profile_id=p1, staff_id=staff_a,
        type='رفتاری', date='1405/06/10', status='completed',
        description='R4-IV1'
    )
    insert_min(
        'interventions', student_profile_id=p1, staff_id=staff_a,
        type='رفتاری', date='1405/06/12', status='planned',
        description='R4-IV2'
    )
    insert_min(
        'interventions', student_profile_id=p3, staff_id=staff_b,
        type='رفتاری', date='1405/06/11', status='cancelled',
        description='R4-IV3'
    )
    iv_a1 = one("SELECT id FROM interventions WHERE description='R4-IV1'")['id']
    iv_a2 = one("SELECT id FROM interventions WHERE description='R4-IV2'")['id']

    # پیگیری‌ها: الف → یک معوق (موعد گذشته) + یک انجام‌شده؛ ب → آینده
    insert_min(
        'followups', intervention_id=iv_a1, staff_id=staff_a,
        date='1405/06/15', status='pending', method='تماس',
        next_action_date='1405/06/01', description='تست'
    )
    insert_min(
        'followups', intervention_id=iv_a2, staff_id=staff_a,
        date='1405/06/16', status='done', method='تماس',
        next_action_date=None, description='تست'
    )
    insert_min(
        'followups', intervention_id=iv_a2, staff_id=staff_b,
        date='1405/06/17', status='pending', method='تماس',
        next_action_date='1405/12/01', description='تست'
    )

    obs_dal = ObservationDAL()
    int_dal = InterventionDAL()
    fup_dal = FollowUpDAL()
    stu_dal = StudentDAL()

    # ============================================================
    print("=" * 76)
    print("بخش A: format_timestamp — مبدل شمسی مهر زمانی")
    print("=" * 76)

    r = format_timestamp("2026-09-18 19:47:37")
    check("A1", "CURRENT_TIMESTAMP (UTC) → شمسی تهران ۲۳:۱۷",
          r == "1405/06/27 23:17", f"گرفته شد {r!r}")

    r = format_timestamp("2026-09-18T19:47:37.123456")
    check("A2", "isoformat محلی (T) → ساعت دست‌نخورده ۱۹:۴۷",
          r == "1405/06/27 19:47", f"گرفته شد {r!r}")

    r = format_timestamp("2026-09-18T19:47:37Z")
    check("A3", "پسوند Z → UTC، همان انتظار تهران",
          r == "1405/06/27 23:17", f"گرفته شد {r!r}")

    r = format_timestamp("2026-09-18T23:17:37+03:30")
    check("A4", "آفست +03:30 → همان ساعت محفوظ",
          r == "1405/06/27 23:17", f"گرفته شد {r!r}")

    r = format_timestamp("1405/06/27")
    check("A5", "تاریخ از قبل شمسی → دست‌نخورده",
          r == "1405/06/27", f"گرفته شد {r!r}")

    r = format_timestamp("1405-6-7")
    check("A6", "شمسی با خط تیره و بدون صفر → یکدست",
          r == "1405/06/07", f"گرفته شد {r!r}")

    r = format_timestamp("2026-09-18", with_time=False)
    check("A7", "فقط تاریخ میلادی → فقط تاریخ شمسی",
          r == "1405/06/27", f"گرفته شد {r!r}")

    r = format_timestamp("2026-09-18 21:30:00")
    check("A8", "UTC نزدیک نیمه‌شب → روز بعد در تهران",
          r.startswith("1405/06/28"), f"گرفته شد {r!r}")

    r = format_timestamp(None)
    check("A9", "None → جای‌گزین «—»", r == "—", f"گرفته شد {r!r}")

    r = format_timestamp("   ")
    check("A10", "رشتهٔ خالی → جای‌گزین", r == "—", f"گرفته شد {r!r}")

    weird = [12345, 0, [], {}, True, 3.14, "2026-13-45", "18/09/2026",
             "not a date", "", "۱۴۰۵/۰۶/۲۷", "نامشخص"]
    ok = True
    for w in weird:
        try:
            out = format_timestamp(w)
            if not isinstance(out, str):
                ok = False
        except Exception:
            ok = False
    check("A11", "۱۲ ورودی عجیب → بدون هیچ استثنایی", ok)

    r = format_timestamp("۱۴۰۵/۰۶/۲۷")
    check("A12", "ارقام فارسی → نرمال به ASCII",
          r == "1405/06/27", f"گرفته شد {r!r}")

    # ============================================================
    print()
    print("=" * 76)
    print("بخش B: فیلتر معلم در کوئری‌های تحلیلی داشبورد")
    print("=" * 76)

    d = obs_dal.get_observations_distribution_by_type(staff_id=staff_a)
    check("B1", "توزیع مشاهداتِ معلم الف = ۳", d['total'] == 3,
          f"گرفته شد {d['total']}")

    d = obs_dal.get_observations_distribution_by_type()
    check("B2", "بدون فیلتر = ۴ (کل)", d['total'] == 4, f"گرفته شد {d['total']}")

    d = obs_dal.get_observations_distribution_by_type(staff_id=staff_b)
    check("B3", "توزیع مشاهداتِ معلم ب = ۱", d['total'] == 1,
          f"گرفته شد {d['total']}")

    rows = obs_dal.get_observations_by_competency(staff_id=staff_a)
    check("B4", "مشاهدات بر پایه شایستگی (الف) جمع = ۳",
          sum(x['count'] for x in rows) == 3)

    d = int_dal.get_interventions_distribution_by_status(staff_id=staff_a)
    check("B5", "توزیع مداخلات الف = ۲", d['total'] == 2,
          f"گرفته شد {d['total']}")

    d = int_dal.get_interventions_distribution_by_status(staff_id=staff_b)
    check("B6", "توزیع مداخلات ب = ۱", d['total'] == 1,
          f"گرفته شد {d['total']}")

    d = int_dal.get_intervention_success_rate(staff_id=staff_a)
    check("B7", "نرخ موفقیت الف: completed=1، total=2",
          d['completed'] == 1 and d['total'] == 2, f"گرفته شد {d}")

    d = int_dal.get_intervention_success_rate()
    check("B8", "نرخ موفقیت کل: total=3",
          d['total'] == 3, f"گرفته شد {d['total']}")

    d = fup_dal.get_followups_distribution_by_status(staff_id=staff_a)
    check("B9", "توزیع پیگیری‌های الف = ۲", d['total'] == 2,
          f"گرفته شد {d['total']}")

    d = fup_dal.get_followups_distribution_by_status()
    check("B10", "توزیع پیگیری‌های کل = ۳", d['total'] == 3,
          f"گرفته شد {d['total']}")

    n = fup_dal.get_overdue_followups_count(staff_id=staff_a)
    check("B11", "معوقِ الف = ۱ (موعد گذشته)", n == 1, f"گرفته شد {n}")

    n = fup_dal.get_overdue_followups_count(staff_id=staff_b)
    check("B12", "معوقِ ب = ۰ (موعد آینده)", n == 0, f"گرفته شد {n}")

    d = fup_dal.get_followup_completion_rate(staff_id=staff_a)
    check("B13", "نرخ تکمیل الف: total=2، completed=1",
          d['total'] == 2 and d['completed'] == 1, f"گرفته شد {d}")

    rows = stu_dal.get_students_without_observations(staff_id=staff_a)
    check("B14", "بدون‌مشاهدهٔ الف فقط «ب» است",
          [x['last_name'] for x in rows] == ['ب'],
          f"گرفته شد {[x['last_name'] for x in rows]}")

    rows = stu_dal.get_students_without_observations()
    check("B15", "بدون‌مشاهدهٔ کل = ۲ نفر",
          len(rows) == 2, f"گرفته شد {len(rows)}")

    rows = stu_dal.get_student_distribution_by_grade(staff_id=staff_a)
    check("B16", "توزیع پایهٔ الف = ۲ دانش‌آموز",
          sum(x['count'] for x in rows) == 2,
          f"گرفته شد {sum(x['count'] for x in rows)}")

    # ============================================================
    print()
    print("=" * 76)
    print("بخش C: اتصال سرتاسری سرویس داشبورد")
    print("=" * 76)

    from services.dashboard_service import DashboardService
    svc = DashboardService()

    ok = False
    detail = ""
    try:
        data = svc._get_analytics_data(teacher_id=staff_a)
        ok = data['observation_distribution']['total'] == 3
        detail = f"total={data['observation_distribution']['total']}"
    except Exception as e:
        detail = f"{type(e).__name__}: {e}"
    check("C1", "_get_analytics_data(معلم الف) فیلتر را اعمال کرد", ok, detail)

    ok = False
    detail = ""
    try:
        data = svc.get_dashboard_data(teacher_id=staff_a, year_id=year_id)
        an = data.get('analytics', {})
        ok = an.get('observation_distribution', {}).get('total') == 3
        detail = f"total={an.get('observation_distribution', {}).get('total')}"
    except Exception as e:
        detail = f"{type(e).__name__}: {e}"
    check("C2", "get_dashboard_data(معلم الف) سرتاسری سالم", ok, detail)

    # ============================================================
    print()
    print("=" * 76)
    print("بخش D: فوتر شمسیِ خروجی اکسل")
    print("=" * 76)

    from models.student import Student
    from utils.excel_importer import ExcelImporter

    stu = Student()
    stu.first_name = 'دانش'
    stu.last_name = 'آزمون'
    stu.national_code = '9999999999'

    xlsx = os.path.join(TMP, "test_export.xlsx")
    ok, msg = ExcelImporter().export_students_to_excel([stu], xlsx)
    check("D1", "خروجی اکسل ساخته شد", ok and os.path.exists(xlsx), msg[:60])

    if os.path.exists(xlsx):
        import openpyxl
        wb = openpyxl.load_workbook(xlsx)
        ws = wb.active
        footer = None
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                if isinstance(cell, str) and 'تاریخ خروجی' in cell:
                    footer = cell
        m = re.search(r'(\d{4})/(\d{2})/(\d{2})', footer or '')
        jalali_year = int(m.group(1)) if m else 0
        check("D2", "تاریخ فوتر شمسی است (سال ۱۳۰۰–۱۵۰۰)",
              1300 <= jalali_year <= 1500,
              f"فوتر: {footer!r}")
    else:
        check("D2", "تاریخ فوتر شمسی است", False, "فایل ساخته نشد")

    # ============================================================
    print()
    print("=" * 76)
    print("بخش E: بدون پس‌روندگی")
    print("=" * 76)

    n = one("SELECT COUNT(*) c FROM competencies")['c']
    check("E1", "seed دست‌نخورده: ۲۸ شایستگی", n == 28, f"گرفته شد {n}")

    n = one("SELECT COUNT(*) c FROM audit_logs")['c']
    check("E2", "تریگرهای حسابرسی در طول تست فعال بودند", n > 41,
          f"تعداد لاگ = {n}")

    ic = one("PRAGMA integrity_check")[0]
    check("E3", "integrity_check روی دیتابیس تست", ic == 'ok', ic)

    ok = StaffDAL().restore(staff_a, user_id=staff_b) in (True, False)
    check("E4", "فراخوانی restore امضای قبلی را نگه داشته", ok)

finally:
    _restore_main()
    settings.DB_PATH = _orig_settings_path
    dbc.DB_PATH = _orig_conn_path
    shutil.rmtree(TMP, ignore_errors=True)

# ============================================================
print()
print("=" * 76)
print(f"نتیجهٔ دور چهارم:  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های دور چهارم سبز است.")
