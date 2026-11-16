"""ExoRehab 3D assets — procedural exoskeleton arm scene (Blender 5.x, Cycles).

blender -b --factory-startup -P blender/exo_scene.py -- --theme dark --still out.png [--angle 70]
blender -b --factory-startup -P blender/exo_scene.py -- --theme dark --anim out_dir/ [--frames 120]
"""
import bpy, math, sys, random, argparse
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--theme", default="dark")
ap.add_argument("--still"); ap.add_argument("--anim")
ap.add_argument("--angle", type=float, default=70)
ap.add_argument("--frames", type=int, default=144)
ap.add_argument("--res", default="1920x1080")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--cam", default="hero")
A = ap.parse_args(argv)
DARK = A.theme == "dark"

# ---------- brand palette (linear-ish sRGB inputs) ----------
def hexc(h, a=1.0):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (a,)
BLUE, DEEP, SKY, ICE, INK = hexc("2F7BFF"), hexc("1646D6"), hexc("8CC6FF"), hexc("DDEBFF"), hexc("16233F")
BG = hexc("070D1F") if DARK else hexc("E9EFF7")

# ---------- reset ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene

def mat(name, base, rough=0.4, metal=0.0, emit=None, estr=0.0, coat=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = base
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat: b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = emit
        b.inputs["Emission Strength"].default_value = estr
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m

M = {
    "shell": mat("shell", hexc("F4F7FC"), 0.28, coat=0.6),
    "skin": mat("skin", hexc("2A3756") if DARK else hexc("C9D4E4"), 0.55),
    "rail": mat("rail", hexc("1B2440"), 0.3, 0.6),
    "blue": mat("blue", BLUE, 0.3, emit=BLUE, estr=1.2),
    "glow": mat("glow", BLUE, 0.2, emit=BLUE, estr=7.0 if DARK else 3.0),
    "glow2": mat("glow2", SKY, 0.2, emit=SKY, estr=4.0 if DARK else 1.5),
    "chrome": mat("chrome", hexc("DDE3EE"), 0.12, 1.0),
    "led": mat("led", hexc("19B97A"), 0.3, emit=hexc("19B97A"), estr=25.0),
    "floor": mat("floor", hexc("0A1328") if DARK else hexc("D9E3F0"), 0.22 if DARK else 0.45, coat=0.3),
}

def ghost_mat():
    m = bpy.data.materials.new("ghost")
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (0.82, 0.9, 1, 1)
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = SKY if DARK else BLUE
    em.inputs["Strength"].default_value = 2.2 if DARK else 1.2
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lw.outputs["Facing"], mx.inputs["Fac"])
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m
M["skin"] = ghost_mat()

def smooth(o, sub=2):
    for p in o.data.polygons: p.use_smooth = True
    if sub:
        m = o.modifiers.new("sub", "SUBSURF"); m.levels = sub; m.render_levels = sub
    return o

def add(kind, mat_, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), parent=None, sub=2, **kw):
    getattr(bpy.ops.mesh, f"primitive_{kind}_add")(location=loc, rotation=rot, **kw)
    o = bpy.context.active_object; o.scale = scale
    o.data.materials.append(M[mat_])
    if parent: o.parent = parent
    return smooth(o, sub)

def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None); S.collection.objects.link(e); e.location = loc
    if parent: e.parent = parent
    return e

def rbox(mat_, loc, size, parent=None, bevel=0.012, rot=(0, 0, 0)):
    o = add("cube", mat_, loc, (size[0] / 2, size[1] / 2, size[2] / 2), rot, parent, sub=0)
    b = o.modifiers.new("bev", "BEVEL"); b.width = bevel; b.segments = 5
    return o

# ---------- figure (abstract mannequin, side view facing -Y camera) ----------
ROOT = empty("root", (0, 0, 0))
ELB_Z = 0.62
add("uv_sphere", "skin", (0.0, 0.0, 1.02), (0.075, 0.075, 0.075), parent=ROOT, segments=48, ring_count=24)  # shoulder

add("uv_sphere", "skin", (0.0, 0.0, 0.82), (0.056, 0.056, 0.22), parent=ROOT, segments=48, ring_count=24)  # upper arm

# upper-arm exo: two cuffs, strap, rail, controller pod
def cuff(z, r, h, parent):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r, depth=h, location=(0, 0, z), end_fill_type="NOTHING")
    o = bpy.context.active_object; o.parent = parent; o.data.materials.append(M["shell"])
    so = o.modifiers.new("sol", "SOLIDIFY"); so.thickness = 0.009; so.offset = 1
    bv = o.modifiers.new("bev", "BEVEL"); bv.width = 0.004; bv.segments = 4; bv.limit_method = "ANGLE"
    smooth(o, 0)
    add("torus", "blue", (0, 0, z), (1, 1, 0.55), parent=parent, sub=1, major_radius=r + 0.0095, minor_radius=0.0055, major_segments=64, minor_segments=12)
