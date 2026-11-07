"""Ponto de entrada do aplicativo."""

from __future__ import annotations

import logging
import os
import sys
import threading
import traceback

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from pixora import __app_name__, __version__
from pixora.core.logging_setup import setup_logging
from pixora.core.service import PixoraService
from pixora.providers.instaloader_provider import InstaloaderProvider
from pixora.storage import paths
from pixora.storage.history import HistoryStore
from pixora.storage.settings import SettingsStore
from pixora.ui import icons, theme

log = logging.getLogger("pixora")


def _install_exception_hooks(app: QApplication) -> None:
    """Registra erros inesperados no log e mostra uma mensagem amigável, sem encerrar o app."""
    showing = {"active": False}

    def show_error() -> None:
        if showing["active"]:
            return
        showing["active"] = True
        try:
            QMessageBox.warning(
                app.activeWindow(), "Erro inesperado",
                "Ocorreu um erro inesperado, mas o Pixora continua funcionando.\n"
                "Se o problema persistir, reinicie o aplicativo.",
            )
        finally:
            showing["active"] = False

    def hook(exc_type, exc, tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        log.error("Exceção não tratada:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
        QTimer.singleShot(0, show_error)

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        log.error("Exceção não tratada em thread %s:\n%s", args.thread.name if args.thread else "?",
                  "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))

    sys.excepthook = hook
    threading.excepthook = thread_hook


def create_app(argv: list[str] | None = None) -> QApplication:
    if sys.platform == "win32":
        try:  # agrupa a janela sob o ícone do Pixora na barra de tarefas
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Pixora.Desktop")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(__app_name__)
    app.setFont(theme.default_font())
    app.setWindowIcon(icons.app_icon())
    _install_qt_translation(app)
    return app  # type: ignore[return-value]


def _install_qt_translation(app: QApplication) -> None:
    """Traduz textos padrão do Qt (botões Sim/Não, diálogos de pasta) para português."""
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator

    translator = QTranslator(app)
    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil), "qtbase", "_", folder):
        app.installTranslator(translator)
        app._pixora_translator = translator  # type: ignore[attr-defined]  # mantém referência viva


def run_diagnostics(url: str) -> int:
    """Verifica, sem interface, a cadeia completa: validação → Instagram → prévia → download.

    Uso: ``Pixora.exe --diagnose <link>``. O resultado vai para o log e para
    ``diagnostico.txt`` na pasta de logs; o código de saída é 0 em caso de sucesso.
    """
    import tempfile
    from pathlib import Path

    from PySide6.QtGui import QGuiApplication, QImage

    from pixora.core.errors import PixoraError
    from pixora.core.filenames import ConflictPolicy

    _ = QGuiApplication.instance() or QGuiApplication([sys.argv[0], "-platform", "offscreen"])
    lines: list[str] = [f"{__app_name__} {__version__} — diagnóstico"]
    ok = True
    try:
        svc = PixoraService(InstaloaderProvider())
        post = svc.fetch(svc.validate(url))
        lines.append(f"Publicação: {post.shortcode} ({post.kind.value}), {post.image_count} imagem(ns)")
        thumb = QImage.fromData(svc.http.fetch_bytes(post.images[0].thumbnail_url))
        lines.append(f"Prévia decodificada: {not thumb.isNull()} ({thumb.width()}x{thumb.height()})")
        ok = ok and not thumb.isNull()
        with tempfile.TemporaryDirectory(prefix="pixora-diag-") as tmp:
            report = svc.download(post, post.images[:1], Path(tmp), ConflictPolicy.RENAME)
            for r in report.results:
                size = r.path.stat().st_size if r.path and r.path.exists() else 0
                lines.append(f"Download: {'OK' if r.ok else 'FALHA'} {r.path.name if r.path else ''} "
                             f"{size} bytes {r.error or ''}".rstrip())
            ok = ok and bool(report.saved)
    except PixoraError as exc:
        ok = False
        lines.append(f"ERRO: {exc.title}: {exc.user_message}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        log.exception("Falha no diagnóstico")
        lines.append(f"ERRO inesperado: {exc!r}")
    lines.append("RESULTADO: " + ("OK" if ok else "FALHA"))
    text = "\n".join(lines)
    log.info("\n%s", text)
    try:
        (paths.log_dir() / "diagnostico.txt").write_text(text + "\n", encoding="utf-8")
    except OSError:
        pass
    if sys.stdout:
        print(text)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    log_file = setup_logging(paths.log_dir())
    log.info("Iniciando %s %s (Python %s, %s)", __app_name__, __version__, sys.version.split()[0], sys.platform)
    args = list(argv if argv is not None else sys.argv)
    if "--diagnose" in args:
        i = args.index("--diagnose")
        return run_diagnostics(args[i + 1] if i + 1 < len(args) else "")
    app = create_app(argv)
    _install_exception_hooks(app)

    from pixora.ui.main_window import MainWindow  # importado após o QApplication existir

    settings_store = SettingsStore()
    settings = settings_store.load()
    theme.apply_theme(app, settings.theme)
    try:
        history = HistoryStore()
    except Exception:  # noqa: BLE001 — histórico corrompido não pode impedir o uso
        log.exception("Histórico indisponível; usando um histórico temporário nesta sessão")
        import tempfile
        from pathlib import Path
        history = HistoryStore(Path(tempfile.mkdtemp(prefix="pixora-")) / "history.db")

    service = PixoraService(InstaloaderProvider())
    window = MainWindow(service, settings_store, history, str(log_file))
    window.show()

    if os.environ.get("PIXORA_SMOKE_TEST"):
        # Usado no build para confirmar que o executável inicia corretamente.
        QTimer.singleShot(int(os.environ.get("PIXORA_SMOKE_TEST_MS", "1500")), app.quit)

    code = app.exec()
    log.info("Encerrando (código %s)", code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
