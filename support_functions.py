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


def get_output_data_dir(scenario_name):
    scenario_output_dir = get_scenario_input_dir(scenario_name) / 'output'
    scenario_output_dir.mkdir(exist_ok=True)
    return scenario_output_dir


def get_scenario_input_dir(scenario_dir_name):
    """
    Gets the absolute path to a named scenario directory, which contains all the input files for the scenario.
    :param scenario_dir_name: Name of the scenario directory
    :type scenario_dir_name: str
    :return: Path object of the scenario input directory
    :rtype: pathlib.Path object
    """
    return get_input_data_dir() / scenario_dir_name


