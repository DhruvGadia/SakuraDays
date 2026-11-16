"""Layer Prompt 12 improvements over the saved street, never rebuild its base.

SAKURA_TOWN_STAGE=geometry|identity|materials|lighting. Run each stage, then PIE.
Existing assets are reused with actor-local materials; new imports are revisions.
"""
import hashlib, json, math, os, shutil, sys, traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from town_common import *

STAGE=os.environ.get('SAKURA_TOWN_STAGE','geometry')
assert STAGE in ('geometry','identity','materials','lighting')
REPORT={'stage':STAGE,'passed':False,'errors':[]}
PROTECTED=['Prototype_Road','Prototype_LeftSidewalk','Prototype_RightSidewalk','PlayerStart_SakuraStreet','CAM_SakuraStreet_Reference']

def world_local(a,p):
    loc=a.get_actor_location();yaw=math.radians(a.get_actor_rotation().yaw)
    return (loc.x+p[0]*math.cos(yaw)-p[1]*math.sin(yaw),loc.y+p[0]*math.sin(yaw)+p[1]*math.cos(yaw),loc.z+p[2])

def facade_override(a,colors):
    c=a.static_mesh_component
    for i,(name,h) in enumerate(colors):c.set_material(i,material(name,h,'siding' if i==1 else ''))

