import bpy,bmesh,random,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_candle_assets as base
root=base.begin('CourtyardTree')
bpy.ops.import_scene.gltf(filepath=str(Path.cwd()/'art/references/polyhaven/tree_small_02/tree_small_02.gltf'))
# Split the imported trunk/branches/leaves for independent geometric simplification.
for obj in list(bpy.context.scene.objects):
 if obj.type=='MESH':
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.separate(type='MATERIAL');bpy.ops.object.mode_set(mode='OBJECT')
for obj in list(bpy.context.scene.objects):
 if obj.type!='MESH':continue
 material=obj.data.materials[0]
 label=material.name.lower()
 if 'leaves' in label:
  # Preserve the leaf silhouettes and their UVs; remove complete leaves, not corners.
  bm=bmesh.new();bm.from_mesh(obj.data)
  unseen=set(bm.verts);remove=[];rng=random.Random(210)
  while unseen:
   first=unseen.pop();component=[first];pending=[first]
   while pending:
    vertex=pending.pop()
    for edge in vertex.link_edges:
     other=edge.other_vert(vertex)
     if other in unseen:
      unseen.remove(other);component.append(other);pending.append(other)
   if rng.random()>.07:remove.extend(component)
  bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(obj.data);bm.free()
 else:
  mod=obj.modifiers.new('GameMesh','DECIMATE');mod.ratio=.22
  bpy.context.view_layer.objects.active=obj
  bpy.ops.object.modifier_apply(modifier=mod.name)
 obj.matrix_world=root.matrix_world.inverted()@obj.matrix_world
 obj.parent=root
 # Leaves cast dappled light using an alpha cutout rather than blended transparency.
 for mat in obj.data.materials:
  if 'leaves' in mat.name.lower():
   mat.surface_render_method='DITHERED'
   mat.use_transparency_overlap=False
for obj in list(bpy.context.scene.objects):
 if obj!=root and obj.type=='EMPTY' and len(obj.children)==0: bpy.data.objects.remove(obj,do_unlink=True)
# Preserve base-on-ground export contract.
from mathutils import Vector
points=[o.matrix_world@Vector(c) for o in root.children_recursive if o.type=='MESH' for c in o.bound_box]
base_z=min(v.z for v in points)
for o in root.children:
 if o.type=='MESH':o.location.z-=base_z
row=base.save_asset('courtyard_tree',root,(0,0,2.2),6,6,render_preview=False)
Path('docs/04_BLENDER_ENV/fidelity/tree_build.json').write_text(json.dumps(row,indent=2)+'\n')
print('TREE_READY',row['triangles'])
