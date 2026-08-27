"""Lecture, découpe et sauvegarde des bandes raster Sentinel-2."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.features import geometry_mask

from .errors import is_retryable_error

CLOUD_CLASSES = (0, 1, 3, 8, 9, 10, 11)


def _read_clipped_one_band(url, aoi_geom, aoi_crs="EPSG:4326"):
    """
    Lit une bande depuis une URL, la découpe sur l'AOI.

    Retourne (array_2d, profile) où profile contient CRS, transform, dtype.
    Lève une ValueError si la lecture semble corrompue (pas de CRS, bande vide).
    """
    with rasterio.Env(GDAL_HTTP_MULTIPLEX="NO", VSI_CACHE="FALSE"):
        with rasterio.open(url) as src:
            if src.crs is None:
                raise ValueError(f"Raster sans CRS (lecture probablement corrompue) : {url}")

            aoi_proj = gpd.GeoSeries([aoi_geom], crs=aoi_crs).to_crs(src.crs)
            geom = [aoi_proj.iloc[0].__geo_interface__]
            out_image, out_transform = mask(src, geom, crop=True, filled=False)

            if out_image.shape[0] != 1:
                raise ValueError(f"Attendu 1 bande, obtenu {out_image.shape[0]} pour {url}")
            if out_image.size == 0:
                raise ValueError(f"AOI hors de l'étendue du raster pour {url}")

            profile = src.profile.copy()
            profile.update({
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "count": 1,
                "compress": "lzw",
                "tiled": True,
                "nodata": 0,
            })

    return out_image[0], profile  # MaskedArray


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


def save_band(array, profile, output_path):
    """Sauvegarde en GeoTIFF. array peut être un MaskedArray : on remplit
    explicitement à 0 (= nodata) uniquement au moment d'écrire sur disque."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    flat = np.ma.filled(array, 0) if np.ma.isMaskedArray(array) else array
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(flat, 1)


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


def load_band_with_aoi_mask(path, aoi_geom, aoi_crs="EPSG:4326"):
    """
    Relit une bande locale et recalcule le masque 'hors polygone AOI' depuis
    le géoréférencement du fichier lui-même (transform/crs/shape).

    Ne dépend d'aucune info baked dans les pixels au moment de l'écriture :
    le résultat est identique que le fichier vienne d'être téléchargé ou soit
    déjà sur disque depuis longtemps. C'est ce qui évite la divergence entre
    la Phase 1 (calcul frais, MaskedArray) et la Phase 2 (relecture disque,
    ndarray plat) qui faussait valid_fraction.
    """
    with rasterio.open(path) as src:
        data = src.read(1)
        aoi_proj = gpd.GeoSeries([aoi_geom], crs=aoi_crs).to_crs(src.crs)
        geom = [aoi_proj.iloc[0].__geo_interface__]
        outside = geometry_mask(
            geom, out_shape=(src.height, src.width), transform=src.transform, invert=False
        )
    return data, outside


def compute_valid_fraction(scl_data, outside_mask, cloud_classes=CLOUD_CLASSES):
    """
    Calcule la fraction de pixels valides à partir de la bande SCL.

    outside_mask : booléen h×w, True hors du polygone AOI (cf. load_band_with_aoi_mask).
    Le dénominateur ne compte que les pixels réellement à l'intérieur du
    polygone — pas toute la bbox englobante.

    Retourne (valid_fraction, invalid_mask).
    """
    cloud = np.isin(scl_data, cloud_classes) & ~outside_mask
    total_in_polygon = int((~outside_mask).sum())
    valid_fraction = 1.0 - (cloud.sum() / total_in_polygon) if total_in_polygon else 0.0
    invalid_mask = cloud | outside_mask
    return float(valid_fraction), invalid_mask


def read_or_download_band(url, aoi_geom, aoi_crs, output_path, max_retries=3):
    """
    Télécharge si absent, puis relit TOUJOURS depuis le disque de la même
    façon (via load_band_with_aoi_mask). Un seul chemin de code pour
    'vient d'être téléchargé' et 'déjà présent' — c'est ce qui élimine
    la source du bug de fraction valide incohérente entre les deux phases.
    """
    output_path = Path(output_path)
    if not output_path.exists():
        array, profile = read_clipped_band(url, aoi_geom, aoi_crs, max_retries)
        save_band(array, profile, output_path)
    return load_band_with_aoi_mask(output_path, aoi_geom, aoi_crs)