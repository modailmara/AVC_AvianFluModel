"""
Scenario exploring the effect of changing the initial number of infectious farms
  - uses the default parameters
  - uses the default farms and people input files
  - varies the number of starting infectious farms (1 infectious cow each)
"""
import pandas as pd

from mesa.batchrunner import batch_run

from support_functions import get_output_data_dir
from Models.MainModel import MainModel
from InputData.scenario_constants import NUM_ITERATIONS, STEPS


scenario_name = 'AnimalIntroduction'
var_name = 'num_infected_farms'
var_values = [1, 5, 10, 15, 20]  # range(1, 20)


if __name__ == "__main__":
    # simulator = ABMSimulator()
    results = batch_run(
        MainModel,
        parameters={
            'scenario_name': scenario_name,
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
