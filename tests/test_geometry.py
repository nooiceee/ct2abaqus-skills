import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from mesh_and_inp import voxel

class VoxelGeometryTests(unittest.TestCase):
    def fixture(self,matrix):
        mask=np.zeros((3,4,5),dtype=np.uint8);mask[1:3,1:4,1:5]=1
        return {'mask':mask,'crop_min_ijk':np.array([7,11,13]),'ijk_to_ras':matrix}

    def check_geometry(self,matrix):
        z=self.fixture(matrix);xyz,conn,qa=voxel(z,1000)
        self.assertEqual(len(conn),24)
        self.assertEqual(qa['element_type'],'C3D8')
        self.assertTrue(np.array_equal(np.unique(conn),np.arange(len(xyz))))
        corners=xyz[conn]
        determinants=np.linalg.det(np.stack([corners[:,1]-corners[:,0],corners[:,3]-corners[:,0],corners[:,4]-corners[:,0]],axis=2))
        self.assertTrue(np.all(determinants>0))
        np.testing.assert_allclose(determinants,abs(np.linalg.det(matrix[:3,:3])),rtol=1e-12,atol=1e-12)
        self.assertAlmostEqual(qa['volume_mm3'],float(determinants.sum()))
        ijk=np.argwhere(z['mask'])[:,::-1]+z['crop_min_ijk']
        expected_centers=ijk@matrix[:3,:3].T+matrix[:3,3]
        np.testing.assert_allclose(corners.mean(axis=1),expected_centers,rtol=1e-12,atol=1e-12)

    def test_positive_affine_preserves_physical_centers_and_volume(self):
        m=np.array([[.8,.2,0,10],[0,1.1,.1,20],[0,0,1.3,30],[0,0,0,1.]])
        self.check_geometry(m)

    def test_left_handed_image_produces_positive_volume_elements(self):
        m=np.array([[-.8,0,0,10],[0,1.1,0,20],[0,0,1.3,30],[0,0,0,1.]])
        self.check_geometry(m)

    def test_element_budget_stops_instead_of_downsampling(self):
        with self.assertRaises(ValueError):voxel(self.fixture(np.eye(4)),23)

    def test_empty_region_is_rejected(self):
        with self.assertRaises(AssertionError):voxel({'mask':np.zeros((2,2,2))},100)

if __name__=='__main__':unittest.main()
