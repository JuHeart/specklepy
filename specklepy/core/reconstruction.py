from IPython import embed
import numpy as np
import os

from astropy.io import fits

from specklepy.core import alignment
from specklepy.core.ssa import coadd_frames
from specklepy.exceptions import SpecklepyTypeError, SpecklepyValueError
from specklepy.io.outfile import Outfile
from specklepy.io.reconstructionfile import ReconstructionFile
from specklepy.logging import logger
from specklepy.utils.box import Box


class Reconstruction(object):

    """Base class for image reconstructions.

    This class stores the principle parameters of the reconstructed image. In the future, the functions `ssa` and
    `holography` may become child classes of this one.
    """

    supported_modes = ['full', 'same', 'valid']

    def __init__(self, in_files, mode='same', reference_image=None, out_file=None, in_dir=None, tmp_dir=None,
                 alignment_method='collapse', var_ext=None, box_indexes=None, debug=False):
        """Create a Reconstruction instance.

        Args:
            in_files (list):
                List of input data cubes.
            mode (str, optional):
                Reconstruction mode, defines the final image size and can be `full`, `same` and `valid`. The final image
                sizes is derived as follows:
                - `full`:
                    The reconstruction image covers every patch of the sky that is covered by at least one frame in the
                    input data.
                - `same`:
                    The reconstruction image covers the same field of view as the image in the reference file.
                - `valid`:
                    The reconstruction image covers only that field that is covered by all images in the input files.
            reference_image (int or str, optional):
                The index in the `in_files` list or the name of the image serving as reference in 'same' mode.
            out_file (str, optional):
                Name of an output file to store the reconstructed image in.
            in_dir (str, optional):
                Path to the `in_files`.
            tmp_dir (str, optional):
                Path to the directory for storing temporary products.
            debug (bool, optional):
                Show debugging information.
        """

        # Check input parameter types
        if not isinstance(in_files, (list, np.ndarray)):
            raise SpecklepyTypeError('Reconstruction', 'in_files', type(in_files), 'list')
        if not isinstance(mode, str):
            raise SpecklepyTypeError('Reconstruction', 'mode', type(mode), 'str')
        if out_file is not None and not isinstance(out_file, str):
            raise SpecklepyTypeError('Reconstruction', 'out_file', type(out_file), 'str')

        # Check input parameter values
        if mode not in self.supported_modes:
            raise SpecklepyValueError('Reconstruction', 'mode', mode, f"in {self.supported_modes}")

        # Store input data
        self.in_files = in_files
        self.mode = mode
        self.out_file = out_file if out_file is not None else 'reconstruction.fits'
        self.reference_image = reference_image if reference_image is not None else 0
        self.in_dir = in_dir if in_dir is not None else ''
        self.tmp_dir = tmp_dir if tmp_dir is not None else ''
        self.var_ext = var_ext  # if var_ext is not None else 'VAR'
        self.box = Box(box_indexes) if box_indexes is not None else None

        # Retrieve name of reference file
        self.reference_file = self.identify_reference_file()

        # Derive shape of individual input frames
        single_cube_mode = len(self.in_files) == 1
        example_frame = fits.getdata(os.path.join(in_dir, self.in_files[0]))
        if example_frame.ndim == 3:
            example_frame = example_frame[0]
        self.frame_shape = example_frame.shape

        # Initialize image
        if single_cube_mode:
            self.image = np.zeros(self.frame_shape)
            self.shifts = (0, 0)
        else:
            # Compute SSA reconstructions of cubes or collapse cubes for initial alignments
            self.long_exp_files = self.create_long_exposures(alignment_method=alignment_method)

            # Identify reference tmp file
            self.reference_tmp_file = self.identify_reference_long_exposure_file()

            # Estimate relative shifts
            self.shifts = alignment.get_shifts(files=self.long_exp_files, reference_file=self.reference_tmp_file,
                                               lazy_mode=True, return_image_shape=False, in_dir=tmp_dir, debug=debug)

            # Derive corresponding padding vectors
            self.pad_vectors, self.reference_pad_vector = \
                alignment.get_pad_vectors(shifts=self.shifts, cube_mode=False, return_reference_image_pad_vector=True)

            # Derive corresponding image sizes
            self.image = self.initialize_image()

        # Initialize the variance map
        self.var = np.zeros(self.image.shape) if self.var_ext is not None else None

        # Initialize output file and create an extension for the variance
        self.out_file = ReconstructionFile(files=self.in_files, filename=self.out_file, shape=self.image.shape,
                                      in_dir=in_dir, cards={"RECONSTRUCTION": "SSA"})
        if self.var is not None:
            self.out_file.new_extension(name=self.var_ext, data=self.var)

    def identify_reference_file(self):

        # Initialize reference file
        reference_file = None

        # Interpret reference image
        if isinstance(self.reference_image, str):
            reference_file = self.reference_image
        elif isinstance(self.reference_image, int):
            reference_file = self.in_files[self.reference_image]
        else:
            SpecklepyTypeError('Reconstruction', 'reference_image', type(self.reference_image), 'int or str')

        return reference_file

    def identify_reference_long_exposure_file(self):
        """Identify the long exposure file that corresponds to the reference cube"""
        reference_tmp_file = None

        if isinstance(self.reference_image, str):
            for tmp_file in self.long_exp_files:
                if self.reference_file in tmp_file:
                    self.reference_tmp_file = tmp_file
            if reference_tmp_file is None:
                raise RuntimeError(f"Unable to identify reference file in list of temporary reconstructions!")

        elif isinstance(self.reference_image, int):
            reference_tmp_file = self.long_exp_files[self.reference_image]

        return reference_tmp_file

    def create_long_exposures(self, alignment_method):
        """Compute long exposures from the input data cubes."""

        # Initialize list of long exposure files
        long_exposure_files = []

        # Iterate over input data cubes
        for file in self.in_files:

            # Read data from file
            cube = fits.getdata(os.path.join(self.in_dir, file))
            image = None
            image_var = None

            # Compute collapsed or SSA'ed images from the cube
            if alignment_method == 'collapse':
                image = np.sum(cube, axis=0)
                tmp_file = 'int_' + os.path.basename(file)
            elif alignment_method == 'ssa':
                image, image_var = coadd_frames(cube=cube, box=self.box)
                tmp_file = 'ssa_' + os.path.basename(file)
            else:
                raise SpecklepyValueError('Reconstruction', 'alignment_method', alignment_method,
                                          expected="either 'collapse' or 'ssa'")

            # Store data to a new Outfile instance
            tmp_path = os.path.join(self.tmp_dir, tmp_file)
            logger.info(f"Saving temporary reconstruction of cube {file} to {tmp_path}")
            tmp_file_object = Outfile(tmp_path, data=image, verbose=True)
            if image_var is not None:
                tmp_file_object.new_extension(name=self.var_ext, data=image_var)

            # Add the recently created file to the list
            long_exposure_files.append(tmp_file)

        return long_exposure_files

    def initialize_image(self):
        """Initialize the reconstruction image."""

        # Initialize image along the input frame shape
        image = np.zeros(self.frame_shape)

        # Crop or expand according to the reconstruction mode
        if self.mode == 'same':
            pass
        elif self.mode == 'full':
            image = np.pad(image, self.reference_pad_vector, mode='constant')
        elif self.mode == 'valid':
            # Estimate minimum overlap
            _shifts = np.array(self.shifts)
            _crop_by = np.max(_shifts, axis=0) - np.min(_shifts, axis=0)
            image = image[_crop_by[0]:, _crop_by[1]:]

        return image

    def coadd_long_exposures(self):
        """Coadd the interim long exposures."""

        # Iterate over long exposure images
        for index, file in enumerate(self.long_exp_files):

            # Read data
            with fits.open(os.path.join(self.tmp_dir, file)) as hdu_list:
                tmp_image = hdu_list[0].data
                if self.var_ext is not None and self.var_ext in hdu_list:
                    tmp_image_var = hdu_list[self.var_ext].data
                else:
                    tmp_image_var = None

            # Co-add reconstructions and var images
            self.image += alignment.pad_array(tmp_image, self.pad_vectors[index], mode=self.mode,
                                                  reference_image_pad_vector=self.reference_pad_vector)
            if tmp_image_var is not None:
                self.var += alignment.pad_array(tmp_image_var, self.pad_vectors[index], mode=self.mode,
                                                          reference_image_pad_vector=self.reference_pad_vector)

        # Update out_file
        self.out_file.data = self.image
        if self.var_ext is not None and self.var is not None:
            self.out_file.update_extension(ext_name=self.var_ext, data=self.var)

        return self.image, self.var
