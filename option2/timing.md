# Option 2 Timing Analysis: TS Lengths and Critical Paths

Status: **draft for the user's review** (phase 1). Companion to [spec.md](spec.md) §8 and [plan.md](plan.md) (phase 0).

Scope: levers 1 (per-TS lengths) and 2 (the FETCH/EXECUTE split) of the plan's "Timing budget", as the user directed. Logic is mixed: ACT on the critical paths named here, HCT elsewhere. The CPU spans several boards; memory and I/O connect through a backplane, and CPU-internal signals may cross between boards on a ribbon cable.

## 1. Target

From phase 0 ([plan.md](plan.md)): D2AB PRG0 routines 4 and 5 need the ISZ + JMP loop at 3.75 to 3.85 µs. With option 2 that is 2·FETCH + EXECUTE.

| Clock | TSTEP | Target 2F + X | 3a exactly (8/E: F 1.2 µs, X 1.4 µs) |
|---|---|---|---|
| 20 MHz | 50 ns | 75 to 77 steps | F = 24, X = 28 |
| 40 MHz | 25 ns | 150 to 154 steps | F = 48, X = 56 |

Today: every state is 28 steps (TS1 to TS4 = 6, 9, 7, 6; `diagrams/timing/cpu-timing/source/cpu-timing-overview.json`). The user is not committed to those counts.

At reduced TCLK during hardware debugging, every length scales. Time-based tests (D2AB routines 4 and 5) are not expected to pass then. The TS-length table includes a uniform-slow mode for bring-up ([spec.md](spec.md) §8).

## 2. Part Figures

Maximum propagation delays, −40 to 85 °C, CL = 50 pF, VCC = 4.5 to 5.5 V, from the manufacturers' datasheets (downloaded 2026-11-19; TI except where noted). "Typ" values are not used.

| Function | Part | Path | ACT | HCT (4.5 V) |
|---|---|---|---|---|
| Octal D flip-flop | 74x574 | CLK→Q / setup / hold | 12 / 2.5 / 1 | 45 / 25 / 5 |
| Quad 2:1 mux | 74x157 | data→Y / select→Y / G→Y | 8.6 / 13.2 / 12.3 | 52 / 58 / — (150 pF table) |
| Dual 4:1 mux | 74x153 | data→Y / select→Y / G→Y | 16.4 / 20 / 11.5 | 30 / 43 / 30 |
| 3:8 decoder | 74x138 | A→Y / enable→Y | 10.9 / 10 | 45 / 42 |
| Octal transceiver | 74x245 | A→B / OE→enable | 9 / 12 | — |
| Octal buffer | 74x244 / 541 | A→Y / OE→enable | (ACT244 enable 10.5) | 29 / 38 (HCT541) |
| Quad XOR | 74x86 | A→Y | 10.5 | (HCT86 ≈ 2.5× ACT) |
| Quad AND / OR | 74x08 / 32 | A→Y | 10 / 10 | — |
| 4-bit adder | 74F283 (bipolar F) | A/B→C4 / C0→C4 / C0→Σ | 8.5 / 8.5 / 10.5 | HC283 C0→Σ0 40, C0→Σ1 45 |
| EEPROM 32K×8 | AT28C256-15 (Microchip, doc0006) | tACC (address→output) / tOE | 150 / 70 | (grades -20, -25, -35: 200, 250, 350) |
| SRAM 32K×8 | AS6C62256-55 (Alliance) | tAA | 55 | **tOE not yet verified** (assumed 30; datasheet download blocked) |

Derived:
- **12-bit ripple adder, three 74F283:** 8.5 + 8.5 + 10.5 = **27.5 ns**. The same with HC283 is roughly 130 to 150 ns, so the ALU stays F or ACT-family.
- **Wiring:** each backplane or ribbon crossing is allowed 5 ns, which covers trace delay and loading. This is an estimate to replace once the backplane is laid out.

## 3. The Control-Store Path

Every TS waits for its control word. Its parts:

