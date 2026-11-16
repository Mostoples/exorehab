"""ExoRehab — assemble the real 3D-printed hand exoskeleton parts (blender/parts/*.stl, from 3dstl/*.3mf)
onto an MPFB (MakeHuman, CC0) mannequin and render it.

Requires the MPFB extension (run Blender WITHOUT --factory-startup):
  blender -b -P blender/exo_mannequin.py -- --theme dark --cam hand --still out.png
  blender -b -P blender/exo_mannequin.py -- --theme dark --cam hand --anim out_dir/ --frames 144
Part axes (from the STL files): finger/thumb: Z = finger axis (+Z proximal), hinges on X.
Hand plate: flat in XY, hooks on +Z (outside), +Y = knuckle end, thumb hook on -X.
"""
import bpy, bmesh, addon_utils, math, sys, os, json, argparse
from mathutils import Vector, Matrix, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--theme", default="dark"); ap.add_argument("--cam", default="hand")
ap.add_argument("--still"); ap.add_argument("--anim"); ap.add_argument("--frames", type=int, default=144)
ap.add_argument("--res", default="1920x1080"); ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--flip-dorsal", action="store_true"); ap.add_argument("--blend")
ap.add_argument("--transparent", action="store_true")
ap.add_argument("--grip", type=float, default=0.0)
A = ap.parse_args(argv)
DARK = A.theme == "dark"
HERE = os.path.dirname(os.path.abspath(__file__))
SIDE = "L"

addon_utils.enable("bl_ext.blender_org.mpfb", default_set=True)
from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.targetservice import TargetService

for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
S = bpy.context.scene

# ---------------- materials ----------------
def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)
BLUE, SKY, INK = hexc("2F7BFF"), hexc("8CC6FF"), hexc("16233F")

def mat(name, base, rough=0.4, metal=0.0, emit=None, estr=0.0, coat=0.0, sss=0.0):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = base; b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat: b.inputs["Coat Weight"].default_value = coat
    if sss: b.inputs["Subsurface Weight"].default_value = sss
    if emit: b.inputs["Emission Color"].default_value = emit; b.inputs["Emission Strength"].default_value = estr
    return m
MAT = {
    "body": mat("mannequin", hexc("18223F") if DARK else hexc("A9B7CE"), 0.5, coat=0.15),
    "print": mat("petg_white", hexc("F2F5FA"), 0.33, coat=0.4),
    "plate": mat("petg_blue", BLUE, 0.3, coat=0.5, emit=BLUE, estr=0.15),
    "strap": mat("strap", hexc("111A33") if DARK else hexc("2A3756"), 0.75),
    "elastic": mat("elastic", SKY if DARK else hexc("1646D6"), 0.3, emit=BLUE, estr=3.0 if DARK else 0.6),
    "glow": mat("glow", BLUE, 0.2, emit=BLUE, estr=6.0 if DARK else 2.5),
    "glow2": mat("glow2", SKY, 0.2, emit=SKY, estr=3.5 if DARK else 1.2),
    "shirt": mat("shirt", hexc("9FB0CC") if DARK else hexc("FFFFFF"), 0.9),
    "pants": mat("pants", hexc("0E1630") if DARK else hexc("2A3756"), 0.8),
    "shoes": mat("shoes", hexc("F2F5FA"), 0.45, coat=0.3),
    "floor": mat("floor", hexc("0A1328") if DARK else hexc("DCE5F1"), 0.25, coat=0.3),
}

# ---------------- mannequin ----------------
macro = TargetService.get_default_macro_info_dict(); macro.update(gender=0.9, muscle=0.55, weight=0.5)
human = HumanService.create_human(feet_on_ground=True, scale=0.1, macro_detail_dict=macro)
rig = HumanService.add_builtin_rig(human, "default")
human.data.materials.clear(); human.data.materials.append(MAT["body"])

# clothing: separate shells cut from the body by geometry, so the mannequin wears a short-sleeve tee,
# trousers and shoes (forearms and hands stay bare for the orthosis)
def bhead(n, alt=None):
    bb = rig.data.bones.get(n) or (rig.data.bones.get(alt) if alt else None)
    return bb.head_local.copy() if bb else None
