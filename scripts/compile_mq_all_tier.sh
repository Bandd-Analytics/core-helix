#!/usr/bin/env bash
# scripts/compile_mq_all_tier.sh — Phase 12 Plan 01 (D-08/D-09)
#
# Tier-batch compile wrapper around scripts/compile_mq.sh.
#
# Usage: scripts/compile_mq_all_tier.sh <tier-name>
#   tier-name = tier0 | tier1 | tier2
#
# tier0 → MQ4 + MQ5 helpers (sm_gmtoffset, sm_WorkTime, sm_WorkTime_no_autogmt)
# tier1 → 5 atomic indicators (SM_ADR_Marker, SM_Daily_HiLo, SM_BPCT,
#         SM_IlsleyPsychLevels, SM_Crossover_Arrows)
# tier2 → 6 composite indicators (SM_TDI, SM_PivotPoints, SM_AlertZone_1,
#         SM_AlertZone_2, SM_Alerting+TL, SM_NewHUD)
#
# Aggregate exit code: 0 only if every file passes (or compile_mq.sh
# advisory-skips them on Linux per D-08).

set -uo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <tier0|tier1|tier2>" >&2
    exit 2
fi

TIER="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPILE="$SCRIPT_DIR/compile_mq.sh"

if [[ ! -x "$COMPILE" ]]; then
    echo "ERROR: $COMPILE not executable" >&2
    exit 2
fi

MT4_DIR="$REPO_ROOT/resource_pack/MMM/SM Indicators/MT4/_helix_built"
MT5_DIR="$REPO_ROOT/resource_pack/MMM/SM Indicators/MT5"

declare -a FILES=()
case "$TIER" in
    tier0)
        for n in sm_gmtoffset sm_WorkTime sm_WorkTime_no_autogmt; do
            FILES+=("$MT5_DIR/helpers/${n}.mq5")
            FILES+=("$MT4_DIR/helpers/${n}.mq4")
        done
        ;;
    tier1)
        for n in SM_ADR_Marker SM_Daily_HiLo SM_BPCT SM_IlsleyPsychLevels SM_Crossover_Arrows; do
            FILES+=("$MT5_DIR/indicators/${n}.mq5")
            FILES+=("$MT4_DIR/indicators/${n}.mq4")
        done
        ;;
    tier2)
        for n in SM_TDI SM_PivotPoints SM_AlertZone_1 SM_AlertZone_2 "SM_Alerting+TL" SM_NewHUD; do
            FILES+=("$MT5_DIR/indicators/${n}.mq5")
            FILES+=("$MT4_DIR/indicators/${n}.mq4")
        done
        ;;
    *)
        echo "ERROR: unknown tier '$TIER' (expected tier0|tier1|tier2)" >&2
        exit 2
        ;;
esac

OK=0
FAIL=0
SKIP=0
for f in "${FILES[@]}"; do
    if [[ ! -f "$f" ]]; then
        echo "SKIP: missing source $f"
        SKIP=$((SKIP+1))
        continue
    fi
    echo ""
    echo "=== compile: $f ==="
    if "$COMPILE" "$f"; then
        OK=$((OK+1))
    else
        FAIL=$((FAIL+1))
    fi
done

echo ""
echo "=== Tier $TIER batch summary ==="
echo "OK:    $OK"
echo "FAIL:  $FAIL"
echo "SKIP:  $SKIP"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
