"""
Migration نسخه 3 - اضافه کردن جداول Screening و ProfessionalInterpretation
"""

def upgrade(connection):
    """
    ارتقاء به نسخه 3 - اضافه کردن جداول جدید
    """
    cursor = connection.cursor()
    
    # ===== ایجاد جدول screenings =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS screenings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_profile_id INTEGER NOT NULL,
            staff_id INTEGER NOT NULL,
            tool_name TEXT NOT NULL,
            tool_version TEXT,
            tool_reference TEXT,
            execution_date TEXT NOT NULL,
            execution_context TEXT,
            raw_scores TEXT,
            total_score REAL,
            domain TEXT,
            sub_domain TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            deleted_by INTEGER,
            FOREIGN KEY (student_profile_id) REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
        )
    """)
    
    # ===== ایجاد جدول professional_interpretations =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS professional_interpretations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_profile_id INTEGER NOT NULL,
            staff_id INTEGER NOT NULL,
            observation_id INTEGER,
            screening_id INTEGER,
            level TEXT NOT NULL,
            domain TEXT,
            title TEXT NOT NULL,
            summary TEXT,
            detailed_text TEXT NOT NULL,
            recommendations TEXT,
            next_steps TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            deleted_by INTEGER,
            FOREIGN KEY (student_profile_id) REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
            FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE SET NULL,
            FOREIGN KEY (screening_id) REFERENCES screenings(id) ON DELETE SET NULL
        )
    """)
    
    # ===== ایجاد ایندکس‌ها =====
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenings_student_profile ON screenings(student_profile_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenings_tool ON screenings(tool_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenings_domain ON screenings(domain)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenings_status ON screenings(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenings_date ON screenings(execution_date)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interpretations_student_profile ON professional_interpretations(student_profile_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interpretations_observation ON professional_interpretations(observation_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interpretations_screening ON professional_interpretations(screening_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interpretations_level ON professional_interpretations(level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interpretations_status ON professional_interpretations(status)")
    
    connection.commit()
    print("✅ Migration به نسخه 3 با موفقیت انجام شد.")


def downgrade(connection):
    """
    بازگشت از نسخه 3 - حذف جداول جدید
    """
    cursor = connection.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS professional_interpretations")
    cursor.execute("DROP TABLE IF EXISTS screenings")
    
    connection.commit()
    print("✅ بازگشت از نسخه 3 با موفقیت انجام شد.")