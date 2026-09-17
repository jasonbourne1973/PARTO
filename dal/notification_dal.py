"""
لایه دسترسی به داده اعلان‌ها
"""

from database.connection import DatabaseConnection
from models.notification import Notification
from datetime import datetime


class NotificationDAL:
    """عملیات CRUD برای اعلان‌ها"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, notification):
        """ایجاد اعلان جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notifications (
                user_id, type, priority, title, message,
                link, entity_type, entity_id,
                is_read, read_at, is_dismissed, dismissed_at,
                scheduled_at, expires_at, related_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            notification.user_id,
            notification.type,
            notification.priority,
            notification.title,
            notification.message,
            notification.link,
            notification.entity_type,
            notification.entity_id,
            1 if notification.is_read else 0,
            notification.read_at,
            1 if notification.is_dismissed else 0,
            notification.dismissed_at,
            notification.scheduled_at,
            notification.expires_at,
            notification.related_data
        ))
        
        conn.commit()
        notification.id = cursor.lastrowid
        return notification
    
    def get_by_id(self, notification_id):
        """دریافت اعلان با شناسه"""
        cursor = self.db.execute_query(
            "SELECT * FROM notifications WHERE id = ? AND is_deleted = 0",
            (notification_id,)
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_notification(row)
        return None
    
    def get_by_user(self, user_id, limit=None, include_read=False):
        """دریافت اعلان‌های یک کاربر"""
        query = """
            SELECT * FROM notifications 
            WHERE user_id = ? AND is_deleted = 0
        """
        params = [user_id]
        
        if not include_read:
            query += " AND is_read = 0 AND is_dismissed = 0"
        
        query += " ORDER BY created_at DESC"
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_notification(row) for row in rows]
    
    def get_unread_count(self, user_id):
        """دریافت تعداد اعلان‌های خوانده نشده"""
        cursor = self.db.execute_query("""
            SELECT COUNT(*) as count 
            FROM notifications 
            WHERE user_id = ? AND is_read = 0 AND is_dismissed = 0 AND is_deleted = 0
        """, (user_id,))
        row = cursor.fetchone()
        return row['count'] if row else 0
    
    def get_by_type(self, user_id, notification_type, limit=None):
        """دریافت اعلان‌های یک نوع خاص"""
        query = """
            SELECT * FROM notifications 
            WHERE user_id = ? AND type = ? AND is_deleted = 0
            ORDER BY created_at DESC
        """
        params = [user_id, notification_type]
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_notification(row) for row in rows]
    
    def get_all(self, limit=None, user_id=None):
        """دریافت همه اعلان‌ها"""
        query = "SELECT * FROM notifications WHERE is_deleted = 0"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY created_at DESC"
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params if params else None)
        rows = cursor.fetchall()
        return [self._row_to_notification(row) for row in rows]
    
    def get_pending(self, limit=None):
        """دریافت اعلان‌های در انتظار (برنامه‌ریزی شده)"""
        now = datetime.now().isoformat()
        query = """
            SELECT * FROM notifications 
            WHERE scheduled_at IS NOT NULL 
            AND scheduled_at <= ? 
            AND is_read = 0 
            AND is_dismissed = 0 
            AND is_deleted = 0
            ORDER BY scheduled_at ASC
        """
        params = [now]
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_notification(row) for row in rows]
    
    def get_active(self, user_id, limit=None):
        """دریافت اعلان‌های فعال (خوانده نشده و رد نشده)"""
        return self.get_by_user(user_id, limit, include_read=False)
    
    def mark_as_read(self, notification_id):
        """علامت‌گذاری اعلان به عنوان خوانده شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE notifications SET
                is_read = 1,
                read_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (now, notification_id))
        
        conn.commit()
        return True
    
    def mark_all_as_read(self, user_id):
        """علامت‌گذاری همه اعلان‌های کاربر به عنوان خوانده شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE notifications SET
                is_read = 1,
                read_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND is_read = 0 AND is_dismissed = 0 AND is_deleted = 0
        """, (now, user_id))
        
        conn.commit()
        return True
    
    def mark_as_dismissed(self, notification_id):
        """علامت‌گذاری اعلان به عنوان رد شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE notifications SET
                is_dismissed = 1,
                dismissed_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (now, notification_id))
        
        conn.commit()
        return True
    
    def delete(self, notification_id):
        """حذف منطقی اعلان"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE notifications SET
                is_deleted = 1,
                deleted_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (notification_id,))
        
        conn.commit()
        return True
    
    def delete_old(self, days=30):
        """حذف اعلان‌های قدیمی"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        from datetime import datetime, timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            UPDATE notifications SET
                is_deleted = 1,
                deleted_at = CURRENT_TIMESTAMP
            WHERE created_at < ? AND is_deleted = 0
        """, (cutoff_date,))
        
        conn.commit()
        return True
    
    def _row_to_notification(self, row):
        """تبدیل ردیف دیتابیس به مدل Notification"""
        notification = Notification()
        notification.id = row['id']
        notification.user_id = row['user_id']
        notification.type = row['type']
        notification.priority = row['priority']
        notification.title = row['title']
        notification.message = row['message']
        notification.link = row['link']
        notification.entity_type = row['entity_type']
        notification.entity_id = row['entity_id']
        notification.is_read = bool(row['is_read'])
        notification.read_at = row['read_at']
        notification.is_dismissed = bool(row['is_dismissed'])
        notification.dismissed_at = row['dismissed_at']
        notification.scheduled_at = row['scheduled_at']
        notification.expires_at = row['expires_at']
        notification.related_data = row['related_data']
        notification.created_at = row['created_at']
        notification.updated_at = row['updated_at']
        notification.is_deleted = row['is_deleted']
        notification.deleted_at = row['deleted_at']
        return notification