hip_z = (bhead("pelvis.L", "root") or Vector((0, 0, 0.95))).z
neck_z = (bhead("neck01") or Vector((0, 0, 1.45))).z
sh_l = bhead("upperarm01.L"); el_l = bhead("lowerarm01.L")
ank_z = (bhead("foot.L") or Vector((0, 0, 0.09))).z
body_g = human.vertex_groups.get("body")
def in_body(v): return body_g is None or any(g.group == body_g.index and g.weight > 0.5 for g in v.groups)
def sleeve_t(co):  # 0 at shoulder joint → 1 at elbow, for either arm
    sh = Vector((abs(sh_l.x), sh_l.y, sh_l.z)); el = Vector((abs(el_l.x), el_l.y, el_l.z))
    c = Vector((abs(co.x), co.y, co.z)); ax = el - sh
    return (c - sh).dot(ax) / ax.length_squared
ARMG = {g.index for g in human.vertex_groups if g.name.startswith(("upperarm", "lowerarm", "wrist", "finger", "hand", "metacarpal"))}
ARMV = {v.index for v in human.data.vertices if sum(g.weight for g in v.groups if g.group in ARMG) > 0.3}
def garment(name, m, push, thick, cuts, drop=lambda co: False, no_arms=False):
    """cuts: list of (point, normal, arm_only) — geometry on the far side of normal is removed."""
    o = human.copy(); o.data = human.data.copy(); o.name = name; S.collection.objects.link(o)
    for md in list(o.modifiers):
        if md.type != "ARMATURE": o.modifiers.remove(md)
    bm = bmesh.new(); bm.from_mesh(o.data)
    dl = bm.verts.layers.deform.verify()
    if no_arms: bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index in ARMV], context="VERTS")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if body_g is not None and v[dl].get(body_g.index, 0) < 0.5], context="VERTS")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if drop(v.co)], context="VERTS")
    for p, n, arm_only in cuts:
        p, n = Vector(p), Vector(n).normalized()
        isarm = lambda v: sum(v[dl].get(g, 0.0) for g in ARMG) > 0.5 and v.co.x * p.x > 0
        sel = [v for v in bm.verts if (not arm_only or isarm(v))]
        geom = list(set(sel) | {e for v in sel for e in v.link_edges} | {f for v in sel for f in v.link_faces})
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=p, plane_no=n, dist=1e-5)
        bm.verts.ensure_lookup_table()
        far = [v for v in bm.verts if (v.co - p).dot(n) > 1e-5 and (not arm_only or isarm(v))]
        bmesh.ops.delete(bm, geom=far, context="VERTS")
    print("GARMENT", name, len(bm.verts), "arm-verts", sum(1 for v in bm.verts if abs(v.co.x) > 0.2), "z-range", round(min(v.co.z for v in bm.verts),3), round(max(v.co.z for v in bm.verts),3))
    bm.to_mesh(o.data); bm.free()
    o.data.materials.clear(); o.data.materials.append(MAT[m])
    for pp in o.data.polygons: pp.use_smooth = True
    d = o.modifiers.new("push", "DISPLACE"); d.strength = push; d.mid_level = 0
    so = o.modifiers.new("sol", "SOLIDIFY"); so.thickness = thick; so.offset = 1
    sb = o.modifiers.new("sub", "SUBSURF"); sb.levels = 1; sb.render_levels = 2
    return o
print("LANDMARKS hip", round(hip_z,3), "neck", round(neck_z,3), "ank", round(ank_z,3), "sh", tuple(round(x,3) for x in sh_l), "el", tuple(round(x,3) for x in el_l), "pelvis", [bn.name for bn in rig.data.bones if "pelvis" in bn.name or bn.name in ("root","spine05","spine01","neck01")])
def sleeve_cut(sign):
    sh = Vector((sign * abs(sh_l.x), sh_l.y, sh_l.z)); el = Vector((sign * abs(el_l.x), el_l.y, el_l.z))
    return (sh + (el - sh) * 0.42, el - sh, True)
garment("tee", "shirt", 0.006, 0.003,
        [((0, 0, hip_z - 0.05), (0, 0, -1), False), ((0, 0, neck_z - 0.03), (0, 0, 1), False), sleeve_cut(1), sleeve_cut(-1)])
