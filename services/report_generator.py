"""
سرویس تولید گزارش‌های دانش‌آموزی - نسخه اصلاح شده با PDF بدون Emoji
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.student_dal import StudentDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.observation_dal import ObservationDAL
from dal.intervention_dal import InterventionDAL
from dal.followup_dal import FollowUpDAL
from dal.academic_year_dal import AcademicYearDAL
from dal.competency_dal import CompetencyDAL
from dal.staff_dal import StaffDAL
from services.case_timeline_service import CaseTimelineService
from database.connection import DatabaseConnection
from utils.persian_pdf import PersianPDF

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    print("⚠️ کتابخانه openpyxl نصب نیست. برای نصب: pip install openpyxl")


class ReportGenerator:
    """تولید کننده گزارش‌های دانش‌آموزی با قابلیت ردیابی و خروجی PDF"""
    
    def __init__(self):
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.academic_year_dal = AcademicYearDAL()
        self.competency_dal = CompetencyDAL()
        self.staff_dal = StaffDAL()
        self.timeline_service = CaseTimelineService()
        self.db = DatabaseConnection()
    
    def generate_student_report(self, profile_id):
        """
        تولید گزارش کامل برای یک پرونده سالانه دانش‌آموز
        
        Returns:
            dict: شامل تمام اطلاعات گزارش با قابلیت ردیابی
        """
        profile = self.profile_dal.get_by_id(profile_id)
        if not profile:
            return None
        
        student = self.student_dal.get_by_id(profile.student_id)
        if not student:
            return None
        
        academic_year = self.academic_year_dal.get_by_id(profile.academic_year_id)
        
        # دریافت داده‌ها با استفاده از Timeline Service
        timeline = self.timeline_service.get_timeline(profile_id)
        summary = self.timeline_service.get_timeline_summary(profile_id)
        
        observations = self.observation_dal.get_by_student_profile(profile_id)
        interventions = self.intervention_dal.get_by_student_profile(profile_id)
        
        # دریافت پیگیری‌ها
        all_followups = []
        for inter in interventions:
            all_followups.extend(self.followup_dal.get_by_intervention(inter.id))
        
        # تحلیل شایستگی‌ها
        competency_stats = self.calculate_competency_stats(observations)
        strengths, weaknesses = self.analyze_strengths_weaknesses(competency_stats)
        recommendations = self.generate_recommendations(competency_stats, observations, interventions)
        
        # روند و آمار نیمسال
        trend_data = self.calculate_trend(observations)
        semester_stats = self.calculate_semester_stats(observations)
        
        # داده‌های ردیابی
        traceability = self._build_traceability(observations, interventions, all_followups)
        
        report = {
            'student': student,
            'profile': profile,
            'academic_year': academic_year,
            'observations_count': len(observations),
            'interventions_count': len(interventions),
            'followups_count': len(all_followups),
            'competency_stats': competency_stats,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendations': recommendations,
            'trend_data': trend_data,
            'semester_stats': semester_stats,
            'summary': self.generate_summary(observations, interventions, all_followups, competency_stats),
            'observations': observations,
            'interventions': interventions,
            'followups': all_followups,
            'timeline': timeline,
            'has_data': len(observations) > 0 or len(interventions) > 0,
            'traceability': traceability,
        }
        
        return report
    
    def generate_parent_report(self, profile_id):
        """
        تولید گزارش مختصر و غیرمحرمانه برای والدین
        
        Returns:
            dict: گزارش مناسب برای والدین
        """
        full_report = self.generate_student_report(profile_id)
        if not full_report:
            return None
        
        student = full_report['student']
        
        parent_report = {
            'student_name': student.full_name,
            'grade': full_report['profile'].grade_display,
            'class': full_report['profile'].class_name or 'نامشخص',
            'observations_count': full_report['observations_count'],
            'interventions_count': full_report['interventions_count'],
            'strengths': full_report['strengths'][:5],
            'weaknesses': full_report['weaknesses'][:5],
            'recommendations': {
                'parents': full_report['recommendations'].get('parents', ['نظری ثبت نشده است.'])
            },
            'trend': full_report.get('trend_data', None),
            'summary': f"دانش‌آموز {student.full_name} در پایه {full_report['profile'].grade_display} دارای {full_report['observations_count']} مشاهده ثبت‌شده و {full_report['interventions_count']} مداخله است."
        }
        
        return parent_report
    
    # ============================================================
    # متدهای کمکی (بدون تغییر)
    # ============================================================
    
    def calculate_competency_stats(self, observations):
        """محاسبه آمار شایستگی‌ها بر اساس مشاهدات"""
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
                            'negative': 0,
                            'avg_severity': 0,
                            'competency_id': obs.competency_id,
                            'observation_ids': []
                        }
                    
                    stats[key]['count'] += 1
                    stats[key]['total_severity'] += obs.severity or 1
                    stats[key]['observation_ids'].append(obs.id)
                    
                    if obs.behavior_type == "مثبت":
                        stats[key]['positive'] += 1
                    elif obs.behavior_type == "منفی":
                        stats[key]['negative'] += 1
        
        for key in stats:
            if stats[key]['count'] > 0:
                stats[key]['avg_severity'] = round(stats[key]['total_severity'] / stats[key]['count'], 1)
        
        return stats
    
    def analyze_strengths_weaknesses(self, competency_stats):
        """تحلیل نقاط قوت و زمینه‌های نیازمند حمایت"""
        strengths = []
        weaknesses = []
        
        for competency, stats in competency_stats.items():
            avg = stats['avg_severity']
            count = stats['count']
            
            if count >= 2 and avg >= 3.5:
                strengths.append({
                    'competency': competency,
                    'avg_severity': avg,
                    'count': count,
                    'competency_id': stats.get('competency_id'),
                    'observation_ids': stats.get('observation_ids', [])
                })
            elif count >= 2 and avg <= 2.0:
                weaknesses.append({
                    'competency': competency,
                    'avg_severity': avg,
                    'count': count,
                    'competency_id': stats.get('competency_id'),
                    'observation_ids': stats.get('observation_ids', [])
                })
        
        strengths.sort(key=lambda x: x['avg_severity'], reverse=True)
        weaknesses.sort(key=lambda x: x['avg_severity'])
        
        return strengths, weaknesses
    
    def generate_recommendations(self, competency_stats, observations, interventions):
        """تولید پیشنهادات بر اساس آمار شایستگی‌ها و مداخلات"""
        recommendations = {'teacher': [], 'parents': [], 'counselor': []}
        
        for competency, stats in competency_stats.items():
            avg = stats['avg_severity']
            count = stats['count']
            
            has_intervention = False
            for inter in interventions:
                if inter.observation_id in stats.get('observation_ids', []):
                    has_intervention = True
                    break
            
            if count >= 2 and avg <= 2.0:
                if not has_intervention:
                    recommendations['teacher'].append(
                        f"در شاخص '{competency}' نیاز به تمرین و توجه بیشتر است "
                        f"(تعداد: {count} مشاهده). پیشنهاد می‌شود یک مداخله هدفمند ثبت شود."
                    )
                else:
                    recommendations['teacher'].append(
                        f"در شاخص '{competency}' نیاز به ادامه حمایت است "
                        f"(تعداد: {count} مشاهده). اثر مداخلات ثبت‌شده بررسی شود."
                    )
                recommendations['counselor'].append(
                    f"در شاخص '{competency}' ممکن است نیاز به بررسی و حمایت عاطفی باشد."
                )
            elif count >= 2 and avg >= 3.5:
                recommendations['parents'].append(
                    f"در شاخص '{competency}' عملکرد خوبی دارد (میانگین {avg}). به تقویت ادامه دهید."
                )
            elif count == 0:
                recommendations['teacher'].append(
                    f"هیچ مشاهده‌ای برای شاخص '{competency}' ثبت نشده است. "
                    f"برای تحلیل دقیق‌تر، ثبت مشاهدات بیشتر توصیه می‌شود."
                )
        
        if not recommendations['teacher']:
            recommendations['teacher'].append(
                "وضعیت عمومی مطلوب است یا داده کافی برای تحلیل وجود ندارد. "
                "ثبت مشاهدات بیشتر به تحلیل دقیق‌تر کمک می‌کند."
            )
        if not recommendations['parents']:
            recommendations['parents'].append(
                "وضعیت عمومی مطلوب است. به حمایت‌های فعلی ادامه دهید."
            )
        if not recommendations['counselor']:
            recommendations['counselor'].append(
                "وضعیت عمومی مطلوب است. نیاز به مداخله خاصی نیست."
            )
        
        return recommendations
    
    def calculate_trend(self, observations):
        """محاسبه روند تغییرات در طول زمان"""
        if len(observations) < 3:
            return None
        
        monthly_data = {}
        for obs in observations:
            if obs.observation_date and len(obs.observation_date) >= 7:
                month_key = obs.observation_date[:7]
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        'count': 0,
                        'total_severity': 0,
                        'observation_ids': []
                    }
                monthly_data[month_key]['count'] += 1
                monthly_data[month_key]['total_severity'] += obs.severity or 1
                monthly_data[month_key]['observation_ids'].append(obs.id)
        
        months = sorted(monthly_data.keys())
        if len(months) < 2:
            return None
        
        trend_data = []
        for month in months:
            data = monthly_data[month]
            avg_severity = round(data['total_severity'] / data['count'], 1) if data['count'] > 0 else 0
            trend_data.append({
                'month': month,
                'count': data['count'],
                'avg_severity': avg_severity,
                'observation_ids': data['observation_ids']
            })
        
        return trend_data
    
    def calculate_semester_stats(self, observations):
        """محاسبه آمار نیمسال اول و دوم"""
        if not observations:
            return None
        
        first_semester = []
        second_semester = []
        
        for obs in observations:
            if obs.observation_date and len(obs.observation_date) >= 7:
                month = int(obs.observation_date[5:7])
                if 1 <= month <= 6:
                    second_semester.append(obs)
                else:
                    first_semester.append(obs)
        
        stats = {
            'first': {
                'count': len(first_semester),
                'positive': sum(1 for o in first_semester if o.behavior_type == "مثبت"),
                'negative': sum(1 for o in first_semester if o.behavior_type == "منفی"),
                'avg_severity': round(sum(o.severity or 1 for o in first_semester) / len(first_semester), 1) if first_semester else 0,
                'observation_ids': [o.id for o in first_semester]
            },
            'second': {
                'count': len(second_semester),
                'positive': sum(1 for o in second_semester if o.behavior_type == "مثبت"),
                'negative': sum(1 for o in second_semester if o.behavior_type == "منفی"),
                'avg_severity': round(sum(o.severity or 1 for o in second_semester) / len(second_semester), 1) if second_semester else 0,
                'observation_ids': [o.id for o in second_semester]
            }
        }
        
        if stats['first']['count'] > 0 and stats['second']['count'] > 0:
            if stats['second']['avg_severity'] > stats['first']['avg_severity']:
                stats['trend'] = "افزایش"
            elif stats['second']['avg_severity'] < stats['first']['avg_severity']:
                stats['trend'] = "کاهش"
            else:
                stats['trend'] = "ثابت"
        elif stats['first']['count'] > 0 and stats['second']['count'] == 0:
            stats['trend'] = "داده ناکافی در نیمسال دوم"
        elif stats['first']['count'] == 0 and stats['second']['count'] > 0:
            stats['trend'] = "داده ناکافی در نیمسال اول"
        else:
            stats['trend'] = "داده ناکافی"
        
        return stats
    
    def generate_summary(self, observations, interventions, followups, competency_stats):
        """تولید خلاصه گزارش با تأکید بر داده‌های واقعی"""
        if not observations:
            return "هنوز مشاهده‌ای برای این پرونده ثبت نشده است. برای تحلیل دقیق‌تر، ثبت مشاهدات توصیه می‌شود."
        
        total_obs = len(observations)
        total_inter = len(interventions)
        total_follow = len(followups)
        
        positive = sum(1 for obs in observations if obs.behavior_type == "مثبت")
        negative = sum(1 for obs in observations if obs.behavior_type == "منفی")
        neutral = total_obs - positive - negative
        
        top_competencies = sorted(competency_stats.items(), key=lambda x: x[1]['avg_severity'], reverse=True)[:3]
        top_list = ", ".join([f"{c[0]} ({c[1]['avg_severity']})" for c in top_competencies]) if top_competencies else "ثبت نشده"
        
        summary = f"""
