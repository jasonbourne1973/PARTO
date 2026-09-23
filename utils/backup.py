"""
ابزارهای پشتیبان‌گیری و بازیابی اطلاعات - نسخه ساده (بدون رمزنگاری)
"""

import hashlib
import json
import os
import re
import shutil
import sqlite3
import threading
import zipfile
from datetime import datetime
from pathlib import Path

from config.settings import APP_VERSION
from utils.logger import get_logger
from utils.time_utils import utc_now, utc_now_iso

logger = get_logger(__name__)

# پسوند فایل پشتیبان و پسوند فایل کنارِ آن (checksum)
BACKUP_EXTENSION = '.partobak'
CHECKSUM_SUFFIX = '.sha256'

# نویسه‌های مجاز در نام پشتیبان (بازرسی شانزدهم): نام از ورودی می‌آید و
# نباید بتواند با «..» یا جداکنندهٔ مسیر از پوشهٔ پشتیبان بیرون برود.
_UNSAFE_NAME_CHARS = re.compile(r'[^\w\-.]', re.UNICODE)


class AutoBackupHandle:
    """
    دستگیرهٔ پشتیبان‌گیری خودکار (بازرسی شانزدهم)

    نسخهٔ قبلی فقط یک `threading.Thread` با حلقهٔ `while True` برمی‌گرداند
    که هیچ راهی برای توقف نداشت؛ دکمهٔ «توقف» در تنظیمات فقط مرجع را None
    می‌کرد و پشتیبان‌گیری در پس‌زمینه ادامه می‌یافت. حالا حلقه روی یک
    Event منتظر می‌ماند و `stop()` واقعاً آن را تمام می‌کند.
    """

    def __init__(self, interval_hours):
        self.interval_hours = interval_hours
        self._stop_event = threading.Event()
        self.thread = None
        self.last_result = None

    def stop(self, timeout=5):
        """درخواست توقف و انتظار (کوتاه) برای پایان نخ؛ True اگر نخ تمام شد."""
        self._stop_event.set()
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout)
        return not self.is_running()

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()

    # سازگاری با کد قدیمی که thread را نگه می‌داشت
    def is_alive(self):
        return self.is_running()

    def wait_interval(self):
        """False یعنی توقف خواسته شده است."""
        return not self._stop_event.wait(self.interval_hours * 3600)


