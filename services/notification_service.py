"""
سرویس مدیریت اعلان‌ها و یادآوری‌ها
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.notification_dal import NotificationDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.notification import Notification
from services.base_service import BaseService
from utils.error_handler import ServiceError
from utils.logger import get_logger
from utils.time_utils import utc_now_iso


class NotificationService(BaseService):
    """
    سرویس مدیریت اعلان‌ها و یادآوری‌ها
    
    ویژگی‌ها:
    - ایجاد اعلان‌های سیستم
    - یادآوری‌های خودکار پیگیری‌ها
    - مدیریت اعلان‌های خوانده/نخوانده
    - پاکسازی اعلان‌های قدیمی
    """
    
    def __init__(self):
        super().__init__()
        self.notification_dal = NotificationDAL()
        self.followup_dal = FollowUpDAL()
        self.intervention_dal = InterventionDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    def create_notification(self, user_id, notification_type, title, message,
                           priority=None, link=None, entity_type=None, entity_id=None,
                           scheduled_at=None, expires_at=None):
        """
        ایجاد اعلان جدید
        
        Args:
            user_id: شناسه کاربر گیرنده
            notification_type: نوع اعلان
            title: عنوان
            message: پیام
            priority: اولویت (high/medium/low)
            link: لینک مرتبط
            entity_type: نوع موجودیت مرتبط
            entity_id: شناسه موجودیت مرتبط
            scheduled_at: زمان برنامه‌ریزی‌شده
            expires_at: زمان انقضا
        
        Returns:
            Notification: اعلان ایجاد شده
        """
        notification = Notification()
        notification.user_id = user_id
        notification.type = notification_type
        notification.priority = priority or Notification.PRIORITY_MEDIUM
        notification.title = title
        notification.message = message
        notification.link = link
        notification.entity_type = entity_type
        notification.entity_id = entity_id
        notification.scheduled_at = scheduled_at
        notification.expires_at = expires_at
        
        errors = notification.validate()
        if errors:
            raise ServiceError("\n".join(errors))
        
        return self.notification_dal.create(notification)
    
    def get_user_notifications(self, user_id, limit=20, include_read=False):
        """
        دریافت اعلان‌های یک کاربر
        
        Args:
            user_id: شناسه کاربر
            limit: تعداد محدود
            include_read: آیا اعلان‌های خوانده شده را هم شامل شود؟
        
        Returns:
            list: لیست اعلان‌ها
        """
        try:
            notifications = self.notification_dal.get_by_user(
                user_id, limit, include_read
            )
            
            # افزودن اطلاعات تکمیلی
            for notif in notifications:
                self._enrich_notification(notif)
            
            return notifications
        except Exception as e:
            self.logger.error(f"خطا در دریافت اعلان‌ها: {e}")
            raise ServiceError(f"خطا در دریافت اعلان‌ها: {e!s}")
    
    def get_unread_count(self, user_id):
        """دریافت تعداد اعلان‌های خوانده نشده"""
        try:
            return self.notification_dal.get_unread_count(user_id)
        except Exception as e:
            self.logger.error(f"خطا در دریافت تعداد اعلان‌ها: {e}")
            return 0
    
    def mark_as_read(self, notification_id):
        """علامت‌گذاری اعلان به عنوان خوانده شده"""
        try:
            return self.notification_dal.mark_as_read(notification_id)
        except Exception as e:
            self.logger.error(f"خطا در علامت‌گذاری اعلان: {e}")
            raise ServiceError(f"خطا: {e!s}")
    
    def mark_all_as_read(self, user_id):
        """علامت‌گذاری همه اعلان‌های کاربر به عنوان خوانده شده"""
        try:
            return self.notification_dal.mark_all_as_read(user_id)
        except Exception as e:
            self.logger.error(f"خطا در علامت‌گذاری همه اعلان‌ها: {e}")
            raise ServiceError(f"خطا: {e!s}")
    
    def mark_as_dismissed(self, notification_id):
        """علامت‌گذاری اعلان به عنوان رد شده"""
        try:
            return self.notification_dal.mark_as_dismissed(notification_id)
        except Exception as e:
            self.logger.error(f"خطا در رد اعلان: {e}")
            raise ServiceError(f"خطا: {e!s}")
    
    def delete_notification(self, notification_id):
        """حذف اعلان"""
        try:
            return self.notification_dal.delete(notification_id)
        except Exception as e:
            self.logger.error(f"خطا در حذف اعلان: {e}")
            raise ServiceError(f"خطا: {e!s}")
    
    def create_reminder_for_followup(self, followup, user_id=None):
        """
        ایجاد یادآوری برای یک پیگیری
        
        Args:
            followup: شیء FollowUp
            user_id: شناسه کاربر (اگر مشخص نشده باشد، از staff_id پیگیری استفاده می‌شود)
        
        Returns:
            Notification: اعلان ایجاد شده
        """
        try:
            # دریافت اطلاعات پیگیری
            if not followup:
                return None
            
            # دریافت مداخله
            intervention = self.intervention_dal.get_by_id(followup.intervention_id)
            if not intervention:
                return None
            
            # دریافت دانش‌آموز
            profile = self.profile_dal.get_by_id(intervention.student_profile_id)
            if not profile:
                return None
            
            student = self.student_dal.get_by_id(profile.student_id)
            student_name = student.full_name if student else "نامشخص"
            
            # تعیین کاربر گیرنده
            recipient_id = user_id or followup.staff_id
            if not recipient_id:
                return None
            
            # ساخت عنوان و پیام
            title = f"یادآوری پیگیری - {student_name}"
            message = f"""
