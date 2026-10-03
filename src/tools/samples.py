"""
Jeux de données d'exemple pour l'audit et le rendu.

L'onglet d'analyse travaille sur des cours réels, mais l'audit de mise en
page et les tests ont besoin de séries déterministes, sans réseau et sans
dépendance à l'heure du jour. Ce module fabrique donc quelques situations
types, construites pour faire apparaître les cas difficiles :

    * un achat propre (structure, position, rejet, plan complet) ;
    * une vente propre ;
    * un refus pour ratio insuffisant ;
    * un refus faute de structure ;
    * une panne de données.

Ces jeux sont aussi utilisés par les tests : une régression de mise en page
détectée ici l'est aussi là-bas.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from market import analysis as an
from market import levels as lv
from market import pairs as mp
from market import structure as stx
from market.plan import atr, build_plan

EURUSD = mp.get("EURUSD")
USDJPY = mp.get("USDJPY")


# --------------------------------------------------------------------------- #
# Construction de séries
# --------------------------------------------------------------------------- #


def _frame(closes: list[float], freq: str = "15min", wick: float = 0.0004) -> pd.DataFrame:
    """DataFrame OHLC cohérent à partir d'une suite de clôtures."""
    rows = []
    prev = closes[0]
    for c in closes:
        rows.append((prev, max(prev, c) + wick, min(prev, c) - wick, c))
        prev = c
    idx = pd.date_range("2026-01-05 08:00", periods=len(closes), freq=freq)
    return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx)


#: Vague de référence : 5 bougies montantes, 2 de repli, 5 de remontée.
#: C'est la longueur minimale pour que la fractale (2 bougies à gauche, 2 à
#: droite) confirme un sommet ET un creux. En dessous, aucun swing n'est
#: détecté et la structure reste indéterminée — comportement correct, pas un
#: défaut des données.
#: Une période = creux, montée, sommet, repli, creux suivant.
#:
#: La longueur n'est pas libre : deux sommets doivent être espacés d'au moins
#: 5 bougies, sinon la fenêtre de la fractale (+-2) les confond et aucun swing
#: n'est confirmé. D'où 10 bougies par période, sommet au milieu.
#:
#:        0    1    2    3    4    5    6    7    8    9
#: creux  .    .    .    .    .  SOM   .    .    .    .   creux
PERIOD = [0.00, 0.20, 0.40, 0.50, 0.45, 0.55, 0.40, 0.30, 0.25, 0.20]

#: Montée d'une période à la suivante. Doit rester sous 0.05, sinon le creux
#: suivant passe sous le creux précédent et la structure n'est plus haussière.
RISE = 0.04


def uptrend(periods: int = 4, base: float = 1.0000,
            step: float = 0.2000, rise: float = RISE) -> list[float]:
    """Des périodes successives dont les sommets et les creux remontent.

    Chaque période est la précédente remontée de `rise` : les sommets sont
    « plus hauts que les précédents », et les creux aussi. C'est la seule
    configuration que la structure reconnaît comme haussière — un sommet plus
    haut avec un creux plus bas ne suffit pas.

    `base` est le prix de départ, `step` l'amplitude d'une période.
    """
    out: list[float] = []
    for k in range(periods):
        out += [base + (v + k * rise) * step for v in PERIOD]
    return out


def downtrend(periods: int = 4, base: float = 1.0000,
              step: float = 0.2000, rise: float = RISE) -> list[float]:
    """Miroir d'`uptrend` : même motif, excursion vers le bas."""
    up = uptrend(periods, base, step, rise)
    top = max(up)
    return [2 * top - c for c in up]


#: Mèche des bougies d'exemple : assez longue pour être visible, assez courte
#: pour que le corps domine.
WICK = 0.0020


def pullback_to(level: float, from_price: float, bars: int = 12) -> list[float]:
    """Descente régulière de `from_price` jusqu'au niveau `level`."""
    out = []
    for k in range(bars + 1):
        out.append(from_price - (from_price - level) * k / bars)
    return out


