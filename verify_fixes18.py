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
print(f"نتیجهٔ دور هجدهم (مرحلهٔ ۲ — پیوست‌ها):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
print("=" * 76)
if FAILURES:
    print("موارد ناموفق:")
    for f in FAILURES:
        print(f"   - {f}")
    sys.exit(1)
sys.exit(0)
