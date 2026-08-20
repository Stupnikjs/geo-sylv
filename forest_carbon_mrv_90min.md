# Sprint 90 minutes — Forest Carbon MRV

## Objectif de la session

Mettre en place un environnement de travail **minimal, propre et reproductible** pour commencer le premier POC de monitoring satellite de projets forestiers carbone.

À la fin des 90 minutes, l'objectif n'est **pas** d'avoir un modèle ML ni un produit fini.

L'objectif est d'avoir :

- un repository Git propre ;
- un environnement Python `venv` fonctionnel ;
- `pip` comme gestionnaire de dépendances ;
- un notebook Jupyter ;
- les principales librairies géospatiales installées ;
- une structure de données simple ;
- un premier projet forestier réel identifié ;
- idéalement une première connexion aux données Sentinel-2 ;
- quelques notes métier permettant de guider les prochaines étapes.

> **Principe : explorer avant d'architecturer.**
>
> Pas de package Python, pas de `src/`, pas de Docker, pas de cloud infrastructure, pas de deep learning aujourd'hui.

---

# 0–10 min — Créer le repository

## 1. Créer le dossier

```bash
mkdir forest-carbon-mrv
cd forest-carbon-mrv
```

Initialiser Git :

```bash
git init
```

Créer les dossiers :

```bash
mkdir -p data/raw
mkdir -p data/processed
mkdir -p data/projects
mkdir -p notebooks
mkdir -p docs
```

Créer les fichiers :

```bash
touch README.md
touch requirements.txt
touch .gitignore
touch docs/domain.md
```

Structure attendue :

```text
forest-carbon-mrv/
├── .gitignore
├── README.md
├── requirements.txt
├── data/
│   ├── raw/
│   ├── processed/
│   └── projects/
├── notebooks/
└── docs/
    └── domain.md
```

---

# 10–20 min — Créer l'environnement Python

Créer le virtual environment :

```bash
python -m venv .venv
```

## Activation

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scriptsctivate
```

Vérifier :

```bash
python --version
which python
```

Sous Windows :

```powershell
where python
```

Le Python utilisé doit être celui de `.venv`.

Mettre `pip` à jour :

```bash
python -m pip install --upgrade pip
```

---

# 20–30 min — Installer les dépendances

Pour le premier POC, rester volontairement minimal.

`requirements.txt` :

```text
numpy
pandas
geopandas
shapely
pyproj
rasterio
rioxarray
xarray
matplotlib
jupyter
pystac-client
stackstac
planetary-computer
```

Installer :

```bash
pip install -r requirements.txt
```

Tester les imports :

```bash
python -c "import numpy, pandas, geopandas, rasterio, xarray, pystac_client, stackstac; print('Environment OK')"
```

Si tout fonctionne :

```bash
pip freeze > requirements-lock.txt
```

Le fichier `requirements.txt` reste la liste des dépendances principales.

`requirements-lock.txt` sert de snapshot de l'environnement actuel.

---

# 30–35 min — Configurer Git

`.gitignore` :

```text
.venv/
__pycache__/
.ipynb_checkpoints/
*.pyc

data/raw/
data/processed/

.env
.DS_Store
```

Vérifier :

```bash
git status
```

Premier commit :

```bash
git add .
git commit -m "Initial forest carbon MRV environment"
```

---

# 35–40 min — Créer le notebook

Lancer Jupyter :

```bash
jupyter notebook
```

Créer :

```text
notebooks/01_first_project.ipynb
```

Titre du notebook :

```markdown
# Forest Carbon MRV — First Project

Premier test de monitoring satellite d'un projet forestier carbone.

Objectif :
- charger une géométrie forestière ;
- rechercher des observations Sentinel-2 ;
- construire une première série temporelle ;
- calculer NDVI / NDMI / NBR ;
- identifier les premières anomalies ;
- documenter les questions métier.
```

---

# 40–50 min — Préparer le premier projet

## Objectif

Ne pas chercher immédiatement 100 projets.

Trouver **un seul projet réel** avec :

- géométrie exploitable ;
- localisation connue ;
- méthode LBC connue si possible ;
- date de début connue ;
- contexte forestier identifiable ;
- idéalement un événement connu : incendie, tempête, dépérissement, crise sanitaire, etc.

## Informations à enregistrer

Dans `data/projects/`, créer par exemple :

```text
project_001/
```

Avec éventuellement :

```text
geometry.geojson
metadata.md
```

Le `metadata.md` peut contenir :

```markdown
# Project 001

## Identification

Project ID:
Nom:
Méthode LBC:
Région:
Département:

## Forêt

Surface:
Type de peuplement:
Essence dominante:
Âge approximatif:

## Projet carbone

Date de labellisation:
Date de début:
Événement initial:

## Sources

Registre:
Document méthodologique:
Autres sources:

## Questions

- Quel était l'état initial ?
- Quel événement doit être détectable par satellite ?
- Existe-t-il une date connue de l'événement ?
- Existe-t-il une vérité terrain ?
```

---

# 50–65 min — Première connexion à Sentinel-2

## Objectif

Ne pas télécharger toute une scène Sentinel.

Utiliser un catalogue STAC pour rechercher les observations qui intersectent la géométrie du projet.

Dans le notebook :

1. charger la géométrie ;
2. afficher la géométrie ;
3. rechercher les observations Sentinel-2 ;
4. filtrer par période ;
5. filtrer par couverture nuageuse ;
6. inspecter les dates disponibles.

Exemple de logique :

```python
import geopandas as gpd
import pystac_client

project = gpd.read_file("../data/projects/project_001/geometry.geojson")

