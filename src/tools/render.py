"""
Rendu des scènes en PNG sans fenêtre (contrôle visuel / génération de docs).

Usage :
    python src/tools/render.py                # toutes les leçons -> build/preview/
    python src/tools/render.py structure      # seulement les leçons dont l'id commence par ce texte
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.canvas import ChartCanvas  # noqa: E402
from lessons import LESSONS  # noqa: E402

OUT = ROOT.parent / "build" / "preview"


def render(app: QApplication, scene, step: int | None, path: Path, size=(1200, 700)) -> None:
    canvas = ChartCanvas()
    canvas.resize(*size)
    canvas.set_scene(scene)
    canvas.set_step(step)
    # laisse Qt stabiliser la mise en page avant le grab()
    canvas.repaint()
    app.processEvents()
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.grab().save(str(path))
    print(f"  {path.name}  ({'tout' if step is None else f'étape {step}'})")


def main() -> int:
    # la console Windows est souvent en cp1252 : on force l'UTF-8
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    app = QApplication(sys.argv)

    wanted = sys.argv[1] if len(sys.argv) > 1 else ""
    scenes = [s for s in LESSONS if not wanted or s.id.startswith(wanted)]
    if not scenes:
        print(f"Aucune leçon ne correspond à « {wanted} ».")
        return 1

    print(f"Rendu de {len(scenes)} leçon(s) :")
    for scene in scenes:
        render(app, scene, None, OUT / f"{scene.id}-complet.png")
        for i, _step in enumerate(scene.steps, start=1):
            render(app, scene, i, OUT / f"{scene.id}-etape{i}.png")
    print(f"OK → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
