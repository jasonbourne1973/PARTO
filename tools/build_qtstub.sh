#!/bin/bash
# ابزار محیطِ توسعه (نه بخشی از برنامه): ساختِ کتابخانه‌های جانشینِ
# libGL/libEGL/libxkbcommon/libdbus برای اجرای PySide6 در حالتِ
# QT_QPA_PLATFORM=offscreen در سندباکس‌هایی که این کتابخانه‌های سیستمی
# را ندارند و شبکهٔ apt هم بسته است. خروجی در /home/user/qtstub/lib
# قرار می‌گیرد و در .gitignore نیست چون خودِ این اسکریپت هم کد منبع
# نیست (فقط ابزار محیط)، ولی داخل مخزن نگه داشته می‌شود تا بینِ
# نوبت‌های کاری (که پکیج‌های pip/فایل‌های بیرونِ مخزن گاهی ریست
# می‌شوند) دوباره قابلِ ساخت باشد بدون تکرارِ دستیِ کشفِ نمادها.
#
# استفاده:
#   bash tools/build_qtstub.sh
#   LD_LIBRARY_PATH=/home/user/qtstub/lib QT_QPA_PLATFORM=offscreen python3 ...
set -euo pipefail

PYSIDE_LIB_DIR="$(python3 -c 'import PySide6, os; print(os.path.join(os.path.dirname(PySide6.__file__), "Qt", "lib"))')"
PYSIDE_ROOT="$(python3 -c 'import PySide6, os; print(os.path.join(os.path.dirname(PySide6.__file__), "Qt"))')"
OUT=/home/user/qtstub/lib
WORK=$(mktemp -d)
mkdir -p "$OUT"

echo "PySide6 Qt lib dir: $PYSIDE_LIB_DIR"

# نمادهای تعریف‌نشده را از همهٔ .so های PySide6 (کتابخانه + پلاگین‌ها) جمع کن
find "$PYSIDE_ROOT" -name "*.so*" | while read -r f; do
  objdump -T "$f" 2>/dev/null
done | grep UND | awk '{print $NF}' | sort -u > "$WORK/all_und.txt"

grep -E "^gl[A-Z]|^glX[A-Z]" "$WORK/all_und.txt" | sort -u > "$WORK/gl_syms.txt"
grep -E "^egl[A-Z]" "$WORK/all_und.txt" | sort -u > "$WORK/egl_syms.txt"
grep -E "^xkb_" "$WORK/all_und.txt" | sort -u > "$WORK/xkb_syms.txt"
grep -E "^dbus_" "$WORK/all_und.txt" | sort -u > "$WORK/dbus_syms.txt"

build_simple() {
  local outfile="$1" soname="$2" symfile="$3"
  { echo "#include <stddef.h>"; while read -r s; do echo "long $s(){ return 0; }"; done < "$symfile"; } > "$WORK/$soname.c"
  gcc -shared -fPIC -o "$outfile" "$WORK/$soname.c" -Wl,-soname,"$soname"
}

build_versioned() {
  local outfile="$1" soname="$2" symfile="$3" version="$4"
  { echo "#include <stddef.h>"; while read -r s; do echo "long $s(){ return 0; }"; done < "$symfile"; } > "$WORK/$soname.c"
  { echo "$version {"; echo "  global:"; while read -r s; do echo "    $s;"; done < "$symfile"; echo "  local: *;"; echo "};"; } > "$WORK/$soname.map"
  gcc -shared -fPIC -o "$outfile" "$WORK/$soname.c" -Wl,-soname,"$soname" -Wl,--version-script="$WORK/$soname.map"
}

build_simple "$OUT/libGL.so.1" libGL.so.1 "$WORK/gl_syms.txt"
build_simple "$OUT/libEGL.so.1" libEGL.so.1 "$WORK/egl_syms.txt"
build_versioned "$OUT/libxkbcommon.so.0" libxkbcommon.so.0 "$WORK/xkb_syms.txt" "V_0.5.0"
build_versioned "$OUT/libdbus-1.so.3" libdbus-1.so.3 "$WORK/dbus_syms.txt" "LIBDBUS_1_3"

rm -rf "$WORK"
echo "ساخته شد: $OUT"
ls -la "$OUT"

echo "آزمایش QApplication (offscreen):"
LD_LIBRARY_PATH="$OUT" QT_QPA_PLATFORM=offscreen python3 -c "
from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
print('OK', app)
"
