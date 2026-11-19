"""Gera src/pixora/assets/pixora.ico (multi-resolução) a partir de assets/logo.png."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from pixora.ui.icons import logo_image  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)


def render_png(size: int) -> bytes:
    src = logo_image()
    if src.isNull():
        raise SystemExit("assets/logo.png não encontrado")
    img = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    buf = QByteArray()
    dev = QBuffer(buf)
    dev.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(dev, "PNG")
    return bytes(buf)


def build_ico(images: list[tuple[int, bytes]]) -> bytes:
    """ICO com entradas PNG (suportado desde o Windows Vista)."""
    import struct
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, png in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset + len(blobs))
        blobs += png
    return header + entries + blobs


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841
    out = ROOT / "src" / "pixora" / "assets"
    out.mkdir(parents=True, exist_ok=True)
    (out / "pixora.ico").write_bytes(build_ico([(s, render_png(s)) for s in SIZES]))
    (out / "pixora.png").write_bytes(render_png(256))
    print("Ícone gerado em", out / "pixora.ico")


if __name__ == "__main__":
    main()
