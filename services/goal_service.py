"""
سرویس مدیریت اهداف فردی دانش‌آموزان
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.competency_dal import CompetencyDAL
from dal.goal_dal import GoalDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.individual_goal import IndividualGoal
from services.base_service import BaseService
from utils.error_handler import ServiceError, ValidationError
from utils.logger import get_logger


class GoalService(BaseService):
    """
    سرویس مدیریت اهداف فردی
    
    ویژگی‌ها:
    - تعیین اهداف شخصی‌سازی‌شده
    - پیگیری پیشرفت اهداف
    - مدیریت وضعیت اهداف
    - ارتباط با شایستگی‌ها و مداخلات
    """
    
    def __init__(self):
        super().__init__()
        self.goal_dal = GoalDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.competency_dal = CompetencyDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    def create_goal(self, data, user_id=None):
        """ایجاد هدف جدید"""
        def _create():
            self._validate_goal_data(data)
            
            profile = self.profile_dal.get_by_id(data.get('student_profile_id'))
            if not profile:
                raise ValidationError("پرونده دانش‌آموز یافت نشد")
            
            goal = IndividualGoal()
            goal.student_profile_id = data.get('student_profile_id')
            goal.created_by = user_id
            goal.assigned_to = data.get('assigned_to')
            goal.related_competency_id = data.get('related_competency_id')
            goal.related_intervention_id = data.get('related_intervention_id')
            goal.title = data.get('title')
            goal.description = data.get('description')
            goal.domain = data.get('domain', IndividualGoal.DOMAIN_OTHER)
            goal.priority = data.get('priority', IndividualGoal.PRIORITY_MEDIUM)
            goal.success_criteria = data.get('success_criteria')
            goal.target_date = self.clean_date(data.get('target_date'))
            goal.start_date = self.clean_date(data.get('start_date'))
            goal.end_date = self.clean_date(data.get('end_date'))
            goal.progress_percent = max(0, min(100, data.get('progress_percent', 0) or 0))
            goal.progress_notes = data.get('progress_notes')
            goal.result = data.get('result')
            goal.status = data.get('status', IndividualGoal.STATUS_DRAFT)
            
            errors = goal.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            created = self.goal_dal.create(goal)
            self.logger.info(f"هدف {created.title} برای دانش‌آموز {profile.student_id} ایجاد شد")
            return created
        
        return self.execute_in_transaction(_create)
    
    def update_goal(self, goal_id, data, user_id=None):
        """به‌روزرسانی هدف"""
        def _update():
            goal = self.goal_dal.get_by_id(goal_id)
            if not goal:
                raise ServiceError(f"هدف با شناسه {goal_id} یافت نشد")
            
            self._validate_goal_data(data, is_update=True)
            
            goal.student_profile_id = data.get('student_profile_id', goal.student_profile_id)
            goal.assigned_to = data.get('assigned_to', goal.assigned_to)
            goal.related_competency_id = data.get('related_competency_id', goal.related_competency_id)
            goal.related_intervention_id = data.get('related_intervention_id', goal.related_intervention_id)
            goal.title = data.get('title', goal.title)
            goal.description = data.get('description', goal.description)
            goal.domain = data.get('domain', goal.domain)
            goal.priority = data.get('priority', goal.priority)
            goal.success_criteria = data.get('success_criteria', goal.success_criteria)
            goal.target_date = self.clean_date(
                data.get('target_date'), goal.target_date)
            goal.start_date = self.clean_date(data.get('start_date'), goal.start_date)
            goal.end_date = self.clean_date(data.get('end_date'), goal.end_date)
            if 'progress_percent' in data:
                goal.progress_percent = max(
                    0, min(100, data.get('progress_percent') or 0)
                )
            if 'progress_notes' in data:
                goal.progress_notes = data.get('progress_notes')
            if 'result' in data:
                goal.result = data.get('result')
            goal.status = data.get('status', goal.status)
            
            errors = goal.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            updated = self.goal_dal.update(goal)
            self.logger.info(f"هدف {goal_id} به‌روزرسانی شد")
            return updated
        
        return self.execute_in_transaction(_update)
    
    def get_goal(self, goal_id):
        """دریافت هدف با شناسه"""
        goal = self.goal_dal.get_by_id(goal_id)
        if goal:
            self._enrich_goal(goal)
        return goal
    
    def get_student_goals(self, profile_id, include_achieved=True):
        """دریافت اهداف یک دانش‌آموز"""
        if include_achieved:
            goals = self.goal_dal.get_by_student_profile(profile_id)
        else:
            goals = self.goal_dal.get_active_goals(profile_id)
        
        for goal in goals:
            self._enrich_goal(goal)
        return goals
    
    def get_active_goals(self, profile_id):
        """دریافت اهداف فعال یک دانش‌آموز"""
        goals = self.goal_dal.get_active_goals(profile_id)
        for goal in goals:
            self._enrich_goal(goal)
        return goals
    
    def get_achieved_goals(self, profile_id):
        """دریافت اهداف محقق‌شده یک دانش‌آموز"""
        goals = self.goal_dal.get_achieved_goals(profile_id)
        for goal in goals:
            self._enrich_goal(goal)
        return goals
    
    def get_all_goals(self, status=None, domain=None, assigned_to=None, include_achieved=True):
        """دریافت همه اهداف فردی برای صفحه مدیریت."""
        getter = getattr(self.goal_dal, "get_all_goals", None)
        if not callable(getter):
            getter = getattr(self.goal_dal, "get_all", None)
        if not callable(getter):
            raise ServiceError("متد دریافت همه اهداف در GoalDAL وجود ندارد")

        try:
            goals = getter()
        except TypeError as _exc:
            self.logger.debug(f"خطای مدیریت‌شده در get_all_goals (مسیر جایگزین): {_exc}")
            goals = getter(include_deleted=False)

        goals = list(goals or [])
        if not include_achieved:
            achieved_statuses = {
                IndividualGoal.STATUS_ACHIEVED,
                IndividualGoal.STATUS_COMPLETED,
            }
            goals = [
                goal for goal in goals
                if getattr(goal, "status", None) not in achieved_statuses
            ]
        if status:
            goals = [goal for goal in goals if getattr(goal, "status", None) == status]
        if domain:
            goals = [goal for goal in goals if getattr(goal, "domain", None) == domain]
        if assigned_to:
            goals = [goal for goal in goals if getattr(goal, "assigned_to", None) == assigned_to]

        for goal in goals:
            self._enrich_goal(goal)
        return goals

    def update_goal_progress(self, goal_id, progress_percent, notes=None, user_id=None):
        """به‌روزرسانی پیشرفت هدف"""
        goal = self.goal_dal.get_by_id(goal_id)
        if not goal:
            raise ServiceError(f"هدف با شناسه {goal_id} یافت نشد")
        
        progress_percent = max(0, min(100, progress_percent))
        result = self.goal_dal.update_progress(goal_id, progress_percent, notes)
        
        self.logger.info(f"پیشرفت هدف {goal_id} به {progress_percent}% به‌روزرسانی شد")
        return result
    
    def update_goal_status(self, goal_id, status, user_id=None):
        """به‌روزرسانی وضعیت هدف"""
        if status not in [s[0] for s in IndividualGoal.STATUS_CHOICES]:
            raise ValidationError(f"وضعیت '{status}' نامعتبر است")
        
        # اگر وضعیت به محقق‌شده تغییر کرد، پیشرفت را ۱۰۰% تنظیم کن
        if status in [IndividualGoal.STATUS_ACHIEVED, IndividualGoal.STATUS_COMPLETED]:
            self.goal_dal.update_progress(goal_id, 100)
        
        result = self.goal_dal.update_status(goal_id, status)
        self.logger.info(f"وضعیت هدف {goal_id} به {status} تغییر یافت")
        return result
    
    def achieve_goal(self, goal_id, result=None, user_id=None):
        """ثبت دستیابی به هدف"""
        goal = self.goal_dal.get_by_id(goal_id)
        if not goal:
            raise ServiceError(f"هدف با شناسه {goal_id} یافت نشد")
        
        goal.achieve(result)
        updated = self.goal_dal.update(goal)
        self.logger.info(f"هدف {goal_id} محقق شد")
        return updated
    
    def delete_goal(self, goal_id, user_id=None):
        """حذف هدف"""
        result = self.goal_dal.delete(goal_id, user_id)
        if result:
            self.logger.info(f"هدف {goal_id} حذف شد")
        return result
    
    def get_goal_stats(self, profile_id):
        """دریافت آمار اهداف یک دانش‌آموز"""
        stats = self.goal_dal.get_goal_stats(profile_id)
        profile = self.profile_dal.get_by_id(profile_id)
        if profile:
            student = self.student_dal.get_by_id(profile.student_id)
            if student:
                stats['student_name'] = student.full_name
        return stats
    
    def get_goals_by_domain(self, profile_id, domain):
        """دریافت اهداف بر اساس حوزه"""
        all_goals = self.goal_dal.get_by_student_profile(profile_id)
        return [g for g in all_goals if g.domain == domain]
    
    def _validate_goal_data(self, data, is_update=False):
        """اعتبارسنجی داده‌های هدف"""
        errors = []
        
        if not is_update and not data.get('student_profile_id'):
            errors.append("پرونده دانش‌آموز باید انتخاب شود")
        
        title = self.clean_text(data.get('title'))
        if not title:
            errors.append("عنوان هدف نمی‌تواند خالی باشد")
        elif len(title) < 2:
            errors.append("عنوان هدف باید حداقل ۲ کاراکتر باشد")

        # ===== اصلاح (بازرسی هشتم): اعتبارسنجی واقعی تاریخ‌ها =====
        start_date, err = self.check_date(data.get('start_date'), "تاریخ شروع")
        if err:
            errors.append(err)
        _, err = self.check_date(data.get('target_date'), "تاریخ هدف")
        if err:
            errors.append(err)
        end_date, err = self.check_date(data.get('end_date'), "تاریخ پایان")
        if err:
            errors.append(err)

        if start_date and end_date and end_date < start_date:
            errors.append("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد")
        
        if data.get('priority') and data.get('priority') not in [p[0] for p in IndividualGoal.PRIORITY_CHOICES]:
            errors.append("اولویت هدف نامعتبر است")
        
        if data.get('domain') and data.get('domain') not in [d[0] for d in IndividualGoal.DOMAIN_CHOICES]:
            errors.append("حوزه هدف نامعتبر است")
        
        if data.get('status') and data.get('status') not in [s[0] for s in IndividualGoal.STATUS_CHOICES]:
            errors.append("وضعیت هدف نامعتبر است")
        
        if data.get('progress_percent') and (data.get('progress_percent') < 0 or data.get('progress_percent') > 100):
            errors.append("درصد پیشرفت باید بین 0 تا 100 باشد")
        
        if errors:
            raise ValidationError("\n".join(errors))
    
    def _enrich_goal(self, goal):
        """افزودن اطلاعات تکمیلی به هدف"""
        # نام دانش‌آموز
        try:
            profile = self.profile_dal.get_by_id(goal.student_profile_id)
            if profile:
                student = self.student_dal.get_by_id(profile.student_id)
                if student:
                    goal.student_name = student.full_name
        except Exception as _exc:
            self.logger.debug(f"خطای مدیریت‌شده در _enrich_goal (مسیر جایگزین): {_exc}")
            goal.student_name = "نامشخص"
        
        # نام ایجادکننده
        if goal.created_by:
            try:
                creator = self.staff_dal.get_by_id(goal.created_by)
                if creator:
                    goal.created_by_name = creator.full_name
            except Exception as _exc:
                self.logger.debug(f"خطای مدیریت‌شده در _enrich_goal (مسیر جایگزین): {_exc}")
                goal.created_by_name = "نامشخص"
        
        # نام مسئول
        if goal.assigned_to:
            try:
                assignee = self.staff_dal.get_by_id(goal.assigned_to)
                if assignee:
                    goal.assigned_to_name = assignee.full_name
            except Exception as _exc:
                self.logger.debug(f"خطای مدیریت‌شده در _enrich_goal (مسیر جایگزین): {_exc}")
                goal.assigned_to_name = "نامشخص"
        
        # نام شایستگی
        if goal.related_competency_id:
            try:
                comp = self.competency_dal.get_by_id(goal.related_competency_id)
                if comp:
                    goal.competency_name = comp.title
            except Exception as _exc:
                self.logger.debug(f"خطای مدیریت‌شده در _enrich_goal (مسیر جایگزین): {_exc}")
                goal.competency_name = "نامشخص"