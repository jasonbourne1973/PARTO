"""
Migration نسخه 4 - اضافه کردن جداول FamilyContext و ParentInterview
"""

def upgrade(connection):
    """
    ارتقاء به نسخه 4 - اضافه کردن جداول جدید
    """
    cursor = connection.cursor()
    
    # ===== ایجاد جدول family_contexts =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_profile_id INTEGER NOT NULL,
            guardian_status TEXT,
            guardian_notes TEXT,
            siblings_brothers INTEGER DEFAULT 0,
            siblings_sisters INTEGER DEFAULT 0,
            family_members INTEGER DEFAULT 0,
            school_contact TEXT,
            contact_details TEXT,
            has_study_space INTEGER DEFAULT 0,
            has_desk INTEGER DEFAULT 0,
            parental_support TEXT,
            educational_notes TEXT,
            economic_status TEXT,
            economic_notes TEXT,
            family_stress TEXT,
            health_issues TEXT,
            other_factors TEXT,
            notes TEXT,
            recorded_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            deleted_by INTEGER,
            FOREIGN KEY (student_profile_id) REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (recorded_by) REFERENCES staff(id) ON DELETE SET NULL
        )
    """)
    
    # ===== ایجاد جدول parent_interviews =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parent_interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_profile_id INTEGER NOT NULL,
            staff_id INTEGER NOT NULL,
            interview_date TEXT NOT NULL,
            interview_method TEXT,
            interviewer_name TEXT,
            parent_name TEXT NOT NULL,
            parent_relation TEXT,
            parent_phone TEXT,
            topic TEXT NOT NULL,
            topic_category TEXT,
            summary TEXT,
            details TEXT,
            key_points TEXT,
            result TEXT,
            outcome_notes TEXT,
            next_action TEXT,
            next_action_date TEXT,
            next_action_by TEXT,
            status TEXT DEFAULT 'scheduled',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            deleted_by INTEGER,
            FOREIGN KEY (student_profile_id) REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
        )
    """)
    
    # ===== ایجاد ایندکس‌ها =====
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_family_student_profile ON family_contexts(student_profile_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_family_is_deleted ON family_contexts(is_deleted)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interview_student_profile ON parent_interviews(student_profile_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interview_status ON parent_interviews(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interview_date ON parent_interviews(interview_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interview_is_deleted ON parent_interviews(is_deleted)")
    
    # (بازرسی شانزدهم — BUG-NEW-02) commit این‌جا حذف شد: تراکنش را فقط
    # MigrationManager._run_step (یا _heal_schema) باز و commit/rollback می‌کند.
    print("✅ Migration به نسخه 4 با موفقیت انجام شد.")


def downgrade(connection):
    """
    بازگشت از نسخه 4 - حذف جداول جدید
    """
    cursor = connection.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS parent_interviews")
    cursor.execute("DROP TABLE IF EXISTS family_contexts")
    
    # (بازرسی شانزدهم — BUG-NEW-02) commit این‌جا حذف شد: تراکنش را فقط
    # MigrationManager._run_step (یا _heal_schema) باز و commit/rollback می‌کند.
    print("✅ بازگشت از نسخه 4 با موفقیت انجام شد.")