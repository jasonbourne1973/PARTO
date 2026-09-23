"""
Migration نسخه ۷ - ساخت جدول‌های گمشده و اصلاح ستون‌های ناقص

===== چرا این migration لازم است؟ =====
بررسی کد نشان داد چهار مشکل ساختاری وجود دارد که هیچ migration قبلی
آن‌ها را حل نمی‌کرد:

۱. جدول‌های `recommendations` و `saved_filters` هیچ‌جا ساخته نمی‌شدند،
   در حالی که RecommendationDAL و SavedFilterDAL روی آن‌ها کار می‌کنند.
   یعنی دو قابلیت کامل از روز اول با «no such table» شکست می‌خوردند.

۲. جدول `backups` وجود نداشت. اطلاعات پشتیبان فقط داخل خود فایل ZIP
   نگه داشته می‌شد، پس checksum هیچ‌وقت قابل بررسی نبود.

۳. جدول `attachments` ستون `updated_at` نداشت، ولی AttachmentDAL.update
   آن را ست می‌کرد ⇒ OperationalError: no such column: updated_at

۴. مدل Observation فیلدهای `indicator_id` و `observable_behavior_id`
   داشت (ساختار سه‌لایه شایستگی ← شاخص ← رفتار قابل مشاهده) ولی
   این ستون‌ها در جدول نبودند، پس مسیر سه‌لایه هرگز ذخیره نمی‌شد.

===== نکته درباره idempotent بودن =====
همه عملیات این فایل طوری نوشته شده‌اند که چند بار اجرا شدنشان مشکلی
نسازد. دلیلش باگ migration_v5 است که `ALTER TABLE ... ADD COLUMN total_score`
را بدون بررسی می‌زد و روی دیتابیسی که آن ستون را داشت با
«duplicate column name» می‌ترکید.
"""


# ============================================================
# ابزارهای کمکی
# ============================================================

def _table_exists(cursor, table_name):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def _column_exists(cursor, table_name, column_name):
    """
    بررسی وجود ستون با PRAGMA table_info

    این همان گاردی است که migration_v5 نداشت.
    """
    if not _table_exists(cursor, table_name):
        return False
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def _index_exists(cursor, index_name):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None


def _add_column(cursor, table_name, column_name, definition):
    """افزودن ستون فقط در صورت نبودن"""
    if _column_exists(cursor, table_name, column_name):
        print(f"  ⏭️  ستون {table_name}.{column_name} از قبل وجود دارد.")
        return False

    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {definition}")
    print(f"  ✅ ستون {table_name}.{column_name} اضافه شد.")
    return True


# ============================================================
# ساخت جدول‌ها
# ============================================================

def _create_recommendations(cursor):
    """جدول پیشنهادات هوشمند - مورد استفاده RecommendationDAL"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_profile_id INTEGER NOT NULL,
            staff_id INTEGER,
            rule_id TEXT,
            category TEXT,
            priority TEXT DEFAULT 'medium',
            title TEXT NOT NULL,
            description TEXT,
            suggested_action TEXT,
            suggested_intervention_type TEXT,
            related_competency_id INTEGER,
            related_observation_ids TEXT,
            score INTEGER DEFAULT 50,
            metadata TEXT,
            status TEXT DEFAULT 'pending',
            implemented_at TEXT,
            completed_at TEXT,
            feedback TEXT,
            feedback_notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            deleted_by INTEGER,
            FOREIGN KEY (student_profile_id)
                REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (staff_id)
                REFERENCES staff(id) ON DELETE SET NULL,
            FOREIGN KEY (related_competency_id)
                REFERENCES competencies(id) ON DELETE SET NULL
        )
    """)

    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_rec_student_profile_id "
        "ON recommendations(student_profile_id)",
        "CREATE INDEX IF NOT EXISTS idx_rec_status "
        "ON recommendations(status)",
        "CREATE INDEX IF NOT EXISTS idx_rec_priority "
        "ON recommendations(priority)",
        "CREATE INDEX IF NOT EXISTS idx_rec_category "
        "ON recommendations(category)",
        "CREATE INDEX IF NOT EXISTS idx_rec_is_deleted "
        "ON recommendations(is_deleted)",
    ):
        cursor.execute(statement)

    print("  ✅ جدول recommendations ساخته شد.")


