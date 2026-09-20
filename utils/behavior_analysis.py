"""
تحلیل رفتار بر پایهٔ «نوع رفتار ثبت‌شده» — نه شدت (بازرسی یازدهم)

اصل محتوایی که این ماژول تضمین می‌کند:

  • نقطهٔ قوت           = الگوی **تکرارشوندهٔ** رفتارهای **مثبت** مرتبط با یک شایستگی
  • زمینهٔ نیازمند توجه = الگوی **تکرارشوندهٔ** رفتارهای **منفی** مرتبط با یک شایستگی
  • رفتار خنثی به‌خودی‌خود نه قوت است و نه ضعف
  • شدت (severity) فقط **اطلاعات تکمیلی** است؛ تصمیم قوت/ضعف را نمی‌گیرد
  • یک مشاهدهٔ منفرد هرگز مبنای نتیجه‌گیری دربارهٔ دانش‌آموز نیست
  • کاهش/افزایش «تعداد مشاهدات» شاخص رشد نیست؛ فقط **حجم ثبت و پایش** است
  • جهت روند از **مسیر بین همهٔ بازه‌ها** به دست می‌آید، نه فقط از مقایسهٔ
    اولین و آخرین بازه؛ اگر تغییرات یک‌جهت نباشد، «روند غیرقطعی» است
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

# تلورانس نوسان جزئی (درصد نقطه): جابه‌جایی کمتر از این، «حرکت» شمرده نمی‌شود
MINOR_SHARE_CHANGE = 5.0

# بازه‌ای با کمتر از این تعداد مشاهده، «کم‌مشاهده» است (فقط یادداشت احتیاطی؛
# در تصمیم روند نقشی ندارد، چون تعداد مشاهدات شاخص رشد نیست)
SMALL_PERIOD_TOTAL = 3

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
    if pos_change >= MEANINGFUL_SHARE_CHANGE and neg_change <= MINOR_SHARE_CHANGE:
        return 'improving'
    if neg_change >= MEANINGFUL_SHARE_CHANGE and pos_change <= MINOR_SHARE_CHANGE:
        return 'declining'
    if (abs(pos_change) < MEANINGFUL_SHARE_CHANGE
            and abs(neg_change) < MEANINGFUL_SHARE_CHANGE):
        return 'stable'
    return 'mixed'


def _step_tendency(pos_change, neg_change):
    """
    «گرایش» یک گام، مستقل از معنادار بودن آن.

    برای اینکه تغییرهای تدریجی (هر گام زیر آستانهٔ معناداری، ولی همه
    هم‌جهت) و نوسان‌های جزئی هم دیده شوند:
      • up   : حرکت به نفع رفتار مثبت (بیش از تلورانس) بدون حرکت مخالف
      • down : حرکت به نفع رفتار منفی (بیش از تلورانس) بدون حرکت مخالف
      • flat : هر دو سهم داخل تلورانس
      • mixed: هر دو سهم هم‌زمان بیش از تلورانس جابه‌جا شده‌اند
    """
    favorable = pos_change > MINOR_SHARE_CHANGE or neg_change < -MINOR_SHARE_CHANGE
    adverse = neg_change > MINOR_SHARE_CHANGE or pos_change < -MINOR_SHARE_CHANGE
    if favorable and not adverse:
        return 'up'
    if adverse and not favorable:
        return 'down'
    if not favorable and not adverse:
        return 'flat'
    return 'mixed'


_STEP_LABELS = {
    'improving': 'تغییر به سمت رفتارهای مثبت‌تر',
    'declining': 'افزایش سهم رفتارهای منفی',
    'stable': 'ترکیب رفتارها تقریباً ثابت',
    'mixed': 'تغییر ترکیبی',
}

_MINOR_STEP_LABELS = {
    'up': 'تغییر جزئی به سمت مثبت‌تر (زیر آستانهٔ معناداری)',
    'down': 'افزایش جزئی سهم منفی (زیر آستانهٔ معناداری)',
}


def _step_label(kind, tendency):
    """برچسب گام: گام‌های زیر آستانه ولی جهت‌دار هم خوانا گزارش می‌شوند."""
    if kind == 'stable' and tendency in _MINOR_STEP_LABELS:
        return _MINOR_STEP_LABELS[tendency]
    return _STEP_LABELS[kind]


_DIRECTION_LABELS = {
    'improving': 'تغییر به سمت رفتارهای مثبت‌تر',
    'declining': 'افزایش سهم رفتارهای منفی',
    'stable': 'ترکیب رفتارها تقریباً ثابت',
    'mixed': 'تغییر ترکیبی (روند غیرقطعی)',
    'insufficient': 'دادهٔ کافی برای تحلیل روند',
}


def _fmt_share(value):
    """نمایش کوتاه درصد (بدون اعشار اضافه)."""
    if value is None:
        return '-'
    return str(int(value)) if float(value).is_integer() else str(value)


def _period_text(entry):
    """توصیف یک بازه: «مهر (۲۰٪ مثبت / ۸۰٪ منفی)»."""
    return (f"{entry['label']} ({_fmt_share(entry['positive_share'])}٪ مثبت / "
            f"{_fmt_share(entry['negative_share'])}٪ منفی)")


def _join_labels(labels, limit=3):
    labels = [str(x) for x in labels if x is not None]
    if not labels:
        return ''
    shown = labels[:limit]
    text = ' و '.join(shown)
    if len(labels) > limit:
        text += ' و …'
    return text


def _step_names(steps):
    """نام خوانای گام‌ها: «مهر←آبان»."""
    return [f"{s['from']}←{s['to']}" for s in steps]


def growth_direction(periods, min_periods=2):
    """
    جهت تغییر رفتار در طول زمان — بر اساس **ترکیب رفتارها**، نه تعداد مشاهدات.

    ===== منطق (بازرسی سیزدهم) =====
    نتیجه فقط از مقایسهٔ «اولین بازه با آخرین بازه» گرفته نمی‌شود؛ مسیر
    بین همهٔ بازه‌های دارای داده بررسی می‌شود:

      ۱) برای هر گام پیاپی (بازهٔ ۱←۲، ۲←۳، …) تغییر سهم مثبت/منفی
         محاسبه و «معنادار» بودن آن (آستانهٔ ۱۰ واحد درصد) و «گرایش»
         آن (بالا/پایین/ثابت با تلورانس ۵ واحد) تعیین می‌شود.
      ۲) برآیند ابتدا←انتها هم جداگانه محاسبه می‌شود (``overall_status``)
         ولی به‌تنهایی مبنای نتیجه نیست.
      ۳) تصمیم:
         • اگر در بازه‌های میانی هم بهبود معنادار و هم افت معنادار رخ
           داده باشد → «تغییر ترکیبی / روند غیرقطعی» (برگشت جهت).
         • اگر برآیند کلی بهبود/افت معنادار باشد و **هیچ گام معنادار
           مخالفی** در میانه نباشد → همان جهت (چه یک‌باره، چه تدریجی
           با گام‌های کوچکِ هم‌جهت).
         • اگر برآیند کلی بهبود/افت باشد ولی یک گام معنادار مخالف در
           میانه ثبت شده باشد → «روند غیرقطعی»؛ چون تغییرات یک‌جهت نیست.
         • اگر برآیند کلی «ثابت» باشد ولی در میانه تغییر معناداری رخ
           داده و برگشته باشد → «روند غیرقطعی»؛ نه «ثابت».
         • اگر نه برآیند و نه هیچ گامی تغییر معنادار نداشته باشد → «ثابت».
      ۴) تعداد مشاهدات همچنان فقط «حجم ثبت و پایش» است و در هیچ‌یک از
         تصمیم‌های بالا نقشی ندارد؛ فقط اگر بازه‌ای خیلی کم‌مشاهده باشد،
         یک یادداشت احتیاطی به خروجی اضافه می‌شود.

    Args:
        periods: فهرست زمانی‌مرتب‌شده از دیکشنری‌های
                 {label, positive, negative, neutral, total}

    Returns:
        dict با کلیدهای status ('improving'|'declining'|'stable'|'mixed'|
        'insufficient'), label, message, share_first/share_last،
        overall_status (برآیند ابتدا/انتها)، steps (جزئیات گام‌به‌گام)،
        path (سهم هر بازه)، path_text (مسیر خوانا)، turning_points
        (بازه‌های برگشت جهت)، unanimous (آیا تغییرات یک‌جهت است؟)،
        volume_note و caution_notes.
    """
    usable = [p for p in (periods or []) if (p.get('total') or 0) > 0]
    if len(usable) < min_periods:
        return {
            'status': 'insufficient',
            'label': _DIRECTION_LABELS['insufficient'],
            'message': ("برای تحلیل روند، دست‌کم دو بازهٔ زمانی با مشاهدهٔ "
                        "ثبت‌شده لازم است."),
            'share_first': None,
            'share_last': None,
            'positive_change': 0.0,
            'negative_change': 0.0,
            'overall_status': 'insufficient',
            'overall_label': _DIRECTION_LABELS['insufficient'],
            'periods_with_data': len(usable),
            'steps': [],
            'path': [],
            'path_text': '',
            'turning_points': [],
            'unanimous': True,
            'reason': 'insufficient',
            'caution_notes': [],
            'volume_note': _volume_note(
                usable[0].get('total', 0) if usable else 0, 0),
        }

    period_shares = [
        shares({'positive': p.get('positive', 0),
                'negative': p.get('negative', 0),
                'neutral': p.get('neutral', 0),
                'total': p.get('total', 0)})
        for p in usable
    ]
    path = [{
        'label': p.get('label'),
        'positive_share': s['positive'],
        'negative_share': s['negative'],
        'neutral_share': s['neutral'],
        'total': p.get('total', 0),
    } for p, s in zip(usable, period_shares)]

    steps = []
    for index in range(1, len(usable)):
        pos_change = (period_shares[index]['positive']
                      - period_shares[index - 1]['positive'])
        neg_change = (period_shares[index]['negative']
                      - period_shares[index - 1]['negative'])
        kind = _classify_share_step(pos_change, neg_change)
        tendency = _step_tendency(pos_change, neg_change)
        steps.append({
            'from': usable[index - 1].get('label'),
            'to': usable[index].get('label'),
            'status': kind,
            'label': _step_label(kind, tendency),
            'tendency': tendency,
            'meaningful': kind in ('improving', 'declining', 'mixed'),
            'positive_change': round(pos_change, 1),
            'negative_change': round(neg_change, 1),
        })

    first_share = period_shares[0]
    last_share = period_shares[-1]
    pos_change = last_share['positive'] - first_share['positive']
    neg_change = last_share['negative'] - first_share['negative']
    overall_status = _classify_share_step(pos_change, neg_change)

    up_steps = [s for s in steps if s['status'] == 'improving']
    down_steps = [s for s in steps if s['status'] == 'declining']
    both_steps = [s for s in steps if s['status'] == 'mixed']

    # بازه‌هایی که جهتِ گام‌های معنادار در آن‌ها برمی‌گردد
    turning_points = []
    previous = None
    for step in steps:
        if step['status'] not in ('improving', 'declining'):
            continue
        if previous and previous['status'] != step['status']:
            turning_points.append(step['from'])
        previous = step

    if up_steps and down_steps:
        status, reason = 'mixed', 'reversal'
    elif overall_status == 'improving':
        status, reason = ('mixed', 'counter_step') if down_steps else ('improving', 'consistent')
    elif overall_status == 'declining':
        status, reason = ('mixed', 'counter_step') if up_steps else ('declining', 'consistent')
    elif overall_status == 'stable':
        if up_steps or down_steps:
            status, reason = 'mixed', 'returned'
        elif both_steps:
            status, reason = 'mixed', 'both_shares'
        else:
            status, reason = 'stable', 'consistent'
    else:
        status, reason = 'mixed', 'both_shares'

    unanimous = status != 'mixed'

    # نوسان‌های جزئی مخالف جهت (زیر آستانهٔ معناداری) فقط گزارش می‌شوند
    counter_tendency = 'down' if status == 'improving' else 'up' if status == 'declining' else None
    minor_counter = [s for s in steps
                     if counter_tendency and s['tendency'] == counter_tendency
                     and not s['meaningful']]

    gradual = status in ('improving', 'declining') and not up_steps and not down_steps

    caution_notes = []
    small = [p for p in path if (p['total'] or 0) < SMALL_PERIOD_TOTAL]
    if small:
        caution_notes.append(
            f"حجم ثبت در {len(small)} بازه کمتر از {SMALL_PERIOD_TOTAL} مشاهده است "
            f"({_join_labels([p['label'] for p in small])})؛ در چنین بازه‌هایی سهم "
            "رفتارها با یک مشاهده هم جابه‌جا می‌شود و باید با احتیاط خوانده شود.")

    path_parts = [_period_text(path[0])]
    for step, entry in zip(steps, path[1:]):
        path_parts.append(f"{_period_text(entry)} [{step['label']}]")
    path_text = ' ← '.join(path_parts)

    first_pos = _fmt_share(first_share['positive'])
    last_pos = _fmt_share(last_share['positive'])
    first_neg = _fmt_share(first_share['negative'])
    last_neg = _fmt_share(last_share['negative'])

    if len(steps) == 1:
        span_text = "بین این دو بازه"
    else:
        span_text = f"در طول {len(steps)} گام پیاپی (شامل بازه‌های میانی)"

    if status == 'improving':
        message = (f"سهم رفتارهای مثبت از {first_pos}٪ در «{path[0]['label']}» به "
                   f"{last_pos}٪ در «{path[-1]['label']}» رسیده و {span_text} افت "
                   "معناداری ثبت نشده است"
                   + ("؛ این تغییر تدریجی و در چند بازهٔ پیاپی رخ داده است" if gradual else "")
                   + ". این نتیجه بر پایهٔ نوع رفتارهای ثبت‌شده است، نه تعداد مشاهدات.")
    elif status == 'declining':
        message = (f"سهم رفتارهای منفی از {first_neg}٪ در «{path[0]['label']}» به "
                   f"{last_neg}٪ در «{path[-1]['label']}» رسیده و {span_text} بهبود "
                   "معناداری ثبت نشده است"
                   + ("؛ این تغییر تدریجی و در چند بازهٔ پیاپی رخ داده است" if gradual else "")
                   + ". بررسی و حمایت بیشتر پیشنهاد می‌شود؛ این گزارش، تشخیص نیست.")
    elif status == 'stable':
        message = ("ترکیب رفتارهای مثبت و منفی نه در برآیند ابتدا/انتها و نه در "
                   "هیچ‌یک از بازه‌های میانی تغییر معناداری نداشته است.")
    elif reason == 'reversal':
        message = (f"تغییر رفتارها یک‌جهت نیست: تغییر به سمت مثبت‌تر در گام "
                   f"{_join_labels(_step_names(up_steps))} و "
                   f"افزایش سهم منفی در گام "
                   f"{_join_labels(_step_names(down_steps))} "
                   "ثبت شده است. بنابراین روند «غیرقطعی» گزارش می‌شود و برآیند "
                   f"ابتدا/انتها ({_DIRECTION_LABELS[overall_status]}) به‌تنهایی مبنای "
                   "نتیجه قرار نگرفته است؛ جمع‌بندی دقیق‌تر به مشاهدهٔ بیشتر نیاز دارد.")
    elif reason == 'counter_step':
        opposite = down_steps if overall_status == 'improving' else up_steps
        message = (f"برآیند ابتدا/انتها «{_DIRECTION_LABELS[overall_status]}» است، اما در "
                   f"گام {_join_labels(_step_names(opposite))} "
                   "تغییر معناداری در جهت مخالف ثبت شده است. چون تغییرات یک‌جهت "
                   "نیست، روند «غیرقطعی» گزارش می‌شود، نه صرفاً برآیند ابتدا و انتها.")
    elif reason == 'returned':
        moved = up_steps + down_steps
        message = (f"در گام {_join_labels(_step_names(moved))} "
                   f"تغییر معناداری ({_join_labels([s['label'] for s in moved], 2)}) رخ "
                   "داده، اما تا آخرین بازه، ترکیب رفتارها به وضعیتی نزدیک به ابتدا "
                   "برگشته است. این تغییرِ میانی نادیده گرفته نمی‌شود و روند "
                   "«غیرقطعی» گزارش می‌شود، نه «ثابت».")
    else:
        message = ("سهم رفتارهای مثبت و منفی هم‌زمان جابه‌جا شده‌اند (معمولاً با کم "
                   "شدن سهم رفتار خنثی)؛ نتیجه‌گیری جهت‌دار ممکن نیست و روند "
                   "«ترکیبی» گزارش می‌شود.")

    if minor_counter:
        message += (f" نوسان جزئی مخالف جهت (زیر آستانهٔ معناداری) در گام "
                    f"{_join_labels(_step_names(minor_counter))} "
                    "دیده می‌شود.")

    return {
        'status': status,
        'label': _DIRECTION_LABELS[status],
        'message': message,
        'share_first': first_share,
        'share_last': last_share,
        'positive_change': round(pos_change, 1),
        'negative_change': round(neg_change, 1),
        'overall_status': overall_status,
        'overall_label': _DIRECTION_LABELS[overall_status],
        'periods_with_data': len(usable),
        'steps': steps,
        'path': path,
        'path_text': path_text,
        'turning_points': turning_points,
        'unanimous': unanimous,
        'reason': reason,
        'caution_notes': caution_notes,
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
