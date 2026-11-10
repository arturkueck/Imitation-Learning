import json
import numpy as np
import h5py
from PIL import Image,ImageDraw
from transport_data import demos,DATA,OUT,summary
ds=demos(); rows=[]; visibility=[]
sheet=Image.new('RGB',(768,768),'white'); draw=ImageDraw.Draw(sheet)
with h5py.File(DATA,'r') as f:
    for n,d in enumerate(ds):
        ids=np.flatnonzero(d['phase']==4)
        if not len(ids) or ids[0]==0:continue
        i=ids[0]; prev=i-1; obs=d['obs']; a=d['actions']
        positions=np.c_[obs['robot0_eef_pos'],obs['object'],obs['robot0_gripper_qpos']]
        q=obs['robot0_eef_quat'][[prev,i]]
        rows.append(dict(demo=d['name'],split=d['split'],step=int(i),
            eef_z_before=float(obs['robot0_eef_pos'][prev,2]),eef_z_after=float(obs['robot0_eef_pos'][i,2]),
            B_z_before=float(obs['object'][prev,5]),B_z_after=float(obs['object'][i,5]),
            feature_distance_m=float(np.linalg.norm(positions[i]-positions[prev])),
            eef_angle_change_deg=float(np.degrees(2*np.arccos(np.clip(abs(np.dot(*q)),-1,1)))),
            xy_action_before=a[prev,:2].tolist(),xy_action_after=a[i,:2].tolist(),
            xy_action_jump=float(np.linalg.norm(a[i,:2]-a[prev,:2])),
            xy_velocity_before=((obs['object'][prev,3:5]-obs['object'][prev-1,3:5])*20).tolist(),
            xy_velocity_after=((obs['object'][i,3:5]-obs['object'][prev,3:5])*20).tolist()))
        images=f['data/'+d['name']+'/obs/agentview_image'][ids].astype(float)
        red=(images[...,0]>70)&(images[...,0]>1.5*images[...,1])&(images[...,0]>1.5*images[...,2])
        green=(images[...,1]>60)&(images[...,1]>1.4*images[...,0])&(images[...,1]>1.4*images[...,2])
        rc=red.sum(axis=(1,2));gc=green.sum(axis=(1,2))
        blank=images.max(axis=(1,2,3))==0
        visibility.extend([dict(demo=d['name'],split=d['split'],step=int(k),red_pixels=int(r),green_pixels=int(g),all_black=bool(b)) for k,r,g,b in zip(ids,rc,gc,blank)])
        if n<12:
            for j,step in enumerate((ids[0],ids[len(ids)//2],ids[-1])):
                image=Image.fromarray(f['data/'+d['name']+'/obs/agentview_image'][step]).resize((128,128))
                x=(n%4)*192;y=(n//4)*256
                # One strip of three original-size frames for each demonstration.
                img=Image.fromarray(f['data/'+d['name']+'/obs/agentview_image'][step]).resize((64,64))
                sheet.paste(img,(x+j*64,y+28))
                draw.text((x+3,y+3),d['name']+' lift -> transport',fill='black')
                draw.text((x+j*64,y+96),str(int(step)),fill='black')
result=dict(boundary_count=len(rows),feature_distance_m=summary([r['feature_distance_m'] for r in rows]),
    xy_action_jump=summary([r['xy_action_jump'] for r in rows]),
    eef_z_at_transport_start=summary([r['eef_z_after'] for r in rows]),B_z_at_transport_start=summary([r['B_z_after'] for r in rows]),
    visibility=dict(n=len(visibility),red_pixels=summary([r['red_pixels'] for r in visibility]),green_pixels=summary([r['green_pixels'] for r in visibility]),
        target_red_lt3_fraction=float(np.mean([r['red_pixels']<3 for r in visibility])),held_green_lt3_fraction=float(np.mean([r['green_pixels']<3 for r in visibility])),
        all_black_frames=sum(r['all_black'] for r in visibility),all_black_demo_count=len(set(r['demo'] for r in visibility if r['all_black'])),
        nonblack_target_lt3_fraction=float(np.mean([r['red_pixels']<3 for r in visibility if not r['all_black']])),
        nonblack_held_lt3_fraction=float(np.mean([r['green_pixels']<3 for r in visibility if not r['all_black']])),
        caveat='RGB color-support proxy at 64x64, not ground-truth occlusion or localization labels; black frames are missing image data, not evidence of object occlusion. Baseline policy does not consume images.'),boundaries=rows,visibility_rows=visibility)
(OUT/'boundary_visibility.json').write_text(json.dumps(result,indent=2));sheet.save(OUT/'demo_transport_visibility.png')
print(json.dumps({k:v for k,v in result.items() if k not in ('boundaries','visibility_rows')},indent=2))
