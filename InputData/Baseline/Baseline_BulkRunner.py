"""
The Baseline scenario uses all default parameters.
"""
import pandas as pd

from mesa.batchrunner import batch_run

from InputData.scenario_constants import NUM_ITERATIONS, STEPS, clear_working_directory
from support_functions import get_output_data_dir
from Models.MainModel import MainModel

scenario_name = 'Baseline'


if __name__ == "__main__":
    clear_working_directory(scenario_name)

    results = batch_run(
        MainModel,
        parameters={
            'scenario_name': scenario_name,
        },
        iterations=NUM_ITERATIONS,
        max_steps=STEPS,
        number_processes=None,
        data_collection_period=1,
        display_progress=True
    )

    # convert to DataFrame and write to file
    results_df = pd.DataFrame(results)
    results_df.to_csv(get_output_data_dir(scenario_name) / '{}_data-{}.csv'.format(scenario_name, NUM_ITERATIONS),
                      index=False)