garment("trousers", "pants", 0.005, 0.003,
        [((0, 0, hip_z - 0.02), (0, 0, 1), False), ((0, 0, ank_z + 0.05), (0, 0, -1), False)], no_arms=True)
garment("shoes", "shoes", 0.006, 0.004, [((0, 0, ank_z + 0.06), (0, 0, 1), False)], no_arms=True)
for p in human.data.polygons: p.use_smooth = True
sub = human.modifiers.new("sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 2
PB = rig.pose.bones
def b(n): return PB[f"{n}.{SIDE}"]
def W(v): return rig.matrix_world @ v
def upd(): bpy.context.view_layer.update()

# pose: raise forearm so the hand is presented in front of the body, palm down
def rot(n, axis, deg):
    pb = b(n); pb.rotation_mode = "XYZ"; setattr(pb.rotation_euler, axis, getattr(pb.rotation_euler, axis) + math.radians(deg))
rot("upperarm01", "x", 0); upd()

# rest-pose finger curl → palm direction
def head(n): return W(b(n).head)
def tail(n): return W(b(n).tail)
palm = Vector()
for f in (2, 3, 4, 5):
    d1 = (tail(f"finger{f}-1") - head(f"finger{f}-1")).normalized()
    d3 = (tail(f"finger{f}-3") - head(f"finger{f}-3")).normalized()
    palm += d3 - d1
# straighten fingers (orthosis holds them extended)
for f in (1, 2, 3, 4, 5):
    for k in ((3,) if f == 1 else (2, 3)):
        pb, par = b(f"finger{f}-{k}"), b(f"finger{f}-{k - 1}")
        M = par.matrix.copy(); M.translation = par.tail; pb.matrix = M; upd()

wrist = head("wrist")
knuck = sum((head(f"finger{f}-1") for f in (2, 3, 4, 5)), Vector()) / 4
along = (knuck - wrist).normalized()
radial = (head("finger2-1") - head("finger5-1")); radial = (radial - radial.dot(along) * along).normalized()
dorsal = along.cross(radial).normalized()
palm = palm - palm.dot(along) * along
if palm.length > 1e-6 and dorsal.dot(palm) > 0: dorsal = -dorsal
if A.flip_dorsal: dorsal = -dorsal
radial = dorsal.cross(along).normalized() * (1 if dorsal.cross(along).dot(radial) > 0 else -1)
print("FRAME along", along[:], "dorsal", dorsal[:], "radial", radial[:])

# ---------------- parts ----------------
def import_part(name):
    bpy.ops.wm.stl_import(filepath=os.path.join(HERE, "parts", f"{name}.stl"), global_scale=0.001)
    o = bpy.context.selected_objects[0]; o.name = name
    o.data.transform(Matrix.Diagonal(tuple(o.scale) + (1,)))  # bake importer scale into the mesh
    o.scale = (1, 1, 1)
    if max(o.dimensions) > 1.0: o.data.transform(Matrix.Scale(0.001, 4))  # still in mm → m
    print("PART", name, [round(x * 1000, 1) for x in o.dimensions])
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS"); o.location = (0, 0, 0)
    for p in o.data.polygons: p.use_smooth = False
    o.modifiers.new("wn", "WEIGHTED_NORMAL") if hasattr(bpy.types, "WeightedNormalModifier") else None
    return o

def frame(z_dir, y_dir):  # rotation whose +Z = z_dir, +Y = y_dir (orthonormalised)
    z = z_dir.normalized(); y = (y_dir - y_dir.dot(z) * z).normalized(); x = y.cross(z)
    return Matrix((x, y, z)).transposed().to_4x4()

finger_src = import_part("finger"); thumb_src = import_part("thumb")
PARTS = []
WIDTH = {2: 1.0, 3: 1.04, 4: 0.97, 5: 0.86}
for f in (2, 3, 4, 5):
    H, E = head(f"finger{f}-1"), tail(f"finger{f}-3")
    L = (E - H).length; ax = (E - H).normalized()
    o = finger_src.copy(); o.data = finger_src.data; S.collection.objects.link(o)
    sz = L * 0.97 / 0.088; sw = WIDTH[f] * min(1.05, max(0.8, sz))
    o.matrix_world = Matrix.Translation((H + E) / 2 + dorsal * 0.001) @ frame(-ax, dorsal) @ Matrix.Diagonal((sw, sw, sz, 1))
    o.data.materials.append(MAT["print"]) if not o.data.materials else None
    PARTS.append((f, o, sz, sw))
finger_src.hide_render = finger_src.hide_viewport = True
H, E = head("finger1-2"), tail("finger1-3")
tax = (E - H).normalized()
tdorsal = (dorsal * 0.35 + radial * 0.94); tdorsal = (tdorsal - tdorsal.dot(tax) * tax).normalized()
st = (E - H).length * 1.0 / 0.0464
thumb_src.matrix_world = Matrix.Translation((H + E) / 2) @ frame(-tax, tdorsal) @ Matrix.Diagonal((0.95, 0.95, st, 1))
thumb_src.data.materials.append(MAT["print"])

def split_to_bones(o, cuts, bones, tag):
    """Cut a placed print-in-place part at the joint planes (part-local z) and parent each piece to its bone."""
    Mw = o.matrix_world.copy(); segs = []
    bounds = [None] + sorted(cuts) + [None]  # ascending local z: distal (-z) … proximal (+z)
    for i, bone in enumerate(bones):  # bones ordered distal → proximal
        lo, hi = bounds[i], bounds[i + 1]
        me = o.data.copy(); bm = bmesh.new(); bm.from_mesh(me)
        for z, keep_above in ((lo, True), (hi, False)):
            if z is None: continue
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, z), plane_no=(0, 0, 1), dist=1e-6)
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if (v.co.z < z - 1e-6 if keep_above else v.co.z > z + 1e-6)], context="VERTS")
        bm.to_mesh(me); bm.free()
        seg = bpy.data.objects.new(f"{tag}_{bone}", me); S.collection.objects.link(seg)
        seg.parent = rig; seg.parent_type = "BONE"; seg.parent_bone = f"{bone}.{SIDE}"
        upd(); seg.matrix_world = Mw; segs.append(seg)
    o.hide_render = o.hide_viewport = True
    return segs
