"""
آزمون‌های پیوست‌ها — دور هجدهم، مرحلهٔ ۲ (BUG-ATT-04/05/06)

پوشش مأموریت (بند ۱۱):
  • BUG-ATT-04 — مسیر بازیابی پیوست حذف‌شده: سرویس + قرارداد واقعی
    («فقط رکورد حذف‌شده»، «بررسی نتیجهٔ واقعی»، «خطای صریح»). مسیر UI
    (چک‌باکس «نمایش حذف‌شده‌ها» + دکمهٔ ↩️) با اجرای آفلاین دیالوگ در
    verify_fixes18.py §A آزموده می‌شود.
  • BUG-ATT-05 — بازیابی باید «وجود فایل فیزیکی» را پیش از هر تغییر DB
    راستی‌آزمایی کند؛ فایل گم‌شده → خطای صریح و رکورد در همان حالت حذف.
  • BUG-ATT-06 — سقف ۲۰ پیوست در هر موجودیت: ۲۰قبول/۲۱رد + «بدون خرابی
    نیمه‌کاره» (نه ردیف DB، نه فایل روی دیسک) + برهم‌کنش با حذف/بازیابی
    (پیوست بازیابی‌شده هم در سقف می‌شمارد).

هر تست روی دیتابیس/پوشهٔ پیوست موقت تازه اجرا می‌شود.
"""

import contextlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.connection as _dbc
from config import settings as _settings


class AttachmentRestoreTestBase(unittest.TestCase):
    """پایهٔ مشترک: دیتابیس موقت + پوشهٔ پیوست موقت"""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="partow_att_")
        self._saved = (
            _settings.DB_PATH, _dbc.DB_PATH,
            getattr(_settings, 'ATTACHMENTS_DIR', None),
        )
        _settings.DB_PATH = os.path.join(self._tmpdir, "partow.db")
        _dbc.DB_PATH = _settings.DB_PATH
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False

        # پوشهٔ پیوست‌ها باید داخل همان محیط موقت باشد؛ ماژول‌های
        # attachment از config.settings.ATTACHMENTS_DIR می‌خوانند
        att_dir = os.path.join(self._tmpdir, "attachments")
        _settings.ATTACHMENTS_DIR = att_dir
        import config.settings as _cfg
        _cfg.ATTACHMENTS_DIR = att_dir
        import dal.attachment_dal as _ad
        _ad.ATTACHMENTS_DIR = att_dir
        self.att_dir = att_dir

        _dbc.DatabaseConnection()  # seed (admin/manager + سال پیش‌فرض)
        from services.attachment_service import AttachmentService
        self.service = AttachmentService()

    def tearDown(self):
        with contextlib.suppress(Exception):
            _dbc.DatabaseConnection().close_all()
        db_path, dbc_path, att_dir = self._saved
        _settings.DB_PATH, _dbc.DB_PATH = db_path, dbc_path
        if att_dir is not None:
            _settings.ATTACHMENTS_DIR = att_dir
        _dbc.DatabaseConnection._instance = None
        _dbc.DatabaseConnection._connection = None
        _dbc.DatabaseConnection._initialized = False

    # ---------------- کمکی ----------------

    def upload(self, name="f.txt", content=b"hello", entity=("observation", 1)):
        return self.service.upload_attachment(
            entity[0], entity[1], content, name,
            created_by=None, user_id=None)

    def upload_n(self, n, entity=("observation", 1)):
        ids = []
        for i in range(n):
            att = self.upload(
                f"file_{i:02d}.txt", f"content-{i}".encode(), entity)
            ids.append(att.id)
        return ids


