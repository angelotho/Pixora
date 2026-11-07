"""Diálogo do histórico de downloads."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QMessageBox, QStackedWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from pixora.storage.history import HistoryEntry, HistoryStore
from pixora.ui import theme
from pixora.ui.widgets.common import StateView, label, make_button


class HistoryDialog(QDialog):
    def __init__(self, store: HistoryStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Histórico de downloads")
        self.resize(880, 520)
        self.setMinimumSize(620, 380)
        self._store = store
        self._entries: list[HistoryEntry] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)
        head = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(label("Histórico", "title"))
        self._subtitle = label("", "muted")
        title_col.addWidget(self._subtitle)
        head.addLayout(title_col, 1)
        self._clear = make_button("Limpar histórico", variant="danger", icon_name="trash",
                                  icon_color=theme.current().danger)
        self._clear.clicked.connect(self._clear_all)
        head.addWidget(self._clear, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(head)

        self._stack = QStackedWidget()
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Data", "Publicação", "Arquivos", "Pasta"])
        self._table.verticalHeader().hide()
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setWordWrap(False)
        self._table.verticalHeader().setDefaultSectionSize(40)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._table.itemSelectionChanged.connect(self._update_buttons)
        self._table.doubleClicked.connect(self._open_folder)
        self._empty = StateView()
        self._empty.set_state(icon_name="history", title="Nenhum download ainda",
                              text="As publicações que você baixar aparecerão aqui.", tone="muted")
        self._stack.addWidget(self._table)
        self._stack.addWidget(self._empty)
        root.addWidget(self._stack, 1)

        foot = QHBoxLayout()
        self._open_post = make_button("Abrir publicação", variant="ghost", icon_name="external")
        self._open_post.clicked.connect(self._open_post_url)
        self._remove = make_button("Remover item", variant="ghost", icon_name="x")
        self._remove.clicked.connect(self._remove_selected)
        self._open_dir = make_button("Abrir pasta", variant="primary", icon_name="folder")
        self._open_dir.clicked.connect(self._open_folder)
        close = make_button("Fechar", variant="ghost")
        close.clicked.connect(self.accept)
        foot.addWidget(self._remove)
        foot.addStretch(1)
        foot.addWidget(close)
        foot.addWidget(self._open_post)
        foot.addWidget(self._open_dir)
        root.addLayout(foot)
        self._clear.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        close.setDefault(True)
        self.reload()
        (self._table if self._entries else close).setFocus()

    def showEvent(self, event) -> None:  # noqa: N802
        theme.apply_window_frame(self)
        super().showEvent(event)

    def reload(self) -> None:
        try:
            self._entries = self._store.list()
        except Exception:  # noqa: BLE001
            self._entries = []
            QMessageBox.warning(self, "Histórico", "Não foi possível ler o histórico local.")
        self._table.setRowCount(len(self._entries))
        for row, e in enumerate(self._entries):
            who = f"@{e.owner} · " if e.owner else ""
            files = f"{e.saved_count} salvo(s)" + (f", {e.failed_count} falha(s)" if e.failed_count else "")
            cells = [e.updated_at.strftime("%d/%m/%Y %H:%M"), f"{who}{e.shortcode}", files, e.folder]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                self._table.setItem(row, col, item)
        n = len(self._entries)
        self._subtitle.setText("Nenhum registro" if n == 0 else f"{n} publicação(ões) baixada(s)")
        self._stack.setCurrentIndex(0 if n else 1)
        self._clear.setEnabled(n > 0)
        self._update_buttons()

    def _selected(self) -> HistoryEntry | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        return self._entries[rows[0].row()]

    def _update_buttons(self) -> None:
        has = self._selected() is not None
        for b in (self._open_post, self._open_dir, self._remove):
            b.setEnabled(has)

    def _open_folder(self) -> None:
        e = self._selected()
        if not e:
            return
        if not Path(e.folder).is_dir():
            QMessageBox.information(self, "Pasta não encontrada",
                                    "Esta pasta não existe mais ou foi movida.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(e.folder))

    def _open_post_url(self) -> None:
        e = self._selected()
        if e:
            QDesktopServices.openUrl(QUrl(e.url))

    def _remove_selected(self) -> None:
        e = self._selected()
        if e:
            self._store.delete(e.id)
            self.reload()

    def _clear_all(self) -> None:
        answer = QMessageBox.question(
            self, "Limpar histórico",
            "Remover todos os registros do histórico?\nOs arquivos baixados não serão apagados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._store.clear()
            self.reload()
