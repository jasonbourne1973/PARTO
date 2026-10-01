# دور نوزدهم — برنامهٔ اجرای اصلاحات سند «PARTO Master Audit & Repair Specification»

> بند ۱۸ سند (بافت صوتی / خروجی دستگاه بافت / خروجی‌های رنگرز) به تأیید
> مدیر پروژه **کنار گذاشته شد** — مربوط به پروژهٔ دیگری بوده و ربطی به
> PARTO ندارد. تمام مراحل زیر فقط روی موارد واقعی و مرتبط با PARTO است
> (مستند در `docs/manager_spec_gap_audit_fa.md`).

## اصول اجرا (طبق قوانین ۱–۱۸ سند + قواعد قبلی پروژه)

- بدون افزودن قابلیت جدید — فقط اصلاح.
- هیچ Button/Dialog/API موجود صرفاً برای رفع Bug حذف نمی‌شود.
- اگر تغییر رفتار قابل‌مشاهده لازم شود (نه صرفاً پیاده‌سازی داخلی)، به‌عنوان
  **DESIGN DECISION REQUIRED** علامت می‌خورد و بدون تأیید مدیر پروژه حدس زده
  نمی‌شود (مثل روال قبلی BUG-NAV-02).
- برای هر مرحله: تست Regression مرتبط اضافه/اصلاح → اجرا → Full Suite در پایان.

---

## مرحله‌بندی پیشنهادی — ۸ مرحله

### ✅ مرحلهٔ ۱ — انجام شد (دامنه با تأیید کاربر گسترش یافت: «همهٔ create/update»)
اجرا شد روی هر ۴ موجودیت اصلی (نه فقط Import) + پیوست‌ها + گیت‌بندی UI.
جزئیات/شواهد: `verify_fixes19.py` بخش‌های A–E (۲۳ بررسی)،
`tests/test_permission_boundary.py` (تست‌های جدید create/update/attachment).
دو باگ جانبی هم در `attachment_service.py` کشف و رفع شد (نوع خطای مجوز
در `delete_attachments_by_entity`/`get_deleted_attachments_by_entity`
پنهان می‌شد؛ `search_attachments` رد مجوز را به «فهرست خالی» تبدیل
می‌کرد — هر دو الان صریح `PermissionDeniedError` می‌دهند).

### ✅ مرحلهٔ ۲ — انجام شد
زیرساخت مشترک `AccessControl.has_student_scope`/`require_student_scope`
در `utils/security.py` طبق DD-6 پیاده شد (فقط TEACHER با انتساب فعال در
`teacher_assignments` محدود است؛ بقیهٔ نقش‌ها/بافت بدون نشست آزادند).
جزئیات/شواهد: `tests/test_scope_boundary.py` (۱۱ تست مستقل از هر
Entity)، `verify_fixes19.py` بخش F. **این زیرساخت هنوز به هیچ
DAL/سرویسی وصل نشده** — وصل‌کردن آن به Intervention/Followup (مرحلهٔ ۳)
و Observation/Attachment/Activity (مرحلهٔ ۴) در ادامه انجام می‌شود.

### ✅ مرحلهٔ ۳ — انجام شد
Object-Level (IDOR) Scope روی `InterventionDAL`/`FollowUpDAL` وصل شد:
resolverهای زنجیره (`_student_id_from_profile`، `_profile_id_from_intervention`،
`_intervention_id_from_followup` و `has/require_profile_scope`،
`has/require_intervention_scope`، `has/require_followup_scope`) به
`utils/security.py::AccessControl` اضافه شد و در نقاط زیر سیم‌کشی شد:
- `InterventionDAL.create` → `require_profile_scope` روی `student_profile_id`.
- `InterventionDAL.get_by_id` → هستهٔ رفع IDOR: پیش از این، خواندن مستقیم
  با ID هیچ بررسی Scope نداشت؛ حالا رد Scope صریح `PermissionDeniedError`
  می‌دهد (نه NotFound، طبق DD-6).
- `InterventionDAL.update/delete/restore` → هم رکورد موجود (پیش از تغییر)
  و هم مقصد (اگر `student_profile_id` عوض شود) بررسی می‌شوند.
- `FollowUpDAL.create` → `require_intervention_scope` روی `intervention_id`
  (جلوگیری از Cross-resource: نمی‌شود روی مداخلهٔ خارج از Scope پیگیری ساخت).
- `FollowUpDAL.get_by_id/update/delete/restore` → همان الگو، با زنجیرهٔ
  کامل FollowUp→Intervention→Profile→Student.

