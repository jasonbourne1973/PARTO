"""
سرویس مدیریت پیوست‌ها - نسخه کامل با قابلیت‌های جدید
"""

import hashlib
import mimetypes
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import ClassVar

from config.settings import ATTACHMENTS_DIR
from dal.attachment_dal import AttachmentDAL
from models.attachment import Attachment
from services.base_service import BaseService
from utils.error_handler import ServiceError, ValidationError
from utils.logger import get_logger
from utils.security import Security
from utils.time_utils import utc_now


class AttachmentService(BaseService):
    """
    سرویس مدیریت پیوست‌ها - نسخه کامل
    
    تمام منطق مربوط به فایل‌های پیوست در این سرویس قرار دارد.
    """
    
    # انواع فایل‌های مجاز
    ALLOWED_FILE_TYPES: ClassVar[dict[str, str]] = {
        'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'tiff', 'ico'],
        'document': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf', 'odt', 'ods', 'odp'],
        'audio': ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma'],
        'video': ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v'],
        'archive': ['zip', 'rar', '7z', 'tar', 'gz'],
        'other': ['csv', 'json', 'xml', 'html', 'css', 'js', 'log']
    }
    
    # حداکثر حجم فایل (۲۰ مگابایت)
    MAX_FILE_SIZE = 20 * 1024 * 1024
    
    # حداکثر تعداد پیوست در هر موجودیت
    MAX_ATTACHMENTS_PER_ENTITY = 20
    
    def __init__(self):
        super().__init__()
        self.attachment_dal = AttachmentDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    def upload_attachment(self, entity_type, entity_id, file_data, file_name, 
                          title=None, description=None, tags=None,
                          created_by=None, user_id=None, ip_address=None):
        """
        آپلود و ثبت پیوست جدید - نسخه کامل
        
        Args:
            entity_type: نوع موجودیت
            entity_id: شناسه موجودیت
            file_data: محتوای فایل (bytes)
            file_name: نام فایل
            title: عنوان (اختیاری)
            description: توضیحات (اختیاری)
            tags: برچسب‌ها (اختیاری)
            created_by: شناسه کاربر ایجادکننده
            user_id: شناسه کاربر (برای Audit)
            ip_address: آدرس IP کاربر
            
        Returns:
            Attachment: پیوست ایجاد شده
            
        Raises:
            ServiceError: در صورت بروز خطا
            ValidationError: در صورت عدم اعتبار فایل
        """
        def _upload():
            # 1. اعتبارسنجی فایل
            self._validate_file(file_data, file_name)
            
            # 2. بررسی حداکثر تعداد پیوست‌ها
            existing_count = self.attachment_dal.get_count_by_entity(entity_type, entity_id)
            if existing_count >= self.MAX_ATTACHMENTS_PER_ENTITY:
                raise ValidationError(
                    f"تعداد پیوست‌های این موجودیت به حداکثر ({self.MAX_ATTACHMENTS_PER_ENTITY}) رسیده است."
                )
            
            # 3. ایجاد نام فایل ایمن
            safe_filename = self._generate_safe_filename(file_name)
            
            # 4. ایجاد پوشه موجودیت
            entity_folder = self._get_entity_folder(entity_type, entity_id)
            if not os.path.exists(entity_folder):
                os.makedirs(entity_folder)
            
            # 5. ذخیره فایل
            file_path = os.path.join(entity_folder, safe_filename)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # 6. محاسبه checksum
            checksum = hashlib.md5(file_data).hexdigest()
            
            # 7. دریافت اطلاعات فایل
            file_size = len(file_data)
            file_type = self._get_file_category(file_name)
            mime_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
            extension = self._get_file_extension(file_name)
            
            # 8. ایجاد مدل Attachment
            attachment = Attachment()
            attachment.entity_type = entity_type
            attachment.entity_id = entity_id
            attachment.file_name = file_name
            attachment.file_path = file_path
            attachment.file_size = file_size
            attachment.file_type = file_type
            attachment.mime_type = mime_type
            attachment.file_extension = extension
            attachment.title = title
            attachment.description = description
            attachment.tags = tags
            attachment.created_by = created_by
            
            # 9. اعتبارسنجی مدل
            errors = attachment.validate()
            if errors:
                # حذف فایل ذخیره شده
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise ValidationError("\n".join(errors))
            
            # 10. ذخیره در دیتابیس
            created_attachment = self.attachment_dal.create(attachment)
            
            # 11. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='create',
                entity_type='attachment',
                entity_id=created_attachment.id,
                new_value={
                    'attachment_id': created_attachment.id,
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'file_name': file_name,
                    'file_size': file_size,
                    'checksum': checksum
                },
                ip_address=ip_address
            )
            
            self.logger.info(f"پیوست با ID {created_attachment.id} برای {entity_type}/{entity_id} آپلود شد")
            return created_attachment
        
        return self.execute_in_transaction(_upload)
    
    def get_attachment(self, attachment_id):
        """دریافت پیوست با شناسه"""
        try:
            attachment = self.attachment_dal.get_by_id(attachment_id)
            if not attachment:
                raise ServiceError(f"پیوست با شناسه {attachment_id} یافت نشد.")
            self._enrich_attachment(attachment)
            return attachment
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیوست: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_attachments_by_entity(self, entity_type, entity_id):
        """دریافت پیوست‌های یک موجودیت"""
        try:
            attachments = self.attachment_dal.get_by_entity(entity_type, entity_id)
            for att in attachments:
                self._enrich_attachment(att)
            return attachments
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیوست‌ها: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def delete_attachment(self, attachment_id, user_id=None, ip_address=None):
        """حذف پیوست"""
        def _delete():
            attachment = self.attachment_dal.get_by_id(attachment_id)
            if not attachment:
                raise ServiceError(f"پیوست با شناسه {attachment_id} یافت نشد.")
            
            old_value = {
                'id': attachment.id,
                'file_name': attachment.file_name,
                'entity_type': attachment.entity_type,
                'entity_id': attachment.entity_id,
                'file_size': attachment.file_size
            }
            
            result = self.attachment_dal.delete(attachment_id, user_id)
            
            self.log_audit(
                user_id=user_id,
                action='delete_soft',
                entity_type='attachment',
                entity_id=attachment_id,
                old_value=old_value,
                ip_address=ip_address
            )
            
            self.logger.info(f"پیوست با ID {attachment_id} حذف شد")
            return result
        
        return self.execute_in_transaction(_delete)
    
    def delete_attachments_by_entity(self, entity_type, entity_id, user_id=None):
        """حذف تمام پیوست‌های یک موجودیت"""
        try:
            attachments = self.attachment_dal.get_by_entity(entity_type, entity_id)
            for att in attachments:
                self.delete_attachment(att.id, user_id)
            return True
        except Exception as e:
            self.logger.error(f"خطا در حذف پیوست‌ها: {e}")
            raise ServiceError(f"خطا در حذف: {e!s}")
    
    def get_attachment_path(self, attachment_id):
        """دریافت مسیر فیزیکی فایل پیوست"""
        attachment = self.get_attachment(attachment_id)
        if not os.path.exists(attachment.file_path):
            raise ServiceError("فایل پیوست در سیستم وجود ندارد.")
        return attachment.file_path
    
    def get_attachment_content(self, attachment_id):
        """دریافت محتوای فایل پیوست"""
        file_path = self.get_attachment_path(attachment_id)
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"خطا در خواندن فایل: {e}")
            raise ServiceError(f"خطا در خواندن فایل: {e!s}")
    
    def get_attachments_summary(self, entity_type, entity_id):
        """دریافت خلاصه پیوست‌های یک موجودیت"""
        attachments = self.get_attachments_by_entity(entity_type, entity_id)
        total_size = sum(a.file_size for a in attachments)
        
        by_type = {}
        for att in attachments:
            if att.file_type not in by_type:
                by_type[att.file_type] = {'count': 0, 'size': 0}
            by_type[att.file_type]['count'] += 1
            by_type[att.file_type]['size'] += att.file_size
        
        return {
            'total_count': len(attachments),
            'total_size': total_size,
            'total_size_display': self._format_size(total_size),
            'by_type': by_type,
            'attachments': attachments
        }
    
    def search_attachments(self, entity_type, entity_id, search_text):
        """جستجوی پیوست‌ها بر اساس متن"""
        try:
            attachments = self.get_attachments_by_entity(entity_type, entity_id)
            search_lower = search_text.lower()
            results = []
            for att in attachments:
                if (search_lower in att.file_name.lower() or
                    (att.title and search_lower in att.title.lower()) or
                    (att.description and search_lower in att.description.lower())):
                    results.append(att)
            return results
        except Exception as e:
            self.logger.error(f"خطا در جستجوی پیوست‌ها: {e}")
            return []
    
    def _validate_file(self, file_data, file_name):
        """اعتبارسنجی فایل"""
        errors = []
        
        if not file_data:
            errors.append("محتوای فایل نمی‌تواند خالی باشد.")
        
        if len(file_data) > self.MAX_FILE_SIZE:
            errors.append(f"حجم فایل از حد مجاز ({self.MAX_FILE_SIZE // (1024*1024)} مگابایت) بیشتر است.")
        
        if not file_name:
            errors.append("نام فایل نمی‌تواند خالی باشد.")
        
        ext = self._get_file_extension(file_name).lower()
        if ext:
            all_extensions = []
            for exts in self.ALLOWED_FILE_TYPES.values():
                all_extensions.extend(exts)
            
            if ext not in all_extensions:
                errors.append(f"نوع فایل '{ext}' مجاز نیست. پسوندهای مجاز: {', '.join(all_extensions)}")
        else:
            errors.append("فایل بدون پسوند است.")

        # ===== افزودن (بازرسی هفتم — اولویت ۳) =====
        # بررسی محتوای فایل، نه فقط پسوند.
        #
        # پیش از این، اعتبارسنجی فقط پسوند را می‌دید؛ یعنی یک فایل
        # اجرایی با نام «عکس.png» به‌عنوان پیوست ذخیره می‌شد. ابزار
        # `utils/file_validator.py` دقیقاً برای همین نوشته شده بود
        # ولی هیچ‌جا import نمی‌شد و ماژول هم به‌دلیل `import magic`
        # (که نصب نبود) اصلاً بالا نمی‌آمد.
        #
        # حالا محتوای مشکوک رد می‌شود. این بررسی عمداً «پسوند‌محور»
        # نیست؛ اگر کتابخانه در دسترس نباشد، هیچ پیوستی بی‌دلیل
        # رد نمی‌شود (شکست نرم).
        try:
            from utils.file_validator import FileValidator
            danger = FileValidator._detect_dangerous(file_data)
            if danger:
                errors.append(
                    f"محتوای فایل «{danger}» است و مجاز نیست؛ "
                    "پسوند فایل با محتوای آن هم‌خوان نیست."
                )
        except Exception as exc:  # pragma: no cover - مسیر پشتیبان
            self.logger.warning(f"بررسی محتوای فایل انجام نشد: {exc}")

        if errors:
            raise ValidationError("\n".join(errors))
    
    def _generate_safe_filename(self, original_name):
        """تولید نام فایل ایمن"""
        safe_name = Security.sanitize_filename(original_name)
        
        if not safe_name:
            safe_name = f"file_{int(utc_now().timestamp())}"
        
        name_parts = safe_name.rsplit('.', 1)
        if len(name_parts) == 2:
            base, ext = name_parts
            return f"{base}_{int(utc_now().timestamp())}.{ext}"
        else:
            return f"{safe_name}_{int(utc_now().timestamp())}"
    
    def _get_entity_folder(self, entity_type, entity_id):
        """دریافت پوشه ذخیره فایل‌های یک موجودیت"""
        return os.path.join(ATTACHMENTS_DIR, entity_type, str(entity_id))
    
    def _get_file_category(self, file_name):
        """دریافت دسته‌بندی فایل بر اساس پسوند"""
        ext = self._get_file_extension(file_name).lower()
        for category, extensions in self.ALLOWED_FILE_TYPES.items():
            if ext in extensions:
                return category
        return 'other'
    
    def _get_file_extension(self, file_name):
        """دریافت پسوند فایل"""
        if '.' in file_name:
            return file_name.rsplit('.', 1)[1].lower()
        return ''
    
    def _get_file_type_display(self, file_name):
        """دریافت نمایش فارسی نوع فایل"""
        ext = self._get_file_extension(file_name).lower()
        
        type_map = {
            'pdf': 'PDF',
            'doc': 'Word',
            'docx': 'Word',
            'xls': 'Excel',
            'xlsx': 'Excel',
            'ppt': 'PowerPoint',
            'pptx': 'PowerPoint',
            'txt': 'متن',
            'jpg': 'تصویر',
            'jpeg': 'تصویر',
            'png': 'تصویر',
            'gif': 'تصویر',
            'mp3': 'صوت',
            'mp4': 'ویدئو',
            'zip': 'بایگانی',
            'rar': 'بایگانی',
        }
        
        return type_map.get(ext, ext.upper())
    
    def _get_file_icon(self, file_name):
        """دریافت آیکون مناسب برای فایل"""
        ext = self._get_file_extension(file_name).lower()
        
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
            'mp3': '🎵',
            'wav': '🎵',
            'mp4': '🎬',
            'avi': '🎬',
            'zip': '📦',
            'rar': '📦',
        }
        
        return icon_map.get(ext, '📎')
    
    def _can_preview(self, file_name):
        """بررسی قابلیت پیش‌نمایش فایل"""
        ext = self._get_file_extension(file_name).lower()
        preview_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'pdf', 'txt', 'doc', 'docx']
        return ext in preview_extensions
    
    def _format_size(self, size):
        """فرمت‌سازی حجم فایل"""
        if not size:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def _enrich_attachment(self, attachment):
        """افزودن اطلاعات تکمیلی به پیوست"""
        attachment.display_size = self._format_size(attachment.file_size)
        attachment.display_type = self._get_file_type_display(attachment.file_name)
        attachment.icon = self._get_file_icon(attachment.file_name)
        attachment.can_preview = self._can_preview(attachment.file_name)
        
        # افزودن نام کاربر
        if attachment.created_by:
            try:
                from dal.staff_dal import StaffDAL
                staff_dal = StaffDAL()
                staff = staff_dal.get_by_id(attachment.created_by)
                if staff:
                    attachment.created_by_name = staff.full_name
            except Exception:
                attachment.created_by_name = "نامشخص"