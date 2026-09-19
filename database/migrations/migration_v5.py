"""
Migration نسخه 5 - اضافه کردن جداول ابزارها و نتایج غربالگری

===== چه چیزی اصلاح شد =====
سه دستور `ALTER TABLE screenings ADD COLUMN ...` (tool_id، domain_scores،
total_score) بدون هیچ گاردی اجرا می‌شدند. ولی جدول `screenings` در
`_create_all_tables` از قبل با همین سه ستون ساخته می‌شود، پس اجرای این
migration روی هر دیتابیس نرمالی فوراً می‌ترکید:

    sqlite3.OperationalError: duplicate column name: tool_id

(تست شد: اجرای migration_v5.upgrade روی دیتابیس تازه ⇒ همین خطا.)
اگر هم دیتابیس قدیمی اصلاً جدول `screenings` نداشت، خطا
«no such table: screenings» می‌شد.

نتیجه: مسیر ارتقاء از نسخه ۴ به ۷ همیشه نصفه‌کاره می‌ماند.

حالا وجود جدول و ستون قبل از هر ALTER بررسی می‌شود، پس این migration
هم idempotent است و هم روی دیتابیس قدیمی/جدید یکسان کار می‌کند.
"""

import sqlite3


def _table_exists(cursor, table_name):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def _column_exists(cursor, table_name, column_name):
    if not _table_exists(cursor, table_name):
        return False
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def _add_column_if_missing(cursor, table_name, column_name, definition):
    """افزودن ستون فقط وقتی جدول هست و ستون نیست"""
    if not _table_exists(cursor, table_name):
        print(f"  ⏭️  جدول {table_name} وجود ندارد؛ افزودن {column_name} رد شد.")
        return False
    if _column_exists(cursor, table_name, column_name):
        print(f"  ⏭️  ستون {table_name}.{column_name} از قبل وجود دارد.")
        return False
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {definition}")
    print(f"  ✅ ستون {table_name}.{column_name} اضافه شد.")
    return True


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
    # گاردگذاری شد؛ توضیح کامل در docstring بالای همین فایل
    print("📋 بررسی ستون‌های جدول screenings:")
    _add_column_if_missing(cursor, "screenings", "tool_id", "tool_id INTEGER")
    _add_column_if_missing(cursor, "screenings", "domain_scores", "domain_scores TEXT")
    _add_column_if_missing(cursor, "screenings", "total_score", "total_score REAL")

    # ایندکس فقط وقتی ساخته شود که جدول و ستون واقعاً وجود داشته باشند؛
    # وگرنه «no such column: tool_id» می‌داد.
    if _column_exists(cursor, "screenings", "tool_id"):
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
    except sqlite3.OperationalError:
        # SQLite قدیمی‌تر از ۳٫۳۵ ستون DROP را پشتیبانی نمی‌کند؛ جدول
        # در ادامهٔ همین downgrade بازسازی می‌شود، پس بی‌اثر است.
        print("  ⚠️ حذف ستون‌های screenings روی این نسخهٔ SQLite ممکن نبود.")
    
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