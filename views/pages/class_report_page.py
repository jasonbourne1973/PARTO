"""
صفحه گزارش کلاس - بدون رتبه‌بندی
نمایش وضعیت کلی کلاس بر اساس داده‌های ثبت‌شده
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import matplotlib
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dal.academic_year_dal import AcademicYearDAL
from dal.class_dal import ClassDAL
from dal.staff_dal import StaffDAL
from services.class_report_service import ClassReportService
from utils.shamsi_date_input import ShamsiDateInput

matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from utils.logger import get_logger

logger = get_logger(__name__)


class ClassReportPage(QWidget):
    """صفحه گزارش کلاس - بدون رتبه‌بندی"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.class_report_service = ClassReportService()
        self.class_dal = ClassDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.staff_dal = StaffDAL()
        
        self.current_class_id = None
        self.current_report = None
        self.all_classes = []
        
        self.setup_ui()
        self.load_academic_years()
        self.load_classes()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== عنوان =====
        title_label = QLabel("📊 گزارش کلاس")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        layout.addWidget(title_label)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        toolbar.addWidget(QLabel("سال تحصیلی:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(150)
        self.year_combo.currentIndexChanged.connect(self.on_year_changed)
        self.year_combo.setStyleSheet("""
            QComboBox {
    color: #F4C542;
                padding: 5px 10px;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                background-color: #08223A;
            }
        """)
        toolbar.addWidget(self.year_combo)
        
        toolbar.addSpacing(15)
        
        toolbar.addWidget(QLabel("کلاس:"))
        self.class_combo = QComboBox()
        self.class_combo.setMinimumWidth(200)
        self.class_combo.setPlaceholderText("انتخاب کلاس...")
        self.class_combo.currentIndexChanged.connect(self.on_class_changed)
        self.class_combo.setStyleSheet("""
            QComboBox {
    color: #F4C542;
                padding: 5px 10px;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                background-color: #08223A;
            }
            QComboBox:hover {
                border-color: #0B2E4F;
            }
        """)
        toolbar.addWidget(self.class_combo)
        
        toolbar.addSpacing(15)
        
        toolbar.addWidget(QLabel("از تاریخ:"))
        self.start_date = ShamsiDateInput()
        toolbar.addWidget(self.start_date)
        
        toolbar.addWidget(QLabel("تا تاریخ:"))
        self.end_date = ShamsiDateInput()
        toolbar.addWidget(self.end_date)
        
        toolbar.addSpacing(10)
        
        self.generate_btn = QPushButton("📊 تولید گزارش")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.generate_btn.clicked.connect(self.generate_report)
        toolbar.addWidget(self.generate_btn)
        
        toolbar.addStretch()
        
        # دکمه‌های خروجی
        self.pdf_btn = QPushButton("📄 PDF")
        self.pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 6px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #D94B4B; }
        """)
        self.pdf_btn.clicked.connect(self.export_pdf)
        toolbar.addWidget(self.pdf_btn)
        
        self.excel_btn = QPushButton("📊 Excel")
        self.excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 6px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.excel_btn.clicked.connect(self.export_excel)
        toolbar.addWidget(self.excel_btn)
        
        layout.addLayout(toolbar)
        
        # ===== پیام "داده ناکافی" =====
        self.insufficient_data_label = QLabel("")
        self.insufficient_data_label.setStyleSheet("""
            QLabel {
                background-color: #C62828;
                color: #C62828;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                border: 1px solid #F4C542;
            }
        """)
        self.insufficient_data_label.setVisible(False)
        layout.addWidget(self.insufficient_data_label)
        
        # ===== نوار پیشرفت =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #D9C36A;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0B2E4F;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # ===== تب‌های گزارش =====
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
            }
            QTabBar::tab:selected {
    border-color: #F4C542;
                background-color: #8BC34A;
                color: #111111;
            }
        """)
        
        self.tabs.addTab(self.create_summary_tab(), "📊 خلاصه")
        self.tabs.addTab(self.create_competency_tab(), "⭐ شایستگی‌ها")
        self.tabs.addTab(self.create_students_tab(), "📋 دانش‌آموزان")
        self.tabs.addTab(self.create_chart_tab(), "📈 نمودار")
        self.tabs.addTab(self.create_recommendations_tab(), "💡 پیشنهادات")
        
        layout.addWidget(self.tabs)
        
        # تنظیم تاریخ‌های پیش‌فرض
        self._set_default_dates()
    
    def _set_default_dates(self):
        """تنظیم تاریخ‌های پیش‌فرض"""
        try:
            import jdatetime
            today = jdatetime.date.today()
            self.end_date.set_date(f"{today.year:04d}/{today.month:02d}/{today.day:02d}")
            start_month = today.month - 3
            start_year = today.year
            if start_month <= 0:
                start_month += 12
                start_year -= 1
            self.start_date.set_date(f"{start_year:04d}/{start_month:02d}/{today.day:02d}")
        except (ImportError, ValueError, AttributeError, TypeError) as e:
            # نبود jdatetime یا تاریخ نامعتبر: صفحه بدون تاریخ پیش‌فرض
            # بالا می‌آید و کاربر خودش تاریخ را وارد می‌کند.
            logger.debug(f"تاریخ‌های پیش‌فرض تنظیم نشد: {e}")
    
    def create_summary_tab(self):
        """ایجاد تب خلاصه"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                padding: 15px;
                font-size: 13px;
                line-height: 1.8;
            }
        """)
        self.summary_text.setPlaceholderText("پس از انتخاب کلاس و کلیک روی تولید گزارش، خلاصه اینجا نمایش داده می‌شود...")
        scroll.setWidget(self.summary_text)
        layout.addWidget(scroll)
        
        return tab
    
    def create_competency_tab(self):
        """ایجاد تب شایستگی‌ها"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.competency_table = QTableWidget()
        self.competency_table.setColumnCount(6)
        self.competency_table.setHorizontalHeaderLabels([
            "شایستگی", "تعداد", "میانگین شدت", "مثبت", "منفی", "وضعیت"
        ])
        self.competency_table.setAlternatingRowColors(True)
        self.competency_table.setStyleSheet("""
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
        
        header = self.competency_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.competency_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.competency_table)
        
        return tab
    
    def create_students_tab(self):
        """ایجاد تب دانش‌آموزان"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(7)
        self.students_table.setHorizontalHeaderLabels([
            "ردیف", "دانش‌آموز", "تعداد مشاهدات", "مثبت", "منفی", "میانگین شدت", "وضعیت"
        ])
        self.students_table.setAlternatingRowColors(True)
        self.students_table.setStyleSheet("""
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
        
        header = self.students_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        self.students_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.students_table)
        
        return tab
    
    def create_chart_tab(self):
        """ایجاد تب نمودار"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #0B2E4F; border: 1px solid #D9C36A; border-radius: 5px;")
        layout.addWidget(self.canvas)
        
        return tab
    
    def create_recommendations_tab(self):
        """ایجاد تب پیشنهادات"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        self.recommendations_text.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                background-color: #08223A;
                border: 1px solid #8BC34A;
                border-radius: 5px;
                padding: 15px;
                font-size: 13px;
                line-height: 1.8;
            }
        """)
        self.recommendations_text.setPlaceholderText("پیشنهادات پس از تولید گزارش نمایش داده می‌شود...")
        scroll.setWidget(self.recommendations_text)
        layout.addWidget(scroll)
        
        return tab
    
    def load_academic_years(self):
        """بارگذاری سال‌های تحصیلی در کامبوباکس"""
        try:
            years = self.academic_year_dal.get_all(include_archived=True)
            self.year_combo.clear()
            self.year_combo.addItem("همه سال‌ها", None)
            for year in years:
                display_text = f"{year.title} {'📦' if year.is_archived == 1 else ''}"
                self.year_combo.addItem(display_text, year.id)
            
            # انتخاب سال فعال
            active_year = self.academic_year_dal.get_active()
            if active_year:
                for i in range(self.year_combo.count()):
                    if self.year_combo.itemData(i) == active_year.id:
                        self.year_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            logger.error(f"خطا در بارگذاری سال‌های تحصیلی: {e}")
    
    def load_classes(self):
        """بارگذاری کلاس‌ها در کامبوباکس"""
        try:
            year_id = self.year_combo.currentData()
            self.all_classes = self.class_dal.get_all(year_id)
            
            self.class_combo.clear()
            self.class_combo.addItem("انتخاب کلاس...", None)
            
            for class_obj in self.all_classes:
                display_text = f"{class_obj.display_name}"
                self.class_combo.addItem(display_text, class_obj.id)
        except Exception as e:
            logger.error(f"خطا در بارگذاری کلاس‌ها: {e}")
    
    def on_year_changed(self, index):
        """وقتی سال تحصیلی تغییر می‌کند"""
        self.load_classes()
    
    def on_class_changed(self, index):
        """وقتی کلاس تغییر می‌کند"""
        if index >= 0:
            self.current_class_id = self.class_combo.itemData(index)
    
    def generate_report(self):
        """تولید گزارش کلاس"""
        if not self.current_class_id:
            QMessageBox.warning(self, "توجه", "لطفاً یک کلاس را انتخاب کنید.")
            return
        
        start_date = self.start_date.get_date_string()
        end_date = self.end_date.get_date_string()
        
        if not start_date or not end_date:
            QMessageBox.warning(self, "توجه", "لطفاً تاریخ شروع و پایان را وارد کنید.")
            return
        
        # نمایش نوار پیشرفت
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.set_buttons_enabled(False)
        
        try:
            self.progress_bar.setValue(30)
            
            # تولید گزارش
            report_data = self.class_report_service.get_class_report(
                self.current_class_id, start_date, end_date
            )
            
            self.progress_bar.setValue(80)
            
            if not report_data:
                self.progress_bar.setVisible(False)
                self.set_buttons_enabled(True)
                QMessageBox.information(self, "توجه", "داده‌ای برای تولید گزارش وجود ندارد.")
                return
            
            self.current_report = report_data
            self.display_report(report_data)
            
            self.progress_bar.setValue(100)
            
            # بررسی داده ناکافی
            if not report_data.get('has_data', False):
                self.insufficient_data_label.setVisible(True)
                self.insufficient_data_label.setText(
                    "⚠️ داده کافی برای تحلیل کامل وجود ندارد. "
                    "ثبت مشاهدات بیشتر توصیه می‌شود."
                )
            else:
                self.insufficient_data_label.setVisible(False)
            
            QMessageBox.information(self, "موفقیت", "گزارش با موفقیت تولید شد.")
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در تولید گزارش:\n{e!s}")
        
        finally:
            self.progress_bar.setVisible(False)
            self.set_buttons_enabled(True)
    
    def display_report(self, report_data):
        """نمایش گزارش"""
        self.display_summary(report_data)
        self.display_competencies(report_data)
        self.display_students(report_data)
        self.draw_chart(report_data)
        self.display_recommendations(report_data)
    
    def display_summary(self, data):
        """نمایش خلاصه گزارش"""
        class_obj = data['class']
        obs_stats = data.get('observations_stats', {})
        inter_stats = data.get('intervention_stats', {})
        follow_stats = data.get('followup_stats', {})
        
        summary = f"""
