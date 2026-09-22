# Inventory رابط کاربری — دور شانزدهم (تولید خودکار با tools/ui_inventory.py)

طبقه‌بندی ایستا: BACKEND = به سرویس/DAL/فایل می‌رسد؛ DIALOG = دیالوگ باز می‌کند (زنجیره در دیالوگ)؛ SIGNAL = سیگنال به والد؛ NAV = ناوبری؛ UI_ONLY = فقط تغییر ویجت؛ MSG_ONLY = فقط پیام؛ STUB = pass؛ NO_CONNECT = بدون اتصال؛ MISSING = handler در کلاس نیست.

## جمع‌بندی

| طبقه | تعداد |
|---|---|
| BACKEND | 115 |
| UI_ONLY | 19 |
| MSG_ONLY | 10 |
| DIALOG | 9 |
| NAV | 7 |
| SIGNAL | 6 |

## موارد نیازمند بازبینی دستی (NO_CONNECT / STUB / MSG_ONLY / MISSING)

| فایل | کلاس | دکمه | متن | خط | طبقه |
|---|---|---|---|---|---|
| `views/main_window.py` | MainWindow | `self.btn_logout` | 🚪 خروج | 330 | MSG_ONLY |
| `views/pages/activities_page.py` | ActivitiesPage | `view_btn` | 👁️ | 235 | MSG_ONLY |
| `views/pages/followups_page.py` | FollowUpsPage | `view_btn` | 👁️ | 300 | MSG_ONLY |
| `views/pages/interventions_page.py` | InterventionsPage | `view_btn` | 👁️ | 346 | MSG_ONLY |
| `views/pages/observations_page.py` | ObservationsPage | `view_btn` | 👁️ | 517 | MSG_ONLY |
| `views/pages/student_profile_page.py` | StudentProfilePage | `view_btn` | 👁️ | 1162 | MSG_ONLY |
| `views/pages/student_profile_page.py` | StudentProfilePage | `view_btn` | 👁️ | 1192 | MSG_ONLY |
| `views/pages/student_profile_page.py` | StudentProfilePage | `view_btn` | 👁️ | 1222 | MSG_ONLY |
| `views/dialogs/export_ai_dialog.py` | ExportAIDialog | `self.copy_prompt_btn` | 📋 کپی پرامپت | 293 | MSG_ONLY |
| `views/dialogs/observation_form.py` | ObservationForm | `self.guide_btn` | ❓ راهنما | 125 | MSG_ONLY |

## سیگنال‌های سفارشی (تعریف → emit → گیرنده)

