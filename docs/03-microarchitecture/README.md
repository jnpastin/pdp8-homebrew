# Microarchitecture Overview

Reference Diagram:
![alt text](../../diagrams/architecture/High-Level-Architecture/export/High-Level-Architecture.png "Microarchitecture Block Diagram")

This section defines the high-level structure of the microarchitecture.

The system is built around three planes:
- Timing Plane: defines when operations occur
- Control Plane: defines what operations occur
- Datapath Plane: executes operations

Core control function:

CONTROL = f(MS, TS, IR, FLAGS)

Execution progresses in discrete steps, with each Timing Pulse (TP) advancing the system to the next microstate.
