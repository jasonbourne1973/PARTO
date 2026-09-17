"""
ابزار پیش‌نمایش فایل‌ها - نمایش تصاویر، PDF، متن و سایر فایل‌ها
"""

import os
import sys
from typing import Optional, Tuple
from PySide6.QtWidgets import QLabel, QTextEdit, QWidget
from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QPixmap, QImage, QColor


class FilePreview:
    """
    ابزار پیش‌نمایش فایل‌ها
    
    ویژگی‌ها:
    - پیش‌نمایش تصاویر (jpg, png, gif, ...)
    - پیش‌نمایش متن (txt, csv, json, ...)
    - پیش‌نمایش PDF (با آیکون)
    - نمایش اطلاعات فایل
    """
    
    @staticmethod
    def can_preview(file_name: str) -> bool:
        """
        بررسی قابلیت پیش‌نمایش فایل
        
        Args:
            file_name: نام فایل
            
        Returns:
            bool: آیا می‌توان پیش‌نمایش داد؟
        """
        ext = FilePreview._get_extension(file_name).lower()
        
        # تصاویر
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'tiff', 'ico']
        
        # متون
        text_extensions = ['txt', 'csv', 'json', 'xml', 'log', 'py', 'js', 'html', 'css', 'md']
        
        # PDF
        pdf_extensions = ['pdf']
        
        all_preview = image_extensions + text_extensions + pdf_extensions
        return ext in all_preview
    
    @staticmethod
    def get_preview_type(file_name: str) -> str:
        """
        دریافت نوع پیش‌نمایش
        
        Args:
            file_name: نام فایل
            
        Returns:
            str: نوع پیش‌نمایش ('image', 'text', 'pdf', 'unknown')
        """
        ext = FilePreview._get_extension(file_name).lower()
        
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'tiff', 'ico']
        text_extensions = ['txt', 'csv', 'json', 'xml', 'log', 'py', 'js', 'html', 'css', 'md']
        pdf_extensions = ['pdf']
        
        if ext in image_extensions:
            return 'image'
        elif ext in text_extensions:
            return 'text'
        elif ext in pdf_extensions:
            return 'pdf'
        else:
            return 'unknown'
    
    @staticmethod
    def preview_image(file_path: str, max_width: int = 350, max_height: int = 250) -> Optional[QPixmap]:
        """
        ایجاد پیش‌نمایش تصویر
        
        Args:
            file_path: مسیر فایل
            max_width: حداکثر عرض
            max_height: حداکثر ارتفاع
            
        Returns:
            QPixmap: تصویر مقیاس‌شده یا None در صورت خطا
        """
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                if pixmap.width() > max_width or pixmap.height() > max_height:
                    pixmap = pixmap.scaled(
                        max_width, max_height,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                return pixmap
        except:
            pass
        return None
    
    @staticmethod
    def preview_text(file_path: str, max_chars: int = 800) -> Optional[str]:
        """
        ایجاد پیش‌نمایش متن
        
        Args:
            file_path: مسیر فایل
            max_chars: حداکثر تعداد کاراکتر
            
        Returns:
            str: متن پیش‌نمایش یا None در صورت خطا
        """
        try:
            encodings = ['utf-8', 'cp1256', 'iso-8859-1', 'ascii']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read(max_chars)
                        if len(content) >= max_chars:
                            content += "\n\n... (ادامه فایل)"
                        return content
                except UnicodeDecodeError:
                    continue
            
            return "⚠️ فایل قابل خواندن نیست (فرمت نامشخص)"
            
        except Exception:
            return None
    
    @staticmethod
    def preview_pdf(file_path: str) -> str:
        """
        ایجاد پیش‌نمایش PDF (آیکون و اطلاعات)
        
        Args:
            file_path: مسیر فایل
            
        Returns:
            str: متن پیش‌نمایش
        """
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                num_pages = len(reader.pages)
                
                # خواندن چند خط اول
                preview_text = f"📄 فایل PDF\n\nتعداد صفحات: {num_pages}\n"
                
                if num_pages > 0:
                    try:
                        first_page = reader.pages[0]
                        text = first_page.extract_text()[:300]
                        if text:
                            preview_text += f"\nمتن صفحه اول:\n{text}..."
                    except:
                        pass
                
                return preview_text
        except:
            return "📄 فایل PDF\n\n(برای مشاهده کامل، فایل را باز کنید)"
    
    @staticmethod
    def create_preview_widget(file_path: str, file_name: str, parent=None) -> QWidget:
        """
        ایجاد ویجت پیش‌نمایش
        
        Args:
            file_path: مسیر فایل
            file_name: نام فایل
            parent: والد ویجت
            
        Returns:
            QWidget: ویجت پیش‌نمایش
        """
        preview_type = FilePreview.get_preview_type(file_name)
        
        if preview_type == 'image':
            # ویجت تصویر
            label = QLabel(parent)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = FilePreview.preview_image(file_path)
            if pixmap:
                label.setPixmap(pixmap)
            else:
                label.setText("🖼️\n(پیش‌نمایش تصویر در دسترس نیست)")
                label.setStyleSheet("font-size: 14px; color: #7f8c8d; padding: 20px;")
            return label
            
        elif preview_type == 'text':
            # ویجت متن
            text_edit = QTextEdit(parent)
            text_edit.setReadOnly(True)
            text_edit.setStyleSheet("""
                QTextEdit {
                    border: none;
                    padding: 10px;
                    font-family: monospace;
                    font-size: 12px;
                    background-color: #f8f9fa;
                    color: #2c3e50;
                }
            """)
            content = FilePreview.preview_text(file_path)
            if content:
                text_edit.setText(content)
            else:
                text_edit.setText("⚠️ متن قابل خواندن نیست")
            return text_edit
            
        elif preview_type == 'pdf':
            # ویجت PDF
            label = QLabel(parent)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text = FilePreview.preview_pdf(file_path)
            label.setText(text)
            label.setStyleSheet("""
                QLabel {
                    padding: 20px;
                    font-size: 14px;
                    color: #2c3e50;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                }
            """)
            return label
            
        else:
            # ویجت عمومی
            label = QLabel(parent)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon = FilePreview._get_file_icon(file_name)
            size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            label.setText(f"{icon}\n{file_name}\n\n({FilePreview._format_size(size)})\nپیش‌نمایش در دسترس نیست")
            label.setStyleSheet("""
                QLabel {
                    padding: 20px;
                    font-size: 14px;
                    color: #7f8c8d;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                }
            """)
            return label
    
    @staticmethod
    def get_file_icon(file_name: str) -> str:
        """دریافت آیکون مناسب برای فایل"""
        ext = FilePreview._get_extension(file_name).lower()
        
        icon_map = {
            'pdf': '📄',
            'doc': '📝',
            'docx': '📝',
            'xls': '📊',
            'xlsx': '📊',
            'ppt': '📽️',
            'pptx': '📽️',
            'txt': '📃',
            'jpg': '🖼️',
            'jpeg': '🖼️',
            'png': '🖼️',
            'gif': '🖼️',
            'bmp': '🖼️',
            'svg': '🖼️',
            'mp3': '🎵',
            'wav': '🎵',
            'ogg': '🎵',
            'mp4': '🎬',
            'avi': '🎬',
            'mkv': '🎬',
            'mov': '🎬',
            'zip': '📦',
            'rar': '📦',
            '7z': '📦',
            'tar': '📦',
            'gz': '📦',
        }
        
        return icon_map.get(ext, '📎')
    
    @staticmethod
    def _get_extension(file_name: str) -> str:
        """دریافت پسوند فایل"""
        if '.' in file_name:
            return file_name.rsplit('.', 1)[1].lower()
        return ''
    
    @staticmethod
    def _format_size(size: int) -> str:
        """فرمت‌سازی حجم فایل"""
        if size == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @staticmethod
    def get_file_info_text(attachment) -> str:
        """
        دریافت متن اطلاعات فایل برای نمایش
        
        Args:
            attachment: شیء Attachment
            
        Returns:
            str: متن اطلاعات
        """
        info = f"""
📄 **نام فایل:** {attachment.file_name}
📊 **نوع:** {getattr(attachment, 'display_type', attachment.file_type or 'نامشخص')}
📦 **حجم:** {getattr(attachment, 'display_size', FilePreview._format_size(attachment.file_size))}
📅 **تاریخ آپلود:** {attachment.created_at}
👤 **آپلودکننده:** {getattr(attachment, 'created_by_name', 'نامشخص')}
        """
        
        if attachment.title:
            info += f"\n📝 **عنوان:** {attachment.title}"
        if attachment.description:
            info += f"\n📋 **توضیحات:** {attachment.description}"
        if attachment.tags:
            info += f"\n🏷️ **برچسب‌ها:** {attachment.tags}"
        
        return info