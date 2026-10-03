"""
Panneau d'une leçon : le principe, le pas-à-pas, le graphique et l'à retenir.

La navigation (◀ ▶) pilote à la fois le texte affiché et la révélation
progressive du graphique : chaque étape montre une annotation de plus. C'est ce
qui distingue une illustration d'un support pédagogique.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.canvas import ChartCanvas
from core.model import Scene
from core.theme import INFO, MUTED, TEXT


class LessonPanel(QWidget):
    """Affiche une scène et son explication, avec navigation par étapes."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._scene: Scene | None = None
        self._step: int | None = None  # None = vue complète

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # --- principe
        self.principle = QLabel()
        self.principle.setWordWrap(True)
        self.principle.setStyleSheet(
            f"background: {INFO.name()}; color: {TEXT.name()};"
            "border-left: 3px solid #7ea8ff; border-radius: 4px;"
            "padding: 9px 12px; font-size: 11px;"
        )
        root.addWidget(self.principle)

        # --- graphique
        self.canvas = ChartCanvas()
        root.addWidget(self.canvas, 1)

        # --- navigation
        nav = QHBoxLayout()
        nav.setSpacing(6)
        self.btn_prev = QPushButton("◀ Précédent")
        self.btn_all = QPushButton("Tout voir")
        self.btn_next = QPushButton("Suivant ▶")
        for b in (self.btn_prev, self.btn_all, self.btn_next):
            b.setCursor(Qt.PointingHandCursor)
        self.btn_prev.clicked.connect(lambda: self._go(-1))
        self.btn_next.clicked.connect(lambda: self._go(1))
        self.btn_all.clicked.connect(self.show_all)

        self.btn_prev.setFixedWidth(100)
        self.btn_all.setFixedWidth(90)
        self.btn_next.setFixedWidth(100)
        nav.addWidget(self.btn_prev)
        nav.addWidget(self.btn_all)
        nav.addWidget(self.btn_next)
        nav.addStretch(1)

        self.step_label = QLabel()
        self.step_label.setStyleSheet(f"color: {MUTED.name()}; font-size: 10px;")
        nav.addWidget(self.step_label)
        root.addLayout(nav)

        # --- explication de l'étape
        self.step_title = QLabel()
        self.step_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        root.addWidget(self.step_title)

        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #12171f; border: 1px solid #1e2532; border-radius: 5px; }")
        fv = QVBoxLayout(frame)
        fv.setContentsMargins(10, 8, 10, 8)
        self.step_text = QTextEdit()
        self.step_text.setReadOnly(True)
        self.step_text.setFrameShape(QFrame.NoFrame)
        self.step_text.setStyleSheet("background: transparent; color: #d8dee9; font-size: 11px;")
        self.step_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        fv.addWidget(self.step_text)
        root.addWidget(frame, 1)

        # --- à retenir
        self.takeaway = QLabel()
        self.takeaway.setWordWrap(True)
        self.takeaway.setStyleSheet(
            "background: #1a1408; color: #ffd08a; border: 1px solid #4a3a12;"
            "border-radius: 4px; padding: 9px 12px; font-size: 11px;"
        )
        root.addWidget(self.takeaway)

    # ------------------------------------------------------------------ API
    def set_scene(self, scene: Scene) -> None:
        self._scene = scene
        self._step = None
        self.principle.setText(f"<b>Principe</b> — {scene.principle}")
        self.takeaway.setText(f"<b>À retenir</b> — {scene.takeaway}" if scene.takeaway else "")
        self.canvas.set_scene(scene)
        self._refresh()

    def show_all(self) -> None:
        self._step = None
        self._refresh()

    # ------------------------------------------------------------ navigation
    def go_step(self, delta: int) -> None:
        """Avance ou recule d'une étape (API publique, utilisée par les raccourcis)."""
        self._go(delta)

    def _go(self, delta: int) -> None:
        if self._scene is None or not self._scene.steps:
            return
        last = len(self._scene.steps) - 1
        if self._step is None:
            # depuis la vue complète, on démarre à la première étape
            nxt = 0 if delta > 0 else last
        else:
            nxt = self._step + delta
        self._step = max(0, min(last, nxt))
        self._refresh()

    def _refresh(self) -> None:
        scene, step = self._scene, self._step
        if scene is None:
            return
        self.canvas.set_step(step)

        if step is None:
            self.step_title.setText("Vue complète — tous les éléments sont affichés")
            body = scene.takeaway or ""
            self.step_text.setPlainText(body)
            self.step_label.setText(f"{len(scene.steps)} étapes")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(True)
        else:
            s = scene.steps[step]
            self.step_title.setText(f"{step + 1}. {s.title}")
            self.step_text.setPlainText(s.text)
            self.step_label.setText(f"Étape {step + 1} / {len(scene.steps)}")
            self.btn_prev.setEnabled(step > 0)
            self.btn_next.setEnabled(True)
