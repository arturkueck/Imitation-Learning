"""Deployable-input RGB reference subtraction. No simulator or truth access.

Reference RGB must use the same camera pose, robot pose and lighting. Robot
silhouette comes from known robot geometry/kinematics, not unknown objects.
Masks are image evidence only, never a collision/free-space certificate.
"""
import numpy as np
from scipy.ndimage import binary_closing, binary_dilation, binary_erosion, binary_fill_holes, label, distance_transform_edt


def foreground(rgb,empty_reference,robot_mask,threshold=16):
    if rgb.shape!=empty_reference.shape or rgb.shape[-1]!=3:raise ValueError('Reference RGB shape mismatch')
    if robot_mask.shape!=rgb.shape[:2]:raise ValueError('Robot mask shape mismatch')
    if not np.isfinite(threshold) or threshold<=0:raise ValueError('Invalid RGB threshold')
    valid=~binary_dilation(robot_mask.astype(bool),iterations=2)
    delta=np.linalg.norm(rgb.astype(float)-empty_reference.astype(float),axis=-1)
    changed=(delta>=threshold)&valid
    closed=binary_closing(changed,iterations=1)&valid
    components,count=label(closed);sizes=np.bincount(components.ravel())
    keep=sizes>=4;keep[0]=False
    mask=keep[components]
    # Closed object outlines can recover white interiors. This is a segmentation
    # inference, not observed depth/free-space evidence; shadows may also remain.
    mask=binary_fill_holes(mask)&valid
    return dict(mask=mask,valid=valid,delta=delta,
                weak_change=(delta>=threshold/2)&(delta<threshold)&valid)


def features(images,references,robot_masks,cameras,groups,threshold=16):
    import image_consistency as geometry
    evidence=[foreground(rgb,ref,robot,threshold) for rgb,ref,robot in zip(images,references,robot_masks)]
    per_group=[[] for _ in groups]
    for camera,ev in zip(cameras,evidence):
        owner,_,faces,_=geometry.rasterize(camera,groups)
        fg=ev['mask'];valid=ev['valid']
        edge=fg & ~binary_erosion(fg)
        distances=distance_transform_edt(~edge)
        for i in range(len(groups)):
            visible=(owner==i)&valid
            boundary=geometry.expected_edges(owner,faces,i)&valid
            usable=visible.sum()>=9 and boundary.sum()>=3
            edge_error=float(np.mean(np.minimum(distances[boundary],8))/8) if usable else None
            mismatch=float((~fg)[visible].mean()) if usable else None
            per_group[i].append(dict(usable=bool(usable),edge_error=edge_error,mismatch=mismatch,
                                     visible_pixels=int(visible.sum())))
    output=[]
    for views in per_group:
        usable=[v for v in views if v['usable']]
        edge=float(np.mean([v['edge_error'] for v in usable])) if usable else 1.
        mismatch=float(np.mean([v['mismatch'] for v in usable])) if usable else 1.
        output.append(dict(image_score=.5*edge+.5*mismatch,image_unknown=len(usable)<2,
                           edge_error=edge,reference_mismatch=mismatch,usable_views=len(usable)))
    return output,evidence
