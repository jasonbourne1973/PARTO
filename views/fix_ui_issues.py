# ============================================================
# fix_ui_issues.py
# ============================================================
# این فایل تمام مشکلات رابط کاربری گزارش‌شده را یکجا برطرف می‌کند
# برای اجرا: python fix_ui_issues.py
# ============================================================

import os
import re
import sys
from pathlib import Path

# ============================================================
# ۱. اصلاح پنجره ورود - اسامی کادرها مشکی
# ============================================================

def fix_login_dialog():
    """رفع مشکل رنگ متن فرم ورود"""
    file_path = Path("views/dialogs/login_dialog.py")
    if not file_path.exists():
        print(f"⚠️ فایل {file_path} یافت نشد")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # اصلاح استایل QFormLayout QLabel
    old_style = '''QFormLayout QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #111111;
            }'''
    
    new_style = '''QFormLayout QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #F4C542;
            }'''
    
    if old_style in content:
        content = content.replace(old_style, new_style)
    else:
        # اگر دقیقاً منطبق نبود، با regex جایگزین کن
        content = re.sub(
            r'(QFormLayout QLabel \{[\s\S]*?color: )#111111([\s\S]*?\})',
            r'\1#F4C542\2',
            content
        )
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ پنجره ورود اصلاح شد")
    return True


# ============================================================
# ۲. حذف لوگوی صفحه خوش‌آمدگویی
# ============================================================

def fix_welcome_logo():
    """حذف لوگوی بزرگ از صفحه خوش‌آمدگویی"""
    file_path = Path("main_window.py")
    if not file_path.exists():
        print(f"⚠️ فایل {file_path} یافت نشد")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # پیدا کردن بخش _create_welcome_page و حذف لوگو
    # الگوی جستجو برای بخش لوگو
    pattern = r'(if os\.path\.exists\(LOGO_PATH\):.*?content_layout\.addSpacing\(10\))'
    
    # جایگزینی با یک کامنت
    replacement = '# لوگوی بزرگ صفحه خوش‌آمدگویی حذف شد (درخواست کاربر)'
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # همچنین لوگوی محو (پس‌زمینه) را نگه می‌داریم
    # (این همانی است که کاربر گفت نگه دارد)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ لوگوی صفحه خوش‌آمدگویی حذف شد")
    return True


# ============================================================
# ۳. اصلاح نمودارها - حروف برعکس و مشکی
# ============================================================

def fix_chart_helper():
    """رفع مشکل جهت نوشته‌ها و رنگ‌های نمودار"""
    file_path = Path("utils/chart_helper.py")
    if not file_path.exists():
        print(f"⚠️ فایل {file_path} یافت نشد")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # اصلاح متد create_trend_chart
    # اطمینان از استفاده از _farsi برای همه برچسب‌ها
    
    # پیدا کردن بخش set_xticklabels
    pattern1 = r"ax\.set_xticklabels\(labels, fontsize=9, color='#475569', fontweight='bold'\)"
    replacement1 = "ax.set_xticklabels(labels_fa, fontsize=9, color='#F4C542', fontweight='bold')"
    content = content.replace(pattern1, replacement1)
    
    # اصلاح رنگ محورها
    pattern2 = r"ax\.tick_params\(axis='both', which='both', length=0, labelsize=9, colors='#D9C36A'\)"
    replacement2 = "ax.tick_params(axis='both', which='both', length=0, labelsize=9, colors='#F4C542')"
    content = content.replace(pattern2, replacement2)
    
    # اصلاح رنگ عنوان
    pattern3 = r"ax\.set_title\(ChartHelper\._farsi\(title\), fontsize=14, fontweight='bold', color='#F4C542', pad=15\)"
    # این درست است، فقط مطمئن می‌شویم که در همه جا استفاده شده
    
    # اضافه کردن تابع _farsi برای مطمئن شدن از استفاده در همه جا
    if "def _farsi" not in content:
        # تابع _farsi را اضافه کن
        farsi_func = '''
    @staticmethod
    def _farsi(text):
        """اصلاح نمایش حروف فارسی در Matplotlib"""
        if not text:
            return ""
        if PERSIAN_FONT_SUPPORT:
            try:
                return get_display(arabic_reshaper.reshape(str(text)))
            except:
                return str(text)
        return str(text)
'''
        # پیدا کردن جای مناسب برای درج
        content = content.replace('class ChartHelper:', 'class ChartHelper:' + farsi_func)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ نمودارها اصلاح شدند")
    return True


# ============================================================
# ۴. اصلاح گزارش معلم - دکمه‌های تو در تو
# ============================================================

