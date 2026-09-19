"""
صفحه مدیریت پشتیبان‌گیری و بازیابی
"""

import os

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.settings import ATTACHMENTS_DIR, DB_PATH
from utils.backup import BackupManager
from utils.persian_date import format_timestamp


class BackupWorker(QThread):
    """کارگر برای عملیات طولانی Backup"""
    
    progress = Signal(int)
    finished = Signal(bool, str)
    
    def __init__(self, backup_manager, action, backup_file=None):
        super().__init__()
        self.backup_manager = backup_manager
        self.action = action
        self.backup_file = backup_file
    
    def run(self):
        if self.action == "create":
            result = self.backup_manager.create_backup()
            self.finished.emit(result['success'], result['message'])
        elif self.action == "restore":
            result = self.backup_manager.restore_backup(self.backup_file)
            self.finished.emit(result['success'], result['message'])
        elif self.action == "delete":
            success, message = self.backup_manager.delete_backup(self.backup_file)
            self.finished.emit(success, message)


class BackupPage(QWidget):
    """صفحه مدیریت پشتیبان‌گیری"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # مسیرهای پیش‌فرض
        self.backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
        self.backup_manager = BackupManager(DB_PATH, ATTACHMENTS_DIR, self.backup_dir)
        self.worker = None
        
        self.setup_ui()
        self.load_backups()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ===== عنوان =====
        title_label = QLabel("💾 پشتیبان‌گیری و بازیابی")
        title_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #F4C542; }")
        layout.addWidget(title_label)
        
        # ===== نوار ابزار =====
        toolbar = QHBoxLayout()
        
        self.create_btn = QPushButton("➕ ایجاد پشتیبان جدید")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #66BB6A;
                color: #F4C542;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #8BC34A; }
        """)
        self.create_btn.clicked.connect(self.create_backup)
        toolbar.addWidget(self.create_btn)
        
        self.restore_btn = QPushButton("📂 بازیابی از فایل")
        self.restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #F4D35E;
                color: #F4C542;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #F28C28; }
        """)
        self.restore_btn.clicked.connect(self.restore_from_file)
        toolbar.addWidget(self.restore_btn)
        
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedWidth(40)
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
        self.refresh_btn.clicked.connect(self.load_backups)
        toolbar.addWidget(self.refresh_btn)
        
        layout.addLayout(toolbar)
        
        # ===== نوار پیشرفت =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #D9C36A;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #8BC34A;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # ===== جدول Backupها =====
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["نام فایل", "تاریخ ایجاد", "حجم", "وضعیت", "عملیات"])
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
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
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
    
    def load_backups(self):
        """بارگذاری لیست Backupها"""
        try:
            backups = self.backup_manager.list_backups()
            self.table.setRowCount(len(backups))
            
            for row, backup in enumerate(backups):
                self.table.setItem(row, 0, QTableWidgetItem(backup['name']))
                # created_at از metadata خودِ فایل پشتیبان می‌آید:
                # «datetime.now().isoformat()» یعنی میلادیِ محلی با جداکنندهٔ «T»
                # (و اگر metadata نداشته باشد، mtime فایل). در برنامه‌ای که
                # همه‌چیزش شمسی است، نمایش «2026-09-18T19:47:37.123456» هم
                # تقویمش غلط است هم برای کاربر بی‌معنی.
                self.table.setItem(
                    row, 1,
                    QTableWidgetItem(format_timestamp(backup.get('created_at')))
                )
                self.table.setItem(row, 2, QTableWidgetItem(backup['size_display']))
                
                # وضعیت
                status_item = QTableWidgetItem("✅ سالم")
                status_item.setBackground(QColor(200, 255, 200))
                self.table.setItem(row, 3, status_item)
                
                # دکمه‌ها
                btn_widget = QWidget()
                btn_layout = QHBoxLayout()
                btn_layout.setContentsMargins(2, 2, 2, 2)
                
                restore_btn = QPushButton("🔄 بازیابی")
                restore_btn.setFixedSize(70, 25)
                restore_btn.setStyleSheet("background-color: #F4D35E; color: #F4C542; border: none; border-radius: 3px;")
                restore_btn.clicked.connect(lambda checked, b=backup: self.restore_backup(b))
                btn_layout.addWidget(restore_btn)
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 25)
                delete_btn.setStyleSheet("background-color: #C62828; color: #F4C542; border: none; border-radius: 3px;")
                delete_btn.clicked.connect(lambda checked, b=backup: self.delete_backup(b))
                btn_layout.addWidget(delete_btn)
                
                btn_widget.setLayout(btn_layout)
                self.table.setCellWidget(row, 4, btn_widget)
                self.table.setRowHeight(row, 35)
                
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"مشکل در بارگذاری Backupها:\n{e!s}")
    
    def create_backup(self):
        """ایجاد پشتیبان جدید"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.set_buttons_enabled(False)
        
        self.worker = BackupWorker(self.backup_manager, "create")
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.backup_finished)
        self.worker.start()
    
    def restore_backup(self, backup):
        """بازیابی از یک Backup موجود"""
        reply = QMessageBox.question(
            self,
            "تأیید بازیابی",
            f"آیا از بازیابی فایل '{backup['name']}' اطمینان دارید؟\n\n⚠️ اطلاعات فعلی با اطلاعات فایل Backup جایگزین می‌شود.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.set_buttons_enabled(False)
            
            self.worker = BackupWorker(self.backup_manager, "restore", backup['path'])
            self.worker.progress.connect(self.update_progress)
            self.worker.finished.connect(self.backup_finished)
            self.worker.start()
    
    def restore_from_file(self):
        """بازیابی از فایل خارجی"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب فایل پشتیبان",
            "",
            "PARTO Backup (*.partobak)"
        )
        
        if file_path:
            reply = QMessageBox.question(
                self,
                "تأیید بازیابی",
                f"آیا از بازیابی فایل '{os.path.basename(file_path)}' اطمینان دارید؟\n\n⚠️ اطلاعات فعلی با اطلاعات فایل Backup جایگزین می‌شود.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                self.set_buttons_enabled(False)
                
                self.worker = BackupWorker(self.backup_manager, "restore", file_path)
                self.worker.progress.connect(self.update_progress)
                self.worker.finished.connect(self.backup_finished)
                self.worker.start()
    
    def delete_backup(self, backup):
        """حذف فایل پشتیبان"""
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف فایل '{backup['name']}' اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.worker = BackupWorker(self.backup_manager, "delete", backup['path'])
            self.worker.finished.connect(self.backup_finished)
            self.worker.start()
    
    def update_progress(self, value):
        """به‌روزرسانی نوار پیشرفت"""
        self.progress_bar.setValue(value)
    
    def backup_finished(self, success, message):
        """پایان عملیات Backup"""
        self.progress_bar.setVisible(False)
        self.set_buttons_enabled(True)
        
        if success:
            QMessageBox.information(self, "موفقیت", message)
            self.load_backups()
        else:
            QMessageBox.critical(self, "خطا", message)
    
    def set_buttons_enabled(self, enabled):
        """فعال/غیرفعال کردن دکمه‌ها"""
        self.create_btn.setEnabled(enabled)
        self.restore_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)