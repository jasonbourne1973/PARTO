"""
سرویس داشبورد مدیریتی - نسخه اصلاح شده بدون مقایسه و رتبه‌بندی
با متدهای تحلیلی پیشرفته
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jdatetime

from dal.academic_year_dal import AcademicYearDAL
from dal.audit_log_dal import AuditLogDAL
from dal.competency_dal import CompetencyDAL
from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from services.base_service import BaseService
from services.trend_analysis_service import TrendAnalysisService
from utils.error_handler import ServiceError
from utils.logger import get_logger


class DashboardService(BaseService):
    """
    سرویس داشبورد مدیریتی - بدون مقایسه و رتبه‌بندی
    
    این سرویس فقط شاخص‌های مربوط به روند و وضعیت پرونده را نمایش می‌دهد.
    هیچ مقایسه‌ای بین دانش‌آموزان انجام نمی‌شود.
    """
    
    def __init__(self):
        super().__init__()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.staff_dal = StaffDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        self.audit_log_dal = AuditLogDAL()
        self.competency_dal = CompetencyDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    def get_dashboard_data(self, teacher_id=None, year_id=None):
        """
        دریافت کامل داده‌های داشبورد - بدون مقایسه و رتبه‌بندی
        
        Args:
            teacher_id: شناسه معلم برای فیلتر (اختیاری)
            year_id: شناسه سال تحصیلی (اختیاری)
            
        Returns:
            dict: تمام داده‌های مورد نیاز داشبورد
        """
        try:
            # دریافت سال تحصیلی
            if year_id:
                year = self.academic_year_dal.get_by_id(year_id)
            else:
                year = self.academic_year_dal.get_active()
            
            # ===== ۱. آمار کلی (فقط تعداد) =====
            stats = self._get_general_stats(teacher_id, year_id)
            
            # ===== ۲. شاخص‌های مدیریتی (بدون مقایسه) =====
            management_indicators = self._get_management_indicators(teacher_id, year_id)
            
            # ===== ۳. روند ثبت مشاهدات (بر اساس خود دانش‌آموزان) =====
            trend_data = self._get_observation_trend(teacher_id, year_id)
            
            # ===== ۴. وضعیت سال تحصیلی =====
            year_status = self._get_year_status(year)
            
            # ===== ۵. آمار معلم (اگر انتخاب شده باشد) =====
            teacher_stats = None
            if teacher_id:
                teacher_stats = self._get_teacher_stats(teacher_id, year_id)
            
            # ===== ۶. یادآوری‌های پیگیری (بدون رتبه‌بندی) =====
            reminders = self._get_reminders(teacher_id)
            
            # ===== ۷. فعالیت‌های اخیر =====
            recent_activities = self._get_recent_activities()
            
            # ===== ۸. داده‌های تحلیلی جدید =====
            analytics_data = self._get_analytics_data(teacher_id, year_id)
            
            return {
                'general_stats': stats,
                'management_indicators': management_indicators,
                'trend_data': trend_data,
                'year_status': year_status,
                'teacher_stats': teacher_stats,
                'reminders': reminders,
                'recent_activities': recent_activities,
                'analytics': analytics_data
            }
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت داده‌های داشبورد: {e}")
            raise ServiceError(f"خطا در دریافت اطلاعات: {str(e)}")
    
    # ============================================================
    # متدهای جدید تحلیلی
    # ============================================================
    
    def _get_analytics_data(self, teacher_id=None, year_id=None):
        """
        دریافت داده‌های تحلیلی برای داشبورد
        
        Args:
            teacher_id: شناسه معلم (اختیاری)
            year_id: شناسه سال تحصیلی (اختیاری)
        
        Returns:
            dict: داده‌های تحلیلی
        """
        try:
            # ===== اصلاح =====
            # قبلاً پارامتر teacher_id پذیرفته می‌شد ولی هرگز به کوئری‌ها
            # پاس داده نمی‌شد. نتیجه: وقتی کاربر در داشبورد یک معلم خاص را
            # انتخاب می‌کرد، نیمی از پنل‌ها (نمودارها و داده‌های تحلیلی)
            # آمار «کل مدرسه» را نشان می‌دادند بدون هیچ هشداری. حالا
            # فیلتر معلم به همهٔ کوئری‌های این بخش اعمال می‌شود.
            #
            # برای جدول‌های observations/interventions/followups فیلتر
            # مستقیم روی staff_id است؛ برای دانش‌آموزان، نسبت معلم-دانش‌آموز
            # از جدول teacher_assignments گرفته می‌شود.

            # دریافت توزیع مشاهدات
            obs_distribution = self.observation_dal.get_observations_distribution_by_type(
                staff_id=teacher_id
            )
            
            # دریافت توزیع دانش‌آموزان بر اساس پایه
            grade_distribution = self.student_dal.get_student_distribution_by_grade(
                year_id, staff_id=teacher_id
            )
            
            # دریافت توزیع مداخلات
            inter_status = self.intervention_dal.get_interventions_distribution_by_status(
                staff_id=teacher_id
            )
            
            # دریافت توزیع پیگیری‌ها
            follow_status = self.followup_dal.get_followups_distribution_by_status(
                staff_id=teacher_id
            )
            
            # دریافت تعداد پیگیری‌های معوق
            overdue_count = self.followup_dal.get_overdue_followups_count(
                staff_id=teacher_id
            )
            
            # دریافت نرخ موفقیت مداخلات
            inter_success = self.intervention_dal.get_intervention_success_rate(
                staff_id=teacher_id
            )
            
            # دریافت نرخ تکمیل پیگیری‌ها
            follow_completion = self.followup_dal.get_followup_completion_rate(
                staff_id=teacher_id
            )
            
            # دریافت پرکاربردترین شایستگی‌ها
            top_competencies = self.observation_dal.get_observations_by_competency(
                limit=5, staff_id=teacher_id
            )
            
            # دریافت دانش‌آموزان بدون مشاهده
            students_without_obs = self.student_dal.get_students_without_observations(
                year_id, staff_id=teacher_id
            )
            
            return {
                'observation_distribution': obs_distribution,
                'grade_distribution': grade_distribution,
                'intervention_status': inter_status,
                'followup_status': follow_status,
                'overdue_count': overdue_count,
                'intervention_success_rate': inter_success,
                'followup_completion_rate': follow_completion,
                'top_competencies': top_competencies,
                'students_without_observation': len(students_without_obs),
                'students_without_observation_list': students_without_obs[:5]
            }
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت داده‌های تحلیلی: {e}")
            return {
                'observation_distribution': {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0},
                'grade_distribution': [],
                'intervention_status': {'planned': 0, 'in_progress': 0, 'completed': 0, 'cancelled': 0, 'total': 0},
                'followup_status': {'pending': 0, 'done': 0, 'continued': 0, 'closed': 0, 'cancelled': 0, 'total': 0},
                'overdue_count': 0,
                'intervention_success_rate': {'total': 0, 'completed': 0, 'success_rate': 0},
                'followup_completion_rate': {'total': 0, 'completed': 0, 'completion_rate': 0},
                'top_competencies': [],
                'students_without_observation': 0,
                'students_without_observation_list': []
            }
    
    def _get_general_stats(self, teacher_id=None, year_id=None):
        """دریافت آمار کلی - فقط تعداد و بدون مقایسه"""
        try:
            if teacher_id:
                assignments = self.assignment_dal.get_by_teacher(teacher_id, year_id)
                student_ids = [a.student_id for a in assignments if a.is_active == 1]
                students = [self.student_dal.get_by_id(sid) for sid in student_ids if sid]
            else:
                students = self.student_dal.get_all()
            
            if teacher_id:
                observations = self.observation_dal.get_all()
                observations = [o for o in observations if o.staff_id == teacher_id]
                if year_id:
                    filtered = []
                    for o in observations:
                        profile = self.profile_dal.get_by_id(o.student_profile_id)
                        if profile and profile.academic_year_id == year_id:
                            filtered.append(o)
                    observations = filtered
            else:
                observations = self.observation_dal.get_all()
            
            if teacher_id:
                interventions = self.intervention_dal.get_all()
                interventions = [i for i in interventions if i.staff_id == teacher_id]
                if year_id:
                    filtered = []
                    for i in interventions:
                        profile = self.profile_dal.get_by_id(i.student_profile_id)
                        if profile and profile.academic_year_id == year_id:
                            filtered.append(i)
                    interventions = filtered
            else:
                interventions = self.intervention_dal.get_all()
            
            if teacher_id:
                followups = self.followup_dal.get_all()
                followups = [f for f in followups if f.staff_id == teacher_id]
            else:
                followups = self.followup_dal.get_all()
            
            positive = sum(1 for o in observations if o.behavior_type == "مثبت")
            negative = sum(1 for o in observations if o.behavior_type == "منفی")
            neutral = len(observations) - positive - negative
            
            pending = sum(1 for f in followups if f.status == "pending")
            
            active_profiles = 0
            for student in students:
                if student:
                    profile = self.profile_dal.get_active_by_student(student.id)
                    if profile:
                        active_profiles += 1
            
            return {
                'students_count': len(students),
                'active_profiles': active_profiles,
                'observations_count': len(observations),
                'interventions_count': len(interventions),
                'followups_count': len(followups),
                'positive_count': positive,
                'negative_count': negative,
                'neutral_count': neutral,
                'pending_followups': pending,
                'has_data': len(observations) > 0 or len(interventions) > 0
            }
        except Exception as e:
            self.logger.error(f"خطا در دریافت آمار کلی: {e}")
            return {
                'students_count': 0,
                'active_profiles': 0,
                'observations_count': 0,
                'interventions_count': 0,
                'followups_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'pending_followups': 0,
                'has_data': False
            }
    
    def _get_management_indicators(self, teacher_id=None, year_id=None):
        """دریافت شاخص‌های مدیریتی - بدون مقایسه و رتبه‌بندی"""
        stats = self._get_general_stats(teacher_id, year_id)
        
        positive_ratio = 0
        if stats['observations_count'] > 0:
            positive_ratio = (stats['positive_count'] / stats['observations_count']) * 100
        
        pending_ratio = 0
        if stats['followups_count'] > 0:
            pending_ratio = (stats['pending_followups'] / stats['followups_count']) * 100
        
        avg_obs_per_student = 0
        if stats['students_count'] > 0:
            avg_obs_per_student = stats['observations_count'] / stats['students_count']
        
        return {
            'positive_ratio': round(positive_ratio, 1),
            'pending_ratio': round(pending_ratio, 1),
            'avg_obs_per_student': round(avg_obs_per_student, 1),
            'status': self._get_overall_status(positive_ratio, pending_ratio)
        }
    
    def _get_overall_status(self, positive_ratio, pending_ratio):
        """تعیین وضعیت کلی - بدون مقایسه"""
        if positive_ratio >= 60 and pending_ratio <= 20:
            return "مطلوب"
        elif positive_ratio >= 40 and pending_ratio <= 40:
            return "متوسط"
        else:
            return "نیازمند توجه"
    
    def _get_observation_trend(self, teacher_id=None, year_id=None):
        """دریافت روند ثبت مشاهدات - بدون مقایسه با دیگران"""
        try:
            today = jdatetime.date.today()
            current_month = today.month
            current_year = today.year
            
            months_data = []
            for i in range(6):
                month = current_month - i
                year = current_year
                if month <= 0:
                    month += 12
                    year -= 1
                
                month_key = f"{year}/{month:02d}"
                month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                               "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
                label = month_names[month-1] if 1 <= month <= 12 else str(month)
                
                months_data.append({
                    'month': month_key,
                    'label': label,
                    'count': 0,
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0
                })
            
            if teacher_id:
                observations = self.observation_dal.get_all()
                observations = [o for o in observations if o.staff_id == teacher_id]
                if year_id:
                    filtered = []
                    for o in observations:
                        profile = self.profile_dal.get_by_id(o.student_profile_id)
                        if profile and profile.academic_year_id == year_id:
                            filtered.append(o)
                    observations = filtered
            else:
                observations = self.observation_dal.get_all()
            
            for obs in observations:
                if obs.observation_date and len(obs.observation_date) >= 7:
                    obs_month = obs.observation_date[:7]
                    for month_data in months_data:
                        if month_data['month'] == obs_month:
                            month_data['count'] += 1
                            if obs.behavior_type == "مثبت":
                                month_data['positive'] += 1
                            elif obs.behavior_type == "منفی":
                                month_data['negative'] += 1
                            else:
                                month_data['neutral'] += 1
                            break
            
            months_data.reverse()
            
            return {
                'months': [m['month'] for m in months_data],
                'labels': [m['label'] for m in months_data],
                'counts': [m['count'] for m in months_data],
                'positive': [m['positive'] for m in months_data],
                'negative': [m['negative'] for m in months_data],
                'neutral': [m['neutral'] for m in months_data],
                'total': sum(m['count'] for m in months_data)
            }
            
        except Exception as e:
            self.logger.error(f"خطا در محاسبه روند: {e}")
            return {'months': [], 'labels': [], 'counts': [], 'positive': [], 'negative': [], 'neutral': [], 'total': 0}
    
    def _get_year_status(self, year):
        """دریافت وضعیت سال تحصیلی"""
        if not year:
            return {
                'exists': False,
                'title': 'هیچ سالی فعال نیست',
                'status': 'خطا'
            }
        
        remaining_days = "نامشخص"
        try:
            if year.end_date:
                parts = year.end_date.split('/')
                end_date = jdatetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
                today = jdatetime.date.today()
                diff = end_date - today
                remaining_days = f"{diff.days} روز"
        except Exception as _exc:
            self.logger.debug(
                f"خطای غیرمنتظره در {self.__class__.__name__}: {_exc}"
            )
        
        is_active = getattr(year, 'is_active', 0)
        is_archived = getattr(year, 'is_archived', 0)
        
        return {
            'exists': True,
            'id': year.id,
            'title': year.title,
            'is_active': is_active == 1,
            'is_archived': is_archived == 1,
            'status': "🟢 فعال" if is_active == 1 else "📦 بایگانی شده" if is_archived == 1 else "⚪ غیرفعال",
            'remaining_days': remaining_days,
            'start_date': year.start_date,
            'end_date': year.end_date
        }

    def _get_teacher_stats(self, teacher_id, year_id=None):
        """دریافت آمار یک معلم خاص"""
        try:
            teacher = self.staff_dal.get_by_id(teacher_id)
            if not teacher:
                return None
            
            assignments = self.assignment_dal.get_by_teacher(teacher_id, year_id)
            student_ids = [a.student_id for a in assignments if getattr(a, 'is_active', 0) == 1]
            students = [self.student_dal.get_by_id(sid) for sid in student_ids if sid]
            
            observations = self.observation_dal.get_all()
            observations = [o for o in observations if o.staff_id == teacher_id]
            if year_id:
                filtered = []
                for o in observations:
                    profile = self.profile_dal.get_by_id(o.student_profile_id)
                    if profile and profile.academic_year_id == year_id:
                        filtered.append(o)
                observations = filtered
            
            interventions = self.intervention_dal.get_all()
            interventions = [i for i in interventions if i.staff_id == teacher_id]
            if year_id:
                filtered = []
                for i in interventions:
                    profile = self.profile_dal.get_by_id(i.student_profile_id)
                    if profile and profile.academic_year_id == year_id:
                        filtered.append(i)
                interventions = filtered
            
            followups = self.followup_dal.get_all()
            followups = [f for f in followups if f.staff_id == teacher_id]
            
            positive = sum(1 for o in observations if o.behavior_type == "مثبت")
            positive_percent = (positive / len(observations) * 100) if observations else 0
            pending = sum(1 for f in followups if f.status == "pending")
            
            return {
                'teacher_name': getattr(teacher, 'full_name', 'نامشخص'),
                'teacher_id': teacher_id,
                'students_count': len(students),
                'observations_count': len(observations),
                'interventions_count': len(interventions),
                'followups_count': len(followups),
                'positive_percent': round(positive_percent, 1),
                'pending_followups': pending,
                'has_data': len(observations) > 0 or len(interventions) > 0
            }
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت آمار معلم: {e}")
            return None
    
    def _get_reminders(self, teacher_id=None):
        """دریافت یادآوری‌های پیگیری - بدون رتبه‌بندی"""
        try:
            from services.reminder_service import ReminderService
            reminder_service = ReminderService()
            
            if teacher_id:
                summary = reminder_service.get_reminder_summary()
                if summary.get('pending_list'):
                    summary['pending_list'] = [p for p in summary['pending_list'] if p.get('staff_id') == teacher_id]
                if summary.get('overdue_list'):
                    summary['overdue_list'] = [p for p in summary['overdue_list'] if p.get('staff_id') == teacher_id]
                summary['total_pending'] = len(summary.get('pending_list', []))
                summary['overdue_count'] = len(summary.get('overdue_list', []))
                summary['has_reminder'] = summary['total_pending'] > 0
            else:
                summary = reminder_service.get_reminder_summary()
            
            return summary
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت یادآوری‌ها: {e}")
            return {
                'total_pending': 0,
                'overdue_count': 0,
                'due_soon_count': 0,
                'pending_list': [],
                'overdue_list': [],
                'has_reminder': False
            }
    
    def _get_recent_activities(self, limit=20):
        """دریافت فعالیت‌های اخیر"""
        try:
            return self.audit_log_dal.get_logs(limit=limit)
        except Exception as e:
            self.logger.error(f"خطا در دریافت فعالیت‌های اخیر: {e}")
            return []
    
    def get_student_trend_data(self, student_id, year_id=None):
        """دریافت داده‌های روند یک دانش‌آموز خاص"""
        try:
            if year_id:
                profile = self.profile_dal.get_by_student_and_year(student_id, year_id)
            else:
                profile = self.profile_dal.get_active_by_student(student_id)
            
            if not profile:
                return {
                    'success': False,
                    'error': 'پرونده فعالی برای این دانش‌آموز یافت نشد.'
                }
            
            trend_service = TrendAnalysisService()
            return trend_service.analyze_student_trend(profile.id)
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت روند دانش‌آموز: {e}")
            return {
                'success': False,
                'error': str(e)
            }