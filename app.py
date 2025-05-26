import solara
from matplotlib.figure import Figure
from mesa.visualization import (
    Slider,
    SolaraViz,
    make_plot_component,
    make_space_component,
)
from mesa.experimental.devs import ABMSimulator
from mesa.visualization.utils import update_counter


from Agents import PersonAgent, HospitalAgent, DairyFarmAgent, FarmServicesVet, FarmServicesTechnician, FloatingStaff, \
    LargeAnimalVet, SmallAnimalVet
from MainModel import MainModel
from constants import FarmVetVisitState, DiseaseState, HospitalDepartment, \
    HUMAN_INFECT_HUMAN_PROB, HUMAN_INFECT_CATTLE_PROB, CATTLE_INFECT_HUMAN_PROB, CATTLE_INFECT_CATTLE_PROB, \
    BIRD_INFECT_COW_PROB


def vet_location_portrayal(agent):
    if agent is None:
        return

    portrayal = {'size': 35, 'edgecolors': 'black', 'linewidths': 0}

    # marker and size by type
    if isinstance(agent, PersonAgent):
        portrayal['linewidths'] = .5
        portrayal['marker'] = 'o'
        portrayal['zorder'] = 2

        if isinstance(agent, FarmServicesVet):
            portrayal['color'] = 'xkcd:brown'
        elif isinstance(agent, FarmServicesTechnician):
            portrayal['color'] = 'xkcd:slate grey'
        elif isinstance(agent, FloatingStaff):
            portrayal['color'] = 'xkcd:apricot'
        elif isinstance(agent, LargeAnimalVet):
            portrayal['color'] = 'xkcd:blue'
        elif isinstance(agent, SmallAnimalVet):
            portrayal['color'] = 'xkcd:drab green'
        else:  # farmer
            portrayal['color'] = 'xkcd:green'

        if agent.disease_state == DiseaseState.INFECTED:
            portrayal['edgecolors'] = 'xkcd:red'
        elif agent.disease_state == DiseaseState.RECOVERED:
            portrayal['edgecolors'] = 'xkcd:black'
        else:  # susceptible
            portrayal['edgecolors'] = 'xkcd:green'

    elif isinstance(agent, HospitalAgent):
        portrayal['marker'] = 's'
        portrayal['size'] = 500
        if agent.department == HospitalDepartment.FARM_SERVICES:
            portrayal['color'] = 'xkcd:light grey'
        elif agent.department == HospitalDepartment.LARGE_ANIMAL:
            portrayal['color'] = 'xkcd:eggshell'
        else:  # small animal
            portrayal['color'] = 'xkcd:ice blue'
    else:  # farm
        portrayal['marker'] = 's'
        portrayal['size'] = 100

        # disease state
        if agent.infection_level > 0:
            portrayal['color'] = 'xkcd:light pink'
        else:
            portrayal['color'] = 'xkcd:light green'

    return portrayal


model_params = {
    # 'seed': {
    #     'type': 'InputText',
    #     'value': 42,
    #     'label': 'Random Seed'
    # },
    'human_infect_human_prob': Slider(
        label='Prob: Person infect Person',
        value=HUMAN_INFECT_HUMAN_PROB,
        min=0,
        max=.5,
        step=.01,
    ),
    'human_infect_cattle_prob': Slider(
        label='Prob: Person infect Cow',
        value=HUMAN_INFECT_CATTLE_PROB,
        min=0,
        max=.5,
        step=.01,
    ),
    'cattle_infect_human_prob': Slider(
        label='Prob: Cow infect Person',
        value=CATTLE_INFECT_HUMAN_PROB,
        min=0,
        max=.5,
        step=.01,
    ),
    'cattle_infect_cattle_prob': Slider(
        label='Prob: Cow infect Cow',
        value=CATTLE_INFECT_CATTLE_PROB,
        min=0,
        max=.5,
        step=.01,
    ),
    'bird_infect_cattle_prob': Slider(
        label='Prob: Bird infect Cow',
        value=BIRD_INFECT_COW_PROB,
        min=0,
        max=.5,
        step=.01,
    ),
}


def post_process_space(ax):
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])

space_component = make_space_component(
    vet_location_portrayal, draw_grid=False, post_process=post_process_space
)


