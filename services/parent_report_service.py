"""
سرویس تولید گزارش والدین - ساده، قابل فهم و غیرتشخیصی

===== منبع واحد گزارش والدین (بازرسی پانزدهم) =====
پیش از این دو مسیر مستقل برای گزارش والدین وجود داشت:

  • ``ReportGenerator.generate_parent_report`` (که صفحهٔ گزارش‌ها از آن
    استفاده می‌کرد) — برگرفته از گزارش کامل، ولی بدون پیگیری‌های در
    انتظار، بدون روند سادهٔ والدین‌فهم و بدون خروجی PDF؛
  • ``ParentReportService`` — با منطق جداگانهٔ استخراج قوت/ضعف، روند و
    پیشنهاد، که هیچ صفحه‌ای آن را صدا نمی‌زد.

اکنون **فقط یک منبع** وجود دارد: همین سرویس. تحلیل‌ها (الگوهای رفتاری،
روند ماهانه، اثربخشی مداخلات، پیشنهادها) یک بار در
``ReportGenerator.generate_student_report`` ساخته می‌شوند و این سرویس
فقط «نمای والدین» همان تحلیل را می‌سازد؛ بنابراین گزارش داخلی و گزارش
والدین هرگز از هم فاصله نمی‌گیرند. ``ReportGenerator.generate_parent_report``
اکنون به همین سرویس واگذار می‌کند و صفحهٔ گزارش‌ها و خروجی PDF هر دو از
همین دادهٔ واحد استفاده می‌کنند.

===== چه چیزهایی عمداً در گزارش والدین نمی‌آید =====
  • متن مشاهدات، شناسهٔ مشاهدات و نام ثبت‌کننده (ردیابی داخلی)
  • جزئیات زمینهٔ خانوادگی و متن مصاحبه‌های والدین (فقط «وجود/عدم
    وجود» گزارش می‌شود)
  • نتایج غربالگری، تفسیر حرفه‌ای، جلسات مشاوره، شرح و هدف مداخلات
  • هر گونه تشخیص یا برچسب
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jdatetime

from dal.family_context_dal import FamilyContextDAL
from dal.parent_interview_dal import ParentInterviewDAL
from services.base_service import BaseService
from services.report_generator import ReportGenerator
from utils.behavior_analysis import (
    count_behaviors,
    observations_volume_note,
    shares,
)
from utils.persian_pdf import PersianPDF
from utils.time_utils import utc_now

# کلیدهایی از هر الگوی رفتاری که برای والدین قابل ارائه است (بدون
# شناسهٔ مشاهدات و بدون نمونهٔ متن مشاهده)
PARENT_SAFE_ENTRY_KEYS = (
    'competency', 'pattern', 'pattern_label', 'positive', 'negative',
    'neutral', 'count', 'positive_share', 'negative_share',
)

# لایه‌هایی که عمداً در گزارش والدین نمی‌آیند (برای شفافیت در خروجی و تست)
PARENT_EXCLUDED_LAYERS = (
    'observation_texts_and_ids',
    'family_context_details',
    'parent_interview_texts',
    'screening_results',
    'professional_interpretations',
    'counseling_sessions',
    'intervention_descriptions',
)

_TRACE_PATTERN = re.compile(r"؛?\s*شناسهٔ مشاهدات:\s*[^)\.؛]*")


class ParentReportService(BaseService):
    """
    سرویس تولید گزارش والدین — منبع واحد

    ویژگی‌ها:
    - ساده و قابل فهم
    - غیرتشخیصی
    - بدون اطلاعات تخصصی و محرمانه
    - شامل نقاط قوت مشاهده‌شده
    - شامل زمینه‌های نیازمند حمایت
    - شامل روند رشد (بر پایهٔ ترکیب رفتارها، نه تعداد مشاهدات)
    - شامل اقدامات انجام‌شده و نتیجهٔ پیگیری (فقط شمارش)
    - شامل پیشنهادهای عمومی تربیتی/آموزشی
    """

    def __init__(self, report_generator=None):
        super().__init__()
        # منبع واحد تحلیل: همان تولیدکنندهٔ گزارش داخلی
        self.report_generator = report_generator or ReportGenerator()
        self.family_dal = FamilyContextDAL()
        self.interview_dal = ParentInterviewDAL()

    # ------------------------------------------------------------
    # داده‌های گزارش والدین
    # ------------------------------------------------------------
    def generate_parent_report_data(self, profile_id):
        """
        تولید داده‌های گزارش والدین از روی تحلیل واحد گزارش کامل

        Returns:
            dict | None: دادهٔ مناسب برای نمایش در برنامه و خروجی PDF.
            کلیدهای سازگار با نسخهٔ قبلی (student_name, grade, class,
            observations_count, interventions_count, strengths,
            weaknesses, intervention_effectiveness, trend_direction,
            balance_note, recommendations['parents'], trend, summary)
            حفظ شده‌اند.
        """
        try:
            full_report = self.report_generator.generate_student_report(profile_id)
            if not full_report:
                return None

            student = full_report['student']
            profile = full_report['profile']
            observations = full_report.get('observations') or []
            interventions = full_report.get('interventions') or []
            followups = full_report.get('followups') or []

            # الگوهای رفتاری: همان منطق تأییدشدهٔ گزارش داخلی
            # (utils/behavior_analysis) — فقط از فیلدهای داخلی پاک می‌شود
            strengths = [self._parent_safe_entry(e)
                         for e in full_report.get('strengths', [])[:5]]
            weaknesses = [self._parent_safe_entry(e)
                          for e in full_report.get('weaknesses', [])[:5]]
            strength_lines = self._strength_lines(strengths, observations)
            weakness_lines = self._weakness_lines(weaknesses, observations)

            # روند: از همان دادهٔ ماهانهٔ گزارش داخلی
            trend_data = full_report.get('trend_data')
            direction = self.report_generator.calculate_trend_direction(trend_data)
            trend = self._calculate_simple_trend(observations, trend_data, direction)

            # اثربخشی مداخلات: فقط شمارش نتیجه‌ها (بدون شرح مداخله)
            effectiveness = full_report.get('intervention_effectiveness') or {}
            effectiveness_summary = {
                'total': len(effectiveness.get('items') or []),
                'with_followup': sum(1 for i in (effectiveness.get('items') or [])
                                     if i.get('outcome_known')),
                'outcome_counts': dict(effectiveness.get('outcome_counts') or {}),
                'summary': effectiveness.get('summary', ''),
            }

            pending_count = sum(1 for f in followups
                                if getattr(f, 'status', None) == "pending")

            # پیشنهادها: همان پیشنهادهای والدینِ گزارش داخلی (بدون شناسهٔ
            # ردیابی) + یادداشت‌های زمینه‌ای مخصوص والدین
            recommendations = self._generate_parent_recommendations(
                (full_report.get('recommendations') or {}).get('parents', []),
                observations, interventions, followups,
            )

            family_context = self._first_or_none(
                self.family_dal.get_by_student_profile(profile_id))
            interviews = self.interview_dal.get_by_student_profile(profile_id) or []
            if not isinstance(interviews, (list, tuple)):
                interviews = [interviews]

            balance_note = ('در این گزارش، توانمندی‌ها و زمینه‌های نیازمند توجه در '
                            'کنار هم آمده‌اند؛ تمرکز گزارش فقط بر مشکل نیست.')
            privacy_note = ('این گزارش فقط بر پایهٔ رفتارهای ثبت‌شده در مدرسه تهیه '
                            'شده است؛ متن مشاهدات، نتایج غربالگری، تفسیر حرفه‌ای و '
                            'جزئیات گفت‌وگوهای خانوادگی در آن نیامده و هیچ بخشی از '
                            'آن تشخیص روان‌شناختی نیست.')

            summary = (
                f"در پروندهٔ {student.full_name} (پایهٔ {profile.grade_display}) "
                f"{full_report['observations_count']} مشاهدهٔ رفتاری و "
                f"{full_report['interventions_count']} مداخله ثبت شده است. "
                f"توانمندی‌های مشاهده‌شده: {len(strengths)} زمینه؛ "
                f"زمینه‌های نیازمند توجه: {len(weaknesses)} زمینه. "
                f"جهت تغییر رفتار: {direction['label']}. "
                "این گزارش، تشخیص روان‌شناختی نیست."
            )

            return {
                # اشیای پایه (برای PDF)
                'student': student,
                'profile': profile,
                'academic_year': full_report.get('academic_year'),
                # کلیدهای سازگار با نسخهٔ قبلی
                'student_name': student.full_name,
                'grade': profile.grade_display,
                'class': profile.class_name or 'نامشخص',
                'observations_count': full_report['observations_count'],
                'interventions_count': full_report['interventions_count'],
                'followups_count': full_report.get('followups_count', len(followups)),
                'pending_count': pending_count,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'strength_lines': strength_lines,
                'weakness_lines': weakness_lines,
                'intervention_effectiveness': effectiveness_summary,
                'trend_direction': direction,
                'trend': trend,
                'balance_note': balance_note,
                'privacy_note': privacy_note,
                'recommendations': {'parents': recommendations},
                'summary': summary,
                'has_data': len(observations) > 0 or len(interventions) > 0,
                # فقط «وجود» زمینهٔ خانوادگی/مصاحبه؛ محتوای آن‌ها داخلی است
                'has_family_context': family_context is not None,
                'has_interviews': len(interviews) > 0,
                'excluded_layers': list(PARENT_EXCLUDED_LAYERS),
            }

        except Exception as e:
            self.logger.error(f"خطا در تولید داده‌های گزارش والدین: {e}")
            return None

    # ------------------------------------------------------------
    # کمکی‌ها
    # ------------------------------------------------------------
    @staticmethod
    def _first_or_none(value):
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            return value[0] if value else None
        return value

    @staticmethod
    def _parent_safe_entry(entry):
        """نسخهٔ والدین‌پسند یک الگوی رفتاری: بدون شناسه و متن مشاهده."""
        return {key: entry.get(key) for key in PARENT_SAFE_ENTRY_KEYS if key in entry}

    @staticmethod
    def _strip_trace(text):
        """حذف «شناسهٔ مشاهدات: …» (ردیابی داخلی) از متن پیشنهاد."""
        cleaned = _TRACE_PATTERN.sub('', text or '')
        return re.sub(r"\(\s*\)", '', cleaned).replace('  ', ' ').strip()

    def _strength_lines(self, strengths, observations):
        """
        متن توانمندی‌ها برای والدین — رفتارمحور و غیرتشخیصی

        بازرسی یازدهم: «توانمندی» یعنی الگوی **تکرارشوندهٔ رفتار مثبت**
        مرتبط با یک شایستگی. یک مشاهدهٔ منفرد نتیجه‌گیری نمی‌سازد و
        شدت رفتار در این تصمیم نقشی ندارد. (منطق در گزارش داخلی ساخته
        می‌شود؛ اینجا فقط متن می‌شود.)
        """
        result = [
            f"{entry['competency']}: الگوی تکرارشوندهٔ رفتار مثبت "
            f"({entry['positive']} رفتار مثبت از {entry['count']} مشاهدهٔ ثبت‌شده)"
            for entry in strengths
        ]
        if not result:
            counts = count_behaviors(observations)
            if counts['positive']:
                result = [("مشاهدهٔ رفتار مثبت ثبت شده است، ولی هنوز برای "
                           "تشخیص «الگوی تکرارشونده» به ثبت بیشتری نیاز است.")]
            else:
                result = ["هنوز مشاهدهٔ مثبتی ثبت نشده است."]
        return result[:5]

    def _weakness_lines(self, weaknesses, observations):
        """
        متن زمینه‌های نیازمند توجه برای والدین — رفتارمحور و غیرتشخیصی

        «زمینهٔ نیازمند توجه» یعنی الگوی **تکرارشوندهٔ رفتار منفی**؛ نه
        یک مشاهدهٔ منفرد و نه بر پایهٔ شدت. این گزارش به‌معنای تشخیص یا
        برچسب نیست.
        """
        result = [
            f"{entry['competency']}: الگوی تکرارشوندهٔ رفتار منفی "
            f"({entry['negative']} رفتار منفی از {entry['count']} مشاهدهٔ ثبت‌شده) "
            "— نیازمند توجه و بررسی"
            for entry in weaknesses
        ]
        if not result:
            counts = count_behaviors(observations)
            if counts['negative']:
                result = [("مشاهدهٔ رفتار منفی ثبت شده است، ولی هنوز برای "
                           "تشخیص «الگوی تکرارشونده» به ثبت بیشتری نیاز است.")]
            else:
                result = ["هیچ زمینهٔ نیازمند توجهی ثبت نشده است."]
        return result[:5]

    def _calculate_simple_trend(self, observations, trend_data=None, direction=None):
        """
        روند سادهٔ والدین‌فهم — از همان دادهٔ ماهانهٔ گزارش داخلی

        بازرسی یازدهم: روند از «ترکیب رفتارهای ثبت‌شده» ساخته می‌شود و
        تعداد مشاهدات صرفاً «حجم ثبت و پایش» است. بازرسی پانزدهم:
        گروه‌بندی ماهانه دیگر اینجا تکرار نمی‌شود؛ ``trend_data`` همان
        خروجی ``ReportGenerator.calculate_trend`` است و جهت تغییر با همان
        ``growth_direction`` مشترک (با لحاظ همهٔ بازه‌های میانی) به دست
        می‌آید.
        """
        if trend_data is None:
            trend_data = self.report_generator.calculate_trend(observations)
        if not trend_data or len(trend_data) < 2:
            return {
                'has_data': False,
                'message': 'داده کافی برای تحلیل روند وجود ندارد.',
            }
        if direction is None:
            direction = self.report_generator.calculate_trend_direction(trend_data)

        months = [p['label'] for p in trend_data]
        monthly_counts = {p['label']: p.get('count', p.get('total', 0)) for p in trend_data}
        counts = count_behaviors(observations)
        share = shares(counts)

        # حجم ثبت در دو نیمه (فقط «حجم ثبت و پایش»؛ نه شاخص رشد)
        half = len(months) // 2
        first_volume = sum(monthly_counts[m] for m in months[:half])
        second_volume = sum(monthly_counts[m] for m in months[half:])

        labels = {
            'improving': ("روند تغییر رفتار به سمت رفتارهای مثبت‌تر بوده است.", "📈"),
            'declining': ("سهم رفتارهای نیازمند توجه افزایش یافته است؛ بررسی بیشتر پیشنهاد می‌شود.", "📉"),
            'stable': ("ترکیب رفتارهای ثبت‌شده تقریباً ثابت بوده است.", "➡️"),
            'mixed': ("ترکیب رفتارها در بازه‌های مختلف متفاوت بوده است؛ تحلیل قطعی نیازمند مشاهدهٔ بیشتر است.", "➡️"),
            'insufficient': ("دادهٔ کافی برای تحلیل روند وجود ندارد.", "❓"),
        }
        trend_text, trend_icon = labels.get(direction['status'], labels['insufficient'])

        return {
            'has_data': True,
            'trend_text': trend_text,
            'trend_icon': trend_icon,
            'direction': direction,
            'path_text': direction.get('path_text', ''),
            'months': months,
            'monthly_counts': monthly_counts,
            # حجم ثبت (نه شاخص رشد)
            'first_half_count': first_volume,
            'second_half_count': second_volume,
            'positive_count': counts['positive'],
            'negative_count': counts['negative'],
            'positive_share': share['positive'],
            'negative_share': share['negative'],
            'volume_note': observations_volume_note(counts),
            'total_observations': counts['total'],
        }

    def _generate_parent_recommendations(self, base_recommendations, observations,
                                         interventions, followups):
        """
        پیشنهادهای عمومی برای والدین — غیرتخصصی

        منبع اصلی همان پیشنهادهای والدینِ گزارش داخلی است (ساخته‌شده از
        الگوهای تکرارشوندهٔ رفتار مثبت)؛ فقط «شناسهٔ مشاهدات» که ردیابی
        داخلی است حذف می‌شود. سپس یادداشت‌های زمینه‌ای مخصوص والدین
        (حجم ثبت، غلبهٔ رفتار نیازمند توجه، پیگیری‌های در انتظار) اضافه
        می‌شود. هیچ‌کدام تشخیص نیست.
        """
        recommendations = []
        for text in base_recommendations or []:
            cleaned = self._strip_trace(text)
            if cleaned and cleaned not in recommendations:
                recommendations.append(cleaned)

        # یادداشت‌های زمینه‌ای (بر اساس حجم ثبت — نه رشد)
        if len(observations) < 3:
            recommendations.append(
                "حجم ثبت مشاهده در این بازه کم است؛ ثبت مشاهدات بیشتر به "
                "دقت تحلیل کمک می‌کند. این موضوع به‌خودی‌خود نشانهٔ بهبود یا "
                "وخامت نیست."
            )

        counts = count_behaviors(observations)
        if counts['negative'] > counts['positive'] and counts['negative'] >= 2:
            recommendations.append(
                "در رفتارهای ثبت‌شده، سهم رفتارهای نیازمند توجه بیشتر بوده "
                "است. پیشنهاد می‌شود در خانه نیز فرصت‌های رفتار مثبت تقویت "
                "شوند و گفت‌وگوی روزانه ادامه یابد؛ این متن تشخیص نیست."
            )

        pending = [f for f in followups if getattr(f, 'status', None) == "pending"]
        if pending:
            recommendations.append(
                "برخی از پیگیری‌های آموزشی نیازمند انجام است. "
                "لطفاً با مدرسه در این زمینه همکاری کنید."
            )

        if not recommendations:
            recommendations.append(
                "وضعیت عمومی دانش‌آموز مطلوب است. "
                "توصیه می‌شود ارتباط با مدرسه مستمر باشد و در صورت نیاز، "
                "جلسات مشاوره با معلم یا مشاور مدرسه برگزار شود."
            )

        return recommendations[:5]

    # ------------------------------------------------------------
    # خروجی PDF (از همان دادهٔ واحد)
    # ------------------------------------------------------------
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
            pdf.add_text(report_data['balance_note'])
            pdf.add_spacer(0.3)

            # ===== خلاصه (ساده) =====
            pdf.add_subtitle("خلاصه وضعیت")
            pdf.add_text(report_data['summary'])
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
            for strength in report_data['strength_lines']:
                pdf.add_strength(strength)
            pdf.add_spacer(0.3)

            # ===== زمینه‌های نیازمند حمایت =====
            pdf.add_subtitle("زمینه‌های نیازمند حمایت")
            for weakness in report_data['weakness_lines']:
                pdf.add_weakness(weakness)
            pdf.add_spacer(0.3)

            # ===== روند رشد =====
            pdf.add_subtitle("روند رشد (بر پایهٔ ترکیب رفتارها)")
            trend = report_data['trend']
            if trend['has_data']:
                pdf.add_text(f"{trend['trend_icon']} {trend['trend_text']}")
                pdf.add_text(
                    f"ترکیب رفتارهای ثبت‌شده: {trend['positive_count']} مثبت و "
                    f"{trend['negative_count']} منفی "
                    f"(سهم مثبت {trend['positive_share']}٪)"
                )
                if trend['first_half_count'] > 0:
                    pdf.add_text(
                        "حجم ثبت و پایش — نیمهٔ اول: "
                        f"{trend['first_half_count']} مشاهده | "
                        "نیمهٔ دوم: "
                        f"{trend['second_half_count']} مشاهده"
                    )
                pdf.add_text(trend['volume_note'])
            else:
                pdf.add_text(trend['message'])
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
            outcome_counts = report_data['intervention_effectiveness'].get('outcome_counts', {})
            if outcome_counts.get('improved'):
                pdf.add_text(
                    f"در {outcome_counts['improved']} مورد از پیگیری‌ها، بهبود مشاهده شده است."
                )
            pdf.add_spacer(0.3)

            # ===== پیشنهادات عمومی =====
            pdf.add_subtitle("پیشنهادات")
            for rec in report_data['recommendations']['parents']:
                pdf.add_text(f"* {rec}")
            pdf.add_spacer(0.3)

            # ===== یادداشت و اطلاعات تماس =====
            pdf.add_separator()
            pdf.add_text(report_data['privacy_note'])
            pdf.add_text("برای اطلاعات بیشتر، با مدرسه تماس بگیرید.")
            try:
                today = jdatetime.date.today()
                date_str = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
            except Exception as _exc:
                self.logger.debug(f"خطای مدیریت‌شده در export_parent_report_pdf (مسیر جایگزین): {_exc}")
                date_str = utc_now().strftime("%Y/%m/%d")

            pdf.add_text(f"تاریخ تهیه گزارش: {date_str}")
            pdf.add_text("PARTO - سامانه مدیریت پرونده دانش‌آموزان")

            # ساخت PDF
            pdf.build(file_path)

            return True, f"فایل PDF با موفقیت در {file_path} ذخیره شد."

        except Exception as e:
            self.logger.error(f"خطا در ساخت PDF گزارش والدین: {e}")
            return False, "خطا در ساخت PDF."
