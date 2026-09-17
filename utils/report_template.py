"""
قالب استاندارد گزارش‌ها - بدون Emoji
"""

import os
from datetime import datetime
import jdatetime


class ReportTemplate:
    """
    قالب استاندارد برای تمام گزارش‌های پروژه
    
    ویژگی‌ها:
    - هدر یکسان با لوگو و عنوان
    - فوتر یکسان با تاریخ و شماره صفحه
    - بازه زمانی مشخص
    - منبع داده مشخص
    - تعداد رکوردها
    - بدون استفاده از Emoji
    """
    
    @staticmethod
    def _remove_emoji(text):
        """حذف Emoji از متن"""
        if not text:
            return text
        
        emoji_patterns = [
            '⭐', '🌟', '✨', '💡', '📊', '📚', '🏫', '👤', '👨', '👩', '👦', '👧',
            '🔴', '🟢', '🟡', '🔵', '🟣', '🟠', '⚪', '⚫',
            '✅', '❌', '⚠️', 'ℹ️', '📌', '🔹', '🔸', '🫂', '👨‍👩‍👦',
            '📋', '📝', '📈', '📉', '📅', '📆', '📁', '📂', '📎', '🖊️', '🖋️',
        ]
        
        for emoji in emoji_patterns:
            text = text.replace(emoji, '')
        
        import re
        emoji_unicode_pattern = re.compile(
            "[\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F700-\U0001F77F"
            "\U0001F780-\U0001F7FF"
            "\U0001F800-\U0001F8FF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]",
            flags=re.UNICODE
        )
        text = emoji_unicode_pattern.sub('', text)
        text = ' '.join(text.split())
        return text.strip()
    
    @staticmethod
    def get_header(title, subtitle=None, include_date=True, include_logo=True):
        """
        دریافت هدر استاندارد گزارش - بدون Emoji
        """
        lines = []
        
        # خط جداکننده بالا
        lines.append("━" * 60)
        lines.append("")
        
        # لوگو (اگر درخواست شده باشد)
        if include_logo:
            lines.append("  ██████╗  █████╗ ██████╗ ████████╗ ██████╗ ██╗    ")
            lines.append("  ██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔═══██╗██║    ")
            lines.append("  ██████╔╝███████║██████╔╝   ██║   ██║   ██║██║    ")
            lines.append("  ██╔═══╝ ██╔══██║██╔══██╗   ██║   ██║   ██║██║    ")
            lines.append("  ██║     ██║  ██║██║  ██║   ██║   ╚██████╔╝███████╗")
            lines.append("  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚══════╝")
            lines.append("")
            lines.append("  سامانه پرونده ارزيابي و رشد توانمندي دانش آموز")
            lines.append("")
        
        # عنوان - حذف Emoji
        title = ReportTemplate._remove_emoji(title)
        lines.append(f"  {title}")
        lines.append("")
        
        # زیرعنوان - حذف Emoji
        if subtitle:
            subtitle = ReportTemplate._remove_emoji(subtitle)
            lines.append(f"  {subtitle}")
            lines.append("")
        
        # تاریخ
        if include_date:
            try:
                today = jdatetime.date.today()
                date_str = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
            except:
                date_str = datetime.now().strftime("%Y/%m/%d")
            
            lines.append(f"  تاريخ گزارش: {date_str}")
        
        # خط جداکننده پایین
        lines.append("")
        lines.append("━" * 60)
        lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def get_footer(page_number=None, total_pages=None, include_signature=False):
        """
        دریافت فوتر استاندارد گزارش - بدون Emoji
        """
        lines = []
        
        lines.append("━" * 60)
        
        # اطلاعات صفحه
        if page_number is not None:
            if total_pages is not None:
                lines.append(f"صفحه {page_number} از {total_pages}")
            else:
                lines.append(f"صفحه {page_number}")
        
        # خط جداکننده
        lines.append("")
        
        # اطلاعات سیستم - بدون Emoji
        lines.append("  PARTO - سامانه مديريت پرونده دانش آموزان")
        lines.append("  پشتيباني: support@partow.ir")
        lines.append("  www.partow.ir")
        lines.append("")
        
        # امضا
        if include_signature:
            lines.append("  ──────────────────────────────────────────────")
            lines.append("  امضاي مسئول: ___________________")
            lines.append("  ──────────────────────────────────────────────")
        
        lines.append("")
        lines.append("━" * 60)
        
        return "\n".join(lines)
    
    @staticmethod
    def get_section(title, content, level=1):
        """
        دریافت یک بخش استاندارد - بدون Emoji
        """
        lines = []
        
        # حذف Emoji از عنوان
        title = ReportTemplate._remove_emoji(title)
        
        # عنوان بر اساس سطح
        if level == 1:
            lines.append("")
            lines.append("█" * 50)
            lines.append(f"  {title}")
            lines.append("█" * 50)
            lines.append("")
        elif level == 2:
            lines.append("")
            lines.append(f"  {title}")
            lines.append("─" * 40)
            lines.append("")
        else:
            lines.append("")
            lines.append(f"  - {title}")
            lines.append("")
        
        # محتوا - حذف Emoji
        if isinstance(content, list):
            for item in content:
                if item:
                    item = ReportTemplate._remove_emoji(str(item))
                    lines.append(f"    * {item}")
        elif isinstance(content, str) and content:
            content = ReportTemplate._remove_emoji(content)
            for line in content.split('\n'):
                if line.strip():
                    lines.append(f"    {line}")
        elif content:
            content = ReportTemplate._remove_emoji(str(content))
            lines.append(f"    {content}")
        
        lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def get_table(headers, rows, title=None, column_widths=None):
        """
        دریافت جدول استاندارد - بدون Emoji
        """
        lines = []
        
        # عنوان - حذف Emoji
        if title:
            title = ReportTemplate._remove_emoji(title)
            lines.append("")
            lines.append(f"  {title}")
            lines.append("")
        
        # حذف Emoji از هدرها
        headers = [ReportTemplate._remove_emoji(str(h)) for h in headers]
        
        # حذف Emoji از ردیف‌ها
        cleaned_rows = []
        for row in rows:
            cleaned_row = [ReportTemplate._remove_emoji(str(cell)) if cell is not None else "" for cell in row]
            cleaned_rows.append(cleaned_row)
        
        # محاسبه عرض ستون‌ها
        if not column_widths:
            col_count = len(headers)
            if cleaned_rows:
                for row in cleaned_rows:
                    if len(row) > col_count:
                        col_count = len(row)
            
            max_width = 80
            col_widths = []
            for i in range(col_count):
                max_len = len(headers[i]) if i < len(headers) else 0
                for row in cleaned_rows:
                    if i < len(row):
                        max_len = max(max_len, len(str(row[i])))
                col_widths.append(min(max_len + 2, 20))
        
        # ساخت خط جداکننده
        separator = "+"
        for w in col_widths:
            separator += "-" * w + "+"
        
        # سرستون‌ها
        lines.append(separator)
        header_line = "|"
        for i, header in enumerate(headers):
            w = col_widths[i] if i < len(col_widths) else 10
            header_line += f"{header:^{w}}|"
        lines.append(header_line)
        lines.append(separator)
        
        # ردیف‌ها
        for row in cleaned_rows:
            row_line = "|"
            for i, cell in enumerate(row):
                w = col_widths[i] if i < len(col_widths) else 10
                cell_str = str(cell) if cell is not None else ""
                row_line += f"{cell_str:<{w}}|"
            lines.append(row_line)
        
        lines.append(separator)
        lines.append("")
        
        # تعداد رکوردها
        lines.append(f"  تعداد ركوردها: {len(cleaned_rows)}")
        lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def get_info_box(title, items):
        """
        دریافت جعبه اطلاعات استاندارد - بدون Emoji
        """
        lines = []
        
        title = ReportTemplate._remove_emoji(title)
        
        lines.append("")
        lines.append("┌" + "─" * 58 + "┐")
        lines.append(f"│ {title:^56} │")
        lines.append("├" + "─" * 58 + "┤")
        
        if isinstance(items, dict):
            items_list = items.items()
        else:
            items_list = items
        
        for key, value in items_list:
            key_str = ReportTemplate._remove_emoji(str(key)) if key else ""
            value_str = ReportTemplate._remove_emoji(str(value)) if value is not None else ""
            line = f"│ {key_str:<20} : {value_str:<33} │"
            lines.append(line)
        
        lines.append("└" + "─" * 58 + "┘")
        lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def get_metadata(source, record_count, date_range=None, generated_by=None):
        """
        دریافت متادیتای گزارش - بدون Emoji
        """
        lines = []
        
        lines.append("")
        lines.append("━" * 60)
        lines.append("")
        lines.append("متاديتاي گزارش")
        lines.append("")
        
        items = [
            ("منبع داده", ReportTemplate._remove_emoji(source)),
            ("تعداد رکوردها", record_count),
        ]
        
        if date_range:
            items.append(("بازه زماني", ReportTemplate._remove_emoji(date_range)))
        
        if generated_by:
            items.append(("توليد شده توسط", ReportTemplate._remove_emoji(generated_by)))
        
        # زمان تولید
        try:
            now = jdatetime.datetime.now()
            time_str = f"{now.year:04d}/{now.month:02d}/{now.day:02d} {now.hour:02d}:{now.minute:02d}"
        except:
            time_str = datetime.now().strftime("%Y/%m/%d %H:%M")
        
        items.append(("زمان توليد", time_str))
        
        for key, value in items:
            lines.append(f"  * {key}: {value}")
        
        lines.append("")
        lines.append("━" * 60)
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_full_report(title, sections, metadata, footer_page=None):
        """
        تولید گزارش کامل با تمام بخش‌ها - بدون Emoji
        """
        lines = []
        
        # هدر - حذف Emoji
        title = ReportTemplate._remove_emoji(title)
        lines.append(ReportTemplate.get_header(title))
        
        # بخش‌ها
        for section in sections:
            lines.append(ReportTemplate.get_section(
                title=section.get('title', ''),
                content=section.get('content', ''),
                level=section.get('level', 1)
            ))
        
        # متادیتا
        if metadata:
            lines.append(ReportTemplate.get_metadata(**metadata))
        
        # فوتر
        if footer_page is not None:
            lines.append(ReportTemplate.get_footer(page_number=footer_page))
        
        return "\n".join(lines)
    
    @staticmethod
    def get_parent_report_header(title, student_name, grade, class_name, include_date=True):
        """
        دریافت هدر گزارش والدین - ساده و دوستانه
        """
        lines = []
        lines.append("━" * 50)
        lines.append("")
        lines.append(f"  {title}")
        lines.append("")
        lines.append(f"  دانش‌آموز: {student_name}")
        lines.append(f"  پایه: {grade} - کلاس: {class_name}")
        lines.append("")
        
        if include_date:
            try:
                today = jdatetime.date.today()
                date_str = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
            except:
                date_str = datetime.now().strftime("%Y/%m/%d")
            lines.append(f"  تاریخ: {date_str}")
        
        lines.append("")
        lines.append("━" * 50)
        lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def get_school_report_header(title, student_name, grade, class_name, profile_id, include_date=True):
        """
        دریافت هدر گزارش مدرسه - رسمی و کامل
        """
        lines = []
        lines.append("━" * 60)
        lines.append("")
        lines.append(f"  {title}")
        lines.append("")
        lines.append(f"  نام دانش‌آموز: {student_name}")
        lines.append(f"  پایه: {grade} - کلاس: {class_name}")
        lines.append(f"  شناسه پرونده: {profile_id}")
        lines.append("")
        
        if include_date:
            try:
                today = jdatetime.date.today()
                date_str = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
            except:
                date_str = datetime.now().strftime("%Y/%m/%d")
            lines.append(f"  تاریخ تهیه: {date_str}")
        
        lines.append("")
        lines.append("━" * 60)
        lines.append("")
        lines.append("⚠️ این گزارش محرمانه است و فقط برای استفاده داخلی مدرسه تهیه شده است.")
        lines.append("━" * 60)
        lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def get_parent_footer():
        """
        دریافت فوتر گزارش والدین - ساده و دوستانه
        """
        lines = []
        lines.append("")
        lines.append("━" * 50)
        lines.append("")
        lines.append("  با احترام،")
        lines.append("  مدیریت مدرسه")
        lines.append("")
        lines.append("  PARTO - سامانه مدیریت پرونده دانش‌آموزان")
        lines.append("")
        lines.append("━" * 50)
        return "\n".join(lines)
    
    @staticmethod
    def get_school_footer(page_number=None, total_pages=None):
        """
        دریافت فوتر گزارش مدرسه - رسمی
        """
        lines = []
        lines.append("━" * 60)
        
        if page_number is not None:
            if total_pages is not None:
                lines.append(f"صفحه {page_number} از {total_pages}")
            else:
                lines.append(f"صفحه {page_number}")
        
        lines.append("")
        lines.append("  PARTO - سامانه مدیریت پرونده دانش‌آموزان")
        lines.append("  گزارش داخلی - محرمانه")
        lines.append("")
        lines.append("━" * 60)
        
        return "\n".join(lines)