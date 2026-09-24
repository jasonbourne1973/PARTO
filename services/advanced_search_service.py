"""
سرویس جستجوی پیشرفته - جستجوی ترکیبی با چندین معیار و ذخیره فیلترها
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.saved_filter_dal import SavedFilterDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.saved_filter import SavedFilter
from services.base_service import BaseService
from utils.error_handler import ServiceError, ValidationError
from utils.logger import get_logger


class AdvancedSearchService(BaseService):
    """
    سرویس جستجوی پیشرفته
    
    ویژگی‌ها:
    - جستجوی ترکیبی با چندین معیار
    - ذخیره فیلترهای پرکاربرد
    - اشتراک‌گذاری فیلترها
    - جستجوی هوشمند با پیشنهادات
    """
    
    def __init__(self):
        super().__init__()
        self.student_dal = StudentDAL()
        # ===== اصلاح (بازرسی دوم) =====
        # search_observations در خط ~۱۶۷ از `self.profile_dal` استفاده می‌کند:
        #
        #     profile = self.profile_dal.get_active_by_student(params['student_id'])
        #
        # ولی __init__ هرگز آن را نمی‌ساخت. نتیجه (اجرای واقعی):
        #
        #     AdvancedSearchService().search_observations({'student_id': 1})
        #     → AttributeError: 'AdvancedSearchService' object has no attribute 'profile_dal'
        #     → ServiceError: خطا در جستجو: ...
        #
        # یعنی «فیلتر کردن مشاهدات بر اساس دانش‌آموز» در جست‌وجوی پیشرفته
        # همیشه شکست می‌خورد. جالب اینکه متد search_students در همین فایل
        # یک StudentAcademicProfileDAL محلی می‌ساخت (الگوی درست) — فقط این
        # یکی صفت جا افتاده بود (همان الگوی باگ گزارش معلم).
        self.profile_dal = StudentAcademicProfileDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.saved_filter_dal = SavedFilterDAL()
        self.staff_dal = StaffDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    # ============================================================
    # جستجوی دانش‌آموزان
    # ============================================================
    
    def search_students(self, params):
        """
        جستجوی پیشرفته دانش‌آموزان
        
        Args:
            params: dict {
                'name': str,
                'national_code': str,
                'grade': int,
                'class_name': str,
                'birth_date': str,
                'teacher_id': int,
                'academic_year_id': int,
                'has_observation': bool,
                'has_intervention': bool,
                'status': str
            }
        
        Returns:
            list: لیست دانش‌آموزان مطابق با جستجو
        """
        try:
            # استفاده از جستجوی پیشرفته موجود
            results = self.student_dal.advanced_search(
                name=params.get('name'),
                national_code=params.get('national_code'),
                grade=params.get('grade'),
                class_name=params.get('class_name'),
                birth_date=params.get('birth_date')
            )
            
            # فیلترهای اضافی
            if params.get('teacher_id'):
                from dal.teacher_assignment_dal import TeacherAssignmentDAL
                assignment_dal = TeacherAssignmentDAL()
                assignments = assignment_dal.get_by_teacher(params['teacher_id'], params.get('academic_year_id'))
                teacher_student_ids = [a.student_id for a in assignments]
                results = [s for s in results if s.id in teacher_student_ids]
            
            if params.get('has_observation') is not None:
                if params['has_observation']:
                    # فقط دانش‌آموزانی که مشاهده دارند
                    results = [s for s in results if self._has_observation(s.id, params.get('academic_year_id'))]
                else:
                    # فقط دانش‌آموزانی که مشاهده ندارند
                    results = [s for s in results if not self._has_observation(s.id, params.get('academic_year_id'))]
            
            if params.get('has_intervention') is not None:
                if params['has_intervention']:
                    results = [s for s in results if self._has_intervention(s.id, params.get('academic_year_id'))]
                else:
                    results = [s for s in results if not self._has_intervention(s.id, params.get('academic_year_id'))]
            
            if params.get('status'):
                results = [s for s in results if self._get_student_status(s.id, params.get('academic_year_id')) == params['status']]
            
            return results
            
        except Exception as e:
            self.logger.error(f"خطا در جستجوی دانش‌آموزان: {e}")
            raise ServiceError(f"خطا در جستجو: {e!s}")
    
    def _has_observation(self, student_id, academic_year_id=None):
        """بررسی وجود مشاهده برای دانش‌آموز"""
        try:
            observations = self.observation_dal.get_by_student(student_id, academic_year_id)
            return len(observations) > 0
        except Exception:
            return False
    
    def _has_intervention(self, student_id, academic_year_id=None):
        """بررسی وجود مداخله برای دانش‌آموز"""
        try:
            interventions = self.intervention_dal.get_by_student(student_id, academic_year_id)
            return len(interventions) > 0
        except Exception:
            return False
    
    def _get_student_status(self, student_id, academic_year_id=None):
        """دریافت وضعیت دانش‌آموز"""
        try:
            # از همان self.profile_dal استفاده می‌شود (ساخت DAL محلی در هر
            # فراخوانی لازم نیست؛ تازه‌سازی هم بالا انجام شده است)
            if academic_year_id:
                profile = self.profile_dal.get_by_student_and_year(student_id, academic_year_id)
            else:
                profile = self.profile_dal.get_active_by_student(student_id)
            return profile.status if profile else 'inactive'
        except Exception:
            return 'inactive'
    
    # ============================================================
    # جستجوی مشاهدات
    # ============================================================
    
    def search_observations(self, params):
        """
        جستجوی پیشرفته مشاهدات
        
        Args:
            params: dict {
                'student_id': int,
                'teacher_id': int,
                'start_date': str,
                'end_date': str,
                'behavior_type': str,
                'location': str,
                'severity_min': int,
                'severity_max': int,
                'competency_id': int,
                'search_text': str
            }
        
        Returns:
            list: لیست مشاهدات مطابق با جستجو
        """
        try:
            observations = []
            
            if params.get('student_id'):
                profile = self.profile_dal.get_active_by_student(params['student_id'])
                if profile:
                    observations = self.observation_dal.get_by_student_profile(profile.id)
            else:
                observations = self.observation_dal.get_all()
            
            # فیلتر بر اساس معلم
            if params.get('teacher_id'):
                observations = [o for o in observations if o.staff_id == params['teacher_id']]
            
            # فیلتر بر اساس تاریخ
            if params.get('start_date'):
                observations = [o for o in observations if o.observation_date >= params['start_date']]
            if params.get('end_date'):
                observations = [o for o in observations if o.observation_date <= params['end_date']]
            
            # فیلتر بر اساس نوع رفتار
            if params.get('behavior_type'):
                observations = [o for o in observations if o.behavior_type == params['behavior_type']]
            
            # فیلتر بر اساس محیط
            if params.get('location'):
                observations = [o for o in observations if o.location == params['location']]
            
            # فیلتر بر اساس شدت
            if params.get('severity_min') is not None:
                observations = [o for o in observations if o.severity >= params['severity_min']]
            if params.get('severity_max') is not None:
                observations = [o for o in observations if o.severity <= params['severity_max']]
            
            # فیلتر بر اساس شایستگی
            if params.get('competency_id'):
                observations = [o for o in observations if o.competency_id == params['competency_id']]
            
            # جستجوی متن
            if params.get('search_text'):
                text = params['search_text'].lower()
                observations = [
                    o for o in observations 
                    if text in (o.behavior or '').lower() 
                    or text in (o.description or '').lower()
                    or text in (o.antecedent or '').lower()
                    or text in (o.consequence or '').lower()
                ]
            
            return observations
            
        except Exception as e:
            self.logger.error(f"خطا در جستجوی مشاهدات: {e}")
            raise ServiceError(f"خطا در جستجو: {e!s}")
    
    # ============================================================
    # مدیریت فیلترهای ذخیره‌شده
    # ============================================================
    
    def save_filter(self, name, filter_type, filter_params, user_id, 
                    description=None, visibility=SavedFilter.VISIBILITY_PRIVATE):
        """
        ذخیره فیلتر
        
        Args:
            name: نام فیلتر
            filter_type: نوع فیلتر
            filter_params: پارامترهای فیلتر
            user_id: شناسه کاربر
            description: توضیحات (اختیاری)
            visibility: سطح دسترسی
        
        Returns:
            SavedFilter: فیلتر ذخیره‌شده
        """
        try:
            # اعتبارسنجی
            if not name or len(name.strip()) < 2:
                raise ValidationError("نام فیلتر باید حداقل ۲ کاراکتر باشد")
            if not filter_params:
                raise ValidationError("پارامترهای فیلتر نمی‌تواند خالی باشد")
            
            saved_filter = SavedFilter()
            saved_filter.name = name.strip()
            saved_filter.description = description.strip() if description else None
            saved_filter.filter_type = filter_type
            saved_filter.visibility = visibility
            saved_filter.user_id = user_id
            saved_filter.filter_params = filter_params
            saved_filter.use_count = 0
            
            errors = saved_filter.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            created = self.saved_filter_dal.create(saved_filter)
            self.logger.info(f"فیلتر '{name}' برای کاربر {user_id} ذخیره شد")
            return created
            
        except Exception as e:
            self.logger.error(f"خطا در ذخیره فیلتر: {e}")
            raise ServiceError(f"خطا در ذخیره فیلتر: {e!s}")
    
    def get_user_filters(self, user_id, filter_type=None):
        """دریافت فیلترهای یک کاربر"""
        try:
            return self.saved_filter_dal.get_by_user(user_id, filter_type)
        except Exception as e:
            self.logger.error(f"خطا در دریافت فیلترها: {e}")
            return []
    
    def get_shared_filters(self, filter_type=None):
        """دریافت فیلترهای اشتراکی"""
        try:
            return self.saved_filter_dal.get_shared_filters(filter_type)
        except Exception as e:
            self.logger.error(f"خطا در دریافت فیلترهای اشتراکی: {e}")
            return []
    
    def get_popular_filters(self, filter_type=None, limit=10):
        """دریافت پرکاربردترین فیلترها"""
        try:
            return self.saved_filter_dal.get_popular_filters(filter_type, limit)
        except Exception as e:
            self.logger.error(f"خطا در دریافت فیلترهای پرکاربرد: {e}")
            return []
    
    def apply_filter(self, filter_id, user_id=None):
        """
        اعمال فیلتر و افزایش تعداد استفاده
        
        Args:
            filter_id: شناسه فیلتر
            user_id: شناسه کاربر (برای بررسی دسترسی)
        
        Returns:
            dict: پارامترهای فیلتر
        """
        try:
            saved_filter = self.saved_filter_dal.get_by_id(filter_id)
            if not saved_filter:
                raise ServiceError(f"فیلتر با شناسه {filter_id} یافت نشد")
            
            # بررسی دسترسی
            if saved_filter.visibility == SavedFilter.VISIBILITY_PRIVATE and saved_filter.user_id != user_id:
                raise ServiceError("شما به این فیلتر دسترسی ندارید")
            
            # افزایش تعداد استفاده
            self.saved_filter_dal.increment_use(filter_id)
            
            return saved_filter.filter_params
            
        except Exception as e:
            self.logger.error(f"خطا در اعمال فیلتر: {e}")
            raise ServiceError(f"خطا در اعمال فیلتر: {e!s}")
    
    def delete_filter(self, filter_id, user_id=None):
        """حذف فیلتر"""
        try:
            saved_filter = self.saved_filter_dal.get_by_id(filter_id)
            if not saved_filter:
                raise ServiceError(f"فیلتر با شناسه {filter_id} یافت نشد")
            
            # بررسی دسترسی
            if saved_filter.user_id != user_id:
                raise ServiceError("شما فقط می‌توانید فیلترهای خود را حذف کنید")
            
            return self.saved_filter_dal.delete(filter_id, user_id)
            
        except Exception as e:
            self.logger.error(f"خطا در حذف فیلتر: {e}")
            raise ServiceError(f"خطا در حذف فیلتر: {e!s}")
    
    def update_filter(self, filter_id, data, user_id=None):
        """به‌روزرسانی فیلتر"""
        try:
            saved_filter = self.saved_filter_dal.get_by_id(filter_id)
            if not saved_filter:
                raise ServiceError(f"فیلتر با شناسه {filter_id} یافت نشد")
            
            # بررسی دسترسی
            if saved_filter.user_id != user_id:
                raise ServiceError("شما فقط می‌توانید فیلترهای خود را ویرایش کنید")
            
            if 'name' in data:
                saved_filter.name = data['name'].strip()
            if 'description' in data:
                saved_filter.description = data['description'].strip()
            if 'visibility' in data:
                saved_filter.visibility = data['visibility']
            if 'filter_params' in data:
                saved_filter.filter_params = data['filter_params']
            
            errors = saved_filter.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            return self.saved_filter_dal.update(saved_filter)
            
        except Exception as e:
            self.logger.error(f"خطا در به‌روزرسانی فیلتر: {e}")
            raise ServiceError(f"خطا در به‌روزرسانی فیلتر: {e!s}")
    
    def get_filter_suggestions(self, filter_type, user_id=None):
        """
        دریافت پیشنهادات فیلتر بر اساس نوع و کاربر
        
        Args:
            filter_type: نوع فیلتر
            user_id: شناسه کاربر (اختیاری)
        
        Returns:
            list: لیست فیلترهای پیشنهادی
        """
        try:
            suggestions = []
            
            # فیلترهای پرکاربرد از نوع مشخص
            popular = self.get_popular_filters(filter_type, 5)
            suggestions.extend(popular)
            
            # فیلترهای اشتراکی از نوع مشخص
            shared = self.get_shared_filters(filter_type)
            for f in shared:
                if f not in suggestions:
                    suggestions.append(f)
            
            # فیلترهای شخصی کاربر
            if user_id:
                personal = self.get_user_filters(user_id, filter_type)
                for f in personal:
                    if f not in suggestions:
                        suggestions.append(f)
            
            return suggestions[:10]  # حداکثر ۱۰ پیشنهاد
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیشنهادات فیلتر: {e}")
            return []