# Manuscript PDF Renamer

The manuscript renamer gives PDF files consistent, descriptive names in this
format:

```text
Year First Author Title.pdf
```

For example:

```text
2024 Jane Smith A Study of Citation Networks.pdf
```

It reads PDF metadata and first-page text, previews proposed names by default,
and renames files only when explicitly instructed. PDF contents are never
modified.

## Author and affiliation

- **Author:** Jogesh S Nanda
- **Email:** <jogesh.s.nanda@gmail.com>
- **Affiliation:** Indian Institute of Science (IISc), Bengaluru, India
- **Project:** CiteSight
- **Copyright:** Copyright (c) 2026 Jogesh S Nanda, IISc

## Components

- [`rename.sh`](rename.sh) is a convenience launcher intended to rename PDFs
  in `$HOME/Downloads`.
- [`rename_manuscript.py`](../check%20manuscript/rename_manuscript.py) performs
  metadata extraction, previews, recursive processing, overrides, and renaming.

> **Current layout note:** `rename.sh` searches for the Python program at
> `rename maniscript/bin/rename_manuscript.py` (or the legacy `.p` filename),
> while this repository currently stores it in the sibling `check manuscript`
> directory. Until the launcher and deployment layout are aligned, use the
> direct Python commands below. Otherwise, the launcher exits with
> `cannot find a readable manuscript renamer`.

## Requirements

- Python 3.10 or newer
- the `pypdf` package
- permission to read the PDFs
- write permission in each containing directory when applying changes
- lowercase `.pdf` filename extensions

The project launcher is configured to use:

```text
/home/yogesh/PycharmProjects/CiteSight/.venv/bin/python
```

That environment must exist and contain `pypdf`. If the project is moved, use
the Python interpreter configured for the new environment and update
`python_executable` in `rename.sh` before using the launcher.

## Quick start: preview first

From the repository root, preview proposed names without changing any files:

```bash
/home/yogesh/PycharmProjects/CiteSight/.venv/bin/python \
  "SRC/Manuscript Tools/check manuscript/rename_manuscript.py" \
  "$HOME/Downloads"
```

The default operation is a dry run. Review every `DRY RUN` line before applying
the changes.

To preview PDFs in Downloads and all its subdirectories:

```bash
/home/yogesh/PycharmProjects/CiteSight/.venv/bin/python \
  "SRC/Manuscript Tools/check manuscript/rename_manuscript.py" \
  "$HOME/Downloads" --recursive
```

Any directory can be supplied instead of `$HOME/Downloads` when the Python
program is invoked directly.

## Apply the proposed names

Add `--apply` only after reviewing the preview:

```bash
/home/yogesh/PycharmProjects/CiteSight/.venv/bin/python \
  "SRC/Manuscript Tools/check manuscript/rename_manuscript.py" \
  "$HOME/Downloads" --apply
```

To rename PDFs recursively:

```bash
/home/yogesh/PycharmProjects/CiteSight/.venv/bin/python \
  "SRC/Manuscript Tools/check manuscript/rename_manuscript.py" \
  "$HOME/Downloads" --recursive --apply
```

Only filenames change. Each PDF remains in its original directory. There is no
built-in undo command, so retain a backup or save the preview output if the
original names may be needed later.

## Convenience launcher

Once `rename_manuscript.py` is available in the launcher's expected `bin`
directory, run:

```bash
bash "SRC/Manuscript Tools/rename maniscript/rename.sh"
```

For subdirectories:

```bash
bash "SRC/Manuscript Tools/rename maniscript/rename.sh" --recursive
```

The launcher always:

- targets `$HOME/Downloads`;
- uses its hard-coded project Python interpreter;
- passes `--apply`, so changes happen immediately; and
- forwards other arguments to the Python program.

The launcher cannot select another target directory because it supplies
`$HOME/Downloads` as the required positional argument. Use the Python program
directly for another directory or for a safe preview.

## How names are generated

### Year

The program searches, in order, for likely publication-year information in:

- meeting or subject metadata;
- the first few lines of the first page;
- arXiv or DOI metadata;
- a `Published` statement in first-page text; and
- the PDF creation or modification date as a fallback.

PDF creation dates may differ from publication dates. If no year can be found,
the filename uses `Unknown Year`.

### First author

The first author is taken from PDF author metadata when available. Otherwise,
the program attempts to read the line following the title on the first page.
Common author separators, affiliation numbers, and markers are cleaned. If no
author can be inferred, the filename uses `Unknown Author`.

### Title

The title is read from PDF metadata. If title metadata is missing, the current
filename is used after removing a recognized year and author prefix from an
earlier run.

### Filename safety and collisions

