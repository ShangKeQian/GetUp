# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('blaze_face_short_range.tflite', '.'), ('C:\\Users\\ShangKeQian\\AppData\\Roaming\\Python\\Python313\\site-packages\\mediapipe/tasks/c/libmediapipe.dll', 'mediapipe/tasks/c/'), ('C:\\Users\\ShangKeQian\\AppData\\Roaming\\Python\\Python313\\site-packages\\mediapipe/modules', 'mediapipe/modules/'), ('C:\\Users\\ShangKeQian\\AppData\\Roaming\\Python\\Python313\\site-packages\\mediapipe/tasks/metadata', 'mediapipe/tasks/metadata/')],
    hiddenimports=['pynput.keyboard._win32', 'pynput.mouse._win32', 'mediapipe', 'mediapipe.tasks', 'mediapipe.tasks.python', 'mediapipe.tasks.python.vision'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GetUp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GetUp',
)
