"""
Analyse d'une paire : le fil qui relie les briques en un rapport lisible.

`analyse` est la seule porte d'entrée de l'onglet d'analyse. Elle prend des
DataFrames, pas un nom de paire : le réseau se décide en amont (`data.fetch`),
ce qui rend cette fonction pure et testable hors ligne.

Elle renvoie un `Report` qui contient à la fois :

  * le **verdict** (`Plan`) — ce qu'il faut faire, ou pourquoi on ne fait rien ;
  * le **contexte** (structure, position, niveaux, balayage) — ce qui a servi
    à décider ;
  * une **`Scene`** du modèle pédagogique, pour que l'onglet d'analyse
    s'affiche dans le même canevas que les leçons.

C'est le point important du raccord : le graphe de l'analyse n'est pas un
widget de plus, c'est une scène comme les autres. Les annotations du verdict
sont donc des `Level`, `Marker`, `Path` — les mêmes objets que dans les leçons.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from core.model import Candle, Level, Marker, Path, Scene, Step

from . import levels as lv
from . import structure as stx
from .pairs import Pair
from .plan import BUY, Plan, SELL, WAIT, build_plan, no_plan

#: Nombre de bougies affichées dans l'onglet d'analyse.
VISIBLE_BARS = 90

#: Deux prix sont « le même » en dessous cette différence. Utile pour ne pas
#: afficher deux fois le même niveau : l'entrée du plan est posée sur un niveau,
#: la cible sur un obstacle, et ces prix sont identiques à une marge près.
SAME_PRICE = 1e-9

#: Décalage vertical des étiquettes du plan, en pixels. Deux fois la hauteur
#: d'une étiquette (environ 13 px en Segoe UI 8), ce qui les sépare sans
#: éloigner l'étiquette de sa ligne.
TAG_DY = 14.0


def _close(a: float | None, b: float | None) -> bool:
    """Ces deux prix désignent-ils le même niveau ?"""
    if a is None or b is None:
        return False
    return abs(a - b) <= max(SAME_PRICE, abs(a) * 1e-6)


@dataclass
class Report:
    """Tout ce que l'onglet d'analyse affiche pour une paire."""

    pair: Pair
    ok: bool = False
    error: str = ""
    timeframe: str = "D1"
    plan: Plan = field(default_factory=Plan)
    structure: stx.Structure = field(default_factory=stx.Structure)
    position: stx.Position = field(default_factory=stx.Position)
    sr: list[lv.SRLevel] = field(default_factory=list)
    trigger: lv.Trigger | None = None
    sweep: dict | None = None
    df: pd.DataFrame | None = None

    @property
    def decision(self) -> str:
        return self.plan.decision

    @property
    def is_long(self) -> bool:
        return self.decision == BUY

    @property
    def is_short(self) -> bool:
        return self.decision == SELL

    @property
    def waiting(self) -> bool:
        return self.decision == WAIT

    def context_lines(self) -> list[str]:
        """Le contexte, en français, pour le panneau latéral.

        Chaque niveau est annoncé avec sa distance au prix. C'est la seule façon
        de distinguer un support où l'on peut réellement poser un ordre d'un
        souvenir de cours situé trois cents pips plus bas : les deux se lisent
        « support », et ils ne se valent pas.
        """
        if not self.ok:
            return []
        fmt = f"{{:.{self.pair.digits}f}}"
        lines = [
            f"Structure : {self.structure.describe()}",
            f"Position : {self.position.describe(fmt)}",
        ]
        for level in self.sr:
            away = self.pair.pips(abs(level.price - self.position.price))
            lines.append(
                f"{level.label()} à {fmt.format(level.price)} — {away:.0f} pips"
            )
        if self.trigger:
            lines.append(f"Déclencheur : {self.trigger.describe(fmt)}")
        else:
            lines.append("Déclencheur : aucun rejet récent sur ces niveaux.")
        if self.sweep:
            lines.append(f"Balayage de liquidité : {self.sweep['why']}.")
        return lines

    def verdict_lines(self) -> list[str]:
        """Le verdict et ses raisons, pour le panneau latéral."""
        if not self.ok:
            return []
        out = [f"<b>{self.plan.headline()}</b>"]
        for r in self.plan.reasons:
            out.append(f"— {r}")
        for b in self.plan.blocks:
            out.append(f"— {b}")
        return out

    def to_scene(self) -> Scene:
        """La même analyse, comme scène du modèle pédagogique."""
        pair = self.pair
        scene = Scene(
            id=f"analyse-{pair.symbol}",
            title=f"Analyse {pair.symbol} — {pair.name}",
            principle=(
                "Structure d'abord, position ensuite, déclencheur en dernier. "
                "Si l'un des trois manque, il n'y a pas de plan."
            ),
            digits=pair.digits,
        )
        if not self.ok or self.df is None:
            scene.at(Step(
                title="Données indisponibles",
                text=self.error or "Aucune donnée exploitable pour cette paire.",
            ))
            return scene

        df = self.df
        offset = max(0, len(df) - VISIBLE_BARS)
        window = df.iloc[offset:]
        base = offset  # index du dataframe, pour dater les annotations

        for i, (ts, row) in enumerate(window.iterrows()):
            scene.candles.append(Candle(
                o=float(row["Open"]), h=float(row["High"]),
                l=float(row["Low"]), c=float(row["Close"]),
            ))

        n = len(scene.candles) - 1

        # --- niveaux de structure
        #
        # Quand un plan existe, on n'affiche PAS le niveau dont il est issu :
        # l'entrée est posée dessus et la cible sur l'obstacle, donc afficher
        # les deux drewait deux étiquettes sur la même ligne — deux fois la
        # même information, à des pixels d'écart. Le plan reprend le libellé
        # du niveau (« cible — 4 contacts ») pour ne rien perdre.
        entry = self.plan.entry if self.plan.actionable else None
        target = self.plan.target if self.plan.actionable else None
        stop = self.plan.stop if self.plan.actionable else None

        for level in self.sr:
            if _close(level.price, entry) or _close(level.price, target):
                continue  # ce niveau est déjà représenté par une ligne du plan
            if _close(level.price, stop):
                continue
            if not self._in_view(level.price, window):
                continue  # hors de la fenêtre : le dessiner déformerait l'échelle
            scene.add(Level(
                price=level.price,
                label=level.label(),
                kind=level.kind,
                start=0,
                end=n,
            ))

        # --- déclencheur
        if self.trigger is not None:
            i = self.trigger.index - base
            if 0 <= i <= n:
                kind = "good" if self.trigger.is_long else "bad"
                scene.add(Marker(
                    index=i,
                    price=float(window["High"].iloc[i]) + (self._tick() if self.trigger.is_long else -self._tick()),
                    text="rejet" + (" acheteur" if self.trigger.is_long else " vendeur"),
                    kind=kind,
                ))

        # --- plan
        #
        # Les étiquettes entrée / stop / cible sont décalées verticalement.
        # Sur un plan réel elles sont séparées de quelques dizaines de pips,
        # soit 5 à 10 pixels à l'écran : leurs étiquettes se toucheraient
        # donc. Le décalage est en pixels — c'est la seule unité dans laquelle
        # le problème existe — et il vaut deux fois la hauteur d'une étiquette,
        # ce qui les sépare quelle que soit la taille de la fenêtre.
        if self.plan.actionable:
            scene.add(
                Level(price=self.plan.entry, label="entrée", kind="entry",
                      start=0, end=n, tag_dy=-TAG_DY),
                Level(price=self.plan.stop, label="stop", kind="stop",
                      start=0, end=n, tag_dy=+TAG_DY),
                Level(price=self.plan.target, label=self._target_label(), kind="target",
                      start=0, end=n, tag_dy=-TAG_DY),
            )
        else:
            # Le verdict « rien à faire » est posé à gauche, sur le prix de la
            # première bougie : le rejet, lui, reste sur la bougie qui l'a
            # produit. Deux marqueurs au même endroit seraient illisibles, et
            # les confondrait en un seul.
            scene.add(Marker(
                index=0,
                price=float(window["High"].iloc[0]),
                text="aucun trade",
                kind="warn",
            ))

        scene.at(*self._steps())
        scene.takeaway = self._takeaway()
        return scene

    # ------------------------------------------------------------------ privé
    def _in_view(self, price: float, window: pd.DataFrame) -> bool:
        """Ce prix est-il dans la fenêtre affichée ?

        Sur cinq ans de daily, un niveau peut se trouver à plusieurs milliers de
        pips du dernier prix. Le dessiner ne le rend pas plus informatif : cela
        élargit l'échelle jusqu'à écraser les bougies, qui sont la seule chose
        que l'écran doit montrer. Un niveau hors fenêtre reste dans le panneau
        latéral, avec sa distance — c'est là qu'on le consulte.
        """
        low = float(window["Low"].min())
        high = float(window["High"].max())
        return low <= price <= high

    def _tick(self) -> float:
        """Une hauteur proportionnelle au prix affiché, pour les marqueurs.

        En prix : les marqueurs (rejet, verdict) sont posés sur une bougie, et
        ce qui compte est de les garder dans le cadre du graphe.
        """
        span = self.position.span or abs(self.position.price) * 0.0005
        return span * 0.018

    def _target_label(self) -> str:
        """Le libellé de la cible, complété par le nombre de contacts.

        La cible est posée sur l'obstacle réel. Sans cette information, on
        perdrait ce que l'analyse sait de cet obstacle — et l'analyse
        remplacerait le graphique au lieu de l'expliquer.
        """
        if not self.plan.actionable:
            return "cible"
        target = self.plan.target
        for level in self.sr:
            if _close(level.price, target):
                return f"cible — {level.touches} contacts"
        return "cible"

    def _steps(self) -> list[Step]:
        """Les étapes de révélation, dans l'ordre du raisonnement."""
        fmt = f"{{:.{self.pair.digits}f}}"
        out = [
            Step(
                title="1. La structure",
                text=self.structure.describe(),
            ),
            Step(
                title="2. La position",
                text=self.position.describe(fmt),
            ),
        ]
        if self.trigger:
            out.append(Step(title="3. Le déclencheur", text=self.trigger.describe(fmt)))
        else:
            out.append(Step(
                title="3. Le déclencheur",
                text="Aucune bougie récente n'a rejeté un niveau avec une mèche "
                     "suffisante. Sans cela, la structure ne donne qu'un contexte, "
                     "pas une entrée.",
            ))
        if self.plan.actionable:
            out.append(Step(
                title="4. Le plan",
                text=(f"{self.plan.headline()}\n\n"
                      + "\n".join(self.plan.reasons)),
            ))
        else:
            why = "\n".join(self.plan.blocks) or "aucune condition remplie"
            out.append(Step(
                title="4. Le plan",
                text=f"On n'engage rien.\n\n{why}",
            ))
        return out

    def _takeaway(self) -> str:
        if self.plan.actionable:
            return (f"Structure {self.structure.label}, prix {self.position.where}, "
                    f"rejet dans le bon sens : le plan tient avec un ratio de "
                    f"{self.plan.rr:.2f}.")
        return (f"Aucun trade ici — {self.plan.blocks[0] if self.plan.blocks else ''}. "
                f"Un plan qu'on refuse est un plan qui vaut de l'argent.")


