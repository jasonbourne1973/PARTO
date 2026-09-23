"""
بررسی‌های دور هفدهم — «MASTER FIX / FINAL TECHNICAL AUDIT»

هر بررسی «کارکردی با پیش/پس‌شرط» است: وضعیت دیتابیس/فایل پیش و پس از
عملیات مقایسه می‌شود، نه فقط «استثنا نداد».

مرحلهٔ ۱ — مرحلهٔ P0: داده و صداقت پشتیبان/بازیابی (بند ۱۰ مأموریت):
  A) شکست checksum = شکست بازیابی با پیش/پس‌شرط، وضعیت صریح پشتیبان بدون
     فایل کناری (legacy) با هشدار دیده‌شدنی، حساب‌داری واقعی پیوست‌ها در
     متادیتا (موردانتظار طبق DB / بسته‌بندی‌شده / گم‌شده)، پشتیبان ناقص ≠
     کامل، پاک‌سازی فایل ایمنی در مسیر استثنا، توقف واقعی نخ پشتیبان‌گیری
     خودکار پیش از خروج برنامه، و حفظ قراردادهای قبلی ..................... ۱۲ بررسی

جمع فعلی: ۱۲ بررسی
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
print(f"نتیجهٔ دور هفدهم (مرحلهٔ ۱):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
if FAILURES:
    print("موارد ناموفق:")
    for f in FAILURES:
        print("   -", f)
print("=" * 76)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
