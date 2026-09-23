"""
صفحه مدیریت مداخلات - نسخه نهایی با ویرایش کامل و جستجوی پیشرفته
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
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

from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.academic_year_dal import AcademicYearDAL
from dal.student_dal import StudentDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from services.intervention_service import InterventionService
from utils.logger import get_logger
from views.dialogs.intervention_form import InterventionForm


class InterventionsPage(QWidget):
    """صفحه مدیریت مداخلات با جستجوی پیشرفته"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.intervention_service = InterventionService()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        self.logger = get_logger(self.__class__.__name__)
        
        self.interventions = []
        self.all_students = []
        self.all_teachers = []
        self.selected_teacher_id = None
        
        self.setup_ui()
        self.load_teachers()
        self.load_students_filter()
        self.load_interventions()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== نوار ابزار اصلی =====
        toolbar = QHBoxLayout()
        
        title_label = QLabel("🛠️ مدیریت مداخلات")
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
        self.student_filter_combo.currentIndexChanged.connect(self.filter_interventions)
        toolbar.addWidget(self.student_filter_combo)
        
        # جستجوی ساده
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجوی متن در مداخلات...")
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
        self.search_input.returnPressed.connect(self.apply_search)
        toolbar.addWidget(self.search_input)
        
        self.search_btn = QPushButton("🔍 جستجو")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #F28C28;
                color: #111111;
                padding: 5px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #d35400; }
        """)
        self.search_btn.clicked.connect(self.apply_search)
        toolbar.addWidget(self.search_btn)
        
        # فیلتر وضعیت
        toolbar.addWidget(QLabel("وضعیت:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItem("همه", None)
        self.status_filter_combo.addItem("🟡 برنامه‌ریزی شده", "planned")
        self.status_filter_combo.addItem("🔄 در حال اجرا", "in_progress")
        self.status_filter_combo.addItem("✅ انجام شده", "done")
        self.status_filter_combo.addItem("🟢 تکمیل شده", "completed")
        self.status_filter_combo.addItem("❌ لغو شده", "cancelled")
        self.status_filter_combo.currentIndexChanged.connect(self.apply_search)
        toolbar.addWidget(self.status_filter_combo)
        
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
        
        self.add_btn = QPushButton("➕ ثبت مداخله جدید")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #F28C28;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #d35400; }
        """)
        self.add_btn.clicked.connect(self.add_intervention)
        toolbar.addWidget(self.add_btn)
        
        layout.addLayout(toolbar)
        
        # ===== جدول نتایج =====
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ردیف", "دانش‌آموز", "تاریخ", "نوع", "مسئول", "وضعیت", "نتیجه", "عملیات"
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
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
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
        """وقتی معلم تغییر می‌کند، لیست دانش‌آموزان و مداخلات را فیلتر کن"""
        self.selected_teacher_id = self.teacher_combo.currentData()
        self.load_students_filter()
        self.filter_interventions()
    
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
    
    def apply_search(self):
        """اعمال جستجو و فیلترها"""
        student_id = self.student_filter_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        search_text = self.search_input.text().strip()
        status = self.status_filter_combo.currentData()
        
        try:
            if search_text:
                if student_id:
                    interventions = self.intervention_service.search_interventions_by_student(
                        student_id, search_text
                    )
                elif teacher_id:
                    interventions = self.intervention_service.search_interventions_by_teacher(
                        teacher_id, search_text
                    )
                else:
                    interventions = self.intervention_service.search_interventions(search_text)
            else:
                if student_id:
                    interventions = self.intervention_service.get_interventions_by_student(student_id)
                elif teacher_id:
                    interventions = self.intervention_service.get_interventions_by_teacher(teacher_id)
                else:
                    interventions = self.intervention_service.get_all_interventions(include_staff_info=True)
            
            # فیلتر وضعیت
            if status is not None:
                interventions = [i for i in interventions if i.status == status]
            
            # فیلتر اضافی بر اساس معلم
            if student_id and teacher_id:
                interventions = [i for i in interventions if i.staff_id == teacher_id]
            
            self.interventions = interventions
            self.display_interventions(self.interventions)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در جستجو:\n{e!s}")
    
    def clear_search(self):
        """پاک کردن جستجو"""
        self.search_input.clear()
        self.status_filter_combo.setCurrentIndex(0)
        self.student_filter_combo.setCurrentIndex(0)
        self.load_interventions()
    
    def load_interventions(self):
        """بارگذاری مداخلات با استفاده از سرویس"""
        try:
            self.interventions = self.intervention_service.get_all_interventions(limit=100, include_staff_info=True)
            self.display_interventions(self.interventions)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری مداخلات:\n{e!s}")
    
    def filter_interventions(self):
        """فیلتر مداخلات بر اساس دانش‌آموز و معلم"""
        self.apply_search()
    
    def display_interventions(self, interventions):
        """نمایش مداخلات در جدول"""
        self.table.setRowCount(len(interventions))
        
        for row, intervention in enumerate(interventions):
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            student_name = getattr(intervention, 'student_name', 'نامشخص')
            self.table.setItem(row, 1, QTableWidgetItem(student_name))
            
            self.table.setItem(row, 2, QTableWidgetItem(intervention.date or ""))
            self.table.setItem(row, 3, QTableWidgetItem(intervention.type_display))
            
            staff_name = getattr(intervention, 'staff_name', 'نامشخص')
            self.table.setItem(row, 4, QTableWidgetItem(staff_name))
            
            status_item = QTableWidgetItem(intervention.status_display)
            if intervention.status == "planned":
                status_item.setBackground(QColor(255, 255, 200))
            elif intervention.status == "in_progress":
                status_item.setBackground(QColor(200, 230, 255))
            elif intervention.status == "done" or intervention.status == "completed":
                status_item.setBackground(QColor(200, 255, 200))
            else:
                status_item.setBackground(QColor(255, 200, 200))
            self.table.setItem(row, 5, status_item)
            
            result_text = intervention.result[:50] + "..." if intervention.result and len(intervention.result) > 50 else intervention.result or "نامشخص"
            self.table.setItem(row, 6, QTableWidgetItem(result_text))
            
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            view_btn = QPushButton("👁️")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("background-color: #0B2E4F; color: #F4C542; border: none; border-radius: 4px;")
            view_btn.clicked.connect(lambda checked, i=intervention: self.view_intervention(i))
            btn_layout.addWidget(view_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 4px;")
            delete_btn.clicked.connect(lambda checked, i=intervention: self.delete_intervention(i))
            btn_layout.addWidget(delete_btn)
            
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 7, btn_widget)
            self.table.setRowHeight(row, 40)
    
    def on_item_double_clicked(self, item):
        row = item.row()
        if row < len(self.interventions):
            inter = self.interventions[row]
            self.edit_intervention(inter)
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current_row = self.table.currentRow()
            if current_row >= 0 and current_row < len(self.interventions):
                self.edit_intervention(self.interventions[current_row])
        super().keyPressEvent(event)
    
    def edit_intervention(self, inter):
        """ویرایش مداخله"""
        from views.dialogs.intervention_form import InterventionForm
        form = InterventionForm(intervention_id=inter.id, parent=self)
        form.intervention_saved.connect(self.filter_interventions)
        form.exec()
    
    def add_intervention(self):
        """افزودن مداخله جدید"""
        form = InterventionForm(parent=self)
        if form.exec() == QDialog.DialogCode.Accepted:
            self.filter_interventions()
            QMessageBox.information(self, "موفقیت", "مداخله با موفقیت ثبت شد")
    
    def view_intervention(self, intervention):
        """نمایش جزئیات مداخله"""
        student_name = getattr(intervention, 'student_name', 'نامشخص')
        staff_name = getattr(intervention, 'staff_name', 'نامشخص')
        
        detail_text = f"""
🛠️ **جزئیات مداخله**

👤 دانش‌آموز: {student_name}
📅 تاریخ: {intervention.date}
🎯 نوع: {intervention.type_display}
👤 مسئول: {staff_name}
📌 وضعیت: {intervention.status_display}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 **توضیحات:**
{intervention.description}

🎯 **هدف:**
{intervention.goal or 'ثبت نشده'}

📊 **نتیجه:**
{intervention.result or 'هنوز مشخص نشده است'}
"""
        
        QMessageBox.information(self, "جزئیات مداخله", detail_text)
    
    def delete_intervention(self, intervention):
        """حذف مداخله با استفاده از سرویس"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            "آیا از حذف این مداخله اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted = self.intervention_service.delete_intervention(
                    intervention.id
                )
                self.filter_interventions()
                if deleted:
                    QMessageBox.information(
                        self, "موفقیت", "مداخله با موفقیت حذف شد"
                    )
                else:
                    QMessageBox.warning(self, "خطا", "مداخله حذف نشد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{e!s}")