"""
اجزای مشترک «نمایش حذف‌شده‌ها و بازیابی» (دور هفدهم — BUG-RESTORE-01/05/06/07)

چرا یک ماژول مشترک؟ چهار صفحه (دانش‌آموزان، فعالیت‌ها، اهداف، مشاوره) همین
مسیر را لازم دارند. اگر هر صفحه دکمه/چک‌باکس/تأییدیه را جدا می‌ساخت،
قرارداد «نتیجهٔ واقعی بازیابی» و شکل پیام‌ها بین صفحه‌ها ناهمخوان می‌شد —
همان مشکلی که در بند ۴ مأموریت توصیف شده است.

این ماژول قابلیت تازه‌ای معرفی نمی‌کند؛ فقط مسیر UI برای capability موجودِ
`DAL.restore` را یکدست می‌کند.
"""

from PySide6.QtWidgets import QCheckBox, QMessageBox, QPushButton

from database.connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def current_user_id():
    """شناسهٔ کاربر واردشده (برای ثبت Audit در بازیابی) یا None"""
    try:
        return DatabaseConnection().get_current_user()
    except Exception as e:  # pragma: no cover - وابسته به اتصال
        logger.debug(f"شناسهٔ کاربر جاری خوانده نشد: {e}")
        return None


def make_show_deleted_checkbox(page, handler_name, tooltip=None):
    """
    چک‌باکس «نمایش حذف‌شده‌ها» برای نوار ابزار صفحه

    Args:
        page: نمونهٔ صفحه (handler روی همان صفحه صدا زده می‌شود)
        handler_name: نام متد صفحه که با تغییر وضعیت اجرا می‌شود
        tooltip: متن راهنما

    Returns:
        QCheckBox: چک‌باکس متصل‌شده
    """
    checkbox = QCheckBox("نمایش حذف‌شده‌ها")
    checkbox.setToolTip(
        tooltip or "رکوردهای حذف‌شده را نشان می‌دهد تا بتوان آن‌ها را بازیابی کرد.")
    checkbox.setStyleSheet("QCheckBox { color: #F4C542; font-weight: bold; }")
    handler = getattr(page, handler_name, None)
    if callable(handler):
        checkbox.toggled.connect(handler)
    else:  # pragma: no cover - خطای برنامه‌نویسی، نه خطای کاربر
        logger.error(
            f"صفحهٔ {type(page).__name__} متد «{handler_name}» را ندارد؛ "
            "چک‌باکس نمایش حذف‌شده‌ها بدون handler می‌ماند."
        )
    return checkbox


def make_restore_button(record, handler, tooltip=None):
    """دکمهٔ «↩️ بازیابی» یک ردیف حذف‌شده"""
    button = QPushButton("↩️")
    button.setFixedSize(30, 30)
    button.setToolTip(tooltip or "بازیابی این رکورد حذف‌شده")
    button.setStyleSheet(
        "background-color: #66BB6A; color: #111111; border: none; "
        "border-radius: 4px; font-size: 14px;")
    button.clicked.connect(lambda checked=False, r=record: handler(r))
    return button


def ask_restore_confirmation(parent, description):
    """
    تأییدیهٔ بازیابی

    Returns:
        bool: True اگر کاربر تأیید کند.
    """
    reply = QMessageBox.question(
        parent,
        "تأیید بازیابی",
        f"{description}\n\nرکورد به فهرست فعال برمی‌گردد؛ پروندهٔ سالانه و "
        "سال تحصیلی آن تغییر نمی‌کند.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes


def report_restore_failure(parent, error):
    """گزارش خطای بازیابی: پیام کاربر + traceback در لاگ (بدون بلع خاموش)"""
    logger.error(f"بازیابی ناموفق: {error}", exc_info=True)
    QMessageBox.critical(parent, "خطا در بازیابی", str(error))


def deleted_label(full_name):
    """برچسب رکورد حذف‌شده برای ستون نام"""
    return f"{full_name} (حذف‌شده)"
