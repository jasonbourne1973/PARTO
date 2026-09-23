"""
صفحه مدیریت اهداف فردی دانش‌آموزان
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

undefined
from dal.student_dal import StudentDAL
from models.individual_goal import IndividualGoal
from services.goal_service import GoalService
from utils.logger import get_logger
from views.dialogs.goal_form import GoalForm


class GoalsPage(QWidget):
    """صفحه مدیریت اهداف فردی"""
    
    student_selected = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.goal_service = GoalService()
        self.student_dal = StudentDAL()
        self.staff_dal = StaffDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.logger = get_logger(self.__class__.__name__)
        
        self.goals = []
        self.visible_goals = []
        self.all_students = []
        
        self.setup_ui()
        self.load_students()
        self.load_goals()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        title_label = QLabel("🎯 مدیریت اهداف فردی")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        toolbar.addWidget(title_label)
        toolbar.addStretch()
        
        # فیلتر وضعیت
        toolbar.addWidget(QLabel("وضعیت:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.setMinimumWidth(120)
        self.status_filter_combo.addItem("همه", None)
        for value, display in IndividualGoal.STATUS_CHOICES:
            self.status_filter_combo.addItem(display, value)
        self.status_filter_combo.currentIndexChanged.connect(self.filter_goals)
        toolbar.addWidget(self.status_filter_combo)
        
        # فیلتر حوزه
        toolbar.addWidget(QLabel("حوزه:"))
        self.domain_filter_combo = QComboBox()
        self.domain_filter_combo.addItem("همه", None)
        for value, display in IndividualGoal.DOMAIN_CHOICES:
            self.domain_filter_combo.addItem(display, value)
        self.domain_filter_combo.currentIndexChanged.connect(self.filter_goals)
        toolbar.addWidget(self.domain_filter_combo)
        
        toolbar.addSpacing(10)
        
        self.add_btn = QPushButton("➕ ثبت هدف جدید")
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
        self.add_btn.clicked.connect(self.add_goal)
        toolbar.addWidget(self.add_btn)
        
        layout.addLayout(toolbar)
        
        # ===== بخش اصلی: Splitter =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ===== سمت چپ: جدول اهداف =====
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ردیف", "دانش‌آموز", "عنوان", "حوزه", "پیشرفت", "وضعیت", "عملیات"
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
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemClicked.connect(self.on_item_clicked)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        left_layout.addWidget(self.table)
        splitter.addWidget(left_widget)
        
        # ===== سمت راست: جزئیات =====
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        details_group = QGroupBox("📋 جزئیات هدف")
        details_group.setStyleSheet("""
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
        details_layout = QVBoxLayout(details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                border: 1px solid #8BC34A;
                padding: 10px;
                font-size: 13px;
                background-color: #08223A;
                line-height: 1.8;
            }
        """)
        self.details_text.setPlaceholderText("برای مشاهده جزئیات، روی یک هدف کلیک کنید...")
        details_layout.addWidget(self.details_text)
        
        right_layout.addWidget(details_group)
        
        # دکمه مشاهده پرونده
        view_profile_btn = QPushButton("👤 مشاهده پرونده دانش‌آموز")
        view_profile_btn.setStyleSheet("""
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
        view_profile_btn.clicked.connect(self.view_student_profile)
        right_layout.addWidget(view_profile_btn)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([550, 450])
        
        layout.addWidget(splitter)
    
    def load_students(self):
        """بارگذاری دانش‌آموزان"""
        try:
            self.all_students = self.student_dal.get_all()
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری دانش‌آموزان: {e}")
    
    def load_goals(self):
        """بارگذاری اهداف"""
        try:
            self.goals = self.goal_service.get_all_goals()
            active_year = self.academic_year_dal.get_active()
            if active_year:
                profiles = self.profile_dal.get_by_ids([g.student_profile_id for g in self.goals if g.student_profile_id])
                valid_profile_ids = {pid for pid, p in profiles.items() if p and p.academic_year_id == active_year.id}
                self.goals = [g for g in self.goals if g.student_profile_id in valid_profile_ids]
            self.display_goals(self.goals)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری اهداف:\n{e!s}")
    
    def filter_goals(self):
        """فیلتر اهداف"""
        status = self.status_filter_combo.currentData()
        domain = self.domain_filter_combo.currentData()
        
        filtered = self.goals
        
        if status:
            filtered = [g for g in filtered if g.status == status]
        
        if domain:
            filtered = [g for g in filtered if g.domain == domain]
        
        self.display_goals(filtered)
    
    def display_goals(self, goals):
        """نمایش اهداف در جدول و نگه‌داشتن نگاشت ردیف به هدف."""
        self.visible_goals = list(goals or [])
        self.table.setRowCount(len(self.visible_goals))
        
        for row, goal in enumerate(self.visible_goals):
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            student_name = getattr(goal, 'student_name', 'نامشخص')
            self.table.setItem(row, 1, QTableWidgetItem(student_name))
            
            self.table.setItem(row, 2, QTableWidgetItem(goal.title or ""))
            
            domain_item = QTableWidgetItem(goal.domain_display)
            self.table.setItem(row, 3, domain_item)
            
            # نوار پیشرفت
            progress_widget = QWidget()
            progress_layout = QHBoxLayout(progress_widget)
            progress_layout.setContentsMargins(0, 0, 0, 0)
            
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(goal.progress_percent or 0)
            progress_bar.setTextVisible(True)
            progress_bar.setFormat(f"{goal.progress_percent or 0}%")
            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #D9C36A;
                    border-radius: 3px;
                    text-align: center;
                    height: 16px;
                }
                QProgressBar::chunk {
                    background-color: #66BB6A;
                    border-radius: 3px;
                }
            """)
            progress_layout.addWidget(progress_bar)
            
            self.table.setCellWidget(row, 4, progress_widget)
            
            status_item = QTableWidgetItem(goal.status_display)
            if goal.status in [IndividualGoal.STATUS_ACHIEVED, IndividualGoal.STATUS_COMPLETED]:
                status_item.setBackground(QColor(200, 255, 200))
            elif goal.is_active_goal:
                status_item.setBackground(QColor(200, 230, 255))
            elif goal.status == IndividualGoal.STATUS_ABANDONED:
                status_item.setBackground(QColor(255, 200, 200))
            else:
                status_item.setBackground(QColor(255, 255, 200))
            self.table.setItem(row, 5, status_item)
            
            # دکمه‌ها
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            view_btn = QPushButton("👁️")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("background-color: #0B2E4F; color: #F4C542; border: none; border-radius: 4px;")
            view_btn.clicked.connect(lambda checked, g=goal: self.view_goal(g))
            btn_layout.addWidget(view_btn)
            
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setStyleSheet("background-color: #F4D35E; color: #111111; border: none; border-radius: 4px;")
            edit_btn.clicked.connect(lambda checked, g=goal: self.edit_goal(g))
            btn_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 4px;")
            delete_btn.clicked.connect(lambda checked, g=goal: self.delete_goal(g))
            btn_layout.addWidget(delete_btn)
            
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 6, btn_widget)
            self.table.setRowHeight(row, 45)
    
    def on_item_clicked(self, item):
        """نمایش جزئیات هدف با یک کلیک در پنل سمت راست."""
        row = item.row()
        if 0 <= row < len(self.visible_goals):
            self.show_goal_details(self.visible_goals[row])

    def on_item_double_clicked(self, item):
        """ویرایش هدف با دابل کلیک."""
        row = item.row()
        if 0 <= row < len(self.visible_goals):
            self.edit_goal(self.visible_goals[row])

    def add_goal(self):
        """افزودن هدف جدید"""
        form = GoalForm(parent=self)
        form.exec()

    def edit_goal(self, goal):
        """ویرایش هدف"""
        form = GoalForm(goal_id=goal.id, parent=self)
        form.goal_saved.connect(self.load_goals)
        form.exec()

    def view_goal(self, goal):
        """نمایش جزئیات هدف در پنل سمت راست."""
        self.show_goal_details(goal)

    def show_goal_details(self, goal):
        """ساخت و نمایش جزئیات هدف انتخاب‌شده."""
        details = f"""
