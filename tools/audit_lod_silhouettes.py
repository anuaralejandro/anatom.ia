#!/usr/bin/env python3
"""Independent 720p projected triangle-mask QA for two anatomical LOD changes.
This is a real rasterized silhouette test, not an AABB/corner proxy.
No asset is modified; no Blender/web/API needed.
"""
import json, struct, sys, math, hashlib
from pathlib import Path
import cv2
import numpy as np
from scipy.spatial.transform import Rotation

W,H=1280,720
TARGETS={"ta2:1071":"sacrum","ta2:3401":"urinary_bladder"}
CAMERAS={"anterior":(0.0,0.25),"oblique":(math.pi/4,0.25),"posterior":(math.pi,0.2),"inferior":(0.0,-0.6),"superior":(0.0,1.1)}
def parse(path):
    raw=Path(path).read_bytes()
    assert raw[:4]==b"glTF" and struct.unpack_from("<I",raw,4)[0]==2
    n=struct.unpack_from("<I",raw,8)[0];assert n==len(raw)
    off=12; chunks={}
    while off<n:
        length,typ=struct.unpack_from("<II",raw,off);off+=8
        assert off+length<=n
        chunks[typ]=raw[off:off+length];off+=length
    doc=json.loads(chunks[0x4E4F534A])
    binary=chunks[0x004E4942]
    accessors=doc["accessors"]; views=doc["bufferViews"]
    def acc(i):
        a=accessors[i];v=views[a["bufferView"]];count=a["count"];ct=a["componentType"]
        dtype={5126:np.dtype("<f4"),5125:np.dtype("<u4"),5123:np.dtype("<u2")}[ct]
        comps={"SCALAR":1,"VEC3":3}[a["type"]]
        stride=v.get("byteStride",dtype.itemsize*comps)
        start=v.get("byteOffset",0)+a.get("byteOffset",0)
        return np.ndarray(shape=(count,comps),dtype=dtype,buffer=binary,offset=start,strides=(stride,dtype.itemsize)).copy()
    scene={}
    for node in doc["nodes"]:
        aid=node.get("extras",{}).get("atlas_id")
        if not aid or "mesh" not in node:continue
        if "matrix" in node:mt=np.array(node["matrix"],dtype=float).reshape(4,4).T
        else:
            mt=np.eye(4)
            rotation=Rotation.from_quat(node.get("rotation",[0,0,0,1])).as_matrix()
            mt[:3,:3]=rotation@np.diag(node.get("scale",[1,1,1]))
            mt[:3,3]=node.get("translation",[0,0,0])
        tris=[]
        for prim in doc["meshes"][node["mesh"]]["primitives"]:
            pts=acc(prim["attributes"]["POSITION"]).astype(np.float64)
            pos=(np.hstack([pts,np.ones((len(pts),1))])@mt.T)[:,:3]
            inds=acc(prim["indices"]).reshape(-1).astype(int)
            assert len(inds)%3==0 and len(pos)>inds.max()
            tris.append(pos[inds.reshape(-1,3)])
        scene[aid]=np.concatenate(tris,axis=0)
    return scene
def matrix(center,radius,yaw,pitch):
    direction=np.array([math.cos(pitch)*math.sin(yaw),math.sin(pitch),math.cos(pitch)*math.cos(yaw)])
    eye=center+direction*max(radius*3.5,0.8)
    forward=center-eye;forward/=np.linalg.norm(forward)
    right=np.cross(forward,np.array([0.,1.,0.]));right/=np.linalg.norm(right)
    up=np.cross(right,forward)
    return eye,right,up,forward
def render(tris,camera):
    eye,right,up,forward=camera
    flat=tris.reshape(-1,3)-eye
    x=flat@right;y=flat@up;z=flat@forward
    valid=z>0.005
    f=1/math.tan(math.pi/8)
    px=(0.5+x*f/(2*np.maximum(z,0.005)*(W/H)))*W
    py=(0.5-y*f/(2*np.maximum(z,0.005)))*H
    uv=np.stack((px,py),axis=1).reshape(-1,3,2)
    valid=valid.reshape(-1,3).all(axis=1)
    out=np.zeros((H,W),np.uint8)
    for triangle in uv[valid]:
        if np.all(np.isfinite(triangle)):
            q=np.rint(np.clip(triangle,-10000,10000)).astype(np.int32)
            cv2.fillConvexPoly(out,q,255)
    return out
