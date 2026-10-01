"""مدیریت ظاهر واحد PARTO.

این ماژول یک Design System ساده و اداری را اعمال می‌کند: سفید، خاکستری روشن
و خاکستری تیره. هیچ تم آبی/طلایی یا تم قابل انتخابی در UI وجود ندارد.
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
    """مدیر Design System واحد PARTO."""

    SETTINGS_ORG = "PARTOW"
    SETTINGS_APP = "PARTOW"
    DEFAULT_THEME = "default"

    THEMES: ClassVar[dict[str, dict[str, str]]] = {
        "default": {"title": "ظاهر استاندارد اداری"}
    }

    COLORS: ClassVar[dict[str, str]] = {
        "bg": "#F8F9FA",
        "surface": "#FFFFFF",
        "surface_alt": "#FFFFFF",
        "text": "#2C3E50",
        "text_strong": "#1A252F",
        "text_muted": "#7F8C8D",
        "border": "#DEE2E6",
        "border_light": "#ECF0F1",
        "primary": "#2C3E50",
        "primary_hover": "#1A252F",
        "primary_pressed": "#1A252F",
        "accent": "#3498DB",
        "success": "#27AE60",
        "warning": "#F39C12",
        "error": "#E74C3C",
        "info": "#7F8C8D",
    }

    # رنگ‌های قدیمی UI را به پالت خنثی جدید نگاشت می‌کنیم تا استایل‌های
    # مستقیم موجود در View/Dialogها نیز همان ظاهر اداری را حفظ کنند.
    # نگاشت رنگ‌های طراحی جدید به معادل‌های ظاهری نسخه ZIP قدیمی.
    # رنگ‌های قدیمیِ خود ZIP هرگز دوباره به پالت دیگری تبدیل نمی‌شوند.
    _OLD_COLORS = {
        "#0B2E4F": "#2C3E50", "#174F78": "#34495E", "#08223A": "#1A252F",
        "#17212B": "#2C3E50", "#D9AF24": "#3498DB", "#B8860B": "#2980B9",
        "#111111": "#2C3E50", "#061B2D": "#08223A", "#344054": "#2C3E50",
        "#1D2939": "#1A252F", "#101828": "#1A252F", "#475467": "#7F8C8D",
        "#667085": "#7F8C8D", "#98A2B3": "#BDC3C7", "#D0D5DD": "#DEE2E6",
        "#EAECF0": "#ECF0F1", "#F2F6FA": "#F8F9FA", "#F5F6F8": "#F8F9FA",
        "#F5F7FA": "#F8F9FA", "#F9FAFB": "#FFFFFF", "#F8FAFC": "#F8F9FA",
        "#F0F2F5": "#F8F9FA", "#F1F5F9": "#F0F4F8", "#CBD5E1": "#BDC3C7",
        "#94A3B8": "#95A5A6", "#64748B": "#7F8C8D", "#E2E8F0": "#DEE2E6",
        "#E4E7EC": "#DEE2E6", "#DC2626": "#E74C3C", "#EF4444": "#EF5350",
        "#B42318": "#C0392B", "#D97706": "#E67E22", "#F59E0B": "#F39C12",
        "#16A34A": "#27AE60", "#22C55E": "#2ECC71", "#2563EB": "#3498DB",
        "#3B82F6": "#3498DB", "#1D4ED8": "#2980B9", "#7C3AED": "#9B59B6",
        "#8B5CF6": "#8E44AD",
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
        """سازگاری با API قدیمی؛ چیزی از QSettings خوانده نمی‌شود."""
        return cls.DEFAULT_THEME

    @classmethod
    def stylesheet_path(cls, theme_name: str = DEFAULT_THEME) -> Path:
        base = Path(__file__).resolve().parent.parent
        return base / "assets" / "styles" / "main_style.qss"

    @classmethod
    def transform_style(cls, stylesheet: str, theme_name: str = DEFAULT_THEME) -> str:
        """رنگ‌های legacy را به پالت خنثی و اداری تبدیل می‌کند."""
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
        """استایل مستقیم ویجت را فقط از پالت جدید به ظاهر نسخه ZIP قدیمی تبدیل می‌کند."""
        if not style:
            return style
        pattern = re.compile("|".join(re.escape(token) for token in cls._OLD_COLORS), re.I)
        return pattern.sub(lambda m: cls._OLD_COLORS.get(m.group(0).upper(), m.group(0)), style)

    @classmethod
    def _hide_legacy_theme_selector(cls, root: QWidget) -> None:
        """کنترل انتخاب Theme قدیمی را از UI حذف می‌کند."""
        for combo in root.findChildren(QComboBox):
            if combo.toolTip() == "انتخاب ظاهر برنامه":
                combo.hide()
                combo.setEnabled(False)
                parent = combo.parentWidget()
                if parent and parent.layout():
                    index = parent.layout().indexOf(combo)
                    if index >= 0:
                        item = parent.layout().itemAt(index)
                        if item is not None and item.widget():
                            item.widget().hide()
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
