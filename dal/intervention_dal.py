"""
لایه دسترسی به داده مداخلات - با Soft Delete یکپارچه
با متدهای تحلیلی برای داشبورد و پیشنهادات
"""

import sqlite3

from database.connection import DatabaseConnection
from models.intervention import Intervention
from utils.batch_query import id_chunks, placeholders
from utils.logger import get_logger
from utils.pagination import normalize_limit_offset
from utils.security import AccessControl, Permission
from utils.time_utils import utc_now_iso

logger = get_logger(__name__)


class InterventionDAL:
    """عملیات CRUD برای مداخلات با Soft Delete یکپارچه"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, intervention):
        """ایجاد مداخله جدید"""
        # مرز مجوز backend (دور نوزدهم — سند ممیزی مدیر پروژه)
        AccessControl.require_permission(
            Permission.CREATE_INTERVENTION.value, action="InterventionDAL.create")
        # مرز Scope (دور نوزدهم — مرحلهٔ ۳، DD-6): معلم فقط برای
        # دانش‌آموزهای منتسب‌شدهٔ خودش می‌تواند مداخله بسازد.
        AccessControl.require_profile_scope(
            intervention.student_profile_id, action="InterventionDAL.create")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO interventions (
                student_profile_id, staff_id, observation_id,
                type, date, description, goal, status, result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            intervention.student_profile_id,
            intervention.staff_id,
            intervention.observation_id,
            intervention.type,
            intervention.date,
            intervention.description,
            intervention.goal,
            intervention.status,
            intervention.result
        ))
        
        self.db.commit()
        intervention.id = cursor.lastrowid
        return intervention
    
    def get_by_id(self, intervention_id, include_deleted=False):
        """دریافت مداخله با شناسه"""
        query = "SELECT * FROM interventions WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (intervention_id,))
        row = cursor.fetchone()
        if row:
            intervention = self._row_to_intervention(row)
            # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۳، SEC-IDOR-01، DD-6):
            # پیش از این، خواندن مستقیم با ID هیچ بررسی «آیا این دانش‌آموز
            # در Scope کاربر جاری است؟» نداشت — معلم می‌توانست با حدس‌زدن
            # شناسه، مداخلهٔ دانش‌آموزِ معلم دیگری را بخواند. رد Scope
            # همیشه صریح است (PermissionDeniedError)، نه پنهان به‌شکل
            # NotFound (تصمیم صریح مدیر پروژه در DD-6).
            AccessControl.require_profile_scope(
                intervention.student_profile_id, action="InterventionDAL.get_by_id")
            return intervention
        return None
    
    def get_by_ids(self, intervention_ids, include_deleted=False):
        """
        دریافت چند مداخله با «یک» کوئری (بازرسی چهاردهم: رفع N+1)

        معناشناسی مثل get_by_id (پیش‌فرض: حذف‌شده‌ها برنمی‌گردند).

        Returns:
            dict: {intervention_id: Intervention}
        """
        result = {}
        for chunk in id_chunks(intervention_ids):
            query = f"SELECT * FROM interventions WHERE id IN ({placeholders(len(chunk))})"
            if not include_deleted:
                query += " AND is_deleted = 0"
            cursor = self.db.execute_query(query, tuple(chunk))
            for row in cursor.fetchall():
                intervention = self._row_to_intervention(row)
                result[intervention.id] = intervention
        return result

    def get_by_student_profile(self, profile_id, limit=None, include_deleted=False):
        """دریافت مداخلات یک پرونده دانش‌آموز - فقط رکوردهای موجود"""
        query = "SELECT * FROM interventions WHERE student_profile_id = ?"
        params = [profile_id]
        
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY date DESC"
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_intervention(row) for row in rows]
    
    def get_by_student(self, student_id, academic_year_id=None, include_deleted=False):
        """دریافت مداخلات یک دانش‌آموز (با فیلتر سال تحصیلی)"""
        if academic_year_id:
            query = """
                SELECT i.* FROM interventions i
                JOIN student_academic_profiles sap ON i.student_profile_id = sap.id
                WHERE sap.student_id = ? AND sap.academic_year_id = ?
            """
            params = [student_id, academic_year_id]
        else:
            query = """
                SELECT i.* FROM interventions i
                JOIN student_academic_profiles sap ON i.student_profile_id = sap.id
                WHERE sap.student_id = ?
            """
            params = [student_id]
        
        if not include_deleted:
            query += " AND i.is_deleted = 0"
        
        query += " ORDER BY i.date DESC"
        
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_intervention(row) for row in rows]
    
    def get_by_observation(self, observation_id, include_deleted=False):
        """دریافت مداخلات مرتبط با یک مشاهده - فقط رکوردهای موجود"""
        query = "SELECT * FROM interventions WHERE observation_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY date DESC"
        
        cursor = self.db.execute_query(query, (observation_id,))
        rows = cursor.fetchall()
        return [self._row_to_intervention(row) for row in rows]
    
    def get_all(self, limit=None, include_deleted=False, academic_year_id=None,
                staff_id=None, offset=None):
        """
        دریافت همه مداخلات با فیلتر سال/معلم قبل از LIMIT.

        (دور نوزدهم، مرحلهٔ ۶) پارامتر offset سازگار با گذشته اضافه شده
        (پیش‌فرض None یعنی بدون OFFSET)؛ limit=None هم مثل قبل «بدون سقف»
        است. این DAL هنوز کنترل صفحه‌بندی‌ای در UI ندارد.
        """
        limit, offset = normalize_limit_offset(limit, offset)

        query = "SELECT i.* FROM interventions i"
        joins = []
        where = []
        params = []
        if academic_year_id is not None:
            joins.append("JOIN student_academic_profiles sap ON i.student_profile_id = sap.id")
            where.append("sap.academic_year_id = ?")
            params.append(academic_year_id)
            # (دور نوزدهم، مرحلهٔ ۷ — رفع باگ) پروندهٔ حذف‌شده در فیلتر سال
            # نباید شمرده شود؛ هم‌راستا با profile_dal.get_by_ids در همه‌جا.
            where.append("sap.is_deleted = 0")
        if not include_deleted:
            where.append("i.is_deleted = 0")
        if staff_id is not None:
            where.append("i.staff_id = ?")
            params.append(staff_id)
        if joins:
            query += " " + " ".join(joins)
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY i.date DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_intervention(row) for row in rows]

    def count_all(self, include_deleted=False, academic_year_id=None, staff_id=None):
        """شمارش مداخلات با همان فیلترهای get_all (بدون LIMIT/OFFSET) — مرحلهٔ ۶"""
        query = "SELECT COUNT(*) as cnt FROM interventions i"
        joins = []
        where = []
        params = []
        if academic_year_id is not None:
            joins.append("JOIN student_academic_profiles sap ON i.student_profile_id = sap.id")
            where.append("sap.academic_year_id = ?")
            params.append(academic_year_id)
            where.append("sap.is_deleted = 0")
        if not include_deleted:
            where.append("i.is_deleted = 0")
        if staff_id is not None:
            where.append("i.staff_id = ?")
            params.append(staff_id)
        if joins:
            query += " " + " ".join(joins)
        if where:
            query += " WHERE " + " AND ".join(where)
        cursor = self.db.execute_query(query, params)
        row = cursor.fetchone()
        return row["cnt"] if row else 0
    
    def get_active(self, include_deleted=False):
        """دریافت مداخلات فعال (برنامه‌ریزی شده یا در حال اجرا) - فقط رکوردهای موجود"""
        query = """
            SELECT * FROM interventions 
            WHERE (status = 'planned' OR status = 'in_progress')
        """
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY date DESC"
        
        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        return [self._row_to_intervention(row) for row in rows]
    
    def update(self, intervention):
        """به‌روزرسانی مداخله - فقط رکوردهای موجود"""
        # مرز مجوز backend (دور نوزدهم)
        AccessControl.require_permission(
            Permission.EDIT_INTERVENTION.value, action="InterventionDAL.update")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT student_profile_id FROM interventions WHERE id = ? AND is_deleted = 0",
            (intervention.id,)
        )
        existing = cursor.fetchone()
        if not existing:
            raise Exception("رکورد مورد نظر یافت نشد یا حذف شده است.")

        # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۳، DD-6): هم رکورد موجود
        # (قبل از تغییر) و هم پروندهٔ مقصد (اگر جابه‌جا شده باشد) باید
        # در Scope کاربر جاری باشند — وگرنه معلم می‌توانست مداخلهٔ
        # دانش‌آموز خودش را به دانش‌آموز خارج از Scope منتقل کند یا
        # برعکس، رکورد دانش‌آموز دیگری را با ID مستقیم ویرایش کند.
        AccessControl.require_profile_scope(
            existing["student_profile_id"], action="InterventionDAL.update")
        if intervention.student_profile_id != existing["student_profile_id"]:
            AccessControl.require_profile_scope(
                intervention.student_profile_id,
                action="InterventionDAL.update(new_profile)")
        
        cursor.execute("""
            UPDATE interventions SET
                student_profile_id = ?, staff_id = ?, observation_id = ?,
                type = ?, date = ?, description = ?, goal = ?,
                status = ?, result = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            intervention.student_profile_id,
            intervention.staff_id,
            intervention.observation_id,
            intervention.type,
            intervention.date,
            intervention.description,
            intervention.goal,
            intervention.status,
            intervention.result,
            intervention.id
        ))
        
        self.db.commit()
        return intervention
    
    def update_status(self, intervention_id, new_status):
        """به‌روزرسانی وضعیت مداخله - فقط رکوردهای موجود"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE interventions SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (new_status, intervention_id))
        
        self.db.commit()
        return True
    
    def delete(self, intervention_id, user_id=None):
        """حذف منطقی مداخله - فقط رکوردهای موجود"""
        # مرز مجوز backend (BUG-NAV-03): حذف مداخله = DELETE_INTERVENTION
        AccessControl.require_permission(
            Permission.DELETE_INTERVENTION.value, action="intervention_dal.delete")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT student_profile_id FROM interventions WHERE id = ? AND is_deleted = 0",
            (intervention_id,)
        )
        existing = cursor.fetchone()
        if not existing:
            return False
        # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۳)
        AccessControl.require_profile_scope(
            existing["student_profile_id"], action="InterventionDAL.delete")
        
        now = utc_now_iso()
        cursor.execute("""
            UPDATE interventions SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (now, user_id, intervention_id))
        
        self.db.commit()
        return True
    
    def restore(self, intervention_id, user_id=None):
        """بازیابی مداخله حذف شده - فقط رکوردهای حذف شده"""
        # مرز مجوز backend (BUG-NAV-03): بازیابی = همان مجوز حذف
        AccessControl.require_permission(
            Permission.DELETE_INTERVENTION.value, action="intervention_dal.restore")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT student_profile_id FROM interventions WHERE id = ? AND is_deleted = 1",
            (intervention_id,)
        )
        existing = cursor.fetchone()
        if not existing:
            return False
        # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۳)
        AccessControl.require_profile_scope(
            existing["student_profile_id"], action="InterventionDAL.restore")

        # مرحلهٔ ۸ (RESTORE-EDGE-01): پروندهٔ سالانهٔ والد باید هنوز
        # وجود داشته و حذف نشده باشد.
        parent = cursor.execute(
            "SELECT 1 FROM student_academic_profiles WHERE id = ? AND is_deleted = 0",
            (existing["student_profile_id"],)
        ).fetchone()
        if not parent:
            raise ValueError(
                "پروندهٔ سالانهٔ مربوط به این مداخله حذف شده یا وجود "
                "ندارد؛ پیش از بازیابیِ مداخله باید ابتدا خودِ پرونده "
                "را بازگردانی کنید."
            )

        cursor.execute("""
            UPDATE interventions SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 1
        """, (intervention_id,))
        
        self.db.commit()
        return True
    
    def get_deleted(self, limit=None):
        """دریافت لیست رکوردهای حذف شده"""
        query = "SELECT * FROM interventions WHERE is_deleted = 1 ORDER BY deleted_at DESC"
        params = []
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, tuple(params) if params else None)
        rows = cursor.fetchall()
        return [self._row_to_intervention(row) for row in rows]
    
    def permanent_delete(self, intervention_id):
        """
        حذف فیزیکی مداخله - فقط برای موارد خاص استفاده شود

        (دور نوزدهم، مرحلهٔ ۸ — SEC-HARD-DELETE-01) قبلاً بدون هیچ
        بررسیِ Permission یا وابستگی، ردیف مستقیماً DELETE می‌شد. چون
        `followups.intervention_id` با ON DELETE CASCADE به
        interventions.id وصل است، این کار عملاً تمام تاریخچهٔ پیگیریِ
        این مداخله را هم برای همیشه پاک می‌کرد. حالا مثل
        staff_dal.permanent_delete: Permission بررسی می‌شود و اگر
        پیگیری‌ای وابسته باشد، حذف رد می‌شود.
        """
        AccessControl.require_permission(
            Permission.DELETE_INTERVENTION.value, action="InterventionDAL.permanent_delete")

        conn = self.db.get_connection()
        cursor = conn.cursor()

        if cursor.execute(
            "SELECT 1 FROM interventions WHERE id = ?", (intervention_id,)
        ).fetchone() is None:
            return False

        followup_count = cursor.execute(
            "SELECT COUNT(*) FROM followups WHERE intervention_id = ?",
            (intervention_id,)
        ).fetchone()[0]
        if followup_count:
            raise ValueError(
                f"این مداخله دارای {followup_count} پیگیری وابسته است؛ "
                "حذف دائم این تاریخچه را برای همیشه نابود می‌کند. "
                "به‌جای آن از حذف عادی استفاده کنید."
            )

        cursor.execute(
            "DELETE FROM interventions WHERE id = ?",
            (intervention_id,)
        )
        affected = cursor.rowcount
        self.db.commit()
        return affected > 0
    
    def _row_to_intervention(self, row):
        """تبدیل ردیف دیتابیس به مدل Intervention"""
        intervention = Intervention()
        intervention.id = row['id']
        intervention.student_profile_id = row['student_profile_id']
        intervention.staff_id = row['staff_id']
        intervention.observation_id = row['observation_id']
        intervention.type = row['type']
        intervention.date = row['date']
        intervention.description = row['description']
        intervention.goal = row['goal']
        intervention.status = row['status']
        intervention.result = row['result']
        intervention.created_at = row['created_at']
        intervention.updated_at = row['updated_at']
        
        # فیلدهای Soft Delete
        intervention.is_deleted = row['is_deleted']
        intervention.deleted_at = row['deleted_at']
        intervention.deleted_by = row['deleted_by']
        
        return intervention

    # ============================================================
    # متدهای تحلیلی برای داشبورد
    # ============================================================

    def get_interventions_distribution_by_status(self, start_date=None, end_date=None, staff_id=None):
        """دریافت توزیع مداخلات بر اساس وضعیت

        Args:
            staff_id: اگر داده شود، فقط مداخلاتِ ثبت‌شدهٔ همین معلم شمرده
                می‌شود (فیلتر انتخاب معلم در داشبورد).
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'planned' THEN 1 ELSE 0 END) as planned,
                    SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                    SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                FROM interventions
                WHERE is_deleted = 0
            """
            params = []

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            if staff_id:
                query += " AND staff_id = ?"
                params.append(staff_id)

            cursor = self.db.execute_query(query, params)
            row = cursor.fetchone()

            return {
                'planned': row['planned'] if row else 0,
                'in_progress': row['in_progress'] if row else 0,
                'done': row['done'] if row else 0,
                'completed': row['completed'] if row else 0,
                'cancelled': row['cancelled'] if row else 0,
                'total': row['total'] if row else 0
            }

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت توزیع مداخلات: {e}")
            return {'planned': 0, 'in_progress': 0, 'done': 0, 'completed': 0, 'cancelled': 0, 'total': 0}

    def get_interventions_by_type(self, start_date=None, end_date=None, limit=10):
        """دریافت مداخلات گروه‌بندی شده بر اساس نوع"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT type, COUNT(*) as count
                FROM interventions
                WHERE is_deleted = 0
            """
            params = []

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            query += " GROUP BY type ORDER BY count DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            type_map = {
                "individual_talk": "گفتگوی فردی",
                "group_talk": "گفتگوی گروهی",
                "parent_call": "تماس با والدین",
                "parent_meeting": "جلسه با والدین",
                "responsibility": "سپردن مسئولیت",
                "encouragement": "تشویق",
                "group_activity": "فعالیت گروهی",
                "educational_game": "بازی تربیتی",
                "referral": "ارجاع به مشاور",
                "counseling": "مشاوره",
                "seat_change": "تغییر جای نشستن",
                "peer_helper": "همیار دانش‌آموز",
                "warning": "تذکر شفاهی",
                "other": "سایر"
            }

            result = []
            for row in rows:
                result.append({
                    'type': row['type'],
                    'type_display': type_map.get(row['type'], row['type']),
                    'count': row['count']
                })

            return result

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت مداخلات بر اساس نوع: {e}")
            return []

    def get_interventions_by_teacher(self, start_date=None, end_date=None, limit=10):
        """دریافت مداخلات گروه‌بندی شده بر اساس معلم"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT i.staff_id, s.full_name as staff_name, COUNT(*) as count
                FROM interventions i
                LEFT JOIN staff s ON i.staff_id = s.id
                WHERE i.is_deleted = 0
            """
            params = []

            if start_date:
                query += " AND i.date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND i.date <= ?"
                params.append(end_date)

            query += " GROUP BY i.staff_id ORDER BY count DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    'staff_id': row['staff_id'],
                    'staff_name': row['staff_name'] or 'نامشخص',
                    'count': row['count']
                })

            return result

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت مداخلات بر اساس معلم: {e}")
            return []

    def get_interventions_trend(self, period='monthly', start_date=None, end_date=None, limit=12):
        """دریافت روند مداخلات در بازه‌های زمانی"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT date
                FROM interventions
                WHERE is_deleted = 0
            """
            params = []

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            cursor = self.db.execute_query(query, params)
            rows = cursor.fetchall()

            if not rows:
                return []

            from collections import defaultdict
            grouped = defaultdict(int)

            for row in rows:
                date_str = row['date']
                if not date_str:
                    continue

                if period == 'monthly':
                    key = date_str[:7]
                    label = self._get_month_label(date_str)
                elif period == 'weekly':
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        try:
                            day = int(parts[2])
                            week = (day - 1) // 7 + 1
                            key = f"{parts[0]}/{parts[1]}/W{week}"
                            label = f"هفته {week} {parts[1]}"
                        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as _exc:
                            logger.debug(f"خطای مدیریت‌شده در get_interventions_trend (مسیر جایگزین): {_exc}")
                            key = date_str[:7]
                            label = date_str[:7]
                    else:
                        key = date_str[:7]
                        label = date_str[:7]
                else:
                    key = date_str
                    label = date_str

                grouped[key] += 1

            sorted_keys = sorted(grouped.keys())

            result = []
            for key in sorted_keys[-limit:]:
                result.append({
                    'period': key,
                    'label': label if period != 'daily' else key,
                    'count': grouped[key]
                })

            return result

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت روند مداخلات: {e}")
            return []

    def _get_month_label(self, date_str):
        """دریافت برچسب ماه از تاریخ — پیاده‌سازی مشترک

        بازرسی نهم: این متد در ۴ فایل DAL کپی شده بود؛ حالا همه به یک
        منبع واحد (utils.persian_date) وصل‌اند تا اصلاح‌های آینده
        (ارقام فارسی، تاریخ ناقص، نام ماه) یک‌جا اعمال شود.
        """
        from utils.persian_date import PersianDate
        return PersianDate.get_month_label(date_str)

    def get_intervention_success_rate(self, start_date=None, end_date=None, staff_id=None):
        """دریافت نرخ موفقیت مداخلات

        Args:
            staff_id: اگر داده شود، فقط مداخلاتِ ثبت‌شدهٔ همین معلم شمرده
                می‌شود (فیلتر انتخاب معلم در داشبورد).
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status IN ('completed', 'done') THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                    SUM(CASE WHEN status IN ('planned', 'in_progress') THEN 1 ELSE 0 END) as pending
                FROM interventions
                WHERE is_deleted = 0
            """
            params = []

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            if staff_id:
                query += " AND staff_id = ?"
                params.append(staff_id)

            cursor = self.db.execute_query(query, params)
            row = cursor.fetchone()

            total = row['total'] if row else 0
            completed = row['completed'] if row else 0
            cancelled = row['cancelled'] if row else 0
            pending = row['pending'] if row else 0

            return {
                'total': total,
                'completed': completed,
                'cancelled': cancelled,
                'pending': pending,
                'success_rate': round((completed / total * 100), 1) if total > 0 else 0
            }

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت نرخ موفقیت مداخلات: {e}")
            return {'total': 0, 'completed': 0, 'cancelled': 0, 'pending': 0, 'success_rate': 0}

    # ============================================================
    # متدهای تحلیل برای پیشنهادات (جدید)
    # ============================================================

    def get_interventions_for_student(self, profile_id, limit=None):
        """
        دریافت مداخلات یک دانش‌آموز

        Args:
            profile_id: شناسه پرونده دانش‌آموز
            limit: تعداد محدود

        Returns:
            list: لیست مداخلات
        """
        try:
            return self.get_by_student_profile(profile_id, limit=limit)
        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت مداخلات دانش‌آموز: {e}")
            return []

    def get_successful_interventions_for_student(self, profile_id, limit=3):
        """
        دریافت مداخلات موفق یک دانش‌آموز

        Args:
            profile_id: شناسه پرونده دانش‌آموز
            limit: تعداد محدود

        Returns:
            list: لیست مداخلات موفق
        """
        try:
            interventions = self.get_by_student_profile(profile_id)
            successful = [i for i in interventions if i.status in ['completed', 'done']]
            return successful[:limit]
        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت مداخلات موفق: {e}")
            return []

    def get_recommended_intervention_types(self, profile_id, competency_id=None):
        """
        دریافت انواع مداخلات پیشنهادی بر اساس شایستگی

        Args:
            profile_id: شناسه پرونده دانش‌آموز
            competency_id: شناسه شایستگی (اختیاری)

        Returns:
            list: لیست انواع مداخلات پیشنهادی
        """
        try:
            # دریافت مداخلات موفق برای دانش‌آموز
            successful = self.get_successful_interventions_for_student(profile_id)
            
            # اگر مداخله موفق وجود داشته باشد، نوع آن را پیشنهاد کن
            if successful:
                recommended_types = []
                for inter in successful[:3]:
                    if inter.type not in recommended_types:
                        recommended_types.append(inter.type)
                return recommended_types
            
            # اگر مداخله موفق وجود نداشت، انواع پیش‌فرض را برگردان
            default_types = [
                'encouragement',
                'individual_talk',
                'responsibility',
                'peer_helper'
            ]
            
            # اگر شایستگی مشخص شده باشد، انواع مناسب را انتخاب کن
            if competency_id:
                # بر اساس شایستگی، نوع مداخله مناسب را پیشنهاد کن
                competency_based = {
                    'emotional': ['individual_talk', 'encouragement', 'counseling'],
                    'social': ['group_activity', 'group_talk', 'peer_helper'],
                    'educational': ['encouragement', 'responsibility', 'seat_change'],
                    'moral': ['individual_talk', 'warning', 'responsibility'],
                    'self_management': ['responsibility', 'encouragement', 'seat_change'],
                    'participation': ['group_activity', 'encouragement', 'responsibility']
                }
                
                # دریافت دسته‌بندی شایستگی
                from dal.competency_dal import CompetencyDAL
                comp_dal = CompetencyDAL()
                comp = comp_dal.get_by_id(competency_id)
                if comp and comp.category in competency_based:
                    return competency_based[comp.category]
            
            return default_types
            
        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت انواع مداخلات پیشنهادی: {e}")
            return ['encouragement', 'individual_talk']

    # ============================================================
    # جست‌وجوی متن آزاد
    # ============================================================
    # ===== اصلاح (باگ گزارش‌شده در بازرسی دوم) =====
    # InterventionService.search_interventions / search_interventions_by_student / search_interventions_by_teacher
    # سه متد این DAL را صدا می‌زدند که هیچ‌کدام وجود نداشتند:
    #
    #     AttributeError: 'InterventionDAL' object has no attribute 'search'
    #
    # سرویس آن را به ServiceError تبدیل می‌کرد و در نتیجه کادر جست‌وجوی
    # صفحه مداخلات (views/pages/interventions_page.py:251-259) همیشه با پیام
    # «مشکل در جستجو: ...» شکست می‌خورد. یعنی جست‌وجو در این صفحه
    # از ابتدا کار نمی‌کرد و هیچ داده‌ای برنمی‌گشت.
    #
    # حالا هر سه متد پیاده‌سازی شده‌اند. نکته‌ها:
    #   - «بر اساس معلم» یعنی interventions.staff_id (همان معنایی که
    #     InterventionService.get_interventions_by_teacher در فیلتر پایتونی استفاده می‌کند).
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
    _SEARCH_COLUMNS = ('description', 'goal', 'result', 'type', 'status')

    def search(self, search_term, limit=None, include_deleted=False, academic_year_id=None,
               offset=None):
        """جست‌وجوی متن آزاد در همه مداخلات"""
        return self._search_text(search_term, limit=limit, include_deleted=include_deleted,
                                 academic_year_id=academic_year_id, offset=offset)

    def search_by_student(self, student_id, search_term, limit=None, include_deleted=False,
                          academic_year_id=None, offset=None):
        """جست‌وجوی متن آزاد در مداخلات یک دانش‌آموز"""
        return self._search_text(search_term, student_id=student_id, limit=limit,
                                 include_deleted=include_deleted, academic_year_id=academic_year_id,
                                 offset=offset)

    def search_by_teacher(self, teacher_id, search_term, limit=None, include_deleted=False,
                          academic_year_id=None, offset=None):
        """جست‌وجوی متن آزاد در مداخلات یک معلم"""
        return self._search_text(search_term, teacher_id=teacher_id, limit=limit,
                                 include_deleted=include_deleted, academic_year_id=academic_year_id,
                                 offset=offset)

    def count_search(self, search_term, student_id=None, teacher_id=None,
                      include_deleted=False, academic_year_id=None):
        """شمارش نتایج جست‌وجوی متن آزاد (بدون LIMIT/OFFSET) — مرحلهٔ ۶"""
        if search_term is None or not str(search_term).strip():
            return 0
        where, params, joins = self._search_where(
            search_term, student_id=student_id, teacher_id=teacher_id,
            include_deleted=include_deleted, academic_year_id=academic_year_id)
        query = "SELECT COUNT(*) as cnt FROM interventions i%s WHERE %s" % (
            joins, " AND ".join(where))
        cursor = self.db.execute_query(query, params)
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    def _search_where(self, search_term, student_id=None, teacher_id=None,
                       include_deleted=False, academic_year_id=None):
        """ساخت مشترک WHERE/params/joins جست‌وجو (استفادهٔ _search_text و count_search)"""
        term = self._escape_like(search_term)
        like = " OR ".join("i.%s %s" % (c, self._LIKE) for c in self._SEARCH_COLUMNS)

        joins = ""
        where = ["(%s)" % like]
        params = [term] * len(self._SEARCH_COLUMNS)

        if student_id is not None:
            joins += " JOIN student_academic_profiles sap ON i.student_profile_id = sap.id"
            where.append("sap.student_id = ?")
            params.append(student_id)

        if teacher_id is not None:
            where.append("i.staff_id = ?")
            params.append(teacher_id)

        if academic_year_id is not None:
            if "sap" not in joins:
                joins += " JOIN student_academic_profiles sap ON i.student_profile_id = sap.id"
            where.append("sap.academic_year_id = ?")
            params.append(academic_year_id)

        if not include_deleted:
            where.append("i.is_deleted = 0")

        return where, params, joins

    def _search_text(self, search_term, student_id=None, teacher_id=None,
                     limit=None, include_deleted=False, academic_year_id=None, offset=None):
        """پیاده‌سازی مشترک جست‌وجو (ساختار کوئری همانند get_by_student)"""
        if search_term is None or not str(search_term).strip():
            return []

        limit, offset = normalize_limit_offset(limit, offset)

        where, params, joins = self._search_where(
            search_term, student_id=student_id, teacher_id=teacher_id,
            include_deleted=include_deleted, academic_year_id=academic_year_id)

        query = "SELECT i.* FROM interventions i%s WHERE %s" % (joins, " AND ".join(where))
        query += " ORDER BY i.date DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_intervention(row) for row in rows]
