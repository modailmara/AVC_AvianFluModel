import seaborn as sns
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import networkx as nx
import upsetplot

from support_functions import get_output_data_dir
from InputData.scenario_constants import NUM_ITERATIONS
from constants import PersonRole

matplotlib.use('TkAgg')

STEPS_PER_DAY = 24


def set_seaborn_context():
    sns.set_theme(rc={'figure.figsize': (10, 5)})
    sns.set_style('whitegrid')
    sns.set_context("paper")


def _convert_person_role_list_to_string(person_role_list):
    """
    Converts a stringified list of PersonRole to a string of PersonRole names separated by '-'
    Example: input "[<PersonRole.FARMER: 'f'>, <PersonRole.FARM_SERVICES_CLINICIAN: 'FSc'>]"
                   -> "FARMER-FARM_SERVICES_CLINICIAN"
    Input can be "[None]", then output is "None"

    :param person_role_list: Stringified list of PersonRole or "[None]"
    :type person_role_list: str
    :return: string of short PersonRole codes separated by '-', or 'None'
    :rtype: str
    """
    if '[none]' in person_role_list.strip().lower():
        return 'None'
    else:
        name_list = []
        for role_str in [r.strip() for r in person_role_list[1:-1].split(',')]:
            # role_str is "<PersonRole.ROLE: 'short_code'>"
            role_name = role_str[1:-1].split(':')[0]
            # role_name is "PersonRole.ROLE"
            role_name = role_name.split('.')[1]
            name_list.append(role_name)
        names = '-'.join(name_list)
        # print('  {} from {}'.format(short_codes, person_role_list))
        return names


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
    spillover_result_df['Days to Community Spillover'] = spillover_result_df.steps_to_community / STEPS_PER_DAY

    plot = sns.boxplot(spillover_result_df, x=var_name, y='Days to Community Spillover', order=var_values)
    plt.ylim(0, np.nanmax(spillover_result_df['Days to Community Spillover']) + 1)

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

    # make a day column as it's easier to read
    result_df['Days'] = result_df.Step / STEPS_PER_DAY

    # make a line plot comparing outcomes
    plot = sns.lineplot(result_df, x='Days', y='Community_prop_INFECTIOUS', hue=var_name, palette='colorblind')

    plt.ylim(-0.05, 1.05)

    plot.get_figure().savefig(get_output_data_dir(scenario_name) / '{}-prop_infectious-line.png'.format(scenario_name))

    plt.close()


def get_node_pos(nx_graph, current_node, current_x=0, y_min=0, visited_nodes=[]):
    """
    Returns a dictionary with nodes as keys and position tuples as
    :param nx_graph:
    :type nx_graph:
    :param start_nodes:
    :type start_nodes:
    :param visited_nodes:
    :type visited_nodes:
    :return:
    :rtype:
    """
    positions = {}
    visited_nodes.append(current_node)
    unvisited_successors = [n for n in nx_graph.successors(current_node) if n not in visited_nodes]
    if len(unvisited_successors) == 0:
        # this is a leaf node
        y_span = 1
        positions[current_node] = (current_x, y_min)
    else:
        # not a leaf - recurse through subtrees
        y_span = 0
        for node in unvisited_successors:
            sub_y_span, subtree_pos = get_node_pos(nx_graph, node, current_x+1, y_min+y_span, visited_nodes)
            positions.update(subtree_pos)

            y_span += sub_y_span

        # position the current node
        positions[current_node] = (current_x, (y_span + y_min) / 2)

    return y_span, positions