SEGS = {}
for f, o, sz, sw in PARTS:
    inv = o.matrix_world.inverted()
    cuts = [(inv @ head(f"finger{f}-{k}")).z for k in (2, 3)]
    SEGS[f] = split_to_bones(o, cuts, [f"finger{f}-3", f"finger{f}-2", f"finger{f}-1"], f"ring{f}")
inv = thumb_src.matrix_world.inverted()
SEGS[1] = split_to_bones(thumb_src, [(inv @ head("finger1-3")).z], ["finger1-3", "finger1-2"], "ring1")

# hand plate, "thermoformed": a dense proxy grid is shrinkwrapped to the hand and the plate follows it via Surface Deform
plate = import_part("hand_heated_part"); plate.data.materials.append(MAT["plate"])
x_plate = along.cross(dorsal)  # plate +X for a proper rotation (+Y along, +Z dorsal)
mirror = x_plate.dot(radial) > 0  # thumb hook sits at plate -X → must face radial side
if mirror:
    for v in plate.data.vertices: v.co.x = -v.co.x
    plate.data.flip_normals(); plate.data.update()
center = knuck - along * 0.068 + dorsal * 0.03
plate.matrix_world = Matrix.Translation(center) @ frame(dorsal, along)
# frame(z=dorsal, y=along): x = along × dorsal = x_plate ✓
bpy.ops.mesh.primitive_grid_add(x_subdivisions=48, y_subdivisions=72, size=1.0)
grid = bpy.context.active_object; grid.name = "plate_proxy"
grid.matrix_world = plate.matrix_world @ Matrix.Translation((0, 0, -0.004)) @ Matrix.Diagonal((0.104, 0.164, 1, 1))
upd()
sd = plate.modifiers.new("sd", "SURFACE_DEFORM"); sd.target = grid
with bpy.context.temp_override(object=plate, active_object=plate, selected_objects=[plate], selected_editable_objects=[plate]):
    bpy.ops.object.surfacedeform_bind(modifier="sd")
