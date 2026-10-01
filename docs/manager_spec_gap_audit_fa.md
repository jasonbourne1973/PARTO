# ممیزی نقطه‌به‌نقطهٔ سند «PARTO Master Audit & Repair Specification»

**تاریخ:** ۱۴۰۵/۰۷/۰۴ (2026-09-26)
**هدف این سند:** فقط بررسی صحت ادعاهای مدیر پروژه در برابر کد واقعی — **بدون تغییر کد**.
**Branch/Commit بررسی‌شده:** `arena/01a0ddf1-parto`، آخرین کامیت `309b973` (روی `ea2d15f Initial commit`).

---

## نتیجهٔ کلی

| بخش | نتیجه |
|---|---|
| آیا سند مربوط به همین پروژه PARTO است؟ | ✅ بله — تمام موجودیت‌ها، اسم متدها، Permissionها و کلاس‌های خطا عیناً در کد پیدا شدند. |
| آیا موارد امنیتی/فنی مطرح‌شده واقعی‌اند؟ | ✅ بله — چند مورد P1 (IDOR، Import بدون Permission، Error leak، Dashboard N+1) با شاهد مستقیم از کد تأیید شد. |
| آیا بخشی از سند نامرتبط/اشتباه است؟ | ⚠️ بله — بند ۱۸ (بافت صوتی/دستگاه بافت/رنگرز) کاملاً بی‌ربط به PARTO است. |

---

## ۱) بند ۱۸ — قابلیت‌های حذف‌شدهٔ نامرتبط ❌ (اشتباه در سند)

ادعا: نباید این‌ها برگردند: Audio weaving، Weaving machine output، Dyer/color-code outputs.

**بررسی:** جست‌وجوی کامل در کد فعلی، کل تاریخچهٔ Git (فقط ۲ کامیت: `ea2d15f`, `309b973`) و تمام `docs/*.md` هیچ ردی از بافندگی/دستگاه بافت/رنگرزی نشان نداد. PARTO یک سامانهٔ پایش رفتاری دانش‌آموزان است. تنها برخورد، کلمهٔ «بافت» به معنای *context* (بافت سیستمی = system context در تست‌های Round 18) بود که ربطی به صنعت نساجی ندارد.

**نتیجه:** این سه خط ظاهراً از قالب ممیزی یک پروژهٔ دیگر (احتمالاً یک نرم‌افزار کارخانه‌ای/نساجی) به اشتباه در این سند باقی مانده. **باید نادیده گرفته شود یا از مدیر پروژه دربارهٔ منشأش سؤال شود.**

---

## ۲) بخش‌های تأییدشده با شاهد مستقیم کد (مشکل واقعاً وجود دارد)

### ۲.۱ SEC-IDOR-01 — عدم Object-Level Authorization (P1) ✅ تأیید شد

مثال دقیقاً همانی‌ست که خود سند زده (`get_intervention`):

```python
# dal/intervention_dal.py:50
def get_by_id(self, intervention_id, include_deleted=False):
    query = "SELECT * FROM interventions WHERE id = ?"   # بدون هیچ Scope/staff_id

# services/intervention_service.py:289
def get_intervention(self, intervention_id):
    intervention = self.intervention_dal.get_by_id(intervention_id)  # بدون Authorization
```

همین الگو عیناً در `attachment_service.get_attachment / get_attachment_path /
get_attachment_content` هم هست (SEC-ATT-01).

**نکتهٔ مهم:** تست‌های «مرز مجوز» دور ۱۸ (`tests/test_permission_boundary.py`) فقط
سطح **Permission/Role** را چک می‌کنند (مثلاً «آیا این نقش اجازهٔ حذف مداخله
دارد؟») نه سطح **Scope شیء** (آیا این مداخلهٔ خاص به این معلم/مربی تعلق دارد؟).
یعنی این شکاف امنیتی از دورهای قبلی باقی مانده و رفع نشده — دقیقاً همان چیزی
که قانون ۹ سند می‌گوید: «Permission به‌تنهایی برای دسترسی به Resource کافی
نیست.»

