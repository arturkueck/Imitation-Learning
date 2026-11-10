"""Version-pinned proximity query on a copied model and separate native data."""
import copy,hashlib,json
import numpy as np
import helpers as h
FIELDS=['geom_margin','geom_gap','pair_margin','pair_gap']

INACTIVE_ISLAND_FIELDS={'dof_island','island_dofnum','island_dofadr','island_dofind','dof_islandind','efc_island','island_efcnum','island_efcadr','island_efcind'}

INACTIVE_DUAL_FIELDS={'efc_AR','efc_AR_rownnz','efc_AR_rowadr','efc_AR_colind'}

def array_hashes(obj, omit_inactive_islands=False, omit_inactive_dual=False):
    hashes={}
    if omit_inactive_islands:assert obj.nisland==0
    for name in dir(obj):
        if name.startswith('_') or (omit_inactive_islands and name in INACTIVE_ISLAND_FIELDS) or (omit_inactive_dual and name in INACTIVE_DUAL_FIELDS):continue
        value=getattr(obj,name)
        if isinstance(value,np.ndarray):
            digest=hashlib.sha256()
            digest.update(str(value.dtype).encode());digest.update(str(value.shape).encode());digest.update(value.tobytes())
            hashes[name]=digest.hexdigest()
    return hashes

def contacts(model,data,names):
    import mujoco
    rows=[]
    for i in range(data.ncon):
        c=data.contact[i];ids=[int(c.geom1),int(c.geom2)]
        pair=[mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_GEOM,g) for g in ids]
        if any(name in names for name in pair):
            rows.append(dict(geom_ids=ids,names=pair,types=[int(model.geom_type[g]) for g in ids],
                             distance_m=float(c.dist),includemargin_m=float(c.includemargin),efc_address=int(c.efc_address)))
    return rows

def query(model,original_data,names,margin):
    import mujoco
    assert mujoco.__version__=='3.2.3' and margin==.015
    model_before=array_hashes(model)
    islands_disabled=not bool(model.opt.enableflags & int(mujoco.mjtEnableBit.mjENBL_ISLAND))
    dual_solver_active=bool(mujoco.mj_isDual(model))
    data_before=array_hashes(original_data,omit_inactive_islands=islands_disabled,omit_inactive_dual=not dual_solver_active);time_before=float(original_data.time)
    clone=copy.copy(model);assert clone is not model
    assert array_hashes(clone)==model_before,'Copied model differs before query'
    originals={k:getattr(clone,k).copy() for k in FIELDS}
    for k in FIELDS:assert not np.shares_memory(getattr(clone,k),getattr(model,k))
    data=mujoco.MjData(clone)
    for k in ['qpos','qvel','act','ctrl','qacc_warmstart','qfrc_applied','xfrc_applied','mocap_pos','mocap_quat','userdata']:
        getattr(data,k)[:]=getattr(original_data,k)
    data.time=time_before
    result=dict(native_version=mujoco.__version__,native_library_version=mujoco.mj_versionString(),query_margin_m=margin,
                robot_geometry_names=sorted(names),original_margin_gap_values={k:v.tolist() for k,v in originals.items()},
                original_model_array_hashes=model_before,original_data_array_hashes=data_before,
                original_model_numeric_arrays=len(model_before),original_data_numeric_arrays=len(data_before),
                dual_solver_active=dual_solver_active,excluded_inactive_dual_arrays=sorted(INACTIVE_DUAL_FIELDS) if not dual_solver_active else [],
                dual_array_role='Only computed by mj_projectConstraint for dual solvers; excluded only when native mj_isDual(model) is false.',
                island_discovery_enabled=not islands_disabled,excluded_inactive_data_arrays=sorted(INACTIVE_ISLAND_FIELDS) if islands_disabled else [],
                island_array_role='Only computed by mj_island; exclude these arrays only when native island feature disabled and nisland=0.',
                geometry_position_error=0.,velocity_error=0.,integration_steps=0)
    try:
        for k in FIELDS:getattr(clone,k)[:]=margin
        result['effective_margin_gap_values']={k:getattr(clone,k).tolist() for k in FIELDS}
        # Full forward computation on independent data, no time integration.
        mujoco.mj_forward(clone,data)
        assert data.time==time_before and np.array_equal(data.qpos,original_data.qpos) and np.array_equal(data.qvel,original_data.qvel)
        result.update(nearby_robot_contacts=contacts(clone,data,names),explicit_forward_calls=1,
                      same_qpos_qvel_after_forward=True,query_time_unchanged=True)
    finally:
        for k,v in originals.items():getattr(clone,k)[:]=v
        result['copied_model_restored']=array_hashes(clone)==model_before
        result['original_model_unchanged']=array_hashes(model)==model_before
        result['original_data_unchanged']=array_hashes(original_data,omit_inactive_islands=islands_disabled,omit_inactive_dual=not dual_solver_active)==data_before and float(original_data.time)==time_before
        assert result['copied_model_restored'] and result['original_model_unchanged'] and result['original_data_unchanged']
    return result

def filter_anchor(env,ctrl,margin):
    sim=env.env.sim;robot=env.env.robots[0]
    before=h.snapshot(env,ctrl);initial=h.robot_contacts(sim,robot)
    names=set(robot.robot_model.contact_geoms)|set(robot.gripper['right'].contact_geoms)
    info=query(sim.model._model,sim.data._data,names,margin)
    after=h.snapshot(env,ctrl);error=h.difference(before,after);assert error==0
    near=info['nearby_robot_contacts']
    internal=[c for c in near if all(n in names for n in c['names'])]
    external=[c for c in near if not all(n in names for n in c['names'])]
    assert all(sum(n in names for n in c['names'])==1 for c in external)
    return dict(initial_robot_contacts=initial,proximity=info,anchor_before_query=before,anchor_after_query=after,
                full_snapshot_error_after_query=error,M0_initial_contact_free=not initial,
                M1_initial_and_proximity_contact_free=not initial and not info['nearby_robot_contacts'],
                internal_proximity_contacts=internal,external_proximity_contacts=external,
                M2_initial_and_external_proximity_contact_free=not initial and not external,
                dynamic_label_retains_all_actual_self_contacts=True,computed_before_any_response_action=True,policy_training_updates=0)
