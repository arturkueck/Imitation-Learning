"""Quarantine legacy full-scene qpos; keep only Panda robot state as an input.

RGB-mask scoring never reads qpos. This changes storage provenance only and
preserves the original report and all full state in evaluation_only.
"""
from pathlib import Path
import argparse,json,shutil
import numpy as np
from ensemble_uncertainty import digest

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('name');args=parser.parse_args()
    out=(HERE/args.name).resolve()
    if out.parent!=HERE.resolve():raise ValueError('Expected a direct experiment output directory')
    old=out/'observations/qpos.npy';target=out/'evaluation_only/full_scene_qpos.npy'
    if not old.exists():raise RuntimeError('No legacy state to separate')
    original_report=out/'results.json';backup=out/'evaluation_only/pre_state_split_results.json'
    if backup.exists() or target.exists():raise RuntimeError('State already separated')
    report=json.loads(original_report.read_text(encoding='utf-8'))
    state=np.load(old);robot=state[:,:9].copy()
    np.save(out/'observations/robot_qpos.npy',robot)
    shutil.copyfile(original_report,backup)
    old.rename(target)
    report['artifact_sha256'].pop('observations/qpos.npy',None)
    for path in [target,out/'observations/robot_qpos.npy']:
        report['artifact_sha256'][str(path.relative_to(out))]=digest(path)
    report['robot_state_storage']=dict(robot_qpos_columns='Panda arm joints 1..7, then two gripper joints',
                                     full_unknown_object_state='evaluation_only/full_scene_qpos.npy',
                                     scoring_unchanged=True,original_report='evaluation_only/pre_state_split_results.json',
                                     migration_source_sha256=digest(Path(__file__)))
    original_report.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print('Robot-only state separated; metrics unchanged.')


if __name__=='__main__':main()
