#!/usr/bin/env python3
"""
Télécharge le périmètre final (Grading Product) de l'incendie de Landiras
(Copernicus EMS, activation EMSR592, juillet 2022) et le convertit en GeoJSON.

Usage:
    python download_landiras.py
    python download_landiras.py --output-dir ./data/reference
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

GRADING_URL = (
    "https://cems-mapping-website.s3.eu-west-1.amazonaws.com/static/"
    "activations/EMSR592/EMSR592_AOI01_GRA_PRODUCT_r1_RTP01_v1_vector.zip"
)


def download_zip(url: str, dest: Path) -> Path:
    """Télécharge le zip du vector package Copernicus EMS."""
    print(f"Téléchargement : {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(url, dest)
    print(f"  -> {dest} ({dest.stat().st_size / 1024:.0f} Ko)")
    return dest


def extract_zip(zip_path: Path, extract_dir: Path) -> Path:
    """Extrait le zip et retourne le dossier d'extraction."""
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    print(f"Extrait dans : {extract_dir}")
    return extract_dir


def find_shapefile(extract_dir: Path) -> Path:
    """Trouve le .shp correspondant au périmètre du feu (polygones brûlés)."""
    shp_files = list(extract_dir.rglob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(f"Aucun .shp trouvé dans {extract_dir}")

    # Le vector package contient plusieurs couches (légende, grille, source...).
    # On cherche en priorité un nom explicite de périmètre brûlé.
    priority_keywords = ["area", "perimeter", "burnt", "delin", "poly"]
    for shp in shp_files:
        name_lower = shp.stem.lower()
        if any(kw in name_lower for kw in priority_keywords):
            return shp

    if len(shp_files) == 1:
        return shp_files[0]

    print(f"  Plusieurs .shp trouvés, aucun nom évident de périmètre : {[s.name for s in shp_files]}")
    print(f"  Utilisation du premier : {shp_files[0].name} — vérifie que c'est le bon.")
    return shp_files[0]


def convert_to_geojson(shp_path: Path, output_path: Path) -> Path:
    """Convertit le shapefile en GeoJSON via geopandas."""
    try:
        import geopandas as gpd
    except ImportError:
        print("ERREUR: geopandas n'est pas installé (pip install geopandas)")
        sys.exit(1)

    gdf = gpd.read_file(shp_path)
    print(f"  {len(gdf)} géométrie(s) lue(s), CRS: {gdf.crs}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver="GeoJSON")
    print(f"GeoJSON sauvegardé : {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Télécharge et convertit le périmètre de l'incendie de Landiras (EMSR592) en GeoJSON."
    )
    parser.add_argument(
        "--output-dir",
        default="./data/reference/landiras_2022",
        help="Dossier de sortie (défaut: ./data/reference/landiras_2022)",
    )
    parser.add_argument(
        "--keep-raw",
        action="store_true",
        help="Conserve le zip et le shapefile brut en plus du GeoJSON.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    zip_path = output_dir / "EMSR592_AOI01_GRA_PRODUCT_vector.zip"
    extract_dir = output_dir / "raw"
    geojson_path = output_dir / "landiras_perimetre_2022.geojson"

    download_zip(GRADING_URL, zip_path)
    extract_zip(zip_path, extract_dir)
    shp_path = find_shapefile(extract_dir)
    convert_to_geojson(shp_path, geojson_path)

    if not args.keep_raw:
        zip_path.unlink(missing_ok=True)
        shutil.rmtree(extract_dir, ignore_errors=True)
        print("Fichiers intermédiaires supprimés (zip, shapefile brut).")

    print(f"\nTerminé. GeoJSON prêt : {geojson_path}")


if __name__ == "__main__":
    main()
