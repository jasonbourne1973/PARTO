"""
لایه دسترسی به داده کاربران - با Soft Delete یکپارچه

این فایل جایگزین SQL پراکنده‌ای است که قبلاً در چهار فایل تکرار شده بود:
    - views/pages/settings_page.py       (افزودن/حذف/غیرفعال/ریست رمز)
    - views/dialogs/login_dialog.py      (احراز هویت)
    - views/dialogs/change_password_dialog.py (تغییر رمز)
    - database/connection.py             (seed کاربر admin)

===== نکته حیاتی =====
متد `authenticate` مقدار `staff_id` را برمی‌گرداند، نه `users.id`.
دلیل: جدول audit_logs.user_id یک FOREIGN KEY به staff(id) دارد و
`DatabaseConnection.set_current_user` هم کاربر را در جدول staff جست‌وجو
می‌کند. فرستادن users.id باعث می‌شد:
    ۱. INSERT در audit_logs با FOREIGN KEY constraint failed شکست بخورد
    ۲. set_current_user مقدار None ست کند و همه تریگرهای Audit
       بدون ثبت‌کننده (user_id=NULL) ثبت شوند
برای کاربر admin این باگ دیده نمی‌شد چون users.id و staff.id هر دو ۱ بودند.
"""

import sqlite3
from typing import ClassVar

from database.connection import DatabaseConnection
from models.user import User
from utils.logger import get_logger
from utils.security import (
    AccessControl,
    Permission,
    Security,
)
from utils.time_utils import utc_now_iso

logger = get_logger(__name__)


