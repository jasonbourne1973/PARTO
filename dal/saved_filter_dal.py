"""
لایه دسترسی به داده فیلترهای ذخیره‌شده
"""

import json

from database.connection import DatabaseConnection
from models.saved_filter import SavedFilter
from utils.time_utils import utc_now_iso


class SavedFilterDAL:
    """عملیات CRUD برای فیلترهای ذخیره‌شده"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, saved_filter):
        """ایجاد فیلتر جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        filter_params_json = json.dumps(saved_filter.filter_params, ensure_ascii=False) if saved_filter.filter_params else '{}'
        
        cursor.execute("""
            INSERT INTO saved_filters (
                name, description, filter_type, visibility,
                user_id, filter_params, use_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            saved_filter.name,
            saved_filter.description,
            saved_filter.filter_type,
            saved_filter.visibility,
            saved_filter.user_id,
            filter_params_json,
            saved_filter.use_count or 0
        ))
        
        conn.commit()
        saved_filter.id = cursor.lastrowid
        return saved_filter
    
    def get_by_id(self, filter_id, include_deleted=False):
        """دریافت فیلتر با شناسه"""
        query = "SELECT * FROM saved_filters WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (filter_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_filter(row)
        return None
    
    def get_by_user(self, user_id, filter_type=None, include_deleted=False):
        """دریافت فیلترهای یک کاربر"""
        query = """
            SELECT * FROM saved_filters 
            WHERE user_id = ?
        """
        params = [user_id]
        
        if filter_type:
            query += " AND filter_type = ?"
            params.append(filter_type)
        
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY use_count DESC, created_at DESC"
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_filter(row) for row in rows]
    
    def get_shared_filters(self, filter_type=None, include_deleted=False):
        """دریافت فیلترهای اشتراکی"""
        query = """
            SELECT * FROM saved_filters 
            WHERE visibility IN (?, ?)
        """
        params = [SavedFilter.VISIBILITY_SHARED, SavedFilter.VISIBILITY_TEAM]
        
        if filter_type:
            query += " AND filter_type = ?"
            params.append(filter_type)
        
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY use_count DESC, created_at DESC"
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_filter(row) for row in rows]
    
    def get_by_type(self, filter_type, user_id=None, include_deleted=False):
        """دریافت فیلترها بر اساس نوع"""
        query = "SELECT * FROM saved_filters WHERE filter_type = ?"
        params = [filter_type]
        
        if user_id:
            query += " AND (user_id = ? OR visibility IN (?, ?))"
            params.extend([user_id, SavedFilter.VISIBILITY_SHARED, SavedFilter.VISIBILITY_TEAM])
        else:
            query += " AND visibility IN (?, ?)"
            params.extend([SavedFilter.VISIBILITY_SHARED, SavedFilter.VISIBILITY_TEAM])
        
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY use_count DESC, created_at DESC"
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_filter(row) for row in rows]
    
    def get_all(self, limit=None, include_deleted=False):
        """دریافت همه فیلترها"""
        query = "SELECT * FROM saved_filters"
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        query += " ORDER BY use_count DESC, created_at DESC"
        
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params if params else None)
        rows = cursor.fetchall()
        return [self._row_to_filter(row) for row in rows]
    
    def update(self, saved_filter):
        """به‌روزرسانی فیلتر"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        filter_params_json = json.dumps(saved_filter.filter_params, ensure_ascii=False) if saved_filter.filter_params else '{}'
        
        cursor.execute("""
            UPDATE saved_filters SET
                name = ?,
                description = ?,
                filter_type = ?,
                visibility = ?,
                user_id = ?,
                filter_params = ?,
                use_count = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            saved_filter.name,
            saved_filter.description,
            saved_filter.filter_type,
            saved_filter.visibility,
            saved_filter.user_id,
            filter_params_json,
            saved_filter.use_count or 0,
            saved_filter.id
        ))
        
        conn.commit()
        return saved_filter
    
    def increment_use(self, filter_id):
        """افزایش تعداد استفاده از فیلتر"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE saved_filters SET
                use_count = use_count + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (filter_id,))
        
        conn.commit()
        return True
    
    def delete(self, filter_id, user_id=None):
        """حذف منطقی فیلتر"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM saved_filters WHERE id = ? AND is_deleted = 0",
            (filter_id,)
        )
        if not cursor.fetchone():
            return False
        
        now = utc_now_iso()
        cursor.execute("""
            UPDATE saved_filters SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, filter_id))
        
        conn.commit()
        return True
    
    def restore(self, filter_id):
        """بازیابی فیلتر حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE saved_filters SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (filter_id,))
        
        conn.commit()
        return True
    
    def get_popular_filters(self, filter_type=None, limit=10):
        """دریافت پرکاربردترین فیلترها"""
        query = """
            SELECT * FROM saved_filters 
            WHERE is_deleted = 0
        """
        params = []
        
        if filter_type:
            query += " AND filter_type = ?"
            params.append(filter_type)
        
        query += " ORDER BY use_count DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_filter(row) for row in rows]
    
    def _row_to_filter(self, row):
        """تبدیل ردیف دیتابیس به مدل SavedFilter"""
        saved_filter = SavedFilter()
        saved_filter.id = row['id']
        saved_filter.name = row['name']
        saved_filter.description = row['description']
        saved_filter.filter_type = row['filter_type']
        saved_filter.visibility = row['visibility']
        saved_filter.user_id = row['user_id']
        
        if row['filter_params']:
            try:
                saved_filter.filter_params = json.loads(row['filter_params'])
            except Exception:
                saved_filter.filter_params = {}
        else:
            saved_filter.filter_params = {}
        
        saved_filter.use_count = row['use_count'] or 0
        saved_filter.created_at = row['created_at']
        saved_filter.updated_at = row['updated_at']
        saved_filter.is_deleted = row['is_deleted']
        saved_filter.deleted_at = row['deleted_at']
        saved_filter.deleted_by = row['deleted_by']
        
        return saved_filter