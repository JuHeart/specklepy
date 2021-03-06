import unittest
import numpy as np

from specklepy.core.segmentation import Segmentation


class TestSegmentation(unittest.TestCase):

    def setUp(self):
        self.shape = (4, 32, 32)
        self.data = np.random.rand(*self.shape)
        self.data[0] *= 3
        self.data[1] *= 1
        self.data[2] *= 4
        self.data[3] *= 5
        self.vars = np.random.rand(*self.shape) * 0.5

    def test_init(self):
        seg = Segmentation(3, 5, self.shape)

        for segment in seg:
            # imshow(image=self.data[0, segment.xmin:segment.xmax, segment.ymin:segment.ymax], title=str(segment))
            _ = self.data[0, segment.xmin:segment.xmax, segment.ymin:segment.ymax]
            print(segment)

    def test_call(self):
        segmentation = Segmentation(3, 5, self.shape)
        subarray = segmentation[0](self.data[0])
        # imshow(subarray)

    def test_contain(self):
        segmentation = Segmentation(3, 5, self.shape)
        test_pos = (1, 1)
        self.assertIn(test_pos, segmentation[0])

    def test_all_covered(self):
        np.random.seed(123)
        segmentation = Segmentation(3, 5, self.shape)
        positions = []
        for seg in segmentation.segments:
            pos = (np.random.randint(seg.xmin, seg.xmax), np.random.randint(seg.ymin, seg.ymax))
            positions.append(pos)
        self.assertTrue(segmentation.all_covered(positions=positions))



if __name__ == "__main__":
    unittest.main()