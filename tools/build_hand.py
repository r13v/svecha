"""Crop the CC0 MakeHuman hand, pose its real joints, and export a candle grip."""
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_church_assets as kit
base=kit.base
REF=base.ROOT/'art/references/makehuman'


def hand():
    vertices=[];uvs=[];faces=[];groups={};group=''
    for line in (REF/'base.obj').read_text().splitlines():
        parts=line.split()
        if not parts:continue
        if parts[0]=='v':vertices.append(Vector(tuple(map(float,parts[1:4]))))
        elif parts[0]=='vt':uvs.append(tuple(map(float,parts[1:3])))
        elif parts[0]=='g':group=parts[1];groups.setdefault(group,set())
        elif parts[0]=='f':
            indices=[tuple(int(n)-1 if n else 0 for n in part.split('/')) for part in parts[1:]]
            groups[group].update(v[0] for v in indices)
            if group=='body':faces.append(indices)
    def center(name):return sum((vertices[i] for i in groups[name]),Vector())/len(groups[name])
    wrist=center('joint-r-hand')
    z_axis=(center('joint-r-finger-3-1')-wrist).normalized()
    x_axis=(center('joint-r-finger-5-1')-center('joint-r-finger-2-1')).normalized()
    y_axis=z_axis.cross(x_axis).normalized();x_axis=y_axis.cross(z_axis).normalized()
    axes=Matrix((x_axis,y_axis,z_axis))
    def point(v):return axes@((v-wrist)*.1)+Vector((0,0,.19))
    coords=[point(v) for v in vertices]
    # The coat covers the lower forearm; omit hidden skin so it cannot pierce the sleeve.
    faces=[f for f in faces if all(coords[i[0]].z>.155 and (vertices[i[0]]-wrist).length<3.3 for i in f)]
    # The relaxed hand is close to the thigh in the source pose; keep only its connected shell.
    neighbors={}
    for face in faces:
        ids=[i[0] for i in face]
        for i in ids:neighbors.setdefault(i,set()).update(ids)
    unseen=set(neighbors);components=[]
    while unseen:
        pending=[unseen.pop()];component=set(pending)
        while pending:
            found=neighbors[pending.pop()] & unseen
            unseen.difference_update(found);component.update(found);pending.extend(found)
        components.append(component)
    keep=max(components,key=len)
    faces=[f for f in faces if f[0][0] in keep]
    used=sorted({i[0] for face in faces for i in face});remap={old:new for new,old in enumerate(used)}
    root=base.begin('HandGrip')
    mesh=bpy.data.meshes.new('AnatomicalHand');mesh.from_pydata([coords[i] for i in used],[],[[remap[i[0]] for i in f] for f in faces]);mesh.update()
    layer=mesh.uv_layers.new(name='UVMap')
    for poly,original in zip(mesh.polygons,faces):
        poly.use_smooth=True
        for loop,vertex in zip(poly.loop_indices,original):layer.data[loop].uv=uvs[vertex[1]]
    obj=bpy.data.objects.new('HandSkin',mesh);bpy.context.collection.objects.link(obj);obj.parent=root
    skin=base.material('Skin',(.52,.30,.20),0,.52)
    path=base.ROOT/'game/assets/textures/skin/young_lightskinned_male_diffuse.png'
    if path.exists():
        node=skin.node_tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(path))
        skin.node_tree.links.new(node.outputs['Color'],skin.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    skin.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value=.12
    mesh.materials.append(skin)
    skeleton=json.loads((REF/'default.mhskel').read_text())
    weights=json.loads((REF/'default_weights.mhw').read_text())['weights']
    def joint_position(name):
        ids=skeleton['joints'][name]
        return point(sum((vertices[i] for i in ids),Vector())/len(ids))
    rig_data=bpy.data.armatures.new('HandAuthoringRig')
    rig=bpy.data.objects.new('HandAuthoringRig',rig_data);bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    names=[n for n in skeleton['bones'] if n.endswith('.R') and (n.startswith(('finger','metacarpal')) or n in {'wrist.R','lowerarm02.R','lowerarm01.R'})]
    for name in names:
        spec=skeleton['bones'][name]
        bone=rig_data.edit_bones.new(name)
        bone.head=joint_position(spec['head']);bone.tail=joint_position(spec['tail'])
        plane=[joint_position(n) for n in skeleton['planes'][spec['rotation_plane']]]
        bend_axis=(plane[1]-plane[0]).cross(plane[2]-plane[0]).normalized()
        bone.align_roll(bend_axis.cross(bone.tail-bone.head).normalized())
    for name in names:
        parent=skeleton['bones'][name]['parent']
        if parent in names:rig_data.edit_bones[name].parent=rig_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    assigned={i:0.0 for i in range(len(used))}
    for name in names:
        vg=obj.vertex_groups.new(name=name)
        for index,weight in weights.get(name,[]):
            if index in remap:
                vg.add([remap[index]],weight,'REPLACE');assigned[remap[index]]+=weight
    wrist_group=obj.vertex_groups['wrist.R']
    for index,total in assigned.items():
        if total<.999:wrist_group.add([index],1-total,'ADD')
    deform=obj.modifiers.new('AnatomicalJointPose','ARMATURE');deform.object=rig;deform.use_deform_preserve_volume=True
    for bone in rig.pose.bones:bone.rotation_mode='XYZ'
    signs={}
    for digit in range(1,6):
        for segment in range(1,4):
            name='finger%d-%d.R'%(digit,segment)
            toward=Vector((.8,.3,.3)) if digit==1 else Vector((0,1,0))
            world_z=rig.data.bones[name].matrix_local.to_3x3()@Vector((0,0,1))
            signs[name]=1 if world_z.dot(toward)>=0 else -1
    relaxed={1:[8,5,5],2:[5,10,5],3:[8,12,6],4:[10,15,8],5:[12,18,8]}
    closed={1:[30,20,20],2:[20,45,25],3:[40,65,28],4:[43,70,30],5:[46,75,32]}
    def pose(values):
        for bone in rig.pose.bones:bone.rotation_euler=(0,0,0)
        for digit,angles in values.items():
            for segment,angle in enumerate(angles,1):
                name='finger%d-%d.R'%(digit,segment)
                rig.pose.bones[name].rotation_euler.x=signs[name]*math.radians(angle)
        bpy.context.view_layer.update()
    # Contact on the thumb pad and the side of the index, rather than bone tips.
    pads={}
    for digit,direction in [(1,Vector((1,.4,0)).normalized()),(2,Vector((-1,0,0)))]:
        name='finger%d-3.R'%digit;bone=rig.data.bones[name]
        along=(bone.tail_local-bone.head_local).normalized()
        estimate=bone.tail_local-along*.006+direction*.006
        ids=[remap[i] for i,w in weights[name] if i in remap and w>.70]
        ids=sorted(ids,key=lambda i:(obj.data.vertices[i].co-estimate).length_squared)[:8]
        center=sum((obj.data.vertices[i].co for i in ids),Vector())/len(ids)
        normal=sum((obj.data.vertices[i].normal for i in ids),Vector()).normalized()
        pads[digit]=(bone.matrix_local.inverted()@center,bone.matrix_local.to_3x3().inverted()@normal)
    pose(closed)
    grip_target=Vector((-.018,.035,.305))
    limits={1:[(5,55),(0,45),(0,55)],2:[(5,45),(15,80),(0,50)]}
    for digit in [1,2]:
        goal=grip_target+Vector((-.005 if digit==1 else .005,0,0))
        expected_normal=Vector((1 if digit==1 else -1,0,0))
        controls=[]
        for segment,(low,high) in enumerate(limits[digit],1):
            name='finger%d-%d.R'%(digit,segment);sign=signs[name]
            low,high=sorted((math.radians(low)*sign,math.radians(high)*sign))
            controls.append((rig.pose.bones[name],0,low,high))
        base_bone=rig.pose.bones['finger%d-1.R'%digit]
        controls.append((base_bone,2,math.radians(-25 if digit==1 else -12),math.radians(25 if digit==1 else 12)))
        if digit==1:controls.append((base_bone,1,math.radians(-45),math.radians(45)))
        preferred=[bone.rotation_euler[axis] for bone,axis,_,_ in controls]
        def error():
            bpy.context.view_layer.update()
            tip=rig.pose.bones['finger%d-3.R'%digit]
            position=tip.matrix@pads[digit][0]
            normal=(tip.matrix.to_3x3()@pads[digit][1]).normalized()
            posture=sum((bone.rotation_euler[axis]-value)**2 for (bone,axis,_,_),value in zip(controls,preferred))
            delta=position-goal
            return delta.x**2+delta.y**2+.05*delta.z**2+.000025*(1-normal.dot(expected_normal))**2+.000004*posture
        for step in [8,4,2,1,.5]:
            for repeat in range(6):
                for bone,axis,low,high in controls:
                    old=bone.rotation_euler[axis];best=error();chosen=old
                    for sign in [-1,1]:
                        candidate=max(low,min(high,old+math.radians(step)*sign))
                        bone.rotation_euler[axis]=candidate;value=error()
                        if value<best:best=value;chosen=candidate
                    bone.rotation_euler[axis]=chosen
    bpy.context.view_layer.update()
    grip_pose={b.name:tuple(b.rotation_euler) for b in rig.pose.bones}
    contacts=[rig.pose.bones['finger%d-3.R'%i].matrix@pads[i][0] for i in [1,2]]
    grip=(contacts[0]+contacts[1])/2
    print('HAND_CONTACT',json.dumps({'points':[list(v) for v in contacts],'gap':(contacts[0]-contacts[1]).length,'grip':list(grip),'angles':{n:[round(math.degrees(x),2) for x in v] for n,v in grip_pose.items() if n.startswith('finger')}}),flush=True)
    sub=obj.modifiers.new('SkinSubdivision','SUBSURF');sub.levels=2;sub.render_levels=2
    closed_mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    pose(relaxed)
    open_mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    assert len(closed_mesh.vertices)==len(open_mesh.vertices), 'Hand poses must keep matching topology'
    obj.name='HandAuthoringSkin';obj.parent=None;obj.hide_render=True;obj.hide_set(True)
    rig.hide_render=True;rig.hide_set(True);rig.select_set(False);obj.select_set(False)
    runtime=bpy.data.objects.new('HandSkin',open_mesh);bpy.context.collection.objects.link(runtime);runtime.parent=root
    runtime.shape_key_add(name='Open',from_mix=False)
    shape=runtime.shape_key_add(name='Grip',from_mix=False)
    coordinates=np.empty(len(closed_mesh.vertices)*3,dtype=np.float32)
    closed_mesh.vertices.foreach_get('co',coordinates);shape.data.foreach_set('co',coordinates);shape.value=1
    bpy.data.meshes.remove(closed_mesh)
    for name,rotation in grip_pose.items():rig.pose.bones[name].rotation_euler=rotation
    root['grip_radial_gap_m']=math.hypot(contacts[0].x-contacts[1].x,contacts[0].y-contacts[1].y)
    cloth=base.material('WoolSleeve',(.095,.087,.053),0,.9)
    sleeve=base.lathe('CoatSleeve',[(.072,-.50),(.065,-.30),(.055,-.12),(.044,0),(.043,.04),(.040,.09),(.034,.14),(.031,.16),(.032,.166),(.032,.18),(.029,.184),(.027,.18)],cloth,root,64,wobble=.035)
    # A sewn cuff and longitudinal folds make the sleeve read at arm's length.
    base.lathe('CuffSeam',[(.0322,.160),(.033,.163),(.033,.167),(.0322,.170)],cloth,root,64)
    for poly in sleeve.data.polygons:
        for loop in poly.loop_indices:
            v=sleeve.data.vertices[sleeve.data.loops[loop].vertex_index].co
            sleeve.data.uv_layers.active.data[loop].uv=(math.atan2(v.y,v.x)*.04/.22,v.z/.22)
    base.empty('GripAnchor',root,tuple(grip))
    root['reference_license']='MakeHuman Team / CC0'
    return root


if __name__=='__main__':
    root=hand()
    report=base.save_asset('hand_grip',root,(0,-.005,.18),.35,.37,render_preview=True)
    (base.REPORTS/'fidelity/hand_build.json').write_text(json.dumps(report,indent=2)+'\n')
