#!/usr/bin/env python3
"""Deliberate placement for isc-motorbeep, with a self-check.

Board is 70 x 50 mm, origin top-left, y increasing downward.

Two footprint facts drive the coordinates, both measured rather than assumed:

  * Pin headers (J2, J3, J4, J5, BT1) have their ORIGIN AT PIN 1, not at their
    centre, and extend +Y from there -- J2 (1x08) reaches +19.6 mm. Placing
    them by centre puts them through the board edge.
  * U3's courtyard is x +-24.3, y -28..+13.6 because it includes the antenna
    keepout. The module BODY is only x +-9, y -6.6..+13.6. Overlap checking
    against the courtyard gives false positives for every part beside the
    module, so the check below uses the body for U3 and the keepout separately.

Floorplan: U3 top-left with its antenna overhanging the top edge; USB chain
(J1 -> U1 -> U4) top-right; buck-boost bottom-right with L1 hard against U2 so
the SW1/SW2 switching loop stays small; the two motor channels down the left
edge, each next to its own connector; audio bottom-centre.
"""
import pcbnew, sys, itertools

BOARD = "/home/pmudry/git/cad-demo/hardware/isc-motorbeep/isc-motorbeep.kicad_pcb"
W, H, MARGIN = 70.0, 50.0, 0.5

PLACE = {
    # MCU, top-left. U3 first; its antenna hangs off the top edge.
    "U3": (22, 9), "R10": (5, 5), "C13": (5, 9), "SW2": (5, 15), "SW1": (5, 22),
    "C10": (14, 25), "C11": (18, 25), "C12": (22, 25),
    "D3": (36, 5), "R12": (40, 5), "SW3": (38, 12), "R13": (36, 18), "R11": (41, 18),
    "J2": (46, 5),
    # USB-C -> ESD -> bridge, top-right, in that physical order.
    "J1": (61, 6), "R1": (52, 4), "R2": (52, 8),
    "U1": (61, 14), "U4": (60, 22),
    "C14": (52, 13), "C15": (52, 17), "R14": (52, 21),
    "R15": (67, 14), "Q2": (67, 19), "Q3": (67, 25), "R16": (56, 27),
    # Buck-boost, bottom-right. L1 sits 1.7 mm below U2: this gap IS the
    # switching loop, and it is the one dimension worth protecting.
    # L1 sits directly LEFT of U2, rotated 90 so its two pads line up with the
    # SW1/SW2 pins. Those pins are pads 2 and 4 of a 0.5 mm-pitch column, so
    # this is the only geometry that gets both switching nodes out as short
    # straight traces instead of routing them around the package.
    "U2": (54, 34), "L1": (48.5, 34, 90),
    "C1": (50.5, 38), "C4": (58, 30), "R5": (58, 27),
    "C2": (50.5, 30), "C3": (54, 29.5), "C5": (61, 34),
    "D1": (48, 44), "D2": (53, 46), "Q1": (60, 45),
    "R3": (64, 33), "R4": (64, 37), "BT1": (67, 43),
    # Motor 1 then motor 2, down the left edge beside their connectors.
    "J3": (3, 27.5), "U5": (13, 31),
    "R30": (9, 28), "R31": (9, 34), "R32": (24, 31),
    "R33": (18, 29), "R34": (18, 33), "C20": (13, 27), "C21": (24, 27),
    "J4": (3, 39), "U6": (13, 43),
    "R40": (9, 40), "R41": (9, 46), "R42": (24, 43),
    "R43": (18, 41), "R44": (18, 45), "C22": (13, 39), "C23": (24, 39),
    "R20": (28.5, 29), "R21": (28.5, 33), "R22": (28.5, 37),
    "R23": (28.5, 41), "R24": (28.5, 45),
    # Audio, bottom-centre, speaker connector on the bottom edge.
    "U7": (36, 38), "R50": (41, 38), "J5": (36, 45),
    "C30": (32, 33), "C31": (36, 33), "C32": (40, 33),
}

# Anchors keep their coordinates exactly: connectors must stay on their edge,
# and U2/L1 must stay adjacent or the switching loop grows. Everything else is
# a passive that may be nudged to the nearest free spot.
ANCHORS = {"U3","U2","L1","U1","U4","U5","U6","U7",
           "J1","J2","J3","J4","J5","BT1","SW1","SW2","SW3","D1","D2"}

# U3: real body, and the copper/footprint keepout, relative to its origin.
U3_BODY    = (-9.0, 9.0, -6.6, 13.6)
U3_KEEPOUT = (-24.3, 24.3, -28.0, -6.6)

