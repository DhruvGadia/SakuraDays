"""Author a sparse looping Niagara petal system using Epic's editor conversion API.

Launch with -EnablePlugins=PythonScriptPlugin,EditorScriptingUtilities,CascadeToNiagaraConverter,NiagaraToolsets.
The converter and diagnostics toolset are authoring-only engine tools; project
runtime uses Niagara. No project plugin configuration is changed by this script.
"""
import json, sys, traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from town_common import *

FXBASE='/Game/SakuraDays/Effects/Petals/Prompt12'
REPORT={'passed':False,'errors':[],'parameter_checks':[]}
RECIPE='v2'
conversion_context=None

def validate_compilation(system):
    """Inspect the finished compile instead of treating Finalize as success.

    NiagaraSystem::PreSave waits for compilation in this engine version. The
    toolset query should therefore resolve synchronously after save. A pending
    query is deliberately treated as unverified, never as a passing default
    value. Runtime particle activity still requires the separate PIE check.
    """
    # UE 5.8 toolset endpoints are reflected AICallable functions without
    # generated Python glue. Object.call_method invokes their native UFunction.
    diagnostics=unreal.get_default_object(unreal.NiagaraToolset_System)
    result=diagnostics.call_method('GetSystemCompileState',(system,))
    if not result.get_editor_property('is_complete'):
        raise RuntimeError('Niagara compile diagnostics still pending after save; rerun validation after editor ticks')
    error=result.get_editor_property('error')
    if error:raise RuntimeError('Niagara compile diagnostics: '+error)
    state=result.get_editor_property('value')
    REPORT['compile']=json.loads(result.get_value_as_json_string())
    if state.get_editor_property('is_compiling') or state.get_editor_property('is_stale') or state.get_editor_property('has_errors'):
        raise RuntimeError('Niagara compile is stale, pending, or contains errors; see petals.json')
    scripts=state.get_editor_property('scripts')
    if not scripts:raise RuntimeError('Niagara diagnostics returned no compiled scripts')
    for script in scripts:
        status=str(script.get_editor_property('last_compile_status')).upper()
        if not any(s in status for s in ('UP_TO_DATE','UPTODATE')):
            raise RuntimeError('Niagara script not ready: '+str(script.get_editor_property('script_name'))+' '+status)
    issues=diagnostics.call_method('GetStackIssues',(system,))
    if not issues.get_editor_property('is_complete'):
        raise RuntimeError('Niagara stack diagnostics pending; no validation claim made')
    error=issues.get_editor_property('error')
    if error:raise RuntimeError('Niagara stack diagnostics: '+error)
    REPORT['stack']=json.loads(issues.get_value_as_json_string())
    if issues.get_editor_property('value').get_editor_property('num_errors'):
        raise RuntimeError('Niagara stack has errors; see petals.json')
    REPORT['runtime_activity_verified']=False

