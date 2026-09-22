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
| ۲ | Backup/Restore و file handling | ۱۱، ۱۲، ۲۵ | **انجام شد** (بخش ۲) |
| ۳ | Inventory کامل صفحات (`views/pages` + `main_window`)، کنتراست، Signal/Slot؛ دیالوگ‌ها/ویجت‌ها | ۲، ۳، ۱۰، ۱۴، ۱۸، ۱۹، ۳۶ | **۳-الف و ۳-ب انجام شد** (بخش‌های ۳ و ۴) |
| ۴ | Attachment (زنجیرهٔ کامل)، Thread/Worker، Race، وضعیت Screening/Recommendation | ۷، ۸، ۹، ۲۰، ۲۱، ۳۲ | **انجام شد** (بخش ۵) |
| ۵ | Exception/Return/Transaction/DAL/Constraints/Import-Export/Consistency | ۱۶، ۱۷، ۲۲، ۲۳، ۲۴، ۲۶، ۳۰، ۳۱ | **انجام شد** (بخش ۶) |
| ۶ | Dead code، وابستگی‌ها، لایهٔ سرویس، ارزیابی تست‌ها، گزارش نهایی | ۱۳، ۱۴، ۲۷، ۲۸، ۲۹، ۳۳، ۳۴، ۳۷، ۳۸ | **انجام شد** (بخش‌های ۷ و ۸) |

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

---

# بخش ۲ — مرحلهٔ ۲: Backup/Restore و file handling

پایه: کامیت `df7c95d`. فایل‌های تغییریافته: `utils/backup.py`،
`config/settings.py` (`BACKUP_DIR`/`LEGACY_BACKUP_DIR`)، `views/pages/backup_page.py`،
`views/pages/settings_page.py` (شروع/توقف پشتیبان خودکار)، `.gitignore`،
`verify_fixes16.py` (§B، ۱۲ بررسی کارکردی). سه فایل `.partobak` که در
`views/backups/` **داخل مخزن** ردیابی می‌شدند از ایندکس git خارج شدند (روی
دیسک می‌مانند و با اولین بازکردن صفحهٔ پشتیبان‌گیری به `backups/` منتقل
می‌شوند).

## وضعیت زنجیره‌ها (قالب بند ۲)

| قابلیت | صفحه/Widget | دکمه | Handler | Service/Manager | Database/File | خروجی | وضعیت |
|---|---|---|---|---|---|---|---|
| ایجاد پشتیبان | BackupPage | `create_btn` | `create_backup` → `_start_worker("create")` | `BackupWorker.run` → `BackupManager.create_backup` | اسنپ‌شات online-backup → ZIP اتمیک + `.sha256` | پیام موفقیت + `load_backups` (+۱ ردیف) | **VERIFIED** (verify16 B12: offscreen، فایل روی دیسک، جدول +۱) |
| بازیابی از فهرست | BackupPage | دکمهٔ ردیف «🔄 بازیابی» | `restore_backup(b)` → تأیید → worker | `restore_backup` | جایگزینی DB زیر قفل + پیوست‌ها | پیام + تازه‌سازی | **VERIFIED** در سطح Manager با پیش/پس‌شرط DB و پیوست (B7/B8)؛ دیالوگ تأیید: `NOT_TESTED - GUI EXECUTION REQUIRED` |
| بازیابی از فایل خارجی | BackupPage | `restore_btn` | `restore_from_file` (QFileDialog) | همان | همان | همان | Backend VERIFIED؛ انتخاب فایل: `NOT_TESTED - GUI EXECUTION REQUIRED` |
| حذف پشتیبان | BackupPage | دکمهٔ ردیف «🗑️» | `delete_backup(b)` → worker | `delete_backup` (canonical + پسوند + sidecar) | حذف فایل + `.sha256` | پیام + جدول −۱ | **VERIFIED** (B5/B6/B12) |
| تازه‌سازی فهرست | BackupPage | `refresh_btn` | `load_backups` | `list_backups` (وضعیت واقعی) | خواندن پوشه | جدول با وضعیت واقعی | **VERIFIED** (B4/B12) |
| شروع پشتیبان خودکار | SettingsPage | `start_auto_backup_btn` | `start_auto_backup` | `schedule_auto_backup` → `AutoBackupHandle` | فایل‌های `auto_backup_*` | وضعیت «فعال» | **VERIFIED** در سطح Manager (B10)؛ کلیک: `NOT_TESTED - GUI EXECUTION REQUIRED` |
| توقف پشتیبان خودکار | SettingsPage | `stop_auto_backup_btn` | `stop_auto_backup` | `AutoBackupHandle.stop()` | — | وضعیت «غیرفعال» | قبلاً **BROKEN (دکمهٔ تزئینی)** → اکنون VERIFIED در سطح Manager (B10) |

## [BUG-009]
### بخش
```text
utils/backup.py — BackupManager.delete_backup
```
### وضعیت
`BROKEN` (P0 — Security / Data loss)
### مشکل
مسیر ورودی مستقیم به `os.remove` داده می‌شد: بدون canonical path، بدون بررسی
اینکه داخل پوشهٔ پشتیبان است، بدون بررسی پسوند؛ فایل `.sha256` کناری هم هرگز
حذف نمی‌شد (تلنبار sidecarهای یتیم).
### علت فنی
اعتماد کامل به آرگومان `backup_file`.
### اثر
هر مسیری که به این متد برسد (پیوند نمادین داخل پوشه، مسیر با `..`، مسیر
دیگر) قابل حذف بود.
### اصلاح / پیاده‌سازی
`_resolve_backup_path`: `realpath` → باید داخل `realpath(backup_dir)` باشد
(`os.path.commonpath`)، پسوند `.partobak`، فایل معمولی، نه symlink. سپس حذف
فایل، ثبت در لاگ، حذف sidecar؛ اگر حذف sidecar شکست بخورد →
`(False, پیام صریح)` + `logger.warning`.
### تست
verify16 B5 (بیرون پوشه / `..` / پسوند غلط / symlink / خود پوشه → رد و
دست‌نخورده؛ معتبر → فایل و sidecar هر دو حذف)، B6 (شکست sidecar → نتیجهٔ
صریح False، فایل اصلی حذف‌شده).
```text
STATUS: FIXED
```

## [BUG-010]
### بخش
```text
utils/backup.py — create_backup
```
### وضعیت
`PARTIALLY_BROKEN` (P2 — فایل نیمه‌کاره / پیمایش مسیر در نام)
### مشکل
ZIP مستقیماً روی مسیر نهایی نوشته می‌شد (شکست وسط کار = `.partobak` ناقص
در فهرست)؛ اسنپ‌شات موقت در مسیر خطا پاک نمی‌شد؛ `name` بدون امن‌سازی به
`os.path.join` می‌رفت (`../../x` بیرون پوشه می‌ساخت).
### اصلاح
`sanitize_backup_name` (فقط `\w-.`، بدون جداکننده/`..`)؛ نوشتن در
`<file>.tmp` + `testzip` + `os.replace`؛ `finally` همهٔ موقت‌ها را پاک می‌کند؛
`checksum_saved` در نتیجه.
### تست
B1 (نام با پیمایش → فقط داخل پوشه)، B2 (بدون فایل موقت)، B3 (شکست تزریق‌شده →
`success=False` و پوشه دقیقاً مثل قبل).
```text
STATUS: FIXED
```

## [BUG-011]
### بخش
```text
utils/backup.py — create_backup (اسنپ‌شات)
```
### وضعیت
`PARTIALLY_BROKEN` (P3 — نشت فایل)
### مشکل
**کشف حین آزمون:** کنار هر پشتیبان دو فایل `<name>.db.tmp-wal` و
`<name>.db.tmp-shm` در پوشهٔ پشتیبان جا می‌ماند (اسنپ‌شات حالت WAL منبع را
به ارث می‌برد و راستی‌آزمایی فقط‌خواندنی ژورنال‌ها را نمی‌بست).
### اصلاح
`PRAGMA journal_mode=DELETE` روی اسنپ‌شات پس از backup (فایل خودبسنده) +
پاک‌سازی `-wal/-shm/-journal` در `finally`.
### تست
B2 (فهرست پوشه بدون هیچ `-wal/-shm`).
```text
STATUS: FIXED
```

## [BUG-012]
### بخش
```text
utils/backup.py — _calculate_checksum / sidecar .sha256
```
### وضعیت
`PARTIALLY_BROKEN` (P3)
### مشکل
فایل کناری با پسوند `.sha256` حاوی **MD5** بود.
### اصلاح
SHA-256 برای پشتیبان‌های جدید؛ `_checksum_matches` مقدار ۳۲ رقمی قدیمی را با
MD5 مقایسه می‌کند تا پشتیبان‌های موجود همچنان راستی‌آزمایی شوند.
### تست
B2 (مقدار sidecar == sha256 فایل).
```text
STATUS: FIXED
```

## [BUG-013]
### بخش
```text
views/pages/backup_page.py — load_backups (ستون «وضعیت»)
utils/backup.py — list_backups
```
### وضعیت
`BROKEN` (P2 — UI ادعای سلامت بدون بررسی)
### مشکل
برای هر فایل بدون هیچ بررسی «✅ سالم» نوشته می‌شد؛ حتی برای فایل غیر-ZIP.
### اصلاح
`backup_status()` → `ok / no_checksum / mismatch / corrupt`؛ جدول برچسب و
رنگ واقعی نشان می‌دهد و برای فایل خراب دکمهٔ بازیابی غیرفعال است.
### تست
B4 (چهار وضعیت با فایل‌های واقعی)، B12 (جدول).
```text
STATUS: FIXED
```

## [BUG-014]
### بخش
```text
utils/backup.py — restore_backup (پیوست‌ها، پاک‌سازی)
```
### وضعیت
`PARTIALLY_BROKEN` (P2 — Data loss احتمالی)
### مشکل
پوشهٔ پیوست‌های فعلی با `rmtree` حذف و بعد `copytree` می‌شد؛ شکست کپی = از
دست رفتن پیوست‌های قبلی + پیوست‌های جدید ناقص؛ در استثنا، پوشهٔ استخراج
موقت پاک نمی‌شد؛ نتیجه در حالت «DB بازیابی شد ولی پیوست‌ها نه» شفاف نبود.
### اصلاح
`_swap_attachments_dir`: کنارگذاشتن پوشهٔ فعلی (`.restore_safety`) → کپی →
حذف پوشهٔ کناری؛ در شکست، همان پوشه برمی‌گردد؛ نتیجه
`attachments_restored/attachments_error` و پیام ⚠️؛ `finally` پوشهٔ
`temp_restore` را همیشه پاک می‌کند.
### تست
B7 (بازیابی کامل با پیش/پس‌شرط: تعداد دانش‌آموزان، فایل پیوست حذف‌شده
برمی‌گردد، بدون پوشهٔ موقت/ایمنی)، B8 (`copytree` تزریق‌شکست → DB بازیابی،
پیوست‌های قبلی سالم، نتیجهٔ صریح).
```text
STATUS: FIXED
```

## [BUG-015]
### بخش
```text
views/pages/settings_page.py — stop_auto_backup / start_auto_backup
utils/backup.py — schedule_auto_backup
```
### وضعیت
`BROKEN` (P1 — دکمهٔ تزئینی با پیام موفقیت دروغین)
### مشکل
«توقف پشتیبان‌گیری خودکار» فقط مرجع نخ را `None` می‌کرد و پیام «متوقف شد»
می‌داد؛ نخ (`while True` + `sleep`) تا بستن برنامه ادامه می‌داد. شروع
دوباره پس از «توقف» = دو نخ هم‌زمان. کاربر پشتیبان خودکار هم `user_id=1`
(مدیر) ثبت می‌شد.
### اصلاح
`AutoBackupHandle` با `threading.Event`؛ حلقه روی `wait(interval)`؛ `stop()`
واقعاً نخ را تمام می‌کند و نتیجه‌اش را برمی‌گرداند؛ شروع دوباره اول قبلی را
متوقف می‌کند؛ `user_id=None` (سیستم).
### تست
B10 (پشتیبان ساخته می‌شود، `stop()` → نخ مرده، پس از آن فایل جدیدی ساخته
نمی‌شود). کلیک واقعی دکمه‌ها: `NOT_TESTED - GUI EXECUTION REQUIRED`.
```text
STATUS: FIXED
```

