"""
Canevas de rendu des scènes pédagogiques.

Responsabilités :
  * convertir l'espace (index de bougie, prix) en pixels ;
  * dessiner la grille, les bougies et les annotations ;
  * gérer la révélation progressive (`set_step`) : sans étape, tout est visible ;
    avec une étape active, seuls les éléments d'étape <= l'étape active sont
    tracés, et ceux de l'étape active sont mis en évidence.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from .model import Arrow, Level, Marker, Note, Path, Scene, VLine, Zone
from .theme import (
    BG,
    DOWN,
    DOWN_FILL,
    GRID,
    MUTED,
    UP,
    UP_FILL,
    alpha,
    color_of,
)

# marges du graphe : gauche = place pour l'axe des prix, bas = index des bougies
MARGIN_LEFT = 14
MARGIN_RIGHT = 96
MARGIN_TOP = 26
MARGIN_BOTTOM = 34

# Valeurs entières de QFont::Style / QFont::Weight : plus stables que les noms
# d'énumération, qui ont été renommés entre les versions de PySide6.
_FONT_NORMAL = 0
_FONT_ITALIC = 1
_FONT_WEIGHT_NORMAL = 50
_FONT_WEIGHT_BOLD = 75


def _font(size: int, bold: bool = False, italic: bool = False) -> QFont:
    """Construit une QFont via le constructeur, qui accepte des entiers.

    On évite `setStyle` / `setWeight` : ces setters exigent l'énumération
    `QFont.Style`, dont les noms ont changé entre les versions de PySide6
    (`Italic` est devenu `StyleItalic`), alors que les valeurs entières
    n'ont pas bougé.
    """
    weight = _FONT_WEIGHT_BOLD if bold else _FONT_WEIGHT_NORMAL
    style = _FONT_ITALIC if italic else _FONT_NORMAL
    return QFont("Segoe UI", size, weight, style)


class ChartCanvas(QWidget):
    """Rendu d'une `Scene`."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(720, 460)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAutoFillBackground(False)

        self._scene: Scene | None = None
        self._step: int | None = None
        self._geom: dict | None = None

    # ------------------------------------------------------------------ API
    def set_scene(self, scene: Scene | None) -> None:
        self._scene = scene
        self._step = None
        self.update()

    def scene(self) -> Scene | None:
        return self._scene

    def set_step(self, step: int | None) -> None:
        """`None` = tout afficher ; sinon/index d'étape jusqu'à laquelle révéler."""
        self._step = step
        self.update()

    def step(self) -> int | None:
        return self._step

    # --------------------------------------------------------------- géométrie
    def _plot_rect(self) -> QRectF:
        return QRectF(
            MARGIN_LEFT,
            MARGIN_TOP,
            max(1.0, self.width() - MARGIN_LEFT - MARGIN_RIGHT),
            max(1.0, self.height() - MARGIN_TOP - MARGIN_BOTTOM),
        )

    def _bounds(self, scene: Scene | None) -> tuple[float, float]:
        """Bornes de prix incluant toutes les annotations, pour que rien ne sorte."""
        if scene is None:
            return 0.0, 1.0
        values: list[float] = []
        for c in scene.candles:
            values += [c.h, c.l]
        for a in scene.annotations:
            if isinstance(a, Level):
                values.append(a.price)
            elif isinstance(a, Zone):
                values += [a.low, a.high]
            elif isinstance(a, Marker):
                values.append(a.price)
            elif isinstance(a, Arrow):
                values += [a.p1, a.p2]
            elif isinstance(a, Path):
                values += [p[1] for p in a.points]
            elif isinstance(a, Note):
                values.append(a.price)
        if not values:
            return 0.0, 1.0
        lo, hi = min(values), max(values)
        if hi - lo < 1e-9:
            lo -= 5e-4
            hi += 5e-4
        return lo, hi

    def _layout(self) -> dict:
        """Table de correspondance index/prix -> pixels.

        Renvoie des bornes par défaut si aucune scène n'est chargée, pour que
        l'appel ne plante jamais (utile aux tests comme à l'initialisation).
        """
        rect = self._plot_rect()
        n = max(1, len(self._scene.candles)) if self._scene else 1
        lo, hi = self._bounds(self._scene) if self._scene else (0.0, 1.0)
        pad = (hi - lo) * 0.09
        lo, hi = lo - pad, hi + pad

        cw = rect.width() / n

        def x_of(index: float) -> float:
            return rect.left() + (index + 0.5) * cw

        def y_of(price: float) -> float:
            return rect.bottom() - (price - lo) / (hi - lo) * rect.height()

        def price_of(y: float) -> float:
            return lo + (rect.bottom() - y) / rect.height() * (hi - lo)

        return {
            "rect": rect,
            "n": n,
            "cw": cw,
            "lo": lo,
            "hi": hi,
            "x": x_of,
            "y": y_of,
            "price": price_of,
        }

    # ------------------------------------------------------------------ filtres
    def _visible(self, item) -> bool:
        """Un élément est visible si son étape est <= l'étape active."""
        if self._step is None:
            return True
        st = getattr(item, "step", None)
        if st is None:
            return True  # annotations structurelles : toujours visibles
        return st <= self._step

    def _is_current(self, item) -> bool:
        if self._step is None:
            return False
        return getattr(item, "step", None) == self._step

    def _pen_for(self, item, base_width: float = 1.0, dashed: bool = False) -> QPen:
        c = color_of(getattr(item, "kind", "neutral"))
        w = float(getattr(item, "width", 1.0) or base_width)
        style = Qt.DashLine if dashed else Qt.SolidLine
        return QPen(c, w, style)

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event):  # noqa: N802 (API Qt)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), BG)

        scene = self._scene
        if scene is None or not scene.candles:
            p.setPen(MUTED)
            p.setFont(_font(11))
            p.drawText(self.rect(), Qt.AlignCenter, "Aucune leçon sélectionnée.")
            p.end()
            return

        g = self._layout()
        self._geom = g

        self._draw_grid(p, g, scene)
        for a in scene.annotations:
            if not self._visible(a):
                continue
            self._draw_annotation(p, a, g, scene)
        self._draw_candles(p, g, scene)
        self._draw_axis(p, g, scene)

        # cadre de mise en évidence de l'étape courante
        if self._step is not None:
            p.setPen(QPen(alpha(color_of("info"), 60), 1, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRect(g["rect"])

        p.end()

    # ------------------------------------------------------------------- grille
    def _draw_grid(self, p: QPainter, g: dict, scene: Scene) -> None:
        rect: QRectF = g["rect"]
        p.setPen(QPen(GRID, 1))
        steps = 8
        for k in range(steps + 1):
            y = int(rect.top() + rect.height() * k / steps)
            p.drawLine(int(rect.left()), y, int(rect.right()), y)

    # ----------------------------------------------------------------- bougies
    def _draw_candles(self, p: QPainter, g: dict, scene: Scene) -> None:
        x_of, y_of = g["x"], g["y"]
        cw = g["cw"]
        body = max(1.0, cw * 0.68)

        for i, c in enumerate(scene.candles):
            if not self._visible(c):
                continue
            edge = UP if c.bull else DOWN
            fill = UP_FILL if c.bull else DOWN_FILL
            x = x_of(i)

            # mèche
            p.setPen(QPen(edge, 1))
            p.drawLine(int(x), int(y_of(c.h)), int(x), int(y_of(c.l)))

            # corps
            y_top, y_bot = y_of(c.top), y_of(c.bottom)
            h = max(1.0, y_bot - y_top)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(edge, 1))
            p.drawRect(int(x - body / 2), int(y_top), int(body), int(h))

            # label de la bougie (pin bar, engulfing…)
            if c.label:
                self._tag(p, c.label, x, y_of(c.h) - 10, color_of("info"), bg=alpha(BG, 210))

    # -------------------------------------------------------------- annotations
    def _draw_annotation(self, p: QPainter, a, g: dict, scene: Scene) -> None:
        if isinstance(a, Level):
            self._draw_level(p, a, g, scene)
        elif isinstance(a, Zone):
            self._draw_zone(p, a, g, scene)
        elif isinstance(a, Marker):
            self._draw_marker(p, a, g, scene)
        elif isinstance(a, Arrow):
            self._draw_arrow(p, a, g, scene)
        elif isinstance(a, Path):
            self._draw_path(p, a, g, scene)
        elif isinstance(a, VLine):
            self._draw_vline(p, a, g, scene)
        elif isinstance(a, Note):
            self._draw_note(p, a, g, scene)

    def _draw_level(self, p: QPainter, a: Level, g: dict, scene: Scene) -> None:
        x_of, y_of = g["x"], g["y"]
        n = g["n"]
        x1 = x_of(max(-0.4, a.start))
        x2 = x_of(min(n - 0.6, a.end if a.end is not None else n - 1))
        y = y_of(a.price)
        color = color_of(a.kind)
        emph = self._is_current(a)
        if emph:
            color = QColor(color)
            color.setAlpha(255)

        pen = QPen(color, a.width + (0.6 if emph else 0.0))
        if a.dashed:
            pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.drawLine(int(x1), int(y), int(x2), int(y))

        if a.label and a.show_tag:
            self._tag(p, a.tag_text(scene.digits), x1 + 2 + a.tag_dx, y - 16 + a.tag_dy,
                      color, bg=alpha(BG, 220))

    def _draw_zone(self, p: QPainter, a: Zone, g: dict, scene: Scene) -> None:
        x_of, y_of = g["x"], g["y"]
        n = g["n"]
        x1 = x_of(max(-0.4, a.start))
        x2 = x_of(min(n - 0.6, a.end if a.end is not None else n - 1))
        y1, y2 = y_of(a.high), y_of(a.low)
        color = color_of(a.kind)
        rect = QRectF(x1, y1, max(1.0, x2 - x1), max(2.0, y2 - y1))

        p.setBrush(alpha(color, a.fill_alpha))
        if a.border:
            p.setPen(QPen(alpha(color, 200), 1))
        else:
            p.setPen(Qt.NoPen)
        p.drawRect(rect)

        if a.label:
            ly = y1 - 4 if a.tag_side == "top" else y2 + 14
            self._tag(p, a.label, x1 + 3, ly, color, bg=alpha(BG, 220))

    def _draw_marker(self, p: QPainter, a: Marker, g: dict, scene: Scene) -> None:
        x_of, y_of = g["x"], g["y"]
        color = color_of(a.kind)
        x = x_of(a.index) + a.dx
        y = y_of(a.price) + a.dy
        self._tag(p, a.text, x, y, color, bg=alpha(BG, 230), bold=True)

    def _draw_arrow(self, p: QPainter, a: Arrow, g: dict, scene: Scene) -> None:
        x_of, y_of = g["x"], g["y"]
        p1 = QPointF(x_of(a.x1), y_of(a.p1))
        p2 = QPointF(x_of(a.x2), y_of(a.p2))
        self._arrow(p, p1, p2, color_of(a.kind), a.width)

        if a.label:
            mid = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
            self._tag(p, a.label, mid.x(), mid.y() - 10, color_of(a.kind), bg=alpha(BG, 220))

    def _draw_path(self, p: QPainter, a: Path, g: dict, scene: Scene) -> None:
        x_of, y_of = g["x"], g["y"]
        if len(a.points) < 2:
            return
        color = color_of(a.kind)
        pen = QPen(color, a.width)
        if a.dashed:
            pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        pts = [QPointF(x_of(i), y_of(pr)) for i, pr in a.points]
        for a_pt, b_pt in zip(pts, pts[1:]):
            p.drawLine(a_pt, b_pt)

        if a.dots:
            p.setBrush(QBrush(color))
            p.setPen(QPen(BG, 1))
            r = 3.2
            for pt in pts:
                p.drawEllipse(pt, r, r)

        if a.label:
            self._tag(p, a.label, pts[0].x(), pts[0].y() - 10, color, bg=alpha(BG, 220))

    def _draw_vline(self, p: QPainter, a: VLine, g: dict, scene: Scene) -> None:
        x_of = g["x"]
        rect: QRectF = g["rect"]
        x = x_of(a.index)
        pen = QPen(alpha(color_of(a.kind), 150), 1)
        if a.dashed:
            pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
        if a.label:
            self._tag(p, a.label, x, rect.top() - 8, color_of(a.kind), bg=alpha(BG, 220))

    def _draw_note(self, p: QPainter, a: Note, g: dict, scene: Scene) -> None:
        x_of, y_of = g["x"], g["y"]
        color = color_of(a.kind)
        x = x_of(a.x)
        y = y_of(a.price)
        p.setFont(_font(9))
        fm = QFontMetrics(p.font())
        lines = a.text.split("\n")
        w = max(fm.horizontalAdvance(line) for line in lines) + 16
        h = len(lines) * fm.height() + 10
        if a.align == "right":
            x -= w
        elif a.align == "center":
            x -= w / 2
        rect = QRectF(x, y - h, w, h)
        p.setBrush(alpha(BG, 235))
        p.setPen(QPen(alpha(color, 160), 1))
        p.drawRoundedRect(rect, 5, 5)
        p.setPen(color)
        for i, line in enumerate(lines):
            p.drawText(QRectF(rect.left() + 8, rect.top() + 5 + i * fm.height(), rect.width(), fm.height()),
                       Qt.AlignLeft | Qt.AlignVCenter, line)

    # -------------------------------------------------------------------- axes
    def _draw_axis(self, p: QPainter, g: dict, scene: Scene) -> None:
        rect: QRectF = g["rect"]

        # prix, à droite
        steps = 6
        p.setPen(MUTED)
        for k in range(steps + 1):
            frac = k / steps
            price = g["hi"] - (g["hi"] - g["lo"]) * frac
            y = rect.top() + rect.height() * frac
            p.drawLine(int(rect.right()), int(y), int(rect.right() + 5), int(y))
            p.drawText(QRectF(rect.right() + 7, y - 8, MARGIN_RIGHT, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, f"{price:.{scene.digits}f}")

        # numéro de bougie, en bas
        if scene.show_index_axis:
            p.setPen(MUTED)
            n = g["n"]
            vstep = max(1, n // 10)
            for i in range(0, n, vstep):
                x = g["x"](i)
                p.drawLine(int(x), int(rect.bottom()), int(x), int(rect.bottom() + 4))
                p.drawText(QRectF(x - 14, rect.bottom() + 6, 28, 16),
                           Qt.AlignCenter, str(i + 1))
        # filigrane du principe
        p.setPen(alpha(MUTED, 60))
        p.setFont(_font(9, italic=True))
        p.drawText(QRectF(rect.left(), 6, rect.width(), 18), Qt.AlignLeft | Qt.AlignVCenter, scene.title)

    # ------------------------------------------------------------------ helpers
    def tag_rect(self, text: str, x: float, y: float, bold: bool = False) -> QRectF:
        """Rectangle qu'occupera `_tag` — partagé avec l'audit de mise en page."""
        f = _font(8, bold=bold)
        fm = QFontMetrics(f)
        w = fm.horizontalAdvance(text) + 8
        h = fm.height() + 2
        return QRectF(x, y - h / 2, w, h)

    def _tag(self, p: QPainter, text: str, x: float, y: float, color: QColor,
             bg: QColor | None = None, bold: bool = False) -> None:
        """Petite étiquette texte avec fond, centrée verticalement sur (x, y).

        Le x est ramené dans le cadre pour qu'aucune étiquette ne soit tronquée,
        quelle que soit la taille de la fenêtre.
        """
        p.setFont(_font(8, bold=bold))
        rect = self.tag_rect(text, x, y, bold)
        rect.moveLeft(self._clamp_tag(rect.left(), y, rect.width()))
        p.setBrush(QBrush(bg or alpha(BG, 220)))
        p.setPen(QPen(alpha(color, 140), 1))
        p.drawRoundedRect(rect, 3, 3)
        p.setPen(color)
        p.drawText(rect, Qt.AlignCenter, text)

    def _clamp_tag(self, x: float, y: float, width: float) -> float:
        """Ramené une étiquette dans le cadre du graphe.

        Une étiquette qui sortirait du cadre serait tronquée ou illisible ; on
        la décale plutôt que de la laisser disparaître. Le calcul est fait sur
        les mêmes marges que `_plot_rect`, donc l'audit et le rendu concordent.
        """
        rect = self._plot_rect()
        if x + width > rect.right():
            return rect.right() - width
        if x < rect.left():
            return rect.left()
        return x

    def _arrow(self, p: QPainter, p1: QPointF, p2: QPointF, color: QColor, width: float) -> None:
        """Trace une flèche de p1 vers p2 avec pointe triangulaire."""
        pen = QPen(color, width)
        p.setPen(pen)
        p.setBrush(QBrush(color))
        p.drawLine(p1, p2)

        dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
        length = max(1.0, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / length, dy / length
        size = 9.0
        # base de la pointe
        bx, by = p2.x() - ux * size, p2.y() - uy * size
        px, py = -uy, ux  # perpendiculaire
        head = QPolygonF([
            p2,
            QPointF(bx + px * size * 0.45, by + py * size * 0.45),
            QPointF(bx - px * size * 0.45, by - py * size * 0.45),
        ])
        p.setPen(Qt.NoPen)
        p.drawPolygon(head)
