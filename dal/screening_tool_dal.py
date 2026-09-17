"""
لایه دسترسی به داده ابزارهای غربالگری (ScreeningTool)
"""

from database.connection import DatabaseConnection
from models.screening_tool import ScreeningTool
import json


class ScreeningToolDAL:
    """عملیات CRUD برای ابزارهای غربالگری"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, tool):
        """ایجاد ابزار جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # تبدیل فیلدهای JSON
        domains_json = json.dumps(tool.domains, ensure_ascii=False) if tool.domains else None
        sub_domains_json = json.dumps(tool.sub_domains, ensure_ascii=False) if tool.sub_domains else None
        scoring_scale_json = json.dumps(tool.scoring_scale, ensure_ascii=False) if tool.scoring_scale else None
        cutoff_scores_json = json.dumps(tool.cutoff_scores, ensure_ascii=False) if tool.cutoff_scores else None
        
        cursor.execute("""
            INSERT INTO screening_tools (
                name, version, type,
                description, reference,
                target_age_group, target_grade_range,
                domains, sub_domains,
                scoring_scale, min_score, max_score, cutoff_scores,
                status, is_standard,
                administration_time, required_training
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tool.name,
            tool.version,
            tool.type,
            tool.description,
            tool.reference,
            tool.target_age_group,
            tool.target_grade_range,
            domains_json,
            sub_domains_json,
            scoring_scale_json,
            tool.min_score,
            tool.max_score,
            cutoff_scores_json,
            tool.status,
            1 if tool.is_standard else 0,
            tool.administration_time,
            1 if tool.required_training else 0
        ))
        
        conn.commit()
        tool.id = cursor.lastrowid
        return tool
    
    def get_by_id(self, tool_id, include_deleted=False):
        """دریافت ابزار با شناسه"""
        query = "SELECT * FROM screening_tools WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (tool_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_tool(row)
        return None
    
    def get_by_name(self, name, include_deleted=False):
        """دریافت ابزار با نام"""
        query = "SELECT * FROM screening_tools WHERE name = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (name,))
        row = cursor.fetchone()
        if row:
            return self._row_to_tool(row)
        return None
    
    def get_all(self, include_inactive=False, include_deleted=False):
        """دریافت همه ابزارها"""
        query = "SELECT * FROM screening_tools WHERE 1=1"
        if not include_inactive:
            query += " AND status = 'active'"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY name, version"
        
        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        return [self._row_to_tool(row) for row in rows]
    
    def get_by_type(self, tool_type, include_deleted=False):
        """دریافت ابزارها بر اساس نوع"""
        query = "SELECT * FROM screening_tools WHERE type = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY name"
        
        cursor = self.db.execute_query(query, (tool_type,))
        rows = cursor.fetchall()
        return [self._row_to_tool(row) for row in rows]
    
    def get_active(self, include_deleted=False):
        """دریافت ابزارهای فعال"""
        return self.get_all(include_inactive=False, include_deleted=include_deleted)
    
    def update(self, tool):
        """به‌روزرسانی ابزار"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        domains_json = json.dumps(tool.domains, ensure_ascii=False) if tool.domains else None
        sub_domains_json = json.dumps(tool.sub_domains, ensure_ascii=False) if tool.sub_domains else None
        scoring_scale_json = json.dumps(tool.scoring_scale, ensure_ascii=False) if tool.scoring_scale else None
        cutoff_scores_json = json.dumps(tool.cutoff_scores, ensure_ascii=False) if tool.cutoff_scores else None
        
        cursor.execute("""
            UPDATE screening_tools SET
                name = ?,
                version = ?,
                type = ?,
                description = ?,
                reference = ?,
                target_age_group = ?,
                target_grade_range = ?,
                domains = ?,
                sub_domains = ?,
                scoring_scale = ?,
                min_score = ?,
                max_score = ?,
                cutoff_scores = ?,
                status = ?,
                is_standard = ?,
                administration_time = ?,
                required_training = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            tool.name,
            tool.version,
            tool.type,
            tool.description,
            tool.reference,
            tool.target_age_group,
            tool.target_grade_range,
            domains_json,
            sub_domains_json,
            scoring_scale_json,
            tool.min_score,
            tool.max_score,
            cutoff_scores_json,
            tool.status,
            1 if tool.is_standard else 0,
            tool.administration_time,
            1 if tool.required_training else 0,
            tool.id
        ))
        
        conn.commit()
        return tool
    
    def update_status(self, tool_id, new_status):
        """به‌روزرسانی وضعیت ابزار"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE screening_tools SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (new_status, tool_id))
        
        conn.commit()
        return True
    
    def delete(self, tool_id, user_id=None):
        """حذف منطقی ابزار"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM screening_tools WHERE id = ? AND is_deleted = 0",
            (tool_id,)
        )
        if not cursor.fetchone():
            return False
        
        from datetime import datetime
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE screening_tools SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, tool_id))
        
        conn.commit()
        return True
    
    def restore(self, tool_id, user_id=None):
        """بازیابی ابزار حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE screening_tools SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (tool_id,))
        
        conn.commit()
        return True
    
    def _row_to_tool(self, row):
        """تبدیل ردیف دیتابیس به مدل ScreeningTool"""
        tool = ScreeningTool()
        tool.id = row['id']
        tool.name = row['name']
        tool.version = row['version']
        tool.type = row['type']
        tool.description = row['description']
        tool.reference = row['reference']
        tool.target_age_group = row['target_age_group']
        tool.target_grade_range = row['target_grade_range']
        
        # تبدیل JSON
        if row['domains']:
            try:
                tool.domains = json.loads(row['domains'])
            except:
                tool.domains = None
        else:
            tool.domains = None
        
        if row['sub_domains']:
            try:
                tool.sub_domains = json.loads(row['sub_domains'])
            except:
                tool.sub_domains = None
        else:
            tool.sub_domains = None
        
        if row['scoring_scale']:
            try:
                tool.scoring_scale = json.loads(row['scoring_scale'])
            except:
                tool.scoring_scale = None
        else:
            tool.scoring_scale = None
        
        tool.min_score = row['min_score']
        tool.max_score = row['max_score']
        
        if row['cutoff_scores']:
            try:
                tool.cutoff_scores = json.loads(row['cutoff_scores'])
            except:
                tool.cutoff_scores = None
        else:
            tool.cutoff_scores = None
        
        tool.status = row['status']
        tool.is_standard = bool(row['is_standard'])
        tool.administration_time = row['administration_time']
        tool.required_training = bool(row['required_training'])
        tool.created_at = row['created_at']
        tool.updated_at = row['updated_at']
        tool.is_deleted = row['is_deleted']
        tool.deleted_at = row['deleted_at']
        tool.deleted_by = row['deleted_by']
        return tool