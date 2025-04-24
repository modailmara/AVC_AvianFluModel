import sys
import inspect

import mesa
import math
from mesa.datacollection import DataCollector
from mesa.experimental.cell_space import OrthogonalVonNeumannGrid

import Agents
from Agents import HospitalAgent, DairyFarmAgent, PersonAgent, FarmServicesVet, FarmServicesTechnician, \
    LargeAnimalVet, SmallAnimalVet, FloatingStaff, Farmer
from constants import Location, VET_STEPS_AT_FARM, DiseaseState, HospitalDepartment, NUM_FARM_SERVICES_VETS, \
    NUM_FARM_SERVICES_TECHS, NUM_FLOATING_STAFF, NUM_LARGE_ANIMAL_VETS, NUM_SMALL_ANIMAL_VETS, \
    HUMAN_INFECT_HUMAN_PROB, HUMAN_INFECT_CATTLE_PROB, CATTLE_INFECT_CATTLE_PROB, CATTLE_INFECT_HUMAN_PROB, \
    BIRD_INFECT_COW_PROB


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

    def __init__(self, width=20, height=20, seed=None, simulator=None, num_infected_farms=0,
                 human_infect_human_prob=HUMAN_INFECT_HUMAN_PROB,
                 human_infect_cattle_prob=HUMAN_INFECT_CATTLE_PROB,
                 cattle_infect_human_prob=CATTLE_INFECT_HUMAN_PROB,
                 cattle_infect_cattle_prob=CATTLE_INFECT_CATTLE_PROB,
                 bird_infect_cattle_prob=BIRD_INFECT_COW_PROB,
                 ):
        super().__init__(seed=seed)
        self.simulator = simulator
        self.simulator.setup(self)

        # store a list of all the Person agent types - seems this gets used a bit
        self.person_agent_types = [cls for cls in inspect.getmembers(Agents, inspect.isclass)
                                   if issubclass(cls[1], PersonAgent) and cls[1] != PersonAgent]

        self.width = width
        self.height = height

        # Create grid using experimental cell space
        self.grid = OrthogonalVonNeumannGrid(
            [self.height, self.width],
            torus=False,
            capacity=math.inf,
            random=self.random,
        )

        self.hospital_cells = []  # keep a list of cells that are hospital
        self.farm_services_cells = []
        self.large_animal_cells = []
        self.small_animal_cells = []
        # create the hospital agents and farm agents
        for cell in self.grid:
            # print("{}".format(cell.coordinate))
            if cell.coordinate[0] < 10:
                # Hospital covers the left of the space
                if cell.coordinate[1] <= int(self.height / 3):
                    # farm services at the top
                    HospitalAgent(self, HospitalDepartment.FARM_SERVICES, cell=cell)
                    self.farm_services_cells.append(cell)
                elif int(self.height / 3) < cell.coordinate[1] <= 2 * int(self.height / 3):
                    # large animal in the middle
                    HospitalAgent(self, HospitalDepartment.LARGE_ANIMAL, cell=cell)
                    self.large_animal_cells.append(cell)
                elif cell.coordinate[1] > 2 * int(self.height / 3):
                    # small animal at the bottom
                    HospitalAgent(self, HospitalDepartment.SMALL_ANIMAL, cell=cell)
                    self.small_animal_cells.append(cell)
                # print("  hospital")

                self.hospital_cells.append(cell)
            elif cell.coordinate[0] in range(height - 4, height, 2) and cell.coordinate[1] % 2 == 0:
                # farms are every second cell along the right edge of the space
                # print("  farm")
                farm = DairyFarmAgent(self, cell=cell,
                                      cattle_infect_human_prob=cattle_infect_human_prob,
                                      cattle_infect_cattle_prob=cattle_infect_cattle_prob,
                                      bird_infect_cattle_prob=bird_infect_cattle_prob)
                # one farmer per farm
                farmer = Farmer(self, cell=cell,
                                human_infect_human_prob=human_infect_human_prob,
                                human_infect_cattle_prob=human_infect_cattle_prob)
                farmer.location = Location.FARM
                farmer.farm = farm

        # queue to manage farm requests for vets
        self.farm_request_queue = []

        # create vets and start them at the hospital
        for _ in range(NUM_FARM_SERVICES_TECHS):
            FarmServicesTechnician(self, cell=self.random.choice(self.farm_services_cells),
                                   human_infect_human_prob=human_infect_human_prob,
                                   human_infect_cattle_prob=human_infect_cattle_prob)
        for _ in range(NUM_FARM_SERVICES_VETS):
            FarmServicesVet(self, cell=self.random.choice(self.farm_services_cells),
                            human_infect_human_prob=human_infect_human_prob,
                            human_infect_cattle_prob=human_infect_cattle_prob)
        for _ in range(NUM_LARGE_ANIMAL_VETS):
            LargeAnimalVet(self, cell=self.random.choice(self.large_animal_cells),
                           human_infect_human_prob=human_infect_human_prob,
                           human_infect_cattle_prob=human_infect_cattle_prob)
        for _ in range(NUM_SMALL_ANIMAL_VETS):
            SmallAnimalVet(self, cell=self.random.choice(self.small_animal_cells),
                           human_infect_human_prob=human_infect_human_prob,
                           human_infect_cattle_prob=human_infect_cattle_prob)
        for _ in range(NUM_FLOATING_STAFF):
            FloatingStaff(self, cell=self.random.choice(self.large_animal_cells + self.small_animal_cells),
                          human_infect_human_prob=human_infect_human_prob,
                          human_infect_cattle_prob=human_infect_cattle_prob)

        # infect some random farms to get things going
        num_infected_farms = min(num_infected_farms, len(self.agents_by_type[DairyFarmAgent]))
        for farm in self.random.sample(self.agents_by_type[DairyFarmAgent], k=num_infected_farms):
            farm.infect_cattle(1)

        # add collecters for the people infection trackers
        model_reporters = {
            "Infected": proportion_vet_infected,
            "Susceptible": number_vet_susceptible,
            "Recovered": number_vet_recovered,
            # FarmServicesVet, FarmServicesTechnician, LargeAnimalVet, SmallAnimalVet, FloatingStaff
            "FarmServicesVet":
                lambda model: number_state(model, DiseaseState.INFECTED, [FarmServicesVet]) /
                              number_people(model, FarmServicesVet),
            "FarmServicesTechnician":
                lambda model: number_state(model, DiseaseState.INFECTED, [FarmServicesTechnician]) /
                              number_people(model, FarmServicesTechnician),
            "LargeAnimalVet":
                lambda model: number_state(model, DiseaseState.INFECTED, [LargeAnimalVet]) /
                              number_people(model, LargeAnimalVet),
            "SmallAnimalVet":
                lambda model: number_state(model, DiseaseState.INFECTED, [SmallAnimalVet]) /
                              number_people(model, SmallAnimalVet),
            "FloatingStaff":
                lambda model: number_state(model, DiseaseState.INFECTED, [FloatingStaff]) /
                              number_people(model, FloatingStaff),
            "Farmer": lambda model: number_state(model, DiseaseState.INFECTED, [Farmer]) / number_people(model, Farmer)
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
        available_vets = list(self.agents_by_type[FarmServicesVet].select(lambda a: a.location == Location.HOSPITAL))
        min_vets_farms = min(len(available_vets), len(self.farm_request_queue))
        for _ in range(min_vets_farms):
            farm = self.farm_request_queue.pop(0)
            farm_services_vet = available_vets.pop(0)

            farm.visit_from_vet(farm_services_vet)
            farm_services_vet.visit_farm(farm)

        # manage vets that have finished their visit at a farm and are returning to the hospital
        vets_at_farms = self.agents_by_type[FarmServicesVet].select(
            lambda a: a.location == Location.FARM and isinstance(a, FarmServicesVet))
        for farm_services_vet in vets_at_farms:
            if farm_services_vet.steps_at_farm > VET_STEPS_AT_FARM:
                # been there long enough - time to go back to the hospital
                farm_services_vet.farm.vet_leaving()
                farm_services_vet.leave_farm()

        # agents do all their steps
        # self.agents_by_type[PersonAgent].shuffle_do('step')
        for name, agent_class in self.person_agent_types:
            self.agents_by_type[agent_class].shuffle_do('step')
        self.agents_by_type[DairyFarmAgent].shuffle_do('step')

        self.datacollector.collect(self)

    def request_vet_visit(self, farm):
        """
        A farm needs a vet to visit. Put them at the end of the queue
        :param farm: The farm requesting a vet visit
        :type farm: DairyFarmAgent object
        """
        self.farm_request_queue.append(farm)
