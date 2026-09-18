# How this schematic was generated

The schematic was authored without opening the KiCad GUI, by driving the
[KiCAD-MCP-Server](https://github.com/mixelpixx/KiCAD-MCP-Server) over stdio. This file records
what is needed to reproduce that, and the traps worth knowing. None of it is required to *use*
the schematic — for that, open the project in KiCad 9.

## Prerequisites

| Tool | Why | Debian/Ubuntu | macOS |
|---|---|---|---|
| KiCad 9 | `pcbnew`, `kicad-cli`, symbol + footprint libraries | `sudo add-apt-repository ppa:kicad/kicad-9.0-releases && sudo apt install kicad` | `brew install --cask kicad` |
| Node.js ≥ 18 | the MCP server itself | `sudo apt install nodejs npm` | `brew install node` |
| Python ≥ 3.11 | `kicad-skip`, `sexpdata`, `pymupdf` | `sudo apt install python3 python3-venv` | `brew install python` |

The server is cloned into `tools/kicad-mcp-server/` and is **not** tracked here — it is a
third-party project with its own history. `.mcp.json` registers it for Claude Code and contains
absolute paths; adjust them to wherever you cloned it.

Two setup snags on Ubuntu 24.04: `python3 -m venv` produces a venv with no `pip` (bootstrap it with
`get-pip.py`), and the venv cannot see KiCad's `pcbnew` unless you drop a `.pth` file naming
`/usr/lib/python3/dist-packages` into its `site-packages`.

## The KiCad 10 vs 9 file format problem

The server writes `(version 20260101)`, the KiCad 10 schematic format. KiCad 9 refuses those files
with no better diagnostic than `Failed to load schematic`. The fix is three lines and is described
in [`KICAD9-PATCH.md`](./KICAD9-PATCH.md). Re-apply it after pulling the server upstream.

## Scripts in `tools/`

| Script | Does |
|---|---|
| `pins.py` | prints a library symbol's pins, resolving `(extends …)`, so nets are wired against real pin numbers |
| `place.py` | emits component-move batches with every origin snapped to the 2.54 mm connection grid |
| `check_nets.py` | parses the exported netlist and asserts each design-intent net reaches the pins it should |
| `price_bom.py` | prices the BOM against the server's offline JLCPCB catalog and writes [`BOM.md`](./BOM.md) |
| `render.sh` | exports a sheet to SVG + PNG and prints its ERC |

`kmcp.mjs`, the minimal stdio MCP client used to call the server (`list` / `schema` / `call` /
`batch`), lives inside the untracked server directory because it resolves the server's own
`node_modules`.

## Traps

- **Off-grid origins break ERC.** Placing parts on round millimetre coordinates puts their pins off
  the 2.54 mm connection grid, and KiCad then reports *"Symbol pin or wire end off connection grid"*
  for every one. `place.py` snaps origins so this cannot happen.
- **Per-sheet ERC is not the real ERC.** Cross-sheet global labels look dangling on their own sheet.
  Only `run_erc` on the root schematic is meaningful.
- **"Connected N pins" is not verification.** The server reports success for labels it placed, not
  for a netlist KiCad agrees with. `check_nets.py` closes that gap, and it is what caught the pin
  mapping questions recorded in `DESIGN.md` §8.6.
- **Parse symbol files by paren depth, not by lookahead.** A bounded regex over a `(pin …)` block
  silently drops pins with long name/effects blocks — it reported the ESP32 module as 29 pins
  instead of 39, and the USB-C receptacle as 11 instead of 17. That produced one wrong conclusion
  that survived into a published README before the netlist contradicted it.

## Adding a sheet

1. `create_hierarchical_subsheet` against `isc-motorbeep.kicad_sch` — creates the file and links it.
2. Add parts with `batch_add_and_connect` and `labelType: "global_label"`; cross-sheet nets join by name.
3. Snap origins with `place.py`, then `autoplace_schematic_fields` and `suggest_schematic_declutter`.
4. `run_erc` on the **root**.
5. Add the sheet's nets to `check_nets.py`, render it, and look at the PNG.
