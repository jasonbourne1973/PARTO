"""
لایه دسترسی به داده کادر مدرسه
"""

from database.connection import DatabaseConnection
from models.staff import Staff


class StaffDAL:
    """عملیات CRUD برای کادر مدرسه"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, staff):
        """ایجاد عضو جدید کادر"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO staff (
                full_name, role, phone, email, is_active, description
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            staff.full_name,
            staff.role,
            staff.phone,
            staff.email,
            staff.is_active,
            staff.description
        ))
        
        conn.commit()
        staff.id = cursor.lastrowid
        return staff
    
    def get_by_id(self, staff_id):
        """دریافت عضو کادر با شناسه"""
        cursor = self.db.execute_query(
            "SELECT * FROM staff WHERE id = ?",
            (staff_id,)
        )
        row = cursor.fetchone()
        
        if row:
            return self._row_to_staff(row)
        return None
    
    def get_all(self, include_inactive=False):
        """دریافت همه اعضای کادر"""
        if include_inactive:
            query = "SELECT * FROM staff ORDER BY full_name"
        else:
            query = "SELECT * FROM staff WHERE is_active = 1 ORDER BY full_name"
        
        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        return [self._row_to_staff(row) for row in rows]
    
    def get_by_role(self, role):
        """دریافت اعضای کادر بر اساس سمت"""
        cursor = self.db.execute_query(
            "SELECT * FROM staff WHERE role = ? AND is_active = 1 ORDER BY full_name",
            (role,)
        )
        rows = cursor.fetchall()
        return [self._row_to_staff(row) for row in rows]
    
    def update(self, staff):
        """به‌روزرسانی عضو کادر"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE staff SET
                full_name = ?, role = ?, phone = ?, email = ?,
                is_active = ?, description = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            staff.full_name,
            staff.role,
            staff.phone,
            staff.email,
            staff.is_active,
            staff.description,
            staff.id
        ))
        
        conn.commit()
        return staff
    
    def delete(self, staff_id):
        """حذف عضو کادر"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM staff WHERE id = ?",
            (staff_id,)
        )
        
        conn.commit()
        return True
    
    def _row_to_staff(self, row):
        """تبدیل ردیف دیتابیس به مدل Staff"""
        staff = Staff()
        staff.id = row['id']
        staff.full_name = row['full_name']
        staff.role = row['role']
        staff.phone = row['phone']
        staff.email = row['email']
        staff.is_active = row['is_active']
        staff.description = row['description']
        staff.created_at = row['created_at']
        return staff