def petal_material():
    path=FXBASE+'/M_Petal_'+RECIPE
    if EAL.does_asset_exist(path):return unreal.load_asset(path)
    m=AT.create_asset(path.rsplit('/',1)[1],FXBASE,unreal.Material,unreal.MaterialFactoryNew())
    m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property('two_sided',True)
    m.set_editor_property('used_with_niagara_sprites',True)
    m.set_editor_property('opacity_mask_clip_value',.4)
    uv=node(m,unreal.MaterialExpressionTextureCoordinate,-500,0)
    shape=node(m,unreal.MaterialExpressionCustom,-200,0)
    i=unreal.CustomInput();i.set_editor_property('input_name','UV');shape.set_editor_property('inputs',[i])
    shape.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    shape.set_editor_property('code','float2 p=UV-float2(.5,.5); float w=.33*(.8+.3*p.y); float d=(p.x/w)*(p.x/w)+(p.y/.46)*(p.y/.46); float notch=length((UV-float2(.5,.965))*float2(1,1.1)); return (1-smoothstep(.92,1,d))*smoothstep(.05,.09,notch);')
    assert MEL.connect_material_expressions(uv,'',shape,'UV')
    link(shape,unreal.MaterialProperty.MP_OPACITY_MASK)
    b=node(m,unreal.MaterialExpressionConstant3Vector,-200,200,constant=color('ECC0D7'))
    link(b,unreal.MaterialProperty.MP_BASE_COLOR)
    link(scalar(m,.95),unreal.MaterialProperty.MP_ROUGHNESS)
    mul=node(m,unreal.MaterialExpressionMultiply)
    assert MEL.connect_material_expressions(b,'',mul,'A')
    assert MEL.connect_material_expressions(scalar(m,.2),'',mul,'B')
    link(mul,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=MEL.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    EAL.save_loaded_asset(m,only_if_is_dirty=False)
    return m

try:
    FX=unreal.FXConverterUtilitiesLibrary
    if not hasattr(unreal,'NiagaraToolset_System'):
        raise RuntimeError('Enable the installed NiagaraToolsets editor plugin for this authoring session to validate the compile')
    convpath=Path(unreal.Paths.engine_plugins_dir())/'FX/CascadeToNiagaraConverter/Content/Python'
    sys.path.insert(0,str(convpath))
    import Paths
    cat=unreal.ScriptExecutionCategory
    typ=unreal.NiagaraScriptInputType
    def args(path,version=None):
        data=FX.create_asset_data(path)
        return unreal.CreateScriptContextArgs(data,version) if version else unreal.CreateScriptContextArgs(data)
    def setp(script,key,value,*switches):
        ok=script.set_parameter(key,value,*switches);REPORT['parameter_checks'].append({'name':key,'passed':bool(ok)})
        if not ok:raise RuntimeError('Niagara input not found: '+key)
    def random_input(path,lo,hi,kind):
        context=FX.create_script_context(args(path))
        setp(context,'Minimum',lo);setp(context,'Maximum',hi)
        return FX.create_script_input_dynamic(context,kind)
    material_asset=petal_material()
    system_path=FXBASE+'/NS_SakuraPetals_'+RECIPE
    if EAL.does_asset_exist(system_path):
        system=unreal.load_asset(system_path)
        if EAL.get_metadata_tag(system,'SakuraDays.PetalsRecipe')!=RECIPE:raise RuntimeError('Unverified existing system preserved')
    else:
        system=AT.create_asset('NS_SakuraPetals_'+RECIPE,FXBASE,unreal.NiagaraSystem,unreal.NiagaraSystemFactoryNew())
        context=FX.create_system_conversion_context(system)
        conversion_context=context
        emitter=context.add_empty_emitter('GentleFallingPetals');emitter.set_enabled(True);emitter.set_local_space(True)
        emitter.set_sim_target(unreal.NiagaraSimTarget.CPU_SIM)
        def module(name,path,category,version=None):return emitter.find_or_add_module_script(name,args(path,version),category)
        state=module('EmitterState','/Niagara/Modules/Emitter/EmitterState.EmitterState',cat.EMITTER_UPDATE,[1,0])
        setp(state,'Life Cycle Mode',FX.create_script_input_enum(Paths.enum_niagara_emitter_life_cycle_mode,'Self'))
        setp(state,'Loop Behavior',FX.create_script_input_enum(Paths.enum_niagara_emitter_state_options,'Infinite'))
        setp(state,'Loop Duration',FX.create_script_input_float(5.))
        # Pin the same module version and exact input name used by Epic's
        # installed CascadeSpawnToNiagaraSpawn.py converter. Names are exact.
        spawn=module('SpawnRate',Paths.script_spawnrate,cat.EMITTER_UPDATE,[1,0])
        setp(spawn,'SpawnRate',FX.create_script_input_float(4.))
        init=module('InitializeParticle',Paths.script_initialize_particle,cat.PARTICLE_SPAWN,[1,0])
        setp(init,'Lifetime',FX.create_script_input_float(12.))
        setp(init,'Sprite Size Mode',FX.create_script_input_enum(Paths.enum_niagara_size_scale_mode,'Non-Uniform'))
        setp(init,'Sprite Size',FX.create_script_input_vec2(unreal.Vector2D(5.,7.)),True,True)
        rotation=random_input(Paths.di_random_range_float,FX.create_script_input_float(0.),FX.create_script_input_float(1.),typ.FLOAT)
        setp(init,'Sprite Rotation Mode',FX.create_script_input_enum(Paths.enum_niagara_sprite_rotation_mode,'Direct Normalized Angle (0-1)'))
        setp(init,'Sprite Rotation Angle',rotation)
        position=random_input(Paths.di_random_range_vector,FX.create_script_input_vector(unreal.Vector(-350,-240,380)),FX.create_script_input_vector(unreal.Vector(350,240,550)),typ.VEC3)
        # Direct parameter sets are pasted before InitializeParticle and its
        # position default overwrites them. A spawn module runs after init.
        offset_path=FXBASE+'/Modules/MS_PetalSpawnOffset_'+RECIPE
        if not EAL.does_asset_exist(offset_path):
            offset_asset=EAL.duplicate_asset(Paths.script_add_vector_to_position,offset_path)
            if not offset_asset:raise RuntimeError('Cannot copy built-in spawn-offset module into project')
            EAL.save_loaded_asset(offset_asset,only_if_is_dirty=False)
        offset=module('PetalSpawnOffset',offset_path,cat.PARTICLE_SPAWN)
        setp(offset,'Vector',position)
        velocity=random_input(Paths.di_random_range_vector,FX.create_script_input_vector(unreal.Vector(-8,-12,-32)),FX.create_script_input_vector(unreal.Vector(16,12,-24)),typ.VEC3)
        emitter.set_parameter_directly('Particles.Velocity',velocity,cat.PARTICLE_SPAWN)
        module('ParticleState',Paths.script_particle_state,cat.PARTICLE_UPDATE,[1,1])
        module('SolveForcesAndVelocity',Paths.script_solve_forces_and_velocity,cat.PARTICLE_UPDATE)
        rotation_rate=module('SpriteRotationRate',Paths.script_sprite_rotation_rate,cat.PARTICLE_UPDATE)
        setp(rotation_rate,'Rotation Rate',FX.create_script_input_float(22.))
        renderer=unreal.NiagaraSpriteRendererProperties()
        renderer.set_editor_property('material',material_asset)
        emitter.add_renderer('PetalSprites',renderer)
        context.set_warmup_time(4.)
        context.set_warmup_tick_delta(1/30.)
        context.finalize()
        EAL.set_metadata_tag(system,'SakuraDays.PetalsRecipe',RECIPE)
        if not EAL.save_loaded_asset(system,only_if_is_dirty=False):
            raise RuntimeError('Failed to save and compile Niagara system')
        context.cleanup()
        conversion_context=None
    # Existing owned systems are also saved to force PreSave's compilation wait.
    if not EAL.save_loaded_asset(system,only_if_is_dirty=False):
        raise RuntimeError('Failed to save Niagara system before validation')
    validate_compilation(system)
    scene=Scene()
    for i,(x,y) in enumerate([(700,-220),(2450,300),(4100,-120)]):
        a=scene.actor('PetalDrift%d'%i,unreal.NiagaraActor,'Effects')
        a.set_actor_location(unreal.Vector(x,y,15),False,False)
        component=a.get_component_by_class(unreal.NiagaraComponent)
        component.set_asset(system);component.set_auto_activate(True)
        component.set_cast_shadow(False)
    scene.save()
    REPORT.update(passed=True,system=system.get_path_name(),rate_per_emitter=4,lifetime_seconds=12,emitters_placed=3,maximum_steady_particles=144,collision=False,audio='None: no licensed ambience supplied')
except Exception:
    REPORT['errors'].append(traceback.format_exc());raise
finally:
    if conversion_context is not None:conversion_context.cleanup()
    (OUT/'petals.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