def geometry(s):
    stone=material('WarmStone','A7A5A4','blocks');trim=material('PlumEdges','45414D')
    concrete=material('PoleConcrete','B7B5B0');metal=material('Metal','696D77');cream=material('EaveCream','DBD3C5')
    pale=material('Paper','E5DDCF');green=material('GardenGreen','658665');roof=material('RoofBlue','565C72')
    white=material('RoadWhite','DFDFDB');yellow=material('HazardYellow','D8AC3D')
    # Retain the existing perimeter physics, screen it with authored town context.
    hidden=[]
    for name,a in s.existing.items():
        if name.startswith('Prototype_') and 'Boundary' in name:
            a.static_mesh_component.set_visibility(False,True)
            hidden.append(name)
    REPORT['preserved_invisible_boundary_collision']=hidden
    # Open the ramen frontage by moving its existing framing tree into the rear garden.
    for name,a in s.existing.items():
        if name=='SD_Sakura_HeroCafe':
            a.set_actor_location(unreal.Vector(980,-1350,15),False,False)
        elif name=='SD_TreePit_HeroCafe':
            a.set_actor_location(unreal.Vector(980,-1350,15.6),False,False)
        elif name.startswith('SD_PitRim_HeroCafe'):
            j=int(name[-1]);dx,dy=[(-52,0),(52,0),(0,-52),(0,52)][j]
            a.set_actor_location(unreal.Vector(980+dx,-1350+dy,18),False,False)
        elif name=='SD_Sakura_NearLeft':
            a.set_actor_location(unreal.Vector(1750,-195,15),False,False)
        elif name=='SD_TreePit_NearLeft':
            a.set_actor_location(unreal.Vector(1750,-195,15.6),False,False)
        elif name.startswith('SD_PitRim_NearLeft'):
            j=int(name[-1]);dx,dy=[(-52,0),(52,0),(0,-52),(0,52)][j]
            a.set_actor_location(unreal.Vector(1750+dx,-195+dy,18),False,False)
    # Continuous visual ground supports scenery beyond the compact collision floor.
    s.box('DistantGround',(2000,150,-40),(30000,25000,50),green,folder='Background')
    for key,p,size in [('West',(2000,-2750,0),(15000,2500,30)),('East',(2000,3000,0),(15000,2300,30)),('Far',(9000,150,0),(8000,8000,30)),('Near',(-3000,150,0),(4000,8000,30))]:
        s.box('TownGround'+key,p,size,green,folder='Background')
    s.existing['SD_BackgroundHouse02'].set_actor_location(unreal.Vector(6100,150,15),False,False)
    for name,a in s.existing.items():
        if name.startswith('SD_EndHedge') and abs(a.get_actor_location().y-150)<600:
            a.static_mesh_component.set_visibility(False,True)
    # Front garden walls stay at believable shoulder/waist height with slatted fences.
    for i,(x,y,width) in enumerate([(1900,-590,620),(3500,-590,620),(1100,855,600),(3300,855,620),(-200,855,600)]):
        for side in (-1,1):
            span=width/2-90;cx=x+side*(90+span/2)
            s.box('GardenLowWall%02d_%d'%(i,side),(cx,y,55),(span,22,80),stone,collision=True,folder='Residential')
            for j in range(4):
                s.box('Fence_%d_%d_%d'%(i,side,j),(cx-span*.4+j*span*.267,y,120),(10,8,52),trim,folder='Residential')
            s.box('FenceRail%d_%d'%(i,side),(cx,y,144),(span,9,8),trim,folder='Residential')
    # Existing modules remain. Add roof machinery, gutter downpipes and window shutters.
    for i,name in enumerate(['SD_House01','SD_House02','SD_House03','SD_House04','SD_House05']):
        a=s.existing[name];yaw=a.get_actor_rotation().yaw
        for side in (-1,1):
            p=world_local(a,(305,side*385,300));q=world_local(a,(305,side*385,25))
            s.beam('Downpipe_%d_%d'%(i,side),p,q,3.5,metal,'Residential')
        # A compact utility box and meter, off the pedestrian corridor.
        s.box('Meter%d'%i,world_local(a,(307,280,145)),(16,28,38),cream,yaw,folder='Residential')
        # Side equipment is set back and its cables connect to the house.
        ac=OLD['ac'];s.mesh('ResidentialAC%d'%i,ac,world_local(a,(310,-270,35)),yaw,collision=False,folder='Residential')
        # Fine roof rails/solar panels on two rear slopes provide silhouette variety.
        if i in (1,3):
            panel=s.box('RoofPanel%d'%i,world_local(a,(-155,0,638)),(170,260,7),roof,yaw,folder='Residential')
            panel.set_actor_rotation(unreal.Rotator(pitch=18,yaw=yaw,roll=0),False)
        # Folded metal shutters flank selected upper windows, not every opening.
        for j,side in enumerate([-1,1]):
            s.box('Shutter%d_%d'%(i,j),world_local(a,(303,side*185,444)),(9,34,132),metal,yaw,folder='Residential')
        # Balcony laundry is a small everyday detail on two homes only.
        if i in (0,2):
            s.beam('LaundryRail%d'%i,world_local(a,(398,-130,450)),world_local(a,(398,130,450)),2.2,metal,'Residential')
            for j,h in enumerate(['D2DCE2','C8C1D4','E5DCCB']):
                s.box('Laundry%d_%d'%(i,j),world_local(a,(400,-75+j*70,416)),(2.5,45,62),material('Laundry'+str(j),h),yaw,folder='Residential')
    # Surface drainage follows both curbs; thin geometry has no collision lips.
    for side,y in [('L',-135),('R',435)]:
        s.box('DrainChannel'+side,(2000,y,1.2),(5800,20,1.4),metal,folder='Road')
        for i,x in enumerate(range(-650,4900,500)):
            s.box('DrainGrate%s%02d'%(side,i),(x,y,2.1),(70,24,1),trim,folder='Road')
            for j in range(5):s.box('GrateSlat%s%d_%d'%(side,i,j),(x-28+j*14,y,2.8),(5,25,1),metal,folder='Road')
    for i,x in enumerate([350,2500,4100]):
        s.mesh('Manhole%d'%i,s.cylinder,(x,225,1.2),scale=(.62,.62,.025),mat=metal,folder='Road')
        for j in (-1,0,1):s.box('ManholeLine%d_%d'%(i,j),(x,225+j*13,2.6),(44,2,1),trim,folder='Road')
    # Realistic overhead service cables, crossarm hardware and transformers.
    for i,(x,y) in enumerate([(1350,-170),(2900,-170),(4400,-170),(5950,-170)]):
        s.mesh('Transformer%d'%i,s.cylinder,(x,y-27,710),scale=(.5,.5,.9),mat=metal,folder='Utilities')
        s.beam('SecondaryCrossarm%d'%i,(x,y-100,725),(x,y+100,725),4,trim)
        for j,offset in enumerate([-65,60]):
            s.mesh('Porcelain%d_%d'%(i,j),s.cylinder,(x,y+offset,752),scale=(.10,.10,.32),mat=pale,folder='Utilities')
        for j,offset in enumerate([-100,-48,34,100]):
            if i==3:break
            x2=[2900,4400,5950][i]
            for k in range(8):
                def pt(t):return (x+(x2-x)*t,y+offset,740-95*4*t*(1-t))
                s.beam('LowCable%d_%d_%d'%(i,j,k),pt(k/8),pt((k+1)/8),.8,trim)
    for i,(start,end) in enumerate([((1350,-170,730),(1100,920,590)),((2900,-170,730),(1900,-690,590)),((4400,-170,730),(3500,-690,590))]):
        for k in range(8):
            def pt(t):return tuple(start[j]+(end[j]-start[j])*t-(35*4*t*(1-t) if j==2 else 0) for j in range(3))
            s.beam('ServiceDrop%d_%d'%(i,k),pt(k/8),pt((k+1)/8),.75,trim)
    # Small off-road residential parking bay, no misleading main-road stop marking.
    paving=material('ParkingSurface','777A84','asphalt')
    s.box('ParkingPad',(2770,-1130,-1),(550,560,20),paving,folder='Residential')
    for i,x in enumerate([2540,2770,3000]):s.box('ParkingStripe%d'%i,(x,-1130,10),(7,480,1),white,folder='Residential')
    for i,x in enumerate([2655,2885]):s.box('WheelStop%d'%i,(x,-1320,18),(100,18,15),concrete,collision=True,folder='Residential')
    # A modest shrine threshold terminates the small street instead of a bare wall.
    vermilion=material('ToriiVermilion','C95743');wood=material('Wood','735C4B')
    for i,x in enumerate([4860,4940,5020]):s.box('ShrineStep%d'%i,(x,150,10+i*18),(80,420,20+i*36),stone,collision=True,folder='Shrine')
    for side,y in enumerate([-25,325]):
        s.beam('ToriiPost%d'%side,(5050,y,65),(5050,y,430),17,vermilion,'Shrine')
        s.beam('ToriiBase%d'%side,(5050,y,65),(5050,y,120),18,trim,'Shrine')
    s.box('ToriiLintel',(5050,150,400),(28,430,32),vermilion,folder='Shrine')
    s.box('ToriiCrossbar',(5050,150,325),(24,390,23),vermilion,folder='Shrine')
    s.box('ToriiCap',(5050,150,428),(44,475,22),trim,folder='Shrine')
    s.box('ToriiTablet',(5028,150,360),(8,38,56),wood,folder='Shrine')
    s.box('ShrineCourt',(5440,150,55),(700,720,100),stone,folder='Shrine')
    # Rooflines on three sides and soft distant hills hide the edge of the prototype.
    placements=[(6200,-1100,90,.86),(6900,-500,90,.7),(6500,1350,-90,.82),(7600,700,180,.7),
                (-1700,-1200,90,.8),(-1600,1100,-90,.75),(800,-2250,90,.84),(2400,-2400,90,.92),(4200,-2200,90,.78),
                (500,2450,-90,.86),(2200,2400,-90,.78),(4200,2500,-90,.88),(-700,-1080,90,.92)]
    for i,(x,y,yaw,scale) in enumerate(placements):
        a=s.mesh('DistantHouse%02d'%i,OLD['house'],(x,y,15),yaw,(scale,scale,scale),folder='Background')
        a.static_mesh_component.set_cast_shadow(False)
        a.static_mesh_component.set_material(0,material('DistantPlaster'+str(i%3),['C3BCB0','B6C2C7','CDC3AE'][i%3]))
    s.box('NearNeighborPlot',(-700,-1080,0),(1000,870,30),green,folder='Background')
    for i,(x,y,z,size) in enumerate([(10500,-2800,-850,(85,55,25)),(11600,1800,-900,(75,65,31)),(9000,4200,-920,(52,60,23))]):
        a=s.mesh('Hill%02d'%i,s.sphere,(x,y,z),scale=size,mat=material('DistantHill'+str(i),'7C9A8B'),folder='Background')
        a.static_mesh_component.set_cast_shadow(False)
    # Five saved review views; the approved reference camera itself stays unchanged.
    s.camera('Camera_MainStreet',(-450,-180,225),(3000,90,220),75)
    s.camera('Camera_Hana',(480,360,220),(180,-700,290),64)
    s.camera('Camera_Residential',(1950,350,220),(1050,1100,400),68)
    s.camera('Camera_Storefront',(970,360,210),(980,-570,295),65)
    s.camera('Camera_StreetSign',(1170,160,230),(1350,-170,390),55)
    s.camera('Camera_Noticeboard',(4400,460,200),(4530,845,160),55)

