import geopandas as gpd

# 1. Charger la couche forestière téléchargée (ex: BD FORÊT)
gdf = gpd.read_file("data/BDFORET_33/FORMATION_VEGETALE.shp")
# 2. S'assurer de la projection en WGS84 (EPSG:4326) requise par le standard GeoJSON
if gdf.crs != "EPSG:4326":
    gdf = gdf.to_crs(epsg=4326)

# 3. Exporter au format GeoJSON pour ton pipeline
gdf.to_file("forets.geojson", driver="GeoJSON")