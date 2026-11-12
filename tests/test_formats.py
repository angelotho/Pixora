"""Escolha do formato de saída: PNG/JPG para imagens, MP4 fixo para vídeos."""

import pytest

from pixora.core.downloader import DownloadManager
from pixora.core.http import MediaHttpClient
from pixora.core.models import ImageFormat, ImageItem, PostInfo, PostKind
from pixora.storage.settings import Settings

from conftest import CDN, FakeResponse, FakeSession, jpeg_response, make_post, png_bytes

MP4_BYTES = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 4000


def manager(routes):
    return DownloadManager(MediaHttpClient(FakeSession(routes)))


def qt_image_bytes(fmt: str, w: int = 8, h: int = 6, alpha: bool = False) -> bytes:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QColor, QImage
    img = QImage(w, h, QImage.Format.Format_ARGB32 if alpha else QImage.Format.Format_RGB32)
    img.fill(QColor(200, 30, 90, 0 if alpha else 255))
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, fmt, 95)
    return bytes(data)


def test_png_choice_converts_jpeg_without_further_loss(tmp_path):
    from PySide6.QtGui import QImage
    post = make_post(1)
    src = qt_image_bytes("JPG")
    report = manager({post.images[0].full_url: FakeResponse(200, src, {"Content-Type": "image/jpeg"})}) \
        .download(post, post.images, tmp_path, image_format=ImageFormat.PNG)
    out = tmp_path / "instagram_TESTabc123_01.png"
    assert [r.path for r in report.saved] == [out]
    assert out.read_bytes().startswith(b"\x89PNG")
    original, converted = QImage.fromData(src), QImage(str(out))
    assert converted.size() == original.size()
    assert converted.pixelColor(3, 3) == original.pixelColor(3, 3)   # PNG é sem perdas
    assert [p.name for p in tmp_path.iterdir()] == [out.name]        # sem temporários


def test_jpg_choice_flattens_transparency_on_white(tmp_path):
    from PySide6.QtGui import QImage
    post = make_post(1)
    src = qt_image_bytes("PNG", alpha=True)
    manager({post.images[0].full_url: FakeResponse(200, src, {"Content-Type": "image/png"})}) \
        .download(post, post.images, tmp_path, image_format=ImageFormat.JPG)
    out = QImage(str(tmp_path / "instagram_TESTabc123_01.jpg"))
    c = out.pixelColor(2, 2)
    assert min(c.red(), c.green(), c.blue()) > 240


def test_matching_format_keeps_original_bytes(tmp_path):
    post = make_post(1)
    body = png_bytes()
    manager({post.images[0].full_url: FakeResponse(200, body, {"Content-Type": "image/png"})}) \
        .download(post, post.images, tmp_path, image_format=ImageFormat.PNG)
    assert (tmp_path / "instagram_TESTabc123_01.png").read_bytes() == body


def test_undecodable_image_fails_conversion_cleanly(tmp_path):
    post = make_post(1)
    report = manager({post.images[0].full_url: jpeg_response()}) \
        .download(post, post.images, tmp_path, image_format=ImageFormat.PNG)
    assert report.failed and "PNG" in report.failed[0].error
    assert list(tmp_path.iterdir()) == []


def _video_post() -> PostInfo:
    item = ImageItem(position=1, full_url=f"{CDN}clip.mp4", thumbnail_url=f"{CDN}cover.jpg", is_video=True)
    return PostInfo("VIDabc123", "https://www.instagram.com/p/VIDabc123/", PostKind.SINGLE, (item,))


@pytest.mark.parametrize("fmt", list(ImageFormat))
def test_video_is_always_saved_as_mp4_untouched(tmp_path, fmt):
    post = _video_post()
    report = manager({post.images[0].full_url: FakeResponse(200, MP4_BYTES, {"Content-Type": "video/mp4"})}) \
        .download(post, post.images, tmp_path, image_format=fmt)
    out = tmp_path / "instagram_VIDabc123_01.mp4"
    assert [r.path for r in report.saved] == [out]
    assert out.read_bytes() == MP4_BYTES


def test_video_url_returning_non_video_is_rejected(tmp_path):
    post = _video_post()
    report = manager({post.images[0].full_url: jpeg_response()}).download(post, post.images, tmp_path)
    assert report.failed and "MP4" in report.failed[0].error


def test_settings_format_is_validated():
    assert Settings(image_format="png").format is ImageFormat.PNG
    assert Settings(image_format="bmp").format is ImageFormat.JPG
