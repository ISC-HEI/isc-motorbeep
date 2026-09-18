<picture>
  <source media="(prefers-color-scheme: dark)"
          srcset="https://raw.githubusercontent.com/ISC-HEI/isc-logos/main/white/ISC%20Logo%20inline%20white%20v3%20-%20large.webp">
  <img align="right" height="50" alt="ISC Logo"
       src="https://raw.githubusercontent.com/ISC-HEI/isc-logos/main/black/ISC%20Logo%20inline%20black%20v3%20-%20large.webp"/>
</picture>

# ISC MotorBeep — ESP32 dual-stepper + audio board

A complete [KiCad 9](https://www.kicad.org/) schematic for an ESP32 board driving two bipolar
stepper motors and a small speaker, powered from 3× AA cells. It is an improved derivative of the
ESP32 DevKit DOIT v1: the AMS1117 LDO, the thin bulk capacitance, the micro-USB connector and the
absent battery sensing are all addressed.

## Schematic

Four hierarchical sheets plus a root. Click any image for full resolution, or read
[the complete PDF](./doc/isc-motorbeep-schematic.pdf).

### Root — sheet hierarchy

[![Root sheet](./doc/render/root.png)](./doc/render/root.png)

### Power — 3× AA, Schottky OR, TPS63001 buck-boost, USB-C

[![Power sheet](./doc/render/power.png)](./doc/render/power.png)

### MCU — ESP32-WROOM-32E, CP2102N bridge, auto-reset

[![MCU sheet](./doc/render/mcu.png)](./doc/render/mcu.png)

### Motors — 2× STSPIN220 stepper drivers

[![Motors sheet](./doc/render/motors.png)](./doc/render/motors.png)

### Audio — MAX98357A Class-D

[![Audio sheet](./doc/render/audio.png)](./doc/render/audio.png)

## Architecture

Three AA cells deliver 2.8–4.8 V, and that range sits inside the supply window of both power loads —
the STSPIN220 works from 1.8 V and the MAX98357A from 2.5 V — so the motors and the speaker run
straight off the pack with no converter at all. Only the ESP32 needs one, and it has to be a
buck-boost: the pack starts above 3.3 V and ends below it, so an LDO would drop out and a plain
boost could not regulate down. USB and battery are OR'd through two Schottky diodes into that
converter only, which is what stops USB from back-feeding and charging the alkaline cells.

```mermaid
flowchart LR
    B["3x AA / 2.8-4.8 V"] --> D2["D2 Schottky"]
    U["USB-C 5 V"] --> D1["D1 Schottky"]
    D1 --> V["VSYS"]
    D2 --> V
    V --> R["U2 TPS63001 buck-boost"]
    R --> L3["+3V3 - ESP32 only"]
    B --> M["U5/U6 STSPIN220 - 2 steppers"]
    B --> A["U7 MAX98357A - speaker"]
```

Every line the ESP32 gates has a resistor defining its state at reset, so the motors cannot twitch
and the speaker cannot pop at power-up; `GPIO12` is left unconnected because it straps the flash
voltage. The reasoning, the full pin budget and the pre-fabrication checklist are in
**[`doc/DESIGN.md`](./doc/DESIGN.md)**.

## Bill of materials

70 components in 36 lines, about **$14.49** in parts at 1-off LCSC prices (catalog snapshot of
14 September 2026). Full priced BOM with a part link per line: **[`doc/BOM.md`](./doc/BOM.md)**.

> [!WARNING]
> **The STSPIN220 was down to 27 units at JLCPCB in that snapshot** — check it live before
> committing to a build. `doc/BOM.md` names the substitute and what swapping costs you.

Almost every part is a JLCPCB *Extended* part with a $3 setup fee each, so for a one-off, hand
assembly is cheaper than paying the setup fees.

## Open it

```bash
kicad hardware/isc-motorbeep/isc-motorbeep.kicad_pro
```

Generated headlessly through the KiCAD-MCP-Server — reproduction steps, the KiCad 9 file-format
patch it needs, and the helper scripts are in [`doc/TOOLING.md`](./doc/TOOLING.md).

## Before fabricating

The schematic is complete and ERC-clean, but two questions could not be settled without
manufacturer datasheets. Both are detailed, with the rest of the checklist, in
[`doc/DESIGN.md` §8.5–8.6](./doc/DESIGN.md):

- **Are the STSPIN220 and MAX98357A logic inputs rated independently of their supply?** The ESP32
  drives 3.3 V into them while `+BATT` may be at 2.8 V. If either is VS-referenced, the design
  breaks at low battery. This is the one that matters.
- **The QFN-16 exposed-pad dimension** for U5/U6/U7 — stock footprint variants run 1.45 to 1.85 mm,
  and it is the thermal path the current-chopping depends on.

---

## License

Copyright © 2026 P.-A. Mudry / ISC — HES-SO Valais. Released under
[CC-BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/).

---

*Made with ♥ by mui, 2026*