## [BUG-016]
### بخش
```text
views/pages/backup_page.py, views/pages/settings_page.py — محاسبهٔ پوشهٔ پشتیبان
مخزن git — views/backups/*.partobak
```
### وضعیت
`PARTIALLY_BROKEN` (P2 — دادهٔ کاربر داخل درخت کد و داخل مخزن)
### مشکل
دو صفحه هر کدام جداگانه `views/backups` را می‌ساختند (داخل بستهٔ کد)؛ سه
فایل پشتیبان واقعی در git ردیابی شده بود؛ `.gitignore` هیچ الگویی برای
پشتیبان نداشت.
### اصلاح
`config.settings.BACKUP_DIR = <BASE_DIR>/backups` (کنار دیتابیس و پیوست‌ها)
برای هر دو صفحه؛ `adopt_legacy_backups` فایل‌های پوشهٔ قدیمی را یک‌بار
منتقل می‌کند (بدون بازنویسی؛ لاگ قدیمی به لاگ فعلی افزوده می‌شود)؛
`.gitignore`: `backups/`, `*.partobak`, `*.partobak.sha256`؛ سه فایل از ایندکس
خارج شدند (`git rm --cached`، روی دیسک ماندند).
### تست
B9 (انتقال بدون بازنویسی + ادغام لاگ)، B11 (منبع + `git ls-files` خالی).
```text
STATUS: FIXED
```

## [BUG-017]
### بخش
```text
views/pages/backup_page.py — BackupWorker (سیگنال finished) و مدیریت worker
```
### وضعیت
`PARTIALLY_BROKEN` (P2 — Signal/Slot و Race)
### مشکل
`finished = Signal(bool, str)` سیگنال داخلی `QThread.finished()` را با امضای
متفاوت بازتعریف می‌کرد؛ `self.worker` بدون بررسی جایگزین می‌شد و دکمه‌های
ردیف جدول هنگام عملیات غیرفعال نمی‌شدند → کلیک وسط پشتیبان‌گیری = از دست
رفتن QThread در حال اجرا و دو عملیات هم‌زمان روی فایل‌ها؛ استثنای نخ کارگر
صفحه را با دکمه‌های غیرفعال رها می‌کرد.
### اصلاح
`operation_finished`؛ `_operation_in_progress()` در هر ۴ عمل؛
`set_buttons_enabled` جدول و دکمهٔ تازه‌سازی را هم قفل می‌کند؛ `run()` هر
استثنا را به سیگنال شکست تبدیل می‌کند؛ دکمهٔ ردیف «بازیابی» زرد-روی-زرد
(`#F4C542` روی `#F4D35E`) به متن تیره اصلاح شد.
### تست
B11 (منبع)، B12 (offscreen: ایجاد و حذف از مسیر UI با تازه‌سازی جدول و
فعال‌شدن دوبارهٔ دکمه‌ها).
```text
STATUS: FIXED
```

## چک‌لیست بند ۲۵ برای مسیرهای پشتیبان/بازیابی

| مورد | وضعیت |
|---|---|
| exists | فایل دیتابیس، فایل پشتیبان، عضو `database/partow.db` و پوشهٔ پیوست‌ها پیش از هر تغییر بررسی می‌شوند |
| permissions | همهٔ `OSError`ها به نتیجهٔ صریح `success=False`/`(False, msg)` تبدیل و در لاگ (با traceback) ثبت می‌شوند |
| encoding | sidecar و `backup_log.txt` با UTF-8 صریح؛ متادیتا `ensure_ascii=False` |
| locking | جایگزینی دیتابیس زیر `DB_THREAD_LOCK` پس از `close_all` همهٔ نخ‌ها |
| atomic write | ZIP: `.tmp` + `testzip` + `os.replace`؛ دیتابیس: `os.replace` به `.restore_safety` و برگشت در شکست؛ پیوست‌ها: همان الگو |
| temporary file | اسنپ‌شات و ZIP موقت داخل همان پوشه؛ `temp_restore` داخل پوشهٔ پشتیبان |
| cleanup | `finally` در create و restore؛ ژورنال‌های اسنپ‌شات؛ پوشه‌های ایمنی پس از موفقیت |

## نتیجهٔ اجرای آزمون‌ها پس از مرحلهٔ ۲

| مجموعه | نتیجه |
|---|---|
| `pytest -q tests` | 26 passed |
| verify_fixes 1 … 15 | همه سبز (بدون تغییر) |
| **verify_fixes16 (مرحله‌های ۱ و ۲)** | **27 / 27** |
| `ruff check .` | All checks passed |

هیچ آزمونی حذف/غیرفعال یا تغییر داده نشده است.

## بندهای مأموریت که در این مرحله بسته شدند
۱۱ (حذف sidecar با نتیجهٔ صریح؛ online backup API دست‌نخورده)، ۱۲ (canonical
path + داخل پوشه + پسوند)، ۲۵ برای پشتیبان/بازیابی/پیوست‌ها (Export/Report/
Import در مرحله‌های ۵). به‌علاوه از بندهای دیگر: ۱۸/۳۶ (دکمهٔ توقف تزئینی)،
۱۹ (بازتعریف `finished`)، ۳۲ (race در صفحهٔ پشتیبان)، ۱۷ (نتایج صریح).

---

# بخش ۳ — مرحلهٔ ۳-الف: Inventory صفحات (`views/pages` + `main_window`)

پایه: کامیت `a5a1cc8`. ابزار جدید: `tools/ui_inventory.py` (تحلیل ایستای AST
هر دکمه → connect → handler → طبقه‌بندی؛ سیگنال‌های سفارشی → emit → گیرنده؛
connect داخل متدهای بارگذاری). خروجی کامل در `docs/ui_inventory_16.md`.

## روش (بند ۲ و ۳ — نه فقط «clicked.connect دارد»)

1. **ایستا:** ۱۷۷ `QPushButton(`، ۱۸۰ `clicked.connect`، ۳۹ `Signal(`، ۱۹۹ handler
   متصل در کل `views/`. هر handler به‌صورت بازگشتی تا رسیدن به سرویس/DAL/فایل/
   دیالوگ/سیگنال دنبال می‌شود؛ طبقه‌ها: BACKEND / DIALOG / SIGNAL / NAV /
   UI_ONLY / MSG_ONLY / STUB / NO_CONNECT / MISSING.
2. **پویا (offscreen):** هر ۲۲ کلاس صفحه + `MainWindow` (با ورود شبیه‌سازی‌شده)
   روی دیتابیس موقتِ seed‌شده ساخته می‌شوند؛ ردیف اول همهٔ جدول‌ها انتخاب
   می‌شود؛ **۱۶۷ handler** (بدون آرگومان، با ردیف انتخاب‌شده، یا با شیء ردیف/
   آیتم) واقعاً اجرا می‌شوند؛ دیالوگ‌ها با Rejected، سؤال‌ها با No، انتخاب فایل
   خالی. معیار شکست: استثنا یا `QMessageBox.critical`. نتیجه پس از اصلاحات:
   **۰ استثنا، ۰ پیام خطا** (verify16 C1/C2).
3. **بازبینی دستی** همهٔ موارد MSG_ONLY/UI_ONLY/NAV.

## وضعیت صفحه‌ها (بند ۳۶)

| صفحه | دکمه‌های نام‌دار | طبقه‌بندی ایستا | بازبینی دستی / وضعیت |
|---|---|---|---|
| `main_window.py` | ۳ (+۱۳ دکمهٔ منو در حلقه) | NAV، UI_ONLY، MSG_ONLY (`logout`) | `logout`: سؤال → ثبت Audit → بستن و اجرای دوبارهٔ فرایند ✔ (سنگین ولی واقعی)؛ **کامبوی سال تحصیلی در هدر: BROKEN/تزئینی** (BUG-023، تصمیم لازم) |
| `academic_structure_page.py` | ۹ | BACKEND=9 | ✏️ ویرایش کلاس قبلاً MSG_ONLY → **FIXED** (BUG-019) |
| `activities_page.py` | ۴ | BACKEND=2، DIALOG=1، MSG_ONLY=1 | 👁️ جزئیات = نمایش دادهٔ رکورد (VERIFIED read-only) |
| `analysis_page.py` | ۳ | BACKEND=2، NAV=1 | VERIFIED |
| `analytics_dashboard.py` | ۱ (+ دابل‌کلیک) | BACKEND | دابل‌کلیک قبلاً «در نسخهٔ بعدی» → **FIXED** (BUG-020) |
| `assign_teacher_page.py` | ۵ | BACKEND=5 | VERIFIED؛ سیگنال `assignment_changed` هرگز emit/دریافت نمی‌شود (کد مرده، بند ۲۷) |
| `backup_page.py` | ۵ | BACKEND=5 | مرحلهٔ ۲ |
| `class_report_page.py` | ۳ | BACKEND=3 | VERIFIED (تولید فایل: مرحلهٔ ۵) |
| `counseling_page.py` | ۵ | BACKEND/DIALOG/SIGNAL | VERIFIED |
| `dashboard_page.py` | ۱ | BACKEND | VERIFIED |
| `followups_page.py` | ۵ | BACKEND=4، MSG_ONLY=1 (👁️) | VERIFIED |
| `goals_page.py` | ۵ | BACKEND/DIALOG/SIGNAL | VERIFIED |
| `indicators_page.py` | ۳ | BACKEND=2، NAV=1 | VERIFIED |
| `interventions_page.py` | ۵ | BACKEND=4، MSG_ONLY=1 (👁️) | VERIFIED |
| `observations_page.py` | ۸ | BACKEND=6، MSG_ONLY=1 (👁️)، UI_ONLY=1 (پاک‌کردن جست‌وجو) | VERIFIED |
| `promotion_page.py` | ۵ | BACKEND=5 | VERIFIED (اجرای واقعی ارتقا: مرحلهٔ ۵ — تراکنش) |
| `reports_page.py` | ۶ | BACKEND/DIALOG/NAV | VERIFIED؛ `select_student` افزوده شد (BUG-021) |
| `settings_page.py` | ۲۰ | BACKEND=20 | «💾 ذخیره اطلاعات مدرسه» قبلاً **تزئینی با موفقیت دروغین** → **FIXED** (BUG-018)؛ ✏️ کلاس → FIXED؛ توقف پشتیبان خودکار → مرحلهٔ ۲ |
| `student_profile_page.py` | ۹ | BACKEND=5، MSG_ONLY=3 (👁️ ×۳)، NAV=1 | «📄 گزارش پرونده» قبلاً فقط پیام → **FIXED** (BUG-021)؛ سیگنال `student_changed` هرگز emit نمی‌شود (کد مرده) |
| `students_page.py` | ۱۰ | BACKEND/DIALOG/SIGNAL | VERIFIED |
| `teacher_performance_page.py` | ۲ | BACKEND=2 | VERIFIED |
| `teacher_report_page.py` | ۳ | BACKEND=3 | VERIFIED |
| `teacher_students_page.py` | ۳ | BACKEND/SIGNAL | VERIFIED |

«VERIFIED» در این جدول یعنی: زنجیرهٔ دکمه → handler → سرویس/DAL از نظر ایستا
کامل است **و** اجرای واقعی handler روی دیتابیس seed‌شده بدون استثنا/پیام خطا
بوده است. صحت عمیق داده (Create/Edit/Delete با پیش/پس‌شرط، تراکنش، Export
فایل واقعی) موضوع مرحله‌های ۵ است. کلیک واقعی موس و دیالوگ‌های modal:
`NOT_TESTED - GUI EXECUTION REQUIRED`.

