"""Execução em segundo plano compatível com o modelo de threads do Qt.

As tarefas rodam em ``QThreadPool`` e se comunicam com a interface exclusivamente
por sinais (entregues na thread principal por conexão enfileirada). Nenhum widget
é tocado fora da thread da interface.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QImage

from pixora.core.errors import PixoraError
from pixora.core.http import MediaHttpClient

log = logging.getLogger(__name__)


class TaskSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(object)      # PixoraError
    progress = Signal(object)
    done = Signal()


class Task(QRunnable):
    """Executa ``fn(*args, report=..., **kwargs)`` e publica o resultado por sinais.

    Se ``with_progress`` for verdadeiro, ``fn`` recebe um argumento ``report`` que
    emite o sinal ``progress`` de forma segura entre threads.
    """

    def __init__(self, fn: Callable[..., Any], *args: Any, with_progress: bool = False, **kwargs: Any) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self.signals = TaskSignals()
        self._fn, self._args, self._kwargs = fn, args, kwargs
        if with_progress:
            self._kwargs["report"] = self.signals.progress.emit

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
        except PixoraError as exc:
            log.info("Tarefa falhou: %s (%s)", type(exc).__name__, exc)
            self._emit(self.signals.failed, exc)
        except Exception as exc:  # noqa: BLE001 — nunca deixar uma exceção escapar da thread
            log.exception("Erro inesperado em tarefa de segundo plano")
            self._emit(self.signals.failed, PixoraError(detail=repr(exc)))
        else:
            self._emit(self.signals.succeeded, result)
        finally:
            try:
                self.signals.done.emit()
            except RuntimeError:
                pass

    @staticmethod
    def _emit(signal: Any, value: Any) -> None:
        try:
            signal.emit(value)
        except RuntimeError:  # receptor destruído (ex.: janela fechada)
            pass


class _Relay(QObject):
    """Receptor que vive na thread da interface.

    Sinais conectados a *métodos de um QObject* são entregues na thread desse objeto
    (conexão enfileirada). Já funções soltas/lambdas seriam executadas na thread do
    worker — por isso todos os callbacks passam por aqui.
    """

    def __init__(self, runner: "TaskRunner", signals: TaskSignals,
                 on_success: Callable[[Any], None] | None,
                 on_error: Callable[[PixoraError], None] | None,
                 on_progress: Callable[[Any], None] | None) -> None:
        super().__init__(runner)
        self._runner = runner
        self._signals = signals
        self._cbs = (on_success, on_error, on_progress)
        signals.succeeded.connect(self._success)
        signals.failed.connect(self._error)
        signals.progress.connect(self._progress)
        signals.done.connect(self._done)

    @Slot(object)
    def _success(self, value: Any) -> None:
        self._call(self._cbs[0], value)

    @Slot(object)
    def _error(self, value: Any) -> None:
        self._call(self._cbs[1], value)

    @Slot(object)
    def _progress(self, value: Any) -> None:
        self._call(self._cbs[2], value)

    @Slot()
    def _done(self) -> None:
        self._runner._release(self)

    @staticmethod
    def _call(cb: Callable[[Any], None] | None, value: Any) -> None:
        if cb is None:
            return
        try:
            cb(value)
        except Exception:  # noqa: BLE001 — erro na UI não pode derrubar o app
            log.exception("Erro ao processar resultado de tarefa")


class TaskRunner(QObject):
    """Inicia tarefas e entrega resultados na thread da interface."""

    def __init__(self, pool: QThreadPool, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.pool = pool
        self._alive: set[_Relay] = set()

    def start(self, task: Task, *, on_success: Callable[[Any], None] | None = None,
              on_error: Callable[[PixoraError], None] | None = None,
              on_progress: Callable[[Any], None] | None = None) -> Task:
        relay = _Relay(self, task.signals, on_success, on_error, on_progress)
        self._alive.add(relay)
        self.pool.start(task)
        return task

    def _release(self, relay: _Relay) -> None:
        self._alive.discard(relay)
        relay.deleteLater()

    def wait(self, msecs: int = 3000) -> bool:
        return self.pool.waitForDone(msecs)

    @property
    def active(self) -> int:
        return len(self._alive)

    def wait(self, msecs: int = 3000) -> bool:
        return self.pool.waitForDone(msecs)


def load_thumbnail(http: MediaHttpClient, url: str, max_side: int) -> QImage:
    """Baixa e decodifica a miniatura já reduzida (QImage é seguro fora da thread da UI)."""
    data = http.fetch_bytes(url)
    image = QImage.fromData(data)
    if image.isNull():
        raise PixoraError("Não foi possível exibir a prévia desta imagem.")
    if max(image.width(), image.height()) > max_side:
        image = image.scaled(max_side, max_side, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    return image
