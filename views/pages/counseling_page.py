"""
صفحه مدیریت جلسات مشاوره
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
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dal.academic_year_dal import AcademicYearDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from services.counseling_service import CounselingService
from utils.logger import get_logger
from views.dialogs.counseling_session_form import CounselingSessionForm


class CounselingPage(QWidget):
    """صفحه مدیریت جلسات مشاوره"""
    
    student_selected = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.counseling_service = CounselingService()
        self.student_dal = StudentDAL()
        self.staff_dal = StaffDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.logger = get_logger(self.__class__.__name__)
        
        self.sessions = []
        self.visible_sessions = []
        self.all_students = []
        self.all_counselors = []
        
        self.setup_ui()
        self.load_counselors()
        self.load_students()
        self.load_sessions()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        title_label = QLabel("🧑‍⚕️ مدیریت جلسات مشاوره")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        toolbar.addWidget(title_label)
        toolbar.addStretch()
        
        # فیلتر مشاور
        toolbar.addWidget(QLabel("مشاور:"))
        self.counselor_filter_combo = QComboBox()
        self.counselor_filter_combo.setMinimumWidth(150)
        self.counselor_filter_combo.addItem("همه مشاوران", None)
        self.counselor_filter_combo.currentIndexChanged.connect(self.filter_sessions)
        toolbar.addWidget(self.counselor_filter_combo)
        
        # فیلتر وضعیت
        toolbar.addWidget(QLabel("وضعیت:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItem("همه", None)
        from models.counseling_session import CounselingSession
        for value, display in CounselingSession.STATUS_CHOICES:
            self.status_filter_combo.addItem(display, value)
        self.status_filter_combo.currentIndexChanged.connect(self.filter_sessions)
        toolbar.addWidget(self.status_filter_combo)
        
        toolbar.addSpacing(10)
        
        self.add_btn = QPushButton("➕ ثبت جلسه جدید")
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
        self.add_btn.clicked.connect(self.add_session)
        toolbar.addWidget(self.add_btn)
        
        layout.addLayout(toolbar)
        
        # ===== بخش اصلی: Splitter =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ===== سمت چپ: جدول جلسات =====
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ردیف", "دانش‌آموز", "تاریخ", "نوع", "مشاور", "وضعیت", "عملیات"
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
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemClicked.connect(self.on_item_clicked)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        left_layout.addWidget(self.table)
        splitter.addWidget(left_widget)
        
        # ===== سمت راست: جزئیات =====
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        details_group = QGroupBox("📋 جزئیات جلسه")
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
        self.details_text.setPlaceholderText("برای مشاهده جزئیات، روی یک جلسه کلیک کنید...")
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
    
    def load_counselors(self):
        """بارگذاری مشاوران"""
        try:
            staff_list = self.staff_dal.get_all()
            self.all_counselors = [s for s in staff_list if s.role == "counselor"]
            self.counselor_filter_combo.clear()
            self.counselor_filter_combo.addItem("همه مشاوران", None)
            for counselor in self.all_counselors:
                self.counselor_filter_combo.addItem(counselor.full_name, counselor.id)
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری مشاوران: {e}")
    
    def load_students(self):
        """بارگذاری دانش‌آموزان"""
        try:
            self.all_students = self.student_dal.get_all()
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری دانش‌آموزان: {e}")
    
    def load_sessions(self):
        """بارگذاری جلسات"""
        try:
            self.sessions = self.counseling_service.get_all_sessions()
            active_year = self.academic_year_dal.get_active()
            if active_year:
                profiles = self.profile_dal.get_by_ids([s.student_profile_id for s in self.sessions if s.student_profile_id])
                valid_profile_ids = {pid for pid, p in profiles.items() if p and p.academic_year_id == active_year.id}
                self.sessions = [s for s in self.sessions if s.student_profile_id in valid_profile_ids]
            self.display_sessions(self.sessions)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری جلسات:\n{e!s}")
    
    def filter_sessions(self):
        """فیلتر جلسات"""
        counselor_id = self.counselor_filter_combo.currentData()
        status = self.status_filter_combo.currentData()
        
        filtered = self.sessions
        
        if counselor_id:
            filtered = [s for s in filtered if s.counselor_id == counselor_id]
        
        if status:
            filtered = [s for s in filtered if s.status == status]
        
        self.display_sessions(filtered)
    
    def display_sessions(self, sessions):
        """نمایش جلسات در جدول و نگه‌داشتن نگاشت ردیف به جلسه."""
        self.visible_sessions = list(sessions or [])
        self.table.setRowCount(len(self.visible_sessions))
        
        for row, session in enumerate(self.visible_sessions):
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            student_name = getattr(session, 'student_name', 'نامشخص')
            self.table.setItem(row, 1, QTableWidgetItem(student_name))
            
            self.table.setItem(row, 2, QTableWidgetItem(session.session_date or ""))
            
            type_display = session.type_display if hasattr(session, 'type_display') else session.type
            self.table.setItem(row, 3, QTableWidgetItem(type_display))
            
            counselor_name = getattr(session, 'counselor_name', 'نامشخص')
            self.table.setItem(row, 4, QTableWidgetItem(counselor_name))
            
            status_item = QTableWidgetItem(session.status_display)
            if session.status == 'completed':
                status_item.setBackground(QColor(200, 255, 200))
            elif session.status == 'scheduled':
                status_item.setBackground(QColor(255, 255, 200))
            elif session.status == 'cancelled':
                status_item.setBackground(QColor(255, 200, 200))
            else:
                status_item.setBackground(QColor(240, 240, 240))
            self.table.setItem(row, 5, status_item)
            
            # دکمه‌ها
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            view_btn = QPushButton("👁️")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("background-color: #0B2E4F; color: #F4C542; border: none; border-radius: 4px;")
            view_btn.clicked.connect(lambda checked, s=session: self.view_session(s))
            btn_layout.addWidget(view_btn)
            
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setStyleSheet("background-color: #F4D35E; color: #111111; border: none; border-radius: 4px;")
            edit_btn.clicked.connect(lambda checked, s=session: self.edit_session(s))
            btn_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 4px;")
            delete_btn.clicked.connect(lambda checked, s=session: self.delete_session(s))
            btn_layout.addWidget(delete_btn)
            
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 6, btn_widget)
            self.table.setRowHeight(row, 40)
    
    def on_item_clicked(self, item):
        """نمایش جزئیات جلسه با یک کلیک در پنل سمت راست."""
        row = item.row()
        if 0 <= row < len(self.visible_sessions):
            self.show_session_details(self.visible_sessions[row])

    def on_item_double_clicked(self, item):
        """ویرایش جلسه با دابل کلیک."""
        row = item.row()
        if 0 <= row < len(self.visible_sessions):
            self.edit_session(self.visible_sessions[row])

    def add_session(self):
        """افزودن جلسه جدید"""
        form = CounselingSessionForm(parent=self)
        form.exec()

    def edit_session(self, session):
        """ویرایش جلسه"""
        form = CounselingSessionForm(session_id=session.id, parent=self)
        form.session_saved.connect(self.load_sessions)
        form.exec()

    def view_session(self, session):
        """نمایش جزئیات جلسه در پنل سمت راست."""
        self.show_session_details(session)

    def show_session_details(self, session):
        """ساخت و نمایش متن جزئیات جلسه انتخاب‌شده."""
        details = f"""
