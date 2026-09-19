"""
مدل پیوست - نسخه کامل با فیلدهای جدید
"""

from typing import ClassVar

from models.base import BaseModel


class Attachment(BaseModel):
    """
    مدل پیوست با پشتیبانی از فیلدهای جدید
    
    ویژگی‌ها:
    - پشتیبانی از انواع مختلف موجودیت‌ها
    - ذخیره اطلاعات کامل فایل
    - پشتیبانی از تگ‌ها و توضیحات
    """
    
    # انواع موجودیت‌های مجاز
    ENTITY_TYPES: ClassVar[list[str]] = [
        'observation',
        'intervention',
        'followup',
        'student',
        'profile',
        'report',
        'other'
    ]
    
    def __init__(self):
        super().__init__()
        # ===== اطلاعات پایه =====
        self.entity_type = None      # observation, intervention, followup, student, profile, report, other
        self.entity_id = None        # شناسه موجودیت
        
        # ===== اطلاعات فایل =====
        self.file_name = None        # نام اصلی فایل
        self.file_path = None        # مسیر ذخیره فایل
        self.file_size = None        # حجم فایل (بایت)
        self.file_type = None        # نوع فایل (image, document, audio, video, archive, other)
        self.mime_type = None        # MIME type فایل
        self.file_extension = None   # پسوند فایل
        
        # ===== اطلاعات اضافی =====
        self.title = None            # عنوان (اختیاری)
        self.description = None      # توضیحات (اختیاری)
        self.tags = None             # برچسب‌ها (JSON)
        
        # ===== کاربر =====
        self.created_by = None       # شناسه کاربر آپلودکننده
        
        # ===== فیلدهای کمکی =====
        self.created_by_name = None  # نام کاربر آپلودکننده
        self.display_size = None     # حجم فرمت‌شده
        self.display_type = None     # نوع نمایشی
        self.icon = None             # آیکون
        self.can_preview = False     # قابلیت پیش‌نمایش
    
    @property
    def file_size_display(self):
        """نمایش حجم فایل به صورت فرمت‌شده"""
        if not self.file_size:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
    
    @property
    def extension(self):
        """دریافت پسوند فایل"""
        if '.' in self.file_name:
            return self.file_name.rsplit('.', 1)[1].lower()
        return ''
    
    @property
    def is_image(self):
        """آیا فایل تصویر است؟"""
        return self.file_type == 'image'
    
    @property
    def is_document(self):
        """آیا فایل سند است؟"""
        return self.file_type == 'document'
    
    @property
    def is_audio(self):
        """آیا فایل صوتی است؟"""
        return self.file_type == 'audio'
    
    @property
    def is_video(self):
        """آیا فایل ویدئویی است؟"""
        return self.file_type == 'video'
    
    def validate(self):
        errors = []
        if not self.entity_type:
            errors.append("نوع موجودیت باید مشخص شود")
        if self.entity_type and self.entity_type not in self.ENTITY_TYPES:
            errors.append(f"نوع موجودیت '{self.entity_type}' نامعتبر است")
        if not self.entity_id:
            errors.append("شناسه موجودیت باید مشخص شود")
        if not self.file_name:
            errors.append("نام فایل باید مشخص شود")
        if not self.file_path:
            errors.append("مسیر فایل باید مشخص شود")
        if self.file_size is None:
            errors.append("حجم فایل باید مشخص شود")
        return errors