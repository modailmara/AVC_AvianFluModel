"""
The Quarantine Farmers scenario
  - uses the default parameters
  - uses the default farms and people input files
  - farmers remain on their farm if there are any infectious cattle on the farm
"""

from mesa.batchrunner import batch_run


from VisualiseResults import visualise_paths, visualise_visit_counts, write_scenario_summary_graph
from Models.MainModel import MainModel

# 15 weeks
DAYS = 15 * 7
STEPS = DAYS * 24

scenario_name = 'QuarantineFarmers'

if __name__ == "__main__":
    # simulator = ABMSimulator()
    results = batch_run(
        MainModel,
        parameters={
            'scenario_name': scenario_name,
            'is_quarantine_farmer': True},
        iterations=10,
        max_steps=STEPS,
        number_processes=5,
        data_collection_period=-1,
        display_progress=True
    )

    # visualise_paths(results[0]['paths'])
    # visualise_visit_counts(results[0]['farm_visits'], DAYS)

    path_results = [result['paths'].infection_graph for result in results]
    write_scenario_summary_graph(scenario_name, path_results)
