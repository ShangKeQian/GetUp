"""Build script for GetUp - packages the app as a standalone Windows executable."""

import subprocess
import sys
import os


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "GetUp",
        "main.py",
    ]

    print("Building GetUp.exe...")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.join("dist", "GetUp.exe")
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\nBuild successful! Output: {exe_path} ({size_mb:.1f} MB)")
    else:
        print("\nBuild failed!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
