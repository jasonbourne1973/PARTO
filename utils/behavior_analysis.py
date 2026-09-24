"""
تحلیل رفتار بر پایهٔ «نوع رفتار ثبت‌شده» — نه شدت (بازرسی یازدهم)

اصل محتوایی که این ماژول تضمین می‌کند:

  • نقطهٔ قوت           = الگوی **تکرارشوندهٔ** رفتارهای **مثبت** مرتبط با یک شایستگی
  • زمینهٔ نیازمند توجه = الگوی **تکرارشوندهٔ** رفتارهای **منفی** مرتبط با یک شایستگی
  • رفتار خنثی به‌خودی‌خود نه قوت است و نه ضعف
  • شدت (severity) فقط **اطلاعات تکمیلی** است؛ تصمیم قوت/ضعف را نمی‌گیرد
  • یک مشاهدهٔ منفرد هرگز مبنای نتیجه‌گیری دربارهٔ دانش‌آموز نیست
  • کاهش/افزایش «تعداد مشاهدات» شاخص رشد نیست؛ فقط **حجم ثبت و پایش** است
  • دانش‌آموز فقط با **خودش در طول زمان** مقایسه می‌شود

هیچ تشخیص روان‌شناختی یا برچسبی در این ماژول تولید نمی‌شود؛ خروجی‌ها
همیشه به «رفتارهای ثبت‌شده» و شناسهٔ آن‌ها قابل ردیابی‌اند.
"""

from collections import defaultdict

# حداقل تکرار برای اینکه یک الگو «تکرارشونده» شمرده شود
MIN_PATTERN_COUNT = 2

# سهم لازم از یک نوع رفتار تا الگو «غالب» شناخته شود
DOMINANCE_RATIO = 0.6

# حداقل تعداد مشاهده برای تحلیل روند
MIN_OBSERVATIONS_FOR_TREND = 3

# حداقل اختلاف سهم (درصد نقطه) برای اینکه تغییر «معنادار» شمرده شود
MEANINGFUL_SHARE_CHANGE = 10.0

PATTERN_STRENGTH = 'strength'
PATTERN_NEEDS_ATTENTION = 'needs_attention'
PATTERN_MIXED = 'mixed'
PATTERN_INSUFFICIENT = 'insufficient'

# نگاشت نوع الگو به کلیدهای خروجی گروه‌بندی‌شده
PATTERN_BUCKETS = {
    PATTERN_STRENGTH: 'strengths',
    PATTERN_NEEDS_ATTENTION: 'needs_attention',
    PATTERN_MIXED: 'mixed',
    PATTERN_INSUFFICIENT: 'insufficient',
}

# برچسب‌های محتاطانه (بدون تشخیص/برچسب)
PATTERN_LABELS = {
    PATTERN_STRENGTH: "الگوی تکرارشوندهٔ رفتار مثبت",
    PATTERN_NEEDS_ATTENTION: "الگوی تکرارشوندهٔ رفتار منفی (نیازمند توجه)",
    PATTERN_MIXED: "الگوی ترکیبی رفتارها",
    PATTERN_INSUFFICIENT: "دادهٔ کافی برای تحلیل الگو",
}

# توضیح هر الگو با لحن غیرتشخیصی و قابل ردیابی
PATTERN_DESCRIPTIONS = {
    PATTERN_STRENGTH: (
        "در رفتارهای ثبت‌شدهٔ این زمینه، رفتار مثبت به‌صورت تکرارشونده "
        "مشاهده شده است؛ این الگو به‌عنوان «توانمندی» گزارش می‌شود."
    ),
    PATTERN_NEEDS_ATTENTION: (
        "در رفتارهای ثبت‌شدهٔ این زمینه، رفتار منفی به‌صورت تکرارشونده "
        "مشاهده شده است؛ این الگو به‌عنوان «زمینهٔ نیازمند توجه» گزارش "
        "می‌شود و به‌معنای تشخیص یا برچسب نیست."
    ),
    PATTERN_MIXED: (
        "رفتارهای ثبت‌شده در این زمینه ترکیبی از مثبت و منفی است؛ "
        "نتیجه‌گیری قطعی نیازمند مشاهدهٔ بیشتر است."
    ),
    PATTERN_INSUFFICIENT: (
        "تعداد رفتارهای ثبت‌شده برای نتیجه‌گیری کافی نیست؛ ثبت مشاهدهٔ "
        "بیشتر به تحلیل دقیق‌تر کمک می‌کند."
    ),
}


