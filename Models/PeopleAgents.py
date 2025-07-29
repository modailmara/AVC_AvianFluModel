from mesa.experimental.cell_space import CellAgent
import numpy as np

from constants import DiseaseState, Location, STEPS_PER_DAY, WORK_DAY_STEPS, COMMUNITY_STEPS, PersonRole, \
    HUMAN_INFECTED_STEPS, HUMAN_RECOVERED_STEPS, HUMAN_INFECT_HUMAN_PROB, VET_STEPS_AT_FARM, VET_CONTACTS_PER_STEP, \
    HUMAN_INFECT_CATTLE_PROB, CATTLE_INFECT_HUMAN_PROB, COMMUNITY_CONTACTS_PER_STEP


class PersonAgent(CellAgent):
    """
    Represents a person based at the Hospital
    """

    def __init__(self, model, person_id, role, cell, area_weights=()):
        """

        :param model:
        :type model:
        :param cell:
        :type cell:
        :param role:
        :type role:
        :param area_weights:
        :type area_weights:
        """
        super().__init__(model)

        self.cell = cell

        self.person_id = person_id
        self.role = role
        self.area_weights = area_weights

        # disease information
        self.disease_state = DiseaseState.SUSCEPTIBLE
        self.steps_current_disease_state = 0

        # the path to the person agent's current infection, [] if they aren't infected
        self.current_infection_path = []

        # information about where they are now - start in the community
        self.location = Location.COMMUNITY

    def step(self):
        """
        Do all the things that a person does in a step:
        - move to a new location
        - progress their disease status
        """
        # check if need to change location
        step_of_day = self.model.steps % STEPS_PER_DAY
        if step_of_day == WORK_DAY_STEPS[0]:  # time to go to work
            self.start_work()
        elif step_of_day == COMMUNITY_STEPS[0]:  # time to go home from work
            self.go_home()
        elif self.location == Location.HOSPITAL:  # no change of location - just do a normal move
            self.move()

        # disease stuff
        self.progress_disease()
        self.infect_others()

    @property
    def name(self):
        return self.person_id

    def move(self):
        """
        If at the hospital, do a weighted random selection of hospital area and random selection of cell in that area
        """
        if self.location == Location.HOSPITAL:
            # at the hospital so do a weighted random move to a hospital area, randomly pick a cell in that area
            # note that it may be the same cell - that is OK

            areas, weights = zip(*self.area_weights)
            selected_area = self.random.choices(areas, weights=weights)[0]  # choices() returns a list

            self.cell = self.random.choice(self.model.hospital_cells[selected_area])

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
        If this person is infected or recently recovered, then progress the status of the disease.
        """
        if self.disease_state == DiseaseState.INFECTED:
            if self.steps_current_disease_state >= HUMAN_INFECTED_STEPS:
                # they've done their time - now recovered
                self.disease_state = DiseaseState.RECOVERED
                self.steps_current_disease_state = 0
            else:
                # still infected - record the time
                self.steps_current_disease_state += 1
        elif self.disease_state == DiseaseState.RECOVERED:
            if self.steps_current_disease_state >= HUMAN_RECOVERED_STEPS:
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
            self.disease_state = DiseaseState.INFECTED
            self.steps_current_disease_state = 0

    def infect_others(self):
        """
        If this person is infected/infectious:
          - if at the hospital, infect other people in the same cell
          - if at the community, infect the community; stop the simulation if successful
        """
        if self.disease_state == DiseaseState.INFECTED:  # can only infect if infectious
            if self.cell is not None:
                # cell not None means there may be other agents to infect
                # get all the agents in this cell
                susceptible_agents_in_cell = [agent for agent in self.cell.agents
                                              if isinstance(agent, PersonAgent)
                                              and agent.disease_state == DiseaseState.SUSCEPTIBLE]
                for agent in susceptible_agents_in_cell:
                    if self.random.random() < HUMAN_INFECT_HUMAN_PROB:
                        agent.become_infected()
            elif self.location == Location.COMMUNITY:
                # try to infect the community
                num_possible_infections = np.random.binomial(COMMUNITY_CONTACTS_PER_STEP,
                                                              self.model.community_model.proportion_susceptible)
                num_infections = np.random.binomial(num_possible_infections, HUMAN_INFECT_HUMAN_PROB)

                if num_infections > 0:
                    # stop if any infections (Community spillover has happened)
                    # self.model.running = False
                    pass


class FarmPersonAgent(PersonAgent):
    """
    Person agent that spends time on a farm
    """

    def __init__(self, model, person_id, role, cell, area_weights=()):
        super().__init__(model, person_id, role, cell, area_weights)

        self.farm = None

    def step(self):
        """
        Do all the usual person step stuff, but also interact with the farm
        """
        super().step()

        if self.location == Location.FARM and self.farm is not None:
            if self.disease_state == DiseaseState.INFECTED:
                # possibility to infect some cattle
                self.infect_cattle()
            if self.disease_state == DiseaseState.SUSCEPTIBLE and self.farm.infection_level > 0:
                # infected cattle - maybe get infected
                self.is_become_infected_by_cattle()

    def infect_cattle(self):
        """
        This person is infectious and on the farm. They may infect susceptible cattle on the farm.
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

        self.steps_at_farm = 0

    def visit_farm(self, farm):
        """
        Go to a farm.
        :param farm:
        :type farm:
        """
        self.farm = farm
        self.cell = farm.cell
        self.location = Location.FARM
        self.steps_at_farm = 0

        if self.role == PersonRole.FARM_SERVICES_VET:
            # visiting vet so register with the farm
            self.farm.visit_from_vet(self)

    def leave_farm(self):
        """
        Leave the farm and return to the hospital
        """
        if self.role == PersonRole.FARM_SERVICES_VET:
            # visiting vet so de-register with the farm
            self.farm.vet_leaving()
        self.model.come_back_from_farm(self)
        self.farm = None
        self.steps_at_farm = 0
        self.location = Location.HOSPITAL
        self.move()

    def step(self):
        """
        Usual step stuff but also count how long at the farm and check if the agent should leave
        """
        super().step()

        if self.location == Location.FARM:
            if self.steps_at_farm >= VET_STEPS_AT_FARM:
                # been here long enough, time to leave
                self.leave_farm()
            else:
                self.steps_at_farm += 1

    def infect_cattle(self):
        """
        This person is infectious and on the farm. They may infect susceptible cattle on the farm.

        This is a farm services vet or student to see some cows that may be sick. This method runs once per step.
        """
        num_susceptible_cows_contacted = min(self.farm.susceptible,
                                             np.random.binomial(VET_CONTACTS_PER_STEP,
                                                                self.farm.proportion_susceptible))
        num_infected = np.random.binomial(num_susceptible_cows_contacted, HUMAN_INFECT_CATTLE_PROB)

        self.farm.cattle_model.infect_susceptible(num_infected, self.current_infection_path)

    def is_become_infected_by_cattle(self):
        """
        This person is susceptible and on a farm. They may become infected by infectious cattle.

        This is a farm services vet or student to see some cows that may be sick. This method runs once per step.
        """
        num_infected_cows_contacted = min(self.farm.susceptible,
                                          np.random.binomial(VET_CONTACTS_PER_STEP,
                                                             self.farm.infection_level))
        num_infections = np.random.binomial(num_infected_cows_contacted, HUMAN_INFECT_CATTLE_PROB)

        if num_infections > 0:
            self.become_infected()


