"""Modelos de dados imutáveis compartilhados entre as camadas."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ImageFormat(str, Enum):
    """Formato de saída escolhido pelo usuário para as imagens (vídeos são sempre MP4)."""

    JPG = "jpg"
    PNG = "png"

    @property
    def extension(self) -> str:
        return f".{self.value}"

    @property
    def label(self) -> str:
        return self.value.upper()


VIDEO_EXTENSION = ".mp4"


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
    """Uma mídia (imagem ou vídeo) de uma publicação.

    Para vídeos, ``full_url`` aponta para o arquivo MP4 e ``thumbnail_url`` para a capa.

    ``position`` é a posição (1-based) na publicação original, contando também
    eventuais vídeos do carrossel, para que os nomes de arquivo reflitam a ordem real.
    """

    position: int
    full_url: str
    thumbnail_url: str
    width: int | None = None
    height: int | None = None
    is_video: bool = False

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

    @property
    def video_count(self) -> int:
        return sum(1 for i in self.images if i.is_video)

    @property
    def photo_count(self) -> int:
        return self.image_count - self.video_count


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
