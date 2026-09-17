"""
سرویس مدیریت دانش‌آموزان - با پشتیبانی از تحلیل روند
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_service import BaseService
from services.trend_analysis_service import TrendAnalysisService
from dal.student_dal import StudentDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.academic_year_dal import AcademicYearDAL
from models.student import Student
from models.student_academic_profile import StudentAcademicProfile
from utils.security import Security
from utils.error_handler import ServiceError


class StudentService(BaseService):
    """
    سرویس مدیریت دانش‌آموزان با پشتیبانی از تحلیل روند
    
    تمام منطق مربوط به دانش‌آموزان در این سرویس قرار دارد.
    View فقط برای نمایش و دریافت ورودی استفاده می‌شود.
    """
    
    def __init__(self):
        super().__init__()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.trend_service = TrendAnalysisService()
    
    def create_student(self, data, user_id=None, ip_address=None):
        """
        ایجاد دانش‌آموز جدید با پرونده سالانه
        
        Args:
            data: دیکشنری شامل اطلاعات دانش‌آموز
            user_id: شناسه کاربر ایجادکننده (برای Audit)
            ip_address: آدرس IP کاربر
            
        Returns:
            Student: دانش‌آموز ایجاد شده
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        def _create():
            # 1. اعتبارسنجی داده‌ها
            if not data.get('first_name'):
                raise ServiceError("نام نمی‌تواند خالی باشد")
            if not data.get('last_name'):
                raise ServiceError("نام خانوادگی نمی‌تواند خالی باشد")
            
            # 2. ایجاد مدل Student
            student = Student()
            student.first_name = data.get('first_name', '').strip()
            student.last_name = data.get('last_name', '').strip()
            student.national_code = data.get('national_code', '').strip()
            student.birth_date = data.get('birth_date', '').strip()
            student.father_name = data.get('father_name', '').strip()
            student.guardian_name = data.get('guardian_name', '').strip()
            student.guardian_phone = data.get('guardian_phone', '').strip()
            student.address = data.get('address', '').strip()
            student.is_active = 1
            
            # 3. اعتبارسنجی مدل
            self.validate_model(student)
            
            # 4. بررسی تکراری نبودن کد ملی
            if student.national_code:
                existing = self.student_dal.get_by_national_code(student.national_code)
                if existing:
                    raise ServiceError(f"دانش‌آموز با کد ملی '{student.national_code}' قبلاً ثبت شده است.")
            
            # 5. ذخیره در دیتابیس
            created_student = self.student_dal.create(student)
            
            # 6. ایجاد پرونده سالانه
            active_year = self.academic_year_dal.get_active()
            if active_year:
                profile = StudentAcademicProfile()
                profile.student_id = created_student.id
                profile.academic_year_id = active_year.id
                profile.grade = data.get('grade', 1)
                profile.class_name = data.get('class_name', '').strip()
                profile.status = StudentAcademicProfile.STATUS_ACTIVE
                
                self.profile_dal.create(profile)
                self.logger.info(f"پرونده سالانه برای دانش‌آموز {created_student.full_name} ایجاد شد.")
            
            # 7. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='create',
                entity_type='student',
                entity_id=created_student.id,
                new_value={'student_id': created_student.id, 'name': created_student.full_name},
                ip_address=ip_address
            )
            
            self.logger.info(f"دانش‌آموز {created_student.full_name} با ID {created_student.id} ایجاد شد.")
            return created_student
        
        return self.execute_in_transaction(_create)
    
    def update_student(self, student_id, data, user_id=None, ip_address=None):
        """
        به‌روزرسانی دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            data: دیکشنری شامل اطلاعات جدید
            user_id: شناسه کاربر ویرایش‌کننده
            ip_address: آدرس IP کاربر
            
        Returns:
            Student: دانش‌آموز به‌روزرسانی شده
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        def _update():
            # 1. دریافت دانش‌آموز موجود
            student = self.student_dal.get_by_id(student_id)
            if not student:
                raise ServiceError(f"دانش‌آموز با شناسه {student_id} یافت نشد.")
            
            # 2. ذخیره مقدار قبلی برای Audit
            old_value = student.to_dict()
            
            # 3. به‌روزرسانی فیلدها
            student.first_name = data.get('first_name', student.first_name).strip()
            student.last_name = data.get('last_name', student.last_name).strip()
            student.national_code = data.get('national_code', student.national_code).strip()
            student.birth_date = data.get('birth_date', student.birth_date).strip()
            student.father_name = data.get('father_name', student.father_name).strip()
            student.guardian_name = data.get('guardian_name', student.guardian_name).strip()
            student.guardian_phone = data.get('guardian_phone', student.guardian_phone).strip()
            student.address = data.get('address', student.address).strip()
            
            # 4. اعتبارسنجی
            self.validate_model(student)
            
            # 5. ذخیره در دیتابیس
            updated_student = self.student_dal.update(student)
            
            # 6. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='edit',
                entity_type='student',
                entity_id=student_id,
                old_value=old_value,
                new_value=updated_student.to_dict(),
                ip_address=ip_address
            )
            
            self.logger.info(f"دانش‌آموز {updated_student.full_name} با ID {student_id} ویرایش شد.")
            return updated_student
        
        return self.execute_in_transaction(_update)
    
    def delete_student(self, student_id, user_id=None, ip_address=None):
        """
        حذف منطقی دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            user_id: شناسه کاربر حذف‌کننده
            ip_address: آدرس IP کاربر
            
        Returns:
            bool: آیا حذف موفقیت‌آمیز بود؟
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        def _delete():
            # 1. بررسی وجود دانش‌آموز
            student = self.student_dal.get_by_id(student_id)
            if not student:
                raise ServiceError(f"دانش‌آموز با شناسه {student_id} یافت نشد.")
            
            old_value = student.to_dict()
            
            # 2. حذف منطقی
            result = self.student_dal.delete(student_id, user_id)
            
            # 3. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='delete_soft',
                entity_type='student',
                entity_id=student_id,
                old_value=old_value,
                ip_address=ip_address
            )
            
            self.logger.info(f"دانش‌آموز {student.full_name} با ID {student_id} حذف شد.")
            return result
        
        return self.execute_in_transaction(_delete)
    
    def get_student(self, student_id):
        """دریافت دانش‌آموز با شناسه"""
        try:
            student = self.student_dal.get_by_id(student_id)
            if not student:
                raise ServiceError(f"دانش‌آموز با شناسه {student_id} یافت نشد.")
            return student
        except Exception as e:
            self.logger.error(f"خطا در دریافت دانش‌آموز: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {str(e)}")
    
    def get_all_students(self, limit=None, offset=None):
        """دریافت لیست همه دانش‌آموزان"""
        try:
            return self.student_dal.get_all(limit, offset)
        except Exception as e:
            self.logger.error(f"خطا در دریافت لیست دانش‌آموزان: {e}")
            raise ServiceError(f"خطا در دریافت لیست: {str(e)}")
    
    def search_students(self, search_term):
        """جستجوی دانش‌آموزان"""
        try:
            if not search_term or len(search_term.strip()) < 1:
                return self.get_all_students()
            return self.student_dal.search(search_term.strip())
        except Exception as e:
            self.logger.error(f"خطا در جستجوی دانش‌آموزان: {e}")
            raise ServiceError(f"خطا در جستجو: {str(e)}")

    def get_student_trend(self, student_id, academic_year_id=None, period='monthly'):
        """
        دریافت تحلیل روند دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            academic_year_id: شناسه سال تحصیلی (اختیاری)
            period: بازه زمانی ('monthly', 'weekly', 'daily')
            
        Returns:
            dict: داده‌های تحلیل روند
        """
        try:
            # دریافت پرونده دانش‌آموز
            if academic_year_id:
                profile = self.profile_dal.get_by_student_and_year(student_id, academic_year_id)
            else:
                profile = self.profile_dal.get_active_by_student(student_id)
            
            if not profile:
                return {
                    'success': False,
                    'error': 'پرونده فعالی برای این دانش‌آموز یافت نشد.'
                }
            
            # تحلیل روند
            return self.trend_service.analyze_student_trend(profile.id, period)
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت روند دانش‌آموز: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_student_timeline(self, student_id, academic_year_id=None):
        """
        دریافت Timeline دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            academic_year_id: شناسه سال تحصیلی (اختیاری)
            
        Returns:
            list: لیست رویدادها
        """
        try:
            if academic_year_id:
                profile = self.profile_dal.get_by_student_and_year(student_id, academic_year_id)
            else:
                profile = self.profile_dal.get_active_by_student(student_id)
            
            if not profile:
                return []
            
            return self.trend_service.get_student_timeline(profile.id)
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت Timeline: {e}")
            return []
    
    def get_student_progress(self, student_id, academic_year_id=None):
        """
        دریافت خلاصه پیشرفت دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            academic_year_id: شناسه سال تحصیلی (اختیاری)
            
        Returns:
            dict: خلاصه پیشرفت
        """
        try:
            if academic_year_id:
                profile = self.profile_dal.get_by_student_and_year(student_id, academic_year_id)
            else:
                profile = self.profile_dal.get_active_by_student(student_id)
            
            if not profile:
                return {
                    'has_data': False,
                    'message': 'پرونده فعالی برای این دانش‌آموز یافت نشد.'
                }
            
            return self.trend_service.get_student_progress_summary(profile.id)
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیشرفت دانش‌آموز: {e}")
            return {
                'has_data': False,
                'message': f'خطا: {str(e)}'
            }