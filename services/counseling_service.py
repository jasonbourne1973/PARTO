"""
سرویس مدیریت جلسات مشاوره
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.counseling_session_dal import CounselingSessionDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.counseling_session import CounselingSession
from services.base_service import BaseService
from utils.error_handler import ServiceError, ValidationError
from utils.logger import get_logger


class CounselingService(BaseService):
    """
    سرویس مدیریت جلسات مشاوره
    
    ویژگی‌ها:
    - ثبت جلسات مشاوره
    - مدیریت وضعیت جلسات
    - دریافت آمار جلسات
    - برنامه‌ریزی جلسات آینده
    """
    
    def __init__(self):
        super().__init__()
        self.session_dal = CounselingSessionDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    def create_session(self, data, user_id=None):
        """ایجاد جلسه مشاوره جدید"""
        def _create():
            # اعتبارسنجی
            self._validate_session_data(data)
            
            # بررسی وجود دانش‌آموز
            profile = self.profile_dal.get_by_id(data.get('student_profile_id'))
            if not profile:
                raise ValidationError("پرونده دانش‌آموز یافت نشد")
            
            # بررسی وجود مشاور
            counselor = self.staff_dal.get_by_id(data.get('counselor_id'))
            if not counselor:
                raise ValidationError("مشاور انتخاب شده وجود ندارد")
            
            # ایجاد مدل
            session = CounselingSession()
            session.student_profile_id = data.get('student_profile_id')
            session.counselor_id = data.get('counselor_id')
            session.referred_by = data.get('referred_by')
            # ===== اصلاح (بازرسی هشتم): یکدست‌سازی قالب تاریخ =====
            session.session_date = self.clean_date(data.get('session_date'))
            session.session_time = self.clean_text(data.get('session_time'), None)
            session.duration_minutes = data.get('duration_minutes')
            session.type = data.get('type', CounselingSession.TYPE_INDIVIDUAL)
            session.method = data.get('method', CounselingSession.METHOD_IN_PERSON)
            session.location = data.get('location')
            session.topic = data.get('topic')
            session.goals = data.get('goals')
            session.summary = data.get('summary')
            session.details = data.get('details')
            session.interventions_discussed = data.get('interventions_discussed')
            session.recommendations = data.get('recommendations')
            session.homework = data.get('homework')
            session.outcome = data.get('outcome')
            session.follow_up_needed = data.get('follow_up_needed', False)
            session.next_session_date = self.clean_date(data.get('next_session_date'))
            session.next_session_notes = data.get('next_session_notes')
            session.status = data.get('status', CounselingSession.STATUS_SCHEDULED)
            
            # اعتبارسنجی مدل
            errors = session.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            # ذخیره
            created = self.session_dal.create(session)
            
            self.logger.info(f"جلسه مشاوره {created.id} برای دانش‌آموز {profile.student_id} ایجاد شد")
            return created
        
        return self.execute_in_transaction(_create)
    
    def update_session(self, session_id, data, user_id=None):
        """به‌روزرسانی جلسه مشاوره"""
        def _update():
            session = self.session_dal.get_by_id(session_id)
            if not session:
                raise ServiceError(f"جلسه با شناسه {session_id} یافت نشد")
            
            self._validate_session_data(data, is_update=True)
            
            # به‌روزرسانی فیلدها
            session.student_profile_id = data.get('student_profile_id', session.student_profile_id)
            session.counselor_id = data.get('counselor_id', session.counselor_id)
            session.referred_by = data.get('referred_by', session.referred_by)
            session.session_date = self.clean_date(
                data.get('session_date'), session.session_date)
            session.session_time = data.get('session_time', session.session_time)
            session.duration_minutes = data.get('duration_minutes', session.duration_minutes)
            session.type = data.get('type', session.type)
            session.method = data.get('method', session.method)
            session.location = data.get('location', session.location)
            session.topic = data.get('topic', session.topic)
            session.goals = data.get('goals', session.goals)
            session.summary = data.get('summary', session.summary)
            session.details = data.get('details', session.details)
            session.interventions_discussed = data.get('interventions_discussed', session.interventions_discussed)
            session.recommendations = data.get('recommendations', session.recommendations)
            session.homework = data.get('homework', session.homework)
            session.outcome = data.get('outcome', session.outcome)
            session.follow_up_needed = data.get('follow_up_needed', session.follow_up_needed)
            session.next_session_date = self.clean_date(
                data.get('next_session_date'), session.next_session_date)
            session.next_session_notes = data.get('next_session_notes', session.next_session_notes)
            session.status = data.get('status', session.status)
            
            errors = session.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            updated = self.session_dal.update(session)
            self.logger.info(f"جلسه مشاوره {session_id} به‌روزرسانی شد")
            return updated
        
        return self.execute_in_transaction(_update)
    
    def get_session(self, session_id):
        """دریافت جلسه با شناسه"""
        session = self.session_dal.get_by_id(session_id)
        if session:
            self._enrich_session(session)
        return session
    
    def get_student_sessions(self, profile_id):
        """دریافت جلسات یک دانش‌آموز"""
        sessions = self.session_dal.get_by_student_profile(profile_id)
        for session in sessions:
            self._enrich_session(session)
        return sessions
    
    def get_counselor_sessions(self, counselor_id):
        """دریافت جلسات یک مشاور"""
        sessions = self.session_dal.get_by_counselor(counselor_id)
        for session in sessions:
            self._enrich_session(session)
        return sessions
    
    def get_upcoming_sessions(self, days=7):
        """دریافت جلسات آینده"""
        sessions = self.session_dal.get_upcoming_sessions(days)
        for session in sessions:
            self._enrich_session(session)
        return sessions
    
    def get_all_sessions(self, status=None, counselor_id=None, include_deleted=False):
        """دریافت همه جلسات مشاوره برای صفحه مدیریت.

        نسخه‌های مختلف DAL ممکن است متد را با نام get_all یا
        get_all_sessions ارائه کنند؛ سرویس هر دو قرارداد را پشتیبانی می‌کند
        تا UI به نام داخلی DAL وابسته نباشد.
        """
        getter = getattr(self.session_dal, "get_all_sessions", None)
        if not callable(getter):
            getter = getattr(self.session_dal, "get_all", None)
        if not callable(getter):
            raise ServiceError("متد دریافت همه جلسات در CounselingSessionDAL وجود ندارد")

        try:
            sessions = getter(include_deleted=include_deleted)
        except TypeError:
            sessions = getter()

        sessions = list(sessions or [])
        if status:
            sessions = [session for session in sessions if getattr(session, "status", None) == status]
        if counselor_id:
            sessions = [
                session for session in sessions
                if getattr(session, "counselor_id", None) == counselor_id
            ]

        for session in sessions:
            self._enrich_session(session)
        return sessions

    def update_session_status(self, session_id, status, user_id=None):
        """به‌روزرسانی وضعیت جلسه"""
        if status not in [s[0] for s in CounselingSession.STATUS_CHOICES]:
            raise ValidationError(f"وضعیت '{status}' نامعتبر است")
        
        result = self.session_dal.update_status(session_id, status)
        self.logger.info(f"وضعیت جلسه {session_id} به {status} تغییر یافت")
        return result
    
    def delete_session(self, session_id, user_id=None):
        """حذف جلسه"""
        result = self.session_dal.delete(session_id, user_id)
        if result:
            self.logger.info(f"جلسه مشاوره {session_id} حذف شد")
        return result
    
    def get_session_stats(self, profile_id):
        """دریافت آمار جلسات یک دانش‌آموز"""
        # ===== اصلاح (بازرسی دوم) =====
        # نسخه قبلی:
        #     student = self.profile_dal.get_by_id(profile_id)
        #     if student:
        #         stats['student_name'] = student.student_name
        #
        # دو اشکال:
        #   ۱) profile_dal یک «پرونده سالانه» (StudentAcademicProfile)
        #      برمی‌گرداند، نه دانش‌آموز. نام متغیر هم گمراه‌کننده بود.
        #   ۲) مدل StudentAcademicProfile صفت student_name ندارد
        #      (فیلدهایش: student_id، academic_year_id، grade، class_name،
        #       status و ...). اجرای واقعی:
        #
        #         AttributeError: 'StudentAcademicProfile' object
        #                         has no attribute 'student_name'
        #
        # یعنی get_session_stats برای هر پرونده‌ای که وجود داشته باشد
        # استثنا می‌داد (فقط وقتی پرونده پیدا نمی‌شد، بی‌صدا کار می‌کرد).
        #
        # حالا دقیقاً همان الگوی درستِ GoalService.get_goal_stats و
        # ExtracurricularService.get_activity_stats استفاده می‌شود:
        # پرونده → student_id → دانش‌آموز → full_name (که property است).
        stats = self.session_dal.get_session_stats(profile_id)
        profile = self.profile_dal.get_by_id(profile_id)
        if profile:
            student = self.student_dal.get_by_id(profile.student_id)
            if student:
                stats['student_name'] = student.full_name
        return stats
    
    def _validate_session_data(self, data, is_update=False):
        """
        اعتبارسنجی داده‌های جلسه

        ===== اصلاح (بازرسی هشتم) =====
        • در حالت ویرایش، فقط کلیدهای ارسالی بررسی می‌شوند (ویرایش
          جزئی دیگر رد نمی‌شود).
        • تاریخ‌ها با تقویم واقعی شمسی اعتبارسنجی می‌شوند، نه با
          نگاه‌کردن به خالی‌بودن.
        """
        errors = []

        def provided(key):
            return (not is_update) or (key in data)

        if not is_update:
            if not data.get('student_profile_id'):
                errors.append("پرونده دانش‌آموز باید انتخاب شود")
            if not data.get('counselor_id'):
                errors.append("مشاور باید انتخاب شود")

        if provided('session_date'):
            _norm, _err = self.check_date(
                data.get('session_date'), "تاریخ جلسه", required=True)
            if _err:
                errors.append(_err)

        if provided('next_session_date'):
            _norm, _err = self.check_date(
                data.get('next_session_date'), "تاریخ جلسهٔ بعدی")
            if _err:
                errors.append(_err)
        
        if data.get('type') and data.get('type') not in [t[0] for t in CounselingSession.TYPE_CHOICES]:
            errors.append("نوع جلسه نامعتبر است")
        
        if data.get('method') and data.get('method') not in [m[0] for m in CounselingSession.METHOD_CHOICES]:
            errors.append("روش جلسه نامعتبر است")
        
        if data.get('status') and data.get('status') not in [s[0] for s in CounselingSession.STATUS_CHOICES]:
            errors.append("وضعیت جلسه نامعتبر است")
        
        if errors:
            raise ValidationError("\n".join(errors))
    
    def _enrich_session(self, session):
        """افزودن اطلاعات تکمیلی به جلسه"""
        # نام دانش‌آموز
        try:
            profile = self.profile_dal.get_by_id(session.student_profile_id)
            if profile:
                student = self.student_dal.get_by_id(profile.student_id)
                if student:
                    session.student_name = student.full_name
        except Exception:
            session.student_name = "نامشخص"
        
        # نام مشاور
        try:
            counselor = self.staff_dal.get_by_id(session.counselor_id)
            if counselor:
                session.counselor_name = counselor.full_name
        except Exception:
            session.counselor_name = "نامشخص"
        
        # نام معرف
        if session.referred_by:
            try:
                referred = self.staff_dal.get_by_id(session.referred_by)
                if referred:
                    session.referred_by_name = referred.full_name
            except Exception:
                session.referred_by_name = "نامشخص"