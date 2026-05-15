# Firmware

## Purpose
This directory contains programmable logic content, including:
- Microcode (if used)
- ROM images
- Bootstrap loaders

---

## Structure

- `microcode` - Control store definitions
- `bootstrap` - Boot loaders and initialization code

---

## Notes
- This is not firmware in the traditional MCU sense
- All contents target PROM/EEPROM devices

---

## Design Constraints
- Must align with control model defined in `/docs/04-control`
- Must not define behavior outside documented specifications
