from mesa.batchrunner import batch_run
from VisualiseResults import visualise_paths

from MainModel import MainModel


if __name__ == "__main__":
    results = batch_run(
        MainModel,
        parameters={'width': 20, 'height': 20},
        iterations=100,
        max_steps=60,
        number_processes=5,
        data_collection_period=-1,
        display_progress=True
    )
    # for d in results:
    #     for name, anything in d.items():
    #         if name in ['RunId', 'iteration', 'Step', 'paths']:
    #             print('{}: {}'.format(name, anything))
    #     print('---')

    visualise_paths(results)
