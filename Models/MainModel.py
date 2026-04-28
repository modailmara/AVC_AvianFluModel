import mesa
import math
from mesa.experimental.cell_space import OrthogonalMooreGrid
import pandas as pd
from collections import defaultdict
from functools import partial

from InputData.scenario_constants import STEPS
from support_functions import get_input_data_dir, get_output_data_dir
from Models.CompartmentModel import SEIRModel
from InfectionNetwork import InfectionNetwork
from Parameters import Parameters

from Models.PeopleAgents import PersonAgent, FarmerAgent, FarmVisitorAgent
from Models.LocationAgents import DairyFarmAgent, HospitalAgent, TruckAgent, LocationAgent
from constants import FARM_INPUT_FILENAME, HospitalDepartment, PEOPLE_INPUT_FILENAME, PersonRole, DiseaseState, \
    input_to_role, TRUCK_ROLE, Cleaning, Location


def count_person_agents_with_disease_state(disease_state, model):
    """
    Returns the number of the model's person agents that have the supplied disease state.
    :param disease_state: The disease state of person agents to count
    :type disease_state: DiseaseState
    :param model: The ABM model containing the agents
    :type model: MainModel
    :return: Count of agents with disease state matching the given disease_state
    :rtype: int
    """
    return len(model.agents.select(lambda a: isinstance(a, PersonAgent) and a.disease_state == disease_state))


def count_person_agents_with_disease_state_and_role(role, disease_state, model):
    """
    Returns the number of the model's person agents that have the supplied disease state and the supplied role.

    :param role: The role of the person agents to count
    :type role: PersonRole
    :param disease_state: The disease state of person agents to count
    :type disease_state: DiseaseState
    :param model: The ABM model containing the agents
    :type model: MainModel
    :return: Count of person agents with both matching role and disease state
    :rtype: int
    """
    return len(model.agents.select(lambda a: isinstance(a, PersonAgent)
                                             and a.disease_state == disease_state
                                             and a.role == role))


