"""Lecture, découpe et sauvegarde des bandes raster Sentinel-2."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask

from .errors import is_retryable_error


def _read_clipped_one_band(
    url: str,
    aoi_geom: Any,
    aoi_crs: str = "EPSG:4326",
) -> tuple[np.ndarray, dict]:
    """
    Lit une bande depuis une URL, la découpe sur l'AOI.

    Retourne (array_2d, profile) où profile contient CRS, transform, dtype.
    Lève une ValueError si la lecture semble corrompue (pas de CRS, bande vide).
    """
    with rasterio.Env(GDAL_HTTP_MULTIPLEX="NO", VSI_CACHE="FALSE"):
        with rasterio.open(url) as src:
            if src.crs is None:
                raise ValueError(
                    f"Raster sans CRS (lecture probablement corrompue) : {url}"
                )

            aoi_proj = gpd.GeoSeries([aoi_geom], crs=aoi_crs).to_crs(src.crs)
            geom = [aoi_proj.iloc[0].__geo_interface__]
            out_image, out_transform = mask(src, geom, crop=True)

            if out_image.shape[0] != 1:
                raise ValueError(
                    f"Attendu 1 bande, obtenu {out_image.shape[0]} pour {url}"
                )
            if out_image.size == 0:
                raise ValueError(f"AOI hors de l'étendue du raster pour {url}")

            # Profile pour sauvegarde : on garde le dtype d'origine.
            profile = src.profile.copy()
            profile.update(
                {
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                    "count": 1,
                    "compress": "lzw",
                    "tiled": True,
                }
            )

    return out_image[0], profile


def read_clipped_band(
    url: str,
    aoi_geom: Any,
    aoi_crs: str = "EPSG:4326",
    max_retries: int = 3,
) -> tuple[np.ndarray, dict]:
    """Lit et découpe une bande avec retry sur erreurs transitoires."""
    for attempt in range(max_retries):
        try:
            return _read_clipped_one_band(url, aoi_geom, aoi_crs)
        except Exception as e:
            if is_retryable_error(e):
                delay = 5 * (2**attempt)
                print(
                    f"  Erreur transitoire ({type(e).__name__}), "
                    f"attente {delay}s (tentative {attempt + 1}/{max_retries})..."
                )
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"Échec de lecture après {max_retries} tentatives : {url}")


def save_band(array: np.ndarray, profile: dict, output_path: Path) -> None:
    """Sauvegarde un tableau 2D en GeoTIFF (LZW compressé)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(array, 1)


def read_clipped_band_safe_and_save(
    url: str,
    aoi_geom: Any,
    aoi_crs: str,
    output_path: Path,
    max_retries: int = 3,
) -> bool:
    """
    Lit une bande depuis une URL, la découpe sur l'AOI et la sauvegarde localement.

    Retourne True si le fichier a été écrit, False s'il existait déjà (skip).
    """
    output_path = Path(output_path)
    if output_path.exists():
        return False

    array, profile = read_clipped_band(url, aoi_geom, aoi_crs, max_retries)
    save_band(array, profile, output_path)
    return True


# --- Classes SCL pour le calcul de fraction valide ---
CLOUD_CLASSES = (0, 1, 3, 8, 9, 10, 11)


def compute_valid_fraction(
    scl_array: np.ndarray,
    cloud_classes: tuple = CLOUD_CLASSES,
) -> tuple[float, np.ndarray]:
    """
    Calcule la fraction de pixels valides à partir de la bande SCL.

    Retourne (valid_fraction, invalid_mask).
    """
    invalid = np.isin(scl_array, cloud_classes)
    valid_fraction = 1.0 - (invalid.sum() / scl_array.size)
    return valid_fraction, invalid