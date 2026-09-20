"""
Migration نسخه 6 - اضافه کردن جدول notifications
"""

def upgrade(connection):
    """
    ارتقاء به نسخه 6 - اضافه کردن جدول notifications
    """
    cursor = connection.cursor()
    
    # ===== ایجاد جدول notifications =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            link TEXT,
            entity_type TEXT,
            entity_id INTEGER,
            is_read INTEGER DEFAULT 0,
            read_at TEXT,
            is_dismissed INTEGER DEFAULT 0,
            dismissed_at TEXT,
            scheduled_at TEXT,
            expires_at TEXT,
            related_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            FOREIGN KEY (user_id) REFERENCES staff(id) ON DELETE CASCADE
        )
    """)
    
    # ===== ایجاد ایندکس‌ها =====
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_is_dismissed ON notifications(is_dismissed)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_scheduled_at ON notifications(scheduled_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_is_deleted ON notifications(is_deleted)")
    
    # ===== تریگرهای Audit =====
    # (بازرسی پانزدهم) این migration دیگر تریگر نمی‌سازد. نسخهٔ قبلی
    # دو تریگر را به‌صورت «فقط اگر وجود نداشت» و فقط با id
    # می‌ساخت؛ یعنی روی دیتابیس‌های موجود هرگز به‌روز نمی‌شدند و
    # user_id گیرندهٔ اعلان را به‌جای انجام‌دهنده ثبت می‌کردند. تریگرهای
    # همهٔ جدول‌های حسابرسی‌شده (از جمله notifications) به‌صورت متمرکز در
    # DatabaseConnection._ensure_audit_triggers با DROP + CREATE در هر
    # راه‌اندازی ساخته/به‌روز می‌شوند (JSON کامل ردیف، انجام‌دهندهٔ
    # واقعی)، بدون حذف داده‌ای از audit_logs.

    connection.commit()
    print("✅ Migration به نسخه 6 با موفقیت انجام شد.")


def downgrade(connection):
    """
    بازگشت از نسخه 6 - حذف جدول notifications
    """
    cursor = connection.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS notifications")
    
    connection.commit()
    print("✅ بازگشت از نسخه 6 با موفقیت انجام شد.")