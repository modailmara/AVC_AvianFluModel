from mesa.experimental.cell_space import CellAgent
import numpy as np

from Models.CompartmentModel import SEIRModel
import Models
from constants import FarmMilkingSystem, FarmHousing, FarmVetVisitState, Location, TRUCK_ROLE, DiseaseState, Cleaning


class LocationAgent(CellAgent):
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
        self.short_name = '<location>'

        self.disease_state = DiseaseState.SUSCEPTIBLE
        self.num_infectious_steps = 0

        self.cell = cell

    def move(self):
        """
        By default, location agents don't move.
        """
        pass

    def progress_disease(self):
        if self.disease_state == DiseaseState.INFECTIOUS:
            if self.num_infectious_steps >= self.model.params.env_infectious_steps:
                # the infection has expired
                self.disease_state = DiseaseState.SUSCEPTIBLE
                self.num_infectious_steps = 0
            else:
                # increment the disease step counter
                self.num_infectious_steps += 1

    def infect_others(self):
        """
        If infectious, there is a possibility to infect agents at this location
        """
        if self.disease_state == DiseaseState.INFECTIOUS:
            # if there are any people agents in this location, there's a chance to infect them
            for person_agent in [agent for agent in self.cell.agents
                                 if isinstance(agent, Models.PeopleAgents.PersonAgent)
                                    and agent.disease_state == DiseaseState.SUSCEPTIBLE]:
                if self.random.random() <= self.model.params.env_infect_human_prob:
                    person_agent.become_infected()

                    # record the environment infecting the person
                    self.model.infection_network.add_infection_event(self.short_name, person_agent.short_name,
                                                                     self.model.steps)

    def become_infected(self):
        """
        If the location does not already have infectious material, it is now infectious.
        """
        if self.disease_state == DiseaseState.SUSCEPTIBLE:
            self.disease_state = DiseaseState.INFECTIOUS
            self.num_infectious_steps = 0

    def clean(self):
        """
        Clean the location so there is no infectious material.
        """
        self.disease_state = DiseaseState.SUSCEPTIBLE

    def scheduled_cleaning(self):
        """
        Locations can be cleaned of the disease on schedule. By default they aren't.
        """
        pass


class HospitalAgent(LocationAgent):
    """
    Agent for a part of the teaching hospital.
    Has a fixed location.
    """

    def __init__(self, model, department, cell=None, dept_id=None):
        super().__init__(model, cell)

        self.location = Location.HOSPITAL
        self.department = department

        short_dept = ''.join([word[0].upper() for word in self.department.value.split()])
        self.short_name = 'H{}_{}'.format(short_dept, dept_id)

    def scheduled_cleaning(self):
        if self.disease_state == DiseaseState.INFECTIOUS \
                and self.model.params.hospital_cleaning_schedule == Cleaning.DAILY \
                and self.model.is_after_hours_workday(self.model.steps):
            # do a daily clean
            self.clean()


