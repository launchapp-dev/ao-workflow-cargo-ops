# Air Cargo Operations Manager — Build Plan

## Overview

An air cargo operations pipeline that automates the full lifecycle of cargo processing: intake shipment bookings from JSON manifests, classify dangerous goods against IATA DGR categories, calculate load plans with weight/balance constraints, generate cargo manifests with piece counts and dimensions, validate against aircraft payload and volume limits, flag overweight or hazardous cargo for special handling, produce departure-ready documentation packages (manifest, DG declaration, NOTOC), track shipment status through transit points, and generate operations dashboards with utilization metrics.

This example demonstrates AO as a multi-agent orchestration engine for aviation cargo operations — a domain with strict regulatory compliance (IATA DGR, ICAO), safety-critical decision routing, and complex weight/balance calculations.

## Agents

| Agent | Model | Role |
|---|---|---|
| **booking-processor** | claude-haiku-4-5 | Receives and validates cargo booking requests — checks shipper info, piece count, dimensions, weight, commodity codes, special handling requirements |
| **dg-classifier** | claude-sonnet-4-6 | Classifies cargo against IATA Dangerous Goods Regulations — identifies UN numbers, packing groups, labels, quantity limits, compatibility groups, determines if cargo is forbidden/restricted/acceptable |
| **load-planner** | claude-sonnet-4-6 | Calculates optimal cargo positions using weight and balance constraints — considers CG envelope, max floor loading, compartment volume limits, stacking rules |
| **manifest-generator** | claude-haiku-4-5 | Generates cargo manifests, DG declarations (Shipper's Declaration for Dangerous Goods), and NOTOC (Notification to Captain) documents |
| **compliance-checker** | claude-sonnet-4-6 | Final validation — checks total payload vs aircraft MTOW, volume vs compartment capacity, DG segregation rules, special cargo compatibility, ULD weight limits |
| **ops-dashboard** | claude-haiku-4-5 | Generates operations dashboard with load factor, utilization metrics, DG summary, revenue/weight analysis, departure readiness status |

## Phase Pipeline

```
1. process-booking       (booking-processor)    → validate and enrich booking data
2. classify-dg           (dg-classifier)        → dangerous goods classification
   └─ on "rework" → back to process-booking (missing MSDS/commodity data)
   └─ on "fail" → reject-cargo (forbidden goods)
3. calculate-load-plan   (load-planner)         → weight/balance and position assignment
   └─ on "rework" → back to classify-dg (DG segregation conflict needs re-class)
4. validate-compliance   (compliance-checker)    → final aircraft limit checks
   └─ on "rework" → back to calculate-load-plan (marginal load, needs rebalancing)
   └─ on "fail" → reject-cargo (exceeds aircraft limits)
5. generate-manifest     (manifest-generator)   → produce departure documentation
6. generate-dashboard    (ops-dashboard)        → produce operations dashboard and metrics
7. reject-cargo          (command phase)        → log rejection with reason code
```

## Decision Contracts

### classify-dg
- **advance** → proceed to load planning (cargo classified, acceptable for air transport)
- **rework** → back to process-booking (missing material safety data, shipper must provide UN number or proper shipping name)
- **fail** → reject-cargo (forbidden dangerous goods — no air transport permitted)

Required fields: `verdict`, `reasoning`, `dg_class` (null if non-DG), `un_number` (null if non-DG), `packing_group`, `restrictions`

### calculate-load-plan
- **advance** → proceed to compliance check (load plan within CG envelope and floor limits)
- **rework** → back to classify-dg (DG segregation conflict requires re-classification or offload of incompatible item)

Required fields: `verdict`, `reasoning`, `total_weight_kg`, `cg_position`, `within_envelope`

### validate-compliance
- **advance** → proceed to manifest generation (all checks passed)
- **rework** → back to calculate-load-plan (marginal — within limits but load rebalancing recommended)
- **fail** → reject-cargo (exceeds MTOW, volume, or ULD weight limits)

Required fields: `verdict`, `reasoning`, `payload_pct`, `volume_pct`, `limiting_factor`

## MCP Servers

- **filesystem** — read/write all data files (bookings, classifications, load plans, manifests, dashboards)
- **sequential-thinking** — structured reasoning for DG classification and weight/balance calculations

## Data Files

| File | Purpose | Written By | Read By |
|---|---|---|---|
| `data/booking-request.json` | Incoming cargo booking (shipper, pieces, dims, weight, commodity) | Human/external | booking-processor |
| `data/validated-booking.json` | Validated booking with enriched commodity codes | booking-processor | dg-classifier, load-planner |
| `data/aircraft-specs.json` | Aircraft type specs: MTOW, OEW, compartments, CG limits, ULD positions | Seed data | load-planner, compliance-checker |
| `data/iata-dgr-reference.json` | IATA DGR classification table (common UN numbers, classes, limits) | Seed data | dg-classifier |
| `data/dg-classification.json` | DG classification result (class, UN number, packing group, labels) | dg-classifier | load-planner, manifest-generator, compliance-checker |
| `data/load-plan.json` | Cargo position assignments, weight distribution, CG calculation | load-planner | compliance-checker, manifest-generator |
| `data/compliance-result.json` | Final compliance check results (pass/fail per constraint) | compliance-checker | manifest-generator |
| `documents/cargo-manifest.md` | Departure cargo manifest with piece list and totals | manifest-generator | — |
| `documents/dg-declaration.md` | Shipper's Declaration for Dangerous Goods (IATA format) | manifest-generator | — |
| `documents/notoc.md` | NOTOC — Notification to Captain for DG/special cargo | manifest-generator | — |
| `reports/ops-dashboard.md` | Operations dashboard: load factor, utilization, DG summary | ops-dashboard | — |
| `data/rejection-log.json` | Cargo rejection log with reason codes | reject-cargo phase | — |

## Sample Data

### data/booking-request.json
```json
{
  "booking_id": "CG-2026-0331-001",
  "flight": "AO-7742",
  "aircraft_type": "B777-200F",
  "route": "JFK → FRA",
  "departure": "2026-04-01T08:30Z",
  "shipper": {
    "name": "Precision Electronics Corp",
    "iata_code": "PEC",
    "account": "PEC-4421"
  },
  "consignments": [
    {
      "awb": "125-44782910",
      "pieces": 12,
      "description": "Lithium-ion batteries (packed with equipment)",
      "commodity_code": "850760",
      "gross_weight_kg": 840,
      "dimensions_cm": {"l": 120, "w": 80, "h": 60},
      "special_handling": ["ELI", "CAO"],
      "declared_value_usd": 125000
    },
    {
      "awb": "125-44782911",
      "pieces": 48,
      "description": "Consumer electronics (smartphones)",
      "commodity_code": "851712",
      "gross_weight_kg": 2160,
      "dimensions_cm": {"l": 60, "w": 40, "h": 40},
      "special_handling": [],
      "declared_value_usd": 890000
    },
    {
      "awb": "125-44782912",
      "pieces": 6,
      "description": "Perfume samples containing ethanol",
      "commodity_code": "330300",
      "gross_weight_kg": 180,
      "dimensions_cm": {"l": 60, "w": 40, "h": 30},
      "special_handling": ["RFL"],
      "declared_value_usd": 15000
    },
    {
      "awb": "125-44782913",
      "pieces": 24,
      "description": "Automotive spare parts (non-hazardous)",
      "commodity_code": "870899",
      "gross_weight_kg": 3600,
      "dimensions_cm": {"l": 100, "w": 80, "h": 80},
      "special_handling": ["HEA"],
      "declared_value_usd": 67000
    }
  ],
  "total_pieces": 90,
  "total_gross_weight_kg": 6780,
  "priority": "general"
}
```

### data/aircraft-specs.json
```json
{
  "aircraft_type": "B777-200F",
  "registration": "N-AO777",
  "mtow_kg": 347452,
  "oew_kg": 144400,
  "max_payload_kg": 102010,
  "max_fuel_kg": 145540,
  "max_structural_payload_kg": 102010,
  "compartments": {
    "main_deck": {
      "positions": ["ML1", "ML2", "ML3", "MR1", "MR2", "MR3", "MC1", "MC2", "MC3", "MC4", "MC5"],
      "uld_type": "PMC",
      "max_uld_weight_kg": 6804,
      "total_volume_m3": 386,
      "max_floor_load_kg_m2": 1220
    },
    "lower_forward": {
      "positions": ["LF1", "LF2", "LF3", "LF4"],
      "uld_type": "LD3",
      "max_uld_weight_kg": 1588,
      "total_volume_m3": 42,
      "max_floor_load_kg_m2": 732
    },
    "lower_aft": {
      "positions": ["LA1", "LA2", "LA3", "LA4", "LA5"],
      "uld_type": "LD3",
      "max_uld_weight_kg": 1588,
      "total_volume_m3": 53,
      "max_floor_load_kg_m2": 732
    },
    "bulk": {
      "positions": ["BLK"],
      "uld_type": "loose",
      "max_weight_kg": 2000,
      "total_volume_m3": 14
    }
  },
  "cg_limits": {
    "forward_limit_pct_mac": 14.0,
    "aft_limit_pct_mac": 33.0,
    "optimal_cg_pct_mac": 25.0
  },
  "fuel_burn_estimate_kg_hr": 7800,
  "flight_time_hr": 7.5
}
```

### data/iata-dgr-reference.json (excerpt)
```json
{
  "classifications": [
    {
      "un_number": "UN3481",
      "proper_shipping_name": "Lithium ion batteries packed with equipment",
      "class": "9",
      "subsidiary_risk": null,
      "packing_group": "II",
      "labels": ["Class 9", "Lithium Battery"],
      "passenger_limit_kg": 5,
      "cargo_limit_kg": 35,
      "special_provisions": ["A99", "A154", "A164"],
      "packing_instructions": {"cargo": "PI 966 Section II", "passenger": "PI 967 Section II"},
      "forbidden_passenger": false,
      "forbidden_cargo": false
    },
    {
      "un_number": "UN1197",
      "proper_shipping_name": "Extracts, flavouring, liquid (ethanol-based)",
      "class": "3",
      "subsidiary_risk": null,
      "packing_group": "III",
      "labels": ["Flammable Liquid"],
      "passenger_limit_kg": 60,
      "cargo_limit_kg": 220,
      "special_provisions": [],
      "packing_instructions": {"cargo": "PI 309", "passenger": "PI 305"},
      "forbidden_passenger": false,
      "forbidden_cargo": false
    }
  ],
  "segregation_rules": [
    {"class_a": "3", "class_b": "5.1", "rule": "forbidden"},
    {"class_a": "3", "class_b": "9", "rule": "allowed_with_separation"},
    {"class_a": "9", "class_b": "9", "rule": "allowed"}
  ]
}
```

## Scripts

### scripts/weight-balance.py
Python script for weight/balance calculations:
- Input: `data/load-plan.json`, `data/aircraft-specs.json`
- Calculates total cargo weight, fuel load, zero-fuel weight, takeoff weight
- Computes CG position as % MAC
- Validates against forward/aft CG limits
- Output: `data/weight-balance-result.json`

### scripts/capacity-check.sh
Bash script using jq for quick capacity validation:
- Reads aircraft specs and current load plan
- Checks payload vs max structural payload
- Checks compartment volume utilization
- Outputs pass/fail with percentages

## Schedules

| Schedule | Cron | Purpose |
|---|---|---|
| daily-load-planning | `0 4 * * *` | Process all pending bookings for today's departures |
| weekly-capacity-analysis | `0 8 * * 1` | Generate weekly fleet utilization and capacity report |

## README Outline

1. **What This Does** — overview of air cargo operations automation
2. **Quick Start** — ao daemon start, submit a booking
3. **Workflow Pipeline** — visual flow with decision points
4. **Agent Roles** — who does what
5. **Data Files** — input/output file reference
6. **Customization** — adding aircraft types, updating DGR tables, adjusting scoring weights
7. **Domain Reference** — air cargo terminology (AWB, NOTOC, ULD, MAC, MTOW, etc.)

## Directory Structure

```
examples/cargo-ops/
├── .ao/workflows/
│   ├── agents.yaml
│   ├── phases.yaml
│   ├── workflows.yaml
│   ├── mcp-servers.yaml
│   └── schedules.yaml
├── CLAUDE.md
├── README.md
├── PLAN.md
├── data/
│   ├── booking-request.json
│   ├── aircraft-specs.json
│   └── iata-dgr-reference.json
├── documents/          (generated output)
├── reports/            (generated dashboards)
├── scripts/
│   ├── weight-balance.py
│   └── capacity-check.sh
└── config/
    └── handling-codes.json
```

## Key Domain Concepts

- **AWB** — Air Waybill: the contract of carriage for air cargo
- **NOTOC** — Notification to Captain: mandatory document listing all DG/special cargo onboard
- **ULD** — Unit Load Device: standardized container/pallet (PMC, LD3, LD7, etc.)
- **MAC** — Mean Aerodynamic Chord: reference for CG position calculations
- **MTOW** — Maximum Takeoff Weight: regulatory limit for the aircraft
- **OEW** — Operating Empty Weight: aircraft weight without payload or fuel
- **ZFW** — Zero Fuel Weight: OEW + payload (no fuel)
- **CG** — Center of Gravity: must stay within certified envelope for safe flight
- **IATA DGR** — International Air Transport Association Dangerous Goods Regulations
- **ICAO TI** — ICAO Technical Instructions for Safe Transport of Dangerous Goods by Air
- **Packing Group** — I (great danger), II (medium), III (minor) — affects quantity limits
- **SHC** — Special Handling Code: ELI (lithium), RFL (flammable liquid), CAO (cargo aircraft only), HEA (heavy cargo), etc.
- **PI** — Packing Instruction: specific IATA packing requirements per DG item
