import argparse
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import geopandas as gpd
import numpy as np
import pandas as pd
from pystac_client import Client


from errors import search_with_retry
from store import load, save, _cache_file
from config import load_windows_env, load_env
from raster import read_clipped_bands


# Classes SCL à exclure : nuage moyen/haute proba (8,9), cirrus (10), ombre (3), neige (11)
# + no-data (0) et pixel défectueux/saturé (1), absents du filtre initial
CLOUD_CLASSES = (0, 1, 3, 8, 9, 10, 11)
MIN_VALID_FRACTION = 0.8
MAX_CLOUD_COVER_SCENE = 60  # pré-filtre grossier sur métadonnée, avant tout téléchargement
MAX_CONCURRENT_REQUESTS = 4  # borne la concurrence réseau réelle, remplace les sleep fixes

INDEX_BANDS = {
    "nbr": ("B8A_20m", "B12_20m"),
    "ndvi": ("B08_10m", "B04_10m"),
    "ndmi": ("B8A_20m", "B11_20m"),
}


def get_valid_fraction(item, aoi_geom, aoi_crs="EPSG:4326", cloud_classes=CLOUD_CLASSES, max_retries=3):
    scl_url = item.assets["SCL_20m"].href
    scl = read_clipped_bands([scl_url], aoi_geom, aoi_crs, max_retries=max_retries)[0]
    invalid = np.isin(scl, cloud_classes)
    valid_fraction = 1 - (invalid.sum() / scl.size)
    return valid_fraction, invalid


