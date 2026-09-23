"""
صفحه مدیریت فعالیت‌های فوق‌برنامه
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

undefined
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.extracurricular_activity import ExtracurricularActivity
from services.extracurricular_service import ExtracurricularService
from utils.logger import get_logger
from views.dialogs.activity_form import ActivityForm


class ActivitiesPage(QWidget):
    """صفحه مدیریت فعالیت‌های فوق‌برنامه"""
    
    student_selected = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.extracurricular_service = ExtracurricularService()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.logger = get_logger(self.__class__.__name__)
        
        self.activities = []
        self.visible_activities = []
        self.all_students = []
        
        self.setup_ui()
        self.load_students()
        self.load_activities()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        title_label = QLabel("🎯 مدیریت فعالیت‌های فوق‌برنامه")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        toolbar.addWidget(title_label)
        toolbar.addStretch()
        
        # فیلتر نوع فعالیت
        toolbar.addWidget(QLabel("نوع:"))
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.setMinimumWidth(120)
        self.type_filter_combo.addItem("همه", None)
        for value, display in ExtracurricularActivity.TYPE_CHOICES:
            self.type_filter_combo.addItem(display, value)
        self.type_filter_combo.currentIndexChanged.connect(self.filter_activities)
        toolbar.addWidget(self.type_filter_combo)
        
        # فیلتر وضعیت
        toolbar.addWidget(QLabel("وضعیت:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItem("همه", None)
        for value, display in ExtracurricularActivity.STATUS_CHOICES:
            self.status_filter_combo.addItem(display, value)
        self.status_filter_combo.currentIndexChanged.connect(self.filter_activities)
        toolbar.addWidget(self.status_filter_combo)
        
        toolbar.addSpacing(10)
        
        self.add_btn = QPushButton("➕ ثبت فعالیت جدید")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.add_btn.clicked.connect(self.add_activity)
        toolbar.addWidget(self.add_btn)

        # (بازرسی شانزدهم) سیگنال student_selected تعریف و در پنجرهٔ اصلی
        # متصل بود ولی این صفحه هیچ‌جا آن را emit نمی‌کرد؛ همان دکمهٔ
        # صفحه‌های اهداف و مشاوره این‌جا هم اضافه شد.
        self.view_profile_btn = QPushButton("👤 مشاهده پرونده دانش‌آموز")
        self.view_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #08223A; }
        """)
        self.view_profile_btn.clicked.connect(self.view_student_profile)
        toolbar.addWidget(self.view_profile_btn)
        
        layout.addLayout(toolbar)
        
        # ===== بخش اصلی: جدول فعالیت‌ها =====
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ردیف", "دانش‌آموز", "عنوان", "نوع", "تاریخ شروع", "تاریخ پایان", "وضعیت", "عملیات"
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
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.table)
    
    def load_students(self):
        """بارگذاری دانش‌آموزان"""
        try:
            self.all_students = self.student_dal.get_all()
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری دانش‌آموزان: {e}")
    
    def load_activities(self):
        """بارگذاری فعالیت‌ها"""
        try:
            self.activities = self.extracurricular_service.get_all_activities()
            active_year = self.academic_year_dal.get_active()
            if active_year:
                profiles = self.profile_dal.get_by_ids([a.student_profile_id for a in self.activities if a.student_profile_id])
                valid_profile_ids = {pid for pid, p in profiles.items() if p and p.academic_year_id == active_year.id}
                self.activities = [a for a in self.activities if a.student_profile_id in valid_profile_ids]
            self.display_activities(self.activities)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری فعالیت‌ها:\n{e!s}")
    
    def filter_activities(self):
        """فیلتر فعالیت‌ها"""
        activity_type = self.type_filter_combo.currentData()
        status = self.status_filter_combo.currentData()
        
        filtered = self.activities
        
        if activity_type:
            filtered = [a for a in filtered if a.type == activity_type]
        
        if status:
            filtered = [a for a in filtered if a.status == status]
        
        self.display_activities(filtered)
    
    def display_activities(self, activities):
        """نمایش فعالیت‌ها در جدول"""
        # (بازرسی شانزدهم) فهرستِ نمایش‌داده‌شده جدا نگه داشته می‌شود؛ قبلاً
        # دابل‌کلیک با فیلتر فعال، ردیف را در فهرست «فیلترنشده» جست‌وجو می‌کرد
        # و فعالیت اشتباهی برای ویرایش باز می‌شد.
        self.visible_activities = list(activities or [])
        self.table.setRowCount(len(self.visible_activities))
        
        for row, activity in enumerate(activities):
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            student_name = getattr(activity, 'student_name', 'نامشخص')
            self.table.setItem(row, 1, QTableWidgetItem(student_name))
            
            self.table.setItem(row, 2, QTableWidgetItem(activity.title or ""))
            self.table.setItem(row, 3, QTableWidgetItem(activity.type_display))
            self.table.setItem(row, 4, QTableWidgetItem(activity.start_date or ""))
            self.table.setItem(row, 5, QTableWidgetItem(activity.end_date or ""))
            
            status_item = QTableWidgetItem(activity.status_display)
            if activity.status == ExtracurricularActivity.STATUS_COMPLETED:
                status_item.setBackground(QColor(200, 255, 200))
            elif activity.status == ExtracurricularActivity.STATUS_IN_PROGRESS:
                status_item.setBackground(QColor(200, 230, 255))
            elif activity.status == ExtracurricularActivity.STATUS_PLANNED:
                status_item.setBackground(QColor(255, 255, 200))
            else:
                status_item.setBackground(QColor(255, 200, 200))
            self.table.setItem(row, 6, status_item)
            
            # دکمه‌های عملیات
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            view_btn = QPushButton("👁️")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("background-color: #0B2E4F; color: #F4C542; border: none; border-radius: 4px;")
            view_btn.clicked.connect(lambda checked, a=activity: self.view_activity(a))
            btn_layout.addWidget(view_btn)
            
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setStyleSheet("background-color: #F4D35E; color: #111111; border: none; border-radius: 4px;")
            edit_btn.clicked.connect(lambda checked, a=activity: self.edit_activity(a))
            btn_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 4px;")
            delete_btn.clicked.connect(lambda checked, a=activity: self.delete_activity(a))
            btn_layout.addWidget(delete_btn)
            
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 7, btn_widget)
            self.table.setRowHeight(row, 40)
    
    def view_student_profile(self):
        """مشاهده پرونده دانش‌آموزِ فعالیت انتخاب‌شده (از طریق پنجرهٔ اصلی)"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "توجه", "لطفاً یک فعالیت را انتخاب کنید.")
            return
        visible = getattr(self, 'visible_activities', None) or self.activities
        if row >= len(visible):
            QMessageBox.warning(self, "توجه", "فعالیت انتخاب‌شده معتبر نیست.")
            return
        profile_id = getattr(visible[row], 'student_profile_id', None)
        if profile_id:
            self.student_selected.emit(profile_id)
        else:
            QMessageBox.warning(self, "توجه", "پرونده دانش‌آموز یافت نشد.")

    def on_item_double_clicked(self, item):
        """ویرایش فعالیت با دابل کلیک (روی همان فهرست نمایش‌داده‌شده)"""
        row = item.row()
        visible = getattr(self, 'visible_activities', None) or self.activities
        if 0 <= row < len(visible):
            self.edit_activity(visible[row])
    
    def add_activity(self):
        """افزودن فعالیت جدید"""
        form = ActivityForm(parent=self)
        form.exec()
    
    def edit_activity(self, activity):
        """ویرایش فعالیت"""
        form = ActivityForm(activity_id=activity.id, parent=self)
        form.activity_saved.connect(self.load_activities)
        form.exec()
    
    def view_activity(self, activity):
        """نمایش جزئیات فعالیت"""
        details = f"""