🧑‍⚕️ **جزئیات جلسه مشاوره**

👤 دانش‌آموز: {getattr(session, 'student_name', 'نامشخص')}
🧑‍⚕️ مشاور: {getattr(session, 'counselor_name', 'نامشخص')}
📅 تاریخ: {getattr(session, 'session_date', None) or 'ثبت نشده'}
🕐 زمان: {getattr(session, 'session_time', None) or 'ثبت نشده'}
⏱️ مدت: {getattr(session, 'duration_minutes', None) or 0} دقیقه
📍 نوع: {getattr(session, 'type_display', None) or getattr(session, 'type', 'ثبت نشده')}
📞 روش: {getattr(session, 'method_display', None) or getattr(session, 'method', 'ثبت نشده')}
📍 مکان: {getattr(session, 'location', None) or 'ثبت نشده'}
📌 وضعیت: {getattr(session, 'status_display', None) or getattr(session, 'status', 'ثبت نشده')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 **موضوع:** {getattr(session, 'topic', None) or 'ثبت نشده'}

🎯 **اهداف:**
{getattr(session, 'goals', None) or 'ثبت نشده'}

📊 **خلاصه:**
{getattr(session, 'summary', None) or 'ثبت نشده'}

📄 **جزئیات:**
{getattr(session, 'details', None) or 'ثبت نشده'}

🛠️ **مداخلات مطرح‌شده:**
{getattr(session, 'interventions_discussed', None) or 'ثبت نشده'}

📋 **توصیه‌ها:**
{getattr(session, 'recommendations', None) or 'ثبت نشده'}

📚 **تکالیف:**
{getattr(session, 'homework', None) or 'ثبت نشده'}

📊 **نتیجه:**
{getattr(session, 'outcome', None) or 'ثبت نشده'}

🔔 **نیاز به پیگیری:** {'بله' if getattr(session, 'follow_up_needed', False) else 'خیر'}
📅 **جلسه بعدی:** {getattr(session, 'next_session_date', None) or 'تعیین نشده'}
"""
        self.details_text.setPlainText(details)
        self.details_text.verticalScrollBar().setValue(0)

    def delete_session(self, session):
        """حذف جلسه"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            "آیا از حذف این جلسه مشاوره اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # (بازرسی شانزدهم) نتیجهٔ حذف بررسی می‌شود
                deleted = self.counseling_service.delete_session(session.id)
                self.load_sessions()
                if deleted:
                    QMessageBox.information(self, "موفقیت", "جلسه با موفقیت حذف شد")
                else:
                    QMessageBox.warning(self, "توجه", "این جلسه پیدا نشد (احتمالاً قبلاً حذف شده است)؛ فهرست تازه‌سازی شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{e!s}")
    
    def view_student_profile(self):
        """مشاهده پرونده دانش‌آموز"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "توجه", "لطفاً یک جلسه را انتخاب کنید.")
            return
        
        if row >= len(self.visible_sessions):
            QMessageBox.warning(self, "توجه", "جلسه انتخاب‌شده معتبر نیست.")
            return

        session = self.visible_sessions[row]
        profile_id = session.student_profile_id
        if profile_id:
            self.student_selected.emit(profile_id)
        else:
            QMessageBox.warning(self, "توجه", "پرونده دانش‌آموز یافت نشد.")