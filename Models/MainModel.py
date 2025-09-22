import mesa
import math
from mesa.experimental.cell_space import OrthogonalMooreGrid
import pandas as pd
from collections import defaultdict

from support_functions import get_input_data_dir, is_business_hours, is_weekend
from Models.SIRModel import SIRModel
from InfectionNetwork import InfectionNetwork

from Models.PeopleAgents import PersonAgent, FarmerAgent, FarmVisitorAgent
from Models.LocationAgents import DairyFarmAgent, HospitalAgent
from constants import FARM_INPUT_FILENAME, HospitalDepartment, PEOPLE_INPUT_FILENAME, PersonRole, DiseaseState, \
    input_to_role, MAX_VISITS_PER_TRIP

STOP_ON_COMMUNITY_INFECTION = False


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
        self.farm_emergency_request_queue = []
        self.available_farm_clinicians = []
        self.available_farm_students = []

        self.infection_network = InfectionNetwork()

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
        self.total_people = 0  # count the number of people, remains constant
        for _, farm_row in farm_df.iterrows():
            cell = self.grid[cell_x, cell_y]
            farm = DairyFarmAgent(self, cell,
                                  farm_row.farm_id, farm_row.herd_size, farm_row.visit_frequency_days,
                                  farm_row.milking_system, farm_row.housing, farm_row.pasture, farm_row.num_infected,
                                  num_farms=len(farm_df))
            self.farm_cells.append(cell)

            if farm_row.num_infected > 0:
                # record this starting infection
                self.infection_network.add_infection_source(farm)

            # one farmer per farm
            FarmerAgent(self, farm)
            self.total_people += 1

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

        # create agents for each role
        for _, role_def_row in people_df.iterrows():
            role_name = role_def_row.type.lower().strip()
            person_role = input_to_role[role_name]
            num_role = int(role_def_row.num)
            self.total_people += num_role

            # parse the weightings for each area for this role
            area_weights = []
            for name in area_names:
                area = HospitalDepartment(name)
                area_weights.append((area, float(role_def_row['area: ' + name])))

            for person_num in range(num_role):
                if person_role in [PersonRole.FARM_SERVICES_CLINICIAN, PersonRole.FARM_SERVICES_STUDENT]:
                    visitor_agent = FarmVisitorAgent(self, person_num, cell=None, role=person_role,
                                                     area_weights=area_weights)
                    if person_role == PersonRole.FARM_SERVICES_CLINICIAN:
                        # add the farmer to the queue for vet farm visits
                        self.available_farm_clinicians.append(visitor_agent)
                    elif person_role == PersonRole.FARM_SERVICES_STUDENT:
                        # add the farmer to the queue for vet farm visits
                        self.available_farm_students.append(visitor_agent)
                else:
                    PersonAgent(self, person_num, cell=None, role=person_role,
                                area_weights=area_weights)
                # person.move()

        self.community_model = SIRModel(self, 'community')

        # track visits to farms by FS vets (doesn't fit with collectors)
        # farm_visits_by_vet {step_num: [(vet id, farm id), ...]
        self.farm_visits_by_vets = defaultdict(list)

        # add collecters for the people infection trackers
        model_reporters = {
            'Infected': lambda model: model.infected_proportion(),
            'Susceptible': lambda model: model.susceptible_proportion(),
            'Recovered': lambda model: model.recovered_proportion(),
            'paths': lambda model: model.infection_network,
            'farm_visits': lambda model: model.farm_visits_by_vets
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

        self.running = True

    def step(self) -> None:
        """
        Execute one step of the model
        """
        # print('{}: {}'.format(self.steps, self.community_model.proportion_infected))
        if self.community_model.proportion_infected > 0 and STOP_ON_COMMUNITY_INFECTION:
            # there has been community spillover - stop here
            self.running = False
        else:
            # go ahead with another model step
            self.agents.shuffle_do('step')
            self.community_model.step()

            # prioritise emergency visits anytime
            while len(self.farm_emergency_request_queue) > 0 and len(self.available_farm_clinicians) > 0:
                # get the next available clinician and give them a visit list
                clinician = self.available_farm_clinicians.pop(0)
                clinician.farms_to_visit = self.farm_emergency_request_queue[:MAX_VISITS_PER_TRIP]
                # remove those requests from the queue
                self.farm_emergency_request_queue = self.farm_emergency_request_queue[MAX_VISITS_PER_TRIP:]

                # send them on their way
                clinician.visit_next_farm()

            # normal priority farm visits happen only during business hours
            if is_business_hours(self.steps):
                while len(self.farm_request_queue) > 0 and len(self.available_farm_clinicians) > 0:
                    # get the list of farms to visit on this trip
                    farms_to_visit = self.farm_request_queue[:MAX_VISITS_PER_TRIP]
                    # remove these requests from queue
                    self.farm_request_queue = self.farm_request_queue[MAX_VISITS_PER_TRIP:]

                    # set the clinician's trip
                    clinician = self.available_farm_clinicians.pop(0)
                    clinician.farms_to_visit = farms_to_visit.copy()

                    print("{}: {} trip {}".format(self.steps, clinician.short_name,
                                                  [f.short_name for f in clinician.farms_to_visit]))

                    # send them on their way
                    clinician.visit_next_farm()

                    # if there's a student around, they should go along as well
                    if len(self.available_farm_students) > 0:
                        student = self.available_farm_students.pop(0)
                        student.farms_to_visit = farms_to_visit.copy()
                        print("{}: {} trip {}".format(self.steps, student.short_name,
                                                      [f.short_name for f in student.farms_to_visit]))
                        student.visit_next_farm()

            self.datacollector.collect(self)

    def come_back_from_farm(self, farm_visitor):
        """
        A vet or student has returned from visiting a farm. Put them back in the relevant availability queue
        :param farm_visitor: Returning Vet or Student
        :type farm_visitor: PeopleAgents.FarmVisitorAgent object
        """
        if farm_visitor.role == PersonRole.FARM_SERVICES_CLINICIAN:
            self.available_farm_clinicians.append(farm_visitor)
        elif farm_visitor.role == PersonRole.FARM_SERVICES_STUDENT:
            self.available_farm_students.append(farm_visitor)

    def request_vet_visit(self, farm):
        """
        A farm needs a vet to visit. Put them at the end of the queue
        :param farm: The farm requesting a vet visit
        :type farm: DairyFarmAgent object
        """
        self.farm_request_queue.append(farm)

    def request_emergency_vet_visit(self, farm):
        """
        A farm needs an emergency vet visit. Put them at the end of the queue
        :param farm: The farm requesting a vet visit
        :type farm: DairyFarmAgent object
        """
        self.farm_emergency_request_queue.append(farm)

    def susceptible_proportion(self):
        """
        Proportion of people that are susceptible
        :return: Proportion (0-1) of the people agents with disease state INFECTED
        :rtype:
        """
        susceptible_people = [agent for agent in self.agents
                              if isinstance(agent, PersonAgent) and agent.disease_state == DiseaseState.SUSCEPTIBLE]

        return len(susceptible_people) / self.total_people

    def infected_proportion(self):
        """
        Proportion of people that are infected
        :return: Proportion (0-1) of the people agents with disease state INFECTED
        :rtype:
        """
        infected_people = [agent for agent in self.agents
                           if isinstance(agent, PersonAgent) and agent.disease_state == DiseaseState.INFECTED]

        return len(infected_people) / self.total_people

    def recovered_proportion(self):
        """
        Proportion of people that are susceptible
        :return: Proportion (0-1) of the people agents with disease state INFECTED
        :rtype:
        """
        recovered_people = [agent for agent in self.agents
                            if isinstance(agent, PersonAgent) and agent.disease_state == DiseaseState.RECOVERED]

        return len(recovered_people) / self.total_people

