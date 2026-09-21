"""
سرویس مدیریت فعالیت‌های فوق‌برنامه
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.extracurricular_dal import ExtracurricularDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.extracurricular_activity import ExtracurricularActivity
from services.base_service import BaseService
from utils.error_handler import ServiceError, ValidationError
from utils.logger import get_logger


class ExtracurricularService(BaseService):
    """
    سرویس مدیریت فعالیت‌های فوق‌برنامه
    
    ویژگی‌ها:
    - ثبت فعالیت‌های مختلف
    - مدیریت وضعیت فعالیت‌ها
    - دریافت آمار فعالیت‌ها
    - گزارش‌گیری از فعالیت‌ها
    """
    
    def __init__(self):
        super().__init__()
        self.activity_dal = ExtracurricularDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    def create_activity(self, data, user_id=None):
        """ایجاد فعالیت جدید"""
        def _create():
            self._validate_activity_data(data)
            
            profile = self.profile_dal.get_by_id(data.get('student_profile_id'))
            if not profile:
                raise ValidationError("پرونده دانش‌آموز یافت نشد")
            
            activity = ExtracurricularActivity()
            activity.student_profile_id = data.get('student_profile_id')
            activity.teacher_id = data.get('teacher_id')
            activity.title = data.get('title')
            activity.type = data.get('type')
            activity.description = data.get('description')
            activity.start_date = self.clean_date(data.get('start_date'))
            activity.end_date = self.clean_date(data.get('end_date'))
            activity.duration_hours = data.get('duration_hours')
            activity.location = data.get('location')
            activity.participation_level = data.get('participation_level', ExtracurricularActivity.LEVEL_PARTICIPANT)
            activity.role = data.get('role')
            activity.team_name = data.get('team_name')
            activity.result = data.get('result')
            activity.achievements = data.get('achievements')
            activity.feedback = data.get('feedback')
            activity.status = data.get('status', ExtracurricularActivity.STATUS_PLANNED)
            
            errors = activity.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            created = self.activity_dal.create(activity)
            self.logger.info(f"فعالیت {created.title} برای دانش‌آموز {profile.student_id} ایجاد شد")
            return created
        
        return self.execute_in_transaction(_create)
    
    def update_activity(self, activity_id, data, user_id=None):
        """به‌روزرسانی فعالیت"""
        def _update():
            activity = self.activity_dal.get_by_id(activity_id)
            if not activity:
                raise ServiceError(f"فعالیت با شناسه {activity_id} یافت نشد")
            
            self._validate_activity_data(data, is_update=True)
            
            activity.student_profile_id = data.get('student_profile_id', activity.student_profile_id)
            activity.teacher_id = data.get('teacher_id', activity.teacher_id)
            activity.title = data.get('title', activity.title)
            activity.type = data.get('type', activity.type)
            activity.description = data.get('description', activity.description)
            activity.start_date = self.clean_date(
                data.get('start_date'), activity.start_date)
            activity.end_date = self.clean_date(data.get('end_date'), activity.end_date)
            activity.duration_hours = data.get('duration_hours', activity.duration_hours)
            activity.location = data.get('location', activity.location)
            activity.participation_level = data.get('participation_level', activity.participation_level)
            activity.role = data.get('role', activity.role)
            activity.team_name = data.get('team_name', activity.team_name)
            activity.result = data.get('result', activity.result)
            activity.achievements = data.get('achievements', activity.achievements)
            activity.feedback = data.get('feedback', activity.feedback)
            activity.status = data.get('status', activity.status)
            
            errors = activity.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            updated = self.activity_dal.update(activity)
            self.logger.info(f"فعالیت {activity_id} به‌روزرسانی شد")
            return updated
        
        return self.execute_in_transaction(_update)
    
    def get_activity(self, activity_id):
        """دریافت فعالیت با شناسه"""
        activity = self.activity_dal.get_by_id(activity_id)
        if activity:
            self._enrich_activity(activity)
        return activity
    
    def get_student_activities(self, profile_id, include_completed=True):
        """دریافت فعالیت‌های یک دانش‌آموز"""
        activities = self.activity_dal.get_by_student_profile(profile_id)
        if not include_completed:
            activities = [a for a in activities if a.status != ExtracurricularActivity.STATUS_COMPLETED]
        for activity in activities:
            self._enrich_activity(activity)
        return activities
    
    def get_activities_by_type(self, activity_type):
        """دریافت فعالیت‌ها بر اساس نوع"""
        activities = self.activity_dal.get_by_type(activity_type)
        for activity in activities:
            self._enrich_activity(activity)
        return activities
    
    def get_teacher_activities(self, teacher_id):
        """دریافت فعالیت‌های یک معلم"""
        activities = self.activity_dal.get_by_teacher(teacher_id)
        for activity in activities:
            self._enrich_activity(activity)
        return activities
    
    def get_active_activities(self, profile_id):
        """دریافت فعالیت‌های فعال یک دانش‌آموز"""
        activities = self.activity_dal.get_by_student_profile(profile_id)
        active = [a for a in activities if a.is_active]
        for activity in active:
            self._enrich_activity(activity)
        return active
    
    def get_all_activities(self, status=None, activity_type=None, include_completed=True):
        """دریافت همه فعالیت‌های فوق‌برنامه برای صفحه مدیریت."""
        getter = getattr(self.activity_dal, "get_all_activities", None)
        if not callable(getter):
            getter = getattr(self.activity_dal, "get_all", None)
        if not callable(getter):
            raise ServiceError("متد دریافت همه فعالیت‌ها در ExtracurricularDAL وجود ندارد")

        try:
            activities = getter()
        except TypeError as _exc:
            self.logger.debug(f"خطای مدیریت‌شده در get_all_activities (مسیر جایگزین): {_exc}")
            activities = getter(include_deleted=False)

        activities = list(activities or [])
        if not include_completed:
            activities = [
                activity for activity in activities
                if getattr(activity, "status", None) != ExtracurricularActivity.STATUS_COMPLETED
            ]
        if status:
            activities = [activity for activity in activities if getattr(activity, "status", None) == status]
        if activity_type:
            activities = [activity for activity in activities if getattr(activity, "type", None) == activity_type]

        for activity in activities:
            self._enrich_activity(activity)
        return activities

    def update_activity_status(self, activity_id, status, user_id=None):
        """به‌روزرسانی وضعیت فعالیت"""
        if status not in [s[0] for s in ExtracurricularActivity.STATUS_CHOICES]:
            raise ValidationError(f"وضعیت '{status}' نامعتبر است")
        
        result = self.activity_dal.update_status(activity_id, status)
        self.logger.info(f"وضعیت فعالیت {activity_id} به {status} تغییر یافت")
        return result
    
    def complete_activity(self, activity_id, result=None, achievements=None, user_id=None):
        """تکمیل فعالیت"""
        activity = self.activity_dal.get_by_id(activity_id)
        if not activity:
            raise ServiceError(f"فعالیت با شناسه {activity_id} یافت نشد")
        
        activity.complete(result, achievements)
        updated = self.activity_dal.update(activity)
        self.logger.info(f"فعالیت {activity_id} تکمیل شد")
        return updated
    
    def delete_activity(self, activity_id, user_id=None):
        """حذف فعالیت"""
        result = self.activity_dal.delete(activity_id, user_id)
        if result:
            self.logger.info(f"فعالیت {activity_id} حذف شد")
        return result
    
    def get_activity_stats(self, profile_id):
        """دریافت آمار فعالیت‌های یک دانش‌آموز"""
        stats = self.activity_dal.get_activity_stats(profile_id)
        profile = self.profile_dal.get_by_id(profile_id)
        if profile:
            student = self.student_dal.get_by_id(profile.student_id)
            if student:
                stats['student_name'] = student.full_name
        return stats
    
    def get_activity_types_summary(self):
        """دریافت خلاصه انواع فعالیت‌ها"""
        all_activities = self.activity_dal.get_all()
        
        summary = {}
        for activity in all_activities:
            type_display = activity.type_display
            if type_display not in summary:
                summary[type_display] = {
                    'total': 0,
                    'completed': 0,
                    'planned': 0,
                    'in_progress': 0
                }
            summary[type_display]['total'] += 1
            if activity.status == ExtracurricularActivity.STATUS_COMPLETED:
                summary[type_display]['completed'] += 1
            elif activity.status == ExtracurricularActivity.STATUS_PLANNED:
                summary[type_display]['planned'] += 1
            elif activity.status == ExtracurricularActivity.STATUS_IN_PROGRESS:
                summary[type_display]['in_progress'] += 1
        
        return summary
    
    def _validate_activity_data(self, data, is_update=False):
        """اعتبارسنجی داده‌های فعالیت"""
        errors = []
        
        if not is_update and not data.get('student_profile_id'):
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        
        title = self.clean_text(data.get('title'))
        if not title:
            errors.append("عنوان فعالیت نمی‌تواند خالی باشد")
        elif len(title) < 2:
            errors.append("عنوان فعالیت باید حداقل ۲ کاراکتر باشد")
        
        if not data.get('type'):
            errors.append("نوع فعالیت باید انتخاب شود")
        elif data.get('type') and data.get('type') not in [t[0] for t in ExtracurricularActivity.TYPE_CHOICES]:
            errors.append("نوع فعالیت نامعتبر است")
        
        # ===== اصلاح (بازرسی هشتم): اعتبارسنجی واقعی تاریخ‌ها =====
        start_date, err = self.check_date(
            data.get('start_date'), "تاریخ شروع", required=True)
        if err:
            errors.append(err)

        end_date, err = self.check_date(data.get('end_date'), "تاریخ پایان")
        if err:
            errors.append(err)

        if start_date and end_date and end_date < start_date:
            # مقایسهٔ رشته‌ای فقط وقتی معتبر است که قالب یکدست
            # (yyyy/MM/dd با صفر ابتدایی) باشد — و همین است.
            errors.append("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد")
        
        if data.get('participation_level') and data.get('participation_level') not in [l[0] for l in ExtracurricularActivity.LEVEL_CHOICES]:
            errors.append("سطح مشارکت نامعتبر است")
        
        if data.get('status') and data.get('status') not in [s[0] for s in ExtracurricularActivity.STATUS_CHOICES]:
            errors.append("وضعیت فعالیت نامعتبر است")
        
        if errors:
            raise ValidationError("\n".join(errors))
    
    def _enrich_activity(self, activity):
        """افزودن اطلاعات تکمیلی به فعالیت"""
        # نام دانش‌آموز
        try:
            profile = self.profile_dal.get_by_id(activity.student_profile_id)
            if profile:
                student = self.student_dal.get_by_id(profile.student_id)
                if student:
                    activity.student_name = student.full_name
        except Exception as _exc:
            self.logger.debug(f"خطای مدیریت‌شده در _enrich_activity (مسیر جایگزین): {_exc}")
            activity.student_name = "نامشخص"
        
        # نام معلم
        if activity.teacher_id:
            try:
                teacher = self.staff_dal.get_by_id(activity.teacher_id)
                if teacher:
                    activity.teacher_name = teacher.full_name
            except Exception as _exc:
                self.logger.debug(f"خطای مدیریت‌شده در _enrich_activity (مسیر جایگزین): {_exc}")
                activity.teacher_name = "نامشخص"