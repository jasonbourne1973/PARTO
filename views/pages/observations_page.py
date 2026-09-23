"""
صفحه ثبت و مدیریت مشاهدات با نمایش مدل ABC و StudentFile - با فیلتر معلم و جستجوی پیشرفته
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dal.competency_dal import CompetencyDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.academic_year_dal import AcademicYearDAL
from dal.student_dal import StudentDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from database.connection import DatabaseConnection
from services.observation_service import ObservationService
from utils.logger import get_logger
from views.dialogs.observation_form import ObservationForm


class ObservationsPage(QWidget):
    """صفحه مدیریت مشاهدات با نمایش ABC و StudentFile و فیلتر معلم و جستجوی پیشرفته"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.observation_service = ObservationService()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.competency_dal = CompetencyDAL()
        self.staff_dal = StaffDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        self.db = DatabaseConnection()
        self.logger = get_logger(self.__class__.__name__)
        
        self.observations = []
        self.all_students = []
        self.all_teachers = []
        self.selected_teacher_id = None
        
        self.setup_ui()
        self.load_teachers()
        self.load_students_filter()
        self.load_observations()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== نوار ابزار اصلی =====
        toolbar = QHBoxLayout()
        
        title_label = QLabel("📝 ثبت مشاهدات (مدل ABC)")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        toolbar.addWidget(title_label)
        toolbar.addStretch()
        
        # انتخاب معلم
        toolbar.addWidget(QLabel("معلم:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.setMinimumWidth(150)
        self.teacher_combo.addItem("همه معلمان", None)
        self.teacher_combo.currentIndexChanged.connect(self.on_teacher_changed)
        toolbar.addWidget(self.teacher_combo)
        
        # فیلتر دانش‌آموز
        toolbar.addWidget(QLabel("دانش‌آموز:"))
        self.student_filter_combo = QComboBox()
        self.student_filter_combo.setMinimumWidth(200)
        self.student_filter_combo.addItem("📋 همه دانش‌آموزان", None)
        self.student_filter_combo.currentIndexChanged.connect(self.filter_observations)
        toolbar.addWidget(self.student_filter_combo)
        
        # جستجوی ساده
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجوی متن در مشاهدات...")
        self.search_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                padding: 5px 10px;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                font-size: 13px;
                min-width: 180px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F;
                border: 2px solid #F4C542;
            }
        """)
        self.search_input.returnPressed.connect(self.apply_advanced_search)
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
        self.search_btn.clicked.connect(self.apply_advanced_search)
        toolbar.addWidget(self.search_btn)
        
        # دکمه جستجوی پیشرفته
        self.advanced_search_btn = QPushButton("⚙️ پیشرفته")
        self.advanced_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 5px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #66BB6A; }
        """)
        self.advanced_search_btn.clicked.connect(self.toggle_advanced_search)
        toolbar.addWidget(self.advanced_search_btn)
        
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
        
        self.add_btn = QPushButton("➕ ثبت مشاهده جدید")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #66BB6A; }
        """)
        self.add_btn.clicked.connect(self.add_observation)
        toolbar.addWidget(self.add_btn)
        
        layout.addLayout(toolbar)
        
        # ===== پنل جستجوی پیشرفته =====
        self.advanced_panel = QGroupBox("🔍 جستجوی پیشرفته")
        self.advanced_panel.setStyleSheet("""
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
        """)
        self.advanced_panel.setVisible(False)
        
        advanced_layout = QHBoxLayout()
        advanced_layout.setSpacing(10)
        
        # نوع رفتار
        advanced_layout.addWidget(QLabel("نوع:"))
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItem("همه", None)
        self.filter_type_combo.addItem("✅ مثبت", "مثبت")
        self.filter_type_combo.addItem("❌ منفی", "منفی")
        self.filter_type_combo.addItem("⬜ خنثی", "خنثی")
        advanced_layout.addWidget(self.filter_type_combo)
        
        # محیط
        advanced_layout.addWidget(QLabel("محیط:"))
        self.filter_location_combo = QComboBox()
        self.filter_location_combo.addItem("همه", None)
        from config.settings import OBSERVATION_LOCATIONS
        for loc in OBSERVATION_LOCATIONS:
            self.filter_location_combo.addItem(loc)
        advanced_layout.addWidget(self.filter_location_combo)
        
        # شدت
        advanced_layout.addWidget(QLabel("شدت از:"))
        self.filter_severity_min = QComboBox()
        for i in range(1, 6):
            self.filter_severity_min.addItem(str(i), i)
        self.filter_severity_min.setCurrentIndex(0)
        advanced_layout.addWidget(self.filter_severity_min)
        
        advanced_layout.addWidget(QLabel("تا:"))
        self.filter_severity_max = QComboBox()
        for i in range(1, 6):
            self.filter_severity_max.addItem(str(i), i)
        self.filter_severity_max.setCurrentIndex(4)
        advanced_layout.addWidget(self.filter_severity_max)
        
        # دکمه اعمال فیلتر
        self.apply_filter_btn = QPushButton("✅ اعمال فیلتر")
        self.apply_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 5px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.apply_filter_btn.clicked.connect(self.apply_advanced_search)
        advanced_layout.addWidget(self.apply_filter_btn)
        
        self.clear_filters_btn = QPushButton("🗑️ پاک کردن فیلترها")
        self.clear_filters_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 5px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #D94B4B; }
        """)
        self.clear_filters_btn.clicked.connect(self.clear_filters)
        advanced_layout.addWidget(self.clear_filters_btn)
        
        advanced_layout.addStretch()
        self.advanced_panel.setLayout(advanced_layout)
        layout.addWidget(self.advanced_panel)
        
        # ===== جدول نتایج =====
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ردیف", "دانش‌آموز", "تاریخ", "محیط",
            "شایستگی", "نوع", "شدت", "عملیات"
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
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.table)
    
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
            self.logger.error(f"خطا در بارگذاری معلمان: {e}")
    
    def on_teacher_changed(self, index):
        """وقتی معلم تغییر می‌کند، لیست دانش‌آموزان و مشاهدات را فیلتر کن"""
        self.selected_teacher_id = self.teacher_combo.currentData()
        self.load_students_filter()
        self.filter_observations()
    
    def load_students_filter(self):
        """بارگذاری دانش‌آموزان در کامبوباکس با فیلتر معلم"""
        try:
            while self.student_filter_combo.count() > 1:
                self.student_filter_combo.removeItem(1)
            
            if self.selected_teacher_id:
                assignments = self.assignment_dal.get_by_teacher(self.selected_teacher_id)
                student_ids = [a.student_id for a in assignments if a.is_active == 1]
                # خوانش دسته‌ای (رفع N+1)؛ همان خروجی قبلی: شناسهٔ ناموجود → None
                student_map = self.student_dal.get_by_ids(student_ids)
                self.all_students = [student_map.get(sid) for sid in student_ids if sid]
            else:
                self.all_students = self.student_dal.get_all()
            
            for student in self.all_students:
                if student:
                    display_text = f"{student.full_name}"
                    self.student_filter_combo.addItem(display_text, student.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری فیلتر: {e}")
    
    def toggle_advanced_search(self):
        """نمایش/مخفی کردن پنل جستجوی پیشرفته"""
        self.advanced_panel.setVisible(not self.advanced_panel.isVisible())
    
    def clear_filters(self):
        """پاک کردن تمام فیلترها"""
        self.filter_type_combo.setCurrentIndex(0)
        self.filter_location_combo.setCurrentIndex(0)
        self.filter_severity_min.setCurrentIndex(0)
        self.filter_severity_max.setCurrentIndex(4)
        self.search_input.clear()
        self.apply_advanced_search()
    
    def apply_advanced_search(self):
        """اعمال جستجوی پیشرفته"""
        student_id = self.student_filter_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        search_text = self.search_input.text().strip()
        
        # دریافت فیلترها
        behavior_type = self.filter_type_combo.currentData()
        location = self.filter_location_combo.currentText()
        if location == "همه":
            location = None
        severity_min = self.filter_severity_min.currentData()
        severity_max = self.filter_severity_max.currentData()
        
        try:
            # اگر جستجوی متنی وجود دارد
            if search_text:
                # جستجو در سرویس
                if student_id:
                    observations = self.observation_service.search_observations_by_student(
                        student_id, search_text
                    )
                elif teacher_id:
                    observations = self.observation_service.search_observations_by_teacher(
                        teacher_id, search_text
                    )
                else:
                    observations = self.observation_service.search_observations(search_text)
            else:
                # فیلتر معمولی
                if student_id:
                    observations = self.observation_service.get_observations_by_student(student_id)
                elif teacher_id:
                    observations = self.observation_service.get_observations_by_teacher(teacher_id)
                else:
                    observations = self.observation_service.get_all_observations(include_staff_info=True)
            
            # اعمال فیلترهای اضافی
            if behavior_type:
                observations = [o for o in observations if o.behavior_type == behavior_type]
            
            if location:
                observations = [o for o in observations if o.location == location]
            
            if severity_min is not None:
                observations = [o for o in observations if o.severity >= severity_min]
            
            if severity_max is not None:
                observations = [o for o in observations if o.severity <= severity_max]
            
            # فیلتر اضافی بر اساس معلم (اگر هر دو فیلتر فعال باشند)
            if student_id and teacher_id:
                observations = [o for o in observations if o.staff_id == teacher_id]
            
            active_year = self.academic_year_dal.get_active()
            if active_year:
                profiles = self.profile_dal.get_by_ids(o.student_profile_id for o in observations)
                observations = [
                    o for o in observations
                    if profiles.get(o.student_profile_id)
                    and profiles[o.student_profile_id].academic_year_id == active_year.id
                ]
            self.observations = observations
            self.display_observations(self.observations)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در جستجو:\n{e!s}")
    
    def clear_search(self):
        """پاک کردن جستجو و نمایش همه"""
        self.search_input.clear()
        self.filter_type_combo.setCurrentIndex(0)
        self.filter_location_combo.setCurrentIndex(0)
        self.filter_severity_min.setCurrentIndex(0)
        self.filter_severity_max.setCurrentIndex(4)
        self.advanced_panel.setVisible(False)
        self.student_filter_combo.setCurrentIndex(0)
        self.load_observations()
    
    def load_observations(self):
        """بارگذاری مشاهدات با استفاده از سرویس"""
        try:
            self.observations = self.observation_service.get_all_observations(limit=100, include_staff_info=True)
            self.display_observations(self.observations)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری مشاهدات:\n{e!s}")
    
    def filter_observations(self):
        """فیلتر مشاهدات بر اساس دانش‌آموز و معلم"""
        # از متد apply_advanced_search استفاده کن
        self.apply_advanced_search()
    
    def get_competency_name(self, competency_id):
        """دریافت نام شایستگی از شناسه"""
        if not competency_id:
            return "نامشخص"
        try:
            competency = self.competency_dal.get_by_id(competency_id)
            return competency.title if competency else "نامشخص"
        except Exception:
            return "نامشخص"
    
    def get_abc_preview(self, obs):
        """دریافت پیش‌نمایش مدل ABC"""
        parts = []
        if obs.antecedent:
            parts.append(f"زمینه: {obs.antecedent[:30]}...")
        if obs.behavior:
            parts.append(f"رفتار: {obs.behavior[:30]}...")
        if obs.consequence:
            parts.append(f"پیامد: {obs.consequence[:30]}...")
        
        if parts:
            return " | ".join(parts)
        return "ABC ثبت نشده"
    
    def display_observations(self, observations):
        """نمایش مشاهدات در جدول"""
        self.table.setRowCount(len(observations))
        
        for row, obs in enumerate(observations):
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            student_name = getattr(obs, 'student_name', 'نامشخص')
            item = QTableWidgetItem(student_name)
            item.setToolTip(f"پرونده: {obs.student_profile_id}")
            self.table.setItem(row, 1, item)
            
            self.table.setItem(row, 2, QTableWidgetItem(obs.observation_date or ""))
            self.table.setItem(row, 3, QTableWidgetItem(obs.location or ""))
            
            competency_name = getattr(obs, 'competency_title', 'نامشخص')
            if competency_name == 'نامشخص':
                competency_name = self.get_competency_name(obs.competency_id)
            
            comp_item = QTableWidgetItem(competency_name)
            if competency_name != "نامشخص":
                comp_item.setBackground(QColor(230, 240, 255))
            comp_item.setToolTip(self.get_abc_preview(obs))
            self.table.setItem(row, 4, comp_item)
            
            type_item = QTableWidgetItem(obs.behavior_type or "نامشخص")
            if obs.behavior_type == "مثبت":
                type_item.setBackground(Qt.GlobalColor.green)
                type_item.setForeground(Qt.GlobalColor.black)
            elif obs.behavior_type == "منفی":
                type_item.setBackground(Qt.GlobalColor.red)
                type_item.setForeground(Qt.GlobalColor.black)
            self.table.setItem(row, 5, type_item)
            
            self.table.setItem(row, 6, QTableWidgetItem("⭐" * obs.severity))
            
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            view_btn = QPushButton("👁️")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("background-color: #0B2E4F; color: #F4C542; border: none; border-radius: 4px;")
            view_btn.clicked.connect(lambda checked, o=obs: self.view_observation(o))
            btn_layout.addWidget(view_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 4px;")
            delete_btn.clicked.connect(lambda checked, o=obs: self.delete_observation(o))
            btn_layout.addWidget(delete_btn)
            
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 7, btn_widget)
            self.table.setRowHeight(row, 40)
    
    def add_observation(self):
        """افزودن مشاهده جدید با استفاده از سرویس"""
        form = ObservationForm(parent=self)
        if form.exec() == QDialog.DialogCode.Accepted:
            self.filter_observations()
            QMessageBox.information(self, "موفقیت", "مشاهده با موفقیت ثبت شد")
    
    def view_observation(self, obs):
        """نمایش جزئیات مشاهده"""
        student_name = getattr(obs, 'student_name', 'نامشخص')
        competency_name = getattr(obs, 'competency_title', 'نامشخص')
        staff_name = getattr(obs, 'staff_name', 'نامشخص')
        
        detail_text = f"""
👤 دانش‌آموز: {student_name}
📅 تاریخ: {obs.observation_date}
📍 محیط: {obs.location}
📊 شایستگی: {competency_name}
👤 مشاهده‌گر: {staff_name}
🏷️ نوع: {obs.behavior_type}
⭐ شدت: {obs.severity_display}

━━━━━━━━━━ مدل ABC ━━━━━━━━━━

🔴 A - زمینه (Antecedent):
{obs.antecedent or 'ثبت نشده'}

🟡 B - رفتار (Behavior):
{obs.behavior or 'ثبت نشده'}

🟢 C - پیامد (Consequence):
{obs.consequence or 'ثبت نشده'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 توضیحات تکمیلی:
{obs.description or 'ندارد'}

🏷️ برچسب‌ها: {obs.tags or 'ندارد'}
"""
        
        QMessageBox.information(self, "جزئیات مشاهده (مدل ABC)", detail_text)
    
    def delete_observation(self, obs):
        """حذف مشاهده با استفاده از سرویس"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            "آیا از حذف این مشاهده اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted = self.observation_service.delete_observation(obs.id)
                self.filter_observations()
                if deleted:
                    QMessageBox.information(
                        self, "موفقیت", "مشاهده با موفقیت حذف شد"
                    )
                else:
                    QMessageBox.warning(self, "خطا", "مشاهده حذف نشد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{e!s}")
    
    def on_item_double_clicked(self, item):
        """ویرایش مشاهده با دابل کلیک"""
        row = item.row()
        if row < len(self.observations):
            obs = self.observations[row]
            self.edit_observation(obs)
    
    def keyPressEvent(self, event):
        """ویرایش با کلید Enter"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current_row = self.table.currentRow()
            if current_row >= 0 and current_row < len(self.observations):
                self.edit_observation(self.observations[current_row])
        super().keyPressEvent(event)
    
    def edit_observation(self, obs):
        """ویرایش مشاهده با استفاده از فرم"""
        from views.dialogs.observation_form import ObservationForm
        form = ObservationForm(observation_id=obs.id, parent=self)
        form.observation_saved.connect(self.filter_observations)
        form.exec()