def count_behaviors(observations):
    """شمارش رفتارهای مثبت/منفی/خنثی بر اساس نوع رفتار ثبت‌شده."""
    positive = negative = neutral = 0
    for obs in observations or []:
        btype = getattr(obs, 'behavior_type', None)
        if btype == "مثبت":
            positive += 1
        elif btype == "منفی":
            negative += 1
        else:
            neutral += 1
    return {
        'positive': positive,
        'negative': negative,
        'neutral': neutral,
        'total': positive + negative + neutral,
    }


def shares(counts):
    """سهم هر نوع رفتار از کل (درصد)."""
    total = counts.get('total', 0) or 0
    if total <= 0:
        return {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}
    return {
        'positive': round(counts.get('positive', 0) / total * 100, 1),
        'negative': round(counts.get('negative', 0) / total * 100, 1),
        'neutral': round(counts.get('neutral', 0) / total * 100, 1),
    }


def classify_pattern(positive, negative, neutral=0, total=None,
                     min_count=MIN_PATTERN_COUNT):
    """
    تعیین الگوی رفتاری یک زمینه/شایستگی **بر اساس نوع رفتار**.

    شدت در این تابع هیچ نقشی ندارد. یک مشاهدهٔ منفرد (کمتر از
    ``min_count``) هم هرگز نتیجه نمی‌دهد.

    Returns:
        یکی از PATTERN_STRENGTH / PATTERN_NEEDS_ATTENTION /
        PATTERN_MIXED / PATTERN_INSUFFICIENT
    """
    if total is None:
        total = (positive or 0) + (negative or 0) + (neutral or 0)
    if total <= 0:
        return PATTERN_INSUFFICIENT

    positive = positive or 0
    negative = negative or 0

    pos_ratio = positive / total
    neg_ratio = negative / total

    strength = positive >= min_count and pos_ratio >= DOMINANCE_RATIO and positive > negative
    needs_attention = negative >= min_count and neg_ratio >= DOMINANCE_RATIO and negative > positive

    if strength and needs_attention:
        # از نظر ریاضی با هم رخ نمی‌دهد، ولی برای احتیاط:
        return PATTERN_MIXED
    if strength:
        return PATTERN_STRENGTH
    if needs_attention:
        return PATTERN_NEEDS_ATTENTION
    if positive or negative:
        return PATTERN_MIXED
    return PATTERN_INSUFFICIENT


def pattern_label(kind):
    """برچسب فارسی محتاطانه برای نوع الگو."""
    return PATTERN_LABELS.get(kind, PATTERN_LABELS[PATTERN_INSUFFICIENT])


def pattern_description(kind):
    """توضیح فارسی غیرتشخیصی برای نوع الگو."""
    return PATTERN_DESCRIPTIONS.get(kind, PATTERN_DESCRIPTIONS[PATTERN_INSUFFICIENT])


def summarize_by_competency(observations, name_of, min_count=MIN_PATTERN_COUNT,
                            examples_limit=2, example_length=60):
    """
    تحلیل الگوهای رفتاری گروه‌بندی‌شده بر اساس شایستگی.

    Args:
        observations: فهرست مشاهدات
        name_of: تابع/دیکشنری تبدیل شناسهٔ شایستگی به نام آن
        min_count: حداقل تکرار برای الگوی «تکرارشونده»

    Returns:
        dict: {
            'strengths': [...], 'needs_attention': [...],
            'mixed': [...], 'insufficient': [...],
            'all': [...]
        }
        هر آیتم شامل شمارش رفتارها، سهم‌ها، شدت میانگین (**تکمیلی**)،
        شناسهٔ مشاهدات و نمونهٔ رفتارهای ثبت‌شده است.
    """
    groups = defaultdict(list)
    for obs in observations or []:
        comp_id = getattr(obs, 'competency_id', None)
        if comp_id is None:
            continue
        groups[comp_id].append(obs)

    def _name(comp_id):
        return name_of(comp_id) if callable(name_of) else name_of.get(comp_id)

    result = {'strengths': [], 'needs_attention': [], 'mixed': [],
              'insufficient': [], 'all': []}

    for comp_id, items in groups.items():
        counts = count_behaviors(items)
        kind = classify_pattern(counts['positive'], counts['negative'],
                                counts['neutral'], counts['total'], min_count)
        severities = [getattr(o, 'severity', None) or 1 for o in items]
        examples = []
        for obs in items:
            text = (getattr(obs, 'behavior', '') or '').strip()
            if text and text not in examples and len(examples) < examples_limit:
                examples.append(text[:example_length])

        entry = {
            'competency_id': comp_id,
            'competency': _name(comp_id) or f"شایستگی {comp_id}",
            'pattern': kind,
            'pattern_label': pattern_label(kind),
            'pattern_note': pattern_description(kind),
            'count': counts['total'],
            'positive': counts['positive'],
            'negative': counts['negative'],
            'neutral': counts['neutral'],
            'positive_share': shares(counts)['positive'],
            'negative_share': shares(counts)['negative'],
            # شدت فقط اطلاعات تکمیلی است و در قوت/ضعف نقشی ندارد
            'avg_severity': round(sum(severities) / len(severities), 1) if severities else 0,
            'severity_is_auxiliary': True,
            'observation_ids': [getattr(o, 'id', None) for o in items],
            'examples': examples,
        }
        result['all'].append(entry)
        result[PATTERN_BUCKETS.get(kind, 'insufficient')].append(entry)

    # مرتب‌سازی: الگوهای پرتکرارتر اول (بر اساس تعداد رفتارهای مربوطه)
    for key in ('strengths', 'needs_attention', 'mixed', 'insufficient', 'all'):
        result[key].sort(key=lambda x: (x['count'], x['positive'] + x['negative']),
                         reverse=True)

    return result


