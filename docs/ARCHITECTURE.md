# معماری پروژه PARTOW

## 🏗️ نمای کلی

PARTOW یک سامانه آفلاین تحت ویندوز برای مدیریت پرونده‌های رشد و توانمندی دانش‌آموزان است. این سامانه با معماری لایه‌ای (Layered Architecture) طراحی شده است.
┌─────────────────────────────────────────────────────────────┐
│ Presentation Layer (View) │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │ Pages │ │ Dialogs │ │ Widgets │ │ Main │ │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Service Layer │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │ Student │ │Observe │ │Interven │ │Followup │ │
│ │ Service │ │ Service │ │ Service │ │ Service │ │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Data Access Layer (DAL) │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │Student │ │Observe │ │Interven │ │Followup │ │
│ │ DAL │ │ DAL │ │ DAL │ │ DAL │ │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Database Layer │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ SQLite Database │ │
│ │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │ │
│ │ │students│ │obs │ │inter │ │follow│ │staff │ │ │
│ │ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

## 📁 ساختار پوشه‌ها
PARTOW/
├── config/ # تنظیمات و ثابت‌ها
│ ├── constants.py # ثابت‌های پروژه
│ ├── messages.py # پیام‌های استاندارد
│ ├── settings.py # تنظیمات مرکزی
│ └── help_messages.py # پیام‌های راهنما
│
├── database/ # مدیریت دیتابیس
│ └── connection.py # اتصال به دیتابیس
│
├── dal/ # لایه دسترسی به داده
│ ├── student_dal.py
│ ├── observation_dal.py
│ ├── intervention_dal.py
│ ├── followup_dal.py
│ ├── staff_dal.py
│ ├── academic_year_dal.py
│ ├── competency_dal.py
│ ├── teacher_assignment_dal.py
│ └── audit_log_dal.py
│
├── models/ # مدل‌های داده
│ ├── base.py # مدل پایه
│ ├── student.py
│ ├── observation.py
│ ├── intervention.py
│ ├── followup.py
│ ├── staff.py
│ ├── academic_year.py
│ ├── competency.py
│ ├── enums.py # Enumها
│ └── student_academic_profile.py
│
├── services/ # لایه سرویس
│ ├── base_service.py
│ ├── student_service.py
│ ├── observation_service.py
│ ├── intervention_service.py
│ ├── followup_service.py
│ ├── dashboard_service.py
│ ├── case_timeline_service.py
│ ├── reminder_service.py
│ └── report_generator.py
│
├── utils/ # ابزارهای کمکی
│ ├── logger.py
│ ├── error_handler.py
│ ├── security.py
│ ├── backup.py
│ ├── persian_date.py
│ └── persian_pdf.py
│
├── views/ # لایه نمایش
│ ├── main_window.py
│ ├── pages/ # صفحات اصلی
│ │ ├── dashboard_page.py
│ │ ├── students_page.py
│ │ ├── observations_page.py
│ │ ├── interventions_page.py
│ │ ├── followups_page.py
│ │ ├── indicators_page.py
│ │ ├── analysis_page.py
│ │ ├── reports_page.py
│ │ └── settings_page.py
│ └── dialogs/ # دیالوگ‌ها
│ ├── student_form.py
│ ├── observation_form.py
│ ├── intervention_form.py
│ ├── followup_form.py
│ └── attachment_dialog.py
│
├── tests/ # تست‌ها
│ ├── test_services.py
│ └── test_dal.py
│
├── docs/ # مستندات
│ ├── architecture.md
│ ├── erd.md
│ ├── workflow.md
│ └── folder_structure.md
│
├── assets/ # منابع
│ ├── styles/
│ └── images/
│
├── main.py # نقطه ورود برنامه
└── requirements.txt # وابستگی‌ها

## 🔄 جریان داده
کاربر با View تعامل دارد

View داده‌ها را به Service ارسال می‌کند

Service اعتبارسنجی و منطق کسب‌وکار را انجام می‌دهد

Service از DAL برای ذخیره/دریافت داده استفاده می‌کند

DAL با Database ارتباط برقرار می‌کند

نتیجه به صورت زنجیره‌ای به View بازمی‌گردد

## 🛡️ اصول طراحی

1. **Separation of Concerns**: هر لایه مسئولیت مشخصی دارد
2. **Dependency Injection**: وابستگی‌ها به صورت واضح مدیریت می‌شوند
3. **Single Responsibility**: هر کلاس فقط یک وظیفه دارد
4. **Open/Closed**: کلاس‌ها برای توسعه باز و برای تغییر بسته هستند
5. **DRY**: از تکرار کد پرهیز می‌شود