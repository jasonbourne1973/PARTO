"""
سیستم راهنمای داخلی برنامه - نسخه کامل
مدیریت صفحات راهنما و نمایش آنها
"""

from typing import ClassVar, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

try:
    from config.help_messages import HELP_PAGES
except ImportError:
    # حداقل صفحات داخلی؛ اگر فایل تنظیمات پروژه وجود داشته باشد، از همان
    # داده‌های کامل استفاده می‌شود.
    HELP_PAGES = {
        "general": {
            "id": "general",
            "title": "راهنمای عمومی برنامه",
            "category": "general",
            "category_order": 0,
            "content": "از منوی برنامه برای دسترسی به بخش‌های مختلف استفاده کنید.",
            "keywords": "عمومی برنامه منو",
            "tags": ["general"],
        },
        "observation_form": {
            "id": "observation_form",
            "title": "راهنمای ثبت مشاهده",
            "category": "observations",
            "category_order": 1,
            "content": "دانش‌آموز، تاریخ، شایستگی و شرح مشاهده را وارد و ذخیره کنید.",
            "keywords": "مشاهده ثبت رفتار",
            "tags": ["observations"],
        },
        "intervention_form": {
            "id": "intervention_form",
            "title": "راهنمای ثبت مداخله",
            "category": "interventions",
            "category_order": 2,
            "content": "نوع مداخله، هدف، مسئول و نتیجه را ثبت کنید.",
            "keywords": "مداخله اقدام",
            "tags": ["interventions"],
        },
        "followup_form": {
            "id": "followup_form",
            "title": "راهنمای ثبت پیگیری",
            "category": "followups",
            "category_order": 3,
            "content": "تاریخ، وضعیت و نتیجه پیگیری را ثبت کنید.",
            "keywords": "پیگیری نتیجه",
            "tags": ["followups"],
        },
    }


class HelpSystem:
    """
    سیستم مدیریت راهنماهای برنامه
    
    ویژگی‌ها:
    - مدیریت صفحات راهنما
    - جستجو در راهنماها
    - نمایش راهنمای گام‌به‌گام
    - مدیریت تاریخچه مشاهده
    """
    
    _instance = None
    _help_pages: ClassVar[dict[str, str]] = {}
    _view_history: ClassVar[list[str]] = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._help_pages:
            self._help_pages = HELP_PAGES.copy()
    
    def get_page(self, page_id: str) -> Optional[dict]:
        """دریافت یک صفحه راهنما با شناسه"""
        return self._help_pages.get(page_id)
    
    def get_all_pages(self) -> list[dict]:
        """دریافت لیست تمام صفحات راهنما"""
        return list(self._help_pages.values())
    
    def get_pages_by_category(self, category: str) -> list[dict]:
        """دریافت صفحات راهنما بر اساس دسته‌بندی"""
        return [p for p in self._help_pages.values() if p.get('category') == category]
    
    def search(self, query: str) -> list[dict]:
        """جستجو در صفحات راهنما"""
        query = query.lower()
        results = []
        
        for page in self._help_pages.values():
            keywords = page.get('keywords', '')
            if isinstance(keywords, (list, tuple, set)):
                keywords = ' '.join(str(item) for item in keywords)
            if (query in str(page.get('title', '')).lower() or
                query in str(page.get('content', '')).lower() or
                query in str(keywords).lower()):
                results.append(page)
        
        return results
    
    def get_related_pages(self, page_id: str, limit: int = 3) -> list[dict]:
        """دریافت صفحات مرتبط با یک صفحه"""
        page = self.get_page(page_id)
        if not page:
            return []
        
        tags = page.get('tags', [])
        related = []
        
        for p in self._help_pages.values():
            if p.get('id') == page_id:
                continue
            p_tags = p.get('tags', [])
            if any(tag in p_tags for tag in tags):
                related.append(p)
        
        return related[:limit]
    
    def add_to_history(self, page_id: str):
        """افزودن صفحه به تاریخچه مشاهده"""
        if page_id in self._view_history:
            self._view_history.remove(page_id)
        self._view_history.insert(0, page_id)
        
        if len(self._view_history) > 20:
            self._view_history.pop()
    
    def get_history(self, limit: int = 10) -> list[dict]:
        """دریافت تاریخچه مشاهده صفحات"""
        pages = []
        for page_id in self._view_history[:limit]:
            page = self.get_page(page_id)
            if page:
                pages.append(page)
        return pages
    
    def clear_history(self):
        """پاک کردن تاریخچه مشاهده"""
        self._view_history.clear()