class TestRestoreRoundtrip(AttachmentRestoreTestBase):
    """BUG-ATT-04: چرخهٔ کامل حذف → بازیابی بدون از دست رفتن چیزی"""

    def test_delete_then_restore_roundtrip(self):
        att = self.upload("report.pdf", b"%PDF-1.4 test")
        path = att.file_path
        self.assertTrue(os.path.exists(path))

        # حذف منطقی: فایل فیزیکی می‌ماند
        self.service.delete_attachment(att.id)
        self.assertTrue(os.path.exists(path))
        self.assertIsNone(self.service.attachment_dal.get_by_id(att.id))

        # بازیابی
        restored = self.service.restore_attachment(att.id)
        self.assertEqual(restored.id, att.id)
        self.assertFalse(getattr(restored, "is_deleted", 0))

        # بازخوانی مستقل: تنها شاهد واقعی
        again = self.service.get_attachment(att.id)
        self.assertIsNotNone(again)
        self.assertFalse(getattr(again, "is_deleted", 0))

        # محتوا همچنان خوانا و همان محتوای اول
        content = self.service.get_attachment_content(att.id)
        self.assertEqual(content, b"%PDF-1.4 test")

    def test_restore_non_deleted_raises(self):
        att = self.upload()
        from utils.error_handler import ServiceError
        with self.assertRaises(ServiceError):
            self.service.restore_attachment(att.id)

    def test_restore_missing_id_raises(self):
        from utils.error_handler import ServiceError
        with self.assertRaises(ServiceError):
            self.service.restore_attachment(999999)

    def test_dal_restore_real_result_contract(self):
        """قرارداد DAL: فقط رکوردِ واقعاً حذف‌شده بازیابی می‌شود"""
        att = self.upload()
        # بازیابیِ رکورد فعال → rowcount=0 → False (نه True ثابت)
        self.assertFalse(self.service.attachment_dal.restore(att.id))
        self.service.delete_attachment(att.id)
        # حالا باید True بدهد
        self.assertTrue(self.service.attachment_dal.restore(att.id))
        # و بار دوم باز False
        self.assertFalse(self.service.attachment_dal.restore(att.id))

    def test_get_deleted_by_entity_lists_exactly_deleted(self):
        a = self.upload("a.txt")
        self.upload("b.txt")
        c = self.upload("c.txt")
        self.service.delete_attachment(a.id)
        self.service.delete_attachment(c.id)
        deleted = self.service.get_deleted_attachments_by_entity(
            "observation", 1)
        self.assertEqual(sorted(x.id for x in deleted), [a.id, c.id])


class TestRestoreVerifiesPhysicalFile(AttachmentRestoreTestBase):
    """BUG-ATT-05: بازیابی بدون فایل فیزیکی نباید موفقیت خاموش بدهد"""

    def test_restore_without_physical_file_fails_and_keeps_deleted(self):
        att = self.upload("ghost.txt", b"will vanish")
        self.service.delete_attachment(att.id)

        # فایل فیزیکی «گم» می‌شود (مثلاً پاک‌شدن دستی)
        os.remove(att.file_path)

        from utils.error_handler import ServiceError
        with self.assertRaises(ServiceError) as ctx:
            self.service.restore_attachment(att.id)
        self.assertIn("فایل فیزیکی", str(ctx.exception))

        # رکورد باید «حذف‌شده» بماند — نه نیمه‌بازیابی‌شده
        row = _dbc.DatabaseConnection().get_connection().execute(
            "SELECT is_deleted FROM attachments WHERE id = ?",
            (att.id,)).fetchone()
        self.assertEqual(row["is_deleted"], 1)
        # و در فهرست حذف‌شده‌ها هم هست (کاربر می‌تواند وضعیت را ببیند)
        deleted = self.service.get_deleted_attachments_by_entity(
            "observation", 1)
        self.assertIn(att.id, [x.id for x in deleted])

    def test_restore_with_empty_path_fails(self):
        """مسیر خالی در DB (رکورد خراب) → خطای صریح، نه استثنای خاموش"""
        att = self.upload("no_path.txt", b"x")
        self.service.delete_attachment(att.id)
        conn = _dbc.DatabaseConnection().get_connection()
        conn.execute("UPDATE attachments SET file_path = '' WHERE id = ?",
                     (att.id,))
        conn.commit()

        from utils.error_handler import ServiceError
        with self.assertRaises(ServiceError):
            self.service.restore_attachment(att.id)