def fix_teacher_report():
    """رفع مشکل دکمه‌های تو در تو در گزارش معلم"""
    file_path = Path("views/pages/teacher_report_page.py")
    if not file_path.exists():
        print(f"⚠️ فایل {file_path} یافت نشد")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # پیدا کردن بخش setup_ui و اصلاح toolbar
    # الگوی جستجو برای نوار ابزار
    pattern = r'(toolbar = QHBoxLayout\(\)\s*.*?self\.pdf_btn.*?\)\s*)'
    
    # ساخت layout جدید با spacing مناسب
    new_toolbar = '''toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.setContentsMargins(5, 5, 5, 5)
        
        # گروه معلم
        teacher_group = QHBoxLayout()
        teacher_group.setSpacing(5)
        teacher_group.addWidget(QLabel("معلم:"))
        teacher_group.addWidget(self.teacher_combo)
        toolbar.addLayout(teacher_group)
        
        toolbar.addSpacing(15)
        
        # گروه سال تحصیلی
        year_group = QHBoxLayout()
        year_group.setSpacing(5)
        year_group.addWidget(QLabel("سال تحصیلی:"))
        year_group.addWidget(self.year_combo)
        toolbar.addLayout(year_group)
        
        toolbar.addSpacing(15)
        
        # گروه تاریخ
        date_group = QHBoxLayout()
        date_group.setSpacing(5)
        date_group.addWidget(QLabel("از تاریخ:"))
        date_group.addWidget(self.start_date)
        date_group.addWidget(QLabel("تا تاریخ:"))
        date_group.addWidget(self.end_date)
        toolbar.addLayout(date_group)
        
        toolbar.addStretch()
        
        # گروه دکمه‌ها
        btn_group = QHBoxLayout()
        btn_group.setSpacing(8)
        btn_group.addWidget(self.generate_btn)
        btn_group.addWidget(self.excel_btn)
        btn_group.addWidget(self.pdf_btn)
        toolbar.addLayout(btn_group)'''
    
    # جایگزینی
    content = re.sub(pattern, new_toolbar, content, flags=re.DOTALL)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ گزارش معلم اصلاح شد")
    return True


# ============================================================
# ۵. اصلاح دکمه‌های خروجی در گزارش‌ها
# ============================================================

def fix_reports_page():
    """رفع استایل دکمه‌های خروجی در گزارش‌ها"""
    file_path = Path("views/pages/reports_page.py")
    if not file_path.exists():
        print(f"⚠️ فایل {file_path} یافت نشد")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # اصلاح استایل دکمه PDF
    pdf_style = '''self.pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 15px;
                border: 2px solid #8BC34A;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8BC34A;
            }
        """)'''
    
    # اصلاح استایل دکمه Excel
    excel_style = '''self.excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 15px;
                border: 2px solid #8BC34A;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8BC34A;
            }
        """)'''
    
    # پیدا کردن و جایگزینی
    # دکمه PDF
    pattern_pdf = r'self\.pdf_btn\.setStyleSheet\(.*?\)'
    content = re.sub(pattern_pdf, pdf_style, content, flags=re.DOTALL)
    
    # دکمه Excel
    pattern_excel = r'self\.excel_btn\.setStyleSheet\(.*?\)'
    content = re.sub(pattern_excel, excel_style, content, flags=re.DOTALL)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ دکمه‌های خروجی گزارش اصلاح شدند")
    return True


# ============================================================
# ۶. اصلاح تحلیل روند - کادرهای تاریخ
# ============================================================

