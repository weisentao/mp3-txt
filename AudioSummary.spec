# -*- mode: python ; coding: utf-8 -*-
import os
import sys

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from PyInstaller.utils.hooks import collect_all, copy_metadata

datas = [('src', 'src')]
binaries = []
hiddenimports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtWidgets',
    'PyQt5.QtGui',
    'pydub',
]

for pkg in ['faster_whisper', 'ctranslate2']:
    try:
        d, b, h = collect_all(pkg)
        datas.extend(d)
        binaries.extend(b)
        hiddenimports.extend(h)
    except Exception as e:
        print(f"collect_all notice for {pkg}: {e}")

for meta in ['huggingface_hub', 'tqdm', 'regex', 'requests', 'packaging', 'filelock', 'numpy', 'tokenizers']:
    try:
        datas.extend(copy_metadata(meta))
    except Exception as e:
        print(f"copy_metadata notice for {meta}: {e}")

def dedupe_entries(entries):
    seen = set()
    res = []
    for s, d in entries:
        norm = (os.path.normpath(str(s)).lower(), os.path.normpath(str(d)).lower())
        if norm not in seen:
            seen.add(norm)
            res.append((s, d))
    return res

datas = dedupe_entries(datas)
binaries = dedupe_entries(binaries)
hiddenimports = list(dict.fromkeys(hiddenimports))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'pytest', 'pytest_qt'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AudioSummary',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name='AudioSummary',
)
