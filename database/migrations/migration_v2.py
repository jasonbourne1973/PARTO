"""
Migration نسخه 2 - اضافه کردن جداول Indicator و ObservableBehavior
"""

def upgrade(connection):
    """
    ارتقاء به نسخه 2 - اضافه کردن جداول جدید
    """
    cursor = connection.cursor()
    
    # ===== ایجاد جدول indicators =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competency_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            deleted_by INTEGER,
            FOREIGN KEY (competency_id) REFERENCES competencies(id) ON DELETE CASCADE
        )
    """)
    
    # ===== ایجاد جدول observable_behaviors =====
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS observable_behaviors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_id INTEGER NOT NULL,
            competency_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            deleted_by INTEGER,
            FOREIGN KEY (indicator_id) REFERENCES indicators(id) ON DELETE CASCADE,
            FOREIGN KEY (competency_id) REFERENCES competencies(id) ON DELETE CASCADE
        )
    """)
    
    # ===== ایجاد ایندکس‌ها =====
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_indicators_competency_id ON indicators(competency_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_indicators_is_deleted ON indicators(is_deleted)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_behaviors_indicator_id ON observable_behaviors(indicator_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_behaviors_competency_id ON observable_behaviors(competency_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_behaviors_is_deleted ON observable_behaviors(is_deleted)")
    
    # ===== Seed کردن داده‌های شایستگی‌ها با ساختار جدید =====
    cursor.execute("SELECT COUNT(*) FROM competencies WHERE is_deleted = 0")
    if cursor.fetchone()[0] == 0:
        _seed_competencies_with_structure(cursor)
    
    connection.commit()
    print("✅ Migration به نسخه 2 با موفقیت انجام شد.")


def downgrade(connection):
    """
    بازگشت از نسخه 2 - حذف جداول جدید
    """
    cursor = connection.cursor()
    
    # حذف جداول جدید
    cursor.execute("DROP TABLE IF EXISTS observable_behaviors")
    cursor.execute("DROP TABLE IF EXISTS indicators")
    
    connection.commit()
    print("✅ بازگشت از نسخه 2 با موفقیت انجام شد.")


def _seed_competencies_with_structure(cursor):
    """Seed کردن داده‌های شایستگی‌ها با ساختار کامل"""
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    try:
        from data.competencies_data import COMPETENCIES_DATA
        
        for comp_data in COMPETENCIES_DATA:
            # ایجاد شایستگی
            cursor.execute("""
                INSERT INTO competencies (title, description, category, is_active)
                VALUES (?, ?, ?, ?)
            """, (
                comp_data["title"],
                comp_data["description"],
                comp_data["category"],
                1
            ))
            competency_id = cursor.lastrowid
            
            # ایجاد شاخص‌ها
            for idx, indicator_data in enumerate(comp_data.get("indicators", []), 1):
                cursor.execute("""
                    INSERT INTO indicators (competency_id, title, description, sort_order)
                    VALUES (?, ?, ?, ?)
                """, (
                    competency_id,
                    indicator_data["title"],
                    indicator_data["description"],
                    idx
                ))
                indicator_id = cursor.lastrowid
                
                # ایجاد رفتارهای قابل مشاهده
                for beh_idx, behavior_text in enumerate(
                    indicator_data.get("observable_behaviors", []), 1
                ):
                    cursor.execute("""
                        INSERT INTO observable_behaviors (indicator_id, competency_id, text, sort_order)
                        VALUES (?, ?, ?, ?)
                    """, (
                        indicator_id,
                        competency_id,
                        behavior_text,
                        beh_idx
                    ))
            
            print(f"  ✅ شایستگی '{comp_data['title']}' با {len(comp_data.get('indicators', []))} شاخص ایجاد شد.")
        
        print(f"✅ {len(COMPETENCIES_DATA)} شایستگی با شاخص‌ها و رفتارهای قابل مشاهده ایجاد شد.")
        
    except ImportError as e:
        print(f"⚠️ خطا در بارگذاری داده‌های شایستگی‌ها: {e}")
        _seed_basic_competencies(cursor)


def _seed_basic_competencies(cursor):
    """داده‌های پایه شایستگی‌ها (در صورت عدم وجود فایل داده)"""
    basic_competencies = [
        ("شناخت و بیان هیجان", "توانایی شناسایی و بیان احساسات", "emotional"),
        ("تنظیم هیجان", "توانایی مدیریت واکنش‌های هیجانی", "emotional"),
        ("تحمل ناکامی", "توانایی تحمل شکست و ادامه فعالیت", "emotional"),
        ("کنترل تکانه", "توانایی کنترل واکنش‌های فوری", "emotional"),
        ("خودباوری", "اعتماد به توانمندی خود", "emotional"),
        ("سازگاری با تغییر", "توانایی پذیرش تغییرات", "emotional"),
        ("همکاری", "مشارکت در فعالیت‌های گروهی", "social"),
        ("ارتباط مؤثر", "برقراری ارتباط مناسب", "social"),
        ("احترام", "رعایت حقوق دیگران", "social"),
        ("حل تعارض", "حل اختلاف از طریق گفتگو", "social"),
        ("مشارکت اجتماعی", "مشارکت در فعالیت‌های جمعی", "social"),
        ("مشارکت در یادگیری", "مشارکت در فعالیت‌های کلاسی", "educational"),
        ("پشتکار", "ادامه تلاش در فعالیت‌های دشوار", "educational"),
        ("مسئولیت‌پذیری آموزشی", "انجام تکالیف و پیگیری وظایف", "educational"),
        ("خودتنظیمی یادگیری", "مدیریت زمان و فعالیت‌های آموزشی", "educational"),
        ("رعایت قوانین", "رعایت قوانین مدرسه", "moral"),
        ("امانت‌داری", "مراقبت از وسایل دیگران", "moral"),
        ("صداقت", "پذیرش مسئولیت اشتباه", "moral"),
        ("مسئولیت‌پذیری اخلاقی", "انجام تعهدات", "moral"),
        ("مدیریت زمان", "استفاده مناسب از زمان", "self_management"),
        ("نظم فردی", "مراقبت از وسایل شخصی", "self_management"),
        ("مسئولیت‌پذیری فردی", "پذیرش و پیگیری مسئولیت‌ها", "self_management"),
        ("خودمدیریتی", "برنامه‌ریزی و پیگیری فعالیت‌ها", "self_management"),
        ("مشارکت فرهنگی", "مشارکت در فعالیت‌های فرهنگی", "participation"),
        ("مشارکت هنری", "مشارکت در فعالیت‌های هنری", "participation"),
        ("مشارکت ورزشی", "مشارکت در فعالیت‌های ورزشی", "participation"),
        ("مشارکت مذهبی", "مشارکت در فعالیت‌های مذهبی", "participation"),
        ("مسئولیت‌های دانش‌آموزی", "پذیرش نقش در مدرسه", "participation"),
    ]
    
    for title, description, category in basic_competencies:
        cursor.execute("""
            INSERT INTO competencies (title, description, category)
            VALUES (?, ?, ?)
        """, (title, description, category))
    
    print(f"✅ {len(basic_competencies)} شایستگی پایه ایجاد شد.")