class FarmerAgent(FarmPersonAgent):
    """
    Farmers stay on the farm. One per farm.
    """

    def __init__(self, model, farm):
        """

        :param model: The model that this agent belongs to
        :type model: MainModel object
        """
        super().__init__(model, 'farmer_{}'.format(farm.farm_id), PersonRole.FARMER, None, ())

        # farmers are always on the same farm
        self.farm = farm

    def start_work(self):
        """
        Work day has started.
        """
        self.cell = self.farm.cell
        self.location = Location.FARM

    def move(self):
        """
        farmers stay on the farm
        """
        if self.location == Location.FARM:
            self.cell = self.farm.cell
        else:
            # in the community
            self.cell = None

    def infect_cattle(self):
        """
        This person is infectious and on the farm. They may infect susceptible cattle on the farm.

        This is a farmer, so contacts happen to all cows at milking time. Number of contacts depend on milking system.
        """
        # milking only happens at the first step of the day
        if self.model.steps % STEPS_PER_DAY == WORK_DAY_STEPS[0]:
            # contact every cow a number of times based on milking system
            for _ in range(self.farm.num_milking_contacts):
                num_susceptible_cows_contacted = self.farm.susceptible
                num_infected = np.random.binomial(num_susceptible_cows_contacted, HUMAN_INFECT_CATTLE_PROB)

                self.farm.cattle_model.infect_susceptible(num_infected, self.current_infection_path)

    def is_become_infected_by_cattle(self):
        """
        This person is susceptible and on a farm. They may become infected by infectious cattle.

        This is a farm services vet or student to see some cows that may be sick. This method runs once per step.
        """
        # milking only happens at the first step of the day
        if self.model.steps % STEPS_PER_DAY == WORK_DAY_STEPS[0]:
            # contact every cow a number of times based on milking system
            for _ in range(self.farm.num_milking_contacts):
                num_infected_cows_contacted = self.farm.infected
                num_infections = np.random.binomial(num_infected_cows_contacted, CATTLE_INFECT_HUMAN_PROB)

                if num_infections > 0:
                    self.become_infected()
                    break  # can only become infected once




