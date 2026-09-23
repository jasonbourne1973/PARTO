# ساختار پوشه‌های پروژه PARTOW

## 📁 ساختار کامل
PARTOW/
│
├── 📁 assets/ # منابع و فایل‌های استاتیک
│ ├── 📁 fonts/ # فونت‌ها
│ │ ├── Vazir.ttf
│ │ └── BNazanin.ttf
│ ├── 📁 images/ # تصاویر و لوگو
│ │ └── logo.png
│ └── 📁 styles/ # فایل‌های استایل
│ └── main_style.qss
│
├── 📁 config/ # تنظیمات و ثابت‌ها
│ ├── init.py
│ ├── constants.py # ثابت‌های پروژه
│ ├── messages.py # پیام‌های استاندارد
│ ├── settings.py # تنظیمات مرکزی
│ └── help_messages.py # پیام‌های راهنما
│
├── 📁 database/ # مدیریت دیتابیس
│ ├── init.py
│ ├── connection.py # اتصال به دیتابیس
│ └── partow.db # فایل دیتابیس (ایجاد می‌شود)
│
├── 📁 dal/ # لایه دسترسی به داده
│ ├── init.py
│ ├── student_dal.py
│ ├── observation_dal.py
│ ├── intervention_dal.py
│ ├── followup_dal.py
│ ├── staff_dal.py
│ ├── academic_year_dal.py
│ ├── competency_dal.py
│ ├── teacher_assignment_dal.py
│ ├── student_academic_profile_dal.py
│ └── audit_log_dal.py
│
├── 📁 models/ # مدل‌های داده
│ ├── init.py
│ ├── base.py # مدل پایه
│ ├── student.py
│ ├── observation.py
│ ├── intervention.py
│ ├── followup.py
│ ├── staff.py
│ ├── academic_year.py
│ ├── competency.py
│ ├── enums.py # Enumها
│ ├── student_academic_profile.py
│ ├── teacher_assignment.py
│ └── attachment.py
│
├── 📁 services/ # لایه سرویس
│ ├── init.py
│ ├── base_service.py # سرویس پایه
│ ├── student_service.py
│ ├── observation_service.py
│ ├── intervention_service.py
│ ├── followup_service.py
│ ├── dashboard_service.py
│ ├── case_timeline_service.py # Timeline یکپارچه
│ ├── reminder_service.py # یادآوری‌ها
│ ├── report_generator.py # تولید گزارش
│ └── teacher_report_service.py # گزارش معلم
│
├── 📁 utils/ # ابزارهای کمکی
│ ├── init.py
│ ├── logger.py # سیستم لاگ‌نویسی
│ ├── error_handler.py # مدیریت خطاها
│ ├── security.py # امنیت و هش
│ ├── backup.py # پشتیبان‌گیری
│ ├── cache.py # کش داده‌ها
│ ├── persian_date.py # تاریخ شمسی
│ ├── persian_calendar.py # تقویم شمسی
│ ├── persian_pdf.py # تولید PDF فارسی
│ └── shamsi_date_input.py # ورودی تاریخ شمسی
│
├── 📁 views/ # لایه نمایش
│ ├── init.py
│ ├── main_window.py # پنجره اصلی
│ │
│ ├── 📁 pages/ # صفحات اصلی
│ │ ├── init.py
│ │ ├── dashboard_page.py
│ │ ├── students_page.py
│ │ ├── observations_page.py
│ │ ├── interventions_page.py
│ │ ├── followups_page.py
│ │ ├── indicators_page.py
│ │ ├── analysis_page.py
│ │ ├── reports_page.py
│ │ ├── settings_page.py
│ │ ├── promotion_page.py
│ │ ├── teacher_report_page.py
│ │ ├── student_profile_page.py
│ │ └── backup_page.py
│ │
│ └── 📁 dialogs/ # دیالوگ‌ها
│ ├── init.py
│ ├── student_form.py
│ ├── observation_form.py
│ ├── intervention_form.py
│ ├── followup_form.py
│ ├── assign_teacher_dialog.py
│ ├── advanced_search_dialog.py
│ └── attachment_dialog.py
│
├── 📁 tests/ # تست‌ها
│ ├── init.py
│ ├── test_services.py
│ └── test_dal.py
│
├── 📁 docs/ # مستندات
│ ├── architecture.md
│ ├── erd.md
│ ├── workflow.md
│ └── folder_structure.md
│
├── 📁 backups/ # فایل‌های پشتیبان
│ └── (ایجاد می‌شود)
│
├── 📁 reports/ # گزارش‌های خروجی
│ └── (ایجاد می‌شود)
│
├── 📁 logs/ # فایل‌های لاگ
│ ├── partow.log
│ ├── errors.log
│ └── audit.json
│
├── main.py # نقطه ورود برنامه
├── requirements.txt # وابستگی‌ها
└── README.md # توضیحات پروژه

## 📂 توضیحات پوشه‌ها

| پوشه | توضیح |
|:---|:---|
| `assets/` | منابع استاتیک (فونت‌ها، تصاویر، استایل‌ها) |
| `config/` | تنظیمات، ثابت‌ها و پیام‌های برنامه |
| `database/` | مدیریت دیتابیس و فایل دیتابیس |
| `dal/` | لایه دسترسی به داده (Data Access Layer) |
| `models/` | مدل‌های داده و Enumها |
| `services/` | لایه سرویس (منطق کسب‌وکار) |
| `utils/` | ابزارهای کمکی عمومی |
| `views/` | لایه نمایش (UI) |
| `tests/` | تست‌های خودکار |
| `docs/` | مستندات پروژه |
| `backups/` | فایل‌های پشتیبان |
| `reports/` | گزارش‌های خروجی |
| `logs/` | فایل‌های لاگ |

## 📝 فایل‌های اصلی

| فایل | توضیح |
|:---|:---|
| `main.py` | نقطه ورود برنامه |
| `requirements.txt` | لیست وابستگی‌ها |
| `README.md` | توضیحات و راهنمای نصب |