| فایل | کلاس | سیگنال | خط | تعداد emit | گیرنده‌ها |
|---|---|---|---|---|---|
| `views/dialogs/activity_form.py` | ActivityForm | `activity_saved` | 40 | 1 | `views/pages/activities_page.py` |
| `views/dialogs/advanced_search_dialog.py` | AdvancedSearchDialog | `student_selected` | 30 | 1 | `views/main_window.py`, `views/pages/students_page.py` |
| `views/dialogs/assign_teacher_dialog.py` | AssignTeacherDialog | `assignment_saved` | 37 | 1 | **هیچ** |
| `views/dialogs/attachment_dialog.py` | AttachmentDialog | `attachment_added` | 104 | 1 | **هیچ** |
| `views/dialogs/attachment_dialog.py` | AttachmentDialog | `attachment_deleted` | 105 | 1 | **هیچ** |
| `views/dialogs/attachment_dialog.py` | AttachmentUploadWorker | `progress` | 53 | 3 | `views/pages/backup_page.py`, `views/dialogs/attachment_dialog.py` |
| `views/dialogs/attachment_dialog.py` | AttachmentUploadWorker | `upload_finished` | 54 | 2 | `views/dialogs/attachment_dialog.py` |
| `views/dialogs/change_password_dialog.py` | ChangePasswordDialog | `password_changed` | 33 | 1 | **هیچ** |
| `views/dialogs/counseling_session_form.py` | CounselingSessionForm | `session_saved` | 40 | 1 | `views/pages/counseling_page.py` |
| `views/dialogs/followup_form.py` | FollowUpForm | `followup_saved` | 34 | 1 | `views/pages/followups_page.py` |
| `views/dialogs/goal_form.py` | GoalForm | `goal_saved` | 41 | 1 | `views/pages/goals_page.py` |
| `views/dialogs/intervention_form.py` | InterventionForm | `intervention_saved` | 34 | 1 | `views/pages/interventions_page.py` |
| `views/dialogs/login_dialog.py` | LoginDialog | `login_successful` | 36 | 1 | `views/main_window.py` |
| `views/dialogs/login_dialog.py` | LoginDialog | `need_change_password` | 37 | 1 | `views/main_window.py` |
| `views/dialogs/observation_form.py` | ObservationForm | `observation_saved` | 46 | 1 | `views/pages/observations_page.py` |
| `views/main_window.py` | MainWindow | `academic_year_changed` | 58 | 1 | **هیچ** |
| `views/pages/academic_structure_page.py` | AcademicStructurePage | `student_selected` | 59 | 1 | `views/main_window.py`, `views/pages/students_page.py` |
| `views/pages/activities_page.py` | ActivitiesPage | `student_selected` | 38 | 1 | `views/main_window.py`, `views/pages/students_page.py` |
| `views/pages/analytics_dashboard.py` | AnalyticsDashboardPage | `student_selected` | 55 | 1 | `views/main_window.py`, `views/pages/students_page.py` |
| `views/pages/backup_page.py` | BackupWorker | `operation_finished` | 47 | 5 | `views/pages/backup_page.py` |
| `views/pages/backup_page.py` | BackupWorker | `progress` | 46 | 2 | `views/pages/backup_page.py`, `views/dialogs/attachment_dialog.py` |
| `views/pages/counseling_page.py` | CounselingPage | `student_selected` | 39 | 1 | `views/main_window.py`, `views/pages/students_page.py` |
| `views/pages/goals_page.py` | GoalsPage | `student_selected` | 41 | 1 | `views/main_window.py`, `views/pages/students_page.py` |
| `views/pages/student_profile_page.py` | StudentProfilePage | `report_requested` | 58 | 1 | `views/main_window.py` |
| `views/pages/students_page.py` | StudentsPage | `student_double_clicked` | 43 | 2 | `views/main_window.py` |
| `views/widgets/competency_tree_widget.py` | CompetencyTreeWidget | `behavior_selected` | 43 | 2 | **هیچ** |
| `views/widgets/competency_tree_widget.py` | CompetencyTreeWidget | `competency_selected` | 41 | 2 | **هیچ** |
| `views/widgets/competency_tree_widget.py` | CompetencyTreeWidget | `full_path_selected` | 44 | 3 | `views/dialogs/observation_form.py` |
| `views/widgets/competency_tree_widget.py` | CompetencyTreeWidget | `indicator_selected` | 42 | 2 | **هیچ** |
| `views/widgets/help_widget.py` | HelpWidget | `help_requested` | 30 | 1 | **هیچ** |
| `views/widgets/notification_widget.py` | NotificationItem | `clicked` | 31 | 1 | `views/main_window.py`, `views/pages/academic_structure_page.py`, `views/pages/activities_page.py`, `views/pages/analysis_page.py`, `views/pages/analytics_dashboard.py`, `views/pages/backup_page.py`, `views/pages/class_report_page.py`, `views/pages/counseling_page.py`, `views/pages/dashboard_page.py`, `views/pages/followups_page.py`, `views/pages/goals_page.py`, `views/pages/indicators_page.py`, `views/pages/interventions_page.py`, `views/pages/observations_page.py`, `views/pages/promotion_page.py`, `views/pages/reports_page.py`, `views/pages/settings_page.py`, `views/pages/student_profile_page.py`, `views/pages/students_page.py`, `views/pages/teacher_performance_page.py`, `views/pages/teacher_report_page.py`, `views/dialogs/activity_form.py`, `views/dialogs/advanced_search_dialog.py`, `views/dialogs/assign_teacher_dialog.py`, `views/dialogs/attachment_dialog.py`, `views/dialogs/change_password_dialog.py`, `views/dialogs/counseling_session_form.py`, `views/dialogs/export_ai_dialog.py`, `views/dialogs/followup_form.py`, `views/dialogs/goal_form.py`, `views/dialogs/intervention_form.py`, `views/dialogs/login_dialog.py`, `views/dialogs/observation_form.py`, `views/dialogs/student_form.py`, `views/widgets/competency_tree_widget.py`, `views/widgets/help_widget.py`, `views/widgets/notification_widget.py`, `views/widgets/recommendation_widget.py` |
| `views/widgets/notification_widget.py` | NotificationWidget | `notification_clicked` | 128 | 1 | `views/main_window.py` |
| `views/widgets/recommendation_widget.py` | RecommendationWidget | `intervention_requested` | 41 | 1 | `views/pages/student_profile_page.py` |
| `views/widgets/recommendation_widget.py` | RecommendationWidget | `recommendation_updated` | 40 | 4 | **هیچ** |

