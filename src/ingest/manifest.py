"""
Manifeste JSON : registre des scènes téléchargées.

C'est le seul point d'interface entre `ingest` et les packages en aval
(indices, visu). Tout ce qu'il faut pour travailler en local s'y trouve.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _manifest_path(zone_dir: str | Path) -> Path:
    return Path(zone_dir) / "manifest.json"


def _scenes_dir(zone_dir: str | Path) -> Path:
    return Path(zone_dir) / "scenes"


def get_scene_dir(zone_dir: str | Path, scene_id: str) -> Path:
    """Retourne le chemin vers le dossier d'une scène."""
    return _scenes_dir(zone_dir) / scene_id


def load_manifest(zone_dir: str | Path) -> dict | None:
    """Charge le manifeste JSON. Retourne None s'il n'existe pas."""
    f = _manifest_path(zone_dir)
    if not f.exists():
        return None
    with open(f, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_manifest(zone_dir: str | Path, manifest: dict) -> None:
    """Sauvegarde le manifeste en JSON (indenté, lisible)."""
    Path(zone_dir).mkdir(parents=True, exist_ok=True)
    f = _manifest_path(zone_dir)
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False, default=str)


def create_manifest(
    zone_name: str,
    geojson_path: str,
    start_date: str,
    end_date: str,
    bands: list[str],
    aoi_crs: str = "EPSG:4326",
    aoi_bounds: list[float] | None = None,
    area_ha: float | None = None,
) -> dict:
    """Crée un manifeste vide."""
    return {
        "zone_name": zone_name,
        "geojson_path": str(geojson_path),
        "start_date": start_date,
        "end_date": end_date,
        "aoi_crs": aoi_crs,
        "aoi_bounds": aoi_bounds,
        "area_ha": area_ha,
        "bands": bands,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "scenes": [],
    }


def add_scene(manifest: dict, scene_entry: dict) -> dict:
    """Ajoute ou remplace une scène dans le manifeste."""
    scenes = manifest.get("scenes", [])
    # Remplace si déjà présent (même id)
    scenes = [s for s in scenes if s["id"] != scene_entry["id"]]
    scenes.append(scene_entry)
    scenes.sort(key=lambda s: s["datetime"])
    manifest["scenes"] = scenes
    return manifest


def list_scenes(manifest: dict) -> list[dict]:
    """Retourne la liste des scènes du manifeste."""
    return manifest.get("scenes", [])


def get_band_path(scene_entry: dict, band_name: str) -> Path | None:
    """
    Retourne le chemin vers un fichier de bande pour une scène donnée.
    None si la bande n'est pas disponible.
    """
    bands = scene_entry.get("bands", {})
    path_str = bands.get(band_name)
    if path_str is None:
        return None
    return Path(path_str)


def get_usable_scenes(manifest: dict) -> list[dict]:
    """Retourne uniquement les scènes exploitables (valid_fraction > seuil)."""
    return [s for s in list_scenes(manifest) if s.get("usable", False)]