"""Build the remaining authored church kit. Uses only Blender's bundled libraries."""

import json
import math
import sys
import random
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_candle_assets as base


def textures():
    """Original repeatable material swatches, not edits of reference artwork."""
    folder = base.ROOT / "game/assets/textures"
    folder.mkdir(exist_ok=True)
    y, x = np.mgrid[0:512, 0:512] / 512.0
    noise = np.random.default_rng(52).random((512, 512))
    grain = np.sin(x * math.tau * 67 + 3 * np.sin(y * math.tau * 3) + np.sin(y * math.tau * 11))
    fields = {
        "walnut": ((0.21, 0.115, 0.058), 0.75 + grain * 0.14 + noise * 0.16),
        "plaster": ((0.73, 0.66, 0.53), 0.97 + noise * 0.03),
        "limestone": ((0.49, 0.44, 0.35), 0.96 + noise * 0.04),
        "agedbrass": ((0.69, 0.47, 0.19), 0.90 + noise * 0.08 + np.sin(x * 51) * np.cos(y * 39) * 0.07),
        "roofslate": ((0.13, 0.18, 0.19), 0.80 + noise * 0.25),
    }
    for name, (color, field) in fields.items():
        pixels = np.ones((512, 512, 4), dtype=np.float32)
        pixels[:, :, :3] = np.clip(field[:, :, None] * np.array(color), 0, 1)
        image = bpy.data.images.new(name, 512, 512)
        image.pixels.foreach_set(pixels.ravel())
        image.filepath_raw = str(folder / f"{name}_basecolor.png")
        image.file_format = "PNG"
        image.save()


def palette():
    return {
        "wood": base.material("Walnut", (0.15, 0.075, 0.032), 0, 0.62),
        "boards": base.material("WalnutBoards", (0.15, 0.075, 0.032), 0, 0.62),
        "floor": base.material("FloorStone", (0.55, 0.50, 0.41), 0, 0.75),
        "stone": base.material("Limestone", (0.49, 0.44, 0.35), 0, 0.84),
        "plaster": base.material("Plaster", (0.73, 0.66, 0.53), 0, 0.92),
        "brass": base.material("AgedBrass", (0.56, 0.34, 0.105), 0.94, 0.28),
        "iron": base.material("ForgedIron", (0.035, 0.032, 0.027), 0.8, 0.55),
        "slate": base.material("RoofSlate", (0.13, 0.18, 0.19), 0.2, 0.8),
    }


def uv_box(mesh, mat=None, offset=(0, 0)):
    uv = mesh.uv_layers.active or mesh.uv_layers.new()
    for face in mesh.polygons:
        axis = max(range(3), key=lambda a: abs(face.normal[a]))
        axes = [(1, 2), (0, 2), (0, 1)][axis]
        for index in face.loop_indices:
            v = mesh.vertices[mesh.loops[index].vertex_index].co
            scale = mat.get("tile_m", (1, 1)) if mat else (1, 1)
            uv.data[index].uv = (v[axes[0]] / scale[0] + offset[0], v[axes[1]] / scale[1] + offset[1])


def box(name, size, location, mat, parent, bevel=0.006):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = location
    obj.parent = parent
    obj.data.materials.append(mat)
    uv_box(obj.data, mat, (location[0] * 0.37 + location[1] * 0.51, location[2] * 0.13))
    if bevel:
        mod = obj.modifiers.new("EdgeWear", "BEVEL")
        mod.width = min(bevel, min(size) / 5)
        mod.segments = 2
        obj.modifiers.new("CornerNormals", "WEIGHTED_NORMAL")
    return obj


