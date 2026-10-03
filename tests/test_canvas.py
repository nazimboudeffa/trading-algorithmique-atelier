"""Tests du canevas : géométrie, conversion des coordonnées, révélation."""
from __future__ import annotations

import pytest

from core.canvas import MARGIN_LEFT, MARGIN_RIGHT
from core.model import Level, Marker, Path, Scene, Zone, build

pytestmark = pytest.mark.usefixtures("app")


def _scene(n=10, start=1.0850, closes=None) -> Scene:
    closes = closes or [start + 0.0001 * (i + 1) for i in range(n)]
    return Scene(id="t", title="Test", principle="p", candles=build(start, closes))


class TestLayout:
    def test_bornes_incluent_le_padding(self, canvas):
        scene = _scene()
        canvas.set_scene(scene)
        g = canvas._layout()
        lows = [c.l for c in scene.candles]
        highs = [c.h for c in scene.candles]
        assert g["lo"] < min(lows)
        assert g["hi"] > max(highs)

    def test_bornes_incluent_les_annotations(self, canvas):
        scene = _scene()
        scene.add(Level(price=1.0900), Marker(index=0, price=1.0800, text="x"))
        canvas.set_scene(scene)
        g = canvas._layout()
        assert g["lo"] <= 1.0800
        assert g["hi"] >= 1.0900

    def test_bornes_tiennent_pour_une_serie_plate(self, canvas):
        scene = Scene(id="t", title="T", principle="p",
                      candles=build(1.0, [1.0, 1.0, 1.0], wick=0.0))
        canvas.set_scene(scene)
        g = canvas._layout()
        assert g["hi"] > g["lo"]

    def test_conversion_prix_est_reversible(self, canvas):
        canvas.set_scene(_scene())
        g = canvas._layout()
        for price in (g["lo"] * 0.5, 1.0855, g["hi"] * 0.99):
            assert g["price"](g["y"](price)) == pytest.approx(price, abs=1e-9)

    def test_un_prix_plus_haut_est_plus_haut_a_l_ecran(self, canvas):
        canvas.set_scene(_scene())
        g = canvas._layout()
        assert g["y"](1.0900) < g["y"](1.0800)

    def test_rectangle_du_graphe_respecte_marges(self, canvas):
        rect = canvas._plot_rect()
        assert rect.left() == MARGIN_LEFT
        assert canvas.width() - rect.right() == pytest.approx(MARGIN_RIGHT)


class TestPasDeScene:
    def test_layout_sans_bougies_ne_plante_pas(self, canvas):
        assert canvas._layout()["n"] == 1

    def test_set_scene_none(self, canvas):
        canvas.set_scene(None)
        assert canvas.scene() is None


class TestRevelationProgressive:
    def test_sans_etape_tout_est_visible(self, canvas):
        scene = _scene()
        scene.add(Level(price=1.0855, step=1), Level(price=1.0856, step=3))
        canvas.set_scene(scene)
        assert canvas._visible(Level(price=1.0855, step=3)) is True

    def test_etape_1_ne_montre_pas_l_etape_3(self, canvas):
        canvas.set_scene(_scene())
        canvas.set_step(1)
        assert canvas._visible(Level(price=1.0, step=1)) is True
        assert canvas._visible(Level(price=1.0, step=3)) is False

    def test_annotations_sans_step_sont_toujours_visibles(self, canvas):
        canvas.set_scene(_scene())
        canvas.set_step(1)
        assert canvas._visible(Level(price=1.0)) is True

    def test_etape_courante_est_mise_en_evidence(self, canvas):
        canvas.set_scene(_scene())
        canvas.set_step(2)
        assert canvas._is_current(Level(price=1.0, step=2)) is True
        assert canvas._is_current(Level(price=1.0, step=1)) is False

    def test_sans_etape_active_aucune_mise_en_evidence(self, canvas):
        canvas.set_scene(_scene())
        canvas.set_step(None)
        assert canvas._is_current(Level(price=1.0, step=1)) is False

    def test_set_scene_reinitialise_l_etape(self, canvas):
        canvas.set_scene(_scene())
        canvas.set_step(2)
        canvas.set_scene(_scene())
        assert canvas.step() is None


class TestEtiquettes:
    def test_tag_rect_contient_le_texte(self, canvas):
        from PySide6.QtGui import QFontMetrics

        from core.canvas import _font

        text = "Support 1.08500"
        r = canvas.tag_rect(text, 100, 100)
        assert r.width() >= QFontMetrics(_font(8)).horizontalAdvance(text)

    def test_etiquette_rentree_dans_le_cadre_a_droite(self, canvas):
        rect = canvas._plot_rect()
        x = rect.right() + 500
        w = 120.0
        assert canvas._clamp_tag(x, 100, w) == pytest.approx(rect.right() - w)

    def test_etiquette_rentree_dans_le_cadre_a_gauche(self, canvas):
        rect = canvas._plot_rect()
        assert canvas._clamp_tag(rect.left() - 500, 100, 120.0) == pytest.approx(rect.left())

    def test_etiquette_dedans_nest_pas_deplacee(self, canvas):
        rect = canvas._plot_rect()
        x = rect.left() + 100
        assert canvas._clamp_tag(x, 100, 50.0) == pytest.approx(x)


class TestRendu:
    @pytest.mark.parametrize("step", [None, 1, 2, 3])
    def test_paint_ne_lève_pas_erreur(self, canvas, step):
        scene = _scene()
        scene.add(
            Level(price=1.0855, label="Support", step=1),
            Zone(low=1.0845, high=1.0848, label="zone", step=2),
            Marker(index=3, price=1.0856, text="marqueur", step=3),
            Path(points=[(0, 1.0850), (5, 1.0860)], label="HH", step=1, dots=True),
        )
        canvas.set_scene(scene)
        canvas.set_step(step)
        canvas.repaint()  # ne doit pas lever

    def test_scene_vide_ne_plante_pas(self, canvas):
        canvas.set_scene(Scene(id="x", title="T", principle="p"))
        canvas.repaint()