- control characters, `/`, and `\` are replaced with spaces;
- repeated whitespace and leading/trailing dots or spaces are removed;
- the generated stem is limited to 220 UTF-8 bytes;
- an existing destination is never overwritten; and
- conflicts receive suffixes such as `(2)`, `(3)`, and so on.

An already-correct filename remains unchanged.

## Correct inaccurate or missing metadata

Automatic extraction is heuristic. Verified values can be supplied through a
JSON overrides file without modifying the PDF. Overrides are keyed by the PDF's
SHA-256 content digest, so they still apply after the file is renamed.

First obtain the digest:

```bash
sha256sum "$HOME/Downloads/example.pdf"
```

Then create `$HOME/Downloads/.manuscript_metadata.json`:

```json
{
  "REPLACE_WITH_THE_COMPLETE_64_CHARACTER_SHA256_DIGEST": {
    "year": 2024,
    "author": "Jane Smith",
    "title": "A Study of Citation Networks"
  }
}
```

Each entry may contain `year`, `author`, `title`, or any combination of those
fields. The default override file is `.manuscript_metadata.json` in the target
directory.

To use another file:

```bash
/home/yogesh/PycharmProjects/CiteSight/.venv/bin/python \
  "SRC/Manuscript Tools/check manuscript/rename_manuscript.py" \
  "$HOME/Downloads" \
  --overrides "/absolute/path/to/metadata.json"
```

Preview the overridden results first, then repeat the command with `--apply`.
If the specified file does not exist, the current implementation treats it as
an empty override set. Invalid JSON or invalid value types produce an error.

## Command reference

```text
rename_manuscript.py FOLDER [--apply] [--recursive] [--overrides FILE]
```

| Argument | Description |
| --- | --- |
| `FOLDER` | Directory containing the PDFs. Required. |
| `--apply` | Rename files. Without it, only preview proposed names. |
| `--recursive` | Include PDFs in all subdirectories. |
| `--overrides FILE` | Load verified metadata from the specified JSON file. |
| `--help` | Display command-line help and exit without processing PDFs. |

The program matches lowercase `*.pdf`. On a case-sensitive filesystem, names
ending in `.PDF` or `.Pdf` are not processed. Other file types are ignored.

## Reading the output

| Output | Meaning |
| --- | --- |
| `DRY RUN: old.pdf -> new.pdf` | Preview only; no filename was changed. |
| `RENAMED: old.pdf -> new.pdf` | The filename was changed successfully. |
| `UNCHANGED: path` | The current filename already matches the proposal. |
| `ERROR: path: message` | That PDF could not be processed; other PDFs continue. |
| No output | No matching lowercase `.pdf` files were found at the selected depth. |

An error for one PDF is caught so that processing can continue. Consequently,
the process can finish successfully even when one or more files printed an
`ERROR` line. Always review the complete output.

## Troubleshooting

| Problem | Resolution |
| --- | --- |
| `No module named 'pypdf'` | Install `pypdf` in the exact Python environment used for the command. |
| `Not a directory` | Check the target path and quote it if it contains spaces. |
| `cannot find a readable manuscript renamer` | The launcher cannot see its expected `bin/rename_manuscript.py`; use the direct command or correct the deployment layout. |
| `Downloads folder does not exist` | Create `$HOME/Downloads` or invoke the Python program with the correct directory. |
| `Python interpreter is unavailable` | Restore the project environment or update `python_executable` in `rename.sh`. |
| Incorrect year, author, or title | Add verified values to an overrides file and preview again. |
| JSON parsing error | Use valid JSON with double-quoted keys and no trailing commas. |
| No PDFs processed | Check filename extensions and add `--recursive` when files are in subdirectories. |

## Known limitations

- Metadata and first-page text can be missing, malformed, or inaccurate.
- Scanned PDFs without searchable text provide fewer author and year hints.
- Preview does not reserve destination names. If files change between preview
  and application, collision suffixes may differ.
- The generated filenames are made safe for Linux paths but should still be
  checked for the requirements of a specific submission system or filesystem.
- Concurrent renaming in the same directory can affect collision handling.

For a separate cross-platform filename audit, use the
[`check_manuscript.sh`](../check%20manuscript/check_manuscript.sh) tool after
renaming.

## License

This work is provided to the **Indian Institute of Science (IISc)** and other
recipients under the **GNU General Public License, version 3 (GPL-3.0)**, as
used by the CiteSight repository. IISc may use, study, modify, and redistribute
the software under the terms of that license.

The complete license text is available in the repository's
[`LICENSE`](../../../LICENSE) file. This software is provided without warranty,
to the extent permitted by the GPL-3.0.

The author's IISc affiliation and this license notice do not imply institutional
endorsement of metadata extracted or filenames generated by this tool.
