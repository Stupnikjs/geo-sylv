# Sylviculture géospatiale — au-delà des indices spectraux

*Ce cours suppose acquis : vecteur/raster, CRS, résolution Sentinel-2, NDVI/NBR/NDMI, phénologie, détection de rupture, geopandas/rasterio/rioxarray/shapely/pyproj/STAC. On ne revient sur aucun de ces points. L'objectif ici est d'ouvrir les couches suivantes : structure 3D, radar, apprentissage automatique spatial, biomasse/carbone, cadre réglementaire, architecture de production.*

---

## 1. La limite structurelle de l'optique passif — et pourquoi la 3D change tout

Un indice spectral (NDVI, NBR) décrit une **surface** : la réflectance du sommet de la canopée. Il ne dit rien sur ce qui se trouve dessous — hauteur des arbres, densité du sous-étage, stratification verticale du peuplement. Deux forêts avec un NDVI identique peuvent avoir des volumes sur pied radicalement différents (jeune plantation dense vs futaie mature clairsemée).

### 1.1 LiDAR aéroporté (ALS) — mesurer la structure, pas juste la couleur

Le LiDAR (Light Detection And Ranging) émet des impulsions laser et mesure le temps de retour de chaque écho. Contrairement à l'optique, un faisceau laser peut traverser partiellement une canopée et renvoyer plusieurs échos : un pour le sommet des arbres, d'autres pour les strates intermédiaires, un dernier pour le sol nu (si la végétation n'est pas totalement fermée).

À partir d'un nuage de points LiDAR classé (sol / végétation), on dérive trois surfaces raster fondamentales :

- **DTM (Digital Terrain Model)** : altitude du sol nu, obtenue en interpolant uniquement les échos classés "sol"
- **DSM (Digital Surface Model)** : altitude du point le plus haut à chaque position (sommet de canopée compris)
- **CHM (Canopy Height Model)** : `CHM = DSM − DTM`, la hauteur de végétation au-dessus du sol, indépendante du relief

Le CHM est l'objet central de la foresterie LiDAR : il permet de calculer une hauteur dominante par parcelle, de segmenter des houppiers individuels, et sert d'entrée à la quasi-totalité des modèles de biomasse structurelle.

**Point de vigilance méthodologique** : la qualité du DTM dépend de la densité de pénétration du signal au sol. En forêt très dense (résineux serrés, sous-bois épais), peu d'échos atteignent le sol — le DTM peut être localement biaisé, ce qui fausse le CHM en aval même si les mesures de hauteur brute sont correctes. C'est un problème d'échantillonnage, pas de précision instrumentale.

### 1.2 Segmentation d'arbres individuels (ITC — Individual Tree Crown delineation)

Sur un CHM à résolution fine (< 1m), on peut appliquer des algorithmes de segmentation pour isoler chaque houppier individuellement plutôt que de raisonner à l'échelle de la parcelle :

- **Watershed** (ligne de partage des eaux) appliqué à l'inverse du CHM : chaque maximum local (sommet d'arbre) devient un bassin versant, dont les limites approximent les frontières entre houppiers voisins
- **Détection de maxima locaux** avec une fenêtre de taille adaptative (souvent proportionnelle à la hauteur elle-même, car un grand arbre a statistiquement un houppier plus large)

Chaque arbre segmenté devient une entité géométrique (polygone) à laquelle on peut associer des attributs : hauteur, surface de houppier, position (X,Y,Z), et in fine une estimation de diamètre et de volume via des relations allométriques (section suivante). C'est le socle des inventaires forestiers "arbre par arbre" à grande échelle, en rupture avec l'inventaire par placette échantillonnée au sol.

**Limite connue** : la segmentation ITC fonctionne bien en peuplement régulier (plantation, résineux) et se dégrade en forêt mélangée dense où les houppiers se chevauchent fortement — sur-segmentation ou fusion d'arbres voisins sont les deux modes d'erreur classiques, à quantifier avant de vendre un chiffre d'inventaire.

### 1.3 LiDAR spatial et données ouvertes

Le LiDAR aéroporté est cher à acquérir en propre, mais plusieurs sources ouvertes existent :

- **Lidar HD (IGN, France)** : couverture nationale en cours de complétion, licence ouverte, nuage de points classé disponible en téléchargement libre — une ressource considérable pour un produit français
- **GEDI (Global Ecosystem Dynamics Investigation)** : LiDAR spatial embarqué sur l'ISS, mesures en trace (footprint ~25m, pas une couverture continue), mais donne une hauteur de canopée et une structure verticale exploitables en complément statistique sur de vastes zones, gratuit
- **ICESat-2** : LiDAR spatial similaire, complémentaire à GEDI en termes de couverture latitudinale

