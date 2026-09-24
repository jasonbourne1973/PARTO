"""
صفحه گزارش عملکرد معلم - نمایش تعداد و کیفیت مشاهدات، مداخلات و پیگیری‌ها
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

from dal.staff_dal import StaffDAL
from services.teacher_performance_service import TeacherPerformanceService
from utils.shamsi_date_input import ShamsiDateInput

matplotlib.use('QtAgg')
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from utils.behavior_analysis import classify_pattern, pattern_label
from utils.logger import get_logger

logger = get_logger(__name__)


class TeacherPerformancePage(QWidget):
    """
    صفحه گزارش عملکرد معلم
    
    ویژگی‌ها:
    - نمایش تعداد مشاهدات، مداخلات و پیگیری‌ها
    - تحلیل کیفیت مشاهدات (مثبت/منفی)
    - نمایش روند عملکرد
    - تحلیل شایستگی‌های مرتبط
    - پیشنهادات بهبود
    - خروجی PDF
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.teacher_performance_service = TeacherPerformanceService()
        self.staff_dal = StaffDAL()
        
        self.current_teacher_id = None
        self.current_report = None
        self.all_teachers = []
        
        self.setup_ui()
        self.load_teachers()
        self._set_default_dates()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== عنوان =====
        title_label = QLabel("📊 گزارش عملکرد معلم")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        layout.addWidget(title_label)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        toolbar.addWidget(QLabel("معلم:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.setMinimumWidth(200)
        self.teacher_combo.setPlaceholderText("انتخاب معلم...")
        self.teacher_combo.currentIndexChanged.connect(self.on_teacher_changed)
        self.teacher_combo.setStyleSheet("""
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
        toolbar.addWidget(self.teacher_combo)
        
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
        
        # دکمه خروجی PDF
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
        self.tabs.addTab(self.create_students_tab(), "📋 دانش‌آموزان")
        self.tabs.addTab(self.create_competency_tab(), "⭐ شایستگی‌ها")
        self.tabs.addTab(self.create_chart_tab(), "📈 نمودار")
        self.tabs.addTab(self.create_recommendations_tab(), "💡 پیشنهادات")
        
        layout.addWidget(self.tabs)
    
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
        self.summary_text.setPlaceholderText("پس از انتخاب معلم و کلیک روی تولید گزارش، خلاصه اینجا نمایش داده می‌شود...")
        scroll.setWidget(self.summary_text)
        layout.addWidget(scroll)
        
        return tab
    
    def create_students_tab(self):
        """ایجاد تب دانش‌آموزان"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(7)
        self.students_table.setHorizontalHeaderLabels([
            "ردیف", "دانش‌آموز", "پایه", "کلاس", "تعداد مشاهدات", "مثبت", "میانگین شدت"
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
    
    def create_competency_tab(self):
        """ایجاد تب شایستگی‌ها"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.competency_table = QTableWidget()
        self.competency_table.setColumnCount(5)
        self.competency_table.setHorizontalHeaderLabels([
            "شایستگی", "تعداد", "میانگین شدت", "مثبت", "وضعیت"
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
        
        self.competency_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.competency_table)
        
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
    
    def load_teachers(self):
        """بارگذاری معلمان در کامبوباکس"""
        try:
            all_staff = self.staff_dal.get_all()
            self.all_teachers = [s for s in all_staff if s.role == "teacher"]
            self.teacher_combo.clear()
            self.teacher_combo.addItem("انتخاب معلم...", None)
            for teacher in self.all_teachers:
                self.teacher_combo.addItem(f"{teacher.full_name}", teacher.id)
        except Exception as e:
            logger.error(f"خطا در بارگذاری معلمان: {e}")
    
    def on_teacher_changed(self, index):
        """وقتی معلم تغییر می‌کند"""
        if index >= 0:
            self.current_teacher_id = self.teacher_combo.itemData(index)
    
    def generate_report(self):
        """تولید گزارش عملکرد معلم"""
        if not self.current_teacher_id:
            QMessageBox.warning(self, "توجه", "لطفاً یک معلم را انتخاب کنید.")
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
            report = self.teacher_performance_service.get_teacher_performance(
                self.current_teacher_id, start_date, end_date
            )
            
            self.progress_bar.setValue(80)
            
            if not report or not report.get('has_data', False):
                self.progress_bar.setVisible(False)
                self.set_buttons_enabled(True)
                self.insufficient_data_label.setVisible(True)
                self.insufficient_data_label.setText(
                    "⚠️ داده کافی برای تحلیل کامل وجود ندارد. "
                    "ثبت مشاهدات بیشتر توصیه می‌شود."
                )
                return
            
            self.current_report = report
            self.display_report(report)
            
            self.progress_bar.setValue(100)
            self.insufficient_data_label.setVisible(False)
            
            QMessageBox.information(self, "موفقیت", "گزارش با موفقیت تولید شد.")
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در تولید گزارش:\n{e!s}")
        
        finally:
            self.progress_bar.setVisible(False)
            self.set_buttons_enabled(True)
    
    def display_report(self, report):
        """نمایش گزارش"""
        self.display_summary(report)
        self.display_students(report)
        self.display_competencies(report)
        self.draw_chart(report)
        self.display_recommendations(report)
    
    def display_summary(self, report):
        """نمایش خلاصه گزارش"""
        teacher = report['teacher']
        stats = report.get('stats', {})
        
        summary = f"""
📊 **گزارش عملکرد معلم**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **اطلاعات معلم**
• نام: {teacher.full_name}
• سمت: {teacher.role_display}
• تعداد دانش‌آموزان: {stats.get('total_students', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **آمار کلی**
• کل مشاهدات: {stats.get('total_observations', 0)}
• مشاهدات مثبت: {stats.get('positive', 0)}
• مشاهدات منفی: {stats.get('negative', 0)}
• مشاهدات خنثی: {stats.get('neutral', 0)}
• میانگین شدت: {stats.get('avg_severity', 0)}
• مداخلات ثبت‌شده: {stats.get('total_interventions', 0)}
• پیگیری‌های انجام‌شده: {stats.get('total_followups', 0) - stats.get('pending_followups', 0)}
• پیگیری‌های در انتظار: {stats.get('pending_followups', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **تحلیل عملکرد**
"""
        total_obs = stats.get('total_observations', 0)
        if total_obs > 0:
            positive_ratio = stats.get('positive', 0) / total_obs
            if positive_ratio >= 0.6:
                summary += "✅ عملکرد مطلوب: درصد مشاهدات مثبت بالا است."
            elif positive_ratio >= 0.4:
                summary += "🟡 عملکرد متوسط: می‌توان با تمرین بیشتر بهبود یافت."
            else:
                summary += "🔴 عملکرد نیازمند توجه: درصد مشاهدات مثبت پایین است."
        else:
            summary += "⚠️ هنوز مشاهده‌ای ثبت نشده است."
        
        self.summary_text.setText(summary)
    
    def display_students(self, report):
        """نمایش دانش‌آموزان"""
        students = report.get('students', [])
        self.students_table.setRowCount(len(students))
        
        for row, student in enumerate(students):
            self.students_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.students_table.setItem(row, 1, QTableWidgetItem(student.get('student_name', 'نامشخص')))
            self.students_table.setItem(row, 2, QTableWidgetItem(str(student.get('grade', '-'))))
            self.students_table.setItem(row, 3, QTableWidgetItem(student.get('class_name', '-')))
            self.students_table.setItem(row, 4, QTableWidgetItem(str(student.get('observations_count', 0))))
            self.students_table.setItem(row, 5, QTableWidgetItem(str(student.get('positive', 0))))
            self.students_table.setItem(row, 6, QTableWidgetItem(str(student.get('avg_severity', 0))))
            self.students_table.setRowHeight(row, 30)
    
    def display_competencies(self, report):
        """نمایش شایستگی‌ها"""
        competency_stats = report.get('competency_stats', {})
        self.competency_table.setRowCount(len(competency_stats))
        
        # بازرسی دهم: به‌جای شمارندهٔ دستی، enumerate
        for row, (name, stats) in enumerate(competency_stats.items()):
            self.competency_table.setItem(row, 0, QTableWidgetItem(name))
            self.competency_table.setItem(row, 1, QTableWidgetItem(str(stats.get('count', 0))))
            self.competency_table.setItem(row, 2, QTableWidgetItem(str(stats.get('avg_severity', 0))))
            self.competency_table.setItem(row, 3, QTableWidgetItem(str(stats.get('positive', 0))))
            
            # بازرسی یازدهم: وضعیت بر پایهٔ الگوی رفتار ثبت‌شده، نه شدت
            kind = classify_pattern(
                stats.get('positive', 0), stats.get('negative', 0),
                max(stats.get('count', 0) - stats.get('positive', 0)
                    - stats.get('negative', 0), 0),
                stats.get('count', 0))
            if kind == 'strength':
                status = "✅ " + pattern_label(kind)
                color = QColor(0, 128, 0)
            elif kind == 'needs_attention':
                status = "🔴 " + pattern_label(kind)
                color = QColor(255, 0, 0)
            elif kind == 'mixed':
                status = "🟠 " + pattern_label(kind)
                color = QColor(255, 140, 0)
            else:
                status = "⬜ " + pattern_label(kind)
                color = QColor(158, 158, 158)
            
            item = QTableWidgetItem(status)
            item.setForeground(color)
            self.competency_table.setItem(row, 4, item)
            self.competency_table.setRowHeight(row, 30)
    
    def draw_chart(self, report):
        """رسم نمودارها"""
        self.figure.clear()
        
        # دو نمودار
        ax1 = self.figure.add_subplot(121)
        ax2 = self.figure.add_subplot(122)
        
        # ===== نمودار ۱: توزیع مشاهدات =====
        stats = report.get('stats', {})
        positive = stats.get('positive', 0)
        negative = stats.get('negative', 0)
        neutral = stats.get('neutral', 0)
        
        if positive + negative + neutral > 0:
            labels = ['مثبت', 'منفی', 'خنثی']
            sizes = [positive, negative, neutral]
            colors = ['#8BC34A', '#C62828', '#F4D35E']
            
            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.set_title('توزیع مشاهدات', fontsize=12, fontweight='bold')
        else:
            ax1.text(0.5, 0.5, 'داده‌ای وجود ندارد', ha='center', va='center', fontsize=12)
            ax1.axis('off')
        
        # ===== نمودار ۲: روند =====
        trend = report.get('trend', [])
        if trend:
            labels = [item['label'][:8] for item in trend[-6:]]
            positive_vals = [item['positive'] for item in trend[-6:]]
            negative_vals = [item['negative'] for item in trend[-6:]]
            
            x = np.arange(len(labels))
            width = 0.35
            
            ax2.bar(x - width/2, positive_vals, width, label='مثبت', color='#8BC34A')
            ax2.bar(x + width/2, negative_vals, width, label='منفی', color='#C62828')
            
            ax2.set_xlabel('بازه زمانی', fontsize=10)
            ax2.set_ylabel('تعداد', fontsize=10)
            ax2.set_title('روند مشاهدات', fontsize=12, fontweight='bold')
            ax2.set_xticks(x)
            ax2.set_xticklabels(labels, rotation=30)
            ax2.legend()
        else:
            ax2.text(0.5, 0.5, 'داده‌ای وجود ندارد', ha='center', va='center', fontsize=12)
            ax2.axis('off')
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def display_recommendations(self, report):
        """نمایش پیشنهادات"""
        recommendations = report.get('recommendations', {})
        
        text = """
💡 **پیشنهادات بر اساس داده‌های عملکرد**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**👨‍🏫 پیشنهادات برای معلم:**
"""
        for rec in recommendations.get('teacher', []):
            text += f"\n{rec}\n"
        
        if not recommendations.get('teacher'):
            text += "\n✅ عملکرد مطلوب است. به روند فعلی ادامه دهید."
        
        text += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🫂 پیشنهادات برای مشاور:**
"""
        for rec in recommendations.get('counselor', []):
            text += f"\n{rec}\n"
        
        if not recommendations.get('counselor'):
            text += "\n✅ وضعیت مطلوب است. نیاز به مداخله خاصی نیست."
        
        self.recommendations_text.setText(text)
    
    def set_buttons_enabled(self, enabled):
        """فعال/غیرفعال کردن دکمه‌ها"""
        self.generate_btn.setEnabled(enabled)
        self.pdf_btn.setEnabled(enabled)
    
    def export_pdf(self):
        """خروجی PDF"""
        if not self.current_report:
            QMessageBox.warning(self, "توجه", "لطفاً ابتدا یک گزارش تولید کنید.")
            return
        
        teacher = self.current_report['teacher']
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره فایل PDF",
            f"گزارش_معلم_{teacher.full_name}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return
        
        try:
            start_date = self.start_date.get_date_string()
            end_date = self.end_date.get_date_string()
            
            success, message = self.teacher_performance_service.export_teacher_report_pdf(
                self.current_teacher_id, file_path, start_date, end_date
            )
            
            if success:
                QMessageBox.information(self, "موفقیت", message)
            else:
                QMessageBox.critical(self, "خطا", message)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در خروجی PDF:\n{e!s}")