# load et save le cache 
def filter_usable_scenes(items, aoi_geom, zone_name, aoi_crs="EPSG:4326", max_workers=MAX_CONCURRENT_REQUESTS):
    # Cache tenu par zone_name : évite qu'une zone lise/écrase le cache d'une autre
    # (avant, le chemin de cache était hardcodé sur "foret_chambord" pour tout le monde).
    cache = load(zone_name, "quality")
    to_fetch = [item for item in items if cache.get(item.id) is None]

    if to_fetch:
        print(f"Calcul SCL pour {len(to_fetch)} scènes (absentes du cache)...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(get_valid_fraction, item, aoi_geom, aoi_crs): item for item in to_fetch
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    frac, invalid_mask = future.result()
                    cache[item.id] = {"valid_fraction": frac, "invalid_mask": invalid_mask}
                except Exception as e:
                    print(f"Skip {item.id} (SCL) : {e}")
                    cache[item.id] = None
        save(cache, zone_name, "quality")

    usable_items = [
        item for item in items if cache.get(item.id) is not None and cache[item.id]["valid_fraction"] > MIN_VALID_FRACTION
    ]
    return usable_items, cache


def compute_index_for_item(item, aoi_geom, aoi_crs, index, scl_entry):
    b_num, b_denom = INDEX_BANDS[index]
    urls = [item.assets[b_num].href, item.assets[b_denom].href]
    num, denom = read_clipped_bands(urls, aoi_geom, aoi_crs)

    # Pixels no-data en bord de tuile : num == denom == 0 donne (0-0)/(0+eps) = 0,
    # qui s'invitait silencieusement dans la moyenne car non couvert par le masque SCL.
    nodata_mask = (num == 0) & (denom == 0)
    full_invalid = scl_entry["invalid_mask"] | nodata_mask

    idx_array = (num - denom) / (num + denom + 1e-6)
    idx_array_masked = np.where(full_invalid, np.nan, idx_array)

    return {
        "date": item.datetime,
        "mean": np.nanmean(idx_array_masked),
        "std": np.nanstd(idx_array_masked),
        "p10": np.nanpercentile(idx_array_masked, 10),
        "valid_fraction": scl_entry["valid_fraction"],
        "item_id": item.id,
    }


def compute_index_timeseries(items, aoi_geom, scl_cache, index, aoi_crs="EPSG:4326", max_workers=MAX_CONCURRENT_REQUESTS):
    records = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for item in items:
            scl_entry = scl_cache.get(item.id)
            if scl_entry is None:
                continue
            futures[executor.submit(compute_index_for_item, item, aoi_geom, aoi_crs, index, scl_entry)] = item

        for future in as_completed(futures):
            item = futures[future]
            try:
                records.append(future.result())
            except Exception as e:
                print(f"Skip {item.id} : {e}")
                continue

    return pd.DataFrame(records)


def run(zone_name, geojson_path, start_date, end_date, index, output_dir):
    

    zone = gpd.read_file(geojson_path).to_crs(epsg=4326)
    aoi_geom_4326 = zone.geometry.union_all()
    # retourne un tuple (min_lon, min_lat, max_lon, max_lat) — le plus petit rectangle englobant ta géométrie (peu importe sa forme réelle, même irrégulière)
    # bbox sert uniquement à la recherche de scènes
    bbox = list(aoi_geom_4326.bounds)
    poly_area_ha = gpd.GeoSeries([aoi_geom_4326], crs=4326).to_crs(epsg=2154).area.iloc[0] / 10_000

    print(f"Zone : {zone_name}")
    print(f"Bbox : {bbox}")
    print(f"Aire de la zone : {poly_area_ha:.1f} ha")

    catalog = Client.open("https://catalogue.dataspace.copernicus.eu/stac")


    # liste d'objets pystac.Item — chacun représentant une scène, avec ses métadonnées et ses liens vers les fichiers image
    items = search_with_retry(
        catalog,
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
    )
    print(f"{len(items)} scènes trouvées sur la période")

    # Pré-filtre sur le cloud_cover de la scène ENTIÈRE (métadonnée, zéro téléchargement).
    # Ne remplace pas le filtre SCL précis sur l'AOI plus bas (une scène à 50% de nuages
    # globalement peut être parfaitement claire sur la zone d'intérêt, et inversement) —
    # ça évite juste de télécharger des scènes manifestement inutilisables.
    items = [item for item in items if item.properties.get("eo:cloud_cover", 0) <= MAX_CLOUD_COVER_SCENE]
    print(f"{len(items)} scènes après pré-filtre cloud_cover <= {MAX_CLOUD_COVER_SCENE}%")
    items = sorted(items, key=lambda i: i.datetime)

    usable_items, scl_cache = filter_usable_scenes(items, aoi_geom_4326, zone_name)
    print(f"{len(usable_items)} / {len(items)} scènes exploitables après filtre SCL")

    ts = compute_index_timeseries(usable_items, aoi_geom_4326, scl_cache, index=index)
    if ts.empty:
        print(f"Aucune scène exploitable pour {zone_name} sur {start_date}/{end_date}, série vide.")
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{index}_{zone_name}_{start_date[:4]}_{end_date[:4]}.csv"
        ts.to_csv(out_path, index=False)
        return ts
    ts = ts.sort_values("date").reset_index(drop=True)


    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{index}_{zone_name}_{start_date[:4]}_{end_date[:4]}.csv"
    ts.to_csv(out_path, index=False)

    print(ts)
    print(f"Résultat sauvegardé : {out_path}")
    return ts



def run_by_year(
    zone_name,
    geojson_path,
    start_date,
    end_date,
    index,
    output_dir,
):
    dfs = []

    if os.name == "nt":
        load_windows_env()

    load_env()

    # Extraire les années à partir des dates YYYY-MM-DD
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])

    for year in range(start_year, end_year + 1):

        # Gérer correctement les bornes si la période ne commence/termine
        # pas exactement au 1er janvier / 31 décembre.
        if year == start_year:
            year_start = start_date
        else:
            year_start = f"{year}-01-01"

        if year == end_year:
            year_end = end_date
        else:
            year_end = f"{year}-12-31"

        print("\n" + "=" * 70)
        print(f"TRAITEMENT ANNÉE {year}")
        print(f"Période : {year_start} → {year_end}")
        print("=" * 70)

        try:
            df_year = run(
                zone_name=zone_name,
                geojson_path=geojson_path,
                start_date=year_start,
                end_date=year_end,
                index=index,
                output_dir=output_dir,
            )

            if not df_year.empty:
                dfs.append(df_year)

        except Exception as e:
            print(f"Erreur pour {year} : {e}")
            continue

    if not dfs:
        print("Aucune donnée disponible.")
        return pd.DataFrame()

    # Concaténation des DataFrames annuels
    df = pd.concat(dfs, ignore_index=True)

    # Tri chronologique
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # CSV final
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = (
        out_dir
        / f"{index}_{zone_name}_{start_year}_{end_year}.csv"
    )

    df.to_csv(out_path, index=False)

    print("\n" + "=" * 70)
    print("SÉRIE TEMPORELLE FINALE")
    print("=" * 70)
    print(df)
    print(f"\nRésultat final sauvegardé : {out_path}")

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcul de série temporelle d'indice spectral sur une AOI")
    parser.add_argument("--zone", required=True, help="Nom court de la zone (ex: chambord, vosges) — utilisé pour le cache et les fichiers de sortie")
    parser.add_argument("--geojson", required=True, help="Chemin vers le GeoJSON de l'AOI")
    parser.add_argument("--start", default="2017-01-01", help="Date de début (YYYY-MM-DD), défaut: 2017-01-01 (début de la disponibilité L2A en Europe)")
    parser.add_argument("--end", default="2023-12-31", help="Date de fin (YYYY-MM-DD)")
    parser.add_argument("--index", default="ndmi", choices=list(INDEX_BANDS.keys()), help="Indice spectral à calculer")
    parser.add_argument("--output-dir", default="./data", help="Dossier de sortie pour le CSV")
    args = parser.parse_args()

    run_by_year(
        zone_name=args.zone,
        geojson_path=args.geojson,
        start_date=args.start,
        end_date=args.end,
        index=args.index,
        output_dir=args.output_dir,
    )