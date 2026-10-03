"""
Leçon 1 — La structure de marché.

C'est le principe le plus important et le plus souvent mal compris. Le prix ne
bouge pas au hasard : il laisse une suite de sommets (highs) et de creux (lows).
Lire la suite de ces pivots donne la structure, et la structure donne le biais.

Trois cas, et seulement trois :
  * HH + HL  → tendance haussière (Higher High, Higher Low)
  * LH + LL  → tendance baissière (Lower High, Lower Low)
  * mélangé  → range / consolidation

Règle qui en découle : on cherche des achats dans un uptrend, des ventes dans
un downtrend, et dans un range on ne fait rien tant que la structure n'est pas
tranchée.
"""
from __future__ import annotations

from core.model import Arrow, Level, Marker, Path, Scene, Zone, build

# --------------------------------------------------------------------------- #
# Séries de clôtures (synthétiques, conçues pour être lisibles)
# --------------------------------------------------------------------------- #

# Uptrend propre : sommets et creux qui montent, jamais l'inverse.
UP_CLOSES = [
    1.08500, 1.08540, 1.08510, 1.08620, 1.08600, 1.08700, 1.08660,
    1.08780, 1.08740, 1.08860, 1.08820, 1.08920, 1.08880, 1.08980,
]

# Downtrend : sommets et creux qui descendent.
DOWN_CLOSES = [
    1.09200, 1.09150, 1.09080, 1.09100, 1.09020, 1.08950, 1.08980,
    1.08900, 1.08840, 1.08860, 1.08780, 1.08720, 1.08660, 1.08600,
]

# Range : le prix rebondit toujours entre les mêmes deux bornes.
RANGE_CLOSES = [
    1.08500, 1.08620, 1.08700, 1.08600, 1.08520, 1.08450, 1.08500,
    1.08600, 1.08680, 1.08600, 1.08520, 1.08460, 1.08500, 1.08560,
]


def _swings(points, label, kind, step=1):
    """Ligne brisée reliant les pivots, pour illustrer HH / HL / LH / LL."""
    return Path(points=points, label=label, kind=kind, step=step, dots=True, dashed=True, width=1.6)


# --------------------------------------------------------------------------- #
# Leçons
# --------------------------------------------------------------------------- #


def uptrend() -> Scene:
    scene = Scene(
        id="structure-uptrend",
        title="Tendance haussière : HH + HL",
        principle=(
            "Des sommets qui montent et des creux qui montent. "
            "Le prix achète plus haut à chaque rebond : on cherche des achats."
        ),
        candles=build(1.08500, UP_CLOSES, wick=0.00035),
        takeaway=(
            "Le premier signe de retournement, c'est un creux plus bas (Lower Low) : "
            "la structure se casse. Tant qu'elle tient, on ne s'oppose pas au mouvement."
        ),
    )
    scene.add(
        # étape 1 : un premier pivot isolé, pour montrer ce qu'est un sommet
        Marker(index=4, price=1.08620, text="sommet", kind="neutral", step=1, dy=-22, dx=-14),
        Marker(index=2, price=1.08510, text="creux", kind="neutral", step=1, dy=24, dx=-14),
        # étape 2 : on relie les pivots et on nomme la structure
        _swings([(4, 1.08620), (7, 1.08780), (10, 1.08920), (12, 1.08980)], "HH", "good", step=2),
        _swings([(2, 1.08510), (6, 1.08660), (9, 1.08820), (13, 1.08880)], "HL", "good", step=2),
        # étape 3 : le biais qui en découle
        Marker(index=7, price=1.08780, text="bias haussier", kind="good", step=3, dy=-22, dx=-30),
    )
    scene.at(
        ("1. Repérer les pivots",
         "Un sommet est une bougie qui dépasse ses voisines, un creux le contraire. "
         "On les relie de gauche à droite : c'est la structure."),
        ("2. Lire la suite",
         "Les sommets montent (HH : Higher High) et les creux montent aussi (HL : Higher Low). "
         "Les deux conditions réunies valent tendance haussière."),
        ("3. En déduire le biais",
         "Dans un uptrend on cherche des achats sur les replis. La question n'est plus "
         "« est-ce que ça monte ? » mais « où est-ce que ça achète ? »"),
    )
    return scene


def downtrend() -> Scene:
    scene = Scene(
        id="structure-downtrend",
        title="Tendance baissière : LH + LL",
        principle=(
            "Des sommets qui descendent et des creux qui descendent. "
            "Le prix vend plus bas à chaque rebond : on cherche des ventes."
        ),
        candles=build(1.09200, DOWN_CLOSES, wick=0.00035),
        takeaway=(
            "En pratique on n'attend pas la confirmation complète pour vendre : "
            "le premier sommet plus bas suffit souvent, car le biais est déjà clair."
        ),
    )
    scene.add(
        Marker(index=1, price=1.09150, text="sommet", kind="neutral", step=1, dy=-22, dx=-14),
        Marker(index=5, price=1.08950, text="creux", kind="neutral", step=1, dy=24, dx=-14),
        _swings([(1, 1.09150), (4, 1.09100), (9, 1.08860), (11, 1.08720)], "LH", "bad", step=2),
        _swings([(5, 1.08950), (8, 1.08840), (12, 1.08660), (13, 1.08600)], "LL", "bad", step=2),
        Marker(index=9, price=1.08860, text="bias baissier", kind="bad", step=3, dy=-22, dx=-30),
    )
    scene.at(
        ("1. Repérer les pivots",
         "Même méthode que pour l'uptrend : sommet quand une bougie dépasse ses voisines, "
         "creux quand elle est dépassée."),
        ("2. Lire la suite",
         "Cette fois les sommets descendent (LH : Lower High) et les creux descendent "
         "(LL : Lower Low). Tendance baissière confirmée."),
        ("3. En déduire le biais",
         "On ne cherche que des ventes, sur les rebonds. Acheter un repli dans un downtrend, "
         "c'est construire une position contre la structure."),
    )
    return scene


