#!/usr/bin/env bash
# Render a paper markdown file to PDF with pandoc + tectonic (XeTeX).
#
#   ./paper/render.sh              # renders every .md in paper/
#   ./paper/render.sh mathy.md     # renders one
#
# Math is written \(inline\) and \[display\], which is what MathJax wants in
# the markdown; `tex_math_single_backslash` is what makes pandoc read it.
# Requires pandoc and tectonic on PATH (both install to ~/.local/bin as
# single binaries; no sudo and no TeX Live -- tectonic fetches what it needs).

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for tool in pandoc tectonic; do
    command -v "$tool" >/dev/null || { echo "render.sh: $tool is not on PATH" >&2; exit 1; }
done

targets=("$@")
if [ ${#targets[@]} -eq 0 ]; then
    mapfile -t targets < <(cd "$here" && ls *.md 2>/dev/null)
    [ ${#targets[@]} -gt 0 ] || { echo "render.sh: no .md files in $here" >&2; exit 1; }
fi

for target in "${targets[@]}"; do
    src="$here/$(basename "$target")"
    [ -f "$src" ] || { echo "render.sh: no such file: $src" >&2; exit 1; }
    [ -s "$src" ] || { echo "render.sh: skipping empty $(basename "$src")"; continue; }
    stem="$(basename "$src" .md)"
    work="$(mktemp -d)"
    trap 'rm -rf "$work"' EXIT

    pandoc "$src" \
        --from=markdown+tex_math_single_backslash \
        --to=latex \
        --standalone \
        --syntax-highlighting=none \
        --include-in-header="$here/_render/preamble.tex" \
        --variable=documentclass:article \
        --variable=fontsize:10pt \
        --variable=colorlinks:true \
        --variable=linkcolor:NavyBlue \
        --output="$work/$stem.tex"

    # --keep-logs leaves the real TeX log, which is where an
    # undefined macro shows up; tectonic's own output does not always say.
    if ! tectonic -X compile "$work/$stem.tex" --outdir "$work" \
            --keep-logs >"$work/out" 2>&1; then
        echo "render.sh: tectonic failed on $stem" >&2
        tail -40 "$work/out" >&2
        exit 1
    fi

    # A missing macro does not fail the build, so check for it explicitly.
    # This is the point of rendering through LaTeX at all: it catches markup
    # that MathJax accepts but a LaTeX paper pipeline would not.
    # "Missing character" matters as much as an undefined macro: the symbol
    # is dropped from the page without any error. That is how \setminus went
    # missing the first time this file was rendered.
    if grep -qE "Undefined control sequence|LaTeX Error|Missing character" "$work/$stem.log"; then
        echo "render.sh: $stem has bad markup --" >&2
        grep -B1 -A3 -E "Undefined control sequence|LaTeX Error|Missing character" \
            "$work/$stem.log" >&2
        exit 1
    fi

    mv "$work/$stem.pdf" "$here/$stem.pdf"
    echo "render.sh: wrote paper/$stem.pdf"
    rm -rf "$work"
    trap - EXIT
done
