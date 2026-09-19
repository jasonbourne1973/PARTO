"""
کلاس تولید PDF فارسی با پشتیبانی کامل از ReportLab
نسخه اصلاح‌شده با فونت از مسیر پروژه و حذف Emoji
"""

import os

from utils.logger import get_logger

logger = get_logger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("⚠️ reportlab نصب نیست. pip install reportlab")
    # ===== اصلاح (بازرسی دوم) =====
    # try/except بالا برای این بود که برنامه «بدون reportlab هم بالا بیاید»
    # و فقط موقع گرفتن خروجی PDF خطای خوانا بدهد. اما این قصد با یک خط
    # خنثی می‌شد:
    #
    #     def add_image(self, image_data, width=14*cm, height=9*cm):
    #
    # مقدار پیش‌فرض آرگومان «در زمان import» ارزیابی می‌شود، پس وقتی
    # reportlab نصب نباشد:
    #
    #     NameError: name 'cm' is not defined
    #
    # و چون utils.persian_pdf را این ماژول‌ها import می‌کنند:
    #     services/report_generator، services/parent_report_service،
    #     services/school_report_service، services/teacher_report_service
    # و آن‌ها هم توسط صفحه‌های گزارش import می‌شوند ⇒ کل برنامه با یک
    # NameError بی‌ربط بالا نمی‌آمد (نه پیام «reportlab نصب نیست»).
    #
    # اجرای واقعی روی محیط بدون reportlab (قبل از این اصلاح):
    #     import services.report_generator
    #     → ModuleNotFoundError/NameError: name 'cm' is not defined
    #
    # راه‌حل: همان مقادیر عددی reportlab به عنوان جایگزین تعریف می‌شوند
    # (reportlab: cm = 28.346456692913385 و inch = 72.0 نقطه). اگر
    # reportlab نصب باشد، import واقعی موفق است و این شاخه اصلاً اجرا
    # نمی‌شود؛ اگر نصب نباشد، import ماژول سالم می‌ماند و build()
    # پایین خطای خوانا می‌دهد.
    cm = 28.346456692913385   # ۱ سانتی‌متر بر حسب نقطه (point)
    inch = 72.0

# پیام یکپارچه برای نبودِ reportlab (در __init__ و _load_font استفاده می‌شود)
REPORTLAB_MISSING_MSG = (
    "کتابخانه reportlab نصب نیست و خروجی PDF گرفته نمی‌شود. "
    "نصب: pip install reportlab"
)

try:
    import arabic_reshaper
    ARABIC_RESHAPER_AVAILABLE = True
except ImportError:
    ARABIC_RESHAPER_AVAILABLE = False
    logger.warning("⚠️ arabic-reshaper نصب نیست. pip install arabic-reshaper")

try:
    from bidi.algorithm import get_display
    BIDI_AVAILABLE = True
except ImportError:
    BIDI_AVAILABLE = False
    logger.warning("⚠️ python-bidi نصب نیست. pip install python-bidi")


