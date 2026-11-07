import pytest

from pixora.core.filenames import (
    ConflictPolicy, build_base_name, detect_extension, resolve_target, sanitize_component,
    sniff_image_extension,
)
from pixora.core.selection import Selection

from conftest import JPEG_BYTES, png_bytes


# --- nomes de arquivo -------------------------------------------------------

def test_base_name_pattern():
    assert build_base_name("DeAYvsnn4la", 1) == "instagram_DeAYvsnn4la_01"
    assert build_base_name("DeAYvsnn4la", 3, 10) == "instagram_DeAYvsnn4la_03"
    assert build_base_name("abc_DEF-12", 7, 120) == "instagram_abc_DEF-12_007"


def test_sanitize_component():
    assert sanitize_component('a<b>c:"d/e\\f|g?h*') == "a_b_c__d_e_f_g_h_"
    assert sanitize_component("   ") == "arquivo"
    assert sanitize_component("CON") == "_CON"
    assert len(sanitize_component("x" * 500)) == 100


@pytest.mark.parametrize("head, ext", [
    (JPEG_BYTES[:32], ".jpg"),
    (png_bytes()[:32], ".png"),
    (b"RIFF\x00\x00\x00\x00WEBPVP8 ", ".webp"),
    (b"GIF89a\x00\x00", ".gif"),
    (b"\x00\x00\x00\x1cftypheic\x00\x00", ".heic"),
    (b"\x00\x00\x00\x1cftypavif\x00\x00", ".avif"),
    (b"\x00\x00\x00\x1cftypmif1\x00\x00", ".heif"),
])
def test_extension_from_real_content(head, ext):
    assert detect_extension(head) == ext
    assert sniff_image_extension(head) == ext


def test_content_beats_misleading_header():
    # Servidor diz JPEG, mas o conteúdo é WEBP: vale o conteúdo.
    assert detect_extension(b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/jpeg") == ".webp"


def test_header_and_default_fallbacks():
    assert detect_extension(b"????", "image/png; charset=binary") == ".png"
    assert detect_extension(b"????", None) == ".jpg"
    assert sniff_image_extension(b"<html>") is None


def test_resolve_target_rename_and_skip(tmp_path):
    first, skipped = resolve_target(tmp_path, "img", ".jpg", ConflictPolicy.RENAME)
    assert first.name == "img.jpg" and not skipped
    first.write_bytes(b"x")
    second, skipped = resolve_target(tmp_path, "img", ".jpg", ConflictPolicy.RENAME)
    assert second.name == "img (2).jpg" and not skipped
    second.write_bytes(b"x")
    assert resolve_target(tmp_path, "img", ".jpg", ConflictPolicy.RENAME)[0].name == "img (3).jpg"
    same, skipped = resolve_target(tmp_path, "img", ".jpg", ConflictPolicy.SKIP)
    assert same == first and skipped


# --- seleção ------------------------------------------------------------------

def test_selection_defaults_to_all():
    s = Selection([1, 2, 3])
    assert s.count == 3 and s.all_selected and s.selected() == [1, 2, 3]


def test_selection_toggle_and_order_preserved():
    s = Selection([1, 2, 4, 5])
    s.clear()
    s.set(5, True)
    s.set(1, True)
    assert s.selected() == [1, 5]
    assert s.toggle(4) is True
    assert s.selected() == [1, 4, 5]
    assert s.toggle(4) is False


def test_selection_select_all_clear_and_summary():
    s = Selection([1, 2, 3], select_all=False)
    assert s.none_selected and s.summary() == "3 imagens · 0 selecionadas"
    s.select_all()
    assert s.all_selected
    s.set(2, False)
    assert s.summary() == "3 imagens · 2 selecionadas"
    s.clear()
    assert s.selected() == []
    assert Selection([7]).summary() == "1 imagem · 1 selecionada"
    assert Selection([]).summary() == "Nenhuma imagem"


def test_selection_reports_change_and_rejects_unknown():
    s = Selection([1, 2])
    assert s.set(1, False) is True
    assert s.set(1, False) is False
    with pytest.raises(KeyError):
        s.set(99, True)


def test_selection_ignores_duplicate_positions():
    assert Selection([1, 1, 2]).total == 2
