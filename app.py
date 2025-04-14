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

    portrayal = {'size': 35}

    # marker and size by type
    if isinstance(agent, PersonAgent):
        if isinstance(agent, FarmServicesVet):
            portrayal['color'] = 'xkcd:light brown'
        elif isinstance(agent, FarmServicesTechnician):
            portrayal['color'] = 'xkcd:slate grey'
        elif isinstance(agent, FloatingStaff):
            portrayal['color'] = 'xkcd:apricot'
        elif isinstance(agent, LargeAnimalVet):
            portrayal['color'] = 'xkcd:blue'
        elif isinstance(agent, SmallAnimalVet):
            portrayal['color'] = 'xkcd:drab green'
        else:
            portrayal['color'] = 'xkcd:green'
        if agent.disease_state == DiseaseState.INFECTED:
            portrayal['color'] = 'xkcd:red'
        # elif agent.disease_state == DiseaseState.RECOVERED:
        #     portrayal['color'] = 'xkcd:black'
        # else:  # susceptible
        #     portrayal['color'] = 'xkcd:green'
        portrayal['marker'] = 'o'
        portrayal['zorder'] = 2
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
        if agent.num_infected_cattle > 0:
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
    'num_infected_farms': Slider(
        label="# infected farms",
        value=0,
        min=0,
        max=20,
        step=1,
    ),
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
    ax.legend(bbox_to_anchor=(1.05, 1.0), loc="upper left")


vet_staff_plot = make_plot_component(
    {"Infected": "xkcd:red", "Susceptible": "xkcd:green", "Recovered": "xkcd:black"},
    post_process=post_process_vet_staff_lineplot,
)


# dairy_farm_lineplot = make_plot_component(
#     {"f1": 'xkcd:blood'},
#     post_process=post_process_dairy_farm_lineplot,
# )
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


simulator = ABMSimulator()
model = MainModel(simulator=simulator)

page = SolaraViz(
    model,
    components=[space_component, vet_staff_plot, dairy_farm_lineplot],
    model_params=model_params,
    name="Hub and Spoke",
    simulator=simulator,
)
page  # noqa