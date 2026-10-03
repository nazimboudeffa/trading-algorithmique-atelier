"""
Leçon 8 — Gestion du risque : entrée, stop, cible, R:R.

C'est la leçon qui décide du résultat, pas du gain. Une configuration avec 60 %
de réussite et 3:1 de ratio bat une configuration à 80 % de réussite et 0,8:1.
On peut être mauvais lecteur de marché et tout de même rentable, si on sait
placer son stop.

Quatre règles, dans l'ordre :

1. L'entrée se décide AVANT le stop, en fonction de la structure.
2. Le stop se place là où la configuration est fausse, jamais à distance fixe.
3. La cible se place sur ce que le prix peut atteindre (liquidité, niveau opposé).
4. Si le ratio obtenu ne vaut pas 2:1, on ne prend pas le trade. Point.
"""
from __future__ import annotations

from core.model import Level, Marker, Note, Path, Scene, Zone, build

# Configuration complète : uptrend, repli sur support, pin bar, reprise.
TRADE = [
    1.08500, 1.08580, 1.08660, 1.08740, 1.08820, 1.08900,
    1.08820, 1.08720, 1.08640,                         # repli
    1.08650, 1.08760,                                   # reprise
    1.08840, 1.08920,
]

ENTRY = 1.08650
STOP = 1.08560      # sous le creux du repli (1.08620) + une marge
TARGET = 1.08960    # vers la résistance / liquidité au-dessus


def anatomy() -> Scene:
    scene = Scene(
        id="rk-anatomie",
        title="Anatomie d'un trade : entrée, stop, cible",
        principle=(
            "Le stop ne se choisit pas en pourcentage de risque : il se choisit "
            "à l'endroit où l'idée est fausse. Le ratio vient après, il ne se négocie pas."
        ),
        candles=build(1.08500, TRADE, wick=0.00030),
        takeaway=(
            "Un stop trop serré se déclenche sur le bruit normal du marché. "
            "Un stop trop large mange le ratio. Le bon stop est le plus proche "
            "qui soit logiquement justifié — ici, sous le creux qui a lancé la reprise."
        ),
    )
    scene.add(
        # étape 1 : le contexte, avant les niveaux — le creux qui structure le stop
        Path(points=[(8, 1.08640), (10, 1.08840)], label="reprise", kind="good", step=1,
             dots=True, dashed=True, width=1.4),
        Marker(index=8, price=1.08640, text="pin bar : le creux du repli", kind="info", step=1, dy=-36, dx=-200),
        # étape 2 : entrée, stop et objectif
        Level(price=ENTRY, label="Entrée", kind="entry", start=8, end=11, step=2, width=1.6, dashed=False, tag_dx=118),
        Level(price=STOP, label="Stop Loss", kind="stop", start=8, end=11, step=2, width=1.6, dashed=False),
        Level(price=TARGET, label="Objectif", kind="target", start=9, end=11, step=2, width=1.6, dashed=False),
        Zone(low=1.08620, high=1.08650, label="zone d'entrée", kind="entry",
             start=8, end=11, fill_alpha=45, step=2, tag_side="bottom"),
        # étape 3 : ce que la cible doit être
        Level(price=1.08900, label="liquidité au-dessus", kind="liquidity", start=10, end=11, step=3, tag_dx=-40),
    )
    scene.at(
        ("1. L'entrée : sur la confirmation",
         "Pas sur le premier contact du support, mais sur la bougie qui confirme "
         "le rejet. On paie un peu plus pour être moins faux."),
        ("2. Le stop : au mauvais endroit, et pas plus loin",
         "Le creux du repli est à 1.08620. Le stop se pose un peu en dessous : "
         "au-delà, l'idée de reprise est fausse. Le ratio vient de cette distance."),
        ("3. La cible : ce que le prix peut atteindre",
         "La cible n'est pas un chiffre choisi pour faire un joli ratio. "
         "C'est le prochain obstacle réel : ici, la liquidité au-dessus des sommets."),
    )
    return scene


