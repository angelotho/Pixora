"""Componentes visuais reutilizáveis."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from pixora.ui import icons, theme


def make_button(text: str = "", *, variant: str | None = None, icon_name: str | None = None,
                icon_color: str | None = None, tooltip: str | None = None,
                parent: QWidget | None = None) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if variant:
        btn.setProperty("variant", variant)
    if icon_name:
        set_button_icon(btn, icon_name, icon_color)
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


def set_button_icon(btn: QPushButton, name: str, color: str | None = None, size: int = 18) -> None:
    t = theme.current()
    variant = btn.property("variant")
    if color is None:
        color = t.on_accent if variant == "primary" else t.text
    btn.setIcon(icons.icon(name, color, size, disabled_color=t.text_faint))
    btn.setIconSize(QSize(size, size))
    btn.setProperty("iconName", name)


def label(text: str = "", role: str | None = None, *, wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    if role:
        lbl.setProperty("role", role)
    lbl.setWordWrap(wrap)
    return lbl


def icon_label(name: str, color: str, size: int = 18) -> QLabel:
    lbl = QLabel()
    lbl.setPixmap(icons.pixmap(name, color, size))
    lbl.setFixedSize(size, size)
    lbl.setProperty("iconName", name)
    return lbl


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class Spinner(QWidget):
    """Indicador de atividade animado (arco giratório)."""

    def __init__(self, size: int = 40, line: float = 3.5, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle = 0
        self._line = line
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._timer.start()
        self.show()

    def stop(self) -> None:
        self._timer.stop()

    def _tick(self) -> None:
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        t = theme.current()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self._line, self._line, self.width() - 2 * self._line, self.height() - 2 * self._line)
        pen = QPen(theme.qcolor(t.surface3), self._line)
        p.setPen(pen)
        p.drawEllipse(r)
        pen.setColor(theme.qcolor(t.accent))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(r, int(-self._angle * 16), int(100 * 16))
        p.end()


class Banner(QFrame):
    """Mensagem em linha (sucesso, aviso, erro ou informação) com ação opcional."""

    action_clicked = Signal()
    closed = Signal()

    _ICONS = {"success": "check-circle", "error": "alert", "warning": "alert", "info": "info"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Banner")
        self._kind = "info"
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 8, 10)
        lay.setSpacing(12)
        self._icon = QLabel()
        self._icon.setFixedSize(20, 20)
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._title = label("", "heading")
        self._text = label("", "muted", wrap=True)
        text_col.addWidget(self._title)
        text_col.addWidget(self._text)
        self._action = make_button("", variant="small")
        self._action.clicked.connect(self.action_clicked)
        self._close = make_button("", variant="icon", icon_name="x", tooltip="Fechar")
        self._close.clicked.connect(self._on_close)
        lay.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(text_col, 1)
        lay.addWidget(self._action, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._close, 0, Qt.AlignmentFlag.AlignVCenter)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.hide()

    def show_message(self, kind: str, title: str, text: str = "", action: str | None = None,
                     action_icon: str | None = None) -> None:
        self._kind = kind
        self._title.setText(title)
        self._text.setText(text)
        self._text.setVisible(bool(text))
        self._action.setVisible(bool(action))
        if action:
            self._action.setText(action)
            if action_icon:
                set_button_icon(self._action, action_icon, size=16)
        self.restyle()
        self.show()

    def restyle(self) -> None:
        t = theme.current()
        color = {"success": t.success, "error": t.danger, "warning": t.warning}.get(self._kind, t.accent)
        soft = {"success": t.success_soft, "error": t.danger_soft, "warning": t.warning_soft}.get(
            self._kind, t.accent_soft)
        self.setStyleSheet(
            f"#Banner {{ background: {soft}; border: 1px solid {color}; border-radius: 12px; }}"
        )
        self._icon.setPixmap(icons.pixmap(self._ICONS.get(self._kind, "info"), color, 20))
        set_button_icon(self._close, "x", t.text_muted, 16)
        icon_name = self._action.property("iconName")
        if icon_name:
            set_button_icon(self._action, icon_name, size=16)

    def _on_close(self) -> None:
        self.hide()
        self.closed.emit()


class StateView(QWidget):
    """Tela central para estados vazio, carregando e erro."""

    action_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch(1)
        self._badge = QLabel()
        self._badge.setFixedSize(72, 72)
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner = Spinner(48, 4)
        self.spinner.hide()
        self._title = label("", "title")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text = label("", "muted", wrap=True)
        self._text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text.setFixedWidth(480)
        self._title.setWordWrap(True)
        self._title.setFixedWidth(480)
        self._button = make_button("", variant="secondary")
        self._button.clicked.connect(self.action_clicked)
        self._button.hide()
        for w in (self._badge, self.spinner):
            outer.addWidget(w, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addSpacing(14)
        outer.addWidget(self._title, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addSpacing(4)
        outer.addWidget(self._text, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addSpacing(16)
        outer.addWidget(self._button, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)
        self._icon_name = "images"
        self._tone = "accent"

    def set_state(self, *, icon_name: str | None, title: str, text: str, tone: str = "accent",
                  loading: bool = False, action: str | None = None, action_icon: str | None = None) -> None:
        self._icon_name = icon_name or "images"
        self._tone = tone
        self._title.setText(title)
        self._text.setText(text)
        self._text.setVisible(bool(text))
        # Rótulos com quebra de linha alinhados no layout não recalculam a altura sozinhos.
        for lbl in (self._title, self._text):
            lbl.setFixedHeight(lbl.heightForWidth(lbl.width()) if lbl.text() else 0)
        if loading:
            self._badge.hide()
            self.spinner.start()
        else:
            self.spinner.stop()
            self.spinner.hide()
            self._badge.show()
        self._button.setVisible(bool(action))
        if action:
            self._button.setText(action)
            if action_icon:
                set_button_icon(self._button, action_icon)
        self.restyle()

    def restyle(self) -> None:
        t = theme.current()
        color = {"danger": t.danger, "warning": t.warning, "muted": t.text_muted}.get(self._tone, t.accent)
        soft = {"danger": t.danger_soft, "warning": t.warning_soft, "muted": t.surface2}.get(
            self._tone, t.accent_soft)
        self._badge.setStyleSheet(f"background: {soft}; border-radius: 36px;")
        self._badge.setPixmap(icons.pixmap(self._icon_name, color, 32))
        icon_name = self._button.property("iconName")
        if icon_name:
            set_button_icon(self._button, icon_name)
