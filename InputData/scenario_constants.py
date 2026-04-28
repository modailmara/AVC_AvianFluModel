"""
This file has constants that are used repeatedly for the scenario batch run programs.

It helps to make sure the same batch
"""
from support_functions import get_output_data_dir

# 15 weeks
DAYS = 15 * 7
STEPS = DAYS * 24

NUM_ITERATIONS = 500

# None means use all the available processors
NUM_PROCESSORS = None


def clear_working_directory(scenario_name):
    # clear the working directory
    working_dir = get_output_data_dir(scenario_name) / 'working'
    if working_dir.exists():
        for filepath in [x for x in working_dir.iterdir() if x.is_file()]:
            filepath.unlink()
