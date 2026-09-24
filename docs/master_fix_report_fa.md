# گزارش نهایی دور هجدهم — تحویل سند MASTER FIX / FINAL TECHNICAL AUDIT

**شاخه:** `arena/01a0d3e6-parto` · **تاریخ:** ۲۰۲۶-۰۹-۲۴
**نسخهٔ machine-readable:** `docs/master_fix_report.json`
**سند ممیزی زنده:** `docs/tech_audit_18_fa.md`

---

## ۱. خلاصهٔ اجرا

سند MASTER FIX در دو دور تکمیل شد:

| دور | مراحل | محتوا |
|---|---|---|
| ۱۷ (عامل قبل) | ۱ تا ۴ | ایمنی پشتیبان/بازیابی، اتمیک‌بودن CRUD دانش‌آموز، مسیرهای Restore، ایمپورت/خروجی/صفحه‌بندی/LIMIT |
| **۱۸ (این دور)** | **۵ تا ۸** | **مرز مجوز backend، بازیابی پیوست، سال و UI، رگرسیون نهایی + گزارش** |

**جمع راستی‌آزمایی نهایی:** pytest ‏**۱۲۰/۱۲۰** · verify16 ‏**۱۰۱/۱۰۱** ·
verify17 ‏**۴۳/۴۳** · verify18 ‏**۷۸/۷۸** · ruff **پاک**

---

## ۲. Changed files (فایل‌های تغییرکردهٔ دور ۱۸)

**مرحلهٔ امنیت (P0):** `utils/security.py` (AccessControl + PermissionDeniedError
+ permission_required)، `dal/user_dal.py`، `dal/academic_year_dal.py`،
`dal/student_dal.py`، `dal/observation_dal.py`، `dal/intervention_dal.py`،
`dal/followup_dal.py`، `dal/staff_dal.py`، `dal/class_dal.py`،
`utils/backup.py`، `views/main_window.py`، چهار صفحهٔ رکورد
(دکمه‌های هماهنگ)، `tests/test_permission_boundary.py` [جدید]،
`docs/design_decisions_fa.md` [جدید]

**مرحلهٔ پیوست‌ها:** `dal/attachment_dal.py`، `services/attachment_service.py`،
`views/dialogs/attachment_dialog.py`، `tests/test_attachment_restore.py` [جدید]

**مرحلهٔ سال و UI:** `dal/student_academic_profile_dal.py` (متد دسته‌ای
سال‌دار)، `views/pages/indicators_page.py`، `views/pages/analysis_page.py`،
`views/main_window.py` (رنگ سایدبار + PAGE_INDEX/goto_page)،
`tests/test_year_ui_scope.py` [جدید]

**مرحلهٔ نهایی:** `verify_fixes18.py` [جدید — ۷۸ بررسی]،
`docs/gui_test_checklist_fa.md` (افزوده‌های ۷/۸/۹)، این گزارش،
`docs/master_fix_report.json`

## ۳. Fixed bugs

| ID | ریشه | اصلاح | آزمون | نتیجه |
|---|---|---|---|---|
| BUG-NAV-03 | enforce مجوز فقط در UI بود | مرز واحد AccessControl روی enum موجود؛ خوانش تازهٔ نقش از DB؛ Audit رد مجوز؛ ۲۱ متد حساس | ۱۳ آزمون + verify18 §C | ✅ |
| BUG-NAV-02 | هیچ سیاست دسترسی برای مشاوره/فعالیت/اهداف نیست | **DESIGN DECISION REQUIRED** ثبت شد (DD-1)؛ چیزی ابداع نشد | — | 📋 |
| BUG-ATT-04 | بازیابی پیوست اصلاً وجود نداشت | DAL.restore + سرویس + چک‌باکس/دکمهٔ UI | ۱۴ آزمون + verify18 A1-A4 | ✅ |
| BUG-ATT-05 | فایل فیزیکی راستی‌آزمایی نمی‌شد | بررسی وجود فایل **پیش از** هر تغییر DB؛ شکست صریح | آزمون فایل گم‌شده + verify18 A5 | ✅ |
| BUG-ATT-06 | سقف ۲۰ فقط در آپلود | سقف با بازیابی هم سنجیده؛ ۲۰قبول/۲۱رد بدون خرابی | آزمون سقف + verify18 A6 | ✅ |
| BUG-GUI-13 | پنل شاخص‌های سال قبلی روی صفحه می‌ماند | on_year_changed صریح: پاک‌سازی پنل + فهرست سال جدید + حفظ ایمن انتخاب | ۱۳ آزمون + verify18 B2/B4 | ✅ |
| BUG-GUI-07/08 | پایهٔ فهرست از پروندهٔ فعال (نشتی سال) | پایه از پروندهٔ سال انتخاب‌شده (DAL دسته‌ای جدید)؛ بدون fallback | آزمون دو‌ساله + verify18 B1/B3/B4 | ✅ |
| BUG-GUI-01 | رنگ نام/آیکون کاربر = پس‌زمینه (نامرئی 1:1) | رنگ #F4C542 (~9:1) + آزمون WCAG شش جفت | verify18 C3 | ✅ |
| BUG-NAV-07 | ایندکس ناوبری خام و تکراری | PAGE_INDEX تنها مرجع؛ goto_page؛ آزمون منع ایندکس خام | pytest + verify18 C1/C2 | ✅ |