Le LiDAR spatial ne remplace pas l'ALS aéroporté en résolution, mais permet un étalonnage ou une extrapolation de modèles de hauteur/biomasse sur des zones où aucun survol aérien n'existe.

---

## 2. Le radar — l'angle mort de tout ce qui précède

Tout ce qui a été vu jusqu'ici (semaines 1 à 3 de la roadmap initiale) repose sur l'optique passif : Sentinel-2 mesure la lumière solaire réfléchie. Deux limites structurelles en découlent, que le radar contourne par construction.

### 2.1 Pourquoi le radar est insensible aux nuages

Un capteur radar (SAR — Synthetic Aperture Radar) est un capteur **actif** : il émet lui-même une onde micro-ondes et mesure le signal rétrodiffusé (backscatter). Cette longueur d'onde (bande C pour Sentinel-1, ~5.6 cm) traverse les nuages sans atténuation significative, et fonctionne de nuit puisqu'elle ne dépend d'aucun éclairage solaire. Pour une zone tropicale ou une région à couverture nuageuse persistante — précisément là où la déforestation est souvent la plus critique — c'est la différence entre un suivi mensuel réaliste et un suivi optique dégradé à quelques images exploitables par an.

### 2.2 Ce que mesure réellement le backscatter radar

Le signal radar rétrodiffusé dépend de la **structure géométrique** de la cible et de ses propriétés diélectriques (liées à l'humidité), pas de sa couleur ou de sa composition chimique. Concrètement :

- Une surface lisse (eau calme, sol nu compacté) réfléchit le signal de façon spéculaire, loin du capteur → backscatter faible
- Une canopée forestière, avec sa structure complexe (troncs, branches, feuillage à toutes les échelles), génère une rétrodiffusion volumique importante → backscatter élevé
- Un sol nu rugueux ou une coupe rase se situe entre les deux, avec un signal intermédiaire dépendant fortement de l'humidité du sol

La **coupe forestière** produit donc une chute de backscatter nette et rapide — signal exploitable indépendamment de tout NDVI ou passage optique. Sentinel-1 (bande C, deux polarisations VV et VH disponibles en Europe) permet ainsi une détection de coupe quasi temps réel, tout temps, sans dépendre de la disponibilité d'images optiques propres.

### 2.3 Polarisation — une dimension d'information supplémentaire

Le signal radar peut être émis et reçu selon différentes polarisations (verticale V, horizontale H). Sentinel-1 fournit typiquement VV et VH :

- **VV (co-polarisé)** : plus sensible à la structure du sol et à l'humidité
- **VH (croisé)** : la dépolarisation du signal croisé est particulièrement sensible à la diffusion volumique complexe — donc à la structure de la canopée forestière elle-même

Le **ratio VH/VV** ou sa différence est souvent utilisé comme proxy structurel de densité de couvert forestier, un peu comme le NDVI l'est pour la vigueur en optique — mais avec une physique complètement différente et complémentaire.

### 2.4 InSAR — la cohérence interférométrique comme signal de perturbation

Au-delà du simple backscatter, deux acquisitions radar de la même zone à des dates différentes peuvent être comparées en phase (pas seulement en amplitude), donnant une mesure de **cohérence interférométrique**. Une surface stable dans le temps (bâti, sol nu) garde une cohérence de phase élevée d'une acquisition à l'autre. Une canopée forestière, en mouvement constant (vent, croissance), a naturellement une cohérence faible et volatile — mais une **coupe rase** provoque un changement radical et durable de cette signature de cohérence, exploitable comme signal de détection indépendant du backscatter brut. C'est une piste plus avancée, moins accessible en traitement (nécessite des paires cohérentes, un pré-traitement InSAR spécifique), mais avec un fort potentiel de détection précoce.

### 2.5 Limites du radar à connaître avant de le vendre comme solution miracle

- **Speckle** : le radar souffre d'un bruit multiplicatif caractéristique (chatoiement) nécessitant un filtrage spécifique (Lee, Frost, ou moyennage temporel) avant toute interprétation pixel à pixel — ignorer ce bruit produit de fausses détections de changement
- **Sensibilité à l'humidité du sol** : une pluie récente peut faire varier le backscatter d'une parcelle non perturbée de façon suffisante pour ressembler à un faux signal de changement, un piège classique en zone tropicale humide
- **Effets géométriques de relief** (foreshortening, layover, ombre radar) : en terrain montagneux, la géométrie d'acquisition oblique du radar déforme fortement le signal sur les pentes, un problème quasi inexistant en optique nadir

---

## 3. Apprentissage automatique spatial — au-delà du seuil sur un indice

Toute la roadmap initiale raisonne par seuils et règles (dNBR > x → sévérité forte). C'est robuste et interprétable, mais ça plafonne vite en précision dès que le paysage se complexifie (mélange d'essences, gradients de sévérité continus, confusion coupe/feu/chablis). Le passage à l'apprentissage automatique est l'étape suivante logique — avec des pièges spécifiques au domaine spatial qu'il faut connaître avant de se lancer.