def visualise_infection_network(scenario_name, result_type, var_value):
    print("    {}_{}".format(result_type, var_value))
    # get the dir with the edgelist files
    edgelist_dir = get_output_data_dir(scenario_name) / 'working'
    # read in all the iteration result edge lists and put them together
    edge_df_list = []
    for edgelist_filepath in [edgelist_dir / filename for filename in list(edgelist_dir.glob('{}::{}::{}::*.csv'.format(
            scenario_name, result_type, var_value)))]:
        # each file is a single iteration
        iteration_df = pd.read_csv(edgelist_filepath, names=['source', 'target', 'weight', 'step'])

        edge_df_list.append(iteration_df)
    edgelist_df = pd.concat(edge_df_list)

    # simplify nodes into types
    edgelist_df['source'] = edgelist_df['source'].apply(lambda x: x.split('_')[0])
    edgelist_df['target'] = edgelist_df['target'].apply(lambda x: x.split('_')[0])

    # group by (source, target), mean weights and min of step
    edgelist_group = edgelist_df.groupby(by=['source', 'target'])
    edgelist_df = edgelist_group.agg({'weight': 'mean', 'step': 'min'}).reset_index()

    # write the edgelist to a csv file
    filename = '{}::{}::{}::edgelist.csv'.format(scenario_name, result_type, var_value)
    edgelist_df.to_csv(get_output_data_dir(scenario_name) / filename, index=False)

    # convert to a network graph
    infection_graph = nx.from_pandas_edgelist(edgelist_df, source='source', target='target', edge_attr=True,
                                              create_using=nx.DiGraph)

    # Draw the graph nodes
    # node_pos = nx.spring_layout(infection_graph, seed=63, k=10)
    # get the source nodes (infected farms)
    if 'complete' in filename:
        # for debugging
        print(filename)
    y_span, node_pos = get_node_pos(infection_graph, 'h', current_x=0, y_min=0, visited_nodes=[])
    # position community node to the right, halfway between top and bottom
    node_pos['C'] = (max(node_pos.values(), key=lambda x: x[0])[0] + 2, y_span / 2)

    nx.draw_networkx_nodes(infection_graph, node_pos, node_size=700)

    # sort weights and put them in bands for drawing
    sorted_weights = sorted(edgelist_df.weight.unique())
    num_bands = 10
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
    # nx.draw_networkx_edge_labels(infection_graph, node_pos, edge_labels)

    ax = plt.gca()
    ax.margins(0.08)
    plt.axis("off")
    # plt.tight_layout()

    ax.get_figure().savefig(get_output_data_dir(scenario_name) / '{}::{}::{}::network.png'.format(scenario_name,
                                                                                                  result_type,
                                                                                                  var_value))

    plt.close()


def visualise_infection_upset(scenario_name, result_type, var_value, axis=None):
    # var_value = 'None' if var_value == 'none' else var_value
    var_value = var_value.replace(', ', ',')
    print("    {}_{}".format(result_type, var_value))

    # get the dir with the edgelist files
    edgelist_dir = get_output_data_dir(scenario_name) / 'working'
    # read in all the iteration result edge lists and put them together
    edge_df_list = []
    print("scenario={}\nresult_type={}\nvar_value={}".format(scenario_name, result_type, var_value))
    for edgelist_filepath in [edgelist_dir / filename
                              for filename in list(edgelist_dir.glob('{}::{}::{}::*.csv'.format(scenario_name,
                                                                                                result_type,
                                                                                                var_value)))]:
        # each file is a single iteration
        iteration_df = pd.read_csv(edgelist_filepath, names=['from_node', 'to_node', 'weight', 'step'])

        # simplify nodes into types
        iteration_df['from_node'] = iteration_df['from_node'].apply(lambda x: x.split('_')[0])
        iteration_df['to_node'] = iteration_df['to_node'].apply(lambda x: x.split('_')[0])

        # upset doesn't preserve direction so sort standard (alphabetically)
        iteration_df['source'] = iteration_df.apply(lambda r: sorted([r.from_node, r.to_node])[0], axis=1)
        iteration_df['target'] = iteration_df.apply(lambda r: sorted([r.from_node, r.to_node])[-1], axis=1)

        # add together any repeats
        iteration_group = iteration_df.groupby(by=['source', 'target'])
        iteration_df = iteration_group.agg({'weight': 'sum', 'step': 'min'}).reset_index()

        edge_df_list.append(iteration_df)
    edgelist_df = pd.concat(edge_df_list)

    # remove the h <-> F row
    edgelist_df = edgelist_df[~((edgelist_df.source == 'FA') & (edgelist_df.target == 'h'))]

    # get the mean number of node connections
    edgelist_group = edgelist_df.groupby(by=['source', 'target'])
    edgelist_df = edgelist_group.agg({'weight': 'mean', 'step': 'min'}).reset_index()

    edgelist_df.sort_values(by='weight', ascending=False, inplace=True)

    num_edges = 15
    short_edgelist_df = edgelist_df[:num_edges]

    memberships = []
    counts = []
    for _, row in short_edgelist_df.iterrows():
        item = [row.source, row.target]
        item.sort()
        try:
            index = memberships.index(item)

            # link is already in the memberships so add the weight to the count
            counts[index] += row.weight
        except ValueError:
            # new item - append to both lists
            memberships.append(item)
            counts.append(row.weight)
    upset_df = upsetplot.from_memberships(memberships, counts)

    plot_result = upsetplot.plot(upset_df, sort_by='cardinality', totals_plot_elements=0, fig=axis)

    subtext = """C=community, FA=farm, FL=floating, FS=farm services, LA=large animal, SA=small animal. 
    s=staff, u=student, c=clinician, t=technician, f=farmer, h=herd. 
    Combinations, e.g. FSu=farm services student"""

    plot_result['shading'].set_xlabel(subtext, multialignment='left')

    plot_result['intersections'].set_ylabel('Pathogen transmissions')
    plot_result['intersections'].set_ylim(0, 300)

    plt.savefig(get_output_data_dir(scenario_name) / '{}::{}::{}::upset.png'.format(scenario_name,
                                                                                    result_type,
                                                                                    var_value))
    plt.close()


