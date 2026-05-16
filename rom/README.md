# ROM

## Purpose
This directory contains all programmable read-only content for the system, including:
- Microcode / control store definitions
- Bootstrap loaders
- ROM images ready for programming

---

## Structure

- `microcode/` - Control store source definitions
- `bootstrap/` - Boot loaders and initialization code

Generated binary images are placed in `/build/rom_images`, not here.

---

## Design Constraints
- Content must align with the control model defined in `/docs/04-control`
- Must not define behavior outside documented specifications
