# -*- mode: python ; coding: utf-8 -*-
# Gera o Pixora para Windows.  Uso:  pyinstaller pixora.spec --noconfirm
# Defina PIXORA_ONEFILE=1 para gerar um único .exe (inicia mais devagar).
import os

ONEFILE = os.environ.get("PIXORA_ONEFILE") == "1"

# Módulos Qt que o Pixora não usa: reduzem bastante o tamanho do pacote.
QT_EXCLUDES = [
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtSql", "PySide6.QtTest",
    "PySide6.QtDBus", "PySide6.QtConcurrent", "PySide6.QtXml", "PySide6.QtPrintSupport",
    "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtUiTools", "PySide6.QtMultimedia",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtPdf",
]

a = Analysis(
    ["run_pixora.py"],
    pathex=["src"],
    binaries=[],
    datas=[("src/pixora/assets", "pixora/assets")],
    hiddenimports=["PySide6.QtSvg"],
    excludes=["tkinter", "pytest", "PyInstaller", *QT_EXCLUDES],
    noarchive=False,
)
# Remove o OpenGL por software (~20 MB; não usado por um app de widgets) e
# traduções do Qt que não sejam o português.
a.binaries = [b for b in a.binaries if "opengl32sw" not in b[0].lower()]
a.datas = [
    d for d in a.datas
    if "translations" not in d[0].replace("\\", "/").split("/")
    or os.path.basename(d[0]).startswith("qtbase_pt")
]
pyz = PYZ(a.pure)

exe_kwargs = dict(
    name="Pixora",
    icon="src/pixora/assets/pixora.ico",
    version="scripts/version_info.txt",
    console=False,
    upx=False,  # UPX aumenta falsos positivos de antivírus
    debug=False,
    strip=False,
)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], runtime_tmpdir=None, **exe_kwargs)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exe_kwargs)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Pixora")
