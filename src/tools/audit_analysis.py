"""
Audit de mise en page des scènes d'analyse.

Les scènes d'analyse sont construites à partir de cours réels, donc leurs
annotations ne sont pas choisies à la main. Le risque n'est pas le texte
(mais le moteur) : c'est la géométrie — un niveau hors cadre, deux étiquettes
superposées, une entrée et un stop indiscernables parce qu'ils sont à 2 pips
l'un de l'autre.

On réutilise les fonctions de `tools.audit` : la mesure est la même que pour
les leçons, donc un bug ici serait un bug là-bas aussi.

Usage :
    python src/tools/audit_analysis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.canvas import ChartCanvas  # noqa: E402
from tools.audit import SIZES, _layout_problems  # noqa: E402


def audit_scene(canvas: ChartCanvas, scene) -> list[str]:
    """Tous les défauts de mise en page d'une scène, à toutes les tailles."""
    problems: list[str] = []
    for size in SIZES:
        found = _layout_problems(canvas, scene, size)
        problems += [f"{size[0]}x{size[1]} : {p}" for p in found]
        if found:
            break  # une seule taille suffit à signaler
    return problems


def audit_report(canvas: ChartCanvas, report) -> list[str]:
    """Vérifie la scène d'un rapport d'analyse, étape par étape."""
    scene = report.to_scene()
    problems = audit_scene(canvas, scene)
    for step in range(len(scene.steps)):
        scene.step = None
        problems += [f"étape {step + 1} — {p}" for p in audit_scene(canvas, scene)]
    return problems


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    app = QApplication(sys.argv)  # noqa: F841 — métriques de police
    canvas = ChartCanvas()

    from tools.samples import SAMPLE_REPORTS

    total = 0
    for report in SAMPLE_REPORTS():
        problems = audit_report(canvas, report)
        status = "OK  " if not problems else f"{len(problems):>2} pb"
        print(f"[{status}] {report.pair.symbol:10s} {report.plan.headline()}")
        for p in problems:
            print(f"         - {p}")
        total += len(problems)

    print()
    print("Audit terminé : aucun problème." if total == 0 else f"Audit terminé : {total} problème(s).")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