### 3.1 Modèles classiques sur features tabulaires (Random Forest, Gradient Boosting)

L'approche la plus courante et la plus robuste en foresterie opérationnelle : pour chaque pixel ou chaque parcelle, on construit un vecteur de caractéristiques (features) — valeurs de plusieurs bandes optiques, plusieurs indices, statistiques de texture, valeurs radar, hauteur LiDAR si disponible — et on entraîne un modèle de classification ou de régression supervisée dessus.

**Random Forest** et **Gradient Boosting** (XGBoost, LightGBM) sont les choix dominants en pratique parce qu'ils gèrent nativement des features hétérogènes (optique + radar + topographie), sont peu sensibles à la mise à l'échelle des variables, et offrent une mesure d'importance de variable directement interprétable — utile pour justifier une méthode auprès d'un client qui veut comprendre "sur quoi se base le modèle".

### 3.2 Le piège central : l'autocorrélation spatiale et la fuite de données (spatial leakage)

C'est le point le plus sous-estimé par quiconque arrive au machine learning depuis un contexte non-spatial. Une validation croisée classique (k-fold aléatoire) suppose que les observations sont indépendantes. Or des pixels ou parcelles voisins dans l'espace sont **statistiquement corrélés** (loi de Tobler : "tout est lié à tout, mais les choses proches le sont plus que les choses éloignées"). 

Conséquence concrète : si on découpe aléatoirement les pixels en train/test, des pixels du jeu de test se retrouvent géographiquement adjacents à des pixels du jeu d'entraînement — le modèle "triche" en captant une autocorrélation spatiale locale plutôt que d'apprendre un vrai signal généralisable. Le score de validation obtenu est **artificiellement optimiste**, parfois de façon spectaculaire (95% de précision en interne, 70% sur une nouvelle région).

**La bonne pratique : la validation croisée spatiale.** Plutôt qu'un découpage aléatoire, on découpe l'espace en blocs géographiques (spatial block cross-validation) et on s'assure qu'aucun bloc de test n'est adjacent à un bloc d'entraînement. C'est une contrainte méthodologique non négociable pour tout modèle destiné à être déployé sur des zones non vues à l'entraînement — précisément le cas d'usage d'un produit commercial de monitoring forestier.

### 3.3 Indice de Moran — quantifier l'autocorrélation avant de modéliser

L'**indice de Moran (Moran's I)** mesure statistiquement le degré d'autocorrélation spatiale d'une variable (proche de +1 : forte autocorrélation positive, proche de 0 : distribution spatialement aléatoire, proche de -1 : dispersion régulière). Le calculer sur ses données ou ses résidus de modèle en amont donne une estimation quantitative du risque de fuite si on ignore la contrainte spatiale en validation — et permet de dimensionner la taille des blocs de validation croisée spatiale en fonction de la portée réelle de l'autocorrélation observée.

### 3.4 Deep learning — segmentation sémantique (U-Net) et séries temporelles (LSTM/Transformer)

Pour des tâches de segmentation fine (délinéation précise de contours de coupe, cartographie d'essence à l'échelle du pixel), les architectures de type **U-Net** (réseau convolutif encodeur-décodeur avec connexions résiduelles) dominent en télédétection forestière : elles apprennent directement depuis les images multi-bandes empilées, sans feature engineering manuel préalable.