class PersianPDF:
    """
    کلاس تولید PDF فارسی با پشتیبانی کامل از:
    - فونت فارسی از مسیر پروژه (assets/fonts/)
    - arabic-reshaper برای اتصال حروف
    - python-bidi برای راست‌چین
    - جدول، عنوان، متن، تصویر و...
    - Page Break واقعی
    - بدون استفاده از Emoji
    """
    
    def __init__(self, file_path=None):
        self.file_path = file_path
        self.elements = []
        self.styles = {}
        self.font_name = None
        self.font_loaded = False
        self.font_error = None

        # ===== اصلاح (بازرسی دوم) =====
        # اگر reportlab نصب نباشد، _create_styles() با
        #     NameError: name 'getSampleStyleSheet' is not defined
        # و build() با
        #     NameError: name 'SimpleDocTemplate' is not defined
        # می‌شکست. هر دو بی‌ربط و گیج‌کننده‌اند.
        #
        # حالا همان اول، با پیام خوانا و قابل‌عمل شکست می‌خوریم تا
        # سرویس‌های گزارش‌ساز (که داخل try/except هستند) همان پیام را
        # به کاربر نشان دهند:
        #     «خطا در تولید PDF: کتابخانه reportlab نصب نیست ...»
        # و مهم‌تر: import ماژول (که با cm در مقدار پیش‌فرض add_image
        # می‌ترکید) دیگر برنامه را از بالا آمدن نمی‌اندازد.
        if not REPORTLAB_AVAILABLE:
            self.font_error = REPORTLAB_MISSING_MSG
            raise RuntimeError(self.font_error)

        self._load_font()
        self._create_styles()
    
    def _get_project_root(self):
        """دریافت مسیر ریشه پروژه"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # از utils به ریشه پروژه برو
        return os.path.dirname(current_dir)
    
    def _load_font(self):
        """بارگذاری فونت فارسی از مسیر پروژه - بدون وابستگی به ویندوز"""
        # ===== اصلاح (بازرسی دوم) =====
        # اگر reportlab نصب نباشد، pdfmetrics/TTFont تعریف نشده‌اند و خطای
        # واقعی «name 'pdfmetrics' is not defined» بود — پیامی که کاربر
        # نمی‌فهمد. حالا همان اول، پیام خوانا در font_error گذاشته می‌شود
        # تا _create_styles آن را با RuntimeError بالا بدهد و سرویس‌های
        # گزارش‌ساز (که داخل try هستند) به کاربر بگویند:
        # «reportlab نصب نیست؛ pip install reportlab».
        if not REPORTLAB_AVAILABLE:
            self.font_loaded = False
            self.font_error = REPORTLAB_MISSING_MSG
            return

        project_root = self._get_project_root()
        
        # لیست فونت‌های موجود در assets/fonts/
        font_files = [
            # اولویت با فونت‌های Vazirmatn
            "Vazirmatn-Regular.ttf",
            "Vazirmatn-Bold.ttf",
            "Vazir-Regular.ttf",
            "Vazir-Bold.ttf",
            "Vazir.ttf",
            "Vazir-FD.ttf",
            "BNazanin.ttf",
            "IRANSans.ttf",
            "Sahel.ttf",
        ]
        
        # مسیرهای جستجو
        search_paths = [
            os.path.join(project_root, "assets", "fonts"),
            os.path.join(project_root, "assets", "font"),
            os.path.join(project_root, "fonts"),
            # مسیرهای رایج در سیستم برای پشتیبانی بیشتر
            "C:/Windows/Fonts",
            "/usr/share/fonts",
            "/usr/local/share/fonts",
        ]
        
        # جستجو در مسیرهای مختلف
        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue
                
            for font_file in font_files:
                font_path = os.path.join(search_path, font_file)
                if os.path.exists(font_path):
                    try:
                        # ثبت فونت با نام 'PersianFont'
                        pdfmetrics.registerFont(TTFont('PersianFont', font_path))
                        self.font_name = 'PersianFont'
                        self.font_loaded = True
                        logger.debug(f"✅ فونت فارسی از {font_path} بارگذاری شد")
                        return
                    except Exception as e:
                        logger.error(f"⚠️ خطا در بارگذاری فونت {font_path}: {e}")
                        continue
        
        # اگر هیچ فونتی پیدا نشد، خطای واضح ایجاد کن
        self.font_loaded = False
        self.font_error = (
            "❌ خطای حیاتی: هیچ فونت فارسی در مسیر پروژه پیدا نشد!\n"
            "لطفاً یکی از فونت‌های زیر را در پوشه assets/fonts/ قرار دهید:\n"
            "  - Vazirmatn-Regular.ttf (پیشنهادی)\n"
            "  - Vazir-Regular.ttf\n"
            "  - BNazanin.ttf\n"
            "  - IRANSans.ttf\n"
            "مسیر جستجو: " + os.path.join(self._get_project_root(), "assets", "fonts")
        )
        logger.debug(self.font_error)
        
        # از فونت پیش‌فرض ReportLab استفاده نکن
        self.font_name = None
    
    def _create_styles(self):
        """ایجاد سبک‌های مختلف برای PDF با پشتیبانی از فارسی"""
        styles = getSampleStyleSheet()
        
        # اگر فونت فارسی بارگذاری نشده، خطا بده
        if not self.font_loaded or self.font_name is None:
            raise RuntimeError(self.font_error)
        
        font_name = self.font_name
        
        self.styles['normal'] = ParagraphStyle(
            'NormalPersian',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=12,
            alignment=TA_RIGHT,
            encoding='utf-8',
            leading=20,
            spaceAfter=4
        )
        
        self.styles['bold'] = ParagraphStyle(
            'BoldPersian',
            parent=self.styles['normal'],
            fontName=font_name,
            fontSize=14,
            alignment=TA_RIGHT,
            font_weight='bold',
            leading=22,
            spaceAfter=6
        )
        
        self.styles['title'] = ParagraphStyle(
            'TitlePersian',
            parent=self.styles['bold'],
            fontName=font_name,
            fontSize=22,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a252f'),
            leading=30,
            spaceAfter=16
        )
        
        self.styles['subtitle'] = ParagraphStyle(
            'SubtitlePersian',
            parent=self.styles['bold'],
            fontName=font_name,
            fontSize=16,
            alignment=TA_RIGHT,
            textColor=colors.HexColor('#2980b9'),
            leading=24,
            spaceAfter=10
        )
        
        self.styles['strength'] = ParagraphStyle(
            'StrengthPersian',
            parent=self.styles['normal'],
            fontName=font_name,
            fontSize=12,
            alignment=TA_RIGHT,
            textColor=colors.HexColor('#27ae60'),
            spaceAfter=2
        )
        
        self.styles['weakness'] = ParagraphStyle(
            'WeaknessPersian',
            parent=self.styles['normal'],
            fontName=font_name,
            fontSize=12,
            alignment=TA_RIGHT,
            textColor=colors.HexColor('#e74c3c'),
            spaceAfter=2
        )
        
        self.styles['ltr'] = ParagraphStyle(
            'LTRPersian',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            alignment=TA_LEFT,
            encoding='utf-8',
            leading=18
        )
        
        self.styles['table_header'] = ParagraphStyle(
            'TableHeaderPersian',
            parent=self.styles['bold'],
            fontName=font_name,
            fontSize=11,
            alignment=TA_CENTER,
            textColor=colors.white,
            leading=16,
            spaceAfter=0
        )
        
        self.styles['table_cell'] = ParagraphStyle(
            'TableCellPersian',
            parent=self.styles['normal'],
            fontName=font_name,
            fontSize=11,
            alignment=TA_RIGHT,
            leading=16,
            spaceAfter=0
        )
    
    def _prepare(self, text):
        """
        آماده‌سازی متن فارسی برای PDF
        - اتصال حروف با arabic-reshaper
        - راست‌چین با python-bidi
        - استفاده از یک تابع واحد برای تمام متن‌ها
        """
        if not text:
            return ""
        
        text = str(text)
        
        # اگر فونت فارسی بارگذاری نشده، خطا بده
        if not self.font_loaded:
            raise RuntimeError(self.font_error)
        
        # مرحله ۱: اتصال حروف فارسی
        if ARABIC_RESHAPER_AVAILABLE:
            try:
                text = arabic_reshaper.reshape(text)
            except Exception as e:
                logger.error(f"⚠️ خطا در reshape: {e}")
                pass
        
        # مرحله ۲: راست‌چین کردن
        if BIDI_AVAILABLE:
            try:
                text = get_display(text)
            except Exception as e:
                logger.error(f"⚠️ خطا در get_display: {e}")
                pass
        
        return text
    
    def add_title(self, text):
        """اضافه کردن عنوان اصلی - بدون Emoji"""
        self.elements.append(Paragraph(self._prepare(text), self.styles['title']))
        self.elements.append(Spacer(1, 0.5*cm))
    
    def add_subtitle(self, text):
        """اضافه کردن زیرعنوان - بدون Emoji"""
        # حذف Emoji از متن
        text = self._remove_emoji(text)
        self.elements.append(Paragraph(self._prepare(text), self.styles['subtitle']))
        self.elements.append(Spacer(1, 0.3*cm))
    
    def add_bold(self, text):
        """اضافه کردن متن پررنگ - بدون Emoji"""
        text = self._remove_emoji(text)
        self.elements.append(Paragraph(self._prepare(text), self.styles['bold']))
    
    def add_text(self, text):
        """اضافه کردن متن معمولی - بدون Emoji"""
        if not text:
            return
        text = self._remove_emoji(text)
        self.elements.append(Paragraph(self._prepare(text), self.styles['normal']))
    
    def add_strength(self, text):
        """اضافه کردن متن با رنگ سبز (نقاط قوت) - بدون Emoji"""
        text = self._remove_emoji(text)
        # استفاده از علامت متنی ساده به جای ⭐
        self.elements.append(Paragraph(self._prepare(f"[+] {text}"), self.styles['strength']))
    
    def add_weakness(self, text):
        """اضافه کردن متن با رنگ قرمز (نقاط ضعف) - بدون Emoji"""
        text = self._remove_emoji(text)
        # استفاده از علامت متنی ساده به جای 🔴
        self.elements.append(Paragraph(self._prepare(f"[-] {text}"), self.styles['weakness']))
    
    def add_spacer(self, height=0.3):
        """اضافه کردن فاصله عمودی"""
        self.elements.append(Spacer(1, height*cm))
    
    def add_separator(self):
        """اضافه کردن خط جداکننده - بدون Emoji"""
        self.elements.append(Spacer(1, 0.2*cm))
        self.add_text("━" * 60)
        self.elements.append(Spacer(1, 0.2*cm))
    
    def add_page_break(self):
        """
        اضافه کردن صفحه جدید - Page Break واقعی
        این تابع واقعاً یک صفحه جدید ایجاد می‌کند
        """
        self.elements.append(PageBreak())
    
    def add_table(self, data, col_widths=None, header=True):
        """
        اضافه کردن جدول با پشتیبانی از فارسی - بدون Emoji
        
        Args:
            data: لیست دوبعدی داده‌ها
            col_widths: لیست عرض ستون‌ها (اختیاری)
            header: آیا ردیف اول به عنوان هدر است؟
        """
        if not data or len(data) < 1:
            return
        
        table_data = []
        
        for row_idx, row in enumerate(data):
            new_row = []
            for cell in row:
                if isinstance(cell, str):
                    # حذف Emoji از سلول
                    cell = self._remove_emoji(cell)
                    # اگر ردیف اول و هدر است، از استایل هدر استفاده کن
                    if row_idx == 0 and header:
                        style = self.styles['table_header']
                    else:
                        style = self.styles['table_cell']
                    new_row.append(Paragraph(self._prepare(cell), style))
                else:
                    new_row.append(cell)
            table_data.append(new_row)
        
        # محاسبه خودکار عرض ستون‌ها اگر مشخص نشده باشد
        if col_widths is None:
            col_count = len(data[0]) if data else 1
            page_width = 16 * cm
            col_widths = [page_width / col_count] * col_count
        
        table = Table(table_data, colWidths=col_widths)
        
        style = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]
        
        if header:
            style.append(('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')))
            style.append(('TEXTCOLOR', (0, 0), (-1, 0), colors.white))
            style.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
        
        # راست‌چین کردن سلول‌های غیر هدر
        if header:
            for i in range(1, len(data)):
                style.append(('ALIGN', (0, i), (-1, i), 'RIGHT'))
        
        table.setStyle(TableStyle(style))
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.3*cm))
    
    def add_image(self, image_data, width=14*cm, height=9*cm):
        """اضافه کردن تصویر"""
        try:
            if isinstance(image_data, str) and os.path.exists(image_data):
                img = Image(image_data, width=width, height=height)
            else:
                img = Image(image_data, width=width, height=height)
            
            self.elements.append(img)
            self.elements.append(Spacer(1, 0.3*cm))
        except Exception as e:
            logger.error(f"⚠️ خطا در اضافه کردن تصویر: {e}")
            self.add_text("(نمودار قابل نمایش نیست)")
    
    def _remove_emoji(self, text):
        """
        حذف Emoji از متن
        """
        if not text:
            return text
        
        # لیست Emojiهای رایج که باید حذف شوند
        emoji_patterns = [
            '⭐', '🌟', '✨', '💡', '📊', '📚', '🏫', '👤', '👨', '👩', '👦', '👧',
            '🔴', '🟢', '🟡', '🔵', '🟣', '🟠', '⚪', '⚫',
            '✅', '❌', '⚠️', 'ℹ️', '📌', '🔹', '🔸', '🫂', '👨‍👩‍👦',
            '📋', '📝', '📈', '📉', '📅', '📆', '📁', '📂', '📎', '🖊️', '🖋️',
            '😊', '😐', '😟', '😢', '😡', '👍', '👎', '👏', '🙏', '🤝',
            '🎯', '🏆', '🎖️', '🏅', '🎗️', '🎀', '🎁', '🎉', '🎊', '🎈',
            '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎',
            '🚀', '💪', '🤗', '🧠', '👀', '👂', '🗣️', '💬', '💭',
        ]
        
        for emoji in emoji_patterns:
            text = text.replace(emoji, '')
        
        # حذف ایموجی‌های Unicode (محدوده‌های رایج)
        import re
        # حذف ایموجی‌های Unicode
        emoji_unicode_pattern = re.compile(
            "[\U0001F600-\U0001F64F"  # احساسات
            "\U0001F300-\U0001F5FF"   # نمادها و نشانه‌ها
            "\U0001F680-\U0001F6FF"   # حمل و نقل و نقشه
            "\U0001F700-\U0001F77F"   # نمادهای الفبایی
            "\U0001F780-\U0001F7FF"   # نمادهای هندسی
            "\U0001F800-\U0001F8FF"   # نمادهای اضافی
            "\U0001F900-\U0001F9FF"   # ایموجی‌های تکمیلی
            "\U0001FA00-\U0001FA6F"   # ایموجی‌های تکمیلی
            "\U0001FA70-\U0001FAFF"   # نمادهای تکمیلی
            "\U00002702-\U000027B0"   # نمادهای زینتی
            "\U000024C2-\U0001F251"   # نمادهای محصور شده
            "]",
            flags=re.UNICODE
        )
        text = emoji_unicode_pattern.sub('', text)
        
        # پاکسازی فاصله‌های اضافی
        text = ' '.join(text.split())
        
        return text.strip()
    
    def build(self, file_path=None):
        """ساخت و ذخیره PDF"""
        output_path = file_path or self.file_path
        if not output_path:
            raise ValueError("مسیر فایل مشخص نشده است.")
        
        # ===== اصلاح (بازرسی دوم) =====
        # گارد صریح reportlab: بدون آن، SimpleDocTemplate تعریف‌نشده بود و
        # NameError می‌داد. (در حالت عادی __init__ زودتر شکست می‌خورد، اما
        # اگر کسی نمونه را از راه دیگری ساخته باشد، پیام خوانا می‌گیرد.)
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError(REPORTLAB_MISSING_MSG)

        # اگر فونت بارگذاری نشده، خطا بده
        if not self.font_loaded:
            raise RuntimeError(self.font_error)
        
        # اطمینان از وجود پوشه
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        try:
            doc.build(self.elements)
            logger.debug(f"✅ PDF در {output_path} ساخته شد.")
            return True
        except Exception as e:
            logger.error(f"❌ خطا در ساخت PDF: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def clear(self):
        """پاک کردن محتوای PDF"""
        self.elements = []