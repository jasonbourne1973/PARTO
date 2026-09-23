"""
ویجت راهنمای سریع - نمایش درون فرم‌ها
"""

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.help_system import HelpSystem
from utils.help_system import HelpWidget as FullHelpDialog


class HelpWidget(QFrame):
    """
    ویجت راهنمای سریع برای نمایش درون فرم‌ها
    
    ویژگی‌ها:
    - نمایش راهنماهای کوتاه
    - قابلیت باز/بسته شدن
    - نمایش راهنمای کامل با کلیک
    """
    
    help_requested = Signal(str)  # برای درخواست راهنمای کامل
    
    def __init__(self, title: str = "راهنما", message: str = "", parent=None):
        super().__init__(parent)
        
        self.title = title
        self.message = message
        self.is_expanded = False
        
        self.setup_ui()
        
        if message:
            self.set_message(message)
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        self.setStyleSheet("""
            QFrame#HelpWidget {
                background-color: #F4D35E;
                border: 1px solid #F4C542;
                border-radius: 6px;
            }
        """)
        self.setObjectName("HelpWidget")
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # ===== هدر =====
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(10)
        header.setLayout(header_layout)
        
        # آیکون و عنوان
        icon_label = QLabel("💡")
        icon_label.setStyleSheet("font-size: 16px;")
        header_layout.addWidget(icon_label)
        
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #C62828;
                font-size: 13px;
            }
        """)
        self.title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_label.setToolTip("برای باز کردن راهنمای کامل کلیک کنید")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # دکمه باز/بسته
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #C62828;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 4px;
            }
        """)
        self.toggle_btn.setToolTip("نمایش/مخفی کردن توضیح کوتاه")
        self.toggle_btn.clicked.connect(self.toggle_expand)
        header_layout.addWidget(self.toggle_btn)

        # خود نوار زرد، آیکون و عنوان نیز کلیک‌پذیر هستند. در نسخه قبلی فقط
        # دکمه کوچک فلش رویداد داشت و متن «راهنما...» عملاً دکوری بود.
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.setToolTip("برای باز کردن راهنمای کامل کلیک کنید")
        self._help_click_targets = (header, icon_label, self.title_label)
        for target in self._help_click_targets:
            target.installEventFilter(self)

        main_layout.addWidget(header)
        
        # ===== محتوا =====
        self.content = QFrame()
        self.content.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 0 10px 10px 10px;
            }
        """)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(10, 0, 10, 10)
        content_layout.setSpacing(8)
        self.content.setLayout(content_layout)
        
        self.message_label = QLabel()
        self.message_label.setStyleSheet("""
            QLabel {
                color: #475569;
                font-size: 12px;
                line-height: 1.6;
            }
        """)
        self.message_label.setWordWrap(True)
        content_layout.addWidget(self.message_label)
        
        # دکمه راهنمای کامل
        self.more_btn = QPushButton("📖 راهنمای کامل")
        self.more_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #0B2E4F;
                border: none;
                font-size: 11px;
                font-weight: bold;
                text-align: left;
                padding: 0;
            }
            QPushButton:hover {
                color: #08223A;
                text-decoration: underline;
            }
        """)
        self.more_btn.clicked.connect(self.show_full_help)
        content_layout.addWidget(self.more_btn)
        
        main_layout.addWidget(self.content)
        
        # مخفی کردن محتوا در ابتدا
        self.content.setVisible(False)
    
    def set_message(self, message: str):
        """تنظیم متن راهنما"""
        self.message = message
        self.message_label.setText(message)
        
        if not message:
            self.hide()
    
    def set_title(self, title: str):
        """تنظیم عنوان"""
        self.title = title
        self.title_label.setText(title)
    
    def toggle_expand(self):
        """باز/بسته کردن ویجت"""
        self.is_expanded = not self.is_expanded
        self.content.setVisible(self.is_expanded)
        self.toggle_btn.setText("▲" if self.is_expanded else "▼")
    
    def expand(self):
        """باز کردن ویجت"""
        if not self.is_expanded:
            self.toggle_expand()
    
    def collapse(self):
        """بستن ویجت"""
        if self.is_expanded:
            self.toggle_expand()
    
    def show_full_help(self):
        """نمایش راهنمای کامل"""
        # هم سیگنال عمومی را حفظ می‌کنیم و هم یک رفتار پیش‌فرض واقعی داریم؛
        # بنابراین فرم‌هایی که به help_requested متصل نشده‌اند نیز راهنما را
        # نمایش می‌دهند.
        self.help_requested.emit(self.title)
        self.open_full_help(self.title, self.window())
    
    def eventFilter(self, watched, event):
        """باز کردن راهنما با کلیک روی نوار زرد، آیکون یا عنوان."""
        targets = getattr(self, "_help_click_targets", ())
        # بازرسی دهم: شرط‌های تودرتو با «and» ادغام شدند
        if (watched in targets
                and event.type() == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton):
            self.show_full_help()
            return True
        return super().eventFilter(watched, event)

    def add_help_button(self, widget: QWidget):
        """افزودن دکمه راهنما به یک ویجت"""
        from PySide6.QtWidgets import QPushButton
        
        btn = QPushButton("❓")
        btn.setFixedSize(24, 24)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #0B2E4F;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(52, 152, 219, 0.1);
                border-radius: 4px;
            }
        """)
        btn.clicked.connect(self.show_full_help)
        return btn
    
    @staticmethod
    def _get_guide(constant_name: str, fallback: str) -> str:
        """خواندن متن راهنما با fallback امن برای نصب‌های قدیمی."""
        try:
            from config import help_messages
            value = getattr(help_messages, constant_name, None)
            if value:
                return str(value)
        except (ImportError, AttributeError):
            # نصب قدیمی بدون ماژول help_messages → متن پیش‌فرض
            pass
        return fallback

    @staticmethod
    def create_for_observation_form(parent=None):
        """ایجاد ویجت راهنما برای فرم مشاهده"""
        guide = HelpWidget._get_guide(
            "OBSERVATION_GUIDE",
            "دانش‌آموز، تاریخ، شایستگی و شرح مشاهده را وارد و ذخیره کنید."
        )
        return HelpWidget("راهنمای ثبت مشاهده", guide[:300] + "...", parent)

    @staticmethod
    def create_for_intervention_form(parent=None):
        """ایجاد ویجت راهنما برای فرم مداخله"""
        guide = HelpWidget._get_guide(
            "INTERVENTION_GUIDE",
            "نوع مداخله، هدف، مسئول و نتیجه را ثبت کنید."
        )
        return HelpWidget("راهنمای ثبت مداخله", guide[:300] + "...", parent)

    @staticmethod
    def create_for_followup_form(parent=None):
        """ایجاد ویجت راهنما برای فرم پیگیری"""
        guide = HelpWidget._get_guide(
            "FOLLOWUP_GUIDE",
            "تاریخ، وضعیت و نتیجه پیگیری را ثبت کنید."
        )
        return HelpWidget("راهنمای ثبت پیگیری", guide[:300] + "...", parent)

    @staticmethod
    def open_full_help(topic: str, parent=None):
        """باز کردن راهنمای کامل برای موضوع انتخاب‌شده."""
        clean_topic = str(topic or "").strip()
        clean_topic = clean_topic.replace("راهنمای ", "", 1).strip()

        topic_map = {
            "ثبت مشاهده": "observation_form",
            "ثبت مداخله": "intervention_form",
            "ثبت پیگیری": "followup_form",
            "ثبت فعالیت": "activity_form",
            "ثبت جلسه مشاوره": "counseling_session_form",
            "ثبت هدف": "goal_form",
            "تغییر رمز عبور": "change_password",
            "خروجی داده": "export_ai",
            "مدل ABC": "abc_model",
            "شایستگی‌ها": "competencies",
            "گزارش‌ها": "reports",
        }
        page_id = topic_map.get(clean_topic)

        # اگر شناسه در نسخه فعلی config متفاوت بود، از عنوان خود صفحه پیدا کن.
        help_system = HelpSystem()
        if page_id and not help_system.get_page(page_id):
            page_id = None
        if page_id is None and clean_topic:
            for page in help_system.get_all_pages():
                page_title = str(page.get("title", "")).replace("راهنمای ", "").strip()
                if clean_topic in page_title or page_title in clean_topic:
                    page_id = page.get("id")
                    break

        try:
            dialog_parent = parent if parent is not None else None
            if page_id:
                dialog = FullHelpDialog(page_id=page_id, parent=dialog_parent)
            else:
                # حتی اگر صفحه اختصاصی در HELP_PAGES تعریف نشده باشد، صفحه
                # خوش‌آمدگویی راهنما نمایش داده می‌شود و کلیک بی‌اثر نیست.
                dialog = FullHelpDialog(parent=dialog_parent)
            dialog.exec()
        except Exception as exc:
            # خطای راهنما نباید بی‌صدا ناپدید شود.
            QMessageBox.warning(
                dialog_parent,
                "راهنما",
                f"امکان نمایش راهنما وجود ندارد:\n{exc}"
            )

