#!/usr/bin/env bash
# render.sh <sheet-name> — export a sheet to SVG+PNG and print ERC
set -e
HW=/home/pmudry/git/cad-demo/hardware/isc-motorbeep
OUT=/home/pmudry/git/cad-demo/doc/render
S=$1
mkdir -p $OUT
cd /home/pmudry/git/cad-demo/tools/kicad-mcp-server
timeout 300 node kmcp.mjs call export_schematic_svg \
  "{\"schematicPath\":\"$HW/$S.kicad_sch\",\"outputPath\":\"$OUT/$S.svg\"}" >/dev/null
.venv/bin/python -c "
import pymupdf
d=pymupdf.open('$OUT/$S.svg')
pymupdf.open('pdf',d.convert_to_pdf())[0].get_pixmap(dpi=200).save('$OUT/$S.png')
"
echo "--- ERC $S ---"
timeout 300 node kmcp.mjs call run_erc "{\"schematicPath\":\"$HW/$S.kicad_sch\"}" \
  | grep -E "ERC result|\[error\]|\[warning\]" | head -15