def identity(s):
    imported=json.loads((OUT/'imports.json').read_text(encoding='utf-8'))
    assert imported.get('passed'), 'Validated town imports required'
    kit={k:unreal.load_asset(v) for k,v in imported['assets'].items()}
    # Keys are normalized by import_town_assets.py; front is +X in Unreal.
    s.mesh('RamenShop',kit['ramen'],(980,-800,15),90,collision=True,folder='Shops')
    paving=material('ShopApron','B8B3AD','tile')
    s.box('RamenApron',(980,-520,5),(650,180,20),paving,folder='Shops')
    s.mesh('HanaJapaneseSign',kit['hana_sign'],(15,-686,244),90,(.58,.58,.58),folder='Signs')
    s.mesh('HanaOpenSign',kit['open_sign'],(295,-687,167),90,folder='Signs')
    # Lettering faces +Y. Mount ahead of the pole so the pole cannot cover it.
    s.mesh('SakuraStreetSign',kit['street_sign'],(1350,-130,390),90,folder='Signs')
    s.box('StreetSignBracket',(1350,-151,407),(14,42,9),material('Metal','696D77'),folder='Signs')
    s.mesh('VendingMachine',kit['vending'],(635,-590,15),90,collision=True,folder='Shops')
    s.mesh('BicycleCafe',kit['bicycle'],(-160,-610,15),15,collision=True,folder='Props')
    s.mesh('BicycleHouse',kit['bicycle'],(1500,960,15),165,collision=True,folder='Residential')
    s.mesh('NeighborhoodNoticeboard',kit['noticeboard'],(4530,845,15),-90,collision=True,folder='Props')
    s.mesh('RoadMirror',kit['mirror'],(4720,490,15),-120,collision=True,folder='Road')
    for i,name in enumerate(['SD_House01','SD_House02','SD_House03','SD_House04','SD_House05']):
        a=s.existing[name]
        s.mesh('Mailbox%d'%i,kit['mailbox'],world_local(a,(455,195,0)),a.get_actor_rotation().yaw,collision=True,folder='Residential')
    REPORT['japanese_signs']={k:v for k,v in imported.get('signs',{}).items()}

