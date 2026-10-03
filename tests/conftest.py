"""Configuration partagée des tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Qt doit tourner hors écran : les tests n'ouvrent aucune fenêtre
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))


@pytest.fixture(scope="session")
def app():
    """Une QApplication unique pour toute la session (obligatoire pour les polices)."""
    from PySide6.QtWidgets import QApplication

    instance = QApplication.instance() or QApplication([])
    yield instance


@pytest.fixture
def canvas(app):
    """Un canevas prêt à rendre, à la taille de référence des tests."""
    from core.canvas import ChartCanvas

    widget = ChartCanvas()
    widget.resize(1280, 720)
    yield widget
    widget.deleteLater()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Interdit toute sortie réseau pendant les tests.

    Sans cela, un test qui construit la fenêtre principale déclenche un
    téléchargement réel : le test passe, mais il est lent, non déterministe,
    et il écrit dans le cache de l'utilisateur. Le besoin de données se règle
    en injectant un `fetcher` — `data.fetch` le prend en paramètre, c'est
    justement pour ça qu'il existe.
    """
    from market import data as md

    def forbidden(*args, **kwargs):
        raise md.DataError("réseau interdit dans les tests")

    monkeypatch.setattr(md, "yf_fetch", forbidden)
