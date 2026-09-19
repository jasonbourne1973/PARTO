"""
سرویس تولید گزارش‌های دانش‌آموزی - نسخه اصلاح شده با PDF بدون Emoji
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.academic_year_dal import AcademicYearDAL
from dal.competency_dal import CompetencyDAL
from dal.family_context_dal import FamilyContextDAL
from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.parent_interview_dal import ParentInterviewDAL
from dal.professional_interpretation_dal import ProfessionalInterpretationDAL
from dal.screening_dal import ScreeningDAL
from dal.screening_result_dal import ScreeningResultDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from database.connection import DatabaseConnection
from services.case_timeline_service import CaseTimelineService
from utils.behavior_analysis import (
    PATTERN_MIXED,
    PATTERN_NEEDS_ATTENTION,
    PATTERN_STRENGTH,
    classify_pattern,
    count_behaviors,
    growth_direction,
    observations_volume_note,
    pattern_label,
    shares,
    summarize_by_competency,
)
from utils.logger import get_logger
from utils.persian_pdf import PersianPDF
from utils.time_utils import utc_now

logger = get_logger(__name__)

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logger.warning("⚠️ کتابخانه openpyxl نصب نیست. برای نصب: pip install openpyxl")


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
        # لایه‌های اطلاعاتی جدا از مشاهدهٔ رفتاری (بازرسی یازدهم)
        self.family_dal = FamilyContextDAL()
        self.parent_interview_dal = ParentInterviewDAL()
        self.screening_dal = ScreeningDAL()
        self.screening_result_dal = ScreeningResultDAL()
        self.interpretation_dal = ProfessionalInterpretationDAL()
        self.timeline_service = CaseTimelineService()
        self.db = DatabaseConnection()
        self.logger = get_logger(self.__class__.__name__)
    
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
        
        observations = self.observation_dal.get_by_student_profile(profile_id)
        interventions = self.intervention_dal.get_by_student_profile(profile_id)
        
        # دریافت پیگیری‌ها
        all_followups = []
        for inter in interventions:
            all_followups.extend(self.followup_dal.get_by_intervention(inter.id))
        
        # تحلیل شایستگی‌ها
        competency_stats = self.calculate_competency_stats(observations)
        # الگوهای رفتاری: قوت/ضعف بر اساس «نوع رفتار ثبت‌شده» (بازرسی یازدهم)
        behavior_patterns = summarize_by_competency(
            observations, self._competency_name, min_count=2)
        strengths = behavior_patterns['strengths']
        weaknesses = behavior_patterns['needs_attention']
        recommendations = self.generate_recommendations(
            competency_stats, observations, interventions)
        
        # روند و آمار نیمسال (ترکیب رفتارها، نه تعداد مشاهدات)
        trend_data = self.calculate_trend(observations)
        semester_stats = self.calculate_semester_stats(observations)
        # اثربخشی مداخلات: مداخله ← پیگیری ← نتیجه
        intervention_effectiveness = self.build_intervention_effectiveness(
            interventions, all_followups)
        # تفکیک لایه‌های اطلاعاتی: مشاهده / غربالگری / تفسیر حرفه‌ای
        information_layers = self.build_information_layers(profile_id, observations)
        # زمینهٔ خانوادگی: اطلاعات زمینه‌ای، نه قضاوت
        family_background = self.build_family_background(profile_id)
        
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
            'behavior_patterns': behavior_patterns,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendations': recommendations,
            'trend_data': trend_data,
            'semester_stats': semester_stats,
            'intervention_effectiveness': intervention_effectiveness,
            'information_layers': information_layers,
            'family_background': family_background,
            'summary': self.generate_summary(
                observations, interventions, all_followups, competency_stats,
                behavior_patterns=behavior_patterns,
            ),
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
        
        # بازرسی یازدهم: گزارش والدین هم رشدمحور است و فقط «فهرست مشکل»
        # نیست؛ توانمندی‌ها در کنار زمینه‌های نیازمند توجه می‌آید.
        strengths = full_report['strengths'][:5]
        needs = full_report['weaknesses'][:5]
        effectiveness = full_report.get('intervention_effectiveness', {})
        direction = self.calculate_trend_direction(full_report.get('trend_data'))

        balance = ('در این گزارش، توانمندی‌ها و زمینه‌های نیازمند توجه در '
                   'کنار هم آمده‌اند؛ تمرکز گزارش فقط بر مشکل نیست.')

        parent_report = {
            'student_name': student.full_name,
            'grade': full_report['profile'].grade_display,
            'class': full_report['profile'].class_name or 'نامشخص',
            'observations_count': full_report['observations_count'],
            'interventions_count': full_report['interventions_count'],
            'strengths': strengths,
            'weaknesses': needs,
            'intervention_effectiveness': effectiveness,
            'trend_direction': direction,
            'balance_note': balance,
            'recommendations': {
                'parents': full_report['recommendations'].get('parents', ['نظری ثبت نشده است.'])
            },
            'trend': full_report.get('trend_data', None),
            'summary': (
                f"در پروندهٔ {student.full_name} (پایهٔ "
                f"{full_report['profile'].grade_display}) "
                f"{full_report['observations_count']} مشاهدهٔ رفتاری و "
                f"{full_report['interventions_count']} مداخله ثبت شده است. "
                f"توانمندی‌های مشاهده‌شده: {len(strengths)} زمینه؛ "
                f"زمینه‌های نیازمند توجه: {len(needs)} زمینه. "
                f"جهت تغییر رفتار: {direction['label']}. "
                "این گزارش، تشخیص روان‌شناختی نیست."
            )
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
    
    def analyze_strengths_weaknesses(self, competency_stats, observations=None):
        """
        تحلیل توانمندی‌ها و زمینه‌های نیازمند توجه — **بر پایهٔ نوع رفتار**

        بازرسی یازدهم: پیش از این، قوت/ضعف با «میانگین شدت» تعیین می‌شد.
        این منطق محتوایی نادرست بود؛ چون شدت به‌تنهایی نمی‌گوید یک رفتار
        مثبت است یا منفی. اکنون:

          • نقطهٔ قوت  = الگوی تکرارشوندهٔ رفتارهای مثبت یک شایستگی
          • نیازمند توجه = الگوی تکرارشوندهٔ رفتارهای منفی یک شایستگی
          • رفتار خنثی به‌خودی‌خود نه قوت است نه ضعف
          • یک مشاهدهٔ منفرد مبنای نتیجه‌گیری نیست (حداقل ۲ مشاهده)
          • شدت فقط به‌عنوان «اطلاع اطلاعاتی» در خروجی می‌ماند

        Args:
            competency_stats: آمار شایستگی‌ها (شامل positive/negative)
            observations: در صورت وجود، الگوها از خود مشاهدات ساخته می‌شوند

        Returns:
            tuple: (strengths, weaknesses) — هر آیتم قابل ردیابی به
            شناسهٔ مشاهدات ثبت‌شده است.
        """
        if observations:
            summary = summarize_by_competency(
                observations, self._competency_name, min_count=2)
            return summary['strengths'], summary['needs_attention']

        # مسیر پشتیبان: اگر مشاهدات در دست نبود، از آمار شایستگی‌ها
        strengths, weaknesses = [], []
        for competency, stats in (competency_stats or {}).items():
            positive = stats.get('positive', 0) or 0
            negative = stats.get('negative', 0) or 0
            total = stats.get('count', 0) or 0
            kind = classify_pattern(positive, negative,
                                    max(total - positive - negative, 0), total)
            entry = {
                'competency': competency,
                'pattern': kind,
                'pattern_label': pattern_label(kind),
                'positive': positive,
                'negative': negative,
                'neutral': max(total - positive - negative, 0),
                'count': total,
                'positive_share': shares({'positive': positive, 'negative': negative,
                                          'neutral': max(total - positive - negative, 0),
                                          'total': total})['positive'],
                'negative_share': shares({'positive': positive, 'negative': negative,
                                          'neutral': max(total - positive - negative, 0),
                                          'total': total})['negative'],
                'avg_severity': stats.get('avg_severity', 0),
                'severity_is_auxiliary': True,
                'competency_id': stats.get('competency_id'),
                'observation_ids': stats.get('observation_ids', []),
                'examples': [],
            }
            if kind == PATTERN_STRENGTH:
                strengths.append(entry)
            elif kind == PATTERN_NEEDS_ATTENTION:
                weaknesses.append(entry)

        strengths.sort(key=lambda x: (x['positive'], x['count']), reverse=True)
        weaknesses.sort(key=lambda x: (x['negative'], x['count']), reverse=True)
        return strengths, weaknesses

    def _competency_name(self, competency_id):
        """نام شایستگی از شناسه (برای گزارش‌های الگومحور)."""
        comp = self.competency_dal.get_by_id(competency_id)
        return comp.title if comp else None
    
    def generate_recommendations(self, competency_stats, observations, interventions):
        """
        تولید پیشنهادهای محتاطانه و قابل ردیابی

        بازرسی یازدهم: پیشنهادها از «دادهٔ ثبت‌شده ← الگوی مشاهده‌شده ←
        پیشنهاد برای بررسی/اقدام» ساخته می‌شوند؛ نه «تشخیص قطعی ← دستور».
        هر پیشنهاد به شناسهٔ مشاهدات مرتبط اشاره می‌کند و هیچ‌گاه
        برچسب روان‌شناختی به دانش‌آموز نمی‌زند.
        """
        recommendations = {'teacher': [], 'parents': [], 'counselor': []}
        patterns = summarize_by_competency(observations or [],
                                           self._competency_name, min_count=2) \
            if observations else {'strengths': [], 'needs_attention': [], 'mixed': []}

        def _ids_text(entry, limit=6):
            ids = [str(i) for i in entry.get('observation_ids', []) if i is not None]
            return ", ".join(ids[:limit]) if ids else "-"

        def _has_intervention(entry):
            obs_ids = set(entry.get('observation_ids', []))
            return any(getattr(inter, 'observation_id', None) in obs_ids
                       for inter in (interventions or []))

        # ۱) الگوهای تکرارشوندهٔ رفتار منفی → بررسی و اقدام
        for entry in patterns['needs_attention']:
            name = entry['competency']
            trace = _ids_text(entry)
            if _has_intervention(entry):
                recommendations['teacher'].append(
                    f"در زمینهٔ «{name}» الگوی تکرارشوندهٔ رفتار منفی مشاهده شده "
                    f"({entry['negative']} مورد از {entry['count']} مشاهدهٔ ثبت‌شده؛ "
                    f"شناسهٔ مشاهدات: {trace}). یک مداخله ثبت شده است؛ "
                    "بررسی اثر آن در پیگیری بعدی پیشنهاد می‌شود."
                )
            else:
                recommendations['teacher'].append(
                    f"در زمینهٔ «{name}» الگوی تکرارشوندهٔ رفتار منفی مشاهده شده "
                    f"({entry['negative']} مورد از {entry['count']} مشاهدهٔ ثبت‌شده؛ "
                    f"شناسهٔ مشاهدات: {trace}). پیشنهاد می‌شود ابتدا با ثبت "
                    "مشاهدهٔ بیشتر، الگو را تأیید و سپس مداخلهٔ هدفمند ثبت کنید."
                )
            recommendations['counselor'].append(
                f"در زمینهٔ «{name}» الگوی تکرارشوندهٔ رفتار منفی ثبت شده است "
                f"(شناسهٔ مشاهدات: {trace}). بررسی و گفت‌وگوی حمایتی پیشنهاد "
                "می‌شود؛ این یک پیشنهاد بررسی است، نه تشخیص."
            )

        # ۲) الگوهای تکرارشوندهٔ رفتار مثبت → تقویت
        for entry in patterns['strengths']:
            name = entry['competency']
            recommendations['parents'].append(
                f"در زمینهٔ «{name}» الگوی تکرارشوندهٔ رفتار مثبت مشاهده شده است "
                f"({entry['positive']} مورد از {entry['count']} مشاهدهٔ ثبت‌شده؛ "
                f"شناسهٔ مشاهدات: {_ids_text(entry)}). تقویت و تشویق این رفتار "
                "پیشنهاد می‌شود."
            )

        # ۳) زمینه‌های ترکیبی/دادهٔ ناکافی → ثبت مشاهدهٔ بیشتر
        for entry in patterns['mixed']:
            recommendations['teacher'].append(
                f"در زمینهٔ «{entry['competency']}» رفتارهای ثبت‌شده ترکیبی است "
                f"({entry['positive']} مثبت و {entry['negative']} منفی از "
                f"{entry['count']} مشاهده). برای جمع‌بندی دقیق‌تر، ثبت مشاهدهٔ "
                "بیشتر پیشنهاد می‌شود."
            )

        # ۴) شایستگی‌های بدون مشاهده
        for competency, stats in (competency_stats or {}).items():
            if (stats.get('count', 0) or 0) == 0:
                recommendations['teacher'].append(
                    f"برای زمینهٔ «{competency}» هیچ مشاهده‌ای ثبت نشده است. "
                    "ثبت مشاهده، مبنای هر تحلیل بعدی است."
                )

        if not recommendations['teacher']:
            recommendations['teacher'].append(
                "برای این پرونده الگوی تکرارشونده‌ای ثبت نشده است یا داده کافی "
                "نیست. ثبت مشاهدهٔ بیشتر به تحلیل دقیق‌تر کمک می‌کند."
            )
        if not recommendations['parents']:
            recommendations['parents'].append(
                "برای این پرونده الگوی تکرارشوندهٔ رفتار مثبت ثبت نشده است. "
                "ثبت مشاهده‌های مثبت، تصویر کامل‌تری از توانمندی‌ها می‌دهد."
            )
        if not recommendations['counselor']:
            recommendations['counselor'].append(
                "بر پایهٔ داده‌های ثبت‌شده، الگوی نیازمند بررسی ویژه‌ای مشاهده "
                "نشده است."
            )

        return recommendations

    def calculate_trend(self, observations):
        """
        محاسبهٔ روند تغییرات بر پایهٔ **ترکیب رفتارها** در طول زمان

        بازرسی یازدهم: تعداد مشاهدات ثبت‌شده در یک ماه، شاخص رشد دانش‌آموز
        نیست (کم شدن ثبت ≠ بهبود؛ زیاد شدن ثبت ≠ بدتر شدن). پس هر بازه با
        سهم رفتارهای مثبت/منفی توصیف می‌شود و «جهت تغییر» از همین سهم‌ها
        به دست می‌آید. تعداد مشاهدات فقط «حجم ثبت و پایش» است.
        """
        if len(observations) < 3:
            return None

        monthly_data = {}
        for obs in observations:
            if obs.observation_date and len(obs.observation_date) >= 7:
                month_key = obs.observation_date[:7]
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        'count': 0,
                        'positive': 0,
                        'negative': 0,
                        'neutral': 0,
                        'total_severity': 0,
                        'observation_ids': []
                    }
                bucket = monthly_data[month_key]
                bucket['count'] += 1
                bucket['total_severity'] += obs.severity or 1
                bucket['observation_ids'].append(obs.id)
                if obs.behavior_type == "مثبت":
                    bucket['positive'] += 1
                elif obs.behavior_type == "منفی":
                    bucket['negative'] += 1
                else:
                    bucket['neutral'] += 1

        months = sorted(monthly_data.keys())
        if len(months) < 2:
            return None

        trend_data = []
        for month in months:
            data = monthly_data[month]
            count = data['count']
            share = shares({'positive': data['positive'], 'negative': data['negative'],
                            'neutral': data['neutral'], 'total': count})
            trend_data.append({
                'month': month,
                'label': month,
                'count': count,                       # حجم ثبت و پایش
                'positive': data['positive'],
                'negative': data['negative'],
                'neutral': data['neutral'],
                'positive_share': share['positive'],
                'negative_share': share['negative'],
                # شدت: فقط اطلاعات تکمیلی
                'avg_severity': round(data['total_severity'] / count, 1) if count else 0,
                'severity_is_auxiliary': True,
                'observation_ids': data['observation_ids'],
            })
        return trend_data

    def calculate_trend_direction(self, trend_data):
        """جهت تغییر رفتار در طول زمان (فقط از ترکیب رفتارها)."""
        return growth_direction(trend_data or [])
    
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
        
        # بازرسی یازدهم: مقایسهٔ نیمسال‌ها بر پایهٔ «ترکیب رفتارها» است،
        # نه میانگین شدت. شدت تنها به‌عنوان اطلاعات تکمیلی گزارش می‌شود.
        for key in ('first', 'second'):
            share = shares({'positive': stats[key]['positive'],
                            'negative': stats[key]['negative'],
                            'neutral': stats[key]['count'] - stats[key]['positive']
                                       - stats[key]['negative'],
                            'total': stats[key]['count']})
            stats[key]['positive_share'] = share['positive']
            stats[key]['negative_share'] = share['negative']

        direction = growth_direction([
            {'label': 'نیمسال اول', 'positive': stats['first']['positive'],
             'negative': stats['first']['negative'],
             'neutral': max(stats['first']['count'] - stats['first']['positive']
                            - stats['first']['negative'], 0),
             'total': stats['first']['count']},
            {'label': 'نیمسال دوم', 'positive': stats['second']['positive'],
             'negative': stats['second']['negative'],
             'neutral': max(stats['second']['count'] - stats['second']['positive']
                            - stats['second']['negative'], 0),
             'total': stats['second']['count']},
        ])
        stats['direction'] = direction
        stats['trend'] = direction['label']
        stats['trend_note'] = direction['message']
        stats['volume_note'] = direction['volume_note']

        if stats['first']['count'] > 0 and stats['second']['count'] > 0:
            # اختلاف شدت فقط برای اطلاع (تکمیلی)
            stats['severity_change'] = round(
                stats['second']['avg_severity'] - stats['first']['avg_severity'], 1)
        elif stats['first']['count'] > 0 and stats['second']['count'] == 0:
            stats['trend'] = "داده ناکافی در نیمسال دوم"
        elif stats['first']['count'] == 0 and stats['second']['count'] > 0:
            stats['trend'] = "داده ناکافی در نیمسال اول"
        else:
            stats['trend'] = "داده ناکافی"
        
        return stats
    
    def generate_summary(self, observations, interventions, followups,
                         competency_stats, behavior_patterns=None):
        """
        جمع‌بندی سالانهٔ رشد (بازرسی یازدهم)

        بر پایهٔ اطلاعات موجود نشان می‌دهد: توانمندی‌ها، زمینه‌های نیازمند
        توجه، اقدامات انجام‌شده، نتیجهٔ پیگیری‌ها و روند کلی تغییر رفتار
        در همان سال. تصویر دانش‌آموز فقط «مجموعه‌ای از مشکلات» نیست.
        """
        counts = count_behaviors(observations)
        if not observations:
            return ("هنوز مشاهده‌ای برای این پرونده ثبت نشده است. "
                    "ثبت مشاهده، مبنای تحلیل رشد است.")

        patterns = behavior_patterns or summarize_by_competency(
            observations, self._competency_name, min_count=2)
        share = shares(counts)

        strengths = "؛ ".join(
            f"{e['competency']} ({e['positive']} رفتار مثبت از {e['count']} مشاهده)"
            for e in patterns['strengths'][:3]) or "الگوی تکرارشوندهٔ رفتار مثبت ثبت نشده است"
        needs = "؛ ".join(
            f"{e['competency']} ({e['negative']} رفتار منفی از {e['count']} مشاهده)"
            for e in patterns['needs_attention'][:3]) or "الگوی تکرارشوندهٔ رفتار منفی ثبت نشده است"

        # نتیجهٔ پیگیری‌ها (مداخله ← پیگیری ← نتیجه)
        effectiveness = self.build_intervention_effectiveness(interventions, followups)
        outcomes = effectiveness['outcome_counts']
        outcome_text = (
            f"بهبود مشاهده‌شده: {outcomes.get('improved', 0)}؛ "
            f"بدون تغییر قابل مشاهده: {outcomes.get('no_change', 0)}؛ "
            f"تداوم وضعیت: {outcomes.get('continued', 0)}؛ "
            f"نیازمند پیگیری بیشتر: {outcomes.get('needs_more', 0)}؛ "
            f"بدون پیگیری ثبت‌شده: {outcomes.get('no_followup', 0)}"
        )

        direction = growth_direction([
            {'label': p['month'], 'positive': p['positive'], 'negative': p['negative'],
             'neutral': p['neutral'], 'total': p['count']}
            for p in (self.calculate_trend(observations) or [])
        ])

        summary = f"""
