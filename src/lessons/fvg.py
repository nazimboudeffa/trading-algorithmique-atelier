"""
Leçon 5 — Les Fair Value Gaps (déséquilibres / imbalances).

Définition opératoire, en trois bougies : si le bas de la bougie 3 est au-dessus
du haut de la bougie 1, il existe un intervalle de prix que personne n'a
traité. Sur cet intervalle, un seul côté du carnet était présent : c'est un
déséquilibre, et le prix y revient souvent le recharger.

On parle de FVG haussier quand le trou est entre la bougie 1 et la bougie 3
d'une séquence haussière, et de FVG baissier dans le cas inverse.

Limite importante : un FVG n'est pas un signal, c'est une zone de meilleure
exécution. Un FVG au milieu d'un range ne sert à rien ; un FVG après une
impulsion forte, oui.
"""
from __future__ import annotations

from core.model import Marker, Scene, VLine, Zone, from_rows

# Impulsion haussière laissant un trou entre les bougies 1 et 3.
BULLISH_FVG = [
    (1.08500, 1.08560, 1.08480, 1.08550, None, 1),   # b1 : haut 1.08560
    (1.08550, 1.08610, 1.08530, 1.08600, None, 1),   # b2
    (1.08600, 1.08720, 1.08590, 1.08710, None, 1),   # b3 : bas 1.08590 > 1.08560 -> FVG
    (1.08710, 1.08760, 1.08680, 1.08750, None, 1),
    (1.08750, 1.08755, 1.08660, 1.08670, None, 3),   # retour dans le trou
    (1.08670, 1.08740, 1.08650, 1.08730, None, 3),   # recharge
]

# Idem à la baisse.
BEARISH_FVG = [
    (1.08500, 1.08540, 1.08400, 1.08420, None, 1),   # b1 : bas 1.08400
    (1.08420, 1.08430, 1.08300, 1.08320, None, 1),   # b2
    (1.08250, 1.08280, 1.08150, 1.08180, None, 1),   # b3 : haut 1.08280 < bas 1.08400
    (1.08180, 1.08190, 1.08050, 1.08070, None, 1),   # l'impulsion continue
    (1.08070, 1.08360, 1.08060, 1.08340, None, 3),   # retour dans le trou
    (1.08340, 1.08360, 1.08100, 1.08120, None, 3),   # recharge
]


def bullish_fvg() -> Scene:
    low, high = 1.08560, 1.08590
    scene = Scene(
        id="fvg-bullish",
        title="FVG haussier : le trou que personne n'a traité",
        principle=(
            "Quand le bas de la 3e bougie dépasse le haut de la 1re, l'intervalle "
            "entre les deux n'a reçu aucun ordre : c'est un déséquilibre."
        ),
        candles=from_rows(BULLISH_FVG),
        takeaway=(
            "Le prix revient « recharger » le déséquilibre : c'est une meilleure "
            "exécution, pas une prédiction. Un FVG jamais retraité depuis un range "
            "n'a aucune valeur — il n'indique rien sur la force du mouvement."
        ),
    )
    scene.add(
        Zone(low=low, high=high, label="FVG haussier", kind="fvg",
             start=0, end=5, fill_alpha=60, step=2),
        VLine(index=0, label="b1", kind="neutral", step=1),
        VLine(index=2, label="b3", kind="neutral", step=1),
        Marker(index=0, price=1.08560, text="haut de la b1", kind="fvg", step=1, dy=-20, dx=-14),
        Marker(index=2, price=1.08590, text="bas de la b3", kind="fvg", step=1, dy=-20, dx=-14),
        Marker(index=4, price=1.08660, text="retour dans le trou", kind="fvg", step=3, dy=-20, dx=-30),
    )
    scene.at(
        ("1. Mesurer le trou",
         "Haut de la bougie 1 : 1.08560. Bas de la bougie 3 : 1.08590. "
         "La 3e commence au-dessus de la fin de la 1re : rien ne s'est traité entre les deux."),
        ("2. Ce que ça dit du marché",
         "Entre 1.08560 et 1.08590, il n'y avait que des acheteurs. "
         "Un déséquilibre de cet ordre n'est pas rare après une impulsion."),
        ("3. Le retour du prix",
         "Le prix redescend dans le trou et le recharge. C'est le comportement "
         "attendu : la zone attire les ordres, elle n'annonce pas une direction."),
    )
    return scene


def bearish_fvg() -> Scene:
    high, low = 1.08280, 1.08400
    scene = Scene(
        id="fvg-bearish",
        title="FVG baissier : le trou inverse",
        principle=(
            "Quand le haut de la 3e bougie passe sous le bas de la 1re, "
            "l'intervalle n'a reçu que des vendeurs : FVG baissier."
        ),
        candles=from_rows(BEARISH_FVG),
        takeaway=(
            "Un FVG n'est exploitable que dans le sens du déséquilibre. "
            "Un FVG haussier dans un downtrend n'est pas un signal d'achat : "
            "c'est un simple niveau de résistance déguisé."
        ),
    )
    scene.add(
        Zone(low=low, high=high, label="FVG baissier", kind="fvg",
             start=0, end=5, fill_alpha=60, step=2),
        Marker(index=2, price=1.08280, text="haut de la b3", kind="fvg", step=1, dy=-20, dx=-14),
        Marker(index=0, price=1.08400, text="bas de la b1", kind="fvg", step=1, dy=-20, dx=-14),
        Marker(index=4, price=1.08340, text="retour dans le trou", kind="fvg", step=3, dy=-22, dx=-30),
    )
    scene.at(
        ("1. Mesurer le trou",
         "Bas de la bougie 1 : 1.08400. Haut de la bougie 3 : 1.08280. "
         "La 3e se termine bien sous le début de la 1re."),
        ("2. Même lecture, sens opposé",
         "L'intervalle n'a reçu que des vendeurs. Le déséquilibre pousse le prix "
         "vers le bas jusqu'à ce qu'il soit rechargé."),
        ("3. Rester dans le sens",
         "On exploite un FVG baissier pour vendre, un FVG haussier pour acheter. "
         "Utiliser un FVG contre son propre déséquilibre, c'est chercher une opposition."),
    )
    return scene


def SCENES() -> list[Scene]:
    return [bullish_fvg(), bearish_fvg()]
