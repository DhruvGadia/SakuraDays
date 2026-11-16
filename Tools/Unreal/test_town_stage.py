"""Reuse the verified street traversal, then capture new review cameras in PIE.

No project settings, character assets, transforms or map saves are changed.
SAKURA_TOWN_TEST_STAGE labels evidence. SAKURA_TOWN_TEST_EXIT=1 closes this test
editor normally after reports and screenshots are written.
"""
import importlib.util, json, os, statistics, time, traceback
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
STAGE=os.environ.get('SAKURA_TOWN_TEST_STAGE','review')
OUT=ROOT/'Saved/TownRefinement'/('PIE_'+STAGE);OUT.mkdir(parents=True,exist_ok=True)
source=(ROOT/'Tools/Unreal/test_street_scene.py').read_text(encoding='utf-8')
marker='\ntry:\n    setup()'
assert source.count(marker)==1, 'Traversal harness changed; review this adapter.'
scope={'__name__':'sakura_town_pie','__file__':str(ROOT/'Tools/Unreal/test_street_scene.py')}
exec(compile(source.split(marker)[0],str(ROOT/'Tools/Unreal/test_street_scene.py'),'exec'),scope)
scope['OUT']=OUT;scope['REPORT']=OUT/'validation.json'
scope['STATE']['stage']=STAGE
scope['STATE']['test_scope']='Genuine PIE route traversal using movement-input calls, possession, ground contact, jump/landing and real 1080p captures. This does not test keyboard bindings or every collision approach. Frame times are editor observations, not packaged GPU benchmarks.'
original_stop=scope['stop']
review={'index':0,'phase':'settle','start':0,'handle':None,'frame_ms':[]}
views=[('Hana','JP_Camera_Hana'),('Residential','JP_Camera_Residential'),('Storefront','JP_Camera_Storefront'),('MainStreet','JP_Camera_MainStreet')]
if STAGE=='final':
    views += [('StreetSign','JP_Camera_StreetSign'),('Noticeboard','JP_Camera_Noticeboard')]
petals={'module':None,'samples':[],'game_times':[],'summary_checked':False}
if STAGE=='final':
    scope['STATE']['petals_runtime']={
        'method':'Two live Niagara simulation-cache samples during PIE',
        'minimum_game_time_interval_seconds':1.0,
        'samples':[], 'game_times_seconds':[], 'complete':False,
        'note':'Reads actual positions and velocities; does not manually advance simulation or save assets.'}

def sample_petals(world):
    """Sample two distinct live frames without changing route/capture state."""
    if STAGE!='final' or len(petals['samples'])>=2:return
    game_time=float(unreal.GameplayStatics.get_time_seconds(world))
    # Wait for real PIE game time, not just wall time across a screenshot stall.
    if game_time<1.0:return
    if petals['game_times'] and game_time-petals['game_times'][0]<1.0:return
    if petals['module'] is None:
        path=ROOT/'Tools/Unreal/verify_petals_runtime.py'
        spec=importlib.util.spec_from_file_location('sakura_final_petal_verifier',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        petals['module']=module
    result=petals['module'].sample(world)
    petals['samples'].append(result);petals['game_times'].append(game_time)
    evidence=scope['STATE']['petals_runtime']
    evidence['samples']=petals['samples'];evidence['game_times_seconds']=petals['game_times']
    scope['check']('petals_live_sample_%d'%len(petals['samples']),result.get('passed',False),
                   game_time_seconds=game_time,total_live_particles=result.get('total_live_particles',0),
                   downward_velocity_verified=result.get('downward_velocity_verified',False),
                   errors=result.get('errors',[]))
    if len(petals['samples'])==2:finish_petal_checks()

def finish_petal_checks():
    if STAGE!='final' or petals['summary_checked']:return
    petals['summary_checked']=True
    evidence=scope['STATE']['petals_runtime']
    interval=(petals['game_times'][1]-petals['game_times'][0]) if len(petals['game_times'])==2 else None
    evidence['sample_interval_game_seconds']=interval
    evidence['complete']=len(petals['samples'])==2
    evidence['passed']=bool(evidence['complete'] and interval>=1.0
                            and all(s.get('passed',False) for s in petals['samples']))
    evidence['temporal_position_motion_verified']=bool(
        evidence['complete'] and petals['samples'][-1].get('temporal_motion_verified',False))
    scope['check']('petals_two_distinct_live_frames',
                   evidence['complete'] and interval>=1.0,
                   sample_interval_game_seconds=interval,sample_count=len(petals['samples']))
    # Matching particle IDs are an additional measurement. Some compiled
    # emitters strip UniqueID; the required per-frame velocity evidence remains
    # explicit in the two checks above rather than claiming a measured delta.
    scope['write_report']()

def finish(status,error=None):
    if review['handle']:
        unreal.unregister_slate_post_tick_callback(review['handle']);review['handle']=None
    samples=review['frame_ms']
    if samples:
        ordered=sorted(samples)
        scope['STATE']['editor_frame_observations']={'samples':len(samples),'median_ms':round(statistics.median(samples),2),'p95_ms':round(ordered[min(len(ordered)-1,int(len(ordered)*.95))],2),'note':'Slate tick interval during captures; includes editor overhead and screenshot stalls; not an RTX 4050 performance certification.'}
    if STAGE=='final':finish_petal_checks()
    original_stop(status,error)
    if os.environ.get('SAKURA_TOWN_TEST_EXIT','1')=='1':
        # Let end-PIE complete before requesting a normal editor shutdown.
        start=time.monotonic();handle=[None]
        def close_editor(delta):
            if time.monotonic()-start>3:
                unreal.unregister_slate_post_tick_callback(handle[0])
                unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        handle[0]=unreal.register_slate_post_tick_callback(close_editor)

def review_tick(delta):
    try:
        now=time.monotonic();age=now-review['start']
        review['frame_ms'].append(delta*1000)
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not world:raise RuntimeError('PIE ended during review captures')
        sample_petals(world)
        controller=unreal.GameplayStatics.get_player_controller(world,0)
        if review['index']>=len(views):finish('complete');return
        name,label=views[review['index']]
        if review['phase']=='select':
            cameras=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.CameraActor)
            camera=next((a for a in cameras if a.get_actor_label()==label),None)
            if not camera:raise RuntimeError('Missing review camera '+label)
            controller.set_view_target_with_blend(camera,0.)
            review.update(phase='settle',start=now)
        elif review['phase']=='settle' and age>5:
            scope['capture'](world,name);review.update(phase='capture',start=now)
        elif review['phase']=='capture' and age>3:
            captured=scope['capture_finished'](name)
            if captured or age>20:
                scope['check'](name+'_1920x1080',captured,file=str(OUT/(name+'.png')))
                review.update(index=review['index']+1,phase='select',start=now)
    except Exception:finish('failed',traceback.format_exc())

def stop(status,error=None):
    if status!='complete':finish(status,error);return
    if scope['HANDLE']:
        unreal.unregister_slate_post_tick_callback(scope['HANDLE']);scope['HANDLE']=None
    review.update(phase='select',start=time.monotonic())
    review['handle']=unreal.register_slate_post_tick_callback(review_tick)

scope['stop']=stop
try:scope['setup']()
except Exception:finish('failed',traceback.format_exc())
