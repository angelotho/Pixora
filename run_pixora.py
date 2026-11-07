"""Ponto de entrada usado pelo PyInstaller (e para executar sem instalar o pacote)."""

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pixora.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