def extrude(name, outline, depth, mat, parent):
    """Extrude an X/Z outline along Y; the visible front faces Blender -Y."""
    n = len(outline)
    vertices = [(x, y, z) for y in [-depth / 2, depth / 2] for x, z in outline]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    faces += [(i, i + n, (i + 1) % n + n, (i + 1) % n) for i in range(n)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    # Closed extrusions must face outward, including the inner curve of an arch.
    import bmesh
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh); bm.free()
    mesh.materials.append(mat)
    uv_box(mesh, mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    return obj


def arch(name, radius, thickness, spring, depth, mat, parent, steps=32):
    outline = [(math.cos(t) * (radius + thickness), spring + math.sin(t) * (radius + thickness))
               for t in np.linspace(0, math.pi, steps + 1)]
    outline += [(math.cos(t) * radius, spring + math.sin(t) * radius)
                for t in np.linspace(math.pi, 0, steps + 1)]
    return extrude(name, outline, depth, mat, parent)


def ring(name, center, radius, minor, mat, parent):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=minor,
                                   major_segments=24, minor_segments=8)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler.x = math.pi / 2
    obj.location = center
    obj.parent = parent
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def picture(name, filename, width, height, location, parent):
    mat = base.material(name, (1, 1, 1), 0, 0.75)
    nodes = mat.node_tree.nodes
    image = nodes.new("ShaderNodeTexImage")
    image.image = bpy.data.images.load(str(base.ROOT / "game/assets/icons" / filename), check_existing=True)
    mat.node_tree.links.new(image.outputs["Color"], nodes.get("Principled BSDF").inputs["Base Color"])
    ratio = image.image.size[0] / image.image.size[1]
    width = min(width, height * ratio)
    height = min(height, width / ratio)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(-width / 2, 0, 0), (width / 2, 0, 0), (width / 2, 0, height), (-width / 2, 0, height)], [], [(0, 1, 2, 3)])
    mesh.materials.append(mat)
    layer = mesh.uv_layers.new()
    for i, uv in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        layer.data[i].uv = uv
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.parent = parent
    return obj


def trim_curve(name, points, radius, mat, parent, cyclic=False):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 3
    data.bevel_depth = radius
    data.bevel_resolution = 2
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points): p.co = (*co, 1)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    data.materials.append(mat)
    return obj


def carved_panel(parent, at, width, height, p):
    root = base.empty("CarvedPanel", parent, at)
    box("PanelGround", (width, 0.055, height), (0, 0, 0), p["wood"], root, 0.018)
    # Layered routed borders, then four mirrored scrolls around a central rosette.
    for inset, depth in [(0.055, 0.010), (0.075, 0.004)]:
        w, h = width / 2 - inset, height / 2 - inset
        trim_curve("RoutedBorder", [(-w,-.038,-h),(w,-.038,-h),(w,-.038,h),(-w,-.038,h)], depth, p["wood"], root, True)
    radius = min(width, height) * 0.27
    points = [(radius * math.cos(a), -.047, radius * .75 * math.sin(a)) for a in np.linspace(0, math.tau, 65)]
    trim_curve("DiamondRelief", [(0,-.047,radius),(radius,-.047,0),(0,-.047,-radius),(-radius,-.047,0)], .008, p["wood"], root, True)
    for quadrant in range(4):
        turn = quadrant * math.pi / 2
        points = []
        for t in np.linspace(0, math.tau * 1.25, 48):
            r = radius * .42 * (1 - t / (math.tau * 1.5))
            x = radius * .48 + r * math.cos(t)
            z = r * math.sin(t)
            points.append((x*math.cos(turn)-z*math.sin(turn), -.052, x*math.sin(turn)+z*math.cos(turn)))
        trim_curve("CarvedScroll", points, .007, p["wood"], root)
    points = []
    for a in np.linspace(0, math.tau, 65):
        r = radius * .23 * (1 + .35 * math.cos(a * 4))
        points.append((r*math.cos(a),-.061,r*math.sin(a)))
    trim_curve("Rosette", points, .007, p["wood"], root, True)
    return root


def frame(name, width, height, location, p, parent):
    root = base.empty(name, parent, location)
    for border, depth, projection in [(0.074,0.12,0), (.026,.035,-.082), (.010,.025,-.105)]:
        for x in [-width / 2 - border / 2, width / 2 + border / 2]:
            box("FrameMoulding", (border,depth,height+border*2), (x,projection,height/2), p["wood"], root, .004)
        for z in [-border/2, height+border/2]:
            box("FrameMoulding", (width+border*2,depth,border), (0,projection,z), p["wood"], root,.004)
    for x in [-width/2+.008,width/2-.008]:
        box("GiltInnerEdge", (.008,.012,height), (x,-.125,height/2),p["brass"],root,.001)
    return root