### ۲.۲ Import بدون هیچ کنترل Permission (P1 — این مورد را سند صریحاً نگفته ولی دقیقاً هم‌خانوادهٔ رگ‌های ۹/۱۰/۱۴ است) ✅ تأیید شد

```python
# views/pages/students_page.py:196
self.import_btn.clicked.connect(self.import_from_excel)   # هیچ has_permission/setEnabled چکی ندارد

# views/pages/students_page.py:704 → import_from_excel()
importer.import_students_from_excel(file_path, year_id)   # بدون AccessControl.has_permission(CREATE_STUDENT)
```

`ExcelImporter.import_students_from_excel` (در `utils/excel_importer.py`) هم
هیچ‌جا `AccessControl`/`Permission` را import یا چک نمی‌کند. یعنی هر کاربر
واردشده (حتی نقش `VIEWER`/مشاهده‌گر که باید فقط‌خواندنی باشد) می‌تواند دکمهٔ
Import را بزند و دانش‌آموز واقعی در دیتابیس ایجاد کند. این دقیقاً همان الگوی
ممنوعِ رگ ۸ سند است: «Security را به UI واگذار نکن» — اینجا حتی در UI هم
گیت نشده.

### ۲.۳ ERR-01 / ERR-LEAK-01 — نشت متن خام Exception (P1) ✅ تأیید شد، الگوی سیستمی

```python
# services/intervention_service.py, attachment_service.py, base_service.py و بیشتر سرویس‌ها
raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
raise ServiceError(f"خطا در عملیات: {e!s}") from e     # base_service.execute_in_transaction
```

این الگو در چند فایل سرویس تکرار شده — یعنی مورد ایزوله نیست، یک الگوی
سیستمی است. با اینکه ساختار `ErrorHandler`/`ValidationError`/... حفظ شده
(نکتهٔ خوب سند در بخش ۳۸)، اما در لایهٔ `ServiceError` عمومی، متن خامِ
Exception پایتون (`{e!s}`) مستقیم به پیام User-facing تزریق می‌شود.

### ۲.۴ PERF-01/08/09 — Dashboard بدون Aggregate/Scope (P2) ✅ تأیید شد

```python
# services/dashboard_service.py
observations = self.observation_dal.get_all()   # بدون Year/Scope/Limit، کل دیتاست
interventions = self.intervention_dal.get_all()
followups = self.followup_dal.get_all()
```

نکتهٔ مثبت: بخشی از Dashboard (`profile_dal.get_by_ids`, `student_dal.get_by_ids`)
از دور ۱۴ اصلاح و Batch شده — پس این بخش الگوی خوبی دارد، ولی
Observation/Intervention/Followup هنوز `get_all()` کامل را Load می‌کنند و
Aggregate در پایتون انجام می‌شود.

### ۲.۵ Pagination Correctness — Anti-pattern واقعی در students_page (P1/P2) ✅ تأیید شد

```python
# views/pages/students_page.py
self.all_students = ...   # کل دیتاست فیلترشده در حافظه لود می‌شود
self.total_pages = (len(self.all_students) + self.page_size - 1) // self.page_size
start = self.current_page * self.page_size
end = min(start + self.page_size, len(self.all_students))
```

Pagination به‌صورت **کامل در پایتون** (slice روی لیست از قبل لودشده) انجام
می‌شود، نه با `LIMIT/OFFSET` در SQL. برای دیتاست کوچک (یک مدرسه) خطر عملکردی
جدی نیست، ولی دقیقاً همان الگویی‌ست که سند رد می‌کند (بخش ۲۵، ۳۵).

همچنین در سطح DAL هیچ‌کدام از `observation_dal / intervention_dal /
followup_dal / extracurricular_dal` پارامتر `page/page_size/offset` استاندارد
ندارند — فقط `limit` ساده دارند (`student_dal.get_all` تنها موردی‌ست که
`offset` هم دارد). یعنی «Pagination مرکزی و قابل‌استفادهٔ مجدد» طبق تعریف
بخش ۲۵ سند وجود ندارد.

---

