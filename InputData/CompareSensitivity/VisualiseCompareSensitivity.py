"""
Visualises the scenario comparison.

Produces a figure like the individual scenarios but comparing different scenarios with one value each
 - box and whisker plot for time to first community exposure
 - line (95% CI) plot with community infection proportion
 - upset plots for transmissions between agents
"""
import matplotlib.pyplot as plt
import pandas as pd

from support_functions import get_output_data_dir
from InputData.scenario_constants import NUM_ITERATIONS
from VisualiseResults import visualise_steps_to_spillover, visualise_community_infectious_proportion
from InputData.CompareSensitivity.CompareSensitivity_BulkRunner import PARAM_VALUES_DICT


def main():
    scenario_name = "CompareSensitivity"

    print('Visualising scenario: {}'.format(scenario_name))

    figure, axs = plt.subplots(len(PARAM_VALUES_DICT), 2, layout='constrained')
    figure.set_figwidth(8)
    figure.set_figheight(11)

    title_font_size = 12

    for num, (param, value_list) in enumerate(PARAM_VALUES_DICT.items()):
        print("{}".format(param))
        scenario_df = pd.read_csv(get_output_data_dir(scenario_name) / '{}-{}_data-{}.csv'.format(scenario_name,
                                                                                                  param,
                                                                                                  NUM_ITERATIONS))

        print("  steps to spillover boxplot")
        ax = axs[num][0]
        visualise_steps_to_spillover(ax, scenario_name, scenario_df, param, value_list)
        ax.set_title(param, fontsize=title_font_size, weight='bold')

        print("  community infection lineplot")
        ax = axs[num][1]
        visualise_community_infectious_proportion(ax, scenario_name, scenario_df, param)
        ax.set_title(param, fontsize=title_font_size, weight='bold')

        print()

    plt.savefig(get_output_data_dir(scenario_name) / f'{scenario_name}-all.tiff', dpi=500)
    plt.savefig(get_output_data_dir(scenario_name) / f'{scenario_name}-all.png')
    plt.close()

if __name__ == "__main__":
    main()