def ratio() -> Scene:
    risk = ENTRY - STOP
    reward = TARGET - ENTRY
    scene = Scene(
        id="rk-ratio",
        title="Le ratio risque/réward et la règle des 2:1",
        principle=(
            "Avec un ratio de 2:1, il suffit d'avoir raison plus d'un tiers du temps. "
            "Avec 1:1, il faut être juste plus d'une fois sur deux, sur le long terme."
        ),
        candles=build(1.08500, TRADE, wick=0.00030),
        takeaway=(
            "Filtre inflexible : si le ratio calculé à partir de la structure est "
            "inférieur à 2:1, on ne prend pas le trade — même si l'analyse est belle. "
            "Une bonne configuration à mauvais ratio est un trade à refuser."
        ),
    )
    scene.add(
        Level(price=ENTRY, label="Entrée", kind="entry", start=8, end=11, step=1, width=1.6, dashed=False),
        Level(price=STOP, label="Stop", kind="stop", start=8, end=11, step=1, width=1.6, dashed=False),
        Level(price=TARGET, label="Objectif", kind="target", start=8, end=11, step=1, width=1.6, dashed=False),
        Note(x=9.5, price=1.08520,
             text=f"Risque  = {risk:.5f}\nGain    = {reward:.5f}\nRatio   = {reward / risk:.2f} : 1",
             kind="info", step=2, width=210, align="center"),
        Marker(index=9, price=1.08860, text="ratio 1,67 : 1 → refusé", kind="bad", step=3, dy=-22, dx=-40),
    )
    scene.at(
        ("1. Mesurer le risque réel",
         "Risque = distance entrée-stop. Ici environ 90 pips. "
         "C'est la seule distance qui compte pour la survie."),
        ("2. Mesurer le gain possible",
         "Gain = distance entrée-objectif. Le ratio s'obtient en divisant, "
         "et il découle de la structure, pas d'un ratio souhaité."),
        ("3. Le filtre des 2:1",
         "Ce trade affiche 1,67:1 — sous le seuil. On le refuse. "
         "Rapprocher la cible de 10 pips ne change rien : "
         "il faut soit une meilleure cible, soit passer son chemin."),
    )
    return scene


def sizing() -> Scene:
    scene = Scene(
        id="rk-taille",
        title="La taille de position : le risque, pas le montant",
        principle=(
            "On ne choisit pas combien d'argent on met, mais combien on accepte "
            "de perdre si l'analyse est fausse."
        ),
        candles=build(1.08500, TRADE, wick=0.00030),
        takeaway=(
            "Sur 10 000 € de capital avec 1 % de risque par trade et 90 pips de "
            "stop, la position se calcule, elle ne se devine pas. "
            "Le levier change tout : il ne change pas le R:R, il change la taille "
            "de la perte réelle."
        ),
    )
    scene.add(
        Level(price=ENTRY, label="Entrée", kind="entry", start=8, end=11, step=1, width=1.6, dashed=False),
        Level(price=STOP, label="Stop (90 pips)", kind="stop", start=8, end=11, step=1, width=1.6, dashed=False),
        Note(x=6, price=1.08450,
             text="Capital 10 000 €\nRisque par trade 1 % → 100 € à perdre\n"
                  "Stop de 90 pips → taille de position calculée sur 100 €",
             kind="info", step=2, width=330, align="center"),
        # étape 3 : ce que le levier ne change pas
        Marker(index=11, price=1.08920, text="le levier n'améliore pas le R:R", kind="warn", step=3, dy=-24, dx=-30),
    )
    scene.at(
        ("1. Fixer le risque en pourcentage",
         "Un pourcentage fixe du capital, par trade. 1 % est une valeur prudente "
         "lorsque l'analyse n'est pas encore fiable."),
        ("2. Convertir en taille de position",
         "La distance du stop donne la taille : plus le stop est large, "
         "plus la position est petite. Le montant risqué ne bouge jamais."),
        ("3. Ce que le levier ne change pas",
         "Lever le levier n'améliore pas le R:R. Il augmente seulement la perte "
         "encourue quand l'analyse se trompe. On ne lève pas le levier pour "
         "gagner plus vite, on ne le lève pas."),
    )
    return scene


def SCENES() -> list[Scene]:
    return [anatomy(), ratio(), sizing()]
