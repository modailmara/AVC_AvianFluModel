from mesa.experimental.cell_space import CellAgent
import numpy as np

from constants import DiseaseState, Location, PersonRole
import Models


class PersonAgent(CellAgent):
    """
    Represents a person in the model. Tracks Avian Influenza status and location in the model.
    """

    def __init__(self, model, person_id, role, cell, area_weights=()):
        """

        :param model: Model that this agent belongs to
        :type model: MainModel
        :param person_id: ID number unique amongst the role
        :type person_id: int
        :param role: Role of the agent in the model.
        :type role: PersonRole
        :param cell: Starting grid location of the agent
        :type cell: mesa.experimental.cell_space.grid.GridCell
        :param area_weights: Weighting for selecting areas of the hospital to move to
        :type area_weights: list
        """
        super().__init__(model)

        self.cell = cell

        self.farm = None  # only gets a value when this agent visits a farm

        self.number = person_id
        self.role = role
        self.name = '{}_{}'.format(self.role.name, self.number)
        self.short_name = '{}_{}'.format(self.role.value, self.number)
        self.area_weights = area_weights

        # disease information
        self.vaccinated = False
        self.disease_state = DiseaseState.SUSCEPTIBLE
        self.steps_current_disease_state = 0
        # person becomes symptomatic sometime after being exposed
        self.symptomatic = False
        self.steps_since_exposed = 0

        # information about where they are now - start in the community
        self.location = Location.COMMUNITY
        self.department = None

    def start_stop_work(self):
        """
        At the beginning of each week day, people go to work. At the end of the day they go home.
        """
        # check need to change location
        if self.location == Location.COMMUNITY and self.model.is_business_hours(self.model.steps):
            # out in the community and it's time to go to work
            self.start_work()
        elif self.location == Location.HOSPITAL and not self.model.is_business_hours(self.model.steps):
            # at work and work time is over so time to go home
            self.go_home()

    def move(self):
        """
        If at the hospital, do a weighted random selection of hospital area and random selection of cell in that area
        """
        if self.location == Location.HOSPITAL:
            # at the hospital so do a weighted random move to a hospital area, randomly pick a cell in that area
            # note that it may be the same cell - that is OK

            areas, weights = zip(*self.area_weights)
            choices = self.random.choices(areas, weights=weights)
            selected_area = choices[0]  # choices() returns a list

            self.cell = self.random.choice(self.model.hospital_cells[selected_area])

            self.department = selected_area

    def go_home(self):
        """
        Go home after work. Removes from farm cell and goes to the community.
        """
        self.location = Location.COMMUNITY
        self.cell = None

    def start_work(self):
        """
        Work day has started.
        """
        self.location = Location.HOSPITAL
        self.move()

    def progress_disease(self):
        """
        If this person is exposed, infectious, or recovered, then progress the status of the disease.
        """
        if self.disease_state == DiseaseState.EXPOSED:
            if self.steps_current_disease_state >= self.model.params.human_exposed_steps:
                # exposed time is done - now infectious
                self.disease_state = DiseaseState.INFECTIOUS
                self.steps_current_disease_state = 0
            else:
                # more time to go being exposed - increment the counter
                self.steps_current_disease_state += 1
            self.steps_since_exposed += 1
        elif self.disease_state == DiseaseState.INFECTIOUS:
            if self.steps_current_disease_state >= self.model.params.human_infectious_steps:
                # they've done their time - now recovered
                self.disease_state = DiseaseState.RECOVERED
                self.steps_current_disease_state = 0
            else:
                # still infectious - increment time counter
                self.steps_current_disease_state += 1
            self.steps_since_exposed += 1
        elif self.disease_state == DiseaseState.RECOVERED:
            if self.steps_current_disease_state >= self.model.params.human_recovered_steps:
                # immunity has expired - back to susceptible
                self.disease_state = DiseaseState.SUSCEPTIBLE
                self.steps_current_disease_state = 0
            else:
                # still immune from recent recovery
                self.steps_current_disease_state += 1
            # no longer symptomatic
            self.symptomatic = False
            self.steps_since_exposed = 0

        if self.steps_since_exposed >= self.model.params.human_symptomatic_steps:
            self.become_symptomatic()

    def become_symptomatic(self):
        """
        This person agent is showing signs of having the disease.
        """
        self.symptomatic = True

    def become_infected(self):
        """
        This susceptible agent becomes exposed
        """
        if self.disease_state == DiseaseState.SUSCEPTIBLE:
            self.disease_state = DiseaseState.EXPOSED
            self.steps_current_disease_state = 0

    def infect_others(self):
        """
        If this person is infectious/infectious:
          - if at the hospital, infect other people in the same cell
          - if at the community, infect the community; stop the simulation if successful
        """
        if self.disease_state == DiseaseState.INFECTIOUS:  # can only infect if infectious
            if self.location == Location.COMMUNITY:
                # in the community so can infect community members
                if self.vaccinated:
                    # print("to community: {} using vaccination prob".format(self.name))
                    infection_prob = self.model.params.vacc_human_infect_human_prob
                else:
                    infection_prob = self.model.params.human_infect_human_prob

                num_possible_infections = np.random.binomial(self.model.params.community_contacts_per_step,
                                                             self.model.community_model.proportion_susceptible)
                num_infections = np.random.binomial(num_possible_infections, infection_prob)

                # can only infect up to the number of susceptible
                num_infections = min(num_infections, self.model.community_model.num_susceptible)
                if num_infections > 0:
                    self.model.community_model.expose_to_infection(num_infections)
                    # record the infection
                    self.model.infection_network.add_community_spillover(self.short_name, self.model.steps)
            elif self.location in [Location.HOSPITAL, Location.TRAVEL]:
                self.infect_environment()
                self.infect_other_person_agents()

    def infect_environment(self):
        """
        May infect the environment/location agent in the same cell as this agent.
        """
        if self.vaccinated:
            # print("to env: {} using vaccination prob".format(self.name))
            infection_prob = self.model.params.vacc_human_infect_env_prob
        else:
            infection_prob = self.model.params.human_infect_env_prob
        # chance of infecting the environment
        env_location_agents = [agent for agent in self.cell.agents
                               if isinstance(agent, Models.LocationAgents.LocationAgent)
                               and agent.disease_state == DiseaseState.SUSCEPTIBLE]
        for location_agent in env_location_agents:

            # hopefully only 0 or 1 but no harm in doing a for loop
            if self.random.random() <= infection_prob:
                location_agent.become_infected()

                # record the infection in the infection network
                self.model.infection_network.add_infection_event(self.short_name, location_agent.short_name,
                                                                 self.model.steps)

    def infect_other_person_agents(self):
        """
        May infect all the other person agents in the same cell as this agent.
        """
        # work out the infection probability
        if self.vaccinated:
            # print("to person: {} using vaccination prob".format(self.name))
            infection_prob = self.model.params.vacc_human_infect_human_prob
        else:
            infection_prob = self.model.params.human_infect_human_prob
        # get all the location agents (environment) in this cell
        # get all the agents in this cell
        susceptible_agents_in_cell = [agent for agent in self.cell.agents
                                      if isinstance(agent, PersonAgent)
                                      and agent.disease_state == DiseaseState.SUSCEPTIBLE]
        for agent in susceptible_agents_in_cell:
            if self.random.random() < infection_prob:
                agent.become_infected()

                # record in the infection graph
                self.model.infection_network.add_infection_event(source_name=self.short_name,
                                                                 target_name=agent.short_name,
                                                                 time_step=self.model.steps)

    def become_infected_by_community(self):
        """

        """
        if self.disease_state == DiseaseState.SUSCEPTIBLE and self.location == Location.COMMUNITY \
                and self.model.community_model.num_infectious > 0:
            if self.vaccinated:
                # print("from community: {} using vaccination prob".format(self.name))
                infection_prob = self.model.params.vacc_human_infect_human_prob
            else:
                infection_prob = self.model.params.human_infect_human_prob
            num_infected_people_contacted = min(self.model.community_model.num_infectious,
                                                np.random.binomial(self.model.params.community_contacts_per_step,
                                                                   self.model.community_model.proportion_infected))
            num_infections = np.random.binomial(num_infected_people_contacted, infection_prob)

            if num_infections > 0:
                self.become_infected()

                self.model.infection_network.add_community_infection(target_name=self.short_name,
                                                                     time_step=self.model.steps)

    def become_infected_by_cattle(self):
        """
        Empty method to be implemented by person agents that go to farms.
        """
        raise NotImplementedError("Should only be used by person agents on a farm")

    def infect_cattle(self):
        """
        If this person is infectious and on the farm. They may infect susceptible cattle on the farm.

        Empty, to be implemented by person agents that go to farms
        """
        raise NotImplementedError("Should only be used by person agents on a farm")


