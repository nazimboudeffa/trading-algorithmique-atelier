"""
Niveaux et déclencheurs.

Deux familles, à ne pas confondre :

    les niveaux (`sr_levels`)   — des zones où le prix a déjà réagi. On les
                                  trouve en H1, pas en M15 : un niveau de M15
                                  est du bruit.

    le déclencheur (`find_trigger`) — ce que le prix fait *maintenant* en M15.
                                  C'est lui qui déclenche, pas le niveau. Un
                                  niveau qui ne déclenche rien ne vaut rien.

Le déclencheur retenu est volontairement étroit et vérifiable : une bougie de
rejet qui clôture du bon côté du niveau. Trois critères objectifs, aucun vote.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .measure import median_range
from .structure import BOTTOM, TOP, Position, Structure, Swing

#: Deux swings dont les prix sont à moins de ce multiple de l'amplitude typique
#: d'une bougie appartiennent au même niveau. 0.5 : une demi-bougie d'écart,
#: c'est-à-dire le bruit d'une mèche.
LEVEL_TOLERANCE_FACTOR = 0.5

#: Nombre de swings structurels pris en compte. Au-delà, ce sont des niveaux
#: que le marché a abandonnés : on trade contre la structure vivante, pas
#: contre l'histoire.
LEVEL_DEPTH = 8

#: Deux passages sur un même niveau ne comptent pour deux tests distincts que
#: s'ils sont séparés d'au moins `VISIT_GAP` bougies. En dessous, le prix n'a
#: pas quitté la zone : il longeait.
VISIT_GAP = 3

#: Nombre de swings qui classe un niveau comme « fort ».
STRONG_TOUCHES = 3

#: Un rejet est crédible si sa mèche vaut au moins ce ratio de l'amplitude.
REJECTION_WICK_RATIO = 0.45

#: Distance maximale d'un niveau par rapport au prix, en fraction de
#: l'enveloppe de structure, pour qu'un niveau compte encore comme « proche ».
NEAR_RATIO = 0.12

#: Direction d'un déclencheur.
LONG = "long"
SHORT = "short"


# --------------------------------------------------------------------------- #
# Niveaux
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SRLevel:
    """Un niveau de support ou de résistance, et le nombre de fois atteint.

    `touches` compte des *retours du prix*, pas des bougies. C'est la nuance
    qui sépare une lecture de marché d'un décor : une résistance que le prix a
    « touchée » 39 fois n'est pas une résistance, c'est une zone dans laquelle
    il cohabite. Ce qui compte, ce sont les changements d'avis répétés au même
    prix.

    `alive` répond à une autre question, et c'est la plus importante : ce niveau
    existe-t-il *encore* ? Un sommet que le marché a quitté il y a quatre mois
    sans y revenir n'est pas un niveau, c'est une anecdote. On peut le
    retrouver sur l'historique, mais on ne peut ni entrer dessus ni le viser
    comme obstacle : le ratio qu'on calculerait serait une fiction.
    """

    price: float
    kind: str  # "support" | "resistance"
    touches: int = 1
    first_index: int = 0
    last_index: int = 0
    alive: bool = True

    @property
    def strong(self) -> bool:
        return self.alive and self.touches >= STRONG_TOUCHES

    def label(self) -> str:
        word = "support" if self.kind == "support" else "resistance"
        marks = "*" * min(self.touches, 4)
        if not self.alive:
            return f"{word} {marks} — ancien, plus jamais testé"
        return f"{word} {marks} ({self.touches} tests)"


def _clusters(swings: list[Swing], tolerance: float) -> list[list[Swing]]:
    """Regroupe les swings dont les prix sont à moins de `tolerance` les uns des autres.

    Le regroupement est fait dans l'ordre des prix, pas des dates : deux
    sommets éloignés de six semaines mais quasi identiques comptent autant que
    deux sommets consécutifs. Ce qui rapproche deux niveaux, c'est le prix,
    pas le temps.
    """
    if not swings:
        return []
    ordered = sorted(swings, key=lambda s: s.price)
    groups: list[list[Swing]] = [[ordered[0]]]
    for swing in ordered[1:]:
        if swing.price - groups[-1][-1].price <= tolerance:
            groups[-1].append(swing)
        else:
            groups.append([swing])
    return groups


def _visits(df: pd.DataFrame, price: float, tolerance: float, start: int) -> list[int]:
    """Les positions où le prix est repassé sur le niveau depuis `start`.

    Deux passages comptés comme un seul s'ils sont séparés de moins de
    `VISIT_GAP` bougies : le prix a longeu le niveau, il ne l'a pas testé
    quarante fois. C'est la distinction entre un support qui tient et un prix
    qui cohabite avec une zone.

    On travaille en positions et jamais sur les étiquettes d'index : l'index de
    yfinance est horodaté, et soustraire deux dates ne donne pas un nombre de
    bougies.
    """
    n = len(df)
    if start + 1 >= n:
        return []

    highs = df["High"].to_numpy()
    lows = df["Low"].to_numpy()
    out: list[int] = []
    for pos in range(start + 1, n):
        if lows[pos] <= price + tolerance and highs[pos] >= price - tolerance:
            if not out or pos - out[-1] >= VISIT_GAP:
                out.append(pos)
    return out


def _as_level(group: list[Swing], df: pd.DataFrame, tolerance: float) -> SRLevel:
    """Le groupe de swings le plus récent devient un niveau.

    Un groupe peut contenir des sommets *et* des creux : c'est un range, un
    prix où le marché a changé d'avis dans les deux sens. Le dernier swing
    tranche, parce que c'est lui qui décrit la structure en cours.
    """
    prices = [s.price for s in group]
    most_recent = max(group, key=lambda s: s.index)
    price = sum(prices) / len(prices)
    born = min(s.index for s in group)

    visits = _visits(df, price, tolerance, born)
    return SRLevel(
        price=price,
        kind="resistance" if most_recent.is_high else "support",
        touches=1 + len(visits),
        first_index=born,
        last_index=visits[-1] if visits else max(s.index for s in group),
        alive=bool(visits),
    )


def _has_level_at(levels: list[SRLevel], price: float, kind: str, tolerance: float) -> bool:
    return any(lv.kind == kind and abs(lv.price - price) <= tolerance for lv in levels)


def sr_levels(
    df: pd.DataFrame,
    structure: Structure,
    tolerance: float = 0.0,
    depth: int = LEVEL_DEPTH,
) -> list[SRLevel]:
    """Les niveaux de structure : les prix où le marché a déjà changé d'avis.

    On part des swings structurels — les mêmes que ceux qui ont donné la
    tendance — et on regroupe ceux qui sont au même prix. Les deux bornes, le
    dernier sommet et le dernier creux, sont toujours présents même isolés :
    ce sont elles qui définissent la position du prix, et le raisonnement a
    besoin de l'enveloppe complète.

    Chaque niveau portera la mention `alive` : le prix est-il revenu le tester
    depuis qu'il s'est formé ? Cette mention est le garde-fou qui empêche le
    moteur de chiffrer un plan sur un sommet d'il y a quatre mois. Sur une
    fenêtre daily de cinq ans, l'écart entre le dernier sommet et le prix
    peut atteindre plusieurs centaines de pips ; y poser une entrée et un stop
    produirait un ratio qui n'a aucun sens. Un plan calculé sur un niveau mort
    n'est pas un plan prudent, c'est un calcul.
    """
    if tolerance <= 0:
        typical = median_range(df)
        # série plate ou dégénérée : on retombe sur un pourcentage du prix,
        # plutôt que de refuser de produire des niveaux
        tolerance = typical * LEVEL_TOLERANCE_FACTOR if typical > 0 else \
            float(df["High"].iloc[-1]) * 0.0002

    swings = structure.swings[-depth:] if structure.swings else []
    levels = [_as_level(g, df, tolerance) for g in _clusters(swings, tolerance)]

    # les deux bornes de la structure, garanties
    for kind, swing in (("resistance", structure.last_high), ("support", structure.last_low)):
        if swing is not None and not _has_level_at(levels, swing.price, kind, tolerance):
            visits = _visits(df, swing.price, tolerance, swing.index)
            levels.append(
                SRLevel(price=swing.price, kind=kind, touches=1 + len(visits),
                        first_index=swing.index,
                        last_index=visits[-1] if visits else swing.index,
                        alive=bool(visits))
            )

    levels.sort(key=lambda lv_: lv_.price)
    return levels


def nearest(levels: list[SRLevel], price: float, kind: str, alive_only: bool = True) -> SRLevel | None:
    """Le niveau de ce type le plus proche du prix.

    `alive_only` est le comportement par défaut, et c'est le point important :
    on ne se place pas sur un niveau mort. Le paramètre reste là pour les rares
    cas où l'on veut lire l'enveloppe complète — typiquement pour dessiner le
    contexte, pas pour construire un plan.
    """
    same = [lv for lv in levels if lv.kind == kind and (lv.alive or not alive_only)]
    if not same:
        return None
    return min(same, key=lambda lv: abs(lv.price - price))


# --------------------------------------------------------------------------- #
# Déclencheur
# --------------------------------------------------------------------------- #


@dataclass
class Trigger:
    """Un rejet confirmé sur un niveau, avec ses mesures.

    Les faits sont stockés bruts et la phrase est fabriquée à la demande : le
    nombre de décimales dépend de la paire, et ce module ne connaît pas les
    paires. Écrire la phrase ici imposerait cinq décimales à tout le monde.

    `at` est l'horodatage de la bougie. Sans lui, il faudrait annoncer « bougie
    1297 » : un numéro qu'aucun lecteur ne peut retrouver sur un graphique de
    cinq ans. Une date se vérifie d'un coup d'œil.
    """

    direction: str  # LONG | SHORT
    index: int
    price: float  # le niveau rejeté
    close: float  # la clôture qui confirme
    wick_ratio: float  # part de la mèche dans l'amplitude
    at: str = ""

    @property
    def is_long(self) -> bool:
        return self.direction == LONG

    def describe(self, fmt: str = "{:.5f}") -> str:
        """Une phrase : quand, où, et de quelle qualité."""
        side = "au-dessus" if self.is_long else "au-dessous"
        when = f"le {self.at}" if self.at else f"bougie {self.index + 1}"
        return (
            f"{when} : mèche de {self.wick_ratio * 100:.0f} % de l'amplitude, "
            f"clôture à {fmt.format(self.close)} {side} du niveau "
            f"{fmt.format(self.price)}"
        )


def _rejection(i: int, row: pd.Series, level: float) -> tuple[str, float] | None:
    """Direction et qualité d'un rejet de la bougie `i` autour de `level`."""
    rng = float(row["High"] - row["Low"])
    if rng <= 0:
        return None
    o, c = float(row["Open"]), float(row["Close"])
    h, low = float(row["High"]), float(row["Low"])

    # --- rejet acheteur : la mèche basse touche le niveau, le corps reste dessus
    if low <= level <= min(o, c):
        wick = min(o, c) - low
        if wick / rng >= REJECTION_WICK_RATIO:
            return LONG, wick / rng

    # --- rejet vendeur : la mèche haute touche le niveau, le corps reste dessous
    if h >= level >= max(o, c):
        wick = h - max(o, c)
        if wick / rng >= REJECTION_WICK_RATIO:
            return SHORT, wick / rng
    return None


