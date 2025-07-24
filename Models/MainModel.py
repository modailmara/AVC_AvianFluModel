import inspect
import mesa
import math
from mesa.experimental.cell_space import OrthogonalMooreGrid
import pandas as pd

from support_functions import get_input_data_dir
from constants import convert_days_to_steps
from Models.SIRModel import SIRModel
from InfectionPaths import InfectionPaths

import Models
from Models.Agents import HospitalAgent, PersonAgent, FarmerAgent
from Models.FarmAgent import DairyFarmAgent
from constants import FARM_INPUT_FILENAME, Location, DiseaseState, HospitalDepartment, NUM_FARM_SERVICES_VETS, \
    NUM_FARM_SERVICES_TECHS, NUM_FLOATING_STAFF, NUM_LARGE_ANIMAL_VETS, NUM_SMALL_ANIMAL_VETS, \
    HUMAN_INFECT_HUMAN_PROB, HUMAN_INFECT_CATTLE_PROB, CATTLE_INFECT_CATTLE_PROB, CATTLE_INFECT_HUMAN_PROB, \
    WORK_DAY_STEPS, COMMUNITY_STEPS, VET_DAYS_AT_FARM, STEPS_PER_DAY, PEOPLE_INPUT_FILENAME, PersonRole


def number_state(model, disease_state, agent_types=None):
    """
    Get the number of person agents of a type in a model that are in a particular disease state.

    :param model: The model to get the information from
    :type model: MainModel object
    :param disease_state: State of disease to match
    :type disease_state: DiseaseState enum value
    :param agent_types: List of person agent types to count. Defaults to all person agents
    :type agent_types: list of classes

    :return: Count of how many agents of that type are in that disease state
    :rtype: int
    """
    if agent_types is None:
        person_classes = [cls[1] for cls in model.person_agent_types]
    else:
        person_classes = agent_types

    num = 0
    for agent_class in person_classes:
        num += len(model.agents_by_type[agent_class].select(lambda agent: agent.disease_state == disease_state))
    return num


def number_people(model, agent_type=PersonAgent):
    """
    Get the number of person agents in the model

    :param model: The model to get the information from
    :type model: MainModel object
    :param agent_type: The type of agent to count. Default=PersonAgent
    :type agent_type: class

    :return: Count of how many agents of that ty
    :rtype: int
    """
    return len([agent for agent in model.agents if isinstance(agent, agent_type)])


def proportion_vet_infected(model):
    return number_state(model, DiseaseState.INFECTED) / number_people(model)


def number_vet_susceptible(model):
    return number_state(model, DiseaseState.SUSCEPTIBLE) / number_people(model)


def number_vet_recovered(model):
    return number_state(model, DiseaseState.RECOVERED) / number_people(model)


