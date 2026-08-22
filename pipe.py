import time
import os
import json

import geopandas as gpd
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import rasterio
from rasterio.mask import mask
from pystac_client import Client

os.environ["USERPROFILE"] = r"C:\temp"
os.environ["HOME"] = r"C:\temp"
os.environ["TEMP"] = r"C:\temp"
os.environ["TMP"] = r"C:\temp"
os.environ["GDAL_DATA"] = r"C:\temp\gdal_data"
os.makedirs(r"C:\temp", exist_ok=True)

# clé récupérée depuis une variable d'environnement système, jamais en dur
os.environ["AWS_ACCESS_KEY_ID"] = "CLZN1E05TUXMT25FJCID"
os.environ["AWS_SECRET_ACCESS_KEY"] = "UpTldRQnVrsx3bgplVfZQKzHgQzxAa9i576BV0oo"
os.environ["AWS_S3_ENDPOINT"] = "eodata.dataspace.copernicus.eu"
os.environ["AWS_VIRTUAL_HOSTING"] = "FALSE"
os.environ["AWS_HTTPS"] = "TRUE"

# === Zone d'intérêt ===

new_zone = gpd.read_file("data/projects/foret_chambord/untitled.geojson")
new_zone = new_zone.to_crs(epsg=4326)
clean_gdf = new_zone

bounds = clean_gdf.total_bounds
bbox = list(bounds)
poly_area_ha = clean_gdf.to_crs(epsg=2154).geometry.area.iloc[0] / 10_000

print("Nouvelle bbox :", bbox)
print(f"Aire de la zone : {poly_area_ha:.1f} ha")

# === Recherche STAC avec retry ===

catalog = Client.open("https://catalogue.dataspace.copernicus.eu/stac")

def search_with_retry(catalog, max_retries=5, base_delay=5, **search_kwargs):
    for attempt in range(max_retries):
        try:
            search = catalog.search(**search_kwargs)
            return list(search.items())
        except Exception as e:
            if "429" in str(e):
                delay = base_delay * (2 ** attempt)
                print(f"Rate limit, attente {delay}s (tentative {attempt+1}/{max_retries})")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("Échec après plusieurs tentatives")

items = search_with_retry(
    catalog,
    collections=["sentinel-2-l2a"],
    bbox=bbox,
    datetime="2021-01-01/2023-12-31",
)
print(f"{len(items)} scènes trouvées sur la période")
items = sorted(items, key=lambda i: i.datetime)

# === Lecture clippée ===

def read_clipped(url, aoi_gdf):
    with rasterio.open(url) as src:
        aoi_proj = aoi_gdf.to_crs(src.crs)
        geom = [aoi_proj.geometry.iloc[0].__geo_interface__]
        out_image, out_transform = mask(src, geom, crop=True)
        profile = src.profile.copy()
        profile.update({
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
        })
    return out_image[0].astype("float32"), profile

def read_clipped_safe(url, aoi_gdf, max_retries=3):
    for attempt in range(max_retries):
        try:
            return read_clipped(url, aoi_gdf)
        except Exception as e:
            if "429" in str(e):
                delay = 5 * (2 ** attempt)
                print(f"Rate limit sur lecture, attente {delay}s...")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"Échec de lecture après {max_retries} tentatives : {url}")

# === Filtre qualité (bande SCL) ===

def get_valid_fraction_safe(item, aoi_gdf, cloud_classes=(3, 8, 9, 10, 11), max_retries=3):
    scl_url = item.assets["SCL_20m"].href
    scl, _ = read_clipped_safe(scl_url, aoi_gdf, max_retries=max_retries)
    invalid = np.isin(scl, cloud_classes)
    valid_fraction = 1 - (invalid.sum() / scl.size)
    return valid_fraction, invalid

usable_items = []
for item in items:
    try:
        frac, _ = get_valid_fraction_safe(item, clean_gdf)
        if frac > 0.8:
            usable_items.append(item)
        time.sleep(0.5)  # throttling systématique
    except Exception as e:
        print(f"Skip {item.id} (SCL) : {e}")
        continue

print(f"{len(usable_items)} / {len(items)} scènes exploitables après filtre SCL")

# === Série temporelle d'indice ===

def compute_index_timeseries(items, aoi_gdf, index="ndmi"):
    records = []

    for item in items:
        try:
            if index == "nbr":
                b_num, b_denom = "B8A_20m", "B12_20m"
            elif index == "ndvi":
                b_num, b_denom = "B08_10m", "B04_10m"
            elif index == "ndmi":
                b_num, b_denom = "B8A_20m", "B11_20m"

            num, _ = read_clipped_safe(item.assets[b_num].href, aoi_gdf)
            denom, _ = read_clipped_safe(item.assets[b_denom].href, aoi_gdf)

            frac_valid, invalid_mask = get_valid_fraction_safe(item, aoi_gdf)
            if frac_valid < 0.8:
                continue

            idx_array = (num - denom) / (num + denom + 1e-6)
            idx_array_masked = np.where(invalid_mask, np.nan, idx_array)

            records.append({
                "date": item.datetime,
                "mean": np.nanmean(idx_array_masked),
                "std": np.nanstd(idx_array_masked),
                "p10": np.nanpercentile(idx_array_masked, 10),
                "valid_fraction": frac_valid,
                "item_id": item.id,
            })
            time.sleep(0.5)  # throttling systématique
        except Exception as e:
            print(f"Skip {item.id} : {e}")
            continue

    return pd.DataFrame(records)

ts_ndmi = compute_index_timeseries(usable_items, clean_gdf, index="ndmi")
ts_ndmi = ts_ndmi.sort_values("date").reset_index(drop=True)
print(ts_ndmi)

# === Visualisation ===

fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(ts_ndmi["date"], ts_ndmi["mean"], marker="o", markersize=3)
ax.fill_between(
    ts_ndmi["date"],
    ts_ndmi["mean"] - ts_ndmi["std"],
    ts_ndmi["mean"] + ts_ndmi["std"],
    alpha=0.15,
)
ax.set_ylabel("NDMI moyen")
ax.set_title("Série temporelle NDMI - Forêt de Chambord")
plt.tight_layout()
plt.show()