def fix_analysis_page():
    """رفع مشکل کادرهای تاریخ در تحلیل روند"""
    file_path = Path("views/pages/analysis_page.py")
    if not file_path.exists():
        print(f"⚠️ فایل {file_path} یافت نشد")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # اصلاح استایل date_group
    date_group_style = '''date_group = QGroupBox("📅 بازه زمانی تحلیل (شمسی)")
        date_group.setStyleSheet("""
            QGroupBox {
                color: #111111;
                font-weight: bold;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #66BB6A;
            }
            QGroupBox::title {
                background-color: #8BC34A;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #111111;
            }
        """)'''
    
    # اضافه کردن استایل برای ShamsiDateInput
    date_input_style = '''
        # تنظیم استایل ورودی‌های تاریخ
        self.start_date.setStyleSheet("""
            QLineEdit {
                background-color: #08223A;
                color: #F4C542;
                border: 2px solid #8BC34A;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
                min-height: 32px;
                min-width: 120px;
            }
            QLineEdit:focus {
                border: 2px solid #F4C542;
                background-color: #0B2E4F;
            }
        """)
        
        self.end_date.setStyleSheet("""
            QLineEdit {
                background-color: #08223A;
                color: #F4C542;
                border: 2px solid #8BC34A;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
                min-height: 32px;
                min-width: 120px;
            }
            QLineEdit:focus {
                border: 2px solid #F4C542;
                background-color: #0B2E4F;
            }
        """)'''
    
    # جایگزینی
    pattern_date_group = r'date_group = QGroupBox\(.*?\)\s*date_group\.setStyleSheet\(.*?\)'
    content = re.sub(pattern_date_group, date_group_style, content, flags=re.DOTALL)
    
    # اضافه کردن استایل تاریخ‌ها
    if "self.start_date.setStyleSheet" not in content:
        # پیدا کردن جای مناسب برای درج
        content = content.replace(
            'self.start_date = ShamsiDateInput()',
            'self.start_date = ShamsiDateInput()\n        self.start_date.setStyleSheet("""\n            QLineEdit {\n                background-color: #08223A;\n                color: #F4C542;\n                border: 2px solid #8BC34A;\n                border-radius: 5px;\n                padding: 5px 10px;\n                font-size: 13px;\n                min-height: 32px;\n                min-width: 120px;\n            }\n            QLineEdit:focus {\n                border: 2px solid #F4C542;\n                background-color: #0B2E4F;\n            }\n        """)'
        )
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ تحلیل روند اصلاح شد")
    return True


# ============================================================
# ۷. اصلاح مدیریت مداخلات - کادرهای تو در تو
# ============================================================

def fix_interventions_page():
    """رفع مشکل کادرهای تو در تو در مدیریت مداخلات"""
    file_path = Path("views/pages/interventions_page.py")
    if not file_path.exists():
        print(f"⚠️ فایل {file_path} یافت نشد")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # اصلاح toolbar با spacing مناسب
    toolbar_pattern = r'(toolbar = QHBoxLayout\(\)\s*.*?self\.add_btn.*?\))'
    new_toolbar = '''toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        toolbar.setContentsMargins(5, 5, 5, 5)
        
        # گروه عنوان
        title_group = QHBoxLayout()
        title_group.addWidget(title_label)
        toolbar.addLayout(title_group)
        
        toolbar.addStretch()
        
        # گروه معلم
        teacher_group = QHBoxLayout()
        teacher_group.setSpacing(5)
        teacher_group.addWidget(QLabel("معلم:"))
        teacher_group.addWidget(self.teacher_combo)
        toolbar.addLayout(teacher_group)
        
        toolbar.addSpacing(10)
        
        # گروه دانش‌آموز
        student_group = QHBoxLayout()
        student_group.setSpacing(5)
        student_group.addWidget(QLabel("دانش‌آموز:"))
        student_group.addWidget(self.student_filter_combo)
        toolbar.addLayout(student_group)
        
        toolbar.addSpacing(10)
        
        # گروه جستجو
        search_group = QHBoxLayout()
        search_group.setSpacing(5)
        search_group.addWidget(self.search_input)
        search_group.addWidget(self.search_btn)
        search_group.addWidget(self.clear_search_btn)
        toolbar.addLayout(search_group)
        
        toolbar.addSpacing(10)
        
        # گروه وضعیت
        status_group = QHBoxLayout()
        status_group.setSpacing(5)
        status_group.addWidget(QLabel("وضعیت:"))
        status_group.addWidget(self.status_filter_combo)
        toolbar.addLayout(status_group)
        
        toolbar.addSpacing(10)
        
        # دکمه افزودن
        toolbar.addWidget(self.add_btn)'''
    
    content = re.sub(toolbar_pattern, new_toolbar, content, flags=re.DOTALL)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ مدیریت مداخلات اصلاح شد")
    return True


# ============================================================
# ۸. اصلاح منوی گزارش‌ها
# ============================================================

def fix_main_menu():
    """رفع مشکل منوی تو در تو"""
    file_path = Path("main_window.py")
    if not file_path.exists():
        print(f"⚠️ فایل {file_path} یافت نشد")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # اصلاح استایل دکمه‌های منو
    btn_style = '''btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #F4C542;
                    border: none;
                    border-radius: 0px;
                    padding: 8px 16px;
                    text-align: right;
                    font-size: 12px;
                    font-weight: 500;
                    min-height: 32px;
                    max-height: 38px;
                    margin: 1px 0px;
                }
                QPushButton:hover {
                    background-color: #174F78;
                    color: #FFE8A3;
                    border-right: 3px solid #F4C542;
                }
                QPushButton:pressed {
                    background-color: #08223A;
                    color: #FFE8A3;
                    border-right: 3px solid #F4C542;
                }
            """)'''
    
    # پیدا کردن بخش ایجاد دکمه‌های منو
    menu_pattern = r'btn\.setStyleSheet\(.*?\)'
    content = re.sub(menu_pattern, btn_style, content, flags=re.DOTALL)
    
    # تنظیم spacing منو
    menu_spacing = 'menu_layout.setSpacing(1)'
    content = content.replace('menu_layout.setSpacing(2)', menu_spacing)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ منوی اصلی اصلاح شد")
    return True


