import mesa
import math
from mesa.experimental.cell_space import OrthogonalMooreGrid
import pandas as pd
from collections import defaultdict

from support_functions import get_input_data_dir, is_business_hours, is_start_of_workday, is_middle_of_workday
from Models.SIRModel import SIRModel
from InfectionNetwork import InfectionNetwork

from Models.PeopleAgents import PersonAgent, FarmerAgent, FarmVisitorAgent
from Models.LocationAgents import DairyFarmAgent, HospitalAgent, TruckAgent
from constants import FARM_INPUT_FILENAME, HospitalDepartment, PEOPLE_INPUT_FILENAME, PersonRole, DiseaseState, \
    input_to_role, MAX_VISITS_PER_TRIP, NUM_TRUCKS, TRUCK_ROLE


class MainModel(mesa.Model):
    """
    The model that coordinates the agents and environment for a Hub and Spoke model of Avian Influenza.
    """

    def __init__(self, seed=None, simulator=None, is_stop_community_infection=True, is_quarantine_farmer=True):
        super().__init__(seed=seed)
        if simulator is not None:
            self.simulator = simulator
            self.simulator.setup(self)

        self.is_stop_community_infection = is_stop_community_infection
        self.is_quarantine_farmer = is_quarantine_farmer

        self.width = 43
        self.height = 31

        # Create grid using experimental cell space
        self.grid = OrthogonalMooreGrid(
            [self.width, self.height],
            torus=False,
            capacity=math.inf,
            random=self.random,
        )

        # queues to manage farm requests for vets
        self.farm_request_queue = []
        self.farm_emergency_request_queue = []
        self.available_farm_clinicians = []
        self.available_farm_students = []
        self.available_trucks = []

        self.infection_network = InfectionNetwork()

        # keep references to the different types of locations
        self.hospital_cells = {HospitalDepartment.FARM_SERVICES: [], HospitalDepartment.SMALL_ANIMAL: [],
                               HospitalDepartment.LARGE_ANIMAL: [], HospitalDepartment.COMMON: []}
        self.farm_cells = []

        # --------------------------
        # create the hospital

        hospital_width = 30

        # large animal clinic
        # from map is 18x21 = 378
        # roughly width=30, height=12
        large_start = 0
        large_height = 12

        # farm services area
        # from map is 4*7 + 1 = 29
        # roughly width=30, height=1
        farm_start = large_start + large_height
        farm_height = 1

        # common area
        # from map: 3*3 + 2*8 + 1*4 + 24*1 + 24*1 = 77
        # roughly width=30, height=3
        common_start = farm_start + farm_height
        common_height = 3

        # small animal clinic
        # from map is 14*3 + 7*6 + 4*24 + 7*12 + 18*10 = 444
        # roughly width=30, height=15
        small_start = common_start + common_height
        small_height = 15

        for cell_x in range(hospital_width):
            for cell_y in range(large_start, large_start+large_height):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.LARGE_ANIMAL, cell=cell)
                self.hospital_cells[HospitalDepartment.LARGE_ANIMAL].append(cell)

            for cell_y in range(farm_start, farm_start+farm_height):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.FARM_SERVICES, cell=cell)
                self.hospital_cells[HospitalDepartment.FARM_SERVICES].append(cell)

            for cell_y in range(common_start, common_start+common_height):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.COMMON, cell=cell)
                self.hospital_cells[HospitalDepartment.COMMON].append(cell)

            for cell_y in range(small_start, small_start+small_height):
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.SMALL_ANIMAL, cell=cell)
                self.hospital_cells[HospitalDepartment.SMALL_ANIMAL].append(cell)

        # ------------------------- end hospital space definition
        # ------------------------- Farms

        # load the farm file to define farms and farmers
        farm_df = pd.read_excel(get_input_data_dir() / FARM_INPUT_FILENAME)
        # add the farm cells, starting top right and every second cell to bottom then left
        cell_x = self.width - 2  # all the way right, with 1 padding
        cell_y = 1  # bottom with 1 padding
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
            if cell_y >= self.height-1:
                cell_y = 1
                cell_x -= 3

        # ------------------------- end farm space definition
        # ------------------------- People

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

        # ------------------------- end initial people placement
        # ------------------------- Trucks
        cell_x = hospital_width
        cell_y = farm_start
        for truck_num in range(NUM_TRUCKS):
            cell = self.grid[cell_x, cell_y+truck_num]
            truck = TruckAgent(self, cell, truck_num)

            self.available_trucks.append(truck)

        # ------------------------- end initial truck placement

        self.community_model = SIRModel(self, 'community')

        # track visits to farms by FS vets (doesn't fit with collectors)
        # farm_visits_by_vet {step_num: [(vet id, farm id), ...]
        self.farm_visits_by_vets = defaultdict(list)

        # add collecters for the people infection trackers
        model_reporters = {
            'Infected': lambda model: model.infected_proportion(),
            'Exposed': lambda model: model.exposed_proportion(),
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
        if self.is_stop_community_infection and self.community_model.proportion_infected > 0:
            # there has been community spillover - stop here
            self.running = False
        else:
            # go ahead with another model step
            self.agents.shuffle_do('step')
            self.community_model.step()

            # prioritise is_emergency visits anytime
            self.start_farm_visit(is_emergency=True, take_student=False)

            # normal priority farm trips are started at beginning and middle of workdays
            if is_start_of_workday(self.steps) or is_middle_of_workday(self.steps):
                self.start_farm_visit(is_emergency=False, take_student=True)

            self.datacollector.collect(self)

    def start_farm_visit(self, is_emergency, take_student):
        """
        Send a clinician with a truck on a farm visit. Optionally check if a student is available.

        Might be an emergency visit or a normal priority.

        :param is_emergency: True if this trip should draw farms from the emergency queue.
        Otherwise use the non-urgent farm request queue.
        :type is_emergency: bool
        :param take_student: True indicates to take a student if they are available.
        :type take_student: bool
        """
        queue = self.farm_emergency_request_queue if is_emergency else self.farm_request_queue
        while len(queue) > 0 and len(self.available_farm_clinicians) > 0 and len(self.available_trucks) > 0:
            if is_emergency:
                farms_to_visit = self.farm_emergency_request_queue[:MAX_VISITS_PER_TRIP]
                # remove those requests from the queue
                del self.farm_emergency_request_queue[:MAX_VISITS_PER_TRIP]
            else:
                farms_to_visit = self.farm_request_queue[:MAX_VISITS_PER_TRIP]
                # remove those requests from the queue
                del self.farm_request_queue[:MAX_VISITS_PER_TRIP]

            # get the next available clinician and give them a visit list
            clinician = self.available_farm_clinicians.pop(0)
            # print(f'  c: {clinician.name}')
            clinician.farms_to_visit = farms_to_visit.copy()
            # send them on their way
            clinician.visit_next_farm()

            # send a truck
            truck = self.available_trucks.pop(0)
            # print(f'  t: {truck.name}')
            truck.farms_to_visit = farms_to_visit.copy()
            truck.visit_next_farm()

            # optionally, send a student
            if take_student:
                # if there's a student around, they should go along as well
                if len(self.available_farm_students) > 0:
                    student = self.available_farm_students.pop(0)
                    # print(f'  s: {student.name}')
                    student.farms_to_visit = farms_to_visit.copy()
                    student.visit_next_farm()

    def come_back_from_farm(self, farm_visitor):
        """
        A vet or take_student has returned from visiting a farm. Put them back in the relevant availability queue
        :param farm_visitor: Returning Vet or Student
        :type farm_visitor: PeopleAgents.FarmVisitorAgent object
        """
        if farm_visitor.role == TRUCK_ROLE:
            self.available_trucks.append(farm_visitor)
        elif farm_visitor.role == PersonRole.FARM_SERVICES_CLINICIAN:
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

    def exposed_proportion(self):
        """

        :return:
        :rtype:
        """
        exposed_people = [agent for agent in self.agents
                          if isinstance(agent, PersonAgent) and agent.disease_state == DiseaseState.EXPOSED]
        return len(exposed_people) / self.total_people

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

