#!/usr/bin/env bash
# =============================================================================
# check_spec.sh — Per-spec conformance audit for Phase 11 SM Indicators specs
# =============================================================================
# Rubric source: .planning/phases/11-sm-indicators-full-spec-documentation/11-VALIDATION.md
# Wave 0 Requirement #1 — implements all 8 checks listed there.
#
# Usage:
#   bash check_spec.sh <path-to-spec.md>
#
# Exit codes:
#   0  — spec passes all checks (PASS)
#   1  — spec fails one or more checks (failures listed)
#   2  — fatal: file not found
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Guard: require exactly one argument
# ---------------------------------------------------------------------------
if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <spec_file.md>" >&2
    exit 2
fi

SPEC_FILE="$1"

# ---------------------------------------------------------------------------
# Check 1: File exists
# ---------------------------------------------------------------------------
if [[ ! -f "$SPEC_FILE" ]]; then
    echo "FATAL: file not found: $SPEC_FILE"
    exit 2
fi

failures=0
failure_msgs=()

# ---------------------------------------------------------------------------
# Check 2: All 12 H2/H3 sections present
# ---------------------------------------------------------------------------
# Section headings to find (case-sensitive; anchored to start-of-line)
# Pattern: ^## <term> or ^### <term> (anywhere in heading)
declare -a expected=(
    "Header"
    "Purpose"
    "Inputs"
    "Outputs"
    "Calculation"
    "Pseudocode"
    "Visual"
    "Dependencies"
    "Edge cases"
    "Test cases"
    "Port notes"
    "Uncertainty"
)

for term in "${expected[@]}"; do
    if ! grep -qE "^(## |### ).*${term}" "$SPEC_FILE" 2>/dev/null; then
        failure_msgs+=("MISSING SECTION: ${term}")
        ((failures++)) || true
    fi
done

# ---------------------------------------------------------------------------
# Check 3: Confidence declared in Header section
# ---------------------------------------------------------------------------
if ! grep -q "Confidence: High\|Confidence: Medium\|Confidence: Low" "$SPEC_FILE" 2>/dev/null; then
    failure_msgs+=("MISSING: Confidence declaration (need 'Confidence: High', 'Confidence: Medium', or 'Confidence: Low')")
    ((failures++)) || true
fi

# ---------------------------------------------------------------------------
# Check 4: At least one [INFER] tag present
# ---------------------------------------------------------------------------
if ! grep -qF "[INFER]" "$SPEC_FILE" 2>/dev/null && ! grep -qF "[INFER:guess]" "$SPEC_FILE" 2>/dev/null; then
    failure_msgs+=("MISSING: at least one [INFER] tag — every spec has at least one inference (sources are non-decompilable)")
    ((failures++)) || true
fi

# ---------------------------------------------------------------------------
# Check 5: Pseudocode block >= 10 lines
# ---------------------------------------------------------------------------
# Find first fenced code block (```) after the "Pseudocode" heading.
# Count lines between open-fence and close-fence; require >= 10.
pseudocode_lines=$(awk '
    /^(## |### ).*Pseudocode/ { in_section=1; next }
    in_section && /^```/ {
        if (in_block) {
            exit
        } else {
            in_block=1
            next
        }
    }
    in_block { line_count++ }
    END { print line_count+0 }
' "$SPEC_FILE")

if [[ "$pseudocode_lines" -lt 10 ]]; then
    failure_msgs+=("PSEUDOCODE TOO SHORT: found ${pseudocode_lines} lines in first fenced block after Pseudocode heading (need >= 10)")
    ((failures++)) || true
fi

# ---------------------------------------------------------------------------
# Check 6: Inputs section contains a markdown table
# ---------------------------------------------------------------------------
# Look for a line starting with '|' between the "Inputs" heading and the next H2.
# Note: Inputs may have H3 sub-sections (Buffers, Objects, Alerts) — stop at H2 only.
inputs_table=$(awk '
    /^(## |### ).*Inputs/ { in_section=1; next }
    in_section && /^## / { exit }
    in_section && /^\|/ { found=1; exit }
    END { print found+0 }
' "$SPEC_FILE")

if [[ "$inputs_table" -lt 1 ]]; then
    failure_msgs+=("MISSING: Inputs section must contain a markdown table (line starting with '|')")
    ((failures++)) || true
fi

# ---------------------------------------------------------------------------
# Check 7: Test cases section has >= 2 entries
# ---------------------------------------------------------------------------
# Count lines matching ^[0-9]+. (numbered) OR ^[*-]  (bulleted) between
# "Test cases" heading and next H2 (stop at H2 only — test cases may have H3 sub-structure).
test_count=$(awk '
    /^(## |### ).*Test cases/ { in_section=1; next }
    in_section && /^## / { exit }
    in_section && (/^[0-9]+\./ || /^[*-] /) { count++ }
    END { print count+0 }
' "$SPEC_FILE")

if [[ "$test_count" -lt 2 ]]; then
    failure_msgs+=("INSUFFICIENT TEST CASES: found ${test_count} (need >= 2 numbered or bulleted entries in Test cases section)")
    ((failures++)) || true
fi

# ---------------------------------------------------------------------------
# Check 8: Port notes mentions MQ4 AND MQ5 AND Python
# ---------------------------------------------------------------------------
# Extract lines between "Port notes" heading and next H2 (## only — NOT ###,
# because Port notes itself has H3 sub-headings for MQ4/MQ5/Python paragraphs).
port_notes_body=$(awk '
    /^(## |### ).*Port notes/ { in_section=1; next }
    in_section && /^## / { exit }
    in_section { print }
' "$SPEC_FILE")

for token in "MQ4" "MQ5" "Python"; do
    if ! echo "$port_notes_body" | grep -q "$token" 2>/dev/null; then
        failure_msgs+=("PORT NOTES MISSING: ${token}")
        ((failures++)) || true
    fi
done

# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------
if [[ "$failures" -eq 0 ]]; then
    echo "PASS: $SPEC_FILE"
    exit 0
else
    echo "FAIL: $SPEC_FILE (${failures} issues)"
    for msg in "${failure_msgs[@]}"; do
        echo "  - ${msg}"
    done
    exit 1
fi
