"""Build script for GetUp - packages the app as a standalone Windows executable."""

import os
import shutil
import subprocess
import sys
import winreg

import mediapipe

from config import VERSION

VERSION_FILE = "version_info.txt"
# 部署目标：必须在 OneDrive 等同步目录之外（见 _deploy 的说明）
DEPLOY_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "GetUp")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOTIFY_KEY = r"Control Panel\NotifyIconSettings"


def _write_version_info(version: str) -> None:
    """生成 PyInstaller 版本资源文件（exe 的 RT_VERSION）。

    exe 缺少版本信息资源是安全软件误报的常见诱因（未签名 + 无元数据的裸产物
    画像最差），因此从 config.VERSION 单点生成，保证版本号只有一处来源。
    写为 utf-8-sig：PyInstaller 按二进制读取该文件并依 BOM/编码声明解码，
    带 BOM 才能让文件里的中文注释被正确解析。
    """
    quad = tuple(([int(p) for p in version.split(".")] + [0, 0, 0, 0])[:4])
    content = f"""# 由 build.py 依据 config.VERSION 自动生成，请勿手工编辑
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={quad}, prodvers={quad}, mask=0x3f, flags=0x0,
    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('080404b0', [
        StringStruct('CompanyName', 'ShangKeQian'),
        StringStruct('FileDescription', 'GetUp - 久坐提醒'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', 'GetUp'),
        StringStruct('OriginalFilename', 'GetUp.exe'),
        StringStruct('ProductName', 'GetUp'),
        StringStruct('ProductVersion', '{version}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [0x0804, 1200])])
  ]
)
"""
    with open(VERSION_FILE, "w", encoding="utf-8-sig") as f:
        f.write(content)


def _promote_tray_icon(exe: str) -> bool:
    """若 shell 已为该 exe 建立托盘条目，则置 IsPromoted=1（固定显示在任务栏）。

    Windows 11 对**新**注册的托盘条目默认不给 IsPromoted，图标会落进
    "隐藏的图标"溢出区，用户看到的就是"没有托盘图标"。该条目按 exe 路径记账，
    所以换目录部署后会生成新条目、需要重新固定。
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, NOTIFY_KEY) as root:
            for i in range(winreg.QueryInfoKey(root)[0]):
                name = winreg.EnumKey(root, i)
                with winreg.OpenKey(root, name) as sub:
                    try:
                        value = winreg.QueryValueEx(sub, "ExecutablePath")[0]
                    except FileNotFoundError:
                        continue
                    if value.lower() == exe.lower():
                        with winreg.OpenKey(root, name, 0, winreg.KEY_SET_VALUE) as w:
                            winreg.SetValueEx(w, "IsPromoted", 0, winreg.REG_DWORD, 1)
                        return True
    except OSError:
        pass
    return False


def _deploy(dist_dir: str) -> None:
    """把产物部署到同步目录之外，并让自启动与托盘固定指向新位置。

    **不要直接从项目目录（本项目位于 OneDrive 同步范围内）运行 dist 产物**：
    同步驱动会让 PyInstaller 引导程序读不到自身内嵌的 PKG 归档，启动时弹出标题为
    "Error" 的对话框、正文为 "Could not load PyInstaller's embedded PKG archive"；
    进程因阻塞在该对话框上而留在任务管理器，但 Qt 从未初始化，因此没有托盘图标。
    """
    if not DEPLOY_DIR or not os.environ.get("LOCALAPPDATA"):
        print("部署失败：未找到 LOCALAPPDATA", file=sys.stderr)
        return
    # 覆盖式拷贝（不先删除目标目录，避开批量删除保护）
    shutil.copytree(dist_dir, DEPLOY_DIR, dirs_exist_ok=True)
    exe = os.path.join(DEPLOY_DIR, "GetUp.exe")
    print(f"\n已部署到 {DEPLOY_DIR}")

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_ALL_ACCESS) as key:
            try:
                winreg.QueryValueEx(key, "GetUp")
            except FileNotFoundError:
                pass  # 未启用开机自启，不擅自新建
            else:
                winreg.SetValueEx(key, "GetUp", 0, winreg.REG_SZ, f'"{exe}"')
                print("自启动项已指向新路径")
    except OSError:
        print("自启动项更新失败（可在应用设置里重新勾选）")

    if _promote_tray_icon(exe):
        print("托盘图标已设为固定显示")
    else:
        print("提示：首次运行后，把托盘图标从「隐藏的图标」拖到任务栏即可固定")

    print(f"\n请从 {exe} 启动；不要运行 dist 目录内的副本。")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    mp_path = os.path.dirname(mediapipe.__file__)

    _write_version_info(VERSION)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--windowed",
        "--name", "GetUp",
        "--icon", "GetUp.ico",
        "--version-file", VERSION_FILE,
        "-y",
        "--add-data", f"blaze_face_short_range.tflite;.",
        "--add-data", f"{mp_path}/tasks/c/libmediapipe.dll;mediapipe/tasks/c/",
        "--add-data", f"{mp_path}/modules;mediapipe/modules/",
        "--add-data", f"{mp_path}/tasks/metadata;mediapipe/tasks/metadata/",
        "--hidden-import", "cv2",
        "--hidden-import", "mediapipe",
        "--hidden-import", "mediapipe.tasks",
        "--hidden-import", "mediapipe.tasks.python",
        "--hidden-import", "mediapipe.tasks.python.vision",
        # GetUp 只做脸检测，从不调用 mediapipe 的绘图函数；matplotlib 仅被
        # drawing_utils 间接引用。排除真实 matplotlib（detectors/camera.py 用空 stub
        # 顶替），省体积、省启动时间，也避免其字体缓存产生临时目录。
        "--exclude-module", "matplotlib",
        "main.py",
    ]

    print(f"Building GetUp.exe (v{VERSION})...")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        dist_dir = os.path.join("dist", "GetUp")
        if "--deploy" in sys.argv:
            _deploy(dist_dir)
        else:
            print(f"\nBuild successful! Output folder: {dist_dir}")
            print("注意：本目录位于 OneDrive 同步范围内，直接运行 dist 产物会启动失败")
            print("     （Could not load PyInstaller's embedded PKG archive）。")
            print("     正式使用请改用：python build.py --deploy")
    else:
        print("\nBuild failed!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
