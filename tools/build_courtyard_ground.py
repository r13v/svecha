"""Low stone path, scan-based soil and small 3D grass tufts for the church court."""
import json,math,random,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_church_assets as kit
base=kit.base


def ground():
    root=base.begin('CourtyardGround')
    mat=base.material('GrassSoil',(.18,.20,.07),0,.95)
    nx=128;ny=128
    verts=[];faces=[]
    for j in range(ny+1):
        y=-80+160*j/ny
        for i in range(nx+1):
            x=-80+160*i/nx
            height=.038+.023*math.sin(x*.6)*math.sin(y*.8)+.010*math.sin(x*2.3+y*.27)
            if abs(x)<1.6 and y<-5.7:height=.005
            distance=math.sqrt(x*x+y*y)
            height+=min(1,max(0,distance-18)/30)*(2.5+1.3*math.sin(x*.04)+1.2*math.cos(y*.035))
            if i==0 or j==0:height=0
            verts.append((x,y,height))
    for j in range(ny):
        for i in range(nx):
            k=j*(nx+1)+i;faces.append((k,k+1,k+nx+2,k+nx+1))
    mesh=bpy.data.meshes.new('Soil');mesh.from_pydata(verts,[],faces);mesh.update();mesh.materials.append(mat)
    layer=mesh.uv_layers.new()
    for f in mesh.polygons:
        f.use_smooth=True
        for index in f.loop_indices:
            p=mesh.vertices[mesh.loops[index].vertex_index].co;layer.data[index].uv=(p.x/2,p.y/2)
    obj=bpy.data.objects.new('Soil',mesh);bpy.context.collection.objects.link(obj);obj.parent=root
    return root


def path():
    root=base.begin('StoneApproach');p=kit.palette();rng=random.Random(91)
    dirt=base.material('PackedEarth',(.18,.14,.09),0,.98)
    kit.box('PathBed',(2.50,15,.015),(0,-13.25,.0075),dirt,root,0)
    for row in range(25):
        for col in range(4):
            width=.53+rng.uniform(-.045,.04);length=.53+rng.uniform(-.04,.04)
            x=(col-1.5)*.555+rng.uniform(-.022,.022)
            y=-6.16-row*.587+(col%2)*.12
            obj=kit.box('Flagstone',(width,length,.062+rng.uniform(-.01,.01)),(x,y,.045+rng.uniform(-.006,.006)),p['stone'],root,.024)
            obj.rotation_euler.z=rng.uniform(-.018,.018)
    return root


def grass():
    root=base.begin('GrassTuft');rng=random.Random(85)
    mat=base.material('GrassBlade',(.23,.25,.065),0,.96);mat.use_backface_culling=False
    verts=[];faces=[];colors=[]
    for i in range(12):
        a=rng.random()*math.tau;r=rng.random()*.06;height=rng.uniform(.075,.24);bend=rng.uniform(.015,.067)
        center=(math.cos(a)*r,math.sin(a)*r)
        width=rng.uniform(.003,.008)
        side=(math.cos(a+1.2),math.sin(a+1.2))
        begin=len(verts)
        for z,t,w in [(0,0,width),(.48*height,.35,width*.72),(height,1,0)]:
            for sign in [-1,1]:
                verts.append((center[0]+math.cos(a)*bend*t+side[0]*w*sign,center[1]+math.sin(a)*bend*t+side[1]*w*sign,z))
                colors.append((.35+rng.random()*.60,.65,.25,1))
        faces.extend([(begin,begin+1,begin+3,begin+2),(begin+2,begin+3,begin+5,begin+4)])
    mesh=bpy.data.meshes.new('Grass');mesh.from_pydata(verts,[],faces);mesh.materials.append(mat)
    channel=mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='POINT')
    for point,color in zip(channel.data,colors):point.color=color
    obj=bpy.data.objects.new('Grass',mesh);bpy.context.collection.objects.link(obj);obj.parent=root
    return root


if __name__=='__main__':
    report=[]
    for slug,builder,target,distance,size in [('courtyard_ground',ground,(0,0,0),24,40),('stone_approach',path,(0,-13,.1),12,17),('grass_tuft',grass,(0,0,.12),.3,.35)]:
        report.append(base.save_asset(slug,builder(),target,distance,size,render_preview=False))
        print('GROUND_READY',slug,flush=True)
    (base.REPORTS/'fidelity/ground_build.json').write_text(json.dumps(report,indent=2)+'\n')
