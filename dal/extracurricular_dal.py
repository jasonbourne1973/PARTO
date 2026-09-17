"""
لایه دسترسی به داده فعالیت‌های فوق‌برنامه
"""

from database.connection import DatabaseConnection
from models.extracurricular_activity import ExtracurricularActivity
import json


class ExtracurricularDAL:
    """عملیات CRUD برای فعالیت‌های فوق‌برنامه"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, activity):
        """ایجاد فعالیت جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        achievements_json = json.dumps(activity.achievements, ensure_ascii=False) if activity.achievements else None
        
        cursor.execute("""
            INSERT INTO extracurricular_activities (
                student_profile_id, teacher_id,
                title, type, description,
                start_date, end_date, duration_hours,
                location, participation_level, role, team_name,
                result, achievements, feedback,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            activity.student_profile_id,
            activity.teacher_id,
            activity.title,
            activity.type,
            activity.description,
            activity.start_date,
            activity.end_date,
            activity.duration_hours,
            activity.location,
            activity.participation_level,
            activity.role,
            activity.team_name,
            activity.result,
            achievements_json,
            activity.feedback,
            activity.status
        ))
        
        conn.commit()
        activity.id = cursor.lastrowid
        return activity
    
    def get_by_id(self, activity_id, include_deleted=False):
        """دریافت فعالیت با شناسه"""
        query = "SELECT * FROM extracurricular_activities WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (activity_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_activity(row)
        return None
    
    def get_by_student_profile(self, profile_id, include_deleted=False):
        """دریافت فعالیت‌های یک پرونده دانش‌آموز"""
        query = "SELECT * FROM extracurricular_activities WHERE student_profile_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY start_date DESC"
        
        cursor = self.db.execute_query(query, (profile_id,))
        rows = cursor.fetchall()
        return [self._row_to_activity(row) for row in rows]
    
    def get_by_type(self, activity_type, include_deleted=False):
        """دریافت فعالیت‌ها بر اساس نوع"""
        query = "SELECT * FROM extracurricular_activities WHERE type = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY start_date DESC"
        
        cursor = self.db.execute_query(query, (activity_type,))
        rows = cursor.fetchall()
        return [self._row_to_activity(row) for row in rows]
    
    def get_by_teacher(self, teacher_id, include_deleted=False):
        """دریافت فعالیت‌های یک معلم"""
        query = "SELECT * FROM extracurricular_activities WHERE teacher_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY start_date DESC"
        
        cursor = self.db.execute_query(query, (teacher_id,))
        rows = cursor.fetchall()
        return [self._row_to_activity(row) for row in rows]
    
    def get_by_status(self, status, include_deleted=False):
        """دریافت فعالیت‌ها بر اساس وضعیت"""
        query = "SELECT * FROM extracurricular_activities WHERE status = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY start_date DESC"
        
        cursor = self.db.execute_query(query, (status,))
        rows = cursor.fetchall()
        return [self._row_to_activity(row) for row in rows]
    
    def get_by_date_range(self, start_date, end_date, include_deleted=False):
        """دریافت فعالیت‌ها در بازه زمانی مشخص"""
        query = """
            SELECT * FROM extracurricular_activities 
            WHERE start_date BETWEEN ? AND ?
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY start_date DESC"
        
        cursor = self.db.execute_query(query, (start_date, end_date))
        rows = cursor.fetchall()
        return [self._row_to_activity(row) for row in rows]
    
    def get_all(self, limit=None, include_deleted=False):
        """دریافت همه فعالیت‌ها"""
        query = "SELECT * FROM extracurricular_activities"
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        query += " ORDER BY start_date DESC"
        
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params if params else None)
        rows = cursor.fetchall()
        return [self._row_to_activity(row) for row in rows]
    
    def update(self, activity):
        """به‌روزرسانی فعالیت"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        achievements_json = json.dumps(activity.achievements, ensure_ascii=False) if activity.achievements else None
        
        cursor.execute("""
            UPDATE extracurricular_activities SET
                student_profile_id = ?,
                teacher_id = ?,
                title = ?,
                type = ?,
                description = ?,
                start_date = ?,
                end_date = ?,
                duration_hours = ?,
                location = ?,
                participation_level = ?,
                role = ?,
                team_name = ?,
                result = ?,
                achievements = ?,
                feedback = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            activity.student_profile_id,
            activity.teacher_id,
            activity.title,
            activity.type,
            activity.description,
            activity.start_date,
            activity.end_date,
            activity.duration_hours,
            activity.location,
            activity.participation_level,
            activity.role,
            activity.team_name,
            activity.result,
            achievements_json,
            activity.feedback,
            activity.status,
            activity.id
        ))
        
        conn.commit()
        return activity
    
    def update_status(self, activity_id, new_status):
        """به‌روزرسانی وضعیت فعالیت"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE extracurricular_activities SET
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (new_status, activity_id))
        
        conn.commit()
        return True
    
    def delete(self, activity_id, user_id=None):
        """حذف منطقی فعالیت"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM extracurricular_activities WHERE id = ? AND is_deleted = 0",
            (activity_id,)
        )
        if not cursor.fetchone():
            return False
        
        from datetime import datetime
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE extracurricular_activities SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, activity_id))
        
        conn.commit()
        return True
    
    def restore(self, activity_id):
        """بازیابی فعالیت حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE extracurricular_activities SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (activity_id,))
        
        conn.commit()
        return True
    
    def get_activity_stats(self, profile_id):
        """دریافت آمار فعالیت‌های یک دانش‌آموز"""
        activities = self.get_by_student_profile(profile_id)
        
        total = len(activities)
        completed = sum(1 for a in activities if a.status == ExtracurricularActivity.STATUS_COMPLETED)
        planned = sum(1 for a in activities if a.status == ExtracurricularActivity.STATUS_PLANNED)
        in_progress = sum(1 for a in activities if a.status == ExtracurricularActivity.STATUS_IN_PROGRESS)
        
        # آمار بر اساس نوع
        by_type = {}
        for a in activities:
            type_display = a.type_display
            if type_display not in by_type:
                by_type[type_display] = 0
            by_type[type_display] += 1
        
        return {
            'total': total,
            'completed': completed,
            'planned': planned,
            'in_progress': in_progress,
            'by_type': by_type,
            'has_activities': total > 0
        }
    
    def _row_to_activity(self, row):
        """تبدیل ردیف دیتابیس به مدل ExtracurricularActivity"""
        activity = ExtracurricularActivity()
        activity.id = row['id']
        activity.student_profile_id = row['student_profile_id']
        activity.teacher_id = row['teacher_id']
        activity.title = row['title']
        activity.type = row['type']
        activity.description = row['description']
        activity.start_date = row['start_date']
        activity.end_date = row['end_date']
        activity.duration_hours = row['duration_hours']
        activity.location = row['location']
        activity.participation_level = row['participation_level']
        activity.role = row['role']
        activity.team_name = row['team_name']
        activity.result = row['result']
        
        if row['achievements']:
            try:
                activity.achievements = json.loads(row['achievements'])
            except:
                activity.achievements = None
        else:
            activity.achievements = None
        
        activity.feedback = row['feedback']
        activity.status = row['status']
        activity.created_at = row['created_at']
        activity.updated_at = row['updated_at']
        activity.is_deleted = row['is_deleted']
        activity.deleted_at = row['deleted_at']
        activity.deleted_by = row['deleted_by']
        
        return activity