# Fiche référence — Objets, méthodes et types (stack géospatiale Python)

> Couvre `geopandas`, `shapely`, `pystac_client`/`pystac`, `rasterio`, `requests`. Pour chaque objet : ce qu'il représente, son type réel, et les pièges d'API à connaître.

---

## geopandas

### `gpd.read_file(path)` → `GeoDataFrame`
Sous-classe de `pandas.DataFrame`. Une colonne spéciale `geometry` contient des objets **shapely**, pas des strings ni du GeoJSON brut. Toutes les méthodes pandas classiques restent disponibles (`.head()`, `.shape`, `.loc`, etc.).

### `gdf.geometry` → `GeoSeries`
Sous-classe de `pandas.Series`, spécialisée pour contenir des géométries shapely. Expose des méthodes vectorisées (`.area`, `.to_crs()`, `.intersects()`, `.buffer()`...) qui s'appliquent ligne par ligne.

### `gdf.geometry.iloc[0]` → objet shapely (`Polygon`, `MultiPolygon`, `Point`...)
Descend d'un niveau : on quitte le monde geopandas (tabulaire) pour un objet shapely individuel. C'est sur cet objet qu'on utilise `.area`, `.interiors`, `.geoms`, `.centroid`, etc. — **pas** sur le GeoDataFrame ou la GeoSeries directement (même si geopandas propose des raccourcis vectorisés équivalents).

### `gdf.crs` → `pyproj.CRS`
Objet représentant le système de coordonnées. `gdf.to_crs(epsg=2154)` renvoie un **nouveau** GeoDataFrame reprojeté (ne modifie pas en place).

### `gdf.total_bounds` → `numpy.ndarray` de 4 floats
`[xmin, ymin, xmax, ymax]` — l'enveloppe globale de **toutes** les géométries.
⚠️ Piège : `gdf.bounds` (sans `total_`) renvoie une `pandas.DataFrame` avec une ligne de bounds **par géométrie**, pas la même chose.

### `gdf.geometry.is_valid` → `GeoSeries` de booléens
Un booléen par géométrie. `.iloc[0]` pour en extraire un seul si le GeoDataFrame n'a qu'une ligne.

### `GeoDataFrame(geometry=[...], crs="EPSG:xxxx")`
Constructeur pour créer un GeoDataFrame à partir d'une liste d'objets shapely. Le paramètre `crs` doit être précisé explicitement — sinon le GeoDataFrame n'a pas de CRS défini, ce qui bloque les reprojections ultérieures.

---

## shapely

### `Polygon` / `MultiPolygon`
Objets géométriques immuables. Un `MultiPolygon` regroupe plusieurs `Polygon` disjoints sous une seule géométrie logique.

### `multipoly.geoms` → séquence itérable (`GeometrySequence`)
Pas une liste Python native, mais itérable et indexable : `for poly in geom.geoms`, ou `geom.geoms[i]`. Chaque élément est un `Polygon` individuel.

### `polygon.exterior` → `LinearRing`
Le contour extérieur du polygone. Un `LinearRing` n'est **pas** un `Polygon` — pas d'aire directement significative dans ce contexte de manipulation, on le repasse dans `Polygon(ring)` si besoin d'un calcul d'aire ou d'opérations d'ensemble.

### `polygon.interiors` → séquence de `LinearRing`
Un `LinearRing` par trou interne. Pour recalculer une surface de trou : `Polygon(ring).area`.

### `polygon.area` → `float`
Aire dans les unités du CRS courant. **Sens physique uniquement si le CRS est projeté** (mètres) — en CRS géographique (degrés), le nombre n'est pas interprétable comme une surface réelle.