# ============================================================
# ۹. اصلاح داشبورد تحلیلی
# ============================================================

def fix_analytics_dashboard():
    """رفع مشکل نوشته‌های مشکی و برعکس در داشبورد تحلیلی"""
    file_path = Path("views/pages/analytics_dashboard.py")
    if not file_path.exists():
        print(f"⚠️ فایل {file_path} یافت نشد")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # اصلاح رنگ کارت‌ها
    card_style = '''card.value_label.setStyleSheet(f"""
                font-size: 22px;
                font-weight: 800;
                color: #F4C542;
                padding-top: 4px;
            """)'''
    
    # جایگزینی استایل‌های کارت
    content = re.sub(
        r'card\.value_label\.setStyleSheet\(.*?\)',
        card_style,
        content,
        flags=re.DOTALL
    )
    
    # اصلاح عنوان کارت‌ها
    title_style = 'title_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #F4C542;")'
    content = re.sub(
        r'title_label\.setStyleSheet\(.*?\)',
        title_style,
        content,
        flags=re.DOTALL
    )
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ داشبورد تحلیلی اصلاح شد")
    return True


# ============================================================
# ۱۰. اصلاح پرونده دانش‌آموزان - کادر جداکننده
# ============================================================

def fix_student_profile():
    """رفع مشکل کادر جداکننده در پرونده دانش‌آموزان"""
    file_path = Path("views/pages/student_profile_page.py")
    if not file_path.exists():
        print(f"⚠️ فایل {file_path} یافت نشد")
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # اصلاح استایل header_frame
    header_style = '''self.header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #F4C542, stop:1 #66BB6A);
                border-radius: 8px;
                border: 2px solid #D9C36A;
                padding: 15px;
            }
        """)'''
    
    content = re.sub(
        r'self\.header_frame\.setStyleSheet\(.*?\)',
        header_style,
        content,
        flags=re.DOTALL
    )
    
    # اصلاح استایل timeline_frame
    timeline_style = '''timeline_frame.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: 2px solid #D9C36A;
                border-radius: 8px;
                padding: 5px;
            }
        """)'''
    
    content = re.sub(
        r'timeline_frame\.setStyleSheet\(.*?\)',
        timeline_style,
        content,
        flags=re.DOTALL
    )
    
    # اصلاح استایل details_frame
    details_style = '''details_frame.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: 2px solid #D9C36A;
                border-radius: 8px;
                padding: 5px;
            }
        """)'''
    
    content = re.sub(
        r'details_frame\.setStyleSheet\(.*?\)',
        details_style,
        content,
        flags=re.DOTALL
    )
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ پرونده دانش‌آموزان اصلاح شد")
    return True


# ============================================================
# اجرای همه اصلاحات
# ============================================================

def main():
    print("=" * 60)
    print("شروع اصلاح مشکلات رابط کاربری PARTO")
    print("=" * 60)
    print()
    
    fixes = [
        ("پنجره ورود", fix_login_dialog),
        ("لوگوی خوش‌آمدگویی", fix_welcome_logo),
        ("نمودارها", fix_chart_helper),
        ("گزارش معلم", fix_teacher_report),
        ("دکمه‌های خروجی", fix_reports_page),
        ("تحلیل روند", fix_analysis_page),
        ("مدیریت مداخلات", fix_interventions_page),
        ("منوی اصلی", fix_main_menu),
        ("داشبورد تحلیلی", fix_analytics_dashboard),
        ("پرونده دانش‌آموزان", fix_student_profile),
    ]
    
    success_count = 0
    for name, func in fixes:
        print(f"⏳ در حال اصلاح: {name}...")
        try:
            if func():
                success_count += 1
            else:
                print(f"⚠️ اصلاح {name} با مشکل مواجه شد")
        except Exception as e:
            print(f"❌ خطا در اصلاح {name}: {e}")
        print()
    
    print("=" * 60)
    print(f"✅ {success_count} از {len(fixes)} مشکل با موفقیت اصلاح شد")
    print("=" * 60)
    print()
    print("📌 نکته: برای اعمال تغییرات، برنامه را مجدداً اجرا کنید.")
    print("📌 در صورت نیاز به بازگردانی تغییرات، از Git استفاده کنید.")


if __name__ == "__main__":
    main()