## ۴. DB changes

**هیچ تغییر schema در این دور لازم نشد** (هیچ fixی نیاز به migration نداشت —
مطابق قاعدهٔ ۱۷ مأموریت: هیچ تغییر schema بدون migration). یافتهٔ ثبت‌شدهٔ
D11: DBهای تازه CHECK رفتار/شدت دارند؛ DBهای قدیمیِ فقط-upgrade‌شده تا
بازسازی جدول CHECK ندارند (SQLite اجازهٔ افزودن CHECK با ALTER ندارد) — به‌عنوان
محدودیت مستند شد، نه مفروضِ پنهان.

## ۵. Tests (فرمان → نتیجه)

| فرمان | نتیجه |
|---|---|
| `python -m pytest tests/ -q` (با QT_QPA_PLATFORM=offscreen) | **120 passed** |
| `python verify_fixes16.py` | **101/101** |
| `python verify_fixes17.py` | **43/43** |
| `python verify_fixes18.py` | **78/78** (A: پیوست ۲۶ · B: سال ۱۴ · C: ناوبری/کنتراست ۱۰ · D: رگرسیون نهایی ۲۸) |
| `python -m ruff check .` | All checks passed |

*(اجرای Qt در این محیط با کتابخانه‌های جانشین بیرون از مخزن:
`LD_LIBRARY_PATH=/home/user/qtstub/lib QT_QPA_PLATFORM=offscreen`)*

## ۶. Remaining (باقی‌مانده با دلیل واقعی)

1. **اجرای واقعی GUI** — `NOT_TESTED - GUI EXECUTION REQUIRED`: کلیک موس
   واقعی، QFileDialog سیستمی، بازکردن فایل با برنامهٔ خارجی، ورود/خروج با
   ری‌استارت واقعی فرایند. مسیر headless معادل هر ردیف با هندلر واقعی
   صفحه آزموده و سبز است؛ چک‌لیست دستی (با موارد جدید ۷/۸/۹):
   `docs/gui_test_checklist_fa.md`.
2. **BUG-NAV-02** — `DESIGN DECISION REQUIRED`: سیاست دسترسی محصول برای
   مشاوره/فعالیت/اهداف در مخزن وجود ندارد و Agent حق ابداع نداشت (DD-1).
3. **CHECK در DB قدیمی** — محدودیت مستند SQLite (نیاز به بازسازی جدول؛
   خارج از قلمرو «بدون افزودن قابلیت»).

## ۷. Regression (اثبات برقراری fixهای قبلی)

فهرست بند ۴۲ («دوباره حل نکن») با اجرای مجدد verify16 + verify17 بعد از
**هر** مرحله سبز ماند: تراکنش migration، Online Backup، rollback ایمنی
بازیابی، ایمنی حذف پیوست، ماندگاری auto-backup، workflow پیشنهاد→مداخله،
پیشرفت هدف، حفظ پروندهٔ تاریخی، فیلتر سال قبل از LIMIT، خروجی کامل
دانش‌آموزان، دامنهٔ سال داشبورد، ارتقاء/تکرار پایه، حذف کد مرده، ممیزی SQL،
مدیریت استثنا. علاوه بر آن، verify18 §D رگرسیون شش‌گزارشی با فایل واقعی،
AI export چهار قالب، داشبورد دوساله، کلمپ پیشرفت هدف، چرخهٔ
downgrade/شکست‌میانی/upgrade و constraint هر دو دیتابیس را اضافه می‌کند.

## ۸. معیارهای پذیرش (بند ۴۱) — وضعیت

همهٔ ۱۸ معیار برقرارند (جزئیات در `docs/master_fix_report.json` →
`acceptance_criteria_41`). سه مورد «Remaining» بالایی صریح ثبت شده‌اند،
نه پنهان.
