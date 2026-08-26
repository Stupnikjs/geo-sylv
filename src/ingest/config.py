"""Configuration : variables d'environnement pour l'accès S3 Copernicus."""

import os
from pathlib import Path

# --- Credentials Copernicus EO DataSpace (S3) ---
_S3_ACCESS_KEY = "CLZN1E05TUXMT25FJCID"
_S3_SECRET_KEY = "UpTldRQnVrsx3bgplVfZQKzHgQzxAa9i576BV0oo"
_S3_ENDPOINT = "eodata.dataspace.copernicus.eu"

# --- Catalogue STAC ---
STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac"

# --- Collection Sentinel-2 L2A ---
COLLECTION = "sentinel-2-l2a"


def load_env():
    """Configure les variables d'environnement pour vsis3 / rasterio."""
    os.environ["AWS_ACCESS_KEY_ID"] = _S3_ACCESS_KEY
    os.environ["AWS_SECRET_ACCESS_KEY"] = _S3_SECRET_KEY
    os.environ["AWS_S3_ENDPOINT"] = _S3_ENDPOINT
    os.environ["AWS_VIRTUAL_HOSTING"] = "FALSE"
    os.environ["AWS_HTTPS"] = "TRUE"


def load_windows_env():
    """Workaround pour Windows : force des chemins temp valides pour GDAL."""
    if os.name != "nt":
        return
    temp = Path(r"C:\temp")
    temp.mkdir(parents=True, exist_ok=True)
    (temp / "gdal_data").mkdir(exist_ok=True)
    os.environ["USERPROFILE"] = str(temp)
    os.environ["HOME"] = str(temp)
    os.environ["TEMP"] = str(temp)
    os.environ["TMP"] = str(temp)
    os.environ["GDAL_DATA"] = str(temp / "gdal_data")


def setup():
    """À appeler une fois au démarrage, avant tout accès réseau."""
    load_windows_env()
    load_env()