"""
صفحه مرکز پرونده دانش‌آموز - نسخه نهایی با Timeline واقعی و جستجو و انتخاب سال
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dal.academic_year_dal import AcademicYearDAL
from dal.competency_dal import CompetencyDAL
from dal.family_context_dal import FamilyContextDAL
from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.parent_interview_dal import ParentInterviewDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from services.case_timeline_service import CaseTimelineService
from services.trend_analysis_service import TrendAnalysisService
from utils.behavior_analysis import summarize_by_competency
from utils.logger import get_logger
from views.dialogs.followup_form import FollowUpForm
from views.dialogs.intervention_form import InterventionForm
from views.dialogs.observation_form import ObservationForm
from views.widgets.recommendation_widget import RecommendationWidget

logger = get_logger(__name__)


class StudentProfilePage(QWidget):
    """صفحه مرکز پرونده دانش‌آموز با Timeline و جستجو و انتخاب سال"""
    
    # (بازرسی شانزدهم) درخواست گزارش کامل: پنجرهٔ اصلی صفحهٔ گزارش‌ها را با
    # همین دانش‌آموز باز می‌کند (قبلاً دکمه فقط پیام «به بخش گزارش‌ها بروید» می‌داد).
    report_requested = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.competency_dal = CompetencyDAL()
        self.staff_dal = StaffDAL()
        # زمینهٔ رشد (بازرسی یازدهم): زمینهٔ خانوادگی و گفت‌وگو با والدین
        self.family_dal = FamilyContextDAL()
        self.parent_interview_dal = ParentInterviewDAL()
        self.timeline_service = CaseTimelineService()
        self.trend_service = TrendAnalysisService()
        
        self.student_id = None
        self.profile_id = None
        self.student = None
        self.profile = None
        self.all_students = []
        self.all_academic_years = []
        self.selected_year_id = None
        
        self.setup_ui()
        self.load_academic_years()
        self.load_student_list()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # ===== نوار جستجو و انتخاب دانش‌آموز =====
        search_layout = QHBoxLayout()
        
        search_label = QLabel("🔍 جستجوی دانش‌آموز:")
        search_label.setStyleSheet("font-weight: bold;")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("نام، نام خانوادگی یا کد ملی...")
        self.search_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                padding: 5px 10px;
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
        search_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("🔍 جستجو")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 5px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #08223A; }
        """)
        self.search_btn.clicked.connect(self.search_student)
        search_layout.addWidget(self.search_btn)
        
        self.clear_search_btn = QPushButton("✖")
        self.clear_search_btn.setFixedSize(30, 30)
        self.clear_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #9E1B1B; }
        """)
        self.clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_search_btn)
        
        search_layout.addStretch()
        
        # انتخاب دانش‌آموز از لیست
        self.student_select_combo = QComboBox()
        self.student_select_combo.setMinimumWidth(200)
        self.student_select_combo.setPlaceholderText("انتخاب دانش‌آموز...")
        self.student_select_combo.currentIndexChanged.connect(self.on_student_selected)
        search_layout.addWidget(self.student_select_combo)
        
        main_layout.addLayout(search_layout)
        
        # ===== Header با اطلاعات دانش‌آموز =====
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #F4C542, stop:1 #66BB6A);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        header_layout = QHBoxLayout()
        self.header_frame.setLayout(header_layout)
        
        self.student_name_label = QLabel("نام دانش‌آموز")
        self.student_name_label.setStyleSheet("color: #F4C542; font-size: 20px; font-weight: bold;")
        header_layout.addWidget(self.student_name_label)
        
        header_layout.addSpacing(20)
        
        self.student_info_label = QLabel("پایه: - | کلاس: -")
        self.student_info_label.setStyleSheet("color: #D9C36A; font-size: 14px;")
        header_layout.addWidget(self.student_info_label)
        
        header_layout.addStretch()
        
        # ===== انتخاب سال تحصیلی (جدید) =====
        header_layout.addWidget(QLabel("سال تحصیلی:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(130)
        self.year_combo.setStyleSheet("""
            QComboBox {
                background-color: #08223A;
                color: #F4C542;
                padding: 5px 10px;
                border-radius: 15px;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #8BC34A;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { image: none; }
            QComboBox:hover { background-color: #174F78; }
        """)
        self.year_combo.currentIndexChanged.connect(self.on_year_changed)
        header_layout.addWidget(self.year_combo)
        
        self.status_label = QLabel("وضعیت: -")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #111111;
                font-size: 14px;
                font-weight: bold;
                background-color: #66BB6A;
                padding: 5px 15px;
                border-radius: 15px;
            }
        """)
        header_layout.addWidget(self.status_label)
        
        main_layout.addWidget(self.header_frame)
        
        # ===== دکمه‌های عملیاتی سریع =====
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        self.btn_observation = QPushButton("📝 ثبت مشاهده")
        self.btn_observation.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #08223A; }
        """)
        self.btn_observation.clicked.connect(self.add_observation)
        action_layout.addWidget(self.btn_observation)
        
        self.btn_intervention = QPushButton("🛠️ ثبت مداخله")
        self.btn_intervention.setStyleSheet("""
            QPushButton {
                background-color: #F28C28;
                color: #111111;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #d35400; }
        """)
        self.btn_intervention.clicked.connect(self.add_intervention)
        action_layout.addWidget(self.btn_intervention)
        
        self.btn_followup = QPushButton("🔔 ثبت پیگیری")
        self.btn_followup.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7d3c98; }
        """)
        self.btn_followup.clicked.connect(self.add_followup)
        action_layout.addWidget(self.btn_followup)
        
        action_layout.addStretch()
        
        self.btn_report = QPushButton("📄 گزارش پرونده")
        self.btn_report.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.btn_report.clicked.connect(self.generate_report)
        action_layout.addWidget(self.btn_report)

        # (بازرسی شانزدهم — BUG-027) دیالوگ پیوست‌ها کامل بود ولی هیچ نقطهٔ
        # ورودی در برنامه نداشت؛ این دکمه همان دیالوگ را برای دانش‌آموز باز می‌کند.
        self.btn_attachments = QPushButton("📎 پیوست‌ها")
        self.btn_attachments.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 8px 20px;
                border: 1px solid #D9C36A;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #08223A; }
        """)
        self.btn_attachments.clicked.connect(self.open_attachments)
        action_layout.addWidget(self.btn_attachments)
        
        main_layout.addLayout(action_layout)
        
        # ===== بخش اصلی: Splitter =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ===== سمت چپ: Timeline =====
        timeline_frame = QFrame()
        timeline_frame.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 5px;
            }
        """)
        timeline_layout = QVBoxLayout()
        timeline_frame.setLayout(timeline_layout)
        
        timeline_title = QLabel("⏳ Timeline پرونده")
        timeline_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F4C542; padding: 5px;")
        timeline_layout.addWidget(timeline_title)
        
        self.timeline_list = QListWidget()
        self.timeline_list.setStyleSheet("""
            QListWidget {
                border: none;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #08223A;
            }
            QListWidget::item:selected {
                background-color: #174F78;
                border: 1px solid #0B2E4F;
                border-radius: 5px;
            }
            QListWidget::item:hover {
                background-color: #08223A;
            }
        """)
        self.timeline_list.itemClicked.connect(self.on_timeline_item_clicked)
        timeline_layout.addWidget(self.timeline_list)
        
        splitter.addWidget(timeline_frame)
        
        # ===== سمت راست: جزئیات رویداد =====
        details_frame = QFrame()
        details_frame.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 5px;
            }
        """)
        details_layout = QVBoxLayout()
        details_frame.setLayout(details_layout)
        
        details_title = QLabel("📋 جزئیات رویداد")
        details_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F4C542; padding: 5px;")
        details_layout.addWidget(details_title)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                border: 1px solid #8BC34A;
                padding: 10px;
                font-size: 13px;
                background-color: #08223A;
            }
        """)
        self.details_text.setPlaceholderText("برای مشاهده جزئیات، روی هر رویداد در Timeline کلیک کنید...")
        details_layout.addWidget(self.details_text)
        
        splitter.addWidget(details_frame)
        
        splitter.setSizes([500, 500])
        main_layout.addWidget(splitter)
        
        # ===== تب‌های پایین =====
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
        
        self.tabs.addTab(self.create_observations_tab(), "📝 مشاهدات")
        self.tabs.addTab(self.create_interventions_tab(), "🛠️ مداخلات")
        self.tabs.addTab(self.create_followups_tab(), "🔔 پیگیری‌ها")
        self.tabs.addTab(self.create_trend_tab(), "📈 روند")  # تب جدید
        self.tabs.addTab(self.create_growth_context_tab(), "🌱 زمینهٔ رشد")
        self.tabs.addTab(self.create_summary_tab(), "📊 خلاصه")
        # (بازرسی شانزدهم — بندهای ۸ و ۹) ویجت پیشنهادها قبلاً هیچ‌جا سوار
        # نشده بود؛ اکنون یک تب پروندهٔ دانش‌آموز است و با همان پرونده
        # هم‌گام می‌شود. درخواست «ثبت مداخله» از یک پیشنهاد، فرم مداخلهٔ
        # همین صفحه را باز می‌کند.
        self.recommendation_widget = RecommendationWidget()
        self.recommendation_widget.intervention_requested.connect(self.on_intervention_requested)
        self.tabs.addTab(self.recommendation_widget, "💡 پیشنهادها")
        
        main_layout.addWidget(self.tabs)
    
    def load_academic_years(self):
        """بارگذاری سال‌های تحصیلی در کامبوباکس"""
        try:
            self.all_academic_years = self.academic_year_dal.get_all(include_archived=True)
            self.year_combo.clear()
            for year in self.all_academic_years:
                display_text = f"{year.title} {'📦' if year.is_archived == 1 else ''}"
                self.year_combo.addItem(display_text, year.id)
            
            # انتخاب سال فعال
            active_year = self.academic_year_dal.get_active()
            if active_year:
                for i in range(self.year_combo.count()):
                    if self.year_combo.itemData(i) == active_year.id:
                        self.year_combo.setCurrentIndex(i)
                        self.selected_year_id = active_year.id
                        break
        except Exception as e:
            logger.error(f"خطا در بارگذاری سال‌های تحصیلی: {e}")
    
    def on_year_changed(self, index):
        """وقتی سال تحصیلی تغییر می‌کند"""
        if index >= 0:
            self.selected_year_id = self.year_combo.itemData(index)
            if self.student_id:
                self.load_student_data()
    
    def load_student_list(self):
        """بارگذاری لیست دانش‌آموزان در کامبوباکس"""
        try:
            self.all_students = self.student_dal.get_all()
            self.student_select_combo.clear()
            self.student_select_combo.addItem("انتخاب دانش‌آموز...", None)
            # پروندهٔ فعال دانش‌آموزان یک‌جا خوانده می‌شود (رفع N+1)
            profile_map = self.profile_dal.get_active_by_students(
                s.id for s in self.all_students)
            for student in self.all_students:
                profile = profile_map.get(student.id)
                grade_text = profile.grade_display if profile else "نامشخص"
                display_text = f"{student.full_name} - پایه {grade_text}"
                self.student_select_combo.addItem(display_text, student.id)
        except Exception as e:
            logger.error(f"خطا در بارگذاری لیست دانش‌آموزان: {e}")
    
    def search_student(self):
        """جستجوی دانش‌آموز و انتخاب در کامبوباکس"""
        search_term = self.search_input.text().strip()
        if not search_term:
            QMessageBox.warning(self, "توجه", "لطفاً عبارت جستجو را وارد کنید.")
            return
        
        try:
            results = self.student_dal.search(search_term)
            if not results:
                QMessageBox.information(self, "نتیجه", "هیچ دانش‌آموزی یافت نشد.")
                return
            
            if len(results) == 1:
                student = results[0]
                for i in range(self.student_select_combo.count()):
                    if self.student_select_combo.itemData(i) == student.id:
                        self.student_select_combo.setCurrentIndex(i)
                        break
            else:
                names = "\n".join([f"• {s.full_name} (کد: {s.national_code or 'ندارد'})" for s in results[:10]])
                msg = f"{len(results)} دانش‌آموز پیدا شد:\n\n{names}\n\nلطفاً از لیست کشویی انتخاب کنید."
                QMessageBox.information(self, "نتیجه جستجو", msg)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در جستجو:\n{e!s}")
    
    def clear_search(self):
        """پاک کردن جستجو و نمایش همه"""
        self.search_input.clear()
        self.student_select_combo.setCurrentIndex(0)
    
    def on_student_selected(self, index):
        """وقتی دانش‌آموز از کامبوباکس انتخاب می‌شود"""
        if index >= 0:
            student_id = self.student_select_combo.itemData(index)
            if student_id:
                self.set_student_id(student_id)
    
    def create_summary_tab(self):
        """ایجاد تب خلاصه"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        container = QWidget()
        container_layout = QGridLayout()
        container.setLayout(container_layout)
        
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #0B2E4F; border: 1px solid #D9C36A; border-radius: 8px; padding: 15px;")
        stats_layout = QHBoxLayout()
        stats_frame.setLayout(stats_layout)
        
        self.obs_count_label = QLabel("مشاهدات: 0")
        self.obs_count_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #F4C542;")
        stats_layout.addWidget(self.obs_count_label)
        
        stats_layout.addSpacing(30)
        self.inter_count_label = QLabel("مداخلات: 0")
        self.inter_count_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #F4C542;")
        stats_layout.addWidget(self.inter_count_label)
        
        stats_layout.addSpacing(30)
        self.follow_count_label = QLabel("پیگیری‌ها: 0")
        self.follow_count_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #F4C542;")
        stats_layout.addWidget(self.follow_count_label)
        
        stats_layout.addSpacing(30)
        self.pending_label = QLabel("پیگیری‌های باز: 0")
        self.pending_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #C62828;")
        stats_layout.addWidget(self.pending_label)
        
        stats_layout.addStretch()
        container_layout.addWidget(stats_frame, 0, 0, 1, 2)
        
        strengths_frame = QGroupBox("⭐ نقاط قوت ثبت‌شده")
        strengths_frame.setStyleSheet("""
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
        strengths_layout = QVBoxLayout()
        strengths_frame.setLayout(strengths_layout)
        self.strengths_label = QLabel("هیچ نقطه قوتی ثبت نشده است.")
        self.strengths_label.setWordWrap(True)
        strengths_layout.addWidget(self.strengths_label)
        container_layout.addWidget(strengths_frame, 1, 0)
        
        weaknesses_frame = QGroupBox("🔴 زمینه‌های نیازمند حمایت")
        weaknesses_frame.setStyleSheet("""
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
        weaknesses_layout = QVBoxLayout()
        weaknesses_frame.setLayout(weaknesses_layout)
        self.weaknesses_label = QLabel("هیچ زمینه‌ای ثبت نشده است.")
        self.weaknesses_label.setWordWrap(True)
        weaknesses_layout.addWidget(self.weaknesses_label)
        container_layout.addWidget(weaknesses_frame, 1, 1)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        return tab
    
    def create_observations_tab(self):
        """ایجاد تب مشاهدات"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.obs_table = QTableWidget()
        self.obs_table.setColumnCount(6)
        self.obs_table.setHorizontalHeaderLabels(["تاریخ", "محیط", "شایستگی", "نوع", "شدت", "عملیات"])
        self.obs_table.setAlternatingRowColors(True)
        self.obs_table.setStyleSheet("""
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
        
        header = self.obs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.obs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.obs_table)
        return tab
    
    def create_interventions_tab(self):
        """ایجاد تب مداخلات"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.inter_table = QTableWidget()
        self.inter_table.setColumnCount(6)
        self.inter_table.setHorizontalHeaderLabels(["تاریخ", "نوع", "مسئول", "وضعیت", "نتیجه", "عملیات"])
        self.inter_table.setAlternatingRowColors(True)
        self.inter_table.setStyleSheet("""
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
        
        header = self.inter_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.inter_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.inter_table)
        return tab
    
    def create_followups_tab(self):
        """ایجاد تب پیگیری‌ها"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.follow_table = QTableWidget()
        self.follow_table.setColumnCount(6)
        self.follow_table.setHorizontalHeaderLabels(["تاریخ", "مسئول", "وضعیت", "نوع نتیجه", "نتیجه", "عملیات"])
        self.follow_table.setAlternatingRowColors(True)
        self.follow_table.setStyleSheet("""
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
        
        header = self.follow_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.follow_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.follow_table)
        return tab
    
    # ============================================================
    # تب روند (جدید)
    # ============================================================
    
    def create_growth_context_tab(self):
        """
        تب «زمینهٔ رشد» — زمینهٔ خانوادگی و گفت‌وگو با والدین

        بازرسی یازدهم: این اطلاعات باید در کنار رفتارها و مداخلات دیده
        شود، ولی **زمینه‌ای** است؛ مبنای قضاوت دربارهٔ خانواده یا
        دانش‌آموز نیست و به‌تنهایی نتیجه‌گیری نمی‌سازد.
        """
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        note = QLabel(
            "این بخش، زمینهٔ رشد دانش‌آموز را نشان می‌دهد: وضعیت خانواده و "
            "گفت‌وگوهای والدین، در کنار رفتارهای ثبت‌شده و اقدامات انجام‌شده. "
            "این اطلاعات زمینه‌ای است، مبنای قضاوت دربارهٔ خانواده یا "
            "دانش‌آموز نیست و PARTO هیچ تشخیص روان‌شناختی یا برچسبی تولید "
            "نمی‌کند.\n"
            "مسیر تحلیل: مشاهدهٔ رفتار ← ثبت داده ← تحلیل الگو ← اقدام ← "
            "پیگیری ← نتیجه ← بررسی روند رشد."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "background-color: #0B2E4F; color: #F4C542; border: 1px solid #D9C36A;"
            "border-radius: 8px; padding: 12px; font-size: 13px;")
        layout.addWidget(note)

        # ----- زمینهٔ خانوادگی -----
        family_frame = QGroupBox("🏠 زمینهٔ خانوادگی (اطلاعات زمینه‌ای)")
        family_frame.setStyleSheet(
            "QGroupBox { color: #111111; background-color: #66BB6A; font-weight: bold;"
            "border: 2px solid #8BC34A; border-radius: 8px; margin-top: 12px; padding: 10px; }")
        family_layout = QVBoxLayout()
        family_frame.setLayout(family_layout)
        self.family_info_label = QLabel("اطلاعات زمینه‌ای خانواده ثبت نشده است.")
        self.family_info_label.setWordWrap(True)
        self.family_info_label.setStyleSheet("color: #111111; background: transparent;")
        family_layout.addWidget(self.family_info_label)
        layout.addWidget(family_frame)

        # ----- گفت‌وگو با والدین -----
        interview_frame = QGroupBox("👨‍👩‍👦 گفت‌وگو با والدین")
        interview_frame.setStyleSheet(
            "QGroupBox { color: #111111; background-color: #66BB6A; font-weight: bold;"
            "border: 2px solid #8BC34A; border-radius: 8px; margin-top: 12px; padding: 10px; }")
        interview_layout = QVBoxLayout()
        interview_frame.setLayout(interview_layout)

        self.interview_table = QTableWidget()
        self.interview_table.setColumnCount(5)
        self.interview_table.setHorizontalHeaderLabels(
            ["تاریخ", "روش", "موضوع", "وضعیت", "نتیجه"])
        self.interview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.interview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.interview_table.setMaximumHeight(200)
        interview_layout.addWidget(self.interview_table)

        self.interview_note_label = QLabel(
            "گفت‌وگوها برای درک بهتر وضعیت دانش‌آموز ثبت می‌شوند؛ نتیجهٔ آن‌ها "
            "به‌عنوان «زمینه» در تحلیل دیده می‌شود، نه به‌عنوان برچسب.")
        self.interview_note_label.setWordWrap(True)
        self.interview_note_label.setStyleSheet("color: #111111; background: transparent;")
        interview_layout.addWidget(self.interview_note_label)

        layout.addWidget(interview_frame)
        layout.addStretch()
        return tab

    def load_growth_context(self):
        """بارگذاری زمینهٔ رشد: زمینهٔ خانوادگی و گفت‌وگوهای والدین"""
        if not self.profile_id:
            return

        try:
            context = self.family_dal.get_by_student_profile(self.profile_id)
            if context:
                parts = []
                parts.append(f"وضعیت سرپرستی: {getattr(context, 'guardian_status_display', '-')}")
                parts.append(f"حمایت والدین: {getattr(context, 'parental_support', None) or '-'}")
                parts.append(f"وضعیت اقتصادی: {getattr(context, 'economic_status', None) or '-'}")
                parts.append(f"فضای مطالعه: {'دارد' if getattr(context, 'has_study_space', 0) else 'ندارد'}")
                stress = getattr(context, 'family_stress', None)
                if stress:
                    parts.append(f"فشارهای خانوادگی ثبت‌شده: {stress}")
                notes = getattr(context, 'educational_notes', None)
                if notes:
                    parts.append(f"یادداشت: {notes}")
                self.family_info_label.setText(" | ".join(parts))
            else:
                self.family_info_label.setText("اطلاعات زمینه‌ای خانواده ثبت نشده است.")
        except Exception as e:
            logger.error(f"خطا در بارگذاری زمینهٔ خانوادگی: {e}")
            self.family_info_label.setText("اطلاعات زمینه‌ای خانواده در دسترس نیست.")

        try:
            interviews = self.parent_interview_dal.get_by_student_profile(self.profile_id) or []
            self.interview_table.setRowCount(len(interviews))
            for row, interview in enumerate(interviews):
                self.interview_table.setItem(row, 0, QTableWidgetItem(interview.interview_date or "-"))
                self.interview_table.setItem(row, 1, QTableWidgetItem(
                    getattr(interview, 'method_display', None) or '-'))
                self.interview_table.setItem(row, 2, QTableWidgetItem(interview.topic or "-"))
                self.interview_table.setItem(row, 3, QTableWidgetItem(
                    getattr(interview, 'status_display', None) or '-'))
                self.interview_table.setItem(row, 4, QTableWidgetItem(
                    interview.result or interview.summary or "-"))
        except Exception as e:
            logger.error(f"خطا در بارگذاری گفت‌وگوهای والدین: {e}")
            self.interview_table.setRowCount(0)

    def create_trend_tab(self):
        """ایجاد تب روند"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # ===== خلاصه روند =====
        summary_frame = QFrame()
        summary_frame.setStyleSheet("background-color: #0B2E4F; border-radius: 8px; padding: 10px;")
        summary_layout = QGridLayout()
        summary_frame.setLayout(summary_layout)
        
        self.trend_status_label = QLabel("در حال بارگذاری...")
        self.trend_status_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        summary_layout.addWidget(self.trend_status_label, 0, 0, 1, 2)
        
        self.trend_total_label = QLabel("کل مشاهدات: 0")
        summary_layout.addWidget(self.trend_total_label, 1, 0)
        
        self.trend_positive_label = QLabel("مثبت: 0")
        self.trend_positive_label.setStyleSheet("color: #66BB6A;")
        summary_layout.addWidget(self.trend_positive_label, 1, 1)
        
        self.trend_negative_label = QLabel("منفی: 0")
        self.trend_negative_label.setStyleSheet("color: #C62828;")
        summary_layout.addWidget(self.trend_negative_label, 2, 0)
        
        self.trend_neutral_label = QLabel("خنثی: 0")
        self.trend_neutral_label.setStyleSheet("color: #D9C36A;")
        summary_layout.addWidget(self.trend_neutral_label, 2, 1)
        
        self.trend_competencies_label = QLabel("زمینه‌های پرتکرار ثبت‌شده: -")
        self.trend_competencies_label.setWordWrap(True)
        summary_layout.addWidget(self.trend_competencies_label, 3, 0, 1, 2)

        # بازرسی یازدهم: یادآوری اینکه تعداد مشاهدات، شاخص رشد نیست
        self.trend_note_label = QLabel("")
        self.trend_note_label.setWordWrap(True)
        self.trend_note_label.setStyleSheet("color: #7F8C8D; font-size: 11px;")
        summary_layout.addWidget(self.trend_note_label, 4, 0, 1, 2)
        
        layout.addWidget(summary_frame)
        
        # ===== جدول روند =====
        trend_table_frame = QGroupBox("روند تغییرات در طول زمان")
        trend_table_frame.setStyleSheet("""
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
        trend_table_layout = QVBoxLayout()
        trend_table_frame.setLayout(trend_table_layout)
        
        self.trend_table = QTableWidget()
        self.trend_table.setColumnCount(6)
        self.trend_table.setHorizontalHeaderLabels(["بازه", "تعداد", "مثبت", "منفی", "خنثی", "درصد مثبت"])
        self.trend_table.setAlternatingRowColors(True)
        self.trend_table.setStyleSheet("""
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
    background-color: #0B2E4F; padding: 5px; }
            QHeaderView::section {
                background-color: #66BB6A;
                color: #111111;
                padding: 5px;
                border: 1px solid #D9C36A;
                font-weight: bold;
            }
        """)
        header = self.trend_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.trend_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        trend_table_layout.addWidget(self.trend_table)
        
        layout.addWidget(trend_table_frame)
        
        return tab
    
    # ============================================================
    # متدهای بارگذاری داده
    # ============================================================
    
    def set_student_id(self, student_id):
        """تنظیم شناسه دانش‌آموز برای بارگذاری"""
        self.student_id = student_id
        self.load_student_data()
    
    def load_student_data(self):
        """بارگذاری اطلاعات دانش‌آموز با توجه به سال انتخاب شده"""
        if not self.student_id:
            self.clear_display()
            return
        
        try:
            self.student = self.student_dal.get_by_id(self.student_id)
            if not self.student:
                QMessageBox.critical(self, "خطا", "دانش‌آموز مورد نظر یافت نشد.")
                self.clear_display()
                return
            
            # دریافت پرونده بر اساس سال انتخاب شده
            if self.selected_year_id:
                self.profile = self.profile_dal.get_by_student_and_year(self.student_id, self.selected_year_id)
                if not self.profile:
                    self.profile = self.profile_dal.get_active_by_student(self.student_id)
            else:
                self.profile = self.profile_dal.get_active_by_student(self.student_id)
            
            self.profile_id = self.profile.id if self.profile else None
            
            # به‌روزرسانی هدر
            self.student_name_label.setText(self.student.full_name)
            if self.profile:
                # به‌روزرسانی سال انتخاب شده در کامبوباکس
                for i in range(self.year_combo.count()):
                    if self.year_combo.itemData(i) == self.profile.academic_year_id:
                        self.year_combo.setCurrentIndex(i)
                        self.selected_year_id = self.profile.academic_year_id
                        break
                
                self.student_info_label.setText(f"پایه: {self.profile.grade_display} | کلاس: {self.profile.class_name or '-'}")
                self.status_label.setText(f"وضعیت: {self.profile.status_display}")
            else:
                self.student_info_label.setText("پایه: - | کلاس: -")
                self.status_label.setText("وضعیت: بدون پرونده")
            
            # بارگذاری داده‌ها
            self.load_timeline()
            self.load_summary()
            self.load_observations()
            self.load_interventions()
            self.load_followups()
            self.load_trend_chart()  # بارگذاری روند
            self.recommendation_widget.set_profile_id(self.profile_id)
            self.load_growth_context()  # زمینهٔ رشد (خانواده و گفت‌وگوها)
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری اطلاعات:\n{e!s}")
            self.clear_display()
    
    def load_timeline(self):
        """بارگذاری Timeline"""
        if not self.profile_id:
            self.timeline_list.clear()
            return
        
        events = self.timeline_service.get_timeline(self.profile_id)
        self.timeline_list.clear()
        
        for event in events:
            date = event.get('date', 'بدون تاریخ')
            icon = event.get('icon', '📌')
            title = event.get('title', 'رویداد')
            
            item_text = f"{icon} {date} - {title}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, event)
            self.timeline_list.addItem(item)
        
        summary = self.timeline_service.get_timeline_summary(self.profile_id)
        self.obs_count_label.setText(f"مشاهدات: {summary['observations']}")
        self.inter_count_label.setText(f"مداخلات: {summary['interventions']}")
        self.follow_count_label.setText(f"پیگیری‌ها: {summary['followups']}")
        self.pending_label.setText(f"پیگیری‌های باز: {summary['pending_followups']}")
    
    def on_timeline_item_clicked(self, item):
        """نمایش جزئیات رویداد انتخاب شده در Timeline"""
        event = item.data(Qt.ItemDataRole.UserRole)
        if not event:
            return
        
        details = self._format_event_details(event)
        self.details_text.setText(details)
    
    def _format_event_details(self, event):
        """فرمت‌سازی جزئیات رویداد برای نمایش"""
        lines = []
        lines.append(f"📌 **{event['type_display']}**")
        lines.append("")
        lines.append(f"📅 تاریخ: {event['date'] or 'نامشخص'}")
        lines.append(f"📝 عنوان: {event['title']}")
        lines.append("")
        lines.append("📄 توضیحات:")
        lines.append(f"{event['description'] or 'توضیحاتی ثبت نشده است.'}")
        lines.append("")
        
        if event['type'] == 'observation':
            details = event['details']
            lines.append("━━━━━━━━━━ مدل ABC ━━━━━━━━━━")
            lines.append(f"🔴 A - زمینه: {details.get('antecedent') or 'ثبت نشده'}")
            lines.append(f"🟡 B - رفتار: {details.get('behavior') or 'ثبت نشده'}")
            lines.append(f"🟢 C - پیامد: {details.get('consequence') or 'ثبت نشده'}")
            lines.append("")
            lines.append(f"🏷️ نوع: {details.get('behavior_type') or 'نامشخص'}")
            lines.append(f"⭐ شدت: {details.get('severity_display') or 'نامشخص'}")
            lines.append(f"📍 محیط: {details.get('location') or 'نامشخص'}")
            lines.append(f"👤 مشاهده‌گر: {details.get('staff') or 'نامشخص'}")
            
        elif event['type'] == 'intervention':
            details = event['details']
            lines.append(f"🎯 نوع مداخله: {details.get('type') or 'نامشخص'}")
            lines.append(f"📌 وضعیت: {details.get('status') or 'نامشخص'}")
            if details.get('goal'):
                lines.append(f"🎯 هدف: {details['goal']}")
            if details.get('result'):
                lines.append(f"📊 نتیجه: {details['result']}")
            lines.append(f"👤 مسئول: {details.get('staff') or 'نامشخص'}")
            
        elif event['type'] == 'followup':
            details = event['details']
            lines.append(f"📌 وضعیت: {details.get('status') or 'نامشخص'}")
            if details.get('method'):
                lines.append(f"📞 روش: {details['method']}")
            if details.get('next_action_date'):
                lines.append(f"📅 اقدام بعدی: {details['next_action_date']}")
            if details.get('result_type'):
                lines.append(f"📊 نوع نتیجه: {details['result_type']}")
            if details.get('result_description'):
                lines.append(f"📄 شرح نتیجه: {details['result_description']}")
            lines.append(f"👤 مسئول: {details.get('staff') or 'نامشخص'}")
        
        return "\n".join(lines)
    
    def load_summary(self):
        """بارگذاری خلاصه پرونده"""
        if not self.profile_id:
            return
        
        observations = self.observation_dal.get_by_student_profile(self.profile_id)

        # ===== اصلاح (بازرسی یازدهم) =====
        # پیش از این فقط «تعداد مشاهدات مثبت/منفی» نمایش داده می‌شد.
        # حالا الگوی تکرارشوندهٔ رفتارها بر پایهٔ نوع رفتار (و نه شدت)
        # ساخته می‌شود؛ یک مشاهدهٔ منفرد نتیجه‌گیری نمی‌سازد.
        #
        # (بازرسی دوازدهم) نام شایستگی‌ها با یک کوئری دسته‌ای خوانده
        # می‌شود، نه یک کوئری برای هر شایستگی (رفع N+1؛ خروجی یکسان).
        _comp_titles = self.competency_dal.get_titles_by_ids(
            [o.competency_id for o in observations])
        patterns = summarize_by_competency(
            observations, lambda cid: _comp_titles.get(cid))

        def _format(entries, behavior_field, empty_text):
            if not entries:
                return empty_text
            parts = []
            for entry in entries[:4]:
                parts.append(f"{entry['competency']} "
                             f"({entry[behavior_field]} مورد از {entry['count']} مشاهده)")
            return " | ".join(parts)

        strengths_text = _format(
            patterns['strengths'], 'positive',
            "الگوی تکرارشوندهٔ رفتار مثبت ثبت نشده است.")
        needs_text = _format(
            patterns['needs_attention'], 'negative',
            "الگوی تکرارشوندهٔ رفتار منفی ثبت نشده است.")

        self.strengths_label.setText(f"توانمندی‌ها (الگوی تکرارشوندهٔ رفتار مثبت): {strengths_text}")
        self.weaknesses_label.setText(
            f"زمینه‌های نیازمند توجه (الگوی تکرارشوندهٔ رفتار منفی): {needs_text}")
    
    def load_observations(self):
        """بارگذاری مشاهدات در جدول"""
        if not self.profile_id:
            return
        
        observations = self.observation_dal.get_by_student_profile(self.profile_id)
        self.obs_table.setRowCount(len(observations))

        # (بازرسی دوازدهم) یک کوئری دسته‌ای به‌جای یک کوئری برای هر ردیف
        _comp_titles = self.competency_dal.get_titles_by_ids(
            [o.competency_id for o in observations])

        for row, obs in enumerate(observations):
            self.obs_table.setItem(row, 0, QTableWidgetItem(obs.observation_date or ""))
            self.obs_table.setItem(row, 1, QTableWidgetItem(obs.location or ""))

            comp_name = "نامشخص"
            if obs.competency_id:
                comp_name = _comp_titles.get(obs.competency_id, "نامشخص")
            self.obs_table.setItem(row, 2, QTableWidgetItem(comp_name))
            
            self.obs_table.setItem(row, 3, QTableWidgetItem(obs.behavior_type or "خنثی"))
            self.obs_table.setItem(row, 4, QTableWidgetItem("⭐" * obs.severity))
            
            view_btn = QPushButton("👁️")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("background-color: #0B2E4F; color: #F4C542; border: none; border-radius: 4px;")
            view_btn.clicked.connect(lambda checked, o=obs: self.view_observation(o))
            self.obs_table.setCellWidget(row, 5, view_btn)
    
    def load_interventions(self):
        """بارگذاری مداخلات در جدول"""
        if not self.profile_id:
            return
        
        interventions = self.intervention_dal.get_by_student_profile(self.profile_id)
        self.inter_table.setRowCount(len(interventions))

        # (بازرسی دوازدهم) یک کوئری دسته‌ای به‌جای یک کوئری برای هر ردیف
        _staff_names = self.staff_dal.get_names_by_ids(
            [i.staff_id for i in interventions])

        for row, inter in enumerate(interventions):
            self.inter_table.setItem(row, 0, QTableWidgetItem(inter.date or ""))
            self.inter_table.setItem(row, 1, QTableWidgetItem(inter.type_display))

            staff_name = "نامشخص"
            if inter.staff_id:
                staff_name = _staff_names.get(inter.staff_id, "نامشخص")
            self.inter_table.setItem(row, 2, QTableWidgetItem(staff_name))
            
            self.inter_table.setItem(row, 3, QTableWidgetItem(inter.status_display))
            self.inter_table.setItem(row, 4, QTableWidgetItem(inter.result or "نامشخص"))
            
            view_btn = QPushButton("👁️")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("background-color: #F28C28; color: #111111; border: none; border-radius: 4px;")
            view_btn.clicked.connect(lambda checked, i=inter: self.view_intervention(i))
            self.inter_table.setCellWidget(row, 5, view_btn)
    
    def load_followups(self):
        """بارگذاری پیگیری‌ها در جدول"""
        if not self.profile_id:
            return
        
        followups = self.followup_dal.get_by_student_profile(self.profile_id)
        self.follow_table.setRowCount(len(followups))

        # (بازرسی دوازدهم) یک کوئری دسته‌ای به‌جای یک کوئری برای هر ردیف
        _staff_names = self.staff_dal.get_names_by_ids(
            [f.staff_id for f in followups])

        for row, follow in enumerate(followups):
            self.follow_table.setItem(row, 0, QTableWidgetItem(follow.date or ""))

            staff_name = "نامشخص"
            if follow.staff_id:
                staff_name = _staff_names.get(follow.staff_id, "نامشخص")
            self.follow_table.setItem(row, 1, QTableWidgetItem(staff_name))
            
            self.follow_table.setItem(row, 2, QTableWidgetItem(follow.status_display))
            self.follow_table.setItem(row, 3, QTableWidgetItem(follow.result_type_display))
            self.follow_table.setItem(row, 4, QTableWidgetItem(follow.result_description or "نامشخص"))
            
            view_btn = QPushButton("👁️")
            view_btn.setFixedSize(30, 30)
            view_btn.setStyleSheet("background-color: #66BB6A; color: #111111; border: none; border-radius: 4px;")
            view_btn.clicked.connect(lambda checked, f=follow: self.view_followup(f))
            self.follow_table.setCellWidget(row, 5, view_btn)
    
    # ============================================================
    # متدهای روند
    # ============================================================
    
    def load_trend_chart(self):
        """بارگذاری نمودار روند دانش‌آموز"""
        if not self.profile_id:
            return
        
        trend = self.trend_service.analyze_student_trend(self.profile_id)
        if not trend['success']:
            self.trend_status_label.setText(f"⚠️ {trend.get('error', 'داده‌ای موجود نیست')}")
            return
        
        # به‌روزرسانی آمار
        self.trend_total_label.setText(f"کل مشاهدات: {trend['total_observations']}")
        self.trend_positive_label.setText(f"مثبت: {trend['positive_count']}")
        self.trend_negative_label.setText(f"منفی: {trend['negative_count']}")
        self.trend_neutral_label.setText(f"خنثی: {trend['neutral_count']}")
        
        # نمایش روند کلی
        overall = trend['overall_trend']
        self.trend_status_label.setText(f"{overall['icon']} {overall['message']}")
        self.trend_status_label.setStyleSheet(f"color: {overall.get('color', '#F4C542')}; font-weight: bold;")
        # یادآوری محتوایی: تعداد مشاهدات، شاخص رشد نیست (بازرسی یازدهم)
        # + مسیر تغییر بین بازه‌ها (بازرسی سیزدهم): جهت روند فقط از
        #   ابتدا/انتها گرفته نمی‌شود؛ گام‌های میانی هم نشان داده می‌شوند.
        note_lines = []
        path_text = overall.get('path_text') or ''
        if path_text:
            note_lines.append(f"مسیر تغییر بین بازه‌ها: {path_text}")
        direction = overall.get('direction') or {}
        if direction.get('message'):
            note_lines.append(direction['message'])
        for caution in direction.get('caution_notes') or []:
            note_lines.append(caution)
        note = trend.get('volume_note')
        if note:
            note_lines.append(note)
        if note_lines and hasattr(self, 'trend_note_label'):
            self.trend_note_label.setText("\n".join(note_lines))
        
        # نمایش زمینه‌های پرتکرار (بر پایهٔ نوع رفتار ثبت‌شده)
        if trend['top_competencies']:
            # بازرسی یازدهم: خروجی (نام، تعداد، برچسب الگو) است
            parts = []
            for item in trend['top_competencies'][:5]:
                name, count = item[0], item[1]
                label = item[2] if len(item) > 2 else ''
                parts.append(f"{name} ({count} مشاهده — {label})" if label
                             else f"{name} ({count} مشاهده)")
            self.trend_competencies_label.setText(
                "زمینه‌های پرتکرار ثبت‌شده: " + " | ".join(parts))
        else:
            self.trend_competencies_label.setText(
                "زمینه‌های پرتکرار ثبت‌شده: ثبت نشده")
        
        # به‌روزرسانی جدول روند
        self.load_trend_table(trend['trend_data'])
    
    def load_trend_table(self, trend_data):
        """بارگذاری جدول روند"""
        self.trend_table.setRowCount(len(trend_data))
        
        for row, period in enumerate(trend_data):
            self.trend_table.setItem(row, 0, QTableWidgetItem(period['label']))
            self.trend_table.setItem(row, 1, QTableWidgetItem(str(period['total'])))
            self.trend_table.setItem(row, 2, QTableWidgetItem(str(period['positive'])))
            self.trend_table.setItem(row, 3, QTableWidgetItem(str(period['negative'])))
            self.trend_table.setItem(row, 4, QTableWidgetItem(str(period['neutral'])))
            self.trend_table.setItem(row, 5, QTableWidgetItem(f"{period['positive_percent']}%"))
            
            # رنگ‌بندی بر اساس درصد مثبت
            if period['positive_percent'] >= 60:
                color = "#66BB6A"  # سبز
            elif period['positive_percent'] >= 40:
                color = "#F4D35E"  # نارنجی
            else:
                color = "#C62828"  # قرمز
            
            for col in range(6):
                item = self.trend_table.item(row, col)
                if item:
                    item.setForeground(QColor(color))
    
    # ============================================================
    # متدهای عملیاتی
    # ============================================================
    
    def clear_display(self):
        """پاک کردن نمایش"""
        self.student_name_label.setText("دانش‌آموزی انتخاب نشده است")
        self.student_info_label.setText("پایه: - | کلاس: -")
        self.status_label.setText("وضعیت: -")
        self.timeline_list.clear()
        self.details_text.clear()
        self.obs_count_label.setText("مشاهدات: 0")
        self.inter_count_label.setText("مداخلات: 0")
        self.follow_count_label.setText("پیگیری‌ها: 0")
        self.pending_label.setText("پیگیری‌های باز: 0")
        self.strengths_label.setText("هیچ نقطه قوتی ثبت نشده است.")
        self.weaknesses_label.setText("هیچ زمینه‌ای ثبت نشده است.")
        if hasattr(self, 'recommendation_widget'):
            self.recommendation_widget.set_profile_id(None)
        self.obs_table.setRowCount(0)
        self.inter_table.setRowCount(0)
        self.follow_table.setRowCount(0)
        self.trend_table.setRowCount(0)
        self.trend_status_label.setText("در حال بارگذاری...")
        self.trend_total_label.setText("کل مشاهدات: 0")
        self.trend_positive_label.setText("مثبت: 0")
        self.trend_negative_label.setText("منفی: 0")
        self.trend_neutral_label.setText("خنثی: 0")
        self.trend_competencies_label.setText("زمینه‌های پرتکرار ثبت‌شده: -")
        self.trend_note_label.setText("")
        self.family_info_label.setText("اطلاعات زمینه‌ای خانواده ثبت نشده است.")
        self.interview_table.setRowCount(0)
    
    def add_observation(self):
        if not self.student_id:
            QMessageBox.warning(self, "توجه", "دانش‌آموزی انتخاب نشده است.")
            return
        
        form = ObservationForm(student_id=self.student_id, parent=self)
        if form.exec() == QDialog.DialogCode.Accepted:
            self.load_student_data()
            QMessageBox.information(self, "موفقیت", "مشاهده با موفقیت ثبت شد.")
    
    def on_intervention_requested(self, data=None):
        """درخواست ثبت مداخله از روی یک پیشنهاد (تب پیشنهادها)"""
        self.add_intervention()

    def add_intervention(self):
        if not self.student_id:
            QMessageBox.warning(self, "توجه", "دانش‌آموزی انتخاب نشده است.")
            return
        
        form = InterventionForm(student_id=self.student_id, parent=self)
        if form.exec() == QDialog.DialogCode.Accepted:
            self.load_student_data()
            QMessageBox.information(self, "موفقیت", "مداخله با موفقیت ثبت شد.")
    
    def add_followup(self):
        if not self.profile_id:
            QMessageBox.warning(self, "توجه", "هیچ پرونده فعالی برای این دانش‌آموز وجود ندارد.")
            return
        
        interventions = self.intervention_dal.get_by_student_profile(self.profile_id)
        if not interventions:
            QMessageBox.warning(self, "توجه", "هیچ مداخله‌ای برای پیگیری وجود ندارد.")
            return
        
        form = FollowUpForm(parent=self)
        if form.exec() == QDialog.DialogCode.Accepted:
            self.load_student_data()
            QMessageBox.information(self, "موفقیت", "پیگیری با موفقیت ثبت شد.")
    
    def view_observation(self, obs):
        details = f"""
📅 تاریخ: {obs.observation_date}
📍 محیط: {obs.location}
📝 شرح: {obs.description}
🏷️ نوع: {obs.behavior_type}
⭐ شدت: {obs.severity_display}

━━━━━━━━━━ مدل ABC ━━━━━━━━━━
🔴 A - زمینه: {obs.antecedent or 'ثبت نشده'}
🟡 B - رفتار: {obs.behavior or 'ثبت نشده'}
🟢 C - پیامد: {obs.consequence or 'ثبت نشده'}
"""
        QMessageBox.information(self, "جزئیات مشاهده", details)
    
    def view_intervention(self, inter):
        details = f"""
📅 تاریخ: {inter.date}
🎯 نوع: {inter.type_display}
📝 شرح: {inter.description}
🎯 هدف: {inter.goal or 'ثبت نشده'}
📊 نتیجه: {inter.result or 'ثبت نشده'}
📌 وضعیت: {inter.status_display}
"""
        QMessageBox.information(self, "جزئیات مداخله", details)
    
    def view_followup(self, follow):
        details = f"""
📅 تاریخ: {follow.date}
📝 شرح: {follow.description}
📊 نوع نتیجه: {follow.result_type_display}
📄 شرح نتیجه: {follow.result_description or 'ثبت نشده'}
📌 وضعیت: {follow.status_display}
📅 اقدام بعدی: {follow.next_action_date or 'تعیین نشده'}
"""
        QMessageBox.information(self, "جزئیات پیگیری", details)
    
    def open_attachments(self):
        """مدیریت پیوست‌های دانش‌آموز (BUG-027 — نقطهٔ ورودی AttachmentDialog)"""
        if not self.student_id:
            QMessageBox.warning(self, "توجه", "ابتدا یک دانش‌آموز را انتخاب کنید.")
            return
        from views.dialogs.attachment_dialog import AttachmentDialog
        dialog = AttachmentDialog("student", int(self.student_id), self)
        dialog.exec()

    def generate_report(self):
        """باز کردن گزارش کامل همین دانش‌آموز در صفحهٔ گزارش‌ها (بازرسی شانزدهم)"""
        if not self.profile_id:
            QMessageBox.warning(self, "توجه", "هیچ پرونده فعالی برای این دانش‌آموز وجود ندارد.")
            return
        if not self.student_id:
            QMessageBox.warning(self, "توجه", "دانش‌آموزی انتخاب نشده است.")
            return
        self.report_requested.emit(int(self.student_id))