### `polygon.centroid` → `Point`
Centre géométrique (pas forcément à l'intérieur du polygone pour des formes très concaves).

### `polygon.is_valid` → `bool`
Vérifie l'absence d'auto-intersections, d'anneaux mal formés, etc.

### `polygon.buffer(0)` → `Polygon`/`MultiPolygon`
Astuce classique pour réparer une géométrie invalide (recalcule les anneaux proprement). Effet de bord : peut légèrement modifier la géométrie (à utiliser en dernier recours, pas en réflexe systématique).

### `box(xmin, ymin, xmax, ymax)` → `Polygon`
Fonction utilitaire (`from shapely.geometry import box`) pour construire un rectangle à partir de 4 coordonnées — utile pour matérialiser une bounding box en objet géométrique manipulable.

### `shape(geojson_dict)` → objet shapely
Fonction (`from shapely.geometry import shape`) qui convertit un dict GeoJSON brut (comme `item.geometry` d'un item STAC) en objet shapely utilisable (`Polygon`, etc.). Complémentaire de `mapping()` qui fait l'inverse (shapely → dict GeoJSON).

### `geom1.intersection(geom2)` → objet shapely (géométrie résultante)
Renvoie la géométrie d'intersection (peut être vide : `Polygon` vide si aucun recouvrement). Ne pas confondre avec `geom1.intersects(geom2)` → `bool`, qui teste juste si ça se recoupe sans renvoyer la géométrie.

---

## pystac_client / pystac

### `Client.open(url)` → `pystac_client.Client`
Point d'entrée vers un catalogue STAC. Ne déclenche qu'un appel léger de vérification, pas le chargement de toutes les données.

### `catalog.search(...)` → `pystac_client.ItemSearch`
**Paresseux (lazy)** : ne fait pas encore de requête HTTP réelle. Les paramètres (`collections`, `bbox`, `datetime`) sont juste stockés.

### `search.items()` → générateur de `pystac.Item`
C'est l'itération sur ce générateur (ou `list(search.items())`) qui déclenche réellement les appels HTTP et gère la pagination côté client automatiquement.

### `pystac.Item`
Un objet représentant une scène/produit satellite. Attributs clés :
- `item.id` → `str` (identifiant unique de la scène)
- `item.datetime` → `datetime.datetime`
- `item.geometry` → `dict` (GeoJSON brut, à convertir avec `shape()` si besoin d'un objet shapely)
- `item.bbox` → `list` de 4 floats
- `item.properties` → `dict` (toutes les métadonnées, ex. `properties["eo:cloud_cover"]`)
- `item.assets` → `dict[str, pystac.Asset]`

### `pystac.Asset`
Représente un fichier associé à l'item (une bande spectrale, une miniature, etc.). Attribut clé : `asset.href` → `str` (URL ou URI, ex. `s3://...` ou `https://...`). Ce n'est **pas** juste une string — l'objet porte aussi le type MIME et d'autres métadonnées.

### Piège de nommage de collection
Les identifiants de collection (`"sentinel-2-l2a"`, etc.) sont spécifiques à chaque fournisseur STAC — jamais à deviner. En cas d'erreur `CollectionInQuerryDoesNotExist`, l'API renvoie généralement l'endpoint où lister les collections valides (`GET /collections`).

---

## rasterio

### `rasterio.open(path_or_url)` → `DatasetReader`
S'utilise en context manager : `with rasterio.open(url) as src:`. Fonctionne aussi bien sur un chemin local que sur une URL/URI distante (`s3://`, `https://`) si GDAL est configuré pour ce protocole.

### Sur un `DatasetReader` (`src`)
- `src.crs` → `rasterio.crs.CRS` (objet distinct du CRS pyproj/geopandas — conversion parfois nécessaire selon le contexte d'usage croisé)
- `src.width`, `src.height` → `int` (dimensions en **pixels**, pas en unités métriques)
- `src.res` → `tuple(float, float)` (taille de pixel en unités du CRS, ex. `(20.0, 20.0)` pour une bande 20m)
- `src.bounds` → `BoundingBox` (namedtuple-like avec `.left`, `.bottom`, `.right`, `.top`)
- `src.read(band_index)` → `numpy.ndarray` (valeurs de pixels de la bande demandée)

### Variables d'environnement GDAL/AWS pertinentes pour l'accès S3
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT`, `AWS_VIRTUAL_HOSTING`, `AWS_HTTPS` — à définir **avant** l'import de `rasterio` pour être sûr qu'elles soient prises en compte par GDAL sous-jacent.

---

## requests

### `requests.get(url)` → `Response`
Attributs/méthodes clés :
- `.status_code` → `int`
- `.json()` → `dict` ou `list` (désérialisation automatique du corps JSON — lève une erreur si le contenu n'est pas du JSON valide)
- `.text` → `str` (corps brut, non parsé)
- `.content` → `bytes` (corps brut binaire)

### Pattern de pagination générique
Beaucoup d'APIs REST (dont STAC) renvoient un champ `links` contenant un objet avec `"rel": "next"` et un `"href"`. Pattern robuste :
```python
while url:
    data = requests.get(url).json()
    # traiter data...
    url = next((l["href"] for l in data.get("links", []) if l["rel"] == "next"), None)
```
Préférable à un `limit` fixe qui peut être silencieusement plafonné par l'API.

---

## Récapitulatif express — hiérarchie des types

```
GeoDataFrame (pandas.DataFrame)
 └─ .geometry → GeoSeries (pandas.Series)
     └─ .iloc[i] → objet shapely (Polygon / MultiPolygon / Point...)
         ├─ .geoms (si Multi*) → GeometrySequence → Polygon individuels
         ├─ .exterior → LinearRing
         ├─ .interiors → séquence de LinearRing
         └─ .centroid → Point

pystac_client.Client
 └─ .search(...) → ItemSearch (lazy)
     └─ .items() → générateur de pystac.Item
         ├─ .properties → dict
         ├─ .geometry → dict (GeoJSON, à convertir avec shapely.geometry.shape)
         └─ .assets → dict[str, pystac.Asset]
             └─ .href → str (URL/URI du fichier)

rasterio.open(...) → DatasetReader (context manager)
 ├─ .crs → rasterio.crs.CRS
 ├─ .width / .height → int
 ├─ .res → tuple(float, float)
 └─ .read(i) → numpy.ndarray
```