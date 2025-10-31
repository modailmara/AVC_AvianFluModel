"""
The Quarantine Farmers scenario
  - uses the default parameters
  - uses the default farms and people input files
  - farmers remain on their farm if there are any infectious cattle on the farm
"""
import pandas as pd

from mesa.batchrunner import batch_run

from VisualiseResults import visualise_paths, visualise_visit_counts, write_scenario_summary_graph, \
    visualise_steps_to_spillover
from support_functions import get_output_data_dir
from Models.MainModel import MainModel

# 15 weeks
DAYS = 15 * 7
STEPS = DAYS * 24

NUM_ITERATIONS = 10

# STEPS = 100  # testing

scenario_name = 'QuarantineFarmers'
var_name = 'is_quarantine_farmer'
var_values = [False, True]

if __name__ == "__main__":
    # simulator = ABMSimulator()
    results = batch_run(
        MainModel,
        parameters={
            'scenario_name': scenario_name,
            var_name: var_values},
        iterations=NUM_ITERATIONS,
        max_steps=STEPS,
        number_processes=3,
        data_collection_period=1,
        display_progress=True
    )

    print('creating DF')
    all_df = pd.DataFrame(results)
    print('writing data')
    all_df.to_csv(get_output_data_dir(scenario_name) / '{}_data-{}.csv'.format(scenario_name, NUM_ITERATIONS),
                  index=False)
