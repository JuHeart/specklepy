import unittest
import os


class TestReduce(unittest.TestCase):

    def setUp(self):
        self.parameter_file = 'data/test/test_reduction.par'

    def test_call(self):
        os.system('python specklepy/scripts/reduction.py -p {}'.format(self.parameter_file))



if __name__ == "__main__":
    unittest.main()