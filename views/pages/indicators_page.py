"""
صفحه نمایش شاخص‌های رشد (Competencies) - نسخه نهایی با وضعیت "داده ناکافی" و جستجو و فیلتر معلم
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dal.academic_year_dal import AcademicYearDAL
from dal.competency_dal import CompetencyDAL
from dal.observation_dal import ObservationDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from database.connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


class IndicatorsPage(QWidget):
    """صفحه نمایش شاخص‌های رشد با وضعیت "داده ناکافی" و جستجو و فیلتر معلم"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.observation_dal = ObservationDAL()
        self.competency_dal = CompetencyDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.staff_dal = StaffDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        self.db = DatabaseConnection()
        self.current_student_id = None
        self.current_profile_id = None
        self.all_students = []
        self.all_teachers = []
        self.selected_teacher_id = None
        
        self.setup_ui()
        self.load_competencies()
        self.load_teachers()
        self.load_academic_years()
        self.load_students()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        title_label = QLabel("📊 شاخص‌های رشد (شایستگی‌ها)")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #F4C542;
            }
        """)
        toolbar.addWidget(title_label)
        
        toolbar.addStretch()
        
        # ===== انتخاب معلم (جدید) =====
        toolbar.addWidget(QLabel("معلم:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.setMinimumWidth(150)
        self.teacher_combo.addItem("همه معلمان", None)
        self.teacher_combo.currentIndexChanged.connect(self.on_teacher_changed)
        toolbar.addWidget(self.teacher_combo)
        
        # انتخاب دانش‌آموز
        toolbar.addWidget(QLabel("دانش‌آموز:"))
        self.student_combo = QComboBox()
        self.student_combo.setMinimumWidth(200)
        self.student_combo.addItem("انتخاب دانش‌آموز...", None)
        self.student_combo.currentIndexChanged.connect(self.load_student_indicators)
        toolbar.addWidget(self.student_combo)
        
        # انتخاب سال تحصیلی
        toolbar.addWidget(QLabel("سال:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(120)
        self.year_combo.addItem("همه سال‌ها", None)
        self.year_combo.currentIndexChanged.connect(self.on_teacher_changed)
        toolbar.addWidget(self.year_combo)
        
        # دکمه جستجوی دانش‌آموز
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجوی نام یا کد ملی...")
        self.search_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                padding: 5px 10px;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                font-size: 13px;
                min-width: 150px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F;
                border: 2px solid #F4C542;
            }
        """)
        toolbar.addWidget(self.search_input)
        
        self.search_btn = QPushButton("🔍 جستجو")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 5px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #08223A; }
        """)
        self.search_btn.clicked.connect(self.search_student)
        toolbar.addWidget(self.search_btn)
        
        self.clear_search_btn = QPushButton("✖")
        self.clear_search_btn.setFixedSize(30, 30)
        self.clear_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #9E1B1B; }
        """)
        self.clear_search_btn.clicked.connect(self.clear_search)
        toolbar.addWidget(self.clear_search_btn)
        
        layout.addLayout(toolbar)
        
        # ===== پیام "داده ناکافی" =====
        self.insufficient_data_label = QLabel("")
        self.insufficient_data_label.setStyleSheet("""
            QLabel {
                background-color: #C62828;
                color: #C62828;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                border: 1px solid #F4C542;
            }
        """)
        self.insufficient_data_label.setVisible(False)
        layout.addWidget(self.insufficient_data_label)
        
        # ===== بخش اصلی (درخت + توضیحات) =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # درخت شایستگی‌ها
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["شایستگی / شاخص", "امتیاز", "وضعیت"])
        self.tree.setColumnWidth(0, 400)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 120)
        self.tree.setStyleSheet("""
            QTreeWidget {
    color: #F4C542;
    gridline-color: #D9C36A;
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 5px;
            }
            QTreeWidget::item {
    color: #F4C542;
    border-bottom: 1px solid #D9C36A;
    background-color: #0B2E4F;
                padding: 5px;
            }
            QTreeWidget::item:selected {
                background-color: #66BB6A;
                color: #F4C542;
            }
            QTreeWidget::item:hover {
    color: #FFE8A3;
                background-color: #174F78;
            }
        """)
        self.tree.itemClicked.connect(self.show_competency_details)
        splitter.addWidget(self.tree)
        
        # پنل توضیحات
        self.details_panel = QTextEdit()
        self.details_panel.setReadOnly(True)
        self.details_panel.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                padding: 10px;
                font-size: 13px;
            }
        """)
        self.details_panel.setPlaceholderText("برای مشاهده جزئیات، روی هر آیتم کلیک کنید...")
        splitter.addWidget(self.details_panel)
        
        splitter.setSizes([600, 400])
        layout.addWidget(splitter)
        
        # ===== دکمه به‌روزرسانی =====
        refresh_btn = QPushButton("🔄 به‌روزرسانی شاخص‌ها")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #08223A;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_indicators)
        layout.addWidget(refresh_btn)
    
    def load_teachers(self):
        """بارگذاری معلمان در کامبوباکس"""
        try:
            all_staff = self.staff_dal.get_all()
            self.all_teachers = [s for s in all_staff if s.role == "teacher"]
            self.teacher_combo.clear()
            self.teacher_combo.addItem("همه معلمان", None)
            for teacher in self.all_teachers:
                self.teacher_combo.addItem(f"{teacher.full_name}", teacher.id)
        except Exception as e:
            logger.error(f"خطا در بارگذاری معلمان: {e}")
    
    def load_academic_years(self):
        """بارگذاری سال‌های تحصیلی در کامبوباکس"""
        try:
            years = self.academic_year_dal.get_all(include_archived=True)
            self.year_combo.clear()
            self.year_combo.addItem("همه سال‌ها", None)
            for year in years:
                display_text = f"{year.title} {'(بایگانی)' if year.is_archived == 1 else ''}"
                self.year_combo.addItem(display_text, year.id)
            
            # انتخاب سال فعال
            active_year = self.academic_year_dal.get_active()
            if active_year:
                for i in range(self.year_combo.count()):
                    if self.year_combo.itemData(i) == active_year.id:
                        self.year_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            logger.error(f"خطا در بارگذاری سال‌های تحصیلی: {e}")
    
    def on_teacher_changed(self, index):
        """وقتی معلم یا سال تغییر می‌کند، لیست دانش‌آموزان را به‌روز کن"""
        self.selected_teacher_id = self.teacher_combo.currentData()
        self.load_students_for_teacher()
    
    def load_students_for_teacher(self):
        """بارگذاری دانش‌آموزان یک معلم خاص"""
        try:
            self.student_combo.clear()
            self.student_combo.addItem("انتخاب دانش‌آموز...", None)
            
            year_id = self.year_combo.currentData()
            
            if self.selected_teacher_id:
                assignments = self.assignment_dal.get_by_teacher(self.selected_teacher_id, year_id)
                
                for assignment in assignments:
                    student = self.student_dal.get_by_id(assignment.student_id)
                    if student:
                        profile = self.profile_dal.get_active_by_student(student.id)
                        grade_text = profile.grade_display if profile else "نامشخص"
                        display_text = f"{student.full_name} - پایه {grade_text}"
                        self.student_combo.addItem(display_text, student.id)
            else:
                self.all_students = self.student_dal.get_all()
                for student in self.all_students:
                    profile = self.profile_dal.get_active_by_student(student.id)
                    grade_text = profile.grade_display if profile else "نامشخص"
                    display_text = f"{student.full_name} - پایه {grade_text}"
                    self.student_combo.addItem(display_text, student.id)
        except Exception as e:
            logger.error(f"خطا در بارگذاری دانش‌آموزان معلم: {e}")
    
    def load_students(self):
        """بارگذاری دانش‌آموزان در کامبوباکس"""
        try:
            self.all_students = self.student_dal.get_all()
            self.student_combo.clear()
            self.student_combo.addItem("انتخاب دانش‌آموز...", None)
            for student in self.all_students:
                profile = self.profile_dal.get_active_by_student(student.id)
                grade_text = profile.grade_display if profile else "نامشخص"
                display_text = f"{student.full_name} - پایه {grade_text}"
                self.student_combo.addItem(display_text, student.id)
        except Exception as e:
            logger.error(f"خطا در بارگذاری دانش‌آموزان: {e}")
    
    def search_student(self):
        """جستجوی دانش‌آموز و انتخاب در کامبوباکس"""
        search_term = self.search_input.text().strip()
        if not search_term:
            QMessageBox.warning(self, "توجه", "لطفاً عبارت جستجو را وارد کنید.")
            return
        
        try:
            results = self.student_dal.search(search_term)
            if not results:
                QMessageBox.information(self, "نتیجه", "هیچ دانش‌آموزی یافت نشد.")
                return
            
            if len(results) == 1:
                student = results[0]
                for i in range(self.student_combo.count()):
                    if self.student_combo.itemData(i) == student.id:
                        self.student_combo.setCurrentIndex(i)
                        break
            else:
                names = "\n".join([f"• {s.full_name} (کد: {s.national_code or 'ندارد'})" for s in results[:10]])
                msg = f"{len(results)} دانش‌آموز پیدا شد:\n\n{names}\n\nلطفاً از لیست کشویی انتخاب کنید."
                QMessageBox.information(self, "نتیجه جستجو", msg)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در جستجو:\n{e!s}")
    
    def clear_search(self):
        """پاک کردن جستجو و نمایش همه"""
        self.search_input.clear()
        self.student_combo.setCurrentIndex(0)
    
    def load_competencies(self):
        """بارگذاری شایستگی‌ها در درخت"""
        try:
            competencies = self.competency_dal.get_all()
            
            self.tree.clear()
            
            # گروه‌بندی بر اساس دسته
            categories = {}
            for comp in competencies:
                category = comp.category or "other"
                if category not in categories:
                    categories[category] = []
                categories[category].append(comp)
            
            category_map = {
                "emotional": "عاطفی-هیجانی",
                "social": "اجتماعی",
                "educational": "آموزشی",
                "moral": "اخلاقی",
                "self_management": "خودمدیریتی",
                "participation": "مشارکت",
                "other": "سایر"
            }
            
            for category, comps in categories.items():
                cat_display = category_map.get(category, category)
                category_item = QTreeWidgetItem(self.tree)
                category_item.setText(0, f"📁 {cat_display}")
                category_item.setData(0, Qt.ItemDataRole.UserRole, "category")
                category_item.setExpanded(True)
                
                for comp in comps:
                    comp_item = QTreeWidgetItem(category_item)
                    comp_item.setText(0, f"📌 {comp.title}")
                    comp_item.setData(0, Qt.ItemDataRole.UserRole, "competency")
                    comp_item.setData(1, Qt.ItemDataRole.UserRole, comp.id)
                    
                    # تنظیم امتیاز و وضعیت (پیش‌فرض - داده ناکافی)
                    comp_item.setText(1, "❓")
                    comp_item.setText(2, "⚠️ داده ناکافی")
                    comp_item.setData(2, Qt.ItemDataRole.UserRole, -1)  # -1 یعنی داده ناکافی
                    comp_item.setForeground(2, QColor(241, 196, 15))
            
            logger.debug(f"✅ {len(competencies)} شایستگی بارگذاری شد")
            
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری شایستگی‌ها: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری شایستگی‌ها:\n{e!s}")
    
    def _get_category_display(self, category):
        """نمایش نام دسته به فارسی"""
        category_map = {
            "emotional": "عاطفی-هیجانی",
            "social": "اجتماعی",
            "educational": "آموزشی",
            "moral": "اخلاقی",
            "self_management": "خودمدیریتی",
            "participation": "مشارکت",
            "other": "سایر"
        }
        return category_map.get(category, category)
    
    def load_student_indicators(self):
        """بارگذاری شاخص‌های دانش‌آموز انتخاب شده با فیلتر معلم و سال"""
        student_id = self.student_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        year_id = self.year_combo.currentData()
        
        if student_id is None:
            self.clear_scores()
            self.details_panel.setText("⚠️ لطفاً یک دانش‌آموز را انتخاب کنید.")
            self.insufficient_data_label.setVisible(False)
            return
        
        self.current_student_id = student_id
        
        # دریافت پرونده دانش‌آموز (با توجه به سال انتخاب شده)
        if year_id:
            profile = self.profile_dal.get_by_student_and_year(student_id, year_id)
        else:
            profile = self.profile_dal.get_active_by_student(student_id)
        
        if not profile:
            self.clear_scores()
            self.details_panel.setText("⚠️ هیچ پرونده‌ای برای این دانش‌آموز در سال انتخاب شده وجود ندارد.")
            self.insufficient_data_label.setVisible(True)
            self.insufficient_data_label.setText("⚠️ پرونده‌ای برای این دانش‌آموز در سال انتخاب شده وجود ندارد.")
            return
        
        self.current_profile_id = profile.id
        
        # دریافت مشاهدات با فیلتر معلم
        observations = self.observation_dal.get_by_student_profile(profile.id)
        
        # فیلتر بر اساس معلم (اگر انتخاب شده باشد)
        if teacher_id:
            observations = [obs for obs in observations if obs.staff_id == teacher_id]
        
        if len(observations) < 2:
            self.clear_scores()
            self.details_panel.setText(
                f"⚠️ داده کافی برای تحلیل شاخص‌ها وجود ندارد.\n"
                f"تعداد مشاهدات ثبت‌شده: {len(observations)} (حداقل ۲ مورد نیاز است)"
            )
            self.insufficient_data_label.setVisible(True)
            self.insufficient_data_label.setText(
                f"⚠️ داده کافی برای تحلیل شاخص‌ها وجود ندارد. "
                f"تعداد مشاهدات ثبت‌شده: {len(observations)} (حداقل ۲ مورد نیاز است)"
            )
            return
        
        self.insufficient_data_label.setVisible(False)
        self.calculate_indicators(profile.id, observations)
    
    def calculate_indicators(self, profile_id, observations=None):
        """محاسبه امتیاز شایستگی‌ها بر اساس مشاهدات"""
        try:
            if observations is None:
                observations = self.observation_dal.get_by_student_profile(profile_id)
            
            if not observations:
                self.clear_scores()
                self.details_panel.setText("⚠️ هیچ مشاهده‌ای برای این دانش‌آموز ثبت نشده است.")
                return
            
            # دریافت همه شایستگی‌ها
            competencies = self.competency_dal.get_all()
            
            # پیمایش درخت و به‌روزرسانی امتیازها
            self.update_tree_scores(competencies, observations)
            
            logger.debug("✅ امتیاز شایستگی‌ها برای دانش‌آموز محاسبه شد")
            
        except Exception as e:
            logger.error(f"❌ خطا در محاسبه شایستگی‌ها: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در محاسبه شایستگی‌ها:\n{e!s}")
    
    def update_tree_scores(self, competencies, observations):
        """به‌روزرسانی امتیازها در درخت با وضعیت "داده ناکافی" """
        root = self.tree.invisibleRootItem()
        
        # ایجاد دیکشنری برای دسترسی سریع
        comp_scores = {}
        for obs in observations:
            if obs.competency_id:
                if obs.competency_id not in comp_scores:
                    comp_scores[obs.competency_id] = {
                        'count': 0,
                        'total': 0
                    }
                comp_scores[obs.competency_id]['count'] += 1
                comp_scores[obs.competency_id]['total'] += obs.severity or 1
        
        # پیمایش درخت
        for i in range(root.childCount()):
            category_item = root.child(i)
            
            for j in range(category_item.childCount()):
                comp_item = category_item.child(j)
                comp_id = comp_item.data(1, Qt.ItemDataRole.UserRole)
                
                if comp_id in comp_scores:
                    data = comp_scores[comp_id]
                    count = data['count']
                    score = round(data['total'] / count, 1) if count > 0 else 0
                    
                    comp_item.setText(1, f"{score} ({count} obs)")
                    comp_item.setData(2, Qt.ItemDataRole.UserRole, score)
                    
                    # تنظیم وضعیت
                    if count < 2:
                        # داده ناکافی برای این شایستگی خاص
                        comp_item.setText(2, "⚠️ داده ناکافی")
                        comp_item.setForeground(2, QColor(241, 196, 15))
                    elif score >= 4:
                        comp_item.setText(2, "✅ عالی")
                        comp_item.setForeground(2, QColor(0, 128, 0))
                    elif score >= 3:
                        comp_item.setText(2, "🟡 خوب")
                        comp_item.setForeground(2, QColor(255, 165, 0))
                    elif score >= 2:
                        comp_item.setText(2, "🟠 متوسط")
                        comp_item.setForeground(2, QColor(255, 140, 0))
                    elif score > 0:
                        comp_item.setText(2, "🔴 نیاز به توجه")
                        comp_item.setForeground(2, QColor(255, 0, 0))
                    else:
                        comp_item.setText(2, "❌ ثبت نشده")
                        comp_item.setForeground(2, QColor(128, 128, 128))
                else:
                    comp_item.setText(1, "❓")
                    comp_item.setText(2, "⚠️ داده ناکافی")
                    comp_item.setData(2, Qt.ItemDataRole.UserRole, -1)
                    comp_item.setForeground(2, QColor(241, 196, 15))
    
    def clear_scores(self):
        """پاک کردن امتیازها و نمایش وضعیت "داده ناکافی" """
        root = self.tree.invisibleRootItem()
        
        for i in range(root.childCount()):
            category_item = root.child(i)
            
            for j in range(category_item.childCount()):
                comp_item = category_item.child(j)
                comp_item.setText(1, "❓")
                comp_item.setText(2, "⚠️ داده ناکافی")
                comp_item.setData(2, Qt.ItemDataRole.UserRole, -1)
                comp_item.setForeground(2, QColor(241, 196, 15))
    
    def show_competency_details(self, item, column):
        """نمایش جزئیات شایستگی با در نظر گرفتن وضعیت "داده ناکافی" """
        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        
        if item_type == "category":
            category_name = item.text(0).replace("📁 ", "")
            self.details_panel.setText(f"""
            📂 دسته: {category_name}
            
            این دسته شامل شایستگی‌های مختلفی است.
            
            برای مشاهده جزئیات هر شایستگی، روی آن کلیک کنید.
            """)
            
        elif item_type == "competency":
            comp_name = item.text(0).replace("📌 ", "")
            comp_id = item.data(1, Qt.ItemDataRole.UserRole)
            score = item.data(2, Qt.ItemDataRole.UserRole) or -1
            status_text = item.text(2)
            
            # دریافت اطلاعات از دیتابیس
            competency = self.competency_dal.get_by_id(comp_id)
            description = competency.description if competency else "توضیحاتی ثبت نشده است."
            category = competency.category if competency else "سایر"
            
            self.details_panel.setText(f"""
            📊 شایستگی: {comp_name}
            
            📂 دسته: {self._get_category_display(category)}
            
            📝 توضیحات:
            {description}
            
            ⭐ امتیاز: {score if score >= 0 else 'داده ناکافی'}
            📈 وضعیت: {status_text}
            
            💡 پیشنهاد:
            {self.get_suggestion(score, status_text)}
            """)
    
    def get_suggestion(self, score, status_text):
        """گرفتن پیشنهاد بر اساس امتیاز و وضعیت"""
        if score == -1 or "داده ناکافی" in status_text:
            return "⚠️ داده کافی برای تحلیل این شایستگی وجود ندارد. برای تحلیل دقیق‌تر، حداقل ۲ مشاهده مرتبط ثبت کنید."
        elif score >= 4:
            return "✅ این شایستگی در وضعیت عالی قرار دارد. ادامه دهید."
        elif score >= 3:
            return "🟡 این شایستگی در وضعیت خوبی است. با تمرین بیشتر می‌توانید آن را به عالی برسانید."
        elif score >= 2:
            return "🟠 این شایستگی نیاز به توجه بیشتری دارد. تمرین‌های هدفمند می‌تواند کمک‌کننده باشد."
        elif score > 0:
            return "🔴 این شایستگی نیاز به حمایت و تمرین ویژه دارد. با مشاور مدرسه هماهنگ کنید."
        else:
            return "❌ هنوز مشاهده‌ای برای این شایستگی ثبت نشده است. لطفاً مشاهدات مرتبط را ثبت کنید."
    
    def refresh_indicators(self):
        """به‌روزرسانی شاخص‌ها"""
        if self.current_profile_id:
            self.calculate_indicators(self.current_profile_id)
            QMessageBox.information(self, "موفقیت", "شاخص‌ها با موفقیت به‌روزرسانی شدند")
        else:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا یک دانش‌آموز را انتخاب کنید.")