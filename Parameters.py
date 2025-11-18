import configparser

from support_functions import get_scenario_input_dir, get_input_data_dir
from constants import DEFAULT_PARAMETERS_INPUT_FILENAME, FarmHousing, FarmMilkingSystem, \
    SCENARIO_PARAMETERS_INPUT_FILENAME, Cleaning, input_to_role


class Parameters:
    """
    Access to all the parameters for running the model
    """

    def __init__(self, scenario_name=None):

        # read the configuration - default parameters first
        self.config = configparser.ConfigParser()
        param_filepaths = [get_input_data_dir() / DEFAULT_PARAMETERS_INPUT_FILENAME]
        if scenario_name is not None:
            # override with specific parameters for the scenario
            param_filepaths.append(get_scenario_input_dir(scenario_name) / SCENARIO_PARAMETERS_INPUT_FILENAME)
        self.config.read(param_filepaths)

        # ----------------- MODEL ------------
        self.is_stop_community_infection = self.config['MODEL'].getboolean('IS_STOP_COMMUNITY_INFECTION')
        self.is_quarantine_farmer = self.config['MODEL'].getboolean('IS_QUARANTINE_FARMER')

        # ----------------- TIME ------------
        self.steps_per_day = self.config['TIME'].getint('STEPS_PER_DAY')
        self.daytime_steps = self.config['TIME'].getint('DAYTIME_STEPS')
        self.work_day_steps = [step+1 for step in range(self.daytime_steps)]

        # ----------------- FARM SERVICE VISITS TO FARMS ------------
        self.emergency_visits_per_month = self.config['FARM VISITS'].getint('EMERGENCY_VISITS_PER_MONTH')
        # 8 = number of weekend days in a month
        self.emergency_visits_per_step = self.emergency_visits_per_month / (8 * self.steps_per_day)

        # Unscheduled calls that aren't emergencies, should result in 1-2 visits per day in business hours
        self.non_urgent_calls_per_day = self.config['FARM VISITS'].getfloat('NON_URGENT_CALLS_PER_DAY')
        self.non_urgent_calls_per_step = self.non_urgent_calls_per_day / self.steps_per_day

        self.num_trucks = self.config['FARM VISITS'].getint('NUM_TRUCKS')

        self.vet_steps_at_farm = self.config['FARM VISITS'].getfloat('VET_STEPS_AT_FARM')
        self.vet_contacts_per_step = self.config['FARM VISITS'].getfloat('VET_CONTACTS_PER_STEP')

        self.truck_contacts_per_step = self.config['FARM VISITS'].getfloat('TRUCK_CONTACTS_PER_STEP')

        # maximum number of farms that can be visited in a single trip from the VTH by a farm services clinician
        self.max_visits_per_trip = self.config['FARM VISITS'].getint('MAX_VISITS_PER_TRIP')

        # number of steps to travel between hospital and farm or between farms
        self.visit_travel_steps = self.config['FARM VISITS'].getint('VISIT_TRAVEL_STEPS')

        # ----------------- DISEASE ------------------------------------
        self.num_init_infected_farms = self.config['DISEASE'].getint('NUM_INIT_INFECTED_FARMS')

        self.human_infect_cattle_prob = self.config['DISEASE'].getfloat('HUMAN_INFECT_CATTLE_PROB')
        self.human_infect_human_prob = self.config['DISEASE'].getfloat('HUMAN_INFECT_HUMAN_PROB')
        self.cattle_infect_human_prob = self.config['DISEASE'].getfloat('CATTLE_INFECT_HUMAN_PROB')
        self.cattle_infect_cattle_prob = self.config['DISEASE'].getfloat('CATTLE_INFECT_CATTLE_PROB')
        self.truck_infect_cattle_prob = self.config['DISEASE'].getfloat('TRUCK_INFECT_CATTLE_PROB')
        self.cattle_infect_truck_prob = self.config['DISEASE'].getfloat('CATTLE_INFECT_TRUCK_PROB')

        # vaccination reduces the probabilities of both being infected and infecting. Only people/humans are vaccinated
        # VACC_ROLES is either None or a comma (,) separated list of the roles of people that are getting vaccinated
        # possible roles are: farmer, farm services vet, farm services technician, farm services student,
        # large animal vet, large animal staff, large animal student, small animal vet, small animal staff,
        # small animal student, floating vet, floating clinician, floating staff, floating student
        role_input_list = [role.strip().lower() for role in self.config['DISEASE'].get('VACC_ROLES').split(',')]
        self.vacc_roles = []
        for role_input in role_input_list:
            if role_input in input_to_role:
                self.vacc_roles.append(input_to_role[role_input])
        self.vacc_human_infect_cattle_prob = self.config['DISEASE'].getfloat('VACC_HUMAN_INFECT_CATTLE_PROB')
        self.vacc_cattle_infect_human_prob = self.config['DISEASE'].getfloat('VACC_CATTLE_INFECT_HUMAN_PROB')
        self.vacc_human_infect_human_prob = self.config['DISEASE'].getfloat('VACC_HUMAN_INFECT_HUMAN_PROB')
        self.vacc_human_infect_env_prob = self.config['DISEASE'].getfloat('VACC_HUMAN_INFECT_ENV_PROB')
        self.vacc_env_infect_human_prob = self.config['DISEASE'].getfloat('VACC_ENV_INFECT_HUMAN_PROB')

        self.human_exposed_days = self.config['DISEASE'].getfloat('HUMAN_EXPOSED_DAYS')
        self.human_exposed_steps = self.convert_days_to_steps(self.human_exposed_days)
        self.human_infectious_days = self.config['DISEASE'].getfloat('HUMAN_INFECTIOUS_DAYS')
        self.human_infectious_steps = self.convert_days_to_steps(self.human_infectious_days)
        self.human_recovered_days = self.config['DISEASE'].getfloat('HUMAN_RECOVERED_DAYS')
        self.human_recovered_steps = self.convert_days_to_steps(self.human_recovered_days)

        self.cattle_exposed_days = self.config['DISEASE'].getfloat('CATTLE_EXPOSED_DAYS')
        self.cattle_exposed_steps = self.convert_days_to_steps(self.cattle_exposed_days)
        self.cattle_infected_days = self.config['DISEASE'].getfloat('CATTLE_INFECTED_DAYS')
        self.cattle_infected_steps = self.convert_days_to_steps(self.cattle_infected_days)
        self.cattle_recovered_days = self.config['DISEASE'].getfloat('CATTLE_RECOVERED_DAYS')
        self.cattle_recovered_steps = self.convert_days_to_steps(self.cattle_recovered_days)

        # environment <-> human infection
        self.env_infect_human_prob = self.config['DISEASE'].getfloat('ENV_INFECT_HUMAN_PROB')
        self.human_infect_env_prob = self.config['DISEASE'].getfloat('HUMAN_INFECT_ENV_PROB')

        # environment <-> cattle interaction
        self.env_infect_cattle_prob = self.config['DISEASE'].getfloat('ENV_INFECT_CATTLE_PROB')
        self.cattle_infect_env_prob = self.config['DISEASE'].getfloat('CATTLE_INFECT_ENV_PROB')

        # environment <-> truck interaction
        self.env_infect_truck_prob = self.config['DISEASE'].getfloat('ENV_INFECT_TRUCK_PROB')
        self.truck_infect_env_prob = self.config['DISEASE'].getfloat('TRUCK_INFECT_ENV_PROB')

        self.env_infectious_days = self.config['DISEASE'].getfloat('ENV_INFECTIOUS_DAYS')
        self.env_infectious_steps = self.convert_days_to_steps(self.env_infectious_days)

        # ----------------- COMMUNITY -------------------------------
        self.community_population = self.config['COMMUNITY'].getfloat('COMMUNITY_POPULATION')
        self.community_contacts_per_step = self.config['COMMUNITY'].getint('COMMUNITY_CONTACTS_PER_STEP')

        # ----------------- FARM -------------------------------
        self.cattle_contacts_per_step = {
            FarmHousing.FREE_STALL: self.config['FARM'].getint('FREE_STALL_CONTACTS_PER_STEP'),
            FarmHousing.TIE_STALL: self.config['FARM'].getint('TIE_STALL_CONTACTS_PER_STEP'),
            FarmHousing.STRAW_PACK: self.config['FARM'].getint('STRAW_PACK_CONTACTS_PER_STEP'),
            FarmHousing.TIE_AND_STRAW: self.config['FARM'].getint('TIE_AND_STRAW_CONTACTS_PER_STEP'),
        }

        self.num_milking_events_per_day = self.config['FARM'].getint('PARLOUR_MILKING_CONTACTS')

        # number of contacts cow<->farmer at each milking event
        self.num_milking_contacts = {
            FarmMilkingSystem.PARLOUR: self.config['FARM'].getint('PARLOUR_MILKING_CONTACTS'),
            FarmMilkingSystem.AMS: self.config['FARM'].getint('AMS_MILKING_CONTACTS'),
            FarmMilkingSystem.PIPELINE: self.config['FARM'].getint('PIPELINE_MILKING_CONTACTS'),
            FarmMilkingSystem.ROTARY_PARLOUR: self.config['FARM'].getint('ROTARY_PARLOUR_MILKING_CONTACTS')
        }

        # ----------------- CLEANING -------------------------------
        truck_cleaning_input = self.config['CLEANING'].get('TRUCK').strip().lower()
        if truck_cleaning_input == 'daily':
            self.truck_cleaning_schedule = Cleaning.DAILY
        elif truck_cleaning_input == 'visit':
            self.truck_cleaning_schedule = Cleaning.VISIT
        else:
            # default to none on any other input
            self.truck_cleaning_schedule = Cleaning.NONE

        hospital_cleaning_input = self.config['CLEANING'].get('HOSPITAL').strip().lower()
        if hospital_cleaning_input == 'daily':
            self.hospital_cleaning_schedule = Cleaning.DAILY
        else:
            # default to none on any other input
            self.hospital_cleaning_schedule = Cleaning.NONE

        # ----------------- PEOPLE -------------------------------
        self.people_sheet = self.config['PEOPLE'].get('SHEET_NAME').strip().lower()

    # ---------------------------------------------------------
    # useful functions

    def convert_per_day_to_per_step(self, num_per_day):
        """
        Converts a number of events per day into a number of events per step. Rounds to the nearest integer.

        :param num_per_day: Number of events per day
        :type num_per_day: int
        :return: Number of events per step
        :rtype: int
        """
        return max(1, round(num_per_day / self.steps_per_day))

    def convert_days_to_steps(self, num_days):
        """
        Converts a number of days into a number of steps. Rounds to the nearest integer.

        :param num_days: Number of days to convert
        :type num_days: numeric
        :return: Number of model steps
        :rtype: int
        """
        return round(num_days * self.steps_per_day)