def _classify_share_step(pos_change, neg_change):
    """
    دسته‌بندی «یک گام» تغییر ترکیب رفتار (بین دو بازهٔ پیاپی).

    آستانه‌ها دقیقاً همان منطق قبلی جهت روند است:
      • بهبود: افزایش معنادار سهم مثبت، بدون افزایش محسوس سهم منفی
      • افت: افزایش معنادار سهم منفی، بدون افزایش محسوس سهم مثبت
      • ثابت: هیچ‌کدام تغییر معنادار ندارند
      • ترکیبی: در غیر این صورت (تغییرها یک‌جهت نیستند)

    تعداد مشاهدات در این تصمیم هیچ نقشی ندارد.
    """
    if pos_change >= MEANINGFUL_SHARE_CHANGE and neg_change <= 5:
        return 'improving'
    if neg_change >= MEANINGFUL_SHARE_CHANGE and pos_change <= 5:
        return 'declining'
    if (abs(pos_change) < MEANINGFUL_SHARE_CHANGE
            and abs(neg_change) < MEANINGFUL_SHARE_CHANGE):
        return 'stable'
    return 'mixed'


_STEP_LABELS = {
    'improving': 'تغییر به سمت رفتارهای مثبت‌تر',
    'declining': 'افزایش سهم رفتارهای منفی',
    'stable': 'ترکیب رفتارها تقریباً ثابت',
    'mixed': 'تغییر ترکیبی',
}


