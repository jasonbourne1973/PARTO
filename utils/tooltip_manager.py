"""
مدیریت Tooltip در سراسر برنامه
با قابلیت نمایش راهنماهای پیشرفته
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QToolTip, QVBoxLayout, QWidget

from config.help_messages import FIELD_HELP, HELP_MESSAGES


class TooltipManager:
    """
    مدیریت Tooltip در سراسر برنامه
    
    ویژگی‌ها:
    - تنظیم Tooltip برای ویجت‌ها
    - نمایش Tooltip با تاخیر
    - استایل‌دهی پیشرفته به Tooltip
    - نمایش راهنماهای چندخطی
    """
    
    # استایل Tooltip
    TOOLTIP_STYLE = """
        QToolTip {
            background-color: #1a252f;
            color: #ecf0f1;
            border: 1px solid #34495e;
            border-radius: 6px;
            padding: 8px 12px;
            font-family: "Segoe UI", "Vazirmatn", "Tahoma", sans-serif;
            font-size: 12px;
            line-height: 1.6;
            max-width: 300px;
        }
    """
    
    @staticmethod
    def setup():
        """تنظیم استایل Tooltip در سطح برنامه"""
        QToolTip.setStyleSheet(TooltipManager.TOOLTIP_STYLE)
    
    @staticmethod
    def set_tooltip(widget: QWidget, message: str, delay_ms: int = 500):
        """
        تنظیم Tooltip برای یک ویجت
        
        Args:
            widget: ویجت مورد نظر
            message: متن راهنما
            delay_ms: تاخیر نمایش (میلی‌ثانیه)
        """
        widget.setToolTip(message)
        widget.setToolTipDuration(delay_ms)
    
    @staticmethod
    def set_field_tooltip(widget: QWidget, field_name: str):
        """
        تنظیم Tooltip بر اساس نام فیلد
        
        Args:
            widget: ویجت مورد نظر
            field_name: نام فیلد (کلید در HELP_MESSAGES)
        """
        message = FIELD_HELP.get(field_name)
        if message:
            TooltipManager.set_tooltip(widget, message)
    
    @staticmethod
    def show_delayed_tooltip(widget: QWidget, message: str, delay_ms: int = 500):
        """
        نمایش Tooltip با تاخیر
        
        Args:
            widget: ویجت مورد نظر
            message: متن راهنما
            delay_ms: تاخیر نمایش (میلی‌ثانیه)
        """
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(
            lambda: TooltipManager._show_tooltip_at_widget(widget, message)
        )
        timer.start(delay_ms)
        return timer
    
    @staticmethod
    def _show_tooltip_at_widget(widget: QWidget, message: str):
        """نمایش Tooltip در موقعیت ویجت"""
        if widget and widget.isVisible():
            pos = widget.mapToGlobal(widget.rect().bottomLeft())
            pos.setX(pos.x() - 50)
            QToolTip.showText(pos, message, widget)
    
    @staticmethod
    def create_help_label(message: str) -> QLabel:
        """
        ایجاد یک QLabel با استایل راهنما
        
        Args:
            message: متن راهنما
            
        Returns:
            QLabel: برچسب با استایل راهنما
        """
        label = QLabel(f"💡 {message}")
        label.setStyleSheet("""
            QLabel {
                background-color: #fef9e7;
                color: #7d6608;
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid #f1c40f;
                font-size: 12px;
                line-height: 1.6;
            }
        """)
        label.setWordWrap(True)
        return label
    
    @staticmethod
    def create_help_widget(messages: list) -> QWidget:
        """
        ایجاد یک ویجت راهنما با چند خط متن
        
        Args:
            messages: لیست متن‌های راهنما
            
        Returns:
            QWidget: ویجت راهنما
        """
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        for msg in messages:
            label = QLabel(f"• {msg}")
            label.setStyleSheet("""
                QLabel {
                    color: #475569;
                    font-size: 11px;
                    line-height: 1.4;
                }
            """)
            layout.addWidget(label)
        
        widget.setLayout(layout)
        return widget
    
    @staticmethod
    def clear_tooltip(widget: QWidget):
        """پاک کردن Tooltip یک ویجت"""
        widget.setToolTip("")
    
    @staticmethod
    def get_help_for_field(field_name: str) -> str:
        """دریافت متن راهنما برای یک فیلد"""
        return FIELD_HELP.get(field_name, "")
    
    @staticmethod
    def get_help_for_topic(topic_name: str) -> str:
        """دریافت متن راهنما برای یک موضوع"""
        return HELP_MESSAGES.get(topic_name, "")