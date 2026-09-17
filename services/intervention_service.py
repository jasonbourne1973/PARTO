"""
سرویس مدیریت مداخلات - نسخه کامل با انتقال منطق از View به Service
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_service import BaseService
from dal.intervention_dal import InterventionDAL
from dal.student_dal import StudentDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.academic_year_dal import AcademicYearDAL
from dal.staff_dal import StaffDAL
from dal.observation_dal import ObservationDAL
from models.intervention import Intervention
from models.student_academic_profile import StudentAcademicProfile
from utils.error_handler import ServiceError, ValidationError
from utils.logger import get_logger
from datetime import datetime
import jdatetime


class InterventionService(BaseService):
    """
    سرویس مدیریت مداخلات
    
    تمام منطق مربوط به مداخلات در این سرویس قرار دارد.
    View فقط برای نمایش و دریافت ورودی استفاده می‌شود.
    """
    
    # وضعیت‌های مجاز مداخله
    VALID_STATUSES = ['planned', 'in_progress', 'done', 'completed', 'cancelled']
    
    def __init__(self):
        super().__init__()
        self.intervention_dal = InterventionDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.staff_dal = StaffDAL()
        self.observation_dal = ObservationDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    def create_intervention(self, data, user_id=None, ip_address=None):
        """
        ایجاد مداخله جدید
        
        Args:
            data: دیکشنری شامل اطلاعات مداخله
            user_id: شناسه کاربر ایجادکننده (برای Audit)
            ip_address: آدرس IP کاربر
            
        Returns:
            Intervention: مداخله ایجاد شده
            
        Raises:
            ServiceError: در صورت بروز خطا
            ValidationError: در صورت عدم اعتبار داده‌ها
        """
        def _create():
            # 1. اعتبارسنجی داده‌ها
            self._validate_intervention_data(data)
            
            # 2. دریافت یا ایجاد StudentAcademicProfile
            student_id = data.get('student_id')
            if not student_id:
                raise ValidationError("دانش‌آموز باید انتخاب شود")
            
            profile = self._get_or_create_profile(student_id)
            if not profile:
                raise ServiceError("امکان ایجاد یا دریافت پرونده سالانه وجود ندارد")
            
            # 3. اعتبارسنجی وجود مسئول مداخله
            staff_id = data.get('staff_id')
            if not staff_id:
                raise ValidationError("مسئول مداخله باید انتخاب شود")
            
            staff = self.staff_dal.get_by_id(staff_id)
            if not staff:
                raise ValidationError("مسئول مداخله انتخاب شده وجود ندارد")
            
            # 4. اعتبارسنجی مشاهده مرتبط (اگر انتخاب شده باشد)
            observation_id = data.get('observation_id')
            if observation_id:
                observation = self.observation_dal.get_by_id(observation_id)
                if not observation:
                    raise ValidationError("مشاهده مرتبط انتخاب شده وجود ندارد")
                
                # بررسی اینکه مشاهده متعلق به همین دانش‌آموز باشد
                if observation.student_profile_id != profile.id:
                    raise ValidationError("مشاهده مرتبط متعلق به این دانش‌آموز نیست")
            
            # 5. ایجاد مدل Intervention
            intervention = Intervention()
            intervention.student_profile_id = profile.id
            intervention.staff_id = staff_id
            intervention.observation_id = observation_id
            intervention.type = data.get('type', '').strip()
            intervention.date = data.get('date', '').strip()
            intervention.description = data.get('description', '').strip()
            intervention.goal = data.get('goal', '').strip()
            intervention.status = data.get('status', Intervention.STATUS_PLANNED)
            intervention.result = data.get('result', '').strip()
            
            # 6. اعتبارسنجی مدل
            errors = intervention.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            # 7. ذخیره در دیتابیس
            created_intervention = self.intervention_dal.create(intervention)
            
            # 8. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='create',
                entity_type='intervention',
                entity_id=created_intervention.id,
                new_value={'intervention_id': created_intervention.id, 'student_id': student_id},
                ip_address=ip_address
            )
            
            self.logger.info(f"مداخله با ID {created_intervention.id} برای دانش‌آموز {student_id} ایجاد شد.")
            return created_intervention
        
        return self.execute_in_transaction(_create)
    
    def update_intervention(self, intervention_id, data, user_id=None, ip_address=None):
        """
        به‌روزرسانی مداخله
        
        Args:
            intervention_id: شناسه مداخله
            data: دیکشنری شامل اطلاعات جدید
            user_id: شناسه کاربر ویرایش‌کننده
            ip_address: آدرس IP کاربر
            
        Returns:
            Intervention: مداخله به‌روزرسانی شده
            
        Raises:
            ServiceError: در صورت بروز خطا
            ValidationError: در صورت عدم اعتبار داده‌ها
        """
        def _update():
            # 1. دریافت مداخله موجود
            intervention = self.intervention_dal.get_by_id(intervention_id)
            if not intervention:
                raise ServiceError(f"مداخله با شناسه {intervention_id} یافت نشد.")
            
            # 2. ذخیره مقدار قبلی برای Audit
            old_value = {
                'id': intervention.id,
                'student_profile_id': intervention.student_profile_id,
                'staff_id': intervention.staff_id,
                'observation_id': intervention.observation_id,
                'type': intervention.type,
                'date': intervention.date,
                'status': intervention.status,
                'result': intervention.result
            }
            
            # 3. اعتبارسنجی داده‌ها
            self._validate_intervention_data(data, is_update=True)
            
            # 4. به‌روزرسانی فیلدها
            student_id = data.get('student_id')
            if student_id:
                profile = self._get_or_create_profile(student_id)
                if profile:
                    intervention.student_profile_id = profile.id
            
            intervention.staff_id = data.get('staff_id', intervention.staff_id)
            intervention.observation_id = data.get('observation_id', intervention.observation_id)
            intervention.type = data.get('type', intervention.type).strip()
            intervention.date = data.get('date', intervention.date).strip()
            intervention.description = data.get('description', intervention.description).strip()
            intervention.goal = data.get('goal', intervention.goal).strip()
            intervention.status = data.get('status', intervention.status)
            intervention.result = data.get('result', intervention.result).strip()
            
            # 5. اعتبارسنجی مشاهده مرتبط (اگر تغییر کرده باشد)
            if intervention.observation_id:
                observation = self.observation_dal.get_by_id(intervention.observation_id)
                if not observation:
                    raise ValidationError("مشاهده مرتبط انتخاب شده وجود ندارد")
                
                # بررسی اینکه مشاهده متعلق به همین دانش‌آموز باشد
                profile = self.profile_dal.get_by_id(intervention.student_profile_id)
                if profile and observation.student_profile_id != profile.id:
                    raise ValidationError("مشاهده مرتبط متعلق به این دانش‌آموز نیست")
            
            # 6. اعتبارسنجی مدل
            errors = intervention.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            # 7. ذخیره در دیتابیس
            updated_intervention = self.intervention_dal.update(intervention)
            
            # 8. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='edit',
                entity_type='intervention',
                entity_id=intervention_id,
                old_value=old_value,
                new_value={'id': updated_intervention.id, 'updated': True},
                ip_address=ip_address
            )
            
            self.logger.info(f"مداخله با ID {intervention_id} ویرایش شد.")
            return updated_intervention
        
        return self.execute_in_transaction(_update)
    
    def delete_intervention(self, intervention_id, user_id=None, ip_address=None):
        """
        حذف مداخله
        
        Args:
            intervention_id: شناسه مداخله
            user_id: شناسه کاربر حذف‌کننده
            ip_address: آدرس IP کاربر
            
        Returns:
            bool: آیا حذف موفقیت‌آمیز بود؟
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        def _delete():
            # 1. بررسی وجود مداخله
            intervention = self.intervention_dal.get_by_id(intervention_id)
            if not intervention:
                raise ServiceError(f"مداخله با شناسه {intervention_id} یافت نشد.")
            
            # 2. بررسی وجود پیگیری‌های مرتبط
            from dal.followup_dal import FollowUpDAL
            followup_dal = FollowUpDAL()
            followups = followup_dal.get_by_intervention(intervention_id)
            if followups:
                # اگر پیگیری‌های فعال وجود دارد، هشدار بده
                active_followups = [f for f in followups if f.status == 'pending']
                if active_followups:
                    raise ValidationError(
                        f"این مداخله {len(active_followups)} پیگیری فعال دارد. "
                        "لطفاً ابتدا پیگیری‌ها را تکمیل یا لغو کنید."
                    )
            
            old_value = {
                'id': intervention.id,
                'student_profile_id': intervention.student_profile_id,
                'staff_id': intervention.staff_id,
                'type': intervention.type,
                'date': intervention.date
            }
            
            # 3. حذف از دیتابیس
            result = self.intervention_dal.delete(intervention_id)
            
            # 4. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='delete_soft',
                entity_type='intervention',
                entity_id=intervention_id,
                old_value=old_value,
                ip_address=ip_address
            )
            
            self.logger.info(f"مداخله با ID {intervention_id} حذف شد.")
            return result
        
        return self.execute_in_transaction(_delete)
    
    def get_intervention(self, intervention_id):
        """
        دریافت مداخله با شناسه
        
        Args:
            intervention_id: شناسه مداخله
            
        Returns:
            Intervention: مداخله
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        try:
            intervention = self.intervention_dal.get_by_id(intervention_id)
            if not intervention:
                raise ServiceError(f"مداخله با شناسه {intervention_id} یافت نشد.")
            
            # افزودن اطلاعات تکمیلی
            self._enrich_intervention(intervention)
            
            return intervention
        except Exception as e:
            self.logger.error(f"خطا در دریافت مداخله: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {str(e)}")
    
    def get_interventions_by_student(self, student_id, year_id=None, limit=None):
        """
        دریافت مداخلات یک دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            year_id: شناسه سال تحصیلی (اختیاری)
            limit: تعداد محدود (اختیاری)
            
        Returns:
            list: لیست مداخلات
            
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
            
            interventions = self.intervention_dal.get_by_student_profile(profile.id, limit)
            
            # افزودن اطلاعات تکمیلی
            for inter in interventions:
                self._enrich_intervention(inter)
            
            return interventions
        except Exception as e:
            self.logger.error(f"خطا در دریافت مداخلات دانش‌آموز: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {str(e)}")
    
    def get_interventions_by_teacher(self, teacher_id, year_id=None, limit=None):
        """
        دریافت مداخلات یک معلم
        
        Args:
            teacher_id: شناسه معلم
            year_id: شناسه سال تحصیلی (اختیاری)
            limit: تعداد محدود (اختیاری)
            
        Returns:
            list: لیست مداخلات
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        try:
            # دریافت همه مداخلات
            interventions = self.intervention_dal.get_all(limit)
            
            # فیلتر بر اساس معلم
            interventions = [inter for inter in interventions if inter.staff_id == teacher_id]
            
            # فیلتر بر اساس سال (اگر مشخص شده باشد)
            if year_id:
                filtered = []
                for inter in interventions:
                    profile = self.profile_dal.get_by_id(inter.student_profile_id)
                    if profile and profile.academic_year_id == year_id:
                        filtered.append(inter)
                interventions = filtered
            
            # افزودن اطلاعات تکمیلی
            for inter in interventions:
                self._enrich_intervention(inter)
            
            return interventions
        except Exception as e:
            self.logger.error(f"خطا در دریافت مداخلات معلم: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {str(e)}")
    
    def get_all_interventions(self, limit=None, include_staff_info=False):
        """
        دریافت همه مداخلات
        
        Args:
            limit: تعداد محدود (اختیاری)
            include_staff_info: آیا اطلاعات مسئول هم افزوده شود؟
            
        Returns:
            list: لیست مداخلات
        """
        try:
            interventions = self.intervention_dal.get_all(limit)
            
            for inter in interventions:
                self._enrich_intervention(inter, include_staff_info)
            
            return interventions
        except Exception as e:
            self.logger.error(f"خطا در دریافت همه مداخلات: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {str(e)}")
    
    def update_status(self, intervention_id, new_status, user_id=None, ip_address=None):
        """
        به‌روزرسانی وضعیت مداخله
        
        Args:
            intervention_id: شناسه مداخله
            new_status: وضعیت جدید
            user_id: شناسه کاربر
            ip_address: آدرس IP کاربر
            
        Returns:
            bool: آیا به‌روزرسانی موفقیت‌آمیز بود؟
            
        Raises:
            ServiceError: در صورت بروز خطا
            ValidationError: در صورت عدم اعتبار وضعیت
        """
        def _update_status():
            # 1. بررسی وجود مداخله
            intervention = self.intervention_dal.get_by_id(intervention_id)
            if not intervention:
                raise ServiceError(f"مداخله با شناسه {intervention_id} یافت نشد.")
            
            # 2. اعتبارسنجی وضعیت
            if new_status not in self.VALID_STATUSES:
                raise ValidationError(f"وضعیت '{new_status}' نامعتبر است.")
            
            # 3. ذخیره مقدار قبلی
            old_value = {'status': intervention.status}
            
            # 4. به‌روزرسانی وضعیت
            result = self.intervention_dal.update_status(intervention_id, new_status)
            
            # 5. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='edit',
                entity_type='intervention',
                entity_id=intervention_id,
                old_value=old_value,
                new_value={'status': new_status},
                ip_address=ip_address
            )
            
            self.logger.info(f"وضعیت مداخله {intervention_id} به {new_status} تغییر کرد.")
            return result
        
        return self.execute_in_transaction(_update_status)
    
    def get_interventions_summary(self, student_id, year_id=None):
        """
        دریافت خلاصه آماری مداخلات یک دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            year_id: شناسه سال تحصیلی (اختیاری)
            
        Returns:
            dict: خلاصه آماری
        """
        try:
            interventions = self.get_interventions_by_student(student_id, year_id)
            
            if not interventions:
                return {
                    'total': 0,
                    'planned': 0,
                    'in_progress': 0,
                    'done': 0,
                    'completed': 0,
                    'cancelled': 0,
                    'active': 0
                }
            
            total = len(interventions)
            planned = sum(1 for i in interventions if i.status == 'planned')
            in_progress = sum(1 for i in interventions if i.status == 'in_progress')
            done = sum(1 for i in interventions if i.status == 'done')
            completed = sum(1 for i in interventions if i.status == 'completed')
            cancelled = sum(1 for i in interventions if i.status == 'cancelled')
            active = planned + in_progress
            
            return {
                'total': total,
                'planned': planned,
                'in_progress': in_progress,
                'done': done,
                'completed': completed,
                'cancelled': cancelled,
                'active': active,
                'interventions': interventions
            }
        except Exception as e:
            self.logger.error(f"خطا در دریافت خلاصه مداخلات: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {str(e)}")
    
    def get_available_observations_for_intervention(self, student_id):
        """
        دریافت مشاهدات بدون مداخله برای یک دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            
        Returns:
            list: لیست مشاهدات بدون مداخله
        """
        try:
            profile = self.profile_dal.get_active_by_student(student_id)
            if not profile:
                return []
            
            # دریافت همه مشاهدات دانش‌آموز
            all_observations = self.observation_dal.get_by_student_profile(profile.id)
            
            # دریافت شناسه مشاهداتی که مداخله دارند
            interventions = self.intervention_dal.get_by_student_profile(profile.id)
            observation_ids_with_intervention = set()
            for inter in interventions:
                if inter.observation_id:
                    observation_ids_with_intervention.add(inter.observation_id)
            
            # فیلتر کردن مشاهدات بدون مداخله
            observations_without_intervention = [
                obs for obs in all_observations 
                if obs.id not in observation_ids_with_intervention
            ]
            
            return observations_without_intervention
        except Exception as e:
            self.logger.error(f"خطا در دریافت مشاهدات بدون مداخله: {e}")
            return []
    
    def _validate_intervention_data(self, data, is_update=False):
        """
        اعتبارسنجی داده‌های مداخله
        
        Args:
            data: دیکشنری داده‌ها
            is_update: آیا در حالت ویرایش هستیم؟
            
        Raises:
            ValidationError: در صورت عدم اعتبار
        """
        errors = []
        
        # بررسی دانش‌آموز (در حالت ایجاد اجباری است)
        if not is_update and not data.get('student_id'):
            errors.append("دانش‌آموز باید انتخاب شود")
        
        # بررسی مسئول مداخله
        if data.get('staff_id') is None:
            errors.append("مسئول مداخله باید انتخاب شود")
        elif data.get('staff_id') and data.get('staff_id') <= 0:
            errors.append("مسئول مداخله نامعتبر است")
        
        # بررسی نوع مداخله
        intervention_type = data.get('type', '').strip()
        if not intervention_type:
            errors.append("نوع مداخله باید انتخاب شود")
        
        # بررسی تاریخ
        date = data.get('date', '').strip()
        if not date:
            errors.append("تاریخ مداخله نمی‌تواند خالی باشد")
        else:
            # بررسی فرمت تاریخ (ساده)
            import re
            if not re.match(r'^\d{4}/\d{2}/\d{2}$', date):
                errors.append("فرمت تاریخ باید به صورت yyyy/MM/dd باشد")
        
        # بررسی توضیحات
        description = data.get('description', '').strip()
        if not description:
            errors.append("توضیحات مداخله نمی‌تواند خالی باشد")
        elif len(description) < 3:
            errors.append("توضیحات باید حداقل ۳ کاراکتر باشد")
        
        # بررسی وضعیت
        status = data.get('status', 'planned')
        if status not in self.VALID_STATUSES:
            errors.append(f"وضعیت '{status}' نامعتبر است")
        
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
    
    def _enrich_intervention(self, intervention, include_staff_info=False):
        """
        افزودن اطلاعات تکمیلی به مداخله
        
        Args:
            intervention: شیء Intervention
            include_staff_info: آیا اطلاعات مسئول هم افزوده شود؟
        """
        # افزودن نام دانش‌آموز
        try:
            profile = self.profile_dal.get_by_id(intervention.student_profile_id)
            if profile:
                student = self.student_dal.get_by_id(profile.student_id)
                if student:
                    intervention.student_name = student.full_name
                    intervention.student_id = profile.student_id
        except Exception as e:
            self.logger.warning(f"خطا در افزودن نام دانش‌آموز: {e}")
        
        # افزودن نام مسئول
        if include_staff_info or not intervention.staff_name:
            try:
                staff = self.staff_dal.get_by_id(intervention.staff_id)
                if staff:
                    intervention.staff_name = staff.full_name
                    intervention.staff_role = staff.role
            except Exception as e:
                self.logger.warning(f"خطا در افزودن نام مسئول: {e}")
        
        # افزودن اطلاعات مشاهده مرتبط
        if intervention.observation_id:
            try:
                observation = self.observation_dal.get_by_id(intervention.observation_id)
                if observation:
                    intervention.observation_date = observation.observation_date
                    intervention.observation_location = observation.location
            except Exception as e:
                self.logger.warning(f"خطا در افزودن اطلاعات مشاهده: {e}")
        
        # تنظیم نام‌های پیش‌فرض
        if not hasattr(intervention, 'student_name') or not intervention.student_name:
            intervention.student_name = "نامشخص"
        if not hasattr(intervention, 'staff_name') or not intervention.staff_name:
            intervention.staff_name = "نامشخص"
    
    def validate_intervention(self, data):
        """
        اعتبارسنجی داده‌های مداخله (برای استفاده در View)
        
        Args:
            data: دیکشنری داده‌ها
            
        Returns:
            tuple: (is_valid, errors_list)
        """
        try:
            self._validate_intervention_data(data)
            return True, []
        except ValidationError as e:
            return False, str(e).split('\n')
        except Exception as e:
            return False, [str(e)]

    def search_interventions(self, search_term, limit=100):
        """
        جستجوی مداخلات بر اساس متن
        
        Args:
            search_term: عبارت جستجو
            limit: تعداد محدود
            
        Returns:
            list: لیست مداخلات مطابق با جستجو
        """
        try:
            interventions = self.intervention_dal.search(search_term, limit)
            for inter in interventions:
                self._enrich_intervention(inter)
            return interventions
        except Exception as e:
            self.logger.error(f"خطا در جستجوی مداخلات: {e}")
            raise ServiceError(f"خطا در جستجو: {str(e)}")
    
    def search_interventions_by_student(self, student_id, search_term):
        """
        جستجوی مداخلات یک دانش‌آموز بر اساس متن
        
        Args:
            student_id: شناسه دانش‌آموز
            search_term: عبارت جستجو
            
        Returns:
            list: لیست مداخلات مطابق با جستجو
        """
        try:
            interventions = self.intervention_dal.search_by_student(student_id, search_term)
            for inter in interventions:
                self._enrich_intervention(inter)
            return interventions
        except Exception as e:
            self.logger.error(f"خطا در جستجوی مداخلات دانش‌آموز: {e}")
            raise ServiceError(f"خطا در جستجو: {str(e)}")
    
    def search_interventions_by_teacher(self, teacher_id, search_term):
        """
        جستجوی مداخلات یک معلم بر اساس متن
        
        Args:
            teacher_id: شناسه معلم
            search_term: عبارت جستجو
            
        Returns:
            list: لیست مداخلات مطابق با جستجو
        """
        try:
            interventions = self.intervention_dal.search_by_teacher(teacher_id, search_term)
            for inter in interventions:
                self._enrich_intervention(inter)
            return interventions
        except Exception as e:
            self.logger.error(f"خطا در جستجوی مداخلات معلم: {e}")
            raise ServiceError(f"خطا در جستجو: {str(e)}")