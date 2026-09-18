"""
لایه دسترسی به داده مشاهدات - با Soft Delete یکپارچه و متدهای گروهی
با متدهای تحلیلی برای داشبورد و پیشنهادات
"""

from database.connection import DatabaseConnection
from models.observation import Observation


class ObservationDAL:
    """عملیات CRUD برای مشاهدات با Soft Delete یکپارچه"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, observation):
        """ایجاد مشاهده جدید

        نکته: ستون‌های indicator_id و observable_behavior_id هم ذخیره
        می‌شوند (ساختار سه‌لایه شایستگی ← شاخص ← رفتار قابل مشاهده).
        توضیح کامل باگ قبلی در docstring متد `_row_to_observation` آمده است.
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO observations (
                student_profile_id, staff_id, competency_id,
                indicator_id, observable_behavior_id,
                observation_date, location, description,
                antecedent, behavior, consequence,
                behavior_type, severity, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            observation.student_profile_id,
            observation.staff_id,
            observation.competency_id,
            getattr(observation, 'indicator_id', None),
            getattr(observation, 'observable_behavior_id', None),
            observation.observation_date,
            observation.location,
            observation.description,
            observation.antecedent,
            observation.behavior,
            observation.consequence,
            observation.behavior_type,
            observation.severity,
            observation.tags
        ))
        
        conn.commit()
        observation.id = cursor.lastrowid
        return observation
    
    def get_by_id(self, observation_id, include_deleted=False):
        """دریافت مشاهده با شناسه"""
        query = "SELECT * FROM observations WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (observation_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_observation(row)
        return None
    
    def get_by_student_profile(self, profile_id, limit=None, include_deleted=False):
        """دریافت مشاهدات یک پرونده دانش‌آموز - فقط رکوردهای موجود"""
        query = "SELECT * FROM observations WHERE student_profile_id = ?"
        params = [profile_id]
        
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY observation_date DESC"
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_observation(row) for row in rows]
    
    def get_by_student(self, student_id, academic_year_id=None, include_deleted=False):
        """دریافت مشاهدات یک دانش‌آموز (با فیلتر سال تحصیلی)"""
        if academic_year_id:
            query = """
                SELECT o.* FROM observations o
                JOIN student_academic_profiles sap ON o.student_profile_id = sap.id
                WHERE sap.student_id = ? AND sap.academic_year_id = ?
            """
            params = [student_id, academic_year_id]
        else:
            query = """
                SELECT o.* FROM observations o
                JOIN student_academic_profiles sap ON o.student_profile_id = sap.id
                WHERE sap.student_id = ?
            """
            params = [student_id]
        
        if not include_deleted:
            query += " AND o.is_deleted = 0"
        
        query += " ORDER BY o.observation_date DESC"
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_observation(row) for row in rows]
    
    def get_all(self, limit=None, include_deleted=False):
        """دریافت همه مشاهدات - فقط رکوردهای موجود"""
        query = "SELECT * FROM observations"
        
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        
        query += " ORDER BY observation_date DESC"
        params = []
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params if params else None)
        rows = cursor.fetchall()
        return [self._row_to_observation(row) for row in rows]
    
    def get_by_date_range(self, profile_id, start_date, end_date, include_deleted=False):
        """دریافت مشاهدات در بازه زمانی مشخص"""
        query = """
            SELECT * FROM observations 
            WHERE student_profile_id = ? 
            AND observation_date BETWEEN ? AND ?
        """
        params = [profile_id, start_date, end_date]
        
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY observation_date DESC"
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_observation(row) for row in rows]
    
    def get_positive_observations(self, profile_id, include_deleted=False):
        """دریافت مشاهدات مثبت - فقط رکوردهای موجود"""
        query = """
            SELECT * FROM observations 
            WHERE student_profile_id = ? AND behavior_type = 'مثبت'
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY observation_date DESC"
        
        cursor = self.db.execute_query(query, (profile_id,))
        rows = cursor.fetchall()
        return [self._row_to_observation(row) for row in rows]
    
    def get_negative_observations(self, profile_id, include_deleted=False):
        """دریافت مشاهدات منفی - فقط رکوردهای موجود"""
        query = """
            SELECT * FROM observations 
            WHERE student_profile_id = ? AND behavior_type = 'منفی'
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY observation_date DESC"
        
        cursor = self.db.execute_query(query, (profile_id,))
        rows = cursor.fetchall()
        return [self._row_to_observation(row) for row in rows]
    
    def update(self, observation):
        """به‌روزرسانی مشاهده - فقط رکوردهای موجود"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM observations WHERE id = ? AND is_deleted = 0",
            (observation.id,)
        )
        if not cursor.fetchone():
            raise Exception("رکورد مورد نظر یافت نشد یا حذف شده است.")
        
        cursor.execute("""
            UPDATE observations SET
                student_profile_id = ?, staff_id = ?, competency_id = ?,
                indicator_id = ?, observable_behavior_id = ?,
                observation_date = ?, location = ?, description = ?,
                antecedent = ?, behavior = ?, consequence = ?,
                behavior_type = ?, severity = ?, tags = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            observation.student_profile_id,
            observation.staff_id,
            observation.competency_id,
            getattr(observation, 'indicator_id', None),
            getattr(observation, 'observable_behavior_id', None),
            observation.observation_date,
            observation.location,
            observation.description,
            observation.antecedent,
            observation.behavior,
            observation.consequence,
            observation.behavior_type,
            observation.severity,
            observation.tags,
            observation.id
        ))
        
        conn.commit()
        return observation
    
    def delete(self, observation_id, user_id=None):
        """حذف منطقی مشاهده - فقط رکوردهای موجود"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM observations WHERE id = ? AND is_deleted = 0",
            (observation_id,)
        )
        if not cursor.fetchone():
            return False
        
        from datetime import datetime
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE observations SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (now, user_id, observation_id))
        
        conn.commit()
        return True
    
    def restore(self, observation_id, user_id=None):
        """بازیابی مشاهده حذف شده - فقط رکوردهای حذف شده"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM observations WHERE id = ? AND is_deleted = 1",
            (observation_id,)
        )
        if not cursor.fetchone():
            return False
        
        cursor.execute("""
            UPDATE observations SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 1
        """, (observation_id,))
        
        conn.commit()
        return True
    
    def get_deleted(self, limit=None):
        """دریافت لیست رکوردهای حذف شده"""
        query = "SELECT * FROM observations WHERE is_deleted = 1 ORDER BY deleted_at DESC"
        params = []
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, tuple(params) if params else None)
        rows = cursor.fetchall()
        return [self._row_to_observation(row) for row in rows]
    
    def permanent_delete(self, observation_id):
        """حذف فیزیکی مشاهده - فقط برای موارد خاص استفاده شود"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM observations WHERE id = ?",
            (observation_id,)
        )
        conn.commit()
        return True
    
    # ============================================================
    # متدهای گروهی برای گزارش کلاس (ادامه از بخش قبلی)
    # ============================================================
    
    def get_grouped_by_class(self, class_name, start_date=None, end_date=None):
        """دریافت مشاهدات گروه‌بندی شده بر اساس نوع رفتار برای یک کلاس"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT o.*
                FROM observations o
                JOIN student_academic_profiles sap ON o.student_profile_id = sap.id
                WHERE sap.class_name = ?
                AND o.is_deleted = 0
            """
            params = [class_name]
            
            if start_date:
                query += " AND o.observation_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND o.observation_date <= ?"
                params.append(end_date)
            
            query += " ORDER BY o.observation_date DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            observations = [self._row_to_observation(row) for row in rows]
            
            positive = sum(1 for o in observations if o.behavior_type == 'مثبت')
            negative = sum(1 for o in observations if o.behavior_type == 'منفی')
            neutral = len(observations) - positive - negative
            
            return {
                'positive': positive,
                'negative': negative,
                'neutral': neutral,
                'total': len(observations),
                'observations': observations
            }
            
        except Exception as e:
            print(f"خطا در دریافت مشاهدات گروهی کلاس: {e}")
            return {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0, 'observations': []}
    
    def get_grouped_by_grade(self, grade, academic_year_id=None, start_date=None, end_date=None):
        """دریافت مشاهدات گروه‌بندی شده بر اساس پایه"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT o.*
                FROM observations o
                JOIN student_academic_profiles sap ON o.student_profile_id = sap.id
                WHERE sap.grade = ?
                AND o.is_deleted = 0
            """
            params = [grade]
            
            if academic_year_id:
                query += " AND sap.academic_year_id = ?"
                params.append(academic_year_id)
            if start_date:
                query += " AND o.observation_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND o.observation_date <= ?"
                params.append(end_date)
            
            query += " ORDER BY o.observation_date DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            observations = [self._row_to_observation(row) for row in rows]
            
            positive = sum(1 for o in observations if o.behavior_type == 'مثبت')
            negative = sum(1 for o in observations if o.behavior_type == 'منفی')
            neutral = len(observations) - positive - negative
            
            return {
                'positive': positive,
                'negative': negative,
                'neutral': neutral,
                'total': len(observations),
                'observations': observations
            }
            
        except Exception as e:
            print(f"خطا در دریافت مشاهدات گروهی پایه: {e}")
            return {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0, 'observations': []}
    
    def get_trend_by_class(self, class_name, period='monthly', start_date=None, end_date=None):
        """دریافت روند مشاهدات یک کلاس"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT o.observation_date, o.behavior_type
                FROM observations o
                JOIN student_academic_profiles sap ON o.student_profile_id = sap.id
                WHERE sap.class_name = ?
                AND o.is_deleted = 0
            """
            params = [class_name]
            
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
            
            # ===== اصلاح =====
            # نسخه قبلی `label` را در حلقه روی ردیف‌ها ست می‌کرد و بعد
            # در حلقه جداگانه‌ای روی کلیدها می‌خواند. نتیجه: همه ردیف‌ها
            # برچسب آخرین ردیف پردازش‌شده را می‌گرفتند (مثلاً همه
            # «شهریور ۱۴۰۵» می‌شدند).
            # حالا label داخل همان دیکشنری گروه ذخیره می‌شود.
            from collections import defaultdict
            grouped = defaultdict(
                lambda: {'label': None, 'positive': 0, 'negative': 0, 'neutral': 0}
            )

            for row in rows:
                date_str = row['observation_date']
                if not date_str:
                    continue

                key, label = self._make_period_key(date_str, period)
                bucket = grouped[key]
                # اولین بار که این کلید دیده می‌شود، برچسبش ثبت شود
                if bucket['label'] is None:
                    bucket['label'] = label

                behavior = row['behavior_type']
                if behavior == 'مثبت':
                    bucket['positive'] += 1
                elif behavior == 'منفی':
                    bucket['negative'] += 1
                else:
                    bucket['neutral'] += 1

            result = []
            for key in sorted(grouped.keys()):
                data = grouped[key]
                total = data['positive'] + data['negative'] + data['neutral']
                result.append({
                    'period': key,
                    'label': data['label'] or key,
                    'positive': data['positive'],
                    'negative': data['negative'],
                    'neutral': data['neutral'],
                    'total': total
                })

            return result
            
        except Exception as e:
            print(f"خطا در دریافت روند مشاهدات کلاس: {e}")
            return []
    
    def _get_month_label(self, date_str):
        """دریافت برچسب ماه از تاریخ"""
        if not date_str or len(date_str) < 7:
            return date_str
        try:
            month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
            parts = date_str.split('/')
            if len(parts) >= 2:
                month = int(parts[1])
                if 1 <= month <= 12:
                    return f"{month_names[month-1]} {parts[0]}"
        except:
            pass
        return date_str

    def _make_period_key(self, date_str, period='monthly'):
        """
        ساخت کلید و برچسب یک بازه زمانی از تاریخ

        Returns:
            tuple: (key, label)

        نکته درباره کلیدهای هفتگی:
        نسخه قبلی کلید را به شکل «1405/07/W1» می‌ساخت. چون مرتب‌سازی
        رشته‌ای است، W10 قبل از W2 می‌آمد. حالا هفته با صفر پر می‌شود
        («W01»، «W02»، ... «W10») تا ترتیب درست شود.
        """
        if not date_str:
            return date_str, date_str

        if period == 'monthly':
            return date_str[:7], self._get_month_label(date_str)

        if period == 'weekly':
            parts = str(date_str).split('/')
            if len(parts) == 3:
                try:
                    day = int(parts[2])
                    week = (day - 1) // 7 + 1
                    return (
                        f"{parts[0]}/{parts[1]}/W{week:02d}",
                        f"هفته {week} {parts[1]}"
                    )
                except (ValueError, IndexError):
                    pass
            return date_str[:7], date_str[:7]

        # daily
        return date_str, date_str

    # ============================================================
    # متدهای گزارش معلم (ادامه از بخش قبلی)
    # ============================================================
    
    def get_by_teacher(self, teacher_id, start_date=None, end_date=None, include_deleted=False):
        """دریافت مشاهدات یک معلم"""
        query = """
            SELECT o.*
            FROM observations o
            WHERE o.staff_id = ?
        """
        params = [teacher_id]
        
        if not include_deleted:
            query += " AND o.is_deleted = 0"
        
        if start_date:
            query += " AND o.observation_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND o.observation_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY o.observation_date DESC"
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_observation(row) for row in rows]
    
    def get_teacher_stats_by_period(self, teacher_id, period='monthly', start_date=None, end_date=None):
        """دریافت آمار معلم در بازه‌های زمانی"""
        try:
            observations = self.get_by_teacher(teacher_id, start_date, end_date)
            
            if not observations:
                return []
            
            # ===== اصلاح: label داخل گروه ذخیره می‌شود (همان باگ نشتی متغیر) =====
            from collections import defaultdict
            grouped = defaultdict(lambda: {
                'label': None, 'positive': 0, 'negative': 0,
                'neutral': 0, 'severities': []
            })

            for obs in observations:
                date_str = obs.observation_date
                if not date_str:
                    continue

                key, label = self._make_period_key(date_str, period)
                bucket = grouped[key]
                if bucket['label'] is None:
                    bucket['label'] = label

                bucket['positive'] += 1 if obs.behavior_type == 'مثبت' else 0
                bucket['negative'] += 1 if obs.behavior_type == 'منفی' else 0
                bucket['neutral'] += 1 if obs.behavior_type == 'خنثی' else 0
                bucket['severities'].append(obs.severity or 1)

            result = []
            for key in sorted(grouped.keys()):
                data = grouped[key]
                total = data['positive'] + data['negative'] + data['neutral']
                avg_severity = (
                    sum(data['severities']) / len(data['severities'])
                    if data['severities'] else 0
                )

                result.append({
                    'period': key,
                    'label': data['label'] or key,
                    'positive': data['positive'],
                    'negative': data['negative'],
                    'neutral': data['neutral'],
                    'total': total,
                    'avg_severity': round(avg_severity, 1)
                })

            return result
            
        except Exception as e:
            print(f"خطا در دریافت آمار معلم: {e}")
            return []

    # ============================================================
    # متدهای تحلیلی برای داشبورد
    # ============================================================

    def get_observations_distribution_by_type(self, start_date=None, end_date=None):
        """دریافت توزیع مشاهدات بر اساس نوع رفتار"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN behavior_type = 'مثبت' THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN behavior_type = 'منفی' THEN 1 ELSE 0 END) as negative,
                    SUM(CASE WHEN behavior_type = 'خنثی' THEN 1 ELSE 0 END) as neutral
                FROM observations
                WHERE is_deleted = 0
            """
            params = []

            if start_date:
                query += " AND observation_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND observation_date <= ?"
                params.append(end_date)

            cursor.execute(query, tuple(params))  # اصلاح: None می‌داد «parameters are of unsupported type»
            row = cursor.fetchone()

            total = row['total'] if row else 0
            positive = row['positive'] if row else 0
            negative = row['negative'] if row else 0
            neutral = row['neutral'] if row else 0

            return {
                'positive': positive,
                'negative': negative,
                'neutral': neutral,
                'total': total,
                'positive_percentage': round((positive / total * 100), 1) if total > 0 else 0,
                'negative_percentage': round((negative / total * 100), 1) if total > 0 else 0,
                'neutral_percentage': round((neutral / total * 100), 1) if total > 0 else 0
            }

        except Exception as e:
            print(f"خطا در دریافت توزیع مشاهدات: {e}")
            return {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0,
                    'positive_percentage': 0, 'negative_percentage': 0, 'neutral_percentage': 0}

    def get_observations_distribution_by_location(self, start_date=None, end_date=None, limit=10):
        """دریافت توزیع مشاهدات بر اساس محیط"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT location, COUNT(*) as count
                FROM observations
                WHERE is_deleted = 0 AND location IS NOT NULL AND location != ''
            """
            params = []

            if start_date:
                query += " AND observation_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND observation_date <= ?"
                params.append(end_date)

            query += " GROUP BY location ORDER BY count DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            total = sum(row['count'] for row in rows) if rows else 0

            result = []
            for row in rows:
                result.append({
                    'location': row['location'],
                    'count': row['count'],
                    'percentage': round((row['count'] / total * 100), 1) if total > 0 else 0
                })

            return result

        except Exception as e:
            print(f"خطا در دریافت توزیع مشاهدات بر اساس محیط: {e}")
            return []

    def get_observations_by_time_period(self, period='monthly', start_date=None, end_date=None, limit=12):
        """دریافت مشاهدات در بازه‌های زمانی"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT observation_date, behavior_type
                FROM observations
                WHERE is_deleted = 0
            """
            params = []

            if start_date:
                query += " AND observation_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND observation_date <= ?"
                params.append(end_date)

            cursor.execute(query, tuple(params))  # اصلاح: None می‌داد «parameters are of unsupported type»
            rows = cursor.fetchall()

            if not rows:
                return []

            # ===== اصلاح =====
            # محل چهارم باگ نشتی متغیر label (در get_observations_by_time_period).
            # این یکی در بازبینی اول از قلم افتاده بود؛ همان الگو،
            # همان نتیجه: همه ردیف‌ها برچسب آخرین ردیف را می‌گرفتند.
            from collections import defaultdict
            grouped = defaultdict(
                lambda: {'label': None, 'positive': 0, 'negative': 0, 'neutral': 0}
            )

            for row in rows:
                date_str = row['observation_date']
                if not date_str:
                    continue

                key, label = self._make_period_key(date_str, period)
                bucket = grouped[key]
                if bucket['label'] is None:
                    bucket['label'] = label

                behavior = row['behavior_type']
                if behavior == 'مثبت':
                    bucket['positive'] += 1
                elif behavior == 'منفی':
                    bucket['negative'] += 1
                else:
                    bucket['neutral'] += 1

            sorted_keys = sorted(grouped.keys())

            result = []
            for key in sorted_keys[-limit:]:
                data = grouped[key]
                total = data['positive'] + data['negative'] + data['neutral']
                result.append({
                    'period': key,
                    'label': data['label'] or key,
                    'total': total,
                    'positive': data['positive'],
                    'negative': data['negative'],
                    'neutral': data['neutral']
                })

            return result

        except Exception as e:
            print(f"خطا در دریافت مشاهدات در بازه‌های زمانی: {e}")
            return []

    def get_observations_by_competency(self, start_date=None, end_date=None, limit=10):
        """دریافت مشاهدات گروه‌بندی شده بر اساس شایستگی"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT o.competency_id, c.title as competency_name, 
                       COUNT(*) as count, AVG(o.severity) as avg_severity
                FROM observations o
                LEFT JOIN competencies c ON o.competency_id = c.id
                WHERE o.is_deleted = 0 AND o.competency_id IS NOT NULL
            """
            params = []

            if start_date:
                query += " AND o.observation_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND o.observation_date <= ?"
                params.append(end_date)

            query += " GROUP BY o.competency_id ORDER BY count DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    'competency_id': row['competency_id'],
                    'competency_name': row['competency_name'] or f"شایستگی {row['competency_id']}",
                    'count': row['count'],
                    'avg_severity': round(row['avg_severity'], 1) if row['avg_severity'] else 0
                })

            return result

        except Exception as e:
            print(f"خطا در دریافت مشاهدات بر اساس شایستگی: {e}")
            return []

    def get_daily_observation_summary(self, days=30):
        """دریافت خلاصه روزانه مشاهدات"""
        try:
            import jdatetime
            from datetime import timedelta

            conn = self.db.get_connection()
            cursor = conn.cursor()

            # ===== اصلاح (بازرسی دوم) =====
            # days=None (اگر صریحاً پاس داده شود) باعث
            #     TypeError: unsupported type for timedelta days component: NoneType
            # می‌شد و چون کل متد داخل try است، خطا فقط چاپ و نتیجه خالی
            # برمی‌گشت («خلاصه روزانه» بی‌صدا خالی می‌ماند).
            if not days:
                days = 30

            today = jdatetime.date.today()
            start_date = today - timedelta(days=days)
            start_date_str = f"{start_date.year}/{start_date.month:02d}/{start_date.day:02d}"

            query = """
                SELECT observation_date, 
                       COUNT(*) as total,
                       SUM(CASE WHEN behavior_type = 'مثبت' THEN 1 ELSE 0 END) as positive,
                       SUM(CASE WHEN behavior_type = 'منفی' THEN 1 ELSE 0 END) as negative
                FROM observations
                WHERE is_deleted = 0
                AND observation_date >= ?
                GROUP BY observation_date
                ORDER BY observation_date DESC
            """

            cursor.execute(query, (start_date_str,))
            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    'date': row['observation_date'],
                    'total': row['total'],
                    'positive': row['positive'] or 0,
                    'negative': row['negative'] or 0
                })

            return result

        except Exception as e:
            print(f"خطا در دریافت خلاصه روزانه مشاهدات: {e}")
            return []

    # ============================================================
    # متدهای تحلیل برای پیشنهادات (جدید)
    # ============================================================

    def get_weak_competencies_for_student(self, profile_id, limit=3):
        """
        دریافت شایستگی‌های ضعیف یک دانش‌آموز برای پیشنهاد مداخله

        Args:
            profile_id: شناسه پرونده دانش‌آموز
            limit: تعداد محدود

        Returns:
            list: [
                {
                    'competency_id': int,
                    'competency_name': str,
                    'avg_severity': float,
                    'count': int,
                    'observation_ids': list
                }
            ]
        """
        try:
            observations = self.get_by_student_profile(profile_id)
            
            if not observations:
                return []
            
            # گروه‌بندی بر اساس شایستگی
            comp_stats = {}
            for obs in observations:
                if obs.competency_id:
                    if obs.competency_id not in comp_stats:
                        comp_stats[obs.competency_id] = {
                            'count': 0,
                            'total_severity': 0,
                            'negative_count': 0,
                            'observation_ids': []
                        }
                    comp_stats[obs.competency_id]['count'] += 1
                    comp_stats[obs.competency_id]['total_severity'] += obs.severity or 1
                    if obs.behavior_type == 'منفی':
                        comp_stats[obs.competency_id]['negative_count'] += 1
                    comp_stats[obs.competency_id]['observation_ids'].append(obs.id)
            
            # ===== اصلاح مهم: معنای «شایستگی ضعیف» =====
            #
            # نسخه قبلی دو مشکل داشت:
            #
            # ۱) فیلتر `avg_severity <= 2.0`
            #    در PARTO شدت (severity) یعنی «میزان برجستگی مشاهده»
            #    (۱=خیلی کم تا ۵=خیلی زیاد) و جهت‌دار نیست؛ جهت رفتار در
            #    `behavior_type` (مثبت/منفی/خنثی) ذخیره می‌شود.
            #    پس این فیلتر دقیقاً شایستگی‌هایی را که بیشترین مشکل
            #    جدی را دارند حذف می‌کرد و فقط مشکلات خفیف را نگه
            #    می‌داشت. نتیجه: «شایستگی‌های ضعیف» در واقع
            #    «شایستگی‌های بی‌مشکل» بودند.
            #
            # ۲) مرتب‌سازی صعودی + [:limit]
            #    `sort(key=avg_severity)` صعودی است و بعد اولین `limit`
            #    مورد گرفته می‌شد، یعنی کم‌شدت‌ترین‌ها برمی‌گشتند.
            #
            # حالا: شایستگی ضعیف = شایستگی با بیشترین مشاهده منفی،
            # و رتبه‌بندی بر اساس امتیاز ترکیبی (تعداد منفی × شدت).
            weak_comps = []
            for comp_id, stats in comp_stats.items():
                if stats['count'] < 2:
                    continue

                avg_severity = stats['total_severity'] / stats['count']
                negative_count = stats['negative_count']

                # فقط شایستگی‌هایی که واقعاً مشاهده منفی دارند
                if negative_count == 0:
                    continue

                weak_comps.append({
                    'competency_id': comp_id,
                    'avg_severity': round(avg_severity, 1),
                    'count': stats['count'],
                    'negative_count': negative_count,
                    # امتیاز وخامت: هم حجم، هم شدت
                    'impact_score': round(negative_count * avg_severity, 2),
                    'observation_ids': stats['observation_ids']
                })

            # وخیم‌ترین شایستگی اول
            weak_comps.sort(key=lambda x: x['impact_score'], reverse=True)
            
            # دریافت نام شایستگی‌ها
            for comp in weak_comps[:limit]:
                competency = self._get_competency_name(comp['competency_id'])
                comp['competency_name'] = competency
            
            return weak_comps[:limit]
            
        except Exception as e:
            print(f"خطا در دریافت شایستگی‌های ضعیف: {e}")
            return []

    def get_strong_competencies_for_student(self, profile_id, limit=3):
        """
        دریافت شایستگی‌های قوی یک دانش‌آموز برای تشویق

        Args:
            profile_id: شناسه پرونده دانش‌آموز
            limit: تعداد محدود

        Returns:
            list: [
                {
                    'competency_id': int,
                    'competency_name': str,
                    'avg_severity': float,
                    'count': int
                }
            ]
        """
        try:
            observations = self.get_by_student_profile(profile_id)
            
            if not observations:
                return []
            
            # گروه‌بندی بر اساس شایستگی
            comp_stats = {}
            for obs in observations:
                if obs.competency_id:
                    if obs.competency_id not in comp_stats:
                        comp_stats[obs.competency_id] = {
                            'count': 0,
                            'total_severity': 0
                        }
                    comp_stats[obs.competency_id]['count'] += 1
                    comp_stats[obs.competency_id]['total_severity'] += obs.severity or 1
            
            # محاسبه میانگین و فیلتر شایستگی‌های قوی (میانگین شدت >= 3.5 و حداقل 2 مشاهده)
            strong_comps = []
            for comp_id, stats in comp_stats.items():
                if stats['count'] >= 2:
                    avg_severity = stats['total_severity'] / stats['count']
                    if avg_severity >= 3.5:
                        strong_comps.append({
                            'competency_id': comp_id,
                            'avg_severity': round(avg_severity, 1),
                            'count': stats['count']
                        })
            
            # مرتب‌سازی بر اساس میانگین شدت (قوی‌ترین اول)
            strong_comps.sort(key=lambda x: x['avg_severity'], reverse=True)
            
            # دریافت نام شایستگی‌ها
            for comp in strong_comps[:limit]:
                competency = self._get_competency_name(comp['competency_id'])
                comp['competency_name'] = competency
            
            return strong_comps[:limit]
            
        except Exception as e:
            print(f"خطا در دریافت شایستگی‌های قوی: {e}")
            return []

    def get_recent_observations_for_student(self, profile_id, limit=5):
        """
        دریافت آخرین مشاهدات یک دانش‌آموز

        Args:
            profile_id: شناسه پرونده دانش‌آموز
            limit: تعداد محدود

        Returns:
            list: لیست مشاهدات
        """
        try:
            return self.get_by_student_profile(profile_id, limit=limit)
        except Exception as e:
            print(f"خطا در دریافت آخرین مشاهدات: {e}")
            return []

    def get_observation_patterns_for_student(self, profile_id):
        """
        تشخیص الگوهای رفتاری یک دانش‌آموز

        Args:
            profile_id: شناسه پرونده دانش‌آموز

        Returns:
            dict: {
                'most_common_location': str,
                'most_common_behavior_type': str,
                'avg_severity': float,
                'total_observations': int,
                'positive_ratio': float,
                'negative_ratio': float,
                'trend': str  # 'improving', 'declining', 'stable', 'insufficient'
            }
        """
        try:
            observations = self.get_by_student_profile(profile_id)
            
            if not observations:
                return {
                    'most_common_location': None,
                    'most_common_behavior_type': None,
                    'avg_severity': 0,
                    'total_observations': 0,
                    'positive_ratio': 0,
                    'negative_ratio': 0,
                    'trend': 'insufficient'
                }
            
            # محاسبه آمار
            total = len(observations)
            positive = sum(1 for o in observations if o.behavior_type == 'مثبت')
            negative = sum(1 for o in observations if o.behavior_type == 'منفی')
            
            # تشخیص مکان رایج
            locations = {}
            for obs in observations:
                if obs.location:
                    locations[obs.location] = locations.get(obs.location, 0) + 1
            most_common_location = max(locations.items(), key=lambda x: x[1])[0] if locations else None
            
            # تشخیص نوع رفتار رایج
            types = {'مثبت': positive, 'منفی': negative, 'خنثی': total - positive - negative}
            most_common_type = max(types.items(), key=lambda x: x[1])[0] if total > 0 else None
            
            # میانگین شدت
            severities = [o.severity or 1 for o in observations]
            avg_severity = sum(severities) / len(severities) if severities else 0
            
            # تشخیص روند
            if len(observations) >= 3:
                # ===== اصلاح مهم: جهت مقایسه =====
                # کوئری بالا `ORDER BY observation_date DESC` است، پس
                # observations از جدیدترین به قدیمی‌ترین چیده شده.
                # نسخه قبلی:
                #     first_third = observations[:n]  ← جدیدترین‌ها
                #     last_third  = observations[2n:] ← قدیمی‌ترین‌ها
                # و شرط `if last_ratio > first_ratio: improving` یعنی
                # «اگر گذشته بهتر از امروز بود → در حال بهبود».
                # دقیقاً برعکس. دانش‌آموزی که بدتر شده «improving»
                # می‌گرفت و دانش‌آموز در حال بهبود «declining».
                #
                # حالا نام‌ها با معنا جور شده و مقایسه به شکل
                # (امروز نسبت به گذشته) انجام می‌شود.
                third = max(len(observations) // 3, 1)
                recent_third = observations[:third]    # جدیدترین (چون DESC است)
                older_third = observations[-third:]    # قدیمی‌ترین

                recent_positive = sum(1 for o in recent_third if o.behavior_type == 'مثبت')
                older_positive = sum(1 for o in older_third if o.behavior_type == 'مثبت')

                recent_ratio = recent_positive / len(recent_third) if recent_third else 0
                older_ratio = older_positive / len(older_third) if older_third else 0

                if recent_ratio > older_ratio + 0.2:
                    trend = 'improving'      # امروز بهتر از گذشته است
                elif recent_ratio < older_ratio - 0.2:
                    trend = 'declining'      # امروز بدتر از گذشته است
                else:
                    trend = 'stable'
            else:
                trend = 'insufficient'
            
            return {
                'most_common_location': most_common_location,
                'most_common_behavior_type': most_common_type,
                'avg_severity': round(avg_severity, 1),
                'total_observations': total,
                'positive_ratio': round(positive / total * 100, 1) if total > 0 else 0,
                'negative_ratio': round(negative / total * 100, 1) if total > 0 else 0,
                'trend': trend
            }
            
        except Exception as e:
            print(f"خطا در تشخیص الگوهای رفتاری: {e}")
            return {
                'most_common_location': None,
                'most_common_behavior_type': None,
                'avg_severity': 0,
                'total_observations': 0,
                'positive_ratio': 0,
                'negative_ratio': 0,
                'trend': 'insufficient'
            }

    def _get_competency_name(self, competency_id):
        """دریافت نام شایستگی"""
        try:
            from dal.competency_dal import CompetencyDAL
            comp_dal = CompetencyDAL()
            comp = comp_dal.get_by_id(competency_id)
            return comp.title if comp else f"شایستگی {competency_id}"
        except:
            return f"شایستگی {competency_id}"

    def _row_to_observation(self, row):
        """تبدیل ردیف دیتابیس به مدل Observation"""
        observation = Observation()
        observation.id = row['id']
        observation.student_profile_id = row['student_profile_id']
        observation.staff_id = row['staff_id']
        observation.competency_id = row['competency_id']

        # ===== اصلاح مهم: ساختار سه‌لایه =====
        # ستون‌های indicator_id و observable_behavior_id توسط
        # migration_v7 به جدول observations اضافه شده‌اند و مدل
        # Observation هم این دو فیلد را دارد، ولی این DAL هیچ‌وقت
        # آن‌ها را نه می‌نوشت و نه می‌خواند.
        #
        # نتیجه واقعی: فرم ثبت مشاهده (views/dialogs/observation_form.py)
        # انتخاب کاربر از درخت «شایستگی ← شاخص ← رفتار قابل مشاهده» را
        # داخل data می‌فرستاد (کلیدهای indicator_id و
        # observable_behavior_id) ولی در دیتابیس NULL ذخیره می‌شد. وقتی
        # کاربر همان مشاهده را برای ویرایش باز می‌کرد، کد سعی می‌کرد
        # انتخاب قبلی را از obs.indicator_id برگرداند و همیشه None
        # می‌گرفت ⇒ انتخاب کاربر بی‌صدا از بین می‌رفت.
        #
        # از getattr روی row.keys() استفاده می‌شود تا اگر دیتابیس قدیمی
        # هنوز این ستون‌ها را نداشت (قبل از ترمیم ساختار) برنامه crash
        # نکند.
        try:
            available = set(row.keys())
        except Exception:
            available = set()
        observation.indicator_id = (
            row['indicator_id'] if 'indicator_id' in available else None
        )
        observation.observable_behavior_id = (
            row['observable_behavior_id']
            if 'observable_behavior_id' in available else None
        )

        observation.observation_date = row['observation_date']
        observation.location = row['location']
        observation.description = row['description']
        observation.antecedent = row['antecedent']
        observation.behavior = row['behavior']
        observation.consequence = row['consequence']
        observation.behavior_type = row['behavior_type']
        observation.severity = row['severity'] or 1
        observation.tags = row['tags']
        observation.created_at = row['created_at']
        observation.updated_at = row['updated_at']
        
        # فیلدهای Soft Delete
        observation.is_deleted = row['is_deleted']
        observation.deleted_at = row['deleted_at']
        observation.deleted_by = row['deleted_by']
        
        return observation

    # ============================================================
    # جست‌وجوی متن آزاد
    # ============================================================
    # ===== اصلاح (باگ گزارش‌شده در بازرسی دوم) =====
    # ObservationService.search_observations / search_observations_by_student / search_observations_by_teacher
    # سه متد این DAL را صدا می‌زدند که هیچ‌کدام وجود نداشتند:
    #
    #     AttributeError: 'ObservationDAL' object has no attribute 'search'
    #
    # سرویس آن را به ServiceError تبدیل می‌کرد و در نتیجه کادر جست‌وجوی
    # صفحه مشاهدات (views/pages/observations_page.py:380-388) همیشه با پیام
    # «مشکل در جستجو: ...» شکست می‌خورد. یعنی جست‌وجو در این صفحه
    # از ابتدا کار نمی‌کرد و هیچ داده‌ای برنمی‌گشت.
    #
    # حالا هر سه متد پیاده‌سازی شده‌اند. نکته‌ها:
    #   - «بر اساس معلم» یعنی observations.staff_id (همان معنایی که
    #     ObservationService.get_observations_by_teacher در فیلتر پایتونی استفاده می‌کند).
    #   - «بر اساس دانش‌آموز» با JOIN روی پرونده سالانه انجام می‌شود
    #     (همان الگوی get_by_student).
    #   - کاراکترهای ویژه LIKE فرار داده می‌شوند تا جست‌وجوی «٪» یا «_»
    #     به‌جای wildcard، خودِ همان نویسه را پیدا کند.
    #   - رکوردهای حذف منطقی‌شده برنمی‌گردند (مگر include_deleted=True).

    @staticmethod
    def _escape_like(text):
        """ساخت الگوی LIKE امن (فرار کاراکترهای ویژه) برای جست‌وجوی متن آزاد"""
        s = '' if text is None else str(text)
        s = s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        return '%' + s + '%'

    _LIKE = "LIKE ? ESCAPE '\\'"
    _SEARCH_COLUMNS = ('description', 'behavior', 'location', 'antecedent',
                       'consequence', 'tags', 'behavior_type')

    def search(self, search_term, limit=None, include_deleted=False):
        """جست‌وجوی متن آزاد در همه مشاهدات"""
        return self._search_text(search_term, limit=limit, include_deleted=include_deleted)

    def search_by_student(self, student_id, search_term, limit=None, include_deleted=False):
        """جست‌وجوی متن آزاد در مشاهدات یک دانش‌آموز"""
        return self._search_text(search_term, student_id=student_id, limit=limit,
                                 include_deleted=include_deleted)

    def search_by_teacher(self, teacher_id, search_term, limit=None, include_deleted=False):
        """جست‌وجوی متن آزاد در مشاهدات ثبت‌شده توسط یک معلم"""
        return self._search_text(search_term, teacher_id=teacher_id, limit=limit,
                                 include_deleted=include_deleted)

    def _search_text(self, search_term, student_id=None, teacher_id=None,
                     limit=None, include_deleted=False):
        """پیاده‌سازی مشترک جست‌وجو (ساختار کوئری همانند get_by_student)"""
        if search_term is None or not str(search_term).strip():
            return []

        term = self._escape_like(search_term)
        like = " OR ".join("o.%s %s" % (c, self._LIKE) for c in self._SEARCH_COLUMNS)

        joins = ""
        where = ["(%s)" % like]
        params = [term] * len(self._SEARCH_COLUMNS)

        if student_id is not None:
            joins += " JOIN student_academic_profiles sap ON o.student_profile_id = sap.id"
            where.append("sap.student_id = ?")
            params.append(student_id)

        if teacher_id is not None:
            where.append("o.staff_id = ?")
            params.append(teacher_id)

        if not include_deleted:
            where.append("o.is_deleted = 0")

        query = "SELECT o.* FROM observations o%s WHERE %s" % (joins, " AND ".join(where))
        query += " ORDER BY o.observation_date DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_observation(row) for row in rows]
