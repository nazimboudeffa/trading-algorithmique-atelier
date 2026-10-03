"""
Structure de marché : sommets, creux, tendance, position du prix.

C'est la brique qui remplace l'empilement d'indicateurs. Un indicateur
mélange tout ; un sommet et un creux ne demandent qu'une chose à voir : « le
prix a-t-il monté plus haut que la fois précédente, ou moins haut ? ».

Trois notions, dans cet ordre :

    1. les swings  — sommets et creux confirmés (fractales) ;
    2. la structure — sommet plus haut + creux plus haut : tendance haussière ;
                    sommet moins haut + creux moins bas : tendance baissière ;
                    le reste : range, donc on ne cherche pas de tendance ;
    3. la position  — où le prix se trouve entre le dernier creux et le dernier
                    sommet. C'est ce qui décide du *sens* ; la structure
                    décide de la *force*.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .measure import median_range

#: Fenêtre de confirmation d'un swing. 3 de chaque côté : à 2, chaque wiggle
#: du M15 devient un sommet, et une « structure » ainsi construite ne dit
#: plus rien — c'est le bruit, dessiné au crayon.
SWING_LEFT = 3
SWING_RIGHT = 3

#: Un swing ne compte comme sommet ou creux *structurel* que si le prix s'est
#: éloigné d'au moins ce multiple de l'amplitude typique depuis le dernier swing
#: retenu.
#:
#: C'est le filtre qui fait toute la différence entre une lecture de marché et
#: une énumération de bosses. Sur du H1 réel, une fractale à 3 bougies produit
#: un sommet tous les 4 chandeliers ; comparés entre eux, ils ne disent rien.
#:
#: Le choix de 5 se lit ainsi : un sommet que le marché aurait produit en
#: moins de cinq bougies ne marque aucun changement d'avis, et cinq bougies
#: constituent déjà une décision. Mesuré sur cinq paires réelles, ce seuil
#: laisse 30 à 90 swings structurels pour trois mois de H1 — soit un sommet
#: tous les vingt à cinquante chandeliers, ce qui se regarde sur un graphique.
MIN_SWING_ATR = 5.0

#: Positions possibles du prix dans l'enveloppe de structure.
ABOVE = "au-dessus de l'enveloppe"
BELOW = "en dessous de l'enveloppe"
TOP = "haut du range"
MIDDLE = "milieu du range"
BOTTOM = "bas du range"

#: Tendances.
UP = "haussiere"
DOWN = "baissiere"
RANGE = "range"


@dataclass(frozen=True)
class Swing:
    """Un sommet ou un creux confirmé."""

    index: int
    price: float
    kind: str  # "high" | "low"

    @property
    def is_high(self) -> bool:
        return self.kind == "high"


@dataclass
class Structure:
    """Ce que l'on peut dire de la structure à un instant donné."""

    trend: str = RANGE
    label: str = "structure indetermined"
    reason: str = ""
    swings: list[Swing] = field(default_factory=list)
    last_high: Swing | None = None
    last_low: Swing | None = None
    prev_high: Swing | None = None
    prev_low: Swing | None = None

    @property
    def is_up(self) -> bool:
        return self.trend == UP

    @property
    def is_down(self) -> bool:
        return self.trend == DOWN

    @property
    def is_range(self) -> bool:
        return self.trend == RANGE

    @property
    def has_enough(self) -> bool:
        """Faut-il deux sommets ET deux creux pour conclure."""
        return all(s is not None for s in (self.last_high, self.prev_high,
                                           self.last_low, self.prev_low))

    def describe(self) -> str:
        """Une phrase, en français, utilisable directement dans l'interface."""
        if not self.has_enough:
            return (
                "Structure indéterminée : il manque des sommets ou des creux "
                "confirmés. On n'analyse pas une structure qu'on ne voit pas."
            )
        return f"{self.label} — {self.reason}"


# --------------------------------------------------------------------------- #
# Swings
# --------------------------------------------------------------------------- #


def find_swings(df: pd.DataFrame, left: int = SWING_LEFT, right: int = SWING_RIGHT) -> list[Swing]:
    """Sommet / creux confirmés par fractale.

    Un sommet en i est confirmé quand `high[i]` est le plus haut des `left+1`
    bougies qui le précèdent et des `right+1` qui le suivent. Les `right`
    bougies de retard sont le prix de la confirmation : sans elles, un sommet
    n'est confirmé qu'après coup, et on travaille dans le futur.
    """
    n = len(df)
    if n < left + right + 1:
        return []

    highs = df["High"].to_numpy()
    lows = df["Low"].to_numpy()
    out: list[Swing] = []

    for i in range(left, n - right):
        window_h = highs[i - left : i + right + 1]
        if highs[i] == window_h.max() and (window_h.argmax() == left):
            out.append(Swing(index=i, price=float(highs[i]), kind="high"))
        window_l = lows[i - left : i + right + 1]
        if lows[i] == window_l.min() and (window_l.argmin() == left):
            out.append(Swing(index=i, price=float(lows[i]), kind="low"))

    out.sort(key=lambda s: s.index)
    return out


