"""
سرویس تولید گزارش والدین - ساده، قابل فهم و غیرتشخیصی
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_service import BaseService
from dal.student_dal import StudentDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.observation_dal import ObservationDAL
from dal.intervention_dal import InterventionDAL
from dal.followup_dal import FollowUpDAL
from dal.academic_year_dal import AcademicYearDAL
from dal.competency_dal import CompetencyDAL
from dal.family_context_dal import FamilyContextDAL
from dal.parent_interview_dal import ParentInterviewDAL
from utils.persian_pdf import PersianPDF
import jdatetime


class ParentReportService(BaseService):
    """
    سرویس تولید گزارش والدین
    
    ویژگی‌ها:
    - ساده و قابل فهم
    - غیرتشخیصی
    - بدون اطلاعات تخصصی و محرمانه
    - شامل نقاط قوت مشاهده‌شده
    - شامل زمینه‌های نیازمند حمایت
    - شامل روند رشد
    - شامل اقدامات انجام‌شده
    - شامل پیشنهادهای عمومی تربیتی/آموزشی
    - شامل نتیجه پیگیری
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
        self.family_dal = FamilyContextDAL()
        self.interview_dal = ParentInterviewDAL()
    
    def generate_parent_report_data(self, profile_id):
        """
        تولید داده‌های گزارش والدین
        
        Returns:
            dict: داده‌های مناسب برای گزارش والدین
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
            
            # دریافت مشاهدات
            observations = self.observation_dal.get_by_student_profile(profile_id)
            
            # دریافت مداخلات و پیگیری‌ها
            interventions = self.intervention_dal.get_by_student_profile(profile_id)
            followups = []
            for inter in interventions:
                followups.extend(self.followup_dal.get_by_intervention(inter.id))
            
            # دریافت اطلاعات خانواده
            family_context = self.family_dal.get_by_student_profile(profile_id)
            
            # دریافت مصاحبه‌های والدین
            parent_interviews = self.interview_dal.get_by_student_profile(profile_id)
            
            # تحلیل نقاط قوت و ضعف (غیرتشخیصی)
            strengths = self._extract_strengths(observations)
            weaknesses = self._extract_weaknesses(observations)
            
            # تحلیل روند (ساده)
            trend = self._calculate_simple_trend(observations)
            
            # تعداد پیگیری‌های در انتظار
            pending_count = sum(1 for f in followups if f.status == "pending")
            
            # پیشنهادات عمومی (غیرتخصصی)
            recommendations = self._generate_parent_recommendations(
                observations, interventions, followups
            )
            
            return {
                'student': student,
                'profile': profile,
                'academic_year': academic_year,
                'family_context': family_context,
                'parent_interviews': parent_interviews,
                'observations_count': len(observations),
                'interventions_count': len(interventions),
                'followups_count': len(followups),
                'pending_count': pending_count,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'trend': trend,
                'recommendations': recommendations,
                'has_data': len(observations) > 0 or len(interventions) > 0,
                'has_family_context': family_context is not None,
                'has_interviews': len(parent_interviews) > 0,
            }
            
        except Exception as e:
            self.logger.error(f"خطا در تولید داده‌های گزارش والدین: {e}")
            return None
    
    def _extract_strengths(self, observations):
        """
        استخراج نقاط قوت از مشاهدات - غیرتشخیصی
        
        فقط تعداد و نوع رفتارهای مثبت را گزارش می‌دهد
        بدون تشخیص شخصیت
        """
        positive_obs = [o for o in observations if o.behavior_type == "مثبت"]
        
        if not positive_obs:
            return ["هنوز مشاهده مثبتی ثبت نشده است."]
        
        # گروه‌بندی بر اساس شایستگی
        strengths_by_competency = {}
        for obs in positive_obs:
            if obs.competency_id:
                key = obs.competency_id
                if key not in strengths_by_competency:
                    strengths_by_competency[key] = {
                        'count': 0,
                        'examples': []
                    }
                strengths_by_competency[key]['count'] += 1
                if obs.behavior and len(strengths_by_competency[key]['examples']) < 2:
                    strengths_by_competency[key]['examples'].append(obs.behavior[:50])
        
        # تبدیل به لیست
        result = []
        for comp_id, data in strengths_by_competency.items():
            comp = self.competency_dal.get_by_id(comp_id)
            comp_name = comp.title if comp else f"شایستگی {comp_id}"
            if data['count'] >= 2:
                result.append(f"{comp_name}: {data['count']} بار مشاهده شده")
        
        if not result:
            # اگر شایستگی ثبت نشده بود
            result = [f"{len(positive_obs)} مشاهده مثبت ثبت شده است."]
        
        return result[:5]  # حداکثر ۵ مورد
    
    def _extract_weaknesses(self, observations):
        """
        استخراج زمینه‌های نیازمند حمایت - غیرتشخیصی
        
        فقط تعداد و نوع رفتارهای منفی را گزارش می‌دهد
        بدون تشخیص شخصیت
        """
        negative_obs = [o for o in observations if o.behavior_type == "منفی"]
        
        if not negative_obs:
            return ["هیچ زمینه نیازمند حمایتی ثبت نشده است."]
        
        # گروه‌بندی بر اساس شایستگی
        weaknesses_by_competency = {}
        for obs in negative_obs:
            if obs.competency_id:
                key = obs.competency_id
                if key not in weaknesses_by_competency:
                    weaknesses_by_competency[key] = {
                        'count': 0,
                        'examples': []
                    }
                weaknesses_by_competency[key]['count'] += 1
                if obs.behavior and len(weaknesses_by_competency[key]['examples']) < 2:
                    weaknesses_by_competency[key]['examples'].append(obs.behavior[:50])
        
        # تبدیل به لیست
        result = []
        for comp_id, data in weaknesses_by_competency.items():
            comp = self.competency_dal.get_by_id(comp_id)
            comp_name = comp.title if comp else f"شایستگی {comp_id}"
            if data['count'] >= 2:
                result.append(f"{comp_name}: {data['count']} بار مشاهده شده")
        
        if not result:
            result = [f"{len(negative_obs)} مشاهده منفی ثبت شده است."]
        
        return result[:5]  # حداکثر ۵ مورد
    
    def _calculate_simple_trend(self, observations):
        """
        محاسبه روند ساده - غیرتشخیصی
        
        فقط تغییرات تعداد مشاهدات را نشان می‌دهد
        """
        if len(observations) < 3:
            return {
                'has_data': False,
                'message': 'داده کافی برای تحلیل روند وجود ندارد.',
            }
        
        # گروه‌بندی ماهانه
        monthly_counts = {}
        for obs in observations:
            if obs.observation_date and len(obs.observation_date) >= 7:
                month_key = obs.observation_date[:7]
                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
        
        months = sorted(monthly_counts.keys())
        if len(months) < 2:
            return {
                'has_data': False,
                'message': 'داده کافی برای تحلیل روند وجود ندارد.',
            }
        
        # مقایسه نیمسال‌ها
        first_half = months[:len(months)//2]
        second_half = months[len(months)//2:]
        
        first_count = sum(monthly_counts[m] for m in first_half)
        second_count = sum(monthly_counts[m] for m in second_half)
        
        # تعیین روند
        if second_count > first_count:
            trend_text = "روند ثبت مشاهدات افزایشی بوده است."
            trend_icon = "📈"
        elif second_count < first_count:
            trend_text = "روند ثبت مشاهدات کاهشی بوده است."
            trend_icon = "📉"
        else:
            trend_text = "روند ثبت مشاهدات تقریباً ثابت بوده است."
            trend_icon = "➡️"
        
        return {
            'has_data': True,
            'trend_text': trend_text,
            'trend_icon': trend_icon,
            'months': months,
            'monthly_counts': monthly_counts,
            'first_half_count': first_count,
            'second_half_count': second_count,
            'total_observations': len(observations),
        }
    
    def _generate_parent_recommendations(self, observations, interventions, followups):
        """
        تولید پیشنهادات عمومی برای والدین - غیرتخصصی
        """
        recommendations = []
        
        # پیشنهادات بر اساس تعداد مشاهدات
        if len(observations) < 3:
            recommendations.append(
                "توصیه می‌شود همکاری و تعامل با مدرسه برای ثبت دقیق‌تر رفتارهای دانش‌آموز افزایش یابد."
            )
        
        # پیشنهادات بر اساس نوع رفتار
        positive_count = sum(1 for o in observations if o.behavior_type == "مثبت")
        negative_count = sum(1 for o in observations if o.behavior_type == "منفی")
        
        if negative_count > positive_count and negative_count >= 3:
            recommendations.append(
                "توصیه می‌شود در خانه نیز الگوهای رفتاری مثبت تقویت شوند. "
                "تشویق رفتارهای مناسب و گفتگوی روزانه درباره احساسات می‌تواند مؤثر باشد."
            )
        
        if positive_count >= 3:
            recommendations.append(
                "نقاط قوت دانش‌آموز در مدرسه شناسایی شده است. "
                "توصیه می‌شود این توانمندی‌ها در خانه نیز تقویت و تشویق شوند."
            )
        
        # پیشنهادات بر اساس پیگیری‌ها
        pending_followups = [f for f in followups if f.status == "pending"]
        if pending_followups:
            recommendations.append(
                "برخی از پیگیری‌های آموزشی نیازمند انجام است. "
                "لطفاً با مدرسه در این زمینه همکاری کنید."
            )
        
        # پیشنهادات عمومی
        if not recommendations:
            recommendations.append(
                "وضعیت عمومی دانش‌آموز مطلوب است. "
                "توصیه می‌شود ارتباط با مدرسه مستمر باشد و در صورت نیاز، "
                "جلسات مشاوره با معلم یا مشاور مدرسه برگزار شود."
            )
        
        return recommendations[:5]  # حداکثر ۵ مورد
    
    def export_parent_report_pdf(self, profile_id, file_path):
        """
        خروجی گزارش والدین به صورت PDF
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
            file_path: مسیر ذخیره فایل PDF
            
        Returns:
            tuple: (success, message)
        """
        try:
            report_data = self.generate_parent_report_data(profile_id)
            if not report_data:
                return False, "امکان تولید گزارش وجود ندارد."
            
            pdf = PersianPDF(file_path)
            
            # ===== عنوان =====
            pdf.add_title("گزارش پیشرفت تحصیلی و تربیتی")
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
            ]
            
            for item in info_items:
                pdf.add_text(item)
            pdf.add_spacer(0.3)
            
            # ===== پیام خوش‌آمدگویی =====
            pdf.add_text(
                "والدین گرامی، این گزارش بر اساس مشاهدات ثبت‌شده در مدرسه تهیه شده است. "
                "هدف از این گزارش، کمک به درک بهتر وضعیت تحصیلی و تربیتی دانش‌آموز شماست."
            )
            pdf.add_spacer(0.3)
            
            # ===== خلاصه آماری (ساده) =====
            pdf.add_subtitle("خلاصه وضعیت")
            stats_items = [
                f"تعداد مشاهدات ثبت‌شده: {report_data['observations_count']} مورد",
                f"تعداد مداخلات آموزشی: {report_data['interventions_count']} مورد",
                f"تعداد پیگیری‌های انجام‌شده: {report_data['followups_count']} مورد",
            ]
            for item in stats_items:
                pdf.add_text(item)
            pdf.add_spacer(0.3)
            
            # ===== نقاط قوت =====
            pdf.add_subtitle("نقاط قوت مشاهده‌شده")
            for strength in report_data['strengths']:
                pdf.add_strength(strength)
            pdf.add_spacer(0.3)
            
            # ===== زمینه‌های نیازمند حمایت =====
            pdf.add_subtitle("زمینه‌های نیازمند حمایت")
            for weakness in report_data['weaknesses']:
                pdf.add_weakness(weakness)
            pdf.add_spacer(0.3)
            
            # ===== روند رشد =====
            pdf.add_subtitle("روند رشد")
            if report_data['trend']['has_data']:
                pdf.add_text(f"{report_data['trend']['trend_icon']} {report_data['trend']['trend_text']}")
                pdf.add_text(f"تعداد کل مشاهدات: {report_data['trend']['total_observations']}")
                if report_data['trend']['first_half_count'] > 0:
                    pdf.add_text(
                        f"نیمسال اول: {report_data['trend']['first_half_count']} مشاهده | "
                        f"نیمسال دوم: {report_data['trend']['second_half_count']} مشاهده"
                    )
            else:
                pdf.add_text(report_data['trend']['message'])
            pdf.add_spacer(0.3)
            
            # ===== اقدامات انجام‌شده =====
            pdf.add_subtitle("اقدامات انجام‌شده")
            if report_data['interventions_count'] > 0:
                pdf.add_text(f"تعداد مداخلات آموزشی انجام‌شده: {report_data['interventions_count']} مورد")
                pdf.add_text("در صورت تمایل، برای اطلاع از جزئیات بیشتر با مدرسه تماس بگیرید.")
            else:
                pdf.add_text("هیچ مداخله آموزشی خاصی ثبت نشده است.")
            pdf.add_spacer(0.3)
            
            # ===== نتیجه پیگیری‌ها =====
            pdf.add_subtitle("نتیجه پیگیری‌ها")
            completed = report_data['followups_count'] - report_data.get('pending_count', 0)
            pdf.add_text(f"پیگیری‌های انجام‌شده: {completed} مورد")
            pdf.add_text(f"پیگیری‌های در انتظار: {report_data.get('pending_count', 0)} مورد")
            pdf.add_spacer(0.3)
            
            # ===== پیشنهادات عمومی =====
            pdf.add_subtitle("پیشنهادات")
            for rec in report_data['recommendations']:
                pdf.add_text(f"* {rec}")
            pdf.add_spacer(0.3)
            
            # ===== اطلاعات تماس =====
            pdf.add_separator()
            pdf.add_text("برای اطلاعات بیشتر، با مدرسه تماس بگیرید.")
            try:
                today = jdatetime.date.today()
                date_str = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
            except Exception:
                from datetime import datetime
                date_str = datetime.now().strftime("%Y/%m/%d")
            
            pdf.add_text(f"تاریخ تهیه گزارش: {date_str}")
            pdf.add_text("PARTO - سامانه مدیریت پرونده دانش‌آموزان")
            
            # ساخت PDF
            pdf.build(file_path)
            
            return True, f"فایل PDF با موفقیت در {file_path} ذخیره شد."
            
        except Exception as e:
            self.logger.error(f"خطا در ساخت PDF گزارش والدین: {e}")
            return False, f"خطا در ساخت فایل PDF: {str(e)}"