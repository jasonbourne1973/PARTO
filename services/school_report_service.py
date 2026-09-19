"""
سرویس تولید گزارش داخلی مدرسه - جزئی‌تر و تخصصی
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jdatetime

from dal.academic_year_dal import AcademicYearDAL
from dal.competency_dal import CompetencyDAL
from dal.family_context_dal import FamilyContextDAL
from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.parent_interview_dal import ParentInterviewDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from services.base_service import BaseService
from services.case_timeline_service import CaseTimelineService
from services.report_generator import ReportGenerator
from utils.persian_pdf import PersianPDF
from utils.time_utils import utc_now


class SchoolReportService(BaseService):
    """
    سرویس تولید گزارش داخلی مدرسه - جزئی‌تر
    
    ویژگی‌ها:
    - شامل تمام مشاهدات با تاریخ
    - شامل پیگیری‌ها و اقدامات
    - شامل روند تغییرات
    - شامل ارجاع به مشاور در صورت وجود
    - اطلاعات تخصصی و محرمانه
    """
    
    def __init__(self):
        super().__init__()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.competency_dal = CompetencyDAL()
        self.staff_dal = StaffDAL()
        self.family_dal = FamilyContextDAL()
        self.interview_dal = ParentInterviewDAL()
        self.timeline_service = CaseTimelineService()
        self.report_generator = ReportGenerator()
    
    def generate_school_report_data(self, profile_id):
        """
        تولید داده‌های گزارش داخلی مدرسه
        
        Returns:
            dict: داده‌های کامل برای گزارش مدرسه
        """
        try:
            # دریافت اطلاعات پایه
            profile = self.profile_dal.get_by_id(profile_id)
            if not profile:
                return None
            
            student = self.student_dal.get_by_id(profile.student_id)
            if not student:
                return None
            
            academic_year = self.academic_year_dal.get_by_id(profile.academic_year_id)
            
            # دریافت تمام داده‌ها
            observations = self.observation_dal.get_by_student_profile(profile_id)
            interventions = self.intervention_dal.get_by_student_profile(profile_id)
            
            followups = []
            for inter in interventions:
                followups.extend(self.followup_dal.get_by_intervention(inter.id))
            
            family_context = self.family_dal.get_by_student_profile(profile_id)
            parent_interviews = self.interview_dal.get_by_student_profile(profile_id)
            
            # Timeline
            timeline = self.timeline_service.get_timeline(profile_id)
            
            # تحلیل کامل
            competency_stats = self.report_generator.calculate_competency_stats(observations)
            strengths, weaknesses = self.report_generator.analyze_strengths_weaknesses(competency_stats)
            recommendations = self.report_generator.generate_recommendations(
                competency_stats, observations, interventions
            )
            
            # روند کامل
            trend_data = self.report_generator.calculate_trend(observations)
            semester_stats = self.report_generator.calculate_semester_stats(observations)
            
            return {
                'student': student,
                'profile': profile,
                'academic_year': academic_year,
                'observations': observations,
                'interventions': interventions,
                'followups': followups,
                'family_context': family_context,
                'parent_interviews': parent_interviews,
                'timeline': timeline,
                'observations_count': len(observations),
                'interventions_count': len(interventions),
                'followups_count': len(followups),
                'competency_stats': competency_stats,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'recommendations': recommendations,
                'trend_data': trend_data,
                'semester_stats': semester_stats,
                'has_data': len(observations) > 0 or len(interventions) > 0,
                'has_family_context': family_context is not None,
                'has_interviews': len(parent_interviews) > 0,
            }
            
        except Exception as e:
            self.logger.error(f"خطا در تولید داده‌های گزارش مدرسه: {e}")
            return None
    
    def export_school_report_pdf(self, profile_id, file_path):
        """
        خروجی گزارش داخلی مدرسه به صورت PDF
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
            file_path: مسیر ذخیره فایل PDF
            
        Returns:
            tuple: (success, message)
        """
        try:
            report_data = self.generate_school_report_data(profile_id)
            if not report_data:
                return False, "امکان تولید گزارش وجود ندارد."
            
            pdf = PersianPDF(file_path)
            
            # ===== عنوان =====
            pdf.add_title("گزارش داخلی پرونده دانش‌آموز")
            pdf.add_spacer(0.2)
            
            # ===== اطلاعات دانش‌آموز =====
            student = report_data['student']
            profile = report_data['profile']
            academic_year = report_data['academic_year']
            
            info_items = [
                f"نام دانش‌آموز: {student.full_name}",
                f"پایه: {profile.grade_display}",
                f"کلاس: {profile.class_name or '-'}",
                f"سال تحصیلی: {academic_year.title if academic_year else '-'}",
                f"شناسه پرونده: {profile.id}",
                f"وضعیت پرونده: {profile.status_display}",
            ]
            
            for item in info_items:
                pdf.add_text(item)
            pdf.add_spacer(0.3)
            
            # ===== خلاصه آماری کامل =====
            pdf.add_subtitle("خلاصه آماری")
            stats_items = [
                f"تعداد مشاهدات: {report_data['observations_count']}",
                f"تعداد مداخلات: {report_data['interventions_count']}",
                f"تعداد پیگیری‌ها: {report_data['followups_count']}",
            ]
            
            # آمار مثبت/منفی
            positive = sum(1 for o in report_data['observations'] if o.behavior_type == "مثبت")
            negative = sum(1 for o in report_data['observations'] if o.behavior_type == "منفی")
            neutral = report_data['observations_count'] - positive - negative
            
            stats_items.append(f"مشاهدات مثبت: {positive}")
            stats_items.append(f"مشاهدات منفی: {negative}")
            stats_items.append(f"مشاهدات خنثی: {neutral}")
            
            for item in stats_items:
                pdf.add_text(item)
            pdf.add_spacer(0.3)
            
            # ===== اطلاعات خانواده =====
            if report_data['has_family_context']:
                pdf.add_subtitle("اطلاعات زمینه‌ای خانواده")
                family = report_data['family_context']
                pdf.add_text(f"وضعیت سرپرستی: {family.guardian_status_display}")
                pdf.add_text(f"تعداد برادران: {family.siblings_brothers or 0}")
                pdf.add_text(f"تعداد خواهران: {family.siblings_sisters or 0}")
                pdf.add_text(f"ارتباط با مدرسه: {family.school_contact_display}")
                if family.notes:
                    pdf.add_text(f"یادداشت: {family.notes}")
                pdf.add_spacer(0.3)
            
            # ===== مصاحبه‌های والدین =====
            if report_data['has_interviews']:
                pdf.add_subtitle("مصاحبه‌های والدین")
                for interview in report_data['parent_interviews']:
                    pdf.add_bold(f"تاریخ: {interview.interview_date} - {interview.parent_name}")
                    pdf.add_text(f"موضوع: {interview.topic}")
                    if interview.summary:
                        pdf.add_text(f"خلاصه: {interview.summary}")
                    if interview.result:
                        pdf.add_text(f"نتیجه: {interview.result}")
                    if interview.next_action:
                        pdf.add_text(f"اقدام بعدی: {interview.next_action}")
                    pdf.add_spacer(0.2)
                pdf.add_spacer(0.3)
            
            # ===== مشاهدات (جزئی) =====
            if report_data['observations']:
                pdf.add_subtitle("مشاهدات ثبت‌شده")
                
                # جدول مشاهدات
                table_data = [["تاریخ", "محیط", "نوع", "شدت", "رفتار"]]
                for obs in report_data['observations'][:15]:
                    table_data.append([
                        obs.observation_date or "",
                        obs.location or "",
                        obs.behavior_type or "خنثی",
                        "|" * (obs.severity or 0),
                        obs.behavior[:50] + "..." if obs.behavior and len(obs.behavior) > 50 else (obs.behavior or "")
                    ])
                pdf.add_table(table_data)
                
                if len(report_data['observations']) > 15:
                    pdf.add_text(f"... و {len(report_data['observations']) - 15} مشاهده دیگر")
                pdf.add_spacer(0.3)
            
            # ===== مداخلات =====
            if report_data['interventions']:
                pdf.add_subtitle("مداخلات انجام‌شده")
                for inter in report_data['interventions']:
                    pdf.add_bold(f"{inter.type_display} - {inter.date}")
                    pdf.add_text(f"توضیحات: {inter.description}")
                    if inter.goal:
                        pdf.add_text(f"هدف: {inter.goal}")
                    pdf.add_text(f"وضعیت: {inter.status_display}")
                    if inter.result:
                        pdf.add_text(f"نتیجه: {inter.result}")
                    pdf.add_spacer(0.15)
                pdf.add_spacer(0.3)
            
            # ===== پیگیری‌ها =====
            if report_data['followups']:
                pdf.add_subtitle("پیگیری‌ها")
                for follow in report_data['followups']:
                    pdf.add_bold(f"{follow.date} - {follow.method or 'پیگیری'}")
                    if follow.description:
                        pdf.add_text(f"توضیحات: {follow.description}")
                    pdf.add_text(f"وضعیت: {follow.status_display}")
                    if follow.result_type:
                        pdf.add_text(f"نوع نتیجه: {follow.result_type_display}")
                    if follow.result_description:
                        pdf.add_text(f"شرح نتیجه: {follow.result_description}")
                    if follow.next_action_date:
                        pdf.add_text(f"اقدام بعدی: {follow.next_action_date}")
                    pdf.add_spacer(0.15)
                pdf.add_spacer(0.3)
            
            # ===== روند تغییرات =====
            if report_data['trend_data']:
                pdf.add_subtitle("روند تغییرات")
                for item in report_data['trend_data']:
                    pdf.add_text(
                        f"{item['month']}: {item['count']} مشاهده (میانگین شدت: {item['avg_severity']})"
                    )
                pdf.add_spacer(0.3)
            
            # ===== مقایسه نیمسال‌ها =====
            if report_data['semester_stats']:
                stats = report_data['semester_stats']
                pdf.add_subtitle("مقایسه نیمسال‌ها")
                pdf.add_text(f"نیمسال اول: {stats['first']['count']} مشاهده")
                pdf.add_text(f"نیمسال دوم: {stats['second']['count']} مشاهده")
                pdf.add_text(f"روند کلی: {stats['trend']}")
                pdf.add_spacer(0.3)
            
            # ===== نقاط قوت و ضعف =====
            pdf.add_subtitle("تحلیل مشاهدات")
            
            pdf.add_bold("نقاط قوت مشاهده‌شده:")
            for strength in report_data['strengths']:
                pdf.add_strength(
                    f"{strength['competency']} (میانگین شدت: {strength['avg_severity']}, تعداد: {strength['count']})"
                )
            
            pdf.add_bold("زمینه‌های نیازمند حمایت:")
            for weakness in report_data['weaknesses']:
                pdf.add_weakness(
                    f"{weakness['competency']} (میانگین شدت: {weakness['avg_severity']}, تعداد: {weakness['count']})"
                )
            pdf.add_spacer(0.3)
            
            # ===== پیشنهادات تخصصی =====
            pdf.add_subtitle("پیشنهادات تخصصی")
            
            pdf.add_bold("به معلم:")
            for rec in report_data['recommendations']['teacher']:
                pdf.add_text(f"* {rec}")
            pdf.add_spacer(0.2)
            
            pdf.add_bold("به مشاور:")
            for rec in report_data['recommendations']['counselor']:
                pdf.add_text(f"* {rec}")
            pdf.add_spacer(0.3)
            
            # ===== متادیتا =====
            pdf.add_separator()
            try:
                today = jdatetime.date.today()
                date_str = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
            except Exception:
                date_str = utc_now().strftime("%Y/%m/%d")
            
            pdf.add_text(f"تاریخ تهیه گزارش: {date_str}")
            pdf.add_text("PARTO - سامانه مدیریت پرونده دانش‌آموزان")
            pdf.add_text("گزارش داخلی - محرمانه")
            
            # ساخت PDF
            pdf.build(file_path)
            
            return True, f"فایل PDF با موفقیت در {file_path} ذخیره شد."
            
        except Exception as e:
            self.logger.error(f"خطا در ساخت PDF گزارش مدرسه: {e}")
            return False, f"خطا در ساخت فایل PDF: {str(e)}"