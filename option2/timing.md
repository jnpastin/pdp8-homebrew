# Option 2 Timing Analysis: TS Lengths and Critical Paths

Status: **revision 2, reviewed 2026-11-20** (phase 1); the analysis as made, with names kept current. Companion to [spec.md](spec.md) §8 and §11.1, and [plan.md](plan.md) (phase 0).

Revision 2 (2026-11-20; control-store part updated to the AS7C256C-15PCN) assumes **decision 12: the control store runs from fast SRAM** shadowed from the EEPROMs at power-on ([spec.md](spec.md) §11.1). Revision 1 assumed the machine ran from the 150 ns EEPROMs; its figures are kept in section 7 for comparison.

Scope: levers 1 (per-TS lengths) and 2 (the FETCH/EXECUTE split) of the plan's "Timing budget". Logic is mixed: ACT on the critical paths named here, HCT elsewhere. The CPU spans several boards; memory and I/O connect through a backplane, and CPU-internal signals may cross between boards on a ribbon cable.

**Main memory is not chosen here.** The figures use the 55 ns SRAM placeholder of revision 1. Section 4.4 gives the access time that any main-memory part must meet.

## 1. Target

From phase 0 ([plan.md](plan.md)): D2AB PRG0 routines 4 and 5 need the ISZ + JMP loop at 3.75 to 3.85 µs. With option 2 that is 2·FETCH + EXECUTE.

| Clock | TSTEP | Target 2F + X | 3a exactly (8/E: F 1.2 µs, X 1.4 µs) |
|---|---|---|---|
| 20 MHz | 50 ns | 75 to 77 steps | F = 24, X = 28 |
| 40 MHz | 25 ns | 150 to 154 steps | F = 48, X = 56 |

Today: every state is 28 steps (TS1 to TS4 = 6, 9, 7, 6; `diagrams/timing/cpu-timing/source/cpu-timing-overview.json`).

At reduced TCLK during hardware debugging, every length scales. Time-based tests (D2AB routines 4 and 5) are not expected to pass then. The TS-length table includes a uniform-slow mode for bring-up ([spec.md](spec.md) §8).

## 2. Part Figures

Maximum propagation delays, −40 to 85 °C, CL = 50 pF, VCC = 4.5 to 5.5 V, from the manufacturers' datasheets (TI except where noted). "Typ" values are not used.

| Function | Part | Path | ACT | HCT (4.5 V) |
|---|---|---|---|---|
| Octal D flip-flop | 74x574 | CLK→Q / setup / hold | 12 / 2.5 / 1 | 45 / 25 / 5 |
| Quad 2:1 mux | 74x157 | data→Y / select→Y / G→Y | 8.6 / 13.2 / 12.3 | 52 / 58 / — (150 pF table) |
| Dual 4:1 mux | 74x153 | data→Y / select→Y / G→Y | 16.4 / 20 / 11.5 | 30 / 43 / 30 |
| 3:8 decoder | 74x138 | A→Y / enable→Y | 10.9 / 10 | 45 / 42 |
| Octal transceiver | 74x245 | A→B / OE→enable | 9 / 12 | — |
| Octal buffer | 74x244 / 541 | A→Y / OE→enable | 9 (assumed equal to 245) / 10.5 | 29 / 38 (HCT541) |
| Quad XOR | 74x86 | A→Y | 10.5 | (HCT86 ≈ 2.5× ACT) |
| Quad AND / OR | 74x08 / 32 | A→Y | 10 / 10 | — |
| 4-bit adder | 74F283 (bipolar F) | A/B→C4 / C0→C4 / C0→Σ | 8.5 / 8.5 / 10.5 | HC283 C0→Σ0 40, C0→Σ1 45 |
| EEPROM 32K×8 (control-store source only) | AT28C256-15 (Microchip, doc0006) | tACC / tOE | 150 / 70 | |
| **Control-store SRAM 32K×8** | **AS7C256C-15PCN** (Alliance Memory; 2.7 to 5.5 V; 28-pin 300 mil PDIP; datasheet Rev 1.0, June 2024) | **tAA / tOE** | **15 / 7** | |
| Main-memory placeholder 32K×8 | AS6C62256-55 (Alliance) | tAA | 55 | tOE not verified (assumed 30) |

