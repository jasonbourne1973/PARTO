"""
لایه دسترسی به داده جلسات مشاوره
"""

import json
import sqlite3

from database.connection import DatabaseConnection
from models.counseling_session import CounselingSession
from utils.logger import get_logger
from utils.time_utils import utc_now_iso

logger = get_logger(__name__)


class CounselingSessionDAL:
    """عملیات CRUD برای جلسات مشاوره"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, session):
        """ایجاد جلسه مشاوره جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # تبدیل فیلدهای JSON
        goals_json = json.dumps(session.goals, ensure_ascii=False) if session.goals else None
        interventions_json = json.dumps(session.interventions_discussed, ensure_ascii=False) if session.interventions_discussed else None
        recommendations_json = json.dumps(session.recommendations, ensure_ascii=False) if session.recommendations else None
        homework_json = json.dumps(session.homework, ensure_ascii=False) if session.homework else None
        
        cursor.execute("""
            INSERT INTO counseling_sessions (
                student_profile_id, counselor_id, referred_by,
                session_date, session_time, duration_minutes,
                type, method, location,
                topic, goals, summary, details,
                interventions_discussed, recommendations, homework,
                outcome, follow_up_needed, next_session_date, next_session_notes,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.student_profile_id,
            session.counselor_id,
            session.referred_by,
            session.session_date,
            session.session_time,
            session.duration_minutes,
            session.type,
            session.method,
            session.location,
            session.topic,
            goals_json,
            session.summary,
            session.details,
            interventions_json,
            recommendations_json,
            homework_json,
            session.outcome,
            1 if session.follow_up_needed else 0,
            session.next_session_date,
            session.next_session_notes,
            session.status
        ))
        
        self.db.commit()
        session.id = cursor.lastrowid
        return session
    
    def get_by_id(self, session_id, include_deleted=False):
        """دریافت جلسه با شناسه"""
        query = "SELECT * FROM counseling_sessions WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (session_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_session(row)
        return None
    
    def get_by_student_profile(self, profile_id, include_deleted=False):
        """دریافت جلسات یک پرونده دانش‌آموز"""
        query = "SELECT * FROM counseling_sessions WHERE student_profile_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY session_date DESC, session_time DESC"
        
        cursor = self.db.execute_query(query, (profile_id,))
        rows = cursor.fetchall()
        return [self._row_to_session(row) for row in rows]
    
    def get_by_counselor(self, counselor_id, include_deleted=False):
        """دریافت جلسات یک مشاور"""
        query = "SELECT * FROM counseling_sessions WHERE counselor_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY session_date DESC, session_time DESC"
        
        cursor = self.db.execute_query(query, (counselor_id,))
        rows = cursor.fetchall()
        return [self._row_to_session(row) for row in rows]
    
    def get_by_status(self, status, include_deleted=False):
        """دریافت جلسات بر اساس وضعیت"""
        query = "SELECT * FROM counseling_sessions WHERE status = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY session_date DESC, session_time DESC"
        
        cursor = self.db.execute_query(query, (status,))
        rows = cursor.fetchall()
        return [self._row_to_session(row) for row in rows]
    
    def get_scheduled(self, include_deleted=False):
        """دریافت جلسات برنامه‌ریزی شده"""
        return self.get_by_status(CounselingSession.STATUS_SCHEDULED, include_deleted)
    
    def get_completed(self, include_deleted=False):
        """دریافت جلسات انجام شده"""
        return self.get_by_status(CounselingSession.STATUS_COMPLETED, include_deleted)
    
    def get_by_date_range(self, start_date, end_date, include_deleted=False):
        """دریافت جلسات در بازه زمانی مشخص"""
        query = """
            SELECT * FROM counseling_sessions 
            WHERE session_date BETWEEN ? AND ?
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY session_date DESC, session_time DESC"
        
        cursor = self.db.execute_query(query, (start_date, end_date))
        rows = cursor.fetchall()
        return [self._row_to_session(row) for row in rows]
    
    def get_upcoming_sessions(self, days=7, include_deleted=False):
        """دریافت جلسات آینده"""
        from datetime import timedelta

        import jdatetime

        # ===== اصلاح (بازرسی دوم) =====
        # اگر فراخوانی‌کننده صریحاً None بدهد (مثلاً از یک فیلد خالی UI یا
        # یک dict که کلیدش وجود ندارد) این خطا می‌آمد:
        #     TypeError: unsupported type for timedelta days component: NoneType
        # مقدار پیش‌فرض فقط وقتی استفاده می‌شود که آرگومان «داده نشود»،
        # پس None صریح از آن عبور می‌کرد. حالا به پیش‌فرض برمی‌گردیم.
        if not days:
            days = 7

        today = jdatetime.date.today()
        end_date = today + timedelta(days=days)
        today_str = f"{today.year}/{today.month:02d}/{today.day:02d}"
        end_date_str = f"{end_date.year}/{end_date.month:02d}/{end_date.day:02d}"
        
        query = """
            SELECT * FROM counseling_sessions 
            WHERE session_date BETWEEN ? AND ?
            AND status = ?
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY session_date ASC, session_time ASC"
        
        cursor = self.db.execute_query(
            query, 
            (today_str, end_date_str, CounselingSession.STATUS_SCHEDULED)
        )
        rows = cursor.fetchall()
        return [self._row_to_session(row) for row in rows]
    
    def get_all(self, limit=None, include_deleted=False):
        """دریافت همه جلسات"""
        query = "SELECT * FROM counseling_sessions"
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        query += " ORDER BY session_date DESC, session_time DESC"
        
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params if params else None)
        rows = cursor.fetchall()
        return [self._row_to_session(row) for row in rows]
    
    def update(self, session):
        """به‌روزرسانی جلسه"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        goals_json = json.dumps(session.goals, ensure_ascii=False) if session.goals else None
        interventions_json = json.dumps(session.interventions_discussed, ensure_ascii=False) if session.interventions_discussed else None
        recommendations_json = json.dumps(session.recommendations, ensure_ascii=False) if session.recommendations else None
        homework_json = json.dumps(session.homework, ensure_ascii=False) if session.homework else None
        
        cursor.execute("""
            UPDATE counseling_sessions SET
                student_profile_id = ?,
                counselor_id = ?,
                referred_by = ?,
                session_date = ?,
                session_time = ?,
                duration_minutes = ?,
                type = ?,
                method = ?,
                location = ?,
                topic = ?,
                goals = ?,
                summary = ?,
                details = ?,
                interventions_discussed = ?,
                recommendations = ?,
                homework = ?,
                outcome = ?,
                follow_up_needed = ?,
                next_session_date = ?,
                next_session_notes = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            session.student_profile_id,
            session.counselor_id,
            session.referred_by,
            session.session_date,
            session.session_time,
            session.duration_minutes,
            session.type,
            session.method,
            session.location,
            session.topic,
            goals_json,
            session.summary,
            session.details,
            interventions_json,
            recommendations_json,
            homework_json,
            session.outcome,
            1 if session.follow_up_needed else 0,
            session.next_session_date,
            session.next_session_notes,
            session.status,
            session.id
        ))
        
        self.db.commit()
        return session
    
    def update_status(self, session_id, new_status):
        """به‌روزرسانی وضعیت جلسه"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE counseling_sessions SET
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (new_status, session_id))
        
        self.db.commit()
        return True
    
    def delete(self, session_id, user_id=None):
        """حذف منطقی جلسه"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM counseling_sessions WHERE id = ? AND is_deleted = 0",
            (session_id,)
        )
        if not cursor.fetchone():
            return False
        
        now = utc_now_iso()
        cursor.execute("""
            UPDATE counseling_sessions SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, session_id))
        
        self.db.commit()
        return True
    
    def restore(self, session_id):
        """بازیابی جلسه حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE counseling_sessions SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (session_id,))
        
        updated = cursor.rowcount > 0
        self.db.commit()
        return updated

    def get_deleted(self, limit=None):
        """
        فهرست جلسات مشاورهٔ حذف‌شده (دور هفدهم — BUG-RESTORE-07)

        لازم برای مسیر بازیابی در UI؛ فقط رکوردهای `is_deleted = 1`.
        """
        query = ("SELECT * FROM counseling_sessions "
                 "WHERE is_deleted = 1 ORDER BY deleted_at DESC")
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.db.execute_query(query, tuple(params) if params else None)
        return [self._row_to_session(row) for row in cursor.fetchall()]

    def get_session_stats(self, profile_id):
        """دریافت آمار جلسات یک دانش‌آموز"""
        sessions = self.get_by_student_profile(profile_id)
        
        total = len(sessions)
        completed = sum(1 for s in sessions if s.status == CounselingSession.STATUS_COMPLETED)
        scheduled = sum(1 for s in sessions if s.status == CounselingSession.STATUS_SCHEDULED)
        cancelled = sum(1 for s in sessions if s.status == CounselingSession.STATUS_CANCELLED)
        
        return {
            'total': total,
            'completed': completed,
            'scheduled': scheduled,
            'cancelled': cancelled,
            'has_sessions': total > 0
        }
    
    def _row_to_session(self, row):
        """تبدیل ردیف دیتابیس به مدل CounselingSession"""
        session = CounselingSession()
        session.id = row['id']
        session.student_profile_id = row['student_profile_id']
        session.counselor_id = row['counselor_id']
        session.referred_by = row['referred_by']
        session.session_date = row['session_date']
        session.session_time = row['session_time']
        session.duration_minutes = row['duration_minutes']
        session.type = row['type']
        session.method = row['method']
        session.location = row['location']
        session.topic = row['topic']
        
        # تبدیل JSON
        if row['goals']:
            try:
                session.goals = json.loads(row['goals'])
            except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as _exc:
                logger.debug(f"خطای مدیریت‌شده در _row_to_session (مسیر جایگزین): {_exc}")
                session.goals = None
        else:
            session.goals = None
        
        session.summary = row['summary']
        session.details = row['details']
        
        if row['interventions_discussed']:
            try:
                session.interventions_discussed = json.loads(row['interventions_discussed'])
            except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as _exc:
                logger.debug(f"خطای مدیریت‌شده در _row_to_session (مسیر جایگزین): {_exc}")
                session.interventions_discussed = None
        else:
            session.interventions_discussed = None
        
        if row['recommendations']:
            try:
                session.recommendations = json.loads(row['recommendations'])
            except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as _exc:
                logger.debug(f"خطای مدیریت‌شده در _row_to_session (مسیر جایگزین): {_exc}")
                session.recommendations = None
        else:
            session.recommendations = None
        
        if row['homework']:
            try:
                session.homework = json.loads(row['homework'])
            except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as _exc:
                logger.debug(f"خطای مدیریت‌شده در _row_to_session (مسیر جایگزین): {_exc}")
                session.homework = None
        else:
            session.homework = None
        
        session.outcome = row['outcome']
        session.follow_up_needed = bool(row['follow_up_needed'])
        session.next_session_date = row['next_session_date']
        session.next_session_notes = row['next_session_notes']
        session.status = row['status']
        session.created_at = row['created_at']
        session.updated_at = row['updated_at']
        session.is_deleted = row['is_deleted']
        session.deleted_at = row['deleted_at']
        session.deleted_by = row['deleted_by']
        
        return session