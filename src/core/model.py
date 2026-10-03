"""
Modèle de scène pédagogique.

Une `Scene` décrit ce qu'il faut dessiner pour expliquer une notion de Price
Action : une série de bougies (synthétiques, construites pour être lisibles),
des annotations (niveaux, zones, flèches, markers) et des étapes de
progressive disclosure.

Tout est en espace « index de bougie » et « prix » : le canevas se charge de
la conversion en pixels. Aucun module de leçon ne manipule de coordonnées
d'écran.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

# --------------------------------------------------------------------------- #
# Données de prix
# --------------------------------------------------------------------------- #


@dataclass
class Candle:
    """Une bougie OHLC. `label` et `step` servent à la révélation progressive."""

    # noms o/h/l/c : convention OHLC du métier, on ne les change pas
    o: float  # noqa: E741
    h: float
    l: float  # noqa: E741
    c: float
    label: str | None = None
    step: int | None = None

    @property
    def bull(self) -> bool:
        return self.c >= self.o

    @property
    def top(self) -> float:
        return max(self.o, self.c)

    @property
    def bottom(self) -> float:
        return min(self.o, self.c)


def build(start: float, closes: Sequence[float], wick: float = 0.0004) -> list[Candle]:
    """Construit une série de bougies à partir d'une suite de clôtures.

    C'est la brique de base pour écrire une leçon : on décrit le mouvement
    qu'on veut montrer, pas des quadruplets OHLC à la main. L'ouverture vaut la
    clôture précédente, les mèches sont symétriques de `wick`.

        candles = build(1.0850, [1.0852, 1.0861, 1.0860, 1.0840])
    """
    out: list[Candle] = []
    prev = start
    for close in closes:
        out.append(Candle(o=prev, h=max(prev, close) + wick, l=min(prev, close) - wick, c=close))
        prev = close
    return out


def from_rows(rows: Iterable[Sequence]) -> list[Candle]:
    """Construit des bougies depuis des tuples explicites (O, H, L, C[, label][, step])."""
    out: list[Candle] = []
    for row in rows:
        o, h, low, c = row[0], row[1], row[2], row[3]
        label = row[4] if len(row) > 4 else None
        step = row[5] if len(row) > 5 else None
        out.append(Candle(o=o, h=h, l=low, c=c, label=label, step=step))
    return out


# --------------------------------------------------------------------------- #
# Annotations
# --------------------------------------------------------------------------- #


@dataclass
class Level:
    """Ligne horizontale (support, résistance, entrée, stop, cible…)."""

    price: float
    label: str = ""
    kind: str = "neutral"
    start: int = 0
    end: int | None = None
    step: int | None = None
    width: float = 1.0
    dashed: bool = True
    show_tag: bool = True
    tag_dx: float = 0.0
    tag_dy: float = 0.0

    def tag_text(self, digits: int) -> str:
        """Texte affiché sur la ligne — source de vérité pour le rendu ET l'audit."""
        price = f"{self.price:.{digits}f}"
        return f"{self.label} {price}" if self.label else price


@dataclass
class Zone:
    """Rectangle horizontal (order block, FVG, zone de range, zone d'intérêt)."""

    low: float
    high: float
    label: str = ""
    kind: str = "neutral"
    start: int = 0
    end: int | None = None
    step: int | None = None
    fill_alpha: int = 48
    border: bool = True
    tag_side: str = "top"  # "top" | "bottom"


@dataclass
class Marker:
    """Marqueur textuel ancré sur une bougie (achat, vente, attente, alerte)."""

    index: int
    price: float
    text: str
    kind: str = "neutral"
    step: int | None = None
    dy: float = 0.0
    dx: float = 0.0


@dataclass
class Arrow:
    """Flèche entre deux points (index, prix) — annoter un mouvement."""

    x1: float
    p1: float
    x2: float
    p2: float
    label: str = ""
    kind: str = "info"
    step: int | None = None
    width: float = 1.6


@dataclass
class Path:
    """Ligne brisée passant par des points (index, prix) — swing points, trajectoires."""

    points: list[tuple[float, float]]
    label: str = ""
    kind: str = "info"
    step: int | None = None
    dashed: bool = False
    dots: bool = False
    width: float = 1.4


@dataclass
class VLine:
    """Ligne verticale (séparation de phase, clôture de bougie, repère de temps)."""

    index: float
    label: str = ""
    kind: str = "neutral"
    step: int | None = None
    dashed: bool = True


@dataclass
class Note:
    """Bloc de texte libre positionné dans le graphe (avertissement, légende)."""

    x: float
    price: float
    text: str
    kind: str = "info"
    step: int | None = None
    width: float = 260.0
    align: str = "left"  # "left" | "center" | "right"


# --------------------------------------------------------------------------- #
# Scène
# --------------------------------------------------------------------------- #


@dataclass
class Step:
    """Une étape de révélation : un titre et une explication."""

    title: str
    text: str


@dataclass
class Scene:
    """Tout ce qu'il faut pour dessiner et expliquer une leçon."""

    id: str
    title: str
    principle: str
    candles: list[Candle] = field(default_factory=list)
    annotations: list = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    takeaway: str = ""
    digits: int = 5
    show_index_axis: bool = True

    # -- helpers de construction -----------------------------------------
    def add(self, *items) -> "Scene":
        """Ajoute des annotations (niveau, zone, marker…)."""
        self.annotations.extend(items)
        return self

    def at(self, *items) -> "Scene":
        """Ajoute des étapes.

        Accepte indifféremment des `Step` ou des couples `(titre, texte)` :
        `scene.at(("Titre", "Explication"))` est la forme courte, celle qu'on
        utilise dans les leçons.
        """
        for item in items:
            if isinstance(item, Step):
                self.steps.append(item)
            else:
                title, text = item
                self.steps.append(Step(title=title, text=text))
        return self

    def last_index(self) -> int:
        return max(0, len(self.candles) - 1)
