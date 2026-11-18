# Memory Model

## 1. Purpose

Models main memory at the memory-interface boundary: 32K 12-bit words in eight fields of 4096, selected by `MEM_ADDR = {MFB, AB}` ([Memory Model](../../docs/06-memory/01-memory-model.md), [Read/Write Protocol](../../docs/06-memory/03-read-write-protocol.md)).

## 2. Behavior

- A read returns the stored word and changes nothing.
- A write changes exactly one word and is recorded in `write_log`, for comparison against a reference model.
- The documents do not define the contents at power-on, so every word starts UNDEFINED (`None`) until written.
- `preload` places words directly. It is for unit tests only: programs are loaded through console DEPOSIT so the console microcode is exercised.

The CPU decides when a read or write occurs and with which address and data; this model only stores and returns words.

## 3. Testing

```text
python -m unittest discover -s sim/memory/tests -p "test_*.py"
```
