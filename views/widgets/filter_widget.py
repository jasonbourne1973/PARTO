"""
ویجت فیلتر - نمایش و مدیریت فیلترهای ذخیره‌شده
"""

import os
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.saved_filter import SavedFilter
from services.advanced_search_service import AdvancedSearchService
from utils.logger import get_logger


class FilterItemWidget(QFrame):
    """آیتم فیلتر در لیست"""
    
    filter_selected = Signal(dict)
    filter_deleted = Signal(int)
    
    def __init__(self, saved_filter, user_id=None, parent=None):
        super().__init__(parent)
        self.saved_filter = saved_filter
        self.user_id = user_id
        self.setup_ui()
    
    def setup_ui(self):
        """راه‌اندازی آیتم فیلتر"""
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)
        self.setLayout(layout)
        
        # اطلاعات
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # نام
        name_label = QLabel(self.saved_filter.name)
        name_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #F4C542;")
        info_layout.addWidget(name_label)
        
        # توضیحات
        if self.saved_filter.description:
            desc_label = QLabel(self.saved_filter.description)
            desc_label.setStyleSheet("font-size: 11px; color: #D9C36A;")
            desc_label.setWordWrap(True)
            info_layout.addWidget(desc_label)
        
        # متادیتا
        meta_label = QLabel(
            f"{self.saved_filter.type_display} | "
            f"{self.saved_filter.visibility_display} | "
            f"استفاده: {self.saved_filter.use_count} بار"
        )
        meta_label.setStyleSheet("font-size: 10px; color: #D9C36A;")
        info_layout.addWidget(meta_label)
        
        layout.addWidget(info_widget, 2)
        
        # دکمه‌ها
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)
        
        # دکمه اعمال
        apply_btn = QPushButton("✅ اعمال")
        apply_btn.setFixedSize(60, 28)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #08223A;
            }
        """)
        apply_btn.clicked.connect(self.on_apply)
        btn_layout.addWidget(apply_btn)
        
        # دکمه حذف (فقط برای فیلترهای شخصی)
        if self.saved_filter.user_id == self.user_id:
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(28, 28)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #EF4444;
                    color: #F4C542;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #DC2626;
                }
            """)
            delete_btn.clicked.connect(self.on_delete)
            btn_layout.addWidget(delete_btn)
        
        layout.addWidget(btn_widget)
        
        # استایل
        self.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 6px;
            }
            QFrame:hover {
                background-color: #0B2E4F;
                border-color: #D9C36A;
            }
        """)
    
    def on_apply(self):
        """اعمال فیلتر"""
        self.filter_selected.emit(self.saved_filter.filter_params)
    
    def on_delete(self):
        """حذف فیلتر"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف فیلتر '{self.saved_filter.name}' اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.filter_deleted.emit(self.saved_filter.id)