class HelpWidget(QDialog):
    """
    ویجت نمایش راهنما - به صورت دیالوگ
    """
    
    def __init__(self, page_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        
        self.help_system = HelpSystem()
        self.current_page_id = page_id
        
        self.setWindowTitle("راهنمای برنامه")
        self.setModal(True)
        self.resize(800, 600)
        self.setMinimumSize(600, 400)
        
        self.setup_ui()
        
        if page_id:
            self.show_page(page_id)
        else:
            self.show_welcome()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # ===== هدر =====
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #1a252f;
                padding: 15px 20px;
            }
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 10, 15, 10)
        header.setLayout(header_layout)
        
        title_label = QLabel("📖 راهنمای برنامه")
        title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # دکمه بستن
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)
        close_btn.clicked.connect(self.accept)
        header_layout.addWidget(close_btn)
        
        main_layout.addWidget(header)
        
        # ===== بخش اصلی =====
        body = QWidget()
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body.setLayout(body_layout)
        
        # ===== سمت چپ: لیست صفحات =====
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-right: 1px solid #dee2e6;
            }
        """)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(5)
        sidebar.setLayout(sidebar_layout)
        
        # جستجو
        search_label = QLabel("🔍 جستجو:")
        search_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        sidebar_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("عبارت جستجو...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        sidebar_layout.addWidget(self.search_input)
        
        sidebar_layout.addSpacing(10)
        
        # لیست صفحات
        self.page_list = QListWidget()
        self.page_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                outline: 0;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-radius: 4px;
                color: #2c3e50;
            }
            QListWidget::item:hover {
                background-color: #e8f0fe;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        self.page_list.itemClicked.connect(self.on_page_selected)
        sidebar_layout.addWidget(self.page_list)
        
        body_layout.addWidget(sidebar)
        
        # ===== سمت راست: محتوای راهنما =====
        content_frame = QFrame()
        content_frame.setStyleSheet("background-color: white;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_frame.setLayout(content_layout)
        
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f1f2f6;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background-color: #bdc3c7;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #95a5a6;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: white;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(15)
        
        self.content_scroll.setWidget(self.content_widget)
        content_layout.addWidget(self.content_scroll)
        
        # دکمه‌های پایین
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.prev_btn = QPushButton("◀ قبلی")
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1;
                color: #2c3e50;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
            }
            QPushButton:disabled {
                color: #bdc3c7;
            }
        """)
        self.prev_btn.clicked.connect(self.go_previous)
        button_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("بعدی ▶")
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.next_btn.clicked.connect(self.go_next)
        button_layout.addWidget(self.next_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("بستن")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        content_layout.addLayout(button_layout)
        
        body_layout.addWidget(content_frame)
        
        main_layout.addWidget(body)
        
        # بارگذاری صفحات
        self.load_pages()
    
    def load_pages(self):
        """بارگذاری صفحات راهنما در لیست"""
        self.page_list.clear()
        
        pages = self.help_system.get_all_pages()
        
        # مرتب‌سازی بر اساس دسته‌بندی و عنوان
        pages.sort(key=lambda p: (p.get('category_order', 0), p.get('title', '')))
        
        for page in pages:
            item = QListWidgetItem()
            item.setText(page.get('title', 'بدون عنوان'))
            item.setData(Qt.ItemDataRole.UserRole, page.get('id'))
            
            # آیکون دسته‌بندی
            category = page.get('category', 'general')
            icon_map = {
                'general': '📋',
                'observations': '📝',
                'interventions': '🛠️',
                'followups': '🔔',
                'reports': '📄',
                'settings': '⚙️',
                'students': '👤',
                'competencies': '📊',
            }
            icon = icon_map.get(category, '📋')
            item.setText(f"{icon} {page.get('title', '')}")
            
            self.page_list.addItem(item)
    
    def show_page(self, page_id: str):
        """نمایش یک صفحه راهنما با شناسه"""
        page = self.help_system.get_page(page_id)
        if not page:
            self.show_error(f"صفحه '{page_id}' یافت نشد.")
            return
        
        # افزودن به تاریخچه
        self.help_system.add_to_history(page_id)
        self.current_page_id = page_id
        
        # انتخاب در لیست
        for i in range(self.page_list.count()):
            item = self.page_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == page_id:
                self.page_list.setCurrentItem(item)
                break
        
        # به‌روزرسانی محتوا
        self.display_page(page)
        
        # به‌روزرسانی دکمه‌های ناوبری
        self.update_navigation_buttons()
    
    def display_page(self, page: dict):
        """نمایش محتوای یک صفحه"""
        # پاک کردن محتوای قبلی
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # عنوان
        title_label = QLabel(page.get('title', 'بدون عنوان'))
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
        title_label.setWordWrap(True)
        self.content_layout.addWidget(title_label)
        
        # دسته‌بندی
        category = page.get('category', 'general')
        category_names = {
            'general': 'عمومی',
            'observations': 'مشاهدات',
            'interventions': 'مداخلات',
            'followups': 'پیگیری‌ها',
            'reports': 'گزارش‌ها',
            'settings': 'تنظیمات',
            'students': 'دانش‌آموزان',
            'competencies': 'شایستگی‌ها',
        }
        cat_label = QLabel(f"📂 {category_names.get(category, 'عمومی')}")
        cat_label.setStyleSheet("font-size: 12px; color: #64748B;")
        self.content_layout.addWidget(cat_label)
        
        self.content_layout.addSpacing(10)
        
        # محتوا
        content = page.get('content', '')
        if content:
            content_label = QLabel(content)
            content_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    line-height: 1.8;
                    color: #1E293B;
                }
            """)
            content_label.setWordWrap(True)
            self.content_layout.addWidget(content_label)
        
        # گام‌ها (اگر وجود داشته باشد)
        steps = page.get('steps', [])
        if steps:
            steps_label = QLabel("📌 **مراحل انجام کار:**")
            steps_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F172A;")
            self.content_layout.addWidget(steps_label)
            
            for i, step in enumerate(steps, 1):
                step_label = QLabel(f"{i}. {step}")
                step_label.setStyleSheet("""
                    QLabel {
                        font-size: 13px;
                        line-height: 1.8;
                        color: #1E293B;
                        padding: 4px 0;
                    }
                """)
                step_label.setWordWrap(True)
                self.content_layout.addWidget(step_label)
        
        # برچسب‌ها
        tags = page.get('tags', [])
        if tags:
            tags_text = "🏷️ " + ", ".join(tags)
            tags_label = QLabel(tags_text)
            tags_label.setStyleSheet("font-size: 11px; color: #64748B;")
            self.content_layout.addWidget(tags_label)
        
        # افزودن فضای خالی در انتها
        self.content_layout.addStretch()
    
    def show_welcome(self):
        """نمایش صفحه خوش‌آمدگویی"""
        # پاک کردن محتوای قبلی
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        welcome_label = QLabel("""
📖 **به راهنمای برنامه خوش آمدید**

