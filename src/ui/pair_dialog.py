"""
Sélection des paires à analyser — l'icône engrenage.

Une boîte de dialogue simple : trois groupes de cases à cocher, un champ de
filtre, et deux boutons. La sélection est enregistrée immédiatement, donc
l'atelier s'ouvre ensuite sur les mêmes paires sans qu'on ait à les re-cocher.

Le filtre est un vrai filtre, pas un décor : taper « jpy » réduit la liste à
EURJPY, GBPJPY, USDJPY… et cocher « tout afficher » revient à la liste
complète.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.theme import MUTED

from market.pairs import CATALOGUE, GROUPS, by_group

BULLET = "\u2699"  # engrenage


class PairDialog(QDialog):
    """Choix des paires de forex à suivre."""

    def __init__(self, selection: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{BULLET}  Paires analysées")
        self.resize(460, 540)

        self._checks: dict[str, QCheckBox] = {}
        self._selected = list(selection)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        head = QLabel("Cochez les paires que vous souhaitez analyser.")
        head.setWordWrap(True)
        head.setStyleSheet(f"color: {MUTED.name()}; font-size: 11px;")
        root.addWidget(head)

        # --- filtre
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filtrer — jpy, eur, or…")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        root.addWidget(self.filter)

        # --- groupes de cases
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        bv = QVBoxLayout(body)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(10)

        for group, pairs in by_group().items():
            if not pairs:
                continue
            title = QLabel(group)
            title.setStyleSheet("font-weight: bold; font-size: 11px; color: #7ea8ff;")
            bv.addWidget(title)
            for pair in pairs:
                cb = QCheckBox(f"{pair.symbol}   {pair.name}")
                cb.setChecked(pair.symbol in self._selected)
                cb.setToolTip(f"{pair.symbol} — {pair.digits} décimales, "
                              f"1 pip = {pair.pip}")
                cb.toggled.connect(lambda _=False: self._update_count())
                self._checks[pair.symbol] = cb
                bv.addWidget(cb)
            bv.addSpacing(2)

        bv.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # --- actions de masse
        actions = QHBoxLayout()
        all_btn = QPushButton("Tout cocher")
        none_btn = QPushButton("Tout décocher")
        maj_btn = QPushButton("Majeures")
        all_btn.clicked.connect(lambda: self._set_all(True))
        none_btn.clicked.connect(lambda: self._set_all(False))
        maj_btn.clicked.connect(self._set_majors)
        for b in (all_btn, maj_btn, none_btn):
            b.setCursor(Qt.PointingHandCursor)
            actions.addWidget(b)
        root.addLayout(actions)

        self.count = QLabel()
        self.count.setStyleSheet(f"color: {MUTED.name()}; font-size: 11px;")
        root.addWidget(self.count)

        # --- validation
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Enregistrer")
        buttons.button(QDialogButtonBox.Ok).setEnabled(bool(self._selected))
        buttons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        buttons.button(QDialogButtonBox.Cancel).setText("Annuler")
        buttons.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self._ok_button = buttons.button(QDialogButtonBox.Ok)
        root.addWidget(buttons)

        self._update_count()

    # ------------------------------------------------------------------ API
    def selection(self) -> list[str]:
        """Les paires cochées, dans l'ordre du catalogue."""
        return [p.symbol for p in CATALOGUE if self._checks[p.symbol].isChecked()]

    # ----------------------------------------------------------------- privé
    def _set_all(self, value: bool) -> None:
        for cb in self._checks.values():
            cb.setChecked(value)
        self._update_count()

    def _set_majors(self) -> None:
        for cb in self._checks.values():
            cb.setChecked(False)
        for pair in by_group().get("Majeures", []):
            self._checks[pair.symbol].setChecked(True)
        self._update_count()

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for symbol, cb in self._checks.items():
            pair = next(p for p in CATALOGUE if p.symbol == symbol)
            haystack = f"{symbol} {pair.name} {pair.group}".lower()
            cb.setVisible(not needle or needle in haystack)

    def _update_count(self) -> None:
        n = len(self.selection())
        self.count.setText(f"{n} paire(s) sélectionnée(s) sur {len(CATALOGUE)} disponibles.")
        self._ok_button.setEnabled(n > 0)

    def accept(self) -> None:  # noqa: D102 (API Qt)
        self._selected = self.selection()
        if not self._selected:
            return
        super().accept()
