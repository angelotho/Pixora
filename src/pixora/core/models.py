"""Modelos de dados imutáveis compartilhados entre as camadas."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class PostKind(str, Enum):
    SINGLE = "single"
    CAROUSEL = "carousel"


@dataclass(frozen=True)
class ParsedPostUrl:
    """Resultado da validação de um link."""

    shortcode: str
    canonical_url: str


@dataclass(frozen=True)
class ImageItem:
    """Uma imagem de uma publicação.

    ``position`` é a posição (1-based) na publicação original, contando também
    eventuais vídeos do carrossel, para que os nomes de arquivo reflitam a ordem real.
    """

    position: int
    full_url: str
    thumbnail_url: str
    width: int | None = None
    height: int | None = None

    @property
    def aspect_ratio(self) -> float:
        if self.width and self.height:
            return self.width / self.height
        return 1.0


@dataclass(frozen=True)
class PostInfo:
    shortcode: str
    url: str
    kind: PostKind
    images: tuple[ImageItem, ...]
    owner: str | None = None
    skipped_videos: int = 0

    @property
    def image_count(self) -> int:
        return len(self.images)


@dataclass
class FileResult:
    item: ImageItem
    path: Path | None = None
    error: str | None = None
    skipped_existing: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class DownloadReport:
    folder: Path
    results: list[FileResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def saved(self) -> list[FileResult]:
        return [r for r in self.results if r.ok and r.path is not None and not r.skipped_existing]

    @property
    def skipped(self) -> list[FileResult]:
        return [r for r in self.results if r.skipped_existing]

    @property
    def failed(self) -> list[FileResult]:
        return [r for r in self.results if not r.ok]
