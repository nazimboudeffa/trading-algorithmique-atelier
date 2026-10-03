"""
Leçon 6 — Les figures de bougies qui comptent.

Toutes les figures ne se valent pas. En Price Action on n'en utilise que
quelques-unes, et surtout on ne les utilise jamais seules : une figure n'a de
valeur qu'au bon endroit (sur un niveau, une zone ou une structure).

Les trois figures à retenir :
  * le pin bar, qui signale un rejet ;
  * l'engulfing, qui signale une reprise de contrôle ;
  * l'inside bar, qui signale une compression avant un mouvement.
"""
from __future__ import annotations

from core.model import Arrow, Level, Marker, Scene, Zone, from_rows

# Pin bar haussier : longue mèche basse, petit corps, sur un support.
PINBAR_BULL = [
    (1.08500, 1.08540, 1.08480, 1.08520, None, 1),
    (1.08520, 1.08550, 1.08500, 1.08530, None, 1),
    (1.08530, 1.08560, 1.08510, 1.08540, None, 1),
    (1.08540, 1.08550, 1.08420, 1.08440, "pin bar", 2),   # rejet du support
    (1.08440, 1.08560, 1.08430, 1.08550, None, 2),
    (1.08550, 1.08640, 1.08540, 1.08630, None, 2),
]

# Engulfing haussier : la bougie verte recouvre entièrement la rouge.
ENGULF_BULL = [
    (1.08500, 1.08550, 1.08430, 1.08440, None, 1),
    (1.08440, 1.08490, 1.08400, 1.08410, "rouge", 2),
    (1.08410, 1.08530, 1.08400, 1.08520, "engulfing", 2),   # englobe la précédente
    (1.08520, 1.08600, 1.08510, 1.08590, None, 2),
]

# Inside bar : compression après une impulsion.
INSIDE = [
    (1.08500, 1.08620, 1.08480, 1.08610, None, 1),
    (1.08610, 1.08660, 1.08590, 1.08650, "mère", 2),
    (1.08650, 1.08652, 1.08600, 1.08620, "inside", 2),
    (1.08620, 1.08625, 1.08610, 1.08615, "inside", 2),
    (1.08615, 1.08760, 1.08610, 1.08750, None, 3),   # explosion
]


def pinbar() -> Scene:
    scene = Scene(
        id="cd-pinbar",
        title="Le pin bar : le rejet d'une zone",
        principle=(
            "Une longue mèche et un petit corps disent que le prix a été repoussé. "
            "La direction de la mèche indique qui a perdu le contrôle."
        ),
        candles=from_rows(PINBAR_BULL),
        takeaway=(
            "Un pin bar n'est un signal que s'il apparaît sur un niveau ou dans une "
            "zone. Au milieu de nulle part, une longue mèche n'est que du bruit."
        ),
    )
    scene.add(
        Level(price=1.08520, label="support", kind="support", start=0, end=4, step=1),
        Zone(low=1.08480, high=1.08520, label="zone touchée", kind="support",
             start=0, end=4, fill_alpha=40, step=1, tag_side="bottom"),
        Marker(index=3, price=1.08420, text="mèche basse : les vendeurs ont été repoussés",
               kind="good", step=2, dy=26, dx=-64),
        # étape 3 : on n'entre pas sur la bougie du rejet
        Marker(index=4, price=1.08550, text="entrée ici, sur la suivante", kind="good", step=3, dy=-22, dx=-40),
    )
    scene.at(
        ("1. Le prix atteint une zone",
         "Le support est testé. Le contexte compte autant que la figure : "
         "sans zone, pas de pin bar exploitable."),
        ("2. La mèche raconte l'histoire",
         "Corps petit en haut, longue mèche en bas : le prix a baissé, puis a été "
         "repoussé. Les vendeurs ont dominé, puis ont été repris."),
        ("3. Confirmation attendue",
         "Le pin bar n'est qu'un appel à l'attention. On entre sur la bougie suivante "
         "si elle va dans le sens du rejet — jamais sur la bougie du rejet elle-même."),
    )
    return scene


def engulfing() -> Scene:
    scene = Scene(
        id="cd-engulfing",
        title="L'engulfing : la reprise de contrôle",
        principle=(
            "Quand une bougie recouvre entièrement le corps de la précédente, "
            "ceux qui dominaient viennent de perdre la main."
        ),
        candles=from_rows(ENGULF_BULL),
        takeaway=(
            "L'engulfing est plus fiable quand il survient sur un niveau important. "
            "Un engulfing au milieu d'un range ne fait que confirmer le bruit ambiant."
        ),
    )
    scene.add(
        Level(price=1.08420, label="support cassé", kind="resistance", start=0, end=2, step=1),
        Marker(index=2, price=1.08520, text="recouvre la bougie rouge", kind="good", step=2, dy=-24, dx=-30),
        # étape 3 : le contexte qui rend la figure exploitable
        Level(price=1.08530, label="support", kind="support", start=1, end=3, step=3, tag_dy=18),
    )
    scene.at(
        ("1. Une bougie de vente",
         "La bougie rouge ferme au plus bas : les vendeurs semblent dominer le court terme."),
        ("2. La bougie suivante prend le dessus",
         "Le corps vert ouvre sous la clôture rouge et ferme au-dessus de son ouverture : "
         "les acheteurs ont repris la main, et plus que ça."),
        ("3. Le contexte tranche",
         "L'engulfing n'a de force que s'il arrive sur un niveau. Ici il ferme "
         "juste au-dessus du support qui venait d'être testé."),
    )
    return scene


def inside_bar() -> Scene:
    scene = Scene(
        id="cd-inside",
        title="L'inside bar : la compression avant le départ",
        principle=(
            "Une bougie entièrement contenue dans la précédente annonce un équilibre "
            "qui ne tiendra pas. Le marché n'a pas encore choisi son sens."
        ),
        candles=from_rows(INSIDE),
        takeaway=(
            "L'inside bar ne donne pas de direction, elle donne une fenêtre : le prochain "
            "mouvement sera plus ample que les trois précédentes. On attend la sortie, "
            "puis on entre dans le sens du départ."
        ),
    )
    scene.add(
        Zone(low=1.08590, high=1.08660, label="compression", kind="neutral",
             start=1, end=4, fill_alpha=40, step=2, tag_side="bottom"),
        Arrow(x1=4, p1=1.08620, x2=4, p2=1.08740, label="sortie", kind="info", step=3, width=2.0),
    )
    scene.at(
        ("1. Une impulsion, puis le silence",
         "Le prix monte, puis trois bougies se resserrent. Les participants "
         "attendent : personne n'ajoute de position."),
        ("2. L'inside bar",
         "Chaque bougie est entièrement contenue dans la précédente. "
         "La volatilité se contracte, le carnet se vide."),
        ("3. La sortie",
         "La compression se résout dans un sens. L'inside bar ne prédit pas "
         "lequel : elle indique qu'il va y avoir un mouvement, pas lequel."),
    )
    return scene


def SCENES() -> list[Scene]:
    return [pinbar(), engulfing(), inside_bar()]
