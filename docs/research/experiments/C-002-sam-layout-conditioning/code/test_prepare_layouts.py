"""CPU regression for frozen contour encoding, including retained disconnected speckles."""
import unittest
import cv2
import numpy as np
from prepare_layouts import render

class LayoutTest(unittest.TestCase):
    def test_outline_not_fill_and_components_retained(self):
        mask=np.zeros((480,832),np.uint8);mask[100:200,100:200]=255;mask[300,400]=255
        out=render(mask)
        self.assertEqual(out.dtype,np.uint8)
        self.assertTrue(np.all(out[150,150]==255))
        self.assertTrue(np.all(out[100,150]==0))
        self.assertTrue(np.all(out[300,400]==0))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        expected=np.full((480,832,3),255,np.uint8)
        cv2.drawContours(expected,contours,-1,(0,0,0),3)
        np.testing.assert_array_equal(out,expected)
    def test_fail_closed_invalid_masks(self):
        for mask in (np.zeros((480,832),np.uint8),np.ones((480,832),np.uint8),np.ones((10,10),np.uint8)):
            with self.assertRaises(ValueError):render(mask)

if __name__=='__main__':unittest.main()