- AS7C256C-15PCN, from its datasheet: tRC 15 min, tAA 15 max, tACE 15 max, tOE 7 max, tOH 3 min; write tWC 15, tWP 10, tAW 12, tDW 8, tDH 0. Inputs and outputs are TTL compatible (VOH 2.4 V at −4 mA), which ACT and HCT inputs accept. The B part (no longer available) had the same figures; the A part's faster grades are SOJ and TSOP only.
- **Two differences from the logic figures above:** the C part is specified for **0 to 70 °C only** (commercial; no industrial grade), and its timing is specified into **CL = 30 pF + 1 TTL load**, lighter than the 50 pF used for the logic. A control-word bit that fans out across the ribbon to several boards may need a buffer at the SRAM, or a derating of tAA (section 8).
- In normal running the control-store SRAMs have `/CE` and `/OE` held asserted and `/WE` deasserted, so **tAA** applies.
- **Shadow address buffer:** each SRAM address is driven by the address-formation logic through a tri-state buffer, disabled while `LOADING` so that the copy counter can drive it ([spec.md](spec.md) §11.1). It adds **9 ns** to the address path. Making the last multiplexer stage a tri-state type (74x257) would remove it; this analysis keeps the buffer.
- **12-bit ripple adder, three 74F283:** 8.5 + 8.5 + 10.5 = **27.5 ns**.
- **Wiring:** each backplane or ribbon crossing is allowed 5 ns. Revision 2 also charges one crossing to the control word itself (control board to datapath boards), which revision 1 did not count.

## 3. The Control-Store Path

| Segment | Path | ns |
|---|---|---|
| `T_addr`: address formation | Registered inputs (TS code, MS, `MAPR`, IR, flags) through the `MS_EFF` / `VARIANT` / overlay multiplexers | 22 to 52 (below) |
| Shadow buffer | ACT244/541 | 9 |
| `T_ROM` | AS7C256C-15PCN tAA | 15 |
| Distribution | control word across the ribbon | 5 |
| **`T_CW`** | **raw control-word outputs valid at their receivers** | **51 to 81** |
| `T_dec` | where a field drives tri-state bus enables through a decoder (`IDB_SRC`: 138 + buffer OE) | +23 |

Address-formation paths, ACT (unchanged from revision 1):

| Path | Segments | ns |
|---|---|---|
| TS code (registered 2-bit code) | 574 CLK→Q | 12 (22 if formed by OR gates from one-hot TS signals) |
| `MAPR` → `VARIANT` (EXECUTE) | 574 + 157 data | 21 |
| `MAPR` → `DP_OVL_SEL` → overlay mux select | 574 + 157 data + 153 select | 41 |
| **Class decode** → `VARIANT` (v2 FETCH TS3 and later) | IR 574 + 138 + two gate levels + 157 data | **52** |
| `MS` → `MS_EFF` → `MS_EFF_IS_EXECUTE` → `DP_OVL_SEL` → overlay select | 574 + 157 + compare (about 2 gates) + 157 select + 153 select | 74 |
| Combinational condition through the overlay, for example `ISZ_SKIP_REQ` (MB zero detect) | 574 + 12-bit NOR tree (about 30) + 153 data | 58 |

- **With decision 11** (registered `MS_EFF_IS_EXECUTE` and overlay conditions): `T_addr` ≤ 52 ns, set by the class decode, so **`T_CW` = 81 ns**.
- **Without decision 11:** `T_addr` = 74 ns, so `T_CW` = 103 ns. Section 4.3 shows this still meets 3a.
- **The mapping ROM's lookahead still holds.** The mapping SRAM is addressed by the registered TS code and IR and loads `MAPR` at the next TP: 12 + 9 + 15 + 2.5 ≈ 39 ns, far less than the shortest TS.
- **The timing ROM** (TS lengths), also shadowed, is addressed by the registered MS, TS, and class bit. Its terminal count is valid 12 + 9 + 15 + compare (about 20) ≈ 56 ns into each TS, before the earliest TS end.

### 3.1 CW_VALID

`/RD`, `/WR`, and `/DB_*`, and the CPU's bus drivers, are gated by `CW_VALID`, a registered signal that asserts at a fixed TSTEP once the control word and its enable decodes have settled (Timing Terminology §5.6). Here that is `T_CW` + `T_dec` = 104 ns:
- **at 50 ns TSTEP, `CW_VALID` asserts at step 3 (150 ns)**, with 46 ns of margin. Step 2 (100 ns) would miss by 4 ns;
- at 25 ns TSTEP, at step 5 (125 ns), with 21 ns of margin.

TP-qualified signals (register loads, selects, ALU fields, sequencing) do not wait for `CW_VALID`; they need only settle before their TP. A per-TS `CW_VALID` step from the timing ROM remains possible but is not needed (section 4.3).

## 4. Per-TS Minimum Lengths (v2, ACT critical paths, decision 11, 50 ns TSTEP)

`N = ceil(path / 50)`, where `path` runs from the TS's start (the previous TP edge) to the setup time of its TP.

### 4.1 Actions after the control word

