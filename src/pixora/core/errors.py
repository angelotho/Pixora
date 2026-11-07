"""Hierarquia de erros do Pixora.

Cada erro carrega uma mensagem amigável (``user_message``) pensada para ser
exibida diretamente na interface, sem detalhes técnicos. Detalhes técnicos vão
apenas para o log, por meio de ``str(exc)`` / ``__cause__``.
"""

from __future__ import annotations


class PixoraError(Exception):
    """Erro base. ``title`` e ``user_message`` são exibidos ao usuário."""

    title: str = "Algo deu errado"
    default_message: str = "Ocorreu um erro inesperado. Tente novamente."

    def __init__(self, user_message: str | None = None, *, detail: str | None = None) -> None:
        self.user_message = user_message or self.default_message
        self.detail = detail
        super().__init__(detail or self.user_message)


# --- Validação de links -----------------------------------------------------

class InvalidUrlError(PixoraError):
    title = "Link inválido"
    default_message = "O endereço informado não é um link válido de publicação do Instagram."


class UnsupportedContentError(PixoraError):
    title = "Conteúdo não suportado"
    default_message = "O Pixora baixa apenas imagens de publicações e carrosséis."


# --- Acesso à publicação ----------------------------------------------------

class PostUnavailableError(PixoraError):
    title = "Publicação indisponível"
    default_message = (
        "Não foi possível acessar esta publicação. Ela pode ter sido removida, "
        "pertencer a uma conta privada ou ter acesso restrito."
    )


class AccessRestrictedError(PixoraError):
    title = "Acesso restrito"
    default_message = (
        "Esta publicação exige login ou tem acesso restrito. O Pixora acessa apenas "
        "conteúdo público e não contorna essas restrições."
    )


class RateLimitedError(PixoraError):
    title = "Muitas solicitações"
    default_message = (
        "O Instagram está limitando temporariamente as consultas. "
        "Aguarde alguns minutos antes de tentar novamente."
    )


class NetworkError(PixoraError):
    title = "Falha de conexão"
    default_message = "Não foi possível conectar. Verifique sua internet e tente novamente."


class ProviderBrokenError(PixoraError):
    title = "Serviço incompatível"
    default_message = (
        "O Instagram respondeu em um formato inesperado. A plataforma pode ter mudado; "
        "verifique se há uma atualização do Pixora."
    )


# --- Downloads --------------------------------------------------------------

class DestinationError(PixoraError):
    title = "Pasta de destino"
    default_message = (
        "Não foi possível gravar na pasta escolhida. Verifique se ela existe e se você "
        "tem permissão de escrita."
    )


class DownloadError(PixoraError):
    title = "Falha no download"
    default_message = "Não foi possível baixar o arquivo."


class CancelledError(PixoraError):
    title = "Cancelado"
    default_message = "A operação foi cancelada."
