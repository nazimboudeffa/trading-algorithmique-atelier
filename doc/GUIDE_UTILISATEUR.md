# Guide utilisateur — Atelier Price Action

> Guide pratique pour installer, lancer et parcourir l'atelier.
> Le README décrit la structure du projet ; ce guide décrit l'usage.

---

## 1. Installation

L'atelier n'a besoin que de Python et de Qt. **Pas de connexion réseau, pas
d'Ollama, pas de données de marché.**

```bash
setup.bat
```

Le script crée `.venv` puis installe les dépendances. C'est à faire une seule
fois.

> Python 3.10 ou plus récent. `setup.bat` utilise `py -3.14` ; adaptez la version
> si votre installation diffère.

---

## 2. Lancement

```bash
run.bat
```

La fenêtre s'ouvre sur la première leçon. Vous pouvez aussi lancer directement :

```bash
.venv\Scripts\python.exe src\main.py
```

---

## 3. Navigation

### 3.1 Choisir une leçon

La liste de gauche contient les 22 leçons, dans l'ordre du programme :

| | Leçon | Ce qu'elle montre |
|---|---|---|
| **Structure** | Tendance haussière : HH + HL | des sommets et creux qui montent |
| | Tendance baissière : LH + LL | des sommets et creux qui descendent |
| | Range : aucune direction | pourquoi le milieu d'un range est mort |
| | La structure se casse | le Lower Low, signal de retournement |
| **Support / résistance** | Un niveau est une zone | pourquoi 1,08500 n'est pas un chiffre |
| | Le retournement | un support cassé devient résistance |
| | Ce qui rend un niveau solide | les tests qui affaiblissent la zone |
| **Liquidité** | Les sommets égaux | les stops au-dessus, et l'attrait |
| | Le sweep | prendre la liquidité puis revenir |
| | Le piège du sweep | pourquoi un sweep isolé ne dit rien |
| **Order blocks** | Haussier | la dernière bougie de vente |
| | Baissier | la dernière bougie d'achat |
| **FVG** | Haussier | le trou entre les bougies 1 et 3 |
| | Baissier | le trou inverse |
| **Bougies** | Le pin bar | la longue mèche = rejet |
| | L'engulfing | la reprise de contrôle |
| | L'inside bar | la compression avant le départ |
| **Cassure / retest** | Entrer sur le retest | pourquoi pas sur la cassure |
| | Le faux breakout | exiger une clôture, pas une mèche |
| **Risque** | Anatomie d'un trade | entrée, stop, cible |
| | Le ratio R:R | la règle des 2:1 |
| | La taille de position | risquer 1 %, par trade |

### 3.2 Avancer dans une leçon

Chaque leçon se lit en trois étapes. Le schéma se construit sous vos yeux : à
chaque étape, un élément s'ajoute et l'explication change.

- **→** ou **Suivant ▶** : étape suivante
- **←** ou **◀ Précédent** : étape précédente
- **Tout voir** : le schéma complet, d'un coup

**↑ / ↓** changent de leçon. En haut et en bas de la fenêtre, deux boutons font
de même.

> Un flèche en haut à droite du graphique passe d'une étape à l'autre ; le
> schéma déjà révélé le reste, ce qui permet de relire une étape en gardant le
> contexte.

---

## 4. Comment lire une leçon

Chaque leçon est encadrée par trois blocs :

- **Principe** (en haut, bleu) — la règle en une phrase. C'est ce qu'il faut
  retenir si vous ne lisez rien d'autre.
- **À retenir** (en bas, orange) — la nuance, le piège, la limite. C'est ce qui
  distingue une compréhension correcte d'une simple récitation.

Entre les deux, l'étape courante. Le cadre du graphique se resserre sur l'étape
active pour signaler ce qui vient d'apparaître.

Les couleurs ont un sens constant dans tout l'atelier :

| Couleur | Sens |
|---|---|
| Vert | haussier, favorable, soutien qui tient |
| Rouge | baissier, défavorable, ce qui casse |
| Orange | avertissement, zone d'attention |
| Bleu | entrée, information neutre |
| Violet | liquidité (les stops des autres) |
| Turquoise | support |
| Ambre | order block |

---

## 5. Ce que l'atelier n'est pas

L'atelier ne tire aucun signal, ne conectado à aucun broker et ne trace aucun
ordre. Les schémas sont **synthétiques** : ils ont été construits pour
illustrer une notion, pas relevés sur le marché.

C'est un choix : un graphique réel serait bruité, et une formation serait
approximative (« à peu près un pin bar ? »). Ici, chaque schéma est le cas
idéal — et beaucoup de leçons montrent aussi le cas où on se trompe.

Les notions sont décrites, pas recommandées. Un order block n'est pas un signal
d'achat ; un FVG n'est pas un prédicteur de direction. L'atelier le dit à
chaque fois, parce que c'est là que se font les mauvaises interprétations.

---

## 6. Raccourcis

| Touche | Action |
|---|---|
| **←** | étape précédente |
| **→** | étape suivante |
| **↑** | leçon précédente |
| **↓** | leçon suivante |
| Clic sur une leçon | y aller directement |

---

## 7. En cas de problème

**La fenêtre s'ouvre noire ou reste vide**
Lancez depuis le terminal pour voir l'erreur :
`.venv\Scripts\python.exe src\main.py`

**« Qt platform plugin could not be loaded »**
Le Qt est mal installé. Rejouez `setup.bat`.

**Un schéma semble décalé**
Lancez l'audit, qui vérifie la mise en page de toutes les leçons :
`.venv\Scripts\python.exe src\tools\audit.py`

**Les polices sont bizarres**
L'atelier utilise Segoe UI, présente sur Windows. Sur un autre système, la
police de remplacement s'utilise automatiquement ; l'affichage reste correct.

---

## 8. Avertissement

Cet atelier est un support d'apprentissage. Il ne constitue aucun conseil en
investissement, aucune recommandation financière, et ne comporte aucun conseil
d'achat ou de vente.

**Si vous tradez, vous pouvez perdre une part importante de votre capital,
voire la totalité de ce qui est engagé.** N'utilisez jamais ce type d'outil
avec de l'argent que vous ne pouvez pas perdre. Vous le faites à vos seuls
risques et sous votre entière responsabilité.
