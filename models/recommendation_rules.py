"""
مدل قوانین پیشنهاددهی هوشمند
تعریف قوانین و شرایط برای تولید پیشنهادات شخصی‌سازی‌شده
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class RulePriority(Enum):
    """اولویت قوانین پیشنهاددهی"""
    CRITICAL = 1      # بحرانی - نیاز به اقدام فوری
    HIGH = 2          # بالا - نیاز به توجه ویژه
    MEDIUM = 3        # متوسط - پیشنهاد بهبود
    LOW = 4           # پایین - پیشنهاد اختیاری


class RecommendationCategory(Enum):
    """دسته‌بندی پیشنهادات"""
    INTERVENTION = "intervention"      # پیشنهاد مداخله
    ENCOURAGEMENT = "encouragement"    # پیشنهاد تشویق
    FOLLOWUP = "followup"              # پیشنهاد پیگیری
    SUPPORT = "support"                # پیشنهاد حمایت
    REFERRAL = "referral"              # پیشنهاد ارجاع
    OBSERVATION = "observation"        # پیشنهاد مشاهده بیشتر


@dataclass
class RecommendationRule:
    """
    قانون پیشنهاددهی
    
    Attributes:
        id: شناسه قانون
        name: نام قانون
        description: توضیحات قانون
        priority: اولویت قانون
        category: دسته‌بندی پیشنهاد
        condition: تابع شرط (دریافت داده‌ها و بازگشت True/False)
        action: تابع اقدام (دریافت داده‌ها و بازگشت پیشنهاد)
        suggested_intervention_type: نوع مداخله پیشنهادی (اختیاری)
        tags: برچسب‌های مرتبط
    """
    id: str
    name: str
    description: str
    priority: RulePriority
    category: RecommendationCategory
    condition: Callable
    action: Callable
    suggested_intervention_type: Optional[str] = None
    tags: list[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class RecommendationResult:
    """
    نتیجه پیشنهاددهی
    
    Attributes:
        rule_id: شناسه قانون اعمال‌شده
        category: دسته‌بندی پیشنهاد
        priority: اولویت
        title: عنوان پیشنهاد
        description: توضیحات پیشنهاد
        suggested_action: اقدام پیشنهادی
        suggested_intervention_type: نوع مداخله پیشنهادی (اختیاری)
        related_competency_id: شناسه شایستگی مرتبط (اختیاری)
        related_observation_ids: شناسه مشاهدات مرتبط (اختیاری)
        score: امتیاز اهمیت (0-100)
        metadata: اطلاعات اضافی
    """
    rule_id: str
    category: RecommendationCategory
    priority: RulePriority
    title: str
    description: str
    suggested_action: str
    suggested_intervention_type: Optional[str] = None
    related_competency_id: Optional[int] = None
    related_observation_ids: Optional[list[int]] = None
    score: int = 50
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def priority_label(self) -> str:
        """برچسب اولویت به فارسی"""
        labels = {
            RulePriority.CRITICAL: "🔴 بحرانی",
            RulePriority.HIGH: "🟠 بالا",
            RulePriority.MEDIUM: "🟡 متوسط",
            RulePriority.LOW: "🟢 پایین"
        }
        return labels.get(self.priority, "متوسط")
    
    @property
    def priority_color(self) -> str:
        """رنگ اولویت"""
        colors = {
            RulePriority.CRITICAL: "#DC2626",
            RulePriority.HIGH: "#F97316",
            RulePriority.MEDIUM: "#F59E0B",
            RulePriority.LOW: "#22C55E"
        }
        return colors.get(self.priority, "#F59E0B")
    
    @property
    def category_label(self) -> str:
        """برچسب دسته‌بندی به فارسی"""
        labels = {
            RecommendationCategory.INTERVENTION: "🛠️ مداخله",
            RecommendationCategory.ENCOURAGEMENT: "⭐ تشویق",
            RecommendationCategory.FOLLOWUP: "🔔 پیگیری",
            RecommendationCategory.SUPPORT: "🫂 حمایت",
            RecommendationCategory.REFERRAL: "📋 ارجاع",
            RecommendationCategory.OBSERVATION: "📝 مشاهده"
        }
        return labels.get(self.category, "پیشنهاد")


# ============================================================
# قوانین پیش‌فرض سیستم
# ============================================================

def get_default_rules():
    """
    دریافت قوانین پیش‌فرض سیستم
    
    Returns:
        list: لیست قوانین پیش‌فرض
    """
    rules = []
    
    # ===== قانون 1: شایستگی ضعیف =====
    def weak_competency_condition(data):
        """شرط: وجود شایستگی با میانگین شدت <= 2 و حداقل 2 مشاهده"""
        weak_comps = data.get('weak_competencies', [])
        return len(weak_comps) > 0
    
    def weak_competency_action(data):
        """اقدام: پیشنهاد مداخله برای شایستگی ضعیف"""
        weak_comps = data.get('weak_competencies', [])
        if not weak_comps:
            return None
        
        comp = weak_comps[0]
        return RecommendationResult(
            rule_id="weak_competency",
            category=RecommendationCategory.INTERVENTION,
            priority=RulePriority.HIGH,
            title=f"نیاز به مداخله در شایستگی '{comp.get('competency_name', 'نامشخص')}'",
            description=f"این شایستگی با میانگین شدت {comp.get('avg_severity', 0)} و {comp.get('count', 0)} مشاهده، نیاز به توجه ویژه دارد.",
            suggested_action="ثبت مداخله هدفمند برای تقویت این شایستگی",
            suggested_intervention_type="individual_talk",
            related_competency_id=comp.get('competency_id'),
            related_observation_ids=comp.get('observation_ids', []),
            score=80
        )
    
    rules.append(RecommendationRule(
        id="weak_competency",
        name="شایستگی ضعیف",
        description="زمانی که یک شایستگی میانگین شدت پایین دارد، مداخله پیشنهاد می‌شود",
        priority=RulePriority.HIGH,
        category=RecommendationCategory.INTERVENTION,
        condition=weak_competency_condition,
        action=weak_competency_action,
        suggested_intervention_type="individual_talk",
        tags=["weak", "competency", "intervention"]
    ))
    
    # ===== قانون 2: شایستگی قوی =====
    def strong_competency_condition(data):
        """شرط: وجود شایستگی با میانگین شدت >= 3.5 و حداقل 2 مشاهده"""
        strong_comps = data.get('strong_competencies', [])
        return len(strong_comps) > 0
    
    def strong_competency_action(data):
        """اقدام: پیشنهاد تشویق برای شایستگی قوی"""
        strong_comps = data.get('strong_competencies', [])
        if not strong_comps:
            return None
        
        comp = strong_comps[0]
        return RecommendationResult(
            rule_id="strong_competency",
            category=RecommendationCategory.ENCOURAGEMENT,
            priority=RulePriority.MEDIUM,
            title=f"تشویق در شایستگی '{comp.get('competency_name', 'نامشخص')}'",
            description=f"این شایستگی با میانگین شدت {comp.get('avg_severity', 0)} و {comp.get('count', 0)} مشاهده، عملکرد خوبی دارد.",
            suggested_action="تشویق و تقویت این شایستگی",
            suggested_intervention_type="encouragement",
            related_competency_id=comp.get('competency_id'),
            score=60
        )
    
    rules.append(RecommendationRule(
        id="strong_competency",
        name="شایستگی قوی",
        description="زمانی که یک شایستگی میانگین شدت بالا دارد، تشویق پیشنهاد می‌شود",
        priority=RulePriority.MEDIUM,
        category=RecommendationCategory.ENCOURAGEMENT,
        condition=strong_competency_condition,
        action=strong_competency_action,
        suggested_intervention_type="encouragement",
        tags=["strong", "competency", "encouragement"]
    ))
    
    # ===== قانون 3: بدون مشاهده =====
    def no_observation_condition(data):
        """شرط: دانش‌آموز هیچ مشاهده‌ای ندارد"""
        total_obs = data.get('total_observations', 0)
        return total_obs == 0
    
    def no_observation_action(data):
        """اقدام: پیشنهاد ثبت مشاهده"""
        return RecommendationResult(
            rule_id="no_observation",
            category=RecommendationCategory.OBSERVATION,
            priority=RulePriority.HIGH,
            title="ثبت مشاهده برای دانش‌آموز",
            description="این دانش‌آموز هیچ مشاهده‌ای ندارد. ثبت مشاهدات برای تحلیل دقیق‌تر ضروری است.",
            suggested_action="ثبت حداقل یک مشاهده برای این دانش‌آموز",
            score=90
        )
    
    rules.append(RecommendationRule(
        id="no_observation",
        name="بدون مشاهده",
        description="زمانی که دانش‌آموز هیچ مشاهده‌ای ندارد، ثبت مشاهده پیشنهاد می‌شود",
        priority=RulePriority.HIGH,
        category=RecommendationCategory.OBSERVATION,
        condition=no_observation_condition,
        action=no_observation_action,
        tags=["no_observation", "observation"]
    ))
    
    # ===== قانون 4: مشاهده کم =====
    def low_observation_condition(data):
        """شرط: تعداد مشاهدات کمتر از 3"""
        total_obs = data.get('total_observations', 0)
        return 0 < total_obs < 3
    
    def low_observation_action(data):
        """اقدام: پیشنهاد ثبت مشاهده بیشتر"""
        return RecommendationResult(
            rule_id="low_observation",
            category=RecommendationCategory.OBSERVATION,
            priority=RulePriority.MEDIUM,
            title="ثبت مشاهدات بیشتر",
            description=f"این دانش‌آموز فقط {data.get('total_observations', 0)} مشاهده دارد. برای تحلیل دقیق‌تر، ثبت مشاهدات بیشتر توصیه می‌شود.",
            suggested_action="ثبت مشاهدات بیشتر برای تحلیل دقیق‌تر",
            score=70
        )
    
    rules.append(RecommendationRule(
        id="low_observation",
        name="مشاهده کم",
        description="زمانی که دانش‌آموز کمتر از 3 مشاهده دارد، ثبت مشاهده بیشتر پیشنهاد می‌شود",
        priority=RulePriority.MEDIUM,
        category=RecommendationCategory.OBSERVATION,
        condition=low_observation_condition,
        action=low_observation_action,
        tags=["low_observation", "observation"]
    ))
    
    # ===== قانون 5: پیگیری معوق =====
    def overdue_followup_condition(data):
        """شرط: وجود پیگیری معوق"""
        overdue_count = data.get('overdue_followups', 0)
        return overdue_count > 0
    
    def overdue_followup_action(data):
        """اقدام: پیشنهاد انجام پیگیری معوق"""
        return RecommendationResult(
            rule_id="overdue_followup",
            category=RecommendationCategory.FOLLOWUP,
            priority=RulePriority.CRITICAL,
            title="انجام پیگیری معوق",
            description=f"{data.get('overdue_followups', 0)} پیگیری معوق وجود دارد که نیاز به اقدام فوری دارد.",
            suggested_action="انجام پیگیری‌های معوق",
            score=100
        )
    
    rules.append(RecommendationRule(
        id="overdue_followup",
        name="پیگیری معوق",
        description="زمانی که پیگیری معوق وجود دارد، انجام آن پیشنهاد می‌شود",
        priority=RulePriority.CRITICAL,
        category=RecommendationCategory.FOLLOWUP,
        condition=overdue_followup_condition,
        action=overdue_followup_action,
        tags=["overdue", "followup"]
    ))
    
    # ===== قانون 6: مداخله ناموفق =====
    def unsuccessful_intervention_condition(data):
        """شرط: وجود مداخله لغو شده یا ناموفق"""
        cancelled = data.get('cancelled_interventions', 0)
        return cancelled > 0
    
    def unsuccessful_intervention_action(data):
        """اقدام: پیشنهاد مداخله جایگزین"""
        return RecommendationResult(
            rule_id="unsuccessful_intervention",
            category=RecommendationCategory.INTERVENTION,
            priority=RulePriority.HIGH,
            title="مداخله جایگزین پیشنهاد می‌شود",
            description=f"{data.get('cancelled_interventions', 0)} مداخله لغو یا ناموفق شده است. بررسی و انتخاب مداخله جایگزین توصیه می‌شود.",
            suggested_action="بررسی علت ناموفق بودن و انتخاب مداخله جدید",
            score=85
        )
    
    rules.append(RecommendationRule(
        id="unsuccessful_intervention",
        name="مداخله ناموفق",
        description="زمانی که مداخله ناموفق بوده، مداخله جایگزین پیشنهاد می‌شود",
        priority=RulePriority.HIGH,
        category=RecommendationCategory.INTERVENTION,
        condition=unsuccessful_intervention_condition,
        action=unsuccessful_intervention_action,
        tags=["unsuccessful", "intervention"]
    ))
    
    # ===== قانون 7: عدم پیگیری =====
    def no_followup_condition(data):
        """شرط: مداخله بدون پیگیری"""
        interventions_without_followup = data.get('interventions_without_followup', 0)
        return interventions_without_followup > 0
    
    def no_followup_action(data):
        """اقدام: پیشنهاد ثبت پیگیری"""
        return RecommendationResult(
            rule_id="no_followup",
            category=RecommendationCategory.FOLLOWUP,
            priority=RulePriority.MEDIUM,
            title="ثبت پیگیری برای مداخله",
            description=f"{data.get('interventions_without_followup', 0)} مداخله بدون پیگیری وجود دارد. ثبت پیگیری برای ارزیابی اثربخشی توصیه می‌شود.",
            suggested_action="ثبت پیگیری برای مداخلات بدون پیگیری",
            score=65
        )
    
    rules.append(RecommendationRule(
        id="no_followup",
        name="بدون پیگیری",
        description="زمانی که مداخله بدون پیگیری است، ثبت پیگیری پیشنهاد می‌شود",
        priority=RulePriority.MEDIUM,
        category=RecommendationCategory.FOLLOWUP,
        condition=no_followup_condition,
        action=no_followup_action,
        tags=["no_followup", "followup"]
    ))
    
    # ===== قانون 8: شایستگی بدون مشاهده =====
    def unobserved_competency_condition(data):
        """شرط: وجود شایستگی بدون مشاهده"""
        unobserved = data.get('unobserved_competencies', 0)
        return unobserved > 0
    
    def unobserved_competency_action(data):
        """اقدام: پیشنهاد مشاهده برای شایستگی بدون مشاهده"""
        return RecommendationResult(
            rule_id="unobserved_competency",
            category=RecommendationCategory.OBSERVATION,
            priority=RulePriority.LOW,
            title="ثبت مشاهده برای شایستگی‌های بدون مشاهده",
            description=f"{data.get('unobserved_competencies', 0)} شایستگی بدون مشاهده وجود دارد. ثبت مشاهدات مرتبط برای تحلیل جامع‌تر توصیه می‌شود.",
            suggested_action="ثبت مشاهدات برای شایستگی‌های بدون مشاهده",
            score=40
        )
    
    rules.append(RecommendationRule(
        id="unobserved_competency",
        name="شایستگی بدون مشاهده",
        description="زمانی که شایستگی بدون مشاهده است، ثبت مشاهده پیشنهاد می‌شود",
        priority=RulePriority.LOW,
        category=RecommendationCategory.OBSERVATION,
        condition=unobserved_competency_condition,
        action=unobserved_competency_action,
        tags=["unobserved", "competency", "observation"]
    ))
    
    # ===== قانون 9: رفتار منفی زیاد =====
    def high_negative_ratio_condition(data):
        """شرط: نسبت رفتار منفی بالا (> 50%)"""
        negative_ratio = data.get('negative_ratio', 0)
        return negative_ratio > 50
    
    def high_negative_ratio_action(data):
        """اقدام: پیشنهاد مداخله برای کاهش رفتار منفی"""
        return RecommendationResult(
            rule_id="high_negative_ratio",
            category=RecommendationCategory.INTERVENTION,
            priority=RulePriority.HIGH,
            title="کاهش رفتارهای منفی",
            description=f"{data.get('negative_ratio', 0)}% مشاهدات منفی هستند. نیاز به مداخله برای کاهش رفتارهای منفی وجود دارد.",
            suggested_action="ثبت مداخله برای کاهش رفتارهای منفی",
            suggested_intervention_type="individual_talk",
            score=85
        )
    
    rules.append(RecommendationRule(
        id="high_negative_ratio",
        name="رفتار منفی زیاد",
        description="زمانی که نسبت رفتار منفی بالا است، مداخله پیشنهاد می‌شود",
        priority=RulePriority.HIGH,
        category=RecommendationCategory.INTERVENTION,
        condition=high_negative_ratio_condition,
        action=high_negative_ratio_action,
        suggested_intervention_type="individual_talk",
        tags=["negative", "ratio", "intervention"]
    ))
    
    # ===== قانون 10: رفتار مثبت زیاد =====
    def high_positive_ratio_condition(data):
        """شرط: نسبت رفتار مثبت بالا (> 70%)"""
        positive_ratio = data.get('positive_ratio', 0)
        return positive_ratio > 70
    
    def high_positive_ratio_action(data):
        """اقدام: پیشنهاد تشویق"""
        return RecommendationResult(
            rule_id="high_positive_ratio",
            category=RecommendationCategory.ENCOURAGEMENT,
            priority=RulePriority.LOW,
            title="تشویق رفتارهای مثبت",
            description=f"{data.get('positive_ratio', 0)}% مشاهدات مثبت هستند. عملکرد بسیار خوب است، تشویق و تقویت ادامه یابد.",
            suggested_action="تشویق و تقویت رفتارهای مثبت",
            suggested_intervention_type="encouragement",
            score=50
        )
    
    rules.append(RecommendationRule(
        id="high_positive_ratio",
        name="رفتار مثبت زیاد",
        description="زمانی که نسبت رفتار مثبت بالا است، تشویق پیشنهاد می‌شود",
        priority=RulePriority.LOW,
        category=RecommendationCategory.ENCOURAGEMENT,
        condition=high_positive_ratio_condition,
        action=high_positive_ratio_action,
        suggested_intervention_type="encouragement",
        tags=["positive", "ratio", "encouragement"]
    ))
    
    return rules


# ============================================================
# کلاس مدیریت قوانین
# ============================================================

class RuleManager:
    """
    مدیر قوانین پیشنهاددهی
    
    ویژگی‌ها:
    - بارگذاری و مدیریت قوانین
    - ارزیابی قوانین بر اساس داده‌ها
    - اولویت‌بندی نتایج
    """
    
    def __init__(self):
        self.rules = get_default_rules()
        self._rule_map = {rule.id: rule for rule in self.rules}
    
    def get_all_rules(self) -> list[RecommendationRule]:
        """دریافت همه قوانین"""
        return self.rules.copy()
    
    def get_rule_by_id(self, rule_id: str) -> Optional[RecommendationRule]:
        """دریافت قانون با شناسه"""
        return self._rule_map.get(rule_id)
    
    def get_rules_by_category(self, category: RecommendationCategory) -> list[RecommendationRule]:
        """دریافت قوانین بر اساس دسته‌بندی"""
        return [r for r in self.rules if r.category == category]
    
    def get_rules_by_priority(self, priority: RulePriority) -> list[RecommendationRule]:
        """دریافت قوانین بر اساس اولویت"""
        return [r for r in self.rules if r.priority == priority]
    
    def evaluate_rules(self, data: dict) -> list[RecommendationResult]:
        """
        ارزیابی قوانین بر اساس داده‌ها
        
        Args:
            data: دیکشنری داده‌های دانش‌آموز
            
        Returns:
            list: لیست نتایج پیشنهادات (مرتب‌شده بر اساس اولویت و امتیاز)
        """
        results = []
        
        for rule in self.rules:
            try:
                if rule.condition(data):
                    result = rule.action(data)
                    if result:
                        results.append(result)
            except Exception as e:
                print(f"خطا در ارزیابی قانون {rule.id}: {e}")
        
        # مرتب‌سازی بر اساس اولویت و امتیاز
        results.sort(key=lambda x: (x.priority.value, -x.score))
        
        return results
    
    def get_top_recommendations(self, data: dict, limit: int = 5) -> list[RecommendationResult]:
        """
        دریافت بهترین پیشنهادات
        
        Args:
            data: دیکشنری داده‌های دانش‌آموز
            limit: تعداد محدود
            
        Returns:
            list: لیست بهترین پیشنهادات
        """
        results = self.evaluate_rules(data)
        return results[:limit]
    
    def add_rule(self, rule: RecommendationRule):
        """افزودن قانون جدید"""
        self.rules.append(rule)
        self._rule_map[rule.id] = rule
    
    def remove_rule(self, rule_id: str) -> bool:
        """حذف قانون"""
        if rule_id in self._rule_map:
            self.rules = [r for r in self.rules if r.id != rule_id]
            del self._rule_map[rule_id]
            return True
        return False
    
    def get_rules_summary(self) -> dict:
        """دریافت خلاصه قوانین"""
        summary = {
            'total': len(self.rules),
            'by_category': {},
            'by_priority': {}
        }
        
        for rule in self.rules:
            category = rule.category.value
            if category not in summary['by_category']:
                summary['by_category'][category] = 0
            summary['by_category'][category] += 1
            
            priority = rule.priority.value
            if priority not in summary['by_priority']:
                summary['by_priority'][priority] = 0
            summary['by_priority'][priority] += 1
        
        return summary