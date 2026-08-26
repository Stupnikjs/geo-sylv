"""
Orchestration principale : recherche → filtrage SCL → téléchargement des bandes.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np

from .config import setup
from .manifest import (
    add_scene,
    create_manifest,
    get_scene_dir,
    load_manifest,
    save_manifest,
)
from .raster import (
    compute_valid_fraction,
    read_clipped_band,
    read_clipped_band_safe_and_save,
    save_band,
)
from .search import load_aoi, search_scenes


# --- Bandes Sentinel-2 L2A téléchargées par défaut ---
DEFAULT_BANDS = [
    "B02_10m",
    "B03_10m",
    "B04_10m",
    "B08_10m",    # 10m : RVB + NIR
    "B05_20m",
    "B06_20m",
    "B07_20m",
    "B8A_20m",    # 20m : red edge + NIR étroit
    "B11_20m",
    "B12_20m",    # 20m : SWIR
    "SCL_20m",    # 20m : classification de scène
]

# --- Paramètres de filtrage ---
MAX_CLOUD_COVER_SCENE = 60
MIN_VALID_FRACTION = 0.8
MAX_CONCURRENT_REQUESTS = 4


def _download_scl(
    item: Any,
    aoi_geom: Any,
    aoi_crs: str,
    scene_dir: Path,
) -> tuple[float, np.ndarray] | None:
    """Télécharge SCL, calcule la fraction valide. Retourne None si échec."""
    if "SCL_20m" not in item.assets:
        print(f"  SKIP {item.id} : pas de SCL_20m dans les assets")
        return None

    scl_url = item.assets["SCL_20m"].href
    scl_path = scene_dir / "SCL_20m.tif"

    # SCL déjà téléchargé ? On le lit depuis le disque.
    if scl_path.exists():
        import rasterio
        with rasterio.open(scl_path) as src:
            scl = src.read(1)
    else:
        array, profile = read_clipped_band(scl_url, aoi_geom, aoi_crs)
        save_band(array, profile, scl_path)
        scl = array

    valid_fraction, invalid_mask = compute_valid_fraction(scl)
    return valid_fraction, invalid_mask


def _download_scene_bands(
    item: Any,
    aoi_geom: Any,
    aoi_crs: str,
    scene_dir: Path,
    bands: list[str],
    max_retries: int = 3,
) -> dict[str, str]:
    """
    Télécharge toutes les bandes demandées pour une scène.
    Retourne un dict {band_name: relative_path}.
    """
    scene_dir.mkdir(parents=True, exist_ok=True)
    downloaded = {}

    for band_name in bands:
        if band_name not in item.assets:
            print(f"    {band_name} : absent des assets, skip")
            continue

        url = item.assets[band_name].href
        band_path = scene_dir / f"{band_name}.tif"

        try:
            written = read_clipped_band_safe_and_save(
                url, aoi_geom, aoi_crs, band_path, max_retries
            )
            if written:
                print(f"    {band_name} : téléchargé")
            else:
                print(f"    {band_name} : déjà présent")
            downloaded[band_name] = str(band_path.relative_to(scene_dir.parent.parent))
        except Exception as e:
            print(f"    {band_name} : ÉCHEC ({e})")

    return downloaded


def _process_scene(
    item: Any,
    aoi_geom: Any,
    aoi_crs: str,
    zone_dir: Path,
    bands: list[str],
    min_valid_fraction: float,
    max_retries: int,
) -> dict:
    """
    Traite une scène : télécharge SCL → filtre → télécharge les bandes.
    Retourne une entrée de manifeste pour cette scène.
    """
    scene_dir = get_scene_dir(zone_dir, item.id)
    scene_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        "id": item.id,
        "datetime": item.datetime.isoformat() if item.datetime else None,
        "cloud_cover": item.properties.get("eo:cloud_cover", 0),
        "valid_fraction": None,
        "usable": False,
        "scene_dir": str(scene_dir.relative_to(zone_dir)),
        "bands": {},
    }

    # --- Phase 1 : SCL ---
    try:
        result = _download_scl(item, aoi_geom, aoi_crs, scene_dir)
        if result is None:
            entry["usable"] = False
            return entry
        valid_fraction, _ = result
        entry["valid_fraction"] = float(valid_fraction)
    except Exception as e:
        print(f"  SKIP {item.id} (SCL) : {e}")
        entry["usable"] = False
        return entry

    if valid_fraction < min_valid_fraction:
        print(
            f"  SKIP {item.id} : fraction valide {valid_fraction:.2%} "
            f"< seuil {min_valid_fraction:.0%}"
        )
        entry["usable"] = False
        return entry

    entry["usable"] = True
    print(f"  OK {item.id} : fraction valide {valid_fraction:.2%}")

    # --- Phase 2 : toutes les autres bandes ---
    bands_to_download = [b for b in bands if b != "SCL_20m"]
    downloaded = _download_scene_bands(
        item, aoi_geom, aoi_crs, scene_dir, bands_to_download, max_retries
    )

    scl_rel = str((scene_dir / "SCL_20m.tif").relative_to(zone_dir))
    downloaded["SCL_20m"] = scl_rel
    entry["bands"] = downloaded

    return entry


def ingest(
    geojson_path: str | Path,
    zone_name: str,
    start_date: str = "2017-01-01",
    end_date: str = "2023-12-31",
    output_dir: str | Path = "./data",
    bands: list[str] | None = None,
    max_cloud_cover: int = MAX_CLOUD_COVER_SCENE,
    min_valid_fraction: float = MIN_VALID_FRACTION,
    max_workers: int = MAX_CONCURRENT_REQUESTS,
    max_retries: int = 3,
    skip_existing: bool = True,
) -> dict:
    """
    Télécharge toutes les bandes Sentinel-2 L2A pour une AOI et une période.
    """
    if bands is None:
        bands = DEFAULT_BANDS

    # 1. Setup environnement
    setup()

    # 2. Charger l'AOI
    aoi_geom, bbox, area_ha = load_aoi(geojson_path)
    print(f"Zone : {zone_name}")
    print(f"Bbox : {bbox}")
    print(f"Aire : {area_ha:.1f} ha")
    print(f"Période : {start_date} → {end_date}")
    print(f"Bandes : {', '.join(bands)}")

    # 3. Préparer le dossier de zone et le manifeste
    zone_dir = Path(output_dir) / zone_name
    zone_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(zone_dir)
    if manifest is None:
        manifest = create_manifest(
            zone_name=zone_name,
            geojson_path=str(geojson_path),
            start_date=start_date,
            end_date=end_date,
            bands=bands,
            aoi_crs="EPSG:4326",
            aoi_bounds=bbox,
            area_ha=area_ha,
        )
        save_manifest(zone_dir, manifest)
        print(f"Manifeste créé : {zone_dir / 'manifest.json'}")
    else:
        print(f"Manifeste existant chargé ({len(manifest.get('scenes', []))} scènes)")

    # 4. Recherche STAC
    print("\n--- Recherche des scènes ---")
    items = search_scenes(bbox, start_date, end_date, max_cloud_cover)
    print(f"{len(items)} scènes trouvées (cloud_cover <= {max_cloud_cover}%)")

    # 5. Filtrer les scènes déjà traitées
    existing_ids = {s["id"] for s in manifest.get("scenes", [])}
    if skip_existing:
        to_process = [item for item in items if item.id not in existing_ids]
        print(f"{len(to_process)} nouvelles scènes à traiter "
              f"({len(items) - len(to_process)} déjà présentes)")
    else:
        to_process = items

    if not to_process:
        print("Rien à télécharger.")
        return manifest

    # 6. Traitement scène par scène
    print(f"\n--- Téléchargement ({max_workers} workers concurrents pour SCL) ---")

    # Phase 1 : SCL concurrent (filtrage)
    print("\nPhase 1/2 : Filtrage SCL")
    scl_results: dict[str, tuple[float, np.ndarray] | None] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for item in to_process:
            scene_dir = get_scene_dir(zone_dir, item.id)
            future = executor.submit(
                _download_scl, item, aoi_geom, "EPSG:4326", scene_dir
            )
            futures[future] = item

        for future in as_completed(futures):
            item = futures[future]
            try:
                result = future.result()
                scl_results[item.id] = result
                if result is not None:
                    frac = result[0]
                    print(f"  {item.id} : fraction valide {frac:.2%}")
                else:
                    print(f"  {item.id} : SCL indisponible")
            except Exception as e:
                print(f"  {item.id} : ÉCHEC SCL ({e})")
                scl_results[item.id] = None

    # Phase 2 : Bandes pour les scènes exploitables
    print("\nPhase 2/2 : Téléchargement des bandes")
    usable_items = [
        item
        for item in to_process
        if scl_results.get(item.id) is not None
        and scl_results[item.id][0] >= min_valid_fraction
    ]
    skipped = len(to_process) - len(usable_items)
    print(f"{len(usable_items)} scènes exploitables, {skipped} skipées")

    for i, item in enumerate(usable_items, 1):
        print(f"\n[{i}/{len(usable_items)}] {item.id}")

        entry = _process_scene(
            item=item,
            aoi_geom=aoi_geom,
            aoi_crs="EPSG:4326",
            zone_dir=zone_dir,
            bands=bands,
            min_valid_fraction=min_valid_fraction,
            max_retries=max_retries,
        )

        add_scene(manifest, entry)
        save_manifest(zone_dir, manifest)

    # 7. Résumé final
    all_scenes = manifest.get("scenes", [])
    usable = [s for s in all_scenes if s.get("usable")]
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Zone         : {zone_name}")
    print(f"  Période      : {start_date} → {end_date}")
    print(f"  Scènes totales     : {len(all_scenes)}")
    print(f"  Scènes exploitables : {len(usable)}")
    print(f"  Manifeste    : {zone_dir / 'manifest.json'}")
    print(f"  Données      : {zone_dir / 'scenes'}")

    return manifest