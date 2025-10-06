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


def get_output_data_dir():
    return get_root_dir() / 'output'


def get_day_from_steps(step_number):
    """
    Gets the day number given a step number.
    :param step_number: The step number to convert to a day number
    :type step_number: int
    :return: Day number for the given step
    :rtype: int
    """
    return step_number // STEPS_PER_DAY


def get_weeks_days_steps(steps):
    """
    From a number of steps, calculates the number of weeks and days.
    Also returns the number of leftover days (from week calculation), and number of leftover steps (from days).

    Note that days is from the steps, not after weeks is calculated. For example (assume STEPS_PER_DAY=16):
    get_weeks_days_steps(130) gives 1 week, 8 days, 1 leftover day, and 2 leftover steps

    :param steps: Total number of model steps.
    :type steps: int
    :return: Tuple of (total weeks, total days, days left after weeks, steps left after days)
    :rtype: tuple
    """
    days, leftover_steps = divmod(steps, STEPS_PER_DAY)
    weeks, leftover_days = divmod(days, 7)

    return weeks, days, leftover_days, leftover_steps


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
    _, _, leftover_days, leftover_steps = get_weeks_days_steps(all_steps)

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
    _, _, leftover_days, _ = get_weeks_days_steps(all_steps)

    return leftover_days in [5, 6]


def is_start_of_workday(step):
    """
    Returns True if the step is the first step of a working day.

    Step 1 is the first step of the first workday (Monday). Each 24 hours is STEPS_PER_DAY steps long.
    The first 1 <= x <= DAYTIME_STEPS of each day is work hours.
    Weekends (saturday and sunday, days 5 and 6) are not business hours.

    :param step: Step count of the model
    :type step: int
    :return: True if the first step of a weekday
    :rtype: bool
    """
    # get the number of days and the steps into the day
    _, _, leftover_days, leftover_steps = get_weeks_days_steps(step)

    # True if a weekday and the first step of the day
    return leftover_days in range(5) and leftover_steps == 1


def is_middle_of_workday(step):
    """
    Returns True if the step is the middle step of a working day.

    Step 1 is the first step of the first workday (Monday).
    The first 1 <= x <= DAYTIME_STEPS of each day is work hours.
    Weekends (saturday and sunday, days 5 and 6) are not business hours.

    :param step: Step count of the model
    :type step: int
    :return: True if step is the middle step of a weekday
    :rtype: bool
    """
    # get the number of days and the steps into the day
    _, _, leftover_days, leftover_steps = get_weeks_days_steps(step)

    # True if a weekday and the first step of the day
    return leftover_days in range(5) and leftover_steps == DAYTIME_STEPS // 2 + 1

