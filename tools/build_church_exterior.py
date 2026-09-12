"""Stone portal, slate roof and courtyard kit authored from concept frame 01."""
import json
import math
import random
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_church_assets as kit
base=kit.base


def roof():
    root=base.begin('ChurchRoof');p=kit.palette()
    copper=base.material('PatinatedCopper',(.11,.17,.145),.72,.57)
    dark=base.material('DarkWindow',(.015,.020,.018),0,.9)
    body=kit.extrude('RoofSubstrate',[(-3.85,.25),(3.85,.25),(0,2.75)],11.4,p['slate'],root)
    body.data.materials.append(p['plaster'])
    # The vault occupies the roof void; omit the underside.
    import bmesh
    bm=bmesh.new();bm.from_mesh(body.data);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.faces[2]],context='FACES_ONLY');bm.to_mesh(body.data);bm.free()
    for face in body.data.polygons:
        if abs(face.normal.y)>.9:face.material_index=1
    rng=random.Random(55);slope=math.atan2(2.50,3.85)
    # Overlapping slate courses retain a broken silhouette at the eaves.
    for side in [-1,1]:
        for row in range(16):
            x=(row+.5)*3.85/16
            for col in range(40):
                y=-5.95+(col+.5)*.298+(row%2)*.149
                if y>5.97:continue
                tile=kit.box('SlateTile',(.345,.307,.014),(side*x,y,.25+(1-x/3.85)*2.50+.022+rng.uniform(-.004,.004)),p['slate'],root,.004)
                tile.rotation_euler.y=side*slope
        kit.box('Fascia',(.105,12.08,.23),(side*3.83,0,.115),p['wood'],root,.008)
        # Half-round gutters, a narrow seam along the real roof edge.
        kit.trim_curve('Gutter',[(side*3.94,-6,.12),(side*3.94,6,.12)],.037,copper,root)
    for y in [-5.59,5.59]:
        kit.box('GableFrieze',(7.4,.25,.28),(0,y,.14),p['plaster'],root)
        for side in [-1,1]:
            kit.trim_curve('Bargeboard',[(side*3.91,y*1.077,.25),(0,y*1.077,2.79)],.07,p['wood'],root)
    for y in np.arange(-5.9,6.0,.30):
        cap=base.lathe('RidgeCap',[(.072,0),(.082,.02),(.076,.30)],copper,root,20)
        cap.rotation_euler.x=math.pi/2;cap.location=(0,y,2.81)
    dome=base.empty('Cupola',root,(0,-3.90,2.50))
    base.lathe('Drum',[(.47,0),(.49,.06),(.47,.09),(.47,1.08),(.52,1.11),(.52,1.17)],p['plaster'],dome,96)
    for i in range(8):
        angle=math.tau*i/8
        niche=base.empty('DrumNiche',dome,(math.sin(angle)*.474,-math.cos(angle)*.474,.28));niche.rotation_euler.z=angle
        kit.box('Slit',(.13,.012,.49),(0,0,.245),dark,niche,0)
        outline=[(-.065,0),(.065,0),(.065,.49)]+[(.065*math.cos(a),.49+.065*math.sin(a)) for a in np.linspace(0,math.pi,17)]
        kit.extrude('ArchedSlit',outline,.013,dark,niche)
        kit.arch('StoneArch',.071,.042,.49,.048,p['stone'],niche,16)
        for x in [-.09,.09]:kit.box('SlitJamb',(.04,.045,.49),(x,0,.245),p['stone'],niche)
    profile=[(.50,1.13),(.59,1.20),(.65,1.33),(.66,1.46),(.60,1.63),(.45,1.83),(.25,2.00),(.07,2.17),(.025,2.22)]
    base.lathe('OnionDome',profile,copper,dome,128)
    for a in np.linspace(0,math.tau,13)[:-1]:
        kit.trim_curve('CopperStandingSeam',[((r+.005)*math.cos(a),(r+.005)*math.sin(a),z) for r,z in profile],.004,copper,dome)
    base.lathe('CrossBall',[(.013,2.20),(.07,2.26),(.078,2.31),(.03,2.39)],p['brass'],dome,32)
    kit.box('CrossStem',(.034,.034,.68),(0,0,2.65),p['brass'],dome,.003)
    for z,width in [(2.88,.20),(2.73,.38),(2.48,.21)]:
        bar=kit.box('Crossbar',(width,.032,.029),(0,0,z),p['brass'],dome,.002)
        if z<2.5:bar.rotation_euler.y=-.23
    return root


