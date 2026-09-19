"""
صفحه مدیریت دانش‌آموزان - نسخه با جستجوی سریع و پیشرفته و Pagination
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from dal.academic_year_dal import AcademicYearDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from utils.time_utils import utc_now
from views.dialogs.student_form import StudentForm
from views.pages.student_profile_page import StudentProfilePage


class StudentsPage(QWidget):
    """صفحه مدیریت دانش‌آموزان با جستجوی سریع و پیشرفته و Pagination"""
    
    student_double_clicked = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.academic_year_dal = AcademicYearDAL()
        
        self.students = []
        self.all_students = []
        self.current_page = 0
        self.page_size = 20
        self.total_pages = 1
        
        self.setup_ui()
        self.load_students()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        title_label = QLabel("📋 دانش‌آموزان")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #F4C542;
            }
        """)
        main_layout.addWidget(title_label)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
    color: #111111;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                background-color: #66BB6A;
            }
            QTabBar::tab {
    color: #111111;
    border: 1px solid #8BC34A;
    background-color: #66BB6A;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QTabBar::tab:selected {
    border-color: #F4C542;
                background-color: #8BC34A;
                color: #111111;
            }
        """)
        
        list_tab = QWidget()
        layout = QVBoxLayout()
        list_tab.setLayout(layout)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        toolbar.addStretch()
        
        # ===== جعبه جستجو =====
        search_label = QLabel("🔍 جستجو:")
        search_label.setStyleSheet("font-weight: bold;")
        toolbar.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("نام، نام خانوادگی، کد ملی...")
        self.search_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                padding: 8px;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                font-size: 13px;
                min-width: 200px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F;
                border: 2px solid #F4C542;
            }
        """)
        self.search_input.textChanged.connect(self.search_students)
        toolbar.addWidget(self.search_input)
        
        # دکمه جستجوی پیشرفته
        self.advanced_search_btn = QPushButton("🔍 پیشرفته")
        self.advanced_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #66BB6A; }
        """)
        self.advanced_search_btn.clicked.connect(self.open_advanced_search)
        toolbar.addWidget(self.advanced_search_btn)
        
        self.add_btn = QPushButton("➕ افزودن دانش‌آموز")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #08223A;
            }
        """)
        self.add_btn.clicked.connect(self.add_student)
        toolbar.addWidget(self.add_btn)
        
        # ===== دکمه‌های ایمپورت و اکسل (جدید) =====
        self.import_btn = QPushButton("📥 ایمپورت از Excel")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8BC34A;
            }
        """)
        self.import_btn.clicked.connect(self.import_from_excel)
        toolbar.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("📤 خروجی Excel")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #08223A;
            }
        """)
        self.export_btn.clicked.connect(self.export_to_excel)
        toolbar.addWidget(self.export_btn)
        
        self.sample_btn = QPushButton("📄 دریافت نمونه")
        self.sample_btn.setStyleSheet("""
            QPushButton {
                background-color: #F4D35E;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F28C28;
            }
        """)
        self.sample_btn.clicked.connect(self.download_sample_excel)
        toolbar.addWidget(self.sample_btn)
        
        layout.addLayout(toolbar)
        
        # ===== جدول =====
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ردیف", "نام", "نام خانوادگی", "پایه", "کلاس",
            "کد ملی", "عملیات"
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
    background-color: #0B2E4F;
                padding: 8px;
            }
            QTableWidget::item:hover {
    color: #FFE8A3;
                background-color: #174F78;
            }
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
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.table)
        
        # ===== بخش Pagination =====
        pagination_layout = QHBoxLayout()
        
        self.page_label = QLabel("صفحه 1 از 1")
        self.page_label.setStyleSheet("font-size: 13px; color: #D9C36A;")
        pagination_layout.addWidget(self.page_label)
        
        pagination_layout.addStretch()
        
        self.prev_page_btn = QPushButton("◀ قبلی")
        self.prev_page_btn.setFixedWidth(80)
        self.prev_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 5px 10px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #08223A; }
            QPushButton:disabled { background-color: #D9C36A; }
        """)
        self.prev_page_btn.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_page_btn)
        
        self.next_page_btn = QPushButton("بعدی ▶")
        self.next_page_btn.setFixedWidth(80)
        self.next_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 5px 10px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #08223A; }
            QPushButton:disabled { background-color: #D9C36A; }
        """)
        self.next_page_btn.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_page_btn)
        
        pagination_layout.addWidget(QLabel("تعداد در صفحه:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "20", "50", "100"])
        self.page_size_combo.setCurrentText("20")
        self.page_size_combo.currentTextChanged.connect(self.load_students)
        pagination_layout.addWidget(self.page_size_combo)
        
        layout.addLayout(pagination_layout)
        
        self.tabs.addTab(list_tab, "📋 لیست دانش‌آموزان")
        
        self.profile_page = StudentProfilePage()
        self.tabs.addTab(self.profile_page, "👤 پرونده دانش‌آموز")
        
        main_layout.addWidget(self.tabs)
    
    def open_profile_tab(self, student_id):
        """باز کردن تب پرونده دانش‌آموز"""
        self.profile_page.set_student_id(student_id)
        self.tabs.setCurrentIndex(1)
    
    def load_students(self):
        """بارگذاری لیست دانش‌آموزان با Pagination"""
        try:
            self.page_size = int(self.page_size_combo.currentText())
            self.all_students = self.student_dal.get_all()
            self.total_pages = (len(self.all_students) + self.page_size - 1) // self.page_size
            self.current_page = min(self.current_page, self.total_pages - 1)
            if self.current_page < 0:
                self.current_page = 0
            
            start = self.current_page * self.page_size
            end = min(start + self.page_size, len(self.all_students))
            self.students = self.all_students[start:end]
            
            self.display_students(self.students)
            self.update_pagination_controls()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری دانش‌آموزان:\n{str(e)}")
    
    def update_pagination_controls(self):
        """به‌روزرسانی کنترل‌های Pagination"""
        self.page_label.setText(f"صفحه {self.current_page + 1} از {max(1, self.total_pages)}")
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)
    
    def prev_page(self):
        """رفتن به صفحه قبل"""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_students()
    
    def next_page(self):
        """رفتن به صفحه بعد"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.load_students()
    
    def get_student_info(self, student_id):
        """دریافت اطلاعات پرونده فعال دانش‌آموز"""
        try:
            profile = self.profile_dal.get_active_by_student(student_id)
            if profile:
                return {
                    'grade': profile.grade_display,
                    'class': profile.class_name or ''
                }
        except Exception:
            pass
        return {'grade': '-', 'class': '-'}
    
    def display_students(self, students):
        """نمایش دانش‌آموزان در جدول"""
        self.table.setRowCount(len(students))
        
        for row, student in enumerate(students):
            info = self.get_student_info(student.id)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(student.first_name or ""))
            self.table.setItem(row, 2, QTableWidgetItem(student.last_name or ""))
            self.table.setItem(row, 3, QTableWidgetItem(info['grade']))
            self.table.setItem(row, 4, QTableWidgetItem(info['class']))
            self.table.setItem(row, 5, QTableWidgetItem(student.national_code or ""))
            
            # دکمه‌های عملیات
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(2)
            
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F4D35E;
                    color: #F4C542;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #F28C28;
                }
            """)
            edit_btn.clicked.connect(lambda checked, s=student: self.edit_student(s))
            btn_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #C62828;
                    color: #F4C542;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #9E1B1B;
                }
            """)
            delete_btn.clicked.connect(lambda checked, s=student: self.delete_student(s))
            btn_layout.addWidget(delete_btn)
            
            profile_btn = QPushButton("👤")
            profile_btn.setFixedSize(30, 30)
            profile_btn.setStyleSheet("""
                QPushButton {
                    background-color: #66BB6A;
                    color: #F4C542;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #7d3c98;
                }
            """)
            profile_btn.clicked.connect(lambda checked, s=student: self.open_profile(s))
            btn_layout.addWidget(profile_btn)
            
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 6, btn_widget)
            self.table.setRowHeight(row, 40)
    
    def search_students(self):
        """جستجوی دانش‌آموزان با Pagination"""
        search_term = self.search_input.text().strip()
        
        if not search_term:
            self.load_students()
            return
        
        try:
            self.all_students = self.student_dal.search(search_term)
            self.total_pages = (len(self.all_students) + self.page_size - 1) // self.page_size
            self.current_page = 0
            
            start = self.current_page * self.page_size
            end = min(start + self.page_size, len(self.all_students))
            self.students = self.all_students[start:end]
            
            self.display_students(self.students)
            self.update_pagination_controls()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در جستجو:\n{str(e)}")
    
    def open_advanced_search(self):
        """باز کردن دیالوگ جستجوی پیشرفته"""
        from views.dialogs.advanced_search_dialog import AdvancedSearchDialog
        dialog = AdvancedSearchDialog(self)
        dialog.student_selected.connect(self.open_profile_by_id)
        dialog.exec()
    
    def open_profile_by_id(self, student_id):
        """باز کردن پرونده دانش‌آموز با شناسه"""
        self.student_double_clicked.emit(student_id)
    
    def on_item_double_clicked(self, item):
        """باز کردن پرونده دانش‌آموز با دابل‌کلیک"""
        row = item.row()
        if row < len(self.students):
            student = self.students[row]
            self.open_profile(student)
    
    def open_profile(self, student):
        """باز کردن پرونده دانش‌آموز"""
        self.student_double_clicked.emit(student.id)
    
    def add_student(self):
        """افزودن دانش‌آموز جدید - باز کردن فرم ثبت"""
        try:
            form = StudentForm(parent=self)
            result = form.exec()
            if result == QDialog.DialogCode.Accepted:
                self.load_students()
                QMessageBox.information(self, "موفقیت", "دانش‌آموز با موفقیت ثبت شد")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در باز کردن فرم:\n{str(e)}")
    
    def edit_student(self, student):
        """ویرایش دانش‌آموز"""
        form = StudentForm(student=student, parent=self)
        if form.exec() == QDialog.DialogCode.Accepted:
            self.load_students()
            QMessageBox.information(self, "موفقیت", "دانش‌آموز با موفقیت ویرایش شد")
    
    def delete_student(self, student):
        """حذف دانش‌آموز"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف دانش‌آموز '{student.full_name}' اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.student_dal.delete(student.id)
                self.load_students()
                QMessageBox.information(self, "موفقیت", "دانش‌آموز با موفقیت حذف شد")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{str(e)}")
    
    # ===== متدهای جدید برای Excel =====
    
    def export_to_excel(self):
        """خروجی Excel از دانش‌آموزان"""
        if not self.students:
            QMessageBox.warning(self, "توجه", "هیچ دانش‌آموزی برای خروجی وجود ندارد.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل Excel",
            f"دانش‌آموزان_{utc_now().strftime('%Y%m%d')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            from utils.excel_importer import ExcelImporter
            importer = ExcelImporter()
            
            active_year = self.academic_year_dal.get_active()
            success, message = importer.export_students_to_excel(
                self.students, file_path, active_year
            )
            
            if success:
                QMessageBox.information(self, "موفقیت", message)
            else:
                QMessageBox.critical(self, "خطا", message)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در خروجی:\n{str(e)}")
    
    def import_from_excel(self):
        """ایمپورت دانش‌آموزان از Excel"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب فایل Excel",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if not file_path:
            return
        
        # انتخاب سال تحصیلی
        years = self.academic_year_dal.get_all()
        if not years:
            QMessageBox.warning(self, "توجه", "هیچ سال تحصیلی فعالی وجود ندارد. لطفاً ابتدا یک سال ایجاد کنید.")
            return
        
        # دیالوگ ساده برای انتخاب سال
        dialog = QDialog(self)
        dialog.setWindowTitle("انتخاب سال تحصیلی")
        dialog.setModal(True)
        dialog_layout = QVBoxLayout()
        
        dialog_layout.addWidget(QLabel("لطفاً سال تحصیلی را انتخاب کنید:"))
        year_combo = QComboBox()
        for year in years:
            year_combo.addItem(year.title, year.id)
        dialog_layout.addWidget(year_combo)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        dialog_layout.addWidget(button_box)
        
        dialog.setLayout(dialog_layout)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        year_id = year_combo.currentData()
        
        try:
            from utils.excel_importer import ExcelImporter
            importer = ExcelImporter()
            
            # ایمپورت
            success, message, imported_count, errors = importer.import_students_from_excel(
                file_path, year_id
            )
            
            if success:
                self.load_students()
                msg = message
                if errors:
                    # نمایش ۱۰ خطای اول
                    error_text = "\n".join(errors[:10])
                    if len(errors) > 10:
                        error_text += f"\n... و {len(errors)-10} خطای دیگر"
                    msg += f"\n\nخطاها:\n{error_text}"
                
                QMessageBox.information(self, "نتیجه ایمپورت", msg)
            else:
                QMessageBox.critical(self, "خطا", message)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در ایمپورت:\n{str(e)}")
    
    def download_sample_excel(self):
        """دانلود فایل نمونه Excel"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل نمونه",
            "نمونه_دانش‌آموزان.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            from utils.excel_importer import ExcelImporter
            importer = ExcelImporter()
            success, message = importer.create_sample_excel(file_path)
            
            if success:
                QMessageBox.information(self, "موفقیت", message)
            else:
                QMessageBox.critical(self, "خطا", message)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در ایجاد فایل نمونه:\n{str(e)}")