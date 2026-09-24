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

# بخش ۳ — مرحلهٔ ۲ (P2 پیوست‌ها): بازیابی پیوست — BUG-ATT-04/05/06

## ریشهٔ مشکل
- **BUG-ATT-04:** `AttachmentDAL` حذف منطقی و حذف دائم داشت ولی هیچ
  متد بازیابی‌ای وجود نداشت؛ مسیر UI هم فقط نمایش/آپلود/دانلود/حذف.
- **BUG-ATT-05:** تابع بازیابی وجود نداشت؛ یعنی هیچ راستی‌آزمایی فایل
  فیزیکی هم در کار نبود.
- **BUG-ATT-06:** سقف ۲۰ فقط در آپلود سنجیده می‌شد؛ اثرش روی «بازیابی»
  و آزمون ۲۰/۲۱ نداشت.

## تغییرات
### DAL — `dal/attachment_dal.py`
- `get_by_id(attachment_id, include_deleted=False)` — برای مسیر بازیابی
  (همان قرارداد StudentDAL).
- `get_deleted_by_entity(entity_type, entity_id)` — فهرست حذف‌شده‌های
  یک موجودیت.
- `restore(attachment_id, user_id)` — قرارداد سایر DALها:
  `UPDATE ... WHERE id=? AND is_deleted=1` → `rowcount > 0` (نه True ثابت)؛
  فقط رکورد؛ مسئولیت فایل فیزیکی با سرویس.
- **رگرسیون بند ۱۳:** `delete` قبلاً True ثابت برمی‌گرداند؛ حالا
  `rowcount == 0 → False` (سرویسِ حذف همین را با پیام «حذف نشد» نشان می‌داد
  ولی DAL همیشه True می‌داد).

### سرویس — `services/attachment_service.py`
- `restore_attachment(...)` با همین زنجیرهٔ StudentService.restore_student:
  ۱) رکورد باید واقعاً حذف‌شده باشد؛ ۲) **BUG-ATT-05:** وجود فایل فیزیکی
  پیش از هر تغییر DB (فایل گم‌شده → ServiceError صریح، رکورد حذف می‌ماند)؛
  ۳) سقف ۲۰ با پیوست‌های بازیابی‌شده هم سنجیده می‌شود (**BUG-ATT-06**)؛
  ۴) نتیجهٔ واقعی DAL + بازخوانی از DB؛ ۵) Audit (تریگر
  `trg_attachments_restore_audit` خودش ردیف action='restore' را می‌نویسد
  و `log_audit` از ثبت تکراری می‌گذرد).
- `get_deleted_attachments_by_entity(...)` با همان غنی‌سازی فهرست فعال
  (آیکون/حجم نمایشی).

### UI — `views/dialogs/attachment_dialog.py`
- چک‌باکس «نمایش حذف‌شده‌ها» (همان کمک‌تابع مشترک `make_show_deleted_checkbox`)
  + دکمهٔ «↩️ بازیابی» (فقط در حالت حذف‌شده‌ها دیده می‌شود؛ با
  `make_*` مشترک `views/widgets/deleted_records.py` — همان قرارداد
  چهار صفحهٔ دیگر).
- انتخاب ردیف حذف‌شده: فقط «بازیابی» فعال می‌شود (open/download/delete
  قفل) و اطلاعات از شیء حذف‌شده خوانده می‌شود (پیش‌نمایش ندارد).
- تأییدیهٔ بازیابی → سرویس → **نتیجهٔ واقعی** سنجیده می‌شود؛ شکست (فایل
  گم‌شده/سقف پر) با `report_restore_failure` صریح به کاربر — بدون
  موفقیت خاموش. پس از موفقیت، دیالوگ به فهرست فعال برمی‌گردد.
- جست‌وجو در حالت حذف‌شده‌ها روی همان فهرست حذف‌شده‌ها کار می‌کند.
- سیگنال جداگانهٔ «بازیابی» تعریف نشد: سیگنال‌های موجود دیالوگ
  (`attachment_added/deleted`) هم گیرنده‌ای در معماری فعلی ندارند و
  ممیزی Signal/Slot دور ۱۶ (verify16 §C) هر سیگنال بلااستفادهٔ تازه را
  می‌گیرد؛ بازخورد بازیابی داخل خود دیالوگ است.

## آزمون‌ها
- **جدید:** `tests/test_attachment_restore.py` — ۱۴ آزمون:
  چرخهٔ کامل حذف→بازیابی با محتوای سالم؛ بازیابیِ حذف‌نشده/ناموجود →
  خطای صریح؛ قرارداد `rowcount>0` در DAL؛ فهرست حذف‌شده‌ها دقیق؛
  **BUG-ATT-05:** فایل گم‌شده/مسیر خالی → خطای صریح + رکورد حذف می‌ماند؛
  **BUG-ATT-06:** ۲۰قبول/۲۱رد بدون ردیف DB و فایل یتیم، آزادشدن جا با
  حذف، شمردن پیوست بازیابی‌شده در سقف، سقف به‌ازای هر موجودیت؛ Audit
  بازیابی (دقیقاً یک ردیف تریگر، بدون تکرار) و زنجیرهٔ حذف/بازیابی/حذف.
- **جدید:** `verify_fixes18.py` — ۲۶ بررسی با «صفحهٔ واقعی» دیالوگ
  (آفلاین): A1 تا A8 شامل انتخاب با هندلر واقعی `itemClicked`
  (`on_file_selected`)، بازیابی موفق/شکست از مسیر UI، پیام‌های
  صریح، رگرسیون حذف منطقی (فایل می‌ماند) و قرارداد DAL.
- **رگرسیون کل:** pytest ‏۱۰۷/۱۰۷ (۹۳ قبلی + ۱۴ جدید) · verify16 ‏۱۰۱/۱۰۱ ·
  verify17 ‏۴۳/۴۳ · verify18 ‏۲۶/۲۶ · ruff پاک.

## فایل‌های تغییرکردهٔ مرحلهٔ ۲
- `dal/attachment_dal.py`، `services/attachment_service.py`،
  `views/dialogs/attachment_dialog.py`
- `tests/test_attachment_restore.py` (جدید) · `verify_fixes18.py` (جدید)
- این سند

## باقی‌ماندهٔ GUI واقعی
`NOT_TESTED - GUI EXECUTION REQUIRED`: کلیک واقعی چک‌باکس/دکمه‌ها،
دیالوگ تأیید واقعی، آپلود چندفایلی با QFileDialog واقعی (سقف ۲۰ در سطح
سرویس و صفحه آزموده شد؛ انتخاب‌گر فایل سیستمی نه) و بازکردن فایل با
برنامهٔ خارجی.

---

# بخش ۴ — مرحلهٔ ۳ (P2 سال و UI) — در انتظار تأیید کاربر
# بخش ۵ — مرحلهٔ ۴ (P3 رگرسیون نهایی + گزارش) — در انتظار تأیید کاربر
