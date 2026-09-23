"""
تست‌های حساب‌داری پیوست‌ها و وضعیت checksum پشتیبان (دور هفدهم — مرحلهٔ ۱)

مبنا: بند ۱۰ مأموریت MASTER FIX
  • BUG-BACKUP-03: نبود فایل کناری `.sha256` باید وضعیت «راستی‌آزمایی‌نشده»
    بدهد، نه موفقیت خاموش.
  • BUG-BACKUP-04/05: متادیتای پشتیبان باید «تعداد موردانتظار طبق دیتابیس»،
    «فایل‌های بسته‌بندی‌شده» و «فایل‌های گم‌شده» را جدا گزارش کند.

این تست‌ها روی دیتابیس‌های کاملاً مستقل (ساختهٔ خودِ تست) اجرا می‌شوند و
نه به دیتابیس واقعی برنامه دست می‌زنند و نه به اتصال سراسری برنامه، پس
ترتیب اجرای تست‌ها روی نتیجه اثر ندارد.
"""

import hashlib
import os
import sqlite3
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.backup import BackupManager

_TMP_DIR = tempfile.mkdtemp(prefix='partow_backup_test_')

_ATTACHMENTS_TABLE = """
    CREATE TABLE attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER,
        file_type TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER,
        is_deleted INTEGER DEFAULT 0,
        deleted_at TEXT,
        deleted_by INTEGER
    )
"""


