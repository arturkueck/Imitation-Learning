"""Post-evaluation oracle audit of selected examples, never an input to ranking."""
from pathlib import Path
import sys,csv,json
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import image_consistency as diagnostic


def main():
    folder=HERE.parent/'run_001/data/validation'
    data={k:np.load(folder/f'{k}.npy',mmap_mode='r') for k in ['images','rays','positions','sizes','rotations','active']}
    examples=list(csv.DictReader((HERE/'qualitative_examples.csv').open(encoding='utf-8')))
    results=[]
    for row in examples:
        scene=int(row['scene']);target=int(row['gt_index'])
        if target<0:continue
        active=np.flatnonzero(data['active'][scene])
        boxes=[dict(position=data['positions'][scene,i],size=data['sizes'][scene,i],rotation=data['rotations'][scene,i]) for i in active]
        cameras=[diagnostic.camera_from_rays(r) for r in data['rays'][scene]]
        features,_,views=diagnostic.image_features(data['images'][scene],cameras,boxes)
        index=int(np.flatnonzero(active==target)[0])
        results.append(dict(scene=scene,category=row['category'],
                            predicted_image_score=float(row['image_score']),
                            correct_geometry_image_score=features[index]['image_score'],
                            correct_geometry_background_contradiction=features[index]['background_contradiction'],
                            correct_geometry_views=views[index]))
    report=dict(purpose='Post-hoc qualitative diagnosis only. GT geometry not used by evaluated rankers; not a new benchmark or heuristic selection.',examples=results)
    (HERE/'oracle_example_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
