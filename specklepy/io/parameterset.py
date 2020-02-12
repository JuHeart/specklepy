import os
import configparser
# from configparser import ConfigParser
from astropy.table import Table

from specklepy.exceptions import SpecklepyTypeError
from specklepy.logging import logging
from specklepy.io.filemanager import FileManager


class ParameterSet(object):

    def __init__(self, parameter_file, defaults_file=None, essential_attributes=None, make_dirs=None):
        """Class that carries parameters.

        This class carries all the important parameters. The values are
        provided by reading in a default/ config file first (if a file is
        provided) and then reading in the actual parameter file to overwrite
        the default values. The parameters are stored hierarchically following
        the sections of the defaults or parameter files to allow the same names
        in multiple sections. The parameters are stored within Section class
        instances, see below, and are thereby accessible via attribute calls.

        In a second step this class is checking a list of essential parameters
        for existence and creates directories, if the arguments are not None.

        Args:
            parameter_file (str):
                Path to a file that contains parameters
            defaults_file (str, optional):
                Path to a file that contains default parameters.
            essential_attributes (list, optional):
                List of attributes that are essential and are thus filled from
                the defaults file, if not provided in the parameter file.
            make_dirs (list, optional):
                List of directory paths to create, if they are not existing yet.
        """

        # Check input parameters
        if isinstance(parameter_file, str):
            # Check whether file exist
            if not os.path.isfile(parameter_file):
                raise FileNotFoundError("Parameter file {} not found!".format(parameter_file))
            self.parameter_file = parameter_file
        else:
            raise SpecklepyTypeError('ParameterSet', argname='parameter_file', argtype=type(parameter_file), expected='str')

        if isinstance(defaults_file, str):
            if not os.path.isfile(defaults_file):
                raise FileNotFoundError("Defaults file {} not found!".format(defaults_file))
            self.defaults_file = defaults_file
        elif defaults_file is None:
            self.defaults_file = defaults_file
        else:
            raise SpecklepyTypeError('ParameterSet', argname='defaults_file', argtype=type(defaults_file), expected='str')

        if essential_attributes is None:
            essential_attributes = []
        if make_dirs is None:
            make_dirs = []


        # Create essential attributes from defaults file
        if self.defaults_file is not None:
            defaults = configparser.ConfigParser(inline_comment_prefixes="#")
            defaults.optionxform = str  # make option names case sensitive
            logging.info("Reading defaults file {}".format(self.defaults_file))
            defaults.read(self.defaults_file)

            for section in defaults.sections():
                self.__setattr__(section.lower(), Section(defaults[section]))
            # for attr in essential_attributes:
            #     if not hasattr(self, attr):
            #         attr_set = False
            #         for section in defaults.sections():
            #             for key in defaults[section]:
            #                 if key == attr:
            #                     value = defaults[section][key]
            #                     # Interprete data type
            #                     try:
            #                         setattr(self, key, eval(value))
            #                     except:
            #                         setattr(self, key, value)
            #                     attr_set = True
            #         if not attr_set:
            #             logging.warning("Essential parameter '{}' not found in parameter file or config file!".format(attr))

        # Overwrite attributes from parameter_file
        parser = configparser.ConfigParser(inline_comment_prefixes="#")
        parser.optionxform = str  # make option names case sensitive
        logging.info("Reading parameter file {}".format(self.parameter_file))
        parser.read(self.parameter_file)
        for section in parser.sections():
            if not hasattr(self, section.lower()):
                self.__setattr__(section.lower(), Section(parser[section]))
            else:
                for option in parser[section]:
                    value = parser[section][option]
                    try:
                        self.__getattribute__(section.lower()).__setattr__(option, eval(value))
                    except:
                        self.__getattribute__(section.lower()).__setattr__(option, value)
            # for key in parser[section]:
            #     value = parser[section][key]
            #     # Interprete data type
            #     try:
            #         setattr(self, key, eval(value))
            #     except:
            #         setattr(self, key, value)

        # Create directories
        self.makedirs(dir_list=make_dirs)

        # Create file lists
        try:
            self.inFiles = FileManager(self.paths.inDir).files
        except AttributeError:
            logging.warning("ParameterSet instance is not storing 'inFiles' due to missing entry 'inDir' parameter in parameter file!")



    def makedirs(self, dir_list):
        """
        This function makes sure that the paths exist and creates if not.
        """

        for key in dir_list:
            path = getattr(self.paths, key)
            path = os.path.dirname(path) + '/' # Cosmetics to allow for generic input for inDir
            if not os.path.exists(path):
                logging.info('Creating {} directory {}'.format(key, path))
                os.makedirs(path)



class Section(object):

    def __init__(self, options=None):
        """Dummy object class that stores section options.

        Args:
            options (configparser.SectionProxy, optional):
                All section options to be stored.
        """

        if not isinstance(options, (dict, configparser.SectionProxy)):
            raise SpecklepyTypeError('Section', argname='options', argtype=type(options), expected='dict')

        for key in options.keys():
            value = options[key]
            try:
                setattr(self, key, eval(value))
            except:
                setattr(self, key, value)
