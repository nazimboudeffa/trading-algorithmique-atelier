"""Calibrage du filtre de prominence sur données réelles (script de diagnostic)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

from market import data as md  # noqa: E402
from market import measure as ms  # noqa: E402
from market import structure as stx  # noqa: E402

for symbol in ("EURUSD", "GBPUSD", "USDJPY", "EURJPY", "XAUUSD"):
    print(f"=== {symbol}")
    for tf in ("H1", "M15"):
        try:
            df = md.fetch(symbol, tf, use_cache=True)
        except (md.DataError, KeyError) as exc:
            print(f"    {tf}: {exc}")
            continue
        typical = ms.median_range(df) * 10000
        line = [f"    {tf}: {len(df):5d} bougies, typique {typical:5.1f} pips"]
        for k in (2, 3, 4, 5, 6, 8):
            kept = stx.structure_swings(df, min_swing_atr=k)
            line.append(f"k={k}:{len(kept):4d}")
        st = stx.read_structure(df, min_swing_atr=4)
        line.append(f"| H1@4: {st.label}")
        print("\n    ".join(line))