## connect داخل متدهای بارگذاری/تازه‌سازی (خطر اتصال چندباره)

| فایل | کلاس | متد | فرستنده | رویداد | خط |
|---|---|---|---|---|---|
| `views/main_window.py` | MainWindow | `show_login_dialog` | `login_dialog` | login_successful | 91 |
| `views/main_window.py` | MainWindow | `show_login_dialog` | `login_dialog` | need_change_password | 92 |
| `views/widgets/notification_widget.py` | NotificationWidget | `load_notifications` | `widget` | clicked | 365 |

## جدول کامل دکمه‌ها


### `views/main_window.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| MainWindow | `self.btn_logout` | 🚪 خروج | 330 | `lambda:self.logout()` | MSG_ONLY |
| MainWindow | `self.notification_btn` | 🔔 | 402 | `self.toggle_notifications` | UI_ONLY |
| MainWindow | `btn` |  | 296 | `lambda:self.stacked_widget.setCurrentInd` | NAV |

### `views/pages/academic_structure_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| AcademicStructurePage | `self.refresh_btn` | 🔄 به‌روزرسانی | 134 | `self.refresh_all` | BACKEND |
| AcademicStructurePage | `self.add_class_btn` | ➕ افزودن کلاس | 338 | `self.add_class` | BACKEND |
| AcademicStructurePage | `self.cancel_edit_class_btn` | ✖ انصراف از ویرایش | 357 | `self.cancel_edit_class` | BACKEND |
| AcademicStructurePage | `self.assign_new_btn` | ➕ اختصاص معلم جدید | 456 | `self.open_assign_dialog` | BACKEND |
| AcademicStructurePage | `view_profile_btn` | 👤 مشاهده پرونده کامل | 667 | `self.view_full_profile` | BACKEND |
| AcademicStructurePage | `edit_btn` | ✏️ | 826 | `lambda:self.edit_class()` | BACKEND |
| AcademicStructurePage | `delete_btn` | 🗑️ | 832 | `lambda:self.delete_class()` | BACKEND |
| AcademicStructurePage | `edit_btn` | ✏️ | 984 | `lambda:self.edit_assignment()` | BACKEND |
| AcademicStructurePage | `delete_btn` | 🗑️ | 990 | `lambda:self.delete_assignment()` | BACKEND |

### `views/pages/activities_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| ActivitiesPage | `self.add_btn` | ➕ ثبت فعالیت جدید | 91 | `self.add_activity` | BACKEND |
| ActivitiesPage | `self.view_profile_btn` | 👤 مشاهده پرونده دانش‌آموز | 109 | `self.view_student_profile` | SIGNAL |
| ActivitiesPage | `view_btn` | 👁️ | 235 | `lambda:self.view_activity()` | MSG_ONLY |
| ActivitiesPage | `edit_btn` | ✏️ | 241 | `lambda:self.edit_activity()` | DIALOG |
| ActivitiesPage | `delete_btn` | 🗑️ | 247 | `lambda:self.delete_activity()` | BACKEND |

### `views/pages/analysis_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| AnalysisPage | `self.search_btn` | 🔍 جستجو | 121 | `self.search_student` | BACKEND |
| AnalysisPage | `self.clear_search_btn` | ✖ | 136 | `self.clear_search` | NAV |
| AnalysisPage | `self.analyze_btn` | 📊 تحلیل | 193 | `self.load_analysis` | BACKEND |

