import json
import time

import pytest

from pixora.core.errors import AccessRestrictedError, InvalidUrlError, PostUnavailableError
from pixora.core.filenames import ConflictPolicy
from pixora.core.http import MediaHttpClient
from pixora.core.logging_setup import redact
from pixora.core.service import PixoraService
from pixora.storage import paths
from pixora.storage.history import HistoryStore
from pixora.storage.settings import Settings, SettingsStore

from conftest import FakeProvider, FakeSession, jpeg_response, make_post


# --- configurações -----------------------------------------------------------

def test_settings_roundtrip(tmp_path):
    store = SettingsStore(tmp_path / "s.json")
    s = store.load()
    assert s.theme == "dark" and s.download_dir  # padrões
    s.theme = "light"
    s.download_dir = str(tmp_path / "fotos")
    s.conflict_policy = "skip"
    s.ask_folder_each_time = True
    store.save(s)
    again = store.load()
    assert again.theme == "light" and again.download_dir == str(tmp_path / "fotos")
    assert again.policy is ConflictPolicy.SKIP and again.ask_folder_each_time


def test_settings_survive_corrupt_or_invalid_file(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("{ isto não é json", encoding="utf-8")
    assert SettingsStore(path).load() == Settings()
    path.write_text(json.dumps({"theme": "neon", "conflict_policy": "explode", "save_history": "sim",
                                "unknown": 1}), encoding="utf-8")
    s = SettingsStore(path).load()
    assert s.theme == "dark" and s.conflict_policy == "rename" and s.save_history is True


def test_app_dirs_live_in_user_profile_not_install_dir(isolated_home):
    assert paths.config_dir().is_relative_to(isolated_home)
    assert paths.log_dir().is_relative_to(isolated_home)


# --- histórico ---------------------------------------------------------------

def test_history_records_and_deduplicates(tmp_path):
    h = HistoryStore(tmp_path / "h.db")
    folder = tmp_path / "out"
    h.record(shortcode="ABC", url="https://www.instagram.com/p/ABC/", owner="x", folder=folder,
             saved_files=["a_01.jpg", "a_02.jpg"], failed_count=0)
    time.sleep(1.1)
    h.record(shortcode="ABC", url="https://www.instagram.com/p/ABC/", owner=None, folder=folder,
             saved_files=["a_02.jpg", "a_03.jpg"], failed_count=1)
    h.record(shortcode="XYZ", url="https://www.instagram.com/p/XYZ/", owner=None, folder=folder,
             saved_files=["x_01.jpg"], failed_count=0)
    entries = h.list()
    assert [e.shortcode for e in entries] == ["XYZ", "ABC"]
    abc = entries[1]
    assert abc.files == ("a_01.jpg", "a_02.jpg", "a_03.jpg")  # sem duplicatas
    assert abc.saved_count == 3 and abc.failed_count == 1 and abc.owner == "x"
    assert abc.updated_at > abc.created_at


def test_history_same_post_different_folder_is_separate(tmp_path):
    h = HistoryStore(tmp_path / "h.db")
    for sub in ("a", "b"):
        h.record(shortcode="ABC", url="u", owner=None, folder=tmp_path / sub, saved_files=["f"], failed_count=0)
    assert len(h.list()) == 2


def test_history_delete_and_clear(tmp_path):
    h = HistoryStore(tmp_path / "h.db")
    for code in ("A", "B", "C"):
        h.record(shortcode=code, url="u", owner=None, folder=tmp_path, saved_files=[], failed_count=0)
    first = h.list()[0]
    h.delete(first.id)
    assert len(h.list()) == 2
    h.clear()
    assert h.list() == []


# --- logs ----------------------------------------------------------------------

def test_logs_redact_tokens_and_signatures():
    line = ("GET https://scontent.cdninstagram.com/v/a.jpg?oh=SIGNATURE&oe=123 sessionid=abc123 "
            "password=hunter2")
    out = redact(line)
    assert "SIGNATURE" not in out and "abc123" not in out and "hunter2" not in out
    assert "https://scontent.cdninstagram.com/v/a.jpg" in out


# --- serviço (camada de negócio, ponta a ponta com dublês) ---------------------

def test_service_validate_fetch_and_download(tmp_path):
    post = make_post(2, shortcode="DeAYvsnn4la")
    provider = FakeProvider({"DeAYvsnn4la": post})
    session = FakeSession({i.full_url: jpeg_response() for i in post.images})
    svc = PixoraService(provider, MediaHttpClient(session))

    parsed = svc.validate("instagram.com/p/DeAYvsnn4la/?igsh=xyz")
    info = svc.fetch(parsed)
    assert provider.calls == ["DeAYvsnn4la"]
    report = svc.download(info, info.images, tmp_path, ConflictPolicy.RENAME)
    assert len(report.saved) == 2


def test_service_invalid_url_never_reaches_provider():
    provider = FakeProvider()
    svc = PixoraService(provider)
    with pytest.raises(InvalidUrlError):
        svc.validate("https://evil.com/p/DeAYvsnn4la/")
    assert provider.calls == []


@pytest.mark.parametrize("err", [PostUnavailableError(), AccessRestrictedError()])
def test_service_propagates_friendly_errors(err):
    svc = PixoraService(FakeProvider({"DeAYvsnn4la": err}))
    with pytest.raises(type(err)):
        svc.fetch(svc.validate("https://www.instagram.com/p/DeAYvsnn4la/"))
