from mesa.batchrunner import batch_run
from mesa.experimental.devs import ABMSimulator

from VisualiseResults import visualise_paths, visualise_visit_counts, write_scenario_summary_graph
from Models.MainModel import MainModel
from constants import convert_days_to_steps

DAYS = 100
STEPS = convert_days_to_steps(DAYS)


if __name__ == "__main__":
    # simulator = ABMSimulator()
    results = batch_run(
        MainModel,
        parameters={},  # {'width': 20, 'height': 20},
        iterations=10,
        max_steps=STEPS,
        number_processes=1,
        data_collection_period=-1,
        display_progress=True
    )
    for d in results:
        for name, anything in d.items():
            if name in ['RunId', 'iteration', 'Step']:
                print('{}: {}'.format(name, anything))
        print('---')

    # visualise_paths(results[0]['paths'])
    # visualise_visit_counts(results[0]['farm_visits'], DAYS)

    path_results = [result['paths'].infection_graph for result in results]
    write_scenario_summary_graph('default_scenario', path_results)
