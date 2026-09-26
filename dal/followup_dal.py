"""
لایه دسترسی به داده پیگیری‌ها - با Soft Delete یکپارچه
با متدهای تحلیلی برای داشبورد
"""

import sqlite3

from database.connection import DatabaseConnection
from models.followup import FollowUp
from utils.logger import get_logger
from utils.pagination import normalize_limit_offset
from utils.security import AccessControl, Permission
from utils.time_utils import utc_now_iso

logger = get_logger(__name__)


class FollowUpDAL:
    """عملیات CRUD برای پیگیری‌ها با Soft Delete یکپارچه"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create(self, followup):
        """ایجاد پیگیری جدید"""
        # مرز مجوز backend (دور نوزدهم — سند ممیزی مدیر پروژه)
        AccessControl.require_permission(
            Permission.CREATE_FOLLOWUP.value, action="FollowupDAL.create")
        # مرز Scope/Cross-resource (دور نوزدهم — مرحلهٔ ۳، DD-6): پیگیری
        # به یک مداخله وصل می‌شود؛ اگر آن مداخله در Scope کاربر جاری
        # نباشد، نباید بشود رویش پیگیری ثبت کرد (وگرنه معلم می‌توانست
        # با دانستن intervention_id مداخلهٔ معلم دیگر، پیگیری روی
        # دانش‌آموزی خارج از Scope خودش بسازد).
        AccessControl.require_intervention_scope(
            followup.intervention_id, action="FollowupDAL.create")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO followups (
                intervention_id, staff_id, date, method,
                description, status, next_action_date,
                result_type, result_description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            followup.intervention_id,
            followup.staff_id,
            followup.date,
            followup.method,
            followup.description,
            followup.status,
            followup.next_action_date,
            followup.result_type,
            followup.result_description
        ))
        
        self.db.commit()
        followup.id = cursor.lastrowid
        return followup
    
    def get_by_id(self, followup_id, include_deleted=False):
        """دریافت پیگیری با شناسه"""
        query = "SELECT * FROM followups WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        cursor = self.db.execute_query(query, (followup_id,))
        row = cursor.fetchone()
        if row:
            followup = self._row_to_followup(row)
            # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۳، SEC-IDOR-01، DD-6):
            # زنجیرهٔ FollowUp→Intervention→Profile→Student→Scope.
            AccessControl.require_intervention_scope(
                followup.intervention_id, action="FollowupDAL.get_by_id")
            return followup
        return None
    
    def get_by_intervention(self, intervention_id, include_deleted=False):
        """دریافت پیگیری‌های یک مداخله - فقط رکوردهای موجود"""
        query = "SELECT * FROM followups WHERE intervention_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY date DESC"
        
        cursor = self.db.execute_query(query, (intervention_id,))
        rows = cursor.fetchall()
        return [self._row_to_followup(row) for row in rows]
    
    def get_pending(self, include_deleted=False):
        """دریافت پیگیری‌های در انتظار - فقط رکوردهای موجود"""
        query = "SELECT * FROM followups WHERE status = 'pending'"
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY date DESC"
        
        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        return [self._row_to_followup(row) for row in rows]
    
    def get_by_student_profile(self, profile_id, include_deleted=False):
        """دریافت پیگیری‌های یک پرونده دانش‌آموز - فقط رکوردهای موجود"""
        query = """
            SELECT f.* FROM followups f
            JOIN interventions i ON f.intervention_id = i.id
            WHERE i.student_profile_id = ?
        """
        if not include_deleted:
            query += " AND f.is_deleted = 0 AND i.is_deleted = 0"
        
        query += " ORDER BY f.date DESC"
        
        cursor = self.db.execute_query(query, (profile_id,))
        rows = cursor.fetchall()
        return [self._row_to_followup(row) for row in rows]
    
    def get_all(self, limit=None, include_deleted=False, academic_year_id=None,
                staff_id=None, offset=None):
        """
        دریافت همه پیگیری‌ها با فیلتر سال/معلم قبل از LIMIT.

        (دور نوزدهم، مرحلهٔ ۶) پارامتر offset سازگار با گذشته اضافه شده
        (پیش‌فرض None یعنی بدون OFFSET)؛ limit=None هم مثل قبل «بدون سقف»
        است. این DAL هنوز کنترل صفحه‌بندی‌ای در UI ندارد.
        """
        limit, offset = normalize_limit_offset(limit, offset)

        query = "SELECT f.* FROM followups f"
        joins, where, params = self._base_filters(
            include_deleted=include_deleted, academic_year_id=academic_year_id,
            staff_id=staff_id)
        if joins:
            query += " " + " ".join(joins)
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY f.date DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)
        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_followup(row) for row in rows]

    def count_all(self, include_deleted=False, academic_year_id=None, staff_id=None):
        """شمارش پیگیری‌ها با همان فیلترهای get_all (بدون LIMIT/OFFSET) — مرحلهٔ ۶"""
        query = "SELECT COUNT(*) as cnt FROM followups f"
        joins, where, params = self._base_filters(
            include_deleted=include_deleted, academic_year_id=academic_year_id,
            staff_id=staff_id)
        if joins:
            query += " " + " ".join(joins)
        if where:
            query += " WHERE " + " AND ".join(where)
        cursor = self.db.execute_query(query, params)
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    def _base_filters(self, include_deleted=False, academic_year_id=None, staff_id=None):
        """ساخت مشترک joins/where/params برای get_all و count_all (مرحلهٔ ۶)"""
        joins = []
        where = []
        params = []
        if academic_year_id is not None:
            joins.extend([
                "JOIN interventions i ON f.intervention_id = i.id",
                "JOIN student_academic_profiles sap ON i.student_profile_id = sap.id",
            ])
            where.append("sap.academic_year_id = ?")
            params.append(academic_year_id)
            # (دور نوزدهم، مرحلهٔ ۷ — رفع باگ) پروندهٔ حذف‌شده در فیلتر سال
            # نباید شمرده شود؛ هم‌راستا با profile_dal.get_by_ids در همه‌جا.
            where.append("sap.is_deleted = 0")
            if not include_deleted:
                where.append("i.is_deleted = 0")
        if not include_deleted:
            where.append("f.is_deleted = 0")
        if staff_id is not None:
            where.append("f.staff_id = ?")
            params.append(staff_id)
        return joins, where, params

    def get_dashboard_stats(self, staff_id=None, academic_year_id=None):
        """
        شمارش کل/در-انتظار پیگیری‌ها با یک کوئری Aggregate (مرحلهٔ ۷ —
        PERF-01/08/09)؛ جایگزین get_all() کامل + شمارش پایتونی در
        dashboard_service. فیلترها دقیقاً همان count_all/get_all را دارند.

        Returns:
            dict: {'total', 'pending'}
        """
        query = "SELECT COUNT(*) as total, SUM(CASE WHEN f.status = 'pending' THEN 1 ELSE 0 END) as pending FROM followups f"
        joins, where, params = self._base_filters(
            include_deleted=False, academic_year_id=academic_year_id, staff_id=staff_id)
        if joins:
            query += " " + " ".join(joins)
        if where:
            query += " WHERE " + " AND ".join(where)
        cursor = self.db.execute_query(query, params)
        row = cursor.fetchone()
        total = (row["total"] if row else 0) or 0
        pending = (row["pending"] if row else 0) or 0
        return {'total': total, 'pending': pending}

    def update(self, followup):
        """به‌روزرسانی پیگیری - فقط رکوردهای موجود"""
        # مرز مجوز backend (دور نوزدهم)
        AccessControl.require_permission(
            Permission.EDIT_FOLLOWUP.value, action="FollowupDAL.update")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # بررسی وجود رکورد و عدم حذف
        cursor.execute(
            "SELECT intervention_id FROM followups WHERE id = ? AND is_deleted = 0",
            (followup.id,)
        )
        existing = cursor.fetchone()
        if not existing:
            raise Exception("رکورد مورد نظر یافت نشد یا حذف شده است.")

        # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۳): هم رکورد موجود
        # (پیش از تغییر) و هم مداخلهٔ مقصد (اگر عوض شده باشد).
        AccessControl.require_intervention_scope(
            existing["intervention_id"], action="FollowupDAL.update")
        if followup.intervention_id != existing["intervention_id"]:
            AccessControl.require_intervention_scope(
                followup.intervention_id, action="FollowupDAL.update(new_intervention)")
        
        cursor.execute("""
            UPDATE followups SET
                intervention_id = ?, staff_id = ?, date = ?, method = ?,
                description = ?, status = ?, next_action_date = ?,
                result_type = ?, result_description = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            followup.intervention_id,
            followup.staff_id,
            followup.date,
            followup.method,
            followup.description,
            followup.status,
            followup.next_action_date,
            followup.result_type,
            followup.result_description,
            followup.id
        ))
        
        self.db.commit()
        return followup
    
    def update_status(self, followup_id, new_status):
        """به‌روزرسانی وضعیت پیگیری - فقط رکوردهای موجود"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE followups SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (new_status, followup_id))
        
        self.db.commit()
        return True
    
    def delete(self, followup_id, user_id=None):
        """حذف منطقی پیگیری - فقط رکوردهای موجود"""
        # مرز مجوز backend (BUG-NAV-03): حذف پیگیری = DELETE_FOLLOWUP
        AccessControl.require_permission(
            Permission.DELETE_FOLLOWUP.value, action="followup_dal.delete")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # بررسی وجود رکورد و عدم حذف قبلی
        cursor.execute(
            "SELECT intervention_id FROM followups WHERE id = ? AND is_deleted = 0",
            (followup_id,)
        )
        existing = cursor.fetchone()
        if not existing:
            return False
        # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۳)
        AccessControl.require_intervention_scope(
            existing["intervention_id"], action="FollowupDAL.delete")
        
        now = utc_now_iso()
        cursor.execute("""
            UPDATE followups SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (now, user_id, followup_id))
        
        self.db.commit()
        return True
    
    def restore(self, followup_id, user_id=None):
        """بازیابی پیگیری حذف شده - فقط رکوردهای حذف شده"""
        # مرز مجوز backend (BUG-NAV-03): بازیابی = همان مجوز حذف
        AccessControl.require_permission(
            Permission.DELETE_FOLLOWUP.value, action="followup_dal.restore")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # بررسی وجود رکورد و حذف شده بودن
        cursor.execute(
            "SELECT intervention_id FROM followups WHERE id = ? AND is_deleted = 1",
            (followup_id,)
        )
        existing = cursor.fetchone()
        if not existing:
            return False
        # مرز Scope/IDOR (دور نوزدهم — مرحلهٔ ۳)
        AccessControl.require_intervention_scope(
            existing["intervention_id"], action="FollowupDAL.restore")

        # مرحلهٔ ۸ (RESTORE-EDGE-01): مداخلهٔ والد باید هنوز وجود
        # داشته و حذف نشده باشد — وگرنه یک پیگیریِ «فعال» روی یک
        # مداخلهٔ حذف‌شده ساخته می‌شود.
        parent = cursor.execute(
            "SELECT 1 FROM interventions WHERE id = ? AND is_deleted = 0",
            (existing["intervention_id"],)
        ).fetchone()
        if not parent:
            raise ValueError(
                "مداخلهٔ مربوط به این پیگیری حذف شده یا وجود ندارد؛ "
                "پیش از بازیابیِ پیگیری باید ابتدا خودِ مداخله را "
                "بازگردانی کنید."
            )

        cursor.execute("""
            UPDATE followups SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 1
        """, (followup_id,))
        
        self.db.commit()
        return True
    
    def get_deleted(self, limit=None):
        """دریافت لیست رکوردهای حذف شده"""
        query = "SELECT * FROM followups WHERE is_deleted = 1 ORDER BY deleted_at DESC"
        params = []
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor = self.db.execute_query(query, tuple(params) if params else None)
        rows = cursor.fetchall()
        return [self._row_to_followup(row) for row in rows]
    
    def permanent_delete(self, followup_id):
        """
        حذف فیزیکی پیگیری - فقط برای موارد خاص استفاده شود

        (دور نوزدهم، مرحلهٔ ۸ — SEC-HARD-DELETE-01) قبلاً بدون هیچ
        بررسیِ Permission، ردیف مستقیماً DELETE می‌شد. هیچ جدولی به
        followups.id کلید خارجی ندارد (برگ درخت وابستگی است)، پس فقط
        Permission لازم است، نه گاردِ وابستگی.
        """
        AccessControl.require_permission(
            Permission.DELETE_FOLLOWUP.value, action="FollowUpDAL.permanent_delete")

        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM followups WHERE id = ?",
            (followup_id,)
        )
        affected = cursor.rowcount
        self.db.commit()
        return affected > 0
    
    def _row_to_followup(self, row):
        """تبدیل ردیف دیتابیس به مدل FollowUp"""
        followup = FollowUp()
        followup.id = row['id']
        followup.intervention_id = row['intervention_id']
        followup.staff_id = row['staff_id']
        followup.date = row['date']
        followup.method = row['method']
        followup.description = row['description']
        followup.status = row['status']
        followup.next_action_date = row['next_action_date']
        followup.result_type = row['result_type']
        followup.result_description = row['result_description']
        followup.created_at = row['created_at']
        followup.updated_at = row['updated_at']
        
        # فیلدهای Soft Delete
        followup.is_deleted = row['is_deleted']
        followup.deleted_at = row['deleted_at']
        followup.deleted_by = row['deleted_by']
        
        return followup

    # ============================================================
    # متدهای تحلیلی برای داشبورد
    # ============================================================

    def get_followups_distribution_by_status(self, start_date=None, end_date=None, staff_id=None):
        """
        دریافت توزیع پیگیری‌ها بر اساس وضعیت

        Args:
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
            staff_id: اگر داده شود فقط پیگیری‌های ثبت‌شدهٔ همین معلم
                شمرده می‌شود (فیلتر انتخاب معلم در داشبورد)

        Returns:
            dict: {
                'pending': int,
                'done': int,
                'continued': int,
                'closed': int,
                'cancelled': int,
                'total': int
            }
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
                    SUM(CASE WHEN status = 'continued' THEN 1 ELSE 0 END) as continued,
                    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                FROM followups
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
                'pending': row['pending'] if row else 0,
                'done': row['done'] if row else 0,
                'continued': row['continued'] if row else 0,
                'closed': row['closed'] if row else 0,
                'cancelled': row['cancelled'] if row else 0,
                'total': row['total'] if row else 0
            }

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت توزیع پیگیری‌ها: {e}")
            return {'pending': 0, 'done': 0, 'continued': 0, 'closed': 0, 'cancelled': 0, 'total': 0}

    def get_overdue_followups_count(self, start_date=None, end_date=None, staff_id=None):
        """
        دریافت تعداد پیگیری‌های معوق

        Args:
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
            staff_id: اگر داده شود فقط پیگیری‌های ثبت‌شدهٔ همین معلم
                شمرده می‌شود (فیلتر انتخاب معلم در داشبورد)

        Returns:
            int: تعداد پیگیری‌های معوق
        """
        try:
            import jdatetime
            conn = self.db.get_connection()
            cursor = conn.cursor()

            today = jdatetime.date.today()
            today_str = f"{today.year}/{today.month:02d}/{today.day:02d}"

            query = """
                SELECT COUNT(*) as count
                FROM followups
                WHERE status = 'pending'
                AND next_action_date IS NOT NULL
                AND next_action_date < ?
                AND is_deleted = 0
            """
            params = [today_str]

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            if staff_id:
                query += " AND staff_id = ?"
                params.append(staff_id)

            cursor.execute(query, params)
            row = cursor.fetchone()

            return row['count'] if row else 0

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت تعداد پیگیری‌های معوق: {e}")
            return 0

    def get_followups_by_result_type(self, start_date=None, end_date=None):
        """
        دریافت پیگیری‌ها گروه‌بندی شده بر اساس نوع نتیجه

        Args:
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)

        Returns:
            list: [
                {
                    'result_type': str,
                    'result_type_display': str,
                    'count': int
                }
            ]
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT result_type, COUNT(*) as count
                FROM followups
                WHERE is_deleted = 0
                AND result_type IS NOT NULL
            """
            params = []

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            query += " GROUP BY result_type ORDER BY count DESC"

            cursor = self.db.execute_query(query, params)
            rows = cursor.fetchall()

            # نگاشت نوع نتیجه به نمایش فارسی
            result_map = {
                "improved": "بهبود مشاهده شد",
                "no_change": "بدون تغییر قابل مشاهده",
                "continued": "تداوم وضعیت",
                "new_status": "وضعیت جدید",
                "insufficient": "اطلاعات ناکافی",
                "needs_more": "نیازمند پیگیری بیشتر"
            }

            result = []
            for row in rows:
                result.append({
                    'result_type': row['result_type'],
                    'result_type_display': result_map.get(row['result_type'], row['result_type']),
                    'count': row['count']
                })

            return result

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت پیگیری‌ها بر اساس نوع نتیجه: {e}")
            return []

    def get_followups_by_teacher(self, start_date=None, end_date=None, limit=10):
        """
        دریافت پیگیری‌ها گروه‌بندی شده بر اساس معلم

        Args:
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
            limit: تعداد محدود

        Returns:
            list: [
                {
                    'staff_id': int,
                    'staff_name': str,
                    'count': int
                }
            ]
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT f.staff_id, s.full_name as staff_name, COUNT(*) as count
                FROM followups f
                LEFT JOIN staff s ON f.staff_id = s.id
                WHERE f.is_deleted = 0
            """
            params = []

            if start_date:
                query += " AND f.date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND f.date <= ?"
                params.append(end_date)

            query += " GROUP BY f.staff_id ORDER BY count DESC LIMIT ?"
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
            logger.error(f"خطا در دریافت پیگیری‌ها بر اساس معلم: {e}")
            return []

    def get_followup_trend(self, period='monthly', start_date=None, end_date=None, limit=12):
        """
        دریافت روند پیگیری‌ها در بازه‌های زمانی

        Args:
            period: بازه زمانی ('monthly', 'weekly', 'daily')
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
            limit: تعداد محدود

        Returns:
            list: [
                {
                    'period': str,
                    'label': str,
                    'count': int,
                    'pending': int,
                    'done': int
                }
            ]
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT date, status
                FROM followups
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
            grouped = defaultdict(lambda: {'total': 0, 'pending': 0, 'done': 0})

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
                            logger.debug(f"خطای مدیریت‌شده در get_followup_trend (مسیر جایگزین): {_exc}")
                            key = date_str[:7]
                            label = date_str[:7]
                    else:
                        key = date_str[:7]
                        label = date_str[:7]
                else:
                    key = date_str
                    label = date_str

                grouped[key]['total'] += 1
                if row['status'] == 'pending':
                    grouped[key]['pending'] += 1
                elif row['status'] == 'done':
                    grouped[key]['done'] += 1

            sorted_keys = sorted(grouped.keys())

            result = []
            for key in sorted_keys[-limit:]:
                data = grouped[key]
                result.append({
                    'period': key,
                    'label': label if period != 'daily' else key,
                    'count': data['total'],
                    'pending': data['pending'],
                    'done': data['done']
                })

            return result

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت روند پیگیری‌ها: {e}")
            return []

    def _get_month_label(self, date_str):
        """دریافت برچسب ماه از تاریخ — پیاده‌سازی مشترک

        بازرسی نهم: این متد در ۴ فایل DAL کپی شده بود؛ حالا همه به یک
        منبع واحد (utils.persian_date) وصل‌اند تا اصلاح‌های آینده
        (ارقام فارسی، تاریخ ناقص، نام ماه) یک‌جا اعمال شود.
        """
        from utils.persian_date import PersianDate
        return PersianDate.get_month_label(date_str)

    def get_followup_completion_rate(self, start_date=None, end_date=None, staff_id=None):
        """
        دریافت نرخ تکمیل پیگیری‌ها

        Args:
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
            staff_id: اگر داده شود فقط پیگیری‌های ثبت‌شدهٔ همین معلم
                شمرده می‌شود (فیلتر انتخاب معلم در داشبورد)

        Returns:
            dict: {
                'total': int,
                'completed': int,
                'pending': int,
                'completion_rate': float
            }
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status IN ('done', 'closed') THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
                FROM followups
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
            pending = row['pending'] if row else 0

            return {
                'total': total,
                'completed': completed,
                'pending': pending,
                'completion_rate': round((completed / total * 100), 1) if total > 0 else 0
            }

        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            logger.error(f"خطا در دریافت نرخ تکمیل پیگیری‌ها: {e}")
            return {'total': 0, 'completed': 0, 'pending': 0, 'completion_rate': 0}

    # ============================================================
    # جست‌وجوی متن آزاد
    # ============================================================
    # ===== اصلاح (باگ گزارش‌شده در بازرسی دوم) =====
    # FollowUpService.search_followups / search_followups_by_student / search_followups_by_teacher
    # سه متد این DAL را صدا می‌زدند که هیچ‌کدام وجود نداشتند:
    #
    #     AttributeError: 'FollowUpDAL' object has no attribute 'search'
    #
    # سرویس آن را به ServiceError تبدیل می‌کرد و در نتیجه کادر جست‌وجوی
    # صفحه پیگیری‌ها (views/pages/followups_page.py:218-222) همیشه با پیام
    # «مشکل در جستجو: ...» شکست می‌خورد. یعنی جست‌وجو در این صفحه
    # از ابتدا کار نمی‌کرد و هیچ داده‌ای برنمی‌گشت.
    #
    # حالا هر سه متد پیاده‌سازی شده‌اند. نکته‌ها:
    #   - «بر اساس معلم» یعنی followups.staff_id (همان معنایی که
    #     FollowUpService.get_followups_by_teacher در فیلتر پایتونی استفاده می‌کند).
    #   - «بر اساس دانش‌آموز» با JOIN روی پرونده سالانه انجام می‌شود
    #     (همان الگوی get_by_student).
    #   - کاراکترهای ویژه LIKE فرار داده می‌شوند تا جست‌وجوی «٪» یا «_»
    #     به‌جای wildcard، خودِ همان نویسه را پیدا کند.
    #   - رکوردهای حذف منطقی‌شده برنمی‌گردند (مگر include_deleted=True).
    # نکته: جدول followups ستون student_profile_id ندارد؛ وابستگی از طریق
    #       followups.intervention_id → interventions.student_profile_id است.
    #       (همان الگوی get_by_student_profile در همین فایل)

    @staticmethod
    def _escape_like(text):
        """ساخت الگوی LIKE امن (فرار کاراکترهای ویژه) برای جست‌وجوی متن آزاد"""
        s = '' if text is None else str(text)
        s = s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        return '%' + s + '%'

    _LIKE = "LIKE ? ESCAPE '\\'"
    _SEARCH_COLUMNS = ('description', 'method', 'result_description', 'result_type', 'status')

    def search(self, search_term, limit=None, include_deleted=False, academic_year_id=None,
               offset=None):
        """جست‌وجوی متن آزاد در همه پیگیری‌ها"""
        return self._search_text(search_term, limit=limit, include_deleted=include_deleted,
                                 academic_year_id=academic_year_id, offset=offset)

    def search_by_student(self, student_id, search_term, limit=None, include_deleted=False,
                          academic_year_id=None, offset=None):
        """جست‌وجوی متن آزاد در پیگیری‌های یک دانش‌آموز"""
        return self._search_text(search_term, student_id=student_id, limit=limit,
                                 include_deleted=include_deleted, academic_year_id=academic_year_id,
                                 offset=offset)

    def search_by_teacher(self, teacher_id, search_term, limit=None, include_deleted=False,
                          academic_year_id=None, offset=None):
        """جست‌وجوی متن آزاد در پیگیری‌های یک معلم"""
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
        query = "SELECT COUNT(*) as cnt FROM followups f%s WHERE %s" % (
            joins, " AND ".join(where))
        cursor = self.db.execute_query(query, params)
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    def _search_where(self, search_term, student_id=None, teacher_id=None,
                       include_deleted=False, academic_year_id=None):
        """ساخت مشترک WHERE/params/joins جست‌وجو (استفادهٔ _search_text و count_search)"""
        term = self._escape_like(search_term)
        like = " OR ".join("f.%s %s" % (c, self._LIKE) for c in self._SEARCH_COLUMNS)

        joins = ""
        where = ["(%s)" % like]
        params = [term] * len(self._SEARCH_COLUMNS)

        if student_id is not None:
            joins += (" JOIN interventions i ON f.intervention_id = i.id"
                      " JOIN student_academic_profiles sap ON i.student_profile_id = sap.id")
            where.append("sap.student_id = ?")
            params.append(student_id)
            if not include_deleted:
                where.append("i.is_deleted = 0")

        if teacher_id is not None:
            where.append("f.staff_id = ?")
            params.append(teacher_id)

        if academic_year_id is not None:
            if "sap" not in joins:
                joins += (" JOIN interventions i ON f.intervention_id = i.id"
                          " JOIN student_academic_profiles sap ON i.student_profile_id = sap.id")
            where.append("sap.academic_year_id = ?")
            params.append(academic_year_id)
            if not include_deleted:
                where.append("i.is_deleted = 0")

        if not include_deleted:
            where.append("f.is_deleted = 0")

        return where, params, joins

    def _search_text(self, search_term, student_id=None, teacher_id=None,
                     limit=None, include_deleted=False, academic_year_id=None, offset=None):
        """پیاده‌سازی مشترک جست‌وجو"""
        if search_term is None or not str(search_term).strip():
            return []

        limit, offset = normalize_limit_offset(limit, offset)

        where, params, joins = self._search_where(
            search_term, student_id=student_id, teacher_id=teacher_id,
            include_deleted=include_deleted, academic_year_id=academic_year_id)

        query = "SELECT f.* FROM followups f%s WHERE %s" % (joins, " AND ".join(where))
        query += " ORDER BY f.date DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

        cursor = self.db.execute_query(query, params)
        rows = cursor.fetchall()
        return [self._row_to_followup(row) for row in rows]