def find_trigger(df: pd.DataFrame, levels: list[SRLevel], lookback: int = 5) -> Trigger | None:
    """Le déclencheur le plus récent, ou `None`.

    On regarde les `lookback` dernières bougies et on garde le rejet le plus
    récent. Seuls les niveaux vivants sont retenus : un rejet sur un sommet
    d'il y a quatre mois est une anecdote, pas un signal.

    `None` est une réponse parfaitement normale : sans déclencheur, il n'y a
    rien à faire, et le moteur le dira.
    """
    usable = [lv for lv in levels if lv.alive]
    if not usable:
        return None
    n = len(df)
    start = max(0, n - lookback)
    best: Trigger | None = None

    for i in range(n - 1, start - 1, -1):
        row = df.iloc[i]
        for lv in usable:
            found = _rejection(i, row, lv.price)
            if found is None:
                continue
            direction, quality = found
            if best is not None:
                continue  # on a déjà un rejet plus récent
            best = Trigger(
                direction=direction,
                index=i,
                price=lv.price,
                close=float(row["Close"]),
                wick_ratio=quality,
                at=df.index[i].strftime("%d/%m/%Y"),
            )
        if best is not None:
            break
    return best


def sweep_of_liquidity(df: pd.DataFrame, structure: Structure, lookback: int = 5) -> dict | None:
    """Détecte un balayage de liquidité récent au-delà d'un sommet ou creux.

    Le prix perce un sommet précédent puis referme en dessous : c'est un
    achat-stop déclenché puis annulé. Le moteur le signale comme un contexte
    (favorable à un retournement), jamais comme un signal.
    """
    n = len(df)
    # profondeur réelle : on ne peut pas remonter de `lookback` bougies si la
    # série est plus courte — sinon on irait lire des index négatifs.
    depth = min(lookback, max(0, n - 1))
    if depth < 1:
        return None
    for swing, name in ((structure.prev_high, "sommet"), (structure.prev_low, "creux")):
        if swing is None:
            continue
        for i in range(n - 1, n - depth - 1, -1):
            row = df.iloc[i]
            if swing.is_high and float(row["High"]) > swing.price and float(row["Close"]) < swing.price:
                return {
                    "kind": "sweep_high",
                    "index": i,
                    "level": swing.price,
                    "why": f"la bougie {i + 1} dépasse le {name} {swing.price:.5f} puis clôture dessous",
                }
            if not swing.is_high and float(row["Low"]) < swing.price and float(row["Close"]) > swing.price:
                return {
                    "kind": "sweep_low",
                    "index": i,
                    "level": swing.price,
                    "why": f"la bougie {i + 1} perce le {name} {swing.price:.5f} puis clôture dessus",
                }
    return None


# --------------------------------------------------------------------------- #
# Mise en correspondance
# --------------------------------------------------------------------------- #


def bias_of(trigger: Trigger, position: Position, structure: Structure) -> tuple[str, str]:
    """Le biais du plan, et pourquoi.

    La règle est celle qu'on enseigne : on n'achète que si la structure est
    haussière, le prix est en bas, et le déclencheur est un rejet acheteur.
    Trois conditions, pas une moyenne de scores.
    """
    if trigger is None:
        return "aucun", "aucun déclencheur sur les niveaux surveillés"

    want = LONG if structure.is_up else SHORT if structure.is_down else None
    if want is None:
        return "aucun", "structure en range : pas de biais directionnel assumé"
    if trigger.direction != want:
        return "aucun", (
            f"le déclencheur est {'acheteur' if trigger.is_long else 'vendeur'} "
            f"alors que la structure est {structure.label}"
        )
    if not position.is_favourable_for(structure.trend):
        return "aucun", (
            f"déclencheur dans le bon sens mais mauvais prix : {position.where}"
        )
    return want, "structure, position et déclencheur alignés"
