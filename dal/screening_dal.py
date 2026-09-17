"""
لایه دسترسی به داده غربالگری (Screening) - اصلاح شده
"""

from database.connection import DatabaseConnection
from models.screening import Screening
import json


class ScreeningDAL:
    """عملیات CRUD برای غربالگری"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, screening):
        """ایجاد غربالگری جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # تبدیل domain_scores به JSON (به جای raw_scores)
        domain_scores_json = json.dumps(screening.domain_scores, ensure_ascii=False) if screening.domain_scores else None
        
        cursor.execute("""
            INSERT INTO screenings (
                student_profile_id, staff_id,
                tool_name, tool_version,
                execution_date, execution_context,
                domain_scores, total_score,
                domain, sub_domain,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            screening.student_profile_id,
            screening.staff_id,
            screening.tool_name,
            screening.tool_version,
            screening.execution_date,
            screening.execution_context,
            domain_scores_json,
            screening.total_score,
            screening.domain,
            screening.sub_domain,
            screening.status
        ))
        
        conn.commit()
        screening.id = cursor.lastrowid
        return screening
    
    def get_by_id(self, screening_id, include_deleted=False):
        """دریافت غربالگری با شناسه"""
        query = "SELECT * FROM screenings WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (screening_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_screening(row)
        return None
    
    def get_by_student_profile(self, profile_id, include_deleted=False):
        """دریافت غربالگری‌های یک پرونده دانش‌آموز"""
        query = "SELECT * FROM screenings WHERE student_profile_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY execution_date DESC"
        
        cursor = self.db.execute_query(query, (profile_id,))
        rows = cursor.fetchall()
        return [self._row_to_screening(row) for row in rows]
    
    def get_by_tool(self, tool_name, include_deleted=False):
        """دریافت غربالگری‌های یک ابزار خاص"""
        query = "SELECT * FROM screenings WHERE tool_name = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY execution_date DESC"
        
        cursor = self.db.execute_query(query, (tool_name,))
        rows = cursor.fetchall()
        return [self._row_to_screening(row) for row in rows]
    
    def get_by_domain(self, domain, include_deleted=False):
        """دریافت غربالگری‌های یک حوزه خاص"""
        query = "SELECT * FROM screenings WHERE domain = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY execution_date DESC"
        
        cursor = self.db.execute_query(query, (domain,))
        rows = cursor.fetchall()
        return [self._row_to_screening(row) for row in rows]
    
    def get_completed(self, include_deleted=False):
        """دریافت غربالگری‌های تکمیل شده"""
        query = "SELECT * FROM screenings WHERE status = 'completed'"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY execution_date DESC"
        
        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        return [self._row_to_screening(row) for row in rows]
    
    def update(self, screening):
        """به‌روزرسانی غربالگری"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        domain_scores_json = json.dumps(screening.domain_scores, ensure_ascii=False) if screening.domain_scores else None
        
        cursor.execute("""
            UPDATE screenings SET
                student_profile_id = ?,
                staff_id = ?,
                tool_name = ?,
                tool_version = ?,
                execution_date = ?,
                execution_context = ?,
                domain_scores = ?,
                total_score = ?,
                domain = ?,
                sub_domain = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            screening.student_profile_id,
            screening.staff_id,
            screening.tool_name,
            screening.tool_version,
            screening.execution_date,
            screening.execution_context,
            domain_scores_json,
            screening.total_score,
            screening.domain,
            screening.sub_domain,
            screening.status,
            screening.id
        ))
        
        conn.commit()
        return screening
    
    def update_status(self, screening_id, new_status):
        """به‌روزرسانی وضعیت غربالگری"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE screenings SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (new_status, screening_id))
        
        conn.commit()
        return True
    
    def delete(self, screening_id, user_id=None):
        """حذف منطقی غربالگری"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM screenings WHERE id = ? AND is_deleted = 0",
            (screening_id,)
        )
        if not cursor.fetchone():
            return False
        
        from datetime import datetime
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE screenings SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, screening_id))
        
        conn.commit()
        return True
    
    def restore(self, screening_id, user_id=None):
        """بازیابی غربالگری حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE screenings SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (screening_id,))
        
        conn.commit()
        return True
    
    def _row_to_screening(self, row):
        """تبدیل ردیف دیتابیس به مدل Screening"""
        screening = Screening()
        screening.id = row['id']
        screening.student_profile_id = row['student_profile_id']
        screening.staff_id = row['staff_id']
        screening.tool_name = row['tool_name']
        screening.tool_version = row['tool_version']
        screening.execution_date = row['execution_date']
        screening.execution_context = row['execution_context']
        
        # تبدیل JSON به دیکشنری
        if row['domain_scores']:
            try:
                screening.domain_scores = json.loads(row['domain_scores'])
            except:
                screening.domain_scores = None
        else:
            screening.domain_scores = None
        
        screening.total_score = row['total_score']
        screening.domain = row['domain']
        screening.sub_domain = row['sub_domain']
        screening.status = row['status']
        screening.created_at = row['created_at']
        screening.updated_at = row['updated_at']
        screening.is_deleted = row['is_deleted']
        screening.deleted_at = row['deleted_at']
        screening.deleted_by = row['deleted_by']
        return screening