"""Janela principal do Pixora."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, Qt, QThreadPool, QTimer, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QBoxLayout, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from pixora import __app_name__, __version__
from pixora.core.downloader import Progress
from pixora.core.errors import (
    AccessRestrictedError, NetworkError, PixoraError, PostUnavailableError, ProviderBrokenError,
    RateLimitedError, UnsupportedContentError,
)
from pixora.core.models import DownloadReport, ParsedPostUrl, PostInfo, PostKind
from pixora.core.selection import Selection
from pixora.core.service import PixoraService
from pixora.core.url_validator import is_probable_instagram_url
from pixora.storage.history import HistoryStore
from pixora.storage.settings import Settings, SettingsStore
from pixora.ui import icons, theme
from pixora.ui.dialogs.history_dialog import HistoryDialog
from pixora.ui.dialogs.settings_dialog import SettingsDialog
from pixora.ui.widgets.common import Banner, StateView, label, make_button, repolish, set_button_icon
from pixora.ui.widgets.gallery import ImageGrid
from pixora.ui.workers import Task, TaskRunner, load_thumbnail

log = logging.getLogger(__name__)

PAGE_STATE, PAGE_RESULTS = 0, 1
THUMB_MAX_SIDE_GRID = 640
THUMB_MAX_SIDE_SINGLE = 1280
NARROW_WIDTH = 820


def _error_visual(exc: PixoraError) -> tuple[str, str]:
    if isinstance(exc, NetworkError):
        return "wifi-off", "warning"
    if isinstance(exc, AccessRestrictedError):
        return "lock", "warning"
    if isinstance(exc, RateLimitedError):
        return "clock", "warning"
    if isinstance(exc, UnsupportedContentError):
        return "video-off", "muted"
    if isinstance(exc, (PostUnavailableError, ProviderBrokenError)):
        return "alert", "danger"
    return "alert", "danger"


class MainWindow(QMainWindow):
    def __init__(self, service: PixoraService, settings_store: SettingsStore, history: HistoryStore,
                 log_path: str) -> None:
        super().__init__()
        self.service = service
        self.settings_store = settings_store
        self.settings: Settings = settings_store.load()
        self.history = history
        self.log_path = log_path

        self._runner = TaskRunner(QThreadPool.globalInstance(), self)
        thumb_pool = QThreadPool(self)
        thumb_pool.setMaxThreadCount(4)
        self._thumbs = TaskRunner(thumb_pool, self)

        self._generation = 0            # invalida resultados de análises antigas/canceladas
        self._analyzing = False
        self._downloading = False
        self._cancel_event: threading.Event | None = None
        self._post: PostInfo | None = None
        self._selection = Selection()
        self._session_folder = Path(self.settings.download_dir)
        self._last_auto_paste = ""
        self._last_folder: Path | None = None
        self._narrow: bool | None = None

        self.setWindowTitle(__app_name__)
        self.setWindowIcon(icons.app_icon())
        self.setMinimumSize(680, 620)
        self.resize(1120, 780)
        if self.settings.window_geometry:
            try:
                self.restoreGeometry(QByteArray.fromBase64(self.settings.window_geometry.encode()))
            except Exception:  # noqa: BLE001
                pass

        self._build()
        self._show_empty()
        self._update_footer()
        self.url_input.setFocus()

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(28, 20, 28, 20)
        outer.setSpacing(16)

        # Cabeçalho
        header = QHBoxLayout()
        header.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(icons.logo_pixmap(38))
        logo.setFixedSize(38, 38)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addWidget(label(__app_name__, "appTitle"))
        self.version_label = label(f"v{__version__}", "version")
        self.version_label.setToolTip(f"{__app_name__} versão {__version__}")
        title_row.addWidget(self.version_label, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch(1)
        titles.addLayout(title_row)
        titles.addWidget(label("Imagens de publicações do Instagram", "appSubtitle"))
        header.addWidget(logo)
        header.addLayout(titles)
        header.addStretch(1)
        self.history_btn = make_button("Histórico", variant="ghost", icon_name="history",
                                       tooltip="Downloads anteriores (Ctrl+H)")
        self.history_btn.clicked.connect(self.open_history)
        self.settings_btn = make_button("", variant="icon", icon_name="settings",
                                        tooltip="Configurações (Ctrl+,)")
        self.settings_btn.clicked.connect(self.open_settings)
        header.addWidget(self.history_btn)
        header.addWidget(self.settings_btn)
        outer.addLayout(header)

        # Cartão do link
        url_card = QFrame()
        url_card.setObjectName("Card")
        uc = QVBoxLayout(url_card)
        uc.setContentsMargins(20, 16, 20, 14)
        uc.setSpacing(10)
        uc.addWidget(label("LINK DA PUBLICAÇÃO", "section"))
        self.url_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.url_row.setSpacing(10)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.instagram.com/p/…")
        self.url_input.setClearButtonEnabled(True)
        self.url_input.setAccessibleName("Link da publicação")
        self._link_action = QAction(self.url_input)
        self.url_input.addAction(self._link_action, QLineEdit.ActionPosition.LeadingPosition)
        self.url_input.returnPressed.connect(self.analyze)
        self.url_input.textChanged.connect(self._on_url_changed)
        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.paste_btn = make_button("Colar", variant="secondary", icon_name="paste",
                                     tooltip="Colar da área de transferência")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        self.analyze_btn = make_button("Analisar", variant="primary", icon_name="search",
                                       tooltip="Identificar as imagens da publicação (Enter)")
        self.analyze_btn.clicked.connect(self.analyze)
        self.analyze_btn.setMinimumWidth(130)
        btns.addWidget(self.paste_btn)
        btns.addWidget(self.analyze_btn)
        self.url_row.addWidget(self.url_input, 1)
        self.url_row.addLayout(btns)
        uc.addLayout(self.url_row)
        self.url_hint = label("Funciona com publicações públicas de imagem única e carrosséis.", "faint")
        uc.addWidget(self.url_hint)
        outer.addWidget(url_card)

        # Área central
        self.pages = QStackedWidget()
        self.state_view = StateView()
        self.state_view.action_clicked.connect(self._on_state_action)
        self.pages.addWidget(self.state_view)

        results = QWidget()
        rl = QVBoxLayout(results)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(12)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        self.post_title = label("", "heading")
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        self.post_meta = label("", "muted")
        self.open_post_btn = make_button("Abrir no Instagram", variant="link")
        self.open_post_btn.clicked.connect(self._open_post_in_browser)
        meta_row.addWidget(self.post_meta)
        meta_row.addWidget(self.open_post_btn)
        meta_row.addStretch(1)
        info_col.addWidget(self.post_title)
        info_col.addLayout(meta_row)
        toolbar.addLayout(info_col, 1)
        self.counter = label("", "counter")
        self.select_all_btn = make_button("Selecionar todas", variant="ghost", icon_name="select-all")
        self.select_all_btn.clicked.connect(self.select_all)
        self.clear_sel_btn = make_button("Limpar seleção", variant="ghost", icon_name="select-none")
        self.clear_sel_btn.clicked.connect(self.clear_selection)
        toolbar.addWidget(self.counter, 0, Qt.AlignmentFlag.AlignVCenter)
        toolbar.addSpacing(6)
        toolbar.addWidget(self.select_all_btn)
        toolbar.addWidget(self.clear_sel_btn)
        rl.addLayout(toolbar)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(2, 2, 6, 2)
        self.grid = ImageGrid()
        self.grid.toggled.connect(self._on_card_toggled)
        hl.addWidget(self.grid)
        hl.addStretch(1)
        self.scroll.setWidget(holder)
        self.scroll.viewport().installEventFilter(self)
        rl.addWidget(self.scroll, 1)
        self.pages.addWidget(results)
        outer.addWidget(self.pages, 1)

        # Banner de resultado
        self.banner = Banner()
        self.banner.action_clicked.connect(self._on_banner_action)
        outer.addWidget(self.banner)

        # Rodapé
        footer = QFrame()
        footer.setObjectName("Footer")
        self.footer_row = QBoxLayout(QBoxLayout.Direction.LeftToRight, footer)
        self.footer_row.setContentsMargins(16, 12, 12, 12)
        self.footer_row.setSpacing(12)
        dest = QHBoxLayout()
        dest.setSpacing(10)
        self.folder_icon = QLabel()
        self.folder_icon.setFixedSize(20, 20)
        dest_text = QVBoxLayout()
        dest_text.setSpacing(0)
        dest_text.addWidget(label("SALVAR EM", "section"))
        self.folder_label = QLabel()
        self.folder_label.setMinimumWidth(120)
        self.folder_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        dest_text.addWidget(self.folder_label)
        self.change_folder_btn = make_button("Alterar", variant="small", tooltip="Escolher a pasta de destino")
        self.change_folder_btn.clicked.connect(self.choose_folder)
        dest.addWidget(self.folder_icon)
        dest.addLayout(dest_text, 1)
        dest.addWidget(self.change_folder_btn)
        self.footer_row.addLayout(dest, 1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        prog_col = QVBoxLayout()
        prog_col.setSpacing(6)
        self.progress_label = label("", "counter")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setFixedWidth(220)
        prog_col.addWidget(self.progress_label)
        prog_col.addWidget(self.progress)
        self.progress_box = QWidget()
        self.progress_box.setLayout(prog_col)
        self.progress_box.hide()
        self.cancel_btn = make_button("Cancelar", variant="ghost", icon_name="x")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.hide()
        self.download_btn = make_button("Baixar", variant="primary", icon_name="download")
        self.download_btn.setMinimumWidth(190)
        self.download_btn.clicked.connect(self.start_download)
        actions.addWidget(self.progress_box)
        actions.addWidget(self.cancel_btn)
        actions.addWidget(self.download_btn)
        self.footer_row.addLayout(actions)
        outer.addWidget(footer)

        # Atalhos
        QShortcut(QKeySequence("Ctrl+L"), self, activated=lambda: (self.url_input.setFocus(),
                                                                    self.url_input.selectAll()))
        QShortcut(QKeySequence("Ctrl+H"), self, activated=self.open_history)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self.open_settings)
        QShortcut(QKeySequence("Ctrl+Shift+A"), self, activated=self.select_all)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self.start_download)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self._escape)

        self._restyle_icons()

    def _restyle_icons(self) -> None:
        t = theme.current()
        self._link_action.setIcon(icons.icon("link", t.text_faint, 18))
        self.folder_icon.setPixmap(icons.pixmap("folder", t.accent, 20))
        for btn in self.findChildren(type(self.analyze_btn)):
            name = btn.property("iconName")
            if name and btn.property("variant") != "danger":
                set_button_icon(btn, name, size=16 if btn.property("variant") == "small" else 18)
        self.state_view.restyle()
        if self.banner.isVisible():
            self.banner.restyle()
        self.grid.update()
        for card in self.grid.cards.values():
            card.update()

    # ------------------------------------------------------------ eventos
    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.scroll.viewport() and event.type() == QEvent.Type.Resize:
            self.grid.set_viewport_height(self.scroll.viewport().height())
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        narrow = self.width() < NARROW_WIDTH
        if narrow != self._narrow:
            self._narrow = narrow
            d = QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
            self.url_row.setDirection(d)
            self.footer_row.setDirection(d)
            self.select_all_btn.setText("" if narrow else "Selecionar todas")
            self.clear_sel_btn.setText("" if narrow else "Limpar seleção")
            self.select_all_btn.setToolTip("Selecionar todas (Ctrl+Shift+A)")
            self.clear_sel_btn.setToolTip("Limpar seleção")
        self._update_folder_label()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        theme.apply_window_frame(self)

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow():
            QTimer.singleShot(0, self._maybe_auto_paste)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._downloading:
            answer = QMessageBox.question(
                self, "Download em andamento",
                "Há um download em andamento. Deseja cancelá-lo e sair?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            if self._cancel_event:
                self._cancel_event.set()
            self._runner.wait(5000)
        self._generation += 1
        self.settings.window_geometry = bytes(self.saveGeometry().toBase64()).decode()
        self.settings_store.save(self.settings)
        self._thumbs.pool.clear()
        super().closeEvent(event)

    def _escape(self) -> None:
        if self._analyzing:
            self.cancel_analysis()
        elif self._downloading:
            self.cancel_download()

    # --------------------------------------------------------- link / colar
    def _on_url_changed(self, _text: str) -> None:
        if self.url_input.property("invalid"):
            self.url_input.setProperty("invalid", False)
            repolish(self.url_input)
            self._set_hint("Funciona com publicações públicas de imagem única e carrosséis.", "faint")

    def _set_hint(self, text: str, role: str) -> None:
        self.url_hint.setText(text)
        self.url_hint.setProperty("role", role)
        repolish(self.url_hint)

    def paste_from_clipboard(self) -> None:
        text = (QGuiApplication.clipboard().text() or "").strip()
        if not text:
            self._set_hint("A área de transferência está vazia.", "error")
            return
        self.url_input.setText(text)
        self.url_input.setFocus()
        if is_probable_instagram_url(text):
            self.analyze()

    def _maybe_auto_paste(self) -> None:
        if not self.settings.auto_paste or self._analyzing or self._downloading:
            return
        if self.url_input.text().strip():
            return
        text = (QGuiApplication.clipboard().text() or "").strip()
        if text and text != self._last_auto_paste and is_probable_instagram_url(text):
            self._last_auto_paste = text
            self.url_input.setText(text)
            self._set_hint("Link colado da área de transferência. Pressione Enter para analisar.", "success")

    # ------------------------------------------------------------- análise
    def analyze(self) -> None:
        if self._analyzing or self._downloading:
            return
        try:
            parsed = self.service.validate(self.url_input.text())
        except PixoraError as exc:
            self.url_input.setProperty("invalid", True)
            repolish(self.url_input)
            self._set_hint(exc.user_message, "error")
            return
        self.url_input.setText(parsed.canonical_url)
        self.url_input.setProperty("invalid", False)
        repolish(self.url_input)
        self._start_analysis(parsed)

    def _start_analysis(self, parsed: ParsedPostUrl) -> None:
        self._generation += 1
        gen = self._generation
        self._analyzing = True
        self._last_parsed = parsed
        self.banner.hide()
        self._set_hint("Funciona com publicações públicas de imagem única e carrosséis.", "faint")
        self.state_view.set_state(
            icon_name=None, title="Analisando publicação…",
            text="Buscando as imagens disponíveis. Isso costuma levar poucos segundos.",
            loading=True, action="Cancelar", action_icon="x",
        )
        self.pages.setCurrentIndex(PAGE_STATE)
        self._update_controls()
        task = Task(self.service.fetch, parsed)
        self._runner.start(
            task,
            on_success=lambda post, g=gen: self._on_analysis_done(g, post),
            on_error=lambda exc, g=gen: self._on_analysis_failed(g, exc),
        )

    def cancel_analysis(self) -> None:
        if not self._analyzing:
            return
        self._generation += 1
        self._analyzing = False
        if self._post:
            self.pages.setCurrentIndex(PAGE_RESULTS)
        else:
            self._show_empty()
        self._update_controls()

    def _on_analysis_done(self, gen: int, post: PostInfo) -> None:
        if gen != self._generation:
            return
        self._analyzing = False
        self._post = post
        self._selection = Selection([i.position for i in post.images], select_all=True)
        is_single = post.kind is PostKind.SINGLE
        self.post_title.setText("Imagem única" if is_single else f"Carrossel · {post.image_count} imagens")
        meta = f"@{post.owner}" if post.owner else post.shortcode
        self.post_meta.setText(meta)
        self.grid.set_items(post.images)
        self.pages.setCurrentIndex(PAGE_RESULTS)
        self.scroll.verticalScrollBar().setValue(0)
        max_side = THUMB_MAX_SIDE_SINGLE if is_single else THUMB_MAX_SIDE_GRID
        for item in post.images:
            task = Task(load_thumbnail, self.service.http, item.thumbnail_url, max_side)
            self._thumbs.start(
                task,
                on_success=lambda img, g=gen, p=item.position: self._on_thumb(g, p, img),
                on_error=lambda _e, g=gen, p=item.position: self._on_thumb_failed(g, p),
            )
        if post.skipped_videos:
            n = post.skipped_videos
            self.banner.show_message(
                "info", f"{n} vídeo{'s' if n > 1 else ''} ignorado{'s' if n > 1 else ''}",
                "O Pixora baixa apenas imagens; os vídeos deste carrossel não foram incluídos.",
            )
        self._update_controls()

    def _on_analysis_failed(self, gen: int, exc: PixoraError) -> None:
        if gen != self._generation:
            return
        self._analyzing = False
        self._post = None
        self.grid.clear()
        icon_name, tone = _error_visual(exc)
        retry = not isinstance(exc, UnsupportedContentError)
        self.state_view.set_state(
            icon_name=icon_name, title=exc.title, text=exc.user_message, tone=tone,
            action="Tentar novamente" if retry else None, action_icon="refresh" if retry else None,
        )
        self.pages.setCurrentIndex(PAGE_STATE)
        self._update_controls()

    def _on_state_action(self) -> None:
        if self._analyzing:
            self.cancel_analysis()
        elif getattr(self, "_last_parsed", None) is not None:
            self._start_analysis(self._last_parsed)

    def _on_thumb(self, gen: int, position: int, image) -> None:
        if gen == self._generation:
            self.grid.set_thumbnail(position, image)

    def _on_thumb_failed(self, gen: int, position: int) -> None:
        if gen == self._generation:
            self.grid.set_thumbnail_failed(position)

    def _show_empty(self) -> None:
        self.state_view.set_state(
            icon_name="images", title="Cole um link para começar",
            text="Copie o link de uma publicação pública no Instagram (⋯ › Copiar link), cole acima e "
                 "clique em Analisar. Você poderá escolher quais imagens baixar.",
        )
        self.pages.setCurrentIndex(PAGE_STATE)

    def _open_post_in_browser(self) -> None:
        if self._post:
            QDesktopServices.openUrl(QUrl(self._post.url))

    # ------------------------------------------------------------ seleção
    def _on_card_toggled(self, position: int, selected: bool) -> None:
        self._selection.set(position, selected)
        self._update_controls()

    def select_all(self) -> None:
        if self._post and not self._downloading:
            self._selection.select_all()
            self.grid.set_all_selected(True)
            self._update_controls()

    def clear_selection(self) -> None:
        if self._post and not self._downloading:
            self._selection.clear()
            self.grid.set_all_selected(False)
            self._update_controls()

    # ------------------------------------------------------------ pastas
    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Escolha onde salvar as imagens", str(self._session_folder))
        if folder:
            self._session_folder = Path(folder)
            self._update_folder_label()

    def _update_folder_label(self) -> None:
        text = str(self._session_folder)
        fm = self.folder_label.fontMetrics()
        width = max(80, self.folder_label.width())
        self.folder_label.setText(fm.elidedText(text, Qt.TextElideMode.ElideMiddle, width))
        self.folder_label.setToolTip(text)

    def _open_folder(self, folder: Path) -> None:
        if folder.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    # ------------------------------------------------------------ download
    def start_download(self) -> None:
        if not self._post or self._downloading or self._analyzing or self._selection.none_selected:
            return
        folder = self._session_folder
        if self.settings.ask_folder_each_time:
            chosen = QFileDialog.getExistingDirectory(self, "Escolha onde salvar as imagens", str(folder))
            if not chosen:
                return
            folder = self._session_folder = Path(chosen)
            self._update_folder_label()
        selected = set(self._selection.selected())
        items = [i for i in self._post.images if i.position in selected]
        self._downloading = True
        self._cancel_event = threading.Event()
        self.banner.hide()
        self.progress.setValue(0)
        self.progress_label.setText("Preparando…")
        self.progress_box.show()
        self.cancel_btn.show()
        self._update_controls()
        post = self._post
        task = Task(self.service.download, post, items, folder, self.settings.policy, self._cancel_event,
                    with_progress=True)
        self._runner.start(
            task,
            on_success=lambda rep, p=post: self._on_download_done(p, rep),
            on_error=self._on_download_failed,
            on_progress=self._on_download_progress,
        )

    def cancel_download(self) -> None:
        if self._downloading and self._cancel_event:
            self._cancel_event.set()
            self.progress_label.setText("Cancelando…")
            self.cancel_btn.setEnabled(False)

    def _on_download_progress(self, prog: Progress) -> None:
        if not self._downloading:
            return
        self.progress.setValue(int(prog.fraction * 1000))
        if prog.file_index < prog.file_count:
            self.progress_label.setText(f"Baixando {prog.file_index + 1} de {prog.file_count}…")

    def _finish_download_ui(self) -> None:
        self._downloading = False
        self._cancel_event = None
        self.progress_box.hide()
        self.cancel_btn.hide()
        self.cancel_btn.setEnabled(True)
        self._update_controls()

    def _on_download_done(self, post: PostInfo, report: DownloadReport) -> None:
        self._finish_download_ui()
        saved, skipped, failed = len(report.saved), len(report.skipped), len(report.failed)
        self._last_folder = report.folder
        if self.settings.save_history and (saved or skipped):
            try:
                files = [r.path.name for r in report.saved + report.skipped if r.path]
                self.history.record(shortcode=post.shortcode, url=post.url, owner=post.owner,
                                    folder=report.folder, saved_files=files, failed_count=failed)
            except Exception:  # noqa: BLE001
                log.exception("Falha ao gravar histórico")

        parts = []
        if saved:
            parts.append(f"{saved} {'imagem salva' if saved == 1 else 'imagens salvas'}")
        if skipped:
            parts.append(f"{skipped} já {'existia' if skipped == 1 else 'existiam'} e {'foi pulada' if skipped == 1 else 'foram puladas'}")
        if failed:
            parts.append(f"{failed} com falha")
        summary = " · ".join(parts) if parts else "Nenhum arquivo salvo"
        detail = ""
        if failed:
            reasons = list(dict.fromkeys(r.error for r in report.failed if r.error))
            detail = " ".join(reasons[:2])
        if report.cancelled:
            kind, title = "warning", "Download cancelado"
            detail = (summary + ". " + detail).strip()
        elif failed and not saved and not skipped:
            kind, title = "error", "Não foi possível salvar as imagens"
        elif failed:
            kind, title = "warning", summary
        else:
            kind, title = "success", "Download concluído"
            detail = f"{summary} em {report.folder}"
        has_files = bool(saved or skipped)
        self.banner.show_message(kind, title, detail,
                                 action="Abrir pasta" if has_files else None, action_icon="folder")
        if has_files and self.settings.open_folder_after_download and not report.cancelled:
            self._open_folder(report.folder)

    def _on_download_failed(self, exc: PixoraError) -> None:
        self._finish_download_ui()
        self._last_folder = None
        self.banner.show_message("error", exc.title, exc.user_message)

    def _on_banner_action(self) -> None:
        if self._last_folder:
            self._open_folder(self._last_folder)

    # ----------------------------------------------------- estado/controles
    def _update_controls(self) -> None:
        busy = self._analyzing or self._downloading
        self.url_input.setEnabled(not self._downloading)
        self.paste_btn.setEnabled(not busy)
        self.analyze_btn.setEnabled(not busy)
        self.analyze_btn.setText("Analisando…" if self._analyzing else "Analisar")
        self.change_folder_btn.setEnabled(not self._downloading)
        has_post = self._post is not None and not self._analyzing
        for b in (self.select_all_btn, self.clear_sel_btn):
            b.setEnabled(has_post and not self._downloading)
        if has_post:
            self.select_all_btn.setEnabled(not self._selection.all_selected and not self._downloading)
            self.clear_sel_btn.setEnabled(not self._selection.none_selected and not self._downloading)
            self.counter.setText(self._selection.summary())
            self.grid.setEnabled(not self._downloading)
        self._update_footer()

    def _update_footer(self) -> None:
        n = self._selection.count if self._post else 0
        if self._downloading:
            text = "Baixando…"
        elif not self._post or self._analyzing:
            text = "Baixar"
        elif self._post.kind is PostKind.SINGLE:
            text = "Baixar imagem"
        elif self._selection.all_selected:
            text = f"Baixar todas ({n})"
        else:
            text = f"Baixar selecionadas ({n})"
        self.download_btn.setText(text)
        self.download_btn.setEnabled(
            self._post is not None and n > 0 and not self._downloading and not self._analyzing
        )
        self._update_folder_label()

    # ----------------------------------------------------------- diálogos
    def open_settings(self) -> None:
        if self._downloading:
            return
        dlg = SettingsDialog(self.settings, self.log_path, self)
        if dlg.exec():
            old_theme = self.settings.theme
            old_default = self.settings.download_dir
            self.settings = dlg.result_settings()
            self.settings_store.save(self.settings)
            if self.settings.download_dir != old_default:
                self._session_folder = Path(self.settings.download_dir)
            if self.settings.theme != old_theme:
                app = QApplication.instance()
                theme.apply_theme(app, self.settings.theme)  # type: ignore[arg-type]
                icons.pixmap.cache_clear()
                icons.icon.cache_clear()
                self._restyle_icons()
            self._update_footer()

    def open_history(self) -> None:
        HistoryDialog(self.history, self).exec()

    def about_text(self) -> str:
        return f"{__app_name__} {__version__}"
