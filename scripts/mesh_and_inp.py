"""Actual tetra/voxel generation; per-part failures remain visible."""
import argparse,json,math,traceback
from pathlib import Path
import numpy as np
def voxel(z,limit):
 mask=z['mask']>0;cells=np.argwhere(mask)[:,::-1];assert len(cells)>0
 if len(cells)>limit:raise ValueError('Native voxel element budget exceeded; no silent downsampling')
 corners=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]])
 allcorners=(cells[:,None,:]+corners).reshape(-1,3)
 unique,inv=np.unique(allcorners,axis=0,return_inverse=True);M=z['ijk_to_ras'];ij=unique+z['crop_min_ijk']-.5
 xyz=ij@M[:3,:3].T+M[:3,3];conn=inv.reshape(-1,8)
 det=float(np.linalg.det(M[:3,:3]))
 if det<0:conn=conn[:,[0,3,2,1,4,7,6,5]]
 return xyz,conn,{'element_type':'C3D8','volume_mm3':float(len(cells)*abs(det)),'minimum_element_volume_mm3':abs(det),'reference_voxel_occupancy_preserved':True,'surface_description':'Stepped native voxel boundary','edge_lengths_mm':np.linalg.norm(M[:3,:3],axis=0).tolist()}
def tetra(surface,cfg,reference_volume):
 import gmsh
 gmsh.initialize()
 try:
  gmsh.option.setNumber('General.NumThreads',cfg.get('threads',2));gmsh.model.add('IMAGE_COMPONENT');gmsh.merge(str(surface))
  tags,coords,_=gmsh.model.mesh.getNodes();lookup=np.empty(int(tags.max())+1,dtype=np.int64);lookup[tags]=np.arange(len(tags));types,_,nodes=gmsh.model.mesh.getElements(2)
  triangles=np.concatenate([lookup[n].reshape(-1,3)for t,n in zip(types,nodes)if t==2]);p=coords.reshape(-1,3)
  if len(np.unique(np.sort(triangles,axis=1),axis=0))!=len(triangles):raise ValueError('Duplicate boundary triangles')
  edges=np.sort(np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]]),axis=1);_,counts=np.unique(edges,axis=0,return_counts=True)
  if np.any(counts!=2):raise ValueError('Surface has open or nonmanifold edges')
  gmsh.model.mesh.classifySurfaces(math.pi,True,True,math.pi);gmsh.model.mesh.createGeometry()
  surfaces=[t for _,t in gmsh.model.getEntities(2)];curve_to_faces={}
  for t in surfaces:
   _,curves=gmsh.model.getAdjacencies(2,t)
   for c in curves:curve_to_faces.setdefault(abs(int(c)),set()).add(t)
  adjacency={t:set()for t in surfaces}
  for fs in curve_to_faces.values():
   for t in fs:adjacency[t].update(fs-{t})
  remaining=set(surfaces);shells=0
  while remaining:
   shells+=1;todo=[remaining.pop()]
   while todo:
    for t in adjacency[todo.pop()]&remaining:remaining.remove(t);todo.append(t)
  if shells!=1:raise ValueError('Multiple boundary shells: cavity hierarchy is not inferred; retain via voxel or adapt explicitly')
  sl=gmsh.model.geo.addSurfaceLoop(surfaces);gmsh.model.geo.addVolume([sl]);gmsh.model.geo.synchronize()
  target=float(cfg.get('target_edge_mm',1.5));assert target>0
  gmsh.option.setNumber('Mesh.MeshSizeMin',target*.7);gmsh.option.setNumber('Mesh.MeshSizeMax',target)
  gmsh.option.setNumber('Mesh.MeshSizeFromPoints',0);gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',0);gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0)
  gmsh.option.setNumber('Mesh.Algorithm',6);gmsh.option.setNumber('Mesh.Algorithm3D',1);gmsh.model.mesh.generate(3)
  warning=None
  try:gmsh.model.mesh.optimize('Netgen')
  except Exception as e:warning=repr(e)
  tags,coords,_=gmsh.model.mesh.getNodes();xyz=coords.reshape(-1,3);lookup=np.empty(int(tags.max())+1,dtype=np.int64);lookup[tags]=np.arange(len(tags))
  types,ids,nodes=gmsh.model.mesh.getElements(3)
  if list(types)!=[4]:raise ValueError('Unexpected volume element types '+repr(types))
  conn=lookup[nodes[0]].reshape(-1,4);v=xyz[conn];det=np.linalg.det(np.stack([v[:,1]-v[:,0],v[:,2]-v[:,0],v[:,3]-v[:,0]],axis=2))
  if not np.all(det>1e-12):raise ValueError('Nonpositive/degenerate tetrahedra')
  if len(np.unique(np.sort(conn,axis=1),axis=0))!=len(conn):raise ValueError('Duplicate tetrahedra')
  faces=np.sort(np.concatenate([conn[:,[0,1,2]],conn[:,[0,1,3]],conn[:,[0,2,3]],conn[:,[1,2,3]]]),axis=1);_,fc=np.unique(faces,axis=0,return_counts=True)
  if np.any(fc>2):raise ValueError('Nonmanifold volume-face connectivity')
  volume=float(det.sum()/6);change=volume/reference_volume-1
  if abs(change)>cfg.get('max_tet_volume_change_fraction',.05):raise ValueError('Tetra/label volume change exceeds configured candidate screen: %.5f'%change)
  quality=gmsh.model.mesh.getElementQualities(ids[0],'gamma')
  lengths=np.concatenate([np.linalg.norm(v[:,i]-v[:,j],axis=1)for i,j in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]])
  return xyz,conn,{'element_type':'C3D4','volume_mm3':volume,'volume_change_fraction':change,'minimum_element_volume_mm3':float(det.min()/6),'gamma_min':float(quality.min()),'gamma_p05':float(np.percentile(quality,5)),'gamma_median':float(np.median(quality)),'gamma_lt_0p1':int((quality<.1).sum()),'target_edge_mm':target,'actual_edge_p05_median_p95_mm':np.percentile(lengths,[5,50,95]).tolist(),'netgen_warning':warning}
 finally:gmsh.finalize()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args();cfg=json.loads(Path(args.config).read_text(encoding='utf-8'));out=Path(cfg['output_dir']);prep=json.loads((out/'prepared.json').read_text(encoding='utf-8'));model=out/'model';model.mkdir()
 report={'parts':[],'failures':[],'inter_part_collision_check':'NOT_PERFORMED; independent per-part meshes can overlap near interfaces','mechanical_connections':'NONE','analysis':'NOT_RUN'}
 for c in prep['components']:
  print('MESH_COMPONENT',c['part'],c['parent_segment'],flush=True)
  try:
   z=np.load(out/c['mask']);teterror=None
   if cfg.get('mesh_mode','tet')=='tet':
    try:xyz,conn,qa=tetra(out/c['surface'],cfg,c['reference_volume_mm3'])
    except Exception as e:
     teterror=repr(e)
     if not cfg.get('fallback_to_voxel',False):raise
     xyz,conn,qa=voxel(z,cfg.get('max_voxel_elements_per_part',500000))
   elif cfg.get('mesh_mode')=='voxel':xyz,conn,qa=voxel(z,cfg.get('max_voxel_elements_per_part',500000))
   else:raise ValueError('mesh_mode must be tet or voxel')
   assert np.isfinite(xyz).all()and conn.min()>=0 and conn.max()<len(xyz)
   assert np.array_equal(np.unique(conn),np.arange(len(xyz)))
   np.savez_compressed(model/(c['part']+'.npz'),vertices=xyz,elements=conn)
   report['parts'].append(dict(c,**qa,nodes=len(xyz),elements=len(conn),tet_fallback_reason=teterror))
  except Exception:
   report['failures'].append({'part':c['part'],'parent_segment':c['parent_segment'],'error':traceback.format_exc()})
 report['complete_requested_regions']=len(report['parts'])==len(prep['components'])
 (out/'mesh_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 if report['parts']:
  with (model/'image_geometry.inp').open('w',encoding='ascii')as f:
   f.write('** IMAGE-DERIVED GEOMETRY ONLY; NO MATERIALS, CONTACT, LOADS OR ANALYSIS STEPS\n** Coordinates RAS / mm; anatomy and interfaces require review\n')
   for p in report['parts']:
    z=np.load(model/(p['part']+'.npz'));f.write('*Part, name='+p['part']+'\n*Node\n')
    for i,v in enumerate(z['vertices'],1):f.write('%d, %.9g, %.9g, %.9g\n'%(i,*v))
    f.write('*Element, type='+p['element_type']+', elset=ALL_ELEMENTS\n')
    for i,c in enumerate(z['elements'],1):f.write(str(i)+', '+', '.join(str(int(x)+1)for x in c)+'\n')
    f.write('*End Part\n')
   f.write('*Assembly, name=IMAGE_GEOMETRY\n')
   for p in report['parts']:f.write('*Instance, name='+p['part']+'-1, part='+p['part']+'\n*End Instance\n')
   f.write('*End Assembly\n')
if __name__=='__main__':main()