جمع‌بندی سالانهٔ رشد دانش‌آموز:

۱) توانمندی‌ها (الگوی رفتار مثبت): {strengths}
۲) زمینه‌های نیازمند توجه (الگوی رفتار منفی): {needs}
۳) ترکیب رفتارهای ثبت‌شده: {counts['positive']} مثبت، {counts['negative']} منفی و {counts['neutral']} خنثی
   از مجموع {counts['total']} مشاهده (سهم مثبت {share['positive']}٪، سهم منفی {share['negative']}٪)
۴) اقدامات و نتایج: {len(interventions)} مداخله و {len(followups)} پیگیری ثبت شده است.
   نتیجهٔ پیگیری‌ها → {outcome_text}
۵) روند تغییر رفتار در سال: {direction['label']} — {direction['message']}

یادداشت‌های محتوایی:
• {observations_volume_note(counts)}
• {direction['volume_note']}
• این جمع‌بندی بر پایهٔ رفتارهای ثبت‌شده است و هیچ تشخیص روان‌شناختی
  یا برچسب قطعی دربارهٔ دانش‌آموز ارائه نمی‌کند.
• مقایسه فقط با خود دانش‌آموز در طول زمان انجام می‌شود، نه با دیگران.
"""
        return summary

    def build_intervention_effectiveness(self, interventions, followups):
        """
        اتصال «مشکل/نیاز مشاهده‌شده ← مداخله ← پیگیری ← نتیجه»

        Returns:
            dict: {'items': [...], 'outcome_counts': {...}, 'summary': str}
        """
        by_intervention = {}
        for follow in followups or []:
            inter_id = getattr(follow, 'intervention_id', None)
            by_intervention.setdefault(inter_id, []).append(follow)

        items = []
        outcome_counts = {'improved': 0, 'no_change': 0, 'continued': 0,
                          'new_status': 0, 'insufficient': 0, 'needs_more': 0,
                          'no_followup': 0}

        for inter in interventions or []:
            related = sorted(by_intervention.get(inter.id, []),
                             key=lambda f: f.date or '')
            followup_items = []
            for follow in related:
                key = getattr(follow, 'result_type', None) or 'insufficient'
                outcome_counts[key if key in outcome_counts else 'insufficient'] += 1
                followup_items.append({
                    'date': follow.date,
                    'method': follow.method or 'پیگیری',
                    'status': follow.status_display,
                    'result_type': key,
                    'result_label': follow.result_type_display,
                    'result_description': follow.result_description or '',
                    'observation_ids': [follow.id] if follow.id else [],
                })
            if not related:
                outcome_counts['no_followup'] += 1
            items.append({
                'intervention_id': inter.id,
                'type': inter.type_display,
                'date': inter.date,
                'goal': inter.goal or '',
                'description': inter.description or '',
                'status': inter.status_display,
                'observation_id': inter.observation_id,
                'followups': followup_items,
                'outcome': (followup_items[-1]['result_label'] if followup_items
                            else 'پیگیری ثبت نشده است'),
                'outcome_known': bool(followup_items),
            })

        known = sum(1 for i in items if i['outcome_known'])
        summary = (f"از {len(items)} مداخلهٔ ثبت‌شده، برای {known} مورد نتیجهٔ "
                   "پیگیری ثبت شده است.")
        return {'items': items, 'outcome_counts': outcome_counts, 'summary': summary}

    def build_information_layers(self, profile_id, observations):
        """
        تفکیک سه لایهٔ اطلاعاتی (بازرسی یازدهم)

          • مشاهدهٔ رفتاری: آنچه کارکنان مدرسه ثبت کرده‌اند.
          • غربالگری: نتیجهٔ یک ابزار/آزمون مشخص (تشخیص نیست).
          • تفسیر حرفه‌ای: ثبت نظر متخصص بر پایهٔ اطلاعات موجود.

        این لایه‌ها با هم مخلوط نمی‌شوند و نتیجهٔ غربالگری هرگز به‌عنوان
        تشخیص یا برچسب قطعی نمایش داده نمی‌شود.
        """
        counts = count_behaviors(observations)
        layers = {
            'observation': {
                'title': 'مشاهدهٔ رفتاری (ثبت کارکنان مدرسه)',
                'counts': counts,
                'note': observations_volume_note(counts),
                'items': [{
                    'date': getattr(o, 'observation_date', None),
                    'behavior': getattr(o, 'behavior', '') or '',
                    'type': getattr(o, 'behavior_type', '') or '',
                    'severity': getattr(o, 'severity', None),
                } for o in (observations or [])[:20]],
            },
            'screening': {'title': 'غربالگری (نتیجهٔ ابزار/آزمون)', 'items': [],
                          'note': ('نتیجهٔ غربالگری، «یافتهٔ ابزار» است و '
                                   'به‌معنای تشخیص روان‌شناختی یا برچسب قطعی '
                                   'برای دانش‌آموز نیست.')},
            'interpretation': {'title': 'تفسیر حرفه‌ای (نظر متخصص)',
                               'items': [],
                               'note': ('تفسیر حرفه‌ای، ثبت نظر متخصص بر پایهٔ '
                                        'اطلاعات موجود است و جای تشخیص بالینی '
                                        'را نمی‌گیرد.')},
            'chain_note': ('مسیر اطلاعات: مشاهدهٔ رفتاری ← غربالگری ← '
                           'تفسیر حرفه‌ای؛ هر لایه معنای مستقل خود را دارد.'),
        }

        try:
            for screening in self.screening_dal.get_by_student_profile(profile_id) or []:
                layers['screening']['items'].append({
                    'tool': getattr(screening, 'tool_display_name', None)
                            or getattr(screening, 'tool_name', '') or 'ابزار غربالگری',
                    'date': getattr(screening, 'execution_date', None),
                    'status': screening.status_display,
                    'domain': getattr(screening, 'domain', '') or '',
                    'total_score': getattr(screening, 'total_score', None),
                    'note': 'یافتهٔ ابزار — نه تشخیص',
                })
        except Exception as e:
            self.logger.warning(f"خواندن لایهٔ غربالگری ممکن نشد: {e}")

        try:
            for interp in self.interpretation_dal.get_by_student_profile(profile_id) or []:
                layers['interpretation']['items'].append({
                    'level': interp.level_display,
                    'title': interp.title or '',
                    'summary': interp.summary or '',
                    'status': interp.status_display,
                    'next_steps': interp.next_steps or '',
                })
        except Exception as e:
            self.logger.warning(f"خواندن لایهٔ تفسیر حرفه‌ای ممکن نشد: {e}")

        return layers

    def build_family_background(self, profile_id):
        """
        زمینهٔ خانوادگی و گفت‌وگوهای والدین (بازرسی یازدهم)

        این اطلاعات **زمینه‌ای** است برای درک بهتر وضعیت دانش‌آموز و
        هرگز مبنای قضاوت دربارهٔ خانواده یا برچسب‌گذاری نیست.
        """
        background = {
            'note': ('اطلاعات خانواده، زمینه‌ای است؛ مبنای قضاوت دربارهٔ خانواده '
                     'یا دانش‌آموز نیست و فقط برای درک بهتر وضعیت رشد او '
                     'ثبت می‌شود.'),
            'contexts': [],
            'interviews': [],
        }
        def _as_list(value):
            """DAL ممکن است یک رکورد یا فهرست برگرداند؛ هر دو حالت را بپذیر."""
            if value is None:
                return []
            if isinstance(value, (list, tuple)):
                return list(value)
            return [value]

        try:
            for ctx in _as_list(self.family_dal.get_by_student_profile(profile_id)):
                background['contexts'].append({
                    'guardian_status': getattr(ctx, 'guardian_status_display', None)
                    or getattr(ctx, 'guardian_status', '') or '-',
                    'parental_support': getattr(ctx, 'parental_support', None) or '-',
                    'economic_status': getattr(ctx, 'economic_status', None) or '-',
                    'family_stress': getattr(ctx, 'family_stress', None) or '-',
                    'study_space': ('دارد' if getattr(ctx, 'has_study_space', 0) else 'ندارد'),
                    'notes': getattr(ctx, 'educational_notes', '') or '',
                })
        except Exception as e:
            self.logger.warning(f"خواندن زمینهٔ خانوادگی ممکن نشد: {e}")

        try:
            for iv in _as_list(self.parent_interview_dal.get_by_student_profile(profile_id)):
                background['interviews'].append({
                    'date': getattr(iv, 'interview_date', None),
                    'method': getattr(iv, 'method_display', None)
                    or getattr(iv, 'interview_method', '') or '-',
                    'topic': getattr(iv, 'topic', '') or '',
                    'status': getattr(iv, 'status_display', None)
                    or getattr(iv, 'status', '') or '-',
                    'summary': getattr(iv, 'summary', '') or '',
                    'result': getattr(iv, 'result', '') or '',
                    'next_action': getattr(iv, 'next_action', '') or '',
                })
        except Exception as e:
            self.logger.warning(f"خواندن مصاحبه‌های والدین ممکن نشد: {e}")

        return background

    def generate_growth_narrative(self, student_id):
        """
        روایت رشد چندسالهٔ دانش‌آموز (بازرسی یازدهم)

        برای گزارش پایان دورهٔ ابتدایی: مسیر رشد دانش‌آموز در سال‌های
        مختلف با هم نشان داده می‌شود — توانمندی‌ها، زمینه‌های نیازمند
        توجه، اقدامات، نتایج و جهت تغییر. مقایسه فقط با خودِ دانش‌آموز
        در طول زمان است.
        """
        profiles = self.profile_dal.get_all_profiles_for_student(student_id)
        if not profiles:
            return {'has_data': False,
                    'message': 'برای این دانش‌آموز پرونده‌ای ثبت نشده است.'}

        years = []
        timeline_periods = []
        for profile in profiles:
            observations = self.observation_dal.get_by_student_profile(profile.id)
            interventions = self.intervention_dal.get_by_student_profile(profile.id)
            followups = []
            for inter in interventions:
                followups.extend(self.followup_dal.get_by_intervention(inter.id))

            counts = count_behaviors(observations)
            patterns = summarize_by_competency(observations, self._competency_name, 2)
            effectiveness = self.build_intervention_effectiveness(interventions, followups)

            years.append({
                'year': getattr(profile, 'academic_year_title', 'نامشخص'),
                'grade': profile.grade_display,
                'counts': counts,
                'shares': shares(counts),
                'strengths': [{'competency': e['competency'],
                               'positive': e['positive'], 'count': e['count']}
                              for e in patterns['strengths'][:3]],
                'needs_attention': [{'competency': e['competency'],
                                     'negative': e['negative'], 'count': e['count']}
                                    for e in patterns['needs_attention'][:3]],
                'interventions_count': len(interventions),
                'outcomes': effectiveness['outcome_counts'],
                'volume_note': observations_volume_note(counts),
                'has_data': counts['total'] > 0,
            })
            timeline_periods.append({
                'label': getattr(profile, 'academic_year_title', 'نامشخص'),
                'positive': counts['positive'], 'negative': counts['negative'],
                'neutral': counts['neutral'], 'total': counts['total'],
            })

        direction = growth_direction(timeline_periods)
        years_with_data = [y for y in years if y['has_data']]
        narrative = (
            f"مسیر رشد دانش‌آموز در {len(years)} سال تحصیلی ثبت‌شده بررسی شد"
            f"؛ در {len(years_with_data)} سال، مشاهدهٔ رفتاری ثبت شده است. "
            f"جهت کلی تغییر رفتار: {direction['label']}. {direction['message']} "
            f"{direction['volume_note']} این روایت بر پایهٔ رفتارهای ثبت‌شده "
            "است و شامل تشخیص روان‌شناختی یا مقایسه با دانش‌آموزان دیگر نیست."
        )
        return {'has_data': bool(years_with_data), 'years': years,
                'direction': direction, 'narrative': narrative}

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
            
            # ===== توانمندی‌ها (الگوی رفتار مثبت) =====
            pdf.add_subtitle("توانمندی‌ها (الگوی تکرارشوندهٔ رفتار مثبت)")
            if report['strengths']:
                for strength in report['strengths']:
                    line = (f"{strength['competency']} — "
                            f"{strength['positive']} رفتار مثبت از "
                            f"{strength['count']} مشاهدهٔ ثبت‌شده")
                    if strength.get('examples'):
                        line += f" (نمونه: {strength['examples'][0]})"
                    pdf.add_strength(line)
            else:
                pdf.add_text("* الگوی تکرارشوندهٔ رفتار مثبت ثبت نشده است.")
            pdf.add_spacer(0.3)

            # ===== زمینه‌های نیازمند توجه =====
            pdf.add_subtitle("زمینه‌های نیازمند توجه (الگوی تکرارشوندهٔ رفتار منفی)")
            if report['weaknesses']:
                for weakness in report['weaknesses']:
                    line = (f"{weakness['competency']} — "
                            f"{weakness['negative']} رفتار منفی از "
                            f"{weakness['count']} مشاهدهٔ ثبت‌شده")
                    if weakness.get('examples'):
                        line += f" (نمونه: {weakness['examples'][0]})"
                    pdf.add_weakness(line)
            else:
                pdf.add_text("* الگوی تکرارشوندهٔ رفتار منفی ثبت نشده است.")
            pdf.add_text("توجه: این فهرست بر پایهٔ رفتارهای ثبت‌شده است و "
                         "به‌معنای تشخیص یا برچسب نیست.")
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
            
            # ===== روند تغییر رفتار =====
            if report['trend_data']:
                pdf.add_subtitle("روند تغییر رفتار (بر پایهٔ ترکیب رفتارها)")
                for item in report['trend_data']:
                    pdf.add_text(
                        f"* {item['month']}: {item['positive']} مثبت، "
                        f"{item['negative']} منفی، {item['neutral']} خنثی "
                        f"(سهم مثبت {item['positive_share']}٪) — "
                        f"حجم ثبت: {item['count']} مشاهده"
                    )
                direction = self.calculate_trend_direction(report['trend_data'])
                pdf.add_text(f"* جهت تغییر: {direction['label']} — {direction['message']}")
                pdf.add_text(f"* {direction['volume_note']}")
            pdf.add_spacer(0.3)

            # ===== مقایسه نیمسال‌ها =====
            if report['semester_stats']:
                stats = report['semester_stats']
                pdf.add_subtitle("مقایسه نیمسال‌ها")
                pdf.add_text(
                    f"* نیمسال اول: {stats['first']['positive']} مثبت، "
                    f"{stats['first']['negative']} منفی از {stats['first']['count']} "
                    f"مشاهده (سهم مثبت {stats['first'].get('positive_share', 0)}٪)")
                pdf.add_text(
                    f"* نیمسال دوم: {stats['second']['positive']} مثبت، "
                    f"{stats['second']['negative']} منفی از {stats['second']['count']} "
                    f"مشاهده (سهم مثبت {stats['second'].get('positive_share', 0)}٪)")
                pdf.add_text(f"* جهت تغییر رفتار: {stats.get('trend', '-')}")
                if stats.get('trend_note'):
                    pdf.add_text(f"* {stats['trend_note']}")
                if stats.get('volume_note'):
                    pdf.add_text(f"* {stats['volume_note']}")
            pdf.add_spacer(0.3)

            # ===== اثربخشی مداخلات (مداخله ← پیگیری ← نتیجه) =====
            effectiveness = report.get('intervention_effectiveness') or {}
            if effectiveness.get('items'):
                pdf.add_subtitle("اثربخشی مداخلات (اقدام ← پیگیری ← نتیجه)")
                for item in effectiveness['items'][:10]:
                    pdf.add_bold(f"{item['type']} — {item['date'] or ''}")
                    if item.get('goal'):
                        pdf.add_text(f"* هدف: {item['goal']}")
                    if item['followups']:
                        for follow in item['followups'][:3]:
                            pdf.add_text(
                                f"* پیگیری {follow['date'] or ''} "
                                f"({follow['method']}): {follow['result_label']}"
                                + (f" — {follow['result_description']}"
                                   if follow['result_description'] else "")
                            )
                    else:
                        pdf.add_text("* پیگیری ثبت نشده است؛ نتیجهٔ مداخله "
                                     "قابل ارزیابی نیست.")
                pdf.add_text(f"* {effectiveness['summary']}")
                pdf.add_spacer(0.3)

            # ===== زمینهٔ خانوادگی (اطلاعات زمینه‌ای) =====
            family = report.get('family_background') or {}
            if family.get('contexts') or family.get('interviews'):
                pdf.add_subtitle("زمینهٔ خانوادگی و گفت‌وگو با والدین")
                pdf.add_text(f"* {family.get('note', '')}")
                for ctx in family['contexts'][:3]:
                    pdf.add_text(
                        f"* وضعیت سرپرست: {ctx['guardian_status']} | "
                        f"حمایت والدین: {ctx['parental_support']} | "
                        f"فضای مطالعه: {ctx['study_space']}"
                    )
                for iv in family['interviews'][:5]:
                    line = (f"* گفت‌وگو {iv['date'] or ''} ({iv['method']}) — "
                            f"{iv['topic'] or 'بدون موضوع ثبت‌شده'} | "
                            f"وضعیت: {iv['status']}")
                    pdf.add_text(line)
                    if iv.get('result'):
                        pdf.add_text(f"  نتیجهٔ گفت‌وگو: {iv['result']}")
                pdf.add_spacer(0.3)

            # ===== تفکیک لایه‌های اطلاعاتی =====
            layers = report.get('information_layers') or {}
            if layers:
                pdf.add_subtitle("لایه‌های اطلاعاتی (مشاهده / غربالگری / تفسیر)")
                pdf.add_text(f"* {layers.get('chain_note', '')}")
                obs_layer = layers.get('observation', {})
                pdf.add_bold(f"{obs_layer.get('title', 'مشاهدهٔ رفتاری')}")
                pdf.add_text(f"* {obs_layer.get('note', '')}")
                scr = layers.get('screening', {})
                pdf.add_bold(scr.get('title', 'غربالگری'))
                if scr.get('items'):
                    for item in scr['items'][:5]:
                        pdf.add_text(
                            f"* {item['tool']} — {item['date'] or ''} | "
                            f"وضعیت: {item['status']} | یافته: "
                            f"{item['total_score'] if item['total_score'] is not None else '-'}"
                        )
                else:
                    pdf.add_text("* نتیجهٔ غربالگری ثبت نشده است.")
                pdf.add_text(f"* {scr.get('note', '')}")
                interp = layers.get('interpretation', {})
                pdf.add_bold(interp.get('title', 'تفسیر حرفه‌ای'))
                if interp.get('items'):
                    for item in interp['items'][:5]:
                        pdf.add_text(f"* [{item['level']}] {item['title']} — "
                                     f"{item['status']}")
                        if item.get('summary'):
                            pdf.add_text(f"  {item['summary']}")
                else:
                    pdf.add_text("* تفسیر حرفه‌ای ثبت نشده است.")
                pdf.add_text(f"* {interp.get('note', '')}")
                pdf.add_spacer(0.3)

            # ===== سابقهٔ رشد چندساله =====
            try:
                narrative = self.generate_growth_narrative(student.id)
            except Exception as exc:
                narrative = None
                self.logger.warning(f"ساخت روایت رشد ممکن نشد: {exc}")
            if narrative and narrative.get('has_data'):
                pdf.add_subtitle("سابقهٔ رشد و مسیر طی‌شده (چندساله)")
                pdf.add_text(f"* {narrative['narrative']}")
                for year in narrative['years']:
                    if not year['has_data']:
                        continue
                    strength_text = "؛ ".join(
                        f"{s['competency']} ({s['positive']} رفتار مثبت)"
                        for s in year['strengths']) or "ثبت نشده"
                    need_text = "؛ ".join(
                        f"{n['competency']} ({n['negative']} رفتار منفی)"
                        for n in year['needs_attention']) or "ثبت نشده"
                    pdf.add_bold(f"سال {year['year']} (پایهٔ {year['grade']})")
                    pdf.add_text(f"* توانمندی‌ها: {strength_text}")
                    pdf.add_text(f"* زمینه‌های نیازمند توجه: {need_text}")
                    pdf.add_text(
                        f"* تعداد مداخلات: {year['interventions_count']} | "
                        f"ترکیب رفتارها: {year['counts']['positive']} مثبت، "
                        f"{year['counts']['negative']} منفی از "
                        f"{year['counts']['total']} مشاهده"
                    )
                    outcomes = year['outcomes']
                    pdf.add_text(
                        f"* نتایج پیگیری: بهبود {outcomes.get('improved', 0)} | "
                        f"بدون تغییر {outcomes.get('no_change', 0)} | "
                        f"نیازمند پیگیری بیشتر {outcomes.get('needs_more', 0)} | "
                        f"بدون پیگیری {outcomes.get('no_followup', 0)}"
                    )
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
            except Exception:
                date_str = utc_now().strftime("%Y/%m/%d")
            
            pdf.add_text(f"تاریخ تهیه گزارش: {date_str}")
            pdf.add_text("PARTO - سامانه مدیریت پرونده دانش آموزان")
            pdf.add_text("پشتیبانی: support@partow.ir")
            
            # ساخت PDF
            pdf.build(file_path)
            
            return True, f"فایل PDF با موفقیت در {file_path} ذخیره شد."
            
        except Exception as e:
            return False, f"خطا در ساخت فایل PDF: {e!s}"
    
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
                    obs_ids = ', '.join([str(i) for i in strength.get('observation_ids', [])])
                    ws2.cell(row=row, column=1, value=(
                        f"• {strength['competency']} — {strength['positive']} رفتار مثبت "
                        f"از {strength['count']} مشاهده"))
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
                    ws2.cell(row=row, column=1, value=(
                        f"• {weakness['competency']} — {weakness['negative']} رفتار منفی "
                        f"از {weakness['count']} مشاهده"))
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
                    ws2.cell(row=row, column=1, value=(
                        f"• {item['month']}: {item['positive']} مثبت، {item['negative']} منفی، "
                        f"{item['neutral']} خنثی (سهم مثبت {item['positive_share']}٪) — "
                        f"حجم ثبت: {item['count']}"))
                    ws2.cell(row=row, column=2, value=f"شناسه مشاهده‌ها: {obs_ids}").font = Font(name='B Nazanin', size=9, color='7F8C8D')
                    row += 1
                row += 1
            
            # اثربخشی مداخلات (مداخله ← پیگیری ← نتیجه)
            effectiveness = report.get('intervention_effectiveness') or {}
            if effectiveness.get('items'):
                row += 1
                ws2.cell(row=row, column=1,
                         value="🔗 اثربخشی مداخلات (اقدام ← پیگیری ← نتیجه)"
                         ).font = Font(name='B Nazanin', size=12, bold=True, color='8E44AD')
                row += 1
                for item in effectiveness['items']:
                    outcome = item['outcome']
                    ws2.cell(row=row, column=1, value=(
                        f"• {item['type']} ({item['date'] or '-'}): {outcome}"))
                    if item['followups']:
                        ws2.cell(row=row, column=2, value=(
                            f"پیگیری‌ها: {len(item['followups'])} | نتیجهٔ آخر: "
                            f"{item['followups'][-1]['result_label']}"),
                            ).font = Font(name='B Nazanin', size=9, color='7F8C8D')
                    else:
                        ws2.cell(row=row, column=2,
                                 value="پیگیری ثبت نشده است؛ نتیجه قابل ارزیابی نیست."
                                 ).font = Font(name='B Nazanin', size=9, color='95A5A6')
                    row += 1
                ws2.cell(row=row, column=1, value=f"• {effectiveness['summary']}")
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
            ws3.cell(row=1, column=6, value="الگو (بر پایهٔ نوع رفتار)").font = Font(name='B Nazanin', size=12, bold=True)
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
                
                # بازرسی یازدهم: وضعیت هر زمینه از «نوع رفتارهای ثبت‌شده»
                # می‌آید، نه از میانگین شدت. شدت فقط در ستون جداگانه
                # به‌عنوان اطلاعات تکمیلی نمایش داده می‌شود.
                _positive = stats.get('positive', 0) or 0
                _negative = stats.get('negative', 0) or 0
                _total = stats.get('count', 0) or 0
                kind = classify_pattern(_positive, _negative,
                                        max(_total - _positive - _negative, 0), _total)
                if kind == PATTERN_STRENGTH:
                    status, color = "الگوی مثبت تکرارشونده", '27AE60'
                elif kind == PATTERN_NEEDS_ATTENTION:
                    status, color = "الگوی منفی تکرارشونده", 'E74C3C'
                elif kind == PATTERN_MIXED:
                    status, color = "الگوی ترکیبی", 'F39C12'
                else:
                    status, color = "داده ناکافی", '95A5A6'
                
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
            return False, f"خطا در ساخت فایل Excel: {e!s}"