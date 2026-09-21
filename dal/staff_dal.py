"""
لایه دسترسی به داده کادر مدرسه
"""

import sqlite3

from database.connection import DatabaseConnection
from models.staff import Staff
from utils.batch_query import id_chunks, placeholders
from utils.logger import get_logger
from utils.time_utils import utc_now_iso

logger = get_logger(__name__)


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
        
        self.db.commit()
        staff.id = cursor.lastrowid
        return staff
    
    def get_by_id(self, staff_id, include_deleted=True):
        """
        دریافت عضو کادر با شناسه

        ===== چرا include_deleted به‌طور پیش‌فرض True است؟ =====
        سوابق تاریخی (مشاهدات، مداخلات، پیگیری‌ها، جلسات مشاوره،
        مصاحبه‌ها، گزارش‌ها) همه به staff_id اشاره می‌کنند. اگر عضو
        کادری حذف منطقی شود و این متد او را برنگرداند، در همهٔ آن
        سوابق و در گزارش‌های چاپی نام فرد «نامشخص» می‌افتاد — یعنی
        تاریخچهٔ دانش‌آموز بی‌دلیل ناقص می‌شد.

        پس: برای «خواندن نام/سمت یک فرد در سابقه» از حالت پیش‌فرض
        استفاده کنید، و برای فهرست‌هایی که کاربر از آن‌ها انتخاب می‌کند
        (فرم‌ها، تنظیمات) از get_all() که حذف‌شده‌ها را فیلتر می‌کند.
        """
        query = "SELECT * FROM staff WHERE id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"

        cursor = self.db.execute_query(query, (staff_id,))
        row = cursor.fetchone()

        if row:
            return self._row_to_staff(row)
        return None

    def get_names_by_ids(self, staff_ids, include_deleted=True):
        """
        دریافت نام چند عضو کادر با «یک» کوئری (بازرسی دوازدهم: رفع N+1)

        جدول‌های مداخلات/پیگیری‌ها قبلاً برای هر ردیف یک get_by_id جدا
        می‌زدند. حالا شناسه‌ها یک‌جا خوانده می‌شوند. رفتار فیلتر
        حذف‌شده‌ها دقیقاً مثل get_by_id است (پیش‌فرض True: نام افراد
        حذف‌شده در سوابق تاریخی همچنان نمایش داده می‌شود).

        Returns:
            dict: {staff_id: full_name}
        """
        result = {}
        for chunk in id_chunks(staff_ids):
            query = f"SELECT id, full_name FROM staff WHERE id IN ({placeholders(len(chunk))})"
            if not include_deleted:
                query += " AND is_deleted = 0"
            cursor = self.db.execute_query(query, tuple(chunk))
            result.update({row['id']: row['full_name'] for row in cursor.fetchall()})
        return result

    def get_all(self, include_inactive=False, include_deleted=False):
        """
        دریافت همه اعضای کادر

        ===== اصلاح (بازرسی سوم) =====
        هیچ‌کدام از دو شاخهٔ این متد is_deleted را فیلتر نمی‌کردند.
        بعد از اینکه delete() از حذف فیزیکی به حذف منطقی اصلاح شد،
        بدون این فیلتر عضو حذف‌شده همچنان در فهرست‌ها و در
        کامبوباکس انتخاب معلم (۸+ فرم مختلف) ظاهر می‌شد.

        نکتهٔ رفتاری: delete() هم is_deleted=1 می‌گذارد و هم
        is_active=0 (همان قرارداد ClassDAL و TeacherAssignmentDAL)، تا
        ورود آن کاربر هم بسته شود. پس include_deleted=True به‌تنهایی
        هیچ حذف‌شده‌ای را برنمی‌گرداند — به همین دلیل این دو پرچم با هم
        ترکیب شده‌اند: include_deleted=True یعنی «همهٔ رکوردها، شامل
        حذف‌شده‌ها و غیرفعال‌ها» (کاربردش فهرست بازگردانی است).
        """
        query = "SELECT * FROM staff WHERE 1=1"
        if not include_deleted:
            query += " AND is_deleted = 0"
            if not include_inactive:
                query += " AND is_active = 1"
        query += " ORDER BY full_name"

        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        return [self._row_to_staff(row) for row in rows]

    def get_by_role(self, role, include_deleted=False):
        """دریافت اعضای کادر بر اساس سمت"""
        query = "SELECT * FROM staff WHERE role = ? AND is_active = 1"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY full_name"

        cursor = self.db.execute_query(query, (role,))
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
        
        self.db.commit()
        return staff
    
    def delete(self, staff_id, user_id=None):
        """
        حذف منطقی عضو کادر

        ===== 🔴 اصلاح بحرانی (بازرسی سوم) =====
        نسخهٔ قبلی این بود:

            cursor.execute("DELETE FROM staff WHERE id = ?", (staff_id,))

        یعنی **حذف فیزیکی**. و چون در database/connection.py دستور
        `PRAGMA foreign_keys = ON` اجرا می‌شود و یازده جدول به staff.id
        کلید خارجی با `ON DELETE CASCADE` دارند، یک بار کلیک روی
        «حذف» در صفحهٔ تنظیمات این‌ها را **برای همیشه** نابود می‌کرد:

            observations.staff_id            ← CASCADE
            interventions.staff_id           ← CASCADE
            followups.staff_id               ← CASCADE
            counseling_sessions.counselor_id ← CASCADE
            parent_interviews.staff_id       ← CASCADE
            screenings.staff_id              ← CASCADE
            screening_results.staff_id       ← CASCADE
            professional_interpretations.staff_id ← CASCADE
            teacher_assignments.staff_id     ← CASCADE
            users.staff_id                   ← CASCADE
            notifications.user_id            ← CASCADE

        تست عملی (قبل از اصلاح): با ساختن یک معلم، ۵ مشاهده، ۱ مداخله،
        ۱ پیگیری، ۱ مصاحبهٔ والدین و ۱ انتساب، سپس صدا زدن
        delete() روی آن معلم:

            observations                 5 → 0   🔴
            interventions                1 → 0   🔴
            followups                    1 → 0   🔴
            parent_interviews            1 → 0   🔴
            teacher_assignments          1 → 0   🔴
            staff                        3 → 2   🔴
            audit_logs                  40 → 40  (حذف اصلاً ثبت نشد!)

        یعنی **کل تاریخچهٔ رشد یک دانش‌آموز** با حذف معلمش از بین
        می‌رفت؛ بی‌بازگشت، و بدون هیچ ردی در گزارش حسابرسی — چون
        تریگرهای audit فقط روی UPDATE (is_deleted 0→1) کار می‌کنند و
        روی DELETE فیزیکی هرگز اجرا نمی‌شوند.

        این دقیقاً خلاف فلسفهٔ خود برنامه است: همهٔ DALهای دیگر
        (مشاهده، مداخله، پیگیری، دانش‌آموز، پرونده، شایستگی، ...)
        حذف منطقی می‌کنند و restore() دارند. staff تنها استثنا بود —
        و پراارجاع‌ترین موجودیت هم هست.

        حالا: حذف منطقی (is_deleted=1 + is_active=0)، با ثبت زمان و
        کاربر، تریگر audit به‌درستی اجرا می‌شود، و همهٔ سوابق دست‌نخورده
        می‌مانند. is_active=0 گذاشته می‌شود تا ورود آن کاربر هم بسته
        شود (login_dialog مقدار s.is_active را چک می‌کند).
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # ===== گارد: حساب «سیستم» حذف‌شدنی نیست =====
        # دیتابیس تازه یک عضو کادر با role='system' می‌سازد و حساب
        # کاربری پیش‌فرض «admin» به همان وصل است. حذفش یعنی از دست
        # رفتن حساب مدیر و بی‌نام شدن رکوردهای حسابرسی.
        cursor.execute("SELECT role FROM staff WHERE id = ?", (staff_id,))
        row = cursor.fetchone()
        if row is None:
            return False
        if (row['role'] or '') == 'system':
            raise ValueError(
                "حساب «سیستم» قابل حذف نیست؛ حساب کاربری مدیر (admin) "
                "به همین عضو کادر متصل است و رکوردهای حسابرسی به آن "
                "ارجاع می‌دهند. در صورت نیاز آن را غیرفعال کنید."
            )

        now = utc_now_iso()
        cursor.execute("""
            UPDATE staff SET
                is_deleted = 1,
                is_active = 0,
                deleted_at = ?,
                deleted_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (now, user_id, staff_id))

        affected = cursor.rowcount
        self.db.commit()
        return affected > 0

    def restore(self, staff_id, user_id=None):
        """
        بازگرداندن عضو کادر حذف‌شده (تا پیش از این اصلاً وجود نداشت)

        توجه: is_active عمداً ۱ نمی‌شود. بازگرداندن فقط رکورد و
        دسترسی به سابقه را برمی‌گرداند؛ فعال‌سازی مجدد یک تصمیم
        جداگانه است و باید با update() انجام شود تا کاربر آگاهانه
        آن را انجام دهد (وگرنه یک حساب غیرفعال ناگهان می‌توانست وارد
        برنامه شود).
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE staff SET
                is_deleted = 0,
                deleted_at = NULL,
                deleted_by = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 1
        """, (staff_id,))

        affected = cursor.rowcount
        self.db.commit()
        return affected > 0

    def permanent_delete(self, staff_id):
        """
        حذف دائمی عضو کادر — با گارد ایمنی

        ===== چرا این متد گارد دارد؟ =====
        هفت DAL دیگر پروژه (مشاهده، مداخله، پیگیری، دانش‌آموز، کاربر،
        پیوست، پشتیبان) هم delete() منطقی دارند و هم permanent_delete()
        صریح. staff تنها DALای بود که delete() عادی‌اش فیزیکی بود.

        اما permanent_delete روی staff با بقیه فرق مهمی دارد: یازده جدول
        به staff.id کلید خارجی با ON DELETE CASCADE دارند. یعنی حذف
        دائمی یک عضو کادر، هر رکوردی را که او ساخته برای همیشه می‌برد
        (مشاهده‌ها، مداخلات، پیگیری‌ها، جلسات مشاوره، مصاحبه‌ها،
        غربالگری‌ها، تفسیرها، انتساب‌ها، حساب کاربری، اعلان‌ها).

        پس این متد تنها وقتی اجازه دارد کار کند که آن فرد **هیچ** سابقه‌ای
        نداشته باشد — یعنی عملاً فقط برای پاک کردن رکوردی که اشتباهی
        ساخته شده. در غیر این صورت با پیام روشن رد می‌شود و کاربر را به
        همان delete() منطقی ارجاع می‌دهد که سابقه را حفظ می‌کند.
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT full_name, role FROM staff WHERE id = ?", (staff_id,))
        row = cursor.fetchone()
        if row is None:
            return False
        if (row['role'] or '') == 'system':
            raise ValueError(
                "حساب «سیستم» قابل حذف دائمی نیست؛ حساب کاربری مدیر "
                "(admin) به همین عضو کادر متصل است."
            )

        # جدول‌هایی که با ON DELETE CASCADE به staff.id وصل‌اند
        dependents = [
            ("observations", "staff_id", "مشاهده"),
            ("interventions", "staff_id", "مداخله"),
            ("followups", "staff_id", "پیگیری"),
            ("counseling_sessions", "counselor_id", "جلسهٔ مشاوره"),
            ("parent_interviews", "staff_id", "مصاحبه با والدین"),
            ("screenings", "staff_id", "غربالگری"),
            ("screening_results", "staff_id", "نتیجهٔ غربالگری"),
            ("professional_interpretations", "staff_id", "تفسیر حرفه‌ای"),
            ("teacher_assignments", "staff_id", "انتساب معلم"),
            ("users", "staff_id", "حساب کاربری"),
            ("notifications", "user_id", "اعلان"),
        ]
        blocking = []
        for table, column, label in dependents:
            try:
                n = cursor.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {column} = ?",
                    (staff_id,)
                ).fetchone()[0]
            except sqlite3.Error as _exc:
                logger.debug(f"خطای مدیریت‌شده در permanent_delete (مسیر جایگزین): {_exc}")
                continue
            if n:
                blocking.append(f"{n} {label}")

        if blocking:
            raise ValueError(
                f"«{row['full_name']}» سابقه دارد ({'، '.join(blocking)}) و "
                "حذف دائمی او این سابقه‌ها را برای همیشه نابود می‌کند — "
                "شامل تاریخچهٔ رشد دانش‌آموزان. به‌جای آن از حذف عادی "
                "استفاده کنید تا رکورد غیرفعال و از فهرست‌ها پنهان شود "
                "ولی همهٔ سوابق و نام فرد در گزارش‌ها حفظ شود."
            )

        cursor.execute("DELETE FROM staff WHERE id = ?", (staff_id,))
        affected = cursor.rowcount
        self.db.commit()
        return affected > 0

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
        # وضعیت حذف منطقی هم روی مدل منتقل می‌شود تا فراخوان بتواند
        # تشخیص دهد رکورد حذف‌شده است (مثلاً در نمایش سابقهٔ تاریخی
        # یک «(حذف‌شده)» کنار نام بگذارد).
        try:
            staff.is_deleted = row['is_deleted']
            staff.deleted_at = row['deleted_at']
            staff.deleted_by = row['deleted_by']
        except (IndexError, KeyError):
            # ردیف/کوئری بدون این ستون‌ها: مقادیر پیش‌فرض مدل (None)
            # حفظ می‌شود و بقیهٔ اطلاعات بارگذاری می‌شود.
            pass
        return staff