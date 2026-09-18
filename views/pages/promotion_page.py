"""
صفحه مدیریت ارتقاء پایه دانش‌آموزان - نسخه اصلاح‌شده با جستجو
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
    QMessageBox, QComboBox, QGroupBox, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from dal.student_dal import StudentDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.academic_year_dal import AcademicYearDAL
from datetime import datetime
import jdatetime


class PromotionPage(QWidget):
    """صفحه مدیریت ارتقاء پایه دانش‌آموزان"""
    
    def __init__(self, parent=None, embedded=False):
        super().__init__(parent)
        self.embedded = embedded
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.students = []
        self.all_students = []  # ذخیره همه دانش‌آموزان برای جستجو
        self.selected_student_ids = []
        self.current_search_results = []  # نتایج جستجوی فعلی
        
        self.setup_ui()
        self.load_students()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        if not self.embedded:
            title_label = QLabel("📈 مدیریت ارتقاء پایه")
            title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
            layout.addWidget(title_label)
        
        # گروه سال تحصیلی
        info_group = QGroupBox("📅 تنظیمات سال تحصیلی (شمسی)")
        info_group.setStyleSheet("""
            QGroupBox {
    color: #111111;
                font-weight: bold;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #66BB6A;
            }
            QGroupBox::title {
    background-color: #8BC34A;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #111111;
            }
        """)
        info_layout = QHBoxLayout(info_group)
        
        info_layout.addWidget(QLabel("سال تحصیلی جدید (شمسی):"))
        self.year_input = QComboBox()
        
        try:
            jalali_now = jdatetime.datetime.now()
            current_jalali_year = jalali_now.year
        except:
            current_jalali_year = datetime.now().year - 621
        
        for year in range(current_jalali_year - 2, current_jalali_year + 5):
            self.year_input.addItem(f"{year}-{year+1}")
        
        self.year_input.setCurrentText(f"{current_jalali_year+1}-{current_jalali_year+2}")
        
        info_layout.addWidget(self.year_input)
        
        layout.addWidget(info_group)
        
        # ===== نوار جستجو =====
        search_group = QGroupBox("🔍 جستجوی دانش‌آموز")
        search_group.setStyleSheet("""
            QGroupBox {
    color: #111111;
                font-weight: bold;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #66BB6A;
            }
            QGroupBox::title {
    background-color: #8BC34A;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #111111;
            }
        """)
        search_layout = QHBoxLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجوی نام، نام خانوادگی یا کد ملی...")
        self.search_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                padding: 8px 12px;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                font-size: 13px;
                min-width: 250px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F;
                border: 2px solid #F4C542;
            }
        """)
        search_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("🔍 جستجو")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #66BB6A; }
        """)
        self.search_btn.clicked.connect(self.search_students)
        search_layout.addWidget(self.search_btn)
        
        self.clear_search_btn = QPushButton("✖ نمایش همه")
        self.clear_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #9E1B1B; }
        """)
        self.clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_search_btn)
        
        search_layout.addStretch()
        
        # نمایش تعداد نتایج
        self.result_count_label = QLabel("")
        self.result_count_label.setStyleSheet("color: #D9C36A; font-size: 13px;")
        search_layout.addWidget(self.result_count_label)
        
        layout.addWidget(search_group)
        
        # گروه دکمه‌ها
        action_group = QGroupBox("⚡ عملیات")
        action_group.setStyleSheet("""
            QGroupBox {
    color: #111111;
                font-weight: bold;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #66BB6A;
            }
            QGroupBox::title {
    background-color: #8BC34A;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #111111;
            }
        """)
        action_layout = QHBoxLayout(action_group)
        
        self.promote_all_btn = QPushButton("📈 ارتقاء همه")
        self.promote_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.promote_all_btn.clicked.connect(self.promote_all_students)
        action_layout.addWidget(self.promote_all_btn)
        
        self.promote_selected_btn = QPushButton("📌 ارتقاء انتخاب‌شده")
        self.promote_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #F4D35E;
                color: #F4C542;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #F28C28; }
        """)
        self.promote_selected_btn.clicked.connect(self.promote_selected_students)
        action_layout.addWidget(self.promote_selected_btn)
        
        self.repeat_grade_btn = QPushButton("🔄 تکرار پایه")
        self.repeat_grade_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #9E1B1B; }
        """)
        self.repeat_grade_btn.clicked.connect(self.repeat_grade_students)
        action_layout.addWidget(self.repeat_grade_btn)
        
        layout.addWidget(action_group)
        
        # جدول دانش‌آموزان
        table_label = QLabel("📋 لیست دانش‌آموزان (برای انتخاب، روی ردیف کلیک کنید)")
        table_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(table_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "✅", "ردیف", "نام و نام خانوادگی", "پایه فعلی", "پایه جدید", "کلاس"
        ])
        
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
    color: #F4C542;
                background-color: #0B2E4F;
                alternate-background-color: #0B2E4F;
                gridline-color: #D9C36A;
                border: 1px solid #D9C36A;
                border-radius: 5px;
            }
            QTableWidget::item {
    color: #F4C542;
    border-bottom: 1px solid #D9C36A;
    background-color: #0B2E4F; padding: 8px; }
            QTableWidget::item:hover {
    color: #FFE8A3; background-color: #174F78; }
            QHeaderView::section {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px;
                border: 1px solid #D9C36A;
                font-weight: bold;
            }
        """)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemClicked.connect(self.on_item_clicked)
        
        layout.addWidget(self.table)
        
        help_label = QLabel(
            "💡 راهنما: روی هر ردیف کلیک کنید تا انتخاب شود. "
            "دانش‌آموزان پایه ششم فارغ‌التحصیل می‌شوند."
        )
        help_label.setStyleSheet("color: #D9C36A; font-size: 12px; margin-top: 5px;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
    
    def load_students(self):
        """بارگذاری لیست دانش‌آموزان"""
        try:
            self.all_students = self.student_dal.get_all()
            self.students = self.all_students.copy()
            self.selected_student_ids = []
            self.current_search_results = []
            self.result_count_label.setText(f"تعداد کل: {len(self.students)}")
            self.display_students(self.students)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری دانش‌آموزان:\n{str(e)}")
    
    def search_students(self):
        """جستجوی دانش‌آموزان"""
        search_term = self.search_input.text().strip()
        
        if not search_term:
            QMessageBox.warning(self, "توجه", "لطفاً عبارت جستجو را وارد کنید.")
            return
        
        try:
            results = self.student_dal.search(search_term)
            self.current_search_results = results
            self.students = results
            self.selected_student_ids = []  # پاک کردن انتخاب‌های قبلی
            self.result_count_label.setText(f"نتایج جستجو: {len(results)}")
            
            if not results:
                self.table.setRowCount(0)
                QMessageBox.information(self, "نتیجه", "هیچ دانش‌آموزی با این عبارت یافت نشد.")
                return
            
            self.display_students(results)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در جستجو:\n{str(e)}")
    
    def clear_search(self):
        """پاک کردن جستجو و نمایش همه دانش‌آموزان"""
        self.search_input.clear()
        self.current_search_results = []
        self.students = self.all_students.copy()
        self.selected_student_ids = []
        self.result_count_label.setText(f"تعداد کل: {len(self.students)}")
        self.display_students(self.students)
    
    def display_students(self, students):
        """نمایش دانش‌آموزان در جدول"""
        self.table.setRowCount(len(students))
        grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}
        
        for row, student in enumerate(students):
            profile = self.profile_dal.get_active_by_student(student.id)
            
            if profile:
                current_grade = profile.grade
                class_name = profile.class_name or ""
            else:
                # اگر پرونده فعال وجود نداشت، از داده‌های دانش‌آموز استفاده کن
                # یا پایه پیش‌فرض 1
                current_grade = getattr(student, 'grade', 1)
                class_name = getattr(student, 'class_name', "")
            
            # بررسی انتخاب شده بودن
            check_item = QTableWidgetItem("☑" if student.id in self.selected_student_ids else "☐")
            check_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            check_item.setData(Qt.ItemDataRole.UserRole, student.id)
            self.table.setItem(row, 0, check_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(str(row + 1)))
            self.table.setItem(row, 2, QTableWidgetItem(student.full_name))
            self.table.setItem(row, 3, QTableWidgetItem(grade_names.get(current_grade, str(current_grade))))
            
            if current_grade and current_grade < 6:
                new_grade_item = QTableWidgetItem(grade_names.get(current_grade + 1, str(current_grade + 1)))
                new_grade_item.setBackground(QColor(200, 255, 200))
                self.table.setItem(row, 4, new_grade_item)
            else:
                graduate_item = QTableWidgetItem("🎓 فارغ‌التحصیل")
                graduate_item.setBackground(QColor(255, 200, 200))
                self.table.setItem(row, 4, graduate_item)
            
            self.table.setItem(row, 5, QTableWidgetItem(class_name))
            self.table.setRowHeight(row, 35)
    
    def on_item_clicked(self, item):
        """انتخاب/لغو انتخاب دانش‌آموز"""
        row = item.row()
        if row >= len(self.students):
            return
        
        student = self.students[row]
        check_item = self.table.item(row, 0)
        
        if student.id in self.selected_student_ids:
            self.selected_student_ids.remove(student.id)
            check_item.setText("☐")
        else:
            self.selected_student_ids.append(student.id)
            check_item.setText("☑")
    
    def get_selected_students(self):
        """دریافت لیست دانش‌آموزان انتخاب شده"""
        return [s for s in self.students if s.id in self.selected_student_ids]
    
    def _get_or_create_target_year(self, year_title):
        """
        پیدا کردن (یا ساختن) سال تحصیلی مقصد

        ===== اصلاح =====
        نسخه قبلی `self.academic_year_dal.get_active()` را صدا می‌زد،
        یعنی «سال فعال فعلی» — نه سالی که کاربر در کشوی
        `year_input` انتخاب کرده بود. اگر کاربر سال بعد را انتخاب
        می‌کرد و سال فعال هنوز سال جاری بود، همه دانش‌آموزان در همان
        سال جاری ارتقاء می‌خوردند و رکورد تکراری می‌ساختند.

        همچنین اگر سال فعالی وجود نداشت، یک AcademicYear خام ساخته
        می‌شد که start_date و end_date آن None بود و validate() هم
        هیچ‌وقت صدا زده نمی‌شد.
        """
        # ===== اصلاح (بازرسی دوم) =====
        # نسخه قبلی:
        #     try:
        #         existing = self.academic_year_dal.get_by_title(year_title)
        #         ...
        #     except AttributeError:
        #         pass          # «متد در این نسخه DAL وجود ندارد»
        #     for y in (self.academic_year_dal.get_all() or []):  # حلقه جایگزین
        #
        # متد get_by_title واقعاً وجود نداشت، پس همیشه شاخه حلقه اجرا
        # می‌شد. اما get_all() به‌طور پیش‌فرض سال‌های بایگانی‌شده را
        # برنمی‌گرداند ⇒ اگر سال مقصد قبلاً ساخته و بایگانی شده بود،
        # پیدا نمی‌شد و یک سال تحصیلی «تکراری» با همان عنوان ساخته می‌شد.
        #
        # حالا get_by_title در AcademicYearDAL پیاده‌سازی شده (شامل
        # سال‌های بایگانی‌شده) و مستقیم صدا زده می‌شود.
        # ۱) سال با همین عنوان از قبل هست؟
        existing = self.academic_year_dal.get_by_title(year_title)
        if existing:
            return existing

        # ۲) نبود؛ بساز — ولی با تاریخ‌های واقعی و اعتبارسنجی
        from models.academic_year import AcademicYear
        new_year = AcademicYear()
        new_year.title = year_title
        new_year.is_active = 1
        new_year.is_archived = 0

        # تاریخ شروع و پایان از عنوان سال («1405-1406») استخراج می‌شود
        try:
            start_year = int(str(year_title).split('-')[0].strip())
            new_year.start_date = f"{start_year}/07/01"      # اول مهر
            new_year.end_date = f"{start_year + 1}/06/31"    # آخر شهریور
        except (ValueError, IndexError):
            new_year.start_date = None
            new_year.end_date = None

        # اعتبارسنجی قبل از ذخیره (قبلاً هیچ‌وقت صدا زده نمی‌شد)
        if hasattr(new_year, 'validate'):
            errs = new_year.validate()
            if errs:
                raise ValueError(
                    f"سال تحصیلی «{year_title}» معتبر نیست: " + "؛ ".join(errs)
                )

        return self.academic_year_dal.create(new_year)

    def _promote_one_student(self, student, target_year):
        """
        ارتقاء یک دانش‌آموز به سال تحصیلی جدید

        ===== اصلاح مهم =====
        نسخه قبلی پرونده فعال موجود را تغییر می‌داد:
            profile.grade += 1
            profile.academic_year_id = active_year.id
            self.profile_dal.update(profile)

        یعنی همان رکورد پارسال، با همان شناسه، به سال جدید منتقل
        می‌شد. چون همه مشاهده‌ها، مداخله‌ها و پیگیری‌ها به
        profile_id وصل هستند، کل تاریخچه سال گذشته ناگهان به سال
        جدید منتسب می‌شد و گزارش‌های سال قبل خالی می‌ماندند.

        حالا:
          - پرونده پارسال دست‌نخورده می‌ماند و فقط «بسته» می‌شود
          - یک پرونده جدید برای سال جدید ساخته می‌شود
        """
        from models.student_academic_profile import StudentAcademicProfile

        profile = self.profile_dal.get_active_by_student(student.id)

        if not profile:
            # پرونده‌ای ندارد: یک پرونده پایه در سال مقصد بساز.
            # ===== اصلاح =====
            # نسخه قبلی grade = 1 می‌گذاشت. برای دانش‌آموزی که از قبل
            # در سامانه بوده ولی پرونده فعال ندارد، پایه ۱ غلط است.
            # پایه را نمی‌توان حدس زد؛ از آخرین پرونده موجود (حتی
            # غیرفعال) گرفته می‌شود و اگر هیچ‌کدام نبود، کار با خطا
            # متوقف می‌شود تا کاربر خودش پایه را تعیین کند.
            last_grade = None
            # ===== اصلاح (بازرسی دوم) =====
            # نسخه قبلی `self.profile_dal.get_by_student(student.id)` را صدا
            # می‌زد. چنین متدی در StudentAcademicProfileDAL وجود ندارد
            # (متدهای واقعی: get_by_student_and_year، get_active_by_student،
            # get_all_profiles_for_student و ...). نتیجه:
            #
            #     AttributeError → except AttributeError: pass
            #     ⇒ حلقه هرگز اجرا نمی‌شد ⇒ last_grade همیشه None می‌ماند
            #     ⇒ ValueError پایین «همیشه» پرتاب می‌شد
            #
            # یعنی دانش‌آموزی که پرونده فعال ندارد ولی سابقه‌اش در سامانه
            # هست (مثلاً پارسال فارغ‌التحصیل/انتقالی شده) هرگز قابل ارتقاء
            # نبود و کاربر پیام گمراه‌کننده «ابتدا پایه را در فرم دانش‌آموز
            # مشخص کنید» می‌دید — با اینکه پایه در سابقه موجود بود.
            # گارد except AttributeError این خرابی را کاملاً پنهان می‌کرد.
            history = self.profile_dal.get_all_profiles_for_student(student.id) or []

            # ===== اصلاح (بازرسی دوم) — جلوی ثبت‌نام دوباره =====
            # get_active_by_student دیگر پرونده «فارغ‌التحصیل/انصرافی/
            # انتقالی» را برنمی‌گرداند (واژگان مرده 'archived'/'closed'
            # اصلاح شد). بدون این گارد، چنین دانش‌آموزی وارد همین شاخه
            # می‌شد، پایه‌اش از سابقه پیدا می‌شد (مثلاً ۶) و یک پرونده
            # جدید با پایه min(6+1, 6)=6 در سال جدید ساخته می‌شد —
            # یعنی دانش‌آموز فارغ‌التحصیل، بی‌صدا و خودکار، دوباره در
            # پایه ششم ثبت‌نام می‌شد.
            #
            # لیست get_all_profiles_for_student بر اساس شروع سال تحصیلی
            # مرتب است، پس آخرین عنصر = تازه‌ترین پرونده.
            latest = history[-1] if history else None
            if latest is not None:
                st = getattr(latest, 'status', None)
                terminal = (StudentAcademicProfile.STATUS_GRADUATED,
                            StudentAcademicProfile.STATUS_DROPPED,
                            StudentAcademicProfile.STATUS_TRANSFERRED)
                if st in terminal:
                    labels = dict(StudentAcademicProfile.STATUS_CHOICES)
                    raise ValueError(
                        f"پرونده این دانش‌آموز «{labels.get(st, st)}» است و "
                        "ارتقاء داده نمی‌شود. اگر این وضعیت اشتباه است، "
                        "ابتدا پرونده را فعال کنید."
                    )

            for old_profile in history:
                g = getattr(old_profile, 'grade', None)
                if g:
                    last_grade = max(last_grade or 0, g)

            if not last_grade:
                raise ValueError(
                    "پرونده فعالی ندارد و پایه‌ای هم در سابقه یافت نشد؛ "
                    "ابتدا پایه را در فرم دانش‌آموز مشخص کنید."
                )

            new_profile = StudentAcademicProfile()
            new_profile.student_id = student.id
            new_profile.academic_year_id = target_year.id
            new_profile.grade = min(last_grade + 1, 6)
            new_profile.class_name = ""
            new_profile.status = StudentAcademicProfile.STATUS_ACTIVE
            self.profile_dal.create(new_profile)
            return True

        # پرونده از قبل در سال مقصد ساخته شده؟ (جلوگیری از اجرای دوباره)
        # ===== اصلاح (بازرسی دوم) =====
        # این گارد هم دقیقاً به همان متد ناموجود get_by_student تکیه بود:
        #
        #     try:
        #         for existing in (self.profile_dal.get_by_student(student.id) or []):
        #             if existing.academic_year_id == target_year.id:
        #                 return False        # قبلاً ارتقاء یافته
        #     except AttributeError:
        #         pass                        # ← بی‌صدا رد می‌شد
        #
        # یعنی «بررسی اجرای دوباره» هرگز انجام نمی‌شد. نتیجه: اگر کاربر
        # دکمه ارتقاء را دو بار می‌زد (یا همان گروه را دوباره انتخاب
        # می‌کرد)، برای هر دانش‌آموز یک پرونده «تکراری» در همان سال
        # تحصیلی ساخته می‌شد. چون مشاهده‌ها/مداخله‌ها به profile_id وصل
        # هستند، پرونده تکراری یعنی تاریخچه دوپاره و آمار غلط.
        #
        # حالا از متد واقعی و دقیق get_by_student_and_year استفاده می‌شود
        # که خودش هم is_deleted = 0 را در نظر می‌گیرد.
        if self.profile_dal.get_by_student_and_year(student.id, target_year.id):
            return False   # قبلاً ارتقاء یافته؛ دوباره نساز

        current_grade = profile.grade or 1

        if current_grade >= 6:
            # فارغ‌التحصیل: پرونده پارسال بسته می‌شود، پرونده جدیدی
            # ساخته نمی‌شود.
            # ===== اصلاح =====
            # نسخه قبلی status = "closed" می‌گذاشت. این مقدار در
            # STATUS_CHOICES مدل نیست (انتخاب‌ها: active, inactive,
            # graduated, transferred, dropped) و validate() آن را رد
            # می‌کند. enums.StudentProfileStatus.CLOSED هم یک واژگان
            # سوم و موازی است.
            profile.status = StudentAcademicProfile.STATUS_GRADUATED
            self.profile_dal.update(profile)
            return True

        # پرونده جدید برای سال جدید
        new_profile = StudentAcademicProfile()
        new_profile.student_id = student.id
        new_profile.academic_year_id = target_year.id
        new_profile.grade = current_grade + 1
        new_profile.class_name = ""
        new_profile.status = StudentAcademicProfile.STATUS_ACTIVE
        self.profile_dal.create(new_profile)

        # پرونده پارسال بسته می‌شود ولی محتوایش دست‌نخورده می‌ماند
        profile.status = StudentAcademicProfile.STATUS_INACTIVE
        self.profile_dal.update(profile)
        return True

    def promote_all_students(self):
        """ارتقاء همه دانش‌آموزان"""
        if not self.students:
            QMessageBox.warning(self, "توجه", "هیچ دانش‌آموزی وجود ندارد.")
            return
        
        reply = QMessageBox.question(
            self,
            "تأیید ارتقاء همه",
            f"آیا از ارتقاء {len(self.students)} دانش‌آموز اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        next_year = self.year_input.currentText()
        success_count = 0
        errors = []
        
        try:
            # ===== اصلاح =====
            # سال مقصد همان سالی است که کاربر انتخاب کرده، نه
            # «سال فعال فعلی».
            active_year = self._get_or_create_target_year(next_year)
            
            for student in self.students:
                try:
                    if self._promote_one_student(student, active_year):
                        success_count += 1
                except Exception as e:
                    errors.append(f"{student.full_name}: {str(e)}")
            
            msg = f"✅ {success_count} دانش‌آموز با موفقیت ارتقاء یافتند.\nسال تحصیلی جدید: {next_year}"
            if errors:
                msg += f"\n\n⚠️ خطاها:\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    msg += f"\nو {len(errors)-5} خطای دیگر..."
            
            QMessageBox.information(self, "موفقیت", msg)
            self.load_students()
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در ارتقاء:\n{str(e)}")
    
    def promote_selected_students(self):
        """ارتقاء دانش‌آموزان انتخاب شده"""
        selected = self.get_selected_students()
        
        if not selected:
            QMessageBox.warning(self, "توجه", "لطفاً حداقل یک دانش‌آموز را انتخاب کنید.")
            return
        
        reply = QMessageBox.question(
            self,
            "تأیید ارتقاء",
            f"آیا از ارتقاء {len(selected)} دانش‌آموز انتخاب‌شده اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        next_year = self.year_input.currentText()
        success_count = 0
        errors = []
        
        try:
            active_year = self._get_or_create_target_year(next_year)
            
            for student in selected:
                try:
                    if self._promote_one_student(student, active_year):
                        success_count += 1
                except Exception as e:
                    errors.append(f"{student.full_name}: {str(e)}")
            
            msg = f"✅ {success_count} دانش‌آموز با موفقیت ارتقاء یافتند.\nسال تحصیلی جدید: {next_year}"
            if errors:
                msg += f"\n\n⚠️ خطاها:\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    msg += f"\nو {len(errors)-5} خطای دیگر..."
            
            QMessageBox.information(self, "موفقیت", msg)
            self.selected_student_ids = []
            self.load_students()
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در ارتقاء:\n{str(e)}")
    
    def repeat_grade_students(self):
        """تکرار پایه دانش‌آموزان انتخاب شده"""
        selected = self.get_selected_students()
        
        if not selected:
            QMessageBox.warning(self, "توجه", "لطفاً حداقل یک دانش‌آموز را انتخاب کنید.")
            return
        
        reply = QMessageBox.question(
            self,
            "تأیید تکرار پایه",
            f"آیا از تکرار پایه {len(selected)} دانش‌آموز اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        next_year = self.year_input.currentText()
        success_count = 0
        errors = []
        
        try:
            active_year = self._get_or_create_target_year(next_year)
            
            for student in selected:
                try:
                    profile = self.profile_dal.get_active_by_student(student.id)
                    if profile:
                        # پایه را تغییر نمی‌دهیم، فقط سال تحصیلی را به‌روز می‌کنیم
                        profile.academic_year_id = active_year.id
                        self.profile_dal.update(profile)
                        success_count += 1
                    else:
                        from models.student_academic_profile import StudentAcademicProfile
                        new_profile = StudentAcademicProfile()
                        new_profile.student_id = student.id
                        new_profile.academic_year_id = active_year.id
                        new_profile.grade = 1
                        new_profile.class_name = ""
                        new_profile.status = "active"
                        self.profile_dal.create(new_profile)
                        success_count += 1
                except Exception as e:
                    errors.append(f"{student.full_name}: {str(e)}")
            
            msg = f"✅ {success_count} دانش‌آموز با موفقیت تکرار پایه شدند.\nسال تحصیلی آن‌ها به {next_year} تغییر یافت."
            if errors:
                msg += f"\n\n⚠️ خطاها:\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    msg += f"\nو {len(errors)-5} خطای دیگر..."
            
            QMessageBox.information(self, "موفقیت", msg)
            self.selected_student_ids = []
            self.load_students()
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در تکرار پایه:\n{str(e)}")