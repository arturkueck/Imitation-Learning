"""Same frozen weights on development starts, orchestration ablation only."""
import json,time
import torch
from method import OUT,PhaseNet,evaluate,write,digest

def main():
    assert json.loads((OUT/'final_test/status.json').read_text())['state'] in ['COMPLETE','TIME_LIMIT_PARTIAL']
    folder=OUT/'retreat_ablation';folder.mkdir(exist_ok=False)
    chosen=json.loads((OUT/'final_test/selection.json').read_text())['models'];deadline=json.loads((OUT/'session.json').read_text())['deadline']-120
    torch.set_num_threads(4);results={}
    for seed in [1,2,3]:
        if time.time()>=deadline:break
        info=chosen[str(seed)];ck=torch.load(info['path'],map_location='cpu',weights_only=False);m=PhaseNet().cuda().eval();m.load_state_dict(ck['model'])
        result=evaluate(m,3,list(range(63000,63010)),folder/f'seed{seed}_no_retreat.json',deadline,.8,False)
        rnd=info['selection']['round'];old=json.loads((OUT/'block2'/f'seed{seed}'/f'dev3_round{rnd}.json').read_text());new=json.loads((folder/f'seed{seed}_no_retreat.json').read_text())
        originals={r['seed']:r for r in old['rows']}
        assert all(r['initial_sha256']==originals[r['seed']]['initial_sha256'] for r in new['rows'])
        assert digest(info['path'])==info['sha256']
        results[str(seed)]=dict(with_retreat=old['successes'],without_retreat=result,paired_initials=True,
            gained_with_retreat=[r['seed'] for r in new['rows'] if not r['success'] and originals[r['seed']]['success']],
            lost_with_retreat=[r['seed'] for r in new['rows'] if r['success'] and not originals[r['seed']]['success']])
        write(folder/'results.json',results)
    write(folder/'status.json',dict(state='COMPLETE' if len(results)==3 and all(r['without_retreat']['complete'] for r in results.values()) else 'PARTIAL',results=results))
if __name__=='__main__':main()
