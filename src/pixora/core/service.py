"""Fachada da lógica de negócio usada pela interface.

Mantém a interface gráfica livre de detalhes de rede, integração e arquivos.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from pathlib import Path

from .downloader import DownloadManager, Progress
from .filenames import ConflictPolicy
from .http import MediaHttpClient
from .models import DownloadReport, ImageFormat, ImageItem, ParsedPostUrl, PostInfo
from .url_validator import parse_post_url

log = logging.getLogger(__name__)


class PixoraService:
    def __init__(self, provider, http: MediaHttpClient | None = None) -> None:  # provider: PostProvider
        self.provider = provider
        self.http = http or MediaHttpClient()
        self.downloader = DownloadManager(self.http)

    @staticmethod
    def validate(raw_url: str) -> ParsedPostUrl:
        return parse_post_url(raw_url)

    def fetch(self, parsed: ParsedPostUrl) -> PostInfo:
        log.info("Analisando publicação %s via %s", parsed.shortcode, self.provider.name)
        post = self.provider.fetch_post(parsed.shortcode)
        log.info("Publicação %s: %s, %d imagem(ns), %d vídeo(s), %d ignorado(s)",
                 post.shortcode, post.kind.value, post.photo_count, post.video_count, post.skipped_videos)
        return post

    def download(
        self,
        post: PostInfo,
        items: Sequence[ImageItem],
        folder: Path,
        policy: ConflictPolicy,
        cancel: threading.Event | None = None,
        report: Callable[[Progress], None] | None = None,
        image_format: ImageFormat = ImageFormat.JPG,
    ) -> DownloadReport:
        self.downloader.policy = policy
        result = self.downloader.download(post, items, folder, on_progress=report, cancel=cancel,
                                          image_format=image_format)
        log.info("Download de %s: %d salvos, %d pulados, %d falhas, cancelado=%s",
                 post.shortcode, len(result.saved), len(result.skipped), len(result.failed), result.cancelled)
        return result
