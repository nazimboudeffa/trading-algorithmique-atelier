"""
Fenêtre principale de l'atelier Price Action.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.theme import MUTED, TEXT  # noqa: E402
from lessons import LESSONS  # noqa: E402
from ui.lesson_panel import LessonPanel  # noqa: E402


class LessonsPage(QWidget):
    """La page des leçons : liste à gauche, leçon à droite, navigation en bas."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        title = QLabel("Atelier Price Action")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {TEXT.name()};")
        root.addWidget(title)

        sub = QLabel("Chaque notion est expliquée en trois temps : le schéma idéal, "
                     "l'erreur classique, la règle à retenir.")
        sub.setStyleSheet(f"color: {MUTED.name()}; font-size: 11px;")
        sub.setWordWrap(True)
        root.addWidget(sub)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.list = QListWidget()
        self.list.setFixedWidth(300)
        for scene in LESSONS:
            self.list.addItem(QListWidgetItem(scene.title))
        self.list.currentRowChanged.connect(self._on_select)

        self.panel = LessonPanel()

        splitter.addWidget(self.list)
        splitter.addWidget(self.panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        nav = QHBoxLayout()
        prev = QPushButton("◀ Leçon précédente")
        nxt = QPushButton("Leçon suivante ▶")
        prev.clicked.connect(lambda: self.move(-1))
        nxt.clicked.connect(lambda: self.move(1))
        nav.addWidget(prev)
        nav.addStretch(1)
        hint = QLabel("Astuce : ← et → pour les étapes d'une leçon, ↑ et ↓ pour changer de leçon.")
        hint.setStyleSheet(f"color: {MUTED.name()}; font-size: 10px;")
        nav.addWidget(hint)
        nav.addWidget(nxt)
        root.addLayout(nav)

        if LESSONS:
            self.list.setCurrentRow(0)

    def move(self, delta: int) -> None:
        row = self.list.currentRow()
        nxt = row + delta
        if 0 <= nxt < len(LESSONS):
            self.list.setCurrentRow(nxt)

    def go_step(self, delta: int) -> None:
        self.panel.go_step(delta)

    def _on_select(self, row: int) -> None:
        if 0 <= row < len(LESSONS):
            self.panel.set_scene(LESSONS[row])


class MainWindow(QMainWindow):
    """Fenêtre de l'atelier Price Action."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Price Action — atelier visuel")
        self.resize(1440, 880)

        self.lessons = LessonsPage()
        self.setCentralWidget(self.lessons)

        self._bind_shortcuts()

    def _bind_shortcuts(self) -> None:
        bindings = (
            ("Left", lambda: self.lessons.go_step(-1)),
            ("Right", lambda: self.lessons.go_step(1)),
            ("Up", lambda: self.lessons.move(-1)),
            ("Down", lambda: self.lessons.move(1)),
        )
        for seq, fn in bindings:
            act = QAction(self)
            act.setShortcut(seq)
            act.triggered.connect(fn)
            self.addAction(act)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
