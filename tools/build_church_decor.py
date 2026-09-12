"""Authored furniture, lamps and textiles visible in the approved concept frames."""
import json
import math
import sys
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_church_assets as kit
base=kit.base


def bench():
    root=base.begin('WallBench');p=kit.palette()
    for x in [-.66,.66]:
        for y in [-.15,.15]:kit.box('Leg',(.055,.055,.45),(x,y,.225),p['wood'],root,.006)
        kit.box('ArmPost',(.048,.055,.35),(x,-.15,.61),p['wood'],root)
        kit.box('Armrest',(.075,.43,.045),(x,0,.785),p['wood'],root)
        kit.box('RearStile',(.052,.055,.54),(x,.17,.71),p['wood'],root)
    for y in [-.14,0,.14]:kit.box('SeatPlank',(1.48,.135,.038),(0,y,.456),p['boards'],root,.007)
    for z in [.66,.85]:kit.box('BackPlank',(1.40,.045,.125),(0,.18,z),p['boards'],root,.006)
    kit.box('FrontApron',(1.37,.042,.095),(0,-.17,.36),p['wood'],root)
    return root


def side_table():
    root=base.begin('SideTable');p=kit.palette()
    kit.box('Tabletop',(.62,.38,.042),(0,0,.74),p['boards'],root,.009)
    for x in [-.255,.255]:
        for y in [-.125,.125]:kit.box('Leg',(.055,.055,.72),(x,y,.36),p['wood'],root)
    for y in [-.145,.145]:kit.box('Apron',(.55,.04,.14),(0,y,.65),p['wood'],root)
    kit.box('Shelf',(.53,.29,.03),(0,0,.12),p['wood'],root)
    base.empty('VaseAnchor',root,(0,0,.761))
    return root


def vase():
    root=base.begin('FlowerVase');p=kit.palette()
    ceramic=base.material('AgedCeramic',(.125,.096,.060),0,.55)
    leaf=base.material('OliveLeaf',(.065,.105,.035),0,.8)
    stem=base.material('DryStem',(.17,.12,.052),0,.8)
    ivory=base.material('TinyWhiteFlower',(.79,.70,.49),0,.85)
    violet=base.material('DriedLavender',(.16,.083,.16),0,.84)
    base.lathe('Pot',[(.05,0),(.075,.018),(.097,.062),(.100,.11),(.078,.15),(.051,.18),(.054,.21),(.049,.215),(.043,.208),(.043,.185),(.060,.16)],ceramic,root,48)
    rng=np.random.default_rng(20)
    for i in range(17):
        a=i*2.39996;r=float(rng.uniform(.08,.22));top=float(rng.uniform(.38,.63))
        end=np.array([math.cos(a)*r,math.sin(a)*r,top])
        kit.trim_curve('FlowerStem',[(0,0,.14),tuple(end*.4+np.array([0,0,.12])),tuple(end)],.0017,stem,root)
        for j in range(3):
            origin=end*(.48+j*.13);origin[2]+=.10
            t=a+j*1.8
            dx,dy=math.cos(t)*.035,math.sin(t)*.035
            points=[tuple(origin),tuple(origin+np.array([dx-dy*.2,dy+dx*.2,.013])),tuple(origin+np.array([dx*1.75,dy*1.75,.021])),tuple(origin+np.array([dx+dy*.2,dy-dx*.2,.007]))]
            mesh=bpy.data.meshes.new('Leaf');mesh.from_pydata(points,[],[(0,1,2,3)]);mesh.materials.append(leaf)
            obj=bpy.data.objects.new('Leaf',mesh);bpy.context.collection.objects.link(obj);obj.parent=root
        for j in range(5):
            offset=np.array([math.cos(j*math.tau/5)*.008,math.sin(j*math.tau/5)*.008,j*.002])
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.0045,location=end+offset)
            obj=bpy.context.object;obj.name='Blossom';obj.parent=root;obj.data.materials.append(violet if i%3==0 else ivory)
    return root


def oil_lamp():
    root=base.begin('HangingLamp');p=kit.palette()
    ruby=base.material('RubyGlass',(.22,.012,.004),0,.2)
    base.lathe('LampBowl',[(.008,0),(.030,.025),(.064,.046),(.090,.085),(.087,.099),(.074,.097),(.060,.060)],p['brass'],root,48)
    base.lathe('RedOilCup',[(.035,.049),(.069,.090),(.077,.114),(.072,.118),(.061,.098)],ruby,root,48)
    for a in [0,math.tau/3,math.tau*2/3]:
        for i in range(28):
            t=i/27;r=.086*(1-t)
            ring=kit.ring('ChainLink',(math.cos(a)*r,math.sin(a)*r,.11+t*.59),.008,.0014,p['brass'],root)
            ring.rotation_euler.z=a+(i%2)*math.pi/2
    base.lathe('Hanger',[(.018,.70),(.020,.73),(.008,.75)],p['brass'],root,24)
    base.empty('FlameAnchor',root,(0,0,.105))
    return root


def chandelier():
    root=base.begin('Chandelier');p=kit.palette()
    # Ring is at the origin; eight CandleAnchor nodes receive real finite candles in Godot.
    base.lathe('IronRing',[(.46,0),(.48,0),(.48,.035),(.46,.035)],p['iron'],root,96,closed=True)
    for i in range(8):
        a=i*math.tau/8;x,y=math.cos(a)*.48,math.sin(a)*.48
        cup=base.lathe('Cup',[(.01,0),(.028,.009),(.024,.020)],p['brass'],root,24);cup.location=(x,y,.035)
        base.empty('CandleAnchor%02d'%i,root,(x,y,.047))
    for i in range(4):
        a=i*math.pi/2
        kit.trim_curve('Suspension',[(math.cos(a)*.47,math.sin(a)*.47,.035),(0,0,1.215)],.004,p['iron'],root)
    base.lathe('CeilingCap',[(.025,1.215),(.053,1.235),(.050,1.260)],p['iron'],root,32)
    return root