| Action | Path after `T_CW` (ns) | Total (ns) | Steps |
|---|---|---|---|
| Register load from a selected source (for example `MA ← PC`): 157 select + setup | 16 | 97 | 2 |
| ALU operation into a register (INC through the ALU into PC or MB) | 66 | 147 | 3 |
| ALU operation into AC through the IDB (ADD, AND): + 245 9 + 157 8.6 | 84 | 165 | 4 |
| Transfer through the IDB (for example `PC ← MB`, `EA_ADDR ← MB`): `IDB_SRC` decode and OE 23 + 245 9 + select 13 + setup 2.5 | 48 | 129 | 3 |
| **Memory read into MB** (and IR): from `CW_VALID` (150): 574 12 + gate 10 + backplane driver enable 12 + 5 + receiver 9 + main-memory tAA 55 + memory-side driver enable 12 + 5 + receiver 9 + `MB_SRC` 157 8.6 + setup 2.5 | 140 after `CW_VALID` | 290 | 6 |
| **Memory write:** `/WR` from `CW_VALID` for ≥ tWP and ending one TSTEP before TP (`WR_VALID`); write data (`MDB_SRC` select 13 + drivers 12 + 5 + 9) settles at about 120, well before `/WR` ends | — | `CW_VALID` + 2 steps = 250 | 5 |
| OPR pass (FETCH TS3): the pass result is ready about 117 ns after TP2 (section 5), before TS3 begins; then `AC_SRC` select 20 + setup 2.5 | 23 | 104 | 3 |
| SKIP load (FETCH TS3): load-enable 157 select + setup | 16 | 97 | 2 |
| JMP `PC ← EA_FORMED` (FETCH TS3): `PC_SRC` 153 select + setup | 23 | 104 | 3 |
| Sequencer next-state (TP4): class predecodes 52 + buffer 9 + SRAM 15 + 5 + setup | — | 84 | 2 |

### 4.2 Minimum steps per TS

| State | TS1 | TS2 | TS3 | TS4 | Total | Notes |
|---|---|---|---|---|---|---|
| **FETCH (v2)**, PC increment through the ALU | 3 (ALU INC 147) | 6 (read 290) | 3 (OPR, JMP 104) | 3 (skip INC 147; sequencer 84) | **15** | |
| FETCH, PC as a counter (decision 9) | 2 (97) | 6 | 3 | 2 (97) | 13 | |
| **EXECUTE (ISZ)**: `MA ← EA`; read; MB+1 through the ALU; write MB, PC+1 if zero | 2 | 6 | 3 (147) | 5 (write 250; PC INC 147 in parallel) | **16** | |
| EXECUTE (TAD): `MA ← EA`; read; ADD into AC | 2 | 6 | 4 (165) | 2 | 14 | |
| EXECUTE (DCA): `AC_TO_MB`, write | 2 | 2 (97) | 5 (write) | 5 (write, `AC_CLEAR`) | 14 | upper bound: v1 writes in TS3 or TS4 per MRI |
| DEFER (no autoindex); JMP I | 2 | 6 | 2 | 3 (`EA_ADDR ← MB` or `PC ← MB`, 129) | 13 | |
| DEFER (autoindex): MB+1, write back | 2 | 6 | 3 | 5 | 16 | |

Every state's minimum is **13 to 16 steps**, against 24 (fast) and 28 (slow).

### 4.3 Meeting the target

**Proposed 3a lengths, 50 ns TSTEP:**