| Segment | Path | ns |
|---|---|---|
| `T_addr`: address formation | Registered inputs (TS code, MS, `MAPR`, IR, flags) through the `MS_EFF` / `VARIANT` / overlay multiplexers to the ROM address | 22 to 52 (below) |
| `T_ROM` | AT28C256-15 address→output | 150 |
| `T_CW` | Raw control-word outputs valid | **172 to 202** |
| `T_dec` | Where a field drives tri-state bus enables through a decoder (`IDB_SRC`: 138 + buffer OE) | +23 |

Address-formation paths, ACT:

| Path | Segments | ns |
|---|---|---|
| TS code (registered 2-bit code) | 574 CLK→Q | 12 (22 if formed by OR gates from one-hot TS signals, CSO §5.1) |
| `MAPR` → `VARIANT` (EXECUTE) | 574 + AND (v1) or 157 data (v2) | 21 to 22 |
| `MAPR` → `DP_OVL_SEL` → overlay mux select → ROM | 574 + 157 data + 153 select | 41 |
| **Class decode** → `VARIANT` (v2 FETCH TS3 and later) | IR 574 + 138 + two gate levels + 157 data | **52** |
| `MS` → `MS_EFF` → `MS_EFF_IS_EXECUTE` → `DP_OVL_SEL` → overlay select | 574 + 157 + compare (about 2 gates) + 157 select + 153 select | 74 |
| Combinational condition through the overlay, for example `ISZ_SKIP_REQUIRED` (MB zero detect) | 574 + 12-bit NOR tree (about 30) + 153 data | 58 |

**Recommendation (decision 11):**
- Register `MS_EFF_IS_EXECUTE` (and `MS_EFF`) at the TP that loads MS, computed from `MS_NEXT` and `RUN_NEXT`, as the docs already do for MS itself. That removes the 74 ns path, leaving 12 + 13.2 + 20 = **45 ns**.
- Register the conditions the overlay reads (zero detects) at the TP before they are used, as SKIP already is ([spec.md](spec.md) §4.2).

With both, **`T_addr` ≤ 52 ns**, set by the class decode, and **`T_CW` ≈ 202 ns**.

HCT in this path instead: `T_addr` ≈ 130 to 160 ns, so `T_CW` ≈ 300 ns. That is 6 steps of settling per TS before any action, more than 24 steps per state, and 3a is out of reach. **The address formation, the overlay, `MAPR`, and the post-ROM select decoders must be ACT.** This is the most consequential family choice.

### 3.1 CW_VALID quantization

`/RD`, `/WR`, and `/DB_*` are gated by `CW_VALID`, a registered signal that asserts at a fixed TSTEP once `T_CS` has elapsed (Timing Terminology §5.6). With `T_CW` ≈ 202 ns:
- at 50 ns TSTEP, `CW_VALID` asserts at step 5 (250 ns), losing 48 ns;
- at 25 ns TSTEP, at step 9 (225 ns), losing 23 ns.

The TS-length table can also give `CW_VALID`'s step per TS, so that a TS whose `T_addr` is short asserts it earlier; this lever is not counted below.

## 4. Per-TS Minimum Lengths (v2, ACT critical paths, 50 ns TSTEP)

`N = ceil(path / 50)`, where `path` runs from the TS's start (the previous TP edge) to the setup time of its TP. A strobe TS also needs its strobe window.

### 4.1 Actions after the control word

