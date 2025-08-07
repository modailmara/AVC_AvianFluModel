from pathlib import Path

from constants import STEPS_PER_DAY


def get_root_dir():
    """
    Gets the full path for the root of the AvianFlu project.
    Will work anywhere in the application directory hierarchy.

    :return: Path object with directory of this project.
    :raise: ValueError if 'AvianFlu' is not in the current path.
    :rtype: pathlib.Path object
    """
    cwd = Path.cwd()

    # find the last part where AvianFlu is a substring
    last_index = None
    for i, part in enumerate(cwd.parts):
        if 'avianflu' in part.lower():
            last_index = i

    if last_index is None:
        # we're not in a subdirectory of AvianFlu (how?)
        raise ValueError("{} is not a subdirectory of AvianFlu\n{}".format(cwd))
    else:
        avianflu_path = Path(*cwd.parts[:last_index+1])

    return avianflu_path


def get_input_data_dir():
    """
    Gets the absolute path to the directory with the input data files

    :return: Path object with input data files
    :raise: ValueError if 'AvianFlu' is not in the current path.
    :rtype: pathlib.Path object
    """
    return get_root_dir() / 'InputData'


def get_day_from_steps(step_number):
    """
    Gets the day number given a step number.
    :param step_number: The step number to convert to a day number
    :type step_number: int
    :return: Day number for the given step
    :rtype: int
    """
    return step_number // STEPS_PER_DAY
