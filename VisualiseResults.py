import seaborn as sns
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import networkx as nx

from support_functions import get_day_from_steps, get_output_data_dir

matplotlib.use('TkAgg')

X_MULT = 20
Y_INC = 15


def get_pos_dict_for_node(network, node, current_y, visited):
    # print('{}: {}'.format(node, network.successors(node)))
    total_y_span = 1
    current_x = network.nodes[node]['step'] * X_MULT
    current_pos_dict = {node: (current_x, current_y)}
    for adj_node in network.successors(node):
        if adj_node not in visited:
            visited.append(adj_node)
            adj_dict, y_span = get_pos_dict_for_node(network, adj_node, current_y, visited)
            current_y += y_span * Y_INC
            total_y_span += y_span * Y_INC

            current_pos_dict.update(adj_dict)

    return current_pos_dict, total_y_span


def visualise_paths(infection_network):
    """

    """

    options = {
        "font_size": 10,
        "node_size": 10,
        "node_color": "black",
        "edgecolors": "black",
        "linewidths": 1,
        "width": 1,
        'with_labels': False,
    }

    sns.set_theme(rc={'figure.figsize': (10, 10)})
    sns.set_style('whitegrid')
    sns.set_context("paper")

    # Set margins for the axes so that nodes aren't clipped
    ax = plt.gca()
    # ax.margins(0.20)
    plt.axis("off")

    # pos_dict = {}
    # current_y = 0
    # for source_node in infection_network.source_nodes:
    #     source_node_pos_dict, y_span = get_pos_dict_for_node(infection_network.infection_graph,
    #                                                          source_node, current_y, [])
    #     pos_dict.update(source_node_pos_dict)
    #     current_y += y_span
    # pos_dict = nx.nx_agraph.graphviz_layout(infection_network.infection_graph, prog="twopi")
    # nx.draw_networkx(infection_network.infection_graph, pos_dict)  # , **options)
    graph = infection_network.infection_graph

    nx.draw(graph, ax=ax,
            pos=nx.bfs_layout(graph, start='F9'),
            **options)

    ax.get_figure().savefig(get_output_data_dir() / 'infection_network.png')

    plt.close()


def visualise_visit_counts(visit_dict, days):
    """

    :param days:
    :type days:
    :param visit_dict:
    :type visit_dict:
    """
    # generate a histogram list from the visit dictionary
    hist_list = []
    for step, visit_list in visit_dict.items():
        day = get_day_from_steps(step)
        hist_list.append(day)

    sns.set_theme(rc={'figure.figsize': (10, 5)})
    sns.set_style('whitegrid')
    sns.set_context("paper")

    hist = sns.histplot(hist_list, discrete=True)
    max_x = days
    # hist.bar(range(max_x), hist_list, width=1, align='center')
    hist.set(xticks=range(1, max_x, 5), xlim=[-1, max_x])
    hist.set_ylim(ymin=0, ymax=5.5)
    # hist.set_xlim(xmin=1, xmax=days)

    # draw rectangles to mark weekends
    for d in range(5, max_x, 7):
        hist.add_patch(patches.Rectangle(
            xy=(d - .5, 0), width=2, height=6, color='lightgrey', fill=True, zorder=0
        ))

    hist.set_title("Number of farm visits each day by FS vets")
    hist.set_ylabel('# of farm visits per day')
    hist.set_xlabel('Day')

    hist.get_figure().savefig(get_output_data_dir() / 'visits_hist.png')

    plt.close()


def write_scenario_summary_graph(scenario_name, scenario_results):
    """
    Writes a graph file in standard format that summarises a multi-trial simulation.

    The output graph is a weighted directed graph. Weights indicate how many times that edge featured in
    an infection path.

    :param scenario_name: Name of the scenario being summarised.
    :type scenario_name: str
    :param scenario_results: All
    :type scenario_results:
    :return:
    :rtype:
    """
    summary_graph = nx.DiGraph()

    # go through the result graph and put the edges in the summary graph
    for result_graph in scenario_results:
        for source, target, edge_num in result_graph.edges:
            # don't include repeated edges from the same iteration
            if edge_num == 0:
                if (source, target) in summary_graph.edges:
                    # edge is already there - increase the weight
                    summary_graph.edges[source, target]['weight'] += 1
                else:
                    # add the new edge with a weight of 1
                    summary_graph.add_edge(source, target, weight=1)

    # write out the summary graph in a standard format
    nx.write_weighted_edgelist(summary_graph, get_output_data_dir() / '{}_edgelist.csv'.format(scenario_name),
                               delimiter=',')


