"""
Récupère le périmètre de l'incendie de Landiras (juillet 2022) depuis
Copernicus EMS (activation EMSR592, AOI01) et produit
data/projects/project_001/geometry.geojson

Usage :
    python fetch_project_001_geometry.py

Dépendances (déjà dans requirements.txt du sprint + requests) :
    pip install requests geopandas shapely
"""

import io
import zipfile
from pathlib import Path

import geopandas as gpd
import requests

# Produit "Grading" = version la plus consolidée du périmètre brûlé
# (livré le 21/07/2022, après stabilisation de l'incendie)
EMSR592_AOI01_GRADING_URL = (
    "https://cems-mapping-website.s3.eu-west-1.amazonaws.com/static/"
    "activations/EMSR592/EMSR592_AOI01_GRA_PRODUCT_r1_RTP01_v1_vector.zip"
)

# Chemin ancré sur l'emplacement du script lui-même (pas sur le dossier
# depuis lequel tu le lances). Le script est supposé être à la racine
# du projet (geo-sylv/), avec data/ juste à côté.
SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "data" / "projects" / "project_001"
OUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"[debug] Dossier de sortie utilisé : {OUT_DIR.resolve()}")


def download_and_extract(url: str, target_dir: Path) -> Path:
    print(f"Téléchargement : {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(target_dir)
        names = zf.namelist()

    return target_dir, names


def find_burnt_area_shapefile(extract_dir: Path) -> Path:
    """
    Le zip contient plusieurs couches (AOI, hydro, zones bâties, etc.).
    On cherche la couche liée à la zone brûlée / event area.
    Les noms varient selon les activations, donc on liste tout
    et on inspecte manuellement si besoin.
    """
    shapefiles = list(extract_dir.rglob("*.shp"))
    print("\nShapefiles trouvés dans l'archive :")
    for shp in shapefiles:
        print(f"  - {shp.name}")
    return shapefiles


def main():
    raw_dir = OUT_DIR / "_raw_emsr592"
    raw_dir.mkdir(exist_ok=True)

    extract_dir, names = download_and_extract(EMSR592_AOI01_GRADING_URL, raw_dir)
    shapefiles = find_burnt_area_shapefile(extract_dir)

    if not shapefiles:
        print("Aucun shapefile trouvé, vérifie le contenu de l'archive manuellement.")
        return

    # Étape manuelle probable : plusieurs couches (ex: "*_area_of_interest_a.shp",
    # "*_observed_event_a.shp", "*_grading_a.shp"). On veut la couche polygonale
    # qui représente la zone endommagée (souvent "grading" ou "event").
    # On charge chacune pour que tu puisses choisir la bonne.
    for shp in shapefiles:
        gdf = gpd.read_file(shp)
        print(f"\n{shp.name} -> {len(gdf)} entités, colonnes: {list(gdf.columns)}")
        print(gdf.geom_type.unique())

    print(
        "\nInspecte la sortie ci-dessus, identifie la couche polygonale "
        "représentant la zone endommagée/brûlée (souvent 'grading' ou "
        "'damage'), puis relance avec ce nom explicite via "
        "build_geometry(shapefile_name)."
    )


def build_geometry(shapefile_name: str, simplify_tolerance: float = 0.0005):
    """
    Une fois la bonne couche identifiée (via main()), génère le
    geometry.geojson final, simplifié et en WGS84.
    """
    raw_dir = OUT_DIR / "_raw_emsr592"
    print(f"[debug] Recherche de {shapefile_name} dans {raw_dir.resolve()}")

    matches = list(raw_dir.rglob(shapefile_name))
    if not matches:
        print(
            f"[info] {shapefile_name} introuvable dans {raw_dir}. "
            "Téléchargement automatique en cours..."
        )
        raw_dir.mkdir(parents=True, exist_ok=True)
        download_and_extract(EMSR592_AOI01_GRADING_URL, raw_dir)
        matches = list(raw_dir.rglob(shapefile_name))
        if not matches:
            raise FileNotFoundError(
                f"{shapefile_name} toujours introuvable après téléchargement. "
                f"Vérifie le nom exact du fichier dans {raw_dir}."
            )

    shp_path = matches[0]

    gdf = gpd.read_file(shp_path)
    gdf = gdf.to_crs(epsg=4326)

    # Dissout toutes les entités en un seul polygone (périmètre global)
    dissolved = gdf.dissolve()
    dissolved["geometry"] = dissolved.geometry.simplify(
        simplify_tolerance, preserve_topology=True
    )

    out_path = OUT_DIR / "geometry.geojson"
    dissolved[["geometry"]].to_file(out_path, driver="GeoJSON")
    print(f"Écrit : {out_path}")
    print(f"Surface approx (deg^2, non projetée) : {dissolved.geometry.area.sum():.6f}")


if __name__ == "__main__":
    main()