def extent(f):
    """Origin-relative (x0,x1,y0,y1) of a footprint's courtyard, in mm."""
    o = f.GetPosition(); cy = f.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox()
    return ((bb.GetLeft()-o.x)/1e6, (bb.GetRight()-o.x)/1e6,
            (bb.GetTop()-o.y)/1e6, (bb.GetBottom()-o.y)/1e6)

def box(f):
    o = f.GetPosition(); ox, oy = o.x/1e6, o.y/1e6
    if f.GetReference() == "U3":
        x0, x1, y0, y1 = U3_BODY
    else:
        x0, x1, y0, y1 = extent(f)
    return (ox+x0, ox+x1, oy+y0, oy+y1)

def overlap(a, b, tol=0.0):
    return (a[0] < b[1]-tol and b[0] < a[1]-tol and
            a[2] < b[3]-tol and b[2] < a[3]-tol)

def main():
    b = pcbnew.LoadBoard(BOARD)
    for ref, spec in PLACE.items():
        x, y, rot = (spec + (0,))[:3] if len(spec) == 2 else spec
        f = b.FindFootprintByReference(ref)
        if f is None:
            print(f"  !! {ref} not on board"); continue
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        f.SetOrientationDegrees(rot)

    fps = list(b.GetFootprints())

    # Resolve overlaps: walk the non-anchor parts and, for any that collides,
    # search outward on a 0.5 mm grid for the nearest position that is free and
    # on-board. Anchors never move.
    u3 = b.FindFootprintByReference("U3"); uo = u3.GetPosition()
    keep = (uo.x/1e6+U3_KEEPOUT[0], uo.x/1e6+U3_KEEPOUT[1],
            uo.y/1e6+U3_KEEPOUT[2], uo.y/1e6+U3_KEEPOUT[3])

    def fits(ref, bx, others):
        if bx[0] < MARGIN or bx[1] > W-MARGIN or bx[2] < MARGIN or bx[3] > H-MARGIN:
            return False
        if overlap(bx, keep, tol=0.05):
            return False
        return not any(overlap(bx, ob, tol=0.05) for r, ob in others.items() if r != ref)

    placed_boxes = {f.GetReference(): box(f) for f in fps}
    moved = []
    for f in fps:
        ref = f.GetReference()
        if ref in ANCHORS:
            continue
        if fits(ref, placed_boxes[ref], placed_boxes):
            continue
        o = f.GetPosition(); ox, oy = o.x/1e6, o.y/1e6
        ex = extent(f)
        found = None
        for radius in [r*0.5 for r in range(1, 41)]:
            for dx, dy in [(radius,0),(-radius,0),(0,radius),(0,-radius),
                           (radius,radius),(-radius,radius),(radius,-radius),(-radius,-radius)]:
                nx, ny = ox+dx, oy+dy
                cand = (nx+ex[0], nx+ex[1], ny+ex[2], ny+ex[3])
                if fits(ref, cand, placed_boxes):
                    found = (nx, ny, cand); break
            if found: break
        if found:
            nx, ny, cand = found
            f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(nx), pcbnew.FromMM(ny)))
            placed_boxes[ref] = cand
            moved.append(f"{ref} -> ({nx:.1f}, {ny:.1f})")
    if moved:
        print(f"nudged {len(moved)}: " + ", ".join(moved))

    boxes = {f.GetReference(): box(f) for f in fps}
    problems = []
    for ref, bx in boxes.items():
        if bx[0] < MARGIN or bx[1] > W-MARGIN or bx[2] < MARGIN or bx[3] > H-MARGIN:
            problems.append(f"off-board/at-edge: {ref} "
                            f"x {bx[0]:.1f}..{bx[1]:.1f} y {bx[2]:.1f}..{bx[3]:.1f}")
    for (r1, b1), (r2, b2) in itertools.combinations(boxes.items(), 2):
        if overlap(b1, b2, tol=0.05):
            problems.append(f"overlap: {r1} / {r2}")
    # nothing may sit inside U3's antenna keepout
    u3 = b.FindFootprintByReference("U3"); o = u3.GetPosition()
    ko = (o.x/1e6+U3_KEEPOUT[0], o.x/1e6+U3_KEEPOUT[1],
          o.y/1e6+U3_KEEPOUT[2], o.y/1e6+U3_KEEPOUT[3])
    for ref, bx in boxes.items():
        if ref != "U3" and overlap(bx, ko, tol=0.05):
            problems.append(f"inside antenna keepout: {ref}")

    b.Save(BOARD)
    print(f"placed {len(PLACE)}/{len(fps)} footprints on a {W:.0f}x{H:.0f} mm board")
    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems: print("  " + p)
        return 1
    print("no overlaps, nothing off-board, antenna keepout clear")
    return 0

if __name__ == "__main__":
    sys.exit(main())
