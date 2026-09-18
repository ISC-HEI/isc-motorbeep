# Local patch: emit KiCad 9 schematic format

Upstream v2.7.0 creates schematics as `(version 20260101) (generator_version "10.0")`
(KiCad 10). KiCad 9.0.9 — the version this project targets, and the minimum the
server itself documents — refuses to load those files: `kicad-cli` reports only
`Failed to load schematic`.

Root cause is narrow. `dynamic_symbol_loader.py::_supports_kicad10_symbol_tokens`
already gates the KiCad-10-only tokens `(body_style N)` and `(in_pos_files yes)`
on the file's declared version, so it does the right thing *if the file declares
version 9*. Only the creation path was hardcoded to 10.

Changed the declared version to `20250114` / `"9.0"` in:

- `python/commands/schematic.py`   (create_schematic)
- `python/commands/project.py`     (project creation)
- `python/templates/blank.kicad_sch`

20250114 is readable by both KiCad 9 and 10 (10 upgrades on load), so this is
the safe target rather than a downgrade.

Re-apply after any `git pull` of the upstream server.