Pour exploiter des séries temporelles complètes (plutôt qu'une comparaison à deux dates), des architectures récurrentes (**LSTM**) ou plus récemment des **Transformers temporels** (adaptés du NLP au domaine spatio-temporel) apprennent des motifs de trajectoire directement — utile pour distinguer automatiquement une signature de coupe d'une signature de feu ou de chablis sans coder cette distinction à la main comme en semaine 3 de la roadmap initiale.

**Coût réel à anticiper** : ces approches nécessitent des jeux d'annotation nettement plus volumineux (des milliers de polygones labellisés, pas quelques dizaines), une infrastructure GPU pour l'entraînement, et une explicabilité plus faible qu'un Random Forest — un compromis à évaluer selon l'exigence de traçabilité du produit visé (voir section 5 sur le cadre réglementaire, où la traçabilité méthodologique devient une contrainte légale, pas seulement technique).

### 3.5 Construire un jeu d'entraînement fiable — le vrai goulot d'étranglement

En pratique, la qualité d'un modèle dépend davantage de la qualité du jeu d'annotation que du choix d'algorithme. Sources de vérité terrain mobilisables :

- Bases de données de référence existantes : **BD Forêt** (IGN, France — cartographie de la couverture forestière par formation végétale), **Hansen Global Forest Change** (perte de couvert arboré annuelle mondiale, produite par l'Université du Maryland, largement utilisée comme référence académique malgré une résolution et une méthodologie propres qu'il faut documenter)
- Photo-interprétation manuelle sur imagerie très haute résolution ponctuelle (gratuite via certains programmes, ou échantillonnée à coût maîtrisé)
- Remontées terrain structurées (relevés GPS géoréférencés par des opérateurs)

Un biais fréquent : constituer un jeu d'annotation en piochant préférentiellement les cas "faciles" (fortes perturbations bien visibles), ce qui produit un modèle très bon sur les cas évidents et médiocre sur les cas ambigus — précisément ceux où un modèle apporte le plus de valeur par rapport à un simple seuil sur indice.

---

## 4. De l'indice au tonnage — biomasse, volume, carbone

Un indice ou une hauteur LiDAR n'est pas en soi un volume de bois ou une masse de carbone. Le pont entre les deux passe par des relations empiriques calibrées, avec leurs propres sources d'incertitude.

### 4.1 Équations allométriques

Une **équation allométrique** relie une variable facilement mesurable (diamètre à hauteur de poitrine, hauteur totale) à une variable difficile à mesurer directement (volume de bois, biomasse aérienne totale), sous la forme générale `Biomasse = a × Diamètre^b × Hauteur^c`, avec des coefficients (a, b, c) calibrés empiriquement par essence et parfois par région biogéographique (une équation calibrée sur du pin des Landes ne s'applique pas telle quelle à un chêne pédonculé, encore moins à une forêt tropicale humide).

Quand on dispose d'une hauteur LiDAR par arbre segmenté (section 1.2) mais pas du diamètre, une relation hauteur-diamètre intermédiaire (elle aussi calibrée par essence) est nécessaire avant d'appliquer l'équation de biomasse — chaque étape ajoute une incertitude qui se propage et se cumule.

### 4.2 Biomasse aérienne, biomasse racinaire, et stock de carbone

La biomasse aérienne (AGB — Above Ground Biomass) est ce que mesurent directement les approches précédentes. Le **stock de carbone total** d'un arbre inclut aussi la biomasse racinaire (souvent estimée via un ratio racine/aérien standard par type de peuplement, faute de mesure directe possible par télédétection), et la conversion biomasse → carbone utilise classiquement un facteur d'environ 0.47 (47% du poids sec d'un arbre est du carbone), avec des variations selon les essences documentées par le GIEC (IPCC).

### 4.3 Missions satellite dédiées à la biomasse

Au-delà des indices optiques classiques, deux missions récentes ciblent directement l'estimation de biomasse à large échelle :

- **BIOMASS (ESA)**, radar en bande P (grande longueur d'onde, plus pénétrante dans la canopée que la bande C de Sentinel-1), conçu spécifiquement pour estimer la biomasse forestière tropicale à l'échelle globale
- **GEDI** (déjà mentionné en 1.3) fournit, en plus de la hauteur, des métriques de structure verticale directement corrélées à la biomasse, utilisées comme données d'étalonnage pour des modèles régionaux

Pour un produit à l'échelle d'exploitations forestières européennes, ces missions servent surtout de référence de calibration/validation plutôt que de source primaire — leur résolution ou leur couverture ne remplace pas un LiDAR aéroporté local, mais permet de vérifier la cohérence d'un modèle régional face à un référentiel indépendant.

---

## 5. Cadre réglementaire — la contrainte qui change la donne commerciale

C'est le point le plus absent de toute discussion purement technique, et pourtant décisif pour un produit commercial en 2026.

### 5.1 EUDR (EU Deforestation Regulation)

Le règlement européen sur la déforestation impose, pour un ensemble de matières premières (bois compris), une **preuve de non-déforestation géolocalisée** : chaque lot doit être associé à des coordonnées de parcelle de production, avec une vérification que cette parcelle n'a pas fait l'objet de déforestation après une date de référence (31 décembre 2020). C'est un cas d'usage direct et immédiat pour toute la chaîne technique développée dans ce cours : détection de changement fiable, horodatée, documentée, à l'échelle de la parcelle individuelle.

**Implication technique concrète** : un produit visant ce marché doit pouvoir produire, pour chaque parcelle et chaque date, non seulement une classification binaire (déforesté / non déforesté) mais une **trace méthodologique auditable** — quelles données ont été utilisées, quel niveau de confiance, quelles limites connues. C'est directement la logique de la semaine 4 de la roadmap initiale (documenter les limites plutôt que les cacher), mais élevée au rang d'exigence légale plutôt que de bonne pratique optionnelle.

### 5.2 MRV — Measurement, Reporting, Verification

Le triptyque MRV est le cadre méthodologique standard pour tout projet carbone forestier (crédits carbone volontaires ou obligatoires) : **mesurer** un stock ou un flux de carbone avec une méthode documentée, **rapporter** ce chiffre selon un format standardisé, et permettre à un tiers de **vérifier** indépendamment le résultat. Les standards de certification (Verra/VCS, Gold Standard) exigent des méthodologies MRV précises, avec des niveaux de rigueur croissants (Tier 1 : facteurs par défaut génériques, Tier 3 : mesures directes spécifiques au site) empruntés au cadre du GIEC.

Pour un produit de monitoring forestier, s'aligner explicitement sur un niveau Tier reconnu — plutôt que d'inventer sa propre méthodologie — conditionne directement la crédibilité commerciale auprès d'acheteurs de crédits carbone ou d'auditeurs.

### 5.3 Inventaire Forestier National et données de référence françaises

En France, l'**IGN** publie un Inventaire Forestier National (placettes d'échantillonnage au sol, mesures dendrométriques standardisées) qui sert de référence officielle pour le calcul de volume et de biomasse à l'échelle nationale. Toute méthode de télédétection destinée au marché français gagne en crédibilité si elle est validée/calibrée contre ces données de référence plutôt que contre des équations allométriques génériques importées d'autres contextes.

---

## 6. Architecture de production — du notebook au produit qui tient à l'échelle

La roadmap initiale s'arrête à "passage à l'échelle : ce qui change quand on passe d'une parcelle test à des centaines/milliers de parcelles". Voici ce que ça implique concrètement en architecture technique.

### 6.1 Cloud Optimized GeoTIFF (COG) — le format qui rend le cloud utilisable

Un GeoTIFF classique doit être téléchargé intégralement avant d'en lire une portion. Un **COG** (Cloud Optimized GeoTIFF) réorganise en interne les données en tuiles indexées avec des overviews (pyramides de résolution), permettant une lecture par **HTTP range request** : on ne télécharge que les octets correspondant à la zone et à la résolution effectivement nécessaires. C'est ce qui rend viable un traitement à l'échelle sans rapatrier des téraoctets d'imagerie Sentinel-2 en local — les catalogues STAC modernes (dont le Copernicus Data Space) exposent leurs actifs directement en COG.

### 6.2 Data cubes et catalogues STAC à l'échelle

Au-delà de l'interrogation ponctuelle vue précédemment, des outils comme **odc-stac** ou **stackstac** permettent de charger directement le résultat d'une requête STAC comme un cube xarray paresseux (lazy), sans télécharger physiquement chaque scène — le calcul n'est déclenché qu'au moment effectif où le résultat est nécessaire (évaluation différée), une mécanique portée par **Dask** en arrière-plan.

### 6.3 Dask — paralléliser sans réécrire la logique métier

**Dask** étend les APIs pandas/xarray/numpy à des tableaux et dataframes qui dépassent la mémoire disponible, en les découpant automatiquement en blocs traités en parallèle (multi-cœur local, ou distribué sur un cluster). L'intérêt majeur : le code d'analyse écrit avec xarray/rioxarray reste quasiment identique, Dask gère la parallélisation et le hors-mémoire en arrière-plan. C'est ce qui permet de passer d'un notebook traitant une parcelle test à un pipeline traitant plusieurs milliers de parcelles sans réécrire la logique de calcul, seulement l'orchestration.

### 6.4 Diffusion du résultat — de l'analyse à l'API consommable

Un résultat d'analyse géospatiale destiné à un client final ne se diffuse pas comme un fichier brut :

- **Tuiles vectorielles (Vector Tiles, format MVT)** pour afficher efficacement des milliers de polygones de parcelles dans une carte web interactive, sans charger la géométrie complète à chaque zoom
- **WMTS/XYZ** pour diffuser des rasters (cartes de sévérité, cartes de hauteur) sous forme de tuiles image pré-calculées, consommables par n'importe quel client cartographique standard
- **API REST/GraphQL** exposant les résultats structurés (diagnostics par parcelle, historique de trajectoire) pour une intégration dans le système d'information du client plutôt qu'une simple consultation visuelle

Ce dernier point rejoint directement la section 4 de la roadmap initiale sur la restitution à un public non-technique : l'architecture de diffusion fait partie intégrante de la crédibilité produit, pas seulement la qualité de l'analyse en amont.

---

## 7. Cartographie des essences et suivi phytosanitaire — au-delà de la détection de perturbation

Toute la roadmap initiale traite la forêt comme relativement homogène (une essence, un statut sain/perturbé). Un produit mature va plus loin sur deux axes.

### 7.1 Les bandes red-edge de Sentinel-2 — un signal jamais mobilisé jusqu'ici

Sentinel-2 possède, en plus des bandes visible/PIR/SWIR classiques, trois bandes dites **red-edge** (B5, B6, B7, autour de 705-783 nm) qui capturent la zone de transition abrupte entre absorption chlorophyllienne et diffusion foliaire. Cette zone est particulièrement sensible aux variations fines de teneur en chlorophylle et de stress précoce, plus discriminante que le NDVI classique pour distinguer des essences proches ou détecter un stress avant qu'il ne devienne visible sur les bandes plus larges déjà connues (indices dérivés : NDRE — Normalized Difference Red Edge, ou CRE — Chlorophyll Red-Edge index).

### 7.2 Classification d'essences par signature temporelle

Deux essences peuvent avoir un NDVI très proche à une date donnée, mais des **trajectoires phénologiques saisonnières distinctes** (date de débourrement au printemps, vitesse de sénescence à l'automne, amplitude de variation saisonnière). En exploitant une série temporelle complète sur une année plutôt qu'une image ponctuelle, un classifieur (Random Forest sur features temporelles, ou approche deep learning temporelle vue en section 3.4) peut discriminer des essences bien plus finement qu'avec une seule date — un axe produit à forte valeur ajoutée pour des inventaires forestiers détaillés.

### 7.3 Détection précoce de dépérissement (exemple : scolytes)

Les attaques de scolytes (bark beetles) sur épicéas suivent une signature caractéristique : un stress hydrique et une perte de vigueur détectables via le red-edge et le NDMI **avant** le roussissement visible en RGB (le "green attack" — arbre encore vert en apparence mais déjà colonisé). C'est un cas d'usage direct de détection précoce à forte valeur commerciale pour la gestion forestière (identifier et exploiter les arbres attaqués avant propagation, plutôt que constater les dégâts a posteriori) — et un prolongement naturel de la logique vue en semaine 2 sur les limites du visible face à l'infrarouge.

---

## Comment prioriser à partir d'ici

Pour un produit commercial, l'ordre de priorité dépend du marché ciblé, mais une progression raisonnable :

1. **Radar Sentinel-1** en complément de l'optique existant — gain de fiabilité et de fréquence immédiat, effort d'apprentissage modéré, aucune dépendance à des données payantes
2. **Validation croisée spatiale** — même sans machine learning avancé, cette rigueur méthodologique doit être acquise avant toute promesse de taux de fiabilité chiffré à un client
3. **Cadre réglementaire (EUDR/MRV)** — comprendre les exigences avant de construire, pas après ; ça oriente directement quelles traces méthodologiques le pipeline doit produire
4. **LiDAR** (Lidar HD IGN si le marché est français) — apporte une dimension structurelle qu'aucun optique ne remplace, différenciant fort face à des concurrents purement spectraux
5. **Machine learning et architecture à l'échelle** — une fois les fondamentaux physiques et réglementaires solides, pas avant

Chaque section de ce cours peut, comme pour la roadmap initiale, être transformée en session de questions-réponses guidées avec un LLM pour approfondir un point précis en codant.