def _create_saved_filters(cursor):
    """جدول فیلترهای ذخیره‌شده - مورد استفاده SavedFilterDAL"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            filter_type TEXT NOT NULL,
            visibility TEXT DEFAULT 'private',
            user_id INTEGER,
            filter_params TEXT,
            use_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            deleted_by INTEGER,
            FOREIGN KEY (user_id)
                REFERENCES staff(id) ON DELETE SET NULL
        )
    """)

    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_sf_user_id "
        "ON saved_filters(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_sf_filter_type "
        "ON saved_filters(filter_type)",
        "CREATE INDEX IF NOT EXISTS idx_sf_visibility "
        "ON saved_filters(visibility)",
        "CREATE INDEX IF NOT EXISTS idx_sf_is_deleted "
        "ON saved_filters(is_deleted)",
    ):
        cursor.execute(statement)

    print("  ✅ جدول saved_filters ساخته شد.")


def _create_backups(cursor):
    """
    جدول رکوردهای پشتیبان - مورد استفاده BackupDAL

    این جدول حلقه گمشده بررسی یکپارچگی است: checksum اینجا ذخیره
    می‌شود تا در زمان بازیابی بتوان مقایسه‌اش کرد.
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            checksum TEXT,
            kind TEXT DEFAULT 'manual',
            db_version INTEGER,
            attachments_count INTEGER,
            records_count INTEGER,
            notes TEXT,
            created_by INTEGER,
            is_verified INTEGER DEFAULT 0,
            verified_at TEXT,
            restored_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            deleted_by INTEGER,
            FOREIGN KEY (created_by)
                REFERENCES staff(id) ON DELETE SET NULL
        )
    """)

    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_backups_kind ON backups(kind)",
        "CREATE INDEX IF NOT EXISTS idx_backups_created_at ON backups(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_backups_checksum ON backups(checksum)",
        "CREATE INDEX IF NOT EXISTS idx_backups_is_deleted ON backups(is_deleted)",
    ):
        cursor.execute(statement)

    print("  ✅ جدول backups ساخته شد.")


# ============================================================
# اصلاح ستون‌های ناقص
# ============================================================

def _fix_missing_columns(cursor):
    """افزودن ستون‌هایی که مدل دارد ولی جدول نداشت"""

    # ۱. attachments.updated_at - AttachmentDAL.update آن را ست می‌کرد
    _add_column(cursor, "attachments", "updated_at",
                "updated_at TEXT")

    # ۲. ساختار سه‌لایه روی observations
    _add_column(cursor, "observations", "indicator_id",
                "indicator_id INTEGER REFERENCES indicators(id) ON DELETE SET NULL")
    _add_column(cursor, "observations", "observable_behavior_id",
                "observable_behavior_id INTEGER "
                "REFERENCES observable_behaviors(id) ON DELETE SET NULL")

    # ایندکس برای مسیر سه‌لایه
    if not _index_exists(cursor, "idx_obs_indicator_id"):
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_obs_indicator_id "
            "ON observations(indicator_id)"
        )
    if not _index_exists(cursor, "idx_obs_observable_behavior_id"):
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_obs_observable_behavior_id "
            "ON observations(observable_behavior_id)"
        )


