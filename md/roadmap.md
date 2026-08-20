# Roadmap 1 mois — Télédétection & analyse forestière (concepts, stack open source)

> Objectif : acquérir en 4 semaines les concepts fondamentaux nécessaires pour analyser des zones forestières par satellite (incendies, coupes, exploitation, régénération), en vue d'un produit commercial. Stack 100% open source : Google Earth Engine est exclu (licence commerciale payante), les données et outils utilisés sont tous libres d'usage commercial.

---

## Semaine 1 — Comprendre une donnée géospatiale avant de la manipuler

**Objectif** : savoir ce qu'on regarde avant de calculer quoi que ce soit dessus.

**Concepts à acquérir**
- **Vecteur vs raster** : un contour de forêt (polygone) n'a pas la même nature qu'une image satellite (grille de pixels) — comprendre quand utiliser l'un ou l'autre
- **Système de coordonnées (CRS)** : différence entre un CRS géographique (degrés, ex. WGS84) et un CRS projeté (mètres, ex. Lambert-93) — pourquoi calculer une surface en degrés est faux, et pourquoi certains calculs (angles, distances longues) préfèrent un CRS géographique
- **Résolution spatiale et résolution temporelle** : un pixel Sentinel-2 fait 10-20m de côté selon la bande ; le satellite repasse tous les ~5 jours en théorie, souvent moins en pratique
- **Bandes spectrales** : une image satellite n'est pas une photo, c'est un empilement de mesures à différentes longueurs d'onde (visible, proche infrarouge, infrarouge court) — chaque bande capture une information physique différente (végétation, humidité, chaleur)
- **Validité topologique** : un polygone peut être mal formé (auto-intersections, trous mal fermés) et fausser silencieusement les calculs en aval

**Quand ces concepts servent** : à chaque étape suivante — tout le reste de la roadmap repose sur ces bases. Sans elles, on calcule des chiffres qui semblent justes mais ne le sont pas (mauvais CRS, mauvaise bande, géométrie invalide).

**Exercice pratique**
Prendre un contour de zone forestière ou incendiée, vérifier sa validité, le reprojeter, calculer sa surface correctement, et l'associer à une image satellite de la même zone.

**Livrable** : une note d'une page qui explique, avec tes propres mots, pourquoi le choix du CRS et la validité géométrique ont un impact direct sur la fiabilité d'une analyse.

---

## Semaine 2 — Les indices spectraux et ce qu'ils mesurent réellement

**Objectif** : comprendre la physique derrière les indices utilisés en foresterie/incendie, pas seulement leur formule.

**Concepts à acquérir**
- **NDVI (indice de végétation)** : repose sur le contraste entre réflectance proche-infrarouge (forte pour la végétation vivante) et rouge (absorbée par la chlorophylle) — pourquoi une végétation stressée ou morte fait chuter cet indice
- **NBR et dNBR (sévérité de brûlure)** : repose sur le contraste proche-infrarouge / infrarouge court — pourquoi le sol brûlé et la végétation calcinée ont une signature très différente de la végétation saine, et comment on classe la sévérité (non brûlé, faible, modéré, fort) à partir d'un delta pré/post-événement
- **NDMI (humidité)** : utile pour distinguer stress hydrique et perte de végétation pure
- **Choix de la date de référence** : un indice seul ne dit rien, c'est la comparaison à un état antérieur (même saison, idéalement) qui donne un signal exploitable — piège classique : comparer deux dates de saisons différentes et confondre variation phénologique normale et vraie perturbation
- **Limites du satellite optique** : les nuages bloquent le signal ; plus la fréquence de passage utile (hors nuages) est faible, plus il est difficile de dater précisément un événement — un radar (signal différent, insensible aux nuages) peut combler ce manque quand la contrainte devient bloquante

**Quand ces concepts servent** : dès qu'on veut caractériser un état (brûlé/sain, stressé/vigoureux) plutôt que juste afficher une image. C'est la base de toute détection de perturbation forestière.

**Exercice pratique**
Sur une zone ayant subi une perturbation connue (incendie, coupe), calculer NDVI et dNBR avant/après, produire une carte de sévérité, et identifier une zone où le signal ne correspond pas à l'attendu — comprendre pourquoi.

**Livrable** : carte de sévérité + explication écrite du choix des dates de référence et des limites rencontrées (nuages, dates disponibles).

---

## Semaine 3 — Du constat ponctuel à la trajectoire dans le temps

**Objectif** : passer de "cette image montre une perturbation" à "cette parcelle a un historique caractéristique".

