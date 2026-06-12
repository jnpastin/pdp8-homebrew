# Microarchitectural Control Signals

## Index
- [AB_src](#ab_src)
- [MA_load](#ma_load)
- [MB_load](#mb_load)
- [IR_load](#ir_load)
- [PC_inc](#pc_inc)
- [MDB_src](#mdb_src)

---

## AB_src

### Definition
Selects source driving AB.

### Values
- PC
- EA

### Constraints
- Only valid when MA_load = 1

---

## MA_load

### Definition
Loads MA from AB.

### Values
0, 1

### Constraints
- AB must be driven

### Preconditions:
- Correct producer is active (CPU or DMA device)

---

## MB_load

### Definition
Loads MB from MDB.

### Values
0, 1

### Constraints
- MDB must be driven
- Data must be CPU-valid

### Preconditions:
- MDB contains CPU-valid data
- Correct producer is active (RD or DB_READ)

---

## IR_load

### Definition
Loads IR from MB.

### Values
0, 1

### Preconditions:
- MB contains valid instruction word

---

## PC_inc

### Definition
Increments PC.

### Values
0, 1

---

## MDB_src

### Definition
Selects source driving MDB.

### Values
- MB
- ALU (future)

### Constraints
- Must match operation (write or compute)

### Preconditions:
- Selected source contains valid data
