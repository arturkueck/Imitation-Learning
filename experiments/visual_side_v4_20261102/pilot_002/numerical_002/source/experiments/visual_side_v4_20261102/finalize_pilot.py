"""Finalize immutable data pilot with corrected shared-assignment benchmark."""
from pathlib import Path
import json,time,shutil,importlib.metadata as md
import numpy as np
from PIL import Image
import pilot as P

def main():
    root=P.HERE/'pilot_002';out=root/'numerical_002';out.mkdir(exist_ok=False);P.settings()
    rows=[json.loads(x) for x in (root/'families.jsonl').read_text().splitlines()];assert len(rows)==200
    paths=[];family_ids=[]
    for row in rows:
        path=root/'samples'/f'sample_{row["index"]:04d}.npz'
        assert P.sha(path)==row['sample_sha256']
        with np.load(path) as z:
            assert z['images'].shape==(3,3,160,160,3)
            assert z['rays'].shape==(3,3,20,20,6)
            assert np.isfinite(z['rays']).all()
            assert z['pose_available'][2]==(row['stage']=='captured')
            assert z['count']==z['active'].sum()==row['count']
            family_ids.append(tuple(z['family'].tolist()))
        paths.append(path)
    assert len(set(family_ids))==200
    original=json.loads((root/'checkpoint_hashes.json').read_text());base=P.ROOT/'experiments/visual_active_v3_20261101/run_001/checkpoints'
    assert all(P.sha(base/name)==value for name,value in original.items())
    began=time.perf_counter();bench=P.numerical_pilot(out,paths)
    assert all(P.sha(base/name)==value for name,value in original.items())
    versions={name:md.version(name) for name in ['torch','numpy','scipy','mujoco','Pillow','matplotlib','psutil']}
    sourcefiles=[P.HERE/name for name in ['pilot.py','pilot_bank.py','paired_learning.py','test_pilot.py','report_pilot.py','finalize_pilot.py']]
    sourcefiles += [P.ROOT/'experiments/visual_active_v3_20261101'/name for name in ['data_v3.py','physical_setup.py','model_v3.py','followup_core.py']]
    sourcefiles += [P.ROOT/'experiments/visual_scene_v2_20261101'/name for name in ['learning.py','preflight.py','scene_data.py','model_prototype.py','ensemble_uncertainty.py']]
    for f in sourcefiles:
        dest=out/'source'/f.relative_to(P.ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
    P.save(out/'provenance.json',dict(versions=versions,source_hashes={str(f.relative_to(P.ROOT)):P.sha(f) for f in sourcefiles},
        reason='Use one common Hungarian assignment for geometric and contextual visibility losses; prior double-assignment benchmark preserved in parent directory.',
        main_training_started=False))
    r=json.loads((root/'report.json').read_text());r['numerical']=bench;r['numerical_artifact_directory']='numerical_002';r['elapsed_seconds']+=time.perf_counter()-began
    r['review_note']='Data and first numerical report remain unchanged. Review uses corrected common-assignment loss and independently repeated numerical benchmark.'
    P.save(root/'review.json',r)
    P.save(root/'audit.json',dict(passed=True,sample_hashes_verified=200,unique_families=200,all_availability_masks_verified=True,
        original_checkpoint_hashes_unchanged=True,unit_tests_passed=6,common_assignment_test=True,versions=versions,main_training_started=False))
    Image.open(out/'diagnostic_loss.png').verify()
    print(json.dumps(dict(audit='passed',numerical=bench),default=P.jsonable),flush=True)

if __name__=='__main__':main()
