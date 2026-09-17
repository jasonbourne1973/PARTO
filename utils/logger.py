"""
سیستم Logging استاندارد برای کل پروژه
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json

# ایمیل پشتیبانی
SUPPORT_EMAIL = "jaadougaroz1960@gmail.com"


def _resolve_log_dir():
    """
    پیدا کردن پوشه مناسب برای لاگ‌ها

    نسخه قبلی این بود:
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')

    مشکل: در بسته PyInstaller، __file__ داخل bundle است که فقط‌خواندنی
    است. پس os.makedirs شکست می‌خورد و کل برنامه بالا نمی‌آمد.

    حالا به ترتیب این مسیرها امتحان می‌شوند:
      ۱. متغیر محیطی PARTOW_LOG_DIR (برای تست و استقرار سفارشی)
      ۲. پوشه قابل نوشتن کاربر (AppData در ویندوز)
      ۳. پوشه logs کنار پروژه (حالت توسعه)
    """
    candidates = []

    # ۱. متغیر محیطی
    env_dir = os.environ.get('PARTOW_LOG_DIR')
    if env_dir:
        candidates.append(env_dir)

    # ۲. پوشه قابل نوشتن کاربر
    if sys.platform == 'win32':
        base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
        candidates.append(os.path.join(base, 'PARTOW', 'logs'))
    else:
        candidates.append(os.path.expanduser('~/.local/share/PARTOW/logs'))

    # ۳. پوشه logs کنار پروژه
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates.append(os.path.join(project_root, 'logs'))
    except NameError:
        pass

    for candidate in candidates:
        try:
            os.makedirs(candidate, exist_ok=True)
            # بررسی واقعاً قابل نوشتن بودن
            probe = os.path.join(candidate, '.write_test')
            with open(probe, 'w') as f:
                f.write('ok')
            os.remove(probe)
            return candidate
        except OSError:
            continue

    # آخرین چاره: پوشه موقت سیستم
    import tempfile
    fallback = os.path.join(tempfile.gettempdir(), 'partow_logs')
    os.makedirs(fallback, exist_ok=True)
    return fallback



class CustomFormatter(logging.Formatter):
    """فرمت‌دهنده سفارشی برای لاگ‌ها"""
    
    def format(self, record):
        # اضافه کردن زمان به صورت ISO
        record.iso_time = datetime.now().isoformat()
        
        # اضافه کردن نام ماژول
        if not hasattr(record, 'module_name'):
            record.module_name = record.name
        
        return super().format(record)


class Logger:
    """مدیریت لاگ‌های برنامه"""
    
    _instance = None
    _loggers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """مقداردهی اولیه سیستم لاگ"""
        # ایجاد پوشه logs
        log_dir = _resolve_log_dir()
        self.log_dir = log_dir
        self.log_level = logging.DEBUG
        self.max_file_size = 10 * 1024 * 1024  # 10 MB
        self.backup_count = 5
        
        # فرمت لاگ
        self.formatter = CustomFormatter(
            '%(iso_time)s | %(levelname)-8s | %(module_name)-20s | %(funcName)-15s | %(lineno)-4d | %(message)s'
        )
        
        # لاگ‌های عمومی (همه چیز)
        self._setup_general_logger()
        
        # لاگ‌های خطا (فقط ERROR و بالا)
        self._setup_error_logger()
        
        # لاگ‌های امنیتی (Audit)
        self._setup_audit_logger()
    
    def _setup_general_logger(self):
        """تنظیم لاگر عمومی"""
        self.general_logger = logging.getLogger('general')
        self.general_logger.setLevel(self.log_level)
        
        # فایل Handler
        log_file = os.path.join(self.log_dir, 'partow.log')
        handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        handler.setFormatter(self.formatter)
        self.general_logger.addHandler(handler)
        
        # Console Handler (برای توسعه)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self.formatter)
        self.general_logger.addHandler(console_handler)
    
    def _setup_error_logger(self):
        """تنظیم لاگر خطاها"""
        self.error_logger = logging.getLogger('error')
        self.error_logger.setLevel(logging.ERROR)
        
        # فایل Handler
        log_file = os.path.join(self.log_dir, 'errors.log')
        handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        # ===== نکته مهم =====
        # سطح باید روی خود هندلر ست شود، نه فقط روی لاگر.
        # دلیل: این هندلر به لاگرهای partow.* هم متصل می‌شود
        # (در get_logger) و سطح آن‌ها DEBUG است. اگر سطح فقط روی
        # error_logger باشد، لاگ‌های INFO هم به errors.log می‌روند.
        handler.setLevel(logging.ERROR)
        handler.setFormatter(self.formatter)
        self.error_logger.addHandler(handler)
    
    def _setup_audit_logger(self):
        """تنظیم لاگر امنیتی"""
        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.setLevel(logging.INFO)
        
        # فایل Handler (با فرمت JSON)
        log_file = os.path.join(self.log_dir, 'audit.json')
        handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        
        # فرمت JSON برای Audit
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'level': record.levelname,
                    'module': record.name,
                    'user_id': getattr(record, 'user_id', None),
                    'action': getattr(record, 'action', None),
                    'message': record.getMessage()
                }
                return json.dumps(log_entry, ensure_ascii=False)
        
        handler.setFormatter(JSONFormatter())
        self.audit_logger.addHandler(handler)
    
    def get_logger(self, name):
        """
        دریافت یک لاگر با نام مشخص
        
        Args:
            name: نام لاگر (معمولاً نام کلاس)
            
        Returns:
            logging.Logger: شیء لاگر
        """
        if name not in self._loggers:
            logger = logging.getLogger(f'partow.{name}')
            logger.setLevel(self.log_level)

            # ===== اصلاح مهم =====
            # نسخه قبلی فقط هندلرهای general_logger را کپی می‌کرد.
            # نتیجه: errors.log که برای تشخیص سریع خطاها ساخته شده بود
            # همیشه خالی می‌ماند، چون log_error() و ErrorHandler هر دو
            # از همین مسیر می‌آمدند.
            # حالا هندلر فایل خطاها هم اضافه می‌شود. چون سطح آن
            # ERROR است، فقط خطاها را می‌گیرد.
            for handler in self.general_logger.handlers:
                logger.addHandler(handler)

            for handler in self.error_logger.handlers:
                if handler not in logger.handlers:
                    logger.addHandler(handler)

            # جلوگیری از تکرار لاگ در root logger
            logger.propagate = False

            self._loggers[name] = logger

        return self._loggers[name]
    
    def get_audit_logger(self):
        """دریافت لاگر امنیتی"""
        return self.audit_logger
    
    def get_error_logger(self):
        """دریافت لاگر خطاها"""
        return self.error_logger


# ===== توابع کمکی برای استفاده آسان =====

_logger_instance = None

def get_logger(name):
    """دریافت یک لاگر با نام مشخص"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = Logger()
    return _logger_instance.get_logger(name)

def log_info(name, message, **kwargs):
    """ثبت لاگ INFO"""
    logger = get_logger(name)
    logger.info(message, extra=kwargs)

def log_warning(name, message, **kwargs):
    """ثبت لاگ WARNING"""
    logger = get_logger(name)
    logger.warning(message, extra=kwargs)

def log_error(name, message, **kwargs):
    """ثبت لاگ ERROR"""
    logger = get_logger(name)
    logger.error(message, extra=kwargs)

def log_debug(name, message, **kwargs):
    """ثبت لاگ DEBUG"""
    logger = get_logger(name)
    logger.debug(message, extra=kwargs)

def log_audit(user_id, action, message, **kwargs):
    """ثبت لاگ امنیتی"""
    logger = Logger().get_audit_logger()
    extra = {'user_id': user_id, 'action': action}
    extra.update(kwargs)
    logger.info(message, extra=extra)