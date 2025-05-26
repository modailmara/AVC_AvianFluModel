from mesa.experimental.cell_space import CellAgent, FixedAgent, CellCollection
import numpy as np

from SIRModel import SIRModel

from constants import CHANCE_FARM_NEEDS_VET, FarmVetVisitState, Location, DiseaseState, HospitalDepartment, \
    HUMAN_INFECTED_STEPS, HUMAN_RECOVERED_STEPS, HUMAN_INFECT_HUMAN_PROB, HUMAN_INFECT_CATTLE_PROB, \
    CATTLE_INFECT_HUMAN_PROB, BIRD_INFECT_COW_PROB, CATTLE_INFECT_CATTLE_PROB, \
    DEFAULT_DAIRY_HERD_SIZE, CATTLE_CATTLE_CONTACTS_PER_DAY, CATTLE_INFECTED_DAYS, CATTLE_RECOVERED_DAYS, \
    CATTLE_FARMER_CONTACTS_PER_STEP, CATTLE_VET_CONTACTS_PER_STEP, \
    COMMUNITY_CONTACTS_PER_STEP


class PersonAgent(CellAgent):
    """
    Represents a vet that works at the Hospital and goes out to visit dairy farms
    """

    def __init__(self, model, cell=None,
                 human_infect_human_prob=HUMAN_INFECT_HUMAN_PROB,
                 human_infect_cattle_prob=HUMAN_INFECT_CATTLE_PROB):
        """

        :param model: The model that this agent belongs to
        :type model: MainModel object
        """
        super().__init__(model)

        self.name = type(self).__name__

        self.farm = None

        # disease information
        self.human_infect_human_prob = human_infect_human_prob
        self.human_infect_cattle_prob = human_infect_cattle_prob
        self.disease_state = DiseaseState.SUSCEPTIBLE
        self.steps_current_disease_state = 0

        # the path to the person agent's current infection, [] if they aren't infected
        self.current_infection_path = []

        # information about where they are now - start in the community
        self.location = Location.COMMUNITY

        self.cell = cell

    def progress_disease(self):
        """
        If the agent is already infected, then the disease progresses. Either increment time in the current stage or
        move to the next stage.
        """
        if self.disease_state == DiseaseState.INFECTED:
            if self.steps_current_disease_state > HUMAN_INFECTED_STEPS:
                # been infected long enough, time to get better
                self.steps_current_disease_state = 0
                self.disease_state = DiseaseState.RECOVERED

                # empty infection path
                self.current_infection_path = []
            else:
                # remain at this state so add another step
                self.steps_current_disease_state += 1
        elif self.disease_state == DiseaseState.RECOVERED:
            if self.steps_current_disease_state > HUMAN_RECOVERED_STEPS:
                # immunity time is over, time to be susceptible again
                self.steps_current_disease_state = 0
                self.disease_state = DiseaseState.SUSCEPTIBLE
            else:
                # immunity for a bit longer
                self.steps_current_disease_state += 1

    def move(self):
        """
        If in the hospital area, move randomly to another hospital space.
        """
        if self.location == Location.HOSPITAL:
            hospital_neighbour_cells = self.get_hospital_neighbour_cells()
            # move to a random neighbouring hospital cell
            self.cell = hospital_neighbour_cells.select_random_cell()
            # raise NotImplementedError("Should be implemented by inheriting classes.")

    def get_hospital_neighbour_cells(self):
        """
        Gets the cells in this agent's neighbourhood that are available for them to move to.
        Different for each type of person agent.
        :return: Collection of cells that this agent can move to.
        :rtype: CellCollection object
        """
        neighbourhood = self.cell.neighborhood.select(
            lambda cell: any(isinstance(agent, HospitalAgent) for agent in cell.agents)
        )
        return neighbourhood
        # raise NotImplementedError("This method must be overridden by child classes.")

    def step(self):
        """
        Do all the things for a single step
        """
        if self.disease_state == DiseaseState.INFECTED:
            if self.location == Location.COMMUNITY:
                # try to infect some people in the community
                potential_infections = np.random.binomial(COMMUNITY_CONTACTS_PER_STEP,
                                                          self.model.community_model.proportion_susceptible)
                num_infections = np.random.binomial(potential_infections, HUMAN_INFECT_HUMAN_PROB)
                self.model.community_model.infect_susceptible(num_infections,
                                                              infection_path=self.current_infection_path)
            else:
                # try to infect other people in the same cell
                local_susceptible_people = [vet for vet in self.cell.agents if isinstance(vet, PersonAgent)]
                for person in local_susceptible_people:
                    if self.random.random() < self.human_infect_human_prob:
                        person.infect(infection_path=self.current_infection_path + [self.name])
                if self.location == Location.FARM:
                    # try to infect a cow in the farm's herd
                    if isinstance(self, Farmer):
                        possible_infections = np.random.binomial(
                            CATTLE_FARMER_CONTACTS_PER_STEP,
                            self.farm.cattle_model.proportion_susceptible)
                    else:
                        possible_infections = np.random.binomial(
                            CATTLE_VET_CONTACTS_PER_STEP,
                            self.farm.cattle_model.proportion_susceptible)
                    infections = np.random.binomial(possible_infections, HUMAN_INFECT_CATTLE_PROB)
                    self.farm.cattle_model.infect_susceptible(
                        infections, infection_path=self.current_infection_path + [self.name])
        elif self.disease_state == DiseaseState.SUSCEPTIBLE:
            # may get infected from an SIR model. Note that infections from other agents happen by sharing a cell
            if self.location in [Location.FARM, Location.COMMUNITY]:
                if self.location == Location.FARM:
                    sir_model = self.farm.cattle_model
                    num_contacts = CATTLE_FARMER_CONTACTS_PER_STEP if isinstance(self, Farmer) \
                        else CATTLE_VET_CONTACTS_PER_STEP
                    infection_prob = CATTLE_INFECT_HUMAN_PROB
                else:  # self.location == Location.COMMUNITY
                    sir_model = self.model.community_model
                    num_contacts = COMMUNITY_CONTACTS_PER_STEP
                    infection_prob = HUMAN_INFECT_HUMAN_PROB

                possible_infection_sources = np.random.binomial(num_contacts, sir_model.proportion_infected)
                is_infected = np.random.binomial(possible_infection_sources, infection_prob) > 0

                if is_infected:
                    self.infect(infection_path=[sir_model.name])

        # advance the agent's own disease
        self.progress_disease()
        # move depending on location
        self.move()

    def infect(self, infection_path=[]):
        """
        Get infected by avian influenza
        """
        self.disease_state = DiseaseState.INFECTED
        self.steps_current_disease_state = 0
        self.current_infection_path = infection_path
        self.model.infection_paths.add_path(infection_path + [self.name])

    def go_home(self):
        """
        This agent is finished for the day.
        """
        self.cell = None
        self.location = Location.COMMUNITY

    def start_work(self):
        """
        Work day has started.
        """
        self.go_to_start_cell()
        self.location = Location.HOSPITAL

    def go_to_start_cell(self):
        """
        Assign a cell to this agent.
        This method should be overriden by most person agents. Default is a random cell in the hospital.
        """
        self.cell = self.random.choice(self.model.hospital_cells)