🎯 **جزئیات هدف فردی**

👤 دانش‌آموز: {getattr(goal, 'student_name', 'نامشخص')}
📝 عنوان: {getattr(goal, 'title', None) or 'ثبت نشده'}
🎯 حوزه: {getattr(goal, 'domain_display', None) or getattr(goal, 'domain', 'ثبت نشده')}
📊 اولویت: {getattr(goal, 'priority_display', None) or getattr(goal, 'priority', 'ثبت نشده')}
👨‍🏫 مسئول پیگیری: {getattr(goal, 'assigned_to_name', None) or 'نامشخص'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 **بازه زمانی**
تاریخ شروع: {getattr(goal, 'start_date', None) or 'ثبت نشده'}
تاریخ هدف: {getattr(goal, 'target_date', None) or 'ثبت نشده'}
تاریخ پایان: {getattr(goal, 'end_date', None) or 'ثبت نشده'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 **توضیحات:**
{getattr(goal, 'description', None) or 'ثبت نشده'}

✅ **معیارهای موفقیت:**
{getattr(goal, 'success_criteria', None) or 'ثبت نشده'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **پیشرفت:**
درصد پیشرفت: {getattr(goal, 'progress_percent', 0) or 0}%
وضعیت پیشرفت: {getattr(goal, 'progress_status', None) or 'ثبت نشده'}
یادداشت‌ها: {getattr(goal, 'progress_notes', None) or 'ثبت نشده'}

📌 **وضعیت:** {getattr(goal, 'status_display', None) or getattr(goal, 'status', 'ثبت نشده')}
📊 **نتیجه:** {getattr(goal, 'result', None) or 'ثبت نشده'}

🔗 **شایستگی مرتبط:** {getattr(goal, 'competency_name', None) or 'ثبت نشده'}
"""
        self.details_text.setPlainText(details)
        self.details_text.verticalScrollBar().setValue(0)

    def delete_goal(self, goal):
        """حذف هدف"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            "آیا از حذف این هدف اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # (بازرسی شانزدهم) نتیجهٔ حذف بررسی می‌شود
                deleted = self.goal_service.delete_goal(goal.id)
                self.load_goals()
                if deleted:
                    QMessageBox.information(self, "موفقیت", "هدف با موفقیت حذف شد")
                else:
                    QMessageBox.warning(self, "توجه", "این هدف پیدا نشد (احتمالاً قبلاً حذف شده است)؛ فهرست تازه‌سازی شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{e!s}")
    
    def view_student_profile(self):
        """مشاهده پرونده دانش‌آموز"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "توجه", "لطفاً یک هدف را انتخاب کنید.")
            return
        
        if row >= len(self.visible_goals):
            QMessageBox.warning(self, "توجه", "هدف انتخاب‌شده معتبر نیست.")
            return

        goal = self.visible_goals[row]
        profile_id = goal.student_profile_id
        if profile_id:
            self.student_selected.emit(profile_id)
        else:
            QMessageBox.warning(self, "توجه", "پرونده دانش‌آموز یافت نشد.")