class MainModel(mesa.Model):
    """
    The model that coordinates the agents and environment for a Hub and Spoke model of Avian Influenza.
    """

    def __init__(self, seed=None, simulator=None,
                 human_infect_human_prob=HUMAN_INFECT_HUMAN_PROB,
                 human_infect_cattle_prob=HUMAN_INFECT_CATTLE_PROB,
                 cattle_infect_human_prob=CATTLE_INFECT_HUMAN_PROB,
                 cattle_infect_cattle_prob=CATTLE_INFECT_CATTLE_PROB,
                 ):
        super().__init__(seed=seed)
        if simulator is not None:
            self.simulator = simulator
            self.simulator.setup(self)

        # store a list of all the Person agent types - seems this gets used a bit
        self.person_agent_types = [cls for cls in inspect.getmembers(Models.Agents, inspect.isclass)
                                   if issubclass(cls[1], PersonAgent) and cls[1] != PersonAgent]

        self.width = 20
        self.height = 20

        # Create grid using experimental cell space
        self.grid = OrthogonalMooreGrid(
            [self.height, self.width],
            torus=False,
            capacity=math.inf,
            random=self.random,
        )

        # queue to manage farm requests for vets
        self.farm_request_queue = []
        self.available_farm_clinicians = []

        self.infection_paths = InfectionPaths()

        # keep references to the different types of locations
        self.hospital_cells = {HospitalDepartment.FARM_SERVICES: [], HospitalDepartment.SMALL_ANIMAL: [],
                               HospitalDepartment.LARGE_ANIMAL: [], HospitalDepartment.COMMON: []}
        self.farm_cells = []

        # --------------------------
        # create the hospital

        hospital_width = 9

        # large animal clinic
        for cell_x in range(hospital_width):
            for cell_y in range(13, 20):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.LARGE_ANIMAL, cell=cell)
                self.hospital_cells[HospitalDepartment.LARGE_ANIMAL].append(cell)
        # add a partial row for where farm services overlaps
        for cell_x in range(4, hospital_width):
            cell_y = 12
            cell = self.grid[cell_x, cell_y]
            HospitalAgent(self, HospitalDepartment.LARGE_ANIMAL, cell=cell)
            self.hospital_cells[HospitalDepartment.LARGE_ANIMAL].append(cell)

        # small animal clinic + ???
        for cell_x in range(hospital_width):
            for cell_y in range(9):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.SMALL_ANIMAL, cell=cell)
                self.hospital_cells[HospitalDepartment.SMALL_ANIMAL].append(cell)
        # extra partial row for where farm services overlaps
        for cell_x in range(4, hospital_width):
            cell_y = 9
            cell = self.grid[cell_x, cell_y]
            HospitalAgent(self, HospitalDepartment.SMALL_ANIMAL, cell=cell)
            self.hospital_cells[HospitalDepartment.SMALL_ANIMAL].append(cell)

        # farm services area
        for cell_x in range(4):
            for cell_y in range(9, 13):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.FARM_SERVICES, cell=cell)
                self.hospital_cells[HospitalDepartment.FARM_SERVICES].append(cell)

        # common area
        for cell_x in range(hospital_width, 12):
            for cell_y in range(6, 10):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.COMMON, cell=cell)
                self.hospital_cells[HospitalDepartment.COMMON].append(cell)

        # ------------------------- end hospital space definition

        # load the farm file to define farms and farmers
        farm_df = pd.read_excel(get_input_data_dir() / FARM_INPUT_FILENAME)
        # add the farm cells, starting top right and every second cell to bottom then left
        cell_x = self.width - 1  # all the way right
        cell_y = 0  # top
        for _, farm_row in farm_df.iterrows():
            cell = self.grid[cell_x, cell_y]
            farm = DairyFarmAgent(self, cell,
                                  farm_row.farm_id, farm_row.herd_size, farm_row.visit_frequency_days,
                                  farm_row.milking_system, farm_row.housing, farm_row.pasture, farm_row.num_infected)
            self.farm_cells.append(cell)

            # one farmer per farm
            FarmerAgent(self, farm)

            # increment the cell coordinates
            cell_y += 2
            if cell_y >= self.height:
                cell_y = 0
                cell_x -= 2

        # load the people file to define hospital locations and staff/clinicians/students
        people_df = pd.read_excel(get_input_data_dir() / PEOPLE_INPUT_FILENAME)
        people_df.columns = people_df.columns.str.lower()
        area_names = [name.split(':')[1].strip()
                      for name in people_df.columns if name.startswith('area:')]

        for _, role_def_row in people_df.iterrows():
            role_name = role_def_row.type.lower().strip()
            person_role = PersonRole(role_name)
            num_role = int(role_def_row.num)

            area_weights = []
            for name in area_names:
                area = HospitalDepartment(name)
                area_weights.append((area, float(role_def_row['area: ' + name])))

            for i in range(num_role):
                PersonAgent(self, "{}_{}".format(person_role, i),
                            cell=None, role=person_role, area_weights=area_weights)
                # person.move()

        self.community_model = SIRModel(self, 'community')

        # add collecters for the people infection trackers
        model_reporters = {
            "Infected": proportion_vet_infected,
            "Susceptible": number_vet_susceptible,
            "Recovered": number_vet_recovered,
            # FarmServicesVet, FarmServicesTechnician, LargeAnimalVet, SmallAnimalVet, FloatingStaff

            "FarmerAgent": lambda model: number_state(model, DiseaseState.INFECTED, [FarmerAgent]) / number_people(model, FarmerAgent),
            "Community": lambda model: model.community_model.proportion_infected,
            # 'paths': lambda model: model.infection_paths._path_dict
        }
        # add in a model reporter for each farm
        agent_reporters = {DairyFarmAgent: {'Infection': 'infection_level'}}

        self.datacollector = mesa.DataCollector(
            model_reporters=model_reporters,
            agenttype_reporters=agent_reporters,
        )
        self.datacollector.collect(self)

    def step(self) -> None:
        """
        Execute one step of the model
        """
        # fill any farm requests for vets
        # available_vets = list(self.agents_by_type[PersonAgent].select(lambda a: a.location == Location.HOSPITAL and
        #                                                                         a.role == PersonRole.FARM_SERVICES_VET))
        # min_vets_farms = min(len(available_vets), len(self.farm_request_queue))
        # for _ in range(min_vets_farms):
        #     farm = self.farm_request_queue.pop(0)
        #     farm_services_vet = available_vets.pop(0)
        #
        #     farm.visit_from_vet(farm_services_vet)
        #     farm_services_vet.visit_farm(farm)

        # manage vets that have finished their visit at a farm and are returning to the hospital
        # vets_at_farms = self.agents_by_type[PersonAgent].select(lambda a: a.location == Location.FARM)
        # for farm_services_vet in vets_at_farms:
        #     if farm_services_vet.steps_at_farm > convert_days_to_steps(VET_DAYS_AT_FARM):
        #         # been there long enough - time to go back to the hospital
        #         farm_services_vet.farm.vet_leaving()
        #         farm_services_vet.leave_farm()

        self.agents.shuffle_do('step')

        self.datacollector.collect(self)

    def request_vet_visit(self, farm):
        """
        A farm needs a vet to visit. Put them at the end of the queue
        :param farm: The farm requesting a vet visit
        :type farm: DairyFarmAgent object
        """
        self.farm_request_queue.append(farm)
