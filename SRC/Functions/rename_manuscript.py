#!/usr/bin/env python3
"""Rename manuscript PDFs to ``Year First Author Title.pdf``.

Author: Jogesh S Nanda <jogesh.s.nanda@gmail.com>
Project: CiteSight

Usage::

    python rename_manuscript.py ~/Downloads              # Preview names.
    python rename_manuscript.py ~/Downloads --apply      # Rename files.
    python rename_manuscript.py ~/Downloads --recursive  # Include subfolders.

Requires ``pypdf``. Metadata and first-page text provide naming hints; PDF
creation dates are only a fallback and may differ from publication dates.
Missing values remain ``Unknown Year`` or ``Unknown Author``.

Verified corrections can be supplied with ``--overrides`` or stored in
``.manuscript_metadata.json`` in the target folder. The JSON object maps each
PDF's SHA-256 digest to optional ``year``, ``author``, and ``title`` fields.
Content hashes keep these corrections valid after a file is renamed.
Only filenames change; PDF contents are never edited.
"""

import argparse
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

from pypdf import PdfReader


class MetadataOverride(TypedDict, total=False):
    """Manually verified fields that supersede automatic extraction."""

    year: str | int
    author: str
    title: str


def clean(value: str) -> str:
    """Make metadata suitable for a Linux filename."""
    value = re.sub(r"[\x00-\x1f/\\]+", " ", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value.strip(". ")


def metadata_text(metadata: Mapping[str, Any], key: str) -> str:
    """Resolve a PDF metadata value, returning an empty string when absent."""
    value = metadata.get(key)
    if hasattr(value, "get_object"):
        value = value.get_object()
    return str(value) if value is not None else ""


def extract_year(metadata: Mapping[str, Any], text: str = "") -> str:
    """Infer a year from publication hints, arXiv identifiers, or PDF dates.

    ``text`` is the first page's extracted text. These are heuristics, so
    manually verified overrides should resolve ambiguous publication dates.
    """
    # Publication years take precedence over when a PDF was generated.
    year_pattern = r"\b(?:18|19|20)\d{2}\b"
    for value in (metadata_text(metadata, "/Meeting Starting Date"),
                  metadata_text(metadata, "/Subject").split(";", 2)[1]
                  if ";" in metadata_text(metadata, "/Subject") else re.sub(r"https?://\S+", "", metadata_text(metadata, "/Subject")),
                  "\n".join(line for line in text.splitlines()[:3] if "doi" not in line.lower())):
        match = re.search(year_pattern, value)
        if match:
            return match.group(0)
    arxiv = metadata_text(metadata, "/arXivID") or metadata_text(metadata, "/DOI")
    match = re.search(r"(?:abs/|arxiv[.:/])(\d{2})\d{2}\.\d+", arxiv, re.I)
    if match:
        return str(2000 + int(match.group(1)))
    match = re.search(r"Published(?:\s+online)?\s*:[^\n]{0,60}?((?:19|20)\d{2})", text, re.I)
    if match:
        return match.group(1)
    for key in ("/CreationDate", "/ModDate"):
        # PDF dates concatenate year and month: D:20250630... has no word
        # boundary after the year, so match the first four digits directly.
        match = re.match(r"^(?:D:)?((?:18|19|20)\d{2})", metadata_text(metadata, key))
        if match:
            return match.group(1)
    return "Unknown Year"


def first_author(value: str) -> str:
    """Extract one author and remove ordinal labels and affiliation markers.

    Comma-separated names are ambiguous; a single ``Surname, Given`` pair
    is preserved when the surname contains only one word.
    """
    value = re.sub(r"^\s*\d+(?:st|nd|rd|th)\s+", "", value)
    # Common PDF author-list separators; preserve a lone 'Surname, Given'.
    value = re.split(r";|\s+and\s+|\s*&\s*|[·•]", value, maxsplit=1)[0]
    parts = value.split(",")
    if len(parts) > 2 or (len(parts) == 2 and len(parts[0].split()) > 1):
        value = parts[0]
    value = re.sub(r"[\d*†‡]+", "", value)
    return clean(value)


def author_from_text(text: str, title: str) -> str:
    """Read the line following a matched title, or return an empty string.

    Search near the start of the page, allowing the title to wrap across
    lines. This assumes the PDF's extracted reading order follows its layout.
    """
    # Match across wrapped title lines, then read the following author line.
    def normalize(value: str) -> str:
        """Ignore punctuation, whitespace, and case when matching titles."""
        return "".join(c for c in value.casefold() if c.isalnum())

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    target = normalize(title)
    if not target:
        return ""
    for start in range(min(20, len(lines))):
        for end in range(start + 1, min(start + 8, len(lines))):
            if normalize("".join(lines[start:end])) == target:
                return first_author(lines[end])
    return ""


def unique_path(path: Path) -> Path:
    """Find an unused name, appending ``(2)``, ``(3)``, etc. if necessary.

    This checks existing paths but does not reserve the returned filename.
    """
    if not path.exists():
        return path

    number = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
        if not candidate.exists():
            return candidate
        number += 1


def proposed_name(
    pdf: Path,
    overrides: Mapping[str, MetadataOverride] | None = None,
) -> Path:
    """Return a destination beside ``pdf`` without renaming or editing it.

    Overrides are keyed by PDF content digest. Reading or parsing errors
    propagate to the caller, which reports them separately for each file.
    """
    reader = PdfReader(pdf)
    metadata = reader.metadata or {}
    text = (reader.pages[0].extract_text() or "") if reader.pages else ""
    year = extract_year(metadata, text)
    raw_author = clean(metadata_text(metadata, "/Author"))
    title = clean(metadata_text(metadata, "/Title"))
    if not title:
        # Remove prefixes from earlier runs before reusing the filename.
        title = re.sub(r"^(?:Unknown Year|\d{4})\s+", "", clean(pdf.stem))
        for prefix in (raw_author, first_author(raw_author), "Unknown Author"):
            if prefix and title.startswith(prefix + " "):
                title = title[len(prefix) + 1:]
                break
    author = first_author(raw_author) or author_from_text(text, title) or "Unknown Author"
    if overrides:
        entry = overrides.get(hashlib.sha256(pdf.read_bytes()).hexdigest(), {})
        year = str(entry.get("year", year))
        author = first_author(entry.get("author", author))
        title = clean(entry.get("title", title))

    # Linux filename limits count bytes. Leave room for the extension and
    # collision suffix, dropping an incomplete UTF-8 character if truncated.
    filename = clean(f"{year} {author} {title}").encode("utf-8")[:220].decode("utf-8", errors="ignore") + ".pdf"
    destination = pdf.with_name(filename)
    # An already-correct filename must not acquire a collision suffix.
    return destination if destination == pdf else unique_path(destination)


def main() -> None:
    """Parse CLI options and preview or apply each PDF's proposed filename."""
    parser = argparse.ArgumentParser(
        description="Rename PDFs to 'YYYY First Author Title.pdf'."
    )
    parser.add_argument("folder", type=Path)
    parser.add_argument("--overrides", type=Path,
                        help="JSON mapping PDF SHA-256 hashes to verified metadata; defaults to .manuscript_metadata.json in the folder.")
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
    override_path = args.overrides or folder / ".manuscript_metadata.json"
    overrides: dict[str, MetadataOverride] = (
        json.loads(override_path.read_text()) if override_path.exists() else {}
    )

    pattern = "**/*.pdf" if args.recursive else "*.pdf"

    for pdf in sorted(folder.glob(pattern)):
        try:
            destination = proposed_name(pdf, overrides)

            if destination == pdf:
                print(f"UNCHANGED: {pdf}")
            elif args.apply:
                pdf.rename(destination)
                print(f"RENAMED: {pdf.name} -> {destination.name}")
            else:
                print(f"DRY RUN: {pdf.name} -> {destination.name}")

        except Exception as error:
            # One unreadable PDF should not prevent processing the others.
            print(f"ERROR: {pdf}: {error}")


if __name__ == "__main__":
    main()
