"""
بررسی‌های دور هفدهم — «MASTER FIX / FINAL TECHNICAL AUDIT»

هر بررسی «کارکردی با پیش/پس‌شرط» است: وضعیت دیتابیس/فایل پیش و پس از
عملیات مقایسه می‌شود، نه فقط «استثنا نداد».

مرحلهٔ ۱ — P0: داده و صداقت پشتیبان/بازیابی (بند ۱۰ مأموریت):
  A) شکست checksum = شکست بازیابی با پیش/پس‌شرط، وضعیت صریح پشتیبان بدون
     فایل کناری (legacy) با هشدار دیده‌شدنی، حساب‌داری واقعی پیوست‌ها در
     متادیتا (موردانتظار طبق DB / بسته‌بندی‌شده / گم‌شده)، پشتیبان ناقص ≠
     کامل، پاک‌سازی فایل ایمنی در مسیر استثنا، توقف واقعی نخ پشتیبان‌گیری
     خودکار پیش از خروج برنامه، و حفظ قراردادهای قبلی ..................... ۱۲ بررسی

مرحلهٔ ۲ — P1: یکپارچگی نوشتن دانش‌آموز و استثناهای بی‌صدا (بندهای ۱۲، ۱۳، ۳۴):
  B) تراکنش واقعی برای student+profile+family، پیام موفقیت فقط یک لایه،
     بررسی نتیجهٔ واقعی update، و نبود «except: pass» در لایه‌های بحرانی ... ۹ بررسی

مرحلهٔ ۳ — P1: مسیرهای بازیابی (service + UI) و آزمون‌های یکپارچه (بندهای ۳، ۳۸، ۳۹):
  C) چک‌باکس «نمایش حذف‌شده‌ها» + دکمهٔ ↩️ در چهار صفحهٔ دانش‌آموز/فعالیت/
     هدف/مشاوره با عبور از لایهٔ سرویس، بررسی نتیجهٔ واقعی بازیابی، حفظ
     پروندهٔ تاریخی در زنجیرهٔ حذف→بازیابی→تغییر سال→ویرایش
     (IT-RESTORE-YEAR-01)، جدایی دادهٔ سال‌ها (IT-YEAR-CRUD-01) و
     بازگرداندن کاربر در صفحهٔ تنظیمات (RESTORE-02) ...................... ۱۱ بررسی

مرحلهٔ ۴ — P1: درستی ایمپورت/خروجی/صفحه‌بندی/جست‌وجو (بندهای ۱۴، ۱۵، ۱۶، ۱۷، ۱۹):
  D) ماتریس کامل صفحه‌بندی (N=۰/۱/۲۰/۲۱/۴۰/۴۱ و ۱۵۰ رکورد)، خروجی Excel
     «همهٔ دانش‌آموزان بارگذاری‌شده» (نه صفحهٔ جاری) با برچسب صریح در حالت
     حذف‌شده‌ها، لغو دیالوگ‌های ایمپورت، نمایش جزئیات خطا در مسیر واقعی UI،
     و «فیلتر سال پیش از LIMIT» با ۲۴۰ رکورد در دو سال برای مشاهدات/مداخلات/
     پیگیری‌ها (خود query، مسیر جست‌وجو و صفحهٔ واقعی) .................. ۱۰ بررسی

جمع فعلی: ۴۲ بررسی
"""

import contextlib
import hashlib
import io
import json
import logging
import os
import shutil
import sys
import tempfile
import zipfile

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


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


TMP = tempfile.mkdtemp(prefix="round17_verify_")

# ============================================================
# دیتابیس موقت برنامه (هیچ دست‌زدنی به دیتابیس واقعی نمی‌شود)
# ============================================================
TEST_DB = os.path.join(TMP, "partow.db")
ATT_DIR = os.path.join(TMP, "attachments")
BK_DIR = os.path.join(TMP, "backups")
os.makedirs(ATT_DIR, exist_ok=True)
os.makedirs(BK_DIR, exist_ok=True)

import config.settings as settings
import database.connection as dbc

settings.DB_PATH = TEST_DB
dbc.DB_PATH = TEST_DB
dbc.DatabaseConnection._instance = None
dbc.DatabaseConnection._connection = None
dbc.DatabaseConnection._initialized = False

with contextlib.redirect_stdout(io.StringIO()):
    db = dbc.DatabaseConnection()
    conn = db.get_connection(user_id=1)

import utils.backup as backup_mod
from dal.attachment_dal import AttachmentDAL
from dal.student_dal import StudentDAL
from models.attachment import Attachment
from models.student import Student
from utils.backup import BackupManager

for _h in list(backup_mod.logger.handlers):
    if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
        _h.setLevel(logging.CRITICAL)

bm = BackupManager(TEST_DB, ATT_DIR, BK_DIR)
for _h in list(bm.logger.handlers):
    if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
        _h.setLevel(logging.CRITICAL)


def _student_count():
    """شمار دانش‌آموزان با اتصال تازه (بازیابی، اتصال‌ها را می‌بندد)."""
    fresh = dbc.DatabaseConnection().get_connection(user_id=1)
    return fresh.execute("SELECT COUNT(*) FROM students").fetchone()[0]