## [BUG-018]
### بخش
```text
views/pages/settings_page.py — create_school_tab / load_school_info / save_school_info
```
### وضعیت
`BROKEN` (P1 — دکمهٔ تزئینی با موفقیت دروغین + دادهٔ ساختگی)
### مشکل
فرم «اطلاعات مدرسه» همیشه مقادیر ثابت ساختگی را نشان می‌داد، «💾 ذخیره
اطلاعات» فقط پیام «با موفقیت ذخیره شد» می‌داد و هیچ‌چیز ذخیره نمی‌شد؛ برچسب
«این اطلاعات در گزارش‌ها نمایش داده می‌شود» هم نادرست بود (هیچ گزارشی آن را
نمی‌خواند).
### اصلاح
ذخیره/بارگذاری با `QSettings` (همان سازوکار موجودِ تم برنامه؛ بدون جدول/
migration جدید)، `sync()` + بازخوانی و مقایسه پس از نوشتن، خطا → پیام خطا؛
برچسب صادقانه «روی همین دستگاه ذخیره می‌شود».
### تست
verify16 C5: مقادیر → ذخیره → نمونهٔ تازهٔ صفحه همان مقادیر را می‌خواند.
```text
STATUS: FIXED (اتصال به گزارش‌ها عمداً اضافه نشد — قابلیت جدید می‌بود)
```

## [BUG-019]
### بخش
```text
views/pages/settings_page.py, views/pages/academic_structure_page.py — edit_class / add_class
```
### وضعیت
`PARTIALLY_BROKEN` (P2 — backend داشت، UI نداشت؛ حالت ۴)
### مشکل
دکمهٔ ✏️ در جدول کلاس‌ها فقط «این قابلیت در نسخهٔ بعدی کامل می‌شود» می‌گفت،
در حالی که `ClassDAL.update` و `get_by_id` موجود بودند.
### اصلاح
همان فرم افزودن در «حالت ویرایش» استفاده می‌شود: پرشدن فیلدها، تبدیل دکمه به
«💾 ذخیرهٔ تغییرات»، دکمهٔ «انصراف»، `update` + بازخوانی از DB برای تأیید،
بازگشت فرم به حالت افزودن. (در ساختار آموزشی، سال تحصیلی کلاس در ویرایش تغییر
نمی‌کند.)
### تست
verify16 C6 (هر دو صفحه: پرشدن فرم → ذخیره → ردیف `classes` با نام/ظرفیت
جدید → فرم reset).
```text
STATUS: FIXED
```

## [BUG-020]
### بخش
```text
views/pages/analytics_dashboard.py — on_student_double_clicked ؛ views/main_window.py
```
### وضعیت
`BROKEN` (P2 — حالت ۳)
### مشکل
دابل‌کلیک روی دانش‌آموزِ «بدون مشاهده» فقط پیام «در نسخهٔ بعدی» می‌داد؛ شناسهٔ
دانش‌آموز در همان دادهٔ سرویس بود.
### اصلاح
شناسه در `UserRole` ردیف؛ سیگنال `student_selected(int)` (الگوی بقیهٔ
صفحه‌ها)؛ `MainWindow` آن را به `open_student_profile` وصل می‌کند.
### تست
verify16 C4 (emit با شناسهٔ درست → پروندهٔ همان دانش‌آموز باز می‌شود).
```text
STATUS: FIXED
```

## [BUG-021]
### بخش
```text
views/pages/student_profile_page.py — generate_report ؛ views/pages/reports_page.py — select_student ؛ views/main_window.py — open_student_report
```
### وضعیت
`BROKEN` (P3 — حالت ۳)
### مشکل
«📄 گزارش پرونده» فقط پیام «به بخش گزارش‌ها بروید» می‌داد.
### اصلاح
سیگنال `report_requested(student_id)`؛ پنجرهٔ اصلی صفحهٔ گزارش‌ها را باز و
با `ReportsPage.select_student` همان دانش‌آموز را انتخاب می‌کند (گزارش با
همان مسیر موجود بارگذاری می‌شود).
### تست
verify16 C3 (صفحهٔ جاری = گزارش‌ها، کامبو = همان دانش‌آموز، `current_report` پر).
```text
STATUS: FIXED
```

## [BUG-022]
### بخش
```text
۴۰ فایل در views/ (صفحه‌ها، دیالوگ‌ها، ویجت‌ها) — بلوک‌های setStyleSheet
```
### وضعیت
`PARTIALLY_BROKEN` (P2 — خوانایی؛ در چند مورد متن عملاً نامرئی)
### مشکل
اسکن نسبت کنتراست WCAG روی همهٔ جفت‌های `color`/`background-color` در یک بلوک:
**۱۰۴ مورد زیر ۳:۱** — از جمله متن هم‌رنگ زمینه (نامرئی): دکمهٔ Generate
پیشنهادها (`#0B2E4F` روی `#0B2E4F`)، دکمه‌های «🔄 به‌روزرسانی» داشبورد اصلی و
تحلیلی، برچسب‌های «داده ناکافی» در ۶ صفحه (`#C62828` روی `#C62828`)، و طلایی
`#F4C542` روی سبز/زرد/نارنجی (نسبت ۱٫۱ تا ۱٫۵) در ۸۲ دکمه/برچسب.
### اصلاح
قاعده‌مند و بدون بازطراحی: فقط مقدار `color` همان بلوک عوض شد — روی زمینهٔ
سرمه‌ای همان طلایی استاندارد برنامه، روی زمینه‌های روشن `#111111` (که در
همین پروژه استفاده می‌شود)، روی زمینهٔ تیرهٔ اشباع `#FFFFFF`. زمینه‌ها و بقیهٔ
استایل دست‌نخورده.
### تست
verify16 C8: اسکن دوباره → ۰ مورد زیر ۳:۱؛ دکمهٔ Generate پیشنهادها دیگر
هم‌رنگ زمینه نیست.
```text
STATUS: FIXED
```

## [BUG-023] — نیازمند تصمیم
### بخش
```text
views/main_window.py — year_combo / on_year_changed / academic_year_changed
```
### وضعیت
`BROKEN` (P2 — کنترل تزئینی؛ حالت ۵: UI و backend هست، اتصال نیست)
### مشکل
کامبوی «سال تحصیلی» در هدر فقط برچسب را عوض می‌کند و سیگنال
`academic_year_changed` را emit می‌کند که **هیچ گیرنده‌ای ندارد**؛ همهٔ صفحه‌ها
سال فعال دیتابیس (`AcademicYearDAL.get_active`) را می‌خوانند. کاربر سال را
عوض می‌کند و هیچ داده‌ای عوض نمی‌شود.
### گزینه‌ها
(الف) انتخاب در هدر = فعال‌سازی همان سال در دیتابیس (با تأیید؛ سال‌های
بایگانی‌شده مستثنا) + بارگذاری دوبارهٔ صفحه‌ها — تغییر رفتار داده‌ای، نیاز به
تأیید شما؛ (ب) کامبو فقط نمایشی شود (فعال‌سازی در صفحهٔ ساختار آموزشی می‌ماند)؛
(ج) فعلاً فقط گزارش.
```text
STATUS: NOT_FIXED (منتظر تصمیم)
```

## یافته‌های جانبی این مرحله (بدون تغییر کد)
- سیگنال‌های هرگز-emit-نشده: `StudentProfilePage.student_changed`،
  `AcademicStructurePage.assignment_changed`، `AssignTeacherPage.assignment_changed`
  → کد مرده (فهرست بند ۲۷، مرحلهٔ ۶).
- `BackupWorker.progress` تعریف و متصل است ولی هرگز emit نمی‌شود → نوار
  پیشرفت همیشه ۰ (P4، آرایشی).
- `auto_logout` پس از ۳۰ دقیقه بی‌کاری همان `logout` را صدا می‌زند که با
  دیالوگ تأیید شروع می‌شود (خروج خودکار عملاً منتظر کلیک می‌ماند) — P4،
  تغییر رفتار امنیتی بدون تأیید انجام نشد.
- سیگنال‌های بدون گیرنده در دیالوگ‌ها/ویجت‌ها (`attachment_added/deleted`،
  `password_changed`، `assignment_saved`، `filter_applied`، `help_requested`،
  `recommendation_*`) → مرحلهٔ ۳-ب.

## نتیجهٔ اجرای آزمون‌ها پس از مرحلهٔ ۳-الف

| مجموعه | نتیجه |
|---|---|
| `pytest -q tests` | 26 passed |
| verify_fixes 1 … 15 | همه سبز |
| **verify_fixes16 (۱ تا ۳-الف)** | **36 / 36** |
| `ruff check .` | All checks passed |

آزمون تغییریافته: هیچ. (`verify_fixes14` §I یک‌بار به‌خاطر import ابزار
جدید قرمز شد؛ با ساخت بستهٔ `tools/` و import بسته‌ای رفع شد، نه با تغییر آزمون.)

## بندهای مأموریت در این مرحله
۲ و ۳ (Inventory و اجرای واقعی زنجیره‌ها برای صفحه‌ها و پنجرهٔ اصلی)، ۱۰
(کنتراست کل `views/`)، ۱۸ (دکمه‌های تزئینی صفحه‌ها: ۴ مورد رفع، ۱ مورد منتظر
تصمیم)، ۱۹ (ممیزی سیگنال‌ها: صفحه‌ها)، ۳۶ (جدول وضعیت). دیالوگ‌ها/ویجت‌ها در
۳-ب.

---

# بخش ۴ — مرحلهٔ ۳-ب: دیالوگ‌ها (`views/dialogs`) و ویجت‌ها (`views/widgets`)

پایه: کامیت `a746876`. روش: همان Inventory ایستا + **اجرای واقعی فرم‌ها** روی
دیتابیس موقت با پیش/پس‌شرط (بند ۱۴): برای هر فرم، «ایجاد» (شمارش جدول +۱،
مقدار ستون، کلید خارجی درست، سیگنال `*_saved`، `Accepted`) و سپس «ویرایش»
(بارگذاری مقدار قبلی در فرم → ذخیرهٔ مقدار جدید → همان مقدار در DB).

## وضعیت دیالوگ‌ها و ویجت‌ها (بند ۳۶)

| کلاس | مصرف‌کننده در برنامه | آزمون کارکردی (verify16 §D) | وضعیت |
|---|---|---|---|
| `ObservationForm` | observations_page، student_profile_page | D1 ایجاد/ویرایش، D9 انتخاب از درخت شایستگی → `competency_id` در DB | قبلاً **BROKEN** (BUG-024) → VERIFIED |
| `InterventionForm` | interventions_page، student_profile_page | D2 | VERIFIED |
| `FollowUpForm` | followups_page، student_profile_page | D3 (ویرایش) | قبلاً **BROKEN در ویرایش** (BUG-025) → VERIFIED |
| `StudentForm` | students_page | D4 | VERIFIED |
| `GoalForm` | goals_page | D5 | VERIFIED |
| `ActivityForm` | activities_page | D6 | VERIFIED |
| `CounselingSessionForm` | counseling_page | D7 | VERIFIED |
| `AssignTeacherDialog` | academic_structure، assign_teacher، teacher_students | D8 (اختصاص) | VERIFIED برای اختصاص؛ حالت ویرایش اختصاص: `NOT_TESTED` (فقط ساخت) |
| `LoginDialog` | main_window | D10 (رمز غلط/درست) | VERIFIED |
| `ChangePasswordDialog` | main_window، login_dialog | D11 (رمز فعلی غلط → بدون تغییر؛ درست → رمز جدید) | VERIFIED |
| `AdvancedSearchDialog` | students_page | D12 | قبلاً **BROKEN** (BUG-026) → VERIFIED |
| `ExportAIDialog` | reports_page | D13 (۶ قالب فایل واقعی + کپی پرامپت) | VERIFIED |
| `AttachmentDialog` (+ `AttachmentUploadWorker`) | **هیچ** | D16 | **UNREACHABLE** (BUG-027 — تصمیم لازم) |
| `CompetencyTreeWidget` | observation_form | D9 | VERIFIED |
| `NotificationWidget` (زنگولهٔ هدر) | main_window | D14 | VERIFIED — منبعش `ReminderService` (پیگیری‌های در انتظار/معوق) است، نه جدول `notifications` |
| `HelpWidget` | ۶ فرم + help_system | ساخت/نمایش | VERIFIED (نمایش متن) |
| `FilterWidget` (+ `SavedFilterDAL`، جدول `saved_filters`) | **هیچ** | D16 | **DEAD_CODE / UNREACHABLE** (BUG-029) |
| `RecommendationWidget` | **هیچ** | D16 | **DEAD_CODE** (طبق تصمیم شما فقط گزارش) |

