"""ExoRehab web assets (light studio, transparent PNG with soft shadows):
  parts  — flat-lay of the 3D-printed orthosis parts (blender/parts/*.stl)
  icons  — six brand-style 3D feature icons
blender -b --factory-startup -P blender/exo_assets.py -- parts out.png
blender -b --factory-startup -P blender/exo_assets.py -- icons out_dir/
"""
import bpy, math, sys, os
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
MODE, OUT = argv[0], argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)
BLUE, DEEP, SKY = hexc("2F7BFF"), hexc("1646D6"), hexc("8CC6FF")

def mat(name, base, rough=0.35, metal=0.0, coat=0.4, emit=None, estr=0.0):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = base; p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal; p.inputs["Coat Weight"].default_value = coat
    if emit: p.inputs["Emission Color"].default_value = emit; p.inputs["Emission Strength"].default_value = estr
    return m
M = {"white": mat("white", hexc("F4F7FC"), 0.3), "blue": mat("blue", BLUE, 0.28, emit=BLUE, estr=0.15),
     "deep": mat("deep", DEEP, 0.3), "sky": mat("sky", SKY, 0.25, emit=SKY, estr=0.6),
     "ink": mat("ink", hexc("16233F"), 0.35), "green": mat("green", hexc("19B97A"), 0.3, emit=hexc("19B97A"), estr=0.3)}

def stage(cam_loc, target, lens=50, ortho=None):
    bpy.ops.mesh.primitive_plane_add(size=20); fl = bpy.context.active_object; fl.is_shadow_catcher = True
    w = bpy.data.worlds.new("w"); S.world = w
    try: w.use_nodes = True
    except Exception: pass
    w.node_tree.nodes["Background"].inputs["Color"].default_value = hexc("E9EFF7")
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    def light(loc, e, col=(1, 1, 1), size=1.5):
        d = bpy.data.lights.new("l%d" % len(bpy.data.lights), "AREA"); d.energy = e; d.size = size; d.color = col[:3]
        o = bpy.data.objects.new(d.name, d); S.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    light((-1.2, -1.4, 2.0), 160); light((1.4, 1.0, 1.2), 140, SKY[:3], 1.0); light((0.4, -1.6, 0.5), 40)
    cd = bpy.data.cameras.new("c"); cd.lens = lens
    if ortho: cd.type = "ORTHO"; cd.ortho_scale = ortho
    cam = bpy.data.objects.new("c", cd); S.collection.objects.link(cam); S.camera = cam
    cam.location = cam_loc; cam.rotation_euler = (Vector(target) - Vector(cam_loc)).to_track_quat("-Z", "Y").to_euler()
    S.render.engine = "CYCLES"
    pr = bpy.context.preferences.addons["cycles"].preferences; pr.compute_device_type = "OPTIX"; pr.get_devices()
    for d in pr.devices: d.use = d.type == "OPTIX"
    S.cycles.device = "GPU"; S.cycles.samples = 128; S.cycles.use_denoising = True
    S.render.film_transparent = True; S.view_settings.view_transform = "Standard"; S.view_settings.exposure = -0.5

def part(name, m, loc, rot=(0, 0, 0), scale=1.0):
    bpy.ops.wm.stl_import(filepath=os.path.join(HERE, "parts", f"{name}.stl"))
    o = bpy.context.selected_objects[0]
    o.data.transform(Matrix.Diagonal(tuple(o.scale) + (1,))); o.scale = (1, 1, 1)
    if max(o.dimensions) > 1: o.data.transform(Matrix.Scale(0.001, 4))
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    o.data.materials.append(M[m]); o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    o.scale = (scale,) * 3
    bpy.context.view_layer.update()
    lo = min((o.matrix_world @ Vector(c)).z for c in o.bound_box); o.location.z -= lo  # rest on the floor
    return o

if MODE == "parts":
    S.render.resolution_x, S.render.resolution_y = 2000, 1250
    part("hand_heated_part", "blue", (0.0, 0.0, 0), (0, 0, 90))
    for i, x in enumerate((-0.03, -0.005, 0.02, 0.045)):
        part("finger", "white", (x * 1.7, 0.135, 0), (90, 0, 8 - 5 * i), 1.0 - 0.04 * abs(i - 1.5))
    part("thumb", "white", (-0.14, 0.075, 0), (90, 0, -20))
    part("strap", "white", (0.14, 0.08, 0), (0, 0, 25)); part("strap", "white", (0.165, 0.045, 0), (0, 0, -15))
    stage((0.03, -0.33, 0.31), (0.0, 0.06, 0.0), 50)
    S.render.filepath = OUT; bpy.ops.render.render(write_still=True)

