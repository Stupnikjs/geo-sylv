# raster.py
import time
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.mask import mask

from errors import is_retryable_error


def _read_clipped_one_band(url, aoi_geom, aoi_crs="EPSG:4326"):
    """Interne : lit et découpe une seule bande, sans retry."""
    with rasterio.Env(GDAL_HTTP_MULTIPLEX="NO", VSI_CACHE="FALSE"):
        with rasterio.open(url) as src:
            if src.crs is None:
                # Signal fort d'une lecture corrompue/incomplète (ex: document
                # d'erreur S3 mal interprété comme raster) plutôt qu'un vrai
                # problème de géoréférencement JP2 — à retenter, pas à accepter.
                raise ValueError(f"Raster sans CRS (lecture probablement corrompue) pour {url}")

            aoi_proj = gpd.GeoSeries([aoi_geom], crs=aoi_crs).to_crs(src.crs)
            geom = [aoi_proj.iloc[0].__geo_interface__]
            out_image, out_transform = mask(src, geom, crop=True)

            if out_image.shape[0] != 1:
                raise ValueError(f"Attendu 1 bande, obtenu {out_image.shape[0]} pour {url}")
            if out_image.size == 0:
                raise ValueError(f"AOI hors de l'étendue du raster pour {url}")

    return out_image[0].astype("float32")


def _read_one_band_safe(url, aoi_geom, aoi_crs="EPSG:4326", max_retries=3):
    for attempt in range(max_retries):
        try:
            return _read_clipped_one_band(url, aoi_geom, aoi_crs)
        except Exception as e:
            if is_retryable_error(e):
                delay = 5 * (2**attempt)
                print(f"Erreur transitoire ({type(e).__name__}), attente {delay}s (tentative {attempt + 1}/{max_retries})...")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"Échec de lecture après {max_retries} tentatives : {url}")


def read_clipped_bands(urls, aoi_geom, aoi_crs="EPSG:4326", max_retries=3):
    """Point d'entrée unique : 1 ou N URLs → tableau (n_bands, height, width).
    Pour une seule bande, faire stacked[0] côté appelant.
    """
    bands = [_read_one_band_safe(u, aoi_geom, aoi_crs, max_retries) for u in urls]
    return np.stack(bands)