class FarmServicesVet(PersonAgent):
    """
    farm services vets (5) and students (6) (go between farms, hospital farm services area, and some contact with
    large animal clinic area)
    """

    def __init__(self, model, cell=None,
                 human_infect_human_prob=HUMAN_INFECT_HUMAN_PROB,
                 human_infect_cattle_prob=HUMAN_INFECT_CATTLE_PROB):
        """

        :param model: The model that this agent belongs to
        :type model: MainModel object
        """
        super().__init__(model, cell=cell,
                         human_infect_human_prob=human_infect_human_prob,
                         human_infect_cattle_prob=human_infect_cattle_prob)

        self.name = 'fs clinician'
        self.farm = None
        self.steps_at_farm = 0

    def visit_farm(self, farm):
        """
        Visit a farm
        :type farm: DairyFarmAgent object
        """
        self.location = Location.FARM
        self.farm = farm
        self.cell = farm.cell

    def leave_farm(self):
        """
        Return from a farm visit to the hospital
        """
        self.farm = None
        self.location = Location.HOSPITAL
        self.cell = self.model.random.choice(self.model.farm_services_cells)
        self.steps_at_farm = 0

    def move(self):
        """
        If in the hospital area, move randomly to another hospital space.
        """
        if self.location == Location.HOSPITAL:
            hospital_neighbour_cells = self.get_hospital_neighbour_cells()
            # move to a random hospital cell
            self.cell = hospital_neighbour_cells.select_random_cell()
        elif self.location == Location.FARM:
            self.steps_at_farm += 1

    def get_hospital_neighbour_cells(self):
        """
        This type of agent can move within the farm services area in the hospital
        :return: Collection of Farm Services cells next to this agent
        :rtype: CellCollection
        """
        neighbourhood = self.cell.neighborhood.select(
            lambda cell: any(isinstance(agent, HospitalAgent) and agent.department == HospitalDepartment.FARM_SERVICES
                             for agent in cell.agents)
        )
        return neighbourhood

    def go_home(self):
        """
        This agent is finished for the day.
        """
        if self.location == Location.FARM:
            self.farm.vet_leaving()
            self.leave_farm()
        self.cell = None
        self.location = Location.COMMUNITY

    def go_to_start_cell(self):
        """
        Assign a cell to this agent.
        This method should be overriden by most person agents. Default is a random cell in the hospital.
        """
        self.cell = self.random.choice(self.model.farm_services_cells)


