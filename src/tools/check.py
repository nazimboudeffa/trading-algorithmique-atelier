"""
Le moteur sur les cours réels.

Passe en revue les paires choisies et affiche le raisonnement complet, tel
que l'onglet d'analyse le montre. C'est le seul endroit où l'on voit le
moteur travailler sur des données qu'il n'a pas construites lui-même.

Usage :
    python src/tools/inspect.py [EURUSD USDJPY ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from market import analysis as an  # noqa: E402
from market import data as md  # noqa: E402
from market import pairs as mp  # noqa: E402


def show(symbol: str, timeframe: str = "D1", use_cache: bool = True) -> int:
    pair = mp.get(symbol)
    label = md.TIMEFRAMES[timeframe]["label"]
    print("=" * 78)
    print(f"{pair.symbol} — {pair.name}   ({label}, "
          f"{pair.digits} décimales, 1 pip = {pair.pip})")
    print("=" * 78)

    try:
        df = md.fetch(pair.symbol, timeframe, use_cache=use_cache)
    except (md.DataError, KeyError) as exc:
        print(f"  ERREUR : {exc}")
        return 1

    print(f"  {len(df)} bougies, du {df.index[0].date()} au {df.index[-1].date()}")
    report = an.analyse(pair, df, timeframe)

    for line in report.context_lines():
        print(f"  {line}")

    print()
    for line in report.verdict_lines():
        print(f"  {line}")

    if report.plan.actionable:
        p = report.plan
        print()
        print(f"  entrée {p.entry:.5f}   stop {p.stop:.5f}   cible {p.target:.5f}")
        print(f"  risque {p.stop_pips:.0f} pips   ratio {p.rr:.2f}")
        print()
        print("  Ordre limité, stop, et rien d'autre. Si le prix part sans nous,")
        print("  on attend : le prochain calcul le dira.")

    scene = report.to_scene()
    print()
    print(f"  scène : {len(scene.candles)} bougies, {len(scene.annotations)} annotations, "
          f"{len(scene.steps)} étapes")
    print(f"  à retenir : {scene.takeaway}")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    timeframe = md.DEFAULT_TIMEFRAME
    if args and args[0].upper() in md.TIMEFRAMES:
        timeframe = args.pop(0).upper()
    codes = [show(s, timeframe) for s in (args or list(mp.DEFAULT_SELECTION))]
    return 1 if any(codes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