def _sha256(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as fh:
        hasher.update(fh.read())
    return hasher.hexdigest()


def _dir_files(path):
    return sorted(os.listdir(path)) if os.path.isdir(path) else []


def _leftover_files():
    """فایل/پوشه‌های موقتی که نباید بعد از عملیات باقی بمانند"""
    leftovers = []
    for name in ("temp_restore",):
        if os.path.exists(os.path.join(BK_DIR, name)):
            leftovers.append(name)
    if os.path.exists(TEST_DB + ".restore_safety"):
        leftovers.append("partow.db.restore_safety")
    if os.path.exists(ATT_DIR + ".restore_safety"):
        leftovers.append("attachments.restore_safety")
    leftovers += [f for f in _dir_files(BK_DIR)
                  if f.endswith((".tmp", ".db.tmp", "-wal", "-shm", "-journal"))]
    return leftovers


def _metadata_of(backup_file):
    with zipfile.ZipFile(backup_file, "r") as zipf:
        return json.loads(zipf.read("metadata.json").decode("utf-8"))


# ============================================================
print("=" * 76)
print("بخش A: مرحلهٔ ۱ — داده و صداقت پشتیبان/بازیابی (بند ۱۰ مأموریت)")
print("=" * 76)

# --- دادهٔ پایه: یک دانش‌آموز + دو ردیف پیوست (یکی فایل دارد، یکی ندارد)
student = Student()
student.first_name = "زهرا"
student.last_name = "پشتیبان‌آزمون"
student.national_code = "1700000001"
student.is_active = 1
with contextlib.redirect_stdout(io.StringIO()):
    student = StudentDAL().create(student)

ATT_SUBDIR = os.path.join(ATT_DIR, "student", str(student.id))
os.makedirs(ATT_SUBDIR, exist_ok=True)
present_file = os.path.join(ATT_SUBDIR, "present_attachment.txt")
with open(present_file, "w", encoding="utf-8") as fh:
    fh.write("محتوای پیوست موجود")

att_dal = AttachmentDAL()
att_present = Attachment()
att_present.entity_type = "student"
att_present.entity_id = student.id
att_present.file_name = "present_attachment.txt"
att_present.file_path = present_file
att_present.file_size = os.path.getsize(present_file)
att_present.file_type = "document"
att_present.created_by = None
att_present = att_dal.create(att_present)

missing_path = os.path.join(ATT_SUBDIR, "ghost_attachment.txt")
att_missing = Attachment()
att_missing.entity_type = "student"
att_missing.entity_id = student.id
att_missing.file_name = "ghost_attachment.txt"
att_missing.file_path = missing_path
att_missing.file_size = 1234
att_missing.file_type = "document"
att_missing.created_by = None
att_missing = att_dal.create(att_missing)

# --- A1: پشتیبان کامل‌نما با فایل گم‌شده → هشدار صریح در متادیتا و نتیجه
res_incomplete = bm.create_backup("incomplete_case", user_id=1, user_name="آزمون")
incomplete_file = res_incomplete.get("file") or ""
meta_incomplete = _metadata_of(incomplete_file) if incomplete_file else {}
check("A",
      "پشتیبان ناقص «کامل» معرفی نمی‌شود: متادیتا تعداد موردانتظار طبق DB، فایل‌های بسته‌بندی‌شده و نام فایل‌های گم‌شده را گزارش می‌کند و نتیجه complete=False با پیام ⚠️ برمی‌گرداند",
      res_incomplete.get("success") is True
      and res_incomplete.get("attachments_expected_in_db") == 2
      and res_incomplete.get("attachments_packaged_files") == 1
      and res_incomplete.get("attachments_missing_count") == 1
      and "ghost_attachment.txt" in res_incomplete.get("attachments_missing_files", [])
      and res_incomplete.get("complete") is False
      and str(res_incomplete.get("message", "")).lstrip().startswith("⚠️")
      and meta_incomplete.get("attachments_expected_in_db") == 2
      and meta_incomplete.get("attachments_packaged_files") == 1
      and meta_incomplete.get("attachments_missing_count") == 1
      and "ghost_attachment.txt" in meta_incomplete.get("attachments_missing_files", [])
      and meta_incomplete.get("complete") is False,
      f"res={ {k: res_incomplete.get(k) for k in ('attachments_expected_in_db', 'attachments_packaged_files', 'attachments_missing_count', 'complete')} } "
      f"meta={ {k: meta_incomplete.get(k) for k in ('attachments_expected_in_db', 'attachments_packaged_files', 'attachments_missing_count', 'complete')} }")

# --- A2: پشتیبان کامل (همهٔ ردیف‌های DB فایل دارند) → complete=True بدون هشدار
conn.execute("UPDATE attachments SET is_deleted = 1 WHERE id = ?", (att_missing.id,))
conn.commit()
res_complete = bm.create_backup("complete_case", user_id=1, user_name="آزمون")
complete_file = res_complete.get("file") or ""
meta_complete = _metadata_of(complete_file) if complete_file else {}
check("A",
      "پشتیبان کامل: تعداد موردانتظار طبق DB با فایل‌های بسته‌بندی‌شده می‌خواند، complete=True است و پیام هیچ هشدار ناقصی ندارد",
      res_complete.get("success") is True
      and res_complete.get("attachments_expected_in_db") == 1
      and res_complete.get("attachments_packaged_files") == 1
      and res_complete.get("attachments_missing_count") == 0
      and res_complete.get("complete") is True
      and "⚠️" not in str(res_complete.get("message", ""))
      and meta_complete.get("complete") is True
      and meta_complete.get("attachments_missing_count") == 0,
      f"meta={meta_complete.get('complete')} res_missing={res_complete.get('attachments_missing_count')}")

# --- A3: شکست checksum = شکست بازیابی (رگرسیون BUG-BACKUP-01) با پیش/پس‌شرط
tampered = os.path.join(BK_DIR, "tampered_case.partobak")
shutil.copy2(complete_file, tampered)
shutil.copy2(complete_file + ".sha256", tampered + ".sha256")
with open(tampered, "ab") as fh:
    fh.write(b"garbage after archive")
students_before = _student_count()
files_before = _dir_files(BK_DIR)
res_bad = bm.restore_backup(tampered, user_id=1, user_name="آزمون")
files_after = _dir_files(BK_DIR)
check("A",
      "BUG-BACKUP-01 (رگرسیون): checksum نامطابق → بازیابی انجام نمی‌شود، دیتابیس دست‌نخورده، نتیجه checksum_state='failed' و هیچ فایل/پوشهٔ موقتی باقی نمی‌ماند",
      res_bad.get("success") is False
      and res_bad.get("checksum_verified") is False
      and res_bad.get("checksum_state") == "failed"
      and _student_count() == students_before
      and files_after == files_before
      and not _leftover_files(),
      f"state={res_bad.get('checksum_state')} students {students_before}->{_student_count()} leftovers={_leftover_files()}")

# --- A4: پشتیبان بدون فایل کناری (قدیمی) → بازیابی مجاز، ولی وضعیت صریح و هشدار
legacy = os.path.join(BK_DIR, "legacy_case.partobak")
shutil.copy2(complete_file, legacy)
res_legacy = bm.restore_backup(legacy, user_id=1, user_name="آزمون")
legacy_msg = str(res_legacy.get("message", ""))
check("A",
      "BUG-BACKUP-03: پشتیبان قدیمی بدون .sha256 → بازیابی انجام می‌شود ولی نتیجه checksum_state='legacy_no_sidecar'، checksum_verified=False و پیام کاربر هشدار صریح «راستی‌آزمایی نشد» دارد",
      res_legacy.get("success") is True
      and res_legacy.get("checksum_verified") is False
      and res_legacy.get("checksum_state") == "legacy_no_sidecar"
      and "⚠️" in legacy_msg
      and "راستی‌آزمایی نشد" in legacy_msg,
      f"state={res_legacy.get('checksum_state')} msg={legacy_msg[:120]!r}")

# --- A5: پشتیبان سالم با فایل کناری → وضعیت verified
res_verified = bm.restore_backup(complete_file, user_id=1, user_name="آزمون")
check("A",
      "پشتیبان سالم با فایل کناری: checksum_state='verified'، checksum_verified=True و هیچ هشدار یکپارچگی در پیام نیست (مسیر عادی تضعیف نشده)",
      res_verified.get("success") is True
      and res_verified.get("checksum_verified") is True
      and res_verified.get("checksum_state") == "verified"
      and "راستی‌آزمایی نشد" not in str(res_verified.get("message", "")),
      f"state={res_verified.get('checksum_state')}")

# --- A6: بازیابی پشتیبانی که ردیف پیوستِ گم‌شده دارد → هشدار پس از بازیابی
res_restore_incomplete = bm.restore_backup(incomplete_file, user_id=1, user_name="آزمون")
restore_incomplete_msg = str(res_restore_incomplete.get("message", ""))
check("A",
      "BUG-BACKUP-04/05 (سمت بازیابی): اگر دیتابیس بازیابی‌شده به فایلی اشاره کند که موجود نیست، نتیجه complete=False، شمار گم‌شده‌ها گزارش می‌شود و پیام با هشدار شروع می‌شود (موفقیت خاموش ممنوع)",
      res_restore_incomplete.get("success") is True
      and res_restore_incomplete.get("attachments_missing_count", 0) >= 1
      and res_restore_incomplete.get("complete") is False
      and restore_incomplete_msg.lstrip().startswith("⚠️")
      and "ghost_attachment.txt" in restore_incomplete_msg,
      f"missing={res_restore_incomplete.get('attachments_missing_count')} msg={restore_incomplete_msg[:140]!r}")

# --- A7: استثنا وسط بازیابی → برگشت دیتابیس قبلی، بدون باقی‌ماندهٔ ایمنی
students_before_exc = _student_count()
real_verify = BackupManager._verify_restored_database


def _boom_verify(self):
    raise RuntimeError("verify exploded")


BackupManager._verify_restored_database = _boom_verify
try:
    res_exc = bm.restore_backup(complete_file, user_id=1, user_name="آزمون")
finally:
    BackupManager._verify_restored_database = real_verify
check("A",
      "BUG-BACKUP-07 (مسیر استثنا): شکست در راستی‌آزمایی پس از جایگزینی → نتیجه success=False، دیتابیس قبلی برگشته، هیچ فایل .restore_safety/پوشهٔ موقتی باقی نمی‌ماند",
      res_exc.get("success") is False
      and "verify exploded" in str(res_exc.get("message", ""))
      and _student_count() == students_before_exc
      and not os.path.exists(TEST_DB + ".restore_safety")
      and not _leftover_files(),
      f"count {students_before_exc}->{_student_count()} leftovers={_leftover_files()}")

# --- A8: شکست کپی پیوست‌ها → دیتابیس بازیابی می‌شود، پیوست‌های قبلی دست‌نخورده
with open(present_file, "w", encoding="utf-8") as fh:
    fh.write("محتوای پیوست موجود (نسخهٔ فعلی)")
real_swap = BackupManager._swap_attachments_dir


def _fail_swap(self, new_dir):
    return False, "شبیه‌سازی شکست کپی پیوست"


BackupManager._swap_attachments_dir = _fail_swap
try:
    res_att = bm.restore_backup(complete_file, user_id=1, user_name="آزمون")
finally:
    BackupManager._swap_attachments_dir = real_swap
att_content = ""
if os.path.exists(present_file):
    with open(present_file, encoding="utf-8") as fh:
        att_content = fh.read()
check("A",
      "شکست بازیابی پیوست‌ها: دیتابیس بازیابی می‌شود، پیوست‌های قبلی دست‌نخورده می‌مانند، نتیجه صریحاً attachments_restored=False با پیام ⚠️ است و فایل ایمنی باقی نمی‌ماند",
      res_att.get("success") is True
      and res_att.get("attachments_restored") is False
      and str(res_att.get("message", "")).lstrip().startswith("⚠️")
      and "شبیه‌سازی شکست کپی پیوست" in str(res_att.get("message", ""))
      and att_content.startswith("محتوای پیوست موجود")
      and not os.path.exists(ATT_DIR + ".restore_safety")
      and not _leftover_files(),
      f"restored={res_att.get('attachments_restored')} att_exists={os.path.exists(present_file)} leftovers={_leftover_files()}")

# --- A9: قراردادهای قبلی حفظ شده‌اند (بدون تضعیف)
with open(complete_file + ".sha256", encoding="utf-8") as _fh:
    sidecar_value = _fh.read().strip()
sidecar_ok = (os.path.exists(complete_file + ".sha256")
              and sidecar_value == _sha256(complete_file) == res_complete.get("checksum")
              and len(res_complete.get("checksum", "")) == 64)
corrupt_file = os.path.join(BK_DIR, "corrupt_case.partobak")
with open(corrupt_file, "wb") as fh:
    fh.write(b"this is not a zip file")
nochk_file = os.path.join(BK_DIR, "nochecksum_case.partobak")
shutil.copy2(complete_file, nochk_file)
statuses = {b["file"]: b["status"] for b in bm.list_backups()}
check("A",
      "بدون تضعیف: sidecar همان SHA-256 فایل و همان checksum نتیجه است؛ متادیتا کلید attachments_count و _count_attachments را حفظ کرده (قرارداد verify_fixes16 §B3)؛ وضعیت‌های ok/mismatch/corrupt/no_checksum دست‌نخورده‌اند",
      sidecar_ok
      and "self._count_attachments()" in read("utils/backup.py")
      and "attachments_count" in meta_complete
      and statuses.get("complete_case.partobak") == "ok"
      and statuses.get("tampered_case.partobak") == "mismatch"
      and statuses.get("corrupt_case.partobak") == "corrupt"
      and statuses.get("nochecksum_case.partobak") == "no_checksum",
      f"sidecar_ok={sidecar_ok} statuses={statuses}")

# --- A10: هشدار پیش از تأیید بازیابی در UI (پشتیبان قدیمی/نامطابق/خراب)
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

app = QApplication.instance() or QApplication(sys.argv)

import views.pages.backup_page as backup_page_mod
from views.pages.backup_page import BackupPage

# صفحهٔ پشتیبان‌گیری باید روی محیط موقت همین آزمون کار کند (نتیجهٔ واقعی
# در دیتابیس واقعی کاربر نوشته نشود).
backup_page_mod.BACKUP_DIR = BK_DIR
backup_page_mod.DB_PATH = TEST_DB
backup_page_mod.ATTACHMENTS_DIR = ATT_DIR
backup_page_mod.LEGACY_BACKUP_DIR = os.path.join(TMP, "legacy_backups")

warnings = {status: BackupPage._checksum_warning(status)
            for status in ("ok", "no_checksum", "mismatch", "corrupt")}
ui_messages = []
real_question = QMessageBox.question
real_critical = QMessageBox.critical
real_information = QMessageBox.information
real_get_open = QFileDialog.getOpenFileName
asked_texts = []


def _fake_question(parent, title, text, *a, **k):
    asked_texts.append(text)
    return QMessageBox.StandardButton.No


QMessageBox.question = staticmethod(_fake_question)
QMessageBox.critical = staticmethod(
    lambda *a, **k: ui_messages.append(("crit", str(a[2]))) or QMessageBox.StandardButton.Ok)
QMessageBox.information = staticmethod(
    lambda *a, **k: ui_messages.append(("info", str(a[2]))) or QMessageBox.StandardButton.Ok)

page_shutdown_ok = False
try:
    page = BackupPage()
    # ۱) فایل خراب از مسیر «بازیابی از فایل» باید پیش از هر کاری رد شود
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (corrupt_file, "PARTO Backup (*.partobak)"))
    with contextlib.redirect_stdout(io.StringIO()):
        page.restore_from_file()
    corrupt_refused = (page.worker is None
                       and any("نامعتبر" in msg or "معتبری نیست" in msg
                               for _kind, msg in ui_messages))
    # ۲) پشتیبان قدیمی از مسیر فهرست: متن تأییدیه باید هشدار داشته باشد
    legacy_entry = next(b for b in page.backup_manager.list_backups()
                        if b["file"] == "legacy_case.partobak")
    asked_texts.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        page.restore_backup(legacy_entry)
    legacy_warn_in_dialog = bool(asked_texts) and "یکپارچگی آن راستی‌آزمایی نمی‌شود" in asked_texts[0]
    # ۳) توقف کارگر در بستن برنامه (بدون کارگر فعال → True)
    page_shutdown_ok = page.shutdown(timeout=2) is True
finally:
    QMessageBox.question = real_question
    QMessageBox.critical = real_critical
    QMessageBox.information = real_information
    QFileDialog.getOpenFileName = real_get_open
check("A",
      "UI پشتیبان: پشتیبان خراب از مسیر «بازیابی از فایل» پیش از هر عملیات رد می‌شود؛ متن تأیید بازیابی پشتیبان بدون checksum هشدار «راستی‌آزمایی نمی‌شود» را نشان می‌دهد؛ shutdown کارگر بدون کارگر فعال True برمی‌گرداند",
      warnings["no_checksum"].startswith("\n\n⚠️")
      and warnings["mismatch"].startswith("\n\n❌")
      and warnings["ok"] == ""
      and corrupt_refused and legacy_warn_in_dialog and page_shutdown_ok,
      f"warnings={ {k: v[:12] for k, v in warnings.items()} } corrupt_refused={corrupt_refused} legacy_dialog={legacy_warn_in_dialog} shutdown={page_shutdown_ok}")

# --- A11: توقف واقعی نخ پشتیبان‌گیری خودکار از مسیر SettingsPage
from PySide6.QtWidgets import QDialog

import views.dialogs.login_dialog as login_dialog_mod


def _fake_login_exec(self, *a, **k):
    self.login_successful.emit(1, "admin", "admin")
    return QDialog.DialogCode.Accepted


login_dialog_mod.LoginDialog.exec = _fake_login_exec
import views.main_window as main_window_mod

