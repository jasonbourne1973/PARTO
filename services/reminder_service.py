"""
سرویس مدیریت یادآوری پیگیری‌ها
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.student_dal import StudentDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.staff_dal import StaffDAL
from datetime import datetime
import jdatetime


class ReminderService:
    """سرویس یادآوری پیگیری‌ها"""
    
    def __init__(self):
        self.followup_dal = FollowUpDAL()
        self.intervention_dal = InterventionDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
    
    def get_pending_followups(self):
        """دریافت پیگیری‌های در انتظار"""
        try:
            return self.followup_dal.get_pending()
        except Exception as e:
            print(f"خطا در دریافت پیگیری‌های در انتظار: {e}")
            return []
    
    def get_overdue_followups(self):
        """دریافت پیگیری‌های معوق (تاریخ اقدام بعدی گذشته است)"""
        try:
            all_pending = self.followup_dal.get_pending()
            overdue = []
            
            # دریافت تاریخ امروز شمسی
            try:
                today = jdatetime.date.today()
                today_str = f"{today.year}/{today.month:02d}/{today.day:02d}"
            except:
                today_str = datetime.now().strftime("%Y/%m/%d")
            
            for followup in all_pending:
                if followup.next_action_date:
                    # مقایسه تاریخ‌ها
                    if followup.next_action_date < today_str:
                        overdue.append(followup)
            
            return overdue
        except Exception as e:
            print(f"خطا در دریافت پیگیری‌های معوق: {e}")
            return []
    
    def get_followups_due_soon(self, days=3):
        """دریافت پیگیری‌هایی که تا چند روز آینده موعد دارند"""
        try:
            all_pending = self.followup_dal.get_pending()
            due_soon = []
            
            # دریافت تاریخ امروز شمسی
            try:
                today = jdatetime.date.today()
                today_str = f"{today.year}/{today.month:02d}/{today.day:02d}"
            except:
                today_str = datetime.now().strftime("%Y/%m/%d")
            
            for followup in all_pending:
                if followup.next_action_date:
                    # محاسبه تفاوت تاریخ‌ها (ساده)
                    if followup.next_action_date > today_str:
                        due_soon.append(followup)
            
            return due_soon[:10]  # حداکثر 10 مورد
        except Exception as e:
            print(f"خطا در دریافت پیگیری‌های نزدیک: {e}")
            return []
    
    def get_reminder_summary(self):
        """دریافت خلاصه وضعیت پیگیری‌ها"""
        pending = self.get_pending_followups()
        overdue = self.get_overdue_followups()
        due_soon = self.get_followups_due_soon()
        
        # دریافت اطلاعات تکمیلی برای هر پیگیری
        detailed_pending = []
        for f in pending:
            detail = self._get_followup_detail(f)
            if detail:
                detailed_pending.append(detail)
        
        detailed_overdue = []
        for f in overdue:
            detail = self._get_followup_detail(f)
            if detail:
                detail['is_overdue'] = True
                detailed_overdue.append(detail)
        
        return {
            'total_pending': len(pending),
            'overdue_count': len(overdue),
            'due_soon_count': len(due_soon),
            'pending_list': detailed_pending,
            'overdue_list': detailed_overdue,
            'has_reminder': len(pending) > 0
        }
    
    def _get_followup_detail(self, followup):
        """دریافت اطلاعات کامل یک پیگیری"""
        try:
            # دریافت مداخله
            intervention = self.intervention_dal.get_by_id(followup.intervention_id)
            if not intervention:
                return None
            
            # دریافت دانش‌آموز
            profile = self.profile_dal.get_by_id(intervention.student_profile_id)
            if not profile:
                return None
            
            student = self.student_dal.get_by_id(profile.student_id)
            if not student:
                return None
            
            # دریافت مسئول
            staff = self.staff_dal.get_by_id(followup.staff_id) if followup.staff_id else None
            
            return {
                'id': followup.id,
                'student_name': student.full_name,
                'student_id': student.id,
                'intervention_type': intervention.type_display,
                'intervention_date': intervention.date,
                'followup_date': followup.date,
                'next_action_date': followup.next_action_date,
                'status': followup.status,
                'status_display': followup.status_display,
                'description': followup.description,
                'staff_name': staff.full_name if staff else 'نامشخص',
                'staff_id': followup.staff_id,
                'is_overdue': False,
            }
        except Exception as e:
            print(f"خطا در دریافت جزئیات پیگیری: {e}")
            return None