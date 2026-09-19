"""
ویجت تقویم شمسی کامل و ابزارهای گروه‌بندی زمانی
"""

from collections import defaultdict

import jdatetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.time_utils import utc_now


class TimeGrouper:
    """
    ابزار گروه‌بندی زمانی برای تحلیل روند
    
    این کلاس در سطح ماژول تعریف شده است تا در سراسر برنامه قابل استفاده باشد.
    """
    
    @staticmethod
    def get_month_key(date_str):
        """دریافت کلید ماه از تاریخ شمسی"""
        if not date_str:
            return None
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                return f"{parts[0]}/{parts[1]}"
        except (AttributeError, IndexError, TypeError):
            # ورودی نامعتبر (مثلاً None) → کلید ندارد
            pass
        return None
    
    @staticmethod
    def get_week_key(date_str):
        """دریافت کلید هفته از تاریخ شمسی"""
        if not date_str:
            return None
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                week_num = (day - 1) // 7 + 1
                return f"{year}/{month:02d}/W{week_num}"
        except (ValueError, IndexError, TypeError):
            # اجزای تاریخ عددی نیستند → کلید هفته ساخته نمی‌شود
            pass
        return None
    
    @staticmethod
    def get_day_key(date_str):
        """دریافت کلید روز از تاریخ شمسی"""
        if not date_str:
            return None
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                return f"{parts[0]}/{parts[1]}/{parts[2]}"
        except (AttributeError, IndexError, TypeError):
            # ورودی نامعتبر (None/عدد) → کلید روز ساخته نمی‌شود
            pass
        return None
    
    @staticmethod
    def get_month_label(month_key):
        """دریافت برچسب فارسی ماه — منبع واحد: utils.persian_date"""
        if not month_key:
            return ""
        from utils.persian_date import PersianDate
        return PersianDate.get_month_label(month_key)
    
    @staticmethod
    def get_week_label(week_key):
        """دریافت برچسب فارسی هفته"""
        if not week_key:
            return ""
        try:
            parts = week_key.split('/')
            if len(parts) == 3:
                week_num = parts[2].replace('W', '')
                month_num = int(parts[1])
                if 1 <= month_num <= 12:
                    from utils.persian_date import PersianDate
                    return f"هفته {week_num} {PersianDate.month_name(month_num)}"
        except (ValueError, IndexError, TypeError):
            # کلید هفتهٔ نامعتبر → همان کلید خام برگردانده می‌شود
            pass
        return week_key
    
    @staticmethod
    def group_by_time(items, date_field, period='monthly'):
        """
        گروه‌بندی آیتم‌ها بر اساس زمان
        
        Args:
            items: لیست آیتم‌ها
            date_field: نام فیلد تاریخ در آیتم‌ها
            period: 'monthly', 'weekly', 'daily'
            
        Returns:
            dict: گروه‌بندی شده
        """
        grouped = defaultdict(list)
        
        for item in items:
            date_str = getattr(item, date_field, None)
            if not date_str:
                continue
            
            if period == 'monthly':
                key = TimeGrouper.get_month_key(date_str)
            elif period == 'weekly':
                key = TimeGrouper.get_week_key(date_str)
            else:  # daily
                key = TimeGrouper.get_day_key(date_str)
            
            if key:
                grouped[key].append(item)
        
        # مرتب‌سازی کلیدها
        sorted_keys = sorted(grouped.keys())
        return {key: grouped[key] for key in sorted_keys}


