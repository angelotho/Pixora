"""Downloads com HTTP simulado: sucesso, falhas parciais, interrupções e segurança."""

import threading

import pytest
import requests

from pixora.core.downloader import DownloadManager, ensure_writable_folder
from pixora.core.errors import DestinationError
from pixora.core.filenames import ConflictPolicy
from pixora.core.http import MediaHttpClient, is_allowed_media_url, redact_url

from conftest import CDN, JPEG_BYTES, FakeResponse, FakeSession, jpeg_response, make_post, png_bytes


def manager(routes, policy=ConflictPolicy.RENAME):
    session = FakeSession(routes)
    return DownloadManager(MediaHttpClient(session), policy), session


def test_downloads_selected_items_with_consistent_names(tmp_path):
    post = make_post(3)
    routes = {i.full_url: jpeg_response() for i in post.images}
    routes[post.images[1].full_url] = FakeResponse(200, png_bytes(), {"Content-Type": "image/png"})
    dm, _ = manager(routes)
    report = dm.download(post, post.images, tmp_path)
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["instagram_TESTabc123_01.jpg", "instagram_TESTabc123_02.png", "instagram_TESTabc123_03.jpg"]
    assert len(report.saved) == 3 and not report.failed and not report.cancelled
    assert (tmp_path / "instagram_TESTabc123_01.jpg").read_bytes() == JPEG_BYTES


def test_position_in_name_follows_original_post_order(tmp_path):
    post = make_post(5)
    chosen = [post.images[1], post.images[4]]
    dm, _ = manager({i.full_url: jpeg_response() for i in chosen})
    dm.download(post, chosen, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "instagram_TESTabc123_02.jpg", "instagram_TESTabc123_05.jpg"]


def test_single_image_post(tmp_path):
    post = make_post(1)
    dm, _ = manager({post.images[0].full_url: jpeg_response()})
    report = dm.download(post, post.images, tmp_path)
    assert [r.path.name for r in report.saved] == ["instagram_TESTabc123_01.jpg"]


def test_partial_failure_keeps_other_files(tmp_path):
    post = make_post(3)
    routes = {
        post.images[0].full_url: jpeg_response(),
        post.images[1].full_url: FakeResponse(403),
        post.images[2].full_url: requests.ConnectionError("offline"),
    }
    dm, _ = manager(routes)
    report = dm.download(post, post.images, tmp_path)
    assert len(report.saved) == 1 and len(report.failed) == 2
    assert "expirou" in report.failed[0].error
    assert "conectar" in report.failed[1].error.lower()
    assert [p.name for p in tmp_path.iterdir()] == ["instagram_TESTabc123_01.jpg"]


def test_connection_drop_mid_download_leaves_no_partial_file(tmp_path):
    post = make_post(1)
    body = JPEG_BYTES * 100
    dm, _ = manager({post.images[0].full_url: jpeg_response(body, fail_after=65536)})
    report = dm.download(post, post.images, tmp_path)
    assert len(report.failed) == 1 and "interrompida" in report.failed[0].error
    assert list(tmp_path.iterdir()) == []  # nem arquivo final nem temporário


def test_truncated_response_is_rejected(tmp_path):
    post = make_post(1)
    resp = FakeResponse(200, JPEG_BYTES, {"Content-Type": "image/jpeg", "Content-Length": str(len(JPEG_BYTES) + 500)})
    dm, _ = manager({post.images[0].full_url: resp})
    report = dm.download(post, post.images, tmp_path)
    assert report.failed and "incompleto" in report.failed[0].error
    assert list(tmp_path.iterdir()) == []


def test_non_image_content_is_rejected(tmp_path):
    post = make_post(1)
    resp = FakeResponse(200, b"<html>login</html>", {"Content-Type": "text/html"})
    dm, _ = manager({post.images[0].full_url: resp})
    report = dm.download(post, post.images, tmp_path)
    assert report.failed and "não é uma imagem" in report.failed[0].error


def test_empty_response_is_rejected(tmp_path):
    post = make_post(1)
    dm, _ = manager({post.images[0].full_url: FakeResponse(200, b"", {"Content-Type": "image/jpeg"})})
    assert dm.download(post, post.images, tmp_path).failed


def test_existing_files_are_never_overwritten(tmp_path):
    post = make_post(1)
    existing = tmp_path / "instagram_TESTabc123_01.jpg"
    existing.write_bytes(b"original")
    dm, _ = manager({post.images[0].full_url: jpeg_response()})
    report = dm.download(post, post.images, tmp_path)
    assert existing.read_bytes() == b"original"
    assert report.saved[0].path.name == "instagram_TESTabc123_01 (2).jpg"