def with_rejection(closes: list[float], level: float, depth: float = 0.0030,
                   freq: str = "15min") -> pd.DataFrame:
    """Ajoute à la série une bougie de rejet explicite au niveau donné.

    La bougie ne peut pas être produite par `_frame` : celle-ci dérive la
    mèche de l'écart entre ouverture et clôture, donc une bougie qui monte
    après une descente a un corps long et une mèche courte — l'inverse d'un
    rejet. On construit donc la bougie à la main : petit corps de part et
    d'autre du niveau, mèche qui perce en dessous.
    """
    df = _frame(closes, freq=freq, wick=WICK / 4)
    prev_close = float(closes[-1])
    last = len(df) - 1

    row = df.iloc[last].copy()
    row["Open"] = prev_close
    row["Close"] = level + depth * 0.25
    row["High"] = max(prev_close, row["Close"]) + WICK / 4
    row["Low"] = level - depth  # la mèche perce sous le niveau
    df.iloc[last] = row
    return df


def with_sell_rejection(closes: list[float], level: float, depth: float = 0.0030,
                        freq: str = "15min") -> pd.DataFrame:
    """Rejet vendeur : le miroir de `with_rejection`.

    Corps au-dessus du niveau, mèche qui perce par le haut. On ne l'obtient
    pas en inversant les prix : il faut une remontée préalable, sinon la
    bougie précédente est elle-même en baisse et le motif ne se forme pas.
    """
    df = _frame(closes, freq=freq, wick=WICK / 4)
    prev_close = float(closes[-1])
    last = len(df) - 1

    row = df.iloc[last].copy()
    row["Open"] = prev_close
    row["Close"] = level - depth * 0.25
    row["Low"] = min(prev_close, row["Close"]) - WICK / 4
    row["High"] = level + depth  # la mèche perce au-dessus du niveau
    df.iloc[last] = row
    return df


def spike_past(level: float, distance: float, bars: int = 10) -> list[float]:
    """Remontée qui dépasse `level` de `distance`, puis repli : un balayage."""
    out = []
    for k in range(bars + 1):
        out.append(level - distance * 0.6 * (1 - k / bars))
    out.append(level + distance)
    out.append(level - distance * 0.15)
    return out


def _rejection_at(index: int, price: float, wick: float = 0.0006) -> list[float]:
    """Série qui finit sur un rejet net : mèche longue, clôture au-dessus.

    Le moteur cherche ce motif ; sans lui, le déclencheur reste `None` et le
    plan est refusé — ce qui est correct mais peu parlant sur une image.
    """
    out = [price] * (index + 1)
    out[-1] = price - wick * 3      # la mèche perce
    out[-2] = price                 # clôture au-dessus du niveau
    return out


# --------------------------------------------------------------------------- #
# Rapports d'exemple
# --------------------------------------------------------------------------- #


#: Historique suffisant pour que `data.fetch` accepte la série : le moteur
#: refuse une série trop courte, et c'est le comportement voulu. Les jeux
#: d'exemple doivent donc respecter `data.MIN_BARS`, sinon l'audit testerait
#: autre chose que ce qu'il croit tester.
H1_BARS = 120   # minimum requis : 80
M15_BARS = 72   # minimum requis : 60