def door():
    root = base.begin("ChurchDoor"); p = palette()
    for x in [-0.775, 0.775]:
        box("Jamb", (0.15, 0.22, 2.0), (x, 0, 1.0), p["wood"], root)
    arch("ArchedFrame", 0.70, 0.15, 2.0, 0.22, p["wood"], root)
    for side, label in [(-1, "Left"), (1, "Right")]:
        hinge = base.empty(f"{label}Hinge", root, (side * 0.70, 0, 0))
        world_outline = [(0, 0), (0.694, 0), (0.694, 2.0)]
        world_outline += [(0.694 * math.cos(t), 2 + 0.694 * math.sin(t)) for t in np.linspace(0, math.pi / 2, 18)]
        outline = [(side * (x - 0.70), z) for x, z in world_outline]
        if side < 0:
            outline.reverse()
        extrude(f"{label}Leaf", outline, 0.07, p["wood"], hinge)
        for z in [0.40, 1.10, 1.76]:
            carved_panel(hinge, (-side * 0.35, -0.050, z), 0.53, 0.51, p)
        for z in [0.72, 1.45, 1.98]:
            box("CrossRail", (0.66, 0.05, 0.045), (-side * 0.35, -0.058, z), p["wood"], hinge)
        handle = base.empty(f"{label}Handle", hinge, (-side * 0.59, -0.083, 1.02))
        box("HandlePlate", (0.075, 0.018, 0.23), (0, 0, 0), p["iron"], handle)
        ring("RingPull", (0, -0.028, -0.02), 0.039, 0.007, p["iron"], handle)
        for z in [0.38, 1.75]:
            pin = base.lathe("HingePin", [(0.012, 0), (0.012, 0.17)], p["iron"], hinge, 16)
            pin.location = (0, 0, z)
    return root


def table():
    root = base.begin("CandleTable"); p = palette()
    box("Top", (0.95, 0.5, 0.055), (0, 0, 0.825), p["wood"], root, 0.012)
    for x in [-0.39, 0.39]:
        for y in [-0.18, 0.18]:
            box("Leg", (0.065, 0.065, 0.8), (x, y, 0.4), p["wood"], root)
        box("Stretcher", (0.06, 0.4, 0.055), (x, 0, 0.17), p["wood"], root)
    box("CrossStretcher", (0.8, 0.05, 0.065), (0, 0, 0.17), p["wood"], root)
    for y in [-0.205, 0.205]:
        box("Apron", (0.82, 0.035, 0.13), (0, y, 0.73), p["wood"], root)
    base.empty("TrayAnchor", root, (0, 0, 0.8525))
    return root


def tray():
    root = base.begin("CandleTray"); p = palette()
    box("Bottom", (0.39, 0.29, 0.015), (0, 0, 0.0075), p["wood"], root)
    for x in [-0.2, 0.2]:
        box("Side", (0.02, 0.32, 0.055), (x, 0, 0.0275), p["wood"], root)
    for y in [-0.15, 0.15]:
        box("End", (0.39, 0.02, 0.055), (0, y, 0.0275), p["wood"], root)
    base.empty("PickupAnchor", root, (0, 0, 0.025))
    return root


