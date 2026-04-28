"""
Change the frequency of cleaning the trucks.
"""
import pandas as pd

from mesa.batchrunner import batch_run

from support_functions import get_output_data_dir
from Models.MainModel import MainModel
from InputData.scenario_constants import NUM_ITERATIONS, STEPS, clear_working_directory
from constants import PersonRole


scenario_name = 'Quarantine+Vacc'
var_name = 'VACC_ROLES'
var_values = ['none',
              'farm services clinician',
              'farm services student, farm services clinician'
              ]


if __name__ == "__main__":
    clear_working_directory(scenario_name)
    results = batch_run(
        MainModel,
        parameters={
            'scenario_name': scenario_name,
            'IS_QUARANTINE_FARM': True,
            var_name: var_values},
        iterations=NUM_ITERATIONS,
        max_steps=STEPS,
        number_processes=None,
        data_collection_period=1,
        display_progress=True
    )

    print('creating DF')
    all_df = pd.DataFrame(results)
    print('writing data')
    all_df.to_csv(get_output_data_dir(scenario_name) / '{}_data-{}.csv'.format(scenario_name, NUM_ITERATIONS),
                  index=False)
