"""32K x 12-bit memory: eight fields of 4096 words, selected by MEM_ADDR = {MFB, AB}.

Sources: docs/06-memory/01-memory-model.md (12-bit words selected by field and address),
docs/06-memory/03-read-write-protocol.md (a read returns the stored word and changes nothing; a
write changes exactly one word). The documents do not define the contents at power-on, so every
word starts UNDEFINED (None) until written.
"""

from __future__ import annotations

FIELDS = 8
WORDS = 4096


class Memory:
    def __init__(self):
        self.words = [[None] * WORDS for _ in range(FIELDS)]
        self.write_count = 0              # writes so far; lock-step compares each write from the
                                          # CPU's per-TS records, so none are kept here

    @staticmethod
    def _check(field, address):
        if not (0 <= field < FIELDS and 0 <= address < WORDS):
            raise ValueError(f"memory address {field:o}:{address:04o} out of range")

    def read(self, field: int, address: int):
        self._check(field, address)
        return self.words[field][address]

    def write(self, field: int, address: int, value):
        self._check(field, address)
        if value is not None:
            value &= 0o7777
        self.words[field][address] = value
        self.write_count += 1

    def preload(self, field: int, address: int, values):
        """Place words directly, bypassing the CPU. For unit tests only: programs are loaded
        through console DEPOSIT so the console microcode is exercised."""
        for k, value in enumerate(values):
            self._check(field, address + k)
            self.words[field][address + k] = value & 0o7777