**یافتهٔ جانبی (پرچم شده، عمداً دست‌نخورده):** نقش TEACHER امروز اصلاً
`EDIT_INTERVENTION`/`DELETE_INTERVENTION`/`EDIT_FOLLOWUP`/`DELETE_FOLLOWUP`
را در `ROLE_PERMISSIONS` ندارد (فقط `CREATE_*` و `VIEW_*`) — یعنی چک‌های
Scope تازه در `update`/`delete`/`restore` امروز عملاً برای تنها نقش
محدودشده (TEACHER) قابل رسیدن نیستند (چون گیت Permission زودتر رد
می‌کند)؛ برای `create`/`get_by_id` (که TEACHER واقعاً مجوزشان را دارد)
اما Scope کاملاً «زنده» و مؤثر است. این یک تصمیم سیاست مجوز پیش‌موجود
است (آیا TEACHER اصلاً باید بتواند مداخله/پیگیری را ویرایش/حذف کند؟)
و طبق قانون «بدون حدس‌زدن Design Decision»، دست‌نخورده باقی ماند —
فقط گزارش شد. سیم‌کشی update/delete/restore به‌عنوان دفاع در عمق و
آماده برای تغییر احتمالی سیاست مجوز در آینده، همچنان اضافه شد و با
تست (با اعطای موقت مجوز فقط در طول آزمون) راستی‌آزمایی شد.

جزئیات/شواهد: `tests/test_intervention_followup_scope.py` (۲۴ تست)،
`verify_fixes19.py` بخش G (۷ بررسی).

### ✅ مرحلهٔ ۴ — انجام شد
همان الگوی مرحلهٔ ۳ برای `ObservationDAL` (که مستقیماً ستون
`student_profile_id` دارد، بدون واسطه): `create`/`get_by_id`/`update`
با مجوز واقعی TEACHER (که برخلاف Intervention/Followup، هم
`CREATE_OBSERVATION` و هم `EDIT_OBSERVATION` را دارد) به‌طور کامل
راستی‌آزمایی شدند؛ `delete`/`restore` هم سیم‌کشی شدند (TEACHER امروز
`DELETE_OBSERVATION` ندارد، پس آزمون با اعطای موقت مجوز صورت گرفت،
مثل مرحلهٔ ۳).

**تصمیم صریح مدیر پروژه (dd1_scope=add_scope_only)** برای سه موجودیتی
که طبق DD-1 هیچ Permission‌ای ندارند: به `CounselingSessionDAL`،
`ExtracurricularDAL`، `GoalDAL` *فقط* لایهٔ Scope اضافه شد (بدون
اختراع هیچ Permission جدید — DD-1 دست‌نخورده ماند). نتیجه: هر کاربرِ
واردشده‌ای هنوز می‌تواند این سه موجودیت را بسازد/ویرایش/حذف کند (چون
Permission‌ای برایشان تعریف نشده)، اما TEACHER محدود به دانش‌آموزهای
منتسب خودش است — دقیقاً همان چیزی که کاربر خواسته بود.

`AttachmentService._require_entity_scope` (جدید، مستقل از
`_require_entity_permission`) روی هر ۷ نوع `entity_type` شناخته‌شده
اعمال می‌شود (student/observation/intervention/followup/
counseling_session/extracurricular_activity/individual_goal) — یعنی
حتی برای سه موجودیت بدون Permission، اگر روزی UI برایشان پیوست
بسازد، از همین حالا IDOR روی پیوستشان هم مسدود است.

جزئیات/شواهد: `tests/test_stage4_scope.py` (۲۲ تست)، `verify_fixes19.py`
بخش H (۶ بررسی).

### مرحلهٔ ۱ — بستن حفرهٔ Permission در Import/Export (P1، کم‌ریسک، سریع) [مرجع اصلی — بالاتر انجام شد]
- افزودن چک `AccessControl.has_permission(CREATE_STUDENT)` قبل از اجرای
  `import_from_excel` (هم UI: غیرفعال/مخفی کردن دکمه برای بی‌مجوز، هم Service:
  رد با `PermissionDeniedError` حتی در فراخوانی مستقیم).
- بازبینی مشابه برای Export (`EXPORT_REPORTS` نباید معادل Export کل DB باشد —
  بررسی می‌شود آیا الان همین‌طور است یا نه).
- تست‌ها: سناریوی «کاربر VIEWER سعی در Import» → باید رد شود.

### مرحلهٔ ۲ — زیرساخت مشترک Scope/IDOR (پیش‌نیاز مراحل ۳ و ۴)
- ساخت یک لایهٔ کمکی مشترک (مثلاً در `utils/security.py`) برای «آیا کاربر
  جاری به این Student/Profile/Year مشخص دسترسی دارد؟» — بر پایهٔ
  `teacher_assignments` و نقش (مدیر/معاون = همه؛ معلم/مربی = فقط انتساب‌شده).
- بدون این زیرساخت، مراحل بعدی هرکدام باید منطق تکراری بسازند.
- تست‌ها: واحد روی خودِ تابع Scope‌چک (مستقل از هر Entity).

### مرحلهٔ ۳ — IDOR/Scope در Intervention + Follow-up (P1 — SEC-IDOR-01, SEC-SCOPE-01/02/03, SEC-CROSS-01)
- افزودن Object-Level check به `get_intervention`, create/update/delete/restore
  مداخله.
- زنجیرهٔ Follow-up→Intervention→Profile→Student→Year→Scope کاربر جاری.
- جلوگیری از اتصال Follow-up به Intervention خارج از دسترسی (Cross-resource).
- تست‌ها: معلم A نباید بتواند مداخلهٔ معلم B را با ID مستقیم بخواند/ویرایش کند.

