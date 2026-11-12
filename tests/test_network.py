"""Testes de integração REAIS com o Instagram (desativados por padrão).

Execute com:  PIXORA_NETWORK_TESTS=1 pytest -m network
Usam apenas publicações públicas de contas institucionais, sem login.
Os códigos podem deixar de existir com o tempo; nesse caso, substitua-os.
"""

import os

import pytest

from pixora.core.errors import PostUnavailableError, UnsupportedContentError
from pixora.core.http import MediaHttpClient
from pixora.core.models import PostKind
from pixora.core.service import PixoraService
from pixora.core.filenames import ConflictPolicy
from pixora.providers.instaloader_provider import InstaloaderProvider

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(not os.environ.get("PIXORA_NETWORK_TESTS"), reason="defina PIXORA_NETWORK_TESTS=1"),
]

SINGLE = os.environ.get("PIXORA_TEST_SINGLE", "DeJ28eTxo4s")      # @nasawebb, imagem única
CAROUSEL = os.environ.get("PIXORA_TEST_CAROUSEL", "DeAYvsnn4la")  # @nasa, carrossel de 3 imagens
VIDEO = os.environ.get("PIXORA_TEST_VIDEO", "DeTUk4sDSp-")        # @nasa, vídeo


@pytest.fixture(scope="module")
def service():
    return PixoraService(InstaloaderProvider(), MediaHttpClient())


def test_real_single(service, tmp_path):
    post = service.fetch(service.validate(f"https://www.instagram.com/p/{SINGLE}/"))
    assert post.kind is PostKind.SINGLE and post.image_count == 1
    report = service.download(post, post.images, tmp_path, ConflictPolicy.RENAME)
    assert len(report.saved) == 1 and report.saved[0].path.stat().st_size > 10_000


def test_real_carousel(service):
    post = service.fetch(service.validate(f"https://www.instagram.com/p/{CAROUSEL}/"))
    assert post.kind is PostKind.CAROUSEL and post.image_count >= 2
    assert [i.position for i in post.images] == sorted(i.position for i in post.images)


def test_real_video_is_downloaded_as_mp4(service, tmp_path):
    post = service.fetch(service.validate(f"https://www.instagram.com/reel/{VIDEO}/"))
    assert post.video_count == 1
    report = service.download(post, post.images, tmp_path, ConflictPolicy.RENAME)
    assert report.saved and report.saved[0].path.suffix == ".mp4"


def test_real_missing_post(service):
    with pytest.raises(PostUnavailableError):
        service.fetch(service.validate("https://www.instagram.com/p/AAAAAAAAAAA/"))