🎯 **جزئیات فعالیت**

👤 دانش‌آموز: {getattr(activity, 'student_name', 'نامشخص')}
📝 عنوان: {activity.title}
🏷️ نوع: {activity.type_display}
📅 تاریخ شروع: {activity.start_date}
📅 تاریخ پایان: {activity.end_date or 'ثبت نشده'}
⏱️ مدت: {activity.duration_hours or 0} ساعت
📍 مکان: {activity.location or 'ثبت نشده'}
📊 سطح مشارکت: {activity.level_display}
🎭 نقش: {activity.role or 'ثبت نشده'}
🏆 تیم: {activity.team_name or 'ثبت نشده'}
📌 وضعیت: {activity.status_display}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 **توضیحات:**
{activity.description or 'ثبت نشده'}

📊 **نتیجه:**
{activity.result or 'ثبت نشده'}

🏅 **دستاوردها:**
{activity.achievements or 'ثبت نشده'}

💬 **بازخورد:**
{activity.feedback or 'ثبت نشده'}
"""
        QMessageBox.information(self, "جزئیات فعالیت", details)
    
    def delete_activity(self, activity):
        """حذف فعالیت"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف فعالیت '{activity.title}' اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # (بازرسی شانزدهم) نتیجهٔ حذف بررسی می‌شود؛ قبلاً حتی وقتی سرویس
                # False برمی‌گرداند (رکورد قبلاً حذف شده) پیام موفقیت داده می‌شد.
                deleted = self.extracurricular_service.delete_activity(activity.id)
                self.load_activities()
                if deleted:
                    QMessageBox.information(self, "موفقیت", "فعالیت با موفقیت حذف شد")
                else:
                    QMessageBox.warning(self, "توجه", "این فعالیت پیدا نشد (احتمالاً قبلاً حذف شده است)؛ فهرست تازه‌سازی شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{e!s}")