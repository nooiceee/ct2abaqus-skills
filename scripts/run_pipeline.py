"""Portable orchestrator. Geometry conversion only, no analysis submission."""
import argparse,datetime,hashlib,json,os,shutil,signal,subprocess,sys,zipfile
from pathlib import Path
SCRIPTS=Path(__file__).resolve().parent
def digest(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args()
 cp=Path(args.config).resolve();cfg=json.loads(cp.read_text(encoding='utf-8-sig'))
 if cfg.get('geometry_only',True)is not True:raise ValueError('These helpers implement geometry_only=true')
 def path(v):
  p=Path(os.path.expandvars(os.path.expanduser(v)));return str((cp.parent/p).resolve())if not p.is_absolute()else str(p.resolve())
 for k in ['image','segmentation','output_dir']:
  if cfg.get(k):cfg[k]=path(cfg[k])
 out=Path(cfg['output_dir']);out.mkdir(parents=True,exist_ok=False)
 status={'started':datetime.datetime.now().isoformat(),'state':'STARTED','analysis':'NOT_RUN','stages':[]}
 def save(): (out/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
 save()
 try:
  image=Path(cfg['image'])
  if image.suffix.lower()=='.zip':
   extracted=out/'source_unpack';extracted.mkdir()
   with zipfile.ZipFile(image)as z:
    members=z.infolist();total=sum(x.file_size for x in members)
    if total>cfg.get('max_archive_uncompressed_bytes',16*1024**3):raise ValueError('Archive exceeds configured unpack budget')
    for x in members:
     p=(extracted/x.filename).resolve()
     if not p.is_relative_to(extracted.resolve())or (x.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe archive member '+x.filename)
    z.extractall(extracted)
   candidates=[p for p in extracted.rglob('*')if p.is_file()and p.name.lower().endswith(('.nii','.nii.gz','.nrrd'))and not p.name.lower().endswith('.seg.nrrd')]
   if cfg.get('archive_image_member'):
    selected=(extracted/cfg['archive_image_member']).resolve()
    if not selected.is_relative_to(extracted.resolve())or not selected.is_file():raise ValueError('Invalid archive_image_member')
    cfg['image']=str(selected)
   elif len(candidates)>1:
    status.update(state='NEEDS_IMAGE_FILE_SELECTION',candidate_images=[str(p)for p in candidates]);save();return
   else:cfg['image']=str(candidates[0]if len(candidates)==1 else extracted)
   if cfg.get('archive_segmentation_member'):
    selected=(extracted/cfg['archive_segmentation_member']).resolve()
    if not selected.is_relative_to(extracted.resolve())or not selected.is_file():raise ValueError('Invalid archive_segmentation_member')
    cfg['segmentation']=str(selected)
   elif not cfg.get('segmentation'):
    segmentations=list(extracted.rglob('*.seg.nrrd'))
    if len(segmentations)==1:cfg['segmentation']=str(segmentations[0])
   cfg['source_archive']={'path':str(image),'sha256':digest(image),'uncompressed_bytes':total}
  slicer=cfg.get('slicer_executable')or os.environ.get('SLICER_EXECUTABLE')or shutil.which('Slicer')or shutil.which('Slicer.exe')
  if not slicer or not Path(slicer).is_file():raise FileNotFoundError('Configure the installed Slicer application executable')
  cfg['slicer_executable']=str(Path(slicer).resolve())
  (out/'config.resolved.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
  env=os.environ.copy();env['CT2ABAQUS_CONFIG']=str(out/'config.resolved.json');env['PYTHONUTF8']='1'
  for k in ['ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS','OMP_NUM_THREADS','VTK_SMP_MAX_THREADS']:env[k]=str(cfg.get('threads',2))
  def run(name,cmd):
   with (out/(name+'.log')).open('w',encoding='utf-8')as log:
    options={'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW}if os.name=='nt'else {'start_new_session':True}
    p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=str(out),env=env,**options)
    try: code=p.wait(timeout=cfg.get('timeout_seconds',900))
    except subprocess.TimeoutExpired:
     if os.name=='nt':subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=log,stderr=log)
     else:os.killpg(p.pid,signal.SIGTERM)
     raise RuntimeError(name+' timed out; only this launched process tree was stopped')
   status['stages'].append({'stage':name,'command':cmd,'exit_code':code});save()
   if code:raise RuntimeError(name+' failed; inspect '+str(out/(name+'.log')))
  run('slicer_prepare',[slicer,'--no-splash','--ignore-slicerrc','--python-script',str(SCRIPTS/'slicer_prepare.py')])
  prep=json.loads((out/'prepared.json').read_text(encoding='utf-8'))
  status['segmentation_status']=prep['segmentation_status']
  if not prep.get('components'):
   status['state']=prep['segmentation_status'];save();return
  run('mesh',[sys.executable,str(SCRIPTS/'mesh_and_inp.py'),'--config',str(out/'config.resolved.json')])
  mesh=json.loads((out/'mesh_report.json').read_text())
  status['complete_requested_regions']=mesh['complete_requested_regions']
  if not mesh['parts']:raise RuntimeError('No mesh parts succeeded; no INP candidate exists')
  if cfg.get('abaqus_command'):
   imp={'input_inp':str(out/'model/image_geometry.inp'),'output_cae':str(out/'model/image_geometry.cae'),'report_json':str(out/'abaqus_import.json'),'expected_parts':len(mesh['parts']),'expected_elements':sum(x['elements']for x in mesh['parts'])}
   (out/'abaqus_config.json').write_text(json.dumps(imp,indent=2))
   env['CT2ABAQUS_IMPORT_CONFIG']=str(out/'abaqus_config.json')
   run('abaqus_import',[cfg['abaqus_command'],'cae','noGUI='+str(SCRIPTS/'abaqus_import.py')])
   imp_report=json.loads((out/'abaqus_import.json').read_text());assert imp_report['state']=='CAE_IMPORT_VERIFIED'
   status['cae_import']='VERIFIED'
  else:status['cae_import']='NOT_RUN'
  status['state']='GEOMETRY_GENERATED'if mesh['complete_requested_regions']else'PARTIAL_GEOMETRY'
 except Exception as e:
  status.update(state='FAILED',error=repr(e));save();raise
 finally:
  status['finished']=datetime.datetime.now().isoformat();save()
  files=[]
  for p in sorted(out.rglob('*')):
   if p.is_file()and p.name!='manifest.json':files.append({'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':digest(p)})
  (out/'manifest.json').write_text(json.dumps({'files':files},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
