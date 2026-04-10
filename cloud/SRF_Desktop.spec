# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=[('C:\\Python313\\python3.dll', '.')],
    datas=[('app', 'app'), ('..\\aparencia', 'aparencia'), ('..\\atm_v5.py', '.'), ('..\\srf_excel_format.py', '.'), ('..\\config.json', '.'), ('..\\testes', 'testes'), ('..\\tutorial', 'tutorial')],
    hiddenimports=['app.main', 'app.auth', 'app.session', 'app.storage', 'app.report_parser', 'app.rules_engine', 'app.ollama_bridge'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'tensorflow', 'transformers', 'scipy', 'sklearn', 'cv2', 'onnxruntime'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SRF_Desktop',
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
    icon=['E:\\cli_planilhas\\cloud\\assets\\srf_lion_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SRF_Desktop',
)
