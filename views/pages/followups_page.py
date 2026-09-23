"""
صفحه مدیریت پیگیری‌ها - نسخه نهایی با ویرایش کامل و جستجوی پیشرفته
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
from dal.student_dal import StudentDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.intervention_dal import InterventionDAL
from dal.academic_year_dal import AcademicYearDAL
from services.followup_service import FollowUpService
from utils.logger import get_logger
from views.dialogs.followup_form import FollowUpForm


class FollowUpsPage(QWidget):
    """صفحه مدیریت پیگیری‌ها با جستجوی پیشرفته"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.followup_service = FollowUpService()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.intervention_dal = InterventionDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.staff_dal = StaffDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        self.logger = get_logger(self.__class__.__name__)
        
        self.followups = []
        self.all_students = []
        self.all_teachers = []
        self.selected_teacher_id = None
        
        self.setup_ui()
        self.load_teachers()
        self.load_followups()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== نوار ابزار اصلی =====
        toolbar = QHBoxLayout()
        
        title_label = QLabel("🔔 مدیریت پیگیری‌ها")
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
        
        # جستجوی ساده
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجوی متن در پیگیری‌ها...")
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
                background-color: #66BB6A;
                color: #111111;
                padding: 5px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7d3c98; }
        """)
        self.search_btn.clicked.connect(self.apply_search)
        toolbar.addWidget(self.search_btn)
        
        # فیلتر وضعیت
        toolbar.addWidget(QLabel("وضعیت:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItem("همه", None)
        self.status_filter_combo.addItem("🟡 در انتظار", "pending")
        self.status_filter_combo.addItem("✅ انجام شده", "done")
        self.status_filter_combo.addItem("🔄 نیازمند ادامه", "continued")
        self.status_filter_combo.addItem("🔒 مختومه", "closed")
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
        
        self.add_btn = QPushButton("➕ ثبت پیگیری جدید")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7d3c98; }
        """)
        self.add_btn.clicked.connect(self.add_followup)
        toolbar.addWidget(self.add_btn)
        
        layout.addLayout(toolbar)
        
        # ===== جدول نتایج =====
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ردیف", "دانش‌آموز", "مداخله", "تاریخ پیگیری", "تاریخ اقدام بعدی", "وضعیت", "توضیحات", "عملیات"
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
        """وقتی معلم تغییر می‌کند، پیگیری‌ها را فیلتر کن"""
        self.selected_teacher_id = self.teacher_combo.currentData()
        self.apply_search()
    
    def apply_search(self):
        """اعمال جستجو و فیلترها"""
        teacher_id = self.teacher_combo.currentData()
        search_text = self.search_input.text().strip()
        status = self.status_filter_combo.currentData()
        
        try:
            active_year = self.academic_year_dal.get_active()
            year_id = active_year.id if active_year else None
            if search_text:
                if teacher_id:
                    followups = self.followup_service.search_followups_by_teacher(
                        teacher_id, search_text, year_id=year_id
                    )
                else:
                    followups = self.followup_service.search_followups(search_text, limit=None, year_id=year_id)
            else:
                if teacher_id:
                    followups = self.followup_service.get_followups_by_teacher(teacher_id, year_id=year_id)
                else:
                    followups = self.followup_service.get_all_followups(limit=None, year_id=year_id)
            
            # فیلتر وضعیت
            if status is not None:
                followups = [f for f in followups if f.status == status]
            
            active_year = self.academic_year_dal.get_active()
            if active_year:
                interventions = self.intervention_dal.get_by_ids(f.intervention_id for f in followups)
                profiles = self.profile_dal.get_by_ids(
                    i.student_profile_id for i in interventions.values()
                )
                followups = [
                    f for f in followups
                    if (interventions.get(f.intervention_id)
                        and profiles.get(interventions[f.intervention_id].student_profile_id)
                        and profiles[interventions[f.intervention_id].student_profile_id].academic_year_id == active_year.id)
                ]
            self.followups = followups
            self.display_followups(self.followups)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در جستجو:\n{e!s}")
    
    def clear_search(self):
        """پاک کردن جستجو"""
        self.search_input.clear()
        self.status_filter_combo.setCurrentIndex(0)
        self.teacher_combo.setCurrentIndex(0)
        self.load_followups()
    
    def load_followups(self):
        """بارگذاری پیگیری‌ها با استفاده از سرویس"""
        try:
            followups = active_year = self.academic_year_dal.get_active()
            year_id = active_year.id if active_year else None
            followups = self.followup_service.get_all_followups(limit=None, year_id=year_id)
            active_year = self.academic_year_dal.get_active()
            if active_year:
                interventions = self.intervention_dal.get_by_ids(f.intervention_id for f in followups)
                profiles = self.profile_dal.get_by_ids(
                    i.student_profile_id for i in interventions.values()
                )
                followups = [
                    f for f in followups
                    if (interventions.get(f.intervention_id)
                        and profiles.get(interventions[f.intervention_id].student_profile_id)
                        and profiles[interventions[f.intervention_id].student_profile_id].academic_year_id == active_year.id)
                ]
            self.followups = followups
            self.display_followups(self.followups)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری پیگیری‌ها:\n{e!s}")
    
    def filter_followups(self):
        """فیلتر پیگیری‌ها بر اساس وضعیت و معلم"""
        self.apply_search()
    
    def display_followups(self, followups):
        """نمایش پیگیری‌ها در جدول"""
        self.table.setRowCount(len(followups))
        
        for row, followup in enumerate(followups):
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            student_name = getattr(followup, 'student_name', 'نامشخص')
            self.table.setItem(row, 1, QTableWidgetItem(student_name))
            
            intervention_display = getattr(followup, 'intervention_type_display', 'نامشخص')
            self.table.setItem(row, 2, QTableWidgetItem(intervention_display))
            
            self.table.setItem(row, 3, QTableWidgetItem(followup.date or ""))
            self.table.setItem(row, 4, QTableWidgetItem(followup.next_action_date or ""))
            
            status_item = QTableWidgetItem(followup.status_display)
            if followup.status == "pending":
                status_item.setBackground(QColor(255, 255, 200))
            elif followup.status == "done":
                status_item.setBackground(QColor(200, 255, 200))
            elif followup.status == "continued":
                status_item.setBackground(QColor(200, 230, 255))
            else:
                status_item.setBackground(QColor(255, 200, 200))
            self.table.setItem(row, 5, status_item)
            
            desc_text = followup.description[:40] + "..." if followup.description and len(followup.description) > 40 else followup.description or ""
            self.table.setItem(row, 6, QTableWidgetItem(desc_text))
            
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            view_btn = QPushButton("👁️")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("background-color: #0B2E4F; color: #F4C542; border: none; border-radius: 4px;")
            view_btn.clicked.connect(lambda checked, f=followup: self.view_followup(f))
            btn_layout.addWidget(view_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 4px;")
            delete_btn.clicked.connect(lambda checked, f=followup: self.delete_followup(f))
            btn_layout.addWidget(delete_btn)
            
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 7, btn_widget)
            self.table.setRowHeight(row, 40)
    
    def on_item_double_clicked(self, item):
        row = item.row()
        if row < len(self.followups):
            f = self.followups[row]
            self.edit_followup(f)
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current_row = self.table.currentRow()
            if current_row >= 0 and current_row < len(self.followups):
                self.edit_followup(self.followups[current_row])
        super().keyPressEvent(event)
    
    def edit_followup(self, followup):
        """ویرایش پیگیری"""
        from views.dialogs.followup_form import FollowUpForm
        form = FollowUpForm(followup_id=followup.id, parent=self)
        form.followup_saved.connect(self.filter_followups)
        form.exec()
    
    def add_followup(self):
        """افزودن پیگیری جدید"""
        form = FollowUpForm(parent=self)
        if form.exec() == QDialog.DialogCode.Accepted:
            self.filter_followups()
            QMessageBox.information(self, "موفقیت", "پیگیری با موفقیت ثبت شد")
    
    def view_followup(self, followup):
        """نمایش جزئیات پیگیری"""
        student_name = getattr(followup, 'student_name', 'نامشخص')
        staff_name = getattr(followup, 'staff_name', 'نامشخص')
        
        detail_text = f"""
🔔 **جزئیات پیگیری**

👤 دانش‌آموز: {student_name}
🛠️ مداخله: {getattr(followup, 'intervention_type_display', 'نامشخص')}
📅 تاریخ پیگیری: {followup.date}
📅 تاریخ اقدام بعدی: {followup.next_action_date or 'تعیین نشده'}
📌 وضعیت: {followup.status_display}
👤 مسئول: {staff_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 **توضیحات:**
{followup.description or 'ثبت نشده'}

📊 **نوع نتیجه:**
{followup.result_type_display or 'ثبت نشده'}

📄 **شرح نتیجه:**
{followup.result_description or 'ثبت نشده'}
"""
        QMessageBox.information(self, "جزئیات پیگیری", detail_text)
    
    def delete_followup(self, followup):
        """حذف پیگیری با استفاده از سرویس"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            "آیا از حذف این پیگیری اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted = self.followup_service.delete_followup(followup.id)
                self.filter_followups()
                if deleted:
                    QMessageBox.information(
                        self, "موفقیت", "پیگیری با موفقیت حذف شد"
                    )
                else:
                    QMessageBox.warning(self, "خطا", "پیگیری حذف نشد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{e!s}")