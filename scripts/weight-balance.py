#!/usr/bin/env python3
"""
Weight & Balance Calculator for Air Cargo Operations
Reads: data/load-plan.json, data/aircraft-specs.json
Writes: data/weight-balance-result.json
"""

import json
import sys
from datetime import datetime, timezone

def load_json(path):
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def calculate_cg(positions, datum_arms):
    """Calculate CG from a list of {position, weight_kg} items and arm reference."""
    total_weight = 0
    total_moment = 0
    position_details = []

    for item in positions:
        pos = item.get('position')
        weight = item.get('weight_kg', 0)
        arm = datum_arms.get(pos, 0)
        moment = weight * arm
        total_weight += weight
        total_moment += moment
        position_details.append({
            'position': pos,
            'weight_kg': weight,
            'arm_m': arm,
            'moment_kg_m': round(moment, 1)
        })

    if total_weight == 0:
        return 0, 0, position_details

    cg_index = total_moment / total_weight
    return total_weight, cg_index, position_details

def main():
    print("=== Weight & Balance Calculator ===\n")

    # Load input files
    try:
        specs = load_json('data/aircraft-specs.json')
    except FileNotFoundError:
        print("ERROR: data/aircraft-specs.json not found", file=sys.stderr)
        sys.exit(1)

    try:
        load_plan = load_json('data/load-plan.json')
    except FileNotFoundError:
        print("ERROR: data/load-plan.json not found. Run load planning first.", file=sys.stderr)
        sys.exit(1)

    # Build flat datum arms map
    datum_arms = {}
    for compartment_name, compartment in specs['compartments'].items():
        datum_arms.update(compartment.get('datum_arms_m', {}))

    # Extract all loaded positions from load plan
    loaded_positions = load_plan.get('positions', [])

    # Calculate cargo CG
    total_cargo_weight, cargo_cg_index, position_details = calculate_cg(loaded_positions, datum_arms)

    # Aircraft weights
    oew = specs['oew_kg']
    planned_fuel = specs.get('planned_fuel_kg', 58500)
    crew_equipment = specs.get('crew_and_equipment_kg', 800)

    # OEW CG assumption (typical for B777-200F)
    oew_arm = 28.0  # meters from nose datum
    oew_moment = oew * oew_arm

    # Fuel CG (fuel in wing tanks, arm ~28m)
    fuel_arm = 28.0
    fuel_moment = planned_fuel * fuel_arm

    # Calculate ZFW
    zfw = oew + total_cargo_weight + crew_equipment
    zfw_moment = oew_moment + (total_cargo_weight * (cargo_cg_index if cargo_cg_index > 0 else oew_arm)) + (crew_equipment * 26.0)
    zfw_cg = zfw_moment / zfw if zfw > 0 else oew_arm

    # Calculate TOW
    tow = zfw + planned_fuel
    tow_moment = zfw_moment + fuel_moment
    tow_cg = tow_moment / tow if tow > 0 else oew_arm

    # Convert CG to % MAC
    mac_datum = specs['cg_limits']['mac_datum_m']
    mac_length = specs['cg_limits']['mac_length_m']
    fwd_limit = specs['cg_limits']['forward_limit_pct_mac']
    aft_limit = specs['cg_limits']['aft_limit_pct_mac']

    def to_pct_mac(cg_m):
        return round(((cg_m - mac_datum) / mac_length) * 100, 1)

    zfw_cg_pct = to_pct_mac(zfw_cg)
    tow_cg_pct = to_pct_mac(tow_cg)

    # Limits check
    mtow = specs['mtow_kg']
    max_payload = specs['max_structural_payload_kg']
    mzfw = specs.get('max_zero_fuel_weight_kg', oew + max_payload)

    payload_pct = round((total_cargo_weight / max_payload) * 100, 1)
    zfw_pct = round((zfw / mzfw) * 100, 1)
    tow_pct = round((tow / mtow) * 100, 1)

    cg_within_limits = fwd_limit <= tow_cg_pct <= aft_limit
    payload_ok = total_cargo_weight <= max_payload
    zfw_ok = zfw <= mzfw
    tow_ok = tow <= mtow

    all_ok = cg_within_limits and payload_ok and zfw_ok and tow_ok
    status = "CLEARED" if all_ok else "EXCEEDS_LIMITS"

    result = {
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "aircraft_type": specs['aircraft_type'],
        "weights": {
            "oew_kg": oew,
            "cargo_payload_kg": total_cargo_weight,
            "crew_equipment_kg": crew_equipment,
            "zfw_kg": zfw,
            "planned_fuel_kg": planned_fuel,
            "tow_kg": tow
        },
        "limits": {
            "max_payload_kg": max_payload,
            "max_zfw_kg": mzfw,
            "mtow_kg": mtow
        },
        "utilization": {
            "payload_pct": payload_pct,
            "zfw_pct_of_mzfw": zfw_pct,
            "tow_pct_of_mtow": tow_pct
        },
        "weight_and_balance": {
            "zfw_cg_m": round(zfw_cg, 2),
            "zfw_cg_pct_mac": zfw_cg_pct,
            "tow_cg_m": round(tow_cg, 2),
            "tow_cg_pct_mac": tow_cg_pct,
            "forward_limit_pct_mac": fwd_limit,
            "aft_limit_pct_mac": aft_limit,
            "within_envelope": cg_within_limits
        },
        "checks": {
            "payload_ok": payload_ok,
            "zfw_ok": zfw_ok,
            "tow_ok": tow_ok,
            "cg_within_limits": cg_within_limits
        },
        "position_details": position_details
    }

    save_json('data/weight-balance-result.json', result)

    # Print summary
    print(f"Aircraft:        {specs['aircraft_type']} ({specs['registration']})")
    print(f"Cargo Payload:   {total_cargo_weight:,} kg ({payload_pct}% of max {max_payload:,} kg)")
    print(f"Zero Fuel Wt:    {zfw:,} kg ({zfw_pct}% of MZFW {mzfw:,} kg)")
    print(f"Takeoff Wt:      {tow:,} kg ({tow_pct}% of MTOW {mtow:,} kg)")
    print(f"TOW CG:          {tow_cg_pct}% MAC (limits: {fwd_limit}%–{aft_limit}%)")
    print()
    print(f"Status:          {'✓ CLEARED' if all_ok else '✗ EXCEEDS LIMITS'}")
    if not cg_within_limits:
        print(f"  WARNING: CG {tow_cg_pct}% MAC is outside {fwd_limit}%–{aft_limit}% envelope!")
    if not payload_ok:
        print(f"  WARNING: Payload {total_cargo_weight:,} kg exceeds max {max_payload:,} kg!")
    if not tow_ok:
        print(f"  WARNING: TOW {tow:,} kg exceeds MTOW {mtow:,} kg!")
    print()
    print("Results saved to data/weight-balance-result.json")

if __name__ == '__main__':
    main()
