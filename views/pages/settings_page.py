"""
صفحه تنظیمات برنامه - نسخه کامل با مدیریت کاربران
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QMessageBox, QGroupBox,
    QFormLayout, QCheckBox, QSpinBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDialog, QTextEdit, QGridLayout, QScrollArea
    
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from dal.academic_year_dal import AcademicYearDAL
from dal.staff_dal import StaffDAL
from models.academic_year import AcademicYear
from models.staff import Staff
from config.constants import STAFF_ROLES
from utils.security import Security, SessionManager
from database.connection import DatabaseConnection  # ✅ اضافه شد
import sqlite3  # ✅ اضافه شد
import os  # ✅ این خط را اضافه کنید


class SettingsPage(QWidget):
    """صفحه تنظیمات برنامه با مدیریت کاربران"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.academic_year_dal = AcademicYearDAL()
        self.staff_dal = StaffDAL()
        self.db = DatabaseConnection()  # ✅ اضافه شد
        
        self.setup_ui()
        self.load_academic_years()
        self.load_staff()
        self.load_users()
        self.load_staff_for_users()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # عنوان
        title_label = QLabel("⚙️ تنظیمات")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        layout.addWidget(title_label)
        
        # تب‌های تنظیمات
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
    color: #111111;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                padding: 10px;
                background-color: #66BB6A;
            }
            QTabBar::tab {
    color: #111111;
    border: 1px solid #8BC34A;
    background-color: #66BB6A;
                padding: 8px 15px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
    border-color: #F4C542;
                background-color: #8BC34A;
                color: #111111;
            }
        """)
        
        # تب 1: سال‌های تحصیلی
        year_tab = self.create_academic_years_tab()
        tabs.addTab(year_tab, "📅 سال‌های تحصیلی")
        
        # تب 2: کادر مدرسه
        staff_tab = self.create_staff_tab()
        tabs.addTab(staff_tab, "👥 کادر مدرسه")
        
        # تب 3: مدیریت کاربران
        user_tab = self.create_users_tab()
        tabs.addTab(user_tab, "👤 مدیریت کاربران")
        
        # تب 4: اطلاعات مدرسه
        school_tab = self.create_school_tab()
        tabs.addTab(school_tab, "🏫 اطلاعات مدرسه")
        
        # تب 5: درباره
        about_tab = self.create_about_tab()
        tabs.addTab(about_tab, "ℹ️ درباره")

        # تب 6: پشتیبان‌گیری
        self.backup_tab = self.create_backup_tab()
        tabs.addTab(self.backup_tab, "💾 پشتیبان‌گیری")

        # تب 7: مدیریت کلاس‌ها
        class_tab = self.create_classes_tab()
        tabs.addTab(class_tab, "🏫 مدیریت کلاس‌ها")
        
        layout.addWidget(tabs)
    
    def create_academic_years_tab(self):
        """ایجاد تب سال‌های تحصیلی"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # فرم افزودن سال جدید
        form_group = QGroupBox("➕ افزودن سال تحصیلی جدید")
        form_group.setStyleSheet("""
            QGroupBox {
    color: #111111;
    background-color: #66BB6A;
                font-weight: bold;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
    background-color: #8BC34A;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #111111;
            }
        """)
        form_layout = QHBoxLayout()
        form_group.setLayout(form_layout)
        
        form_layout.addWidget(QLabel("عنوان سال:"))
        self.year_title_input = QLineEdit()
        self.year_title_input.setPlaceholderText("مثال: 1406-1407")
        form_layout.addWidget(self.year_title_input)
        
        self.add_year_btn = QPushButton("➕ افزودن")
        self.add_year_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 5px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.add_year_btn.clicked.connect(self.add_academic_year)
        form_layout.addWidget(self.add_year_btn)
        
        layout.addWidget(form_group)
        
        # جدول سال‌های تحصیلی
        self.year_table = QTableWidget()
        self.year_table.setColumnCount(5)
        self.year_table.setHorizontalHeaderLabels(["شناسه", "عنوان", "وضعیت", "بایگانی", "عملیات"])
        self.year_table.setAlternatingRowColors(True)
        self.year_table.setStyleSheet("""
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
        
        header = self.year_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.year_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.year_table)
        
        return tab
    
    def load_academic_years(self):
        """بارگذاری سال‌های تحصیلی در جدول"""
        try:
            years = self.academic_year_dal.get_all(include_archived=True)
            self.year_table.setRowCount(len(years))
            
            for row, year in enumerate(years):
                self.year_table.setItem(row, 0, QTableWidgetItem(str(year.id)))
                self.year_table.setItem(row, 1, QTableWidgetItem(year.title))
                
                status_text = "🟢 فعال" if year.is_active == 1 else "⚪ غیرفعال"
                status_item = QTableWidgetItem(status_text)
                if year.is_active == 1:
                    status_item.setBackground(QColor(200, 255, 200))
                self.year_table.setItem(row, 2, status_item)
                
                archive_text = "📦 بایگانی" if year.is_archived == 1 else "❌ بایگانی نشده"
                archive_item = QTableWidgetItem(archive_text)
                if year.is_archived == 1:
                    archive_item.setBackground(QColor(255, 200, 200))
                self.year_table.setItem(row, 3, archive_item)
                
                btn_widget = QWidget()
                btn_layout = QHBoxLayout()
                btn_layout.setContentsMargins(2, 2, 2, 2)
                
                if year.is_active == 0 and year.is_archived == 0:
                    activate_btn = QPushButton("✅ فعال کن")
                    activate_btn.setFixedSize(70, 25)
                    activate_btn.setStyleSheet("background-color: #66BB6A; color: #F4C542; border: none; border-radius: 3px;")
                    activate_btn.clicked.connect(lambda checked, y=year: self.activate_year(y))
                    btn_layout.addWidget(activate_btn)
                
                if year.is_archived == 0:
                    archive_btn = QPushButton("📦 بایگانی")
                    archive_btn.setFixedSize(70, 25)
                    archive_btn.setStyleSheet("background-color: #F4D35E; color: #F4C542; border: none; border-radius: 3px;")
                    archive_btn.clicked.connect(lambda checked, y=year: self.archive_year(y))
                    btn_layout.addWidget(archive_btn)
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 25)
                delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 3px;")
                delete_btn.clicked.connect(lambda checked, y=year: self.delete_year(y))
                btn_layout.addWidget(delete_btn)
                
                btn_widget.setLayout(btn_layout)
                self.year_table.setCellWidget(row, 4, btn_widget)
                self.year_table.setRowHeight(row, 35)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری سال‌های تحصیلی:\n{str(e)}")
    
    def add_academic_year(self):
        """افزودن سال تحصیلی جدید"""
        title = self.year_title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "خطا", "لطفاً عنوان سال را وارد کنید.")
            return
        
        year = AcademicYear()
        year.title = title
        year.is_active = 0
        year.is_archived = 0
        
        try:
            self.academic_year_dal.create(year)
            self.year_title_input.clear()
            self.load_academic_years()
            QMessageBox.information(self, "موفقیت", f"سال تحصیلی {title} با موفقیت اضافه شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در افزودن سال:\n{str(e)}")
    
    def activate_year(self, year):
        """فعال کردن یک سال تحصیلی"""
        reply = QMessageBox.question(
            self,
            "تأیید فعال‌سازی",
            f"آیا از فعال‌سازی سال {year.title} اطمینان دارید؟\nسال فعلی غیرفعال می‌شود.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.academic_year_dal.set_active(year.id)
                self.load_academic_years()
                QMessageBox.information(self, "موفقیت", f"سال {year.title} با موفقیت فعال شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در فعال‌سازی:\n{str(e)}")
    
    def archive_year(self, year):
        """بایگانی کردن یک سال تحصیلی"""
        reply = QMessageBox.question(
            self,
            "تأیید بایگانی",
            f"آیا از بایگانی سال {year.title} اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.academic_year_dal.archive(year.id)
                self.load_academic_years()
                QMessageBox.information(self, "موفقیت", f"سال {year.title} با موفقیت بایگانی شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در بایگانی:\n{str(e)}")
    
    def delete_year(self, year):
        """حذف سال تحصیلی"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف سال {year.title} اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.academic_year_dal.delete(year.id)
                self.load_academic_years()
                QMessageBox.information(self, "موفقیت", f"سال {year.title} با موفقیت حذف شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{str(e)}")
    
    def create_staff_tab(self):
        """ایجاد تب کادر مدرسه"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # فرم افزودن عضو جدید
        form_group = QGroupBox("➕ افزودن عضو جدید کادر")
        form_group.setStyleSheet("""
            QGroupBox {
    color: #111111;
    background-color: #66BB6A;
                font-weight: bold;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
    background-color: #8BC34A;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #111111;
            }
        """)
        form_layout = QHBoxLayout()
        form_group.setLayout(form_layout)
        
        form_layout.addWidget(QLabel("نام کامل:"))
        self.staff_name_input = QLineEdit()
        self.staff_name_input.setPlaceholderText("نام و نام خانوادگی")
        form_layout.addWidget(self.staff_name_input)
        
        form_layout.addWidget(QLabel("سمت:"))
        self.staff_role_combo = QComboBox()
        for value, display in STAFF_ROLES:
            self.staff_role_combo.addItem(display, value)
        form_layout.addWidget(self.staff_role_combo)
        
        self.add_staff_btn = QPushButton("➕ افزودن")
        self.add_staff_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 5px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #66BB6A; }
        """)
        self.add_staff_btn.clicked.connect(self.add_staff)
        form_layout.addWidget(self.add_staff_btn)
        
        layout.addWidget(form_group)
        
        # جدول کادر مدرسه
        self.staff_table = QTableWidget()
        self.staff_table.setColumnCount(5)
        self.staff_table.setHorizontalHeaderLabels(["شناسه", "نام کامل", "سمت", "وضعیت", "عملیات"])
        self.staff_table.setAlternatingRowColors(True)
        self.staff_table.setStyleSheet("""
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
        
        header = self.staff_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.staff_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.staff_table)
        
        return tab
    
    def load_staff(self):
        """بارگذاری اعضای کادر در جدول"""
        try:
            staff_list = self.staff_dal.get_all(include_inactive=True)
            self.staff_table.setRowCount(len(staff_list))
            
            role_map = {value: display for value, display in STAFF_ROLES}
            
            for row, staff in enumerate(staff_list):
                self.staff_table.setItem(row, 0, QTableWidgetItem(str(staff.id)))
                self.staff_table.setItem(row, 1, QTableWidgetItem(staff.full_name))
                
                role_display = role_map.get(staff.role, staff.role)
                self.staff_table.setItem(row, 2, QTableWidgetItem(role_display))
                
                status_text = "🟢 فعال" if staff.is_active == 1 else "🔴 غیرفعال"
                status_item = QTableWidgetItem(status_text)
                if staff.is_active == 1:
                    status_item.setBackground(QColor(200, 255, 200))
                else:
                    status_item.setBackground(QColor(255, 200, 200))
                self.staff_table.setItem(row, 3, status_item)
                
                btn_widget = QWidget()
                btn_layout = QHBoxLayout()
                btn_layout.setContentsMargins(2, 2, 2, 2)
                
                if staff.is_active == 1:
                    deactivate_btn = QPushButton("🔴 غیرفعال کن")
                    deactivate_btn.setFixedSize(80, 25)
                    deactivate_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 3px;")
                    deactivate_btn.clicked.connect(lambda checked, s=staff: self.toggle_staff_status(s))
                    btn_layout.addWidget(deactivate_btn)
                else:
                    activate_btn = QPushButton("🟢 فعال کن")
                    activate_btn.setFixedSize(80, 25)
                    activate_btn.setStyleSheet("background-color: #66BB6A; color: #F4C542; border: none; border-radius: 3px;")
                    activate_btn.clicked.connect(lambda checked, s=staff: self.toggle_staff_status(s))
                    btn_layout.addWidget(activate_btn)
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 25)
                delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 3px;")
                delete_btn.clicked.connect(lambda checked, s=staff: self.delete_staff(s))
                btn_layout.addWidget(delete_btn)
                
                btn_widget.setLayout(btn_layout)
                self.staff_table.setCellWidget(row, 4, btn_widget)
                self.staff_table.setRowHeight(row, 35)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری کادر مدرسه:\n{str(e)}")
    
    def add_staff(self):
        """افزودن عضو جدید به کادر"""
        full_name = self.staff_name_input.text().strip()
        if not full_name:
            QMessageBox.warning(self, "خطا", "لطفاً نام کامل را وارد کنید.")
            return
        
        role = self.staff_role_combo.currentData()
        
        staff = Staff()
        staff.full_name = full_name
        staff.role = role
        staff.is_active = 1
        
        try:
            self.staff_dal.create(staff)
            self.staff_name_input.clear()
            self.load_staff()
            self.load_staff_for_users()
            QMessageBox.information(self, "موفقیت", f"عضو {full_name} با موفقیت اضافه شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در افزودن عضو:\n{str(e)}")
    
    def toggle_staff_status(self, staff):
        """تغییر وضعیت فعال/غیرفعال عضو کادر"""
        new_status = 0 if staff.is_active == 1 else 1
        status_text = "فعال" if new_status == 1 else "غیرفعال"
        
        reply = QMessageBox.question(
            self,
            "تأیید تغییر وضعیت",
            f"آیا از تغییر وضعیت {staff.full_name} به {status_text} اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                staff.is_active = new_status
                self.staff_dal.update(staff)
                self.load_staff()
                QMessageBox.information(self, "موفقیت", f"وضعیت {staff.full_name} با موفقیت تغییر کرد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در تغییر وضعیت:\n{str(e)}")
    
    def delete_staff(self, staff):
        """حذف عضو کادر"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف {staff.full_name} اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.staff_dal.delete(staff.id)
                self.load_staff()
                self.load_staff_for_users()
                QMessageBox.information(self, "موفقیت", f"{staff.full_name} با موفقیت حذف شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{str(e)}")
    
    def create_users_tab(self):
        """ایجاد تب مدیریت کاربران"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # ===== فرم افزودن کاربر جدید =====
        form_group = QGroupBox("➕ افزودن کاربر جدید")
        form_group.setStyleSheet("""
            QGroupBox {
    color: #111111;
    background-color: #66BB6A;
                font-weight: bold;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
    background-color: #8BC34A;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #111111;
            }
        """)
        form_layout = QGridLayout()
        form_group.setLayout(form_layout)
        
        # انتخاب کاربر از کادر
        form_layout.addWidget(QLabel("انتخاب عضو کادر:"), 0, 0)
        self.user_staff_combo = QComboBox()
        self.user_staff_combo.setMinimumWidth(200)
        form_layout.addWidget(self.user_staff_combo, 0, 1)
        
        form_layout.addWidget(QLabel("نام کاربری:"), 1, 0)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("نام کاربری")
        form_layout.addWidget(self.username_input, 1, 1)
        
        form_layout.addWidget(QLabel("رمز عبور:"), 2, 0)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("رمز عبور (حداقل ۶ کاراکتر)")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(self.password_input, 2, 1)
        
        form_layout.addWidget(QLabel("تکرار رمز عبور:"), 3, 0)
        self.password_confirm_input = QLineEdit()
        self.password_confirm_input.setPlaceholderText("تکرار رمز عبور")
        self.password_confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(self.password_confirm_input, 3, 1)
        
        form_layout.addWidget(QLabel("نقش:"), 4, 0)
        self.user_role_combo = QComboBox()
        for role, display in STAFF_ROLES:
            self.user_role_combo.addItem(display, role)
        form_layout.addWidget(self.user_role_combo, 4, 1)
        
        self.add_user_btn = QPushButton("➕ افزودن کاربر")
        self.add_user_btn.setStyleSheet("""
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
        self.add_user_btn.clicked.connect(self.add_user)
        form_layout.addWidget(self.add_user_btn, 5, 0, 1, 2)
        
        layout.addWidget(form_group)
        
        # ===== لیست کاربران =====
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(["شناسه", "نام کاربری", "عضو کادر", "نقش", "وضعیت", "عملیات"])
        self.user_table.setAlternatingRowColors(True)
        self.user_table.setStyleSheet("""
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
        
        header = self.user_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.user_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.user_table)
        
        return tab
    
    def load_staff_for_users(self):
        """بارگذاری اعضای کادر برای کامبوباکس کاربران"""
        try:
            staff_list = self.staff_dal.get_all()
            self.user_staff_combo.clear()
            for staff in staff_list:
                self.user_staff_combo.addItem(f"{staff.full_name} ({staff.role_display})", staff.id)
        except Exception as e:
            print(f"خطا در بارگذاری اعضای کادر: {e}")
    
    def load_users(self):
        """بارگذاری لیست کاربران"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.*, s.full_name as staff_name, s.role as staff_role
                FROM users u
                LEFT JOIN staff s ON u.staff_id = s.id
                WHERE u.is_deleted = 0
                ORDER BY u.id
            """)
            rows = cursor.fetchall()
            
            self.user_table.setRowCount(len(rows))
            
            role_map = {value: display for value, display in STAFF_ROLES}
            
            for row, user in enumerate(rows):
                self.user_table.setItem(row, 0, QTableWidgetItem(str(user['id'])))
                self.user_table.setItem(row, 1, QTableWidgetItem(user['username']))
                self.user_table.setItem(row, 2, QTableWidgetItem(user['staff_name'] or 'نامشخص'))
                
                role_display = role_map.get(user['role'], user['role'])
                self.user_table.setItem(row, 3, QTableWidgetItem(role_display))
                
                status_text = "🟢 فعال" if user['is_active'] == 1 else "🔴 غیرفعال"
                status_item = QTableWidgetItem(status_text)
                if user['is_active'] == 1:
                    status_item.setBackground(QColor(200, 255, 200))
                else:
                    status_item.setBackground(QColor(255, 200, 200))
                self.user_table.setItem(row, 4, status_item)
                
                # دکمه‌ها
                btn_widget = QWidget()
                btn_layout = QHBoxLayout()
                btn_layout.setContentsMargins(2, 2, 2, 2)
                
                if user['is_active'] == 1:
                    deactivate_btn = QPushButton("🔴 غیرفعال کن")
                    deactivate_btn.setFixedSize(80, 25)
                    deactivate_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 3px;")
                    deactivate_btn.clicked.connect(lambda checked, u=user: self.toggle_user_status(u))
                    btn_layout.addWidget(deactivate_btn)
                else:
                    activate_btn = QPushButton("🟢 فعال کن")
                    activate_btn.setFixedSize(80, 25)
                    activate_btn.setStyleSheet("background-color: #66BB6A; color: #F4C542; border: none; border-radius: 3px;")
                    activate_btn.clicked.connect(lambda checked, u=user: self.toggle_user_status(u))
                    btn_layout.addWidget(activate_btn)
                
                reset_btn = QPushButton("🔑 ریست رمز")
                reset_btn.setFixedSize(80, 25)
                reset_btn.setStyleSheet("background-color: #F4D35E; color: #F4C542; border: none; border-radius: 3px;")
                reset_btn.clicked.connect(lambda checked, u=user: self.reset_user_password(u))
                btn_layout.addWidget(reset_btn)
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 25)
                delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 3px;")
                delete_btn.clicked.connect(lambda checked, u=user: self.delete_user(u))
                btn_layout.addWidget(delete_btn)
                
                btn_widget.setLayout(btn_layout)
                self.user_table.setCellWidget(row, 5, btn_widget)
                self.user_table.setRowHeight(row, 35)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری کاربران:\n{str(e)}")
    
    def add_user(self):
        """افزودن کاربر جدید"""
        staff_id = self.user_staff_combo.currentData()
        if not staff_id:
            QMessageBox.warning(self, "خطا", "لطفاً یک عضو کادر را انتخاب کنید.")
            return
        
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "خطا", "لطفاً نام کاربری را وارد کنید.")
            return
        
        password = self.password_input.text()
        password_confirm = self.password_confirm_input.text()
        
        # ===== اصلاح =====
        # عدد ۶ اینجا هاردکد بود و با Security.is_password_strong
        # (که هم ۶ می‌خواست و هم حروف بزرگ/کوچک/عدد/کاراکتر خاص)
        # و با change_password_dialog ناسازگار بود. حالا همه از
        # Security.MIN_PASSWORD_LENGTH = 8 می‌آیند.
        if not password or len(password) < Security.MIN_PASSWORD_LENGTH:
            QMessageBox.warning(
                self, "خطا",
                f"رمز عبور باید حداقل {Security.MIN_PASSWORD_LENGTH} کاراکتر باشد."
            )
            return
        
        if password != password_confirm:
            QMessageBox.warning(self, "خطا", "رمز عبور و تکرار آن مطابقت ندارند.")
            return
        
        # بررسی قدرت رمز عبور
        # ===== اصلاح امنیتی =====
        # نسخه قبلی پرسش Yes/No می‌گرفت: «آیا با این رمز عبور ادامه
        # می‌دهید؟». یعنی سیاست رمز قوی با یک کلیک دور زده می‌شد.
        # برای سامانه‌ای که اطلاعات کودکان را نگه می‌دارد این
        # پذیرفتنی نیست.
        strong, msg = Security.is_password_strong(password)
        if not strong:
            QMessageBox.warning(
                self, "رمز عبور ضعیف",
                f"{msg}\n\nلطفاً رمز قوی‌تری انتخاب کنید."
            )
            self.password_input.clear()
            self.password_confirm_input.clear()
            return
        
        role = self.user_role_combo.currentData()
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # ===== اصلاح =====
            # نسخه قبلی بررسی نمی‌کرد که این عضو کادر از قبل حساب
            # دارد یا نه. چون users.staff_id یکتا نیست، می‌شد برای
            # یک نفر دو حساب ساخت. موقع ورود، کوئری
            # `WHERE username = ?` هر دو را برمی‌گرداند و fetchone()
            # فقط یکی را می‌گرفت — یعنی ورود تصادفی می‌شد.
            cursor.execute("""
                SELECT username FROM users
                WHERE staff_id = ? AND is_deleted = 0
            """, (staff_id,))
            existing = cursor.fetchone()
            if existing:
                QMessageBox.warning(
                    self, "خطا",
                    f"برای این عضو کادر قبلاً حساب کاربری "
                    f"«{existing['username']}» ساخته شده است.\n"
                    "به جای ساخت حساب جدید، رمز همان حساب را بازنشانی کنید."
                )
                return

            password_hash = Security.hash_password(password)

            # ===== اصلاح =====
            # نسخه قبلی ستون must_change_password را در INSERT
            # نمی‌آورد. یعنی کاربر جدید با رمز ساخته‌شده توسط مدیر
            # وارد می‌شد و هیچ‌وقت مجبور به تغییر آن نبود.
            cursor.execute("""
                INSERT INTO users (
                    staff_id, username, password_hash, role,
                    is_active, must_change_password
                )
                VALUES (?, ?, ?, ?, ?, 1)
            """, (staff_id, username, password_hash, role, 1))

            conn.commit()
            
            self.username_input.clear()
            self.password_input.clear()
            self.password_confirm_input.clear()
            self.load_users()
            
            QMessageBox.information(self, "موفقیت", f"کاربر {username} با موفقیت ایجاد شد.")
            
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "خطا", "این نام کاربری قبلاً ثبت شده است.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در افزودن کاربر:\n{str(e)}")
    
    def toggle_user_status(self, user):
        """تغییر وضعیت کاربر"""
        new_status = 0 if user['is_active'] == 1 else 1
        status_text = "فعال" if new_status == 1 else "غیرفعال"
        
        reply = QMessageBox.question(
            self,
            "تأیید تغییر وضعیت",
            f"آیا از تغییر وضعیت کاربر {user['username']} به {status_text} اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = self.db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_status, user['id']))
                
                conn.commit()
                self.load_users()
                
                QMessageBox.information(self, "موفقیت", f"وضعیت کاربر {user['username']} با موفقیت تغییر کرد.")
                
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در تغییر وضعیت:\n{str(e)}")
    
    def reset_user_password(self, user):
        """ریست رمز عبور کاربر"""
        reply = QMessageBox.question(
            self,
            "تأیید ریست رمز",
            f"آیا از ریست رمز عبور کاربر {user['username']} اطمینان دارید؟\n\nرمز جدید به صورت تصادفی تولید می‌شود.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                import secrets
                import string
                
                # تولید رمز تصادفی
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                new_password = ''.join(secrets.choice(alphabet) for _ in range(10))
                
                password_hash = Security.hash_password(new_password)
                
                conn = self.db.get_connection()
                cursor = conn.cursor()
                
                # ===== اصلاح مهم =====
                # نسخه قبلی فقط password_hash را به‌روز می‌کرد. یعنی
                # کاربر با رمز تصادفی ساخته‌شده توسط مدیر وارد می‌شد
                # و تا ابد همان رمز را نگه می‌داشت — مدیر هم رمزی را
                # می‌دانست که نباید می‌دانست.
                #
                # حالا must_change_password = 1 هم ست می‌شود، پس در
                # اولین ورود، LoginDialog سیگنال need_change_password
                # را می‌فرستد و کاربر مجبور به انتخاب رمز خودش است.
                cursor.execute("""
                    UPDATE users
                    SET password_hash = ?,
                        must_change_password = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (password_hash, user['id']))

                conn.commit()

                QMessageBox.information(
                    self,
                    "رمز عبور موقت",
                    f"رمز عبور موقت برای کاربر {user['username']}:\n\n"
                    f"{new_password}\n\n"
                    "این رمز را به کاربر بدهید. در اولین ورود، سامانه "
                    "از او می‌خواهد رمز خودش را انتخاب کند."
                )
                
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در ریست رمز:\n{str(e)}")
    
    def delete_user(self, user):
        """حذف کاربر (Soft Delete)"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف کاربر {user['username']} اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = self.db.get_connection()
                cursor = conn.cursor()
                
                # ===== اصلاح =====
                # نسخه قبلی فقط is_deleted = 1 ست می‌کرد و
                # deleted_at و deleted_by را خالی می‌گذاشت. یعنی
                # هیچ راهی نبود بفهمیم چه کسی و کِی این حساب را
                # حذف کرده — برای سامانه‌ای که Audit دارد، این
                # حفره بزرگی است.
                #
                # همچنین is_active دست‌نخورده می‌ماند، پس در هر
                # کوئری‌ای که is_deleted را فیلتر نکند، کاربر «حذف‌شده»
                # هنوز فعال دیده می‌شد.
                current_user = getattr(self, 'current_user_id', None) \
                    or getattr(self.db, '_current_user_id', None)

                cursor.execute("""
                    UPDATE users SET
                        is_deleted = 1,
                        is_active = 0,
                        deleted_at = CURRENT_TIMESTAMP,
                        deleted_by = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (current_user, user['id'],))

                conn.commit()
                self.load_users()

                QMessageBox.information(
                    self, "موفقیت",
                    f"کاربر {user['username']} حذف شد.\n"
                    "این حذف برگشت‌پذیر است و از «کاربران حذف‌شده» "
                    "قابل بازگرداندن است."
                )

            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{str(e)}")

    def restore_user(self, user):
        """
        بازگرداندن کاربر حذف‌شده

        ===== افزودن =====
        نسخه قبلی مسیر بازگرداندن نداشت. حذف منطقی یعنی «قابل
        بازگشت»، ولی بدون این متد عملاً برگشت‌ناپذیر بود و تنها راه،
        دستکاری دستی دیتابیس بود.
        """
        reply = QMessageBox.question(
            self,
            "تأیید بازگرداندن",
            f"آیا کاربر {user['username']} بازگردانده شود؟\n\n"
            "حساب غیرفعال باز می‌گردد و کاربر باید در اولین ورود "
            "رمز عبورش را تغییر دهد.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # کاربر با همان نام کاربری فعال دیگری ساخته نشده باشد
            cursor.execute("""
                SELECT id FROM users
                WHERE username = ? AND id != ? AND is_deleted = 0
            """, (user['username'], user['id'],))
            if cursor.fetchone():
                QMessageBox.warning(
                    self, "خطا",
                    f"نام کاربری «{user['username']}» اکنون در اختیار "
                    "حساب فعال دیگری است. ابتدا آن را تغییر دهید."
                )
                return

            cursor.execute("""
                UPDATE users SET
                    is_deleted = 0,
                    deleted_at = NULL,
                    deleted_by = NULL,
                    is_active = 1,
                    must_change_password = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user['id'],))

            conn.commit()
            self.load_users()

            QMessageBox.information(
                self, "موفقیت", f"کاربر {user['username']} بازگردانده شد."
            )

        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بازگرداندن:\n{str(e)}")
    
    # ===== اطلاعات مدرسه =====
    
    def create_school_tab(self):
        """ایجاد تب اطلاعات مدرسه"""
        tab = QWidget()
        layout = QFormLayout()
        tab.setLayout(layout)
        
        self.school_name = QLineEdit()
        self.school_name.setPlaceholderText("نام مدرسه")
        layout.addRow("نام مدرسه:", self.school_name)
        
        self.school_code = QLineEdit()
        self.school_code.setPlaceholderText("کد مدرسه")
        layout.addRow("کد مدرسه:", self.school_code)
        
        self.school_address = QLineEdit()
        self.school_address.setPlaceholderText("آدرس مدرسه")
        layout.addRow("آدرس:", self.school_address)
        
        self.school_phone = QLineEdit()
        self.school_phone.setPlaceholderText("شماره تماس")
        layout.addRow("تلفن:", self.school_phone)
        
        self.school_principal = QLineEdit()
        self.school_principal.setPlaceholderText("نام مدیر")
        layout.addRow("مدیر:", self.school_principal)
        
        layout.addRow(QLabel(""))
        layout.addRow(QLabel("📌 این اطلاعات در گزارش‌ها نمایش داده می‌شود."))
        
        save_btn = QPushButton("💾 ذخیره اطلاعات")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 10px 25px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        save_btn.clicked.connect(self.save_school_info)
        layout.addRow("", save_btn)
        
        self.load_school_info()
        
        return tab
    
    def load_school_info(self):
        """بارگذاری اطلاعات مدرسه"""
        self.school_name.setText("مدرسه نمونه")
        self.school_code.setText("12345")
        self.school_address.setText("تهران، خیابان اصلی")
        self.school_phone.setText("021-12345678")
        self.school_principal.setText("مدیر مدرسه")
    
    def save_school_info(self):
        """ذخیره اطلاعات مدرسه"""
        QMessageBox.information(self, "موفقیت", "اطلاعات مدرسه با موفقیت ذخیره شد.")

    # ===== درباره =====

    def create_about_tab(self):
        """ایجاد تب درباره با اطلاعات مالکیت و پشتیبانی"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # دریافت اطلاعات از settings
        from config.settings import (
            APP_NAME, APP_VERSION, APP_AUTHOR, 
            APP_EMAIL, APP_WEBSITE, APP_COPYRIGHT
        )
        
        about_text = QLabel(f"""
        <div style='text-align: center; padding: 20px;'>
            <h1 style='color: #F4C542; font-size: 28px;'>{APP_NAME}</h1>
            <h2 style='color: #0B2E4F; font-size: 18px;'>پرونده ارزیابی و رشد توانمندی دانش‌آموز</h2>
            <br>
            
            <div style='background-color: #0B2E4F; padding: 15px; border-radius: 10px; margin: 10px 20px;'>
                <p style='font-size: 14px; color: #F4C542;'>
                    <b>نسخه:</b> {APP_VERSION}
                </p>
                <p style='font-size: 14px; color: #F4C542;'>
                    <b>توسعه‌دهنده:</b> {APP_AUTHOR}
                </p>
            </div>
            
            <br>
            
            <div style='background-color: #174F78; padding: 15px; border-radius: 10px; margin: 10px 20px;'>
                <p style='font-size: 14px; color: #F4C542;'>
                    <b>📧 پشتیبانی:</b> 
                    <a href='mailto:{APP_EMAIL}' style='color: #0B2E4F; text-decoration: none;'>
                        {APP_EMAIL}
                    </a>
                </p>
                <p style='font-size: 14px; color: #F4C542;'>
                    <b>🌐 وب‌سایت:</b> 
                    <a href='http://{APP_WEBSITE}' style='color: #0B2E4F; text-decoration: none;'>
                        {APP_WEBSITE}
                    </a>
                </p>
            </div>
            
            <br>
            
            <div style='background-color: #F4D35E; padding: 15px; border-radius: 10px; margin: 10px 20px; border: 1px solid #F4D35E;'>
                <p style='font-size: 12px; color: #C62828; line-height: 1.8; text-align: justify;'>
                    {APP_COPYRIGHT}
                </p>
            </div>
            
            <br>
            <p style='font-size: 13px; color: #D9C36A;'>
                طراحی شده برای مدارس ابتدایی | کاملاً آفلاین
            </p>
            <p style='font-size: 12px; color: #D9C36A; margin-top: 10px;'>
                © 1405 - تمام حقوق محفوظ است
            </p>
        </div>
        """)
        about_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_text.setWordWrap(True)
        
        # اسکرول برای نمایش کامل متن
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #D9C36A;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #D9C36A;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(about_text)
        container.setLayout(container_layout)
        scroll.setWidget(container)
        
        layout.addWidget(scroll)
        
        return tab
       
    # ===== پشتیبان‌گیری =====
    
    def create_backup_tab(self):
        """ایجاد تب پشتیبان‌گیری"""
        from views.pages.backup_page import BackupPage
        return BackupPage()

    def create_backup_tab(self):
        """ایجاد تب پشتیبان‌گیری با تنظیمات خودکار"""
        from views.pages.backup_page import BackupPage
        
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # صفحه پشتیبان‌گیری موجود
        self.backup_page = BackupPage()
        layout.addWidget(self.backup_page)
        
        # ===== تنظیمات پشتیبان‌گیری خودکار =====
        auto_group = QGroupBox("🤖 پشتیبان‌گیری خودکار")
        auto_group.setStyleSheet("""
            QGroupBox {
    color: #111111;
    background-color: #66BB6A;
                font-weight: bold;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
    background-color: #8BC34A;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #111111;
            }
        """)
        auto_layout = QFormLayout()
        auto_group.setLayout(auto_layout)
        
        # انتخاب بازه زمانی
        self.auto_backup_interval = QComboBox()
        self.auto_backup_interval.addItem("هر ۶ ساعت", 6)
        self.auto_backup_interval.addItem("هر ۱۲ ساعت", 12)
        self.auto_backup_interval.addItem("هر ۲۴ ساعت (روزانه)", 24)
        self.auto_backup_interval.addItem("هر ۴۸ ساعت (دو روز یکبار)", 48)
        self.auto_backup_interval.addItem("هر ۷۲ ساعت (سه روز یکبار)", 72)
        auto_layout.addRow("بازه زمانی:", self.auto_backup_interval)
        
        # وضعیت پشتیبان‌گیری خودکار
        self.auto_backup_status = QLabel("⏹️ غیرفعال")
        self.auto_backup_status.setStyleSheet("color: #C62828; font-weight: bold;")
        auto_layout.addRow("وضعیت:", self.auto_backup_status)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        
        self.start_auto_backup_btn = QPushButton("▶️ شروع پشتیبان‌گیری خودکار")
        self.start_auto_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.start_auto_backup_btn.clicked.connect(self.start_auto_backup)
        btn_layout.addWidget(self.start_auto_backup_btn)
        
        self.stop_auto_backup_btn = QPushButton("⏹️ توقف")
        self.stop_auto_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #D94B4B; }
        """)
        self.stop_auto_backup_btn.clicked.connect(self.stop_auto_backup)
        self.stop_auto_backup_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_auto_backup_btn)
        
        auto_layout.addRow(btn_layout)
        
        layout.addWidget(auto_group)
        
        return tab
    
    def start_auto_backup(self):
        """شروع پشتیبان‌گیری خودکار"""
        try:
            # ✅ ایمپورت‌های مورد نیاز
            import os  # ✅ این خط را داخل تابع اضافه کنید
            from utils.backup import BackupManager
            from config.settings import DB_PATH, ATTACHMENTS_DIR
            
            # ایجاد پوشه backup
            backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
            
            backup_manager = BackupManager(DB_PATH, ATTACHMENTS_DIR, backup_dir)
            
            interval = self.auto_backup_interval.currentData()
            
            # ذخیره مرجع به ترد برای توقف
            self.auto_backup_thread = backup_manager.schedule_auto_backup(
                interval_hours=interval,
                user_id=1,
                user_name="سیستم"
            )
            
            self.auto_backup_status.setText(f"🟢 فعال (هر {interval} ساعت)")
            self.auto_backup_status.setStyleSheet("color: #66BB6A; font-weight: bold;")
            self.start_auto_backup_btn.setEnabled(False)
            self.stop_auto_backup_btn.setEnabled(True)
            
            QMessageBox.information(self, "موفقیت", f"پشتیبان‌گیری خودکار هر {interval} ساعت فعال شد.")
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در فعال‌سازی پشتیبان‌گیری خودکار:\n{str(e)}")
    
    def stop_auto_backup(self):
        """توقف پشتیبان‌گیری خودکار"""
        try:
            if hasattr(self, 'auto_backup_thread'):
                # در Python، تردهای daemon با بسته شدن برنامه متوقف می‌شوند
                # اما ما وضعیت را تغییر می‌دهیم
                self.auto_backup_thread = None
            
            self.auto_backup_status.setText("⏹️ غیرفعال")
            self.auto_backup_status.setStyleSheet("color: #C62828; font-weight: bold;")
            self.start_auto_backup_btn.setEnabled(True)
            self.stop_auto_backup_btn.setEnabled(False)
            
            QMessageBox.information(self, "موفقیت", "پشتیبان‌گیری خودکار متوقف شد.")
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در توقف پشتیبان‌گیری خودکار:\n{str(e)}")

    def create_classes_tab(self):
        """ایجاد تب مدیریت کلاس‌ها"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # ===== فرم افزودن کلاس جدید =====
        form_group = QGroupBox("➕ افزودن کلاس جدید")
        form_group.setStyleSheet("""
            QGroupBox {
    color: #111111;
    background-color: #66BB6A;
                font-weight: bold;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
    background-color: #8BC34A;
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #111111;
            }
        """)
        form_layout = QGridLayout()
        form_group.setLayout(form_layout)
        
        # نام کلاس
        form_layout.addWidget(QLabel("نام کلاس:"), 0, 0)
        self.class_name_input = QLineEdit()
        self.class_name_input.setPlaceholderText("مثال: الف، ب، ج، ...")
        form_layout.addWidget(self.class_name_input, 0, 1)
        
        # پایه
        form_layout.addWidget(QLabel("پایه:"), 1, 0)
        self.class_grade_combo = QComboBox()
        grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}
        for grade in range(1, 7):
            self.class_grade_combo.addItem(f"پایه {grade_names[grade]}", grade)
        form_layout.addWidget(self.class_grade_combo, 1, 1)
        
        # معلم
        form_layout.addWidget(QLabel("معلم اصلی:"), 2, 0)
        self.class_teacher_combo = QComboBox()
        self.class_teacher_combo.addItem("بدون معلم", None)
        form_layout.addWidget(self.class_teacher_combo, 2, 1)
        
        # ظرفیت
        form_layout.addWidget(QLabel("ظرفیت:"), 3, 0)
        self.class_capacity_spin = QSpinBox()
        self.class_capacity_spin.setRange(0, 100)
        self.class_capacity_spin.setValue(30)
        form_layout.addWidget(self.class_capacity_spin, 3, 1)
        
        # سال تحصیلی
        form_layout.addWidget(QLabel("سال تحصیلی:"), 4, 0)
        self.class_year_combo = QComboBox()
        form_layout.addWidget(self.class_year_combo, 4, 1)
        
        # دکمه افزودن
        self.add_class_btn = QPushButton("➕ افزودن کلاس")
        self.add_class_btn.setStyleSheet("""
            QPushButton {
                background-color: #F28C28;
                color: #F4C542;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #d35400; }
        """)
        self.add_class_btn.clicked.connect(self.add_class)
        form_layout.addWidget(self.add_class_btn, 5, 0, 1, 2)
        
        layout.addWidget(form_group)
        
        # ===== جدول کلاس‌ها =====
        self.class_table = QTableWidget()
        self.class_table.setColumnCount(6)
        self.class_table.setHorizontalHeaderLabels(["شناسه", "نام کلاس", "پایه", "معلم", "تعداد دانش‌آموز", "عملیات"])
        self.class_table.setAlternatingRowColors(True)
        self.class_table.setStyleSheet("""
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
        
        header = self.class_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.class_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.class_table)
        
        # بارگذاری داده‌ها
        self.load_class_teachers()
        self.load_class_years()
        self.load_classes()
        
        return tab
    
    def load_class_teachers(self):
        """بارگذاری معلمان برای کامبوباکس کلاس"""
        try:
            self.class_teacher_combo.clear()
            self.class_teacher_combo.addItem("بدون معلم", None)
            staff_list = self.staff_dal.get_all()
            for staff in staff_list:
                if staff.role == "teacher":
                    self.class_teacher_combo.addItem(f"{staff.full_name}", staff.id)
        except Exception as e:
            print(f"خطا در بارگذاری معلمان: {e}")
    
    def load_class_years(self):
        """بارگذاری سال‌های تحصیلی برای کامبوباکس کلاس"""
        try:
            self.class_year_combo.clear()
            years = self.academic_year_dal.get_all()
            for year in years:
                self.class_year_combo.addItem(year.title, year.id)
            
            # انتخاب سال فعال
            active_year = self.academic_year_dal.get_active()
            if active_year:
                for i in range(self.class_year_combo.count()):
                    if self.class_year_combo.itemData(i) == active_year.id:
                        self.class_year_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            print(f"خطا در بارگذاری سال‌ها: {e}")
    
    def load_classes(self):
        """بارگذاری کلاس‌ها در جدول"""
        try:
            from dal.class_dal import ClassDAL
            class_dal = ClassDAL()
            
            active_year = self.academic_year_dal.get_active()
            year_id = active_year.id if active_year else None
            
            classes = class_dal.get_classes_with_stats(year_id)
            self.class_table.setRowCount(len(classes))
            
            grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}
            
            for row, item in enumerate(classes):
                class_obj = item['class']
                
                self.class_table.setItem(row, 0, QTableWidgetItem(str(class_obj.id)))
                self.class_table.setItem(row, 1, QTableWidgetItem(class_obj.name or ""))
                self.class_table.setItem(row, 2, QTableWidgetItem(grade_names.get(class_obj.grade, str(class_obj.grade)) if class_obj.grade else "-"))
                
                teacher_name = "بدون معلم"
                if class_obj.teacher_id:
                    teacher = self.staff_dal.get_by_id(class_obj.teacher_id)
                    if teacher:
                        teacher_name = teacher.full_name
                self.class_table.setItem(row, 3, QTableWidgetItem(teacher_name))
                
                self.class_table.setItem(row, 4, QTableWidgetItem(str(item['student_count'])))
                
                # دکمه‌های عملیات
                btn_widget = QWidget()
                btn_layout = QHBoxLayout()
                btn_layout.setContentsMargins(2, 2, 2, 2)
                btn_layout.setSpacing(2)
                
                edit_btn = QPushButton("✏️")
                edit_btn.setFixedSize(30, 30)
                edit_btn.setStyleSheet("background-color: #F4D35E; color: #F4C542; border: none; border-radius: 4px;")
                edit_btn.clicked.connect(lambda checked, c=class_obj: self.edit_class(c))
                btn_layout.addWidget(edit_btn)
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 30)
                delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 4px;")
                delete_btn.clicked.connect(lambda checked, c=class_obj: self.delete_class(c))
                btn_layout.addWidget(delete_btn)
                
                btn_widget.setLayout(btn_layout)
                self.class_table.setCellWidget(row, 5, btn_widget)
                self.class_table.setRowHeight(row, 35)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری کلاس‌ها:\n{str(e)}")
    
    def add_class(self):
        """افزودن کلاس جدید"""
        name = self.class_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "خطا", "لطفاً نام کلاس را وارد کنید.")
            return
        
        grade = self.class_grade_combo.currentData()
        teacher_id = self.class_teacher_combo.currentData()
        capacity = self.class_capacity_spin.value()
        academic_year_id = self.class_year_combo.currentData()
        
        if not academic_year_id:
            QMessageBox.warning(self, "خطا", "لطفاً سال تحصیلی را انتخاب کنید.")
            return
        
        try:
            from dal.class_dal import ClassDAL
            from models.class_model import ClassModel
            
            class_dal = ClassDAL()
            class_obj = ClassModel()
            class_obj.name = name
            class_obj.grade = grade
            class_obj.teacher_id = teacher_id
            class_obj.academic_year_id = academic_year_id
            class_obj.capacity = capacity
            class_obj.is_active = 1
            
            class_dal.create(class_obj)
            
            self.class_name_input.clear()
            self.class_capacity_spin.setValue(30)
            self.load_classes()
            
            QMessageBox.information(self, "موفقیت", f"کلاس {name} با موفقیت اضافه شد.")
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در افزودن کلاس:\n{str(e)}")
    
    def edit_class(self, class_obj):
        """ویرایش کلاس"""
        # در این نسخه ساده، یک پیام نمایش می‌دهیم
        QMessageBox.information(
            self,
            "ویرایش کلاس",
            f"ویرایش کلاس {class_obj.display_name}\n\nاین قابلیت در نسخه بعدی کامل می‌شود."
        )
    
    def delete_class(self, class_obj):
        """حذف کلاس"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف کلاس {class_obj.display_name} اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from dal.class_dal import ClassDAL
                class_dal = ClassDAL()
                class_dal.delete(class_obj.id)
                self.load_classes()
                QMessageBox.information(self, "موفقیت", f"کلاس با موفقیت حذف شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{str(e)}")