class TestAttachmentLedger(unittest.TestCase):
    """حساب‌داری واقعی پیوست‌ها (BUG-BACKUP-04/05)"""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='env_', dir=_TMP_DIR)
        self.att_dir = os.path.join(self.root, 'attachments')
        self.backup_dir = os.path.join(self.root, 'backups')
        self.db_path = os.path.join(self.root, 'partow.db')
        os.makedirs(self.att_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        self.manager = BackupManager(self.db_path, self.att_dir, self.backup_dir)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(_ATTACHMENTS_TABLE)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def _write_file(self, name, content='پیوست'):
        path = os.path.join(self.att_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content)
        return path

    def _add_attachment(self, file_path, is_deleted=0):
        self.conn.execute(
            "INSERT INTO attachments (entity_type, entity_id, file_name, file_path, "
            "file_size, file_type, is_deleted) VALUES ('student', 1, ?, ?, 10, "
            "'document', ?)",
            (os.path.basename(file_path), file_path, is_deleted))
        self.conn.commit()

    def test_all_files_present_is_complete(self):
        """پشتیبان کامل: موردانتظار = بسته‌بندی‌شده، گم‌شده = ۰، complete=True"""
        self._add_attachment(self._write_file('present.txt'))

        ledger = self.manager.attachment_ledger(db_file=self.db_path)

        self.assertEqual(ledger['expected_in_db'], 1)
        self.assertEqual(ledger['packaged_files'], 1)
        self.assertEqual(ledger['missing_count'], 0)
        self.assertEqual(ledger['missing_files'], [])
        self.assertTrue(ledger['complete'])
        self.assertIsNone(ledger['error'])

    def test_missing_physical_file_is_reported_not_hidden(self):
        """ردیف DB بدون فایل فیزیکی → گزارش صریح «گم‌شده» و complete=False"""
        self._add_attachment(self._write_file('present.txt'))
        self._add_attachment(os.path.join(self.att_dir, 'ghost.txt'))

        ledger = self.manager.attachment_ledger(db_file=self.db_path)

        self.assertEqual(ledger['expected_in_db'], 2)
        self.assertEqual(ledger['packaged_files'], 1)
        self.assertEqual(ledger['missing_count'], 1)
        self.assertEqual(ledger['missing_files'], ['ghost.txt'])
        self.assertFalse(ledger['complete'])

    def test_deleted_rows_are_not_counted_as_expected(self):
        """حذف‌شده‌ها در «موردانتظار» شمرده نمی‌شوند (ولی گزارش می‌شوند)"""
        self._add_attachment(self._write_file('present.txt'))
        self._add_attachment(os.path.join(self.att_dir, 'deleted.txt'), is_deleted=1)

        ledger = self.manager.attachment_ledger(db_file=self.db_path)

        self.assertEqual(ledger['expected_in_db'], 1)
        self.assertEqual(ledger['deleted_rows'], 1)
        self.assertTrue(ledger['complete'])

    def test_unreadable_database_is_reported(self):
        """خطای خواندن دیتابیس نباید بی‌صدا رد شود"""
        self._add_attachment(self._write_file('present.txt'))

        ledger = self.manager.attachment_ledger(
            db_file=os.path.join(self.root, 'no_such.db'))

        self.assertIsNotNone(ledger['error'])
        self.assertFalse(ledger['complete'])
        self.assertEqual(ledger['missing_count'], 0)

    def test_database_without_attachments_table_is_not_an_error(self):
        """دیتابیس قدیمی بدون جدول attachments → صفر و توضیح، نه استثنا"""
        legacy_db = os.path.join(self.root, 'legacy.db')
        sqlite3.connect(legacy_db).close()

        ledger = self.manager.attachment_ledger(db_file=legacy_db)

        self.assertEqual(ledger['expected_in_db'], 0)
        self.assertTrue(ledger['complete'])
        self.assertIn('attachments', ledger.get('note', ''))

    def test_relative_paths_resolve_against_base_dir(self):
        """مسیر نسبی در DB باید نسبت به ریشهٔ برنامه حل شود"""
        self._write_file('present.txt')
        self._add_attachment('attachments/present.txt')

        ledger = self.manager.attachment_ledger(
            db_file=self.db_path, base_dir=self.root)

        self.assertEqual(ledger['expected_in_db'], 1)
        self.assertEqual(ledger['missing_count'], 0)
        self.assertTrue(ledger['complete'])


class TestChecksumReporting(unittest.TestCase):
    """وضعیت صریح checksum (BUG-BACKUP-03)"""

    def test_unverified_note_only_for_legacy(self):
        note_legacy = BackupManager._unverified_checksum_note('legacy_no_sidecar')
        self.assertIn('⚠️', note_legacy)
        self.assertIn('راستی‌آزمایی نشد', note_legacy)
        self.assertEqual(BackupManager._unverified_checksum_note('verified'), '')
        self.assertEqual(BackupManager._unverified_checksum_note('failed'), '')

    def test_backup_status_mapping(self):
        """نگاشت وضعیت فایل: ok / no_checksum / mismatch / corrupt"""
        root = tempfile.mkdtemp(prefix='status_', dir=_TMP_DIR)
        manager = BackupManager(
            os.path.join(root, 'partow.db'),
            os.path.join(root, 'attachments'),
            os.path.join(root, 'backups'))
        os.makedirs(manager.backup_dir, exist_ok=True)

        backup_file = os.path.join(manager.backup_dir, 'probe.partobak')
        with zipfile.ZipFile(backup_file, 'w') as zipf:
            zipf.writestr('metadata.json', '{}')
        with open(backup_file, 'rb') as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()

        self.assertEqual(manager.backup_status(backup_file), 'no_checksum')

        with open(backup_file + '.sha256', 'w', encoding='utf-8') as fh:
            fh.write(digest)
        self.assertEqual(manager.backup_status(backup_file), 'ok')

        with open(backup_file, 'ab') as fh:
            fh.write(b'tampered')
        self.assertEqual(manager.backup_status(backup_file), 'mismatch')

        corrupt = os.path.join(manager.backup_dir, 'corrupt.partobak')
        with open(corrupt, 'wb') as fh:
            fh.write(b'not a zip')
        self.assertEqual(manager.backup_status(corrupt), 'corrupt')


if __name__ == '__main__':
    unittest.main()
