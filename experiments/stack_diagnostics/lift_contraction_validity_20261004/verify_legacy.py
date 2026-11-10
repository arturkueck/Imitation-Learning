"""Check historical BC comparison summaries against their unmodified rollout files."""
import hashlib
import json
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    comparisons=[('full_20','final_eval','lift_ph_full_20ep_summary.json','', 'w1'),
                 ('full_100','final_eval_100','lift_ph_full_100ep_summary.json','e100','w1e100'),
                 ('20pct_100','final_eval_20pct','lift_ph_20pct_100ep_summary.json','d20e100','w1d20e100')]
    output={'passed':True,'comparisons':{},'source_sha256':sha(Path(__file__))}
    for label,folder,report,bc_tag,ext_tag in comparisons:
        report_path=ROOT/'praxis/reports'/report
        summary=json.loads(report_path.read_text())
        aggregate={};files={str(report_path.relative_to(ROOT)):sha(report_path)};missing_initial_states=0
        for row in summary['rows']:
            seed,condition=row['training_seed'],row['condition']
            base='lift_ph_bc'+('_'+bc_tag if bc_tag else '')+f'_seed{seed}_{condition}.json'
            ext=f'lift_ph_bc_contraction_{ext_tag}_seed{seed}_{condition}.json'
            paths=[ROOT/'praxis/results'/folder/n for n in [base,ext]]
            results=[json.loads(p.read_text()) for p in paths]
            for prefix,data in zip(['bc','extension'],results):
                assert data['episodes']==len(data['rollouts'])==row['episodes']==20
                assert data['successes']==sum(bool(r['success']) for r in data['rollouts'])==row[prefix+'_successes']
                assert data['horizon']==400
            for a,b in zip(results[0]['rollouts'],results[1]['rollouts']):
                assert a['seed']==b['seed']
                if 'initial_cube_qpos' in a and 'initial_cube_qpos' in b:
                    assert np.array_equal(a['initial_cube_qpos'],b['initial_cube_qpos'])
                    assert np.array_equal(a['initial_eef_pos'],b['initial_eef_pos'])
                else:
                    missing_initial_states+=1
            paired=list(zip(results[0]['rollouts'],results[1]['rollouts']))
            assert sum(a['success'] and not b['success'] for a,b in paired)==row['bc_only_successes']
            assert sum(b['success'] and not a['success'] for a,b in paired)==row['extension_only_successes']
            value=aggregate.setdefault(condition,{'episodes':0,'bc_successes':0,'extension_successes':0})
            for key in value:value[key]+=row[key]
            for path in paths:files[str(path.relative_to(ROOT))]=sha(path)
        output['comparisons'][label]={'rows_verified':len(summary['rows']),'aggregate':aggregate,'source_hashes':files,
                                     'paired_initial_states_verified':missing_initial_states==0,
                                     'episode_pairs_missing_initial_state_metadata':missing_initial_states,
                                     'training_seeds':sorted(set(r['training_seed'] for r in summary['rows']))}
    (HERE/'legacy_verification.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v['aggregate'] for k,v in output['comparisons'].items()},indent=2))


if __name__=='__main__':verify()
