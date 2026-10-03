"""
Catalogue des leçons.

Chaque module du package expose une fonction `SCENES()` qui renvoie la liste
de ses scènes. Le registre les découvre automatiquement : ajouter une leçon
revient à déposer un fichier dans ce dossier, sans toucher à la liste centrale.

    from lessons import LESSONS
    for scene in LESSONS:
        print(scene.id, scene.title)
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Callable

from core.model import Scene

#: ordre d'affichage des modules (le reste est ajouté alphabétiquement après)
MODULE_ORDER = [
    "structure",
    "support_resistance",
    "liquidity",
    "order_block",
    "fvg",
    "candles",
    "breakout_retest",
    "risk",
]


def _module_names() -> list[str]:
    found = {m.name for m in pkgutil.iter_modules(__path__)}
    ordered = [n for n in MODULE_ORDER if n in found]
    ordered += sorted(found - set(ordered))
    return ordered


def _collect() -> list[Scene]:
    scenes: list[Scene] = []
    for name in _module_names():
        mod = importlib.import_module(f"{__name__}.{name}")
        factory: Callable[[], list[Scene]] | None = getattr(mod, "SCENES", None)
        if factory is None:
            raise AttributeError(
                f"le module de leçon « {name} » doit exposer une fonction SCENES()"
            )
        scenes.extend(factory())
    return scenes


#: toutes les leçons, dans l'ordre d'affichage
LESSONS: list[Scene] = _collect()


def get(scene_id: str) -> Scene | None:
    """Récupère une scène par identifiant."""
    return next((s for s in LESSONS if s.id == scene_id), None)


__all__ = ["LESSONS", "MODULE_ORDER", "get"]