class FarmServicesTechnician(PersonAgent):
    """
    farm services technicians (2) (stay at farm services area)
    """

    def get_hospital_neighbour_cells(self):
        """
        This type of agent can move within the farm services area in the hospital
        :return: Collection of Farm Services cells next to this agent
        :rtype: CellCollection
        """
        neighbourhood = self.cell.neighborhood.select(
            lambda cell: any(isinstance(agent, HospitalAgent) and agent.department == HospitalDepartment.FARM_SERVICES
                             for agent in cell.agents)
        )
        return neighbourhood

    def go_to_start_cell(self):
        """
        Assign a cell to this agent.
        This method should be overriden by most person agents. Default is a random cell in the hospital.
        """
        self.cell = self.random.choice(self.model.farm_services_cells)


class LargeAnimalVet(PersonAgent):
    """
    Large animal clinic, farm services
    """

    def get_hospital_neighbour_cells(self):
        """
        This type of agent can move within the farm services area in the hospital
        :return: Collection of Farm Services cells next to this agent
        :rtype: CellCollection
        """
        neighbourhood = self.cell.neighborhood.select(
            lambda cell: any(isinstance(agent, HospitalAgent)
                             and (agent.department == HospitalDepartment.FARM_SERVICES
                                  or agent.department == HospitalDepartment.LARGE_ANIMAL)
                             for agent in cell.agents)
        )
        return neighbourhood

    def go_to_start_cell(self):
        """
        Assign a cell to this agent.
        This method should be overriden by most person agents. Default is a random cell in the hospital.
        """
        self.cell = self.random.choice(self.model.large_animal_cells)


class SmallAnimalVet(PersonAgent):
    """
    farm services technicians (2) (stay at farm services area)
    """

    def get_hospital_neighbour_cells(self):
        """
        This type of agent can move within the farm services area in the hospital
        :return: Collection of Farm Services cells next to this agent
        :rtype: CellCollection
        """
        neighbourhood = self.cell.neighborhood.select(
            lambda cell: any(isinstance(agent, HospitalAgent) and agent.department == HospitalDepartment.SMALL_ANIMAL
                             for agent in cell.agents)
        )
        return neighbourhood

    def go_to_start_cell(self):
        """
        Assign a cell to this agent.
        This method should be overriden by most person agents. Default is a random cell in the hospital.
        """
        self.cell = self.random.choice(self.model.small_animal_cells)


class FloatingStaff(PersonAgent):
    """
    Floating staff: small animal and large animal
    """

    def get_hospital_neighbour_cells(self):
        """
        This type of agent can move within the farm services area in the hospital
        :return: Collection of Farm Services cells next to this agent
        :rtype: CellCollection
        """
        neighbourhood = self.cell.neighborhood.select(
            lambda cell: any(isinstance(agent, HospitalAgent)
                             and (agent.department == HospitalDepartment.SMALL_ANIMAL
                                  or agent.department == HospitalDepartment.LARGE_ANIMAL)
                             for agent in cell.agents)
        )
        return neighbourhood

    def go_to_start_cell(self):
        """
        Assign a cell to this agent.
        This method should be overriden by most person agents. Default is a random cell in the hospital.
        """
        self.cell = self.random.choice(self.model.large_animal_cells + self.model.small_animal_cells)


