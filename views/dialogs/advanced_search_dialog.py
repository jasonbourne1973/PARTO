"""
دیالوگ جستجوی پیشرفته دانش‌آموزان
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QMessageBox, QWidget, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from dal.student_dal import StudentDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from utils.shamsi_date_input import ShamsiDateInput


class AdvancedSearchDialog(QDialog):
    """دیالوگ جستجوی پیشرفته دانش‌آموزان"""
    
    student_selected = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.search_results = []
        
        self.setWindowTitle("🔍 جستجوی پیشرفته دانش‌آموزان")
        self.setModal(True)
        self.resize(750, 550)
        
        self.setup_ui()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # ===== گروه جستجو =====
        search_group = QGroupBox("🔍 معیارهای جستجو")
        search_group.setStyleSheet("""
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
        
        form_layout = QFormLayout()
        search_group.setLayout(form_layout)
        
        # نام
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("نام یا نام خانوادگی...")
        form_layout.addRow("📝 نام:", self.name_input)
        
        # کد ملی
        self.national_code_input = QLineEdit()
        self.national_code_input.setPlaceholderText("کد ملی...")
        self.national_code_input.setMaxLength(10)
        form_layout.addRow("🆔 کد ملی:", self.national_code_input)
        
        # پایه
        self.grade_combo = QComboBox()
        self.grade_combo.addItem("همه پایه‌ها", None)
        grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}
        for grade in range(1, 7):
            self.grade_combo.addItem(f"پایه {grade_names[grade]}", grade)
        form_layout.addRow("📚 پایه:", self.grade_combo)
        
        # کلاس
        self.class_input = QLineEdit()
        self.class_input.setPlaceholderText("مثال: الف، ب، ...")
        form_layout.addRow("🏫 کلاس:", self.class_input)
        
        # تاریخ تولد
        self.birth_date_input = ShamsiDateInput()
        form_layout.addRow("📅 تاریخ تولد:", self.birth_date_input)
        
        main_layout.addWidget(search_group)
        
        # ===== دکمه‌های جستجو =====
        btn_layout = QHBoxLayout()
        
        self.search_btn = QPushButton("🔍 جستجو")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 10px 30px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.search_btn.clicked.connect(self.perform_search)
        btn_layout.addWidget(self.search_btn)
        
        self.clear_btn = QPushButton("🗑️ پاک کردن")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 10px 30px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #D94B4B; }
        """)
        self.clear_btn.clicked.connect(self.clear_search)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)
        
        # ===== نتایج =====
        result_group = QGroupBox("📋 نتایج جستجو")
        result_group.setStyleSheet("""
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
        
        result_layout = QVBoxLayout()
        result_group.setLayout(result_layout)
        
        self.result_count_label = QLabel("تعداد نتایج: 0")
        self.result_count_label.setStyleSheet("color: #D9C36A; font-size: 13px;")
        result_layout.addWidget(self.result_count_label)
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels([
            "ردیف", "نام و نام خانوادگی", "پایه", "کلاس", "کد ملی"
        ])
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setStyleSheet("""
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
        
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.itemDoubleClicked.connect(self.on_result_double_clicked)
        result_layout.addWidget(self.result_table)
        
        main_layout.addWidget(result_group)
    
    def perform_search(self):
        """اجرای جستجوی پیشرفته"""
        try:
            # دریافت معیارهای جستجو
            name = self.name_input.text().strip()
            national_code = self.national_code_input.text().strip()
            grade = self.grade_combo.currentData()
            class_name = self.class_input.text().strip()
            birth_date = self.birth_date_input.get_date_string()
            
            # اگر هیچ معیاری وارد نشده
            if not any([name, national_code, grade, class_name, birth_date]):
                QMessageBox.warning(self, "توجه", "لطفاً حداقل یک معیار جستجو را وارد کنید.")
                return
            
            # اجرای جستجو
            self.search_results = self.student_dal.advanced_search(
                name=name,
                national_code=national_code,
                grade=grade,
                class_name=class_name,
                birth_date=birth_date
            )
            
            # نمایش نتایج
            self.display_results(self.search_results)
            
            if self.search_results:
                QMessageBox.information(self, "نتیجه", f"{len(self.search_results)} دانش‌آموز پیدا شد.")
            else:
                QMessageBox.information(self, "نتیجه", "هیچ دانش‌آموزی با این معیارها یافت نشد.")
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در جستجو:\n{str(e)}")
    
    def display_results(self, results):
        """نمایش نتایج جستجو"""
        self.result_table.setRowCount(len(results))
        self.result_count_label.setText(f"تعداد نتایج: {len(results)}")
        
        grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}
        
        for row, student in enumerate(results):
            # دریافت اطلاعات پرونده
            profile = self.profile_dal.get_active_by_student(student.id)
            grade_text = profile.grade_display if profile else "-"
            class_text = profile.class_name if profile else "-"
            
            self.result_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.result_table.setItem(row, 1, QTableWidgetItem(student.full_name))
            self.result_table.setItem(row, 2, QTableWidgetItem(grade_text))
            self.result_table.setItem(row, 3, QTableWidgetItem(class_text))
            self.result_table.setItem(row, 4, QTableWidgetItem(student.national_code or ""))
            self.result_table.setRowHeight(row, 30)
    
    def on_result_double_clicked(self, item):
        """وقتی روی یک نتیجه دابل‌کلیک می‌شود"""
        row = item.row()
        if row < len(self.search_results):
            student = self.search_results[row]
            self.student_selected.emit(student.id)
            self.accept()
    
    def clear_search(self):
        """پاک کردن همه فیلدها"""
        self.name_input.clear()
        self.national_code_input.clear()
        self.grade_combo.setCurrentIndex(0)
        self.class_input.clear()
        self.birth_date_input.clear()
        self.result_table.setRowCount(0)
        self.result_count_label.setText("تعداد نتایج: 0")
        self.search_results = []