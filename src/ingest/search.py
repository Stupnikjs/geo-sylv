"""Recherche de scènes Sentinel-2 via le catalogue STAC Copernicus."""

from __future__ import annotations

from typing import Any

import geopandas as gpd
import pystac_client

from .config import COLLECTION, STAC_URL
from .errors import search_with_retry


def load_aoi(geojson_path: str) -> tuple[Any, list[float], float]:
    """
    Charge un GeoJSON et retourne :
    - aoi_geom : géométrie fusionnée (union) en EPSG:4326
    - bbox : [min_lon, min_lat, max_lon, max_lat]
    - area_ha : surface en hectares ( reprojetée en EPSG:2154)
    """
    zone = gpd.read_file(geojson_path).to_crs(epsg=4326)
    aoi_geom = zone.geometry.union_all()
    bbox = list(aoi_geom.bounds)
    area_ha = (
        gpd.GeoSeries([aoi_geom], crs=4326).to_crs(epsg=2154).area.iloc[0] / 10_000.0
    )
    return aoi_geom, bbox, area_ha


def search_scenes(
    bbox: list[float],
    start_date: str,
    end_date: str,
    max_cloud_cover: int = 60,
    max_retries: int = 5,
    timeout: int = 10,
) -> list:
    """
    Recherche les scènes Sentinel-2 L2A sur une bbox et une période.

    Pré-filtre sur eo:cloud_cover (métadonnée, zéro téléchargement).
    Retourne une liste d'items pystac triés par date.
    """
    catalog = pystac_client.Client.open(STAC_URL, timeout=timeout)

    items = search_with_retry(
        catalog,
        max_retries=max_retries,
        collections=[COLLECTION],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
    )

    # Pré-filtre cloud_cover
    items = [
        item
        for item in items
        if item.properties.get("eo:cloud_cover", 0) <= max_cloud_cover
    ]

    items = sorted(items, key=lambda i: i.datetime)
    return items