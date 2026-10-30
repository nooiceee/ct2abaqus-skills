"""Run inside full Slicer application. No hardcoded dataset or installation path."""
import os,json,traceback
from pathlib import Path
import numpy as np
from scipy import ndimage
import slicer,qt,vtk
from vtkSegmentationCorePython import vtkOrientedImageData
cfg=json.loads(Path(os.environ['CT2ABAQUS_CONFIG']).read_text(encoding='utf-8'))
out=Path(cfg['output_dir']);(out/'masks').mkdir();(out/'surfaces').mkdir()
report={'source_image':cfg['image'],'source_segmentation':cfg.get('segmentation'),'components':[],'warnings':[]}
def save(): (out/'prepared.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
class DecisionRequired(Exception):pass
try:
 if slicer.util.mainWindow():slicer.util.mainWindow().hide()
 source=Path(cfg['image']);volume=None;seg=None
 if source.is_dir():
  from DICOMLib import DICOMUtils
  with DICOMUtils.TemporaryDICOMDatabase()as db:
   DICOMUtils.importDicom(str(source),db);series=[]
   for patient in db.patients():
    for study in db.studiesForPatient(patient):
     for uid in db.seriesForStudy(study):
      files=db.filesForSeries(uid)
      if files:series.append({'uid':uid,'files':len(files),'description':db.fileValue(files[0],'0008,103e'),'modality':db.fileValue(files[0],'0008,0060')})
   report['dicom_series']=series;wanted=cfg.get('series_uid')
   if not wanted and len(series)==1:wanted=series[0]['uid']
   if not wanted or wanted not in [s['uid']for s in series]:raise DecisionRequired('NEEDS_SERIES_SELECTION')
   nodes=DICOMUtils.loadSeriesByUID([wanted]);volumes=[slicer.mrmlScene.GetNodeByID(n)for n in nodes if slicer.mrmlScene.GetNodeByID(n).IsA('vtkMRMLScalarVolumeNode')]
   if len(volumes)!=1:raise DecisionRequired('NEEDS_IMAGE_NODE_SELECTION')
   volume=volumes[0]
 elif source.suffix.lower()=='.mrb':
  if not slicer.util.loadScene(str(source)):raise ValueError('MRB load failed')
  vols=list(slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode'));segs=list(slicer.util.getNodesByClass('vtkMRMLSegmentationNode'))
  if cfg.get('image_node_name'):vols=[n for n in vols if n.GetName()==cfg['image_node_name']]
  if len(vols)!=1:raise DecisionRequired('NEEDS_IMAGE_NODE_SELECTION')
  volume=vols[0]
  if cfg.get('segmentation_node_name'):segs=[n for n in segs if n.GetName()==cfg['segmentation_node_name']]
  if len(segs)==1:seg=segs[0]
  elif len(segs)>1:raise DecisionRequired('NEEDS_SEGMENTATION_NODE_SELECTION')
 else:volume=slicer.util.loadVolume(str(source))
 if volume is None:raise ValueError('Image could not be loaded')
 if volume.GetParentTransformNode():raise DecisionRequired('IMAGE_PARENT_TRANSFORM_REQUIRES_EXPLICIT_HANDLING')
 matrix=vtk.vtkMatrix4x4();volume.GetIJKToRASMatrix(matrix);M=np.array([[matrix.GetElement(i,j)for j in range(4)]for i in range(4)])
 if not np.isfinite(M).all()or abs(np.linalg.det(M[:3,:3]))<1e-12:raise ValueError('Invalid image physical transform')
 voxvol=abs(float(np.linalg.det(M[:3,:3])));image=slicer.util.arrayFromVolume(volume)
 report['image_geometry']={'array_axes':'KJI','shape_KJI':list(image.shape),'ijk_to_RAS_mm':M.tolist(),'voxel_volume_mm3':voxvol,'coordinate_system':'RAS mm','actual_slicer_version':slicer.app.applicationVersion}
 if cfg.get('segmentation'):
  p=Path(cfg['segmentation'])
  if p.name.lower().endswith('.seg.nrrd'):seg=slicer.util.loadSegmentation(str(p))
  else:
   label=slicer.util.loadLabelVolume(str(p));a=slicer.util.arrayFromVolume(label)
   if not np.isfinite(a).all()or not np.equal(a,np.rint(a)).all()or a.min()<0:raise ValueError('Labelmap must contain nonnegative integer labels')
   present=sorted(int(v)for v in np.unique(a)if v!=0)
   seg=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode','SUPPLIED_SEGMENTATION');seg.CreateDefaultDisplayNodes()
   if not slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(label,seg):raise ValueError('Label import failed')
   if seg.GetSegmentation().GetNumberOfSegments()!=len(present):raise ValueError('Label import count mismatch')
   for i,value in enumerate(present):seg.GetSegmentation().GetNthSegment(i).SetName(cfg.get('label_names',{}).get(str(value),'LABEL_'+str(value)))
   slicer.mrmlScene.RemoveNode(label)
  report['segmentation_status']='REVIEWED_SEGMENTATION'if cfg.get('segmentation_reviewed')else'SUPPLIED_SEGMENTATION_NEEDS_REVIEW'
 elif seg is not None:report['segmentation_status']='REVIEWED_SEGMENTATION'if cfg.get('segmentation_reviewed')else'SUPPLIED_SEGMENTATION_NEEDS_REVIEW'
 else:
  seg=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode','CANDIDATE_SEGMENTATION');seg.CreateDefaultDisplayNodes();seg.SetReferenceImageGeometryParameterFromVolumeNode(volume)
  report['segmentation_status']='NEEDS_SEGMENTATION'
  if cfg.get('modality','').upper()=='CT'and cfg.get('intensity_is_hu')is True:
   auto=cfg.get('auto_ct',{});limits=auto.get('threshold_hu',[200,3000]);mask=(image>=limits[0])&(image<=limits[1])
   if auto.get('fill_internal_holes',False):mask=ndimage.binary_fill_holes(mask)
   cc,n=ndimage.label(mask);counts=np.bincount(cc.ravel());minimum=auto.get('minimum_component_volume_mm3',20)
   eligible=[int(i)for i in np.argsort(counts[1:])[::-1]+1 if counts[i]*voxvol>=minimum]
   keep=eligible[:auto.get('maximum_components',64)]
   report['auto_ct']={'threshold_hu':limits,'minimum_volume_mm3':minimum,'component_count':n,'retained':len(keep),'eligible_omitted_by_limit':len(eligible)-len(keep),'fill_internal_holes':auto.get('fill_internal_holes',False)}
   for i,value in enumerate(keep,1):
    sid=seg.GetSegmentation().AddEmptySegment('CT_COMPONENT_%03d_UNIDENTIFIED'%i)
    slicer.util.updateSegmentBinaryLabelmapFromArray((cc==value).astype('uint8'),seg,sid,volume)
   report['segmentation_status']='NEEDS_SEGMENTATION_REVIEW'
 if seg.GetParentTransformNode():raise DecisionRequired('SEGMENTATION_PARENT_TRANSFORM_REQUIRES_EXPLICIT_HANDLING')
 seg.SetReferenceImageGeometryParameterFromVolumeNode(volume);seg.CreateDefaultDisplayNodes()
 seg.GetSegmentation().SetConversionParameter('Smoothing factor','0.0')
 selected=cfg.get('selected_segments',[]);available=[seg.GetSegmentation().GetNthSegment(i).GetName()for i in range(seg.GetSegmentation().GetNumberOfSegments())]
 missing=sorted(set(selected)-set(available))
 if missing:raise ValueError('Requested segments not found: '+repr(missing))
 for i in range(seg.GetSegmentation().GetNumberOfSegments()):
  original=seg.GetSegmentation().GetNthSegment(i);name=original.GetName();sid=seg.GetSegmentation().GetNthSegmentID(i)
  if selected and name not in selected:continue
  native=vtkOrientedImageData();seg.GetBinaryLabelmapRepresentation(sid,native)
  nativeMatrix=vtk.vtkMatrix4x4();native.GetImageToWorldMatrix(nativeMatrix)
  NM=np.array([[nativeMatrix.GetElement(a,b)for b in range(4)]for a in range(4)])
  native_volume=float(np.count_nonzero(slicer.util.arrayFromSegmentBinaryLabelmap(seg,sid))*abs(np.linalg.det(NM[:3,:3])))
  mask=slicer.util.arrayFromSegmentBinaryLabelmap(seg,sid,volume)>0
  if not mask.any():continue
  cc,n=ndimage.label(mask)
  for component,bounds in enumerate(ndimage.find_objects(cc),1):
   if bounds is None:continue
   local=cc[bounds]==component;offset=np.array([bounds[2].start,bounds[1].start,bounds[0].start],dtype=int)
   identifier='REGION_%04d'%(len(report['components'])+1)
   f=out/'masks'/(identifier+'.npz');np.savez_compressed(f,mask=local.astype('uint8'),crop_min_ijk=offset,ijk_to_ras=M)
   single=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode',identifier);single.CreateDefaultDisplayNodes();single.SetReferenceImageGeometryParameterFromVolumeNode(volume)
   csid=single.GetSegmentation().AddEmptySegment(identifier)
   slicer.util.updateSegmentBinaryLabelmapFromArray((cc==component).astype('uint8'),single,csid,volume)
   single.GetSegmentation().SetConversionParameter('Smoothing factor','0.0');single.CreateClosedSurfaceRepresentation()
   poly=vtk.vtkPolyData();single.GetClosedSurfaceRepresentation(csid,poly)
   if poly.GetNumberOfCells()==0:raise ValueError('Empty surface '+identifier)
   # VTK STL writer retains the scene's RAS coordinates; STL has no reliable unit header.
   stl=out/'surfaces'/(identifier+'.stl');writer=vtk.vtkSTLWriter();writer.SetFileName(str(stl));writer.SetInputData(poly);writer.SetFileTypeToBinary();writer.Write()
   report['components'].append({'part':identifier,'parent_segment':name,'component_index':component,'mask':str(f.relative_to(out)),'surface':str(stl.relative_to(out)),'voxel_count':int(local.sum()),'reference_volume_mm3':float(local.sum()*voxvol),'parent_native_volume_mm3':native_volume,'resampling':'Nearest neighbor to source-image geometry; compare physical origin/direction, not array indices'})
   slicer.mrmlScene.RemoveNode(single)
 assert slicer.util.saveNode(volume,str(out/'source_image.nrrd'))
 assert slicer.util.saveNode(seg,str(out/'segmentation.seg.nrrd'))
 seg.CreateClosedSurfaceRepresentation();slicer.util.setSliceViewerLayers(background=volume);slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
 slicer.util.resetSliceViews();slicer.util.resetThreeDViews();slicer.util.selectModule('SegmentEditor')
 editor=slicer.modules.segmenteditor.widgetRepresentation().self().editor;editor.setSegmentationNode(seg);editor.setSourceVolumeNode(volume)
 assert slicer.util.saveScene(str(out/'manual_review.mrb'))
 report['state']='PREPARED';save();qt.QTimer.singleShot(200,lambda:slicer.app.exit(0))
except DecisionRequired as e:
 report.update(state='DECISION_REQUIRED',segmentation_status=str(e));save();qt.QTimer.singleShot(200,lambda:slicer.app.exit(0))
except Exception:
 report.update(state='FAILED',exception=traceback.format_exc());save();print(report['exception'],flush=True);qt.QTimer.singleShot(200,lambda:slicer.app.exit(1))
