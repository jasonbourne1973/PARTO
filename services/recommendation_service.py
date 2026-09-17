"""
سرویس پیشنهاددهی هوشمند - تولید پیشنهادات شخصی‌سازی‌شده برای دانش‌آموزان
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_service import BaseService
from dal.observation_dal import ObservationDAL
from dal.intervention_dal import InterventionDAL
from dal.followup_dal import FollowUpDAL
from dal.competency_dal import CompetencyDAL
from dal.recommendation_dal import RecommendationDAL
from dal.student_dal import StudentDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.staff_dal import StaffDAL
from models.recommendation_rules import RuleManager, RecommendationResult, RulePriority, RecommendationCategory
from models.recommendation import Recommendation
from utils.logger import get_logger
from utils.error_handler import ServiceError
import jdatetime


class RecommendationService(BaseService):
    """
    سرویس پیشنهاددهی هوشمند
    
    ویژگی‌ها:
    - تولید پیشنهادات شخصی‌سازی‌شده برای هر دانش‌آموز
    - تحلیل داده‌های موجود (مشاهدات، مداخلات، پیگیری‌ها)
    - اولویت‌بندی پیشنهادات بر اساس اهمیت
    - ذخیره و مدیریت پیشنهادات
    - پیگیری اجرای پیشنهادات
    """
    
    def __init__(self):
        super().__init__()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.competency_dal = CompetencyDAL()
        self.recommendation_dal = RecommendationDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.rule_manager = RuleManager()
        self.logger = get_logger(self.__class__.__name__)
    
    def generate_recommendations(self, profile_id, staff_id=None):
        """
        تولید پیشنهادات برای یک دانش‌آموز
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
            staff_id: شناسه کاربر درخواست‌دهنده (اختیاری)
        
        Returns:
            list: لیست پیشنهادات تولیدشده
        """
        try:
            # دریافت اطلاعات دانش‌آموز
            profile = self.profile_dal.get_by_id(profile_id)
            if not profile:
                raise ServiceError(f"پرونده با شناسه {profile_id} یافت نشد.")
            
            student = self.student_dal.get_by_id(profile.student_id)
            if not student:
                raise ServiceError(f"دانش‌آموز با شناسه {profile.student_id} یافت نشد.")
            
            # جمع‌آوری داده‌های مورد نیاز
            data = self._collect_student_data(profile_id)
            
            # ارزیابی قوانین
            results = self.rule_manager.evaluate_rules(data)
            
            if not results:
                self.logger.info(f"هیچ پیشنهادی برای دانش‌آموز {student.full_name} تولید نشد.")
                return []
            
            # ذخیره پیشنهادات در دیتابیس
            saved_recommendations = []
            for result in results[:5]:  # حداکثر ۵ پیشنهاد
                recommendation = self._save_recommendation(profile_id, staff_id, result)
                if recommendation:
                    saved_recommendations.append(recommendation)
            
            self.logger.info(f"{len(saved_recommendations)} پیشنهاد برای دانش‌آموز {student.full_name} تولید شد.")
            return saved_recommendations
            
        except Exception as e:
            self.logger.error(f"خطا در تولید پیشنهادات: {e}")
            raise ServiceError(f"خطا در تولید پیشنهادات: {str(e)}")
    
    def _collect_student_data(self, profile_id):
        """
        جمع‌آوری داده‌های مورد نیاز برای تحلیل
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
        
        Returns:
            dict: داده‌های جمع‌آوری‌شده
        """
        try:
            # دریافت مشاهدات
            observations = self.observation_dal.get_by_student_profile(profile_id)
            
            # دریافت مداخلات
            interventions = self.intervention_dal.get_by_student_profile(profile_id)
            
            # دریافت پیگیری‌ها
            followups = self.followup_dal.get_by_student_profile(profile_id)
            
            # تحلیل شایستگی‌ها
            weak_comps = self.observation_dal.get_weak_competencies_for_student(profile_id)
            strong_comps = self.observation_dal.get_strong_competencies_for_student(profile_id)
            
            # الگوهای رفتاری
            patterns = self.observation_dal.get_observation_patterns_for_student(profile_id)
            
            # آمار مداخلات
            successful_interventions = [i for i in interventions if i.status in ['completed', 'done']]
            cancelled_interventions = [i for i in interventions if i.status == 'cancelled']
            
            # آمار پیگیری‌ها
            pending_followups = [f for f in followups if f.status == 'pending']
            overdue_followups = self._get_overdue_followups(followups)
            
            # مداخلات بدون پیگیری
            interventions_with_followup = set()
            for f in followups:
                if f.intervention_id:
                    interventions_with_followup.add(f.intervention_id)
            interventions_without_followup = [i for i in interventions if i.id not in interventions_with_followup]
            
            # شایستگی‌های بدون مشاهده
            all_competencies = self.competency_dal.get_all(include_inactive=False)
            observed_comp_ids = set(o.competency_id for o in observations if o.competency_id)
            unobserved_competencies = [c for c in all_competencies if c.id not in observed_comp_ids]
            
            # محاسبه نسبت‌ها
            total_obs = len(observations)
            positive_count = sum(1 for o in observations if o.behavior_type == 'مثبت')
            negative_count = sum(1 for o in observations if o.behavior_type == 'منفی')
            
            positive_ratio = round(positive_count / total_obs * 100, 1) if total_obs > 0 else 0
            negative_ratio = round(negative_count / total_obs * 100, 1) if total_obs > 0 else 0
            
            return {
                'student_profile_id': profile_id,
                'observations': observations,
                'interventions': interventions,
                'followups': followups,
                'weak_competencies': weak_comps,
                'strong_competencies': strong_comps,
                'patterns': patterns,
                'total_observations': total_obs,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'positive_ratio': positive_ratio,
                'negative_ratio': negative_ratio,
                'successful_interventions': len(successful_interventions),
                'cancelled_interventions': len(cancelled_interventions),
                'pending_followups': len(pending_followups),
                'overdue_followups': len(overdue_followups),
                'interventions_without_followup': len(interventions_without_followup),
                'unobserved_competencies': len(unobserved_competencies),
                'has_data': total_obs > 0
            }
            
        except Exception as e:
            self.logger.error(f"خطا در جمع‌آوری داده‌ها: {e}")
            return {
                'student_profile_id': profile_id,
                'observations': [],
                'interventions': [],
                'followups': [],
                'weak_competencies': [],
                'strong_competencies': [],
                'patterns': {},
                'total_observations': 0,
                'positive_count': 0,
                'negative_count': 0,
                'positive_ratio': 0,
                'negative_ratio': 0,
                'successful_interventions': 0,
                'cancelled_interventions': 0,
                'pending_followups': 0,
                'overdue_followups': 0,
                'interventions_without_followup': 0,
                'unobserved_competencies': 0,
                'has_data': False
            }
    
    def _get_overdue_followups(self, followups):
        """دریافت پیگیری‌های معوق"""
        try:
            today = jdatetime.date.today()
            today_str = f"{today.year}/{today.month:02d}/{today.day:02d}"
            
            overdue = []
            for f in followups:
                if f.status == 'pending' and f.next_action_date and f.next_action_date < today_str:
                    overdue.append(f)
            return overdue
        except:
            return []
    
    def _save_recommendation(self, profile_id, staff_id, result):
        """
        ذخیره پیشنهاد در دیتابیس
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
            staff_id: شناسه کاربر
            result: نتیجه پیشنهاددهی
        
        Returns:
            Recommendation: پیشنهاد ذخیره‌شده
        """
        try:
            recommendation = Recommendation()
            recommendation.student_profile_id = profile_id
            recommendation.staff_id = staff_id
            recommendation.rule_id = result.rule_id
            recommendation.category = result.category.value
            recommendation.priority = result.priority.name.lower()
            recommendation.title = result.title
            recommendation.description = result.description
            recommendation.suggested_action = result.suggested_action
            recommendation.suggested_intervention_type = result.suggested_intervention_type
            recommendation.related_competency_id = result.related_competency_id
            recommendation.related_observation_ids = result.related_observation_ids
            recommendation.score = result.score
            recommendation.metadata = result.metadata
            recommendation.status = Recommendation.STATUS_PENDING
            
            return self.recommendation_dal.create(recommendation)
            
        except Exception as e:
            self.logger.error(f"خطا در ذخیره پیشنهاد: {e}")
            return None
    
    def get_recommendations_for_student(self, profile_id, limit=None):
        """
        دریافت پیشنهادات یک دانش‌آموز
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
            limit: تعداد محدود
        
        Returns:
            list: لیست پیشنهادات
        """
        try:
            recommendations = self.recommendation_dal.get_by_student_profile(profile_id)
            
            # افزودن اطلاعات تکمیلی
            for rec in recommendations[:limit] if limit else recommendations:
                self._enrich_recommendation(rec)
            
            return recommendations[:limit] if limit else recommendations
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیشنهادات: {e}")
            return []
    
    def get_active_recommendations(self, profile_id):
        """
        دریافت پیشنهادات فعال یک دانش‌آموز
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
        
        Returns:
            list: لیست پیشنهادات فعال
        """
        try:
            recommendations = self.recommendation_dal.get_by_student_profile(profile_id)
            active = [r for r in recommendations if r.is_pending]
            
            for rec in active:
                self._enrich_recommendation(rec)
            
            return active
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیشنهادات فعال: {e}")
            return []
    
    def accept_recommendation(self, recommendation_id, staff_id=None):
        """
        پذیرش پیشنهاد
        
        Args:
            recommendation_id: شناسه پیشنهاد
            staff_id: شناسه کاربر
        
        Returns:
            bool: آیا عملیات موفق بود؟
        """
        try:
            recommendation = self.recommendation_dal.get_by_id(recommendation_id)
            if not recommendation:
                raise ServiceError(f"پیشنهاد با شناسه {recommendation_id} یافت نشد.")
            
            recommendation.accept()
            self.recommendation_dal.update(recommendation)
            
            self.logger.info(f"پیشنهاد {recommendation_id} پذیرفته شد.")
            return True
            
        except Exception as e:
            self.logger.error(f"خطا در پذیرش پیشنهاد: {e}")
            raise ServiceError(f"خطا: {str(e)}")
    
    def reject_recommendation(self, recommendation_id, notes=None, staff_id=None):
        """
        رد پیشنهاد
        
        Args:
            recommendation_id: شناسه پیشنهاد
            notes: یادداشت رد
            staff_id: شناسه کاربر
        
        Returns:
            bool: آیا عملیات موفق بود؟
        """
        try:
            recommendation = self.recommendation_dal.get_by_id(recommendation_id)
            if not recommendation:
                raise ServiceError(f"پیشنهاد با شناسه {recommendation_id} یافت نشد.")
            
            recommendation.reject(notes)
            self.recommendation_dal.update(recommendation)
            
            self.logger.info(f"پیشنهاد {recommendation_id} رد شد.")
            return True
            
        except Exception as e:
            self.logger.error(f"خطا در رد پیشنهاد: {e}")
            raise ServiceError(f"خطا: {str(e)}")
    
    def implement_recommendation(self, recommendation_id, staff_id=None):
        """
        اجرای پیشنهاد
        
        Args:
            recommendation_id: شناسه پیشنهاد
            staff_id: شناسه کاربر
        
        Returns:
            bool: آیا عملیات موفق بود؟
        """
        try:
            recommendation = self.recommendation_dal.get_by_id(recommendation_id)
            if not recommendation:
                raise ServiceError(f"پیشنهاد با شناسه {recommendation_id} یافت نشد.")
            
            recommendation.implement()
            self.recommendation_dal.update(recommendation)
            
            self.logger.info(f"پیشنهاد {recommendation_id} اجرا شد.")
            return True
            
        except Exception as e:
            self.logger.error(f"خطا در اجرای پیشنهاد: {e}")
            raise ServiceError(f"خطا: {str(e)}")
    
    def complete_recommendation(self, recommendation_id, feedback=None, staff_id=None):
        """
        تکمیل پیشنهاد
        
        Args:
            recommendation_id: شناسه پیشنهاد
            feedback: بازخورد
            staff_id: شناسه کاربر
        
        Returns:
            bool: آیا عملیات موفق بود؟
        """
        try:
            recommendation = self.recommendation_dal.get_by_id(recommendation_id)
            if not recommendation:
                raise ServiceError(f"پیشنهاد با شناسه {recommendation_id} یافت نشد.")
            
            recommendation.complete(feedback)
            self.recommendation_dal.update(recommendation)
            
            self.logger.info(f"پیشنهاد {recommendation_id} تکمیل شد.")
            return True
            
        except Exception as e:
            self.logger.error(f"خطا در تکمیل پیشنهاد: {e}")
            raise ServiceError(f"خطا: {str(e)}")
    
    def _enrich_recommendation(self, recommendation):
        """افزودن اطلاعات تکمیلی به پیشنهاد"""
        # افزودن نام دانش‌آموز
        try:
            profile = self.profile_dal.get_by_id(recommendation.student_profile_id)
            if profile:
                student = self.student_dal.get_by_id(profile.student_id)
                if student:
                    recommendation.student_name = student.full_name
        except:
            recommendation.student_name = "نامشخص"
        
        # افزودن نام مسئول
        if recommendation.staff_id:
            try:
                staff = self.staff_dal.get_by_id(recommendation.staff_id)
                if staff:
                    recommendation.staff_name = staff.full_name
            except:
                recommendation.staff_name = "نامشخص"
        
        # افزودن نام شایستگی
        if recommendation.related_competency_id:
            try:
                comp = self.competency_dal.get_by_id(recommendation.related_competency_id)
                if comp:
                    recommendation.competency_name = comp.title
            except:
                recommendation.competency_name = "نامشخص"
    
    def get_recommendation_summary(self, profile_id):
        """
        دریافت خلاصه پیشنهادات یک دانش‌آموز
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
        
        Returns:
            dict: خلاصه پیشنهادات
        """
        try:
            recommendations = self.get_recommendations_for_student(profile_id)
            
            if not recommendations:
                return {
                    'total': 0,
                    'pending': 0,
                    'accepted': 0,
                    'rejected': 0,
                    'implemented': 0,
                    'completed': 0,
                    'has_recommendations': False
                }
            
            total = len(recommendations)
            pending = sum(1 for r in recommendations if r.status == Recommendation.STATUS_PENDING)
            accepted = sum(1 for r in recommendations if r.status == Recommendation.STATUS_ACCEPTED)
            rejected = sum(1 for r in recommendations if r.status == Recommendation.STATUS_REJECTED)
            implemented = sum(1 for r in recommendations if r.status == Recommendation.STATUS_IMPLEMENTED)
            completed = sum(1 for r in recommendations if r.status == Recommendation.STATUS_COMPLETED)
            
            return {
                'total': total,
                'pending': pending,
                'accepted': accepted,
                'rejected': rejected,
                'implemented': implemented,
                'completed': completed,
                'has_recommendations': total > 0,
                'active_count': pending + accepted
            }
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت خلاصه پیشنهادات: {e}")
            return {
                'total': 0,
                'pending': 0,
                'accepted': 0,
                'rejected': 0,
                'implemented': 0,
                'completed': 0,
                'has_recommendations': False,
                'active_count': 0
            }
    
    def get_recommendations_by_category(self, profile_id, category):
        """
        دریافت پیشنهادات بر اساس دسته‌بندی
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
            category: دسته‌بندی پیشنهاد
        
        Returns:
            list: لیست پیشنهادات
        """
        try:
            recommendations = self.get_recommendations_for_student(profile_id)
            return [r for r in recommendations if r.category == category]
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیشنهادات بر اساس دسته‌بندی: {e}")
            return []