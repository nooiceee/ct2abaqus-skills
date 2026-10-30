import gzip,json,os,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

class IntakeTests(unittest.TestCase):
    def invoke(self,root,config):
        cp=root/'config.json';cp.write_text(json.dumps(config),encoding='utf-8')
        result=subprocess.run([sys.executable,str(ROOT/'scripts/run_pipeline.py'),'--config',str(cp)],capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONUTF8='1'))
        return result,json.loads((Path(config['output_dir'])/'STATUS.json').read_text())

    def test_zip_path_traversal_is_rejected_before_any_application(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);arc=root/'input.zip'
            with zipfile.ZipFile(arc,'w')as z:z.writestr('../escaped.txt',b'test')
            result,status=self.invoke(root,{'image':str(arc),'output_dir':str(root/'output'),'slicer_executable':str(root/'nonexistent_application')})
            self.assertNotEqual(result.returncode,0);self.assertEqual(status['state'],'FAILED')
            self.assertFalse((root/'output/escaped.txt').exists());self.assertEqual(status['stages'],[])

    def test_ambiguous_scalar_volumes_require_selection(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);arc=root/'input.zip'
            with zipfile.ZipFile(arc,'w')as z:z.writestr('a.nrrd',b'a');z.writestr('b.nrrd',b'b')
            result,status=self.invoke(root,{'image':str(arc),'output_dir':str(root/'output')})
            self.assertEqual(result.returncode,0);self.assertEqual(status['state'],'NEEDS_IMAGE_FILE_SELECTION')
            self.assertEqual(len(status['candidate_images']),2);self.assertEqual(status['stages'],[])

    def test_uncompressed_archive_budget_is_enforced(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);arc=root/'input.zip'
            with zipfile.ZipFile(arc,'w')as z:z.writestr('a.bin',b'1234')
            result,status=self.invoke(root,{'image':str(arc),'output_dir':str(root/'output'),'max_archive_uncompressed_bytes':3})
            self.assertNotEqual(result.returncode,0);self.assertEqual(status['state'],'FAILED');self.assertEqual(status['stages'],[])

    def test_synthetic_fixture_matches_its_record_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory()as td:
            output=Path(td)/'fixture';command=[sys.executable,str(ROOT/'scripts/create_test_fixture.py'),'--out',str(output)]
            first=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONUTF8='1'));self.assertEqual(first.returncode,0,first.stderr)
            expected=json.loads((output/'expected.json').read_text());data=(output/'labels.nrrd').read_bytes();header,payload=data.split(b'\n\n',1)
            self.assertIn(b'sizes: 48 40 32',header);labels=np.frombuffer(gzip.decompress(payload),dtype=np.uint8).reshape(32,40,48)
            self.assertEqual(int((labels==1).sum()),expected['label1_voxels']);self.assertEqual(int((labels==2).sum()),expected['label2_voxels'])
            second=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,PYTHONUTF8='1'));self.assertNotEqual(second.returncode,0);self.assertEqual((output/'labels.nrrd').read_bytes(),data)

if __name__=='__main__':unittest.main()
