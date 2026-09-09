#!/usr/bin/env bash
# Run the manuscript renamer on Downloads from any working directory.
# Author: Jogesh S Nanda <jogesh.s.nanda@gmail.com>
# Usage: ./rename.sh [--recursive] [--overrides /path/to/metadata.json]
# The Python program receives --apply, so running this launcher renames PDFs.

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
downloads_dir="$HOME/Downloads"
# Use CiteSight's configured environment, which includes pypdf.
python_executable='/home/yogesh/PycharmProjects/CiteSight/.venv/bin/python'
renamer=''

# Resolve bin relative to this launcher, not the terminal's current directory.
for candidate in \
    "$script_dir/bin/rename_manuscript.py" \
    "$script_dir/bin/rename_manuscript.p"; do
    if [[ -f "$candidate" && -r "$candidate" ]]; then
        renamer="$candidate"
        break
    fi
done

if [[ -z "$renamer" ]]; then
    printf 'Error: cannot find a readable manuscript renamer in %s/bin\n' "$script_dir" >&2
    exit 1
fi
if [[ ! -d "$downloads_dir" ]]; then
    printf 'Error: Downloads folder does not exist: %s\n' "$downloads_dir" >&2
    exit 1
fi
if [[ ! -x "$python_executable" ]]; then
    printf 'Error: Python interpreter is unavailable: %s\n' "$python_executable" >&2
    exit 1
fi

# Quoting preserves spaces in paths; exec forwards the Python exit status.
exec "$python_executable" "$renamer" "$downloads_dir" --apply "$@"
