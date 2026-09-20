# گزارش فنی دور شانزدهم — عیب‌یابی و اصلاح کامل (مأموریت ۳۸ بندی)

سند تجمعی است و با هر مرحله تکمیل می‌شود. قالب هر ایراد همان قالب بند ۳۳
مأموریت است؛ اولویت‌ها طبق بند ۳۴ (P0 تا P4). هیچ امتیاز/رتبهٔ کلی به
برنامه داده نمی‌شود.

**محدودیت محیط اجرا (بند ۳۷-۱۴):** Qt در این محیط فقط به‌صورت offscreen و
با stub اجرا می‌شود. صفحه‌ها ساخته می‌شوند و handlerها برنامه‌ای صدا زده
می‌شوند و دیتابیس/فایل قبل و بعد سنجیده می‌شود؛ اما کلیک واقعی کاربر،
file picker و دیالوگ‌های modal اجرا نمی‌شوند. هر قابلیتی که فقط از این راه
قابل اثبات است با `NOT_TESTED - GUI EXECUTION REQUIRED` علامت می‌خورد.

## مرحله‌بندی

| مرحله | موضوع | بندهای مأموریت | وضعیت |
|---|---|---|---|
| ۱ | Migration، تست‌های قدیمی، نسخهٔ پایتون | ۴، ۵، ۶، ۱۵، ۲۲ (بخش migration) | **انجام شد** (این سند، بخش ۱) |
| ۲ | Backup/Restore و file handling | ۱۱، ۱۲، ۲۵ | — |
| ۳ | Inventory کامل صفحات (`views/pages` + `main_window`)، کنتراست، Signal/Slot | ۲، ۳، ۱۰، ۱۸، ۱۹، ۳۶ | — |
| ۴ | دیالوگ‌ها/ویجت‌ها، Screening، Recommendation، Attachment، Thread/Race | ۷، ۸، ۹، ۲۰، ۲۱، ۳۲ | — |
| ۵ | Exception/Return/Transaction/DAL/Constraints/Import-Export/Consistency | ۱۶، ۱۷، ۲۲، ۲۳، ۲۴، ۲۶، ۳۰، ۳۱ | — |
| ۶ | Dead code، وابستگی‌ها، لایهٔ سرویس، ارزیابی تست‌ها، گزارش نهایی | ۱۳، ۱۴، ۲۷، ۲۸، ۲۹، ۳۳، ۳۴، ۳۷، ۳۸ | — |

تصمیم‌های کاربر پیش از شروع: Screening و RecommendationWidget فعلاً فقط
گزارش وضعیت (UNREACHABLE / DEAD_CODE) — تصمیم ساخت/حذف بعداً.

---

# بخش ۱ — مرحلهٔ ۱: Migration، تست‌های قدیمی، نسخهٔ پایتون

پایه: کامیت `5e9a9b5`. فایل‌های تغییریافته: `database/migrations/manager.py`،
`database/connection.py` (فقط لاگ شکست migration)، `main.py`،
`tests/test_dal.py`، `tests/test_services.py`، `README.md`،
`verify_fixes15.py` (تطبیق بررسی G2 با قرارداد جدید کشف migration)،
`verify_fixes16.py` (جدید — ۱۵ بررسی کارکردی با پیش/پس‌شرط).

## وضعیت زنجیره (قالب بند ۲)

```text
نام قابلیت:   ارتقاء/بازگشت نسخهٔ دیتابیس هنگام راه‌اندازی
صفحه/Widget:  ندارد (راه‌اندازی برنامه، main.py → DatabaseConnection)
دکمه/Event:   اجرای برنامه / python database/migrations/manager.py
Handler:      DatabaseConnection._initialize_database → _migrate_database
Service:      MigrationManager.migrate → _run_step
DAL:          —
Database:     migration_vN.upgrade/downgrade + db_version
خروجی:        نسخهٔ ثبت‌شده == اسکیمای واقعی؛ در شکست: خطا + لاگ + پیام به کاربر
وضعیت:        VERIFIED (پس از اصلاح؛ verify16 §A، verify14 §D، verify12 §H)
```

## [BUG-001]

