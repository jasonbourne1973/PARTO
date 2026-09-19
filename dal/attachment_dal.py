"""
لایه دسترسی به داده پیوست‌ها - نسخه کامل
"""

import os

from config.settings import ATTACHMENTS_DIR
from database.connection import DatabaseConnection
from models.attachment import Attachment
from utils.logger import get_logger


class AttachmentDAL:
    """عملیات CRUD برای پیوست‌ها"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = get_logger(self.__class__.__name__)
        
        # اطمینان از وجود پوشه پیوست‌ها
        if not os.path.exists(ATTACHMENTS_DIR):
            os.makedirs(ATTACHMENTS_DIR)
    
    def create(self, attachment):
        """ایجاد پیوست جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO attachments (
                entity_type, entity_id, file_name, file_path,
                file_size, file_type, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            attachment.entity_type,
            attachment.entity_id,
            attachment.file_name,
            attachment.file_path,
            attachment.file_size,
            attachment.file_type,
            attachment.created_by
        ))
        
        conn.commit()
        attachment.id = cursor.lastrowid
        self.logger.info(f"پیوست با ID {attachment.id} ایجاد شد: {attachment.file_name}")
        return attachment
    
    def get_by_id(self, attachment_id):
        """دریافت پیوست با شناسه"""
        cursor = self.db.execute_query(
            "SELECT * FROM attachments WHERE id = ? AND is_deleted = 0",
            (attachment_id,)
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_attachment(row)
        return None
    
    def get_by_entity(self, entity_type, entity_id):
        """دریافت پیوست‌های یک موجودیت"""
        cursor = self.db.execute_query("""
            SELECT * FROM attachments 
            WHERE entity_type = ? AND entity_id = ? AND is_deleted = 0
            ORDER BY created_at DESC
        """, (entity_type, entity_id))
        rows = cursor.fetchall()
        return [self._row_to_attachment(row) for row in rows]
    
    def get_by_entity_and_type(self, entity_type, entity_id, file_type):
        """دریافت پیوست‌های یک موجودیت با فیلتر نوع فایل"""
        cursor = self.db.execute_query("""
            SELECT * FROM attachments 
            WHERE entity_type = ? AND entity_id = ? AND file_type = ? AND is_deleted = 0
            ORDER BY created_at DESC
        """, (entity_type, entity_id, file_type))
        rows = cursor.fetchall()
        return [self._row_to_attachment(row) for row in rows]
    
    def get_all(self, limit=None):
        """دریافت همه پیوست‌ها"""
        query = "SELECT * FROM attachments WHERE is_deleted = 0 ORDER BY created_at DESC"
        params = []
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params if params else None)
        rows = cursor.fetchall()
        return [self._row_to_attachment(row) for row in rows]
    
    def update(self, attachment):
        """به‌روزرسانی پیوست"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE attachments SET
                file_name = ?, file_path = ?, file_size = ?,
                file_type = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            attachment.file_name,
            attachment.file_path,
            attachment.file_size,
            attachment.file_type,
            attachment.id
        ))
        
        conn.commit()
        return attachment
    
    def delete(self, attachment_id, user_id=None):
        """
        حذف منطقی پیوست

        ===== اصلاح مهم =====
        نسخه قبلی همزمان با حذف منطقی (is_deleted = 1)، فایل فیزیکی
        را هم از روی دیسک پاک می‌کرد:

            os.remove(attachment.file_path)

        یعنی یک «حذف منطقی» که برگشت‌ناپذیر بود. اگر کاربر اشتباهی
        پیوستی را حذف می‌کرد، ردیف دیتابیس سر جایش می‌ماند ولی فایل
        رفته بود — و هیچ راه بازگرداندنی وجود نداشت. بدتر: اگر دو
        پیوست به یک فایل اشاره می‌کردند، حذف یکی فایل دیگری را هم
        از بین می‌برد.

        حالا حذف منطقی واقعاً منطقی است. حذف فایل فیزیکی به متد
        جداگانه‌ای منتقل شده که فقط از مسیر «حذف دائم» صدا زده
        می‌شود.
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # حذف منطقی در دیتابیس (فایل دست‌نخورده می‌ماند)
        cursor.execute("""
            UPDATE attachments SET
                is_deleted = 1,
                deleted_at = CURRENT_TIMESTAMP,
                deleted_by = ?
            WHERE id = ?
        """, (user_id, attachment_id))
        
        conn.commit()
        self.logger.info(f"پیوست با ID {attachment_id} حذف شد")
        return True
    
    def permanent_delete(self, attachment_id, user_id=None):
        """
        حذف دائم پیوست: هم ردیف دیتابیس، هم فایل فیزیکی

        این متد برگشت‌ناپذیر است. باید فقط بعد از تأیید صریح کاربر
        و ترجیحاً از صفحه «مدیریت فایل‌های حذف‌شده» صدا زده شود.
        """
        attachment = self.get_by_id(attachment_id)

        conn = self.db.get_connection()
        cursor = conn.cursor()

        # اول ردیف دیتابیس حذف می‌شود تا اگر حذف فایل شکست خورد،
        # وضعیت نصفه‌نیمه نماند
        cursor.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        conn.commit()

        if attachment and attachment.file_path:
            # فقط اگر هیچ پیوست دیگری به همین مسیر اشاره نمی‌کند
            cursor.execute(
                "SELECT COUNT(*) FROM attachments WHERE file_path = ?",
                (attachment.file_path,)
            )
            still_referenced = cursor.fetchone()[0]
            if still_referenced == 0 and os.path.exists(attachment.file_path):
                try:
                    os.remove(attachment.file_path)
                    self.logger.info(f"فایل پیوست برای همیشه حذف شد: {attachment.file_path}")
                except OSError as e:
                    self.logger.warning(f"خطا در حذف فایل: {e}")

        self.logger.info(f"پیوست با ID {attachment_id} برای همیشه حذف شد")
        return True

    def delete_by_entity(self, entity_type, entity_id, user_id=None):
        """حذف تمام پیوست‌های یک موجودیت"""
        attachments = self.get_by_entity(entity_type, entity_id)
        for attachment in attachments:
            self.delete(attachment.id, user_id)
        return True
    
    def get_total_size_by_entity(self, entity_type, entity_id):
        """دریافت حجم کل پیوست‌های یک موجودیت"""
        cursor = self.db.execute_query("""
            SELECT SUM(file_size) as total_size 
            FROM attachments 
            WHERE entity_type = ? AND entity_id = ? AND is_deleted = 0
        """, (entity_type, entity_id))
        row = cursor.fetchone()
        return row['total_size'] if row and row['total_size'] else 0
    
    def get_count_by_entity(self, entity_type, entity_id):
        """دریافت تعداد پیوست‌های یک موجودیت"""
        cursor = self.db.execute_query("""
            SELECT COUNT(*) as count 
            FROM attachments 
            WHERE entity_type = ? AND entity_id = ? AND is_deleted = 0
        """, (entity_type, entity_id))
        row = cursor.fetchone()
        return row['count'] if row else 0
    
    def get_attachment_stats(self):
        """دریافت آمار کلی پیوست‌ها"""
        cursor = self.db.execute_query("""
            SELECT 
                COUNT(*) as total_count,
                SUM(file_size) as total_size,
                entity_type,
                COUNT(*) as type_count
            FROM attachments 
            WHERE is_deleted = 0
            GROUP BY entity_type
        """)
        rows = cursor.fetchall()
        
        stats = {
            'total_count': 0,
            'total_size': 0,
            'by_type': {}
        }
        
        for row in rows:
            stats['total_count'] += row['type_count']
            stats['total_size'] += row['total_size'] or 0
            stats['by_type'][row['entity_type']] = {
                'count': row['type_count'],
                'size': row['total_size'] or 0
            }
        
        return stats
    
    def _row_to_attachment(self, row):
        """تبدیل ردیف دیتابیس به مدل Attachment"""
        attachment = Attachment()
        attachment.id = row['id']
        attachment.entity_type = row['entity_type']
        attachment.entity_id = row['entity_id']
        attachment.file_name = row['file_name']
        attachment.file_path = row['file_path']
        attachment.file_size = row['file_size']
        attachment.file_type = row['file_type']
        attachment.created_by = row['created_by']
        attachment.created_at = row['created_at']
        attachment.is_deleted = row['is_deleted']
        attachment.deleted_at = row['deleted_at']
        attachment.deleted_by = row['deleted_by']
        return attachment