| State | TS1 | TS2 | TS3 | TS4 | Total | Duration |
|---|---|---|---|---|---|---|
| FETCH, DEFER without autoindex (fast) | 5 | 8 | 6 | 5 | **24** | 1.20 µs |
| EXECUTE, DEFER with autoindex (slow) | 6 | 9 | 7 | 6 | **28** | 1.40 µs (today's 6/9/7/6) |

Margins, from each TS's longest path in section 4.2:

| State | TS1 | TS2 | TS3 | TS4 |
|---|---|---|---|---|
| FETCH | 103 ns (ALU INC) | 110 ns (read) | 196 ns (OPR, JMP) | 103 ns (skip INC) |
| DEFER (fast) | 153 ns | 110 ns | 203 ns | 121 ns (IDB transfer) |
| EXECUTE | 203 ns | 160 ns (read) | 185 ns (TAD) | 50 ns (write) |
| DEFER (autoindex) | 203 ns | 160 ns | 203 ns | 50 ns (write) |

2F + X = 76 steps = 3.80 µs, the 8/E figure and the middle of D2AB's window. The console transaction uses the slow TS2 (9 steps), as before.

Conclusions:
1. **3a is met exactly, with at least 50 ns of margin in every TS** and at least 100 ns in every FETCH TS. Revision 1 had 1 to 2 steps of slack per state at best.
2. **The slow states keep today's 6/9/7/6.** Only the fast states (FETCH and plain DEFER) change, to 5/8/6/5.
3. **Decision 9 (PC as a counter) is not needed.** It would save one step in FETCH TS1 and TS4, which the budget does not need. Keeping the increment in the ALU matches DEC: the 8/E increments the PC through its adder path (KK8-E).
4. **Decision 10 (drive AB from MA early) is not needed.** It shortened only the read, which now has 110 ns of margin.
5. **Decision 11 is not needed.** Without it `T_CW` = 103 ns: every TP-qualified path grows by 22 ns, and `CW_VALID` stays at step 3 (`T_CW` + `T_dec` = 126 < 150). The FETCH minimum becomes 4/6/3/4 = 17 steps and EXECUTE (ISZ) 3/6/4/5 = 18, still within 24 and 28. The margins of TP-qualified paths shrink by 22 ns (FETCH TS1 and TS4 to 81 ns); the memory paths, timed from `CW_VALID`, are unchanged, so the smallest margin stays 50 ns.
6. **Decision 3' (TSTEP): 50 ns is sufficient.** 3a's lengths are whole 50 ns steps, so a 25 ns TSTEP gains nothing for D2AB and costs a faster counter and comparator.
7. **Decision 8 still matters: the control-store address path must stay ACT** (section 6). The SRAM removes the 150 ns EEPROM access, but the HCT address logic would put most of it back (section 7.2).

### 4.4 What main memory must meet

The memory read in FETCH TS2 (8 steps, 400 ns) is the tightest memory path. With `CW_VALID` at 150 ns and 85 ns of fixed path outside the memory part (section 4.1), **any main-memory part with an access time up to about 165 ns fits.** The writes allow a `/WR` pulse of 100 ns (TS4, 6 steps) to 150 ns (TS3, 7 steps). The main-memory technology can therefore be chosen later without changing these lengths.

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

FETCH TS2 lasts 400 ns, so the pass result is ready before TS3 begins. **The OPR pass adds nothing to FETCH TS3** beyond the final `AC_SRC` select.

## 6. Family Assignments (decision 8)

ACT (or F for the adders) on:
- control-store address formation: `MS_EFF`, `VARIANT` / class decode, overlay multiplexers, `MAPR`, and the shadow address buffers;
- post-ROM decoders that drive bus enables (`IDB_SRC`, `MDB_SRC`, `AB`);
- the ALU (74F283), the OPR pass unit, the IDB and MDB transceivers, and the `MB_SRC` / `AC_SRC` multiplexers;
- the memory board's address and data transceivers, and the backplane drivers;
- the TSTEP counter, terminal-count comparator, and `CW_VALID` / `WR_VALID` registers.

HCT is fine for:
- the control-store copy logic (copy counter, `LOADING`, write strobe): it runs once, at power-on, at any speed;
- the front panel, the console command path, and the field registers' sources;
- interrupt enable and inhibit flip-flops, and I/O-side logic outside the timing contract.

## 7. Sensitivity

### 7.1 Revision 1 (EEPROM control store) for comparison

| Configuration | `T_CW` | FETCH min | EXECUTE (ISZ) min | 3a (24/28) |
|---|---|---|---|---|
| Rev. 1: EEPROM, ACT, ALU PC increment | 202 | 25 | 26 | not reachable; fallback 25/26 with no slack |
| Rev. 1: EEPROM, ACT, counter PC | 202 | 23 | 26 | reachable, 1 to 2 steps of slack |
| **Rev. 2: SRAM, ACT, ALU PC increment** | **81** | **15** | **16** | **reachable, ≥ 50 ns margin per TS** |

### 7.2 HCT in the control-store address path

HCT `T_addr` ≈ 130 to 160 ns (revision 1), HCT541 buffer 29, SRAM 15, distribution 5: **`T_CW` ≈ 180 to 210 ns**, about revision 1's EEPROM figure. FETCH would again need about 25 steps with the ALU PC increment, and 3a would again depend on decision 9. The SRAM's slack exists only with ACT address formation.

## 8. Open Items

- Control-word fan-out: each AS7C256C output is specified into 30 pF + 1 TTL. Decide whether each control-word bit is buffered at the SRAM (an ACT244/541 adds 9 ns, keeping every TS within its margins) or derated, once the board split is known.
- The backplane and ribbon crossing allowance (5 ns each): replace once the physical design exists (`docs/11`).
- The ACT244/541 buffer delay is assumed equal to the ACT245's (9 ns).
- Main memory: chosen later, within section 4.4's limits.
- Decisions 3', 8, 9, 10, and 11: recommendations revised in [spec.md](spec.md) §11 from this revision.
- The DMA and console states keep slow lengths. The console transaction uses the slow TS2.