def window_bay():
    root=base.begin("WindowBay");p=palette()
    # Deep limewashed splayed reveals; the aperture is actual open geometry.
    half=.44; bottom=1.07; spring=2.61; wall_h=3.4; thick=.52
    for x in [-.975,.975]:
        box("WallSide",(1.05,thick,wall_h),(x,0,wall_h/2),p["plaster"],root,0)
    box("WallBelow",(.90,thick,bottom),(0,0,bottom/2),p["plaster"],root,0)
    box("WallAbove",(.90,thick,.35),(0,0,3.225),p["plaster"],root,0)
    arch("LimewashReveal",.45,.20,spring,thick,p["plaster"],root,48)
    for x in [-.445,.445]:
        box("RevealEdge",(.042,.58,1.56),(x,-.02,1.85),p["plaster"],root,.01)
    box("WindowSill",(1.10,.74,.12),(0,-.04,bottom),p["stone"],root,.018)
    # Recessed wood and iron mullions, inside the wall rather than flush with it.
    for x in [-.422,.422]:
        box("WindowFrame",(.032,.055,spring-bottom),(x,.19,(spring+bottom)/2),p["wood"],root,.003)
    arch("WindowArch",.402,.033,spring,.055,p["wood"],root,48).location.y=.19
    box("VerticalMullion",(.026,.040,1.96),(0,.19,2.03),p["iron"],root,.002)
    for z in [1.58,2.17,2.63]:
        box("HorizontalMullion",(.84,.040,.023),(0,.19,z),p["iron"],root,.002)
    return root


def shell():
    root = base.begin("ChurchShell"); p = palette()
    box("Floor", (7.4, 11.4, 0.14), (0, 0, 0.07), p["stone"], root, 0.005)
    # In Blender the entrance is -Y; in Godot it becomes +Z.
    for x in [-2.2, 2.2]:
        box("EntrySide", (2.6, 0.38, 3.4), (x, -5.5, 1.86), p["plaster"], root)
    box("EntryTop", (1.8, 0.38, 0.65), (0, -5.5, 3.235), p["plaster"], root)
    entry_arch = arch("EntryArch", 0.85, 0.25, 2.16, 0.38, p["stone"], root)
    entry_arch.location.y = -5.54
    for x in [-0.975, 0.975]:
        box("EntryStoneJamb", (0.25, 0.46, 2.0), (x, -5.52, 1.16), p["stone"], root)
    box("RearWall", (7.4, 0.38, 3.4), (0, 5.5, 1.86), p["plaster"], root)
    for x in [-3.5, 3.5]:
        for y in [-5, 5]:
            box("SideEnd", (0.38, 1, 3.4), (x, y, 1.86), p["plaster"], root)
        box("Cornice", (0.49, 11.3, 0.12), (x, 0, 3.53), p["stone"], root)
        box("Plinth", (0.48, 11.3, 0.17), (x, 0, 0.245), p["stone"], root)
    # A continuous displaced flagstone surface; no second grid fighting the scanned joints.
    vertices=[]; faces=[]; nx=84; ny=132
    floor_mat=p["floor"]
    image=bpy.data.images.load(str(base.ROOT / "game/assets/textures/limestone/floor_albedo.png"),check_existing=True)
    pixels=np.array(image.pixels[:]).reshape(image.size[1],image.size[0],4)
    for j in range(ny+1):
        y=-5.5+11*j/ny
        for i in range(nx+1):
            x=-3.5+7*i/nx
            u=(x/2.8)%1;v=(y/3.2)%1
            value=pixels[int(v*(image.size[1]-1)),int(u*(image.size[0]-1)),0]
            vertices.append((x,y,.158+float(value)*.009))
    for j in range(ny):
        for i in range(nx):
            k=j*(nx+1)+i;faces.append((k,k+1,k+nx+2,k+nx+1))
    mesh=bpy.data.meshes.new("WornFlagstones");mesh.from_pydata(vertices,[],faces);mesh.update();mesh.materials.append(floor_mat)
    uv=mesh.uv_layers.new()
    for poly in mesh.polygons:
        poly.use_smooth=True
        for index in poly.loop_indices:
            v=mesh.vertices[mesh.loops[index].vertex_index].co
            uv.data[index].uv=(v.x/2.8,v.y/3.2)
    obj=bpy.data.objects.new("WornFlagstones",mesh);bpy.context.collection.objects.link(obj);obj.parent=root
    for y in [-5.5, 5.5]:
        outline = [(-3.5, 3.55), (3.5, 3.55)]
        outline += [(3.5 * math.cos(a), 3.56 + 1.5 * math.sin(a)) for a in np.linspace(0, math.pi, 49)]
        gable = extrude("VaultEndWall", outline, 0.38, p["plaster"], root)
        gable.location.y = y
    return root


