#!/usr/bin/env bash

# Filename Compatibility Checker
# Author: Jogesh S Nanda
# Copyright (c) 2026 Jogesh Nanda, IISc
#
# Purpose:
#   Recursively identify names that may fail when copied between Linux,
#   Windows, macOS, network storage, or removable media.
#
# Safety:
#   Normal mode is read-only. With --fix, control characters are replaced by
#   spaces and Windows-forbidden characters are replaced by underscores.
#   Existing paths are never overwritten.

set -u
export LC_ALL=C
shopt -s lastpipe

readonly PROGRAM_NAME='Filename Compatibility Checker'
readonly AUTHOR='Jogesh S Nanda'
readonly COPYRIGHT='Copyright (c) 2026 Jogesh Nanda, IISc'

usage() {
    printf 'Usage: %s [--fix] DIRECTORY\n' "${0##*/}"
    printf 'Check only: %s "/home/me/Documents"\n' "${0##*/}"
    printf 'Auto-fix:  %s --fix "/home/me/Documents"\n' "${0##*/}"
}

# Print a stable heading so saved terminal logs remain self-explanatory.
print_banner() {
    local mode=$1
    printf '%s\n' '============================================================'
    printf '  %s\n' "$PROGRAM_NAME"
    printf '  Author: %s\n' "$AUTHOR"
    printf '  %s\n' "$COPYRIGHT"
    printf '%s\n' '------------------------------------------------------------'
    printf '  Mode:   %s\n' "$mode"
    printf '  Target: %q\n' "$root"
    printf '%s\n\n' '============================================================'
}