win = None
win_problems = []
stopped_handle = None
handle_stop_calls = []
try:
    with contextlib.redirect_stdout(io.StringIO()):
        win = main_window_mod.MainWindow()
        app.processEvents()

    settings_page = win.settings_page

    # الف) دستگیرهٔ ساعت‌بندی‌شدهٔ واقعی: باید با فراخوانی خروج واقعاً تمام شود
    handle = bm.schedule_auto_backup(interval_hours=6, user_id=None, user_name="سیستم")
    settings_page.auto_backup_thread = handle
    real_stop = handle.stop


    def _spy_stop(timeout=5):
        handle_stop_calls.append(timeout)
        return real_stop(timeout)


    handle.stop = _spy_stop
    with contextlib.redirect_stdout(io.StringIO()):
        result = win._shutdown_background_workers()
    stopped_handle = (not handle.is_running()
                      and settings_page.auto_backup_thread is None)

    # ب) خروج واقعی پنجره هم همان مسیر را طی می‌کند
    call_log = []
    real_shutdown = settings_page.shutdown_backup_workers
    settings_page.shutdown_backup_workers = lambda *a, **k: (
        call_log.append("called") or real_shutdown(*a, **k))
    try:
        win.close()
        app.processEvents()
    finally:
        settings_page.shutdown_backup_workers = real_shutdown
    window_closed = not win.isVisible()
except Exception as e:
    win_problems.append(f"{type(e).__name__}: {e}")
    window_closed = False
check("A",
      "BUG-BACKUP-09: پیش از خروج، زمان‌بند پشتیبان‌گیری خودکار واقعاً متوقف می‌شود (نه فقط مرجع None)، نتیجهٔ گزارش‌شده صادق است و closeEvent پنجرهٔ اصلی همین مسیر را صدا می‌زند",
      not win_problems
      and stopped_handle is True
      and bool(handle_stop_calls)
      and call_log == ["called"]
      and window_closed
      and "shutdown_backup_workers" in read("views/pages/settings_page.py")
      and "self._shutdown_background_workers()" in read("views/main_window.py"),
      f"problems={win_problems} handle_stop={handle_stop_calls} close_called={call_log} closed={window_closed} result={result if not win_problems else None}")

# --- A12: نگهبان کلید تنظیمات — خروج، پشتیبان‌گیری خودکار را «خاموش» نمی‌کند
settings_source = read("views/pages/settings_page.py")
shutdown_block = settings_source.split("def shutdown_backup_workers", 1)[-1].split("def stop_auto_backup", 1)[0]
stop_block = settings_source.split("def stop_auto_backup", 1)[-1].split("def ", 1)[0]
check("A",
      "خروج برنامه انتخاب کاربر را عوض نمی‌کند: shutdown_backup_workers هیچ مقدار QSettings را تغییر نمی‌دهد (پشتیبان‌گیری خودکار در اجرای بعدی مثل قبل ادامه می‌یابد)، ولی دکمهٔ «توقف» کاربر همان‌طور که بود تنظیمات را خاموش ثبت می‌کند",
      "setValue" not in shutdown_block
      and "setValue" in stop_block
      and "auto_backup/enabled" in stop_block,
      f"shutdown_has_setValue={'setValue' in shutdown_block}")

# ============================================================
print()
print("=" * 76)
print("بخش B: مرحلهٔ ۲ — یکپارچگی نوشتن دانش‌آموز و استثناهای بی‌صدا (بندهای ۱۲، ۱۳، ۳۴)")
print("=" * 76)

import ast
import pathlib

import views.pages.students_page as students_page_mod
from dal.academic_year_dal import AcademicYearDAL
from models.academic_year import AcademicYear
from views.dialogs.student_form import StudentForm
from views.pages.students_page import StudentsPage

# آستانه‌های پیش از آزمون‌ها (تا اثر هر سناریو جدا سنجیده شود).
# اتصال ماژول در مسیر بازیابی بسته شده است؛ یک اتصال تازه گرفته می‌شود.
conn = dbc.DatabaseConnection().get_connection(user_id=1)
baseline_students = _student_count()
baseline_profiles = conn.execute(
    "SELECT COUNT(*) FROM student_academic_profiles").fetchone()[0]
baseline_family = conn.execute(
    "SELECT COUNT(*) FROM family_contexts").fetchone()[0]

