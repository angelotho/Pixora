"""Conversão de imagens baixadas para o formato escolhido pelo usuário (PNG ou JPG).

Usa o ``QImage`` do Qt (já presente no aplicativo), que é reentrante e pode ser usado
fora da thread principal. Princípios:

* se o arquivo já está no formato pedido, ele é mantido **byte a byte** (sem recompressão);
* PNG é sem perdas: a conversão para PNG preserva integralmente os pixels decodificados;
* JPG usa qualidade alta (95) e, quando a imagem tem transparência, ela é composta
  sobre fundo branco (JPG não suporta canal alfa).
"""

from __future__ import annotations

from pathlib import Path

from .errors import PixoraError
from .models import ImageFormat

JPEG_QUALITY = 95

_EXT_TO_FORMAT = {".jpg": ImageFormat.JPG, ".jpeg": ImageFormat.JPG, ".png": ImageFormat.PNG}


def needs_conversion(source_ext: str, target: ImageFormat) -> bool:
    return _EXT_TO_FORMAT.get(source_ext.lower()) is not target


def convert_image(source: Path, dest: Path, target: ImageFormat) -> None:
    """Decodifica ``source`` e grava ``dest`` no formato ``target``.

    Levanta :class:`PixoraError` se a imagem não puder ser lida ou gravada.
    """
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
    from PySide6.QtGui import QColor, QImage, QImageReader, QPainter

    # Lê da memória para não manter o arquivo aberto (no Windows isso impediria removê-lo).
    try:
        data = QByteArray(source.read_bytes())
    except OSError as exc:
        raise PixoraError(f"Não foi possível converter a imagem para {target.label}.", detail=str(exc)) from exc
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buffer)
    reader.setAutoTransform(True)  # respeita a orientação EXIF
    image = reader.read()
    buffer.close()
    if image.isNull():
        raise PixoraError(
            f"Não foi possível converter a imagem para {target.label}: formato de origem não suportado.",
            detail=reader.errorString(),
        )

    if target is ImageFormat.JPG:
        if image.hasAlphaChannel():
            flat = QImage(image.size(), QImage.Format.Format_RGB32)
            flat.setDevicePixelRatio(image.devicePixelRatio())
            flat.fill(QColor(Qt.GlobalColor.white))
            painter = QPainter(flat)
            painter.drawImage(0, 0, image)
            painter.end()
            image = flat
        ok = image.save(str(dest), "JPG", JPEG_QUALITY)
    else:
        ok = image.save(str(dest), "PNG")  # compressão padrão; sem perdas
    if not ok:
        raise PixoraError(f"Não foi possível gravar a imagem em {target.label}.")
