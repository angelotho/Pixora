"""Diálogo de preferências."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from pixora.core.filenames import ConflictPolicy
from pixora.storage.settings import Settings
from pixora.ui import theme
from pixora.ui.widgets.common import label, make_button


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, log_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.setModal(True)
        self.setMinimumWidth(560)
        self._settings = replace(settings)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(18)
        root.addWidget(label("Configurações", "title"))

        # Downloads
        root.addWidget(label("DOWNLOADS", "section"))
        card = self._card()
        lay = card.layout()
        lay.addWidget(label("Pasta padrão"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self._folder = QLabel(self._settings.download_dir)
        self._folder.setProperty("role", "muted")
        self._folder.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._folder.setWordWrap(True)
        choose = make_button("Escolher…", variant="small", icon_name="folder")
        choose.clicked.connect(self._choose_folder)
        row.addWidget(self._folder, 1)
        row.addWidget(choose)
        lay.addLayout(row)

        self._ask = QCheckBox("Perguntar onde salvar a cada download")
        self._ask.setChecked(self._settings.ask_folder_each_time)
        self._open_after = QCheckBox("Abrir a pasta automaticamente ao concluir")
        self._open_after.setChecked(self._settings.open_folder_after_download)
        lay.addWidget(self._ask)
        lay.addWidget(self._open_after)

        lay.addWidget(label("Quando um arquivo com o mesmo nome já existir"))
        self._policy = QComboBox()
        self._policy.addItem("Salvar uma cópia numerada — ex.: instagram_ABC_01 (2).jpg", ConflictPolicy.RENAME.value)
        self._policy.addItem("Pular e manter o arquivo existente", ConflictPolicy.SKIP.value)
        self._policy.setCurrentIndex(max(0, self._policy.findData(self._settings.conflict_policy)))
        lay.addWidget(self._policy)
        root.addWidget(card)

        # Aparência e comportamento
        root.addWidget(label("APARÊNCIA E COMPORTAMENTO", "section"))
        card2 = self._card()
        lay2 = card2.layout()
        theme_row = QHBoxLayout()
        theme_row.addWidget(label("Tema"), 1)
        self._theme = QComboBox()
        self._theme.addItem("Escuro", "dark")
        self._theme.addItem("Claro", "light")
        self._theme.setCurrentIndex(max(0, self._theme.findData(self._settings.theme)))
        self._theme.setMinimumWidth(180)
        theme_row.addWidget(self._theme)
        lay2.addLayout(theme_row)
        self._auto_paste = QCheckBox("Colar automaticamente links do Instagram copiados")
        self._auto_paste.setChecked(self._settings.auto_paste)
        self._history = QCheckBox("Registrar downloads no histórico local")
        self._history.setChecked(self._settings.save_history)
        lay2.addWidget(self._auto_paste)
        lay2.addWidget(self._history)
        root.addWidget(card2)

        privacy = label(
            "O Pixora funciona apenas localmente: não pede senhas, não usa sua conta do Instagram "
            f"e não envia dados de uso. Logs de diagnóstico ficam em: {log_path}",
            "faint", wrap=True,
        )
        privacy.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(privacy)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = make_button("Cancelar", variant="ghost")
        cancel.clicked.connect(self.reject)
        save = make_button("Salvar", variant="primary")
        save.setDefault(True)
        save.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

    def _card(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        return frame

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Pasta padrão de downloads", self._settings.download_dir)
        if folder:
            self._settings.download_dir = folder
            self._folder.setText(folder)

    def showEvent(self, event) -> None:  # noqa: N802
        theme.apply_window_frame(self)
        super().showEvent(event)

    def result_settings(self) -> Settings:
        s = self._settings
        s.ask_folder_each_time = self._ask.isChecked()
        s.open_folder_after_download = self._open_after.isChecked()
        s.conflict_policy = self._policy.currentData()
        s.theme = self._theme.currentData()
        s.auto_paste = self._auto_paste.isChecked()
        s.save_history = self._history.isChecked()
        return s
