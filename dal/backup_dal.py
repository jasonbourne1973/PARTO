"""
لایه دسترسی به داده نسخه‌های پشتیبان

===== چرا این فایل لازم بود؟ =====
قبلاً اطلاعات پشتیبان‌ها فقط داخل فایل ZIP (metadata.json) نگه داشته می‌شد.
مشکلات آن روش:
    ۱. checksum محاسبه می‌شد ولی هرگز جایی ذخیره نمی‌شد، پس در زمان
       بازیابی چیزی برای مقایسه نبود. ادعای «بررسی یکپارچگی» عملی نبود.
    ۲. برای لیست کردن پشتیبان‌ها باید همه فایل‌های ZIP باز و خوانده
       می‌شدند (BackupManager.list_backups دقیقاً این کار را می‌کرد) -
       یعنی به ازای هر فایل یک unzip. با چند صد پشتیبان، کند می‌شود.
    ۳. پشتیبان‌های pre_restore بی‌نهایت جمع می‌شدند و هیچ ردی نداشتند.

حالا هر پشتیبان یک رکورد در جدول backups دارد که checksum و نوع
(دستی/خودکار/پیش از بازیابی) در آن ثبت می‌شود.

جدول backups در migration_v7 ساخته می‌شود.
"""

import os
import sqlite3
from datetime import datetime

from database.connection import DatabaseConnection
from models.base import BaseModel


class BackupRecord(BaseModel):
    """مدل رکورد پشتیبان"""

    KIND_MANUAL = 'manual'          # کاربر دستی گرفته
    KIND_AUTO = 'auto'              # زمان‌بند خودکار گرفته
    KIND_PRE_RESTORE = 'pre_restore'  # قبل از بازیابی گرفته شده

    KINDS = [KIND_MANUAL, KIND_AUTO, KIND_PRE_RESTORE]

    def __init__(self):
        super().__init__()
        self.name = None
        self.file_path = None
        self.file_size = None
        self.checksum = None
        self.kind = self.KIND_MANUAL
        self.db_version = None
        self.attachments_count = None
        self.records_count = None       # تعداد رکوردهای اصلی دیتابیس
        self.notes = None
        self.created_by = None          # staff.id
        self.is_verified = 0            # checksum تأیید شده؟
        self.verified_at = None
        self.restored_at = None         # اگر از این پشتیبان بازیابی شده

        # فیلد کمکی
        self.created_by_name = None

    @property
    def size_display(self):
        """حجم به صورت خوانا"""
        size = self.file_size or 0
        for unit in ('بایت', 'کیلوبایت', 'مگابایت', 'گیگابایت'):
            if size < 1024:
                return f"{size:.1f} {unit}" if unit != 'بایت' else f"{size} بایت"
            size /= 1024
        return f"{size:.1f} ترابایت"

    @property
    def kind_display(self):
        return {
            self.KIND_MANUAL: "🖐️ دستی",
            self.KIND_AUTO: "🤖 خودکار",
            self.KIND_PRE_RESTORE: "🛡️ پیش از بازیابی",
        }.get(self.kind, self.kind or "نامشخص")

    @property
    def exists_on_disk(self):
        """آیا فایل فیزیکی هنوز وجود دارد؟"""
        return bool(self.file_path and os.path.exists(self.file_path))

    @property
    def short_checksum(self):
        """چک‌سام کوتاه برای نمایش"""
        if not self.checksum:
            return "—"
        return f"{self.checksum[:8]}…{self.checksum[-4:]}"

    def validate(self):
        errors = []
        if not self.name:
            errors.append("نام پشتیبان نمی‌تواند خالی باشد")
        if not self.file_path:
            errors.append("مسیر فایل پشتیبان نمی‌تواند خالی باشد")
        if not self.checksum:
            errors.append("چک‌سام باید محاسبه شود")
        if self.kind not in self.KINDS:
            errors.append(
                f"نوع نامعتبر. انواع مجاز: {', '.join(self.KINDS)}"
            )
        return errors


