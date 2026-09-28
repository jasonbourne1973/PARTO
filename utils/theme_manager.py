"""مدیریت چهار تم رابط کاربری PARTOW.

این فایل فقط ظاهر برنامه را مدیریت می‌کند و به مدل، DAL، سرویس یا دیتابیس
دست نمی‌زند. استایل‌های مستقیم ویجت‌ها نیز با توکن‌های پالت اصلی تعویض می‌شوند
تا تغییر تم روی فرم‌ها و صفحات داخلی هم دیده شود.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar, Optional

from PySide6.QtCore import QEvent, QObject, QSettings
from PySide6.QtWidgets import QApplication, QWidget


class _ThemeEventFilter(QObject):
    """اعمال تم به دیالوگ‌ها و ویجت‌هایی که بعداً ساخته می‌شوند."""

    def __init__(self, manager: ThemeManager):
        super().__init__()
        self.manager = manager

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Show and isinstance(watched, QWidget):
            self.manager.apply_to_tree(watched)
        return False


class ThemeManager:
    """مدیر تم‌های PARTOW با حفظ تم ثابت منوی سمت چپ."""

    SETTINGS_ORG = "PARTOW"
    SETTINGS_APP = "PARTOW"
    DEFAULT_THEME = "royal"

    # این توکن‌ها فقط رنگ‌هایِ «Brand/Accent» و دو توکنِ خنثیِ ویژهٔ تمِ
    # کنتراست‌بالا هستند (نسخهٔ ۲۱ — Design System). رنگ‌هایِ خنثی
    # (سطح/متنِ ثانویه/حاشیهٔ ظریف) و رنگ‌هایِ معنایی (موفقیت/هشدار/خطا/
    # اطلاعات) دیگر اینجا نیستند: طبقِ اصلِ «Neutral و Semantic مستقل از
    # برند»، این‌ها در همهٔ تم‌ها ثابت می‌مانند تا تعویضِ تم فقط هویتِ
    # برند (Navy/Gold یا معادلش) را عوض کند، نه معنایِ رنگ‌ها را.
    TOKENS = (
        "#0B2E4F",  # Primary
        "#08223A",  # Primary Pressed
        "#174F78",  # Primary Hover
        "#D9AF24",  # Accent
        "#B8860B",  # Accent Strong
        "#17212B",  # Text Primary (فقط برایِ تمِ کنتراست‌بالا تغییر می‌کند)
        "#D0D5DD",  # Border (فقط برایِ تمِ کنتراست‌بالا پررنگ‌تر می‌شود)
    )

    THEMES: ClassVar[dict[str, dict[str, str]]] = {
        "royal": {
            "title": "آبی سلطنتی و طلایی",
            "#0B2E4F": "#0B2E4F",
            "#08223A": "#08223A",
            "#174F78": "#174F78",
            "#D9AF24": "#D9AF24",
            "#B8860B": "#B8860B",
            "#17212B": "#17212B",
            "#D0D5DD": "#D0D5DD",
        },
        "corporate": {
            "title": "آبی سازمانی و نقره‌ای",
            "#0B2E4F": "#102A43",
            "#08223A": "#0B1F33",
            "#174F78": "#243B53",
            "#D9AF24": "#94A3B8",
            "#B8860B": "#475569",
            "#17212B": "#17212B",
            "#D0D5DD": "#D0D5DD",
        },
        "educational": {
            "title": "سبز آموزشی و کرم",
            "#0B2E4F": "#1B4B43",
            "#08223A": "#123A33",
            "#174F78": "#2F6F62",
            "#D9AF24": "#C9A227",
            "#B8860B": "#A47E1B",
            "#17212B": "#17212B",
            "#D0D5DD": "#D0D5DD",
        },
        "contrast": {
            "title": "کنتراست بالا",
            "#0B2E4F": "#061B2D",
            "#08223A": "#000000",
            "#174F78": "#0D3A5C",
            "#D9AF24": "#B8860B",
            "#B8860B": "#000000",
            "#17212B": "#000000",
            "#D0D5DD": "#4A5568",
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
