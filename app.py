import networkx.exception
import solara
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from mesa.visualization import (
    Slider,
    SolaraViz,
    make_plot_component,
    make_space_component,
)
from mesa.experimental.devs import ABMSimulator
from mesa.visualization.utils import update_counter
import networkx as nx

from Models.PeopleAgents import PersonAgent
from Models.LocationAgents import DairyFarmAgent, HospitalAgent, TruckAgent
from Models.MainModel import MainModel
from constants import DiseaseState, HospitalDepartment, PersonRole, DEFAULT_CATTLE_INFECT_CATTLE_PROB, \
    DEFAULT_HUMAN_INFECT_CATTLE_PROB, DEFAULT_HUMAN_INFECT_HUMAN_PROB, DEFAULT_CATTLE_INFECT_HUMAN_PROB


def vet_location_portrayal(agent):
    if agent is None:
        return

    portrayal = {'size': 30, 'linewidths': 1}

    if agent.disease_state == DiseaseState.INFECTIOUS:
        portrayal['edgecolors'] = 'xkcd:red'
    elif agent.disease_state == DiseaseState.RECOVERED:
        portrayal['edgecolors'] = 'xkcd:black'
    elif agent.disease_state == DiseaseState.EXPOSED:
        portrayal['edgecolors'] = 'xkcd:mustard yellow'
    else:  # susceptible
        portrayal['edgecolors'] = 'xkcd:grey'

    # marker and size by type
    if isinstance(agent, PersonAgent):
        portrayal['linewidths'] = 1
        portrayal['marker'] = 'o'
        portrayal['zorder'] = 3

        if agent.role == PersonRole.FARMER:
            portrayal['color'] = 'xkcd:brown'
            portrayal['zorder'] = 2
            portrayal['size'] = 10
        elif agent.role == PersonRole.FARM_SERVICES_CLINICIAN:
            portrayal['color'] = 'xkcd:light brown'
        elif agent.role == PersonRole.FARM_SERVICES_STUDENT:
            portrayal['color'] = 'xkcd:beige'
        else:
            portrayal['color'] = 'xkcd:green'

    elif isinstance(agent, HospitalAgent):
        # fixed agents for the hospital areas
        portrayal['marker'] = 's'
        portrayal['size'] = 60
        if agent.department == HospitalDepartment.FARM_SERVICES:
            portrayal['color'] = 'xkcd:peach'
        elif agent.department == HospitalDepartment.LARGE_ANIMAL:
            portrayal['color'] = 'xkcd:eggshell'
        elif agent.department == HospitalDepartment.SMALL_ANIMAL:
            portrayal['color'] = 'xkcd:ice blue'
        elif agent.department == HospitalDepartment.COMMON:
            portrayal['color'] = 'xkcd:light grey'
    elif isinstance(agent, DairyFarmAgent):  # farm
        portrayal['marker'] = 's'
        portrayal['size'] = 100

        # disease state
        if agent.infection_level > 0:
            portrayal['color'] = 'xkcd:light pink'
        else:
            portrayal['color'] = 'xkcd:light green'
    elif isinstance(agent, TruckAgent):
        portrayal['marker'] = 's'
        portrayal['size'] = 40
        portrayal['color'] = 'xkcd:light brown'

    return portrayal


def post_process_space(ax):
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])


space_component = make_space_component(
    vet_location_portrayal, draw_grid=False, post_process=post_process_space
)


def post_process_people_lineplot(ax):
    ax.set_title("SEIR counts for people agents")
    # ax.set_ylim(ymin=-1, ymax=140)
    ax.set_ylabel("Num. people agents")
    # ax.legend(bbox_to_anchor=(1.05, 1.0), loc="upper left")


person_infection_plot = make_plot_component(
    {'People_num_SUSCEPTIBLE': "xkcd:green",
     "People_num_EXPOSED": "xkcd:mustard yellow",
     "People_num_INFECTIOUS": "xkcd:red",
     "People_num_RECOVERED": "xkcd:black"},
    post_process=post_process_people_lineplot,
)


def post_process_community_lineplot(ax):
    ax.set_title("SEIR counts for the Community")
    # ax.set_ylim(ymin=-1000, ymax=201000)
    ax.set_ylabel("Num. community members")


community_infection_plot = make_plot_component(
    {'Community_num_SUSCEPTIBLE': "xkcd:green",
     "Community_num_EXPOSED": "xkcd:mustard yellow",
     "Community_num_INFECTIOUS": "xkcd:red",
     "Community_num_RECOVERED": "xkcd:black"
     },
    post_process=post_process_community_lineplot,
)


@solara.component
def people_infection_plots(model):
    """
    Creates a plot for each type of Person Agent, showing the infection levels on that type.
    """
    fig = Figure()
    axs = fig.subplots(ncols=len(model.person_agent_types), sharex=True, sharey=True)

    # get the infection values to chart
    update_counter.get()  # update

    vars_df = model.datacollector.get_model_vars_dataframe()
    print(vars_df.head())

    axs[0].set_ylim(ymin=0, ymax=1)
    for ax in axs:
        ax.set_ylabel("infected / total")
        ax.set_xlabel('Step')

    solara.FigureMatplotlib(fig)


