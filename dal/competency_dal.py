"""
لایه دسترسی به داده شایستگی‌ها - با پشتیبانی از Indicator و ObservableBehavior
با متدهای تحلیلی برای داشبورد و پیشنهادات
"""

from dal.indicator_dal import IndicatorDAL
from dal.observable_behavior_dal import ObservableBehaviorDAL
from database.connection import DatabaseConnection
from models.competency import Competency
from utils.logger import get_logger
from utils.time_utils import utc_now_iso

logger = get_logger(__name__)


class CompetencyDAL:
    """عملیات CRUD برای شایستگی‌ها با بارگذاری کامل ساختار"""

    def __init__(self):
        self.db = DatabaseConnection()
        self.indicator_dal = IndicatorDAL()
        self.behavior_dal = ObservableBehaviorDAL()

    def create(self, competency):
        """ایجاد شایستگی جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO competencies (
                title, description, category, is_active, sort_order
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            competency.title,
            competency.description,
            competency.category,
            competency.is_active,
            competency.sort_order
        ))

        conn.commit()
        competency.id = cursor.lastrowid
        return competency

    def get_by_id(self, competency_id, load_full=False, include_deleted=False):
        """دریافت شایستگی با شناسه"""
        query = "SELECT * FROM competencies WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"

        cursor = self.db.execute_query(query, (competency_id,))
        row = cursor.fetchone()

        if not row:
            return None

        competency = self._row_to_competency(row)

        if load_full:
            competency.indicators = self.indicator_dal.get_by_competency(
                competency_id, include_deleted
            )
            competency.observable_behaviors = self.behavior_dal.get_by_competency(
                competency_id, include_deleted
            )

        return competency

    def get_by_title(self, title, load_full=False):
        """دریافت شایستگی با عنوان"""
        cursor = self.db.execute_query(
            "SELECT * FROM competencies WHERE title = ? AND is_deleted = 0",
            (title,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        competency = self._row_to_competency(row)

        if load_full:
            competency.indicators = self.indicator_dal.get_by_competency(competency.id)
            competency.observable_behaviors = self.behavior_dal.get_by_competency(competency.id)

        return competency

    def get_all(self, include_inactive=False, load_full=False):
        """دریافت همه شایستگی‌ها"""
        if include_inactive:
            query = "SELECT * FROM competencies WHERE is_deleted = 0 ORDER BY sort_order, title"
        else:
            query = "SELECT * FROM competencies WHERE is_active = 1 AND is_deleted = 0 ORDER BY sort_order, title"

        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        competencies = [self._row_to_competency(row) for row in rows]

        if load_full:
            for comp in competencies:
                comp.indicators = self.indicator_dal.get_by_competency(comp.id)
                comp.observable_behaviors = self.behavior_dal.get_by_competency(comp.id)

        return competencies

    def get_by_category(self, category, load_full=False):
        """دریافت شایستگی‌های یک دسته"""
        cursor = self.db.execute_query(
            """SELECT * FROM competencies
               WHERE category = ? AND is_active = 1 AND is_deleted = 0
               ORDER BY sort_order, title""",
            (category,)
        )
        rows = cursor.fetchall()
        competencies = [self._row_to_competency(row) for row in rows]

        if load_full:
            for comp in competencies:
                comp.indicators = self.indicator_dal.get_by_competency(comp.id)
                comp.observable_behaviors = self.behavior_dal.get_by_competency(comp.id)

        return competencies

    def get_full_structure(self, competency_id=None):
        """دریافت ساختار کامل شایستگی با تمام شاخص‌ها و رفتارهای قابل مشاهده"""
        if competency_id:
            comp = self.get_by_id(competency_id, load_full=True)
            return [comp] if comp else []

        return self.get_all(load_full=True)

    def get_competency_with_details(self, competency_id):
        """دریافت شایستگی با جزئیات کامل برای نمایش در UI"""
        comp = self.get_by_id(competency_id, load_full=True)
        if not comp:
            return None

        return {
            'competency': comp,
            'indicators': comp.indicators,
            'observable_behaviors': comp.observable_behaviors,
            'structure': comp.get_indicators_with_behaviors()
        }

    def update(self, competency):
        """به‌روزرسانی شایستگی"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE competencies SET
                title = ?,
                description = ?,
                category = ?,
                is_active = ?,
                sort_order = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (
            competency.title,
            competency.description,
            competency.category,
            competency.is_active,
            competency.sort_order,
            competency.id
        ))

        conn.commit()
        return competency

    def delete(self, competency_id, user_id=None):
        """حذف منطقی شایستگی و تمام شاخص‌ها و رفتارهای مرتبط"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM competencies WHERE id = ? AND is_deleted = 0",
            (competency_id,)
        )
        if not cursor.fetchone():
            return False

        now = utc_now_iso()

        cursor.execute("""
            UPDATE competencies SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE id = ?
        """, (now, user_id, competency_id))

        cursor.execute("""
            UPDATE indicators SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE competency_id = ? AND is_deleted = 0
        """, (now, user_id, competency_id))

        cursor.execute("""
            UPDATE observable_behaviors SET
                is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE competency_id = ? AND is_deleted = 0
        """, (now, user_id, competency_id))

        conn.commit()
        return True

    def restore(self, competency_id, user_id=None):
        """بازیابی شایستگی حذف شده و تمام شاخص‌ها و رفتارهای مرتبط"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE competencies SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE id = ? AND is_deleted = 1
        """, (competency_id,))

        cursor.execute("""
            UPDATE indicators SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE competency_id = ? AND is_deleted = 1
        """, (competency_id,))

        cursor.execute("""
            UPDATE observable_behaviors SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL
            WHERE competency_id = ? AND is_deleted = 1
        """, (competency_id,))

        conn.commit()
        return True

    def get_categories_with_counts(self):
        """دریافت دسته‌بندی‌ها با تعداد شایستگی"""
        cursor = self.db.execute_query("""
            SELECT category, COUNT(*) as count
            FROM competencies
            WHERE is_deleted = 0 AND is_active = 1
            GROUP BY category
            ORDER BY count DESC
        """)
        rows = cursor.fetchall()

        category_names = {
            "emotional": "عاطفی-هیجانی",
            "social": "اجتماعی",
            "educational": "آموزشی",
            "moral": "اخلاقی",
            "self_management": "خودمدیریتی",
            "participation": "مشارکت",
            "other": "سایر"
        }

        return [
            {
                'key': row['category'],
                'name': category_names.get(row['category'], row['category']),
                'count': row['count']
            }
            for row in rows
        ]

    def get_active_competencies(self):
        """دریافت شایستگی‌های فعال"""
        return self.get_all(include_inactive=False)

    def search(self, search_term):
        """جستجوی شایستگی‌ها بر اساس عنوان یا توضیحات"""
        search_pattern = f"%{search_term}%"
        cursor = self.db.execute_query("""
            SELECT * FROM competencies
            WHERE (title LIKE ? OR description LIKE ?)
            AND is_deleted = 0 AND is_active = 1
            ORDER BY sort_order, title
        """, (search_pattern, search_pattern))
        rows = cursor.fetchall()
        return [self._row_to_competency(row) for row in rows]

    def _row_to_competency(self, row):
        """تبدیل ردیف دیتابیس به مدل Competency"""
        competency = Competency()
        competency.id = row['id']
        competency.title = row['title']
        competency.description = row['description']
        competency.category = row['category']
        competency.is_active = row['is_active']
        competency.sort_order = row['sort_order']
        competency.created_at = row['created_at']
        competency.updated_at = row['updated_at']
        competency.is_deleted = row['is_deleted']
        competency.deleted_at = row['deleted_at']
        competency.deleted_by = row['deleted_by']
        return competency

    # ============================================================
    # متدهای تحلیلی برای داشبورد
    # ============================================================

    def get_competency_usage_stats(self, start_date=None, end_date=None):
        """دریافت آمار استفاده از شایستگی‌ها"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            competencies = self.get_all(include_inactive=False)
            comp_ids = [c.id for c in competencies]

            if not comp_ids:
                return {
                    'total_competencies': 0,
                    'used_competencies': 0,
                    'unused_competencies': 0,
                    'most_used': [],
                    'least_used': []
                }

            placeholders = ','.join(['?'] * len(comp_ids))
            query = f"""
                SELECT competency_id, COUNT(*) as count
                FROM observations
                WHERE is_deleted = 0
                AND competency_id IN ({placeholders})
            """
            params = comp_ids.copy()

            if start_date:
                query += " AND observation_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND observation_date <= ?"
                params.append(end_date)

            query += " GROUP BY competency_id ORDER BY count DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            used_comp_ids = set(row['competency_id'] for row in rows)
            used_competencies = len(used_comp_ids)
            unused_competencies = len(comp_ids) - used_competencies

            comp_dict = {c.id: c.title for c in competencies}

            most_used = []
            least_used = []

            for row in rows[:5]:
                most_used.append({
                    'competency_id': row['competency_id'],
                    'competency_name': comp_dict.get(row['competency_id'], f"ID:{row['competency_id']}"),
                    'count': row['count']
                })

            unused_ids = set(comp_ids) - used_comp_ids
            for comp_id in list(unused_ids)[:5]:
                least_used.append({
                    'competency_id': comp_id,
                    'competency_name': comp_dict.get(comp_id, f"ID:{comp_id}"),
                    'count': 0
                })

            return {
                'total_competencies': len(comp_ids),
                'used_competencies': used_competencies,
                'unused_competencies': unused_competencies,
                'most_used': most_used,
                'least_used': least_used
            }

        except Exception as e:
            logger.error(f"خطا در دریافت آمار استفاده از شایستگی‌ها: {e}")
            return {
                'total_competencies': 0,
                'used_competencies': 0,
                'unused_competencies': 0,
                'most_used': [],
                'least_used': []
            }

    def get_competency_category_distribution(self):
        """دریافت توزیع شایستگی‌ها بر اساس دسته‌بندی"""
        try:
            categories = self.get_categories_with_counts()
            total = sum(c['count'] for c in categories) if categories else 0

            result = []
            for cat in categories:
                result.append({
                    'category': cat['key'],
                    'category_display': cat['name'],
                    'count': cat['count'],
                    'percentage': round((cat['count'] / total * 100), 1) if total > 0 else 0
                })

            return result

        except Exception as e:
            logger.error(f"خطا در دریافت توزیع شایستگی‌ها: {e}")
            return []

    def get_competency_avg_severity(self, start_date=None, end_date=None):
        """دریافت میانگین شدت هر شایستگی"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT o.competency_id, c.title as competency_name,
                       AVG(o.severity) as avg_severity, COUNT(*) as count
                FROM observations o
                LEFT JOIN competencies c ON o.competency_id = c.id
                WHERE o.is_deleted = 0
                AND o.competency_id IS NOT NULL
            """
            params = []

            if start_date:
                query += " AND o.observation_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND o.observation_date <= ?"
                params.append(end_date)

            query += " GROUP BY o.competency_id ORDER BY avg_severity DESC"

            cursor.execute(query, tuple(params))  # اصلاح: None می‌داد «parameters are of unsupported type»
            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    'competency_id': row['competency_id'],
                    'competency_name': row['competency_name'] or f"شایستگی {row['competency_id']}",
                    'avg_severity': round(row['avg_severity'], 1) if row['avg_severity'] else 0,
                    'count': row['count']
                })

            return result

        except Exception as e:
            logger.error(f"خطا در دریافت میانگین شدت شایستگی‌ها: {e}")
            return []

    # ============================================================
    # متدهای تحلیل برای پیشنهادات (جدید)
    # ============================================================

    def get_competency_by_category_for_student(self, profile_id, category):
        """
        دریافت شایستگی‌های یک دسته خاص برای یک دانش‌آموز

        Args:
            profile_id: شناسه پرونده دانش‌آموز
            category: دسته‌بندی شایستگی

        Returns:
            list: لیست شایستگی‌ها با آمار
        """
        try:
            from dal.observation_dal import ObservationDAL
            obs_dal = ObservationDAL()
            observations = obs_dal.get_by_student_profile(profile_id)
            
            if not observations:
                return []
            
            # دریافت شایستگی‌های آن دسته
            competencies = self.get_by_category(category)
            comp_ids = [c.id for c in competencies]
            
            if not comp_ids:
                return []
            
            # آمار مشاهدات برای این شایستگی‌ها
            comp_stats = {}
            for obs in observations:
                if obs.competency_id in comp_ids:
                    if obs.competency_id not in comp_stats:
                        comp_stats[obs.competency_id] = {
                            'count': 0,
                            'total_severity': 0
                        }
                    comp_stats[obs.competency_id]['count'] += 1
                    comp_stats[obs.competency_id]['total_severity'] += obs.severity or 1
            
            # ترکیب با اطلاعات شایستگی
            result = []
            for comp in competencies:
                stats = comp_stats.get(comp.id, {'count': 0, 'total_severity': 0})
                avg_severity = stats['total_severity'] / stats['count'] if stats['count'] > 0 else 0
                result.append({
                    'competency_id': comp.id,
                    'competency_name': comp.title,
                    'category': comp.category,
                    'category_display': comp.category_display,
                    'count': stats['count'],
                    'avg_severity': round(avg_severity, 1)
                })
            
            # مرتب‌سازی بر اساس تعداد و میانگین شدت
            result.sort(key=lambda x: (x['count'], x['avg_severity']), reverse=True)
            
            return result
            
        except Exception as e:
            logger.error(f"خطا در دریافت شایستگی‌های دسته برای دانش‌آموز: {e}")
            return []

    def get_recommended_competencies_for_student(self, profile_id, limit=3):
        """
        دریافت شایستگی‌های پیشنهادی برای یک دانش‌آموز
        
        شایستگی‌هایی که تعداد مشاهدات کم یا میانگین شدت پایینی دارند

        Args:
            profile_id: شناسه پرونده دانش‌آموز
            limit: تعداد محدود

        Returns:
            list: لیست شایستگی‌های پیشنهادی
        """
        try:
            from dal.observation_dal import ObservationDAL
            obs_dal = ObservationDAL()
            
            # دریافت شایستگی‌های ضعیف
            weak = obs_dal.get_weak_competencies_for_student(profile_id, limit)
            
            if weak:
                return weak
            
            # اگر شایستگی ضعیفی وجود نداشت، شایستگی‌های بدون مشاهده را پیشنهاد کن
            # دریافت همه شایستگی‌های فعال
            all_comps = self.get_all(include_inactive=False)
            
            # دریافت مشاهدات دانش‌آموز
            observations = obs_dal.get_by_student_profile(profile_id)
            observed_comp_ids = set(o.competency_id for o in observations if o.competency_id)
            
            # شایستگی‌های بدون مشاهده
            unobserved = [c for c in all_comps if c.id not in observed_comp_ids]
            
            result = []
            for comp in unobserved[:limit]:
                result.append({
                    'competency_id': comp.id,
                    'competency_name': comp.title,
                    'avg_severity': 0,
                    'count': 0,
                    'observation_ids': []
                })
            
            return result
            
        except Exception as e:
            logger.error(f"خطا در دریافت شایستگی‌های پیشنهادی: {e}")
            return []