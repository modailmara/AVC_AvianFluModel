import seaborn as sns
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import networkx as nx

from support_functions import get_day_from_steps

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
        "node_size": 700,
        "node_color": "white",
        "edgecolors": "black",
        "linewidths": 2,
        "width": 2,
    }

    pos_dict = {}
    current_y = 0
    for source_node in infection_network.source_nodes:
        source_node_pos_dict, y_span = get_pos_dict_for_node(infection_network.infection_graph,
                                                             source_node, current_y, [])
        pos_dict.update(source_node_pos_dict)
        current_y += y_span

    nx.draw_networkx(infection_network.infection_graph, pos_dict, **options)

    # Set margins for the axes so that nodes aren't clipped
    ax = plt.gca()
    ax.margins(0.20)
    plt.axis("off")

    ax.get_figure().savefig('./visualisations/infection_network.png')


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
        # if day > len(hist_list)-1:
        #     hist_list += (day - len(hist_list) + 1) * [0]
        # num_visits = len(visit_dict[step])
        #
        # hist_list[day] += num_visits

    sns.set_context("notebook")
    sns.set_theme(rc={'figure.figsize': (10, 5)})

    hist = sns.histplot(hist_list, discrete=True)
    max_x = days
    # hist.bar(range(max_x), hist_list, width=1, align='center')
    hist.set(xticks=range(1, max_x, 5), xlim=[-1, max_x])
    hist.set_ylim(ymin=0, ymax=5.5)
    # hist.set_xlim(xmin=1, xmax=days)

    hist.set_title("Number of farm visits each day by FS vets")
    hist.set_ylabel('# of farm visits per day')
    hist.set_xlabel('Day')

    hist.get_figure().savefig('./visualisations/visits_hist.png')
