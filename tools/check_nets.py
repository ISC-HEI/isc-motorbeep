#!/usr/bin/env python3
"""Assert the netlist matches design intent. Exits non-zero on any mismatch."""
import xml.etree.ElementTree as ET, sys
NET = "/home/pmudry/git/cad-demo/doc/isc-motorbeep.net"
nets = {}
for n in ET.parse(NET).getroot().find("nets"):
    nets[n.get("name").lstrip("/")] = {f'{d.get("ref")}-{d.get("pin")}' for d in n.findall("node")}

# net -> pins that MUST be on it (design doc sections 2, 3, 4, 7)
EXPECT = {
  "I2S_BCLK":  {"U3-30","U7-16"},        "I2S_LRCLK": {"U3-31","U7-14"},
  "I2S_DIN":   {"U3-33","U7-1"},         "AUD_SD":    {"U3-36","U7-4","R50-1"},
  "M1_STCK":   {"U3-8","U5-2"},          "M1_DIR":    {"U3-9","U5-1"},
  "M2_STCK":   {"U3-10","U6-2"},         "M2_DIR":    {"U3-11","U6-1"},
  "MOT_STBY":  {"U3-12","U5-14","U6-14","R22-1"},
  "M1_ENP":    {"U5-13","R30-2","R31-1"},"M2_ENP":    {"U6-13","R40-2","R41-1"},
  "MOT_VREF":  {"U5-11","U6-11","R20-2","R21-1"},
  "VBAT_SENSE":{"U3-6","R3-2","R4-1"},   "VBAT_SENSE_EN":{"U3-37","Q1-1"},
  "+3V3":      {"U2-1","U3-2"},
  "+BATT":     {"BT1-1","D2-2","U5-6","U6-6","U7-7"},
  "VSYS":      {"D1-1","D2-1","U2-5","U2-6","R5-1"},
  "EN_MCU":    {"U3-3","R10-2","Q2-3"},  "BOOT":      {"U3-25","R11-2","Q3-3"},
  "UART_TX_ESP":{"U3-35","U4-20"},       "UART_RX_ESP":{"U3-34","U4-21"},
  "USB_DP":    {"J1-A6","U1-3","U4-3"},  "USB_DM":    {"J1-A7","U1-1","U4-4"},
  "CP_VDD":    {"U4-6","U4-5"},          "VBUS":      {"J1-A4","U4-8","U4-7","D1-2"},
}
bad = 0
for net, must in sorted(EXPECT.items()):
    have = nets.get(net)
    if have is None:
        print(f"  MISSING NET  {net}"); bad += 1; continue
    miss = must - have
    print(f"  {'ok  ' if not miss else 'FAIL'} {net:15s} {len(have)} pins" + (f"  missing {sorted(miss)}" if miss else ""))
    bad += bool(miss)
# GPIO12 must carry no signal: KiCad puts a no-connect pin on its own
# "unconnected-(...)" net, so that name is the pass condition, not a failure.
io12 = [n for n, p in nets.items() if "U3-14" in p]
ok12 = len(io12) == 1 and io12[0].startswith("unconnected-")
print(f"  {'ok  ' if ok12 else 'FAIL'} GPIO12 no-connect -> {io12}")
bad += not ok12
# Strapping pins (design doc 8.1): nothing may quietly land on them. A boot
# strap with an extra load is exactly the failure this design is guarding against.
STRAP = {"U3-24": ("IO2  / LED_STATUS", {"U3-24", "R12-1"}),
         "U3-23": ("IO15 / header",     {"U3-23", "J2-2"}),
         "U3-29": ("IO5  / header",     {"U3-29", "J2-1"})}
for pin, (what, exact) in STRAP.items():
    net = next((p for p in nets.values() if pin in p), None)
    ok = net == exact
    print(f"  {'ok  ' if ok else 'FAIL'} strap {what:20s} {sorted(net) if net else 'NO NET'}")
    bad += not ok

print(f"\n{len(nets)} nets total; {bad} problem(s)")
sys.exit(1 if bad else 0)