## [BUG-024]
### بخش
```text
models/observation.py — validate ؛ services/observation_service.py — create/update_observation
```
### وضعیت
`BROKEN` (P1 — قابلیت اصلی: ثبت مشاهده)
### مشکل
فرم مشاهده «توضیحات تکمیلی» را **اختیاری** و زیر «نمایش فیلدهای بیشتر (اختیاری)»
پنهان کرده است، ولی `Observation.validate()` آن را الزامی (≥۳ نویسه) می‌دانست.
کاربری که فقط فیلدهای الزامیِ نمایان را پر می‌کرد، پس از کلیک «ذخیره» خطای
«خطا در عملیات: توضیحات باید حداقل ۳ کاراکتر باشد» می‌گرفت.
### علت فنی
ناهم‌خوانی قرارداد مدل با فرم پس از حرکت به ساختار سه‌لایه (متن اصلی =
`behavior`)، در حالی که ستون `description` در DB `NOT NULL` است.
### اصلاح
مدل: `description` فقط اگر نوشته شد ≥۳ نویسه؛ `behavior` همچنان الزامی.
سرویس: در نبود توضیحات، متن رفتار در ستون `description` نوشته می‌شود؛ در
ویرایش، اگر توضیحات قبلی همان رفتار قبلی بود، با رفتار جدید هم‌گام می‌شود.
### تست
D1 (فرم بدون توضیحات ثبت می‌شود)، D15 (سرویس: بدون توضیحات → description = رفتار؛
توضیحات کوتاه → خطا؛ رفتار خالی → خطا).
```text
STATUS: FIXED
```

## [BUG-025]
### بخش
```text
views/dialogs/followup_form.py — load_followup_data
```
### وضعیت
`BROKEN` (P1 — ویرایش پیگیری غیرممکن بود)
### مشکل
در حالت ویرایش، (۱) `FollowUpDAL.get_by_id` فقط ستون‌های `followups` را
برمی‌گرداند و `follow.student_id` همیشه `None` بود → دانش‌آموز انتخاب و
مداخلات بارگذاری نمی‌شدند؛ (۲) فهرست مداخلات فقط «مداخلات بدون پیگیری» است و
مداخلهٔ خودِ این پیگیری در آن نبود. نتیجه: هر ذخیره‌ای با «لطفاً یک مداخله
انتخاب کنید» رد می‌شد.
### اصلاح
دانش‌آموز از مداخله ← پرونده به دست می‌آید؛ مداخلهٔ خودِ پیگیری به فهرست
اضافه و انتخاب می‌شود.
### تست
D3: فرم ویرایش، مداخلهٔ خودش و دانش‌آموز را نشان می‌دهد؛ ذخیره → مقدار جدید در DB.
```text
STATUS: FIXED
```

## [BUG-026]
### بخش
```text
views/dialogs/advanced_search_dialog.py — birth_date_input / perform_search
```
### وضعیت
`BROKEN` (P1 — جست‌وجوی پیشرفته همیشه خالی)
### مشکل
`ShamsiDateInput` به‌طور پیش‌فرض «امروز» را پر می‌کند؛ جست‌وجو همیشه شرط
`birth_date = امروز` را هم می‌فرستاد → با هر معیاری صفر نتیجه.
### اصلاح
فیلد تاریخ تولد خالی شروع می‌شود (برچسب «اختیاری»)، فقط در صورت ورود
اعمال می‌شود و تاریخ نامعتبر پیام می‌دهد.
### تست
D12: مقدار پیش‌فرض خالی؛ جست‌وجوی نام → نتیجه؛ دابل‌کلیک → `student_selected` درست.
```text
STATUS: FIXED
```

## [BUG-027] — نیازمند تصمیم
### بخش
```text
views/dialogs/attachment_dialog.py (AttachmentDialog, AttachmentUploadWorker)، services/attachment_service.py، جدول attachments
```
### وضعیت
`UNREACHABLE` (P2 — حالت ۴: backend و دیالوگ هست، هیچ نقطهٔ ورودی در UI نیست)
### مشکل
هیچ صفحه/دکمه‌ای `AttachmentDialog` را باز نمی‌کند (تنها ارجاع‌ها در
اسکریپت‌های verify هستند). کل زنجیرهٔ پیوست‌ها (آپلود در نخ کارگر، ذخیرهٔ
فایل، رکورد DB، پشتیبان‌گیری از پوشهٔ پیوست‌ها) از دید کاربر وجود ندارد.
### گزینه‌ها
(الف) یک دکمهٔ «📎 پیوست‌ها» در پروندهٔ دانش‌آموز که همین دیالوگ را برای
همان دانش‌آموز باز کند (اتصال کد موجود؛ آزمون کامل زنجیره در مرحلهٔ ۴ — بند
۲۱)؛ (ب) حذف کد مرده (دیالوگ، کارگر، سرویس، DAL) — جدول می‌ماند؛ (ج) فقط گزارش.
```text
STATUS: NOT_FIXED (منتظر تصمیم)
```

## [BUG-028] — نیازمند تصمیم
### بخش
```text
utils/notification_scheduler.py، services/notification_service.py، dal/notification_dal.py، جدول notifications
```
### وضعیت
`UNREACHABLE / DEAD_CODE` (P3 — حالت ۴)
### مشکل
`NotificationScheduler` هیچ‌جا (main.py/پنجرهٔ اصلی) راه‌اندازی نمی‌شود و هیچ
UI‌ای جدول `notifications` را نمی‌خواند؛ زنگولهٔ هدر مستقیماً از
`ReminderService` (پیگیری‌های در انتظار/معوق) پر می‌شود. یعنی زیرسیستم
اعلان‌ها (با تریگرهای Audit و جلوگیری از تکرار که در دورهای ۱۴/۱۵ اصلاح شد)
فقط در آزمون‌ها اجرا می‌شود.
### گزینه‌ها
(الف) راه‌اندازی زمان‌بند در شروع برنامه و نمایش جدول `notifications` در
زنگوله (کنار یادآورهای فعلی)؛ (ب) حذف زیرسیستم (زنگولهٔ فعلی کار خود را
می‌کند)؛ (ج) فقط گزارش.
```text
STATUS: NOT_FIXED (منتظر تصمیم)
```

## [BUG-029]
### بخش
```text
views/widgets/filter_widget.py، dal/saved_filter_dal.py، models/saved_filter.py، جدول saved_filters
```
### وضعیت
`DEAD_CODE` (P4)
### مشکل
هیچ مصرف‌کننده‌ای ندارد؛ تصمیم حذف در مرحلهٔ ۶ (بند ۲۷) پس از جست‌وجوی کامل.
```text
STATUS: NOT_FIXED (گزارش)
```

## سیگنال‌های دیالوگ‌ها/ویجت‌ها بدون گیرنده (بند ۱۹)
`attachment_added/attachment_deleted` (دیالوگ خودش دست‌نیافتنی است)،
`password_changed` (دیالوگ خودبسنده؛ بی‌خطر)، `assignment_saved` (صفحه‌ها پس
از `exec()` خودشان تازه‌سازی می‌کنند؛ بی‌خطر)، `filter_applied`،
`help_requested`، `recommendation_*` (کد مرده). موردی که باعث اجرای دوبارهٔ
عملیات دیتابیس شود پیدا نشد.

## نتیجهٔ اجرای آزمون‌ها پس از مرحلهٔ ۳-ب

| مجموعه | نتیجه |
|---|---|
| `pytest -q tests` | 26 passed |
| verify_fixes 1 … 15 | همه سبز |
| **verify_fixes16 (۱ تا ۳-ب)** | **52 / 52** |
| `ruff check .` | All checks passed |

آزمون تغییریافته: هیچ.

## بندهای مأموریت در این مرحله
۲، ۳، ۱۴ (ایجاد/ویرایش با پیش/پس‌شرط برای ۸ فرم)، ۱۸ و ۱۹ (دیالوگ‌ها/ویجت‌ها)،
۳۶ (جدول وضعیت)، بخشی از ۲۴ (خروجی AI: ۶ فایل واقعی و معتبر) و ۲۷ (کشف کد
دست‌نیافتنی: پیوست‌ها، اعلان‌ها، فیلترهای ذخیره‌شده، پیشنهادها).

---

# بخش ۵ — مرحلهٔ ۴: پیوست‌ها، نخ‌ها/کارگرها، Race، وضعیت Screening/Recommendation

پایه: کامیت `9256067`. تصمیم‌های باز (BUG-023/027/028) بدون پاسخ ماندند → طبق
گزینهٔ «ج» فقط گزارش؛ **اما** زنجیرهٔ پیوست‌ها (بند ۲۱) مستقل از نقطهٔ ورودی
UI، کامل آزمایش و اصلاح شد تا هر وقت تصمیم به اتصال گرفته شد، سالم باشد.

## وضعیت زنجیرهٔ پیوست (بند ۲۱) — پس از اصلاحات

```text
Add file → (QFileDialog: NOT_TESTED - GUI EXECUTION REQUIRED)
        → upload_files([...]) صف ترتیبی → AttachmentUploadWorker (QThread، worker_context کاربر)
        → خواندن فایل → AttachmentService.upload_attachment
        → اعتبارسنجی پسوند + محتوا → نوشتن اتمیک (.part → os.replace) با نام یکتا
        → رکورد attachments (created_by = کاربر) → Audit
        → progress (۲۰/۶۰/۱۰۰) → upload_finished → فایل بعدی صف
        → پایان صف: load_attachments + attachment_added + یک پیام جمع‌بندی
Search / Clear / Refresh / Preview / Download / Delete / Double-click: VERIFIED (E5, E6, E11)
نقطهٔ ورودی در برنامه: هنوز وجود ندارد (BUG-027 — منتظر تصمیم)
```

## [BUG-030]
### بخش
```text
views/dialogs/attachment_dialog.py — add_attachment / upload_file / upload_finished
```
### وضعیت
`BROKEN` (P1 — Crash احتمالی + Race)
### مشکل
برای هر فایلِ انتخاب‌شده بلافاصله یک `AttachmentUploadWorker` جدید ساخته و در
`self.upload_worker` جایگزین می‌شد؛ QThread قبلی در حال اجرا از دست می‌رفت
(«QThread: Destroyed while thread is still running») و چند آپلود هم‌زمان روی
یک موجودیت انجام می‌شد؛ بستن دیالوگ وسط آپلود همین اثر را داشت؛ سیگنال
`finished` داخلی QThread هم با امضای متفاوت بازتعریف شده بود.
### اصلاح
صف ترتیبی (`upload_files` → `_start_next_upload` → `_finish_upload_batch`)؛
درخواست آپلود وسط آپلود با پیام رد می‌شود؛ `closeEvent`/`reject` منتظر پایان
کارگر می‌مانند؛ سیگنال `upload_finished`؛ پیام جمع‌بندی (موفق/ناموفق).
### تست
E1 (دو فایل → دو رکورد/دو فایل/یک پیام)، E7 (آپلود دوم وسط آپلود اول رد؛
بستن امن)، E9 (بدون بازتعریف `finished`).
```text
STATUS: FIXED
```

## [BUG-031]
### بخش
```text
services/attachment_service.py — _generate_safe_filename / upload_attachment
```
### وضعیت
`BROKEN` (P1 — Data loss)
### مشکل
نام فایل ذخیره‌شده فقط با timestamp **ثانیه‌ای** یکتا می‌شد؛ دو آپلود هم‌نام
در یک ثانیه (دقیقاً سناریوی انتخاب چند فایل) روی هم نوشته می‌شدند و دو رکورد
به یک فایل اشاره می‌کردند.
### اصلاح
پسوند یکتا (timestamp + ۸ نویسهٔ تصادفی) + حلقهٔ بررسی وجود فایل.
### تست
E2 (دو فایل هم‌نام پشت سر هم → دو مسیر متفاوت با محتوای خودشان).
```text
STATUS: FIXED
```

