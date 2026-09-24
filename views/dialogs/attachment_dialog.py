"""
دیالوگ مدیریت پیوست‌ها - نسخه کامل با پیش‌نمایش بهتر
"""

import os
import sys

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import DatabaseConnection
from services.attachment_service import AttachmentService
from utils.error_handler import ServiceError
from utils.logger import get_logger
from views.widgets.deleted_records import (
    ask_restore_confirmation,
    deleted_label,
    make_show_deleted_checkbox,
    report_restore_failure,
)


class AttachmentUploadWorker(QThread):
    """
    کارگر برای آپلود فایل در پس‌زمینه

    ===== اصلاح (بازرسی چهاردهم) — هویت کاربر در نخ کارگر =====
    کاربر جاری دیتابیس «نخ‌محلی» است (تا نخ زمان‌بند به نام کاربر
    واردشده ثبت نشود). این کارگر در نخ جداگانه می‌نویسد؛ اگر هویت را
    صریح تحویل نگیرد، ردیف Audit آپلود با user_id=NULL یعنی «سیستم»
    ثبت می‌شد، در حالی که کاربر واقعی آن را انجام داده است. حالا
    هویت در نخ UI (سازنده) گرفته و در نخ کارگر با worker_context
    اعمال می‌شود؛ اتصال نخ کارگر هم در پایان آزاد می‌شود.
    """
    
    # (بازرسی شانزدهم) نام سیگنال از `finished` (که سیگنال داخلی QThread است)
    # به `upload_finished` تغییر کرد تا دو سیگنال هم‌نام با امضای متفاوت روی
    # یک شیء نباشد.
    progress = Signal(int)
    upload_finished = Signal(bool, str, object)  # success, message, attachment
    
    def __init__(self, service, entity_type, entity_id, file_path, 
                 title=None, description=None, created_by=None):
        super().__init__()
        self.service = service
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.file_path = file_path
        self.title = title
        self.description = description
        # سازنده در نخ UI اجرا می‌شود؛ همین‌جا هویت کاربر واقعی گرفته
        # می‌شود تا در نخ کارگر (که کاربر نخ‌محلی ندارد) استفاده شود.
        self.user_context = DatabaseConnection().get_current_user()
        self.created_by = (created_by if created_by is not None
                           else self.user_context)
    
    def run(self):
        try:
            self.progress.emit(20)
            
            # خواندن فایل
            with open(self.file_path, 'rb') as f:
                file_data = f.read()
            
            self.progress.emit(60)
            
            # آپلود (به نام همان کاربری که در نخ UI وارد شده است)
            file_name = os.path.basename(self.file_path)
            with DatabaseConnection().worker_context(self.user_context):
                attachment = self.service.upload_attachment(
                    entity_type=self.entity_type,
                    entity_id=self.entity_id,
                    file_data=file_data,
                    file_name=file_name,
                    title=self.title,
                    description=self.description,
                    created_by=self.created_by
                )
            
            self.progress.emit(100)
            self.upload_finished.emit(True, "فایل با موفقیت آپلود شد", attachment)
            
        except Exception as e:
            self.upload_finished.emit(False, str(e), None)


