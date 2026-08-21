# Fiche méthode — Préparation d'une zone brûlée pour analyse Sentinel-2

> Séquence appliquée sur le feu de Landiras (2022), généralisable à toute zone de perturbation forestière.

## 1. Chargement et inspection de la géométrie

```python
import geopandas as gpd

project = gpd.read_file("data/projects/project_001/geometry.geojson")
print(project.crs)
print(project.shape)
project.head()
```

Vérifier systématiquement : CRS (géographique en degrés vs projeté en mètres), nombre de lignes, type de géométrie.

## 2. Calcul de surface (toujours en CRS projeté)

```python
lambert = project.to_crs(epsg=2154)  # Lambert-93 pour la France
area_ha = lambert.geometry.area / 10_000
print(area_ha)
```

Ne jamais calculer une aire directement en EPSG:4326 (degrés) — résultat non interprétable physiquement.

## 3. Exploration d'un MultiPolygon (fragments)

```python
geom = project.geometry.iloc[0]
print(type(geom))
print(len(geom.geoms))

geom_metric = lambert.geometry.iloc[0]
for i, poly in enumerate(geom_metric.geoms):
    print(i, poly.area / 10_000, "ha")
```

Objectif : repérer si un seul polygone domine largement les autres (cas fréquent) — les petits fragments sont souvent du bruit de classification.

## 4. Isoler le polygone principal

```python
areas = [poly.area for poly in geom_metric.geoms]
main_poly = geom_metric.geoms[areas.index(max(areas))]
```

## 5. Analyser les trous internes (zones non brûlées à l'intérieur du contour)

```python
from shapely.geometry import Polygon

print("Nombre de trous :", len(main_poly.interiors))
holes_area = sum(Polygon(ring).area for ring in main_poly.interiors) / 10_000
print("Surface totale des trous :", holes_area, "ha")

# isoler le trou principal
hole_areas = [Polygon(ring).area for ring in main_poly.interiors]
main_hole = Polygon(main_poly.interiors[hole_areas.index(max(hole_areas))])

# localiser (centroïde en lat/lon)
centroid_wgs84 = gpd.GeoSeries([main_hole.centroid], crs="EPSG:2154").to_crs(epsg=4326)
print(centroid_wgs84.iloc[0].y, centroid_wgs84.iloc[0].x)
```

Ne pas remplir les trous (`Polygon(main_poly.exterior)`) si l'objectif est un masque d'analyse — les trous doivent être conservés pour exclure les zones non brûlées.

## 6. Sauvegarder une géométrie nettoyée (polygone principal + trous, sans les fragments parasites)

```python
import os

clean_gdf = gpd.GeoDataFrame(geometry=[main_poly], crs="EPSG:2154").to_crs(epsg=4326)
os.makedirs("data/projects/project_001", exist_ok=True)
clean_gdf.to_file("data/projects/project_001/geometry_clean.geojson", driver="GeoJSON")
```

## 7. Vérifier la validité topologique

```python
print("Géométrie valide :", clean_gdf.geometry.is_valid.iloc[0])
```

Si `False` : réparer avec `.buffer(0)` avant toute utilisation en aval (clip, intersection...).

## 8. Bounding box et comparaison à la surface réelle

```python
bounds = clean_gdf.total_bounds  # [xmin, ymin, xmax, ymax] en WGS84

from shapely.geometry import box
bbox_gdf = gpd.GeoDataFrame(geometry=[box(*bounds)], crs="EPSG:4326").to_crs(epsg=2154)
bbox_area_ha = bbox_gdf.geometry.area.iloc[0] / 10_000
poly_area_ha = clean_gdf.to_crs(epsg=2154).geometry.area.iloc[0] / 10_000

print("Ratio bbox/polygone :", bbox_area_ha / poly_area_ha)
```

Usage pratique : **bbox** pour interroger un catalogue de données (recherche rapide, robuste) ; **polygone exact** pour le calcul final des statistiques (clip précis, pas de pollution par des zones hors périmètre).

## 9. Interroger un catalogue Sentinel-2 (STAC, Copernicus Data Space)

```python
from pystac_client import Client

catalog = Client.open("https://catalogue.dataspace.copernicus.eu/stac")

search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=list(bounds),
    datetime="2022-07-01/2022-08-31",
)
items = list(search.items())
print("Nombre de scènes trouvées :", len(items))
```

Point d'attention : lister les collections disponibles avant de deviner un nom (`requests.get(".../collections?limit=100")`, en paginant via les liens `next` si besoin). Le niveau **L2A** (corrigé atmosphériquement, avec bande SCL) est le bon choix pour l'analyse d'indices.

## 10. Filtrer par couverture nuageuse

```python
threshold = 20
usable = [item for item in items if item.properties.get("eo:cloud_cover", 100) < threshold]
print(f"Scènes utilisables (<{threshold}%) : {len(usable)} sur {len(items)}")

for item in sorted(usable, key=lambda i: i.datetime):
    print(item.id, "-", item.properties.get("eo:cloud_cover"), "%")
```

## 11. Choisir les dates pré/post-événement

Critères : date pré-événement la plus proche possible mais encore saine ; date post-événement la plus proche possible mais stabilisée (pas en pleine combustion/fumée). Croiser avec le calendrier réel de l'événement (dates de l'incendie) avant de figer le choix.

---

## Points de vigilance génériques (à retenir au-delà de Landiras)
- Toujours vérifier CRS et validité géométrique avant tout calcul.
- Un MultiPolygon peut cacher un unique polygone dominant + du bruit — ne pas traiter les fragments comme équivalents sans vérifier leur taille relative.
- Les trous internes d'un polygone sont une information, pas un défaut à corriger par défaut — les conserver pour un usage en masque.
- La bbox et le polygone exact ont des usages complémentaires, pas interchangeables (recherche vs calcul précis).
- Une zone peut chevaucher plusieurs tuiles satellite (grille MGRS pour Sentinel-2) : le nombre de scènes trouvées n'est pas directement le nombre de dates disponibles.
- Le taux de couverture nuageuse théorique (revisite ~5 jours) est très différent du nombre de dates réellement exploitables — toujours vérifier `eo:cloud_cover` avant de planifier une analyse temporelle.