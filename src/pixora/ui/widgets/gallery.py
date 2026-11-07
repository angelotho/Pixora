"""Cartões de pré-visualização e grade responsiva de imagens."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor, QFont, QImage, QKeyEvent, QLinearGradient, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from pixora.core.models import ImageItem
from pixora.ui import icons, theme

CARD_RADIUS = 14.0
IMAGE_INSET = 6.0
MIN_CARD_WIDTH = 190
MAX_CARD_WIDTH = 300
GAP = 16
SINGLE_MAX_WIDTH = 560


class ImageCard(QWidget):
    toggled = Signal(int, bool)

    def __init__(self, item: ImageItem, total_positions: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item = item
        self._digits = max(2, len(str(total_positions)))
        self._image: QImage | None = None
        self._scaled: QPixmap | None = None
        self._scaled_key: tuple[int, int, float] | None = None
        self._failed = False
        self._selected = True
        self._hover = False
        self._pressed = False
        self.phase = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        dims = f" · {item.width} × {item.height}px" if item.width and item.height else ""
        self.setToolTip(f"Imagem {item.position:0{self._digits}d}{dims}\nClique para selecionar ou desmarcar")
        self.setAccessibleName(f"Imagem {item.position}")

    # --- estado ---------------------------------------------------------
    @property
    def loading(self) -> bool:
        return self._image is None and not self._failed

    def set_image(self, image: QImage) -> None:
        self._image = image
        self._scaled = None
        self.update()

    def set_failed(self) -> None:
        self._failed = True
        self.update()

    def set_selected(self, selected: bool) -> None:
        if self._selected != selected:
            self._selected = selected
            self.update()

    def is_selected(self) -> bool:
        return self._selected

    def _toggle(self) -> None:
        self._selected = not self._selected
        self.update()
        self.toggled.emit(self.item.position, self._selected)

    # --- eventos --------------------------------------------------------
    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._pressed:
            self._pressed = False
            if self.rect().contains(event.position().toPoint()):
                self._toggle()
            self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._toggle()
        else:
            super().keyPressEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().focusOutEvent(event)

    # --- pintura --------------------------------------------------------
    def _scaled_pixmap(self, target: QSize) -> QPixmap | None:
        if self._image is None:
            return None
        dpr = self.devicePixelRatioF()
        key = (target.width(), target.height(), dpr)
        if self._scaled is None or self._scaled_key != key:
            img = self._image.scaled(
                int(target.width() * dpr), int(target.height() * dpr),
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
            )
            pm = QPixmap.fromImage(img)
            pm.setDevicePixelRatio(dpr)
            self._scaled, self._scaled_key = pm, key
        return self._scaled

    def paintEvent(self, _event) -> None:  # noqa: N802
        t = theme.current()
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        outer = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        # Fundo e borda
        bg = theme.qcolor(t.surface3 if self._hover else t.surface2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(outer, CARD_RADIUS, CARD_RADIUS)

        # Área da imagem
        img_rect = outer.adjusted(IMAGE_INSET, IMAGE_INSET, -IMAGE_INSET, -IMAGE_INSET)
        clip = QPainterPath()
        clip.addRoundedRect(img_rect, CARD_RADIUS - 4, CARD_RADIUS - 4)
        p.save()
        p.setClipPath(clip)
        p.fillRect(img_rect, theme.qcolor(t.surface))
        pm = self._scaled_pixmap(img_rect.size().toSize())
        if pm is not None:
            w = pm.width() / pm.devicePixelRatio()
            h = pm.height() / pm.devicePixelRatio()
            x = img_rect.x() + (img_rect.width() - w) / 2
            y = img_rect.y() + (img_rect.height() - h) / 2
            p.drawPixmap(QPointF(x, y), pm)
            if not self._selected:
                p.fillRect(img_rect, QColor(0, 0, 0, 115 if t.dark else 80))
        elif self._failed:
            ic = icons.pixmap("image", t.text_faint, 30)
            p.drawPixmap(QPointF(img_rect.center().x() - 15, img_rect.center().y() - 26), ic)
            p.setPen(theme.qcolor(t.text_faint))
            f = QFont(self.font())
            f.setPointSizeF(9)
            p.setFont(f)
            p.drawText(img_rect.adjusted(8, 30, -8, 0), Qt.AlignmentFlag.AlignCenter, "Prévia indisponível")
        else:  # carregando: brilho deslizante
            grad = QLinearGradient(img_rect.left(), 0, img_rect.right(), 0)
            base = theme.qcolor(t.surface)
            shine = theme.qcolor(t.surface3)
            c = self.phase
            grad.setColorAt(0, base)
            grad.setColorAt(max(0.0, c - 0.25), base)
            grad.setColorAt(min(1.0, max(0.001, c)), shine)
            grad.setColorAt(min(1.0, c + 0.25), base)
            grad.setColorAt(1, base)
            p.fillRect(img_rect, grad)
        p.restore()

        # Borda / anel de seleção
        if self._selected:
            p.setPen(QPen(theme.qcolor(t.accent), 2.5))
        elif self.hasFocus() or self._hover:
            p.setPen(QPen(theme.qcolor(t.border_strong), 1.5))
        else:
            p.setPen(QPen(theme.qcolor(t.border), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(outer, CARD_RADIUS, CARD_RADIUS)
        if self.hasFocus():
            p.setPen(QPen(theme.qcolor(t.accent_hover), 1.5, Qt.PenStyle.DashLine))
            p.drawRoundedRect(outer.adjusted(3, 3, -3, -3), CARD_RADIUS - 2, CARD_RADIUS - 2)

        # Marcador de seleção (canto superior direito)
        d = 26.0
        cr = QRectF(img_rect.right() - d - 8, img_rect.top() + 8, d, d)
        if self._selected:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme.qcolor(t.accent))
            p.drawEllipse(cr)
            p.drawPixmap(cr.adjusted(5, 5, -5, -5).topLeft(), icons.pixmap("check", "#FFFFFF", 16, 3.0))
        else:
            p.setBrush(QColor(0, 0, 0, 90))
            p.setPen(QPen(QColor(255, 255, 255, 230), 2))
            p.drawEllipse(cr.adjusted(1, 1, -1, -1))

        # Posição (canto inferior esquerdo)
        self._pill(p, f"{self.item.position:0{self._digits}d}", img_rect, left=True)
        if self._hover and self.item.width and self.item.height:
            self._pill(p, f"{self.item.width}×{self.item.height}", img_rect, left=False)
        p.end()

    def _pill(self, p: QPainter, text: str, area: QRectF, *, left: bool) -> None:
        f = QFont(self.font())
        f.setPointSizeF(8.5)
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        fm = p.fontMetrics()
        w = fm.horizontalAdvance(text) + 16
        h = fm.height() + 6
        x = area.left() + 8 if left else area.right() - w - 8
        r = QRectF(x, area.bottom() - h - 8, w, h)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(10, 12, 16, 175))
        p.drawRoundedRect(r, h / 2, h / 2)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)


class ImageGrid(QWidget):
    """Grade que se adapta à largura disponível, preservando a ordem da publicação."""

    toggled = Signal(int, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cards: dict[int, ImageCard] = {}
        self._order: list[int] = []
        self._tile_aspect = 0.8
        self._viewport_height = 480
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._shimmer = QTimer(self)
        self._shimmer.setInterval(33)
        self._shimmer.timeout.connect(self._animate)
        self._phase = 0.0

    def clear(self) -> None:
        for card in self.cards.values():
            card.deleteLater()
        self.cards.clear()
        self._order.clear()
        self._shimmer.stop()
        self.setMinimumHeight(0)

    def set_items(self, items: tuple[ImageItem, ...]) -> None:
        self.clear()
        total = max((i.position for i in items), default=1)
        aspects = [i.aspect_ratio for i in items if i.width and i.height]
        # O Instagram usa proporções entre 4:5 e 1.91:1; mantemos a grade uniforme.
        self._tile_aspect = min(1.91, max(0.8, aspects[0] if aspects else 0.8))
        for item in items:
            card = ImageCard(item, total, self)
            card.toggled.connect(self.toggled)
            card.show()
            self.cards[item.position] = card
            self._order.append(item.position)
        self._shimmer.start()
        self._relayout()

    def set_thumbnail(self, position: int, image: QImage) -> None:
        card = self.cards.get(position)
        if card:
            card.set_image(image)
        self._maybe_stop_shimmer()

    def set_thumbnail_failed(self, position: int) -> None:
        card = self.cards.get(position)
        if card:
            card.set_failed()
        self._maybe_stop_shimmer()

    def set_all_selected(self, selected: bool) -> None:
        for card in self.cards.values():
            card.set_selected(selected)

    def set_viewport_height(self, h: int) -> None:
        if h != self._viewport_height:
            self._viewport_height = h
            self._relayout()

    def _maybe_stop_shimmer(self) -> None:
        if not any(c.loading for c in self.cards.values()):
            self._shimmer.stop()

    def _animate(self) -> None:
        self._phase = (self._phase + 0.025) % 1.5
        for c in self.cards.values():
            if c.loading:
                c.phase = self._phase - 0.25
                c.update()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        n = len(self._order)
        if n == 0:
            return
        width = max(1, self.width())
        if n == 1:
            max_h = max(260, self._viewport_height - 8)
            card_w = min(width, SINGLE_MAX_WIDTH, int(max_h * self._tile_aspect))
            card_h = int(card_w / self._tile_aspect)
            x = (width - card_w) // 2
            self.cards[self._order[0]].setGeometry(QRect(x, 0, card_w, card_h))
            self.setMinimumHeight(card_h)
            return
        cols = max(1, min(n, (width + GAP) // (MIN_CARD_WIDTH + GAP)))
        if n <= 3:
            cols = min(cols, n)
        card_w = (width - GAP * (cols - 1)) // cols
        card_w = min(card_w, MAX_CARD_WIDTH)
        card_h = int(card_w / self._tile_aspect)
        used = cols * card_w + (cols - 1) * GAP
        x0 = (width - used) // 2
        for idx, pos in enumerate(self._order):
            r, c = divmod(idx, cols)
            self.cards[pos].setGeometry(QRect(x0 + c * (card_w + GAP), r * (card_h + GAP), card_w, card_h))
        rows = math.ceil(n / cols)
        self.setMinimumHeight(rows * card_h + (rows - 1) * GAP)
