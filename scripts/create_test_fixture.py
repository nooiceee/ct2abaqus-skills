"""Small synthetic, nonclinical volumes for portable workflow checks."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
def write(path,a):
 header='NRRD0005\ntype: '+('short'if a.dtype==np.int16 else'unsigned char')+'\ndimension: 3\nspace: right-anterior-superior\nsizes: 48 40 32\nspace directions: (-0.8,0,0) (0,1.1,0) (0,0,1.3)\nkinds: domain domain domain\nendian: little\nencoding: gzip\nspace origin: (10,20,30)\n\n'
 path.write_bytes(header.encode()+gzip.compress(a.tobytes(order='C')))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
 z,y,x=np.indices((32,40,48));labels=np.zeros((32,40,48),dtype='uint8')
 labels[((x-12)/5)**2+((y-15)/6)**2+((z-12)/5)**2<=1]=1
 labels[((x-32)/4)**2+((y-23)/5)**2+((z-21)/4)**2<=1]=2
 labels[3:6,3:6,3:6]=1
 image=np.full(labels.shape,-1000,dtype=np.int16);image[labels>0]=700
 write(out/'synthetic_CT.nrrd',image);write(out/'labels.nrrd',labels)
 expected={'clinical_data':False,'dimensions_IJK':[48,40,32],'ijk_to_RAS':[[-.8,0,0,10],[0,1.1,0,20],[0,0,1.3,30],[0,0,0,1]],'label1_voxels':int((labels==1).sum()),'label2_voxels':int((labels==2).sum()),'face_connected_components':3,'expected_total_volume_mm3':float((labels>0).sum()*.8*1.1*1.3)}
 (out/'expected.json').write_text(json.dumps(expected,indent=2));print(out)
if __name__=='__main__':main()
