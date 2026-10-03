"""Tests du modèle de scène : construction des bougies et des annotations."""
from __future__ import annotations

import math

import pytest

from core.model import Arrow, Level, Marker, Scene, Step, Zone, build, from_rows


class TestBuild:
    def test_premiere_bougie_utilise_le_prix_de_depart(self):
        candles = build(1.0850, [1.0860, 1.0870])
        assert candles[0].o == pytest.approx(1.0850)
        assert candles[0].c == pytest.approx(1.0860)

    def test_ouverture_suivant_la_cloture_precedente(self):
        candles = build(1.0850, [1.0860, 1.0870, 1.0865])
        assert candles[1].o == pytest.approx(candles[0].c)
        assert candles[2].o == pytest.approx(candles[1].c)

    def test_mèches_encadrent_le_corps(self):
        wick = 0.0004
        for c in build(1.0850, [1.0860, 1.0840, 1.0850]):
            assert c.h >= max(c.o, c.c)
            assert c.l <= min(c.o, c.c)
            assert c.h - max(c.o, c.c) == pytest.approx(wick)
            assert min(c.o, c.c) - c.l == pytest.approx(wick)

    def test_serie_vide(self):
        assert build(1.0850, []) == []

    def test_bougie_haussiere_et_baissiere(self):
        candles = build(1.0850, [1.0860, 1.0840])
        assert candles[0].bull is True
        assert candles[1].bull is False

    def test_bougie_neutre_est_consideree_haussiere(self):
        # à la clôture égale, on évite d'inventer une direction
        from core.model import Candle

        assert Candle(o=1.0, h=1.0, l=1.0, c=1.0).bull is True

    def test_top_et_bottom(self):
        from core.model import Candle

        c = Candle(o=1.0, h=1.5, l=0.5, c=1.2)
        assert c.top == 1.2
        assert c.bottom == 1.0


class TestFromRows:
    def test_quatre_colonnes(self):
        candles = from_rows([(1.0, 1.5, 0.5, 1.2)])
        assert len(candles) == 1
        assert candles[0].label is None and candles[0].step is None

    def test_label_et_step_en_option(self):
        candles = from_rows([(1.0, 1.5, 0.5, 1.2, "pin bar", 2)])
        assert candles[0].label == "pin bar"
        assert candles[0].step == 2

    def test_label_sans_step(self):
        candles = from_rows([(1.0, 1.5, 0.5, 1.2, "x")])
        assert candles[0].label == "x"
        assert candles[0].step is None


class TestLevel:
    def test_tag_text_avec_libelle(self):
        assert Level(price=1.085, label="Support").tag_text(5) == "Support 1.08500"

    def test_tag_text_sans_libelle(self):
        assert Level(price=1.085).tag_text(3) == "1.085"

    def test_tag_text_respecte_la_precision(self):
        assert Level(price=150.25, label="Pivot").tag_text(2) == "Pivot 150.25"


class TestSceneBuilders:
    def test_add_renvoie_la_scene_pour_le_chainage(self):
        scene = Scene(id="x", title="t", principle="p")
        assert scene.add(Level(price=1.0)) is scene

    def test_at_accepte_des_tuples(self):
        scene = Scene(id="x", title="t", principle="p")
        scene.at(("Titre", "Texte"))
        assert scene.steps == [Step(title="Titre", text="Texte")]

    def test_at_accepte_des_step(self):
        scene = Scene(id="x", title="t", principle="p")
        scene.at(Step(title="A", text="B"))
        assert scene.steps[0].title == "A"

    def test_at_melange_les_deux_formes(self):
        scene = Scene(id="x", title="t", principle="p")
        scene.at(("T", "x"), Step(title="S", text="y"))
        assert [s.title for s in scene.steps] == ["T", "S"]

    def test_last_index(self):
        scene = Scene(id="x", title="t", principle="p", candles=build(1.0, [1.1, 1.2, 1.3]))
        assert scene.last_index() == 2

    def test_last_index_sans_bougie(self):
        scene = Scene(id="x", title="t", principle="p")
        assert scene.last_index() == 0


class TestAnnotations:
    @pytest.mark.parametrize("item", [
        Level(price=1.0),
        Zone(low=1.0, high=1.1),
        Marker(index=0, price=1.0, text="x"),
    ])
    def test_kind_par_defaut_est_neutre(self, item):
        assert item.kind == "neutral"

    def test_arrow_vient_par_defaut_en_info(self):
        assert Arrow(x1=0, p1=1.0, x2=1, p2=1.1).kind == "info"

    def test_annotations_admettent_un_step(self):
        assert Level(price=1.0, step=2).step == 2
        assert Zone(low=1.0, high=1.1, step=3).step == 3

    def test_values_finies(self):
        for a in (Level(price=1.0), Zone(low=1.0, high=1.1), Arrow(x1=0, p1=1.0, x2=1, p2=1.1)):
            for v in vars(a).values():
                if isinstance(v, float):
                    assert math.isfinite(v)