### `views/pages/analytics_dashboard.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| AnalyticsDashboardPage | `self.refresh_btn` | 🔄 به‌روزرسانی | 219 | `self.load_dashboard_data` | BACKEND |

### `views/pages/backup_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| BackupPage | `self.create_btn` | ➕ ایجاد پشتیبان جدید | 136 | `self.create_backup` | BACKEND |
| BackupPage | `self.restore_btn` | 📂 بازیابی از فایل | 151 | `self.restore_from_file` | BACKEND |
| BackupPage | `self.refresh_btn` | 🔄 | 166 | `self.load_backups` | BACKEND |
| BackupPage | `restore_btn` | 🔄 بازیابی | 270 | `lambda:self.restore_backup()` | BACKEND |
| BackupPage | `delete_btn` | 🗑️ | 278 | `lambda:self.delete_backup()` | BACKEND |

### `views/pages/class_report_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| ClassReportPage | `self.generate_btn` | 📊 تولید گزارش | 127 | `self.generate_report` | BACKEND |
| ClassReportPage | `self.pdf_btn` | 📄 PDF | 145 | `self.export_pdf` | BACKEND |
| ClassReportPage | `self.excel_btn` | 📊 Excel | 160 | `self.export_excel` | BACKEND |

### `views/pages/counseling_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| CounselingPage | `self.add_btn` | ➕ ثبت جلسه جدید | 92 | `self.add_session` | BACKEND |
| CounselingPage | `view_profile_btn` | 👤 مشاهده پرونده دانش‌آموز | 204 | `self.view_student_profile` | SIGNAL |
| CounselingPage | `view_btn` | 👁️ | 301 | `lambda:self.view_session()` | BACKEND |
| CounselingPage | `edit_btn` | ✏️ | 307 | `lambda:self.edit_session()` | DIALOG |
| CounselingPage | `delete_btn` | 🗑️ | 313 | `lambda:self.delete_session()` | BACKEND |

### `views/pages/dashboard_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| DashboardPage | `self.refresh_btn` | 🔄 به‌روزرسانی | 239 | `self.load_dashboard_data` | BACKEND |

### `views/pages/followups_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| FollowUpsPage | `self.search_btn` | 🔍 جستجو | 97 | `self.apply_search` | BACKEND |
| FollowUpsPage | `self.clear_search_btn` | ✖ | 124 | `self.clear_search` | BACKEND |
| FollowUpsPage | `self.add_btn` | ➕ ثبت پیگیری جدید | 139 | `self.add_followup` | BACKEND |
| FollowUpsPage | `view_btn` | 👁️ | 300 | `lambda:self.view_followup()` | MSG_ONLY |
| FollowUpsPage | `delete_btn` | 🗑️ | 306 | `lambda:self.delete_followup()` | BACKEND |

### `views/pages/goals_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| GoalsPage | `self.add_btn` | ➕ ثبت هدف جدید | 93 | `self.add_goal` | BACKEND |
| GoalsPage | `view_profile_btn` | 👤 مشاهده پرونده دانش‌آموز | 205 | `self.view_student_profile` | SIGNAL |
| GoalsPage | `view_btn` | 👁️ | 313 | `lambda:self.view_goal()` | BACKEND |
| GoalsPage | `edit_btn` | ✏️ | 319 | `lambda:self.edit_goal()` | DIALOG |
| GoalsPage | `delete_btn` | 🗑️ | 325 | `lambda:self.delete_goal()` | BACKEND |

### `views/pages/indicators_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| IndicatorsPage | `self.search_btn` | 🔍 جستجو | 129 | `self.search_student` | BACKEND |
| IndicatorsPage | `self.clear_search_btn` | ✖ | 144 | `self.clear_search` | NAV |
| IndicatorsPage | `refresh_btn` | 🔄 به‌روزرسانی شاخص‌ها | 232 | `self.refresh_indicators` | BACKEND |

