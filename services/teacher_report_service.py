"""
سرویس تولید گزارش معلم - بدون Emoji
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ===== اصلاح (بازرسی دوم) =====
# این importها «بدون گارد» در سطح ماژول بودند. اگر openpyxl نصب نبود:
#
#     import services.teacher_report_service
#     → ModuleNotFoundError: No module named 'openpyxl'
#
# و چون صفحه گزارش معلم این ماژول را import می‌کند، کل برنامه بالا
# نمی‌آمد (به‌جای پیام «openpyxl نصب نیست»). همین الگو در
# services/class_report_service.py درست پیاده شده بود (import داخل متد
# با except ImportError و پیام راهنما) — اینجا هم همان رفتار گرفته شد.
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    Workbook = Font = PatternFill = Alignment = Border = Side = None
    get_column_letter = None
    logger.warning("⚠️ openpyxl نصب نیست. pip install openpyxl")

import jdatetime

from utils.behavior_analysis import classify_pattern, pattern_label
from utils.logger import get_logger
from utils.persian_pdf import PersianPDF
from utils.time_utils import utc_now


class TeacherReportService:
    """سرویس تولید گزارش معلم با خروجی Excel و PDF - بدون Emoji"""
    
    def __init__(self):
        pass
    
    def export_to_pdf(self, report_data, file_path):
        """
        خروجی گزارش معلم به PDF با طراحی حرفه‌ای - بدون Emoji
        
        Args:
            report_data: دیکشنری داده‌های گزارش
            file_path: مسیر ذخیره فایل PDF
        """
        try:
            pdf = PersianPDF(file_path)
            
            # ===== عنوان =====
            pdf.add_title("گزارش عملکرد معلم")
            pdf.add_spacer(0.2)
            
            # ===== اطلاعات معلم =====
            info_items = [
                f"نام معلم: {report_data.get('teacher_name', 'نامشخص')}",
                f"تعداد دانش آموزان: {report_data.get('total_students', 0)} نفر",
                f"بازه زمانی: {report_data.get('start_date', '')} تا {report_data.get('end_date', '')}",
                f"سال تحصیلی: {report_data.get('year_title', 'همه سال‌ها')}",
            ]
            
            for item in info_items:
                pdf.add_text(item)
            pdf.add_spacer(0.3)
            
            # ===== آمار کلی =====
            pdf.add_subtitle("آمار کلی")
            total = report_data.get('total_observations', 0)
            positive = report_data.get('positive_observations', 0)
            negative = report_data.get('negative_observations', 0)
            neutral = report_data.get('neutral_observations', 0)
            positive_percent = (positive / total * 100) if total > 0 else 0
            
            stats_items = [
                f"* کل مشاهدات: {total}",
                f"* مشاهدات مثبت: {positive} ({positive_percent:.0f}%)",
                f"* مشاهدات منفی: {negative} ({negative/total*100 if total > 0 else 0:.0f}%)",
                f"* مشاهدات خنثی: {neutral} ({neutral/total*100 if total > 0 else 0:.0f}%)",
                f"* مداخلات ثبت شده: {report_data.get('total_interventions', 0)}",
                f"* پیگیری‌های باز: {report_data.get('pending_followups', 0)}",
            ]
            
            for item in stats_items:
                pdf.add_text(item)
            pdf.add_spacer(0.3)
            
            # ===== تحلیل وضعیت =====
            pdf.add_subtitle("تحلیل وضعیت کلاس")
            if positive_percent >= 60:
                status_text = "وضعیت کلاس مطلوب است. فضای آموزشی مثبت و سازنده حاکم است."
            elif positive_percent >= 40:
                status_text = "وضعیت کلاس متوسط است. با تلاش بیشتر می‌توان به بهبود کمک کرد."
            else:
                status_text = "وضعیت کلاس نیازمند توجه ویژه است. بررسی و تغییر رویکرد توصیه می‌شود."
            pdf.add_text(status_text)
            pdf.add_spacer(0.3)
            
            # ===== شایستگی‌ها =====
            stats = report_data.get('competency_stats', {})
            if stats:
                pdf.add_subtitle("وضعیت زمینه‌ها (بر پایهٔ نوع رفتار ثبت‌شده)")
                table_data = [["زمینه", "مثبت", "منفی", "از مشاهدات", "الگو"]]
                for name, stat in list(stats.items())[:15]:
                    # بازرسی یازدهم: الگو از نوع رفتار می‌آید، نه میانگین شدت
                    kind = classify_pattern(
                        stat.get('positive', 0), stat.get('negative', 0),
                        max(stat.get('count', 0) - stat.get('positive', 0)
                            - stat.get('negative', 0), 0),
                        stat.get('count', 0))
                    table_data.append([
                        name, str(stat.get('positive', 0)),
                        str(stat.get('negative', 0)), str(stat['count']),
                        pattern_label(kind)])
                pdf.add_table(table_data)
                pdf.add_spacer(0.3)
            
            # ===== لیست دانش‌آموزان =====
            students_data = report_data.get('students_data', [])
            if students_data:
                pdf.add_subtitle("لیست دانش آموزان")
                table_data = [["ردیف", "دانش آموز", "پایه", "کلاس", "مشاهدات", "وضعیت"]]
                for idx, s in enumerate(students_data[:20], 1):
                    table_data.append([
                        str(idx),
                        s['student'].full_name,
                        str(s['assignment'].grade) if s['assignment'].grade else "-",
                        s['assignment'].class_name or "-",
                        str(s['observations_count']),
                        s['status']
                    ])
                pdf.add_table(table_data)
                pdf.add_spacer(0.3)
            
            # ===== پیشنهادات =====
            recs = report_data.get('recommendations', {})
            pdf.add_subtitle("پیشنهادات")
            
            pdf.add_bold("به معلم:")
            for rec in recs.get('teacher', []):
                pdf.add_text(f"* {rec}")
            pdf.add_spacer(0.2)
            
            pdf.add_bold("به مشاور:")
            for rec in recs.get('counselor', []):
                pdf.add_text(f"* {rec}")
            if not recs.get('counselor'):
                pdf.add_text("وضعیت عمومی مطلوب است. نیاز به مداخله خاصی نیست.")
            pdf.add_spacer(0.3)
            
            # ===== متادیتا =====
            pdf.add_separator()
            try:
                today = jdatetime.date.today()
                date_str = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
            except Exception as _exc:
                logger.debug(f"خطای مدیریت‌شده در export_to_pdf (مسیر جایگزین): {_exc}")
                date_str = utc_now().strftime("%Y/%m/%d")
            
            pdf.add_text(f"تاریخ تهیه گزارش: {date_str}")
            pdf.add_text("PARTO - سامانه مدیریت پرونده دانش آموزان")
            pdf.add_text("پشتیبانی: support@partow.ir")
            
            # ساخت PDF
            pdf.build(file_path)
            
        except Exception as e:
            raise Exception(f"خطا در تولید PDF: {e!s}")
    
    def export_to_excel(self, report_data, file_path):
        """خروجی گزارش معلم به Excel - بدون Emoji"""
        # اگر openpyxl نصب نباشد، به‌جای NameError یک پیام خوانا بده
        if not OPENPYXL_AVAILABLE:
            raise Exception("کتابخانه openpyxl نصب نیست و خروجی Excel گرفته نمی‌شود. "
                            "نصب: pip install openpyxl")

        wb = Workbook()
        
        # ===== برگه 1: خلاصه =====
        ws1 = wb.active
        ws1.title = "خلاصه"
        
        # استایل هدر
        header_font = Font(name='B Nazanin', size=12, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')
        header_alignment = Alignment(horizontal='center', vertical='center')
        
        # عنوان
        ws1.cell(row=1, column=1, value="گزارش عملکرد معلم").font = Font(name='B Nazanin', size=16, bold=True)
        ws1.merge_cells('A1:D1')
        
        # اطلاعات
        info_data = [
            ("نام معلم", report_data.get('teacher_name', 'نامشخص')),
            ("تعداد دانش‌آموزان", report_data.get('total_students', 0)),
            ("بازه زمانی", f"{report_data.get('start_date', '')} تا {report_data.get('end_date', '')}"),
            ("سال تحصیلی", report_data.get('year_title', 'همه سال‌ها')),
        ]
        
        for row, (label, value) in enumerate(info_data, 3):
            ws1.cell(row=row, column=1, value=label).font = Font(name='B Nazanin', size=12, bold=True)
            ws1.cell(row=row, column=2, value=value).font = Font(name='B Nazanin', size=12)
            ws1.merge_cells(f'A{row}:B{row}')
        
        # آمار
        row = 8
        ws1.cell(row=row, column=1, value="آمار کلی").font = Font(name='B Nazanin', size=14, bold=True)
        row += 1
        
        stats = [
            ("کل مشاهدات", report_data.get('total_observations', 0)),
            ("مشاهدات مثبت", report_data.get('positive_observations', 0)),
            ("مشاهدات منفی", report_data.get('negative_observations', 0)),
            ("مشاهدات خنثی", report_data.get('neutral_observations', 0)),
            ("مداخلات ثبت‌شده", report_data.get('total_interventions', 0)),
            ("پیگیری‌های باز", report_data.get('pending_followups', 0)),
        ]
        
        for label, value in stats:
            ws1.cell(row=row, column=1, value=label).font = Font(name='B Nazanin', size=11, bold=True)
            ws1.cell(row=row, column=2, value=value).font = Font(name='B Nazanin', size=11)
            row += 1
        
        ws1.column_dimensions['A'].width = 30
        ws1.column_dimensions['B'].width = 20
        
        # ===== برگه 2: شایستگی‌ها =====
        ws2 = wb.create_sheet("شایستگی‌ها")
        
        ws2.cell(row=1, column=1, value="شایستگی").font = header_font
        ws2.cell(row=1, column=1).fill = header_fill
        ws2.cell(row=1, column=2, value="مثبت").font = header_font
        ws2.cell(row=1, column=2).fill = header_fill
        ws2.cell(row=1, column=3, value="منفی").font = header_font
        ws2.cell(row=1, column=3).fill = header_fill
        ws2.cell(row=1, column=4, value="الگو (بر پایهٔ نوع رفتار)").font = header_font
        ws2.cell(row=1, column=4).fill = header_fill
        
        stats = report_data.get('competency_stats', {})
        row = 2
        for name, stat in stats.items():
            ws2.cell(row=row, column=1, value=name)
            ws2.cell(row=row, column=2, value=stat.get('positive', 0))
            ws2.cell(row=row, column=3, value=stat.get('negative', 0))
            # بازرسی یازدهم: الگو از نوع رفتار می‌آید، نه میانگین شدت
            status = pattern_label(classify_pattern(
                stat.get('positive', 0), stat.get('negative', 0),
                max(stat.get('count', 0) - stat.get('positive', 0)
                    - stat.get('negative', 0), 0),
                stat.get('count', 0)))
            ws2.cell(row=row, column=4, value=status)
            row += 1
        
        ws2.column_dimensions['A'].width = 30
        ws2.column_dimensions['B'].width = 20
        ws2.column_dimensions['C'].width = 15
        ws2.column_dimensions['D'].width = 20
        
        # ===== برگه 3: دانش‌آموزان =====
        ws3 = wb.create_sheet("دانش‌آموزان")
        
        headers = ["ردیف", "دانش‌آموز", "پایه", "کلاس", "مشاهدات", "درصد مثبت", "وضعیت کلی"]
        for col, header in enumerate(headers, 1):
            cell = ws3.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        students_data = report_data.get('students_data', [])
        row = 2
        for idx, s in enumerate(students_data, 1):
            ws3.cell(row=row, column=1, value=idx)
            ws3.cell(row=row, column=2, value=s['student'].full_name)
            ws3.cell(row=row, column=3, value=s['assignment'].grade or "-")
            ws3.cell(row=row, column=4, value=s['assignment'].class_name or "-")
            ws3.cell(row=row, column=5, value=s['observations_count'])
            ws3.cell(row=row, column=6, value=f"{s.get('positive_percent', 0):.0f}%")
            ws3.cell(row=row, column=7, value=s['status'])
            row += 1
        
        for col in range(1, 8):
            ws3.column_dimensions[get_column_letter(col)].width = 20
        
        # ذخیره
        wb.save(file_path)