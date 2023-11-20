# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app/macos/main.py'],
    pathex=[],
    binaries=[],
    datas=[('html', 'html'), ('img', 'img')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
      'PySide6.QtNetwork', 
      'PySide6.QtSql', 
      'PyQt5',
      'PySide6.QtDBus',
      'PySide6.QtOpenGL',
      'PySide6.QtPdf',
      'PySide6.QtQml',
      'PySide6.QtQmlModels',
      'PySide6.QtQuick',
      'PySide6.QtVirtualKeyboard'
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Babel Tower',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='app/macos/Babel_Tower_macOS.icns',
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
    name='Babel Tower',
)
app = BUNDLE(
    coll,
    name='Babel Tower.app',
    icon='app/macos/Babel_Tower_macOS.icns',
    bundle_identifier=None,
)
