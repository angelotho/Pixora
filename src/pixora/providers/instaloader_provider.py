"""Integração com o Instagram via Instaloader, em modo anônimo (somente conteúdo público).

Decisões:
* nenhuma sessão, login, cookie ou senha é utilizada;
* uma única tentativa por consulta (``max_connection_attempts=1``);
* em caso de limite de requisições o controlador de taxa **falha imediatamente**
  em vez de dormir por minutos (o que pareceria um travamento), e o usuário é
  orientado a aguardar;
* os dados brutos são convertidos para os modelos do Pixora aqui, de modo que
  mudanças no formato do Instagram fiquem contidas neste módulo.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import requests

from pixora.core.errors import (
    AccessRestrictedError, NetworkError, PixoraError, PostUnavailableError,
    ProviderBrokenError, RateLimitedError, UnsupportedContentError,
)
from pixora.core.models import ImageItem, PostInfo, PostKind

log = logging.getLogger(__name__)

# Largura mínima da miniatura: carrosséis aparecem em grade; posts únicos, em destaque.
THUMB_WIDTH_GRID = 480
THUMB_WIDTH_SINGLE = 1080
REQUEST_TIMEOUT = 20.0
# Esperas curtas (cortesia entre requisições) são aceitas; esperas longas indicam limite.
MAX_POLITE_SLEEP = 4.0
# Intervalo mínimo entre consultas ao Instagram (substitui a pausa aleatória de até 15 s do
# Instaloader, que faria a interface parecer travada).
MIN_QUERY_INTERVAL = 2.5

try:  # importado de forma tardia/protegida para que o app abra mesmo sem a biblioteca
    import instaloader
    from instaloader import exceptions as ilx
except Exception:  # noqa: BLE001
    instaloader = None  # type: ignore[assignment]
    ilx = None  # type: ignore[assignment]


class _RateLimitHit(Exception):
    pass


def _make_rate_controller(ctx: Any) -> Any:
    class FailFastRateController(instaloader.RateController):  # type: ignore[misc,name-defined]
        def sleep(self, secs: float) -> None:
            if secs > MAX_POLITE_SLEEP:
                raise _RateLimitHit(f"espera solicitada de {secs:.0f}s")
            super().sleep(secs)

        def handle_429(self, query_type: str) -> None:
            raise _RateLimitHit("HTTP 429")

    return FailFastRateController(ctx)


class InstaloaderProvider:
    name = "Instaloader"

    def __init__(self) -> None:
        self._lock = threading.Lock()  # o contexto do Instaloader não é thread-safe
        self._loader: Any = None
        self._last_query = 0.0

    def _get_loader(self) -> Any:
        if instaloader is None:
            raise ProviderBrokenError(
                "O componente de acesso ao Instagram não pôde ser carregado. Reinstale o Pixora."
            )
        if self._loader is None:
            self._loader = instaloader.Instaloader(
                sleep=False,
                quiet=True,
                download_pictures=False,
                download_videos=False,  # o Pixora baixa por conta própria
                download_video_thumbnails=False,
                save_metadata=False,
                compress_json=False,
                max_connection_attempts=1,
                request_timeout=REQUEST_TIMEOUT,
                rate_controller=_make_rate_controller,
            )
        return self._loader

    def fetch_post(self, shortcode: str) -> PostInfo:
        with self._lock:
            try:
                loader = self._get_loader()
                wait = MIN_QUERY_INTERVAL - (time.monotonic() - self._last_query)
                if wait > 0:
                    time.sleep(wait)
                self._last_query = time.monotonic()
                post = instaloader.Post.from_shortcode(loader.context, shortcode)
                return parse_post_node(post._node, shortcode, owner=_safe_owner(post))
            except PixoraError:
                raise
            except Exception as exc:  # noqa: BLE001 — traduz qualquer falha em erro amigável
                raise translate_exception(exc) from exc


def _safe_owner(post: Any) -> str | None:
    try:
        node = post._node
        owner = node.get("owner") or node.get("user") or {}
        return owner.get("username") or None
    except Exception:  # noqa: BLE001
        return None


def _cause_chain(exc: BaseException) -> list[BaseException]:
    chain: list[BaseException] = []
    cur: BaseException | None = exc
    while cur is not None and cur not in chain and len(chain) < 10:
        chain.append(cur)
        cur = cur.__cause__ or cur.__context__
    return chain


def translate_exception(exc: BaseException) -> PixoraError:
    """Converte exceções do Instaloader/requests em erros do Pixora."""
    chain = _cause_chain(exc)
    text = " | ".join(str(e) for e in chain)
    log.warning("Falha ao consultar publicação: %s: %s", type(exc).__name__, text[:500])

    def has(kind: Any) -> bool:
        return kind is not None and any(isinstance(e, kind) for e in chain)

    if has(_RateLimitHit) or (ilx and has(ilx.TooManyRequestsException)) or "429" in text:
        return RateLimitedError(detail=text)
    if has(requests.Timeout):
        return NetworkError("O Instagram demorou demais para responder. Tente novamente.", detail=text)
    if has(requests.ConnectionError):
        return NetworkError(detail=text)
    if ilx is not None:
        if has(ilx.QueryReturnedNotFoundException):
            return PostUnavailableError(
                "Publicação não encontrada. Ela pode ter sido removida ou o link está incorreto.", detail=text
            )
        if has(ilx.LoginRequiredException) or has(ilx.PrivateProfileNotFollowedException) \
                or has(ilx.LoginException):
            return AccessRestrictedError(detail=text)
        if has(ilx.AbortDownloadException):
            return AccessRestrictedError(
                "O Instagram solicitou uma verificação de segurança para este acesso. "
                "O Pixora não contorna essas verificações; tente mais tarde.",
                detail=text,
            )
        if has(ilx.QueryReturnedForbiddenException) or "401" in text or "403" in text:
            return AccessRestrictedError(detail=text)
        if has(ilx.BadResponseException):
            # Resposta do Instaloader para posts inexistentes, removidos, privados ou restritos.
            return PostUnavailableError(detail=text)
        if has(ilx.ConnectionException):
            return NetworkError(
                "Não foi possível obter a publicação agora. Verifique sua conexão e tente novamente.",
                detail=text,
            )
    if isinstance(exc, (KeyError, TypeError, ValueError, AttributeError)):
        return ProviderBrokenError(detail=text)
    return PixoraError(detail=text)


# --- Conversão do formato bruto --------------------------------------------

def _candidates(node: dict[str, Any]) -> list[dict[str, Any]]:
    iv = node.get("image_versions2") or {}
    cands = iv.get("candidates") or []
    out = [c for c in cands if isinstance(c, dict) and c.get("url")]
    # Formato GraphQL antigo
    for r in node.get("display_resources") or []:
        if isinstance(r, dict) and r.get("src"):
            out.append({"url": r["src"], "width": r.get("config_width"), "height": r.get("config_height")})
    return out


def _dims(node: dict[str, Any]) -> tuple[int | None, int | None]:
    w = node.get("original_width")
    h = node.get("original_height")
    if not (w and h):
        d = node.get("dimensions") or {}
        w, h = d.get("width"), d.get("height")
    return (int(w) if w else None, int(h) if h else None)


def _pick_urls(node: dict[str, Any], thumb_width: int = THUMB_WIDTH_GRID
               ) -> tuple[str, str, int | None, int | None]:
    """Retorna (url_maior_resolução, url_miniatura, largura, altura)."""
    width, height = _dims(node)
    cands = _candidates(node)
    fallback = node.get("display_url") or node.get("display_uri") or node.get("display_src")

    if not cands:
        if not fallback:
            raise ProviderBrokenError(detail="nenhuma URL de imagem no nó")
        return fallback, fallback, width, height

    def ratio(c: dict[str, Any]) -> float | None:
        if c.get("width") and c.get("height"):
            return c["width"] / c["height"]
        return None

    target_ratio = (width / height) if (width and height) else ratio(max(
        cands, key=lambda c: (c.get("width") or 0) * (c.get("height") or 0)))
    # Exclui recortes quadrados quando a imagem original não é quadrada.
    same_shape = [c for c in cands
                  if target_ratio is None or ratio(c) is None or abs(ratio(c) - target_ratio) < 0.02]
    pool = same_shape or cands

    best = max(pool, key=lambda c: (c.get("width") or 0) * (c.get("height") or 0))
    sized = [c for c in pool if c.get("width")]
    thumb = best
    if sized:
        bigger = [c for c in sized if c["width"] >= thumb_width]
        thumb = min(bigger, key=lambda c: c["width"]) if bigger else max(sized, key=lambda c: c["width"])

    full_url = best["url"]
    # display_url costuma ser a maior versão disponível sem recorte.
    if fallback and not best.get("width"):
        full_url = fallback
    if not (width and height):
        width, height = best.get("width"), best.get("height")
    return full_url, thumb["url"], width, height


def _is_video(node: dict[str, Any]) -> bool:
    if node.get("media_type") == 2:
        return True
    if node.get("is_video") is True:
        return True
    return node.get("__typename") in ("GraphVideo", "XDTGraphVideo")


def _video_url(node: dict[str, Any]) -> str | None:
    """URL do MP4 de maior resolução disponível, ou ``None``."""
    versions = [v for v in node.get("video_versions") or [] if isinstance(v, dict) and v.get("url")]
    if versions:
        return max(versions, key=lambda v: (v.get("width") or 0) * (v.get("height") or 0))["url"]
    url = node.get("video_url")
    return url if isinstance(url, str) and url else None


def _parse_item(node: dict[str, Any], pos: int, thumb_width: int) -> ImageItem | None:
    """Converte um nó em item; ``None`` para vídeos sem URL acessível."""
    full, thumb, w, h = _pick_urls(node, thumb_width)
    if _is_video(node):
        video = _video_url(node)
        if not video:
            return None
        return ImageItem(position=pos, full_url=video, thumbnail_url=thumb, width=w, height=h, is_video=True)
    return ImageItem(position=pos, full_url=full, thumbnail_url=thumb, width=w, height=h)


def parse_post_node(node: dict[str, Any], shortcode: str, owner: str | None = None) -> PostInfo:
    if not isinstance(node, dict):
        raise ProviderBrokenError(detail="nó da publicação não é um dicionário")

    children: list[dict[str, Any]] = []
    if node.get("carousel_media"):
        children = [c for c in node["carousel_media"] if isinstance(c, dict)]
    elif (node.get("edge_sidecar_to_children") or {}).get("edges"):
        children = [e.get("node") or {} for e in node["edge_sidecar_to_children"]["edges"]]

    url = f"https://www.instagram.com/p/{shortcode}/"
    if children:
        items: list[ImageItem] = []
        skipped = 0
        for pos, child in enumerate(children, start=1):
            item = _parse_item(child, pos, THUMB_WIDTH_GRID)
            if item is None:
                skipped += 1
                continue
            items.append(item)
        if not items:
            raise UnsupportedContentError(
                "Não foi possível obter as mídias deste carrossel. Tente novamente mais tarde."
            )
        return PostInfo(shortcode, url, PostKind.CAROUSEL, tuple(items), owner, skipped)

    item = _parse_item(node, 1, THUMB_WIDTH_SINGLE)
    if item is None:
        raise UnsupportedContentError(
            "Não foi possível obter o arquivo deste vídeo. Ele pode estar indisponível sem login."
        )
    return PostInfo(shortcode, url, PostKind.SINGLE, (item,), owner)
