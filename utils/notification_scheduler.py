"""
زمان‌بندی اعلان‌ها و یادآوری‌های خودکار
"""

import threading
import time

from services.notification_service import NotificationService
from utils.logger import get_logger


class NotificationScheduler:
    """
    زمان‌بندی اعلان‌ها و یادآوری‌های خودکار
    
    ویژگی‌ها:
    - اجرای دوره‌ای بررسی پیگیری‌ها
    - ایجاد یادآوری‌های خودکار
    - پاکسازی اعلان‌های قدیمی
    """
    
    _instance = None
    _running = False
    _thread = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationScheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.logger = get_logger(self.__class__.__name__)
        self.notification_service = NotificationService()
        self._running = False
        self._thread = None
    
    def start(self, interval_minutes=60):
        """
        شروع زمان‌بندی
        
        Args:
            interval_minutes: فاصله زمانی بین اجراها (دقیقه)
        """
        if self._running:
            self.logger.warning("زمان‌بندی اعلان‌ها قبلاً شروع شده است.")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._worker,
            args=(interval_minutes,),
            daemon=True
        )
        self._thread.start()
        self.logger.info(f"زمان‌بندی اعلان‌ها شروع شد (هر {interval_minutes} دقیقه)")
    
    def stop(self):
        """توقف زمان‌بندی"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self.logger.info("زمان‌بندی اعلان‌ها متوقف شد")
    
    def _worker(self, interval_minutes):
        """کارگر زمان‌بندی"""
        while self._running:
            try:
                self._run_scheduled_tasks()
            except Exception as e:
                self.logger.error(f"خطا در اجرای وظایف زمان‌بندی: {e}")
            
            # منتظر ماندن تا زمان بعدی
            for _ in range(interval_minutes * 60):
                if not self._running:
                    break
                time.sleep(1)
    
    def _run_scheduled_tasks(self):
        """اجرای وظایف زمان‌بندی شده"""
        self.logger.debug("اجرای وظایف زمان‌بندی اعلان‌ها...")
        
        # 1. ایجاد یادآوری‌ها
        result = self.notification_service.check_and_create_reminders()
        if result['total'] > 0:
            self.logger.info(
                f"{result['created_count']} یادآوری و "
                f"{result['overdue_count']} اعلان معوق ایجاد شد"
            )
        
        # 2. پاکسازی اعلان‌های قدیمی (هر ۲۴ ساعت یکبار)
        # بررسی اینکه آیا امروز پاکسازی انجام شده است
        if self._should_cleanup():
            self.notification_service.cleanup_old_notifications()
            self.logger.info("پاکسازی اعلان‌های قدیمی انجام شد")
    
    def _should_cleanup(self):
        """بررسی اینکه آیا پاکسازی باید انجام شود"""
        # در این نسخه ساده، هر بار که وظیفه اجرا می‌شود، پاکسازی انجام می‌شود
        # برای بهبود می‌توان یک فایل نشانگر ذخیره کرد
        return True
    
    def run_once(self):
        """اجرای یک بار وظایف زمان‌بندی (برای تست)"""
        self.logger.info("اجرای یک بار وظایف زمان‌بندی...")
        self._run_scheduled_tasks()
        return True


# ===== تابع کمکی برای شروع زمان‌بندی =====

_scheduler_instance = None

def start_notification_scheduler(interval_minutes=60):
    """
    شروع زمان‌بندی اعلان‌ها
    
    Args:
        interval_minutes: فاصله زمانی بین اجراها (دقیقه)
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = NotificationScheduler()
    _scheduler_instance.start(interval_minutes)
    return _scheduler_instance

def stop_notification_scheduler():
    """توقف زمان‌بندی اعلان‌ها"""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None