SCENARIOS_1 = [
    ('AnimalIntroduction', 'num_infected_farms', [1, 5, 10, 15, 19]),
    ('HospitalCleaning', 'hospital_cleaning', ['none', 'daily']),
    ('PeopleMixing', 'people_sheet', ['default', 'no_common', 'dept_only']),

    ('TransmissionCowCow', 'cattle_infect_cattle_prob', [i / 10 for i in range(1, 10, 4)]),
    ('TransmissionPersonPerson', 'human_infect_human_prob', [i / 10 for i in range(1, 10, 4)]),
    ('TruckCleaning', 'truck_cleaning', ['none', 'daily', 'visit']),

]
# [[None], [PersonRole.FARM_SERVICES_STUDENT],
# [PersonRole.FARM_SERVICES_STUDENT, PersonRole.FARM_SERVICES_CLINICIAN]])

SCENARIOS_2 = [
    # ('QuarantineFarms', 'is_quarantine_farm', [False, True]),
    # ('Quarantine+TClean', 'truck_cleaning', ['none', 'daily', 'visit']),
    # ('Vaccination', 'vacc_roles', ['none', 'farm services clinician',
    #                                'farm services student, farm services clinician']),
    ('Quarantine+Vacc', 'vacc_roles', ['none', 'farm services clinician',
                                       'farm services student, farm services clinician']),
    # ('Quarantine+Vacc+TClean', 'truck_cleaning', ['none', 'daily', 'visit']),
]


if __name__ == "__main__":
    for scenario_name, var_name, var_values in SCENARIOS_2:
        print(scenario_name)
        print('  reading data')
        scenario_df = pd.read_csv(get_output_data_dir(scenario_name) / '{}_data-{}.csv'.format(scenario_name,
                                                                                               NUM_ITERATIONS))
        print('  plotting number of steps to spillover')
        # plt.subplot(3, 1, 1)
        visualise_steps_to_spillover(scenario_name, scenario_df, var_name, var_values)

        print('  plotting community infectious proportion')
        # plt.subplot(3, 1, 2)
        visualise_community_infectious_proportion(scenario_name, scenario_df, var_name)

        print('  drawing the infection networks and upset plots')
        for num, var_value in enumerate(var_values):
            # visualise_infection_network(scenario_name, 'spillover', var_value)
            # visualise_infection_network(scenario_name, 'complete', var_value)
            # visualise_infection_upset(scenario_name, 'spillover', var_value)
            # ax = plt.subplot(3, len(var_values), 2 + len(var_values) + num)
            visualise_infection_upset(scenario_name, 'complete', var_value)

        # plt.savefig(get_output_data_dir(scenario_name) / f'{scenario_name}-all.png')
        plt.close()
