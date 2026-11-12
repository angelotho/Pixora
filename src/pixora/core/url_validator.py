"""Validação e normalização de links de publicações do Instagram.

Regras de segurança:
* apenas hosts oficiais do Instagram (sem IPs, portas, credenciais embutidas);
* apenas esquemas http/https (normalizados para https);
* apenas caminhos de publicação (``/p/``, ``/reel/``, ``/tv/``), com ou sem nome de usuário;
* o link nunca é requisitado diretamente — apenas o código (shortcode) extraído
  é repassado à camada de integração, eliminando redirecionamentos inseguros.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from .errors import InvalidUrlError, UnsupportedContentError
from .models import ParsedPostUrl

ALLOWED_HOSTS = frozenset({
    "instagram.com",
    "www.instagram.com",
    "m.instagram.com",
    "instagr.am",
    "www.instagr.am",
})

# Shortcodes usam o alfabeto base64 de URL. Posts atuais têm 11 caracteres,
# posts antigos podem ter menos; códigos muito longos indicam posts privados
# (que exigem login) ou lixo.
SHORTCODE_RE = re.compile(r"^[A-Za-z0-9_-]{5,40}$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")

_POST_PREFIXES = {"p"}
_VIDEO_PREFIXES = {"reel", "reels", "tv"}
_OTHER_UNSUPPORTED = {
    "stories": "Stories não são suportados. O Pixora baixa apenas mídias de publicações.",
    "live": "Transmissões ao vivo não são suportadas.",
    "explore": "Páginas de explorar não são suportadas. Use o link de uma publicação.",
}

MAX_URL_LENGTH = 2048


def parse_post_url(raw: str) -> ParsedPostUrl:
    """Valida ``raw`` e devolve o shortcode e a URL canônica.

    Levanta :class:`InvalidUrlError` ou :class:`UnsupportedContentError` com
    mensagens prontas para o usuário.
    """
    text = (raw or "").strip()
    if not text:
        raise InvalidUrlError("Cole o link de uma publicação do Instagram para começar.")
    if len(text) > MAX_URL_LENGTH or any(ch.isspace() for ch in text):
        raise InvalidUrlError("O texto colado não parece ser um único link válido.")

    if "://" not in text:
        if text.startswith("//"):
            text = "https:" + text
        else:
            text = "https://" + text

    try:
        parts = urlsplit(text)
        port = parts.port  # levanta ValueError para portas inválidas
    except ValueError as exc:
        raise InvalidUrlError("O endereço informado está malformado.", detail=str(exc)) from exc

    if parts.scheme.lower() not in {"http", "https"}:
        raise InvalidUrlError("Apenas links http ou https do Instagram são aceitos.")
    if parts.username is not None or parts.password is not None:
        raise InvalidUrlError("O link contém credenciais embutidas e foi bloqueado por segurança.")
    if port is not None and port not in (80, 443):
        raise InvalidUrlError("O link aponta para uma porta não permitida.")

    host = (parts.hostname or "").lower().rstrip(".")
    if host not in ALLOWED_HOSTS:
        raise InvalidUrlError("O link não pertence ao Instagram. Use um endereço como instagram.com/p/…")

    segments = [s for s in parts.path.split("/") if s]
    if not segments:
        raise InvalidUrlError("Este é o link da página inicial. Cole o link de uma publicação específica.")

    # Formatos aceitos: /p/<code>, /<usuario>/p/<code>
    prefix_index = 0
    first = segments[0].lower()
    if (
        first not in _POST_PREFIXES | _VIDEO_PREFIXES
        and first not in _OTHER_UNSUPPORTED
        and len(segments) >= 3
        and segments[1].lower() in _POST_PREFIXES | _VIDEO_PREFIXES
        and USERNAME_RE.match(segments[0])
    ):
        prefix_index = 1

    prefix = segments[prefix_index].lower()
    if prefix in _OTHER_UNSUPPORTED:
        raise UnsupportedContentError(_OTHER_UNSUPPORTED[prefix])
    if prefix not in _POST_PREFIXES | _VIDEO_PREFIXES:
        if len(segments) == 1 and USERNAME_RE.match(segments[0]):
            raise UnsupportedContentError(
                "Este é o link de um perfil. O Pixora baixa mídias de uma publicação por vez — "
                "abra a publicação e copie o link dela."
            )
        raise InvalidUrlError("O link não corresponde a uma publicação do Instagram.")

    if len(segments) <= prefix_index + 1:
        raise InvalidUrlError("O link está incompleto: falta o código da publicação.")

    shortcode = segments[prefix_index + 1]
    if not SHORTCODE_RE.match(shortcode):
        raise InvalidUrlError("O código da publicação no link não é válido.")

    return ParsedPostUrl(
        shortcode=shortcode,
        canonical_url=f"https://www.instagram.com/p/{shortcode}/",
    )


def is_probable_instagram_url(raw: str) -> bool:
    """Checagem leve (sem exceções) usada para colar automaticamente da área de transferência."""
    try:
        parse_post_url(raw)
        return True
    except (InvalidUrlError, UnsupportedContentError):
        return False
