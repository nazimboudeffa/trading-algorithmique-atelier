"""
Audit de mise en page des scènes.

Contrôle ce qu'un œil ne peut pas vérifier facilement sur un PNG :
  * aucune annotation ne doit sortir du cadre du graphe (donc être invisible) ;
  * les étiquettes de texte ne doivent pas se chevaucher entre elles ;
  * les bougies ne doivent pas toucher les bords (sinon le prix sort du cadre).

Usage :
    python src/tools/audit.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRectF  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.canvas import ChartCanvas  # noqa: E402
from core.model import Arrow, Level, Marker, Note, Path, Scene, VLine, Zone  # noqa: E402
from lessons import LESSONS  # noqa: E402

SIZE = (1280, 720)

#: tailles testées : la fenêtre réelle, un laptop étroit, et un rendu large
SIZES = [(1280, 720), (1024, 680), (1600, 900)]


def check_geometry(scene: Scene) -> list[str]:
    """Cohérence OHLC : une bougie doit toujours contenir son corps."""
    problems = []
    for i, c in enumerate(scene.candles):
        if not all(math.isfinite(v) for v in (c.o, c.h, c.l, c.c)):
            problems.append(f"bougie {i} : valeur non finie")
            continue
        if c.h < max(c.o, c.c) - 1e-12:
            problems.append(f"bougie {i} : haut {c.h} sous le corps")
        if c.l > min(c.o, c.c) + 1e-12:
            problems.append(f"bougie {i} : bas {c.l} au-dessus du corps")
    return problems


def check_coverage(scene: Scene, canvas: ChartCanvas) -> list[str]:
    """Toute annotation révélée doit rester dans les bornes de prix calculées."""
    canvas.resize(*SIZE)
    canvas.set_scene(scene)
    g = canvas._layout()
    problems = []
    for step in [None, *range(1, len(scene.steps) + 1)]:
        for a in scene.annotations:
            st = getattr(a, "step", None)
            if step is not None and st is not None and st > step:
                continue
            for v in (getattr(a, "price", None), getattr(a, "p1", None), getattr(a, "p2", None)):
                if v is not None and not (g["lo"] <= v <= g["hi"]):
                    problems.append(
                        f"étape {step} : {type(a).__name__} à {v} hors des bornes")
    return problems


def check_content(scene: Scene) -> list[str]:
    """Chaque leçon doit être complète : principe, étape(s) et à-retenir."""
    problems = []
    if not scene.principle.strip():
        problems.append("principe vide")
    if not scene.steps:
        problems.append("aucune étape")
    if not scene.takeaway.strip():
        problems.append("« à retenir » vide")
    for s in scene.steps:
        if not s.title.strip() or not s.text.strip():
            problems.append(f"étape incomplète : {s.title!r}")
    return problems


def _overlap(a: QRectF, b: QRectF) -> float:
    """Aire d'intersection entre deux rectangles (0 si disjoints)."""
    r = a.intersected(b)
    return r.width() * r.height() if r.isValid() else 0.0


