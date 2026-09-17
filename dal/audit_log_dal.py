"""
لایه دسترسی به داده Audit Log (تاریخچه تغییرات)
"""

from database.connection import DatabaseConnection
from datetime import datetime


class AuditLogDAL:
    """عملیات دسترسی به لاگ تغییرات"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def get_logs(self, limit=100, user_id=None, entity_type=None,
                 action=None, entity_id=None, start_date=None, end_date=None):
        """
        دریافت لاگ‌ها با فیلتر

        ===== اصلاح =====
        نسخه قبلی پارامتر `entity_id` نداشت، ولی `get_recent_changes`
        آن را با نام کلیدی می‌فرستاد:

            self.get_logs(limit=limit, entity_id=entity_id, ...)

        نتیجه: TypeError در هر فراخوانی «تاریخچه تغییرات یک موجودیت».
        حالا entity_id به همراه start_date/end_date اضافه شده.
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT al.*, 
                       s.full_name as staff_name,
                       s.role as staff_role
                FROM audit_logs al
                LEFT JOIN staff s ON al.user_id = s.id
                WHERE 1=1
            """
            params = []
            
            if user_id:
                query += " AND al.user_id = ?"
                params.append(user_id)
            if entity_type:
                query += " AND al.entity_type = ?"
                params.append(entity_type)
            if action:
                query += " AND al.action = ?"
                params.append(action)

            # ===== پارامترهای جدید =====
            if entity_id is not None:
                query += " AND al.entity_id = ?"
                params.append(entity_id)
            if start_date:
                query += " AND al.created_at >= ?"
                params.append(start_date)
            if end_date:
                query += " AND al.created_at <= ?"
                params.append(end_date)
            
            query += " ORDER BY al.created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                logs.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'user_name': row['staff_name'] or 'سیستم',
                    'user_role': row['staff_role'],
                    'action': row['action'],
                    'entity_type': row['entity_type'],
                    'entity_id': row['entity_id'],
                    'old_value': row['old_value'],
                    'new_value': row['new_value'],
                    'ip_address': row['ip_address'],
                    'created_at': row['created_at'],
                })
            
            return logs
        except Exception as e:
            print(f"⚠️ خطا در دریافت Audit Log: {e}")
            return []
    
    def get_recent_changes(self, entity_id, entity_type, limit=20):
        """دریافت تغییرات اخیر یک موجودیت خاص"""
        return self.get_logs(limit=limit, entity_id=entity_id, entity_type=entity_type)
    
    def get_user_activity(self, user_id, limit=50):
        """دریافت فعالیت‌های یک کاربر خاص"""
        return self.get_logs(limit=limit, user_id=user_id)
    
    def get_actions_summary(self, days=30):
        """دریافت خلاصه فعالیت‌ها در روزهای اخیر"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    action,
                    entity_type,
                    COUNT(*) as count,
                    DATE(created_at) as date
                FROM audit_logs
                WHERE created_at >= date('now', ?)
                GROUP BY action, entity_type, DATE(created_at)
                ORDER BY date DESC, count DESC
            """, (f'-{days} days',))
            
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    'action': row['action'],
                    'entity_type': row['entity_type'],
                    'count': row['count'],
                    'date': row['date'],
                })
            return results
        except Exception as e:
            print(f"⚠️ خطا در دریافت خلاصه فعالیت‌ها: {e}")
            return []