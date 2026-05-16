# Build Artifacts

## Purpose
Contains generated outputs produced from source files.

This directory is tracked in version control. Committed artifacts serve as reference outputs and allow verification that source and generated content stay in sync.

---

## Structure

- `gerbers/` - PCB fabrication files (generated from KiCad)
- `rom_images/` - Binary ROM images (generated from microcode source)
- `simulation_outputs/` - Captured simulation results

---

## Rules

- Do not hand-edit files here; all content must be regenerated from source
- Source for each artifact lives in `/hardware`, `/rom`, or `/sim`
- Committed files should be current with their source; stale artifacts are an error
