"""Fixtures e dublês de teste.

Nenhum teste padrão acessa a rede ou usa credenciais: as respostas HTTP e o
provider do Instagram são simulados aqui (dados claramente fictícios).
"""

from __future__ import annotations

import os
import struct
import zlib
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
import requests

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pixora.core.errors import PostUnavailableError  # noqa: E402
from pixora.core.models import ImageItem, PostInfo, PostKind  # noqa: E402

CDN = "https://scontent-fake.cdninstagram.com/v/t51/"

JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 2000 + b"\xff\xd9"


def png_bytes(w: int = 4, h: int = 5) -> bytes:
    """PNG válido mínimo (para testes que decodificam a imagem)."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x80\x40\xc0" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


@dataclass
class FakeResponse:
    status_code: int = 200
    body: bytes = b""
    headers: dict = field(default_factory=dict)
    fail_after: int | None = None   # simula queda de conexão após N bytes
    closed: bool = False

    @property
    def is_redirect(self) -> bool:
        return self.status_code in (301, 302, 303, 307, 308) and "Location" in self.headers

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        sent = 0
        for i in range(0, len(self.body), chunk_size):
            if self.fail_after is not None and sent >= self.fail_after:
                raise requests.ConnectionError("conexão interrompida (simulada)")
            part = self.body[i:i + chunk_size]
            sent += len(part)
            yield part

    def close(self) -> None:
        self.closed = True


class FakeSession:
    """Substitui ``requests.Session``; mapeia URL -> FakeResponse ou exceção."""

    def __init__(self, routes: dict | None = None) -> None:
        self.headers: dict = {}
        self.routes: dict = routes or {}
        self.calls: list[str] = []

    def get(self, url: str, **kwargs) -> FakeResponse:
        self.calls.append(url)
        assert kwargs.get("allow_redirects") is False, "redirecionamentos devem ser manuais"
        assert kwargs.get("timeout"), "toda requisição precisa de timeout"
        route = self.routes.get(url)
        if route is None:
            return FakeResponse(404)
        if isinstance(route, Exception):
            raise route
        if callable(route):
            return route()
        return FakeResponse(route.status_code, route.body, dict(route.headers), route.fail_after)


def jpeg_response(body: bytes = JPEG_BYTES, **kw) -> FakeResponse:
    return FakeResponse(200, body, {"Content-Type": "image/jpeg", "Content-Length": str(len(body))}, **kw)


def make_post(n: int = 3, kind: PostKind | None = None, shortcode: str = "TESTabc123") -> PostInfo:
    images = tuple(
        ImageItem(position=i, full_url=f"{CDN}full_{i}.jpg?sig=secret", thumbnail_url=f"{CDN}thumb_{i}.png",
                  width=1080, height=1350)
        for i in range(1, n + 1)
    )
    k = kind or (PostKind.SINGLE if n == 1 else PostKind.CAROUSEL)
    return PostInfo(shortcode, f"https://www.instagram.com/p/{shortcode}/", k, images, owner="conta_teste")


class FakeProvider:
    """Provider simulado — não acessa o Instagram."""

    name = "Fake"

    def __init__(self, posts: dict[str, PostInfo | Exception] | None = None) -> None:
        self.posts = posts or {}
        self.calls: list[str] = []

    def fetch_post(self, shortcode: str) -> PostInfo:
        self.calls.append(shortcode)
        value = self.posts.get(shortcode)
        if value is None:
            raise PostUnavailableError()
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture
def fake_session() -> FakeSession:
    return FakeSession()


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Garante que nenhum teste escreva no perfil real do usuário."""
    monkeypatch.setenv("PIXORA_HOME", str(tmp_path / "home"))
    return tmp_path / "home"