def post_process_vet_staff_lineplot(ax):
    ax.set_title("Infections in Vet Hospital Staff")
    ax.set_ylim(ymin=-0.05, ymax=1.05)
    ax.set_ylabel("Proportion Population")
    # ax.legend(bbox_to_anchor=(1.05, 1.0), loc="upper left")

person_infection_plot = make_plot_component(
    {"Infected": "xkcd:red", "Susceptible": "xkcd:green", "Recovered": "xkcd:black"},
    post_process=post_process_vet_staff_lineplot,
)


def post_process_fs_vet_lineplot(ax):
    post_process_vet_staff_lineplot(ax)
    ax.set_title("Farm Services Vets and Students")


fs_vet_plot = make_plot_component(
    {"FarmServicesVet": "xkcd:red"}, post_process=post_process_fs_vet_lineplot,
)


def post_process_fs_tech_lineplot(ax):
    post_process_vet_staff_lineplot(ax)
    ax.set_title("Farm Services Technician")

fs_tech_plot = make_plot_component(
    {"FarmServicesTechnician": "xkcd:red"}, post_process=post_process_fs_tech_lineplot,
)


def post_process_large_vet_lineplot(ax):
    ax.set_title("Large Animal Vet")
    post_process_vet_staff_lineplot(ax)

large_vet_plot = make_plot_component(
    {"LargeAnimalVet": "xkcd:red"}, post_process=post_process_large_vet_lineplot,
)


def post_process_small_vet_lineplot(ax):
    ax.set_title("Small Animal Vet")
    post_process_vet_staff_lineplot(ax)

small_vet_plot = make_plot_component(
    {"SmallAnimalVet": "xkcd:red"}, post_process=post_process_small_vet_lineplot,
)


def post_process_floating_staff_lineplot(ax):
    ax.set_title("Floating Staff")
    post_process_vet_staff_lineplot(ax)

float_staff_plot = make_plot_component(
    {"FloatingStaff": "xkcd:red"}, post_process=post_process_floating_staff_lineplot,
)


def post_process_community_lineplot(ax):
    post_process_vet_staff_lineplot(ax)
    ax.set_title("Community Infection Proportion")

community_plot = make_plot_component(
    {"Community": "xkcd:red"}, post_process=post_process_community_lineplot,
)


def post_process_farmer_lineplot(ax):
    post_process_vet_staff_lineplot(ax)
    ax.set_title("Farmer")

farmer_plot = make_plot_component(
    {"Farmer": "xkcd:red"}, post_process=post_process_farmer_lineplot,
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
        ax.plot(list(range(max_step+1)), agent_history)

    ax.set_title("Infection Proportion on Dairy Farms")
    ax.set_ylim(ymin=0, ymax=1)
    ax.set_ylabel("infected / total")
    ax.set_xlabel('Step')

    solara.FigureMatplotlib(fig)


@solara.component
def infection_path_vis(model):
    # get the path labels and the counts
    update_counter.get()
    path_items = model.infection_paths.get_paths_counts()
    # print(path_items)
    if len(path_items) > 0:
        paths, counts = zip(*path_items)
    else:
        paths, counts = ([], [])
    paths = [('-'.join(names),) for names in paths]
    # print(paths)
    all_paths = []
    for i in range(len(paths)):
        all_paths += paths[i] * counts[i]
    # print(all_paths)
    # make a histogram plot of the paths vs count
    fig = Figure()
    ax = fig.subplots()

    ax.hist(all_paths, orientation='horizontal')

    ax.set_title("Counts of Infection Paths")
    ax.set_ylabel("# times infection path occurred")
    ax.set_xlabel('')

    solara.FigureMatplotlib(fig)


simulator = ABMSimulator()
main_model = MainModel(simulator=simulator)

page = SolaraViz(
    main_model,
    components=[space_component, dairy_farm_lineplot, infection_path_vis, community_plot],
    # components=[space_component, dairy_farm_lineplot,
    #             fs_vet_plot, fs_tech_plot, large_vet_plot, small_vet_plot, float_staff_plot, farmer_plot],
    model_params=model_params,
    name="Avian Flu in the Veterinary Teaching Hospital",
    simulator=simulator,
)
page  # noqa