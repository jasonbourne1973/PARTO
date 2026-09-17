"""
ابزار اعتبارسنجی فایل‌ها - بررسی نوع، حجم و محتوای فایل‌های آپلودی
"""

import os
import magic
import hashlib
from typing import Tuple, List, Optional


class FileValidator:
    """
    اعتبارسنجی فایل‌ها برای آپلود
    
    ویژگی‌ها:
    - بررسی نوع فایل (بر اساس محتوا و پسوند)
    - بررسی حجم فایل
    - بررسی یکپارچگی فایل
    - شناسایی فایل‌های مخرب
    """
    
    # انواع فایل‌های مجاز با MIME type
    ALLOWED_MIME_TYPES = {
        # تصاویر
        'image/jpeg': 'image',
        'image/png': 'image',
        'image/gif': 'image',
        'image/bmp': 'image',
        'image/svg+xml': 'image',
        'image/webp': 'image',
        'image/tiff': 'image',
        'image/x-icon': 'image',
        
        # اسناد
        'application/pdf': 'document',
        'application/msword': 'document',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'document',
        'application/vnd.ms-excel': 'document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'document',
        'application/vnd.ms-powerpoint': 'document',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'document',
        'text/plain': 'document',
        'text/rtf': 'document',
        'application/rtf': 'document',
        'application/vnd.oasis.opendocument.text': 'document',
        'application/vnd.oasis.opendocument.spreadsheet': 'document',
        'application/vnd.oasis.opendocument.presentation': 'document',
        
        # صوتی
        'audio/mpeg': 'audio',
        'audio/wav': 'audio',
        'audio/ogg': 'audio',
        'audio/flac': 'audio',
        'audio/mp4': 'audio',
        'audio/aac': 'audio',
        'audio/x-ms-wma': 'audio',
        
        # ویدئویی
        'video/mp4': 'video',
        'video/x-msvideo': 'video',
        'video/x-matroska': 'video',
        'video/quicktime': 'video',
        'video/x-ms-wmv': 'video',
        'video/webm': 'video',
        'video/mp2t': 'video',
        
        # بایگانی
        'application/zip': 'archive',
        'application/x-rar-compressed': 'archive',
        'application/x-7z-compressed': 'archive',
        'application/x-tar': 'archive',
        'application/gzip': 'archive',
        
        # سایر
        'text/csv': 'other',
        'application/json': 'other',
        'application/xml': 'other',
        'text/html': 'other',
        'text/css': 'other',
        'application/javascript': 'other',
        'text/x-log': 'other',
    }
    
    # پسوندهای مجاز
    ALLOWED_EXTENSIONS = {
        'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'tiff', 'ico'],
        'document': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf', 'odt', 'ods', 'odp'],
        'audio': ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma'],
        'video': ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v'],
        'archive': ['zip', 'rar', '7z', 'tar', 'gz'],
        'other': ['csv', 'json', 'xml', 'html', 'css', 'js', 'log'],
    }
    
    # حداکثر حجم بر اساس نوع (بایت)
    MAX_SIZE_BY_TYPE = {
        'image': 10 * 1024 * 1024,      # 10 MB
        'document': 20 * 1024 * 1024,   # 20 MB
        'audio': 30 * 1024 * 1024,      # 30 MB
        'video': 50 * 1024 * 1024,      # 50 MB
        'archive': 25 * 1024 * 1024,    # 25 MB
        'other': 10 * 1024 * 1024,      # 10 MB
    }
    
    # حداکثر حجم کلی
    MAX_TOTAL_SIZE = 20 * 1024 * 1024   # 20 MB
    
    @classmethod
    def validate_file(cls, file_data: bytes, file_name: str, 
                      allowed_types: Optional[List[str]] = None) -> Tuple[bool, str, dict]:
        """
        اعتبارسنجی کامل فایل
        
        Args:
            file_data: محتوای فایل
            file_name: نام فایل
            allowed_types: لیست انواع مجاز (اختیاری)
            
        Returns:
            tuple: (is_valid, message, info_dict)
        """
        errors = []
        info = {
            'size': len(file_data),
            'extension': cls._get_extension(file_name),
            'mime_type': None,
            'file_type': None,
            'category': None,
            'checksum': None,
        }
        
        # 1. بررسی وجود داده
        if not file_data:
            errors.append("محتوای فایل نمی‌تواند خالی باشد")
            return False, "\n".join(errors), info
        
        # 2. بررسی حجم
        if len(file_data) > cls.MAX_TOTAL_SIZE:
            errors.append(f"حجم فایل ({cls._format_size(len(file_data))}) از حد مجاز ({cls._format_size(cls.MAX_TOTAL_SIZE)}) بیشتر است")
        
        # 3. بررسی نام فایل
        if not file_name:
            errors.append("نام فایل نمی‌تواند خالی باشد")
        
        # 4. بررسی پسوند
        ext = info['extension']
        if not ext:
            errors.append("فایل بدون پسوند است")
        else:
            # بررسی وجود پسوند در انواع مجاز
            all_extensions = []
            for exts in cls.ALLOWED_EXTENSIONS.values():
                all_extensions.extend(exts)
            
            if ext.lower() not in all_extensions:
                errors.append(f"پسوند '{ext}' مجاز نیست. پسوندهای مجاز: {', '.join(all_extensions)}")
        
        # 5. بررسی MIME type با python-magic
        try:
            mime = magic.from_buffer(file_data, mime=True)
            info['mime_type'] = mime
            
            if mime in cls.ALLOWED_MIME_TYPES:
                info['category'] = cls.ALLOWED_MIME_TYPES[mime]
                info['file_type'] = mime
            else:
                # اگر MIME type شناخته نشد، از پسوند استفاده کن
                if ext and ext.lower() in all_extensions:
                    # پیدا کردن دسته بر اساس پسوند
                    for category, extensions in cls.ALLOWED_EXTENSIONS.items():
                        if ext.lower() in extensions:
                            info['category'] = category
                            info['file_type'] = mime
                            break
                else:
                    errors.append(f"نوع فایل '{mime}' مجاز نیست")
        except:
            # اگر python-magic نصب نیست، فقط از پسوند استفاده کن
            if ext and ext.lower() in all_extensions:
                for category, extensions in cls.ALLOWED_EXTENSIONS.items():
                    if ext.lower() in extensions:
                        info['category'] = category
                        break
            else:
                errors.append("نوع فایل قابل شناسایی نیست")
        
        # 6. بررسی حجم بر اساس نوع
        if info['category'] and info['category'] in cls.MAX_SIZE_BY_TYPE:
            max_size = cls.MAX_SIZE_BY_TYPE[info['category']]
            if len(file_data) > max_size:
                errors.append(
                    f"حجم فایل ({cls._format_size(len(file_data))}) از حد مجاز برای "
                    f"نوع {info['category']} ({cls._format_size(max_size)}) بیشتر است"
                )
        
        # 7. بررسی محتوای مخرب (ساده)
        if cls._is_suspicious(file_data):
            errors.append("فایل مشکوک به نظر می‌رسد. لطفاً فایل را بررسی کنید.")
        
        # 8. محاسبه checksum
        info['checksum'] = hashlib.md5(file_data).hexdigest()
        
        # 9. فیلتر بر اساس انواع مجاز
        if allowed_types and info['category'] and info['category'] not in allowed_types:
            errors.append(f"نوع فایل '{info['category']}' مجاز نیست. انواع مجاز: {', '.join(allowed_types)}")
        
        if errors:
            return False, "\n".join(errors), info
        
        return True, "فایل معتبر است", info
    
    @classmethod
    def validate_extension(cls, file_name: str) -> Tuple[bool, str, str]:
        """
        اعتبارسنجی پسوند فایل
        
        Args:
            file_name: نام فایل
            
        Returns:
            tuple: (is_valid, category, extension)
        """
        ext = cls._get_extension(file_name)
        if not ext:
            return False, "unknown", ext
        
        ext_lower = ext.lower()
        for category, extensions in cls.ALLOWED_EXTENSIONS.items():
            if ext_lower in extensions:
                return True, category, ext
        
        return False, "unknown", ext
    
    @classmethod
    def validate_size(cls, file_data: bytes, max_size: Optional[int] = None) -> Tuple[bool, str]:
        """
        اعتبارسنجی حجم فایل
        
        Args:
            file_data: محتوای فایل
            max_size: حداکثر حجم مجاز (اختیاری)
            
        Returns:
            tuple: (is_valid, message)
        """
        if max_size is None:
            max_size = cls.MAX_TOTAL_SIZE
        
        size = len(file_data)
        if size > max_size:
            return False, f"حجم فایل ({cls._format_size(size)}) از حد مجاز ({cls._format_size(max_size)}) بیشتر است"
        
        return True, "حجم فایل مناسب است"
    
    @classmethod
    def get_file_info(cls, file_data: bytes, file_name: str) -> dict:
        """
        دریافت اطلاعات کامل فایل
        
        Args:
            file_data: محتوای فایل
            file_name: نام فایل
            
        Returns:
            dict: اطلاعات فایل
        """
        info = {
            'size': len(file_data),
            'size_display': cls._format_size(len(file_data)),
            'extension': cls._get_extension(file_name),
            'name': file_name,
            'mime_type': None,
            'category': None,
            'checksum': hashlib.md5(file_data).hexdigest(),
        }
        
        try:
            mime = magic.from_buffer(file_data, mime=True)
            info['mime_type'] = mime
            if mime in cls.ALLOWED_MIME_TYPES:
                info['category'] = cls.ALLOWED_MIME_TYPES[mime]
        except:
            # اگر magic کار نکرد، از پسوند استفاده کن
            ext = info['extension']
            for category, extensions in cls.ALLOWED_EXTENSIONS.items():
                if ext.lower() in extensions:
                    info['category'] = category
                    break
        
        return info
    
    @classmethod
    def _get_extension(cls, file_name: str) -> str:
        """دریافت پسوند فایل"""
        if '.' in file_name:
            return file_name.rsplit('.', 1)[1].lower()
        return ''
    
    @classmethod
    def _format_size(cls, size: int) -> str:
        """فرمت‌سازی حجم فایل"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @classmethod
    def _is_suspicious(cls, file_data: bytes) -> bool:
        """
        بررسی ساده برای تشخیص فایل‌های مشکوک
        
        بررسی:
        - فایل‌های خیلی بزرگ
        - محتوای غیرعادی
        - الگوهای مشکوک
        """
        # بررسی اندازه خیلی بزرگ
        if len(file_data) > 100 * 1024 * 1024:  # 100 MB
            return True
        
        # بررسی الگوهای مشکوک (ساده)
        suspicious_patterns = [
            b'<script>',
            b'javascript:',
            b'data:',
            b'base64,',
            b'eval(',
        ]
        
        # فقط 10 کیلوبایت اول را بررسی کن
        sample = file_data[:10240]
        for pattern in suspicious_patterns:
            if pattern in sample:
                return True
        
        return False
    
    @classmethod
    def get_allowed_extensions(cls) -> List[str]:
        """دریافت لیست تمام پسوندهای مجاز"""
        all_extensions = []
        for extensions in cls.ALLOWED_EXTENSIONS.values():
            all_extensions.extend(extensions)
        return all_extensions
    
    @classmethod
    def get_extensions_by_category(cls, category: str) -> List[str]:
        """دریافت پسوندهای یک دسته خاص"""
        return cls.ALLOWED_EXTENSIONS.get(category, [])
    
    @classmethod
    def get_category_display(cls, category: str) -> str:
        """دریافت نمایش فارسی دسته‌بندی"""
        display_map = {
            'image': 'تصویر',
            'document': 'سند',
            'audio': 'صوتی',
            'video': 'ویدئویی',
            'archive': 'بایگانی',
            'other': 'سایر',
        }
        return display_map.get(category, category)