### بخش
```text
database/migrations/manager.py
class MigrationManager
function migrate (مسیر Downgrade)
```
### وضعیت
`BROKEN` (P1 — ناسازگاری اسکیما/متادیتا)
### مشکل
در مسیر بازگشت، ابتدا `set_version(version - 1)` اجرا می‌شد و بعد
`downgrade()`؛ اگر downgrade شکست می‌خورد، اسکیما در نسخهٔ بالاتر می‌ماند ولی
شمارهٔ ثبت‌شده پایین رفته بود.
### علت فنی
ترتیب اشتباه دو عمل و نبود تراکنش صریح دور گام.
### اثر
```text
Schema واقعی = 9 ، Metadata = 8  →  در راه‌اندازی بعدی migration_v9 دوباره اجرا می‌شود
```
### اصلاح لازم / پیاده‌سازی
`_run_step(connection, module, version, direction, new_version)`:
`BEGIN` صریح ← `downgrade()`/`upgrade()` ← `set_version(new_version)` ←
commit؛ در شکست: `rollback()` و `MigrationStepError(version, direction, cause)`.
### تست لازم
`verify_fixes16.py` §A5 (downgrade موفق ۳→۱: ترتیب v3 سپس v2، جدول‌ها حذف،
نسخه ۱) و §A6 (downgrade v3 شکست می‌خورد: نسخه ۳ می‌ماند، جدول `t3` سر جایش،
جدول نیمه‌کارهٔ `downgrade_probe_3` با rollback نیست، v2 اصلاً اجرا نمی‌شود،
تراکنش باز نمی‌ماند).
### نتیجه مورد انتظار
شمارهٔ نسخه فقط پس از موفقیت کامل همان گام تغییر می‌کند.
```text
BEFORE: نسخه قبل از downgrade کم می‌شد
FIX:    _run_step با ترتیب درست + تراکنش + rollback
AFTER:  verify16 A5/A6 سبز؛ probe واقعی: 9→8→9 روی migrationهای واقعی
STATUS: FIXED
```

## [BUG-002]

### بخش
```text
database/migrations/manager.py
function _discover_migrations
```
### وضعیت
`PARTIALLY_BROKEN` (P2)
### مشکل
`for version in range(1, 100)` + `except ImportError: continue`: فایلی که
وجود داشت ولی یکی از importهای داخلی‌اش شکست می‌خورد، «وجود ندارد» تلقی و
بعداً به‌صورت گمراه‌کننده «نسخهٔ گمشده» گزارش می‌شد؛ سقف ۱۰۰ هم ثابت بود.
### علت فنی
کشف با حدس‌زدن نام ماژول به‌جای خواندن فایل‌سیستم؛ ImportError داخلی از
«ماژول نیست» قابل تفکیک نبود.
### اثر
خطای واقعی (مثلاً وابستگی نصب‌نشده در migration) پنهان و با پیام اشتباه
جایگزین می‌شد.
### اصلاح لازم / پیاده‌سازی
پیمایش پوشهٔ بسته و استخراج شماره از نام فایل با
`^migration_v(\d+)\.py$` (بدون سقف)؛ هر فایلِ موجود که import نشود یا
`upgrade` نداشته باشد → `MigrationLoadError(filename, reason)` با
`__cause__` و `logger.error(..., exc_info=True)`. پارامتر اختیاری `directory`
برای آزمون پوشه‌های دیگر (بارگذاری از مسیر فایل).
### تست لازم
verify16 §A1 (پوشهٔ موقت با v1, v2, v7, v100 و فایل‌های نامربوط → دقیقاً
{1,2,7,100})، §A2 (import داخلی شکست‌خورده → MigrationLoadError با
ImportError به‌عنوان علت و رکورد ERROR با traceback)، §A3 (بدون upgrade)،
§A4 (نسخهٔ واقعاً گمشده همچنان MigrationMissingError پیش از اجرای هر گام)،
§A9 (بستهٔ واقعی = فایل‌های روی دیسک).
```text
BEFORE: migration خراب = «وجود ندارد»؛ سقف ۱۰۰
FIX:    کشف از فایل‌سیستم + MigrationLoadError
AFTER:  verify16 A1–A4, A9 سبز
STATUS: FIXED
```

## [BUG-003]