sw_ = grid.modifiers.new("wrap", "SHRINKWRAP"); sw_.target = human
sw_.wrap_method = "NEAREST_SURFACEPOINT"; sw_.wrap_mode = "OUTSIDE_SURFACE"; sw_.offset = 0.0035
sm = grid.modifiers.new("smooth", "SMOOTH"); sm.factor = 0.6; sm.iterations = 6
grid.hide_render = True; grid.display_type = "WIRE"
upd()

# hook positions after forming (plate local mm → nearest vertex index → evaluated world position)
HOOKS = {"index": (-23.5, 72), "middle": (-4, 75), "ring": (15.5, 73), "pinky": (34, 68), "thumb": (-25, -24)}
dg = bpy.context.evaluated_depsgraph_get()
pe = plate.evaluated_get(dg); pm = pe.to_mesh()
def hook_world(xmm, ymm):
    xmm = -xmm if mirror else xmm
    target = Vector((xmm / 1000, ymm / 1000, 0.0038)); best = min(range(len(plate.data.vertices)), key=lambda i: (plate.data.vertices[i].co - target).length)
    return plate.matrix_world @ pm.vertices[best].co
HW = {k: hook_world(*v) for k, v in HOOKS.items()}
pe.to_mesh_clear()

def aim(o, p0, p1):
    d = p1 - p0; o.location = (p0 + p1) / 2
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); o.scale = (1, 1, d.length)
def rod(p0, p1, r, m, name="rod"):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=1.0, vertices=12)
    o = bpy.context.active_object; o.name = name; o.data.materials.append(MAT[m])
    for p in o.data.polygons: p.use_smooth = True
    aim(o, p0, p1); return o
# elastic bands: hook → dorsal tab of each distal ring
TAB = {f: Vector((0, 0.019, -0.036)) for f in (2, 3, 4, 5)}; TAB[1] = Vector((0, 0.016, -0.018))
RODS = []
for f, key in zip((2, 3, 4, 5, 1), ("index", "middle", "ring", "pinky", "thumb")):
    dist = SEGS[f][0]
    RODS.append((rod(HW[key], dist.matrix_world @ TAB[f], 0.0011, "elastic", f"elastic_{key}"), HW[key], dist, TAB[f]))

# finger flexion: find the sign of local-X rotation that curls toward the palm
FB = [f"finger{f}-{k}" for f in (1, 2, 3, 4, 5) for k in (1, 2, 3)]
BASEQ = {}
for n in FB:
    b(n).rotation_mode = "QUATERNION"; BASEQ[n] = b(n).rotation_quaternion.copy()
t0 = tail("finger3-3"); b("finger3-2").rotation_quaternion = BASEQ["finger3-2"] @ Quaternion((1, 0, 0), math.radians(30)); upd()
FLEX = 1 if (tail("finger3-3") - t0).dot(dorsal) < 0 else -1
b("finger3-2").rotation_quaternion = BASEQ["finger3-2"]; upd()
print("FLEX sign", FLEX)
CURL = {1: (0, 18, 32), 2: (48, 70, 40), 3: (52, 74, 42), 4: (55, 76, 44), 5: (58, 78, 46)}
def flex(g):
    for f, (a1, a2, a3) in CURL.items():
        for k, a in zip((1, 2, 3), (a1, a2, a3)):
            n = f"finger{f}-{k}"
            if n == "finger1-1": continue
            b(n).rotation_quaternion = BASEQ[n] @ Quaternion((1, 0, 0), FLEX * math.radians(a * g))
    upd()
    for o, p0, dist, tab in RODS: aim(o, p0, dist.matrix_world @ tab)

# straps: open tubes shrinkwrapped around wrist and palm + the printed clip
def strap(c, axis, r, w, name):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=w, vertices=96, end_fill_type="NOTHING", location=c)
    o = bpy.context.active_object; o.name = name
    o.rotation_euler = axis.to_track_quat("Z", "Y").to_euler(); o.data.materials.append(MAT["strap"])
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.subdivide(number_cuts=3); bpy.ops.object.mode_set(mode="OBJECT")
    s = o.modifiers.new("wrap", "SHRINKWRAP"); s.target = human; s.wrap_method = "NEAREST_SURFACEPOINT"; s.wrap_mode = "OUTSIDE_SURFACE"; s.offset = 0.0075
    so = o.modifiers.new("sol", "SOLIDIFY"); so.thickness = 0.0022; so.offset = 1
    o.modifiers.new("sub", "SUBSURF").render_levels = 1
    for p in o.data.polygons: p.use_smooth = True
    return o
