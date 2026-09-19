"""
سرویس تحلیل روند دانش‌آموز - بر اساس خود دانش‌آموز و بدون مقایسه با دیگران
با پشتیبانی از تحلیل چندساله
"""

import sys
import os
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_service import BaseService
from dal.observation_dal import ObservationDAL
from dal.intervention_dal import InterventionDAL
from dal.followup_dal import FollowUpDAL
from dal.competency_dal import CompetencyDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
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
import jdatetime


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
            
            return {
                'success': True,
                'profile_id': profile_id,
                'period': period,
                'trend_data': trend_data,
                'overall_trend': overall_trend,
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
            
            # محاسبه تغییرات
            first_half = observations[:len(observations)//2]
            second_half = observations[len(observations)//2:]
            
            first_positive = sum(1 for o in first_half if o.behavior_type == "مثبت")
            first_negative = sum(1 for o in first_half if o.behavior_type == "منفی")
            second_positive = sum(1 for o in second_half if o.behavior_type == "مثبت")
            second_negative = sum(1 for o in second_half if o.behavior_type == "منفی")
            
            # تعیین روند
            if second_half:
                if second_positive > first_positive and second_negative < first_negative:
                    trend = "بهبود"
                    trend_icon = "📈"
                    color = "#27ae60"
                elif second_positive < first_positive and second_negative > first_negative:
                    trend = "نیاز به توجه"
                    trend_icon = "📉"
                    color = "#e74c3c"
                else:
                    trend = "ثابت"
                    trend_icon = "➡️"
                    color = "#f39c12"
            else:
                trend = "داده ناکافی"
                trend_icon = "❓"
                color = "#95a5a6"
            
            return {
                'has_data': True,
                'total_observations': len(observations),
                'positive_count': sum(1 for o in observations if o.behavior_type == "مثبت"),
                'negative_count': sum(1 for o in observations if o.behavior_type == "منفی"),
                'neutral_count': sum(1 for o in observations if o.behavior_type == "خنثی"),
                'first_half_positive': first_positive,
                'first_half_negative': first_negative,
                'second_half_positive': second_positive,
                'second_half_negative': second_negative,
                'trend': trend,
                'trend_icon': trend_icon,
                'color': color,
            }
            
        except Exception as e:
            self.logger.error(f"خطا در دریافت خلاصه پیشرفت: {e}")
            return {'has_data': False, 'message': f'خطا: {str(e)}'}

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
                year_info = {
                    'year': getattr(profile, 'academic_year_title', 'نامشخص'),
                    'profile_id': profile.id,
                    'grade': profile.grade,
                    'grade_display': profile.grade_display,
                    'class_name': profile.class_name,
                    'observations_count': len(observations),
                    'positive': sum(1 for o in observations if o.behavior_type == "مثبت"),
                    'negative': sum(1 for o in observations if o.behavior_type == "منفی"),
                    'neutral': len(observations) - sum(1 for o in observations if o.behavior_type == "مثبت") - sum(1 for o in observations if o.behavior_type == "منفی"),
                    'avg_severity': round(sum(o.severity or 1 for o in observations) / len(observations), 1) if observations else 0,
                    'has_data': len(observations) > 0
                }
                year_data.append(year_info)
                observation_counts.append(len(observations))
                
                # تحلیل شایستگی‌ها در هر سال
                for obs in observations:
                    if obs.competency_id:
                        comp = self.competency_dal.get_by_id(obs.competency_id)
                        if comp:
                            competency_trend[comp.title].append({
                                'year': getattr(profile, 'academic_year_title', 'نامشخص'),
                                'severity': obs.severity or 1,
                                'behavior_type': obs.behavior_type
                            })
            
            # تحلیل روند کلی چندساله
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
        
        if competency_name:
            # دریافت روند یک شایستگی خاص
            comp_data = trend['competency_trend'].get(competency_name, [])
            return {
                'competency_name': competency_name,
                'data': comp_data,
                'years': [item['year'] for item in comp_data],
                'severities': [item['severity'] for item in comp_data],
                'has_data': len(comp_data) > 0
            }
        else:
            # دریافت همه شایستگی‌ها
            result = {}
            for name, data in trend['competency_trend'].items():
                result[name] = {
                    'years': [item['year'] for item in data],
                    'severities': [item['severity'] for item in data],
                    'count': len(data)
                }
            return result

    def _analyze_multi_year_overall(self, observation_counts, year_data):
        """
        تحلیل روند کلی چندساله
        """
        if len(observation_counts) < 2:
            return {
                'status': 'insufficient',
                'message': 'داده کافی برای تحلیل روند چندساله وجود ندارد.',
                'icon': '❓'
            }
        
        # بررسی تغییرات تعداد مشاهدات
        first_count = observation_counts[0]
        last_count = observation_counts[-1]
        
        # بررسی تغییرات درصد مثبت
        first_positive_ratio = year_data[0]['positive'] / year_data[0]['observations_count'] if year_data[0]['observations_count'] > 0 else 0
        last_positive_ratio = year_data[-1]['positive'] / year_data[-1]['observations_count'] if year_data[-1]['observations_count'] > 0 else 0
        
        positive_change = last_positive_ratio - first_positive_ratio
        
        if positive_change > 0.15:
            status = 'improving'
            message = 'روند کلی بهبود یافته است. عملکرد دانش‌آموز در حال رشد است.'
            icon = '📈'
            color = '#27ae60'
        elif positive_change > 0.05:
            status = 'slightly_improving'
            message = 'روند کلی کمی بهبود یافته است. ادامه حمایت توصیه می‌شود.'
            icon = '📈'
            color = '#2ecc71'
        elif positive_change > -0.05:
            status = 'stable'
            message = 'روند کلی تقریباً ثابت است. به حمایت‌های فعلی ادامه دهید.'
            icon = '➡️'
            color = '#f39c12'
        elif positive_change > -0.15:
            status = 'slightly_declining'
            message = 'روند کلی کمی کاهشی است. نیاز به توجه و بررسی دارد.'
            icon = '📉'
            color = '#e67e22'
        else:
            status = 'declining'
            message = 'روند کلی کاهشی است. نیاز به مداخله و حمایت ویژه دارد.'
            icon = '📉'
            color = '#e74c3c'
        
        # بررسی تعداد سال‌های با داده کافی
        years_with_data = sum(1 for y in year_data if y['has_data'])
        
        return {
            'status': status,
            'message': message,
            'icon': icon,
            'color': color,
            'years_with_data': years_with_data,
            'total_years': len(year_data),
            'first_year': year_data[0]['year'] if year_data else None,
            'last_year': year_data[-1]['year'] if year_data else None,
            'positive_change': round(positive_change * 100, 1)
        }

    def _get_multi_year_top_competencies(self, competency_trend):
        """
        دریافت شایستگی‌های برتر در چند سال
        """
        result = []
        for name, data in competency_trend.items():
            avg_severity = sum(item['severity'] for item in data) / len(data) if data else 0
            result.append({
                'name': name,
                'count': len(data),
                'avg_severity': round(avg_severity, 1),
                'years': sorted(set(item['year'] for item in data))
            })
        
        # مرتب‌سازی بر اساس تعداد و میانگین شدت
        result.sort(key=lambda x: (x['count'], x['avg_severity']), reverse=True)
        return result[:10]  # ۱۰ شایستگی برتر

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
            
            result.append({
                'period': period_key,
                'label': items[0]['label'] if items else period_key,
                'positive': positive,
                'negative': negative,
                'neutral': neutral,
                'total': total,
                'avg_severity': round(avg_severity, 1),
                'positive_percent': round((positive / total) * 100) if total > 0 else 0,
                'items': items
            })
        
        return result
    
    def _analyze_overall_trend(self, trend_data):
        """تحلیل روند کلی"""
        if len(trend_data) < 2:
            return {
                'status': 'insufficient_data',
                'message': 'داده کافی برای تحلیل روند وجود ندارد.',
                'icon': '❓'
            }
        
        first = trend_data[0]
        last = trend_data[-1]
        
        if last['positive_percent'] > first['positive_percent'] + 10:
            return {
                'status': 'improving',
                'message': 'روند بهبود مشاهده می‌شود.',
                'icon': '📈',
                'color': '#27ae60'
            }
        elif last['positive_percent'] < first['positive_percent'] - 10:
            return {
                'status': 'declining',
                'message': 'توجه بیشتر نیاز است.',
                'icon': '📉',
                'color': '#e74c3c'
            }
        else:
            return {
                'status': 'stable',
                'message': 'روند ثابت است.',
                'icon': '➡️',
                'color': '#f39c12'
            }
    
    def _get_top_competencies(self, observations):
        """دریافت شایستگی‌های برتر"""
        competency_counts = defaultdict(int)
        
        for obs in observations:
            if obs.competency_id:
                comp = self.competency_dal.get_by_id(obs.competency_id)
                if comp:
                    competency_counts[comp.title] += 1
        
        sorted_comps = sorted(competency_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_comps[:5]
    
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