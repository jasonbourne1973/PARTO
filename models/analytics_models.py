"""
مدل‌های تحلیل داده برای داشبورد تحلیلی
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class ObservationDistribution:
    """توزیع مشاهدات بر اساس نوع"""
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    total: int = 0
    
    @property
    def positive_percentage(self) -> float:
        return round((self.positive / self.total * 100), 1) if self.total > 0 else 0
    
    @property
    def negative_percentage(self) -> float:
        return round((self.negative / self.total * 100), 1) if self.total > 0 else 0
    
    @property
    def neutral_percentage(self) -> float:
        return round((self.neutral / self.total * 100), 1) if self.total > 0 else 0


@dataclass
class GradeDistribution:
    """توزیع دانش‌آموزان بر اساس پایه"""
    grade: int
    grade_display: str
    count: int
    percentage: float = 0


@dataclass
class CompetencyUsage:
    """آمار استفاده از شایستگی"""
    competency_id: int
    competency_name: str
    count: int
    avg_severity: float = 0


@dataclass
class InterventionStats:
    """آمار مداخلات"""
    total: int = 0
    planned: int = 0
    in_progress: int = 0
    completed: int = 0
    cancelled: int = 0
    
    @property
    def success_rate(self) -> float:
        return round((self.completed / self.total * 100), 1) if self.total > 0 else 0
    
    @property
    def active_count(self) -> int:
        return self.planned + self.in_progress


@dataclass
class FollowupStats:
    """آمار پیگیری‌ها"""
    total: int = 0
    pending: int = 0
    done: int = 0
    continued: int = 0
    closed: int = 0
    cancelled: int = 0
    
    @property
    def completion_rate(self) -> float:
        completed = self.done + self.closed
        return round((completed / self.total * 100), 1) if self.total > 0 else 0


@dataclass
class TrendPoint:
    """نقطه داده روند"""
    period: str
    label: str
    value: int
    positive: int = 0
    negative: int = 0
    neutral: int = 0


@dataclass
class AnalyticsDashboardData:
    """داده‌های کامل داشبورد تحلیلی"""
    observation_distribution: ObservationDistribution
    grade_distribution: List[GradeDistribution]
    competency_usage: List[CompetencyUsage]
    intervention_stats: InterventionStats
    followup_stats: FollowupStats
    overdue_count: int
    students_without_observation: int
    observation_trend: List[TrendPoint]
    intervention_trend: List[TrendPoint]
    followup_trend: List[TrendPoint]
    generated_at: str = None
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()