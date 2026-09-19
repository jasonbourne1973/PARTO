"""
لایه دسترسی به داده مصاحبه والدین (ParentInterview)
"""

import json

from database.connection import DatabaseConnection
from models.parent_interview import ParentInterview  # این خط باید کار کند
from utils.time_utils import utc_now_iso


class ParentInterviewDAL:
    """عملیات CRUD برای مصاحبه والدین"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, interview):
        """ایجاد مصاحبه جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # تبدیل key_points به JSON
        key_points_json = json.dumps(interview.key_points, ensure_ascii=False) if interview.key_points else None
        
        cursor.execute("""
            INSERT INTO parent_interviews (
                student_profile_id, staff_id,
                interview_date, interview_method, interviewer_name,
                parent_name, parent_relation, parent_phone,
                topic, topic_category,
                summary, details, key_points,
                result, outcome_notes,
                next_action, next_action_date, next_action_by,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interview.student_profile_id,
            interview.staff_id,
            interview.interview_date,
            interview.interview_method,
            interview.interviewer_name,
            interview.parent_name,
            interview.parent_relation,
            interview.parent_phone,
            interview.topic,
            interview.topic_category,
            interview.summary,
            interview.details,
            key_points_json,
            interview.result,
            interview.outcome_notes,
            interview.next_action,
            interview.next_action_date,
            interview.next_action_by,
            interview.status
        ))
        
        conn.commit()
        interview.id = cursor.lastrowid
        return interview
    
    def get_by_id(self, interview_id, include_deleted=False):
        """دریافت مصاحبه با شناسه"""
        query = "SELECT * FROM parent_interviews WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (interview_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_interview(row)
        return None
    
    def get_by_student_profile(self, profile_id, include_deleted=False):
        """دریافت مصاحبه‌های یک پرونده دانش‌آموز"""
        query = "SELECT * FROM parent_interviews WHERE student_profile_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY interview_date DESC"
        
        cursor = self.db.execute_query(query, (profile_id,))
        rows = cursor.fetchall()
        return [self._row_to_interview(row) for row in rows]
    
    def get_by_status(self, status, include_deleted=False):
        """دریافت مصاحبه‌ها بر اساس وضعیت"""
        query = "SELECT * FROM parent_interviews WHERE status = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY interview_date DESC"
        
        cursor = self.db.execute_query(query, (status,))
        rows = cursor.fetchall()
        return [self._row_to_interview(row) for row in rows]
    
    def get_completed(self, include_deleted=False):
        """دریافت مصاحبه‌های انجام شده"""
        return self.get_by_status(ParentInterview.STATUS_COMPLETED, include_deleted)
    
    def get_scheduled(self, include_deleted=False):
        """دریافت مصاحبه‌های برنامه‌ریزی شده"""
        return self.get_by_status(ParentInterview.STATUS_SCHEDULED, include_deleted)
    
    def get_by_date_range(self, start_date, end_date, include_deleted=False):
        """دریافت مصاحبه‌ها در بازه زمانی مشخص"""
        query = """
            SELECT * FROM parent_interviews 
            WHERE interview_date BETWEEN ? AND ?
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY interview_date DESC"
        
        cursor = self.db.execute_query(query, (start_date, end_date))
        rows = cursor.fetchall()
        return [self._row_to_interview(row) for row in rows]
    
    def update(self, interview):
        """به‌روزرسانی مصاحبه"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        key_points_json = json.dumps(interview.key_points, ensure_ascii=False) if interview.key_points else None
        
        cursor.execute("""
            UPDATE parent_interviews SET
                student_profile_id = ?,
                staff_id = ?,
                interview_date = ?,
                interview_method = ?,
                interviewer_name = ?,
                parent_name = ?,
                parent_relation = ?,
                parent_phone = ?,
                topic = ?,
                topic_category = ?,
                summary = ?,
                details = ?,
                key_points = ?,
                result = ?,
                outcome_notes = ?,
                next_action = ?,
                next_action_date = ?,
                next_action_by = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            interview.student_profile_id,
            interview.staff_id,
            interview.interview_date,
            interview.interview_method,
            interview.interviewer_name,
            interview.parent_name,
            interview.parent_relation,
            interview.parent_phone,
            interview.topic,
            interview.topic_category,
            interview.summary,
            interview.details,
            key_points_json,
            interview.result,
            interview.outcome_notes,
            interview.next_action,
            interview.next_action_date,
            interview.next_action_by,
            interview.status,
            interview.id
        ))
        
        conn.commit()
        return interview
    
    def update_status(self, interview_id, new_status):
        """به‌روزرسانی وضعیت مصاحبه"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE parent_interviews SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (new_status, interview_id))
        
        conn.commit()
        return True
    
    def delete(self, interview_id, user_id=None):
        """حذف منطقی مصاحبه"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM parent_interviews WHERE id = ? AND is_deleted = 0",
            (interview_id,)
        )
        if not cursor.fetchone():
            return False
        
        now = utc_now_iso()
        cursor.execute("""
            UPDATE parent_interviews SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, interview_id))
        
        conn.commit()
        return True
    
    def restore(self, interview_id, user_id=None):
        """بازیابی مصاحبه حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE parent_interviews SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (interview_id,))
        
        conn.commit()
        return True
    
    def _row_to_interview(self, row):
        """تبدیل ردیف دیتابیس به مدل ParentInterview"""
        interview = ParentInterview()
        interview.id = row['id']
        interview.student_profile_id = row['student_profile_id']
        interview.staff_id = row['staff_id']
        interview.interview_date = row['interview_date']
        interview.interview_method = row['interview_method']
        interview.interviewer_name = row['interviewer_name']
        interview.parent_name = row['parent_name']
        interview.parent_relation = row['parent_relation']
        interview.parent_phone = row['parent_phone']
        interview.topic = row['topic']
        interview.topic_category = row['topic_category']
        interview.summary = row['summary']
        interview.details = row['details']
        
        # تبدیل JSON
        if row['key_points']:
            try:
                interview.key_points = json.loads(row['key_points'])
            except Exception:
                interview.key_points = None
        else:
            interview.key_points = None
        
        interview.result = row['result']
        interview.outcome_notes = row['outcome_notes']
        interview.next_action = row['next_action']
        interview.next_action_date = row['next_action_date']
        interview.next_action_by = row['next_action_by']
        interview.status = row['status']
        interview.created_at = row['created_at']
        interview.updated_at = row['updated_at']
        interview.is_deleted = row['is_deleted']
        interview.deleted_at = row['deleted_at']
        interview.deleted_by = row['deleted_by']
        return interview