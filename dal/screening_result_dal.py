"""
لایه دسترسی به داده نتایج غربالگری (ScreeningResult)
"""

from database.connection import DatabaseConnection
from models.screening_result import ScreeningResult
import json


class ScreeningResultDAL:
    """عملیات CRUD برای نتایج غربالگری"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, result):
        """ایجاد نتیجه غربالگری جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # تبدیل فیلدهای JSON
        raw_answers_json = json.dumps(result.raw_answers, ensure_ascii=False) if result.raw_answers else None
        raw_observations_json = json.dumps(result.raw_observations, ensure_ascii=False) if result.raw_observations else None
        domain_scores_json = json.dumps(result.domain_scores, ensure_ascii=False) if result.domain_scores else None
        
        cursor.execute("""
            INSERT INTO screening_results (
                student_profile_id, staff_id, tool_id,
                execution_date, execution_context,
                raw_answers, raw_observations,
                domain_scores, total_score,
                notes, duration_minutes,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.student_profile_id,
            result.staff_id,
            result.tool_id,
            result.execution_date,
            result.execution_context,
            raw_answers_json,
            raw_observations_json,
            domain_scores_json,
            result.total_score,
            result.notes,
            result.duration_minutes,
            result.status
        ))
        
        conn.commit()
        result.id = cursor.lastrowid
        return result
    
    def get_by_id(self, result_id, include_deleted=False):
        """دریافت نتیجه با شناسه"""
        query = "SELECT * FROM screening_results WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (result_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_result(row)
        return None
    
    def get_by_student_profile(self, profile_id, include_deleted=False):
        """دریافت نتایج یک پرونده دانش‌آموز"""
        query = "SELECT * FROM screening_results WHERE student_profile_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY execution_date DESC"
        
        cursor = self.db.execute_query(query, (profile_id,))
        rows = cursor.fetchall()
        return [self._row_to_result(row) for row in rows]
    
    def get_by_tool(self, tool_id, include_deleted=False):
        """دریافت نتایج یک ابزار خاص"""
        query = "SELECT * FROM screening_results WHERE tool_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY execution_date DESC"
        
        cursor = self.db.execute_query(query, (tool_id,))
        rows = cursor.fetchall()
        return [self._row_to_result(row) for row in rows]
    
    def get_completed(self, include_deleted=False):
        """دریافت نتایج تکمیل شده"""
        query = "SELECT * FROM screening_results WHERE status = 'completed'"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY execution_date DESC"
        
        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        return [self._row_to_result(row) for row in rows]
    
    def get_by_date_range(self, start_date, end_date, include_deleted=False):
        """دریافت نتایج در بازه زمانی مشخص"""
        query = """
            SELECT * FROM screening_results 
            WHERE execution_date BETWEEN ? AND ?
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY execution_date DESC"
        
        cursor = self.db.execute_query(query, (start_date, end_date))
        rows = cursor.fetchall()
        return [self._row_to_result(row) for row in rows]
    
    def update(self, result):
        """به‌روزرسانی نتیجه غربالگری"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        raw_answers_json = json.dumps(result.raw_answers, ensure_ascii=False) if result.raw_answers else None
        raw_observations_json = json.dumps(result.raw_observations, ensure_ascii=False) if result.raw_observations else None
        domain_scores_json = json.dumps(result.domain_scores, ensure_ascii=False) if result.domain_scores else None
        
        cursor.execute("""
            UPDATE screening_results SET
                student_profile_id = ?,
                staff_id = ?,
                tool_id = ?,
                execution_date = ?,
                execution_context = ?,
                raw_answers = ?,
                raw_observations = ?,
                domain_scores = ?,
                total_score = ?,
                notes = ?,
                duration_minutes = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            result.student_profile_id,
            result.staff_id,
            result.tool_id,
            result.execution_date,
            result.execution_context,
            raw_answers_json,
            raw_observations_json,
            domain_scores_json,
            result.total_score,
            result.notes,
            result.duration_minutes,
            result.status,
            result.id
        ))
        
        conn.commit()
        return result
    
    def update_status(self, result_id, new_status):
        """به‌روزرسانی وضعیت نتیجه"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE screening_results SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (new_status, result_id))
        
        conn.commit()
        return True
    
    def delete(self, result_id, user_id=None):
        """حذف منطقی نتیجه"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM screening_results WHERE id = ? AND is_deleted = 0",
            (result_id,)
        )
        if not cursor.fetchone():
            return False
        
        from datetime import datetime
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE screening_results SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, result_id))
        
        conn.commit()
        return True
    
    def restore(self, result_id, user_id=None):
        """بازیابی نتیجه حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE screening_results SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (result_id,))
        
        conn.commit()
        return True
    
    def _row_to_result(self, row):
        """تبدیل ردیف دیتابیس به مدل ScreeningResult"""
        result = ScreeningResult()
        result.id = row['id']
        result.student_profile_id = row['student_profile_id']
        result.staff_id = row['staff_id']
        result.tool_id = row['tool_id']
        result.execution_date = row['execution_date']
        result.execution_context = row['execution_context']
        
        # تبدیل JSON
        if row['raw_answers']:
            try:
                result.raw_answers = json.loads(row['raw_answers'])
            except:
                result.raw_answers = None
        else:
            result.raw_answers = None
        
        if row['raw_observations']:
            try:
                result.raw_observations = json.loads(row['raw_observations'])
            except:
                result.raw_observations = None
        else:
            result.raw_observations = None
        
        if row['domain_scores']:
            try:
                result.domain_scores = json.loads(row['domain_scores'])
            except:
                result.domain_scores = None
        else:
            result.domain_scores = None
        
        result.total_score = row['total_score']
        result.notes = row['notes']
        result.duration_minutes = row['duration_minutes']
        result.status = row['status']
        result.created_at = row['created_at']
        result.updated_at = row['updated_at']
        result.is_deleted = row['is_deleted']
        result.deleted_at = row['deleted_at']
        result.deleted_by = row['deleted_by']
        return result