از لیست سمت چپ، موضوع مورد نظر خود را انتخاب کنید.
برای جستجو در راهنماها، از فیلد جستجو استفاده کنید.

💡 **نکته:** می‌توانید با کلیک روی دکمه‌های قبلی و بعدی،
بین صفحات راهنما حرکت کنید.
""")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                line-height: 2;
                color: #1E293B;
                padding: 40px 20px;
                background-color: #F8FAFC;
                border-radius: 8px;
            }
        """)
        welcome_label.setWordWrap(True)
        self.content_layout.addWidget(welcome_label)
        
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
    
    def show_error(self, message: str):
        """نمایش پیام خطا"""
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        error_label = QLabel(f"❌ {message}")
        error_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-size: 14px;
                padding: 20px;
                text-align: center;
            }
        """)
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(error_label)
    
    def on_page_selected(self, item: QListWidgetItem):
        """وقتی صفحه‌ای از لیست انتخاب می‌شود"""
        page_id = item.data(Qt.ItemDataRole.UserRole)
        if page_id:
            self.show_page(page_id)
    
    def on_search_changed(self, text: str):
        """وقتی جستجو تغییر می‌کند"""
        text = text.strip()
        
        self.page_list.clear()
        
        if text:
            results = self.help_system.search(text)
            for page in results:
                item = QListWidgetItem()
                item.setText(page.get('title', 'بدون عنوان'))
                item.setData(Qt.ItemDataRole.UserRole, page.get('id'))
                self.page_list.addItem(item)
        else:
            self.load_pages()
    
    def go_previous(self):
        """رفتن به صفحه قبلی در تاریخچه"""
        history = self.help_system.get_history()
        if len(history) > 1:
            # صفحه قبلی در تاریخچه
            current_index = None
            for i, page in enumerate(history):
                if page.get('id') == self.current_page_id:
                    current_index = i
                    break
            
            if current_index is not None and current_index < len(history) - 1:
                prev_page = history[current_index + 1]
                self.show_page(prev_page.get('id'))
    
    def go_next(self):
        """رفتن به صفحه بعدی در تاریخچه"""
        history = self.help_system.get_history()
        if len(history) > 1:
            # صفحه بعدی در تاریخچه
            current_index = None
            for i, page in enumerate(history):
                if page.get('id') == self.current_page_id:
                    current_index = i
                    break
            
            if current_index is not None and current_index > 0:
                next_page = history[current_index - 1]
                self.show_page(next_page.get('id'))
    
    def update_navigation_buttons(self):
        """به‌روزرسانی دکمه‌های ناوبری"""
        history = self.help_system.get_history()
        
        # پیدا کردن موقعیت صفحه فعلی در تاریخچه
        current_index = None
        for i, page in enumerate(history):
            if page.get('id') == self.current_page_id:
                current_index = i
                break
        
        if current_index is None:
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
        else:
            self.prev_btn.setEnabled(current_index < len(history) - 1)
            self.next_btn.setEnabled(current_index > 0)
    
    def keyPressEvent(self, event):
        """مدیریت کلیدهای کیبورد"""
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
        elif event.key() == Qt.Key.Key_F1:
            # اگر F1 زده شد، برنامه را بستن
            pass
        super().keyPressEvent(event)