#!/usr/bin/env python

import argparse
import os
import sys
import warnings

try:
    from specklepy.logging import logging
    from specklepy.io.parameterset import ParameterSet
    from specklepy.io.filemanager import FileManager
    from specklepy.reduction.flat import MasterFlat
    from specklepy.deprecated import setups
    from specklepy.reduction import sky
except ModuleNotFoundError:
    # Prepare import from current path
    PATH = os.getcwd()
    warnings.warn("Importing from path {}. Apparently the package is not installed properly on your machine!".format(PATH), ImportWarning)
    sys.path.insert(0, PATH)

    # Repeat import
    from specklepy.logging import logging
    from specklepy.io.parameterset import ParameterSet
    from specklepy.io.filemanager import FileManager
    from specklepy.reduction.flat import MasterFlat
    from specklepy.deprecated.setups import identify_setups
    from specklepy.reduction import sky
    from specklepy.utils.plot import imshow



def parser(options=None):

    parser = argparse.ArgumentParser(description='This script reduces the data, following the parameters specified in the paramater fils.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-p', '--parameter_file', type=str, help='Path to the parameter file.')
    parser.add_argument('-d', '--debug', type=bool, default=False, help='Set to True to inspect intermediate results.')

    if options is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(options)
    return args



def main(options=None):

    args = parser(options=options)

    # Default values
    defaults_file = "specklepy/config/reduction.cfg"
    essential_attributes = ['filePath', 'fileList', 'tmpDir', 'skipFlat', 'flatCorrectionPrefix', 'setupKeywords', 'skipSky', 'ignore_time_stamps', 'skySubtractionPrefix']
    make_dirs = ['tmpDir']

    # Read parameters from file
    if args.parameter_file is None:
        raise RuntimeError("No parameter file was provided! Use --help for instructions.")
    else:
        params = ParameterSet(parameter_file=args.parameter_file,
                        defaults_file=defaults_file,
                        essential_attributes=essential_attributes,
                        make_dirs=make_dirs)

    # Execute data reduction
    # (0) Read file list table
    logging.info("Reading file list ...")
    inFiles = FileManager(params.fileList)
    print(inFiles.table)

    # (1) Flat fielding
    if not params.skipFlat:
        flat_files = inFiles.filter({'OBSTYPE': 'FLAT'})
        master_flat = MasterFlat(flat_files, filename=params.masterFlatFile, file_path=params.filePath)
        master_flat.combine()
        inFiles.table = master_flat.run_correction(inFiles.table, filter={'OBSTYPE': ['SCIENCE', 'SKY']}, prefix=params.flatCorrectionPrefix)

    # (...) Linearisation

    # (...) Identify setups
    inFiles.identify_setups(params.setupKeywords)

    # (...) Sky subtraction
    if not params.skipSky:
        sequences = sky.identify_sequences(params.fileList, file_path=params.filePath, ignore_time_stamps=params.ignore_time_stamps)
        for sequence in sequences:
            sequence.subtract_master_sky(saveto=params.tmpDir, filename_prefix=params.skySubtractionPrefix)




if __name__ == '__main__':
    main()
