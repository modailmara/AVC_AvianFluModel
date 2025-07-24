from mesa.experimental.cell_space import CellAgent, FixedAgent, CellCollection
import numpy as np

from constants import DiseaseState, Location, STEPS_PER_DAY, DAYTIME_STEPS, WORK_DAY_STEPS, COMMUNITY_STEPS, PersonRole


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

        """
        # check if need to change location
        step_of_day = self.model.steps % STEPS_PER_DAY
        if step_of_day == WORK_DAY_STEPS[0]:  # time to go to work
            self.start_work()
        elif step_of_day == COMMUNITY_STEPS[0]:
            self.go_home()
        else:
            self.move()

    @property
    def name(self):
        return self.person_id

    def move(self):
        """
        If at the hospital, randomly select a new hospital cell, weighted by area
        """
        if self.location == Location.HOSPITAL:
            areas, weights = zip(*self.area_weights)
            selected_area = self.random.choices(areas, weights=weights)[0]  # choices() returns a list
            # randomly select a cell in that area
            # print("areas: {}\nweights: {}\nselected: {}".format(areas, weights, selected_area))
            # print("hospital cells: {}".format(self.model.hospital_cells[selected_area]))
            self.cell = self.random.choice(self.model.hospital_cells[selected_area])
        else:
            self.cell = None

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


class FarmerAgent(PersonAgent):
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
        self.steps_at_farm = 0

        self.location = Location.COMMUNITY

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
            self.cell = None


# --------------------------------------------------------
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

        self.department = department