def vault():
    root = base.begin("ChurchVault"); p = palette()
    # Elliptical vault, split from walls for manual placement and roof access.
    vertices = []
    for y in [-5.6, 5.6]:
        for angle in np.linspace(0, math.pi, 49):
            vertices.append((3.5 * math.cos(angle), y, 1.5 * math.sin(angle)))
    faces = [(i + 1, i + 50, i + 49, i) for i in range(48)]
    mesh = bpy.data.meshes.new("VaultInterior")
    mesh.from_pydata(vertices, [], faces); mesh.update(); mesh.materials.append(p["plaster"])
    uv_box(mesh, p["plaster"])
    obj = bpy.data.objects.new("VaultInterior", mesh); bpy.context.collection.objects.link(obj); obj.parent = root
    for poly in mesh.polygons: poly.use_smooth = True
    # The vault's interior faces point inward; a roof is a separate asset.
    return root


def icon_case():
    root = base.begin("IconCase"); p = palette()
    for width, depth, height, z in [(1.17,.37,.12,.06),(1.08,.29,.075,.16),(1.06,.28,.07,1.0),(1.19,.38,.095,1.10),(1.12,.32,.07,2.79)]:
        box("CabinetCornice", (width,depth,height), (0,0,z),p["wood"],root,.009)
    carved_panel(root, (0,-.12,.59), .94,.74,p)
    box("IconBacking", (1.02,.16,1.57),(0,0,1.94),p["wood"],root)
    holder = frame("IconFrame", .84,1.48,(0,-.11,1.20),p,root)
    picture("TheotokosIcon", "hodegetria_dionysius.jpg", .84,1.48,(0,-.14,.17),holder)
    for x in [-.52,.52]:
        box("CasePilaster",(.10,.24,1.54),(x,-.02,1.97),p["wood"],root,.008)
        for z in [1.24,2.62]:
            box("PilasterCapital",(.16,.29,.065),(x,-.02,z),p["wood"],root,.006)
    # A solid carved crown rather than an empty hoop.
    outline=[(-.57,2.83),(-.52,2.91),(-.37,2.92),(-.23,3.06),(0,3.18),(.23,3.06),(.37,2.92),(.52,2.91),(.57,2.83)]
    crown=extrude("CarvedCrown",list(reversed(outline)),.24,p["wood"],root)
    trim_curve("CrownMoulding",[(x,-.14,z+.01) for x,z in outline],.018,p["wood"],root)
    carved_panel(root,(0,-.15,2.90),.42,.30,p)
    return root


