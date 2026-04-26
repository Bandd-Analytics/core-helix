#!/usr/bin/env bash
# =============================================================================
# check_index.sh — INDEX.md audit for Phase 11 SM Indicators docs
# =============================================================================
# Rubric source: .planning/phases/11-sm-indicators-full-spec-documentation/11-VALIDATION.md
# Wave 0 Requirement #3 — implements all 4 checks listed there.
#
# Usage:
#   bash check_index.sh [path-to-INDEX.md]
#
# Default INDEX.md path if not supplied:
#   resource_pack/MMM/SM Indicators/docs/INDEX.md
#
# Exit codes:
#   0  — INDEX passes all checks (PASS)
#   1  — INDEX fails one or more checks (failures listed)
#   2  — fatal: file not found
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve INDEX.md path
# ---------------------------------------------------------------------------
DEFAULT_INDEX="resource_pack/MMM/SM Indicators/docs/INDEX.md"
INDEX_FILE="${1:-$DEFAULT_INDEX}"

# ---------------------------------------------------------------------------
# Guard: file must exist
# ---------------------------------------------------------------------------
if [[ ! -f "$INDEX_FILE" ]]; then
    echo "FATAL: INDEX.md not found at: $INDEX_FILE"
    exit 2
fi

failures=0
failure_msgs=()

# ---------------------------------------------------------------------------
# Check 1: Overview heading present
# ---------------------------------------------------------------------------
# Accept any of: "## Overview", "## Introduction", "## How to use this folder"
if ! grep -qE "^## (Overview|Introduction|How to use this folder)" "$INDEX_FILE" 2>/dev/null; then
    failure_msgs+=("MISSING: Overview/Introduction heading (need '## Overview', '## Introduction', or '## How to use this folder')")
    ((failures++)) || true
fi

# ---------------------------------------------------------------------------
# Check 2: Dependency graph block present
# ---------------------------------------------------------------------------
# Accept either:
#   (a) a fenced code block within 100 lines after a heading containing "graph" or "Dependency"
#   (b) a fenced ```mermaid block anywhere in the file
if grep -q '```mermaid' "$INDEX_FILE" 2>/dev/null; then
    : # mermaid block found — check 2 passes
elif awk '
    /^(## |### ).*[Gg]raph|^(## |### ).*[Dd]ependency/ { heading_line=NR }
    heading_line > 0 && NR <= heading_line + 100 && /^```/ { found=1; exit }
    END { exit (found ? 0 : 1) }
' "$INDEX_FILE" 2>/dev/null; then
    : # fenced block within 100 lines of graph/Dependency heading — check 2 passes
else
    failure_msgs+=("MISSING: Dependency graph block (need a fenced code block near a 'graph'/'Dependency' heading, or a \`\`\`mermaid block)")
    ((failures++)) || true
fi

# ---------------------------------------------------------------------------
# Check 3: All 14 spec files linked via relative paths
# ---------------------------------------------------------------------------
# Expected filenames (from 11-CONTEXT.md):
declare -a expected_files=(
    # Helpers (3)
    "sm_gmtoffset.md"
    "sm_WorkTime.md"
    "sm_WorkTime_no_autogmt.md"
    # Indicators (11)
    "SM_ADR_Marker.md"
    "SM_Daily_HiLo.md"
    "SM_BPCT.md"
    "SM_IlsleyPsychLevels.md"
    "SM_Crossover_Arrows.md"
    "SM_TDI.md"
    "SM_PivotPoints.md"
    "SM_AlertZone_1.md"
    "SM_AlertZone_2.md"
    "SM_Alerting+TL.md"
    "SM_NewHUD.md"
)

for fname in "${expected_files[@]}"; do
    if ! grep -qF "$fname" "$INDEX_FILE" 2>/dev/null; then
        failure_msgs+=("MISSING LINK: ${fname}")
        ((failures++)) || true
    fi
done

# ---------------------------------------------------------------------------
# Check 4: MMM glossary cross-refs present
# ---------------------------------------------------------------------------
# Grep for at least one reference to resource_pack/MMM/docs/ OR MMM_Glossary OR MMM Book
if ! grep -qE "resource_pack/MMM/docs/|MMM_Glossary|MMM Book" "$INDEX_FILE" 2>/dev/null; then
    failure_msgs+=("MISSING: MMM glossary cross-reference (need 'resource_pack/MMM/docs/', 'MMM_Glossary', or 'MMM Book' in INDEX.md)")
    ((failures++)) || true
fi

# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------
if [[ "$failures" -eq 0 ]]; then
    echo "PASS: INDEX"
    exit 0
else
    echo "FAIL: INDEX (${failures} issues)"
    for msg in "${failure_msgs[@]}"; do
        echo "  - ${msg}"
    done
    exit 1
fi