## [BUG-032]
### بخش
```text
services/attachment_service.py — upload_attachment (ترتیب فایل/دیتابیس)
```
### وضعیت
`PARTIALLY_BROKEN` (P2 — فایل یتیم / نوشتن غیراتمیک)
### مشکل
فایل پیش از درج رکورد روی دیسک نوشته می‌شد؛ اگر درج شکست می‌خورد یا تراکنش
برمی‌گشت، فایل یتیم می‌ماند؛ نوشتن هم اتمیک نبود.
### اصلاح
نوشتن در `.part` و `os.replace`؛ هر شکستی پس از نوشتن (اعتبارسنجی مدل، DB،
Audit) فایل را پاک می‌کند؛ `get_attachment_path` برای شناسهٔ ناموجود پیام
روشن می‌دهد.
### تست
E3 (نوع غیرمجاز → نه رکورد نه فایل)، E4 (شکست تزریق‌شدهٔ `AttachmentDAL.create` →
بدون فایل یتیم).
```text
STATUS: FIXED
```

## [BUG-033]
### بخش
```text
views/dialogs/attachment_dialog.py — open_file
```
### وضعیت
`BROKEN` (P0 — Security: Command injection)
### مشکل
مسیر فایل داخل رشتهٔ فرمان shell قرار می‌گرفت؛ نام فایل آپلودشده با نویسهٔ
`"` یا `;` می‌توانست فرمان دلخواه اجرا کند (نام فایل‌ها با
`sanitize_filename` فقط چند نویسهٔ مسیر را حذف می‌کند، نه `;` و `$`).
### اصلاح
`QDesktopServices.openUrl(QUrl.fromLocalFile(path))` (بدون shell، چندسکویی).
### تست
E11 (منبع: بدون `os.system`؛ با Qt). اجرای واقعی برنامهٔ خارجی:
`NOT_TESTED - GUI EXECUTION REQUIRED`.
```text
STATUS: FIXED
```

## [BUG-034]
### بخش
```text
۸ فرم ثبت/ویرایش (views/dialogs/*_form.py, assign_teacher_dialog.py) — save_*
utils/ui_guards.py (جدید)
```
### وضعیت
`PARTIALLY_BROKEN` (P2 — Race: double insert)
### مشکل
handler ذخیره وسط کار `QMessageBox.information` را باز می‌کند که یک حلقهٔ
رویداد تودرتو است؛ کلیک دومِ در صف همان‌جا پردازش می‌شود و `save_*` دوباره
(تودرتو) اجرا می‌شود → دو رکورد برای یک فرم.
### اصلاح
دکوراتور `single_submit`: رد ورود دوباره + غیرفعال‌کردن دکمهٔ ذخیره تا پایان.
### تست
E8 (شبیه‌سازی کلیک دوم داخل پیام موفقیت → دقیقاً یک رکورد؛ پرچم آزاد؛ دکمه
فعال؛ هر ۸ فرم نگهبان دارند).
```text
STATUS: FIXED
```

## بند ۲۰ — نخ‌ها و کارگرها (جمع‌بندی)

| Worker | مالکیت/ساخت | Signal/Slot | اتصال DB | دسترسی UI از نخ | پاک‌سازی/خاتمه | وضعیت |
|---|---|---|---|---|---|---|
| `AttachmentUploadWorker` (QThread) | دیالوگ، در صف | `progress`, `upload_finished` (بدون بازتعریف `finished`) | `worker_context(user)` نخ‌محلی؛ رجیستری اتصال رشد نمی‌کند (E10) | فقط سیگنال (E9) | صف ترتیبی؛ بستن دیالوگ منتظر می‌ماند (E7) | VERIFIED |
| `BackupWorker` (QThread) | صفحهٔ پشتیبان | `progress`, `operation_finished` | `worker_context(user)` | فقط سیگنال (E9) | قفل هم‌زمانی صفحه (مرحلهٔ ۲) | VERIFIED |
| `AutoBackupHandle` (threading) | تنظیمات | — | online backup روی اتصال خودش | ندارد | `stop()` واقعی (مرحلهٔ ۲) | VERIFIED |
| `NotificationScheduler` (threading) | **هیچ‌جا راه‌اندازی نمی‌شود** | — | `worker_context(None)` (دور ۱۴) | ندارد | `stop()` دارد | UNREACHABLE (BUG-028) |
| `idle_timer`/`auto_logout` (QTimer در نخ UI) | پنجرهٔ اصلی | — | — | — | — | نکتهٔ P4 مرحلهٔ ۳-الف |

## بند ۳۲ — Race condition (جمع‌بندی)

| سناریو | وضعیت |
|---|---|
| Upload چندفایل / بستن وسط آپلود | FIXED (BUG-030) |
| Save دوباره با کلیک دوم | FIXED (BUG-034) |
| Delete/Refresh هم‌زمان در صفحهٔ پشتیبان | FIXED مرحلهٔ ۲ (BUG-017) |
| Backup هم‌زمان با نوشتن UI | امن: SQLite online backup API روی اتصال جدا |
| Restore هم‌زمان با نخ‌های دیگر | امن: `DB_THREAD_LOCK` + `close_all` (دور ۱۲/۱۴) |
| نام فایل تکراری پیوست | FIXED (BUG-031) |
| Generate گزارش هم‌زمان | همزمان در نخ UI (سری) — بدون Race |

## وضعیت Screening و Recommendation (بندهای ۷، ۸، ۹ — فقط گزارش طبق تصمیم شما)

```text
Screening:      models/dal/database/service موجود؛ در views/ هیچ فرم/صفحه/دکمه‌ای وجود ندارد
                (فقط نمایش «لایهٔ غربالگری» در گزارش). وضعیت: UNREACHABLE (backend بدون UI).
Recommendation: RecommendationService در گزارش‌ها استفاده می‌شود (VERIFIED)؛
                RecommendationWidget و دکمهٔ Generate آن هیچ مصرف‌کننده‌ای ندارند → DEAD_CODE.
                کنتراست دکمهٔ Generate در مرحلهٔ ۳-الف اصلاح شد (BUG-022).
```
(E12 این وضعیت را قفل می‌کند تا تغییر آن آگاهانه باشد.)

## نتیجهٔ اجرای آزمون‌ها پس از مرحلهٔ ۴

| مجموعه | نتیجه |
|---|---|
| `pytest -q tests` | 26 passed |
| verify_fixes 1 … 15 | همه سبز |
| **verify_fixes16 (۱ تا ۴)** | **64 / 64** |
| `ruff check .` | All checks passed |

آزمون تغییریافته: هیچ. فایل جدید: `utils/ui_guards.py`.

## بندهای مأموریت در این مرحله
۲۰ (نخ‌ها/کارگرها)، ۲۱ (زنجیرهٔ پیوست به‌جز نقطهٔ ورودی UI که تصمیم شماست)،
۳۲ (Race: آپلود، ثبت دوباره، پشتیبان)، ۷/۸/۹ (فقط گزارش وضعیت)، به‌علاوه ۳۰
(تزریق فرمان در بازکردن فایل) و ۲۵ (نوشتن اتمیک پیوست).

---

# بخش ۶ — مرحلهٔ ۵: تراکنش، ایمپورت، قرارداد نتیجه، استثناها، SQL، Constraints، خروجی‌ها، سازگاری داده

پایه: کامیت `27edf72`. فایل‌های تغییریافته: همهٔ `dal/*.py` (۱۴۴ مورد
`conn.commit()` و ۲۴ مورد `conn.rollback()` → `self.db.*`)، ۳۹ فایل در
`services/` و `dal/` (۷۸ except بی‌صدا لاگ‌دار شدند)، `utils/excel_importer.py`،
`views/pages/{goals,activities,counseling}_page.py`، `database/connection.py`
(سند سیاست suppress)، `verify_fixes16.py` (§F، ۹ بررسی).

## [BUG-035]
### بخش
```text
dal/*.py — ۱۴۴ فراخوانی conn.commit() ؛ services/base_service.py — execute_in_transaction
```
### وضعیت
`BROKEN` (P1 — Database consistency: تراکنش سرویس‌ها عملاً بی‌اثر بود)
### مشکل
طراحی تراکنش برنامه (`begin_transaction` → عمق تراکنش نخ‌محلی؛ `db.commit()`
داخل تراکنش بی‌اثر) فرض می‌کرد DALها از `self.db.commit()` استفاده می‌کنند؛
ولی **همهٔ** DALها `conn.commit()` را روی اتصال خام sqlite3 صدا می‌زدند که
هیچ‌جا رهگیری نمی‌شود. نتیجه: هر گام DAL بلافاصله commit می‌شد و
`execute_in_transaction` در عملیات چندمرحله‌ای (حذف دانش‌آموز با
وابسته‌ها، آپلود پیوست، ایمپورت، …) هیچ اتمیک‌بودنی نمی‌داد؛ rollback سرویس
پس از شکست، گام‌های قبلی را برنمی‌گرداند.
### اثبات پیش از اصلاح
`begin_transaction()` → `StudentDAL.create()` → `in_transaction == False` و
`rollback_transaction()` رکورد را برنگرداند (۱ ردیف ماند).
### اصلاح
جایگزینی مکانیکی `conn.commit()` → `self.db.commit()` و `conn.rollback()` →
`self.db.rollback()` در همهٔ DALها (بیرون از تراکنش همان رفتار قبلی؛ داخل
تراکنش فقط لایهٔ سرویس commit می‌کند). هیچ API عمومی تغییر نکرد.
### تست
F1 (دو درج DAL + شکست داخل `execute_in_transaction` → هیچ ردیفی نمی‌ماند؛
`conn.commit()` خام در dal/ = ۰)، F3 (ایمپورت: شکست ساخت پرونده → دانش‌آموز
همان ردیف هم نمی‌ماند). کل باتری (۶۳۳ بررسی) پس از این تغییر سبز است.
```text
STATUS: FIXED
```

## [BUG-036]
### بخش
```text
utils/excel_importer.py — import_students_from_excel (نگاشت ستون‌ها)
```
### وضعیت
`BROKEN` (P1 — ایمپورت اکسل هرگز کار نمی‌کرد)
### مشکل
نگاشت ستون‌ها با «زیررشته» انجام می‌شد؛ چون «نام» زیررشتهٔ «نام خانوادگی»،
«نام پدر» و «نام ولی» است، همهٔ این ستون‌ها روی `first_name` می‌افتادند و
`last_name` هرگز پیدا نمی‌شد. حتی **فایل نمونهٔ خودِ برنامه** با پیام
«ستون‌های ضروری یافت نشدند: last_name» رد می‌شد.
### اصلاح
تطبیق دقیق پس از یکدست‌سازی (نیم‌فاصله، ی/ک عربی)، سپس طولانی‌ترین کلید؛
هر فیلد فقط به اولین ستون هم‌خوان. پایهٔ غیرعددی به‌جای «بی‌صدا ۱»، خطای
همان ردیف می‌شود. دانش‌آموز + پرونده در یک تراکنش؛ شمارش «موفق» فقط پس از
هر دو.
### تست
F2 (نمونهٔ برنامه → همهٔ ردیف‌ها با پرونده، نام/نام خانوادگی/نام پدر جدا)،
F3 (کد ملی تکراری در فایل و در DB، پایهٔ غیرعددی، نام خالی → گزارش ردیف و
ادامه؛ فایل خالی/خراب/ناموجود → پیام روشن بدون crash؛ شکست پرونده → بدون
دانش‌آموز نیمه‌کاره).
```text
STATUS: FIXED
```

## [BUG-037]
### بخش
```text
views/pages/goals_page.py, activities_page.py, counseling_page.py — delete_*
```
### وضعیت
`PARTIALLY_BROKEN` (P3 — بند ۱۷: موفقیت ظاهری)
### مشکل
سرویس‌های حذف هدف/فعالیت/جلسه در نبود رکورد `False` برمی‌گردانند، ولی
صفحه‌ها بدون بررسی نتیجه «با موفقیت حذف شد» می‌گفتند.
### اصلاح
نتیجه بررسی می‌شود؛ `False` → هشدار «پیدا نشد (احتمالاً قبلاً حذف شده)» +
تازه‌سازی فهرست. سایر سرویس‌های حذف (مشاهده/مداخله/پیگیری/دانش‌آموز) با
استثنا شکست را اعلام می‌کنند (قرارداد صریح).
### تست
F4.
```text
STATUS: FIXED
```