def iconostasis():
    root=base.begin("Iconostasis");p=palette()
    # Continuous panelwork, deeply moulded icon frames and a small feast tier.
    box("ContinuousBacking",(6.6,.12,3.30),(0,.035,1.65),p["boards"],root)
    for x in [-3.21,-2.10,-.88,.88,2.10,3.21]:
        box("Pilaster",(.13,.28,3.13),(x,-.05,1.565),p["wood"],root,.006)
        for z in [.16,.76,2.36,2.51,3.10]:
            box("Capital",(.21,.34,.068),(x,-.08,z),p["wood"],root,.007)
    for z,depth,height in [(.08,.30,.16),(.76,.29,.06),(2.40,.32,.10),(2.49,.29,.06),(3.31,.33,.10),(3.39,.40,.06)]:
        box("Cornice",(6.7,depth,height),(0,-.03,z),p["wood"],root,.008)
    files=["nicholas_sinai.jpg","hodegetria_dionysius.jpg","christ_sinai.jpg","john_baptist.jpg"]
    for i,x in enumerate([-2.65,-1.49,1.49,2.65]):
        carved_panel(root,(x,-.08,.43),1.0,.55,p)
        holder=frame("MainIconFrame",.91,1.41,(x,-.11,.90),p,root)
        picture("MainIcon",files[i],.91,1.41,(0,-.14,0),holder)
        arch("ArchedIconMoulding",.46,.028,1.85,.06,p["wood"],root).location=(x,-.28,0)
    feasts=["birth_mary","presentation","nativity","baptism","last_supper","transfiguration","harrowing","thomas","dormition"]
    for i,x in enumerate([-2.95,-2.28,-1.61,-.94,0,.94,1.61,2.28,2.95]):
        width=.91 if i==4 else .50
        holder=frame("FeastFrame",width,.66,(x,-.13,2.58),p,root)
        picture("FeastIcon","feast_"+feasts[i]+".jpg",width,.66,(0,-.14,0),holder)
    for side in [-1,1]:
        # Doors stay closed and retain an arch-shaped upper silhouette.
        pts=[(0,0),(.76,0),(.76,1.86)]
        pts += [(.76*math.cos(a),1.86+.40*math.sin(a)) for a in np.linspace(0,math.pi/2,25)]
        pts=[(side*x,z) for x,z in pts]
        if side<0:pts.reverse()
        leaf=extrude("RoyalDoor",pts,.19,p["wood"],root);leaf.location.y=-.15
        carved_panel(root,(side*.40,-.27,.44),.63,.61,p)
        box("DoorCrossStem",(.026,.025,.43),(side*.37,-.275,1.53),p["brass"],root,.003)
        box("DoorCrossbar",(.24,.025,.026),(side*.37,-.275,1.61),p["brass"],root,.003)
        arch("RoyalDoorCarving",.68,.036,1.85,.075,p["wood"],root).location.y=-.26
    points=[(-.98,-.15,3.42),(-.71,-.15,3.43),(-.52,-.15,3.58),(-.29,-.15,3.66),(0,-.15,3.85),(.29,-.15,3.66),(.52,-.15,3.58),(.71,-.15,3.43),(.98,-.15,3.42)]
    crown=extrude("IconostasisCrown",[(v[0],v[2]) for v in reversed(points)],.21,p["wood"],root)
    trim_curve("CrownRelief",points,.032,p["wood"],root)
    for sign in [-1,1]:
        points=[]
        for t in np.linspace(0,math.tau*1.1,60):
            r=.22*(1-t/(math.tau*1.5))
            points.append((sign*(.23+r*math.cos(t)),-.16,3.54+r*math.sin(t)))
        trim_curve("CrownScroll",points,.018,p["wood"],root)
    box("TopCross",(.055,.065,.52),(0,-.04,4.10),p["wood"],root,.005)
    box("TopCrossbar",(.32,.065,.055),(0,-.04,4.20),p["wood"],root,.005)
    return root


def main():
    from build_church_exterior import roof
    from build_hand import hand
    textures()
    reports = []
    for slug, builder, target, distance, size in [
        ("church_door", door, (0, 0, 1.4), 2.5, 3.2),
        ("candle_table", table, (0, 0, 0.43), 1.0, 1.25),
        ("candle_tray", tray, (0, 0, 0.04), 0.4, 0.55),
        ("window_bay", window_bay, (0, 0, 1.7), 4, 4.0),
        ("church_shell", shell, (0, 0, 1.8), 10, 15),
        ("church_vault", vault, (0, 0, 0.8), 10, 13),
        ("church_roof", roof, (0, 0, 1.5), 10, 14),
        ("icon_case", icon_case, (0, 0, 1.25), 2, 3.0),
        ("iconostasis", iconostasis, (0, 0, 1.5), 5, 7.2),
        ("hand_grip", hand, (0, 0, 0.15), 0.4, 0.36),
    ]:
        root = builder()
        reports.append(base.save_asset(slug, root, target, distance, size, render_preview=slug in {"church_door", "candle_table", "icon_case", "hand_grip"}))
    (base.REPORTS / "church_asset_build.json").write_text(json.dumps({"blender_version": bpy.app.version_string, "assets": reports}, indent=2) + "\n")
    base.main()  # Re-export the first set with the same original patina texture.
    print("CHURCH_ASSETS_EXPORTED", len(reports))


if __name__ == "__main__":
    main()
