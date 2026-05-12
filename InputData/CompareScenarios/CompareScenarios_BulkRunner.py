"""
Runs a group of different scenarios and combines the results for the paper.
Does not preserve data not needed for the paper figure.

-   baseline,
-   quarantine + vaccinate farmers,
-   vaccinate farmers + FS clinicians
-   Vaccination + disinfect trucks + Common areas
"""
import pandas as pd

from mesa.batchrunner import batch_run

from support_functions import get_output_data_dir
from Models.MainModel import MainModel
from InputData.scenario_constants import NUM_ITERATIONS, STEPS, clear_working_directory, NUM_PROCESSORS


scenario_name = 'CompareScenarios'


def run_condition(condition, parameters):
    parameters['scenario_name'] = scenario_name
    results = batch_run(
        MainModel,
        parameters=parameters,
        iterations=NUM_ITERATIONS,
        max_steps=STEPS,
        number_processes=NUM_PROCESSORS,
        data_collection_period=1,
        display_progress=True
    )

    print('{}: creating DF and writing data'.format(condition))
    all_df = pd.DataFrame(results)
    spillover_columns = ['iteration', 'steps_to_community', 'Step']
    community_cols = ['Community_num_SUSCEPTIBLE', 'Community_num_EXPOSED', 'Community_num_INFECTIOUS',
                      'Community_num_RECOVERED']
    relevant_df = all_df.loc[:, spillover_columns + community_cols]
    relevant_df['condition'] = condition
    relevant_df.to_csv(get_output_data_dir(scenario_name) / '{}-{}_data-{}.csv'.format(scenario_name, condition,
                                                                                       NUM_ITERATIONS),
                       index=False)
    return relevant_df


def main():
    clear_working_directory(scenario_name)

    condition_df_list = []

    # baseline
    condition_df_list.append(run_condition('baseline', {}))

    # quarantine + vaccinate farmers
    parameters = {
        'IS_QUARANTINE_FARM': True,
        'VACC_ROLES': 'farmer'
    }
    condition_df_list.append(run_condition('quarantine + vaccinate farmers', parameters))

    # vaccinate farmers + FS clinicians
    parameters = {
        'VACC_ROLES': 'farmer, farm services clinician'
    }
    condition_df_list.append(run_condition('vaccinate farmers + FS clinicians', parameters))

    # Vaccination + disinfect trucks + Common areas
    parameters = {
        'VACC_ROLES': 'farmer, farm services clinician',
        'TRUCK_CLEANING_SCHEDULE': 'visit',
        'SHEET_NAME': 'no_common'
    }
    condition_df_list.append(
        run_condition('vaccinate farmers + FS clinicians and disinfect trucks and close common areas', parameters)
    )

    compare_scenarios_df = pd.concat(condition_df_list)
    compare_scenarios_df.to_csv(get_output_data_dir(scenario_name) / '{}_data-{}.csv'.format(scenario_name,
                                                                                             NUM_ITERATIONS),
                                index=False)


if __name__ == "__main__":
    main()

