"""
ویجت اعلان‌ها - نمایش پیگیری‌های معوق و یادآوری‌ها
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QListWidget, QListWidgetItem,
    QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import QColor, QFont, QIcon, QAction

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.reminder_service import ReminderService
from utils.logger import get_logger


class NotificationItem(QFrame):
    """آیتم اعلان در لیست"""
    
    clicked = Signal(dict)
    
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.setup_ui()
    
    def setup_ui(self):
        """راه‌اندازی آیتم اعلان"""
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        self.setLayout(layout)
        
        # رنگ وضعیت
        color_frame = QFrame()
        color_frame.setFixedWidth(4)
        is_overdue = self.data.get('is_overdue', False)
        color = "#C62828" if is_overdue else "#F4D35E"
        color_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(color_frame)
        
        # اطلاعات
        info_widget = QWidget()
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        info_widget.setLayout(info_layout)
        
        # نام دانش‌آموز و نوع مداخله
        title = f"👤 {self.data.get('student_name', 'نامشخص')} - {self.data.get('intervention_type', 'مداخله')}"
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #F4C542;")
        info_layout.addWidget(title_label)
        
        # تاریخ اقدام بعدی
        next_date = self.data.get('next_action_date', '')
        if next_date:
            date_label = QLabel(f"📅 تاریخ اقدام: {next_date}")
        else:
            date_label = QLabel("📅 تاریخ اقدام: تعیین نشده")
        date_label.setStyleSheet("font-size: 11px; color: #D9C36A;")
        info_layout.addWidget(date_label)
        
        # مسئول
        staff_name = self.data.get('staff_name', 'نامشخص')
        staff_label = QLabel(f"👨‍🏫 مسئول: {staff_name}")
        staff_label.setStyleSheet("font-size: 11px; color: #D9C36A;")
        info_layout.addWidget(staff_label)
        
        layout.addWidget(info_widget)
        layout.addStretch()
        
        # نشان معوق بودن
        if is_overdue:
            badge = QLabel("🔴 معوق")
            badge.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    font-weight: bold;
                    color: #C62828;
                    background-color: #F4D35E;
                    padding: 2px 8px;
                    border-radius: 10px;
                    border: 1px solid #C62828;
                }
            """)
            layout.addWidget(badge)
        
        # استایل
        self.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: none;
                border-bottom: 1px solid #08223A;
            }
            QFrame:hover {
                background-color: #0B2E4F;
            }
        """)
        
        # کلیک روی آیتم
        self.mousePressEvent = self.on_click
    
    def on_click(self, event):
        """مدیریت کلیک روی آیتم"""
        self.clicked.emit(self.data)


class NotificationWidget(QWidget):
    """ویجت اعلان‌ها - نمایش به صورت پنل کشویی"""
    
    notification_clicked = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.reminder_service = ReminderService()
        self.logger = get_logger(self.__class__.__name__)
        self.notifications = []
        self.is_open = False
        
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(380, 450)
        
        self.setup_ui()
        self.load_notifications()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # کارت اصلی
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border-radius: 12px;
                border: 1px solid #D9C36A;
            }
        """)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        card.setLayout(card_layout)
        
        # هدر
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border-radius: 12px 12px 0 0;
                border-bottom: 1px solid #D9C36A;
            }
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 12, 15, 12)
        header.setLayout(header_layout)
        
        title_label = QLabel("🔔 اعلان‌ها")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #F4C542;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.count_label = QLabel("۰")
        self.count_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: bold;
                color: #0B2E4F;
                background-color: #EF4444;
                padding: 1px 8px;
                border-radius: 10px;
                min-width: 20px;
                text-align: center;
            }
        """)
        header_layout.addWidget(self.count_label)
        
        card_layout.addWidget(header)
        
        # لیست اعلان‌ها
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #0B2E4F;
            }
            QScrollBar:vertical {
                background-color: #08223A;
                width: 4px;
                border-radius: 2px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: #D9C36A;
                border-radius: 2px;
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
        container.setStyleSheet("background-color: #0B2E4F;")
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container.setLayout(container_layout)
        
        # لیست آیتم‌ها
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: #0B2E4F;
                outline: 0;
            }
            QListWidget::item {
                padding: 0px;
                border: none;
            }
        """)
        container_layout.addWidget(self.list_widget)
        
        # پیام خالی
        self.empty_label = QLabel("✅ همه پیگیری‌ها به موقع انجام شده‌اند.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #D9C36A;
                padding: 30px 20px;
            }
        """)
        self.empty_label.setVisible(False)
        container_layout.addWidget(self.empty_label)
        
        scroll.setWidget(container)
        card_layout.addWidget(scroll)
        
        # دکمه مشاهده همه
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                border-top: 1px solid #D9C36A;
                border-radius: 0 0 12px 12px;
                background-color: #0B2E4F;
            }
        """)
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(15, 8, 15, 8)
        footer.setLayout(footer_layout)
        
        self.view_all_btn = QPushButton("مشاهده همه در داشبورد")
        self.view_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #0B2E4F;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #08223A;
            }
        """)
        self.view_all_btn.clicked.connect(self.view_all)
        footer_layout.addWidget(self.view_all_btn)
        
        footer_layout.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #D9C36A;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #08223A;
                color: #F4C542;
            }
        """)
        self.close_btn.clicked.connect(self.hide)
        footer_layout.addWidget(self.close_btn)
        
        card_layout.addWidget(footer)
        
        main_layout.addWidget(card)
        
        # سایه
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
    
    def load_notifications(self):
        """بارگذاری اعلان‌ها"""
        try:
            summary = self.reminder_service.get_reminder_summary()
            
            # دریافت لیست پیگیری‌های معوق و در انتظار
            notifications = []
            
            # اولویت با موارد معوق
            overdue = summary.get('overdue_list', [])
            for item in overdue:
                item['is_overdue'] = True
                notifications.append(item)
            
            # سپس موارد در انتظار
            pending = summary.get('pending_list', [])
            for item in pending:
                if not item.get('is_overdue', False):
                    item['is_overdue'] = False
                    notifications.append(item)
            
            self.notifications = notifications
            
            # به‌روزرسانی لیست
            self.list_widget.clear()
            
            if notifications:
                self.count_label.setText(str(len(notifications)))
                self.count_label.setVisible(True)
                self.empty_label.setVisible(False)
                
                for data in notifications[:10]:  # حداکثر ۱۰ مورد
                    item = QListWidgetItem()
                    widget = NotificationItem(data)
                    widget.clicked.connect(self.on_notification_clicked)
                    item.setSizeHint(widget.sizeHint())
                    self.list_widget.addItem(item)
                    self.list_widget.setItemWidget(item, widget)
            else:
                self.count_label.setText("۰")
                self.count_label.setVisible(False)
                self.empty_label.setVisible(True)
                
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری اعلان‌ها: {e}")
    
    def on_notification_clicked(self, data):
        """وقتی روی اعلان کلیک می‌شود"""
        self.notification_clicked.emit(data)
        self.hide()
        
        # نمایش پیام به کاربر
        student_name = data.get('student_name', 'نامشخص')
        intervention_type = data.get('intervention_type', 'مداخله')
        next_date = data.get('next_action_date', 'تعیین نشده')
        staff_name = data.get('staff_name', 'نامشخص')
        
        QMessageBox.information(
            self.parent(),
            "جزئیات پیگیری",
            f"""
📋 **جزئیات پیگیری**

👤 دانش‌آموز: {student_name}
🛠️ نوع مداخله: {intervention_type}
📅 تاریخ اقدام بعدی: {next_date}
👨‍🏫 مسئول: {staff_name}

💡 لطفاً برای پیگیری به بخش مدیریت پیگیری‌ها مراجعه کنید.
"""
        )
    
    def view_all(self):
        """مشاهده همه در داشبورد"""
        self.hide()
        # ارسال سیگنال به MainWindow برای رفتن به داشبورد
        if self.parent():
            # پیدا کردن MainWindow
            parent = self.parent()
            while parent:
                if hasattr(parent, 'stacked_widget') and hasattr(parent, 'btn_dashboard'):
                    parent.stacked_widget.setCurrentIndex(1)  # داشبورد
                    break
                parent = parent.parent()
    
    def show_at(self, pos):
        """نمایش پنل در موقعیت مشخص"""
        self.load_notifications()
        self.move(pos)
        self.show()
        self.raise_()
        self.is_open = True
    
    def hideEvent(self, event):
        """وقتی پنل مخفی می‌شود"""
        self.is_open = False
        super().hideEvent(event)