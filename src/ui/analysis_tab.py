"""
Onglet d'analyse : les paires choisies, leur lecture structurelle, leur plan.

La disposition reprend celle de l'onglet des leçons, volontairement : à
gauche la liste de ce qu'on regarde, au centre le graphique, à droite ce que
le moteur a compris. Un atelier où les deux moitiés ne se ressemblent pas
serait deux outils dans un même programme.

Le graphique n'est pas un widget de cotation : c'est le même `ChartCanvas` que
les leçons, alimenté par une `Scene` construite à partir de l'analyse. Les
annotations du plan (entrée, stop, cible) sont donc exactement les mêmes
objets que ceux des leçons — d'où la cohérence visuelle.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.canvas import ChartCanvas
from core.theme import BAD, GOOD, MUTED, TEXT, WARN

from market import analysis as an
from market import data as md
from market import pairs as mp
from market.analysis import BUY, Report, SELL, WAIT
from ui.pair_dialog import BULLET, PairDialog

#: Couleur du bandeau de verdict, par décision.
VERDICT_COLORS = {BUY: GOOD, SELL: BAD, WAIT: WARN}


class AnalysisTab(QWidget):
    """Liste des paires à gauche, scène d'analyse au centre, lecture à droite."""

    #: Émis quand l'unité de temps change, pour que la fenêtre retitre l'onglet.
    timeframe_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._reports: dict[str, Report] = {}
        self._fetcher = None  # injectable par les tests
        self._timeframe = md.DEFAULT_TIMEFRAME

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        # --- barre d'actions
        bar = QHBoxLayout()

        self.tf_combo = QComboBox()
        self.tf_combo.setToolTip(
            "L'unité de temps analysée. Tout — structure, niveaux, déclencheur, "
            "plan — est lu sur cette seule unité."
        )
        for code, spec in md.TIMEFRAMES.items():
            self.tf_combo.addItem(spec["label"], code)
        self.tf_combo.setCurrentIndex(
            max(0, self.tf_combo.findData(self._timeframe))
        )
        self.tf_combo.currentIndexChanged.connect(self._on_timeframe)

        self.btn_gear = QPushButton("Paires analysées")
        self.btn_gear.setToolTip(
            "Choisir les paires de forex à analyser. La sélection est mémorisée."
        )
        self.btn_refresh = QPushButton("Actualiser")
        self.btn_refresh.setToolTip("Retélécharger les cours au lieu du cache.")
        for b in (self.btn_gear, self.btn_refresh):
            b.setCursor(Qt.PointingHandCursor)
        self.btn_gear.clicked.connect(self.gear_clicked)
        self.btn_refresh.clicked.connect(self.refresh_clicked)
        bar.addWidget(QLabel("Unité"))
        bar.addWidget(self.tf_combo)
        bar.addWidget(self.btn_gear)
        bar.addWidget(self.btn_refresh)
        bar.addStretch(1)
        self.status = QLabel("Choisissez vos paires, puis sélectionnez-en une.")
        self.status.setStyleSheet(f"color: {MUTED.name()}; font-size: 11px;")
        bar.addWidget(self.status)
        root.addLayout(bar)

        # --- contenu
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.list = QListWidget()
        self.list.setFixedWidth(180)
        self.list.currentItemChanged.connect(self._on_select)
        splitter.addWidget(self.list)

        mid = QWidget()
        mv = QVBoxLayout(mid)
        mv.setContentsMargins(0, 0, 0, 0)
        mv.setSpacing(6)
        self.verdict = QLabel("—")
        self.verdict.setWordWrap(True)
        self.verdict.setStyleSheet(
            f"background: {MUTED.name()}; color: {TEXT.name()};"
            "border-radius: 4px; padding: 8px 10px; font-size: 12px; font-weight: bold;"
        )
        self.verdict.setMinimumHeight(44)
        mv.addWidget(self.verdict)
        self.canvas = ChartCanvas()
        mv.addWidget(self.canvas, 1)

        nav = QHBoxLayout()
        self.btn_step_prev = QPushButton("◀")
        self.btn_step_all = QPushButton("Tout voir")
        self.btn_step_next = QPushButton("▶")
        for b in (self.btn_step_prev, self.btn_step_all, self.btn_step_next):
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedWidth(92)
        self.btn_step_prev.clicked.connect(lambda: self._step(-1))
        self.btn_step_all.clicked.connect(self._step_all)
        self.btn_step_next.clicked.connect(lambda: self._step(1))
        nav.addWidget(self.btn_step_prev)
        nav.addWidget(self.btn_step_all)
        nav.addWidget(self.btn_step_next)
        nav.addStretch(1)
        self.step_label = QLabel("")
        self.step_label.setStyleSheet(f"color: {MUTED.name()}; font-size: 10px;")
        nav.addWidget(self.step_label)
        mv.addLayout(nav)
        splitter.addWidget(mid)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setStyleSheet(
            "background: #12171f; border: 1px solid #1e2532; border-radius: 5px;"
            "font-size: 11px;"
        )
        self.detail.setFixedWidth(340)
        splitter.addWidget(self.detail)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        root.addWidget(splitter, 1)

    # ------------------------------------------------------------------ API
    @property
    def timeframe(self) -> str:
        """L'unité de temps analysée, telle que `data.fetch` la nomme."""
        return self._timeframe

    def set_timeframe(self, code: str) -> None:
        """Change l'unité de temps et réanalyse la paire affichée."""
        if code not in md.TIMEFRAMES or code == self._timeframe:
            return
        self._timeframe = code
        index = self.tf_combo.findData(code)
        if index >= 0 and self.tf_combo.currentIndex() != index:
            self.tf_combo.setCurrentIndex(index)  # déclenche _on_timeframe
            return
        self._reload()

    def set_selection(self, symbols) -> None:
        """Remplit la liste avec les paires choisies et affiche la première."""
        keep = self.list.currentRow()
        self._reports.clear()
        self.list.clear()
        for symbol in symbols:
            pair = mp.get(symbol)
            item = QListWidgetItem(f"{pair.symbol}\n{pair.name}")
            item.setData(Qt.UserRole, symbol)
            self.list.addItem(item)
        if self.list.count():
            row = keep if 0 <= keep < self.list.count() else 0
            self.list.setCurrentRow(row)
        else:
            self._clear("Aucune paire sélectionnée. Utilisez l'engrenage pour en choisir.")
        self._update_gear_label()

    def current_report(self) -> Report | None:
        row = self.list.currentRow()
        item = self.list.item(row)
        if item is None:
            return None
        return self._reports.get(item.data(Qt.UserRole))

    def step(self, delta: int) -> None:
        """Avance ou recule d'une étape, comme dans l'onglet des leçons."""
        self._step(delta)

    # ----------------------------------------------------------------- privé
    def _on_timeframe(self, _index: int) -> None:
        """Le menu déroulant a changé d'unité : tout le contenu est périmé."""
        code = self.tf_combo.currentData()
        if not code or code == self._timeframe:
            return
        self._timeframe = code
        self._reload()
        self.timeframe_changed.emit(self._timeframe_label())

    def _reload(self) -> None:
        """Réanalyse la paire courante sur l'unité courante."""
        self._reports.clear()
        item = self.list.currentItem()
        if item is None:
            if not self.list.count():
                self._clear("Aucune paire sélectionnée. Utilisez l'engrenage pour en choisir.")
            return
        self._load(item.data(Qt.UserRole))

    def timeframe_label(self) -> str:
        """Le nom lisible de l'unité courante, tel qu'il apparaît dans l'onglet."""
        return md.TIMEFRAMES[self._timeframe]["label"]

    def _update_gear_label(self) -> None:
        n = self.list.count()
        self.btn_gear.setText(f"{BULLET}  Paires analysées ({n})")

    def _clear(self, message: str) -> None:
        self.verdict.setText("—")
        self.verdict.setStyleSheet(
            f"background: {MUTED.name()}; color: {TEXT.name()};"
            "border-radius: 4px; padding: 8px 10px; font-size: 12px; font-weight: bold;"
        )
        self.canvas.set_scene(None)
        self.detail.setPlainText(message)
        self.status.setText(message)
        self.step_label.setText("")

    def gear_clicked(self) -> None:
        """Ouvre le sélecteur de paires. Point d'entrée de l'icône engrenage."""
        current = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        dlg = PairDialog(current, self)
        if dlg.exec() == PairDialog.Accepted:
            saved = mp.save_selection(dlg.selection())
            self.set_selection(saved)
            self.status.setText(f"{len(saved)} paire(s) suivie(s).")

    def refresh_clicked(self) -> None:
        """Retélécharge les cours, en ignorant le cache d'une heure."""
        row = self.list.currentRow()
        item = self.list.item(row)
        if item is None:
            return
        symbol = item.data(Qt.UserRole)
        self._reports.pop(symbol, None)
        self._load(symbol, use_cache=False)

    def _on_select(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            return
        symbol = current.data(Qt.UserRole)
        report = self._reports.get(symbol)
        if report is None:
            self._load(symbol)
        else:
            self._show(report)

    def _load(self, symbol: str, use_cache: bool = True) -> None:
        """Télécharge puis analyse une paire. Les erreurs sont affichées telles quelles."""
        pair = mp.get(symbol)
        label = self._timeframe_label()
        self.status.setText(f"Analyse de {pair.symbol} en {label} en cours…")
        try:
            df = md.fetch(
                pair.symbol, self._timeframe, fetcher=self._fetcher, use_cache=use_cache
            )
        except (md.DataError, KeyError) as exc:
            self._reports[symbol] = an.failed(pair, str(exc))
            self._show(self._reports[symbol])
            return
        report = an.analyse(pair, df, self._timeframe)
        self._reports[symbol] = report
        self._show(report)

    def _show(self, report: Report) -> None:
        scene = report.to_scene()
        self.canvas.set_scene(scene)
        self.canvas.set_step(None)

        if not report.ok:
            self.verdict.setText(f"{report.pair.symbol} — données indisponibles")
            self.verdict.setStyleSheet(
                f"background: #2a1414; color: {BAD.name()};"
                "border-radius: 4px; padding: 8px 10px; font-size: 12px; font-weight: bold;"
            )
            self.detail.setPlainText(report.error)
            self.status.setText(report.error)
            self.step_label.setText("")
            return

        color = VERDICT_COLORS.get(report.decision, MUTED)
        self.verdict.setText(report.plan.headline())
        self.verdict.setStyleSheet(
            f"background: #12171f; color: {color.name()};"
            "border-left: 4px solid %s; border-radius: 4px;"
            "padding: 8px 10px; font-size: 12px; font-weight: bold;" % color.name()
        )

        parts = [f"<b>{report.pair.symbol}</b> — {report.pair.name}"
                 f" · {self._timeframe_label()}<br>"]
        parts.append("<b>Contexte</b>")
        for line in report.context_lines():
            parts.append(f"• {line}")
        parts.append("")
        parts.append("<b>Verdict</b>")
        for line in report.verdict_lines():
            parts.append(line)
        if report.plan.actionable:
            parts.append("")
            parts.append(
                f"<i>Risque par paires de 1 lot : "
                f"{report.plan.stop_pips:.0f} pips.</i>"
            )
        self.detail.setHtml("<div style='color:#d8dee9'>" + "<br>".join(parts) + "</div>")
        self.status.setText(
            f"{report.pair.symbol} · {self._timeframe_label()} — {len(scene.steps)} étapes. "
            "Utilisez ← → pour dérouler le raisonnement."
        )
        self.step_label.setText(f"{len(scene.steps)} étapes")

    def _step(self, delta: int) -> None:
        report = self.current_report()
        if report is None:
            return
        scene = self.canvas.scene()
        if scene is None or not scene.steps:
            return
        cur = self.canvas.step()
        last = len(scene.steps) - 1
        nxt = (0 if delta > 0 else last) if cur is None else cur + delta
        nxt = max(0, min(last, nxt))
        self.canvas.set_step(nxt)
        s = scene.steps[nxt]
        self.step_label.setText(f"Étape {nxt + 1} / {len(scene.steps)} — {s.title}")

    def _step_all(self) -> None:
        self.canvas.set_step(None)
        self.step_label.setText("vue complète")
