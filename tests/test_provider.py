"""Conversão dos dados do Instagram e tradução de erros (sem rede)."""

import pytest
import requests
from instaloader import exceptions as ilx

from pixora.core.errors import (
    AccessRestrictedError, NetworkError, PixoraError, PostUnavailableError, ProviderBrokenError,
    RateLimitedError, UnsupportedContentError,
)
from pixora.core.models import PostKind
from pixora.providers.instaloader_provider import _RateLimitHit, parse_post_node, translate_exception

CDN = "https://scontent.cdninstagram.com/v/"


def cands(tag, w, h):
    """Candidatos como o Instagram envia: proporção original + recortes quadrados."""
    sizes = [(w, h), (int(w * 0.66), int(h * 0.66)), (480, int(480 * h / w)), (320, int(320 * h / w)),
             (1080, 1080), (480, 480), (150, 150)]
    return {"image_versions2": {"candidates": [
        {"url": f"{CDN}{tag}_{a}x{b}.jpg?sig=x", "width": a, "height": b} for a, b in sizes]}}


def image_node(tag, w=1080, h=1350, **extra):
    return {"media_type": 1, "original_width": w, "original_height": h, **cands(tag, w, h), **extra}


def video_node(tag):
    return {"media_type": 2, "original_width": 1080, "original_height": 1920, **cands(tag, 1080, 1920),
            "video_url": f"{CDN}{tag}.mp4"}


def test_single_image_picks_largest_uncropped_and_separate_thumbnail():
    node = image_node("a", 2000, 1872, owner={"username": "nasawebb"})
    post = parse_post_node(node, "SHORT1")
    assert post.kind is PostKind.SINGLE and post.image_count == 1
    img = post.images[0]
    assert img.full_url.startswith(f"{CDN}a_2000x1872")
    assert img.thumbnail_url != img.full_url           # miniatura separada do arquivo final
    assert "1080x1080" not in img.thumbnail_url         # nunca o recorte quadrado
    assert (img.width, img.height) == (2000, 1872)
    assert post.url == "https://www.instagram.com/p/SHORT1/"


def test_carousel_preserves_order_and_uses_small_thumbnails():
    node = {"media_type": 8, "carousel_media": [image_node("c1"), image_node("c2"), image_node("c3")]}
    post = parse_post_node(node, "CAR")
    assert post.kind is PostKind.CAROUSEL
    assert [i.position for i in post.images] == [1, 2, 3]
    assert [i.full_url.split("_")[0][-2:] for i in post.images] == ["c1", "c2", "c3"]
    assert all("_480x600" in i.thumbnail_url for i in post.images)
    assert all("_1080x1350" in i.full_url for i in post.images)


def test_carousel_skips_videos_but_keeps_original_positions():
    node = {"carousel_media": [image_node("a"), video_node("v"), image_node("b")]}
    post = parse_post_node(node, "MIX")
    assert [i.position for i in post.images] == [1, 3]
    assert post.skipped_videos == 1


def test_carousel_with_only_videos_is_unsupported():
    with pytest.raises(UnsupportedContentError):
        parse_post_node({"carousel_media": [video_node("a"), video_node("b")]}, "VID")


def test_video_post_is_unsupported():
    with pytest.raises(UnsupportedContentError) as exc:
        parse_post_node(video_node("x"), "VID")
    assert "vídeo" in exc.value.user_message


def test_legacy_graphql_sidecar_format():
    node = {
        "__typename": "GraphSidecar",
        "edge_sidecar_to_children": {"edges": [
            {"node": {"__typename": "GraphImage", "display_url": f"{CDN}l1.jpg",
                      "dimensions": {"width": 1080, "height": 1080}}},
            {"node": {"__typename": "GraphVideo", "is_video": True, "display_url": f"{CDN}v.jpg"}},
            {"node": {"__typename": "GraphImage", "display_url": f"{CDN}l3.jpg",
                      "display_resources": [
                          {"src": f"{CDN}l3_640.jpg", "config_width": 640, "config_height": 640},
                          {"src": f"{CDN}l3_1080.jpg", "config_width": 1080, "config_height": 1080}]}},
        ]},
    }
    post = parse_post_node(node, "OLD")
    assert [i.position for i in post.images] == [1, 3]
    assert post.images[0].full_url == f"{CDN}l1.jpg"
    assert post.images[1].full_url == f"{CDN}l3_1080.jpg"
    assert post.images[1].thumbnail_url == f"{CDN}l3_640.jpg"
    assert post.skipped_videos == 1


def test_missing_image_urls_means_provider_broken():
    with pytest.raises(ProviderBrokenError):
        parse_post_node({"media_type": 1}, "BROKEN")
    with pytest.raises(ProviderBrokenError):
        parse_post_node(None, "BROKEN")  # type: ignore[arg-type]


@pytest.mark.parametrize("exc, expected", [
    (ilx.QueryReturnedNotFoundException("404"), PostUnavailableError),
    (ilx.BadResponseException("Fetching Post metadata failed."), PostUnavailableError),
    (ilx.LoginRequiredException("login required"), AccessRestrictedError),
    (ilx.PrivateProfileNotFollowedException("private"), AccessRestrictedError),
    (ilx.QueryReturnedForbiddenException("403"), AccessRestrictedError),
    (ilx.AbortDownloadException("checkpoint_required"), AccessRestrictedError),
    (ilx.TooManyRequestsException("429"), RateLimitedError),
    (_RateLimitHit("espera"), RateLimitedError),
    (ilx.ConnectionException("JSON Query: 429 Too Many Requests"), RateLimitedError),
    (ilx.ConnectionException("unknown"), NetworkError),
    (requests.ConnectionError("dns"), NetworkError),
    (requests.Timeout("slow"), NetworkError),
    (KeyError("data"), ProviderBrokenError),
    (RuntimeError("???"), PixoraError),
])
def test_translate_exception(exc, expected):
    result = translate_exception(exc)
    assert type(result) is expected
    assert result.user_message


def test_translate_follows_cause_chain():
    try:
        try:
            raise requests.ConnectionError("offline")
        except requests.ConnectionError as inner:
            raise ilx.ConnectionException("wrapped") from inner
    except ilx.ConnectionException as outer:
        assert isinstance(translate_exception(outer), NetworkError)
