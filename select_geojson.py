

import geopandas as gpd

# Charger le GeoJSON
gdf = gpd.read_file("data/projects/gironde/gironde.geojson")


# Tirer une parcelle au hasard
parcelle = gdf.sample(n=1)

# Afficher son ID
print(parcelle["ID"].iloc[0])

# L'enregistrer dans un nouveau GeoJSON
parcelle.to_file(
    "parcelle_au_hasard.geojson",
    driver="GeoJSON"
)