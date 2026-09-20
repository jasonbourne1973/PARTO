"""
ابزار Inventory رابط کاربری (دور شانزدهم — بند ۲، ۳، ۱۸، ۱۹)

برای هر فایل در views/ با تحلیل ایستای AST:
  • هر QPushButton/QAction/QToolButton ساخته‌شده و اینکه `.clicked/.triggered.connect`
    دارد یا نه، و به چه handlerی وصل است؛
  • برای هر handler (به‌صورت بازگشتی روی متدهای خودِ کلاس) اینکه آیا به
    سرویس/DAL/دیتابیس/فایل/دیالوگ می‌رسد یا فقط پیام/`pass` است؛
  • سیگنال‌های سفارشی (`Signal(...)`)، emit و connect آن‌ها در کل درخت؛
  • connectهایی که داخل متدهای «بارگذاری/تازه‌سازی» انجام می‌شوند (خطر اتصال چندباره).

خروجی: جدول Markdown روی stdout (یا با --write در docs/ui_inventory_16.md).
این ابزار «قضاوت نهایی» نیست؛ نقطهٔ شروع بازبینی دستی و آزمون‌های کارکردی است.

اجرا:  python tools/ui_inventory.py [--write]
"""

import ast
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

VIEW_FILES = []
for sub in ('views', 'views/pages', 'views/dialogs', 'views/widgets'):
    d = os.path.join(ROOT, sub)
    for f in sorted(os.listdir(d)):
        if f.endswith('.py') and f != '__init__.py':
            VIEW_FILES.append(os.path.join(d, f))

BUTTON_CLASSES = {'QPushButton', 'QToolButton', 'QAction', 'QCommandLinkButton'}
SIGNAL_EVENTS = {'clicked', 'triggered', 'pressed', 'released', 'toggled'}
LOAD_METHOD_RE = re.compile(r'^(load|refresh|reload|populate|update|render|display|show|fill|rebuild|apply)_')
BACKEND_HINTS = ('service', 'dal', '_dal', 'db', 'database', 'repository', 'manager',
                 'generator', 'exporter', 'importer', 'analy', 'report', 'backup',
                 'qsettings', '.setvalue', '.sync')
UI_ONLY_CALLS = {'QMessageBox.information', 'QMessageBox.warning', 'QMessageBox.critical',
                 'QMessageBox.about', 'QMessageBox.question'}


