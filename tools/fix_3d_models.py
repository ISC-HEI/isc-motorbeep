#!/usr/bin/env python3
"""Point the four unresolved 3D models at equivalent bodies, for rendering only.

The KiCad 9.0.9 packages3D library ships no STEP for these four footprints. The
substitutes below have the same package body and pin count, so the render is
faithful; only the exposed-pad dimension differs, and that is hidden under the
part. THIS CHANGES NOTHING ELECTRICAL -- pads, courtyards and nets are
untouched, it only swaps the decorative (model ...) path.

The EP mismatch is itself informative: the library ships QFN-16 3x3 in
EP1.7 and EP1.8 but not the EP1.45 this design currently specifies, which is
weak evidence for the open question in doc/DESIGN.md 8.6 about the real
exposed-pad size. It is not strong enough to change the footprint -- that stays
a datasheet check.
"""
import pathlib, re, sys

BOARD = pathlib.Path("/home/pmudry/git/cad-demo/hardware/isc-motorbeep/isc-motorbeep.kicad_pcb")
SUBS = {
    "Connector_USB.3dshapes/USB_C_Receptacle_G-Switch_GT-USB-7010ASV.step":
        "Connector_USB.3dshapes/USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.step",
    "Package_DFN_QFN.3dshapes/QFN-16-1EP_3x3mm_P0.5mm_EP1.45x1.45mm.step":
        "Package_DFN_QFN.3dshapes/QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm.step",
    "Package_DFN_QFN.3dshapes/QFN-24-1EP_4x4mm_P0.5mm_EP2.15x2.15mm.step":
        "Package_DFN_QFN.3dshapes/QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm.step",
    "Package_SON.3dshapes/Texas_DRC0010J.step":
        "Package_SON.3dshapes/VSON-10-1EP_3x3mm_P0.5mm_EP1.65x2.4mm.step",
}

def main():
    t = BOARD.read_text(); n = 0
    for old, new in SUBS.items():
        t, k = re.subn(re.escape(old), new, t)
        print(f"  {k:2d}x  {old.split('/')[-1]}  ->  {new.split('/')[-1]}")
        n += k
    BOARD.write_text(t)
    print(f"{n} model reference(s) repointed (visual only)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
