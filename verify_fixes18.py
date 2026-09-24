"""
راستی‌آزمایی دور هجدهم — مرحلهٔ ۲: پیوست‌ها (BUG-ATT-04/05/06 + رگرسیون)

بخش‌ها:
  A) بازیابی پیوست حذف‌شده با «صفحهٔ واقعی» دیالوگ (آفلاین):
     چک‌باکس «نمایش حذف‌شده‌ها»، انتخاب ردیف حذف‌شده، دکمهٔ ↩️،
     راستی‌آزمایی فایل فیزیکی پیش از بازیابی (BUG-ATT-05)، برهم‌کنش
     سقف ۲۰ با بازیابی (BUG-ATT-06)، و رگرسیون حذف منطقی (فایل می‌ماند).

نکتهٔ محیط: اجرای واقعی Qt با کتابخانه‌های جانشین (qtstub) و
QT_QPA_PLATFORM=offscreen. کلیک واقعی موس، QFileDialog و بازکردن فایل
خارجی همچنان NOT_TESTED - GUI EXECUTION REQUIRED هستند.

اجرا:
  LD_LIBRARY_PATH=/home/user/qtstub/lib QT_QPA_PLATFORM=offscreen \
      python3 verify_fixes18.py
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = 0
FAIL = 0
FAILURES = []


def check(section, name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ [{section}] {name}")
    else:
        FAIL += 1
        FAILURES.append(f"[{section}] {name} {detail}")
        print(f"  ❌ [{section}] {name}  {detail}")


TMP = tempfile.mkdtemp(prefix="round18_verify_")

# ============================================================
# دیتابیس و پوشهٔ پیوست موقت (هیچ دست‌زدنی به دادهٔ واقعی نمی‌شود)
# ============================================================
TEST_DB = os.path.join(TMP, "partow.db")
ATT_DIR = os.path.join(TMP, "attachments")
os.makedirs(ATT_DIR, exist_ok=True)

import config.settings as settings
import database.connection as dbc

settings.DB_PATH = TEST_DB
dbc.DB_PATH = TEST_DB
settings.ATTACHMENTS_DIR = ATT_DIR
dbc.DatabaseConnection._instance = None
dbc.DatabaseConnection._connection = None
dbc.DatabaseConnection._initialized = False

with contextlib.redirect_stdout(io.StringIO()):
    db = dbc.DatabaseConnection()
    conn = db.get_connection(user_id=1)

# ماژول‌هایی که ATTACHMENTS_DIR را در سطح ماژول نگه می‌دارند
import dal.attachment_dal as attachment_dal_mod
import services.attachment_service as attachment_service_mod

attachment_dal_mod.ATTACHMENTS_DIR = ATT_DIR
attachment_service_mod.ATTACHMENTS_DIR = ATT_DIR

from services.attachment_service import AttachmentService
from dal.attachment_dal import AttachmentDAL

SERVICE = AttachmentService()

from PySide6.QtWidgets import QApplication, QMessageBox

app = QApplication.instance() or QApplication(sys.argv)

# --- رهگیری پیام‌ها (بدون جلوهٔ واقعی؛ محتوا سنجیده می‌شود) ---
messages = []
real_info = QMessageBox.information
real_crit = QMessageBox.critical
real_warn = QMessageBox.warning
real_question = QMessageBox.question

QMessageBox.information = staticmethod(
    lambda *a, **k: messages.append(("info", str(a[2])))
    or QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(
    lambda *a, **k: messages.append(("crit", str(a[2])))
    or QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(
    lambda *a, **k: messages.append(("warn", str(a[2])))
    or QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(
    lambda *a, **k: QMessageBox.StandardButton.Yes)

from views.dialogs.attachment_dialog import AttachmentDialog

ENTITY = ("observation", 42)


def make_attachment(name, content, entity=ENTITY):
    return SERVICE.upload_attachment(
        entity[0], entity[1], content, name, user_id=None)


def active_count(entity=ENTITY):
    return SERVICE.attachment_dal.get_count_by_entity(entity[0], entity[1])


def is_deleted(attachment_id):
    row = conn.execute(
        "SELECT is_deleted FROM attachments WHERE id = ?",
        (attachment_id,)).fetchone()
    return row is None or row["is_deleted"] == 1


print()
print("=" * 76)
print("بخش A: مرحلهٔ ۲ — بازیابی پیوست و راستی‌آزمایی فایل فیزیکی (بند ۱۱)")
print("=" * 76)

# ---------- A1: دیالوگ فعال‌ها؛ چک‌باکس موجود؛ دکمهٔ بازیابی پنهان ----------
a = make_attachment("active.txt", b"active content")
dlg = AttachmentDialog(ENTITY[0], ENTITY[1])
check("A", "A1: دیالوگ باز شد و پیوست فعال را نشان داد",
      dlg.file_list.count() == 1 and active_count() == 1,
      f"count={dlg.file_list.count()}")
check("A", "A1: چک‌باکس «نمایش حذف‌شده‌ها» در دیالوگ هست",
      hasattr(dlg, "show_deleted_check") and dlg.show_deleted_check is not None)
check("A", "A1: دکمهٔ بازیابی در حالت عادی پنهان است",
      dlg.restore_btn.isHidden() and not dlg.showing_deleted)
check("A", "A1: دکمهٔ افزودن فعال است",
      dlg.add_btn.isEnabled())
dlg.close()
dlg.deleteLater()

# ---------- A2: حذف منطقی → چک‌باکس → فهرست حذف‌شده‌ها ----------
deleted_att = make_attachment("victim.txt", b"victim content")
SERVICE.delete_attachment(deleted_att.id)
check("A", "A2: حذف منطقی: فایل فیزیکی سر جای خودش ماند",
      os.path.exists(deleted_att.file_path))

dlg = AttachmentDialog(ENTITY[0], ENTITY[1])
dlg.show_deleted_check.setChecked(True)   # سیگنال toggled → toggle_show_deleted
check("A", "A2: حالت حذف‌شده‌ها فعال شد و افزودن قفل شد",
      dlg.showing_deleted and not dlg.add_btn.isEnabled())
check("A", "A2: پیوست حذف‌شده با برچسب «(حذف‌شده)» در فهرست است",
      dlg.file_list.count() == 1
      and "(حذف‌شده)" in dlg.file_list.item(0).text())
check("A", "A2: دکمهٔ بازیابی در این حالت به نمایش درمی‌آید",
      not dlg.restore_btn.isHidden())

# ---------- A3: انتخاب ردیف حذف‌شده → فقط بازیابی ----------
dlg.file_list.setCurrentRow(0)
# کلیک واقعی در آفلاین ممکن نیست؛ همان هندلرِ itemClicked صدا زده می‌شود
dlg.on_file_selected(dlg.file_list.item(0))
check("A", "A3: انتخاب حذف‌شده → فقط «بازیابی» فعال است",
      dlg.restore_btn.isEnabled() and not dlg.open_btn.isEnabled()
      and not dlg.download_btn.isEnabled() and not dlg.delete_btn.isEnabled())

# ---------- A4: بازیابی واقعی از مسیر UI ----------
messages.clear()
dlg.restore_selected()

check("A", "A4: بازیابی از مسیر UI روی DB اثر واقعی گذاشت",
      not is_deleted(deleted_att.id), f"is_deleted={is_deleted(deleted_att.id)}")
check("A", "A4: فهرست خودکار به حالت فعال برگشت و پیوست دیده می‌شود",
      not dlg.showing_deleted and dlg.file_list.count() == 2)
check("A", "A4: پیام موفقیت صادر شد",
      any(kind == "info" for kind, _ in messages), f"messages={messages}")
check("A", "A4: دیالوگ به فهرست فعال برگشت (چک‌باکس برداشته شد)",
      not dlg.showing_deleted and not dlg.show_deleted_check.isChecked())
dlg.close()
dlg.deleteLater()

# ---------- A5: BUG-ATT-05 — فایل فیزیکی گم‌شده: شکست صریح، نه موفقیت خاموش ----------
ghost = make_attachment("ghost.txt", b"i will vanish")
SERVICE.delete_attachment(ghost.id)
os.remove(ghost.file_path)  # «پاک‌شدن دستی» فایل

dlg = AttachmentDialog(ENTITY[0], ENTITY[1])
dlg.show_deleted_check.setChecked(True)
ids = [dlg.file_list.item(i).data(0x0100)
       for i in range(dlg.file_list.count())]
check("A", "A5: پیوست بدون فایل در فهرست حذف‌شده‌ها دیده می‌شود",
      ghost.id in ids)
row = ids.index(ghost.id)
dlg.file_list.setCurrentRow(row)
dlg.on_file_selected(dlg.file_list.item(row))
messages.clear()
dlg.restore_selected()

check("A", "A5: بازیابی رد شد و پیام خطای صریح «فایل فیزیکی» آمد",
      any(kind == "crit" and "فایل فیزیکی" in msg
          for kind, msg in messages), f"messages={messages}")
check("A", "A5: رکورد در همان حالت حذف‌شده ماند (بدون نیمه‌بازیابی)",
      is_deleted(ghost.id))
check("A", "A5: پیام موفقیت جعلی صادر نشد",
      not any(kind == "info" for kind, _ in messages))
dlg.close()
dlg.deleteLater()

# ---------- A6: BUG-ATT-06 — سقف ۲۰ با بازیابی هم سنجیده می‌شود ----------
LIMITED = ("intervention", 9)
for i in range(20):
    make_attachment(f"lim_{i:02d}.txt", f"c{i}".encode(), LIMITED)
first = SERVICE.get_attachments_by_entity(LIMITED[0], LIMITED[1])[0]
SERVICE.delete_attachment(first.id)
extra = make_attachment("to_delete.txt", b"x", LIMITED)
# اکنون: ۲۰ فعال (سقف پر) + ۱ حذف‌شدهٔ در انتظار بازیابی («first»)
check("A", "A6: پیش‌فرض سناریو — ۲۰ فعال و ۱ حذف‌شده",
      active_count(LIMITED) == 20 and is_deleted(first.id)
      and not is_deleted(extra.id))

dlg = AttachmentDialog(LIMITED[0], LIMITED[1])
dlg.show_deleted_check.setChecked(True)
dlg.file_list.setCurrentRow(0)
dlg.on_file_selected(dlg.file_list.item(0))
messages.clear()
dlg.restore_selected()

check("A", "A6: بازیابی در سقفِ پر رد شد با پیام «حداکثر»",
      any(kind == "crit" and "حداکثر" in msg
          for kind, msg in messages), f"messages={messages}")
check("A", "A6: رکورد همچنان حذف‌شده است",
      is_deleted(first.id))

# جا باز می‌کنیم → همان مسیر UI حالا موفق می‌شود
holder = SERVICE.get_attachments_by_entity(LIMITED[0], LIMITED[1])[0]
SERVICE.delete_attachment(holder.id)
messages.clear()
dlg.load_attachments()          # تازه‌سازی فهرست حذف‌شده‌ها
dlg.file_list.setCurrentRow(0)
dlg.on_file_selected(dlg.file_list.item(0))
dlg.restore_selected()
check("A", "A6: پس از بازکردن جا، بازیابی از همان مسیر UI موفق شد",
      any(kind == "info" for kind, _ in messages)
      and not is_deleted(first.id)
      and active_count(LIMITED) == 20)
dlg.close()
dlg.deleteLater()

# ---------- A7: رگرسیون — حذف منطقی از مسیر UI فایل را نگه می‌دارد ----------
dlg = AttachmentDialog(ENTITY[0], ENTITY[1])
keep = make_attachment("keep_me.txt", b"keep", ENTITY)
dlg.load_attachments()
for i in range(dlg.file_list.count()):
    if dlg.file_list.item(i).data(0x0100) == keep.id:
        dlg.file_list.setCurrentRow(i)
        break
dlg.on_file_selected(dlg.file_list.currentItem())
messages.clear()
dlg.delete_selected()
check("A", "A7: حذف منطقی: رکورد حذف شد ولی فایل فیزیکی ماند",
      is_deleted(keep.id) and os.path.exists(keep.file_path))
check("A", "A7: پیام موفقیت حذف صادر شد",
      any(kind == "info" and "حذف" in msg for kind, msg in messages))
dlg.close()
dlg.deleteLater()

# ---------- A8: رگرسیون — قرارداد DAL (نباید True ثابت بدهد) ----------
fresh = make_attachment("contract.txt", b"contract", ENTITY)
check("A", "A8: بازیابی رکورد فعال در DAL → False (نه True ثابت)",
      AttachmentDAL().restore(fresh.id) is False)
SERVICE.delete_attachment(fresh.id)
check("A", "A8: بازیابی رکورد حذف‌شده در DAL → True",
      AttachmentDAL().restore(fresh.id) is True)
check("A", "A8: بازیابی دوبارهٔ همان رکورد → False",
      AttachmentDAL().restore(fresh.id) is False)

# ============================================================
# بخش B: مرحلهٔ ۳ — سال و پایهٔ فهرست‌ها (بندهای ۶ و ۷)
# ============================================================
print()
print("=" * 76)
print("بخش B: مرحلهٔ ۳ — هندلر سال شاخص‌ها/تحلیل و پایهٔ سال انتخاب‌شده")
print("=" * 76)

from dal.academic_year_dal import AcademicYearDAL
from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from dal.student_dal import StudentDAL
from models.academic_year import AcademicYear
from models.student import Student
from models.student_academic_profile import StudentAcademicProfile
from views.pages.indicators_page import IndicatorsPage
from views.pages.analysis_page import AnalysisPage

year_dal = AcademicYearDAL()
student_dal = StudentDAL()
profile_dal = StudentAcademicProfileDAL()


def make_year(title, start, end):
    year = AcademicYear()
    year.title = title
    year.start_date = start
    year.end_date = end
    return year_dal.create(year)


def make_student(first, last, national_code):
    student = Student()
    student.first_name = first
    student.last_name = last
    student.national_code = national_code
    return student_dal.create(student)


def make_profile(student_id, year_id, grade, class_name):
    profile = StudentAcademicProfile()
    profile.student_id = student_id
    profile.academic_year_id = year_id
    profile.grade = grade
    profile.class_name = class_name
    profile.status = "active"
    return profile_dal.create(profile)


def select_combo_item(combo, data_value, emit=True):
    """انتخاب در کامبو (با یا بدون سیگنال واقعی)"""
    for i in range(combo.count()):
        if combo.itemData(i) == data_value:
            if not emit:
                combo.blockSignals(True)
            combo.setCurrentIndex(i)
            if not emit:
                combo.blockSignals(False)
            return True
    return False


def combo_student_ids(combo):
    return [combo.itemData(i) for i in range(combo.count())]


def combo_row_text(combo, data_value):
    for i in range(combo.count()):
        if combo.itemData(i) == data_value:
            return combo.itemText(i)
    return None


# دادهٔ دو ساله: A فقط ۱۴۰۳ (پایهٔ سوم)؛ B فقط ۱۴۰۴ (پایهٔ اول)
y1403 = make_year("۱۴۰۳-۱۴۰۴", "1403/07/01", "1404/06/30")
y1404 = make_year("۱۴۰۴-۱۴۰۵", "1404/07/01", "1405/06/30")
year_dal.set_active(y1404.id)

student_a = make_student("علی", "یک‌سال‌ه", "5550000001")
student_b = make_student("رضا", "دو‌سال‌ه", "5550000002")
profile_a = make_profile(student_a.id, y1403.id, 3, "سوم-الف")
profile_b = make_profile(student_b.id, y1404.id, 1, "اول-ب")

# ---------- B1: فهرست شاخص‌ها از سال انتخاب‌شده ----------
with contextlib.redirect_stdout(io.StringIO()):
    ipage = IndicatorsPage()

check("B", "B1: صفحهٔ شاخص‌ها با سال فعال (۱۴۰۴) بالا آمد",
      ipage.year_combo.currentData() == y1404.id,
      f"year={ipage.year_combo.currentData()}")
select_combo_item(ipage.year_combo, y1403.id)   # سیگنال واقعی → on_year_changed
check("B", "B1: فهرست ۱۴۰۳ فقط A را دارد (B نشت نکرده)",
      combo_student_ids(ipage.student_combo) == [None, student_a.id],
      f"ids={combo_student_ids(ipage.student_combo)}")
check("B", "B1: پایهٔ نمایشی A از پروندهٔ ۱۴۰۳ است («سوم»)",
      "سوم" in (combo_row_text(ipage.student_combo, student_a.id) or ""))

# ---------- B2: تغییر سال → پنل کهنه پاک ----------
select_combo_item(ipage.student_combo, student_a.id, emit=False)
with contextlib.redirect_stdout(io.StringIO()):
    ipage.load_student_indicators()
check("B", "B2: انتخاب A در ۱۴۰۳ ثبت شد",
      ipage.current_student_id == student_a.id
      and ipage.current_profile_id == profile_a.id)

select_combo_item(ipage.year_combo, y1404.id)   # سیگنال واقعی
check("B", "B2: تغییر سال → انتخاب و پروندهٔ کهنه پاک شد",
      ipage.current_student_id is None
      and ipage.current_profile_id is None)
check("B", "B2: پنل جزئیات پیام راهنما دارد (نه نتیجهٔ کهنه)",
      "دانش‌آموز" in ipage.details_panel.toPlainText())
check("B", "B2: فهرست ۱۴۰۴ فقط B را دارد",
      combo_student_ids(ipage.student_combo) == [None, student_b.id])
check("B", "B2: پایهٔ نمایشی B از پروندهٔ ۱۴۰۴ است («اول»)",
      "اول" in (combo_row_text(ipage.student_combo, student_b.id) or ""))
ipage.close()
ipage.deleteLater()

# ---------- B3: حفظ ایمن انتخاب وقتی همان دانش‌آموز در هر دو سال هست ----------
make_profile(student_b.id, y1403.id, 2, "دوم-ب")
with contextlib.redirect_stdout(io.StringIO()):
    ipage = IndicatorsPage()
select_combo_item(ipage.year_combo, y1404.id)
select_combo_item(ipage.student_combo, student_b.id, emit=False)
with contextlib.redirect_stdout(io.StringIO()):
    ipage.load_student_indicators()
select_combo_item(ipage.year_combo, y1403.id)   # سیگنال واقعی
check("B", "B3: انتخاب B پس از تغییر سال حفظ شد",
      ipage.current_student_id == student_b.id)
check("B", "B3: پنل با پروندهٔ ۱۴۰۳ دوباره خوانده شد (پایهٔ دوم)",
      ipage.current_profile_id == profile_dal.get_by_student_and_year(
          student_b.id, y1403.id).id)
ipage.close()
ipage.deleteLater()

# ---------- B4: صفحهٔ تحلیل — همان قرارداد ----------
# (توجه: از B3، دانش‌آموز B در ۱۴۰۳ هم پرونده دارد → فهرست ۱۴۰۳ هر دو)
with contextlib.redirect_stdout(io.StringIO()):
    apage = AnalysisPage()
select_combo_item(apage.year_combo, y1403.id)   # سیگنال واقعی → on_year_changed
ids_1403 = combo_student_ids(apage.student_combo)
check("B", "B4: فهرست تحلیل ۱۴۰۳ = پرونده‌های همان سال (A و B از B3)",
      ids_1403 == [None, student_b.id, student_a.id], f"ids={ids_1403}")
check("B", "B4: پایهٔ B در ۱۴۰۳ «دوم» است (پروندهٔ همان سال، نه فعال)",
      "دوم" in (combo_row_text(apage.student_combo, student_b.id) or ""))
select_combo_item(apage.year_combo, y1404.id)
check("B", "B4: فهرست تحلیل در ۱۴۰۴ فقط B است",
      combo_student_ids(apage.student_combo) == [None, student_b.id])
check("B", "B4: پایهٔ B در ۱۴۰۴ «اول» است (پروندهٔ همان سال)",
      "اول" in (combo_row_text(apage.student_combo, student_b.id) or ""))
apage.close()
apage.deleteLater()

# ============================================================
# بخش C: مرحلهٔ ۳ — نگاشت ناوبری و کنتراست هدر (بندهای ۲۶ و ۳۱)
# ============================================================
print()
print("=" * 76)
print("بخش C: مرحلهٔ ۳ — نگاشت مرکزی ناوبری و کنتراست نام/آیکون کاربر")
print("=" * 76)

from views.main_window import PAGE_INDEX

# ---------- C1: نگاشت مرکزی ----------
check("C", "C1: PAGE_INDEX پیوسته 0..N است",
      sorted(PAGE_INDEX.values()) == list(range(len(PAGE_INDEX))))
check("C", "C1: ایندکس‌های کلیدی مطابق ترتیب addWidget است",
      PAGE_INDEX["students"] == 2 and PAGE_INDEX["followups"] == 5
      and PAGE_INDEX["reports"] == 8 and PAGE_INDEX["goals"] == 13)

# ---------- C2: هیچ setCurrentIndex عددی خام روی stacked_widget ----------
import pathlib
mw_src = pathlib.Path("views/main_window.py").read_text(encoding="utf-8")
import re
raw_indexes = [
    m.group(1).strip()
    for m in re.finditer(r"stacked_widget\.setCurrentIndex\(([^)]*)\)", mw_src)
]
check("C", "C2: setCurrentIndex فقط از PAGE_INDEX (index/idx) می‌خواند",
      set(raw_indexes) <= {"index", "idx"}, f"args={raw_indexes}")
check("C", "C2: منو با نام صفحه کار می‌کند نه ایندکس عددی",
      '"btn_settings", "⚙️ تنظیمات", "settings", None' in mw_src
      and ', 9, None)' not in mw_src)

# ---------- C3: کنتراست محاسباتی (WCAG) ----------

def _relative_luminance(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))
    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(fg_hex, bg_hex):
    l1 = _relative_luminance(fg_hex)
    l2 = _relative_luminance(bg_hex)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# سایدبار: user_frame #08223A — نام/آیکون باید مرئی باشند (دور هجدهم)
sidebar_name = contrast_ratio("F4C542", "08223A")
check("C", "C3: نام/آیکون کاربر سایدبار (#F4C542 روی #08223A) ≥ 4.5",
      sidebar_name >= 4.5, f"ratio={sidebar_name:.2f}")
# رگرسیون: رنگ قدیمی نامرئی نباید برگردد
check("C", "C3: رنگ نامرئی قبلی (#08223A روی خودش) در سورس سایدبار نیست",
      'user_icon_label.setStyleSheet("font-size: 20px; color: #08223A;")'
      not in mw_src
      and "color: #08223A; font-size: 13px; font-weight: bold;" not in mw_src)
# هدر اصلی: پس‌زمینه #0B2E4F
header_user = contrast_ratio("66BB6A", "0B2E4F")
header_title = contrast_ratio("F4C542", "0B2E4F")
header_version = contrast_ratio("D9C36A", "0B2E4F")
check("C", "C3: نام کاربر هدر (#66BB6A) ≥ 4.5",
      header_user >= 4.5, f"ratio={header_user:.2f}")
check("C", "C3: عنوان هدر (#F4C542) ≥ 4.5",
      header_title >= 4.5, f"ratio={header_title:.2f}")
check("C", "C3: نسخهٔ هدر (#D9C36A) ≥ 4.5",
      header_version >= 4.5, f"ratio={header_version:.2f}")
# نقش کاربر سایدبار (#D9C36A روی #08223A)
check("C", "C3: نقش کاربر سایدبار (#D9C36A) ≥ 4.5",
      contrast_ratio("D9C36A", "08223A") >= 4.5)

# ============================================================
# پایان
# ============================================================

QMessageBox.information = real_info
QMessageBox.critical = real_crit
QMessageBox.warning = real_warn
QMessageBox.question = real_question

with contextlib.suppress(Exception):
    dbc.DatabaseConnection().close_all()
with contextlib.suppress(Exception):
    shutil.rmtree(TMP, ignore_errors=True)

print()
print("=" * 76)
print(f"نتیجهٔ دور هجدهم (مرحله‌های ۲ و ۳):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("موارد ناموفق:")
    for f in FAILURES:
        print(f"   - {f}")
    sys.exit(1)
sys.exit(0)