📊 **گزارش کلاس {class_obj.display_name}**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **اطلاعات کلاس**
• نام کلاس: {class_obj.display_name}
• پایه: {class_obj.grade_display if hasattr(class_obj, 'grade_display') else class_obj.grade}
• معلم: {data.get('teacher_name', 'نامشخص')}
• تعداد دانش‌آموزان: {data.get('student_count', 0)}
• سال تحصیلی: {data['academic_year'].title if data.get('academic_year') else 'همه سال‌ها'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **آمار مشاهدات**
• کل مشاهدات: {obs_stats.get('total', 0)}
• مشاهدات مثبت: {obs_stats.get('positive', 0)}
• مشاهدات منفی: {obs_stats.get('negative', 0)}
• مشاهدات خنثی: {obs_stats.get('neutral', 0)}
• میانگین شدت: {obs_stats.get('avg_severity', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛠️ **آمار مداخلات**
• کل مداخلات: {inter_stats.get('total', 0)}
• در حال اجرا: {inter_stats.get('in_progress', 0)}
• تکمیل شده: {inter_stats.get('completed', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔔 **آمار پیگیری‌ها**
• کل پیگیری‌ها: {follow_stats.get('total', 0)}
• در انتظار: {follow_stats.get('pending', 0)}
• انجام شده: {follow_stats.get('done', 0)}
"""
        
        self.summary_text.setText(summary)
    
    def display_competencies(self, data):
        """نمایش شایستگی‌ها"""
        comp_stats = data.get('competency_stats', {})
        self.competency_table.setRowCount(len(comp_stats))
        
        # بازرسی دهم: به‌جای شمارندهٔ دستی، enumerate
        for row, (name, stats) in enumerate(comp_stats.items()):
            self.competency_table.setItem(row, 0, QTableWidgetItem(name))
            self.competency_table.setItem(row, 1, QTableWidgetItem(str(stats.get('count', 0))))
            self.competency_table.setItem(row, 2, QTableWidgetItem(str(stats.get('avg_severity', 0))))
            self.competency_table.setItem(row, 3, QTableWidgetItem(str(stats.get('positive', 0))))
            self.competency_table.setItem(row, 4, QTableWidgetItem(str(stats.get('negative', 0))))
            
            avg = stats.get('avg_severity', 0)
            if avg >= 3.5:
                status = "✅ عالی"
                color = QColor(0, 128, 0)
            elif avg >= 2.5:
                status = "🟡 خوب"
                color = QColor(255, 165, 0)
            elif avg >= 1.5:
                status = "🟠 متوسط"
                color = QColor(255, 140, 0)
            else:
                status = "🔴 نیاز به توجه"
                color = QColor(255, 0, 0)
            
            item = QTableWidgetItem(status)
            item.setForeground(color)
            self.competency_table.setItem(row, 5, item)
            self.competency_table.setRowHeight(row, 30)
    
    def display_students(self, data):
        """نمایش لیست دانش‌آموزان"""
        student_stats = data.get('student_stats', [])
        self.students_table.setRowCount(len(student_stats))
        
        for row, student in enumerate(student_stats):
            self.students_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.students_table.setItem(row, 1, QTableWidgetItem(student.get('student_name', 'نامشخص')))
            self.students_table.setItem(row, 2, QTableWidgetItem(str(student.get('observations_count', 0))))
            self.students_table.setItem(row, 3, QTableWidgetItem(str(student.get('positive', 0))))
            self.students_table.setItem(row, 4, QTableWidgetItem(str(student.get('negative', 0))))
            self.students_table.setItem(row, 5, QTableWidgetItem(str(student.get('avg_severity', 0))))
            
            status = student.get('status', 'بدون مشاهده')
            status_item = QTableWidgetItem(status)
            if status == "مطلوب":
                status_item.setBackground(QColor(200, 255, 200))
            elif status == "متوسط":
                status_item.setBackground(QColor(255, 255, 200))
            elif status == "نیازمند توجه":
                status_item.setBackground(QColor(255, 200, 200))
            else:
                status_item.setBackground(QColor(240, 240, 240))
            self.students_table.setItem(row, 6, status_item)
            self.students_table.setRowHeight(row, 30)
    
    def draw_chart(self, data):
        """رسم نمودارها"""
        self.figure.clear()
        
        # ایجاد دو نمودار کنار هم
        ax1 = self.figure.add_subplot(121)
        ax2 = self.figure.add_subplot(122)
        
        # ===== نمودار ۱: توزیع مشاهدات =====
        obs_stats = data.get('observations_stats', {})
        positive = obs_stats.get('positive', 0)
        negative = obs_stats.get('negative', 0)
        neutral = obs_stats.get('neutral', 0)
        
        if positive + negative + neutral > 0:
            labels = ['مثبت', 'منفی', 'خنثی']
            sizes = [positive, negative, neutral]
            colors = ['#8BC34A', '#C62828', '#F4D35E']
            
            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.set_title('توزیع مشاهدات', fontsize=12, fontweight='bold')
        else:
            ax1.text(0.5, 0.5, 'داده‌ای وجود ندارد', ha='center', va='center', fontsize=12)
            ax1.axis('off')
        
        # ===== نمودار ۲: شایستگی‌های برتر =====
        comp_stats = data.get('competency_stats', {})
        if comp_stats:
            # مرتب‌سازی بر اساس میانگین شدت
            sorted_items = sorted(
                comp_stats.items(),
                key=lambda x: x[1].get('avg_severity', 0),
                reverse=True
            )[:8]
            
            names = [item[0][:15] for item in sorted_items]
            values = [item[1].get('avg_severity', 0) for item in sorted_items]
            
            bars = ax2.bar(names, values, color='#0B2E4F')
            
            # رنگ‌بندی
            for bar, val in zip(bars, values):
                if val >= 3.5:
                    bar.set_color('#66BB6A')
                elif val >= 2.5:
                    bar.set_color('#F4D35E')
                elif val >= 1.5:
                    bar.set_color('#F28C28')
                else:
                    bar.set_color('#C62828')
            
            ax2.set_ylabel('میانگین شدت', fontsize=10)
            ax2.set_title('شایستگی‌های برتر', fontsize=12, fontweight='bold')
            ax2.set_ylim(0, 5)
            ax2.tick_params(axis='x', rotation=30)
        else:
            ax2.text(0.5, 0.5, 'داده‌ای وجود ندارد', ha='center', va='center', fontsize=12)
            ax2.axis('off')
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def display_recommendations(self, data):
        """نمایش پیشنهادات"""
        recommendations = data.get('recommendations', {})
        
        text = """
💡 **پیشنهادات بر اساس داده‌های کلاس**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**👨‍🏫 پیشنهادات برای معلم:**
"""
        for rec in recommendations.get('teacher', []):
            text += f"\n{rec}\n"
        
        if not recommendations.get('teacher'):
            text += "\n✅ وضعیت کلاس مطلوب است. به ثبت مستمر مشاهدات ادامه دهید."
        
        text += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🫂 پیشنهادات برای مشاور:**
"""
        for rec in recommendations.get('counselor', []):
            text += f"\n{rec}\n"
        
        if not recommendations.get('counselor'):
            text += "\n✅ وضعیت کلاس مطلوب است. نیاز به مداخله تخصصی خاصی نیست."
        
        text += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**💡 پیشنهادات عمومی:**
"""
        for rec in recommendations.get('general', []):
            text += f"\n{rec}\n"
        
        self.recommendations_text.setText(text)
    
    def set_buttons_enabled(self, enabled):
        """فعال/غیرفعال کردن دکمه‌ها"""
        self.generate_btn.setEnabled(enabled)
        self.pdf_btn.setEnabled(enabled)
        self.excel_btn.setEnabled(enabled)
    
    def export_pdf(self):
        """خروجی PDF"""
        if not self.current_report:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا یک گزارش تولید کنید.")
            return
        
        class_name = self.current_report['class'].display_name
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل PDF",
            f"گزارش_کلاس_{class_name}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return
        
        try:
            start_date = self.start_date.get_date_string()
            end_date = self.end_date.get_date_string()
            
            success, message = self.class_report_service.export_class_report_pdf(
                self.current_class_id, file_path, start_date, end_date
            )
            
            if success:
                QMessageBox.information(self, "موفقیت", message)
            else:
                QMessageBox.critical(self, "خطا", message)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در خروجی PDF:\n{e!s}")
    
    def export_excel(self):
        """خروجی Excel"""
        if not self.current_report:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا یک گزارش تولید کنید.")
            return
        
        class_name = self.current_report['class'].display_name
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل Excel",
            f"گزارش_کلاس_{class_name}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            start_date = self.start_date.get_date_string()
            end_date = self.end_date.get_date_string()
            
            success, message = self.class_report_service.export_class_report_excel(
                self.current_class_id, file_path, start_date, end_date
            )
            
            if success:
                QMessageBox.information(self, "موفقیت", message)
            else:
                QMessageBox.critical(self, "خطا", message)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در خروجی Excel:\n{e!s}")