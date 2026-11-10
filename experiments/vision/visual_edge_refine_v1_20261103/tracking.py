"""Forward/backward LK corner tracks near predicted object edges; RGB-only checks."""
import cv2
import numpy as np
from geometry import edge_samples,visible,project,triangulate

def edges(rgb):
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    edge=cv2.Canny(cv2.GaussianBlur(gray,(3,3),.7),45,100)
    distance=cv2.distanceTransform(255-edge,cv2.DIST_L2,5)
    return gray,edge,distance

def seeds(gray,camera,boxes):
    h,w=gray.shape;labels=np.full((h,w),-1,np.int16);best=np.full((h,w),np.inf)
    for j,box in enumerate(boxes):
        points=edge_samples(box,15);uv,z=project(points,camera);ok=visible(points,camera,boxes)
        canvas=np.zeros((h,w),np.uint8)
        for p in np.rint(uv[ok]).astype(int):cv2.circle(canvas,tuple(p),2,255,-1)
        if not canvas.any():continue
        dist=cv2.distanceTransform(255-canvas,cv2.DIST_L2,5);take=(dist<8)&(dist<best)
        best[take]=dist[take];labels[take]=j
    mask=np.uint8(labels>=0)*255
    pts=cv2.goodFeaturesToTrack(gray,maxCorners=180,qualityLevel=.015,minDistance=5,mask=mask,blockSize=5)
    if pts is None:return []
    return [(p.astype(float),int(labels[int(round(p[1])),int(round(p[0]))])) for p in pts[:,0]]

def track(images,cameras,fit_ids,boxes):
    """Only fit_ids RGB is read. Holdout images never enter fitting tracks."""
    tracks=[];active=[];previous=None;gray_prev=None;stats=dict(forward_backward_rejected=0,photometric_rejected=0)
    for step,frame in enumerate(fit_ids):
        gray,_,_=edges(images[frame])
        if active:
            p=np.float32([tracks[i]['observations'][-1][1] for i in active]).reshape(-1,1,2)
            q,status,_=cv2.calcOpticalFlowPyrLK(gray_prev,gray,p,None,winSize=(21,21),maxLevel=3)
            back,back_status,_=cv2.calcOpticalFlowPyrLK(gray,gray_prev,q,None,winSize=(21,21),maxLevel=3)
            survivors=[]
            for k,index in enumerate(active):
                xy=q[k,0];h,w=gray.shape
                if not(status[k,0] and back_status[k,0]) or np.linalg.norm(back[k,0]-p[k,0])>1. or not(4<=xy[0]<w-4 and 4<=xy[1]<h-4):
                    stats['forward_backward_rejected']+=1;continue
                a=cv2.getRectSubPix(gray_prev,(5,5),tuple(map(float,p[k,0]))).astype(float)
                b=cv2.getRectSubPix(gray,(5,5),tuple(map(float,xy))).astype(float)
                # Photometric consistency is a filter, not a dense photometric reconstruction.
                if np.mean(np.abs(a-b))>30:stats['photometric_rejected']+=1;continue
                tracks[index]['observations'].append((int(frame),xy.astype(float)));survivors.append(index)
            active=survivors
        if step%4==0:
            for xy,obj in seeds(gray,cameras[frame],boxes):
                if obj<0:continue
                if any(np.linalg.norm(xy-tracks[i]['observations'][-1][1])<5 for i in active):continue
                tracks.append(dict(object_index=obj,observations=[(int(frame),xy)]));active.append(len(tracks)-1)
        previous=frame;gray_prev=gray
    points=[]
    for i,t in enumerate(tracks):
        result=triangulate(t['observations'],cameras)
        if result is None:continue
        box=boxes[t['object_index']];local=(result['point']-box['position'])@box['rotation']
        if np.any(np.abs(local)>box['size']/2+.025):continue
        points.append(dict(track=i,object_index=t['object_index'],**result))
    return tracks,points,stats
