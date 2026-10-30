# -*- coding: utf-8 -*-
"""Abaqus/CAE Python entry; no Job, Data Check or analysis."""
from __future__ import print_function
import os,json,io,traceback
try:import builtins as py
except ImportError:import __builtin__ as py
cfg=json.load(io.open(os.environ['CT2ABAQUS_IMPORT_CONFIG'],'r',encoding='utf-8'))
result={'state':'STARTED','scope':'Geometry/mesh import only','analysis':'NOT_RUN'}
try:
 from abaqus import mdb,session
 from abaqusConstants import ON
 model=mdb.ModelFromInputFile(name='IMAGE_DERIVED_GEOMETRY_ONLY',inputFileName=cfg['input_inp'])
 parts=[]
 for name in py.sorted(model.parts.keys()):
  p=model.parts[name];types={}
  for e in p.elements:types[str(e.type)]=types.get(str(e.type),0)+1
  parts.append({'part':name,'nodes':py.len(p.nodes),'elements':py.len(p.elements),'types':types})
 assert py.len(parts)==cfg['expected_parts']
 assert py.sum([p['elements']for p in parts])==cfg['expected_elements']
 assert not model.materials.keys() and not model.loads.keys() and not model.interactions.keys()
 try:
  import displayGroupMdbToolset as dgm
  a=model.rootAssembly;a.regenerate();leaf=dgm.LeafFromInstance(instances=py.tuple(a.instances.values()))
  for vp in session.viewports.values():vp.setValues(displayedObject=a);vp.assemblyDisplay.displayGroup.replace(leaf=leaf);vp.assemblyDisplay.setValues(mesh=ON);vp.view.fitView()
 except Exception:result['display_warning']=traceback.format_exc()
 mdb.saveAs(pathName=cfg['output_cae'])
 result.update(state='CAE_IMPORT_VERIFIED',parts=parts,cae=cfg['output_cae'],note='Use orchestrator manifest for hash after normal CAE close/compaction')
except Exception:
 result.update(state='FAILED',exception=traceback.format_exc());raise
finally:
 with io.open(cfg['report_json'],'w',encoding='utf-8')as f:f.write(py.str(json.dumps(result,ensure_ascii=True,indent=2)))
