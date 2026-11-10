"""Copy two already-recorded local replay examples and preserve provenance."""
from pathlib import Path
import json
import hashlib
import shutil
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=ROOT/'experiments/stack_diagnostics/stack_replication_20261001'
SOURCE=BASE/'representative'
records=json.loads((BASE/'direct/seed_3/rollouts/results.json').read_text(encoding='utf-8'))
original_manifest=json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'))
manifest=[]
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)

for seed,name in [(46003,'04_stack_erfolg'),(46005,'05_stack_misserfolg')]:
    src=SOURCE/f'direct_seed_3_start_{seed}.mp4'
    dst=HERE/f'{name}.mp4'
    assert src.stat().st_size < 5_000_000
    shutil.copy2(src,dst)
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    assert hashlib.sha256(dst.read_bytes()).hexdigest()==digest
    row=next(r for r in records if r['seed']==seed)
    origin=next(r for r in original_manifest if r['model_class']=='direct' and r['training_seed']==3 and r['start_seed']==seed)
    reader=imageio.get_reader(dst)
    meta=reader.get_meta_data()
    count=reader.count_frames()
    selections=[0,count//2,count-1]
    tiles=[]
    for n in selections:
        frame=Image.fromarray(reader.get_data(n)).convert('RGB')
        frame.thumbnail((600,600),Image.Resampling.LANCZOS)
        tiles.append((n,frame))
    width=sum(fr.width for _,fr in tiles)
    height=max(fr.height for _,fr in tiles)
    sheet=Image.new('RGB',(width,height+100),'#F5F3EF')
    d=ImageDraw.Draw(sheet)
    text='Erfolgsbeispiel' if row['sustained_success'] else 'Misserfolgsbeispiel'
    d.text((20,10),f'Stack-Replay · {text} · Trainingsseed 3 · Start {seed}',font=font,fill='#182B3A')
    x=0
    for n,fr in tiles:
        sheet.paste(fr,(x,50))
        d.text((x+16,height+61),f't = {n/meta["fps"]:.1f} s',font=font,fill='#182B3A')
        x += fr.width
    sheet.save(HERE/f'{name}_storyboard.png')
    Image.fromarray(reader.get_data(count-1)).save(HERE/f'{name}_cover.png')
    reader.close()
    manifest.append({
        'source_video':str(src),'copied_video':str(dst),'sha256':digest,
        'byte_identical_copy':True,'file_bytes':dst.stat().st_size,
        'source_manifest':str(SOURCE/'manifest.json'),'source_manifest_entry':origin,
        'source_results':str(BASE/'direct/seed_3/rollouts/results.json'),
        'model_class':'direct','training_seed':3,'start_seed':seed,
        'saved_states_replayed':True,
        'video_duration_seconds':meta['duration'],'fps':meta['fps'],'frame_count':count,
        'dimensions':meta['size'],
        'outcome':{k:row[k] for k in ['measured_steps','grasp','lift','stack','sustained_success','correct_lift','premature_transport']},
        'purpose':'Selected qualitative replay; not evidence for a benchmark score or a mechanism.'
    })

(HERE/'replay_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps([{k:r[k] for k in ['copied_video','file_bytes','video_duration_seconds','fps','frame_count','outcome']} for r in manifest],indent=2))
