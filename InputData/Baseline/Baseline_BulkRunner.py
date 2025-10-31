"""
The Baseline scenario uses all default parameters.
"""
import pandas as pd

from mesa.batchrunner import batch_run


from VisualiseResults import write_scenario_summary_graph
from support_functions import get_output_data_dir
from Models.MainModel import MainModel

scenario_name = 'Baseline'

# 15 weeks
DAYS = 15 * 7
# DAYS = 7  # testing
STEPS = DAYS * 24

NUM_ITERATIONS = 10

if __name__ == "__main__":
    # simulator = ABMSimulator()
    results = batch_run(
        MainModel,
        parameters={
            'scenario_name': scenario_name,
        },
        iterations=NUM_ITERATIONS,
        max_steps=STEPS,
        number_processes=2,
        data_collection_period=1,
        display_progress=True
    )

    path_results = [result['paths'].infection_graph for result in results]
    write_scenario_summary_graph(scenario_name, path_results)

    # remove the path objects
    for result in results:
        del result['paths']

    # convert to DataFrame and write to file
    results_df = pd.DataFrame(results)
    results_df.to_csv(get_output_data_dir(scenario_name) / '{}_data-{}.csv'.format(scenario_name, NUM_ITERATIONS),
                      index=False)