### بخش
```text
database/migrations/manager.py
MigrationManager.migrate / set_version
```
### وضعیت
`PARTIALLY_BROKEN` (P2 — Database consistency)
### مشکل
گام‌های migration بدون تراکنش صریح اجرا می‌شدند. `sqlite3` پایتون فقط پیش از
INSERT/UPDATE/DELETE تراکنش ضمنی باز می‌کند؛ DDL (CREATE/ALTER/DROP) در
autocommit اجرا می‌شود، پس شکست وسط یک گام، اسکیمای نیمه‌کاره می‌گذاشت.
`set_version` هم سه دستور (DROP/CREATE/INSERT) را بدون تراکنش واحد اجرا می‌کرد.
### اصلاح لازم / پیاده‌سازی
`_begin_transaction(connection)` (BEGIN اگر تراکنش باز نیست) پیش از هر گام و
داخل `set_version`؛ rollback در شکست.
**محدودیت شفاف:** اگر خودِ ماژول migration وسط کار `connection.commit()`
بزند (همهٔ migrationهای فعلی در پایان خود commit می‌کنند)، آنچه تا آن نقطه
commit شده قابل بازگشت نیست؛ ولی شمارهٔ نسخه باز هم فقط پس از موفقیت کامل
گام نوشته می‌شود.
### تست لازم
verify16 §A7 (ارتقاء ۱→۳ که v3 پس از CREATE TABLE شکست می‌خورد: v2 اعمال و
نسخه ۲ ثبت، `t3` وجود ندارد، نسخه هرگز ۳ نمی‌شود، تراکنش باز نمی‌ماند).
```text
STATUS: FIXED (با محدودیت مستند برای commit داخلی ماژول‌ها)
```

## [BUG-004]

### بخش
```text
database/migrations/manager.py — همهٔ print()های اجرایی
database/connection.py — _migrate_database (شکست بدون traceback در لاگ)
```
### وضعیت
`PARTIALLY_BROKEN` (P3 — قابلیت تشخیص در production)
### مشکل
پیشرفت/خطای migration فقط `print` می‌شد؛ در اجرای پنجره‌ای دیده نمی‌شد و
traceback نداشت.
### اصلاح
`logger.info/warning/error(..., exc_info=True)` در manager؛ CLI
`run_migration()` علاوه بر لاگ، در کنسول هم چاپ می‌کند و مقدار بولی
برمی‌گرداند؛ `_migrate_database` شکست را با traceback در لاگ ثبت می‌کند و
مثل قبل خطا را بالا می‌فرستد.
### تست لازم
verify16 §A10 (بدون print در MigrationManager/کشف؛ رکورد INFO در اجرای موفق؛
stdout خالی)، §A2/§A6 (ERROR با `exc_info`).
```text
STATUS: FIXED
```

## [BUG-005]

### بخش
```text
database/migrations/manager.py — migrate (Downgrade)، وقتی ماژول downgrade ندارد
```
### وضعیت
`BROKEN` (P2)
### مشکل
`if hasattr(module, 'downgrade')` — اگر ماژول downgrade نداشت، شمارهٔ نسخه
بی‌سروصدا کم می‌شد بدون هیچ تغییری در اسکیما.
### اصلاح
`_run_step` در نبود تابع، `MigrationLoadError` با پیام روشن می‌دهد و نسخه
دست نمی‌خورد.
### تست لازم
verify16 §A8.
```text
STATUS: FIXED
```

## [BUG-006]

### بخش
```text
main.py
function main — بلوک except Exception
```
### وضعیت
`BROKEN` (P1 — خطای واقعی راه‌اندازی هرگز به کاربر نمی‌رسید)
### مشکل
اتصال دیتابیس و Migration در «مرحلهٔ ۲» و **پیش از** ساخت `QApplication`
انجام می‌شود؛ اگر شکست بخورند، بلوک except یک `QMessageBox` می‌سازد که بدون
QApplication ممکن نیست: فرایند با
`QWidget: Must construct a QApplication before a QWidget` می‌میرد و پیام
«خطا در اجرای برنامه» هرگز نمایش داده نمی‌شود.
### علت فنی
ترتیب ساخت QApplication نسبت به عملیات خطاپذیر + نبود تضمین در مسیر خطا.
### اثر
کاربر فقط بسته‌شدن ناگهانی برنامه را می‌بیند (در اجرای پنجره‌ای حتی خروجی
کنسول هم نیست).
### اصلاح
در مسیر خطا: ثبت خطا با traceback در لاگ برنامه، سپس
`if QApplication.instance() is None: QApplication(sys.argv)` پیش از ساخت
QMessageBox. (ترتیب اصلی راه‌اندازی برای حداقل تغییر دست نخورد.)
### تست لازم
verify16 §A11 (بررسی منبع: ترتیب و لاگ) و §A12 (اثبات سازوکار با زیرفرایند:
QMessageBox بدون QApplication → فرایند می‌میرد و «ALIVE» چاپ نمی‌شود؛ با
QApplication → زنده). اجرای واقعی پنجرهٔ خطا: `NOT_TESTED - GUI EXECUTION REQUIRED`.
```text
STATUS: FIXED
```

