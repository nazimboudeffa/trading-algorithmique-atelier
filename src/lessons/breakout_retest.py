"""
Leçon 7 — Cassure et retest.

Une cassure, ce n'est pas « le prix dépasse un niveau ». Si ça suffisait, on
n'aurait pas de méthode. Une cassure exploitable suppose trois choses :

  1. une CLÔTURE de bougie au-delà du niveau, pas une simple mèche ;
  2. un retest de ce même niveau, qui tient et devient support ;
  3. un contexte favorable — casser un sommet dans un range haussier ne
     signifie pas la même chose que casser un sommet après deux ans de baisse.

Le retest est l'étape qu'on oublie le plus. C'est pourtant là que se joue
l'intérêt : on n'entre pas sur la cassure, on entre sur le retest.
"""
from __future__ import annotations

from core.model import Arrow, Level, Marker, Scene, Zone, build

# Range serré, cassure haussière franche, retest qui tient.
BREAKOUT = [
    1.08500, 1.08560, 1.08620, 1.08580, 1.08640, 1.08590, 1.08660,
    1.08610, 1.08650, 1.08620, 1.08680, 1.08630,        # range
    1.08760, 1.08840,                                   # cassure franche
    1.08700, 1.08690, 1.08730,                         # retest
    1.08800,                                            # reprise
]

# Cassure qui échoue : le retest casse, on revient dans le range.
FALSE_BREAKOUT = [
    1.08500, 1.08600, 1.08700, 1.08620, 1.08710, 1.08630, 1.08680,
    1.08640, 1.08720, 1.08650, 1.08690, 1.08640,
    1.08790,                                            # cassure (mèche)
    1.08660,                                            # clôture sous le niveau : échec
    1.08560, 1.08500,                                   # retour dans le range
]


def breakout() -> Scene:
    level = 1.08680
    scene = Scene(
        id="br-retest",
        title="Cassure et retest : entrer sur le retest, pas sur la cassure",
        principle=(
            "La cassure montre que le prix peut passer. Le retest montre qu'il peut "
            "rester. C'est le retest qui donne une entrée à un risque connu."
        ),
        candles=build(1.08500, BREAKOUT, wick=0.00030),
        takeaway=(
            "Entrer sur la cassure, c'est payer le prix le plus haut avec un stop "
            "imposé par le niveau. Entrer sur le retest, c'est payer moins cher et "
            "placer son stop sous une zone que le marché vient de valider."
        ),
    )
    scene.add(
        Level(price=level, label="résistance du range", kind="resistance", start=0, end=11, step=1),
        Zone(low=level, high=1.08760, label="zone cassée", kind="good",
             start=0, end=11, fill_alpha=26, step=1, tag_side="bottom"),
        Marker(index=12, price=1.08840, text="clôture au-dessus", kind="good", step=2, dy=-22, dx=-24),
        Level(price=level, label="nouveau support", kind="support", start=13, end=16, step=3, tag_dy=16),
        Arrow(x1=14, p1=1.08690, x2=14, p2=1.08730, label="le retest tient", kind="good", step=3, width=1.8),
    )
    scene.at(
        ("1. Un range, donc une résistance connue",
         "Le prix a rebondi plusieurs fois sous 1.08680. Beaucoup de vendeurs "
         "sont exposés au-dessus : une fois le prix passé, ils doivent racheter."),
        ("2. La clôture compte",
         "Ce n'est pas la mèche qui casse le range, c'est la clôture. "
         "Une mèche au-dessus puis un retour immédiat, c'est un faux signal."),
        ("3. Le retest, le vrai point d'entrée",
         "Le prix revient toucher 1.08680 et repart. Le niveau est validé comme "
         "support : on peut acheter au retest avec un stop sous la zone."),
    )
    return scene


def false_breakout() -> Scene:
    level = 1.08690
    scene = Scene(
        id="br-faux",
        title="Le faux breakout : quand la cassure échoue",
        principle=(
            "Une cassure non suivie d'un retest qui tient n'est pas une cassure. "
            "C'est un piège, et il est très fréquent en fin de range."
        ),
        candles=build(1.08500, FALSE_BREAKOUT, wick=0.00032),
        takeaway=(
            "La règle qui protège du piège : exiger une clôture, pas une mèche. "
            "Si le prix referme dans le range, il n'y a pas de cassure — "
            "et souvent, c'est là qu'on trouve la meilleure entrée du range, à l'inverse."
        ),
    )
    scene.add(
        Level(price=level, label="résistance", kind="resistance", start=0, end=12, step=1),
        Arrow(x1=12, p1=1.08790, x2=12, p2=1.08720, label="mèche", kind="bad", step=2, width=1.8),
        Marker(index=13, price=1.08660, text="clôture dans le range → échec", kind="bad", step=3, dy=24, dx=-150),
        Level(price=1.08700, label="aucun nouveau support", kind="warn", start=13, end=16, step=3, dashed=True, tag_dx=-210),
    )
    scene.at(
        ("1. Le prix dépasse le niveau",
         "Une bougie monte au-dessus de 1.08690. Pris de court terme, "
         "c'est ce qu'il faut pour déclencher des achats."),
        ("2. La bougie se retourne",
         "Elle clôture dans le range. Personne n'a suivi, et surtout les acheteurs "
         "viennent d'ouvrir une position que rien ne soutient."),
        ("3. Conséquence",
         "Pas de cassure, donc pas de configuration. Le prix revient au milieu du "
         "range, et la structure reste neutre."),
    )
    return scene


def SCENES() -> list[Scene]:
    return [breakout(), false_breakout()]
