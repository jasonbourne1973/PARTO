"""
ابزار اعتبارسنجی فایل‌ها - بررسی نوع، حجم و محتوای فایل‌های آپلودی
"""

import hashlib
from typing import List, Optional, Tuple

# ===== اصلاح (بازرسی هفتم — اولویت ۳) =====
# python-magic اختیاری است.
#
# نسخهٔ قبلی `import magic` را در بالای فایل داشت بدون هیچ محافظی.
# نتیجه: روی هر سیستمی که python-magic نصب نبود (و در
# requirements.txt هم نیست، چون روی ویندوز به libmagic سیستم نیاز
# دارد)، import این ماژول با ModuleNotFoundError می‌شکست — در حالی
# که خود کد پایین‌تر دو جا نوشته بود «اگر python-magic نصب نیست،
# فقط از پسوند استفاده کن»؛ آن مسیر پشتیبان هرگز قابل اجرا نبود.
#
# حالا اگر magic نباشد، از تشخیص امضامحورِ خالص‌پایتون
# (_detect_mime_by_signature) استفاده می‌شود که برای کاربرد این
# برنامه (جلوگیری از آپلود فایل جعلی با پسوند فریب‌دهنده) کافی است.
try:  # pragma: no cover - بستگی به محیط دارد
    import magic  # type: ignore
    MAGIC_AVAILABLE = True
    MAGIC_IMPORT_ERROR = None
