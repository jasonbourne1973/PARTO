"""
لایه دسترسی به داده اطلاعات زمینه‌ای خانواده (FamilyContext)
"""

from database.connection import DatabaseConnection
from models.family_context import FamilyContext
from utils.logger import get_logger
from utils.time_utils import utc_now_iso

logger = get_logger(__name__)


class FamilyContextDAL:
    """عملیات CRUD برای اطلاعات زمینه‌ای خانواده"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
    
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

    def count_for_profile(self, profile_id, include_deleted=True):
        """تعداد ردیف‌های زمینهٔ خانوادگی یک پرونده (برای تضمین نبود تکرار)"""
        query = "SELECT COUNT(*) FROM family_contexts WHERE student_profile_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        cursor = self.db.execute_query(query, (profile_id,))
        return cursor.fetchone()[0]

    def upsert_family_facts(self, profile_id, living_status=None,
                            siblings_brothers=None, siblings_sisters=None):
        """
        ثبت/به‌روزرسانی «اطلاعات پایهٔ خانواده» یک پرونده در «یک» ردیف
        (بازبینی نهایی — رفع BUG-GUI-02)

        چرا این متد؟ فرم دانش‌آموز سه ورودی خانوادگی دارد (وضعیت زندگی،
        تعداد برادران، تعداد خواهران). این داده‌ها جای قانونی‌شان در
        جدول family_contexts است، پس ذخیره باید:

          • برای هر پرونده دقیقاً یک ردیف بسازد (نه ردیف تکراری در هر ذخیره)،
          • نتیجهٔ واقعی درج/به‌روزرسانی را بررسی کند (rowcount)،
          • و در پایان، همان چیزی را که در دیتابیس نشسته بازبخواند.

        Args:
            profile_id: شناسهٔ پروندهٔ سالانه (student_profile_id)
            living_status: متن «وضعیت زندگی» فرم یا None (دست‌نخوردنی)
            siblings_brothers: تعداد برادران یا None (دست‌نخوردنی)
            siblings_sisters: تعداد خواهران یا None (دست‌نخوردنی)

        Returns:
            FamilyContext: ردیف بازخوانی‌شده از دیتابیس

        Raises:
            ValueError: اگر profile_id نامعتبر باشد
            RuntimeError: اگر درج/به‌روزرسانی واقعاً روی دیتابیس اثر نکند
        """
        if not profile_id:
            raise ValueError("ثبت اطلاعات خانوادگی بدون شناسهٔ پرونده ممکن نیست.")

        existing = self.get_by_student_profile(profile_id)
        context = existing or FamilyContext()
        context.student_profile_id = profile_id

        # مقدارهای None یعنی «این فیلد را تغییر نده» (حفظ رفتار قبلیِ داده)
        if living_status is not None:
            context.living_status = living_status
        if siblings_brothers is not None:
            context.siblings_brothers = max(0, int(siblings_brothers))
        if siblings_sisters is not None:
            context.siblings_sisters = max(0, int(siblings_sisters))

        conn = self.db.get_connection()
        cursor = conn.cursor()

        if existing is None:
            cursor.execute("""
                INSERT INTO family_contexts (
                    student_profile_id, guardian_status,
                    siblings_brothers, siblings_sisters
                ) VALUES (?, ?, ?, ?)
            """, (
                profile_id,
                context.guardian_status,
                context.siblings_brothers or 0,
                context.siblings_sisters or 0,
            ))
            if cursor.rowcount != 1 or not cursor.lastrowid:
                raise RuntimeError(
                    "درج اطلاعات خانوادگی روی دیتابیس اثر نکرد "
                    f"(rowcount={cursor.rowcount})."
                )
            context.id = cursor.lastrowid
            action = "ایجاد"
        else:
            cursor.execute("""
                UPDATE family_contexts SET
                    guardian_status = ?,
                    siblings_brothers = ?,
                    siblings_sisters = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 0
            """, (
                context.guardian_status,
                context.siblings_brothers or 0,
                context.siblings_sisters or 0,
                context.id,
            ))
            if cursor.rowcount != 1:
                raise RuntimeError(
                    "به‌روزرسانی اطلاعات خانوادگی روی دیتابیس اثر نکرد "
                    f"(rowcount={cursor.rowcount})."
                )
            action = "به‌روزرسانی"

        self.db.commit()

        # بازخوانی از دیتابیس: تنها شاهد «ذخیره‌شدن» همین است
        saved = self.get_by_student_profile(profile_id)
        if saved is None:
            raise RuntimeError(
                "اطلاعات خانوادگی پس از ذخیره در دیتابیس یافت نشد."
            )

        rows = self.count_for_profile(profile_id, include_deleted=False)
        if rows != 1:
            raise RuntimeError(
                f"برای این پرونده {rows} ردیف زمینهٔ خانوادگی ثبت شده است؛ "
                "باید دقیقاً یک ردیف باشد."
            )

        if (saved.siblings_brothers or 0) != (context.siblings_brothers or 0) \
                or (saved.siblings_sisters or 0) != (context.siblings_sisters or 0):
            raise RuntimeError(
                "اطلاعات خانوادگی ذخیره‌شده با ورودی مطابقت ندارد."
            )

        self.logger.info(
            f"{action} اطلاعات خانوادگی پرونده {profile_id}: "
            f"وضعیت زندگی={saved.living_status!r}، "
            f"برادر={saved.siblings_brothers}، خواهر={saved.siblings_sisters}"
        )
        return saved

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