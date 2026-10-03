"""
Leçon 3 — La liquidité.

Le prix va là où sont les ordres, pas là où il est rentable. Or les ordres
s'accumulent toujours aux extremos visibles :

  * au-dessus des sommets : les stops des acheteurs (et les ordres d'achat en
    breakout) ;
  * en dessous des creux : les stops des vendeurs.

D'où la règle : la liquidité est un aimant. Le prix va la chercher, la prend,
puis repart — c'est le sweep. Le mouvement qui suit un sweep est souvent plus
fiable que le mouvement qui l'a créé, parce qu'il est déclenché par des stops
et non par des acheteurs.
"""
from __future__ import annotations

from core.model import Arrow, Level, Marker, Path, Scene, Zone, from_rows

# Deux sommets quasi identiques, puis le prix les dépasse à la hausse.
EQUAL_HIGHS = [
    (1.08500, 1.08580, 1.08480, 1.08570, None, 1),
    (1.08570, 1.08660, 1.08550, 1.08650, None, 1),
    (1.08650, 1.08670, 1.08540, 1.08560, None, 1),
    (1.08560, 1.08665, 1.08530, 1.08655, None, 1),
    (1.08655, 1.08680, 1.08560, 1.08580, None, 1),
    (1.08580, 1.08650, 1.08500, 1.08520, None, 1),
    (1.08520, 1.08560, 1.08460, 1.08480, None, 1),
    (1.08480, 1.08760, 1.08470, 1.08750, "sweep", 3),   # le sweep de liquidité
    (1.08750, 1.08770, 1.08600, 1.08610, None, 3),        # le rejet
]


def equal_highs() -> Scene:
    scene = Scene(
        id="liq-equal-highs",
        title="Les sommets égaux sont un aimant à liquidité",
        principle=(
            "Deux sommets au même prix = des stops au même prix. "
            "Il y a donc, au-dessus, une concentration d'ordres qui attend le prix."
        ),
        candles=from_rows(EQUAL_HIGHS),
        takeaway=(
            "Chercher des sommets égaux ou presque égaux, c'est chercher où le prix "
            "a une raison d'aller. Un range entre deux sommets égaux est un "
            "préparatif : quelque chose va se passer."
        ),
    )
    scene.add(
        Path(points=[(1, 1.08660), (3, 1.08665)], kind="liquidity", step=1, width=2.0, dashed=False),
        Level(price=1.08663, label="liquidité au-dessus", kind="liquidity", start=0, end=6,
              width=1.4, step=1, tag_dy=-26),
        Zone(low=1.08530, high=1.08670, label="zone d'indécision", kind="neutral",
             start=0, end=6, fill_alpha=26, step=2, tag_side="bottom"),
    )
    scene.at(
        ("1. Deux sommets, même prix",
         "Le premier sommet à 1.0866, le second exactement au même endroit. "
         "L'alignement est trop net pour être un hasard."),
        ("2. Où sont les ordres ?",
         "Au-dessus de ces sommets se trouvent les stops des acheteurs. "
         "C'est la seule chose qui intéresse ces niveaux : ce n'est pas le prix, "
         "c'est ce qu'il y a derrière."),
        ("3. Le prix va les chercher",
         "Tant que la liquidité n'est pas prise, le sideways n'a pas de raison "
         "d'être. Le prix a intérêt à aller la chercher au plus vite."),
    )
    return scene