| Action | Path after `T_CW` (ns) | Total (ns) |
|---|---|---|
| Register load from a selected source (for example `MA ← PC`): 157 select + setup | 13.2 + 2.5 = 16 | 218 |
| ALU operation into a register (ADD, AND, INC through the ALU): A/B 153 select 20 + adder 27.5 + result mux 16.4 + setup 2.5. If through the IDB to AC: + 245 9 + 157 8.6 | 66 to 84 | 268 to 286 |
| **Memory read into MB** (and IR): from `CW_VALID` (250): 574 12 + gate 10 + backplane driver enable 12 + 5 + receiver 9 + SRAM tAA 55 + SRAM-side driver enable 12 + 5 + receiver 9 + `MB_SRC` 157 8.6 + setup 2.5 | 140 after `CW_VALID` | 390 |
| Memory read, **address driven onto AB before `/RD`** (decision 10): tOE 30 in place of tAA 55 and enable | 115 after `CW_VALID` | 365 |
| **Memory write:** `/WR` from `CW_VALID` for ≥ tWP (one 50 ns step) and ending one TSTEP before TP (`WR_VALID`); write data path (`MDB_SRC` select 13 + drivers 12 + 5 + 9) settles at about 244, well before `/WR` ends | — | `CW_VALID` + 2 steps = 350 |
| OPR pass (v2 FETCH TS3): controls from IR (574 12 + class gating 20) then AND 10 + OR 10 + XOR 10.5 + increment 27.5 + 153 data 16.4: ready about 106 ns after TP2, long before `T_CW`; then `AC_SRC` select 20 + setup 2.5 | 23 | 225 |
| SKIP load (FETCH TS3): skip logic from AC and IR ready about 70; load-enable 157 select + setup | 16 | 218 |
| JMP `PC ← EA_FORMED`: EA from IR and MA (157 data) ready early; `PC_SRC` 153 select + setup | 23 | 225 |
| Sequencer next-state (TP4): sequencer ROM from IR predecodes (52) + 150 + setup | — | 205 |

The **timing ROM** (TS lengths) is addressed by the registered MS, TS, and class bit. Its terminal count is valid 12 + 150 + compare ≈ 185 ns into each TS, before any TS ends. No lookahead from `MS_NEXT` is needed.

### 4.2 Minimum steps per TS

| State | TS1 | TS2 | TS3 | TS4 | Total | Notes |
|---|---|---|---|---|---|---|
| **FETCH (v2)**, PC increment through the ALU | 6 (ALU INC 268) | 8 (read 390) | 5 (OPR, JMP, EA 225) | 6 (skip INC 268, sequencer) | **25** | |
| FETCH, PC as a counter (decision 9) | 5 (218) | 8 | 5 | 5 (218) | **23** | |
| FETCH, counter PC + early AB (decisions 9, 10) | 5 | 8 (365, still over 350) | 5 | 5 | 23 | 7 steps at TS2 needs `CW_VALID` at step 4: `T_CW` ≤ 200 |
| **EXECUTE (ISZ)**: `MA ← EA`; read; MB+1 through ALU; write MB, PC+1 if zero | 5 | 8 | 6 (ALU 268) | 7 (write 350; PC INC 268 in parallel) | **26** | |
| EXECUTE (TAD): `MA ← EA`; read; ADD into AC | 5 | 8 | 6 (286) | 5 | 24 | |
| EXECUTE (DCA): `AC_TO_MB`, write | 5 | 5 (`AC_TO_MB` 218) | 7 (write) | 7 (write, `AC_CLEAR`) | 24 | upper bound: v1 writes in TS3 or TS4 per MRI (execution definitions) |
| DEFER (no autoindex) | 5 | 8 | 5 | 5 | 23 | |
| DEFER (autoindex): MB+1, write back | 5 | 8 | 6 | 7 | 26 | |

### 4.3 Meeting the target

| Configuration | F (min) | X (ISZ, min) | 2F + X (min) | Can be padded to | Slack |
|---|---|---|---|---|---|
| As specified (ALU PC increment) | 25 | 26 | 76 | F = 25, X = 26: 76 | **none** (fallback split; 3a exactly is not reachable) |
| Counter PC (decision 9) | 23 | 26 | 72 | **F = 24, X = 28: 76 (3a exactly)** | 1 step in FETCH, 2 in EXECUTE |
| Counter PC, 40 MHz TSTEP | ≈ 45 (25 ns steps) | ≈ 50 | ≈ 140 | F = 48, X = 56 | ≈ 3 steps (75 ns) per state |