## [BUG-007]

### بخش
```text
tests/test_dal.py, tests/test_services.py — run_tests()
```
### وضعیت
`BROKEN` روی Python 3.13 (P3)
### مشکل
۹ فراخوانی `unittest.makeSuite` که در Python 3.13 حذف شده است.
### اصلاح
`unittest.TestLoader().loadTestsFromTestCase(...)`؛ کشف با
`python -m unittest discover -s tests` و pytest هم مثل قبل کار می‌کند.
### تست لازم
verify16 §A13 (بدون makeSuite؛ discover و اجرای مستقیم هر دو فایل با کد خروج ۰ و «OK»).
```text
STATUS: FIXED
```

## [BUG-008]

### بخش
```text
README.md، main.py، ruff.toml — نسخهٔ Python
```
### وضعیت
`PARTIALLY_BROKEN` (P4 — مستندسازی/نگهبان)
### مشکل
فقط «۳.۹ یا بالاتر» بدون سقف و بدون بررسی در زمان اجرا.
### اصلاح
حداقل ۳.۹ با `vermin --eval-annotations` روی ۱۷۷ فایل تأیید شد (خروجی:
«Minimum required versions: 3.9»)؛ README: «۳.۹ تا ۳.۱۳ (توسعه/آزمون روی
۳.۱۱)»؛ `main.py` پیش از import PySide6 نسخهٔ کمتر از ۳.۹ را با پیام روشن رد
می‌کند؛ `ruff.toml` همچنان `py39`.
**صادقانه:** اجرای واقعی روی ۳.۹ و ۳.۱۳ در این محیط ممکن نبود؛ ادعای ۳.۱۳
بر پایهٔ حذف تنها API ناسازگار شناخته‌شده (makeSuite) و تحلیل ایستاست.
### تست لازم
verify16 §A14.
```text
STATUS: FIXED
```

## نتیجهٔ اجرای آزمون‌ها پس از مرحلهٔ ۱

| مجموعه | نتیجه |
|---|---|
| `pytest -q tests` | 26 passed |
| `python -m unittest discover -s tests` | Ran 26 — OK |
| verify_fixes 1 … 15 | 17 / 32 / 50 / 36 / 25 / 34 / 30 / 62 / 38 / 37 / 30 / 43 / 32 / 50 / 44 — همه سبز |
| **verify_fixes16 (مرحلهٔ ۱)** | **15 / 15** |
| `ruff check .` | All checks passed |
| probe واقعی | دیتابیس تازه = نسخه ۹؛ اجبار به ۵ و بازکردن دوباره → ۹ از مسیر جدید؛ ۹→۸→۹ با migrationهای واقعی |

آزمون تغییریافته: `verify_fixes15.py` §G2 — چون کشف migration دیگر با
حدس نام ماژول نیست، سناریوی «ماژول خراب» با پوشهٔ موقت و فایل واقعی
شبیه‌سازی می‌شود و انتظارش به قرارداد جدید (توقف با MigrationLoadError +
traceback در لاگ) تغییر کرد. هیچ آزمونی حذف/غیرفعال نشده است.

## بندهای مأموریت که در این مرحله بسته شدند
۴ (ترتیب Downgrade + تراکنش + تست هر دو سناریو)، ۵ (logging با traceback)،
۶ (کشف پویا + تفکیک «نیست» از «خراب»)، ۱۵ (makeSuite + نسخهٔ پایتون)،
۲۲ فقط برای Migration (تراکنش/rollback گام‌ها). بند ۳۵ رعایت شد: API عمومی
`MigrationManager.migrate/set_version/get_current_version` و امضای
`_discover_migrations()` بدون آرگومان دست‌نخورده ماند.