پیگیری برای دانش‌آموز {student_name} در تاریخ {followup.next_action_date or 'تعیین نشده'} برنامه‌ریزی شده است.

نوع مداخله: {intervention.type_display}
شرح: {followup.description or 'ثبت نشده'}

لطفاً اقدامات لازم را انجام دهید.
"""
            
            # تعیین اولویت بر اساس تاریخ
            priority = Notification.PRIORITY_MEDIUM
            if followup.next_action_date:
                try:
                    import jdatetime
                    today = jdatetime.date.today()
                    next_date_parts = followup.next_action_date.split('/')
                    if len(next_date_parts) == 3:
                        next_date = jdatetime.date(
                            int(next_date_parts[0]),
                            int(next_date_parts[1]),
                            int(next_date_parts[2])
                        )
                        days_diff = (next_date - today).days
                        if days_diff <= 1:
                            priority = Notification.PRIORITY_HIGH
                        elif days_diff <= 3:
                            priority = Notification.PRIORITY_MEDIUM
                except Exception as _exc:
                    self.logger.debug(
                        f"خطای غیرمنتظره در {self.__class__.__name__}: {_exc}"
                    )
            
            # ایجاد اعلان
            notification = self.create_notification(
                user_id=recipient_id,
                notification_type=Notification.TYPE_REMINDER,
                title=title,
                message=message.strip(),
                priority=priority,
                entity_type='followup',
                entity_id=followup.id,
                scheduled_at=utc_now_iso()
            )
            
            self.logger.info(f"یادآوری برای پیگیری {followup.id} ایجاد شد")
            return notification
            
        except Exception as e:
            self.logger.error(f"خطا در ایجاد یادآوری پیگیری: {e}")
            return None
    
    def create_overdue_notification(self, followup):
        """
        ایجاد اعلان معوق شدن پیگیری
        
        Args:
            followup: شیء FollowUp معوق شده
        
        Returns:
            Notification: اعلان ایجاد شده
        """
        try:
            # دریافت اطلاعات پیگیری
            if not followup:
                return None
            
            # دریافت مداخله
            intervention = self.intervention_dal.get_by_id(followup.intervention_id)
            if not intervention:
                return None
            
            # دریافت دانش‌آموز
            profile = self.profile_dal.get_by_id(intervention.student_profile_id)
            if not profile:
                return None
            
            student = self.student_dal.get_by_id(profile.student_id)
            student_name = student.full_name if student else "نامشخص"
            
            # تعیین کاربر گیرنده
            recipient_id = followup.staff_id
            if not recipient_id:
                return None
            
            # ساخت عنوان و پیام
            title = f"⚠️ پیگیری معوق - {student_name}"
            message = f"""
پیگیری برای دانش‌آموز {student_name} که برای تاریخ {followup.next_action_date or 'تعیین نشده'} برنامه‌ریزی شده بود، معوق شده است.

نوع مداخله: {intervention.type_display}
شرح: {followup.description or 'ثبت نشده'}

