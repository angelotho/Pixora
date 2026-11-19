"""Animação de abertura e novo logotipo."""

from __future__ import annotations

import time

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from pixora.ui import icons, splash, theme  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    theme.apply_theme(app, "dark")
    yield app


def wait_until(app, cond, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.01)
    raise AssertionError("condição não atingida a tempo")


def test_logo_asset_loads_and_tints(qapp):
    assert icons.LOGO_PATH.exists()
    img = icons.logo_image()
    assert not img.isNull() and img.width() == img.height()
    assert img.pixelColor(0, 0).alpha() == 0  # fundo transparente
    pm = icons.logo_pixmap(38, theme.current().brand)
    assert not pm.isNull() and round(pm.width() / pm.devicePixelRatio()) == 38
    assert not icons.app_icon().isNull()


@pytest.mark.parametrize("mode", ["dark", "light"])
def test_every_frame_paints(qapp, mode):
    theme.apply_theme(qapp, mode)
    sp = splash.SplashScreen()
    for ms in range(0, splash.DURATION_MS + 1, 50):
        sp._progress = ms / splash.DURATION_MS
        assert not sp.grab().isNull()
    sp.deleteLater()
    theme.apply_theme(qapp, "dark")


def test_play_intro_reveals_window_and_finishes(qapp, monkeypatch):
    monkeypatch.delenv("PIXORA_NO_SPLASH", raising=False)
    monkeypatch.setattr(splash, "animations_enabled", lambda: True)
    win = QWidget()
    sp = splash.play_intro(win, duration_ms=200)
    assert sp is not None and sp.isVisible() and not win.isVisible()
    done = []
    sp.finished.connect(lambda: done.append(True))
    wait_until(qapp, lambda: done)
    assert win.isVisible() and win.windowOpacity() == pytest.approx(1.0)
    win.close()


def test_click_skips_to_the_end(qapp, monkeypatch):
    monkeypatch.setattr(splash, "animations_enabled", lambda: True)
    win = QWidget()
    sp = splash.play_intro(win, duration_ms=60_000)
    sp.skip()
    wait_until(qapp, lambda: win.isVisible(), timeout=3.0)
    win.close()


def test_no_animation_shows_window_immediately(qapp, monkeypatch):
    monkeypatch.setenv("PIXORA_NO_SPLASH", "1")
    win = QWidget()
    assert splash.play_intro(win) is None
    assert win.isVisible()
    win.close()
