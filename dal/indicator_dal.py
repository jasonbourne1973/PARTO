"""
لایه دسترسی به داده شاخص‌ها (Indicator)
"""

from database.connection import DatabaseConnection
from models.indicator import Indicator


class IndicatorDAL:
    """عملیات CRUD برای شاخص‌ها"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, indicator):
        """ایجاد شاخص جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO indicators (
                competency_id, title, description, sort_order
            ) VALUES (?, ?, ?, ?)
        """, (
            indicator.competency_id,
            indicator.title,
            indicator.description,
            indicator.sort_order
        ))
        
        conn.commit()
        indicator.id = cursor.lastrowid
        return indicator
    
    def get_by_id(self, indicator_id, include_deleted=False):
        """دریافت شاخص با شناسه"""
        query = "SELECT * FROM indicators WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (indicator_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_indicator(row)
        return None
    
    def get_by_competency(self, competency_id, include_deleted=False):
        """دریافت شاخص‌های یک شایستگی"""
        query = "SELECT * FROM indicators WHERE competency_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY sort_order, title"
        
        cursor = self.db.execute_query(query, (competency_id,))
        rows = cursor.fetchall()
        return [self._row_to_indicator(row) for row in rows]
    
    def get_all(self, include_deleted=False):
        """دریافت همه شاخص‌ها"""
        query = "SELECT * FROM indicators"
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        query += " ORDER BY competency_id, sort_order, title"
        
        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        return [self._row_to_indicator(row) for row in rows]
    
    def search(self, search_term, include_deleted=False):
        """جستجوی شاخص‌ها بر اساس عنوان یا توضیحات"""
        search_pattern = f"%{search_term}%"
        query = """
            SELECT * FROM indicators 
            WHERE title LIKE ? OR description LIKE ?
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY competency_id, sort_order, title"
        
        cursor = self.db.execute_query(query, (search_pattern, search_pattern))
        rows = cursor.fetchall()
        return [self._row_to_indicator(row) for row in rows]
    
    def update(self, indicator):
        """به‌روزرسانی شاخص"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE indicators SET
                competency_id = ?,
                title = ?,
                description = ?,
                sort_order = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            indicator.competency_id,
            indicator.title,
            indicator.description,
            indicator.sort_order,
            indicator.id
        ))
        
        conn.commit()
        return indicator
    
    def delete(self, indicator_id, user_id=None):
        """حذف منطقی شاخص"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # بررسی وجود رکورد
        cursor.execute(
            "SELECT id FROM indicators WHERE id = ? AND is_deleted = 0",
            (indicator_id,)
        )
        if not cursor.fetchone():
            return False
        
        from datetime import datetime
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE indicators SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, indicator_id))
        
        conn.commit()
        return True
    
    def restore(self, indicator_id, user_id=None):
        """بازیابی شاخص حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE indicators SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (indicator_id,))
        
        conn.commit()
        return True
    
    def _row_to_indicator(self, row):
        """تبدیل ردیف دیتابیس به مدل Indicator"""
        indicator = Indicator()
        indicator.id = row['id']
        indicator.competency_id = row['competency_id']
        indicator.title = row['title']
        indicator.description = row['description']
        indicator.sort_order = row['sort_order']
        indicator.created_at = row['created_at']
        indicator.updated_at = row['updated_at']
        indicator.is_deleted = row['is_deleted']
        indicator.deleted_at = row['deleted_at']
        indicator.deleted_by = row['deleted_by']
        return indicator