wpt = wrist - along * 0.045
strap(wpt, along, 0.06, 0.024, "strap_wrist")
strap(knuck - along * 0.035, along, 0.07, 0.022, "strap_palm")
clip = import_part("strap"); clip.data.materials.append(MAT["print"])
clip.matrix_world = Matrix.Translation(wpt + dorsal * 0.0) @ frame(along, dorsal)
upd()
# move clip onto the evaluated wrist-strap surface on the ulnar side
ws = bpy.data.objects["strap_wrist"].evaluated_get(bpy.context.evaluated_depsgraph_get())
pts = [ws.matrix_world @ v.co for v in ws.data.vertices]
side = max(pts, key=lambda p: (p - wpt).dot(-radial * 0.8 + dorsal * 0.6))
clip.matrix_world = Matrix.Translation(side + (side - wpt).normalized() * 0.004) @ frame((side - wpt).normalized(), along)

# ---------------- stage ----------------
feet = min((W(v.co).z for v in human.data.vertices[:2000]), default=0)
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0)); fl = bpy.context.active_object; fl.data.materials.append(MAT["floor"])
if not DARK: fl.is_shadow_catcher = True
for r in ((0.45, 0.8) if DARK else ()):
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.004, major_segments=192, location=(0, 0, 0.003))
    t = bpy.context.active_object; t.scale.z = 0.15; t.data.materials.append(MAT["glow"])
HAND_C = (wrist + knuck) / 2 + dorsal * 0.01
RINGS = []
for off, r in (((-0.22, 0.10, 0.12), 0.09), ((0.18, 0.25, -0.08), 0.06), ((0.05, 0.55, 0.30), 0.13)):
    loc = HAND_C + radial * off[0] + Vector((0, off[1], off[2]))
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.0035, major_segments=160, location=loc, rotation=(math.radians(80), 0, math.radians(20)))
    o = bpy.context.active_object; o.data.materials.append(MAT["glow"]); RINGS.append(o)
import random; random.seed(3); DOTS = []
for i in range(40):
    p = HAND_C + Vector((random.uniform(-0.6, 0.6), random.uniform(-0.1, 1.2), random.uniform(-0.5, 0.5)))
    if (p - HAND_C).length < 0.12: continue
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0035, segments=12, ring_count=8, location=p)
    o = bpy.context.active_object; o.data.materials.append(MAT["glow2"]); DOTS.append((o, p.copy(), random.uniform(0, 6.28)))

W_ = bpy.data.worlds.new("w"); S.world = W_
try: W_.use_nodes = True
except Exception: pass
W_.node_tree.nodes["Background"].inputs["Color"].default_value = hexc("070D1F") if DARK else hexc("E9EFF7")
W_.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0 if DARK else 0.45

