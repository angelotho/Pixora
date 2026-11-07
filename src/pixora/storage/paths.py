"""Diretórios do aplicativo no perfil do usuário (nunca na pasta do executável)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "Pixora"


def _base(env_var: str, fallback: Path) -> Path:
    override = os.environ.get("PIXORA_HOME")
    if override:
        return Path(override)
    value = os.environ.get(env_var)
    return Path(value) / APP_DIR_NAME if value else fallback


def config_dir() -> Path:
    """%APPDATA%\\Pixora — configurações e histórico (acompanham o perfil móvel)."""
    if sys.platform == "win32":
        path = _base("APPDATA", Path.home() / "AppData" / "Roaming" / APP_DIR_NAME)
    else:
        path = _base("XDG_CONFIG_HOME", Path.home() / ".config" / "pixora")
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    """%LOCALAPPDATA%\\Pixora\\logs — logs locais (não sincronizados)."""
    if sys.platform == "win32":
        base = _base("LOCALAPPDATA", Path.home() / "AppData" / "Local" / APP_DIR_NAME)
    else:
        base = _base("XDG_STATE_HOME", Path.home() / ".local" / "state" / "pixora")
    path = base / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _windows_pictures_dir() -> Path | None:
    """Pasta Imagens real do usuário (respeita redirecionamento para OneDrive, outro disco etc.)."""
    try:
        import ctypes
        from ctypes import wintypes
        from uuid import UUID

        class GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                        ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

        raw = UUID("33E28130-4E1E-4676-835A-98395C3BC3BB").bytes_le  # FOLDERID_Pictures
        guid = GUID.from_buffer_copy(raw)
        out = ctypes.c_wchar_p()
        shell32 = ctypes.windll.shell32  # type: ignore[attr-defined]
        if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) != 0:
            return None
        try:
            return Path(out.value) if out.value else None
        finally:
            ctypes.windll.ole32.CoTaskMemFree(out)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return None


def default_download_dir() -> Path:
    candidates = [_windows_pictures_dir()] if sys.platform == "win32" else []
    candidates.append(Path.home() / "Pictures")
    for pictures in candidates:
        if pictures and pictures.is_dir():
            return pictures / "Pixora"
    return Path.home() / "Pixora"