class TestAttachmentLimit(AttachmentRestoreTestBase):
    """BUG-ATT-06: سقف ۲۰ پیوست — ۲۰قبول/۲۱رد + بدون خرابی نیمه‌کاره"""

    ENTITY = ("observation", 7)

    def test_twenty_accepted(self):
        ids = self.upload_n(20, self.ENTITY)
        self.assertEqual(len(set(ids)), 20)
        count = self.service.attachment_dal.get_count_by_entity(*self.ENTITY)
        self.assertEqual(count, 20)

    def test_twenty_first_rejected_without_corruption(self):
        self.upload_n(20, self.ENTITY)
        disk_before = set()
        root = os.path.join(self.att_dir, self.ENTITY[0], str(self.ENTITY[1]))
        if os.path.exists(root):
            disk_before = set(os.listdir(root))

        # (ValidationError در مرز execute_in_transaction به ServiceError
        #  با حفظ پیام اصلی تبدیل می‌شود — قرارداد موجود پروژه)
        from utils.error_handler import ServiceError
        with self.assertRaises(ServiceError) as ctx:
            self.upload("the_21st.txt", b"over the limit", self.ENTITY)
        self.assertIn("حداکثر", str(ctx.exception))

        # نه ردیف تازه، نه فایل یتیم روی دیسک
        count = self.service.attachment_dal.get_count_by_entity(*self.ENTITY)
        self.assertEqual(count, 20)
        disk_after = set()
        if os.path.exists(root):
            disk_after = set(os.listdir(root))
        self.assertEqual(disk_before, disk_after)

    def test_delete_frees_slot_then_upload_works(self):
        ids = self.upload_n(20, self.ENTITY)
        self.service.delete_attachment(ids[0])
        # ۱۹ فعال → جا برای یکی
        self.upload("after_delete.txt", b"fits now", self.ENTITY)
        count = self.service.attachment_dal.get_count_by_entity(*self.ENTITY)
        self.assertEqual(count, 20)

    def test_restored_attachments_count_toward_limit(self):
        """پیوست بازیابی‌شده هم در سقف می‌شمارد (نکتهٔ مأموریت در ATT-06)"""
        ids = self.upload_n(20, self.ENTITY)
        victim = ids[0]
        self.service.delete_attachment(victim)

        # جا باز شد؛ یکی دیگر آپلود می‌کنیم → دوباره ۲۰ فعال
        extra = self.upload("extra.txt", b"extra", self.ENTITY)
        count = self.service.attachment_dal.get_count_by_entity(*self.ENTITY)
        self.assertEqual(count, 20)

        # حالا بازیابی victim یعنی ۲۱ فعال → باید رد شود
        from utils.error_handler import ServiceError
        with self.assertRaises(ServiceError) as ctx:
            self.service.restore_attachment(victim)
        self.assertIn("حداکثر", str(ctx.exception))

        # با حذف یکی، بازیابی ممکن می‌شود
        self.service.delete_attachment(extra.id)
        restored = self.service.restore_attachment(victim)
        self.assertEqual(restored.id, victim)
        count = self.service.attachment_dal.get_count_by_entity(*self.ENTITY)
        self.assertEqual(count, 20)

    def test_limit_is_per_entity_not_global(self):
        """سقف برای هر موجودیت جداگانه است، نه روی کل سیستم"""
        self.upload_n(20, self.ENTITY)
        other = ("intervention", 3)
        ids = self.upload_n(20, other)
        self.assertEqual(len(ids), 20)
        count = self.service.attachment_dal.get_count_by_entity(*other)
        self.assertEqual(count, 20)


class TestRestoreAudit(AttachmentRestoreTestBase):
    """بازیابی پیوست باید ردیف Audit داشته باشد (بدون سکوت)"""

    def test_restore_is_audited(self):
        att = self.upload("audited.txt", b"audit me")
        self.service.delete_attachment(att.id)
        self.service.restore_attachment(att.id)

        conn = _dbc.DatabaseConnection().get_connection()
        # تریگر trg_attachments_restore_audit خودش ردیف را می‌نویسد
        # (entity_type = نام جدول)؛ log_auditِ سرویس هم عمداً از ثبت
        # تکراری می‌گذرد — پس دقیقاً یک ردیف باید باشد.
        rows = conn.execute(
            "SELECT action, entity_type, entity_id FROM audit_logs "
            "WHERE entity_id = ? AND action = 'restore' AND "
            "entity_type IN ('attachment', 'attachments')",
            (att.id,)).fetchall()
        self.assertEqual(len(rows), 1,
                         "دقیقاً یک ردیف Audit برای بازیابی (تریگر، بدون تکرار)")

    def test_delete_then_restore_then_delete_audit_chain(self):
        att = self.upload("chain.txt", b"chain")
        self.service.delete_attachment(att.id)
        self.service.restore_attachment(att.id)
        self.service.delete_attachment(att.id)

        conn = _dbc.DatabaseConnection().get_connection()
        rows = conn.execute(
            "SELECT action FROM audit_logs "
            "WHERE entity_id = ? AND entity_type IN "
            "('attachment', 'attachments') ORDER BY id",
            (att.id,)).fetchall()
        actions = [r["action"] for r in rows]
        self.assertIn("delete_soft", actions)
        self.assertIn("restore", actions)
        self.assertEqual(actions.count("delete_soft"), 2)
        self.assertEqual(actions.count("restore"), 1)


if __name__ == "__main__":
    unittest.main()
