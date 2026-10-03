"""Tests de l'interface : sélection de paires, onglets, navigation."""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from market import analysis as an
from market import pairs as mp
from market import structure as stx
from tools.samples import SAMPLE_REPORTS, report_long


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Le cache des cours, redirigé vers un dossier jetable.

    Sans cela, un test qui télécharge écrit dans le cache réel et le suivant le
    relit au lieu d'appeler son faux fournisseur : le second test passerait
    alors pour une mauvaise raison, et l'ordre des tests deviendrait significatif.
    """
    from market import data as md

    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(md, "CACHE_DIR", cache)
    return cache


@pytest.fixture
def tab(app, isolated_cache):
    """Un onglet d'analyse prêt, alimenté par un faux fournisseur de données."""
    from ui.analysis_tab import AnalysisTab

    widget = AnalysisTab()
    widget._fetcher = _fake_fetcher
    yield widget
    widget.deleteLater()


def _fake_fetcher(symbol, interval, period):
    """Cours synthétiques : jamais de réseau, résultats identiques à chaque fois.

    Les séries doivent dépasser `data.MIN_BARS`, sinon le moteur les refuse —
    ce qu'il a raison de faire, et ce qui masquerait le test que l'on veut
    réellement écrire.
    """
    from tools.samples import M15_BARS, PERIOD, _frame, uptrend, with_rejection, pullback_to
    from market import structure as stx

    if interval == "1h":
        return _frame(uptrend(periods=120 // len(PERIOD)), freq="1h")
    h1 = _frame(uptrend(periods=120 // len(PERIOD)), freq="1h")
    support = stx.read_structure(h1).last_low.price
    return with_rejection(
        pullback_to(support, h1["Close"].iloc[-1], bars=M15_BARS - 1), support
    )


# --------------------------------------------------------------------------- #
# Sélection de paires
# --------------------------------------------------------------------------- #


def test_selection_remplit_la_liste(app, isolated_cache):
    from ui.analysis_tab import AnalysisTab

    widget = AnalysisTab()
    widget.set_selection(["EURUSD", "USDJPY"])
    assert widget.list.count() == 2
    assert widget.list.item(0).data(Qt.UserRole) == "EURUSD"
    widget.deleteLater()


def test_selection_vide_autorise_le_message(app, isolated_cache):
    from ui.analysis_tab import AnalysisTab

    widget = AnalysisTab()
    widget.set_selection([])
    assert widget.list.count() == 0
    assert widget.current_report() is None
    widget.deleteLater()


def test_le_bouton_engrenage_porte_le_nombre(app, isolated_cache):
    from ui.analysis_tab import AnalysisTab
    from ui.pair_dialog import BULLET

    widget = AnalysisTab()
    widget.set_selection(["EURUSD", "GBPUSD", "USDJPY"])
    text = widget.btn_gear.text()
    assert BULLET in text
    assert "3" in text
    widget.deleteLater()


# --------------------------------------------------------------------------- #
# Chargement d'un rapport
# --------------------------------------------------------------------------- #


def test_charger_un_rapport_affiche_le_verdict(tab):
    tab.set_selection(["EURUSD"])
    report = tab.current_report()
    assert report is not None
    assert report.ok
    assert tab.canvas.scene() is not None
    assert tab.detail.toPlainText()


def test_une_erreur_est_affichee_telle_quelle(app, isolated_cache):
    from ui.analysis_tab import AnalysisTab

    def failing(symbol, interval, period):
        from market.data import DataError

        raise DataError("réseau coupé")

    widget = AnalysisTab()
    widget._fetcher = failing
    widget.set_selection(["EURUSD"])
    assert "réseau coupé" in widget.detail.toPlainText()
    assert widget.canvas.scene() is not None  # la scène d'erreur reste dessinable
    widget.deleteLater()


def test_navigation_entre_les_etapes(tab):
    tab.set_selection(["EURUSD"])
    scene = tab.canvas.scene()
    last = len(scene.steps) - 1

    tab.step(1)
    assert tab.canvas.step() == 0
    tab.step(1)
    assert tab.canvas.step() == 1
    tab.step(-1)
    assert tab.canvas.step() == 0
    tab.step(-1)
    assert tab.canvas.step() == 0  # ne descend pas sous la première

    for _ in range(last + 2):
        tab.step(1)
    assert tab.canvas.step() == last  # ne dépasse pas la dernière


def test_tout_voir_retablit_la_vue_complete(tab):
    tab.set_selection(["EURUSD"])
    tab.step(1)
    assert tab.canvas.step() == 0
    tab._step_all()  # noqa: SLF001 — accès au bouton « Tout voir »
    assert tab.canvas.step() is None


def test_actualiser_ignore_le_cache(tab):
    tab.set_selection(["EURUSD"])
    tab.refresh_clicked()
    assert tab.current_report() is not None


# --------------------------------------------------------------------------- #
# Sélecteur de paires
# --------------------------------------------------------------------------- #


def test_selecteur_ouvre_sur_la_selection(app):
    from ui.pair_dialog import PairDialog

    dlg = PairDialog(["USDJPY", "EURUSD"])
    assert dlg.selection() == ["EURUSD", "USDJPY"]  # dans l'ordre du catalogue
    dlg.deleteLater()


def test_selecteur_filtre(app):
    from ui.pair_dialog import PairDialog

    dlg = PairDialog([])
    dlg.filter.setText("jpy")
    # `isVisible` ment sur une fenêtre jamais affichée : tout y est « invisible ».
    # `isHidden` en revanche dit ce que le filtre a réellement fait.
    caches = [s for s, cb in dlg._checks.items() if not cb.isHidden()]  # noqa: SLF001
    assert "EURJPY" in caches
    assert "USDJPY" in caches
    assert "EURUSD" not in caches
    dlg.deleteLater()


def test_selecteur_filtre_vide_tout_montre(app):
    from ui.pair_dialog import PairDialog

    dlg = PairDialog([])
    dlg.filter.setText("jpy")
    dlg.filter.setText("")
    assert all(not cb.isHidden() for cb in dlg._checks.values())  # noqa: SLF001
    dlg.deleteLater()


def test_selecteur_filtre_sur_le_nom(app):
    from ui.pair_dialog import PairDialog

    dlg = PairDialog([])
    dlg.filter.setText("yen")
    caches = [s for s, cb in dlg._checks.items() if not cb.isHidden()]  # noqa: SLF001
    assert set(caches) == {"USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY"}
    dlg.deleteLater()


def test_selecteur_selection_par_defaut(app):
    from ui.pair_dialog import PairDialog

    dlg = PairDialog(mp.DEFAULT_SELECTION)
    assert set(dlg.selection()) == set(mp.DEFAULT_SELECTION)
    dlg.deleteLater()


def test_selecteur_tout_cocher(app):
    from ui.pair_dialog import PairDialog

    dlg = PairDialog([])
    dlg._set_all(True)  # noqa: SLF001 — le bouton « Tout cocher »
    assert len(dlg.selection()) == len(mp.CATALOGUE)
    dlg.deleteLater()


def test_selecteur_tout_decocher(app):
    from ui.pair_dialog import PairDialog

    dlg = PairDialog(mp.DEFAULT_SELECTION)
    dlg._set_all(False)  # noqa: SLF001
    assert dlg.selection() == []
    dlg.deleteLater()


def test_selecteur_majeures(app):
    from ui.pair_dialog import PairDialog

    dlg = PairDialog([])
    dlg._set_majors()  # noqa: SLF001 — le bouton « Majeures »
    assert set(dlg.selection()) == {p.symbol for p in mp.by_group()["Majeures"]}
    dlg.deleteLater()


def test_selecteur_refuse_une_selection_vide(app):
    from ui.pair_dialog import PairDialog

    dlg = PairDialog([])
    assert not dlg._ok_button.isEnabled()  # noqa: SLF001
    dlg._set_all(True)  # noqa: SLF001
    assert dlg._ok_button.isEnabled()  # noqa: SLF001
    dlg.deleteLater()


def test_selecteur_enregistre_la_selection(app, tmp_path):
    dlg_symbols = mp.save_selection(["EURGBP"], root=tmp_path)
    assert mp.load_selection(tmp_path) == dlg_symbols


# --------------------------------------------------------------------------- #
# Fenêtre principale
# --------------------------------------------------------------------------- #


def test_fenetre_a_deux_onglets(app, isolated_cache, tmp_path, monkeypatch):
    monkeypatch.setattr(mp, "selection_path", lambda root=None: tmp_path / "sel.json")
    from ui.main_window import MainWindow

    win = MainWindow()
    assert win.tabs.count() == 2
    assert win.tabs.tabText(0) == "Leçons"
    assert win.tabs.tabText(1) == "Analyse"
    win.deleteLater()


def test_raccourci_dirige_vers_l_onglet_actif(app, isolated_cache, tmp_path, monkeypatch):
    monkeypatch.setattr(mp, "selection_path", lambda root=None: tmp_path / "sel.json")
    from ui.main_window import MainWindow

    win = MainWindow()
    # sur l'onglet des leçons, les flèches agissent sur la leçon
    win.tabs.setCurrentIndex(0)
    win.lessons.panel.show_all()
    win._act("go_step", 1)  # noqa: SLF001 — le raccourci
    assert win.lessons.panel.step_label.text().startswith("Étape 1")

    # sur l'onglet d'analyse, elles n'ont plus le même effet : l'état de la
    # leçon ne doit pas bouger
    win.tabs.setCurrentIndex(1)
    avant = win.lessons.panel.step_label.text()
    win._act("go_step", 1)  # noqa: SLF001
    assert win.lessons.panel.step_label.text() == avant
    win.deleteLater()


def test_navigation_par_les_fleches_dans_l_onglet_leçons(app, isolated_cache, tmp_path, monkeypatch):
    monkeypatch.setattr(mp, "selection_path", lambda root=None: tmp_path / "sel.json")
    from ui.main_window import MainWindow

    win = MainWindow()
    win.tabs.setCurrentIndex(0)
    row = win.lessons.list.currentRow()
    win._act("move", 1)  # noqa: SLF001 — flèche bas
    assert win.lessons.list.currentRow() == row + 1
    win._act("move", -1)  # noqa: SLF001
    assert win.lessons.list.currentRow() == row
    win.deleteLater()
