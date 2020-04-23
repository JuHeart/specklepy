from configparser import ConfigParser
import glob
import os

from astropy.io import fits
from astropy.table import Table
from astropy.utils.exceptions import AstropyWarning, AstropyUserWarning

from specklepy.logging import logger


def setup(files, instrument, sortby, outfile, parfile):
    """Sets up the data reduction parameter file and file list.

    Args:
        files (str):
            Path to the files.
        instrument:
            Name of the instrument that took the data. This must be covered by config/instruments.cfg.
        sortby:
            Header card that is used for the sorting of files.
        outfile:
            Name of the file that contains all the files.
        parfile:
            Name of the parameter file.
    """

    # Defaults
    header_cards = ['OBSTYPE', 'OBJECT', 'FILTER', 'EXPTIME', 'nFRAMES', 'DATE']
    instrument_config_file = os.path.join(os.path.dirname(__file__), '../config/instruments.cfg')

    # Verification of args
    if not os.path.isdir(os.path.dirname(files)):
        raise RuntimeError("Path not found: {}".format(files))

    # Read config
    config = ConfigParser()
    config.read(instrument_config_file)
    instrument = config['INSTRUMENTS'][instrument]
    instrument_header_cards = config[instrument]

    # Double check whether all aliases are defined
    for card in header_cards:
        try:
            instrument_header_cards[card]
        except:
            logger.info(
                f"Dropping header card {card} from setup identification, as there is no description in the config file."
                f"\nCheck out {instrument_config_file} for details.")
            header_cards.remove(card)

    # Find files
    if '*' in files:
        files = glob.glob(files)
    else:
        files = glob.glob(files + '*fits')
    logger.info("Found {} file(s)".format(len(files)))

    # Prepare dictionary for collecting table data
    table_data = {'FILE': []}
    for card in header_cards:
        table_data[card] = []

    # Read data from files
    for file in files:
        logger.info(f"Retrieving header information from file {file}")
        try:
            hdr = fits.getheader(file)
        except (AstropyWarning, AstropyUserWarning):
            print("Caught")
        table_data['FILE'].append(os.path.basename(file))
        for card in header_cards:
            try:
                table_data[card].append(hdr[instrument_header_cards[card]])
            except KeyError:
                logger.info(
                    f"Skipping file {os.path.basename(file)} due to missing header card ({instrument_header_cards[card]}).")
                table_data[card].append("_" * 3)

    # Create table from dict and save
    table = Table([table_data[keyword] for keyword in table_data.keys()], names=table_data.keys())
    table.sort('FILE')
    table.sort('OBSTYPE')
    table.sort(sortby)
    logger.info("Writing data to {}".format(outfile))
    table.write(outfile, format='ascii.fixed_width', overwrite=True)

    # Write dummy parameter file for the reduction
    logger.info("Creating default reduction INI file {}".format(parfile))
    par_file_content = "[PATHS]" \
                       f"\nfilePath = {files}" \
                       f"\nfileList = {outfile}" \
                       "\ntmpDir = tmp/" \
                       "\n\n[FLAT]" \
                       "\nskipFlat = False" \
                       "\nmasterFlatFile = MasterFlat.fits" \
                       "\nflatCorrectionPrefix = f_" \
                       "\n\n[SKY]" \
                       "\nskipSky = False" \
                       "\nskySubtractionPrefix = s"
    with open(parfile, 'w+') as parfile:
        parfile.write(par_file_content)