لطفاً در اسرع وقت پیگیری را انجام دهید.
"""
            
            # ایجاد اعلان با اولویت بالا
            notification = self.create_notification(
                user_id=recipient_id,
                notification_type=Notification.TYPE_OVERDUE,
                title=title,
                message=message.strip(),
                priority=Notification.PRIORITY_HIGH,
                entity_type='followup',
                entity_id=followup.id,
                scheduled_at=utc_now_iso()
            )
            
            self.logger.info(f"اعلان معوق شدن پیگیری {followup.id} ایجاد شد")
            return notification
            
        except Exception as e:
            self.logger.error(f"خطا در ایجاد اعلان معوق: {e}")
            return None
    
    def check_and_create_reminders(self):
        """
        بررسی و ایجاد یادآوری‌های خودکار
        
        این متد باید به صورت دوره‌ای (هر ساعت) اجرا شود
        
        Returns:
            dict: تعداد اعلان‌های ایجاد شده
        """
        try:
            created_count = 0
            overdue_count = 0
            
            # دریافت پیگیری‌های در انتظار
            pending_followups = self.followup_dal.get_pending()
            
            import jdatetime
            today = jdatetime.date.today()
            today_str = f"{today.year}/{today.month:02d}/{today.day:02d}"
            
            for followup in pending_followups:
                # بررسی اینکه آیا برای این پیگیری قبلاً اعلان ایجاد شده است
                existing = self._check_existing_notification(
                    followup.id, 
                    followup.staff_id,
                    Notification.TYPE_REMINDER
                )
                
                if not existing and followup.next_action_date:
                    # بررسی تاریخ اقدام بعدی
                    if followup.next_action_date <= today_str:
                        # معوق شده
                        if self._check_existing_notification(
                            followup.id,
                            followup.staff_id,
                            Notification.TYPE_OVERDUE
                        ):
                            continue
                        self.create_overdue_notification(followup)
                        overdue_count += 1
                        created_count += 1
                    else:
                        # هنوز معوق نشده - ایجاد یادآوری
                        # فقط اگر ۳ روز مانده به تاریخ اقدام باشد
                        try:
                            next_date_parts = followup.next_action_date.split('/')
                            if len(next_date_parts) == 3:
                                next_date = jdatetime.date(
                                    int(next_date_parts[0]),
                                    int(next_date_parts[1]),
                                    int(next_date_parts[2])
                                )
                                days_diff = (next_date - today).days
                                if 1 <= days_diff <= 3:
                                    self.create_reminder_for_followup(followup)
                                    created_count += 1
                        except Exception as _exc:
                            self.logger.debug(
                                f"خطای غیرمنتظره در {self.__class__.__name__}: {_exc}"
                            )
            
            self.logger.info(f"{created_count} یادآوری و {overdue_count} اعلان معوق ایجاد شد")
            
            return {
                'created_count': created_count,
                'overdue_count': overdue_count,
                'total': created_count + overdue_count
            }
            
        except Exception as e:
            self.logger.error(f"خطا در بررسی و ایجاد یادآوری‌ها: {e}")
            return {'created_count': 0, 'overdue_count': 0, 'total': 0}
    
    def _check_existing_notification(self, entity_id, user_id, notification_type):
        """بررسی وجود اعلان قبلی برای یک موجودیت"""
        try:
            notifications = self.notification_dal.get_by_user(user_id, limit=10)
            for notif in notifications:
                if (notif.entity_id == entity_id and 
                    notif.type == notification_type and 
                    notif.entity_type == 'followup' and
                    not notif.is_dismissed):
                    return True
            return False
        except Exception:
            return False
    
    def _enrich_notification(self, notification):
        """افزودن اطلاعات تکمیلی به اعلان"""
        # افزودن نام کاربر
        if notification.user_id:
            try:
                staff = self.staff_dal.get_by_id(notification.user_id)
                if staff:
                    notification.user_name = staff.full_name
            except Exception:
                notification.user_name = "نامشخص"
        
        # افزودن داده‌های مرتبط
        if notification.entity_type == 'followup' and notification.entity_id:
            try:
                followup = self.followup_dal.get_by_id(notification.entity_id)
                if followup:
                    intervention = self.intervention_dal.get_by_id(followup.intervention_id)
                    if intervention:
                        profile = self.profile_dal.get_by_id(intervention.student_profile_id)
                        if profile:
                            student = self.student_dal.get_by_id(profile.student_id)
                            if student:
                                notification.related_data = {
                                    'student_name': student.full_name,
                                    'intervention_type': intervention.type_display,
                                    'followup_date': followup.date,
                                    'next_action_date': followup.next_action_date
                                }
            except Exception as _exc:
                self.logger.debug(
                    f"خطای غیرمنتظره در {self.__class__.__name__}: {_exc}"
                )
    
    def cleanup_old_notifications(self, days=30):
        """پاکسازی اعلان‌های قدیمی"""
        try:
            return self.notification_dal.delete_old(days)
        except Exception as e:
            self.logger.error(f"خطا در پاکسازی اعلان‌های قدیمی: {e}")
            return False