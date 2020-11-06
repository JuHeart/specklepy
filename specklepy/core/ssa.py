from IPython import embed
import numpy as np
import os

from astropy.io import fits

from specklepy.core import alignment
from specklepy.core.reconstruction import Reconstruction
from specklepy.exceptions import SpecklepyTypeError, SpecklepyValueError
from specklepy.io.outfile import Outfile
from specklepy.io.reconstructionfile import ReconstructionFile
from specklepy.logging import logger
from specklepy.utils.box import Box
from specklepy.plotting.plots import imshow


def ssa(files, mode='same', reference_file=None, outfile=None, in_dir=None, tmp_dir=None, lazy_mode=True,
        box_indexes=None, debug=False, **kwargs):
    """Compute the SSA reconstruction of a list of files.

    The simple shift-and-add (SSA) algorithm makes use of the structure of typical speckle patterns, i.e.
    short-exposure point-spread functions (PSFs). These show multiple peaks resembling the diffraction-limited PSF of
    coherent fractions within the telescope aperture. Under good conditions or on small telescopes, there is typically
    one largest coherent atmospheric cell and therefore, speckle PSFs typically show one major intensity peak. The
    algorithm makes use of this fact and identifies the emission peak in a given observation frame, assuming that this
    always belongs to the same star, and aligns all frames on the coordinate of the emission peak.

    See Bates & Cady (1980) for references.

    Args:
        files (list or array_like):
            List of complete paths to the fits files that shall be considered for the SSA reconstruction.
        mode (str):
            Name of the reconstruction mode: In 'same' mode, the reconstruction covers the same field of view of the
            reference file. In 'full' mode, every patch of the sky that is covered by at least one frame will be
            contained in the final reconstruction.
        reference_file (str, int, optional):
            Path to a reference file or index of the file in files, relative to which the shifts are computed. See
            specklepy.core.aligment.get_shifts for details. Default is 0.
        outfile (specklepy.io.recfile, optional):
            Object to write the result to, if provided.
        in_dir (str, optional):
            Path to the files. `None` is substituted by an empty string.
        tmp_dir (str, optional):
            Path of a directory in which the temporary results are stored in.
        lazy_mode (bool, optional):
            Set to False, to enforce the alignment of a single file with respect to the reference file. Default is True.
        box_indexes (list, optional):
            Constraining the search for the intensity peak to the specified box. Searching the full frames if not
            provided.
        debug (bool, optional):
            Show debugging information. Default is False.

    Returns:
        reconstruction (np.ndarray):
            The image reconstruction. The size depends on the mode argument.
    """

    logger.info("Starting SSA reconstruction...")
    # Check parameters
    if not isinstance(files, (list, np.ndarray)):
        if isinstance(files, str):
            files = [files]
        else:
            raise SpecklepyTypeError('ssa()', argname='files', argtype=type(files), expected='list')

    if isinstance(mode, str):
        if mode not in ['same', 'full', 'valid']:
            raise SpecklepyValueError('ssa()', argname='mode', argvalue=mode, expected="'same', 'full' or 'valid'")
    else:
        raise SpecklepyTypeError('ssa()', argname='mode', argtype=type(mode), expected='str')

    # if reference_file is None:
    #     reference_file = files[0]
    # elif isinstance(reference_file, int):
    #     reference_file = files[reference_file]
    # elif not isinstance(reference_file, str):
    #     raise SpecklepyTypeError('ssa()', argname='reference_file', argtype=type(reference_file), expected='str or int')

    if outfile is None:
        pass
    elif isinstance(outfile, str):
        pass
    #     outfile = ReconstructionFile(files=files, filename=outfile, cards={"RECONSTRUCTION": "SSA"})
    # elif isinstance(outfile, ReconstructionFile):
    #     pass
    else:
        raise SpecklepyTypeError('ssa()', argname='outfile', argtype=type(outfile), expected='str')

    if in_dir is None:
        in_dir = ''
    # reference_file = os.path.join(in_dir, reference_file)

    if tmp_dir is not None:
        if isinstance(tmp_dir, str) and not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir)

    if not isinstance(lazy_mode, bool):
        raise SpecklepyTypeError('ssa()', argname='lazy_mode', argtype=type(lazy_mode), expected='bool')

    if box_indexes is not None:
        box = Box(box_indexes)
    else:
        box = None

    if 'variance_extension_name' in kwargs.keys():
        var_ext = kwargs['variance_extension_name']
    else:
        var_ext = 'VAR'

    if debug:
        logger.setLevel('DEBUG')
        logger.handlers[0].setLevel('DEBUG')
        logger.info("Set logging level to DEBUG")

    reconstruction = Reconstruction(in_files=files, mode=mode, alignment_method='ssa',
                                    reference_image=reference_file,
                                    in_dir=in_dir, tmp_dir=tmp_dir, out_file=outfile,
                                    var_ext=var_ext,
                                    box_indexes=box_indexes, debug=debug)

    reconstruction_image, reconstruction_var = reconstruction.coadd_long_exposures()

    # # Align reconstructions if multiple files are provided
    # if lazy_mode and len(files) == 1:
    #
    #     # Do not align just a single file
    #     with fits.open(os.path.join(in_dir, files[0])) as hdu_list:
    #         cube = hdu_list[0].data
    #         if var_ext in hdu_list:
    #             var_cube = hdu_list[var_ext].data
    #         else:
    #             var_cube = None
    #         reconstruction, reconstruction_var = coadd_frames(cube, var_cube=var_cube, box=box)
    #
    # else:
    #
    #     # Compute temporary reconstructions of the individual cubes
    #     tmp_files = []
    #     for index, file in enumerate(files):
    #         with fits.open(os.path.join(in_dir, file)) as hdu_list:
    #             cube = hdu_list[0].data
    #             if var_ext in hdu_list:
    #                 var_cube = hdu_list[var_ext].data
    #                 logger.debug(f"Found variance extension {var_ext} in file {file}")
    #             else:
    #                 logger.debug(f"Did not find variance extension {var_ext} in file {file}")
    #                 var_cube = None
    #             tmp, tmp_var = coadd_frames(cube, var_cube=var_cube, box=box)
    #
    #         if debug:
    #             imshow(box(tmp), norm='log')
    #
    #         tmp_file = os.path.basename(file).replace(".fits", "_ssa.fits")
    #         tmp_file = os.path.join(tmp_dir, tmp_file)
    #         logger.info("Saving interim SSA reconstruction of cube to {}".format(tmp_file))
    #         tmp_file_object = Outfile(tmp_file, data=tmp, verbose=True)
    #
    #         # Store variance of temporary reconstruction
    #         if tmp_var is not None:
    #             tmp_file_object.new_extension(var_ext, data=tmp_var)
    #             del tmp_var
    #         tmp_files.append(tmp_file)
    #
    #     # Align tmp reconstructions and add up
    #     file_shifts, image_shape = alignment.get_shifts(tmp_files, reference_file=reference_file,
    #                                                     return_image_shape=True, lazy_mode=True)
    #     pad_vectors, ref_pad_vector = alignment.get_pad_vectors(file_shifts, cube_mode=(len(image_shape) == 3),
    #                                                             return_reference_image_pad_vector=True)
    #
    #     # Iterate over file-wise reconstructions
    #     reconstruction = None
    #     reconstruction_var = None
    #     for index, file in enumerate(tmp_files):
    #
    #         # Read data
    #         with fits.open(file) as hdu_list:
    #             tmp_image = hdu_list[0].data
    #             if var_ext in hdu_list:
    #                 tmp_image_var = hdu_list[var_ext].data
    #             else:
    #                 tmp_image_var = None
    #
    #         # Initialize or co-add reconstructions and var images
    #         if reconstruction is None:
    #             reconstruction = alignment.pad_array(tmp_image, pad_vectors[index], mode=mode,
    #                                                  reference_image_pad_vector=ref_pad_vector)
    #             if tmp_image_var is not None:
    #                 reconstruction_var = alignment.pad_array(tmp_image_var, pad_vectors[index], mode=mode,
    #                                                          reference_image_pad_vector=ref_pad_vector)
    #         else:
    #             reconstruction += alignment.pad_array(tmp_image, pad_vectors[index], mode=mode,
    #                                                   reference_image_pad_vector=ref_pad_vector)
    #             if tmp_image_var is not None:
    #                 reconstruction_var += alignment.pad_array(tmp_image_var, pad_vectors[index], mode=mode,
    #                                                           reference_image_pad_vector=ref_pad_vector)
    # logger.info("Reconstruction finished...")

    # Save the result to an Outfile
    if outfile is not None:
        embed()
        # is isinstance(outfile, str):
        #     outfile = ReconstructionFile(files=files, filename=outfile, cards={"RECONSTRUCTION": "SSA"})
        outfile.data = reconstruction_image
        if reconstruction_var is not None:
            outfile.new_extension(name=var_ext, data=reconstruction_var)

    # Return reconstruction (and the variance map if computed)
    if reconstruction_var is not None:
        return reconstruction_image, reconstruction_var
    return reconstruction_image

