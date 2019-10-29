import unittest
from holopy.algorithms.psfextraction import PSFExtraction
from holopy.io.paramhandler import ParamHandler


class TestPSFExtraction(unittest.TestCase):

    def setUp(self):
        self.parameter_file = "data/test/test_parfile.ini"
        self.defaults_file = "holopy/config/holography_defaults.cfg"
        self.essential_attributes = ['inDir', 'tmpDir', 'refSourceFile', 'psfRadius']
        self.make_dirs = ['tmpDir']
        self.params = ParamHandler(parameter_file=self.parameter_file,
                        defaults_file=self.defaults_file,
                        essential_attributes=self.essential_attributes,
                        make_dirs=self.make_dirs)

    def test_init(self):
        PSFExtraction(self.params)


    def test_initialize_apertures(self):
        algorithm = PSFExtraction(self.params)
        print(algorithm.star_table)
        algorithm.init_ref_apertures(self.params.inFiles[0])


    def test_extract(self):
        algorithm = PSFExtraction(self.params)
        algorithm.extract()


if __name__ == "__main__":
    unittest.main()