"""Ícones vetoriais (traço, estilo linear) renderizados em tempo de execução.

Os ícones são desenhados em SVG e coloridos de acordo com o tema, o que mantém
nitidez em qualquer escala de DPI. A exceção é o símbolo do Pixora, que vem de
``assets/logo.png``.
"""

from __future__ import annotations

import hashlib
import tempfile
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

_PATHS: dict[str, str] = {
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
            '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "paste": '<rect x="8" y="2" width="8" height="4" rx="1"/>'
             '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.35-4.35"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/>'
                '<path d="M12 15V3"/>',
    "folder": '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4'
              'a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    "history": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>'
               '<path d="M12 7v5l4 2"/>',
    "settings": '<path d="M20 7h-9"/><path d="M14 17H5"/><circle cx="17" cy="17" r="3"/>'
                '<circle cx="7" cy="7" r="3"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "alert": '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
    "lock": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "wifi-off": '<path d="M12 20h.01"/><path d="M8.5 16.43a5 5 0 0 1 7 0"/><path d="M2 8.82a15 15 0 0 1 4.17-2.65"/>'
                '<path d="M10.66 5c4.01-.36 8.14.9 11.34 3.76"/><path d="M16.85 11.25a10 10 0 0 1 2.22 1.68"/>'
                '<path d="M5 13a10 10 0 0 1 5.24-2.76"/><path d="m2 2 20 20"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/>'
             '<path d="m21 15-3.09-3.09a2 2 0 0 0-2.82 0L6 21"/>',
    "images": '<path d="M18 22H4a2 2 0 0 1-2-2V6"/><path d="m22 13-1.3-1.3a2.4 2.4 0 0 0-3.4 0L11 18"/>'
              '<circle cx="12" cy="8" r="2"/><rect x="6" y="2" width="16" height="16" rx="2"/>',
    "check-circle": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "external": '<path d="M15 3h6v6"/><path d="M10 14 21 3"/>'
                '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    "trash": '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>'
             '<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    "refresh": '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>',
    "select-all": '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="m8 12 3 3 5-6"/>',
    "select-none": '<rect x="3" y="3" width="18" height="18" rx="3"/>',
    "video-off": '<path d="M10.66 6H14a2 2 0 0 1 2 2v2.5l5.25-3.06A.5.5 0 0 1 22 7.87v8.19"/>'
                 '<path d="M16 16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2"/><path d="m2 2 20 20"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
}

# Símbolo oficial do Pixora: PNG quadrado com fundo transparente (cor sólida da marca).
LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
BRAND_COLOR = "#5D01B2"


def svg_markup(name: str, color: str, stroke: float = 2.0) -> str:
    body = _PATHS[name]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


def _render(svg: str, size: int, dpr: float) -> QPixmap:
    px = max(1, round(size * dpr))
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, px, px))
    painter.end()
    pixmap.setDevicePixelRatio(dpr)
    return pixmap


def _dpr() -> float:
    app = QApplication.instance()
    screen = app.primaryScreen() if app else None  # type: ignore[union-attr]
    return max(1.0, screen.devicePixelRatio() if screen else 1.0)


@lru_cache(maxsize=256)
def pixmap(name: str, color: str, size: int = 18, stroke: float = 2.0) -> QPixmap:
    return _render(svg_markup(name, color, stroke), size, max(2.0, _dpr()))


@lru_cache(maxsize=256)
def icon(name: str, color: str, size: int = 18, disabled_color: str | None = None) -> QIcon:
    ic = QIcon()
    ic.addPixmap(pixmap(name, color, size), QIcon.Mode.Normal)
    ic.addPixmap(pixmap(name, color, size), QIcon.Mode.Active)
    if disabled_color:
        ic.addPixmap(pixmap(name, disabled_color, size), QIcon.Mode.Disabled)
    return ic


@lru_cache(maxsize=8)
def logo_image(color: str = BRAND_COLOR) -> QImage:
    """Símbolo em alta resolução, recolorido (a forma vem do canal alfa). Nulo se o arquivo faltar."""
    img = QImage(str(LOGO_PATH))
    if img.isNull():
        return img
    img = img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    if color.lower() != BRAND_COLOR.lower():
        p = QPainter(img)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p.fillRect(img.rect(), QColor(color))
        p.end()
    return img


def _scaled_logo(size: int, dpr: float, color: str) -> QPixmap:
    px = max(1, round(size * dpr))
    img = logo_image(color)
    if img.isNull():
        pm = QPixmap(px, px)
        pm.fill(Qt.GlobalColor.transparent)
    else:
        pm = QPixmap.fromImage(img.scaled(px, px, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
    pm.setDevicePixelRatio(dpr)
    return pm


def logo_pixmap(size: int, color: str = BRAND_COLOR) -> QPixmap:
    return _scaled_logo(size, max(2.0, _dpr()), color)


def app_icon() -> QIcon:
    ic = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        ic.addPixmap(_scaled_logo(s, 1.0, BRAND_COLOR))
    return ic


def icon_file(name: str, color: str, stroke: float = 2.0) -> str:
    """Grava o SVG em um diretório temporário e retorna o caminho (para uso em QSS)."""
    svg = svg_markup(name, color, stroke)
    digest = hashlib.sha1(svg.encode()).hexdigest()[:12]
    folder = Path(tempfile.gettempdir()) / "pixora-icons"
    path = folder / f"{name}-{digest}.svg"
    try:
        if not path.exists():
            folder.mkdir(parents=True, exist_ok=True)
            path.write_text(svg, encoding="utf-8")
    except OSError:
        return ""
    return path.as_posix()


def size(px: int) -> QSize:
    return QSize(px, px)
