"""
لایه دسترسی به داده پیشنهادات (Recommendation)
"""

from database.connection import DatabaseConnection
from models.recommendation import Recommendation
import json
from datetime import datetime


class RecommendationDAL:
    """عملیات CRUD برای پیشنهادات"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, recommendation):
        """ایجاد پیشنهاد جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # تبدیل فیلدهای JSON
        related_obs_ids_json = json.dumps(recommendation.related_observation_ids) if recommendation.related_observation_ids else None
        metadata_json = json.dumps(recommendation.metadata, ensure_ascii=False) if recommendation.metadata else None
        
        cursor.execute("""
            INSERT INTO recommendations (
                student_profile_id, staff_id, rule_id, category, priority,
                title, description, suggested_action, suggested_intervention_type,
                related_competency_id, related_observation_ids, score, metadata,
                status, implemented_at, completed_at, feedback, feedback_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recommendation.student_profile_id,
            recommendation.staff_id,
            recommendation.rule_id,
            recommendation.category,
            recommendation.priority,
            recommendation.title,
            recommendation.description,
            recommendation.suggested_action,
            recommendation.suggested_intervention_type,
            recommendation.related_competency_id,
            related_obs_ids_json,
            recommendation.score,
            metadata_json,
            recommendation.status,
            recommendation.implemented_at,
            recommendation.completed_at,
            recommendation.feedback,
            recommendation.feedback_notes
        ))
        
        conn.commit()
        recommendation.id = cursor.lastrowid
        return recommendation
    
    def get_by_id(self, recommendation_id, include_deleted=False):
        """دریافت پیشنهاد با شناسه"""
        query = "SELECT * FROM recommendations WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (recommendation_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_recommendation(row)
        return None
    
    def get_by_student_profile(self, profile_id, include_deleted=False):
        """دریافت پیشنهادهای یک پرونده دانش‌آموز"""
        query = "SELECT * FROM recommendations WHERE student_profile_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(query, (profile_id,))
        rows = cursor.fetchall()
        return [self._row_to_recommendation(row) for row in rows]
    
    def get_by_staff(self, staff_id, include_deleted=False):
        """دریافت پیشنهادهای یک مسئول"""
        query = "SELECT * FROM recommendations WHERE staff_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(query, (staff_id,))
        rows = cursor.fetchall()
        return [self._row_to_recommendation(row) for row in rows]
    
    def get_by_status(self, status, include_deleted=False):
        """دریافت پیشنهادها بر اساس وضعیت"""
        query = "SELECT * FROM recommendations WHERE status = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(query, (status,))
        rows = cursor.fetchall()
        return [self._row_to_recommendation(row) for row in rows]
    
    def get_pending(self, include_deleted=False):
        """دریافت پیشنهادهای در انتظار"""
        return self.get_by_status(Recommendation.STATUS_PENDING, include_deleted)
    
    def get_active(self, include_deleted=False):
        """دریافت پیشنهادهای فعال (در انتظار یا پذیرفته شده)"""
        query = """
            SELECT * FROM recommendations 
            WHERE status IN (?, ?)
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(
            query, 
            (Recommendation.STATUS_PENDING, Recommendation.STATUS_ACCEPTED)
        )
        rows = cursor.fetchall()
        return [self._row_to_recommendation(row) for row in rows]
    
    def get_implemented(self, include_deleted=False):
        """دریافت پیشنهادهای اجرا شده"""
        return self.get_by_status(Recommendation.STATUS_IMPLEMENTED, include_deleted)
    
    def get_completed(self, include_deleted=False):
        """دریافت پیشنهادهای تکمیل شده"""
        return self.get_by_status(Recommendation.STATUS_COMPLETED, include_deleted)
    
    def get_all(self, limit=None, include_deleted=False):
        """دریافت همه پیشنهادها"""
        query = "SELECT * FROM recommendations"
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params if params else None)
        rows = cursor.fetchall()
        return [self._row_to_recommendation(row) for row in rows]
    
    def update(self, recommendation):
        """به‌روزرسانی پیشنهاد"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        related_obs_ids_json = json.dumps(recommendation.related_observation_ids) if recommendation.related_observation_ids else None
        metadata_json = json.dumps(recommendation.metadata, ensure_ascii=False) if recommendation.metadata else None
        
        cursor.execute("""
            UPDATE recommendations SET
                student_profile_id = ?,
                staff_id = ?,
                rule_id = ?,
                category = ?,
                priority = ?,
                title = ?,
                description = ?,
                suggested_action = ?,
                suggested_intervention_type = ?,
                related_competency_id = ?,
                related_observation_ids = ?,
                score = ?,
                metadata = ?,
                status = ?,
                implemented_at = ?,
                completed_at = ?,
                feedback = ?,
                feedback_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            recommendation.student_profile_id,
            recommendation.staff_id,
            recommendation.rule_id,
            recommendation.category,
            recommendation.priority,
            recommendation.title,
            recommendation.description,
            recommendation.suggested_action,
            recommendation.suggested_intervention_type,
            recommendation.related_competency_id,
            related_obs_ids_json,
            recommendation.score,
            metadata_json,
            recommendation.status,
            recommendation.implemented_at,
            recommendation.completed_at,
            recommendation.feedback,
            recommendation.feedback_notes,
            recommendation.id
        ))
        
        conn.commit()
        return recommendation
    
    def update_status(self, recommendation_id, new_status, feedback=None, notes=None):
        """به‌روزرسانی وضعیت پیشنهاد"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        query = """
            UPDATE recommendations SET
                status = ?,
                updated_at = CURRENT_TIMESTAMP
        """
        params = [new_status]
        
        if feedback is not None:
            query += ", feedback = ?"
            params.append(feedback)
        if notes is not None:
            query += ", feedback_notes = ?"
            params.append(notes)
        
        if new_status == Recommendation.STATUS_IMPLEMENTED:
            query += ", implemented_at = ?"
            params.append(now)
        elif new_status == Recommendation.STATUS_COMPLETED:
            query += ", completed_at = ?"
            params.append(now)
        
        query += " WHERE id = ? AND is_deleted = 0"
        params.append(recommendation_id)
        
        cursor.execute(query, params)
        conn.commit()
        return True
    
    def delete(self, recommendation_id, user_id=None):
        """حذف منطقی پیشنهاد"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM recommendations WHERE id = ? AND is_deleted = 0",
            (recommendation_id,)
        )
        if not cursor.fetchone():
            return False
        
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE recommendations SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, recommendation_id))
        
        conn.commit()
        return True
    
    def restore(self, recommendation_id):
        """بازیابی پیشنهاد حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE recommendations SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (recommendation_id,))
        
        conn.commit()
        return True
    
    def get_count_by_student(self, profile_id, status=None):
        """دریافت تعداد پیشنهادهای یک دانش‌آموز"""
        query = "SELECT COUNT(*) as count FROM recommendations WHERE student_profile_id = ?"
        params = [profile_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, params)
        row = cursor.fetchone()
        return row['count'] if row else 0
    
    def get_recommendation_stats(self, start_date=None, end_date=None):
        """دریافت آمار پیشنهادها"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN status IN ('implemented', 'completed') THEN 1 ELSE 0 END) as implemented,
                    SUM(CASE WHEN priority = 'critical' THEN 1 ELSE 0 END) as critical,
                    SUM(CASE WHEN priority = 'high' THEN 1 ELSE 0 END) as high
                FROM recommendations
                WHERE is_deleted = 0
            """
            params = []
            
            if start_date:
                query += " AND created_at >= ?"
                params.append(start_date)
            if end_date:
                query += " AND created_at <= ?"
                params.append(end_date)
            
            cursor.execute(query, tuple(params))  # اصلاح: None می‌داد «parameters are of unsupported type»
            row = cursor.fetchone()
            
            return {
                'total': row['total'] if row else 0,
                'pending': row['pending'] if row else 0,
                'accepted': row['accepted'] if row else 0,
                'rejected': row['rejected'] if row else 0,
                'implemented': row['implemented'] if row else 0,
                'critical': row['critical'] if row else 0,
                'high': row['high'] if row else 0
            }
            
        except Exception as e:
            print(f"خطا در دریافت آمار پیشنهادها: {e}")
            return {'total': 0, 'pending': 0, 'accepted': 0, 'rejected': 0, 'implemented': 0, 'critical': 0, 'high': 0}
    
    def _row_to_recommendation(self, row):
        """تبدیل ردیف دیتابیس به مدل Recommendation"""
        recommendation = Recommendation()
        recommendation.id = row['id']
        recommendation.student_profile_id = row['student_profile_id']
        recommendation.staff_id = row['staff_id']
        recommendation.rule_id = row['rule_id']
        recommendation.category = row['category']
        recommendation.priority = row['priority']
        recommendation.title = row['title']
        recommendation.description = row['description']
        recommendation.suggested_action = row['suggested_action']
        recommendation.suggested_intervention_type = row['suggested_intervention_type']
        recommendation.related_competency_id = row['related_competency_id']
        
        # تبدیل JSON
        if row['related_observation_ids']:
            try:
                recommendation.related_observation_ids = json.loads(row['related_observation_ids'])
            except Exception:
                recommendation.related_observation_ids = None
        else:
            recommendation.related_observation_ids = None
        
        recommendation.score = row['score']
        
        if row['metadata']:
            try:
                recommendation.metadata = json.loads(row['metadata'])
            except Exception:
                recommendation.metadata = None
        else:
            recommendation.metadata = None
        
        recommendation.status = row['status']
        recommendation.implemented_at = row['implemented_at']
        recommendation.completed_at = row['completed_at']
        recommendation.feedback = row['feedback']
        recommendation.feedback_notes = row['feedback_notes']
        recommendation.created_at = row['created_at']
        recommendation.updated_at = row['updated_at']
        recommendation.is_deleted = row['is_deleted']
        recommendation.deleted_at = row['deleted_at']
        recommendation.deleted_by = row['deleted_by']
        
        return recommendation