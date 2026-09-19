"""
ابزارهای پشتیبان‌گیری و بازیابی اطلاعات - نسخه ساده (بدون رمزنگاری)
"""

import hashlib
import json
import os
import shutil
import sqlite3
import zipfile
from datetime import datetime

from utils.logger import get_logger
from utils.time_utils import utc_now, utc_now_iso

logger = get_logger(__name__)


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
        
        # ایجاد پوشه Backup اگر وجود ندارد
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
    
    def create_backup(self, name=None, user_id=None, user_name=None):
        """
        ایجاد نسخه پشتیبان کامل
        
        Returns:
            dict: اطلاعات Backup ایجاد شده
        """
        try:
            # ایجاد نام فایل
            if not name:
                timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
                name = f"backup_{timestamp}"
            
            backup_file = os.path.join(self.backup_dir, f"{name}.partobak")
            
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
            tmp_db_snapshot = os.path.join(self.backup_dir, f"{name}.db.tmp")
            try:
                if os.path.exists(self.db_path):
                    src = sqlite3.connect(self.db_path)
                    try:
                        dst = sqlite3.connect(tmp_db_snapshot)
                        try:
                            src.backup(dst)      # کپی سازگار و اتمیک
                        finally:
                            dst.close()
                    finally:
                        src.close()
            except sqlite3.Error as e:
                # اگر API پشتیبان در دسترس نبود، به کپی فایل برمی‌گردیم
                self.logger.warning(f"پشتیبان‌گیری آنلاین ممکن نشد، کپی فایل: {e}")
                if os.path.exists(self.db_path):
                    shutil.copy2(self.db_path, tmp_db_snapshot)

            # ایجاد فایل ZIP
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. دیتابیس (از نسخه سازگار گرفته‌شده)
                if os.path.exists(tmp_db_snapshot):
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
                    'version': '2.0.0',
                    'encrypted': False,
                }
                zipf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
            
            # پاک کردن نسخه موقت دیتابیس
            if os.path.exists(tmp_db_snapshot):
                try:
                    os.remove(tmp_db_snapshot)
                except OSError as e:
                    self.logger.warning(f"خطا در حذف فایل موقت پشتیبان: {e}")

            # محاسبه checksum
            checksum = self._calculate_checksum(backup_file)

            # ===== اصلاح =====
            # checksum محاسبه می‌شد ولی هیچ‌جا ذخیره نمی‌شد، پس موقع
            # بازیابی چیزی برای مقایسه وجود نداشت. حالا داخل
            # metadata کنار فایل نوشته می‌شود تا در restore قابل
            # راستی‌آزمایی باشد.
            sidecar = backup_file + '.sha256'
            try:
                with open(sidecar, 'w', encoding='utf-8') as f:
                    f.write(checksum)
            except OSError as e:
                self.logger.warning(f"خطا در ذخیره checksum: {e}")
            
            # ثبت در لاگ
            self._log_backup_operation('create', name, user_id, user_name)
            
            return {
                'success': True,
                'file': backup_file,
                'name': name,
                'size': os.path.getsize(backup_file),
                'size_display': self._format_size(os.path.getsize(backup_file)),
                'checksum': checksum,
                'created_at': metadata['created_at'],
                'created_by': user_id,
                'message': f"✅ Backup با موفقیت در {backup_file} ایجاد شد."
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"❌ خطا در ایجاد Backup: {e!s}"
            }
    
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

        نسخهٔ قبلی restore_backup فقط این را انجام می‌داد:

            shutil.copy2(db_backup, self.db_path)

        یعنی فایل .db با نسخهٔ پشتیبان جایگزین می‌شد، ولی -wal و -shm
        دست‌نخورده می‌ماندند. نتیجه: WAL قدیمی (مربوط به وضعیتِ قبل از
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
        """
        # ۱) checkpoint و بستن اتصال باز
        try:
            from database.connection import DatabaseConnection
            inst = getattr(DatabaseConnection, '_instance', None)
            conn = getattr(inst, '_connection', None) if inst is not None else None
            if conn is not None:
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except sqlite3.Error as e:
                    # checkpoint نشدن مانع بازیابی نیست؛ WAL هنگام بستن
                    # اتصال کنار گذاشته می‌شود.
                    logger.debug(f"wal_checkpoint انجام نشد: {e}")
                try:
                    inst.close()      # _connection = None و _initialized = False
                except Exception as e:
                    logger.debug(f"بستن اتصال پیش از بازیابی ناموفق بود: {e}")
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

    def _verify_restored_database(self):
        """
        راستی‌آزمایی اینکه دیتابیس بازیابی‌شده واقعاً سالم و خواندنی است

        بدون این بررسی، متد حتی وقتی کپی هیچ اثری نکرده بود هم
        `success: True` برمی‌گرداند.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                result = conn.execute("PRAGMA integrity_check").fetchone()
                tables = conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
                ).fetchone()[0]
            finally:
                conn.close()
        except sqlite3.Error as e:
            return False, f"دیتابیس بازیابی‌شده باز نمی‌شود: {e}"

        if not result or result[0] != 'ok':
            return False, f"دیتابیس بازیابی‌شده سالم نیست: {result}"
        if tables < 10:
            return False, f"دیتابیس بازیابی‌شده فقط {tables} جدول دارد"
        return True, f"{tables} جدول، integrity_check = ok"

    def restore_backup(self, backup_file, user_id=None, user_name=None):
        """
        بازیابی از فایل پشتیبان با تأیید و ثبت
        
        Returns:
            dict: نتیجه عملیات
        """
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

            sidecar = backup_file + '.sha256'
            if os.path.exists(sidecar):
                try:
                    with open(sidecar, encoding='utf-8') as f:
                        expected = f.read().strip()
                except OSError as e:
                    expected = None
                    self.logger.warning(f"خطا در خواندن checksum: {e}")

                if expected and expected != checksum:
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
            if not pre_restore['success']:
                return {
                    'success': False,
                    'message': f"❌ امکان ایجاد Backup از وضعیت فعلی وجود ندارد: {pre_restore.get('message')}"
                }
            
            # استخراج فایل
            extract_dir = os.path.join(self.backup_dir, "temp_restore")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(extract_dir)
            
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
            journal_removed = self._quiesce_database()

            # ۲) جایگزینی فایل دیتابیس
            shutil.copy2(db_backup, self.db_path)

            # ۳) ژورنال‌های احتمالیِ باقی‌مانده دوباره پاک شوند
            journal_removed += self._remove_journal_files()

            # ۴) راستی‌آزمایی اینکه بازیابی واقعاً اثر کرده
            healthy, detail = self._verify_restored_database()
            if not healthy:
                return {
                    'success': False,
                    'message': f"❌ بازیابی کامل نشد: {detail}\n\n"
                               f"پشتیبانِ وضعیت قبلی در این فایل نگه داشته شد: "
                               f"{pre_restore.get('file')}"
                }
            
            # بازیابی فایل‌های پیوست
            attachments_backup = os.path.join(extract_dir, "attachments")
            if os.path.exists(attachments_backup):
                if os.path.exists(self.attachments_dir):
                    shutil.rmtree(self.attachments_dir)
                shutil.copytree(attachments_backup, self.attachments_dir)
            
            # پاک کردن فایل‌های موقت
            shutil.rmtree(extract_dir)
            
            # ثبت در لاگ
            self._log_backup_operation('restore', os.path.basename(backup_file), user_id, user_name)
            
            return {
                'success': True,
                'message': (
                    f"✅ بازیابی با موفقیت از {os.path.basename(backup_file)} "
                    f"انجام شد.\n({detail})\n\n"
                    "برای اطمینان، برنامه را یک بار ببندید و دوباره باز کنید "
                    "تا همهٔ صفحه‌ها دادهٔ بازیابی‌شده را نشان دهند."
                ),
                'pre_restore_file': pre_restore.get('file'),
                'checksum': checksum,
                'journal_removed': journal_removed,
                'detail': detail
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"❌ خطا در بازیابی: {e!s}"
            }
    
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

    def list_backups(self):
        """لیست فایل‌های پشتیبان موجود"""
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.endswith('.partobak') and not file.startswith('pre_restore'):
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
                
                # محاسبه checksum
                checksum = self._calculate_checksum(file_path)
                
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
                    'checksum': checksum[:8] + '...'
                })
        
        # مرتب‌سازی بر اساس تاریخ (جدیدترین اول)
        backups.sort(key=lambda x: x['modified'], reverse=True)
        return backups
    
    def delete_backup(self, backup_file, user_id=None, user_name=None):
        """حذف فایل پشتیبان با ثبت"""
        try:
            if os.path.exists(backup_file):
                os.remove(backup_file)
                self._log_backup_operation('delete', os.path.basename(backup_file), user_id, user_name)
                return True, "✅ فایل پشتیبان با موفقیت حذف شد."
            return False, "❌ فایل پشتیبان وجود ندارد."
        except Exception as e:
            return False, f"❌ خطا در حذف فایل: {e!s}"
    
    def _count_attachments(self):
        """تعداد فایل‌های پیوست"""
        count = 0
        if os.path.exists(self.attachments_dir):
            for root, dirs, files in os.walk(self.attachments_dir):
                count += len(files)
        return count
    
    def _calculate_checksum(self, file_path):
        """محاسبه Checksum فایل"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
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
        تنظیم پشتیبان‌گیری خودکار
        
        Args:
            interval_hours: فاصله زمانی بین پشتیبان‌گیری‌ها (ساعت)
            user_id: شناسه کاربر
            user_name: نام کاربر
        """
        import threading
        import time
        
        def auto_backup_worker():
            while True:
                time.sleep(interval_hours * 3600)
                try:
                    # ایجاد پشتیبان
                    timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
                    name = f"auto_backup_{timestamp}"
                    result = self.create_backup(name, user_id, user_name)
                    
                    if result['success']:
                        # حذف پشتیبان‌های قدیمی (نگهداری ۱۰ تا)
                        self._cleanup_old_backups(keep_count=10)
                        
                        # ثبت در لاگ
                        self._log_backup_operation(
                            'auto_backup', 
                            name, 
                            user_id, 
                            user_name
                        )
                except Exception as e:
                    logger.error(f"⚠️ خطا در پشتیبان‌گیری خودکار: {e}")
        
        # شروع ترد
        thread = threading.Thread(target=auto_backup_worker, daemon=True)
        thread.start()
        logger.debug(f"✅ پشتیبان‌گیری خودکار هر {interval_hours} ساعت فعال شد.")
        return thread
    
    def _cleanup_old_backups(self, keep_count=10):
        """حذف پشتیبان‌های قدیمی (به جز فایل‌های auto_backup)"""
        try:
            backups = self.list_backups()
            # فیلتر کردن پشتیبان‌های خودکار
            auto_backups = [b for b in backups if b['name'].startswith('auto_backup_')]
            
            if len(auto_backups) > keep_count:
                # مرتب‌سازی بر اساس تاریخ (قدیمی‌ترین اول)
                auto_backups.sort(key=lambda x: x['created_at'])
                to_delete = auto_backups[:-keep_count]
                
                for backup in to_delete:
                    try:
                        os.remove(backup['path'])
                        logger.debug(f"🗑️ پشتیبان قدیمی حذف شد: {backup['name']}")
                    except Exception as _exc:
                        self.logger.debug(
                            f"خطای غیرمنتظره در {self.__class__.__name__}: {_exc}"
                        )
        except Exception as e:
            logger.error(f"⚠️ خطا در پاکسازی پشتیبان‌های قدیمی: {e}")