class UserDAL:
    """عملیات CRUD برای کاربران با Soft Delete یکپارچه"""

    def __init__(self):
        self.db = DatabaseConnection()

    # ============================================================
    # ایجاد
    # ============================================================

    def create(self, user, raw_password=None, must_change_password=None,
               user_id_actor=None):
        """
        ایجاد کاربر جدید

        Args:
            user: شیء User
            raw_password: رمز عبور خام. اگر داده شود هش می‌شود؛
                          در غیر این صورت از user.password_hash استفاده می‌شود.
            must_change_password: اگر None باشد، به‌طور پیش‌فرض ۱ ست می‌شود
                                  وقتی رمز را ادمین تعیین کرده است.
            user_id_actor: شناسه staff کسی که این کاربر را ساخته
                           (برای Audit Log — بازرسی هفتم)

        Returns:
            User: کاربر ایجاد شده

        Raises:
            ValueError: خطای اعتبارسنجی
            Exception: نام کاربری تکراری یا عضو کادر نامعتبر
        """
        # مرز مجوز backend (BUG-NAV-03): ساخت کاربر = MANAGE_USERS
        AccessControl.require_permission(
            Permission.MANAGE_USERS.value, action="UserDAL.create")
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # رمز خام را همان اول هش کن تا هیچ‌جا در حافظه نماند
        if raw_password:
            user.password_hash = Security.hash_password(raw_password)

        # نام کاربری یکدست شود
        user.username = User.normalize_username(user.username)

        # must_change_password: اگر ادمین رمز را تعیین کرده، کاربر باید عوضش کند
        if must_change_password is None:
            must_change_password = 1

        errors = user.validate()
        if errors:
            raise ValueError("\n".join(errors))

        # بررسی وجود عضو کادر
        cursor.execute(
            "SELECT id, full_name FROM staff WHERE id = ? AND is_deleted = 0",
            (user.staff_id,)
        )
        staff_row = cursor.fetchone()
        if not staff_row:
            raise ValueError(
                f"عضو کادر با شناسه {user.staff_id} وجود ندارد یا حذف شده است."
            )

        # بررسی تکراری نبودن نام کاربری (حتی بین رکوردهای حذف‌شده،
        # چون UNIQUE روی ستون username در دیتابیس بدون شرط است)
        if self.username_exists(user.username, include_deleted=True):
            raise ValueError(
                f"نام کاربری '{user.username}' قبلاً ثبت شده است."
            )

        # هشدار: یک عضو کادر نباید دو حساب کاربری فعال داشته باشد
        existing = self.get_by_staff_id(user.staff_id)
        if existing:
            raise ValueError(
                f"برای «{staff_row['full_name']}» قبلاً حساب کاربری "
                f"«{existing.username}» ثبت شده است."
            )

        try:
            cursor.execute("""
                INSERT INTO users (
                    staff_id, username, password_hash, role,
                    is_active, must_change_password
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user.staff_id,
                user.username,
                user.password_hash,
                user.role,
                user.is_active,
                1 if must_change_password else 0
            ))

            user.id = cursor.lastrowid
            user.staff_name = staff_row['full_name']
            user.must_change_password = 1 if must_change_password else 0

            # ===== اصلاح (بازرسی هفتم) =====
            # ساخت کاربر هیچ ردیفی در Audit Log نمی‌گذاشت؛ یعنی
            # «چه کسی این حساب را ساخت و با چه نقشی» جایی ثبت
            # نمی‌شد (جدول users تریگر Audit ندارد و بقیهٔ متدهای
            # این DAL خودشان _audit می‌زنند — فقط create جا افتاده
            # بود). حالا مثل بقیه رفتار می‌کند.
            self._audit(cursor, user_id_actor, 'create', 'user', user.id, {
                'username': user.username,
                'staff_id': user.staff_id,
                'role': user.role,
                'must_change_password': user.must_change_password,
            })

            self.db.commit()
            return user

        except sqlite3.IntegrityError as e:
            self.db.rollback()
            raise Exception(f"نام کاربری تکراری است یا داده نامعتبر: {e}")
        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError):
            self.db.rollback()
            raise

    # ============================================================
    # خواندن
    # ============================================================

    def get_by_id(self, user_id, include_deleted=False):
        """دریافت کاربر با شناسه"""
        query = """
            SELECT u.*, s.full_name AS staff_name, s.role AS staff_role
            FROM users u
            LEFT JOIN staff s ON u.staff_id = s.id
            WHERE u.id = ?
        """
        if not include_deleted:
            query += " AND u.is_deleted = 0"

        cursor = self.db.execute_query(query, (user_id,))
        row = cursor.fetchone()
        return self._row_to_user(row) if row else None

    def get_by_username(self, username, include_deleted=False):
        """دریافت کاربر با نام کاربری"""
        normalized = User.normalize_username(username)
        if not normalized:
            return None

        query = """
            SELECT u.*, s.full_name AS staff_name, s.role AS staff_role
            FROM users u
            LEFT JOIN staff s ON u.staff_id = s.id
            WHERE u.username = ?
        """
        if not include_deleted:
            query += " AND u.is_deleted = 0"

        cursor = self.db.execute_query(query, (normalized,))
        row = cursor.fetchone()
        return self._row_to_user(row) if row else None

    def get_by_staff_id(self, staff_id, include_deleted=False):
        """دریافت حساب کاربری یک عضو کادر"""
        query = "SELECT * FROM users WHERE staff_id = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY id LIMIT 1"

        cursor = self.db.execute_query(query, (staff_id,))
        row = cursor.fetchone()
        return self._row_to_user(row) if row else None

    def get_all(self, limit=None, offset=None, include_deleted=False):
        """
        دریافت همه کاربران

        نکته: offset فقط وقتی اعمال می‌شود که limit هم داده شده باشد
        (محدودیت SQL). اگر offset دادید و limit ندادید، از یک عدد بزرگ
        برای limit استفاده کنید.
        """
        query = """
            SELECT u.*, s.full_name AS staff_name, s.role AS staff_role
            FROM users u
            LEFT JOIN staff s ON u.staff_id = s.id
            WHERE 1=1
        """
        params = []

        if not include_deleted:
            query += " AND u.is_deleted = 0"

        query += " ORDER BY u.username"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

        cursor = self.db.execute_query(query, tuple(params) if params else None)
        return [self._row_to_user(row) for row in cursor.fetchall()]

    def get_active_users(self):
        """دریافت کاربران فعال (برای کمبوباکس‌ها)"""
        cursor = self.db.execute_query("""
            SELECT u.*, s.full_name AS staff_name, s.role AS staff_role
            FROM users u
            LEFT JOIN staff s ON u.staff_id = s.id
            WHERE u.is_deleted = 0 AND u.is_active = 1
            ORDER BY u.username
        """)
        return [self._row_to_user(row) for row in cursor.fetchall()]

    def get_deleted(self, limit=None):
        """دریافت کاربران حذف‌شده (برای سطل بازیافت)"""
        query = """
            SELECT u.*, s.full_name AS staff_name, s.role AS staff_role
            FROM users u
            LEFT JOIN staff s ON u.staff_id = s.id
            WHERE u.is_deleted = 1
            ORDER BY u.deleted_at DESC
        """
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.db.execute_query(query, tuple(params) if params else None)
        return [self._row_to_user(row) for row in cursor.fetchall()]

    def username_exists(self, username, include_deleted=False):
        """آیا این نام کاربری قبلاً گرفته شده؟"""
        normalized = User.normalize_username(username)
        if not normalized:
            return False

        query = "SELECT COUNT(*) AS c FROM users WHERE username = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"

        cursor = self.db.execute_query(query, (normalized,))
        row = cursor.fetchone()
        return bool(row and row['c'])

    def count(self, include_deleted=False, only_active=False):
        """تعداد کاربران"""
        query = "SELECT COUNT(*) AS c FROM users WHERE 1=1"
        if not include_deleted:
            query += " AND is_deleted = 0"
        if only_active:
            query += " AND is_active = 1"

        cursor = self.db.execute_query(query)
        row = cursor.fetchone()
        return row['c'] if row else 0

    # ============================================================
    # احراز هویت
    # ============================================================

    def authenticate(self, username, password):
        """
        احراز هویت کاربر

        Returns:
            dict با این کلیدها در صورت موفقیت:
                user_id       -> users.id   (برای کارهای مربوط به خود کاربر)
                staff_id      -> staff.id   (برای Audit Log و set_current_user)
                username      -> نام کاربری
                role          -> نقش کاربر
                full_name     -> نام کامل عضو کادر
                must_change_password -> bool
            None در صورت شکست.

            دلیل اینکه هر دو شناسه برگردانده می‌شوند:
            users.id برای جدول users است و staff.id برای audit_logs.
            اشتباه گرفتن این دو، باگ شماره ۱.۵ گزارش بررسی بود.
        """
        normalized = User.normalize_username(username)
        if not normalized or not password:
            return None

        cursor = self.db.execute_query("""
            SELECT u.id, u.staff_id, u.username, u.password_hash, u.role,
                   u.is_active, u.must_change_password,
                   s.full_name, s.is_active AS staff_active,
                   s.is_deleted AS staff_deleted
            FROM users u
            LEFT JOIN staff s ON u.staff_id = s.id
            WHERE u.username = ? AND u.is_deleted = 0
        """, (normalized,))
        row = cursor.fetchone()

        if not row:
            return None

        if row['is_active'] != 1:
            return None

        # عضو کادر مرتبط باید فعال و موجود باشد
        if row['staff_deleted'] or row['staff_active'] != 1:
            return None

        if not Security.verify_password(password, row['password_hash']):
            return None

        return {
            'user_id': row['id'],
            'staff_id': row['staff_id'],
            'username': row['username'],
            'role': row['role'],
            'full_name': row['full_name'],
            'must_change_password': row['must_change_password'] == 1,
        }

    def get_password_hash(self, user_id=None, username=None):
        """
        دریافت هش رمز عبور (برای دیالوگ تغییر رمز)

        فقط یکی از user_id یا username لازم است.
        """
        if user_id:
            cursor = self.db.execute_query(
                "SELECT password_hash FROM users WHERE id = ? "
                "AND is_deleted = 0 AND is_active = 1",
                (user_id,)
            )
        elif username:
            cursor = self.db.execute_query(
                "SELECT password_hash FROM users WHERE username = ? "
                "AND is_deleted = 0 AND is_active = 1",
                (User.normalize_username(username),)
            )
        else:
            return None

        row = cursor.fetchone()
        return row['password_hash'] if row else None

    # ============================================================
    # به‌روزرسانی
    # ============================================================

    def update(self, user):
        """به‌روزرسانی اطلاعات کاربر (بدون رمز عبور)"""
        # مرز مجوز backend (BUG-NAV-03): ویرایش کاربر = MANAGE_USERS؛
        # اگر نقش هم عوض شود، MANAGE_ROLES هم لازم است (جداسازی دو
        # مجوز طبق همان سیاست اعلام‌شده در Permission/ROLE_PERMISSIONS).
        AccessControl.require_permission(
            Permission.MANAGE_USERS.value, action="UserDAL.update")
        conn = self.db.get_connection()
        cursor = conn.cursor()

        old_role_row = cursor.execute(
            "SELECT role FROM users WHERE id = ? AND is_deleted = 0",
            (user.id,)).fetchone()
        if old_role_row is not None:
            old_role = (old_role_row["role"] or "").strip().lower()
            new_role = (user.role or "").strip().lower()
            if old_role != new_role:
                AccessControl.require_permission(
                    Permission.MANAGE_ROLES.value,
                    action="UserDAL.update(role_change)")

        user.username = User.normalize_username(user.username)

        errors = user.validate()
        # هش password_hash فقط برای create لازم است؛ در update هم باید باشد
        if errors:
            raise ValueError("\n".join(errors))

        try:
            cursor.execute("""
                UPDATE users SET
                    staff_id = ?, username = ?, role = ?,
                    is_active = ?, must_change_password = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 0
            """, (
                user.staff_id,
                user.username,
                user.role,
                user.is_active,
                1 if user.must_change_password else 0,
                user.id
            ))

            self.db.commit()
            return user

        except sqlite3.IntegrityError as e:
            self.db.rollback()
            raise Exception(f"نام کاربری تکراری است یا داده نامعتبر: {e}")
        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError):
            self.db.rollback()
            raise

    def update_password(self, user_id, new_raw_password,
                        clear_must_change=True, user_id_actor=None):
        """
        تغییر رمز عبور

        Args:
            user_id: شناسه کاربر
            new_raw_password: رمز خام جدید (همین‌جا هش می‌شود)
            clear_must_change: پرچم «باید رمز را عوض کند» پاک شود؟
                               برای ورود اول True، برای ریست توسط ادمین False.
            user_id_actor: شناسه staff کاربری که این تغییر را داده (برای Audit)

        Returns:
            bool
        """
        # مرز مجوز backend (BUG-NAV-03): تغییر رمز «خودِ کاربر» همیشه
        # مجاز است (وگرنه تغییر رمز در ورودِ اول می‌شکند)؛ تغییر رمز
        # کاربر دیگری = MANAGE_USERS.
        conn = self.db.get_connection()
        if AccessControl.has_session():
            try:
                own_row = conn.execute(
                    "SELECT id FROM users WHERE staff_id = ? "
                    "AND is_deleted = 0 ORDER BY is_active DESC, id LIMIT 1",
                    (AccessControl.current_staff_id(),),
                ).fetchone()
            except sqlite3.Error as e:
                # خواندن «کاربرِ همان نشست» ممکن نشد → سخت‌گیرانه: با
                # MANAGE_USERS بررسی می‌شود؛ لاگ برای ردیابی علت
                logger.debug(f"خواندن users.id نشست جاری شکست خورد: {e}")
                own_row = None
            if own_row is None or own_row["id"] != user_id:
                AccessControl.require_permission(
                    Permission.MANAGE_USERS.value,
                    action="UserDAL.update_password")
        cursor = conn.cursor()

        password_hash = Security.hash_password(new_raw_password)
        cursor.execute("""
            UPDATE users SET
                password_hash = ?,
                must_change_password = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0 AND is_active = 1
        """, (
            password_hash,
            0 if clear_must_change else 1,
            user_id
        ))

        if cursor.rowcount == 0:
            self.db.rollback()
            return False

        self.db.commit()
        self._audit(cursor, user_id_actor, 'edit', 'user', user_id,
                    {'password_changed': True})
        self.db.commit()
        return True

    def reset_password(self, user_id, user_id_actor=None, length=12):
        """
        ریست رمز عبور با تولید رمز تصادفی

        رمز جدید برگردانده می‌شود تا یک‌بار به کاربر نشان داده شود.
        پرچم must_change_password ست می‌شود چون رمز را ادمین تعیین کرده.

        Returns:
            str or None: رمز خام جدید (None اگر کاربر پیدا نشد)
        """
        # مرز مجوز backend (BUG-NAV-03): ریست رمز دیگران = MANAGE_USERS
        AccessControl.require_permission(
            Permission.MANAGE_USERS.value, action="UserDAL.reset_password")
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        new_password = ''.join(secrets.choice(alphabet) for _ in range(length))

        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users SET
                password_hash = ?,
                must_change_password = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (Security.hash_password(new_password), user_id))

        if cursor.rowcount == 0:
            self.db.rollback()
            return None

        self.db.commit()
        self._audit(cursor, user_id_actor, 'edit', 'user', user_id,
                    {'password_reset': True})
        self.db.commit()
        return new_password

    def update_last_login(self, user_id):
        """به‌روزرسانی زمان آخرین ورود"""
        conn = self.db.get_connection()
        conn.execute("""
            UPDATE users SET last_login = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (utc_now_iso(), user_id))
        self.db.commit()

    def set_active(self, user_id, is_active, user_id_actor=None):
        """فعال یا غیرفعال کردن کاربر"""
        # مرز مجوز backend (BUG-NAV-03): فعال/غیرفعال‌سازی = MANAGE_USERS
        AccessControl.require_permission(
            Permission.MANAGE_USERS.value, action="UserDAL.set_active")
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users SET
                is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (1 if is_active else 0, user_id))

        if cursor.rowcount == 0:
            self.db.rollback()
            return False

        self.db.commit()
        self._audit(cursor, user_id_actor, 'status_change', 'user', user_id,
                    {'is_active': 1 if is_active else 0})
        self.db.commit()
        return True

    def set_role(self, user_id, new_role, user_id_actor=None):
        """تغییر نقش کاربر"""
        # مرز مجوز backend (BUG-NAV-03): تغییر نقش = MANAGE_ROLES
        AccessControl.require_permission(
            Permission.MANAGE_ROLES.value, action="UserDAL.set_role")
        from models.enums import UserRole

        valid_roles = [role.value for role in UserRole]
        if new_role not in valid_roles:
            raise ValueError(f"نقش نامعتبر: {new_role}")

        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT role FROM users WHERE id = ? AND is_deleted = 0",
                       (user_id,))
        row = cursor.fetchone()
        if not row:
            return False
        old_role = row['role']

        cursor.execute("""
            UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (new_role, user_id))

        self.db.commit()
        self._audit(cursor, user_id_actor, 'role_change', 'user', user_id,
                    {'old_role': old_role, 'new_role': new_role})
        self.db.commit()
        return True

    # ============================================================
    # حذف و بازیابی
    # ============================================================

    def delete(self, user_id, user_id_actor=None):
        """حذف منطقی کاربر"""
        # مرز مجوز backend (BUG-NAV-03): حذف کاربر = MANAGE_USERS
        AccessControl.require_permission(
            Permission.MANAGE_USERS.value, action="UserDAL.delete")
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE id = ? AND is_deleted = 0", (user_id,))
        if not cursor.fetchone():
            return False

        now = utc_now_iso()
        cursor.execute("""
            UPDATE users SET
                is_deleted = 1,
                is_active = 0,
                deleted_at = ?,
                deleted_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 0
        """, (now, user_id_actor, user_id))

        self.db.commit()
        return True

    def restore(self, user_id, user_id_actor=None):
        """
        بازیابی کاربر حذف‌شده

        نکته: کاربر با وضعیت غیرفعال برمی‌گردد تا ادمین عمداً فعالش کند.
        پرچم must_change_password هم ست می‌شود چون ممکن است مدت زیادی
        از حذف گذشته باشد.
        """
        # مرز مجوز backend (BUG-NAV-03): بازیابی کاربر = MANAGE_USERS
        AccessControl.require_permission(
            Permission.MANAGE_USERS.value, action="UserDAL.restore")
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE id = ? AND is_deleted = 1", (user_id,))
        if not cursor.fetchone():
            return False

        cursor.execute("""
            UPDATE users SET
                is_deleted = 0,
                is_active = 0,
                must_change_password = 1,
                deleted_at = NULL,
                deleted_by = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_deleted = 1
        """, (user_id,))

        self.db.commit()
        self._audit(cursor, user_id_actor, 'restore', 'user', user_id,
                    {'restored': True})
        self.db.commit()
        return True

    def permanent_delete(self, user_id):
        """
        حذف فیزیکی - فقط برای موارد خاص

        (دور نوزدهم، مرحلهٔ ۸ — SEC-HARD-DELETE-01) قبلاً بدون هیچ
        بررسیِ Permission، ردیف مستقیماً DELETE می‌شد. هیچ جدولی به
        users.id کلید خارجی ندارد (جدول staff از این نظر مستقل است)،
        پس فقط Permission لازم است.
        """
        AccessControl.require_permission(
            Permission.MANAGE_USERS.value, action="UserDAL.permanent_delete")

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.db.commit()
        return cursor.rowcount > 0

    # ============================================================
    # آمار
    # ============================================================

    def get_stats(self):
        """آمار کلی کاربران برای داشبورد"""
        cursor = self.db.execute_query("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS inactive,
                SUM(CASE WHEN must_change_password = 1 THEN 1 ELSE 0 END) AS must_change
            FROM users
            WHERE is_deleted = 0
        """)
        row = cursor.fetchone()
        if not row:
            return {'total': 0, 'active': 0, 'inactive': 0, 'must_change': 0}

        return {
            'total': row['total'] or 0,
            'active': row['active'] or 0,
            'inactive': row['inactive'] or 0,
            'must_change': row['must_change'] or 0,
        }

    def get_by_role(self, role, include_deleted=False):
        """دریافت کاربران یک نقش خاص"""
        query = "SELECT * FROM users WHERE role = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        query += " ORDER BY username"

        cursor = self.db.execute_query(query, (role,))
        return [self._row_to_user(row) for row in cursor.fetchall()]

    # ============================================================
    # داخلی
    # ============================================================

    # نگاشت action دستی این DAL به تریگری که همان تغییر را ثبت می‌کند
    # (بازرسی دوازدهم: جدول users حالا تریگر حسابرسی دارد).
    _TRIGGER_AUDIT_ACTIONS: ClassVar[dict] = {
        'create': 'trg_users_insert_audit',
        'edit': 'trg_users_update_audit',
        'delete_soft': 'trg_users_soft_delete_audit',
        'restore': 'trg_users_restore_audit',
        'delete': 'trg_users_hard_delete_audit',
    }

    def _audit_covered_by_trigger(self, cursor, action):
        """
        آیا تریگر دیتابیس همین تغییر جدول users را ثبت می‌کند؟

        اگر بله، ثبت دستی باید رد شود وگرنه هر تغییر دو ردیف
        می‌گیرد (همان منطق BaseService._audit_handled_by_trigger ولی
        در سطح DAL؛ چون این DAL مستقیم INSERT می‌زند نه log_audit).
        actionهایی مثل status_change/role_change تریگر ندارند و
        همچنان دستی ثبت می‌شوند.
        """
        trigger = self._TRIGGER_AUDIT_ACTIONS.get(action)
        if not trigger:
            return False
        try:
            row = cursor.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type = 'trigger' AND name = ?",
                (trigger,),
            ).fetchone()
            return row is not None
        except sqlite3.Error as _exc:
            logger.debug(f"خطای مدیریت‌شده در _audit_covered_by_trigger (مسیر جایگزین): {_exc}")
            return False

    def _audit(self, cursor, user_id_actor, action, entity_type,
               entity_id, payload):
        """
        ثبت در Audit Log

        user_id_actor باید staff.id باشد. اگر None باشد، رکورد با
        user_id=NULL ثبت می‌شود (بهتر از شکست خوردن کل عملیات).
        """
        import json
        try:
            # ===== اصلاح (بازرسی هفتم) =====
            # نام موجودیت یکدست می‌شود ('user' → 'users') تا با
            # ردیف‌هایی که تریگرهای دیتابیس می‌نویسند و با
            # AuditLogDAL.get_logs هم‌خوان باشد. قبلاً همین DAL نام
            # مفرد می‌نوشت و جست‌وجوی تاریخچه با نام جدول نتیجه
            # نمی‌داد.
            try:
                from utils.security import normalize_entity_type
                entity_type = normalize_entity_type(entity_type)
            except (ImportError, AttributeError) as normalize_error:
                # نسخهٔ قدیمیِ security بدون این تابع → نام خام حفظ می‌شود
                logger.debug(
                    f"normalize_entity_type در دسترس نبود "
                    f"({normalize_error})؛ نام موجودیت خام ثبت می‌شود."
                )
            # ===== اصلاح (بازرسی دوازدهم) =====
            # اگر تریگر همان جدول/تغییر فعال است، ثبت دستی انجام
            # نمی‌شود تا ردیف تکراری ساخته نشود. (نام کاربر در ردیف
            # تریگر از کاربر جاریِ همان نخ می‌آید که هنگام لاگین ست
            # شده است.)
            if self._audit_covered_by_trigger(cursor, action):
                return
            cursor.execute("""
                INSERT INTO audit_logs (
                    user_id, action, entity_type, entity_id, new_value
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                user_id_actor,
                action,
                entity_type,
                entity_id,
                json.dumps(payload, ensure_ascii=False)
            ))
        except (sqlite3.Error, OSError, KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            # ثبت نشدن Audit نباید باعث شکست عملیات اصلی شود، ولی
            # بی‌صدا هم نباید بماند (وگرنه ردیابی رویدادها ممکن نیست).
            logger.debug(f"ثبت Audit ناموفق بود: {e}")

    def _row_to_user(self, row):
        """تبدیل ردیف دیتابیس به مدل User"""
        if row is None:
            return None

        user = User()
        user.id = row['id']
        user.staff_id = row['staff_id']
        user.username = row['username']
        user.password_hash = row['password_hash']
        user.role = row['role']
        user.is_active = row['is_active']
        user.must_change_password = row['must_change_password']
        user.last_login = row['last_login']
        user.created_at = row['created_at']
        user.updated_at = row['updated_at']

        # فیلدهای Soft Delete
        user.is_deleted = row['is_deleted']
        user.deleted_at = row['deleted_at']
        user.deleted_by = row['deleted_by']

        # فیلدهای کمکی (ممکن است در کوئری نباشند)
        keys = row.keys() if hasattr(row, 'keys') else []
        user.staff_name = row['staff_name'] if 'staff_name' in keys else None
        user.staff_role = row['staff_role'] if 'staff_role' in keys else None

        return user