class BackupManager:
    """مدیریت پشتیبان‌گیری و بازیابی"""
    
    def __init__(self, db_path, attachments_dir, backup_dir, encrypt=False):
        self.db_path = db_path
        self.attachments_dir = attachments_dir
        self.backup_dir = backup_dir
        self.encrypt = encrypt  # فعلاً غیرفعال است

        # ===== اصلاح مهم =====
        # بدنه این کلاس در ۱۰ نقطه از `self.logger` استفاده می‌کند
        # (create_backup، restore_backup، پاکسازی pre_restore و ...) ولی
        # `__init__` هرگز آن را مقداردهی نمی‌کرد. نتیجه:
        #
        #     AttributeError: 'BackupManager' object has no attribute 'logger'
        #
        # و چون این فراخوان‌ها داخل except هستند، خطای اصلی (مثلاً
        # «فایل checksum یافت نشد») با یک AttributeError بی‌ربط عوض
        # می‌شد؛ در create_backup هم کل عملیات به عنوان «پشتیبان‌گیری
        # ناموفق» گزارش می‌شد در حالی که مشکل چیز دیگری بود.
        #
        # از همان logger استاندارد پروژه استفاده می‌شود تا پیام‌ها در
        # logs/partow.log هم ثبت شوند. اگر به هر دلیل در دسترس نبود،
        # یک logger بی‌صدا جایگزین می‌شود تا پشتیبان‌گیری هرگز به خاطر
        # لاگ از کار نیفتد.
        try:
            from utils.logger import get_logger
            self.logger = get_logger(self.__class__.__name__)
        except Exception:  # pragma: no cover - مسیر اضطراری
            import logging
            self.logger = logging.getLogger(self.__class__.__name__)
        
        # مسیر پوشهٔ پشتیبان همیشه canonical نگه داشته می‌شود تا بررسی
        # «فایل داخل پوشهٔ پشتیبان است» در delete_backup قابل اتکا باشد.
        self.backup_dir = os.path.realpath(backup_dir)
        os.makedirs(self.backup_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # ابزارهای مسیر/نام (بازرسی شانزدهم)
    # ------------------------------------------------------------------
    @staticmethod
    def sanitize_backup_name(name):
        """
        نام پشتیبان را به یک نام فایل امن تبدیل می‌کند

        فقط حروف/اعداد/خط تیره/زیرخط/نقطه می‌مانند؛ جداکنندهٔ مسیر و «..»
        حذف می‌شوند تا فایل هرگز بیرون از پوشهٔ پشتیبان ساخته نشود.
        """
        base = os.path.basename(str(name or '').strip().replace('\\', '/'))
        if base.lower().endswith(BACKUP_EXTENSION):
            base = base[:-len(BACKUP_EXTENSION)]
        cleaned = _UNSAFE_NAME_CHARS.sub('_', base).strip('.')
        while '..' in cleaned:
            cleaned = cleaned.replace('..', '.')
        return cleaned

    def _is_inside_backup_dir(self, path):
        """آیا مسیر canonical داده‌شده داخل پوشهٔ پشتیبان است؟"""
        try:
            return os.path.commonpath([self.backup_dir, path]) == self.backup_dir
        except ValueError:
            # درایوهای متفاوت در ویندوز
            return False

    def _resolve_backup_path(self, backup_file):
        """
        اعتبارسنجی مسیر یک فایل پشتیبان برای عملیات مخرب (حذف)

        Returns:
            (path | None, error_message | None)
        """
        if not backup_file:
            return None, "❌ مسیر فایل پشتیبان مشخص نشده است."
        real = os.path.realpath(str(backup_file))
        if not self._is_inside_backup_dir(real) or real == self.backup_dir:
            return None, ("❌ این فایل داخل پوشهٔ پشتیبان نیست؛ برای حفاظت از فایل‌های دیگر، "
                          "حذف انجام نشد.")
        if not real.lower().endswith(BACKUP_EXTENSION):
            return None, f"❌ فقط فایل‌های {BACKUP_EXTENSION} قابل حذف‌اند."
        if os.path.islink(str(backup_file)):
            return None, "❌ پیوند نمادین به‌عنوان فایل پشتیبان پذیرفته نمی‌شود."
        if not os.path.isfile(real):
            return None, "❌ فایل پشتیبان وجود ندارد."
        return real, None

    def adopt_legacy_backups(self, legacy_dir):
        """
        انتقال یک‌بارهٔ پشتیبان‌های پوشهٔ قدیمی (views/backups) به پوشهٔ استاندارد

        نسخه‌های قبلی صفحهٔ پشتیبان‌گیری فایل‌ها را داخل درخت کد (`views/backups`)
        می‌ساختند. برای اینکه پشتیبان‌های کاربران گم نشوند، هنگام راه‌اندازی
        صفحه، فایل‌های آن پوشه (اگر باشد) به پوشهٔ استاندارد منتقل می‌شوند؛
        فایل هم‌نام موجود بازنویسی نمی‌شود.

        Returns:
            list[str]: نام فایل‌های منتقل‌شده
        """
        moved = []
        try:
            legacy_real = os.path.realpath(legacy_dir)
            if legacy_real == self.backup_dir or not os.path.isdir(legacy_real):
                return moved
            for entry in os.listdir(legacy_real):
                if not (entry.endswith((BACKUP_EXTENSION, BACKUP_EXTENSION + CHECKSUM_SUFFIX))
                        or entry == 'backup_log.txt'):
                    continue
                src = os.path.join(legacy_real, entry)
                dst = os.path.join(self.backup_dir, entry)
                if not os.path.isfile(src):
                    continue
                if entry == 'backup_log.txt' and os.path.exists(dst):
                    # لاگ قدیمی به انتهای لاگ فعلی افزوده می‌شود، نه بازنویسی
                    with open(src, encoding='utf-8', errors='replace') as old_log, \
                            open(dst, 'a', encoding='utf-8') as new_log:
                        new_log.write(old_log.read())
                    os.remove(src)
                    moved.append(entry)
                    continue
                if os.path.exists(dst):
                    continue
                shutil.move(src, dst)
                moved.append(entry)
            if moved:
                self.logger.info(
                    f"{len(moved)} فایل پشتیبان از پوشهٔ قدیمی «{legacy_real}» به "
                    f"«{self.backup_dir}» منتقل شد.")
        except OSError as e:
            self.logger.warning(f"انتقال پشتیبان‌های قدیمی ممکن نشد: {e}")
        return moved

    def create_backup(self, name=None, user_id=None, user_name=None):
        """
        ایجاد نسخه پشتیبان کامل
        
        Returns:
            dict: اطلاعات Backup ایجاد شده
        """
        tmp_db_snapshot = None
        tmp_zip = None
        try:
            # ایجاد نام فایل (امن‌شده؛ بازرسی شانزدهم)
            if not name:
                timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
                name = f"backup_{timestamp}"
            safe_name = self.sanitize_backup_name(name)
            if not safe_name:
                raise ValueError(f"نام پشتیبان معتبر نیست: {name!r}")
            if safe_name != str(name):
                self.logger.warning(
                    f"نام پشتیبان «{name}» به «{safe_name}» امن‌سازی شد.")
            name = safe_name

            backup_file = os.path.join(self.backup_dir, f"{name}{BACKUP_EXTENSION}")
            # نوشتن اتمیک: اول در فایل موقتِ همان پوشه، بعد جایگزینی.
            # اگر وسط کار (دیسک پر، قطع برق) شکست بخورد، هیچ فایل
            # .partobak نیمه‌کاره‌ای در فهرست پشتیبان‌ها ظاهر نمی‌شود.
            tmp_zip = backup_file + '.tmp'
            
            # ===== اصلاح مهم: پشتیبان از دیتابیس زنده =====
            # نسخه قبلی فایل SQLite را در حالی که برنامه باز و در حال
            # نوشتن بود مستقیم ZIP می‌کرد:
            #     zipf.write(self.db_path, "database/partow.db")
            #
            # اگر وسط نوشتن تراکنش این اتفاق می‌افتاد، فایل پشتیبان
            # «پاره» (torn) می‌شد: صفحات دیتابیس با هم هم‌خوان نبودند و
            # موقع بازیابی با «database disk image is malformed»
            # مواجه می‌شدید. چون checksum هم هرگز راستی‌آزمایی
            # نمی‌شد، این خرابی تا لحظه بازیابی دیده نمی‌شد.
            #
            # حالا از API رسمی online backup خود sqlite3 استفاده
            # می‌شود. این API یک نسخه سازگار و کامل می‌گیرد، حتی وقتی
            # نوشتن در جریان است.
            #
            # ===== اصلاح (بازرسی دوازدهم) =====
            # نسخهٔ قبلی اگر online backup خطا می‌داد، بی‌صدا به
            # «کپی مستقیم فایل فعال» برمی‌گشت؛ یعنی دقیقاً همان
            # پشتیبانِ «پاره» که قرار بود حذف شود، با ظاهر «موفق»
            # تحویل داده می‌شد. حالا شکستِ online backup = شکستِ
            # عملیات با پیام روشن؛ هرگز فایل فعال SQLite مستقیم کپی
            # نمی‌شود چون سلامت آن قابل تضمین نیست.
            #
            # ===== اصلاح (بازرسی چهاردهم) =====
            # ۱) اگر فایل دیتابیس اصلاً وجود نداشت، نسخهٔ قبلی یک ZIP
            #    «بدون دیتابیس» می‌ساخت و success=True برمی‌گرداند؛ یعنی
            #    پشتیبان ظاهراً موفق ولی بی‌فایده. حالا شکست روشن.
            # ۲) اسنپ‌شات قبل از بسته‌بندی با integrity_check راستی‌آزمایی
            #    می‌شود تا هر پشتیبانی که «موفق» تحویل می‌شود، از یک
            #    اسنپ‌شات معتبر SQLite ساخته شده باشد.
            if not os.path.exists(self.db_path):
                raise RuntimeError(
                    f"فایل دیتابیس برای پشتیبان‌گیری یافت نشد: {self.db_path}")

            tmp_db_snapshot = os.path.join(self.backup_dir, f"{name}.db.tmp")
            try:
                if os.path.exists(tmp_db_snapshot):
                    os.remove(tmp_db_snapshot)
                src = sqlite3.connect(self.db_path)
                try:
                    dst = sqlite3.connect(tmp_db_snapshot)
                    try:
                        src.backup(dst)      # کپی سازگار و اتمیک
                        # (بازرسی شانزدهم) اسنپ‌شات حالت WAL منبع را به ارث
                        # می‌برد؛ با تبدیل به journal_mode=DELETE همهٔ صفحات
                        # داخل خودِ فایل .db می‌نشینند و فایل خودبسنده است
                        # (قبلاً کنار هر پشتیبان دو فایل .db.tmp-wal/-shm
                        # جا می‌ماند). دیتابیس بازیابی‌شده هنگام بازکردن در
                        # برنامه دوباره WAL می‌شود.
                        dst.execute("PRAGMA journal_mode=DELETE")
                    finally:
                        dst.close()
                finally:
                    src.close()
            except (sqlite3.Error, OSError) as e:
                self._remove_quietly(tmp_db_snapshot)
                raise RuntimeError(
                    "پشتیبان‌گیری آنلاین از دیتابیس ناموفق بود و کپی مستقیم "
                    f"فایل فعال مجاز نیست (خطر پشتیبان ناسالم): {e}"
                ) from e

            snapshot_ok, snapshot_detail = self._verify_sqlite_file(tmp_db_snapshot)
            if not snapshot_ok:
                self._remove_quietly(tmp_db_snapshot)
                raise RuntimeError(
                    f"اسنپ‌شات دیتابیس معتبر نیست؛ پشتیبان ساخته نشد: {snapshot_detail}")

            # ایجاد فایل ZIP (در فایل موقت)
            self._remove_quietly(tmp_zip)
            with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. دیتابیس (از اسنپ‌شات سازگار و راستی‌آزمایی‌شده)
                zipf.write(tmp_db_snapshot, "database/partow.db")
                
                # 2. فایل‌های پیوست
                if os.path.exists(self.attachments_dir):
                    for root, dirs, files in os.walk(self.attachments_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join("attachments", os.path.relpath(file_path, self.attachments_dir))
                            zipf.write(file_path, arcname)
                
                # 3. متادیتا
                metadata = {
                    'name': name,
                    'created_at': utc_now_iso(),
                    'created_by': user_id,
                    'created_by_name': user_name or 'سیستم',
                    'db_file': os.path.basename(self.db_path),
                    'attachments_count': self._count_attachments(),
                    # (بازرسی دوازدهم) نسخه از همان منبع اصلی برنامه؛
                    # دیگر hard-code جداگانه نیست تا سازگاری پشتیبان با
                    # نسخهٔ برنامه قابل تشخیص بماند.
                    'version': APP_VERSION,
                    'encrypted': False,
                }
                zipf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))

            # راستی‌آزمایی ZIP نوشته‌شده پیش از نهایی‌کردن
            with zipfile.ZipFile(tmp_zip, 'r') as zipf:
                bad = zipf.testzip()
                if bad is not None:
                    raise RuntimeError(f"فایل پشتیبان نوشته‌شده سالم نیست: {bad}")

            # محاسبه checksum روی فایل موقت (همان بایت‌ها پس از جایگزینی)
            checksum = self._calculate_checksum(tmp_zip)

            # جایگزینی اتمیک
            os.replace(tmp_zip, backup_file)
            tmp_zip = None

            # ===== اصلاح =====
            # checksum محاسبه می‌شد ولی هیچ‌جا ذخیره نمی‌شد، پس موقع
            # بازیابی چیزی برای مقایسه وجود نداشت. حالا کنار فایل نوشته
            # می‌شود تا در restore قابل راستی‌آزمایی باشد.
            # (بازرسی شانزدهم) الگوریتم واقعاً SHA-256 است (قبلاً MD5 در
            # فایلی با پسوند .sha256 نوشته می‌شد).
            sidecar = backup_file + CHECKSUM_SUFFIX
            checksum_saved = True
            try:
                with open(sidecar, 'w', encoding='utf-8') as f:
                    f.write(checksum)
            except OSError as e:
                checksum_saved = False
                self.logger.warning(f"خطا در ذخیره checksum: {e}")

            # ثبت در لاگ
            self._log_backup_operation('create', name, user_id, user_name)

            size = os.path.getsize(backup_file)
            message = f"✅ Backup با موفقیت در {backup_file} ایجاد شد."
            if not checksum_saved:
                message += "\n⚠️ فایل checksum کنار آن ذخیره نشد؛ هنگام بازیابی یکپارچگی راستی‌آزمایی نخواهد شد."
            return {
                'success': True,
                'file': backup_file,
                'name': name,
                'size': size,
                'size_display': self._format_size(size),
                'checksum': checksum,
                'checksum_saved': checksum_saved,
                'created_at': metadata['created_at'],
                'created_by': user_id,
                'message': message,
            }

        except Exception as e:
            self.logger.error(f"خطا در ایجاد Backup: {e}", exc_info=True)
            return {
                'success': False,
                'message': f"❌ خطا در ایجاد Backup: {e!s}"
            }
        finally:
            # هیچ فایل موقتی (اسنپ‌شات، ژورنال‌های آن یا ZIP نیمه‌کاره) باقی نمی‌ماند
            if tmp_db_snapshot:
                for suffix in ('', '-wal', '-shm', '-journal'):
                    self._remove_quietly(tmp_db_snapshot + suffix)
            if tmp_zip:
                self._remove_quietly(tmp_zip)
    
    def _quiesce_database(self):
        """
        آماده‌سازی دیتابیس برای بازنویسیِ امن فایل

        ===== 🔴 چرا این متد لازم است؟ (باگ بحرانی بازیابی) =====
        دیتابیس برنامه در حالت WAL اجرا می‌شود:

            PRAGMA journal_mode = WAL     (در database/connection.py)

        یعنی فایل‌های partow.db-wal و partow.db-shm کنار partow.db
        وجود دارند و تراکنش‌های ثبت‌شدهٔ checkpoint‌نشده داخل -wal
        هستند. هنگام بازکردن دیتابیس، SQLite محتوای -wal را روی فایل
        اصلی «بازپخش» می‌کند.

        نسخهٔ قبلی restore_backup فقط فایل .db را با نسخهٔ پشتیبان
        جایگزین می‌کرد (یک کپی سادهٔ فایل، بدون بستن اتصال‌ها)؛ یعنی
        -wal و -shm دست‌نخورده می‌ماندند. نتیجه: WAL قدیمی (مربوط به وضعیتِ قبل از
        بازیابی، شامل همان حذف‌هایی که کاربر می‌خواست برگرداند) روی
        دیتابیسِ بازیابی‌شده بازپخش می‌شد و **بازیابی عملاً بی‌اثر
        می‌ماند** — در حالی که متد `{'success': True}` و پیام
        «✅ بازیابی با موفقیت انجام شد» برمی‌گرداند.

        تست عملی (قبل از اصلاح):
            ۳ دانش‌آموز ثبت شد ← پشتیبان گرفته شد ← همه حذف شدند
            ← restore_backup() → success=True
            ← تعداد دانش‌آموز: ۰   (انتظار: ۳)
            ← اندازهٔ -wal باقی‌مانده: ۱٫۹ مگابایت

        با اجرای همین روش درست (بستن اتصال + پاک‌کردن -wal/-shm + کپی)
        نتیجهٔ همان تست ۳ شد.

        علاوه بر این، بازنویسی فایل .db زیر پای یک اتصال **باز** SQLite
        رفتار تعریف‌نشده است؛ پس اول اتصال بسته می‌شود.

        (بازرسی دوازدهم) چون هر نخ اتصال خودش را دارد، این‌جا همهٔ
        اتصال‌ها (نخ رابط کاربری، زمان‌بند اعلان‌ها، ...) با close_all
        بسته می‌شوند؛ هر نخ با استفادهٔ بعدی اتصال تازه می‌گیرد.
        """
        # ۱) checkpoint و بستن اتصال‌های باز همهٔ نخ‌ها
        try:
            from database.connection import DatabaseConnection
            # checkpoint/rollback/close هر اتصال + صفرشدن وضعیت تراکنش
            DatabaseConnection().close_all()
        except Exception as e:
            self.logger.warning(f"بستن اتصال دیتابیس قبل از بازیابی ممکن نشد: {e}")

        # ۲) پاک کردن فایل‌های ژورنال
        return self._remove_journal_files()

    def _remove_journal_files(self):
        """حذف partow.db-wal و partow.db-shm کنار دیتابیس"""
        removed = []
        for ext in ('-wal', '-shm'):
            path = self.db_path + ext
            try:
                if os.path.exists(path):
                    os.remove(path)
                    removed.append(os.path.basename(path))
            except OSError as e:
                self.logger.warning(f"حذف {os.path.basename(path)} ممکن نشد: {e}")
        return removed

    # اعضای مجاز فایل پشتیبان: فقط همین‌ها پذیرفته می‌شوند
    _ALLOWED_BACKUP_MEMBERS = ('metadata.json', 'database/', 'attachments/')

    def _safe_extract(self, zipf, extract_dir):
        """
        استخراج امن فایل پشتیبان (بازرسی دوازدهم)

        نسخهٔ قبلی همهٔ اعضای ZIP را یک‌جا و بدون هیچ اعتبارسنجی
        استخراج می‌کرد؛ یک ZIP مخرب با عضوی مثل `../../x` می‌توانست خارج
        از پوشهٔ بازیابی فایل بنویسد (Path Traversal). حالا:
          • مسیر هر عضو نرمال و بررسی می‌شود؛ مسیر مطلق، `..` و
            جداکنندهٔ معکوس → خطا و توقف بازیابی؛
          • مقصد نهایی حتماً باید داخل extract_dir بماند؛
          • فقط اعضای موردانتظار پشتیبان (دیتابیس/پیوست‌ها/متادیتا)
            پذیرفته می‌شوند و بقیه با هشدار رد می‌شوند.
        """
        base = os.path.realpath(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)
        for member in zipf.infolist():
            name = member.filename or ''
            if not name or name.endswith('/'):
                continue
            normalized = os.path.normpath(name.replace('\\', '/'))
            parts = normalized.split('/')
            if (not normalized or normalized.startswith('..')
                    or os.path.isabs(name) or os.path.isabs(normalized)
                    or '..' in parts or '\\' in name
                    or ':' in name or '\x00' in name):
                raise ValueError(
                    f"عضو نامعتبر در فایل پشتیبان (احتمال Path Traversal): {name}")
            if not (normalized == 'metadata.json'
                    or normalized.startswith(('database/', 'attachments/'))):
                self.logger.warning(
                    f"عضو ناشناختهٔ پشتیبان نادیده گرفته شد: {name}")
                continue
            target = os.path.realpath(os.path.join(extract_dir, normalized))
            if target != base and not target.startswith(base + os.sep):
                raise ValueError(
                    f"عضو پشتیبان خارج از پوشهٔ بازیابی است: {name}")
            zipf.extract(member, extract_dir)

    def _remove_quietly(self, path):
        """حذف فایل موقت؛ شکستِ حذف فقط در لاگ دیباگ ثبت می‌شود."""
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as e:
            self.logger.debug(f"حذف فایل موقت ممکن نشد ({path}): {e}")

    @staticmethod
    def _verify_sqlite_file(path, label="دیتابیس"):
        """
        راستی‌آزمایی یک فایل SQLite (اسنپ‌شات پشتیبان یا دیتابیس بازیابی‌شده)

        فایل فقط‌خواندنی باز می‌شود (بدون ساختن فایل تازه اگر وجود
        نداشته باشد)، integrity_check اجرا و تعداد جدول‌ها بررسی می‌شود.
        """
        if not os.path.exists(path):
            return False, f"{label} وجود ندارد: {path}"
        try:
            uri = Path(os.path.abspath(path)).as_uri() + "?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            try:
                result = conn.execute("PRAGMA integrity_check").fetchone()
                tables = conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
                ).fetchone()[0]
            finally:
                conn.close()
        except sqlite3.Error as e:
            return False, f"{label} باز نمی‌شود: {e}"

        if not result or result[0] != 'ok':
            return False, f"{label} سالم نیست: {result}"
        if tables < 10:
            return False, f"{label} فقط {tables} جدول دارد"
        return True, f"{tables} جدول، integrity_check = ok"

    def _verify_restored_database(self):
        """
        راستی‌آزمایی اینکه دیتابیس بازیابی‌شده واقعاً سالم و خواندنی است

        بدون این بررسی، متد حتی وقتی کپی هیچ اثری نکرده بود هم
        `success: True` برمی‌گرداند.
        """
        return self._verify_sqlite_file(self.db_path, "دیتابیس بازیابی‌شده")

    def restore_backup(self, backup_file, user_id=None, user_name=None):
        """
        بازیابی از فایل پشتیبان با تأیید و ثبت
        
        Returns:
            dict: نتیجه عملیات
        """
        # در همهٔ مسیرهای خروج (موفق/نیمه‌موفق/استثنا) وضعیت این دو
        # متغیر لازم است؛ پیش از try مقداردهی می‌شوند تا finally هم
        # وقتی خطا پیش از ساخته‌شدنشان رخ دهد، خطای NameError ندهد.
        safety_copy = None
        pre_restore_file = None
        try:
            if not os.path.exists(backup_file):
                return {
                    'success': False,
                    'message': f"❌ فایل Backup وجود ندارد: {backup_file}"
                }
            
            # ===== اصلاح مهم: راستی‌آزمایی یکپارچگی =====
            # نسخه قبلی checksum را محاسبه می‌کرد و بعد... هیچ کاری
            # با آن نمی‌کرد. یعنی فایل پشتیبان خراب یا دستکاری‌شده هم
            # بدون هیچ هشداری روی دیتابیس فعال بازنویسی می‌شد.
            # حالا اگر فایل .sha256 کنار پشتیبان باشد، مقایسه می‌شود
            # و در صورت عدم تطابق عملیات متوقف می‌شود.
            checksum = self._calculate_checksum(backup_file)

            expected = self._read_sidecar(backup_file)
            if expected is not None:
                if not self._checksum_matches(backup_file, expected):
                    return {
                        'success': False,
                        'message': (
                            "❌ فایل پشتیبان سالم نیست یا دستکاری شده است.\n"
                            f"checksum ثبت‌شده: {expected[:16]}...\n"
                            f"checksum فعلی:    {checksum[:16]}...\n\n"
                            "بازیابی انجام نشد تا دیتابیس فعلی خراب نشود."
                        )
                    }
            else:
                self.logger.warning(
                    f"فایل checksum برای {os.path.basename(backup_file)} یافت نشد؛ "
                    "یکپارچگی راستی‌آزمایی نمی‌شود."
                )

            # بررسی اینکه ZIP واقعاً باز می‌شود (قبل از هر تغییری)
            try:
                with zipfile.ZipFile(backup_file, 'r') as zipf:
                    bad = zipf.testzip()
                    if bad is not None:
                        return {
                            'success': False,
                            'message': f"❌ فایل پشتیبان خراب است: {bad}"
                        }
            except zipfile.BadZipFile as e:
                return {
                    'success': False,
                    'message': f"❌ فایل پشتیبان معتبر نیست: {e}"
                }

            # ایجاد Backup از وضعیت فعلی قبل از Restore
            # ===== اصلاح =====
            # نسخه قبلی در هر بازیابی یک پشتیبان به نام «pre_restore»
            # می‌ساخت و هرگز پاکش نمی‌کرد. بعد از چند بار بازیابی،
            # چندین فایل چندصد مگابایتی روی دیسک تلنبار می‌شد و هر
            # بار قبلی بی‌صدا بازنویسی می‌شد.
            # حالا قبل از ساخت، نمونه‌های قدیمی پاک می‌شوند.
            self._cleanup_pre_restore_files()

            pre_restore = self.create_backup("pre_restore", user_id, user_name)
            pre_restore_file = pre_restore.get('file')
            if not pre_restore['success']:
                return {
                    'success': False,
                    'message': f"❌ امکان ایجاد Backup از وضعیت فعلی وجود ندارد: {pre_restore.get('message')}"
                }
            
            # استخراج فایل (امن در برابر Path Traversal — بازرسی دوازدهم)
            extract_dir = os.path.join(self.backup_dir, "temp_restore")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)

            with zipfile.ZipFile(backup_file, 'r') as zipf:
                self._safe_extract(zipf, extract_dir)

            # بازیابی دیتابیس
            db_backup = os.path.join(extract_dir, "database", "partow.db")
            if not os.path.exists(db_backup):
                # ===== اصلاح (بازرسی سوم) =====
                # قبلاً اگر فایل پشتیبان هیچ دیتابیسی نداشت، این شاخه
                # بی‌صدا رد می‌شد و متد در پایان `success: True` با پیام
                # «بازیابی با موفقیت انجام شد» برمی‌گرداند — یعنی یک
                # موفقیت دروغین برای عملیاتی که هیچ کاری نکرده بود.
                shutil.rmtree(extract_dir, ignore_errors=True)
                return {
                    'success': False,
                    'message': "❌ فایل پشتیبان شامل دیتابیس نیست؛ "
                               "بازیابی انجام نشد."
                }

            # ===== 🔴 اصلاح بحرانی (بازرسی سوم) =====
            # ۱) اتصال باز بسته و فایل‌های ژورنال WAL پاک می‌شوند، وگرنه
            #    WAL قدیمی روی دیتابیس بازیابی‌شده بازپخش می‌شود و
            #    بازیابی بی‌اثر می‌ماند (توضیح کامل در _quiesce_database).
            #
            # (بازرسی دوازدهم) کل پنجرهٔ «بستن اتصال‌ها ← جایگزینی ←
            # راستی‌آزمایی» زیر قفل سراسری دیتابیس انجام می‌شود تا نخ
            # دیگری (مثلاً زمان‌بند اعلان‌ها) وسط بازیابی اتصال تازه
            # باز نکند و روی فایل نیمه‌جایگزین‌شده ننویسد.
            #
            # ===== اصلاح (بازرسی چهاردهم) — اول اعتبارسنجی، بعد جایگزینی =====
            # نسخهٔ قبلی فایل استخراج‌شده را روی دیتابیس فعال کپی می‌کرد و
            # «بعد» سلامتش را می‌سنجید؛ اگر عضو database/partow.db خراب
            # یا اصلاً SQLite نبود، دیتابیس فعال با آن بازنویسی و برنامه
            # عملاً از کار می‌افتاد (تست عملی: بعد از restore ناموفق،
            # «file is not a database»). حالا:
            #   ۱) فایل استخراج‌شده قبل از هر تغییری راستی‌آزمایی می‌شود؛
            #   ۲) دیتابیس فعلی (پس از quiesce) کنار گذاشته می‌شود و اگر
            #      راستی‌آزمایی پس از جایگزینی شکست خورد، دقیقاً همان
            #      فایل برمی‌گردد — بدون اتکا به pre_restore.
            extracted_ok, extracted_detail = self._verify_sqlite_file(
                db_backup, "دیتابیس داخل فایل پشتیبان")
            if not extracted_ok:
                shutil.rmtree(extract_dir, ignore_errors=True)
                return {
                    'success': False,
                    'message': (f"❌ فایل پشتیبان دیتابیس معتبری ندارد: "
                                f"{extracted_detail}\n\n"
                                "بازیابی انجام نشد و دیتابیس فعلی دست‌نخورده ماند.")
                }

            from database.connection import DB_THREAD_LOCK
            safety_copy = self.db_path + '.restore_safety'
            with DB_THREAD_LOCK:
                journal_removed = self._quiesce_database()

                # ۲) کنارگذاشتن دیتابیس فعلی و جایگزینی فایل
                self._remove_quietly(safety_copy)
                had_previous = os.path.exists(self.db_path)
                if had_previous:
                    os.replace(self.db_path, safety_copy)
                try:
                    shutil.copy2(db_backup, self.db_path)
                except Exception as copy_error:
                    if had_previous:
                        os.replace(safety_copy, self.db_path)
                    raise RuntimeError(
                        f"جایگزینی فایل دیتابیس ممکن نشد: {copy_error}") from copy_error

                # ۳) ژورنال‌های احتمالیِ باقی‌مانده دوباره پاک شوند
                journal_removed += self._remove_journal_files()

                # ۴) راستی‌آزمایی اینکه بازیابی واقعاً اثر کرده
                healthy, detail = self._verify_restored_database()
                if not healthy:
                    if had_previous:
                        self._remove_quietly(self.db_path)
                        os.replace(safety_copy, self.db_path)
                        self._remove_journal_files()
                    shutil.rmtree(extract_dir, ignore_errors=True)
                    return {
                        'success': False,
                        'message': f"❌ بازیابی کامل نشد: {detail}\n\n"
                                   "دیتابیس قبلی سر جای خود برگردانده شد. "
                                   f"پشتیبانِ وضعیت قبلی هم در این فایل هست: "
                                   f"{pre_restore.get('file')}"
                    }
                # فایل safety_copy تا پایان بازیابی پیوست‌ها نگه داشته
                # می‌شود؛ اگر خودِ جایگزینی دیتابیس نیمه‌کاره بماند، همین
                # فایل نسخهٔ قبلی را برمی‌گرداند. در پایانِ عملیات (هر
                # مسیری که باشد) این فایل پاک می‌شود و نسخهٔ قبلی دیتابیس
                # در پشتیبان pre_restore محفوظ می‌ماند.
            
            # بازیابی فایل‌های پیوست
            # (بازرسی شانزدهم) نسخهٔ قبلی اول پوشهٔ پیوست‌های فعلی را پاک
            # می‌کرد و بعد کپی می‌کرد؛ اگر کپی وسط کار شکست می‌خورد، هم
            # پیوست‌های قدیمی از دست رفته بودند هم جدیدها ناقص بودند.
            # حالا پوشهٔ فعلی کنار گذاشته می‌شود و فقط پس از کپی موفق حذف
            # می‌شود؛ در شکست، همان پوشه برمی‌گردد و نتیجه صریح می‌گوید
            # «دیتابیس بازیابی شد ولی پیوست‌ها نه».
            attachments_backup = os.path.join(extract_dir, "attachments")
            attachments_restored = None
            attachments_error = None
            if os.path.exists(attachments_backup):
                attachments_restored, attachments_error = self._swap_attachments_dir(
                    attachments_backup)

            # ثبت در لاگ
            self._log_backup_operation('restore', os.path.basename(backup_file), user_id, user_name)

            if attachments_restored is False:
                # ===== تصمیم طراحی (بازبینی نهایی — قرارداد بازیابی) =====
                # قرارداد مستندشده در docs/tech_audit_16_fa.md (BUG-014) و
                # آزمون B8 در verify_fixes16.py: بخش اصلی بازیابی (دیتابیس)
                # از پشتیبان نصب می‌شود و شکست پیوست‌ها به‌صورت صریح
                # (attachments_restored=False + پیام آغازشده با ⚠️) گزارش
                # می‌شود. پوشهٔ پیوست‌های قبلی هم — به لطف
                # _swap_attachments_dir — دست‌نخورده برمی‌گردد، پس خطای کپی
                # هرگز به ازدست‌رفتن فایل‌ها منجر نمی‌شود.
                #
                # نسخهٔ پیشین در این حالت کل بازیابی دیتابیس را هم برمی‌گرداند
                # و success=False می‌داد؛ یعنی رفتار با همین قرارداد و آزمون
                # نمی‌خواند. برای بازگشت کامل، کاربر همان پشتیبان pre_restore
                # را دارد (نامش در پیام می‌آید) و فایل ایمنی هم پاک می‌شود.
                return {
                    'success': True,
                    'message': (
                        f"⚠️ بازیابی دیتابیس از "
                        f"{os.path.basename(backup_file)} انجام شد، اما "
                        f"پیوست‌ها بازیابی نشدند.\n"
                        f"علت: {attachments_error}\n\n"
                        "پیوست‌های فعلی دست‌نخورده باقی مانده‌اند. برای "
                        "بازگشت به وضعیت قبل از این بازیابی، پشتیبان "
                        f"«{os.path.basename(pre_restore_file or '')}» را "
                        "بازیابی کنید."
                    ),
                    'pre_restore_file': pre_restore.get('file'),
                    'checksum': checksum,
                    'journal_removed': journal_removed,
                    'detail': detail,
                    'attachments_restored': False,
                    'attachments_error': attachments_error,
                }

            # فقط پس از موفقیت DB و پیوست‌ها، فایل safety حذف می‌شود.
            self._remove_quietly(safety_copy)
            message = (
                f"✅ بازیابی با موفقیت از {os.path.basename(backup_file)} "
                f"انجام شد.\n({detail})\n\n"
                "برای اطمینان، برنامه را یک بار ببندید و دوباره باز کنید "
                "تا همهٔ صفحه‌ها دادهٔ بازیابی‌شده را نشان دهند."
            )
            return {
                'success': True,
                'message': message,
                'pre_restore_file': pre_restore.get('file'),
                'checksum': checksum,
                'journal_removed': journal_removed,
                'detail': detail,
                'attachments_restored': attachments_restored,
                'attachments_error': attachments_error,
            }

        except Exception as e:
            self.logger.error(f"خطا در بازیابی: {e}", exc_info=True)
            backup_hint = ""
            if pre_restore_file and os.path.exists(pre_restore_file):
                backup_hint = (
                    "\nپشتیبان وضعیت قبل از این عملیات همچنان موجود است: "
                    f"{os.path.basename(pre_restore_file)}"
                )
            return {
                'success': False,
                'message': f"❌ خطا در بازیابی: {e!s}{backup_hint}"
            }
        finally:
            # پوشهٔ استخراج موقت در هر حالت (موفق/ناموفق/استثنا) پاک می‌شود
            shutil.rmtree(os.path.join(self.backup_dir, "temp_restore"), ignore_errors=True)
            # فایل ایمنی دیتابیس (نسخهٔ قبل از بازیابی) هم در همهٔ مسیرها پاک
            # می‌شود تا باقی‌ماندهٔ بی‌سروصدا روی دیسک نماند؛ ولی اگر دیتابیس
            # فعال وجود نداشته باشد، هرگز حذف نمی‌شود چون در آن حالت همین
            # فایل، تنها نسخهٔ سالم دیتابیس است. نسخهٔ قبل از عملیات هم در
            # پشتیبان pre_restore (در پوشهٔ پشتیبان‌ها) محفوظ می‌ماند.
            if safety_copy and os.path.exists(safety_copy) and os.path.exists(self.db_path):
                self._remove_quietly(safety_copy)

    def _swap_attachments_dir(self, new_attachments_dir):
        """
        جایگزینی امن پوشهٔ پیوست‌ها با نسخهٔ استخراج‌شده از پشتیبان

        Returns:
            (True, None) در موفقیت؛ (False, پیام خطا) در شکست (پوشهٔ قبلی برگردانده شده)
        """
        safety_dir = self.attachments_dir.rstrip('/\\') + '.restore_safety'
        had_previous = os.path.isdir(self.attachments_dir)
        try:
            shutil.rmtree(safety_dir, ignore_errors=True)
            if had_previous:
                os.replace(self.attachments_dir, safety_dir)
            try:
                shutil.copytree(new_attachments_dir, self.attachments_dir)
            except Exception as copy_error:
                shutil.rmtree(self.attachments_dir, ignore_errors=True)
                if had_previous and os.path.isdir(safety_dir):
                    os.replace(safety_dir, self.attachments_dir)
                raise RuntimeError(f"کپی پیوست‌ها ناموفق بود: {copy_error}") from copy_error
            shutil.rmtree(safety_dir, ignore_errors=True)
            return True, None
        except Exception as e:
            self.logger.error(f"بازیابی پوشهٔ پیوست‌ها ناموفق بود: {e}", exc_info=True)
            return False, str(e)
    
    def _cleanup_pre_restore_files(self):
        """پاک کردن فایل‌های pre_restore قدیمی (فایل و sidecar آن‌ها)"""
        try:
            if not os.path.exists(self.backup_dir):
                return
            for entry in os.listdir(self.backup_dir):
                if entry.startswith("pre_restore"):
                    full = os.path.join(self.backup_dir, entry)
                    try:
                        os.remove(full)
                        self.logger.info(f"فایل قدیمی پیش‌بازیابی حذف شد: {entry}")
                    except OSError as e:
                        self.logger.warning(f"خطا در حذف {entry}: {e}")
        except OSError as e:
            self.logger.warning(f"خطا در پاکسازی pre_restore: {e}")

    STATUS_LABELS = {  # noqa: RUF012 - نگاشت ثابت فقط‌خواندنی
        'ok': '✅ سالم',
        'no_checksum': '⚠️ بدون checksum',
        'mismatch': '❌ checksum نامعتبر',
        'corrupt': '❌ خراب',
    }

    def list_backups(self):
        """لیست فایل‌های پشتیبان موجود (با وضعیت واقعی هر فایل)"""
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.endswith(BACKUP_EXTENSION) and not file.startswith('pre_restore'):
                file_path = os.path.join(self.backup_dir, file)
                size = os.path.getsize(file_path)
                modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # خواندن متادیتا
                try:
                    with zipfile.ZipFile(file_path, 'r') as zipf:
                        if 'metadata.json' in zipf.namelist():
                            metadata = json.loads(zipf.read('metadata.json').decode('utf-8'))
                            name = metadata.get('name', file)
                            created_at = metadata.get('created_at', modified.isoformat())
                            created_by = metadata.get('created_by_name', 'سیستم')
                            encrypted = metadata.get('encrypted', False)
                        else:
                            name = file
                            created_at = modified.isoformat()
                            created_by = 'سیستم'
                            encrypted = False
                except Exception:
                    name = file
                    created_at = modified.isoformat()
                    created_by = 'سیستم'
                    encrypted = False
                
                # وضعیت واقعی فایل (ZIP + checksum کناری) — بازرسی شانزدهم
                status = self.backup_status(file_path)
                expected = self._read_sidecar(file_path)
                checksum_display = (expected[:8] + '...') if expected else '—'

                backups.append({
                    'file': file,
                    'path': file_path,
                    'size': size,
                    'size_display': self._format_size(size),
                    'modified': modified,
                    'created_at': created_at,
                    'name': name,
                    'created_by': created_by,
                    'encrypted': encrypted,
                    'checksum': checksum_display,
                    'status': status,
                    'status_display': self.STATUS_LABELS.get(status, status),
                })
        
        # مرتب‌سازی بر اساس تاریخ (جدیدترین اول)
        backups.sort(key=lambda x: x['modified'], reverse=True)
        return backups
    
    def delete_backup(self, backup_file, user_id=None, user_name=None):
        """
        حذف فایل پشتیبان با ثبت (بازرسی شانزدهم)

        ۱) مسیر canonical می‌شود و باید داخل پوشهٔ پشتیبان، با پسوند
           .partobak و یک فایل معمولی باشد؛ وگرنه هیچ چیزی حذف نمی‌شود.
        ۲) فایل checksum کناری (.sha256) هم حذف می‌شود؛ اگر حذف آن شکست
           بخورد، در نتیجه و لاگ صریحاً گفته می‌شود.

        Returns:
            (bool, str)
        """
        real_path, error = self._resolve_backup_path(backup_file)
        if error:
            self.logger.warning(f"حذف پشتیبان رد شد ({backup_file}): {error}")
            return False, error
        base_name = os.path.basename(real_path)
        try:
            os.remove(real_path)
        except OSError as e:
            self.logger.error(f"حذف فایل پشتیبان {base_name} ناموفق بود: {e}", exc_info=True)
            return False, f"❌ خطا در حذف فایل: {e!s}"

        self._log_backup_operation('delete', base_name, user_id, user_name)

        sidecar = real_path + CHECKSUM_SUFFIX
        if os.path.exists(sidecar):
            try:
                os.remove(sidecar)
            except OSError as e:
                self.logger.warning(
                    f"فایل پشتیبان {base_name} حذف شد ولی فایل checksum کنار آن حذف نشد: {e}")
                return False, (f"⚠️ فایل پشتیبان حذف شد، ولی فایل checksum کنار آن "
                               f"({os.path.basename(sidecar)}) حذف نشد: {e!s}")
        return True, "✅ فایل پشتیبان (و فایل checksum آن) با موفقیت حذف شد."
    
    def _count_attachments(self):
        """تعداد فایل‌های پیوست"""
        count = 0
        if os.path.exists(self.attachments_dir):
            for root, dirs, files in os.walk(self.attachments_dir):
                count += len(files)
        return count
    
    def _calculate_checksum(self, file_path, algorithm='sha256'):
        """
        محاسبه Checksum فایل

        (بازرسی شانزدهم) پیش‌فرض SHA-256 است — هم‌نام با پسوند فایل کناری.
        نسخهٔ قبلی MD5 را در فایلی با پسوند .sha256 می‌نوشت؛ برای اینکه
        پشتیبان‌های قدیمی همچنان راستی‌آزمایی شوند، هنگام مقایسه اگر مقدار
        ثبت‌شده ۳۲ رقمی باشد، با MD5 مقایسه می‌شود (`_checksum_matches`).
        """
        hasher = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _checksum_matches(self, file_path, expected):
        """مقایسهٔ checksum فایل با مقدار ثبت‌شده (SHA-256 یا MD5 قدیمی)"""
        expected = (expected or '').strip().lower()
        if len(expected) == 32:
            return self._calculate_checksum(file_path, 'md5') == expected
        return self._calculate_checksum(file_path, 'sha256') == expected

    def _read_sidecar(self, backup_file):
        """مقدار checksum ثبت‌شده کنار فایل، یا None اگر نبود/خوانده نشد"""
        sidecar = backup_file + CHECKSUM_SUFFIX
        if not os.path.exists(sidecar):
            return None
        try:
            with open(sidecar, encoding='utf-8') as f:
                return f.read().strip() or None
        except OSError as e:
            self.logger.warning(f"خطا در خواندن checksum: {e}")
            return None

    def backup_status(self, backup_file):
        """
        وضعیت واقعی یک فایل پشتیبان (بازرسی شانزدهم)

        قبلاً صفحهٔ پشتیبان‌گیری برای همهٔ فایل‌ها «✅ سالم» نشان می‌داد بدون
        هیچ بررسی. حالا:
          ok           → ZIP سالم و checksum با فایل کناری برابر
          no_checksum  → ZIP سالم ولی فایل checksum کنارش نیست
          mismatch     → checksum با فایل کناری برابر نیست (خراب/دستکاری)
          corrupt      → ZIP باز نمی‌شود یا عضو خراب دارد
        """
        try:
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                if zipf.testzip() is not None:
                    return 'corrupt'
        except (zipfile.BadZipFile, OSError):
            return 'corrupt'
        expected = self._read_sidecar(backup_file)
        if expected is None:
            return 'no_checksum'
        return 'ok' if self._checksum_matches(backup_file, expected) else 'mismatch'
    
    def _format_size(self, size):
        """فرمت‌سازی حجم فایل"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def _log_backup_operation(self, operation, backup_name, user_id, user_name):
        """ثبت عملیات Backup در لاگ"""
        log_file = os.path.join(self.backup_dir, "backup_log.txt")
        timestamp = utc_now_iso()
        
        log_entry = f"[{timestamp}] {operation} | user: {user_id} ({user_name}) | backup: {backup_name}\n"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as _exc:
            self.logger.debug(
                f"خطای غیرمنتظره در {self.__class__.__name__}: {_exc}"
            )

    def schedule_auto_backup(self, interval_hours=24, user_id=None, user_name=None):
        """
        تنظیم پشتیبان‌گیری خودکار (قابل توقف — بازرسی شانزدهم)

        Args:
            interval_hours: فاصله زمانی بین پشتیبان‌گیری‌ها (ساعت)
            user_id: شناسه کاربر (None = سیستم)
            user_name: نام کاربر

        Returns:
            AutoBackupHandle: با `stop()` واقعاً متوقف می‌شود؛ `is_running()`
        """
        handle = AutoBackupHandle(interval_hours)

        def auto_backup_worker():
            while handle.wait_interval():
                try:
                    timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
                    name = f"auto_backup_{timestamp}"
                    result = self.create_backup(name, user_id, user_name)
                    handle.last_result = result
                    if result['success']:
                        # حذف پشتیبان‌های خودکار قدیمی (نگهداری ۱۰ تا)
                        self._cleanup_old_backups(keep_count=10)
                        self._log_backup_operation('auto_backup', name, user_id, user_name)
                    else:
                        self.logger.error(f"پشتیبان‌گیری خودکار ناموفق بود: {result.get('message')}")
                except Exception as e:
                    self.logger.error(f"خطا در پشتیبان‌گیری خودکار: {e}", exc_info=True)
            self.logger.info("پشتیبان‌گیری خودکار متوقف شد.")

        handle.thread = threading.Thread(
            target=auto_backup_worker, daemon=True, name="parto-auto-backup")
        handle.thread.start()
        self.logger.info(f"پشتیبان‌گیری خودکار هر {interval_hours} ساعت فعال شد.")
        return handle

    def _cleanup_old_backups(self, keep_count=10):
        """حذف پشتیبان‌های خودکار قدیمی (فایل و checksum کناری)، بقیه دست‌نخورده"""
        try:
            backups = self.list_backups()
            auto_backups = [b for b in backups if b['name'].startswith('auto_backup_')]

            if len(auto_backups) > keep_count:
                # مرتب‌سازی بر اساس تاریخ (قدیمی‌ترین اول)
                auto_backups.sort(key=lambda x: x['created_at'])
                to_delete = auto_backups[:-keep_count]

                for backup in to_delete:
                    ok, message = self.delete_backup(backup['path'], None, 'سیستم')
                    if ok:
                        self.logger.info(f"پشتیبان خودکار قدیمی حذف شد: {backup['name']}")
                    else:
                        self.logger.warning(
                            f"حذف پشتیبان خودکار قدیمی {backup['name']} ناموفق بود: {message}")
        except Exception as e:
            self.logger.error(f"خطا در پاکسازی پشتیبان‌های قدیمی: {e}", exc_info=True)