class AttachmentDialog(QDialog):
    """دیالوگ مدیریت پیوست‌ها با پیش‌نمایش بهتر"""
    
    attachment_added = Signal()
    attachment_deleted = Signal()
    # نکتهٔ دور هجدهم: سیگنال جداگانهٔ «بازیابی» تعریف نشد چون مثل دو
    # سیگنال بالا گیرنده‌ای در معماری فعلی وجود ندارد (والد فقط exec()
    # می‌کند) و ممیزی Signal/Slot دور ۱۶ آن را «سیگنال بلااستفاده»
    # می‌گرفت. بازخورد بازیابی داخل خود دیالوگ داده می‌شود (برگشت به
    # فهرست فعال + پیام موفقیت).

    def __init__(self, entity_type, entity_id, parent=None):
        super().__init__(parent)

        self.entity_type = entity_type
        self.entity_id = entity_id
        self.attachment_service = AttachmentService()
        self.logger = get_logger(self.__class__.__name__)
        self.upload_worker = None
        self.attachments = []
        self.current_attachment_id = None
        self.search_results = []
        # مسیر بازیابی پیوست حذف‌شده (دور هجدهم — BUG-ATT-04/05)
        self.showing_deleted = False
        self.deleted_attachments = []
        self._deleted_by_id = {}
        # (بازرسی شانزدهم) صف آپلود: فایل‌های انتخاب‌شده یکی‌یکی آپلود می‌شوند
        self._upload_queue = []
        self._upload_results = []
        
        # تنظیم عنوان بر اساس نوع موجودیت
        entity_names = {
            'observation': 'مشاهده',
            'intervention': 'مداخله',
            'followup': 'پیگیری',
            'student': 'دانش‌آموز',
            'profile': 'پرونده',
            'report': 'گزارش'
        }
        entity_name = entity_names.get(entity_type, 'موجودیت')
        
        self.setWindowTitle(f"📎 مدیریت پیوست‌ها - {entity_name}")
        self.setModal(True)
        self.resize(800, 600)
        
        self.setup_ui()
        self.load_attachments()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری با پیش‌نمایش بهتر"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ افزودن فایل")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.add_btn.clicked.connect(self.add_attachment)
        toolbar.addWidget(self.add_btn)
        
        toolbar.addSpacing(10)
        
        # جستجو
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 جستجوی فایل...")
        self.search_input.setStyleSheet("""
            QLineEdit {
    color: #F4C542;
    background-color: #08223A;
                padding: 4px 10px;
                border: 1px solid #8BC34A;
                border-radius: 4px;
                font-size: 12px;
                min-width: 150px;
            }
            QLineEdit:focus {
    color: #FFE8A3;
    background-color: #0B2E4F;
                border: 2px solid #F4C542;
            }
        """)
        self.search_input.textChanged.connect(self.search_attachments)
        toolbar.addWidget(self.search_input)
        
        self.clear_search_btn = QPushButton("✖")
        self.clear_search_btn.setFixedSize(30, 30)
        self.clear_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #9E1B1B; }
        """)
        self.clear_search_btn.clicked.connect(self.clear_search)
        toolbar.addWidget(self.clear_search_btn)
        
        toolbar.addStretch()
        
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedSize(36, 36)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover { background-color: #08223A; }
        """)
        self.refresh_btn.clicked.connect(self.load_attachments)
        toolbar.addWidget(self.refresh_btn)

        # «نمایش حذف‌شده‌ها» + بازیابی (دور هجدهم — BUG-ATT-04)
        toolbar.addSpacing(10)
        self.show_deleted_check = make_show_deleted_checkbox(
            self, "toggle_show_deleted",
            tooltip="پیوست‌های حذف‌شده را نشان می‌دهد تا بتوان آن‌ها را "
                    "بازیابی کرد.")
        toolbar.addWidget(self.show_deleted_check)

        # اطلاعات تعداد و حجم
        self.info_label = QLabel("تعداد: 0 | حجم کل: 0 B")
        self.info_label.setStyleSheet("color: #D9C36A; font-size: 13px;")
        toolbar.addWidget(self.info_label)
        
        main_layout.addLayout(toolbar)
        
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
        main_layout.addWidget(self.progress_bar)
        
        # ===== بخش اصلی (Splitter) =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ===== سمت چپ: لیست فایل‌ها =====
        left_frame = QFrame()
        left_frame.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 5px;
            }
        """)
        left_layout = QVBoxLayout()
        left_frame.setLayout(left_layout)
        
        list_title = QLabel("📋 لیست فایل‌ها")
        list_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F4C542; padding: 5px;")
        left_layout.addWidget(list_title)
        
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
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
        self.file_list.itemClicked.connect(self.on_file_selected)
        self.file_list.itemDoubleClicked.connect(self.on_file_double_clicked)
        left_layout.addWidget(self.file_list)
        
        splitter.addWidget(left_frame)
        
        # ===== سمت راست: پیش‌نمایش و اطلاعات =====
        right_frame = QFrame()
        right_frame.setStyleSheet("""
            QFrame {
                background-color: #0B2E4F;
                border: 1px solid #D9C36A;
                border-radius: 5px;
            }
        """)
        right_layout = QVBoxLayout()
        right_frame.setLayout(right_layout)
        
        # ===== پیش‌نمایش =====
        preview_group = QGroupBox("👁️ پیش‌نمایش")
        preview_group.setStyleSheet("""
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
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)
        
        # اسکرول برای پیش‌نمایش
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setFrameShape(QFrame.Shape.NoFrame)
        preview_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #D9C36A;
                border-radius: 4px;
                background-color: #0B2E4F;
            }
        """)
        
        self.preview_label = QLabel("یک فایل را انتخاب کنید")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                padding: 20px;
                min-height: 180px;
                color: #D9C36A;
                font-size: 14px;
            }
        """)
        preview_scroll.setWidget(self.preview_label)
        preview_layout.addWidget(preview_scroll)
        
        right_layout.addWidget(preview_group)
        
        # ===== اطلاعات فایل =====
        info_group = QGroupBox("📋 اطلاعات فایل")
        info_group.setStyleSheet("""
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
        info_layout = QVBoxLayout()
        info_group.setLayout(info_layout)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        self.info_text.setStyleSheet("""
            QTextEdit {
    color: #F4C542;
                border: 1px solid #8BC34A;
                padding: 5px;
                background-color: #08223A;
                font-size: 12px;
                line-height: 1.6;
            }
        """)
        info_layout.addWidget(self.info_text)
        
        right_layout.addWidget(info_group)
        
        # ===== دکمه‌های عملیات =====
        btn_layout = QHBoxLayout()
        
        self.open_btn = QPushButton("📂 باز کردن فایل")
        self.open_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B2E4F;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #08223A; }
        """)
        self.open_btn.clicked.connect(self.open_file)
        btn_layout.addWidget(self.open_btn)
        
        self.download_btn = QPushButton("⬇️ دانلود")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7d3c98; }
        """)
        self.download_btn.clicked.connect(self.download_file)
        btn_layout.addWidget(self.download_btn)
        
        self.delete_btn = QPushButton("🗑️ حذف")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: #F4C542;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #D94B4B; }
        """)
        self.delete_btn.clicked.connect(self.delete_selected)
        btn_layout.addWidget(self.delete_btn)

        self.restore_btn = QPushButton("↩️ بازیابی")
        self.restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.restore_btn.setToolTip(
            "بازیابی پیوست حذف‌شده؛ فایل فیزیکی پیش از بازیابی "
            "راستی‌آزمایی می‌شود.")
        self.restore_btn.clicked.connect(self.restore_selected)
        self.restore_btn.setVisible(False)  # فقط در حالت «نمایش حذف‌شده‌ها»
        btn_layout.addWidget(self.restore_btn)

        btn_layout.addStretch()
        
        self.close_btn = QPushButton("❌ بستن")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #D9C36A;
                color: #111111;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #D9C36A; }
        """)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(right_frame)
        splitter.setSizes([400, 400])
        
        main_layout.addWidget(splitter)
        
        # غیرفعال کردن دکمه‌ها در ابتدا
        self.open_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
    
    def toggle_show_deleted(self, showing):
        """تعویض بین فهرست فعال‌ها و حذف‌شده‌ها (دور هجدهم — BUG-ATT-04)"""
        self.showing_deleted = bool(showing)
        self.restore_btn.setVisible(self.showing_deleted)
        self.add_btn.setEnabled(not self.showing_deleted)
        self.load_attachments()

    def load_attachments(self):
        """بارگذاری لیست پیوست‌ها (فعال یا حذف‌شده — بسته به چک‌باکس)"""
        try:
            if self.showing_deleted:
                self._load_deleted_attachments()
                return

            summary = self.attachment_service.get_attachments_summary(
                self.entity_type, self.entity_id
            )

            self.attachments = summary['attachments']
            self.search_results = self.attachments
            self.file_list.clear()

            for att in self.attachments:
                icon = getattr(att, 'icon', '📎')
                display_name = att.file_name
                display_size = getattr(att, 'display_size', '')

                item_text = f"{icon} {display_name} ({display_size})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, att.id)
                self.file_list.addItem(item)

            # به‌روزرسانی اطلاعات
            self.info_label.setText(
                f"تعداد: {summary['total_count']} | "
                f"حجم کل: {summary['total_size_display']}"
            )

            # پاک کردن پیش‌نمایش
            self.preview_label.setText("یک فایل را انتخاب کنید")
            self.info_text.clear()
            self.open_btn.setEnabled(False)
            self.download_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.restore_btn.setEnabled(False)
            self.current_attachment_id = None

            self.logger.info(f"{summary['total_count']} پیوست برای {self.entity_type}/{self.entity_id} بارگذاری شد")

        except Exception as e:
            self.logger.error(f"خطا در بارگذاری پیوست‌ها: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری:\n{e!s}")

    def _load_deleted_attachments(self):
        """فهرست پیوست‌های حذف‌شده با امکان بازیابی (BUG-ATT-04)"""
        self.deleted_attachments = (
            self.attachment_service.get_deleted_attachments_by_entity(
                self.entity_type, self.entity_id))
        self._deleted_by_id = {att.id: att for att in self.deleted_attachments}
        self.attachments = []
        self.search_results = self.deleted_attachments
        self.file_list.clear()

        for att in self.deleted_attachments:
            icon = getattr(att, 'icon', '📎')
            display_size = getattr(att, 'display_size', '')
            item_text = f"{icon} {deleted_label(att.file_name)} ({display_size})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, att.id)
            self.file_list.addItem(item)

        self.info_label.setText(
            f"حذف‌شده‌ها: {len(self.deleted_attachments)} — برای بازیابی "
            "انتخاب و «↩️ بازیابی» را بزنید")

        self.preview_label.setText("یک فایل را انتخاب کنید")
        self.info_text.clear()
        self.open_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.restore_btn.setEnabled(False)
        self.current_attachment_id = None
    
    def search_attachments(self):
        """جستجوی پیوست‌ها"""
        search_text = self.search_input.text().strip()
        if self.showing_deleted:
            # جست‌وجو در حالت «حذف‌شده‌ها» روی همان فهرست حذف‌شده‌ها
            if not search_text:
                results = self.deleted_attachments
            else:
                needle = search_text.lower()
                results = [
                    att for att in self.deleted_attachments
                    if needle in (att.file_name or "").lower()
                    or needle in (att.title or "").lower()
                ]
            self.search_results = results
            self.file_list.clear()
            for att in results:
                icon = getattr(att, 'icon', '📎')
                display_size = getattr(att, 'display_size', '')
                item = QListWidgetItem(
                    f"{icon} {deleted_label(att.file_name)} ({display_size})")
                item.setData(Qt.ItemDataRole.UserRole, att.id)
                self.file_list.addItem(item)
            return
        if not search_text:
            self.search_results = self.attachments
        else:
            self.search_results = self.attachment_service.search_attachments(
                self.entity_type, self.entity_id, search_text
            )
        
        self.file_list.clear()
        for att in self.search_results:
            icon = getattr(att, 'icon', '📎')
            display_name = att.file_name
            display_size = getattr(att, 'display_size', '')
            item_text = f"{icon} {display_name} ({display_size})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, att.id)
            self.file_list.addItem(item)
    
    def clear_search(self):
        """پاک کردن جستجو"""
        self.search_input.clear()
        self.load_attachments()
    
    def add_attachment(self):
        """افزودن فایل جدید"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "انتخاب فایل‌های پیوست",
            "",
            "همه فایل‌ها (*.*)"
        )
        
        if not file_paths:
            return
        
        self.upload_files(list(file_paths))

    def is_uploading(self):
        return self.upload_worker is not None and self.upload_worker.isRunning()

    def upload_files(self, file_paths):
        """
        آپلود چند فایل به‌صورت ترتیبی (بازرسی شانزدهم)

        نسخهٔ قبلی برای هر فایل بلافاصله یک کارگر جدید می‌ساخت و در
        `self.upload_worker` جایگزین می‌کرد؛ یعنی QThread قبلی در حال اجرا از
        دست می‌رفت («QThread: Destroyed while thread is still running») و
        چند آپلود هم‌زمان روی یک موجودیت انجام می‌شد.
        """
        if self.is_uploading():
            QMessageBox.information(self, "لطفاً صبر کنید",
                                    "آپلود قبلی هنوز تمام نشده است؛ پس از پایان آن دوباره تلاش کنید.")
            return
        self._upload_queue = list(file_paths)
        self._upload_results = []
        self._start_next_upload()

    def upload_file(self, file_path):
        """آپلود یک فایل (سازگاری با فراخوان‌های قبلی)"""
        self.upload_files([file_path])

    def _start_next_upload(self):
        """برداشتن فایل بعدی از صف و آغاز کارگر؛ اگر صف خالی شد، جمع‌بندی"""
        while self._upload_queue:
            file_path = self._upload_queue.pop(0)
            try:
                file_size = os.path.getsize(file_path)
            except OSError as e:
                self._upload_results.append((False, f"{os.path.basename(file_path)}: {e}"))
                continue
            if file_size > self.attachment_service.MAX_FILE_SIZE:
                self._upload_results.append((
                    False,
                    f"حجم فایل '{os.path.basename(file_path)}' از حد مجاز "
                    f"({self.attachment_service.MAX_FILE_SIZE // (1024*1024)} مگابایت) بیشتر است."))
                continue

            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.set_buttons_enabled(False)

            # created_by = کاربر واقعیِ واردشده (staff.id)؛ قبلاً None فرستاده
            # می‌شد و «آپلودکننده» همیشه نامشخص می‌ماند.
            self.upload_worker = AttachmentUploadWorker(
                service=self.attachment_service,
                entity_type=self.entity_type,
                entity_id=self.entity_id,
                file_path=file_path,
                created_by=DatabaseConnection().get_current_user()
            )
            self.upload_worker.progress.connect(self.update_progress)
            self.upload_worker.upload_finished.connect(self.upload_finished)
            self.upload_worker.start()
            return
        self._finish_upload_batch()

    def _finish_upload_batch(self):
        """پایان صف: تازه‌سازی فهرست و یک پیام جمع‌بندی"""
        self.progress_bar.setVisible(False)
        self.set_buttons_enabled(True)
        results = self._upload_results
        self._upload_results = []
        if not results:
            return
        ok = [m for s_ok, m in results if s_ok]
        failed = [m for s_ok, m in results if not s_ok]
        if ok:
            self.load_attachments()
            self.attachment_added.emit()
        if failed and not ok:
            QMessageBox.critical(self, "خطا", "مشکل در آپلود:\n" + "\n".join(failed))
        elif failed:
            QMessageBox.warning(
                self, "آپلود ناتمام",
                f"{len(ok)} فایل آپلود شد؛ {len(failed)} فایل ناموفق:\n" + "\n".join(failed))
        elif len(ok) == 1:
            QMessageBox.information(self, "موفقیت", ok[0])
        else:
            QMessageBox.information(self, "موفقیت", f"{len(ok)} فایل با موفقیت آپلود شد.")
    
    def update_progress(self, value):
        """به‌روزرسانی نوار پیشرفت"""
        self.progress_bar.setValue(value)
    
    def upload_finished(self, success, message, attachment):
        """پایان آپلود یک فایل از صف"""
        if success:
            name = getattr(attachment, 'file_name', None) or ''
            self._upload_results.append((True, f"{message}" + (f" ({name})" if name else "")))
        else:
            self._upload_results.append((False, message))
        self._start_next_upload()

    def closeEvent(self, event):
        """بستن دیالوگ وسط آپلود: منتظر پایان کارگر می‌ماند تا نخ زیر پایش نمیرد"""
        if self.is_uploading():
            self.upload_worker.wait(15000)
            if self.upload_worker.isRunning():
                QMessageBox.warning(self, "آپلود در جریان",
                                    "آپلود هنوز تمام نشده است؛ لطفاً چند لحظه صبر کنید.")
                event.ignore()
                return
        super().closeEvent(event)

    def reject(self):
        """انصراف/Escape وسط آپلود هم مثل بستن رفتار می‌کند"""
        if self.is_uploading():
            self.upload_worker.wait(15000)
            if self.upload_worker.isRunning():
                QMessageBox.warning(self, "آپلود در جریان",
                                    "آپلود هنوز تمام نشده است؛ لطفاً چند لحظه صبر کنید.")
                return
        super().reject()
    
    def on_file_selected(self, item):
        """وقتی فایل انتخاب می‌شود"""
        attachment_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_attachment_id = attachment_id
        if self.showing_deleted:
            # رکورد حذف‌شده: فقط «بازیابی» معنا دارد؛ اطلاعات از شیءِ
            # حذف‌شده خوانده می‌شود (get_attachment رکورد حذف‌شده را
            # برنمی‌گرداند و پیش‌نمایش هم برای حذف‌شده ساخته نمی‌شود).
            self.open_btn.setEnabled(False)
            self.download_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.restore_btn.setEnabled(True)
            att = self._deleted_by_id.get(attachment_id)
            if att is not None:
                self.info_text.setText(
                    f"📄 **نام فایل:** {deleted_label(att.file_name)}\n"
                    f"📦 **حجم:** {getattr(att, 'display_size', self._format_size(att.file_size))}\n"
                    f"📂 **مسیر:** {att.file_path}\n\n"
                    "برای بازگرداندن، «↩️ بازیابی» را بزنید.")
                self.preview_label.setText("پیش‌نمایش برای پیوست حذف‌شده ندارد")
            return
        self.open_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.restore_btn.setEnabled(False)

        self.show_attachment_info(attachment_id)

    def restore_selected(self):
        """بازیابی پیوست حذف‌شدهٔ انتخاب‌شده (دور هجدهم — BUG-ATT-04/05)"""
        if not self.showing_deleted or not self.current_attachment_id:
            return

        att = self._deleted_by_id.get(self.current_attachment_id)
        if att is None:
            return

        if not ask_restore_confirmation(
                self, f"بازیابی فایل «{att.file_name}»؟"):
            return

        try:
            restored = self.attachment_service.restore_attachment(
                self.current_attachment_id)
            # نتیجهٔ واقعی: تنها وقتی «موفقیت» است که رکورد از DB به‌صورت
            # فعال خوانده شود (سرویس خودش هم اثبات می‌کند؛ اینجا دوباره
            # قرارداد برگشت واقعی سنجیده می‌شود)
            if restored is None or getattr(restored, 'is_deleted', 0):
                QMessageBox.warning(self, "خطا", "پیوست بازیابی نشد.")
                return
            # برگشت به فهرست فعال تا کاربر فایل بازیابی‌شده را همان‌جا
            # ببیند (چک‌باکس برداشته می‌شود → load_attachments فعال)
            if self.showing_deleted:
                self.show_deleted_check.setChecked(False)
            else:
                self.load_attachments()
            QMessageBox.information(
                self, "موفقیت",
                f"فایل «{restored.file_name}» با موفقیت بازیابی شد.")
        except Exception as e:
            # شکست (مثلاً فایل فیزیکی گم‌شده یا عبور از سقف ۲۰) صریح
            # به کاربر گزارش می‌شود؛ موفقیت خاموش ممنوع (BUG-ATT-05)
            report_restore_failure(self, e)
    
    def show_attachment_info(self, attachment_id):
        """نمایش اطلاعات و پیش‌نمایش فایل"""
        try:
            attachment = self.attachment_service.get_attachment(attachment_id)
            if not attachment:
                return
            
            info_text = f"""
📄 **نام فایل:** {attachment.file_name}
📊 **نوع:** {getattr(attachment, 'display_type', attachment.file_type or 'نامشخص')}
📦 **حجم:** {getattr(attachment, 'display_size', self._format_size(attachment.file_size))}
📅 **تاریخ آپلود:** {attachment.created_at}
👤 **آپلودکننده:** {getattr(attachment, 'created_by_name', 'نامشخص')}
📂 **نوع فایل:** {attachment.mime_type or 'نامشخص'}
            """
            if attachment.title:
                info_text += f"\n📝 **عنوان:** {attachment.title}"
            if attachment.description:
                info_text += f"\n📋 **توضیحات:** {attachment.description}"
            
            self.info_text.setText(info_text)
            self.show_preview(attachment)
            
        except Exception as e:
            self.logger.error(f"خطا در نمایش اطلاعات: {e}")
            self.preview_label.setText("خطا در نمایش فایل")
    
    def show_preview(self, attachment):
        """نمایش پیش‌نمایش فایل با کیفیت بهتر"""
        file_name = attachment.file_name.lower()
        
        # تصویر
        if file_name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp')):
            try:
                pixmap = QPixmap(attachment.file_path)
                if not pixmap.isNull():
                    max_width = 350
                    max_height = 250
                    if pixmap.width() > max_width or pixmap.height() > max_height:
                        pixmap = pixmap.scaled(
                            max_width, max_height,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                    self.preview_label.setPixmap(pixmap)
                    self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    return
            except Exception as _exc:
                self.logger.debug(
                    f"خطای غیرمنتظره در {self.__class__.__name__}: {_exc}"
                )
        
        # PDF
        elif file_name.endswith('.pdf'):
            self.preview_label.setText("📄 فایل PDF\n\n(برای مشاهده، روی دکمه 'باز کردن' کلیک کنید)")
            self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return
        
        # متن
        elif file_name.endswith(('.txt', '.csv', '.json', '.xml', '.log', '.py', '.js', '.html', '.css')):
            try:
                with open(attachment.file_path, encoding='utf-8') as f:
                    content = f.read(800)
                    if len(content) >= 800:
                        content += "\n\n... (ادامه فایل)"
                    self.preview_label.setText(content)
                    self.preview_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    self.preview_label.setStyleSheet("""
                        QLabel {
                            padding: 10px;
                            font-family: monospace;
                            font-size: 12px;
                            color: #F4C542;
                            background-color: #08223A;
                            border: 1px solid #D9C36A;
                            border-radius: 4px;
                        }
                    """)
                    return
            except Exception as _exc:
                self.logger.debug(
                    f"خطای غیرمنتظره در {self.__class__.__name__}: {_exc}"
                )
        
        # ویدئو و صدا
        elif file_name.endswith(('.mp4', '.avi', '.mkv', '.mov', '.mp3', '.wav', '.ogg')):
            icon = getattr(attachment, 'icon', '🎬')
            self.preview_label.setText(f"{icon}\n{attachment.file_name}\n\n(برای پخش، روی دکمه 'باز کردن' کلیک کنید)")
            self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return
        
        # پیش‌نمایش عمومی
        icon = getattr(attachment, 'icon', '📎')
        self.preview_label.setText(f"{icon}\n{attachment.file_name}\n\n(پیش‌نمایش در دسترس نیست)")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                padding: 20px;
                min-height: 180px;
                color: #D9C36A;
                font-size: 14px;
            }
        """)
    
    def on_file_double_clicked(self, item):
        """باز کردن فایل با دابل کلیک"""
        self.open_file()
    
    def open_file(self):
        """باز کردن فایل با برنامه پیش‌فرض"""
        if not self.current_attachment_id:
            return
        
        try:
            file_path = self.attachment_service.get_attachment_path(self.current_attachment_id)

            # (بازرسی شانزدهم) نسخهٔ قبلی مسیر فایل را داخل رشتهٔ فرمان shell
            # می‌گذاشت (xdg-open / open با رشته‌سازی)؛ نام فایلی با نویسهٔ «"» یا
            # «;» می‌توانست فرمان دلخواه اجرا کند. حالا بدون shell و با Qt.
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(file_path)):
                raise ServiceError("برنامه‌ای برای بازکردن این نوع فایل پیدا نشد.")
                
        except Exception as e:
            self.logger.error(f"خطا در باز کردن فایل: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در باز کردن فایل:\n{e!s}")
    
    def download_file(self):
        """دانلود فایل"""
        if not self.current_attachment_id:
            return
        
        try:
            attachment = self.attachment_service.get_attachment(self.current_attachment_id)
            if not attachment:
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "ذخیره فایل",
                attachment.file_name,
                f"{attachment.display_type} Files (*.{attachment.file_extension or '*'})"
            )
            
            if file_path:
                content = self.attachment_service.get_attachment_content(self.current_attachment_id)
                with open(file_path, 'wb') as f:
                    f.write(content)
                QMessageBox.information(self, "موفقیت", "فایل با موفقیت ذخیره شد")
                
        except Exception as e:
            self.logger.error(f"خطا در دانلود فایل: {e}")
            QMessageBox.critical(self, "خطا", f"مشکل در دانلود:\n{e!s}")
    
    def delete_selected(self):
        """حذف فایل انتخاب شده"""
        if not self.current_attachment_id:
            return
        
        attachment = self.attachment_service.get_attachment(self.current_attachment_id)
        if not attachment:
            return
        
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف فایل '{attachment.file_name}' اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted = self.attachment_service.delete_attachment(
                    self.current_attachment_id
                )
                self.load_attachments()
                if deleted:
                    self.attachment_deleted.emit()
                    QMessageBox.information(
                        self, "موفقیت", "فایل با موفقیت حذف شد"
                    )
                else:
                    QMessageBox.warning(self, "خطا", "فایل حذف نشد.")
            except Exception as e:
                self.logger.error(f"خطا در حذف فایل: {e}")
                QMessageBox.critical(self, "خطا", f"مشکل در حذف:\n{e!s}")
    
    def set_buttons_enabled(self, enabled):
        """فعال/غیرفعال کردن دکمه‌ها"""
        self.add_btn.setEnabled(enabled and not self.showing_deleted)
        self.refresh_btn.setEnabled(enabled)
        self.open_btn.setEnabled(enabled and self.current_attachment_id is not None)
        self.download_btn.setEnabled(enabled and self.current_attachment_id is not None)
        self.delete_btn.setEnabled(enabled and self.current_attachment_id is not None)
        if self.showing_deleted:
            self.restore_btn.setEnabled(
                enabled and self.current_attachment_id is not None)
    
    def _format_size(self, size):
        """فرمت‌سازی حجم فایل"""
        if not size:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"