### مرحلهٔ ۴ — IDOR/Scope در Observation + Attachment + Activity (P1 — SEC-ATT-01/02)
- همان الگوی مرحلهٔ ۳ برای Observation.
- `get_attachment / get_attachment_path / get_attachment_content`: بررسی
  Parent Authorization قبل از Read/Download.
- Extracurricular Activity: بررسی Teacher/Coach Scope در `get_by_id`.
- تست‌ها: دانلود پیوست متعلق به دانش‌آموز خارج از Scope باید رد شود.

### ✅ مرحلهٔ ۵ — انجام شد

**ممیزی سراسری:** الگوی نشت در سه شکل پیدا شد (نه فقط `raise
ServiceError(f"...{e!s}")`):
1. ۵۱ محل `raise ServiceError(f"...: {e!s}")` در ۱۳ فایل `services/*.py`
   (شامل ۲ محل در `base_service.execute_in_transaction`/`commit_transaction`).
2. ۱۰ محل مشابه که با گرِپ اولیه (فقط تک‌خطی/`ServiceError(f"`) دیده
   نمی‌شدند: قالب چندخطی (`attachment_service.py`)، `return False, f"...{e!s}"`
   (خروجی PDF/Excel در ۴ فایل)، `raise Exception(f"...{e!s}")` بدون
   ServiceError (`teacher_report_service.py`)، و دیکشنری‌های
   `{'error'/'message': f'...{e!s}'}` (`dashboard/student/trend_analysis_service.py`).
3. ۷ محل `str(e)`/`[str(e)]` در بلوک `except Exception` توابع
   `validate_*`/گزارش‌ها که خطای غیرمنتظره را به‌جای پیام امن، مستقیم
   به کاربر برمی‌گرداندند.

همهٔ این ۶۸ محل اصلاح شدند: متن خامِ Exception دیگر در پیام کاربر
درز نمی‌کند؛ جزئیات فنی کامل هنوز در `self.logger.error(...)` (که در
همهٔ این محل‌ها از قبل وجود داشت) ثبت می‌شود.

**نکتهٔ مهم کشف‌شده حین رفع (و اصلاح‌شده):** رفعِ ساده‌لوحانهٔ نشت (فقط
حذف `{e!s}`) خودش یک باگِ تازه ایجاد می‌کرد: چند بلوک `except Exception`
هم Exceptionِ خامِ سیستمی و هم `ServiceError`/`ValidationError` عمدی و
امنی را که *داخل همان try* raise شده بودند (مثل «پیشنهاد یافت نشد» یا
«تعداد پیوست‌ها به حداکثر رسیده») یکسان می‌گرفتند. قبلاً بده‌بستانِ
نشت-از-طریق-embedding به‌طور تصادفی پیام مفید را هم نگه می‌داشت
(`tests/test_attachment_restore.py` این را صراحتاً به‌عنوان «قرارداد
موجود پروژه» مستند کرده بود). برای رفع بدون شکستن آن قرارداد، کمکی
مشترک `BaseService._safe_service_error(e, generic_message)` اضافه شد:
اگر `e` از قبل `AppError` با `user_visible=True` است، همان پیام حفظ
می‌شود (فقط به `ServiceError` تبدیل می‌شود)؛ در غیر این صورت
(Exception خام/سیستمی) پیام عمومیِ امن جایگزین می‌شود. همین منطق در
`execute_in_transaction` هم به‌روزرسانی شد تا `ValidationError`/
`NotFoundError`/`AuthorizationError` را — نه فقط `ServiceError` — با
پیام دست‌نخورده رد کند. `PermissionDeniedError` هم پیامش حفظ می‌شود
(اما نوعش هنوز به `ServiceError` بدل می‌شود — نقص جداگانه و از پیش
موجود از مرحله‌های ۳/۴، نه چیزی که این مرحله ایجاد کرده باشد؛ رفعش
نیازمند افزودن `except PermissionDeniedError: raise` در ده‌ها محل
فراخوانی است و خارج از حیطهٔ ERR-01/ERR-LEAK-01 گزارش/پرچم‌گذاری شد،
نه رفع شد).

**`DatabaseError`/`DataIntegrityError`:** بررسی شد که این دو کلاس در
سراسر کدبیس اصلاً هیچ‌جا `raise` نمی‌شدند (کلاس‌های تعریف‌شده ولی
استفاده‌نشده). با کاربر مشورت شد (`ask_user`، گزینهٔ A انتخاب شد):
به‌جای مهاجرت این ۶۸ محل به این دو کلاس (تغییر نوع Exception در سراسر
کد که طبق دستور مدیر پروژه نیازمند ممیزی کامل همهٔ call siteها بود)،
همان `ServiceError` با `user_visible=False` صریح استفاده شد. عدم
تغییرِ نوع = صفر ریسکِ شکستنِ `except ServiceError` موجود (فقط ۳ محل
در UI: `followup_form.py`/`intervention_form.py`/`observation_form.py`،
هیچ‌کدام این ۶۸ محل را صدا نمی‌زنند). درستیِ `user_visible=False` این
دو کلاس با تست مستقیم روی خودِ کلاس (نه فقط جایی که استفاده می‌شود)
تضمین شد (`tests/test_error_leak.py::TestAppErrorVisibilityInvariants`).

