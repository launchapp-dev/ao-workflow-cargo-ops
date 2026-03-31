# Air Cargo Operations Manager

Multi-agent pipeline automating the full air cargo lifecycle — from booking intake through departure documentation — with IATA DGR dangerous goods classification, weight/balance calculations, and regulatory compliance validation.

## Workflow Diagram

```
Booking Request (JSON)
        |
        v
┌─────────────────────┐
│  process-booking    │  booking-processor (haiku)
│  Validate & enrich  │  ← checks dims, weights, SHC codes
│  booking data       │
└──────────┬──────────┘
           |
           v
┌─────────────────────┐                    ┌──────────────────┐
│    classify-dg      │  dg-classifier     │  reject-cargo    │
│  IATA DGR lookup,   │──── fail ─────────>│  Log rejection   │
│  UN numbers,        │                    │  with reason     │
│  packing groups     │                    └──────────────────┘
└──────────┬──────────┘
      rework|advance
      ↑     |
      |     v
┌─────────────────────┐
│ calculate-load-plan │  load-planner (sonnet)
│  ULD assignment,    │──── rework ──> classify-dg
│  CG moments,        │
│  segregation check  │
└──────────┬──────────┘
           |advance
           v
┌─────────────────────┐
│ run-weight-balance  │  (command: python3)
│  ZFW, TOW, CG%MAC  │
│  limits validation  │
└──────────┬──────────┘
           |
           v
┌─────────────────────┐                    ┌──────────────────┐
│ validate-compliance │  compliance-checker│  reject-cargo    │
│  Payload, volume,   │──── fail ─────────>│  (command phase) │
│  ULD weights, CG    │                    └──────────────────┘
│  envelope checks    │
└──────────┬──────────┘
      rework|advance
      ↑     |
      |     v
┌─────────────────────┐
│ generate-manifest   │  manifest-generator (haiku)
│  Cargo manifest,    │
│  DG declaration,    │
│  NOTOC for captain  │
└──────────┬──────────┘
           |
           v
┌─────────────────────┐
│ generate-dashboard  │  ops-dashboard (haiku)
│  Load factor,       │
│  utilization,       │
│  DG summary,        │
│  departure readiness│
└─────────────────────┘
        |
        v
   reports/ops-dashboard.md  ✓ GO
```

## Quick Start

```bash
cd examples/cargo-ops
ao daemon start

# Submit a booking for processing
ao queue enqueue \
  --title "cargo-ops" \
  --description "Process booking CG-2026-0331-001: JFK→FRA, 6,780kg electronics + DG" \
  --workflow-ref process-cargo-booking

# Watch it run
ao daemon stream --pretty

# View generated documents
cat documents/cargo-manifest.md
cat documents/notoc.md
cat reports/ops-dashboard.md
```

## Agents

| Agent | Model | Role |
|---|---|---|
| **booking-processor** | claude-haiku-4-5 | Validates incoming bookings, calculates volumetric weights, assigns SHC codes |
| **dg-classifier** | claude-sonnet-4-6 | IATA DGR classification — UN numbers, packing groups, quantity limits, segregation rules |
| **load-planner** | claude-sonnet-4-6 | Assigns cargo to ULD positions, calculates CG moments, checks segregation conflicts |
| **compliance-checker** | claude-sonnet-4-6 | Final validation against MTOW, MZFW, volume limits, ULD weights, CG envelope |
| **manifest-generator** | claude-haiku-4-5 | Produces cargo manifest, DG declaration (IATA format), NOTOC for captain |
| **ops-dashboard** | claude-haiku-4-5 | Operations dashboard with load factor, DG summary, revenue metrics, departure status |

## AO Features Demonstrated

