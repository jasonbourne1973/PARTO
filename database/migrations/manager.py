"""
مدیریت Migration های دیتابیس
"""

import sqlite3

from config.settings import DB_PATH, DB_VERSION
from utils.logger import get_logger

logger = get_logger(__name__)


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


def _discover_migrations():
    """
    پیدا کردن خودکار همه ماژول‌های migration

    Returns:
        dict: {شماره نسخه: ماژول}

    هر فایلی به شکل migration_vN.py در پوشه migrations که متد
    upgrade داشته باشد، ثبت می‌شود. ماژول‌هایی که import نمی‌شوند
    با هشدار رد می‌شوند تا کل ارتقاء از کار نیفتد.
    """
    import importlib

    found = {}
    for version in range(1, 100):
        module_name = f"database.migrations.migration_v{version}"
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            # ممکن است واقعاً وجود نداشته باشد؛ فقط تا اولین شکاف
            # پیش می‌رویم و بعد ادامه می‌دهیم تا شماره‌های بالاتر
            # (که ممکن است دستی اضافه شده باشند) از قلم نیفتند.
            continue
        except Exception as e:
            # (بازرسی پانزدهم) ثبت در لاگ برنامه، نه فقط چاپ در کنسول؛
            # نسخهٔ گمشده در ادامه با MigrationMissingError متوقف می‌شود.
            logger.error(f"خطا در بارگذاری {module_name}: {e}")
            continue

        if not hasattr(module, 'upgrade'):
            logger.warning(f"{module_name} متد upgrade ندارد؛ نادیده گرفته شد.")
            continue

        found[version] = module

    if not found:
        logger.warning("هیچ ماژول migration یافت نشد.")

    return found


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
        """تنظیم نسخه دیتابیس"""
        cursor = connection.cursor()
        
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
    def migrate(connection, target_version=None):
        """
        اجرای Migration تا نسخه مورد نظر
        """
        if target_version is None:
            target_version = DB_VERSION
        
        current_version = MigrationManager.get_current_version(connection)
        
        if current_version == target_version:
            print(f"✅ دیتابیس در نسخه {current_version} است. نیازی به Migration نیست.")
            return
        
        print(f"🔄 Migration از نسخه {current_version} به {target_version}")
        
        # بارگذاری ماژول‌های Migration
        #
        # ===== اصلاح مهم =====
        # نسخه قبلی فقط v1 و v2 را ثبت کرده بود:
        #     from database.migrations import migration_v1, migration_v2
        #     migrations = {1: ..., 2: ...}
        #
        # ولی در پوشه migrations شش فایل وجود دارد (v1 تا v6).
        # یعنی ارتقاء از نسخه ۲ به بالا برای v3، v4، v5 و v6 پیام
        # «Migration برای نسخه X یافت نشد» می‌داد و رد می‌شد — بدون
        # اینکه چیزی اعمال شود.
        #
        # حالا ثبت‌نام با یک تابع انجام می‌شود که هر ماژول موجود را
        # پیدا می‌کند، پس افزودن migration جدید دیگر نیاز به ویرایش
        # این فایل ندارد.
        migrations = _discover_migrations()
        
        if current_version < target_version:
            # ارتقاء
            #
            # ===== اصلاح (بازرسی دوازدهم) =====
            # نسخهٔ قبلی وقتی Migration یک نسخه را پیدا نمی‌کرد، فقط
            # «⚠️ ... یافت نشد» چاپ می‌کرد و رد می‌شد؛ بعد هم نسخهٔ
            # نهایی مُهر می‌خورد. یعنی دیتابیس ناقص، «سالم» جا زده
            # می‌شد. حالا کل بازه «قبل از اجرا» بررسی می‌شود و اگر
            # حتی یک نسخه جا افتاده باشد، هیچ‌چیز اعمال نمی‌شود و خطای
            # روشن بالا می‌آید.
            missing = [v for v in range(current_version + 1, target_version + 1)
                       if v not in migrations]
            if missing:
                raise MigrationMissingError(missing, current_version,
                                            target_version)
            for version in range(current_version + 1, target_version + 1):
                migrations[version].upgrade(connection)
                MigrationManager.set_version(connection, version)
                print(f"✅ ارتقاء به نسخه {version} انجام شد.")

        elif current_version > target_version:
            # بازگشت (Downgrade)
            missing = [v for v in range(current_version, target_version, -1)
                       if v not in migrations]
            if missing:
                raise MigrationMissingError(missing, current_version,
                                            target_version)
            for version in range(current_version, target_version, -1):
                # کاهش نسخه
                MigrationManager.set_version(connection, version - 1)

                # اجرای downgrade
                if hasattr(migrations[version], 'downgrade'):
                    migrations[version].downgrade(connection)
                    print(f"✅ بازگشت از نسخه {version} انجام شد.")


def run_migration():
    """اجرای Migration از خط فرمان"""
    connection = sqlite3.connect(DB_PATH)
    try:
        MigrationManager.migrate(connection)
        connection.commit()
        print("✅ Migration با موفقیت انجام شد.")
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در اجرای Migration: {e}")
    finally:
        connection.close()


if __name__ == "__main__":
    run_migration()