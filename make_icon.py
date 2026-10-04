"""生成 GetUp.ico —— 应用/任务栏图标（多尺寸）。

图形取自 tray.create_app_icon_pixmap()，与运行时窗口图标共用同一套画法，
避免出现两份会各自漂移的图标定义。

用法: python make_icon.py
"""

import os
import struct
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QApplication

from tray import APP_ICON_SIZES, create_app_icon_pixmap

OUTPUT = "GetUp.ico"


def _png_blob(size):
    pixmap = create_app_icon_pixmap(size)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    return bytes(buffer.data())


def _write_ico(path, blobs):
    """写出 PNG 载荷的 .ico。

    自 Vista 起 Windows 支持 PNG 压缩的图标项；PyInstaller 只把各项原样
    拷进 RT_ICON 资源，不解析内部格式，因此无需引入图像库。
    """
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

    blobs = [(size, _png_blob(size)) for size in sorted(APP_ICON_SIZES, reverse=True)]
    _write_ico(OUTPUT, blobs)
    print(f"wrote {OUTPUT}: {[size for size, _ in blobs]}")


if __name__ == "__main__":
    main()