@solara.component
def dairy_farm_lineplot(model):
    """
    Creates a line plot with all the infection levels of dairy farms
    """
    # set up the chart figure
    fig = Figure()
    ax = fig.subplots()

    # get the infection values to chart
    update_counter.get()  # update
    infection_df = model.datacollector.get_agenttype_vars_dataframe(DairyFarmAgent)

    max_step = max(infection_df.index.get_level_values(0))
    infection_df.reset_index(inplace=True)
    agent_ids = infection_df.AgentID.unique()
    for agent_id in agent_ids:
        agent_history = infection_df.loc[infection_df.AgentID == agent_id]['Infection'].to_list()
        agent_history = [x for x in agent_history]
        # print("  ({}) {}: {}".format(model.steps, agent_id, agent_history))
        ax.plot(list(range(max_step+1)), agent_history)

    ax.set_title("Infection Proportion on Dairy Farms")
    ax.set_ylim(ymin=-0.05, ymax=1.05)
    ax.set_ylabel("infected / total")
    ax.set_xlabel('Step')

    fig.tight_layout()

    solara.FigureMatplotlib(fig)


@solara.component
def num_farm_visits_per_day_plot(model):
    update_counter.get()  # update
    visit_list = []
    for step_num, visits in model.farm_visits_by_vets.items():
        day = model.get_day_from_steps(step_num)
        num_visits = len(visits)

        visit_list += [day] * num_visits

    # set up the chart figure
    fig = Figure()
    ax = fig.subplots()

    counts = np.bincount(visit_list)
    max_x = 1 if len(visit_list) == 0 else max(visit_list) + 1
    ax.bar(range(max_x), counts, width=1, align='center')
    ax.set(xticks=range(max_x), xlim=[-1, max_x])

    # ax.hist(visit_list, range=[0, max_x])
    ax.set_ylim(ymin=0, ymax=10.5)

    # # draw rectangles to mark weekends
    # for d in range(5, max_x, 7):
    #     ax.add_patch(patches.Rectangle(
    #         xy=(d - .5, 0), width=2, height=6, color='lightgrey', fill=True, zorder=0
    #     ))

    ax.set_title("Number of farm visits each day by FS vets")
    ax.set_ylabel('# of farm visits per day')
    ax.set_xlabel('Day')

    solara.FigureMatplotlib(fig)


X_MULT = 20
Y_INC = 1


def get_pos_dict_for_node(network, node, current_x, current_y, visited):
    # print('{}: {}'.format(node, network.successors(node)))
    total_y_span = 1
    current_x += 2
    # current_x = network.nodes[node]['step'] * X_MULT
    current_pos_dict = {node: (current_x, current_y)}
    for adj_node in network.successors(node):
        if adj_node not in visited:
            visited.append(adj_node)
            adj_dict, y_span = get_pos_dict_for_node(network, adj_node, current_x, current_y, visited)
            current_y += y_span * Y_INC
            total_y_span += y_span * Y_INC

            current_pos_dict.update(adj_dict)

    return current_pos_dict, total_y_span


@solara.component
def infection_network(model):
    update_counter.get()

    fig = Figure()
    ax = fig.subplots()

    options = {
        "font_size": 10,
        "node_size": 700,
        "node_color": "white",
        "edgecolors": "black",
        "linewidths": 2,
        "width": 2,
        'connectionstyle': "arc3,rad=0.1"
    }

    pos_dict = {}
    current_y = 0
    for source_node in model.infection_network.source_nodes:
        source_node_pos_dict, y_span = get_pos_dict_for_node(model.infection_network.infection_graph,
                                                             source_node, 0, current_y, [])
        pos_dict.update(source_node_pos_dict)
        current_y += y_span

    max_x = 0
    max_y = 0
    for x, y in pos_dict.values():
        max_x = max(x, max_x)
        max_y = max(y, max_y)
    pos_dict['C'] = (max_x+2, max_y // 2)

    try:
        nx.draw_networkx(model.infection_network.infection_graph, pos_dict, ax=ax, **options)
    except networkx.exception.NetworkXException as e:
        node_str = e.__str__().split()[1].strip("'")
        print("successors: {}".format(list(model.infection_network.infection_graph.successors(node_str))))
        print("predecessors: {}".format(list(model.infection_network.infection_graph.predecessors(node_str))))
        raise e

    # Set margins for the axes so that nodes aren't clipped
    ax = plt.gca()
    ax.margins(0.20)
    plt.axis("off")

    solara.FigureMatplotlib(fig)


model_params = {
    'seed': {
        'type': 'InputText', 'value': 42, 'label': 'Random Seed'
    },
    'is_stop_community_infection': {
        'type': 'Checkbox', 'value': True, 'label': 'Stop on community infection'
    },
    'is_quarantine_farmer': {
        'type': 'Checkbox', 'value': True, 'label': 'Quarantine farmers after infection'
    },
    'cattle_infect_cattle_prob': Slider(min=0, max=1, step=.01, value=DEFAULT_CATTLE_INFECT_CATTLE_PROB,
                                        label='Prob. cow -> cow'),
    'human_infect_human_prob': Slider(min=0, max=1, step=.01, value=DEFAULT_HUMAN_INFECT_HUMAN_PROB,
                                      label='Prob. person -> person'),
    'human_infect_cattle_prob': Slider(min=0, max=1, step=.01, value=DEFAULT_HUMAN_INFECT_CATTLE_PROB,
                                       label='Prob. person -> cow'),
    'cattle_infect_human_prob': Slider(min=0, max=1, step=.01, value=DEFAULT_CATTLE_INFECT_HUMAN_PROB,
                                       label='Prob. cow -> person'),
}


simulator = ABMSimulator()
main_model = MainModel(simulator=simulator, is_stop_community_infection=True, is_quarantine_farmer=True)

page = SolaraViz(
    main_model,
    components=[space_component, infection_network, person_infection_plot, community_infection_plot],
    # components=[space_component, dairy_farm_lineplot, infection_path_vis, community_plot
    #             fs_vet_plot, fs_tech_plot, large_vet_plot, small_vet_plot, float_staff_plot, farmer_plot],
    model_params=model_params,
    name="Avian Influenza in the Veterinary Teaching Hospital",
    simulator=simulator,
)
page  # noqa