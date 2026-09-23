"""
Migration نسخه ۸ — ایندکس‌گذاری ستون‌های کلید خارجی

===== چرا این migration لازم است؟ =====
در بازرسی هشتم، همهٔ ستون‌های FOREIGN KEY با فهرست ایندکس‌های موجود
مقایسه شدند: **۳۳ ستون** کلید خارجی هیچ ایندکسی نداشتند، از جمله:

    observations.competency_id            interventions.staff_id
    interventions.observation_id          followups.intervention_id
    followups.staff_id                    screening_results.student_profile_id
    professional_interpretations.*        family_contexts.student_profile_id
    parent_interviews.student_profile_id  teacher_assignments.staff_id

SQLite برای هر JOIN و هر فیلتر روی این ستون‌ها مجبور به پیمایش کل جدول
(SCAN) است. برای یک مدرسهٔ متوسط با چند هزار مشاهده، این یعنی گزارش‌ها
و داشبورد به‌مرور کند می‌شوند. ایندکس‌گذاری این ستون‌ها هیچ تغییری در
منطق برنامه ایجاد نمی‌کند و فقط سرعت کوئری‌ها را بالا می‌برد.

===== نکته درباره idempotent بودن =====
همهٔ دستورها `CREATE INDEX IF NOT EXISTS` هستند، پس اجرای چندبارهٔ این
فایل بی‌خطر است (این ماژول در فهرست migration‌های ترمیمی هم ثبت شده تا
روی دیتابیس‌های قدیمی، بدون تغییر شماره نسخه هم اجرا شود).
"""

# ایندکس‌هایی که ساخته می‌شوند: (نام ایندکس، جدول، ستون)
FK_INDEXES = [
    # --- پرونده و هویت دانش‌آموز ---
    ("idx_observations_competency_id", "observations", "competency_id"),
    ("idx_observations_behavior_id", "observations", "observable_behavior_id"),
    ("idx_observations_indicator_id", "observations", "indicator_id"),
    ("idx_observations_staff_id", "observations", "staff_id"),

    # --- مداخلات ---
    ("idx_interventions_staff_id", "interventions", "staff_id"),
    ("idx_interventions_observation_id", "interventions", "observation_id"),

    # --- پیگیری‌ها ---
    ("idx_followups_intervention_id", "followups", "intervention_id"),
    ("idx_followups_staff_id", "followups", "staff_id"),

    # --- غربالگری و تفسیر حرفه‌ای ---
    ("idx_screenings_student_profile_id", "screenings", "student_profile_id"),
    ("idx_screenings_staff_id", "screenings", "staff_id"),
    ("idx_screenings_tool_id", "screenings", "tool_id"),
    ("idx_screening_results_student_profile_id", "screening_results", "student_profile_id"),
    ("idx_screening_results_staff_id", "screening_results", "staff_id"),
    ("idx_screening_results_tool_id", "screening_results", "tool_id"),
    ("idx_prof_interp_student_profile_id", "professional_interpretations", "student_profile_id"),
    ("idx_prof_interp_staff_id", "professional_interpretations", "staff_id"),
    ("idx_prof_interp_observation_id", "professional_interpretations", "observation_id"),
    ("idx_prof_interp_screening_id", "professional_interpretations", "screening_id"),

    # --- خانواده و مصاحبهٔ والدین ---
    ("idx_family_contexts_student_profile_id", "family_contexts", "student_profile_id"),
    ("idx_family_contexts_recorded_by", "family_contexts", "recorded_by"),
    ("idx_parent_interviews_student_profile_id", "parent_interviews", "student_profile_id"),
    ("idx_parent_interviews_staff_id", "parent_interviews", "staff_id"),

    # --- ساختار آموزشی ---
    ("idx_indicators_competency_id", "indicators", "competency_id"),
    ("idx_observable_behaviors_indicator_id", "observable_behaviors", "indicator_id"),
    ("idx_observable_behaviors_competency_id", "observable_behaviors", "competency_id"),
    ("idx_profiles_class_id", "student_academic_profiles", "class_id"),
    ("idx_teacher_assignments_staff_id", "teacher_assignments", "staff_id"),
    ("idx_teacher_assignments_class_id", "teacher_assignments", "class_id"),

    # --- جلسات مشاوره، فعالیت‌ها و اهداف ---
    ("idx_counseling_sessions_counselor_id", "counseling_sessions", "counselor_id"),
    ("idx_counseling_sessions_referred_by", "counseling_sessions", "referred_by"),
    ("idx_activities_teacher_id", "extracurricular_activities", "teacher_id"),
    ("idx_goals_competency_id", "individual_goals", "competency_id"),

    # --- کلیدهای خارجی توصیه‌شده در گزارش بازرسی ---
    ("idx_recommendations_competency_id", "recommendations", "related_competency_id"),
    ("idx_recommendations_staff_id", "recommendations", "staff_id"),
    ("idx_audit_logs_entity", "audit_logs", "entity_type", "entity_id"),
    ("idx_saved_filters_created_by", "saved_filters", "created_by"),

    # --- بقیهٔ کلیدهای خارجی (تکمیل در همان دور بازرسی) ---
    ("idx_attachments_created_by", "attachments", "created_by"),
    ("idx_audit_logs_user_id", "audit_logs", "user_id"),
    ("idx_users_staff_id", "users", "staff_id"),
    ("idx_classes_teacher_id", "classes", "teacher_id"),
    ("idx_classes_academic_year_id", "classes", "academic_year_id"),
    ("idx_notifications_user_id", "notifications", "user_id"),
    ("idx_individual_goals_created_by", "individual_goals", "created_by"),
    ("idx_individual_goals_assigned_to", "individual_goals", "assigned_to"),
    ("idx_individual_goals_related_competency_id", "individual_goals", "related_competency_id"),
    ("idx_individual_goals_related_intervention_id", "individual_goals", "related_intervention_id"),
    ("idx_backups_created_by", "backups", "created_by"),
]