## [BUG-038]
### بخش
```text
services/*.py و dal/*.py — ۷۸ بلوک except بدون هیچ لاگ/raise/پیام
```
### وضعیت
`PARTIALLY_BROKEN` (P3 — بند ۱۶: خطاهای بلعیده‌شده)
### مشکل
اسکن AST: ۱۵۱ بلوک except در پروژه هیچ لاگ/raise/پیامی نداشتند؛ ۷۸ مورد در
لایهٔ سرویس/داده بودند (مثلاً «نام: نامشخص» به‌جای نام واقعی، `[]` به‌جای
آمار ماهانه، `False` به‌جای بررسی وجود مشاهده) — رفتار جایگزین درست بود ولی
علت هرگز ثبت نمی‌شد.
### اصلاح
همهٔ این ۷۸ مورد اکنون علت را با `logger.debug` (لاگ برنامه) ثبت می‌کنند و
همان رفتار جایگزین را نگه می‌دارند؛ `except:` خالی در پروژه صفر است؛
سیاست `contextlib.suppress` در `database/connection.py` مستند شد (فقط
مسیرهای بستن/rollback جبرانی). بلوک‌های `pass` توضیح‌دار (عمدی) دست نخوردند.
### تست
F5 (اسکن دوباره: صفر بلوک بی‌صدا در services/ و dal/؛ صفر except خالی).
```text
STATUS: FIXED
```

## بند ۳۰ — DAL
- **SQL injection:** اسکن AST همهٔ f-string/%/format حاوی SQL در dal/services/
  database/utils → تنها درون‌یابی‌ها: فهرست `?` (`placeholders`)، نام ثابت
  جدول/ستون داخلی (`_AUDIT_TABLES`، وابستگی‌های حذف کادر)، تکه‌های WHERE با
  `?`، و DDL تریگرها. هیچ مقدار کاربر با رشته‌سازی وارد SQL نمی‌شود (F6،
  قفل‌شده با فهرست مجاز). جست‌وجوی متن آزاد با `LIKE ? ESCAPE '\'` و فرار
  نویسه‌های ویژه.
- **اتصال/cursor:** اتصال نخ‌محلی با رجیستری (دور ۱۲/۱۴)؛ cursorها با پایان
  متد رها می‌شوند (sqlite3 نیازی به بستن صریح ندارد).
- **رکورد ناموجود:** `get_by_id` → `None`؛ سرویس‌ها `ServiceError` با پیام.
- **رکورد تکراری / FK:** بند ۳۱.

## بند ۳۱ — Constraints (وضعیت واقعی اسکیما)

| جدول | PK | FK | UNIQUE | NOT NULL | CHECK |
|---|---|---|---|---|---|
| students | ✓ | — | national_code | first/last_name | — |
| student_academic_profiles | ✓ | student, year | (student, year) | student, year | — |
| observations | ✓ | ۵ | — | profile, staff, date, description | — |
| interventions | ✓ | ۳ | — | profile, staff, type, date, description | — |
| followups | ✓ | ۲ | — | intervention, staff, date | — |
| users | ✓ | staff | username | staff, username, hash, role | — |
| academic_years / classes / teacher_assignments / competencies | ✓ | ✓ | title / (year,name) / (student,staff,year) / title | ✓ | — |

`PRAGMA foreign_keys = ON` و اجرا می‌شود (F7: FK نقض‌شده، کد ملی تکراری،
پروندهٔ تکراری، NOT NULL همه رد می‌شوند؛ سرویس هم کد ملی تکراری را با پیام
فارسی رد می‌کند). **نکتهٔ باز (P4):** هیچ `CHECK` (مثلاً `severity BETWEEN 1
AND 5`، `behavior_type IN (...)`) در اسکیما نیست؛ این قیود فقط در مدل/سرویس
هستند. افزودن CHECK به جدول‌های موجود در SQLite بازسازی جدول (migration v10)
می‌خواهد — عمداً در این دور انجام نشد (تصمیم با شما).

## بند ۲۴ — خروجی‌ها (فایل واقعی)
F8: از مسیر صفحه‌ها (`reports_page.export_pdf/export_excel`،
`students_page.export_to_excel/download_sample_excel`) فایل واقعی و معتبر
(سرآیند PDF، کتاب Excel با ≥۲ ردیف) + پیام موفقیت. خروجی AI در ۶ قالب:
مرحلهٔ ۳-ب (D13). خروجی PDF/Excel گزارش کلاس، گزارش معلم و عملکرد معلم:
زنجیرهٔ handler → سرویس در مرحلهٔ ۳-الف اجرا شده (بدون فایل چون گزارشی
تولید نشده بود) → `NOT_TESTED` برای فایل نهایی (نیازمند داده/انتخاب در UI).

## بند ۲۳ — سازگاری داده
F9: جدول مشاهدات = DB؛ ثبت از سرویس + بارگذاری دوباره → +۱؛ حذف از صفحه →
`is_deleted=1` و −۱ ردیف. (فرم‌ها: مرحلهٔ ۳-ب — ایجاد/ویرایش با بازخوانی از DB.)

## نتیجهٔ اجرای آزمون‌ها پس از مرحلهٔ ۵

| مجموعه | نتیجه |
|---|---|
| `pytest -q tests` | 26 passed |
| verify_fixes 1 … 15 | همه سبز |
| **verify_fixes16 (۱ تا ۵)** | **73 / 73** |
| `ruff check .` | All checks passed |

آزمون تغییریافته: هیچ.

## بندهای مأموریت در این مرحله
۱۶ (استثناها)، ۱۷ (قرارداد نتیجه)، ۲۲ (تراکنش واقعی + ایمپورت اتمیک)، ۲۳
(سازگاری)، ۲۴ (خروجی‌های واقعی)، ۲۶ (ایمپورت: معتبر/نامعتبر/خالی/خراب/
تکراری/اسکیمای غلط؛ «encoding» برای xlsx موضوعیت ندارد — ورودی فقط xlsx است)،
۳۰ (DAL/SQL)، ۳۱ (Constraints).

---

# بخش ۷ — مرحلهٔ ۶: کد مرده، وابستگی لایه‌ها، لایهٔ سرویس، ارزیابی تست‌ها

پایه: کامیت `c54be48`. روش کشف کد مرده: فهرست همهٔ ماژول‌ها و کلاس/تابع‌های
سطح بالا در کد برنامه، جست‌وجوی ارجاع (نام و import) در **کل مخزن** (کد
برنامه، `tests/`، همهٔ `verify_fixes*`، ابزارها) و بازبینی دستی هر مورد.

## [BUG-039]
### بخش
```text
views/pages/assign_teacher_page.py (۵۸۲ خط)، views/pages/teacher_students_page.py (۶۸۶ خط)
```
### وضعیت
`DEAD_CODE` (حالت ۶ — دو صفحهٔ کامل که هیچ‌جا سوار نشده بودند)
### مشکل
هیچ import/ساختی از این دو صفحه در برنامه وجود نداشت (پنجرهٔ اصلی ۱۳ صفحه
سوار می‌کند؛ این دو جزو آن‌ها نیستند). قابلیت‌شان (اختصاص معلم / دانش‌آموزان
یک معلم) در `academic_structure_page` و فیلتر معلم صفحهٔ گزارش‌ها زنده است.
### اصلاح
حذف (در تاریخچهٔ git موجود است). به‌همراه: `utils/cache.py`،
`utils/competency_helper.py`، `models/student_file.py` (صفر ارجاع در کل
مخزن) و سه سیگنالِ تعریف‌شده ولی هرگز emit‌نشده
(`StudentProfilePage.student_changed`،
`AcademicStructurePage.assignment_changed`، و همان در صفحهٔ حذف‌شده).
### تست
G1 (فایل‌ها نیستند و هیچ ارجاعی نمانده؛ ماژول‌های منتظر تصمیم دست‌نخورده)،
G3 (هیچ سیگنال هرگز-emit-نشده‌ای نمانده).
```text
STATUS: FIXED
```

## [BUG-040]
### بخش
```text
views/pages/activities_page.py — on_item_double_clicked / display_activities / student_selected
```
### وضعیت
`BROKEN` (P2 — ویرایش رکورد اشتباه با فیلتر فعال؛ سیگنال بدون فرستنده)
### مشکل
(۱) دابل‌کلیک، ردیف جدول را در فهرست **فیلترنشده** (`self.activities`)
جست‌وجو می‌کرد؛ با فیلتر نوع/وضعیت فعال، فرم ویرایشِ فعالیت دیگری باز می‌شد.
(۲) سیگنال `student_selected` تعریف و در پنجرهٔ اصلی متصل بود، ولی این صفحه
هرگز آن را emit نمی‌کرد (صفحه‌های اهداف و مشاوره دکمهٔ «👤 مشاهده پرونده
دانش‌آموز» دارند؛ این صفحه نه).
### اصلاح
`visible_activities` برای فهرست نمایش‌داده‌شده؛ دکمهٔ «👤 مشاهده پرونده
دانش‌آموز» با `view_student_profile` مثل دو صفحهٔ خواهر. سایر صفحه‌های
جدولی بررسی شدند: همیشه همان فهرستی را نمایش می‌دهند که به آن اندیس می‌زنند.
### تست
G3 (سیگنال emit می‌شود)؛ اجرای handlerها در §C.
```text
STATUS: FIXED
```

## [BUG-041]
### بخش
```text
views/pages/backup_page.py — BackupWorker.progress
```
### وضعیت
`PARTIALLY_BROKEN` (P4 — نوار پیشرفت آرایشی)
### اصلاح
`progress(10)` در شروع و `progress(100)` در پایان (مقدار میانی برای پشتیبان
SQLite قابل اندازه‌گیری نیست).
```text
STATUS: FIXED
```

## فهرست کد مرده / دست‌نیافتنیِ باقی‌مانده — منتظر تصمیم شما (حذف یا اتصال)

| ماژول | خط | مصرف‌کننده در برنامه | ارجاع در تست‌ها | پیشنهاد |
|---|---|---|---|---|
| `views/dialogs/attachment_dialog.py` (+ سرویس/DAL پیوست) | ۹۰۰+ | هیچ (BUG-027) | verify14/16 | اتصال: دکمهٔ «📎 پیوست‌ها» در پروندهٔ دانش‌آموز (زنجیره سالم و آزموده) |
| `utils/notification_scheduler.py`, `services/notification_service.py`, `dal/notification_dal.py`, جدول `notifications` | ~۹۰۰ | هیچ (BUG-028) | verify14/15/16 | حذف یا راه‌اندازی در `main.py` + نمایش در زنگوله |
| `views/widgets/filter_widget.py`, `dal/saved_filter_dal.py`, `models/saved_filter.py`, جدول `saved_filters` | ~۷۵۰ | هیچ (BUG-029) | verify16 (فقط فهرست) | حذف (جدول می‌ماند) |
| `views/widgets/recommendation_widget.py` | ۴۰۰ | هیچ | verify16 (فهرست) | حذف یا سوارکردن در پروندهٔ دانش‌آموز (سرویس پیشنهادها زنده است) |
| `dal/backup_dal.py` (BackupDAL/BackupRecord) + جدول `backups` | ۴۹۰ | هیچ | verify9 | حذف (پشتیبان‌ها فایل‌محورند) |
| `services/school_report_service.py` | ۳۵۴ | هیچ | verify2/7/8 (وجود فایل) | حذف پس از به‌روزرسانی آن سه بررسی |
| `dal/screening_tool_dal.py` (+ زیرسیستم Screening بدون UI) | ۲۸۷ | هیچ | — | تصمیم Screening (ساخت UI یا حذف) |
| `utils/report_template.py` | ۴۵۶ | هیچ | verify2/3 | حذف پس از به‌روزرسانی بررسی‌ها |
| `models/analytics_models.py` (dataclassهای بی‌استفاده) | ۱۱۰ | هیچ | verify8/10 | حذف پس از به‌روزرسانی بررسی‌ها |
| `config/constants.py` — ۸ تابع `get_*_display` | — | هیچ | — | حذف یا استفاده در صفحه‌ها به‌جای نگاشت‌های محلی |
| `utils/error_handler.py` — `AppError`, `DatabaseError`, `NotFoundError`, … | — | هیچ (فقط `ServiceError/ValidationError` استفاده می‌شود) | — | نگه‌داشتن به‌عنوان سلسله‌مراتب خطا یا حذف |

