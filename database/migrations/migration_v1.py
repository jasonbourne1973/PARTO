"""
Migration نسخه 1 - ساختار اولیه دیتابیس
"""

def upgrade(connection):
    """
    ارتقاء به نسخه 1
    """
    # ایجاد تمام جداول
    # (کد ایجاد جداول در connection.py پیاده‌سازی شده است)
    
    # ایجاد ایندکس‌ها
    # (کد ایجاد ایندکس‌ها در connection.py پیاده‌سازی شده است)
    
    # ایجاد تریگرهای Audit Log
    # (کد ایجاد تریگرها در connection.py پیاده‌سازی شده است)
    
    # Seed داده‌های اولیه
    # (کد Seed در connection.py پیاده‌سازی شده است)
    
    # (بازرسی شانزدهم — BUG-NEW-02) commit این‌جا حذف شد: تراکنش را فقط
    # MigrationManager._run_step (یا _heal_schema) باز و commit/rollback می‌کند.
    print("✅ Migration به نسخه 1 با موفقیت انجام شد.")


def downgrade(connection):
    """
    بازگشت از نسخه 1 (حذف تمام جداول)
    """
    cursor = connection.cursor()
    
    # لیست جداول به ترتیب وابستگی
    tables = [
        'audit_logs',
        'attachments',
        'followups',
        'interventions',
        'observations',
        'competencies',
        'student_academic_profiles',
        'teacher_assignments',
        'classes',
        'users',
        'staff',
        'students',
        'academic_years',
        'db_version'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"✅ جدول {table} حذف شد.")
        except Exception as e:
            print(f"⚠️ خطا در حذف جدول {table}: {e}")
    
    # (بازرسی شانزدهم — BUG-NEW-02) commit این‌جا حذف شد: تراکنش را فقط
    # MigrationManager._run_step (یا _heal_schema) باز و commit/rollback می‌کند.
    print("✅ بازگشت از نسخه 1 با موفقیت انجام شد.")