class FarmVisitorAgent(PersonAgent):
    """
    Hospital person Agent that visits and leaves a farm
    """
    def __init__(self, model, person_id, role, cell, area_weights=()):
        super().__init__(model, person_id, role, cell, area_weights)

        # the truck being used when visiting farms
        self.truck = None

    def travel(self, travel_cell):
        """
        Travelling between hospital and farm or between farms
        :param travel_cell: Cell in the model grid occupied while travelling to the next location
        :type travel_cell: Cell object
        """
        self.location = Location.TRAVEL
        self.cell = travel_cell

    def visit_next_farm(self, farm):
        """
        Visit the next farm in this trip
        """

        if self.location == Location.FARM:
            self.leave_farm()

        self.location = Location.FARM
        self.farm = farm
        # print(f'    {self.model.steps}: {self.name} visiting {self.farm.name}')
        self.cell = self.farm.cell

        if self.role == PersonRole.FARM_SERVICES_CLINICIAN:
            # visiting vet so register with the farm
            self.farm.visit_from_vet(self)

            # record the visit
            self.model.farm_visits_by_vets[self.model.steps].append((self.name, self.farm.name))

    def go_home(self):
        """
        Go home after work. Removes from farm cell and goes to the community.

        Need to override here as if the visitor is at a farm, they need to do farm leaving things first
        """
        if self.location == Location.FARM:
            self.leave_farm()
        self.location = Location.COMMUNITY
        self.cell = None

    def leave_farm(self):
        """
        Leave the farm and return to the hospital
        """
        if self.role == PersonRole.FARM_SERVICES_CLINICIAN:
            # visiting vet so de-register with the farm
            self.farm.vet_leaving()

    def return_to_hospital(self):
        """
        Returning to the hospital after visiting farms
        """
        self.location = Location.HOSPITAL
        self.model.come_back_from_farm(self)
        self.move()

    def infect_others(self):
        super().infect_others()  # hospital and community only

        if self.location == Location.FARM and not self.farm.is_quarantined:
            if self.disease_state == DiseaseState.INFECTIOUS:
                self.infect_environment()
                self.infect_other_person_agents()
                self.infect_cattle()
            elif self.disease_state == DiseaseState.SUSCEPTIBLE:
                self.become_infected_by_cattle()

    def infect_cattle(self):
        """
        This person is infectious and on the farm. They may infect susceptible cattle on the farm.

        This is a farm services vet or student to see some cows that may be sick. This method runs once per step.
        """
        if self.disease_state == DiseaseState.INFECTIOUS and self.farm.num_susceptible > 0 \
                and not self.farm.is_quarantined:
            if self.vaccinated:
                # print("to cattle: {} using vaccination prob".format(self.name))
                infection_prob = self.model.params.vacc_human_infect_cattle_prob
            else:
                infection_prob = self.model.params.human_infect_cattle_prob
            num_susceptible_cows_contacted = min(self.farm.num_susceptible,
                                                 np.random.binomial(self.model.params.vet_contacts_per_step,
                                                                    self.farm.proportion_susceptible))
            num_infected = np.random.binomial(num_susceptible_cows_contacted, infection_prob)

            if num_infected > 0:
                self.farm.cattle_model.expose_to_infection(num_infected)

                self.model.infection_network.add_infection_event(source_name=self.short_name,
                                                                 target_name=self.farm.herd_short_name,
                                                                 time_step=self.model.steps)

    def become_infected_by_cattle(self):
        """
        This person is susceptible and on a farm. They may become infectious by infectious cattle.

        This is a farm services vet or student to see some cows that may be sick. This method runs once per step.
        """
        if self.disease_state == DiseaseState.SUSCEPTIBLE and self.farm.num_infectious > 0 \
                and not self.farm.is_quarantined:
            if self.vaccinated:
                # print("from cattle: {} using vaccination prob".format(self.name))
                infection_prob = self.model.params.vacc_cattle_infect_human_prob
            else:
                infection_prob = self.model.params.cattle_infect_human_prob
            num_infected_cows_contacted = min(self.farm.num_infectious,
                                              np.random.binomial(self.model.params.vet_contacts_per_step,
                                                                 self.farm.proportion_infected))
            num_infections = np.random.binomial(num_infected_cows_contacted, infection_prob)

            if num_infections > 0:
                self.become_infected()

                self.model.infection_network.add_infection_event(source_name=self.farm.herd_short_name,
                                                                 target_name=self.short_name,
                                                                 time_step=self.model.steps)