# --------------------------------------------------------------------------- #
# Analyse
# --------------------------------------------------------------------------- #


def analyse(
    pair: Pair,
    df: pd.DataFrame,
    timeframe: str = "D1",
) -> Report:
    """Analyse structurelle d'une paire. Pur : aucun accès réseau.

    Une seule série, une seule unité de temps. C'est délibéré : la structure,
    les niveaux, le déclencheur et le plan sont lus sur le même jeu de bougies,
    de sorte que l'image affichée et le verdictquilConcernent ne peuvent pas
    diverger.
    """
    report = Report(pair=pair, ok=True, df=df, timeframe=timeframe)

    # 1. structure — c'est là que la tendance se lit
    report.structure = stx.read_structure(df)
    # 2. position — où le prix se trouve entre le dernier creux et le sommet
    report.position = stx.read_position(df, report.structure)
    # 3. niveaux — les prix où le marché a déjà changé d'avis
    report.sr = lv.sr_levels(df, report.structure)
    report.sweep = lv.sweep_of_liquidity(df, report.structure)

    # 4. déclencheur — ce que le prix fait maintenant
    report.trigger = lv.find_trigger(df, report.sr)

    if not report.structure.has_enough:
        report.plan = no_plan(report.structure.describe())
        return report

    # 5. biais : les trois conditions doivent être réunies
    bias, why = lv.bias_of(report.trigger, report.position, report.structure)
    if bias == "aucun":
        report.plan = no_plan(why)
        return report

    # 4. plan chiffré
    report.plan = build_plan(df, pair, report.trigger, report.sr, bias)
    return report


def failed(pair: Pair, message: str) -> Report:
    """Un rapport d'échec, affichable tel quel."""
    return Report(pair=pair, ok=False, error=message)


__all__ = [
    "Report",
    "analyse",
    "failed",
    "VISIBLE_BARS",
    "BUY",
    "SELL",
    "WAIT",
]