def materials(s):
    palettes=[['D8CCB8','99ADB7'],['B9C8CD','718997'],['DED0AC','C2B493'],['C7C1CE','9EA5B4'],['DDD5C3','BCB6A9']]
    for i,name in enumerate(['SD_House01','SD_House02','SD_House03','SD_House04','SD_House05']):
        a=s.existing[name]
        facade_override(a,[('HousePlaster'+str(i),palettes[i][0]),('HouseSiding'+str(i),palettes[i][1]),('PlumEdges','45414D'),('Roof'+str(i),['545B6E','4B5B6A','66666F','53536A','5E5D67'][i]),('Timber'+str(i),['6F594D','565A62','7B6550','625762','716351'][i]),('WindowBlue','738B9D'),('WindowReflection','B7CCD7'),('Foundation','ADA9A2')])
    s.existing['Prototype_Road'].static_mesh_component.set_material(0,material('TownAsphalt','686F80','asphalt'))
    paving=material('TownPaving','B9B6B3','tile')
    for key in ['Prototype_LeftSidewalk','Prototype_RightSidewalk','SD_Cafe_Apron']:
        s.existing[key].static_mesh_component.set_material(0,paving)
    for name,a in s.existing.items():
        if name.startswith('SD_GardenWall'):a.static_mesh_component.set_material(0,material('TownWall','ABA8A2','blocks'))
    cafe=s.existing['SD_Cafe_HANA']
    # Keep HANA geometry/identity while tempering the old bright pink awning.
    slots=cafe.static_mesh_component.static_mesh.get_editor_property('static_materials')
    for i,slot in enumerate(slots):
        n=str(slot.material_slot_name).lower()
        if 'rose' in n or 'awning' in n:cafe.static_mesh_component.set_material(i,material('CafeRose','AC6E80'))

