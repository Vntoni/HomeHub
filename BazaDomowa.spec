# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Ścieżki
project_root = Path.cwd()
view_dir = project_root / "View"
qml_dir = view_dir / "Example"
images_dir = view_dir / "images"

block_cipher = None

a = Analysis(
    [str(view_dir / 'main.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(qml_dir), 'View/Example'),
        (str(images_dir), 'View/images'),
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.QtQuickControls2',
        'qasync',
        'pyairstage',
        'pyairstage.airstageAC',
        'pyairstage.airstageApi',
        'ariston',
        'requests',
        'dotenv',
        'atlantic_client',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BazaDomowa',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Wyłącz konsolę w produkcji (zmień na True do debugowania)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Tutaj możesz dodać ikonę: 'icon.ico'
)
