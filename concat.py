#!/usr/bin/env python3
"""Concatène tous les fichiers .py trouvés dans un dossier (récursif) en un seul .txt."""

import argparse
from pathlib import Path


def concat_py_files(src_dir: Path, output_file: Path) -> None:
    py_files = sorted(src_dir.rglob("*.py"))

    if not py_files:
        print(f"Aucun fichier .py trouvé dans {src_dir}")
        return

    with output_file.open("w", encoding="utf-8") as out:
        for path in py_files:
            rel_path = path.relative_to(src_dir)
            out.write(f"{'=' * 80}\n")
            out.write(f"# FICHIER: {rel_path}\n")
            out.write(f"{'=' * 80}\n\n")
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = path.read_text(encoding="latin-1")
            out.write(content)
            out.write("\n\n")

    print(f"{len(py_files)} fichier(s) concaténé(s) dans {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Concatène les .py d'un dossier dans un .txt")
    parser.add_argument("src", nargs="?", default="src", help="Dossier source (défaut: src)")
    parser.add_argument("-o", "--output", default="output.txt", help="Fichier de sortie (défaut: output.txt)")
    args = parser.parse_args()

    src_dir = Path(args.src)
    if not src_dir.is_dir():
        raise SystemExit(f"Le dossier '{src_dir}' n'existe pas.")

    concat_py_files(src_dir, Path(args.output))