"""
Leçon 2 — Supports, résistances et retournement (flip).

Trois idées à retenir :

1. Un niveau est une ZONE, pas une ligne. Le prix ne respecte pas 1.13500,
   il respecte une bande de prix. Un niveau touché une fois n'est rien ; ce qui
   compte, c'est le nombre de fois où le prix a réagi.

2. Un support qui casse devient une résistance, et réciproquement (flip).
   C'est le même prix, mais le rôle s'inverse parce que les positions
   changent de camp.

3. Un support ne tient pas parce qu'il est « beau » : il tient parce que des
   acheteurs y étaient disposés à entrer. Quand ils n'y sont plus, il casse.
"""
from __future__ import annotations

from core.model import Arrow, Level, Marker, Scene, Zone, build

# Rebonds répétés sur un même niveau bas, puis reprise.
SUPPORT_CLOSES = [
    1.08500, 1.08520, 1.08480, 1.08490, 1.08530, 1.08500, 1.08470,
    1.08495, 1.08525, 1.08485, 1.08510, 1.08540, 1.08590, 1.08650,
]

# Résistance qui cède puis qui refuse le retest : le flip.
FLIP_CLOSES = [
    1.08500, 1.08600, 1.08680, 1.08750, 1.08700, 1.08620, 1.08560,
    1.08500, 1.08540, 1.08600, 1.08550, 1.08520, 1.08560, 1.08510,
]


def support_resistance() -> Scene:
    """Un niveau est une zone, et sa force vient du nombre de réactions."""
    level = 1.08500
    scene = Scene(
        id="sr-zones",
        title="Un niveau est une zone, pas une ligne",
        principle=(
            "Le prix se souvient des zones où il a hésité, pas de chiffres exacts. "
            "Un niveau se mesure au nombre de réactions, pas à sa précision."
        ),
        candles=build(1.08500, SUPPORT_CLOSES, wick=0.00030),
        takeaway=(
            "Devant un niveau, la question n'est pas « le prix va-t-il respecter "
            "1.08500 ? » mais « le prix a-t-il déjà réagi ici, et peut-il encore le faire ? ». "
            "Un niveau touché trois fois est plus significatif qu'un niveau touché une fois."
        ),
    )
    scene.add(
        # étape 1 : la zone, avant même de compter les rebonds
        Zone(low=level - 0.00018, high=level + 0.00018, label="zone de support", kind="support",
             start=0, end=12, fill_alpha=55, step=1),
        Level(price=level, kind="support", start=0, end=12, show_tag=False, step=1),
        # étape 2 : on compte les réactions
        Marker(index=2, price=level, text="1er rebond", kind="support", step=2, dy=-22, dx=-10),
        Marker(index=6, price=level, text="2e rebond", kind="support", step=2, dy=-22, dx=-10),
        Marker(index=10, price=level, text="3e rebond", kind="support", step=2, dy=-22, dx=-10),
        # étape 3 : l'usure de la zone
        Marker(index=11, price=1.08610, text="la zone s'épuise", kind="warn", step=3, dy=-22, dx=-24),
    )
    scene.at(
        ("1. Le prix ignore le chiffre",
         "Le support n'est pas à 1.08500 pile. C'est une bande : tout ce qui est "
         "proche de 1.08500 a été traité comme la même zone."),
        ("2. Compter les réactions",
         "Trois rebonds depuis la même zone. Chaque rebond est autant d'acheteurs "
         "qui se sont engagés : c'est ce qui rend la zone solide."),
        ("3. Règle de prudence",
         "Un niveau touché beaucoup de fois s'affaiblit : il reste de moins en moins "
         "d'acheteurs prêts à entrer. Le prochain test a toutes les chances de passer."),
    )
    return scene


