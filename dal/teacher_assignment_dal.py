"""
لایه دسترسی به داده انتساب معلم به دانش‌آموز - با متدهای آماری
"""

import sqlite3

from database.connection import DatabaseConnection
from models.teacher_assignment import TeacherAssignment
from utils.logger import get_logger
from utils.time_utils import utc_now_iso

logger = get_logger(__name__)


class TeacherAssignmentDAL:
    """عملیات CRUD برای انتساب معلم به دانش‌آموز"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, assignment):
        """ایجاد انتساب جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO teacher_assignments (
                student_id, staff_id, academic_year_id,
                grade, class_name, is_active, assigned_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            assignment.student_id,
            assignment.staff_id,
            assignment.academic_year_id,
            assignment.grade,
            assignment.class_name,
            assignment.is_active,
            assignment.assigned_date
        ))
        
        conn.commit()
        assignment.id = cursor.lastrowid
        return assignment
    
    def get_by_id(self, assignment_id):
        """دریافت انتساب با شناسه"""
        cursor = self.db.execute_query(
            """SELECT ta.*, 
                      s.first_name || ' ' || s.last_name as student_name,
                      st.full_name as teacher_name,
                      ay.title as academic_year_title
               FROM teacher_assignments ta
               LEFT JOIN students s ON ta.student_id = s.id
               LEFT JOIN staff st ON ta.staff_id = st.id
               LEFT JOIN academic_years ay ON ta.academic_year_id = ay.id
               WHERE ta.id = ? AND ta.is_deleted = 0""",
            (assignment_id,)
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_assignment(row)
        return None
    
    def get_by_student(self, student_id, academic_year_id=None, include_inactive=False):
        """دریافت انتساب‌های یک دانش‌آموز"""
        query = """
            SELECT ta.*, 
                   s.first_name || ' ' || s.last_name as student_name,
                   st.full_name as teacher_name,
                   ay.title as academic_year_title
            FROM teacher_assignments ta
            LEFT JOIN students s ON ta.student_id = s.id
            LEFT JOIN staff st ON ta.staff_id = st.id
            LEFT JOIN academic_years ay ON ta.academic_year_id = ay.id
            WHERE ta.student_id = ? AND ta.is_deleted = 0
        """
        params = [student_id]
        
        if academic_year_id:
            query += " AND ta.academic_year_id = ?"
            params.append(academic_year_id)
        
        if not include_inactive:
            query += " AND ta.is_active = 1"
        
        query += " ORDER BY ta.assigned_date DESC"
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_assignment(row) for row in rows]
    
    def get_by_teacher(self, staff_id, academic_year_id=None, include_inactive=False):
        """دریافت انتساب‌های یک معلم (لیست دانش‌آموزان معلم)"""
        query = """
            SELECT ta.*, 
                   s.first_name || ' ' || s.last_name as student_name,
                   st.full_name as teacher_name,
                   ay.title as academic_year_title
            FROM teacher_assignments ta
            LEFT JOIN students s ON ta.student_id = s.id
            LEFT JOIN staff st ON ta.staff_id = st.id
            LEFT JOIN academic_years ay ON ta.academic_year_id = ay.id
            WHERE ta.staff_id = ? AND ta.is_deleted = 0
        """
        params = [staff_id]
        
        if academic_year_id:
            query += " AND ta.academic_year_id = ?"
            params.append(academic_year_id)
        
        if not include_inactive:
            query += " AND ta.is_active = 1"
        
        query += " ORDER BY s.last_name, s.first_name"
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_assignment(row) for row in rows]
    
    def get_by_academic_year(self, academic_year_id):
        """دریافت همه انتساب‌های یک سال تحصیلی"""
        cursor = self.db.execute_query("""
            SELECT ta.*, 
                   s.first_name || ' ' || s.last_name as student_name,
                   st.full_name as teacher_name,
                   ay.title as academic_year_title
            FROM teacher_assignments ta
            LEFT JOIN students s ON ta.student_id = s.id
            LEFT JOIN staff st ON ta.staff_id = st.id
            LEFT JOIN academic_years ay ON ta.academic_year_id = ay.id
            WHERE ta.academic_year_id = ? AND ta.is_deleted = 0 AND ta.is_active = 1
            ORDER BY s.last_name, s.first_name
        """, (academic_year_id,))
        rows = cursor.fetchall()
        return [self._row_to_assignment(row) for row in rows]
    
    def get_all(self, limit=None):
        """دریافت همه انتساب‌ها"""
        query = """
            SELECT ta.*, 
                   s.first_name || ' ' || s.last_name as student_name,
                   st.full_name as teacher_name,
                   ay.title as academic_year_title
            FROM teacher_assignments ta
            LEFT JOIN students s ON ta.student_id = s.id
            LEFT JOIN staff st ON ta.staff_id = st.id
            LEFT JOIN academic_years ay ON ta.academic_year_id = ay.id
            WHERE ta.is_deleted = 0 AND ta.is_active = 1
            ORDER BY ta.id DESC
        """
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params if params else None)
        rows = cursor.fetchall()
        return [self._row_to_assignment(row) for row in rows]
    
    def update(self, assignment):
        """به‌روزرسانی انتساب"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE teacher_assignments SET
                student_id = ?, staff_id = ?, academic_year_id = ?,
                grade = ?, class_name = ?, is_active = ?,
                assigned_date = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            assignment.student_id,
            assignment.staff_id,
            assignment.academic_year_id,
            assignment.grade,
            assignment.class_name,
            assignment.is_active,
            assignment.assigned_date,
            assignment.id
        ))
        
        conn.commit()
        return assignment
    
    def delete(self, assignment_id, user_id=None):
        """حذف منطقی انتساب"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        now = utc_now_iso()
        cursor.execute("""
            UPDATE teacher_assignments SET
                is_deleted = 1,
                is_active = 0,
                deleted_at = ?,
                deleted_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (now, user_id, assignment_id))
        
        conn.commit()
        return True
    
    def deactivate(self, assignment_id):
        """غیرفعال کردن انتساب (بدون حذف)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE teacher_assignments SET
                is_active = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (assignment_id,))
        
        conn.commit()
        return True
    
    def activate(self, assignment_id):
        """فعال کردن انتساب"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE teacher_assignments SET
                is_active = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (assignment_id,))
        
        conn.commit()
        return True
    
    # ============================================================
    # متدهای آماری جدید برای گزارش عملکرد معلم
    # ============================================================
    
    def get_teacher_stats(self, staff_id, start_date=None, end_date=None):
        """
        دریافت آمار کلی عملکرد یک معلم
        
        Args:
            staff_id: شناسه معلم
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
        
        Returns:
            dict: {
                'total_students': int,
                'total_observations': int,
                'positive': int,
                'negative': int,
                'neutral': int,
                'avg_severity': float,
                'total_interventions': int,
                'total_followups': int,
                'pending_followups': int
            }
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # دریافت دانش‌آموزان معلم
            assignments = self.get_by_teacher(staff_id)
            student_ids = [a.student_id for a in assignments if a.is_active == 1]
            
            if not student_ids:
                return {
                    'total_students': 0,
                    'total_observations': 0,
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0,
                    'avg_severity': 0,
                    'total_interventions': 0,
                    'total_followups': 0,
                    'pending_followups': 0
                }
            
            # دریافت مشاهدات
            placeholders = ','.join(['?'] * len(student_ids))
            obs_query = f"""
                SELECT o.*
                FROM observations o
                JOIN student_academic_profiles sap ON o.student_profile_id = sap.id
                WHERE sap.student_id IN ({placeholders})
                AND o.staff_id = ?
                AND o.is_deleted = 0
            """
            obs_params = list(student_ids) + [staff_id]
            
            if start_date:
                obs_query += " AND o.observation_date >= ?"
                obs_params.append(start_date)
            if end_date:
                obs_query += " AND o.observation_date <= ?"
                obs_params.append(end_date)
            
            cursor.execute(obs_query, obs_params)
            obs_rows = cursor.fetchall()
            
            total_obs = len(obs_rows)
            positive = sum(1 for o in obs_rows if o['behavior_type'] == 'مثبت')
            negative = sum(1 for o in obs_rows if o['behavior_type'] == 'منفی')
            neutral = total_obs - positive - negative
            
            severities = [o['severity'] for o in obs_rows if o['severity']]
            avg_severity = sum(severities) / len(severities) if severities else 0
            
            # دریافت مداخلات
            inter_query = f"""
                SELECT i.*
                FROM interventions i
                JOIN student_academic_profiles sap ON i.student_profile_id = sap.id
                WHERE sap.student_id IN ({placeholders})
                AND i.staff_id = ?
                AND i.is_deleted = 0
            """
            inter_params = list(student_ids) + [staff_id]
            
            if start_date:
                inter_query += " AND i.date >= ?"
                inter_params.append(start_date)
            if end_date:
                inter_query += " AND i.date <= ?"
                inter_params.append(end_date)
            
            cursor.execute(inter_query, inter_params)
            inter_rows = cursor.fetchall()
            total_inter = len(inter_rows)
            
            # دریافت پیگیری‌ها
            follow_query = f"""
                SELECT f.*
                FROM followups f
                JOIN interventions i ON f.intervention_id = i.id
                JOIN student_academic_profiles sap ON i.student_profile_id = sap.id
                WHERE sap.student_id IN ({placeholders})
                AND f.staff_id = ?
                AND f.is_deleted = 0
            """
            follow_params = list(student_ids) + [staff_id]
            
            if start_date:
                follow_query += " AND f.date >= ?"
                follow_params.append(start_date)
            if end_date:
                follow_query += " AND f.date <= ?"
                follow_params.append(end_date)
            
            cursor.execute(follow_query, follow_params)
            follow_rows = cursor.fetchall()
            
            total_follow = len(follow_rows)
            pending_follow = sum(1 for f in follow_rows if f['status'] == 'pending')
            
            return {
                'total_students': len(student_ids),
                'total_observations': total_obs,
                'positive': positive,
                'negative': negative,
                'neutral': neutral,
                'avg_severity': round(avg_severity, 1),
                'total_interventions': total_inter,
                'total_followups': total_follow,
                'pending_followups': pending_follow
            }
            
        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت آمار معلم: {e}")
            return {
                'total_students': 0,
                'total_observations': 0,
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'avg_severity': 0,
                'total_interventions': 0,
                'total_followups': 0,
                'pending_followups': 0
            }
    
    def get_teacher_students_with_stats(self, staff_id, start_date=None, end_date=None):
        """
        دریافت لیست دانش‌آموزان معلم با آمار
        
        Args:
            staff_id: شناسه معلم
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
        
        Returns:
            list: [
                {
                    'student_id': int,
                    'student_name': str,
                    'grade': int,
                    'class_name': str,
                    'observations_count': int,
                    'positive': int,
                    'negative': int,
                    'avg_severity': float,
                    'interventions_count': int,
                    'followups_count': int
                }
            ]
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # دریافت انتساب‌ها
            assignments = self.get_by_teacher(staff_id)
            
            if not assignments:
                return []
            
            result = []
            for assignment in assignments:
                student_id = assignment.student_id
                
                # دریافت مشاهدات دانش‌آموز
                obs_query = """
                    SELECT o.*
                    FROM observations o
                    JOIN student_academic_profiles sap ON o.student_profile_id = sap.id
                    WHERE sap.student_id = ?
                    AND o.staff_id = ?
                    AND o.is_deleted = 0
                """
                obs_params = [student_id, staff_id]
                
                if start_date:
                    obs_query += " AND o.observation_date >= ?"
                    obs_params.append(start_date)
                if end_date:
                    obs_query += " AND o.observation_date <= ?"
                    obs_params.append(end_date)
                
                cursor.execute(obs_query, obs_params)
                obs_rows = cursor.fetchall()
                
                total_obs = len(obs_rows)
                positive = sum(1 for o in obs_rows if o['behavior_type'] == 'مثبت')
                negative = sum(1 for o in obs_rows if o['behavior_type'] == 'منفی')
                
                severities = [o['severity'] for o in obs_rows if o['severity']]
                avg_severity = sum(severities) / len(severities) if severities else 0
                
                # دریافت مداخلات دانش‌آموز
                inter_query = """
                    SELECT i.*
                    FROM interventions i
                    JOIN student_academic_profiles sap ON i.student_profile_id = sap.id
                    WHERE sap.student_id = ?
                    AND i.staff_id = ?
                    AND i.is_deleted = 0
                """
                inter_params = [student_id, staff_id]
                
                if start_date:
                    inter_query += " AND i.date >= ?"
                    inter_params.append(start_date)
                if end_date:
                    inter_query += " AND i.date <= ?"
                    inter_params.append(end_date)
                
                cursor.execute(inter_query, inter_params)
                inter_rows = cursor.fetchall()
                
                result.append({
                    'student_id': student_id,
                    'student_name': assignment.student_name or 'نامشخص',
                    'grade': assignment.grade,
                    'class_name': assignment.class_name or '',
                    'observations_count': total_obs,
                    'positive': positive,
                    'negative': negative,
                    'avg_severity': round(avg_severity, 1),
                    'interventions_count': len(inter_rows)
                })
            
            return result
            
        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت لیست دانش‌آموزان معلم: {e}")
            return []
    
    def get_teacher_trend(self, staff_id, period='monthly', start_date=None, end_date=None):
        """
        دریافت روند عملکرد معلم
        
        Args:
            staff_id: شناسه معلم
            period: بازه زمانی ('monthly', 'weekly', 'daily')
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
        
        Returns:
            list: [
                {
                    'period': str,
                    'label': str,
                    'positive': int,
                    'negative': int,
                    'neutral': int,
                    'total': int
                }
            ]
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # دریافت مشاهدات معلم
            query = """
                SELECT o.observation_date, o.behavior_type
                FROM observations o
                WHERE o.staff_id = ?
                AND o.is_deleted = 0
            """
            params = [staff_id]
            
            if start_date:
                query += " AND o.observation_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND o.observation_date <= ?"
                params.append(end_date)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                return []
            
            # گروه‌بندی بر اساس زمان
            from collections import defaultdict
            grouped = defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0})
            
            for row in rows:
                date_str = row['observation_date']
                if not date_str:
                    continue
                
                # استخراج کلید بر اساس دوره
                if period == 'monthly':
                    key = date_str[:7]  # yyyy/MM
                    label = self._get_month_label(date_str)
                elif period == 'weekly':
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        try:
                            day = int(parts[2])
                            week = (day - 1) // 7 + 1
                            key = f"{parts[0]}/{parts[1]}/W{week}"
                            label = f"هفته {week} {parts[1]}"
                        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError):
                            key = date_str[:7]
                            label = date_str[:7]
                    else:
                        key = date_str[:7]
                        label = date_str[:7]
                else:  # daily
                    key = date_str
                    label = date_str
                
                behavior = row['behavior_type']
                if behavior == 'مثبت':
                    grouped[key]['positive'] += 1
                elif behavior == 'منفی':
                    grouped[key]['negative'] += 1
                else:
                    grouped[key]['neutral'] += 1
            
            # مرتب‌سازی کلیدها
            sorted_keys = sorted(grouped.keys())
            
            result = []
            for key in sorted_keys:
                data = grouped[key]
                total = data['positive'] + data['negative'] + data['neutral']
                result.append({
                    'period': key,
                    'label': label if period != 'daily' else key,
                    'positive': data['positive'],
                    'negative': data['negative'],
                    'neutral': data['neutral'],
                    'total': total
                })
            
            return result
            
        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت روند عملکرد معلم: {e}")
            return []
    
    def _get_month_label(self, date_str):
        """دریافت برچسب ماه از تاریخ — پیاده‌سازی مشترک

        بازرسی نهم: این متد در ۴ فایل DAL کپی شده بود؛ حالا همه به یک
        منبع واحد (utils.persian_date) وصل‌اند تا اصلاح‌های آینده
        (ارقام فارسی، تاریخ ناقص، نام ماه) یک‌جا اعمال شود.
        """
        from utils.persian_date import PersianDate
        return PersianDate.get_month_label(date_str)
    
    def _row_to_assignment(self, row):
        """تبدیل ردیف دیتابیس به مدل TeacherAssignment"""
        assignment = TeacherAssignment()
        assignment.id = row['id']
        assignment.student_id = row['student_id']
        assignment.staff_id = row['staff_id']
        assignment.academic_year_id = row['academic_year_id']
        assignment.grade = row['grade']
        assignment.class_name = row['class_name']
        assignment.is_active = row['is_active']
        assignment.assigned_date = row['assigned_date']
        assignment.created_at = row['created_at']
        assignment.updated_at = row['updated_at']
        assignment.is_deleted = row['is_deleted']
        assignment.deleted_at = row['deleted_at']
        assignment.deleted_by = row['deleted_by']
        
        # ✅ اصلاح: استفاده از دسترسی مستقیم به جای متد get()
        assignment.student_name = row['student_name'] if 'student_name' in row.keys() else None
        assignment.teacher_name = row['teacher_name'] if 'teacher_name' in row.keys() else None
        assignment.academic_year_title = row['academic_year_title'] if 'academic_year_title' in row.keys() else None
        
        return assignment