class Farmer(PersonAgent):
    """
    Farmers stay on the farm. One per farm.
    """
    def __init__(self, model, farm, cell=None,
                 human_infect_human_prob=HUMAN_INFECT_HUMAN_PROB,
                 human_infect_cattle_prob=HUMAN_INFECT_CATTLE_PROB):
        """

        :param model: The model that this agent belongs to
        :type model: MainModel object
        """
        super().__init__(model, cell=cell,
                         human_infect_human_prob=human_infect_human_prob,
                         human_infect_cattle_prob=human_infect_cattle_prob)

        # farmers are always on the same farm
        self.farm = farm
        self.steps_at_farm = 0

    def move(self):
        """
        Farmers just stay on the farm or community and don't move.
        """
        pass

    def start_work(self):
        """
        Work day has started.
        """
        self.go_to_start_cell()
        self.location = Location.FARM

    def go_to_start_cell(self):
        """
        Assign a cell to this agent.
        This method should be overriden by most person agents. Default is a random cell in the hospital.
        """
        self.cell = self.farm.cell


# --------------------------------------------------------
class LocationAgent(FixedAgent):
    """
    An agent that primarily represents a location
    """

    def __init__(self, model, cell=None):
        """

        :param model: Model instance
        :type model: MainModel object
        :param cell: Cell
        :type cell:
        """
        super().__init__(model)

        self.cell = cell

    def step(self):
        pass


class HospitalAgent(LocationAgent):
    """
    Agent for a part of the teaching hospital.
    Has a fixed location. Home base for the vets which visit the dairy farms.
    """

    def __init__(self, model, department, cell=None):
        super().__init__(model, cell)

        self.department = department


class DairyFarmAgent(LocationAgent):
    """
    Agent for a dairy farm.

    Maybe keep an internal network model for infected herd?
    """
    def __init__(self, model, cell=None, susceptible_cattle=DEFAULT_DAIRY_HERD_SIZE, infected_cattle=0,
                 cattle_infect_human_prob=CATTLE_INFECT_HUMAN_PROB,
                 cattle_infect_cattle_prob=CATTLE_INFECT_CATTLE_PROB,
                 bird_infect_cattle_prob=BIRD_INFECT_COW_PROB):
        super().__init__(model, cell)

        # SIR model for the cattle herd
        self.cattle_model = SIRModel(model=self.model, name='farm',
                                     population=susceptible_cattle,
                                     infection_probability=cattle_infect_cattle_prob,
                                     recovery_days=CATTLE_INFECTED_DAYS,
                                     recovered_expire_days=CATTLE_RECOVERED_DAYS,
                                     num_contacts_per_day=CATTLE_CATTLE_CONTACTS_PER_DAY)

        self.name = self.cattle_model.name

        # infection parameters
        self.cattle_infect_human_prob = cattle_infect_human_prob
        self.bird_infect_cattle_prob = bird_infect_cattle_prob

        # sometimes the vet visits
        self.vet_state = FarmVetVisitState.OK
        self.visiting_vet = None

    @property
    def herd_count(self):
        """
        Get the total number of cattle in this farm's herd.
        :return: Total number of cattle
        :rtype: int
        """
        return self.cattle_model.population

    @property
    def infection_level(self):
        """
        Get the proportion of infected cattle in the herd
        :return: #infected / #total
        :rtype: float
        """
        return self.cattle_model.proportion_infected

    def step(self):
        # progress the system dynamics model on the farm
        self.cattle_model.progress_infection()

        # does the farm need a vet?
        if self.vet_state == FarmVetVisitState.OK and self.random.random() <= CHANCE_FARM_NEEDS_VET:
            # need a vet and don't have one - request a vet
            self.vet_state = FarmVetVisitState.NEED_VET
            self.model.request_vet_visit(self)

        # see if any cows get infected from wild birds
        num_infect = sum(self.random.random() < self.bird_infect_cattle_prob
                         for _ in range(self.cattle_model.susceptible))
        self.cattle_model.infect_susceptible(num_infect, infection_path=['bird'])

    def visit_from_vet(self, vet):
        """
        A vet has come to visit the herd
        :param vet: The vet agent that is visiting the farm
        :type vet: FarmServicesVet object
        """
        self.visiting_vet = vet
        self.vet_state = FarmVetVisitState.VET_PRESENT

    def vet_leaving(self):
        """
        The vet that came to visit has finished and is now leaving
        """
        self.vet_state = FarmVetVisitState.OK
        self.visiting_vet = None
