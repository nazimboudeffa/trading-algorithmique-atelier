"""
Démarrage à blanc de l'atelier : vérifie que la fenêtre s'ouvre, que les deux
onglets sont là, et que le graphe se dessine réellement.

Un test qui passe peut encore cacher une fenêtre qui ne s'ouvre pas : il ne
fait que construire des widgets. Ce script, lui, affiche la fenêtre, laisse Qt
peindre, puis referme.

Usage :
    QT_QPA_PLATFORM=offscreen python src/tools/smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()

    # laisse Qt peindre réellement avant de refermer
    QTimer.singleShot(800, app.quit)
    app.exec()

    print(f"fenêtre ouverte        : {win.isVisible()}")
    print(f"taille                 : {win.width()}x{win.height()}")
    print(f"nombre d'onglets       : {win.tabs.count()}")
    for i in range(win.tabs.count()):
        print(f"  onglet {i}            : {win.tabs.tabText(i)}")
    print(f"leçons                 : {len(_lesson_titles())} au total")
    print(f"leçon courante         : {win.lessons.list.currentItem().text()}")
    print(f"paires suivies         : {win.analysis.list.count()}")
    for i in range(win.analysis.list.count()):
        print(f"  - {win.analysis.list.item(i).text().replace(chr(10), ' / ')}")
    print(f"verdict affiché        : {win.analysis.verdict.text()}")
    print(f"statut                 : {win.analysis.status.text()}")
    print(f"graphique du lessons   : {win.lessons.panel.canvas.scene() is not None}")
    return 0


def _lesson_titles() -> list[str]:
    from lessons import LESSONS

    return [s.title for s in LESSONS]


if __name__ == "__main__":
    raise SystemExit(main())
