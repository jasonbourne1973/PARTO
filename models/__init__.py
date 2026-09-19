"""
مدل‌های داده پروژه PARTO
"""

from models.academic_year import AcademicYear
from models.attachment import Attachment
from models.base import BaseModel
from models.class_model import ClassModel
from models.competency import Competency
from models.enums import (
    AcademicYearStatus as AcademicYearStatus,
)
from models.enums import (
    ActionType as ActionType,
)
from models.enums import (
    CompetencyCategory as CompetencyCategory,
)
from models.enums import (
    EntityType as EntityType,
)
from models.enums import (
    FollowUpResultType as FollowUpResultType,
)
from models.enums import (
    FollowUpStatus as FollowUpStatus,
)
from models.enums import (
    Grade as Grade,
)
from models.enums import (
    InterventionStatus as InterventionStatus,
)
from models.enums import (
    LivingStatus as LivingStatus,
)

# ===== بازصدور صریح enum‌ها (به‌جای star-import) =====
# قبلاً اینجا `from models.enums import *` بود؛ هم برای lint مبهم
# بود و هم خواننده را گمراه می‌کرد. شکل «X as X» یعنی عمداً
# صادر می‌شود.
from models.enums import (
    ObservationStatus as ObservationStatus,
)
from models.enums import (
    StaffRole as StaffRole,
)
from models.enums import (
    StudentProfileStatus as StudentProfileStatus,
)
from models.enums import (
    UserRole as UserRole,
)
from models.family_context import FamilyContext
from models.followup import FollowUp
from models.indicator import Indicator
from models.intervention import Intervention
from models.observable_behavior import ObservableBehavior
from models.observation import Observation
from models.parent_interview import ParentInterview  # اضافه شده
from models.professional_interpretation import ProfessionalInterpretation
from models.screening import Screening
from models.screening_result import ScreeningResult
from models.screening_tool import ScreeningTool
from models.staff import Staff
from models.student import Student
from models.student_academic_profile import StudentAcademicProfile
from models.teacher_assignment import TeacherAssignment

__all__ = [
    'BaseModel',
    'Student',
    'Observation',
    'Intervention',
    'FollowUp',
    'StudentAcademicProfile',
    'Competency',
    'Staff',
    'AcademicYear',
    'Attachment',
    'ClassModel',
    'TeacherAssignment',
    'FamilyContext',
    'ParentInterview',  # اضافه شده
    'Screening',
    'ScreeningTool',
    'ScreeningResult',
    'ProfessionalInterpretation',
    'Indicator',
    'ObservableBehavior',
]