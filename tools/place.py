#!/usr/bin/env python3
"""Emit a kmcp batch of move_schematic_component calls, snapping every
origin to the 2.54 mm connection grid (KiCad pin offsets are 1.27/2.54
multiples, so off-grid origins put pins off-grid and ERC complains)."""
import json, sys
G = 2.54
snap = lambda v: round(v / G) * G
def batch(sch, placements, declutter=True):
    out = [{"tool": "move_schematic_component",
            "args": {"schematicPath": sch, "reference": r,
                     "position": {"x": round(snap(x), 2), "y": round(snap(y), 2)}}}
           for r, (x, y) in placements.items()]
    if declutter:
        out.append({"tool": "suggest_schematic_declutter",
                    "args": {"schematicPath": sch, "apply": True}})
    return out
if __name__ == "__main__":
    sch, P = sys.argv[1], json.load(sys.stdin)
    print(json.dumps(batch(sch, {k: tuple(v) for k, v in P.items()})))