### `views/pages/interventions_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| InterventionsPage | `self.search_btn` | 🔍 جستجو | 108 | `self.apply_search` | BACKEND |
| InterventionsPage | `self.clear_search_btn` | ✖ | 135 | `self.clear_search` | BACKEND |
| InterventionsPage | `self.add_btn` | ➕ ثبت مداخله جدید | 150 | `self.add_intervention` | BACKEND |
| InterventionsPage | `view_btn` | 👁️ | 346 | `lambda:self.view_intervention()` | MSG_ONLY |
| InterventionsPage | `delete_btn` | 🗑️ | 352 | `lambda:self.delete_intervention()` | BACKEND |

### `views/pages/observations_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| ObservationsPage | `self.search_btn` | 🔍 جستجو | 114 | `self.apply_advanced_search` | BACKEND |
| ObservationsPage | `self.advanced_search_btn` | ⚙️ پیشرفته | 130 | `self.toggle_advanced_search` | UI_ONLY |
| ObservationsPage | `self.clear_search_btn` | ✖ | 145 | `self.clear_search` | BACKEND |
| ObservationsPage | `self.add_btn` | ➕ ثبت مشاهده جدید | 160 | `self.add_observation` | BACKEND |
| ObservationsPage | `self.apply_filter_btn` | ✅ اعمال فیلتر | 236 | `self.apply_advanced_search` | BACKEND |
| ObservationsPage | `self.clear_filters_btn` | 🗑️ پاک کردن فیلترها | 251 | `self.clear_filters` | BACKEND |
| ObservationsPage | `view_btn` | 👁️ | 517 | `lambda:self.view_observation()` | MSG_ONLY |
| ObservationsPage | `delete_btn` | 🗑️ | 523 | `lambda:self.delete_observation()` | BACKEND |

### `views/pages/promotion_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| PromotionPage | `self.search_btn` | 🔍 جستجو | 143 | `self.search_students` | BACKEND |
| PromotionPage | `self.clear_search_btn` | ✖ نمایش همه | 158 | `self.clear_search` | BACKEND |
| PromotionPage | `self.promote_all_btn` | 📈 ارتقاء همه | 204 | `self.promote_all_students` | BACKEND |
| PromotionPage | `self.promote_selected_btn` | 📌 ارتقاء انتخاب‌شده | 219 | `self.promote_selected_students` | BACKEND |
| PromotionPage | `self.repeat_grade_btn` | 🔄 تکرار پایه | 234 | `self.repeat_grade_students` | BACKEND |

### `views/pages/reports_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| ReportsPage | `self.search_btn` | 🔍 جستجو | 139 | `self.search_student` | BACKEND |
| ReportsPage | `self.clear_search_btn` | ✖ | 154 | `self.clear_search` | NAV |
| ReportsPage | `self.parent_btn` | 👨‍👩‍👦 گزارش والدین | 178 | `self.show_parent_report` | BACKEND |
| ReportsPage | `self.excel_btn` | 📊 خروجی Excel | 193 | `self.export_excel` | BACKEND |
| ReportsPage | `self.pdf_btn` | 📄 خروجی PDF | 210 | `self.export_pdf` | BACKEND |
| ReportsPage | `self.ai_export_btn` | 🤖 خروجی برای هوش مصنوعی | 226 | `self.export_for_ai` | DIALOG |

