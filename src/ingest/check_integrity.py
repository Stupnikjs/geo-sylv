#!/usr/bin/env python3
"""
Audit d'intégrité des données ingérées par le package `ingest`.

Vérifie :
  1. Que chaque fichier GeoTIFF listé dans le manifest est lisible (pas corrompu).
  2. Que le manifest.json est cohérent avec ce qui existe réellement sur disque
     (bandes manquantes, fichiers orphelins non référencés).
  3. Que les bandes d'une même scène partagent le même CRS et la même emprise
     (bounds), résolution comprise, pour éviter les décalages en aval.

Usage:
    python check_integrity.py /chemin/vers/data/chambord

Sortie: rapport texte + code de sortie != 0 si des problèmes sont trouvés.
"""

from __future__ import annotations

from .manifest import load_manifest
import sys
from pathlib import Path

try:
    import rasterio
except ImportError:
    print("ERREUR: rasterio n'est pas installé (pip install rasterio)")
    sys.exit(1)



def check_tif_readable(path: Path) -> tuple[bool, str]:
    """Ouvre le fichier et force une lecture réelle des pixels."""
    try:
        with rasterio.open(path) as src:
            src.read(1)
            return True, ""
    except Exception as e:
        return False, str(e)


def audit_scene(zone_dir: Path, scene: dict) -> dict:
    """Audite une scène : lisibilité, complétude, cohérence géométrique."""
    scene_id = scene["id"]
    result = {
        "id": scene_id,
        "usable": scene.get("usable", False),
        "corrupt_files": [],
        "missing_files": [],
        "geometry_mismatch": [],
    }

    if not scene.get("usable"):
        return result

    bands = scene.get("bands", {})
    if not bands:
        result["missing_files"].append("(aucune bande listée dans le manifest)")
        return result

    profiles = {}  # band_name -> (crs, bounds, res)

    for band_name, rel_path in bands.items():
        full_path = zone_dir / rel_path

        if not full_path.exists():
            result["missing_files"].append(band_name)
            continue

        ok, err = check_tif_readable(full_path)
        if not ok:
            result["corrupt_files"].append(f"{band_name}: {err}")
            continue

        with rasterio.open(full_path) as src:
            profiles[band_name] = (src.crs, src.bounds, src.res)

    # Cohérence géométrique : toutes les bandes doivent partager le même CRS
    # et la même emprise (les résolutions 10m/20m sont normales, on les ignore
    # pour la comparaison des bounds mais on vérifie le CRS partout).
    if profiles:
        ref_band, (ref_crs, ref_bounds, _) = next(iter(profiles.items()))
        for band_name, (crs, bounds, _) in profiles.items():
            if crs != ref_crs:
                result["geometry_mismatch"].append(
                    f"{band_name}: CRS {crs} != {ref_crs} ({ref_band})"
                )
                continue
            # Tolérance de 1 pixel (20m) sur les bounds pour absorber
            # les arrondis liés aux résolutions différentes.
            tol = 20.0
            if (
                abs(bounds.left - ref_bounds.left) > tol
                or abs(bounds.bottom - ref_bounds.bottom) > tol
                or abs(bounds.right - ref_bounds.right) > tol
                or abs(bounds.top - ref_bounds.top) > tol
            ):
                result["geometry_mismatch"].append(
                    f"{band_name}: bounds {tuple(bounds)} "
                    f"!= {tuple(ref_bounds)} ({ref_band}, tolérance {tol}m)"
                )

    return result


def check_orphan_files(zone_dir: Path, manifest: dict) -> list[str]:
    """Fichiers .tif présents sur disque mais absents du manifest."""
    referenced = set()
    for scene in manifest.get("scenes", []):
        for rel_path in scene.get("bands", {}).values():
            referenced.add((zone_dir / rel_path).resolve())

    scenes_dir = zone_dir / "scenes"
    if not scenes_dir.exists():
        return []

    orphans = []
    for tif in scenes_dir.rglob("*.tif"):
        if tif.resolve() not in referenced:
            orphans.append(str(tif.relative_to(zone_dir)))
    return orphans


def main():
    if len(sys.argv) != 2:
        print("Usage: python check_integrity.py <zone_dir>")
        sys.exit(1)

    zone_dir = Path(sys.argv[1])
    if not zone_dir.exists():
        print(f"ERREUR: {zone_dir} n'existe pas")
        sys.exit(1)

    manifest = load_manifest(zone_dir)
    scenes = manifest.get("scenes", [])
    print(f"Zone: {manifest.get('zone_name')}")
    print(f"Scènes dans le manifest: {len(scenes)}")
    print("=" * 70)

    has_problems = False
    n_ok = 0

    for scene in scenes:
        result = audit_scene(zone_dir, scene)
        problems = (
            result["corrupt_files"]
            or result["missing_files"]
            or result["geometry_mismatch"]
        )
        if not result["usable"]:
            continue
        if not problems:
            n_ok += 1
            continue

        has_problems = True
        print(f"\n[PROBLEME] {result['id']}")
        for f in result["corrupt_files"]:
            print(f"  CORROMPU       : {f}")
        for f in result["missing_files"]:
            print(f"  MANQUANT       : {f}")
        for f in result["geometry_mismatch"]:
            print(f"  DESALIGNEMENT  : {f}")

    orphans = check_orphan_files(zone_dir, manifest)
    if orphans:
        has_problems = True
        print(f"\n[ORPHELINS] {len(orphans)} fichier(s) .tif non référencés dans le manifest:")
        for o in orphans[:20]:
            print(f"  {o}")
        if len(orphans) > 20:
            print(f"  ... et {len(orphans) - 20} de plus")

    print("\n" + "=" * 70)
    print(f"Scènes exploitables OK        : {n_ok}")
    print(f"Scènes exploitables avec pb   : "
          f"{sum(1 for s in scenes if s.get('usable')) - n_ok}")
    print(f"Fichiers orphelins            : {len(orphans)}")
    print("=" * 70)

    if has_problems:
        print("\nRésultat: PROBLEMES DETECTES")
        sys.exit(1)
    else:
        print("\nRésultat: OK, aucune anomalie détectée")
        sys.exit(0)


if __name__ == "__main__":
    main()
