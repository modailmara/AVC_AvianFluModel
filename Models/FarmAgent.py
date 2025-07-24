from Models.Agents import LocationAgent
from Models.SIRModel import SIRModel
from constants import convert_days_to_steps

from constants import CATTLE_INFECT_CATTLE_PROB, CATTLE_INFECT_HUMAN_PROB, CATTLE_INFECTED_DAYS, \
    CATTLE_RECOVERED_DAYS, CATTLE_CATTLE_CONTACTS_PER_DAY, FarmMilkingSystem, FarmHousing, FarmVetVisitState


class DairyFarmAgent(LocationAgent):
    """
    Agent for a dairy farm.

    Maybe keep an internal network model for infected herd?
    """
    def __init__(self, model, cell, farm_id, herd_size, visit_frequency, milking_system, housing, pasture,
                 infected_cattle=0):
        """

        :param model: The model that this agent belongs to
        :type model: MainModel object
        :param farm_id: Unique ID of this farm
        :type farm_id: str
        :param herd_size: Number of milking cows
        :type herd_size: int
        :param visit_frequency: Number of days between vet visits
        :type visit_frequency: int
        :param milking_system: Type of milking system (case insensitive value of FarmMilkingSystem enum)
        :type milking_system: str
        :param housing: Type of housing on the farm (case insensitive value of FarmHousing enum)
        :type housing: str
        :param pasture: Description of pasture available to cattle
        :type pasture: str`
        :param cell: Cell assigned to this farm in the model environment
        :type cell: mesa cell object
        :param infected_cattle: Number of the herd that are initially infected
        :type infected_cattle: int
        """
        super().__init__(model, cell)

        self.farm_id = farm_id
        self.visit_frequency_steps = convert_days_to_steps(visit_frequency)
        self.steps_since_last_visit = self.random.randint(0, self.visit_frequency_steps)
        self.milking_system = FarmMilkingSystem(milking_system.lower().strip())
        self.housing = FarmHousing(housing.lower().strip())
        self.pasture = pasture.lower().strip()

        # sometimes the vet visits
        self.vet_state = FarmVetVisitState.OK
        self.visiting_vet = None

        # SIR model for the cattle herd
        self.cattle_model = SIRModel(model=self.model, name=self.farm_id,
                                     population=herd_size,
                                     infection_probability=CATTLE_INFECT_CATTLE_PROB,
                                     recovery_days=CATTLE_INFECTED_DAYS,
                                     recovered_expire_days=CATTLE_RECOVERED_DAYS,
                                     num_contacts_per_day=CATTLE_CATTLE_CONTACTS_PER_DAY)

        self.cattle_model.infect_susceptible(infected_cattle, [])

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
        if self.vet_state == FarmVetVisitState.OK:
            if self.steps_since_last_visit >= self.visit_frequency_steps:
                # need a vet and don't have one - request a vet
                self.vet_state = FarmVetVisitState.NEED_VET
                self.model.request_vet_visit(self)
            else:
                # don't need a vet yet
                self.steps_since_last_visit += 1

    def visit_from_vet(self, vet):
        """
        A vet has come to visit the herd
        :param vet: The vet agent that is visiting the farm
        :type vet: FarmServicesVet object
        """
        self.visiting_vet = vet
        self.vet_state = FarmVetVisitState.VET_PRESENT
        self.steps_since_last_visit = 0

    def vet_leaving(self):
        """
        The vet that came to visit has finished and is now leaving
        """
        self.vet_state = FarmVetVisitState.OK
        self.visiting_vet = None