def _alternate(pivots: list[Swing]) -> list[Swing]:
    """Impose l'alternance sommet / creux / sommet / creux.

    Sans cette étape, la fractale renvoie `haut@1550, haut@1554, bas@1564` :
    deux sommets séparés par quatre bougies, dont le second est plus bas que
    le premier. Comparer 1550 et 1554 n'a aucun sens — aucun creux n'est passé
    entre les deux. Une structure se lit sur une suite alternée, et seulement
    sur elle.

    Quand deux swings du même type se suivent, on garde le plus extrême : c'est
    lui qui a donné le plus d'information au marché.
    """
    out: list[Swing] = []
    for p in pivots:
        if out and out[-1].kind == p.kind:
            previous = out[-1]
            better = (
                p.price > previous.price if p.is_high else p.price < previous.price
            )
            if better:
                out[-1] = p
        else:
            out.append(p)
    return out


def _more_extreme(a: Swing, b: Swing) -> bool:
    """`a` est-il plus frappant que `b` ? Un sommet plus haut, un creux plus bas."""
    return a.price > b.price if a.is_high else a.price < b.price


def _prominent(sequence: list[Swing], threshold: float) -> list[Swing]:
    """Ne garde que les swings qui ont vraiment déplacé le prix.

    On parcourt la suite alternée et on ne retient un swing que s'il s'est
    éloigné d'au moins `threshold` du dernier swing retenu. C'est un filtre de
    direction : au-delà d'un certain mouvement, on change d'avis, en dessous on
    considère que ce n'est pas un nouveau sommet.

    Un point de méthode, qui a coûté un bug : quand un swing est écarté, la
    suite doit rester alternée. Il ne suffit pas de l'enlever — le swing suivant,
    du même type que celui qui reste, viendrait alors suivre un sommet sans
    creux intermédiaire, et la comparaison « sommet plus haut / sommet plus bas »
    n'aurait plus aucun sens. On remplace donc le dernier swing retenu quand le
    nouveau est plus extrême, et on ignore les mouvements trop courts.
    """
    kept: list[Swing] = []
    for s in sequence:
        if not kept:
            kept.append(s)
            continue

        last = kept[-1]
        if s.kind == last.kind:
            # même type : on ne garde que le plus extrême des deux
            if _more_extreme(s, last):
                kept[-1] = s
            continue

        if abs(s.price - last.price) >= threshold:
            kept.append(s)
        # sinon le mouvement est trop court : on l'ignore, et le prochain swing
        # de même type que `last` sera comparé à `last`, pas à celui-ci.
    return kept


def structure_swings(
    df: pd.DataFrame,
    left: int = SWING_LEFT,
    right: int = SWING_RIGHT,
    min_swing_atr: float = MIN_SWING_ATR,
) -> list[Swing]:
    """Les swings qui définissent la structure : alternés et significatifs.

    C'est cette liste, et non `find_swings`, qui sert à lire la tendance. La
    différence sur du H1 réel est de un ordre de grandeur : 423 bosses brutes
    contre 40 sommets et creux comparables.
    """
    raw = _alternate(find_swings(df, left, right))
    if len(raw) < 2:
        return raw
    typical = median_range(df)
    if typical <= 0:
        return raw  # données plates : on ne peut pas filtrer, on garde tout
    return _prominent(raw, typical * min_swing_atr)


def _last_two(swings: list[Swing], kind: str) -> tuple[Swing | None, Swing | None]:
    """Les deux derniers swings d'un type, du plus ancien au plus récent."""
    picked = [s for s in swings if s.kind == kind]
    if len(picked) < 2:
        return (picked[-1] if picked else None), None
    return picked[-2], picked[-1]


# --------------------------------------------------------------------------- #
# Structure
# --------------------------------------------------------------------------- #


