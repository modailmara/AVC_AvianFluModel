import seaborn as sns
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import networkx as nx

from support_functions import get_output_data_dir
from InputData.scenario_constants import NUM_ITERATIONS, STEPS

matplotlib.use('TkAgg')


def set_seaborn_context():
    sns.set_theme(rc={'figure.figsize': (10, 5)})
    sns.set_style('whitegrid')
    sns.set_context("paper")


def visualise_steps_to_spillover(scenario_name, result_df, var_name, var_values):
    """
    Draws and saves a boxplot of number of steps to first community spillover.

    :param scenario_name:
    :type scenario_name:
    :param result_df:
    :type result_df:
    :param var_name:
    :type var_name:
    :param var_values:
    :type var_values:

    """
    set_seaborn_context()

    # restrict results to just one line per iteration, var_name pair
    result_group = result_df.groupby(by=['iteration', var_name])
    spillover_result_df = result_group['steps_to_community'].aggregate('max').reset_index()
    # print('sr_df ({}):\n{}'.format(spillover_result_df.shape, spillover_result_df))

    plot = sns.boxplot(spillover_result_df, x=var_name, y='steps_to_community', order=var_values)
    plt.ylim(0, np.nanmax(result_df.steps_to_community) + 10)

    plot.get_figure().savefig(get_output_data_dir(scenario_name) / '{}-spillover_steps-box.png'.format(scenario_name))

    plt.close()


def visualise_community_infectious_proportion(scenario_name, result_df, var_name):
    """

    :param scenario_name:
    :type scenario_name:
    :param result_df:
    :type result_df:
    :param var_name:
    :type var_name:
    :return:
    :rtype:
    """
    set_seaborn_context()

    # make a column with the sum of all community numbers
    community_cols = ['Community_num_SUSCEPTIBLE', 'Community_num_EXPOSED', 'Community_num_INFECTIOUS',
                      'Community_num_RECOVERED']
    result_df['Community_num_TOTAL'] = result_df[community_cols].sum(axis=1)
    # make a column with the proportion of infectious community members
    result_df['Community_prop_INFECTIOUS'] = result_df['Community_num_INFECTIOUS'] / result_df['Community_num_TOTAL']

    # make a line plot comparing outcomes
    plot = sns.lineplot(result_df, x='Step', y='Community_prop_INFECTIOUS', hue=var_name)

    plot.get_figure().savefig(get_output_data_dir(scenario_name) / '{}-prop_infectious-line.png'.format(scenario_name))

    plt.close()


def visualise_infection_network(scenario_name, result_type, var_value):
    print("    {}_{}".format(result_type, var_value))
    # get the dir with the edgelist files
    edgelist_dir = get_output_data_dir(scenario_name) / 'working'
    # read in all the iteration result edge lists and put them together
    edge_df_list = []
    for edgelist_filepath in [edgelist_dir / filename for filename in list(edgelist_dir.glob('{}_{}_{}_*.csv'.format(
            scenario_name, result_type, var_value)))]:
        edge_df_list.append(pd.read_csv(edgelist_filepath, names=['source', 'target', 'weight', 'step']))
    edgelist_df = pd.concat(edge_df_list)

    # simplify nodes into types
    edgelist_df['source'] = edgelist_df['source'].apply(lambda x: x.split('_')[0])
    edgelist_df['target'] = edgelist_df['target'].apply(lambda x: x.split('_')[0])

    # group by (source, target), add weights and min of step
    edgelist_group = edgelist_df.groupby(by=['source', 'target'])
    edgelist_df = edgelist_group.agg({'weight': 'sum', 'step': 'min'}).reset_index()

    # convert to a network graph
    infection_graph = nx.from_pandas_edgelist(edgelist_df, source='source', target='target', edge_attr=True,
                                              create_using=nx.DiGraph)

    # Draw the graph nodes
    # node_pos = nx.circular_layout(infection_graph)
    node_pos = nx.spring_layout(infection_graph, seed=63, k=10)

    nx.draw_networkx_nodes(infection_graph, node_pos, node_size=700)

    # sort weights and put them in bands for drawing
    sorted_weights = sorted(edgelist_df.weight.unique())
    num_bands = 5
    band_size = sorted_weights[-1] / num_bands
    edge_list_list = []
    for i in range(num_bands):
        min_weight = i * band_size
        max_weight = (i+1) * band_size
        edge_list = [(u, v) for (u, v, d) in infection_graph.edges(data=True)
                     if min_weight < d['weight'] <= max_weight]
        edge_list_list.append(edge_list)

    # draw the edges
    edge_width = 2
    edge_inc = 2
    for edge_list in edge_list_list:
        nx.draw_networkx_edges(infection_graph, node_pos, edgelist=edge_list, width=edge_width,
                               connectionstyle="arc3,rad=0.1")
        edge_width += edge_inc

    nx.draw_networkx_labels(infection_graph, node_pos, font_size=10, font_family='sans-serif')
    edge_labels = nx.get_edge_attributes(infection_graph, 'weight')
    nx.draw_networkx_edge_labels(infection_graph, node_pos, edge_labels)

    ax = plt.gca()
    ax.margins(0.08)
    plt.axis("off")
    # plt.tight_layout()

    ax.get_figure().savefig(get_output_data_dir(scenario_name) / '{}_{}_{}_network.png'.format(scenario_name,
                                                                                               result_type,
                                                                                               var_value))

SCENARIOS = [
    # ('QuarantineFarmers', 'is_quarantine_farmer', [False, True]),
    # ('TransmissionCowCow', 'cattle_infect_cattle_prob', [i / 10 for i in range(1, 10, 2)]),
    # ('TransmissionPersonPerson', 'human_infect_human_prob', [i / 10 for i in range(1, 10, 2)]),
    # ('AnimalIntroduction', 'num_infected_farms', [1, 5, 10, 15, 20]),
    ('PeopleMixing', 'people_sheet', ['default', 'no_common', 'dept_only']),
]

if __name__ == "__main__":
    for scenario_name, var_name, var_values in SCENARIOS:
        print(scenario_name)
        print('  reading data')
        scenario_df = pd.read_csv(get_output_data_dir(scenario_name) / '{}_data-{}.csv'.format(scenario_name,
                                                                                               NUM_ITERATIONS))
        print('  plotting number of steps to spillover')
        visualise_steps_to_spillover(scenario_name, scenario_df, var_name, var_values)
        print('  plotting community infectious proportion')
        visualise_community_infectious_proportion(scenario_name, scenario_df, var_name)
        print('  drawing the infection networks')
        for var_value in var_values:
            visualise_infection_network(scenario_name, 'spillover', var_value)
            visualise_infection_network(scenario_name, 'complete', var_value)

