"""مدیریت ظاهر واحد PARTO.

این ماژول عمداً دیگر سیستم چندتمی ندارد. کل برنامه فقط یک Design System ثابت
دارد و استایل‌های مستقیم قدیمیِ ویجت‌ها نیز هنگام اجرا به همان پالت واحد
نرمال می‌شوند. این تغییر فقط مربوط به UI است و به منطق، DAL، سرویس و دیتابیس
دست نمی‌زند.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar, Optional

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QLabel, QComboBox, QWidget


class _ThemeEventFilter(QObject):
    """ظاهر واحد را به دیالوگ‌ها و ویجت‌هایی که بعداً ساخته می‌شوند اعمال می‌کند."""

    def __init__(self, manager: "ThemeManager"):
        super().__init__()
        self.manager = manager

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Show and isinstance(watched, QWidget):
            self.manager.apply_to_tree(watched)
        return False


class ThemeManager:
    """مدیر Design System واحد PARTO؛ هیچ Theme قابل انتخابی وجود ندارد."""

    SETTINGS_ORG = "PARTOW"
    SETTINGS_APP = "PARTOW"
    DEFAULT_THEME = "default"

    # فقط یک ظاهر وجود دارد. این mapping صرفاً برای جلوگیری از شکستن APIهای
    # قدیمی است؛ کاربر هیچ Theme دیگری نمی‌تواند انتخاب یا ذخیره کند.
    THEMES: ClassVar[dict[str, dict[str, str]]] = {
        "default": {"title": "ظاهر استاندارد PARTO"}
    }

    COLORS: ClassVar[dict[str, str]] = {
        "bg": "#F5F7FA",
        "surface": "#FFFFFF",
        "surface_alt": "#F8FAFC",
        "text": "#17212B",
        "text_secondary": "#667085",
        "text_muted": "#98A2B3",
        "border": "#D0D5DD",
        "border_light": "#E4E7EC",
        "primary": "#0B2E4F",
        "primary_hover": "#174F78",
        "primary_pressed": "#08223A",
        "accent": "#D9AF24",
        "success": "#2E7D32",
        "warning": "#F79009",
        "error": "#B42318",
        "info": "#175CD3",
    }

    # رنگ‌های legacy که در View/Dialog/Widgetهای قدیمی باقی مانده‌اند.
    # هیچ رنگ جدیدی اینجا ایجاد نمی‌شود؛ همه به Design System نگاشت می‌شوند.
    _OLD_COLORS = {
        "#F4C542": "#D9AF24",
        "#FFE8A3": "#E4E7EC",
        "#D9C36A": "#667085",
        "#66BB6A": "#2E7D32",
        "#8BC34A": "#D0D5DD",
        "#111111": "#17212B",
        "#000000": "#17212B",
        "#F4D35E": "#D9AF24",
        "#061B2D": "#0B2E4F",
    }

    def __init__(self, app: Optional[QApplication] = None):
        self.app = app or QApplication.instance()
        self.current_theme = self.DEFAULT_THEME
        self._event_filter: Optional[_ThemeEventFilter] = None

    @classmethod
    def theme_title(cls, theme_name: str) -> str:
        return cls.THEMES[cls.DEFAULT_THEME]["title"]

    @classmethod
    def saved_theme(cls) -> str:
        """سازگاری با API قدیمی؛ دیگر چیزی از QSettings خوانده نمی‌شود."""
        return cls.DEFAULT_THEME

    @classmethod
    def stylesheet_path(cls, theme_name: str = DEFAULT_THEME) -> Path:
        base = Path(__file__).resolve().parent.parent
        return base / "assets" / "styles" / "main_style.qss"

    @classmethod
    def transform_style(cls, stylesheet: str, theme_name: str = DEFAULT_THEME) -> str:
        """تمام رنگ‌های legacy را به پالت واحد تبدیل می‌کند."""
        if not stylesheet:
            return stylesheet
        pattern = re.compile("|".join(re.escape(token) for token in cls._OLD_COLORS), re.I)
        return pattern.sub(lambda m: cls._OLD_COLORS.get(m.group(0).upper(), m.group(0)), stylesheet)

    @staticmethod
    def is_menu_widget(widget: QWidget) -> bool:
        current = widget
        while current is not None:
            if current.objectName() == "MenuFrame":
                return True
            current = current.parentWidget()
        return False

    @classmethod
    def _normalize_widget_style(cls, widget: QWidget, style: str) -> str:
        """استایل مستقیم را به Design System واحد متصل می‌کند."""
        if not style:
            return style

        menu = cls.is_menu_widget(widget)
        replacements = dict(cls._OLD_COLORS)

        # Sidebar تیره است؛ متن آن باید روشن و با کنتراست بالا بماند.
        if menu:
            replacements.update({
                "#F4C542": "#FFFFFF",
                "#FFE8A3": "#FFFFFF",
                "#D9C36A": "#E4E7EC",
                "#66BB6A": "#D9AF24",
                "#F4D35E": "#FFFFFF",
            })
        else:
            replacements.update({
                "#F4C542": "#0B2E4F",
                "#FFE8A3": "#174F78",
                "#D9C36A": "#667085",
                "#66BB6A": "#2E7D32",
                "#F4D35E": "#D9AF24",
            })

        pattern = re.compile("|".join(re.escape(token) for token in replacements), re.I)
        normalized = pattern.sub(lambda m: replacements.get(m.group(0).upper(), m.group(0)), style)

        # گرادیان‌های تزئینی قدیمی باعث می‌شوند صفحه‌های مختلف ظاهر متفاوتی
        # داشته باشند. خارج از Sidebar، گرادیان به سطح ساده و واحد تبدیل می‌شود.
        if not menu and "qlineargradient" in normalized.lower():
            normalized = re.sub(
                r"background\s*:\s*qlineargradient\([^;]*\);?",
                "background: #F5F7FA;",
                normalized,
                flags=re.IGNORECASE | re.DOTALL,
            )
            normalized = re.sub(
                r"background-color\s*:\s*qlineargradient\([^;]*\);?",
                "background-color: #F5F7FA;",
                normalized,
                flags=re.IGNORECASE | re.DOTALL,
            )

        return normalized

    @classmethod
    def _hide_legacy_theme_selector(cls, root: QWidget) -> None:
        """کنترل Theme قدیمی را از UI حذف می‌کند؛ برنامه فقط یک ظاهر دارد."""
        for combo in root.findChildren(QComboBox):
            if combo.toolTip() == "انتخاب ظاهر برنامه":
                combo.hide()
                combo.setEnabled(False)
                parent = combo.parentWidget()
                if parent and parent.layout():
                    index = parent.layout().indexOf(combo)
                    if index >= 0:
                        item = parent.layout().itemAt(index)
                        if item is not None:
                            item.widget().hide() if item.widget() else None
                        if index > 0:
                            previous_item = parent.layout().itemAt(index - 1)
                            previous = previous_item.widget() if previous_item else None
                            if isinstance(previous, QLabel) and "تم" in previous.text():
                                previous.hide()

    def apply_to_widget(self, widget: QWidget) -> None:
        if not hasattr(widget, "_partow_base_stylesheet"):
            widget._partow_base_stylesheet = widget.styleSheet()
        base_style = getattr(widget, "_partow_base_stylesheet", "")
        if base_style:
            normalized = self._normalize_widget_style(widget, base_style)
            if normalized != widget.styleSheet():
                widget.setStyleSheet(normalized)

    def apply_to_tree(self, root: QWidget) -> None:
        self._hide_legacy_theme_selector(root)
        self.apply_to_widget(root)
        for widget in root.findChildren(QWidget):
            self.apply_to_widget(widget)

    def apply(self, root: Optional[QWidget] = None, theme_name: Optional[str] = None) -> str:
        if self.app is None:
            self.app = QApplication.instance()
        self.current_theme = self.DEFAULT_THEME

        path = self.stylesheet_path()
        if path.exists() and self.app is not None:
            stylesheet = path.read_text(encoding="utf-8")
            self.app.setStyleSheet(self.transform_style(stylesheet))

        if root is not None:
            self.apply_to_tree(root)

        if self.app is not None and self._event_filter is None:
            self._event_filter = _ThemeEventFilter(self)
            self.app.installEventFilter(self._event_filter)

        return self.DEFAULT_THEME