elif MODE == "icons":
    os.makedirs(OUT, exist_ok=True)
    S.render.resolution_x = S.render.resolution_y = 640
    def rbox(m, loc, size, bev=0.03, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_cube_add(location=loc, rotation=[math.radians(a) for a in rot])
        o = bpy.context.active_object; o.scale = [s / 2 for s in size]; bpy.ops.object.transform_apply(scale=True)
        b = o.modifiers.new("b", "BEVEL"); b.width = bev; b.segments = 6; o.data.materials.append(M[m])
        for p in o.data.polygons: p.use_smooth = True
        return o
    def cyl(m, loc, r, d, rot=(0, 0, 0), bev=0.02, verts=64):
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d, location=loc, rotation=[math.radians(a) for a in rot], vertices=verts)
        o = bpy.context.active_object; b = o.modifiers.new("b", "BEVEL"); b.width = bev; b.segments = 5; b.limit_method = "ANGLE"
        o.data.materials.append(M[m]); [setattr(p, "use_smooth", True) for p in o.data.polygons]; return o
    def torus(m, loc, R, r, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=[math.radians(a) for a in rot], major_segments=96, minor_segments=24)
        o = bpy.context.active_object; o.data.materials.append(M[m]); [setattr(p, "use_smooth", True) for p in o.data.polygons]; return o
    def clear():
        for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    ICONS = {}
    def icon(f): ICONS[f.__name__] = f; return f
    @icon
    def ai():
        rbox("white", (0, 0, 0.12), (0.62, 0.62, 0.16), 0.05)
        rbox("blue", (0, 0, 0.23), (0.34, 0.34, 0.08), 0.03)
        for i in range(4):
            for s in (-1, 1):
                rbox("deep", (s * 0.36, -0.21 + i * 0.14, 0.1), (0.1, 0.06, 0.05), 0.012)
                rbox("deep", (-0.21 + i * 0.14, s * 0.36, 0.1), (0.06, 0.1, 0.05), 0.012)
        cyl("sky", (0.0, 0.0, 0.28), 0.06, 0.02)
    @icon
    def iot():
        cyl("blue", (0, -0.15, 0.08), 0.1, 0.16)
        for i, R in enumerate((0.26, 0.42, 0.58)):
            t = torus("white" if i % 2 else "blue", (0, -0.15, 0.08), R, 0.045, (90, 0, 0))
            bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
            for v in t.data.vertices: v.select = v.co.z < 0.02  # keep upper arcs only
            bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.delete(type="VERT"); bpy.ops.object.mode_set(mode="OBJECT")
            t.rotation_euler = (math.radians(90), 0, 0); t.location.z = 0.08
    @icon
    def leaf():
        import bmesh
        L, Wd, N = 0.9, 0.24, 40
        pts = [(-L / 2 + L * k / N, Wd * math.sin(math.pi * k / N) ** 0.75) for k in range(N + 1)]
        outline = pts + [(x, -y) for x, y in reversed(pts[1:-1])]
        me = bpy.data.meshes.new("leaf"); bm = bmesh.new()
        vs = [bm.verts.new((x, y, 0)) for x, y in outline]; bm.faces.new(vs); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new("leaf", me); S.collection.objects.link(o)
        so = o.modifiers.new("s", "SOLIDIFY"); so.thickness = 0.07; so.offset = 0
        bv = o.modifiers.new("b", "BEVEL"); bv.width = 0.025; bv.segments = 6
        sd = o.modifiers.new("bend", "SIMPLE_DEFORM"); sd.deform_method = "BEND"; sd.angle = math.radians(35); sd.deform_axis = "Y"
        o.location = (0, 0, 0.36); o.rotation_euler = (math.radians(55), math.radians(-25), math.radians(30))
        o.data.materials.append(M["green"]); [setattr(p, "use_smooth", True) for p in o.data.polygons]
        rbox("white", (0, 0, 0.36), (0.78, 0.022, 0.09), 0.01, (55, -25, 30))  # midrib
        cyl("blue", (-0.3, -0.22, 0.07), 0.12, 0.14)
    @icon
    def home():
        rbox("white", (0, 0, 0.2), (0.6, 0.5, 0.4), 0.04)
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.52, depth=0.3, location=(0, 0, 0.55), rotation=(0, 0, math.radians(45)))
        r = bpy.context.active_object; r.scale = (1.0, 0.82, 1); r.data.materials.append(M["blue"])
        b = r.modifiers.new("b", "BEVEL"); b.width = 0.03; b.segments = 5
        rbox("deep", (0, -0.255, 0.15), (0.16, 0.03, 0.26), 0.02)
    @icon
    def chart():
        for i, h in enumerate((0.25, 0.42, 0.62)):
            rbox("blue" if i == 2 else "white", (-0.25 + i * 0.25, 0, h / 2), (0.18, 0.18, h), 0.035)
        rbox("sky", (0, -0.2, 0.02), (0.8, 0.04, 0.04), 0.015)
    @icon
    def shield():
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, location=(0, 0, 0.42), segments=64, ring_count=32)
        o = bpy.context.active_object; o.scale = (1, 0.32, 1.15); o.data.materials.append(M["white"])
        [setattr(p, "use_smooth", True) for p in o.data.polygons]
        rbox("blue", (0.0, -0.13, 0.42), (0.13, 0.05, 0.42), 0.02); rbox("blue", (0.0, -0.13, 0.42), (0.42, 0.05, 0.13), 0.02)
    only = argv[2:] or list(ICONS)
    for name, fn in [(n, ICONS[n]) for n in only]:
        clear(); fn()
        stage((1.35, -1.75, 1.45), (0, 0, 0.18), 50, ortho=1.55)
        S.render.filepath = os.path.join(OUT, f"icon_{name}.png"); bpy.ops.render.render(write_still=True)
print("ASSETS_DONE")