class FarmerAgent(PersonAgent):
    """
    Farmers stay on the farm. One per farm.
    """

    def __init__(self, model, farm):
        """

        :param model: The model that this agent belongs to
        :type model: MainModel object
        :param farm: The farm that this farmer runs
        :type farm: DairyFarmAgent
        """
        super().__init__(model, farm.number, PersonRole.FARMER, None, ())

        # farmers are always on the same farm
        self.farm = farm
        self.farm.farmer = self

        steps_between_milking = self.model.params.daytime_steps // self.model.params.num_milking_events_per_day
        self.milking_time_steps = list(range(1, self.model.params.daytime_steps+1, steps_between_milking))

    def start_stop_work(self):
        """
        At the beginning of each week day, people go to work. At the end of the day they go home.
        """
        if self.location == Location.COMMUNITY and self.model.is_business_hours(self.model.steps):
            self.start_work()
        elif self.location == Location.FARM and not self.model.is_business_hours(self.model.steps):
            self.go_home()

    def start_work(self):
        """
        Work day has started.
        """
        self.cell = self.farm.cell
        self.location = Location.FARM

    def move(self):
        """
        farmers stay on the farm during business hours
        """
        pass

    def go_home(self):
        """
        Farmers are quarantined if there is an infection on their farm
        """
        # check to see if the farm is quarantined
        if not self.farm.is_quarantined:
            # act as normal
            super().go_home()

    def infect_others(self):
        super().infect_others()  # Hospital and community only

        if self.location == Location.FARM and not self.farm.is_quarantined:
            if self.disease_state == DiseaseState.INFECTIOUS:
                self.infect_environment()
                self.infect_other_person_agents()
                self.infect_cattle()
            elif self.disease_state == DiseaseState.SUSCEPTIBLE:
                self.become_infected_by_cattle()

    def become_infected_by_cattle(self):
        """
        This person is susceptible and on a farm. They may become infectious by infectious cattle.

        This is a farm services vet or student to see some cows that may be sick. This method runs once per step.
        """
        if self.disease_state == DiseaseState.SUSCEPTIBLE and self.farm.num_infectious > 0 \
                and not self.farm.is_quarantined:
            # direct contact with cattle is just at milking
            if self.model.steps % self.model.params.steps_per_day in self.milking_time_steps:
                if self.vaccinated:
                    # print("from cattle: {} using vaccination prob".format(self.name))
                    infection_prob = self.model.params.vacc_cattle_infect_human_prob
                else:
                    infection_prob = self.model.params.cattle_infect_human_prob
                # contact every cow a number of times based on milking system
                for _ in range(self.farm.num_milking_contacts):
                    num_infected_cows_contacted = self.farm.num_infectious
                    num_infections = np.random.binomial(num_infected_cows_contacted, infection_prob)

                    if num_infections > 0:
                        self.become_infected()

                        self.model.infection_network.add_infection_event(source_name=self.farm.herd_short_name,
                                                                         target_name=self.short_name,
                                                                         time_step=self.model.steps)

                        break  # can only become infectious once

    def infect_cattle(self):
        """
        This person is infectious and on the farm. They may infect susceptible cattle on the farm.

        This is a farmer, so contacts happen to all cows at milking time. Number of contacts depend on milking system.
        """
        if self.disease_state == DiseaseState.INFECTIOUS and self.farm.num_susceptible > 0 \
                and not self.farm.is_quarantined:
            # direct contact with cattle is just at milking
            if self.model.steps % self.model.params.steps_per_day in self.milking_time_steps:
                if self.vaccinated:
                    # print("to cattle: {} using vaccination prob".format(self.name))
                    infection_prob = self.model.params.vacc_human_infect_cattle_prob
                else:
                    infection_prob = self.model.params.human_infect_cattle_prob
                # contact every cow a number of times based on milking system
                for _ in range(self.farm.num_milking_contacts):
                    num_susceptible_cows_contacted = self.farm.num_susceptible
                    num_infected = np.random.binomial(num_susceptible_cows_contacted, infection_prob)

                    if num_infected > 0:
                        self.farm.cattle_model.expose_to_infection(num_infected)

                        self.model.infection_network.add_infection_event(source_name=self.short_name,
                                                                         target_name=self.farm.herd_short_name,
                                                                         time_step=self.model.steps)

    def become_symptomatic(self):
        """
        In addition to setting the symptomatic flag, farmers becoming symptomatic triggers quarantining the farm.
        """
        super().become_symptomatic()

        if self.model.params.is_quarantine_farm:
            self.farm.is_quarantined = True
