from pathlib import Path

from constants import STEPS_PER_DAY, DAYTIME_STEPS


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


def is_business_hours(all_steps):
    """
    True if the model step falls in business hours.
    Step 1 is the first step of the first workday (Monday). Each 24 hours is STEPS_PER_DAY steps long.
    The first 1 <= x <= DAYTIME_STEPS of each day is work hours.
    Weekends (saturday and sunday) are not business hours.

    :param all_steps: Total count of steps since the model started
    :type all_steps: int
    :return: True if the step falls in business hours
    :rtype: bool
    """
    # get the number of days and the steps into the day
    all_days, leftover_steps = divmod(all_steps, STEPS_PER_DAY)
    weeks, leftover_days = divmod(all_days, 7)

    # print("{} (w={}, d={}, s={}): {}".format(all_steps, weeks, leftover_days, leftover_steps,
    #                                          leftover_days < 5 and 1 <= leftover_steps <= DAYTIME_STEPS))
    return leftover_days < 5 and 1 <= leftover_steps <= DAYTIME_STEPS


def is_weekend(all_steps):
    """
    True if the model step falls in a weekend
    Step 1 is the first step of the first workday (Monday). Each 24 hours is STEPS_PER_DAY steps long.
    Weekends (saturday and sunday) are days 5 and 6 of each week

    :param all_steps: Total count of steps since the model started
    :type all_steps: int
    :return: True if the step falls in a weekend
    :rtype: bool
    """
    # get the number of days and the steps into the day
    all_days, leftover_steps = divmod(all_steps, STEPS_PER_DAY)
    weeks, leftover_days = divmod(all_days, 7)

    return leftover_days in [5, 6]