def ranging() -> Scene:
    scene = Scene(
        id="structure-range",
        title="Range : aucune direction",
        principle=(
            "Les sommets ne montent pas et les creux ne descendent pas : "
            "le prix tourne entre deux bornes. La structure ne donne aucun biais."
        ),
        candles=build(1.08500, RANGE_CLOSES, wick=0.00035),
        takeaway=(
            "Un range n'est pas un marché mort, c'est un marché sans direction. "
            "La seule décision valable au milieu du range est de ne rien faire."
        ),
    )
    scene.add(
        # étape 1 : on repère les deux bornes par leurs rebonds répétés
        Marker(index=2, price=1.08700, text="rebonds répétés", kind="resistance", step=1, dy=-22, dx=-24),
        Marker(index=5, price=1.08450, text="rebonds répétés", kind="support", step=1, dy=24, dx=-24),
        # étape 2 : les bornes explicites, et le constat qu'aucune structure n'existe
        Level(price=1.08700, label="Résistance", kind="resistance", step=2, tag_dy=20),
        Level(price=1.08450, label="Support", kind="support", step=2, tag_dy=-20),
        # étape 3 : le milieu du range, où il ne se passe rien
        Zone(low=1.08530, high=1.08640, label="zone morte", kind="warn",
             start=0, end=13, fill_alpha=32, step=3),
        Marker(index=6, price=1.08590, text="rien à faire", kind="warn", step=3, dy=-4),
    )
    scene.at(
        ("1. Repérer les bornes",
         "Le prix rebondit toujours au même endroit en haut et en bas. "
         "Ce sont les deux seules informations utiles du range."),
        ("2. Constater l'absence de structure",
         "Ni HH/LH sur les sommets, ni HL/LL sur les creux. Aucun biais : "
         "le marché est en équilibre."),
        ("3. La règle qui compte",
         "On n'achète jamais au milieu d'un range et on n'y vend jamais. "
         "On attend la cassure, ou on trade les bornes après un rejet."),
    )
    return scene


def failure() -> Scene:
    """Le cas le plus important : la structure se casse avant de revenir."""
    scene = Scene(
        id="structure-casse",
        title="La structure se casse : le signal le plus fiable",
        principle=(
            "Un uptrend s'arrête quand un creux passe SOUS le creux précédent. "
            "Ce Lower Low est le premier signe fiable de retournement, avant tout indicateur."
        ),
        candles=build(1.08500, [
            1.08540, 1.08620, 1.08600, 1.08700, 1.08660, 1.08780, 1.08740,
            1.08860, 1.08820, 1.08920, 1.08880, 1.08600, 1.08520, 1.08620,
        ], wick=0.00035),
        takeaway=(
            "Tant que la structure tient, on suit le mouvement. Dès qu'elle casse, "
            "on attend la reprise avant de choisir un nouveau sens."
        ),
    )
    scene.add(
        _swings([(4, 1.08620), (7, 1.08780), (10, 1.08920)], "HH", "good"),
        _swings([(2, 1.08510), (6, 1.08660), (9, 1.08820)], "HL", "good"),
        Arrow(x1=10, p1=1.08900, x2=12, p2=1.08560,
              label="cassure", kind="bad", step=2, width=2.0),
        Marker(index=12, price=1.08520, text="Lower Low", kind="bad", step=2, dy=30, dx=-46),
        # étape 3 : la conduite à tenir une fois la structure cassée
        Level(price=1.08920, label="on n'achète plus ici", kind="warn", start=0, end=11, step=3, tag_dy=18),
        Marker(index=13, price=1.08620, text="attendre la reprise", kind="warn", step=3, dy=-22, dx=-24),
    )
    scene.at(
        ("1. La structure est saine",
         "HH et HL : la tendance monte, on ne s'oppose pas au mouvement."),
        ("2. Le creux casse",
         "Le prix passe sous le creux précédent : c'est un Lower Low, la structure est "
         "invalidée. Ce n'est plus un pullback, c'est potentiellement une inversion."),
        ("3. Règle de conduite",
         "Structure cassée = on ne cherche plus d'achats. On attend soit un nouveau creux plus "
         "haut pour reprendre, soit un sommet plus bas pour vendre."),
    )
    return scene


def SCENES() -> list[Scene]:  # noqa: N802 (nom d'API du registre)
    return [uptrend(), downtrend(), ranging(), failure()]

