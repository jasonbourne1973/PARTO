"""
پنجره اصلی برنامه PARTO - نسخه اصلاح شده با استایل یکپارچه
"""

import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QMessageBox,
    QComboBox, QScrollArea, QApplication, QDialog,
    QStatusBar, QToolBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction, QIcon, QPixmap, QFont

from views.pages.dashboard_page import DashboardPage
from views.pages.students_page import StudentsPage
from views.pages.observations_page import ObservationsPage
from views.pages.indicators_page import IndicatorsPage
from views.pages.analysis_page import AnalysisPage
from views.pages.reports_page import ReportsPage
from views.pages.settings_page import SettingsPage
from views.pages.interventions_page import InterventionsPage
from views.pages.followups_page import FollowUpsPage
from views.dialogs.login_dialog import LoginDialog
from views.dialogs.change_password_dialog import ChangePasswordDialog
from views.widgets.notification_widget import NotificationWidget
from dal.academic_year_dal import AcademicYearDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from database.connection import DatabaseConnection
from utils.logger import get_logger
from utils.theme_manager import ThemeManager
from views.pages.academic_structure_page import AcademicStructurePage
from config.settings import APP_NAME, APP_FULL_NAME, APP_VERSION, APP_AUTHOR

class MainWindow(QMainWindow):
    """
    پنجره اصلی برنامه PARTO - با استایل یکپارچه
    """

    academic_year_changed = Signal(int)

    def __init__(self):
        super().__init__()

        self.academic_year_dal = AcademicYearDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.all_academic_years = []
        self.db = DatabaseConnection()
        self.logger = get_logger(self.__class__.__name__)
        self.theme_manager = ThemeManager()

        self.is_logged_in = False
        self.current_user_id = None
        self.current_username = None
        self.current_user_role = None

        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self.auto_logout)
        self.idle_timer.setInterval(30 * 60 * 1000)

        self.show_login_dialog()

        if self.is_logged_in:
            self.setup_ui()
            self.idle_timer.start()
        else:
            QApplication.quit()

    def show_login_dialog(self):
        try:
            login_dialog = LoginDialog(self)
            login_dialog.login_successful.connect(self.on_login_successful)
            login_dialog.need_change_password.connect(self.on_need_change_password)

            result = login_dialog.exec()

            if result != QDialog.DialogCode.Accepted:
                self.is_logged_in = False
        except Exception as e:
            traceback.print_exc()
            self.is_logged_in = False

    def on_login_successful(self, user_id, username, role):
        self.is_logged_in = True
        self.current_user_id = user_id
        self.current_username = username
        self.current_user_role = role
        self.db.set_current_user(user_id)
        self.logger.info(f"کاربر {username} با نقش {role} وارد شد.")

    def on_need_change_password(self, user_id, username):
        self.current_user_id = user_id
        self.current_username = username

        dialog = ChangePasswordDialog(
            username=username,
            user_id=user_id,
            is_first_login=True,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(
                self,
                "موفقیت",
                "رمز عبور با موفقیت تغییر یافت.\nلطفاً با رمز جدید وارد شوید."
            )
            self.show_login_dialog()
        else:
            QMessageBox.warning(
                self,
                "توجه",
                "برای استفاده از برنامه باید رمز عبور خود را تغییر دهید."
            )
            self.close()

    def setup_ui(self):
        # ===== تنظیمات اولیه پنجره =====
        self.setWindowTitle(f"{APP_NAME} - سامانه پرونده دانش‌آموزان")
        self.setGeometry(100, 100, 1200, 800)

        # ===== بارگذاری استایل اصلی =====
        self._load_stylesheet()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        # ===== منوی سمت چپ =====
        menu_frame = QFrame()
        menu_frame.setObjectName("MenuFrame")
        menu_frame.setStyleSheet("""
            QFrame#MenuFrame {
                background-color: #0B2E4F;
                border: none;
            }
        """)
        # عرض ثابت و خوانا برای منوی سمت چپ
        menu_width = 240
        menu_frame.setFixedWidth(menu_width)
        menu_frame.setMinimumWidth(menu_width)
        menu_frame.setMaximumWidth(menu_width)
        menu_frame.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding
        )

        menu_scroll = QScrollArea()
        menu_scroll.setWidgetResizable(True)
        menu_scroll.setFrameShape(QFrame.Shape.NoFrame)
        menu_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        menu_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        menu_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        menu_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #0B2E4F;
            }
        """)
        menu_scroll.viewport().setStyleSheet("background-color: #0B2E4F;")

        menu_content = QWidget()
        menu_content.setFixedWidth(menu_width)
        menu_content.setStyleSheet("background-color: #0B2E4F;")
        menu_layout = QVBoxLayout(menu_content)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(2)

        # ===== هدر منو =====
        user_frame = QFrame()
        user_frame.setStyleSheet("""
            QFrame {
                background-color: #08223A;
                padding: 8px;
                margin: 0px 0px 5px 0px;
            }
        """)
        user_layout = QVBoxLayout()
        user_layout.setContentsMargins(8, 8, 8, 8)
        user_layout.setSpacing(2)
        user_frame.setLayout(user_layout)

        user_icon_label = QLabel("👤")
        user_icon_label.setStyleSheet("font-size: 20px; color: #08223A;")
        user_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        user_layout.addWidget(user_icon_label)

        self.user_name_label = QLabel(self.current_username or "کاربر")
        self.user_name_label.setStyleSheet("color: #08223A; font-size: 13px; font-weight: bold;")
        self.user_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        user_layout.addWidget(self.user_name_label)

        self.user_role_label = QLabel(self.current_user_role or "نقش")
        self.user_role_label.setStyleSheet("color: #D9C36A; font-size: 11px;")
        self.user_role_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        user_layout.addWidget(self.user_role_label)

        menu_layout.addWidget(user_frame)

        # ===== عنوان برنامه =====
        title_label = QLabel(APP_NAME)
        title_label.setStyleSheet("color: #F4C542; font-size: 18px; font-weight: bold; padding: 12px 5px; border-bottom: 2px solid #66BB6A;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(title_label)

        # ===== انتخاب سال تحصیلی =====
        self.year_label = QLabel("📅 سال: بارگذاری...")
        self.year_label.setStyleSheet("color: #F4C542; font-size: 11px; font-weight: bold; padding: 5px 8px; background-color: #66BB6A; border-radius: 4px; margin: 3px 8px;")
        self.year_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.year_label)

        # ===== دکمه‌های منو =====
        # ایجاد دکمه‌ها با کلاس MenuButton
        self.menu_buttons = {}
        menu_items = [
            ("btn_dashboard", "📊 داشبورد", 1),
            ("btn_students", "📋 دانش‌آموزان", 2),
            ("btn_observations", "📝 مشاهدات", 3),
            ("btn_interventions", "🛠️ مداخلات", 4),
            ("btn_followups", "🔔 پیگیری‌ها", 5),
            ("btn_indicators", "📊 شاخص‌ها", 6),
            ("btn_analysis", "📈 تحلیل روند", 7),
            ("btn_reports", "📄 گزارش‌ها", 8),
            ("btn_counseling", "🧑‍⚕️ جلسات مشاوره", 11),
            ("btn_activities", "🎯 فعالیت‌ها", 12),
            ("btn_goals", "🎯 اهداف فردی", 13),
            ("btn_academic_structure", "🏫 ساختار آموزشی", 10),
            ("btn_settings", "⚙️ تنظیمات", 9),
        ]

        for btn_name, btn_text, page_index in menu_items:
            btn = QPushButton(btn_text)
            btn.setProperty("class", "MenuButton")  # برای سازگاری با QSS
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # استایل مستقیم برای جلوگیری از سفیدشدن متن روی پس‌زمینه روشن
            # در صورتی که selector کلاس در QSS نسخه کاربر اعمال نشود.
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #F4C542;
                    border: none;
                    border-radius: 0px;
                    padding: 10px 16px;
                    text-align: right;
                    font-size: 13px;
                    font-weight: 600;
                    min-height: 40px;
                }
                QPushButton:hover {
                    background-color: #174F78;
                    color: #FFE8A3;
                }
                QPushButton:pressed {
                    background-color: #08223A;
                    color: #FFE8A3;
                }
            """)
            btn.clicked.connect(lambda checked, idx=page_index: self.stacked_widget.setCurrentIndex(idx))
            menu_layout.addWidget(btn)
            self.menu_buttons[btn_name] = btn
            setattr(self, btn_name, btn)

        # ===== دکمه خروج =====
        menu_layout.addStretch()

        self.btn_logout = QPushButton("🚪 خروج")
        self.btn_logout.setObjectName("btnLogout")
        self.btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_logout.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F4D35E;
                border: none;
                border-top: 1px solid #174F78;
                padding: 12px 16px;
                text-align: right;
                font-size: 13px;
                font-weight: bold;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #174F78;
                color: #F4D35E;
            }
        """)
        self.btn_logout.clicked.connect(self.logout)
        menu_layout.addWidget(self.btn_logout)

        menu_scroll.setWidget(menu_content)

        # قرار دادن اسکرول منو داخل قاب ثابت؛ قبلاً menu_frame ساخته می‌شد
        # اما هرگز به layout اضافه نمی‌شد و QScrollArea به عرض بسیار کم
        # جمع می‌شد.
        menu_frame_layout = QVBoxLayout(menu_frame)
        menu_frame_layout.setContentsMargins(0, 0, 0, 0)
        menu_frame_layout.setSpacing(0)
        menu_frame_layout.addWidget(menu_scroll)

        # ===== محتوای سمت راست =====
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #061B2D,
                    stop: 0.35 #0B2E4F,
                    stop: 0.65 #174F78,
                    stop: 1 #08223A
                );
            }
        """)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_frame.setLayout(self.content_layout)

        # ===== هدر =====
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #0B2E4F; border-bottom: 1px solid #D9C36A; padding: 5px 15px;")
        header_layout = QHBoxLayout()
        header_frame.setLayout(header_layout)

        header_title = QLabel(f"📋 {APP_NAME}")
        header_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F4C542;")
        header_layout.addWidget(header_title)
        header_layout.addStretch()

        user_info_label = QLabel(f"👤 {self.current_username or 'کاربر'}")
        user_info_label.setStyleSheet("font-size: 13px; color: #66BB6A; font-weight: 600;")
        header_layout.addWidget(user_info_label)

        version_label = QLabel(f"نسخه {APP_VERSION}")
        version_label.setStyleSheet("font-size: 11px; color: #D9C36A; padding: 0 10px;")
        header_layout.addWidget(version_label)

        header_layout.addStretch()

        self.notification_btn = QPushButton("🔔")
        self.notification_btn.setFixedSize(36, 36)
        self.notification_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.notification_btn.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; font-size: 18px; border-radius: 18px; }
            QPushButton:hover { background-color: #08223A; }
        """)
        self.notification_btn.clicked.connect(self.toggle_notifications)
        header_layout.addWidget(self.notification_btn)

        self.notification_badge = QLabel("")
        self.notification_badge.setObjectName("NotificationBadge")
        self.notification_badge.setFixedSize(20, 20)
        self.notification_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notification_badge.setVisible(False)
        header_layout.addWidget(self.notification_badge)

        self.notification_widget = NotificationWidget(self)
        self.notification_widget.notification_clicked.connect(self.on_notification_clicked)

        self.notification_timer = QTimer()
        self.notification_timer.timeout.connect(self.update_notification_badge)
        self.notification_timer.start(60000)
        self.update_notification_badge()

        header_layout.addSpacing(15)

        # انتخاب تم در هدر بالایی، کنار انتخاب سال تحصیلی قرار گرفته است.
        header_layout.addWidget(QLabel("🎨 تم:"))
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(175)
        self.theme_combo.setToolTip("انتخاب ظاهر برنامه")
        for theme_key, theme_data in ThemeManager.THEMES.items():
            self.theme_combo.addItem(theme_data["title"], theme_key)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        header_layout.addWidget(self.theme_combo)

        header_layout.addSpacing(10)
        header_layout.addWidget(QLabel("سال تحصیلی:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(120)
        self.year_combo.setStyleSheet("""
            QComboBox { background-color: #08223A; color: #F4C542; padding: 3px 8px; border-radius: 12px; font-weight: bold; font-size: 12px; border: 1px solid #8BC34A; }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { image: none; }
            QComboBox:hover { background-color: #174F78; }
        """)
        self.year_combo.currentIndexChanged.connect(self.on_year_changed)
        header_layout.addWidget(self.year_combo)

        self.content_layout.addWidget(header_frame)

        # ===== Stacked Widget =====
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background: transparent;")

        # صفحه 0: خوش‌آمدگویی
        self.stacked_widget.addWidget(self._create_welcome_page())

        # صفحات دیگر
        self.dashboard_page = DashboardPage()
        self.stacked_widget.addWidget(self.dashboard_page)

        self.students_page = StudentsPage()
        self.students_page.student_double_clicked.connect(self.open_student_profile)
        self.students_page.table.itemDoubleClicked.connect(self.on_student_double_clicked)
        self.stacked_widget.addWidget(self.students_page)

        self.observations_page = ObservationsPage()
        self.stacked_widget.addWidget(self.observations_page)

        self.interventions_page = InterventionsPage()
        self.stacked_widget.addWidget(self.interventions_page)

        self.followups_page = FollowUpsPage()
        self.stacked_widget.addWidget(self.followups_page)

        self.indicators_page = IndicatorsPage()
        self.stacked_widget.addWidget(self.indicators_page)

        self.analysis_page = AnalysisPage()
        self.stacked_widget.addWidget(self.analysis_page)

        self.reports_page = ReportsPage()
        self.stacked_widget.addWidget(self.reports_page)

        self.settings_page = SettingsPage()
        self.stacked_widget.addWidget(self.settings_page)

        self.academic_structure_page = AcademicStructurePage()
        self.academic_structure_page.student_selected.connect(self.open_student_profile)
        self.stacked_widget.addWidget(self.academic_structure_page)

        # گزارش‌ها و داشبورد تحلیلی داخل تب‌های صفحات اصلی نمایش داده می‌شوند.
        # در اینجا صفحه مستقل دیگری ساخته نمی‌شود تا منوی اصلی و stacked widget
        # شلوغ یا تکراری نشوند.
        from views.pages.counseling_page import CounselingPage
        self.counseling_page = CounselingPage()
        self.counseling_page.student_selected.connect(self.open_student_profile_by_profile_id)
        self.stacked_widget.addWidget(self.counseling_page)

        from views.pages.activities_page import ActivitiesPage
        self.activities_page = ActivitiesPage()
        self.activities_page.student_selected.connect(self.open_student_profile_by_profile_id)
        self.stacked_widget.addWidget(self.activities_page)

        from views.pages.goals_page import GoalsPage
        self.goals_page = GoalsPage()
        self.goals_page.student_selected.connect(self.open_student_profile_by_profile_id)
        self.stacked_widget.addWidget(self.goals_page)

        self.content_layout.addWidget(self.stacked_widget)

        main_layout.addWidget(menu_frame)
        main_layout.addWidget(self.content_frame)
        main_layout.setStretchFactor(menu_frame, 0)
        main_layout.setStretchFactor(self.content_frame, 1)

        self.load_academic_years()
        self.update_academic_year_display()

        self.installEventFilter(self)

        saved_theme = self.theme_manager.saved_theme()
        theme_index = self.theme_combo.findData(saved_theme)
        self.theme_combo.blockSignals(True)
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)
        self.theme_combo.blockSignals(False)
        self.theme_manager.apply(self, saved_theme)

    def on_theme_changed(self, index):
        """اعمال تم انتخاب‌شده بدون تغییر در داده یا منطق برنامه."""
        if index < 0:
            return
        theme_name = self.theme_combo.itemData(index)
        if theme_name:
            self.theme_manager.apply(self, theme_name)

    def _load_stylesheet(self):
        """بارگذاری فایل استایل اصلی"""
        try:
            style_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets", "styles", "main_style.qss"
            )
            if os.path.exists(style_path):
                with open(style_path, "r", encoding="utf-8") as f:
                    stylesheet = f.read()
                application = QApplication.instance()
                if application is not None:
                    application.setStyleSheet(stylesheet)
                else:
                    self.setStyleSheet(stylesheet)
                print(f"✅ استایل از {style_path} بارگذاری شد")
            else:
                print(f"⚠️ فایل استایل یافت نشد: {style_path}")
        except Exception as e:
            print(f"❌ خطا در بارگذاری استایل: {e}")

    def _create_welcome_page(self):
        welcome_page = QWidget()
        welcome_page.setStyleSheet("background-color: #08223A;")
        welcome_layout = QVBoxLayout()
        welcome_page.setLayout(welcome_layout)

        from config.settings import LOGO_PATH
        if os.path.exists(LOGO_PATH):
            background_label = QLabel(welcome_page)
            from PySide6.QtGui import QPixmap, QPainter
            from PySide6.QtCore import QRect

            pixmap = QPixmap(LOGO_PATH)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    600, 600,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                blurred_pixmap = QPixmap(scaled_pixmap.size())
                blurred_pixmap.fill(Qt.GlobalColor.transparent)

                painter = QPainter(blurred_pixmap)
                painter.setOpacity(0.12)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.end()

                background_label.setPixmap(blurred_pixmap)
                background_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                background_label.setGeometry(QRect(0, 0, 1200, 700))
                background_label.setStyleSheet("background-color: transparent;")
                background_label.lower()

        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(50, 50, 50, 50)
        content_layout.addStretch()

        if os.path.exists(LOGO_PATH):
            logo_label = QLabel()
            pixmap = QPixmap(LOGO_PATH)
            if not pixmap.isNull():
                scaled_logo = pixmap.scaled(
                    180, 180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                logo_label.setPixmap(scaled_logo)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                content_layout.addWidget(logo_label)
                content_layout.addSpacing(10)

        welcome_label = QLabel(f"به نرم‌افزار {APP_NAME} خوش آمدید")
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #08223A;
                padding: 15px 30px;
                background-color: rgba(255, 255, 255, 0.75);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
        """)
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(welcome_label)
        content_layout.addSpacing(5)

        user_label = QLabel(f"{self.current_username} عزیز")
        user_label.setStyleSheet("""
            QLabel {
                font-size: 22px;
                color: #F4C542;
                padding: 10px 25px;
                background-color: rgba(255, 255, 255, 0.5);
                border-radius: 10px;
            }
        """)
        user_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(user_label)
        content_layout.addSpacing(15)

        desc_label = QLabel("📋 از منوی سمت چپ یکی از گزینه‌ها را انتخاب کنید")
        desc_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #D9C36A;
                padding: 10px 25px;
                background-color: rgba(255, 255, 255, 0.4);
                border-radius: 10px;
            }
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(desc_label)

        content_layout.addSpacing(30)

        version_info = QLabel(f"نسخه {APP_VERSION} | توسعه‌دهنده: {APP_AUTHOR}")
        version_info.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #D9C36A;
                padding: 8px 20px;
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 8px;
            }
        """)
        version_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(version_info)

        content_layout.addStretch()

        welcome_layout.addWidget(content_widget)

        return welcome_page

    def load_academic_years(self):
        try:
            self.all_academic_years = self.academic_year_dal.get_all(include_archived=True)
            self.year_combo.clear()
            for year in self.all_academic_years:
                display_text = f"{year.title} {'📦' if year.is_archived == 1 else ''}"
                self.year_combo.addItem(display_text, year.id)

            active_year = self.academic_year_dal.get_active()
            if active_year:
                for i in range(self.year_combo.count()):
                    if self.year_combo.itemData(i) == active_year.id:
                        self.year_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            print(f"خطا در بارگذاری سال‌های تحصیلی: {e}")

    def on_year_changed(self, index):
        if index >= 0:
            year_id = self.year_combo.itemData(index)
            if year_id:
                for year in self.all_academic_years:
                    if year.id == year_id:
                        self.year_label.setText(f"📅 {year.title}")
                        break
                self.academic_year_changed.emit(year_id)

    def update_academic_year_display(self):
        try:
            active_year = self.academic_year_dal.get_active()
            if active_year:
                self.year_label.setText(f"📅 {active_year.title}")
            else:
                self.year_label.setText("⚠️ سال فعالی وجود ندارد")
        except Exception as e:
            self.year_label.setText("⚠️ خطا")
            print(f"خطا در به‌روزرسانی سال تحصیلی: {e}")

    def on_student_double_clicked(self, item):
        row = item.row()
        if row < len(self.students_page.students):
            student = self.students_page.students[row]
            self.open_student_profile(student.id)

    def open_student_profile(self, student_id):
        if not student_id:
            QMessageBox.warning(self, "توجه", "لطفاً یک دانش‌آموز را انتخاب کنید.")
            return
        self.students_page.open_profile_tab(student_id)
        self.stacked_widget.setCurrentIndex(2)

    def logout(self):
        reply = QMessageBox.question(
            self,
            "تأیید خروج",
            "آیا از خروج از سیستم اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                from utils.security import AuditLogger
                audit = AuditLogger(self.db)
                audit.log_logout(self.current_user_id)
                self.logger.info(f"🚪 کاربر {self.current_username} خارج شد.")
            except:
                pass

            self.close()
            import subprocess
            import sys
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)

    def auto_logout(self):
        if self.is_logged_in:
            self.logger.info(f"⏰ خروج خودکار کاربر {self.current_username} به دلیل عدم فعالیت.")
            self.logout()

    def eventFilter(self, obj, event):
        if event.type() in [
            event.Type.MouseButtonPress,
            event.Type.MouseMove,
            event.Type.KeyPress,
            event.Type.Wheel
        ]:
            self.idle_timer.start()
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        if self.is_logged_in:
            try:
                from utils.security import AuditLogger
                audit = AuditLogger(self.db)
                audit.log_logout(self.current_user_id)
                self.logger.info(f"🚪 کاربر {self.current_username} برنامه را بست.")
            except:
                pass
        event.accept()

    def update_notification_badge(self):
        try:
            from services.reminder_service import ReminderService
            service = ReminderService()
            summary = service.get_reminder_summary()

            count = summary.get('total_pending', 0)
            if count > 0:
                self.notification_badge.setText(str(count) if count <= 99 else "99+")
                self.notification_badge.setVisible(True)
            else:
                self.notification_badge.setVisible(False)
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی اعلان‌ها: {e}")

    def toggle_notifications(self):
        if self.notification_widget.isVisible():
            self.notification_widget.hide()
        else:
            pos = self.notification_btn.mapToGlobal(
                self.notification_btn.rect().bottomRight()
            )
            pos.setX(pos.x() - self.notification_widget.width() + 30)
            self.notification_widget.show_at(pos)

    def on_notification_clicked(self, data):
        self.stacked_widget.setCurrentIndex(5)  # پیگیری‌ها

    def open_student_profile_by_profile_id(self, profile_id):
        if not profile_id:
            QMessageBox.warning(self, "توجه", "شناسه پرونده نامعتبر است.")
            return

        try:
            profile = self.profile_dal.get_by_id(profile_id)
            if profile:
                self.open_student_profile(profile.student_id)
            else:
                QMessageBox.warning(self, "توجه", "پرونده یافت نشد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در باز کردن پرونده:\n{str(e)}")