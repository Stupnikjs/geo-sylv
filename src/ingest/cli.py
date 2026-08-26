"""Interface en ligne de commande pour le package ingest."""

import argparse

from .downloader import DEFAULT_BANDS, ingest


def main():
    parser = argparse.ArgumentParser(
        prog="ingest",
        description=(
            "Télécharge les bandes Sentinel-2 L2A pour une AOI et une période. "
            "Les bandes sont découpées sur l'AOI et sauvegardées localement en GeoTIFF. "
            "Un manifest.json liste toutes les scènes téléchargées."
        ),
    )
    parser.add_argument(
        "--geojson",
        required=True,
        help="Chemin vers le GeoJSON de l'AOI.",
    )
    parser.add_argument(
        "--zone",
        required=True,
        help="Nom court de la zone (ex: chambord, vosges).",
    )
    parser.add_argument(
        "--start",
        default="2017-01-01",
        help="Date de début YYYY-MM-DD (défaut: 2017-01-01).",
    )
    parser.add_argument(
        "--end",
        default="2023-12-31",
        help="Date de fin YYYY-MM-DD (défaut: 2023-12-31).",
    )
    parser.add_argument(
        "--output-dir",
        default="./data",
        help="Dossier de sortie (défaut: ./data).",
    )
    parser.add_argument(
        "--bands",
        nargs="+",
        default=None,
        help=(
            f"Bandes à télécharger (défaut: {' '.join(DEFAULT_BANDS)}). "
            "Ex: --bands B08_10m B04_10m SCL_20m"
        ),
    )
    parser.add_argument(
        "--max-cloud-cover",
        type=int,
        default=60,
        help="Cloud cover max sur la scène entière (défaut: 60).",
    )
    parser.add_argument(
        "--min-valid-fraction",
        type=float,
        default=0.8,
        help="Fraction min de pixels valides SCL (défaut: 0.8).",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Téléchargements simultanés (défaut: 4).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-télécharge même les scènes déjà présentes.",
    )

    args = parser.parse_args()

    ingest(
        geojson_path=args.geojson,
        zone_name=args.zone,
        start_date=args.start,
        end_date=args.end,
        output_dir=args.output_dir,
        bands=args.bands,
        max_cloud_cover=args.max_cloud_cover,
        min_valid_fraction=args.min_valid_fraction,
        max_workers=args.max_workers,
        skip_existing=not args.force,
    )


if __name__ == "__main__":
    main()