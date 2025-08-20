from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Collect all MediaPipe data files (models, configs, etc)
mediapipe_data = collect_data_files('mediapipe')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=mediapipe_data + [
        ('assets', 'assets'),
        ('fonts', 'fonts'),
        ('logout_redirect.html', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='Gesturefy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/gesturefy.ico'  
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Gesturefy_Windows'
)