class PersianCalendarWidget(QWidget):
    """ویجت تقویم شمسی کامل"""
    
    dateSelected = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_year = None
        self.current_month = None
        self.selected_day = None
        
        self.setup_ui()
        self.set_today()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== هدر =====
        header_layout = QHBoxLayout()
        
        self.prev_month_btn = QPushButton("◀")
        self.prev_month_btn.setFixedSize(30, 30)
        self.prev_month_btn.clicked.connect(self.prev_month)
        header_layout.addWidget(self.prev_month_btn)
        
        self.month_year_label = QLabel("")
        self.month_year_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_year_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self.month_year_label)
        
        self.next_month_btn = QPushButton("▶")
        self.next_month_btn.setFixedSize(30, 30)
        self.next_month_btn.clicked.connect(self.next_month)
        header_layout.addWidget(self.next_month_btn)
        
        layout.addLayout(header_layout)
        
        # ===== روزهای هفته =====
        weekdays_layout = QHBoxLayout()
        weekdays = ["ش", "ی", "د", "س", "چ", "پ", "ج"]
        for day in weekdays:
            label = QLabel(day)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-weight: bold; color: #7f8c8d;")
            weekdays_layout.addWidget(label)
        layout.addLayout(weekdays_layout)
        
        # ===== شبکه روزها =====
        self.days_grid = QGridLayout()
        self.days_grid.setSpacing(2)
        layout.addLayout(self.days_grid)
        
        # ===== دکمه امروز =====
        today_btn = QPushButton("📍 امروز")
        today_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 5px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        today_btn.clicked.connect(self.set_today)
        layout.addWidget(today_btn)
    
    def set_today(self):
        """تنظیم به تاریخ امروز"""
        try:
            today = jdatetime.date.today()
            self.current_year = today.year
            self.current_month = today.month
            self.selected_day = today.day
        except Exception:
            # Fallback: تبدیل تقویمی میلادی → شمسی روی «تاریخ محلی»؛
            # اگر از UTC استفاده شود، بین ۰۰:۰۰ تا ۰۳:۳۰ بامداد یک روز
            # عقب می‌افتد (بازرسی هشتم).
            now = utc_now().astimezone()
            self.current_year = now.year - 621
            self.current_month = now.month
            self.selected_day = now.day
        
        self.update_calendar()
        self.dateSelected.emit(self.get_selected_date())
    
    def set_date(self, date_str):
        """تنظیم تاریخ از رشته"""
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                self.current_year = int(parts[0])
                self.current_month = int(parts[1])
                self.selected_day = int(parts[2])
                self.update_calendar()
                return True
        except (ValueError, IndexError, TypeError):
            # تاریخ نامعتبر برای ویجت → انتخاب تغییر نمی‌کند
            pass
        return False
    
    def get_selected_date(self):
        """دریافت تاریخ انتخاب شده به صورت رشته"""
        if self.selected_day:
            return f"{self.current_year:04d}/{self.current_month:02d}/{self.selected_day:02d}"
        return ""
    
    def update_calendar(self):
        """به‌روزرسانی نمایش تقویم"""
        # پاک کردن شبکه
        for i in reversed(range(self.days_grid.count())):
            widget = self.days_grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # بروزرسانی عنوان
        from utils.persian_date import PersianDate
        self.month_year_label.setText(
            f"{PersianDate.month_name(self.current_month)} {self.current_year}")
        
        # محاسبه روز اول ماه
        try:
            first_day = jdatetime.date(self.current_year, self.current_month, 1)
            first_weekday = first_day.weekday()  # 0=شنبه, 6=جمعه
        except Exception:
            first_weekday = 0
        
        # تعداد روزهای ماه
        try:
            if self.current_month <= 6:
                days_in_month = 31
            elif self.current_month <= 11:
                days_in_month = 30
            else:
                # اسفند - 29 روز (کبیسه‌گیری ساده)
                days_in_month = 29
        except Exception:
            days_in_month = 30
        
        # ایجاد دکمه‌های روزها
        row = 0
        col = first_weekday
        
        for day in range(1, days_in_month + 1):
            btn = QPushButton(str(day))
            btn.setFixedSize(35, 35)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #bdc3c7;
                    border-radius: 5px;
                    background-color: white;
                }
                QPushButton:hover {
                    background-color: #e8f0fe;
                }
                QPushButton:pressed {
                    background-color: #3498db;
                    color: white;
                }
            """)
            
            if day == self.selected_day:
                btn.setStyleSheet("""
                    QPushButton {
                        border: 2px solid #3498db;
                        border-radius: 5px;
                        background-color: #3498db;
                        color: white;
                        font-weight: bold;
                    }
                """)
            
            btn.clicked.connect(lambda checked, d=day: self.select_day(d))
            self.days_grid.addWidget(btn, row, col)
            
            col += 1
            if col > 6:
                col = 0
                row += 1
    
    def select_day(self, day):
        """انتخاب یک روز"""
        self.selected_day = day
        self.update_calendar()
        self.dateSelected.emit(self.get_selected_date())
    
    def prev_month(self):
        """ماه قبل"""
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.selected_day = None
        self.update_calendar()
    
    def next_month(self):
        """ماه بعد"""
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.selected_day = None
        self.update_calendar()


class ShamsiDateEdit(QWidget):
    """ویجت کامل ورودی تاریخ شمسی با تقویم"""
    
    dateChanged = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setup_ui()
        self.set_today()
    
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # فیلد ورودی
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("yyyy/MM/dd")
        self.date_input.setFixedWidth(110)
        self.date_input.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.date_input)
        
        # دکمه تقویم
        self.calendar_btn = QPushButton("📅")
        self.calendar_btn.setFixedSize(30, 30)
        self.calendar_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.calendar_btn.clicked.connect(self.show_calendar)
        layout.addWidget(self.calendar_btn)
        
        self.setLayout(layout)
        
        # تقویم (پنهان)
        self.calendar_widget = PersianCalendarWidget()
        self.calendar_widget.setWindowFlags(Qt.WindowType.Popup)
        self.calendar_widget.dateSelected.connect(self.on_calendar_selected)
    
    def on_text_changed(self):
        """وقتی متن تغییر می‌کند"""
        self.dateChanged.emit(self.date_input.text())
    
    def show_calendar(self):
        """نمایش تقویم"""
        # تنظیم موقعیت تقویم
        pos = self.calendar_btn.mapToGlobal(self.calendar_btn.rect().bottomLeft())
        self.calendar_widget.move(pos)
        self.calendar_widget.show()
    
    def on_calendar_selected(self, date_str):
        """وقتی از تقویم تاریخ انتخاب می‌شود"""
        self.date_input.setText(date_str)
        self.calendar_widget.hide()
        self.dateChanged.emit(date_str)
    
    def set_today(self):
        """تنظیم تاریخ امروز"""
        try:
            today = jdatetime.date.today()
            date_str = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
            self.date_input.setText(date_str)
        except Exception:
            self.date_input.setText("")
    
    def set_date(self, date_str):
        """تنظیم تاریخ از رشته"""
        self.date_input.setText(date_str)
    
    def get_date_string(self):
        """دریافت تاریخ به صورت رشته"""
        return self.date_input.text().strip()
    
    def is_valid(self):
        """بررسی اعتبار تاریخ"""
        from utils.persian_date import PersianDate
        return PersianDate.is_valid_persian_date(self.get_date_string())
    
    def clear(self):
        """پاک کردن تاریخ"""
        self.date_input.clear()