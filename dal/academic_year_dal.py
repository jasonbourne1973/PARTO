"""
لایه دسترسی به داده سال‌های تحصیلی
"""

import sqlite3

from database.connection import DatabaseConnection
from models.academic_year import AcademicYear


class AcademicYearDAL:
    """عملیات CRUD برای سال‌های تحصیلی"""

    def __init__(self):
        self.db = DatabaseConnection()

    def create(self, year):
        """ایجاد سال تحصیلی جدید"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            if year.is_active == 1:
                cursor.execute("UPDATE academic_years SET is_active = 0 WHERE is_deleted = 0")

            cursor.execute("""
                INSERT INTO academic_years (title, start_date, end_date, is_active, is_archived)
                VALUES (?, ?, ?, ?, ?)
            """, (
                year.title,
                year.start_date,
                year.end_date,
                year.is_active,
                year.is_archived
            ))

            self.db.commit()
            year.id = cursor.lastrowid
            return year

        except sqlite3.Error as e:
            self.db.rollback()
            raise Exception(f"خطا در ایجاد سال تحصیلی: {e}")

    def get_by_id(self, year_id):
        """دریافت سال تحصیلی با شناسه"""
        cursor = self.db.execute_query(
            "SELECT * FROM academic_years WHERE id = ? AND is_deleted = 0",
            (year_id,)
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_year(row)
        return None

    def get_all(self, include_archived=False):
        """دریافت همه سال‌های تحصیلی"""
        if include_archived:
            query = """
                SELECT * FROM academic_years
                WHERE is_deleted = 0
                ORDER BY id DESC
            """
        else:
            query = """
                SELECT * FROM academic_years
                WHERE is_deleted = 0 AND is_archived = 0
                ORDER BY id DESC
            """

        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        return [self._row_to_year(row) for row in rows]

    def get_active(self):
        """دریافت سال تحصیلی فعال"""
        cursor = self.db.execute_query("""
            SELECT * FROM academic_years
            WHERE is_active = 1
              AND is_archived = 0
              AND is_deleted = 0
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            return self._row_to_year(row)
        return None

    def get_by_title(self, title, include_archived=True):
        """دریافت سال تحصیلی بر اساس عنوان (مثلاً «۱۴۰۵-۱۴۰۶»)

        ===== اصلاح (بازرسی دوم) =====
        views/pages/promotion_page.py این متد را صدا می‌زد:

            existing = self.academic_year_dal.get_by_title(year_title)

        ولی چنین متدی در این DAL وجود نداشت. صفحه آن را با
        `except AttributeError: pass` می‌پوشاند و بعد در یک حلقه روی
        get_all() می‌گشت. مشکل حلقه این بود که get_all() به‌طور پیش‌فرض
        سال‌های بایگانی‌شده را برنمی‌گرداند (is_archived = 0)، پس اگر
        سال مقصد قبلاً ساخته و بایگانی شده بود، پیدا نمی‌شد و یک سال
        تحصیلی تکراری با همان عنوان ساخته می‌شد.

        حالا جست‌وجو مستقیم و شامل سال‌های بایگانی‌شده انجام می‌شود.
        """
        if not title:
            return None

        query = "SELECT * FROM academic_years WHERE title = ? AND is_deleted = 0"
        if not include_archived:
            query += " AND is_archived = 0"
        query += " LIMIT 1"

        cursor = self.db.execute_query(query, (title,))
        row = cursor.fetchone()
        if row:
            return self._row_to_year(row)
        return None

    def update(self, year):
        """به‌روزرسانی سال تحصیلی"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            if year.is_active == 1:
                cursor.execute("""
                    UPDATE academic_years
                    SET is_active = 0
                    WHERE id != ? AND is_deleted = 0
                """, (year.id,))

            cursor.execute("""
                UPDATE academic_years SET
                    title = ?, start_date = ?, end_date = ?,
                    is_active = ?, is_archived = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 0
            """, (
                year.title,
                year.start_date,
                year.end_date,
                year.is_active,
                year.is_archived,
                year.id
            ))

            self.db.commit()
            return year

        except sqlite3.Error as e:
            self.db.rollback()
            raise Exception(f"خطا در به‌روزرسانی سال تحصیلی: {e}")

    def delete(self, year_id):
        """حذف منطقی سال تحصیلی"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE academic_years
                SET is_deleted = 1,
                    is_active = 0,
                    deleted_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (year_id,))

            self.db.commit()
            return True

        except sqlite3.Error as e:
            self.db.rollback()
            raise Exception(f"خطا در حذف سال تحصیلی: {e}")

    def set_active(self, year_id):
        """تنظیم یک سال به عنوان سال فعال"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("UPDATE academic_years SET is_active = 0 WHERE is_deleted = 0")
            cursor.execute("""
                UPDATE academic_years
                SET is_active = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 0
            """, (year_id,))

            self.db.commit()
            return True

        except sqlite3.Error as e:
            self.db.rollback()
            raise Exception(f"خطا در فعال‌سازی سال تحصیلی: {e}")

    def archive(self, year_id):
        """بایگانی کردن یک سال تحصیلی"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE academic_years
                SET is_archived = 1, is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 0
            """, (year_id,))

            self.db.commit()
            return True

        except sqlite3.Error as e:
            self.db.rollback()
            raise Exception(f"خطا در بایگانی سال تحصیلی: {e}")

    def _row_to_year(self, row):
        """تبدیل ردیف دیتابیس به مدل AcademicYear"""
        year = AcademicYear()
        year.id = row['id']
        year.title = row['title']
        year.start_date = row['start_date']
        year.end_date = row['end_date']
        year.is_active = row['is_active']
        year.is_archived = row['is_archived']
        year.created_at = row['created_at']
        year.updated_at = row['updated_at']
        year.is_deleted = row['is_deleted']
        year.deleted_at = row['deleted_at']
        year.deleted_by = row['deleted_by']
        return year