"""
Contrôle de la documentation.

Vérifie ce qui casse silencieusement la lecture : références à des fichiers
inexistants, et caractères parasites restés dans les textes.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = [ROOT / "README.md", *sorted((ROOT / "doc").glob("*.md"))]


def _docs() -> list[Path]:
    return [d for d in DOCS if d.exists()]


class TestDocumentationPresente:
    def test_readme_present(self):
        assert (ROOT / "README.md").exists()

    def test_guide_utilisateur_present(self):
        assert (ROOT / "doc" / "GUIDE_UTILISATEUR.md").exists()

    def test_les_docs_sont_lisibles(self):
        for d in _docs():
            assert d.read_text(encoding="utf-8").strip(), f"{d.name} est vide"


class TestTextesPropres:
    @pytest.mark.parametrize("doc", _docs(), ids=lambda d: d.name)
    def test_aucun_caractere_cjk(self, doc):
        """Un caractère CJK signale un artefact de génération à corriger."""
        texte = doc.read_text(encoding="utf-8")
        for ch in texte:
            assert not ("一" <= ch <= "鿿"), \
                f"caractère CJK inattendu dans {doc.name} : {ch!r}"

    @pytest.mark.parametrize("doc", _docs(), ids=lambda d: d.name)
    def test_pas_de_mot_anglais_court_incoherent(self, doc):
        """Repère les morceaux de texte resté dans une autre langue."""
        texte = doc.read_text(encoding="utf-8")
        # mots anglais très improbables dans un texte français sur le trading
        for mot in ("the ", "buyer", "masteriser", "refuse le"):
            assert mot not in texte, f"« {mot} » suspect dans {doc.name}"


class TestReferences:
    """Les chemins cités dans le README doivent exister."""

    def _refs(self) -> set[str]:
        """Références de type chemin (`src/core/model.py`, `requirements.txt`).

        On ignore les noms de fichiers cités seuls en prose (`audit.py`) : ils ne
        donnent pas de chemin et seraient trop ambigus à résoudre.
        """
        texte = (ROOT / "README.md").read_text(encoding="utf-8")
        return {
            r for r in re.findall(r"`([\w/.-]+\.py|[\w/.-]+\.txt)`", texte)
            if "/" in r
        }

    def test_aucune_reference_trouee(self):
        manquants = [r for r in self._refs() if not (ROOT / r).exists()]
        assert not manquants, f"fichiers cités mais absents : {manquants}"