fix_mode=0
if (( $# == 2 )) && [[ $1 == --fix ]]; then
    fix_mode=1
    shift
elif (( $# != 1 )); then
    usage >&2
    exit 2
fi

root=$1
if [[ ! -d $root ]]; then
    printf 'Error: not a directory: %s\n' "$root" >&2
    exit 2
fi

if [[ ! -r $root || ! -x $root ]]; then
    printf 'Error: directory cannot be read or searched: %s\n' "$root" >&2
    exit 2
fi

# Remove trailing slashes, except for the filesystem root.
while [[ $root != / && $root == */ ]]; do
    root=${root%/}
done

if (( fix_mode )); then
    print_banner 'AUTO-FIX AND VERIFY'
else
    print_banner 'CHECK ONLY (NO CHANGES)'
fi

# Auto-fix result lists. Parallel old/new arrays preserve exact rename pairs.
renamed_old=()
renamed_new=()
skipped_old=()
skipped_new=()
rename_failures=()

if (( fix_mode )); then
    printf 'Auto-correcting names under: %q\n' "$root"

    # Process children before parents so renamed directories do not invalidate
    # paths that find has already returned.
    find "$root" -depth -mindepth 1 -print0 | while IFS= read -r -d '' path; do
        name=${path##*/}
        parent=${path%/*}
        fixed=${name//[[:cntrl:]]/ }
        fixed=${fixed//['<>:"|?*']/_}
        fixed=${fixed//\\/_}

        [[ $fixed == "$name" ]] && continue
        new_path=$parent/$fixed

        if [[ -e $new_path || -L $new_path ]]; then
            skipped_old+=("$path")
            skipped_new+=("$new_path")
        elif mv -- "$path" "$new_path"; then
            renamed_old+=("$path")
            renamed_new+=("$new_path")
        else
            rename_failures+=("$path")
        fi
    done
    fix_find_status=${PIPESTATUS[0]}

    printf '\n--- AUTO-FIX OVERVIEW ---\n'
    printf '  %-32s %8d\n' 'Successfully renamed:' "${#renamed_old[@]}"
    printf '  %-32s %8d\n' 'Skipped to prevent overwrite:' "${#skipped_old[@]}"
    printf '  %-32s %8d\n' 'Rename failures:' "${#rename_failures[@]}"
    printf '  %-32s %8d\n' 'Traversal failures:' "$((fix_find_status != 0))"

    # Detailed audit trail: every successful old-to-new mapping.
    printf '\n=== RENAMED (%d) ===\n' "${#renamed_old[@]}"
    for ((i = 0; i < ${#renamed_old[@]}; i++)); do
        printf '  - %q\n    -> %q\n' "${renamed_old[i]}" "${renamed_new[i]}"
    done

    if (( ${#skipped_old[@]} > 0 )); then
        printf '\n=== SKIPPED TO PREVENT OVERWRITE (%d) ===\n' "${#skipped_old[@]}"
        for ((i = 0; i < ${#skipped_old[@]}; i++)); do
            printf '  - %q\n    target already exists: %q\n' \
                "${skipped_old[i]}" "${skipped_new[i]}"
        done
    fi

    if (( ${#rename_failures[@]} > 0 || fix_find_status != 0 )); then
        printf '\nWarning: one or more names could not be corrected.\n' >&2
        for path in "${rename_failures[@]}"; do
            printf '  - rename failed: %q\n' "$path" >&2
        done
    fi

    printf '\nRechecking corrected directory...\n\n'
fi

# Scan counters and one array per issue category. Keeping categories separate
# allows both a compact overview and readable grouped details.
issues=0
checked=0
declare -A case_seen=()
windows_forbidden=()
control_characters=()
trailing_dot_space=()
reserved_names=()
long_names=()
long_paths=()
broken_links=()
unreadable_files=()
inaccessible_directories=()
case_collision_paths=()
case_collision_others=()
incomplete_scans=()

add_issue() {
    local array_name=$1 path=$2
    local -n destination=$array_name
    destination+=("$path")
    ((issues++))
}

print_group() {
    local title=$1 description=$2 array_name=$3
    local -n entries=$array_name
    local path

    (( ${#entries[@]} == 0 )) && return
    printf '\n=== %s (%d) ===\n' "$title" "${#entries[@]}"
    printf '%s\n' "$description"
    for path in "${entries[@]}"; do
        printf '  - %q\n' "$path"
    done
}

# Print every category, including zero-count categories, for a complete view.
print_overview() {
    printf '\n--- SCAN OVERVIEW ---\n'
    printf '  %-38s %8s\n' 'Category' 'Count'
    printf '  %-38s %8s\n' '--------------------------------------' '--------'
    printf '  %-38s %8d\n' 'Windows-forbidden characters' "${#windows_forbidden[@]}"
    printf '  %-38s %8d\n' 'Control characters' "${#control_characters[@]}"
    printf '  %-38s %8d\n' 'Trailing dot or space' "${#trailing_dot_space[@]}"
    printf '  %-38s %8d\n' 'Reserved Windows names' "${#reserved_names[@]}"
    printf '  %-38s %8d\n' 'Names longer than 255 bytes' "${#long_names[@]}"
    printf '  %-38s %8d\n' 'Paths longer than 4096 bytes' "${#long_paths[@]}"
    printf '  %-38s %8d\n' 'Broken symbolic links' "${#broken_links[@]}"
    printf '  %-38s %8d\n' 'Unreadable files' "${#unreadable_files[@]}"
    printf '  %-38s %8d\n' 'Inaccessible directories' "${#inaccessible_directories[@]}"
    printf '  %-38s %8d\n' 'Case-insensitive collisions' "${#case_collision_paths[@]}"
    printf '  %-38s %8d\n' 'Incomplete scans' "${#incomplete_scans[@]}"
    printf '  %-38s %8s\n' '--------------------------------------' '--------'
    printf '  %-38s %8d\n' 'Items checked' "$checked"
    printf '  %-38s %8d\n' 'Total findings' "$issues"
}

printf 'Checking: %q\n\n' "$root"

find "$root" -mindepth 1 -print0 | while IFS= read -r -d '' path; do
    ((checked++))
    name=${path##*/}
    rel=${path#"$root"/}

    # Characters forbidden by Windows and commonly rejected by copy tools.
    if [[ $name == *['<>:"/\|?*']* ]]; then
        add_issue windows_forbidden "$path"
    fi

    if [[ $name =~ [[:cntrl:]] ]]; then
        add_issue control_characters "$path"
    fi

    if [[ $name == *'.' || $name == *' ' ]]; then
        add_issue trailing_dot_space "$path"
    fi

    # Windows device names are invalid even when followed by an extension.
    base=${name%%.*}
    upper=${base^^}
    case $upper in
        CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])
            add_issue reserved_names "$path"
            ;;
    esac

    # Most Linux, Windows, and macOS filesystems limit one component to 255 bytes.
    if (( ${#name} > 255 )); then
        add_issue long_names "$path"
    fi

    # A conservative cross-platform full-path warning.
    if (( ${#path} > 4096 )); then
        add_issue long_paths "$path"
    fi

    if [[ -L $path && ! -e $path ]]; then
        add_issue broken_links "$path"
    elif [[ -f $path && ! -r $path ]]; then
        add_issue unreadable_files "$path"
    elif [[ -d $path && ( ! -r $path || ! -x $path ) ]]; then
        add_issue inaccessible_directories "$path"
    fi

    # Detect names that collide on case-insensitive filesystems.
    folded=${rel,,}
    if [[ -v 'case_seen[$folded]' && ${case_seen[$folded]} != "$rel" ]]; then
        case_collision_paths+=("$path")
        case_collision_others+=("${case_seen[$folded]}")
        ((issues++))
    else
        case_seen[$folded]=$rel
    fi
done
find_status=${PIPESTATUS[0]}

if (( find_status != 0 )); then
    add_issue incomplete_scans "$root"
fi

# The overview is always printed, even when the directory is completely clean.
print_overview

if (( issues == 0 )); then
    printf '\nResult: PASS - no common filename or access problems found.\n'
    exit 0
fi

printf '\nDetailed findings grouped by type:\n'

print_group 'WINDOWS-FORBIDDEN CHARACTERS' \
    'Contains one or more of: < > : " / \ | ? *' windows_forbidden
print_group 'CONTROL CHARACTERS' \
    'Contains a newline, tab, or another non-printing control character.' control_characters
print_group 'TRAILING DOT OR SPACE' \
    'Ends with a dot or space, which Windows does not support.' trailing_dot_space
print_group 'RESERVED WINDOWS NAMES' \
    'Uses a device name such as CON, NUL, COM1, or LPT1.' reserved_names
print_group 'NAMES LONGER THAN 255 BYTES' \
    'The individual file or directory name is too long for many filesystems.' long_names
print_group 'PATHS LONGER THAN 4096 BYTES' \
    'The complete path exceeds the conservative portability limit.' long_paths
print_group 'BROKEN SYMBOLIC LINKS' \
    'The symbolic-link target does not exist.' broken_links
print_group 'UNREADABLE FILES' \
    'The current user cannot read the file.' unreadable_files
print_group 'INACCESSIBLE DIRECTORIES' \
    'The current user cannot read or search the directory.' inaccessible_directories

if (( ${#case_collision_paths[@]} > 0 )); then
    printf '\n=== CASE-INSENSITIVE COLLISIONS (%d) ===\n' "${#case_collision_paths[@]}"
    printf 'These names conflict when copied to a case-insensitive filesystem.\n'
    for ((i = 0; i < ${#case_collision_paths[@]}; i++)); do
        printf '  - %q\n    conflicts with: %q\n' \
            "${case_collision_paths[i]}" "${case_collision_others[i]}"
    done
fi

print_group 'INCOMPLETE SCANS' \
    'The directory traversal failed before every item could be checked.' incomplete_scans

printf '\nResult: ATTENTION REQUIRED - found %d issue(s).\n' "$issues"
exit 1
