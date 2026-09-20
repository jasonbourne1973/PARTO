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
| ۳ | Inventory کامل صفحات (`views/pages` + `main_window`)، کنتراست، Signal/Slot | ۲، ۳، ۱۰، ۱۸، ۱۹، ۳۶ | **۳-الف انجام شد** (بخش ۳)؛ ۳-ب: دیالوگ‌ها/ویجت‌ها |
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
