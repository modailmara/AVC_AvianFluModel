from pathlib import Path


def get_root_dir():
    """
    Gets the full path for the root of the AvianFlu project.
    Will work anywhere in the application directory hierarchy.

    :return: Path object with directory of this project.
    :raise: ValueError if 'AvianFlu' is not in the current path.
    :rtype: pathlib.Path object
    """
    cwd = Path.cwd()

    try:
        # find where WeCress is in the path (this is where the ValueError will be raised if it isn't)
        wecress_index = cwd.parts.index('AvianFlu')

        # new path just up to the WeCress bit
        wecress_path = Path(*cwd.parts[:wecress_index+1])

    except ValueError as e:
        # we're not in a subdirectory of WeCress (how?)
        raise ValueError("{} is not a subdirectory of AvianFlu\n{}".format(cwd, e))

    return wecress_path


def get_input_data_dir():
    """
    Gets the absolute path to the directory with the input data files

    :return: Path object with input data files
    :raise: ValueError if 'AvianFlu' is not in the current path.
    :rtype: pathlib.Path object
    """
    return get_root_dir() / 'InputData'
