"""
سرویس تولید گزارش‌های دانش‌آموزی
"""

import sys
import os

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dal.student_dal import StudentDAL
from dal.observation_dal import ObservationDAL
from database.connection import DatabaseConnection


class ReportGenerator:
    """تولید کننده گزارش‌های دانش‌آموزی"""
    
    def __init__(self):
        self.student_dal = StudentDAL()
        self.observation_dal = ObservationDAL()
        self.db = DatabaseConnection()
    
    def generate_student_report(self, student_id):
        """
        تولید گزارش کامل برای یک دانش‌آموز
        """
        # دریافت اطلاعات دانش‌آموز
        student = self.student_dal.get_by_id(student_id)
        if not student:
            return None
        
        # دریافت همه مشاهدات دانش‌آموز
        observations = self.observation_dal.get_by_student(student_id)
        
        # محاسبه شاخص‌ها
        indicators = self.calculate_indicators(student_id, observations)
        
        # تحلیل نقاط قوت و ضعف
        strengths, weaknesses = self.analyze_strengths_weaknesses(indicators)
        
        # تولید پیشنهادات
        recommendations = self.generate_recommendations(indicators)
        
        report = {
            'student': student,
            'observations_count': len(observations),
            'indicators': indicators,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendations': recommendations,
            'summary': self.generate_summary(indicators, observations)
        }
        
        return report
    
    def calculate_indicators(self, student_id, observations):
        """
        محاسبه امتیاز شاخص‌ها بر اساس مشاهدات
        """
        if not observations:
            return {}
        
        # دریافت همه شاخص‌ها
        cursor = self.db.execute_query("""
            SELECT i.id, i.name, d.name as domain_name
            FROM indicators i
            JOIN domains d ON i.domain_id = d.id
            ORDER BY d.id, i.id
        """)
        
        all_indicators = cursor.fetchall()
        
        results = {}
        for ind in all_indicators:
            indicator_name = ind['name']
            domain_name = ind['domain_name']
            
            # محاسبه امتیاز این شاخص (میانگین شدت مشاهدات)
            total_severity = 0
            count = 0
            for obs in observations:
                total_severity += obs.severity
                count += 1
            
            score = round(total_severity / count, 1) if count > 0 else 0
            
            if domain_name not in results:
                results[domain_name] = {}
            
            results[domain_name][indicator_name] = score
        
        return results
    
    def analyze_strengths_weaknesses(self, indicators):
        """
        تحلیل نقاط قوت و نیازهای رشدی
        """
        strengths = []
        weaknesses = []
        
        for domain, indicators_data in indicators.items():
            for indicator, score in indicators_data.items():
                if score >= 4:
                    strengths.append(f"{domain} - {indicator}")
                elif score < 2:
                    weaknesses.append(f"{domain} - {indicator}")
        
        return strengths, weaknesses
    
    def generate_recommendations(self, indicators):
        """
        تولید پیشنهادات بر اساس شاخص‌ها
        """
        recommendations = {
            'teacher': [],
            'parents': [],
            'counselor': []
        }
        
        for domain, indicators_data in indicators.items():
            for indicator, score in indicators_data.items():
                if score < 2:
                    if domain == "آموزشی":
                        recommendations['teacher'].append(
                            f"در شاخص '{indicator}' نیاز به تمرین و توجه بیشتر است."
                        )
                    elif domain in ["هیجانی", "اجتماعی", "رفتاری"]:
                        recommendations['counselor'].append(
                            f"در شاخص '{indicator}' نیاز به مشاوره و حمایت عاطفی است."
                        )
                    else:
                        recommendations['parents'].append(
                            f"در شاخص '{indicator}' نیاز به حمایت و تشویق در خانه است."
                        )
        
        # اگر پیشنهادی نبود
        if not recommendations['teacher']:
            recommendations['teacher'].append("وضعیت عمومی مطلوب است. به روند فعلی ادامه دهید.")
        if not recommendations['parents']:
            recommendations['parents'].append("وضعیت عمومی مطلوب است. به حمایت‌های فعلی ادامه دهید.")
        if not recommendations['counselor']:
            recommendations['counselor'].append("وضعیت عمومی مطلوب است. نیاز به مداخله خاصی نیست.")
        
        return recommendations
    
    def generate_summary(self, indicators, observations):
        """
        تولید خلاصه گزارش
        """
        if not observations:
            return "هنوز مشاهده‌ای برای این دانش‌آموز ثبت نشده است."
        
        total_severity = sum(obs.severity for obs in observations)
        avg_score = round(total_severity / len(observations), 1)
        
        positive = sum(1 for obs in observations if obs.behavior_type == "مثبت")
        negative = sum(1 for obs in observations if obs.behavior_type == "منفی")
        
        summary = f"""
خلاصه گزارش رشد دانش‌آموز:

تعداد کل مشاهدات: {len(observations)}
میانگین شدت مشاهدات: {avg_score}

نوع مشاهدات:
• مثبت: {positive} مورد
• منفی: {negative} مورد

وضعیت کلی: {'مطلوب' if avg_score >= 3 else 'نیازمند توجه'}
        """
        
        return summary