def test_skip_policy_keeps_existing_and_reports_skip(tmp_path):
    post = make_post(1)
    existing = tmp_path / "instagram_TESTabc123_01.jpg"
    existing.write_bytes(b"original")
    dm, _ = manager({post.images[0].full_url: jpeg_response()}, ConflictPolicy.SKIP)
    report = dm.download(post, post.images, tmp_path)
    assert existing.read_bytes() == b"original"
    assert len(report.skipped) == 1 and not report.saved and not report.failed
    assert [p.name for p in tmp_path.iterdir()] == [existing.name]


def test_cancel_stops_batch_and_cleans_temp(tmp_path):
    post = make_post(3)
    cancel = threading.Event()
    big = JPEG_BYTES * 100  # vários blocos de 64 KiB: o cancelamento ocorre no meio do arquivo 2
    routes = {i.full_url: jpeg_response(big) for i in post.images}
    dm, _ = manager(routes)

    def on_progress(p):
        if p.file_index == 1 and p.bytes_done > 0:
            cancel.set()

    report = dm.download(post, post.images, tmp_path, on_progress=on_progress, cancel=cancel)
    assert report.cancelled
    assert [p.name for p in tmp_path.iterdir()] == ["instagram_TESTabc123_01.jpg"]


def test_progress_reports_fraction(tmp_path):
    post = make_post(2)
    dm, _ = manager({i.full_url: jpeg_response() for i in post.images})
    seen = []
    dm.download(post, post.images, tmp_path, on_progress=lambda p: seen.append(p.fraction))
    assert seen[-1] == 1.0
    assert all(0.0 <= f <= 1.0 for f in seen)
    assert seen == sorted(seen)


def test_destination_that_is_a_file_raises_friendly_error(tmp_path):
    blocker = tmp_path / "arquivo.txt"
    blocker.write_text("x")
    with pytest.raises(DestinationError) as exc:
        ensure_writable_folder(blocker / "sub")
    assert "pasta" in exc.value.user_message.lower()


def test_destination_is_created_when_missing(tmp_path):
    target = tmp_path / "a" / "b"
    ensure_writable_folder(target)
    assert target.is_dir()


# --- segurança do cliente HTTP ----------------------------------------------

@pytest.mark.parametrize("url, ok", [
    (f"{CDN}x.jpg", True),
    ("https://instagram.fgru1-1.fna.fbcdn.net/v/x.jpg?sig=1", True),
    ("http://scontent.cdninstagram.com/x.jpg", False),           # sem TLS
    ("https://evil.com/x.jpg", False),
    ("https://cdninstagram.com.evil.com/x.jpg", False),
    ("https://fakecdninstagram.com/x.jpg", False),
    ("https://user@scontent.cdninstagram.com/x.jpg", False),
    ("https://scontent.cdninstagram.com:8443/x.jpg", False),
    ("https://127.0.0.1/x.jpg", False),
])
def test_media_host_allowlist(url, ok):
    assert is_allowed_media_url(url) is ok


def test_blocked_host_is_never_requested(tmp_path):
    post = make_post(1)
    from dataclasses import replace
    bad = replace(post.images[0], full_url="https://evil.example.com/x.jpg")
    dm, session = manager({})
    report = dm.download(post, [bad], tmp_path)
    assert report.failed and "bloqueado" in report.failed[0].error
    assert session.calls == []


def test_redirect_to_foreign_host_is_blocked(tmp_path):
    post = make_post(1)
    url = post.images[0].full_url
    dm, session = manager({url: FakeResponse(302, headers={"Location": "https://evil.example.com/a.jpg"})})
    report = dm.download(post, post.images, tmp_path)
    assert report.failed and session.calls == [url]


def test_redirect_within_cdn_is_followed(tmp_path):
    post = make_post(1)
    url = post.images[0].full_url
    target = f"{CDN}moved.jpg"
    dm, session = manager({url: FakeResponse(302, headers={"Location": target}), target: jpeg_response()})
    report = dm.download(post, post.images, tmp_path)
    assert len(report.saved) == 1 and session.calls == [url, target]


def test_timeout_is_reported_as_network_error(tmp_path):
    post = make_post(1)
    dm, _ = manager({post.images[0].full_url: requests.Timeout("slow")})
    report = dm.download(post, post.images, tmp_path)
    assert "demorou" in report.failed[0].error


def test_redact_url_strips_signatures():
    assert redact_url(f"{CDN}a.jpg?oh=SECRET&oe=1") == "https://scontent-fake.cdninstagram.com/v/t51/a.jpg"
