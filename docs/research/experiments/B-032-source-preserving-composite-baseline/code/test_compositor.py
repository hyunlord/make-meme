import unittest
import numpy as np
from compositor import bbox, blend, fixed_envelope, mask_assisted, radius_for_sources

class Contracts(unittest.TestCase):
    def test_exact_endpoints_and_boundary(self):
        s = np.full((1,3,3), -.37, np.float32)
        g = np.full_like(s, .91)
        e = np.array([[0,.25,1]], np.float32)
        y = blend(s,g,e)
        np.testing.assert_array_equal(y[0,0],s[0,0])
        np.testing.assert_array_equal(y[0,2],g[0,2])
        np.testing.assert_allclose(y[0,1], .75*s[0,1]+.25*g[0,1])
    def test_bbox_and_static_margin(self):
        s=np.zeros((2,100,100),bool); s[:,40:60,30:50]=True
        a=np.zeros((100,100),bool); a[20:30,60:70]=True
        e,b=fixed_envelope(s,a)
        self.assertEqual((b.x0,b.y0,b.x1,b.y1),(26,16,74,64))
        self.assertEqual(e[16,26],.0625)
        self.assertEqual(e[30,40],1)
        self.assertEqual(e[15,26],0)
        self.assertEqual(radius_for_sources(s),2)
    def test_euclidean_union_and_feather(self):
        s=np.zeros((30,30),bool);s[10,10]=True
        t=np.zeros_like(s);t[20,20]=True
        e=mask_assisted(s,t,2)
        self.assertEqual(e[10,12],1)
        self.assertLess(e[12,12],1)
        self.assertEqual(e[20,20],1)
        self.assertEqual(e[10,13],.75)
        self.assertEqual(e[0,0],0)
    def test_invalid_contract(self):
        with self.assertRaises(ValueError): bbox(np.zeros((2,2),bool))
        with self.assertRaises(ValueError): blend(np.zeros((2,2,3),np.float32),np.zeros((2,2,3),np.float32),np.ones((2,2),np.float32)*2)
if __name__=='__main__': unittest.main()
