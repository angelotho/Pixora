"""Gerenciamento de downloads das mídias finais (imagens em PNG/JPG, vídeos em MP4)."""

from __future__ import annotations

import logging
import os
import tempfile
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .converter import convert_image, needs_conversion
from .errors import CancelledError, DestinationError, PixoraError
from .filenames import (
    ConflictPolicy, build_base_name, detect_extension, resolve_target, sniff_image_extension,
)
from .http import MAX_IMAGE_BYTES, MAX_VIDEO_BYTES, MediaHttpClient, redact_url
from .models import VIDEO_EXTENSION, DownloadReport, FileResult, ImageFormat, ImageItem, PostInfo

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Progress:
    file_index: int          # 0-based
    file_count: int
    bytes_done: int
    bytes_total: int | None  # None quando o servidor não informa o tamanho

    @property
    def fraction(self) -> float:
        """Progresso geral entre 0 e 1."""
        if self.file_count == 0:
            return 1.0
        within = 0.0
        if self.bytes_total:
            within = min(1.0, self.bytes_done / self.bytes_total)
        return (self.file_index + within) / self.file_count


ProgressCallback = Callable[[Progress], None]


def ensure_writable_folder(folder: Path) -> None:
    """Cria a pasta se necessário e confirma permissão de escrita."""
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DestinationError(
            "Não foi possível criar a pasta de destino. Escolha outro local.", detail=str(exc)
        ) from exc
    if not folder.is_dir():
        raise DestinationError("O destino escolhido não é uma pasta.")
    try:
        with tempfile.TemporaryFile(dir=folder):
            pass
    except OSError as exc:
        raise DestinationError(detail=str(exc)) from exc


class DownloadManager:
    def __init__(self, http: MediaHttpClient | None = None,
                 policy: ConflictPolicy = ConflictPolicy.RENAME) -> None:
        self._http = http or MediaHttpClient()
        self.policy = policy

    def download(
        self,
        post: PostInfo,
        items: Sequence[ImageItem],
        folder: Path,
        *,
        on_progress: ProgressCallback | None = None,
        cancel: threading.Event | None = None,
        image_format: ImageFormat = ImageFormat.JPG,
    ) -> DownloadReport:
        folder = Path(folder)
        ensure_writable_folder(folder)
        report = DownloadReport(folder=folder)
        total_positions = max((i.position for i in post.images), default=1)
        count = len(items)

        for index, item in enumerate(items):
            if cancel is not None and cancel.is_set():
                report.cancelled = True
                break
            base = build_base_name(post.shortcode, item.position, total_positions)
            try:
                result = self._download_one(item, folder, base, index, count, on_progress, cancel,
                                            image_format)
            except CancelledError:
                report.cancelled = True
                break
            except PixoraError as exc:
                log.warning("Falha ao baixar %s: %s", redact_url(item.full_url), exc)
                result = FileResult(item=item, error=exc.user_message)
            except Exception as exc:  # noqa: BLE001 — nenhum erro de um arquivo pode derrubar o lote
                log.exception("Erro inesperado ao baixar %s", redact_url(item.full_url))
                result = FileResult(item=item, error="Erro inesperado ao salvar o arquivo.")
            report.results.append(result)

        if on_progress:
            on_progress(Progress(count, count, 0, None))
        return report

    def _download_one(
        self, item: ImageItem, folder: Path, base: str, index: int, count: int,
        on_progress: ProgressCallback | None, cancel: threading.Event | None,
        image_format: ImageFormat = ImageFormat.JPG,
    ) -> FileResult:
        part_path = folder / f".{base}.pixora-part"
        conv_path = folder / f".{base}.pixora-conv"
        max_bytes = MAX_VIDEO_BYTES if item.is_video else MAX_IMAGE_BYTES
        done = 0
        try:
            with self._http.open(item.full_url) as resp:
                length = resp.headers.get("Content-Length")
                total = int(length) if length and length.isdigit() else None
                content_type = resp.headers.get("Content-Type")
                head = b""

                def tick(n: int) -> None:
                    nonlocal done
                    done += n
                    if on_progress:
                        on_progress(Progress(index, count, done, total))

                try:
                    with open(part_path, "wb") as fh:
                        for chunk in self._http.iter_content(resp, cancel, tick, max_bytes):
                            if len(head) < 32:
                                head += chunk[: 32 - len(head)]
                            fh.write(chunk)
                except OSError as exc:
                    raise DestinationError(
                        "Não foi possível gravar o arquivo. Verifique o espaço em disco e as permissões da pasta.",
                        detail=str(exc),
                    ) from exc

            if done == 0:
                raise PixoraError("O servidor enviou um arquivo vazio.")
            if total is not None and done < total:
                raise PixoraError("O download ficou incompleto. Tente novamente.")
            final_path = part_path
            if item.is_video:
                if not _looks_like_mp4(head, content_type):
                    raise PixoraError("O arquivo recebido não é um vídeo MP4.")
                ext = VIDEO_EXTENSION
            else:
                if sniff_image_extension(head) is None and not (content_type or "").startswith("image/"):
                    raise PixoraError("O arquivo recebido não é uma imagem.")
                source_ext = detect_extension(head, content_type)
                ext = image_format.extension
                if needs_conversion(source_ext, image_format):
                    convert_image(part_path, conv_path, image_format)
                    final_path = conv_path

            target, skipped = resolve_target(folder, base, ext, self.policy)
            if skipped:
                return FileResult(item=item, path=target, skipped_existing=True)
            try:
                os.replace(final_path, target)
            except OSError as exc:
                raise DestinationError(detail=str(exc)) from exc
            log.info("Salvo %s (%d bytes)", target.name, done)
            return FileResult(item=item, path=target)
        finally:
            for tmp in (part_path, conv_path):
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    log.debug("Não foi possível remover arquivo temporário %s", tmp)


def _looks_like_mp4(head: bytes, content_type: str | None) -> bool:
    """Contêiner ISO-BMFF que não seja imagem (HEIC/AVIF), ou ``Content-Type`` de vídeo."""
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return sniff_image_extension(head) is None
    return (content_type or "").split(";", 1)[0].strip().lower() in ("video/mp4", "video/quicktime")
