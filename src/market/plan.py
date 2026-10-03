"""
Plan de trade : entrée, stop, cible, ratio de risque.

Ce que ce module apporte, et que l'ancien moteur n'avait pas :

  * **l'entrée est la zone, pas le prix du moment.** L'ancien moteur entrait
    toujours au prix courant, donc hors de la zone qu'il venait d'identifier.

  * **le stop est structurel.** Il se pose au-delà du niveau qui invalide
    l'idée, plus une marge. L'ancien moteur mettait toujours 1.5 × ATR et la
    cible 2.5 × ATR : le ratio revenait à 1.67 sur tous les trades, ce qui
    est une information, pas une analyse.

  * **la cible est le prochain obstacle réel.** On vise la liquidité ou la
    résistance qui se trouve devant, pas un multiple d'ATR.

  * **un plan refusé est un plan refusé.** Si le ratio est trop maigre, le
    moteur renvoie « pas de trade » au lieu d'imposer un trade médiocre.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .levels import LONG, SRLevel, Trigger, nearest
from .measure import atr  # noqa: F401 — `plan.atr` reste une entrée connue

#: Marge ajoutée au-delà du niveau d'invalidation, en fraction de l'ATR.
STOP_MARGIN_ATR = 0.35

#: Ratio risque/récompense minimal en dessous duquel on refuse le trade.
MIN_RR = 2.0

#: Un stop plus large que ce multiple de l'amplitude typique n'est plus un
#: stop structurel, c'est une mise d'argent exposée.
#:
#: Ce seuil était d'abord exprimé en pips, ce qui était une erreur : 90 pips
#: est un arrêt raisonnable en intraday et une absurdité en daily, où une seule
#: bougie se déplace de 60 à 80 pips. Exprimé en amplitude, le même seuil
#: garde son sens sur toutes les unités de temps — et il redevient vrai quand
#: le marché change de régime.
MAX_STOP_ATR = 2.5

#: Symétriquement, une cible plus loin que ce multiple de l'amplitude n'est pas
#: une cible, c'est un scénario.
#:
#: Sur une fenêtre daily de cinq ans, le sommet suivant est parfois à quatre
#: cents pips. Le viser afficherait un ratio spectacular — 12 contre 1 — et
#: laisserait croire à une opération de la semaine. Or un plan se juge à
#: l'horizon qu'il engage : au-delà de ce seuil, ce n'est pas un trade, c'est
#: une position tenue pendant des mois, et elle se décide autrement.
MAX_TARGET_ATR = 8.0

#: Décisions.
BUY = "ACHAT"
SELL = "VENTE"
WAIT = "ATTENDRE"


@dataclass
class Plan:
    """Un plan de trade complet, ou un refus motivé."""

    decision: str = WAIT
    entry: float | None = None
    stop: float | None = None
    target: float | None = None
    rr: float | None = None
    stop_pips: float | None = None
    digits: int = 5
    reasons: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)

    @property
    def actionable(self) -> bool:
        return self.decision in (BUY, SELL) and self.entry is not None

    @property
    def is_long(self) -> bool:
        return self.decision == BUY

    def headline(self) -> str:
        if not self.actionable:
            return WAIT
        fmt = f"{{:.{self.digits}f}}"
        return (f"{self.decision} @ {fmt.format(self.entry)} — "
                f"stop {fmt.format(self.stop)} — cible {fmt.format(self.target)}")

    def to_dict(self) -> dict:
        """Version sérialisable (cache, export, tests)."""
        return {
            "decision": self.decision,
            "entry": self.entry,
            "stop": self.stop,
            "target": self.target,
            "rr": self.rr,
            "stop_pips": self.stop_pips,
            "reasons": list(self.reasons),
            "blocks": list(self.blocks),
        }


def _obstacle(levels: list[SRLevel], price: float, direction: str) -> SRLevel | None:
    """Le premier obstacle *vivant* dans le sens du trade.

    Vif, c'est-à-dire retesté depuis sa formation. Viser une résistance que le
    prix n'a plus approchée depuis quatre mois reviendrait à afficher un ratio
    flatteur calculé sur un obstacle imaginaire.
    """
    if direction == LONG:
        ahead = [lv for lv in levels
                 if lv.kind == "resistance" and lv.alive and lv.price > price]
    else:
        ahead = [lv for lv in levels
                 if lv.kind == "support" and lv.alive and lv.price < price]
    if not ahead:
        return None
    return min(ahead, key=lambda lv: abs(lv.price - price))


def build_plan(
    df: pd.DataFrame,
    pair,
    trigger: Trigger,
    levels: list[SRLevel],
    direction: str,
    min_rr: float = MIN_RR,
) -> Plan:
    """Construit le plan, ou explique pourquoi il n'y en a pas.

    `pair` sert à convertir les écarts en pips : sans ça, « 25 pips » n'a pas
    de sens sur du JPY et « 2500 pips » non plus sur une paire à 4 décimales.
    """
    plan = Plan(decision=WAIT, digits=pair.digits)
    if direction not in (LONG, "short"):
        return plan

    price = float(df["Close"].iloc[-1])
    a = atr(df)
    if a <= 0:
        plan.blocks.append("ATR nul : les bougies sont plates, aucun plan n'est calculable.")
        return plan

    # --- entrée : le niveau lui-même, en ordre limite
    # C'est la correction principale : l'ancien moteur entrait au prix du
    # moment, donc en dehors de la zone qu'il venait d'identifier, et payait
    # un prix que personne n'aurait choisi. Ici on entre sur le niveau, ce qui
    # est ce que l'analyse annonce et ce que l'écran affiche.
    entry = trigger.price

    # Une limite n'est posable que si le prix n'est pas déjà parti sans nous.
    # Au-delà d'une bougie d'ATR d'écart, on ne propose plus l'entrée : on
    # propose d'attendre un nouveau rejet, ce que le moteur fera au prochain
    # calcul.
    gap = (price - entry) if direction == LONG else (entry - price)
    if gap > a:
        fmt = f"{{:.{pair.digits}f}}"
        plan.blocks.append(
            f"le prix est déjà {pair.pips(gap):.0f} pips au-delà du niveau "
            f"{fmt.format(entry)} : l'entrée n'est plus honorable, on attend un "
            f"nouveau rejet."
        )
        return plan

    # --- stop : au-delà du niveau invalidé, plus la marge d'ATR
    margin = a * STOP_MARGIN_ATR
    if direction == LONG:
        stop = trigger.price - margin
    else:
        stop = trigger.price + margin
    risk = abs(entry - stop)
    if risk <= 0:
        plan.blocks.append("risque nul : l'entrée est sur le stop.")
        return plan

    stop_pips = pair.pips(risk)
    if risk > a * MAX_STOP_ATR:
        plan.blocks.append(
            f"stop de {stop_pips:.0f} pips, soit {risk / a:.1f} fois l'amplitude "
            f"habituelle : au-delà de {MAX_STOP_ATR:.1f}, ce n'est plus un stop "
            f"structurel mais une mise d'argent exposée."
        )
        return plan

    # --- cible : le premier obstacle réel devant le prix
    obstacle = _obstacle(levels, price, direction)
    if obstacle is None:
        plan.blocks.append(
            "aucun obstacle devant le prix : pas de cible identifiable, donc pas de ratio."
        )
        return plan
    target = obstacle.price

    reward = abs(target - entry)
    if reward > a * MAX_TARGET_ATR:
        plan.blocks.append(
            f"cible à {pair.pips(reward):.0f} pips, soit {reward / a:.0f} fois "
            f"l'amplitude habituelle : au-delà de {MAX_TARGET_ATR:.0f}, ce n'est "
            f"pas un trade mais une position tenue pendant des mois. Elle se "
            f"décide sur une autre échelle."
        )
        return plan

    rr = reward / risk
    plan.entry, plan.stop, plan.target = entry, stop, target
    plan.rr, plan.stop_pips = rr, stop_pips

    if rr < min_rr:
        fmt = f"{{:.{pair.digits}f}}"
        plan.blocks.append(
            f"ratio de {rr:.2f} insuffisant : il faudrait {min_rr:.1f} pour que "
            f"l'espérance soit positive. L'obstacle à {fmt.format(target)} est "
            f"trop proche."
        )
        plan.entry = plan.stop = plan.target = None
        plan.rr = None
        return plan

    plan.decision = BUY if direction == LONG else SELL
    fmt = f"{{:.{pair.digits}f}}"
    plan.reasons.append(
        f"ratio risque/récompense {rr:.2f} pour {stop_pips:.0f} pips de risque."
    )
    plan.reasons.append(
        f"cible placée sur le {obstacle.label()} à {fmt.format(target)}, "
        f"premier obstacle vivant devant le prix."
    )
    plan.reasons.append(
        f"stop {stop_pips:.0f} pips au-delà du niveau {fmt.format(trigger.price)}, "
        f"marge d'amplitude comprise."
    )
    return plan


def no_plan(why: str) -> Plan:
    """Un plan explicite qui refuse, avec la raison."""
    plan = Plan(decision=WAIT)
    plan.blocks.append(why)
    return plan


def nearest_support(levels: list[SRLevel], price: float) -> SRLevel | None:
    return nearest(levels, price, "support")


def nearest_resistance(levels: list[SRLevel], price: float) -> SRLevel | None:
    return nearest(levels, price, "resistance")