خلاصه گزارش پرونده سالانه:

تعداد کل مشاهدات: {total_obs}
• مثبت: {positive} مورد
• منفی: {negative} مورد
• خنثی: {neutral} مورد

تعداد مداخلات: {total_inter}
تعداد پیگیری‌ها: {total_follow}

شایستگی‌های برتر: {top_list}

💡 این گزارش بر اساس داده‌های ثبت‌شده در پرونده سالانه تهیه شده است.
   کاهش تعداد مشاهدات الزاماً به معنای بهبود نیست و ممکن است به دلیل کاهش ثبت باشد.
   این گزارش هیچ‌گونه تشخیص روان‌شناختی یا تحلیل شخصیتی ارائه نمی‌دهد.
"""
        return summary
    
    def _build_traceability(self, observations, interventions, followups):
        """ساخت داده‌های ردیابی"""
        traceability = {
            'observations': {obs.id: obs for obs in observations},
            'interventions': {inter.id: inter for inter in interventions},
            'followups': {follow.id: follow for follow in followups},
            'observation_ids': [obs.id for obs in observations],
            'intervention_ids': [inter.id for inter in interventions],
            'followup_ids': [follow.id for follow in followups],
        }
        return traceability
    
     
    # ============================================================
    # خروجی PDF (اصلاح شده - بدون Emoji)
    # ============================================================
    
    def export_to_pdf(self, profile_id, file_path):
        """
        خروجی گزارش به صورت فایل PDF - بدون Emoji
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
            file_path: مسیر ذخیره فایل PDF
            
        Returns:
            tuple: (success, message)
        """
        try:
            report = self.generate_student_report(profile_id)
            if not report:
                return False, "امکان تولید گزارش وجود ندارد."
            
            # ایجاد PDF
            pdf = PersianPDF(file_path)
            
            # ===== عنوان =====
            pdf.add_title("گزارش پرونده سالانه دانش آموز")
            pdf.add_spacer(0.2)
            
            # ===== اطلاعات دانش‌آموز =====
            student = report['student']
            profile = report['profile']
            academic_year = report['academic_year']
            
            info_items = [
                f"نام دانش آموز: {student.full_name}",
                f"پایه: {profile.grade_display}",
                f"کلاس: {profile.class_name or '-'}",
                f"سال تحصیلی: {academic_year.title if academic_year else '-'}",
                f"شناسه پرونده: {profile.id}",
            ]
            
            for item in info_items:
                pdf.add_text(item)
            pdf.add_spacer(0.3)
            
            # ===== خلاصه آماری =====
            pdf.add_subtitle("خلاصه آماری")
            stats_items = [
                f"* تعداد مشاهدات: {report['observations_count']}",
                f"* تعداد مداخلات: {report['interventions_count']}",
                f"* تعداد پیگیری‌ها: {report['followups_count']}",
            ]
            for item in stats_items:
                pdf.add_text(item)
            pdf.add_spacer(0.3)
            
            # ===== نقاط قوت =====
            pdf.add_subtitle("نقاط قوت")
            if report['strengths']:
                for strength in report['strengths']:
                    pdf.add_strength(
                        f"{strength['competency']} (میانگین شدت: {strength['avg_severity']})"
                    )
            else:
                pdf.add_text("* موردی یافت نشد.")
            pdf.add_spacer(0.3)
            
            # ===== زمینه‌های نیازمند حمایت =====
            pdf.add_subtitle("زمینه‌های نیازمند حمایت")
            if report['weaknesses']:
                for weakness in report['weaknesses']:
                    pdf.add_weakness(
                        f"{weakness['competency']} (میانگین شدت: {weakness['avg_severity']})"
                    )
            else:
                pdf.add_text("* موردی یافت نشد.")
            pdf.add_spacer(0.3)
            
            # ===== پیشنهادات =====
            pdf.add_subtitle("پیشنهادات")
            
            pdf.add_bold("به معلم:")
            for rec in report['recommendations']['teacher']:
                pdf.add_text(f"* {rec}")
            pdf.add_spacer(0.2)
            
            pdf.add_bold("به والدین:")
            for rec in report['recommendations']['parents']:
                pdf.add_text(f"* {rec}")
            pdf.add_spacer(0.2)
            
            pdf.add_bold("به مشاور:")
            for rec in report['recommendations']['counselor']:
                pdf.add_text(f"* {rec}")
            pdf.add_spacer(0.3)
            
            # ===== روند تغییرات =====
            if report['trend_data']:
                pdf.add_subtitle("روند تغییرات")
                for item in report['trend_data']:
                    pdf.add_text(
                        f"* {item['month']}: {item['count']} مشاهده (میانگین شدت: {item['avg_severity']})"
                    )
            pdf.add_spacer(0.3)
            
            # ===== مقایسه نیمسال‌ها =====
            if report['semester_stats']:
                stats = report['semester_stats']
                pdf.add_subtitle("مقایسه نیمسال‌ها")
                pdf.add_text(f"* نیمسال اول: {stats['first']['count']} مشاهده (میانگین شدت: {stats['first']['avg_severity']})")
                pdf.add_text(f"* نیمسال دوم: {stats['second']['count']} مشاهده (میانگین شدت: {stats['second']['avg_severity']})")
                pdf.add_text(f"* روند کلی: {stats['trend']}")
            pdf.add_spacer(0.3)
            
            # ===== جدول مشاهدات =====
            if report['observations']:
                pdf.add_subtitle("لیست مشاهدات")
                table_data = [["ردیف", "تاریخ", "محیط", "نوع", "شدت"]]
                for idx, obs in enumerate(report['observations'][:20], 1):
                    severity_str = ""
                    if obs.severity:
                        severity_str = "|" * obs.severity
                    table_data.append([
                        str(idx),
                        obs.observation_date or "",
                        obs.location or "",
                        obs.behavior_type or "خنثی",
                        severity_str
                    ])
                pdf.add_table(table_data)
            
            # ===== خلاصه نهایی =====
            pdf.add_subtitle("خلاصه")
            pdf.add_text(report['summary'])
            pdf.add_spacer(0.3)
            
            # ===== متادیتا =====
            pdf.add_separator()
            import jdatetime
            try:
                today = jdatetime.date.today()
                date_str = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
            except:
                from datetime import datetime
                date_str = datetime.now().strftime("%Y/%m/%d")
            
            pdf.add_text(f"تاریخ تهیه گزارش: {date_str}")
            pdf.add_text("PARTO - سامانه مدیریت پرونده دانش آموزان")
            pdf.add_text("پشتیبانی: support@partow.ir")
            
            # ساخت PDF
            pdf.build(file_path)
            
            return True, f"فایل PDF با موفقیت در {file_path} ذخیره شد."
            
        except Exception as e:
            return False, f"خطا در ساخت فایل PDF: {str(e)}"
    
    # ============================================================
    # خروجی Excel (موجود)
    # ============================================================
    
    def export_to_excel(self, profile_id, file_path):
        """
        خروجی گزارش به صورت فایل Excel با قابلیت ردیابی
        """
        if not OPENPYXL_AVAILABLE:
            return False, "کتابخانه openpyxl نصب نیست. لطفاً با دستور pip install openpyxl نصب کنید."
        
        report = self.generate_student_report(profile_id)
        if not report:
            return False, "امکان تولید گزارش وجود ندارد."
        
        try:
            wb = Workbook()
            student = report['student']
            profile = report['profile']
            academic_year = report['academic_year']
            
            # ===== برگه اول: اطلاعات اصلی (مشاهدات) =====
            ws1 = wb.active
            ws1.title = "گزارش اصلی"
            
            header_font = Font(name='B Nazanin', size=12, bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')
            header_alignment = Alignment(horizontal='center', vertical='center')
            
            headers = ['ردیف', 'شناسه', 'نام', 'نام خانوادگی', 'پایه', 'کلاس', 'تاریخ', 'محیط', 'شایستگی', 'نوع', 'شدت', 'شرح']
            for col, header in enumerate(headers, 1):
                cell = ws1.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            
            observations = report.get('observations', [])
            for row, obs in enumerate(observations, 2):
                ws1.cell(row=row, column=1, value=row-1)
                ws1.cell(row=row, column=2, value=obs.id)
                ws1.cell(row=row, column=3, value=student.first_name)
                ws1.cell(row=row, column=4, value=student.last_name)
                ws1.cell(row=row, column=5, value=profile.grade_display)
                ws1.cell(row=row, column=6, value=profile.class_name or '')
                ws1.cell(row=row, column=7, value=obs.observation_date or '')
                ws1.cell(row=row, column=8, value=obs.location or '')
                
                competency_name = ""
                if obs.competency_id:
                    comp = self.competency_dal.get_by_id(obs.competency_id)
                    if comp:
                        competency_name = comp.title
                ws1.cell(row=row, column=9, value=competency_name)
                
                ws1.cell(row=row, column=10, value=obs.behavior_type or '')
                ws1.cell(row=row, column=11, value=obs.severity)
                ws1.cell(row=row, column=12, value=obs.description[:100] if obs.description else '')
            
            for col in range(1, 13):
                ws1.column_dimensions[get_column_letter(col)].width = 15
            
            # ===== برگه دوم: خلاصه با قابلیت ردیابی =====
            ws2 = wb.create_sheet("خلاصه")
            
            ws2.cell(row=1, column=1, value="گزارش رشد دانش‌آموز").font = Font(name='B Nazanin', size=16, bold=True)
            ws2.merge_cells('A1:C1')
            
            info_data = [
                ("شناسه پرونده", profile.id),
                ("نام دانش‌آموز", f"{student.first_name} {student.last_name}"),
                ("پایه", profile.grade_display),
                ("کلاس", profile.class_name or ''),
                ("سال تحصیلی", academic_year.title if academic_year else ''),
                ("تعداد مشاهدات", report['observations_count']),
                ("تعداد مداخلات", report['interventions_count']),
                ("تعداد پیگیری‌ها", report['followups_count']),
            ]
            
            for row, (label, value) in enumerate(info_data, 3):
                ws2.cell(row=row, column=1, value=label).font = Font(name='B Nazanin', size=12, bold=True)
                ws2.cell(row=row, column=2, value=value).font = Font(name='B Nazanin', size=12)
                ws2.merge_cells(f'A{row}:B{row}')
            
            # نقاط قوت با شناسه
            row = 13
            ws2.cell(row=row, column=1, value="⭐ نقاط قوت").font = Font(name='B Nazanin', size=12, bold=True, color='27AE60')
            row += 1
            if report['strengths']:
                for strength in report['strengths']:
                    comp_id = strength.get('competency_id', '')
                    obs_ids = ', '.join([str(i) for i in strength.get('observation_ids', [])])
                    ws2.cell(row=row, column=1, value=f"• {strength['competency']} (میانگین شدت: {strength['avg_severity']})")
                    ws2.cell(row=row, column=2, value=f"شناسه مشاهده‌ها: {obs_ids}").font = Font(name='B Nazanin', size=9, color='7F8C8D')
                    row += 1
            else:
                ws2.cell(row=row, column=1, value="• موردی یافت نشد").font = Font(name='B Nazanin', size=11)
                row += 1
            
            # نیازهای رشدی با شناسه
            row += 1
            ws2.cell(row=row, column=1, value="🔴 زمینه‌های نیازمند حمایت").font = Font(name='B Nazanin', size=12, bold=True, color='E74C3C')
            row += 1
            if report['weaknesses']:
                for weakness in report['weaknesses']:
                    obs_ids = ', '.join([str(i) for i in weakness.get('observation_ids', [])])
                    ws2.cell(row=row, column=1, value=f"• {weakness['competency']} (میانگین شدت: {weakness['avg_severity']})")
                    ws2.cell(row=row, column=2, value=f"شناسه مشاهده‌ها: {obs_ids}").font = Font(name='B Nazanin', size=9, color='7F8C8D')
                    row += 1
            else:
                ws2.cell(row=row, column=1, value="• موردی یافت نشد").font = Font(name='B Nazanin', size=11)
                row += 1
            
            # روند تغییرات با شناسه
            row += 1
            if report['trend_data']:
                ws2.cell(row=row, column=1, value="📈 روند تغییرات").font = Font(name='B Nazanin', size=12, bold=True, color='3498DB')
                row += 1
                for item in report['trend_data']:
                    obs_ids = ', '.join([str(i) for i in item.get('observation_ids', [])])
                    ws2.cell(row=row, column=1, value=f"• {item['month']}: {item['count']} مشاهده (میانگین شدت: {item['avg_severity']})")
                    ws2.cell(row=row, column=2, value=f"شناسه مشاهده‌ها: {obs_ids}").font = Font(name='B Nazanin', size=9, color='7F8C8D')
                    row += 1
                row += 1
            
            # پیام "داده ناکافی"
            if report['observations_count'] < 3:
                ws2.cell(row=row, column=1, value="⚠️ داده کافی برای تحلیل روند وجود ندارد.").font = Font(name='B Nazanin', size=11, color='F39C12')
                ws2.cell(row=row, column=2, value=f"تعداد مشاهدات ثبت‌شده: {report['observations_count']} (حداقل ۳ مورد نیاز است)").font = Font(name='B Nazanin', size=11, color='F39C12')
                row += 1
            
            ws2.column_dimensions['A'].width = 60
            ws2.column_dimensions['B'].width = 50
            
            # ===== برگه سوم: شایستگی‌ها =====
            ws3 = wb.create_sheet("شایستگی‌ها")
            
            ws3.cell(row=1, column=1, value="شایستگی").font = Font(name='B Nazanin', size=12, bold=True)
            ws3.cell(row=1, column=2, value="تعداد").font = Font(name='B Nazanin', size=12, bold=True)
            ws3.cell(row=1, column=3, value="میانگین شدت").font = Font(name='B Nazanin', size=12, bold=True)
            ws3.cell(row=1, column=4, value="مثبت").font = Font(name='B Nazanin', size=12, bold=True)
            ws3.cell(row=1, column=5, value="منفی").font = Font(name='B Nazanin', size=12, bold=True)
            ws3.cell(row=1, column=6, value="وضعیت").font = Font(name='B Nazanin', size=12, bold=True)
            ws3.cell(row=1, column=7, value="شناسه مشاهده‌ها").font = Font(name='B Nazanin', size=12, bold=True)
            
            row = 2
            for competency, stats in report['competency_stats'].items():
                ws3.cell(row=row, column=1, value=competency).font = Font(name='B Nazanin', size=11)
                ws3.cell(row=row, column=2, value=stats['count']).font = Font(name='B Nazanin', size=11)
                ws3.cell(row=row, column=3, value=stats['avg_severity']).font = Font(name='B Nazanin', size=11)
                ws3.cell(row=row, column=4, value=stats['positive']).font = Font(name='B Nazanin', size=11)
                ws3.cell(row=row, column=5, value=stats['negative']).font = Font(name='B Nazanin', size=11)
                
                obs_ids = ', '.join([str(i) for i in stats.get('observation_ids', [])])
                ws3.cell(row=row, column=7, value=obs_ids).font = Font(name='B Nazanin', size=9, color='7F8C8D')
                
                if stats['avg_severity'] >= 4:
                    status = "عالی"
                    color = '27AE60'
                elif stats['avg_severity'] >= 3:
                    status = "خوب"
                    color = 'F39C12'
                elif stats['avg_severity'] >= 2:
                    status = "متوسط"
                    color = 'F1C40F'
                elif stats['avg_severity'] > 0:
                    status = "نیاز به توجه"
                    color = 'E67E22'
                else:
                    status = "ثبت نشده"
                    color = '95A5A6'
                
                cell = ws3.cell(row=row, column=6, value=status)
                cell.font = Font(name='B Nazanin', size=11, color=color)
                row += 1
            
            ws3.column_dimensions['A'].width = 30
            ws3.column_dimensions['B'].width = 15
            ws3.column_dimensions['C'].width = 20
            ws3.column_dimensions['D'].width = 15
            ws3.column_dimensions['E'].width = 15
            ws3.column_dimensions['F'].width = 20
            ws3.column_dimensions['G'].width = 30
            
            wb.save(file_path)
            return True, f"فایل با موفقیت در {file_path} ذخیره شد."
            
        except Exception as e:
            return False, f"خطا در ساخت فایل Excel: {str(e)}"