(هیچ‌کدام حذف نشد؛ G1 وجودشان را قفل می‌کند تا حذف آگاهانه باشد.)

## بند ۲۸ — گراف وابستگی (وضعیت واقعی)

```text
views  → services (24 فایل) ، dal (36) ، models ، utils ، database ، config
services → dal (21) ، models ، utils ، database (2: اتصال/قفل) ، config
dal → database ، models ، utils
utils → config ، database (2) ، dal (excel_importer, notification_scheduler) ، services (notification_scheduler)
models → utils
```
- **بدون** services→views، dal→services/views، models→dal/services، database→services/dal.
- هیچ SQL/اتصال خام در `views/` (`execute(`/`get_connection()` صفر مورد).
- هیچ import از Qt در `services/`.
- نکته‌های معماری (P4، بدون تغییر): `utils/excel_importer.py` عملاً یک سرویس
  است (به DAL وابسته)؛ `views` در ۳۶ فایل مستقیم به DAL می‌روند (طبق قاعدهٔ ۱
  README مجاز است — فقط خواندن‌های ساده)؛ G2 جهت‌های ممنوع را قفل می‌کند.

## بند ۲۹ — لایهٔ سرویس
تحلیل AST همهٔ متدهای عمومی سرویس‌ها: تنها `NotificationService` (زیرسیستم
دست‌نیافتنی) اغلب wrapper خالص DAL است؛ بقیهٔ سرویس‌ها اعتبارسنجی، تراکنش،
غنی‌سازی و Audit دارند. هیچ سرویسی ویجت را دستکاری نمی‌کند (G4).

## بندهای ۱۳ و ۱۴ — ارزیابی صادقانهٔ آزمون‌های موجود

| مجموعه | نوع غالب | چه چیزی را ثابت می‌کند | چه چیزی را ثابت **نمی‌کند** |
|---|---|---|---|
| `tests/` (۲۶ unittest) | واحد/DAL/سرویس روی DB موقت | CRUD پایه، مدل‌ها، چند سرویس | هیچ UI، هیچ زنجیرهٔ کامل |
| `verify_fixes1–8` | **Regression** (باگ X برنگشته) | رفتارهای اصلاح‌شدهٔ دورهای ۱–۸ (تاریخ، زمان، حذف منطقی، …) | کارکرد کاربر از UI تا DB |
| `verify_fixes9–10` | Regression + بررسی ایستا (lint، ClassVar، ساخت صفحه‌ها offscreen) | صفحه‌ها بدون استثنا ساخته می‌شوند | کلیک/داده |
| `verify_fixes11–13` | Regression محتوایی (تحلیل رفتار، روند، روایت) | منطق تحلیل روی دادهٔ seed | UI |
| `verify_fixes14–15` | Regression فنی (نخ‌ها، Audit، پشتیبان، migration، N+1) | قراردادهای فنی | زنجیرهٔ UI |
| **`verify_fixes16`** (۷۷) | **Functional با پیش/پس‌شرط** | ۸ فرم ایجاد/ویرایش، ۱۶۷ handler صفحه‌ها، پشتیبان/بازیابی، پیوست، ایمپورت، خروجی‌ها، تراکنش، migration — همه با مقایسهٔ DB/فایل قبل و بعد | کلیک واقعی موس، دیالوگ‌های modal، file picker (`NOT_TESTED - GUI EXECUTION REQUIRED`) |

نتیجه: پیش از این دور، هیچ آزمون کارکردیِ «UI → DB با پس‌شرط» وجود نداشت؛
`verify_fixes16` این شکاف را برای مسیرهای اصلی پر می‌کند ولی جایگزین تست GUI
واقعی نیست.

---

# بخش ۸ — گزارش نهایی (بندهای ۳۳، ۳۴، ۳۷، ۳۸)

## فهرست یک‌نگاهی همهٔ ایرادها

| BUG | اولویت | بخش | خلاصه | STATUS |
|---|---|---|---|---|
| 001 | P1 | migrations/manager | نسخه پیش از downgrade کم می‌شد | FIXED |
| 002 | P2 | migrations/manager | کشف با `range(1,100)` و بلعیدن ImportError | FIXED |
| 003 | P2 | migrations/manager | گام‌ها بدون تراکنش صریح | FIXED (محدودیت commit داخلی مستند) |
| 004 | P3 | migrations/manager, connection | print به‌جای logger/traceback | FIXED |
| 005 | P2 | migrations/manager | downgrade بدون تابع → کاهش خاموش نسخه | FIXED |
| 006 | P1 | main.py | QMessageBox پیش از QApplication → مرگ فرایند در خطای راه‌اندازی | FIXED |
| 007 | P3 | tests/ | `unittest.makeSuite` (Python 3.13) | FIXED |
| 008 | P4 | README/main | نسخهٔ Python صریح نبود | FIXED |
| 009 | P0 | backup.delete_backup | حذف هر مسیر؛ sidecar می‌ماند | FIXED |
| 010 | P2 | backup.create_backup | نوشتن غیراتمیک؛ نام با پیمایش مسیر | FIXED |
| 011 | P3 | backup | نشت `.db.tmp-wal/-shm` کنار هر پشتیبان | FIXED |
| 012 | P3 | backup | MD5 در فایل `.sha256` | FIXED |
| 013 | P2 | backup_page | وضعیت «سالم» بدون بررسی | FIXED |
| 014 | P2 | backup.restore | rmtree پیوست‌ها پیش از کپی؛ پاکسازی | FIXED |
| 015 | P1 | settings_page | توقف پشتیبان خودکار تزئینی | FIXED |
| 016 | P2 | settings, backup_page, git | پشتیبان‌ها داخل درخت کد و مخزن | FIXED |
| 017 | P2 | backup_page | بازتعریف `finished`، race worker | FIXED |
| 018 | P1 | settings_page | ذخیرهٔ اطلاعات مدرسه تزئینی | FIXED |
| 019 | P2 | settings, academic_structure | ویرایش کلاس «در نسخهٔ بعدی» | FIXED |
| 020 | P2 | analytics_dashboard | دابل‌کلیک placeholder | FIXED |
| 021 | P3 | student_profile, reports | «گزارش پرونده» فقط پیام | FIXED |
| 022 | P2 | ۴۰ فایل views | ۱۰۴ بلوک استایل با کنتراست < ۳:۱ | FIXED |
| 023 | P2 | main_window | کامبوی سال تحصیلی تزئینی | FIXED (بخش ۹) |
| 024 | P1 | observation model/service | ثبت مشاهده بدون توضیحات اختیاری شکست می‌خورد | FIXED |
| 025 | P1 | followup_form | ویرایش پیگیری غیرممکن | FIXED |
| 026 | P1 | advanced_search_dialog | جست‌وجوی پیشرفته همیشه خالی | FIXED |
| 027 | P2 | attachment_dialog | بدون نقطهٔ ورودی در UI | FIXED (بخش ۹) |
| 028 | P3 | notifications subsystem | هرگز راه‌اندازی/خوانده نمی‌شود | FIXED — حذف با تصمیم کاربر (بخش ۹) |
| 029 | P4 | filter_widget/saved_filters | کد مرده | FIXED (ویجت حذف؛ سرویس/DAL فیلترهای ذخیره‌شده به‌خاطر پوشش verify1/2 مانده — بخش ۹) |
| 030 | P1 | attachment_dialog | آپلود چندفایل QThread را می‌کشت | FIXED |
| 031 | P1 | attachment_service | نام فایل با timestamp ثانیه‌ای (بازنویسی) | FIXED |
| 032 | P2 | attachment_service | فایل یتیم / نوشتن غیراتمیک | FIXED |
| 033 | P0 | attachment_dialog.open_file | تزریق فرمان shell | FIXED |
| 034 | P2 | ۸ فرم | ثبت دوباره با کلیک دوم | FIXED |
| 035 | P1 | همهٔ DALها | تراکنش سرویس بی‌اثر (`conn.commit()` خام) | FIXED |
| 036 | P1 | excel_importer | ایمپورت اکسل هرگز کار نمی‌کرد | FIXED |
| 037 | P3 | goals/activities/counseling pages | موفقیت دروغین حذف | FIXED |
| 038 | P3 | services/dal | ۷۸ except بی‌صدا | FIXED |
| 039 | — | دو صفحه + ۳ ماژول + ۳ سیگنال | کد مردهٔ تأییدشده | FIXED (حذف) |
| 040 | P2 | activities_page | ویرایش رکورد اشتباه با فیلتر؛ سیگنال بدون فرستنده | FIXED |
| 041 | P4 | backup_page | نوار پیشرفت آرایشی | FIXED |

جمع: **۴۱ ایراد** — **۴۱ FIXED** (چهار تصمیم باز در بخش ۹ اجرا شد). هیچ امتیاز کلی
به برنامه داده نمی‌شود (بند ۳۴).

## وضعیت قابلیت‌ها در ۸ حالت (بند ۳۶)

| حالت | قابلیت‌ها |
|---|---|
| ۱. واقعاً کار می‌کند (اثبات با پیش/پس‌شرط) | ثبت/ویرایش/حذف مشاهده، مداخله، پیگیری، دانش‌آموز، هدف، فعالیت، جلسهٔ مشاوره؛ اختصاص معلم؛ ورود/تغییر رمز؛ جست‌وجوی پیشرفته؛ گزارش دانش‌آموز + PDF/Excel؛ گزارش والدین؛ خروجی AI (۶ قالب)؛ پشتیبان‌گیری/بازیابی/حذف پشتیبان؛ پشتیبان خودکار (شروع/توقف)؛ ایمپورت/خروجی اکسل دانش‌آموزان؛ ویرایش/افزودن/حذف کلاس؛ اطلاعات مدرسه؛ زنگولهٔ یادآور؛ Migration؛ ناوبری همهٔ ۱۳ صفحه؛ ۱۶۷ handler صفحه‌ها بدون خطا |
| ۲. کار می‌کند ولی ناقص | گزارش کلاس/معلم/عملکرد معلم: زنجیره اجرا می‌شود ولی فایل خروجی در این محیط تولید نشد (`NOT_TESTED`)؛ ویرایش اختصاص معلم (فقط ساخت دیالوگ آزموده شد) |
| ۳. دکمه/کد دارد ولی backend ندارد | — (کامبوی سال تحصیلی هدر اکنون سال فعال را عوض می‌کند — BUG-023) |
| ۴. backend دارد ولی UI ندارد | Screening (طبق تصمیم شما فقط گزارش)؛ سرویس/DAL «فیلترهای ذخیره‌شده» و AdvancedSearchService (فقط در verify1/2 استفاده می‌شوند) |
| ۵. UI و backend هست ولی اتصال ناقص | — (موارد یافت‌شده اصلاح شدند: BUG-018/019/020/021/040) |
| ۶. فقط کد مرده | فیلترهای ذخیره‌شده، RecommendationWidget، BackupDAL، SchoolReportService، report_template، analytics_models (جدول بخش ۷) |
| ۷. قابل اجرا نیست | — |
| ۸. نیازمند تست GUI واقعی | کلیک موس، دیالوگ‌های تأیید/modal، file picker، بازکردن فایل با برنامهٔ خارجی، دیالوگ خطای راه‌اندازی |

## چک‌لیست پایان کار (بند ۳۷)