def _name_of(node):
    """نام قابل خواندن برای یک عبارت (self.x.y → 'self.x.y')"""
    if isinstance(node, ast.Attribute):
        base = _name_of(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        return _name_of(node.func) + '()'
    if isinstance(node, ast.Subscript):
        return _name_of(node.value) + '[]'
    if isinstance(node, ast.Lambda):
        return 'lambda:' + _name_of(node.body)
    if isinstance(node, ast.Constant):
        return repr(node.value)
    return type(node).__name__


class ClassInfo:
    def __init__(self, name, node, source_lines):
        self.name = name
        self.node = node
        self.lines = source_lines
        self.methods = {n.name: n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.buttons = []        # dict(name, line, text, connected_to, handler_kind)
        self.connects = []       # dict(sender, event, target, line, in_method)
        self.signals = {}        # name -> line
        self.emits = defaultdict(list)
        self._collect()

    # -------------------------------------------------------------- collection
    def _collect(self):
        for method_name, fn in self.methods.items():
            for node in ast.walk(fn):
                # ساخت دکمه
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                    cls = _name_of(node.value.func).split('.')[-1]
                    if cls in BUTTON_CLASSES:
                        text = ''
                        if node.value.args and isinstance(node.value.args[0], ast.Constant):
                            text = str(node.value.args[0].value)
                        for tgt in node.targets:
                            self.buttons.append({
                                'var': _name_of(tgt), 'line': node.lineno, 'text': text,
                                'cls': cls, 'method': method_name, 'connected_to': None,
                                'connect_line': None,
                            })
                # connect
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'connect':
                    sig = node.func.value
                    if isinstance(sig, ast.Attribute):
                        sender = _name_of(sig.value)
                        event = sig.attr
                        target = _name_of(node.args[0]) if node.args else '?'
                        self.connects.append({'sender': sender, 'event': event, 'target': target,
                                              'line': node.lineno, 'in_method': method_name})
                # emit
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'emit':
                    self.emits[_name_of(node.func.value)].append(node.lineno)
        # سیگنال‌های سفارشی (سطح کلاس)
        for node in self.node.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and _name_of(node.value.func).split('.')[-1] == 'Signal':
                for tgt in node.targets:
                    self.signals[_name_of(tgt)] = node.lineno
        # نگاشت connect به دکمه‌ها
        by_var = defaultdict(list)
        for b in self.buttons:
            by_var[b['var']].append(b)
        for c in self.connects:
            if c['event'] in SIGNAL_EVENTS and c['sender'] in by_var:
                for b in by_var[c['sender']]:
                    if b['connected_to'] is None or b['method'] == c['in_method']:
                        b['connected_to'] = c['target']
                        b['connect_line'] = c['line']

    # -------------------------------------------------------------- analysis
    def handler_kind(self, target, depth=0, seen=None):
        """
        طبقه‌بندی handler:
          MISSING     → متدی با این نام در کلاس نیست (ممکن است در والد باشد)
          STUB        → فقط pass/docstring
          MSG_ONLY    → فقط QMessageBox (بدون هیچ عمل واقعی)
          UI_ONLY     → فقط تغییر ویجت‌ها (بدون سرویس/DAL/دیالوگ/سیگنال)
          DIALOG      → دیالوگ باز می‌کند (زنجیره در دیالوگ ادامه دارد)
          BACKEND     → به سرویس/DAL/دیتابیس/فایل می‌رسد
          SIGNAL      → سیگنال emit می‌کند (والد ادامه می‌دهد)
          NAV         → فقط ناوبری (setCurrentIndex/صفحه)
        """
        seen = seen or set()
        if target is None:
            return 'NO_CONNECT'
        if target.startswith('lambda:'):
            body = target[len('lambda:'):]
            if 'setCurrentIndex' in body or 'setCurrentWidget' in body:
                return 'NAV'
            target = body.split('(')[0]
        name = target.replace('self.', '').split('(')[0]
        if name in ('close', 'accept', 'reject', 'hide', 'show', 'exec', 'clear'):
            return 'UI_ONLY'
        fn = self.methods.get(name)
        if fn is None:
            if '.' in name:
                return 'EXTERNAL:' + name
            return 'MISSING:' + name
        if name in seen or depth > 4:
            return 'UI_ONLY'
        seen.add(name)
        body = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(getattr(s, 'value', None), ast.Constant))]
        if not body or all(isinstance(s, ast.Pass) for s in body):
            return 'STUB'
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
        call_names = [_name_of(c.func) for c in calls]
        kinds = set()
        for cn in call_names:
            low = cn.lower()
            if cn in UI_ONLY_CALLS:
                kinds.add('MSG')
            elif any(h in low for h in BACKEND_HINTS) and not low.startswith('qmessagebox'):
                kinds.add('BACKEND')
            elif low.endswith(('.exec', '.exec_', '.open', 'form()')) or 'dialog' in low:
                kinds.add('DIALOG')
            elif low.endswith('.emit'):
                kinds.add('SIGNAL')
            elif 'setcurrentindex' in low or 'setcurrentwidget' in low:
                kinds.add('NAV')
            elif cn.startswith('self.') and cn.count('.') == 1 and cn[5:] in self.methods:
                sub = self.handler_kind('self.' + cn[5:], depth + 1, seen)
                if sub in ('BACKEND', 'DIALOG', 'SIGNAL', 'NAV'):
                    kinds.add(sub)
        # سرویس‌هایی که به‌عنوان صفت خوانده می‌شوند (self.x_service.y)
        for n in ast.walk(fn):
            if isinstance(n, ast.Attribute):
                low = _name_of(n).lower()
                if any(h in low for h in ('service.', 'dal.', 'manager.', 'generator.')):
                    kinds.add('BACKEND')
        if 'BACKEND' in kinds:
            return 'BACKEND'
        if 'DIALOG' in kinds:
            return 'DIALOG'
        if 'SIGNAL' in kinds:
            return 'SIGNAL'
        if 'NAV' in kinds:
            return 'NAV'
        if kinds == {'MSG'}:
            return 'MSG_ONLY'
        return 'UI_ONLY'


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def analyze_file(path):
    src = _read(path)
    tree = ast.parse(src)
    lines = src.splitlines()
    classes = [ClassInfo(n.name, n, lines) for n in tree.body if isinstance(n, ast.ClassDef)]
    return classes


