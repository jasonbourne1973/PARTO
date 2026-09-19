"""
ابزارهای کمکی برای رسم نمودارهای روند و وضعیت پرونده
بدون مقایسه و رتبه‌بندی دانش‌آموزان
با نمودارهای جدید برای داشبورد تحلیلی و چندساله
"""

import matplotlib

matplotlib.use('QtAgg')
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    PERSIAN_FONT_SUPPORT = True
except ImportError:
    PERSIAN_FONT_SUPPORT = False


class ChartHelper:
    """
    ابزار کمکی برای رسم نمودارهای روند
    
    ویژگی‌ها:
    - نمایش روند بر اساس خود دانش‌آموز
    - بدون مقایسه با دیگران
    - بدون رتبه‌بندی
    - نمایش تغییرات در طول زمان
    - نمودارهای پیشرفته برای داشبورد تحلیلی
    - نمودارهای چندساله
    """
    
    @staticmethod
    def _farsi(text):
        """اصلاح نمایش حروف فارسی در Matplotlib"""
        if not text:
            return ""
        if PERSIAN_FONT_SUPPORT:
            try:
                return get_display(arabic_reshaper.reshape(str(text)))
            except Exception:
                return str(text)
        return str(text)
    
    # ============================================================
    # نمودارهای موجود
    # ============================================================
    
    @staticmethod
    def create_trend_chart(trend_data, title=None):
        """ایجاد نمودار روند تغییرات بر اساس خود دانش‌آموز"""
        if not trend_data or not trend_data.get('success', False):
            return ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        trend_items = trend_data.get('trend_data', [])
        if not trend_items:
            return ChartHelper._create_empty_chart("هیچ مشاهده‌ای ثبت نشده است")
        
        fig = Figure(figsize=(7, 4), dpi=100, facecolor='#0B2E4F')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0B2E4F')
        
        labels = [ChartHelper._farsi(item['label']) for item in trend_items]
        positive = [item['positive'] for item in trend_items]
        negative = [item['negative'] for item in trend_items]
        neutral = [item['neutral'] for item in trend_items]
        
        x = np.arange(len(labels))
        width = 0.25
        
        ax.bar(x - width, positive, width, label=ChartHelper._farsi('مثبت'), 
               color='#8BC34A', edgecolor='none', alpha=0.8)
        ax.bar(x, negative, width, label=ChartHelper._farsi('منفی'), 
               color='#C62828', edgecolor='none', alpha=0.8)
        ax.bar(x + width, neutral, width, label=ChartHelper._farsi('خنثی'), 
               color='#F4D35E', edgecolor='none', alpha=0.8)
        
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9, color='#475569', fontweight='bold')
        
        max_val = max([sum(item) for item in zip(positive, negative, neutral)]) if trend_items else 10
        ax.set_ylim(0, max_val * 1.3)
        ax.tick_params(axis='both', which='both', length=0, labelsize=9, colors='#D9C36A')
        
        ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#D9C36A', zorder=0)
        ax.xaxis.grid(False)
        
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        if title:
            ax.set_title(ChartHelper._farsi(title), fontsize=14, fontweight='bold', 
                        color='#F4C542', pad=15)
        
        ax.legend(loc='upper right', fontsize=9, frameon=True, 
                  facecolor='#0B2E4F', edgecolor='#D9C36A', framealpha=0.9)
        
        fig.subplots_adjust(left=0.08, right=0.96, top=0.88, bottom=0.18)
        
        return FigureCanvas(fig)
    
    @staticmethod
    def create_pie_chart(labels, values, colors=None, title=None):
        """ایجاد نمودار دایره‌ای برای نمایش توزیع"""
        if not values or sum(values) == 0:
            return ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        fig = Figure(figsize=(5, 4), dpi=100, facecolor='#0B2E4F')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0B2E4F')
        
        if not colors:
            colors = ['#8BC34A', '#C62828', '#F4D35E', '#0B2E4F', '#66BB6A']
        
        labels_fa = [ChartHelper._farsi(str(label)) for label in labels]
        _wedges, _texts, autotexts = ax.pie(
            values, 
            labels=labels_fa,
            colors=colors[:len(labels)],
            autopct='%1.0f%%',
            startangle=90,
            textprops={'fontsize': 10, 'fontweight': '600'}
        )
        
        for autotext in autotexts:
            autotext.set_color('#F4C542')
            autotext.set_fontweight('bold')
        
        if title:
            ax.set_title(ChartHelper._farsi(title), fontsize=14, fontweight='bold', 
                        color='#F4C542', pad=15)
        
        fig.subplots_adjust(left=0.05, right=0.95, top=0.88, bottom=0.05)
        
        return FigureCanvas(fig)
    
    @staticmethod
    def create_progress_chart(progress_data, title=None):
        """ایجاد نمودار پیشرفت بر اساس خود دانش‌آموز"""
        if not progress_data or not progress_data.get('has_data', False):
            return ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        fig = Figure(figsize=(6, 3.5), dpi=100, facecolor='#0B2E4F')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0B2E4F')
        
        first_half_pos = progress_data.get('first_half_positive', 0)
        first_half_neg = progress_data.get('first_half_negative', 0)
        second_half_pos = progress_data.get('second_half_positive', 0)
        second_half_neg = progress_data.get('second_half_negative', 0)
        
        x = np.arange(2)
        width = 0.35
        
        ax.bar(x - width/2, [first_half_pos, second_half_pos], width, 
               label=ChartHelper._farsi('مثبت'), color='#8BC34A', edgecolor='none', alpha=0.8)
        ax.bar(x + width/2, [first_half_neg, second_half_neg], width,
               label=ChartHelper._farsi('منفی'), color='#C62828', edgecolor='none', alpha=0.8)
        
        ax.set_xticks(x)
        ax.set_xticklabels([ChartHelper._farsi('نیمسال اول'), ChartHelper._farsi('نیمسال دوم')], 
                          fontsize=11, color='#475569', fontweight='bold')
        ax.tick_params(axis='both', which='both', length=0, labelsize=10, colors='#D9C36A')
        ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#D9C36A', zorder=0)
        ax.xaxis.grid(False)
        
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        if title:
            ax.set_title(ChartHelper._farsi(title), fontsize=14, fontweight='bold', 
                        color='#F4C542', pad=15)
        
        ax.legend(loc='upper right', fontsize=10, frameon=True, 
                  facecolor='#0B2E4F', edgecolor='#D9C36A', framealpha=0.9)
        
        trend_icon = progress_data.get('trend_icon', '')
        trend_text = progress_data.get('trend', '')
        if trend_text:
            fig.text(0.5, 0.02, ChartHelper._farsi(f"{trend_icon} روند کلی: {trend_text}"), 
                    ha='center', fontsize=11, fontweight='bold',
                    color=progress_data.get('color', '#F4C542'))
        
        fig.subplots_adjust(left=0.1, right=0.96, top=0.85, bottom=0.12)
        
        return FigureCanvas(fig)
    
    @staticmethod
    def create_student_timeline_chart(events):
        """ایجاد نمودار Timeline رویدادهای دانش‌آموز"""
        if not events:
            return ChartHelper._create_empty_chart("هیچ رویدادی ثبت نشده است")
        
        fig = Figure(figsize=(6, 4), dpi=100, facecolor='#0B2E4F')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0B2E4F')
        
        obs_count = sum(1 for e in events if e['type'] == 'observation')
        inter_count = sum(1 for e in events if e['type'] == 'intervention')
        follow_count = sum(1 for e in events if e['type'] == 'followup')
        
        display_events = events[:15]
        
        y_positions = np.arange(len(display_events))
        colors = []
        labels = []
        
        for event in display_events:
            if event['type'] == 'observation':
                colors.append('#0B2E4F')
                labels.append('مشاهده')
            elif event['type'] == 'intervention':
                colors.append('#F28C28')
                labels.append('مداخله')
            else:
                colors.append('#66BB6A')
                labels.append('پیگیری')
        
        ax.scatter([1] * len(display_events), y_positions, 
                  c=colors, s=100, alpha=0.8, zorder=3)
        
        ax.set_title(ChartHelper._farsi('خط زمانی رویدادها'), fontsize=14, fontweight='bold', 
                    color='#F4C542', pad=15)
        
        ax.set_yticklabels([ChartHelper._farsi(e['date'] or 'نامشخص') for e in display_events], 
                          fontsize=8, color='#475569')
        ax.set_yticks(y_positions)
        ax.tick_params(axis='both', which='both', length=0, labelsize=9, colors='#D9C36A')
        ax.set_xlim(0.5, 1.5)
        ax.set_xticks([])
        ax.xaxis.grid(False)
        ax.yaxis.grid(True, linestyle='--', alpha=0.3, color='#D9C36A')
        
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        info_text = f"مشاهدات: {obs_count} | مداخلات: {inter_count} | پیگیری‌ها: {follow_count}"
        fig.text(0.5, 0.02, ChartHelper._farsi(info_text), 
                ha='center', fontsize=10, color='#D9C36A')
        
        fig.subplots_adjust(left=0.25, right=0.9, top=0.88, bottom=0.1)
        
        return FigureCanvas(fig)
    
    # ============================================================
    # نمودارهای جدید برای داشبورد تحلیلی
    # ============================================================
    
    @staticmethod
    def create_distribution_chart(data, chart_type='bar', title=None, xlabel=None, ylabel=None):
        """
        ایجاد نمودار توزیع داده‌ها
        
        Args:
            data: dict یا list داده‌ها
            chart_type: نوع نمودار ('bar', 'pie', 'horizontal_bar')
            title: عنوان نمودار
            xlabel: برچسب محور x
            ylabel: برچسب محور y
        
        Returns:
            FigureCanvas: شیء قابل نمایش در Qt
        """
        if not data:
            return ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        fig = Figure(figsize=(6, 4), dpi=100, facecolor='#0B2E4F')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0B2E4F')
        
        items = list(data.items()) if isinstance(data, dict) else data
        
        if not items:
            return ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        labels = [ChartHelper._farsi(str(item[0] if isinstance(item, (list, tuple)) else item)) for item in items]
        values = [item[1] if isinstance(item, (list, tuple)) else 1 for item in items]
        
        if chart_type == 'pie':
            colors = ['#8BC34A', '#C62828', '#F4D35E', '#0B2E4F', '#66BB6A', '#1abc9c', '#F28C28']
            ax.pie(values, labels=labels, colors=colors[:len(labels)], 
                   autopct='%1.1f%%', startangle=90)
            if title:
                ax.set_title(ChartHelper._farsi(title), fontsize=14, fontweight='bold')
        
        elif chart_type == 'horizontal_bar':
            y_pos = np.arange(len(labels))
            ax.barh(y_pos, values, color='#0B2E4F', edgecolor='none', alpha=0.8)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=9)
            if title:
                ax.set_title(ChartHelper._farsi(title), fontsize=14, fontweight='bold')
            if xlabel:
                ax.set_xlabel(ChartHelper._farsi(xlabel), fontsize=11)
            ax.xaxis.grid(True, linestyle='--', alpha=0.3, color='#D9C36A')
            for spine in ax.spines.values():
                spine.set_visible(False)
        
        else:  # bar
            ax.bar(labels, values, color='#0B2E4F', edgecolor='none', alpha=0.8)
            if title:
                ax.set_title(ChartHelper._farsi(title), fontsize=14, fontweight='bold')
            if xlabel:
                ax.set_xlabel(ChartHelper._farsi(xlabel), fontsize=11)
            if ylabel:
                ax.set_ylabel(ChartHelper._farsi(ylabel), fontsize=11)
            ax.yaxis.grid(True, linestyle='--', alpha=0.3, color='#D9C36A')
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.tick_params(axis='x', rotation=30)
        
        fig.subplots_adjust(left=0.12, right=0.96, top=0.85, bottom=0.15)
        return FigureCanvas(fig)
    
    @staticmethod
    def create_competency_chart(competency_data, title=None):
        """
        ایجاد نمودار شایستگی‌ها
        
        Args:
            competency_data: list of dict با کلیدهای 'competency_name' و 'count'
            title: عنوان نمودار
        
        Returns:
            FigureCanvas: شیء قابل نمایش در Qt
        """
        if not competency_data:
            return ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        fig = Figure(figsize=(6, 4), dpi=100, facecolor='#0B2E4F')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0B2E4F')
        
        names = [ChartHelper._farsi(item.get('competency_name', 'نامشخص')) for item in competency_data]
        values = [item.get('count', 0) for item in competency_data]
        avg_severities = [item.get('avg_severity', 0) for item in competency_data]
        
        x = np.arange(len(names))
        width = 0.35
        
        bars = ax.bar(x, values, width, color='#0B2E4F', edgecolor='none', alpha=0.8)
        
        # رنگ‌بندی بر اساس میزان استفاده
        max_val = max(values) if values else 1
        for bar, val in zip(bars, values):
            if val >= max_val * 0.7:
                bar.set_color('#66BB6A')
            elif val >= max_val * 0.4:
                bar.set_color('#F4D35E')
            else:
                bar.set_color('#C62828')
        
        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=9, rotation=30, ha='right')
        
        if title:
            ax.set_title(ChartHelper._farsi(title), fontsize=14, fontweight='bold')
        ax.set_ylabel(ChartHelper._farsi('تعداد'), fontsize=11)
        ax.yaxis.grid(True, linestyle='--', alpha=0.3, color='#D9C36A')
        
        # نمایش میانگین شدت روی میله‌ها
        for i, (bar, sev) in enumerate(zip(bars, avg_severities)):
            if sev > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                       f"شدت: {sev}", ha='center', va='bottom', fontsize=8, color='#475569')
        
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        fig.subplots_adjust(left=0.12, right=0.96, top=0.85, bottom=0.25)
        return FigureCanvas(fig)
    
    @staticmethod
    def create_status_chart(status_data, title=None):
        """
        ایجاد نمودار وضعیت (برای مداخلات یا پیگیری‌ها)
        
        Args:
            status_data: dict با کلیدهای وضعیت و مقادیر
            title: عنوان نمودار
        
        Returns:
            FigureCanvas: شیء قابل نمایش در Qt
        """
        if not status_data or sum(status_data.values()) == 0:
            return ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        fig = Figure(figsize=(5, 4), dpi=100, facecolor='#0B2E4F')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0B2E4F')
        
        # رنگ‌های متناسب با وضعیت
        status_colors = {
            'planned': '#F4D35E',
            'in_progress': '#0B2E4F',
            'done': '#8BC34A',
            'completed': '#66BB6A',
            'cancelled': '#C62828',
            'pending': '#F4D35E',
            'continued': '#0B2E4F',
            'closed': '#D9C36A',
            'active': '#66BB6A',
            'inactive': '#D9C36A'
        }
        
        labels = [ChartHelper._farsi(str(k)) for k in status_data]
        values = list(status_data.values())
        colors = [status_colors.get(k, '#D9C36A') for k in status_data]
        
        # مرتب‌سازی بر اساس مقدار
        sorted_data = sorted(zip(labels, values, colors), key=lambda x: x[1], reverse=True)
        labels, values, colors = zip(*sorted_data) if sorted_data else ([], [], [])
        
        ax.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        
        if title:
            ax.set_title(ChartHelper._farsi(title), fontsize=14, fontweight='bold')
        
        fig.subplots_adjust(left=0.05, right=0.95, top=0.85, bottom=0.05)
        return FigureCanvas(fig)
    
    @staticmethod
    def create_grade_distribution_chart(grade_data, title=None):
        """
        ایجاد نمودار توزیع پایه‌ها
        
        Args:
            grade_data: list of dict با کلیدهای 'grade_display' و 'count'
            title: عنوان نمودار
        
        Returns:
            FigureCanvas: شیء قابل نمایش در Qt
        """
        if not grade_data:
            return ChartHelper._create_empty_chart("داده‌ای برای نمایش وجود ندارد")
        
        fig = Figure(figsize=(6, 4), dpi=100, facecolor='#0B2E4F')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0B2E4F')
        
        # مرتب‌سازی بر اساس پایه
        grade_order = {'اول': 1, 'دوم': 2, 'سوم': 3, 'چهارم': 4, 'پنجم': 5, 'ششم': 6}
        sorted_data = sorted(grade_data, key=lambda x: grade_order.get(x.get('grade_display', ''), 0))
        
        labels = [ChartHelper._farsi(item.get('grade_display', 'نامشخص')) for item in sorted_data]
        values = [item.get('count', 0) for item in sorted_data]
        percentages = [item.get('percentage', 0) for item in sorted_data]
        
        bars = ax.bar(labels, values, color='#0B2E4F', edgecolor='none', alpha=0.8)
        
        # نمایش درصد روی میله‌ها
        for bar, pct in zip(bars, percentages):
            if pct > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                       f"{pct}%", ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        if title:
            ax.set_title(ChartHelper._farsi(title), fontsize=14, fontweight='bold')
        ax.set_ylabel(ChartHelper._farsi('تعداد دانش‌آموزان'), fontsize=11)
        ax.yaxis.grid(True, linestyle='--', alpha=0.3, color='#D9C36A')
        
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        fig.subplots_adjust(left=0.1, right=0.96, top=0.85, bottom=0.12)
        return FigureCanvas(fig)
    
    @staticmethod
    def _create_empty_chart(message):
        """ایجاد نمودار خالی با پیام"""
        fig = Figure(figsize=(6, 3.5), dpi=100, facecolor='#0B2E4F')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0B2E4F')
        ax.text(0.5, 0.5, ChartHelper._farsi(message),
                ha='center', va='center', fontsize=12, color='#D9C36A')
        ax.axis('off')
        return FigureCanvas(fig)