"""
لایه دسترسی به داده تفسیر تخصصی (ProfessionalInterpretation)
"""

from database.connection import DatabaseConnection
from models.professional_interpretation import ProfessionalInterpretation
import json


class ProfessionalInterpretationDAL:
    """عملیات CRUD برای تفسیر تخصصی"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, interpretation):
        """ایجاد تفسیر تخصصی جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # تبدیل JSON
        recommendations_json = json.dumps(interpretation.recommendations, ensure_ascii=False) if interpretation.recommendations else None
        next_steps_json = json.dumps(interpretation.next_steps, ensure_ascii=False) if interpretation.next_steps else None
        
        cursor.execute("""
            INSERT INTO professional_interpretations (
                student_profile_id, staff_id,
                observation_id, screening_id,
                level, domain,
                title, summary, detailed_text,
                recommendations, next_steps,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interpretation.student_profile_id,
            interpretation.staff_id,
            interpretation.observation_id,
            interpretation.screening_id,
            interpretation.level,
            interpretation.domain,
            interpretation.title,
            interpretation.summary,
            interpretation.detailed_text,
            recommendations_json,
            next_steps_json,
            interpretation.status
        ))
        
        conn.commit()
        interpretation.id = cursor.lastrowid
        return interpretation
    
    def get_by_id(self, interpretation_id, include_deleted=False):
        """دریافت تفسیر با شناسه"""
        query = "SELECT * FROM professional_interpretations WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (interpretation_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_interpretation(row)
        return None
    
    def get_by_student_profile(self, profile_id, include_deleted=False):
        """دریافت تفسیرهای یک پرونده دانش‌آموز"""
        query = "SELECT * FROM professional_interpretations WHERE student_profile_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(query, (profile_id,))
        rows = cursor.fetchall()
        return [self._row_to_interpretation(row) for row in rows]
    
    def get_by_observation(self, observation_id, include_deleted=False):
        """دریافت تفسیرهای یک مشاهده"""
        query = "SELECT * FROM professional_interpretations WHERE observation_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(query, (observation_id,))
        rows = cursor.fetchall()
        return [self._row_to_interpretation(row) for row in rows]
    
    def get_by_screening(self, screening_id, include_deleted=False):
        """دریافت تفسیرهای یک غربالگری"""
        query = "SELECT * FROM professional_interpretations WHERE screening_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(query, (screening_id,))
        rows = cursor.fetchall()
        return [self._row_to_interpretation(row) for row in rows]
    
    def get_by_level(self, level, include_deleted=False):
        """دریافت تفسیرهای یک سطح خاص"""
        query = "SELECT * FROM professional_interpretations WHERE level = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(query, (level,))
        rows = cursor.fetchall()
        return [self._row_to_interpretation(row) for row in rows]
    
    def get_final(self, include_deleted=False):
        """دریافت تفسیرهای نهایی"""
        query = "SELECT * FROM professional_interpretations WHERE status = 'final'"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        return [self._row_to_interpretation(row) for row in rows]
    
    def update(self, interpretation):
        """به‌روزرسانی تفسیر تخصصی"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        recommendations_json = json.dumps(interpretation.recommendations, ensure_ascii=False) if interpretation.recommendations else None
        next_steps_json = json.dumps(interpretation.next_steps, ensure_ascii=False) if interpretation.next_steps else None
        
        cursor.execute("""
            UPDATE professional_interpretations SET
                student_profile_id = ?,
                staff_id = ?,
                observation_id = ?,
                screening_id = ?,
                level = ?,
                domain = ?,
                title = ?,
                summary = ?,
                detailed_text = ?,
                recommendations = ?,
                next_steps = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            interpretation.student_profile_id,
            interpretation.staff_id,
            interpretation.observation_id,
            interpretation.screening_id,
            interpretation.level,
            interpretation.domain,
            interpretation.title,
            interpretation.summary,
            interpretation.detailed_text,
            recommendations_json,
            next_steps_json,
            interpretation.status,
            interpretation.id
        ))
        
        conn.commit()
        return interpretation
    
    def update_status(self, interpretation_id, new_status):
        """به‌روزرسانی وضعیت تفسیر"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE professional_interpretations SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (new_status, interpretation_id))
        
        conn.commit()
        return True
    
    def delete(self, interpretation_id, user_id=None):
        """حذف منطقی تفسیر تخصصی"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM professional_interpretations WHERE id = ? AND is_deleted = 0",
            (interpretation_id,)
        )
        if not cursor.fetchone():
            return False
        
        from datetime import datetime
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE professional_interpretations SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, interpretation_id))
        
        conn.commit()
        return True
    
    def restore(self, interpretation_id, user_id=None):
        """بازیابی تفسیر حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE professional_interpretations SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (interpretation_id,))
        
        conn.commit()
        return True
    
    def _row_to_interpretation(self, row):
        """تبدیل ردیف دیتابیس به مدل ProfessionalInterpretation"""
        interpretation = ProfessionalInterpretation()
        interpretation.id = row['id']
        interpretation.student_profile_id = row['student_profile_id']
        interpretation.staff_id = row['staff_id']
        interpretation.observation_id = row['observation_id']
        interpretation.screening_id = row['screening_id']
        interpretation.level = row['level']
        interpretation.domain = row['domain']
        interpretation.title = row['title']
        interpretation.summary = row['summary']
        interpretation.detailed_text = row['detailed_text']
        
        # تبدیل JSON
        if row['recommendations']:
            try:
                interpretation.recommendations = json.loads(row['recommendations'])
            except:
                interpretation.recommendations = None
        else:
            interpretation.recommendations = None
        
        if row['next_steps']:
            try:
                interpretation.next_steps = json.loads(row['next_steps'])
            except:
                interpretation.next_steps = None
        else:
            interpretation.next_steps = None
        
        interpretation.status = row['status']
        interpretation.created_at = row['created_at']
        interpretation.updated_at = row['updated_at']
        interpretation.is_deleted = row['is_deleted']
        interpretation.deleted_at = row['deleted_at']
        interpretation.deleted_by = row['deleted_by']
        return interpretation