def light(kind, loc, energy, color=(1, 1, 1), size=1.0, target=None):
    d = bpy.data.lights.new(kind + str(len(bpy.data.lights)), kind); d.energy = energy; d.color = color[:3]
    if kind == "AREA": d.size = size
    o = bpy.data.objects.new(d.name, d); S.collection.objects.link(o); o.location = loc
    o.visible_camera = False; o.visible_glossy = kind != "AREA" or energy < 300
    o.rotation_euler = (Vector(target or HAND_C) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o
k = 1.0 if DARK else 0.7
light("AREA", HAND_C + Vector((-0.6, -1.4, 1.2)), 110 * k, (1, 0.98, 0.96), 1.4)
light("AREA", HAND_C + Vector((1.0, 0.9, 0.6)), 260 * k, SKY, 0.8)
light("AREA", HAND_C + Vector((0.3, -1.0, -0.5)), 20 * k, (1, 1, 1), 1.5)
light("POINT", HAND_C + dorsal * 0.12, 3 * k, BLUE)

cd = bpy.data.cameras.new("cam"); cd.dof.use_dof = True
CAM = bpy.data.objects.new("cam", cd); S.collection.objects.link(CAM); S.camera = CAM
TGT = bpy.data.objects.new("tgt", None); S.collection.objects.link(TGT); cd.dof.focus_object = TGT
VIEWS = {  # (distance vector in hand frame: dorsal, radial, along, world-z), lens, fstop, target shift along
    "hand":   ((0.30, 0.10, -0.13, 0.06), 70, 3.5, 0.0),
    "detail": ((0.18, -0.06, 0.04, 0.03), 85, 2.8, 0.03),
    "wide":   ((0.85, 0.35, -0.55, 0.15), 40, 5.6, -0.05),
    "top":    ((0.40, 0.0, 0.0, 0.0), 60, 8.0, 0.0),
}
vec, cd.lens, cd.dof.aperture_fstop, tshift = VIEWS.get(A.cam, VIEWS["hand"])
WORLD_CAMS = {"wide": ((1.05, -1.45, 1.12), (0.28, -0.1, 0.98), 45, 4.0), "hero": ((0.78, -0.82, 1.06), (0.42, -0.2, 0.99), 55, 2.8)}
def place_cam(t):
    if A.cam in WORLD_CAMS:
        p, tg, cd.lens, cd.dof.aperture_fstop = WORLD_CAMS[A.cam]
        a = 0.18 * math.sin(2 * math.pi * t); P = Vector(p) - Vector(tg)
        P = Matrix.Rotation(a, 4, "Z") @ P
        TGT.location = Vector(tg); CAM.location = TGT.location + P + Vector((0, 0, 0.03 * math.sin(4 * math.pi * t)))
        cd.dof.focus_object = None; cd.dof.focus_distance = (HAND_C - CAM.location).length
        CAM.rotation_euler = (TGT.location - CAM.location).to_track_quat("-Z", "Y").to_euler(); return
    a = 0.22 * math.sin(2 * math.pi * t)
    rd = radial * math.cos(a) + dorsal * math.sin(a) * 0.3
    off = dorsal * vec[0] + rd * vec[1] + along * vec[2] + Vector((0, 0, vec[3]))
    off = Matrix.Rotation(a * 0.6, 4, along) @ off
    TGT.location = HAND_C + along * tshift
    CAM.location = TGT.location + off
    CAM.rotation_euler = (TGT.location - CAM.location).to_track_quat("-Z", "Y").to_euler()

def animate(t):
    flex(0.5 - 0.5 * math.cos(2 * math.pi * t)) if A.anim else flex(A.grip)
    for o, p, ph in DOTS: o.location = p + Vector((0, 0, 0.012 * math.sin(2 * math.pi * t * 2 + ph)))
    for i, r in enumerate(RINGS): r.rotation_euler.z = math.radians(20 + 360 * t * (1 if i % 2 else -1))
    place_cam(t)

S.render.engine = "CYCLES"
pr = bpy.context.preferences.addons["cycles"].preferences; pr.compute_device_type = "OPTIX"; pr.get_devices()
for d in pr.devices: d.use = d.type == "OPTIX"
S.cycles.device = "GPU"; S.cycles.samples = A.samples; S.cycles.use_denoising = True; S.cycles.max_bounces = 6
S.view_settings.view_transform = "Standard"; S.view_settings.exposure = -0.35 if DARK else -0.75
S.render.film_transparent = A.transparent or not DARK
w, h = (int(x) for x in A.res.split("x")); S.render.resolution_x, S.render.resolution_y = w, h
S.render.use_persistent_data = False

if A.blend: bpy.ops.wm.save_as_mainfile(filepath=A.blend)
if A.still:
    animate(0.0); S.render.filepath = A.still; bpy.ops.render.render(write_still=True)
elif A.anim:
    os.makedirs(A.anim, exist_ok=True)
    for f in range(A.frames):
        out = os.path.join(A.anim, f"f_{f:04d}.png")
        if os.path.exists(out): continue
        animate(f / A.frames); S.render.filepath = out; bpy.ops.render.render(write_still=True)
print("MANNEQUIN_DONE mirror=%s" % mirror)
