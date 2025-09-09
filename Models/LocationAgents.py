from mesa.experimental.cell_space import FixedAgent

from Models.SIRModel import SIRModel
from support_functions import is_business_hours, is_weekend

from constants import CATTLE_INFECT_CATTLE_PROB, CATTLE_INFECTED_DAYS, \
    CATTLE_RECOVERED_DAYS, FarmMilkingSystem, FarmHousing, FarmVetVisitState, CATTLE_CONTACTS_PER_STEP, \
    NUM_MILKING_CONTACTS, Location, EMERGENCY_VISITS_PER_STEP, NON_URGENT_CALLS_PER_STEP, convert_days_to_steps


class LocationAgent(FixedAgent):
    """
    An agent that primarily represents a location
    """

    def __init__(self, model, cell=None):
        """

        :param model: Model instance
        :type model: MainModel objectF
        :param cell: Cell
        :type cell:
        """
        super().__init__(model)

        self.location = None
        self.department = None

        self.cell = cell

    def step(self):
        pass


class HospitalAgent(LocationAgent):
    """
    Agent for a part of the teaching hospital.
    Has a fixed location.
    """

    def __init__(self, model, department, cell=None):
        super().__init__(model, cell)

        self.location = Location.HOSPITAL
        self.department = department


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
        :type farm_id: int
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

        self.location = Location.FARM

        # unique ID (number is only unique within farms)
        self.number = farm_id
        self.name = 'Farm_{}'.format(self.number)
        self.short_name = '{}'.format(self.number)

        # set up the frequency and random counter since last (not modelled) last visit
        self.visit_frequency_steps = convert_days_to_steps(visit_frequency)
        # randomly select a number of days less than visit_frequency but isn't a weekend
        days_since_last_visit = self.random.choice([day for day in range(visit_frequency) if day % 7 not in [5, 6]])
        self.steps_since_last_visit = convert_days_to_steps(days_since_last_visit) + 1

        self.milking_system = FarmMilkingSystem(milking_system.lower().strip())
        self.num_milking_contacts = NUM_MILKING_CONTACTS[self.milking_system]

        self.housing = FarmHousing(housing.lower().strip())
        self.cattle_contacts_per_step = CATTLE_CONTACTS_PER_STEP[self.housing]

        self.pasture = pasture.lower().strip()

        # sometimes the vet visits
        self.vet_state = FarmVetVisitState.OK
        self.visiting_vet = None

        # work out probabilities for emergency calls
        # divide by the number of farms
        self.non_urgent_visit_prob = NON_URGENT_CALLS_PER_STEP / len(self.model.agents_by_type[DairyFarmAgent])
        self.emergency_visit_prob = EMERGENCY_VISITS_PER_STEP / len(self.model.agents_by_type[DairyFarmAgent])

        # SIR model for the cattle herd
        self.cattle_model = SIRModel(model=self.model, name=self.name,
                                     population=herd_size,
                                     infection_probability=CATTLE_INFECT_CATTLE_PROB,
                                     recovery_days=CATTLE_INFECTED_DAYS,
                                     recovered_expire_days=CATTLE_RECOVERED_DAYS,
                                     num_contacts_per_step=self.cattle_contacts_per_step)

        self.cattle_model.infect_susceptible(infected_cattle)

    @property
    def susceptible(self):
        """

        :return:
        :rtype:
        """
        return self.cattle_model.susceptible

    @property
    def proportion_susceptible(self):
        return self.susceptible / self.herd_count

    @property
    def infected(self):
        """

        :return:
        :rtype:
        """
        return sum(self.cattle_model.infected)

    @property
    def proportion_infected(self):
        return self.infected / self.herd_count

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
                # time for a regular visit - request a vet
                self.vet_state = FarmVetVisitState.NEED_VET
                self.model.request_vet_visit(self)
            else:
                # don't need a vet yet
                self.steps_since_last_visit += 1

                # check for emergency visit
                if is_weekend(self.model.steps) and self.random.random() <= self.emergency_visit_prob:
                    # need an emergency clinician - only applies outside business hours
                    self.vet_state = FarmVetVisitState.NEED_VET
                    self.model.request_emergency_vet_visit(self)
                elif self.random.random() <= self.non_urgent_visit_prob:
                    # need a non-urgent visit outside of schedule
                    # can be made outside business hours but only dealt with during business hours
                    self.vet_state = FarmVetVisitState.NEED_VET
                    self.model.request_vet_visit(self)

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
        self.steps_since_last_visit = 0
        self.visiting_vet = None
