"""Preferências do usuário em JSON, com escrita atômica e valores validados."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from pixora.core.filenames import ConflictPolicy
from . import paths

log = logging.getLogger(__name__)

THEMES = ("dark", "light")


@dataclass
class Settings:
    theme: str = "dark"
    download_dir: str = ""
    ask_folder_each_time: bool = False
    conflict_policy: str = ConflictPolicy.RENAME.value
    open_folder_after_download: bool = False
    save_history: bool = True
    auto_paste: bool = True
    window_geometry: str = ""

    def __post_init__(self) -> None:
        if self.theme not in THEMES:
            self.theme = "dark"
        if self.conflict_policy not in {p.value for p in ConflictPolicy}:
            self.conflict_policy = ConflictPolicy.RENAME.value
        if not self.download_dir:
            self.download_dir = str(paths.default_download_dir())

    @property
    def download_path(self) -> Path:
        return Path(self.download_dir)

    @property
    def policy(self) -> ConflictPolicy:
        return ConflictPolicy(self.conflict_policy)


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (paths.config_dir() / "settings.json")

    def load(self) -> Settings:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("formato inválido")
        except FileNotFoundError:
            return Settings()
        except (OSError, ValueError) as exc:
            log.warning("Configurações ilegíveis (%s); usando padrões.", exc)
            return Settings()

        known = {f.name: f for f in fields(Settings)}
        clean = {}
        defaults = Settings()
        for key, value in raw.items():
            if key in known and isinstance(value, type(getattr(defaults, key))):
                clean[key] = value
        return Settings(**clean)

    def save(self, settings: Settings) -> None:
        tmp = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            log.exception("Não foi possível salvar as configurações")
