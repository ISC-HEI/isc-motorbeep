#!/usr/bin/env python3
"""Price the BOM against the local JLCPCB catalog.

Reads doc/isc-motorbeep-bom.csv, asks the KiCAD-MCP-Server's offline JLCPCB
database for each line, and writes a Markdown table with real LCSC part
numbers, unit prices and stock. Every figure is traceable to an LCSC code —
nothing is estimated. Re-run after `download_jlcpcb_database` to refresh.

    python tools/price_bom.py            # prints the Markdown table
"""
import csv, json, re, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRV  = ROOT / "tools" / "kicad-mcp-server"
BOM  = ROOT / "doc" / "isc-motorbeep-bom.csv"

# BOM value -> (JLCPCB query, package filter). Keyed on the Value column so the
# mapping stays readable; passives are matched on value + package.
Q = {
    "ESP32-WROOM-32E": ("ESP32-WROOM-32E", None),
    "TPS63001":        ("TPS63001", None),
    "STSPIN220":       ("STSPIN220", None),
    "MAX98357A":       ("MAX98357A", None),
    "CP2102N":         ("CP2102N", None),
    "USBLC6-2SC6":     ("USBLC6-2SC6", None),
    "BSS138":          ("BSS138", "SOT-23"),
    "MMBT3904":        ("MMBT3904", "SOT-23"),
    "MBR0520":         ("MBR0520 schottky", "SOD-123"),
    "2.2uH":           ("2.2uH power inductor", None),
    "green":           ("green LED 0603", "0603"),
    "USB-C":           ("Type-C 16P connector", None),
    "0.33":            ("330mΩ 1206", None),
}
PASSIVE_PKG = {"Resistor_SMD:R_0603_1608Metric": ("0603", "resistor"),
               "Resistor_SMD:R_1206_3216Metric": ("1206", "resistor"),
               "Capacitor_SMD:C_0603_1608Metric": ("0603", "capacitor"),
               "Capacitor_SMD:C_0805_2012Metric": ("0805", "capacitor"),
               "Capacitor_SMD:C_1210_3225Metric": ("1210", "capacitor")}
SKIP = {"8R 1W (off-board)"}   # not a board part
MECH = {"3x AA", "GPIO header", "Stepper 1", "Stepper 2", "Speaker 4-8R",
        "BOOT", "RESET", "USER"}   # generic mechanical, priced as a class

def rows():
    with open(BOM) as f:
        for r in csv.DictReader(f):
            yield r

def query_for(r):
    v, fp = r["Value"], r["Footprint"]
    if v in SKIP: return None
    if v in Q: return Q[v][0], Q[v][1]
    if fp in PASSIVE_PKG:
        pkg, kind = PASSIVE_PKG[fp]
        return f"{v} {kind} {pkg}", pkg
    if "PinHeader_1x" in fp:
        # JLCPCB sells 2.54 mm headers as a 1x40 strip you cut to length; all
        # five headers here total 20 pins, so it is one strip, counted once.
        return "1x40P 2.54mm pin header", None
    if "SW_SPST" in fp: return "tactile switch SMD", None
    return v, None

def main():
    calls, meta = [], []
    for r in rows():
        q = query_for(r)
        if q is None:
            meta.append((r, None)); continue
        args = {"query": q[0], "limit": 8}
        if q[1]: args["package"] = q[1]
        calls.append({"tool": "search_jlcpcb_parts", "args": args})
        meta.append((r, len(calls) - 1))

    tmp = ROOT / ".price_batch.json"
    tmp.write_text(json.dumps(calls))
    out = subprocess.run(["node", "kmcp.mjs", "batch", str(tmp)],
                         cwd=SRV, capture_output=True, text=True, timeout=1800).stdout
    tmp.unlink(missing_ok=True)
    blocks = re.split(r"^--- \[\d+\] .*?---$", out, flags=re.M)[1:]

    PAT = re.compile(r"(C\d+): (.+?) - .*?\$([\d.]+)/ea \((\d+) in stock\)")
    lines, total, unpriced, seen_pooled = [], 0.0, [], set()
    for r, idx in meta:
        qty = int(r["QUANTITY"])
        ref, val, fp = r["Reference"], r["Value"], r["Footprint"]
        pkg = fp.split(":")[-1] if fp else "—"
        hit = None
        if idx is not None and idx < len(blocks):
            m = PAT.findall(blocks[idx])
            if m:
                # Cheapest *sourceable* part: a 13-in-stock line item is not a
                # real price. Prefer anything with healthy stock, then price.
                stocked = [x for x in m if int(x[3]) >= 500] or m
                hit = min(stocked, key=lambda x: float(x[2]))
        if hit:
            lcsc, _desc, price, stock = hit
            pooled = "PinHeader_1x" in fp
            if pooled and lcsc in seen_pooled:
                lines.append(f"| `{ref}` | {val} | {pkg} | [{lcsc}](https://jlcpcb.com/partdetail/{lcsc[1:]}) | {qty} | — | *(same strip)* | {int(stock):,} |")
                continue
            if pooled: seen_pooled.add(lcsc)
            line = (1 if pooled else qty) * float(price)
            total += line
            lines.append(f"| `{ref}` | {val} | {pkg} | [{lcsc}](https://jlcpcb.com/partdetail/{lcsc[1:]}) | {qty} | {float(price):.4f} | **{line:.2f}** | {int(stock):,} |")
        else:
            unpriced.append(f"{ref} ({val})")
            lines.append(f"| `{ref}` | {val} | {pkg} | — | {qty} | — | — | — |")

    print("| Ref | Value | Package | LCSC | Qty | Unit $ | Line $ | Stock |")
    print("|---|---|---|---|---:|---:|---:|---:|")
    print("\n".join(lines))
    print(f"\n**Total (1 board, parts only): ${total:.2f}**")
    if unpriced:
        print(f"\nNot matched automatically: {', '.join(unpriced)}", file=sys.stderr)

if __name__ == "__main__":
    main()