**تست‌ها:** `tests/test_error_leak.py` (۱۸ تست جدید):
`TestNoRawExceptionLeak` (۸ تست — شبیه‌سازی RuntimeError/OSError در
DAL برای Observation/Intervention/FollowUp/Student/Attachment/
`execute_in_transaction`/`commit_transaction`/`ReportGenerator.export_to_pdf`
و بررسی نبودِ متن خام در پیام)، `TestAppErrorVisibilityInvariants`
(۶ تست — `DatabaseError`/`DataIntegrityError`/`ServiceError`/
`ErrorHandler`)، `TestSafeMessagesPreserved` (۴ تست — پیام سقفِ پیوست،
«یافت نشد» مداخله/پیشنهاد، بازآزمونِ دقیقِ verify_fixes6 §F3). یک
اسمبلیِ قدیمی (`verify_fixes16.py` §E) که صراحتاً انتظار داشت متنِ
خامِ RuntimeErrorِ شبیه‌سازی‌شده در پیامِ کاربر دیده شود (یعنی خودِ
نشت را تأیید می‌کرد) به‌روزرسانی شد تا برعکس، نبودِ متن خام را تضمین
کند. `verify_fixes19.py` با بخش I (۶ بررسی) گسترش یافت.

**رگرسیون نهایی:** unittest 205/205، verify_fixes16-19 = 101+43+78+47
= 269/269، `ruff check .` تمیز. دو شکستِ از پیش‌موجود و نامرتبط
(`verify_fixes5` §C3، `verify_fixes14` §E) بدون تغییر باقی ماندند.

---

### ✅ مرحلهٔ ۶ — انجام شد

**تصمیم دامنه (`ask_user`، گزینهٔ `backend_infra_only`):** به‌جای افزودن
کنترل صفحه‌بندی (page/page_size UI) به صفحه‌های مشاهدات/مداخلات/
پیگیری‌ها/فعالیت‌های فوق‌برنامه — که امروز اصلاً چنین کنترلی ندارند و
افزودنش طبق دستور مدیر پروژه («بدون افزودن قابلیت») یک قابلیت تازه
محسوب می‌شد، نه رفع باگ — فقط زیرساختِ لازم (`count_all()` + پارامتر
`offset`) به این چهار DAL اضافه شد؛ تنها `students_page.py` (که از قبل
UI صفحه‌بندی دارد) پیاده‌سازیِ داخلی‌اش واقعاً از Slice پایتونی به
`LIMIT/OFFSET` واقعی تبدیل شد.

**۱) اعتبارسنج مرکزی Pagination (`utils/pagination.py`):**
تابع `normalize_limit_offset(limit, offset, max_limit=...)` اضافه شد:
- `limit=None` (بدون سقف، رفتار قدیمیِ همهٔ DALها) دست‌نخورده می‌ماند —
  حتی وقتی `offset` مقدار دارد — تا فراخوانی‌های موجود بدون تغییر رفتار
  کار کنند.
- مقادیر منفیِ `limit`/`offset` کلمپ می‌شوند (صفر/حداقل مجاز).
- سقف بالای `limit` اعمال می‌شود تا کوئری‌های ناخواسته با `limit`
  بسیار بزرگ را محدود کند.
- `clamp_page_to_total(total, page, page_size)` هم برای هماهنگیِ همان
  قرارداد «صفحه ۱ از ۱» (حتی برای دیتاست خالی) ثابت نگه داشته شد.

**۲) `students_page.py` — تبدیل Slice→SQL:** پیش از این مرحله،
`load_students`/`search_students` کل دیتاست فیلترشده را در
`self.all_students` می‌ریختند و صفحهٔ جاری را با Slice پایتونی
(`all_students[start:end]`) می‌ساختند؛ `total_pages` هم از
`len(all_students)` محاسبه می‌شد. حالا `self.students` فقط نتیجهٔ یک
کوئری واقعیِ `LIMIT/OFFSET` است و `total_count` از یک کوئری `COUNT`
جداگانه (با همان `WHERE`/Scope/فیلترها) می‌آید — رفتار قابل‌مشاهده برای
کاربر (شمارهٔ صفحه، تعداد کل، محتوای هر صفحه) عوض نشد، فقط پیاده‌سازیِ
داخلی. **نکتهٔ مهم:** `export_to_excel()` عمداً دست‌نخورده ماند و
هنوز کل دیتاستِ فیلترشده (نه فقط صفحهٔ جاری) را با یک واکشیِ کاملِ
جداگانه صادر می‌کند — این رفتار از قبل همین‌طور بود و تغییری در آن
قابلیت داده نشد.

**۳) `count_*`/`offset` در چهار DAL دیگر (بدون UI تازه):**
`ObservationDAL`/`InterventionDAL`/`FollowUpDAL`/`ExtracurricularDAL`
اکنون `count_all()` و پارامتر `offset` در `get_all(limit=None,
offset=0)` دارند؛ چون پیش‌فرض `limit=None` است، هیچ فراخوانی موجودی
(که تا امروز بدون آرگومان صدا زده می‌شد) رفتارش عوض نشد — این فقط
زیرساختِ آمادهٔ استفادهٔ آیندهٔ Dashboard/گزارش‌ها (مرحلهٔ ۷) است.

