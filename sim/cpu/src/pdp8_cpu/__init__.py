"""Control-store simulator of the PDP-8/e-compatible CPU.

The simulator reads the packed control-store images and executes one timing state (TS) at a
time, committing register loads at the timing pulse (TP). Every behavior cites the document
that defines it; where the documents are silent or inconsistent, the simulator raises
`SpecGap` instead of inventing behavior.
"""
