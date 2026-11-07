"""Nomes de arquivo, detecção de formato e tratamento de conflitos."""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/pjpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "image/avif": ".avif",
}


class ConflictPolicy(str, Enum):
    RENAME = "rename"   # cria "nome (2).jpg"
    SKIP = "skip"       # mantém o arquivo existente


def sanitize_component(value: str, fallback: str = "arquivo") -> str:
    cleaned = _UNSAFE_CHARS.sub("_", value).strip(" .")
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in _WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned[:100]


def build_base_name(shortcode: str, position: int, total_positions: int = 1) -> str:
    """``instagram_<código>_<posição>`` com pelo menos 2 dígitos."""
    width = max(2, len(str(total_positions)))
    return f"instagram_{sanitize_component(shortcode)}_{position:0{width}d}"


def detect_extension(head: bytes, content_type: str | None = None) -> str:
    """Determina a extensão pelo conteúdo real (assinatura do arquivo).

    O cabeçalho HTTP é usado apenas como segunda opção, e ``.jpg`` como último recurso.
    """
    sniffed = sniff_image_extension(head)
    if sniffed:
        return sniffed
    if content_type:
        mime = content_type.split(";", 1)[0].strip().lower()
        if mime in CONTENT_TYPE_EXT:
            return CONTENT_TYPE_EXT[mime]
    return ".jpg"


def sniff_image_extension(head: bytes) -> str | None:
    """Extensão a partir da assinatura binária, ou ``None`` se não for imagem conhecida."""
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if len(head) >= 12 and head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"avif", b"avis"):
            return ".avif"
        if brand in (b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis"):
            return ".heic"
        if brand in (b"mif1", b"msf1"):
            return ".heif"
    return None


def resolve_target(folder: Path, base_name: str, ext: str, policy: ConflictPolicy) -> tuple[Path, bool]:
    """Escolhe o caminho final. Retorna ``(caminho, ja_existia_e_foi_pulado)``."""
    candidate = folder / f"{base_name}{ext}"
    if not candidate.exists():
        return candidate, False
    if policy is ConflictPolicy.SKIP:
        return candidate, True
    n = 2
    while True:
        candidate = folder / f"{base_name} ({n}){ext}"
        if not candidate.exists():
            return candidate, False
        n += 1
