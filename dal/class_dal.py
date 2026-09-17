"""
لایه دسترسی به داده کلاس‌ها - با متدهای آماری
"""

import sqlite3
from database.connection import DatabaseConnection
from models.class_model import ClassModel


class ClassDAL:
    """عملیات CRUD برای کلاس‌ها"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, class_obj):
        """ایجاد کلاس جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        errors = class_obj.validate()
        if errors:
            raise ValueError("\n".join(errors))
        
        cursor.execute("""
            INSERT INTO classes (name, grade, teacher_id, academic_year_id, capacity, is_active, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            class_obj.name,
            class_obj.grade,
            class_obj.teacher_id,
            class_obj.academic_year_id,
            class_obj.capacity,
            class_obj.is_active,
            class_obj.description
        ))
        
        conn.commit()
        class_obj.id = cursor.lastrowid
        return class_obj
    
    def get_by_id(self, class_id):
        """دریافت کلاس با شناسه"""
        cursor = self.db.execute_query(
            "SELECT * FROM classes WHERE id = ? AND is_deleted = 0",
            (class_id,)
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_class(row)
        return None
    
    def get_by_grade(self, grade, academic_year_id=None):
        """دریافت کلاس‌های یک پایه"""
        query = "SELECT * FROM classes WHERE grade = ? AND is_deleted = 0 AND is_active = 1"
        params = [grade]
        
        if academic_year_id:
            query += " AND academic_year_id = ?"
            params.append(academic_year_id)
        
        query += " ORDER BY name"
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_class(row) for row in rows]
    
    def get_by_teacher(self, teacher_id, academic_year_id=None):
        """دریافت کلاس‌های یک معلم"""
        query = "SELECT * FROM classes WHERE teacher_id = ? AND is_deleted = 0 AND is_active = 1"
        params = [teacher_id]
        
        if academic_year_id:
            query += " AND academic_year_id = ?"
            params.append(academic_year_id)
        
        query += " ORDER BY grade, name"
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_class(row) for row in rows]
    
    def get_all(self, academic_year_id=None, include_inactive=False):
        """دریافت همه کلاس‌ها"""
        query = "SELECT * FROM classes WHERE is_deleted = 0"
        params = []
        
        if not include_inactive:
            query += " AND is_active = 1"
        
        if academic_year_id:
            query += " AND academic_year_id = ?"
            params.append(academic_year_id)
        
        query += " ORDER BY grade, name"
        
        cursor = self.db.execute_query(query, params if params else None)
        rows = cursor.fetchall()
        return [self._row_to_class(row) for row in rows]
    
    def get_by_academic_year(self, academic_year_id):
        """دریافت کلاس‌های یک سال تحصیلی"""
        cursor = self.db.execute_query(
            "SELECT * FROM classes WHERE academic_year_id = ? AND is_deleted = 0 AND is_active = 1 ORDER BY grade, name",
            (academic_year_id,)
        )
        rows = cursor.fetchall()
        return [self._row_to_class(row) for row in rows]
    
    def update(self, class_obj):
        """به‌روزرسانی کلاس"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        errors = class_obj.validate()
        if errors:
            raise ValueError("\n".join(errors))
        
        cursor.execute("""
            UPDATE classes SET
                name = ?, grade = ?, teacher_id = ?,
                academic_year_id = ?, capacity = ?,
                is_active = ?, description = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            class_obj.name,
            class_obj.grade,
            class_obj.teacher_id,
            class_obj.academic_year_id,
            class_obj.capacity,
            class_obj.is_active,
            class_obj.description,
            class_obj.id
        ))
        
        conn.commit()
        return class_obj
    
    def delete(self, class_id):
        """حذف منطقی کلاس"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE classes SET
                is_deleted = 1,
                is_active = 0,
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (class_id,))
        
        conn.commit()
        return True
    
    def get_student_count(self, class_id):
        """دریافت تعداد دانش‌آموزان یک کلاس"""
        cursor = self.db.execute_query("""
            SELECT COUNT(*) as count
            FROM student_academic_profiles
            WHERE class_name = (
                SELECT name FROM classes WHERE id = ?
            ) AND is_deleted = 0 AND status = 'active'
        """, (class_id,))
        row = cursor.fetchone()
        return row['count'] if row else 0
    
    def get_classes_with_stats(self, academic_year_id=None):
        """دریافت کلاس‌ها با آمار دانش‌آموزان"""
        classes = self.get_all(academic_year_id)
        result = []
        for class_obj in classes:
            student_count = self.get_student_count(class_obj.id)
            result.append({
                'class': class_obj,
                'student_count': student_count,
                'display_name': class_obj.display_name
            })
        return result
    
    # ============================================================
    # متدهای آماری جدید برای گزارش کلاس
    # ============================================================
    
    def get_class_observations_stats(self, class_id, start_date=None, end_date=None):
        """
        دریافت آمار مشاهدات یک کلاس
        
        Args:
            class_id: شناسه کلاس
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
        
        Returns:
            dict: {
                'total': int,
                'positive': int,
                'negative': int,
                'neutral': int,
                'avg_severity': float,
                'students_with_observation': int,
                'students_without_observation': int
            }
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # دریافت کلاس
            class_obj = self.get_by_id(class_id)
            if not class_obj:
                return None
            
            # دریافت دانش‌آموزان کلاس
            students_query = """
                SELECT DISTINCT s.id
                FROM students s
                JOIN student_academic_profiles sap ON s.id = sap.student_id
                WHERE sap.class_name = ? AND sap.is_deleted = 0 AND sap.status = 'active'
            """
            params = [class_obj.name]
            
            cursor.execute(students_query, params)
            student_rows = cursor.fetchall()
            student_ids = [row['id'] for row in student_rows]
            
            if not student_ids:
                return {
                    'total': 0,
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0,
                    'avg_severity': 0,
                    'students_with_observation': 0,
                    'students_without_observation': 0,
                    'student_ids': []
                }
            
            # دریافت مشاهدات دانش‌آموزان
            placeholders = ','.join(['?'] * len(student_ids))
            obs_query = f"""
                SELECT o.*
                FROM observations o
                JOIN student_academic_profiles sap ON o.student_profile_id = sap.id
                WHERE sap.student_id IN ({placeholders})
                AND o.is_deleted = 0
            """
            obs_params = list(student_ids)
            
            if start_date:
                obs_query += " AND o.observation_date >= ?"
                obs_params.append(start_date)
            if end_date:
                obs_query += " AND o.observation_date <= ?"
                obs_params.append(end_date)
            
            obs_query += " ORDER BY o.observation_date DESC"
            
            cursor.execute(obs_query, obs_params)
            obs_rows = cursor.fetchall()
            
            # محاسبه آمار
            total = len(obs_rows)
            positive = sum(1 for o in obs_rows if o['behavior_type'] == 'مثبت')
            negative = sum(1 for o in obs_rows if o['behavior_type'] == 'منفی')
            neutral = total - positive - negative
            
            severities = [o['severity'] for o in obs_rows if o['severity']]
            avg_severity = sum(severities) / len(severities) if severities else 0
            
            # تعداد دانش‌آموزان با/بدون مشاهده
            students_with_obs = set()
            for o in obs_rows:
                students_with_obs.add(o['student_profile_id'])
            
            return {
                'total': total,
                'positive': positive,
                'negative': negative,
                'neutral': neutral,
                'avg_severity': round(avg_severity, 1),
                'students_with_observation': len(students_with_obs),
                'students_without_observation': len(student_ids) - len(students_with_obs),
                'student_ids': student_ids
            }
            
        except Exception as e:
            print(f"خطا در دریافت آمار مشاهدات کلاس: {e}")
            return None
    
    def get_class_competency_stats(self, class_id, start_date=None, end_date=None):
        """
        دریافت آمار شایستگی‌های یک کلاس
        
        Args:
            class_id: شناسه کلاس
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
        
        Returns:
            dict: {
                'competency_name': {
                    'count': int,
                    'avg_severity': float,
                    'positive': int,
                    'negative': int
                }
            }
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # دریافت کلاس
            class_obj = self.get_by_id(class_id)
            if not class_obj:
                return None
            
            # دریافت دانش‌آموزان کلاس
            students_query = """
                SELECT DISTINCT s.id
                FROM students s
                JOIN student_academic_profiles sap ON s.id = sap.student_id
                WHERE sap.class_name = ? AND sap.is_deleted = 0 AND sap.status = 'active'
            """
            cursor.execute(students_query, (class_obj.name,))
            student_rows = cursor.fetchall()
            student_ids = [row['id'] for row in student_rows]
            
            if not student_ids:
                return {}
            
            # دریافت مشاهدات با شایستگی
            placeholders = ','.join(['?'] * len(student_ids))
            obs_query = f"""
                SELECT o.competency_id, o.behavior_type, o.severity, c.title as competency_name
                FROM observations o
                JOIN student_academic_profiles sap ON o.student_profile_id = sap.id
                LEFT JOIN competencies c ON o.competency_id = c.id
                WHERE sap.student_id IN ({placeholders})
                AND o.competency_id IS NOT NULL
                AND o.is_deleted = 0
            """
            obs_params = list(student_ids)
            
            if start_date:
                obs_query += " AND o.observation_date >= ?"
                obs_params.append(start_date)
            if end_date:
                obs_query += " AND o.observation_date <= ?"
                obs_params.append(end_date)
            
            cursor.execute(obs_query, obs_params)
            obs_rows = cursor.fetchall()
            
            # گروه‌بندی بر اساس شایستگی
            stats = {}
            for row in obs_rows:
                comp_name = row['competency_name'] or f"شایستگی {row['competency_id']}"
                if comp_name not in stats:
                    stats[comp_name] = {
                        'count': 0,
                        'total_severity': 0,
                        'positive': 0,
                        'negative': 0,
                        'competency_id': row['competency_id']
                    }
                stats[comp_name]['count'] += 1
                stats[comp_name]['total_severity'] += row['severity'] or 1
                if row['behavior_type'] == 'مثبت':
                    stats[comp_name]['positive'] += 1
                elif row['behavior_type'] == 'منفی':
                    stats[comp_name]['negative'] += 1
            
            # محاسبه میانگین
            for name in stats:
                stats[name]['avg_severity'] = round(
                    stats[name]['total_severity'] / stats[name]['count'], 1
                ) if stats[name]['count'] > 0 else 0
            
            return stats
            
        except Exception as e:
            print(f"خطا در دریافت آمار شایستگی‌های کلاس: {e}")
            return {}
    
    def get_class_student_stats(self, class_id, start_date=None, end_date=None):
        """
        دریافت آمار دانش‌آموزان یک کلاس
        
        Args:
            class_id: شناسه کلاس
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
        
        Returns:
            list: [
                {
                    'student_id': int,
                    'student_name': str,
                    'observations_count': int,
                    'positive': int,
                    'negative': int,
                    'avg_severity': float,
                    'status': str
                }
            ]
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # دریافت کلاس
            class_obj = self.get_by_id(class_id)
            if not class_obj:
                return None
            
            # دریافت دانش‌آموزان کلاس با اطلاعات پرونده
            students_query = """
                SELECT s.id, s.first_name, s.last_name, sap.grade, sap.class_name
                FROM students s
                JOIN student_academic_profiles sap ON s.id = sap.student_id
                WHERE sap.class_name = ? AND sap.is_deleted = 0 AND sap.status = 'active'
                ORDER BY s.last_name, s.first_name
            """
            cursor.execute(students_query, (class_obj.name,))
            student_rows = cursor.fetchall()
            
            if not student_rows:
                return []
            
            result = []
            for student in student_rows:
                student_id = student['id']
                student_name = f"{student['first_name']} {student['last_name']}"
                
                # دریافت مشاهدات دانش‌آموز
                obs_query = """
                    SELECT o.*
                    FROM observations o
                    JOIN student_academic_profiles sap ON o.student_profile_id = sap.id
                    WHERE sap.student_id = ?
                    AND o.is_deleted = 0
                """
                obs_params = [student_id]
                
                if start_date:
                    obs_query += " AND o.observation_date >= ?"
                    obs_params.append(start_date)
                if end_date:
                    obs_query += " AND o.observation_date <= ?"
                    obs_params.append(end_date)
                
                obs_query += " ORDER BY o.observation_date DESC"
                
                cursor.execute(obs_query, obs_params)
                obs_rows = cursor.fetchall()
                
                total = len(obs_rows)
                positive = sum(1 for o in obs_rows if o['behavior_type'] == 'مثبت')
                negative = sum(1 for o in obs_rows if o['behavior_type'] == 'منفی')
                neutral = total - positive - negative
                
                severities = [o['severity'] for o in obs_rows if o['severity']]
                avg_severity = sum(severities) / len(severities) if severities else 0
                
                # تعیین وضعیت
                if total == 0:
                    status = "بدون مشاهده"
                elif positive >= negative and positive >= total * 0.6:
                    status = "مطلوب"
                elif positive >= negative:
                    status = "متوسط"
                else:
                    status = "نیازمند توجه"
                
                result.append({
                    'student_id': student_id,
                    'student_name': student_name,
                    'grade': student['grade'],
                    'class_name': student['class_name'],
                    'observations_count': total,
                    'positive': positive,
                    'negative': negative,
                    'neutral': neutral,
                    'avg_severity': round(avg_severity, 1),
                    'status': status
                })
            
            return result
            
        except Exception as e:
            print(f"خطا در دریافت آمار دانش‌آموزان کلاس: {e}")
            return []
    
    def get_class_summary(self, class_id, start_date=None, end_date=None):
        """
        دریافت خلاصه کامل گزارش کلاس
        
        Args:
            class_id: شناسه کلاس
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
        
        Returns:
            dict: خلاصه کامل گزارش کلاس
        """
        class_obj = self.get_by_id(class_id)
        if not class_obj:
            return None
        
        observations_stats = self.get_class_observations_stats(class_id, start_date, end_date)
        competency_stats = self.get_class_competency_stats(class_id, start_date, end_date)
        student_stats = self.get_class_student_stats(class_id, start_date, end_date)
        
        return {
            'class': class_obj,
            'observations_stats': observations_stats,
            'competency_stats': competency_stats,
            'student_stats': student_stats,
            'student_count': len(student_stats) if student_stats else 0,
            'has_data': observations_stats and observations_stats['total'] > 0
        }
    
    def _row_to_class(self, row):
        """تبدیل ردیف دیتابیس به مدل ClassModel"""
        class_obj = ClassModel()
        class_obj.id = row['id']
        class_obj.name = row['name']
        class_obj.grade = row['grade']
        class_obj.teacher_id = row['teacher_id']
        class_obj.academic_year_id = row['academic_year_id']
        class_obj.capacity = row['capacity'] or 0
        class_obj.is_active = row['is_active']
        class_obj.description = row['description']
        class_obj.created_at = row['created_at']
        class_obj.updated_at = row['updated_at']
        class_obj.is_deleted = row['is_deleted']
        class_obj.deleted_at = row['deleted_at']
        class_obj.deleted_by = row['deleted_by']
        return class_obj