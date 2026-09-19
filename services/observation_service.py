"""
سرویس مدیریت مشاهدات - نسخه کامل با انتقال منطق از View به Service
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.academic_year_dal import AcademicYearDAL
from dal.competency_dal import CompetencyDAL
from dal.observation_dal import ObservationDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.observation import Observation
from models.student_academic_profile import StudentAcademicProfile
from services.base_service import BaseService
from utils.error_handler import ServiceError, ValidationError
from utils.logger import get_logger


class ObservationService(BaseService):
    """
    سرویس مدیریت مشاهدات
    
    تمام منطق مربوط به مشاهدات در این سرویس قرار دارد.
    View فقط برای نمایش و دریافت ورودی استفاده می‌شود.
    """
    
    def __init__(self):
        super().__init__()
        self.observation_dal = ObservationDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.staff_dal = StaffDAL()
        self.competency_dal = CompetencyDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    def create_observation(self, data, user_id=None, ip_address=None):
        """
        ایجاد مشاهده جدید
        
        Args:
            data: دیکشنری شامل اطلاعات مشاهده
            user_id: شناسه کاربر ایجادکننده (برای Audit)
            ip_address: آدرس IP کاربر
            
        Returns:
            Observation: مشاهده ایجاد شده
            
        Raises:
            ServiceError: در صورت بروز خطا
            ValidationError: در صورت عدم اعتبار داده‌ها
        """
        def _create():
            # 1. اعتبارسنجی داده‌ها
            self._validate_observation_data(data)
            
            # 2. دریافت یا ایجاد StudentAcademicProfile
            student_id = data.get('student_id')
            if not student_id:
                raise ValidationError("دانش‌آموز باید انتخاب شود")
            
            profile = self._get_or_create_profile(student_id)
            if not profile:
                raise ServiceError("امکان ایجاد یا دریافت پرونده سالانه وجود ندارد")
            
            # 3. اعتبارسنجی وجود مشاهده‌گر
            staff_id = data.get('staff_id')
            if not staff_id:
                raise ValidationError("مشاهده‌گر باید انتخاب شود")
            
            staff = self.staff_dal.get_by_id(staff_id)
            if not staff:
                raise ValidationError("مشاهده‌گر انتخاب شده وجود ندارد")
            
            # 4. اعتبارسنجی شایستگی (اگر انتخاب شده باشد)
            competency_id = data.get('competency_id')
            if competency_id:
                competency = self.competency_dal.get_by_id(competency_id)
                if not competency:
                    raise ValidationError("شایستگی انتخاب شده وجود ندارد")
            
            # 5. ایجاد مدل Observation
            observation = Observation()
            observation.student_profile_id = profile.id
            observation.staff_id = staff_id
            observation.competency_id = competency_id
            # ===== اصلاح مهم: ساختار سه‌لایه =====
            # فرم ثبت مشاهده (views/dialogs/observation_form.py) این دو
            # کلید را در data می‌فرستد:
            #     'indicator_id': self.selected_indicator_id,
            #     'observable_behavior_id': self.selected_behavior_id,
            # ولی این سرویس هیچ‌وقت آن‌ها را روی مدل ست نمی‌کرد، پس
            # انتخاب کاربر از درخت شایستگی ← شاخص ← رفتار قابل مشاهده
            # بی‌صدا دور ریخته می‌شد و در دیتابیس NULL می‌ماند.
            observation.indicator_id = data.get('indicator_id')
            observation.observable_behavior_id = data.get('observable_behavior_id')
            # ===== اصلاح (بازرسی ششم): None-safe + یکدست‌سازی تاریخ =====
            observation.observation_date = self.clean_date(data.get('observation_date'), '')
            observation.location = self.clean_text(data.get('location'))
            observation.antecedent = self.clean_text(data.get('antecedent'))
            observation.behavior = self.clean_text(data.get('behavior'))
            observation.consequence = self.clean_text(data.get('consequence'))
            observation.description = self.clean_text(data.get('description'))
            observation.behavior_type = data.get('behavior_type') or 'خنثی'
            observation.severity = data.get('severity', 3)
            observation.tags = self.clean_text(data.get('tags'))
            
            # 6. اعتبارسنجی مدل
            errors = observation.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            # 7. تکمیل برچسب‌ها
            if observation.tags:
                if competency_id:
                    observation.tags = f"{observation.tags},comp:{competency_id}"
            elif competency_id:
                observation.tags = f"comp:{competency_id}"
            
            # 8. ذخیره در دیتابیس
            created_observation = self.observation_dal.create(observation)
            
            # 9. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='create',
                entity_type='observation',
                entity_id=created_observation.id,
                new_value={'observation_id': created_observation.id, 'student_id': student_id},
                ip_address=ip_address
            )
            
            self.logger.info(f"مشاهده با ID {created_observation.id} برای دانش‌آموز {student_id} ایجاد شد.")
            return created_observation
        
        return self.execute_in_transaction(_create)
    
    def update_observation(self, observation_id, data, user_id=None, ip_address=None):
        """
        به‌روزرسانی مشاهده
        
        Args:
            observation_id: شناسه مشاهده
            data: دیکشنری شامل اطلاعات جدید
            user_id: شناسه کاربر ویرایش‌کننده
            ip_address: آدرس IP کاربر
            
        Returns:
            Observation: مشاهده به‌روزرسانی شده
            
        Raises:
            ServiceError: در صورت بروز خطا
            ValidationError: در صورت عدم اعتبار داده‌ها
        """
        def _update():
            # 1. دریافت مشاهده موجود
            observation = self.observation_dal.get_by_id(observation_id)
            if not observation:
                raise ServiceError(f"مشاهده با شناسه {observation_id} یافت نشد.")
            
            # 2. ذخیره مقدار قبلی برای Audit
            old_value = {
                'id': observation.id,
                'student_profile_id': observation.student_profile_id,
                'staff_id': observation.staff_id,
                'competency_id': observation.competency_id,
                'observation_date': observation.observation_date,
                'location': observation.location,
                'behavior_type': observation.behavior_type,
                'severity': observation.severity,
                'tags': observation.tags
            }
            
            # 3. اعتبارسنجی داده‌ها
            self._validate_observation_data(data, is_update=True)
            
            # 4. به‌روزرسانی فیلدها
            student_id = data.get('student_id')
            if student_id:
                profile = self._get_or_create_profile(student_id)
                if profile:
                    observation.student_profile_id = profile.id
            
            observation.staff_id = data.get('staff_id', observation.staff_id)
            observation.competency_id = data.get('competency_id', observation.competency_id)
            # اصلاح: شاخص و رفتار قابل مشاهده هم در ویرایش به‌روز می‌شوند
            observation.indicator_id = data.get('indicator_id', observation.indicator_id)
            observation.observable_behavior_id = data.get(
                'observable_behavior_id', observation.observable_behavior_id
            )
            # ===== اصلاح (بازرسی ششم): None-safe + یکدست‌سازی تاریخ =====
            observation.observation_date = self.clean_date(
                data.get('observation_date'), observation.observation_date or ''
            )
            observation.location = self.clean_text(data.get('location'), observation.location)
            observation.antecedent = self.clean_text(data.get('antecedent'), observation.antecedent)
            observation.behavior = self.clean_text(data.get('behavior'), observation.behavior)
            observation.consequence = self.clean_text(data.get('consequence'), observation.consequence)
            observation.description = self.clean_text(data.get('description'), observation.description)
            observation.behavior_type = data.get('behavior_type', observation.behavior_type)
            observation.severity = data.get('severity', observation.severity)
            observation.tags = self.clean_text(data.get('tags'), observation.tags)
            
            # 5. تکمیل برچسب‌ها
            if observation.tags and observation.competency_id:
                observation.tags = f"{observation.tags},comp:{observation.competency_id}"
            elif observation.competency_id:
                observation.tags = f"comp:{observation.competency_id}"
            
            # 6. اعتبارسنجی مدل
            errors = observation.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            # 7. ذخیره در دیتابیس
            updated_observation = self.observation_dal.update(observation)
            
            # 8. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='edit',
                entity_type='observation',
                entity_id=observation_id,
                old_value=old_value,
                new_value={'id': updated_observation.id, 'updated': True},
                ip_address=ip_address
            )
            
            self.logger.info(f"مشاهده با ID {observation_id} ویرایش شد.")
            return updated_observation
        
        return self.execute_in_transaction(_update)
    
    def delete_observation(self, observation_id, user_id=None, ip_address=None):
        """
        حذف مشاهده
        
        Args:
            observation_id: شناسه مشاهده
            user_id: شناسه کاربر حذف‌کننده
            ip_address: آدرس IP کاربر
            
        Returns:
            bool: آیا حذف موفقیت‌آمیز بود؟
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        def _delete():
            # 1. بررسی وجود مشاهده
            observation = self.observation_dal.get_by_id(observation_id)
            if not observation:
                raise ServiceError(f"مشاهده با شناسه {observation_id} یافت نشد.")
            
            old_value = {
                'id': observation.id,
                'student_profile_id': observation.student_profile_id,
                'staff_id': observation.staff_id,
                'observation_date': observation.observation_date
            }
            
            # 2. حذف از دیتابیس
            result = self.observation_dal.delete(observation_id)
            
            # 3. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='delete_soft',
                entity_type='observation',
                entity_id=observation_id,
                old_value=old_value,
                ip_address=ip_address
            )
            
            self.logger.info(f"مشاهده با ID {observation_id} حذف شد.")
            return result
        
        return self.execute_in_transaction(_delete)
    
    def get_observation(self, observation_id):
        """
        دریافت مشاهده با شناسه
        
        Args:
            observation_id: شناسه مشاهده
            
        Returns:
            Observation: مشاهده
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        try:
            observation = self.observation_dal.get_by_id(observation_id)
            if not observation:
                raise ServiceError(f"مشاهده با شناسه {observation_id} یافت نشد.")
            
            # افزودن اطلاعات دانش‌آموز و مشاهده‌گر برای نمایش
            self._enrich_observation(observation)
            
            return observation
        except Exception as e:
            self.logger.error(f"خطا در دریافت مشاهده: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_observations_by_student(self, student_id, year_id=None, limit=None):
        """
        دریافت مشاهدات یک دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            year_id: شناسه سال تحصیلی (اختیاری)
            limit: تعداد محدود (اختیاری)
            
        Returns:
            list: لیست مشاهدات
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        try:
            # دریافت پرونده بر اساس سال
            if year_id:
                profile = self.profile_dal.get_by_student_and_year(student_id, year_id)
            else:
                profile = self.profile_dal.get_active_by_student(student_id)
            
            if not profile:
                return []
            
            observations = self.observation_dal.get_by_student_profile(profile.id, limit)
            
            # افزودن اطلاعات تکمیلی
            for obs in observations:
                self._enrich_observation(obs)
            
            return observations
        except Exception as e:
            self.logger.error(f"خطا در دریافت مشاهدات دانش‌آموز: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_observations_by_teacher(self, teacher_id, year_id=None, limit=None):
        """
        دریافت مشاهدات یک معلم
        
        Args:
            teacher_id: شناسه معلم
            year_id: شناسه سال تحصیلی (اختیاری)
            limit: تعداد محدود (اختیاری)
            
        Returns:
            list: لیست مشاهدات
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        try:
            # دریافت همه مشاهدات
            observations = self.observation_dal.get_all(limit)
            
            # فیلتر بر اساس معلم
            observations = [obs for obs in observations if obs.staff_id == teacher_id]
            
            # فیلتر بر اساس سال (اگر مشخص شده باشد)
            if year_id:
                filtered = []
                for obs in observations:
                    profile = self.profile_dal.get_by_id(obs.student_profile_id)
                    if profile and profile.academic_year_id == year_id:
                        filtered.append(obs)
                observations = filtered
            
            # افزودن اطلاعات تکمیلی
            for obs in observations:
                self._enrich_observation(obs)
            
            return observations
        except Exception as e:
            self.logger.error(f"خطا در دریافت مشاهدات معلم: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_all_observations(self, limit=None, include_staff_info=False):
        """
        دریافت همه مشاهدات
        
        Args:
            limit: تعداد محدود (اختیاری)
            include_staff_info: آیا اطلاعات مشاهده‌گر هم افزوده شود؟
            
        Returns:
            list: لیست مشاهدات
        """
        try:
            observations = self.observation_dal.get_all(limit)
            
            for obs in observations:
                self._enrich_observation(obs, include_staff_info)
            
            return observations
        except Exception as e:
            self.logger.error(f"خطا در دریافت همه مشاهدات: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_observations_by_date_range(self, student_id, start_date, end_date):
        """
        دریافت مشاهدات در بازه زمانی مشخص
        
        Args:
            student_id: شناسه دانش‌آموز
            start_date: تاریخ شروع (شمسی)
            end_date: تاریخ پایان (شمسی)
            
        Returns:
            list: لیست مشاهدات
        """
        try:
            profile = self.profile_dal.get_active_by_student(student_id)
            if not profile:
                return []
            
            observations = self.observation_dal.get_by_date_range(profile.id, start_date, end_date)
            
            for obs in observations:
                self._enrich_observation(obs)
            
            return observations
        except Exception as e:
            self.logger.error(f"خطا در دریافت مشاهدات بازه زمانی: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_observations_summary(self, student_id, year_id=None):
        """
        دریافت خلاصه آماری مشاهدات یک دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            year_id: شناسه سال تحصیلی (اختیاری)
            
        Returns:
            dict: خلاصه آماری
        """
        try:
            observations = self.get_observations_by_student(student_id, year_id)
            
            if not observations:
                return {
                    'total': 0,
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0,
                    'avg_severity': 0,
                    'max_severity': 0,
                    'min_severity': 0
                }
            
            total = len(observations)
            positive = sum(1 for o in observations if o.behavior_type == "مثبت")
            negative = sum(1 for o in observations if o.behavior_type == "منفی")
            neutral = total - positive - negative
            
            severities = [o.severity for o in observations if o.severity]
            avg_severity = sum(severities) / len(severities) if severities else 0
            
            return {
                'total': total,
                'positive': positive,
                'negative': negative,
                'neutral': neutral,
                'avg_severity': round(avg_severity, 1),
                'max_severity': max(severities) if severities else 0,
                'min_severity': min(severities) if severities else 0,
                'observations': observations
            }
        except Exception as e:
            self.logger.error(f"خطا در دریافت خلاصه مشاهدات: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def _validate_observation_data(self, data, is_update=False):
        """
        اعتبارسنجی داده‌های مشاهده
        
        Args:
            data: دیکشنری داده‌ها
            is_update: آیا در حالت ویرایش هستیم؟
            
        Raises:
            ValidationError: در صورت عدم اعتبار
        """
        errors = []

        # ===== اصلاح (بازرسی ششم) =====
        # ۱) در حالت ویرایش فقط کلیدهای ارسالی اعتبارسنجی می‌شوند،
        #    پس ویرایش جزئی (مثلاً فقط توضیحات) دیگر رد نمی‌شود.
        # ۲) مقدار None باعث AttributeError نمی‌شود.
        # ۳) تاریخ با تقویم واقعی شمسی بررسی می‌شود؛ قبلاً یک regex
        #    ساده «1405/13/45» را هم معتبر می‌دانست و در دیتابیس
        #    ذخیره می‌شد.
        def provided(key):
            return (not is_update) or (key in data)

        # بررسی دانش‌آموز (در حالت ایجاد اجباری است)
        if not is_update and not data.get('student_id'):
            errors.append("دانش‌آموز باید انتخاب شود")

        # بررسی مشاهده‌گر
        if provided('staff_id'):
            if data.get('staff_id') is None:
                errors.append("مشاهده‌گر باید انتخاب شود")
            elif data.get('staff_id') and data.get('staff_id') <= 0:
                errors.append("مشاهده‌گر نامعتبر است")

        # بررسی تاریخ — قاعدهٔ یکسان: نرمال‌سازی، بعد اعتبارسنجی
        if provided('observation_date'):
            _norm, _err = self.check_date(
                data.get('observation_date'), "تاریخ مشاهده", required=True)
            if _err:
                errors.append(_err)

        # بررسی شدت
        if provided('severity'):
            severity = data.get('severity', 3)
            if severity is not None and (severity < 1 or severity > 5):
                errors.append("شدت باید بین 1 تا 5 باشد")

        # بررسی نوع رفتار
        if provided('behavior_type'):
            behavior_type = data.get('behavior_type') or 'خنثی'
            valid_types = ["مثبت", "منفی", "خنثی"]
            if behavior_type not in valid_types:
                errors.append("نوع رفتار نامعتبر است")
        
        if errors:
            raise ValidationError("\n".join(errors))
    
    def _get_or_create_profile(self, student_id):
        """
        دریافت یا ایجاد پرونده سالانه برای دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            
        Returns:
            StudentAcademicProfile: پرونده سالانه
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        # بررسی وجود دانش‌آموز
        student = self.student_dal.get_by_id(student_id)
        if not student:
            raise ServiceError(f"دانش‌آموز با شناسه {student_id} یافت نشد.")
        
        # دریافت سال تحصیلی فعال
        academic_year = self.academic_year_dal.get_active()
        if not academic_year:
            raise ServiceError("هیچ سال تحصیلی فعالی وجود ندارد. لطفاً در تنظیمات یک سال فعال کنید.")
        
        # جستجوی پرونده موجود
        profile = self.profile_dal.get_by_student_and_year(student_id, academic_year.id)
        
        if not profile:
            # ایجاد پرونده جدید
            new_profile = StudentAcademicProfile()
            new_profile.student_id = student_id
            new_profile.academic_year_id = academic_year.id
            new_profile.grade = 1
            new_profile.class_name = ""
            new_profile.status = StudentAcademicProfile.STATUS_ACTIVE
            
            profile = self.profile_dal.create(new_profile)
            self.logger.info(f"پرونده جدید برای دانش‌آموز {student_id} در سال {academic_year.title} ایجاد شد.")
        
        return profile
    
    def _enrich_observation(self, observation, include_staff_info=False):
        """
        افزودن اطلاعات تکمیلی به مشاهده
        
        Args:
            observation: شیء Observation
            include_staff_info: آیا اطلاعات مشاهده‌گر هم افزوده شود؟
        """
        # افزودن نام دانش‌آموز
        try:
            profile = self.profile_dal.get_by_id(observation.student_profile_id)
            if profile:
                student = self.student_dal.get_by_id(profile.student_id)
                if student:
                    observation.student_name = student.full_name
                    observation.student_id = profile.student_id
        except Exception as e:
            self.logger.warning(f"خطا در افزودن نام دانش‌آموز: {e}")
        
        # افزودن نام مشاهده‌گر
        if include_staff_info or not observation.staff_name:
            try:
                staff = self.staff_dal.get_by_id(observation.staff_id)
                if staff:
                    observation.staff_name = staff.full_name
                    observation.staff_role = staff.role
            except Exception as e:
                self.logger.warning(f"خطا در افزودن نام مشاهده‌گر: {e}")
        
        # افزودن نام شایستگی
        if observation.competency_id and not observation.competency_title:
            try:
                competency = self.competency_dal.get_by_id(observation.competency_id)
                if competency:
                    observation.competency_title = competency.title
                    observation.competency_category = competency.category
            except Exception as e:
                self.logger.warning(f"خطا در افزودن نام شایستگی: {e}")
        
        # تنظیم نام‌های پیش‌فرض
        if not hasattr(observation, 'student_name') or not observation.student_name:
            observation.student_name = "نامشخص"
        if not hasattr(observation, 'staff_name') or not observation.staff_name:
            observation.staff_name = "نامشخص"
        if not hasattr(observation, 'competency_title') or not observation.competency_title:
            observation.competency_title = "نامشخص"
    
    def validate_observation(self, data):
        """
        اعتبارسنجی داده‌های مشاهده (برای استفاده در View)
        
        Args:
            data: دیکشنری داده‌ها
            
        Returns:
            tuple: (is_valid, errors_list)
        """
        try:
            self._validate_observation_data(data)
            return True, []
        except ValidationError as e:
            return False, str(e).split('\n')
        except Exception as e:
            return False, [str(e)]

    def search_observations(self, search_term, limit=100):
        """
        جستجوی مشاهدات بر اساس متن
        
        Args:
            search_term: عبارت جستجو
            limit: تعداد محدود
            
        Returns:
            list: لیست مشاهدات مطابق با جستجو
        """
        try:
            observations = self.observation_dal.search(search_term, limit)
            for obs in observations:
                self._enrich_observation(obs)
            return observations
        except Exception as e:
            self.logger.error(f"خطا در جستجوی مشاهدات: {e}")
            raise ServiceError(f"خطا در جستجو: {e!s}")
    
    def search_observations_by_student(self, student_id, search_term):
        """
        جستجوی مشاهدات یک دانش‌آموز بر اساس متن
        
        Args:
            student_id: شناسه دانش‌آموز
            search_term: عبارت جستجو
            
        Returns:
            list: لیست مشاهدات مطابق با جستجو
        """
        try:
            observations = self.observation_dal.search_by_student(student_id, search_term)
            for obs in observations:
                self._enrich_observation(obs)
            return observations
        except Exception as e:
            self.logger.error(f"خطا در جستجوی مشاهدات دانش‌آموز: {e}")
            raise ServiceError(f"خطا در جستجو: {e!s}")
    
    def search_observations_by_teacher(self, teacher_id, search_term):
        """
        جستجوی مشاهدات یک معلم بر اساس متن
        
        Args:
            teacher_id: شناسه معلم
            search_term: عبارت جستجو
            
        Returns:
            list: لیست مشاهدات مطابق با جستجو
        """
        try:
            observations = self.observation_dal.search_by_teacher(teacher_id, search_term)
            for obs in observations:
                self._enrich_observation(obs)
            return observations
        except Exception as e:
            self.logger.error(f"خطا در جستجوی مشاهدات معلم: {e}")
            raise ServiceError(f"خطا در جستجو: {e!s}")