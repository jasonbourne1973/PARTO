"""
ابزارهای کمکی شایستگی - برای کار با ساختار سه‌لایه
Competency (شایستگی) → Indicator (شاخص) → ObservableBehavior (رفتار قابل مشاهده)
"""

from dal.competency_dal import CompetencyDAL
from dal.indicator_dal import IndicatorDAL
from dal.observable_behavior_dal import ObservableBehaviorDAL


class CompetencyHelper:
    """
    ابزارهای کمکی برای کار با ساختار شایستگی
    
    ویژگی‌ها:
    - دریافت مسیر کامل یک شایستگی
    - دریافت شناسه‌های مرتبط با یک شناسه
    - اعتبارسنجی ساختار
    - تبدیل شناسه به مسیر
    """
    
    def __init__(self):
        self.competency_dal = CompetencyDAL()
        self.indicator_dal = IndicatorDAL()
        self.behavior_dal = ObservableBehaviorDAL()
    
    def get_full_path(self, competency_id=None, indicator_id=None, behavior_id=None):
        """
        دریافت مسیر کامل بر اساس شناسه‌ها
        
        Args:
            competency_id: شناسه شایستگی
            indicator_id: شناسه شاخص
            behavior_id: شناسه رفتار قابل مشاهده
        
        Returns:
            dict: {
                'competency_id': int or None,
                'indicator_id': int or None,
                'behavior_id': int or None,
                'competency_name': str or None,
                'indicator_name': str or None,
                'behavior_text': str or None,
                'full_path': str
            }
        """
        result = {
            'competency_id': competency_id,
            'indicator_id': indicator_id,
            'behavior_id': behavior_id,
            'competency_name': None,
            'indicator_name': None,
            'behavior_text': None,
            'full_path': ''
        }
        
        path_parts = []
        
        # دریافت شایستگی
        if competency_id:
            competency = self.competency_dal.get_by_id(competency_id)
            if competency:
                result['competency_name'] = competency.title
                path_parts.append(competency.title)
        
        # دریافت شاخص
        if indicator_id:
            indicator = self.indicator_dal.get_by_id(indicator_id)
            if indicator:
                result['indicator_name'] = indicator.title
                path_parts.append(indicator.title)
                
                # اگر competency_id مشخص نبود، از شاخص بگیر
                if not result['competency_id']:
                    result['competency_id'] = indicator.competency_id
                    if not result['competency_name']:
                        comp = self.competency_dal.get_by_id(indicator.competency_id)
                        if comp:
                            result['competency_name'] = comp.title
        
        # دریافت رفتار قابل مشاهده
        if behavior_id:
            behavior = self.behavior_dal.get_by_id(behavior_id)
            if behavior:
                result['behavior_text'] = behavior.text
                path_parts.append(behavior.text)
                
                # اگر indicator_id مشخص نبود، از رفتار بگیر
                if not result['indicator_id']:
                    result['indicator_id'] = behavior.indicator_id
                    if not result['indicator_name']:
                        ind = self.indicator_dal.get_by_id(behavior.indicator_id)
                        if ind:
                            result['indicator_name'] = ind.title
                
                # اگر competency_id مشخص نبود، از رفتار بگیر
                if not result['competency_id']:
                    result['competency_id'] = behavior.competency_id
                    if not result['competency_name']:
                        comp = self.competency_dal.get_by_id(behavior.competency_id)
                        if comp:
                            result['competency_name'] = comp.title
        
        result['full_path'] = " → ".join(path_parts) if path_parts else "ثبت نشده"
        return result
    
    def get_ids_from_behavior(self, behavior_id):
        """
        دریافت شناسه‌های مرتبط با یک رفتار قابل مشاهده
        
        Args:
            behavior_id: شناسه رفتار قابل مشاهده
        
        Returns:
            dict: {
                'competency_id': int or None,
                'indicator_id': int or None,
                'behavior_id': int
            }
        """
        behavior = self.behavior_dal.get_by_id(behavior_id)
        if not behavior:
            return {
                'competency_id': None,
                'indicator_id': None,
                'behavior_id': behavior_id
            }
        
        return {
            'competency_id': behavior.competency_id,
            'indicator_id': behavior.indicator_id,
            'behavior_id': behavior.id
        }
    
    def get_ids_from_indicator(self, indicator_id):
        """
        دریافت شناسه‌های مرتبط با یک شاخص
        
        Args:
            indicator_id: شناسه شاخص
        
        Returns:
            dict: {
                'competency_id': int or None,
                'indicator_id': int
            }
        """
        indicator = self.indicator_dal.get_by_id(indicator_id)
        if not indicator:
            return {
                'competency_id': None,
                'indicator_id': indicator_id
            }
        
        return {
            'competency_id': indicator.competency_id,
            'indicator_id': indicator.id
        }
    
    def get_behavior_for_observation(self, competency_id=None, indicator_id=None, behavior_id=None):
        """
        دریافت بهترین سطح برای ذخیره در مشاهده
        
        اولویت: رفتار قابل مشاهده > شاخص > شایستگی
        
        Args:
            competency_id: شناسه شایستگی
            indicator_id: شناسه شاخص
            behavior_id: شناسه رفتار قابل مشاهده
        
        Returns:
            dict: {
                'competency_id': int or None,
                'indicator_id': int or None,
                'behavior_id': int or None,
                'level': str  # 'behavior', 'indicator', 'competency', 'none'
            }
        """
        if behavior_id:
            # سطح رفتار قابل مشاهده
            ids = self.get_ids_from_behavior(behavior_id)
            return {
                'competency_id': ids['competency_id'],
                'indicator_id': ids['indicator_id'],
                'behavior_id': behavior_id,
                'level': 'behavior'
            }
        elif indicator_id:
            # سطح شاخص
            ids = self.get_ids_from_indicator(indicator_id)
            return {
                'competency_id': ids['competency_id'],
                'indicator_id': indicator_id,
                'behavior_id': None,
                'level': 'indicator'
            }
        elif competency_id:
            # سطح شایستگی
            return {
                'competency_id': competency_id,
                'indicator_id': None,
                'behavior_id': None,
                'level': 'competency'
            }
        else:
            return {
                'competency_id': None,
                'indicator_id': None,
                'behavior_id': None,
                'level': 'none'
            }
    
    def get_children_count(self, competency_id=None, indicator_id=None):
        """
        دریافت تعداد فرزندان یک سطح
        
        Args:
            competency_id: شناسه شایستگی
            indicator_id: شناسه شاخص
        
        Returns:
            dict: {
                'indicators_count': int,
                'behaviors_count': int,
                'total_count': int
            }
        """
        if competency_id:
            indicators = self.indicator_dal.get_by_competency(competency_id)
            behaviors = self.behavior_dal.get_by_competency(competency_id)
            return {
                'indicators_count': len(indicators),
                'behaviors_count': len(behaviors),
                'total_count': len(indicators) + len(behaviors)
            }
        elif indicator_id:
            behaviors = self.behavior_dal.get_by_indicator(indicator_id)
            return {
                'indicators_count': 0,
                'behaviors_count': len(behaviors),
                'total_count': len(behaviors)
            }
        else:
            return {
                'indicators_count': 0,
                'behaviors_count': 0,
                'total_count': 0
            }
    
    def get_competency_hierarchy(self):
        """
        دریافت ساختار کامل سلسله‌مراتبی شایستگی‌ها
        
        Returns:
            list: لیست شایستگی‌ها با شاخص‌ها و رفتارهای قابل مشاهده
        """
        competencies = self.competency_dal.get_all(load_full=True)
        
        result = []
        for comp in competencies:
            comp_data = {
                'id': comp.id,
                'title': comp.title,
                'description': comp.description,
                'category': comp.category,
                'category_display': comp.category_display,
                'indicators': []
            }
            
            for indicator in comp.indicators:
                ind_data = {
                    'id': indicator.id,
                    'title': indicator.title,
                    'description': indicator.description,
                    'behaviors': []
                }
                
                behaviors = [b for b in comp.observable_behaviors 
                           if b.indicator_id == indicator.id]
                for behavior in behaviors:
                    ind_data['behaviors'].append({
                        'id': behavior.id,
                        'text': behavior.text
                    })
                
                comp_data['indicators'].append(ind_data)
            
            result.append(comp_data)
        
        return result
    
    def validate_selection(self, competency_id=None, indicator_id=None, behavior_id=None):
        """
        اعتبارسنجی انتخاب‌ها
        
        بررسی می‌کند که آیا شناسه‌ها با یکدیگر سازگار هستند
        
        Args:
            competency_id: شناسه شایستگی
            indicator_id: شناسه شاخص
            behavior_id: شناسه رفتار قابل مشاهده
        
        Returns:
            dict: {
                'valid': bool,
                'message': str,
                'suggestions': list
            }
        """
        suggestions = []
        
        # اگر هیچ شناسه‌ای انتخاب نشده
        if not any([competency_id, indicator_id, behavior_id]):
            return {
                'valid': True,
                'message': 'هیچ انتخاب‌ی صورت نگرفته است',
                'suggestions': ['می‌توانید شایستگی، شاخص یا رفتار قابل مشاهده را انتخاب کنید']
            }
        
        # بررسی رفتار قابل مشاهده
        if behavior_id:
            behavior = self.behavior_dal.get_by_id(behavior_id)
            if not behavior:
                return {
                    'valid': False,
                    'message': 'رفتار قابل مشاهده انتخاب‌شده وجود ندارد',
                    'suggestions': ['لطفاً یک رفتار قابل مشاهده معتبر انتخاب کنید']
                }
            
            # بررسی سازگاری با شاخص
            if indicator_id and behavior.indicator_id != indicator_id:
                suggestions.append(f'رفتار قابل مشاهده به شاخص {behavior.indicator_id} تعلق دارد، نه {indicator_id}')
            
            # بررسی سازگاری با شایستگی
            if competency_id and behavior.competency_id != competency_id:
                suggestions.append(f'رفتار قابل مشاهده به شایستگی {behavior.competency_id} تعلق دارد، نه {competency_id}')
            
            if suggestions:
                return {
                    'valid': False,
                    'message': 'ساختار انتخاب‌شده ناسازگار است',
                    'suggestions': suggestions
                }
            
            return {
                'valid': True,
                'message': 'انتخاب معتبر است',
                'suggestions': []
            }
        
        # بررسی شاخص
        if indicator_id:
            indicator = self.indicator_dal.get_by_id(indicator_id)
            if not indicator:
                return {
                    'valid': False,
                    'message': 'شاخص انتخاب‌شده وجود ندارد',
                    'suggestions': ['لطفاً یک شاخص معتبر انتخاب کنید']
                }
            
            # بررسی سازگاری با شایستگی
            if competency_id and indicator.competency_id != competency_id:
                suggestions.append(f'شاخص به شایستگی {indicator.competency_id} تعلق دارد، نه {competency_id}')
            
            if suggestions:
                return {
                    'valid': False,
                    'message': 'ساختار انتخاب‌شده ناسازگار است',
                    'suggestions': suggestions
                }
            
            return {
                'valid': True,
                'message': 'انتخاب معتبر است',
                'suggestions': []
            }
        
        # بررسی شایستگی
        if competency_id:
            competency = self.competency_dal.get_by_id(competency_id)
            if not competency:
                return {
                    'valid': False,
                    'message': 'شایستگی انتخاب‌شده وجود ندارد',
                    'suggestions': ['لطفاً یک شایستگی معتبر انتخاب کنید']
                }
            
            return {
                'valid': True,
                'message': 'انتخاب معتبر است',
                'suggestions': []
            }
        
        return {
            'valid': True,
            'message': 'انتخاب معتبر است',
            'suggestions': []
        }