### `views/pages/settings_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| SettingsPage | `self.add_year_btn` | ➕ افزودن | 206 | `self.add_academic_year` | BACKEND |
| SettingsPage | `delete_btn` | 🗑️ | 302 | `lambda:self.delete_year()` | BACKEND |
| SettingsPage | `activate_btn` | ✅ فعال کن | 289 | `lambda:self.activate_year()` | BACKEND |
| SettingsPage | `archive_btn` | 📦 بایگانی | 296 | `lambda:self.archive_year()` | BACKEND |
| SettingsPage | `self.add_staff_btn` | ➕ افزودن | 423 | `self.add_staff` | BACKEND |
| SettingsPage | `delete_btn` | 🗑️ | 519 | `lambda:self.delete_staff()` | BACKEND |
| SettingsPage | `deactivate_btn` | 🔴 غیرفعال کن | 507 | `lambda:self.toggle_staff_status()` | BACKEND |
| SettingsPage | `activate_btn` | 🟢 فعال کن | 513 | `lambda:self.toggle_staff_status()` | BACKEND |
| SettingsPage | `self.add_user_btn` | ➕ افزودن کاربر | 671 | `self.add_user` | BACKEND |
| SettingsPage | `reset_btn` | 🔑 ریست رمز | 819 | `lambda:self.reset_user_password()` | BACKEND |
| SettingsPage | `delete_btn` | 🗑️ | 825 | `lambda:self.delete_user()` | BACKEND |
| SettingsPage | `deactivate_btn` | 🔴 غیرفعال کن | 807 | `lambda:self.toggle_user_status()` | BACKEND |
| SettingsPage | `activate_btn` | 🟢 فعال کن | 813 | `lambda:self.toggle_user_status()` | BACKEND |
| SettingsPage | `save_btn` | 💾 ذخیره اطلاعات | 1108 | `self.save_school_info` | BACKEND |
| SettingsPage | `self.start_auto_backup_btn` | ▶️ شروع پشتیبان‌گیری خودکار | 1339 | `self.start_auto_backup` | BACKEND |
| SettingsPage | `self.stop_auto_backup_btn` | ⏹️ توقف | 1354 | `self.stop_auto_backup` | BACKEND |
| SettingsPage | `self.add_class_btn` | ➕ افزودن کلاس | 1500 | `self.add_class` | BACKEND |
| SettingsPage | `self.cancel_edit_class_btn` | ✖ انصراف از ویرایش | 1518 | `self.cancel_edit_class` | BACKEND |
| SettingsPage | `edit_btn` | ✏️ | 1638 | `lambda:self.edit_class()` | BACKEND |
| SettingsPage | `delete_btn` | 🗑️ | 1644 | `lambda:self.delete_class()` | BACKEND |

### `views/pages/student_profile_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| StudentProfilePage | `self.search_btn` | 🔍 جستجو | 121 | `self.search_student` | BACKEND |
| StudentProfilePage | `self.clear_search_btn` | ✖ | 136 | `self.clear_search` | NAV |
| StudentProfilePage | `self.btn_observation` | 📝 ثبت مشاهده | 227 | `self.add_observation` | BACKEND |
| StudentProfilePage | `self.btn_intervention` | 🛠️ ثبت مداخله | 242 | `self.add_intervention` | BACKEND |
| StudentProfilePage | `self.btn_followup` | 🔔 ثبت پیگیری | 257 | `self.add_followup` | BACKEND |
| StudentProfilePage | `self.btn_report` | 📄 گزارش پرونده | 274 | `self.generate_report` | BACKEND |
| StudentProfilePage | `self.btn_attachments` | 📎 پیوست‌ها | 291 | `self.open_attachments` | DIALOG |
| StudentProfilePage | `view_btn` | 👁️ | 1162 | `lambda:self.view_observation()` | MSG_ONLY |
| StudentProfilePage | `view_btn` | 👁️ | 1192 | `lambda:self.view_intervention()` | MSG_ONLY |
| StudentProfilePage | `view_btn` | 👁️ | 1222 | `lambda:self.view_followup()` | MSG_ONLY |

### `views/pages/students_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| StudentsPage | `self.advanced_search_btn` | 🔍 پیشرفته | 135 | `self.open_advanced_search` | DIALOG |
| StudentsPage | `self.add_btn` | ➕ افزودن دانش‌آموز | 150 | `self.add_student` | BACKEND |
| StudentsPage | `self.import_btn` | 📥 ایمپورت از Excel | 168 | `self.import_from_excel` | BACKEND |
| StudentsPage | `self.export_btn` | 📤 خروجی Excel | 185 | `self.export_to_excel` | BACKEND |
| StudentsPage | `self.sample_btn` | 📄 دریافت نمونه | 202 | `self.download_sample_excel` | BACKEND |
| StudentsPage | `self.prev_page_btn` | ◀ قبلی | 281 | `self.prev_page` | BACKEND |
| StudentsPage | `self.next_page_btn` | بعدی ▶ | 297 | `self.next_page` | BACKEND |
| StudentsPage | `edit_btn` | ✏️ | 405 | `lambda:self.edit_student()` | BACKEND |
| StudentsPage | `delete_btn` | 🗑️ | 422 | `lambda:self.delete_student()` | BACKEND |
| StudentsPage | `profile_btn` | 👤 | 439 | `lambda:self.open_profile()` | SIGNAL |