class MainModel(mesa.Model):
    """
    The model that coordinates the agents and environment for a Hub and Spoke model of Avian Influenza.
    """

    def __init__(self, seed=None, simulator=None, scenario_name=None,
                 **kwargs):
        super().__init__(seed=seed)
        if simulator is not None:
            self.simulator = simulator
            self.simulator.setup(self)

        # set up the parameters
        self.scenario_name = scenario_name
        self.scenario_value = None  # the value of the variable in this iteration
        self.params = Parameters(scenario_name)
        # the init argument values override the parameter values
        param_str_list = []
        for param_name, param_value in kwargs.items():
            # some parameters need proce
            if param_name == 'VACC_ROLES':
                value = self.params.process_vacc_roles(param_value)
            elif param_name in ['TRUCK_CLEANING_SCHEDULE', 'HOSPITAL_CLEANING_SCHEDULE']:
                value = self.params.process_cleaning_schedule(param_value)
            else:
                value = param_value
            setattr(self.params, param_name, value)
            param_str_list.append("{}-{}".format(param_name, param_value))
        self.scenario_value = '_'.join(param_str_list)

        # set up the grid
        self.width = 43
        self.height = 31
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
            # large animal clinic
            for cell_y in range(large_start, large_start+large_height):
                large_id = cell_x * large_height + cell_y
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.LARGE_ANIMAL, cell=cell, dept_id=large_id)
                self.hospital_cells[HospitalDepartment.LARGE_ANIMAL].append(cell)

            # farm services
            for cell_y in range(farm_start, farm_start+farm_height):
                farm_id = cell_x * farm_height + cell_y
                cell = self.grid[cell_x, cell_y]
                farm_services_agent = HospitalAgent(self, HospitalDepartment.FARM_SERVICES, cell=cell, dept_id=farm_id)
                self.hospital_cells[HospitalDepartment.FARM_SERVICES].append(cell)
            # the last farm services location agent is the truck bay
            self.truck_bay = farm_services_agent

            # Common areas
            for cell_y in range(common_start, common_start+common_height):
                common_id = cell_x * large_height + cell_y
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.COMMON, cell=cell, dept_id=common_id)
                self.hospital_cells[HospitalDepartment.COMMON].append(cell)

            # small animal clinic
            for cell_y in range(small_start, small_start+small_height):
                small_id = cell_x * small_height + cell_y
                cell = self.grid[cell_x, cell_y]
                HospitalAgent(self, HospitalDepartment.SMALL_ANIMAL, cell=cell, dept_id=small_id)
                self.hospital_cells[HospitalDepartment.SMALL_ANIMAL].append(cell)

        # ------------------------- end hospital space definition
        # ------------------------- Farms

        # load the farm file to define farms and farmers
        farm_df = pd.read_excel(get_input_data_dir() / FARM_INPUT_FILENAME)
        # add the farm cells, starting top right and every second cell to bottom then left
        cell_x = self.width - 2  # all the way right, with 1 padding
        min_farm_x = cell_x  # store the smallest x position of farms
        cell_y = 1  # bottom with 1 padding
        self.total_people = 0  # count the number of people, remains constant
        for _, farm_row in farm_df.iterrows():
            cell = self.grid[cell_x, cell_y]
            farm = DairyFarmAgent(self, cell,
                                  farm_row.farm_id, farm_row.herd_size, farm_row.visit_frequency_days,
                                  farm_row.milking_system, farm_row.housing, farm_row.pasture, num_farms=len(farm_df))
            self.farm_cells.append(cell)

            # one farmer per farm
            farmer = FarmerAgent(self, farm)
            farmer.vaccinated = PersonRole.FARMER in self.params.VACC_ROLES
            # print("  {} vacc status: {}".format(farmer.name, farmer.vaccinated))
            self.total_people += 1

            # increment the cell coordinates
            cell_y += 2
            if cell_y >= self.height-1:
                cell_y = 1
                cell_x -= 3

            min_farm_x = min(min_farm_x, cell_x)

        # do the initial infections - 1 on params.NUM_INIT_INFECTED_FARMS farms
        infected_farms = self.random.sample(
            self.agents_by_type[DairyFarmAgent],
            min(self.params.NUM_INIT_INFECTED_FARMS, len(self.agents_by_type[DairyFarmAgent]))
        )
        for farm in infected_farms:
            farm.cattle_model.infect_susceptible(1)
            # record this source of infection in the network
            self.infection_network.add_infection_source(farm.herd_short_name)

        # ------------------------- end farm space definition
        # ------------------------- People

        # load the people file to define hospital locations and staff/clinicians/students
        people_df = pd.read_excel(get_input_data_dir() / PEOPLE_INPUT_FILENAME, sheet_name=self.params.SHEET_NAME)
        people_df.columns = people_df.columns.str.lower()
        area_names = [name.split(':')[1].strip()
                      for name in people_df.columns if name.startswith('area:')]

        # create agents for each role
        for _, role_def_row in people_df.iterrows():
            role_name = role_def_row.type.lower().strip()
            person_role = input_to_role[role_name]
            num_role = int(role_def_row.num)
            self.total_people += num_role

            # vaccination status
            is_vaccinated = person_role in self.params.VACC_ROLES

            # parse the weightings for each area for this role
            area_weights = []
            for name in area_names:
                area = HospitalDepartment(name)
                area_weights.append((area, float(role_def_row['area: ' + name])))

            for person_num in range(num_role):
                if person_role in [PersonRole.FARM_SERVICES_CLINICIAN, PersonRole.FARM_SERVICES_STUDENT]:
                    visitor_agent = FarmVisitorAgent(self, person_num, cell=None, role=person_role,
                                                     area_weights=area_weights)
                    visitor_agent.vaccinated = is_vaccinated
                    # print("  {} vacc_status: {}".format(visitor_agent.name, visitor_agent.vaccinated))
                    if person_role == PersonRole.FARM_SERVICES_CLINICIAN:
                        # add the farmer to the queue for vet farm visits
                        self.available_farm_clinicians.append(visitor_agent)
                    elif person_role == PersonRole.FARM_SERVICES_STUDENT:
                        # add the farmer to the queue for vet farm visits
                        self.available_farm_students.append(visitor_agent)
                else:
                    hospital_agent = PersonAgent(self, person_num, cell=None, role=person_role,
                                                 area_weights=area_weights)
                    hospital_agent.vaccinated = is_vaccinated
                    # print("  {} vacc_status: {}".format(hospital_agent.name, hospital_agent.vaccinated))
                # person.move()

        # ------------------------- end initial people placement
        # ------------------------- Trucks
        home_cell_x = hospital_width
        home_cell_y = farm_start
        travel_cell_x = (hospital_width + min_farm_x) // 2
        travel_cell_y = home_cell_y - self.params.NUM_TRUCKS
        for truck_num in range(self.params.NUM_TRUCKS):
            home_cell = self.grid[home_cell_x, home_cell_y+truck_num]
            travel_cell = self.grid[travel_cell_x, travel_cell_y + 2 * truck_num]
            truck = TruckAgent(self, home_cell, truck_num, travel_cell, self.truck_bay)

            self.available_trucks.append(truck)

        # ------------------------- end initial truck placement
        # ------------------------- Community setup
        self.community_model = SEIRModel(self, 'community',
                                         self.params.COMMUNITY_POPULATION, self.params.HUMAN_INFECT_HUMAN_PROB,
                                         self.params.human_exposed_steps, self.params.human_infectious_steps,
                                         self.params.human_recovered_steps, self.params.COMMUNITY_CONTACTS_PER_STEP)

        # ------------------------- end Community setup
        # ------------------------- Data logging
        # farm_visits_by_vet {step_num: [(vet id, farm id), ...]
        self.farm_visits_by_vets = defaultdict(list)

        model_reporters = {  # 'paths': lambda model: model.infection_network,
                           'Community_num_SUSCEPTIBLE': lambda model: model.community_model.num_susceptible,
                           'Community_num_EXPOSED': lambda model: model.community_model.num_exposed,
                           'Community_num_INFECTIOUS': lambda model: model.community_model.num_infectious,
                           'Community_num_RECOVERED': lambda model: model.community_model.num_recovered}

        # log the spread of disease in the community

        # log the numbers of people agents (all roles) with disease states
        for disease_state in [DiseaseState.SUSCEPTIBLE, DiseaseState.EXPOSED, DiseaseState.INFECTIOUS,
                              DiseaseState.RECOVERED]:
            reporter_name = f"People_num_{disease_state.name}"

            model_reporters[reporter_name] = partial(count_person_agents_with_disease_state, disease_state)

        # log counts of disease state for all the people
        for person_role in PersonRole:
            for disease_state in [DiseaseState.SUSCEPTIBLE, DiseaseState.EXPOSED, DiseaseState.INFECTIOUS,
                                  DiseaseState.RECOVERED]:
                reporter_name = f"{person_role.name}_num_{disease_state.name}"

                model_reporters[reporter_name] = partial(count_person_agents_with_disease_state_and_role,
                                                         person_role, disease_state)

        # log the number of steps to first reach the community
        self.step_community_infected = math.nan
        model_reporters['steps_to_community'] = 'step_community_infected'

        # add in an agent reporter for each farm
        agent_reporters = {
            DairyFarmAgent: {
                'Farm_Population': 'herd_count',
                'Farm_num_Susceptible': 'num_susceptible',
                'Farm_num_Exposed': 'num_exposed',
                'Farm_num_Infectious': 'num_infected',
            }
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
        if self.community_model.susceptible < self.community_model.population:
            if pd.isna(self.step_community_infected):
                # there has been community spillover and this is the first time the community is exposed
                # write out the infection graph
                self.infection_network.write_network(get_output_data_dir(self.scenario_name), "spillover",
                                                     self.scenario_name, self.scenario_value)
                # record the step of the first community exposure
                self.step_community_infected = self.steps
                # print('   {}: first infectious {}'.format(self.steps, self.step_community_infected))
        if self.community_model.susceptible < self.community_model.population \
                and self.params.IS_STOP_COMMUNITY_INFECTION:
            # stop running here
            self.running = False
        else:  # go ahead with another model step
            # person agents start/stop work at begin/end of business day
            self.agents.select(lambda a: isinstance(a, PersonAgent)).shuffle_do('start_stop_work')

            # location agents sometimes have a cleaning schedule
            self.agents.select(lambda a: isinstance(a, LocationAgent)).shuffle_do('scheduled_cleaning')

            # start any requested farm visits
            self.agents_by_type[DairyFarmAgent].shuffle_do('request_vet')
            # prioritise is_emergency visits anytime
            self.start_farm_visit(is_emergency=True, take_student=False)
            # normal priority farm trips are started at beginning and middle of workdays
            if self.is_start_of_workday(self.steps) or self.is_middle_of_workday(self.steps):
                self.start_farm_visit(is_emergency=False, take_student=True)

            # move agents
            self.agents.shuffle_do('move')

            # progress existing disease
            self.agents.shuffle_do('progress_disease')
            self.community_model.progress_infection()

            # agents infect other agents (people and location) and compartmental entities (cows and community)
            self.agents.shuffle_do('infect_others')
            # agents in the community may be infected by the community
            self.agents.select(lambda a: isinstance(a, PersonAgent) and a.location == Location.COMMUNITY) \
                .shuffle_do('become_infected_by_community')
            # agents on a farm may become infected by the cattle herd
            self.agents.select(lambda a: isinstance(a, PersonAgent) and a.location == Location.FARM) \
                .shuffle_do('become_infected_by_cattle')

            # do any scheduled cleaning/disinfecting of location agents
            self.agents.select(lambda a: isinstance(a, LocationAgent)).shuffle_do('scheduled_cleaning')

            # collect data from the model
            self.datacollector.collect(self)

        if self.steps == STEPS:
            # at the end of the simulation - write out the completed disease network
            self.infection_network.write_network(get_output_data_dir(self.scenario_name), "complete",
                                                 self.scenario_name, self.scenario_value)

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
                farms_to_visit = self.farm_emergency_request_queue[:self.params.MAX_VISITS_PER_TRIP]
                # remove those requests from the queue
                del self.farm_emergency_request_queue[:self.params.MAX_VISITS_PER_TRIP]
            else:
                farms_to_visit = self.farm_request_queue[:self.params.MAX_VISITS_PER_TRIP]
                # remove those requests from the queue
                del self.farm_request_queue[:self.params.MAX_VISITS_PER_TRIP]

            # get the next available clinician and give them a visit list
            clinician = self.available_farm_clinicians.pop(0)
            # print(f'  c: {clinician.name}')

            visit_people = [clinician]

            # optionally, send a student
            if take_student:
                # if there's a student around, they should go along as well
                if len(self.available_farm_students) > 0:
                    student = self.available_farm_students.pop(0)
                    # print(f'  s: {student.name}')
                    visit_people.append(student)

            # send a truck
            truck = self.available_trucks.pop(0)
            # print(f'  t: {truck.name}')
            truck.start_travel_from_hospital(farms_to_visit, visit_people)

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
        :return: Proportion (0-1) of the people agents with disease state INFECTIOUS
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
        Proportion of people that are infectious
        :return: Proportion (0-1) of the people agents with disease state INFECTIOUS
        :rtype:
        """
        infected_people = [agent for agent in self.agents
                           if isinstance(agent, PersonAgent) and agent.disease_state == DiseaseState.INFECTIOUS]

        return len(infected_people) / self.total_people

    def recovered_proportion(self):
        """
        Proportion of people that are susceptible
        :return: Proportion (0-1) of the people agents with disease state INFECTIOUS
        :rtype:
        """
        recovered_people = [agent for agent in self.agents
                            if isinstance(agent, PersonAgent) and agent.disease_state == DiseaseState.RECOVERED]

        return len(recovered_people) / self.total_people

    def get_day_from_steps(self, step_number):
        """
        Gets the day number given a step number.
        :param step_number: The step number to convert to a day number
        :type step_number: int
        :return: Day number for the given step
        :rtype: int
        """
        return step_number // self.params.STEPS_PER_DAY

    def get_weeks_days_steps(self, steps):
        """
        From a number of steps, calculates the number of weeks and days.
        Also returns the number of leftover days (from week calculation), and number of leftover steps (from days).

        Note that days is from the steps, not after weeks is calculated. For example (assume STEPS_PER_DAY=16):
        get_weeks_days_steps(130) gives 1 week, 8 days, 1 leftover day, and 2 leftover steps

        :param steps: Total number of model steps.
        :type steps: int
        :return: Tuple of (total weeks, total days, days left after weeks, steps left after days)
        :rtype: tuple
        """
        days, leftover_steps = divmod(steps, self.params.STEPS_PER_DAY)
        weeks, leftover_days = divmod(days, 7)

        return weeks, days, leftover_days, leftover_steps

    def is_business_hours(self, all_steps):
        """
        True if the model step falls in business hours.
        Step 1 is the first step of the first workday (Monday). Each 24 hours is STEPS_PER_DAY steps long.
        The first 1 <= x <= DAYTIME_STEPS of each day is work hours.
        Weekends (saturday and sunday) are not business hours.

        :param all_steps: Total count of steps since the model started
        :type all_steps: int
        :return: True if the step falls in business hours
        :rtype: bool
        """
        # get the number of days and the steps into the day
        _, _, leftover_days, leftover_steps = self.get_weeks_days_steps(all_steps)

        # print("{} (w={}, d={}, s={}): {}".format(all_steps, weeks, leftover_days, leftover_steps,
        #                                          leftover_days < 5 and 1 <= leftover_steps <= DAYTIME_STEPS))
        return leftover_days < 5 and 1 <= leftover_steps <= self.params.DAYTIME_STEPS

    def is_weekend(self, all_steps):
        """
        True if the model step falls in a weekend
        Step 1 is the first step of the first workday (Monday). Each 24 hours is STEPS_PER_DAY steps long.
        Weekends (saturday and sunday) are days 5 and 6 of each week

        :param all_steps: Total count of steps since the model started
        :type all_steps: int
        :return: True if the step falls in a weekend
        :rtype: bool
        """
        # get the number of days and the steps into the day
        _, _, leftover_days, _ = self.get_weeks_days_steps(all_steps)

        return leftover_days in [5, 6]

    def is_start_of_workday(self, step):
        """
        Returns True if the step is the first step of a working day.

        Step 1 is the first step of the first workday (Monday). Each 24 hours is STEPS_PER_DAY steps long.
        The first 1 <= x <= DAYTIME_STEPS of each day is work hours.
        Weekends (saturday and sunday, days 5 and 6) are not business hours.

        :param step: Step count of the model
        :type step: int
        :return: True if the first step of a weekday
        :rtype: bool
        """
        # get the number of days and the steps into the day
        _, _, leftover_days, leftover_steps = self.get_weeks_days_steps(step)

        # True if a weekday and the first step of the day
        return leftover_days in range(5) and leftover_steps == 1

    def is_middle_of_workday(self, step):
        """
        Returns True if the step is the middle step of a working day.

        Step 1 is the first step of the first workday (Monday).
        The first 1 <= x <= DAYTIME_STEPS of each day is work hours.
        Weekends (saturday and sunday, days 5 and 6) are not business hours.

        :param step: Step count of the model
        :type step: int
        :return: True if step is the middle step of a weekday
        :rtype: bool
        """
        # get the number of days and the steps into the day
        _, _, leftover_days, leftover_steps = self.get_weeks_days_steps(step)

        # True if a weekday and the first step of the day
        return leftover_days in range(5) and leftover_steps == self.params.DAYTIME_STEPS // 2 + 1

    def is_after_hours_workday(self, step):
        """
        Returns True if the step is after hours on a workday

        :param step: Step count of the model
        :type step: int
        :return: True if step is the middle step of a weekday
        :rtype: bool
        """
        _, _, leftover_days, leftover_steps = self.get_weeks_days_steps(step)

        return leftover_steps in range(5) and leftover_steps >= self.params.DAYTIME_STEPS

    def is_num_steps_after_workday(self, num_steps):
        """
        Returns True if current time steps are num_steps after the workday has finished.

        :param num_steps: Number of steps after the workday has finished.
        :type num_steps: int
        :return: True if current step is end_of_workday + num_steps = current step
        :rtype: bool
        """
        _, _, leftover_days, leftover_steps = self.get_weeks_days_steps(self.steps)

        is_num_steps_after_workday = leftover_days in range(5) \
                                     and leftover_steps == self.params.DAYTIME_STEPS + num_steps

        return is_num_steps_after_workday