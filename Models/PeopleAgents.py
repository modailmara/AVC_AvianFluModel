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

        self.number = person_id
        self.role = role
        self.name = '{}_{}'.format(self.role.name, self.number)
        self.short_name = '{}{}'.format(self.role.value, self.number)
        self.area_weights = area_weights

        # disease information
        self.disease_state = DiseaseState.SUSCEPTIBLE
        self.steps_current_disease_state = 0

        # information about where they are now - start in the community
        self.location = Location.COMMUNITY
        self.department = None

    def step(self):
        """
        Do all the things that a person does in a step:
        - move to a new location
        - progress their disease status
        """
        # check need to change location
        if self.location == Location.COMMUNITY and self.model.is_business_hours(self.model.steps):
            # out in the community and it's time to go to work
            self.start_work()
        elif self.location == Location.HOSPITAL:
            if not self.model.is_business_hours(self.model.steps):
                # at work and work time is over so time to go home from work
                self.go_home()
            elif self.model.is_business_hours(self.model.steps):
                # at the hospital, time to move around
                self.move()

        # disease stuff
        self.progress_disease()
        self.infect_others()  # maybe infect other people agents or community
        self.become_infected_by_community()  # maybe get infected by the community

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
        If this person is exposed, infected, or recovered, then progress the status of the disease.
        """
        if self.disease_state == DiseaseState.EXPOSED:
            if self.steps_current_disease_state >= self.model.params.human_exposed_steps:
                # exposed time is done - now infectious
                self.disease_state = DiseaseState.INFECTIOUS
                self.steps_current_disease_state = 0
            else:
                # more time to go being exposed - increment the counter
                self.steps_current_disease_state += 1
        elif self.disease_state == DiseaseState.INFECTIOUS:
            if self.steps_current_disease_state >= self.model.params.human_infectious_steps:
                # they've done their time - now recovered
                self.disease_state = DiseaseState.RECOVERED
                self.steps_current_disease_state = 0
            else:
                # still infected - increment time counter
                self.steps_current_disease_state += 1
        elif self.disease_state == DiseaseState.RECOVERED:
            if self.steps_current_disease_state >= self.model.params.human_recovered_steps:
                # immunity has expired - back to susceptible
                self.disease_state = DiseaseState.SUSCEPTIBLE
                self.steps_current_disease_state = 0
            else:
                # still immune from recent recovery
                self.steps_current_disease_state += 1

    def become_infected(self):
        """
        This susceptible agent becomes infected
        """
        if self.disease_state == DiseaseState.SUSCEPTIBLE:
            self.disease_state = DiseaseState.EXPOSED
            self.steps_current_disease_state = 0

    def infect_others(self):
        """
        If this person is infected/infectious:
          - if at the hospital, infect other people in the same cell
          - if at the community, infect the community; stop the simulation if successful
        """
        if self.disease_state == DiseaseState.INFECTIOUS:  # can only infect if infectious
            if self.cell is not None:
                # cell not None means there may be other agents to infect
                # get all the agents in this cell
                susceptible_agents_in_cell = [agent for agent in self.cell.agents
                                              if isinstance(agent, PersonAgent)
                                              and agent.disease_state == DiseaseState.SUSCEPTIBLE]
                for agent in susceptible_agents_in_cell:
                    if self.random.random() < self.model.params.human_infect_human_prob:
                        agent.become_infected()

                        # record in the infection graph
                        self.model.infection_network.add_infection_event(source_agent=self, infected_agent=agent,
                                                                         time_step=self.model.steps)
            elif self.location == Location.COMMUNITY:
                # try to infect the community
                num_possible_infections = np.random.binomial(self.model.params.community_contacts_per_step,
                                                             self.model.community_model.proportion_susceptible)
                num_infections = np.random.binomial(num_possible_infections, self.model.params.human_infect_human_prob)

                if num_infections > 0:
                    self.model.community_model.expose_to_infection(num_infections)
                    # record the infection
                    self.model.infection_network.add_community_spillover(self, self.model.steps)

            if self.location == Location.HOSPITAL or self.location == Location.TRAVEL:
                # chance of infecting the environment
                env_location_agents = [agent for agent in self.cell.agents
                                       if isinstance(agent, Models.LocationAgents.LocationAgent)
                                       and agent.disease_state == DiseaseState.SUSCEPTIBLE]
                for location_agent in env_location_agents:
                    # hopefully only 0 or 1 but no harm in doing a for loop
                    if self.random.random() <= self.model.params.human_infect_env_prob:
                        location_agent.become_infected()

                        # record the infection in the infection network
                        self.model.infection_network.add_infection_event(self, location_agent, self.model.steps)

    def become_infected_by_community(self):
        """

        """
        if self.disease_state == DiseaseState.SUSCEPTIBLE and self.location == Location.COMMUNITY:
            num_infected_people_contacted = min(self.model.community_model.num_susceptible,
                                                np.random.binomial(self.model.params.community_contacts_per_step,
                                                                   self.model.community_model.proportion_infected))
            num_infections = np.random.binomial(num_infected_people_contacted,
                                                self.model.params.human_infect_human_prob)

            if num_infections > 0:
                self.become_infected()

                self.model.infection_network.add_community_infection(infected_agent=self, time_step=self.model.steps)


class FarmPersonAgent(PersonAgent):
    """
    Person agent that spends time on a farm
    """

    def __init__(self, model, person_id, role, cell, area_weights=()):
        """

        :param model:
        :type model:
        :param person_id: ID number unique amongst the role
        :type person_id: int
        :param role:
        :type role:
        :param cell:
        :type cell:
        :param area_weights:
        :type area_weights:
        """
        super().__init__(model, person_id, role, cell, area_weights)

        self.farm = None

    def step(self):
        """
        Do all the usual person step stuff, but also interact with the farm
        """
        super().step()

        if self.location == Location.FARM and self.farm is not None:
            if self.disease_state == DiseaseState.INFECTIOUS:
                # possibility to infect some cattle
                self.infect_cattle()
            elif self.disease_state == DiseaseState.SUSCEPTIBLE and self.farm.proportion_infected > 0:
                # infected cattle - maybe get infected
                # print('susceptible {}'.format(self.name))
                self.is_become_infected_by_cattle()

    def infect_cattle(self):
        """
        This person is infectious and on a farm. They may infect susceptible cattle on the farm.
        """
        raise NotImplementedError("Base class. Implement infecting cattle.")

    def is_become_infected_by_cattle(self):
        """
        This person is susceptible and on a farm. They may become infected by infectious cattle.
        """
        raise NotImplementedError("Base class. Implement infecting cattle.")


class FarmVisitorAgent(FarmPersonAgent):
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
        # print("  {}: {} visiting farm, remaining trip {}".format(self.model.steps, self.short_name,
        #                                                          [f.short_name for f in self.farms_to_visit]))
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

    def infect_cattle(self):
        """
        This person is infectious and on the farm. They may infect susceptible cattle on the farm.

        This is a farm services vet or student to see some cows that may be sick. This method runs once per step.
        """
        num_susceptible_cows_contacted = min(self.farm.num_susceptible,
                                             np.random.binomial(self.model.params.vet_contacts_per_step,
                                                                self.farm.proportion_susceptible))
        num_infected = np.random.binomial(num_susceptible_cows_contacted, self.model.params.human_infect_cattle_prob)

        if num_infected > 0:
            self.farm.cattle_model.expose_to_infection(num_infected)

            self.model.infection_network.add_infection_event(source_agent=self, infected_agent=self.farm,
                                                             time_step=self.model.steps)

    def is_become_infected_by_cattle(self):
        """
        This person is susceptible and on a farm. They may become infected by infectious cattle.

        This is a farm services vet or student to see some cows that may be sick. This method runs once per step.
        """
        num_infected_cows_contacted = min(self.farm.num_infected,
                                          np.random.binomial(self.model.params.vet_contacts_per_step,
                                                             self.farm.proportion_infected))
        num_infections = np.random.binomial(num_infected_cows_contacted, self.model.params.cattle_infect_human_prob)

        if num_infections > 0:
            self.become_infected()

            self.model.infection_network.add_infection_event(source_agent=self.farm, infected_agent=self,
                                                             time_step=self.model.steps)


class FarmerAgent(FarmPersonAgent):
    """
    Farmers stay on the farm. One per farm.
    """

    def __init__(self, model, farm):
        """

        :param model: The model that this agent belongs to
        :type model: MainModel object
        """
        super().__init__(model, farm.number, PersonRole.FARMER, None, ())

        # farmers are always on the same farm
        self.farm = farm

    def step(self):
        super().step()

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
        if self.location == Location.FARM:
            self.cell = self.farm.cell
        else:
            # in the community
            self.cell = None

    def go_home(self):
        """
        Farmers are quarantined if there is an infection on their farm
        """
        # check to see if the farmer is quarantined due to an infected farm
        if not self.model.params.is_quarantine_farmer or self.farm.num_infected == 0:
            # act as normal
            super().go_home()

    def infect_cattle(self):
        """
        This person is infectious and on the farm. They may infect susceptible cattle on the farm.

        This is a farmer, so contacts happen to all cows at milking time. Number of contacts depend on milking system.
        """
        # put all the milking events at the beginning of the day
        # currently doesn't matter that they aren't spaced out - if it does then this has to be changed
        if self.model.steps % self.model.params.steps_per_day in \
                self.model.params.work_day_steps[:self.model.params.num_milking_events_per_day]:
            # contact every cow a number of times based on milking system
            for _ in range(self.farm.num_milking_contacts):
                num_susceptible_cows_contacted = self.farm.num_susceptible
                num_infected = np.random.binomial(num_susceptible_cows_contacted,
                                                  self.model.params.human_infect_cattle_prob)

                if num_infected > 0:
                    self.farm.cattle_model.expose_to_infection(num_infected)

                    self.model.infection_network.add_infection_event(source_agent=self, infected_agent=self.farm,
                                                                     time_step=self.model.steps)

    def is_become_infected_by_cattle(self):
        """
        This person is susceptible and on a farm. They may become infected by infectious cattle.

        This is a farm services vet or student to see some cows that may be sick. This method runs once per step.
        """
        # put all the milking events at the beginning of the day
        # currently doesn't matter that they aren't spaced out - if it does then this has to be changed
        if self.model.steps % self.model.params.steps_per_day in \
                self.model.params.work_day_steps[:self.model.params.num_milking_events_per_day]:
            # contact every cow a number of times based on milking system
            for _ in range(self.farm.num_milking_contacts):
                num_infected_cows_contacted = self.farm.num_infected
                num_infections = np.random.binomial(num_infected_cows_contacted,
                                                    self.model.params.cattle_infect_human_prob)

                if num_infections > 0:
                    self.become_infected()

                    self.model.infection_network.add_infection_event(source_agent=self.farm, infected_agent=self,
                                                                     time_step=self.model.steps)

                    break  # can only become infected once




