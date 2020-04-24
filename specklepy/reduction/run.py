from IPython import embed
import matplotlib.pyplot as plt
import numpy as np

from specklepy.io.filemanager import FileManager
from specklepy.logging import logger
from specklepy.reduction import flat, sky
from specklepy.utils import combine

# Suppress downloading from IERS
from astropy.utils import iers
iers.conf.auto_download = False

# TODO: Split this function into the parts and sort into the other modules


def all(params, debug=False):
    # (0) Read file list table
    logger.info("Reading file list ...")
    inFiles = FileManager(params.paths.fileList)
    logger.info('\n' + str(inFiles.table))

    # (1) Initialize reduction files
    # TODO: Implement a data model for the reduction files

    # (2) Flat fielding
    if not params.flat.skip:
        flat_files = inFiles.filter({'OBSTYPE': 'FLAT'})
        if len(flat_files) == 0:
            logger.warning("Did not find any flat field observations. No flat field correction will be applied!")
        else:
            logger.info("Starting flat field correction...")
            master_flat = flat.MasterFlat(flat_files, filename=params.flat.masterFlatFile,
                                          file_path=params.paths.filePath)
            master_flat.combine()

    # (3) Linearization
    # TODO: Implement linearization

    # (4) Sky subtraction
    if not params.sky.skip:

        logger.info("Starting sky subtraction...")
        logger.info(f"Source of sky background measurement: {params.sky.source}")

        # Identify source files and time stamps
        sky_files = []
        sky_times = []
        if params.sky.source == 'default':
            sky_files = inFiles.filter({'OBSTYPE': 'SKY'})
            sky_timestamps = inFiles.filter({'OBSTYPE': 'SKY'}, namekey='DATE')
            sky_times = combine.time_difference(sky_timestamps[0], list(sky_timestamps))
            if debug:
                print("Sky files are:", sky_files)
                print("Sky time stamps are:", sky_times)
            if len(sky_files) == 0:
                logger.warning("Did not find any sky observations. No sky subtraction will be applied!")
                # TODO: Implement proper abortion of sky subtraction

        elif params.sky.source in ['image', 'frame']:
            # TODO: Implement sky subtraction from image
            pass

        # Start extracting sky fluxes
        sky_fluxes = np.zeros(sky_times.shape)
        sky_flux_uncertainties = np.zeros(sky_times.shape)
        for i, file in enumerate(sky_files):
            bkg, d_bkg = sky.get_sky_background(file, path=params.paths.filePath)
            sky_fluxes[i] = bkg
            sky_flux_uncertainties[i] = d_bkg
        if debug:
            print(f"Shapes:\nT: {sky_times.shape}\nF: {sky_fluxes.shape}\ndF: {sky_flux_uncertainties.shape}")

        # Extract time stamps and names of science files
        science_files = inFiles.filter({'OBSTYPE': 'SCIENCE'})
        science_timestamps = inFiles.filter({'OBSTYPE': 'SCIENCE'}, namekey='DATE')
        science_times = combine.time_difference(sky_timestamps[0], list(science_timestamps))

        # Compute weighted sky background for each file
        science_sky_fluxes = np.zeros(science_times.shape)
        science_sky_flux_uncertainties = np.zeros(science_times.shape)
        for i, file in enumerate(science_files):
            t0 = science_timestamps[i]
            dt = combine.time_difference(t0, sky_timestamps)
            weights = combine.get_distance_weights(dt)
            if debug:
                print('Time differences:', dt)
                print('Time weights:', weights)

            wbkg, dwbkg = combine.weighted_mean(sky_fluxes, vars=np.square(sky_flux_uncertainties), weights=weights)

            science_sky_fluxes[i] = wbkg
            science_sky_flux_uncertainties[i] = dwbkg

        if debug:
            print('Science sky fluxes:', science_sky_fluxes)
            print('Science sky flux uncertainties:', science_sky_flux_uncertainties)

        # Plot sky flux estimates
        for i, file in enumerate(sky_files):
            plt.text(sky_times[i], sky_fluxes[i], file, rotation=90, alpha=.5)
        for i, file in enumerate(science_files):
            plt.text(science_times[i], science_sky_fluxes[i], file, rotation=90, alpha=.66)
        plt.errorbar(x=sky_times, y=sky_fluxes, yerr=sky_flux_uncertainties,
                     fmt='None', ecolor='tab:blue', alpha=.5)
        plt.plot(sky_times, sky_fluxes, 'D', label='Sky', c='tab:blue')
        plt.errorbar(x=science_times, y=science_sky_fluxes, yerr=science_sky_flux_uncertainties,
                     fmt='None', ecolor='tab:orange', alpha=.66)
        plt.plot(science_times, science_sky_fluxes, 'D', label='Science', c='tab:orange')
        plt.xlabel('Time (s)')
        plt.ylabel('Flux (counts)')
        plt.legend()
        plt.show()
        plt.close()