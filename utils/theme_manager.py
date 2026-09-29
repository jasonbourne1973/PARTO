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
        "bg": "#F5F6F8",
        "surface": "#FFFFFF",
        "surface_alt": "#F9FAFB",
        "text": "#344054",
        "text_strong": "#1D2939",
        "text_muted": "#667085",
        "border": "#D0D5DD",
        "border_light": "#EAECF0",
        "primary": "#344054",
        "primary_hover": "#1D2939",
        "primary_pressed": "#101828",
        "accent": "#475467",
        "success": "#2E7D32",
        "warning": "#F79009",
        "error": "#B42318",
        "info": "#667085",
    }

    # رنگ‌های قدیمی UI را به پالت خنثی جدید نگاشت می‌کنیم تا استایل‌های
    # مستقیم موجود در View/Dialogها نیز همان ظاهر اداری را حفظ کنند.
    _OLD_COLORS = {
        "#F4C542": "#344054",
        "#FFE8A3": "#EAECF0",
        "#D9C36A": "#667085",
        "#66BB6A": "#2E7D32",
        "#8BC34A": "#D0D5DD",
        "#111111": "#344054",
        "#000000": "#344054",
        "#F4D35E": "#475467",
        "#061B2D": "#1D2939",
        "#0B2E4F": "#344054",
        "#174F78": "#475467",
        "#08223A": "#1D2939",
        "#D9AF24": "#475467",
        "#B8860B": "#344054",
        "#FFE8A3": "#EAECF0",
        "#DCEAF5": "#E4E7EC",
        "#E7EEF5": "#F2F4F7",
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
        """استایل مستقیم قدیمی را به Design System خنثی متصل می‌کند."""
        if not style:
            return style

        replacements = dict(cls._OLD_COLORS)

        # Sidebar هم مانند سایر بخش‌ها خنثی و روشن است؛ فقط حالت فعال کمی
        # تیره‌تر می‌شود تا ناوبری واضح بماند.
        if cls.is_menu_widget(widget):
            replacements.update({
                "#F4C542": "#344054",
                "#FFE8A3": "#1D2939",
                "#D9C36A": "#667085",
                "#66BB6A": "#475467",
                "#F4D35E": "#344054",
            })

        pattern = re.compile("|".join(re.escape(token) for token in replacements), re.I)
        normalized = pattern.sub(lambda m: replacements.get(m.group(0).upper(), m.group(0)), style)

        if "qlineargradient" in normalized.lower():
            normalized = re.sub(
                r"background\s*:\s*qlineargradient\([^;]*\);?",
                "background: #F5F6F8;",
                normalized,
                flags=re.IGNORECASE | re.DOTALL,
            )
            normalized = re.sub(
                r"background-color\s*:\s*qlineargradient\([^;]*\);?",
                "background-color: #F5F6F8;",
                normalized,
                flags=re.IGNORECASE | re.DOTALL,
            )

        return normalized

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