**تست‌ها:** `tests/test_pagination.py` (۳۲ تست جدید):
`TestPaginationHelpers` (۱۱ تست روی `normalize_limit_offset`/
`clamp_page_to_total`)، `TestStudentDALPagination` (۸ تست —
`count_all`/`LIMIT`/`OFFSET`/`search`/`count_search`/`only_deleted`)،
`TestObservationDALPagination`/`TestInterventionDALPagination`/
`TestFollowUpDALPagination`/`TestExtracurricularDALPagination`
(مجموعاً ۱۳ تست — `count_all`+`offset` روی هر چهار DAL دیگر).
`verify_fixes19.py` با بخش J (۸ بررسی J1–J8) گسترش یافت؛ J8 صراحتاً
تأیید می‌کند که هیچ نشانهٔ UI صفحه‌بندی تازه‌ای
(`page_size_combo`/`current_page`/`next_page_btn`/`prev_page_btn`) به
سورس صفحه‌های مشاهدات/مداخلات/پیگیری‌ها اضافه نشده است.

**رگرسیون نهایی:** unittest 237/237 (205 قبلی + ۳۲ جدید)،
`verify_fixes19.py` = 55/55، بقیهٔ `verify_fixes*.py` بدون تغییر نسبت
به مرحلهٔ قبل (همان دو شکستِ از پیش‌موجود و نامرتبط `verify_fixes5`
§C3 و `verify_fixes14` §E)، `ruff check .` تمیز.

---

### ✅ مرحلهٔ ۷ — انجام شد

**جایگزینیِ get_all() کامل با Aggregate SQL:** در `services/dashboard_service.py`
سه متد `_get_general_stats`/`_get_observation_trend`/`_get_teacher_stats`
قبلاً با `observation_dal.get_all()`/`intervention_dal.get_all()`/
`followup_dal.get_all()` **کل** جدول را (بدون سقف) به پایتون می‌آوردند و
شمارش/تفکیکِ نوع رفتار/ماه را با `len()`/`sum()`/حلقه انجام می‌دادند. حالا
سه متد جدید در DAL این کار را با یک کوئری `COUNT/SUM/GROUP BY` مستقیم در
DB انجام می‌دهند:
- `ObservationDAL.get_dashboard_stats(staff_id=None, academic_year_id=None)`
  → `{total, positive, negative, neutral}` با یک کوئری.
- `ObservationDAL.get_monthly_trend(staff_id=None, academic_year_id=None)`
  → `{ماه: {count, positive, negative, neutral}}` با `GROUP BY
  substr(observation_date, 1, 7)`؛ `dashboard_service` فقط ۶ ماه موردنظرش
  را از نتیجه جست‌وجو می‌کند (به‌جای حلقهٔ قدیمی روی همهٔ مشاهدات).
- `FollowUpDAL.get_dashboard_stats(staff_id=None, academic_year_id=None)`
  → `{total, pending}` با یک کوئری.
- برای `interventions_count` نیازی به متد تازه نبود: `count_all` که در
  مرحلهٔ ۶ اضافه شده بود (`staff_id`/`academic_year_id`) دقیقاً همین کار
  را می‌کرد.

هر سه متدِ Aggregate جدید فیلترهای `staff_id`/`academic_year_id` را دقیقاً
مثل `get_all`/`count_all` (مرحلهٔ ۶) دارند؛ اعداد خروجیِ نهاییِ Dashboard
(کارت‌های آماری، نمودار روند ۶‌ماهه، پنل معلمِ انتخاب‌شده) هیچ تغییری
نکرد — فقط پیاده‌سازیِ داخلی از «Load کامل + شمارش پایتونی» به «Aggregate
در DB» تبدیل شد. دو متد کمکیِ خصوصیِ قدیمی (`_filter_by_year`/
`_filter_followups_by_year`) که دیگر مصرف‌کننده‌ای نداشتند حذف شدند
(هیچ فایل دیگری، از جمله تست‌ها، آن‌ها را صدا نمی‌زد).

**نکتهٔ رفتار قدیمیِ عمداً حفظ‌شده:** در `_get_teacher_stats`، بر خلاف
`_get_general_stats`، پیگیری‌ها هرگز بر اساس `year_id` فیلتر نمی‌شدند
(فقط `staff_id`) — این نامتقارنی از قبل در کد وجود داشت؛ چون تغییرش
عددهای موجودِ پنل «آمار معلم» را عوض می‌کرد و خارج از حیطهٔ PERF-01/08/09
بود، عیناً حفظ شد (نه رفع، نه گسترش).

