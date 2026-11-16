"""Merge all glTF animations in a GLB into a single clip (model-viewer plays one animation at a time)."""
import json, struct, sys
path, name = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "grip")
d = open(path, "rb").read()
jl = struct.unpack("<I", d[12:16])[0]; j = json.loads(d[20:20 + jl]); rest = d[20 + jl:]
anims = j.get("animations", [])
merged = {"name": name, "channels": [], "samplers": []}
for a in anims:
    off = len(merged["samplers"]); merged["samplers"] += a["samplers"]
    for c in a["channels"]: c = dict(c); c["sampler"] += off; merged["channels"].append(c)
j["animations"] = [merged]
js = json.dumps(j, separators=(",", ":")).encode(); js += b" " * (-len(js) % 4)
out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + len(rest)) + struct.pack("<II", len(js), 0x4E4F534A) + js + rest
open(path, "wb").write(out)
print("merged", len(anims), "animations ->", len(merged["channels"]), "channels")