message_log = []
real_info = QMessageBox.information
real_crit = QMessageBox.critical
real_warn = QMessageBox.warning
QMessageBox.information = staticmethod(
    lambda *a, **k: message_log.append(("info", str(a[2]))) or QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(
    lambda *a, **k: message_log.append(("crit", str(a[2]))) or QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(
    lambda *a, **k: message_log.append(("warn", str(a[2]))) or QMessageBox.StandardButton.Ok)


def _fill_form(form, national_code, first_name="یتیم", last_name="نیست"):
    form.first_name_input.setText(first_name)
    form.last_name_input.setText(last_name)
    form.father_name_input.setText("پدر")
    form.national_code_input.setText(national_code)
    form.birth_date_input.setText("1390/01/01")
    form.guardian_name_input.setText("ولی")
    form.guardian_phone_input.setText("09120000000")
    form.address_input.setPlainText("نشانی آزمایشی")
    return form


def _rows_for(national_code):
    student = conn.execute(
        "SELECT id FROM students WHERE national_code = ?", (national_code,)).fetchone()
    if not student:
        return None, 0, 0
    profiles = conn.execute(
        "SELECT COUNT(*) FROM student_academic_profiles WHERE student_id = ?",
        (student[0],)).fetchone()[0]
    family = conn.execute(
        "SELECT COUNT(*) FROM family_contexts f JOIN student_academic_profiles p "
        "ON p.id = f.student_profile_id WHERE p.student_id = ?", (student[0],)).fetchone()[0]
    return student[0], profiles, family


# --- B1: شکست مرحلهٔ سوم (اطلاعات خانوادگی) → هیچ دانش‌آموز/پروندهٔ یتیمی نمی‌ماند
fail_code = "1799999001"
form_family_fail = _fill_form(StudentForm(parent=None), fail_code)
original_upsert = form_family_fail.family_dal.upsert_family_facts
form_family_fail.family_dal.upsert_family_facts = lambda *a, **k: (
    (_ for _ in ()).throw(RuntimeError("family upsert failed")))
messages_before = len(message_log)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        form_family_fail.save_student()
finally:
    form_family_fail.family_dal.upsert_family_facts = original_upsert
student_id_fail, profiles_fail, family_fail = _rows_for(fail_code)
family_msgs = message_log[messages_before:]
check("B",
      "بند ۱۲ (اتمیک‌بودن): شکست نوشتن «اطلاعات خانوادگی» در مرحلهٔ سوم → هیچ دانش‌آموز، پروندهٔ سالانه یا ردیف خانوادگی ساخته نمی‌شود (قبلاً دانش‌آموز یتیم ثبت می‌شد)، فرم پیام موفقیت نمی‌دهد و خطا صریح گزارش و لاگ می‌شود",
      student_id_fail is None and profiles_fail == 0 and family_fail == 0
      and _student_count() == baseline_students,
      f"student={student_id_fail} profiles={profiles_fail} family={family_fail} msgs={[m[0] for m in family_msgs]}")
check("B",
      "همان سناریو: پیام نمایش‌داده‌شده از نوع «خطا» است (نه موفقیت) و متن خطا علت واقعی را دارد",
      any(kind == "crit" and "family upsert failed" in msg for kind, msg in family_msgs)
      and not any(kind == "info" for kind, _ in family_msgs),
      f"msgs={[(k, v[:40]) for k, v in family_msgs]}")

# --- B2: شکست مرحلهٔ دوم (ساخت پروندهٔ سالانه) → دانش‌آموز هم برمی‌گردد
profile_fail_code = "1799999002"
form_profile_fail = _fill_form(StudentForm(parent=None), profile_fail_code)
original_create = form_profile_fail.profile_dal.create


def _failing_profile_create(_profile):
    raise RuntimeError("profile create failed")


form_profile_fail.profile_dal.create = _failing_profile_create
messages_before = len(message_log)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        form_profile_fail.save_student()
finally:
    form_profile_fail.profile_dal.create = original_create
student_id_p, profiles_p, family_p = _rows_for(profile_fail_code)
check("B",
      "بند ۱۲ (اتمیک‌بودن): شکست ساخت پروندهٔ سالانه → دانش‌آموز هم برمی‌گردد (بدون رکورد یتیم)، هیچ ردیف خانوادگی ساخته نمی‌شود و پیام خطا با علت واقعی نمایش داده می‌شود",
      student_id_p is None and _student_count() == baseline_students
      and any(kind == "crit" and "profile create failed" in msg
              for kind, msg in message_log[messages_before:])
      and not any(kind == "info" for kind, _ in message_log[messages_before:]),
      f"student={student_id_p} msgs={[(k, v[:40]) for k, v in message_log[messages_before:]]}")

# --- B3: مسیر موفق → یک رکورد کامل و «دقیقاً یک» پیام موفقیت
ok_code = "1799999003"
form_ok = _fill_form(StudentForm(parent=None), ok_code, "سارا", "سالم")
form_ok.brothers_spin.setValue(2)
form_ok.sisters_spin.setValue(1)
messages_before = len(message_log)
with contextlib.redirect_stdout(io.StringIO()):
    form_ok.save_student()
student_id_ok, profiles_ok, family_ok = _rows_for(ok_code)
ok_msgs = message_log[messages_before:]
family_row = conn.execute(
    "SELECT guardian_status, siblings_brothers, siblings_sisters FROM family_contexts f "
    "JOIN student_academic_profiles p ON p.id = f.student_profile_id "
    "WHERE p.student_id = ?", (student_id_ok,)).fetchone() if student_id_ok else None
check("B",
      "مسیر موفق پس از اصلاح: دانش‌آموز + پروندهٔ سالانه + زمینهٔ خانوادگی همه در یک تراکنش ذخیره می‌شوند، «دقیقاً یک» پیام موفقیت نمایش داده می‌شود و مقدارهای خانوادگی درست ثبت شده‌اند",
      student_id_ok is not None and profiles_ok == 1 and family_ok == 1
      and len(ok_msgs) == 1 and ok_msgs[0][0] == "info"
      and family_row is not None and family_row["siblings_brothers"] == 2
      and family_row["siblings_sisters"] == 1,
      f"student={student_id_ok} profiles={profiles_ok} family={family_ok} msgs={[(k, v[:30]) for k, v in ok_msgs]}")

# --- B4: صفحهٔ دانش‌آموزان: بدون پیام تکراری و با «یک» تازه‌سازی
page = StudentsPage()
load_calls = []
real_load = page.load_students
page.load_students = lambda *a, **k: (load_calls.append(1), real_load(*a, **k))[1]


class _AcceptedForm:
    """جانشین فرم که فقط «پذیرفته‌شده» برمی‌گرداند (بدون دیالوگ واقعی)"""

    def __init__(self, *a, **k):
        pass

    def exec(self):
        return QDialog.DialogCode.Accepted


real_form_cls = students_page_mod.StudentForm
students_page_mod.StudentForm = _AcceptedForm
page_messages_before = len(message_log)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        page.add_student()
        page.edit_student(object())
finally:
    students_page_mod.StudentForm = real_form_cls
page_msgs = message_log[page_messages_before:]
add_edit_src = (read("views/pages/students_page.py")
                .split("def add_student", 1)[1]
                .split("def delete_student", 1)[0])
check("B",
      "بند ۱۳: مسیر «افزودن/ویرایش» صفحهٔ دانش‌آموزان پس از پذیرش فرم هیچ پیام موفقیت دیگری نشان نمی‌دهد (پیام فقط یک لایه: فرم) و فهرست برای هر عملیات «دقیقاً یک بار» تازه می‌شود",
      not any(kind == "info" for kind, _ in page_msgs)
      and load_calls.count(1) == 2
      and add_edit_src.count("QMessageBox.information") == 0,
      f"msgs={[k for k, _ in page_msgs]} loads={len(load_calls)} info_in_source={add_edit_src.count('QMessageBox.information')}")

# --- B5: نتیجهٔ واقعی UPDATE بررسی می‌شود (رکورد ناموجود/حذف‌شده)
missing_student = Student()
missing_student.id = 999999
missing_student.first_name = "ناموجود"
missing_student.last_name = "ناموجود"
missing_student.is_active = 1
with contextlib.redirect_stdout(io.StringIO()):
    update_result = StudentDAL().update(missing_student)
deleted_target = StudentDAL().get_by_id(student_id_ok)
StudentDAL().delete(student_id_ok)
with contextlib.redirect_stdout(io.StringIO()):
    update_deleted = StudentDAL().update(deleted_target)
StudentDAL().restore(student_id_ok)
check("B",
      "بند ۱۳ (نتیجهٔ update): به‌روزرسانی رکورد ناموجود یا حذف‌شده دیگر «موفقیت» جا زده نمی‌شود؛ DAL مقدار None برمی‌گرداند و رکورد معتبر همچنان مدل را می‌گیرد",
      update_result is None and update_deleted is None
      and StudentDAL().update(deleted_target) is not None,
      f"missing={update_result} deleted={update_deleted}")

# --- B6: سرویس دانش‌آموز هم نبودِ اثر را به خطای روشن تبدیل می‌کند
from services.student_service import StudentService
from utils.error_handler import ServiceError

service_error = None
try:
    with contextlib.redirect_stdout(io.StringIO()):
        StudentService().update_student(999999, {"first_name": "الف"})
except ServiceError as e:
    service_error = e
except Exception as e:  # pragma: no cover - مسیر غیرمنتظره
    service_error = e
check("B",
      "سرویس دانش‌آموز: ویرایش رکورد ناموجود پیام روشن فارسی می‌دهد (نه موفقیت و نه AttributeError مبهم) و همان خطا به فراخوان می‌رسد",
      isinstance(service_error, ServiceError)
      and "یافت نشد" in str(service_error),
      f"error={service_error!r}")

# --- B7: هیچ استثنای بی‌صدایی در مسیرهای بحرانی نمانده
CRITICAL_DIRS = ("dal", "services", "database", "views/pages", "views/dialogs", "views/widgets")
ALLOWED_SILENT = {
    # (فایل، شمارهٔ خط) موارد مستندشدهٔ غیربحرانی
    "utils/logger.py",
    "utils/persian_calendar.py",
    "views/widgets/help_widget.py",
}
silent_hits = []
for py in pathlib.Path(".").rglob("*.py"):
    text = str(py)
    if ".venv" in text or text.startswith(("verify_fixes", "tests/")):
        continue
    try:
        tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:  # pragma: no cover
        continue
    for node in ast.walk(tree):
        if (isinstance(node, ast.ExceptHandler) and len(node.body) == 1
                and isinstance(node.body[0], ast.Pass)):
            silent_hits.append((text, node.lineno))
critical_hits = [h for h in silent_hits
                 if h[0].startswith(CRITICAL_DIRS) and h[0] not in ALLOWED_SILENT]
unexpected_non_critical = [h for h in silent_hits
                           if not h[0].startswith(CRITICAL_DIRS)
                           and h[0] not in ALLOWED_SILENT]
check("B",
      "بند ۳۴: هیچ «except: pass» در لایه‌های بحرانی (dal/services/database/views) نمانده و موارد باقی‌مانده در ابزارهای غیربحرانی هم دقیقاً همان‌های مستندشده‌اند (هر بلع خاموش تازه، آزمون را می‌شکند)",
      not critical_hits and not unexpected_non_critical
      and len(silent_hits) <= 7,
      f"critical={critical_hits} unexpected={unexpected_non_critical} all={silent_hits}")

# --- B8: ویرایش دانش‌آموز در حالت فعال، پروندهٔ سال‌های دیگر را دست نمی‌زند
other_year = AcademicYear()
other_year.title = "1498-1499"
other_year.start_date = "1498/07/01"
other_year.end_date = "1499/06/30"
other_year.is_active = 0
other_year.is_archived = 0
with contextlib.redirect_stdout(io.StringIO()):
    other_year = AcademicYearDAL().create(other_year)

from dal.student_academic_profile_dal import StudentAcademicProfileDAL
from models.student_academic_profile import StudentAcademicProfile

profile_dal = StudentAcademicProfileDAL()
historical = StudentAcademicProfile()
historical.student_id = student_id_ok
historical.academic_year_id = other_year.id
historical.grade = 3
historical.class_name = "سوم-الف"
historical.status = StudentAcademicProfile.STATUS_ACTIVE
with contextlib.redirect_stdout(io.StringIO()):
    historical = profile_dal.create(historical)

student_row = StudentDAL().get_by_id(student_id_ok)
form_edit = StudentForm(student=student_row, parent=None)
form_edit.class_input.setText("دهم-ب")
with contextlib.redirect_stdout(io.StringIO()):
    form_edit.save_student()
hist_after = profile_dal.get_by_student_and_year(student_id_ok, other_year.id)
check("B",
      "ویرایش دانش‌آموز فقط پروندهٔ «سال فعال» را به‌روز می‌کند و پروندهٔ سال دیگر (پایه/کلاس/شناسه) دست‌نخورده می‌ماند",
      hist_after is not None and hist_after.id == historical.id
      and hist_after.grade == 3 and hist_after.class_name == "سوم-الف"
      and hist_after.academic_year_id == other_year.id,
      f"hist={None if hist_after is None else (hist_after.id, hist_after.grade, hist_after.class_name, hist_after.academic_year_id)} expected=({historical.id}, 3, سوم-الف, {other_year.id})")

QMessageBox.information = real_info
QMessageBox.critical = real_crit
QMessageBox.warning = real_warn

# ============================================================
print()
print("=" * 76)
print("بخش C: مرحلهٔ ۳ — مسیر بازیابی service+UI و آزمون‌های یکپارچه (بندهای ۳، ۳۸، ۳۹)")
print("=" * 76)

import re

from PySide6.QtWidgets import QPushButton

from dal.counseling_session_dal import CounselingSessionDAL
from dal.extracurricular_dal import ExtracurricularDAL
from dal.goal_dal import GoalDAL
from dal.staff_dal import StaffDAL
from dal.user_dal import UserDAL
from models.staff import Staff
from models.user import User
from services.counseling_service import CounselingService
from services.extracurricular_service import ExtracurricularService
from services.goal_service import GoalService
from views.pages.activities_page import ActivitiesPage
from views.pages.counseling_page import CounselingPage
from views.pages.goals_page import GoalsPage
from views.pages.settings_page import SettingsPage as SettingsPageForUsers

# در این بخش «تأیید» همهٔ پرسش‌ها Yes است و متن‌ها ثبت می‌شوند تا هم مسیر
# تأییدیهٔ واقعی طی شود و هم بتوان بررسی کرد که تأییدیه پرسیده شده است.
question_log = []
real_question = QMessageBox.question
# پیام‌های سه‌گانه هم دوباره جایگزین می‌شوند تا هیچ دیالوگ مدالی اجرای
# بررسی‌ها را قفل نکند؛ متن‌ها در message_log می‌مانند و در همان بررسی
# به‌عنوان شاهد سنجیده می‌شوند.
real_info_c = QMessageBox.information
real_crit_c = QMessageBox.critical
real_warn_c = QMessageBox.warning
QMessageBox.question = staticmethod(
    lambda *a, **k: question_log.append(str(a[2])) or QMessageBox.StandardButton.Yes)
QMessageBox.information = staticmethod(
    lambda *a, **k: message_log.append(("info", str(a[2]))) or QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(
    lambda *a, **k: message_log.append(("crit", str(a[2]))) or QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(
    lambda *a, **k: message_log.append(("warn", str(a[2]))) or QMessageBox.StandardButton.Ok)
message_log.clear()


def _cell_buttons(page, row, column):
    """دکمه‌های همان سلول جدول (مسیر واقعی UI، نه فراخوانی مستقیم متد)"""
    holder = page.table.cellWidget(row, column)
    return list(holder.findChildren(QPushButton)) if holder is not None else []


def _click_restore(page, row, column):
    """کلیک روی دکمهٔ ↩️ همان ردیف؛ برمی‌گرداند دکمهٔ کلیک‌شده یا None"""
    button = next((b for b in _cell_buttons(page, row, column)
                   if b.text() == "↩️"), None)
    if button is not None:
        button.click()
    return button


def _row_of(page, items, entity_id):
    """شمارهٔ ردیف رکورد بر اساس فهرست نمایش‌داده‌شدهٔ همان صفحه"""
    for idx, item in enumerate(items):
        if getattr(item, "id", None) == entity_id:
            return idx
    return None


def _fresh_conn():
    """اتصال تازه (بازیابی، اتصال‌ها را بسته/تازه می‌کند)"""
    return dbc.DatabaseConnection().get_connection(user_id=1)


def _db_flag(table, entity_id):
    row = _fresh_conn().execute(
        f"SELECT is_deleted FROM {table} WHERE id = ?", (entity_id,)).fetchone()
    return None if row is None else row[0]


def _profiles_of(student_id):
    rows = _fresh_conn().execute(
        "SELECT id, academic_year_id, grade, class_name FROM student_academic_profiles "
        "WHERE student_id = ? ORDER BY id", (student_id,)).fetchall()
    return [tuple(r) for r in rows]


def _year_profile_count(year_id):
    return _fresh_conn().execute(
        "SELECT COUNT(*) FROM student_academic_profiles WHERE academic_year_id = ?",
        (year_id,)).fetchone()[0]


# --- C1: هر چهار صفحه مسیر بازیابی دارند و از «سرویس» رد می‌شوند، نه DAL
RESTORE_PAGES = ("students_page", "activities_page", "goals_page", "counseling_page")
page_wiring = {}
for page_name in RESTORE_PAGES:
    src = read(f"views/pages/{page_name}.py")
    page_wiring[page_name] = {
        "checkbox": "make_show_deleted_checkbox" in src,
        "button": src.count("make_restore_button(") == 1,
        "guarded": "if self.showing_deleted:" in src,
        "via_service": bool(re.search(r"_service\.restore_\w+\(", src)),
        "no_dal_direct": not re.search(r"_dal\.restore\(", src),
        "confirm": "ask_restore_confirmation" in src,
        "failure": "report_restore_failure" in src,
    }
check("C",
      "BUG-RESTORE-01/05/06/07: هر چهار صفحهٔ دانش‌آموز/فعالیت/هدف/مشاوره چک‌باکس «نمایش حذف‌شده‌ها»، دکمهٔ ↩️ (فقط در حالت حذف‌شده)، تأییدیه و گزارش خطای واقعی دارند و بازیابی را از «سرویس» می‌گیرند؛ هیچ صفحه‌ای مستقیم به DAL.restore نمی‌زند",
      all(all(w.values()) for w in page_wiring.values()),
      str({k: v for k, v in page_wiring.items() if not all(v.values())}))

# --- C2: صفحهٔ دانش‌آموزان — فهرست حذف‌شده‌ها و ↩️ واقعی
spage = StudentsPage()
profiles_before = _profiles_of(student_id_ok)
with contextlib.redirect_stdout(io.StringIO()):
    StudentDAL().delete(student_id_ok, 1)

spage.show_deleted_check.setChecked(True)
deleted_ids = [s.id for s in spage.all_students]
row = _row_of(spage, spage.students, student_id_ok)
name_cell = spage.table.item(row, 2).text() if row is not None else None
row_labels = [b.text() for b in _cell_buttons(spage, row, 6)] if row is not None else []
check("C",
      "صفحهٔ دانش‌آموزان: تیک «نمایش حذف‌شده‌ها» فقط رکوردهای واقعاً حذف‌شده (طبق دیتابیس) را می‌آورد، ردیف با برچسب «(حذف‌شده)» دیده می‌شود و به‌جای ویرایش/حذف فقط دکمهٔ ↩️ دارد",
      spage.showing_deleted
      and student_id_ok in deleted_ids
      and all(_db_flag("students", i) == 1 for i in deleted_ids)
      and row is not None and bool(name_cell) and name_cell.endswith("(حذف‌شده)")
      and row_labels == ["↩️"],
      f"deleted={len(deleted_ids)} row={row} name={name_cell} buttons={row_labels}")

messages_before = len(message_log)
clicked = _click_restore(spage, row, 6) if row is not None else None
app.processEvents()
restore_msgs = message_log[messages_before:]
profiles_after = _profiles_of(student_id_ok)
check("C",
      "بازیابی از دکمهٔ ↩️ صفحهٔ دانش‌آموزان واقعاً در دیتابیس اثر می‌کند (is_deleted=0)، تأییدیه پرسیده می‌شود، «دقیقاً یک» پیام موفقیت می‌آید، فهرست حذف‌شده‌ها کوچک می‌شود و پروندهٔ سال‌های دیگر (شناسه/سال/پایه/کلاس) دست‌نخورده می‌ماند",
      clicked is not None and _db_flag("students", student_id_ok) == 0
      and question_log and "بازیابی شود" in question_log[-1]
      and len([m for m in restore_msgs if m[0] == "info"]) == 1
      and not [m for m in restore_msgs if m[0] == "crit"]
      and profiles_after == profiles_before
      and student_id_ok not in [s.id for s in spage.all_students],
      f"btn={None if clicked is None else clicked.text()} flag={_db_flag('students', student_id_ok)} "
      f"msgs={[k for k, _ in restore_msgs]} before={len(profiles_before)} after={len(profiles_after)}")

# --- C3: جست‌وجو در حالت حذف‌شده‌ها همان فهرست را فیلتر می‌کند (نه فهرست فعال)
with contextlib.redirect_stdout(io.StringIO()):
    victim_a = StudentService().create_student({
        "first_name": "یکتاآزمون", "last_name": "الف", "national_code": "1799999701",
        "grade": 1}, user_id=1)
    victim_b = StudentService().create_student({
        "first_name": "دیگرآزمون", "last_name": "بهرام", "national_code": "1799999702",
        "grade": 2}, user_id=1)
    StudentService().delete_student(victim_a.id, user_id=1)
    StudentService().delete_student(victim_b.id, user_id=1)

spage.search_input.setText("یکتاآزمون")
spage.search_students()
search_ids = [s.id for s in spage.all_students]
spage.search_input.clear()
spage.load_students()
all_deleted_ids = [s.id for s in spage.all_students]
spage.search_input.setText("سارا")
spage.search_students()
active_looking_ids = [s.id for s in spage.all_students]
spage.search_input.clear()
spage.load_students()
active_ids = {s.id for s in StudentDAL().get_all()}
check("C",
      "جست‌وجو در حالت «نمایش حذف‌شده‌ها» روی همان فهرست حذف‌شده انجام می‌شود (فهرست فعال جای آن را نمی‌گیرد)، دانش‌آموز فعالِ هم‌نام وارد مسیر بازیابی نمی‌شود و پاک‌کردن جست‌وجو فهرست کامل حذف‌شده‌ها را برمی‌گرداند",
      search_ids == [victim_a.id]
      and victim_a.id in all_deleted_ids and victim_b.id in all_deleted_ids
      and not (set(all_deleted_ids) & active_ids)
      and student_id_ok not in active_looking_ids
      and not (set(active_looking_ids) & active_ids),
      f"search={search_ids} named_active={active_looking_ids} deleted={len(all_deleted_ids)} "
      f"overlap={sorted(set(all_deleted_ids) & active_ids)}")

# --- C4..C6: مسیر بازیابی فعالیت/هدف/مشاوره در صفحه‌های واقعی
active_year = AcademicYearDAL().get_active()
current_profile = profile_dal.get_by_student_and_year(student_id_ok, active_year.id)
if current_profile is None:  # pragma: no cover - پیش‌شرط آزمون
    current_profile = profile_dal.get_by_student_and_year(student_id_ok, other_year.id)
profile_id_c = current_profile.id

staff_c = Staff()
staff_c.full_name = "مشاور آزمون بازیابی"
staff_c.role = "مشاور"
with contextlib.redirect_stdout(io.StringIO()):
    staff_c = StaffDAL().create(staff_c)

with contextlib.redirect_stdout(io.StringIO()):
    activity = ExtracurricularService().create_activity({
        "student_profile_id": profile_id_c,
        "title": "المپیاد آزمایشی",
        "type": "scientific",
        "start_date": "1404/01/05",
        "status": "planned",
    }, user_id=1)
    ExtracurricularService().delete_activity(activity.id, user_id=1)
activity_page = ActivitiesPage()
activity_page.show_deleted_check.setChecked(True)
activity_row = _row_of(activity_page, activity_page.visible_activities, activity.id)
activity_label = (activity_page.table.item(activity_row, 2).text()
                  if activity_row is not None else None)
before_msgs = len(message_log)
activity_btn = _click_restore(activity_page, activity_row, 7) \
    if activity_row is not None else None
app.processEvents()
activity_msgs = message_log[before_msgs:]
stored_activity = ExtracurricularDAL().get_by_id(activity.id, include_deleted=True)
check("C",
      "BUG-RESTORE-05: صفحهٔ فعالیت‌ها رکورد حذف‌شده را با برچسب «(حذف‌شده)» نشان می‌دهد و کلیک ↩️ آن را واقعاً بازیابی می‌کند (پروندهٔ سالانهٔ فعالیت همان می‌ماند)",
      activity_row is not None and bool(activity_label)
      and activity_label.endswith("(حذف‌شده)")
      and activity_btn is not None and stored_activity is not None
      and getattr(stored_activity, "is_deleted", 1) == 0
      and stored_activity.student_profile_id == profile_id_c
      and len([m for m in activity_msgs if m[0] == "info"]) == 1
      and not [m for m in activity_msgs if m[0] == "crit"],
      f"row={activity_row} label={activity_label} btn={None if activity_btn is None else activity_btn.text()} "
      f"flag={getattr(stored_activity, 'is_deleted', None)} "
      f"profile={getattr(stored_activity, 'student_profile_id', None)} "
      f"msgs={[k for k, _ in activity_msgs]}")

with contextlib.redirect_stdout(io.StringIO()):
    goal = GoalService().create_goal({
        "student_profile_id": profile_id_c,
        "title": "هدف آزمایشی بازیابی",
        "domain": "educational",
        "priority": "low",
        "start_date": "1404/01/05",
    }, user_id=1)
    GoalService().delete_goal(goal.id, user_id=1)
goal_page = GoalsPage()
goal_page.show_deleted_check.setChecked(True)
goal_row = _row_of(goal_page, goal_page.visible_goals, goal.id)
goal_label = goal_page.table.item(goal_row, 2).text() if goal_row is not None else None
before_msgs = len(message_log)
goal_btn = _click_restore(goal_page, goal_row, 6) if goal_row is not None else None
app.processEvents()
goal_msgs = message_log[before_msgs:]
stored_goal = GoalDAL().get_by_id(goal.id, include_deleted=True)
check("C",
      "BUG-RESTORE-06: صفحهٔ اهداف همان قرارداد را اجرا می‌کند — هدف حذف‌شده دیده می‌شود، ↩️ واقعاً بازیابی می‌کند و پروندهٔ سالانهٔ هدف تغییر نمی‌کند",
      goal_row is not None and bool(goal_label) and goal_label.endswith("(حذف‌شده)")
      and goal_btn is not None and stored_goal is not None
      and getattr(stored_goal, "is_deleted", 1) == 0
      and stored_goal.student_profile_id == profile_id_c
      and len([m for m in goal_msgs if m[0] == "info"]) == 1
      and not [m for m in goal_msgs if m[0] == "crit"],
      f"row={goal_row} label={goal_label} btn={None if goal_btn is None else goal_btn.text()} "
      f"flag={getattr(stored_goal, 'is_deleted', None)} msgs={[k for k, _ in goal_msgs]}")

with contextlib.redirect_stdout(io.StringIO()):
    session = CounselingService().create_session({
        "student_profile_id": profile_id_c,
        "counselor_id": staff_c.id,
        "session_date": "1404/01/06",
        "type": "individual",
        "topic": "جلسهٔ آزمایشی بازیابی",
    }, user_id=1)
    CounselingService().delete_session(session.id, user_id=1)
counsel_page = CounselingPage()
counsel_page.show_deleted_check.setChecked(True)
session_row = _row_of(counsel_page, counsel_page.visible_sessions, session.id)
session_label = (counsel_page.table.item(session_row, 2).text()
                 if session_row is not None else None)
before_msgs = len(message_log)
session_btn = _click_restore(counsel_page, session_row, 6) \
    if session_row is not None else None
app.processEvents()
session_msgs = message_log[before_msgs:]
stored_session = CounselingSessionDAL().get_by_id(session.id, include_deleted=True)
check("C",
      "BUG-RESTORE-07: صفحهٔ مشاوره همان قرارداد را اجرا می‌کند — جلسهٔ حذف‌شده دیده می‌شود، ↩️ واقعاً بازیابی می‌کند و پروندهٔ سالانهٔ جلسه تغییر نمی‌کند",
      session_row is not None and bool(session_label)
      and session_label.endswith("(حذف‌شده)")
      and session_btn is not None and stored_session is not None
      and getattr(stored_session, "is_deleted", 1) == 0
      and stored_session.student_profile_id == profile_id_c
      and len([m for m in session_msgs if m[0] == "info"]) == 1
      and not [m for m in session_msgs if m[0] == "crit"],
      f"row={session_row} label={session_label} btn={None if session_btn is None else session_btn.text()} "
      f"flag={getattr(stored_session, 'is_deleted', None)} msgs={[k for k, _ in session_msgs]}")

# --- C7: IT-RESTORE-YEAR-01 با فرم و صفحهٔ واقعی: حذف → بازیابی → تغییر سال → ویرایش
year_1403 = AcademicYearDAL().get_active()
it_code = "1799999710"
it_form = _fill_form(StudentForm(parent=None), it_code, "نیلوفر", "یکپارچه")
grade_index_3 = next((i for i in range(it_form.grade_combo.count())
                      if it_form.grade_combo.itemData(i) == 3), None)
if grade_index_3 is not None:
    it_form.grade_combo.setCurrentIndex(grade_index_3)
it_form.class_input.setText("سوم-الف")
with contextlib.redirect_stdout(io.StringIO()):
    it_form.save_student()
it_student_id = _rows_for(it_code)[0]
it_profile_1403 = profile_dal.get_by_student_and_year(it_student_id, year_1403.id)

it_victim = StudentDAL().get_by_id(it_student_id)
with contextlib.redirect_stdout(io.StringIO()):
    spage.delete_student(it_victim)
if not spage.show_deleted_check.isChecked():
    spage.show_deleted_check.setChecked(True)
it_row = _row_of(spage, spage.students, it_student_id)
it_btn = _click_restore(spage, it_row, 6) if it_row is not None else None
app.processEvents()

year_1404 = AcademicYear()
year_1404.title = "1502-1503"
year_1404.start_date = "1502/07/01"
year_1404.end_date = "1503/06/30"
year_1404.is_active = 0
year_1404.is_archived = 0
with contextlib.redirect_stdout(io.StringIO()):
    year_1404 = AcademicYearDAL().create(year_1404)
AcademicYearDAL().set_active(year_1404.id)

it_edit = StudentForm(student=StudentDAL().get_by_id(it_student_id), parent=None)
grade_index_4 = next((i for i in range(it_edit.grade_combo.count())
                      if it_edit.grade_combo.itemData(i) == 4), None)
if grade_index_4 is not None:
    it_edit.grade_combo.setCurrentIndex(grade_index_4)
it_edit.class_input.setText("چهارم-ب")
with contextlib.redirect_stdout(io.StringIO()):
    it_edit.save_student()

it_old_after = profile_dal.get_by_student_and_year(it_student_id, year_1403.id)
it_new_after = profile_dal.get_by_student_and_year(it_student_id, year_1404.id)
it_profiles = _profiles_of(it_student_id)
check("C",
      "§۳۸ (IT-RESTORE-YEAR-01): حذف از صفحه، بازیابی با ↩️، تغییر سال فعال و ویرایش با فرم واقعی — پروندهٔ ۱۴۰۳ (شناسه/سال/پایه/کلاس) دست‌نخورده می‌ماند، پروندهٔ ۱۴۰۴ ساخته می‌شود و رکورد تاریخی به سال جدید منتقل نمی‌شود",
      it_btn is not None and _db_flag("students", it_student_id) == 0
      and it_profile_1403 is not None and it_old_after is not None
      and it_old_after.id == it_profile_1403.id
      and it_old_after.academic_year_id == year_1403.id
      and it_old_after.grade == 3 and it_old_after.class_name == "سوم-الف"
      and it_new_after is not None and it_new_after.academic_year_id == year_1404.id
      and it_new_after.grade == 4 and it_new_after.class_name == "چهارم-ب"
      and len(it_profiles) == 2,
      f"btn={None if it_btn is None else it_btn.text()} profiles={it_profiles} "
      f"old={(None if it_old_after is None else (it_old_after.id, it_old_after.grade, it_old_after.class_name))} "
      f"new={(None if it_new_after is None else (it_new_after.id, it_new_after.grade, it_new_after.class_name))}")

# --- C8: IT-YEAR-CRUD-01 — جدایی کامل دادهٔ سال‌ها در حذف/بازیابی/ویرایش
sara_before = _profiles_of(student_id_ok)
counts_before = {y: _year_profile_count(y) for y in (year_1403.id, year_1404.id)}

with contextlib.redirect_stdout(io.StringIO()):
    StudentService().delete_student(it_student_id, user_id=1)
    StudentService().restore_student(it_student_id, user_id=1)
it_profiles_after_cycle = _profiles_of(it_student_id)

sara_edit = StudentForm(student=StudentDAL().get_by_id(student_id_ok), parent=None)
grade_index_5 = next((i for i in range(sara_edit.grade_combo.count())
                      if sara_edit.grade_combo.itemData(i) == 5), None)
if grade_index_5 is not None:
    sara_edit.grade_combo.setCurrentIndex(grade_index_5)
sara_edit.class_input.setText("پنجم-الف")
with contextlib.redirect_stdout(io.StringIO()):
    sara_edit.save_student()
sara_after = _profiles_of(student_id_ok)
sara_1403_after = [p for p in sara_after if p[1] == year_1403.id]
sara_1403_before = [p for p in sara_before if p[1] == year_1403.id]
check("C",
      "§۳۹ (IT-YEAR-CRUD-01): دو دانش‌آموز در دو سال — چرخهٔ حذف/بازیابی یکی و ویرایش دیگری، دادهٔ سال‌های دیگر را تغییر نمی‌دهد؛ پروندهٔ ۱۴۰۳ هر دو دانش‌آموز دست‌نخورده می‌ماند و پروندهٔ تازه فقط در سال فعال ساخته می‌شود",
      it_profiles_after_cycle == it_profiles
      and sara_1403_after == sara_1403_before
      and len(sara_after) == len(sara_before) + 1
      and any(p[1] == year_1404.id and p[2] == 5 and p[3] == "پنجم-الف"
              for p in sara_after)
      and _year_profile_count(year_1404.id) == counts_before[year_1404.id] + 1
      and _db_flag("students", it_student_id) == 0,
      f"it_profiles={it_profiles_after_cycle} sara_before={sara_before} sara_after={sara_after} "
      f"counts_before={counts_before} now={_year_profile_count(year_1404.id)}")

# --- C9: BUG-RESTORE-02 — بازگرداندن کاربر در صفحهٔ تنظیمات (آزمون یکپارچه)
restore_user = User()
restore_user.staff_id = staff_c.id
restore_user.username = "restore_check_user"
restore_user.role = "teacher"
restore_user.is_active = 1
with contextlib.redirect_stdout(io.StringIO()):
    restore_user = UserDAL().create(restore_user, raw_password="Test@12345",
                                    user_id_actor=1)
with contextlib.redirect_stdout(io.StringIO()):
    deleted_user_ok = UserDAL().delete(restore_user.id, user_id_actor=1)

settings_page_users = SettingsPageForUsers()
before_msgs = len(message_log)
with contextlib.redirect_stdout(io.StringIO()):
    settings_page_users.restore_user({"id": restore_user.id,
                                      "username": restore_user.username})
app.processEvents()
user_msgs = message_log[before_msgs:]
with contextlib.redirect_stdout(io.StringIO()):
    settings_page_users.restore_user({"id": 987654, "username": "کاربرناموجود"})
app.processEvents()
missing_msgs = message_log[before_msgs + len(user_msgs):]
restored_row = _fresh_conn().execute(
    "SELECT is_deleted, is_active, must_change_password FROM users WHERE id = ?",
    (restore_user.id,)).fetchone()
with contextlib.redirect_stdout(io.StringIO()):
    settings_page_users.shutdown_backup_workers()
check("C",
      "BUG-RESTORE-02: بازگرداندن کاربر از صفحهٔ تنظیمات واقعاً کار می‌کند (is_deleted=0، حساب فعال، اجبار تغییر رمز) و پیام موفقیت فقط در همین حالت می‌آید؛ شناسهٔ ناموجود پیام «یافت نشد» می‌گیرد و موفقیت جا زده نمی‌شود",
      deleted_user_ok and restored_row is not None
      and tuple(restored_row) == (0, 1, 1)
      and len([m for m in user_msgs if m[0] == "info"]) == 1
      and not [m for m in user_msgs if m[0] == "crit"]
      and not [m for m in missing_msgs if m[0] == "info"]
      and [m for m in missing_msgs if m[0] == "warn"],
      f"row={None if restored_row is None else tuple(restored_row)} "
      f"ok_msgs={[k for k, _ in user_msgs]} missing_msgs={[k for k, _ in missing_msgs]}")

# --- C10: capabilityهای باقی‌ماندهٔ بازیابی، عمداً در سطح backend (مستندشده)
backend_only = {}
for module_name in ("observation_dal", "intervention_dal", "followup_dal"):
    dal_src = read(f"dal/{module_name}.py")
    service_src = read(f"services/{module_name.replace('_dal', '_service')}.py")
    backend_only[module_name] = ("def restore(" in dal_src
                                 and "def restore_" not in service_src)
page_has_deleted_view = {
    page_name: ("make_show_deleted_checkbox" in read(f"views/pages/{page_name}.py")
                or "make_restore_button" in read(f"views/pages/{page_name}.py"))
    for page_name in ("observations_page", "interventions_page", "followups_page")
}
check("C",
      "بند ۰-۶: وضعیت «DAL.restore بدون مسیر سرویس/UI» برای مشاهدات/مداخلات/پیگیری‌ها صریح و محدود است — هیچ صفحه‌ای کنترل بازیابی نیمه‌کاره (بدون backend) ندارد و این سه مورد به‌عنوان capability داخلی مستند می‌شوند",
      all(backend_only.values()) and not any(page_has_deleted_view.values()),
      f"backend_only={backend_only} pages={page_has_deleted_view}")

QMessageBox.question = real_question
QMessageBox.information = real_info_c
QMessageBox.critical = real_crit_c
QMessageBox.warning = real_warn_c

# ============================================================
print()
print("=" * 76)
print("بخش D: مرحلهٔ ۴ — درستی ایمپورت/خروجی/صفحه‌بندی/جست‌وجو (بندهای ۱۴، ۱۵، ۱۶، ۱۷، ۱۹)")
print("=" * 76)

import openpyxl
from PySide6.QtWidgets import QDialog as _QDialog

from dal.followup_dal import FollowUpDAL
from dal.intervention_dal import InterventionDAL
from dal.observation_dal import ObservationDAL
from models.followup import FollowUp
from models.intervention import Intervention
from models.observation import Observation
from services.observation_service import ObservationService
from utils.excel_importer import ExcelImporter
from views.pages.observations_page import ObservationsPage

# سه پیام دیگر هم باید استاب باشند: مسیرهای مرحلهٔ ۴ (خروجی/ایمپورت) کادر
# «اطلاع»/«خطا» باز می‌کنند و اگر استاب نباشند، اجرای offscreen روی همان
# دیالوگ مدال قفل می‌شود (ترتیب استورها درست بود ولی §C استاب‌ها را
# برگردانده بود).
real_info_d = QMessageBox.information
real_crit_d = QMessageBox.critical
real_warn_d = QMessageBox.warning
QMessageBox.question = staticmethod(
    lambda *a, **k: question_log.append(str(a[2])) or QMessageBox.StandardButton.Yes)
QMessageBox.information = staticmethod(
    lambda *a, **k: message_log.append(("info", str(a[2]))) or QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(
    lambda *a, **k: message_log.append(("crit", str(a[2]))) or QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(
    lambda *a, **k: message_log.append(("warn", str(a[2]))) or QMessageBox.StandardButton.Ok)


def _year(title, start, end, make_active=True):
    """ساخت سال تحصیلی تازه (بدون دست‌زدن به سال‌های دیگر)"""
    year = AcademicYear()
    year.title = title
    year.start_date = start
    year.end_date = end
    year.is_active = 0
    year.is_archived = 0
    with contextlib.redirect_stdout(io.StringIO()):
        year = AcademicYearDAL().create(year)
    if make_active:
        AcademicYearDAL().set_active(year.id)
    return year


def _student_direct(first_name, last_name, national_code):
    student = Student()
    student.first_name = first_name
    student.last_name = last_name
    student.national_code = national_code
    student.is_active = 1
    with contextlib.redirect_stdout(io.StringIO()):
        return StudentDAL().create(student)


def _profile_direct(student_id, year_id, grade=1, class_name=""):
    profile = StudentAcademicProfile()
    profile.student_id = student_id
    profile.academic_year_id = year_id
    profile.grade = grade
    profile.class_name = class_name
    profile.status = StudentAcademicProfile.STATUS_ACTIVE
    with contextlib.redirect_stdout(io.StringIO()):
        return StudentAcademicProfileDAL().create(profile)


# --- D1: ماتریس صفحه‌بندی (N=0/1/20/21/40/41/100) و نبود سقف ۱۰۰
# دانش‌آموزان ساختهٔ بخش‌های پیشین موقتاً حذف منطقی می‌شوند تا شمارش
# صفحه‌بندی فقط به فیکسچر همین بخش وابسته باشد (شمارش ۱۵۰ باید دقیق باشد).
with contextlib.redirect_stdout(io.StringIO()):
    _preexisting_conn = _fresh_conn()
    _preexisting_ids = [r[0] for r in _preexisting_conn.execute(
        "SELECT id FROM students WHERE is_deleted = 0").fetchall()]
    _preexisting_conn.execute("UPDATE students SET is_deleted = 1")
    _preexisting_conn.commit()

page_years = [r[0] for r in _fresh_conn().execute(
    "SELECT id FROM academic_years WHERE is_active = 1").fetchall()]
paged_students = [_student_direct(f"صفحه{i:03d}", "آزمون‌بندی", f"{4000000000 + i}")
                  for i in range(150)]
for student in paged_students:
    _profile_direct(student.id, page_years[0], grade=1, class_name="اول-الف")

matrix = {}
pagination_page = StudentsPage()
pagination_page.show_deleted_check.setChecked(False)
pagination_page.page_size_combo.setCurrentText("20")
for page_size in (10, 20, 50, 100):
    pagination_page.page_size_combo.setCurrentText(str(page_size))
    total = len(pagination_page.all_students)
    total_pages = pagination_page.total_pages
    pagination_page.current_page = total_pages - 1
    pagination_page.load_students()
    matrix[page_size] = (total, total_pages, pagination_page.current_page,
                         len(pagination_page.students),
                         pagination_page.next_page_btn.isEnabled())
check("D",
      "بند ۱۶ (ماتریس Pagination): با ۱۵۰ دانش‌آموز، تعداد صفحه‌ها و ردیف صفحهٔ آخر برای هر گزینهٔ اندازهٔ صفحه درست است (۱۰→۱۵ صفحه/۱۰ ردیف، ۲۰→۸/۱۰، ۵۰→۳/۵۰، ۱۰۰→۲/۵۰) و در صفحهٔ آخر «بعدی» غیرفعال می‌شود",
      matrix[10][:4] == (150, 15, 14, 10)
      and matrix[20][:4] == (150, 8, 7, 10)
      and matrix[50][:4] == (150, 3, 2, 50)
      and matrix[100][:4] == (150, 2, 1, 50)
      and all(not v[4] for v in matrix.values()),
      f"matrix={matrix}")

# --- D2: N=0/1/20/21/40/41 — صفحه‌بندی روی فهرست‌های کوچک و مرزی
edge_counts = {}
pagination_page.search_input.clear()
pagination_page.show_deleted_check.setChecked(False)
for count in (0, 1, 20, 21, 40, 41):
    # در هر تکرار دقیقاً «count» دانش‌آموز فعال می‌ماند و بقیهٔ فیکسچر حذف
    # منطقی می‌شود؛ بنابراین شمارش صفحه‌بندی قطعی و مستقل است.
    with contextlib.redirect_stdout(io.StringIO()):
        fresh_conn = _fresh_conn()
        fresh_conn.execute(
            "UPDATE students SET is_deleted = 1 WHERE id IN (%s)"
            % ",".join("?" * len(paged_students)), [s.id for s in paged_students])
        if count:
            fresh_conn.execute(
                "UPDATE students SET is_deleted = 0 WHERE id IN (%s)"
                % ",".join("?" * count),
                [s.id for s in paged_students[:count]])
        fresh_conn.commit()
    pagination_page.page_size_combo.setCurrentText("20")
    # بازخوانی صریح: تغییر کامبو اگر مقدارش عوض نشده باشد سیگنالی نمی‌فرستد
    # و فهرست صفحه از تکرار قبلی می‌ماند.
    pagination_page.current_page = 0
    pagination_page.load_students()
    total = len(pagination_page.all_students)
    pages = pagination_page.total_pages
    first_page_rows = len(pagination_page.students)
    pagination_page.current_page = max(0, pages - 1)
    pagination_page.load_students()
    last_page_rows = len(pagination_page.students)
    edge_counts[count] = (total, pages, first_page_rows, last_page_rows,
                          pagination_page.page_label.text())
    pagination_page.current_page = 999          # کلمپ صفحهٔ خارج از محدوده
    pagination_page.load_students()
    edge_counts[count] = edge_counts[count] + (pagination_page.current_page,)

# بازگردانی دانش‌آموزان برای بررسی‌های بعدی
with contextlib.redirect_stdout(io.StringIO()):
    fresh_conn = _fresh_conn()
    fresh_conn.execute(
        "UPDATE students SET is_deleted = 0 WHERE id IN (%s)"
        % ",".join("?" * len(paged_students)),
        [s.id for s in paged_students])
    fresh_conn.commit()
pagination_page.load_students()
check("D",
      "بند ۱۶ (N=۰/۱/۲۰/۲۱/۴۰/۴۱): تعداد صفحه و ردیف‌های اولین/آخرین صفحه در همهٔ حالت‌ها درست است، لیست خالی پیام «صفحه ۱ از ۱» می‌دهد و شمارهٔ صفحهٔ خارج از محدوده به صفحهٔ معتبر کلمپ می‌شود (کرش/صفحهٔ خالی بی‌دلیل نمی‌دهد)",
      edge_counts[0][:5] == (0, 0, 0, 0, "صفحه 1 از 1")
      and edge_counts[1][:4] == (1, 1, 1, 1)
      and edge_counts[20][:4] == (20, 1, 20, 20)
      and edge_counts[21][:4] == (21, 2, 20, 1)
      and edge_counts[40][:4] == (40, 2, 20, 20)
      and edge_counts[41][:4] == (41, 3, 20, 1)
      and all(values[5] == max(0, values[1] - 1) for values in edge_counts.values()),
      f"edges={edge_counts}")

# --- D3: خروجی «همهٔ بارگذاری‌شده‌ها» از صفحهٔ چندصفحه‌ای (نه صفحهٔ جاری)
export_path = os.path.join(TMP, "ui_export_all.xlsx")
real_save_dialog = QFileDialog.getSaveFileName
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (export_path, "xlsx"))
pagination_page.page_size_combo.setCurrentText("20")
pagination_page.current_page = 0
pagination_page.load_students()
visible_rows = len(pagination_page.students)
messages_before = len(message_log)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        pagination_page.export_to_excel()
finally:
    QFileDialog.getSaveFileName = real_save_dialog
export_msgs = message_log[messages_before:]
exported_sheet = openpyxl.load_workbook(export_path).active
exported_rows = [row for row in exported_sheet.iter_rows(values_only=True)
                 if row and isinstance(row[0], int)]
check("D",
      "بند ۱۵ (BUG-GUI-03): خروجی Excel از صفحهٔ چندصفحه‌ای همهٔ دانش‌آموزان بارگذاری‌شده (۱۵۰) را می‌نویسد، نه فقط ۲۰ ردیف صفحهٔ جاری؛ فایل واقعی xlsx است و پیام موفقیت تعداد واقعی را می‌گوید",
      visible_rows == 20 and len(exported_rows) == 150
      and os.path.exists(export_path) and zipfile.is_zipfile(export_path)
      and len([m for m in export_msgs if m[0] == "info"]) == 1
      and "150" in export_msgs[0][1],
      f"visible={visible_rows} exported={len(exported_rows)} msgs={[m[0] for m in export_msgs]}")

# --- D4: خروجی در حالت «نمایش حذف‌شده‌ها» خودش را حذف‌شده معرفی می‌کند
deleted_export_path = os.path.join(TMP, "ui_export_deleted.xlsx")
# فقط یک رکورد حذف‌شده در دیتابیس باشد تا اعداد خروجی قطعی بمانند
# (دانش‌آموزان بخش‌های پیشین هم به حالت فعال برمی‌گردند).
with contextlib.redirect_stdout(io.StringIO()):
    _reset_conn = _fresh_conn()
    _reset_conn.execute("UPDATE students SET is_deleted = 0")
    _reset_conn.commit()
    StudentDAL().delete(paged_students[0].id, 1)
pagination_page.show_deleted_check.setChecked(True)
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (deleted_export_path, "xlsx"))
try:
    with contextlib.redirect_stdout(io.StringIO()):
        pagination_page.export_to_excel()
finally:
    QFileDialog.getSaveFileName = real_save_dialog
deleted_sheet = openpyxl.load_workbook(deleted_export_path).active
deleted_rows = [row for row in deleted_sheet.iter_rows(values_only=True)
                if row and isinstance(row[0], int)]
deleted_texts = [str(cell.value) for row in deleted_sheet.iter_rows()
                 for cell in row if cell.value]
check("D",
      "بند ۱۵/۱۹: خروجی در حالت «نمایش حذف‌شده‌ها» خودش را «لیست دانش‌آموزان حذف‌شده (سطل بازیافت)» معرفی می‌کند و ردیف وضعیت «حذف‌شده» را دارد — فایلی که خواننده فکر کند دادهٔ فعال است ساخته نمی‌شود",
      len(deleted_rows) == 1
      and "حذف‌شده" in str(deleted_sheet.cell(row=1, column=1).value)
      and any("حذف‌شده (این ردیف‌ها" in text for text in deleted_texts),
      f"rows={len(deleted_rows)} title={deleted_sheet.cell(row=1, column=1).value!r}")
pagination_page.show_deleted_check.setChecked(False)

# --- D5: لغو دیالوگ‌های ایمپورت → هیچ تغییر و هیچ پیام
import views.pages.students_page as students_page_mod

importer_ui = ExcelImporter()
cancel_file = os.path.join(TMP, "cancel.xlsx")
wb_cancel = openpyxl.Workbook()
ws_cancel = wb_cancel.active
ws_cancel.append(["نام", "نام خانوادگی", "کد ملی"])
ws_cancel.append(["لغو", "شده", "5511111111"])
wb_cancel.save(cancel_file)

students_before_cancel = _fresh_conn().execute(
    "SELECT COUNT(*) FROM students").fetchone()[0]
messages_before = len(message_log)
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
try:
    with contextlib.redirect_stdout(io.StringIO()):
        pagination_page.import_from_excel()
finally:
    QFileDialog.getOpenFileName = real_get_open
cancel_msgs = message_log[messages_before:]

real_exec = _QDialog.exec
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (cancel_file, "xlsx"))
_QDialog.exec = lambda self, *a, **k: _QDialog.DialogCode.Rejected
try:
    with contextlib.redirect_stdout(io.StringIO()):
        pagination_page.import_from_excel()
finally:
    _QDialog.exec = real_exec
    QFileDialog.getOpenFileName = real_get_open
rejected_msgs = message_log[messages_before + len(cancel_msgs):]
students_after_cancel = _fresh_conn().execute(
    "SELECT COUNT(*) FROM students").fetchone()[0]
check("D",
      "بند ۱۴ (لغو دیالوگ): لغو انتخاب فایل و لغو دیالوگ سال تحصیلی هیچ رکوردی وارد نمی‌کند و هیچ پیامی هم نشان نمی‌دهد (نه موفقیت، نه خطا) — یعنی عملیات ایمپورت بدون تأیید کاربر اجرا نمی‌شود",
      not cancel_msgs and not rejected_msgs
      and students_after_cancel == students_before_cancel,
      f"cancel={[m[0] for m in cancel_msgs]} rejected={[m[0] for m in rejected_msgs]} "
      f"students={students_before_cancel}->{students_after_cancel}")

# --- D6: ایمپورت از مسیر واقعی UI با فایل مختلط و فایل تمام‌غلط
mixed_file = os.path.join(TMP, "mixed.xlsx")
wb_mixed = openpyxl.Workbook()
ws_mixed = wb_mixed.active
ws_mixed.append(["نام", "نام خانوادگی", "کد ملی", "تاریخ تولد", "پایه", "کلاس"])
ws_mixed.append(["وارد", "شدنی", "5522222222", "1395/01/01", 2, "دوم-الف"])
ws_mixed.append(["کد", "تکراری", "5522222222", "1395/01/01", 2, "دوم-الف"])
ws_mixed.append(["تاریخ", "غلط", "5533333333", "1395/13/45", 2, "دوم-الف"])
wb_mixed.save(mixed_file)

all_bad_file = os.path.join(TMP, "all_bad.xlsx")
wb_bad = openpyxl.Workbook()
ws_bad = wb_bad.active
ws_bad.append(["نام", "نام خانوادگی", "کد ملی"])
ws_bad.append(["", "بدون‌نام", "5544444444"])
wb_bad.save(all_bad_file)


def _run_ui_import(file_path):
    """اجرای واقعی مسیر UI ایمپورت (انتخاب فایل + پذیرش دیالوگ سال)"""
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (file_path, "xlsx"))
    _QDialog.exec = lambda self, *a, **k: _QDialog.DialogCode.Accepted
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            pagination_page.import_from_excel()
    finally:
        _QDialog.exec = real_exec
        QFileDialog.getOpenFileName = real_get_open
    app.processEvents()


active_year_for_import = AcademicYearDAL().get_active()


def _profiles_in_year(year_id):
    return _fresh_conn().execute(
        "SELECT COUNT(*) FROM student_academic_profiles WHERE academic_year_id = ?",
        (year_id,)).fetchone()[0]


count_before_mixed = _profiles_in_year(active_year_for_import.id)
messages_before = len(message_log)
_run_ui_import(mixed_file)
mixed_msgs = message_log[messages_before:]
mixed_ids = [r[0] for r in _fresh_conn().execute(
    "SELECT id FROM students WHERE national_code = '5522222222'").fetchall()]
count_after_mixed = _profiles_in_year(active_year_for_import.id)
mixed_profile_ok = bool(mixed_ids) and _fresh_conn().execute(
    "SELECT COUNT(*) FROM student_academic_profiles WHERE student_id = ? "
    "AND academic_year_id = ?", (mixed_ids[0], active_year_for_import.id)).fetchone()[0] == 1

messages_before = len(message_log)
_run_ui_import(all_bad_file)
bad_msgs = message_log[messages_before:]
check("D",
      "بند ۱۴ (مسیر UI): فایل مختلط → یک ردیف وارد می‌شود و کادر اطلاع «دقیقاً با جزئیات خطاهای همان ردیف‌ها» نشان داده می‌شود؛ فایل تمام‌غلط → کادر «خطای ایمپورت» با علت خطاها (نه پیام موفقیت صفر رکورد) و هیچ رکوردی ساخته نمی‌شود",
      len(mixed_ids) == 1 and mixed_profile_ok
      and count_after_mixed == count_before_mixed + 1
      and len([m for m in mixed_msgs if m[0] == "info"]) == 1
      and "تکراری" in mixed_msgs[0][1] and "معتبر نیست" in mixed_msgs[0][1]
      and len([m for m in bad_msgs if m[0] == "crit"]) == 1
      and "هیچ دانش‌آموزی ایمپورت نشد" in bad_msgs[0][1]
      and not _fresh_conn().execute(
          "SELECT COUNT(*) FROM students WHERE national_code = '5544444444'").fetchone()[0],
      f"mixed_info={mixed_msgs[-1:] and mixed_msgs[0][1][:60]!r} "
      f"mixed_ids={mixed_ids} profile_ok={mixed_profile_ok} "
      f"profiles={count_before_mixed}->{count_after_mixed} bad={[m[0] for m in bad_msgs]}")

# --- D7: فیلتر سال پیش از LIMIT با بیش از ۱۰۰ رکورد در دو سال (مشاهدات/مداخلات/پیگیری‌ها)
year_a = AcademicYearDAL().get_active()
year_b = _year("1510-1511", "1510/07/01", "1511/03/31", make_active=False)

student_two_years = _student_direct("دوساله", "فیلترسال", "5600000001")
profile_a = _profile_direct(student_two_years.id, year_a.id, 1, "اول-الف")
profile_b = _profile_direct(student_two_years.id, year_b.id, 2, "دوم-الف")
filter_staff = Staff()
filter_staff.full_name = "مشاهده‌گر فیلتر سال"
filter_staff.role = "teacher"
with contextlib.redirect_stdout(io.StringIO()):
    filter_staff = StaffDAL().create(filter_staff)

observation_dal = ObservationDAL()
intervention_dal = InterventionDAL()
followup_dal = FollowUpDAL()
for index in range(120):
    for profile, day in ((profile_a, "1403/08/01"), (profile_b, "1404/08/01")):
        observation = Observation()
        observation.student_profile_id = profile.id
        observation.staff_id = filter_staff.id
        observation.observation_date = day
        observation.location = "کلاس"
        observation.behavior = f"رفتار آزمون {index}"
        observation.description = f"شرح مشاهدهٔ آزمون {index}"
        observation.behavior_type = "مثبت"
        observation.severity = 3
        with contextlib.redirect_stdout(io.StringIO()):
            observation_dal.create(observation)

        intervention = Intervention()
        intervention.student_profile_id = profile.id
        intervention.staff_id = filter_staff.id
        intervention.type = "educational"
        intervention.date = day
        intervention.description = f"مداخلهٔ آزمون {index}"
        intervention.status = "in_progress"
        with contextlib.redirect_stdout(io.StringIO()):
            intervention_dal.create(intervention)

        followup = FollowUp()
        followup.intervention_id = intervention.id
        followup.staff_id = filter_staff.id
        followup.date = day
        followup.method = "phone"
        followup.description = f"پیگیری آزمون {index}"
        followup.status = "pending"
        with contextlib.redirect_stdout(io.StringIO()):
            followup_dal.create(followup)

with contextlib.redirect_stdout(io.StringIO()):
    obs_a = ObservationService().get_all_observations(limit=None, year_id=year_a.id)
    obs_b = ObservationService().get_all_observations(limit=None, year_id=year_b.id)
obs_a_limited = observation_dal.get_all(limit=100, academic_year_id=year_a.id)
obs_no_year_limited = observation_dal.get_all(limit=100)
interventions_a_limited = intervention_dal.get_all(limit=100, academic_year_id=year_a.id)
interventions_a_all = intervention_dal.get_all(limit=None, academic_year_id=year_a.id)
followups_a_limited = followup_dal.get_all(limit=100, academic_year_id=year_a.id)
followups_b_limited = followup_dal.get_all(limit=100, academic_year_id=year_b.id)
obs_profiles_a = {o.student_profile_id for o in obs_a_limited}
obs_profiles_no_year = {o.student_profile_id for o in obs_no_year_limited}
check("D",
      "بند ۱۷: «فیلتر سال قبل از LIMIT» با ۲۴۰ رکورد در دو سال — get_all(limit=100, year=۱۴۰۳) دقیقاً ۱۰۰ رکورد «همان سال» می‌دهد، در حالی که همان کوئری بدون فیلتر سال ۱۰۰ رکورد از فقط یک سال (جدیدترین‌ها = ۱۴۰۴) برمی‌گرداند؛ فهرست بدون limit همهٔ ۱۲۰ رکورد سال انتخاب‌شده را می‌دهد و همین قرارداد برای مداخلات و پیگیری‌ها برقرار است",
      len(obs_a) == 120 and len(obs_b) == 120
      and len(obs_a_limited) == 100 and obs_profiles_a == {profile_a.id}
      and len(obs_no_year_limited) == 100
      and obs_profiles_no_year == {profile_b.id}      # بدون فیلتر: سالِ دیگر جای ردیف‌ها را می‌گیرد
      and len(interventions_a_limited) == 100
      and {i.student_profile_id for i in interventions_a_limited} == {profile_a.id}
      and len(interventions_a_all) == 120
      and len(followups_a_limited) == 100 and len(followups_b_limited) == 100,
      f"obs={len(obs_a)}/{len(obs_b)} limited={len(obs_a_limited)} profiles={obs_profiles_a} "
      f"no_year={len(obs_no_year_limited)} profiles_no_year={obs_profiles_no_year} "
      f"interv={len(interventions_a_limited)}/{len(interventions_a_all)} fu={len(followups_a_limited)}/{len(followups_b_limited)}")

# --- D8: صفحهٔ مشاهدات با سال اعلام‌شده → فقط رکوردهای همان سال (نه نشتی سال دیگر)
observations_page = ObservationsPage()
observations_page.set_active_year(year_b.id)
page_b_rows = len(observations_page.observations)
page_b_wrong_year = [o for o in observations_page.observations
                     if o.student_profile_id != profile_b.id]
observations_page.set_active_year(year_a.id)
page_a_rows = len(observations_page.observations)
page_a_wrong_year = [o for o in observations_page.observations
                     if o.student_profile_id != profile_a.id]
check("D",
      "بند ۱۷ + GUI-07: صفحهٔ مشاهدات با سال اعلام‌شده فقط رکوردهای همان سال را نشان می‌دهد (۱۲۰ رکورد سال ۱۴۰۳ و ۱۲۰ رکورد سال ۱۴۰۴، بدون نشتی ردیف سال دیگر) — قبلاً فیلتر سال فقط پس از خواندن داده در پایتون اعمال می‌شد",
      page_a_rows == 120 and page_b_rows == 120
      and not page_a_wrong_year and not page_b_wrong_year,
      f"rows_a={page_a_rows} rows_b={page_b_rows} wrong_a={len(page_a_wrong_year)} wrong_b={len(page_b_wrong_year)}")

# --- D9: جست‌وجوی متنی با سال در همان query (قبل از LIMIT) و بدون نشتی
with contextlib.redirect_stdout(io.StringIO()):
    search_a = observation_dal.search("آزمون", limit=None, academic_year_id=year_a.id)
    search_a_limited = observation_dal.search("آزمون", limit=100, academic_year_id=year_a.id)
    search_b = observation_dal.search("آزمون", limit=None, academic_year_id=year_b.id)
check("D",
      "بند ۱۷ (مسیر جست‌وجو): جست‌وجوی متنی با فیلتر سال در خود SQL انجام می‌شود — ۱۲۰ نتیجهٔ سال ۱۴۰۳ و ۱۲۰ نتیجهٔ سال ۱۴۰۴ جدا برمی‌گردند، با limit=۱۰۰ هم دقیقاً ۱۰۰ نتیجه از همان سال (نه محدودکردن قبل از فیلتر سال)",
      len(search_a) == 120 and len(search_b) == 120 and len(search_a_limited) == 100
      and {o.student_profile_id for o in search_a} == {profile_a.id}
      and {o.student_profile_id for o in search_b} == {profile_b.id},
      f"a={len(search_a)} b={len(search_b)} limited={len(search_a_limited)}")

# --- D10: صفر رکورد در سال بدون داده → صفحهٔ خالی، بدون خطا و بدون نشتی
empty_year = _year("1520-1521", "1520/07/01", "1521/03/31", make_active=False)
messages_before = len(message_log)
observations_page.set_active_year(empty_year.id)
empty_rows = len(observations_page.observations)
empty_critical = [m for m in message_log[messages_before:] if m[0] == "crit"]
check("D",
      "بند ۱۶/۱۷ (حالت مرزی): سال بدون داده → صفحهٔ مشاهدات فهرست خالی نشان می‌دهد، خطایی تولید نمی‌شود و دادهٔ سال‌های دیگر جای آن را نمی‌گیرد",
      empty_rows == 0 and not empty_critical,
      f"rows={empty_rows} critical={empty_critical[-2:]}")

QMessageBox.question = real_question
QMessageBox.information = real_info_d
QMessageBox.critical = real_crit_d
QMessageBox.warning = real_warn_d

# ============================================================
print()
print("=" * 76)
print(f"نتیجهٔ دور هفدهم (مرحله‌های ۱ تا ۴):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
if FAILURES:
    print("موارد ناموفق:")
    for f in FAILURES:
        print("   -", f)
print("=" * 76)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
