"""
مدیریت Migration های دیتابیس

(بازرسی شانزدهم — مرحلهٔ ۱)
  • کشف migrationها از روی فایل‌سیستم (migration_vN.py) بدون سقف شماره؛
  • فایلی که هست ولی بارگذاری نمی‌شود → MigrationLoadError با traceback در
    لاگ (نه «نادیده‌گرفتن» به‌عنوان نبودن)؛
  • هر گام upgrade/downgrade داخل تراکنش صریح اجرا می‌شود و شمارهٔ نسخه
    فقط پس از موفقیت همان گام نوشته می‌شود؛ شکست → rollback و
    MigrationStepError؛ نسخه هرگز جلوتر/عقب‌تر از اسکیمای واقعی نمی‌رود؛
    فایل‌های migration خودشان commit/rollback نمی‌کنند (مالک تراکنش این‌جاست)؛
  • همهٔ رخدادها با logger برنامه ثبت می‌شوند (خطاها با exc_info).
"""

import importlib
import importlib.util
import os
import re
import sqlite3

from config.settings import DB_PATH, DB_VERSION
from utils.logger import get_logger

logger = get_logger(__name__)

# نام فایل‌های migration: migration_v<عدد>.py — شمارهٔ نسخه از همین نام
# استخراج می‌شود؛ پس migration شمارهٔ ۱۰۰ یا بیشتر نیاز به تغییر این کد ندارد.
_MIGRATION_FILE_RE = re.compile(r'^migration_v(\d+)\.py$')
_MIGRATIONS_DIR = os.path.dirname(os.path.abspath(__file__))
_PACKAGE_NAME = __package__ or 'database.migrations'


class MigrationMissingError(Exception):
    """
    خطای نبودن Migration مورد نیاز (بازرسی دوازدهم)

    اگر برای ارتقا/بازگشت بین دو نسخه، حتی یک Migration در بازه
    وجود نداشته باشد، ادامه‌دادن یعنی پذیرفتن «دیتابیس
    نیمه‌ارتقایافته به‌عنوان سالم» که خطرناک است؛ پس Migration باید
    Fail شود و دقیقاً اعلام شود کدام نسخه‌ها جا افتاده‌اند.
    """

    def __init__(self, missing, current_version, target_version):
        self.missing = list(missing)
        self.current_version = current_version
        self.target_version = target_version
        super().__init__(
            f"Migration برای نسخه‌های {self.missing} یافت نشد؛ "
            f"ارتقاء از نسخه {current_version} به {target_version} متوقف شد تا "
            f"دیتابیس نیمه‌ارتقایافته مُهر «به‌روز» نخورد."
        )


class MigrationLoadError(Exception):
    """
    فایل migration وجود دارد ولی قابل استفاده نیست (بازرسی شانزدهم)

    قبلاً هر خطای import (حتی وقتی خودِ فایل موجود بود و فقط یکی از
    وابستگی‌های داخلی‌اش import نمی‌شد) با `except ImportError: continue`
    به‌معنای «این migration وجود ندارد» گرفته می‌شد و بعداً به‌صورت
    گمراه‌کننده «نسخهٔ گمشده» گزارش می‌شد. حالا فایلِ موجود که بارگذاری
    نمی‌شود یا تابع لازم را ندارد، با traceback در لاگ ثبت و Migration
    متوقف می‌شود.
    """

    def __init__(self, filename, reason):
        self.filename = filename
        self.reason = reason
        super().__init__(f"Migration «{filename}» قابل استفاده نیست: {reason}")


class MigrationStepError(Exception):
    """
    شکست اجرای یک گام Migration (بازرسی شانزدهم)

    تغییرات commit‌نشدهٔ همان گام برگردانده شده و شمارهٔ نسخهٔ دیتابیس
    تغییر نکرده است؛ پس اسکیمای واقعی و شمارهٔ ثبت‌شده هم‌خوان می‌مانند.
    """

    def __init__(self, version, direction, cause):
        self.version = version
        self.direction = direction
        self.cause = cause
        label = 'ارتقاء' if direction == 'upgrade' else 'بازگشت'
        super().__init__(
            f"{label} نسخه {version} شکست خورد و متوقف شد؛ شمارهٔ نسخهٔ دیتابیس "
            f"تغییر نکرد. علت: {type(cause).__name__}: {cause}"
        )


