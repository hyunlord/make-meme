# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with existing research Python: python -m unittest discover -s code -p test_compositor.py
"""Fixed CPU contracts; fixtures do not establish generated-object coverage."""
from pathlib import Path
import hashlib
import tempfile
import unittest

import numpy as np
from PIL import Image

from compositor import (ContractError, alpha, blend, build_plate, distance,
                        load_rgb, plate_from_validity, save_rgb_new)


class CompositeContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.bg = np.full((240, 416, 3), 60, dtype=np.uint8)
        self.raw = np.full_like(self.bg, 201)

    def test_fixed_alpha_and_rounding(self) -> None:
        a = alpha((208.0, 120.0))
        self.assertEqual(a.dtype, np.dtype('float64'))
        self.assertEqual(a[120, 252], 1.0)
        self.assertAlmostEqual(a[120, 256], 0.5)
        self.assertEqual(a[120, 260], 0.0)
        c = blend(self.raw, self.bg, a)
        expected = np.rint(a[..., None] * self.raw + (1-a[..., None]) * self.bg).astype(np.uint8)
        np.testing.assert_array_equal(c, expected)

    def test_png_readback_exact_and_parent_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'raw.png'
            Image.fromarray(self.raw).save(source)
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            a = alpha((208.0, 120.0))
            result = save_rgb_new(Path(tmp)/'post.png', blend(load_rgb(source), self.bg, a))
            np.testing.assert_array_equal(result[a == 1], self.raw[a == 1])
            np.testing.assert_array_equal(result[a == 0], self.bg[a == 0])
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            with self.assertRaises(FileExistsError):
                save_rgb_new(Path(tmp)/'post.png', self.bg)

    def test_plate_provenance_uses_observable_same_pixels(self) -> None:
        start = self.bg.copy(); end = self.bg.copy()
        start[distance((104.0, 120.0)) <= 28] = 250
        end[distance((312.0, 120.0)) <= 28] = 220
        p = build_plate(start, end)
        np.testing.assert_array_equal(p.image, self.bg)
        np.testing.assert_array_equal(p.image[p.source_map == 1], start[p.source_map == 1])
        np.testing.assert_array_equal(p.image[p.source_map == 2], end[p.source_map == 2])
        self.assertFalse(np.any(p.source_map == 0))

    def test_common_observation_difference_fails(self) -> None:
        end = self.bg.copy(); end[0, 0, 0] += 1
        with self.assertRaises(ContractError):
            build_plate(self.bg, end)

    def test_unknown_is_never_filled(self) -> None:
        visible = distance((208.0, 120.0)) > 52
        with self.assertRaises(ContractError):
            plate_from_validity(self.bg, self.bg, (visible, visible))

    def test_wrong_image_coordinate_and_frame_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wrong = Path(tmp)/'wrong.png'
            Image.new('L', (416, 240)).save(wrong)
            with self.assertRaises(ContractError): load_rgb(wrong)
            Image.new('RGB', (240, 416)).save(wrong)
            with self.assertRaises(ContractError): load_rgb(wrong)
            nonpng = Path(tmp)/'wrong.jpg'
            Image.new('RGB', (416, 240)).save(nonpng)
            with self.assertRaises(ContractError): load_rgb(nonpng)
        for xy in ((float('nan'), 120), (416, 120), (208, 240)):
            with self.assertRaises(ContractError): alpha(xy)
        with self.assertRaises(ContractError): blend(self.raw.astype(np.float32), self.bg, alpha((208,120)))

    def test_stretched_object_can_be_clipped_despite_exact_core(self) -> None:
        stretched = self.bg.copy()
        stretched[116:125, 180:275] = [255, 0, 0]
        a = alpha((208.0, 120.0))
        post = blend(stretched, self.bg, a)
        np.testing.assert_array_equal(post[a == 1], stretched[a == 1])
        self.assertTrue(np.any(stretched[a == 0] != post[a == 0]))
        # This is a deliberately known fixture support, never an inferred real-object mask.
        self.assertTrue(np.all(post[120, 265] == self.bg[120, 265]))


if __name__ == '__main__':
    unittest.main()
