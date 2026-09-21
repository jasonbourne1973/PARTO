"""
لایه دسترسی به داده اطلاعات زمینه‌ای خانواده (FamilyContext)
"""

from database.connection import DatabaseConnection
from models.family_context import FamilyContext
from utils.time_utils import utc_now_iso


class FamilyContextDAL:
    """عملیات CRUD برای اطلاعات زمینه‌ای خانواده"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, family_context):
        """ایجاد اطلاعات زمینه‌ای خانواده جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO family_contexts (
                student_profile_id,
                guardian_status, guardian_notes,
                siblings_brothers, siblings_sisters, family_members,
                school_contact, contact_details,
                has_study_space, has_desk, parental_support, educational_notes,
                economic_status, economic_notes,
                family_stress, health_issues, other_factors,
                notes, recorded_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            family_context.student_profile_id,
            family_context.guardian_status,
            family_context.guardian_notes,
            family_context.siblings_brothers,
            family_context.siblings_sisters,
            family_context.family_members,
            family_context.school_contact,
            family_context.contact_details,
            1 if family_context.has_study_space else 0,
            1 if family_context.has_desk else 0,
            family_context.parental_support,
            family_context.educational_notes,
            family_context.economic_status,
            family_context.economic_notes,
            family_context.family_stress,
            family_context.health_issues,
            family_context.other_factors,
            family_context.notes,
            family_context.recorded_by
        ))
        
        self.db.commit()
        family_context.id = cursor.lastrowid
        return family_context
    
    def get_by_id(self, context_id, include_deleted=False):
        """دریافت اطلاعات زمینه‌ای با شناسه"""
        query = "SELECT * FROM family_contexts WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (context_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_family_context(row)
        return None
    
    def get_by_student_profile(self, profile_id, include_deleted=False):
        """دریافت اطلاعات زمینه‌ای یک پرونده دانش‌آموز"""
        query = "SELECT * FROM family_contexts WHERE student_profile_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY created_at DESC LIMIT 1"
        
        cursor = self.db.execute_query(query, (profile_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_family_context(row)
        return None
    
    def update(self, family_context):
        """به‌روزرسانی اطلاعات زمینه‌ای خانواده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE family_contexts SET
                guardian_status = ?,
                guardian_notes = ?,
                siblings_brothers = ?,
                siblings_sisters = ?,
                family_members = ?,
                school_contact = ?,
                contact_details = ?,
                has_study_space = ?,
                has_desk = ?,
                parental_support = ?,
                educational_notes = ?,
                economic_status = ?,
                economic_notes = ?,
                family_stress = ?,
                health_issues = ?,
                other_factors = ?,
                notes = ?,
                recorded_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            family_context.guardian_status,
            family_context.guardian_notes,
            family_context.siblings_brothers,
            family_context.siblings_sisters,
            family_context.family_members,
            family_context.school_contact,
            family_context.contact_details,
            1 if family_context.has_study_space else 0,
            1 if family_context.has_desk else 0,
            family_context.parental_support,
            family_context.educational_notes,
            family_context.economic_status,
            family_context.economic_notes,
            family_context.family_stress,
            family_context.health_issues,
            family_context.other_factors,
            family_context.notes,
            family_context.recorded_by,
            family_context.id
        ))
        
        self.db.commit()
        return family_context
    
    def delete(self, context_id, user_id=None):
        """حذف منطقی اطلاعات زمینه‌ای"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM family_contexts WHERE id = ? AND is_deleted = 0",
            (context_id,)
        )
        if not cursor.fetchone():
            return False
        
        now = utc_now_iso()
        cursor.execute("""
            UPDATE family_contexts SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, context_id))
        
        self.db.commit()
        return True
    
    def restore(self, context_id, user_id=None):
        """بازیابی اطلاعات زمینه‌ای حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE family_contexts SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (context_id,))
        
        self.db.commit()
        return True
    
    def _row_to_family_context(self, row):
        """تبدیل ردیف دیتابیس به مدل FamilyContext"""
        context = FamilyContext()
        context.id = row['id']
        context.student_profile_id = row['student_profile_id']
        context.guardian_status = row['guardian_status']
        context.guardian_notes = row['guardian_notes']
        context.siblings_brothers = row['siblings_brothers'] or 0
        context.siblings_sisters = row['siblings_sisters'] or 0
        context.family_members = row['family_members'] or 0
        context.school_contact = row['school_contact']
        context.contact_details = row['contact_details']
        context.has_study_space = bool(row['has_study_space'])
        context.has_desk = bool(row['has_desk'])
        context.parental_support = row['parental_support']
        context.educational_notes = row['educational_notes']
        context.economic_status = row['economic_status']
        context.economic_notes = row['economic_notes']
        context.family_stress = row['family_stress']
        context.health_issues = row['health_issues']
        context.other_factors = row['other_factors']
        context.notes = row['notes']
        context.recorded_by = row['recorded_by']
        context.created_at = row['created_at']
        context.updated_at = row['updated_at']
        context.is_deleted = row['is_deleted']
        context.deleted_at = row['deleted_at']
        context.deleted_by = row['deleted_by']
        return context