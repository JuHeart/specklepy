import configparser
import os
import sys
import yaml


def read(par_file):
    """Read parameter dictionary from a config file.

    Args:
        par_file (str):
            Name of the parameter file to read from.

    Returns:
        config (dict):
            Dictionary of config parameters.
    """

    # Identify type of file
    root, ext = os.path.splitext(par_file)

    if ext == '.yaml':
        return read_yaml(par_file)
    else:
        return read_ini(par_file)


def read_ini(par_file):
    """Read parameter dictionary from a config file in INI-format.

    Args:
        par_file (str):
            Name of the parameter file to read from.

    Returns:
        config (dict):
            Dictionary of config parameters.
    """

    # Set up the config parser
    parser = configparser.ConfigParser(inline_comment_prefixes='#')
    parser.optionxform = str  # make option names case sensitive

    # Read in config files
    parser.read(par_file)  # Overwrite defaults

    # Transforming parser information into dict type
    config = {}
    for section in parser.sections():
        config[section] = dict(parser[section])
    return config


def read_yaml(par_file):
    """Read parameter dictionary from a config file in YAML-format.

    Args:
        par_file (str):
            Name of the parameter file to read from.

    Returns:
        config (dict):
            Dictionary of config parameters.
    """

    with open(par_file, "r") as yaml_file:
        try:
            config = yaml.load(yaml_file, Loader=yaml.loader.FullLoader)
        except yaml.parser.ParserError as e:
            sys.tracebacklimit = 0
            raise e
    return config


def update_from_file(params, par_file):
    """Update the config dictionary params from file.

    Args:
        params (dict):
            Dictionary holding the to-be-updated values.
        par_file (str):
            Name of the parameter file with the update values.

    Returns:
        params (dict):
            Updated dictionary of config parameters.
    """

    # Read config parameters to update from
    update = read(par_file=par_file)

    # Overwrite entries in the input dictionary
    for key in update.keys():
        if isinstance(update[key], dict):
            for kkey in update[key].keys():
                params[key][kkey] = update[key][kkey]
        else:
            params[key] = update[key]

    return params
