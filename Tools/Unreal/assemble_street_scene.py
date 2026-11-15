"""Repeatable approved-asset dressing of L_SakuraStreet. Run with Unreal Python.

Preserves roads, sidewalk geometry, boundaries, spawn, fixed camera and player.
Only known graybox building/tree placeholders and this script's tagged actors
are replaced. A byte-for-byte pre-edit map backup is retained under Saved.
"""
import hashlib, json, math, shutil, traceback
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
assert Path(unreal.Paths.project_dir()).resolve() == ROOT
OUT = ROOT/'Saved/StreetAssembly'; OUT.mkdir(parents=True, exist_ok=True)
MAP = '/Game/SakuraDays/Maps/L_SakuraStreet'
TAG = 'SakuraDaysStreetAssembly'
RECIPE = 'street_assembly_v1'
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
REPORT = {'recipe':RECIPE, 'map':MAP, 'errors':[], 'placed':[], 'removed_graybox':[]}
DESIRED = set()

def hashfile(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write_report(): (OUT/'assembly.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
def vec(v): return unreal.Vector(*v)
def rgb(h):
    vals=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return [v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in vals]

def material(name, color, pattern=''):
    fingerprint=hashlib.sha256((name+color+pattern).encode()).hexdigest()[:10]
    folder='/Game/SakuraDays/Environment/Street/Materials'
    path=folder+'/M_'+name+'_'+fingerprint
    if EAL.does_asset_exist(path):
        m=unreal.load_asset(path)
        if EAL.get_metadata_tag(m,'SakuraDays.StreetMaterial')!=fingerprint:
            raise RuntimeError('Unowned material preserved: '+path)
        return m
    m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_'+name+'_'+fingerprint,folder,unreal.Material,unreal.MaterialFactoryNew())
    base=MEL.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-300,0)
    base.set_editor_property('constant',unreal.LinearColor(*rgb(color),1))
    if pattern:
        world=MEL.create_material_expression(m,unreal.MaterialExpressionWorldPosition,-600,-100)
        custom=MEL.create_material_expression(m,unreal.MaterialExpressionCustom,-100,0)
        custom_inputs=[]
        for pin in ('P','C'):
            item=unreal.CustomInput();item.set_editor_property('input_name',pin);custom_inputs.append(item)
        custom.set_editor_property('inputs',custom_inputs)
        custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        if pattern=='paving':
            code='float2 q=P.xy/65.0; q.x+=fmod(floor(q.y),2.0)*0.5; float2 f=frac(q); float e=min(min(f.x,1-f.x),min(f.y,1-f.y)); float g=smoothstep(0.008,0.022,e); return C*(0.78+0.22*g);'
        elif pattern=='tactile':
            code='float f=frac(P.y/6.0); float rib=smoothstep(0.06,0.16,f)*(1-smoothstep(0.65,0.85,f)); return C*(0.78+0.22*rib);'
        else:
            code='float2 q=P.xz/42.0; q.x+=fmod(floor(q.y),2.0)*0.5; float2 f=frac(q); float e=min(min(f.x,1-f.x),min(f.y,1-f.y)); return C*(0.78+0.22*smoothstep(0.01,0.025,e));'
        custom.set_editor_property('code',code)
        assert MEL.connect_material_expressions(world,'',custom,'P')
        assert MEL.connect_material_expressions(base,'',custom,'C')
        base=custom
    assert MEL.connect_material_property(base,'',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=MEL.create_material_expression(m,unreal.MaterialExpressionConstant,-100,180);rough.set_editor_property('r',.92)
    assert MEL.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    spec=MEL.create_material_expression(m,unreal.MaterialExpressionConstant,-100,260);spec.set_editor_property('r',.12)
    assert MEL.connect_material_property(spec,'',unreal.MaterialProperty.MP_SPECULAR)
    errors=MEL.recompile_material(m)
    if errors: raise RuntimeError('Street material compilation: '+str(errors))
    EAL.set_metadata_tag(m,'SakuraDays.StreetMaterial',fingerprint)
    EAL.save_loaded_asset(m,only_if_is_dirty=False)
    return m

def actor(name, cls=unreal.StaticMeshActor, group='Details'):
    label='SD_'+name; DESIRED.add(label)
    a=EXISTING.get(label)
    if a and not a.actor_has_tag(TAG): raise RuntimeError('Unowned actor name preserved: '+label)
    if not a:
        a=ACTORS.spawn_actor_from_class(cls,vec((0,0,0)))
        a.set_actor_label(label);a.set_editor_property('tags',[TAG]);EXISTING[label]=a
    a.set_folder_path('SakuraDays/'+group)
    return a

def mesh(name, asset, pos, yaw=0, scale=(1,1,1), group='Props', collision=True, mat=None):
    a=actor(name,group=group); c=a.static_mesh_component
    c.set_static_mesh(asset);c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    a.set_actor_location(vec(pos),False,False)
    a.set_actor_rotation(unreal.Rotator(pitch=0,yaw=yaw,roll=0),False)
    a.set_actor_scale3d(vec(scale))
    if mat:c.set_material(0,mat)
    REPORT['placed'].append({'label':a.get_actor_label(),'asset':asset.get_path_name(),'position_cm':list(pos),'yaw':yaw,'scale':list(scale),'collision':collision})
    return a

def box(name,pos,size,mat,yaw=0,group='Street',collision=True):
    return mesh(name,BASIC['Cube'],pos,yaw,tuple(v/100 for v in size),group,collision,mat)

def beam(name,a,b,radius,mat,group='Utilities'):
    mid=tuple((x+y)*.5 for x,y in zip(a,b));length=math.dist(a,b)
    obj=mesh(name,BASIC['Cylinder'],mid,0,(radius/50,radius/50,length/100),group,False,mat)
    direction=vec(tuple(y-x for x,y in zip(a,b)))
    obj.set_actor_rotation(unreal.MathLibrary.make_rot_from_z(direction),False)
    return obj

try:
    imported=json.loads((OUT/'imports.json').read_text(encoding='utf-8'))
    if not imported.get('passed') or imported.get('errors') or imported.get('mode')=='plan':
        raise RuntimeError('Passed street imports are required')
    KIT={k:unreal.load_asset(v) for k,v in imported['assets'].items()}
    if any(not isinstance(v,unreal.StaticMesh) for v in KIT.values()):raise RuntimeError('Missing approved mesh')
    headless='-run=' in unreal.SystemLibrary.get_command_line().lower()
    level_subsystem=None if headless else unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if level_subsystem and level_subsystem.is_in_play_in_editor():raise RuntimeError('End PIE normally before assembly')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Save unsaved map changes normally before assembly')
    source=ROOT/'Content/SakuraDays/Maps/L_SakuraStreet.umap'
    backup_dir=OUT/'Backups';backup_dir.mkdir(exist_ok=True)
    backup=backup_dir/('L_SakuraStreet_'+hashfile(source)[:16]+'.umap')
    if not backup.exists(): shutil.copy2(source,backup)
    REPORT['backup']=str(backup.relative_to(ROOT))
    assert unreal.EditorLevelLibrary.load_level(MAP)
    ACTORS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    WORLD=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert WORLD.get_name()=='L_SakuraStreet'
    EXISTING={a.get_actor_label():a for a in ACTORS.get_all_level_actors()}
    protected=['Prototype_Road','Prototype_LeftSidewalk','Prototype_RightSidewalk','PlayerStart_SakuraStreet','CAM_SakuraStreet_Reference']
    def transform(a):
        p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
        return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
    before={n:transform(EXISTING[n]) for n in protected}
    REPORT['protected_before']=before
    # Replace only the prior task's named placeholder objects, after backing up.
    for name,a in list(EXISTING.items()):
        remove=name.startswith(('GB_Cafe_','GB_Tree')) or (name.startswith('GB_House') and not name.endswith('_Plot'))
        if remove:
            ACTORS.destroy_actor(a);EXISTING.pop(name);REPORT['removed_graybox'].append(name)
    BASIC={n:unreal.load_asset('/Engine/BasicShapes/'+n) for n in ('Cube','Cylinder','Sphere')}
    MAT={name:material(name,color,pattern) for name,color,pattern in [
        ('Road','757987',''),('Paving','BFB8B5','paving'),('Stone','B5ACA7','stone'),
        ('Earth','68735D',''),('Cream','D8C9B6',''),('Dark','3D3948',''),
        ('Leaf','6D8B60',''),('LeafLight','8BA574',''),('Yellow','D8AE48',''),
        ('White','E6E1D7',''),('Tactile','D8B24E','tactile'),('Pink','E6A9CC','')]}
    for name,a in EXISTING.items():
        if name=='Prototype_Road':a.static_mesh_component.set_material(0,MAT['Road'])
        elif 'Sidewalk' in name or name.endswith('_Plot'):a.static_mesh_component.set_material(0,MAT['Paving'])
        elif name=='Prototype_Ground':a.static_mesh_component.set_material(0,MAT['Earth'])
        elif name.startswith('Prototype_') and 'Boundary' in name:a.static_mesh_component.set_material(0,MAT['Cream'])
        elif name=='GB_Road_CenterLine':a.static_mesh_component.set_material(0,MAT['Yellow'])
        elif name.startswith('GB_Road_Edge'):a.static_mesh_component.set_material(0,MAT['White'])

    # Approved buildings: same human scale, facades face the street.
    mesh('Cafe_HANA',KIT['cafe'],(180,-950,15),90,group='Buildings')
    box('Cafe_Apron',(180,-580,5),(1000,260,20),MAT['Paving'])
    for name,x,y,yaw in [('House01',1900,-1000,90),('House02',1100,1200,-90),('House03',3300,1200,-90),
                          ('House04',3500,-1000,90),('House05',-200,1200,-90)]:
        mesh(name,KIT['house'],(x,y,15),yaw,group='Buildings')
        front=y+450 if y<0 else y-450
        box(name+'_Path',(x,front,5),(160,300,20),MAT['Paving'])
    # Repeated kit beyond the playable end creates a neighborhood backdrop.
    for i,(x,y,yaw) in enumerate([(5480,-900,90),(5480,1250,-90),(5180,150,180)]):
        mesh('BackgroundHouse%02d'%i,KIT['house'],(x,y,15),yaw,group='Background',collision=i==2)

    trees=[('HeroCafe','tree_hero',1000,-500,.93,15),('NearLeft','tree_spread',1450,-195,.9,40),
           ('LeftMiddle','tree_spread',2800,-195,1.0,115),('LeftFar','tree_hero',4200,-195,.85,70),
           ('RightNear','tree_spread',300,490,.93,130),('RightMiddle','tree_hero',2100,490,.85,195),
           ('RightFar','tree_spread',4000,490,1.05,15),('GardenWeeping','tree_weeping',2600,1150,.86,40),
           ('BackLeft','tree_spread',5200,-400,1.0,15),('BackRight','tree_weeping',5500,700,.9,130)]
    for name,key,x,y,s,yaw in trees:
        mesh('Sakura_'+name,KIT[key],(x,y,15),yaw,(s,s,s),'Trees',collision=x<4900)
        if x<4900:
            box('TreePit_'+name,(x,y,15.6),(100,100,1),MAT['Earth'],collision=False)
            # Low unobtrusive border below the capsule's normal step height.
            for j,(dx,dy,w,d) in enumerate([(-52,0,8,112),(52,0,8,112),(0,-52,96,8),(0,52,96,8)]):
                box('PitRim_'+name+str(j),(x+dx,y+dy,18),(w,d,6),MAT['Stone'],collision=False)

    # Street furniture stays in the furnishing margins, clear of the main lanes.
    for i,(x,y,yaw) in enumerate([(1600,-540,90),(3350,835,-90)]):
        mesh('Bench%02d'%i,KIT['bench'],(x,y,15),yaw)
        mesh('PotBench%02d'%i,KIT['pot'],(x+130,y,15),yaw)
    for i,(x,y) in enumerate([(40,-540),(780,-540),(1800,-590),(3700,835),(850,835)]):
        mesh('Planter%02d'%i,KIT['planter'],(x,y,15),90)
    for i,(x,y) in enumerate([(650,-185),(2350,-185),(3700,-185),(1250,490),(3100,490)]):
        mesh('Lamp%02d'%i,KIT['lamp'],(x,y,15),90)
    # Matte boundary walls, gate gaps and garden green masses.
    for i,(x,y,width) in enumerate([(1350,-590,240),(2450,-590,280),(3000,-590,200),(4050,-590,300),
                                   (500,855,230),(1700,855,260),(2750,855,250),(3900,855,200)]):
        box('GardenWall%02d'%i,(x,y,80),(width,25,130),MAT['Stone'],group='Gardens')
        box('GardenCap%02d'%i,(x,y,149),(width+12,35,10),MAT['Cream'],group='Gardens')
        for j in range(3):
            mesh('Shrub%02d_%d'%(i,j),BASIC['Sphere'],(x+(j-1)*width/3,y+(65 if y>0 else -65),165),0,
                 (width/260,1.05,1.15),'Gardens',False,MAT['Leaf'] if j%2 else MAT['LeafLight'])
    # Utilities provide the reference's strong receding verticals and wire lines.
    poles=[(1350,-170),(2900,-170),(4400,-170),(5950,-170)]
    for i,(x,y) in enumerate(poles):
        pole=beam('Pole%02d'%i,(x,y,15),(x,y,890),9,MAT['Stone'])
        pole.static_mesh_component.set_collision_profile_name('BlockAll')
        beam('Crossarm%02d'%i,(x,y-90,825),(x,y+90,825),4,MAT['Dark'])
        for j,z in enumerate([72,100,128]):
            band=mesh('PoleBand%02d_%d'%(i,j),BASIC['Cylinder'],(x,y,z),0,(.185,.185,.14),'Utilities',False,MAT['Yellow'] if j%2==0 else MAT['Dark'])
        for j,dy in enumerate([-80,0,80]):
            beam('Insulator%02d_%d'%(i,j),(x,y+dy,817),(x,y+dy,850),5,MAT['White'])
    for i in range(len(poles)-1):
        x1,y1=poles[i];x2,y2=poles[i+1]
        for cable,offset in enumerate([-80,0,80]):
            for segment in range(10):
                def pt(t):return (x1+(x2-x1)*t,y1+offset,850-65*4*t*(1-t))
                beam('Cable%d_%d_%d'%(i,cable,segment),pt(segment/10),pt((segment+1)/10),1.15,MAT['Dark'])
    # Readable pavement, curbs, tactile route and road paint; no added collision lips.
    for side,y in [('Left',-235),('Right',690)]:
        box('Tactile'+side,(2000,y,15.8),(5800,32,1),MAT['Tactile'],collision=False)
    for side,y in [('Left',-153),('Right',453)]:
        box('Curb'+side,(2000,y,8),(6000,10,16),MAT['Stone'],collision=False)
    for i,(x,y,yaw) in enumerate([(825,-37.5,-26.565),(975,-37.5,26.565),(975,37.5,-26.565),(825,37.5,26.565)]):
        box('RoadDiamond%d'%i,(x,y,1.3),(167.7,10,1),MAT['White'],yaw,collision=False)
    for i in range(7):box('Crossing%d'%i,(4370, -110+i*80,1.4),(120,35,1),MAT['White'],collision=False)

    # Keep end boundaries physically intact; soften their garden setting.
    for i in range(11):
        mesh('EndHedge%d'%i,BASIC['Sphere'],(5010,-1250+i*270,330),0,(3.5,3.0,1.4),'Background',False,MAT['Leaf'])
    # Save only this map plus our newly-created materials. Existing gameplay untouched.
    light=EXISTING.get('DirectionalLight')
    if light:
        light.set_actor_rotation(unreal.Rotator(pitch=-38,yaw=-35,roll=0),False)
        light.light_component.set_intensity(7.0)
    camera=EXISTING['CAM_SakuraStreet_Reference']
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
    for name,a in list(EXISTING.items()):
        if a.actor_has_tag(TAG) and name not in DESIRED:ACTORS.destroy_actor(a)
    after={n:transform(EXISTING[n]) for n in protected}
    if after!=before:raise RuntimeError('Protected street transforms changed')
    REPORT['protected_after']=after
    REPORT['actor_count']=len(ACTORS.get_all_level_actors())
    if not unreal.EditorLevelLibrary.save_current_level():raise RuntimeError('Level save failed')
    REPORT['passed']=True;write_report();unreal.log('STREET_ASSEMBLY_COMPLETE '+str(REPORT['actor_count']))
except Exception:
    REPORT['passed']=False;REPORT['errors'].append(traceback.format_exc());write_report();raise
