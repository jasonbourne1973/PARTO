# گزارش دور هجدهم — ادامهٔ MASTER FIX / FINAL TECHNICAL AUDIT (مرحله‌های ۵ تا ۸)

**شاخهٔ کار:** `arena/01a0d3e6-parto` (وارث نسخهٔ دور هفدهم — مراحل ۱ تا ۴ کامل)
**مبنای بازبینی:** سند «MASTER FIX / FINAL TECHNICAL AUDIT» (بندهای ۰ تا ۴۵)
**این سند تجمعی است:** با پیشرفت هر مرحله، بخش مربوط به آن تکمیل می‌شود.

**وضعیت محیط اجرا:** مثل دور هفدهم، اجرای واقعی Qt با
`LD_LIBRARY_PATH=<qtstub> QT_QPA_PLATFORM=offscreen` (کتابخانه‌های جانشین
libGL/libEGL/libxkbcommon/libdbus بیرون از مخزن ساخته شدند چون شبکهٔ apt
بسته است). کلیک واقعی موس، دیالوگ modal، `QFileDialog`، بازکردن فایل با
برنامهٔ خارجی و اجرای دوبارهٔ فرایند همچنان
`NOT_TESTED - GUI EXECUTION REQUIRED` هستند.

---

# بخش ۱ — راستی‌آزمایی وضعیت ورودی (قبل از هر تغییر)

ادعاهای دور هفدهم مستقلاً در همین محیط اجرا و تأیید شد:

| بررسی | نتیجه |
|---|---|
| `python -m pytest tests/` | ۸۰/۸۰ سبز |
| `verify_fixes17.py` (مراحل ۱–۴ دور ۱۷) | ۴۳/۴۳ سبز |
| `verify_fixes16.py` | ۱۰۱/۱۰۱ سبز |
| `ruff check .` | پاک |

نتیجه: هیچ‌یک از fixهای ادعاشدهٔ مراحل ۱ تا ۴ نیازی به دوباره‌کاری نداشت.

## فهرست باقی‌مانده (همان مرحله‌های ۵ تا ۸ سند دور هفدهم)

| مرحله | اولویت | محتوا | بندها |
|---|---|---|---|
| ۵ = **مرحلهٔ ۱ این دور** | P0 | مرز مجوز backend + ثبت تصمیم طراحی BUG-NAV-02 + رگرسیون تغییر غیرمجاز سال | ۸، ۹، ۲۷ |
| ۶ = مرحلهٔ ۲ این دور | P2 | پیوست‌ها: بازیابی پیوست حذف‌شده + راستی‌آزمایی فایل فیزیکی + حد ۲۰ فایل | ۱۱، ۳۶ |
| ۷ = مرحلهٔ ۳ این دور | P2 | سال و UI: هندلر سال شاخص‌ها، پایه/پرونده از سال انتخاب‌شده، کنتراست هدر، نگاشت ناوبری | ۶، ۷، ۲۶، ۳۱، ۳۳ |
| ۸ = مرحلهٔ ۴ این دور | P3 | باتری رگرسیون نهایی + گزارش machine-readable | ۱۸–۲۵، ۲۹، ۳۰، ۴۰، ۴۱، ۴۳ |

---

# بخش ۲ — مرحلهٔ ۱ (P0 امنیت): مرز مجوز backend — BUG-NAV-03

## ریشهٔ مشکل
تمام enforce مجوز فقط در UI بود (`MainWindow.has_permission` برای منوها و
`_permission_check` برای تب‌های تنظیمات). فراخوانی مستقیم سرویس/DAL از داخل
همان پردازش عملاً همه‌چیز را می‌داد: معلم می‌توانست `UserDAL.delete`،
`AcademicYearDAL.set_active` یا `BackupManager.restore_backup` را صدا بزند.
`SessionManager.has_permission` هم تعریف شده بود ولی هیچ مصرف‌کنندهٔ واقعی
نداشت.

## طراحی (بدون حدس سیاست جدید — فقط مجوزهای موجود در enum)
- **یک مرز واحد:** کلاس `AccessControl` + استثنای `PermissionDeniedError` +
  دکوراتور `permission_required` در `utils/security.py` — کنار همان
  `get_role_permissions` که «تک‌منبع حقیقت» مجوزهاست. هیچ منطق مجوزی در DALها
  تکرار نشده؛ هر DAL فقط «یک خط اعمال» دارد.
- **نشست:** در `MainWindow.on_login_successful` با همان staff_id که
  `DatabaseConnection.set_current_user` می‌گیرد ثبت می‌شود و در مسیر خروج
  پاک می‌شود. نقشِ کاربر در هر بررسی «تازه از دیتابیس» خوانده می‌شود →
  غیرفعال‌سازی/حذف حساب یا تغییر نقش، همان لحظه دسترسی backend را می‌بندد.
- **قرارداد «بدون نشست»** (مستند در `docs/design_decisions_fa.md` → DD-4):
  بافت سیستمی/اسکریپتی (seed، migration، اسکریپت‌های راستی‌آزمایی) مجاز است؛
  در برنامهٔ واقعی هیچ مسیر UI بدون ورود به این متدها نمی‌رسد.
- **ردِ مجوز** لاگ WARNING + ردیف Audit با `action='permission_denied'` دارد
  (بدون سکوت).

## عملیات‌های محافظت‌شده (نگاشت به مجوزهای موجود)

