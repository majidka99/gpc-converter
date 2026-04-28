# PyInstaller build specification for GPC Converter (Windows)
# Usage: pyinstaller gpc_converter_gui.spec

# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['gpc_converter_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('README.md', '.'), ('convert_to_gpc.py', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='GPC Converter',
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