def lighting(s):
    sun=s.existing.get('DirectionalLight')
    if sun:
        sun.set_actor_rotation(unreal.Rotator(pitch=-36,yaw=-28,roll=0),False)
        sun.light_component.set_intensity(5.5)
        sun.light_component.set_light_color(unreal.LinearColor(1,.985,.96,1))
        sun.light_component.set_editor_property('light_source_angle',2.2)
        sun.light_component.set_dynamic_shadow_distance_movable_light(11000.)
        sun.light_component.set_dynamic_shadow_cascades(3)
    for a in s.existing.values():
        if isinstance(a,unreal.SkyLight):a.light_component.set_intensity(1.2)
    pp=s.actor('TownColorGrade',unreal.PostProcessVolume,'Lighting')
    pp.set_editor_property('unbound',True)
    settings=pp.get_editor_property('settings')
    for prop,value in [('override_bloom_intensity',True),('bloom_intensity',.08),('override_motion_blur_amount',True),('motion_blur_amount',0.),('override_auto_exposure_min_brightness',True),('auto_exposure_min_brightness',1.),('override_auto_exposure_max_brightness',True),('auto_exposure_max_brightness',1.),('override_auto_exposure_bias',True),('auto_exposure_bias',2.)]:
        settings.set_editor_property(prop,value)
    pp.set_editor_property('settings',settings)
    REPORT['lighting']={'sun_intensity':5.5,'sun_elevation':36,'skylight':1.2,'bloom':.08,'motion_blur':0,'exposure_min_max':1.,'exposure_bias':2.,'shadow_method':'Three cascaded shadow maps; hardware ray tracing remains disabled'}

try:
    src=ROOT/'Content/SakuraDays/Maps/L_SakuraStreet.umap'
    backups=OUT/'Backups';backups.mkdir(exist_ok=True)
    backup=backups/(STAGE+'_'+sha(src)[:16]+'.umap')
    if not backup.exists():shutil.copy2(src,backup)
    REPORT['backup']=str(backup.relative_to(ROOT))
    s=Scene();before={n:transform(s.existing[n]) for n in PROTECTED}
    OLD={k:unreal.load_asset(v) for k,v in json.loads((ROOT/'Docs/STREET_IMPORT_RESULTS.json').read_text())['assets'].items()}
    globals()[STAGE](s)
    after={n:transform(s.existing[n]) for n in PROTECTED}
    if before!=after:raise RuntimeError('Protected transforms changed')
    s.save()
    REPORT.update(passed=True,placed=s.placed,protected_before=before,protected_after=after,actor_count=len(s.actors.get_all_level_actors()))
except Exception:
    REPORT['errors'].append(traceback.format_exc());raise
finally:
    (OUT/(STAGE+'.json')).write_text(json.dumps(REPORT,indent=2,ensure_ascii=False),encoding='utf-8')