def _create_missing_indexes(cursor):
    """
    ایندکس‌هایی که برای کوئری‌های سنگین لازم‌اند

    این‌ها کوئری‌های پرتکراری هستند که در گزارش بررسی به عنوان
    مشکل کارایی شناسایی شدند.
    """
    indexes = (
        # داشبورد: فیلتر بر اساس سال تحصیلی
        ("idx_profiles_is_deleted",
         "CREATE INDEX IF NOT EXISTS idx_profiles_is_deleted "
         "ON student_academic_profiles(is_deleted)"),
        # جوین مشاهده → پرونده (در داشبورد و گزارش‌ها زیاد استفاده می‌شود)
        ("idx_obs_is_deleted",
         "CREATE INDEX IF NOT EXISTS idx_obs_is_deleted "
         "ON observations(is_deleted)"),
        ("idx_inter_is_deleted",
         "CREATE INDEX IF NOT EXISTS idx_inter_is_deleted "
         "ON interventions(is_deleted)"),
        ("idx_follow_is_deleted",
         "CREATE INDEX IF NOT EXISTS idx_follow_is_deleted "
         "ON followups(is_deleted)"),
        ("idx_follow_date",
         "CREATE INDEX IF NOT EXISTS idx_follow_date ON followups(date)"),
        # غربالگری و تفسیر
        ("idx_screenings_student_profile_id",
         "CREATE INDEX IF NOT EXISTS idx_screenings_student_profile_id "
         "ON screenings(student_profile_id)"),
        ("idx_screenings_is_deleted",
         "CREATE INDEX IF NOT EXISTS idx_screenings_is_deleted "
         "ON screenings(is_deleted)"),
        ("idx_pi_student_profile_id",
         "CREATE INDEX IF NOT EXISTS idx_pi_student_profile_id "
         "ON professional_interpretations(student_profile_id)"),
        # کلاس‌ها: جست‌وجو بر اساس نام (چون جوین با class_name انجام می‌شود)
        ("idx_profiles_class_name",
         "CREATE INDEX IF NOT EXISTS idx_profiles_class_name "
         "ON student_academic_profiles(class_name)"),
    )

    for name, statement in indexes:
        if not _index_exists(cursor, name):
            cursor.execute(statement)
            print(f"  ✅ ایندکس {name} ساخته شد.")


def _seed_screening_tools(cursor):
    """
    seed ابزارهای غربالگری

    قبلاً این کار فقط در migration_v5 انجام می‌شد که هرگز در مسیر
    اجرای برنامه صدا زده نمی‌شد. نتیجه: روی نصب تازه لیست ابزارها
    خالی بود.
    """
    import json

    cursor.execute("SELECT COUNT(*) FROM screening_tools WHERE is_deleted = 0")
    if cursor.fetchone()[0] > 0:
        print("  ⏭️  ابزارهای غربالگری از قبل seed شده‌اند.")
        return

    default_tools = [
        {
            'name': 'چک‌لیست مشاهده رفتار',
            'version': '1.0',
            'type': 'observation',
            'description': 'چک‌لیست مشاهده رفتارهای دانش‌آموز در محیط مدرسه',
            'domains': ['رفتاری', 'اجتماعی', 'هیجانی'],
        },
        {
            'name': 'پرسشنامه بررسی وضعیت تحصیلی',
            'version': '1.0',
            'type': 'questionnaire',
            'description': 'پرسشنامه ساده برای بررسی وضعیت تحصیلی دانش‌آموز',
            'domains': ['آموزشی', 'مشارکت', 'مسئولیت‌پذیری'],
        },
        {
            'name': 'چک‌لیست مهارت‌های اجتماعی',
            'version': '1.0',
            'type': 'checklist',
            'description': 'چک‌لیست مشاهده مهارت‌های اجتماعی دانش‌آموز',
            'domains': ['اجتماعی', 'ارتباط', 'همکاری'],
        },
    ]

    for tool in default_tools:
        cursor.execute("""
            INSERT INTO screening_tools (
                name, version, type, description, domains, is_standard, status
            ) VALUES (?, ?, ?, ?, ?, 0, 'active')
        """, (
            tool['name'], tool['version'], tool['type'],
            tool['description'],
            json.dumps(tool['domains'], ensure_ascii=False)
        ))
        print(f"  ✅ ابزار '{tool['name']}' اضافه شد.")


