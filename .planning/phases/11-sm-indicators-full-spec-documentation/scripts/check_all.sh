#!/usr/bin/env bash
# =============================================================================
# check_all.sh — Full suite runner for Phase 11 SM Indicators spec audit
# =============================================================================
# Rubric source: .planning/phases/11-sm-indicators-full-spec-documentation/11-VALIDATION.md
# Wave 0 Requirement #2 — wraps check_spec.sh + check_index.sh over all 15 expected files.
#
# Usage (from project root):
#   bash .planning/phases/11-sm-indicators-full-spec-documentation/scripts/check_all.sh
#
# Exit codes:
#   0  — ALL 15 files present, ALL specs pass, INDEX passes, 0 dep-graph warnings
#   1  — one or more failures (summary printed to stdout)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Locate script directory so we can call sibling scripts regardless of cwd
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Root directory for the docs tree (quoted to handle the space in "SM Indicators")
# ---------------------------------------------------------------------------
DOCS_ROOT="resource_pack/MMM/SM Indicators/docs"

# ---------------------------------------------------------------------------
# 15-file manifest
# (3 helpers + 11 indicators + INDEX — exact filenames from 11-CONTEXT.md)
# ---------------------------------------------------------------------------
declare -a SPEC_FILES=(
    "${DOCS_ROOT}/helpers/sm_gmtoffset.md"
    "${DOCS_ROOT}/helpers/sm_WorkTime.md"
    "${DOCS_ROOT}/helpers/sm_WorkTime_no_autogmt.md"
    "${DOCS_ROOT}/indicators/SM_ADR_Marker.md"
    "${DOCS_ROOT}/indicators/SM_Daily_HiLo.md"
    "${DOCS_ROOT}/indicators/SM_BPCT.md"
    "${DOCS_ROOT}/indicators/SM_IlsleyPsychLevels.md"
    "${DOCS_ROOT}/indicators/SM_Crossover_Arrows.md"
    "${DOCS_ROOT}/indicators/SM_TDI.md"
    "${DOCS_ROOT}/indicators/SM_PivotPoints.md"
    "${DOCS_ROOT}/indicators/SM_AlertZone_1.md"
    "${DOCS_ROOT}/indicators/SM_AlertZone_2.md"
    "${DOCS_ROOT}/indicators/SM_Alerting+TL.md"
    "${DOCS_ROOT}/indicators/SM_NewHUD.md"
)
INDEX_FILE="${DOCS_ROOT}/INDEX.md"

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
files_expected=15
files_present=0
files_passing=0
suite_failures=0
dep_warn_count=0
index_status="NOT_YET_WRITTEN"

# ---------------------------------------------------------------------------
# Step 1: File existence check
# ---------------------------------------------------------------------------
missing_files=()
for f in "${SPEC_FILES[@]}" "${INDEX_FILE}"; do
    if [[ -f "$f" ]]; then
        ((files_present++)) || true
    else
        missing_files+=("$f")
    fi
done

if [[ ${#missing_files[@]} -gt 0 ]]; then
    echo "INFO: ${#missing_files[@]} files not yet written, continuing audit on existing files"
    for mf in "${missing_files[@]}"; do
        echo "  MISSING FILE: ${mf}"
    done
fi

# ---------------------------------------------------------------------------
# Step 2: Per-spec conformance check (only on EXISTING spec files, not INDEX)
# ---------------------------------------------------------------------------
for f in "${SPEC_FILES[@]}"; do
    if [[ -f "$f" ]]; then
        if "$SCRIPT_DIR/check_spec.sh" "$f"; then
            ((files_passing++)) || true
        else
            ((suite_failures++)) || true
        fi
    fi
done

# ---------------------------------------------------------------------------
# Step 3: INDEX audit (if INDEX.md exists)
# ---------------------------------------------------------------------------
if [[ -f "$INDEX_FILE" ]]; then
    if "$SCRIPT_DIR/check_index.sh" "$INDEX_FILE"; then
        index_status="PASS"
    else
        index_status="FAIL"
        ((suite_failures++)) || true
    fi
else
    index_status="NOT_YET_WRITTEN"
fi

# ---------------------------------------------------------------------------
# Step 4: Dependency graph cross-check
# ---------------------------------------------------------------------------
# For each EXISTING spec (non-INDEX), check if the body mentions sm_gmtoffset
# or sm_WorkTime outside the Dependencies section; if so, verify those helpers
# are also listed IN the Dependencies section.
#
# Implementation: for each helper token, if it appears in the body of the spec
# AND does NOT appear in the Dependencies section of that spec, emit a warning.
declare -a dep_helpers=("sm_gmtoffset" "sm_WorkTime")

for f in "${SPEC_FILES[@]}"; do
    if [[ ! -f "$f" ]]; then
        continue
    fi
    spec_basename="$(basename "$f")"
    for helper in "${dep_helpers[@]}"; do
        # Check if the helper token appears anywhere in the body
        body_count=$(grep -c "$helper" "$f" 2>/dev/null || true)
        if [[ "$body_count" -gt 0 ]]; then
            # Check if the helper token appears in the Dependencies section specifically
            dep_section_count=$(awk '
                /^(## |### ).*Dependencies/ { in_section=1; next }
                in_section && /^## / { exit }
                in_section { print }
            ' "$f" | grep -c "$helper" 2>/dev/null || true)
            if [[ "$dep_section_count" -eq 0 ]]; then
                echo "WARN: ${spec_basename} mentions '${helper}' in body but does not list it in Dependencies section"
                ((dep_warn_count++)) || true
            fi
        fi
    done
done

# ---------------------------------------------------------------------------
# Step 5: Final summary
# ---------------------------------------------------------------------------
echo ""
echo "=== Phase 11 Spec Audit Summary ==="
echo "Files expected: ${files_expected}"
echo "Files present:  ${files_present}"
echo "Files passing:  ${files_passing}"
echo "INDEX status:   ${index_status}"
echo "Dep-graph warnings: ${dep_warn_count}"
echo "==================================="

# ---------------------------------------------------------------------------
# Exit logic: 0 only if ALL conditions met; otherwise 1
# ---------------------------------------------------------------------------
if [[ "$files_present" -eq "$files_expected" ]] && \
   [[ "$files_passing" -eq "$((files_expected - 1))" ]] && \
   [[ "$index_status" == "PASS" ]] && \
   [[ "$dep_warn_count" -eq 0 ]]; then
    exit 0
else
    exit 1
fi
