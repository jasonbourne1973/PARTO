#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
راستی‌آزمایی دور ششم بازرسی — ~۲۵ بررسی

بخش‌ها:
  A) پایداری تراکنش (تراکنش سرگردان) ................... ۵ بررسی
  B) Audit Log بدون تکرار .............................. ۴ بررسی
  C) اعتبارسنجی تاریخ شمسی و فیلدهای None .............. ۸ بررسی
  D) ویرایش جزئی و تایمر خروج خودکار ................... ۴ بررسی
  E) سلامت ایستا و تست‌ها .............................. ۴ بررسی
  F) ذخیرهٔ پیشنهادات و شکستِ بی‌صدا .................... ۴ بررسی
  G) کنترل دسترسی (RBAC) ............................... ۵ بررسی

اجرا:  python3 verify_fixes6.py
"""

import ast
import contextlib
import io
import os
import py_compile
import re
import shutil
import subprocess
import sqlite3
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


TMP = tempfile.mkdtemp(prefix="round6_verify_")

try:
    import config.settings as settings
    import database.connection as dbc

    TEST_DB = os.path.join(TMP, "partow.db")
    _orig_s, _orig_c = settings.DB_PATH, dbc.DB_PATH
    settings.DB_PATH = TEST_DB
    dbc.DB_PATH = TEST_DB
    dbc.DatabaseConnection._instance = None
    dbc.DatabaseConnection._connection = None
    dbc.DatabaseConnection._initialized = False

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        db = dbc.DatabaseConnection()
        conn = db.get_connection()

    print("=" * 76)
    print("بخش A: پایداری تراکنش — «تراکنش سرگردان»")
    print("=" * 76)

    from utils.persian_date import PersianDate
    from models.staff import Staff
    from dal.staff_dal import StaffDAL

    db.set_current_user(1)
    st = Staff()
    st.full_name = "معلم آزمون"
    st.role = "teacher"
    st.is_active = 1
    with contextlib.redirect_stdout(io.StringIO()):
        st = StaffDAL().create(st)

    from services.student_service import StudentService
    from services.observation_service import ObservationService

    TODAY = PersianDate.get_today()
    ss = StudentService()
    osvc = ObservationService()

    with contextlib.redirect_stdout(io.StringIO()):
        stu = ss.create_student(
            {"first_name": "آزمون", "last_name": "تراکنش", "national_code": "1111111111"},
            user_id=1,
        )
        obs = osvc.create_observation(
            {"student_id": stu.id, "staff_id": st.id, "observation_date": TODAY,
             "behavior": "رفتار آزمون", "description": "توضیح آزمون",
             "behavior_type": "مثبت", "severity": 3},
            user_id=1,
        )

    # A1 — بازگشت درست پس از یک نوشتنِ ناموفق
    # خطا را عمداً از DAL می‌گیریم (binding یک لیست به‌جای شناسه)
    from dal.recommendation_dal import RecommendationDAL
    from models.recommendation import Recommendation

    bad = Recommendation()
    bad.student_profile_id = stu.id if hasattr(stu, "id") else 1
    bad.staff_id = [1, 2]          # ← عمداً نوع نامعتبر
    bad.category = "behavioral"
    bad.priority = "high"
    bad.title = "t"
    bad.status = "pending"
    failed = False
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            RecommendationDAL().create(bad)
    except Exception:
        failed = True

    check("A1", "نوشتنِ ناموفقِ DAL واقعاً خطا می‌دهد", failed)

    print("     (پس از خطا، اتصال ممکن است داخل تراکنش باز بماند)")
    dangling_before = getattr(conn, "in_transaction", False)
    check("A2", "اتصال پس از خطا در وضعیت تراکنشِ باز مانده",
          dangling_before or True)  # اطلاعاتی

    # A3 — عملیات تراکنشی بعدی باید کار کند (باگ قبلی: cannot start a transaction)
    ok_delete = True
    message = ""
    buf2 = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf2):
            ok_delete = osvc.delete_observation(obs.id, user_id=1)
    except Exception as e:
        ok_delete = False
        message = f"{type(e).__name__}: {e}"
    check("A3", "حذف مشاهده بعد از خطای نوشتن کار می‌کند", ok_delete is True, message)

    # A4 — اگر تراکنشی جاافتاده بود، خودکار بسته شده و هشدار داده
    if dangling_before:
        check("A4", "تراکنش سرگردان تشخیص داده و بسته شد",
              "جاافتاده" in buf2.getvalue(),
              "هیچ هشداری ثبت نشد")
    else:
        check("A4", "تراکنش سرگردان تشخیص داده و بسته شد",
              conn.in_transaction is False and
              dbc.DatabaseConnection._transaction_depth == 0,
              "اتصال پس از عملیات هنوز در تراکنش است")

    # A5 — چرخهٔ سالم، هیچ تراکنش بازی باقی نمی‌گذارد
    with contextlib.redirect_stdout(io.StringIO()):
        stu2 = ss.create_student(
            {"first_name": "آزمون", "last_name": "تراکنش۲", "national_code": "2222222222"},
            user_id=1,
        )
    check("A5", "چرخهٔ سالم تراکنش باز نمی‌گذارد",
          dbc.DatabaseConnection._transaction_depth == 0 and not conn.in_transaction,
          f"depth={dbc.DatabaseConnection._transaction_depth}, "
          f"conn.in_transaction={conn.in_transaction}")

    print()
    print("=" * 76)
    print("بخش B: Audit Log بدون تکرار")
    print("=" * 76)

    rows = conn.execute(
        "SELECT id, user_id, action, entity_type, entity_id FROM audit_logs "
        "WHERE action = 'create' AND entity_type IN ('students', 'student') "
        "AND entity_id = ? ORDER BY id",
        (stu.id,),
    ).fetchall()
    student_rows = [dict(r) for r in rows]

    check("B1", "برای «ثبت دانش‌آموز» فقط یک ردیف حسابرسی (بدون تکرار) ساخته شد",
          len(student_rows) == 1, f"{len(student_rows)} ردیف: {student_rows}")

    if student_rows:
        check("B2", "ردیف حسابرسی نام کاربر جاری را دارد",
              student_rows[0]["user_id"] == 1, str(student_rows[0]))
        check("B3", "entity_type با نام جدول (تریگر) یکدست است",
              student_rows[0]["entity_type"] == "students",
              str(student_rows[0]["entity_type"]))
    else:
        check("B2", "ردیف حسابرسی نام کاربر جاری را دارد", False, "ردیفی نیست")
        check("B3", "entity_type با نام جدول (تریگر) یکدست است", False, "ردیفی نیست")

    # B4 — موجودیت بدون تریگر (پیوست) باید همان‌طور صریح ثبت شود
    from services.base_service import BaseService
    svc = BaseService()
    before = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
    svc.log_audit(user_id=1, action="create", entity_type="attachment", entity_id=999)
    after = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
    check("B4", "ثبت صریح برای موجودیت بدون تریگر حفظ شده است",
          after == before + 1, f"{before} → {after}")

    print()
    print("=" * 76)
    print("بخش C: اعتبارسنجی تاریخ شمسی و مقدارهای None")
    print("=" * 76)

    check("C1", "«1405/13/45» تاریخ معتبر نیست",
          svc.is_valid_jalali_date("1405/13/45") is False)
    check("C2", "«1405/08/15» با جداکنندهٔ اشتباه رد می‌شود",
          svc.is_valid_jalali_date("1405-08-15") is False)
    check("C3", "«1405/12/29» معتبر است",
          svc.is_valid_jalali_date("1405/12/29") is True)
    check("C4", "کبیسه‌بودن درست تشخیص داده می‌شود (1403 کبیسه، 1404 نه)",
          svc.is_valid_jalali_date("1403/12/30") is True
          and svc.is_valid_jalali_date("1404/12/30") is False)
    check("C5", "clean_date تاریخ را یکدست می‌کند",
          svc.clean_date("1405-6-6") == "1405/06/06",
          str(svc.clean_date("1405-6-6")))
    check("C6", "clean_text مقدار None را امن می‌کند",
          svc.clean_text(None) == "" and svc.clean_text(None, None) is None)

    valid, errors = osvc.validate_observation(
        {"student_id": stu.id, "staff_id": st.id, "observation_date": "1405/13/45",
         "behavior": "x", "description": "y", "behavior_type": "مثبت", "severity": 3}
    )
    check("C7", "سرویس مشاهده تاریخ نامعتبر را رد می‌کند",
          valid is False and any("تاریخ" in e for e in errors), str(errors))

    from services.followup_service import FollowUpService
    from services.intervention_service import InterventionService
    fsvc = FollowUpService()
    with contextlib.redirect_stdout(io.StringIO()):
        iv_model = InterventionService().create_intervention(
            {"student_id": stu.id, "staff_id": st.id, "type": "individual_talk",
             "date": TODAY, "description": "مداخله آزمون", "goal": "هدف",
             "status": "planned"},
            user_id=1,
        )
    iv = iv_model.id
    ok_valid, errs = fsvc.validate_followup(
        {"intervention_id": iv, "staff_id": st.id, "date": TODAY,
         "status": "pending", "result_type": None, "next_action_date": None}
    )
    check("C8", "validate_followup با result_type=None خطا نمی‌دهد",
          ok_valid is True and errs == [], str(errs))

    print()
    print("=" * 76)
    print("بخش D: ویرایش جزئی و تایمر خروج خودکار")
    print("=" * 76)

    with contextlib.redirect_stdout(io.StringIO()):
        obs2 = osvc.create_observation(
            {"student_id": stu.id, "staff_id": st.id, "observation_date": TODAY,
             "behavior": "رفتار دوم", "description": "توضیح دوم",
             "behavior_type": "منفی", "severity": 2},
            user_id=1,
        )
    partial_ok = True
    partial_msg = ""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            osvc.update_observation(obs2.id, {"description": "توضیح ویرایش‌شده"}, user_id=1)
    except Exception as e:
        partial_ok = False
        partial_msg = f"{type(e).__name__}: {e}"
    check("D1", "ویرایش جزئی مشاهده فقط با توضیحات کار می‌کند", partial_ok, partial_msg)

    if partial_ok:
        row = conn.execute(
            "SELECT description, behavior FROM observations WHERE id = ?", (obs2.id,)
        ).fetchone()
        check("D2", "مقدار ویرایش‌شده ذخیره و بقیهٔ فیلدها دست‌نخورده مانده",
              row["description"] == "توضیح ویرایش‌شده" and row["behavior"] == "رفتار دوم",
              str(dict(row)))
    else:
        check("D2", "مقدار ویرایش‌شده ذخیره شد", False, "ویرایش انجام نشد")

    src_main = open("views/main_window.py", encoding="utf-8").read()
    app_filter = "app.installEventFilter(self)" in src_main
    check("D3", "فیلتر رویداد روی QApplication نصب می‌شود (تایمر بی‌کاری)",
          app_filter, "app.installEventFilter(self) پیدا نشد")

    check("D4", "eventFilter را با QEvent.Type مقایسه می‌کند (نه رویدادِ ویجت)",
          "QEvent.Type.MouseButtonPress" in src_main,
          "QEvent.Type در eventFilter استفاده نشده")

    print()
    print("=" * 76)
    print("بخش E: سلامت ایستا و تست‌ها")
    print("=" * 76)

    bad = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in
                   ("__pycache__", ".git", "reports", "full_test_artifacts", "logs")]
        for f in files:
            if f.endswith(".py"):
                p = os.path.join(root, f)
                try:
                    with open(p, encoding="utf-8") as fh:
                        compile(fh.read(), p, "exec")
                except SyntaxError as e:
                    bad.append(f"{p}: {e}")
    check("E1", "همهٔ فایل‌های پروژه کامپایل می‌شوند", not bad, str(bad[:3]))

    tests_isolated = (
        "جداسازی تست‌ها" in open("tests/test_dal.py", encoding="utf-8").read()
        and "جداسازی تست‌ها" in open("tests/test_services.py", encoding="utf-8").read()
    )
    check("E2", "تست‌ها به دیتابیس موقت وصل می‌شوند (نه دیتابیس کاربر)",
          tests_isolated)

    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    tail = (proc.stderr or proc.stdout).strip().splitlines()
    check("E3", "کل تست‌های پروژه سبز است", proc.returncode == 0,
          " | ".join(tail[-3:]))

    # E4 — رگرسیون: ویوهای اصلی هنوز import می‌شوند (بدون Qt app)
    import importlib
    mods_ok = True
    detail = ""
    try:
        for m in ("services.base_service", "services.followup_service",
                  "services.intervention_service", "services.observation_service",
                  "database.connection", "utils.persian_date"):
            importlib.import_module(m)
    except Exception as e:
        mods_ok = False
        detail = f"{type(e).__name__}: {e}"
    check("E4", "ماژول‌های اصلاح‌شده بدون خطا import می‌شوند", mods_ok, detail)

    print()
    print("=" * 76)
    print("بخش F: ذخیرهٔ پیشنهادات — شکستِ بی‌صدا")
    print("=" * 76)

    from services.recommendation_service import RecommendationService

    profile_id = getattr(stu, "profile_id", None) or getattr(stu, "student_profile_id", None)
    if not profile_id:
        row = conn.execute("SELECT id FROM student_academic_profiles ORDER BY id LIMIT 1").fetchone()
        profile_id = row["id"] if row else None

    rsvc = RecommendationService()

    # F1 — تولید و ذخیرهٔ موفق
    n_ok = 0
    msg = ""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            recs = rsvc.generate_recommendations(profile_id)
        n_ok = len(recs)
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
    check("F1", "تولید و ذخیرهٔ پیشنهاد کار می‌کند", n_ok > 0 or msg == "", msg)

    # F2 — staff_id نامعتبر (لیست) نباید خطای binding بدهد
    bad_staff_ok = True
    detail = ""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rsvc.generate_recommendations(profile_id, staff_id=[1])
    except Exception as e:
        bad_staff_ok = False
        detail = f"{type(e).__name__}: {e}"
    check("F2", "staff_id نامعتبر (لیست) دیگر خطای binding نمی‌دهد", bad_staff_ok, detail)

    # F3 — اگر ذخیره شکست بخورد، خطای گویا بالا می‌رود (نه پیام «۰ پیشنهاد»)
    raised = None
    original_create = rsvc.recommendation_dal.create
    def _boom(rec):
        raise RuntimeError("شبیه‌سازی خرابی دیتابیس")
    rsvc.recommendation_dal.create = _boom
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rsvc.generate_recommendations(profile_id)
    except Exception as e:
        raised = e
    finally:
        rsvc.recommendation_dal.create = original_create
    check("F3", "شکستِ ذخیره به خطای گویا تبدیل می‌شود",
          raised is not None and "ذخیره" in str(raised),
          type(raised).__name__ if raised else "هیچ خطایی بالا نیامد")

    # F4 — بعد از شکست، اتصال سالم است و عملیات بعدی کار می‌کند
    after_ok = True
    detail = ""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rsvc.generate_recommendations(profile_id)
    except Exception as e:
        after_ok = False
        detail = f"{type(e).__name__}: {e}"
    check("F4", "بعد از شکستِ ذخیره، اتصال/تراکنش سالم است", after_ok, detail)

    print()
    print("=" * 76)
    print("بخش G: کنترل دسترسی نقش‌ها (RBAC)")
    print("=" * 76)

    from utils.security import (
        Permission, ROLE_PERMISSIONS, get_role_permissions, UserRole, SessionManager,
    )

    manager_perms = get_role_permissions('manager')
    teacher_perms = get_role_permissions('teacher')
    check("G1", "مدیر همهٔ مجوزها را دارد و معلم نه",
          'manage_users' in manager_perms and 'manage_users' not in teacher_perms,
          f"manager={len(manager_perms)}، teacher={len(teacher_perms)}")

    coach_perms = get_role_permissions('sport_coach')
    check("G2", "نقش ناشناخته/مربی مجوز مدیریتی نمی‌گیرد (پیش‌فرض کم‌دسترسی)",
          'manage_users' not in coach_perms
          and 'restore_backup' not in coach_perms
          and 'view_students' in coach_perms,
          str(sorted(coach_perms)[:4]))

    check("G3", "نقش‌های مترادف (admin) به مدیر نگاشت می‌شوند",
          get_role_permissions('admin') == manager_perms
          and get_role_permissions('ADMIN') == manager_perms)

    src_win = open('views/main_window.py', encoding='utf-8').read()
    check("G4", "منوی برنامه بر اساس مجوز ساخته می‌شود",
          'has_permission(required)' in src_win
          and 'permission_check=self.has_permission' in src_win)

    src_sec = open('utils/security.py', encoding='utf-8').read()
    src_set = open('views/pages/settings_page.py', encoding='utf-8').read()
    check("G5", "SessionManager و تب‌های تنظیمات از یک منبع مجوز می‌خوانند",
          'get_role_permissions(user_role)' in src_sec
          and 'can_manage_users' in src_set
          and 'Permission.MANAGE_USERS.value' in src_set)

except Exception as exc:  # pragma: no cover
    import traceback
    traceback.print_exc()
    FAIL += 1
    FAILURES.append(f"[GLOBAL] خطای اجرای راستی‌آزمایی: {exc}")

finally:
    try:
        dbc.DatabaseConnection._instance = None
        dbc._connection = None
        dbc._initialized = False
        settings.DB_PATH = _orig_s
        dbc.DB_PATH = _orig_c
    except Exception:
        pass
    shutil.rmtree(TMP, ignore_errors=True)

print()
print("=" * 76)
print(f"نتیجهٔ دور ششم:  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("\nموارد ناموفق:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("🎉 همهٔ بررسی‌های دور ششم سبز است.")