| # | معیار | وضعیت |
|---|---|---|
| ۱ | کل `views/` بررسی شد | ✔ ۲۳ صفحه (+۲ صفحهٔ مردهٔ حذف‌شده)، ۱۴ دیالوگ، ۵ ویجت — Inventory ایستا + اجرای واقعی |
| ۲ | همهٔ Buttonها/Actionهای مهم | ✔ ۱۷۷ دکمه؛ ۱۶۷ handler اجرا شد؛ ۵ دکمهٔ تزئینی رفع (۱ منتظر تصمیم) |
| ۳ | Signal/Slotهای مهم | ✔ ۳۹ سیگنال؛ بازتعریف `finished` ×۲ رفع؛ ۳ سیگنال مرده حذف؛ ۱ سیگنال بدون فرستنده رفع |
| ۴ | UI → Service → DAL → DB | ✔ ۸ فرم و ۴ صفحه با پیش/پس‌شرط |
| ۵ | Migration | ✔ (BUG-001..005) |
| ۶ | Backup/Restore | ✔ (BUG-009..017) |
| ۷ | Attachment | ✔ زنجیره (BUG-030..033)؛ نقطهٔ ورودی: تصمیم |
| ۸ | Import/Export | ✔ (BUG-036؛ خروجی‌ها F8/D13) |
| ۹ | Reportها | ✔ گزارش دانش‌آموز/والدین/AI؛ کلاس/معلم: زنجیره اجرا، فایل NOT_TESTED |
| ۱۰ | Error handling | ✔ (BUG-038، سیاست suppress) |
| ۱۱ | Thread/Worker | ✔ (بند ۲۰، جدول بخش ۵) |
| ۱۲ | Dead code | ✔ حذف تأییدشده‌ها + فهرست منتظر تصمیم |
| ۱۳ | تست‌های موجود اجرا و ارزیابی شدند | ✔ ۶۳۷ بررسی + ۲۶ unittest سبز؛ جدول ارزیابی بخش ۷ |
| ۱۴ | برچسب صریح موارد نیازمند GUI | ✔ در هر بخش |

## آزمون نهایی

| مجموعه | نتیجه |
|---|---|
| `pytest -q tests` | 26 passed |
| verify_fixes 1 … 15 | همه سبز (۵۶۰) |
| **verify_fixes16 (۱ تا ۶)** | **77 / 77** |
| `ruff check .` | All checks passed |
| `tools/ui_inventory.py --write` | `docs/ui_inventory_16.md` به‌روز |

آزمون تغییریافته در مرحلهٔ ۶: فقط فهرست‌های داخلی `verify_fixes16` (حذف سه
سیگنال مرده از فهرست «بدون گیرنده»، آستانهٔ تعداد صفحه‌ها پس از حذف دو صفحهٔ
مرده). هیچ آزمونی حذف یا غیرفعال نشد.

---

# بخش ۹ — اجرای چهار تصمیم باز (پس از تأیید کاربر)

پایه: کامیت `3223c67`. کاربر: «موارد باقی‌مانده را اصلاح کن»؛ برای BUG-028 با
پرسش صریح گزینهٔ «حذف زیرسیستم» انتخاب شد.

## BUG-023 — کامبوی سال تحصیلی هدر → FIXED
`MainWindow.on_year_changed`: انتخاب سال = **فعال‌سازی همان سال** با تأیید
(`QMessageBox.question`) → `AcademicYearDAL.set_active` → برچسب هدر → سیگنال
`academic_year_changed` → `_reload_pages_for_year()` (همهٔ متدهای `load_*`
بدون آرگومانِ صفحه‌ها و زیرصفحه‌ها؛ شکست یک صفحه بقیه را متوقف نمی‌کند).
انصراف → کامبو به سال فعال برمی‌گردد؛ سال بایگانی‌شده → هشدار و برگشت.
**تست:** verify16 H1 (انصراف/تأیید/بایگانی با پیش/پس‌شرط روی `academic_years`).

## BUG-027 — نقطهٔ ورودی پیوست‌ها → FIXED
دکمهٔ «📎 پیوست‌ها» در نوار اقدام پروندهٔ دانش‌آموز → `AttachmentDialog('student',
student_id)` (زنجیرهٔ داخلی دیالوگ در مرحلهٔ ۴ کامل آزموده شده بود). بدون
دانش‌آموز → هشدار. **تست:** verify16 H2.

## BUG-028 — زیرسیستم اعلان‌ها → FIXED (حذف)
حذف `utils/notification_scheduler.py`، `services/notification_service.py`،
`dal/notification_dal.py`، `models/notification.py` (هیچ مصرف‌کننده‌ای در برنامه
نداشتند؛ زنگولهٔ هدر از `ReminderService` زنده می‌خواند). جدول `notifications`
و تریگرهای Audit آن در اسکیما ماندند (دیتابیس‌های موجود داده دارند؛ هیچ
migration مخربی اجرا نمی‌شود). **آزمون‌های تطبیق‌داده‌شده (به‌خاطر حذف
موضوع‌شان، نه برای سبزشدن):** verify8 §A (بررسی «delete_old» → همان رگرسیون
قالب زمانی روی `utc_shift_sql`؛ بررسی متدهای زمان‌دار → مدل‌های زنده)، verify10
(ثابت‌های کلاس/متدهای زمان‌دار → مدل‌های زنده)، verify12 §F (۲ بررسی حذف) و §I
(۱ بررسی حذف)، verify14 §B6 (بدون زمان‌بند)، §G (۲ بررسی حذف)، §J (۲ بررسی
حذف)، verify15 §E (همان تریگرهای Audit با SQL مستقیم به‌جای DAL — پوشش حفظ
شد). خالص: ۷ بررسی حذف، ۴ بررسی تطبیق.

## BUG-029 — فیلترهای ذخیره‌شده → FIXED (ویجت)
`views/widgets/filter_widget.py` (بدون مصرف‌کننده) حذف شد.
`dal/saved_filter_dal.py`، `models/saved_filter.py` و
`services/advanced_search_service.py` ماندند چون `verify_fixes.py` و
`verify_fixes2.py` مستقیماً `save_filter`/`search_students` را می‌آزمایند (در
برنامه استفاده نمی‌شوند — در فهرست «منتظر تصمیم» ثبت است).

## آزمون نهایی پس از بخش ۹

| مجموعه | نتیجه |
|---|---|
| `pytest -q tests` | 26 passed |
| verify_fixes 1 … 15 | همه سبز (verify12: ۴۰، verify14: ۴۶ پس از حذف زیرسیستم اعلان‌ها) |
| **verify_fixes16** | **79 / 79** |
| `ruff check .` | All checks passed |
| جمع | **۶۳۲ بررسی** |

## فهرست نهایی کد بدون مصرف‌کنندهٔ باقی‌مانده (اطلاع)
`dal/saved_filter_dal.py` + `services/advanced_search_service.py` (پوشش
verify1/2)، `views/widgets/recommendation_widget.py` (تصمیم شما: گزارش)،
`dal/backup_dal.py`، `services/school_report_service.py` (verify2/7/8)،
`dal/screening_tool_dal.py` (Screening)، `utils/report_template.py` (verify2/3)،
`models/analytics_models.py` (verify8/10)، توابع `get_*_display` در
`config/constants.py`، کلاس‌های خطای بی‌استفاده در `utils/error_handler.py`.

---

# بخش ۱۰ — بستن همهٔ باقی‌مانده‌ها (درخواست «همهٔ کارهای باقیمانده را انجام بده»)

پایه: کامیت `85e6799`.

| مورد باقی‌مانده | اقدام | اثبات |
|---|---|---|
| RecommendationWidget (بندهای ۸ و ۹) | به‌عنوان تب «💡 پیشنهادها» در پروندهٔ دانش‌آموز سوار شد و با پروندهٔ جاری هم‌گام است؛ «ثبت مداخله» از روی پیشنهاد فرم مداخلهٔ همین صفحه را باز می‌کند. **باگ کشف‌شده هنگام سوارکردن:** نمایش پیشنهادها با `'Recommendation' object has no attribute 'priority_color'` می‌شکست (ویجت صفتی را می‌خواست که مدل نداشت) → `priority_color` به مدل افزوده شد | I1 (Generate → رکوردهای `recommendations` = تعداد نمایش؛ بدون خطا) |
| Screening | ساخته **نشد**: هیچ UI ثبتی وجود ندارد و ساخت آن قابلیت جدید است (قاعدهٔ مدیر پروژه)؛ backend حفظ شد چون لایهٔ «غربالگری» گزارش‌ها از آن می‌خواند. فقط `dal/screening_tool_dal.py` (صفر ارجاع) حذف شد | E12 |
| کد مردهٔ وابسته به آزمون‌های قدیمی | حذف شدند با تطبیق همان آزمون‌ها روی مسیر زندهٔ برنامه: `services/advanced_search_service.py` + `dal/saved_filter_dal.py` + `models/saved_filter.py` (verify1/2/3 → `ObservationDAL.get_by_student` و وجود جدول)، `dal/backup_dal.py` (verify9 → اصل «شکست حذف فایل بی‌صدا نمی‌ماند» روی `utils/backup.py`)، `services/school_report_service.py` (verify7)، `utils/report_template.py` (verify2/3 → `utils/persian_pdf.py`)، `models/analytics_models.py` (verify8/10)، ۸ تابع `get_*_display` بی‌استفاده در `config/constants.py`. کلاس‌های خطای بی‌استفاده در `utils/error_handler.py` ماندند (سلسله‌مراتب مستند؛ در docstring ارجاع دارند) | G1 (۱۸ ماژول حذف‌شده بدون ارجاع باقی‌مانده) |
| گزارش کلاس/معلم/عملکرد معلم (`NOT_TESTED` قبلی) | از مسیر صفحه تولید و PDF/Excel واقعی گرفته شد | I2 |
| ویرایش اختصاص معلم (`NOT_TESTED` قبلی) | حالت ویرایش `AssignTeacherDialog`: بارگذاری معلم فعلی، تغییر، به‌روزرسانی همان ردیف | I3 |
| `auto_logout` با دیالوگ تأیید (P4) | `logout(confirm=False)` برای خروج خودکار؛ خروج دستی همچنان تأیید می‌گیرد. **باگ جانبی رفع‌شده:** هر خروج دو ردیف Audit «logout» می‌ساخت (`logout()` و سپس `closeEvent`) → یک ردیف | I6 |
| CHECK در اسکیما (P4) | دیتابیس‌های **تازه**: `observations.behavior_type IN (مثبت/منفی/خنثی)` و `severity BETWEEN 1 AND 5`؛ دیتابیس‌های موجود عمداً بازسازی نشدند (خطر شکست راه‌اندازی روی دادهٔ نامنطبق) | I4 |
| `database/partow.db` در مخزن (P4) | از ایندکس git خارج و در `.gitignore` (همراه `logs/*.log` که هنوز ردیابی می‌شدند) | I5، verify10 §E (تطبیق‌داده‌شده) |
| نوار پیشرفت پشتیبان | فقط شروع/پایان ممکن است (SQLite backup API پیشرفت میانی نمی‌دهد) | — |
| Python 3.9/3.13 اجرای واقعی | **همچنان انجام نشد:** دانلود مفسرهای دیگر در این محیط (TLS/پروکسی) ممکن نبود؛ ادعا بر پایهٔ `vermin` و حذف تنها API ناسازگار (`makeSuite`) است | — |
| اطلاعات مدرسه در گزارش‌ها، جابه‌جایی `excel_importer` به services، حذف دسترسی مستقیم views→DAL | **عمداً انجام نشد** (قابلیت/بازسازی معماری جدید؛ خارج از قاعدهٔ «فقط رفع اشکال») | — |

## آزمون نهایی

| مجموعه | نتیجه |
|---|---|
| `pytest -q tests` | 26 passed |
| verify_fixes 1 … 15 | همه سبز |
| **verify_fixes16** | **85 / 85** |
| `ruff check .` | All checks passed |
| جمع | **۶۳۸ بررسی** |

آزمون‌های تطبیق‌داده‌شده در این بخش (به‌خاطر حذف موضوع، با حفظ نیت رگرسیون روی
کد زنده): verify1 (۱)، verify2 (۳)، verify3 (۲ اشاره)، verify7 (۱)، verify8 (۱)،
verify9 (۱)، verify10 (۲). هیچ آزمونی برای «سبزشدن» حذف نشد.

## آنچه هنوز فقط با GUI واقعی قابل اثبات است
کلیک واقعی موس، دیالوگ‌های modal/تأیید، file picker، بازکردن فایل با برنامهٔ
خارجی، پنجرهٔ خطای راه‌اندازی، اجرای دوبارهٔ برنامه پس از خروج.
