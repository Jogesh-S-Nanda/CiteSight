#!/usr/bin/env python3

import argparse
import re
from pathlib import Path
from pypdf import PdfReader


def clean(value: str) -> str:
    """Make metadata suitable for a Linux filename."""
    value = re.sub(r"[\x00-\x1f/\\]+", " ", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value.strip(". ")


def extract_year(metadata) -> str:
    # Prefer a four-digit year found in the PDF creation date.
    value = str(metadata.get("/CreationDate", ""))
    match = re.search(r"\b(18|19|20)\d{2}\b", value)
    return match.group(0) if match else "Unknown Year"


def unique_path(path: Path) -> Path:
    """Avoid overwriting an existing PDF."""
    if not path.exists():
        return path

    number = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
        if not candidate.exists():
            return candidate
        number += 1


def proposed_name(pdf: Path) -> Path:
    reader = PdfReader(pdf)
    metadata = reader.metadata or {}

    year = extract_year(metadata)
    author = clean(str(metadata.get("/Author", ""))) or "Unknown Author"
    title = clean(str(metadata.get("/Title", ""))) or clean(pdf.stem)

    # Limit excessively long filenames.
    filename = clean(f"{year} {author} {title}")[:220] + ".pdf"
    return unique_path(pdf.with_name(filename))


def main():
    parser = argparse.ArgumentParser(
        description="Rename PDFs to 'YYYY Author Title.pdf'."
    )
    parser.add_argument("folder", type=Path)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually rename files; otherwise perform a dry run.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Include PDFs in subdirectories.",
    )
    args = parser.parse_args()

    folder = args.folder.expanduser().resolve()

    if not folder.is_dir():
        raise SystemExit(f"Not a directory: {folder}")

    pattern = "**/*.pdf" if args.recursive else "*.pdf"

    for pdf in sorted(folder.glob(pattern)):
        try:
            destination = proposed_name(pdf)

            if destination == pdf:
                print(f"UNCHANGED: {pdf}")
            elif args.apply:
                pdf.rename(destination)
                print(f"RENAMED: {pdf.name} -> {destination.name}")
            else:
                print(f"DRY RUN: {pdf.name} -> {destination.name}")

        except Exception as error:
            print(f"ERROR: {pdf}: {error}")


if __name__ == "__main__":
    main()