def compare(a,b):
    ar=int(cv2.countNonZero(a));br=int(cv2.countNonZero(b))
    if ar<150 or br<150:return {"status":"INCONCLUSIVE_SMALL_MASK","pixels0":ar,"pixels1":br}
    inter=int(cv2.countNonZero(cv2.bitwise_and(a,b)))
    union=int(cv2.countNonZero(cv2.bitwise_or(a,b)))
    def boundary(mask):return cv2.morphologyEx(mask,cv2.MORPH_GRADIENT,np.ones((3,3),np.uint8))
    e0=boundary(a);e1=boundary(b)
    dist1=cv2.distanceTransform(255-e1,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    dist0=cv2.distanceTransform(255-e0,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    values=np.concatenate([dist1[e0!=0],dist0[e1!=0]])
    return {"status":"MEASURED_RASTER_SILHOUETTE","pixels0":ar,"pixels1":br,"mask_iou":round(inter/union,6),
            "boundary_symmetric_p95_px":round(float(np.percentile(values,95)),3),
            "boundary_symmetric_p99_px":round(float(np.percentile(values,99)),3),
            "boundary_max_px":round(float(np.max(values)),3)}
def main():
    p0=Path(sys.argv[1]);p1=Path(sys.argv[2]);out=Path(sys.argv[3])
    a=parse(p0);b=parse(p1)
    ids0=set(a);ids1=set(b)
    assert ids0==ids1 and len(ids0)==26,f"ID mismatch {ids0^ids1}"
    allpts=np.concatenate([t.reshape(-1,3) for t in a.values()])
    center=(allpts.min(axis=0)+allpts.max(axis=0))/2
    radius=np.linalg.norm(allpts.max(axis=0)-allpts.min(axis=0))/2
    tests=[]
    for aid,name in TARGETS.items():
        assert aid in a and aid in b
        for cam_name,(yaw,pitch) in CAMERAS.items():
            cam=matrix(center,radius,yaw,pitch)
            m0=render(a[aid],cam);m1=render(b[aid],cam)
            measure=compare(m0,m1)
            test={"id":aid,"name":name,"camera":cam_name,"triangles0":int(len(a[aid])),"triangles1":int(len(b[aid])),**measure}
            tests.append(test);print("QA",json.dumps(test),flush=True)
    decisive=[t for t in tests if t["status"]=="MEASURED_RASTER_SILHOUETTE"]
    adequate=len(decisive)==len(TARGETS)*len(CAMERAS)
    metrics=[t["boundary_symmetric_p95_px"] for t in decisive]
    passed=adequate and max(metrics)<=2.0
    result={"status":"PASS_MEASURED" if passed else "FAIL_OR_INCONCLUSIVE","is_real_rasterized_triangle_mask":True,
     "measurement":"triangle-projected binary silhouette per organ, symmetric nearest-boundary distance in pixel units",
     "cameras":list(CAMERAS),"viewport":[W,H],"ids_exactly_26":True,"tests":tests,
     "max_per_camera_boundary_p95_px":max(metrics) if metrics else None,
     "limitations":["independent surface silhouette, not visible-scene compositing","no depth/self-occlusion test","not clinical validation of topology"],
     "source0":str(p0),"source1":str(p1),
     "sha256_lod0":hashlib.sha256(p0.read_bytes()).hexdigest(),
     "sha256_lod1":hashlib.sha256(p1.read_bytes()).hexdigest()}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("RESULT",result["status"],"MAX_P95",result["max_per_camera_boundary_p95_px"],flush=True)
    sys.exit(0 if passed else 2)
if __name__=="__main__":main()
