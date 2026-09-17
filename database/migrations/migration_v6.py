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
    
    # ===== ایجاد تریگرهای Audit =====
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_notifications_insert_audit
        AFTER INSERT ON notifications
        BEGIN
            INSERT INTO audit_logs (
                user_id, action, entity_type, entity_id, new_value
            ) VALUES (
                NEW.user_id,
                'create',
                'notification',
                NEW.id,
                json_object('id', NEW.id, 'type', NEW.type)
            );
        END
    """)
    
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_notifications_update_audit
        AFTER UPDATE ON notifications
        WHEN NEW.is_deleted = 0 AND OLD.is_deleted = 0
        BEGIN
            INSERT INTO audit_logs (
                user_id, action, entity_type, entity_id, old_value, new_value
            ) VALUES (
                NEW.user_id,
                'edit',
                'notification',
                NEW.id,
                json_object('id', OLD.id),
                json_object('id', NEW.id)
            );
        END
    """)
    
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