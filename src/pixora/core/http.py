"""Cliente HTTP restrito aos servidores de mídia do Instagram.

* Somente HTTPS e somente hosts de CDN conhecidos.
* Redirecionamentos são seguidos manualmente e revalidados a cada salto.
* Limites de tempo em todas as requisições e limite de tamanho por arquivo.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from urllib.parse import urljoin, urlsplit

import requests

from pixora import __version__
from .errors import CancelledError, DownloadError, NetworkError

log = logging.getLogger(__name__)

ALLOWED_MEDIA_HOST_SUFFIXES = (".cdninstagram.com", ".fbcdn.net")
CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 30.0
MAX_REDIRECTS = 3
MAX_IMAGE_BYTES = 60 * 1024 * 1024
MAX_VIDEO_BYTES = 2 * 1024 * 1024 * 1024
CHUNK_SIZE = 64 * 1024


def is_allowed_media_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or "").lower().rstrip(".")
    return (
        parts.scheme == "https"
        and parts.username is None
        and port in (None, 443)
        and any(host.endswith(suffix) for suffix in ALLOWED_MEDIA_HOST_SUFFIXES)
    )


def redact_url(url: str) -> str:
    """Remove a query string (que contém assinaturas/tokens) antes de registrar em log."""
    try:
        p = urlsplit(url)
        return f"{p.scheme}://{p.hostname}{p.path}"
    except ValueError:
        return "<url inválida>"


class MediaHttpClient:
    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()
        self._session.headers.update({
            "User-Agent": f"Pixora/{__version__} (+desktop)",
            "Accept": "image/avif,image/webp,image/jpeg,image/png,image/*;q=0.8",
        })

    @contextmanager
    def open(self, url: str) -> Iterator[requests.Response]:
        """Abre uma resposta em streaming, validando o host em cada redirecionamento."""
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            if not is_allowed_media_url(current):
                raise DownloadError(
                    "O endereço da imagem não pertence aos servidores do Instagram e foi bloqueado.",
                    detail=f"host bloqueado: {redact_url(current)}",
                )
            try:
                resp = self._session.get(
                    current, stream=True, allow_redirects=False,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                )
            except requests.Timeout as exc:
                raise NetworkError("O servidor demorou demais para responder.", detail=str(exc)) from exc
            except requests.RequestException as exc:
                raise NetworkError(detail=str(exc)) from exc

            if resp.is_redirect:
                location = resp.headers.get("Location", "")
                resp.close()
                current = urljoin(current, location)
                continue

            try:
                if resp.status_code in (403, 404, 410):
                    raise DownloadError(
                        "O link da imagem expirou ou não está mais disponível. Analise a publicação novamente.",
                        detail=f"HTTP {resp.status_code} em {redact_url(current)}",
                    )
                if resp.status_code == 429:
                    raise DownloadError(
                        "O servidor limitou temporariamente os downloads. Aguarde alguns minutos.",
                        detail="HTTP 429",
                    )
                if resp.status_code >= 400:
                    raise DownloadError(
                        f"O servidor recusou o download (código {resp.status_code}).",
                        detail=f"HTTP {resp.status_code} em {redact_url(current)}",
                    )
                yield resp
            finally:
                resp.close()
            return
        raise DownloadError("Redirecionamentos demais ao baixar a imagem.")

    def iter_content(
        self,
        resp: requests.Response,
        cancel: threading.Event | None = None,
        on_chunk: Callable[[int], None] | None = None,
        max_bytes: int = MAX_IMAGE_BYTES,
    ) -> Iterator[bytes]:
        total = 0
        try:
            for chunk in resp.iter_content(CHUNK_SIZE):
                if cancel is not None and cancel.is_set():
                    raise CancelledError()
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise DownloadError("O arquivo é maior do que o tamanho máximo permitido.")
                if on_chunk:
                    on_chunk(len(chunk))
                yield chunk
        except requests.RequestException as exc:
            raise NetworkError("A conexão foi interrompida durante o download.", detail=str(exc)) from exc

    def fetch_bytes(self, url: str, cancel: threading.Event | None = None) -> bytes:
        """Baixa um arquivo pequeno inteiro para a memória (usado para miniaturas)."""
        with self.open(url) as resp:
            return b"".join(self.iter_content(resp, cancel))