class BackupDAL:
    """عملیات CRUD برای رکوردهای پشتیبان"""

    def __init__(self):
        self.db = DatabaseConnection()

    # ============================================================
    # ایجاد
    # ============================================================

    def create(self, record):
        """ثبت یک پشتیبان جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        errors = record.validate()
        if errors:
            raise ValueError("\n".join(errors))

        # حجم واقعی فایل را از دیسک بگیر (معتبرتر از چیزی که caller می‌دهد)
        if record.file_path and os.path.exists(record.file_path):
            record.file_size = os.path.getsize(record.file_path)

        try:
            cursor.execute("""
                INSERT INTO backups (
                    name, file_path, file_size, checksum, kind,
                    db_version, attachments_count, records_count,
                    notes, created_by, is_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.name,
                record.file_path,
                record.file_size,
                record.checksum,
                record.kind,
                record.db_version,
                record.attachments_count,
                record.records_count,
                record.notes,
                record.created_by,
                1 if record.is_verified else 0
            ))

            conn.commit()
            record.id = cursor.lastrowid
            return record

        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"خطا در ثبت پشتیبان: {e}")

    # ============================================================
    # خواندن
    # ============================================================

    def get_by_id(self, backup_id):
        """دریافت پشتیبان با شناسه"""
        cursor = self.db.execute_query("""
            SELECT b.*, s.full_name AS created_by_name
            FROM backups b
            LEFT JOIN staff s ON b.created_by = s.id
            WHERE b.id = ? AND b.is_deleted = 0
        """, (backup_id,))
        row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def get_by_checksum(self, checksum):
        """جست‌وجو با چک‌سام (برای پیدا کردن پشتیبان تکراری)"""
        cursor = self.db.execute_query("""
            SELECT b.*, s.full_name AS created_by_name
            FROM backups b
            LEFT JOIN staff s ON b.created_by = s.id
            WHERE b.checksum = ? AND b.is_deleted = 0
            LIMIT 1
        """, (checksum,))
        row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def get_all(self, kind=None, limit=None):
        """
        دریافت همه پشتیبان‌ها (جدیدترین اول)

        این جایگزین BackupManager.list_backups است که مجبور بود
        همه فایل‌های ZIP را باز کند.
        """
        query = """
            SELECT b.*, s.full_name AS created_by_name
            FROM backups b
            LEFT JOIN staff s ON b.created_by = s.id
            WHERE b.is_deleted = 0
        """
        params = []

        if kind:
            query += " AND b.kind = ?"
            params.append(kind)

        query += " ORDER BY b.created_at DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.db.execute_query(query, tuple(params) if params else None)
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_latest(self, kind=None):
        """دریافت آخرین پشتیبان (برای بازیابی سریع)"""
        records = self.get_all(kind=kind, limit=1)
        return records[0] if records else None

    def get_deleted(self, limit=None):
        """پشتیبان‌های حذف‌شده منطقی"""
        query = """
            SELECT b.*, s.full_name AS created_by_name
            FROM backups b
            LEFT JOIN staff s ON b.created_by = s.id
            WHERE b.is_deleted = 1
            ORDER BY b.deleted_at DESC
        """
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.db.execute_query(query, tuple(params) if params else None)
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def find_missing_files(self):
        """
        پیدا کردن رکوردهایی که فایل فیزیکی‌شان گم شده

        برای «بررسی سلامت» در صفحه پشتیبان‌گیری.
        """
        missing = []
        for record in self.get_all():
            if not record.exists_on_disk:
                missing.append(record)
        return missing

    # ============================================================
    # تأیید یکپارچگی
    # ============================================================

    def mark_verified(self, backup_id, checksum_matches):
        """
        ثبت نتیجه بررسی چک‌سام

        این همان حلقه گمشده‌ای است که باعث می‌شد checksum محاسبه شود
        ولی هرگز بررسی نشود.
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE backups SET
                is_verified = ?,
                verified_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            1 if checksum_matches else 0,
            datetime.now().isoformat(),
            backup_id
        ))

        conn.commit()
        return cursor.rowcount > 0

    def mark_restored(self, backup_id):
        """ثبت اینکه از این پشتیبان بازیابی شده است"""
        conn = self.db.get_connection()
        conn.execute("""
            UPDATE backups SET
                restored_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (datetime.now().isoformat(), backup_id))
        conn.commit()

    # ============================================================
    # به‌روزرسانی و حذف
    # ============================================================

    def update(self, record):
        """به‌روزرسانی اطلاعات پشتیبان"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE backups SET
                    name = ?, notes = ?, kind = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 0
            """, (
                record.name,
                record.notes,
                record.kind,
                record.id
            ))
            conn.commit()
            return record
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"خطا در به‌روزرسانی پشتیبان: {e}")

    def delete(self, backup_id, user_id=None, delete_file=False):
        """
        حذف منطقی پشتیبان

        Args:
            delete_file: اگر True، فایل فیزیکی هم پاک می‌شود.
                         برخلاف AttachmentDAL که فایل را بی‌قید و شرط
                         پاک می‌کرد، اینجا پیش‌فرض False است تا رکورد
                         قابل بازیابی بماند.
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        record = self.get_by_id(backup_id)
        if not record:
            return False

        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE backups SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (now, user_id, backup_id))

        conn.commit()

        if delete_file and record.file_path and os.path.exists(record.file_path):
            try:
                os.remove(record.file_path)
            except OSError:
                # پاک نشدن فایل نباید عملیات را شکست دهد
                pass

        return True

    def restore(self, backup_id, user_id=None):
        """بازیابی رکورد حذف‌شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE backups SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 1
        """, (backup_id,))

        conn.commit()
        return cursor.rowcount > 0

    def permanent_delete(self, backup_id, delete_file=True):
        """حذف فیزیکی رکورد و فایل"""
        record = self.get_by_id(backup_id)
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
        conn.commit()

        if (delete_file and record and record.file_path
                and os.path.exists(record.file_path)):
            try:
                os.remove(record.file_path)
            except OSError:
                pass

        return cursor.rowcount > 0

    # ============================================================
    # پاکسازی
    # ============================================================

    def cleanup_old(self, keep_count=10, kinds=None, user_id=None):
        """
        پاکسازی پشتیبان‌های قدیمی

        این همان چیزی است که برای پشتیبان‌های pre_restore لازم بود:
        قبلاً بی‌نهایت جمع می‌شدند و هیچ‌وقت پاک نمی‌شدند.

        Args:
            keep_count: از هر نوع، چند تای آخر نگه داشته شود
            kinds: انواعی که پاکسازی شوند (پیش‌فرض: همه)
            user_id: staff.id کاربری که پاکسازی را انجام داده

        Returns:
            int: تعداد پاک‌شده‌ها
        """
        if kinds is None:
            kinds = self.__class__.__mro__ and BackupRecord.KINDS

        removed = 0
        for kind in kinds:
            records = self.get_all(kind=kind)
            # get_all جدیدترین اول برمی‌گرداند، پس از keep_count به بعد قدیمی‌اند
            for record in records[keep_count:]:
                if self.delete(record.id, user_id=user_id, delete_file=True):
                    removed += 1

        return removed

    # ============================================================
    # آمار
    # ============================================================

    def get_stats(self):
        """آمار کلی پشتیبان‌ها"""
        cursor = self.db.execute_query("""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(file_size), 0) AS total_size,
                SUM(CASE WHEN kind = 'manual' THEN 1 ELSE 0 END) AS manual,
                SUM(CASE WHEN kind = 'auto' THEN 1 ELSE 0 END) AS auto,
                SUM(CASE WHEN kind = 'pre_restore' THEN 1 ELSE 0 END) AS pre_restore,
                SUM(CASE WHEN is_verified = 1 THEN 1 ELSE 0 END) AS verified,
                MAX(created_at) AS last_backup_at
            FROM backups
            WHERE is_deleted = 0
        """)
        row = cursor.fetchone()
        if not row:
            return {
                'total': 0, 'total_size': 0, 'manual': 0, 'auto': 0,
                'pre_restore': 0, 'verified': 0, 'last_backup_at': None
            }

        return {
            'total': row['total'] or 0,
            'total_size': row['total_size'] or 0,
            'manual': row['manual'] or 0,
            'auto': row['auto'] or 0,
            'pre_restore': row['pre_restore'] or 0,
            'verified': row['verified'] or 0,
            'last_backup_at': row['last_backup_at'],
        }

    # ============================================================
    # داخلی
    # ============================================================

    def _row_to_record(self, row):
        if row is None:
            return None

        record = BackupRecord()
        record.id = row['id']
        record.name = row['name']
        record.file_path = row['file_path']
        record.file_size = row['file_size']
        record.checksum = row['checksum']
        record.kind = row['kind']
        record.db_version = row['db_version']
        record.attachments_count = row['attachments_count']
        record.records_count = row['records_count']
        record.notes = row['notes']
        record.created_by = row['created_by']
        record.is_verified = row['is_verified']
        record.verified_at = row['verified_at']
        record.restored_at = row['restored_at']
        record.created_at = row['created_at']
        record.updated_at = row['updated_at']

        record.is_deleted = row['is_deleted']
        record.deleted_at = row['deleted_at']
        record.deleted_by = row['deleted_by']

        keys = row.keys() if hasattr(row, 'keys') else []
        record.created_by_name = (
            row['created_by_name'] if 'created_by_name' in keys else None
        )

        return record