def _load_module_from_path(path, version):
    """بارگذاری یک فایل migration از مسیر دلخواه (برای پوشه‌های غیر از بستهٔ اصلی)"""
    module_name = f"_parto_external_migrations.migration_v{version}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"spec برای {path} ساخته نشد")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _discover_migrations(directory=None):
    """
    پیدا کردن migrationها از روی فایل‌سیستم

    Args:
        directory: پوشهٔ migrationها؛ None یعنی همین بسته
                   (`database/migrations`) که ماژول‌هایش با نام بسته‌ای
                   import می‌شوند. پوشهٔ دیگر (مثلاً در آزمون‌ها) از روی
                   مسیر فایل بارگذاری می‌شود.

    Returns:
        dict: {شماره نسخه: ماژول}

    Raises:
        MigrationLoadError: فایلی با الگوی migration_vN.py هست ولی import
            نمی‌شود یا تابع `upgrade` ندارد. traceback کامل در لاگ برنامه
            ثبت می‌شود و Migration ادامه پیدا نمی‌کند.

    نبودِ یک شماره در توالی، این‌جا خطا نیست؛ `MigrationManager.migrate`
    خودش بازهٔ لازم را بررسی و با MigrationMissingError متوقف می‌کند.
    """
    scan_dir = directory or _MIGRATIONS_DIR
    found = {}
    for filename in sorted(os.listdir(scan_dir)):
        match = _MIGRATION_FILE_RE.match(filename)
        if not match:
            continue
        version = int(match.group(1))
        try:
            if directory is None:
                module = importlib.import_module(f"{_PACKAGE_NAME}.{filename[:-3]}")
            else:
                module = _load_module_from_path(os.path.join(scan_dir, filename), version)
        except Exception as e:
            logger.error(f"بارگذاری migration «{filename}» شکست خورد: {e}", exc_info=True)
            raise MigrationLoadError(filename, f"{type(e).__name__}: {e}") from e

        if not callable(getattr(module, 'upgrade', None)):
            logger.error(f"migration «{filename}» تابع upgrade ندارد؛ Migration متوقف شد.")
            raise MigrationLoadError(filename, "تابع upgrade ندارد")

        found[version] = module

    if not found:
        logger.warning(f"هیچ فایل migration در «{scan_dir}» یافت نشد.")

    return found


def _begin_transaction(connection):
    """
    شروع تراکنش صریح، اگر تراکنشی باز نیست

    sqlite3 پایتون (حالت پیش‌فرض) فقط پیش از INSERT/UPDATE/DELETE تراکنش
    ضمنی باز می‌کند؛ دستورهای DDL مثل CREATE/ALTER/DROP بدون تراکنش صریح
    بلافاصله commit می‌شوند و در صورت شکست وسط گام، قابل بازگشت نیستند.
    """
    if not connection.in_transaction:
        connection.execute("BEGIN")


