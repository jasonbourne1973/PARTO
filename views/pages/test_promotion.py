"""
فایل تست ساده برای پیدا کردن مشکل دکمه‌ها
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
    QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from dal.student_dal import StudentDAL


class TestPromotionPage(QWidget):
    """صفحه تست برای پیدا کردن مشکل"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.student_dal = StudentDAL()
        self.students = []
        self.selected_student_ids = []
        
        self.setup_ui()
        self.load_students()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # عنوان
        title_label = QLabel("🧪 صفحه تست ارتقاء پایه")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #e74c3c; }")
        layout.addWidget(title_label)
        
        # ===== گروه تست دکمه‌ها =====
        test_group = QGroupBox("🟢 تست دکمه‌ها")
        test_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #e74c3c;
            }
        """)
        test_layout = QHBoxLayout(test_group)
        
        # دکمه شماره 1: پیام ساده
        self.test_btn_1 = QPushButton("🔴 تست 1 - پیام ساده")
        self.test_btn_1.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        self.test_btn_1.clicked.connect(self.test_simple_message)
        test_layout.addWidget(self.test_btn_1)
        
        # دکمه شماره 2: تعداد دانش‌آموزان
        self.test_btn_2 = QPushButton("🟡 تست 2 - تعداد دانش‌آموزان")
        self.test_btn_2.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        self.test_btn_2.clicked.connect(self.test_student_count)
        test_layout.addWidget(self.test_btn_2)
        
        # دکمه شماره 3: ارتقاء همه
        self.test_btn_3 = QPushButton("🟢 تست 3 - ارتقاء همه (با لاگ)")
        self.test_btn_3.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        self.test_btn_3.clicked.connect(self.test_promote_all)
        test_layout.addWidget(self.test_btn_3)
        
        layout.addWidget(test_group)
        
        # ===== جدول دانش‌آموزان =====
        table_label = QLabel("📋 لیست دانش‌آموزان (برای تست انتخاب)")
        table_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(table_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "✅", "ردیف", "نام و نام خانوادگی", "پایه", "کلاس"
        ])
        
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #dee2e6;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemClicked.connect(self.on_item_clicked)
        
        layout.addWidget(self.table)
    
    def load_students(self):
        """بارگذاری لیست دانش‌آموزان"""
        try:
            print("🔄 در حال بارگذاری دانش‌آموزان...")
            self.students = self.student_dal.get_all()
            print(f"✅ {len(self.students)} دانش‌آموز بارگذاری شد")
            self.display_students(self.students)
        except Exception as e:
            print(f"❌ خطا در بارگذاری: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری:\n{str(e)}")
    
    def display_students(self, students):
        """نمایش دانش‌آموزان در جدول"""
        self.table.setRowCount(len(students))
        grade_names = {1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم", 6: "ششم"}
        
        for row, student in enumerate(students):
            check_item = QTableWidgetItem("☐")
            check_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            check_item.setData(Qt.ItemDataRole.UserRole, student.id)
            self.table.setItem(row, 0, check_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(str(row + 1)))
            self.table.setItem(row, 2, QTableWidgetItem(student.full_name))
            self.table.setItem(row, 3, QTableWidgetItem(grade_names.get(student.grade, str(student.grade))))
            self.table.setItem(row, 4, QTableWidgetItem(student.class_name or ""))
            self.table.setRowHeight(row, 35)
    
    def on_item_clicked(self, item):
        """انتخاب/لغو انتخاب دانش‌آموز با پرینت در کنسول"""
        row = item.row()
        if row >= len(self.students):
            return
        
        student = self.students[row]
        check_item = self.table.item(row, 0)
        
        if check_item.text() == "☐":
            check_item.setText("☑")
            if student.id not in self.selected_student_ids:
                self.selected_student_ids.append(student.id)
                print(f"✅ {student.full_name} انتخاب شد")
        else:
            check_item.setText("☐")
            if student.id in self.selected_student_ids:
                self.selected_student_ids.remove(student.id)
                print(f"❌ {student.full_name} لغو انتخاب شد")
        
        print(f"📊 تعداد انتخاب‌شده: {len(self.selected_student_ids)}")
    
    # ============================================================
    # توابع تست
    # ============================================================
    
    def test_simple_message(self):
        """تست 1: نمایش پیام ساده"""
        print("🔴 دکمه تست 1 کلیک شد")
        QMessageBox.information(self, "تست 1", "✅ این یک پیام تست ساده است.\nدکمه به درستی کار می‌کند.")
    
    def test_student_count(self):
        """تست 2: نمایش تعداد دانش‌آموزان"""
        print("🟡 دکمه تست 2 کلیک شد")
        count = len(self.students)
        selected = len(self.selected_student_ids)
        QMessageBox.information(
            self, 
            "تست 2", 
            f"📊 تعداد دانش‌آموزان: {count}\n✅ تعداد انتخاب‌شده: {selected}"
        )
    
    def test_promote_all(self):
        """تست 3: ارتقاء همه با نمایش لاگ در کنسول"""
        print("🟢 دکمه تست 3 کلیک شد")
        
        if not self.students:
            QMessageBox.warning(self, "توجه", "هیچ دانش‌آموزی وجود ندارد.")
            return
        
        reply = QMessageBox.question(
            self,
            "تأیید ارتقاء",
            f"آیا از ارتقاء {len(self.students)} دانش‌آموز اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            print("❌ کاربر انصراف داد")
            return
        
        success_count = 0
        try:
            for student in self.students:
                print(f"🔄 در حال ارتقاء: {student.full_name} (پایه {student.grade})")
                if student.grade < 6:
                    student.grade = student.grade + 1
                    self.student_dal.update(student)
                    success_count += 1
                    print(f"✅ {student.full_name} به پایه {student.grade} ارتقاء یافت")
                else:
                    student.is_active = 0
                    self.student_dal.update(student)
                    success_count += 1
                    print(f"🎓 {student.full_name} فارغ‌التحصیل شد")
            
            QMessageBox.information(self, "موفقیت", f"✅ {success_count} دانش‌آموز ارتقاء یافتند.")
            self.load_students()
            
        except Exception as e:
            print(f"❌ خطا: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در ارتقاء:\n{str(e)}")