def flip() -> Scene:
    """Support cassé = résistance : même prix, rôle inversé."""
    level = 1.08700
    scene = Scene(
        id="sr-flip",
        title="Le retournement : support cassé = résistance",
        principle=(
            "Quand un support casse, le même prix devient une résistance. "
            "Le niveau ne bouge pas : c'est le rôle des positions qui s'inverse."
        ),
        candles=build(1.08500, FLIP_CLOSES, wick=0.00030),
        takeaway=(
            "Le flip explique pourquoi un ancien support « ne devrait plus jamais » "
            "retient le prix. Les vendeurs pris au piège vendent pour se sortir, "
            "et leurs ordres empêchent le rebond de durer."
        ),
    )
    scene.add(
        Level(price=level, label="résistance", kind="resistance", start=0, end=6, step=1),
        Zone(low=level - 0.00016, high=level + 0.00016, label="la même zone, rôle inversé",
             kind="resistance", start=6, end=13, fill_alpha=55, step=3),
        Arrow(x1=5, p1=1.08630, x2=6, p2=1.08560, label="casse", kind="bad", step=2, width=1.8),
        Marker(index=8, price=1.08520, text="rebond refusé", kind="bad", step=3, dy=26, dx=-24),
    )
    scene.at(
        ("1. Une résistance qui tient",
         "Le prix rebondit sous 1.08700. Beaucoup de vendeurs y sont entrés : "
         "c'est une résistance crédible."),
        ("2. La cassure",
         "Le prix passe au-dessus. Les vendeurs sont pris au piège et leurs stops "
         "sont déclenchés : c'est ce qui crée l'impulsion."),
        ("3. Le nouveau rôle",
         "Au retest, le prix refuse le niveau. Les acheteurs tardifs revendent et "
         "les prises de perte vendent : le support est devenu une résistance."),
    )
    return scene


def breaking() -> Scene:
    """Ce qui rend un niveau solide, et ce qui le fait céder."""
    scene = Scene(
        id="sr-force",
        title="Ce qui rend un niveau solide, et ce qui le casse",
        principle=(
            "Un niveau tient parce que des ordres s'y accumulent, pas parce qu'il "
            "est arrondi. Il cède quand de nouveaux participants arrivent en face."
        ),
        candles=build(1.08500, [
            1.08530, 1.08580, 1.08640, 1.08620, 1.08560, 1.08520, 1.08490,
            1.08540, 1.08600, 1.08660, 1.08720, 1.08780, 1.08840, 1.08900,
        ], wick=0.00030),
        takeaway=(
            "Plus un niveau a été testé et a tenu, plus il compte — jusqu'au moment "
            "où quelqu'un de décidé passe dessus. Une cassure franche n'est pas un "
            "achat, c'est un avertissement."
        ),
    )
    scene.add(
        # étape 1 : le niveau testé, avec ses trois contacts
        Level(price=1.08500, label="support testé 3 fois", kind="support", start=0, end=8, step=1),
        Marker(index=3, price=1.08500, text="contact", kind="support", step=1, dy=-38, dx=-16),
        Marker(index=6, price=1.08500, text="contact", kind="support", step=1, dy=-38, dx=-16),
        # étape 2 : la sortie de zone
        Arrow(x1=9, p1=1.08610, x2=12, p2=1.08880, label="sortie de zone", kind="info", step=2, width=1.8),
        # étape 3 : le sommet devenu plafond
        Level(price=1.08900, label="nouveau sommet", kind="resistance", start=11, end=13, step=3, tag_dx=-96),
    )
    scene.at(
        ("1. Plusieurs tentatives, aucune rupture",
         "Le support est testé plusieurs fois et encaisse chaque fois. "
         "Les acheteurs défendent la zone : elle devient fiable."),
        ("2. L'accélération",
         "Le prix s'échappe rapidement. Une hausse qui va vite signale que les "
         "vendeurs ont été balayés : stops et ordres en attente partent ensemble."),
        ("3. Le sommet devient un plafond",
         "Le point le plus haut atteint est aussi un niveau : on repassera difficilement "
         "dessous. C'est la même règle que pour un support, appliquée à l'envers."),
    )
    return scene


def SCENES() -> list[Scene]:
    return [support_resistance(), flip(), breaking()]
