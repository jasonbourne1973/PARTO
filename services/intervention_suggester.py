"""
سرویس پیشنهاد مداخلات - پیشنهاد نوع مداخله مناسب بر اساس داده‌ها
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.competency_dal import CompetencyDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from services.base_service import BaseService
from utils.logger import get_logger


class InterventionSuggester(BaseService):
    """
    سرویس پیشنهاد مداخلات
    
    ویژگی‌ها:
    - پیشنهاد نوع مداخله بر اساس شایستگی ضعیف
    - پیشنهاد مداخله بر اساس الگوهای رفتاری
    - پیشنهاد مداخله بر اساس مداخلات موفق قبلی
    - اولویت‌بندی پیشنهادات
    """
    
    # نگاشت شایستگی به نوع مداخله پیشنهادی
    #
    # ===== اصلاح =====
    # نسخه قبلی دو دسته از CompetencyCategory را نداشت:
    # 'behavioral' و 'cognitive'. شایستگی‌های این دو دسته هیچ
    # پیشنهاد دسته‌بندی‌شده‌ای نمی‌گرفتند.
    COMPETENCY_INTERVENTION_MAP = {
        'emotional': ['individual_talk', 'counseling', 'encouragement'],
        'social': ['group_activity', 'group_talk', 'peer_helper'],
        'educational': ['encouragement', 'responsibility', 'seat_change'],
        'moral': ['individual_talk', 'warning', 'responsibility'],
        'self_management': ['responsibility', 'encouragement', 'seat_change'],
        'participation': ['group_activity', 'encouragement', 'responsibility'],
        'behavioral': ['individual_talk', 'warning', 'peer_helper'],
        'cognitive': ['encouragement', 'educational_game', 'responsibility'],
    }

    # نگاشت نوع رفتار به نوع مداخله
    #
    # ===== اصلاح مهم =====
    # نسخه قبلی کلیدهای انگلیسی داشت ('positive'، 'negative'، 'neutral')
    # ولی ObservationDAL.get_observation_patterns_for_student مقدار
    # فارسی برمی‌گرداند ('مثبت'، 'منفی'، 'خنثی'):
    #
    #     types = {'مثبت': positive, 'منفی': negative, 'خنثی': ...}
    #     most_common_type = max(types.items(), ...)[0]
    #
    # پس `most_common_type in BEHAVIOR_INTERVENTION_MAP` همیشه False
    # بود و گام ۳ موتور پیشنهاد (پیشنهاد بر اساس الگوی رفتاری)
    # هرگز اجرا نمی‌شد.
    #
    # حالا هر دو شکل پذیرفته می‌شود تا اگر جایی مقدار انگلیسی هم
    # رسید، کار کند.
    BEHAVIOR_INTERVENTION_MAP = {
        'مثبت': ['encouragement', 'responsibility'],
        'منفی': ['individual_talk', 'warning', 'counseling'],
        'خنثی': ['encouragement', 'group_activity'],
        # سازگاری با مقادیر انگلیسی
        'positive': ['encouragement', 'responsibility'],
        'negative': ['individual_talk', 'warning', 'counseling'],
        'neutral': ['encouragement', 'group_activity'],
    }
    
    def __init__(self):
        super().__init__()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.competency_dal = CompetencyDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    def suggest_intervention(self, profile_id, competency_id=None):
        """
        پیشنهاد مداخله برای یک دانش‌آموز
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
            competency_id: شناسه شایستگی (اختیاری)
        
        Returns:
            dict: {
                'suggested_types': list,
                'reason': str,
                'priority': str,
                'details': dict
            }
        """
        try:
            # دریافت اطلاعات دانش‌آموز
            profile = self.profile_dal.get_by_id(profile_id)
            if not profile:
                return {'suggested_types': [], 'reason': 'پرونده یافت نشد', 'priority': 'low', 'details': {}}
            
            # دریافت مشاهدات
            observations = self.observation_dal.get_by_student_profile(profile_id)
            
            # دریافت مداخلات موفق قبلی
            successful_interventions = self.intervention_dal.get_successful_interventions_for_student(profile_id)
            
            suggestions = []
            reasons = []
            
            # ===== ۱. پیشنهاد بر اساس شایستگی =====
            if competency_id:
                competency = self.competency_dal.get_by_id(competency_id)
                if competency:
                    comp_category = competency.category
                    if comp_category in self.COMPETENCY_INTERVENTION_MAP:
                        suggestions.extend(self.COMPETENCY_INTERVENTION_MAP[comp_category])
                        reasons.append(f"بر اساس شایستگی '{competency.title}'")
            
            # ===== ۲. پیشنهاد بر اساس شایستگی‌های ضعیف =====
            if not suggestions:
                weak_comps = self.observation_dal.get_weak_competencies_for_student(profile_id, limit=1)
                if weak_comps:
                    comp_id = weak_comps[0].get('competency_id')
                    if comp_id:
                        comp = self.competency_dal.get_by_id(comp_id)
                        if comp and comp.category in self.COMPETENCY_INTERVENTION_MAP:
                            suggestions.extend(self.COMPETENCY_INTERVENTION_MAP[comp.category])
                            reasons.append(f"بر اساس شایستگی ضعیف '{comp.title}'")
            
            # ===== ۳. پیشنهاد بر اساس الگوی رفتاری =====
            if observations:
                patterns = self.observation_dal.get_observation_patterns_for_student(profile_id)
                most_common_type = patterns.get('most_common_behavior_type')
                
                if most_common_type and most_common_type in self.BEHAVIOR_INTERVENTION_MAP:
                    suggestions.extend(self.BEHAVIOR_INTERVENTION_MAP[most_common_type])
                    reasons.append(f"بر اساس نوع رفتار '{most_common_type}'")
            
            # ===== ۴. پیشنهاد بر اساس مداخلات موفق قبلی =====
            if successful_interventions:
                for inter in successful_interventions[:2]:
                    if inter.type not in suggestions:
                        suggestions.append(inter.type)
                if successful_interventions:
                    reasons.append("بر اساس مداخلات موفق قبلی")
            
            # ===== ۵. پیشنهادات پیش‌فرض =====
            if not suggestions:
                suggestions = ['encouragement', 'individual_talk']
                reasons.append("پیشنهاد پیش‌فرض")
            
            # حذف تکراری‌ها
            suggestions = list(dict.fromkeys(suggestions))
            
            # تعیین اولویت
            priority = self._determine_priority(profile_id, observations)
            
            # دریافت توضیحات کامل
            details = self._get_suggestion_details(suggestions, profile_id)
            
            return {
                'suggested_types': suggestions[:3],  # حداکثر ۳ نوع
                'reason': ' | '.join(reasons[:3]),
                'priority': priority,
                'details': details
            }
            
        except Exception as e:
            self.logger.error(f"خطا در پیشنهاد مداخله: {e}")
            return {
                'suggested_types': ['encouragement', 'individual_talk'],
                'reason': 'خطا در تحلیل، پیشنهاد پیش‌فرض',
                'priority': 'low',
                'details': {}
            }
    
    def _determine_priority(self, profile_id, observations):
        """تعیین اولویت پیشنهاد"""
        try:
            if not observations:
                return 'low'
            
            # بررسی نسبت رفتار منفی
            negative_count = sum(1 for o in observations if o.behavior_type == 'منفی')
            total = len(observations)
            negative_ratio = negative_count / total if total > 0 else 0
            
            if negative_ratio > 0.5:
                return 'high'
            elif negative_ratio > 0.3:
                return 'medium'
            else:
                return 'low'
                
        except Exception:
            return 'medium'
    
    def _get_suggestion_details(self, suggested_types, profile_id):
        """دریافت جزئیات پیشنهادات"""
        details = {}
        
        # نگاشت نوع مداخله به توضیحات
        type_descriptions = {
            'individual_talk': 'گفتگوی فردی با دانش‌آموز برای بررسی و حل مسئله',
            'group_talk': 'گفتگوی گروهی با چند دانش‌آموز برای بحث و تبادل نظر',
            'parent_call': 'تماس تلفنی با والدین برای هماهنگی و اطلاع‌رسانی',
            'parent_meeting': 'جلسه حضوری با والدین برای هماهنگی بیشتر',
            'responsibility': 'سپردن مسئولیت به دانش‌آموز برای افزایش اعتماد به نفس',
            'encouragement': 'تشویق و تقویت رفتارهای مثبت',
            'group_activity': 'فعالیت گروهی هدفمند برای تقویت همکاری',
            'educational_game': 'بازی تربیتی برای آموزش غیرمستقیم',
            'referral': 'ارجاع به مشاور مدرسه برای بررسی تخصصی',
            'counseling': 'جلسه مشاوره فردی با دانش‌آموز',
            'seat_change': 'تغییر جای نشستن برای بهبود تمرکز',
            'peer_helper': 'تعیین همیار برای کمک و همراهی',
            'warning': 'تذکر شفاهی برای اصلاح رفتار',
            'other': 'سایر مداخلات'
        }
        
        for type_name in suggested_types:
            details[type_name] = type_descriptions.get(type_name, 'مداخله بدون توضیح')
        
        return details
    
    def suggest_intervention_for_competency(self, competency_id):
        """
        پیشنهاد مداخله برای یک شایستگی خاص
        
        Args:
            competency_id: شناسه شایستگی
        
        Returns:
            list: لیست انواع مداخله پیشنهادی
        """
        try:
            competency = self.competency_dal.get_by_id(competency_id)
            if not competency:
                return ['encouragement', 'individual_talk']
            
            category = competency.category
            return self.COMPETENCY_INTERVENTION_MAP.get(category, ['encouragement', 'individual_talk'])
            
        except Exception as e:
            self.logger.error(f"خطا در پیشنهاد مداخله برای شایستگی: {e}")
            return ['encouragement', 'individual_talk']
    
    def get_intervention_recommendations(self, profile_id, limit=3):
        """
        دریافت پیشنهادات مداخله برای یک دانش‌آموز
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
            limit: تعداد محدود
        
        Returns:
            list: لیست پیشنهادات با جزئیات
        """
        try:
            # دریافت شایستگی‌های ضعیف
            weak_comps = self.observation_dal.get_weak_competencies_for_student(profile_id, limit)
            
            recommendations = []
            
            for comp in weak_comps:
                comp_id = comp.get('competency_id')
                if comp_id:
                    comp_obj = self.competency_dal.get_by_id(comp_id)
                    if comp_obj:
                        suggested_types = self.suggest_intervention_for_competency(comp_id)
                        recommendations.append({
                            'competency_id': comp_id,
                            'competency_name': comp_obj.title,
                            'avg_severity': comp.get('avg_severity', 0),
                            'observation_count': comp.get('count', 0),
                            'suggested_interventions': suggested_types[:2],
                            'priority': 'high' if comp.get('avg_severity', 0) <= 1.5 else 'medium'
                        })
            
            return recommendations[:limit]
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیشنهادات مداخله: {e}")
            return []