def _seed_indicators(cursor):
    """
    seed ساختار سه‌لایه شایستگی

    قبلاً _seed_default_data فقط جدول competencies را پر می‌کرد و
    indicators و observable_behaviors خالی می‌ماندند - در حالی که
    لاگ می‌گفت «با شاخص‌های مشاهده‌پذیر ایجاد شد».
    """
    cursor.execute("SELECT COUNT(*) FROM indicators WHERE is_deleted = 0")
    if cursor.fetchone()[0] > 0:
        print("  ⏭️  شاخص‌ها از قبل seed شده‌اند.")
        return

    try:
        from data.competencies_data import COMPETENCIES_DATA
    except ImportError as e:
        print(f"  ⚠️  داده‌های شایستگی در دسترس نیست: {e}")
        return

    # نگاشت عنوان شایستگی → شناسه (چون competencies قبلاً seed شده)
    cursor.execute("SELECT id, title FROM competencies WHERE is_deleted = 0")
    competency_ids = {row[1]: row[0] for row in cursor.fetchall()}

    indicator_count = 0
    behavior_count = 0

    for comp_data in COMPETENCIES_DATA:
        competency_id = competency_ids.get(comp_data["title"])
        if not competency_id:
            # شایستگی در دیتابیس نیست؛ بسازش
            cursor.execute("""
                INSERT INTO competencies (title, description, category, is_active)
                VALUES (?, ?, ?, 1)
            """, (
                comp_data["title"],
                comp_data["description"],
                comp_data["category"]
            ))
            competency_id = cursor.lastrowid

        for idx, indicator_data in enumerate(comp_data.get("indicators", []), 1):
            cursor.execute("""
                INSERT INTO indicators (
                    competency_id, title, description, sort_order
                ) VALUES (?, ?, ?, ?)
            """, (
                competency_id,
                indicator_data["title"],
                indicator_data.get("description"),
                idx
            ))
            indicator_id = cursor.lastrowid
            indicator_count += 1

            for beh_idx, behavior_text in enumerate(
                indicator_data.get("observable_behaviors", []), 1
            ):
                cursor.execute("""
                    INSERT INTO observable_behaviors (
                        indicator_id, competency_id, text, sort_order
                    ) VALUES (?, ?, ?, ?)
                """, (indicator_id, competency_id, behavior_text, beh_idx))
                behavior_count += 1

    print(f"  ✅ {indicator_count} شاخص و {behavior_count} رفتار قابل مشاهده "
          f"seed شد.")


# ============================================================
# ورودی‌های اصلی migration
# ============================================================

def upgrade(connection):
    """ارتقاء به نسخه ۷"""
    print("🔄 اجرای Migration نسخه ۷...")
    cursor = connection.cursor()

    print("📋 ساخت جدول‌های گمشده:")
    _create_recommendations(cursor)
    _create_saved_filters(cursor)
    _create_backups(cursor)

    print("📋 اصلاح ستون‌های ناقص:")
    _fix_missing_columns(cursor)

    print("📋 ساخت ایندکس‌های کارایی:")
    _create_missing_indexes(cursor)

    print("📋 seed داده‌های اولیه:")
    _seed_indicators(cursor)
    _seed_screening_tools(cursor)

    # (بازرسی شانزدهم — BUG-NEW-02) commit این‌جا حذف شد: تراکنش را فقط
    # MigrationManager._run_step (یا _heal_schema) باز و commit/rollback می‌کند.
    print("✅ Migration به نسخه ۷ با موفقیت انجام شد.")


def downgrade(connection):
    """
    بازگشت از نسخه ۷

    نکته: DROP COLUMN فقط در SQLite ۳.۳۵ به بعد پشتیبانی می‌شود،
    پس داخل try/except گذاشته شده تا روی نسخه‌های قدیمی‌تر
    migration نصفه‌کاره نماند (باگ migration_v5).
    """
    print("🔄 بازگشت از نسخه ۷...")
    cursor = connection.cursor()

    for table in ("backups", "saved_filters", "recommendations"):
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"  🗑️  جدول {table} حذف شد.")

    for column in ("indicator_id", "observable_behavior_id"):
        try:
            cursor.execute(
                f"ALTER TABLE observations DROP COLUMN {column}"
            )
            print(f"  🗑️  ستون observations.{column} حذف شد.")
        except Exception as e:
            print(f"  ⚠️  حذف observations.{column} ممکن نشد: {e}")

    try:
        cursor.execute("ALTER TABLE attachments DROP COLUMN updated_at")
        print("  🗑️  ستون attachments.updated_at حذف شد.")
    except Exception as e:
        print(f"  ⚠️  حذف attachments.updated_at ممکن نشد: {e}")

    # (بازرسی شانزدهم — BUG-NEW-02) commit این‌جا حذف شد: تراکنش را فقط
    # MigrationManager._run_step (یا _heal_schema) باز و commit/rollback می‌کند.
    print("✅ بازگشت از نسخه ۷ انجام شد.")