def growth_direction(periods, min_periods=2):
    """
    جهت تغییر رفتار در طول زمان — بر اساس **ترکیب رفتارها**، نه تعداد مشاهدات.

    ===== اصلاح (بازرسی دوازدهم) =====
    نسخهٔ قبلی فقط **اولین بازهٔ دارای داده** را با **آخرین بازه**
    مقایسه می‌کرد؛ یعنی اگر در بازه‌های میانی تغییر مهمی رخ داده و
    بعد برگشته بود، نادیده گرفته می‌شد. حالا **همهٔ گام‌های پیاپی**
    (بازهٔ ۱←۲، ۲←۳، ...) جداگانه دسته‌بندی می‌شوند:
      • اگر همهٔ گام‌ها یک‌جهت باشند (بهبود/افت/ثبات)، همان جهت
        گزارش می‌شود؛
      • اگر گام‌ها یک‌جهت نباشند، نتیجه «تغییر ترکیبی» (روند
        غیرقطعی) اعلام می‌شود، نه برآیند ابتدا و انتها.
    تعداد مشاهدات همچنان فقط «حجم ثبت و پایش» است و در تصمیم
    هیچ نقشی ندارد.

    Args:
        periods: فهرست زمانی‌مرتب‌شده از دیکشنری‌های
                 {label, positive, negative, neutral, total}

    Returns:
        dict با کلیدهای status ('improving'|'declining'|'stable'|'mixed'|
        'insufficient'), label, message, share_first/share_last و
        volume_note (حجم ثبت، نه رشد)؛ به‌علاوهٔ 'steps' (جزئیات
        گام‌به‌گام) و 'unanimous' (آیا همهٔ گام‌ها یک‌جهت‌اند؟).
    """
    usable = [p for p in (periods or []) if (p.get('total') or 0) > 0]
    if len(usable) < min_periods:
        return {
            'status': 'insufficient',
            'label': 'دادهٔ کافی برای تحلیل روند',
            'message': ("برای تحلیل روند، دست‌کم دو بازهٔ زمانی با مشاهدهٔ "
                        "ثبت‌شده لازم است."),
            'share_first': None,
            'share_last': None,
            'steps': [],
            'unanimous': True,
            'volume_note': _volume_note(len(usable), 0),
        }

    period_shares = [
        shares({'positive': p.get('positive', 0),
                'negative': p.get('negative', 0),
                'neutral': p.get('neutral', 0),
                'total': p.get('total', 0)})
        for p in usable
    ]

    steps = []
    for index in range(1, len(usable)):
        pos_change = (period_shares[index]['positive']
                      - period_shares[index - 1]['positive'])
        neg_change = (period_shares[index]['negative']
                      - period_shares[index - 1]['negative'])
        steps.append({
            'from': usable[index - 1].get('label'),
            'to': usable[index].get('label'),
            'status': _classify_share_step(pos_change, neg_change),
            'positive_change': round(pos_change, 1),
            'negative_change': round(neg_change, 1),
        })

    first_share = period_shares[0]
    last_share = period_shares[-1]
    pos_change = last_share['positive'] - first_share['positive']
    neg_change = last_share['negative'] - first_share['negative']

    step_statuses = {s['status'] for s in steps}
    # گام «ثابت» خنثی است: جهت کلی را عوض نمی‌کند.
    directed = step_statuses - {'stable'}
    unanimous = len(directed) <= 1

    if not directed:
        status = 'stable'
        label = 'ترکیب رفتارها تقریباً ثابت'
        message = ("ترکیب رفتارهای مثبت و منفی در بازه‌های ثبت‌شده تغییر "
                   "معناداری نداشته است.")
    elif directed == {'improving'}:
        status = 'improving'
        label = 'تغییر به سمت رفتارهای مثبت‌تر'
        message = ("سهم رفتارهای مثبت در طول بازه‌های ثبت‌شده به‌صورت "
                   "یک‌جهت بیشتر شده است؛ این تغییر بر پایهٔ **نوع رفتارهای "
                   "ثبت‌شده** گزارش می‌شود، نه بر پایهٔ تعداد مشاهدات.")
    elif directed == {'declining'}:
        status = 'declining'
        label = 'افزایش سهم رفتارهای منفی'
        message = ("سهم رفتارهای منفی در طول بازه‌های ثبت‌شده به‌صورت "
                   "یک‌جهت بیشتر شده است؛ بررسی و حمایت بیشتر پیشنهاد "
                   "می‌شود. این گزارش، تشخیص نیست.")
    else:
        status = 'mixed'
        label = 'تغییر ترکیبی'
        message = ("تغییر رفتارها در بازه‌های ثبت‌شده یک‌جهت نیست؛ یعنی در "
                   "بعضی بازه‌های میانی بهبود و در بعضی دیگر افت دیده "
                   "می‌شود. پس روند، «غیرقطعی» گزارش می‌شود و برای "
                   "جمع‌بندی دقیق‌تر به مشاهدهٔ بیشتر نیاز است.")

    return {
        'status': status,
        'label': label,
        'message': message,
        'share_first': first_share,
        'share_last': last_share,
        'positive_change': round(pos_change, 1),
        'negative_change': round(neg_change, 1),
        'periods_with_data': len(usable),
        'steps': steps,
        'unanimous': unanimous,
        'volume_note': _volume_note(usable[0].get('total', 0),
                                    usable[-1].get('total', 0)),
    }


def _volume_note(first_total, last_total):
    """یادآوری اینکه تعداد مشاهدات «حجم ثبت و پایش» است، نه شاخص رشد."""
    if not first_total and not last_total:
        return "حجم ثبت مشاهده: داده‌ای برای مقایسه وجود ندارد."
    if last_total > first_total:
        return (f"حجم ثبت مشاهده از {first_total} به {last_total} افزایش "
                "یافته است؛ این عدد میزان ثبت و پایش را نشان می‌دهد، نه "
                "بهبود یا بدتر شدن رفتار.")
    if last_total < first_total:
        return (f"حجم ثبت مشاهده از {first_total} به {last_total} کاهش "
                "یافته است؛ کاهش تعداد مشاهدات به‌معنای بهبود رفتار نیست و "
                "ممکن است فقط ثبت کمتر باشد.")
    return (f"حجم ثبت مشاهده در دو بازه برابر است ({last_total} مورد)؛ این "
            "عدد شاخص رشد نیست.")


def observations_volume_note(counts):
    """یادداشت حجم ثبت برای یک مجموعهٔ مشاهده."""
    total = (counts or {}).get('total', 0)
    if total == 0:
        return "هیچ مشاهده‌ای ثبت نشده است؛ ثبت مشاهده مبنای هر تحلیل است."
    return (f"تعداد مشاهدات ثبت‌شده: {total} — این عدد «حجم ثبت و پایش» "
            "است و به‌تنهایی شاخص پیشرفت یا پسرفت نیست.")
