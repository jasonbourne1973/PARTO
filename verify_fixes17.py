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

جمع فعلی: ۱۹ بررسی
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
print(f"نتیجهٔ دور هفدهم (مرحله‌های ۱ و ۲):  {PASS} موفق / {FAIL} ناموفق  از {PASS + FAIL}")
if FAILURES:
    print("موارد ناموفق:")
    for f in FAILURES:
        print("   -", f)
print("=" * 76)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
