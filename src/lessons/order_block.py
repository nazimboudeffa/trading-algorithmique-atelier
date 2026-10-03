"""
Leçon 4 — Les order blocks.

Définition opératoire, sans jargon : un order block est la DERNIÈRE bougie
opposée avant un mouvement fort. Autrement dit, la dernière bougie de vente
avant une impulsion haussière, ou la dernière bougie d'achat avant une impulsion
baissière.

Pourquoi ça fonctionne : cette bougie a absorbé les ordres de la direction
contraire. Après le départ du prix, ceux qui restent ne peuvent plus entrer à ce
prix, et ceux qui sont entrés défendent la zone. Le corps de la bougie est donc
la trace d'un déséquilibre réel.

Deux limites à connaître :
  * la bougie doit avoir absorbé (corps net, mèches marquées) ;
  * la zone ne vaut que si elle n'a pas encore été retestée.
"""
from __future__ import annotations

from core.model import Arrow, Marker, Path, Scene, Zone, build

# Impulsion haussière franche après une bougie de vente qui absorbe.
BULLISH_OB = [
    1.08500, 1.08440, 1.08380, 1.08330,   # descente
    1.08260,                                # bougie d'absorption (order block)
    1.08350, 1.08420, 1.08510, 1.08580,    # impulsion
    1.08560, 1.08520,                       # retest
]

# La même chose à l'envers.
BEARISH_OB = [
    1.08500, 1.08560, 1.08620, 1.08670,
    1.08740,
    1.08650, 1.08590, 1.08500, 1.08420,
    1.08440, 1.08480,
]


def bullish_ob() -> Scene:
    ob_low, ob_high = 1.08240, 1.08280
    scene = Scene(
        id="ob-bullish",
        title="Order block haussier : la dernière bougie de vente",
        principle=(
            "La dernière bougie opposée avant une impulsion forte marque une zone "
            "où les acheteurs ne pouvaient plus entrer. C'est une zone d'intérêt."
        ),
        candles=build(1.08500, BULLISH_OB, wick=0.00032),
        takeaway=(
            "On ne cherche pas l'order block le plus proche : on cherche celui qui "
            "a déclenché le mouvement. Un order block suivi d'un long trajet sans "
            "retest ne vaut plus grand-chose — l'écart s'est trop éloigné du prix."
        ),
    )
    scene.add(
        Zone(low=ob_low, high=ob_high, label="order block", kind="orderblock",
             start=4, end=5, fill_alpha=70, border=True, tag_side="bottom"),
        Path(points=[(0, 1.08500), (4, 1.08260)], label="avant", kind="neutral",
             step=1, dots=True, dashed=True, width=1.4),
        Arrow(x1=5, p1=1.08280, x2=9, p2=1.08580, label="impulsion", kind="good", step=2, width=2.2),
        Marker(index=4, price=ob_low, text="absorption", kind="orderblock", step=1, dy=26, dx=-6),
        # étape 3 : le retest, seul moment où la zone se-trade
        Arrow(x1=10, p1=1.08590, x2=9, p2=1.08535, label="retest", kind="info", step=3, width=1.6),
        Marker(index=9, price=1.08520, text="point d'entrée", kind="good", step=3, dy=26, dx=-30),
    )
    scene.at(
        ("1. Repérer l'absorption",
         "Bougie 5 : corps net vers le bas, mèches marquées. Elle a vendu fortement "
         "avant que le prix ne remonte — c'est le profil d'un ordreblock."),
        ("2. Constater le départ",
         "Le prix s'échappe d'une traite : plusieurs corps haussiers d'affilée. "
         "L'order block n'est valable que s'il a déclenché un mouvement franc."),
        ("3. Attendre le retest",
         "Le prix revient sur la zone. C'est là, et seulement là, qu'il y a un "
         "intérêt à entrer : la zone est déjà testée par le marché."),
    )
    return scene


def bearish_ob() -> Scene:
    ob_low, ob_high = 1.08720, 1.08760
    scene = Scene(
        id="ob-bearish",
        title="Order block baissier : la dernière bougie d'achat",
        principle=(
            "Symétrique : la dernière bougie haussière avant une impulsion baissière "
            "devient une zone de résistance."
        ),
        candles=build(1.08500, BEARISH_OB, wick=0.00032),
        takeaway=(
            "Un order block n'est pas un signal d'entrée, c'est une zone à surveiller. "
            "Il faut que le contexte soit aligné : un order block baissier dans une "
            "structure haussière est un simple pullback, pas un retournement."
        ),
    )
    scene.add(
        Zone(low=ob_low, high=ob_high, label="order block", kind="orderblock",
             start=4, end=5, fill_alpha=70, border=True, tag_side="bottom"),
        Arrow(x1=5, p1=1.08720, x2=9, p2=1.08420, label="impulsion", kind="bad", step=2, width=2.2),
        Marker(index=4, price=ob_high, text="absorption", kind="orderblock", step=1, dy=-22, dx=-6),
        # étape 3 : le retest baissier, à condition que la structure le permette
        Arrow(x1=10, p1=1.08470, x2=9, p2=1.08535, label="retest", kind="info", step=3, width=1.6),
        Marker(index=9, price=1.08560, text="zone de vente", kind="bad", step=3, dy=-24, dx=-30),
    )
    scene.at(
        ("1. La bougie d'achat qui bloque",
         "Bougie 5 : le prix monte, il achète, puis il tombe. C'est le dernier "
         "achat avant la distribution — l'order block baissier."),
        ("2. Le départ",
         "L'impulsion baissière confirme la zone. Sans ce départ, on n'aurait "
         "qu'une simple bougie dans le vide."),
        ("3. Le retest ne clôt pas la discussion",
         "Au retour sur la zone, on cherche des ventes si et seulement si la "
         "structure le permet. Sinon, on laisse passer : la zone reste une zone."),
    )
    return scene


def SCENES() -> list[Scene]:
    return [bullish_ob(), bearish_ob()]
