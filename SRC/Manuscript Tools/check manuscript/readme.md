# Manuscript Filename Compatibility Checker

`check_manuscript.sh` recursively checks a manuscript directory for filename,
path, link, and access problems that can cause failures when files are moved
between Linux, Windows, macOS, network storage, and removable media.

The default mode is read-only. An optional fix mode safely renames a limited
set of incompatible names and then runs the complete check again.

## Author and affiliation

- **Author:** Jogesh S Nanda
- **Affiliation:** Indian Institute of Science (IISc), Bengaluru, India
- **Project:** CiteSight
- **Copyright:** Copyright (c) 2026 Jogesh Nanda, IISc

## What the checker detects

The script reports:

- Windows-forbidden filename characters: `< > : " \ | ? *`
- control characters, including tabs and newlines
- names ending in a dot or space
- reserved Windows device names such as `CON`, `NUL`, `COM1`, and `LPT1`
- individual names longer than 255 bytes
- complete paths longer than 4096 bytes
- broken symbolic links
- unreadable files
- directories that cannot be read or searched
- names that collide on a case-insensitive filesystem, such as `Paper.pdf`
  and `paper.pdf`
- incomplete scans caused by directory traversal errors

The checker examines every item below the selected directory. The directory
passed on the command line is used as the scan root and is not itself included
in the item count.

> **Scope:** This tool checks filesystem compatibility. It does not validate a
> manuscript's PDF contents, citations, formatting, or scientific quality.

## Requirements

- Linux or another Unix-like system
- Bash 4.3 or newer (Bash 4.4 or newer is recommended)
- standard command-line tools: `find` and `mv`
- read and search permission for the directory being checked
- write permission in affected directories when using `--fix`

No Python packages are required to run the filename checker. The
`rename_manuscript.py` file in this directory is a separate PDF-renaming tool.

## Quick start

From the repository root, check a directory without changing anything:

```bash
bash "SRC/Manuscript Tools/check manuscript/check_manuscript.sh" \
  "/path/to/manuscripts"
```

For example:

```bash
bash "SRC/Manuscript Tools/check manuscript/check_manuscript.sh" \
  "$HOME/Downloads/manuscripts"
```

Quoting both paths is important when either path contains spaces or shell
metacharacters.

You may optionally make the script executable:

```bash
chmod u+x "SRC/Manuscript Tools/check manuscript/check_manuscript.sh"
"SRC/Manuscript Tools/check manuscript/check_manuscript.sh" \
  "/path/to/manuscripts"
```

## Check-only mode

This is the default and safest mode:

```text
check_manuscript.sh DIRECTORY
```

It prints a summary table followed by detailed, grouped findings. Paths are
shell-escaped in the output so that spaces, newlines, and other unusual
characters remain unambiguous. It never renames or edits an item.

A clean scan ends with:

```text
Result: PASS - no common filename or access problems found.
```

If findings exist, the result is:

```text
Result: ATTENTION REQUIRED - found N issue(s).
```

`N` is the number of findings, not necessarily the number of unique paths. One
path can contribute to several categories.

## Automatic fix mode

After reviewing a check-only run, use `--fix` if appropriate:

```bash
bash "SRC/Manuscript Tools/check manuscript/check_manuscript.sh" \
  --fix "/path/to/manuscripts"
```

Fix mode processes children before their parent directories. It:

1. replaces control characters with spaces;
2. replaces `< > : " \ | ? *` with underscores;
3. refuses to overwrite an existing path;
4. prints every successful rename and every skipped or failed rename; and
5. reruns the complete compatibility scan on the resulting directory.

Fix mode does **not** automatically repair trailing dots or spaces, reserved
Windows names, excessive lengths, broken links, permission problems, or
case-insensitive collisions. These remain in the final report for manual
resolution.

Although existing paths are never overwritten, renaming can affect bookmarks,
scripts, citations, or applications that refer to the old path. Keep a backup
or work on a copy when filenames are externally referenced. There is no
built-in undo command.

## Exit status

| Code | Meaning |
| ---: | --- |
| `0` | The final scan passed with no findings. In fix mode, corrections may have been made before this result. |
| `1` | The final scan found one or more compatibility or access issues. |
| `2` | The command was invalid, the target was not a directory, or the scan root could not be read/searched. |

This makes the checker suitable for scripts and validation jobs:

```bash
if bash "SRC/Manuscript Tools/check manuscript/check_manuscript.sh" \
  "/path/to/manuscripts"; then
    echo "The manuscript directory passed the compatibility check."
else
    echo "Review the checker output before transferring the directory."
fi
```

To retain an audit log, redirect both standard output and standard error:

```bash
bash "SRC/Manuscript Tools/check manuscript/check_manuscript.sh" \
  "/path/to/manuscripts" > manuscript-check.log 2>&1
```

## Interpreting and resolving findings

| Finding | Suggested action |
| --- | --- |
| Forbidden or control characters | Review and use `--fix`, or rename the item manually. |
| Trailing dot or space | Rename the item so its name ends in a visible character. |
| Reserved Windows name | Choose a descriptive name that is not a Windows device name. |
| Name or path too long | Shorten the item name or move the directory closer to the filesystem root. |
| Broken symbolic link | Restore its target or remove/recreate the link as appropriate. |
| Unreadable file | Review ownership and permissions; do not broaden access without considering sensitive data. |
| Inaccessible directory | Grant the intended user suitable read/search access, or run the check as an authorized user. |
| Case-insensitive collision | Rename one of the conflicting items before copying to a case-insensitive filesystem. |
| Incomplete scan | Read the preceding `find` error, correct the access or filesystem problem, and run the checker again. |

## Known limitations

- Length checks count bytes under the script's `C` locale; filesystem and
  application limits can be lower than the reported thresholds.
- A successful scan covers common portability hazards, but it cannot guarantee
  acceptance by every filesystem, cloud service, archive format, or
  manuscript-submission portal.
- Case-collision detection uses lowercase relative paths and is intended as a
  conservative portability warning.
- Permission results describe the user running the command; another user or
  service account may receive different results.
- Files can change during a scan. Avoid modifying the target tree concurrently
  when a reproducible result is required.

## License

This work is provided to the **Indian Institute of Science (IISc)** and other
recipients under the **GNU General Public License, version 3 (GPL-3.0)**, as
used by the CiteSight repository. IISc may use, study, modify, and redistribute
the software under the terms of that license.

The complete license text is available in the repository's
[`LICENSE`](../../../LICENSE) file. This software is provided without warranty,
to the extent permitted by the GPL-3.0.

The author's IISc affiliation and this license notice do not imply institutional
endorsement of results produced by the checker.