def sweep() -> Scene:
    scene = Scene(
        id="liq-sweep",
        title="Le sweep : prendre la liquidité puis revenir",
        principle=(
            "Le prix dépasse un sommet pour déclencher les stops, puis repart. "
            "Ce mouvement s'appelle un sweep ; c'est souvent un signal, pas une erreur."
        ),
        candles=from_rows(EQUAL_HIGHS),
        takeaway=(
            "Un sweep n'est pas un rejet de résistance classique : le niveau a été "
            "dépassé, pas seulement touché. Les vendeurs qui se sont ajoutés sur la "
            "casse sont le moteur du mouvement qui suit."
        ),
    )
    scene.add(
        Level(price=1.08663, label="sommets égaux", kind="liquidity", start=0, end=7, width=1.4, step=1),
        Marker(index=6, price=1.08680, text="stops des acheteurs", kind="liquidity", step=1, dy=-20, dx=-14),
        Arrow(x1=6, p1=1.08690, x2=7, p2=1.08750, label="trajet vers la liquidité", kind="info", step=2, width=1.8),
        Arrow(x1=6, p1=1.08720, x2=7, p2=1.08750, label="sweep", kind="liquidity", step=3, width=2.0),
        Marker(index=7, price=1.08760, text="liquidité prise", kind="liquidity", step=3, dy=-38, dx=-6),
        Arrow(x1=7, p1=1.08700, x2=8, p2=1.08610, label="retour", kind="good", step=3, width=2.0),
    )
    scene.at(
        ("1. Le prix part chercher la liquidité",
         "Il monte droit vers les sommets égaux. Ce n'est pas un achat enthousiaste, "
         "c'est un trajet vers un pocket d'ordres."),
        ("2. Le dépassement",
         "Le sommet est percé : tous les stops sont déclenchés en même temps. "
         "Ces ordres sont de la VENTE, et c'est ce qui alimente la suite."),
        ("3. Le retour",
         "Le prix revient dans la zone. Beaucoup de positions ont été ouvertes trop "
         "tôt : le mouvement vers la zone d'intérêt commence."),
    )
    return scene


def after_sweep() -> Scene:
    """Ce qu'il faut faire d'un sweep : ne pas l'interpréter trop vite."""
    scene = Scene(
        id="liq-piege",
        title="Le piège du sweep : ce n'est pas un signal d'achat",
        principle=(
            "Un sweep suivi d'un retour n'est pas une preuve de retournement. "
            "La structure doit confirmer avant qu'on en déduise un nouveau sens."
        ),
        candles=from_rows(EQUAL_HIGHS + [
            (1.08610, 1.08630, 1.08570, 1.08580, None, 1),
            (1.08580, 1.08590, 1.08480, 1.08490, None, 1),
            (1.08490, 1.08510, 1.08400, 1.08410, None, 1),
        ]),
        takeaway=(
            "La séquence complète (sweep, retour, puis creux plus bas que le précédent) "
            "dit la même chose qu'un downtrend qui commence. Un sweep isolé ne dit rien ; "
            "c'est la structure qui tranche."
        ),
    )
    scene.add(
        Level(price=1.08663, label="sommets égaux", kind="liquidity", start=0, end=7, width=1.4, step=1),
        Arrow(x1=6, p1=1.08720, x2=7, p2=1.08750, label="sweep", kind="liquidity", step=2, width=2.0),
        Marker(index=7, price=1.08760, text="« ça va monter »", kind="bad", step=2, dy=-38, dx=-6),
        Path(points=[(3, 1.08665), (11, 1.08480)], label="puis ça casse", kind="bad", step=3,
             dots=True, dashed=True, width=1.6),
        Marker(index=11, price=1.08400, text="structure baissière", kind="bad", step=3, dy=28, dx=-172),
    )
    scene.at(
        ("1. Le réflexe naturel",
         "Sweep au-dessus des sommets égaux, donc retour : la conclusion rapide, "
         "c'est « ça va redescendre »."),
        ("2. Ce que le sweep ne dit pas",
         "Un sweep indique que de la liquidité a été prise. Il ne dit pas dans quel "
         "sens le prix va ensuite. Le marché peut repartir plusieurs fois."),
        ("3. La structure tranche",
         "Si le prix casse le creux précédent, la structure bascule en baisse : "
         "on ne cherche plus d'achats. Le sweep n'était que le début de la distribution."),
    )
    return scene


def SCENES() -> list[Scene]:
    return [equal_highs(), sweep(), after_sweep()]
