from mesa.experimental.cell_space import CellAgent, FixedAgent, CellCollection

from SIRModel import SIRModel

from constants import CHANCE_FARM_NEEDS_VET, FarmVetVisitState, Location, \
    DiseaseState, HUMAN_INFECTED_STEPS, HUMAN_RECOVERED_STEPS, HUMAN_INFECT_HUMAN_PROB, HUMAN_INFECT_CATTLE_PROB, \
    CATTLE_INFECT_HUMAN_PROB, CATTLE_INFECT_CATTLE_PROB, CATTLE_RECOVERY_PROB, HospitalDepartment, \
    BIRD_INFECT_COW_PROB, CATTLE_RECOVERY_END_PROB, DEFAULT_DAIRY_HERD_SIZE


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

        self.farm = None

        # disease information
        self.human_infect_human_prob = human_infect_human_prob
        self.human_infect_cattle_prob = human_infect_cattle_prob
        self.disease_state = DiseaseState.SUSCEPTIBLE
        self.steps_current_disease_state = 0

        # information about where they are now
        self.location = Location.HOSPITAL

        self.cell = cell

    def progress_disease(self):
        """
        If the agent is already infected, then the disease progresses. Either increment time in the current stage or
        move to the next stage.
        """
        # print('vet Disease: {} ({})'.format(self.disease_state, self.steps_current_disease_state))
        if self.disease_state == DiseaseState.INFECTED:
            if self.steps_current_disease_state > HUMAN_INFECTED_STEPS:
                # been infected long enough, time to get better
                self.steps_current_disease_state = 0
                self.disease_state = DiseaseState.RECOVERED
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
        hospital_neighbour_cells = self.get_hospital_neighbour_cells()
        # print("{} {}".format(len(hospital_neighbour_cells), type(self)))
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
            # try to infect other people in the same cell
            local_susceptible_people = [vet for vet in self.cell.agents if isinstance(vet, PersonAgent)]
            for person in local_susceptible_people:
                if self.random.random() < self.human_infect_human_prob:
                    person.infect()
            if self.location == Location.FARM:
                # try to infect a cow in the farm's herd
                if self.random.random() < self.human_infect_cattle_prob:
                    self.farm.cattle_model.infect_susceptible(1)

        # advance the agent's own disease
        self.progress_disease()
        # move depending on location
        self.move()

    def infect(self):
        """
        Get infected by avian influenza
        """
        self.disease_state = DiseaseState.INFECTED
        self.steps_current_disease_state = 0


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


class LargeAnimalVet(PersonAgent):
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
            lambda cell: any(isinstance(agent, HospitalAgent)
                             and (agent.department == HospitalDepartment.FARM_SERVICES
                                  or agent.department == HospitalDepartment.LARGE_ANIMAL)
                             for agent in cell.agents)
        )
        return neighbourhood


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


class FloatingStaff(PersonAgent):
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
            lambda cell: any(isinstance(agent, HospitalAgent)
                             and (agent.department == HospitalDepartment.SMALL_ANIMAL
                                  or agent.department == HospitalDepartment.LARGE_ANIMAL)
                             for agent in cell.agents)
        )
        return neighbourhood


class Farmer(PersonAgent):
    """
    Farmers stay on the farm. One per farm.
    """
    def move(self):
        """
        Farmers just stay on the farm and don't move.
        """
        pass


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
    def __init__(self, model, cell=None, susceptible_cattle=50, infected_cattle=0,
                 cattle_infect_human_prob=CATTLE_INFECT_HUMAN_PROB,
                 cattle_infect_cattle_prob=CATTLE_INFECT_CATTLE_PROB,
                 bird_infect_cattle_prob=BIRD_INFECT_COW_PROB
                 ):
        super().__init__(model, cell)

        # SIR model for the cattle herd
        self.cattle_model = SIRModel(population=susceptible_cattle,
                                     infection_probability=cattle_infect_cattle_prob,
                                     recovery_rate=CATTLE_RECOVERY_PROB,
                                     recovered_expire_rate=CATTLE_RECOVERY_END_PROB)

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
        return self.cattle_model.infected / self.herd_count

    def step(self):
        # progress the system dynamics model on the farm
        self.cattle_model.progress_infection()

        self.try_infect_vet()

        # does the farm need a vet?
        if self.vet_state == FarmVetVisitState.OK and self.random.random() <= CHANCE_FARM_NEEDS_VET:
            # need a vet and don't have one - request a vet
            self.vet_state = FarmVetVisitState.NEED_VET
            self.model.request_vet_visit(self)

        # see if any cows get infected from wild birds
        num_infect = sum(self.random.random() < self.bird_infect_cattle_prob
                         for _ in range(self.cattle_model.susceptible))
        self.cattle_model.infect_susceptible(num_infect)

    def try_infect_vet(self):
        """
        Try to infect the visiting vet
        """
        if self.visiting_vet is not None and self.cattle_model.infected > 0:
            # there is a vet here and the farm has some infected cattle
            # assumes the vet only contacts one cow
            if self.random.random() < self.cattle_infect_human_prob:
                self.visiting_vet.infect()

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
