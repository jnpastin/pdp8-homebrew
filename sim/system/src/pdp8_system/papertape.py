"""DEC BIN-format paper tapes, loaded through the console.

The BIN format, as read by the standard DEC binary loader, uses eight-bit frames:

| Frame | Meaning |
|---|---|
| `10 000 000` (0200) | leader or trailer |
| `11 fff 000` | field setting: subsequent words load into field fff (not part of the checksum) |
| `01 xxxxxx`, `00 yyyyyy` | origin: the next word loads at address xxxxxxyyyyyy |
| `00 xxxxxx`, `00 yyyyyy` | data word xxxxxxyyyyyy, loaded at the current address, which then advances |
| `11 111 111` (0377) | rubout: frames between a pair of rubouts are ignored |

The last word before the trailer is the checksum: the sum, modulo 4096, of every origin and
data frame before it. It is not loaded.

`load_tape` places the words in memory the way an operator would without a loader in memory:
LOAD ADDRESS then DEPOSIT for each run of consecutive addresses, so every word goes through the
console microcode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

LEADER, RUBOUT = 0o200, 0o377


class TapeError(Exception):
    pass


@dataclass
class Tape:
    words: list = field(default_factory=list)   # (field, address, value) in tape order
    checksum: int = 0                            # checksum word read from the tape
    computed: int = 0                            # checksum computed from the frames

    @property
    def checksum_ok(self) -> bool:
        return self.checksum == self.computed


def parse_bin(data: bytes) -> Tape:
    tape = Tape()
    i, n = 0, len(data)
    while i < n and data[i] == LEADER:                       # leader
        i += 1
    if i == n:
        raise TapeError("tape holds only leader")
    current_field, address = 0, 0
    pending = None                                           # (field, address, value, frame sum)
    total = 0
    ignoring = False
    while i < n:
        b = data[i]
        if b == RUBOUT:
            ignoring = not ignoring
            i += 1
            continue
        if ignoring:
            i += 1
            continue
        if b == LEADER:                                      # trailer: the pending word is the checksum
            break
        if b & 0o300 == 0o300:                               # field setting
            current_field = (b >> 3) & 0o7
            i += 1
            continue
        if i + 1 >= n:
            raise TapeError(f"tape ends inside a word at frame {i}")
        lo = data[i + 1]
        if lo & 0o300:
            raise TapeError(f"second frame {lo:03o} of a word at frame {i} has its high bits set")
        value = ((b & 0o77) << 6) | (lo & 0o77)
        if pending is not None:                              # the previous word was data, not the checksum
            tape.words.append(pending[:3])
            total += pending[3]
            address = (pending[1] + 1) & 0o7777
            pending = None
        if b & 0o100:                                        # origin
            address = value
            total += b + lo
        else:
            pending = (current_field, address, value, b + lo)
        i += 2
    else:
        raise TapeError("no trailer after the data")
    if pending is None:
        raise TapeError("no checksum word before the trailer")
    tape.checksum = pending[2]
    tape.computed = total & 0o7777
    return tape


def read_tape(path) -> Tape:
    return parse_bin(Path(path).read_bytes())


def octal_dump_bytes(path) -> bytes:
    """The bytes listed in a `.od` octal dump (one octal frame value per line)."""
    return bytes(int(line, 8) for line in Path(path).read_text(encoding="ascii").split())


def load_tape(machine, tape: Tape) -> int:
    """Deposit every word through the console. Returns the number of words loaded."""
    if not tape.checksum_ok:
        raise TapeError(f"checksum {tape.checksum:04o} does not match computed {tape.computed:04o}")
    expected = None
    for f, address, value in tape.words:
        if (f, address) != expected:
            machine.load_address(address, instruction_field=f)
        machine.deposit(value)
        expected = (f, (address + 1) & 0o7777)
    return len(tape.words)