def build_report(write=False):
    out = []
    totals = defaultdict(int)
    flagged = []
    all_signals = {}     # (file, class, signal) -> {'emits': [...], 'connects': [...]}
    repeated_connects = []
    for path in VIEW_FILES:
        rel = os.path.relpath(path, ROOT)
        classes = analyze_file(path)
        if not any(c.buttons or c.connects or c.signals for c in classes):
            continue
        out.append(f"\n### `{rel}`\n")
        out.append("| کلاس | دکمه/Action | متن | خط | handler | طبقه‌بندی ایستا |")
        out.append("|---|---|---|---|---|---|")
        for c in classes:
            for b in c.buttons:
                kind = c.handler_kind(b['connected_to'])
                totals[kind.split(':')[0]] += 1
                if kind in ('NO_CONNECT', 'STUB', 'MSG_ONLY') or kind.startswith('MISSING'):
                    flagged.append((rel, c.name, b['var'], b['text'], b['line'], kind))
                out.append(f"| {c.name} | `{b['var']}` | {b['text'][:28]} | {b['line']} | "
                           f"`{(b['connected_to'] or '—')[:40]}` | {kind} |")
            for sig, line in c.signals.items():
                all_signals[(rel, c.name, sig)] = {'line': line, 'emits': c.emits.get('self.' + sig, []) + c.emits.get(sig, [])}
            for con in c.connects:
                if LOAD_METHOD_RE.match(con['in_method']) and con['event'] not in SIGNAL_EVENTS:
                    repeated_connects.append((rel, c.name, con['in_method'], con['sender'], con['event'], con['line']))
                if LOAD_METHOD_RE.match(con['in_method']) and con['event'] in SIGNAL_EVENTS and not any(
                        b['var'] == con['sender'] and b['method'] == con['in_method'] for b in c.buttons):
                    repeated_connects.append((rel, c.name, con['in_method'], con['sender'], con['event'], con['line']))

    # گیرنده‌های سیگنال‌های سفارشی در کل درخت
    all_src = {os.path.relpath(p, ROOT): _read(p) for p in VIEW_FILES}
    signal_rows = []
    for (rel, cls, sig), info in sorted(all_signals.items()):
        receivers = [r for r, s in all_src.items() if re.search(rf'\.{re.escape(sig)}\.connect\(', s)]
        signal_rows.append((rel, cls, sig, info['line'], len(info['emits']), receivers))

    header = ["# Inventory رابط کاربری — دور شانزدهم (تولید خودکار با tools/ui_inventory.py)\n",
              "طبقه‌بندی ایستا: BACKEND = به سرویس/DAL/فایل می‌رسد؛ DIALOG = دیالوگ باز می‌کند (زنجیره در دیالوگ)؛ "
              "SIGNAL = سیگنال به والد؛ NAV = ناوبری؛ UI_ONLY = فقط تغییر ویجت؛ MSG_ONLY = فقط پیام؛ "
              "STUB = pass؛ NO_CONNECT = بدون اتصال؛ MISSING = handler در کلاس نیست.\n",
              "## جمع‌بندی\n", "| طبقه | تعداد |", "|---|---|"]
    header += [f"| {k} | {v} |" for k, v in sorted(totals.items(), key=lambda kv: -kv[1])]
    header.append("\n## موارد نیازمند بازبینی دستی (NO_CONNECT / STUB / MSG_ONLY / MISSING)\n")
    header.append("| فایل | کلاس | دکمه | متن | خط | طبقه |")
    header.append("|---|---|---|---|---|---|")
    header += [f"| `{r}` | {c} | `{v}` | {t[:28]} | {ln} | {k} |" for r, c, v, t, ln, k in flagged]
    header.append("\n## سیگنال‌های سفارشی (تعریف → emit → گیرنده)\n")
    header.append("| فایل | کلاس | سیگنال | خط | تعداد emit | گیرنده‌ها |")
    header.append("|---|---|---|---|---|---|")
    header += [f"| `{r}` | {c} | `{s}` | {ln} | {e} | {', '.join(f'`{x}`' for x in recv) or '**هیچ**'} |"
               for r, c, s, ln, e, recv in signal_rows]
    header.append("\n## connect داخل متدهای بارگذاری/تازه‌سازی (خطر اتصال چندباره)\n")
    header.append("| فایل | کلاس | متد | فرستنده | رویداد | خط |")
    header.append("|---|---|---|---|---|---|")
    header += [f"| `{r}` | {c} | `{m}` | `{s}` | {e} | {ln} |" for r, c, m, s, e, ln in repeated_connects]
    header.append("\n## جدول کامل دکمه‌ها\n")
    text = "\n".join(header + out) + "\n"
    if write:
        dest = os.path.join(ROOT, 'docs', 'ui_inventory_16.md')
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"نوشته شد: {dest}")
    else:
        print(text)
    return {'totals': dict(totals), 'flagged': flagged, 'signals': signal_rows, 'repeated': repeated_connects}


if __name__ == '__main__':
    build_report(write='--write' in sys.argv)
