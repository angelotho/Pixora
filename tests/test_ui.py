"""Testes da interface em modo offscreen, com provider e HTTP simulados."""

from __future__ import annotations

import time

import pytest
import requests

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from pixora.core.errors import AccessRestrictedError  # noqa: E402
from pixora.core.http import MediaHttpClient  # noqa: E402
from pixora.core.service import PixoraService  # noqa: E402
from pixora.storage.history import HistoryStore  # noqa: E402
from pixora.storage.settings import SettingsStore  # noqa: E402
from pixora.ui import theme  # noqa: E402

from conftest import FakeProvider, FakeResponse, FakeSession, jpeg_response, make_post, png_bytes  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    theme.apply_theme(app, "dark")
    yield app


def wait_until(app, cond, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.01)
    raise AssertionError("condição não atingida a tempo")


@pytest.fixture
def window_factory(qapp, tmp_path):
    from pixora.ui.main_window import MainWindow
    created = []

    def make(posts, routes=None, settings=None):
        provider = FakeProvider(posts)
        session = FakeSession(routes or {})
        svc = PixoraService(provider, MediaHttpClient(session))
        store = SettingsStore(tmp_path / "settings.json")
        if settings:
            s = store.load()
            for k, v in settings.items():
                setattr(s, k, v)
            store.save(s)
        win = MainWindow(svc, store, HistoryStore(tmp_path / "history.db"), "log")
        win._session_folder = tmp_path / "out"
        win.show()
        created.append(win)
        return win, provider, session

    yield make
    for w in created:
        w._downloading = False
        w.close()
        w.deleteLater()
    qapp.processEvents()


def routes_for(post, *, broken_thumb=None):
    r = {}
    for i in post.images:
        r[i.full_url] = jpeg_response()
        r[i.thumbnail_url] = FakeResponse(200, png_bytes(8, 10), {"Content-Type": "image/png"})
    if broken_thumb:
        r[post.images[broken_thumb - 1].thumbnail_url] = requests.ConnectionError("x")
    return r


def test_header_shows_app_version(window_factory):
    from pixora import __version__

    win, _, _ = window_factory({})
    assert win.version_label.text() == f"v{__version__}"


def test_invalid_link_shows_inline_error_without_network(window_factory):
    win, provider, _ = window_factory({})
    win.url_input.setText("https://example.com/p/abc123")
    win.analyze()
    assert win.url_input.property("invalid") is True
    assert "não pertence ao Instagram" in win.url_hint.text()
    assert provider.calls == [] and not win._analyzing


def test_carousel_flow_select_and_download(qapp, window_factory, tmp_path):
    post = make_post(4, shortcode="CARouSEL01")
    win, provider, _ = window_factory({"CARouSEL01": post}, routes_for(post, broken_thumb=3))
    win.url_input.setText("https://www.instagram.com/p/CARouSEL01/?igsh=abc")
    win.analyze()
    assert win._analyzing and not win.analyze_btn.isEnabled()  # indicador de carregamento ativo
    wait_until(qapp, lambda: win._post is not None)
    assert list(win.grid.cards) == [1, 2, 3, 4]
    wait_until(qapp, lambda: not any(c.loading for c in win.grid.cards.values()))
    assert win.grid.cards[3]._failed and win.grid.cards[1]._image is not None  # prévia com falha isolada
    assert win.counter.text() == "4 imagens · 4 selecionadas"
    assert win.download_btn.text() == "Baixar todas (4)"

    win.clear_selection()
    assert not win.download_btn.isEnabled()
    win.grid.cards[2]._toggle()
    win.grid.cards[4]._toggle()
    assert win.counter.text() == "4 imagens · 2 selecionadas"
    assert win.download_btn.text() == "Baixar selecionadas (2)"

    win.start_download()
    assert win._downloading and win.progress_box.isVisible()
    wait_until(qapp, lambda: not win._downloading)
    out = tmp_path / "out"
    assert sorted(p.name for p in out.iterdir()) == ["instagram_CARouSEL01_02.jpg", "instagram_CARouSEL01_04.jpg"]
    assert win.banner.isVisible() and win.banner._title.text() == "Download concluído"
    entries = win.history.list()
    assert len(entries) == 1 and entries[0].saved_count == 2


def test_single_image_label(qapp, window_factory):
    post = make_post(1, shortcode="SINGLEpost1")
    win, _, _ = window_factory({"SINGLEpost1": post}, routes_for(post))
    win.url_input.setText("https://www.instagram.com/p/SINGLEpost1/")
    win.analyze()
    wait_until(qapp, lambda: win._post is not None)
    assert win.download_btn.text() == "Baixar imagem"
    assert win.post_title.text() == "Imagem única"


def test_restricted_post_shows_error_state_and_retry(qapp, window_factory):
    win, provider, _ = window_factory({"PRIVATEpost": AccessRestrictedError()})
    win.url_input.setText("https://www.instagram.com/p/PRIVATEpost/")
    win.analyze()
    wait_until(qapp, lambda: not win._analyzing)
    assert win.state_view._title.text() == "Acesso restrito"
    assert not win.download_btn.isEnabled()
    win._on_state_action()  # "Tentar novamente"
    wait_until(qapp, lambda: not win._analyzing)
    assert provider.calls == ["PRIVATEpost", "PRIVATEpost"]


def test_failed_downloads_are_reported(qapp, window_factory):
    post = make_post(2, shortcode="PARTIALdl01")
    routes = routes_for(post)
    routes[post.images[1].full_url] = FakeResponse(404)
    win, _, _ = window_factory({"PARTIALdl01": post}, routes)
    win.url_input.setText("https://www.instagram.com/p/PARTIALdl01/")
    win.analyze()
    wait_until(qapp, lambda: win._post is not None)
    win.start_download()
    wait_until(qapp, lambda: not win._downloading)
    assert "1 imagem salva" in win.banner._title.text() and "1 com falha" in win.banner._title.text()


def test_cancel_analysis_discards_late_result(qapp, window_factory):
    post = make_post(2, shortcode="LATEresult1")
    win, _, _ = window_factory({"LATEresult1": post}, routes_for(post))
    win.url_input.setText("https://www.instagram.com/p/LATEresult1/")
    win.analyze()
    win.cancel_analysis()
    for _ in range(50):
        qapp.processEvents()
        time.sleep(0.01)
    assert win._post is None and not win._analyzing


def test_theme_switch_does_not_break(qapp, window_factory):
    win, _, _ = window_factory({})
    theme.apply_theme(qapp, "light")
    win._restyle_icons()
    assert theme.current().name == "light"
    theme.apply_theme(qapp, "dark")
    win._restyle_icons()
