"""
ویجت ورودی تاریخ شمسی
"""

from PySide6.QtWidgets import QDateEdit
from PySide6.QtCore import QDate, Qt

try:
    import jdatetime
    JDT_AVAILABLE = True
except ImportError:
    JDT_AVAILABLE = False
    print("⚠️ کتابخانه jdatetime نصب نیست.")


class ShamsiDateEdit(QDateEdit):
    """ویجت ورودی تاریخ شمسی"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # تنظیم فرمت نمایش
        self.setDisplayFormat("yyyy/MM/dd")
        self.setCalendarPopup(True)
        
        # تنظیم تاریخ پیش‌فرض به امروز (شمسی)
        if JDT_AVAILABLE:
            today = jdatetime.date.today()
            shamsi_date = QDate(today.year, today.month, today.day)
            self.setDate(shamsi_date)
        else:
            self.setDate(QDate.currentDate())
    
    def date(self):
        """دریافت تاریخ به صورت QDate (با سال شمسی)"""
        return super().date()
    
    def toJalali(self):
        """تبدیل تاریخ انتخاب شده به شیء jdatetime"""
        if not JDT_AVAILABLE:
            return None
        
        qdate = self.date()
        return jdatetime.date(qdate.year(), qdate.month(), qdate.day())
    
    def toGregorian(self):
        """تبدیل تاریخ انتخاب شده به شیء datetime (میلادی)"""
        if not JDT_AVAILABLE:
            return None
        
        jalali = self.toJalali()
        if jalali:
            return jalali.togregorian()
        return None
    
    def toDateString(self):
        """دریافت تاریخ به صورت رشته `yyyy/MM/dd` (همان فرمت شمسی)"""
        return self.date().toString("yyyy/MM/dd")
    
    def setDateShamsi(self, year, month, day):
        """تنظیم تاریخ با اعداد شمسی"""
        if JDT_AVAILABLE:
            # بررسی اعتبار تاریخ شمسی
            try:
                jdatetime.date(year, month, day)
                shamsi_qdate = QDate(year, month, day)
                self.setDate(shamsi_qdate)
                return True
            except Exception:
                return False
        return False