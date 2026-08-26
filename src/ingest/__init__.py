"""
Package ingest : téléchargement local des bandes Sentinel-2 L2A.

Télécharge toutes les bandes demandées pour chaque scène exploitable,
découpées sur l'AOI, et les sauvegarde en GeoTIFF local.
Un manifest.json garde la trace de ce qui a été téléchargé.

Usage CLI:
    python -m ingest --geojson zone.geojson --zone chambord \
        --start 2017-01-01 --end 2023-12-31

Usage Python:
    from ingest import ingest
    manifest = ingest(
        geojson_path="zone.geojson",
        zone_name="chambord",
        start_date="2017-01-01",
        end_date="2023-12-31",
    )
"""

from .downloader import ingest, DEFAULT_BANDS
from .manifest import load_manifest, list_scenes, get_band_path, get_scene_dir

__all__ = [
    "ingest",
    "DEFAULT_BANDS",
    "load_manifest",
    "list_scenes",
    "get_band_path",
    "get_scene_dir",
]