class FilterWidget(QWidget):
    """
    ویجت فیلتر - نمایش و مدیریت فیلترهای ذخیره‌شده
    
    ویژگی‌ها:
    - نمایش لیست فیلترهای کاربر
    - نمایش فیلترهای اشتراکی
    - نمایش فیلترهای پرکاربرد
    - ذخیره فیلتر جدید
    - اعمال و حذف فیلتر
    """
    
    filter_applied = Signal(dict)
    
    def __init__(self, user_id=None, filter_type=None, parent=None):
        super().__init__(parent)
        
        self.user_id = user_id
        self.filter_type = filter_type
        self.search_service = AdvancedSearchService()
        self.logger = get_logger(self.__class__.__name__)
        
        self.filters = []
        
        self.setup_ui()
        
        if self.user_id:
            self.load_filters()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        self.setLayout(main_layout)
        
        # ===== هدر =====
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📋 فیلترهای ذخیره‌شده")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #F4C542;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # دکمه ذخیره فیلتر جدید
        self.save_btn = QPushButton("➕ ذخیره فیلتر")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #22C55E;
                color: #F4C542;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16A34A;
            }
        """)
        self.save_btn.clicked.connect(self.show_save_filter_dialog)
        header_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(header_layout)
        
        # ===== انتخاب نوع فیلتر =====
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("نوع:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("همه", None)
        for value, display in SavedFilter.TYPE_CHOICES:
            self.type_combo.addItem(display, value)
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        filter_layout.addWidget(self.type_combo)
        
        filter_layout.addStretch()
        
        # دکمه به‌روزرسانی
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #08223A;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #D9C36A;
            }
        """)
        refresh_btn.clicked.connect(self.load_filters)
        filter_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(filter_layout)
        
        # ===== لیست فیلترها =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
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
        container.setStyleSheet("background-color: transparent;")
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(6)
        
        # پیام خالی
        self.empty_label = QLabel("هیچ فیلتری ذخیره نشده است.\nبرای ذخیره فیلتر فعلی، روی دکمه '+ ذخیره فیلتر' کلیک کنید.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #D9C36A;
                font-size: 13px;
                padding: 30px 20px;
                background-color: #0B2E4F;
                border-radius: 8px;
                border: 1px dashed #D9C36A;
            }
        """)
        self.container_layout.addWidget(self.empty_label)
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        # ===== تب‌های فیلتر =====
        tab_layout = QHBoxLayout()
        tab_layout.setSpacing(6)
        
        self.personal_btn = QPushButton("👤 شخصی")
        self.personal_btn.setStyleSheet(self._get_tab_style(True))
        self.personal_btn.clicked.connect(lambda: self.load_filters('personal'))
        tab_layout.addWidget(self.personal_btn)
        
        self.shared_btn = QPushButton("🌐 اشتراکی")
        self.shared_btn.setStyleSheet(self._get_tab_style(False))
        self.shared_btn.clicked.connect(lambda: self.load_filters('shared'))
        tab_layout.addWidget(self.shared_btn)
        
        self.popular_btn = QPushButton("⭐ محبوب")
        self.popular_btn.setStyleSheet(self._get_tab_style(False))
        self.popular_btn.clicked.connect(lambda: self.load_filters('popular'))
        tab_layout.addWidget(self.popular_btn)
        
        tab_layout.addStretch()
        main_layout.addLayout(tab_layout)
        
        self.current_tab = 'personal'
    
    def _get_tab_style(self, active):
        """دریافت استایل تب"""
        if active:
            return """
                QPushButton {
                    background-color: #0B2E4F;
                    color: #F4C542;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #08223A;
                    color: #475569;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #D9C36A;
                }
            """
    
    def set_user_id(self, user_id):
        """تنظیم شناسه کاربر"""
        self.user_id = user_id
        self.load_filters()
    
    def set_filter_type(self, filter_type):
        """تنظیم نوع فیلتر"""
        self.filter_type = filter_type
        if self.type_combo:
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == filter_type:
                    self.type_combo.setCurrentIndex(i)
                    break
        self.load_filters()
    
    def load_filters(self, tab=None):
        """بارگذاری فیلترها"""
        if not self.user_id:
            self.empty_label.show()
            self._clear_filters()
            return
        
        if tab:
            self.current_tab = tab
            # به‌روزرسانی استایل تب‌ها
            self.personal_btn.setStyleSheet(self._get_tab_style(tab == 'personal'))
            self.shared_btn.setStyleSheet(self._get_tab_style(tab == 'shared'))
            self.popular_btn.setStyleSheet(self._get_tab_style(tab == 'popular'))
        
        try:
            filter_type = self.type_combo.currentData()
            
            if self.current_tab == 'personal':
                self.filters = self.search_service.get_user_filters(self.user_id, filter_type)
            elif self.current_tab == 'shared':
                self.filters = self.search_service.get_shared_filters(filter_type)
            else:  # popular
                self.filters = self.search_service.get_popular_filters(filter_type)
            
            self.display_filters()
            
        except Exception as e:
            self.logger.error(f"خطا در بارگذاری فیلترها: {e}")
            QMessageBox.warning(self, "خطا", f"مشکل در بارگذاری فیلترها:\n{e!s}")
    
    def display_filters(self):
        """نمایش فیلترها"""
        self._clear_filters()
        
        if not self.filters:
            self.empty_label.show()
            return
        
        self.empty_label.hide()
        
        for saved_filter in self.filters:
            item = FilterItemWidget(saved_filter, self.user_id)
            item.filter_selected.connect(self.on_filter_selected)
            item.filter_deleted.connect(self.on_filter_deleted)
            self.container_layout.addWidget(item)
    
    def _clear_filters(self):
        """پاک کردن لیست فیلترها"""
        for i in reversed(range(self.container_layout.count())):
            widget = self.container_layout.itemAt(i).widget()
            if widget and widget != self.empty_label:
                widget.deleteLater()
    
    def on_filter_selected(self, filter_params):
        """وقتی فیلتر انتخاب می‌شود"""
        self.filter_applied.emit(filter_params)
    
    def on_filter_deleted(self, filter_id):
        """وقتی فیلتر حذف می‌شود"""
        try:
            self.search_service.delete_filter(filter_id, self.user_id)
            self.load_filters()
            QMessageBox.information(self, "موفقیت", "فیلتر با موفقیت حذف شد")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در حذف فیلتر:\n{e!s}")
    
    def on_type_changed(self):
        """وقتی نوع فیلتر تغییر می‌کند"""
        self.load_filters()
    
    def show_save_filter_dialog(self):
        """نمایش دیالوگ ذخیره فیلتر"""
        dialog = QDialog(self)
        dialog.setWindowTitle("ذخیره فیلتر جدید")
        dialog.setModal(True)
        dialog.resize(400, 350)
        
        layout = QVBoxLayout(dialog)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # نام
        name_input = QLineEdit()
        name_input.setPlaceholderText("نام فیلتر...")
        form_layout.addRow("نام:", name_input)
        
        # توضیحات
        desc_input = QTextEdit()
        desc_input.setPlaceholderText("توضیحات (اختیاری)...")
        desc_input.setMaximumHeight(60)
        form_layout.addRow("توضیحات:", desc_input)
        
        # سطح دسترسی
        visibility_combo = QComboBox()
        for value, display in SavedFilter.VISIBILITY_CHOICES:
            visibility_combo.addItem(display, value)
        form_layout.addRow("سطح دسترسی:", visibility_combo)
        
        layout.addLayout(form_layout)
        
        # دکمه‌ها
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "خطا", "لطفاً نام فیلتر را وارد کنید")
                return
            
            # دریافت پارامترهای فیلتر فعلی
            filter_params = self._get_current_filter_params()
            if not filter_params:
                QMessageBox.warning(self, "خطا", "هیچ پارامتر فیلتری برای ذخیره وجود ندارد")
                return
            
            try:
                self.search_service.save_filter(
                    name=name,
                    filter_type=self.filter_type or SavedFilter.TYPE_STUDENT,
                    filter_params=filter_params,
                    user_id=self.user_id,
                    description=desc_input.toPlainText().strip(),
                    visibility=visibility_combo.currentData()
                )
                self.load_filters()
                QMessageBox.information(self, "موفقیت", "فیلتر با موفقیت ذخیره شد")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"مشکل در ذخیره فیلتر:\n{e!s}")
    
    def _get_current_filter_params(self):
        """دریافت پارامترهای فیلتر فعلی"""
        # این متد باید توسط کلاس والد یا صفحه فراخوانی کننده بازنویسی شود
        # در اینجا یک نمونه ساده برگردانده می‌شود
        return {
            'name': '',
            'national_code': '',
            'grade': None,
            'class_name': '',
            'search_text': ''
        }