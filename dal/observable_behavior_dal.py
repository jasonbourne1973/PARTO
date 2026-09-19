"""
لایه دسترسی به داده رفتارهای قابل مشاهده (ObservableBehavior)
"""

from database.connection import DatabaseConnection
from models.observable_behavior import ObservableBehavior
from utils.time_utils import utc_now_iso


class ObservableBehaviorDAL:
    """عملیات CRUD برای رفتارهای قابل مشاهده"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, behavior):
        """ایجاد رفتار قابل مشاهده جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO observable_behaviors (
                indicator_id, competency_id, text, sort_order
            ) VALUES (?, ?, ?, ?)
        """, (
            behavior.indicator_id,
            behavior.competency_id,
            behavior.text,
            behavior.sort_order
        ))
        
        conn.commit()
        behavior.id = cursor.lastrowid
        return behavior
    
    def get_by_id(self, behavior_id, include_deleted=False):
        """دریافت رفتار قابل مشاهده با شناسه"""
        query = "SELECT * FROM observable_behaviors WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (behavior_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_behavior(row)
        return None
    
    def get_by_indicator(self, indicator_id, include_deleted=False):
        """دریافت رفتارهای قابل مشاهده یک شاخص"""
        query = "SELECT * FROM observable_behaviors WHERE indicator_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY sort_order, text"
        
        cursor = self.db.execute_query(query, (indicator_id,))
        rows = cursor.fetchall()
        return [self._row_to_behavior(row) for row in rows]
    
    def get_by_competency(self, competency_id, include_deleted=False):
        """دریافت رفتارهای قابل مشاهده یک شایستگی"""
        query = "SELECT * FROM observable_behaviors WHERE competency_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY indicator_id, sort_order, text"
        
        cursor = self.db.execute_query(query, (competency_id,))
        rows = cursor.fetchall()
        return [self._row_to_behavior(row) for row in rows]
    
    def get_all(self, include_deleted=False):
        """دریافت همه رفتارهای قابل مشاهده"""
        query = "SELECT * FROM observable_behaviors"
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        query += " ORDER BY competency_id, indicator_id, sort_order, text"
        
        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        return [self._row_to_behavior(row) for row in rows]
    
    def search(self, search_term, include_deleted=False):
        """جستجوی رفتارهای قابل مشاهده بر اساس متن"""
        search_pattern = f"%{search_term}%"
        query = "SELECT * FROM observable_behaviors WHERE text LIKE ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY competency_id, indicator_id, sort_order, text"
        
        cursor = self.db.execute_query(query, (search_pattern,))
        rows = cursor.fetchall()
        return [self._row_to_behavior(row) for row in rows]
    
    def update(self, behavior):
        """به‌روزرسانی رفتار قابل مشاهده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE observable_behaviors SET
                indicator_id = ?,
                competency_id = ?,
                text = ?,
                sort_order = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            behavior.indicator_id,
            behavior.competency_id,
            behavior.text,
            behavior.sort_order,
            behavior.id
        ))
        
        conn.commit()
        return behavior
    
    def delete(self, behavior_id, user_id=None):
        """حذف منطقی رفتار قابل مشاهده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM observable_behaviors WHERE id = ? AND is_deleted = 0",
            (behavior_id,)
        )
        if not cursor.fetchone():
            return False
        
        now = utc_now_iso()
        cursor.execute("""
            UPDATE observable_behaviors SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, behavior_id))
        
        conn.commit()
        return True
    
    def restore(self, behavior_id, user_id=None):
        """بازیابی رفتار قابل مشاهده حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE observable_behaviors SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (behavior_id,))
        
        conn.commit()
        return True
    
    def _row_to_behavior(self, row):
        """تبدیل ردیف دیتابیس به مدل ObservableBehavior"""
        behavior = ObservableBehavior()
        behavior.id = row['id']
        behavior.indicator_id = row['indicator_id']
        behavior.competency_id = row['competency_id']
        behavior.text = row['text']
        behavior.sort_order = row['sort_order']
        behavior.created_at = row['created_at']
        behavior.updated_at = row['updated_at']
        behavior.is_deleted = row['is_deleted']
        behavior.deleted_at = row['deleted_at']
        behavior.deleted_by = row['deleted_by']
        return behavior