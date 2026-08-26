"""
Cache disque générique clé/valeur, par zone ET par namespace logique
(ex: "quality" pour la fraction valide SCL, "ndmi_results" pour les résultats
d'indice déjà calculés).

Remplace la duplication qu'on aurait entre un cache SCL et un futur cache
d'index : un seul mécanisme de stockage (pickle par fichier), plusieurs
usages dessus.
"""

import pickle
from pathlib import Path


def _cache_file(zone_name: str, namespace: str) -> Path:
    cache_dir = Path("./cache") / zone_name
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{namespace}.pkl"


def load(zone_name: str, namespace: str) -> dict:
    f = _cache_file(zone_name, namespace)
    if f.exists():
        with open(f, "rb") as fh:
            return pickle.load(fh)
    return {}


def save(cache: dict, zone_name: str, namespace: str) -> None:
    f = _cache_file(zone_name, namespace)
    with open(f, "wb") as fh:
        pickle.dump(cache, fh)
