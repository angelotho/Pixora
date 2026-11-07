"""Regras de seleção de imagens (lógica pura, sem Qt)."""

from __future__ import annotations

from collections.abc import Iterable


class Selection:
    """Conjunto ordenado de posições selecionadas dentro de um conjunto conhecido."""

    def __init__(self, positions: Iterable[int] = (), *, select_all: bool = True) -> None:
        self._available: tuple[int, ...] = tuple(dict.fromkeys(positions))
        self._selected: set[int] = set(self._available) if select_all else set()

    @property
    def available(self) -> tuple[int, ...]:
        return self._available

    @property
    def total(self) -> int:
        return len(self._available)

    @property
    def count(self) -> int:
        return len(self._selected)

    @property
    def all_selected(self) -> bool:
        return self.total > 0 and self.count == self.total

    @property
    def none_selected(self) -> bool:
        return self.count == 0

    def is_selected(self, position: int) -> bool:
        return position in self._selected

    def set(self, position: int, selected: bool) -> bool:
        """Marca/desmarca. Retorna ``True`` se o estado mudou."""
        if position not in self._available:
            raise KeyError(position)
        before = position in self._selected
        if selected:
            self._selected.add(position)
        else:
            self._selected.discard(position)
        return before != selected

    def toggle(self, position: int) -> bool:
        self.set(position, not self.is_selected(position))
        return self.is_selected(position)

    def select_all(self) -> None:
        self._selected = set(self._available)

    def clear(self) -> None:
        self._selected.clear()

    def selected(self) -> list[int]:
        """Posições selecionadas, na ordem original da publicação."""
        return [p for p in self._available if p in self._selected]

    def summary(self) -> str:
        if self.total == 0:
            return "Nenhuma imagem"
        noun = "imagem" if self.total == 1 else "imagens"
        sel = "selecionada" if self.count == 1 else "selecionadas"
        return f"{self.total} {noun} · {self.count} {sel}"