def steps():
    root=base.begin('ChancelSteps');p=kit.palette()
    for i in range(3):
        depth=1.05-i*.29
        kit.box('LimestoneStep',(6.65,depth,.08),(0,-depth/2,.04+i*.08),p['stone'],root,.009)
    # Overlaid narrow riser joints keep the broad treads legible.
    return root


def carpet():
    root=base.begin('ChancelCarpet')
    mat=base.material('BurgundyWool',(.22,.035,.026),0,.97)
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(base.ROOT/'game/assets/textures/carpet/burgundy_runner.png'))
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    # A single cloth strip follows the floor and each of the three risers.
    profile=[(-1.92,0),(-1.055,0),(-1.047,.08),(-.77,.08),(-.762,.16),(-.48,.16),(-.472,.24),(.0,.24)]
    verts=[(x,y,z) for y,z in profile for x in [-.85,.85]]
    faces=[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(profile)-1)]
    mesh=bpy.data.meshes.new('WoolRunner');mesh.from_pydata(verts,[],faces);mesh.materials.append(mat)
    uv=mesh.uv_layers.new()
    lengths=[0.0]
    for a,b in zip(profile,profile[1:]): lengths.append(lengths[-1]+math.dist(a,b))
    for poly in mesh.polygons:
        for j in poly.loop_indices:
            k=mesh.loops[j].vertex_index
            uv.data[j].uv=(k%2,lengths[k//2]/lengths[-1])
    obj=bpy.data.objects.new('WoolRunner',mesh);bpy.context.collection.objects.link(obj);obj.parent=root
    mod=obj.modifiers.new('ClothThickness','SOLIDIFY');mod.thickness=.003;mod.offset=1
    return root


def wall_icon():
    root=base.begin('WallIcon');p=kit.palette()
    kit.box('IconBoard',(.43,.042,.67),(0,0,.335),p['wood'],root)
    holder=kit.frame('CarvedFrame',.28,.49,(0,-.045,.09),p,root)
    kit.picture('ChristIcon','christ_sinai.jpg',.28,.49,(0,-.14,0),holder)
    return root


def banner():
    root=base.begin('HangingBanner');p=kit.palette()
    cloth=base.material('BurgundyCloth',(.13,.013,.019),0,.87)
    outline=[(-.24,.0),(0,.10),(.24,.0),(.24,1.03),(-.24,1.03)]
    body=kit.extrude('EmbroideredCloth',outline,.008,cloth,root)
    for x in [-.215,.215]:
        kit.trim_curve('GoldThread',[(x,-.007,.055),(x,-.007,1.015)],.004,p['brass'],root)
    kit.trim_curve('GoldLowerHem',[(-.215,-.007,.025),(0,-.007,.115),(.215,-.007,.025)],.004,p['brass'],root)
    kit.box('TopRod',(.63,.025,.026),(0,0,1.05),p['brass'],root)
    kit.trim_curve('HangingCord',[(-.265,0,1.05),(0,0,1.32),(.265,0,1.05)],.003,p['brass'],root)
    holder=kit.frame('EmbroideredBorder',.24,.40,(0,-.010,.41),p,root)
    kit.picture('BannerIcon','hodegetria_dionysius.jpg',.24,.40,(0,-.14,0),holder)
    return root


def sconce():
    root=base.begin('WallSconce');p=kit.palette()
    kit.box('Backplate',(.065,.023,.25),(0,0,.125),p['brass'],root,.014)
    for x in [-.08,.08]:
        kit.trim_curve('CurvedArm',[(0,-.020,.07),(x*.7,-.10,.075),(x,-.17,.16),(x,-.17,.24)],.008,p['brass'],root)
        cup=base.lathe('CandleCup',[(.012,0),(.032,.014),(.030,.028)],p['brass'],root,32)
        cup.location=(x,-.17,.24)
        base.empty('CandleAnchorLeft' if x<0 else 'CandleAnchorRight',root,(x,-.17,.257))
    return root


if __name__=='__main__':
    report=[]
    for slug,func,target,distance,size in [
      ('wall_icon',wall_icon,(0,0,.34),1,.8),
      ('hanging_banner',banner,(0,0,.65),1.8,1.6),
      ('wall_sconce',sconce,(0,0,.15),.5,.4),
      ('wall_bench',bench,(0,0,.48),2,1.8),
      ('side_table',side_table,(0,0,.4),1,1),
      ('flower_vase',vase,(0,0,.3),.8,.8),
      ('hanging_lamp',oil_lamp,(0,0,.4),1,1),
      ('chandelier',chandelier,(0,0,.3),2,1.5),
      ('chancel_steps',steps,(0,-.5,.15),4,7.4),
      ('chancel_carpet',carpet,(0,-.75,.1),2,2),
    ]:
        row=base.save_asset(slug,func(),target,distance,size,render_preview=False)
        report.append(row)
        print('DECOR_READY',slug,flush=True)
    (base.REPORTS/'fidelity/decor_build.json').write_text(json.dumps(report,indent=2)+'\n')