### `views/pages/teacher_performance_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| TeacherPerformancePage | `self.generate_btn` | 📊 تولید گزارش | 116 | `self.generate_report` | BACKEND |
| TeacherPerformancePage | `self.pdf_btn` | 📄 PDF | 134 | `self.export_pdf` | BACKEND |

### `views/pages/teacher_report_page.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| TeacherReportPage | `self.generate_btn` | 📊 تولید گزارش | 128 | `self.generate_report` | BACKEND |
| TeacherReportPage | `self.excel_btn` | 📊 Excel | 146 | `self.export_excel` | BACKEND |
| TeacherReportPage | `self.pdf_btn` | 📄 PDF | 161 | `self.export_pdf` | BACKEND |

### `views/dialogs/activity_form.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| ActivityForm | `self.save_btn` | 💾 ذخیره فعالیت | 326 | `self.save_activity` | BACKEND |
| ActivityForm | `self.cancel_btn` | ❌ انصراف | 343 | `self.reject` | UI_ONLY |

### `views/dialogs/advanced_search_dialog.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| AdvancedSearchDialog | `self.search_btn` | 🔍 جستجو | 112 | `self.perform_search` | BACKEND |
| AdvancedSearchDialog | `self.clear_btn` | 🗑️ پاک کردن | 128 | `self.clear_search` | NAV |

### `views/dialogs/assign_teacher_dialog.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| AssignTeacherDialog | `self.save_btn` |  | 160 | `self.save_assignment` | BACKEND |
| AssignTeacherDialog | `self.cancel_btn` | ❌ انصراف | 177 | `self.reject` | UI_ONLY |

### `views/dialogs/attachment_dialog.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| AttachmentDialog | `self.add_btn` | ➕ افزودن فایل | 148 | `self.add_attachment` | BACKEND |
| AttachmentDialog | `self.clear_search_btn` | ✖ | 187 | `self.clear_search` | BACKEND |
| AttachmentDialog | `self.refresh_btn` | 🔄 | 204 | `self.load_attachments` | BACKEND |
| AttachmentDialog | `self.open_btn` | 📂 باز کردن فایل | 393 | `self.open_file` | BACKEND |
| AttachmentDialog | `self.download_btn` | ⬇️ دانلود | 408 | `self.download_file` | BACKEND |
| AttachmentDialog | `self.delete_btn` | 🗑️ حذف | 423 | `self.delete_selected` | BACKEND |
| AttachmentDialog | `self.close_btn` | ❌ بستن | 440 | `self.accept` | UI_ONLY |

### `views/dialogs/change_password_dialog.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| ChangePasswordDialog | `self.save_btn` |  | 216 | `self.change_password` | BACKEND |
| ChangePasswordDialog | `self.cancel_btn` | انصراف | 233 | `self.reject` | UI_ONLY |

### `views/dialogs/counseling_session_form.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| CounselingSessionForm | `self.save_btn` | 💾 ذخیره جلسه | 385 | `self.save_session` | BACKEND |
| CounselingSessionForm | `self.cancel_btn` | ❌ انصراف | 402 | `self.reject` | UI_ONLY |

### `views/dialogs/export_ai_dialog.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| ExportAIDialog | `self.export_btn` | 📤 خروجی و دانلود | 276 | `self.export_data` | BACKEND |
| ExportAIDialog | `self.copy_prompt_btn` | 📋 کپی پرامپت | 293 | `self.copy_prompt` | MSG_ONLY |
| ExportAIDialog | `self.cancel_btn` | ❌ انصراف | 312 | `self.reject` | UI_ONLY |