**باگِ جانبیِ کشف‌شده و رفع‌شده حین این مرحله:** برای این‌که جایگزینیِ
بالا دقیقاً همان اعداد قبلی را بدهد، لازم بود رفتار فیلتر `academic_year_id`ِ
سه DAL (که در مرحلهٔ ۶ اضافه شده بود) با منطق پایتونیِ قدیمیِ
`_filter_by_year`/`_filter_followups_by_year` یکی باشد. بررسی نشان داد
`JOIN`ِ این فیلتر با `student_academic_profiles` شرط `is_deleted = 0`
نداشت — یعنی رکوردهای متعلق به یک **پروندهٔ سالانهٔ حذف‌شده** هم در
فیلتر سال شمرده می‌شدند؛ در حالی‌که `_filter_by_year` قدیمی (از طریق
`profile_dal.get_by_ids`) و همه‌جای دیگرِ کدبیس این پرونده‌ها را مستثنا
می‌کنند. این ناسازگاری در `get_all`/`count_all` مرحلهٔ ۶ هم از قبل وجود
داشت، ولی چون تا این مرحله هیچ مصرف‌کنندهٔ واقعی‌ای نداشت (فقط زیرساخت
آماده بود) بی‌اثر مانده بود؛ با اولین مصرف‌کنندهٔ واقعی (Dashboard) این
ناسازگاری به یک باگِ واقعی تبدیل می‌شد (اعداد نادرست/بزرگ‌تر). رفع شد:
`ObservationDAL`/`InterventionDAL`/`FollowUpDAL` حالا در `get_all`/
`count_all`/`_base_filters` شرط `sap.is_deleted = 0` را هم به فیلتر سال
اضافه می‌کنند — بدون تغییر امضای هیچ متدی، فقط تصحیح WHERE.

**تست‌ها:** `tests/test_dashboard_aggregates.py` (۱۷ تست جدید):
`TestObservationDashboardStats` (۶ تست — شمارش/تفکیک، فیلتر معلم/سال،
حذف نرم مشاهده، و رگرسیونِ باگِ بالا)، `TestObservationMonthlyTrend`
(۳ تست)، `TestFollowUpDashboardStats` (۳ تست، شامل رگرسیونِ باگ)،
`TestInterventionCountAllYearFilterBugfix` (۱ تست مستقل)،
`TestDashboardServiceEndToEnd` (۴ تست — مقایسهٔ عددیِ خروجیِ نهاییِ
`_get_general_stats`/`_get_teacher_stats`/`_get_observation_trend` با
محاسبهٔ دستی روی یک فیکسچر ثابت). `verify_fixes19.py` با بخش K (۸
بررسی K1–K8) گسترش یافت؛ K8 با `inspect.getsource` تضمین می‌کند سه
متدِ اصلاح‌شده دیگر `get_all()` خامِ این سه DAL را صدا نمی‌زنند.

**رگرسیون نهایی:** unittest 254/254 (237 قبلی + ۱۷ جدید)،
`verify_fixes19.py` = 63/63، بقیهٔ `verify_fixes*.py` بدون تغییر نسبت
به مرحلهٔ قبل (همان دو شکستِ از پیش‌موجود و نامرتبط `verify_fixes5`
§C3 و `verify_fixes14` §E)، `ruff check .` تمیز.

---

### ✅ مرحلهٔ ۸ — انجام شد (آخرین مرحله)

**SEC-HARD-DELETE-01 — Permission+Scope+Dependency پیش از Permanent Delete:**
ممیزی نشان داد `permanent_delete` در `StudentDAL`/`ObservationDAL`/
`InterventionDAL`/`FollowUpDAL`/`UserDAL` **هیچ بررسیِ Permission**
نداشت (هر کاربری، حتی VIEWER، می‌توانست مستقیم صدا بزند) و
`StudentDAL`/`InterventionDAL` هیچ بررسیِ وابستگی هم نداشتند — با
اینکه `student_academic_profiles.student_id` و `followups.
intervention_id` هر دو با `ON DELETE CASCADE` وصل‌اند؛ یعنی حذف دائم
یک دانش‌آموز یا مداخله عملاً کل تاریخچهٔ وابسته (پرونده/مشاهده/مداخله/
پیگیری/غربالگری/...) را بدون Audit Trail برای همیشه پاک می‌کرد.
`StaffDAL.permanent_delete` از قبل یک گاردِ وابستگیِ کامل داشت (سند
گزارش کرده بود) ولی آن هم Permission نداشت.

همهٔ این متدها اصلاح شدند — **بدون اختراع Permission تازه**، هرکدام
همان مجوزِ delete()/restore() خودش را می‌خواهد
(`DELETE_STUDENT`/`DELETE_OBSERVATION`/`DELETE_INTERVENTION`/
`DELETE_FOLLOWUP`/`MANAGE_USERS`/`EDIT_SETTINGS`). `StudentDAL`/
`InterventionDAL` گاردِ وابستگیِ تازه هم گرفتند (اگر پروندهٔ سالانه/
پیگیریِ وابسته وجود داشته باشد، حذف دائم با پیام روشن رد می‌شود —
دقیقاً همان الگوی از‌پیش‌موجودِ `staff_dal`). `ObservationDAL`/
`FollowUpDAL`/`UserDAL` نیازی به گاردِ وابستگی نداشتند (بررسی شد: FK
مرتبط با آن‌ها یا `ON DELETE SET NULL` است یا اصلاً جدولی به آن‌ها وصل
نیست). **نکتهٔ مهم دامنه:** هیچ‌کدام از این ۶ متد از هیچ صفحه/دکمه‌ای
در UI صدا زده نمی‌شدند (فقط `verify_fixes3.py`/`verify_fixes14.py`
مستقیم صدایشان می‌زدند) — یعنی این یک سخت‌سازیِ پیش‌گیرانه روی
زیرساختی است که امروز غیرفعال است، نه رفعِ یک حفرهٔ در حالِ سوءاستفاده.