def _tags(canvas: ChartCanvas, g: dict, scene: Scene) -> list[tuple[str, QRectF]]:
    """Recalcule les rectangles de toutes les étiquettes, comme le fait le rendu.

    Le rectangle est toujours mesuré sur le texte RÉELLEMENT affiché ; `id`
    ne sert qu'à nommer l'étiquette dans le rapport.
    """
    x_of, y_of = g["x"], g["y"]
    out: list[tuple[str, QRectF]] = []

    def add(id_: str, text: str, x: float, y: float, bold: bool = False) -> None:
        # on reproduit exactement le placements du rendu, y compris le
        # ramenable dans le cadre fait par ChartCanvas._clamp_tag
        r = canvas.tag_rect(text, x, y, bold)
        r.moveLeft(canvas._clamp_tag(r.left(), y, r.width()))  # noqa: SLF001
        out.append((id_, r))

    for a in scene.annotations:
        if isinstance(a, Level) and a.show_tag:
            x1 = x_of(max(-0.4, a.start))
            add(f"Level:{a.label}", a.tag_text(scene.digits),
                x1 + 2 + a.tag_dx, y_of(a.price) - 16 + a.tag_dy)
        elif isinstance(a, Zone) and a.label:
            x1 = x_of(max(-0.4, a.start))
            y1 = y_of(a.high)
            add(f"Zone:{a.label}", a.label, x1 + 3,
                y1 - 4 if a.tag_side == "top" else y_of(a.low) + 14)
        elif isinstance(a, Marker):
            add(f"Marker:{a.text}", a.text, x_of(a.index) + a.dx, y_of(a.price) + a.dy, bold=True)
        elif isinstance(a, Arrow) and a.label:
            p1 = (x_of(a.x1), y_of(a.p1))
            p2 = (x_of(a.x2), y_of(a.p2))
            add(f"Arrow:{a.label}", a.label, (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 - 10)
        elif isinstance(a, Path) and a.label:
            add(f"Path:{a.label}", a.label, x_of(a.points[0][0]), y_of(a.points[0][1]) - 10)
        elif isinstance(a, VLine) and a.label:
            add(f"VLine:{a.label}", a.label, x_of(a.index), g["rect"].top() - 8)

    for i, c in enumerate(scene.candles):
        if c.label:
            add(f"Candle:{c.label}", c.label, x_of(i), y_of(c.h) - 10)
    return out


def audit_scene(canvas: ChartCanvas, scene: Scene) -> list[str]:
    """Contrôle complet d'une scène, à plusieurs tailles de fenêtre."""
    problems = check_content(scene) + check_geometry(scene) + check_coverage(scene, canvas)

    # les problèmes de mise en page peuvent différer selon la largeur : on
    # signale seulement ceux qui apparaissent à toutes les tailles
    layout_problems: list[str] = []
    for size in SIZES:
        layout_problems = _layout_problems(canvas, scene, size)
        if layout_problems:
            break
    problems += layout_problems
    return problems


def _layout_problems(canvas: ChartCanvas, scene: Scene, size, step: int | None = None) -> list[str]:
    canvas.resize(*size)
    canvas.set_scene(scene)
    # `set_scene` remet l'étape à None : on la réapplique pour que l'audit
    # mesure exactement ce que voit l'utilisateur à cette étape.
    canvas.set_step(step)
    g = canvas._layout()  # noqa: SLF001 — audit interne au projet
    rect: QRectF = g["rect"]
    problems: list[str] = []

    # 1. annotations dans le cadre
    for a in scene.annotations:
        if isinstance(a, Level):
            y = g["y"](a.price)
            if not rect.top() <= y <= rect.bottom():
                problems.append(f"Level {a.label or a.price} hors cadre (y={y:.0f})")
        elif isinstance(a, Zone):
            for p in (a.low, a.high):
                y = g["y"](p)
                if not rect.top() - 1 <= y <= rect.bottom() + 1:
                    problems.append(f"Zone {a.label or ''} hors cadre (y={y:.0f})")
        elif isinstance(a, (Marker,)):
            y = g["y"](a.price)
            if not rect.top() <= y <= rect.bottom():
                problems.append(f"Marker {a.text} hors cadre (y={y:.0f})")
        elif isinstance(a, Note):
            r = QRectF(g["x"](a.x), g["y"](a.price) - 60, a.width, 60)
            if not rect.left() <= r.left() and r.right() > rect.right():
                problems.append(f"Note déborde à droite ({a.text[:24]!r})")

    # 2. étiquettes hors cadre (le rendu les ramène horizontalement, pas en
    #    vertical : un débordement en hauteur est donc un vrai défaut)
    for label, r in _tags(canvas, g, scene):
        if r.right() > rect.right() + 4 or r.left() < rect.left() - 4:
            problems.append(f"étiquette hors cadre horizontalement : {label}")
        if r.top() < 0 or r.bottom() > rect.bottom() + 22:
            problems.append(f"étiquette hors cadre verticalement : {label}")

    # 3. chevauchements d'étiquettes
    tags = _tags(canvas, g, scene)
    for i in range(len(tags)):
        for j in range(i + 1, len(tags)):
            li, ri = tags[i]
            lj, rj = tags[j]
            ov = _overlap(ri, rj)
            if ov > 0:
                pct = 100 * ov / min(ri.width() * ri.height(), rj.width() * rj.height())
                if pct > 12:
                    problems.append(f"étiquettes superposées ({pct:.0f}%) : {li} / {lj}")

    # 4. bougies collées aux bords
    if scene.candles:
        y_hi = min(g["y"](c.h) for c in scene.candles)
        y_lo = max(g["y"](c.l) for c in scene.candles)
        if y_hi < rect.top() + 2:
            problems.append("bougies trop hautes (colle au bord haut)")
        if y_lo > rect.bottom() - 2:
            problems.append("bougies trop basses (colle au bord bas)")

    return problems


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    app = QApplication(sys.argv)  # noqa: F841 — nécessaire aux métriques de police
    canvas = ChartCanvas()

    total = 0
    for scene in LESSONS:
        problems = audit_scene(canvas, scene)
        status = "OK  " if not problems else f"{len(problems):>2} pb"
        print(f"[{status}] {scene.id:28s} {scene.title}")
        for p in problems:
            print(f"         - {p}")
        total += len(problems)

    print()
    print("Audit terminé : aucun problème." if total == 0 else f"Audit terminé : {total} problème(s).")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
