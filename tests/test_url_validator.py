import pytest

from pixora.core.errors import InvalidUrlError, UnsupportedContentError
from pixora.core.url_validator import is_probable_instagram_url, parse_post_url


@pytest.mark.parametrize("raw", [
    "https://www.instagram.com/p/DeAYvsnn4la/",
    "https://www.instagram.com/p/DeAYvsnn4la",
    "http://www.instagram.com/p/DeAYvsnn4la/",
    "https://instagram.com/p/DeAYvsnn4la/",
    "https://m.instagram.com/p/DeAYvsnn4la/",
    "https://WWW.INSTAGRAM.COM/p/DeAYvsnn4la/",
    "www.instagram.com/p/DeAYvsnn4la/",
    "instagram.com/p/DeAYvsnn4la",
    "  https://www.instagram.com/p/DeAYvsnn4la/  ",
    "https://www.instagram.com/p/DeAYvsnn4la/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA==",
    "https://www.instagram.com/p/DeAYvsnn4la/?img_index=2",
    "https://www.instagram.com/p/DeAYvsnn4la/#comments",
    "https://www.instagram.com/nasa/p/DeAYvsnn4la/",
    "https://www.instagram.com/p/DeAYvsnn4la/embed/",
    "https://www.instagram.com.:443/p/DeAYvsnn4la/",
    "https://instagr.am/p/DeAYvsnn4la/",
])
def test_valid_variants_normalize_to_canonical(raw):
    parsed = parse_post_url(raw)
    assert parsed.shortcode == "DeAYvsnn4la"
    assert parsed.canonical_url == "https://www.instagram.com/p/DeAYvsnn4la/"


def test_shortcode_with_dash_and_underscore():
    assert parse_post_url("https://www.instagram.com/p/Ab-_9xY/").shortcode == "Ab-_9xY"


@pytest.mark.parametrize("raw", [
    "",
    "   ",
    "não é um link",
    "https://example.com/p/DeAYvsnn4la/",
    "https://instagram.com.evil.com/p/DeAYvsnn4la/",
    "https://evilinstagram.com/p/DeAYvsnn4la/",
    "https://www.instagram.com@evil.com/p/DeAYvsnn4la/",
    "https://user:pass@www.instagram.com/p/DeAYvsnn4la/",
    "https://www.instagram.com:8080/p/DeAYvsnn4la/",
    "https://127.0.0.1/p/DeAYvsnn4la/",
    "http://localhost/p/DeAYvsnn4la/",
    "file:///C:/Windows/p/DeAYvsnn4la/",
    "ftp://www.instagram.com/p/DeAYvsnn4la/",
    "javascript:alert(1)",
    "https://www.instagram.com/",
    "https://www.instagram.com/p/",
    "https://www.instagram.com/p/abc/",            # curto demais
    "https://www.instagram.com/p/abc$%def/",       # caracteres inválidos
    "https://www.instagram.com/accounts/login/",
    "https://www.instagram.com/p/DeAY vsnn4la/",
    "https://www.instagram.com/p/" + "a" * 2100,
])
def test_invalid_urls_are_rejected(raw):
    with pytest.raises((InvalidUrlError, UnsupportedContentError)) as exc:
        parse_post_url(raw)
    assert exc.value.user_message  # sempre há mensagem amigável


@pytest.mark.parametrize("raw, fragment", [
    ("https://www.instagram.com/reel/DeTUk4sDSp-/", "Reel"),
    ("https://www.instagram.com/reels/DeTUk4sDSp-/", "Reel"),
    ("https://www.instagram.com/tv/DeTUk4sDSp-/", "vídeo"),
    ("https://www.instagram.com/nasa/reel/DeTUk4sDSp-/", "Reel"),
    ("https://www.instagram.com/stories/nasa/123456789/", "Stories"),
    ("https://www.instagram.com/nasa/", "perfil"),
    ("https://www.instagram.com/explore/tags/space/", "explorar"),
])
def test_unsupported_content_has_specific_message(raw, fragment):
    with pytest.raises(UnsupportedContentError) as exc:
        parse_post_url(raw)
    assert fragment.lower() in exc.value.user_message.lower()


def test_is_probable_instagram_url_never_raises():
    assert is_probable_instagram_url("https://www.instagram.com/p/DeAYvsnn4la/")
    assert not is_probable_instagram_url("https://example.com")
    assert not is_probable_instagram_url("")
    assert not is_probable_instagram_url("https://www.instagram.com/reel/DeTUk4sDSp-/")