for z in (0.90, 0.74):
    cuff(z, 0.058, 0.055, ROOT)
rbox("rail", (0.0, -0.072, 0.76), (0.018, 0.014, 0.26), ROOT, 0.006)
pod = rbox("shell", (-0.075, -0.04, 0.86), (0.05, 0.05, 0.085), ROOT, 0.014)
add("uv_sphere", "led", (-0.075, -0.067, 0.885), (0.007, 0.007, 0.007), parent=ROOT, sub=0)
rbox("glow2", (-0.075, -0.066, 0.855), (0.026, 0.002, 0.004), ROOT, 0.001)
for z in (0.80, 0.70):  # sEMG pads
    add("cylinder", "blue", (0.05, -0.03, z), (1, 1, 1), (0, math.radians(70), math.radians(-30)), ROOT, 0, radius=0.011, depth=0.004)

# elbow actuator (lateral side, facing camera)
ELB = empty("elbow", (0, 0, ELB_Z), ROOT)
add("cylinder", "shell", (0, -0.06, ELB_Z), (1, 1, 1), (math.radians(90), 0, 0), ROOT, 1, radius=0.078, depth=0.05, vertices=64)
add("torus", "glow", (0, -0.087, ELB_Z), (1, 1, 1), (math.radians(90), 0, 0), ROOT, 1, major_radius=0.056, minor_radius=0.006, major_segments=96)
add("cylinder", "blue", (0, -0.084, ELB_Z), (1, 1, 1), (math.radians(90), 0, 0), ROOT, 1, radius=0.048, depth=0.008, vertices=64)
add("cylinder", "chrome", (0, -0.09, ELB_Z), (1, 1, 1), (math.radians(90), 0, 0), ROOT, 1, radius=0.018, depth=0.008, vertices=48)
RING = empty("ringdash", (0, -0.091, ELB_Z), ROOT)
for i in range(10):
    a = i / 10 * 2 * math.pi
    rbox("glow2", (0.034 * math.cos(a), 0, 0.034 * math.sin(a)), (0.008, 0.003, 0.003), RING, 0.001, rot=(0, -a, 0))
add("uv_sphere", "skin", (0, 0, ELB_Z), (0.058, 0.058, 0.058), parent=ROOT)

# forearm group (rotates around elbow, local -Z = extended)
FORE = empty("forearm", (0, 0, 0), ELB)
add("uv_sphere", "skin", (0, 0, -0.19), (0.048, 0.048, 0.2), parent=FORE, segments=48, ring_count=24)
rbox("rail", (0, -0.07, -0.12), (0.016, 0.014, 0.2), FORE, 0.006)
cuff(-0.2, 0.05, 0.05, FORE)
# hand + tendon glove
add("uv_sphere", "shell", (0, 0, -0.43), (0.036, 0.05, 0.065), parent=FORE, segments=48, ring_count=24)
add("torus", "blue", (0, 0, -0.385), (0.75, 1, 0.9), parent=FORE, major_radius=0.05, minor_radius=0.009)
for i, dx in enumerate((-0.03, -0.01, 0.01, 0.03)):
    f = add("uv_sphere", "shell", (0.0, dx * 1.1, -0.53 + abs(dx) * 0.5), (0.013, 0.013, 0.05), parent=FORE, sub=1)
    add("cylinder", "glow2", (0.0, dx * 1.1 - 0.0, -0.46), (1, 1, 1), parent=FORE, sub=0, radius=0.0018, depth=0.16)

# ---------- environment ----------
fl = add("plane", "floor", (0, 0, 0.0), (6, 6, 1), sub=0)
# concentric glowing floor rings + floating halo rings (brand blue)
RINGS = []
for r, s in ((0.36, 4.0), (0.62, 1.6)):
    add("torus", "glow", (0, 0, 0.004), (1, 1, 0.15), sub=0, major_radius=r, minor_radius=0.004, major_segments=192)
for loc, r, rot in (((-0.62, 0.55, 1.05), 0.2, (80, 0, 25)), ((0.66, 0.35, 0.72), 0.13, (75, 10, -30)), ((0.95, 1.6, 1.35), 0.24, (85, 0, 10))):
    o = add("torus", "glow", loc, (1, 1, 1), tuple(math.radians(x) for x in rot), sub=0, major_radius=r, minor_radius=0.007, major_segments=160)
    RINGS.append(o)
