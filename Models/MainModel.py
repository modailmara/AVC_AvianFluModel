import inspect
import mesa
import math
from mesa.experimental.cell_space import OrthogonalMooreGrid
import pandas as pd

from support_functions import get_input_data_dir
from constants import convert_days_to_steps
from Models.SIRModel import SIRModel
from InfectionPaths import InfectionPaths

import Models
from Models.PeopleAgents import PersonAgent, FarmerAgent, FarmVisitorAgent
from Models.LocationAgents import DairyFarmAgent, HospitalAgent
from constants import FARM_INPUT_FILENAME, HospitalDepartment, PEOPLE_INPUT_FILENAME, PersonRole


class MainModel(mesa.Model):
    """
    The model that coordinates the agents and environment for a Hub and Spoke model of Avian Influenza.
    """

    def __init__(self, seed=None, simulator=None):
        super().__init__(seed=seed)
        if simulator is not None:
            self.simulator = simulator
            self.simulator.setup(self)

        self.width = 20
        self.height = 20

        # Create grid using experimental cell space
        self.grid = OrthogonalMooreGrid(
            [self.height, self.width],
            torus=False,
            capacity=math.inf,
            random=self.random,
        )

        # queue to manage farm requests for vets
        self.farm_request_queue = []
        self.available_farm_clinicians = []

        self.infection_paths = InfectionPaths()

        # keep references to the different types of locations
        self.hospital_cells = {HospitalDepartment.FARM_SERVICES: [], HospitalDepartment.SMALL_ANIMAL: [],
                               HospitalDepartment.LARGE_ANIMAL: [], HospitalDepartment.COMMON: []}
        self.farm_cells = []

        # --------------------------
        # create the hospital

        hospital_width = 9

        # large animal clinic
        for cell_x in range(hospital_width):
            for cell_y in range(13, 20):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.LARGE_ANIMAL, cell=cell)
                self.hospital_cells[HospitalDepartment.LARGE_ANIMAL].append(cell)
        # add a partial row for where farm services overlaps
        for cell_x in range(4, hospital_width):
            cell_y = 12
            cell = self.grid[cell_x, cell_y]
            HospitalAgent(self, HospitalDepartment.LARGE_ANIMAL, cell=cell)
            self.hospital_cells[HospitalDepartment.LARGE_ANIMAL].append(cell)

        # small animal clinic + ???
        for cell_x in range(hospital_width):
            for cell_y in range(9):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.SMALL_ANIMAL, cell=cell)
                self.hospital_cells[HospitalDepartment.SMALL_ANIMAL].append(cell)
        # extra partial row for where farm services overlaps
        for cell_x in range(4, hospital_width):
            cell_y = 9
            cell = self.grid[cell_x, cell_y]
            HospitalAgent(self, HospitalDepartment.SMALL_ANIMAL, cell=cell)
            self.hospital_cells[HospitalDepartment.SMALL_ANIMAL].append(cell)

        # farm services area
        for cell_x in range(4):
            for cell_y in range(9, 13):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.FARM_SERVICES, cell=cell)
                self.hospital_cells[HospitalDepartment.FARM_SERVICES].append(cell)

        # common area
        for cell_x in range(hospital_width, 12):
            for cell_y in range(6, 10):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.COMMON, cell=cell)
                self.hospital_cells[HospitalDepartment.COMMON].append(cell)

        # ------------------------- end hospital space definition

        # load the farm file to define farms and farmers
        farm_df = pd.read_excel(get_input_data_dir() / FARM_INPUT_FILENAME)
        # add the farm cells, starting top right and every second cell to bottom then left
        cell_x = self.width - 1  # all the way right
        cell_y = 0  # top
        for _, farm_row in farm_df.iterrows():
            cell = self.grid[cell_x, cell_y]
            farm = DairyFarmAgent(self, cell,
                                  farm_row.farm_id, farm_row.herd_size, farm_row.visit_frequency_days,
                                  farm_row.milking_system, farm_row.housing, farm_row.pasture, farm_row.num_infected)
            self.farm_cells.append(cell)

            # one farmer per farm
            FarmerAgent(self, farm)

            # increment the cell coordinates
            cell_y += 2
            if cell_y >= self.height:
                cell_y = 0
                cell_x -= 2

        # load the people file to define hospital locations and staff/clinicians/students
        people_df = pd.read_excel(get_input_data_dir() / PEOPLE_INPUT_FILENAME)
        people_df.columns = people_df.columns.str.lower()
        area_names = [name.split(':')[1].strip()
                      for name in people_df.columns if name.startswith('area:')]

        for _, role_def_row in people_df.iterrows():
            role_name = role_def_row.type.lower().strip()
            person_role = PersonRole(role_name)
            num_role = int(role_def_row.num)

            area_weights = []
            for name in area_names:
                area = HospitalDepartment(name)
                area_weights.append((area, float(role_def_row['area: ' + name])))

            for i in range(num_role):
                if person_role in [PersonRole.FARM_SERVICES_VET, PersonRole.FARM_SERVICES_STUDENT]:
                    FarmVisitorAgent(self, "{}_{}".format(person_role, i), cell=None, role=person_role,
                                     area_weights=area_weights)
                else:
                    PersonAgent(self, "{}_{}".format(person_role, i), cell=None, role=person_role,
                                area_weights=area_weights)
                # person.move()

        self.community_model = SIRModel(self, 'community')

        # add collecters for the people infection trackers
        model_reporters = {
            "Community": lambda model: model.community_model.proportion_infected,
            # 'paths': lambda model: model.infection_paths._path_dict
        }
        # add in a model reporter for each farm
        agent_reporters = {
            DairyFarmAgent: {'Infection': 'infection_level'}
        }

        self.datacollector = mesa.DataCollector(
            model_reporters=model_reporters,
            agenttype_reporters=agent_reporters,
        )
        self.datacollector.collect(self)

    def step(self) -> None:
        """
        Execute one step of the model
        """
        self.agents.shuffle_do('step')

        self.datacollector.collect(self)

    def request_vet_visit(self, farm):
        """
        A farm needs a vet to visit. Put them at the end of the queue
        :param farm: The farm requesting a vet visit
        :type farm: DairyFarmAgent object
        """
        self.farm_request_queue.append(farm)