## ۳) بخش‌هایی که ادعای سند در نمونه‌های بررسی‌شده **تأیید نشد** (به نفع کد)

- **SEC-SQL-EDGE-01 (تزریق sort_by):** در `observation_dal / intervention_dal /
  student_dal` تمام `ORDER BY`ها هاردکد هستند (`ORDER BY observation_date DESC`
  و مشابه)، نه از ورودی مستقیم کاربر. ریسک تزریق SQL از این مسیر در نمونه‌های
  بررسی‌شده دیده نشد. (برای اطمینان کامل باید تمام Sort UI-controlled احتمالی
  در `views/` هم چک شود — خارج از حوصلهٔ این ممیزی سریع.)
- **`except Exception: pass` (Error Swallowing):** در کد Production
  (`dal/`, `services/`, `views/`, `utils/`) دیده نشد؛ فقط در اسکریپت‌های
  مستقل `verify_fixes*.py` (که تست/ابزارند، نه بخشی از برنامه در حال اجرا).
- **Attachment temp-file cleanup (`.part`):** طبق ادعای بند ۳۸ سند («نباید
  Regression بخورد») — بررسی شد و واقعاً درست پیاده شده: نوشتن روی `.part`
  و `os.replace` اتمیک، با پاک‌سازی در صورت شکست بعدی.
- **`get_by_ids()` به‌جای N+1:** واقعاً در `student_dal`, `intervention_dal`,
  `competency_dal`, `student_academic_profile_dal` پیاده شده و در
  `dashboard_service` هم استفاده می‌شود (بخشی از Dashboard).

---

## ۴) بخش‌هایی که نیاز به بررسی عمیق‌تر یا اجرای واقعی GUI دارند (این دور بررسی نشد)

این‌ها را نمی‌شد فقط با خواندن کد به‌طور قطعی تأیید/رد کرد:

- IDOR در Observation/Followup/Student (فقط Intervention/Attachment را با
  جزئیات چک کردم؛ الگو محتمل است مشابه باشد چون همان معماری DAL/Service را
  دارند — `observation_dal.get_by_id` هم بدون Scope است).
- SEC-CROSS-01 (Follow-up متعلق به Intervention اشتباه) — `followup_service`
  فقط بررسی می‌کند Intervention وجود دارد، نه اینکه به Scope/Year همان
  کاربر تعلق دارد.
- IDEMP-01 (Double click/Retry)، DB-EDGE-01 (قفل هم‌زمان SQLite)،
  FILE-EDGE-01 (کامل)، STATE-EDGE-01 — این‌ها رفتاری‌اند و باید با اجرای
  واقعی/تست خودکار سنجیده شوند.
- GUI Contract (بخش ۳۷) — نیاز به `tools/ui_inventory.py` + بازبینی دستی.

---

## ۵) جمع‌بندی نهایی

سند مدیر پروژه **به‌درستی روی همین پروژهٔ PARTO** نوشته شده و **شاخهٔ اشتباهی
بررسی نشده**. تنها ایراد، **بند ۱۸** (سه مورد نساجی/بافندگی) است که باید حذف
یا نادیده گرفته شود. بقیهٔ سند — به‌ویژه بخش‌های Authorization/IDOR
(بخش‌های ۵، ۸، ۱۴، ۱۵)، Import Permission (بخش ۹/۱۰)، Error Leak
(بخش ۲۲)، و Dashboard Performance (بخش ۱۲) — روی **مشکلات واقعی و
هنوز رفع‌نشده** انگشت گذاشته که در دورهای ۱ تا ۱۸ کامل پوشش داده نشده بودند
(چون آن دورها فقط لایهٔ Permission/Role را اضافه کردند، نه Scope شیء).

**بالاترین ریسک برای اصلاح فوری (P1 واقعی):**
1. Import Excel بدون هیچ کنترل Permission (هر نقشی می‌تواند دانش‌آموز بسازد).
2. IDOR در `get_intervention` / `get_attachment*` (و احتمالاً observation/followup مشابه).
3. نشت متن خام Exception در `ServiceError` (سیستمی، نه موردی).
