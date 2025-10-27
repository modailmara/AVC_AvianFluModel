"""
The Baseline scenario uses all default parameters.
"""

from mesa.batchrunner import batch_run


from VisualiseResults import visualise_paths, visualise_visit_counts, write_scenario_summary_graph
from Models.MainModel import MainModel

# 15 weeks
# DAYS = 15 * 7
DAYS = 7  # testing
STEPS = DAYS * 24

scenario_name = 'Baseline'

if __name__ == "__main__":
    # simulator = ABMSimulator()
    results = batch_run(
        MainModel,
        parameters={
            'scenario_name': scenario_name
        },
        iterations=3,
        max_steps=STEPS,
        number_processes=1,
        data_collection_period=-1,
        display_progress=True
    )

    # visualise_paths(results[0]['paths'])
    # visualise_visit_counts(results[0]['farm_visits'], DAYS)

    path_results = [result['paths'].infection_graph for result in results]
    write_scenario_summary_graph(scenario_name, path_results)