### `views/dialogs/followup_form.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| FollowUpForm | `self.save_btn` | 💾 ذخیره پیگیری | 218 | `self.save_followup` | BACKEND |
| FollowUpForm | `self.cancel_btn` | ❌ انصراف | 234 | `self.reject` | UI_ONLY |

### `views/dialogs/goal_form.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| GoalForm | `self.save_btn` | 💾 ذخیره هدف | 335 | `self.save_goal` | BACKEND |
| GoalForm | `self.cancel_btn` | ❌ انصراف | 352 | `self.reject` | UI_ONLY |

### `views/dialogs/intervention_form.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| InterventionForm | `self.save_btn` | 💾 ذخیره مداخله | 285 | `self.save_intervention` | BACKEND |
| InterventionForm | `self.cancel_btn` | ❌ انصراف | 301 | `self.reject` | UI_ONLY |

### `views/dialogs/login_dialog.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| LoginDialog | `self.login_btn` | ورود به سامانه | 170 | `self.login` | BACKEND |
| LoginDialog | `self.change_pass_btn` | تغییر رمز عبور | 207 | `self.open_change_password` | DIALOG |
| LoginDialog | `self.exit_btn` | خروج | 226 | `self.reject` | UI_ONLY |

### `views/dialogs/observation_form.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| ObservationForm | `self.guide_btn` | ❓ راهنما | 125 | `self.show_guide` | MSG_ONLY |
| ObservationForm | `self.show_more_btn` | 🔽 نمایش فیلدهای بیشتر (اختیا | 365 | `self.toggle_more_fields` | UI_ONLY |
| ObservationForm | `clear_comp_btn` | 🗑️ پاک کردن انتخاب شایستگی | 489 | `self.clear_competency_selection` | UI_ONLY |
| ObservationForm | `self.save_btn` | 💾 ذخیره مشاهده | 582 | `self.save_observation` | BACKEND |
| ObservationForm | `self.cancel_btn` | انصراف | 599 | `self.reject` | UI_ONLY |

### `views/dialogs/student_form.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| StudentForm | `self.save_btn` | 💾 ذخیره | 175 | `self.save_student` | BACKEND |
| StudentForm | `self.cancel_btn` | ❌ انصراف | 189 | `self.reject` | UI_ONLY |

### `views/widgets/competency_tree_widget.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| CompetencyTreeWidget | `self.select_btn` | ✅ انتخاب | 145 | `self.emit_selection` | SIGNAL |
| CompetencyTreeWidget | `self.clear_btn` | 🗑️ پاک کردن انتخاب | 162 | `self.clear_selection` | UI_ONLY |

### `views/widgets/help_widget.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| HelpWidget | `self.toggle_btn` | ▼ | 93 | `self.toggle_expand` | UI_ONLY |
| HelpWidget | `self.more_btn` | 📖 راهنمای کامل | 147 | `self.show_full_help` | DIALOG |
| HelpWidget | `btn` | ❓ | 223 | `self.show_full_help` | DIALOG |

### `views/widgets/notification_widget.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| NotificationWidget | `self.view_all_btn` | مشاهده همه در داشبورد | 282 | `self.view_all` | NAV |
| NotificationWidget | `self.close_btn` | ✕ | 302 | `self.hide` | UI_ONLY |

### `views/widgets/recommendation_widget.py`

| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |
|---|---|---|---|---|---|
| RecommendationWidget | `self.generate_btn` | 🔄 تولید پیشنهادات جدید | 76 | `self.generate_recommendations` | BACKEND |
| RecommendationWidget | `accept_btn` | ✅ پذیرش | 336 | `lambda:self.accept_recommendation()` | BACKEND |
| RecommendationWidget | `reject_btn` | ❌ رد | 354 | `lambda:self.reject_recommendation()` | BACKEND |
| RecommendationWidget | `intervention_btn` | 🛠️ ثبت مداخله | 412 | `lambda:self.request_intervention()` | SIGNAL |
| RecommendationWidget | `implement_btn` | 🚀 اجرا | 373 | `lambda:self.implement_recommendation()` | BACKEND |
| RecommendationWidget | `complete_btn` | ✔️ تکمیل | 392 | `lambda:self.complete_recommendation()` | BACKEND |