def read_structure(
    df: pd.DataFrame,
    left: int = SWING_LEFT,
    right: int = SWING_RIGHT,
    min_swing_atr: float = MIN_SWING_ATR,
) -> Structure:
    """Détermine la tendance à partir des swings structurels."""
    swings = structure_swings(df, left, right, min_swing_atr)
    prev_high, last_high = _last_two(swings, "high")
    prev_low, last_low = _last_two(swings, "low")

    st = Structure(
        swings=swings,
        last_high=last_high,
        last_low=last_low,
        prev_high=prev_high,
        prev_low=prev_low,
    )

    if not st.has_enough:
        st.label = "structure indéterminée"
        st.reason = "moins de deux sommets ou deux creux confirmés"
        return st

    hh = last_high.price > prev_high.price
    hl = last_low.price > prev_low.price
    lh = last_high.price < prev_high.price
    ll = last_low.price < prev_low.price

    if hh and hl:
        st.trend = UP
        st.label = "sommets et creux plus hauts (HH + HL)"
        st.reason = (
            f"le sommet passe de {_px(prev_high.price)} à {_px(last_high.price)} "
            f"et le creux de {_px(prev_low.price)} à {_px(last_low.price)}"
        )
    elif lh and ll:
        st.trend = DOWN
        st.label = "sommets et creux plus bas (LH + LL)"
        st.reason = (
            f"le sommet recule de {_px(prev_high.price)} à {_px(last_high.price)} "
            f"et le creux de {_px(prev_low.price)} à {_px(last_low.price)}"
        )
    else:
        st.trend = RANGE
        st.label = "range (pas de tendance nette)"
        if hh and not hl:
            st.reason = (
                f"sommet plus haut ({_px(last_high.price)}) mais creux plus bas "
                f"({_px(last_low.price)}) que le précédent — la hausse n'a pas "
                f"de point d'appui"
            )
        elif lh and not ll:
            st.reason = (
                f"sommet plus bas ({_px(last_high.price)}) mais creux plus haut "
                f"({_px(last_low.price)}) que le précédent — la baisse n'a pas "
                f"de point d'appui"
            )
        elif not hh and not hl:
            st.reason = (
                f"le sommet recule ({_px(last_high.price)}) sans que le creux "
                f"remonte ({_px(last_low.price)}) : pas de reprise"
            )
        else:
            st.reason = (
                f"sommet et creux progressent dans le même sens "
                f"({_px(last_high.price)} / {_px(last_low.price)}) : le marché "
                f"n'est pas tranché"
            )
    return st


def _px(price: float) -> str:
    """Formatage court, suffisant pour une phrase d'explication."""
    return f"{price:.5f}"


# --------------------------------------------------------------------------- #
# Position du prix
# --------------------------------------------------------------------------- #


@dataclass
class Position:
    """Où se trouve le prix par rapport à l'enveloppe de structure."""

    where: str = MIDDLE
    low: float = 0.0
    high: float = 0.0
    price: float = 0.0
    ratio: float = 0.5  # 0 = sur le creux, 1 = sur le sommet

    @property
    def span(self) -> float:
        return self.high - self.low

    def is_favourable_for(self, trend: str) -> bool:
        """Le prix est-il du bon côté pour jouer dans le sens de la tendance ?

        Acheter une tendance haussière se fait en bas du range, vendre une
        tendance baissière se fait en haut. C'est la position qui rend le
        risque asymétrique.
        """
        if trend == UP:
            return self.where in (BOTTOM, BELOW)
        if trend == DOWN:
            return self.where in (TOP, ABOVE)
        return False

    def describe(self, fmt: str = "{:.5f}") -> str:
        """Une phrase, en français, utilisable telle quelle dans l'interface.

        Le format est injectable parce que ce module ignore tout des paires :
        c'est l'appelant, qui connaît le nombre de décimales, qui décide. Écrire
        157.32200 sur une paire cotée à trois décimales ferait croire à une
        précision que le marché n'a pas.
        """
        price = fmt.format(self.price)
        low = fmt.format(self.low)
        high = fmt.format(self.high)
        if self.where == ABOVE:
            return f"{self.where} — le prix {price} dépasse le sommet {high}"
        if self.where == BELOW:
            return f"{self.where} — le prix {price} passe sous le creux {low}"
        return f"{self.where} — le prix {price} se situe entre {low} et {high}"


def read_position(df: pd.DataFrame, st: Structure) -> Position:
    """Situe le dernier cours dans l'enveloppe [dernier creux, dernier sommet].

    Le prix peut être en dehors de l'enveloppe : c'est le cas le plus
    intéressant après une cassure, et il ne faut pas le tronquer.
    """
    price = float(df["Close"].iloc[-1])
    low = st.last_low.price if st.last_low else float(df["Low"].min())
    high = st.last_high.price if st.last_high else float(df["High"].max())
    if high < low:
        low, high = high, low

    pos = Position(low=low, high=high, price=price)
    span = pos.span
    if span <= 0:
        pos.where = MIDDLE
        return pos

    pos.ratio = (price - low) / span
    if price > high:
        pos.where = ABOVE
    elif price < low:
        pos.where = BELOW
    elif pos.ratio >= 0.66:
        pos.where = TOP
    elif pos.ratio <= 0.34:
        pos.where = BOTTOM
    else:
        pos.where = MIDDLE
    return pos
