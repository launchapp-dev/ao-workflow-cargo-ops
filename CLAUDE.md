# Air Cargo Operations Manager — Agent Context

This repo implements a multi-agent air cargo operations pipeline using AO. It processes
cargo bookings through dangerous goods classification, weight/balance, and compliance
validation to produce departure-ready documentation for freight flights.

## Domain Context

You are working within an **aviation cargo operations** domain. The key regulatory
frameworks are:

- **IATA DGR** (Dangerous Goods Regulations) — governs all DG on air transport
- **ICAO Technical Instructions** — international DG air transport law
- **Aircraft Weight & Balance** — FAA/EASA regulations on loading within CG envelope
- **MTOW/MZFW** — structural certification limits that MUST NOT be exceeded

**Safety is paramount.** Errors in DG classification or weight/balance can cause
aircraft accidents. All decisions must be justified with specific data and values.

## Data Files

All runtime data lives in `data/`:
- `booking-request.json` — incoming booking (the starting point)
- `validated-booking.json` — enriched booking with volumetric weights and SHC codes
- `aircraft-specs.json` — B777-200F specs: compartments, limits, CG envelope
- `iata-dgr-reference.json` — DGR classification lookup (UN numbers, limits, segregation)
- `dg-classification.json` — output of DG classifier (created at runtime)
- `load-plan.json` — output of load planner (created at runtime)
- `weight-balance-result.json` — output of python3 calculation script
- `compliance-result.json` — output of compliance checker
- `rejection-log.json` — created if cargo is rejected

## Output Documents

Generated to `documents/` and `reports/`:
- `cargo-manifest.md` — regulatory departure manifest (piece list, totals)
- `dg-declaration.md` — Shipper's Declaration for Dangerous Goods (IATA format)
- `notoc.md` — Notification to Captain (mandatory for DG/special cargo)
- `reports/ops-dashboard.md` — operations dashboard with utilization metrics

## ULD Position Reference (B777-200F)

Main Deck (PMC pallets, max 6,804 kg each):
```
[ML1][MC1][MC2][MC3][MC4][MC5][ML3]  ← Left side
[MR1]                          [MR3]  ← Right side
     [ML2]              [ML3]         ← Center positions
```

Lower Deck:
- Forward (LF1-LF4): LD3 containers, max 1,588 kg each
- Aft (LA1-LA5): LD3 containers, max 1,588 kg each
- Bulk (BLK): loose cargo, max 2,000 kg total

## Datum Arms (meters from nose datum)
For CG moment calculations:
- ML1/MR1: 21.0m | ML2/MR2: 23.5m | ML3/MR3: 26.0m
- MC1: 28.5m | MC2: 31.0m | MC3: 33.5m | MC4: 36.0m | MC5: 38.5m
- LF1: 15.0m | LF2: 17.5m | LF3: 20.0m | LF4: 22.5m
- LA1: 35.0m | LA2: 37.5m | LA3: 40.0m | LA4: 42.5m | LA5: 45.0m
- BLK: 48.0m
- MAC datum: 21.0m | MAC length: 9.0m
- CG envelope: 14–33% MAC

## DG Segregation Rules
From `data/iata-dgr-reference.json`:
- Class 3 (flammable) + Class 5.1 (oxidizer) = **FORBIDDEN**
- Class 3 + Class 9 (lithium) = allowed with 1m separation
- Class 9 + Class 9 = unrestricted

## Scripts

`scripts/weight-balance.py`:
- Input: `data/load-plan.json`, `data/aircraft-specs.json`
- Output: `data/weight-balance-result.json`
- Run: `python3 scripts/weight-balance.py`
- Requires: load-plan.json to have `positions` array with `{position, weight_kg}` objects

`scripts/capacity-check.sh`:
- Input: `data/aircraft-specs.json`, `data/load-plan.json`
- Run: `bash scripts/capacity-check.sh`
- Requires: `jq` installed
- Reads `volume_used_m3` object from load-plan.json

## Decision Logic

### classify-dg
- **advance** — all DG classified, acceptable for air transport
- **rework** — missing UN number or MSDS data; shipper must provide
- **fail** — forbidden DG (e.g., forbidden explosives, Class 7 over limits)

### calculate-load-plan
- **advance** — load plan within CG envelope, no segregation conflicts
- **rework** — DG segregation conflict that requires re-classification

### validate-compliance
- **advance** — all structural and regulatory limits satisfied, CLEARED
- **rework** — within limits but >90% utilized; recommend rebalancing
- **fail** — any hard limit exceeded (MTOW, MZFW, ULD weight, volume)

## Handling Codes Reference
See `config/handling-codes.json` for full SHC definitions and documentation requirements.