class DairyFarmAgent(LocationAgent):
    """
    Agent for a dairy farm.

    Maybe keep an internal network model for infectious herd?
    """
    def __init__(self, model, cell, farm_id, herd_size, visit_frequency, milking_system, housing, pasture,
                 num_farms=19):
        """

        :param model: The model that this agent belongs to
        :type model: MainModel object
        :param farm_id: Unique ID of this farm: 'F' + int
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
        :type pasture: str
        :param cell: Cell assigned to this farm in the model environment
        :type cell: mesa cell object
        """
        super().__init__(model, cell)

        self.farmer = None  # to be set when a farmer is assigned

        self.location = Location.FARM

        # unique ID (number is only unique within farms)
        self.number = int(farm_id[1:])
        self.name = 'Farm_{}'.format(self.number)
        self.short_name = 'F_{}'.format(self.number)

        # is this farm quarantined? means there is no disease transfer outside the herd due to biosecurity measures
        self.is_quarantined = False

        # set up the frequency and random counter since last (not modelled) last visit
        self.visit_frequency_steps = self.model.params.convert_days_to_steps(visit_frequency)
        # randomly select a number of days less than visit_frequency but isn't a weekend
        days_since_last_visit = self.random.choice([day for day in range(visit_frequency) if day % 7 not in [5, 6]])
        self.steps_since_last_visit = self.model.params.convert_days_to_steps(days_since_last_visit) + 1

        self.milking_system = FarmMilkingSystem(milking_system.lower().strip())
        self.num_milking_contacts = self.model.params.num_milking_contacts[self.milking_system]

        self.housing = FarmHousing(housing.lower().strip())
        self.cattle_contacts_per_step = self.model.params.cattle_contacts_per_step[self.housing]

        self.pasture = pasture.lower().strip()

        # sometimes the vet visits
        self.vet_state = FarmVetVisitState.OK
        self.visiting_vet = None

        # work out probabilities for is_emergency calls
        # divide by the number of farms
        self.non_urgent_visit_prob = self.model.params.non_urgent_calls_per_step / num_farms
        self.emergency_visit_prob = self.model.params.emergency_visits_per_step / num_farms

        # SIR model for the cattle herd
        self.cattle_model = SEIRModel(model=self.model, name=self.name,
                                      population=herd_size,
                                      infection_probability=self.model.params.cattle_infect_cattle_prob,
                                      exposed_steps=self.model.params.cattle_exposed_steps,
                                      infectious_steps=self.model.params.cattle_infected_steps,
                                      recovered_steps=self.model.params.cattle_recovered_steps,
                                      num_contacts_per_step=self.cattle_contacts_per_step)

    @property
    def num_susceptible(self):
        """

        :return:
        :rtype:
        """
        return self.cattle_model.susceptible

    @property
    def proportion_susceptible(self):
        return self.num_susceptible / self.herd_count

    @property
    def num_exposed(self):
        return sum(self.cattle_model.exposed)

    @property
    def proportion_exposed(self):
        return self.num_exposed / self.herd_count

    @property
    def num_infectious(self):
        return sum(self.cattle_model.infectious)

    @property
    def proportion_infected(self):
        return self.num_infectious / self.herd_count

    @property
    def num_recovered(self):
        return sum(self.cattle_model.recovered)

    @property
    def proportion_recovered(self):
        return self.num_recovered / self.herd_count

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
        Get the proportion of infectious cattle in the herd
        :return: #infectious / #total
        :rtype: float
        """
        return self.cattle_model.proportion_infected

    def progress_disease(self):
        """
        In addition to usual location agent disease progress, farms need to check quarantine progress.

        If the herd is all clear of the disease, then quarantine should be ended.
        """
        super().progress_disease()

        if self.is_quarantined:
            # quarantine is lifted if the herd and farmer are not infected or exposed
            if self.num_susceptible + self.num_recovered == self.herd_count and not self.farmer.symptomatic:
                self.is_quarantined = False

    def infect_others(self):
        if not self.is_quarantined:
            # only infect other agents if not quarantined
            super().infect_others()

        # infection still transfers between herd and farm environment under quarantine
        self.farm_infect_herd()
        self.herd_infect_farm()

    def farm_infect_herd(self):
        """
        The farm agent (location/environment) infecting the cattle herd.

        Note that this still occurs even during quarantine.
        """
        # farm location agent (not cattle) can infect susceptible cattle
        if self.disease_state == DiseaseState.INFECTIOUS and self.cattle_model.num_susceptible > 0:
            num_infected = np.random.binomial(self.cattle_model.num_susceptible,
                                              self.model.params.env_infect_cattle_prob)
            self.cattle_model.infect_susceptible(num_infected)

            # don't record this for now as it will swamp the rest of the network
            # self.model.infection_network.add_infection_event(self.short_name, 'h_{}'.format(self.number),
            #                                                  time_step=self.model.steps)

    def herd_infect_farm(self):
        """
        The cattle herd can infect the environment (the farm location agent).

        This still happens when the farm is quarantined
        """
        # infectious cattle can infect the farm location agent
        if self.disease_state == DiseaseState.SUSCEPTIBLE and self.cattle_model.num_infectious > 0:
            for _ in range(self.cattle_model.num_infectious):
                if self.random.random() < self.model.params.cattle_infect_env_prob:
                    self.become_infected()

                    # don't record this for now as it will swamp the rest of the network
                    # self.model.infection_network.add_infection_event('h_{}'.format(self.number), self.short_name,
                    #                                                  time_step=self.model.steps)
                    break  # farm location agent can only be infected once

    def request_vet(self):
        """
        Determine if the farm needs a vet from the hospital to come visit, and send a request if it does.

        There are 3 types of visits:
          1. scheduled visits at regular intervals (specified in farm info spreadsheet)
          2. non-urgent visits (random chance to give frequency from parameters)
          3. emergency visits (random chance to give frequency from parameters)

        Visits still happen if the farm is quarantined
        """
        # does the farm need a vet?
        if self.vet_state == FarmVetVisitState.OK:
            if self.steps_since_last_visit >= self.visit_frequency_steps:
                # time for a regular visit - request a vet
                self.vet_state = FarmVetVisitState.NEED_VET
                self.model.request_vet_visit(self)
            else:
                # not time for a scheduled visit yet, keep counting
                self.steps_since_last_visit += 1

            # check for is_emergency visit
            if self.model.is_weekend(self.model.steps) and self.random.random() <= self.emergency_visit_prob:
                # need an is_emergency clinician - only applies outside business hours
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

    def __str__(self):
        return self.short_name


class TruckAgent(LocationAgent):
    """
    Trucks are used for farm visits. The clinician (and maybe students) go from the VTH to the farm, then to other farms
    before back to the VTH. The truck may carry infection between farms.

    The truck agent coordinates travel around locations. It tells PersonAgents where they are on the trip.
    """

    def __init__(self, model, home_cell, truck_id, travel_cell, truck_bay_agent):
        """

        :param model: Main model instance that the truck agent belongs to
        :type model: MainModel object
        :param home_cell: Cell in the model grid that is the default location at the hospital of this truck agent
        :type home_cell: Cell object
        :param truck_id: Number unique to this truck within the trucks in the model
        :type truck_id: int
        :param travel_cell: Cell in the model grid that this truck occupies to indicate travel
        :type travel_cell: Cell object
        """
        super().__init__(model, home_cell)

        self.home_cell = home_cell
        self.travel_cell = travel_cell

        # hospital farm services location agent that is the bay for the trucks
        self.truck_bay = truck_bay_agent

        self.number = truck_id
        self.name = f"Truck_{self.number}"
        self.short_name = f"T_{self.number}"
        self.role = TRUCK_ROLE

        self.farm = None
        self.passengers = None

        # count the number of steps at the current location
        self.steps_at_farm = 0
        self.steps_at_travel = 0
        # list of farms to visit on this trip
        self.farms_to_visit = []

    def move(self):
        """
        If the truck is on a farm visit trip, then continue on the trip
        """
        if self.location == Location.TRAVEL:
            # already travelling
            if self.steps_at_travel >= self.model.params.visit_travel_steps:
                # been travelling long enough - reached destination (farm or hospital)
                self.go_to_next_location()
            else:
                # still travelling
                self.steps_at_travel += 1
        elif self.location == Location.FARM:
            # check if the truck needs to leave the farm
            if self.steps_at_farm >= self.model.params.vet_steps_at_farm:
                # been here long enough, time to leave
                self.travel()
            else:
                self.steps_at_farm += 1

    def infect_others(self):
        """

        """
        # if Infectious, infect any people agents
        super().infect_others()

        if self.location == Location.FARM and not self.farm.is_quarantined:
            # if at a farm, there is a chance to exchange infectious material to the farm
            # if the farm is quarantined, assume biosecurity measures prevent infection
            if self.disease_state == DiseaseState.INFECTIOUS and self.farm.disease_state == DiseaseState.SUSCEPTIBLE:
                # check if there is infection transfer between the truck and farm
                if self.random.random() < self.model.params.truck_infect_env_prob:
                    self.farm.become_infected()
                    # record the truck infecting the farm location
                    self.model.infection_network.add_infection_event(self.short_name, self.farm.short_name,
                                                                     self.model.steps)
                elif self.disease_state == DiseaseState.SUSCEPTIBLE \
                        and self.farm.disease_state == DiseaseState.INFECTIOUS:
                    # susceptible truck and infectious farm - maybe get infectious
                    if self.random.random() < self.model.params.env_infect_truck_prob:
                        self.become_infected()
                        # record the farm location infecting the truck
                        self.model.infection_network.add_infection_event(self.farm.short_name, self.short_name,
                                                                         self.model.steps)
        elif self.location == Location.HOSPITAL:
            # the truck is not actually in the same grid square as the truck bay or farm
            # so (inconsistently) transfer of infectious material to the truck agent happens here
            if self.disease_state == DiseaseState.INFECTIOUS \
                    and self.truck_bay.disease_state == DiseaseState.SUSCEPTIBLE:
                # possibility to infect the truck bay at the hospital
                if self.random.random() < self.model.params.truck_infect_env_prob:
                    self.truck_bay.become_infected()
                    # record the truck infecting the hospital truck bay
                    self.model.infection_network.add_infection_event(self.short_name, self.truck_bay.short_name,
                                                                     self.model.steps)
            elif self.disease_state == DiseaseState.SUSCEPTIBLE \
                    and self.truck_bay.disease_state == DiseaseState.INFECTIOUS:
                # possibility to be infectious by the truck bay
                if self.random.random() < self.model.params.env_infect_truck_prob:
                    self.become_infected()
                    # record the hospital truck bay infecting the truck
                    self.model.infection_network.add_infection_event(self.truck_bay.short_name, self.short_name,
                                                                     self.model.steps)

    def scheduled_cleaning(self):
        if self.disease_state == DiseaseState.INFECTIOUS \
                and self.model.params.truck_cleaning_schedule == Cleaning.DAILY \
                and self.model.is_after_hours_workday(self.model.steps):
            # do a daily clean
            self.clean()

    def start_travel_from_hospital(self, farms_to_visit, passengers):
        """
        Start a trip from the hospital to visit 1 or more farms.

        :param farms_to_visit: List of farms to visit on this trip
        :type farms_to_visit: list
        :param passengers: List of FarmVisitorAgents that are travelling in the truck
        :type passengers: list
        """
        # set the farms to visit
        self.farms_to_visit = farms_to_visit

        # set the passengers
        self.passengers = passengers

        # leave on the trip
        self.travel()

    def travel(self):
        """
        Move to travelling between hospital and farm, or between farms
        """
        if self.location == Location.FARM:
            # leaving a farm - some passengers need to do cleanup
            for passenger in self.passengers:
                passenger.leave_farm()

        self.location = Location.TRAVEL
        self.cell = self.travel_cell
        self.steps_at_travel = 0

        # update the passengers
        for passenger in self.passengers:
            passenger.travel(self.travel_cell)

    def go_to_next_location(self):
        """

        :return:
        :rtype:
        """
        if len(self.farms_to_visit) > 0:
            # still some farms to visit on this trip
            self.visit_next_farm()
        else:
            self.return_to_hospital()

    def visit_next_farm(self):
        """
        Visit the next farm in this trip
        """
        # print("  {}: {} visiting farm, remaining trip {}".format(self.model.steps, self.short_name,
        #      [f.short_name for f in self.farms_to_visit]))
        self.location = Location.FARM
        self.farm = self.farms_to_visit.pop(0)
        # print(f'    {self.model.steps}: {self.name} visiting {self.farm.name}')

        # put the truck next to the farm cell
        coord_x, coord_y = self.farm.cell.coordinate
        coord_x -= 1
        self.cell = self.model.grid[coord_x, coord_y]
        self.steps_at_farm = 0

        for passenger in self.passengers:
            passenger.visit_next_farm(self.farm)

    def return_to_hospital(self):
        """
        Leave the farm and return to the hospital
        """
        self.location = Location.HOSPITAL
        self.farm = None
        self.cell = self.home_cell

        if self.disease_state == DiseaseState.INFECTIOUS \
                and self.model.params.truck_cleaning_schedule == Cleaning.VISIT:
            # clean on return from visiting farms
            self.clean()

        self.model.come_back_from_farm(self)

        for passenger in self.passengers:
            passenger.return_to_hospital()

    def become_infectious(self):
        """
        The truck is infectious.
        """
        self.disease_state = DiseaseState.INFECTIOUS

    def remove_infectious_material(self):
        """
        Any infectious material on the truck is removed.
        """
        self.disease_state = DiseaseState.SUSCEPTIBLE
