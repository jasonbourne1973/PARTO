# -*- coding: utf-8 -*-
"""مدیریت چهار تم رابط کاربری PARTOW.

این فایل فقط ظاهر برنامه را مدیریت می‌کند و به مدل، DAL، سرویس یا دیتابیس
دست نمی‌زند. استایل‌های مستقیم ویجت‌ها نیز با توکن‌های پالت اصلی تعویض می‌شوند
تا تغییر تم روی فرم‌ها و صفحات داخلی هم دیده شود.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QEvent, QObject, QSettings
from PySide6.QtWidgets import QApplication, QWidget


class _ThemeEventFilter(QObject):
    """اعمال تم به دیالوگ‌ها و ویجت‌هایی که بعداً ساخته می‌شوند."""

    def __init__(self, manager: "ThemeManager"):
        super().__init__()
        self.manager = manager

    def eventFilter(self, watched, event):  # noqa: N802 - نام Qt
        if event.type() == QEvent.Type.Show and isinstance(watched, QWidget):
            self.manager.apply_to_tree(watched)
        return False


class ThemeManager:
    """مدیر تم‌های PARTOW با حفظ تم ثابت منوی سمت چپ."""

    SETTINGS_ORG = "PARTOW"
    SETTINGS_APP = "PARTOW"
    DEFAULT_THEME = "royal"

    # این توکن‌ها همان رنگ‌های پایه فایل‌های views هستند.
    TOKENS = (
        "#0B2E4F",  # زمینه اصلی
        "#08223A",  # زمینه عمیق
        "#174F78",  # آبی میانی/hover
        "#F4C542",  # متن طلایی
        "#FFE8A3",  # طلایی روشن
        "#66BB6A",  # سبز کادر/تب
        "#8BC34A",  # سبز روشن
        "#D9C36A",  # خط و حاشیه
        "#F4D35E",  # هشدار
        "#C62828",  # خطا
        "#F28C28",  # نارنجی
        "#111111",  # متن مشکی
    )

    THEMES: Dict[str, Dict[str, str]] = {
        "royal": {
            "title": "آبی سلطنتی و طلایی",
            "#0B2E4F": "#0B2E4F",
            "#08223A": "#08223A",
            "#174F78": "#174F78",
            "#F4C542": "#F4C542",
            "#FFE8A3": "#FFE8A3",
            "#66BB6A": "#66BB6A",
            "#8BC34A": "#8BC34A",
            "#D9C36A": "#D9C36A",
            "#F4D35E": "#F4D35E",
            "#C62828": "#C62828",
            "#F28C28": "#F28C28",
            "#111111": "#111111",
        },
        "corporate": {
            "title": "آبی سازمانی و نقره‌ای",
            "#0B2E4F": "#102A43",
            "#08223A": "#0B1F33",
            "#174F78": "#3E7CB1",
            "#F4C542": "#D9E2EC",
            "#FFE8A3": "#B8C7D9",
            "#66BB6A": "#6FAF8A",
            "#8BC34A": "#9AC7A2",
            "#D9C36A": "#AAB7C4",
            "#F4D35E": "#F4D35E",
            "#C62828": "#B3261E",
            "#F28C28": "#C96A1B",
            "#111111": "#111111",
        },
        "educational": {
            "title": "سبز آموزشی و کرم",
            "#0B2E4F": "#183A37",
            "#08223A": "#102A27",
            "#174F78": "#2B6F68",
            "#F4C542": "#F2D492",
            "#FFE8A3": "#F7E5B2",
            "#66BB6A": "#83C5BE",
            "#8BC34A": "#A8DADC",
            "#D9C36A": "#D8B365",
            "#F4D35E": "#F4D35E",
            "#C62828": "#B3261E",
            "#F28C28": "#C96A1B",
            "#111111": "#111111",
        },
        "contrast": {
            "title": "کنتراست بالا",
            "#0B2E4F": "#061B2D",
            "#08223A": "#020B14",
            "#174F78": "#1D5C8A",
            "#F4C542": "#FFE36E",
            "#FFE8A3": "#FFF0A8",
            "#66BB6A": "#7CCB7F",
            "#8BC34A": "#A8E6A3",
            "#D9C36A": "#E6D37A",
            "#F4D35E": "#F4D35E",
            "#C62828": "#FF6B6B",
            "#F28C28": "#FF9F43",
            "#111111": "#111111",
        },
    }

    def __init__(self, app: Optional[QApplication] = None):
        self.app = app or QApplication.instance()
        self.current_theme = self.saved_theme()
        self._event_filter: Optional[_ThemeEventFilter] = None

    @classmethod
    def theme_title(cls, theme_name: str) -> str:
        return cls.THEMES.get(theme_name, cls.THEMES[cls.DEFAULT_THEME])["title"]

    @classmethod
    def saved_theme(cls) -> str:
        value = QSettings(cls.SETTINGS_ORG, cls.SETTINGS_APP).value(
            "theme", cls.DEFAULT_THEME
        )
        return value if value in cls.THEMES else cls.DEFAULT_THEME

    @classmethod
    def stylesheet_path(cls, theme_name: str) -> Path:
        base = Path(__file__).resolve().parent.parent
        return base / "assets" / "styles" / "themes" / f"{theme_name}.qss"

    @classmethod
    def transform_style(cls, stylesheet: str, theme_name: str) -> str:
        palette = cls.THEMES.get(theme_name, cls.THEMES[cls.DEFAULT_THEME])
        # طولانی‌ترها اول تعویض شوند تا جایگزینی زنجیره‌ای رخ ندهد.
        pattern = re.compile("|".join(re.escape(token) for token in cls.TOKENS), re.I)
        return pattern.sub(lambda match: palette.get(match.group(0).upper(), match.group(0)), stylesheet)

    @staticmethod
    def is_menu_widget(widget: QWidget) -> bool:
        current = widget
        while current is not None:
            if current.objectName() == "MenuFrame":
                return True
            current = current.parentWidget()
        return False

    def apply_to_widget(self, widget: QWidget) -> None:
        if self.is_menu_widget(widget):
            return
        if not hasattr(widget, "_partow_base_stylesheet"):
            widget._partow_base_stylesheet = widget.styleSheet()
        base_style = getattr(widget, "_partow_base_stylesheet", "")
        if base_style:
            widget.setStyleSheet(self.transform_style(base_style, self.current_theme))

    def apply_to_tree(self, root: QWidget) -> None:
        if self.is_menu_widget(root):
            return
        self.apply_to_widget(root)
        for widget in root.findChildren(QWidget):
            self.apply_to_widget(widget)

    def apply(self, root: Optional[QWidget], theme_name: Optional[str] = None) -> str:
        if self.app is None:
            self.app = QApplication.instance()
        theme_name = theme_name if theme_name in self.THEMES else self.DEFAULT_THEME
        path = self.stylesheet_path(theme_name)
        if path.exists() and self.app is not None:
            self.app.setStyleSheet(path.read_text(encoding="utf-8"))
        self.current_theme = theme_name
        QSettings(self.SETTINGS_ORG, self.SETTINGS_APP).setValue("theme", theme_name)
        if root is not None:
            self.apply_to_tree(root)
        if self.app is not None and self._event_filter is None:
            self._event_filter = _ThemeEventFilter(self)
            self.app.installEventFilter(self._event_filter)
        return theme_name
