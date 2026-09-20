"""
سرویس تحلیل روند دانش‌آموز - بر اساس خود دانش‌آموز و بدون مقایسه با دیگران
با پشتیبانی از تحلیل چندساله
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.competency_dal import CompetencyDAL
from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from services.base_service import BaseService
from utils.behavior_analysis import (
    classify_pattern,
    count_behaviors,
    growth_direction,
    observations_volume_note,
    pattern_label,
    shares,
)

# ===== اصلاح =====
# نسخه قبلی اینجا این خط را داشت:
#     from utils.persian_calendar import PersianCalendarWidget
#
# `PersianCalendarWidget` یک ویجت Qt است و در این فایل **هرگز استفاده
# نمی‌شد** (grep روی کل فایل فقط همین خط import را نشان می‌داد).
# همین یک خط بی‌مصرف باعث می‌شد کل لایه سرویس به PySide6 وابسته شود:
#     services/trend_analysis_service
#         → utils/persian_calendar → PySide6.QtWidgets
# و چون `student_service.py` هم `TrendAnalysisService` را import می‌کند،
# نتیجه این بود که هر استفاده بدون رابط گرافیکی از سرویس‌ها (تست‌ها،
# اسکریپت‌ها، تولید گزارش از خط فرمان) با خطای import Qt از کار می‌افتاد.


class TrendAnalysisService(BaseService):
    """
    سرویس تحلیل روند دانش‌آموز
    
    ویژگی‌ها:
    - تحلیل بر اساس خود دانش‌آموز (بدون مقایسه با دیگران)
    - نمایش تغییرات در طول زمان
    - گروه‌بندی بر اساس ماه یا هفته
    - نمایش روند مثبت/منفی/خنثی
    - تحلیل چندساله
    """
    
    def __init__(self):
        super().__init__()
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.competency_dal = CompetencyDAL()
        self.profile_dal = StudentAcademicProfileDAL()
    
    def analyze_student_trend(self, profile_id, period='monthly'):
        """
        تحلیل روند دانش‌آموز بر اساس مشاهدات
        
        Args:
            profile_id: شناسه پرونده دانش‌آموز
            period: بازه زمانی ('monthly', 'weekly', 'daily')
            
        Returns:
            dict: شامل داده‌های روند
        """
        try:
            # دریافت مشاهدات
            observations = self.observation_dal.get_by_student_profile(profile_id)
            if not observations:
                return self._empty_trend()
            
            # گروه‌بندی بر اساس زمان
            grouped_data = self._group_observations_by_time(observations, period)
            
            # محاسبه آمار هر بازه
            trend_data = self._calculate_period_stats(grouped_data)
            
            # تحلیل روند کلی
            overall_trend = self._analyze_overall_trend(trend_data)
            
            # دریافت شایستگی‌های برتر
            top_competencies = self._get_top_competencies(observations)

            # جهت تغییر = ترکیب رفتارها (نه تعداد مشاهدات)
            direction = growth_direction([
                {'label': p['label'], 'positive': p['positive'],
                 'negative': p['negative'], 'neutral': p['neutral'],
                 'total': p['total']}
                for p in trend_data
            ])
            
            return {
                'success': True,
                'profile_id': profile_id,
                'period': period,
                'trend_data': trend_data,
                'overall_trend': overall_trend,
                'direction': direction,
                'volume_note': observations_volume_note(count_behaviors(observations)),
                'total_observations': len(observations),
                'top_competencies': top_competencies,
                'positive_count': sum(1 for o in observations if o.behavior_type == "مثبت"),
                'negative_count': sum(1 for o in observations if o.behavior_type == "منفی"),
                'neutral_count': sum(1 for o in observations if o.behavior_type == "خنثی"),
            }
            
        except Exception as e:
            self.logger.error(f"خطا در تحلیل روند: {e}")
            return self._empty_trend(error=str(e))
    
    def get_student_timeline(self, profile_id):
        """
        دریافت Timeline دانش‌آموز برای نمایش روند
        
        Returns:
            list: لیست رویدادهای مرتب‌شده
        """
        try:
            events = []
            
            # مشاهدات
            observations = self.observation_dal.get_by_student_profile(profile_id)
            for obs in observations:
                events.append({
                    'date': obs.observation_date,
                    'type': 'observation',
                    'type_display': 'مشاهده',
                    'title': obs.behavior or 'رفتار ثبت‌شده',
                    'description': obs.description or '',
                    'details': {
                        'behavior': obs.behavior,
                        'behavior_type': obs.behavior_type,
                        'severity': obs.severity,
                        'location': obs.location,
                    }
                })
            
            # مداخلات
            interventions = self.intervention_dal.get_by_student_profile(profile_id)
            for inter in interventions:
                events.append({
                    'date': inter.date,
                    'type': 'intervention',
                    'type_display': 'مداخله',
                    'title': inter.type_display,
                    'description': inter.description or '',
                    'details': {
                        'type': inter.type_display,
                        'status': inter.status_display,
                        'goal': inter.goal,
                        'result': inter.result,
                    }
                })
            
            # پیگیری‌ها
            followups = self.followup_dal.get_by_student_profile(profile_id)
            for follow in followups:
                events.append({
                    'date': follow.date,
                    'type': 'followup',
                    'type_display': 'پیگیری',
                    'title': follow.method or 'پیگیری انجام شد',
                    'description': follow.description or '',
                    'details': {
                        'status': follow.status_display,
                        'result_type': follow.result_type_display,
                        'result_description': follow.result_description,
                    }
                })
            
            # مرتب‌سازی بر اساس تاریخ (جدیدترین اول)
            events.sort(key=lambda x: x['date'] or '', reverse=True)
            
            return events
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت Timeline: {e}")
            return []
    
    def get_trend_chart_data(self, profile_id, period='monthly'):
        """
        دریافت داده‌های نمودار روند
        
        Returns:
            dict: داده‌های مناسب برای رسم نمودار
        """
        trend = self.analyze_student_trend(profile_id, period)
        if not trend['success']:
            return None
        
        chart_data = {
            'labels': [],
            'positive': [],
            'negative': [],
            'neutral': [],
            'total': [],
        }
        
        for period_data in trend['trend_data']:
            chart_data['labels'].append(period_data['label'])
            chart_data['positive'].append(period_data['positive'])
            chart_data['negative'].append(period_data['negative'])
            chart_data['neutral'].append(period_data['neutral'])
            chart_data['total'].append(period_data['total'])
        
        return chart_data
    
    def get_student_progress_summary(self, profile_id):
        """
        دریافت خلاصه پیشرفت دانش‌آموز
        
        Returns:
            dict: خلاصه پیشرفت
        """
        try:
            observations = self.observation_dal.get_by_student_profile(profile_id)
            if not observations:
                return {
                    'has_data': False,
                    'message': 'هنوز مشاهده‌ای ثبت نشده است.'
                }
            
            # ===== اصلاح (بازرسی یازدهم) =====
            # پیش از این، نیمهٔ دوم با «تعداد خام» رفتارهای مثبت/منفی
            # مقایسه می‌شد؛ اگر ثبت در نیمهٔ دوم کمتر بود، همان کاهش ثبت
            # می‌توانست به‌اشتباه «نیاز به توجه» تعبیر شود. اکنون مقایسه
            # بر پایهٔ **سهم** رفتارها انجام می‌شود و تعداد مشاهدات فقط
            # «حجم ثبت و پایش» گزارش می‌شود.
            first_half = observations[:len(observations)//2]
            second_half = observations[len(observations)//2:]
            minimum_for_halves = 2

            def _half_stats(items):
                counts = count_behaviors(items)
                return counts, shares(counts)

            first_counts, first_share = _half_stats(first_half)
            second_counts, second_share = _half_stats(second_half)

            direction = growth_direction([
                {'label': 'نیمهٔ نخست', 'positive': first_counts['positive'],
                 'negative': first_counts['negative'], 'neutral': first_counts['neutral'],
                 'total': first_counts['total']},
                {'label': 'نیمهٔ دوم', 'positive': second_counts['positive'],
                 'negative': second_counts['negative'], 'neutral': second_counts['neutral'],
                 'total': second_counts['total']},
            ])

            if first_counts['total'] < minimum_for_halves or \
                    second_counts['total'] < minimum_for_halves:
                trend = "داده ناکافی"
                trend_icon = "❓"
                color = "#95a5a6"
            elif direction['status'] == 'improving':
                trend = "تغییر به سمت رفتارهای مثبت‌تر"
                trend_icon = "📈"
                color = "#27ae60"
            elif direction['status'] == 'declining':
                trend = "افزایش سهم رفتارهای منفی"
                trend_icon = "📉"
                color = "#e74c3c"
            elif direction['status'] == 'stable':
                trend = "ترکیب رفتارها تقریباً ثابت"
                trend_icon = "➡️"
                color = "#f39c12"
            else:
                trend = "تغییر ترکیبی / نیازمند مشاهدهٔ بیشتر"
                trend_icon = "➡️"
                color = "#f39c12"

            total_counts = count_behaviors(observations)
            return {
                'has_data': True,
                'total_observations': total_counts['total'],
                'positive_count': total_counts['positive'],
                'negative_count': total_counts['negative'],
                'neutral_count': total_counts['neutral'],
                'positive_share': shares(total_counts)['positive'],
                'negative_share': shares(total_counts)['negative'],
                'first_half_positive': first_counts['positive'],
                'first_half_negative': first_counts['negative'],
                'second_half_positive': second_counts['positive'],
                'second_half_negative': second_counts['negative'],
                'first_half_positive_share': first_share['positive'],
                'second_half_positive_share': second_share['positive'],
                'direction': direction,
                'trend': trend,
                'trend_icon': trend_icon,
                'color': color,
                'volume_note': observations_volume_note(total_counts),
            }
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت خلاصه پیشرفت: {e}")
            return {'has_data': False, 'message': f'خطا: {e!s}'}

    # ============================================================
    # متدهای تحلیل چندساله (جدید)
    # ============================================================

    def analyze_multi_year_trend(self, student_id):
        """
        تحلیل روند چندساله دانش‌آموز
        
        Args:
            student_id: شناسه دانش‌آموز
            
        Returns:
            dict: داده‌های روند چندساله
        """
        try:
            # دریافت تمام پرونده‌های دانش‌آموز
            profiles = self.profile_dal.get_all_profiles_for_student(student_id)
            
            if not profiles:
                return {
                    'success': False,
                    'error': 'هیچ پرونده‌ای برای این دانش‌آموز وجود ندارد.',
                    'has_data': False
                }
            
            year_data = []
            competency_trend = defaultdict(list)
            observation_counts = []
            
            for profile in profiles:
                # دریافت مشاهدات هر سال
                observations = self.observation_dal.get_by_student_profile(profile.id)
                
                # آمار سال
                year_counts = count_behaviors(observations)
                year_share = shares(year_counts)
                year_info = {
                    'year': getattr(profile, 'academic_year_title', 'نامشخص'),
                    'profile_id': profile.id,
                    'grade': profile.grade,
                    'grade_display': profile.grade_display,
                    'class_name': profile.class_name,
                    # حجم ثبت و پایش — نه شاخص رشد
                    'observations_count': year_counts['total'],
                    'volume_note': observations_volume_note(year_counts),
                    'positive': year_counts['positive'],
                    'negative': year_counts['negative'],
                    'neutral': year_counts['neutral'],
                    'positive_share': year_share['positive'],
                    'negative_share': year_share['negative'],
                    # شدت: تکمیلی
                    'avg_severity': round(sum(o.severity or 1 for o in observations) / len(observations), 1) if observations else 0,
                    'severity_is_auxiliary': True,
                    'has_data': year_counts['total'] > 0
                }
                year_data.append(year_info)
                observation_counts.append(len(observations))
                
                # تحلیل شایستگی‌ها در هر سال (عنوان‌ها یک‌جا خوانده می‌شوند — رفع N+1)
                year_titles = self.competency_dal.get_titles_by_ids(
                    o.competency_id for o in observations)
                for obs in observations:
                    if obs.competency_id:
                        comp_title = year_titles.get(obs.competency_id)
                        if comp_title:
                            competency_trend[comp_title].append({
                                'year': getattr(profile, 'academic_year_title', 'نامشخص'),
                                'severity': obs.severity or 1,
                                'behavior_type': obs.behavior_type
                            })
            
            # تحلیل روند کلی چندساله (بر پایهٔ ترکیب رفتارها)
            overall = self._analyze_multi_year_overall(observation_counts, year_data)
            
            # تحلیل شایستگی‌های برتر چندساله
            top_competencies = self._get_multi_year_top_competencies(competency_trend)
            
            return {
                'success': True,
                'has_data': True,
                'student_id': student_id,
                'total_years': len(profiles),
                'year_data': year_data,
                'overall_trend': overall,
                'top_competencies': top_competencies,
                'competency_trend': dict(competency_trend),
                'observation_counts': observation_counts
            }
            
        except Exception as e:
            self.logger.error(f"خطا در تحلیل روند چندساله: {e}")
            return {
                'success': False,
                'error': str(e),
                'has_data': False
            }

    def get_multi_year_chart_data(self, student_id):
        """
        دریافت داده‌های نمودار روند چندساله
        
        Args:
            student_id: شناسه دانش‌آموز
            
        Returns:
            dict: داده‌های مناسب برای رسم نمودار
        """
        trend = self.analyze_multi_year_trend(student_id)
        if not trend['success'] or not trend['has_data']:
            return None
        
        chart_data = {
            'years': [],
            'positive': [],
            'negative': [],
            'neutral': [],
            'total': [],
            'avg_severity': []
        }
        
        for year_info in trend['year_data']:
            chart_data['years'].append(year_info['year'])
            chart_data['positive'].append(year_info['positive'])
            chart_data['negative'].append(year_info['negative'])
            chart_data['neutral'].append(year_info['neutral'])
            chart_data['total'].append(year_info['observations_count'])
            chart_data['avg_severity'].append(year_info['avg_severity'])
        
        return chart_data

    def get_multi_year_competency_trend(self, student_id, competency_name=None):
        """
        دریافت روند یک شایستگی خاص در طول سال‌های مختلف
        
        Args:
            student_id: شناسه دانش‌آموز
            competency_name: نام شایستگی (اختیاری)
            
        Returns:
            dict: داده‌های روند شایستگی
        """
        trend = self.analyze_multi_year_trend(student_id)
        if not trend['success'] or not trend['has_data']:
            return None
        
        def _summarize(comp_data):
            """خلاصهٔ رفتارمحور یک زمینه در طول سال‌ها (نه شدت‌محور)"""
            positive = sum(1 for item in comp_data if item.get('behavior_type') == 'مثبت')
            negative = sum(1 for item in comp_data if item.get('behavior_type') == 'منفی')
            total = len(comp_data)
            kind = classify_pattern(positive, negative,
                                    max(total - positive - negative, 0), total)
            return {
                'years': [item['year'] for item in comp_data],
                # شدت فقط تکمیلی است
                'severities': [item['severity'] for item in comp_data],
                'positive': positive,
                'negative': negative,
                'count': total,
                'pattern': kind,
                'pattern_label': pattern_label(kind),
            }

        if competency_name:
            # دریافت روند یک شایستگی خاص
            comp_data = trend['competency_trend'].get(competency_name, [])
            summary = _summarize(comp_data)
            summary.update({'competency_name': competency_name,
                            'data': comp_data,
                            'has_data': len(comp_data) > 0})
            return summary
        else:
            # دریافت همه شایستگی‌ها (خروجی رفتارمحور)
            return {name: _summarize(data)
                    for name, data in trend['competency_trend'].items()}

    def _analyze_multi_year_overall(self, observation_counts, year_data):
        """
        تحلیل روند کلی چندساله — با لحاظ همهٔ سال‌های میانی (بازرسی پانزدهم)

        نسخهٔ قبلی فقط «اولین سال» را با «آخرین سال» مقایسه می‌کرد
        (``year_data[0]`` در برابر ``year_data[-1]``) و آستانه‌های جداگانهٔ
        خودش را داشت؛ یعنی اگر در سال‌های میانی بهبود یا افت معناداری رخ
        داده و برگشته بود، نادیده گرفته می‌شد. اکنون همان منطق مشترک
        ``growth_direction`` (utils/behavior_analysis) روی **همهٔ سال‌ها**
        اجرا می‌شود: تغییر یک‌جهت → همان جهت؛ برگشت جهت در سال‌های میانی →
        «تغییر ترکیبی / روند غیرقطعی». تعداد مشاهدات هر سال فقط «حجم ثبت
        و پایش» است و در تصمیم نقشی ندارد.

        شکل خروجی برای سازگاری حفظ شده است: status / message / icon /
        color / years_with_data / total_years / first_year / last_year /
        positive_change / volume_note؛ به‌علاوهٔ label، direction (جزئیات
        کامل گام‌ها)، path_text (مسیر خوانا) و turning_points.
        """
        year_data = list(year_data or [])
        direction = growth_direction([
            {'label': y.get('year'), 'positive': y.get('positive', 0),
             'negative': y.get('negative', 0), 'neutral': y.get('neutral', 0),
             'total': y.get('observations_count', 0)}
            for y in year_data
        ])
        years_with_data = sum(1 for y in year_data if y.get('has_data'))
        data_years = [y for y in year_data if y.get('has_data')]

        if direction['status'] == 'insufficient':
            return {
                'status': 'insufficient',
                'label': direction['label'],
                'message': ('داده کافی برای تحلیل روند چندساله وجود ندارد '
                            '(دست‌کم دو سال با مشاهدهٔ ثبت‌شده لازم است).'),
                'icon': '❓',
                'color': '#95a5a6',
                'years_with_data': years_with_data,
                'total_years': len(year_data),
                'first_year': year_data[0]['year'] if year_data else None,
                'last_year': year_data[-1]['year'] if year_data else None,
                'positive_change': 0.0,
                'volume_note': direction.get('volume_note', ''),
                'direction': direction,
                'path_text': '',
                'turning_points': [],
            }

        presets = {
            'improving': ('سهم رفتارهای مثبت در طول سال‌ها (با لحاظ سال‌های میانی) '
                          'بیشتر شده و افت معناداری در میانهٔ مسیر ثبت نشده است؛ '
                          'این تغییر بر پایهٔ نوع رفتارهای ثبت‌شده گزارش می‌شود، '
                          'نه بر پایهٔ تعداد مشاهدات.', '📈', '#27ae60'),
            'declining': ('سهم رفتارهای مثبت در طول سال‌ها کاهش یافته و بهبود '
                          'معناداری در سال‌های میانی ثبت نشده است؛ بررسی و حمایت '
                          'بیشتر پیشنهاد می‌شود. این تحلیل، تشخیص نیست.',
                          '📉', '#e74c3c'),
            'stable': ('ترکیب رفتارهای مثبت و منفی در طول سال‌ها تقریباً ثابت '
                       'است؛ به حمایت‌های فعلی ادامه دهید.', '➡️', '#f39c12'),
            'mixed': ('تغییر ترکیبی / روند غیرقطعی: تغییرات بین سال‌ها یک‌جهت '
                      'نیست (در بعضی سال‌ها بهبود و در بعضی دیگر افت ثبت شده '
                      'است)؛ نتیجه‌گیری قطعی نیازمند مشاهدهٔ بیشتر است.',
                      '🔀', '#f39c12'),
        }
        message, icon, color = presets.get(direction['status'], presets['mixed'])
        first_year, last_year = data_years[0], data_years[-1]
        positive_change = ((last_year.get('positive_share', 0) or 0)
                           - (first_year.get('positive_share', 0) or 0))
        volume_note = observations_volume_note({
            'positive': last_year.get('positive', 0),
            'negative': last_year.get('negative', 0),
            'neutral': last_year.get('neutral', 0),
            'total': last_year.get('observations_count', 0),
        })

        return {
            'status': direction['status'],
            'label': direction['label'],
            'message': f"{message} {direction['message']}",
            'icon': icon,
            'color': color,
            'years_with_data': years_with_data,
            'total_years': len(year_data),
            'first_year': year_data[0]['year'] if year_data else None,
            'last_year': year_data[-1]['year'] if year_data else None,
            # برآیند ابتدا/انتها فقط اطلاع تکمیلی است؛ مبنای نتیجه نیست
            'positive_change': round(positive_change, 1),
            'volume_note': volume_note,
            'direction': direction,
            'path_text': direction.get('path_text', ''),
            'turning_points': direction.get('turning_points', []),
        }

    def _get_multi_year_top_competencies(self, competency_trend):
        """
        دریافت شایستگی‌های برتر در چند سال
        """
        result = []
        for name, data in competency_trend.items():
            positive = sum(1 for item in data if item.get('behavior_type') == 'مثبت')
            negative = sum(1 for item in data if item.get('behavior_type') == 'منفی')
            total = len(data)
            avg_severity = sum(item['severity'] for item in data) / total if total else 0
            kind = classify_pattern(positive, negative, max(total - positive - negative, 0), total)
            result.append({
                'name': name,
                'count': total,
                'positive': positive,
                'negative': negative,
                'pattern': kind,
                'pattern_label': pattern_label(kind),
                # شدت فقط تکمیلی
                'avg_severity': round(avg_severity, 1),
                'severity_is_auxiliary': True,
                'years': sorted({item['year'] for item in data})
            })

        # پرتکرارترین زمینه‌ها اول (بر پایهٔ تعداد رفتارهای جهت‌دار)
        result.sort(key=lambda x: (x['positive'] + x['negative'], x['count']),
                    reverse=True)
        return result[:10]  # ۱۰ زمینهٔ پرتکرار

    def _group_observations_by_time(self, observations, period):
        """گروه‌بندی مشاهدات بر اساس زمان"""
        grouped = defaultdict(list)
        
        for obs in observations:
            date_str = obs.observation_date
            if not date_str:
                continue
            
            try:
                parts = date_str.split('/')
                if len(parts) == 3:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                    
                    if period == 'monthly':
                        key = f"{year:04d}/{month:02d}"
                        label = f"{month:02d}/{year}"
                    elif period == 'weekly':
                        week_num = (day - 1) // 7 + 1
                        key = f"{year:04d}/{month:02d}/W{week_num}"
                        label = f"هفته {week_num} {month}"
                    else:
                        key = f"{year:04d}/{month:02d}/{day:02d}"
                        label = f"{day:02d}/{month:02d}"
                    
                    grouped[key].append({
                        'obs': obs,
                        'label': label,
                        'date': date_str,
                        'year': year,
                        'month': month,
                        'day': day
                    })
            except Exception:
                continue
        
        sorted_keys = sorted(grouped.keys())
        return {key: grouped[key] for key in sorted_keys}
    
    def _calculate_period_stats(self, grouped_data):
        """محاسبه آمار هر بازه زمانی"""
        result = []
        
        for period_key, items in grouped_data.items():
            positive = sum(1 for i in items if i['obs'].behavior_type == "مثبت")
            negative = sum(1 for i in items if i['obs'].behavior_type == "منفی")
            neutral = sum(1 for i in items if i['obs'].behavior_type == "خنثی")
            total = len(items)
            
            avg_severity = sum(i['obs'].severity or 1 for i in items) / total if total > 0 else 0
            share = shares({'positive': positive, 'negative': negative,
                            'neutral': neutral, 'total': total})

            result.append({
                'period': period_key,
                'label': items[0]['label'] if items else period_key,
                'positive': positive,
                'negative': negative,
                'neutral': neutral,
                'total': total,
                # شدت فقط اطلاعات تکمیلی است (بازرسی یازدهم)
                'avg_severity': round(avg_severity, 1),
                'severity_is_auxiliary': True,
                'positive_share': share['positive'],
                'negative_share': share['negative'],
                'positive_percent': share['positive'],
                'items': items
            })
        
        return result
    
    def _analyze_overall_trend(self, trend_data):
        """
        تحلیل روند کلی — با لحاظ همهٔ بازه‌های میانی (بازرسی سیزدهم)

        نسخهٔ قبلی فقط «اولین بازه» را با «آخرین بازه» مقایسه می‌کرد
        (``trend_data[0]`` در برابر ``trend_data[-1]``)؛ یعنی اگر در
        بازه‌های میانی تغییر مهمی رخ داده و برگشته بود، نادیده گرفته
        می‌شد. اکنون همان منطق مشترک ``growth_direction`` استفاده می‌شود
        که مسیر بین همهٔ بازه‌ها را می‌سنجد و اگر تغییرات یک‌جهت نباشد،
        «تغییر ترکیبی / روند غیرقطعی» اعلام می‌کند. تعداد مشاهدات در این
        تصمیم نقشی ندارد (فقط حجم ثبت و پایش است).

        شکل خروجی برای سازگاری با صفحهٔ پرونده حفظ شده است:
        status / message / icon / color؛ به‌علاوهٔ direction (جزئیات
        کامل) و path_text (مسیر خوانا بین بازه‌ها).
        """
        direction = growth_direction([
            {'label': p.get('label'), 'positive': p.get('positive', 0),
             'negative': p.get('negative', 0), 'neutral': p.get('neutral', 0),
             'total': p.get('total', 0)}
            for p in (trend_data or [])
        ])

        if direction['status'] == 'insufficient':
            return {
                'status': 'insufficient_data',
                'message': 'داده کافی برای تحلیل روند وجود ندارد.',
                'icon': '❓',
                'color': '#95a5a6',
                'direction': direction,
                'path_text': '',
            }

        presets = {
            'improving': ('تغییر به سمت رفتارهای مثبت‌تر (در طول بازه‌ها).',
                          '📈', '#27ae60'),
            'declining': ('افزایش سهم رفتارهای منفی (در طول بازه‌ها)؛ '
                          'بررسی بیشتر پیشنهاد می‌شود.', '📉', '#e74c3c'),
            'stable': ('ترکیب رفتارها در طول بازه‌ها تقریباً ثابت است.',
                       '➡️', '#f39c12'),
            'mixed': ('تغییر ترکیبی / روند غیرقطعی: تغییرات بین بازه‌ها '
                      'یک‌جهت نیست.', '🔀', '#f39c12'),
        }
        message, icon, color = presets.get(direction['status'], presets['mixed'])
        return {
            'status': direction['status'],
            'message': message,
            'icon': icon,
            'color': color,
            'direction': direction,
            'path_text': direction.get('path_text', ''),
        }
    
    def _get_top_competencies(self, observations):
        """
        دریافت زمینه‌های پرتکرار — با تفکیک نوع رفتار

        بازرسی یازدهم: صرفِ «نام شایستگی» یا «میانگین شدت» مبنای
        نتیجه‌گیری نیست؛ شمارش رفتارهای مثبت و منفیِ ثبت‌شده و الگوی
        حاصل از آن‌ها مبناست. خروجی به شکل (نام، تعداد، الگو) است.
        """
        stats = defaultdict(lambda: {'positive': 0, 'negative': 0, 'total': 0})
        names = {}
        # عنوان شایستگی‌ها یک‌جا خوانده می‌شود (رفع N+1)
        titles = self.competency_dal.get_titles_by_ids(
            o.competency_id for o in observations)
        for obs in observations:
            if not obs.competency_id:
                continue
            title = titles.get(obs.competency_id)
            if not title:
                continue
            names[title] = names.get(title, title)
            stats[title]['total'] += 1
            if obs.behavior_type == "مثبت":
                stats[title]['positive'] += 1
            elif obs.behavior_type == "منفی":
                stats[title]['negative'] += 1

        result = []
        for title, data in stats.items():
            kind = classify_pattern(data['positive'], data['negative'],
                                    max(data['total'] - data['positive'] - data['negative'], 0),
                                    data['total'])
            result.append((title, data['total'], pattern_label(kind)))
        result.sort(key=lambda x: (x[1], x[2]), reverse=True)
        return result[:5]
    
    def _empty_trend(self, error=None):
        """بازگرداندن داده‌های خالی برای روند"""
        return {
            'success': False,
            'error': error or 'داده‌ای برای تحلیل وجود ندارد.',
            'trend_data': [],
            'overall_trend': {
                'status': 'no_data',
                'message': 'هیچ داده‌ای ثبت نشده است.',
                'icon': '📭'
            },
            'total_observations': 0,
            'top_competencies': [],
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0
        }