# مدل داده (ER Diagram)

## 📊 نمودار ER
┌─────────────────┐ ┌─────────────────────────┐
│ students │ │ academic_years │
├─────────────────┤ ├─────────────────────────┤
│ id (PK) │ │ id (PK) │
│ first_name │ │ title │
│ last_name │ │ start_date │
│ national_code │ │ end_date │
│ birth_date │ │ is_active │
│ father_name │ │ is_archived │
│ guardian_name │ │ created_at │
│ guardian_phone │ │ updated_at │
│ address │ └─────────────────────────┘
│ is_active │ │
│ created_at │ │
│ updated_at │ │
│ is_deleted │ │
│ deleted_at │ │
│ deleted_by │ │
└─────────────────┘ │
│ │
│ 1 │ 1
│ │
▼ ▼
┌─────────────────────────────────────────────────────┐
│ student_academic_profiles │
├─────────────────────────────────────────────────────┤
│ id (PK) │
│ student_id (FK → students) │
│ academic_year_id (FK → academic_years) │
│ grade │
│ class_name │
│ status │
│ status_history │
│ created_at │
│ updated_at │
│ is_deleted │
│ deleted_at │
│ deleted_by │
└─────────────────────────────────────────────────────┘
│
│ 1
│
▼
┌─────────────────────────────────────────────────────┐
│ observations │
├─────────────────────────────────────────────────────┤
│ id (PK) │
│ student_profile_id (FK → profiles) │
│ staff_id (FK → staff) │
│ competency_id (FK → competencies) │
│ observation_date │
│ location │
│ description │
│ antecedent │
│ behavior │
│ consequence │
│ behavior_type │
│ severity │
│ tags │
│ created_at │
│ updated_at │
│ is_deleted │
│ deleted_at │
│ deleted_by │
└─────────────────────────────────────────────────────┘
│
│ 0..1
│
▼
┌─────────────────────────────────────────────────────┐
│ interventions │
├─────────────────────────────────────────────────────┤
│ id (PK) │
│ student_profile_id (FK → profiles) │
│ staff_id (FK → staff) │
│ observation_id (FK → observations) │
│ type │
│ date │
│ description │
│ goal │
│ status │
│ result │
│ created_at │
│ updated_at │
│ is_deleted │
│ deleted_at │
│ deleted_by │
└─────────────────────────────────────────────────────┘
│
│ 1
│
▼
┌─────────────────────────────────────────────────────┐
│ followups │
├─────────────────────────────────────────────────────┤
│ id (PK) │
│ intervention_id (FK → interventions) │
│ staff_id (FK → staff) │
│ date │
│ method │
│ description │
│ status │
│ next_action_date │
│ result_type │
│ result_description │
│ created_at │
│ updated_at │
│ is_deleted │
│ deleted_at │
│ deleted_by │
└─────────────────────────────────────────────────────┘

## 📋 توضیحات جداول

### 1. students (دانش‌آموزان)
اطلاعات دائمی دانش‌آموزان را ذخیره می‌کند.

### 2. academic_years (سال‌های تحصیلی)
سال‌های تحصیلی را مدیریت می‌کند.

### 3. student_academic_profiles (پرونده‌های سالانه)
پرونده سالانه هر دانش‌آموز را ذخیره می‌کند.

### 4. observations (مشاهدات)
مشاهدات ثبت‌شده با مدل ABC را ذخیره می‌کند.

### 5. interventions (مداخلات)
مداخلات ثبت‌شده را ذخیره می‌کند.

### 6. followups (پیگیری‌ها)
پیگیری‌های ثبت‌شده را ذخیره می‌کند.

## 🔑 کلیدهای خارجی

| جدول | کلید خارجی | ارجاع به |
|:---|:---|:---|
| student_academic_profiles | student_id | students.id |
| student_academic_profiles | academic_year_id | academic_years.id |
| observations | student_profile_id | student_academic_profiles.id |
| observations | staff_id | staff.id |
| observations | competency_id | competencies.id |
| interventions | student_profile_id | student_academic_profiles.id |
| interventions | staff_id | staff.id |
| interventions | observation_id | observations.id |
| followups | intervention_id | interventions.id |
| followups | staff_id | staff.id |

## 🔄 چرخه داده
Student → StudentAcademicProfile → Observation → Intervention → FollowUp

هر دانش‌آموز در هر سال یک پرونده دارد.
هر پرونده می‌تواند چندین مشاهده داشته باشد.
هر مشاهده می‌تواند به یک مداخله منجر شود.
هر مداخله می‌تواند چندین پیگیری داشته باشد.