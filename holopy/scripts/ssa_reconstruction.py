import argparse

try:
    from holopy.io.filehandler import FileHandler
    from holopy.logging import logging
except ModuleNotFoundError:
    # Prepare import with hardcoded path
    import warnings
    PATH = '/home/bosco/Documents/phd/sowat/pipeline/github_holopy'
    warnings.warn("Importing spampy from hardcoded path {}. Apparently holopy is not installed properly on your machine!".format(PATH), ImportWarning)
    import sys
    sys.path.insert(0, PATH)

    # Repeat import
    from holopy.io.filehandler import FileHandler
    from holopy.logging import logging



def parser(options=None):

    parser = argparse.ArgumentParser(description='This script creates a simple shift-and-add (SSA) reconstruction of the input files.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-f', '--file', type=str, default=None, help='Fits file or generic file name to consider for the SSA reconstruction.')
    parser.add_argument('-o', '--output', type=str, default=None, help='Name of output file.')

    if options is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(options)
    return args


def main(options=None):

    args = parser(options=options)

    if args.file is not None:
        filehandler = FileHandler(args.file)
    else:
        logging.error("No file or file list was provided! Use --help for instructions.")
        raise RuntimeError("No file or file list was provided! Use --help for instructions.")

    logging.info(str(filehandler))

    # for filename in filehandler:
    #     slit = Slit(filename, datamodel=datamodel)
    #     slit.centroid(nbins=args.nbins)
    #     slit.writeto(args.dir + filename.replace('.fits', '.spam'))


if __name__ == '__main__':
    main()