**RESTORE-EDGE-01 — بررسی وجود/عدم‌حذفِ والد پیش از Restore فرزند:**
`restore()` در `ObservationDAL`/`InterventionDAL`/`FollowUpDAL`/
`StudentAcademicProfileDAL` فقط Scope موجودیت را بررسی می‌کرد، نه
اینکه خودِ موجودیت والد (به‌ترتیب: پروندهٔ سالانه/پروندهٔ سالانه/
مداخله/دانش‌آموز) هنوز وجود دارد و حذف نشده. یعنی می‌شد یک مشاهده را
بازیابی کرد در حالی‌که پروندهٔ سالانه‌اش جداگانه حذف مانده بود —
حالتی ناسازگار (رکورد «فعال» روی والدِ «حذف‌شده») که در Dashboard/
گزارش‌ها (که پروندهٔ حذف‌شده را مستثنا می‌کنند) به شکل نامنسجم دیده
می‌شد. هر چهار متد حالا پیش از تغییر واقعی DB این بررسی را دارند و در
صورت حذف‌بودنِ والد، `ValueError` با پیامِ روشن می‌دهند (کاربر را به
بازیابیِ اول والد ارجاع می‌دهند). `AttachmentService.restore_attachment`
هم همین بررسی را — برای هر ۷ نوع `entity_type` شناخته‌شده (همان
نگاشتِ `ENTITY_SCOPE_CHECKER` از مرحلهٔ ۴) — به‌عنوان گامِ «۱.۵» قبل از
بررسیِ «فایل فیزیکی وجود دارد» اضافه کرد.

**تست‌ها:** `tests/test_hard_delete_restore_edge.py` (۲۴ تست جدید) —
گاردهای Permission/وابستگیِ هر ۶ `permanent_delete`، و گاردهای
والدِ هر ۴ `restore()` + `AttachmentService.restore_attachment`.
`verify_fixes19.py` با بخش L (۹ بررسی L1–L9) گسترش یافت. سه فایل
رگرسیونِ موجود که فیکسچرهایشان روی «`entity_id` نمادین بدون رکورد
واقعی» بنا شده بودند به‌روزرسانی شدند تا با بررسیِ تازهٔ RESTORE-EDGE-01
سازگار بمانند: `tests/test_attachment_restore.py` (حالا یک
Observation واقعی در `setUp` می‌سازد)، `verify_fixes18.py` §A (همان
الگو + یک شمارشِ hardcoded در §D10 که با ۱ مشاهدهٔ تازه هماهنگ شد).

**رگرسیون نهایی:** unittest 278/278 (254 قبلی + ۲۴ جدید)،
`verify_fixes19.py` = 72/72، بقیهٔ `verify_fixes*.py` بدون تغییر نسبت
به مرحلهٔ قبل (همان دو شکستِ از پیش‌موجود و نامرتبط `verify_fixes5`
§C3 و `verify_fixes14` §E)، `ruff check .` تمیز.

**یافتهٔ جانبی — بعداً همان روز با تأیید کاربر تکمیل شد:** حین بررسی،
مشخص شد کلِ `StudentAcademicProfileDAL` (نه فقط `restore`) هیچ
بررسیِ Permission یا Scope‌ای در `create`/`update`/`delete`/`restore`
ندارد — این DAL از قلمِ مراحل ۱ (`expand_all_create`) و ۲–۴ (زیرساخت
Scope) جا مانده بود. ابتدا فقط **مستند و پرچم‌گذاری** شد (طبق قاعدهٔ
«آژانس حق حدسِ سیاست دسترسیِ تازه را ندارد»)؛ کاربر بعداً درخواست کرد
همین‌جا تکمیل شود. تحلیلِ `create`/`update` نشان داد این دو متد چند
مسیر فعال و حساس دارند (از جمله ایجاد خودکار پرونده هنگام ثبت اولین
مشاهده/مداخلهٔ یک دانش‌آموز در سال جاری — در `observation_service.py`/
`intervention_service.py`؛ و همچنین دیالوگ افزودن/ویرایش دانش‌آموز و
صفحهٔ ارتقاء پایه) که TEACHER با `CREATE_OBSERVATION` (نه لزوماً
`EDIT_STUDENT`) آن‌ها را فعال می‌کند — گیت‌کردنِ نادرست اینجا می‌توانست
بی‌سروصدا ثبت مشاهده را برای معلم‌ها بشکند؛ پس **عمداً دست‌نخورده
ماندند** (نیازمند تحلیل جداگانه‌ای در حد یک مرحلهٔ کامل، نه یک تکمیلِ
سریع). اما `delete()`/`restore()` بررسی شد و معلوم شد **هیچ
مصرف‌کنندهٔ فعالی در Service یا UI ندارند** (دقیقاً مثل `permanent_delete`
مرحلهٔ ۸) — پس بدون هیچ ریسکِ رگرسیون، همان مجوز `DELETE_STUDENT` +
Scope دانش‌آموز (`require_student_scope`) به هر دو اضافه شد. تست‌های
تکمیلی در همان `tests/test_hard_delete_restore_edge.py`
(کلاس `TestProfilePermissionAndScope`، ۵ تست) و بخش M جدید در
`verify_fixes19.py` (M1–M2). رگرسیونِ نهایی پس از این تکمیل: unittest
**283/283** (۲۷۸ قبلی + ۵ جدید)، `verify_fixes19.py` = **74/74**، بقیهٔ
`verify_fixes*.py` بدون تغییر (همان دو شکستِ از پیش‌موجود)، `ruff
check .` تمیز.

