"""Animação de abertura.

O símbolo do Pixora surge girando de leve, um brilho atravessa a forma e o nome
aparece logo abaixo; em seguida a tela some enquanto a janela principal surge.
Tudo é pintado a partir de uma única ``QVariantAnimation`` (0 → 1), e cada
elemento lê o seu trecho da linha do tempo. Assim a sequência fica em um só
lugar e não há widgets filhos para sincronizar.

Duração total ~1,3 s. Um clique ou Esc pula para o final. Se o Windows estiver
com as animações desligadas (acessibilidade), a abertura não é exibida.
"""

from __future__ import annotations

import logging
import math
import os
import sys

from PySide6.QtCore import (
    QEasingCurve, QPointF, QPropertyAnimation, QRect, QRectF, Qt, QVariantAnimation, Signal,
)
from PySide6.QtGui import (
    QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from pixora import __app_name__
from pixora.ui import icons, theme

log = logging.getLogger("pixora")

DURATION_MS = 1300
EXIT_MS = 240          # fade final, sobreposto ao surgimento da janela principal
LOGO_SIZE = 96
SIZE = (320, 280)

_OUT = QEasingCurve(QEasingCurve.Type.OutCubic)
_IN_OUT = QEasingCurve(QEasingCurve.Type.InOutCubic)
_POP = QEasingCurve(QEasingCurve.Type.OutBack)
_POP.setOvershoot(1.15)  # leve, só para dar vida; mais que isso parece "quicar"


def animations_enabled() -> bool:
    """Respeita a opção do Windows "Mostrar animações" e ``PIXORA_NO_SPLASH``."""
    if os.environ.get("PIXORA_NO_SPLASH"):
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            enabled = ctypes.c_bool(True)
            spi_getclientareaanimation = 0x1042
            if ctypes.windll.user32.SystemParametersInfoW(  # type: ignore[attr-defined]
                    spi_getclientareaanimation, 0, ctypes.byref(enabled), 0):
                return bool(enabled.value)
        except Exception:  # noqa: BLE001
            pass
    return True


class SplashScreen(QWidget):
    """Janela sem moldura e transparente que pinta a sequência de abertura."""

    reveal = Signal()     # hora de mostrar a janela principal (início do fade final)
    finished = Signal()   # animação concluída; a splash já foi escondida

    def __init__(self, duration_ms: int = DURATION_MS) -> None:
        super().__init__(None, Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(*SIZE)
        self.setAccessibleName(f"Abrindo o {__app_name__}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Clique para pular")

        self._t = theme.current()
        self._duration = max(1, duration_ms)
        self._progress = 0.0
        self._revealed = False
        self._logo = icons.logo_pixmap(LOGO_SIZE, self._t.brand)
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(self._duration)
        self._anim.valueChanged.connect(self._on_tick)
        self._anim.finished.connect(self._on_finished)

    # ------------------------------------------------------------- controle
    def start(self, screen=None) -> None:
        screen = screen or QGuiApplication.primaryScreen()
        if screen is not None:
            self.move(screen.availableGeometry().center() - self.rect().center())
        self.show()
        self.raise_()
        self._anim.start()

    def skip(self) -> None:
        """Vai direto para o fade final (ou não faz nada se já estiver nele)."""
        exit_at = self._duration - self._exit_ms()
        if self._anim.currentTime() < exit_at:
            self._anim.setCurrentTime(int(exit_at))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.skip()
        event.accept()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.skip()
        else:
            super().keyPressEvent(event)

    def _exit_ms(self) -> float:
        return EXIT_MS * self._duration / DURATION_MS

    def _on_tick(self, value) -> None:
        self._progress = float(value)
        if not self._revealed and self._ms() >= self._duration - self._exit_ms():
            self._revealed = True
            self.reveal.emit()
        self.update()

    def _on_finished(self) -> None:
        if not self._revealed:
            self._revealed = True
            self.reveal.emit()
        self.hide()
        self.finished.emit()

    # ---------------------------------------------------------- linha do tempo
    def _ms(self) -> float:
        return self._progress * self._duration

    def _seg(self, start: float, end: float, curve: QEasingCurve | None = None) -> float:
        """Progresso 0..1 do trecho [start, end] (em ms da duração padrão), já com easing."""
        k = self._duration / DURATION_MS
        x = (self._ms() - start * k) / max(1.0, (end - start) * k)
        x = min(1.0, max(0.0, x))
        return curve.valueForProgress(x) if curve else x

    # ----------------------------------------------------------------- pintura
    def paintEvent(self, event) -> None:  # noqa: N802
        t = self._t
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
                         | QPainter.RenderHint.TextAntialiasing)
        w, h = self.width(), self.height()
        exit_x = self._seg(DURATION_MS - EXIT_MS, DURATION_MS, _IN_OUT)

        # Cartão: aparece rápido e cresce 4%; no fim some e cresce um pouco mais.
        card_in = self._seg(0, 200, _OUT)
        scale = 0.96 + 0.04 * self._seg(0, 360, _OUT) + 0.02 * exit_x
        p.setOpacity(card_in * (1.0 - exit_x))
        p.translate(w / 2, h / 2)
        p.scale(scale, scale)
        p.translate(-w / 2, -h / 2)
        card = QRectF(8.5, 8.5, w - 17, h - 17)
        p.setPen(QPen(theme.qcolor(t.border), 1))
        p.setBrush(theme.qcolor(t.surface))
        p.drawRoundedRect(card, 22, 22)

        cx, cy = w / 2, h / 2 - 22
        brand = QColor(t.brand)

        # Halo da marca atrás do símbolo: acende e apaga.
        glow_x = self._seg(80, 1000)
        glow = math.sin(math.pi * glow_x)
        if glow > 0.001:
            radius = LOGO_SIZE * (0.55 + 0.45 * _OUT.valueForProgress(glow_x))
            g = QRadialGradient(QPointF(cx, cy), radius)
            c0 = QColor(brand)
            c0.setAlphaF(0.30 * glow)
            c1 = QColor(brand)
            c1.setAlphaF(0.0)
            g.setColorAt(0.0, c0)
            g.setColorAt(1.0, c1)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawEllipse(QPointF(cx, cy), radius, radius)

        # Símbolo: entra com fade, escala (com leve overshoot) e um giro de 10°.
        logo_a = self._seg(60, 320, _OUT)
        if logo_a > 0:
            pop = self._seg(60, 640, _POP)
            s = 0.70 + 0.30 * pop
            angle = -10.0 * (1.0 - self._seg(60, 640, _OUT))
            p.save()
            p.setOpacity(p.opacity() * logo_a)
            p.translate(cx, cy)
            p.rotate(angle)
            p.scale(s, s)
            p.drawPixmap(QRect(-LOGO_SIZE // 2, -LOGO_SIZE // 2, LOGO_SIZE, LOGO_SIZE),
                         self._shined_logo(self._seg(560, 1000, _IN_OUT)))
            p.restore()

        # Nome e subtítulo sobem 8 px enquanto aparecem.
        base = p.opacity()
        title_y = cy + LOGO_SIZE / 2 + 22
        for text, size, weight, color, start, dy in (
            (__app_name__, 19, QFont.Weight.Bold, t.text, 360, 0),
            ("Imagens de publicações do Instagram", 9, QFont.Weight.Normal, t.text_muted, 450, 30),
        ):
            a = self._seg(start, start + 320, _OUT)
            if a <= 0:
                continue
            f = QFont(theme.default_font())
            f.setPointSizeF(size)
            f.setWeight(weight)
            p.setFont(f)
            p.setOpacity(base * a)
            p.setPen(theme.qcolor(color))
            rect = QRectF(16, title_y + dy + 8 * (1 - a), w - 32, 30)
            p.drawText(rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, text)
        p.end()

    def _shined_logo(self, x: float) -> QPixmap:
        """O símbolo com uma faixa de luz diagonal recortada pela própria forma."""
        if x <= 0.0 or x >= 1.0:
            return self._logo
        pm = QPixmap(self._logo.size())
        pm.setDevicePixelRatio(self._logo.devicePixelRatio())
        pm.fill(Qt.GlobalColor.transparent)
        q = QPainter(pm)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        q.drawPixmap(0, 0, self._logo)
        q.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        size = float(LOGO_SIZE)
        pos = -0.6 * size + 2.2 * size * x
        band = QLinearGradient(QPointF(pos - 0.35 * size, pos - 0.35 * size),
                               QPointF(pos + 0.35 * size, pos + 0.35 * size))
        clear = QColor(255, 255, 255, 0)
        band.setColorAt(0.0, clear)
        band.setColorAt(0.5, QColor(255, 255, 255, 120))
        band.setColorAt(1.0, clear)
        path = QPainterPath()
        path.addRect(QRectF(0, 0, size, size))
        q.fillPath(path, band)
        q.end()
        return pm


def play_intro(window: QWidget, duration_ms: int = DURATION_MS) -> SplashScreen | None:
    """Mostra a abertura e depois ``window`` (com fade). Nunca impede a janela de aparecer."""
    if not animations_enabled():
        window.show()
        return None
    try:
        splash = SplashScreen(duration_ms)
        center = window.frameGeometry().center()
        screen = QGuiApplication.screenAt(center) or QGuiApplication.primaryScreen()

        fade = QPropertyAnimation(window, b"windowOpacity", window)
        fade.setDuration(max(1, round(splash._exit_ms())))
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        def reveal() -> None:
            window.setWindowOpacity(0.0)
            window.show()
            fade.start()

        def done() -> None:
            fade.stop()  # a janela nunca pode ficar semitransparente
            fade.deleteLater()
            window.setWindowOpacity(1.0)
            window.raise_()
            window.activateWindow()
            splash.deleteLater()

        splash.reveal.connect(reveal)
        splash.finished.connect(done)
        splash.start(screen)
        return splash
    except Exception:  # noqa: BLE001 — a abertura é enfeite; o app tem de abrir mesmo assim
        log.exception("Falha na animação de abertura; abrindo a janela diretamente")
        window.setWindowOpacity(1.0)
        window.show()
        return None
