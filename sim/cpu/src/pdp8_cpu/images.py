"""Load the logical control-store images written by the control-store packer.

Image format (tools/rom-generation/control-store-packer README §5): one byte per line as two hex
digits, 32768 lines, address 0 first. `datapath-<n>.hex` holds datapath bits 8n..8n+7.

The packing description supplies the physical wiring the packer chose: the datapath and
sequencer bit layouts and the overlay-group pin assignments. Everything else the simulator needs
(address formation, mapping-register fields, command codes) is coded from the documentation and
only cross-checked against the packing description here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import design as D
from . import encodings as E
from .errors import ImageError

REPO_ROOT = D.REPO_ROOT
# The selected design's packer outputs and schema (design.py; PDP8_DESIGN, default v1).
DEFAULT_DESIGN = D.select()
DEFAULT_IMAGE_DIR = DEFAULT_DESIGN.image_dir
DEFAULT_PACKING = DEFAULT_DESIGN.packing
DEFAULT_SCHEMA = DEFAULT_DESIGN.schema

IMAGE_DEPTH = 1 << 15  # 28C256: 15 address bits (CSO §2)
DATAPATH_DEVICES = 6  # CSO §4.2; the packing's summary gives the design's own count
NON_EXECUTE_GROUP = 1  # CSO §5.4.2: the MS_EFF_IS_EXECUTE = 0 group is wired as group 1

# CSO §4.1 and §4.2: the fields each slice produces.
SEQUENCER_FIELD_NAMES = {"MS_NEXT", "MS_LOAD", "RUN_NEXT", "HLT_REQ_NEXT", "/INITIALIZE"}


@dataclass(frozen=True)
class Slot:
    offset: int
    width: int
    fields: tuple


def read_hex_image(path: Path) -> list[int]:
    if not path.exists():
        raise ImageError(f"image not found: {path}", "run tools/rom-generation/pipeline to create the images")
    lines = path.read_text(encoding="ascii").splitlines()
    if len(lines) != IMAGE_DEPTH:
        raise ImageError(f"{path.name}: {len(lines)} lines, expected {IMAGE_DEPTH}")
    values = []
    for n, line in enumerate(lines):
        if len(line) != 2:
            raise ImageError(f"{path.name} line {n + 1}: {line!r} is not two hex digits")
        try:
            values.append(int(line, 16))
        except ValueError:
            raise ImageError(f"{path.name} line {n + 1}: {line!r} is not hex") from None
    return values


class ControlStore:
    """The mapping ROM, the six datapath devices, and the sequencer device, with their wiring."""

    def __init__(self, mapping, datapath, sequencer, packing, design: D.Design = DEFAULT_DESIGN):
        self.design = design      # the control design these images belong to (design.py)
        self.mapping = mapping
        self.datapath = datapath  # 48-bit words
        self.sequencer = sequencer
        self.packing = packing
        self.datapath_layout = [Slot(s["offset"], s["width"], tuple(s["fields"]))
                                for s in packing["datapath_layout"]]
        self.sequencer_layout = [Slot(s["offset"], s["width"], (s["field"],))
                                 for s in packing["sequencer_layout"]]
        self.overlay_groups = {
            g["code"]: [(b["bit"], b["signal"], b["width"]) for b in g["bits"]]
            for g in packing["overlay_groups"]
        }
        # CSO §6.3: the state group's running face behind the RUN multiplexer (v2); "bits" is
        # then its halted face.
        self.running_overlay_groups = {
            g["code"]: [(b["bit"], b["signal"], b["width"]) for b in g["running_bits"]]
            for g in packing["overlay_groups"] if "running_bits" in g
        }
        self.fields = E.datapath_fields(design.name)   # this design's datapath field definitions
        self._dp_words: dict[int, dict] = {}     # decoded words, by address (the images never change)
        self._seq_words: dict[int, dict] = {}
        self._validate()

    @classmethod
    def load(cls, image_dir: Path | None = None, packing_path: Path | None = None,
             design: D.Design | None = None):
        """Load `design`'s images (default: the selected design); `image_dir` and
        `packing_path` override its paths."""
        design = design or DEFAULT_DESIGN
        image_dir = Path(image_dir or design.image_dir)
        packing_path = Path(packing_path or design.packing)
        if not packing_path.exists():
            raise ImageError(f"packing description not found: {packing_path}",
                             "run tools/rom-generation/pipeline to create it")
        packing = json.loads(packing_path.read_text(encoding="utf-8"))
        mapping = read_hex_image(image_dir / "mapping.hex")
        sequencer = read_hex_image(image_dir / "sequencer.hex")
        count = packing.get("summary", {}).get("datapath_devices", DATAPATH_DEVICES)
        devices = [read_hex_image(image_dir / f"datapath-{n}.hex") for n in range(count)]
        datapath = [sum(devices[n][a] << (8 * n) for n in range(count))
                    for a in range(IMAGE_DEPTH)]
        return cls(mapping, datapath, sequencer, packing, design)

    # -- validation against the documentation ---------------------------------------------

    def _validate(self):
        problems = []
        seen = {}
        for slot in self.datapath_layout:
            for name in slot.fields:
                if name in seen:
                    problems.append(f"datapath field {name} appears in two slots")
                seen[name] = slot
                fd = self.fields.get(name)
                if fd is None:
                    problems.append(f"datapath layout names unknown field {name}")
                elif fd.width > slot.width:
                    problems.append(f"{name} ({fd.width} bits) does not fit its {slot.width}-bit slot")
            limit = 8 * self.packing.get("summary", {}).get("datapath_devices", DATAPATH_DEVICES)
            if slot.offset + slot.width > limit:
                problems.append(f"datapath slot at bit {slot.offset} exceeds {limit} bits")
        names = set(self.fields)
        if set(seen) != names:
            problems.append(f"datapath layout fields differ from CSO §4.2: "
                            f"missing {sorted(names - set(seen))}, "
                            f"extra {sorted(set(seen) - names)}")
        seq_names = {s.fields[0] for s in self.sequencer_layout}
        if seq_names != SEQUENCER_FIELD_NAMES:
            problems.append(f"sequencer layout fields {sorted(seq_names)} differ from CSO §4.1")
        for slot in self.sequencer_layout:
            if slot.width != E.SEQUENCER_FIELDS[slot.fields[0]].width or slot.offset + slot.width > 8:
                problems.append(f"sequencer slot {slot.fields[0]} has a bad width or offset")
        fields = self.packing["mapping_rom"]["fields"]
        for name, (offset, width) in E.MAPR_FIELDS.items():
            if fields.get(name) != [offset, width]:
                problems.append(f"mapping field {name} is {fields.get(name)}, CSO §5.4.1 gives {[offset, width]}")
        if self.packing.get("non_execute_overlay_group") != NON_EXECUTE_GROUP:
            problems.append("non-EXECUTE overlay group is not group 1 (CSO §5.4.2)")
        for key, wired in (("non_execute_variant", self.design.non_execute_variant),
                           ("sequencer_a2", self.design.sequencer_a2),
                           ("sequencer_a1", self.design.sequencer_a1)):
            if self.packing.get(key) != wired:
                problems.append(f"{key} is {self.packing.get(key)!r} in the packing, "
                                f"{wired!r} for design {self.design.name} (CSO §5.4.2, §5.6)")
        muxed = set(self.running_overlay_groups)
        if muxed != ({NON_EXECUTE_GROUP} if self.design.state_group_run_mux else set()):
            problems.append(f"overlay groups with a RUN-multiplexed face {sorted(muxed)} do not "
                            f"match design {self.design.name} (CSO §6.3)")
        for code, bits in [*self.overlay_groups.items(), *self.running_overlay_groups.items()]:
            used = set()
            for bit, _signal, width in bits:
                used |= set(range(bit, bit + width))
            if not used <= set(range(5)):
                problems.append(f"overlay group {code} uses bits outside DP_OVL[4:0]")
        if set(self.overlay_groups) - set(range(4)):
            problems.append("overlay group codes must be 0..3 (DP_OVL_SEL is 2 bits)")
        expected_cmds = {k: v for k, v in E.FP_CMD_CODES.items() if k}
        packed_cmds = {k.removeprefix("FP_"): v for k, v in self.packing["fp_cmd"].items()}
        if packed_cmds != expected_cmds:
            problems.append(f"FP_CMD codes {packed_cmds} differ from CSO §5.2 {expected_cmds}")
        if problems:
            raise ImageError("control-store packing disagrees with the documentation: " + "; ".join(problems))

    # -- decoding --------------------------------------------------------------------------

    def decode_datapath(self, address: int) -> dict:
        """Every datapath field, read from its wired bits; shared bits give every sharer a value.

        Cached per address; callers must not modify the result."""
        cached = self._dp_words.get(address)
        if cached is not None:
            return cached
        word = self.datapath[address]
        out = {}
        for slot in self.datapath_layout:
            raw = (word >> slot.offset) & ((1 << slot.width) - 1)
            for name in slot.fields:
                out[name] = raw & ((1 << self.fields[name].width) - 1)
        self._dp_words[address] = out
        return out

    def decode_sequencer(self, address: int) -> dict:
        """Every sequencer field. Cached per address; callers must not modify the result."""
        cached = self._seq_words.get(address)
        if cached is None:
            word = self.sequencer[address]
            cached = {s.fields[0]: (word >> s.offset) & ((1 << s.width) - 1) for s in self.sequencer_layout}
            self._seq_words[address] = cached
        return cached

    def overlay_group(self, code: int, run) -> list:
        """The bits overlay group `code` presents on DP_OVL: the state group's running face
        while RUN = 1 when the design multiplexes it (CSO §6.3)."""
        if run == 1 and code in self.running_overlay_groups:
            return self.running_overlay_groups[code]
        return self.overlay_groups[code]

    def mapping_entry(self, address: int) -> int:
        return self.mapping[address]
