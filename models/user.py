"""
مدل کاربر سیستم

هر کاربر به یک عضو کادر (staff) وصل است.
نکته مهم: user.id با staff.id فرق دارد.
جدول audit_logs.user_id به staff.id ارجاع می‌دهد، پس هر جا که
می‌خواهیم «چه کسی این کار را کرد» را ثبت کنیم باید staff_id را
بفرستیم، نه user.id. این اشتباه در نسخه قبلی وجود داشت.
"""

import re

from models.base import BaseModel
from models.enums import UserRole


class User(BaseModel):
    """مدل کاربر سیستم با پشتیبانی از Soft Delete"""

    # حداقل طول رمز عبور
    MIN_PASSWORD_LENGTH = 8

    def __init__(self):
        super().__init__()
        # ===== ارتباطات =====
        self.staff_id = None            # ارجاع به staff.id (NOT NULL)

        # ===== اطلاعات ورود =====
        self.username = None
        self.password_hash = None       # هرگز رمز خام اینجا نگه داشته نمی‌شود
        self.role = UserRole.MANAGER.value

        # ===== وضعیت =====
        self._is_active = 1
        self.must_change_password = 0
        self.last_login = None

        # ===== فیلدهای کمکی (در دیتابیس نیستند) =====
        self.staff_name = None          # نام کامل عضو کادر
        self.staff_role = None          # نقش عضو کادر

    # ------------------------------------------------------------------
    # is_active با getter/setter نرمال‌شده
    # ------------------------------------------------------------------
    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        """هر مقدار truthy به ۱ و غیر آن به ۰ تبدیل می‌شود."""
        self._is_active = 1 if value else 0

    @property
    def must_change(self):
        """آیا کاربر باید در اولین ورود رمز را عوض کند؟"""
        return bool(self.must_change_password)

    @property
    def role_display(self):
        """نمایش فارسی نقش کاربر"""
        return UserRole.get_display(self.role)

    @property
    def display_name(self):
        """نام نمایشی: نام کاربری به همراه نام عضو کادر"""
        if self.staff_name:
            return f"{self.username} ({self.staff_name})"
        return self.username or "کاربر نامشخص"

    @property
    def status_display(self):
        if self.is_deleted == 1:
            return "🗑️ حذف شده"
        return "🟢 فعال" if self._is_active == 1 else "🔴 غیرفعال"

    @staticmethod
    def normalize_username(username):
        """
        یکدست‌سازی نام کاربری

        - ارقام فارسی/عربی به ASCII
        - حذف فاصله‌های اضافی
        - تبدیل به حروف کوچک (نام کاربری case-insensitive ذخیره می‌شود)

        این کار از دو مشکل جلوگیری می‌کند:
        ۱. «admin» و «ADMIN» دو کاربر جدا نشوند
        ۲. ارقام فارسی باعث شوند نام کاربری با چیزی که کاربر
           تایپ می‌کند مطابقت نکند
        """
        if not username:
            return ""

        text = str(username).strip()
        text = _to_ascii_digits(text)
        text = re.sub(r"\s+", " ", text)
        return text.lower()

    def validate(self):
        """اعتبارسنجی کاربر"""
        errors = []

        if not self.staff_id:
            errors.append("عضو کادر باید انتخاب شود")

        username = (self.username or "").strip()
        if not username:
            errors.append("نام کاربری نمی‌تواند خالی باشد")
        else:
            if len(username) < 3:
                errors.append("نام کاربری باید حداقل ۳ کاراکتر باشد")
            if len(username) > 50:
                errors.append("نام کاربری نباید بیشتر از ۵۰ کاراکتر باشد")
            if not re.match(r"^[a-zA-Z0-9._@-]+$", username):
                errors.append(
                    "نام کاربری فقط می‌تواند شامل حروف انگلیسی، عدد و "
                    "کاراکترهای . _ @ - باشد"
                )

        if not self.password_hash:
            errors.append("رمز عبور باید تنظیم شود")

        valid_roles = [role.value for role in UserRole]
        if self.role not in valid_roles:
            errors.append(
                f"نقش نامعتبر است. نقش‌های مجاز: {', '.join(valid_roles)}"
            )

        return errors


def _to_ascii_digits(text):
    """تبدیل ارقام فارسی و عربی به ASCII"""
    persian = "۰۱۲۳۴۵۶۷۸۹"
    arabic = "٠١٢٣٤٥٦٧٨٩"
    table = {}
    for index, digit in enumerate("0123456789"):
        table[ord(persian[index])] = digit
        table[ord(arabic[index])] = digit
    return text.translate(table)
