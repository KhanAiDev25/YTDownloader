# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

block_cipher = None

yt_dlp_hidden = collect_submodules('yt_dlp')

# ALL required DLLs from conda
conda_bin = r'C:\ProgramData\miniconda3\Library\bin'
dlls_to_bundle = [
    (f'{conda_bin}\\ffi.dll', '.'),
    (f'{conda_bin}\\liblzma.dll', '.'),
    (f'{conda_bin}\\libbz2.dll', '.'),
    (f'{conda_bin}\\libmpdec-4.dll', '.'),
    (f'{conda_bin}\\libexpat.dll', '.'),
    (f'{conda_bin}\\sqlite3.dll', '.'),
    (f'{conda_bin}\\libssl-3-x64.dll', '.'),
    (f'{conda_bin}\\libcrypto-3-x64.dll', '.'),
    (r'C:\Users\arkha\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe', '.'),
]

a = Analysis(
    ['downloader.py'],
    pathex=[],
    binaries=dlls_to_bundle,
    datas=[],
    hiddenimports=yt_dlp_hidden + ['_ctypes', '_ssl', 'ctypes', 'ssl', '_bz2', '_lzma', '_decimal', '_sqlite3', 'pyexpat'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='YTDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)