def _table_exists(cursor, table_name):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _column_exists(cursor, table_name, column_name):
    if not _table_exists(cursor, table_name):
        return False
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def upgrade(connection):
    """
    ساخت ایندکس‌های کلید خارجی

    برای هر مورد: وجود جدول و ستون بررسی می‌شود تا روی دیتابیس‌هایی
    که ساختار قدیمی/ناقص دارند هم بی‌خطر باشد.
    """
    cursor = connection.cursor()
    created = 0
    skipped = 0

    print("🔄 Migration نسخه ۸: ایندکس‌گذاری ستون‌های کلید خارجی")

    for entry in FK_INDEXES:
        index_name, table, *columns = entry

        if not all(_column_exists(cursor, table, col) for col in columns):
            skipped += 1
            continue

        cols = ", ".join(columns)
        try:
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({cols})"
            )
            created += 1
        except Exception as e:
            # ایندکس‌گذاری هرگز نباید جلوی بالا آمدن برنامه را بگیرد
            print(f"  ⚠️ ایندکس {index_name} ساخته نشد: {e}")
            skipped += 1

    # (بازرسی شانزدهم — BUG-NEW-02) commit این‌جا حذف شد: تراکنش را فقط
    # MigrationManager._run_step (یا _heal_schema) باز و commit/rollback می‌کند.
    print(f"  ✅ {created} ایندکس ساخته/بررسی شد"
          f"{f'، {skipped} مورد رد شد' if skipped else ''}.")


def downgrade(connection):
    """حذف ایندکس‌های ساخته‌شده"""
    print("🔄 بازگشت از نسخه ۸...")
    cursor = connection.cursor()
    for entry in FK_INDEXES:
        index_name = entry[0]
        cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
    # (بازرسی شانزدهم — BUG-NEW-02) commit این‌جا حذف شد: تراکنش را فقط
    # MigrationManager._run_step (یا _heal_schema) باز و commit/rollback می‌کند.
    print("✅ بازگشت از نسخه ۸ انجام شد.")
