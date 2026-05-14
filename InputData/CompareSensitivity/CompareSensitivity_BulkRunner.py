"""
Runs sensitivity analysis on some parameters
"""
import pandas as pd

from support_functions import get_output_data_dir
from InputData.scenario_constants import NUM_ITERATIONS, clear_working_directory
from InputData.CompareScenarios.CompareScenarios_BulkRunner import run_condition

PARAM_VALUES_DICT = {
    # cow -> human
    'CATTLE_INFECT_HUMAN_PROB': [0.0000083, 0.01, 0.05, 0.1, 0.2],  # 0.05
    # human <-> human
    'HUMAN_INFECT_HUMAN_PROB': [0.01, 0.05, 0.1, 0.2],  # 0.1
    # human -> env
    'HUMAN_INFECT_ENV_PROB': [0, 0.05, 0.1, 0.15, 0.2],  # 0.1
    # env -> human
    'ENV_INFECT_HUMAN_PROB': [0, 0.05, 0.1, 0.15, 0.2],  # 0.1
    # truck -> env
    'TRUCK_INFECT_ENV_PROB': [0, 0.1, 0.3, 0.4]  # 0.3
}


def main():
    scenario_name = 'CompareSensitivity'
    clear_working_directory(scenario_name)

    for parameter, values in PARAM_VALUES_DICT.items():
        run_condition(scenario_name, parameter, {parameter: values}, extra_columns=[parameter])


if __name__ == "__main__":
    main()