| عملیات | متد | مجوز (از enum موجود) |
|---|---|---|
| ساخت/ویرایش/حذف/بازیابی/فعال‌سازی/ریست رمز کاربر | `UserDAL.create/update/delete/restore/set_active/reset_password` | MANAGE_USERS |
| تغییر رمز «دیگری» | `UserDAL.update_password` | MANAGE_USERS (رمز «خود» باز — DD-4) |
| تغییر نقش (set_role یا تغییر role در update) | `UserDAL.set_role`، `UserDAL.update` | MANAGE_ROLES |
| ایجاد/ویرایش/حذف/تغییر سال فعال | `AcademicYearDAL.create/update/delete/set_active` | MANAGE_ACADEMIC_YEARS |
| حذف/بازیابی دانش‌آموز | `StudentDAL.delete/restore` | DELETE_STUDENT (DD-2) |
| حذف/بازیابی مشاهده/مداخله/پیگیری | `ObservationDAL`، `InterventionDAL`، `FollowUpDAL` | DELETE_OBSERVATION / DELETE_INTERVENTION / DELETE_FOLLOWUP |
| حذف/بازیابی عضو کادر، حذف کلاس | `StaffDAL.delete/restore`، `ClassDAL.delete` | EDIT_SETTINGS (DD-3) |
| ساخت/بازیابی/حذف پشتیبان | `BackupManager.create_backup/restore_backup/delete_backup` | CREATE_BACKUP / RESTORE_BACKUP / DELETE_BACKUP |

## هماهنگ‌سازی UI ↔ backend (DD-5)
دکمه‌های حذف/بازیابی ردیف‌ها در صفحه‌های دانش‌آموزان/مشاهدات/مداخله‌ها/
پیگیری‌ها حالا همان `AccessControl.has_permission` را می‌پرسند؛ نقش بدون
مجوز دیگر دکمهٔ «دکوریِ همیشه‌خطا» نمی‌بیند. تب‌های تنظیمات از قبل با همان
مجوزها بسته بودند (سازگار).

## تصمیم‌های طراحی ثبت‌شده
`docs/design_decisions_fa.md`:
- **DD-1** — BUG-NAV-02: برای Counseling/Activities/Goals هیچ سیاست دسترسی
  در مخزن نیست → `DESIGN DECISION REQUIRED`؛ چیزی ابداع نشد و رفتار فعلی
  (باز برای کاربران واردشده) حفظ شد.
- **DD-2/3** — نگاشت بازیابی→مجوز حذف همان موجودیت و حذف کادر/کلاس→EDIT_SETTINGS.
- **DD-4** — قرارداد بافت بدون نشست.
- **DD-5** — UI از همان مرز می‌پرسد.

## آزمون‌ها
- **جدید:** `tests/test_permission_boundary.py` — ۱۳ آزمون:
  بدون‌نشست=مجاز (قرارداد سیستم)؛ معلم: ساخت کاربر/تغییر سال/حذف
  دانش‌آموز/بازیابی پشتیبان/حذف مشاهده → همه رد + «نتیجهٔ واقعی» بررسی
  می‌شود (رکورد در DB دست‌نخورده)؛ ثبت رد مجوز در audit_logs؛
  vice_principal: RESTORE_BACKUP دارد ولی MANAGE_USERS ندارد؛ تغییر نقش =
  MANAGE_ROLES جدا از MANAGE_USERS؛ رمز «خود» بدون MANAGE_USERS مجاز، رمز
  «دیگری» رد؛ غیرفعال‌سازی حساب → قطع فوری دسترسی backend؛ کمکی UI همان
  پاسخ مرز را می‌دهد.
- **رگرسیون تغییر غیرمجاز سال تحصیلی (بند ۲۷):** `verify_fixes16 §H` — سبز
  (برگشت کامبو + هشدار + دست‌نخوردن DB). حالا backend هم لایهٔ دوم است.
- **رگرسیون کل:** pytest ‏۹۳/۹۳ (۸۰ قبلی + ۱۳ جدید) · verify16 ‏۱۰۱/۱۰۱ ·
  verify17 ‏۴۳/۴۳ · ruff پاک.

## فایل‌های تغییرکردهٔ مرحلهٔ ۱
- `utils/security.py` (AccessControl، PermissionDeniedError، permission_required)
- `dal/user_dal.py`، `dal/academic_year_dal.py`، `dal/student_dal.py`،
  `dal/observation_dal.py`، `dal/intervention_dal.py`، `dal/followup_dal.py`،
  `dal/staff_dal.py`، `dal/class_dal.py`
- `utils/backup.py`
- `views/main_window.py` (login/logout نشست)
- `views/pages/students_page.py`، `observations_page.py`،
  `interventions_page.py`، `followups_page.py` (هماهنگی دکمه‌ها)
- `tests/test_permission_boundary.py` (جدید)
- `docs/design_decisions_fa.md` (جدید) · این سند

## باقی‌ماندهٔ GUI واقعی
`NOT_TESTED - GUI EXECUTION REQUIRED`: ورود/خروج واقعی با کلیک، دیدن
دکمه‌های پنهان‌شده برای نقش کم‌مجوز، و پیام خطای مرز در دیالوگ واقعی.

---

# بخش ۳ — مرحلهٔ ۲ (P2 پیوست‌ها) — در انتظار تأیید کاربر
# بخش ۴ — مرحلهٔ ۳ (P2 سال و UI) — در انتظار تأیید کاربر
# بخش ۵ — مرحلهٔ ۴ (P3 رگرسیون نهایی + گزارش) — در انتظار تأیید کاربر