| Feature | Where Used |
|---|---|
| **Multi-agent pipeline** | 6 specialized agents, each handling one domain layer |
| **Decision contracts** | `classify-dg`, `calculate-load-plan`, `validate-compliance` with required fields |
| **Phase routing with rework** | DG rework → booking, load rework → DG, compliance rework → load |
| **Fail routing** | Forbidden DG or limit exceeded → `reject-cargo` command phase |
| **Command phases** | `python3 scripts/weight-balance.py`, `bash scripts/capacity-check.sh` |
| **Scheduled workflows** | Daily 04:00 UTC load planning, weekly Monday capacity analysis |
| **Mixed models** | Haiku for fast document tasks, Sonnet for complex DG/load/compliance reasoning |
| **Sequential thinking MCP** | Structured reasoning for DG classification and CG calculations |
| **Output contracts** | Typed JSON outputs from each phase consumed by the next |
| **Post-success merge** | Auto-merge with squash on successful departure clearance |

## Data Flow

| File | Written By | Read By |
|---|---|---|
| `data/booking-request.json` | Human/external system | `process-booking` |
| `data/validated-booking.json` | `booking-processor` | `dg-classifier`, `load-planner` |
| `data/dg-classification.json` | `dg-classifier` | `load-planner`, `compliance-checker`, `manifest-generator` |
| `data/load-plan.json` | `load-planner` | `compliance-checker`, `manifest-generator`, `ops-dashboard` |
| `data/weight-balance-result.json` | `weight-balance.py` | `compliance-checker` |
| `data/compliance-result.json` | `compliance-checker` | `manifest-generator`, `ops-dashboard` |
| `documents/cargo-manifest.md` | `manifest-generator` | Operations team |
| `documents/dg-declaration.md` | `manifest-generator` | Operations team / Airline |
| `documents/notoc.md` | `manifest-generator` | Flight crew |
| `reports/ops-dashboard.md` | `ops-dashboard` | Operations managers |
| `data/rejection-log.json` | `reject-cargo` command | Shipper notification |

## Requirements

**MCP Servers:**
- `@modelcontextprotocol/server-filesystem` — read/write all data and document files
- `@modelcontextprotocol/server-sequential-thinking` — structured multi-step reasoning

**CLI Tools (built-in):**
- `python3` — weight/balance calculations (`scripts/weight-balance.py`)
- `bash` + `jq` — capacity check script (`scripts/capacity-check.sh`)

**No external API keys required** — all logic uses local files and MCP servers.

## Customization

**Adding a new aircraft type:**
Edit `data/aircraft-specs.json` with the new type's MTOW, compartments, and CG limits.

**Updating DGR tables:**
Add entries to `data/iata-dgr-reference.json` for new UN numbers or updated limits.

**Adjusting CG targets:**
Edit `cg_limits.optimal_cg_pct_mac` in `aircraft-specs.json`.

**New handling codes:**
Add to `config/handling-codes.json` — the booking processor reads SHC definitions from there.

## Domain Reference

| Term | Definition |
|---|---|
| **AWB** | Air Waybill — the contract of carriage for air cargo |
| **NOTOC** | Notification to Captain — mandatory DG/special cargo notification to flight crew |
| **ULD** | Unit Load Device — standardized container or pallet (PMC, LD3, LD7, AKE) |
| **MAC** | Mean Aerodynamic Chord — reference for CG position calculations |
| **MTOW** | Maximum Takeoff Weight — regulatory certification limit |
| **OEW** | Operating Empty Weight — aircraft without payload or fuel |
| **ZFW** | Zero Fuel Weight — OEW + payload (no fuel added) |
| **MZFW** | Maximum Zero Fuel Weight — structural limit for ZFW |
| **CG** | Center of Gravity — must remain within certified envelope for safe flight |
| **IATA DGR** | International Air Transport Association Dangerous Goods Regulations |
| **Packing Group** | I (great danger), II (medium), III (minor) — affects quantity limits |
| **SHC** | Special Handling Code — ELI (lithium), RFL (flammable), CAO (cargo only), HEA (heavy) |
| **PI** | Packing Instruction — specific packing requirements per DG commodity |
| **CAO** | Cargo Aircraft Only — DG forbidden on passenger-carrying aircraft |