project
```

Puis ouvrir un catalogue STAC compatible avec Sentinel-2.

L'objectif de cette session est simplement de vérifier que la recherche fonctionne.

Tu dois pouvoir obtenir quelque chose ressemblant à :

```text
date         cloud_cover
2024-03-12   4%
2024-03-17   12%
2024-04-01   2%
...
```

---

# 65–75 min — Construire la première série temporelle

Si l'accès aux données fonctionne, calculer une première statistique par observation.

Pour commencer, ne cherche pas une analyse pixel-perfect.

Calculer une statistique simple sur la géométrie :

```text
date
mean NDVI
median NDVI
valid_fraction
```

Puis faire la même chose pour :

```text
NDMI
NBR
```

## NDVI

```text
NDVI = (NIR - Red) / (NIR + Red)
```

Avec Sentinel-2 :

```text
NIR = B08
Red = B04
```

## NDMI

```text
NDMI = (NIR - SWIR) / (NIR + SWIR)
```

Une première approximation :

```text
NIR  = B08
SWIR = B11
```

## NBR

```text
NBR = (NIR - SWIR2) / (NIR + SWIR2)
```

Avec :

```text
NIR   = B08
SWIR2 = B12
```

---

# 75–82 min — Première visualisation

Créer au minimum un graphique :

```text
Date → NDVI moyen
```

Puis, si le temps le permet :

```text
Date → NDMI moyen
Date → NBR moyen
```

Le but n'est pas d'obtenir un beau graphique.

Le but est de pouvoir regarder la forêt et commencer à se demander :

> Que s'est-il passé ici ?

Chercher visuellement :

- rupture brutale ;
- baisse progressive ;
- récupération ;
- saisonnalité ;
- périodes sans données ;
- valeurs aberrantes.

---

# 82–87 min — Journal métier

Ouvrir :

```text
docs/domain.md
```

Ajouter ce que tu as appris aujourd'hui.

Structure recommandée :

```markdown
# Forest Carbon MRV — Domain Notes

## Concepts appris

### Dépérissement

Notes...

### Chablis

Notes...

### Reconstitution

Notes...

### Projet LBC

Notes...

## Questions ouvertes

- Comment un forestier définit-il un dépérissement significatif ?
- Quelle durée de baisse du NDVI est réellement pertinente ?
- Comment distinguer une éclaircie d'un dépérissement ?
- Quel rôle joue l'essence ?
- Quel rôle joue l'âge du peuplement ?
- Quelle résolution spatiale est utile pour la décision terrain ?

## Hypothèses produit

- Une surveillance continue peut détecter des événements entre deux audits.
- Une anomalie satellite ne doit pas être présentée comme une preuve de causalité.
- Le système doit prioriser les zones à inspecter plutôt que prétendre remplacer le terrain.
```

---

# 87–90 min — Commit + bilan

Sauvegarder le notebook.

Vérifier :

```bash
git status
```

Commit :

```bash
git add .
git commit -m "First forest project and Sentinel-2 exploration"
```

Puis écrire dans le README :

```markdown
## Current status

- [x] Python environment
- [x] Geospatial dependencies
- [x] Jupyter notebook
- [x] First project identified
- [ ] Sentinel-2 time series
- [ ] NDVI
- [ ] NDMI
- [ ] NBR
- [ ] Change detection
- [ ] Expert validation
```

---

# Ce qui constitue une réussite après 90 minutes

## Minimum acceptable

Tu as :

- Git ;
- `venv` ;
- `pip` ;
- les dépendances installées ;
- un notebook ;
- un projet forestier identifié.

## Très bon résultat

Tu as également :

- la géométrie du projet ;
- une recherche STAC fonctionnelle ;
- plusieurs observations Sentinel-2 ;
- une première série temporelle.

## Excellent résultat

Tu as :

- NDVI ;
- NDMI ;
- NBR ;
- graphiques temporels ;
- une première anomalie potentielle ;
- une liste de questions à poser à un forestier.

---

# Ce qu'il ne faut PAS faire aujourd'hui

Ne pas commencer :

- deep learning ;
- biomasse ;
- estimation de tonnes CO2 ;
- fusion Sentinel-1/Sentinel-2 ;
- U-Net ;
- Random Forest ;
- classification complexe ;
- dashboard ;
- API ;
- SaaS ;
- Docker ;
- PostGIS ;
- architecture `src/` ;
- tests unitaires complets ;
- CI/CD.

Le projet est encore au stade **exploration + validation**.

---

# Règle pour les prochaines semaines

Le notebook est ton laboratoire.

Tu ne crées un fichier `.py` que lorsqu'une logique :

1. fonctionne ;
2. est répétée ;
3. mérite d'être réutilisée.

Exemple :

```text
Aujourd'hui
    ↓
Notebook
    ↓
Même code utilisé 3 fois
    ↓
Extraction dans sentinel.py
```

Puis éventuellement :

```text
sentinel.py
metrics.py
```

Pas avant.

---

# La trajectoire du projet

```text
Projet forestier réel
        ↓
Série temporelle Sentinel-2
        ↓
Observation du changement
        ↓
Détection d'anomalie
        ↓
Validation avec un forestier
        ↓
Compréhension métier
        ↓
Meilleure détection
        ↓
Monitoring automatisé
        ↓
Produit MRV forestier
        ↓
Forest Carbon Intelligence
```

Le point clé est que **la donnée et le métier doivent progresser ensemble**.

Tu ne cherches pas encore à prouver que ton modèle est performant.

Tu cherches à apprendre :

> **"À quoi ressemble réellement une forêt vue par satellite lorsqu'il se passe quelque chose d'important pour un projet carbone ?"**

C'est la question de départ du projet.