Conclusions:
1. **3a is feasible**, but not with the PC incremented through the shared ALU in FETCH. Two ALU increments in one FETCH (TS1 always, TS4 on a skip) cost one step each over a plain register load. **Decision 9: make PC a synchronous counter** (four 4-bit synchronous counters, count enable from `PC_INC`), or give it a dedicated incrementer. Either moves the increment out of the ALU path, as the user allowed ("moving some items out of ROM and into discrete logic"). DEC's 8/E increments the PC in its adder path, but its control is hardwired, with no ROM settle in each TS.
2. **Without decision 9, the fallback split works:** F = 25 and X = 26 is 2F + X = 76, and phase 0 showed F 1.25 / X 1.30 passing. But there is **no slack**: any path longer than estimated breaks D2AB routines 4 and 5 at full speed.
3. **The memory read sets TS2.** At 8 steps it takes a third of FETCH. An earlier `CW_VALID` for TS2 (per-TS `CW_VALID` from the timing ROM) and early AB drive could bring it to 7 steps.
4. **A 40 MHz TSTEP** roughly halves the quantization loss (about 25 ns per TS, about 100 ns per state) and gives finer trimming of the ±1.3% loop window. It costs a faster TSTEP counter and comparator. Worth deciding before the timing generator is designed (decision 3').
5. **These are estimates from datasheet maxima** with an assumed 5 ns per board crossing and an assumed SRAM tOE. The thinnest margins are FETCH TS3 (225 against 250) and the 8-step TS2 reads. Verify both on the first boards with a logic analyzer, using the uniform-slow mode as the fallback.

## 5. OPR Pass Unit Delay

Stages per [spec.md](spec.md) §4.1, ACT/F, from AC valid (stable since its last load) and controls valid (IR at TP2 + 12, class gating + 20):

| Stage | Part | ns |
|---|---|---|
| A: zero gating | 08 | 10 |
| B: OR inputs (SR, MQ) | 32 | 10 |
| C: complement | 86 | 10.5 |
| D: increment, 13 bits with link | 74F283 × 3 + link XOR | 27.5 + 10.5 |
| E: rotate/BSW | 153 data | 16.4 |
| Total from controls valid | | **85** |
| From TP2 | 12 + 20 + 85 | **117** |

This finishes before `T_CW` (202), so **the OPR pass adds nothing to FETCH TS3** beyond the final `AC_SRC` select. The class decode in the address (52 against 22 for `MAPR`) is TS3's real cost, and it fits in 5 steps with 25 ns to spare.

## 6. Family Assignments (decision 8)

ACT (or F for the adders) on:
- control-store address formation: `MS_EFF`, `VARIANT` / class decode, overlay multiplexers, `MAPR`, registered conditions;
- post-ROM decoders that drive bus enables (`IDB_SRC`, `MDB_SRC`, `AB`);
- the ALU (74F283), the OPR pass unit, the IDB and MDB transceivers, and the `MB_SRC` / `AC_SRC` multiplexers;
- the memory board's address and data transceivers, and the backplane drivers;
- the TSTEP counter, terminal-count comparator, and `CW_VALID` / `WR_VALID` registers.

HCT is fine for:
- the front panel, the console command path, and the field registers' sources (IF, DF, IB loads are register-to-register with a whole TS to settle);
- interrupt enable and inhibit flip-flops, and I/O-side logic outside the timing contract.

## 7. Open Items

- SRAM output-enable time (AS6C62256-55 tOE): replace the assumed 30 ns with the datasheet value.
- The backplane and ribbon crossing allowance (5 ns each): replace once the physical design exists (`docs/11`).
- Decision 3': 50 ns or 25 ns TSTEP.
- Decision 9 (counter PC), 10 (early AB drive), and 11 (registered `MS_EFF_IS_EXECUTE` and conditions): see [spec.md](spec.md) §11.
- The DMA and console states keep slow lengths. The console transaction uses the slow TS2 (the longest read or write), which v1's console docs already tie to TS2.
