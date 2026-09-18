#!/usr/bin/env python3
"""Print the pins of a KiCad library symbol, resolving (extends ...).
Usage: pins.py Lib:Symbol [Lib:Symbol ...]"""
import re, sys, pathlib
SYMDIR = pathlib.Path("/usr/share/kicad/symbols")

def block(txt, name):
    i = txt.find(f'(symbol "{name}"')
    if i < 0: return None
    d = 0
    for j in range(i, len(txt)):
        if txt[j] == "(": d += 1
        elif txt[j] == ")":
            d -= 1
            if d == 0: return txt[i:j+1]
    return txt[i:]

def pins(lib, name, _seen=()):
    txt = (SYMDIR / f"{lib}.kicad_sym").read_text()
    b = block(txt, name)
    if b is None: return f"!! {lib}:{name} NOT FOUND"
    ext = re.search(r'\(extends "([^"]+)"', b)
    if ext and ext.group(1) not in _seen:
        return pins(lib, ext.group(1), _seen + (name,)) + f"   [via extends {ext.group(1)}]"
    out = []
    for m in re.finditer(
        r'\(pin\s+(\w+)\s+\w+\s*\(at[^)]*\)\s*\(length[^)]*\)\s*'
        r'\(name "([^"]*)"[\s\S]{0,150}?\(number "([^"]*)"', b):
        out.append(f'{m.group(3)}={m.group(2)}[{m.group(1)}]')
    return f"{len(out)} pins: " + "  ".join(out)

for a in sys.argv[1:]:
    lib, name = a.split(":", 1)
    print(f"--- {a} ---\n{pins(lib, name)}\n")
