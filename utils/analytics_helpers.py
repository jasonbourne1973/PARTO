"""
ابزارهای کمکی تحلیل داده برای داشبورد تحلیلی
"""

from typing import List, Dict, Any
from collections import defaultdict
import jdatetime


class AnalyticsHelpers:
    """ابزارهای کمکی برای تحلیل داده‌ها"""
    
    @staticmethod
    def group_by_period(items: List[Dict], date_field: str, period: str = 'monthly') -> Dict:
        """
        گروه‌بندی آیتم‌ها بر اساس بازه زمانی
        
        Args:
            items: لیست آیتم‌ها
            date_field: نام فیلد تاریخ
            period: بازه زمانی ('monthly', 'weekly', 'daily')
        
        Returns:
            dict: داده‌های گروه‌بندی شده
        """
        grouped = defaultdict(list)
        
        for item in items:
            date_str = item.get(date_field)
            if not date_str:
                continue
            
            if period == 'monthly':
                key = date_str[:7] if len(date_str) >= 7 else date_str
            elif period == 'weekly':
                parts = date_str.split('/')
                if len(parts) == 3:
                    try:
                        day = int(parts[2])
                        week = (day - 1) // 7 + 1
                        key = f"{parts[0]}/{parts[1]}/W{week}"
                    except:
                        key = date_str[:7] if len(date_str) >= 7 else date_str
                else:
                    key = date_str[:7] if len(date_str) >= 7 else date_str
            else:  # daily
                key = date_str
            
            grouped[key].append(item)
        
        return dict(sorted(grouped.items()))
    
    @staticmethod
    def calculate_trend(grouped_data: Dict, value_field: str) -> List[Dict]:
        """
        محاسبه روند از داده‌های گروه‌بندی شده
        
        Args:
            grouped_data: داده‌های گروه‌بندی شده
            value_field: نام فیلد مقدار
        
        Returns:
            list: داده‌های روند
        """
        result = []
        for period, items in grouped_data.items():
            total = sum(item.get(value_field, 0) for item in items)
            result.append({
                'period': period,
                'value': total,
                'count': len(items)
            })
        return result
    
    @staticmethod
    def get_persian_month_label(date_str: str) -> str:
        """دریافت برچسب فارسی ماه"""
        if not date_str or len(date_str) < 7:
            return date_str
        try:
            month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
            parts = date_str.split('/')
            if len(parts) >= 2:
                month = int(parts[1])
                if 1 <= month <= 12:
                    return f"{month_names[month-1]} {parts[0]}"
        except:
            pass
        return date_str
    
    @staticmethod
    def calculate_percentage(value: int, total: int) -> float:
        """محاسبه درصد"""
        return round((value / total * 100), 1) if total > 0 else 0
    
    @staticmethod
    def filter_by_date_range(items: List[Dict], date_field: str, 
                            start_date: str = None, end_date: str = None) -> List[Dict]:
        """فیلتر آیتم‌ها بر اساس بازه زمانی"""
        if not start_date and not end_date:
            return items
        
        filtered = []
        for item in items:
            date_str = item.get(date_field)
            if not date_str:
                continue
            
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            
            filtered.append(item)
        
        return filtered
    
    @staticmethod
    def get_date_range(days: int = 30) -> tuple:
        """دریافت بازه زمانی مشخص"""
        try:
            today = jdatetime.date.today()
            start = today - jdatetime.timedelta(days=days)
            end = today
            
            start_str = f"{start.year}/{start.month:02d}/{start.day:02d}"
            end_str = f"{end.year}/{end.month:02d}/{end.day:02d}"
            
            return start_str, end_str
        except:
            return None, None
    
    @staticmethod
    def calculate_avg_severity(items: List[Dict], severity_field: str = 'severity') -> float:
        """محاسبه میانگین شدت"""
        severities = [item.get(severity_field, 1) for item in items if item.get(severity_field)]
        return round(sum(severities) / len(severities), 1) if severities else 0
    
    @staticmethod
    def get_top_items(items: List[Dict], key_field: str, value_field: str, limit: int = 5) -> List[Dict]:
        """دریافت آیتم‌های برتر"""
        sorted_items = sorted(items, key=lambda x: x.get(value_field, 0), reverse=True)
        return sorted_items[:limit]