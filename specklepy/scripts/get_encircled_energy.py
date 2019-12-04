#!/usr/bin/env python

import argparse
import os
import sys
import warnings
import numpy as np
from astropy.io import fits
from datetime import datetime
from matplotlib.colors import LogNorm
import matplotlib.pyplot as plt

try:
    from specklepy.logging import logging
    from specklepy.core.aperture import Aperture
    from specklepy.utils.plot import imshow, encircled_energy_plot, maximize_plot
except ModuleNotFoundError:
    # Prepare import from current path
    PATH = os.getcwd()
    warnings.warn("Importing from path {}. Apparently the package is not installed properly on your machine!".format(PATH), ImportWarning)
    sys.path.insert(0, PATH)

    # Repeat import
    from specklepy.logging import logging
    from specklepy.core.aperture import Aperture
    from specklepy.utils.plot import imshow, encircled_energy_plot, maximize_plot



def parser(options=None):

    parser = argparse.ArgumentParser(description='This script extracts the encircled energy as a function of readius within an aperture.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-f', '--file', type=str, default=None, help='File name to analyse.')
    parser.add_argument('-i', '--index', nargs='+', type=int, help='Center index of the aperture to analyse. Provide this as "--index 123 456", without other symbols.')
    parser.add_argument('-r', '--radius', type=int, default=10, help='Radius of the aperture to analyse in pix.')
    parser.add_argument('-n', '--normalize', type=str, default=None, help='Normalize the energy data, to either "peak", "aperture" or set to None for not normalizing. Default is "aperture".')
    parser.add_argument('-o', '--outdir', type=str, default=None, help='Directory to write the results to. Default is to repace .fits by .dat and add a "energy" prefix.')
    parser.add_argument('-m', '--maximize', type=bool, default=True, help='Set to True to show every debug plot on full screen. Default is True.')
    parser.add_argument('-d', '--debug', type=bool, default=False, help='Set to True to inspect results.')

    if options is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(options)
    return args



def main(options=None):

    args = parser(options=options)


    # Interprete input
    args.index = tuple(args.index)

    if args.file is None:
        raise RuntimeError("No file was provided!")

    outfile = os.path.basename(args.file)
    outfile = "energy_" + outfile.replace(".fits", ".dat")
    outfile = os.path.join(args.outdir, outfile)


    # SInitialize the aperture
    aperture = Aperture(args.index, args.radius, data=args.file, subset_only=False)
    peak = aperture.get_aperture_peak()
    aperture = Aperture(peak, args.radius, data=args.file, subset_only=True)
    if args.debug:
        imshow(aperture.data, maximize=args.maximize)


    xdata, ydata = aperture.get_encircled_energy()

    if args.normalize == 'peak':
        ydata /= ydata[0]
    elif args.normalize == 'aperture':
        ydata /= ydata[-1]
    elif args.normalize is not None:
        raise ValueError("Normalize must be either 'peak', 'aperture, or None!'")


    # Save encircled energy data to outfile
    header = "Radius Energy"
    data = np.concatenate(([xdata], [ydata]), axis=0).transpose()
    np.savetxt(outfile, data, header=header)

    if args.debug:
        encircled_energy_plot(outfile, maximize=args.maximize)



if __name__ == '__main__':
    main()