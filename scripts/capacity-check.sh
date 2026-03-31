#!/usr/bin/env bash
# Cargo Capacity Check
# Reads: data/aircraft-specs.json, data/load-plan.json
# Outputs: pass/fail with utilization percentages to stdout

set -euo pipefail

SPECS="data/aircraft-specs.json"
LOAD_PLAN="data/load-plan.json"

if ! command -v jq &>/dev/null; then
  echo "ERROR: jq is required but not installed" >&2
  exit 1
fi

if [[ ! -f "$SPECS" ]]; then
  echo "ERROR: $SPECS not found" >&2
  exit 1
fi

if [[ ! -f "$LOAD_PLAN" ]]; then
  echo "ERROR: $LOAD_PLAN not found — run load planning first" >&2
  exit 1
fi

echo "=== Cargo Capacity Check ==="
echo ""

# Extract aircraft limits from specs
MAX_PAYLOAD=$(jq -r '.max_structural_payload_kg' "$SPECS")
MAIN_DECK_MAX_VOL=$(jq -r '.compartments.main_deck.total_volume_m3' "$SPECS")
LOWER_FWD_MAX_VOL=$(jq -r '.compartments.lower_forward.total_volume_m3' "$SPECS")
LOWER_AFT_MAX_VOL=$(jq -r '.compartments.lower_aft.total_volume_m3' "$SPECS")
BULK_MAX_VOL=$(jq -r '.compartments.bulk.total_volume_m3' "$SPECS")

# Extract load plan values (with defaults if keys missing)
TOTAL_PAYLOAD=$(jq -r '.total_cargo_weight_kg // 0' "$LOAD_PLAN")
MAIN_DECK_VOL=$(jq -r '.volume_used_m3.main_deck // 0' "$LOAD_PLAN")
LOWER_FWD_VOL=$(jq -r '.volume_used_m3.lower_forward // 0' "$LOAD_PLAN")
LOWER_AFT_VOL=$(jq -r '.volume_used_m3.lower_aft // 0' "$LOAD_PLAN")
BULK_VOL=$(jq -r '.volume_used_m3.bulk // 0' "$LOAD_PLAN")

# Calculate utilization percentages using awk
calc_pct() {
  awk "BEGIN { printf \"%.1f\", ($1 / $2) * 100 }"
}

PAYLOAD_PCT=$(calc_pct "$TOTAL_PAYLOAD" "$MAX_PAYLOAD")
MAIN_DECK_PCT=$(calc_pct "$MAIN_DECK_VOL" "$MAIN_DECK_MAX_VOL")
LOWER_FWD_PCT=$(calc_pct "$LOWER_FWD_VOL" "$LOWER_FWD_MAX_VOL")
LOWER_AFT_PCT=$(calc_pct "$LOWER_AFT_VOL" "$LOWER_AFT_MAX_VOL")
BULK_PCT=$(calc_pct "$BULK_VOL" "$BULK_MAX_VOL")

# Determine pass/fail (threshold: 100%)
check_limit() {
  local pct="$1"
  local label="$2"
  local result
  result=$(awk "BEGIN { print ($pct > 100) ? \"FAIL\" : \"PASS\" }")
  printf "%-35s %7s kg / %7s kg  (%5s%%)  [%s]\n" \
    "$label" "$(printf '%.0f' "$3")" "$(printf '%.0f' "$4")" "$pct" "$result"
  echo "$result"
}

OVERALL="PASS"

echo "Metric                              Used        Limit       Util   Status"
echo "-------------------------------------------------------------------------------"

# Payload
RESULT=$(check_limit "$PAYLOAD_PCT" "Total Payload" "$TOTAL_PAYLOAD" "$MAX_PAYLOAD")
[[ "$RESULT" == "FAIL" ]] && OVERALL="FAIL"

# Volumes
vol_check() {
  local used="$1" max="$2" label="$3"
  local pct
  pct=$(calc_pct "$used" "$max")
  local result
  result=$(awk "BEGIN { print ($pct > 100) ? \"FAIL\" : \"PASS\" }")
  printf "%-35s %7s m³ / %7s m³  (%5s%%)  [%s]\n" "$label" "$used" "$max" "$pct" "$result"
  echo "$result"
}

RESULT=$(vol_check "$MAIN_DECK_VOL" "$MAIN_DECK_MAX_VOL" "Main Deck Volume")
[[ "$RESULT" == "FAIL" ]] && OVERALL="FAIL"

RESULT=$(vol_check "$LOWER_FWD_VOL" "$LOWER_FWD_MAX_VOL" "Lower Forward Volume")
[[ "$RESULT" == "FAIL" ]] && OVERALL="FAIL"

RESULT=$(vol_check "$LOWER_AFT_VOL" "$LOWER_AFT_MAX_VOL" "Lower Aft Volume")
[[ "$RESULT" == "FAIL" ]] && OVERALL="FAIL"

RESULT=$(vol_check "$BULK_VOL" "$BULK_MAX_VOL" "Bulk Volume")
[[ "$RESULT" == "FAIL" ]] && OVERALL="FAIL"

echo "-------------------------------------------------------------------------------"
echo ""
if [[ "$OVERALL" == "PASS" ]]; then
  echo "CAPACITY CHECK: PASS — All limits within bounds"
  exit 0
else
  echo "CAPACITY CHECK: FAIL — One or more limits exceeded"
  exit 1
fi
