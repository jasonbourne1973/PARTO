"""
سرویس گزارش عملکرد معلم - نمایش تعداد و کیفیت مشاهدات، مداخلات و پیگیری‌ها
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jdatetime

from dal.competency_dal import CompetencyDAL
from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.staff_dal import StaffDAL
from dal.teacher_assignment_dal import TeacherAssignmentDAL
from services.base_service import BaseService
from utils.behavior_analysis import classify_pattern, pattern_label
from utils.error_handler import ServiceError
from utils.logger import get_logger
from utils.time_utils import utc_now


class TeacherPerformanceService(BaseService):
    """
    سرویس گزارش عملکرد معلم
    
    ویژگی‌ها:
    - نمایش تعداد مشاهدات، مداخلات و پیگیری‌ها
    - تحلیل کیفیت مشاهدات (مثبت/منفی)
    - نمایش روند عملکرد
    - تحلیل شایستگی‌های مرتبط
    - پیشنهادات بهبود
    """
    
    def __init__(self):
        super().__init__()
        self.staff_dal = StaffDAL()
        self.assignment_dal = TeacherAssignmentDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.competency_dal = CompetencyDAL()
        self.logger = get_logger(self.__class__.__name__)
    
    def get_teacher_performance(self, teacher_id, start_date=None, end_date=None):
        """
        دریافت گزارش عملکرد معلم
        
        Args:
            teacher_id: شناسه معلم
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
        
        Returns:
            dict: گزارش کامل عملکرد
        """
        try:
            # دریافت اطلاعات معلم
            teacher = self.staff_dal.get_by_id(teacher_id)
            if not teacher:
                raise ServiceError(f"معلم با شناسه {teacher_id} یافت نشد.")
            
            # دریافت آمار کلی
            stats = self.assignment_dal.get_teacher_stats(teacher_id, start_date, end_date)
            
            # دریافت دانش‌آموزان با آمار
            students = self.assignment_dal.get_teacher_students_with_stats(teacher_id, start_date, end_date)
            
            # دریافت روند
            trend = self.assignment_dal.get_teacher_trend(teacher_id, 'monthly', start_date, end_date)
            
            # دریافت مشاهدات برای تحلیل شایستگی‌ها
            observations = self.observation_dal.get_by_teacher(teacher_id, start_date, end_date)
            
            # تحلیل شایستگی‌ها
            competency_stats = self._calculate_competency_stats(observations)
            
            # تحلیل نقاط قوت و ضعف
            strengths, weaknesses = self._analyze_strengths_weaknesses(competency_stats)
            
            # تولید پیشنهادات
            recommendations = self._generate_recommendations(stats, competency_stats, students)
            
            # آمار ماهانه
            monthly_stats = self._get_monthly_stats(teacher_id, start_date, end_date)
            
            return {
                'teacher': teacher,
                'stats': stats,
                'students': students,
                'trend': trend,
                'monthly_stats': monthly_stats,
                'competency_stats': competency_stats,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'recommendations': recommendations,
                'has_data': stats.get('total_observations', 0) > 0,
                'start_date': start_date,
                'end_date': end_date
            }
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت گزارش عملکرد معلم: {e}")
            raise ServiceError(f"خطا در دریافت گزارش: {e!s}")
    
    def get_all_teachers_performance(self, start_date=None, end_date=None):
        """
        دریافت گزارش عملکرد همه معلمان
        
        Args:
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
        
        Returns:
            list: لیست گزارش‌های عملکرد معلمان
        """
        try:
            all_staff = self.staff_dal.get_all()
            teachers = [s for s in all_staff if s.role == "teacher"]
            
            reports = []
            for teacher in teachers:
                report = self.get_teacher_performance(teacher.id, start_date, end_date)
                if report:
                    reports.append(report)
            
            return reports
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت گزارش همه معلمان: {e}")
            raise ServiceError(f"خطا در دریافت گزارش: {e!s}")
    
    def _calculate_competency_stats(self, observations):
        """محاسبه آمار شایستگی‌ها"""
        if not observations:
            return {}
        
        stats = {}
        for obs in observations:
            if obs.competency_id:
                competency = self.competency_dal.get_by_id(obs.competency_id)
                if competency:
                    key = competency.title
                    if key not in stats:
                        stats[key] = {
                            'count': 0,
                            'total_severity': 0,
                            'positive': 0,
                            'negative': 0
                        }
                    stats[key]['count'] += 1
                    stats[key]['total_severity'] += obs.severity or 1
                    if obs.behavior_type == 'مثبت':
                        stats[key]['positive'] += 1
                    elif obs.behavior_type == 'منفی':
                        stats[key]['negative'] += 1
        
        for key in stats:
            if stats[key]['count'] > 0:
                stats[key]['avg_severity'] = round(
                    stats[key]['total_severity'] / stats[key]['count'], 1
                )
        
        return stats
    
    def _analyze_strengths_weaknesses(self, competency_stats):
        """
        تحلیل توانمندی‌ها و زمینه‌های نیازمند توجه — بر پایهٔ **نوع رفتار**
        (بازرسی یازدهم)

        معیار پیشین «میانگین شدت» بود؛ اکنون الگوی تکرارشوندهٔ رفتارهای
        مثبت/منفی مبناست و شدت فقط به‌عنوان اطلاعات تکمیلی همراه خروجی
        می‌آید. این تحلیل در سطح معلم/کلاس است و برچسب‌گذاری فردی نیست.
        """
        strengths = []
        weaknesses = []
        
        for competency, stats in competency_stats.items():
            count = stats.get('count', 0)
            positive = stats.get('positive', 0)
            negative = stats.get('negative', 0)
            kind = classify_pattern(positive, negative,
                                    max(count - positive - negative, 0), count)
            entry = {
                'competency': competency,
                'count': count,
                'positive': positive,
                'negative': negative,
                'pattern': kind,
                'pattern_label': pattern_label(kind),
                # شدت: تکمیلی
                'avg_severity': stats.get('avg_severity', 0),
                'severity_is_auxiliary': True,
            }
            if kind == 'strength':
                strengths.append(entry)
            elif kind == 'needs_attention':
                weaknesses.append(entry)
        
        strengths.sort(key=lambda x: (x['positive'], x['count']), reverse=True)
        weaknesses.sort(key=lambda x: (x['negative'], x['count']), reverse=True)
        
        return strengths[:5], weaknesses[:5]
    
    def _generate_recommendations(self, stats, competency_stats, students):
        """تولید پیشنهادات"""
        recommendations = {'teacher': [], 'counselor': [], 'general': []}
        
        total_obs = stats.get('total_observations', 0)
        positive = stats.get('positive', 0)
        
        if total_obs > 0:
            positive_ratio = positive / total_obs
            
            if positive_ratio >= 0.6:
                recommendations['teacher'].append(
                    f"✅ {positive_ratio*100:.0f}% مشاهدات مثبت است. عملکرد مطلوب است."
                )
            elif positive_ratio >= 0.4:
                recommendations['teacher'].append(
                    f"🟡 {positive_ratio*100:.0f}% مشاهدات مثبت است. می‌توان با تمرین بیشتر بهبود یافت."
                )
            else:
                recommendations['teacher'].append(
                    f"🔴 {positive_ratio*100:.0f}% مشاهدات مثبت است. نیاز به تغییر رویکرد آموزشی."
                )
        
        if competency_stats:
            weak = [
                c for c, s in competency_stats.items()
                if classify_pattern(s.get('positive', 0), s.get('negative', 0),
                                    max(s.get('count', 0) - s.get('positive', 0)
                                        - s.get('negative', 0), 0),
                                    s.get('count', 0)) == 'needs_attention'
            ]
            if weak:
                recommendations['teacher'].append(
                    f"📋 زمینه‌های با الگوی تکرارشوندهٔ رفتار منفی: {', '.join(weak[:3])} "
                    "— بررسی این الگوها پیشنهاد می‌شود."
                )
        
        if students:
            no_obs = [s for s in students if s.get('observations_count', 0) == 0]
            if no_obs:
                recommendations['teacher'].append(
                    f"👤 {len(no_obs)} دانش‌آموز بدون مشاهده. توجه ویژه توصیه می‌شود."
                )
        
        pending = stats.get('pending_followups', 0)
        if pending > 0:
            recommendations['counselor'].append(
                f"🔔 {pending} پیگیری در انتظار. هماهنگی برای انجام پیگیری‌ها توصیه می‌شود."
            )
        
        return recommendations
    
    def _get_monthly_stats(self, teacher_id, start_date=None, end_date=None):
        """دریافت آمار ماهانه"""
        try:
            return self.assignment_dal.get_teacher_trend(teacher_id, 'monthly', start_date, end_date)
        except Exception:
            return []
    
    def export_teacher_report_pdf(self, teacher_id, file_path, start_date=None, end_date=None):
        """
        خروجی گزارش عملکرد معلم به PDF
        
        Args:
            teacher_id: شناسه معلم
            file_path: مسیر ذخیره فایل
            start_date: تاریخ شروع (اختیاری)
            end_date: تاریخ پایان (اختیاری)
        
        Returns:
            tuple: (success, message)
        """
        try:
            report = self.get_teacher_performance(teacher_id, start_date, end_date)
            if not report:
                return False, "داده‌ای برای تولید گزارش وجود ندارد."
            
            from utils.persian_pdf import PersianPDF
            
            pdf = PersianPDF(file_path)
            
            teacher = report['teacher']
            stats = report.get('stats', {})
            
            pdf.add_title("گزارش عملکرد معلم")
            pdf.add_spacer(0.2)
            
            info_items = [
                f"نام معلم: {teacher.full_name}",
                f"تعداد دانش‌آموزان: {stats.get('total_students', 0)}",
            ]
            
            if start_date and end_date:
                info_items.append(f"بازه زمانی: {start_date} تا {end_date}")
            
            for item in info_items:
                pdf.add_text(item)
            pdf.add_spacer(0.3)
            
            pdf.add_subtitle("آمار کلی")
            pdf.add_text(f"کل مشاهدات: {stats.get('total_observations', 0)}")
            pdf.add_text(f"مشاهدات مثبت: {stats.get('positive', 0)}")
            pdf.add_text(f"مشاهدات منفی: {stats.get('negative', 0)}")
            pdf.add_text(f"میانگین شدت: {stats.get('avg_severity', 0)}")
            pdf.add_text(f"مداخلات ثبت‌شده: {stats.get('total_interventions', 0)}")
            pdf.add_text(f"پیگیری‌های در انتظار: {stats.get('pending_followups', 0)}")
            pdf.add_spacer(0.3)
            
            recommendations = report.get('recommendations', {})
            if recommendations.get('teacher'):
                pdf.add_subtitle("پیشنهادات")
                for rec in recommendations['teacher'][:5]:
                    pdf.add_text(f"• {rec}")
            
            try:
                today = jdatetime.date.today()
                date_str = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
            except Exception:
                date_str = utc_now().strftime("%Y/%m/%d")
            
            pdf.add_text(f"تاریخ تهیه گزارش: {date_str}")
            pdf.add_text("PARTO - سامانه مدیریت پرونده دانش‌آموزان")
            
            pdf.build(file_path)
            return True, f"فایل PDF با موفقیت در {file_path} ذخیره شد."
            
        except Exception as e:
            self.logger.error(f"خطا در خروجی PDF: {e}")
            return False, f"خطا: {e!s}"