"""Ad-hoc verification: ST_PIP declaration still parses as IEC 61131-3 ST (blark) and every
struct member carries a comment.

Run from the repository root:
    .agents/tmp/ptvenv/bin/python .agents/verify_st_pip.py
Exits non-zero if the declaration fails to parse or a member has no comment.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import blark
from blark.transform import StructDeclaration

PATH = Path("L2SIVacuum/DUTs/Pumps/ST_PIP.TcDUT")

decl_text = ET.parse(PATH).getroot().find("DUT/Declaration").text
source = blark.parse_source_code(decl_text)

structs = [item for item in source.items if isinstance(item, StructDeclaration)]
struct = structs[0]
members = struct.declarations
print(f"blark parsed {len(structs)} struct(s); ST_PIP has {len(members)} members")

uncommented = []
for var in members:
    block = var.init
    name = block.name
    vtype = getattr(block.type, "name", block.type)
    meta = var.meta
    comments = []
    for md in meta.get("comments", []):
        text = getattr(md, "text", None) or str(md)
        comments.append(text)
    print(f"  {str(name):16s} {str(vtype):14s} comments={comments}")
    if not comments:
        uncommented.append(name)

print("UNCOMMENTED:", uncommented)
sys.exit(1 if uncommented else 0)
