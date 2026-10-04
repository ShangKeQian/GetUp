"""生成 GetUp.ico —— 应用/任务栏图标（多尺寸）。

图形取自 tray.create_app_icon_pixmap()，与运行时窗口图标共用同一套画法，
避免出现两份会各自漂移的图标定义。

载荷格式：256×256 用 PNG（体积小，自 Vista 起受支持）；其余尺寸写成
DIB（32bpp BGRA）。PNG 压缩项在 ICO 规范里只定义用于 256×256，小尺寸用
DIB 才是 Windows 惯例，可避免 Explorer / 安全软件解析小尺寸 PNG 项时
行为不一致。PyInstaller 只把各项原样拷进 RT_ICON 资源，不解析内部格式。

用法: python make_icon.py
"""

import os
import struct
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from tray import APP_ICON_SIZES, create_app_icon_pixmap

OUTPUT = "GetUp.ico"
# 该尺寸及以上用 PNG 载荷，其余用 DIB
PNG_MIN_SIZE = 256


def _png_blob(size):
    pixmap = create_app_icon_pixmap(size)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    return bytes(buffer.data())


def _dib_blob(size):
    """把位图写成 ICO 内的 DIB 载荷：BITMAPINFOHEADER + bottom-up BGRA + AND 掩码。"""
    image = create_app_icon_pixmap(size).toImage().convertToFormat(QImage.Format.Format_ARGB32)
    width, height = image.width(), image.height()

    # BITMAPINFOHEADER：高度写 2×height，表示 XOR 位图与 AND 掩码两张位图叠加
    header = struct.pack("<IiiHHIIiiII", 40, width, height * 2, 1, 32, 0, 0, 0, 0, 0, 0)

    # ARGB32 在小端序下的内存字节序正是 DIB 需要的 BGRA；DIB 自下而上存放
    raw = image.constBits().tobytes()
    stride = image.bytesPerLine()
    xor = b"".join(
        raw[y * stride: y * stride + width * 4] for y in range(height - 1, -1, -1)
    )

    # 透明度已由 alpha 通道表达，AND 掩码全 0（行按 4 字节对齐）
    and_mask = b"\x00" * (height * (((width + 31) // 32) * 4))
    return header + xor + and_mask


def _write_ico(path, blobs):
    """写出 PNG/DIB 混合载荷的 .ico。"""
    header = struct.pack("<HHH", 0, 1, len(blobs))
    offset = len(header) + 16 * len(blobs)
    entries = b""
    payload = b""
    for size, blob in blobs:
        dim = 0 if size >= 256 else size  # 256 在 ICO 目录项里记作 0
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        payload += blob
        offset += len(blob)
    with open(path, "wb") as f:
        f.write(header + entries + payload)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    QApplication(sys.argv)

    blobs = []
    for size in sorted(APP_ICON_SIZES, reverse=True):
        blob = _png_blob(size) if size >= PNG_MIN_SIZE else _dib_blob(size)
        blobs.append((size, blob))
    _write_ico(OUTPUT, blobs)
    print(
        f"wrote {OUTPUT}: "
        f"{[(size, 'PNG' if size >= PNG_MIN_SIZE else 'DIB') for size, _ in blobs]}"
    )


if __name__ == "__main__":
    main()
