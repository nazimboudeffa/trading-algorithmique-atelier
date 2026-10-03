"""
Tests du catalogue de leçons.

Ces tests protègent le contenu pédagogique : une leçon incomplète ou
géométriquement incohérente casse l'affichage sans erreur visible, donc on
vérifie ici de manière systématique.

Note sur la progression visuelle : une leçon doit au moins *démarrer* par une
étape qui ajoute un élément au graphique, et au moins une étape sur deux doit
le faire. On n'exige pas que chaque étape ajoute une annotation — la dernière
étape est le plus souvent une conclusion verbale, et une leçon entièrement
statique « en trois temps » n'enseignerait rien.
"""
from __future__ import annotations

import math

import pytest

from lessons import LESSONS, get


def _ids():
    return [s.id for s in LESSONS]


def _visual_steps(scene) -> set[int]:
    """Étapes qui apportent un élément graphique."""
    steps = {getattr(a, "step", None) for a in scene.annotations}
    steps |= {getattr(c, "step", None) for c in scene.candles}
    steps.discard(None)
    return steps


class TestCatalogue:
    def test_le_catalogue_est_rempli(self):
        assert len(LESSONS) > 0

    def test_aucune_erreur_de_doublon(self):
        assert len(_ids()) == len(set(_ids()))

    def test_get_par_identifiant(self):
        scene = LESSONS[0]
        assert get(scene.id) is scene

    def test_get_inconnu_renvoie_none(self):
        assert get("inexistant") is None

    def test_les_notions_prevues_sont_presentes(self):
        """Chaque grand thème du Price Action a au moins une leçon."""
        for theme in ("structure", "sr-", "liq-", "ob-", "fvg-", "cd-", "br-", "rk-"):
            assert any(i.startswith(theme) for i in _ids()), f"thème manquant : {theme}"


class TestIntegriteDesScenes:
    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_identifiant_et_titre_renseignes(self, scene):
        assert scene.id and scene.title

    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_principe_renseigne(self, scene):
        assert scene.principle.strip()

    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_a_retenir_renseigne(self, scene):
        assert scene.takeaway.strip()

    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_au_moins_trois_etapes(self, scene):
        assert len(scene.steps) >= 3

    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_etapes_completes(self, scene):
        for s in scene.steps:
            assert s.title.strip(), f"étape sans titre dans {scene.id}"
            assert s.text.strip(), f"étape sans texte dans {scene.id}"

    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_il_y_a_des_bougies(self, scene):
        assert len(scene.candles) >= 4

    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_bougies_coherentes(self, scene):
        for i, c in enumerate(scene.candles):
            assert all(math.isfinite(v) for v in (c.o, c.h, c.l, c.c)), \
                f"bougie {i} de {scene.id} non finie"
            assert c.h >= max(c.o, c.c) - 1e-12, \
                f"bougie {i} de {scene.id} : haut sous le corps"
            assert c.l <= min(c.o, c.c) + 1e-12, \
                f"bougie {i} de {scene.id} : bas au-dessus du corps"

    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_les_bougies_illustrent_un_mouvement(self, scene):
        prices = [c.c for c in scene.candles]
        assert len(set(prices)) > 1, f"{scene.id} n'illustre aucun mouvement"

    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_textes_sans_caractere_etranger(self, scene):
        """Un caractère CJK signalerait un artefact de génération à corriger."""
        blob = " ".join([scene.title, scene.principle, scene.takeaway]
                        + [s.title + s.text for s in scene.steps])
        for ch in blob:
            assert not ("一" <= ch <= "鿿"), \
                f"caractère CJK inattendu dans {scene.id} : {ch!r}"


class TestEtapes:
    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_les_etapes_sont_dans_la_plage(self, scene):
        for a in scene.annotations:
            if getattr(a, "step", None) is not None:
                assert 1 <= a.step <= len(scene.steps), \
                    f"{scene.id} : étape {a.step} hors plage"

    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_la_lecon_demarre_avec_un_apport_visuel(self, scene):
        assert 1 in _visual_steps(scene), \
            f"{scene.id} : la première étape n'apporte rien à l'écran"

    @pytest.mark.parametrize("scene", LESSONS, ids=_ids())
    def test_progression_visuelle_suffisante(self, scene):
        """Au moins la moitié des étapes doit ajouter un élément graphique."""
        visual = _visual_steps(scene)
        assert len(visual) >= len(scene.steps) / 2, \
            f"{scene.id} : {len(visual)} apport(s) visuel(s) pour {len(scene.steps)} étapes"