**Concepts à acquérir**
- **Série temporelle vs comparaison à deux dates** : une comparaison avant/après peut être trompeuse (bruit, nuage résiduel, saison) ; une série sur plusieurs mois/années donne une trajectoire plus fiable
- **Rupture de trajectoire (change detection)** : comment repérer une chute brutale et durable d'un indice, par opposition à une baisse ponctuelle et réversible (nuage mal filtré, variation saisonnière normale)
- **Phénologie forestière** : les feuillus ont un cycle saisonnier marqué (chute de feuilles en hiver, repousse au printemps), les résineux beaucoup moins — cela change complètement ce qu'on peut détecter et comment interpréter une baisse d'indice selon l'essence
- **Distinguer un feu d'une coupe** : les deux provoquent une chute d'indice, mais la forme de la trajectoire diffère (rapidité de la chute, texture du sol nu résultant, vitesse et régularité de la repousse — une repousse post-plantation est souvent plus homogène qu'une régénération naturelle post-feu)
- **Notion de "recovery"** : comment caractériser un retour à la normale (durée, vitesse, plateau atteint ou non) pour distinguer une perturbation ponctuelle d'une déforestation durable

**Quand ces concepts servent** : c'est le cœur de toute offre produit orientée "monitoring" ou "détection automatique" — sans ces notions, on ne fait que constater un événement déjà visible à l'œil nu, sans valeur ajoutée réelle.

**Exercice pratique**
Construire une trajectoire pluriannuelle d'indice sur 3-4 parcelles de nature différente (résineux, feuillus, une zone perturbée connue), et écrire pour chacune un diagnostic : perturbation ou non, type probable, statut de régénération.

**Livrable** : un document présentant les 3-4 trajectoires avec leur interprétation, et une règle simple (même approximative) qui permettrait de les classer automatiquement.

---

## Semaine 4 — Fiabiliser et faire tenir la démarche à l'échelle

**Objectif** : consolider les acquis en une méthode reproductible, avec un regard critique sur la fiabilité.

**Concepts à acquérir**
- **Validation croisée avec une source indépendante** : comment vérifier qu'un signal détecté correspond à une réalité terrain (cadastre forestier, imagerie très haute résolution ponctuelle, connaissance de terrain) plutôt que de faire confiance aveuglément à l'indice
- **Gestion des données manquantes** : comment définir un seuil raisonnable de tolérance aux trous temporels (nuages) sans soit rejeter presque toutes les zones, soit accepter des données trop clairsemées pour être fiables — c'est un arbitrage, pas un absolu
- **Passage à l'échelle** : ce qui change quand on passe d'une parcelle test à des centaines/milliers de parcelles — nécessité d'automatiser la détection d'anomalies (géométries invalides, données manquantes, indices aberrants) plutôt que de vérifier à l'œil
- **Restitution à un public non-technique** : transformer un indice ou une carte de sévérité en information actionnable et compréhensible (une carte simple avec légende claire vaut souvent mieux qu'un tableau de chiffres)
- **Enjeux de fiabilité pour un produit commercial** : la différence entre "ça marche sur mon exemple" et "je peux garantir un niveau de confiance" — notion de taux de faux positifs/négatifs, importance de documenter les limites connues plutôt que de les cacher

**Quand ces concepts servent** : au moment de transformer l'apprentissage en un outil ou un service vendable — c'est la différence entre un exercice technique et un produit sur lequel un client peut s'appuyer.

**Exercice pratique**
Reprendre les analyses des semaines précédentes, ajouter une étape de détection automatique d'anomalies (géométrie ou signal suspect), et rédiger une note tranchant explicitement : quel niveau de fiabilité peux-tu garantir aujourd'hui, et quelles sont les limites connues à communiquer honnêtement à un client potentiel.

**Livrable final** : une méthode documentée bout en bout (des données brutes au diagnostic), avec ses limites explicitées — la base d'un argumentaire produit crédible.

---

## Comment utiliser cette roadmap comme prompt LLM

Pour chaque semaine, tu peux transformer la section correspondante en prompt du type :

```
Contexte : [décrire brièvement où tu en es dans ton projet]
Objectif de la session : [coller l'objectif de la semaine]
Concepts à couvrir : [coller la liste]
Je veux que tu me poses des questions une par une, auxquelles je réponds
en écrivant et exécutant du code, en me concentrant sur la compréhension
des concepts plutôt que sur une librairie en particulier.
```

## Note sur les outils
Volontairement, cette roadmap ne cite pas d'outils précis : le choix des librairies est secondaire et peut évoluer, alors que les concepts (physique des indices, phénologie, gestion du CRS, fiabilité) restent valables quel que soit l'outil utilisé pour les mettre en œuvre. Les seules contraintes fixées sont : données satellite Sentinel (Copernicus, licence ouverte, utilisables commercialement) et outils open source pour le traitement — pas de dépendance à une API propriétaire soumise à changement de licence.