def facade():
    root=base.begin('StoneFacade');p=kit.palette();rng=random.Random(67)
    # Individual voussoirs keep the stone joints radial around the opening.
    for i in range(13):
        a=i*math.pi/13+.003;b=(i+1)*math.pi/13-.003
        outline=[(.85*math.cos(a),2.16+.85*math.sin(a)),(1.14*math.cos(a),2.16+1.14*math.sin(a)),(1.14*math.cos(b),2.16+1.14*math.sin(b)),(.85*math.cos(b),2.16+.85*math.sin(b))]
        stone=kit.extrude('ArchStone',outline,.30,p['stone'],root);stone.location.y=-5.73
        bevel=stone.modifiers.new('StoneWear','BEVEL');bevel.width=.011;bevel.segments=2
        stone.modifiers.new('StoneNormals','WEIGHTED_NORMAL')
    for x in [-.998,.998]:
        for i in range(7):kit.box('PortalJamb',(.287,.34,.285),(x,-5.72,.172+.15+i*.285),p['stone'],root,.014)
        kit.box('Impost',(.36,.41,.105),(x,-5.72,2.19),p['stone'],root,.011)
    for x in [-3.50,3.50]:
        for i in range(12):
            width=.54 if i%2==0 else .40
            kit.box('Quoin',(width,.41,.274),(x,-5.52,.172+.14+i*.282),p['stone'],root,.014)
    for x in [-3.04,-2.48,-1.92,-1.37,1.37,1.92,2.48,3.04]:
        kit.box('FoundationStone',(.54,.43,.50),(x,-5.51,.062),p['stone'],root,.018)
    for x in [-3.50,3.50]:
        kit.box('SideFoundation',(.48,11.4,.50),(x,0,.062),p['stone'],root,.020)
    kit.box('RearFoundation',(7.4,.45,.50),(0,5.5,.062),p['stone'],root,.020)
    kit.box('FacadeCrossStem',(.084,.082,.63),(0,-5.745,4.30),p['stone'],root,.008)
    kit.box('FacadeCrossbar',(.42,.082,.083),(0,-5.745,4.41),p['stone'],root,.008)
    for obj in root.children:
        obj.location.z += .188
    return root


def entry_steps():
    root=base.begin('EntrySteps');p=kit.palette()
    for i in range(3):
        depth=1.22-i*.35;width=2.70-i*.12
        kit.box('StoneStep',(width,depth,.12),(0,-depth/2,.06+i*.12),p['stone'],root,.016)
    return root


def garden_wall():
    root=base.begin('GardenWall');p=kit.palette();rng=random.Random(44)
    for row in range(3):
        for col in range(6):
            width=.32+rng.uniform(-.035,.03)
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1)
            rock=bpy.context.object;rock.name='RoughStone';rock.parent=root
            for v in rock.data.vertices:v.co *= rng.uniform(.88,1.10)
            rock.dimensions=(width+.03,.43+rng.uniform(-.04,.04),.22+rng.uniform(-.02,.02))
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
            rock.location=(-.86+col*.344+(row%2)*.035,rng.uniform(-.025,.025),.145+row*.19)
            rock.rotation_euler.z=rng.uniform(-.12,.12)
            rock.data.materials.append(p['stone']);kit.uv_box(rock.data,p['stone'],(rng.random(),rng.random()))
            bevel=rock.modifiers.new('WornEdges','BEVEL');bevel.width=.008;bevel.segments=2
            rock.modifiers.new('StoneNormals','WEIGHTED_NORMAL')
    # A buried foundation pins the module to its placement plane.
    kit.box('WallBed',(2.10,.41,.07),(0,0,.035),p['stone'],root,.015)
    return root


def lantern():
    root=base.begin('EntranceLantern');p=kit.palette()
    glass=base.material('LanternGlass',(.80,.33,.05),0,.26)
    kit.box('WallPlate',(.085,.025,.28),(0,.09,.30),p['iron'],root,.008)
    kit.trim_curve('LanternBracket',[(0,.08,.40),(0,-.04,.47),(0,-.20,.41)],.014,p['iron'],root)
    base.lathe('LanternRoof',[(.105,.27),(.09,.30),(.02,.37)],p['iron'],root,4).location.y=-.20
    base.lathe('Glazing',[(.055,.05),(.075,.25)],glass,root,4).location.y=-.20
    base.lathe('LanternFoot',[(.012,0),(.08,.045),(.08,.055)],p['iron'],root,4).location.y=-.20
    for a in [0,math.pi/2,math.pi,math.pi*1.5]:
        kit.trim_curve('IronCorner',[(.055*math.cos(a),-.20+.055*math.sin(a),.05),(.075*math.cos(a),-.20+.075*math.sin(a),.25)],.007,p['iron'],root)
    base.empty('LightAnchor',root,(0,-.20,.15))
    return root


if __name__=='__main__':
    rows=[]
    for slug,builder,target,distance,size in [('church_roof',roof,(0,0,2),10,14),('stone_facade',facade,(0,-5.6,2.1),8,9),('entry_steps',entry_steps,(0,-.6,.2),3,3.2),('garden_wall',garden_wall,(0,0,.3),2,2.5),('entrance_lantern',lantern,(0,-.1,.22),.6,.6)]:
        rows.append(base.save_asset(slug,builder(),target,distance,size,render_preview=False))
        print('EXTERIOR_READY',slug,flush=True)
    (base.REPORTS/'fidelity/exterior_build.json').write_text(json.dumps(rows,indent=2)+'\n')