class MigrationManager:
    """مدیریت نسخه‌بندی و اجرای Migration"""
    
    @staticmethod
    def get_current_version(connection):
        """دریافت نسخه فعلی دیتابیس"""
        cursor = connection.cursor()
        
        # بررسی وجود جدول version
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='db_version'
        """)
        
        if cursor.fetchone() is None:
            return 0
        
        cursor.execute("SELECT version FROM db_version LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else 0
    
    @staticmethod
    def set_version(connection, version):
        """تنظیم نسخه دیتابیس (DROP/CREATE/INSERT در یک تراکنش)"""
        cursor = connection.cursor()

        # (بازرسی شانزدهم) اگر گام migration تراکنش را با commit داخلی
        # بسته باشد، این سه دستور باید خودشان یک واحد اتمیک باشند.
        _begin_transaction(connection)

        # حذف جدول قبلی اگر وجود دارد
        cursor.execute("DROP TABLE IF EXISTS db_version")
        
        # ایجاد جدول جدید
        cursor.execute("""
            CREATE TABLE db_version (
                version INTEGER NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute(
            "INSERT INTO db_version (version) VALUES (?)",
            (version,)
        )
        connection.commit()
    
    @staticmethod
    def _run_step(connection, module, version, direction, new_version):
        """
        اجرای یک گام Migration به‌صورت «یا کامل، یا هیچ»

        ترتیب: BEGIN صریح ← اجرای upgrade/downgrade ← نوشتن شمارهٔ نسخهٔ
        جدید ← commit. اگر گام شکست بخورد، تغییرات commit‌نشده rollback
        می‌شود و شمارهٔ نسخه دست‌نخورده می‌ماند (MigrationStepError).

        (بازرسی شانزدهم — BUG-NEW-02) هیچ فایل migration دیگر خودش commit یا
        rollback نمی‌کند؛ مالک تراکنش فقط همین متد است. بنابراین شکست در هر
        نقطه‌ای از upgrade/downgrade، همهٔ تغییرات همان گام (DDL و DML) را
        برمی‌گرداند و «یا کامل، یا هیچ» واقعاً برقرار است. (اگر migrationی در
        آینده به‌اشتباه commit کند، آزمون verify_fixes16 §K آن را می‌گیرد.)
        """
        func = getattr(module, direction, None)
        if not callable(func):
            raise MigrationLoadError(
                f"migration_v{version}.py",
                f"تابع {direction} ندارد؛ {'بازگشت' if direction == 'downgrade' else 'ارتقاء'} "
                f"از این نسخه ممکن نیست و شمارهٔ نسخه تغییر نکرد")

        _begin_transaction(connection)
        try:
            func(connection)
            MigrationManager.set_version(connection, new_version)
        except Exception as e:
            logger.error(
                f"گام {direction} نسخه {version} شکست خورد؛ rollback و توقف "
                f"(شمارهٔ نسخه تغییر نکرد): {e}", exc_info=True)
            try:
                connection.rollback()
            except Exception as rollback_error:
                logger.warning(f"rollback پس از شکست گام {version} ممکن نشد: {rollback_error}",
                               exc_info=True)
            raise MigrationStepError(version, direction, e) from e

        logger.info(f"گام {direction} نسخه {version} انجام شد؛ نسخهٔ دیتابیس اکنون {new_version} است.")

    @staticmethod
    def migrate(connection, target_version=None):
        """
        اجرای Migration تا نسخه مورد نظر

        Raises:
            MigrationLoadError: فایل migration موجود ولی غیرقابل بارگذاری
            MigrationMissingError: شماره‌ای در بازهٔ لازم وجود ندارد (هیچ
                گامی اجرا نمی‌شود)
            MigrationStepError: یک گام شکست خورد؛ گام‌های قبلی معتبر و
                نسخه‌شان ثبت شده، گام شکست‌خورده rollback و نسخه دست‌نخورده
        """
        if target_version is None:
            target_version = DB_VERSION

        current_version = MigrationManager.get_current_version(connection)

        if current_version == target_version:
            logger.info(f"دیتابیس در نسخه {current_version} است؛ نیازی به Migration نیست.")
            return

        logger.info(f"Migration از نسخه {current_version} به {target_version}")

        # بارگذاری ماژول‌های Migration از روی فایل‌سیستم (بدون سقف شماره)
        migrations = _discover_migrations()

        if current_version < target_version:
            # ارتقاء — کل بازه «قبل از اجرا» بررسی می‌شود؛ اگر حتی یک
            # نسخه جا افتاده باشد، هیچ گامی اجرا نمی‌شود (بازرسی دوازدهم).
            missing = [v for v in range(current_version + 1, target_version + 1)
                       if v not in migrations]
            if missing:
                raise MigrationMissingError(missing, current_version,
                                            target_version)
            for version in range(current_version + 1, target_version + 1):
                MigrationManager._run_step(connection, migrations[version],
                                           version, 'upgrade', new_version=version)

        else:
            # بازگشت (Downgrade) — (بازرسی شانزدهم) اول downgrade، بعد
            # کاهش شمارهٔ نسخه؛ نسخهٔ قبلی برعکس عمل می‌کرد و اگر
            # downgrade شکست می‌خورد، اسکیما در نسخهٔ بالاتر می‌ماند ولی
            # شمارهٔ ثبت‌شده پایین رفته بود.
            missing = [v for v in range(current_version, target_version, -1)
                       if v not in migrations]
            if missing:
                raise MigrationMissingError(missing, current_version,
                                            target_version)
            for version in range(current_version, target_version, -1):
                MigrationManager._run_step(connection, migrations[version],
                                           version, 'downgrade', new_version=version - 1)


def run_migration():
    """اجرای Migration از خط فرمان (خروجی کنسول برای کاربر + ثبت در لاگ)"""
    connection = sqlite3.connect(DB_PATH)
    try:
        MigrationManager.migrate(connection)
        connection.commit()
        logger.info("Migration خط فرمان با موفقیت انجام شد.")
        print("✅ Migration با موفقیت انجام شد.")
        return True
    except Exception as e:
        with_rollback = True
        try:
            connection.rollback()
        except Exception:
            with_rollback = False
        logger.error(f"خطا در اجرای Migration خط فرمان: {e}", exc_info=True)
        print(f"❌ خطا در اجرای Migration: {e}"
              + ("" if with_rollback else " (rollback هم ممکن نشد)"))
        return False
    finally:
        connection.close()


if __name__ == "__main__":
    run_migration()