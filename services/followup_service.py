"""
سرویس مدیریت پیگیری‌ها - نسخه کامل با انتقال منطق از View به Service
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import ClassVar

from dal.academic_year_dal import AcademicYearDAL
from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.followup import FollowUp
from services.base_service import BaseService
from utils.error_handler import ServiceError, ValidationError
from utils.logger import get_logger


class FollowUpService(BaseService):
    """
    سرویس مدیریت پیگیری‌ها
    
    تمام منطق مربوط به پیگیری‌ها در این سرویس قرار دارد.
    View فقط برای نمایش و دریافت ورودی استفاده می‌شود.
    """
    
    # وضعیت‌های مجاز پیگیری
    VALID_STATUSES: ClassVar[list[str]] = ['pending', 'done', 'continued', 'closed', 'cancelled']
    
    # نوع‌های نتیجه مجاز
    VALID_RESULT_TYPES: ClassVar[list[str]] = ['improved', 'no_change', 'continued', 'new_status', 'insufficient', 'needs_more']
    
    def __init__(self):
        super().__init__()
        self.followup_dal = FollowUpDAL()
        self.intervention_dal = InterventionDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    def create_followup(self, data, user_id=None, ip_address=None):
        """
        ایجاد پیگیری جدید
        
        Args:
            data: دیکشنری شامل اطلاعات پیگیری
            user_id: شناسه کاربر ایجادکننده (برای Audit)
            ip_address: آدرس IP کاربر
            
        Returns:
            FollowUp: پیگیری ایجاد شده
            
        Raises:
            ServiceError: در صورت بروز خطا
            ValidationError: در صورت عدم اعتبار داده‌ها
        """
        def _create():
            # 1. اعتبارسنجی داده‌ها
            self._validate_followup_data(data)
            
            # 2. اعتبارسنجی وجود مداخله
            intervention_id = data.get('intervention_id')
            if not intervention_id:
                raise ValidationError("مداخله باید انتخاب شود")
            
            intervention = self.intervention_dal.get_by_id(intervention_id)
            if not intervention:
                raise ValidationError("مداخله انتخاب شده وجود ندارد")
            
            # 3. بررسی اینکه مداخله در وضعیت مناسب است
            if intervention.status in ['cancelled', 'completed']:
                raise ValidationError(
                    f"مداخله در وضعیت '{intervention.status_display}' است و نمی‌توان برای آن پیگیری ثبت کرد."
                )
            
            # 4. بررسی عدم وجود پیگیری تکراری برای همین مداخله (در حالت ایجاد)
            existing_followups = self.followup_dal.get_by_intervention(intervention_id)
            if existing_followups:
                # اگر مداخله قبلاً پیگیری دارد، هشدار بده
                self.logger.warning(f"مداخله {intervention_id} قبلاً {len(existing_followups)} پیگیری دارد.")
                # اما اجازه ثبت پیگیری جدید را می‌دهیم
            
            # 5. اعتبارسنجی وجود مسئول پیگیری
            staff_id = data.get('staff_id')
            if not staff_id:
                raise ValidationError("مسئول پیگیری باید انتخاب شود")
            
            staff = self.staff_dal.get_by_id(staff_id)
            if not staff:
                raise ValidationError("مسئول پیگیری انتخاب شده وجود ندارد")
            
            # 6. ایجاد مدل FollowUp
            followup = FollowUp()
            followup.intervention_id = intervention_id
            followup.staff_id = staff_id
            # ===== اصلاح (بازرسی ششم) =====
            # الگوی data.get('x', '').strip() وقتی کلید وجود داشت و
            # مقدارش None بود، AttributeError می‌داد و کل ثبت پیگیری
            # با پیام «'NoneType' object has no attribute 'strip'»
            # شکست می‌خورد. حالا clean_text/clean_date هر دو حالت را
            # پوشش می‌دهند و تاریخ هم به فرمت یکدست yyyy/MM/dd
            # نرمال می‌شود.
            followup.date = self.clean_date(data.get('date'), '')
            followup.method = self.clean_text(data.get('method'))
            followup.description = self.clean_text(data.get('description'))
            followup.status = data.get('status') or FollowUp.STATUS_PENDING
            followup.next_action_date = self.clean_date(data.get('next_action_date'))
            followup.result_type = self.clean_text(data.get('result_type'), None)
            followup.result_description = self.clean_text(data.get('result_description'), None)
            
            # 7. اعتبارسنجی مدل
            errors = followup.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            # 8. اگر وضعیت "انجام شده" است، تاریخ اقدام بعدی را پاک کن
            if followup.status == FollowUp.STATUS_DONE:
                followup.next_action_date = None
            
            # 9. ذخیره در دیتابیس
            created_followup = self.followup_dal.create(followup)
            
            # 10. اگر پیگیری با وضعیت "انجام شده" ثبت شد، وضعیت مداخله را به‌روز کن
            if followup.status == FollowUp.STATUS_DONE:
                self._update_intervention_status_on_completion(intervention_id, user_id)
            
            # 11. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='create',
                entity_type='followup',
                entity_id=created_followup.id,
                new_value={'followup_id': created_followup.id, 'intervention_id': intervention_id},
                ip_address=ip_address
            )
            
            self.logger.info(f"پیگیری با ID {created_followup.id} برای مداخله {intervention_id} ایجاد شد.")
            return created_followup
        
        return self.execute_in_transaction(_create)
    
    def update_followup(self, followup_id, data, user_id=None, ip_address=None):
        """
        به‌روزرسانی پیگیری
        
        Args:
            followup_id: شناسه پیگیری
            data: دیکشنری شامل اطلاعات جدید
            user_id: شناسه کاربر ویرایش‌کننده
            ip_address: آدرس IP کاربر
            
        Returns:
            FollowUp: پیگیری به‌روزرسانی شده
            
        Raises:
            ServiceError: در صورت بروز خطا
            ValidationError: در صورت عدم اعتبار داده‌ها
        """
        def _update():
            # 1. دریافت پیگیری موجود
            followup = self.followup_dal.get_by_id(followup_id)
            if not followup:
                raise ServiceError(f"پیگیری با شناسه {followup_id} یافت نشد.")
            
            # 2. ذخیره مقدار قبلی برای Audit
            old_value = {
                'id': followup.id,
                'intervention_id': followup.intervention_id,
                'staff_id': followup.staff_id,
                'date': followup.date,
                'status': followup.status,
                'result_type': followup.result_type
            }
            
            # 3. اعتبارسنجی داده‌ها
            self._validate_followup_data(data, is_update=True)
            
            # 4. به‌روزرسانی فیلدها
            intervention_id = data.get('intervention_id')
            if intervention_id and intervention_id != followup.intervention_id:
                # بررسی وجود مداخله جدید
                intervention = self.intervention_dal.get_by_id(intervention_id)
                if not intervention:
                    raise ValidationError("مداخله انتخاب شده وجود ندارد")
                followup.intervention_id = intervention_id
            
            followup.staff_id = data.get('staff_id', followup.staff_id)
            # ===== اصلاح (بازرسی ششم): None-safe + یکدست‌سازی تاریخ =====
            followup.date = self.clean_date(data.get('date'), followup.date or '')
            followup.method = self.clean_text(data.get('method'), followup.method)
            followup.description = self.clean_text(data.get('description'), followup.description)
            followup.status = data.get('status', followup.status)
            followup.next_action_date = self.clean_date(
                data.get('next_action_date'), followup.next_action_date
            )
            followup.result_type = self.clean_text(data.get('result_type'), followup.result_type)
            followup.result_description = self.clean_text(
                data.get('result_description'), followup.result_description
            )
            
            # 5. اگر وضعیت "انجام شده" است، تاریخ اقدام بعدی را پاک کن
            if followup.status == FollowUp.STATUS_DONE:
                followup.next_action_date = None
            
            # 6. اعتبارسنجی مدل
            errors = followup.validate()
            if errors:
                raise ValidationError("\n".join(errors))
            
            # 7. ذخیره در دیتابیس
            updated_followup = self.followup_dal.update(followup)
            
            # 8. اگر وضعیت پیگیری تغییر کرده و به "انجام شده" رسیده، وضعیت مداخله را به‌روز کن
            if followup.status == FollowUp.STATUS_DONE and old_value['status'] != FollowUp.STATUS_DONE:
                self._update_intervention_status_on_completion(followup.intervention_id, user_id)
            
            # 9. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='edit',
                entity_type='followup',
                entity_id=followup_id,
                old_value=old_value,
                new_value={'id': updated_followup.id, 'updated': True},
                ip_address=ip_address
            )
            
            self.logger.info(f"پیگیری با ID {followup_id} ویرایش شد.")
            return updated_followup
        
        return self.execute_in_transaction(_update)
    
    def delete_followup(self, followup_id, user_id=None, ip_address=None):
        """
        حذف پیگیری
        
        Args:
            followup_id: شناسه پیگیری
            user_id: شناسه کاربر حذف‌کننده
            ip_address: آدرس IP کاربر
            
        Returns:
            bool: آیا حذف موفقیت‌آمیز بود؟
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        def _delete():
            # 1. بررسی وجود پیگیری
            followup = self.followup_dal.get_by_id(followup_id)
            if not followup:
                raise ServiceError(f"پیگیری با شناسه {followup_id} یافت نشد.")
            
            old_value = {
                'id': followup.id,
                'intervention_id': followup.intervention_id,
                'staff_id': followup.staff_id,
                'date': followup.date,
                'status': followup.status
            }
            
            # 2. حذف از دیتابیس
            result = self.followup_dal.delete(followup_id)
            
            # 3. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='delete_soft',
                entity_type='followup',
                entity_id=followup_id,
                old_value=old_value,
                ip_address=ip_address
            )
            
            self.logger.info(f"پیگیری با ID {followup_id} حذف شد.")
            return result
        
        return self.execute_in_transaction(_delete)
    
    def get_followup(self, followup_id):
        """
        دریافت پیگیری با شناسه
        
        Args:
            followup_id: شناسه پیگیری
            
        Returns:
            FollowUp: پیگیری
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        try:
            followup = self.followup_dal.get_by_id(followup_id)
            if not followup:
                raise ServiceError(f"پیگیری با شناسه {followup_id} یافت نشد.")
            
            # افزودن اطلاعات تکمیلی
            self._enrich_followup(followup)
            
            return followup
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیگیری: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_followups_by_intervention(self, intervention_id):
        """
        دریافت پیگیری‌های یک مداخله
        
        Args:
            intervention_id: شناسه مداخله
            
        Returns:
            list: لیست پیگیری‌ها
        """
        try:
            followups = self.followup_dal.get_by_intervention(intervention_id)
            for follow in followups:
                self._enrich_followup(follow)
            return followups
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیگیری‌های مداخله: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_followups_by_student(self, student_id, year_id=None):
        """
        دریافت پیگیری‌های یک دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            year_id: شناسه سال تحصیلی (اختیاری)
            
        Returns:
            list: لیست پیگیری‌ها
            
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
            
            followups = self.followup_dal.get_by_student_profile(profile.id)
            
            for follow in followups:
                self._enrich_followup(follow)
            
            return followups
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیگیری‌های دانش‌آموز: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_followups_by_teacher(self, teacher_id, year_id=None):
        """
        دریافت پیگیری‌های یک معلم
        
        Args:
            teacher_id: شناسه معلم
            year_id: شناسه سال تحصیلی (اختیاری)
            
        Returns:
            list: لیست پیگیری‌ها
            
        Raises:
            ServiceError: در صورت بروز خطا
        """
        try:
            # دریافت همه پیگیری‌ها
            followups = self.followup_dal.get_all(academic_year_id=year_id, staff_id=teacher_id)
            
            # فیلتر بر اساس معلم
            followups = [f for f in followups if f.staff_id == teacher_id]
            
            # فیلتر بر اساس سال (اگر مشخص شده باشد)
            if year_id:
                # خوانش دسته‌ای مداخله‌ها و پرونده‌ها (رفع N+1؛ معناشناسی قبلی حفظ شده)
                intervention_map = self.intervention_dal.get_by_ids(
                    f.intervention_id for f in followups)
                profile_map = self.profile_dal.get_by_ids(
                    i.student_profile_id for i in intervention_map.values())
                filtered = []
                for follow in followups:
                    intervention = intervention_map.get(follow.intervention_id)
                    if intervention:
                        profile = profile_map.get(intervention.student_profile_id)
                        if profile and profile.academic_year_id == year_id:
                            filtered.append(follow)
                followups = filtered
            
            for follow in followups:
                self._enrich_followup(follow)
            
            return followups
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیگیری‌های معلم: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_all_followups(self, limit=None, year_id=None):
        """
        دریافت همه پیگیری‌ها
        
        Args:
            limit: تعداد محدود (اختیاری)
            
        Returns:
            list: لیست پیگیری‌ها
        """
        try:
            followups = self.followup_dal.get_all(limit=limit, academic_year_id=year_id)
            for follow in followups:
                self._enrich_followup(follow)
            return followups
        except Exception as e:
            self.logger.error(f"خطا در دریافت همه پیگیری‌ها: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_pending_followups(self):
        """
        دریافت پیگیری‌های در انتظار
        
        Returns:
            list: لیست پیگیری‌های در انتظار
        """
        try:
            followups = self.followup_dal.get_pending()
            for follow in followups:
                self._enrich_followup(follow)
            return followups
        except Exception as e:
            self.logger.error(f"خطا در دریافت پیگیری‌های در انتظار: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def update_status(self, followup_id, new_status, user_id=None, ip_address=None):
        """
        به‌روزرسانی وضعیت پیگیری
        
        Args:
            followup_id: شناسه پیگیری
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
            # 1. بررسی وجود پیگیری
            followup = self.followup_dal.get_by_id(followup_id)
            if not followup:
                raise ServiceError(f"پیگیری با شناسه {followup_id} یافت نشد.")
            
            # 2. اعتبارسنجی وضعیت
            if new_status not in self.VALID_STATUSES:
                raise ValidationError(f"وضعیت '{new_status}' نامعتبر است.")
            
            # 3. ذخیره مقدار قبلی
            old_value = {'status': followup.status}
            
            # 4. به‌روزرسانی وضعیت
            result = self.followup_dal.update_status(followup_id, new_status)
            
            # 5. اگر وضعیت به "انجام شده" تغییر کرد، تاریخ اقدام بعدی را پاک کن
            if new_status == FollowUp.STATUS_DONE:
                followup.next_action_date = None
                self.followup_dal.update(followup)
            
            # 6. اگر وضعیت به "انجام شده" رسید، وضعیت مداخله را به‌روز کن
            if new_status == FollowUp.STATUS_DONE:
                self._update_intervention_status_on_completion(followup.intervention_id, user_id)
            
            # 7. ثبت Audit Log
            self.log_audit(
                user_id=user_id,
                action='edit',
                entity_type='followup',
                entity_id=followup_id,
                old_value=old_value,
                new_value={'status': new_status},
                ip_address=ip_address
            )
            
            self.logger.info(f"وضعیت پیگیری {followup_id} به {new_status} تغییر کرد.")
            return result
        
        return self.execute_in_transaction(_update_status)
    
    def get_followups_summary(self, student_id, year_id=None):
        """
        دریافت خلاصه آماری پیگیری‌های یک دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            year_id: شناسه سال تحصیلی (اختیاری)
            
        Returns:
            dict: خلاصه آماری
        """
        try:
            followups = self.get_followups_by_student(student_id, year_id)
            
            if not followups:
                return {
                    'total': 0,
                    'pending': 0,
                    'done': 0,
                    'continued': 0,
                    'closed': 0,
                    'cancelled': 0,
                    'overdue': 0
                }
            
            total = len(followups)
            pending = sum(1 for f in followups if f.status == 'pending')
            done = sum(1 for f in followups if f.status == 'done')
            continued = sum(1 for f in followups if f.status == 'continued')
            closed = sum(1 for f in followups if f.status == 'closed')
            cancelled = sum(1 for f in followups if f.status == 'cancelled')
            
            # محاسبه پیگیری‌های معوق (تاریخ اقدام بعدی گذشته)
            overdue = 0
            import jdatetime
            try:
                today = jdatetime.date.today()
                today_str = f"{today.year}/{today.month:02d}/{today.day:02d}"
                for f in followups:
                    if f.status == 'pending' and f.next_action_date and f.next_action_date < today_str:
                        overdue += 1
            except Exception as _exc:
                self.logger.debug(
                    f"خطای غیرمنتظره در {self.__class__.__name__}: {_exc}"
                )
            
            return {
                'total': total,
                'pending': pending,
                'done': done,
                'continued': continued,
                'closed': closed,
                'cancelled': cancelled,
                'overdue': overdue,
                'followups': followups
            }
        except Exception as e:
            self.logger.error(f"خطا در دریافت خلاصه پیگیری‌ها: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {e!s}")
    
    def get_available_interventions_for_followup(self, student_id):
        """
        دریافت مداخلات بدون پیگیری برای یک دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            
        Returns:
            list: لیست مداخلات بدون پیگیری
        """
        try:
            profile = self.profile_dal.get_active_by_student(student_id)
            if not profile:
                return []
            
            # دریافت همه مداخلات دانش‌آموز
            all_interventions = self.intervention_dal.get_by_student_profile(profile.id)
            
            # دریافت شناسه مداخلاتی که پیگیری دارند
            followups = self.followup_dal.get_all()
            intervention_ids_with_followup = set()
            for f in followups:
                if f.intervention_id:
                    intervention_ids_with_followup.add(f.intervention_id)
            
            # فیلتر کردن مداخلات بدون پیگیری
            interventions_without_followup = [
                inter for inter in all_interventions 
                if inter.id not in intervention_ids_with_followup
            ]
            
            return interventions_without_followup
        except Exception as e:
            self.logger.error(f"خطا در دریافت مداخلات بدون پیگیری: {e}")
            return []
    
    def _validate_followup_data(self, data, is_update=False):
        """
        اعتبارسنجی داده‌های پیگیری
        
        Args:
            data: دیکشنری داده‌ها
            is_update: آیا در حالت ویرایش هستیم؟
            
        Raises:
            ValidationError: در صورت عدم اعتبار
        """
        errors = []

        # ===== اصلاح (بازرسی ششم) =====
        # در حالت ویرایش، فقط کلیدهایی که واقعاً فرستاده شده‌اند
        # اعتبارسنجی می‌شوند. نسخه قبلی برای یک ویرایش جزئی (مثلاً
        # فقط تغییر وضعیت) هم «تاریخ پیگیری» و «مسئول پیگیری» را
        # اجباری می‌دانست و ویرایش را رد می‌کرد.
        # مقدار None هم دیگر باعث AttributeError نمی‌شود.
        def provided(key):
            return (not is_update) or (key in data)

        # بررسی مداخله (در حالت ایجاد اجباری است)
        if not is_update and not data.get('intervention_id'):
            errors.append("مداخله باید انتخاب شود")

        # بررسی مسئول پیگیری
        if provided('staff_id'):
            if data.get('staff_id') is None:
                errors.append("مسئول پیگیری باید انتخاب شود")
            elif data.get('staff_id') and data.get('staff_id') <= 0:
                errors.append("مسئول پیگیری نامعتبر است")

        # بررسی تاریخ پیگیری — قاعدهٔ یکسان: نرمال‌سازی، بعد اعتبارسنجی
        if provided('date'):
            _norm, _err = self.check_date(
                data.get('date'), "تاریخ پیگیری", required=True)
            if _err:
                errors.append(_err)

        # بررسی تاریخ اقدام بعدی (اختیاری)
        if provided('next_action_date'):
            _norm, _err = self.check_date(
                data.get('next_action_date'), "تاریخ اقدام بعدی")
            if _err:
                errors.append(_err)

        # بررسی وضعیت
        if provided('status'):
            status = data.get('status') or 'pending'
            if status not in self.VALID_STATUSES:
                errors.append(f"وضعیت '{status}' نامعتبر است")

        # بررسی نوع نتیجه (اگر وارد شده باشد)
        if provided('result_type'):
            result_type = self.clean_text(data.get('result_type'))
            if result_type and result_type not in self.VALID_RESULT_TYPES:
                errors.append(f"نوع نتیجه '{result_type}' نامعتبر است")
        
        if errors:
            raise ValidationError("\n".join(errors))
    
    def _update_intervention_status_on_completion(self, intervention_id, user_id=None):
        """
        به‌روزرسانی وضعیت مداخله پس از تکمیل پیگیری
        
        Args:
            intervention_id: شناسه مداخله
            user_id: شناسه کاربر (برای Audit)
        """
        try:
            intervention = self.intervention_dal.get_by_id(intervention_id)
            if not intervention:
                return
            
            # اگر مداخله در وضعیت 'in_progress' یا 'planned' است، آن را به 'completed' تغییر بده
            if intervention.status in ['planned', 'in_progress']:
                # بررسی اینکه آیا همه پیگیری‌های این مداخله انجام شده‌اند
                followups = self.followup_dal.get_by_intervention(intervention_id)
                pending_followups = [f for f in followups if f.status == 'pending']
                
                if not pending_followups:
                    self.intervention_dal.update_status(intervention_id, 'completed')
                    self.logger.info(f"وضعیت مداخله {intervention_id} به 'completed' تغییر یافت.")
        except Exception as e:
            self.logger.warning(f"خطا در به‌روزرسانی وضعیت مداخله: {e}")
    
    def _enrich_followup(self, followup):
        """
        افزودن اطلاعات تکمیلی به پیگیری
        
        Args:
            followup: شیء FollowUp
        """
        # افزودن اطلاعات مداخله و دانش‌آموز
        try:
            intervention = self.intervention_dal.get_by_id(followup.intervention_id)
            if intervention:
                followup.intervention_type = intervention.type
                followup.intervention_type_display = intervention.type_display
                followup.intervention_date = intervention.date
                
                profile = self.profile_dal.get_by_id(intervention.student_profile_id)
                if profile:
                    student = self.student_dal.get_by_id(profile.student_id)
                    if student:
                        followup.student_name = student.full_name
                        followup.student_id = profile.student_id
        except Exception as e:
            self.logger.warning(f"خطا در افزودن اطلاعات مداخله: {e}")
        
        # افزودن نام مسئول
        try:
            staff = self.staff_dal.get_by_id(followup.staff_id)
            if staff:
                followup.staff_name = staff.full_name
                followup.staff_role = staff.role
        except Exception as e:
            self.logger.warning(f"خطا در افزودن نام مسئول: {e}")
        
        # تنظیم نام‌های پیش‌فرض
        if not hasattr(followup, 'student_name') or not followup.student_name:
            followup.student_name = "نامشخص"
        if not hasattr(followup, 'staff_name') or not followup.staff_name:
            followup.staff_name = "نامشخص"
        if not hasattr(followup, 'intervention_type_display') or not followup.intervention_type_display:
            followup.intervention_type_display = "نامشخص"
    
    def validate_followup(self, data):
        """
        اعتبارسنجی داده‌های پیگیری (برای استفاده در View)
        
        Args:
            data: دیکشنری داده‌ها
            
        Returns:
            tuple: (is_valid, errors_list)
        """
        try:
            self._validate_followup_data(data)
            return True, []
        except ValidationError as e:
            self.logger.debug(f"خطای مدیریت‌شده در validate_followup (مسیر جایگزین): {e}")
            return False, str(e).split('\n')
        except Exception as e:
            self.logger.debug(f"خطای مدیریت‌شده در validate_followup (مسیر جایگزین): {e}")
            return False, [str(e)]

    def search_followups(self, search_term, limit=None, year_id=None):
        """
        جستجوی پیگیری‌ها بر اساس متن
        
        Args:
            search_term: عبارت جستجو
            limit: تعداد محدود
            
        Returns:
            list: لیست پیگیری‌ها مطابق با جستجو
        """
        try:
            followups = self.followup_dal.search(search_term, limit, academic_year_id=year_id)
            for follow in followups:
                self._enrich_followup(follow)
            return followups
        except Exception as e:
            self.logger.error(f"خطا در جستجوی پیگیری‌ها: {e}")
            raise ServiceError(f"خطا در جستجو: {e!s}")
    
    def search_followups_by_student(self, student_id, search_term, year_id=None):
        """
        جستجوی پیگیری‌های یک دانش‌آموز بر اساس متن
        
        Args:
            student_id: شناسه دانش‌آموز
            search_term: عبارت جستجو
            
        Returns:
            list: لیست پیگیری‌ها مطابق با جستجو
        """
        try:
            followups = self.followup_dal.search_by_student(student_id, search_term, academic_year_id=year_id)
            for follow in followups:
                self._enrich_followup(follow)
            return followups
        except Exception as e:
            self.logger.error(f"خطا در جستجوی پیگیری‌های دانش‌آموز: {e}")
            raise ServiceError(f"خطا در جستجو: {e!s}")
    
    def search_followups_by_teacher(self, teacher_id, search_term, year_id=None):
        """
        جستجوی پیگیری‌های یک معلم بر اساس متن
        
        Args:
            teacher_id: شناسه معلم
            search_term: عبارت جستجو
            
        Returns:
            list: لیست پیگیری‌ها مطابق با جستجو
        """
        try:
            followups = self.followup_dal.search_by_teacher(teacher_id, search_term, academic_year_id=year_id)
            for follow in followups:
                self._enrich_followup(follow)
            return followups
        except Exception as e:
            self.logger.error(f"خطا در جستجوی پیگیری‌های معلم: {e}")
            raise ServiceError(f"خطا در جستجو: {e!s}")