import numpy as np
from scipy.signal import fftconvolve
from scipy.ndimage import zoom
import warnings

from astropy.io import fits
from astropy.modeling import models
from astropy import units as u
from astropy.units import UnitConversionError

from specklepy.exceptions import SpecklepyTypeError, SpecklepyValueError
from specklepy.logging import logger


class Telescope(object):
	"""Class carrying the parameters of a telescope.

	Attributes:
		diameter (astropy.units.Quantity):
		psf_source (str):
			Name of the PSF model or of the file, from which the PSF frames are extracted.
		psf_frame (int):
			Current frame of the PSF file.

	Optional attributes:
		central_obscuration (float, optional):
	"""

	__name__ = 'telescope'
	TIME_STEP_KEYS = ['TIMESTEP', 'INTTIME', 'CDELT3']
	RESOLUTION_KEYS = ['PIXSIZE', 'CDELT1']

	def __init__(self, diameter, psf_source, central_obscuration=None, psf_frame=0, **kwargs):
		"""Instantiate Telescope class:

		Args:
			diameter (float or astropy.units.Quantity):
				Telescope diameter, used to compute the light collecting area.
			psf_source (str):
				File name to read PSFs from or model name. Models can be either 'AiryDisk' or 'Gaussian'. The models
				require central_obscuration (float, optional): Radial fraction of the
				telescope aperture that is blocked by the secondary.
			central_obscuration (float, optional):
				Radial fraction that is centrally obscured, by the secondary mirror.
			psf_frame (int, optional):
				Index of the first frame to read from psf_source.
			kwargs:
				Are forwarded to the psf_source model.
		"""

		# Input parameters
		if isinstance(diameter, u.Quantity):
			self.diameter = diameter
		elif isinstance(diameter, (int, float)):
			logger.warning(f"Interpreting scalar type diameter as {diameter} m")
			self.diameter = u.Quantity(f"{diameter} m")
		else:
			raise SpecklepyTypeError('Telescope', 'diameter', type(diameter), 'u.Quantity')

		if isinstance(psf_source, str):
			self.psf_source = psf_source
		else:
			raise SpecklepyTypeError('Telescope', 'psf_source', type(psf_source), 'str')

		if isinstance(central_obscuration, float) or central_obscuration is None:
			self.central_obscuration = central_obscuration
		else:
			raise SpecklepyTypeError('Telescope', 'central_obscuration', type(central_obscuration), 'float')

		if isinstance(psf_frame, int):
			self.psf_frame = psf_frame
		else:
			raise SpecklepyTypeError('Telescope', 'psf_frame', type(psf_frame), 'int')

		# Derive secondary parameters
		if self.central_obscuration is not None:
			self.area = (1. - self.central_obscuration**2) * np.pi * (self.diameter / 2)**2
		else:
			self.area = np.pi * (self.diameter / 2)**2

		if psf_source.lower() in ['airydisk', 'gaussian']:
			self.model_psf(psf_source, **kwargs)
		else:
			self.read_psf_file(psf_source)

	def __call__(self, *args, **kwargs):
		return self.get_photon_rate(*args, **kwargs)

	def __str__(self):
		tmp = "Telescope:\n"
		for key in self.__dict__:
			if key == 'psf':
				continue
			tmp += "{}: {}\n".format(key, self.__dict__[key])
		return tmp

	def model_psf(self, model, radius, psf_resolution, shape=256, **kwargs):
		"""Models the PSF given the desired model function and kwargs.

		Args:
			model (str):
				Must be either 'airydisk' or 'gaussian'.
			radius (int, float, astropy.unit.Quantity):
				Radius of the PSF model that is the radius of the first zero in an AiryDisk model or the standard
				deviation of the Gaussian model. Scalar values will be interpreted in units of arcseconds.
			psf_resolution (int, float, astropy.unit.Quantity):
				Resolution of the model PSF, equivalent to the pixel scale of the array. Scalar values will be
				interpreted in units of arcseconds.
			shape (int, optional):
				Size of the model PSF along both axes.
			kwargs are forwarded to the model function.
		"""

		# Check input parameters
		if not isinstance(model, str):
			raise SpecklepyTypeError('model_psf', 'model', type(model), 'str')

		if isinstance(radius, u.Quantity):
			self.radius = radius
		elif isinstance(radius, (int, float)):
			logger.warning(f"Interpreting scalar type radius as {radius} arcsec")
			self.radius = u.Quantity(f"{radius} arcsec")
		else:
			raise SpecklepyTypeError('model_psf', 'radius', type(radius), 'u.Quantity')

		if isinstance(psf_resolution, u.Quantity):
			self.psf_resolution = psf_resolution
		elif isinstance(psf_resolution, (int, float)):
			logger.warning(f"Interpreting scalar type psf_resolution as {psf_resolution} arcsec")
			self.psf_resolution = u.Quantity(f"{psf_resolution} arcsec")
		else:
			raise SpecklepyTypeError('model_psf', 'psf_resolution', type(psf_resolution), 'u.Quantity')

		if isinstance(shape, int):
			center = (shape / 2, shape / 2)
			shape = (shape, shape)
		elif isinstance(shape, tuple):
			center = (shape[0] / 2, shape[1] / 2)
		else:
			raise SpecklepyTypeError('model_psf', 'shape', type(shape), 'int or tuple')

		if model.lower() == 'airydisk':
			model = models.AiryDisk2D(x_0=center[0], y_0=center[1], radius=float(self.radius / self.psf_resolution))
		elif model.lower() == 'gaussian':
			stddev = float(self.radius / self.psf_resolution)
			model = models.Gaussian2D(x_mean=center[0], y_mean=center[1], x_stddev=stddev, y_stddev=stddev)
		else:
			raise SpecklepyValueError('model_psf', 'model', model, 'either AiryDisk or Gaussian')

		y, x = np.mgrid[0:shape[0], 0:shape[1]]
		self.psf = model(x, y)
		self.psf = self.normalize(self.psf)

	def read_psf_file(self, filename, hdu_entry=0):
		"""Read PSF information from file.

		Args:
			filename (str):
				Name of the FITS file containing the PSF frames.
			hdu_entry (int, str, optional:
				Specification of the HDU to read from the file. Default is the first HDU.

		Returns:

		"""

		# Extract header
		header = fits.getheader(filename, hdu_entry)

		if header['NAXIS'] == 2:
			self.psf = self.normalize(fits.getdata(self.psf_source, hdu_entry))
		else:
			for key in self.TIME_STEP_KEYS:
				try:
					self.timestep = self._get_value(header, key)
					break
				except KeyError as e:
					continue
		for key in self.RESOLUTION_KEYS:
			try:
				self.psf_resolution = self._get_value(header, key)
				break
			except KeyError as e:
				continue
			raise IOError("No key from {} was found in file for the psf resolution.".format(self.RESOLUTION_KEYS))

	def _get_value(self, header, key, aliases=None):
		"""Extract unit quantities from FITS headers, based on the unit in the comment.

		Args:
			header:
				Header of the FITS file.
			key (str):
				Key or name of the FITS header card.
			aliases (dict, optional):
				The aliases dictionary maps unit strings such that they are understood by u.Unit(str).

		Returns:
			quantity (u.Quantity):
				Quantity derived from the combination of the FITS header card value and comment.
		"""

		# Read header card
		value = header[key]
		comment = header.comments[key]

		# Handle empty comment
		if not comment:
			logger.warning("Function 'get_value()' received an empty comment string and returns scalar value.")
			return value

		# Apply fall back values
		if aliases is None:
			aliases = {'sec': 's', 'milliarcsec': 'mas', 'microns': 'micron'}

		# Replace comment entries that are not understood by astropy.units by corresponding aliases
		if comment in aliases.keys():
			comment = aliases[comment]

		return value * u.Unit(comment)

	def get_photon_rate(self, photon_rate_density, photon_rate_density_resolution=None, integration_time=None,
						debug=False):
		"""Propagates the 'photon_rate_density' array through the telescope.

		The photon_rate_density is multiplied by the telescope collecting area and then
		convolved with the PSF. If the resolution of the flux array is different
		from the telescopes psf_resolution, then one is resampled. If the PSF is
		non-static, it will be integrated over the 'integration_time' value.

		Args:
			photon_rate_density (np.ndarray, dtype=u.Quantity):
			photon_rate_density_resolution (u.Quantity, optional):
			integration_time(u.Quantity, optional):
				Required only if the PSF is non-static.
			debug (bool, optional):
				Show additional information for debugging. Default is False.

		Returns:
			photon_rate (u.Quantity): PSF-convolved photon rate array.
		"""

		# Input parameters
		if not isinstance(photon_rate_density, u.Quantity):
			raise SpecklepyTypeError('get_photon_rate', 'photon_rate_density', type(photon_rate_density), 'u.Quantity')

		if photon_rate_density_resolution is not None:
			if not isinstance(photon_rate_density_resolution, u.Quantity):
				raise SpecklepyTypeError('get_photon_rate', 'photon_rate_density_resolution',
										 type(photon_rate_density_resolution), 'u.Quantity')
			psf_resample_mode = True
		else:
			psf_resample_mode = False

		if integration_time is None and hasattr(self, 'timestep'):
			raise ValueError("If the PSF source of Telescope is non-static, the call function requires the "
							 "integration_time.")
		elif isinstance(integration_time, (int, float)):
			logger.warning(f"Interpreting scalar type integration_time as {integration_time} s")
			integration_time = u.Quantity(f"{integration_time} s")
		elif not isinstance(integration_time, u.Quantity):
			raise SpecklepyTypeError('get_photon_rate', 'integration_time', type(integration_time), 'u.Quantity')

		# Apply telescope collecting area
		photon_rate = photon_rate_density * self.area
		total_flux = np.sum(photon_rate)
		photon_rate_unit = photon_rate.unit

		# Prepare PSF if non-static
		if hasattr(self, 'timestep'):
			self.integrate_psf(integration_time=integration_time)

		# Resample photon_rate_density to psf resolution
		if psf_resample_mode:
			try:
				ratio = float(photon_rate_density_resolution / self.psf_resolution)
			except UnitConversionError as e:
				raise UnitConversionError(f"The resolution values of the image ({photon_rate_density_resolution}) and "
										  f"PSF ({self.psf_resolution}) have different units!")

			#convolved = np.zeros(photon_rate.shape)
			with warnings.catch_warnings():
				warnings.simplefilter('ignore')
				if ratio < 1.0:
					self.psf = zoom(self.psf, 1/ratio, order=1) / ratio**2
					self.psf = self.normalize(self.psf)
				else:
					memory_sum = np.sum(photon_rate)
					photon_rate = zoom(photon_rate, ratio, order=1) / ratio**2
					photon_rate = photon_rate / np.sum(photon_rate) * memory_sum

		# Convolve the array with the PSF
		convolved = fftconvolve(photon_rate, self.psf, mode='same') * photon_rate_unit

		# Report on flux conservation
		if debug:
			print('Check of flux conservation during convolution:')
			print('Before: ', total_flux)
			print('After:  ', np.sum(convolved))
		return convolved.decompose()

	def normalize(self, array, mode='sum_circular'):
		"""Normalizes the input array depending on the mode.

		Args:
			array (np.ndarray):
				Array to be normalized.
			mode (str, optional):
				Can be either 'sum' for having a sum of 1, 'max' for having a peak value 1, or 'sum_circular' for
				subtracting a constant and then normalizing to a sum of 1. Default is 'sum_circular'.

		Returns:
			normalized (np.ndarray):
				Normalized array, according to mode.
		"""

		if not isinstance(array, np.ndarray):
			raise SpecklepyTypeError('normalize', 'array', type(array), 'np.ndarray')
		if np.sum(array) == 0:
			raise ValueError("Normalize received an array of zeros!")

		if mode not in ['sum', 'max', 'peak', 'sum_circular']:
			raise SpecklepyValueError('normalize', 'mode', mode, "'sum', 'max', or 'sum_circular'")

		if mode == 'sum':
			normalized = array / np.sum(array)
		elif mode == 'max':
			normalized = array / np.max(array)
		elif mode == 'sum_circular':
			x, y = array.shape
			low_cut = array[0, int(y/2)]
			array = np.maximum(array - low_cut, 0)
			normalized = self.normalize(array, mode='sum')
		else:
			normalized = None

		return normalized

	def integrate_psf(self, integration_time, hdu_entry=0):
		"""Integrates psf frames over the input time.

		Args:
			integration_time (u.Quantity):
				This is used for computing the number of frames 'nframes', via floor division by the 'timestep'
				attribute.
			hdu_entry (int):
				Specifier of the HDU. Default is None for the first HDU.
		"""

		# Check input parameters
		if isinstance(integration_time, (int, float)):
			logger.warning(f"Interpreting scalar type integration_time as {integration_time} s")
			integration_time = integration_time * u.s
		elif not isinstance(integration_time, u.Quantity):
			raise SpecklepyTypeError('integrate_psf', 'integration_time', type(integration_time), 'u.Quantity')

		if integration_time < self.timestep:
			raise ValueError(f"integrate_psf received integration time {integration_time} shorter than the time "
							 f"resolution of the psf source ({self.timestep})!")

		nframes = int(integration_time / self.timestep)

		# Read PSF frames from source file
		data = fits.getdata(self.psf_source, hdu_entry)

		self.psf_frame += 1
		if self.psf_frame + nframes < data.shape[0]:
			self.psf = np.sum(data[self.psf_frame : self.psf_frame+nframes], axis=0)
		else:
			self.psf = np.sum(data[self.psf_frame : ], axis=0)
			self.psf += np.sum(data[ : (self.psf_frame+nframes) % data.shape[0]], axis=0)
		self.psf_frame += nframes - 1
		self.psf_frame = self.psf_frame % data.shape[0]

		# Normalize the integrated PSF
		self.psf = self.normalize(self.psf)
