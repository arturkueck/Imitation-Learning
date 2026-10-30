"""Finish native data gates and create a reviewable plan; NEVER approve/start it."""
from pathlib import Path
import json
import re
import datetime
from production_readiness import inspect,freeze_manifest
from transition_pilot import sha,dump

HERE=Path(__file__).resolve().parent


def build():
    plan=json.loads((HERE/'training_plan.json').read_text())
    source=HERE/'native_data_v1/manifest.json'
    native=json.loads(source.read_text());revision=json.loads((source.parent/'cohort_revision_v2.json').read_text())
    if not native.get('complete'):raise ValueError('Collection not yet complete')
    assert revision['fixed_indices']==plan['collection']['fixed_indices']
    assert len(native['rows'])==revision['expected_episodes']==200
    expected={(n,base+i) for n,base in ((3,510000),(4,511000)) for i in revision['fixed_indices']}
    assert {(r['count'],r['seed']) for r in native['rows']}==expected
    # The historical source plan remains immutable. Only runtime cohort size was revised.
    frozen_source=json.loads((source.parent/'source_plan.json').read_text())
    for key in ('parents','events','score','gates'):
        assert frozen_source[key]==plan[key],('data rules changed',key)
    report=inspect(plan,source,measure_signal=True)
    dump(HERE/'DATA_READINESS.json',report)
    if not report['data_ready']:
        dump(HERE/'READINESS_BLOCKERS.json',dict(failed=[k for k,v in report['checks'].items() if not v]))
        raise ValueError('Scientific/data gates failed; do not activate production')
    frozen=HERE/'frozen_native_dataset.json'
    freeze_manifest(plan,source,frozen,report)
    panels={};panel_root=HERE/'frozen_benchmarks';panel_root.mkdir(exist_ok=False)
    allrows=native['prepared_starts'];trainfamilies={s['initial_family_id'] for s in native['sections'] if s['split']=='train'}
    devfamilies=set();confirmationfamilies=set()
    for split in ('development','confirmation'):
        panels[split]={}
        for prefix in (2,3):
            key=f'prepared_prefix{prefix}'
            rows=[r for r in allrows if r['panel']==split and r['prefix']==prefix]
            rows.sort(key=lambda r:r['seed'])
            bounds=plan['evaluation'][split][key]
            assert [r['seed'] for r in rows]==list(range(bounds[0],bounds[1]+1))
            assert len(rows)==20
            for r in rows:
                assert r['split']=='valid' and r['family_id'] not in trainfamilies
                assert sha(r['episode'])==r['episode_sha256']
                if r.get('prepared',False):
                    assert r['replay_verified'] and sha(r['path'])==r['sha256']
                    assert r['replay_proof']['action_max_error']==0
                    assert r['replay_proof']['next_integration_max_error']<1e-10
            families={r['family_id'] for r in rows}
            if split=='development':devfamilies.update(families)
            else:confirmationfamilies.update(families)
            target=panel_root/f'{split}_{key}.json'
            dump(target,dict(complete=True,rows=rows,attempts=len(rows),
                prepared=sum(r.get('prepared',False) for r in rows),
                coverage_failures_remain_in_denominator=True,
                construction='fixed validation source families; panel identifiers are not source seeds'))
            panels[split][key]=dict(path=str(target),sha256=sha(target))
    assert not devfamilies & confirmationfamilies
    files=['transition_pilot.py','native_collector.py','state_replay.py','production_data.py',
           'online_evaluation.py','production_train.py','production_readiness.py','run_training.py']
    code_hashes={str(HERE/name):sha(HERE/name) for name in files}
    for path in [HERE.parent/'stack_phased_8h_20261023/method.py',
                 HERE.parent/'stack_composition_20261023/run.py',
                 HERE.parent/'stack_self_imitation_20261023/pipeline.py',
                 HERE.parent/'stack_five_curriculum_20261023/runner.py']:
        code_hashes[str(path)]=sha(path)
    # Pin the imported dependency code, not a guessed editable-install location.
    import robosuite,robosuite.utils.sim_utils as sim_utils
    import robosuite.controllers.parts.arm.osc as osc
    for module in (sim_utils,osc):code_hashes[str(Path(module.__file__).resolve())]=sha(module.__file__)
    plan['status']='READY_AWAITING_EXPLICIT_USER_GO'
    plan['production_enabled']=True
    plan['blocked_until']=[]
    plan['ready_bundle']=dict(dataset_manifest=str(frozen),dataset_manifest_sha256=sha(frozen),
        prepared_panels=panels,code_hashes=code_hashes,readiness_report=str(HERE/'DATA_READINESS.json'),
        readiness_report_sha256=sha(HERE/'DATA_READINESS.json'),
        data_source_plan_sha256=sha(source.parent/'source_plan.json'),
        runtime_cohort_revision_sha256=sha(source.parent/'cohort_revision_v2.json'),
        dependency_robosuite_version=getattr(robosuite,'__version__','unknown'),
        data_costs_excluded_from_future_run_but_reported_separately=True,
        current_approval='NONE; technical enabled does not authorize launch')
    dump(HERE/'READY_PLAN.json',plan)
    result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='READY_AWAITING_EXPLICIT_USER_GO',ready_plan_sha256=sha(HERE/'READY_PLAN.json'),
        no_production_training_started=True,no_release_file_created=True,
        episodes=len(native['rows']),data_summary=report['summary'],score_std=report['score_std'],
        signal=report['signals'],prepared_panels=panels,
        technical_preflights=['49 invariant tests','six models x3 technical CPU updates only',
            'same- and cross-environment first-action/next-state/observation exact replay',
            'native online positive grasp and contact failure paths',
            'reserved panel technical family498003 only; no held-out starts consumed'],
        eight_hour_upper_bound_after_Go=True,training_updates_per_model=plan['pilot']['steps'])
    dump(HERE/'START_READINESS.json',result)
    print(json.dumps({k:result[k] for k in ('status','episodes','score_std','no_release_file_created')}))


if __name__=='__main__':build()
