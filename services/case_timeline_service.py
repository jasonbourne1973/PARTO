"""
سرویس ساخت Timeline یکپارچه پرونده دانش‌آموز
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.competency_dal import CompetencyDAL
from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from dal.staff_dal import StaffDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from utils.logger import get_logger

logger = get_logger(__name__)


class CaseTimelineService:
    """
    سرویس ساخت Timeline یکپارچه پرونده دانش‌آموز
    
    تمام رویدادها (مشاهده، مداخله، پیگیری) را به ترتیب زمانی
    مرتب کرده و یک Timeline واحد تولید می‌کند.
    """
    
    # انواع رویدادها
    EVENT_OBSERVATION = "observation"
    EVENT_INTERVENTION = "intervention"
    EVENT_FOLLOWUP = "followup"
    
    EVENT_TYPE_DISPLAY = {
        EVENT_OBSERVATION: "📝 مشاهده",
        EVENT_INTERVENTION: "🛠️ مداخله",
        EVENT_FOLLOWUP: "🔔 پیگیری",
    }
    
    EVENT_ICON = {
        EVENT_OBSERVATION: "📝",
        EVENT_INTERVENTION: "🛠️",
        EVENT_FOLLOWUP: "🔔",
    }
    
    EVENT_COLOR = {
        EVENT_OBSERVATION: "#3498db",   # آبی
        EVENT_INTERVENTION: "#e67e22",  # نارنجی
        EVENT_FOLLOWUP: "#8e44ad",      # بنفش
    }
    
    def __init__(self):
        self.observation_dal = ObservationDAL()
        self.intervention_dal = InterventionDAL()
        self.followup_dal = FollowUpDAL()
        self.student_dal = StudentDAL()
        self.profile_dal = StudentAcademicProfileDAL()
        self.staff_dal = StaffDAL()
        self.competency_dal = CompetencyDAL()
    
    def get_timeline(self, profile_id):
        """
        دریافت Timeline کامل برای یک پرونده دانش‌آموز
        
        Args:
            profile_id: شناسه پرونده سالانه دانش‌آموز
            
        Returns:
            list: لیست رویدادهای مرتب‌شده به ترتیب زمانی
        """
        if not profile_id:
            return []
        
        events = []
        
        # ===== ۱. دریافت مشاهدات =====
        observations = self.observation_dal.get_by_student_profile(profile_id)
        for obs in observations:
            events.append({
                'id': obs.id,
                'type': self.EVENT_OBSERVATION,
                'type_display': self.EVENT_TYPE_DISPLAY[self.EVENT_OBSERVATION],
                'icon': self.EVENT_ICON[self.EVENT_OBSERVATION],
                'color': self.EVENT_COLOR[self.EVENT_OBSERVATION],
                'date': obs.observation_date,
                'title': f"مشاهده در {obs.location or 'محیط نامشخص'}",
                'description': obs.description,
                'details': self._get_observation_details(obs),
                'raw_data': obs,
                'can_view': True,
                'can_edit': True,
                'can_delete': True,
            })
        
        # ===== ۲. دریافت مداخلات =====
        interventions = self.intervention_dal.get_by_student_profile(profile_id)
        for inter in interventions:
            
            events.append({
                'id': inter.id,
                'type': self.EVENT_INTERVENTION,
                'type_display': self.EVENT_TYPE_DISPLAY[self.EVENT_INTERVENTION],
                'icon': self.EVENT_ICON[self.EVENT_INTERVENTION],
                'color': self.EVENT_COLOR[self.EVENT_INTERVENTION],
                'date': inter.date,
                'title': f"مداخله: {inter.type_display}",
                'description': inter.description,
                'details': self._get_intervention_details(inter),
                'raw_data': inter,
                'can_view': True,
                'can_edit': True,
                'can_delete': True,
            })
        
        # ===== ۳. دریافت پیگیری‌ها =====
        followups = self.followup_dal.get_by_student_profile(profile_id)
        for follow in followups:
            
            events.append({
                'id': follow.id,
                'type': self.EVENT_FOLLOWUP,
                'type_display': self.EVENT_TYPE_DISPLAY[self.EVENT_FOLLOWUP],
                'icon': self.EVENT_ICON[self.EVENT_FOLLOWUP],
                'color': self.EVENT_COLOR[self.EVENT_FOLLOWUP],
                'date': follow.date,
                'title': f"پیگیری: {follow.status_display}",
                'description': follow.description or follow.result_description or "پیگیری انجام شد",
                'details': self._get_followup_details(follow),
                'raw_data': follow,
                'can_view': True,
                'can_edit': True,
                'can_delete': True,
            })
        
        # ===== ۴. مرتب‌سازی بر اساس تاریخ (از قدیم به جدید) =====
        events.sort(key=lambda x: x['date'] or "")
        
        # ===== ۵. افزودن شماره ردیف =====
        for i, event in enumerate(events, 1):
            event['index'] = i
        
        return events
    
    def get_timeline_grouped(self, profile_id):
        """
        دریافت Timeline گروه‌بندی شده بر اساس نوع رویداد
        
        Returns:
            dict: { 'observation': [...], 'intervention': [...], 'followup': [...] }
        """
        events = self.get_timeline(profile_id)
        
        grouped = {
            'observation': [],
            'intervention': [],
            'followup': [],
        }
        
        for event in events:
            event_type = event['type']
            if event_type in grouped:
                grouped[event_type].append(event)
        
        return grouped
    
    def get_timeline_summary(self, profile_id):
        """
        دریافت خلاصه آماری Timeline
        
        Returns:
            dict: { 'total': int, 'observations': int, 'interventions': int, 
                    'followups': int, 'pending_followups': int }
        """
        events = self.get_timeline(profile_id)
        
        summary = {
            'total': len(events),
            'observations': 0,
            'interventions': 0,
            'followups': 0,
            'pending_followups': 0,
        }
        
        for event in events:
            event_type = event['type']
            if event_type == self.EVENT_OBSERVATION:
                summary['observations'] += 1
            elif event_type == self.EVENT_INTERVENTION:
                summary['interventions'] += 1
            elif event_type == self.EVENT_FOLLOWUP:
                summary['followups'] += 1
                raw = event.get('raw_data')
                if raw and raw.status == 'pending':
                    summary['pending_followups'] += 1
        
        return summary
    
    def get_latest_event(self, profile_id):
        """
        دریافت آخرین رویداد پرونده
        
        Returns:
            dict: آخرین رویداد یا None
        """
        events = self.get_timeline(profile_id)
        if events:
            return events[-1]
        return None
    
    def get_chain_for_observation(self, observation_id):
        """
        دریافت زنجیره کامل برای یک مشاهده:
        Observation → Intervention → FollowUp → Outcome
        
        Returns:
            dict: { 'observation': ..., 'interventions': [...], 'followups': [...] }
        """
        result = {
            'observation': None,
            'interventions': [],
            'followups': [],
        }
        
        # دریافت مشاهده
        observation = self.observation_dal.get_by_id(observation_id)
        if not observation:
            return result
        
        result['observation'] = observation
        
        # دریافت مداخلات مرتبط با این مشاهده
        interventions = self.intervention_dal.get_by_observation(observation_id)
        result['interventions'] = interventions
        
        # دریافت پیگیری‌های هر مداخله
        for inter in interventions:
            followups = self.followup_dal.get_by_intervention(inter.id)
            result['followups'].extend(followups)
        
        # مرتب‌سازی پیگیری‌ها بر اساس تاریخ
        result['followups'].sort(key=lambda x: x.date or "")
        
        return result
    
    def _get_observation_details(self, obs):
        """دریافت جزئیات کامل یک مشاهده"""
        staff_name = self._get_staff_name(obs.staff_id)
        competency_name = self._get_competency_name(obs.competency_id)
        
        details = {
            'staff': staff_name,
            'competency': competency_name,
            'location': obs.location,
            'behavior_type': obs.behavior_type,
            'severity': obs.severity,
            'severity_display': obs.severity_display,
            'antecedent': obs.antecedent,
            'behavior': obs.behavior,
            'consequence': obs.consequence,
            'abc_summary': obs.abc_summary,
            'tags': obs.tags,
        }
        return details
    
    def _get_intervention_details(self, inter):
        """دریافت جزئیات کامل یک مداخله"""
        staff_name = self._get_staff_name(inter.staff_id)
        
        details = {
            'staff': staff_name,
            'type': inter.type_display,
            'status': inter.status_display,
            'goal': inter.goal,
            'result': inter.result,
            'observation_id': inter.observation_id,
        }
        return details
    
    def _get_followup_details(self, follow):
        """دریافت جزئیات کامل یک پیگیری"""
        staff_name = self._get_staff_name(follow.staff_id)
        
        details = {
            'staff': staff_name,
            'status': follow.status_display,
            'method': follow.method,
            'next_action_date': follow.next_action_date,
            'result_type': follow.result_type_display,
            'result_description': follow.result_description,
        }
        return details
    
    def _get_staff_name(self, staff_id):
        """دریافت نام مسئول از شناسه"""
        if not staff_id:
            return "نامشخص"
        try:
            staff = self.staff_dal.get_by_id(staff_id)
            return staff.full_name if staff else "نامشخص"
        except Exception:
            return "نامشخص"
    
    def _get_competency_name(self, competency_id):
        """دریافت نام شایستگی از شناسه"""
        if not competency_id:
            return "نامشخص"
        try:
            comp = self.competency_dal.get_by_id(competency_id)
            return comp.title if comp else "نامشخص"
        except Exception:
            return "نامشخص"
    
    def _get_student_name_by_profile(self, profile_id):
        """دریافت نام دانش‌آموز از شناسه پرونده"""
        try:
            profile = self.profile_dal.get_by_id(profile_id)
            if profile:
                student = self.student_dal.get_by_id(profile.student_id)
                return student.full_name if student else "نامشخص"
        except Exception as e:
            # نبود پرونده/دانش‌آموز نباید ساخت تایم‌لاین را متوقف کند
            logger.debug(f"نام دانش‌آموز برای پرونده {profile_id} خوانده نشد: {e}")
        return "نامشخص"