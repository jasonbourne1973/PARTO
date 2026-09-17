"""
ویجت ورودی تاریخ شمسی با QLineEdit
"""

from PySide6.QtWidgets import QLineEdit, QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator

from utils.persian_date import PersianDate


class ShamsiDateInput(QWidget):
    """ویجت ورودی تاریخ شمسی با سه فیلد جداگانه"""
    
    dateChanged = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setup_ui()
        self.set_today()
    
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # فیلد سال
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("سال")
        self.year_input.setFixedWidth(60)
        self.year_input.setValidator(QIntValidator(1300, 1500))
        self.year_input.textChanged.connect(self.on_date_changed)
        layout.addWidget(self.year_input)
        
        # جداکننده
        layout.addWidget(self.create_separator())
        
        # فیلد ماه
        self.month_input = QLineEdit()
        self.month_input.setPlaceholderText("ماه")
        self.month_input.setFixedWidth(50)
        self.month_input.setValidator(QIntValidator(1, 12))
        self.month_input.textChanged.connect(self.on_date_changed)
        layout.addWidget(self.month_input)
        
        # جداکننده
        layout.addWidget(self.create_separator())
        
        # فیلد روز
        self.day_input = QLineEdit()
        self.day_input.setPlaceholderText("روز")
        self.day_input.setFixedWidth(50)
        self.day_input.setValidator(QIntValidator(1, 31))
        self.day_input.textChanged.connect(self.on_date_changed)
        layout.addWidget(self.day_input)
        
        # دکمه امروز
        self.today_btn = QPushButton("امروز")
        self.today_btn.setFixedWidth(50)
        self.today_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.today_btn.clicked.connect(self.set_today)
        layout.addWidget(self.today_btn)
        
        self.setLayout(layout)
    
    def create_separator(self):
        """ایجاد جداکننده بین فیلدها"""
        sep = QLineEdit()
        sep.setFixedWidth(10)
        sep.setReadOnly(True)
        sep.setText("/")
        sep.setStyleSheet("border: none; background: transparent; color: #2c3e50; font-weight: bold;")
        return sep
    
    def on_date_changed(self):
        """وقتی تاریخ تغییر می‌کند"""
        self.dateChanged.emit(self.get_date_string())
    
    def set_today(self):
        """تنظیم تاریخ امروز"""
        today = PersianDate.get_today()
        parts = today.split('/')
        self.year_input.setText(parts[0])
        self.month_input.setText(parts[1])
        self.day_input.setText(parts[2])
    
    def get_date_string(self):
        """دریافت تاریخ به صورت رشته yyyy/MM/dd"""
        year = self.year_input.text().strip()
        month = self.month_input.text().strip()
        day = self.day_input.text().strip()
        
        if not year or not month or not day:
            return ""
        
        # فرمت کردن با صفر
        year = year.zfill(4)
        month = month.zfill(2)
        day = day.zfill(2)
        
        return f"{year}/{month}/{day}"
    
    def get_date(self):
        """دریافت تاریخ به صورت رشته (همان get_date_string)"""
        return self.get_date_string()
    
    def set_date(self, date_str):
        """تنظیم تاریخ از رشته"""
        if not date_str:
            return
        
        parts = date_str.split('/')
        if len(parts) == 3:
            self.year_input.setText(parts[0])
            self.month_input.setText(parts[1])
            self.day_input.setText(parts[2])
    
    def is_valid(self):
        """بررسی اعتبار تاریخ"""
        date_str = self.get_date_string()
        return PersianDate.is_valid_persian_date(date_str)
    
    def clear(self):
        """پاک کردن تاریخ"""
        self.year_input.clear()
        self.month_input.clear()
        self.day_input.clear()