---

### مرحلهٔ ۵ — رفع نشت Exception خام (P1 — ERR-01, ERR-LEAK-01)
- ممیزی سراسری الگوی ‪`ServiceError(f"...{e!s}")`‬ در تمام `services/*.py`
  و `base_service.execute_in_transaction`.
- جایگزینی با: لاگ کامل فنی + پیام عمومی امن برای کاربر (بدون sqlite/Traceback/مسیر فایل).
- اطمینان از `DatabaseError.user_visible=False` و `DataIntegrityError.user_visible=False`
  در تمام مسیرها (نه فقط جایی که قبلاً تست شده).
- تست‌ها: شبیه‌سازی خطای DB/فایل → پیام کاربر نباید متن خام داشته باشد.

### مرحلهٔ ۶ — اصلاح Query/Pagination (P1/P2 — بخش‌های ۲، ۳، ۲۵، ۳۵)
- افزودن اعتبارسنجی مرکزی Pagination (`page>=1`, `page_size<=MAX`, `offset>=0`)
  به یک محل مشترک (مثلاً `utils` یا `BaseService`) و استفادهٔ آن در
  Observation/Intervention/Followup/Activity.
- تبدیل Pagination صفحهٔ دانش‌آموزان (`students_page.py`) از Slice پایتونی
  روی کل دیتاست به `LIMIT/OFFSET` واقعی در DAL (رفتار قابل‌مشاهده برای کاربر
  عوض نمی‌شود، فقط پیاده‌سازی داخلی).
- اطمینان از اینکه `COUNT` دقیقاً همان `WHERE` را دارد (Scope+Year+Filter).
- تست‌ها: صحت `total`/`page`/`offset` روی دیتاست فیلترشده.

### مرحلهٔ ۷ — Dashboard/Performance با Aggregate (P2 — PERF-01/08/09)
- جایگزینی `observation_dal.get_all()` / `intervention_dal.get_all()` /
  `followup_dal.get_all()` در `dashboard_service.py` با کوئری‌های
  `COUNT/GROUP BY/SUM` مستقیم در DB.
- حفظ دقیق همان اعداد/نمودارهای فعلی Dashboard (بدون تغییر UI/Output).
- تست‌ها: مقایسهٔ عددی خروجی قبل/بعد اصلاح روی دیتاست تست یکسان.

### مرحلهٔ ۸ — Delete/Restore Edge Cases + رگرسیون نهایی کامل (P1/P2 — بخش‌های ۱۸، ۱۹، ۲۹، ۳۰ + Full Suite)
- `SEC-HARD-DELETE-01`: بررسی Permission+Scope+Dependency قبل از Permanent Delete.
- `RESTORE-EDGE-01`: قبل از Restore فرزند، بررسی وجود/فعال/دسترسی‌پذیر بودن والد.
- اجرای کامل `pytest` + تمام `verify_fixes*.py` + اسکریپت جدید
  `verify_fixes19.py` برای موارد این دور.
- تدوین گزارش نهایی machine-readable (مثل `master_fix_report.json`) با
  Round=19.

---

## نکات مهم قبل از شروع

1. **DESIGN DECISIONها تعیین شدند (توسط مدیر پروژه) — ثبت در `docs/design_decisions_fa.md::DD-6`:**
   - مدل Scope: فقط نقش **TEACHER** محدود به `teacher_assignments` خودش
     است؛ MANAGER/COUNSELOR/VICE_PRINCIPAL/VICE_EDUCATION/SPORT_COACH/
     QURAN_COACH/ART_COACH/VIEWER/OTHER/SYSTEM بدون محدودیت Scope هستند
     (فقط از طریق Permission موجود کنترل می‌شوند).
   - رفتار نبود Scope: `PermissionDeniedError` صریح (نه NotFound).
   - Import اکسل: رفتار Partial فعلی **عمداً حفظ می‌شود**؛ فقط Permission
     Gate اضافه می‌شود، نه Atomicity کامل فایل.
2. مراحل ۳ و ۴ به مرحلهٔ ۲ وابسته‌اند (زیرساخت مشترک Scope). مرحلهٔ ۶ و ۷
   مستقل از ۲ تا ۵ هستند و می‌توانند زودتر یا موازی انجام شوند اگر اولویت
   عوض شود.
3. بعد از هر مرحله، Regression کامل قبلی (۶۴۶+ بررسی دورهای ۱–۱۸) هم اجرا
   می‌شود تا Regression جدید ایجاد نشود.
