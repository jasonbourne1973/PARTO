"""
مدیریت اتصال به دیتابیس SQLite - نسخه اصلاح شده با Migration
"""

import sqlite3
import os
import json
from datetime import datetime
import jdatetime
from config.settings import DB_PATH, DB_VERSION, DB_VERSION_FILE


class DatabaseConnection:
    """اتصال دیتابیس با الگوی Singleton و پشتیبانی از Audit Log و Migration"""
    
    _instance = None
    _connection = None
    _audit_enabled = True
    _current_user_id = None
    _initialized = False

    # ===== تراکنش واقعی =====
    # نسخه قبلی `begin_transaction()` در BaseService فقط یک بولین
    # ست می‌کرد؛ DALها همچنان بعد از هر دستور commit می‌زدند.
    # نتیجه: rollback هیچ اثری نداشت و داده نیمه‌نوشته باقی می‌ماند.
    #
    # حالا یک شمارنده عمق تراکنش داریم. تا وقتی تراکنش باز است،
    # متد commit() پایین‌دستی بی‌اثر می‌شود و فقط commit_transaction()
    # لایه سرویس واقعاً commit می‌کند.
    _transaction_depth = 0
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def get_connection(self, user_id=None):
        """دریافت اتصال به دیتابیس با تنظیم کاربر جاری"""
        if user_id is not None:
            self._current_user_id = user_id

        if self._connection is None:
            db_dir = os.path.dirname(DB_PATH)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)

            # ===== اصلاح مهم: کار با ترد =====
            # NotificationScheduler._worker کار دیتابیس را روی یک
            # threading.Thread جداگانه انجام می‌دهد. اتصال پیش‌فرض
            # sqlite3 اجازه استفاده از اتصال در ترد دیگر را نمی‌دهد و
            # ProgrammingError می‌دهد. آن خطا هم با `except Exception`
            # بلعیده می‌شد، پس یادآورها هرگز ساخته نمی‌شدند.
            self._connection = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row

            # حتماً FK روشن باشد
            self._connection.execute("PRAGMA foreign_keys = ON")

            # ===== اصلاح مهم: همزمانی =====
            # WAL اجازه می‌دهد خواننده‌ها همزمان با نویسنده کار کنند
            # (برای ترد زمان‌بند اعلان‌ها و رابط کاربری ضروری است).
            # busy_timeout هم جلوی "database is locked" فوری را می‌گیرد.
            try:
                self._connection.execute("PRAGMA journal_mode = WAL")
                self._connection.execute("PRAGMA busy_timeout = 5000")
                self._connection.execute("PRAGMA synchronous = NORMAL")
            except sqlite3.Error as e:
                # WAL روی برخی سیستم‌فایل‌ها (شبکه/فلش FAT) ممکن نیست؛
                # برنامه نباید به همین دلیل بالا نیاید.
                print(f"هشدار: تنظیم WAL ممکن نشد: {e}")

            # نکته خیلی مهم:
            # هرگز 0 برنگردان؛ چون audit_logs.user_id به staff.id وصل است
            def get_current_user_id():
                return self._current_user_id if self._current_user_id else None

            self._connection.create_function("get_current_user_id", 0, get_current_user_id)

            # ===== 🔴 اصلاح (بازرسی سوم) — ترتیب اعتبارسنجی کاربر جاری =====
            # تریگرهای حسابرسی، شناسهٔ کاربر جاری را در audit_logs.user_id
            # می‌نویسند و آن ستون به staff.id کلید خارجی دارد:
            #
            #     CREATE TRIGGER trg_<table>_insert_audit AFTER INSERT ...
            #         INSERT INTO audit_logs (user_id, ...) VALUES
            #             (get_current_user_id(), ...);
            #
            # اعتبارسنجیِ _current_user_id قبلاً «بعد از»
            # _initialize_database() انجام می‌شد (پایین‌تر:
            # `if self._current_user_id: self.set_current_user(...)`).
            # ولی INSERTهای خودِ seed «داخل» _initialize_database() اجرا
            # می‌شوند. یعنی اگر شناسهٔ کاربر جاری در staff وجود نداشت،
            # همان seed با خطای گمراه‌کنندهٔ زیر شکست می‌خورد و
            # دیتابیس اصلاً ساخته نمی‌شد:
            #
            #     sqlite3.IntegrityError: FOREIGN KEY constraint failed
            #
            # سناریوی واقعی: شناسهٔ کاربری که قبلاً لاگین کرده و حالا
            # عضو کادرش حذف شده (یا دیتابیس تازه/جابه‌جاشده) — آن‌وقت
            # «هر» نوشتنی در برنامه با همان خطا شکست می‌خورد.
            # (نکتهٔ خودِ نویسنده در get_current_user_id هم به همین FK
            # اشاره دارد، ولی فقط جلوی مقدار 0 را گرفته بود، نه شناسهٔ
            # ناموجود.)
            #
            # حالا اعتبارسنجی «قبل از» مقداردهی اولیه انجام می‌شود و اگر
            # جدول staff هنوز ساخته نشده باشد، شناسهٔ درخواستی نگه داشته
            # می‌شود تا بعد از seed دوباره و کامل اعتبارسنجی شود.
            pending_user_id = self._current_user_id
            state = self._validate_current_user()

            # اجرای Migration به جای ایجاد مستقیم جداول
            self._initialize_database()

            # دیتابیس‌های ساخته‌شده در نسخه‌های قبلی ممکن است نسخه‌شان به‌روز
            # باشد اما سه جدول قابلیت‌های جدید را نداشته باشند. این بررسی
            # غیرمخرب فقط جدول‌های مفقود را ایجاد می‌کند.
            self._ensure_feature_tables()

            # اگر کاربری قبلاً set شده بود، بعد از seed اعتبارسنجی‌اش کن
            if state == self._USER_CHECK_DEFERRED and pending_user_id:
                self.set_current_user(pending_user_id)
            elif self._current_user_id:
                self.set_current_user(self._current_user_id)

        else:
            # برای اطمینان
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._validate_current_user()
            self._ensure_feature_tables()

        return self._connection

    # نتیجهٔ _validate_current_user
    _USER_CHECK_OK = "ok"            # شناسه معتبر است
    _USER_CHECK_CLEARED = "cleared"  # شناسه نامعتبر بود و None شد
    _USER_CHECK_DEFERRED = "deferred"  # جدول staff هنوز نبود؛ بعداً بررسی کن

    def _validate_current_user(self):
        """
        اطمینان از اینکه _current_user_id به یک ردیف واقعیِ staff اشاره می‌کند

        چرا لازم است: تریگرهای حسابرسی این مقدار را در audit_logs.user_id
        می‌نویسند که به staff.id کلید خارجی دارد. شناسهٔ ناموجود یعنی
        شکستِ «هر» INSERT با خطای FOREIGN KEY constraint failed.

        این متد برخلاف set_current_user در برابر «جدول staff هنوز وجود
        ندارد» مقاوم است، چون ممکن است قبل از ساخته‌شدن دیتابیس صدا شود.
        """
        if not self._current_user_id:
            return self._USER_CHECK_OK
        if self._connection is None:
            return self._USER_CHECK_DEFERRED

        requested = self._current_user_id
        try:
            row = self._connection.execute(
                "SELECT id FROM staff WHERE id = ?", (requested,)
            ).fetchone()
        except sqlite3.Error:
            # جدول staff هنوز ساخته نشده (اولین مقداردهی اولیهٔ دیتابیس).
            # موقتاً None می‌کنیم تا INSERTهای seed شکست نخورند؛
            # فراخوان بعد از _initialize_database() دوباره و کامل
            # اعتبارسنجی می‌کند.
            self._current_user_id = None
            return self._USER_CHECK_DEFERRED

        if row is None:
            print(f"⚠️ user_id={requested} در جدول staff وجود ندارد؛ "
                  "Audit Log با NULL ثبت می‌شود تا نوشتن رکوردها شکست نخورد.")
            self._current_user_id = None
            return self._USER_CHECK_CLEARED

        return self._USER_CHECK_OK
    
    def _ensure_feature_tables(self):
        """ایجاد جداول قابلیت‌های جدید در دیتابیس‌های قدیمی.

        Migration قبلی فقط بر اساس شماره نسخه اجرا می‌شود. اگر دیتابیس قبل
        از اضافه‌شدن قابلیت‌های مشاوره، فوق‌برنامه و اهداف ساخته شده باشد،
        شماره نسخه ممکن است جدید باشد اما جدول‌ها وجود نداشته باشند. این متد
        فقط وجود جدول را بررسی می‌کند و هیچ رکوردی را حذف یا بازنویسی نمی‌کند.
        """
        if self._connection is None:
            return

        required_tables = {
            "counseling_sessions",
            "extracurricular_activities",
            "individual_goals",
        }
        rows = self._connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        existing_tables = {row[0] for row in rows}
        if required_tables.issubset(existing_tables):
            return

        cursor = self._connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS counseling_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_profile_id INTEGER NOT NULL,
                counselor_id INTEGER NOT NULL,
                referred_by INTEGER,
                session_date TEXT NOT NULL,
                session_time TEXT,
                duration_minutes INTEGER,
                type TEXT NOT NULL,
                method TEXT,
                location TEXT,
                topic TEXT,
                goals TEXT,
                summary TEXT,
                details TEXT,
                interventions_discussed TEXT,
                recommendations TEXT,
                homework TEXT,
                outcome TEXT,
                follow_up_needed INTEGER DEFAULT 0,
                next_session_date TEXT,
                next_session_notes TEXT,
                status TEXT DEFAULT 'scheduled',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (student_profile_id)
                    REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (counselor_id)
                    REFERENCES staff(id) ON DELETE CASCADE,
                FOREIGN KEY (referred_by)
                    REFERENCES staff(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracurricular_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_profile_id INTEGER NOT NULL,
                teacher_id INTEGER,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT,
                duration_hours INTEGER,
                location TEXT,
                participation_level TEXT,
                role TEXT,
                team_name TEXT,
                result TEXT,
                achievements TEXT,
                feedback TEXT,
                status TEXT DEFAULT 'planned',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (student_profile_id)
                    REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id)
                    REFERENCES staff(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS individual_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_profile_id INTEGER NOT NULL,
                created_by INTEGER,
                assigned_to INTEGER,
                related_competency_id INTEGER,
                related_intervention_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                domain TEXT,
                priority TEXT DEFAULT 'medium',
                success_criteria TEXT,
                target_date TEXT,
                start_date TEXT,
                end_date TEXT,
                progress_percent INTEGER DEFAULT 0,
                progress_notes TEXT,
                status TEXT DEFAULT 'draft',
                result TEXT,
                achievement_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (student_profile_id)
                    REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by)
                    REFERENCES staff(id) ON DELETE SET NULL,
                FOREIGN KEY (assigned_to)
                    REFERENCES staff(id) ON DELETE SET NULL,
                FOREIGN KEY (related_competency_id)
                    REFERENCES competencies(id) ON DELETE SET NULL,
                FOREIGN KEY (related_intervention_id)
                    REFERENCES interventions(id) ON DELETE SET NULL
            )
        """)

        # ایندکس‌ها نیز فقط در صورت نبودن ساخته می‌شوند.
        indexes = (
            "CREATE INDEX IF NOT EXISTS idx_cs_student_profile_id "
            "ON counseling_sessions(student_profile_id)",
            "CREATE INDEX IF NOT EXISTS idx_cs_counselor_id "
            "ON counseling_sessions(counselor_id)",
            "CREATE INDEX IF NOT EXISTS idx_cs_session_date "
            "ON counseling_sessions(session_date)",
            "CREATE INDEX IF NOT EXISTS idx_cs_status "
            "ON counseling_sessions(status)",
            "CREATE INDEX IF NOT EXISTS idx_cs_is_deleted "
            "ON counseling_sessions(is_deleted)",
            "CREATE INDEX IF NOT EXISTS idx_ea_student_profile_id "
            "ON extracurricular_activities(student_profile_id)",
            "CREATE INDEX IF NOT EXISTS idx_ea_type "
            "ON extracurricular_activities(type)",
            "CREATE INDEX IF NOT EXISTS idx_ea_status "
            "ON extracurricular_activities(status)",
            "CREATE INDEX IF NOT EXISTS idx_ea_start_date "
            "ON extracurricular_activities(start_date)",
            "CREATE INDEX IF NOT EXISTS idx_ea_is_deleted "
            "ON extracurricular_activities(is_deleted)",
            "CREATE INDEX IF NOT EXISTS idx_ig_student_profile_id "
            "ON individual_goals(student_profile_id)",
            "CREATE INDEX IF NOT EXISTS idx_ig_status "
            "ON individual_goals(status)",
            "CREATE INDEX IF NOT EXISTS idx_ig_domain "
            "ON individual_goals(domain)",
            "CREATE INDEX IF NOT EXISTS idx_ig_priority "
            "ON individual_goals(priority)",
            "CREATE INDEX IF NOT EXISTS idx_ig_is_deleted "
            "ON individual_goals(is_deleted)",
        )
        for statement in indexes:
            cursor.execute(statement)

        self._connection.commit()
        print("✅ جداول مشاوره، فعالیت‌های فوق‌برنامه و اهداف بررسی/تکمیل شدند.")

    def _initialize_database(self):
        """مدیریت نسخه‌بندی و اجرای Migration"""
        if self._initialized:
            return
            
        current_version = self._get_db_version()
        
        if current_version == 0:
            # دیتابیس جدید - ایجاد ساختار کامل
            self._create_all_tables()
            self._create_indexes()
            self._create_audit_triggers()
            self._seed_default_data()
            self._set_db_version(DB_VERSION)
        elif current_version < DB_VERSION:
            # ارتقاء دیتابیس
            self._migrate_database(current_version, DB_VERSION)
        # else: دیتابیس به‌روز است

        # ===== اصلاح بحرانی =====
        # ترمیم ساختار، فارغ از شماره نسخه‌ای که در db_version ثبت شده.
        # توضیح کامل در docstring متد _heal_schema آمده است.
        self._heal_schema()

        self._initialized = True

    # ماژول‌های migration که کاملاً «چندباراجراشدنی» (idempotent) هستند:
    # یعنی هر دستورشان یا IF NOT EXISTS دارد یا قبلش وجود ستون/جدول/داده
    # بررسی می‌شود. این‌ها را می‌توان در هر اجرا با خیال راحت صدا زد.
    _IDEMPOTENT_MIGRATIONS = ("migration_v7",)

    def _heal_schema(self):
        """
        ترمیم ساختار دیتابیس بدون توجه به شماره نسخه ثبت‌شده

        ===== چرا این متد لازم است؟ (باگ بحرانی نصب تازه) =====
        مسیر قبلی _initialize_database برای یک دیتابیس **تازه** این بود:

            _create_all_tables()   ← ۲۵ جدول «مدل نهایی»
            _create_indexes()
            _create_audit_triggers()
            _seed_default_data()
            _set_db_version(7)     ← نسخه ۷ مُهر می‌خورد!

        یعنی هیچ‌کدام از فایل‌های database/migrations/migration_vN.py
        اجرا نمی‌شدند، اما شماره نسخه روی ۷ تنظیم می‌شد. از آن به بعد
        `current_version == DB_VERSION` بود و برنامه همیشه می‌گفت
        «دیتابیس به‌روز است» ⇒ آن سه جدول و آن ستون‌ها **هرگز** ساخته
        نمی‌شدند.

        نتیجه روی هر نصب تازه (و همین دیتابیس موجود در مخزن که
        version=7 دارد):

            ❌ no such table: recommendations      → پیشنهادها
            ❌ no such table: saved_filters        → فیلترهای ذخیره‌شده
            ❌ no such table: backups              → صفحه پشتیبان‌گیری
            ❌ no such column: attachments.updated_at → ویرایش پیوست
            ❌ table observations has no column named indicator_id
               و observable_behavior_id → ساختار سه‌لایه
               (شایستگی ← شاخص ← رفتار قابل مشاهده) ذخیره نمی‌شد
            ❌ indicators / observable_behaviors / screening_tools خالی
               در حالی که لاگ می‌گفت «۲۸ شایستگی با شاخص‌های
               مشاهده‌پذیر ایجاد شد»

        بدتر اینکه این خطاها بلعیده می‌شدند؛ مثلاً خروجی واقعی
        RecommendationService روی نصب تازه این بود:

            ERROR | خطا در ذخیره پیشنهاد: no such table: recommendations
            INFO  | 0 پیشنهاد برای دانش‌آموز ... تولید شد.

        یعنی کاربر فکر می‌کرد «پیشنهادی پیدا نشد»، نه اینکه قابلیتی خراب است.

        ===== رفتار جدید =====
        بعد از هر مسیر ساخت/ارتقاء، migration های idempotent اجرا می‌شوند
        تا هر شیء مفقود ساخته شود. اجرای چندباره‌شان بی‌خطر است (تست شد:
        دو بار پشت سر هم بدون خطا و بدون ساخت داده تکراری).
        """
        import importlib

        # بررسی سریع: اگر همه چیز سر جایش است، کاری نکن.
        # این کار هم زمان راه‌اندازی را کم می‌کند و هم جلوی لاگ
        # اضافی در هر اجرای برنامه را می‌گیرد.
        try:
            cursor = self._connection.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
                "('recommendations', 'saved_filters', 'backups')"
            )
            have_tables = {row[0] for row in cursor.fetchall()}
            cursor.execute("PRAGMA table_info(attachments)")
            attach_cols = {row[1] for row in cursor.fetchall()}
            cursor.execute("PRAGMA table_info(observations)")
            obs_cols = {row[1] for row in cursor.fetchall()}

            missing = (
                {"recommendations", "saved_filters", "backups"} - have_tables
            ) | (
                {"updated_at"} - attach_cols
            ) | (
                {"indicator_id", "observable_behavior_id"} - obs_cols
            )
            if not missing:
                return
            print(f"🩺 ساختار دیتابیس ناقص است؛ ترمیم می‌شود: {sorted(missing)}")
        except Exception as e:
            # اگر همین بررسی هم شکست خورد، ترمیم را اجرا می‌کنیم
            print(f"⚠️ بررسی ساختار دیتابیس ممکن نشد: {e}")

        for module_name in self._IDEMPOTENT_MIGRATIONS:
            try:
                module = importlib.import_module(
                    f"database.migrations.{module_name}"
                )
            except Exception as e:
                print(f"⚠️ بارگذاری {module_name} برای ترمیم ساختار ممکن نشد: {e}")
                continue

            upgrade = getattr(module, "upgrade", None)
            if not callable(upgrade):
                continue

            try:
                upgrade(self._connection)
                self._connection.commit()
            except Exception as e:
                # برنامه به خاطر ترمیم ساختار نباید بالا نیاید؛
                # خطا ثبت می‌شود تا در لاگ قابل پیگیری باشد.
                print(f"⚠️ ترمیم ساختار ({module_name}) کامل نشد: {e}")
                try:
                    self._connection.rollback()
                except Exception:
                    pass

    
    def _get_db_version(self):
        """دریافت نسخه فعلی دیتابیس"""
        cursor = self._connection.cursor()
        
        # بررسی وجود جدول version
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='db_version'
        """)
        
        if cursor.fetchone() is None:
            return 0
        
        cursor.execute("SELECT version FROM db_version LIMIT 1")
        row = cursor.fetchone()
        return row['version'] if row else 0
    
    def _set_db_version(self, version):
        """تنظیم نسخه دیتابیس"""
        cursor = self._connection.cursor()
        
        # حذف جدول قبلی اگر وجود دارد
        cursor.execute("DROP TABLE IF EXISTS db_version")
        
        # ایجاد جدول جدید
        cursor.execute("""
            CREATE TABLE db_version (
                version INTEGER NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute(
            "INSERT INTO db_version (version) VALUES (?)",
            (version,)
        )
        self._connection.commit()
    
    def _migrate_database(self, from_version, to_version):
        """انجام Migration بین نسخه‌ها

        ===== اصلاح مهم =====
        نسخه قبلی فقط یک دیکشنری دستی داشت:

            migrations = {1: self._migrate_to_v1}

        بنابراین برای ارتقاء از نسخه ۲ به ۷ هیچ کاری انجام نمی‌شد جز
        اینکه در پایان `_set_db_version(7)` صدا زده می‌شد! یعنی دیتابیس
        قدیمی بدون دریافت هیچ‌کدام از تغییرات v2..v7، مُهر نسخه ۷
        می‌خورد و برای همیشه ناقص می‌ماند — در حالی که کلاس
        `MigrationManager` (database/migrations/manager.py) با تابع
        `_discover_migrations()` همه فایل‌های migration_vN.py را پیدا و
        اجرا می‌کند. آن کلاس درست کار می‌کرد ولی هیچ‌وقت از اینجا
        صدا زده نمی‌شد.

        حالا اول از MigrationManager واقعی استفاده می‌شود و اگر به هر
        دلیلی شکست خورد، مسیر قدیمی به عنوان fallback اجرا می‌شود تا
        برنامه بالا بیاید (به‌علاوه _heal_schema ساختار را ترمیم می‌کند).
        """
        print(f"🔄 ارتقاء دیتابیس از نسخه {from_version} به {to_version}")

        try:
            from database.migrations.manager import MigrationManager

            MigrationManager.migrate(self._connection, to_version)
            self._connection.commit()
            self._set_db_version(to_version)
            return
        except Exception as e:
            print(f"⚠️ ارتقاء با MigrationManager کامل نشد: {e}")
            try:
                self._connection.rollback()
            except Exception:
                pass

        # ===== مسیر جایگزین (fallback) =====
        migrations = {
            1: self._migrate_to_v1,
        }

        for version in range(from_version + 1, to_version + 1):
            if version in migrations:
                try:
                    migrations[version]()
                    self._set_db_version(version)
                    print(f"✅ ارتقاء به نسخه {version} انجام شد")
                except Exception as e:
                    print(f"⚠️ ارتقاء به نسخه {version} ناموفق بود: {e}")

        self._set_db_version(to_version)

    
    def _migrate_to_v1(self):
        """Migration به نسخه 1 - ایجاد جداول اولیه"""
        self._create_all_tables()
        self._create_indexes()
        self._create_audit_triggers()
        self._seed_default_data()
    
    def _create_all_tables(self):
        """ایجاد تمام جداول دیتابیس با مدل نهایی و فیلدهای Soft Delete"""
        cursor = self._connection.cursor()
        
        # ===== ۱. سال‌های تحصیلی =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS academic_years (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                start_date TEXT,
                end_date TEXT,
                is_active INTEGER DEFAULT 0,
                is_archived INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER
            )
        """)
        
        # ===== ۲. کادر مدرسه (Staff/Observer) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                is_active INTEGER DEFAULT 1,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER
            )
        """)
        
        # ===== ۳. دانش‌آموزان (اطلاعات دائمی) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                national_code TEXT UNIQUE,
                birth_date TEXT,
                father_name TEXT,
                guardian_name TEXT,
                guardian_phone TEXT,
                address TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER
            )
        """)
        
        # ===== ۴. پرونده سالانه دانش‌آموز (StudentAcademicProfile) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_academic_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                academic_year_id INTEGER NOT NULL,
                grade INTEGER,
                class_name TEXT,
                status TEXT DEFAULT 'active',
                status_history TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                UNIQUE(student_id, academic_year_id)
            )
        """)
        
        # ===== ۴.۱. اطلاعات زمینه‌ای خانواده (Family Context) =====
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
        
        # ===== ۴.۲. مصاحبه والدین (Parent Interview) =====
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

        # ===== ۵. شایستگی‌ها (Competencies) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                description TEXT,
                category TEXT,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER
            )
        """)
        
        # ===== ۵.۱. شاخص‌ها (Indicators) =====
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
        
        # ===== ۵.۲. رفتارهای قابل مشاهده (Observable Behaviors) =====
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

        # ===== ۶. مشاهدات (Observations) با مدل ABC =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_profile_id INTEGER NOT NULL,
                staff_id INTEGER NOT NULL,
                competency_id INTEGER,
                observation_date TEXT NOT NULL,
                location TEXT,
                description TEXT NOT NULL,
                antecedent TEXT,
                behavior TEXT,
                consequence TEXT,
                behavior_type TEXT,
                severity INTEGER DEFAULT 1,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (student_profile_id) REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
                FOREIGN KEY (competency_id) REFERENCES competencies(id) ON DELETE SET NULL
            )
        """)
        
                # ===== ۶.۱. غربالگری (Screening) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screenings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_profile_id INTEGER NOT NULL,
                staff_id INTEGER NOT NULL,
                tool_id INTEGER,
                tool_name TEXT NOT NULL,
                tool_version TEXT,
                execution_date TEXT NOT NULL,
                execution_context TEXT,
                domain_scores TEXT,
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
                FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
                FOREIGN KEY (tool_id) REFERENCES screening_tools(id) ON DELETE SET NULL
            )
        """)
        
        # ===== ۶.۱.۱. ابزارهای غربالگری (Screening Tools) =====
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
        
        # ===== ۶.۱.۲. نتایج غربالگری (Screening Results) =====
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
        
        # ===== ۶.۲. تفسیر تخصصی (Professional Interpretation) =====
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
        
        # ===== ۷. مداخلات (Interventions) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interventions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_profile_id INTEGER NOT NULL,
                staff_id INTEGER NOT NULL,
                observation_id INTEGER,
                type TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                goal TEXT,
                status TEXT DEFAULT 'planned',
                result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (student_profile_id) REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
                FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE SET NULL
            )
        """)
        
        # ===== ۸. پیگیری‌ها (FollowUps) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS followups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intervention_id INTEGER NOT NULL,
                staff_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                method TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending',
                next_action_date TEXT,
                result_type TEXT,
                result_description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (intervention_id) REFERENCES interventions(id) ON DELETE CASCADE,
                FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
            )
        """)
        
        # ===== ۹. پیوست‌ها (Attachments) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                file_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES staff(id) ON DELETE SET NULL
            )
        """)
        
        # ===== ۱۰. Audit Log (برای امنیت) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                ip_address TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES staff(id) ON DELETE SET NULL
            )
        """)
        
        # ===== ۱۱. کاربران (Users) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id INTEGER NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                must_change_password INTEGER DEFAULT 0,
                last_login TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
            )
        """)
        
        # ===== ۱۲. انتساب معلم به دانش‌آموز (TeacherAssignment) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teacher_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                staff_id INTEGER NOT NULL,
                academic_year_id INTEGER NOT NULL,
                grade INTEGER,
                class_name TEXT,
                is_active INTEGER DEFAULT 1,
                assigned_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                UNIQUE(student_id, staff_id, academic_year_id)
            )
        """)
        
        # ===== ۱۳. کلاس‌ها (Classes) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                grade INTEGER,
                teacher_id INTEGER,
                academic_year_id INTEGER NOT NULL,
                capacity INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (teacher_id) REFERENCES staff(id) ON DELETE SET NULL,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                UNIQUE(name, academic_year_id)
            )
        """)

        # ===== ۱۴. اعلان‌ها (Notifications) =====
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

        # ===== ۱۵. جلسات مشاوره (Counseling Sessions) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS counseling_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_profile_id INTEGER NOT NULL,
                counselor_id INTEGER NOT NULL,
                referred_by INTEGER,
                session_date TEXT NOT NULL,
                session_time TEXT,
                duration_minutes INTEGER,
                type TEXT NOT NULL,
                method TEXT,
                location TEXT,
                topic TEXT,
                goals TEXT,
                summary TEXT,
                details TEXT,
                interventions_discussed TEXT,
                recommendations TEXT,
                homework TEXT,
                outcome TEXT,
                follow_up_needed INTEGER DEFAULT 0,
                next_session_date TEXT,
                next_session_notes TEXT,
                status TEXT DEFAULT 'scheduled',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (student_profile_id) REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (counselor_id) REFERENCES staff(id) ON DELETE CASCADE,
                FOREIGN KEY (referred_by) REFERENCES staff(id) ON DELETE SET NULL
            )
        """)

        # ===== ۱۶. فعالیت‌های فوق‌برنامه (Extracurricular Activities) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracurricular_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_profile_id INTEGER NOT NULL,
                teacher_id INTEGER,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT,
                duration_hours INTEGER,
                location TEXT,
                participation_level TEXT,
                role TEXT,
                team_name TEXT,
                result TEXT,
                achievements TEXT,
                feedback TEXT,
                status TEXT DEFAULT 'planned',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (student_profile_id) REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id) REFERENCES staff(id) ON DELETE SET NULL
            )
        """)

        # ===== ۱۷. اهداف فردی (Individual Goals) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS individual_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_profile_id INTEGER NOT NULL,
                created_by INTEGER,
                assigned_to INTEGER,
                related_competency_id INTEGER,
                related_intervention_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                domain TEXT,
                priority TEXT DEFAULT 'medium',
                success_criteria TEXT,
                target_date TEXT,
                start_date TEXT,
                end_date TEXT,
                progress_percent INTEGER DEFAULT 0,
                progress_notes TEXT,
                status TEXT DEFAULT 'draft',
                result TEXT,
                achievement_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                deleted_by INTEGER,
                FOREIGN KEY (student_profile_id) REFERENCES student_academic_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES staff(id) ON DELETE SET NULL,
                FOREIGN KEY (assigned_to) REFERENCES staff(id) ON DELETE SET NULL,
                FOREIGN KEY (related_competency_id) REFERENCES competencies(id) ON DELETE SET NULL,
                FOREIGN KEY (related_intervention_id) REFERENCES interventions(id) ON DELETE SET NULL
            )
        """)
                
        self._connection.commit()
        print("✅ تمام جداول با موفقیت ایجاد شدند.")
    
    def _create_indexes(self):
        """ایجاد ایندکس‌ها برای افزایش سرعت جستجو"""
        cursor = self._connection.cursor()
        
        # ایندکس‌های جدول students
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_last_name ON students(last_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_first_name ON students(first_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_national_code ON students(national_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_is_deleted ON students(is_deleted)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_is_active ON students(is_active)")
        
        # ایندکس‌های جدول student_academic_profiles
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_student_id ON student_academic_profiles(student_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_academic_year_id ON student_academic_profiles(academic_year_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_grade ON student_academic_profiles(grade)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_status ON student_academic_profiles(status)")
        
        # ایندکس‌های جدول observations
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_student_profile_id ON observations(student_profile_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_observation_date ON observations(observation_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_staff_id ON observations(staff_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_behavior_type ON observations(behavior_type)")
        
        # ایندکس‌های جدول interventions
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inter_student_profile_id ON interventions(student_profile_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inter_date ON interventions(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inter_status ON interventions(status)")
        
        # ایندکس‌های جدول followups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_follow_intervention_id ON followups(intervention_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_follow_status ON followups(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_follow_next_action_date ON followups(next_action_date)")
        
        # ایندکس‌های جدول teacher_assignments
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ta_student_id ON teacher_assignments(student_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ta_staff_id ON teacher_assignments(staff_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ta_academic_year_id ON teacher_assignments(academic_year_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ta_is_active ON teacher_assignments(is_active)")

        # ایندکس‌های جدول counseling_sessions
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cs_student_profile_id ON counseling_sessions(student_profile_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cs_counselor_id ON counseling_sessions(counselor_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cs_session_date ON counseling_sessions(session_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cs_status ON counseling_sessions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cs_is_deleted ON counseling_sessions(is_deleted)")

        # ایندکس‌های جدول extracurricular_activities
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ea_student_profile_id ON extracurricular_activities(student_profile_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ea_type ON extracurricular_activities(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ea_status ON extracurricular_activities(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ea_start_date ON extracurricular_activities(start_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ea_is_deleted ON extracurricular_activities(is_deleted)")

        # ایندکس‌های جدول individual_goals
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ig_student_profile_id ON individual_goals(student_profile_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ig_status ON individual_goals(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ig_domain ON individual_goals(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ig_priority ON individual_goals(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ig_is_deleted ON individual_goals(is_deleted)")
                
        self._connection.commit()
        print("✅ ایندکس‌های دیتابیس با موفقیت ایجاد شدند.")
    
    def _create_audit_triggers(self):
        """ایجاد تریگرهای Audit Log برای ثبت تغییرات"""
        cursor = self._connection.cursor()
        
        tables = ['students', 'observations', 'interventions', 'followups', 
                  'student_academic_profiles', 'staff', 'competencies']
        
        for table in tables:
            try:
                # تریگر INSERT - با استفاده از تابع get_current_user_id()
                cursor.execute(f"""
                    CREATE TRIGGER IF NOT EXISTS trg_{table}_insert_audit
                    AFTER INSERT ON {table}
                    BEGIN
                        INSERT INTO audit_logs (
                            user_id, action, entity_type, entity_id, new_value
                        ) VALUES (
                            get_current_user_id(),
                            'create',
                            '{table}',
                            NEW.id,
                            json_object('id', NEW.id)
                        );
                    END
                """)
                
                # تریگر UPDATE
                cursor.execute(f"""
                    CREATE TRIGGER IF NOT EXISTS trg_{table}_update_audit
                    AFTER UPDATE ON {table}
                    WHEN NEW.is_deleted = 0 AND OLD.is_deleted = 0
                    BEGIN
                        INSERT INTO audit_logs (
                            user_id, action, entity_type, entity_id, 
                            old_value, new_value
                        ) VALUES (
                            get_current_user_id(),
                            'edit',
                            '{table}',
                            NEW.id,
                            json_object('id', OLD.id),
                            json_object('id', NEW.id)
                        );
                    END
                """)
                
                # تریگر برای Soft Delete
                cursor.execute(f"""
                    CREATE TRIGGER IF NOT EXISTS trg_{table}_soft_delete_audit
                    AFTER UPDATE ON {table}
                    WHEN NEW.is_deleted = 1 AND OLD.is_deleted = 0
                    BEGIN
                        INSERT INTO audit_logs (
                            user_id, action, entity_type, entity_id, 
                            old_value
                        ) VALUES (
                            get_current_user_id(),
                            'delete_soft',
                            '{table}',
                            NEW.id,
                            json_object('id', OLD.id)
                        );
                    END
                """)
                
                # تریگر برای Restore
                cursor.execute(f"""
                    CREATE TRIGGER IF NOT EXISTS trg_{table}_restore_audit
                    AFTER UPDATE ON {table}
                    WHEN NEW.is_deleted = 0 AND OLD.is_deleted = 1
                    BEGIN
                        INSERT INTO audit_logs (
                            user_id, action, entity_type, entity_id, 
                            new_value
                        ) VALUES (
                            get_current_user_id(),
                            'restore',
                            '{table}',
                            NEW.id,
                            json_object('id', NEW.id)
                        );
                    END
                """)
                
            except sqlite3.Error as e:
                print(f"⚠️ خطا در ایجاد تریگر برای {table}: {e}")
        
        self._connection.commit()
        print("✅ تریگرهای Audit Log ایجاد شدند.")
    
    def _seed_default_data(self):
        """پر کردن داده‌های پیش‌فرض"""
        cursor = self._connection.cursor()
        
        # ===== ۱. سال تحصیلی پیش‌فرض =====
        cursor.execute("SELECT COUNT(*) FROM academic_years WHERE is_deleted = 0")
        if cursor.fetchone()[0] == 0:
            try:
                now = jdatetime.datetime.now()
                current_year = now.year
            except:
                current_year = datetime.now().year - 621
            
            current_title = f"{current_year}-{current_year+1}"
            
            cursor.execute("""
                INSERT INTO academic_years (title, start_date, end_date, is_active, is_archived)
                VALUES (?, ?, ?, ?, ?)
            """, (current_title, f"{current_year}/07/01", f"{current_year+1}/06/30", 1, 0))
            
            print(f"✅ سال تحصیلی {current_title} به عنوان سال فعال ایجاد شد.")
        
        # ===== ۲. کاربر پیش‌فرض (سیستم) =====
        cursor.execute("SELECT COUNT(*) FROM staff WHERE is_deleted = 0")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO staff (full_name, role, is_active, description)
                VALUES (?, ?, ?, ?)
            """, ("سیستم", "system", 1, "کاربر پیش‌فرض سیستم"))
            print("✅ کاربر پیش‌فرض (سیستم) ایجاد شد.")
        
        # ===== ۳. کاربر ادمین پیش‌فرض =====
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_deleted = 0")
        if cursor.fetchone()[0] == 0:
            from utils.security import Security
            
            cursor.execute("SELECT id FROM staff WHERE role = 'system' LIMIT 1")
            row = cursor.fetchone()
            system_user_id = row['id'] if row else 1
            
            admin_password = Security.hash_password("Admin@123")
            cursor.execute("""
                INSERT INTO users (staff_id, username, password_hash, role, is_active, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (system_user_id, "admin", admin_password, "manager", 1, 1))  # must_change_password = 1
            
            print("✅ کاربر ادمین پیش‌فرض ایجاد شد. (نام کاربری: admin، رمز: Admin@123)")
            print("⚠️ کاربر در اولین ورود باید رمز عبور خود را تغییر دهد.")
        
        # ===== ۴. شایستگی‌های کامل =====
        cursor.execute("SELECT COUNT(*) FROM competencies WHERE is_deleted = 0")
        if cursor.fetchone()[0] == 0:
            try:
                import sys
                import os
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from data.competencies_data import COMPETENCIES_DATA
                
                for comp_data in COMPETENCIES_DATA:
                    cursor.execute("""
                        INSERT INTO competencies (title, description, category, is_active)
                        VALUES (?, ?, ?, ?)
                    """, (
                        comp_data["title"],
                        comp_data["description"],
                        comp_data["category"],
                        1
                    ))
                    print(f"  ✅ شایستگی '{comp_data['title']}' ایجاد شد.")
                
                print(f"✅ {len(COMPETENCIES_DATA)} شایستگی با شاخص‌های مشاهده‌پذیر ایجاد شد.")
                
            except ImportError as e:
                print(f"⚠️ خطا در بارگذاری داده‌های شایستگی‌ها: {e}")
                self._seed_basic_competencies()
        
        self._connection.commit()
    
    def _seed_basic_competencies(self):
        """داده‌های پایه شایستگی‌ها (در صورت عدم وجود فایل داده)"""
        cursor = self._connection.cursor()
        
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
    
    def set_current_user(self, user_id):
        """
        تنظیم کاربر جاری برای Audit Log

        نکته:
        این user_id باید در واقع staff.id باشد، نه users.id
        """
        if not user_id:
            self._current_user_id = None
            return

        # اگر هنوز connection ساخته نشده، فعلاً نگهش دار
        if self._connection is None:
            self._current_user_id = user_id
            return

        cursor = self._connection.cursor()
        cursor.execute(
            "SELECT id FROM staff WHERE id = ? AND is_deleted = 0",
            (user_id,)
        )
        row = cursor.fetchone()

        if row:
            self._current_user_id = user_id
        else:
            print(f"⚠️ user_id={user_id} در جدول staff وجود ندارد. Audit Log با NULL ثبت می‌شود.")
            self._current_user_id = None
    
    def verify_database_integrity(self):
        """بررسی سریع وضعیت دیتابیس"""
        conn = self.get_connection()
        cursor = conn.cursor()

        print("\n===== DB CHECK =====")

        cursor.execute("PRAGMA foreign_keys")
        fk_status = cursor.fetchone()[0]
        print(f"foreign_keys = {fk_status}")

        cursor.execute("SELECT version FROM db_version LIMIT 1")
        version = cursor.fetchone()
        print(f"db_version = {version['version'] if version else 'None'}")

        cursor.execute("""
            SELECT id, title, is_active, is_archived, is_deleted
            FROM academic_years
            ORDER BY id
        """)
        years = cursor.fetchall()
        print("academic_years:")
        for row in years:
            print(dict(row))

        cursor.execute("SELECT id, full_name, role FROM staff ORDER BY id")
        staff_rows = cursor.fetchall()
        print("staff:")
        for row in staff_rows:
            print(dict(row))

        cursor.execute("PRAGMA foreign_key_check")
        fk_errors = cursor.fetchall()
        print("foreign_key_check:", fk_errors if fk_errors else "OK")
        print("====================\n")
    
    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None
            self._initialized = False
    
    @staticmethod
    def _adapt_sqlite_value(value):
        """تبدیل مقدارهای رایج Python به نوع قابل ذخیره در SQLite."""
        if value is None or isinstance(value, (str, int, float, bytes, bytearray)):
            return value
        if isinstance(value, memoryview):
            return value.tobytes()
        if isinstance(value, dict):
            return {
                key: DatabaseConnection._adapt_sqlite_value(item)
                for key, item in value.items()
            }
        if isinstance(value, (tuple, list)):
            return tuple(DatabaseConnection._adapt_sqlite_value(item) for item in value)
        if hasattr(value, "value") and value.value is not value:
            return DatabaseConnection._adapt_sqlite_value(value.value)
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass
        # جلوگیری از خطای «parameters are of unsupported type» برای اشیایی
        # مثل Path یا مقادیر سفارشی؛ DALها معمولاً این مقادیر را متنی می‌خواهند.
        return str(value)

    @classmethod
    def _normalize_query_params(cls, params):
        """تبدیل scalar و iterable به پارامترهای معتبر sqlite3."""
        if params is None:
            return None
        if isinstance(params, dict):
            return cls._adapt_sqlite_value(params)
        if isinstance(params, tuple):
            values = params
        elif isinstance(params, list):
            values = tuple(params)
        elif isinstance(params, (str, bytes, bytearray, int, float)):
            values = (params,)
        else:
            try:
                values = tuple(params)
            except TypeError:
                values = (params,)
        return tuple(cls._adapt_sqlite_value(value) for value in values)

    def execute_query(self, query, params=None):
        """اجرای query با پشتیبانی از None، scalar و پارامترهای چندتایی."""
        conn = self.get_connection()
        cursor = conn.cursor()
        normalized_params = self._normalize_query_params(params)

        if normalized_params is None:
            cursor.execute(query)
        else:
            cursor.execute(query, normalized_params)

        return cursor
    
    # ============================================================
    # تراکنش واقعی
    # ============================================================
    def begin_transaction(self):
        """
        شروع یک تراکنش واقعی (با پشتیبانی از تودرتو)

        نکته کلیدی: تا وقتی عمق تراکنش بزرگ‌تر از صفر است، متد
        commit() پایین‌اثر می‌شود. این یعنی ۱۲۲ فراخوانی
        conn.commit() پراکنده در DALها لازم نیست تغییر کنند؛
        خودشان بی‌ضرر می‌شوند و فقط لایه سرویس commit می‌کند.

        ===== 🔴 اصلاح (بازرسی ششم) — تراکنش سرگردان =====
        ماژول sqlite3 پایتون در حالت پیش‌فرض، پیش از هر
        INSERT/UPDATE/DELETE خودش یک تراکنش «ضمنی» باز می‌کند و
        آن را تا commit/rollback باز نگه می‌دارد.

        اگر یک نوشتنِ سطح DAL وسط کار خطا بدهد و به commit نرسد
        (مثلاً خطای NOT NULL یا خطای binding)، آن تراکنش ضمنی باز
        می‌ماند؛ در حالی که شمارندهٔ _transaction_depth صفر است.
        اولین BEGIN بعدی برنامه با این خطا شکست می‌خورد:

            sqlite3.OperationalError: cannot start a transaction
            within a transaction

        نتیجهٔ عملی: بعد از یک خطای نوشتن، «همهٔ» عملیات تراکنشی
        برنامه تا پایان اجرا خراب می‌شد؛ مثلاً حذف دانش‌آموز،
        مشاهده یا مداخله با همان پیام مبهم شکست می‌خورد.

        تست عملی روی کد قبلی:
            RecommendationDAL.create(...)  → خطای binding
            ObservationService.delete_observation(...)
                → OperationalError: cannot start a transaction
                  within a transaction

        حالا قبل از BEGIN، اگر اتصال از قبل داخل تراکنشی باشد که
        شمارنده از آن بی‌خبر است، آن کارِ نیمه‌کاره rollback می‌شود
        (قرار نبوده ذخیره شود، وگرنه commit شده بود) و هشدار در
        لاگ می‌آید تا ریشهٔ خطا گم نشود.
        """
        if DatabaseConnection._transaction_depth == 0:
            conn = self.get_connection()
            # اگر تراکنشِ ضمنیِ جاافتاده‌ای باز است، اول ببندش
            if getattr(conn, "in_transaction", False):
                self._recover_dangling_transaction()
            # یک دستور نوشتنی بفرست تا sqlite واقعاً تراکنش را باز کند
            conn.execute("BEGIN")
        DatabaseConnection._transaction_depth += 1

    def _recover_dangling_transaction(self):
        """
        بستن تراکنشی که بدون شمارش باز مانده است

        این حالت وقتی رخ می‌دهد که یک نوشتنِ DAL پیش از رسیدن به
        commit خطا داده و لایهٔ سرویس هم آن را داخل تراکنش خودش
        نگرفته باشد. کار نیمه‌تمام آن‌جا نباید ذخیره شود، پس
        rollback می‌کنیم و در لاگ هشدار می‌دهیم.
        """
        try:
            if self._connection:
                self._connection.rollback()
        except Exception:  # pragma: no cover - مسیر اضطراری
            pass
        try:
            print(
                "⚠️ تراکنشِ بازِ جاافتاده بسته شد (rollback). "
                "یعنی یک نوشتن قبلی نیمه‌کاره مانده بود."
            )
        except Exception:  # pragma: no cover
            pass


    def discard_pending_writes(self):
        """
        پاک‌کردن نوشتن‌های نیمه‌کاره (بازرسی ششم)

        وقتی یک نوشتن شکست می‌خورد (مثلاً خطای binding یا نقض
        محدودیت) و لایهٔ سرویس آن خطا را مدیریت می‌کند، نباید کار
        نیمه‌تمام روی اتصال باقی بماند. این متد هم تراکنشِ
        شمارش‌شده و هم تراکنشِ ضمنیِ جاافتاده را می‌بندد؛ برای
        استفاده در exceptِ سرویس‌ها:

            except Exception:
                self.db.discard_pending_writes()
                raise
        """
        if DatabaseConnection._transaction_depth > 0:
            self.rollback_transaction()
            return
        conn = self._connection
        if conn is not None and getattr(conn, "in_transaction", False):
            self._recover_dangling_transaction()

    def commit_transaction(self):
        """تأیید یک لایه از تراکنش؛ فقط لایه بیرونی واقعاً commit می‌کند"""
        if DatabaseConnection._transaction_depth <= 0:
            return
        DatabaseConnection._transaction_depth -= 1
        if DatabaseConnection._transaction_depth == 0 and self._connection:
            self._connection.commit()

    def rollback_transaction(self):
        """
        بازگشت کل تراکنش (همه لایه‌ها)

        برخلاف commit، بازگشت همیشه تا عمق صفر می‌رود: اگر لایه
        درونی خطا داد، لایه بیرونی هم باید کل کار را لغو کند،
        وگرنه داده نیمه‌نوشته می‌ماند.
        """
        if DatabaseConnection._transaction_depth <= 0:
            return
        DatabaseConnection._transaction_depth = 0
        if self._connection:
            self._connection.rollback()

    @property
    def in_transaction(self):
        """آیا الان داخل یک تراکنش هستیم؟"""
        return DatabaseConnection._transaction_depth > 0

    def commit(self):
        # ===== اصلاح مهم =====
        # نسخه قبلی همیشه commit می‌زد. حالا اگر داخل تراکنش باشیم
        # بی‌اثر است تا rollback واقعاً کار کند.
        if DatabaseConnection._transaction_depth > 0:
            return
        if self._connection:
            self._connection.commit()

    def rollback(self):
        if DatabaseConnection._transaction_depth > 0:
            # داخل تراکنش: کل تراکنش را برگردان
            self.rollback_transaction()
            return
        if self._connection:
            self._connection.rollback()
    
    def enable_audit(self):
        """فعال کردن Audit Log"""
        self._audit_enabled = True
    
    def disable_audit(self):
        """غیرفعال کردن Audit Log (برای عملیات سیستمی)"""
        self._audit_enabled = False
    
    def get_db_version(self):
        """دریافت نسخه فعلی دیتابیس (عمومی)"""
        return self._get_db_version()
    
    def get_current_user(self):
        """دریافت کاربر جاری"""
        return self._current_user_id