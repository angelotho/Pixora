"""Contrato da camada de integração.

A interface gráfica e a lógica de negócio dependem apenas de ``PostProvider``.
Trocar a biblioteca de acesso (por exemplo, se o Instaloader deixar de funcionar)
exige somente uma nova implementação deste protocolo.
"""

from __future__ import annotations

from typing import Protocol

from pixora.core.models import PostInfo


class PostProvider(Protocol):
    name: str

    def fetch_post(self, shortcode: str) -> PostInfo:
        """Obtém os metadados e as URLs das imagens da publicação.

        Deve levar apenas subclasses de :class:`pixora.core.errors.PixoraError`.
        Não deve fazer login, usar cookies do navegador nem contornar restrições.
        """
        ...