except Exception as _exc:  # pragma: no cover
    magic = None
    MAGIC_AVAILABLE = False
    MAGIC_IMPORT_ERROR = _exc


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
    
    # ============================================================
    # تشخیص نوع فایل — بازرسی هفتم
    # ============================================================

    # امضاهای آغازین فایل‌ها (magic number) برای زمانی که
    # python-magic در دسترس نیست. کلید = MIME، مقدار = لیست امضا.
    SIGNATURES = {
        'image/jpeg': [b'\xff\xd8\xff'],
        'image/png': [b'\x89PNG\r\n\x1a\n'],
        'image/gif': [b'GIF87a', b'GIF89a'],
        'image/bmp': [b'BM'],
        'image/webp': [b'RIFF'],
        'image/tiff': [b'II*\x00', b'MM\x00*'],
        'image/x-icon': [b'\x00\x00\x01\x00'],
        'application/pdf': [b'%PDF-'],
        'application/zip': [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],
        'application/x-rar-compressed': [b'Rar!\x1a\x07'],
        'application/x-7z-compressed': [b"7z\xbc\xaf'\x1c"],
        'application/gzip': [b'\x1f\x8b'],
        'application/msword': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],
        'audio/mpeg': [b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'],
        'audio/x-wav': [b'RIFF'],
        'audio/ogg': [b'OggS'],
        'audio/flac': [b'fLaC'],
        'audio/mp4': [b'ftypM4A'],
        'video/x-msvideo': [b'RIFF'],
        'video/x-matroska': [b'\x1aE\xdf\xa3'],
        'video/mp4': [b'ftyp'],
        'video/webm': [b'\x1aE\xdf\xa3'],
    }

    # نگاشت MIME امضامحور به MIMEهای مورد انتظارِ پروژه
    # (چند MIME متفاوت می‌توانند یک دستهٔ یکسان باشند)
    MIME_ALIASES = {
        'application/zip': 'application/zip',
        'application/x-rar-compressed': 'application/x-rar-compressed',
        'application/x-7z-compressed': 'application/x-7z-compressed',
        'application/gzip': 'application/gzip',
        'application/msword': 'application/msword',
        'audio/x-wav': 'audio/wav',
        'video/x-matroska': 'video/x-matroska',
        'video/x-msvideo': 'video/x-msvideo',
    }

    # امضاهای خطرناک: فایل اجرایی/اسکریپت با هر پسوندی رد می‌شود.
    # اینها را نمی‌توان «از پسوند» حدس زد؛ تشخیص محتوایی لازم است.
    DANGEROUS_SIGNATURES = {
        'فایل اجرایی ویندوز (PE)': b'MZ',
        'فایل اجرایی لینوکس (ELF)': b'\x7fELF',
        'کلاس جاوا': b'\xca\xfe\xba\xbe',
        'میان‌بر ویندوز (LNK)': b'\x4c\x00\x00\x00',
        'کتابخانهٔ ویندوز (DLL)': b'MZ',
    }

    @classmethod
    def _detect_dangerous(cls, file_data: bytes) -> Optional[str]:
        """
        آیا محتوای فایل اجرایی/اسکریپت است؟ (بازرسی هفتم)

        چرا لازم شد: چون وقتی پسوند فایل در فهرست مجاز باشد و
        محتوای آن قابل تشخیص نباشد، اعتبارسنجی «معتبر» می‌گفت. یعنی
        یک فایل اجرایی با نام «عکس.png» از فیلتر رد می‌شد. تست روی
        کد قبلی:
            validate_file(b'MZ\x90\x00' + ... , 'evil.png')
            → (True, 'فایل معتبر است')     ← بایستی رد می‌شد
        """
        if not file_data:
            return None
        head = file_data[:8]
        if head.startswith(b'#!'):
            return 'اسکریپت (shebang)'
        for label, sig in cls.DANGEROUS_SIGNATURES.items():
            if head.startswith(sig):
                # «MZ» دو بایتی ممکن است تصادفی باشد؛ فایل اجرایی
                # واقعی هدر DOS بزرگ‌تری دارد
                if sig == b'MZ' and len(file_data) < 64:
                    continue
                return label
        return None

    @classmethod
    def _detect_mime_by_signature(cls, file_data: bytes) -> Optional[str]:
        """
        تشخیص نوع فایل از روی امضای آغازین (بدون python-magic)

        این پشتیبان برای محیط‌هایی است که python-magic نصب نیست.
        اگر هیچ امضایی نخورد، None برمی‌گردد تا منطق بعدی از
        پسوند استفاده کند. (برای فایل‌های متنی مثل csv/json که امضای
        باینری ندارند، تشخیص بر عهدهٔ پسوند می‌ماند.)
        """
        if not file_data:
            return None

        head = file_data[:32]

        # قالب‌های ISO-BMFF (mp4/m4a/3gp/…): «ftyp» در بایت ۴
        if len(head) >= 12 and head[4:8] == b'ftyp':
            brand = head[8:12]
            if brand in (b'M4A ', b'M4B ', b'M4P '):
                return 'audio/mp4'
            return 'video/mp4'

        for mime, signatures in cls.SIGNATURES.items():
            for sig in signatures:
                if head.startswith(sig):
                    # چند فرمت RIFF/zim وجود دارد؛ کمی دقیق‌تر نگاه کن
                    if sig == b'RIFF' and len(head) >= 12:
                        sub = head[8:12]
                        if sub == b'WEBP':
                            return 'image/webp'
                        if sub == b'WAVE':
                            return 'audio/wav'
                        if sub == b'AVI ':
                            return 'video/x-msvideo'
                        continue
                    if sig == b'ftyp' and len(head) >= 12:
                        if head[4:8] == b'ftypM4A':
                            return 'audio/mp4'
                        return 'video/mp4'
                    return cls.MIME_ALIASES.get(mime, mime)
        return None

    @classmethod
    def _detect_mime(cls, file_data: bytes) -> Optional[str]:
        """
        تشخیص MIME فایل — با python-magic اگر باشد، وگرنه امضامحور

        این تنها نقطهٔ تشخیص نوع است؛ هر دو مسیر قبلی (validate_file
        و get_file_info) از همین استفاده می‌کنند تا رفتار یکدست بماند.
        """
        if MAGIC_AVAILABLE:
            try:
                return magic.from_buffer(file_data, mime=True)
            except Exception:
                # حتی وقتی نصب است ممکن است روی بعضی داده‌ها خطا بدهد
                pass
        return cls._detect_mime_by_signature(file_data)

    @classmethod
    def detection_backend(cls) -> str:
        """نام موتور تشخیص نوع فایل (برای نمایش در لاگ/دربارهٔ برنامه)"""
        return 'python-magic' if MAGIC_AVAILABLE else 'امضای محتوا (پشتیبان)'

    @classmethod
    def _category_from_extension(cls, ext: str) -> Optional[str]:
        """پیدا کردن دستهٔ فایل از روی پسوند"""
        ext = (ext or '').lower()
        for category, extensions in cls.ALLOWED_EXTENSIONS.items():
            if ext in extensions:
                return category
        return None

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
        
        # ===== ۵) بررسی MIME (بازرسی هفتم) =====
        # قبلاً یک try/except لخت دور magic بود و مسیر «اگر نصب
        # نیست» عملاً هرگز اجرا نمی‌شد. حالا _detect_mime اگر magic
        # نباشد از امضای محتوا استفاده می‌کند.
        # فایل‌های اجرایی/اسکریپت با هر پسوند و نامی رد می‌شوند
        dangerous = cls._detect_dangerous(file_data)
        if dangerous:
            errors.append(
                f"محتوای فایل «{dangerous}» است و مجاز نیست؛ "
                "پسوند فایل با محتوای آن هم‌خوان نیست."
            )
            return False, "\n".join(errors), info

        mime = cls._detect_mime(file_data)
        info['mime_type'] = mime

        if mime and mime in cls.ALLOWED_MIME_TYPES:
            info['category'] = cls.ALLOWED_MIME_TYPES[mime]
            info['file_type'] = mime
        else:
            # MIME ناشناخته یا در فهرست مجاز نبود → ملاک، پسوند است
            category = cls._category_from_extension(ext)
            if category:
                info['category'] = category
                info['file_type'] = mime
            else:
                errors.append(f"نوع فایل '{mime or 'ناشناخته'}' مجاز نیست")
        
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
        
        # ===== اصلاح (بازرسی هفتم) =====
        # قبلاً try/except لخت دور magic بود. حالا از مسیر مشترک
        # _detect_mime استفاده می‌شود (magic اگر باشد، وگرنه امضا).
        mime = cls._detect_mime(file_data)
        info['mime_type'] = mime
        if mime and mime in cls.ALLOWED_MIME_TYPES:
            info['category'] = cls.ALLOWED_MIME_TYPES[mime]
        else:
            info['category'] = cls._category_from_extension(info['extension'])

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