"""
لایه دسترسی به داده اهداف فردی
"""

import json
import sqlite3

from database.connection import DatabaseConnection
from models.individual_goal import IndividualGoal
from utils.logger import get_logger
from utils.security import AccessControl
from utils.time_utils import utc_now_iso

logger = get_logger(__name__)


class GoalDAL:
    """عملیات CRUD برای اهداف فردی"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, goal):
        """ایجاد هدف جدید"""
        # مرز Scope (دور نوزدهم — مرحلهٔ ۴، DD-6 + dd1_scope=add_scope_only؛
        # طبق DD-1 این موجودیت هنوز Permission‌ای ندارد، فقط Scope)
        AccessControl.require_profile_scope(
            goal.student_profile_id, action="GoalDAL.create")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        success_criteria_json = json.dumps(goal.success_criteria, ensure_ascii=False) if goal.success_criteria else None
        
        cursor.execute("""
            INSERT INTO individual_goals (
                student_profile_id, created_by, assigned_to,
                related_competency_id, related_intervention_id,
                title, description, domain, priority,
                success_criteria, target_date, start_date, end_date,
                progress_percent, progress_notes,
                status, result, achievement_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            goal.student_profile_id,
            goal.created_by,
            goal.assigned_to,
            goal.related_competency_id,
            goal.related_intervention_id,
            goal.title,
            goal.description,
            goal.domain,
            goal.priority,
            success_criteria_json,
            goal.target_date,
            goal.start_date,
            goal.end_date,
            goal.progress_percent,
            goal.progress_notes,
            goal.status,
            goal.result,
            goal.achievement_date
        ))
        
        self.db.commit()
        goal.id = cursor.lastrowid
        return goal
    
    def get_by_id(self, goal_id, include_deleted=False):
        """دریافت هدف با شناسه"""
        query = "SELECT * FROM individual_goals WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (goal_id,))
        row = cursor.fetchone()
        if row:
            goal = self._row_to_goal(row)
            # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۴؛ فقط Scope)
            AccessControl.require_profile_scope(
                goal.student_profile_id, action="GoalDAL.get_by_id")
            return goal
        return None
    
    def get_by_student_profile(self, profile_id, include_deleted=False):
        """دریافت اهداف یک پرونده دانش‌آموز"""
        query = "SELECT * FROM individual_goals WHERE student_profile_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY priority ASC, created_at DESC"
        
        cursor = self.db.execute_query(query, (profile_id,))
        rows = cursor.fetchall()
        return [self._row_to_goal(row) for row in rows]
    
    def get_by_status(self, status, include_deleted=False):
        """دریافت اهداف بر اساس وضعیت"""
        query = "SELECT * FROM individual_goals WHERE status = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(query, (status,))
        rows = cursor.fetchall()
        return [self._row_to_goal(row) for row in rows]
    
    def get_by_domain(self, domain, include_deleted=False):
        """دریافت اهداف بر اساس حوزه"""
        query = "SELECT * FROM individual_goals WHERE domain = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(query, (domain,))
        rows = cursor.fetchall()
        return [self._row_to_goal(row) for row in rows]
    
    def get_by_priority(self, priority, include_deleted=False):
        """دریافت اهداف بر اساس اولویت"""
        query = "SELECT * FROM individual_goals WHERE priority = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor = self.db.execute_query(query, (priority,))
        rows = cursor.fetchall()
        return [self._row_to_goal(row) for row in rows]
    
    def get_active_goals(self, profile_id, include_deleted=False):
        """دریافت اهداف فعال یک دانش‌آموز"""
        query = """
            SELECT * FROM individual_goals 
            WHERE student_profile_id = ? 
            AND status IN (?, ?)
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY priority ASC, created_at DESC"
        
        cursor = self.db.execute_query(
            query, 
            (profile_id, IndividualGoal.STATUS_ACTIVE, IndividualGoal.STATUS_IN_PROGRESS)
        )
        rows = cursor.fetchall()
        return [self._row_to_goal(row) for row in rows]
    
    def get_achieved_goals(self, profile_id, include_deleted=False):
        """دریافت اهداف محقق‌شده یک دانش‌آموز"""
        query = """
            SELECT * FROM individual_goals 
            WHERE student_profile_id = ? 
            AND status IN (?, ?)
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY achievement_date DESC"
        
        cursor = self.db.execute_query(
            query, 
            (profile_id, IndividualGoal.STATUS_ACHIEVED, IndividualGoal.STATUS_COMPLETED)
        )
        rows = cursor.fetchall()
        return [self._row_to_goal(row) for row in rows]
    
    def get_all(self, limit=None, include_deleted=False):
        """دریافت همه اهداف"""
        query = "SELECT * FROM individual_goals"
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        query += " ORDER BY created_at DESC"
        
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params if params else None)
        rows = cursor.fetchall()
        return [self._row_to_goal(row) for row in rows]
    
    def update(self, goal):
        """به‌روزرسانی هدف"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۴؛ فقط Scope)
        cursor.execute(
            "SELECT student_profile_id FROM individual_goals "
            "WHERE id = ? AND is_deleted = 0",
            (goal.id,)
        )
        existing = cursor.fetchone()
        if existing:
            AccessControl.require_profile_scope(
                existing["student_profile_id"], action="GoalDAL.update")
            if goal.student_profile_id != existing["student_profile_id"]:
                AccessControl.require_profile_scope(
                    goal.student_profile_id, action="GoalDAL.update(new_profile)")
        
        success_criteria_json = json.dumps(goal.success_criteria, ensure_ascii=False) if goal.success_criteria else None
        
        cursor.execute("""
            UPDATE individual_goals SET
                student_profile_id = ?,
                created_by = ?,
                assigned_to = ?,
                related_competency_id = ?,
                related_intervention_id = ?,
                title = ?,
                description = ?,
                domain = ?,
                priority = ?,
                success_criteria = ?,
                target_date = ?,
                start_date = ?,
                end_date = ?,
                progress_percent = ?,
                progress_notes = ?,
                status = ?,
                result = ?,
                achievement_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            goal.student_profile_id,
            goal.created_by,
            goal.assigned_to,
            goal.related_competency_id,
            goal.related_intervention_id,
            goal.title,
            goal.description,
            goal.domain,
            goal.priority,
            success_criteria_json,
            goal.target_date,
            goal.start_date,
            goal.end_date,
            goal.progress_percent,
            goal.progress_notes,
            goal.status,
            goal.result,
            goal.achievement_date,
            goal.id
        ))
        
        self.db.commit()
        return goal
    
    def update_progress(self, goal_id, progress_percent, notes=None):
        """به‌روزرسانی پیشرفت هدف"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        progress_percent = max(0, min(100, progress_percent))
        
        # تعیین وضعیت جدید بر اساس پیشرفت
        new_status = IndividualGoal.STATUS_IN_PROGRESS
        if progress_percent >= 100:
            new_status = IndividualGoal.STATUS_COMPLETED
        elif progress_percent == 0:
            new_status = IndividualGoal.STATUS_ACTIVE
        
        cursor.execute("""
            UPDATE individual_goals SET
                progress_percent = ?,
                progress_notes = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (progress_percent, notes, new_status, goal_id))
        
        self.db.commit()
        return True
    
    def update_status(self, goal_id, new_status):
        """به‌روزرسانی وضعیت هدف"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE individual_goals SET
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (new_status, goal_id))
        
        self.db.commit()
        return True
    
    def delete(self, goal_id, user_id=None):
        """حذف منطقی هدف"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT student_profile_id FROM individual_goals "
            "WHERE id = ? AND is_deleted = 0",
            (goal_id,)
        )
        existing = cursor.fetchone()
        if not existing:
            return False
        # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۴؛ فقط Scope)
        AccessControl.require_profile_scope(
            existing["student_profile_id"], action="GoalDAL.delete")
        
        now = utc_now_iso()
        cursor.execute("""
            UPDATE individual_goals SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, goal_id))
        
        self.db.commit()
        return True
    
    def restore(self, goal_id):
        """بازیابی هدف حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۴؛ فقط Scope)
        cursor.execute(
            "SELECT student_profile_id FROM individual_goals "
            "WHERE id = ? AND is_deleted = 1",
            (goal_id,)
        )
        existing = cursor.fetchone()
        if existing:
            AccessControl.require_profile_scope(
                existing["student_profile_id"], action="GoalDAL.restore")
        
        cursor.execute("""
            UPDATE individual_goals SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (goal_id,))
        
        updated = cursor.rowcount > 0
        self.db.commit()
        return updated

    def get_deleted(self, limit=None):
        """
        فهرست اهداف حذف‌شده (دور هفدهم — BUG-RESTORE-06)

        لازم برای مسیر بازیابی در UI؛ فقط رکوردهای `is_deleted = 1`.
        """
        query = ("SELECT * FROM individual_goals "
                 "WHERE is_deleted = 1 ORDER BY deleted_at DESC")
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.db.execute_query(query, tuple(params) if params else None)
        return [self._row_to_goal(row) for row in cursor.fetchall()]

    def get_goal_stats(self, profile_id):
        """دریافت آمار اهداف یک دانش‌آموز"""
        goals = self.get_by_student_profile(profile_id)
        
        total = len(goals)
        active = sum(1 for g in goals if g.is_active_goal)
        achieved = sum(1 for g in goals if g.is_achieved)
        abandoned = sum(1 for g in goals if g.status == IndividualGoal.STATUS_ABANDONED)
        
        # آمار بر اساس حوزه
        by_domain = {}
        for g in goals:
            domain_display = g.domain_display
            if domain_display not in by_domain:
                by_domain[domain_display] = 0
            by_domain[domain_display] += 1
        
        # میانگین پیشرفت
        avg_progress = sum(g.progress_percent for g in goals) / total if total > 0 else 0
        
        return {
            'total': total,
            'active': active,
            'achieved': achieved,
            'abandoned': abandoned,
            'avg_progress': round(avg_progress, 1),
            'by_domain': by_domain,
            'has_goals': total > 0
        }
    
    def _row_to_goal(self, row):
        """تبدیل ردیف دیتابیس به مدل IndividualGoal"""
        goal = IndividualGoal()
        goal.id = row['id']
        goal.student_profile_id = row['student_profile_id']
        goal.created_by = row['created_by']
        goal.assigned_to = row['assigned_to']
        goal.related_competency_id = row['related_competency_id']
        goal.related_intervention_id = row['related_intervention_id']
        goal.title = row['title']
        goal.description = row['description']
        goal.domain = row['domain']
        goal.priority = row['priority']
        
        if row['success_criteria']:
            try:
                goal.success_criteria = json.loads(row['success_criteria'])
            except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as _exc:
                logger.debug(f"خطای مدیریت‌شده در _row_to_goal (مسیر جایگزین): {_exc}")
                goal.success_criteria = None
        else:
            goal.success_criteria = None
        
        goal.target_date = row['target_date']
        goal.start_date = row['start_date']
        goal.end_date = row['end_date']
        goal.progress_percent = row['progress_percent'] or 0
        goal.progress_notes = row['progress_notes']
        goal.status = row['status']
        goal.result = row['result']
        goal.achievement_date = row['achievement_date']
        goal.created_at = row['created_at']
        goal.updated_at = row['updated_at']
        goal.is_deleted = row['is_deleted']
        goal.deleted_at = row['deleted_at']
        goal.deleted_by = row['deleted_by']
        
        return goal