def report_long(pair=EURUSD) -> an.Report:
    """Tendance haussière, repli sur le support du H1, rejet, plan d'achat."""
    h1 = _frame(uptrend(periods=H1_BARS // len(PERIOD)), freq="1h", wick=WICK)
    st = stx.read_structure(h1)
    support = st.last_low.price
    m15 = with_rejection(
        pullback_to(support, h1["Close"].iloc[-1], bars=M15_BARS - 1), support
    )
    return an.analyse(pair, h1, m15)


def report_short(pair=EURUSD) -> an.Report:
    """Tendance baissière, rebond sur la résistance du H1, rejet, plan de vente."""
    h1 = _frame(downtrend(periods=H1_BARS // len(PERIOD)), freq="1h", wick=WICK)
    st = stx.read_structure(h1)
    resistance = st.last_high.price
    # rebond depuis le bas du H1 jusqu'à la résistance, puis rejet vendeur
    bottom = float(h1["Low"].iloc[-1])
    m15 = with_sell_rejection(
        pullback_to(resistance, bottom, bars=M15_BARS - 1), resistance
    )
    return an.analyse(pair, h1, m15)


def report_no_rr(pair=EURUSD, min_rr: float = 6.0) -> an.Report:
    """Configuration correcte mais ratio maigre : le moteur doit refuser.

    Le seuil est passé en paramètre : c'est le seul moyen d'obtenir un refus
    *pour ratio* sur des données dont la géométrie est par ailleurs bonne.
    Une image qui montre « le moteur dit non pour la bonne raison » vaut
    mieux qu'une image dont le refus vient d'un détail accidentel.
    """
    h1 = _frame(uptrend(periods=H1_BARS // len(PERIOD)), freq="1h", wick=WICK)
    st = stx.read_structure(h1)
    support = st.last_low.price
    m15 = with_rejection(
        pullback_to(support, h1["Close"].iloc[-1], bars=M15_BARS - 1), support
    )
    report = an.Report(pair=pair, ok=True, df_h1=h1, df_m15=m15, structure=st)
    report.position = stx.read_position(m15, st)
    tr = lv.Trigger(direction=lv.LONG, index=len(m15) - 1,
                    price=support, close=float(m15["Close"].iloc[-1]), wick_ratio=0.7)
    report.trigger = tr
    # un obstacle au-dessus mais collé à l'entrée : le ratio est maigre
    tight = [
        lv.SRLevel(price=support + 0.0020, kind="resistance", touches=3),
        lv.SRLevel(price=support, kind="support", touches=3),
    ]
    report.plan = build_plan(m15, pair, tr, tight, lv.LONG, min_rr=min_rr)
    return report


def report_sweep(pair=EURUSD) -> an.Report:
    """Balayage de liquidité au-dessus du sommet précédent, sans plan."""
    h1 = _frame(uptrend(periods=H1_BARS // len(PERIOD)), freq="1h", wick=WICK)
    st = stx.read_structure(h1)
    m15 = _frame(spike_past(st.last_high.price, 0.0060, bars=M15_BARS - 2),
                 freq="15min", wick=WICK)
    return an.analyse(pair, h1, m15)


def report_flat(pair=EURUSD) -> an.Report:
    """Série sans structure lisible : rien à dire, et c'est une réponse."""
    flat = [1.0500] * H1_BARS
    return an.analyse(pair, _frame(flat, freq="1h"),
                      _frame([1.0500] * M15_BARS, freq="15min"))


def report_jpy() -> an.Report:
    """Le même cas sur une paire en JPY : 3 décimales, pip à 0.01."""
    # échelle JPY : 100 « unités » de uptrend valent environ 10 yens
    h1 = _frame(uptrend(periods=H1_BARS // len(PERIOD), base=145.00, step=0.60),
                freq="1h", wick=0.05)
    st = stx.read_structure(h1)
    support = st.last_low.price
    m15 = with_rejection(
        pullback_to(support, h1["Close"].iloc[-1], bars=M15_BARS - 1),
        support, depth=0.06,
    )
    return an.analyse(USDJPY, h1, m15)


def report_error(pair=EURUSD) -> an.Report:
    """Panne de données : l'onglet doit l'afficher telle quelle."""
    return an.failed(pair, "EURUSD H1 : historique indisponible sur cette unité de temps.")


def SAMPLE_REPORTS() -> list[an.Report]:  # noqa: N802 — utilisé par l'audit
    """Tous les cas d'exemple, dans l'ordre où l'audit les affiche."""
    return [
        report_long(),
        report_short(),
        report_no_rr(),
        report_sweep(),
        report_flat(),
        report_jpy(),
        report_error(),
    ]


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    for r in SAMPLE_REPORTS():
        print(f"{r.pair.symbol:9s} {r.plan.headline()}")
        for line in r.context_lines():
            print(f"          {line}")
        for b in r.plan.blocks:
            print(f"          ! {b}")
        print()