# light pillars in the back (like data beacons)
random.seed(7)
PILLARS = []
for i in range(9):
    x = random.uniform(-1.6, 1.6); y = random.uniform(0.9, 2.6); h = random.uniform(0.5, 1.4)
    add("cylinder", "shell" if not DARK else "rail", (x, y, h / 2), (1, 1, 1), sub=0, radius=0.012, depth=h)
    add("uv_sphere", "glow2", (x, y, h + 0.02), (0.022, 0.022, 0.022), sub=0)
    add("torus", "glow", (x, y, 0.005), (1, 1, 0.2), sub=0, major_radius=0.09, minor_radius=0.003)
# floating data particles
DOTS = []
for i in range(46):
    p = (random.uniform(-1.3, 1.3), random.uniform(-0.2, 2.0), random.uniform(0.15, 1.5))
    if Vector(p).length < 0.35: continue
    DOTS.append((add("uv_sphere", "glow2", p, (0.006,) * 3, sub=0, segments=12, ring_count=8), p, random.uniform(0, 6.28)))

# world
W = bpy.data.worlds.new("w"); S.world = W
try: W.use_nodes = True
except Exception: pass
W.node_tree.nodes["Background"].inputs["Color"].default_value = BG
W.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0 if DARK else 0.55
if DARK:  # subtle depth haze
    S.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

# lights
def light(kind, loc, energy, color=(1, 1, 1), size=1.0, target=(0, 0, 0.7)):
    d = bpy.data.lights.new(kind + str(len(bpy.data.lights)), kind); d.energy = energy; d.color = color[:3]
    if kind == "AREA": d.size = size
    o = bpy.data.objects.new(d.name, d); S.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o
light("AREA", (-1.4, -1.6, 2.2), 260 if DARK else 150, (1, 0.98, 0.96), 2.2)
light("AREA", (1.6, 0.8, 1.4), 520 if DARK else 160, SKY, 1.0)          # blue rim
light("AREA", (0.2, -1.2, 0.1), 40 if DARK else 25, (1, 1, 1), 2.5)       # fill from below
light("POINT", (0, -0.25, 0.62), 6, BLUE)                                  # actuator spill

# camera
cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 50; cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 2.8
CAM = bpy.data.objects.new("cam", cam_d); S.collection.objects.link(CAM); S.camera = CAM
TGT = empty("tgt", (0.12, 0, 0.7)); cam_d.dof.focus_object = TGT
CAMS = {"hero": (0.7, -1.95, 0.95), "close": (0.42, -0.95, 0.70), "wide": (1.6, -3.0, 1.2), "icon": (0, -2, 0.7)}

def place_cam(t):  # t in 0..1 loop
    base = Vector(CAMS[A.cam]); a = 0.16 * math.sin(2 * math.pi * t)
    rot = Vector((base.x * math.cos(a) - base.y * math.sin(a), base.x * math.sin(a) + base.y * math.cos(a), base.z + 0.04 * math.sin(4 * math.pi * t)))
    CAM.location = rot
    CAM.rotation_euler = (TGT.location - rot).to_track_quat("-Z", "Y").to_euler()

def pose(t, angle=None):
    ang = angle if angle is not None else 18 + 92 * (0.5 - 0.5 * math.cos(2 * math.pi * t * 2))
    # flexion = forearm swings forward (toward -Y? no: toward +X in camera view)
    ELB.rotation_euler = (0, -math.radians(ang), 0)
    RING.rotation_euler = (0, math.radians(360 * t * 2), 0)
    for i, r in enumerate(RINGS):
        r.rotation_euler.z += 0 if angle is not None else 0
    for o, p, ph in DOTS:
        o.location = (p[0], p[1], p[2] + 0.03 * math.sin(2 * math.pi * t * 2 + ph))
    place_cam(t)

# ---------- render settings ----------
S.render.engine = "CYCLES"
pr = bpy.context.preferences.addons["cycles"].preferences
pr.compute_device_type = "OPTIX"; pr.get_devices()
for d in pr.devices: d.use = d.type == "OPTIX"
S.cycles.device = "GPU"; S.cycles.samples = A.samples; S.cycles.use_denoising = True
S.cycles.max_bounces = 6
S.view_settings.view_transform = "Standard"; S.view_settings.exposure = -0.2 if DARK else -0.6
w, h = (int(x) for x in A.res.split("x")); S.render.resolution_x, S.render.resolution_y = w, h
S.render.image_settings.file_format = "PNG"
S.render.use_persistent_data = False

if A.still:
    pose(0.0, A.angle); S.render.filepath = A.still
    bpy.ops.render.render(write_still=True)
elif A.anim:
    import os
    os.makedirs(A.anim, exist_ok=True)
    for f in range(A.frames):
        out = os.path.join(A.anim, f"f_{f:04d}.png")
        if os.path.exists(out): continue
        pose(f / A.frames); S.render.filepath = out
        bpy.ops.render.render(write_still=True)
print("EXO_DONE")
