"""
Migration نسخه 5 - اضافه کردن جداول ابزارها و نتایج غربالگری
"""

def upgrade(connection):
    """
    ارتقاء به نسخه 5 - اضافه کردن جداول جدید
    """
    cursor = connection.cursor()
    
    # ===== ایجاد جدول screening_tools =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS screening_tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            version TEXT,
            type TEXT NOT NULL,
            description TEXT,
            reference TEXT,
            target_age_group TEXT,
            target_grade_range TEXT,
            domains TEXT,
            sub_domains TEXT,
            scoring_scale TEXT,
            min_score REAL,
            max_score REAL,
            cutoff_scores TEXT,
            status TEXT DEFAULT 'active',
            is_standard INTEGER DEFAULT 0,
            administration_time INTEGER,
            required_training INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            deleted_by INTEGER
        )
    """)
    
    # ===== ایجاد جدول screening_results =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS screening_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_profile_id INTEGER NOT NULL,
            staff_id INTEGER NOT NULL,
            tool_id INTEGER NOT NULL,
            execution_date TEXT NOT NULL,
            execution_context TEXT,
            raw_answers TEXT,
            raw_observations TEXT,
            domain_scores TEXT,
            total_score REAL,
            notes TEXT,
            duration_minutes INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            deleted_by INTEGER,
            FOREIGN KEY (student_profile_id) REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
            FOREIGN KEY (tool_id) REFERENCES screening_tools(id) ON DELETE CASCADE
        )
    """)
    
    # ===== اصلاح جدول screenings =====
    cursor.execute("""
        ALTER TABLE screenings ADD COLUMN tool_id INTEGER
    """)
    
    cursor.execute("""
        ALTER TABLE screenings ADD COLUMN domain_scores TEXT
    """)
    
    cursor.execute("""
        ALTER TABLE screenings ADD COLUMN total_score REAL
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_screenings_tool_id ON screenings(tool_id)
    """)
    
    # ===== ایجاد ایندکس‌ها =====
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_tools_name ON screening_tools(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_tools_type ON screening_tools(type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_tools_status ON screening_tools(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_tools_is_deleted ON screening_tools(is_deleted)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_results_student ON screening_results(student_profile_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_results_tool ON screening_results(tool_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_results_status ON screening_results(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_results_date ON screening_results(execution_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_results_is_deleted ON screening_results(is_deleted)")
    
    # ===== Seed کردن ابزارهای پیش‌فرض =====
    _seed_default_tools(cursor)
    
    connection.commit()
    print("✅ Migration به نسخه 5 با موفقیت انجام شد.")


def downgrade(connection):
    """
    بازگشت از نسخه 5 - حذف جداول جدید
    """
    cursor = connection.cursor()
    
    # حذف فیلدهای اضافه شده به screenings
    try:
        cursor.execute("ALTER TABLE screenings DROP COLUMN tool_id")
        cursor.execute("ALTER TABLE screenings DROP COLUMN domain_scores")
        cursor.execute("ALTER TABLE screenings DROP COLUMN total_score")
    except:
        pass
    
    cursor.execute("DROP TABLE IF EXISTS screening_results")
    cursor.execute("DROP TABLE IF EXISTS screening_tools")
    
    connection.commit()
    print("✅ بازگشت از نسخه 5 با موفقیت انجام شد.")


def _seed_default_tools(cursor):
    """Seed کردن ابزارهای غربالگری پیش‌فرض"""
    import json
    
    default_tools = [
        {
            'name': 'چک‌لیست مشاهده رفتار',
            'version': '1.0',
            'type': 'observation',
            'description': 'چک‌لیست مشاهده رفتارهای دانش‌آموز در محیط مدرسه',
            'domains': ['رفتاری', 'اجتماعی', 'هیجانی'],
            'is_standard': False,
        },
        {
            'name': 'پرسشنامه بررسی وضعیت تحصیلی',
            'version': '1.0',
            'type': 'questionnaire',
            'description': 'پرسشنامه ساده برای بررسی وضعیت تحصیلی دانش‌آموز',
            'domains': ['آموزشی', 'مشارکت', 'مسئولیت‌پذیری'],
            'is_standard': False,
        },
        {
            'name': 'چک‌لیست مهارت‌های اجتماعی',
            'version': '1.0',
            'type': 'checklist',
            'description': 'چک‌لیست مشاهده مهارت‌های اجتماعی دانش‌آموز',
            'domains': ['اجتماعی', 'ارتباط', 'همکاری'],
            'is_standard': False,
        }
    ]
    
    for tool_data in default_tools:
        cursor.execute("""
            INSERT INTO screening_tools (
                name, version, type, description,
                domains, is_standard, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tool_data['name'],
            tool_data['version'],
            tool_data['type'],
            tool_data['description'],
            json.dumps(tool_data['domains'], ensure_ascii=False),
            1 if tool_data['is_standard'] else 0,
            'active'
        ))
        print(f"  ✅ ابزار '{tool_data['name']}' ایجاد شد.")
    
    print(f"✅ {len(default_tools)} ابزار غربالگری پیش‌فرض ایجاد شد.")